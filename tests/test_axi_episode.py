"""Pins for `episode` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_episode.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def ep(monkeypatch):
    import core.narrative.episode as ep_mod
    import core.narrative.episode_suggester as sug

    monkeypatch.setattr(sug, "suggest", lambda: None)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return ep_mod


def _run(capsys, action, chapter_id=None, **kw):
    ns = argparse.Namespace(
        action=action,
        chapter_id=chapter_id,
        title=None,
        desc=None,
        why=None,
        accept_title=None,
        accept_desc=None,
        accept_why=None,
        json=False,
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_episode(ns)
    return code, capsys.readouterr().out


def _chapter(**kw):
    return {"id": "ch_1", "title": "", "why": "", "duration_seconds": 75, "beats_count": 2, **kw}


def test_current_is_one_record_with_the_close_hint(ep, capsys, monkeypatch):
    monkeypatch.setattr(ep, "current_episode", lambda: {"current_chapter": _chapter()})
    code, text = _run(capsys, "current")
    assert code == 0
    assert "episode: ch_1\nstatus: open\ntitle: null\nbeats: 2\nduration_s: 75" in text
    assert "episode close" in text


def test_an_empty_episode_points_at_logging_a_beat(ep, capsys, monkeypatch):
    monkeypatch.setattr(ep, "current_episode", lambda: {"current_chapter": _chapter(beats_count=0)})
    _, text = _run(capsys, "current")
    assert "beats: 0" in text
    assert "log <kind> --summary <text>" in text


def test_close_carries_the_chapter_id_into_the_accept_hint(ep, capsys, monkeypatch):
    draft = {"chapter_id": "ch_9", "title": "fixed it", "description": "fixed it", "why": "fixed it"}
    monkeypatch.setattr(ep, "close_episode", lambda **kw: {"draft": draft, "new_current_chapter": {"id": "ch_10"}})
    code, text = _run(capsys, "close")
    assert code == 0
    assert "closed: ch_9" in text
    assert "next_episode: ch_10" in text
    assert 'episode accept ch_9 --title "fixed it"' in text


def test_accept_errors_are_structured(ep, capsys, monkeypatch):
    code, text = _run(capsys, "accept")
    assert code == 2
    assert "code: USAGE" in text
    monkeypatch.setattr(ep, "accept_episode", lambda *a, **kw: {"error": "unknown_chapter", "chapter_id": "ch_x"})
    code, text = _run(capsys, "accept", "ch_x")
    assert code == 1
    assert "code: NOT_FOUND" in text


def test_human_view(ep, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(ep, "current_episode", lambda: {"current_chapter": _chapter(title="port fix")})
    _, text = _run(capsys, "current")
    assert "open  port fix  ch_1" in text
    assert "2 beat(s), open for 75s" in text
