"""
ThemeAssigner (Slice 5, Tier 0 heuristic) -- infer cross-cutting Themes from
keyword signals in a Beat's summary / source / hint context. Multi-label:
a single Beat can belong to many Themes (unlike TrackRouter's single-label).

Semantic Relationship: Beat member_of Theme (multi-label, inferred from keywords)

Inference: keywords in beat text + hint context -> ALL matching theme IDs.
Tier 1 (embeddings via Ranker relevance_fn seam) is a later slice.

Design pattern follows TrackRouter (keyword rules + Tier 0 heuristic first),
but multi-label instead of first-match.
"""
from typing import List, Optional, Tuple

# --- keyword tuples -> theme id ---
# Derived from real beat data analysis: 7 existing beats cluster into 6 themes.
THEME_KEYWORDS: List[Tuple[Tuple[str, ...], str]] = [
    (("trackrouter", "route", "routing", "domain switch", "active track", "ari", "windowdiff"), "routing"),
    (("beatlog", "emit", "hook", "mirror"), "logging"),
    (("test", "benchmark", "metric", "fixture", "acceptance bar", "verification"), "evaluation"),
    (("rule of three", "schema on read", "capture now", "design note", "methodology"), "design"),
    (("memory", "store", "persistence", "retrieval", "recall", "shared memory"), "memory"),
    (("chronicler", "chapter", "narrative", "atlas", "chronicle", "story", "spine"), "narrative"),
]


class ThemeAssigner:
    """Multi-label keyword-based theme inference.

    Assigns ALL matching themes (not first-match). A Beat with no keyword
    match gets an empty theme list (which is valid).
    """

    def __init__(self, keywords: Optional[List[Tuple[Tuple[str, ...], str]]] = None):
        self.keywords = keywords or THEME_KEYWORDS

    def assign(self, beat, hint=None) -> List[str]:
        """Return all theme IDs whose keywords appear in the beat's text."""
        text = self._text_of(beat, hint).lower()
        matched: List[str] = []
        for kws, theme_id in self.keywords:
            if any(kw in text for kw in kws):
                matched.append(theme_id)
        return matched

    @staticmethod
    def _text_of(beat, hint) -> str:
        parts = []
        if hasattr(beat, "summary"):
            parts.append(beat.summary or "")
        if hasattr(beat, "source"):
            parts.append(beat.source or "")
        if hint is not None:
            if hasattr(hint, "task"):
                parts.append(hint.task or "")
            if hasattr(hint, "category"):
                parts.append(hint.category or "")
            if hasattr(hint, "paths"):
                parts.extend(hint.paths or [])
        return " ".join(parts)


_INSTANCE: Optional[ThemeAssigner] = None


def get_theme_assigner() -> ThemeAssigner:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = ThemeAssigner()
    return _INSTANCE
