"""
TagGovernor (Slice G1) -- the append-only, confidence-gated re-tag write path.

What the prior art taught us this is:

- **A CRDT.** The tag store is a confidence-ordered register over an append-only
  multi-value history (an MV-Register that keeps every opinion, plus a survivorship
  resolver). The resolver -- `current = max by (confirmed, confidence, recency)` -- is a
  join over a lattice, which is **idempotent, commutative, and associative**. Therefore
  re-running cleanup any number of times, in any order, CONVERGES to the same current tag
  and can never degrade it. That is the formal version of "successive runs can't lose
  data." [CRDTs: Shapiro et al.]
- **MDM golden-record survivorship.** Each beat's track is a field whose value "survives"
  by a trust-based rule (basis->confidence) with a recency tie-break and a human/confirmed
  source-priority override -- exactly attribute-level survivorship. [MDM golden record]
- **Truth discovery** says the per-source trust should ultimately be *learned* from where
  sources agree/disagree, not hand-set -- that's Slice G3 (the label model). G1 uses the
  fixed `basis->confidence` table as the baseline.

Safety invariants enforced here:
  I1 immutability -- re-tagging MOVES a beat's track-index membership + updates its cached
     `track`, but NEVER deletes the beat or its raw event (facts are sacred).
  I2 monotonicity -- a lower-confidence record cannot change `current` away from a higher /
     confirmed one (the survivorship max is the gate; no explicit gate needed).
  I3 append-only -- every opinion is appended; nothing is overwritten.
  I4 reversibility -- rollback re-asserts a prior value by appending (history preserved).
"""
import json
from typing import Optional, Tuple

from core.foundation.store import Store, create_store
from core.narrative.schema import Beat, Track, beat_key, track_key
from core.narrative.tagging import TagHistory


from core.foundation.timeutil import to_epoch as _epoch   # unified tz-safe epoch (S5)


class TagGovernor:
    def __init__(self, store: Optional[Store] = None):
        self.store = store if store is not None else create_store()

    def _load(self, beat_id: str) -> Optional[Beat]:
        raw = self.store.get(beat_key(beat_id))
        if not raw:
            return None
        try:
            return Beat.from_dict(json.loads(raw))
        except (ValueError, TypeError):
            return None

    def _apply(self, beat: Beat, hist: TagHistory, at: str) -> Tuple[bool, str]:
        """Persist the (possibly updated) history; if current changed, move the track
        index. Facts untouched. Returns (changed, current)."""
        before = beat.track
        after = hist.current_value(default=before or "unknown")
        beat.tag_history = hist.to_list()
        beat.track = after
        self.store.set(beat_key(beat.id), json.dumps(beat.to_dict()))   # opinion update only
        if after != before:
            self._move_index(beat.id, before, after, _epoch(at))
        return (after != before, after)

    def record(self, beat_id: str, value: str, *, source: str = "unknown", at: str,
               confidence: Optional[float] = None, confirmed: bool = False) -> Tuple[bool, Optional[str]]:
        """Append a tag opinion (append-only). `current` changes ONLY if this opinion wins
        the survivorship max -- so a low-confidence record can't override a high/confirmed
        one. Returns (changed, current_value)."""
        beat = self._load(beat_id)
        if beat is None:
            return (False, None)
        hist = TagHistory.from_list(beat.tag_history)
        hist.add(value, source=source, at=at, confidence=confidence, confirmed=confirmed)
        return self._apply(beat, hist, at)

    def confirm(self, beat_id: str, value: str, *, at: str) -> Tuple[bool, Optional[str]]:
        """A human/agent pin: confirmed, confidence 1.0. Auto-records can never override it."""
        return self.record(beat_id, value, source="human", at=at, confirmed=True)

    def rollback(self, beat_id: str, value: str, *, at: str) -> Tuple[bool, Optional[str]]:
        """Undo a bad auto-tag: re-assert a PRIOR value (append-only, pinned). I4."""
        beat = self._load(beat_id)
        if beat is None:
            return (False, None)
        hist = TagHistory.from_list(beat.tag_history)
        if hist.rollback_to(value, at=at) is None:
            return (False, hist.current_value(default=beat.track))
        return self._apply(beat, hist, at)

    def current(self, beat_id: str) -> Optional[str]:
        beat = self._load(beat_id)
        if beat is None:
            return None
        return TagHistory.from_list(beat.tag_history).current_value(default=beat.track or "unknown")

    def _move_index(self, beat_id: str, old_track: Optional[str], new_track: Optional[str],
                    score: float) -> None:
        """Move the beat between per-track indexes. NEVER deletes the beat itself (I1)."""
        if old_track:
            self.store.zrem(f"narr:track:{old_track}:beats", beat_id)
        if new_track:
            self.store.zadd(f"narr:track:{new_track}:beats", {beat_id: score})
            if not self.store.get(track_key(new_track)):
                self.store.set(track_key(new_track), json.dumps(
                    Track(id=new_track, title=new_track.replace("-", " ").title(),
                          created_at="").to_dict()))


_INSTANCE: Optional[TagGovernor] = None


def get_tag_governor(store: Optional[Store] = None) -> TagGovernor:
    global _INSTANCE
    if store is not None:
        return TagGovernor(store)
    if _INSTANCE is None:
        _INSTANCE = TagGovernor()
    return _INSTANCE
