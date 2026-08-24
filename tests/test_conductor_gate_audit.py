"""RED pins: the conductor gate's audit trail must be able to tell the truth about itself.

TWO DEFECTS, both found 2026-08-24 while triaging a 2h44m conductor outage, and both
structural rather than incidental:

1. THE AUDIT LOG HAS NO TEST ISOLATION. `append_provenance` resolves to a machine-global
   %TEMP% path, so `tests/drill_conductor_gate.py` -- which deliberately raises
   `RuntimeError("probe exploded")` and runs a dry-run activation -- writes into the
   PRODUCTION audit trail. Reading that log during the incident, those lines parse as a
   real 12:04:59 detection-that-crashed. They nearly became the headline of the
   post-mortem. An audit log that manufactures false incident narratives is worse than
   no audit log, because it is believed.

   Note the second-order defect: `AKASHIC_CONDUCTOR_PROVENANCE` exists and looks like
   the control for this, but it is only consulted in the FALLBACK branch after the
   wake_seat writer fails. An env var that advertises control it does not have is its
   own small lie.

2. THE GATE IS MUTE WHEN IT DECLINES. `notice_conductor_absence` returns at
   conductor_gate.py:556 without writing anything when `activate` is False. So
   "correctly stood down because the operator was present", "never evaluated", and
   "the runner was dead too" are the SAME observation: an empty log. Across the whole
   real outage the gate produced zero production output, and that silence is
   uninterpretable in either direction.

   The fix is not more logging -- it is a HEARTBEAT, so that absence becomes evidence.
   A defense whose only receipt is "it fired" cannot be distinguished from a defense
   that is not running.

Written before the implementation (M3). RED on arrival.
"""
from __future__ import annotations

import time

import pytest

from core.comm import conductor_gate as cg


def _reap_orphan(agent):
    return "orphan (marker 99m stale, chain broken at pid 1234 (dead))"


def _att_mix(agent):
    return "UNATTENDED" if agent == "claude" else "ATTENDED"


def _att_attended(agent):
    return "ATTENDED"


def _reap_alive(agent):
    return "alive-or-unknown"


def _op_absent():
    return False


@pytest.fixture()
def prov(tmp_path, monkeypatch):
    """Redirect the audit log. If this fixture does not actually redirect, the pins
    below are writing into the production trail -- which is the very defect."""
    p = tmp_path / "conductor_gate.provenance.log"
    monkeypatch.setenv(cg.PROVENANCE_ENV, str(p))
    cg._reset_heartbeat()
    return p


# ------------------------------------------------------- 1: the log is isolatable
def test_the_provenance_env_is_honoured_FIRST_not_merely_as_a_fallback(prov):
    """The env var must actually steer the write, not sit behind a writer that never
    fails. Otherwise every test run pollutes the production audit trail."""
    cg.append_provenance("a line that must land in the redirected file")
    assert prov.exists(), \
        f"{cg.PROVENANCE_ENV} did not steer the write -- the audit log is not isolatable"
    assert "must land in the redirected file" in prov.read_text(encoding="utf-8")


def test_a_drill_is_tagged_so_it_cannot_be_read_as_a_live_incident(prov):
    """Injected probes mean a DRILL. The 09:46 activation of 2026-08-24 was a drill and
    read exactly like a real succession in the log."""
    cg.decide_and_act(agent_self="kimi", reap_fn=_reap_orphan, att_fn=_att_mix,
                      op_present_fn=_op_absent, dry_run=True)
    text = prov.read_text(encoding="utf-8")
    assert "drill" in text.lower(), \
        f"an injected-probe run must be tagged as a drill, got: {text!r}"


def test_a_live_evaluation_is_tagged_live(prov):
    """The other half: a real pass must be positively marked, not merely untagged.
    'Absence of a drill tag' is a green produced by absence."""
    cg.notice_conductor_absence(agent_self="kimi")
    text = prov.read_text(encoding="utf-8")
    assert "live" in text.lower(), \
        f"a real evaluation must be tagged live, got: {text!r}"


# --------------------------------------------------- 2: silence must mean something
def test_a_stand_down_leaves_a_heartbeat(prov):
    """THE fix. On 2026-08-24 the gate wrote nothing across a 2h44m outage, so it was
    impossible to tell a correct stand-down from a gate that never ran."""
    v = cg.notice_conductor_absence(agent_self="kimi")
    assert not v.activate, "precondition: the conductor is alive in this environment"
    assert prov.exists() and prov.read_text(encoding="utf-8").strip(), \
        "a stand-down must leave a heartbeat -- otherwise absence proves nothing"


def test_the_heartbeat_is_rate_limited_so_it_does_not_spam_every_beat(prov):
    """The runners call this every 60s across the whole fleet. A line per beat would
    make the log unreadable, and an unread log is the same as no log."""
    for _ in range(5):
        cg.notice_conductor_absence(agent_self="kimi")
    lines = [ln for ln in prov.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1, \
        f"expected one rate-limited heartbeat, got {len(lines)}: {lines}"


def test_a_CHANGED_verdict_writes_immediately_even_inside_the_rate_window(prov):
    """Rate limiting must never swallow a STATE CHANGE. The transition from 'conductor
    alive' to 'conductor dead but operator present' is the most interesting line the
    log can carry, and it must not wait 15 minutes for a timer."""
    cg.notice_conductor_absence(agent_self="kimi")
    before = len(prov.read_text(encoding="utf-8").splitlines())

    # Same window, different verdict: now the conductor reads dead but we stand down
    # for a different reason. This MUST appear immediately.
    cg.decide_and_act(agent_self="kimi", reap_fn=_reap_orphan, att_fn=_att_attended,
                      op_present_fn=_op_absent, dry_run=True)
    after = len(prov.read_text(encoding="utf-8").splitlines())
    assert after > before, "a changed verdict must write immediately, not wait for the timer"


def test_the_heartbeat_records_which_condition_held(prov):
    """A heartbeat that says only 'still fine' is a green produced by absence. It must
    name the condition that produced the stand-down, so the log can be read backwards."""
    cg.notice_conductor_absence(agent_self="kimi")
    text = prov.read_text(encoding="utf-8").lower()
    assert any(k in text for k in ("not provably dead", "operator present",
                                   "conductor-specific", "idle immunity")), \
        f"the heartbeat must name its reason, got: {text!r}"


# ------------------------------------------------- the guard against regression
def test_the_gate_drill_suite_cannot_write_to_the_production_log(monkeypatch, tmp_path):
    """A conftest-level autouse fixture must isolate EVERY test, so a future drill
    file added by any seat is safe by default rather than by remembering."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    probe = (
        "import os, sys; sys.path.insert(0, r'%s');"
        "from core.comm import conductor_gate as cg;"
        "print(cg._provenance_path())" % str(root)
    )
    # The production path, resolved with no env override -- what an unisolated test
    # would write to.
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True,
                         text=True, cwd=str(root)).stdout.strip()
    assert out, "could not resolve the production provenance path"

    conftest = (root / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert cg.PROVENANCE_ENV in conftest, (
        "tests/conftest.py must redirect the conductor-gate audit log for every test; "
        "isolation by remembering is isolation that will lapse")
