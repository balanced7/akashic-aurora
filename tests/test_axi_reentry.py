"""Pins for `reentry` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_reentry.py -q
"""

import argparse

import pytest

import agent_cli


def _built(moves=(), commits=(), door=None, loops=None):
    b = {
        "since": {"iso": "2026-09-23T12:00:00+00:00", "last_word": None},
        "evidence": {"ledger_moves": list(moves), "commits": list(commits)},
        "open_door": door,
        "your_move": [{"label": "T405 — wake enumerator", "action": "one word opens this: approve T405"}],
        "legend": {"shown": "s", "excluded": "e", "why": "w"},
        "caveat": "this render buys the assembly, not the charge",
    }
    if loops is not None:
        b["open_loops"] = loops
    return b


@pytest.fixture
def built(monkeypatch):
    from core import reentry

    holder = {"built": _built()}
    monkeypatch.setattr(reentry, "build_reentry", lambda **kw: holder["built"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _reentry(capsys, loops=False):
    ns = argparse.Namespace(stale_ok=True, show_open_loops=loops, since=None)
    code = agent_cli.cmd_reentry(ns)
    return code, capsys.readouterr().out


def test_sections_keep_the_order_law(built, capsys):
    built["built"] = _built(moves=[{"id": "T406", "status": "done", "commit": "afe326ad", "title": "eye"}])
    code, text = _reentry(capsys)
    assert code == 0
    assert "moved_total: 1" in text
    assert "T406,done,afe326ad,eye" in text
    assert text.index("moved") < text.index("open_door") < text.index("your_move")
    assert "caveat: " in text
    assert "reentry --show-open-loops" in text


def test_your_move_carries_no_count(built, capsys):
    _, text = _reentry(capsys)
    assert "your_move[1]{door,action}:" in text  # the table length is TOON's, not a field
    assert "your_move_total" not in text


def test_nothing_moved_is_an_explicit_zero(built, capsys):
    _, text = _reentry(capsys)
    assert "moved_total: 0\nmoved: []\ncommits_total: 0" in text
    assert "open_door: null" in text


def test_a_long_commit_list_is_cut_and_says_so(built, capsys):
    built["built"] = _built(commits=[f"c{i:02d} msg" for i in range(30)])
    _, text = _reentry(capsys)
    assert "commits_total: 30" in text
    assert "commits_shown: 12" in text


def test_open_loops_only_when_asked(built, capsys):
    built["built"] = _built(loops=[{"label": "T400 — blob store"}])
    _, text = _reentry(capsys, loops=True)
    assert "open_loops" in text
    assert "help[" not in text


def test_human_view_is_the_render_as_written(built, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _reentry(capsys)
    assert "# re-entry — assembled for Daniil" in text
    assert "## 3 · YOUR MOVE" in text
