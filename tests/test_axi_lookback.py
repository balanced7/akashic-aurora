"""Pins for `lookback` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_lookback.py -q
"""

import argparse

import pytest

import agent_cli


def _hit(layer="notes", status="current", score=1.0, excerpt="we chose sqlite", drill="notes --all (id X)"):
    return {"layer": layer, "source": "mem:decision:X", "status": status, "score": score, "excerpt": excerpt,
            "drill": drill}  # fmt: skip


@pytest.fixture
def hits(monkeypatch):
    import core.recall.lookback as lb

    holder: list = []
    monkeypatch.setattr(lb, "lookback", lambda q, per_layer=3, layers=None: list(holder))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, words="why sqlite", layers=None):
    ns = argparse.Namespace(question=words.split(), layers=layers, per_layer=None, json=False)
    code = agent_cli.cmd_lookback(ns)
    return code, capsys.readouterr().out


def test_hits_are_one_table_with_layer_and_status(hits, capsys):
    hits += [_hit(), _hit(status="retired", score=0.3)]
    code, text = _run(capsys)
    assert code == 0
    assert "question: why sqlite\ntotal: 2" in text
    assert "hits[2]{layer,status,score,excerpt,drill}:" in text
    assert "notes,retired,0.3," in text
    assert "help[" not in text  # a notes drill is not a CLI command: no invented hint


def test_a_cli_drill_becomes_the_next_step(hits, capsys):
    hits.append(_hit(layer="chapters", drill="story --chapter chapter_abc"))
    _, text = _run(capsys)
    assert "agent_cli.py story --chapter chapter_abc" in text


def test_no_hits_is_total_zero_with_wider_layers(hits, capsys):
    code, text = _run(capsys, "zebra", layers="notes")
    assert code == 0
    assert "total: 0" in text
    assert "--layers docs," in text


def test_long_excerpt_is_cut_with_its_size(hits, capsys):
    hits.append(_hit(excerpt="word " * 80))
    _, text = _run(capsys)
    assert "(truncated, 399 chars total)" in text


def test_human_view_groups_by_layer(hits, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    hits.append(_hit())
    _, text = _run(capsys)
    assert "1 hit for why sqlite" in text
    assert "notes" in text
    assert "we chose sqlite" in text
