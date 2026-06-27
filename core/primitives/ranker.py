"""
Ranker: order items by relevance x importance x recency (+ relationship type)

Semantic Relationship: Ranker orders Items by Relevance (shared primitive)

A cross-cutting primitive used by BOTH the Context pillar (which items to surface
within the token budget) and AgentMemory retrieval (which past items matter). The
score is a transparent weighted blend of four signals, so callers can see *why*
something ranked where it did:

- relevance    : how well the item matches the query (keyword overlap now; swap in
                 an embedding similarity via `relevance_fn` later — the seam)
- importance   : the item's own importance (1-5); vital facts weigh more
- recency      : exponential decay by age (fresh outranks stale)
- relationship : weight by the item's relationship_type vs. what the query wants
                 (uses our 66-type vocabulary; neutral by default)

Superseded items are excluded (Supersession-aware): an item is active unless it
carries `superseded: True`. Until AgentMemory Phase B stamps that field, every
item is active, so this is safe now and "just works" later.

See docs/shared-primitives-spec.md and docs/context-compaction-skeleton-research.md.
"""

import re
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# Weighted blend of the four signals (each normalized to 0..1). Tune per caller.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "relevance": 0.4, "importance": 0.2, "recency": 0.2, "relationship": 0.2,
}


@dataclass
class Scored:
    """An item plus its score and the component breakdown (for transparency)."""
    item: Dict[str, Any]
    score: float
    components: Dict[str, float]


def keyword_relevance(text: str, query: str) -> float:
    """
    Fraction of meaningful query words present in the text (0..1).

    Semantic Relationship: Relevance derived_from KeywordOverlap

    The default relevance function. Swap in an embedding-similarity function via
    Ranker(relevance_fn=...) when embeddings land — same 0..1 contract.
    """
    qwords = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 3}
    if not qwords:
        return 0.0
    twords = set(re.findall(r"[a-z0-9]+", text.lower()))
    return len(qwords & twords) / len(qwords)


class Ranker:
    """
    Ranks items by a transparent, weighted blend of relevance/importance/recency/
    relationship, excluding superseded items.

    Semantic Relationship: Ranker scores Items using WeightedSignals
    """

    def __init__(self, *, relevance_fn: Optional[Callable[[str, str], float]] = None,
                 weights: Optional[Dict[str, float]] = None,
                 half_life_days: float = 14.0,
                 relationship_weights: Optional[Dict[str, float]] = None,
                 neutral_relationship: float = 0.5):
        self.relevance_fn = relevance_fn or keyword_relevance
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        self.half_life_days = half_life_days
        self.relationship_weights = relationship_weights or {}
        self.neutral_relationship = neutral_relationship

    @staticmethod
    def is_active(item: Dict[str, Any]) -> bool:
        """An item is active unless explicitly superseded (Supersession-aware)."""
        from core.primitives import supersession
        return supersession.is_active(item)

    def rank(self, items: List[Dict[str, Any]], query: str = "", *,
             now: Optional[float] = None, top_k: Optional[int] = None) -> List[Scored]:
        """
        Score active items and return them ordered best-first.

        Semantic Relationship: ScoredItems derived_from Items (by weighted signals)

        Args:
            items: dicts; each may carry text/importance/timestamp/relationship_type.
            query: text to match for relevance (empty -> relevance contributes 0).
            now: unix timestamp "now" (defaults to current time; pass for tests).
            top_k: cap the returned list.
        """
        now = now if now is not None else datetime.now().timestamp()
        scored: List[Scored] = []
        for item in items:
            if not self.is_active(item):
                continue
            components = {
                "relevance": self.relevance_fn(self._text_of(item), query) if query else 0.0,
                "importance": self._importance_of(item),
                "recency": self._recency_of(item, now),
                "relationship": self._relationship_of(item),
            }
            score = sum(self.weights[k] * components[k] for k in components)
            scored.append(Scored(item=item, score=score, components=components))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_k] if top_k else scored

    # ----- signal components (each returns 0..1) -----
    def _importance_of(self, item: Dict[str, Any]) -> float:
        try:
            imp = float(item.get("importance", 3))
        except (ValueError, TypeError):
            imp = 3.0
        return max(0.0, min(1.0, imp / 5.0))

    def _recency_of(self, item: Dict[str, Any], now: float) -> float:
        ts = item.get("timestamp")
        if ts is None:
            return 0.5  # unknown age -> neutral, don't punish
        try:
            t = ts if isinstance(ts, (int, float)) else datetime.fromisoformat(str(ts)).timestamp()
        except (ValueError, TypeError):
            return 0.5
        age_days = max(0.0, (now - t) / 86400.0)
        if self.half_life_days <= 0:
            return 1.0
        return math.exp(-age_days / self.half_life_days)

    def _relationship_of(self, item: Dict[str, Any]) -> float:
        rt = item.get("relationship_type")
        if rt is None:
            return self.neutral_relationship
        return self.relationship_weights.get(rt, self.neutral_relationship)

    def _text_of(self, item: Dict[str, Any]) -> str:
        """The text to match the query against: explicit 'text', else string fields."""
        if item.get("text"):
            return str(item["text"])
        return " ".join(str(v) for v in item.values() if isinstance(v, (str, int, float)))
