"""
Chapter lifecycle helpers (Slice 7) — bi-temporal stamping, in-place regeneration,
explicit supersession, and track-list hygiene.

Semantic Relationship: Chapter regenerated_from Beats (stable id) ; CorrectedChapter supersedes OldChapter

Design rules this enforces (docs/library/design/20260709_narrative-spine-design-plan-system-4-cap_2357df.md §4–5, sota-comparison):
- **Stable, deterministic ids.** A chapter regenerated from the same atoms keeps its
  id (idempotent re-runs → stable cross-references). Regenerating in place IS the
  anti-drift rule (regenerate-from-atoms), not an edit that must be preserved.
- **Bi-temporal.** `valid_from` = first time the chapter became true; `recorded_at`
  = last time it was written. Set once / refreshed on write.
- **Supersession is for real corrections only** (a *different* id replaces this one).
  It closes `valid_to`, adds a `replaces` edge, and retargets back-links — it does
  NOT fire on ordinary regenerate (that stranded old ids in the track list before).
- **Track lists stay clean.** Only active (not superseded), resolvable chapter ids,
  newest-first.
"""
import json
from datetime import datetime
from typing import List, Optional

from core.narrative.schema import Chapter, Edge, Track, chapter_key, track_key


def is_active_chapter(ch: Chapter) -> bool:
    """True when the chapter is current (its validity interval is still open)."""
    return not ch.valid_to


def active_chapters(chapters: List[Chapter]) -> List[Chapter]:
    return [ch for ch in chapters if is_active_chapter(ch)]


def load_chapter_from_store(store, chapter_id: str) -> Optional[Chapter]:
    raw = store.get(chapter_key(chapter_id))
    if not raw:
        return None
    try:
        return Chapter.from_dict(json.loads(raw))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def persist_chapter_in_place(store, chapter: Chapter, *, now: Optional[str] = None) -> Chapter:
    """Write ``chapter`` under its deterministic id, preserving bi-temporal anchors.

    ``valid_from`` is set the first time the chapter is seen and never moved;
    ``recorded_at`` is refreshed on every write. The id never changes here — a
    regenerate-from-atoms rebuild is the same logical chapter, so it stays stable
    and idempotent.
    """
    now_iso = now or datetime.utcnow().isoformat()
    existing = load_chapter_from_store(store, chapter.id)
    if existing is not None and existing.valid_from:
        chapter.valid_from = existing.valid_from           # never move the origin
    if not chapter.valid_from:
        chapter.valid_from = chapter.span_start
    # Respect a recorded_at the caller already stamped (the Chronicler stamps it from
    # its run `now`, which keeps re-runs byte-identical / idempotent). Only fall back
    # to wall-clock when none was provided.
    if not chapter.recorded_at:
        chapter.recorded_at = now_iso
    store.set(chapter_key(chapter.id), json.dumps(chapter.to_dict()))
    return chapter


def correct_chapter(store, old_id: str, new_chapter: Chapter, *, now: Optional[str] = None) -> Chapter:
    """Explicit correction: a *different*-id chapter supersedes ``old_id``.

    Closes the old chapter's validity interval, links the two with the real
    ``replaces`` / ``is_version_of`` edges (66-type vocabulary), and writes the
    replacement. History stays queryable; only the new chapter is active.
    """
    now_iso = now or datetime.utcnow().isoformat()
    old = load_chapter_from_store(store, old_id)
    if old is not None and is_active_chapter(old):
        old.valid_to = now_iso
        old.relates = list(old.relates or [])
        if not any(e.type == "replaces" and e.target == new_chapter.id for e in old.relates):
            old.relates.append(Edge("replaces", new_chapter.id))
        store.set(chapter_key(old.id), json.dumps(old.to_dict()))
        new_chapter.relates = list(new_chapter.relates or [])
        if not any(e.type == "is_version_of" and e.target == old_id for e in new_chapter.relates):
            new_chapter.relates.append(Edge("is_version_of", old_id))
    return persist_chapter_in_place(store, new_chapter, now=now_iso)


def write_learning_chapter_backlinks(store, chapter: Chapter) -> int:
    """Stamp ``narrative_chapter`` on learn:experiment records referenced by the chapter
    (the bidirectional-pointer rule: any atom knows its place in the story).

    learn:experiment:{id} is a Redis HASH (see core/learning/learning_store.py), so the
    back-link is written as hash FIELDS -- NOT a string get/set, which would raise
    WRONGTYPE on real Redis and clobber the record's other fields. Best-effort per record:
    a single bad/missing key never aborts the chronicle.
    """
    linked = 0
    for src in chapter.learnings or []:
        if not src.startswith("learn:experiment:"):
            continue
        key = src                                  # source already IS the hash key
        try:
            if not store.exists(key):
                continue
            store.hset(key, mapping={
                "narrative_chapter": chapter.id,
                "narrative_track": chapter.track or "",
            })
            linked += 1
        except Exception:
            continue
    return linked


def rebuild_track_chapter_list(store, track_id: str, current_ids: List[str]) -> Track:
    """Set a Track's chapter list to active, resolvable chapters only, newest-first.

    Merges the ids produced this run with any pre-existing ones (so a windowed
    chronicle doesn't lose earlier chapters), then drops anything that is missing
    or superseded — preventing the stale/superseded-id accumulation that would
    otherwise double-count chapters in the Atlas.
    """
    raw = store.get(track_key(track_id))
    track = None
    if raw:
        try:
            track = Track.from_dict(json.loads(raw))
        except (ValueError, TypeError, json.JSONDecodeError):
            track = None
    if track is None:
        track = Track(id=track_id, title=track_id, chapters=[])

    merged: List[str] = []
    seen = set()
    for cid in list(track.chapters or []) + list(current_ids):
        if cid in seen:
            continue
        seen.add(cid)
        ch = load_chapter_from_store(store, cid)
        if ch is not None and is_active_chapter(ch):
            merged.append(cid)

    merged.sort(
        key=lambda cid: (load_chapter_from_store(store, cid).span_start or ""),
        reverse=True,
    )
    track.chapters = merged
    store.set(track_key(track_id), json.dumps(track.to_dict()))
    return track
