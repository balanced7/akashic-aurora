"""
Consolidation: distill raw episodic memory + experiment lessons into a curated chronicle.

Semantic Relationship: Chronicle distilled_from EpisodicMemory + Experiments (lossy + pointer)

The episodic -> semantic loop the research calls for. ONE path (`consolidate_into_chronicle`)
ranks (what matters) + distills (writer->critic, to a budget) the requested sources into a
compact, curated set of durable lessons -- through the single shared Consolidator, so the
faithfulness/critic seam is wired once for every source.

SPINE-1 (review): there used to be TWO functions that BOTH wrote `chronicles/lessons.md` and
clobbered each other -- and one bypassed the Consolidator entirely. Now there is one canonical
writer; the per-source helpers are thin shims that delegate to it and write DISTINCT files, so
nothing clobbers and both sources flow through the same critic seam.

Key rules (docs/library/design/20260620_research-context-handling-compaction-and_e5960c.md):
- **Raw is sacred:** READ-only on the stores; the chronicle is a derived *view*, never deletes.
- **Lossy summary + lossless pointer:** every lesson keeps a `source` pointer to the raw record.
"""

import os
from core.paths import repo_root
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from core.learning.agent_memory import AgentMemory, get_agent_memory
from core.primitives.consolidator import Consolidator
from core.primitives.distiller import Distiller
from core.primitives.ranker import Ranker

# Human labels for the chronicle header, by source key.
_SOURCE_LABEL = {"mem": "memory", "learn": "the LearningStore"}


def _gather_learn_items(learning_store) -> list:
    from core.learning.learning_store import get_learning_store
    ls = learning_store or get_learning_store()
    items = []
    for rec in ls.load_all_learnings_from_store():
        summary = rec.get("recommendation") or rec.get("actual") or rec.get("what_tried", "")
        items.append(Consolidator.item(
            text=summary, source=rec.get("source") or rec.get("experiment_name"),
            kind="lesson", relationship_type=rec.get("category"),
            importance=4 if str(rec.get("success", "")).lower() in ("yes", "true") else 3,
            timestamp=rec.get("timestamp")))
    return items


def _gather_mem_items(agent_memory) -> list:
    mem = agent_memory or get_agent_memory()
    items = []
    for exp in mem.load_all_experiences():
        text = "; ".join(exp.learnings) if exp.learnings else (exp.result or exp.task)
        items.append(Consolidator.item(text=text, source=exp.id, kind="experience",
                                       importance=4 if exp.success else 3, timestamp=exp.timestamp))
    for refl in mem.get_insights(min_confidence=0.0):
        items.append(Consolidator.item(
            text=refl.get("what_would_help") or refl.get("what_went_wrong", ""),
            source=refl.get("id"), kind="reflection", importance=3,
            timestamp=refl.get("created_at")))
    return items


def consolidate_into_chronicle(
    *,
    sources: Sequence[str] = ("learn", "mem"),
    out_name: str = "lessons.md",
    learning_store: Optional[Any] = None,
    agent_memory: Optional[AgentMemory] = None,
    token_budget: int = 4000,
    chronicle_dir: Optional[str] = None,
    ranker: Optional[Ranker] = None,
    distiller: Optional[Distiller] = None,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """THE canonical consolidation path: distill the requested `sources` ('learn' and/or 'mem')
    through ONE Consolidator into `chronicles/<out_name>`. Both sources share the same Ranker +
    Distiller (and thus the FAITH critic seam, once wired). READ-only on the stores."""
    consolidator = Consolidator(ranker=ranker, distiller=distiller, token_budget=token_budget)
    base = Path(chronicle_dir) if chronicle_dir else \
        repo_root() / "chronicles"
    base.mkdir(parents=True, exist_ok=True)

    items = []
    if "learn" in sources:
        items += _gather_learn_items(learning_store)
    if "mem" in sources:
        items += _gather_mem_items(agent_memory)

    distillation = consolidator.consolidate(items, instruction="durable lessons", now=now)

    label = " + ".join(_SOURCE_LABEL.get(s, s) for s in sources)
    path = base / out_name
    header = (
        f"# Lessons (auto-generated from {label} — do not hand-edit)\n\n"
        f"_Distilled from {len(items)} record(s) · critic_ok={distillation.critic_ok} · "
        f"{datetime.now().isoformat()}_\n\n"
        "Each line is a lesson with a `source` pointer back to the raw record.\n\n"
    )
    body = distillation.skeleton if distillation.skeleton else "_(no lessons yet)_"
    path.write_text(header + body + "\n", encoding="utf-8")

    return {
        "chronicle": str(path), "lessons": len(distillation.entries),
        "from_records": len(items), "included_sources": distillation.included_sources,
        "dropped_sources": distillation.dropped_sources, "critic_ok": distillation.critic_ok,
        "approx_tokens": distillation.approx_tokens,
    }


def consolidate_memory_into_chronicle(*, agent_memory: Optional[AgentMemory] = None, **kw) -> Dict[str, Any]:
    """Back-compat shim -> the canonical path, memory source only, to a DISTINCT file (no clobber)."""
    kw.setdefault("out_name", "memory.md")
    return consolidate_into_chronicle(sources=("mem",), agent_memory=agent_memory, **kw)


def consolidate_learnings_into_chronicle(*, learning_store: Optional[Any] = None, **kw) -> Dict[str, Any]:
    """Back-compat shim -> the canonical path, experiment-lessons source only, to a DISTINCT file."""
    kw.setdefault("out_name", "experiments.md")
    return consolidate_into_chronicle(sources=("learn",), learning_store=learning_store, **kw)
