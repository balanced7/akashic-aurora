"""
Consolidation: distill raw episodic memory into a curated chronicle.

Semantic Relationship: Chronicle distilled_from EpisodicMemory (lossy + pointer)

The episodic -> semantic loop the research calls for. It takes the raw experiences
and reflections an agent accumulated (AgentMemory) and distills them — via the
Ranker (what matters) + the Distiller (writer->critic, to a budget) — into a
compact, curated set of durable lessons written to `chronicles/`.

Key rules (docs/context-compaction-skeleton-research.md):
- **Raw is sacred:** this only READS AgentMemory; it never deletes a record. The
  chronicle is a derived *view*.
- **Lossy summary + lossless pointer:** every lesson keeps a `source` pointer back
  to the raw experience/reflection, so detail is always recoverable.
- The chronicle is the "highlights" layer (decisions/failures/lessons), distilled
  from the raw firehose — exactly what the `chronicles/` directory was reserved for.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.learning.agent_memory import AgentMemory, get_agent_memory
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller
from core.primitives.consolidator import Consolidator


def consolidate_learnings_into_chronicle(
    *,
    learning_store: Optional[Any] = None,
    token_budget: int = 4000,
    chronicle_dir: Optional[str] = None,
    ranker: Optional[Ranker] = None,
    distiller: Optional[Distiller] = None,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Distill the LearningStore (experiment lessons) into `chronicles/lessons.md`.

    Semantic Relationship: Lessons consolidated_from Experiments (lossy + pointer)

    The learnings already carry a `source` pointer (e.g. learnings.jsonl:L5), so the
    chronicle stays traceable to the rich raw record. READ-ONLY on the store.
    """
    from core.learning.learning_store import get_learning_store
    ls = learning_store or get_learning_store()
    consolidator = Consolidator(ranker=ranker, distiller=distiller, token_budget=token_budget)
    base = Path(chronicle_dir) if chronicle_dir else \
        Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "chronicles"
    base.mkdir(parents=True, exist_ok=True)

    items = []
    for rec in ls.load_all_learnings_from_store():
        summary = rec.get("recommendation") or rec.get("actual") or rec.get("what_tried", "")
        items.append(Consolidator.item(
            text=summary,
            source=rec.get("source") or rec.get("experiment_name"),
            kind="lesson",
            relationship_type=rec.get("category"),
            importance=4 if str(rec.get("success", "")).lower() in ("yes", "true") else 3,
            timestamp=rec.get("timestamp"),
        ))

    distillation = consolidator.consolidate(
        items, instruction="durable lessons from experiments", now=now)

    path = base / "lessons.md"
    header = (
        "# Lessons (auto-generated from the LearningStore — do not hand-edit)\n\n"
        f"_Distilled from {len(items)} experiment lesson(s) · "
        f"critic_ok={distillation.critic_ok} · {datetime.now().isoformat()}_\n\n"
        "Each line is a lesson with a `source` pointer back to the raw record.\n\n"
    )
    body = distillation.skeleton if distillation.skeleton else "_(no lessons yet)_"
    path.write_text(header + body + "\n", encoding="utf-8")

    return {
        "chronicle": str(path),
        "lessons": len(distillation.entries),
        "from_records": len(items),
        "included_sources": distillation.included_sources,
        "dropped_sources": distillation.dropped_sources,
        "critic_ok": distillation.critic_ok,
        "approx_tokens": distillation.approx_tokens,
    }


def consolidate_memory_into_chronicle(
    *,
    agent_memory: Optional[AgentMemory] = None,
    token_budget: int = 4000,
    chronicle_dir: Optional[str] = None,
    ranker: Optional[Ranker] = None,
    distiller: Optional[Distiller] = None,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Distill experiences + reflections into `chronicles/lessons.md` (generated).

    Semantic Relationship: Lessons consolidated_from Experiences_and_Reflections

    Returns a report: chronicle path, lesson count, source pointers, critic verdict.
    Empty memory -> an empty (but valid) chronicle, gracefully.
    """
    mem = agent_memory or get_agent_memory()
    ranker = ranker or Ranker()
    distiller = distiller or Distiller()
    base = Path(chronicle_dir) if chronicle_dir else \
        Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "chronicles"
    base.mkdir(parents=True, exist_ok=True)

    # Gather raw episodic memory as Ranker items, each pointing back to its record.
    items = []
    for exp in mem.load_all_experiences():
        text = "; ".join(exp.learnings) if exp.learnings else (exp.result or exp.task)
        items.append({"text": text, "source": exp.id, "kind": "experience",
                      "importance": 4 if exp.success else 3, "timestamp": exp.timestamp})
    for refl in mem.get_insights(min_confidence=0.0):  # all reflections
        items.append({"text": refl.get("what_would_help") or refl.get("what_went_wrong", ""),
                      "source": refl.get("id"), "kind": "reflection",
                      "importance": 3, "timestamp": refl.get("created_at")})

    ranked = [s.item for s in ranker.rank(items, query="", now=now)]
    distillation = distiller.distill(ranked, token_budget=token_budget,
                                     instruction="durable lessons from experience")

    path = base / "lessons.md"
    header = (
        "# Lessons (auto-generated from memory — do not hand-edit)\n\n"
        f"_Distilled from {len(items)} memory record(s) · "
        f"critic_ok={distillation.critic_ok} · {datetime.now().isoformat()}_\n\n"
        "Each line is a lesson with a `source` pointer back to the raw record.\n\n"
    )
    body = distillation.skeleton if distillation.skeleton else "_(no lessons yet)_"
    path.write_text(header + body + "\n", encoding="utf-8")

    return {
        "chronicle": str(path),
        "lessons": len(distillation.entries),
        "from_records": len(items),
        "included_sources": distillation.included_sources,
        "dropped_sources": distillation.dropped_sources,
        "critic_ok": distillation.critic_ok,
        "approx_tokens": distillation.approx_tokens,
    }
