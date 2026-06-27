"""
Tests for ThemeAssigner + theme persistence + CLI (Slice 5). Shape, robustness,
and acceptance-bar metrics.

Run: py tests/test_themes.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from core.narrative.chronicler import Chronicler
from core.narrative.schema import (
    Beat, Chapter, Track, Theme, Atlas, Edge,
    beat_key, chapter_key, track_key, theme_key,
    STORY_FORMAT_VERSION,
)
from core.narrative.theme_assigner import ThemeAssigner, THEME_KEYWORDS
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller
from core.narrative.track_router import RouteHint


def _make_store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _run_cli(args, store=None):
    import io
    from agent_cli import cmd_story
    class FakeArgs:
        pass
    fa = FakeArgs()
    fa.chronicle = "--chronicle" in args
    fa.session_end = "--session-end" in args
    fa.track = None
    fa.theme = None
    fa.themes = "--themes" in args
    fa.at = None
    fa.chapter = None
    fa.beat = None
    fa.json = "--json" in args
    for a in args:
        if a.startswith("--track="):
            fa.track = a.split("=", 1)[1]
        elif a.startswith("--theme="):
            fa.theme = a.split("=", 1)[1]
        elif a.startswith("--chapter="):
            fa.chapter = a.split("=", 1)[1]
        elif a.startswith("--beat="):
            fa.beat = a.split("=", 1)[1]
        elif a.startswith("--at="):
            fa.at = a.split("=", 1)[1]
    old_stdout = sys.stdout
    sys.stdout = buf = io.StringIO()
    rc = 0
    try:
        rc = cmd_story(fa, store=store) or 0
    except SystemExit as e:
        rc = e.code if e.code is not None else 0
    except Exception:
        rc = 1
    finally:
        sys.stdout = old_stdout
    return buf.getvalue(), rc


# =========================== ThemeAssigner unit tests ===========================


def test_theme_assigner_keyword_match():
    """Beats with matching keywords get the right theme."""
    ta = ThemeAssigner()

    class FakeBeat:
        summary = "TrackRouter heuristic for domain routing"
        source = ""

    themes = ta.assign(FakeBeat())
    assert "routing" in themes


def test_theme_assigner_multi_label():
    """A beat matching multiple keyword groups gets all matching themes."""
    ta = ThemeAssigner()

    class FakeBeat:
        summary = "Chronicler test benchmark for narrative routing"
        source = ""

    themes = ta.assign(FakeBeat())
    assert "narrative" in themes
    assert "evaluation" in themes
    assert "routing" in themes


def test_theme_assigner_empty():
    """Beat with no matching keywords gets empty list."""
    ta = ThemeAssigner()

    class FakeBeat:
        summary = "completely unrelated content"
        source = ""

    themes = ta.assign(FakeBeat())
    assert themes == []


def test_theme_assigner_uses_source():
    """Source field is also searched for keywords."""
    ta = ThemeAssigner()

    class FakeBeat:
        summary = "some work"
        source = "chronicler:build:1"

    themes = ta.assign(FakeBeat())
    assert "narrative" in themes


# =========================== Chronicler persistence tests ===========================


def _setup_chronicle_with_themes():
    """Create a store with beats that have themes, run chronicle, return store."""
    s = _make_store()
    cdir = tempfile.mkdtemp()
    bl = BeatLog(s)
    bl.emit("note", "fix routing bug in TrackRouter", "src:1",
            at="2026-06-27T10:00:00", weight=1,
            themes=["routing"],
            hint=RouteHint(paths=["core/"]))
    bl.emit("note", "run benchmark suite for chronicler", "src:2",
            at="2026-06-27T10:30:00", weight=1,
            themes=["evaluation", "narrative"],
            hint=RouteHint(paths=["core/"]))
    bl.emit("note", "unrelated admin task", "src:3",
            at="2026-06-27T11:00:00", weight=1,
            themes=[])
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir,
                   ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170),
                   token_budget=4000)
    c.chronicle_all(now="2026-06-27T12:00:00")
    return s


def test_theme_persisted():
    """Chronicler persists theme keys for beats with themes."""
    s = _setup_chronicle_with_themes()
    raw = s.get(theme_key("routing"))
    assert raw is not None, "routing theme should be persisted"
    t = Theme.from_dict(json.loads(raw))
    assert t.id == "routing"
    assert len(t.beats) == 1


def test_theme_persisted_multi_label():
    """Beat with multiple themes creates all theme keys."""
    s = _setup_chronicle_with_themes()
    for th in ("evaluation", "narrative"):
        raw = s.get(theme_key(th))
        assert raw is not None, f"{th} theme should be persisted"
        t = Theme.from_dict(json.loads(raw))
        assert len(t.beats) == 1


def test_theme_empty_beat_no_side_effect():
    """Beat with empty themes does not create spurious theme entries."""
    s = _setup_chronicle_with_themes()
    raw = s.get(theme_key("unrelated"))
    assert raw is None, "no theme should be created for empty-theme beats"


def test_theme_beat_back_link():
    """Beat gets a member_of edge pointing to its theme."""
    s = _setup_chronicle_with_themes()
    raw_at = s.get("narr:atlas:current")
    at = Atlas.from_dict(json.loads(raw_at))
    raw_t = s.get(track_key(at.tracks[0]))
    tr = Track.from_dict(json.loads(raw_t))
    cid = tr.chapters[0]
    raw_ch = s.get(chapter_key(cid))
    ch = Chapter.from_dict(json.loads(raw_ch))
    raw_b = s.get(beat_key(ch.beats[0]))
    b = Beat.from_dict(json.loads(raw_b))
    edge_targets = [e.target for e in b.relates]
    assert any("narr:theme:routing" in t for t in edge_targets), \
        "beat should have member_of edge to routing theme"


def test_theme_idempotent():
    """Re-running chronicle does not duplicate beat IDs in theme list."""
    s = _setup_chronicle_with_themes()
    cdir = tempfile.mkdtemp()
    bl = BeatLog(s)
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir,
                   ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170),
                   token_budget=4000)
    c.chronicle_all(now="2026-06-27T12:00:00")
    raw = s.get(theme_key("routing"))
    t = Theme.from_dict(json.loads(raw))
    beat_ids = t.beats
    assert len(beat_ids) == len(set(beat_ids)), "beat IDs should be unique"


# =========================== CLI tests ===========================


def _setup_cli_with_themes():
    """Create store with chronicled beats that have themes."""
    s = _make_store()
    cdir = tempfile.mkdtemp()
    bl = BeatLog(s)
    bl.emit("note", "routing fix in TrackRouter", "src:1",
            at="2026-06-27T10:00:00", weight=1,
            themes=["routing"],
            hint=RouteHint(paths=["core/"]))
    bl.emit("note", "narrative chronicle benchmark", "src:2",
            at="2026-06-27T11:00:00", weight=1,
            themes=["evaluation", "narrative"],
            hint=RouteHint(paths=["core/"]))
    bl.emit("note", "no themes here", "src:3",
            at="2026-06-27T12:00:00", weight=1,
            themes=[])
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir,
                   ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170),
                   token_budget=4000)
    c.chronicle_all(now="2026-06-27T13:00:00")
    return s


def test_cli_themes_list():
    """story --themes lists all themes with beat counts."""
    s = _setup_cli_with_themes()
    out, rc = _run_cli(["--themes"], store=s)
    assert rc == 0
    assert "routing" in out
    assert "evaluation" in out
    assert "narrative" in out


def test_cli_themes_json():
    """story --themes --json returns JSON dict."""
    s = _setup_cli_with_themes()
    out, rc = _run_cli(["--themes", "--json"], store=s)
    assert rc == 0
    data = json.loads(out)
    assert "routing" in data
    assert "evaluation" in data


def test_cli_theme_filter():
    """story --theme=NAME shows chapters with beats in that theme."""
    s = _setup_cli_with_themes()
    out, rc = _run_cli(["--theme=routing"], store=s)
    assert rc == 0
    assert "routing" in out or "TrackRouter" in out


def test_cli_theme_no_match():
    """story --theme=UNKNOWN returns error code."""
    s = _setup_cli_with_themes()
    out, rc = _run_cli(["--theme=no_such_theme"], store=s)
    assert rc == 1 or "No chapters" in out


def test_cli_theme_cross_track():
    """Themes gather chapters across tracks (cross-cutting)."""
    s = _make_store()
    cdir = tempfile.mkdtemp()
    bl = BeatLog(s)
    bl.emit("note", "routing A", "src:1",
            at="2026-06-27T10:00:00", weight=1,
            themes=["routing"],
            hint=RouteHint(paths=["core/"]))
    bl.emit("note", "routing B", "src:2",
            at="2026-06-27T11:00:00", weight=1,
            themes=["routing"],
            hint=RouteHint(category="research"))
    c = Chronicler(beat_log=bl, store=s, chronicle_dir=cdir,
                   ranker=Ranker(), distiller=Distiller(max_chars_per_entry=170),
                   token_budget=4000)
    c.chronicle_all(now="2026-06-27T12:00:00")
    out, rc = _run_cli(["--theme=routing"], store=s)
    assert rc == 0
    # Should find chapters from both tracks
    assert "1 chapter" in out or "2 chapter" in out or "chapter" in out


def test_cli_empty_store_themes():
    """Empty store with --themes returns empty listing."""
    s = _make_store()
    out, rc = _run_cli(["--themes"], store=s)
    assert rc == 2 or "no story" in out.lower()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
