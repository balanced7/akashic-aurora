"""
Tests for memory consolidation -> chronicle (AgentMemory Phase D).

Run: py tests/test_consolidation.py
"""

import sys
import os
import tempfile

os.environ["AI_SETUP"] = tempfile.mkdtemp()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.learning.agent_memory import AgentMemory
from core.learning.consolidation import consolidate_memory_into_chronicle


def _seeded_memory():
    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    mem.record(task="install comfyui", success=True, learnings=["use the node manager"])
    mem.record(task="configure redis", success=False, learnings=["filtered port hangs connect"])
    mem.reflect(task="configure redis", what_went_wrong="48s hang",
                what_would_help="probe reachability first", confidence=0.9)
    return mem


def test_consolidates_to_chronicle():
    mem = _seeded_memory()
    cdir = tempfile.mkdtemp()
    report = consolidate_memory_into_chronicle(agent_memory=mem, chronicle_dir=cdir)
    assert report["from_records"] == 3, f"2 experiences + 1 reflection, got {report}"
    assert report["lessons"] >= 1 and report["critic_ok"] is True
    # every lesson is traceable back to a raw record (lossy + lossless pointer)
    assert report["included_sources"], "lessons must carry source pointers"
    # the chronicle file was generated and is readable
    text = open(report["chronicle"], encoding="utf-8").read()
    assert "auto-generated from memory" in text
    assert "use the node manager" in text or "probe reachability first" in text
    assert "(source:" in text, "skeleton lines carry source pointers"
    print("\n--- consolidation ---\n  experiences+reflections -> chronicle with source pointers OK")
    print(f"  {report['from_records']} records -> {report['lessons']} lessons -> {report['chronicle']}")


def test_does_not_touch_raw_memory():
    mem = _seeded_memory()
    before = len(mem.load_all_experiences())
    consolidate_memory_into_chronicle(agent_memory=mem, chronicle_dir=tempfile.mkdtemp())
    after = len(mem.load_all_experiences())
    assert before == after == 2, "consolidation must not delete/alter raw memory"
    print("\n--- raw is sacred ---\n  consolidation read-only on memory OK")


def test_empty_memory_graceful():
    empty = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "e.json")))
    report = consolidate_memory_into_chronicle(agent_memory=empty, chronicle_dir=tempfile.mkdtemp())
    assert report["from_records"] == 0 and report["lessons"] == 0
    assert os.path.exists(report["chronicle"]), "still writes a valid (empty) chronicle"
    print("\n--- empty ---\n  empty memory -> valid empty chronicle OK")


if __name__ == "__main__":
    print("=" * 60)
    print("CONSOLIDATION TESTS")
    print("=" * 60)
    test_consolidates_to_chronicle()
    test_does_not_touch_raw_memory()
    test_empty_memory_graceful()
    print("\n" + "=" * 60)
    print("ALL CONSOLIDATION TESTS PASSED")
    print("=" * 60)
