"""discord_guest_reply -- the pure half of the guest reply path (the tier's missing direction).

LIVE DEFECT 2026-08-26 (Daniil verbatim: "your reply never landed in the discord"): the
Discord guest tier was built one-directional. Admission works -- a guest's words reach the
bus attributed, authority:none, heard -- but a seat's reply has no path back, so it dies on
the bus. This module is the tracker half of the fix, split exactly like the ladder
(core/comm/discord_ladder.py): pure, pinnable, no Discord import. The runner wires it
beside the ladder and owns the posting.

THE POSTURE, BOTH DIRECTIONS: a visitor may be ANSWERED, never steered. Control kinds
never produce a post op even from a tracked thread -- two locks on one door, the relay's
own rule (remote_bridge_relay.py: "a relay that trusts its upstream is one upstream bug
from being a remote control").

Idempotency: a reply id that already posted never posts again (RB-26 one plane up -- the
runner lane redelivers on crash; a guest must not receive the same answer twice).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

#: Discord's message cap is 2000; the runner already clips at 1900 (stillbirth confessor).
MAX_POST_CHARS = 1900

#: The kinds that must never ride the way OUT. Deliberately narrow-positive: anything not
#: in this set may be posted; a seat's reply/chat/inform is an answer, these are steering.
#: Membership is the bus plane's control family (halt/interrupt/pause/resume/nudge/steer),
#: registered in check_kind_policy PLANES -- one home, no second taxonomy.
CONTROL_KINDS = frozenset({
    "halt", "interrupt", "pause", "resume", "nudge", "steer",
})


class GuestReplyTracker:
    """Tracks admitted guest messages and decides which seat replies become POST ops.

    channel_key is opaque to this module -- the runner stores whatever handle lets it
    reach the guest's channel (the Discord message object itself, in practice).
    """

    def __init__(self) -> None:
        self._tracked: Dict[str, Any] = {}
        self._posted: set = set()

    def track(self, bus_id: str, channel_key: Any) -> None:
        """Register a guest message by its bus id, so replies to it can find their way out."""
        self._tracked[str(bus_id)] = channel_key

    def poll(self, msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return the POST ops for this batch: {channel_key, frm, text} per reply that
        answers a tracked guest. Never raises; a malformed message is a no-op, not a crash."""
        ops: List[Dict[str, Any]] = []
        for m in msgs or []:
            if not isinstance(m, dict):
                continue
            meta = m.get("meta") or {}
            rid = str(m.get("id") or "")
            # Two link forms, one seam: bus.send_reply stamps meta.reply_id; the CLI's
            # --answers stamps meta.answers (the ladder's strict link). Either answers
            # a guest; the tracker follows both so the door and the ladder never fork.
            reply_to = str(meta.get("reply_id") or meta.get("answers") or "")
            chan = self._tracked.get(reply_to)
            if chan is None:
                continue                       # not answering a guest we admitted -- ambient
            if str(m.get("kind") or "") in CONTROL_KINDS:
                continue                       # answered, never steered -- the tier's law, outbound
            if rid and rid in self._posted:
                continue                       # crash redelivery -- post once, ever
            text = str(m.get("text") or "").strip()
            if not text:
                continue
            ops.append({"channel_key": chan,
                        "frm": str(m.get("frm") or "seat"),
                        "text": text[:MAX_POST_CHARS]})
            if rid:
                self._posted.add(rid)
        return ops
