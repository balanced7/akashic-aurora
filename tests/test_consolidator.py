"""
Slice S1 -- the shared Consolidator primitive (the one rank->distill engine).

Bar: the item() contract carries the fields Ranker+Distiller read; consolidate() ranks then
distills with lossless source pointers, deterministically; empty in -> empty out. The
behavior-identical refactor of the Chronicler + learning/consolidation is guarded by their
existing suites staying green.

Run: py -m pytest tests/test_consolidator.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.primitives.consolidator import Consolidator, get_consolidator


def test_item_contract():
    it = Consolidator.item(text="t", source="git:x", importance=4, timestamp="2026-01-01T00:00:00",
                           relationship_type="causes", kind="lesson")
    assert it == {"text": "t", "source": "git:x", "importance": 4,
                  "timestamp": "2026-01-01T00:00:00", "relationship_type": "causes", "kind": "lesson"}
    # defaults
    d = Consolidator.item(text="t", source="s")
    assert d["importance"] == 1 and d["timestamp"] is None and d["relationship_type"] is None


def test_consolidate_ranks_then_distills_with_pointers():
    c = Consolidator(token_budget=4000)
    items = [
        Consolidator.item(text="low importance note", source="git:a", importance=1,
                          timestamp="2026-01-01T00:00:00"),
        Consolidator.item(text="a salient milestone", source="git:b", importance=5,
                          timestamp="2026-01-02T00:00:00"),
    ]
    dist = c.consolidate(items, instruction="test", kind="beat", now=None)
    # every entry keeps a lossless source pointer; the skeleton names them
    assert dist.entries and all(e["source"] for e in dist.entries)
    assert "(source: git:b)" in dist.skeleton and "(source: git:a)" in dist.skeleton
    # the more important/recent item is ranked first
    assert dist.entries[0]["source"] == "git:b"


def test_empty_and_determinism():
    c = Consolidator()
    empty = c.consolidate([], instruction="x")
    assert empty.entries == [] and empty.skeleton == ""
    items = [Consolidator.item(text=f"item {i}", source=f"git:{i}", importance=i % 5,
                               timestamp=f"2026-01-0{i+1}T00:00:00") for i in range(4)]
    a = c.consolidate(items, now=1_750_000_000.0)
    b = c.consolidate(items, now=1_750_000_000.0)
    assert a.skeleton == b.skeleton, "same input + now -> identical output (deterministic)"


def test_singleton():
    assert get_consolidator() is get_consolidator()


if __name__ == "__main__":
    for fn in [test_item_contract, test_consolidate_ranks_then_distills_with_pointers,
               test_empty_and_determinism, test_singleton]:
        fn()
    print("ALL S1 CONSOLIDATOR TESTS PASSED")
