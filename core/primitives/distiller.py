"""
Distiller: compact many items into a token budget, keeping a pointer to each source.

Semantic Relationship: Distillation derived_from Items (compacted, within budget)

The third shared primitive (Supersession -> Ranker -> Distiller). Used by the
Context pillar (fit the assembled context to 8-10k tokens) and, later, by the
AgentMemory consolidation->chronicles loop. It embodies the compaction research:

- **lossy summary + lossless pointer**: each distilled entry keeps a `source`
  pointer (the raw record stays in the Store/Ledger — never deleted), so detail is
  always recoverable. Footprint drops; nothing is lost.
- **skeleton output**: a compact, human-readable + machine-parseable list — "the
  shape of an idea" — for progressive disclosure (skeleton first, drill down via
  the source pointers on demand).
- **writer -> critic**: a heuristic writer ships now; an LLM writer/critic can be
  injected (the seam) for richer summarization with a faithfulness gate.

See docs/context-compaction-skeleton-research.md and docs/shared-primitives-spec.md.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Fields to summarize from, in priority order (first present wins).
_SUMMARY_FIELDS = ["recommendation", "decision", "description", "title", "summary",
                   "text", "what_tried", "task"]

# Values that look present but carry no signal — skip them when summarizing.
_EMPTY_TOKENS = {"", "none", "null", "n/a", "unknown"}


def _useful(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in _EMPTY_TOKENS


@dataclass
class Distillation:
    skeleton: str                       # compact human-readable text (the shape)
    entries: List[Dict[str, Any]]       # structured: {summary, source, relates, kind}
    included_sources: List[str]
    dropped_sources: List[str]          # didn't fit -> recoverable via these pointers
    approx_tokens: int
    critic_ok: bool
    critic_notes: List[str] = field(default_factory=list)
    skipped_no_source: int = 0          # items excluded for lacking a source pointer


def _summarize_item(item: Dict[str, Any], max_chars: int) -> str:
    for f in _SUMMARY_FIELDS:
        v = item.get(f)
        if _useful(v):
            return str(v)[:max_chars].strip()
    for v in item.values():
        if _useful(v):
            return str(v)[:max_chars].strip()
    return ""


def _source_of(item: Dict[str, Any]) -> Optional[str]:
    return item.get("source") or item.get("id") or item.get("experiment_name")


class Distiller:
    """
    Compacts ranked items into a budgeted skeleton, each entry pointer-traceable.

    Semantic Relationship: Distiller compacts Items into Skeleton (within budget)
    """

    def __init__(self, *,
                 writer: Optional[Callable] = None,
                 critic: Optional[Callable] = None,
                 max_chars_per_entry: int = 120):
        self.writer = writer    # writer(items, token_budget, instruction) -> Distillation
        self.critic = critic    # critic(items, skeleton, entries) -> (ok: bool, notes: list)
        self.max_chars_per_entry = max_chars_per_entry

    def distill(self, items: List[Dict[str, Any]], *, token_budget: int,
                instruction: str = "", kind: str = "") -> Distillation:
        """
        Compact `items` (already ranked best-first) into a skeleton within budget.

        Semantic Relationship: Skeleton derived_from RankedItems (budget-fit + pointers)

        If an LLM `writer` is injected it is used; otherwise a heuristic writer
        ships a one-line-per-item skeleton, including items until the budget is hit
        and recording the rest as `dropped_sources` (recoverable via their pointers).
        """
        if self.writer is not None:
            return self.writer(items, token_budget, instruction)

        entries: List[Dict[str, Any]] = []
        included: List[str] = []
        dropped: List[str] = []
        lines: List[str] = []
        used = 0
        skipped_no_source = 0
        for item in items:  # ranked best-first
            source = _source_of(item)
            if not source:
                # An entry without a source can't be a lossless pointer back to the
                # raw record, so it can't be a faithful distillation -- exclude it.
                skipped_no_source += 1
                continue
            summary = _summarize_item(item, self.max_chars_per_entry)
            relates = item.get("relationship_type")
            line = f"- {summary}" + (f"  [relates: {relates}]" if relates else "") + f"  (source: {source})"
            tokens = max(1, len(line) // 4)
            if used + tokens <= token_budget:
                lines.append(line)
                used += tokens
                entries.append({"summary": summary, "source": source, "relates": relates, "kind": kind})
                included.append(source)
            else:
                dropped.append(source)

        skeleton = "\n".join(lines)
        ok, notes = self._heuristic_critic(entries, used, token_budget, dropped)
        if skipped_no_source:
            notes.append(f"{skipped_no_source} item(s) skipped (no source pointer — not traceable)")
        if self.critic is not None:
            ok, notes = self.critic(items, skeleton, entries)
        return Distillation(skeleton=skeleton, entries=entries, included_sources=included,
                            dropped_sources=dropped, approx_tokens=used,
                            critic_ok=ok, critic_notes=notes, skipped_no_source=skipped_no_source)

    @staticmethod
    def _heuristic_critic(entries, used, budget, dropped):
        notes, ok = [], True
        missing = [e for e in entries if not e.get("source")]
        if missing:
            ok = False
            notes.append(f"{len(missing)} entries missing a source pointer (lossless-pointer rule)")
        if used > budget:
            ok = False
            notes.append(f"over budget: {used} > {budget}")
        if dropped:
            notes.append(f"{len(dropped)} item(s) dropped to fit budget (recoverable via their sources)")
        return ok, notes
