"""
core.narrative — the multi-domain narrative spine (System 4).

Slice 0: schema only. See docs/narrative-spine-plan.md.
"""
from core.narrative.schema import (
    Beat, Chapter, Track, Theme, Atlas, Edge,
    BEAT_KINDS, DEFAULT_WEIGHT, MIN_WEIGHT, MAX_WEIGHT, clamp_weight,
    valid_relationship, validate_beat, validate_edge,
    beat_key, chapter_key, track_key, theme_key, ATLAS_KEY, NARR,
    STORY_FORMAT_VERSION,
)

__all__ = [
    "Beat", "Chapter", "Track", "Theme", "Atlas", "Edge",
    "BEAT_KINDS", "DEFAULT_WEIGHT", "MIN_WEIGHT", "MAX_WEIGHT", "clamp_weight",
    "valid_relationship", "validate_beat", "validate_edge",
    "beat_key", "chapter_key", "track_key", "theme_key", "ATLAS_KEY", "NARR",
    "STORY_FORMAT_VERSION",
]
