"""drift_check -- lightweight SEMANTIC drift detector over the narrative spine (prototype).

The task-ledger (core/coord) catches ILLEGAL moves: file clashes, unmet deps, unproven closes. This
catches the OTHER kind -- INCOHERENT moves: scope creep, rework, tangents -- the churn that's
technically legal but doesn't fit the story we're actually telling.

It asks the spine two cheap questions about a CANDIDATE beat (what you're about to do):
  1. SCOPE  -- does it route to the track you're in? If the TrackRouter sends it elsewhere, this
               action belongs to a different thread (you've wandered).
  2. REWORK -- is it a near-duplicate of a recent beat? If we've already told this part, skip it.
  (3. HOMELESS -- if it routes to no track at all and you have no active track, it can't be placed.)

No model in the loop -- pure routing + word-overlap, like the rest of the coordination substrate.
FAIL-OPEN: any spine error returns coherent=True, so a drift-check machinery fault never blocks work.

    v = drift_check("collapse traces into cards", task="T002", paths=["scripts/bifrost_ui.py"])
    if not v.coherent:
        print("DRIFT:", v.kind, "--", v.reason)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from core.narrative.track_router import RouteHint, get_track_router


@dataclass
class _Cand:
    """A candidate beat -- just the fields the router reads (summary/source)."""
    summary: str
    source: str = ""


@dataclass
class DriftVerdict:
    coherent: bool
    kind: str        # "" | "scope" | "rework" | "homeless"
    reason: str
    track: str


def _words(s: str) -> set:
    return {w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split() if len(w) > 2}


def _similar(a: str, b: str) -> float:
    """Jaccard word overlap -- cheap 'is this the same beat' signal."""
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


def _active_track() -> Optional[str]:
    try:
        from core.narrative.beat_log import ROUTER_ACTIVE, get_beat_log
        return get_beat_log().store.get(ROUTER_ACTIVE)
    except Exception:
        return None


def _recent_beats(limit: int = 40) -> List:
    try:
        from core.narrative.beat_log import get_beat_log
        return get_beat_log().recent(limit=limit)
    except Exception:
        return []


def drift_check(summary: str, *, source: str = "", task: str = "", paths=None, category: str = "",
                active: Optional[str] = "auto", recent_beats: Optional[List] = None,
                dup_threshold: float = 0.6, router=None) -> DriftVerdict:
    """Coherent, or drifted-because? See module docstring. Fail-open on any error."""
    try:
        router = router or get_track_router()
        if active == "auto":
            active = _active_track()
        res = router.route_one(_Cand(summary=summary, source=source),
                               RouteHint(paths=list(paths or []), category=category, task=task),
                               active=active)

        # 1. SCOPE -- routes to a different track than the one we're in
        if active and res.switched:
            return DriftVerdict(False, "scope",
                                f"routes to '{res.track}' but you're in '{active}' (by {res.basis}) "
                                f"-- this belongs to a different thread", res.track)

        # 2. HOMELESS -- can't place it in any track and there's no thread to persist into
        if res.basis == "unknown" and not active:
            return DriftVerdict(False, "homeless",
                                "routes to no track -- can't place this in the story", res.track)

        # 3. REWORK -- a near-identical beat already exists
        beats = recent_beats if recent_beats is not None else _recent_beats()
        for b in beats:
            bs = b if isinstance(b, str) else getattr(b, "summary", "")
            if _similar(summary, bs) >= dup_threshold:
                src = "" if isinstance(b, str) else getattr(b, "source", "")
                return DriftVerdict(False, "rework",
                                    f"near-duplicate of an earlier beat: '{bs[:60]}'"
                                    + (f" ({src})" if src else "") + " -- likely already done", res.track)

        return DriftVerdict(True, "", f"coheres with track '{res.track}' (by {res.basis})", res.track)
    except Exception as e:
        return DriftVerdict(True, "", f"drift-check unavailable ({e}); allowing", active or "unknown")
