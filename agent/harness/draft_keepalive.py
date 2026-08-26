"""draft_keepalive -- make the auto-handoff survive an UNGRACEFUL death.

THE GAP, found 2026-08-24. `chronicles/last-session-draft.md` is the house's auto-handoff:
it captures commits, lessons and notes so the next seat boots with a where-we-are instead
of a blank page. It is written by `scripts/hooks/claude_sessionend.py`, wired to SessionEnd
and PreCompact.

Both of those are GRACEFUL exits.

At 12:01:59 the conductor's Electron GPU process crashed. No SessionEnd fired, no PreCompact
fired, and no draft was written. The draft on disk afterwards is stamped 14:46:12 -- from a
session that ended cleanly AFTER the recovery. The seats that had to reconstruct the outage
did it from raw logs, because the handoff mechanism is bolted to the one path a crash never
takes.

That is the day's shape once more: the safety net attached to the happy path. `!spawn`
reported life and not work; the ladder began above the layer that died; the gate went quiet
in a way that could not be told from not running. And the handoff fires only when the seat
was well enough to say goodbye.

WHAT THIS MODULE IS. The throttle decision, as a pure function, plus a never-raising wrapper.
WIRED 2026-08-26 (Rill) at TWO turn boundaries: the Stop hook (scripts/hooks/claude_stop.py,
the live registered copy) for claude seats, and the DSH turn seam (dsh_plugin/bridge.py
`draft-keepalive` subcommand, fired fire-and-forget from tools/post-execute) for the dsh
seat. Both seams INJECT the one existing builder as the write closure -- this module owns
no second way to build a draft. Built ahead like the conductor gate (built 3431118a, wired
5c09bb5a): the throttle sat unwired for two days while the wiring waited for a seat with
room to think.

WHY A THROTTLE AT ALL. The draft gather reads the transcript and the ledger. Doing that on
every turn would put real work in a hot path that must stay nearly free -- the
renew_two_birds_bus_recorder lesson ("don't touch the hook hot path"). So the common case
here is a single `os.path.getmtime` and an early return.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Optional

#: How stale the draft may get before a turn boundary refreshes it. Ten minutes bounds
#: what an ungraceful death can destroy, while leaving the overwhelming majority of turns
#: doing nothing but one stat() call.
DEFAULT_MAX_AGE_S = 600.0

#: Kill switch, same discipline as AKASHIC_SHIFT_LOOP -- the thing you reach for at 3am
#: when a keepalive is doing something you did not intend.
ENV_OFF = "AKASHIC_DRAFT_KEEPALIVE"
ENV_MAX_AGE = "AKASHIC_DRAFT_MAX_AGE_S"


def enabled() -> bool:
    return os.environ.get(ENV_OFF, "1") != "0"


def max_age_s() -> float:
    try:
        v = float(os.environ.get(ENV_MAX_AGE) or DEFAULT_MAX_AGE_S)
        return v if v > 0 else DEFAULT_MAX_AGE_S
    except (TypeError, ValueError):
        return DEFAULT_MAX_AGE_S


def should_refresh(path: str, *, now: Optional[float] = None,
                   max_age: Optional[float] = None,
                   getmtime: Callable[[str], float] = os.path.getmtime,
                   exists: Callable[[str], bool] = os.path.isfile) -> bool:
    """Is the draft stale enough to be worth rewriting? PURE, with the two filesystem
    calls injected so a pin can drive it without touching a clock or a disk.

    MISSING COUNTS AS STALE. A draft that does not exist is the worst case, not a
    reason to skip -- that is the state a crashed session leaves behind, and the whole
    point of this module is that the state exists BEFORE the crash.

    AN UNREADABLE MTIME COUNTS AS STALE TOO. Fail toward writing: the cost of an extra
    draft is one file; the cost of a skipped one is the next seat booting blind.
    """
    if not enabled():
        return False
    limit = max_age if max_age is not None else max_age_s()
    t = now if now is not None else time.time()
    try:
        if not exists(path):
            return True                 # missing == maximally stale
        return (t - getmtime(path)) >= limit
    except Exception:                                                   # noqa: BLE001
        return True                     # unreadable == stale; fail toward writing


def refresh(path: str, *, write: Callable[[], Any],
            now: Optional[float] = None,
            max_age: Optional[float] = None,
            **probe) -> Dict[str, Any]:
    """Refresh the draft if it is stale. NEVER RAISES.

    `write` is the caller's zero-arg draft writer (in production, the same
    agent_cli.write_last_session_draft path the SessionEnd hook already uses -- this
    module deliberately owns no second way to build a draft).

    Returns {"wrote": bool, "reason": str} so a caller can log ONE auditable line, and so
    a skip is a stated decision rather than silence -- the distinction this whole day was
    spent on.
    """
    try:
        if not enabled():
            return {"wrote": False, "reason": f"disabled ({ENV_OFF}=0)"}
        if not should_refresh(path, now=now, max_age=max_age, **probe):
            return {"wrote": False, "reason": "draft is fresh -- nothing to do"}
        write()
        return {"wrote": True, "reason": "draft was stale; rewritten at the turn boundary"}
    except Exception as e:                                              # noqa: BLE001
        # A keepalive that can raise into a hook is worse than no keepalive: it would
        # wedge every seat in the fleet to protect against one seat's crash.
        return {"wrote": False, "reason": f"refresh failed ({type(e).__name__}: "
                                          f"{str(e)[:80]}) -- keeping the turn alive"}
