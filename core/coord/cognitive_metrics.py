"""
Cognitive Efficiency Metrics — live instrumentation for the Stage-3 evidence engine.

Measures what GPT named as the missing piece: not whether the coordination mechanism WORKS
(demonstration), but whether it produces MEASURABLY BETTER OUTCOMES than the alternative
(experiment). This module is the sensor suite that feeds data into core/coord/metrics.py
and core/coord/experiment.py for cross-run analysis.

Metrics tracked per agent turn (accumulated across a session):
  * reasoning_tokens_coordination  — tokens spent on locks, halts, arbitration, negotiation
  * reasoning_tokens_productive    — tokens spent on the actual task
  * abandoned_tokens               — tokens wasted when barge-in (nudge/halt) interrupted mid-reasoning
  * duplicate_file_reads           — same file read by this same agent without an intervening write
  * file_reads_saved_by_hints      — reads avoided because a context hint covered the file
  * context_refreshes              — times the system prompt was rebuilt (boot/re-onboard)
  * human_interjections            — how many times a human steered/interrupted/halted this agent
  * tool_calls_coordination        — tool calls related to locks, bus, control
  * tool_calls_productive          — tool calls related to actual work (read, write, search, git)

Design:
  - Per-agent, in-memory accumulator (lives on the runner process; cleared on restart).
  - Thread-safe for the runner's single-threaded loop (no locks needed, but atomic incr safe).
  - Zero-cost when disabled (all functions are no-ops if not initialized).
  - Snapshot-able: dump() returns a dict for the experiment harness to collect.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── session accumulator (per agent) ────────────────────────────────────

@dataclass
class EfficiencySnapshot:
    agent_id: str
    started_at: str
    duration_s: float

    # Token economy
    reasoning_tokens_coordination: int = 0
    reasoning_tokens_productive: int = 0
    abandoned_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    # File access efficiency
    duplicate_file_reads: int = 0
    file_reads_saved_by_hints: int = 0
    total_file_reads: int = 0

    # Human cost
    human_interjections: int = 0
    context_refreshes: int = 0

    # Tool call breakdown
    tool_calls_coordination: int = 0
    tool_calls_productive: int = 0
    total_tool_calls: int = 0

    # Derived
    @property
    def coordination_token_ratio(self) -> float:
        """Fraction of reasoning tokens spent on coordination (lower is better)."""
        total = self.reasoning_tokens_coordination + self.reasoning_tokens_productive
        if total == 0:
            return 0.0
        return round(self.reasoning_tokens_coordination / total, 4)

    @property
    def waste_ratio(self) -> float:
        """Abandoned tokens as fraction of total completion tokens."""
        if self.total_completion_tokens == 0:
            return 0.0
        return round(self.abandoned_tokens / self.total_completion_tokens, 4)

    @property
    def duplication_rate(self) -> float:
        """Duplicate reads as fraction of total reads."""
        if self.total_file_reads == 0:
            return 0.0
        return round(self.duplicate_file_reads / self.total_file_reads, 4)

    @property
    def hint_efficiency(self) -> float:
        """Fraction of reads avoided by hints."""
        total = self.file_reads_saved_by_hints + self.total_file_reads
        if total == 0:
            return 0.0
        return round(self.file_reads_saved_by_hints / total, 4)

    @property
    def human_cost_per_turn(self) -> float:
        """Human interjections per tool call (lower = more autonomous)."""
        if self.total_tool_calls == 0:
            return float(self.human_interjections) if self.human_interjections > 0 else 0.0
        return round(self.human_interjections / self.total_tool_calls, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "started_at": self.started_at,
            "duration_s": self.duration_s,
            "reasoning_tokens_coordination": self.reasoning_tokens_coordination,
            "reasoning_tokens_productive": self.reasoning_tokens_productive,
            "abandoned_tokens": self.abandoned_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "duplicate_file_reads": self.duplicate_file_reads,
            "file_reads_saved_by_hints": self.file_reads_saved_by_hints,
            "total_file_reads": self.total_file_reads,
            "human_interjections": self.human_interjections,
            "context_refreshes": self.context_refreshes,
            "tool_calls_coordination": self.tool_calls_coordination,
            "tool_calls_productive": self.tool_calls_productive,
            "total_tool_calls": self.total_tool_calls,
            "derived": {
                "coordination_token_ratio": self.coordination_token_ratio,
                "waste_ratio": self.waste_ratio,
                "duplication_rate": self.duplication_rate,
                "hint_efficiency": self.hint_efficiency,
                "human_cost_per_turn": self.human_cost_per_turn,
            },
        }


# ── per-agent store ────────────────────────────────────────────────────

_store: Dict[str, EfficiencySnapshot] = {}
_lock = threading.Lock()
_enabled = True


def init(agent_id: str) -> EfficiencySnapshot:
    """Initialize or reset the accumulator for an agent. Returns the snapshot (also stored)."""
    snap = EfficiencySnapshot(
        agent_id=agent_id,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        duration_s=0.0,
    )
    with _lock:
        _store[agent_id] = snap
    return snap


def _snap(agent_id: str) -> Optional[EfficiencySnapshot]:
    if not _enabled:
        return None
    with _lock:
        return _store.get(agent_id)


# ── instrumentation calls (zero-cost when disabled) ─────────────────────

def record_prompt_tokens(agent_id: str, n: int):
    if (s := _snap(agent_id)):
        s.total_prompt_tokens += n


def record_completion_tokens(agent_id: str, n: int):
    if (s := _snap(agent_id)):
        s.total_completion_tokens += n


def record_reasoning(agent_id: str, tokens: int, category: str = "productive"):
    """category: 'coordination' | 'productive'"""
    if (s := _snap(agent_id)):
        if category == "coordination":
            s.reasoning_tokens_coordination += tokens
        else:
            s.reasoning_tokens_productive += tokens


def record_abandoned(agent_id: str, tokens: int):
    """Tokens wasted because a nudge/halt interrupted reasoning."""
    if (s := _snap(agent_id)):
        s.abandoned_tokens += tokens


def record_file_read(agent_id: str, path: str, *, from_hint: bool = False):
    """Record a file read. If from_hint=True, this read was AVOIDED because a hint covered it."""
    if (s := _snap(agent_id)):
        if from_hint:
            s.file_reads_saved_by_hints += 1
        else:
            s.total_file_reads += 1
            # Duplicate detection: track last-read path per agent
            _last_reads.setdefault(agent_id, {})
            prev = _last_reads[agent_id].get(path)
            if prev is not None:
                s.duplicate_file_reads += 1
            _last_reads[agent_id][path] = time.time()


def record_human_interjection(agent_id: str):
    if (s := _snap(agent_id)):
        s.human_interjections += 1


def record_context_refresh(agent_id: str):
    if (s := _snap(agent_id)):
        s.context_refreshes += 1


def record_tool_call(agent_id: str, tool_name: str):
    """Classify a tool call as coordination or productive."""
    if (s := _snap(agent_id)):
        s.total_tool_calls += 1
        # Coordination tool calls: bus operations, lock management, control
        coord_tools = frozenset({
            "bifrost_send", "bifrost_inbox", "bifrost_nudge", "bifrost_steer",
            "bifrost_broadcast", "knowledge_recall", "knowledge_boot",
        })
        if tool_name in coord_tools:
            s.tool_calls_coordination += 1
        else:
            s.tool_calls_productive += 1


def record_turn_complete(agent_id: str):
    """Update duration after each turn."""
    if (s := _snap(agent_id)):
        try:
            started = time.mktime(time.strptime(s.started_at, "%Y-%m-%dT%H:%M:%S"))
            s.duration_s = round(time.time() - started, 2)
        except Exception:
            pass


# ── duplicate read tracking (per-agent path -> last read timestamp) ────

_last_reads: Dict[str, Dict[str, float]] = {}


# ── snapshot / dump ─────────────────────────────────────────────────────

def dump(agent_id: str) -> Optional[Dict[str, Any]]:
    """Snapshot current metrics for one agent (for the experiment harness to collect)."""
    if (s := _snap(agent_id)):
        record_turn_complete(agent_id)
        return s.to_dict()
    return None


def dump_all() -> Dict[str, Dict[str, Any]]:
    """Snapshot ALL agents' metrics."""
    return {aid: dump(aid) for aid in list(_store.keys()) if dump(aid)}


def reset(agent_id: str):
    """Clear metrics for one agent (e.g. between experiment runs)."""
    with _lock:
        _store.pop(agent_id, None)
        _last_reads.pop(agent_id, None)


def reset_all():
    """Clear ALL metrics."""
    with _lock:
        _store.clear()
        _last_reads.clear()


def disable():
    """Turn off all instrumentation (zero-cost path)."""
    global _enabled
    _enabled = False
    reset_all()


def enable():
    """Turn instrumentation back on."""
    global _enabled
    _enabled = True
