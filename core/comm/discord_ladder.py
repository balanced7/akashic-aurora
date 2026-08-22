"""T380 -- the comms-stage reaction ladder, pure half (no discord import).

Turns three TRUE observables into reaction ops the gateway applies to the
operator's original Discord message, so message state is legible at a glance
from the phone (Daniil, 2026-08-22: "if I can tell at a glance what is going
on it will help me understand it better"):

  landed   -- stamped by the relay itself at enqueue (discord_inbound reacts
              inline; this module never sees that stage)
  thinking -- the addressed seat OPENED the mail: a mailbox seen receipt exists
              for the message's identity sha. One authority for "seen": both
              producers (daemon runners via mailbox.open, the harness seat via
              agent_cli consume -> mailbox.open_for_message, T133/M6) write
              through the same seam, which pin P1 asserts rather than assumes.
  answered -- STRICT: a message on the operator's inbox stream carries
              meta.answers == tracked mid (the T139 link). Rendered as the
              plain checkmark; the only op allowed to claim "answered".
  replied  -- HEURISTIC, a DISTINCT op rendered as a different emoji: a
              directed non-trace message from an addressed seat to the
              operator, newer than the tracked mid, inside REPLIED_WINDOW_S,
              carrying no strict link. Claims only "the seat wrote back",
              which is exactly what was observed -- never the checkmark.
  dead     -- an expectation_dead record names the tracked mid in refs.

Heimdall's fence counter (bus 1787417935818-0) is folded: one authority per
fact; heuristics labeled IN THE RENDER (distinct emoji); the events reader is
injected (same DI stance as get_event_log(ledger=...)); op staggering, evict-
on-deleted-message and restart re-derivation live in the runner, not here.

State is in-process by design (v1): a gateway restart drops in-flight ladder
entries -- documented residual on T380; the drill G1 does not require restart
survival. Settled entries evict immediately; unsettled entries expire after
ENTRY_TTL_S so the tracker cannot grow unbounded.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

REPLIED_WINDOW_S = 15 * 60        # unlinked-reply correlation horizon (fence counter b)
ENTRY_TTL_S = 24 * 3600           # unsettled entries expire; no unbounded growth
_TERMINAL = ("answered", "replied", "dead")


@dataclass
class _Entry:
    mid: str
    sha: str
    to_agents: List[str]
    channel_id: str
    discord_msg_id: str
    stage: str = "landed"          # landed -> thinking -> (answered|replied|dead)
    tracked_ts: float = field(default_factory=time.time)


class LadderTracker:
    """Tracks relayed operator messages; poll() returns reaction ops.

    Ops are dicts {"op", "channel_id", "discord_msg_id", "mid"} with op one of
    thinking | answered | replied | dead. Each op fires at most once per entry;
    terminal ops settle (and evict) the entry.
    """

    def __init__(self, client: Any, *, ns: str = "bifrost", operator: str = "daniil",
                 events_reader: Optional[Callable[[], List[Dict[str, Any]]]] = None):
        self._c = client
        self.ns = ns
        self.operator = operator
        self._events_reader = events_reader
        self._entries: Dict[str, _Entry] = {}
        # first contact: tail-init, settle nothing from the archive (feed pattern)
        self._op_cursor = self._tail(self._operator_inbox_key())

    # ---------------------------------------------------------------- keys
    def _operator_inbox_key(self) -> str:
        return f"{self.ns}:inbox:{self.operator}"

    def _inbox_key(self, agent: str) -> str:
        return f"{self.ns}:inbox:{agent}"

    def _tail(self, key: str) -> str:
        try:
            last = self._c.xrevrange(key, count=1)
            if last:
                sid = last[0][0]
                return sid.decode() if isinstance(sid, bytes) else str(sid)
        except Exception:
            pass
        return "0-0"

    # ---------------------------------------------------------------- track
    def track(self, mid: str, *, to_agents: List[str], channel_id: str,
              discord_msg_id: str) -> bool:
        """Register one relayed operator message. Resolves the identity sha the
        seen plane keys on by reading the record's OWN stream fields -- the same
        ingredients mailbox._identity_for_message sees at open time, so the join
        holds by construction rather than by hope."""
        mid = str(mid)
        if mid in self._entries or not to_agents:
            return False
        try:
            # identity through the ONE seam every open/declare path uses
            # (mailbox._identity_for_message) -- the pin P1 proved that hashing
            # the raw stream fields instead forks the sha (asserted packet_sha
            # vs the content fallback the projection produces).
            from core.comm.mailbox import _identity_for_message
            entries = self._c.xrange(self._inbox_key(str(to_agents[0])),
                                     min=mid, max=mid)
            if not entries:
                return False
            _, fields = entries[0]
            fields = {(k.decode() if isinstance(k, bytes) else str(k)):
                      (v.decode() if isinstance(v, bytes) else str(v))
                      for k, v in dict(fields).items()}
            msg_shape: Dict[str, Any] = dict(fields)
            msg_shape["meta"] = _meta_of(fields)
            sha, _basis = _identity_for_message(msg_shape)
        except Exception:
            return False
        self._entries[mid] = _Entry(mid=mid, sha=str(sha),
                                    to_agents=[str(a) for a in to_agents],
                                    channel_id=str(channel_id),
                                    discord_msg_id=str(discord_msg_id))
        return True

    # ---------------------------------------------------------------- poll
    def poll(self) -> List[Dict[str, Any]]:
        ops: List[Dict[str, Any]] = []
        self._sweep_expired()
        if not self._entries:
            # cursor still advances so a later track() never replays the gap
            self._op_cursor = self._tail(self._operator_inbox_key())
            return ops
        ops.extend(self._poll_answers())
        ops.extend(self._poll_thinking())
        ops.extend(self._poll_dead())
        return ops

    # thinking: seen receipt exists for any addressed seat
    def _poll_thinking(self) -> List[Dict[str, Any]]:
        out = []
        try:
            from core.comm.mailbox import seen_by
        except Exception:
            return out
        for e in list(self._entries.values()):
            if e.stage != "landed":
                continue
            for agent in e.to_agents:
                try:
                    if seen_by(self.ns, agent, e.sha, client=self._c):
                        e.stage = "thinking"
                        out.append(self._op("thinking", e))
                        break
                except Exception:
                    continue
        return out

    # answered (strict link) / replied (labeled heuristic, window-capped)
    def _poll_answers(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        key = self._operator_inbox_key()
        try:
            new = self._c.xrange(key, min="(" + self._op_cursor, max="+")
        except Exception:
            return out
        now = time.time()
        for sid, fields in new:
            sid = sid.decode() if isinstance(sid, bytes) else str(sid)
            self._op_cursor = sid
            fields = {(k.decode() if isinstance(k, bytes) else str(k)):
                      (v.decode() if isinstance(v, bytes) else str(v))
                      for k, v in dict(fields).items()}
            kind = fields.get("kind", "")
            if kind == "trace":
                continue
            meta = _meta_of(fields)
            answers = str(meta.get("answers") or "")
            if answers and answers in self._entries:
                e = self._entries[answers]
                if e.stage not in _TERMINAL:
                    e.stage = "answered"
                    out.append(self._op("answered", e))
                    self._entries.pop(e.mid, None)
                continue
            frm = fields.get("frm", "")
            if not frm:
                continue
            for e in list(self._entries.values()):
                if e.stage in _TERMINAL:
                    continue
                if frm in e.to_agents and sid > e.mid \
                        and (now - e.tracked_ts) <= REPLIED_WINDOW_S:
                    e.stage = "replied"
                    out.append(self._op("replied", e))
                    self._entries.pop(e.mid, None)
        return out

    # dead: expectation_dead names a tracked mid
    def _poll_dead(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if self._events_reader is None:
            return out
        try:
            records = self._events_reader() or []
        except Exception:
            return out
        for rec in records:
            if str(rec.get("kind") or "") != "expectation_dead":
                continue
            for ref in (rec.get("refs") or []):
                e = self._entries.get(str(ref))
                if e is not None and e.stage not in _TERMINAL:
                    e.stage = "dead"
                    out.append(self._op("dead", e))
                    self._entries.pop(e.mid, None)
        return out

    # ---------------------------------------------------------------- helpers
    def _op(self, op: str, e: _Entry) -> Dict[str, Any]:
        return {"op": op, "channel_id": e.channel_id,
                "discord_msg_id": e.discord_msg_id, "mid": e.mid}

    def _sweep_expired(self) -> None:
        cutoff = time.time() - ENTRY_TTL_S
        for mid in [m for m, e in self._entries.items() if e.tracked_ts < cutoff]:
            self._entries.pop(mid, None)


def _meta_of(fields: Dict[str, str]) -> Dict[str, Any]:
    try:
        m = json.loads(fields.get("meta") or "{}")
        return m if isinstance(m, dict) else {}
    except Exception:
        return {}
