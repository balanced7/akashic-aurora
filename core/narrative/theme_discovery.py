"""ThemeDiscoverer (Spine v2, slice V6) -- embedding theme inference that augments the
keyword baseline, catching beats whose theme is present in MEANING but not in words.

Semantic Relationship: Beat member_of Theme (multi-label; keyword UNION confident-embedding)

Shape (measured, not assumed -- see tests/test_theme_discovery.py ablation gate):
  Pure embedding routing wins recall but TANKS precision (sprays false themes), so it
  loses on F1. The system's own stance is hybrid -- keywords win on dense technical
  tokens, embeddings recover the misses. So `assign` = keyword themes UNION embedding
  themes above tau, which beats the keyword baseline on recall AND F1 while keeping
  precision high.

  STAGE A -- seed routing (V6a): each theme has several short EXEMPLAR phrases; a beat's
    score for a theme is the MAX cosine over that theme's exemplars (short exemplars match
    short summaries far better than one long diluted phrase). Multi-label.
  STAGE B -- residual discovery (V6b, `discover()`): beats no theme claims are clustered
    (the C1 Clusterer) to surface NET-NEW themes not in the seed list, labeled by c-TF-IDF.

Deterministic & fail-soft: if the model is unavailable the exemplars don't embed and
`assign` returns keyword-only (== the baseline). tau is frozen by the V6c ablation sweep.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

from core.primitives.embedder import Embedder, get_embedder

# tau frozen by the V6c ablation sweep on the gold fixture (F1 peak on a wide 0.38-0.46 plateau).
DEFAULT_TAU = 0.44

# Several SHORT exemplar phrases per theme; a beat's theme score is the MAX cosine over them
# (short exemplars match short beat summaries far better than one long multi-concept phrase).
EXEMPLARS: Dict[str, List[str]] = {
    "routing": ["track routing", "which domain does this belong to", "switching the active track",
                "conversation disentanglement", "domain inference for a beat"],
    "logging": ["event logging", "the beat log", "emitting events and hooks",
                "mirroring commits into the ledger", "recording what happened"],
    "evaluation": ["testing and benchmarks", "metrics and acceptance bars", "test fixtures",
                   "verifying correctness", "regression tests", "measuring quality"],
    "design": ["design methodology", "refactoring strategy", "naming and architecture decisions",
               "schema on read", "deprecation strategy", "design principles and notes"],
    "memory": ["persistent storage", "the Store and Redis", "snapshot and restore of state",
               "caching", "single source of truth for data", "recall of saved knowledge"],
    "narrative": ["the narrative spine", "chapters and the atlas", "the story over the record",
                  "narrative structure", "chronicling beats into chapters"],
}


def _cos(a: Sequence[float], b: Sequence[float]) -> float:
    return float(np.array(a, dtype=float) @ np.array(b, dtype=float))   # unit vectors -> dot = cosine


class ThemeDiscoverer:
    """Hybrid multi-label theme assignment: keyword themes UNION confident embedding themes."""

    def __init__(self, embedder: Optional[Embedder] = None, *, tau: float = DEFAULT_TAU,
                 seeds: Optional[Dict[str, List[str]]] = None, keyword_assigner=None):
        self.embedder = embedder or get_embedder()
        self.tau = tau
        self.seeds = {t: list(xs) for t, xs in (seeds or EXEMPLARS).items()}
        self._kw = keyword_assigner
        # embed every exemplar once; keep per-theme vectors for max-pool scoring
        flat_t, flat_x = [], []
        for t, xs in self.seeds.items():
            for x in xs:
                flat_t.append(t); flat_x.append(x)
        vecs = self.embedder.embed_many(flat_x)
        self._theme_vecs: Dict[str, List[List[float]]] = {t: [] for t in self.seeds}
        for t, v in zip(flat_t, vecs):
            if v is not None:
                self._theme_vecs[t].append(v)
        # "ok" only when every theme has at least one embedded exemplar
        self._ok = all(self._theme_vecs[t] for t in self.seeds) and len(self.seeds) > 0

    @property
    def available(self) -> bool:
        return self._ok

    def _kw_assigner(self):
        if self._kw is None:
            from core.narrative.theme_assigner import get_theme_assigner
            self._kw = get_theme_assigner()
        return self._kw

    def scores(self, text: str) -> Dict[str, float]:
        """Per-theme MAX-over-exemplars cosine (for sweeps / the residual boundary). {} if no model."""
        if not self._ok or not text:
            return {}
        v = self.embedder.embed(text)
        if v is None:
            return {}
        return {t: max(_cos(v, sv) for sv in vs) for t, vs in self._theme_vecs.items()}

    def route(self, text: str) -> List[str]:
        """Pure-embedding themes: every theme whose max-exemplar cosine >= tau (sorted)."""
        return sorted(t for t, s in self.scores(text).items() if s >= self.tau)

    def assign(self, beat, hint=None) -> List[str]:
        """Multi-label theme ids = keyword themes UNION confident embedding themes. Falls back to
        keyword-only when the embedding model is unavailable (== the baseline; never loses theming)."""
        from core.narrative.theme_assigner import ThemeAssigner
        kw = self._kw_assigner().assign(beat, hint)
        if not self._ok:
            return kw
        return sorted(set(kw) | set(self.route(ThemeAssigner._text_of(beat, hint))))


_INSTANCE: Optional[ThemeDiscoverer] = None


def get_theme_discoverer() -> ThemeDiscoverer:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = ThemeDiscoverer()
    return _INSTANCE
