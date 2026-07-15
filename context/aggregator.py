"""
Aggregator: assemble the agent's starting context within a token budget.

Semantic Relationship: AssembledContext aggregated_from AllLoaders (within budget)

The Context pillar's one public entrypoint. It calls each loader (briefing /
decisions / learnings / blockers / project state), then fits the result to a hard
token budget — because "context rot" means more tokens is *worse*, so the budget is
a feature (see docs/context-compaction-skeleton-research.md).

This is the *assembly* stage: rank (in the loaders) + budget-trim here. It does NOT
yet LLM-summarize — that's the Distiller (Wave 3). Every entry keeps its `source`
pointer, so the assembled block is fully traceable back to the raw records.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from core.primitives.distiller import Distiller
from context.learning_loader import load_learnings_for_boot
from context.decision_loader import load_decisions_applicable_to_task
from context.blocker_loader import load_blockers_preventing_progress
from context.briefing_loader import load_briefing_from_previous_handoff
from context.narrative_loader import load_recent_narrative_for_boot

# Fraction of the token budget allotted to each section (high-signal first).
SECTION_BUDGET_FRACTION = {
    "briefing": 0.12,
    "narrative": 0.13,
    "decisions": 0.20,
    "learnings": 0.25,
    "blockers": 0.10,
    "project_state": 0.15,
}


def _estimate_tokens(obj: Any) -> int:
    """Rough token estimate (~4 chars/token). Good enough pre-Distiller."""
    return max(1, len(json.dumps(obj, default=str)) // 4)


def _fit_to_budget(sections: Dict[str, Any], token_budget: int) -> tuple:
    """Trim each section to its share of the budget; list sections drop lowest-ranked
    entries first (they arrive ranked best-first). Returns (sections, approx_tokens)."""
    fitted: Dict[str, Any] = {}
    total = 0
    for name, content in sections.items():
        sub_budget = int(token_budget * SECTION_BUDGET_FRACTION.get(name, 0.1))
        if isinstance(content, list):
            kept, used = [], 0
            for entry in content:  # already ranked best-first
                t = _estimate_tokens(entry)
                if used + t <= sub_budget:
                    kept.append(entry)
                    used += t
                else:
                    break
            fitted[name] = kept
            total += used
        else:
            fitted[name] = content  # small scalar/dict sections kept whole
            total += _estimate_tokens(content)
    return fitted, total


def assemble_context(
    task: str,
    *,
    agent: Optional[str] = None,
    token_budget: int = 9000,
    agent_memory: Any = None,
    learning_store: Any = None,
    context_manager: Any = None,
    signal_ledger: Any = None,
    store: Any = None,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Assemble ranked, budget-fitted context for `task` (and optionally `agent`).

    Semantic Relationship: Context assembled_for AgentRepriming (within token budget)

    Returns a structured block: per-section ranked entries (each with a `source`
    pointer), plus token accounting and coverage. Sources are injectable for tests;
    they default to the live singletons.
    """
    if context_manager is None:
        from context.project_context import get_project_context_manager_instance
        context_manager = get_project_context_manager_instance()

    sections: Dict[str, Any] = {}

    if agent:
        briefing = load_briefing_from_previous_handoff(
            agent, signal_ledger=signal_ledger, learning_store=learning_store)
        if briefing:
            sections["briefing"] = briefing

    sections["decisions"] = load_decisions_applicable_to_task(
        task, top_k=8, agent_memory=agent_memory, now=now)
    # T071-R1: MOST-RELEVANT under the fixed relevance budget (was: top-8 by
    # generic rank). Same entry shape; kill switch AKASHIC_RELEVANCE_BUDGET=0.
    sections["learnings"] = load_learnings_for_boot(
        task, learning_store=learning_store, now=now)
    sections["blockers"] = load_blockers_preventing_progress(
        task, top_k=8, context_manager=context_manager, now=now)

    narrative = load_recent_narrative_for_boot(store=store)
    if narrative:
        sections["narrative"] = narrative

    # Compact project-state summary (high-signal, not the full dump).
    full = context_manager.derive_full_context_for_agent_repriming()
    big = full.get("big_picture", {})
    sections["project_state"] = {
        "progress_pct": big.get("progress_percentage"),
        "milestones": big.get("milestones", {}).get("total"),
        "milestones_done": big.get("milestones", {}).get("completed"),
        "current_work": full.get("mid_picture", {}).get("current_work"),
    }

    fitted, approx_tokens = _fit_to_budget(sections, token_budget)
    coverage = [name for name, content in fitted.items()
                if content or content == 0]  # sections that produced something

    # Distill a compact SKELETON over the source-bearing entries (progressive
    # disclosure: this is the small overview an agent reads; `sections` is the
    # structured backing it drills into via each entry's source pointer).
    skeleton_items = []
    narrative = fitted.get("narrative")
    if narrative:
        skeleton_items.append({
            "summary": narrative.get("summary", ""),
            "source": narrative.get("source", "narr:atlas:current"),
            "kind": "narrative",
        })
    for kind in ("decisions", "learnings", "blockers"):
        for entry in fitted.get(kind, []):
            skeleton_items.append({**entry, "kind": kind})
    briefing = fitted.get("briefing")
    if briefing:
        skeleton_items.insert(0, {
            "summary": f"handoff from {briefing.get('from_agent')}: {briefing.get('task')}",
            "source": briefing.get("source"), "kind": "briefing",
        })
    distillation = Distiller().distill(
        skeleton_items, token_budget=token_budget, instruction=f"starting context for: {task}")

    return {
        "task": task,
        "agent": agent,
        "generated_at": datetime.now().isoformat(),
        "token_budget": token_budget,
        "approx_tokens": approx_tokens,
        "within_budget": approx_tokens <= token_budget,
        "coverage": coverage,
        "skeleton": distillation.skeleton,            # compact "shape" to inject
        "skeleton_entries": distillation.entries,     # structured, each with a source
        "skeleton_dropped": distillation.dropped_sources,
        "skeleton_ok": distillation.critic_ok,
        "sections": fitted,                           # full structured backing (drill-down)
    }
