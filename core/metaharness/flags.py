"""Bayesian optimisation over harness flags (meta-harness task 07, step 6; HARBOR-style).

Prose pieces go to the proposer (GEPA-style reflection). On/off and number settings -- a hook
switched on, a recall floor, a turn budget, compaction -- are a small, typed search space where
a model of "config -> score" beats asking an LLM to guess. HARBOR treats the harness config as
flags and tunes it with constrained, noisy Bayesian optimisation; this is that, kept small:

  * a Gaussian process with an RBF kernel and an explicit NOISE term, because two runs of the
    same config disagree, over flags scaled to [0, 1];
  * expected improvement over a random candidate pool, so the next config balances "probably
    good" against "not tried yet";
  * a constraint (for example cost per run <= a cap) handled by a second GP: EI is multiplied by
    the probability the constraint holds.

A SPACE is a dict: {"name": {"type": "bool"} | {"type": "int", "min": a, "max": b} |
{"type": "float", "min": a, "max": b}}. A config is a dict of values. `render` writes a config
into an overlay settings file, so each suggestion becomes an ordinary archive candidate.
"""

from __future__ import annotations

import json
import math
import random
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from pathlib import Path


def _encode(space: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> list[float]:
    out = []
    for name, spec in sorted(space.items()):
        v = cfg[name]
        if spec["type"] == "bool":
            out.append(1.0 if v else 0.0)
        else:
            lo, hi = float(spec["min"]), float(spec["max"])
            out.append((float(v) - lo) / (hi - lo) if hi > lo else 0.0)
    return out


def sample(space: dict[str, dict[str, Any]], rng: random.Random) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    for name, spec in sorted(space.items()):
        if spec["type"] == "bool":
            cfg[name] = rng.random() < 0.5
        elif spec["type"] == "int":
            cfg[name] = rng.randint(int(spec["min"]), int(spec["max"]))
        else:
            cfg[name] = rng.uniform(float(spec["min"]), float(spec["max"]))
    return cfg


class GP:
    """Zero-mean GP regression on standardised targets, RBF kernel, fixed noise."""

    def __init__(self, length: float = 0.3, noise: float = 0.05):
        self.length, self.noise = length, noise

    def fit(self, x: list[list[float]], y: list[float]) -> GP:
        self.x = np.asarray(x, dtype=float)
        yv = np.asarray(y, dtype=float)
        self.mu, self.sd = float(yv.mean()), float(yv.std() or 1.0)
        self.y = (yv - self.mu) / self.sd
        k = self._k(self.x, self.x) + self.noise * np.eye(len(self.x))
        self.l_chol = np.linalg.cholesky(k + 1e-9 * np.eye(len(self.x)))
        self.alpha = np.linalg.solve(self.l_chol.T, np.linalg.solve(self.l_chol, self.y))
        return self

    def _k(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        d2 = ((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)
        return np.exp(-0.5 * d2 / self.length**2)

    def predict(self, x: list[list[float]]) -> tuple[np.ndarray, np.ndarray]:
        xs = np.asarray(x, dtype=float)
        ks = self._k(xs, self.x)
        mean = ks @ self.alpha
        v = np.linalg.solve(self.l_chol, ks.T)
        var = np.clip(1.0 - (v**2).sum(0), 1e-12, None)
        return mean * self.sd + self.mu, np.sqrt(var) * self.sd


def _phi(z: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * z**2) / math.sqrt(2 * math.pi)


def _cdf(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))


def suggest(
    space: dict[str, dict[str, Any]],
    history: list[dict[str, Any]],
    *,
    n: int = 1,
    seed: int = 0,
    n_init: int = 4,
    pool: int = 512,
    constraint: tuple[str, float] | None = None,
) -> list[dict[str, Any]]:
    """The next `n` configs to try. `history` rows: {"config": {...}, "score": float, <metric>: float}.
    `constraint` = (metric, cap): keep that metric <= cap. Random until n_init points exist."""
    rng = random.Random(seed + len(history))
    seen = {json.dumps(h["config"], sort_keys=True) for h in history}
    if len(history) < n_init:
        out = []
        while len(out) < n:
            c = sample(space, rng)
            if json.dumps(c, sort_keys=True) not in seen:
                out.append(c)
                seen.add(json.dumps(c, sort_keys=True))
        return out
    x = [_encode(space, h["config"]) for h in history]
    gp = GP().fit(x, [float(h["score"]) for h in history])
    best = (
        max(
            float(h["score"])
            for h in history
            if constraint is None or float(h.get(constraint[0], 0.0)) <= constraint[1]
        )
        if history
        else 0.0
    )
    cgp = GP().fit(x, [float(h.get(constraint[0], 0.0)) for h in history]) if constraint else None
    cands = [sample(space, rng) for _ in range(pool)]
    cands = [c for c in cands if json.dumps(c, sort_keys=True) not in seen] or cands
    xc = [_encode(space, c) for c in cands]
    mean, sd = gp.predict(xc)
    z = (mean - best) / sd
    ei = (mean - best) * _cdf(z) + sd * _phi(z)
    if cgp is not None and constraint is not None:
        cm, cs = cgp.predict(xc)
        ei = ei * _cdf((constraint[1] - cm) / cs)
    order = np.argsort(-ei)
    out, keys = [], set()
    for i in order:
        k = json.dumps(cands[int(i)], sort_keys=True)
        if k not in keys:
            out.append(cands[int(i)])
            keys.add(k)
        if len(out) >= n:
            break
    return out


def render(cfg: dict[str, Any], overlay: Path, *, target: str = ".claude/settings.json", key: str = "env") -> Path:
    """Write a config into an overlay settings file under `key` (env vars by default), merging
    with what the overlay already holds. Booleans become "1"/"0" for env."""
    p = overlay / target
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = {}
    block = doc.setdefault(key, {})
    for k, v in cfg.items():
        block[k] = ("1" if v else "0") if isinstance(v, bool) and key == "env" else (str(v) if key == "env" else v)
    p.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p
