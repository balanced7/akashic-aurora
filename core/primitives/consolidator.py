"""
Consolidator (Slice S1) -- the one engine that turns a set of records into a budgeted,
pointer-traceable summary. Extracted because three call sites were running the SAME pipeline:

    items  ->  Ranker.rank (what matters)  ->  Distiller.distill (compact + lossless pointers)

  - the Chronicler (beats -> a Chapter summary, on the TIME axis)
  - learning/consolidation (lessons -> chronicles/lessons.md, on the SOURCE axis)
  - the Curator (atoms -> a Resource summary, on the TOPIC axis)  [C5/C6, coming]

The rule of three fired, so this is now real instead of three copies. The DIFFERENCES stay with
the callers (how items are projected from their records, and what they persist the result into);
only the identical middle lives here.

Why it matters beyond DRY: this is the single point where the Ranker + Distiller (and, at C4, the
faithfulness CRITIC) are constructed. Wire the gate in here ONCE and every consumer -- chronicle,
lessons, and the Codex -- inherits it. One seam, not three.

Semantic Relationship: Summary consolidated_from Items (ranked, distilled, pointer-traceable)
"""
from typing import Any, Dict, List, Optional

from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller, Distillation


class Consolidator:
    """Rank a set of items, then distill them to a budget with lossless source pointers."""

    DEFAULT_TOKEN_BUDGET = 4000
    DEFAULT_MAX_CHARS = 170

    def __init__(self, ranker: Optional[Ranker] = None, distiller: Optional[Distiller] = None,
                 token_budget: int = DEFAULT_TOKEN_BUDGET):
        self.ranker = ranker or Ranker()
        self.distiller = distiller or Distiller(max_chars_per_entry=self.DEFAULT_MAX_CHARS)
        self.token_budget = token_budget

    @staticmethod
    def item(*, text: Any, source: Any, importance: Any = 1, timestamp: Any = None,
             relationship_type: Any = None, **extra: Any) -> Dict[str, Any]:
        """The canonical item contract every caller projects its records into. The fields the
        Ranker + Distiller read (text/importance/timestamp/source/relationship_type), plus any
        caller-specific extras passed through verbatim."""
        return {"text": text, "source": source, "importance": importance,
                "timestamp": timestamp, "relationship_type": relationship_type, **extra}

    def consolidate(self, items: List[Dict[str, Any]], *, instruction: str = "", kind: str = "",
                    now: Optional[float] = None, query: str = "") -> Distillation:
        """items (best-first not required -- the Ranker orders them) -> a Distillation. `now` is a
        unix epoch for recency; `query` empty means relevance contributes 0 (recency/importance
        order). The result's `.skeleton` is the summary; `.critic_ok`/`.dropped_sources` carry the
        faithfulness + budget signals."""
        ranked = [s.item for s in self.ranker.rank(items, query=query, now=now)]
        return self.distiller.distill(ranked, token_budget=self.token_budget,
                                      instruction=instruction, kind=kind)


_INSTANCE: Optional[Consolidator] = None


def get_consolidator() -> Consolidator:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = Consolidator()
    return _INSTANCE
