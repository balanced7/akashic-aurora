"""
Bifrost B2 -- the durable promoter (salient bus messages -> append-only Ledger).

Bar: salient kinds (handoff/decision/completion/blocker) are projected into the durable firehose and
queryable back via promoted(); ephemeral kinds (chat/note/...) are NOT promoted; the record survives
a fresh reader on the same File ledger (Redis-restart-survivable). Isolated FileLedger -- no Redis.

Run: py -m pytest tests/test_bifrost_promoter.py -q
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.ledger import FileLedger
from core.events.event_log import EventLog
from core.events.event_query import EventQuery
from core.comm.promoter import promote, promoted, is_salient, PROMOTED_KIND


def _log():
    return EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="promo_")))


def test_is_salient():
    for k in ("handoff", "decision", "completion", "blocker"):
        assert is_salient(k)
    for k in ("chat", "note", "announce", "reply", ""):
        assert not is_salient(k)


def test_salient_is_promoted_and_queryable():
    el = _log()
    ok = promote("claude", "cursor", "handoff", {"task": "B2"}, "msg1", "2026-06-28T20:00:00", event_log=el)
    assert ok is True
    out = promoted(event_query=EventQuery(event_log=el))
    assert len(out) == 1
    ev = out[0]
    assert ev["kind"] == PROMOTED_KIND
    assert ev["detail"]["frm"] == "claude" and ev["detail"]["to"] == "cursor"
    assert ev["detail"]["content"] == {"task": "B2"}
    assert "bifrost:msg1" in ev.get("refs", [])


def test_ephemeral_is_not_promoted():
    el = _log()
    assert promote("claude", "cursor", "chat", "hi", "m2", "2026-06-28T20:01:00", event_log=el) is False
    assert promoted(event_query=EventQuery(event_log=el)) == []


def test_only_salient_appears_among_mixed():
    el = _log()
    promote("a", "b", "decision", "use redis streams", "d1", "2026-06-28T20:02:00", event_log=el)
    promote("a", "b", "chat", "lol", "c1", "2026-06-28T20:02:30", event_log=el)
    promote("a", "b", "completion", "B0 shipped", "k1", "2026-06-28T20:03:00", event_log=el)
    kinds = [e["detail"]["kind"] for e in promoted(event_query=EventQuery(event_log=el))]
    assert sorted(kinds) == ["completion", "decision"]


def test_durable_across_a_fresh_reader():
    """The whole point: a promoted record survives -- a brand-new EventLog/EventQuery on the same
    File ledger still finds it (Redis could have restarted)."""
    led = FileLedger(base_dir=tempfile.mkdtemp(prefix="promo_dur_"))
    promote("claude", "cursor", "handoff", "durable?", "m9", "2026-06-28T20:04:00",
            event_log=EventLog(led))
    fresh = EventQuery(event_log=EventLog(led))      # cold reader on the same ledger
    out = promoted(event_query=fresh)
    assert len(out) == 1 and out[0]["detail"]["content"] == "durable?"


if __name__ == "__main__":
    for fn in [test_is_salient, test_salient_is_promoted_and_queryable, test_ephemeral_is_not_promoted,
               test_only_salient_appears_among_mixed, test_durable_across_a_fresh_reader]:
        fn()
    print("ALL B2 PROMOTER TESTS PASSED")
