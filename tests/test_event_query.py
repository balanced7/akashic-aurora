"""
Auto-logger Slice 3 -- query + search over the raw firehose.

Acceptance bar (docs/library/design/20260714_cross-agent-auto-logger-design-slice-pla_6d21c5.md):
  - window recall = 100%  (every event in a span is returned);
  - search precision@5 >= 0.8 vs gold on the QA queries;
  - filters (kind / agent / track / since / until) are exact;
  - empty store / bad input -> empty result, never a crash.

Metric gates run on tests/fixtures/events_fixture.py (the local benchmark).
"""
import os
import sys
import tempfile

import isolate_canonical            # noqa: F401

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
sys.path.insert(0, _TESTS)
sys.path.insert(0, os.path.join(_TESTS, "fixtures"))

from core.foundation.ledger import FileLedger
from core.events.event_log import EventLog
from core.events.event_query import EventQuery
from events_fixture import build_events_fixture


def _fixture():
    el = EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="evq_")))
    gold = build_events_fixture(el)
    return EventQuery(el), gold


def _precision_at_k(returned, relevant, k):
    top = returned[:k]
    if not top:
        return 0.0
    hits = sum(1 for e in top if e.get("summary") in relevant)
    return hits / len(top)


# ----------------------------------------------------------------- metric gates

def test_window_recall_is_100pct():
    eq, gold = _fixture()
    w = gold["window"]
    got = {e["summary"] for e in eq.events_in_window(w["start"], w["end"])}
    expected = w["expected"]
    missing = expected - got
    assert not missing, f"window recall < 100%: missing {missing}"
    assert got == expected, f"window returned extras: {got - expected}"


def test_search_precision_at_5():
    eq, gold = _fixture()
    scores = []
    for qa in gold["queries"]:
        returned = eq.search(qa["q"], top_k=qa["k"])
        p = _precision_at_k(returned, qa["relevant"], qa["k"])
        scores.append(p)
        assert p >= 0.8, f"query {qa['q']!r}: precision@{qa['k']}={p:.2f} < 0.80"
    assert sum(scores) / len(scores) >= 0.8


def test_search_ranks_relevant_first():
    eq, gold = _fixture()
    qa = gold["queries"][0]                       # stemroller vocab
    top = eq.search(qa["q"], top_k=3)
    assert all(e["summary"] in qa["relevant"] for e in top)


# ----------------------------------------------------------------- filters (exact)

def test_filter_by_kind():
    eq, gold = _fixture()
    got = eq.search("", kind="learning", top_k=100)
    assert len(got) == gold["by_kind"]["learning"]
    assert all(e["kind"] == "learning" for e in got)


def test_filter_by_track():
    eq, gold = _fixture()
    got = eq.search("", track="research", top_k=100)
    assert len(got) == gold["by_track"]["research"]
    assert all(e["track"] == "research" for e in got)


def test_filter_by_agent():
    eq, gold = _fixture()
    got = eq.search("", agent="opencode", top_k=100)
    assert len(got) == gold["by_agent"]["opencode"]
    assert all(e["agent_id"] == "opencode" for e in got)


def test_search_time_bounds():
    eq, _ = _fixture()
    # only Day 3 (stemroller) events fall in this since/until band
    got = eq.search("", since="2026-06-22T00:00:00", until="2026-06-22T23:59:59", top_k=100)
    assert got and all(e["track"] == "stemroller" for e in got)


def test_window_with_kind_filter():
    eq, _ = _fixture()
    got = eq.events_in_window("2026-06-22T00:00:00", "2026-06-22T23:59:59", kind="command")
    assert len(got) == 1 and got[0]["kind"] == "command"


# ----------------------------------------------------------------- robustness

def test_get_resolves_ref_from_query():
    eq, _ = _fixture()
    hit = eq.search("demucs vocals", top_k=1)[0]
    again = eq.get(hit["_ref"])
    assert again is not None and again["summary"] == hit["summary"]


def test_empty_store_returns_empty():
    eq = EventQuery(EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="evq_empty_"))))
    assert eq.search("anything") == []
    assert eq.events_in_window("2026-01-01T00:00:00", "2026-12-31T00:00:00") == []
    assert eq.get("event:events:raw:1") is None


def test_bad_input_never_crashes():
    eq, _ = _fixture()
    assert isinstance(eq.events_in_window("garbage", "also-garbage"), list)
    assert isinstance(eq.search(None), list)            # None query -> falls back, no crash
    assert eq.get("not-a-ref") is None


def test_reversed_window_bounds_tolerated():
    eq, gold = _fixture()
    w = gold["window"]
    got = {e["summary"] for e in eq.events_in_window(w["end"], w["start"])}   # swapped
    assert got == w["expected"]
