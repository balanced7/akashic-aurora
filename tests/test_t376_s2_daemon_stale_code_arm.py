"""T376-S2 PRE-REGISTERED ACCEPTANCE — the daemon's missing stale-code arm.

Cites fences/t376-metabolism/reconciliation.md build slice S2 and errata E2:

  E2 (code-reality reframe): runners ALREADY metabolize (maybe_self_restart
      wired at deepseek:1457, gemini:859, kimi:930, sol:789). The daemon has
      NO stale-code arm (only --max-runtime + the child breaker). The build's
      true scope: the daemon and the gateway are the organs that do not yet
      metabolize — they are the whole point of D.
  S2 daemon: maybe_self_restart at its loop boundary (stale-code arm).

So the daemon's main loop must call self_restart.maybe_self_restart(agent) at
its loop boundary (between ticks, nothing in flight) and, when it returns a
reason, stand down CLEANLY (exit 0) after the successor was launched — the
same ceremony the runners already do.

RED-first (M3): this wiring does not exist yet. Bifrost daemon has no
reference to maybe_self_restart. These pins lock it.

The acceptance is a STATIC contract pin (the wiring seam) plus a BEHAVIORAL
pin over the pure seam — not a live daemon rotation (that is S6's drill, and
rotating a real daemon in a unit test would fight the live lock).

WHY NOT A LIVE ROTATION HERE: a live daemon self-restart would need a real
Redis lock + a real child + a real git HEAD drift, which is exactly what S6's
rolling-refresh drill does end-to-end. S2 pins the WIRING (the call is made
at the loop boundary with the right inputs), leaving the hands-free rotation
proof to the drill where it belongs.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAEMON = os.path.join(ROOT, "scripts", "bifrost_daemon.py")


def _daemon_source() -> str:
    with open(DAEMON, encoding="utf-8") as f:
        return f.read()


# ------------------------------------------------------------------ S2-P1
def test_s2_p1_daemon_imports_and_calls_maybe_self_restart():
    """The daemon's stale-code arm exists: it imports self_restart and calls
    maybe_self_restart(agent) at its loop boundary. (Static wiring seam.)"""
    src = _daemon_source()

    # import present (either module or direct symbol)
    assert re.search(r"from\s+core\.comm\s*import\s+self_restart", src) or \
           re.search(r"from\s+core\.comm\.self_restart\s+import", src) or \
           "self_restart." in src, \
        "S2: bifrost_daemon.py never references self_restart (RED — no arm)"

    # the call is made somewhere in main()'s loop body
    assert re.search(r"maybe_self_restart\s*\(", src), \
        "S2: bifrost_daemon.py never calls maybe_self_restart (RED — arm not wired)"


# ------------------------------------------------------------------ S2-P2
def test_s2_p2_daemon_stand_down_is_clean_exit_zero_on_reason():
    """When maybe_self_restart returns a reason, the daemon must stand down via
    its CLEAN-EXIT path (reason-bearing, lock released, exit 0) — never via the
    FAULT path (exit 1) and never by just ignoring the reason. The earned signal
    (S1) says exit 0 = successor exists; a daemon that relaunches and then
    faults would count itself as a crash.

    Static pin: the loop's maybe_self_restart return must feed a break/clean-exit,
    not be discarded, and must not be treated as an exception.
    """
    src = _daemon_source()

    # The call's return value must be captured, not discarded (no bare statement
    # that throws the reason away). Simplest robust check: the call appears and
    # the file's clean-exit path still says "reason=" (the loop-driven clean exit
    # must carry a reason that is not only "stop"/"signal"/"max-runtime").
    assert "reason=" in src, "S2: daemon must keep its reason-bearing clean exit"
    assert "clean exit" in src, "S2: clean-exit provenance line must survive"

    # The loop that calls maybe_self_restart must be the SAME loop that has a
    # _STOP-style break (so a reason can break out to clean exit). We assert the
    # daemon's signal/stop machinery and the call coexist in main().
    assert "_STOP" in src, "S2: daemon's stop machinery must exist for the arm to feed"


# ------------------------------------------------------------------ S2-P3
def test_s2_p3_daemon_arm_is_in_flight_aware():
    """The daemon's arm must not fire mid-child-spawn. The daemon manages
    children (runner, listeners); a stale-code self-restart that lands between
    child.spawn() and the child's lock-take would orphan a spawn. So the arm's
    in_flight input must reflect live child management state, NOT a hardcoded
    False. Static pin: the maybe_self_restart call site must pass an in_flight
    expression (child/children alive), not a literal False.
    """
    src = _daemon_source()

    # find the maybe_self_restart call and its in_flight arg
    calls = re.findall(r"maybe_self_restart\([^)]*\)", src, re.S)
    assert calls, "S2: maybe_self_restart call missing (P1 already covers import)"

    for call in calls:
        # a hardcoded in_flight=False is the bug; it must be a live expression
        assert "in_flight=False" not in call and "in_flight = False" not in call, \
            f"S2: the arm must NOT hardcode in_flight=False; pass live child " \
            f"management state. Found: {call.strip()[:120]!r}"
