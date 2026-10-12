"""Pins for `followup` after the AXI conversion: both halves named, replays and refusals.

The repo root and the defer queue are pointed at a temporary directory.

Run: uv run pytest tests/test_axi_followup.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def root(monkeypatch, tmp_path):
    from core.coord import defer_queue as dq
    from core.toolbelt import followup

    monkeypatch.setattr(followup, "ROOT", str(tmp_path))
    monkeypatch.setattr(dq, "QUEUE_PATH", str(tmp_path / "defer_queue.json"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    (tmp_path / "verdict.md").write_text("# Verdict\n\nSome analysis.\n", encoding="utf-8")
    return tmp_path


def _followup(capsys, on="verdict.md", ask="does B1 hold?", json=False):
    ns = argparse.Namespace(agent_id="tfu", on=on, to="kimi", ask=ask, needs="write", json=json)
    code = agent_cli.cmd_followup(ns)
    return code, capsys.readouterr().out


def test_a_filed_followup_names_both_halves(root, capsys):
    code, text = _followup(capsys)
    assert code == 0
    assert "question: Q1\nfile: verdict.md\nto: kimi\ndefer_id: " in text
    assert "status: filed" in text
    assert "block: Open Questions created" in text
    assert "defer kimi --list" in text


def test_a_replay_says_already_open(root, capsys):
    _followup(capsys)
    _, text = _followup(capsys)
    assert "question: Q1" in text
    assert "status: already open" in text


def test_refusals_are_structured_and_keep_exit_2(root, capsys):
    code, text = _followup(capsys, on="gone.md")
    assert code == 2
    assert "code: NOT_FOUND" in text
    code, text = _followup(capsys, ask="")
    assert code == 2
    assert "code: REFUSED" in text


def test_json_refusal_keeps_its_old_line(root, capsys):
    code, text = _followup(capsys, on="gone.md", json=True)
    assert code == 2
    assert text.startswith("[followup] no verdict file")


def test_human_view(root, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _followup(capsys)
    assert "Followup · Q1" in text
    assert "defer id" in text
