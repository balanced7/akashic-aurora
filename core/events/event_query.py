"""
EventQuery (Slice 3) -- search and time-window the raw event firehose.

Semantic Relationship: RawEvents retrieved_by Query (filter + rank)

This is the READ surface over the auto-logger's raw firehose -- the half of the feature
that lets "agents navigating the timeline" actually find things. It answers the three
questions an agent asks of the un-distilled record:

  1. "What happened in this span?"   -> events_in_window(start, end, ...)
        the timeline bridge: a Chapter has span_start/span_end, a Beat has `at` +/- a
        window -> drill = "give me the raw events under this stretch of the story".
  2. "Find where X happened."        -> search(query, kind=, agent=, track=, since=, until=)
        filter, then rank with the SHARED Ranker (keyword relevance + recency). The
        embedding relevance_fn is a later swap-in -- same 0..1 contract, must beat the
        keyword baseline on the fixture or it doesn't ship (same gate as TrackRouter Tier 1).
  3. "Show me this exact event."     -> get(event_ref)   (resolve event:<stream>:<id>)

Layering: a PURE domain query (System 1-3). It depends only on the EventLog (foundation
Ledger) and the shared Ranker (core/primitives). It does NOT import the narrative layer --
routing a raw event to a Track / linking it to a Beat is the BRIDGE concern (Slice 4),
which lives in System 4 where importing the TrackRouter is layering-legal.
"""
from typing import Any, Dict, List, Optional

from core.events.event_log import EventLog, get_event_log
from core.primitives.ranker import Ranker

_DEFAULT_SCAN = 20000   # how many recent events a query considers (briefing_loader precedent)


from core.foundation.timeutil import to_epoch as _epoch   # unified tz-safe epoch (S5)


class EventQuery:
    """Filter + rank raw events off the firehose.

    Semantic Relationship: EventQuery selects RawEvents (by window / filters / relevance)
    """

    def __init__(self, event_log: Optional[EventLog] = None, ranker: Optional[Ranker] = None,
                 scan: int = _DEFAULT_SCAN):
        self.log = event_log if event_log is not None else get_event_log()
        self.ranker = ranker if ranker is not None else Ranker()
        self.scan = scan

    # --------------------------------------------------------------- time window (the bridge)
    def events_in_window(self, start_iso: str, end_iso: str, *,
                         agent: Optional[str] = None, kind: Optional[str] = None,
                         track: Optional[str] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Raw events whose `at` falls in [start, end] (inclusive), oldest-first, filtered.

        The core timeline-drill primitive: pass a Chapter/Beat span to see what actually
        happened in it. When the EventLog has a time index (Slice V1), this is a range-scan
        with TOTAL recall within retention. Without one (ledger-only / index cold), it falls
        back to a bounded replay of the newest `scan` events -- correct, but matches older
        than that horizon are not visible until the index is built (`EventLog.rebuild_index`).
        Never raises.
        """
        try:
            lo, hi = _epoch(start_iso), _epoch(end_iso)
            if lo > hi:
                lo, hi = hi, lo
            index = getattr(self.log, "index", None)
            if index is not None:
                # range-scan the read-model (all-agent firehose), then apply ALL secondary
                # filters in-window -- incl. agent, which the scan path got from the per-agent
                # stream but the index must apply explicitly.
                candidates = index.window(start_iso, end_iso)
                out = [e for e in candidates
                       if (agent is None or e.get("agent_id") == agent)
                       and self._match(e, kind=kind, track=track)]
                return out[:limit] if limit else out
            out = []
            for e in self.log.scan(agent=agent, limit=self.scan):
                if lo <= _epoch(e.get("at", "")) <= hi and self._match(e, kind=kind, track=track):
                    out.append(e)
            return out[:limit] if limit else out
        except Exception:
            return []

    # --------------------------------------------------------------- relevance search
    def search(self, query: str, *, kind: Optional[str] = None, agent: Optional[str] = None,
               track: Optional[str] = None, since: Optional[str] = None,
               until: Optional[str] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """Rank raw events by relevance to `query` within the filters, best-first.

        Empty query -> relevance contributes 0, so results fall back to recency/importance
        order (i.e. "the most recent matching events"). Never raises.
        """
        try:
            lo = _epoch(since) if since else None
            hi = _epoch(until) if until else None
            items = []
            for e in self.log.scan(agent=agent, limit=self.scan):
                if not self._match(e, kind=kind, track=track):
                    continue
                t = _epoch(e.get("at", ""))
                if lo is not None and t < lo:
                    continue
                if hi is not None and t > hi:
                    continue
                items.append(self._to_item(e))
            scored = self.ranker.rank(items, query or "", top_k=top_k)
            return [s.item["_event"] for s in scored]
        except Exception:
            return []

    def get(self, ref: str) -> Optional[Dict[str, Any]]:
        """Resolve a followable event:<stream>:<id> pointer to its raw event."""
        return self.log.get(ref)

    # --------------------------------------------------------------- internals
    @staticmethod
    def _match(e: Dict[str, Any], *, kind: Optional[str], track: Optional[str]) -> bool:
        if kind is not None and e.get("kind") != kind:
            return False
        if track is not None and e.get("track") != track:
            return False
        return True

    @staticmethod
    def _to_item(e: Dict[str, Any]) -> Dict[str, Any]:
        """Project a raw event into a Ranker item: searchable text + recency timestamp,
        carrying the original event so callers get the full record back."""
        import json
        text = " ".join([
            str(e.get("summary", "")),
            str(e.get("kind", "")),
            " ".join(str(r) for r in e.get("refs", [])),
            json.dumps(e.get("detail", {}), default=str),
        ])
        return {"text": text, "timestamp": e.get("at"), "_event": e}


_INSTANCE: Optional[EventQuery] = None


def get_event_query(event_log: Optional[EventLog] = None) -> EventQuery:
    """Module singleton (lazy). Pass `event_log` for an isolated query (tests/trial)."""
    global _INSTANCE
    if event_log is not None:
        return EventQuery(event_log)
    import os
    if os.environ.get("_AISETUP_TEST_ISOLATED"):
        return EventQuery()
    if _INSTANCE is None:
        _INSTANCE = EventQuery()
    return _INSTANCE
