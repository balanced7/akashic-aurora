"""
T210 -- discover, at the level of MEANING. RED first.

THE WEAKNESS THIS OFFLOADS TO THE SUBSTRATE, measured on me across two days. Three times
I concluded a capability was missing WITHOUT CHECKING, and all three were wrong:

  * T197 -- I scoped a slice to build a peer-liveness reader. `liveness.attendance()` had
    existed since T155 and already resolved the exact defect I planned to solve.
  * T208 -- I hand-bisected four test failures with `git stash`, one of them wrongly and
    in public. `state/coord/suite_baseline.json` had recorded one of them since 2026-07-24.
  * W133 -- I filed a wish asserting the naming doctrine was UNGUARDED.
    `check_boundaries.py` shipped that guard on 2026-06-19 and runs it in CI.

One failure mode, three costumes: I INFER ABSENCE INSTEAD OF VERIFYING IT. Not from
laziness -- verifying costs a turn AT THE MOMENT OF THE ASSUMPTION, while being wrong
costs nothing until later. The only fix that changes that behaviour is making the check
cheaper than the assumption, at the moment of assuming.

WHY THE EXISTING `discover` COULD NOT HELP: it is a SUBSTRING filter over verb names and
purposes. Asked "check whether a test failure is pre-existing" it returns 0 matches --
while `suite-baseline` sits in the list it just searched. That is the same shape as every
other gap found this session: check_boundaries matches duplicate TOKENS and misses forked
MEANINGS; delta() matched node-id SETS and missed attribution; the unread counter matched
KINDS and missed actionability. The substrate is token-strong and meaning-blind, and so am
I -- which is why "the system already knew and never said" happened four times in two days.

THE ONE REQUIREMENT THAT OUTRANKS THE REST: a tool built to stop me fabricating absence
must never fabricate absence itself. "No such capability" and "the model could not tell"
must be different renders, or this becomes a faster way to make my worst mistake.

Run: py -m pytest tests/test_t210_semantic_discover.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import capability_search as CS  # noqa: E402


class FakeOutcome:
    def __init__(self, ok=True, partial=False, why="", answer="", usd=0.001):
        self.ok, self.partial, self.why = ok, partial, why
        self.detail = {"answer": answer, "usd": usd, "model": "fake"}


def test_a_clear_hit_reports_exists_with_its_pointer(monkeypatch):
    monkeypatch.setattr(CS, "_ask", lambda *a, **k: FakeOutcome(
        answer="EXISTS: yes\nWHAT: suite-baseline verb\nGAP: none\nNEAREST MISS: audit"))
    r = CS.find("is this test failure pre-existing")
    assert r["exists"] == "yes"
    assert "suite-baseline" in r["what"]
    assert r["confident"] is True


def test_a_model_failure_is_UNKNOWN_never_no(monkeypatch):
    """THE LOAD-BEARING PIN. This tool exists because I infer absence without checking.
    If a dead key, a timeout, or an empty answer rendered as 'no such capability', it
    would industrialise my worst error instead of fixing it."""
    monkeypatch.setattr(CS, "_ask", lambda *a, **k: FakeOutcome(
        ok=False, why="no DEEPSEEK_API_KEY -- the door is closed"))
    r = CS.find("anything")
    assert r["exists"] == "UNKNOWN"
    assert r["exists"] != "no"
    assert "could not" in r["why"].lower() or "unreadable" in r["why"].lower()


def test_a_partial_answer_is_not_promoted_to_confident(monkeypatch):
    """A truncated answer may have been about to say 'actually it exists'."""
    monkeypatch.setattr(CS, "_ask", lambda *a, **k: FakeOutcome(
        partial=True, why="cut at the ceiling", answer="EXISTS: no\nWHAT:"))
    r = CS.find("anything")
    assert r["confident"] is False


def test_an_unparseable_answer_is_unknown_not_no(monkeypatch):
    """The model wandered off the format. That is a parsing failure, and a parsing
    failure must not become a claim about the world."""
    monkeypatch.setattr(CS, "_ask", lambda *a, **k: FakeOutcome(
        answer="Well, it depends on what you mean by capability..."))
    r = CS.find("anything")
    assert r["exists"] == "UNKNOWN"


def test_a_genuine_no_is_still_reportable(monkeypatch):
    """It must be ABLE to say no -- a tool that can only say yes or unknown is not an
    instrument, it is a cheerleader. The bar is that `no` requires a well-formed answer
    from a healthy call."""
    monkeypatch.setattr(CS, "_ask", lambda *a, **k: FakeOutcome(
        answer="EXISTS: no\nWHAT: nothing in the list\nGAP: n/a\nNEAREST MISS: recall"))
    r = CS.find("time travel")
    assert r["exists"] == "no" and r["confident"] is True


def test_the_answer_is_labelled_as_a_model_read_not_a_lookup(monkeypatch):
    """Provenance. A substring hit is a FACT about the verb table; this is a model's
    reading of it. Rendering them identically would let an inference inherit a lookup's
    authority -- the laundering the 07-30 plane design forbids one level up."""
    monkeypatch.setattr(CS, "_ask", lambda *a, **k: FakeOutcome(
        answer="EXISTS: yes\nWHAT: x\nGAP: y\nNEAREST MISS: z"))
    r = CS.find("q")
    assert r["source"] == "model"
    assert r.get("model")


def test_cost_is_reported(monkeypatch):
    """It spends money. Spending that is invisible gets distrusted or over-used."""
    monkeypatch.setattr(CS, "_ask", lambda *a, **k: FakeOutcome(
        answer="EXISTS: yes\nWHAT: x\nGAP: -\nNEAREST MISS: -", usd=0.0069))
    assert CS.find("q")["usd"] == 0.0069


def test_inputs_are_the_substrate_not_the_model_s_memory(monkeypatch):
    """It must reason from the ATTACHED verb list and module index, never from what a
    model recalls about a repo it was not trained on. Pinned on the prompt itself."""
    seen = {}

    def fake_ask(prompt, files, **k):
        seen["prompt"], seen["files"] = prompt, files
        return FakeOutcome(answer="EXISTS: yes\nWHAT: x\nGAP: -\nNEAREST MISS: -")

    monkeypatch.setattr(CS, "_ask", fake_ask)
    CS.find("q")
    assert any("MODULE_INDEX" in f for f in seen["files"])
    low = seen["prompt"].lower()
    assert "only" in low and ("do not speculate" in low or "not speculate" in low)


def test_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("everything is on fire")
    monkeypatch.setattr(CS, "_ask", boom)
    r = CS.find("q")
    assert r["exists"] == "UNKNOWN"
