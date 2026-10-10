"""Paired statistics for agent evals (meta-harness task 05). Pure functions, no I/O.

Agent runs are noisy, so a verdict is never "A scored higher once". Following Miller, "Adding
error bars to evals" (arXiv 2411.00640):

  * differences are PER SCENARIO, between paired runs of the two candidates on the same task;
  * with several trials per scenario, the scenario is the cluster: trials are averaged inside a
    scenario first, and resampling draws whole scenarios (a cluster bootstrap), so ten trials
    of one easy task never pass for ten independent tasks;
  * pass/fail outcomes also get an exact McNemar test on the discordant scenarios;
  * the answer is an effect with an interval and one of: better, worse, can't tell.

Deterministic: every random draw uses a seeded generator, so a verdict re-computes identically.
"""

from __future__ import annotations

import math
import random
from statistics import fmean, pstdev
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

BETTER, WORSE, CANT_TELL = "better", "worse", "can't tell"


def scenario_means(trials: Mapping[str, Sequence[float]]) -> dict[str, float]:
    """scenario -> mean over its trials (the cluster average). Empty scenarios are dropped."""
    return {s: fmean(v) for s, v in trials.items() if len(v)}


def paired_diffs(a: Mapping[str, Sequence[float]], b: Mapping[str, Sequence[float]]) -> dict[str, float]:
    """scenario -> mean(b) - mean(a), over the scenarios both candidates ran."""
    ma, mb = scenario_means(a), scenario_means(b)
    return {s: mb[s] - ma[s] for s in sorted(set(ma) & set(mb))}


def bootstrap_ci(
    diffs: Sequence[float], *, level: float = 0.95, n_boot: int = 4000, seed: int = 7
) -> tuple[float, float, float]:
    """(mean, lo, hi): percentile cluster bootstrap over scenarios."""
    d = list(diffs)
    if not d:
        return (0.0, 0.0, 0.0)
    if len(d) == 1:
        return (d[0], d[0], d[0])
    rng = random.Random(seed)
    n = len(d)
    boots = sorted(fmean(d[rng.randrange(n)] for _ in range(n)) for _ in range(n_boot))
    lo = boots[int((1 - level) / 2 * n_boot)]
    hi = boots[min(n_boot - 1, int((1 + level) / 2 * n_boot))]
    return (fmean(d), lo, hi)


def clustered_se(diffs: Sequence[float]) -> float:
    """Standard error of the mean scenario difference (scenarios are the independent units)."""
    d = list(diffs)
    if len(d) < 2:
        return float("inf")
    return pstdev(d) * math.sqrt(len(d) / (len(d) - 1)) / math.sqrt(len(d))


def mcnemar_exact(a_pass: Mapping[str, bool], b_pass: Mapping[str, bool]) -> dict[str, float]:
    """Exact two-sided McNemar test on paired pass/fail. b10 = A passed and B failed."""
    common = set(a_pass) & set(b_pass)
    b10 = sum(1 for s in common if a_pass[s] and not b_pass[s])
    b01 = sum(1 for s in common if b_pass[s] and not a_pass[s])
    n = b10 + b01
    if n == 0:
        return {"b10": 0, "b01": 0, "p": 1.0}
    k = min(b10, b01)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return {"b10": b10, "b01": b01, "p": min(1.0, 2 * tail)}


def verdict(mean: float, lo: float, hi: float, *, higher_is_better: bool = True) -> str:
    """better / worse / can't tell, from an interval on (B - A)."""
    if lo > 0:
        return BETTER if higher_is_better else WORSE
    if hi < 0:
        return WORSE if higher_is_better else BETTER
    return CANT_TELL


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def power(
    n_scenarios: int, trials: int, delta: float, *, p0: float = 0.5, icc: float = 0.5, alpha: float = 0.05
) -> float:
    """Approximate power to detect a pass-rate change of `delta` with a paired design.

    Per-trial variance p(1-p); trials inside a scenario are correlated (intra-class correlation
    `icc`), so the variance of a scenario mean is var * (1 + (t-1)*icc) / t. The paired
    difference doubles it, and pairing recovers part of it -- taken as a factor (1 - icc).
    """
    p1 = min(0.999, max(0.001, p0 + delta))
    var = (p0 * (1 - p0) + p1 * (1 - p1)) / 2
    var_cluster = var * (1 + (trials - 1) * icc) / trials
    se = math.sqrt(2 * var_cluster * (1 - icc) / max(1, n_scenarios))
    z = 1.959963984540054 if abs(alpha - 0.05) < 1e-9 else _z(1 - alpha / 2)
    return _phi(abs(delta) / se - z) if se > 0 else 1.0


def _z(q: float) -> float:
    lo, hi = -10.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _phi(mid) < q else (lo, mid)
    return (lo + hi) / 2


def min_detectable(
    n_scenarios: int, trials: int, *, target_power: float = 0.8, p0: float = 0.5, icc: float = 0.5
) -> float:
    """The smallest pass-rate change this design detects with `target_power`."""
    lo, hi = 0.0, 1.0 - p0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if power(n_scenarios, trials, mid, p0=p0, icc=icc) < target_power else (lo, mid)
    return round(hi, 4)


def pareto(rows: Mapping[str, Mapping[str, float]], higher_is_better: Mapping[str, bool]) -> list[str]:
    """Names on the Pareto front: no other row is at least as good on every axis and strictly
    better on one."""
    names = list(rows)

    def dominates(x: str, y: str) -> bool:
        ge = all(
            (rows[x][k] >= rows[y][k]) if hib else (rows[x][k] <= rows[y][k]) for k, hib in higher_is_better.items()
        )
        gt = any((rows[x][k] > rows[y][k]) if hib else (rows[x][k] < rows[y][k]) for k, hib in higher_is_better.items())
        return ge and gt

    return [n for n in names if not any(dominates(m, n) for m in names if m != n)]
