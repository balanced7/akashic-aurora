"""
Bifrost console capture -- the live cockpit's human-in-the-loop actions -> the durable Ledger.

The console (scripts/bifrost_ui.py) renders interjections, pause/resume, and file drops over ephemeral
SSE. This bar: each of those is ALSO projected into the append-only firehose (same store as bifrost_msg)
and queryable back via console_events(), surviving a fresh reader on the same File ledger. Isolated
FileLedger -- no Redis, no running server.

Run: py -m pytest tests/test_bifrost_console_capture.py -q
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.ledger import FileLedger
from core.events.event_log import EventLog
from core.events.event_query import EventQuery
from core.comm.promoter import (
    promote_interjection, promote_control, promote_drop, console_events,
    INTERJECTION_KIND, CONTROL_KIND, DROP_KIND,
)


def _log():
    return EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="console_")))


def test_interjection_is_captured_and_queryable():
    el = _log()
    verdict = {"intent": "halt", "confidence": 0.92, "why": "stop / redirect signal", "source": "heuristic"}
    assert promote_interjection("wait, that's wrong", verdict, "deepseek",
                                paused=True, by="user", msg_id="m1", event_log=el) is True
    out = console_events(event_query=EventQuery(event_log=el))
    assert len(out) == 1
    ev = out[0]
    assert ev["kind"] == INTERJECTION_KIND
    assert ev["detail"]["intent"] == "halt" and ev["detail"]["to"] == "deepseek"
    assert ev["detail"]["paused"] is True
    assert ev["detail"]["text"] == "wait, that's wrong"
    assert "bifrost:m1" in ev.get("refs", [])


def test_control_pause_and_resume_are_captured():
    el = _log()
    assert promote_control("pause", reason="interjection: redo the auth", by="user", event_log=el) is True
    assert promote_control("resume", by="user", event_log=el) is True
    kinds = [(e["kind"], e["detail"]["action"]) for e in console_events(event_query=EventQuery(event_log=el))]
    assert (CONTROL_KIND, "pause") in kinds
    assert (CONTROL_KIND, "resume") in kinds


def test_file_drop_is_captured_with_provenance():
    el = _log()
    assert promote_drop("dropbox/spec.md", 2048, by="user", event_log=el) is True
    out = console_events(kinds=(DROP_KIND,), event_query=EventQuery(event_log=el))
    assert len(out) == 1
    assert out[0]["kind"] == DROP_KIND
    assert out[0]["detail"]["path"] == "dropbox/spec.md" and out[0]["detail"]["bytes"] == 2048
    assert "file:dropbox/spec.md" in out[0].get("refs", [])


def test_console_events_filters_to_console_kinds_only():
    """console_events() returns ONLY the three console kinds -- unrelated firehose events are excluded."""
    el = _log()
    el.capture("note", "just a note")                         # noise: not a console kind
    el.capture("bifrost_msg", "a promoted handoff")           # noise: the OTHER projection
    promote_interjection("also cover nulls", {"intent": "steer", "why": "additive"}, "claude", event_log=el)
    promote_drop("dropbox/data.csv", 10, event_log=el)
    out = console_events(event_query=EventQuery(event_log=el))
    got = sorted(e["kind"] for e in out)
    assert got == [DROP_KIND, INTERJECTION_KIND]              # note + bifrost_msg excluded


def test_capture_never_raises_on_a_broken_log():
    """The console request path must survive a capture hiccup -> every helper returns False, no raise."""
    class Boom:
        def capture(self, *a, **k):
            raise RuntimeError("ledger down")
    assert promote_interjection("x", {"intent": "ask"}, "claude", event_log=Boom()) is False
    assert promote_control("pause", event_log=Boom()) is False
    assert promote_drop("dropbox/x", 1, event_log=Boom()) is False


def test_durable_across_a_fresh_reader():
    led = FileLedger(base_dir=tempfile.mkdtemp(prefix="console_dur_"))
    promote_control("pause", reason="durable?", by="user", event_log=EventLog(led))
    fresh = EventQuery(event_log=EventLog(led))                # cold reader on the same ledger
    out = console_events(event_query=fresh)
    assert len(out) == 1 and out[0]["detail"]["reason"] == "durable?"


if __name__ == "__main__":
    for fn in [test_interjection_is_captured_and_queryable, test_control_pause_and_resume_are_captured,
               test_file_drop_is_captured_with_provenance, test_console_events_filters_to_console_kinds_only,
               test_capture_never_raises_on_a_broken_log, test_durable_across_a_fresh_reader]:
        fn()
    print("ALL CONSOLE CAPTURE TESTS PASSED")
