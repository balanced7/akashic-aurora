"""
core.narrative — the multi-domain narrative spine (System 4).

Slice 0: schema only. See docs/library/design/20260709_narrative-spine-design-plan-system-4-cap_2357df.md.
"""

from core.narrative.schema import (
    ATLAS_KEY,
    BEAT_KINDS,
    DEFAULT_WEIGHT,
    MAX_WEIGHT,
    MIN_WEIGHT,
    NARR,
    STORY_FORMAT_VERSION,
    Atlas,
    Beat,
    Chapter,
    Edge,
    Theme,
    Track,
    beat_key,
    chapter_key,
    clamp_weight,
    theme_key,
    track_key,
    valid_relationship,
    validate_beat,
    validate_edge,
)

__all__ = [
    "ATLAS_KEY",
    "BEAT_KINDS",
    "DEFAULT_WEIGHT",
    "MAX_WEIGHT",
    "MIN_WEIGHT",
    "NARR",
    "STORY_FORMAT_VERSION",
    "Atlas",
    "Beat",
    "Chapter",
    "Edge",
    "Theme",
    "Track",
    "beat_key",
    "chapter_key",
    "clamp_weight",
    "theme_key",
    "track_key",
    "valid_relationship",
    "validate_beat",
    "validate_edge",
]
