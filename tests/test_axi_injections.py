"""Pins for `injections` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_injections.py -q
"""

import argparse
import time

import pytest

import agent_cli
import core.recall.at_action as at


@pytest.fixture
def ledger(monkeypatch):
    rows: list = []
    monkeypatch.setattr(at, "recent_injections", lambda hours: rows)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return rows


def _run(capsys, hours=24):
    code = agent_cli.cmd_injections(argparse.Namespace(hours=hours, json=False))
    return code, capsys.readouterr().out


def test_an_empty_window_is_said_outright(ledger, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert text.startswith("window_hours: 24\ntotal: 0\ntokens_pushed: 0\nby_family:\n  conductor: 0\n")
    assert "nothing cleared the relevance floor" in text
    assert "injections --hours 168" in text


def test_injections_are_a_table_with_the_gauge_and_a_real_source(ledger, capsys):
    now = time.time()
    ledger += [
        {"at": now, "alt": "action", "t": "", "s": ["learn:experiment:conductor_stance"], "chars": 400},
        {"at": now, "alt": "plan", "t": "", "s": [f"learn:experiment:l{i}" for i in range(5)], "chars": 800},
    ]
    _, text = _run(capsys)
    assert "total: 2\ntokens_pushed: 300" in text
    assert "  conductor: 1" in text
    assert "injections[2]{at,altitude,target,chars,lessons}:" in text
    assert ",plan,(prompt),800,l0 l1 l2 +2" in text
    assert "recall-feedback --source learn:experiment:l0 --noise" in text


def test_a_cut_list_says_so(ledger, capsys):
    ledger += [{"at": time.time(), "alt": "action", "t": "", "s": ["learn:experiment:a"], "chars": 4}] * 30
    _, text = _run(capsys)
    assert "total: 30\n" in text
    assert "shown: 25" in text


def test_human_view(ledger, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "140")
    ledger.append({"at": time.time(), "alt": "plan", "t": "", "s": ["learn:experiment:a"], "chars": 40})
    _, text = _run(capsys)
    assert "tokens pushed" in text
    assert "(prompt)" in text
