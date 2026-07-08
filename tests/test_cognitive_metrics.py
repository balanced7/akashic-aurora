"""Tests for the cognitive-efficiency accumulator (core/coord/cognitive_metrics.py).

P0 test hardening (arch-triage-2026-07-07): the Stage-3 evidence sensor suite, reachable in production
but previously untested. Module state is GLOBAL (_store/_last_reads/_enabled) so every test resets it
first (both the claude and DeepSeek plans flagged this hazard). Synthesized from both plans, 2026-07-07.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import cognitive_metrics as cm


@pytest.fixture(autouse=True)
def _clean_state():
    """Global-state hazard: start every test from a clean, enabled accumulator (and leave it enabled)."""
    cm.enable()
    cm.reset_all()
    yield
    cm.enable()
    cm.reset_all()


# --- basic accumulation + dump ----------------------------------------------------------------------

def test_init_and_dump_roundtrip():
    cm.init("a")
    d = cm.dump("a")
    assert d["agent_id"] == "a" and "derived" in d
    assert d["total_tool_calls"] == 0


def test_record_functions_accumulate():
    cm.init("a")
    cm.record_prompt_tokens("a", 10)
    cm.record_completion_tokens("a", 20)
    cm.record_reasoning("a", 5, "coordination")
    cm.record_reasoning("a", 15, "productive")
    cm.record_abandoned("a", 4)
    cm.record_human_interjection("a")
    cm.record_context_refresh("a")
    d = cm.dump("a")
    assert d["total_prompt_tokens"] == 10 and d["total_completion_tokens"] == 20
    assert d["reasoning_tokens_coordination"] == 5 and d["reasoning_tokens_productive"] == 15
    assert d["abandoned_tokens"] == 4 and d["human_interjections"] == 1 and d["context_refreshes"] == 1


# --- invariants on the counters + derived ratios ----------------------------------------------------

def test_tool_call_breakdown_equality():
    """total_tool_calls == coordination + productive -- if this diverges every derived metric is garbage."""
    cm.init("a")
    for t in ("bifrost_send", "Read", "knowledge_recall", "Edit", "Bash", "bifrost_nudge"):
        cm.record_tool_call("a", t)
    d = cm.dump("a")
    assert d["total_tool_calls"] == d["tool_calls_coordination"] + d["tool_calls_productive"]
    assert d["tool_calls_coordination"] == 3 and d["tool_calls_productive"] == 3   # 3 coord tools above


def test_derived_ratios_are_correct_and_bounded():
    cm.init("a")
    cm.record_reasoning("a", 30, "coordination")
    cm.record_reasoning("a", 10, "productive")
    cm.record_completion_tokens("a", 100)
    cm.record_abandoned("a", 25)
    d = cm.dump("a")["derived"]
    assert d["coordination_token_ratio"] == 0.75 and 0 <= d["coordination_token_ratio"] <= 1
    assert d["waste_ratio"] == 0.25 and 0 <= d["waste_ratio"] <= 1


def test_derived_properties_never_divide_by_zero():
    cm.init("a")
    d = cm.dump("a")["derived"]           # everything zero
    assert all(v == 0.0 for v in d.values())


def test_human_cost_per_turn_zero_tools_but_interjections():
    """The odd branch: no tool calls yet a human interjected -> returns the raw interjection count."""
    cm.init("a")
    cm.record_human_interjection("a")
    assert cm.dump("a")["derived"]["human_cost_per_turn"] == 1.0


# --- file-read duplicate detection ------------------------------------------------------------------

def test_duplicate_file_read_detection():
    cm.init("a")
    cm.record_file_read("a", "x.py")
    cm.record_file_read("a", "x.py")      # duplicate
    cm.record_file_read("a", "y.py")
    d = cm.dump("a")
    assert d["total_file_reads"] == 3 and d["duplicate_file_reads"] == 1


def test_duplicate_detection_is_per_agent():
    cm.init("a"); cm.init("b")
    cm.record_file_read("a", "x.py")
    cm.record_file_read("b", "x.py")      # same path, different agent -> NOT a duplicate for either
    assert cm.dump("a")["duplicate_file_reads"] == 0
    assert cm.dump("b")["duplicate_file_reads"] == 0


def test_hint_read_counts_separately_and_not_as_duplicate():
    cm.init("a")
    cm.record_file_read("a", "x.py", from_hint=True)   # saved, not a real read
    cm.record_file_read("a", "x.py")                    # first REAL read -> not a duplicate
    d = cm.dump("a")
    assert d["file_reads_saved_by_hints"] == 1 and d["total_file_reads"] == 1
    assert d["duplicate_file_reads"] == 0


# --- lifecycle: disable / enable / reset / uninitialized --------------------------------------------

def test_disabled_is_a_noop():
    cm.init("a")
    cm.disable()
    cm.record_prompt_tokens("a", 999)     # swallowed while disabled
    assert cm.dump("a") is None            # _snap returns None when disabled
    cm.enable()
    assert cm.dump("a") is None            # disable() also cleared state


def test_recording_uninitialized_agent_is_safe():
    cm.record_prompt_tokens("never_init", 5)   # must not raise
    assert cm.dump("never_init") is None


def test_reset_clears_one_agent_and_its_read_history():
    cm.init("a"); cm.init("b")
    cm.record_file_read("a", "x.py")
    cm.reset("a")
    assert cm.dump("a") is None and cm.dump("b") is not None
    # read-history cleared: re-init + re-read same path is not a duplicate
    cm.init("a")
    cm.record_file_read("a", "x.py")
    assert cm.dump("a")["duplicate_file_reads"] == 0


def test_dump_all_aggregates_all_agents():
    cm.init("a"); cm.init("b")
    cm.record_prompt_tokens("a", 1)
    alld = cm.dump_all()
    assert set(alld) == {"a", "b"}
