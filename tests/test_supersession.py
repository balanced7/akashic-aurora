"""
Tests for Supersession: the primitive + AgentMemory integration + Ranker honoring it.

Run: py tests/test_supersession.py
"""

import sys
import os
import tempfile

os.environ["AI_SETUP"] = tempfile.mkdtemp()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.primitives import supersession as S
from core.primitives.ranker import Ranker
from core.foundation.store import FileStore
from core.learning.agent_memory import AgentMemory


def test_primitive():
    assert S.is_active({}) is True
    assert S.is_active({"superseded": True}) is False
    assert S.mark_supersedes({}, "old1")["supersedes"] == "old1"
    assert S.mark_supersedes({}, None) == {}            # no-op when nothing to supersede
    assert S.retire({})["superseded"] is True
    assert S.active_only([{"id": 1}, {"id": 2, "superseded": True}]) == [{"id": 1}]
    print("\n--- primitive ---\n  is_active/mark/retire/active_only OK")


def test_agent_memory_decision_supersession():
    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    old = mem.decide(title="Redis HA via Sentinel", decision="3-node sentinel")
    new = mem.decide(title="Single Redis", decision="simplify topology", supersedes=old)
    ids = [d.id for d in mem.get_decisions(days=365)]
    assert new in ids, "the new decision is active"
    assert old not in ids, "the superseded decision is excluded from reads"
    print("\n--- AgentMemory decisions ---\n  superseded decision retired from reads OK")


def test_agent_memory_experience_supersession():
    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "e.json")))
    old = mem.record(task="install comfyui nodes", success=False)
    new = mem.record(task="install comfyui nodes", success=True, supersedes=old)
    ids = [e.id for e in mem.get_similar("install comfyui nodes")]
    assert new in ids and old not in ids, "superseded experience excluded from retrieval"
    print("\n--- AgentMemory experiences ---\n  superseded experience retired from get_similar OK")


def test_ranker_still_honors_supersession():
    r = Ranker()
    out = r.rank([{"text": "x", "superseded": True}, {"text": "x"}], query="x", now=1.0)
    assert len(out) == 1, "Ranker (via the Supersession primitive) excludes superseded"
    print("\n--- Ranker ---\n  Ranker delegates active-check to Supersession OK")


if __name__ == "__main__":
    print("=" * 60)
    print("SUPERSESSION TESTS")
    print("=" * 60)
    test_primitive()
    test_agent_memory_decision_supersession()
    test_agent_memory_experience_supersession()
    test_ranker_still_honors_supersession()
    print("\n" + "=" * 60)
    print("ALL SUPERSESSION TESTS PASSED")
    print("=" * 60)
