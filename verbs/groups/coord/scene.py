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
import sys

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

@verb(local=False, door_notes="CLI only; reads core.coord.intent_shadow. Zero-effect by construction.")
def cmd_shadow(args):
    """Render one deterministic proposed-action ghost without executing it."""
    subject = str(getattr(args, "agent", "") or
                  os.environ.get("AKASHIC_AGENT_ID", "") or "").strip()
    if not subject:
        print("ERROR: intent shadow subject is required: pass --agent <id> or set "
              "AKASHIC_AGENT_ID")
        return 2
    try:
        arguments = json.loads(str(getattr(args, "args_json", "{}") or "{}"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: --args-json must be one JSON object ({exc})")
        return 2
    if not isinstance(arguments, dict):
        print("ERROR: --args-json must decode to one JSON object")
        return 2
    try:
        from core.coord.intent_shadow import build_intent_shadow, render_intent_shadow
        shadow = build_intent_shadow(subject, str(args.target), arguments)
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(shadow, ensure_ascii=False, indent=2, default=str))
    else:
        print(render_intent_shadow(shadow))
    return 0


@verb(local=False, door_notes="CLI only; reads core.coord.ground. Read-only evidence, never an assertion.")
def cmd_ground(args):
    """Build typed verb evidence or a non-authoritative seat continuity profile."""
    subject = str(getattr(args, "agent", "") or
                  os.environ.get("AKASHIC_AGENT_ID", "") or "").strip()
    if not subject:
        print("ERROR: ground subject is required: pass --agent <id> or set "
              "AKASHIC_AGENT_ID")
        return 2
    try:
        from core.coord.ground import ground as _ground, render as _render_ground
        result = _ground(str(args.target), subject=subject,
                         continuity=bool(getattr(args, "continuity", False)))
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(_render_ground(result))
    return 0


@verb(local=False, door_notes="CLI only; reads core.context.world_snapshot. Pinned through the parser by tests/test_world_snapshot_surfaces.py (parsed.fn is agent_cli.cmd_glance).")
def cmd_glance(args):
    """T079/T060: one bounded, read-only projection over named authorities.

    Slice one exposes only the program projection. Adding an arbitrary subject
    label before a subject-specific reader exists would make scope look wider
    than the evidence, so future projections extend the parser deliberately.
    """
    from core.context.world_snapshot import (
        build_program_world_snapshot,
        project_operational_brief,
    )

    projection = str(getattr(args, "glance_projection", "") or "program")
    if projection != "program":
        print(f"[glance] unsupported projection: {projection}", file=sys.stderr)
        return 2
    snapshot = build_program_world_snapshot(
        ledger_path=getattr(args, "ledger_path", None),
        max_items=getattr(args, "max_items", 64),
    )
    payload = (
        project_operational_brief(snapshot)
        if bool(getattr(args, "brief", False))
        else snapshot
    )
    compact = bool(getattr(args, "compact", False))
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=None if compact else 2,
            separators=(",", ":") if compact else None,
        )
    )
    return 0
