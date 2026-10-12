"""Pins for `modes` after the AXI conversion: what an agent and a person see.

`modes compare` is exercised on its refusal only: nothing replays.

Run: uv run pytest tests/test_axi_modes.py -q
"""

import argparse

import pytest

from core.metaharness import cli, modes


class _LS:
    store = None

    def load_all_learnings_from_store(self):
        return []


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    import core.learning.learning_store as ls_mod

    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.delenv("AKASHIC_MEMORY_MODE", raising=False)
    monkeypatch.setattr(ls_mod, "get_learning_store_instance", lambda: _LS())


def _run(capsys, action, **kw):
    ns = argparse.Namespace(action=action, base="", compiled="", scenario=None, trials=3, daily_usd=None, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cli.modes_main(ns)
    return code, capsys.readouterr().out


def test_show_names_the_mode_and_where_it_comes_from(capsys):
    code, text = _run(capsys, "show")
    assert code == 0
    assert "mode: interpretive" in text
    assert "set_by: AKASHIC_MEMORY_MODE" in text


def test_placement_counts_moves(capsys, monkeypatch):
    rows = [
        {"lesson": "a", "move": "compile", "why": "proven"},
        {"lesson": "b", "move": "keep", "why": "stays interpretive"},
    ]
    monkeypatch.setattr(modes, "placement", lambda lessons, store=None: rows)
    _, text = _run(capsys, "placement")
    assert "total: 2" in text
    assert "lessons[2]{lesson,move,why}:" in text
    assert "precompile build" in text


def test_empty_placement_and_stale_say_zero(capsys):
    _, text = _run(capsys, "placement")
    assert "total: 0\nlessons: []" in text
    _, text = _run(capsys, "stale")
    assert "stale: 0\nlessons: []" in text


def test_compare_without_flags_is_refused_before_any_run(capsys, monkeypatch):
    monkeypatch.setattr(modes, "compare", lambda *a, **k: pytest.fail("compared without flags"))
    code, text = _run(capsys, "compare", base="baseline")
    assert code == 2
    assert "code: USAGE" in text
    assert "--daily-usd 5" in text


def test_human_show(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "show")
    assert "Memory mode" in text
    assert "interpretive" in text
