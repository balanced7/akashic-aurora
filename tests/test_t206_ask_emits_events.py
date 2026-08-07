"""
T206 -- a finished background ask leaves a durable trace. RED first.

Daniil 2026-08-07: "you can also trigger events through systems and have observers, or you
observe -- there is so much potential here."

THE SMALLEST HONEST VERSION OF THAT, and the reason it is the right first step. A
background ask is currently PULL: the caller must remember to `--get`. This repo has 1,324
unopened mailbox items, which is what "remember to check later" produces at scale. The
obvious fix -- send mail on completion -- adds a wake surface, a cursor, and one more thing
that accumulates unread. We measured all three failing today.

An EVENT adds none of that. capture_event already exists, the firehose is durable and
append-only, every reader can query it, and crucially an event does NOT demand attention.
That is the correct default for something that may fire dozens of times an hour. Waking
someone stays OPT-IN, because a notification that fires constantly is how you teach a
reader to ignore notifications -- the same disarming pathology as W131's gate.

THE UNPLANNED PAYOFF: Sol's collaboration-friction list named four metrics, and three
(commands per task, operator interventions, recovery time) were unbuildable because NO
DURABLE ANCHOR EXISTED for delegation. This event is that anchor. Every background ask now
leaves cost, outcome, duration, truncation class and whether it was grounded -- which is
"how much did I delegate, what did it cost, and did it work", recorded as it happens
rather than reconstructed later.

Run: py -m pytest tests/test_t206_ask_emits_events.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import ask_bg  # noqa: E402


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ask_bg, "ASK_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def captured(monkeypatch):
    seen = []
    monkeypatch.setattr("core.events.event_log.capture_event",
                        lambda kind, msg, **kw: seen.append((kind, msg, kw)))
    return seen


def test_a_finished_ask_emits_one_event(store, captured):
    ask_bg.write_record("h1", {"status": "running", "prompt": "why is X"})
    ask_bg.finish("h1", {"ok": True, "answer": "because", "usd": 0.0031,
                         "elapsed_s": 12.5, "model": "deepseek-v4-pro"})
    assert len(captured) == 1
    kind, _, kw = captured[0]
    assert kind == "ask_completed"
    assert "h1" in [str(r) for r in (kw.get("refs") or [])]


def test_the_event_carries_what_a_metric_would_need(store, captured):
    """cost, duration, model, outcome -- the anchor Sol's unmeasured metrics lacked. A
    field absent here cannot be reconstructed later: the record is deleted, and the
    conversation that produced it is gone."""
    ask_bg.write_record("h2", {"status": "running", "prompt": "q", "with": ["a.py"]})
    ask_bg.finish("h2", {"ok": True, "answer": "a", "usd": 0.002, "elapsed_s": 9.0,
                         "model": "m", "prompt_tokens": 100, "completion_tokens": 50})
    d = captured[0][2]["detail"]
    for field in ("usd", "elapsed_s", "model", "outcome", "grounded",
                  "prompt_tokens", "completion_tokens"):
        assert field in d, f"missing {field}"
    assert d["grounded"] is True, "an ask carrying files is GROUNDED -- the T203 lever"
    assert d["outcome"] == "done"


def test_failure_and_partial_are_distinct_outcomes(store, captured):
    ask_bg.write_record("f1", {"status": "running"})
    ask_bg.finish("f1", {"ok": False, "why": "STARVED", "truncation": "STARVED"})
    ask_bg.write_record("p1", {"status": "running"})
    ask_bg.finish("p1", {"ok": True, "partial": True, "why": "cut",
                         "truncation": "CUT"})
    outcomes = [c[2]["detail"]["outcome"] for c in captured]
    assert outcomes == ["failed", "partial"]
    assert captured[0][2]["detail"]["truncation"] == "STARVED"


def test_the_answer_body_never_rides_the_event(store, captured):
    """The firehose is a durable index, not a document store. A 30k-token answer on every
    event would bloat the one surface boot and friction read -- the body already lives in
    the record, and the event points at it."""
    ask_bg.write_record("h3", {"status": "running"})
    ask_bg.finish("h3", {"ok": True, "answer": "SECRET-BODY " * 500})
    blob = str(captured[0])
    assert "SECRET-BODY" not in blob
    assert "h3" in blob, "but the handle must be there, so the body is one hop away"


def test_emission_failure_never_costs_the_result(store, monkeypatch):
    """Observability must never be able to destroy the thing it observes. If the firehose
    is down, the answer still lands."""
    def boom(*a, **k):
        raise RuntimeError("event log down")
    monkeypatch.setattr("core.events.event_log.capture_event", boom)
    ask_bg.write_record("h4", {"status": "running"})
    ask_bg.finish("h4", {"ok": True, "answer": "survives"})
    assert ask_bg.read_record("h4")["result"]["answer"] == "survives"


def test_no_event_without_a_finish(store, captured):
    """Arming is not completing. An event per spawn would double-count every delegation
    in any metric built on this anchor."""
    ask_bg.write_record("h5", {"status": "running"})
    assert not captured
