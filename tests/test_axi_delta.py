"""Pins for `delta` after the AXI conversion: moved, unchanged and newborn, for agents and people.

Run: uv run pytest tests/test_axi_delta.py -q
"""

import argparse

import pytest

import agent_cli

MOVED = (
    "[delta alice] since your last boot (abc1234 -> def5678):\n"
    "  git: 2 commit(s)\n"
    "    def5678 fix the ledger\n"
    "    ccc0000 add a pin\n"
    "  notes: updated since your mark -- aurora notes"
)


@pytest.fixture
def delta(monkeypatch, capsys):
    import agent.harness.delta as d

    holder = {"text": MOVED}
    monkeypatch.setattr(d, "render_full", lambda agent: holder["text"])
    monkeypatch.setattr(d, "delta_boot_block", lambda agent: ("", lambda: True))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")

    def run(text, ack=False, **env):
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        holder["text"] = text
        code = agent_cli.cmd_delta(argparse.Namespace(agent_id="alice", ack=ack))
        return code, capsys.readouterr().out

    return run


def test_moved_is_rows_with_commits_and_the_ack_hint(delta):
    code, text = delta(MOVED)
    assert code == 0
    assert "state: moved" in text
    assert "head: abc1234 -> def5678 (at your last boot -> now)" in text
    assert "moved_since_last_boot[2]{area,change}:" in text
    assert "commits[2]{commit}:" in text
    assert "delta alice --ack" in text


def test_unchanged_and_newborn_are_said_outright(delta):
    _, text = delta("[delta alice] no changes since your last boot")
    assert "state: unchanged" in text
    assert "moved_since_last_boot: 0" in text
    assert "help[" not in text, "nothing to do: no next step"
    _, text = delta("[delta alice] no mark yet (newborn) -- the mark writes at your next boot")
    assert "state: newborn" in text


def test_ack_reports_the_mark(delta):
    _, text = delta(MOVED, ack=True)
    assert "mark: advanced to current positions" in text
    assert "--ack" not in text


def test_human_view(delta):
    _, text = delta(MOVED, AURORA_OUTPUT="human", NO_COLOR="1")
    assert text.startswith("Delta · alice")
    assert "moved since your last boot (abc1234 -> def5678" in text
    assert "def5678 fix the ledger" in text
