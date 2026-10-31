"""bus -- read ONE bus message by id, in full (the exception path behind every clipped preview).

Filed by the 2026-10-30 wish (docs/WISHLIST.md, phase 3 of the modular-core detangle): "Full
waking message on wake (WOKE BY previews are clipped; every wake needed a hand-written json
one-liner), plus `bus read <id>`."

WHY A VERB AND NOT A SUB-ACTION OF `bifrost-sync`: this is an INSPECTION with a message id in
hand, not a consume. It reads no cursor, advances nothing and needs no seat -- which is exactly
the property that makes it safe to run from a stranded session, or from a seat whose consumer
seat a twin is holding. The `bifrost-sync` door answers "what is new for me"; this one answers
"what was THAT".

SHAPE NOTE (the registry's first real users report): the CLI spelling is `bus read <id>`, but
`add_subparsers` would make `read` a separate VERB to the door-parity checker -- the phantom-verb
class this house has already paid for twice (`recall-audit`, `fence`). So `read` is a POSITIONAL
CHOICE, following the convention `fence` and `recall-audit` set.
"""
from __future__ import annotations

import json

from verbs.registry import verb


@verb(local=False,
      door_notes="CLI only for now. An MCP twin is a natural follow-up, but it would widen a "
                 "read that spans every stream under the namespace to any attached seat; the "
                 "operator-facing `reachability`/`bus read` pair is deliberately one door while "
                 "the provenance field is still young.")
def cmd_bus(args):
    """`bus read <id>`: one message by id, every field, and where it came from."""
    from core.comm import bus_read
    action = str(getattr(args, "action", "") or "").strip()
    if action != "read":
        print(f"ERROR: unknown `bus` action {action!r}; the only action is `bus read <id>`")
        return 2
    msg_id = str(getattr(args, "id", "") or "").strip()
    if not msg_id:
        print("ERROR: `bus read` needs a message id, e.g. `bus read 1793405184749-0`")
        return 2
    found = bus_read.find_message(msg_id,
                                  agent=(getattr(args, "agent", "") or None),
                                  stream=(getattr(args, "stream", "") or None))
    if getattr(args, "json", False):
        print(json.dumps(found, indent=2, default=str))
    else:
        print(bus_read.render(found))
    return 0 if found.get("found") else 1
