"""T108 acceptance pins -- PRE-REGISTERED, RED ON PURPOSE (M3: acceptance before implementation).

Daniel's charter, verbatim (2026-07-28): "why can't we have two seats or as many as we need so
we stop getting all this mail mis routing, mis waking, mis consuming, mis everything mess."

These pins test the PROPERTY, not the mechanism, so they are valid regardless of how the
T108 fence (claude+deepseek+kimi) reconciles the design:

  PIN 1  TWIN ISOLATION: two live seats of one agent, directed mail addressed to each,
         ZERO cross-consumption. This is the exact defect lived on 2026-07-27/28 -- the
         prior seat consuming replies meant for the new one -- expressed as an assertion.
  PIN 2  REAPER: a dead seat's unread DIRECTED mail must become reachable by a survivor
         (re-homed loudly), never silently stranded on a private cursor.

Both are RED today by construction: delivery is one shared stream per agent id
(bifrost:inbox:<agent>) with one shared cursor, so seat B consuming ALWAYS sees seat A's
directed mail (pin 1), and nothing re-homes anything (pin 2).

Namespace-isolated per T039 precedent (Bus(namespace=...)); conftest's universal isolation
covers the store planes.
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus  # noqa: E402

NS = f"t108pin{uuid.uuid4().hex[:6]}"
AGENT = "claude"
SEAT_A = "aaaa1111-0000-0000-0000-000000000000"
SEAT_B = "bbbb2222-0000-0000-0000-000000000000"


def _seat_bus(session_id: str, ns: str = None) -> Bus:
    """A bus handle AS a specific incarnation of AGENT (env carries the incarnation identity,
    matching how live seats derive it)."""
    os.environ["BIFROST_INCARNATION"] = session_id
    os.environ["CLAUDE_CODE_SESSION_ID"] = session_id
    return Bus(AGENT, namespace=ns or NS)


def _drain_all(bus: Bus):
    """Consume everything currently deliverable to this handle's agent."""
    out = []
    for _ in range(6):
        msgs = bus.inbox(advance=True)
        if not msgs:
            break
        out.extend(msgs)
    return out


def test_pin1_directed_mail_never_crosses_seats():
    """Directed mail to seat A must be invisible to seat B's consume, and vice versa."""
    sender = Bus("deepseek", namespace=NS)
    if not getattr(sender, "online", True):
        print("SKIPPED (Redis not running)")
        return

    sender.send(AGENT, "note", f"for-seat-A-{NS}", meta={"to_incarnation": SEAT_A})
    sender.send(AGENT, "note", f"for-seat-B-{NS}", meta={"to_incarnation": SEAT_B})

    # Seat B consumes FIRST (the theft ordering that bit us live).
    seen_b = _drain_all(_seat_bus(SEAT_B))
    bodies_b = " | ".join(str(getattr(m, "content", m)) for m in seen_b)
    assert f"for-seat-A-{NS}" not in bodies_b, (
        "TWIN THEFT: seat B consumed mail directed to seat A. This is the lived 2026-07-27 "
        "defect (prior seat answering the new seat's mail) as an assertion. Seat B saw: "
        + bodies_b[:300])

    # And seat A must still be able to receive its own mail afterwards.
    seen_a = _drain_all(_seat_bus(SEAT_A))
    bodies_a = " | ".join(str(getattr(m, "content", m)) for m in seen_a)
    assert f"for-seat-A-{NS}" in bodies_a, (
        "STARVED SUCCESSOR: seat A's directed mail is gone -- consumed by another seat's "
        "cursor advance or lost. Seat A saw: " + (bodies_a[:300] or "(nothing)"))


def test_pin2_dead_seat_directed_mail_rehomes():
    """A tombstoned/dead seat's unread directed mail must reach a survivor, loudly."""
    sender = Bus("deepseek", namespace=NS + "r")
    if not getattr(sender, "online", True):
        print("SKIPPED (Redis not running)")
        return

    sender.send(AGENT, "note", f"stranded-{NS}", meta={"to_incarnation": SEAT_A})

    # Seat A dies without ever consuming (no clean SessionEnd -- the realistic death).
    # Survivor B sweeps; the message must become reachable to B by SOME sanctioned door
    # (re-homed to role delivery, a reaper queue -- mechanism is the fence's choice).
    time.sleep(0.2)
    seen_b = _drain_all(_seat_bus(SEAT_B, NS + "r"))
    bodies_b = " | ".join(str(getattr(m, "content", m)) for m in seen_b)
    assert f"stranded-{NS}" in bodies_b, (
        "SILENT STRANDING: seat A died holding directed mail and no survivor can reach it. "
        "The reaper (re-home to role queue, loudly) does not exist. Survivor saw: "
        + (bodies_b[:300] or "(nothing)"))


if __name__ == "__main__":
    test_pin1_directed_mail_never_crosses_seats()
    test_pin2_dead_seat_directed_mail_rehomes()
    print("PASS")
