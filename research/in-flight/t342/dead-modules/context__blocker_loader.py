"""
Blocker loader: surface the active blockers preventing progress, ranked.

Semantic Relationship: ActiveBlockers derived_from ProjectContext (by severity/relevance)

Part of the Context pillar (System 4). Thin reader over the project context's active
blockers, mapped onto the Ranker (severity drives importance) so an agent sees what's
in the way. Each entry carries a `source` pointer to the full blocker record.
"""

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from core.primitives.ranker import Ranker

# severity -> importance (1..5)
_SEVERITY_IMPORTANCE = {"critical": 5, "high": 4, "medium": 3, "low": 2}


def load_blockers_preventing_progress(
    task: str = "",
    top_k: int = 10,
    *,
    context_manager: Any = None,
    ranker: Optional[Ranker] = None,
    now: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Load active blockers, ranked by severity x recency (x relevance to `task`).

    Semantic Relationship: Blockers prevent Progress (surfaced for awareness)

    No active blockers -> empty list (graceful).
    """
    if context_manager is None:
        from context.project_context import get_project_context_manager_instance
        context_manager = get_project_context_manager_instance()
    ranker = ranker or Ranker()

    items = []
    for blocker in context_manager.load_blockers_filtered_by_status(status="active"):
        b = asdict(blocker)
        items.append({
            "text": b.get("description", ""),
            "importance": _SEVERITY_IMPORTANCE.get(str(b.get("severity", "medium")).lower(), 3),
            "timestamp": b.get("created_at"),
            "source": b.get("id"),
            "_blocker": b,
        })

    ranked = ranker.rank(items, query=task, now=now, top_k=top_k)
    return [
        {
            "source": s.item["source"],
            "description": s.item["_blocker"].get("description", ""),
            "severity": s.item["_blocker"].get("severity", ""),
            "score": round(s.score, 4),
        }
        for s in ranked
    ]
