"""
Primitives: cross-cutting algorithms over stored records.

Semantic Relationship: Primitives operate_on records_from Store_and_Ledger

These are shared building blocks used by more than one domain (Context pillar +
AgentMemory): they are algorithms, not persistence (that's `core.foundation`).
Built once here so the same behavior is reused, not re-implemented.

- ranker.py    : order items by relevance x importance x recency (+ relationship type)
- distiller.py : compact items into a token budget, keeping a source pointer each
- supersession.py: a newer record retires an older one (temporal correctness)
"""

from .ranker import Ranker, Scored, keyword_relevance
from .distiller import Distiller, Distillation
from . import supersession

__all__ = ["Ranker", "Scored", "keyword_relevance", "Distiller", "Distillation", "supersession"]
