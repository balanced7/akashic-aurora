"""The scene verbs: what a seat can SEE without changing anything.

`cmd_orient` is the detangle's own mascot: the 2026-09-17 house brief named it as the sync casualty
(the `-110` deletion in a fork's tree) because a fork had to edit it for reasons of its own. It
is also the smallest body in the pilot -- 25 lines, two stdlib names, one `core.coord` import --
which is exactly why it goes first: the migration rail gets proven on the cheapest real case
before ten more bodies ride it.
"""
from __future__ import annotations

import json
import os

from verbs.registry import verb


@verb(local=False, door_notes="CLI only; reads core.coord.orient. Subject comes from --agent or "
                              "AKASHIC_AGENT_ID (env, so no seat name is hardcoded here).")
def cmd_orient(args):
    """Compose awareness and typed focus into one renderer-neutral scene."""
    subject = str(getattr(args, "agent", "") or
                  os.environ.get("AKASHIC_AGENT_ID", "") or "").strip()
    if not subject:
        print("ERROR: orient subject is required: pass --agent <id> or set "
              "AKASHIC_AGENT_ID")
        return 2
    try:
        from core.coord.orient import build_orientation, render_orientation
        scene = build_orientation(
            subject,
            str(getattr(args, "target", "") or ""),
            density=str(getattr(args, "density", "compact") or "compact"),
            depth=str(getattr(args, "depth", "surface") or "surface"),
            per_stream=int(getattr(args, "per_stream", 1000) or 1000),
        )
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(scene, ensure_ascii=False, indent=2, default=str))
    else:
        print(render_orientation(scene))
    return 0
