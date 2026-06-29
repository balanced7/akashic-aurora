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

import math
import os
import re
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from core.primitives.embedder import Embedder, get_embedder

_TOKEN = re.compile(r"[a-z][a-z0-9_]{2,}")
# generic words that shouldn't become theme labels (c-TF-IDF already downweights cross-cluster
# words; this just drops obvious noise so tiny corpora still label cleanly)
_STOP = {"the", "and", "for", "with", "into", "from", "that", "this", "was", "are", "but",
         "not", "you", "your", "our", "its", "has", "have", "had", "will", "can", "onto",
         "per", "via", "add", "fix", "use", "using", "new", "get", "set", "run", "ran"}


def _ctfidf_terms(clusters_texts: Sequence[Sequence[str]], topk: int = 3) -> List[List[str]]:
    """Class-based TF-IDF (BERTopic-style, no LLM): the words that distinguish each CLUSTER
    from the others. Returns the top-k distinctive terms per cluster."""
    toks = [[w for w in _TOKEN.findall(" ".join(ts).lower()) if w not in _STOP]
            for ts in clusters_texts]
    if not toks:
        return []
    global_freq: Dict[str, int] = {}
    for tl in toks:
        for w in tl:
            global_freq[w] = global_freq.get(w, 0) + 1
    A = (sum(len(tl) for tl in toks) / len(toks)) or 1.0
    out: List[List[str]] = []
    for tl in toks:
        n = len(tl) or 1
        tf: Dict[str, int] = {}
        for w in tl:
            tf[w] = tf.get(w, 0) + 1
        weights = {w: (c / n) * math.log(1 + A / global_freq[w]) for w, c in tf.items()}
        out.append(sorted(weights, key=lambda w: (-weights[w], w))[:topk])
    return out

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

    # ------------------------------------------------------------------ V6b: discover net-new themes
    def discover(self, items: Sequence[Dict[str, Any]], *, min_residual: int = 6) -> List[Dict[str, Any]]:
        """Cluster the RESIDUAL beats (no seed theme claims them) to surface NET-NEW themes not in
        the seed vocabulary, labeled by c-TF-IDF (no LLM). `items`: dicts with id/text/[importance].
        Returns [{label, terms, beat_ids, size, cohesion}]. Empty below the cold-start floor or
        when the model is unavailable -- small-N clustering is unreliable."""
        if not self._ok:
            return []
        residual = [it for it in items if not self.route(str(it.get("text", "")))]
        if len(residual) < min_residual:
            return []                                   # cold-start guard
        from core.primitives.clusterer import get_clusterer
        clustering = get_clusterer(self.embedder).cluster(
            [{"id": it["id"], "text": it.get("text", ""), "importance": it.get("importance", 1)}
             for it in residual])
        text_by_id = {it["id"]: str(it.get("text", "")) for it in residual}
        cl_texts = [[text_by_id[a] for a in c.atom_ids] for c in clustering.clusters]
        term_lists = _ctfidf_terms(cl_texts)
        out: List[Dict[str, Any]] = []
        for c, terms in zip(clustering.clusters, term_lists):
            out.append({"label": " / ".join(terms) if terms else c.label[:40], "terms": terms,
                        "beat_ids": c.atom_ids, "size": len(c.atom_ids),
                        "cohesion": round(c.cohesion, 3)})
        return out


_INSTANCE: Optional[ThemeDiscoverer] = None


def get_theme_discoverer() -> ThemeDiscoverer:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = ThemeDiscoverer()
    return _INSTANCE


def select_theme_assigner(embedder: Optional[Embedder] = None):
    """The spine's write-path theme assigner (V6c). DETERMINISTIC by config: embedding theming is
    OPT-IN via `AKASHIC_EMBED_THEMES=1` -- so the same beat always themes the same way for a given
    configuration, and a short-lived CLI write never pays a cold model load by surprise.

      flag off (default) -> fast keyword baseline (unchanged behavior)
      flag on + model reachable -> hybrid ThemeDiscoverer (recovers keyword-miss themes)
      flag on + model absent -> keyword baseline (graceful)

    A consolidation re-theme pass (off the hot path) is the way to upgrade an existing corpus
    regardless of the flag -- that's the clean batch path; this seam is the per-write choice."""
    from core.narrative.theme_assigner import get_theme_assigner
    if os.getenv("AKASHIC_EMBED_THEMES", "").lower() not in ("1", "true", "yes", "on"):
        return get_theme_assigner()
    emb = embedder or get_embedder()
    return get_theme_discoverer() if emb.available else get_theme_assigner()
