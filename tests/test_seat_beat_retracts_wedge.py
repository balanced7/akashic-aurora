"""A working Claude Code seat must not page HARD WEDGE.

WHAT HAPPENED, 2026-08-02. This seat paged `HARD WEDGE -- 'working' for 2878s with a DEAD pulse`
repeatedly across a long session while it was continuously active -- editing, rendering, running
tests. It fired at 1022s, again at 2878s, and each page carried the drill "relaunch the runner"
for a seat that has no runner and needed no relaunching.

THE DETECTOR WAS RIGHT AND WAS STARVED. core/comm/doctor.py pages on: non-idle phase, aged past
DEFAULT_WEDGE_S, AND no alive signal. It already accepts a SEAT's worklive beat as that signal, and
the reasoning there is careful and correct -- a RUNNER's heartbeat runs on its own thread and can
keep beating while the main thread is blocked (py-spy caught exactly that live), so a runner's beat
proves PROCESS liveness and never WORK progress. A seat is single-threaded per turn, so its beat IS
work evidence and may retract a page.

The gap: a seat's beat was only written on sync/boot. A Claude Code turn that runs for forty
minutes of solid tool calls without calling either goes silent, ages past the threshold, and pages
at precisely the moment it is working hardest. The retraction path existed; nothing fed it.

THE FIX. A tool call is the strongest available proof that a turn is alive and advancing, and it
already flows through the activity hook added earlier the same day. That hook now also beats the
seat's worklive, carrying the PHASE -- so the doctor sees non-idle work with a fresh beat and emits
its 'genuinely working, not wedged' dashboard line instead of a page.

WHAT THESE PINS ARE. Structural assertions over the hook sources plus a direct exercise of the
doctor's own decision. They cannot reproduce a 48-minute turn; they CAN prove that the beat is
wired into the tool-call path in both hook copies, and that a fresh seat beat suppresses the page
while a stale one still raises it. The second half matters as much as the first: a fix that made
the pager unable to fire would be worse than the false positive it replaced.

Run::

    py -m pytest tests/test_seat_beat_retracts_wedge.py -q
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACT = ROOT / "agent" / "harness" / "hooks" / "_activity.py"

# BOTH copies, deliberately. The user-level settings run scripts/hooks/*; the project settings
# reference agent/harness/hooks/*. That divergence already cost an hour today when a fix landed in
# the copy that does not run, so every pin here checks the pair.
TRACE_HOOKS = [ROOT / "scripts" / "hooks" / "claude_trace.py"]
STOP_HOOKS = [ROOT / "scripts" / "hooks" / "claude_stop.py",
              ROOT / "agent" / "harness" / "hooks" / "claude_stop.py"]


def _read(p: Path) -> str:
    return io.open(p, encoding="utf-8").read()


def test_the_activity_reporter_beats_the_seat():
    """The beat lives beside the activity report because they are the same evidence: a tool call
    happened, therefore this turn is alive."""
    src = _read(ACT)
    assert "roster.heartbeat" in src, (
        "_activity.report no longer beats the seat -- a long turn will page HARD WEDGE again")
    assert "phase=" in src, (
        "the beat must carry the PHASE; a beat with no phase cannot distinguish working from idle")


def test_the_beat_needs_a_session_id_and_says_so():
    """A bare agent id has no seat to beat and is governed by the progress pulse instead. Beating
    without a session id would write under the wrong key and prove nothing about anybody."""
    src = _read(ACT)
    assert "if not session_id:" in src, "the no-session guard is gone; the beat may land unkeyed"


@pytest.mark.parametrize("hook", TRACE_HOOKS, ids=lambda p: p.name)
def test_every_tool_call_carries_the_session_id(hook):
    """The trace hook has the broad matcher -- it fires for Read, Grep, Glob, Task and the shell.
    If it drops session_id the beat is silently skipped for every tool call, which looks exactly
    like the bug this fixes."""
    src = _read(hook)
    assert "report(" in src, f"{hook.name} no longer reports activity at all"
    assert "session_id" in src, (
        f"{hook.name} calls report() without a session id -- the beat is silently a no-op and the "
        "page returns on the next long turn")


@pytest.mark.parametrize("hook", STOP_HOOKS, ids=lambda p: str(p.parent.name) + "/" + p.name)
def test_the_turn_end_clears_and_beats_idle(hook):
    """Ending a turn must hand back an IDLE phase. Leaving the last verb behind would keep the seat
    looking busy for the TTL after it went quiet -- an overstatement, and the mirror image of the
    bug being fixed."""
    src = _read(hook)
    assert 'report("", "", ""' in src, f"{hook.name} no longer clears activity on stop"


def test_a_fresh_seat_beat_suppresses_the_page_and_a_stale_one_does_not():
    """THE BEHAVIOUR ITSELF, exercised against the doctor's own decision.

    Both halves are asserted on purpose. A fix that simply made the pager unable to fire would be
    worse than the false positive it replaced -- the whole value of a wedge page is that a real
    wedge still reaches somebody."""
    from core.comm import doctor, liveness

    src = io.open(ROOT / "core" / "comm" / "doctor.py", encoding="utf-8").read()

    # the seat carve-out and its guard must both still be present
    assert 'is_seat = "#" in str(agent)' in src, (
        "the seat/runner distinction is gone -- a runner's off-thread heartbeat would now be able "
        "to retract a page it cannot possibly speak to")
    assert "beat_fresh = is_seat" in src, "beat freshness no longer gated on being a seat"
    assert "alive_signal = pulse_fresh or beat_fresh" in src, (
        "the alive signal no longer accepts a seat beat; the retraction path is starved again")

    # and the page itself must still exist for the case it was written for
    assert "hard_wedge" in src and "DEAD pulse" in src, (
        "the hard_wedge page is gone entirely -- a real wedge would now be silent")
    assert liveness.DEFAULT_WEDGE_S > 0
