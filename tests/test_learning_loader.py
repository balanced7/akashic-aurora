"""
Tests for context.learning_loader — the Ranker surfacing LearningStore records.

Run: py tests/test_learning_loader.py
"""

import sys
import os
import tempfile

# Isolate: AI_SETUP -> temp so the LearningStore does NOT import the real legacy
# learnings.jsonl, and FileStore writes to temp. Set BEFORE importing core.
os.environ["AI_SETUP"] = tempfile.mkdtemp()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.learning.learning_store import LearningStore
from core.context.learning_loader import load_learnings_ranked_by_relevance

NOW = 1_750_000_000.0
DAY = 86400.0
import datetime as _dt
def _iso(ts): return _dt.datetime.utcfromtimestamp(ts).isoformat()


def _seeded_store():
    store = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "ll.json")))
    # relevant + high-confidence + recent -> should top the list
    store.record_learning({"experiment_name": "comfyui_install", "category": "vision",
        "what_tried": "install ComfyUI custom nodes", "recommendation": "use the manager",
        "success": "yes", "confidence": "high", "timestamp": _iso(NOW)})
    # relevant but low-confidence + old
    store.record_learning({"experiment_name": "comfyui_old", "category": "vision",
        "what_tried": "manual ComfyUI node install", "recommendation": "avoid manual",
        "success": "no", "confidence": "low", "timestamp": _iso(NOW - 90 * DAY)})
    # irrelevant (different topic)
    store.record_learning({"experiment_name": "nginx_setup", "category": "infra",
        "what_tried": "configure nginx", "recommendation": "use reverse proxy",
        "success": "yes", "confidence": "high", "timestamp": _iso(NOW)})
    return store


def test_surfaces_relevant_ranked():
    store = _seeded_store()
    out = load_learnings_ranked_by_relevance("install comfyui", top_k=3,
                                            learning_store=store, now=NOW)
    assert out, "should return ranked learnings"
    assert out[0]["source"] == "comfyui_install", f"most relevant+confident+recent first, got {out[0]}"
    # the irrelevant nginx learning should rank below the relevant comfyui ones
    sources = [r["source"] for r in out]
    assert sources.index("comfyui_install") < sources.index("nginx_setup")
    print("\n--- ranking ---\n  relevant + high-confidence + recent surfaces first OK")
    print("  order:", sources)


def test_source_pointers_present():
    store = _seeded_store()
    out = load_learnings_ranked_by_relevance("comfyui", learning_store=store, now=NOW)
    assert all(r["source"] for r in out), "every entry must carry a source pointer (lossy+pointer rule)"
    # the pointer must resolve back to the full record in the store
    full = store.load_all_learnings_from_store()
    names = {l["experiment_name"] for l in full}
    assert all(r["source"] in names for r in out), "source must resolve to a real record"
    print("\n--- source pointers ---\n  every entry traceable back to LearningStore OK")


def test_top_k_and_empty():
    store = _seeded_store()
    out = load_learnings_ranked_by_relevance("comfyui", top_k=1, learning_store=store, now=NOW)
    assert len(out) == 1, "top_k caps results"
    empty = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "empty.json")))
    assert load_learnings_ranked_by_relevance("anything", learning_store=empty) == [], "empty store -> []"
    print("\n--- top_k + empty ---\n  cap works; empty store returns [] gracefully OK")


if __name__ == "__main__":
    print("=" * 60)
    print("LEARNING LOADER TESTS")
    print("=" * 60)
    test_surfaces_relevant_ranked()
    test_source_pointers_present()
    test_top_k_and_empty()
    print("\n" + "=" * 60)
    print("ALL LEARNING LOADER TESTS PASSED")
    print("=" * 60)
