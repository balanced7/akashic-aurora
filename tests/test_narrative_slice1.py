"""
Slice 1 completion -- session kinds, auto-capture lifecycle, and mark_chapter.

These guard the three things finished in Slice 1's tail:
  - `session` is a real Beat kind (was silently downgraded to `note`).
  - start_session auto-closes a prior open session (the spine fills itself on boot).
  - end_session is idempotent (no orphan session-end Beats on repeated calls).
  - a `mark` Beat forces a chapter boundary AND names the chapter (explicit intent).
"""
import os
import sys
import tempfile

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
sys.path.insert(0, _TESTS)

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from core.narrative.chronicler import Chronicler, BoundaryDetector
from core.narrative.schema import Beat, BEAT_KINDS, beat_key
from core.narrative.session import start_session, end_session, SESSION_OPEN_KEY
import json


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _beats_in(store):
    bl = BeatLog(store)
    return [b for b in bl.recent(1000)]


# ---------------- session kind ----------------

def test_session_is_a_real_kind():
    assert "session" in BEAT_KINDS
    assert "mark" in BEAT_KINDS


def test_session_beat_keeps_kind():
    s = _store()
    bl = BeatLog(s)
    b = bl.emit("session", "Session started", "session:start")
    assert b is not None and b.kind == "session"   # not downgraded to "note"


# ---------------- auto-capture lifecycle ----------------

def test_start_session_opens_marker():
    s = _store()
    rep = start_session(s, now="2026-06-01T10:00:00", chronicle=False)
    assert rep["closed_prior"] is False
    assert s.get(SESSION_OPEN_KEY) == "2026-06-01T10:00:00"
    kinds = [b.kind for b in _beats_in(s)]
    assert kinds.count("session") == 1            # one start, no end yet


def test_second_start_closes_prior():
    s = _store()
    start_session(s, now="2026-06-01T10:00:00", chronicle=False)
    rep = start_session(s, now="2026-06-02T10:00:00", chronicle=False)
    assert rep["closed_prior"] is True
    assert s.get(SESSION_OPEN_KEY) == "2026-06-02T10:00:00"
    summaries = sorted(b.summary for b in _beats_in(s))
    # start, end (for prior), start  -> exactly one "Session ended"
    assert summaries.count("Session ended") == 1
    assert summaries.count("Session started") == 2


def test_end_session_idempotent():
    s = _store()
    start_session(s, now="2026-06-01T10:00:00", chronicle=False)
    r1 = end_session(s, now="2026-06-01T18:00:00", chronicle=False)
    r2 = end_session(s, now="2026-06-01T19:00:00", chronicle=False)
    assert r1["closed"] is True and r2["closed"] is False
    ends = [b for b in _beats_in(s) if b.summary == "Session ended"]
    assert len(ends) == 1                          # no orphan end on the 2nd call
    assert s.get(SESSION_OPEN_KEY) is None


# ---------------- mark_chapter ----------------

def test_mark_kind_forces_boundary():
    bd = BoundaryDetector()
    beats = [
        Beat(id="a", at="2026-06-01T10:00:00", kind="note", summary="x", source="s1", weight=1),
        Beat(id="b", at="2026-06-01T10:05:00", kind="mark", summary="New arc", source="s2", weight=5),
        Beat(id="c", at="2026-06-01T10:06:00", kind="note", summary="y", source="s3", weight=1),
    ]
    cuts = bd.detect(beats)
    assert 1 in cuts                                # the mark starts a new chapter


def test_mark_titles_its_chapter():
    s = _store()
    bl = BeatLog(s)
    # one segment whose most salient non-mark beat differs from the mark title
    bl.emit("mark", "Build the evaluation harness", "mark:1",
            at="2026-06-01T10:00:00", track="ai-setup")
    bl.emit("commit", "wip", "git:abc", at="2026-06-01T10:30:00", track="ai-setup", weight=2)
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=tempfile.mkdtemp())
    c.chronicle_all(now="2026-06-02T00:00:00")
    titles = []
    for k in s.keys("narr:chapter:*") if hasattr(s, "keys") else []:
        pass
    # load chapters via atlas/track listing
    from core.narrative.schema import Atlas, Track, track_key, chapter_key, ATLAS_KEY
    atlas = Atlas.from_dict(json.loads(s.get(ATLAS_KEY)))
    found = False
    for t in atlas.tracks:
        tr = Track.from_dict(json.loads(s.get(track_key(t))))
        for cid in tr.chapters:
            ch = json.loads(s.get(chapter_key(cid)))
            if ch["title"] == "Build the evaluation harness":
                found = True
    assert found, "mark summary should become the chapter title"
