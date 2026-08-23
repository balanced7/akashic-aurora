"""
T382 -- revive.py, the reconciler: pins, RED-first.

The idempotency doctrine as law (revive-ladder plan, Daniil's safe-to-run
requirement): observe -> skip-if-healthy -> heal-only-the-dead -> verify,
dependency-ordered, no kills on the default path, single-flight.

  P1  IDEMPOTENT BY CONSTRUCTION: decide() over an all-healthy observation
      returns an EMPTY plan -- a revive of a healthy house does nothing.
  P2  PARTIAL: only the dead rung is planned; healthy upstreams untouched.
  P3  ORDER + GATING: redis heals before daemon; a rung whose DEPENDENCY is
      unhealthy is deferred (never spawn runners onto a dead substrate).
  P4  NO KILLS: no plan action on the default path ever contains
      kill/stop/restart -- the gentlest lever only (start/spawn).
  P5  SINGLE-FLIGHT: a second converge while the lock is held refuses
      loudly instead of racing.
  P6  STOP-ON-FAIL: when a heal's verify fails, downstream rungs are NOT
      attempted (the report says exactly where it stopped).

decide() is PURE (observation dict in, plan out) so these pins run without
touching a single live process. Run: py -m pytest tests/test_t382_revive.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.revive import decide, converge, ReviveLocked  # noqa: E402


def _obs(redis=True, daemon=True, runners=True, gateway=True):
    return {
        "redis":   {"healthy": redis,   "detail": "ping" if redis else "no ping"},
        "daemon":  {"healthy": daemon,  "detail": ""},
        "runners": {"healthy": runners, "detail": ""},
        "gateway": {"healthy": gateway, "detail": ""},
    }


def test_p1_healthy_house_empty_plan():
    assert decide(_obs()) == [], "a revive of a healthy house must plan NOTHING"


def test_p2_partial_only_the_dead_rung():
    plan = decide(_obs(daemon=False))
    organs = [p["organ"] for p in plan]
    assert organs == ["daemon"], f"only the dead rung may be planned: {organs}"


def test_p3_order_and_dependency_gating():
    plan = decide(_obs(redis=False, daemon=False))
    organs = [p["organ"] for p in plan]
    assert organs[0] == "redis", "the substrate heals first"
    assert "daemon" not in organs, (
        "a rung whose dependency is dead is DEFERRED to the next converge, "
        "never healed blind onto a dead substrate")


def test_p4_no_kills_on_default_path():
    plan = decide(_obs(redis=False, daemon=False, runners=False, gateway=False))
    for p in plan:
        joined = " ".join(str(x) for x in p.get("cmd", [])).lower()
        for forbidden in ("kill", "stop", "restart", "terminate"):
            assert forbidden not in joined, (
                f"default-path heal may only start/spawn, found {forbidden!r} "
                f"in {joined}")


def test_p5_single_flight(tmp_path, monkeypatch):
    import scripts.revive as rv
    monkeypatch.setattr(rv, "LOCK_PATH", str(tmp_path / "revive.lock"))
    monkeypatch.setattr(rv, "observe", lambda: _obs())
    report = converge(observe_only=True)
    assert report["plan"] == []
    with open(rv.LOCK_PATH, "w", encoding="utf-8") as f:
        f.write("99999999")                      # a holder that isn't us
    with pytest.raises(ReviveLocked):
        converge()


def test_p6_stop_on_fail(monkeypatch):
    import scripts.revive as rv
    monkeypatch.setattr(rv, "observe", lambda: _obs(redis=False, gateway=False))
    attempted = []

    def _fake_heal(step):
        attempted.append(step["organ"])
        return False                              # the heal fails

    monkeypatch.setattr(rv, "_heal_step", _fake_heal)
    monkeypatch.setattr(rv, "LOCK_PATH", str(rv.LOCK_PATH) + ".p6test")
    report = converge()
    assert attempted == ["redis"], (
        f"after a failed heal nothing downstream may be attempted: {attempted}")
    assert report["stopped_at"] == "redis"
    try:
        os.remove(rv.LOCK_PATH)
    except OSError:
        pass
