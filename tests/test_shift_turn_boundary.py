"""RED-first pins for the runner turn boundary (t384/shift-loop step 2).

THE SEAM RULING (claude to deepseek, bus 1787573055226-0): maybe_self_restart is called
at the loop top of FOUR runners -- deepseek, gemini, kimi, sol. Adding a next_beat block
beside each would be a FIFTH copy of orchestration, which is the mistake the t383
extraction spent a night undoing. So: ONE shared function, FOUR one-line calls, and
check_wiring can then enforce that every runner calls it.

THE HARD CONSTRAINT: this runs at the top of every runner's loop. A turn boundary that
can raise can wedge EVERY RUNNER IN THE FLEET AT ONCE -- the one blast radius worth
being paranoid about. So it fails closed to idle on anything: a broken ledger, an import
error, a malformed decision. Silence is always a safe answer here; an exception never is.

Run: py -m pytest tests/test_shift_turn_boundary.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_returns_a_steer_when_there_is_work():
    from core.comm.shift_turn import turn_beat
    out = turn_beat("claude", statuses={"T1": "verifying"})
    assert isinstance(out, dict)
    assert out.get("action") in ("claim", "work", "land", "handoff", "restart", "idle", "blocked")


def test_idle_when_nothing_is_claimable():
    """idle is a RESULT, not a failure -- the loop must be able to say 'nothing to do'."""
    from core.comm.shift_turn import turn_beat
    out = turn_beat("claude", statuses={})
    assert out["action"] in ("idle", "blocked"), out


def test_fails_closed_to_idle_when_the_ledger_raises():
    """A broken ledger must not propagate into a runner's loop top."""
    from core.comm import shift_turn
    def _boom(*a, **k):
        raise RuntimeError("ledger down")
    orig = shift_turn._statuses
    shift_turn._statuses = _boom
    try:
        out = shift_turn.turn_beat("claude")
        assert out["action"] == "idle", out
        assert "ledger" in out["reason"].lower() or "unavailable" in out["reason"].lower()
    finally:
        shift_turn._statuses = orig


def test_fails_closed_to_idle_when_the_decision_core_raises():
    """THE BLAST-RADIUS PIN: next_beat itself blowing up must not wedge four runners."""
    from core.comm import shift_turn
    import core.coord.shift_loop as sl
    orig = sl.next_beat
    sl.next_beat = lambda **k: (_ for _ in ()).throw(ValueError("bad view"))
    try:
        out = shift_turn.turn_beat("claude", statuses={"T1": "verifying"})
        assert out["action"] == "idle", out
    finally:
        sl.next_beat = orig


def test_never_raises_on_a_garbage_agent():
    from core.comm.shift_turn import turn_beat
    for bad in (None, "", 12345, {"not": "an id"}):
        out = turn_beat(bad, statuses={})
        assert out["action"] in ("idle", "blocked"), (bad, out)


def test_kill_switch_silences_it_entirely():
    """One env var must be able to take the whole autonomous loop out of every runner
    without a code change -- the same discipline as the recall kill switches."""
    from core.comm.shift_turn import turn_beat
    os.environ["AKASHIC_SHIFT_LOOP"] = "0"
    try:
        out = turn_beat("claude", statuses={"T1": "verifying"})
        assert out["action"] == "idle"
        assert "off" in out["reason"].lower() or "disabled" in out["reason"].lower()
    finally:
        os.environ.pop("AKASHIC_SHIFT_LOOP", None)


def test_all_four_runners_call_the_shared_function_not_a_copy():
    """The rule-of-three enforcement: four call sites, one implementation. If a runner
    grows its own next_beat block, this fails and points at the copy."""
    import io
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runners = ["bifrost_runner_deepseek.py", "bifrost_runner_gemini.py",
               "bifrost_runner_kimi.py", "bifrost_runner_sol.py"]
    missing, copied = [], []
    for r in runners:
        p = os.path.join(root, "scripts", r)
        if not os.path.exists(p):
            continue
        src = io.open(p, encoding="utf-8").read()
        if "turn_beat" not in src:
            missing.append(r)
        if "next_beat(" in src:            # a runner must never call the core directly
            copied.append(r)
    assert not missing, f"runners not wired to the shared turn boundary: {missing}"
    assert not copied, f"runners calling next_beat directly (a 5th copy): {copied}"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
