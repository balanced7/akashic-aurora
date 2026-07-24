"""
Learning loader: surface the learnings most relevant to a task, ranked.

Semantic Relationship: RankedLearnings derived_from LearningStore (by relevance)

Part of the Context pillar (System 4). A thin reader over `LearningStore` that maps
each learning onto the Ranker's signals and returns the top-ranked few for a task —
so an agent starts informed by the learnings that actually matter to what it's doing,
not a raw dump.

Mapping (LearningStore record -> Ranker signal):
- text         : experiment_name + category + what_tried + recommendation (for relevance)
- importance   : derived from confidence (high=5/medium=3/low=2), +1 if it succeeded,
                 -1 if it failed (a proven win or a known failure weighs more than a maybe)
- timestamp    : the learning's timestamp (recency)
- source       : the experiment_name -> a POINTER back to the full record in the
                 LearningStore (lossy view + lossless pointer; see the research doc)

See docs/library/design/20260709_context-pillar-system-4-design-consolida_89733b.md and docs/library/design/20260619_shared-primitives-interface-spec_03e098.md.
"""

import os
from typing import Any, Dict, List, Optional

from core.primitives.ranker import Ranker
from core.learning.learning_store import LearningStore, get_learning_store_instance, is_graduated


def load_learnings_for_boot(task: str, *, learning_store: Optional[LearningStore] = None,
                            now: Optional[float] = None,
                            cap_chars: Optional[int] = None) -> List[Dict[str, Any]]:
    """T071-R1 boot door: MOST-RELEVANT lessons under the fixed relevance budget
    (context/relevance_budget.py; deepseek Part 5 governs). Kill switch R1-d:
    AKASHIC_RELEVANCE_BUDGET=0 serves the legacy recency/Ranker selection, same
    entry shape. Fail-open: any budget-path error falls back to legacy too."""
    if os.getenv("AKASHIC_RELEVANCE_BUDGET", "1") != "0":
        try:
            from context import relevance_budget as rb
            store = learning_store or get_learning_store_instance()
            return rb.select_within_budget(store, task, cap_chars=cap_chars, now=now)
        except Exception:
            pass
    return load_learnings_ranked_by_relevance(
        task, top_k=8, learning_store=learning_store, now=now)

# confidence -> base importance (1..5)
_CONFIDENCE_IMPORTANCE = {"high": 5, "medium": 3, "low": 2}


def _importance_of(learning: Dict[str, Any]) -> int:
    base = _CONFIDENCE_IMPORTANCE.get(str(learning.get("confidence", "medium")).lower(), 3)
    success = str(learning.get("success", "")).lower()
    if success == "yes":
        base = min(5, base + 1)   # a proven win is worth surfacing
    elif success == "no":
        base = max(1, base - 1)   # a known failure still matters, slightly less
    return base


def _text_of(learning: Dict[str, Any]) -> str:
    parts = [
        learning.get("experiment_name", ""),
        learning.get("category", ""),
        learning.get("what_tried", ""),
        learning.get("recommendation", ""),
    ]
    return " ".join(p for p in parts if p)


def load_learnings_ranked_by_relevance(
    task: str,
    top_k: int = 5,
    *,
    learning_store: Optional[LearningStore] = None,
    ranker: Optional[Ranker] = None,
    now: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Load the `top_k` learnings most relevant to `task`, ranked.

    Semantic Relationship: RelevantLearnings ranked_by Relevance_Importance_Recency

    Returns presentable, traceable entries (each carries a `source` pointer back to
    the full LearningStore record). An empty store -> empty list (graceful).
    """
    store = learning_store or get_learning_store_instance()
    ranker = ranker or Ranker()

    learnings = store.load_all_learnings_from_store()
    items = [
        {
            "text": _text_of(l),
            "importance": _importance_of(l),
            "timestamp": l.get("timestamp"),
            "source": l.get("experiment_name"),
            "_learning": l,
        }
        for l in learnings
        # graduated = rule enforced by automation now; boot's ranked slots go to live knowledge
        if not is_graduated(l)
    ]

    ranked = ranker.rank(items, query=task, now=now, top_k=top_k)

    results: List[Dict[str, Any]] = []
    for s in ranked:
        l = s.item["_learning"]
        results.append({
            "source": s.item["source"],            # pointer to the full record
            "recommendation": l.get("recommendation", ""),
            "what_tried": l.get("what_tried", ""),
            "success": l.get("success", ""),
            "confidence": l.get("confidence", ""),
            "category": l.get("category", ""),
            "score": round(s.score, 4),
        })
    return results
