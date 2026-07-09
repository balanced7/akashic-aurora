"""Forge F2 optimizer pass (core/recall/forge_optimizer.py) -- characterization.

The discipline: selection is curator-named (rehab class) minus in-flight work; the payload
is BLINDED (no replay contexts ever enter the prompt); malformed replies are dropped, not
guessed at; gate verdicts route (PASS/UNMEASURABLE -> pending proposal for the human,
FAIL -> the gate's rejected buffer); a pending proposal blocks re-selection. The model
call is an injected callable -- no network anywhere in these tests.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.forge_optimizer import (select_targets, build_prompt, parse_reply,
                                         run_pass, pending_proposals)
from core.learning.learning_store import LearningStore
from core.foundation.store import FileStore

INCUMBENT = ("Use when editing the consolidator seam pipeline, before refactoring: route "
             "every source through the one consolidator seam quickly. Don't when prototyping.")
GOOD_EDIT = ("Use when editing the consolidator seam, before refactoring: route every "
             "source through the one consolidator seam. Don't when prototyping.")
EVENTS = [{"kind": "flip", "at": "2026-07-08T10:00:00",
           "detail": {"target": "p:core/primitives/consolidator.py", "credited": 2,
                      "sources": ["learn:experiment:seam_guard"]}}]
INJECTIONS = [
    {"at": 1.0, "t": "p:core/primitives/consolidator.py", "s": ["learn:experiment:seam_guard"]},
    {"at": 2.0, "t": "c:py run pipeline task quickly", "s": ["learn:experiment:seam_guard"]},
]


def _fixture():
    d = tempfile.mkdtemp()
    ls = LearningStore(store=FileStore(os.path.join(d, "learn.json")))
    ls.persist_learning_derived_from_experiment({
        "experiment_name": "seam_guard", "what_tried": "moved the seam",
        "actual_outcome": "gate fires", "success": "yes",
        "recommendation": INCUMBENT, "agent_id": "t", "category": "architecture"})
    use = FileStore(os.path.join(d, "use.json"))
    use.set("recall:use:learn:experiment:seam_guard", json.dumps({"surfaced": 12}))
    return ls, use


def test_select_targets_rehab_minus_inflight():
    ls, use = _fixture()
    got = select_targets(store=use, learning_store=ls)
    assert [t["experiment_name"] for t in got] == ["seam_guard"], got
    # a pending proposal blocks re-selection
    assert ls.stamp_forge_proposal("seam_guard", "draft text", "PASS", by="t") is True
    assert select_targets(store=use, learning_store=ls) == []
    ls.clear_forge_proposal("seam_guard")
    # a provisional edit blocks too (one edit in flight per lesson)
    ls.store.hset("learn:experiment:seam_guard", mapping={"forge_provisional": "2026-07-09T00:00:00"})
    assert select_targets(store=use, learning_store=ls) == []
    print("\n--- selection ---\n  rehab picked; pending proposal and provisional both block OK")


def test_prompt_is_blinded_and_carries_the_buffer():
    ls, _ = _fixture()
    ls.mark_forge_rejected("seam_guard", "a rejected draft", ["axis 1: lost context"])
    rec = ls._load_experiment("seam_guard")
    prompt = build_prompt(rec, counters={"surfaced": 12}, trigger_terms=["consolidator"])
    assert "p:core/primitives/consolidator.py" not in prompt, "raw contexts must NEVER enter the prompt"
    assert "c:py run pipeline" not in prompt
    assert "a rejected draft" in prompt and "surfaced=12" in prompt
    assert "PROPOSED-RECOMMENDATION-BEGIN" in prompt
    assert "stays silent otherwise" in prompt, "goal framing: help, not credit-farming"
    print("--- blinding ---\n  no contexts in prompt; buffer + aggregates + framing present OK")


def test_parse_reply_strict():
    good = "noise\nPROPOSED-RECOMMENDATION-BEGIN\nUse when X, before Y: Z. Don't when W.\nPROPOSED-RECOMMENDATION-END\nRATIONALE: tighter."
    p = parse_reply(good)
    assert p["draft"].startswith("Use when X") and p["rationale"] == "tighter."
    assert parse_reply("no markers here") == {}
    assert parse_reply("PROPOSED-RECOMMENDATION-BEGIN\n\nPROPOSED-RECOMMENDATION-END") == {}
    print("--- parsing ---\n  markers required; empty/malformed dropped OK")


def test_run_pass_end_to_end_stamps_proposal():
    ls, use = _fixture()
    def propose(prompt):
        return ("PROPOSED-RECOMMENDATION-BEGIN\n" + GOOD_EDIT +
                "\nPROPOSED-RECOMMENDATION-END\nRATIONALE: dropped promiscuous terms.")
    rows = run_pass(propose, store=use, learning_store=ls,
                    events=EVENTS, injections=INJECTIONS, min_relevance=0.05)
    assert len(rows) == 1 and rows[0]["verdict"] == "PASS", rows
    assert rows[0]["outcome"] == "queued for human review"
    props = pending_proposals(learning_store=ls)
    assert len(props) == 1 and props[0]["experiment"] == "seam_guard"
    assert props[0]["verdict"] == "PASS" and props[0]["by"] == "deepseek-optimizer"
    # second pass: the pending proposal blocks re-selection (no duplicate work)
    assert run_pass(propose, store=use, learning_store=ls,
                    events=EVENTS, injections=INJECTIONS, min_relevance=0.05) == []
    print("--- run_pass ---\n  propose -> gate PASS -> queued; pending blocks the next pass OK")


def test_run_pass_drops_malformed_and_buffers_fails():
    ls, use = _fixture()
    rows = run_pass(lambda p: "no markers at all", store=use, learning_store=ls,
                    events=EVENTS, injections=INJECTIONS, min_relevance=0.05)
    assert rows[0]["outcome"].startswith("malformed-reply"), rows
    assert pending_proposals(learning_store=ls) == []
    hollow = ("PROPOSED-RECOMMENDATION-BEGIN\nUse when editing the consolidator seam "
              "pipeline, before refactoring: ok. Don't when prototyping."
              "\nPROPOSED-RECOMMENDATION-END\nRATIONALE: shorter.")
    rows2 = run_pass(lambda p: hollow, store=use, learning_store=ls,
                     events=EVENTS, injections=INJECTIONS, min_relevance=0.05)
    assert rows2[0]["verdict"] == "FAIL" and "rejected by gate" in rows2[0]["outcome"], rows2
    buf = json.loads(ls._load_experiment("seam_guard").get("forge_rejected") or "[]")
    assert buf, "gate FAIL must land in the durable rejected buffer"
    assert pending_proposals(learning_store=ls) == [], "FAILs never queue for the human"
    def boom(prompt):
        raise RuntimeError("api down")
    rows3 = run_pass(boom, store=use, learning_store=ls,
                     events=EVENTS, injections=INJECTIONS, min_relevance=0.05)
    assert rows3[0]["outcome"].startswith("error:"), rows3
    print("--- failure routing ---\n  malformed dropped; FAIL buffered not queued; api error contained OK")


if __name__ == "__main__":
    print("=" * 60)
    print("FORGE F2 OPTIMIZER PASS")
    print("=" * 60)
    test_select_targets_rehab_minus_inflight()
    test_prompt_is_blinded_and_carries_the_buffer()
    test_parse_reply_strict()
    test_run_pass_end_to_end_stamps_proposal()
    test_run_pass_drops_malformed_and_buffers_fails()
    print("\nALL FORGE F2 TESTS PASSED")
