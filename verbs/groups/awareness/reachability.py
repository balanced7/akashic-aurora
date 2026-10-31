"""reachability -- one screen: is this seat reachable, and by which path? (READ-ONLY)

The verb is a door, not a body: the gathering lives in `core.comm.reachability` so a test can
call it without a parser, and the render lives there too so a second surface (a future MCP twin
or `doctor`) cannot grow a divergent second answer.

The 2026-10-30 wish, verbatim from docs/WISHLIST.md (phase 3 of the modular-core detangle):

    "`reachability` verb: one command for gateway alive + its REAL log path (prod worktree),
     this seat's listener armed, who holds the consumer seat, last inbound/outbound to the
     operator, phone tunnel up. Today it took about 10 commands across two worktrees."

TWO INSTRUCTIONS THAT COME OFF THE WISH AND BECOME CODE HERE:

  * the log path is the GATEWAY'S, not this checkout's -- `core.comm.reachability.gateway()`
    resolves it from the process's working directory and marks a guess as UNKNOWN rather than
    printing a path that merely looks plausible;
  * the subject is REQUIRED, not guessed. A diagnostic that silently reports on the wrong seat
    is worse than no diagnostic (the `sweep` verb's rule, kept here).
"""
from __future__ import annotations

import json
import os

from verbs.registry import verb


def _reachability_subject(args) -> str:
    explicit = str(getattr(args, "agent_id", "") or "").strip()
    inherited = str(os.environ.get("AKASHIC_AGENT_ID", "") or "").strip()
    subject = explicit or inherited
    if not subject:
        raise ValueError(
            "reachability subject is required: pass `reachability <agent_id>` or set "
            "AKASHIC_AGENT_ID -- a reachability screen that silently observes the wrong seat "
            "is worse than none")
    return subject


def _ambient_session() -> str:
    try:
        from core.coord.session_id import ambient_session_id
        sid, _why = ambient_session_id()
        return str(sid or "")
    except Exception:
        return ""


@verb(local=False,
      door_notes="CLI only, read-only. No MCP twin on purpose: it enumerates processes and "
                 "reads other seats' mail streams, which is operator-diagnostic territory "
                 "(the door that a model calls should not be the door that watches the room).")
def cmd_reachability(args):
    """`reachability`: gateway (row + REAL log), this seat's wake listener, the consumer seat,
    the last operator exchange, and the phone tunnel -- one read-only screen, `--json` too."""
    from core.comm import reachability as _r
    try:
        subject = _reachability_subject(args)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    session = str(getattr(args, "session", "") or "").strip() or _ambient_session()
    rep = _r.report(subject, session, phone=not getattr(args, "no_phone", False))
    if getattr(args, "json", False):
        print(json.dumps(rep, indent=2, default=str))
    else:
        print(_r.render(rep))
    return 0
