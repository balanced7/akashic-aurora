"""Pins for `notes` after the AXI conversion: totals, cut bodies with their --get hint, the empty
state, --all statuses and the human view.

Run: uv run pytest tests/test_axi_notes.py -q
"""

import argparse
from types import SimpleNamespace as Ns

import pytest

import agent_cli


class _Mem:
    def __init__(self, decs):
        self.decs = decs

    def get_decisions(self, days=3650, include_superseded=False):
        return [d for d in self.decs if include_superseded or not d.superseded]

    def get_retired_titles(self):
        return []

    def get_long_chains(self):
        return []


def _dec(title, body, superseded=False, i=0):
    return Ns(id=f"ADR_{i}", title=title, decision=body, created_at="2026-10-12T10:00:00", superseded=superseded)


@pytest.fixture
def notes(monkeypatch, capsys):
    import core.learning.agent_memory as am

    holder = _Mem([])
    monkeypatch.setattr(am, "get_agent_memory", lambda: holder)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setenv("AKASHIC_AGENT_ID", "alice")

    def run(decs, **kw):
        env = kw.pop("env", {})
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        holder.decs = decs
        ns = argparse.Namespace(project=False, all=False, days=None, limit=25, json=False)
        for k, v in kw.items():
            setattr(ns, k, v)
        code = agent_cli.cmd_notes(ns)
        return code, capsys.readouterr().out

    return run


def test_rows_total_and_the_get_hint_for_a_cut_body(notes):
    code, text = notes([_dec("open-docket", "x " * 200, i=1), _dec("where-we-are", "Wave 3", i=2)])
    assert code == 0
    assert "total: 2" in text
    assert "notes[2]{date,title,note,id}:" in text
    assert "(truncated, " in text
    assert "note alice --get open-docket" in text


def test_a_cut_list_says_how_to_see_the_rest(notes):
    _, text = notes([_dec(f"n{i}", "body", i=i) for i in range(5)], limit=2)
    assert "total: 5" in text
    assert "shown: 2" in text
    assert "notes --limit 5" in text


def test_empty_is_said_outright(notes):
    code, text = notes([])
    assert code == 0
    assert "total: 0" in text
    assert 'note alice --title "<title>"' in text


def test_all_marks_superseded(notes):
    _, text = notes([_dec("w", "new", i=1), _dec("w", "old", superseded=True, i=2)], all=True)
    assert "notes[2]{date,title,note,id,status}:" in text
    assert "superseded" in text


def test_human_view(notes):
    _, text = notes([_dec("where-we-are", "Wave 3")], env={"AURORA_OUTPUT": "human", "NO_COLOR": "1"})
    assert text.startswith("Notes")
    assert "1 active note(s), newest first" in text
    assert "where-we-are" in text
