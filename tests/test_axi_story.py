"""Pins for `story` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_story.py -q
"""

import os
import tempfile

import pytest

import agent_cli
from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from core.narrative.chronicler import Chronicler
from core.narrative.track_router import RouteHint


class _Args:
    """argparse stand-in: any unset attribute reads as None."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, _name):
        return None


def _store(chronicled=True):
    s = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    if chronicled:
        c = Chronicler(beat_log=BeatLog(s), store=s, chronicle_dir=tempfile.mkdtemp())
        c.beat_log.emit("note", "first beat", "ledger:1", at="2026-06-27T10:00:00")
        c.beat_log.emit("commit", "fix core bug", "git:a1", at="2026-06-27T10:30:00", hint=RouteHint(paths=["core/"]))
        c.beat_log.emit(
            "learning", "prior art RAPTOR", "learn:exp:1", at="2026-06-28T09:00:00", hint=RouteHint(category="research")
        )
        c.chronicle_all(now="2026-06-28T12:00:00")
    return s


@pytest.fixture(autouse=True)
def _agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, store, **kw):
    code = agent_cli.cmd_story(_Args(**kw), store=store)
    return code, capsys.readouterr().out


def test_atlas_is_a_track_table_with_hints(capsys):
    code, text = _run(capsys, _store())
    assert code == 0
    assert "chapters: " in text
    assert "tracks[2]{track,chapters}:" in text
    assert "story --themes" in text


def test_no_story_is_an_explicit_zero(capsys):
    code, text = _run(capsys, _store(chronicled=False))
    assert code == 0
    assert "chapters: 0" in text
    assert "story --chronicle" in text


def test_track_lists_chapters_without_repeating_the_track(capsys):
    _, text = _run(capsys, _store(), track="research")
    assert "track: research" in text
    assert "total: 1" in text
    assert "chapters[1]{id,title,beats,start,end}:" in text
    assert "story --chapter chapter_" in text  # one chapter: the real id


def test_unknown_track_is_a_structured_error_naming_the_real_ones(capsys):
    code, text = _run(capsys, _store(), track="nope")
    assert code == 2
    assert "code: NOT_FOUND" in text
    assert "available[2]:" in text


def test_theme_with_no_chapters_is_total_zero(capsys):
    code, text = _run(capsys, _store(), theme="no_such_theme")
    assert code == 0
    assert "total: 0\nchapters: []" in text


def test_bad_timestamp_is_a_usage_error(capsys):
    code, text = _run(capsys, _store(), at="yesterday")
    assert code == 2
    assert "code: USAGE" in text


def test_human_view_of_a_track(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, _store(), track="research")
    assert "1 chapter" in text
    assert "1 beats" in text
