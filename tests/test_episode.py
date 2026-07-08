"""Session bookends -- the live EPISODE layer (core/narrative/episode.py), Slice S1.

An episode IS a Chapter with an open span + `why` (intent). These tests pin the manual lifecycle:
open -> beats accrue -> close+draft {title,description,why} -> accept, plus the WHY-from-the-right-beat
rule (DeepSeek review) and the fail-soft contract shapes DeepSeek's UI renders against.
"""
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


def _emit(store, kind, summary, at, weight=None):
    return BeatLog(store).emit(kind, summary, f"src:{summary}", at=at, weight=weight,
                               themes=[])   # explicit themes -> skip the embedder on the test path


# --- open / current ---------------------------------------------------------------------------------

def test_current_auto_opens_and_returns_contract_shape():
    s = _store()
    cur = ep.current_episode(s, now="2026-07-07T10:00:00")["current_chapter"]
    assert cur is not None
    for k in ("id", "title", "description", "why", "started", "duration_seconds",
              "beats_count", "suggestion"):
        assert k in cur, k
    assert cur["suggestion"] is None
    assert cur["title"] == "" and cur["why"] == ""       # fresh episode is empty until closed


def test_beats_accrue_into_current_duration_and_count():
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00")
    _emit(s, "note", "did a thing", "2026-07-07T10:00:30")
    _emit(s, "note", "did another", "2026-07-07T10:01:00")
    cur = ep.current_episode(s, now="2026-07-07T10:02:00")["current_chapter"]
    assert cur["beats_count"] >= 2
    assert cur["duration_seconds"] == 120


# --- close + draft ----------------------------------------------------------------------------------

def test_close_drafts_fields_opens_next_and_stamps_span_end():
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00")
    _emit(s, "decision", "switch to the parser fix because QA hit an empty-input crash",
          "2026-07-07T10:00:30", weight=4)
    _emit(s, "note", "edited parser.py", "2026-07-07T10:01:00", weight=5)
    res = ep.close_episode(s, now="2026-07-07T10:05:00")
    draft = res["draft"]
    assert draft["title"]                       # drafted from the salient beat
    assert "parser" in draft["title"].lower() or "parser" in draft["description"].lower()
    # WHY comes from the decision beat (the intent), not the highest-weight edit beat
    assert "because" in draft["why"].lower() and "qa" in draft["why"].lower()
    # the closed chapter is stamped + persisted; a NEW current episode is open
    closed = load_chapter_from_store(s, draft["chapter_id"])
    assert closed.span_end == "2026-07-07T10:05:00" and closed.why == draft["why"]
    assert res["new_current_chapter"]["id"] != draft["chapter_id"]
    assert res["new_current_chapter"]["duration_seconds"] == 0


def test_why_uses_latest_decision_or_mark_beat():
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00")
    _emit(s, "decision", "first intent", "2026-07-07T10:00:10")
    _emit(s, "decision", "the real intent that governs this span", "2026-07-07T10:00:40")
    _emit(s, "note", "some work", "2026-07-07T10:01:00", weight=5)
    draft = ep.close_episode(s, now="2026-07-07T10:02:00")["draft"]
    assert draft["why"] == "the real intent that governs this span"


def test_user_fields_win_over_draft():
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00")
    _emit(s, "note", "auto stuff", "2026-07-07T10:00:30")
    draft = ep.close_episode(s, now="2026-07-07T10:02:00",
                             title="My Title", why="My Why", description="My Desc")["draft"]
    assert draft["title"] == "My Title" and draft["why"] == "My Why" and draft["description"] == "My Desc"


def test_writer_seam_paraphrases_why():
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00")
    _emit(s, "decision", "raw intent basis", "2026-07-07T10:00:30")
    captured = {}

    def writer(basis, beats):
        captured["basis"] = basis
        return "PARAPHRASED: " + basis

    draft = ep.close_episode(s, now="2026-07-07T10:02:00", writer=writer)["draft"]
    assert draft["why"] == "PARAPHRASED: raw intent basis"
    assert captured["basis"] == "raw intent basis"      # seam receives the deterministic basis


# --- accept -----------------------------------------------------------------------------------------

def test_accept_applies_edits_and_marks_final_idempotently():
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00")
    _emit(s, "note", "work", "2026-07-07T10:00:30")
    cid = ep.close_episode(s, now="2026-07-07T10:02:00")["draft"]["chapter_id"]
    out = ep.accept_episode(s, cid, title="Final Title", why="Final Why")
    assert out["chapter"]["final"] is True and out["chapter"]["title"] == "Final Title"
    assert load_chapter_from_store(s, cid).final is True
    # idempotent re-accept
    again = ep.accept_episode(s, cid, why="Edited Again")
    assert again["chapter"]["why"] == "Edited Again" and again["chapter"]["final"] is True


def test_accept_unknown_chapter_is_error_not_raise():
    s = _store()
    out = ep.accept_episode(s, "ch_does_not_exist")
    assert out.get("error") == "unknown_chapter"


def test_finalize_one_shot_close_marks_final():
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00")
    _emit(s, "note", "work", "2026-07-07T10:00:30")
    cid = ep.close_episode(s, now="2026-07-07T10:02:00", finalize=True)["draft"]["chapter_id"]
    assert load_chapter_from_store(s, cid).final is True


# --- open_next / session-end force-close (no leaked chapters, DeepSeek Q5) --------------------------

def test_close_open_next_false_leaves_no_open_episode():
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00")
    _emit(s, "note", "work", "2026-07-07T10:00:30")
    res = ep.close_episode(s, now="2026-07-07T10:02:00", open_next=False)
    assert res["new_current_chapter"] is None
    assert ep._load_open(s) is None                      # pointer cleared -> nothing left open


def test_session_end_force_closes_open_episode():
    from core.narrative.session import start_session, end_session
    s = _store()
    start_session(s, now="2026-07-07T10:00:00", chronicle=False)   # opens an episode
    assert ep._load_open(s) is not None
    _emit(s, "decision", "do the thing because reasons", "2026-07-07T10:00:30")
    end_session(s, now="2026-07-07T10:05:00", chronicle=False)     # must force-close it
    assert ep._load_open(s) is None, "session end must not leak an open episode"


def test_session_start_reuses_single_open_episode():
    from core.narrative.session import start_session
    s = _store()
    start_session(s, now="2026-07-07T10:00:00", chronicle=False)
    first = ep._load_open(s)["chapter_id"]
    # a second boot without an explicit end: prior open episode is closed, exactly one stays open
    start_session(s, now="2026-07-07T11:00:00", chronicle=False)
    second = ep._load_open(s)["chapter_id"]
    assert second != first and ep._load_open(s) is not None
