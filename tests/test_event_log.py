"""
Auto-logger Slice 1 -- EventLog capture primitive (raw cross-agent event firehose).

Acceptance bar (docs/library/design/20260714_cross-agent-auto-logger-design-slice-pla_6d21c5.md):
  - every captured event round-trips File AND Redis identically;
  - survives Redis-down (File durable, no hang);
  - capture() NEVER raises on bad / huge / None input.

Three layers: shape (capture/recent/count/get) -> robustness (fuzz, corruption,
bad input, cross-backend) -> isolation (never touches canonical db 0 / real AI_SETUP).
"""
import os
import sys
import json
import tempfile

import isolate_canonical            # noqa: F401  (side-effect: isolate + flush db15)

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
sys.path.insert(0, _TESTS)

import pytest

from core.foundation.ledger import FileLedger
from core.events.event_log import (
    EventLog, get_event_log, reset_event_log_singleton,
    per_agent_stream, event_ref, RAW_STREAM,
)
from redis_test_helpers import fresh_test_ledger


def _log() -> EventLog:
    """An isolated EventLog on a throwaway FileLedger (the Redis-down equivalent)."""
    return EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="evlog_")))


# ----------------------------------------------------------------- shape

def test_capture_roundtrip():
    el = _log()
    ev = el.capture("tool_call", "ran pytest", detail={"cmd": "pytest -q"},
                    agent_id="opencode", session_id="abc123", refs=["git:deadbeef"])
    assert ev is not None
    assert ev["kind"] == "tool_call"
    assert ev["summary"] == "ran pytest"
    assert ev["agent_id"] == "opencode"
    assert ev["detail"] == {"cmd": "pytest -q"}
    assert ev["refs"] == ["git:deadbeef"]
    assert ev["id"] and ev["_ref"] == event_ref(RAW_STREAM, ev["id"])
    # readable back off the firehose
    back = el.recent(10)
    assert len(back) == 1 and back[0]["summary"] == "ran pytest"


def test_count_matches_captures():
    el = _log()
    for i in range(7):
        el.capture("note", f"n{i}", agent_id="a")
    assert el.count() == 7


def test_recent_is_newest_first():
    el = _log()
    for i in range(5):
        el.capture("note", f"n{i}", agent_id="a")
    recent = el.recent(3)
    assert [r["summary"] for r in recent] == ["n4", "n3", "n2"]


def test_get_resolves_ref():
    el = _log()
    ev = el.capture("observation", "found a bug", agent_id="claude")
    again = el.get(ev["_ref"])
    assert again is not None and again["summary"] == "found a bug"
    assert again["id"] == ev["id"]


def test_get_bad_ref_returns_none():
    el = _log()
    assert el.get("not-a-ref") is None
    assert el.get("event:events:raw:999999") is None
    assert el.get("") is None


def test_open_vocab_kind_preserved():
    el = _log()
    ev = el.capture("weird_custom_kind", "x", agent_id="a")
    assert ev["kind"] == "weird_custom_kind"   # open vocab: NOT downgraded to 'note'


# ----------------------------------------------------------------- per-agent index

def test_per_agent_stream_filters():
    el = _log()
    el.capture("note", "alice-1", agent_id="alice")
    el.capture("note", "bob-1", agent_id="bob")
    el.capture("note", "alice-2", agent_id="alice")
    assert el.count() == 3                        # firehose has all
    assert el.count(agent="alice") == 2           # per-agent index isolates
    assert el.count(agent="bob") == 1
    assert [e["summary"] for e in el.recent(agent="alice")] == ["alice-2", "alice-1"]


def test_per_agent_stream_name_sanitized():
    assert per_agent_stream("a:b/c") == "events:a_b_c:raw"
    assert per_agent_stream(None) == "events:unknown:raw"


# ----------------------------------------------------------------- robustness

def test_capture_never_raises_on_bad_input():
    el = _log()
    assert el.capture("note", None, agent_id=None) is not None        # None summary -> ""
    assert el.capture(None, "s") is not None                          # None kind -> 'note'
    huge = "x" * 50000
    ev = el.capture("note", huge, detail={"blob": huge})
    assert ev is not None
    assert ev["summary"].endswith("...[clipped]")                     # summary clipped
    assert ev["detail"].get("_truncated") is True                     # detail bounded


def test_capture_handles_unserializable_detail():
    el = _log()
    ev = el.capture("note", "weird", detail={"obj": object()})
    assert ev is not None                                             # default=str saves it
    # round-trips as JSON (the stored event must be serializable)
    json.dumps(el.recent(1)[0], default=str)


def test_missing_kind_defaults_to_note():
    el = _log()
    assert el.capture("", "s")["kind"] == "note"


def test_fuzz_order_and_invariants():
    el = _log()
    n = 400
    for i in range(n):
        el.capture("tool_call" if i % 2 else "note", f"event {i}", agent_id=f"ag{i % 3}")
    assert el.count() == n
    allev = list(reversed(el.recent(n)))          # oldest-first
    # every event has the mandatory fields + a followable ref
    assert all(e.get("at") and e.get("kind") and e.get("_ref") for e in allev)
    # ledger ids are monotonic -> time/order is preserved
    ids = [int(e["id"]) for e in allev]
    assert ids == sorted(ids)


def test_corrupt_line_skipped_on_read():
    base = tempfile.mkdtemp(prefix="evlog_corrupt_")
    el = EventLog(FileLedger(base_dir=base))
    el.capture("note", "good", agent_id="a")
    # inject a corrupt JSONL line into the canonical stream file
    safe = RAW_STREAM.replace(":", "_")
    path = os.path.join(base, f"{safe}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write("this is not json\n")
    el.capture("note", "good2", agent_id="a")
    summaries = [e["summary"] for e in el.recent(10)]
    assert "good" in summaries and "good2" in summaries     # corrupt line skipped, not fatal


# ----------------------------------------------------------------- cross-backend

@pytest.mark.skipif(fresh_test_ledger() is None, reason="Redis down -> File-only is enough")
def test_cross_backend_equivalence():
    """File and Redis ledgers capture the same events in the same order."""
    fl = EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="evlog_x_")))
    rl = EventLog(fresh_test_ledger())
    payload = [("tool_call", "compile"), ("file_edit", "edit x.py"),
               ("command", "run tests"), ("note", "done")]
    for kind, summ in payload:
        fl.capture(kind, summ, agent_id="x")
        rl.capture(kind, summ, agent_id="x")
    f_view = [(e["kind"], e["summary"]) for e in reversed(fl.recent(50))]
    r_view = [(e["kind"], e["summary"]) for e in reversed(rl.recent(50))]
    assert f_view == r_view == payload


# ----------------------------------------------------------------- isolation

def test_isolated_singleton_not_cached():
    """Under test isolation, get_event_log() must hand back fresh instances so a
    subprocess CLI test can never pollute the canonical firehose."""
    reset_event_log_singleton()
    a = get_event_log()
    b = get_event_log()
    assert a is not b                              # no shared singleton while isolated
    assert os.environ.get("_AISETUP_TEST_ISOLATED") == "1"
