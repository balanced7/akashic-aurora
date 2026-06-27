"""
Chapter lifecycle helpers (Slice 7) — bi-temporal supersession + active filtering.

Semantic Relationship: NewChapter supersedes OldChapter (valid_to interval closes)

Chapters are never deleted; a corrected rebuild stamps ``valid_to`` on the old
record and links the replacement with a ``replaces`` edge (66-type vocabulary).
"""
import hashlib
import json
from datetime import datetime
from typing import List, Optional

from core.narrative.schema import Chapter, Edge, chapter_key


def is_active_chapter(ch: Chapter) -> bool:
    """True when the chapter is current (not superseded)."""
    return not ch.valid_to


def active_chapters(chapters: List[Chapter]) -> List[Chapter]:
    return [ch for ch in chapters if is_active_chapter(ch)]


def supersede_chapter(old: Chapter, new_id: str, now: Optional[str] = None) -> Chapter:
    """Close the validity interval on ``old`` and point to its replacement."""
    now_iso = now or datetime.utcnow().isoformat()
    old.valid_to = now_iso
    old.relates = list(old.relates or [])
    if not any(e.type == "replaces" and e.target == new_id for e in old.relates):
        old.relates.append(Edge("replaces", new_id))
    return old


def chapter_content_fingerprint(ch: Chapter) -> str:
    """Stable fingerprint for detecting material chapter changes."""
    return "|".join([
        ch.track or "",
        ch.title or "",
        ch.summary or "",
        ",".join(ch.beats or []),
    ])


def load_chapter_from_store(store, chapter_id: str) -> Optional[Chapter]:
    raw = store.get(chapter_key(chapter_id))
    if not raw:
        return None
    try:
        return Chapter.from_dict(json.loads(raw))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def persist_chapter_with_supersession(
    store,
    chapter: Chapter,
    *,
    now: Optional[str] = None,
) -> Chapter:
    """Write ``chapter``; supersede an existing active chapter at the same id if content changed."""
    now_iso = now or datetime.utcnow().isoformat()
    existing = load_chapter_from_store(store, chapter.id)
    if existing and is_active_chapter(existing):
        if chapter_content_fingerprint(existing) != chapter_content_fingerprint(chapter):
            raw = f"{chapter.id}_superseded_{now_iso}"
            new_id = f"{chapter.id}_v{hashlib.md5(raw.encode()).hexdigest()[:8]}"
            supersede_chapter(existing, new_id, now=now_iso)
            store.set(chapter_key(existing.id), json.dumps(existing.to_dict()))
            d = chapter.to_dict()
            d["id"] = new_id
            chapter = Chapter.from_dict(d)
            chapter.relates = list(chapter.relates or [])
            chapter.relates.append(Edge("is_version_of", existing.id))
            chapter.recorded_at = now_iso
    if not chapter.valid_from:
        chapter.valid_from = chapter.span_start
    if not chapter.recorded_at:
        chapter.recorded_at = now_iso
    store.set(chapter_key(chapter.id), json.dumps(chapter.to_dict()))
    return chapter


def write_learning_chapter_backlinks(store, chapter: Chapter) -> int:
    """Stamp ``narrative_chapter`` on learn:experiment records referenced by the chapter."""
    linked = 0
    for src in chapter.learnings or []:
        if not src.startswith("learn:experiment:"):
            continue
        exp = src.split("learn:experiment:", 1)[-1]
        key = f"learn:experiment:{exp}"
        raw = store.get(key)
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rec["narrative_chapter"] = chapter.id
        rec["narrative_track"] = chapter.track
        store.set(key, json.dumps(rec))
        linked += 1
    return linked
