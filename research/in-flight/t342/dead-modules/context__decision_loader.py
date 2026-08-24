"""
Decision loader: surface the decisions most applicable to a task, ranked.

Semantic Relationship: RelevantDecisions derived_from AgentMemory (by relevance)

Part of the Context pillar (System 4). Thin reader over AgentMemory's decisions
(ADR-style), mapped onto the Ranker so an agent sees what was already decided —
and doesn't re-reason it. Each entry carries a `source` pointer to the full record.
"""

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from core.primitives.ranker import Ranker
from core.learning.agent_memory import AgentMemory, get_agent_memory


def _text_of(d: Dict[str, Any]) -> str:
    parts = [d.get("title", ""), d.get("decision", ""), d.get("context", "")]
    parts += [str(r) for r in (d.get("rationale") or [])]
    return " ".join(p for p in parts if p)


def load_decisions_applicable_to_task(
    task: str,
    top_k: int = 5,
    *,
    agent_memory: Optional[AgentMemory] = None,
    ranker: Optional[Ranker] = None,
    now: Optional[float] = None,
    days: int = 365,
) -> List[Dict[str, Any]]:
    """
    Load the `top_k` decisions most applicable to `task`, ranked.

    Semantic Relationship: ApplicableDecisions ranked_by Relevance_Importance_Recency

    Decisions are durable semantic memory, so they carry a high base importance.
    Empty memory -> empty list (graceful).
    """
    mem = agent_memory or get_agent_memory()
    ranker = ranker or Ranker()

    items = []
    for decision in mem.get_decisions(days=days):
        d = asdict(decision)
        items.append({
            "text": _text_of(d),
            "importance": 4,                 # decisions are durable/high-value by nature
            "timestamp": d.get("created_at"),
            "source": d.get("id"),
            "_decision": d,
        })

    ranked = ranker.rank(items, query=task, now=now, top_k=top_k)
    return [
        {
            "source": s.item["source"],
            "title": s.item["_decision"].get("title", ""),
            "decision": s.item["_decision"].get("decision", ""),
            "rationale": s.item["_decision"].get("rationale", []),
            "score": round(s.score, 4),
        }
        for s in ranked
    ]
