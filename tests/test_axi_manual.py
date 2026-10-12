"""Pins for `manual` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_manual.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def shelf(monkeypatch, tmp_path):
    from core.manuals import shelf as shelf_mod

    db = tmp_path / "manuals.db"
    real = shelf_mod.Shelf
    monkeypatch.setattr(shelf_mod, "Shelf", lambda embedder=None: real(db_path=db, embedder=None))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "buttons.md").write_text(
        "# Buttons\n\nA button should be at least 44 points tall so a finger can hit it.\n\n"
        "## Colours\n\nUse the accent colour for the primary action only.\n",
        encoding="utf-8",
    )
    return docs


def _run(capsys, cmd, *words, **kw):
    ns = argparse.Namespace(manual_cmd=cmd, words=list(words), shelf="", limit=8, max_chars=6000, mode="bm25",
                            json=False, selector="", **kw)  # fmt: skip
    code = agent_cli.cmd_manual(ns)
    return code, capsys.readouterr().out


def test_empty_shelf_is_said_outright(shelf, capsys):
    code, text = _run(capsys, "list")
    assert code == 0
    assert "shelves: 0" in text
    assert "note: the shelf is empty" in text
    assert "manual ingest <shelf> <folder>" in text


def test_ingest_then_list_then_search(shelf, capsys):
    code, text = _run(capsys, "ingest", "hig", str(shelf))
    assert code == 0
    assert "shelf: hig\nadded: 1" in text
    _, text = _run(capsys, "list")
    assert "by_shelf[1]{shelf,documents,passages}:" in text
    assert "hig,1," in text
    _, text = _run(capsys, "search", "how", "tall", "is", "a", "button")
    assert "total: " in text
    assert "passages[" in text
    assert "44 points" in text


def test_a_miss_names_its_denominator(shelf, capsys):
    _run(capsys, "ingest", "hig", str(shelf))
    code, text = _run(capsys, "search", "zebra")
    assert code == 0
    assert "searched_passages: " in text
    assert "total: 0" in text


def test_missing_question_is_a_usage_error(shelf, capsys):
    code, text = _run(capsys, "search")
    assert code == 2
    assert "code: USAGE" in text


def test_human_search(shelf, capsys, monkeypatch):
    _run(capsys, "ingest", "hig", str(shelf))
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "search", "button", "tall")
    assert "in [hig]" in text
    assert "1. Buttons" in text or "1. buttons" in text
