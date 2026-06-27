"""
Tests for the Context pillar loaders: decision, blocker, briefing.
(learning_loader has its own test_learning_loader.py)

Run: py tests/test_context_loaders.py
"""

import sys
import os
import tempfile
import isolate_canonical  # noqa: F401 -- isolates file store (AI_SETUP) + Redis db 15 BEFORE foundation import

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.foundation.ledger import FileLedger
from core.learning.agent_memory import AgentMemory
from core.signals.agent_signal_ledger import AgentSignalLedger
from context.decision_loader import load_decisions_applicable_to_task
from context.blocker_loader import load_blockers_preventing_progress
from context.briefing_loader import load_briefing_from_previous_handoff


def test_decision_loader():
    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    mem.decide(title="use ledger for signals", decision="append-and-replay", rationale=["durable", "ordered"])
    mem.decide(title="use nginx", decision="reverse proxy", rationale=["routing"])
    out = load_decisions_applicable_to_task("signals ledger", top_k=5, agent_memory=mem)
    assert out, "should return ranked decisions"
    assert all(r["source"] for r in out), "every decision carries a source pointer"
    titles = [r["title"] for r in out]
    assert titles.index("use ledger for signals") < titles.index("use nginx"), \
        f"query-relevant decision should rank first, got {titles}"
    empty = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "e.json")))
    assert load_decisions_applicable_to_task("x", agent_memory=empty) == []
    print("\n--- decision_loader ---\n  ranks applicable decisions + source pointers + empty OK")


def test_blocker_loader():
    import context.project_context as pcmod
    pcmod.ProjectContextManager._instance = None      # fresh isolated singleton
    mgr = pcmod.ProjectContextManager()
    mgr.record_blocker_preventing_task("GPU allocation unavailable", "critical")
    mgr.record_blocker_preventing_task("minor cosmetic typo", "low")
    out = load_blockers_preventing_progress("", context_manager=mgr)
    assert len(out) == 2 and all(r["source"] for r in out)
    assert out[0]["severity"] == "critical", f"critical blocker should rank first, got {out}"
    print("\n--- blocker_loader ---\n  ranks active blockers by severity + source pointers OK")


def test_briefing_loader():
    sl = AgentSignalLedger(ledger=FileLedger(tempfile.mkdtemp()))
    sl.append_signal({"agent_id": "A", "signal_type": "handoff", "signal_number": 0,
                      "target_agent": "B", "task": "first task", "context": {"k": 1}})
    sl.append_signal({"agent_id": "A", "signal_type": "action", "signal_number": 1, "action_name": "noise"})
    sl.append_signal({"agent_id": "C", "signal_type": "handoff", "signal_number": 0,
                      "target_agent": "B", "task": "latest task", "context": {"k": 2}, "blockers": ["x"]})
    sl.append_signal({"agent_id": "A", "signal_type": "handoff", "signal_number": 2,
                      "target_agent": "OTHER", "task": "not for B"})
    b = load_briefing_from_previous_handoff("B", signal_ledger=sl)
    assert b is not None and b["task"] == "latest task", f"should get most recent handoff to B, got {b}"
    assert b["from_agent"] == "C" and b["blockers"] == ["x"] and b["source"]
    assert load_briefing_from_previous_handoff("NOBODY", signal_ledger=sl) is None
    print("\n--- briefing_loader ---\n  latest handoff to agent + none-for-unknown OK")


if __name__ == "__main__":
    print("=" * 60)
    print("CONTEXT LOADER TESTS (decision / blocker / briefing)")
    print("=" * 60)
    test_decision_loader()
    test_blocker_loader()
    test_briefing_loader()
    print("\n" + "=" * 60)
    print("ALL CONTEXT LOADER TESTS PASSED")
    print("=" * 60)
