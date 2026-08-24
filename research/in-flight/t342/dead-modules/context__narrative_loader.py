"""
Narrative loader (Slice 7) — recent Atlas + active chapters for agent boot context.

Semantic Relationship: NarrativeSummary loaded_from ChronicleStore (active chapters only)
"""
import json
from typing import Any, Dict, List, Optional

from core.narrative.schema import ATLAS_KEY, Atlas, Chapter, Track, chapter_key, track_key
from core.narrative.chapter_lifecycle import is_active_chapter, load_chapter_from_store


def load_recent_narrative_for_boot(
    store=None,
    *,
    max_chapters: int = 5,
    max_chars: int = 2400,
) -> Optional[Dict[str, Any]]:
    """Compact recent narrative for ``boot`` — active chapters only, newest first."""
    if store is None:
        from core.foundation.store import create_store
        store = create_store()

    raw_atlas = store.get(ATLAS_KEY)
    if not raw_atlas:
        return None
    try:
        atlas = Atlas.from_dict(json.loads(raw_atlas))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    chapters: List[Chapter] = []
    for tid in atlas.tracks:
        tr_raw = store.get(track_key(tid))
        if not tr_raw:
            continue
        try:
            track = Track.from_dict(json.loads(tr_raw))
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
        for cid in reversed(track.chapters or []):
            ch = load_chapter_from_store(store, cid)
            if ch and is_active_chapter(ch):
                chapters.append(ch)

    chapters.sort(key=lambda c: c.span_start or "", reverse=True)
    chapters = chapters[:max_chapters]

    if not chapters:
        return {
            "source": ATLAS_KEY,
            "summary": atlas.summary or "No active chapters yet.",
            "tracks": atlas.tracks,
            "chapters": [],
        }

    lines = [f"Atlas: {atlas.summary or '; '.join(atlas.tracks)}"]
    used = len(lines[0])
    picked: List[Dict[str, Any]] = []
    for ch in chapters:
        line = f"- [{ch.track}] {ch.title} ({ch.span_start[:10] if ch.span_start else '?'})"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
        picked.append({
            "id": ch.id,
            "track": ch.track,
            "title": ch.title,
            "span_start": ch.span_start,
            "source": chapter_key(ch.id),
        })

    return {
        "source": ATLAS_KEY,
        "summary": "\n".join(lines),
        "tracks": atlas.tracks,
        "chapters": picked,
        "generated_at": atlas.generated_at,
    }
