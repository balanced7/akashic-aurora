"""
Phase A verification for AgentMemory (the richer memory model, now persisted
through a Store). The acceptance criterion: everything round-trips with Redis
DOWN, via the File backend -- the durability the old Redis-only version lacked.

Run: py tests/test_agent_memory.py
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore, HybridStore
from core.learning.agent_memory import AgentMemory


def _fresh_memory(d):
    # File backend = the Redis-down durability path.
    return AgentMemory(store=FileStore(os.path.join(d, "mem.json")))


def test_decisions():
    with tempfile.TemporaryDirectory() as d:
        mem = _fresh_memory(d)
        dec_id = mem.decide(title="Use Sentinel", decision="Redis HA via Sentinel",
                            rationale=["auto failover"], context="HA needed")
        assert dec_id, "decide should return an id"
        decisions = mem.get_decisions(days=30)
        assert len(decisions) == 1 and decisions[0].title == "Use Sentinel"
        print("\n--- decisions (semantic) ---\n  decide/get_decisions OK")


def test_experiences_and_similarity():
    with tempfile.TemporaryDirectory() as d:
        mem = _fresh_memory(d)
        mem.record(task="install ComfyUI custom nodes", success=True, learnings=["use manager"])
        mem.record(task="configure nginx reverse proxy", success=False)
        similar = mem.get_similar("install ComfyUI again")
        assert any("ComfyUI" in e.task for e in similar), f"expected a ComfyUI match: {similar}"
        stats = mem.get_stats()
        assert stats["experiences"] == 2 and stats["recent_failures"] == 1
        assert 0 < stats["success_rate"] < 1
        print("\n--- experiences (episodic) ---\n  record/get_similar/get_stats OK")


def test_reflections_capped():
    with tempfile.TemporaryDirectory() as d:
        mem = _fresh_memory(d)
        for i in range(55):
            mem.reflect(task=f"task {i}", what_went_wrong="x", what_would_help="y",
                       confidence=0.9 if i % 2 == 0 else 0.3)
        # index must be capped at MAX_REFLECTIONS
        assert mem.store.zcard(mem.KEY_REFLECTION_INDEX) == mem.MAX_REFLECTIONS, \
            "reflection index should be trimmed to the newest 50"
        insights = mem.get_insights(min_confidence=0.6)
        assert insights and all(r["confidence"] >= 0.6 for r in insights)
        print("\n--- reflections (Reflexion) ---\n  reflect/cap-at-50/get_insights OK")


def test_approaches():
    with tempfile.TemporaryDirectory() as d:
        mem = _fresh_memory(d)
        mem.register_approach("vision", "florence2", "working", learnings=["fast"])
        mem.register_approach("vision", "blip", "failed")
        status = mem.get_component_status("vision")
        assert len(status["working"]) == 1 and len(status["failed"]) == 1
        assert status["working"][0]["name"] == "florence2"
        print("\n--- approaches (procedural) ---\n  register/get_component_status OK")


def test_log_failure_and_context():
    with tempfile.TemporaryDirectory() as d:
        mem = _fresh_memory(d)
        mem.decide(title="d1", decision="x")
        mem.record(task="t1", success=True)
        exp_id = mem.log_failure(title="redis timeout", root_cause="port filtered",
                                fix_applied="raw socket probe", component="infrastructure",
                                learnings=["fail-fast probe"])
        assert exp_id, "log_failure should return the experience id"
        stats = mem.get_stats()
        assert stats["recent_failures"] >= 1 and stats["reflections"] >= 1
        ctx = mem.get_context("anything")
        assert set(ctx) == {"decisions", "recent_experiences", "insights", "stats"}
        assert ctx["stats"]["experiences"] >= 2
        print("\n--- failure + context ---\n  log_failure/get_context OK")


def test_survives_reload():
    """Durability: a new AgentMemory on the same file sees prior data (Redis down)."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "mem.json")
        m1 = AgentMemory(store=FileStore(path))
        m1.decide(title="persisted decision", decision="keep me")
        m1.record(task="persisted task", success=True)
        m2 = AgentMemory(store=FileStore(path))
        assert any(x.title == "persisted decision" for x in m2.get_decisions())
        assert m2.get_stats()["experiences"] == 1
        print("\n--- durability ---\n  data survives reload with Redis down OK")


def test_hybrid_redis_down():
    """Construct exactly as production would (HybridStore) with Redis down."""
    with tempfile.TemporaryDirectory() as d:
        store = HybridStore.create(port=63999, file_path=os.path.join(d, "h.json"))
        assert store.redis_available is False
        mem = AgentMemory(store=store)
        assert mem.redis_available is False
        mem.decide(title="hybrid decision", decision="x")
        assert mem.get_decisions()[0].title == "hybrid decision"
        print("\n--- hybrid (Redis down) ---\n  full path works on File fallback OK")


if __name__ == "__main__":
    print("=" * 60)
    print("AGENT MEMORY — PHASE A VERIFICATION (Redis down)")
    print("=" * 60)
    test_decisions()
    test_experiences_and_similarity()
    test_reflections_capped()
    test_approaches()
    test_log_failure_and_context()
    test_survives_reload()
    test_hybrid_redis_down()
    print("\n" + "=" * 60)
    print("ALL AGENT MEMORY CHECKS PASSED")
    print("=" * 60)
