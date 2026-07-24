"""Yardsticks for the future SEMANTIC gate (recall confirmation-bias program) -- measurement-first.

Companion: docs/library/design/20260709_keeping-recall-honest-critic-vs-dialecti_1a5498.md. Slice 3 proved deterministic lexical methods cannot judge
stance (topic-adjacency != contradiction), so genuine-counter detection is deferred to a semantic
(LLM) gate. Per the plan -- and our own lesson "build the yardstick + a real-corpus probe before the
mechanism" -- these are the labeled datasets that gate will be measured against, built BEFORE it
exists so it can never be graded on a metric we cannot compute (the Goodhart trap).

Two datasets, one per route the gate will serve:
  - contradiction_pairs(): does lesson B genuinely CONTRADICT lesson A? (the lesson-vs-lesson counter
    judge). DERIVED from the curated counter fixture -- one source of truth: a case's gold counter is
    a positive; its other corpus items (agreements, off-topic neighbours, and the agrees-distractors)
    are negatives. The hard negatives (an on-topic anti-pattern the thesis AGREES with) are exactly
    the false positives that sank the deterministic finder, so a judge that clears this has earned it.
  - action_applicability_cases(): does an ACTION instantiate an anti-pattern's bad practice? (the
    action-warning channel). Hand-labelled: each anti-pattern paired with an action that DOES it, one
    that does the opposite/fix, and an off-topic one.
"""
from __future__ import annotations

from typing import Any, Dict, List

from fixtures.counter_fixture import gold_cases


def _text(item: Dict[str, Any]) -> str:
    return item.get("recommendation") or item.get("actual") or item.get("what_tried") or item.get("text", "")


def contradiction_pairs() -> List[Dict[str, Any]]:
    """Labeled (a, b, contradicts) pairs derived from the counter fixture's adjudicated cases."""
    pairs: List[Dict[str, Any]] = []
    for c in gold_cases():
        th = c["thesis"]
        a = _text(th)
        gold = set(c["counter_sources"])
        for item in c["corpus"]:
            nm = item["experiment_name"]
            if nm == th["experiment_name"]:
                continue
            pairs.append({"a": a, "b": _text(item), "contradicts": nm in gold,
                          "case": c["id"], "b_source": nm})
    return pairs


# Each anti-pattern -> the text that describes its known-bad practice.
_AP = {
    "capability_without_a_door":
        "shipped a capability in a lower layer but never exposed it on the door agents use, so it went unused",
    "sync_blocking_flush":
        "a synchronous blocking flush hung the store under load; never block the write path",
    "python_loop_unrolling":
        "manual loop unrolling in Python gained ~2% and hurt readability; not worth it",
}


def action_applicability_cases() -> List[Dict[str, Any]]:
    """Labeled (action, anti_pattern, instantiates) cases: does the action DO the known-bad thing?"""
    def C(action, ap, instantiates):
        return {"action": action, "anti_pattern": ap, "ap_text": _AP[ap], "instantiates": instantiates}
    return [
        C("add a method to LearningStore but skip wiring it into agent_cli this slice",
          "capability_without_a_door", True),
        C("add --anti-pattern to agent_cli learn and the store method together in one slice",
          "capability_without_a_door", False),
        C("edit the README badge", "capability_without_a_door", False),
        C("make the store flush synchronously and block until each write is durable",
          "sync_blocking_flush", True),
        C("make the store flush async and non-blocking so the write path never stalls",
          "sync_blocking_flush", False),
        C("rename a variable in the ranker", "sync_blocking_flush", False),
        C("manually unroll the hot loop in the scorer for speed", "python_loop_unrolling", True),
        C("add memoization to the scorer hot path", "python_loop_unrolling", False),
        C("update a module docstring", "python_loop_unrolling", False),
    ]
