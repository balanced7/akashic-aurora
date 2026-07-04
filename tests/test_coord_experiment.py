"""
The coordination experiment harness (core/coord/experiment) -- the A/B/C(+W) evaluator.

These tests are the harness's own falsification checks: they assert the structural relationships the
policies MUST exhibit, and -- per the review's discipline -- that metric C can actually FAIL (a metric
that can't fail proves nothing). Pure/deterministic, no Redis. Run: py -m pytest tests/test_coord_experiment.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import experiment as X


def test_score_shape_and_ranges():
    for name in X.POLICIES:
        m = X.evaluate(X.mixed(), name)
        assert set(m) == {"A_task", "B_cost", "C_explore", "W_waste"}
        assert 0.0 <= m["A_task"] <= 1.0 and 0.0 <= m["C_explore"] <= 1.0
        assert m["B_cost"] >= 0 and m["W_waste"] >= 0


def test_gates_cut_duplicate_waste():
    """Pure duplicate intent: all policies still deliver (A=1), but only the gates avoid redundant
    re-execution -- social pays it as W."""
    c = X.compare(X.collision_heavy(6))
    assert c["social"]["A_task"] == 1.0 and c["lock_gate"]["A_task"] == 1.0 and c["intent_gate"]["A_task"] == 1.0
    assert c["social"]["W_waste"] == 5                     # 6 agents, same work -> 5 wasted
    assert c["lock_gate"]["W_waste"] == 0 and c["intent_gate"]["W_waste"] == 0


def test_lock_gate_exclusivity_bias():
    """same file, DIFFERENT intents: intent_gate admits it all; lock_gate blocks parallel-useful work,
    losing both task coverage (A) and exploration (C)."""
    c = X.compare(X.parallel_useful(6))
    assert c["intent_gate"]["A_task"] == 1.0 and c["intent_gate"]["C_explore"] == 1.0
    assert c["lock_gate"]["A_task"] < c["intent_gate"]["A_task"]         # work lost to over-blocking
    assert c["lock_gate"]["C_explore"] < c["intent_gate"]["C_explore"]   # exploration suppressed


def test_metric_C_can_fail():
    """The Goodhart guard must be falsifiable: an exclusivity-biased policy scores LOW on C."""
    c = X.compare(X.parallel_useful(6))
    assert c["lock_gate"]["C_explore"] < 0.5               # C genuinely drops -> it can fail
    assert c["intent_gate"]["C_explore"] == 1.0            # ...and genuinely pass


def test_intent_gate_is_best_overall_on_mixed():
    """On a realistic mix only intent_gate reaches full coverage AND full exploration AND zero waste;
    lock_gate loses a parallel-useful intent, social pays redundant waste."""
    c = X.compare(X.mixed())
    assert c["intent_gate"]["A_task"] == 1.0 and c["intent_gate"]["C_explore"] == 1.0 and c["intent_gate"]["W_waste"] == 0
    assert c["lock_gate"]["A_task"] < 1.0                  # exclusivity bias drops a real intent
    assert c["social"]["W_waste"] > 0                      # no coordination -> duplicate waste
