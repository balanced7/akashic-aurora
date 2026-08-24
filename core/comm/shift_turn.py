"""The runner turn boundary: one shared decision per loop top, for every runner.

WHY THIS MODULE EXISTS RATHER THAN FOUR BLOCKS. maybe_self_restart is called at the loop
top of four runners (deepseek, gemini, kimi, sol). Pasting a next_beat + shiftstate block
beside each would be the FIFTH copy of orchestration in this repo, which is precisely the
mistake the t383 extraction spent a night undoing -- four is past the rule of three before
anyone starts. So the decision lives here once and each runner carries a single call, and
tests/test_shift_turn_boundary.py fails if a runner grows its own copy or reaches for
next_beat directly.

THE BLAST RADIUS, and why this file is so defensive. Every runner in the fleet executes
this at the top of every turn. An exception escaping here does not break one seat, it
wedges all of them simultaneously -- the single worst failure shape available in this
system. So every path returns a decision dict and nothing raises: a dead ledger, a
malformed view, the decision core itself blowing up, a garbage agent id. Idle is always a
safe answer at a turn boundary; an exception never is.

IDLE IS A RESULT, NOT A FAILURE. next_beat says idle when nothing is claimable, and that
is the correct, common answer. This module never invents work to look busy.

KILL SWITCH: AKASHIC_SHIFT_LOOP=0 takes the autonomous loop out of every runner at once
with no code change -- same discipline as the recall kill switches, and the thing you
reach for at 3am when the loop is doing something you did not intend.
"""
import os
from typing import Any, Dict, Optional

_OFF = {"action": "idle", "task": None,
        "reason": "shift loop disabled (AKASHIC_SHIFT_LOOP=0)"}


def _idle(reason: str) -> Dict[str, Any]:
    return {"action": "idle", "task": None, "reason": reason}


def _statuses() -> Dict[str, str]:
    """The reduced view next_beat needs: {task_id: status}. Reads the git-durable ledger,
    same source the shift daemon uses -- deliberately NOT a second gather implementation."""
    from core.coord import task_ledger as TL
    view = TL.state_view(client=None)
    return {t["id"]: t["status"] for t in
            (view["done"] + view["in_progress"] + view["next"]
             + view["proposed"] + view["blocked"] + view["parked"])}


def turn_beat(agent: Any, statuses: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """One autonomous decision for this turn. Never raises; always returns a decision.

    `statuses` is injectable so a caller (or a pin) can supply the view; when omitted it
    is read from the durable ledger. The return is next_beat's own dict --
    {action, task, reason} -- so the runner can render the reason verbatim, which is what
    makes an autonomous decision auditable rather than mysterious.
    """
    if os.getenv("AKASHIC_SHIFT_LOOP", "1") == "0":
        return dict(_OFF)
    try:
        aid = str(agent).strip() if agent else ""
        if not aid:
            return _idle("no agent id at the turn boundary -- idle (fail-closed)")
        if statuses is None:
            try:
                statuses = _statuses()
            except Exception as e:                                      # noqa: BLE001
                return _idle(f"ledger unavailable ({type(e).__name__}) -- idle (keep-running)")
        from core.coord import shift_loop
        decision = shift_loop.next_beat(statuses=statuses or {})
        if not isinstance(decision, dict) or "action" not in decision:
            return _idle("decision core returned an unusable shape -- idle (fail-closed)")
        return decision
    except Exception as e:                                              # noqa: BLE001
        # THE PIN THAT MATTERS: whatever went wrong, four runners keep turning.
        return _idle(f"turn boundary error ({type(e).__name__}) -- idle (fail-closed)")
