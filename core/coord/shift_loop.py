"""Autonomous shift loop — the missing cadence between existing primitives.

Design: docs/library/design/autonomous-shift-loop-design.md (fence: shift-loop).

This module is the SAFE, PURE, HERMETIC half of that design — the parts we can build and
pin tonight without touching a live runner's self-modification. It does NOT wire into the
runner turn boundary, does NOT self-restart, and does NOT claim on its own. It is:

  next_beat(state) -> action    the pure decision: given the ledger view + a shift note,
                                what is the next autonomous action? (claim / work / land /
                                handoff / idle / blocked)

  shiftstate read/write          the durable shift-state note (one title, supersedes on
                                re-write, idempotent across crash-redelivery)

Everything else in the design (wiring into the runner, cross-seat claim, restart dials)
is FENCED for morning — named here, not built here. Fail direction is keep-running/idle:
a decision function that cannot decide says "idle, nothing claimable" rather than
inventing work.

The claim is the mutex. Every actionable pick must surface as action='claim' with the
task id the CALLER then routes through TaskLedger.claim() — this module never claims
directly, it only DECIDES; the existing ledger claim gate stays the single door.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


# ---------------------------------------------------------------- shift-state note
# One durable title, supersedes on re-write. NOT append-only: "current shift state" is one
# thing, and fifty historical "shift-state" notes is how you get a re-orient instead of a
# continue. The note is a HYPOTHESIS (house rule: an assertion about live state is a
# hypothesis, not a fact) — the next waker verifies against the ledger before acting.
SHIFT_STATE_TITLE = "shift-state"

_DEFAULT_SHIFT_STATE: Dict[str, Any] = {
    "opened": "",            # "<who> @ <iso>"
    "claimed": "none",       # task id, or 'none'
    "landed": "nothing yet", # git sha, or 'nothing yet'
    "handoff_for": "any",    # next-waker agent, or 'any'
    "context": "",           # <3 lines: what to continue, what NOT to redo
    "cadence_note": "",      # why this beat ended here
}


def new_shift_state(**overrides) -> Dict[str, Any]:
    """A fresh shift-state note body (a dict; the caller serializes it via its own note door)."""
    out = dict(_DEFAULT_SHIFT_STATE)
    out.update({k: v for k, v in overrides.items() if k in _DEFAULT_SHIFT_STATE})
    return out


def shift_state_is_complete(s: Dict[str, Any]) -> bool:
    """A handoff is complete when it names a claim/state AND gives the next waker a reason
    to continue (context or a cadence note). A bare `{}` is a non-handoff."""
    if not s or not s.get("opened"):
        return False
    return bool(s.get("context") or s.get("cadence_note"))


# ---------------------------------------------------------------- the pure decision core
# Every input is passed in, so the pins need no ledger, no Redis, no clock, no git. The
# caller gathers the real state; this function only decides. Fail direction: idle.

def next_beat(*, statuses: Dict[str, str], files_held_by_other: bool = False,
              deps_done: bool = True, current_task_done: bool = True,
              stale_behind: int = 0, stale_min: int = 3,
              uptime_s: float = 0.0, uptime_min: float = 900.0):
    """Decide the next autonomous action from a REDUCED view.

    Returns a dict:
      action: 'claim' | 'work' | 'land' | 'handoff' | 'restart' | 'idle' | 'blocked'
      task:   the task id the action is about (when applicable)
      reason: a short, human-readable why (always present — a decision nobody can explain
              is a crash with better manners).

    The reduced view is deliberately small so the caller can gather it cheaply from
    state_view() without loading the whole ledger. statuses maps task_id -> status."""
    # restarts are only ever at a boundary with nothing in flight (the caller passes
    # current_task_done=False when something is mid-flight).
    if current_task_done and 0 < stale_min <= stale_behind and uptime_s >= uptime_min:
        return {"action": "restart", "task": None,
                "reason": f"stale-code: {stale_behind} commits behind, idle, uptime {int(uptime_s)}s"}

    # claimable = APPROVED with deps done and files free; the ledger's own claim() gate is
    # the real mutex — here we only decide WHAT to try.
    claimable = [tid for tid, st in statuses.items() if st == "approved"]
    if claimable:
        if not deps_done:
            return {"action": "blocked", "task": claimable[0],
                    "reason": "a task is APPROVED but its deps are not DONE — cannot claim yet"}
        if files_held_by_other:
            return {"action": "blocked", "task": claimable[0],
                    "reason": "a task is APPROVED but its files are held by another active task"}

    # something is mid-claim/mid-work and not done -> keep working it
    active = [tid for tid, st in statuses.items() if st in ("claimed", "in_progress", "verifying")]
    if active and not current_task_done:
        return {"action": "work", "task": active[0],
                "reason": f"task {active[0]} is active — continue the work"}

    # active but done working -> land it (commit + verify)
    if active and current_task_done:
        return {"action": "land", "task": active[0],
                "reason": f"task {active[0]} is done working — commit and move toward DONE"}

    # claimable and nothing blocking -> claim it
    if claimable:
        return {"action": "claim", "task": claimable[0],
                "reason": f"task {claimable[0]} is APPROVED with deps done and files free — claim it"}

    # nothing claimable and nothing active -> emit a handoff and idle (a valid beat)
    return {"action": "idle", "task": None,
            "reason": "nothing claimable and nothing active — honest idle (not a failure)"}


__all__ = [
    "SHIFT_STATE_TITLE", "new_shift_state", "shift_state_is_complete", "next_beat",
]
