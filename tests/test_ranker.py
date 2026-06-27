"""
Tests for the Ranker shared primitive.

Run: py tests/test_ranker.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.primitives.ranker import Ranker, Scored, keyword_relevance

NOW = 1_750_000_000.0  # fixed "now" for deterministic recency
DAY = 86400.0


def test_recency_decay():
    r = Ranker(half_life_days=14.0)
    fresh = {"text": "x", "timestamp": NOW}
    old = {"text": "x", "timestamp": NOW - 60 * DAY}
    out = r.rank([old, fresh], query="x", now=NOW)
    assert out[0].item is fresh, "fresher item should rank first"
    assert out[0].components["recency"] > out[1].components["recency"]
    print("\n--- recency ---\n  fresh outranks stale OK")


def test_importance_weight():
    r = Ranker()
    vital = {"text": "x", "importance": 5, "timestamp": NOW}
    trivial = {"text": "x", "importance": 1, "timestamp": NOW}
    out = r.rank([trivial, vital], query="x", now=NOW)
    assert out[0].item is vital, "higher importance should rank first"
    print("--- importance ---\n  importance 5 outranks 1 OK")


def test_relevance():
    r = Ranker()
    match = {"text": "install comfyui custom nodes", "timestamp": NOW}
    miss = {"text": "configure nginx reverse proxy", "timestamp": NOW}
    out = r.rank([miss, match], query="comfyui install", now=NOW)
    assert out[0].item is match, "query-matching item should rank first"
    assert out[0].components["relevance"] > 0 and out[1].components["relevance"] == 0
    print("--- relevance ---\n  query match outranks non-match OK")


def test_supersession_excluded():
    r = Ranker()
    active = {"text": "x", "timestamp": NOW}
    retired = {"text": "x", "timestamp": NOW, "superseded": True}
    out = r.rank([active, retired], query="x", now=NOW)
    assert len(out) == 1 and out[0].item is active, "superseded item must be excluded"
    print("--- supersession ---\n  superseded item excluded OK")


def test_relationship_weighting():
    r = Ranker(relationship_weights={"prevents": 1.0, "mentions": 0.1})
    strong = {"text": "x", "timestamp": NOW, "relationship_type": "prevents"}
    weak = {"text": "x", "timestamp": NOW, "relationship_type": "mentions"}
    out = r.rank([weak, strong], query="x", now=NOW)
    assert out[0].item is strong, "stronger relationship type should rank first"
    print("--- relationship ---\n  relationship-type weighting OK")


def test_top_k_and_components():
    r = Ranker()
    items = [{"text": f"item {i} comfyui", "importance": i, "timestamp": NOW} for i in range(1, 6)]
    out = r.rank(items, query="comfyui", now=NOW, top_k=2)
    assert len(out) == 2, "top_k should cap results"
    assert set(out[0].components) == {"relevance", "importance", "recency", "relationship"}
    assert abs(out[0].score - sum(r.weights[k] * out[0].components[k] for k in out[0].components)) < 1e-9
    print("--- top_k + components ---\n  cap + transparent weighted score OK")


def test_empty_query_ranks_by_other_signals():
    r = Ranker()
    a = {"text": "a", "importance": 5, "timestamp": NOW}
    b = {"text": "b", "importance": 1, "timestamp": NOW}
    out = r.rank([b, a], query="", now=NOW)
    assert out[0].item is a, "with no query, importance/recency should still order"
    print("--- empty query ---\n  ranks by importance/recency when no query OK")


def test_relevance_fn_seam():
    # embeddings seam: a custom relevance_fn is honored
    r = Ranker(relevance_fn=lambda text, query: 1.0 if "boost" in text else 0.0)
    boosted = {"text": "boost me", "timestamp": NOW}
    plain = {"text": "ordinary", "importance": 5, "timestamp": NOW}
    out = r.rank([plain, boosted], query="anything", now=NOW)
    assert out[0].item is boosted, "custom relevance_fn should drive ranking"
    print("--- relevance_fn seam ---\n  custom relevance function honored OK")


if __name__ == "__main__":
    print("=" * 60)
    print("RANKER TESTS")
    print("=" * 60)
    test_recency_decay()
    test_importance_weight()
    test_relevance()
    test_supersession_excluded()
    test_relationship_weighting()
    test_top_k_and_components()
    test_empty_query_ranks_by_other_signals()
    test_relevance_fn_seam()
    print("\n" + "=" * 60)
    print("ALL RANKER TESTS PASSED")
    print("=" * 60)
