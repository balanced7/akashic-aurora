"""session_exit -- the clean-death trio (T075 M1-beta, reconciliation ruling 3).

A session that ends CLEANLY releases, in the same breath, everything its liveness
was holding:

  1. the consumer SEAT (runner_lock, session:<sid> token) -- the 2026-07-15 ~03:xx
     thirty-minute seat shadow (receipt f9207c90) was exactly this seat outliving
     its dead session and blocking the successor for SESSION_CONSUMER_TTL;
  2. its incarnation CARD -- siblings must stop seeing a ghost immediately, not at
     card TTL;
  3. its wake LISTENER's seat file + activity marker -- removal IS the stand-down
     signal (bifrost_wake's own seat-lost path exits benign at its next check;
     displacement doctrine, never a kill -- wake_seat K-laws), and a dead session's
     marker must not ghost live_incarnations' fallback.

TTL expiry remains the CRASH net everywhere -- this trio only makes the CLEAN path
instant (0s instead of <=30min). Crash-death changes NOTHING here by construction:
the hook simply never fires.

The EVENT GUARD lives in this module (B-a): only event='SessionEnd' acts.
PreCompact means the session continues -- the hook passes its event through
verbatim so the guard is pinnable in-process instead of trusting hook wiring.

Fail-open discipline: every leg is independently guarded; a clean death must
never block a session from ending (same law as the SessionEnd draft capture).
Kill switch: AKASHIC_CLEAN_DEATH=0 (B-c, the ruling-4 first-week hatch pattern).
Every run appends ONE provenance line (wake_seat.append_provenance) so a released
seat is auditable and never mistaken for a lock expiry.
"""
from __future__ import annotations

import os
from typing import Optional


def clean_death(agent: str, session_id: str, tmp: Optional[str] = None,
                c=None, event: str = "SessionEnd") -> dict:
    """Release seat + card + listener artifacts for exactly (agent, session_id).

    Returns a provenance dict: {"seat","card","listener","marker"} booleans --
    True = released/removed now, False = not held / not present / leg failed
    (fail-open: callers must not care which). {"disabled": True} when the guard
    (event/kill-switch/empty-ids) stopped the trio entirely.

    `c` (bus client) and `tmp` (seat-file dir) are test seams, T074 convention;
    the lock leg talks through runner_lock's own module client. B-d: every leg
    addresses its own session's artifacts only -- the seat by token match, the
    card by exact key, the files by exact name."""
    if event != "SessionEnd":
        return {"disabled": True}
    if os.getenv("AKASHIC_CLEAN_DEATH", "1") == "0":
        return {"disabled": True}
    if not agent or not session_id:
        return {"disabled": True}

    out = {"seat": False, "card": False, "listener": False, "marker": False}
    token = f"session:{session_id}"

    try:   # ---- leg 1: consumer seat (own hold only -- release() refuses foreign tokens)
        from core.comm import runner_lock
        held = runner_lock.holder(agent)
        ours = bool(held and held.get("token") == token)
        if ours:
            runner_lock.release_consumer(agent, token)
            out["seat"] = runner_lock.holder(agent) is None
    except Exception:
        pass

    try:   # ---- leg 2: incarnation card (exact key; TTL stays the crash net)
        from core.comm import incarnation
        out["card"] = incarnation.delete_card(agent, session_id, c=c)
    except Exception:
        pass

    try:   # ---- leg 3: listener seat file + activity marker (removal = stand-down)
        from core.comm import wake_seat
        for field, path in (("listener", wake_seat.seat_path(agent, session_id, tmp)),
                            ("marker", wake_seat.activity_marker_path(agent, session_id, tmp))):
            try:
                if os.path.exists(path):
                    os.remove(path)
                    out[field] = True
            except Exception:
                pass
        wake_seat.append_provenance(
            agent,
            f"clean-death sid={session_id[:8]}: seat={out['seat']} card={out['card']} "
            f"listener={out['listener']} marker={out['marker']} (M1-beta trio; TTLs remain the crash net)",
            tmp)
    except Exception:
        pass

    return out
