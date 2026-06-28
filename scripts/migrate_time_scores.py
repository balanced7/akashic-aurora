"""
One-time migration (S5): re-score the persisted time-zsets with the unified `to_epoch`.

Why: before S5, the per-module `_epoch` helpers interpreted a NAIVE timestamp in the machine's
LOCAL zone (Eastern here -> a 5h skew). After S5 every write uses `timeutil.to_epoch` (naive ==
UTC). Existing zset SCORES were written under the old local interpretation, so a windowed query
whose bounds are now computed UTC-side would miss them (the bound and the stored score disagree
by the local offset). This re-scores the stored entries from each record's `at` via `to_epoch`,
so bounds and scores agree again.

Safe + idempotent + lossless: it only rewrites DERIVED zset scores (recomputable from the
records' immutable `at`); it never touches a beat, event, or the membership of a zset. Running it
twice yields the same scores.

Zsets re-scored:
  narr:beats:timeline          (beat_log)
  narr:track:<track>:beats     (beat_log + tag_governance)
  events:raw:tindex            (event_index)

Run:  py scripts/migrate_time_scores.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import Store, create_store
from core.foundation.timeutil import to_epoch
from core.narrative.schema import Beat, beat_key

TIMELINE = "narr:beats:timeline"
TINDEX = "events:raw:tindex"


def migrate_time_scores(store: Store = None) -> dict:
    """Re-score the persisted time-zsets from their records' `at` via to_epoch. Returns counts."""
    store = store if store is not None else create_store()
    report = {"timeline": 0, "track": 0, "tindex": 0}

    # 1. the beat timeline + each beat's entry in its current track zset
    timeline_scores = {}
    track_scores = {}                      # track -> {beat_id: score}
    for bid in store.zrange(TIMELINE, 0, -1):
        raw = store.get(beat_key(bid))
        if not raw:
            continue
        try:
            b = Beat.from_dict(json.loads(raw))
        except (ValueError, TypeError):
            continue
        score = to_epoch(b.at)
        timeline_scores[bid] = score
        if b.track:
            track_scores.setdefault(b.track, {})[bid] = score
    if timeline_scores:
        store.zadd(TIMELINE, timeline_scores)        # overwrites scores in place
        report["timeline"] = len(timeline_scores)
    for track, mapping in track_scores.items():
        store.zadd(f"narr:track:{track}:beats", mapping)
        report["track"] += len(mapping)

    # 2. the raw-event time index
    tindex_scores = {}
    for eid in store.zrange(TINDEX, 0, -1):
        raw = store.get(f"events:raw:byid:{eid}")
        if not raw:
            continue
        try:
            ev = json.loads(raw)
        except (ValueError, TypeError):
            continue
        tindex_scores[eid] = to_epoch(ev.get("at", ""))
    if tindex_scores:
        store.zadd(TINDEX, tindex_scores)
        report["tindex"] = len(tindex_scores)

    return report


if __name__ == "__main__":
    rep = migrate_time_scores()
    print(f"[migrate_time_scores] re-scored: {rep}")
