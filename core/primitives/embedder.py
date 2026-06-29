"""
Embedder (Slice C0) -- the embedding substrate. One local, CPU, offline model behind a tiny
interface, with a Store-backed vector cache and a graceful keyword fallback.

Semantic Relationship: Text embedded_to Vector (cached, model-optional)

Why it's a primitive (not bolted onto the router/themes/clusterer separately): there is exactly
ONE embedding seam in this system -- `Ranker.relevance_fn`. Everything that wants "meaning, not
just shared words" consumes it through `Embedder.relevance`, so the model is wired in one place
and every consumer (TrackRouter Tier-1, the Clusterer, recall, merge-overlap) gets it for free.

Design (CPU-first, best-effort):
- **Lazy load.** The model is loaded only on a cache MISS, once per process. With the Store cache
  warm, most calls never load it at all -- which matters because external agents shell out one
  short-lived process per command.
- **Store-backed cache.** `embed:<model>:<sha1(text)>` -> the vector (JSON). Survives across
  processes; a content change is a different hash = a natural miss = recompute (cache can't go
  stale). The model tag is in the key, so swapping models never collides.
- **Graceful fallback.** If sentence-transformers / the model is unavailable, `relevance` falls
  back to keyword overlap and `embed` returns None. The system NEVER hard-depends on the model.

Default model: all-MiniLM-L6-v2 (384-d, ~80MB, fast on CPU). Override via EMBED_MODEL. GPU is a
later refinement (just a `device=` change); CPU is the simplicity-first baseline.
"""
import hashlib
import json
import logging
import os
from typing import List, Optional, Sequence

from core.foundation.store import Store, create_store
from core.primitives.ranker import keyword_relevance

logger = logging.getLogger("embedder")

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class Embedder:
    """Text -> vector, with a Store cache and a keyword fallback. Never raises into callers."""

    def __init__(self, model_name: Optional[str] = None, store: Optional[Store] = None,
                 *, cache: bool = True):
        self.model_name = model_name or os.getenv("EMBED_MODEL", DEFAULT_MODEL)
        self.store = store if store is not None else (create_store() if cache else None)
        self._tag = self.model_name.split("/")[-1]
        self._model = None
        self._tried = False                 # have we attempted to load the model?
        self._available: Optional[bool] = None
        self._mem: dict = {}                # in-process cache: hash -> vector

    # ------------------------------------------------------------------ model
    @property
    def available(self) -> bool:
        """True if the embedding model loaded. Triggers a one-time lazy load attempt."""
        if self._available is None:
            self._load()
        return bool(self._available)

    @property
    def is_loaded(self) -> bool:
        """Whether the model is ALREADY loaded -- does NOT trigger a load. Lets a hot path (e.g.
        BeatLog write) pick the fast keyword route instead of paying a cold model load in a
        short-lived CLI process, while warm long-lived agents get embeddings for free."""
        return self._available is True

    def _load(self) -> None:
        if self._tried:
            return
        self._tried = True
        try:
            # prefer the local cache / offline -- the model is already downloaded; don't
            # block on a hub round-trip. (A user who wants a fresh download can unset these.)
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device="cpu")
            self._available = True
        except Exception as e:
            logger.warning(f"embedder unavailable ({type(e).__name__}: {e}); using keyword fallback")
            self._available = False

    # ------------------------------------------------------------------ embed
    def embed(self, text: str) -> Optional[List[float]]:
        """One text -> a unit vector (list of floats), or None if the model is unavailable."""
        return self.embed_many([text])[0]

    def embed_many(self, texts: Sequence[str]) -> List[Optional[List[float]]]:
        """Batch embed. Cache hits avoid the model entirely; only the misses are encoded
        (in one batch) and then cached. Returns a vector (or None on fallback) per input."""
        texts = [str(t or "") for t in texts]
        out: List[Optional[List[float]]] = [None] * len(texts)
        misses = []                                    # (index, text, hash)
        for i, t in enumerate(texts):
            h = _hash(t)
            if h in self._mem:
                out[i] = self._mem[h]
                continue
            cached = self._cache_get(h)
            if cached is not None:
                self._mem[h] = cached
                out[i] = cached
                continue
            misses.append((i, t, h))
        if misses and self.available:                  # `available` triggers the lazy load
            try:
                vecs = self._encode([t for _, t, _ in misses])
                for (i, _t, h), v in zip(misses, vecs):
                    self._mem[h] = v
                    self._cache_put(h, v)
                    out[i] = v
            except Exception as e:
                logger.warning(f"encode failed ({type(e).__name__}: {e}); leaving as fallback")
        return out

    def _encode(self, texts: List[str]) -> List[List[float]]:
        arr = self._model.encode(texts, normalize_embeddings=True)
        return [[float(x) for x in row] for row in arr]

    # ------------------------------------------------------------------ use
    def similarity(self, a: str, b: str) -> float:
        """Cosine similarity in [-1,1] (vectors are unit-normalized -> dot). Keyword fallback."""
        va, vb = self.embed_many([a, b])
        if va is None or vb is None:
            return keyword_relevance(a, b)
        return float(sum(x * y for x, y in zip(va, vb)))

    def relevance(self, text: str, query: str) -> float:
        """Ranker.relevance_fn adapter -> [0,1]. Cosine (negatives clamped to 0); falls back to
        keyword overlap when the model is unavailable. Empty query -> 0 (matches keyword_relevance)."""
        if not query:
            return 0.0
        vt, vq = self.embed_many([text, query])
        if vt is None or vq is None:
            return keyword_relevance(text, query)
        cos = sum(x * y for x, y in zip(vt, vq))
        return max(0.0, min(1.0, cos))

    # ------------------------------------------------------------------ cache
    def _cache_key(self, h: str) -> str:
        return f"embed:{self._tag}:{h}"

    def _cache_get(self, h: str) -> Optional[List[float]]:
        if self.store is None:
            return None
        try:
            raw = self.store.get(self._cache_key(h))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def _cache_put(self, h: str, vec: List[float]) -> None:
        if self.store is None:
            return
        try:
            self.store.set(self._cache_key(h), json.dumps(vec))
        except Exception:
            pass


_INSTANCE: Optional[Embedder] = None


def get_embedder(store: Optional[Store] = None) -> Embedder:
    """Module singleton (lazy). Pass `store` for an isolated Embedder (tests/trial)."""
    global _INSTANCE
    if store is not None:
        return Embedder(store=store)
    if _INSTANCE is None:
        _INSTANCE = Embedder()
    return _INSTANCE
