#!/usr/bin/env python3
"""Report what the claude seat is doing, so the console can SEE it.

WHY THIS EXISTS. core/comm/control.set_activity is what fills /status activities, and the UI maps
that onto the agent avatar's state codebook -- colour, spin, subdivision, breathing. The codebook
has been complete for a while and was never once exercised for claude, because set_activity is
called only from the RUNNER path (bifrost_runner_deepseek/kimi/sol on_activity callbacks). claude
runs inside Claude Code, which has no runner, so it reported nothing and its avatar sat on the
fallback state forever. Daniil asked why the avatar does not change colour when the AI is
thinking; the answer was that nothing had ever told it anyone was thinking.

THE SHAPE OF THE SIGNAL, and it is a genuinely good fit for the hook points that already exist.
A tool call is EXTERNAL work and the model is not generating during it; the gap between one tool
returning and the next starting is INTERNAL work -- generating. So:

    PreToolUse  -> the verb for that tool   (reading / searching / writing / running)
    PostToolUse -> thinking                 (the tool is done; the model is composing again)
    Stop        -> cleared                  (turn over)

which oscillates exactly the way the avatar wants, with no polling and no new process.

SAFETY, because PreToolUse can DENY a tool call and a fault here would break the agent's own
hands. Everything is fail-open and side-effect-only: any exception is swallowed, the caller
ignores the return, and a scope check keeps it silent outside this repo. set_activity carries a
25s TTL of its own (control.ACTIVITY_TTL), so a seat that dies mid-turn expires rather than
leaving the console asserting work that stopped -- the failure mode is going quiet, never lying.
"""
from __future__ import annotations

import os

# Tool name -> the vocabulary control.py documents and the UI's AV_STATE already maps. Anything
# unrecognised falls to 'working' rather than being dropped: an unmapped tool still means the
# seat is busy, and silence would render as idle, which is a wrong claim rather than a vague one.
_VERB = {
    "Read": "reading", "NotebookRead": "reading",
    "Grep": "searching", "Glob": "searching", "WebSearch": "searching", "WebFetch": "reading",
    "Edit": "writing", "Write": "writing", "NotebookEdit": "writing",
    "Bash": "running", "PowerShell": "running",
    "Task": "working", "Agent": "working",
}


def verb_for(tool: str) -> str:
    return _VERB.get(tool or "", "working")


def report(state: str, detail: str = "", cwd: str = "", session_id: str = "") -> None:
    """Best-effort. Never raises, never blocks the caller's decision, never speaks out of scope."""
    try:
        from agent.harness.scope import session_in_scope
        if not session_in_scope(cwd or os.getcwd()):
            return
        agent = os.getenv("AKASHIC_AGENT_ID") or "claude"
        from core.comm import control
        if state:
            control.set_activity(agent, state, detail)
        else:
            control.clear_activity(agent)
        _beat_seat(agent, state, session_id)
    except Exception:
        pass


def _beat_seat(agent: str, state: str, session_id: str) -> None:
    """Beat this SEAT's worklive, because a tool call is the strongest possible proof of work.

    WHY THIS EXISTS. core/comm/doctor.py pages hard_wedge on: non-idle phase, aged past threshold,
    AND no alive signal. It accepts a SEAT's worklive beat as that signal -- deliberately, and the
    reasoning there is careful: a RUNNER's heartbeat runs on its own thread and can keep beating
    while the main thread is blocked, so it proves process liveness and never work progress. A seat
    is single-threaded per turn, so its beat IS work evidence.

    The gap was that a seat's beat was only written on sync/boot. A Claude Code turn that runs for
    forty minutes of solid tool calls without calling either goes silent, ages past the threshold,
    and pages HARD WEDGE at exactly the moment it is working hardest. That fired repeatedly today
    while this seat was continuously active.

    A tool call is the ideal beat: it cannot happen unless the turn is alive and advancing, it
    already flows through this hook, and it carries the PHASE, so the doctor sees non-idle work
    with a fresh beat and emits its 'genuinely working, not wedged' dashboard line instead of a
    page. The retraction path already existed -- it was starved of input, not missing.

    Fail-open and silent: a seat that cannot beat is exactly the seat the pager should still be
    able to page.
    """
    if not session_id:
        return                      # no seat identity to beat; a bare agent id is governed by the
                                    # progress pulse instead, which is the doctor's own fallback
    try:
        from core.comm import roster
        ns = os.getenv("BIFROST_NAMESPACE") or "bifrost"
        roster.heartbeat(ns, agent, session_id, phase=(state or "idle"))
    except Exception:
        pass
