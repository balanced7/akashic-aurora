"""
Tests for context.aggregator.assemble_context — the full Context pillar assembly.

Run: py tests/test_aggregator.py
"""

import sys
import os
import tempfile
import isolate_canonical  # noqa: F401 -- isolates file store (AI_SETUP) + Redis db 15 BEFORE foundation import

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.foundation.ledger import FileLedger
from core.learning.agent_memory import AgentMemory
from core.learning.learning_store import LearningStore
from core.signals.agent_signal_ledger import AgentSignalLedger
from context.aggregator import assemble_context


def _isolated_sources():
    mem = AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "m.json")))
    mem.decide(title="use ledger for signals", decision="append-and-replay", rationale=["durable"])
    mem.decide(title="store by key", decision="hash+index", rationale=["fast"])

    ls = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "l.json")))
    ls.record_learning({"experiment_name": "ledger_fallback", "category": "persistence",
        "what_tried": "ledger file fallback", "recommendation": "trust the fallback",
        "success": "yes", "confidence": "high"})

    import context.project_context as pcmod
    pcmod.ProjectContextManager._instance = None
    cm = pcmod.ProjectContextManager()
    cm.record_milestone_marking_progress("Context pillar", "build it")
    cm.set_current_task_with_details("building aggregator", "wave 2")
    cm.record_blocker_preventing_task("GPU allocation pending", "high")

    sl = AgentSignalLedger(ledger=FileLedger(tempfile.mkdtemp()))
    sl.append_signal({"agent_id": "planner", "signal_type": "handoff", "signal_number": 0,
                      "target_agent": "builder", "task": "build the aggregator",
                      "context": {"phase": "wave 2"}})
    return mem, ls, cm, sl


def test_full_assembly():
    mem, ls, cm, sl = _isolated_sources()
    ctx = assemble_context("build ledger context", agent="builder", token_budget=9000,
                           agent_memory=mem, learning_store=ls, context_manager=cm, signal_ledger=sl)
    s = ctx["sections"]
    # all the expected sections assembled
    assert "briefing" in s and s["briefing"]["task"] == "build the aggregator"
    assert s["decisions"] and s["learnings"] and s["blockers"], "ranked sections present"
    assert s["project_state"]["current_work"]["task"] == "building aggregator"
    # source pointers preserved through assembly (traceability)
    assert all(d["source"] for d in s["decisions"])
    assert all(l["source"] for l in s["learnings"])
    assert all(b["source"] for b in s["blockers"])
    assert s["briefing"]["source"]
    # budget accounting
    assert ctx["within_budget"] is True and ctx["approx_tokens"] > 0
    assert set(["decisions", "learnings", "blockers", "project_state", "briefing"]).issubset(set(ctx["coverage"]))
    # the distilled skeleton (progressive disclosure): compact, traceable, critic-ok
    assert isinstance(ctx["skeleton"], str) and ctx["skeleton"], "should have a compact skeleton"
    assert ctx["skeleton_ok"] is True, f"skeleton critic should pass: {ctx}"
    assert all(e["source"] for e in ctx["skeleton_entries"]), "every skeleton entry keeps a source pointer"
    # the briefing handoff leads the skeleton
    assert "handoff from planner" in ctx["skeleton"]
    print("\n--- full assembly ---\n  all sections + skeleton + source pointers + within budget OK")
    print(f"  coverage={ctx['coverage']}  ~tokens={ctx['approx_tokens']}/{ctx['token_budget']}  skeleton_entries={len(ctx['skeleton_entries'])}")


def test_budget_trims():
    mem, ls, cm, sl = _isolated_sources()
    # extra learnings so there's something to trim
    for i in range(6):
        ls.record_learning({"experiment_name": f"extra_{i}", "category": "persistence",
            "what_tried": f"ledger thing {i}", "recommendation": "x"*120, "success": "yes", "confidence": "medium"})
    tiny = assemble_context("ledger", token_budget=120,
                            agent_memory=mem, learning_store=ls, context_manager=cm)
    big = assemble_context("ledger", token_budget=9000,
                           agent_memory=mem, learning_store=ls, context_manager=cm)
    assert len(tiny["sections"]["learnings"]) <= len(big["sections"]["learnings"]), "tiny budget trims more"
    assert tiny["approx_tokens"] <= big["approx_tokens"]
    print("\n--- budget ---\n  smaller budget assembles fewer/shorter sections OK")
    print(f"  tiny ~tokens={tiny['approx_tokens']}  big ~tokens={big['approx_tokens']}")


if __name__ == "__main__":
    print("=" * 60)
    print("AGGREGATOR TESTS")
    print("=" * 60)
    test_full_assembly()
    test_budget_trims()
    print("\n" + "=" * 60)
    print("ALL AGGREGATOR TESTS PASSED")
    print("=" * 60)
