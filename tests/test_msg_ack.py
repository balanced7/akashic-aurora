"""
P6 / T026 -- message ack lifecycle: read != handled != acknowledged.

Bar: ack() writes a durable msg_ack referencing the bus id; acks_for maps them back;
promoted(with_acks=True, now=...) annotates acked messages and flags salient-unacked past
the threshold as UNHANDLED; the runner auto-acks only handoffs it ACTUALLY answered
(errors do not ack). Four live incidents on 2026-07-09 shared the read-vs-handled gap.

Run: py -m pytest tests/test_msg_ack.py -q
"""
import os
import sys
import time
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from core.comm import promoter


class FakeLog:
    def __init__(self):
        self.captured = []

    def capture(self, kind, summary, **kw):
        self.captured.append({"kind": kind, "summary": summary, **kw})


class FakeQuery:
    def __init__(self, events):
        self.events = events

    def search(self, q, kind=None, since=None, until=None, top_k=50):
        return [e for e in self.events if e.get("kind") == kind][:top_k]


def test_ack_writes_durable_ref():
    log = FakeLog()
    assert promoter.ack("claude", "1783600000000-0", note="reviewed + merged", event_log=log)
    e = log.captured[0]
    assert e["kind"] == "msg_ack"
    assert e["refs"] == ["bifrost:1783600000000-0"]
    assert e["detail"]["by"] == "claude" and "reviewed" in e["detail"]["note"]


def test_acks_for_maps_ids_and_allows_multiple_actors():
    events = [
        {"kind": "msg_ack", "at": "t1", "detail": {"by": "deepseek", "msg_id": "111-0", "note": ""}},
        {"kind": "msg_ack", "at": "t2", "detail": {"by": "claude", "msg_id": "111-0", "note": "also"}},
        {"kind": "msg_ack", "at": "t3", "detail": {"by": "claude", "msg_id": "222-0", "note": ""}},
        {"kind": "other", "at": "t4", "detail": {"msg_id": "111-0"}},
    ]
    m = promoter.acks_for(["111-0", "999-0"], event_query=FakeQuery(events))
    assert [a["by"] for a in m["111-0"]] == ["deepseek", "claude"], "multiple acks per msg legal"
    assert m["999-0"] == []


def _promoted_event(mid, hours_ago, now, kind="handoff", to="claude", content="please do X"):
    at = datetime.fromtimestamp(now - hours_ago * 3600).isoformat()
    return {"kind": "bifrost_msg", "at": at, "refs": [f"bifrost:{mid}"],
            "summary": f"{kind} {mid}",
            "detail": {"kind": kind, "to": to, "frm": "alice", "content": content}}


def test_promoted_flags_old_unacked_asks_and_annotates_acked():
    now = time.time()
    events = [_promoted_event("old-1", 30, now), _promoted_event("new-1", 1, now),
              _promoted_event("done-1", 30, now),
              {"kind": "msg_ack", "at": "t", "detail": {"by": "deepseek", "msg_id": "done-1", "note": ""}}]
    out = promoter.promoted(with_acks=True, now=now, unhandled_hours=6,
                            event_query=FakeQuery(events))
    by_id = {str(e["refs"][0]).split("bifrost:", 1)[-1]: e for e in out}
    assert by_id["old-1"].get("unhandled") is True, "30h unacked ask -> UNHANDLED"
    assert by_id["new-1"].get("unhandled") is False, "1h old -> not yet"
    assert by_id["done-1"].get("acks") and not by_id["done-1"].get("unhandled"), "acked -> never flagged"


def test_flag_scoping_directed_window_and_fire_and_forget_kinds():
    """Red-team rules: decision/completion never flag; directed asks flag at 2h while
    broadcasts get 6h."""
    now = time.time()
    events = [_promoted_event("d-3h", 3, now, to="deepseek"),          # directed, 3h > 2h
              _promoted_event("b-3h", 3, now, to="*"),                 # broadcast, 3h < 6h
              _promoted_event("c-30h", 30, now, kind="completion"),
              _promoted_event("dec-30h", 30, now, kind="decision")]
    out = promoter.promoted(with_acks=True, now=now, unhandled_hours=6,
                            event_query=FakeQuery(events))
    by_id = {str(e["refs"][0]).split("bifrost:", 1)[-1]: e for e in out}
    assert by_id["d-3h"].get("unhandled") is True, "directed past 2h flags"
    assert by_id["b-3h"].get("unhandled") is False, "broadcast under 6h does not"
    assert not by_id["c-30h"].get("unhandled") and not by_id["dec-30h"].get("unhandled"), \
        "fire-and-forget kinds never flag"


def test_closed_ledger_task_suppresses_the_flag(monkeypatch):
    now = time.time()
    monkeypatch.setattr(promoter, "_closed_task_ids", lambda: {"T016"})
    events = [_promoted_event("t016-ask", 30, now, content="[T016 fenced investigation request]"),
              _promoted_event("t099-ask", 30, now, content="please review T099 today")]
    out = promoter.promoted(with_acks=True, now=now, unhandled_hours=6,
                            event_query=FakeQuery(events))
    by_id = {str(e["refs"][0]).split("bifrost:", 1)[-1]: e for e in out}
    assert by_id["t016-ask"].get("handled_via", "").startswith("ledger"), \
        "ask about a closed task is implicitly handled"
    assert not by_id["t016-ask"].get("unhandled")
    assert by_id["t099-ask"].get("unhandled") is True


def test_ack_is_idempotent_per_actor():
    log = FakeLog()
    existing = [{"kind": "msg_ack", "at": "t", "detail": {"by": "deepseek", "msg_id": "111-0", "note": ""}}]
    assert promoter.ack("deepseek", "111-0", event_log=log, event_query=FakeQuery(existing))
    assert log.captured == [], "same actor twice = no-op (re-wake double-answer guard)"
    assert promoter.ack("claude", "111-0", event_log=log, event_query=FakeQuery(existing))
    assert len(log.captured) == 1, "a DIFFERENT actor still records (forensics)"


def test_runner_auto_acks_answered_handoff_only(monkeypatch):
    import scripts.bifrost_runner_deepseek as runner
    acked = []
    monkeypatch.setattr(promoter, "ack", lambda by, mid, note="", **kw: acked.append((by, mid)) or True)
    bus = SimpleNamespace(send=lambda *a, **k: None, broadcast=lambda *a, **k: None)
    args = SimpleNamespace(agent="deepseek", agentic=False, model="m")
    rate = SimpleNamespace(allow=lambda: True)
    msg = SimpleNamespace(kind="handoff", frm="claude", to="deepseek", id="777-0",
                          content="do the thing", meta={})
    runner._process_one(msg, bus, args, lambda prompt: "done: the thing", rate)
    assert acked == [("deepseek", "777-0")], "real answer -> auto-ack"
    acked.clear()
    boom = lambda prompt: (_ for _ in ()).throw(RuntimeError("api down"))
    msg2 = SimpleNamespace(kind="handoff", frm="claude", to="deepseek", id="888-0",
                           content="do the thing", meta={})
    runner._process_one(msg2, bus, args, boom, rate)
    assert acked == [], "error reply must NOT ack -- sender must still see UNHANDLED"
    err_string = lambda prompt: "(deepseek agentic runner error: RuntimeError: api down)"
    msg3 = SimpleNamespace(kind="handoff", frm="claude", to="deepseek", id="999-0",
                           content="do the thing", meta={})
    runner._process_one(msg3, bus, args, err_string, rate)
    assert acked == [], "error-STRING replies must not ack either (respond swallows exceptions)"
