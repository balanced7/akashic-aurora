"""Pins for `tally` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_tally.py -q
"""

import argparse
import json

import pytest

import agent_cli


@pytest.fixture
def research(tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    d = tmp_path / "research"
    d.mkdir()
    opening = d / "routing-opening-2026-10.md"
    opening.write_text("Q1: keep it?\nQ2: move it?\n", encoding="utf-8")
    return d, opening


def _counter(d, author, body):
    (d / f"{author}-counter.md").write_text(f"counter to routing-opening-2026-10\n{body}\n", encoding="utf-8")


def _run(capsys, opening, research_dir, **kw):
    ns = argparse.Namespace(opening=str(opening), research_dir=str(research_dir), json=kw.get("json", False))
    code = agent_cli.cmd_tally(ns)
    return code, capsys.readouterr().out


def test_matrix_with_one_column_per_author_and_counts(research, capsys):
    d, opening = research
    _counter(d, "kimi", "Q1: KEEP\nQ2: AMEND")
    _counter(d, "claude", "Q1: KEEP\nQ2: KILL")
    (d / "sol-brief.md").write_text("see routing-opening-2026-10\n", encoding="utf-8")
    code, text = _run(capsys, opening, d)
    assert code == 0
    assert "counters: 2\nagree: 1\nconflict: 1\npartial: 0\nopen: 0" in text
    assert "questions[2]{q,claude,kimi,status}:" in text
    assert "Q2,KILL,AMEND,CONFLICT" in text
    assert "mentions[1]: sol-brief.md" in text
    assert "help[" not in text  # the matrix answers itself
    assert "consensus" not in text


def test_one_voice_refuses_the_consensus_claim(research, capsys):
    d, opening = research
    _counter(d, "kimi", "Q1: KEEP")
    _, text = _run(capsys, opening, d)
    assert 'consensus: "none claimed, one voice' in text
    assert "Q1,KEEP,partial" in text


def test_no_counters_is_an_explicit_zero(research, capsys):
    d, opening = research
    code, text = _run(capsys, opening, d)
    assert code == 0
    assert "counters: 0" in text
    assert "Q1,open" in text


def test_missing_opening_is_a_usage_error(research, capsys):
    d, _ = research
    code, text = _run(capsys, "", d)
    assert code == 2
    assert "code: USAGE" in text


def test_json_is_unchanged(research, capsys):
    d, opening = research
    _counter(d, "kimi", "Q1: KEEP")
    _, text = _run(capsys, opening, d, json=True)
    doc = json.loads(text)
    assert doc["authors"] == ["kimi"]
    assert doc["status"]["Q1"] == "partial"


def test_human_view_counts_then_matrix(research, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    d, opening = research
    _counter(d, "kimi", "Q1: KEEP\nQ2: AMEND")
    _counter(d, "claude", "Q1: KEEP\nQ2: KILL")
    _, text = _run(capsys, opening, d)
    assert "2 counters: claude, kimi   1 agree  1 conflict  0 partial  0 open" in text
    row = next(line for line in text.splitlines() if line.strip().startswith("Q2"))
    assert row.split() == ["Q2", "KILL", "AMEND", "CONFLICT"]
