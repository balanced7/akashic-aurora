"""The awareness snapshot: bus, bench, health and what moved, in one bounded block.

`sweep` is the verb a seat reaches for on arrival, before it knows what is true. Read-only,
fail-open, deterministic, and explicit about the observed subject -- the subject is required
(argument or env) rather than guessed, because a snapshot that silently reports on the wrong
seat is worse than no snapshot.
"""
from __future__ import annotations

import json
import os

from verbs.registry import verb


def _awareness_subject(args) -> str:
    explicit = str(getattr(args, "agent_id", "") or "").strip()
    inherited = str(os.environ.get("AKASHIC_AGENT_ID", "") or "").strip()
    subject = explicit or inherited
    if not subject:
        raise ValueError(
            "awareness subject is required: pass `sweep <agent_id>` or set "
            "AKASHIC_AGENT_ID"
        )
    return subject

@verb(local=False, door_notes="CLI only; reads core.comm.awareness. `build_sweep` (the render helper, also imported by tests/test_sweep_verb.py) deliberately STAYS in the door script.")
def cmd_sweep(args):
    """`sweep`: the awareness snapshot -- bus, bench, health, moved in one bounded block.
    Read-only, fail-open, deterministic, and explicit about the observed subject."""
    try:
        subject = _awareness_subject(args)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    from core.comm.awareness import build_snapshot
    snapshot = build_snapshot(subject)
    if getattr(args, "json", False):
        print(json.dumps(snapshot.as_dict(), indent=2, default=str))
    else:
        from core.comm.awareness import render_snapshot
        print(render_snapshot(snapshot))
    return 0
