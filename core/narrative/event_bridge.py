"""
EventBridge (Slice 4) -- join the narrative timeline to the raw event firehose.

Semantic Relationship: NarrativeSpan resolved_to RawEvents (timeline drill-down)

The narrative answers "what was salient, and when" (Beats / Chapters). This bridge lets an
agent standing on a point in the story drill DOWN into the un-distilled record: given a
Chapter (which has a span), a Beat (a point in time), or a bare timestamp, return the raw
events underneath it -- "what actually happened, and how".

Layering: this is System 4. It may import BOTH the narrative schema (same layer) and the
domain EventQuery (lower) -- which is exactly why span->events resolution lives HERE and
not in core/events (a domain primitive must not depend upward on the narrative).
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from core.foundation.store import Store, create_store
from core.events.event_query import EventQuery, get_event_query

DEFAULT_WINDOW_SECONDS = 1800   # +/- 30 min around a point (Beat / timestamp)


def _parse_iso(s) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def parse_window(spec, default: int = DEFAULT_WINDOW_SECONDS) -> int:
    """Human window spec -> seconds. '45s' / '30m' / '2h' / '1d' / '900' (bare = seconds)."""
    if spec is None:
        return default
    s = str(spec).strip().lower()
    unit = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        if s and s[-1] in unit:
            return max(0, int(float(s[:-1]) * unit[s[-1]]))
        return max(0, int(float(s)))
    except (ValueError, TypeError):
        return default


def resolve_span(ref: str, *, store: Store,
                 window_seconds: int = DEFAULT_WINDOW_SECONDS) -> Optional[Tuple[str, str]]:
    """Resolve a chapter id / beat id / ISO timestamp to an (start_iso, end_iso) span.

    - chapter id -> its [span_start, span_end] (open chapter -> end = now)
    - beat id    -> beat.at +/- window
    - ISO ts     -> ts +/- window
    Returns None if `ref` resolves to none of these.
    """
    from core.narrative.schema import Chapter, Beat, chapter_key, beat_key

    raw = store.get(chapter_key(ref))
    if raw:
        try:
            ch = Chapter.from_dict(json.loads(raw))
            if ch.span_start:
                return ch.span_start, (ch.span_end or datetime.utcnow().isoformat())
        except (ValueError, TypeError, KeyError):
            pass

    raw = store.get(beat_key(ref))
    if raw:
        try:
            b = Beat.from_dict(json.loads(raw))
            t = _parse_iso(b.at)
            if t:
                return _around(t, window_seconds)
        except (ValueError, TypeError, KeyError):
            pass

    t = _parse_iso(ref)
    if t:
        return _around(t, window_seconds)
    return None


def _around(t: datetime, window_seconds: int) -> Tuple[str, str]:
    return ((t - timedelta(seconds=window_seconds)).isoformat(),
            (t + timedelta(seconds=window_seconds)).isoformat())


def events_around(ref: str, *, store: Optional[Store] = None,
                  window_seconds: int = DEFAULT_WINDOW_SECONDS,
                  kind: Optional[str] = None, agent: Optional[str] = None,
                  track: Optional[str] = None, limit: Optional[int] = None,
                  event_query: Optional[EventQuery] = None) -> Dict[str, Any]:
    """The raw events under a chapter / beat / timestamp. Returns {span, events}. Never raises."""
    try:
        store = store if store is not None else create_store()
        eq = event_query if event_query is not None else get_event_query()
        span = resolve_span(ref, store=store, window_seconds=window_seconds)
        if span is None:
            return {"span": None, "events": []}
        start, end = span
        events = eq.events_in_window(start, end, kind=kind, agent=agent, track=track, limit=limit)
        return {"span": {"start": start, "end": end}, "events": events}
    except Exception:
        return {"span": None, "events": []}


def raw_for_beat(beat_id: str, *, store: Optional[Store] = None,
                 window_seconds: int = DEFAULT_WINDOW_SECONDS,
                 event_query: Optional[EventQuery] = None) -> Dict[str, Any]:
    """A Beat's own raw atom (if its `source` is an event: pointer) PLUS the raw events
    around its time. Returns {atom, span, events}. Never raises."""
    try:
        store = store if store is not None else create_store()
        eq = event_query if event_query is not None else get_event_query()
        atom = None
        from core.narrative.schema import Beat, beat_key
        raw = store.get(beat_key(beat_id))
        if raw:
            try:
                b = Beat.from_dict(json.loads(raw))
                if str(b.source).startswith("event:"):
                    atom = eq.get(b.source)
            except (ValueError, TypeError, KeyError):
                pass
        around = events_around(beat_id, store=store, window_seconds=window_seconds, event_query=eq)
        return {"atom": atom, **around}
    except Exception:
        return {"atom": None, "span": None, "events": []}
