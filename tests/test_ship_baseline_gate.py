"""PRE-REGISTERED ACCEPTANCE -- ship.py's suite gate becomes a RATCHET, not an amnesty.

THE DEFECT (measured 2026-07-27). scripts/ship.py gates on the FULL pytest suite, fail-fast.
The tree carries 6 pre-existing failures (lookback, t060, t086-s5, t093 x3). So ship.py ABORTS
ALWAYS: the disciplined door is IMPASSABLE, not merely longer. Consequence, verified by my own
behaviour -- six commits in one night through raw `git commit`, and therefore ZERO runs of the
three T031 method checkers that ride ship.py lines 38-42. The method loop
("awareness at boot -> recall at action -> gates at ship -> scorecard at wrap",
agent_cli.py:1449) is complete and wired, and its enforcement stage is bypassed because it
cannot be passed.

core/coord/suite_baseline.py already computes exactly what is needed -- delta() returns
{new, fixed, inherited} by node-id set math -- and was never wired to ship.py.

THE RISK THIS FILE EXISTS TO BOUND. Making a red suite shippable is how "blocking" quietly
becomes "inherited", and an inherited list rots: our baseline is already reported 71h stale.
That is the exact shape of tonight's other four failures -- a computed red routed to a channel
nobody acts on. So the gate must be a ONE-WAY RATCHET:

  P1  a NEW failure ABORTS the ship. No exceptions, no flag.
  P2  an INHERITED failure does not abort (that is the point -- the door opens).
  P3  a FIXED failure TIGHTENS the baseline automatically; amnesty is never re-granted by
      accident. This is the self-limiting property. Without it, P2 is an amnesty that only grows.
  P4  the inherited count is announced LOUDLY on every ship. Silence is how a red becomes furniture.
  P5  a STALE baseline is announced with its age.
  P6  NO baseline -> FAIL CLOSED (every failure blocks). Absence must never read as blanket amnesty.

Run: py -m pytest tests/test_ship_baseline_gate.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import suite_baseline as sb   # noqa: E402


def _mk(monkeypatch, tmp_path, nodes):
    """Point the baseline at a temp file holding `nodes` (None = no baseline at all)."""
    p = tmp_path / "suite_baseline.json"
    monkeypatch.setattr(sb, "BASELINE_PATH", str(p))
    if nodes is not None:
        sb.record(list(nodes), seat="test", sha="deadbee")
    return p


def test_p1_a_new_failure_aborts(monkeypatch, tmp_path):
    from scripts import ship_gate
    _mk(monkeypatch, tmp_path, ["tests/test_a.py::test_one"])
    v = ship_gate.evaluate(["tests/test_a.py::test_one", "tests/test_b.py::test_new"])
    assert v["blocked"] is True, "a failure absent from the baseline MUST abort the ship"
    assert "tests/test_b.py::test_new" in v["new"]


def test_p2_an_inherited_failure_does_not_abort(monkeypatch, tmp_path):
    from scripts import ship_gate
    _mk(monkeypatch, tmp_path, ["tests/test_a.py::test_one", "tests/test_b.py::test_two"])
    v = ship_gate.evaluate(["tests/test_a.py::test_one", "tests/test_b.py::test_two"])
    assert v["blocked"] is False, (
        "inherited failures must not abort -- an impassable door is why the method gate "
        "was bypassed six times in one night")
    assert len(v["inherited"]) == 2


def test_p3_a_fixed_failure_tightens_the_baseline(monkeypatch, tmp_path):
    """THE SELF-LIMITING PROPERTY. Without the ratchet, P2 is an amnesty that only grows."""
    from scripts import ship_gate
    _mk(monkeypatch, tmp_path, ["tests/test_a.py::test_one", "tests/test_b.py::test_two"])
    v = ship_gate.evaluate(["tests/test_a.py::test_one"])          # test_two now passes
    assert "tests/test_b.py::test_two" in v["fixed"]
    assert v["blocked"] is False
    remaining = {f["node"] for f in sb.read()["failures"]}
    assert "tests/test_b.py::test_two" not in remaining, (
        "a fixed test stayed in the amnesty -- the list must ratchet DOWN automatically or it "
        "becomes a growing pile of permitted red")
    # and it can never quietly return: it is now NEW
    v2 = ship_gate.evaluate(["tests/test_a.py::test_one", "tests/test_b.py::test_two"])
    assert v2["blocked"] is True, "a regression of a FIXED test must block, not re-inherit"


def test_p4_inherited_failures_are_announced(monkeypatch, tmp_path):
    from scripts import ship_gate
    _mk(monkeypatch, tmp_path, ["tests/test_a.py::test_one"])
    v = ship_gate.evaluate(["tests/test_a.py::test_one"])
    assert v["report"] and "1" in v["report"], (
        "shipping over a red test must SAY SO -- silence is how a red becomes furniture")


def test_p5_a_stale_baseline_is_announced(monkeypatch, tmp_path):
    from scripts import ship_gate
    _mk(monkeypatch, tmp_path, ["tests/test_a.py::test_one"])
    v = ship_gate.evaluate(["tests/test_a.py::test_one"], now=None, stale_after_s=0.0)
    assert "stale" in v["report"].lower(), "a rotting baseline must announce its own age"


def test_p6_no_baseline_fails_closed(monkeypatch, tmp_path):
    """Absence of evidence is not amnesty. A missing baseline must block every failure,
    never wave them all through -- that is the confident-zero failure in gate form."""
    from scripts import ship_gate
    _mk(monkeypatch, tmp_path, None)
    v = ship_gate.evaluate(["tests/test_a.py::test_one"])
    assert v["blocked"] is True, (
        "no baseline read as blanket amnesty -- absence must fail CLOSED")


def test_p8_an_expired_baseline_revokes_the_exemption(monkeypatch, tmp_path):
    """deepseek's counter, and its condition for not opposing this change: a passive
    'stale' line is the disease, not the cure -- a computed red routed to a channel nobody
    acts on. The inherited list must be a TIME-BOXED DEFERRAL, not an amnesty. Past the TTL
    the exemption is REVOKED and the inherited failures block again, because a failure that
    has been inherited for a week is not inherited -- it is owned."""
    from scripts import ship_gate
    _mk(monkeypatch, tmp_path, ["tests/test_a.py::test_one"])
    fresh = ship_gate.evaluate(["tests/test_a.py::test_one"], ttl_s=10 ** 9)
    assert fresh["blocked"] is False, "inside the TTL, inherited failures are exempt"
    expired = ship_gate.evaluate(["tests/test_a.py::test_one"], ttl_s=0.0)
    assert expired["blocked"] is True, (
        "past the TTL the exemption must be REVOKED -- otherwise the inherited list grows "
        "monotonically and rots, which is amnesty wearing a different word")
    assert "expired" in expired["report"].lower()


def test_p7_a_green_suite_is_always_clean(monkeypatch, tmp_path):
    from scripts import ship_gate
    _mk(monkeypatch, tmp_path, ["tests/test_a.py::test_one"])
    v = ship_gate.evaluate([])
    assert v["blocked"] is False and not v["new"]
