"""
EventLog (Slice 1) -- capture raw cross-agent events on an append-only Ledger.

Semantic Relationship: RawEvent appended_to EventFirehose (time-ordered)

The full-fidelity substrate BENEATH the narrative spine: every meaningful thing an agent
does (a tool call, a file edit, a command, an observation) is captured as a RAW EVENT on
the Ledger -- "what HAPPENED, in order". The narrative Beats are the *salient* distillation;
these raw events are the *un-distilled detail* a Beat's `source` can point at, so an agent
navigating the timeline can drill down to "what actually happened, and how".

This is the layer the foundation always reserved (core/foundation/ledger.py: "this ledger
is the RAW firehose ... a chronicle is a distilled view DERIVED FROM this ledger") and the
LEXICON names ("Raw / archival -- ... Ledger streams. Append-only; never mutated or deleted").

Storage (on a Ledger -- the canonical HybridLedger, or an injected ledger for tests):
    events:raw            -> the canonical firehose (every agent)   maxlen ~100k
    events:{agent}:raw    -> per-agent history (a convenience index) maxlen ~10k

A raw event is addressable as  event:<stream>:<id>  -- a followable pointer usable as a
Beat.source (the lossy-summary + lossless-pointer rule, one level deeper).

`kind` is an OPEN vocabulary (tool_call / file_edit / command / observation / message /
note / ...), deliberately distinct from the CLOSED 6-species signal set on `agent:events`
(action/decision/blocker/handoff/completion/learning). That separation is WHY raw events
get their own stream: they must never pollute the coordination firehose the
CoordinatorService switches on by `signal_type`.

Best-effort by design: capture() never raises into the caller's main flow, so hooking it
into hot paths (commits, CLI verbs, sessions) can never break them.
"""
import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.foundation.ledger import Ledger, create_ledger

logger = logging.getLogger("event_log")

RAW_STREAM = "events:raw"
CANONICAL_MAXLEN = 100_000        # the firehose: deep but bounded
PER_AGENT_MAXLEN = 10_000         # per-agent: a shallower convenience index

# Starter kinds (OPEN vocabulary -- a new kind is just a new string, no schema change).
EVENT_KINDS = ("tool_call", "file_edit", "command", "observation", "message", "note")

_MAX_SUMMARY = 500
_MAX_DETAIL_CHARS = 8000          # raw is rich, but a single payload is still bounded
_READ_BATCH = 1000


def per_agent_stream(agent_id: Optional[str]) -> str:
    """The per-agent raw stream name (sanitized so it maps to one safe ledger key)."""
    raw = agent_id or "unknown"
    safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in str(raw))
    return f"events:{safe}:raw"


def event_ref(stream: str, event_id: str) -> str:
    """A followable pointer to one raw event (usable verbatim as a Beat.source)."""
    return f"event:{stream}:{event_id}"


class EventLog:
    """Capture-and-read raw events on an append-only Ledger firehose.

    Semantic Relationship: EventLog records RawEvents (full-fidelity, cross-agent)
    """

    def __init__(self, ledger: Optional[Ledger] = None):
        self.ledger = ledger if ledger is not None else create_ledger()

    # --------------------------------------------------------------- capture (write)
    def capture(self, kind: str, summary: str, *,
                detail: Optional[Dict[str, Any]] = None,
                agent_id: Optional[str] = None, session_id: str = "",
                refs: Optional[List[str]] = None, track: Optional[str] = None,
                at: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Append one raw event to events:raw (+ the per-agent stream).

        Returns the stored event enriched with its assigned `id` and `_ref`
        (event:<stream>:<id>), or None on a refusal. NEVER raises -- a capture hiccup
        must not break the host command.

        `track` is an OPTIONAL pass-through: this is a pure domain primitive (it knows
        nothing of narrative Tracks). Routing a raw event to a Track is a narrative
        concern done at the query/bridge layer (Slice 3/4), where importing the
        TrackRouter is layering-legal -- capture must not depend upward on System 4.
        """
        try:
            agent = self._clean(agent_id) or "unknown"
            event = {
                "at": at or datetime.utcnow().isoformat(),
                "agent_id": agent,
                "session_id": self._clean(session_id),
                "kind": str(kind) if kind else "note",
                "summary": self._clip(summary, _MAX_SUMMARY),
                "detail": self._safe_detail(detail),
                "track": track,
                "refs": [str(r) for r in (refs or []) if r],
            }
            # The canonical firehose is the system of record AND the source of the
            # followable id (reads resolve event:<RAW_STREAM>:<id> against it).
            eid = self.ledger.emit(RAW_STREAM, event, maxlen=CANONICAL_MAXLEN)
            try:
                self.ledger.emit(per_agent_stream(agent), event, maxlen=PER_AGENT_MAXLEN)
            except Exception:
                pass   # the per-agent stream is a convenience index; canonical is the record
            out = dict(event)
            out["id"] = str(eid)
            out["_ref"] = event_ref(RAW_STREAM, str(eid))
            return out
        except Exception as e:
            logger.warning(f"capture failed (ignored): {type(e).__name__}: {e}")
            return None

    # --------------------------------------------------------------- read
    def recent(self, limit: int = 20, *, agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """The newest `limit` raw events (firehose, or one agent's stream), newest-first."""
        stream = per_agent_stream(agent) if agent else RAW_STREAM
        events = self._read_all(stream)
        return list(reversed(events))[:max(0, limit)]

    def count(self, *, agent: Optional[str] = None) -> int:
        """How many raw events are on the firehose (or one agent's stream)."""
        stream = per_agent_stream(agent) if agent else RAW_STREAM
        return len(self._read_all(stream))

    def scan(self, *, agent: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """All raw events OLDEST-first (firehose, or one agent's stream); the read surface
        the query layer filters/ranks over. `limit` keeps the newest `limit` events."""
        stream = per_agent_stream(agent) if agent else RAW_STREAM
        events = self._read_all(stream)
        if limit is not None and len(events) > limit:
            events = events[-limit:]
        return events

    def get(self, ref: str) -> Optional[Dict[str, Any]]:
        """Resolve a followable `event:<stream>:<id>` pointer to its stored raw event."""
        stream, eid = self._parse_ref(ref)
        if not stream:
            return None
        for ev in self._read_all(stream):
            if ev.get("id") == eid:
                return ev
        return None

    # --------------------------------------------------------------- internals
    def _read_all(self, stream: str) -> List[Dict[str, Any]]:
        """Replay a whole stream oldest-first, attaching each event's id + followable ref.

        O(n) by design -- the Ledger is replay-only (no reverse range), and the stream is
        bounded by maxlen. Slice 3 adds time-window / indexed queries for hot paths.
        """
        out: List[Dict[str, Any]] = []
        after = "0"
        while True:
            try:
                batch = self.ledger.consume(stream, after_id=after, count=_READ_BATCH)
            except Exception as e:
                logger.warning(f"read of {stream} failed (partial): {type(e).__name__}: {e}")
                break
            if not batch:
                break
            for eid, ev in batch:
                rec = dict(ev) if isinstance(ev, dict) else {"raw": ev}
                rec["id"] = str(eid)
                rec["_ref"] = event_ref(stream, str(eid))
                out.append(rec)
                after = str(eid)
            if len(batch) < _READ_BATCH:
                break
        return out

    @staticmethod
    def _parse_ref(ref: str):
        """event:<stream>:<id> -> (stream, id). Stream names contain ':' so split carefully."""
        s = str(ref or "")
        if not s.startswith("event:"):
            return None, None
        body = s[len("event:"):]
        if ":" not in body:
            return None, None
        stream, _, eid = body.rpartition(":")
        return (stream or None), (eid or None)

    @staticmethod
    def _clip(s, n: int) -> str:
        s = "" if s is None else str(s)
        return s if len(s) <= n else s[:n] + "...[clipped]"

    @staticmethod
    def _clean(s) -> str:
        return "" if s is None else str(s)[:200]

    @staticmethod
    def _safe_detail(detail):
        """Normalize `detail` to PLAIN-JSON-native types, bounded in size.

        Critical: the Ledger persists each event with a plain ``json.dumps`` (no
        ``default=str``). A payload that only serializes *with* ``default=str`` (e.g. a
        stray object) would therefore crash the backend write and silently drop the event.
        So we round-trip through ``default=str`` HERE and hand back the normalized result,
        guaranteeing the stored detail is safe for the backend's own serializer.
        """
        if detail is None:
            return {}
        try:
            blob = json.dumps(detail, default=str)
        except Exception:
            return {"_repr": str(detail)[:_MAX_DETAIL_CHARS]}
        if len(blob) > _MAX_DETAIL_CHARS:
            return {"_truncated": True, "_repr": blob[:_MAX_DETAIL_CHARS]}
        try:
            return json.loads(blob)   # pure str/int/float/list/dict -- backend-safe
        except Exception:
            return {"_repr": blob[:_MAX_DETAIL_CHARS]}


def capture_event(kind: str, summary: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Best-effort one-liner for hot-path hooks: capture one raw event via the singleton.

    Swallows EVERYTHING (including import/connect failures the caller can't foresee), so a
    hook site reduces to ``capture_event(...)`` with no try/except of its own and zero risk
    of breaking the host command (commit, boot, learn, session). The auto-logger's prime
    directive: capturing the story must never cost you the thing you were doing.
    """
    try:
        return get_event_log().capture(kind, summary, **kwargs)
    except Exception:
        return None


_INSTANCE: Optional[EventLog] = None


def reset_event_log_singleton() -> None:
    """Clear the module singleton (tests only)."""
    global _INSTANCE
    _INSTANCE = None


def get_event_log(ledger: Optional[Ledger] = None) -> EventLog:
    """Module singleton (lazy). Pass `ledger` for an isolated EventLog (tests/trial).

    When ``_AISETUP_TEST_ISOLATED`` is set (see tests/isolate_canonical.py), never cache a
    singleton -- each call uses a fresh Ledger so subprocess CLI tests cannot pollute the
    canonical firehose on db 0.
    """
    global _INSTANCE
    if ledger is not None:
        return EventLog(ledger)
    if os.environ.get("_AISETUP_TEST_ISOLATED"):
        return EventLog(create_ledger())
    if _INSTANCE is None:
        _INSTANCE = EventLog()
    return _INSTANCE
