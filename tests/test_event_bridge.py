"""
Auto-logger Slice 4 -- timeline bridge + ACI verbs.

Acceptance bar (docs/library/design/20260714_cross-agent-auto-logger-design-slice-pla_6d21c5.md):
  - from a Beat/Chapter, the raw events under it are reachable in <= 1 drill;
  - `events` verb: search / around / get / capture work and return within budget;
  - errors teach on empty / bad input; ASCII-safe output.

Bridge units use explicit injection (store + EventQuery); CLI tests drive the real
agent_cli verbs on the isolated default backend.
"""
import os
import sys
import json
import uuid
import tempfile

import isolate_canonical            # noqa: F401

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
sys.path.insert(0, _TESTS)

from core.foundation.store import FileStore
from core.foundation.ledger import FileLedger
from core.events.event_log import EventLog, get_event_log
from core.events.event_query import EventQuery
from core.narrative.beat_log import BeatLog
from core.narrative.schema import Beat, Chapter, beat_key, chapter_key
from core.narrative.event_bridge import parse_window, resolve_span, events_around, raw_for_beat
import agent_cli


class FakeArgs:
    """argparse stand-in: any unset attribute reads as None (cmd_* read defensively)."""
    def __init__(self, **kw):
        self.__dict__.update(kw)
    def __getattr__(self, _name):
        return None


def _ctx():
    store = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    eq = EventQuery(EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="brg_"))))
    return store, eq


# ----------------------------------------------------------------- parse_window

def test_parse_window():
    assert parse_window("30m") == 1800
    assert parse_window("2h") == 7200
    assert parse_window("1d") == 86400
    assert parse_window("45s") == 45
    assert parse_window("900") == 900
    assert parse_window(None) == 1800
    assert parse_window("junk") == 1800      # bad spec -> default, never crash


# ----------------------------------------------------------------- resolve_span

def test_resolve_span_chapter():
    store, _ = _ctx()
    ch = Chapter(id="c1", track="ai-setup", title="t",
                 span_start="2026-06-22T09:00:00", span_end="2026-06-22T15:00:00")
    store.set(chapter_key("c1"), json.dumps(ch.to_dict()))
    assert resolve_span("c1", store=store) == ("2026-06-22T09:00:00", "2026-06-22T15:00:00")


def test_resolve_span_beat_window():
    store, _ = _ctx()
    b = Beat(id="b1", at="2026-06-22T12:00:00", kind="note", summary="x", source="s")
    store.set(beat_key("b1"), json.dumps(b.to_dict()))
    start, end = resolve_span("b1", store=store, window_seconds=3600)
    assert start == "2026-06-22T11:00:00" and end == "2026-06-22T13:00:00"


def test_resolve_span_iso_and_garbage():
    store, _ = _ctx()
    start, end = resolve_span("2026-06-22T12:00:00", store=store, window_seconds=60)
    assert start == "2026-06-22T11:59:00" and end == "2026-06-22T12:01:00"
    assert resolve_span("not-a-thing", store=store) is None


# ----------------------------------------------------------------- events_around

def test_events_around_chapter_returns_in_span_only():
    store, eq = _ctx()
    ch = Chapter(id="c1", track="ai-setup", title="t",
                 span_start="2026-06-22T09:00:00", span_end="2026-06-22T15:00:00")
    store.set(chapter_key("c1"), json.dumps(ch.to_dict()))
    eq.log.capture("tool_call", "inside-A", at="2026-06-22T10:00:00")
    eq.log.capture("command", "inside-B", at="2026-06-22T12:00:00")
    eq.log.capture("note", "outside", at="2026-06-22T20:00:00")
    res = events_around("c1", store=store, event_query=eq)
    got = {e["summary"] for e in res["events"]}
    assert got == {"inside-A", "inside-B"}


def test_events_around_beat_one_drill():
    """The navigation bar: from a Beat, its underlying raw event is reachable in 1 drill."""
    store, eq = _ctx()
    eq.log.capture("tool_call", "the-real-thing", at="2026-06-22T12:05:00")
    b = Beat(id="b1", at="2026-06-22T12:00:00", kind="note", summary="did the thing", source="s")
    store.set(beat_key("b1"), json.dumps(b.to_dict()))
    res = events_around("b1", store=store, event_query=eq, window_seconds=1800)
    assert any(e["summary"] == "the-real-thing" for e in res["events"])


def test_events_around_filter_by_kind():
    store, eq = _ctx()
    ch = Chapter(id="c1", track="x", title="t",
                 span_start="2026-06-22T09:00:00", span_end="2026-06-22T15:00:00")
    store.set(chapter_key("c1"), json.dumps(ch.to_dict()))
    eq.log.capture("command", "a-command", at="2026-06-22T10:00:00")
    eq.log.capture("note", "a-note", at="2026-06-22T11:00:00")
    res = events_around("c1", store=store, event_query=eq, kind="command")
    assert [e["summary"] for e in res["events"]] == ["a-command"]


def test_events_around_unresolvable():
    store, eq = _ctx()
    res = events_around("nope", store=store, event_query=eq)
    assert res["span"] is None and res["events"] == []


# ----------------------------------------------------------------- raw_for_beat

def test_raw_for_beat_resolves_atom():
    store, eq = _ctx()
    ev = eq.log.capture("file_edit", "edited the file", at="2026-06-22T12:00:00")
    b = Beat(id="b1", at="2026-06-22T12:00:00", kind="commit", summary="commit it",
             source=ev.ref)               # the Beat points AT the raw atom
    store.set(beat_key("b1"), json.dumps(b.to_dict()))
    res = raw_for_beat("b1", store=store, event_query=eq)
    assert res["atom"] is not None and res["atom"]["summary"] == "edited the file"
    assert any(e["summary"] == "edited the file" for e in res["events"])


# ----------------------------------------------------------------- CLI verbs

def test_cli_capture_then_search(capsys):
    marker = "CLIMARK_" + uuid.uuid4().hex[:8]
    rc = agent_cli.cmd_events(FakeArgs(capture=True, kind="tool_call", summary=marker,
                                       detail_json='{"x": 1}', refs="git:abc"))
    assert rc == 0
    capsys.readouterr()
    rc = agent_cli.cmd_events(FakeArgs(search=marker, limit=5))
    assert rc == 0
    out = capsys.readouterr().out
    assert marker in out
    assert "event:events:raw:" in out          # drill pointer rendered


def test_cli_get_resolves(capsys):
    marker = "GETMARK_" + uuid.uuid4().hex[:8]
    agent_cli.cmd_events(FakeArgs(capture=True, kind="note", summary=marker))
    capsys.readouterr()
    # find its ref via search, then --get it
    agent_cli.cmd_events(FakeArgs(search=marker, limit=1))
    out = capsys.readouterr().out
    ref = next(tok for tok in out.split() if tok.startswith("event:events:raw:"))
    rc = agent_cli.cmd_events(FakeArgs(get=ref))
    assert rc == 0
    assert marker in capsys.readouterr().out


def test_cli_errors_teach():
    assert agent_cli.cmd_events(FakeArgs(get="nope")) == 2
    assert agent_cli.cmd_events(FakeArgs(around="not-a-beat-or-time")) == 2
    assert agent_cli.cmd_events(FakeArgs(capture=True, kind="note", summary="x",
                                         detail_json="{bad json")) == 2


def test_cli_story_beat_raw(capsys):
    from core.foundation.store import create_store
    store = create_store()
    t = "2026-06-15T12:00:00"
    ev = get_event_log().capture("tool_call", "RAWDRILL_" + uuid.uuid4().hex[:6], at=t)
    beat = BeatLog(store).emit("note", "a beat with raw beneath it", source=ev.ref, at=t)
    rc = agent_cli.cmd_story(FakeArgs(beat=beat.id, raw=True), store=store)
    assert rc == 0
    out = capsys.readouterr().out
    assert ev.detail["summary"] in out        # drilled from the beat into the raw record
