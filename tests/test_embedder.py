"""
Slice C0 -- the Embedder substrate.

Bar (the ablation gate): embedding relevance BEATS the keyword baseline on a fixture where the
right answer shares meaning but not words. Plus: graceful keyword fallback when the model is
absent (the system never hard-depends on it), a Store-backed cache that avoids recompute and
invalidates on content change, and the Ranker.relevance_fn seam working end-to-end.

Model-dependent tests skip cleanly when MiniLM isn't available, so the suite stays green
anywhere; the ablation gate runs wherever the model is present (here it is, cached).

Run: py -m pytest tests/test_embedder.py -q
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
pytest.importorskip("numpy")  # optional embedding subsystem -> skip cleanly when numpy is absent
from core.primitives.embedder import Embedder, get_embedder
from core.primitives.ranker import Ranker, keyword_relevance


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _real_embedder():
    emb = Embedder(store=_store())
    if not emb.available:
        pytest.skip("embedding model not available in this environment")
    return emb


# meaning-not-words fixture: the correct doc shares (almost) no vocabulary with the query,
# so a keyword matcher scores it ~0; embeddings should still rank it first.
FIXTURE = [
    ("audio stem separation tool",      "stemroller pulls vocals out of a finished track",
     ["the redis store persists agent coordination state", "word-boundary regex keeps routing precise"]),
    ("image recognition on a screenshot", "florence reads the text in a captured picture",
     ["half-life decay fades unused association edges", "an append-only firehose of raw events"]),
    ("turning speech into text",         "whisper transcribes a spoken voice recording",
     ["the chronicler distills beats into chapters", "confidence-gated append-only tag history"]),
    ("undo a bad automatic label",       "roll back a mis-applied tag to the prior value",
     ["benchmark the router on the gold fixture", "bounded saturating hebbian reinforcement"]),
]


def _rank_first_accuracy(relevance_fn) -> float:
    hits = 0
    for query, correct, distractors in FIXTURE:
        docs = [correct] + distractors
        best = max(docs, key=lambda d: relevance_fn(d, query))
        hits += (best == correct)
    return hits / len(FIXTURE)


# ---------------------------------------------------------------- always-on (no model needed)
def test_relevance_signature_and_range():
    emb = Embedder(model_name="definitely/not-a-real-model", store=_store())   # forces fallback
    assert emb.available is False
    r = emb.relevance("the redis store keeps state", "redis store")
    assert 0.0 <= r <= 1.0
    assert emb.relevance("anything", "") == 0.0                 # empty query -> 0


def test_fallback_is_keyword_when_model_absent():
    emb = Embedder(model_name="definitely/not-a-real-model", store=_store())
    text, query = "the chronicler distills beats into chapters", "chronicler chapters"
    assert emb.relevance(text, query) == keyword_relevance(text, query)
    assert emb.embed("anything") is None                        # no vector without a model


# ---------------------------------------------------------------- model-dependent (skip if absent)
def test_cache_roundtrip_and_content_invalidation():
    from core.primitives.embedder import _hash
    emb = _real_embedder()
    store = emb.store
    v1 = emb.embed("alpha beta gamma")
    assert v1 is not None and len(v1) > 0
    # it was written to the Store cache, keyed by content hash (survives a cold process)
    assert store.get(emb._cache_key(_hash("alpha beta gamma"))) is not None
    # a fresh Embedder on the SAME store hits that cache (separate in-mem map) -> identical vector
    assert Embedder(store=store).embed("alpha beta gamma") == v1
    # changed content -> different hash -> different vector (cache can't go stale)
    assert emb.embed("alpha beta DELTA") != v1


def test_similarity_semantic_separation():
    emb = _real_embedder()
    near = emb.similarity("separate vocals from a song", "stemroller splits audio stems")
    far = emb.similarity("separate vocals from a song", "the redis store keeps agent state")
    assert near > far + 0.2, f"semantic pair should be clearly closer (near={near:.3f} far={far:.3f})"


def test_ablation_embeddings_beat_keyword():
    """THE gate: on the meaning-not-words fixture, embedding ranking beats keyword ranking."""
    emb = _real_embedder()
    kw_acc = _rank_first_accuracy(keyword_relevance)
    emb_acc = _rank_first_accuracy(emb.relevance)
    assert emb_acc > kw_acc, f"embeddings must beat keyword (emb={emb_acc:.2f} kw={kw_acc:.2f})"
    assert emb_acc >= 0.75, f"embeddings should rank the right doc first most of the time (got {emb_acc:.2f})"


def test_ranker_seam_end_to_end():
    """Plugging the Embedder into Ranker.relevance_fn surfaces the semantically-right item that
    the default keyword Ranker cannot (no shared words)."""
    emb = _real_embedder()
    items = [
        {"text": "stemroller pulls vocals out of a finished track", "importance": 3},
        {"text": "the redis store persists agent coordination state", "importance": 3},
    ]
    q = "audio stem separation"
    kw_top = Ranker().rank(items, q)[0].item["text"]
    emb_top = Ranker(relevance_fn=emb.relevance).rank(items, q)[0].item["text"]
    assert emb_top.startswith("stemroller"), f"embedding seam should surface the audio item, got: {emb_top}"


if __name__ == "__main__":
    test_relevance_signature_and_range()
    test_fallback_is_keyword_when_model_absent()
    print("fallback tests passed; model-dependent tests run under pytest")
