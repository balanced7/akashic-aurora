"""
BeatLog (Slice 1) -- append salient narrative Beats to the Store + read them by time.

Semantic Relationship: Beat appended_to NarrativeTimeline (time-ordered)

The first BEHAVIOR of the narrative spine: meaningful events become Beats that accrete
on a time-ordered timeline. Routing to Tracks (the TrackRouter) and rolling up into
Chapters (the Chronicler) are later slices -- here Beats are stored UNROUTED (track=None).

Storage (on the Store -- canonical, or an injected store for tests/trial mode):
    narr:beat:<id>        -> the Beat as JSON
    narr:beats:timeline   -> zset {beat_id: epoch}   (the spine; query by time window)

Best-effort by design: emit() never raises into the caller's main flow, so hooking it
into `learn`/`mirror` can't break those commands.
"""
import json
import random
from datetime import datetime
from typing import List, Optional

from core.foundation.store import Store, create_store
from core.narrative.schema import (
    Beat, Edge, beat_key, clamp_weight, DEFAULT_WEIGHT, BEAT_KINDS, validate_beat,
)

TIMELINE = "narr:beats:timeline"
ROUTER_ACTIVE = "narr:router:active"


def _epoch(iso: str) -> float:
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (ValueError, TypeError):
        return 0.0


class BeatLog:
    """Append-and-read narrative Beats on a time-ordered timeline."""

    def __init__(self, store: Optional[Store] = None):
        self.store = store if store is not None else create_store()

    def emit(self, kind: str, summary: str, source: str, *,
             weight: Optional[int] = None, at: Optional[str] = None,
             track: Optional[str] = None, themes: Optional[List[str]] = None,
             relates: Optional[List[Edge]] = None, hint=None) -> Optional[Beat]:
        """Append a Beat. Requires a followable `source` (lossless-pointer rule).
        If `track` is not given, the TrackRouter infers it from `hint`/context (Slice 2).
        Returns the Beat, or None on a refusal (no source / invalid). Never raises."""
        if not source:
            return None
        kind = kind if kind in BEAT_KINDS else "note"
        at = at or datetime.utcnow().isoformat()
        weight = clamp_weight(weight if weight is not None else DEFAULT_WEIGHT.get(kind, 1))
        bid = f"beat_{int(_epoch(at))}_{random.randint(1000, 9999)}"
        beat = Beat(id=bid, at=at, kind=kind, summary=str(summary)[:500], source=str(source),
                    weight=weight, track=track, themes=themes or [], relates=relates or [])
        if validate_beat(beat):
            return None
        if track is None:
            self._route(beat, hint, _epoch(at))   # sets beat.track + persists + indexes
        self.store.set(beat_key(bid), json.dumps(beat.to_dict()))
        self.store.zadd(TIMELINE, {bid: _epoch(at)})
        return beat

    def _route(self, beat: Beat, hint, score: float) -> None:
        """Assign the Beat to a Track (Slice 2). Best-effort -- an unrouted Beat is
        still a valid Beat, so a routing hiccup never blocks logging."""
        try:
            from core.narrative.track_router import get_track_router, RouteHint
            from core.narrative.schema import track_key, Track
            active = self.store.get(ROUTER_ACTIVE)
            res = get_track_router().route_one(beat, hint or RouteHint(), active)
            beat.track = res.track
            self.store.set(ROUTER_ACTIVE, res.track)
            self.store.zadd(f"narr:track:{res.track}:beats", {beat.id: score})
            if not self.store.get(track_key(res.track)):
                self.store.set(track_key(res.track), json.dumps(
                    Track(id=res.track, title=res.track.replace("-", " ").title(),
                          created_at=beat.at).to_dict()))
        except Exception:
            pass

    def _load(self, beat_id: str) -> Optional[Beat]:
        raw = self.store.get(beat_key(beat_id))
        if not raw:
            return None
        try:
            return Beat.from_dict(json.loads(raw))
        except (ValueError, TypeError):
            return None

    def recent(self, limit: int = 20) -> List[Beat]:
        ids = self.store.zrange(TIMELINE, 0, max(0, limit - 1), desc=True)  # newest first
        return [b for b in (self._load(i) for i in ids) if b]

    def in_window(self, start_iso: str, end_iso: str) -> List[Beat]:
        ids = self.store.zrangebyscore(TIMELINE, _epoch(start_iso), _epoch(end_iso))
        return [b for b in (self._load(i) for i in ids) if b]

    def count(self) -> int:
        return self.store.zcard(TIMELINE)


_INSTANCE: Optional[BeatLog] = None


def get_beat_log(store: Optional[Store] = None) -> BeatLog:
    """Module singleton (lazy). Pass `store` to get an isolated BeatLog (tests/trial)."""
    global _INSTANCE
    if store is not None:
        return BeatLog(store)
    if _INSTANCE is None:
        _INSTANCE = BeatLog()
    return _INSTANCE
