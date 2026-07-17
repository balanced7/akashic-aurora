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
import os
import random
from datetime import datetime
from typing import List, Optional

from core.foundation.store import Store, create_store
from core.narrative.schema import (
    Beat, Edge, beat_key, clamp_weight, DEFAULT_WEIGHT, BEAT_KINDS, validate_beat,
)

TIMELINE = "narr:beats:timeline"
ROUTER_ACTIVE = "narr:router:active"


from core.foundation.timeutil import to_epoch as _epoch   # unified tz-safe epoch (S5)


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
        # `themes=None` means "infer at write time" (the assign-at-write rule, like the
        # TrackRouter); an explicit list (incl. []) is honored verbatim.
        explicit_themes = themes is not None
        beat = Beat(id=bid, at=at, kind=kind, summary=str(summary)[:500], source=str(source),
                    weight=weight, track=track, themes=list(themes) if themes else [],
                    relates=relates or [])
        if validate_beat(beat):
            return None
        if track is None:
            self._route(beat, hint, _epoch(at))   # sets beat.track + persists + indexes
        if not explicit_themes:
            self._assign_themes(beat, hint)        # multi-label themes inferred from context
        self.store.set(beat_key(bid), json.dumps(beat.to_dict()))
        self.store.zadd(TIMELINE, {bid: _epoch(at)})
        return beat

    def _assign_themes(self, beat: Beat, hint) -> None:
        """Infer cross-cutting Themes for a Beat (Slice 5). Best-effort -- a Beat with
        no themes is still valid, so a hiccup never blocks logging."""
        try:
            # V6c: embedding themes are opt-in.  Choose the default keyword assigner
            # without importing theme_discovery: that module eagerly imports NumPy,
            # and FastMCP executes sync tools on its stdio event-loop thread.  A cold
            # import there blocked a fresh `log` response past the client timeout.
            # The explicit opt-in path is unchanged.
            embed_on = os.getenv("AKASHIC_EMBED_THEMES", "").lower() in (
                "1", "true", "yes", "on",
            )
            if embed_on:
                from core.narrative.theme_discovery import select_theme_assigner
                assigner = select_theme_assigner()
            else:
                from core.narrative.theme_assigner import get_theme_assigner
                assigner = get_theme_assigner()
            beat.themes = assigner.assign(beat, hint)
        except Exception:
            from core.narrative.health import bump
            bump(self.store, "theme:error")

    def _route(self, beat: Beat, hint, score: float) -> None:
        """Assign the Beat to a Track (Slice 2). Best-effort -- an unrouted Beat is
        still a valid Beat, so a routing hiccup never blocks logging."""
        try:
            from core.narrative.track_router import get_track_router, RouteHint
            from core.narrative.schema import track_key, Track
            active = self.store.get(ROUTER_ACTIVE)
            res = get_track_router().route_one(beat, hint or RouteHint(), active)
            beat.track = res.track
            # G1: seed the tag-history with the router's decision (basis -> confidence),
            # so every beat carries an auditable, governable opinion from the start.
            from core.narrative.tagging import TagHistory
            h = TagHistory()
            h.add(res.track, source=res.basis, at=beat.at)
            beat.tag_history = h.to_list()
            self.store.set(ROUTER_ACTIVE, res.track)
            self.store.zadd(f"narr:track:{res.track}:beats", {beat.id: score})
            if not self.store.get(track_key(res.track)):
                self.store.set(track_key(res.track), json.dumps(
                    Track(id=res.track, title=res.track.replace("-", " ").title(),
                          created_at=beat.at).to_dict()))
            from core.narrative.health import bump
            bump(self.store, f"route:{res.basis}")   # observable: which signal routed this beat
        except Exception:
            from core.narrative.health import bump
            bump(self.store, "route:error")          # a silent routing failure now leaves a trace

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


def reset_beat_log_singleton() -> None:
    """Clear the module singleton (tests only)."""
    global _INSTANCE
    _INSTANCE = None


def get_beat_log(store: Optional[Store] = None) -> BeatLog:
    """Module singleton (lazy). Pass `store` to get an isolated BeatLog (tests/trial).

    When ``_AISETUP_TEST_ISOLATED`` is set (see tests/isolate_canonical.py), never
    cache a singleton — each call uses a fresh Store so subprocess CLI tests cannot
    pollute canonical db 0.
    """
    global _INSTANCE
    if store is not None:
        return BeatLog(store)
    if os.environ.get("_AISETUP_TEST_ISOLATED"):
        return BeatLog(create_store())
    if _INSTANCE is None:
        _INSTANCE = BeatLog()
    return _INSTANCE
