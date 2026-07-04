"""
Solution-Space-Shrinkage Tracker — the Metric C cross-run watchdog.

Measures ENTROPY of approach vectors across N experiment runs and detects the failure mode GPT named:
*monotonic diversity drop + flat correctness = collapse*. The policy is converging on a local optimum
that looks good on easy tasks but can't handle novel ones.

Model
-----
An "approach vector" is the set of (resource, intent) pairs an agent proposes in a run — the distinct
solution paths it attempted. Across runs, we track:
  * diversity — Shannon entropy of the multiset of approach vectors (how many different strategies?)
  * uniqueness — fraction of vectors that appeared in exactly one run
  * monotonicity — is diversity strictly decreasing run over run? (the danger signal)
  * collapse — diversity dropped AND correctness is flat (the Goodhart verdict)

This is deterministic, like experiment.py: no randomness, pure structural measurement of the policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import log2
from typing import Dict, List, FrozenSet, Tuple


# --- approach vectors ---

ApproachVector = FrozenSet[Tuple[str, str]]  # {(resource, intent), ...}


def vector_from_run(actions: List[Tuple[str, str, str]]) -> ApproachVector:
    """Extract the approach vector from a run's approved actions: the set of (resource, intent) pairs."""
    return frozenset((a[1], a[2]) for a in actions)


# --- entropy (pure function) ---

def shannon_entropy(vectors: List[ApproachVector]) -> float:
    """Shannon entropy H(X) of the multiset of approach vectors. A single uniform vector = 0 bits
    (no diversity). N distinct vectors each appearing once = log2(N) bits (max diversity)."""
    n = len(vectors)
    if n == 0:
        return 0.0
    counts: Dict[ApproachVector, int] = {}
    for v in vectors:
        counts[v] = counts.get(v, 0) + 1
    total = 0.0
    for c in counts.values():
        p = c / n
        if p > 0:
            total -= p * log2(p)
    return round(total, 4)


def uniqueness_ratio(vectors: List[ApproachVector]) -> float:
    """Fraction of vectors that appeared EXACTLY once. 1.0 = every run tried a different approach."""
    n = len(vectors)
    if n == 0:
        return 0.0
    counts: Dict[ApproachVector, int] = {}
    for v in vectors:
        counts[v] = counts.get(v, 0) + 1
    unique = sum(1 for c in counts.values() if c == 1)
    return round(unique / n, 4)


# --- monotonicity detector ---

def is_monotonic_decreasing(entropies: List[float]) -> bool:
    """True if entropy is strictly non-increasing run over run (e_n >= e_n+1 for all n).
    A single value is trivially monotonic; fewer than 2 values is not enough data."""
    if len(entropies) < 2:
        return False
    for i in range(len(entropies) - 1):
        if entropies[i] < entropies[i + 1]:  # went UP — not monotonic decreasing
            return False
    return True


# --- correctness (flat or rising?) ---

def is_flat(values: List[float], epsilon: float = 0.001) -> bool:
    """True if all values are within epsilon of each other (neither clearly rising nor falling).
    Fewer than 2 values = not enough data to judge."""
    if len(values) < 2:
        return False
    return max(values) - min(values) <= epsilon


def is_rising(values: List[float]) -> bool:
    """True if non-decreasing with at least one strict increase."""
    if len(values) < 2:
        return False
    strict_once = False
    for i in range(len(values) - 1):
        if values[i] > values[i + 1]:
            return False
        if values[i] < values[i + 1]:
            strict_once = True
    return strict_once


# --- the watchdog ---

@dataclass
class ShrinkageVerdict:
    """What the cross-run tracker found."""

    runs: int
    run_diversities: List[float]                # diversity signal PER RUN (e.g. approach count)
    cross_entropy: float                        # symbol entropy across all run-vectors (strategy variety)
    uniqueness: float                           # overall uniqueness ratio
    diversity_dropping: bool                    # monotonic decreasing PER-RUN diversity
    correctness_flat: bool                      # task scores not improving
    collapse: bool                              # THE verdict: dropping + flat = Goodhart
    diagnosis: str                              # human-readable summary


def _run_diversity(v: ApproachVector) -> float:
    """Diversity signal for a single run: log2 of the number of distinct (resource,intent) pairs.
    1 approach = 0, 2 = 1.0, 4 = 2.0, etc. This is the PER-RUN signal that trends toward zero
    as the solution space shrinks."""
    n = len(v)
    if n <= 1:
        return 0.0
    return round(log2(n), 4)


def assess(
    run_vectors: List[ApproachVector],
    run_scores: List[float],
    *,
    epsilon: float = 0.001,
) -> ShrinkageVerdict:
    """The watchdog: given N runs' approach vectors and their A task scores, diagnose whether the
    system is collapsing toward a local optimum (Goodhart's Law in action).

    Measures TWO diversity signals:
      1. PER-RUN diversity — log2(approaches per run). A run with 6 approaches is more exploratory
         than a run with 1. TRENDS on this to detect shrinkage: if runs start with 6 approaches and
         end with 1, the space is collapsing.
      2. CROSS-RUN symbol entropy — Shannon entropy of the multiset of approach vectors. High = many
         distinct strategies tried; low = monoculture. Reported as context, not trended.

    Args:
        run_vectors: one ApproachVector per run (the distinct approaches attempted)
        run_scores: one A_task score per run (fraction of intended work delivered)
        epsilon: tolerance for "flat" correctness

    Returns:
        ShrinkageVerdict with the full diagnosis

    Raises:
        ValueError if len(run_vectors) != len(run_scores)
    """
    if len(run_vectors) != len(run_scores):
        raise ValueError(
            f"run_vectors ({len(run_vectors)}) and run_scores ({len(run_scores)}) must be same length"
        )

    n = len(run_vectors)
    if n == 0:
        return ShrinkageVerdict(
            runs=0, run_diversities=[], cross_entropy=0.0, uniqueness=0.0,
            diversity_dropping=False, correctness_flat=False, collapse=False,
            diagnosis="No data: nothing to assess.",
        )

    # Per-run diversity signal: how many approaches each run attempted
    run_diversities = [_run_diversity(v) for v in run_vectors]

    # Cross-run symbol entropy: how many distinct STRATEGIES across all runs
    cross_entropy = shannon_entropy(run_vectors)
    uniq = uniqueness_ratio(run_vectors)

    # Diversity is "dropping" iff monotonic non-increasing AND at least one strict drop
    # (all-equal is flat, not dropping — the space isn't shrinking, it's static)
    diversity_dropping = (
        is_monotonic_decreasing(run_diversities)
        and len(run_diversities) >= 2
        and run_diversities[-1] < run_diversities[0]
    )
    correctness_flat = is_flat(run_scores, epsilon)
    correctness_rising = is_rising(run_scores)
    collapse = diversity_dropping and correctness_flat and not correctness_rising

    # Build diagnosis
    if collapse:
        diagnosis = (
            f"COLLAPSE: per-run diversity is dropping ({run_diversities[0]:.3f}→{run_diversities[-1]:.3f}) "
            f"but correctness is flat ({run_scores[-1]:.3f}). The policy is converging on a "
            f"local optimum — Goodhart's Law in action. It looks good on known tasks but is "
            f"losing the exploration needed for novel problems."
        )
    elif diversity_dropping and correctness_rising:
        diagnosis = (
            f"CONVERGING WELL: per-run diversity is dropping ({run_diversities[0]:.3f}→{run_diversities[-1]:.3f}) "
            f"AND correctness is rising ({run_scores[0]:.3f}→{run_scores[-1]:.3f}) — the policy is "
            f"narrowing toward a genuinely better solution, not collapsing."
        )
    elif diversity_dropping:
        diagnosis = (
            f"WATCH: per-run diversity is dropping ({run_diversities[0]:.3f}→{run_diversities[-1]:.3f}) but "
            f"correctness is neither clearly rising nor clearly flat. Not enough signal to call "
            f"collapse, but the trend warrants attention."
        )
    elif correctness_flat and len(run_diversities) >= 2 and run_diversities[-1] <= run_diversities[0]:
        diagnosis = (
            f"STAGNANT: correctness is flat ({run_scores[-1]:.3f}) and diversity isn't growing. "
            f"Not yet a collapse (diversity isn't monotonically dropping), but exploration isn't "
            f"producing gains."
        )
    else:
        diagnosis = (
            f"HEALTHY: per-run diversity {run_diversities[-1]:.3f} across {n} runs "
            f"(cross-entropy {cross_entropy:.3f}, uniqueness {uniq:.2%}), "
            f"correctness {run_scores[-1]:.3f}. No collapse signal."
        )

    return ShrinkageVerdict(
        runs=n,
        run_diversities=run_diversities,
        cross_entropy=cross_entropy,
        uniqueness=uniq,
        diversity_dropping=diversity_dropping,
        correctness_flat=correctness_flat,
        collapse=collapse,
        diagnosis=diagnosis,
    )


# --- convenience: wrap a scenario + policy into run data ---
def run_metrics(
    scenario_fn,
    policy_fn,
    n_runs: int = 5,
) -> Tuple[List[ApproachVector], List[float]]:
    """Run the same scenario+policy N times, return vectors and A_task scores.
    Deterministic: same seed, same output each time (isolates policy structure, not LLM variance)."""
    from core.coord.experiment import run, score  # local import: experiment.py is sibling

    vectors = []
    scores = []
    for _ in range(n_runs):
        scenario = scenario_fn()
        outcome = run(scenario, policy_fn)
        s = score(scenario, outcome)
        vectors.append(vector_from_run([(a.agent, a.resource, a.intent) for a in outcome.admitted]))
        scores.append(s["A_task"])
    return vectors, scores
