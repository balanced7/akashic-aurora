"""
Bifrost Bus (Slice B0) -- one ephemeral message transport for local agents, on Redis Streams.

Semantic Relationship: Agent sends Message to Agent (or broadcasts) over the Bus

This consolidates the four old comm layers into one, and fixes their bugs:
  * **Correct port.** Connects via the canonical connector (the single-source-of-truth host/port),
    not the hardcoded 6379 that `fast_agent_comm` used (real Redis is on 16379).
  * **Real fan-out.** Each agent has its OWN inbox stream (`bifrost:inbox:<agent>`); broadcasts go to a
    shared `bifrost:broadcast` stream that every agent reads from its OWN cursor -- so a broadcast reaches
    ALL agents. (The old code used a single shared consumer group, which *load-balances*, so a "broadcast"
    reached exactly one agent -- the bug.)
  * **Ephemeral, not the durable record.** This is the live transport only (Redis Streams). The durable
    "what was said" record is a separate Ledger projection (slice B2) -- the bus and the audit ledger are
    deliberately NOT conflated (design delta F1).

When Redis is down there is NO live bus -- surfaced EXPLICITLY (`online` is False, `send` returns None),
never silently swallowed. Streams are bounded (maxlen) since this is ephemeral transport.

Read model: per-agent cursors (last-read stream id for inbox + broadcast) in a Redis hash, so each agent
catches up on exactly what it missed and never re-reads (offset semantics without consumer-group coupling).
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.comm.blobs import get_blob_store

NS = "bifrost"
DEFAULT_MAXLEN = 10_000
BROADCAST_TO = "*"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads(s: Any) -> Any:
    if s is None or s == "":
        return None
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return s


def _connect():
    """The canonical Redis client (correct host/port, decode_responses). None if unreachable."""
    try:
        from core.foundation.redis_connection import (
            connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
        return connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, timeout_seconds=3, decode_responses=True)
    except Exception:
        return None


@dataclass
class Part:
    """An A2A-style atomic content unit: a typed value that is either INLINE (small/text) or a
    `blob:<sha>` REFERENCE (media/large) the receiver fetches on demand (lossless-pointer rule)."""
    content_type: str               # text/plain | application/json | image/png | ...
    inline: Any = None              # the value, when carried inline
    ref: Optional[str] = None       # a blob ref, when stored out-of-band

    @property
    def is_ref(self) -> bool:
        return self.ref is not None

    def resolve(self, blobs=None) -> Any:
        """The Part's value: the inline value, or the fetched blob bytes (None if the blob is gone)."""
        if self.ref is not None:
            return (blobs or get_blob_store()).get(self.ref)
        return self.inline

    def to_dict(self) -> Dict[str, Any]:
        return {"content_type": self.content_type, "inline": self.inline, "ref": self.ref}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Part":
        return cls(content_type=d.get("content_type", "application/octet-stream"),
                   inline=d.get("inline"), ref=d.get("ref"))


def text_part(s: Any) -> Part:
    return Part("text/plain", inline=str(s))


def json_part(obj: Any) -> Part:
    return Part("application/json", inline=obj)


def media_part(data, content_type: str, *, blobs=None) -> Part:
    """Store bytes/str as a content-addressed blob and carry only the ref (media-by-reference)."""
    return Part(content_type, ref=(blobs or get_blob_store()).put(data))


def file_part(path, *, content_type: Optional[str] = None, blobs=None) -> Part:
    import mimetypes
    ct = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return Part(ct, ref=(blobs or get_blob_store()).put_path(path))


@dataclass
class Message:
    id: str                 # the stream entry id (also the read cursor / offset)
    frm: str
    to: str                 # an agent id, or "*" for a broadcast
    kind: str               # chat | request | response | handoff | note | ...
    content: Any
    ts: str
    meta: Dict[str, Any] = field(default_factory=dict)
    parts: List[Part] = field(default_factory=list)    # A2A parts (inline or blob refs)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "frm": self.frm, "to": self.to, "kind": self.kind,
                "content": self.content, "ts": self.ts, "meta": self.meta,
                "parts": [p.to_dict() for p in self.parts]}


class Bus:
    """An agent's handle on the Bifrost transport. One per agent identity."""

    def __init__(self, agent_id: str, client: Optional[Any] = None, *,
                 namespace: str = NS, maxlen: int = DEFAULT_MAXLEN):
        self.agent_id = str(agent_id or "unknown")
        self.ns = namespace
        self.maxlen = maxlen
        self._client = client if client is not None else _connect()

    # ------------------------------------------------------------------ identity / health
    @property
    def online(self) -> bool:
        """True iff the live bus (Redis) is reachable. When False, sends are no-ops returning None."""
        return self._client is not None

    def status(self) -> Dict[str, Any]:
        return {"online": self.online, "agent_id": self.agent_id, "pending": self.pending()}

    # ------------------------------------------------------------------ keys
    def _inbox_key(self, agent: str) -> str:
        return f"{self.ns}:inbox:{agent}"

    @property
    def _bc_key(self) -> str:
        return f"{self.ns}:broadcast"

    def _cursor_key(self) -> str:
        return f"{self.ns}:cursor:{self.agent_id}"

    # ------------------------------------------------------------------ send
    def send(self, to: str, kind: str, content: Any = None, *, parts: Optional[List[Part]] = None,
             meta: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Direct message to one agent's inbox (optionally with `parts` -- inline or media-by-ref).
        Returns the message id, or None if the bus is offline."""
        return self._emit(self._inbox_key(str(to)), to=str(to), kind=kind, content=content,
                          parts=parts, meta=meta)

    def broadcast(self, kind: str, content: Any = None, *, parts: Optional[List[Part]] = None,
                  meta: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Fan-out to every agent (each reads it from its own cursor). Returns the message id or None."""
        return self._emit(self._bc_key, to=BROADCAST_TO, kind=kind, content=content,
                          parts=parts, meta=meta)

    def _emit(self, stream: str, *, to: str, kind: str, content: Any,
              parts: Optional[List[Part]] = None, meta=None) -> Optional[str]:
        if not self.online:
            return None
        part_dicts = [(p.to_dict() if isinstance(p, Part) else p) for p in (parts or [])]
        env = {"frm": self.agent_id, "to": to, "kind": str(kind),
               "content": json.dumps(content, default=str), "ts": _now(),
               "meta": json.dumps(meta or {}, default=str),
               "parts": json.dumps(part_dicts, default=str)}
        try:
            return str(self._client.xadd(stream, env, maxlen=self.maxlen, approximate=True))
        except Exception:
            return None

    # ------------------------------------------------------------------ receive
    def inbox(self, limit: int = 50, *, advance: bool = True) -> List[Message]:
        """New messages for this agent (direct + broadcast), oldest-first, from the per-agent cursor.

        `advance=True` moves the cursor past what's returned (so the next call won't re-read). An agent's
        own broadcasts are not delivered back to it. Returns [] (never raises) when offline."""
        if not self.online:
            return []
        cur = self._read_cursor()
        try:
            res = self._client.xread(
                {self._inbox_key(self.agent_id): cur["inbox"], self._bc_key: cur["bc"]},
                count=max(1, limit))
        except Exception:
            return []
        new_inbox, new_bc = cur["inbox"], cur["bc"]
        out: List[Message] = []
        for stream, entries in res or []:
            is_bc = (stream == self._bc_key)
            for sid, fields in entries:
                if is_bc:
                    new_bc = sid
                else:
                    new_inbox = sid
                m = self._to_msg(sid, fields)
                if is_bc and m.frm == self.agent_id:
                    continue                       # don't deliver an agent its own broadcast
                out.append(m)
        out.sort(key=lambda m: m.id)               # ms-based stream ids -> ~time order across streams
        if advance and (new_inbox != cur["inbox"] or new_bc != cur["bc"]):
            self._write_cursor(new_inbox, new_bc)
        return out[:limit]

    def pending(self) -> int:
        """How many unread messages are waiting (direct + broadcast), without advancing the cursor."""
        msgs = self.inbox(limit=1000, advance=False)
        return len(msgs)

    # ------------------------------------------------------------------ cursor
    def _read_cursor(self) -> Dict[str, str]:
        try:
            h = self._client.hgetall(self._cursor_key()) or {}
        except Exception:
            h = {}
        return {"inbox": h.get("inbox", "0"), "bc": h.get("bc", "0")}

    def _write_cursor(self, inbox: str, bc: str) -> None:
        try:
            self._client.hset(self._cursor_key(), mapping={"inbox": inbox, "bc": bc})
        except Exception:
            pass

    def _to_msg(self, sid: str, fields: Dict[str, Any]) -> Message:
        parts = [Part.from_dict(d) for d in (_loads(fields.get("parts")) or []) if isinstance(d, dict)]
        return Message(id=str(sid), frm=fields.get("frm", ""), to=fields.get("to", ""),
                       kind=fields.get("kind", ""), content=_loads(fields.get("content")),
                       ts=fields.get("ts", ""), meta=_loads(fields.get("meta")) or {}, parts=parts)


_INSTANCES: Dict[str, Bus] = {}


def get_bus(agent_id: Optional[str] = None) -> Bus:
    """Module cache, one Bus per agent identity. agent_id defaults to $AGENT_ID or 'unknown'."""
    aid = str(agent_id or os.getenv("AGENT_ID", "unknown"))
    if aid not in _INSTANCES:
        _INSTANCES[aid] = Bus(aid)
    return _INSTANCES[aid]
