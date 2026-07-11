"""
T031 hooks 2-4 -- method-baseline enforcement: pre-registered acceptance (committed
BEFORE impl, M3/T031 -- yes, the checker's own pins obey the law it enforces).
Spec: docs/method-baseline-2026-07.md 'Enforcement lane' (hook order reconciled).

Hook 2  scripts/check_preregistration.py  (M3): a ship that stages a NEW pre-registered
        pin file TOGETHER with non-test source FAILS -- registration is its own commit,
        BEFORE impl. Registration-only ships pass; modifying an EXISTING pin file in an
        impl ship passes (harness fixes are review-territory, not machine-checkable).
        --audit N reports historical compliance (the M3 metric).
Hook 3  scripts/arc_scorecard.py  (wrap-time): deterministic M-practice reads over the
        arc window (registrations, verbatim records, guards born, gated-ship ratio,
        reverts, UNGATED audit lines) -- zero-signal practices render as annotate-me
        prompts, never silently absent. Wired into the wrap draft.
Hook 4  scripts/check_verbatim_citation.py  (M6): a ship message that carries GATE
        language (GATE GREEN/RED, AFFIRM, verify record/verdict) must cite a
        research/reviewed/ path. No hatch -- the record must exist anyway (M6 bar).

Run: py -m pytest tests/test_t031_hooks.py -q
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PY = sys.executable

_H2 = os.path.join(_ROOT, "scripts", "check_preregistration.py")
_H3 = os.path.join(_ROOT, "scripts", "arc_scorecard.py")
_H4 = os.path.join(_ROOT, "scripts", "check_verbatim_citation.py")

_BUILT = all(os.path.isfile(p) for p in (_H2, _H3, _H4))

pytestmark = pytest.mark.skipif(
    not _BUILT, reason="T031 hooks 2-4 pins pre-registered; impl pending (assertions frozen)")


def _run(script, *argv):
    r = subprocess.run([_PY, script, *argv], capture_output=True, text=True,
                       cwd=_ROOT, timeout=120)
    return r.returncode, (r.stdout + r.stderr)


# ---------------- Hook 2: pre-registration checker (M3) ----------------

_FAKE_PIN = os.path.join(_ROOT, "tests", "test_zzz_rb99_fakepin.py")
_FAKE_BODY = '"""RB-99 pins -- pre-registered acceptance (committed BEFORE impl)."""\n'


@pytest.fixture()
def fake_pin():
    with open(_FAKE_PIN, "w", encoding="utf-8") as f:
        f.write(_FAKE_BODY)
    yield "tests/test_zzz_rb99_fakepin.py"
    try:
        os.remove(_FAKE_PIN)
    except OSError:
        pass


def test_h2_new_pin_with_source_fails(fake_pin):
    rc, out = _run(_H2, "RB-99 impl + pins in one go", fake_pin, "core/comm/bus.py")
    assert rc == 1 and "M3" in out, \
        "a NEW pre-registered pin file shipping WITH source is the M3 violation"


def test_h2_registration_only_passes(fake_pin):
    rc, out = _run(_H2, "RB-99 registration: pins committed BEFORE impl", fake_pin)
    assert rc == 0, "registration-only ships are the law being followed"


def test_h2_existing_pin_with_source_passes():
    rc, out = _run(_H2, "RB-21 impl (harness-only pin fix)",
                   "tests/test_rb21_consumer_seat.py", "core/comm/runner_lock.py")
    assert rc == 0, "an EXISTING pin file in an impl ship is fine (harness fixes)"


def test_h2_no_tests_staged_passes():
    rc, out = _run(_H2, "docs fixup", "docs/ROADMAP.md")
    assert rc == 0


# ---------------- Hook 4: verbatim-record linter (M6) ----------------

def test_h4_gate_language_without_citation_fails():
    rc, out = _run(_H4, "RB-99 landed: deepseek GATE GREEN, all pins pass")
    assert rc == 1 and "research/reviewed" in out, \
        "a GATE decision must cite its persisted verbatim record (M6)"


def test_h4_gate_language_with_citation_passes():
    rc, out = _run(_H4, "RB-99 landed: GATE GREEN per "
                        "research/reviewed/deepseek-rb21-verify-2026-07-11.md")
    assert rc == 0


def test_h4_plain_message_passes():
    rc, out = _run(_H4, "typo fix in the boot banner")
    assert rc == 0


# ---------------- Hook 3: arc scorecard (wrap-time) ----------------

def test_h3_scorecard_runs_and_reads_the_arc():
    rc, out = _run(_H3, "--days", "3")
    assert rc == 0
    for marker in ("M3", "M6", "M11"):
        assert marker in out, f"the scorecard reads {marker} deterministically"
    assert "annotate" in out.lower() or "skipped" in out.lower(), \
        "zero-signal practices surface as annotate-me prompts, never silently absent"


# ---------------- wiring (built != wired) ----------------

def test_hooks_wired():
    ship = open(os.path.join(_ROOT, "scripts", "ship.py"), encoding="utf-8").read()
    assert "check_preregistration" in ship, "hook 2 rides the ship gate"
    assert "check_verbatim_citation" in ship, "hook 4 rides the ship gate"
    cli = open(os.path.join(_ROOT, "agent_cli.py"), encoding="utf-8").read()
    assert "arc_scorecard" in cli, "hook 3 rides the wrap draft"
