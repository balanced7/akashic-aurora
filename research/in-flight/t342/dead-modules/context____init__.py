"""
Context Intelligence System (SYSTEM 4 - To Be Built)

Semantic Relationship: Context enables agents to start informed

Purpose: Load 8-10k tokens of rich, useable context for agents.

Built so far:
- project_context.py: ProjectContextManager — project state (architecture,
  milestones, tasks, blockers, current work) persisted through a Store; assembles
  the layered re-priming context. (Migrated here from root 2026-06-20.)

Components (still to build):
- briefing_loader.py: load_briefing_from_previous_handoff()
- decision_loader.py: load_decisions_applicable_to_task()
- learning_loader.py: load_learnings_ranked_by_relevance()
- blocker_loader.py: load_blockers_preventing_progress()
- ranker.py: rank_by_relevance_importance_recency() (shared primitive)
- summarizer.py / distiller: summarize_to_fit_token_budget() (shared primitive)
- aggregator.py: assemble_context_from_all_sources()
- quality_scorer.py: score_context_quality_percentage()

All functions use semantic naming with relationship types.
"""

from .project_context import (  # noqa: F401
    ProjectContextManager,
    get_project_context_manager_instance,
)
from .learning_loader import load_learnings_ranked_by_relevance  # noqa: F401
from .decision_loader import load_decisions_applicable_to_task  # noqa: F401
from .blocker_loader import load_blockers_preventing_progress  # noqa: F401
from .briefing_loader import load_briefing_from_previous_handoff  # noqa: F401
from .aggregator import assemble_context  # noqa: F401

__all__ = [
    "ProjectContextManager",
    "get_project_context_manager_instance",
    "load_learnings_ranked_by_relevance",
    "load_decisions_applicable_to_task",
    "load_blockers_preventing_progress",
    "load_briefing_from_previous_handoff",
    "assemble_context",
]
