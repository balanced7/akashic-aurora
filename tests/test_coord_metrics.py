"""Tests for core/coord/metrics.py — the Solution-Space-Shrinkage Tracker."""
import pytest
from core.coord.metrics import (
    ApproachVector,
    vector_from_run,
    shannon_entropy,
    uniqueness_ratio,
    is_monotonic_decreasing,
    is_flat,
    is_rising,
    _run_diversity,
    assess,
    run_metrics,
)


# --- _run_diversity (per-run signal) ---

class TestRunDiversity:
    def test_empty(self):
        assert _run_diversity(frozenset()) == 0.0

    def test_single(self):
        assert _run_diversity(frozenset({("a", "x")})) == 0.0

    def test_two(self):
        assert _run_diversity(frozenset({("a", "x"), ("b", "y")})) == 1.0  # log2(2)

    def test_four(self):
        v = frozenset({("a", "w"), ("b", "x"), ("c", "y"), ("d", "z")})
        assert _run_diversity(v) == 2.0  # log2(4)

    def test_six(self):
        v = frozenset({("api.py", f"f{i}") for i in range(6)})
        assert _run_diversity(v) == pytest.approx(2.585, abs=0.001)  # log2(6)


# --- ApproachVector construction ---

class TestVectorFromRun:
    def test_empty(self):
        assert vector_from_run([]) == frozenset()

    def test_one_action(self):
        v = vector_from_run([("claude", "api.py", "add-rate-limiting")])
        assert v == frozenset({("api.py", "add-rate-limiting")})

    def test_dedup_same_intent(self):
        v = vector_from_run([
            ("claude", "api.py", "add-rate-limiting"),
            ("deepseek", "api.py", "add-rate-limiting"),
        ])
        assert v == frozenset({("api.py", "add-rate-limiting")})

    def test_different_intents_same_file(self):
        v = vector_from_run([
            ("claude", "api.py", "add-rate-limiting"),
            ("deepseek", "api.py", "add-auth"),
        ])
        assert v == frozenset({("api.py", "add-rate-limiting"), ("api.py", "add-auth")})


# --- Shannon entropy ---

class TestShannonEntropy:
    def test_empty(self):
        assert shannon_entropy([]) == 0.0

    def test_single_vector(self):
        v = frozenset({("a", "x")})
        assert shannon_entropy([v]) == 0.0

    def test_all_same_zero(self):
        v = frozenset({("a", "x")})
        assert shannon_entropy([v, v, v]) == 0.0

    def test_max_diversity_two(self):
        a = frozenset({("a", "x")})
        b = frozenset({("b", "y")})
        # 2 distinct, each p=0.5: H = -0.5*log2(0.5)*2 = 1.0
        assert shannon_entropy([a, b]) == 1.0

    def test_max_diversity_four(self):
        a = frozenset({("a", "x")})
        b = frozenset({("b", "y")})
        c = frozenset({("c", "z")})
        d = frozenset({("d", "w")})
        # 4 distinct, each p=0.25: H = -0.25*log2(0.25)*4 = 2.0
        assert shannon_entropy([a, b, c, d]) == 2.0

    def test_mixed(self):
        a = frozenset({("a", "x")})
        b = frozenset({("b", "y")})
        # p(a)=0.75, p(b)=0.25: H ≈ 0.8113
        h = shannon_entropy([a, a, a, b])
        assert 0.81 < h < 0.82


# --- Uniqueness ratio ---

class TestUniquenessRatio:
    def test_empty(self):
        assert uniqueness_ratio([]) == 0.0

    def test_all_unique(self):
        a = frozenset({("a", "x")})
        b = frozenset({("b", "y")})
        assert uniqueness_ratio([a, b]) == 1.0

    def test_none_unique(self):
        a = frozenset({("a", "x")})
        assert uniqueness_ratio([a, a, a]) == 0.0

    def test_mixed(self):
        a = frozenset({("a", "x")})
        b = frozenset({("b", "y")})
        # a appears 3x, b 1x → 1/4 = 0.25
        assert uniqueness_ratio([a, a, a, b]) == 0.25


# --- Monotonicity ---

class TestIsMonotonicDecreasing:
    def test_empty(self):
        assert not is_monotonic_decreasing([])

    def test_single(self):
        assert not is_monotonic_decreasing([1.0])

    def test_strictly_decreasing(self):
        assert is_monotonic_decreasing([2.0, 1.5, 1.0])

    def test_non_increasing(self):
        assert is_monotonic_decreasing([2.0, 2.0, 1.0])

    def test_not_monotonic(self):
        assert not is_monotonic_decreasing([1.0, 2.0, 1.0])

    def test_spike_then_drop(self):
        assert not is_monotonic_decreasing([1.0, 1.5, 1.0])


# --- Flat and rising ---

class TestIsFlat:
    def test_empty(self):
        assert not is_flat([])

    def test_single(self):
        assert not is_flat([1.0])

    def test_identical(self):
        assert is_flat([0.5, 0.5, 0.5])

    def test_within_epsilon(self):
        assert is_flat([0.5, 0.5005, 0.4995], epsilon=0.001)

    def test_outside_epsilon(self):
        assert not is_flat([0.5, 0.51, 0.5], epsilon=0.001)


class TestIsRising:
    def test_empty(self):
        assert not is_rising([])

    def test_single(self):
        assert not is_rising([1.0])

    def test_strictly_rising(self):
        assert is_rising([0.5, 0.6, 0.7])

    def test_non_decreasing(self):
        assert is_rising([0.5, 0.5, 0.6])

    def test_not_rising(self):
        assert not is_rising([0.7, 0.6, 0.5])

    def test_all_flat(self):
        assert not is_rising([0.5, 0.5, 0.5])


# --- Assess (the watchdog) ---

class TestAssessCollapse:
    def test_collapse_signal(self):
        """Diversity dropping + correctness flat = COLLAPSE."""
        a = frozenset({("a", "x")})
        b = frozenset({("a", "x"), ("b", "y")})
        c = frozenset({("a", "x"), ("b", "y"), ("c", "z")})
        # Dropping diversity: [c,b,a] → more diverse earlier, collapsing to a
        vectors = [c, b, a]
        scores = [0.9, 0.9, 0.9]  # flat correctness
        v = assess(vectors, scores)
        assert v.collapse is True
        assert v.diversity_dropping is True
        assert v.correctness_flat is True
        assert "COLLAPSE" in v.diagnosis

    def test_converging_well(self):
        """Diversity dropping + correctness rising = healthy convergence."""
        a = frozenset({("a", "x")})
        b = frozenset({("a", "x"), ("b", "y")})
        vectors = [b, a]  # dropping
        scores = [0.7, 0.9]  # rising
        v = assess(vectors, scores)
        assert v.collapse is False
        assert v.diversity_dropping is True
        assert "CONVERGING WELL" in v.diagnosis

    def test_healthy(self):
        """Diversity growing = healthy exploration."""
        a = frozenset({("a", "x")})
        b = frozenset({("a", "x"), ("b", "y")})
        vectors = [a, b]  # growing: 1→2 approaches
        scores = [0.8, 0.8]
        v = assess(vectors, scores)
        assert v.collapse is False
        assert v.diversity_dropping is False
        # Growing diversity + flat correctness = not stagnant (exploration IS producing variety)
        assert "HEALTHY" in v.diagnosis

    def test_stagnant(self):
        """Flat diversity + flat correctness = stagnant (not collapsing, not exploring)."""
        a = frozenset({("a", "x")})
        b = frozenset({("b", "y")})  # different content, same size (1 approach each)
        vectors = [a, b]
        scores = [0.8, 0.8]  # flat correctness
        v = assess(vectors, scores)
        assert v.collapse is False
        assert v.diversity_dropping is False  # 0.0→0.0, no strict drop
        assert v.correctness_flat is True
        assert "STAGNANT" in v.diagnosis

    def test_no_data(self):
        v = assess([], [])
        assert v.runs == 0
        assert v.collapse is False
        assert "No data" in v.diagnosis

    def test_mismatched_lengths(self):
        a = frozenset({("a", "x")})
        with pytest.raises(ValueError, match="same length"):
            assess([a, a], [0.9])


# --- Integration: run_metrics with experiment.py ---

class TestRunMetricsIntegration:
    def test_smoke_run_metrics(self):
        """run_metrics returns vectors and scores for a real scenario+policy."""
        from core.coord.experiment import mixed as scenario_fn
        from core.coord.experiment import intent_gate as policy_fn

        vectors, scores = run_metrics(scenario_fn, policy_fn, n_runs=3)
        assert len(vectors) == 3
        assert len(scores) == 3
        # All scores should be the same (deterministic scenario+policy)
        assert scores[0] == scores[1] == scores[2]
        # Vectors should all be identical (same scenario each run)
        assert vectors[0] == vectors[1] == vectors[2]
        # intent_gate on mixed admits 4 of 5 actions (blocks the duplicate)
        assert set(vectors[0]) == {
            ("ui.py", "restyle-composer"),
            ("ui.py", "add-hint-cards"),
            ("locks.py", "add-guard-write"),
            ("docs.md", "write-thesis"),
        }

    def test_lock_gate_blocks_parallel_useful(self):
        """lock_gate on parallel_useful: blocks same-resource-different-intent, reducing vectors."""
        from core.coord.experiment import parallel_useful as scenario_fn
        from core.coord.experiment import lock_gate as policy_fn

        vectors, scores = run_metrics(scenario_fn, policy_fn, n_runs=1)
        # parallel_useful: 6 actions on api.py with 6 different intents
        # lock_gate admits only the first one (blocks rest on resource conflict)
        assert len(vectors[0]) == 1  # only first admitted, rest blocked by resource lock

    def test_intent_beats_lock_on_approach_diversity(self):
        """THE falsifiable claim: intent_gate produces richer approach vectors than lock_gate
        on the same parallel_useful scenario — the whole argument that metrics.py measures."""
        from core.coord.experiment import parallel_useful as scenario_fn
        from core.coord.experiment import intent_gate, lock_gate

        iv, is_ = run_metrics(scenario_fn, intent_gate, n_runs=3)
        lv, ls = run_metrics(scenario_fn, lock_gate, n_runs=3)

        # intent_gate: admits all 6 distinct intents → A_task = 1.0
        assert is_[0] == 1.0, f"intent_gate A_task should be 1.0, got {is_[0]}"
        # lock_gate: admits only the first action → 1 of 6 intents delivered
        assert ls[0] == pytest.approx(1/6, abs=0.001), (
            f"lock_gate should deliver 1/6 on parallel_useful, got {ls[0]}"
        )

        # APPROACH VECTOR RICHNESS:
        # intent_gate: each run admits ALL 6 actions → 6 (resource,intent) pairs per vector
        # lock_gate: each run admits only the FIRST → 1 (resource,intent) pair per vector
        # This is the MEASURED advantage: intent delivers 6x more approaches AND all 6 intents
        assert len(iv[0]) > len(lv[0]), (
            f"intent_gate admits {len(iv[0])} approaches per run, "
            f"lock_gate admits only {len(lv[0])}"
        )
        assert len(iv[0]) == 6, f"intent_gate should admit all 6 approaches, got {len(iv[0])}"
        assert len(lv[0]) == 1, f"lock_gate should admit only 1 approach, got {len(lv[0])}"

        # Both are deterministic → identical vectors each run → per-run diversity flat
        # (not dropping: same number of approaches each time)
        # But lock_gate's NARROW per-run diversity (log2(1)=0.0) vs intent_gate's BROAD (log2(6)=2.585)
        # is the signal: lock_gate can't explore if its one approach is wrong
        i_verdict = assess(iv, is_)
        l_verdict = assess(lv, ls)
        assert i_verdict.runs == 3
        assert l_verdict.runs == 3
        assert i_verdict.run_diversities[0] == pytest.approx(2.585, abs=0.001)  # log2(6)
        assert l_verdict.run_diversities[0] == 0.0                              # log2(1)
        # Neither is collapsing (deterministic = flat), but lock's zero diversity is the risk
        # The real live proof: run stochastic scenarios where lock_gate's narrowness HURTS

    def test_assess_flags_lock_gate_stagnation(self):
        """When correctness is flat AND diversity is low, assess() should flag it.
        lock_gate on collision_heavy: same intent repeated → blocks everything, entropy=0, A_task=high.
        That's the Goodhart trap: looks good but can't explore."""
        from core.coord.experiment import collision_heavy as scenario_fn
        from core.coord.experiment import lock_gate

        vectors, scores = run_metrics(scenario_fn, lock_gate, n_runs=5)
        v = assess(vectors, scores)

        # collision_heavy: all 6 actions are same (resource,intent) — one approach
        # lock_gate admits only the first, blocks the rest → A_task = 1.0 (the one intent delivered)
        # But diversity is 0.0 per run (single approach) and never changes → STAGNANT
        # This IS the Goodhart trap: perfect score, zero exploration, but not "collapsing"
        # because it was never diverse — it started narrow and stayed narrow
        assert v.uniqueness == 0.0, "all runs produce identical single-approach vectors"
        assert v.diversity_dropping is False, "diversity was never high, can't drop"
        assert v.correctness_flat is True
        # Stagnant: flat correctness + diversity not growing + not collapsing
        assert "STAGNANT" in v.diagnosis, (
            f"Expected STAGNANT diagnosis, got: {v.diagnosis}"
        )
