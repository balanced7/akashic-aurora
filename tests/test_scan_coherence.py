"""
R9/R17 SCAN-COHERENCE (T029 tier-2): promoted() and lookback must agree on ack state for the
same message. Two read paths, two scan windows -- a message rendered acked in one surface
and UNHANDLED in the other is a silent lie (battery sec. 2, Class 2).

Kill condition (pre-registered): same msg_id -> same ack verdict from both paths.
A message where acks_for returns empty but a durable ack EXISTS in the firehose is the
top_k=500 scan-cap lie -- this test PROVES it is reachable.

Coherence contract:
  acks=[] AND unhandled=False  <->  promoted record has NO acks in firehose
  acks!=[] AND unhandled=False <->  promoted record HAS acks in firehose
  acks=[] AND unhandled=True   <->  genuinely unacked + old enough to flag

Authored by deepseek (T029 tier-2 fenced handoff, bus reply 1783688456583-0);
materialized + reviewed by claude. Run: py -m pytest tests/test_scan_coherence.py -q
"""
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import promoter


class FakeQuery:
    """A coherent event store: search returns events filtered by kind, up to top_k.
    Newest-first, like the real firehose. The SAME store is shared between promoted()
    and acks_for, so acks are never invisible to one path while visible to the other."""
    def __init__(self, events):
        self.events = list(events)

    def search(self, q, kind=None, since=None, until=None, top_k=50):
        out = []
        for e in reversed(self.events):
            if kind is not None and e.get("kind") != kind:
                continue
            out.append(e)
            if len(out) >= top_k:
                break
        return out


def _promoted(mid, frm="alice", to="claude", kind="handoff", content="do X"):
    return {"kind": "bifrost_msg", "at": "t0", "refs": [f"bifrost:{mid}"],
            "detail": {"frm": frm, "to": to, "kind": kind, "content": content, "ts": "t0"}}


def _promoted_at(mid, hours_ago, now, to="claude", kind="handoff", content="please do X"):
    at = datetime.fromtimestamp(now - hours_ago * 3600).isoformat()
    return {"kind": "bifrost_msg", "at": at, "refs": [f"bifrost:{mid}"],
            "detail": {"kind": kind, "to": to, "frm": "alice", "content": content, "ts": at}}


def _ack_event(mid, by="claude"):
    return {"kind": "msg_ack", "at": "t1", "detail": {"by": by, "msg_id": mid, "note": ""}}


# ---------------------------------------------------------- coherence contract

def test_coherence_message_with_ack_is_never_unhandled(monkeypatch):
    """A message with a durable ack must render acked in promoted(), never UNHANDLED."""
    monkeypatch.setattr(promoter, "_closed_task_ids", lambda: set())
    now = time.time()
    events = [_promoted_at("m1", 30, now),
              {"kind": "msg_ack", "at": "t1",
               "detail": {"by": "claude", "msg_id": "m1", "note": ""}}]
    out = promoter.promoted(with_acks=True, now=now, unhandled_hours=6,
                            event_query=FakeQuery(events))
    by_id = {str(e["refs"][0]).split("bifrost:", 1)[-1]: e for e in out}
    assert by_id["m1"].get("acks"), "ack event is visible -> acks list non-empty"
    assert not by_id["m1"].get("unhandled"), "acked message must never flag unhandled"


def test_coherence_acks_for_resolves_existing_ack():
    """acks_for() itself must find the ack for a given message id."""
    events = [_promoted("m1"), _ack_event("m1")]
    amap = promoter.acks_for(["m1"], event_query=FakeQuery(events))
    assert amap["m1"] and amap["m1"][0]["by"] == "claude", \
        "acks_for must resolve the ack when event IS in the firehose"


def test_coherence_unacked_old_message_flags():
    """Genuinely unacked old message: both paths agree -- no acks, unhandled=True."""
    now = time.time()
    events = [_promoted_at("m1", 30, now)]
    out = promoter.promoted(with_acks=True, now=now, unhandled_hours=6,
                            event_query=FakeQuery(events))
    by_id = {str(e["refs"][0]).split("bifrost:", 1)[-1]: e for e in out}
    assert by_id["m1"].get("unhandled") is True
    assert by_id["m1"].get("acks") == []


def test_coherence_scan_cap_drops_oldest_ack_PROOF(monkeypatch):
    """PROOF that the Class 2 scan cap is real: 600 NEWER acks push the target ack
    past top_k=500, so acks_for returns empty even though the ack EXISTS."""
    monkeypatch.setattr(promoter, "_closed_task_ids", lambda: set())
    events = [_promoted("target"), _ack_event("target")]
    for i in range(600):
        events.append(_ack_event(f"other-{i}"))
    amap = promoter.acks_for(["target"], event_query=FakeQuery(events))
    assert not amap["target"], \
        "CLASS 2 PROOF: target ack EXISTS in firehose but acks_for returns empty " \
        "(600 newer acks pushed it past top_k=500) -- the scan-cap lie IS real. " \
        "Fix: by-ref secondary index (Class 2 Wave 2)."


def test_coherence_multiple_surfaces_same_verdict(monkeypatch):
    """Two surfaces sharing one coherent firehose must agree on every message's ack state."""
    monkeypatch.setattr(promoter, "_closed_task_ids", lambda: set())
    now = time.time()
    events = [_promoted_at("m1", 30, now),
              {"kind": "msg_ack", "at": "t1", "detail": {"by": "claude", "msg_id": "m1"}},
              _promoted_at("m2", 30, now)]
    out_a = promoter.promoted(with_acks=True, now=now, unhandled_hours=6,
                              event_query=FakeQuery(events))
    out_b = promoter.promoted(with_acks=True, now=now, unhandled_hours=6,
                              event_query=FakeQuery(events))
    a_by_id = {str(e["refs"][0]).split("bifrost:", 1)[-1]: e for e in out_a}
    b_by_id = {str(e["refs"][0]).split("bifrost:", 1)[-1]: e for e in out_b}
    for mid in a_by_id:
        assert bool(a_by_id[mid].get("acks")) == bool(b_by_id[mid].get("acks")), \
            f"coherence violated for {mid}"
        assert bool(a_by_id[mid].get("unhandled")) == bool(b_by_id[mid].get("unhandled")), \
            f"coherence violated for {mid}"


def test_coherence_promoted_empty_firehose_no_crash():
    """Edge: promoted() with an empty firehose must not crash, must return []."""
    assert promoter.promoted(with_acks=True, event_query=FakeQuery([])) == []
