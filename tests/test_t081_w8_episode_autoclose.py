"""T081-W8 pins: SessionEnd auto-closes the open episode so it never dangles across sessions.

The 189h 'Untitled episode' bug: sessions came and went while one episode stayed open. Fix
(prior art: OpenTelemetry spans auto-close when their context exits -- an episode's context is the
session): at SessionEnd, close a content-bearing episode with a draft, or clear an EMPTY one
without minting a phantom 'Untitled' chapter, and never open a fresh one (open_next=False).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from core.narrative.chapter_lifecycle import load_chapter_from_store
from core.narrative import episode as ep


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _emit(store, kind, summary, at):
    return BeatLog(store).emit(kind, summary, f"src:{summary}", at=at, themes=[])


def test_empty_episode_cleared_no_phantom_chapter():
    s = _store()
    ep.open_episode(s, now="2026-07-16T10:00:00")           # opened, no content beats
    res = ep.close_open_episode_for_session_end(s, now="2026-07-16T10:05:00")
    assert res["action"] == "cleared_empty"
    assert s.get(ep.EPISODE_OPEN_KEY) is None               # pointer cleared
    cur = ep.current_episode(s, now="2026-07-16T10:06:00", auto_open=False)["current_chapter"]
    assert cur is None                                      # no dangling / no phantom Untitled


def test_content_episode_closed_and_drafted():
    s = _store()
    ep.open_episode(s, now="2026-07-16T10:00:00")
    _emit(s, "note", "shipped the honest heal", "2026-07-16T10:01:00")
    _emit(s, "decision", "adopted the 3-way classification", "2026-07-16T10:02:00")
    res = ep.close_open_episode_for_session_end(s, now="2026-07-16T10:05:00")
    assert res["action"] == "closed"
    assert res["title"] and res["title"] != "Untitled episode"
    assert s.get(ep.EPISODE_OPEN_KEY) is None               # open_next=False -> nothing dangling
    ch = load_chapter_from_store(s, res["chapter_id"])
    assert ch.span_end is not None                          # span stamped closed


def test_no_open_episode_is_noop():
    res = ep.close_open_episode_for_session_end(_store(), now="2026-07-16T10:00:00")
    assert res["action"] == "none"


def test_dangling_pointer_is_cleared():
    s = _store()
    s.set(ep.EPISODE_OPEN_KEY, json.dumps(
        {"chapter_id": "ch_missing", "start": "2026-07-16T10:00:00", "track": "ai-setup"}))
    res = ep.close_open_episode_for_session_end(s, now="2026-07-16T10:05:00")
    assert res["action"] == "cleared_dangling"
    assert s.get(ep.EPISODE_OPEN_KEY) is None


def test_session_end_close_never_opens_a_fresh_episode():
    s = _store()
    ep.open_episode(s, now="2026-07-16T10:00:00")
    _emit(s, "note", "did work", "2026-07-16T10:01:00")
    ep.close_open_episode_for_session_end(s, now="2026-07-16T10:05:00")
    assert s.get(ep.EPISODE_OPEN_KEY) is None               # the P3/whisper-noise fix: no new open span
