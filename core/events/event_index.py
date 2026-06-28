"""
EventIndex (Slice V1) -- a Store-backed time index over the raw event firehose.

Semantic Relationship: RawEvents indexed_by Time (queryable read-model)

WHY: the EventLog writes raw events to an append-only Ledger (the system of record). Reading a
time WINDOW off the Ledger meant replaying the whole stream and keeping only the newest `scan`
events -- which silently dropped older matches (false "recall=100%") and cost O(n) per query.

This is the read-model that fixes it (a CQRS projection): on capture, the event's `at`-epoch ->
its id goes into a zset, and the payload into a per-id key. A window query is then a
`zrangebyscore` range-scan (O(log n + k), k = window size) -- recall is total within retention,
and latency is flat as the firehose grows.

  events:raw:tindex        zset  {event_id: at_epoch}     -- the queryable index
  events:raw:byid:<id>     str   event JSON               -- O(1) payload resolution

The Ledger stays the durable system of record AND the rebuild source: `rebuild()` replays it back
into the index, so a lost/cold index (or pre-existing events captured before V1) self-heals.

Bounded in lockstep with the firehose (CANONICAL_MAXLEN): each add evicts the oldest entries by
score so the index can't outgrow the stream it indexes. Best-effort throughout -- an index hiccup
must never break capture (the Ledger write already succeeded; the event is safe and re-indexable).
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from core.foundation.store import Store, create_store

logger = logging.getLogger("event_index")

TINDEX = "events:raw:tindex"
BYID_PREFIX = "events:raw:byid:"
DEFAULT_MAXLEN = 100_000          # match the firehose (event_log.CANONICAL_MAXLEN)


def _epoch(iso) -> float:
    try:
        return datetime.fromisoformat(str(iso)).timestamp()
    except (ValueError, TypeError):
        return 0.0


def byid_key(event_id: str) -> str:
    return f"{BYID_PREFIX}{event_id}"


class EventIndex:
    """A time-ordered, range-queryable projection of the raw firehose, on the Store."""

    def __init__(self, store: Optional[Store] = None, *, maxlen: int = DEFAULT_MAXLEN):
        self.store = store if store is not None else create_store()
        self.maxlen = maxlen

    # ------------------------------------------------------------------ write
    def add(self, event: Dict[str, Any]) -> bool:
        """Index one captured event (must carry `id` + `at`). Best-effort -- returns
        True if indexed, False on any refusal/hiccup. NEVER raises."""
        try:
            eid = str(event.get("id") or "")
            if not eid:
                return False
            score = _epoch(event.get("at", ""))
            self.store.set(byid_key(eid), json.dumps(event))
            self.store.zadd(TINDEX, {eid: score})
            self._trim()
            return True
        except Exception as e:
            logger.warning(f"index add failed (ignored): {type(e).__name__}: {e}")
            return False

    def _trim(self) -> None:
        """Keep the index bounded to `maxlen`, evicting the oldest (lowest score) ids and
        their payload keys in lockstep -- so byid never leaks past the index."""
        try:
            n = self.store.zcard(TINDEX)
            overflow = n - self.maxlen
            if overflow <= 0:
                return
            evict = self.store.zrange(TINDEX, 0, overflow - 1)   # oldest by score
            if not evict:
                return
            self.store.delete(*[byid_key(e) for e in evict])
            self.store.zrem(TINDEX, *evict)
        except Exception:
            pass

    # ------------------------------------------------------------------ read
    def window(self, start_iso: str, end_iso: str, *,
               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Every indexed event whose `at` is in [start, end] (inclusive), OLDEST-first.

        Total recall within retention (the bug this fixes): a range-scan, not a capped
        replay. Returns [] on any hiccup. `limit` keeps the EARLIEST `limit` (window order).
        """
        try:
            lo, hi = _epoch(start_iso), _epoch(end_iso)
            if lo > hi:
                lo, hi = hi, lo
            ids = self.store.zrangebyscore(TINDEX, lo, hi)        # ascending by score
            out: List[Dict[str, Any]] = []
            for eid in ids:
                ev = self.get(eid)
                if ev is not None:
                    out.append(ev)
                if limit is not None and len(out) >= limit:
                    break
            return out
        except Exception:
            return []

    def get(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Resolve one event's payload by id (O(1)). None if absent/corrupt."""
        raw = self.store.get(byid_key(str(event_id)))
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    def count(self) -> int:
        try:
            return self.store.zcard(TINDEX)
        except Exception:
            return 0

    # ------------------------------------------------------------------ heal
    def rebuild(self, events: Iterable[Dict[str, Any]]) -> int:
        """(Re)build the index from a full event replay -- backfills events captured before
        the index existed, or repopulates a cold/lost index. Idempotent: re-adding an event
        overwrites its entry, never duplicates (zset member = id). Returns count indexed."""
        n = 0
        for ev in events:
            if self.add(ev):
                n += 1
        return n
