"""Pins for `handoff` after the AXI conversion: the write confirmation, --list, the empty list,
the usage error and the human view.

Run: uv run pytest tests/test_axi_handoff.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def handoff(monkeypatch, capsys):
    import core.signals.coordinator_api as api

    sent = []

    class _Emitter:
        def __init__(self, agent):
            self.agent = agent

        def emit_handoff_to_target_agent(self, to, task, context=None, blockers=None):
            sent.append({"agent_id": self.agent, "task": task, "context": context or {}, "to": to})

    monkeypatch.setattr(api, "SignalEmitter", _Emitter)
    monkeypatch.setattr(agent_cli, "_incoming_handoffs", lambda who: [s for s in sent if s["to"] == who])
    monkeypatch.setattr(agent_cli, "_warn_unmirrored", lambda *a, **k: False)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")

    def run(agent="bench", **kw):
        env = kw.pop("env", {})
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        ns = argparse.Namespace(agent_id=agent, to=None, task=None, note=None, blocker=None, list=False, json=False)
        for k, v in kw.items():
            setattr(ns, k, v)
        code = agent_cli.cmd_handoff(ns)
        return code, capsys.readouterr().out

    return run


def test_write_confirms_target_blockers_and_delivery(handoff):
    code, text = handoff(to="alice", task="finish the migration", blocker="a || b")
    assert code == 0
    assert "recorded: true" in text
    assert "to: alice" in text
    assert "blockers: 2" in text
    assert "delivery: alice's next boot surfaces this as its briefing" in text
    assert "help[" not in text


def test_list_rows_and_the_empty_list(handoff):
    handoff(agent="bob", to="alice", task="review the PR", note="CI green")
    code, text = handoff(agent="alice", list=True)
    assert code == 0
    assert "total: 1" in text
    assert "handoffs[1]{from,task,note}:" in text
    assert "bob,review the PR,CI green" in text
    _, text = handoff(agent="dave", list=True)
    assert "total: 0" in text
    assert "--to dave" in text


def test_missing_target_is_a_usage_error(handoff):
    code, text = handoff(task="x")
    assert code == 2
    assert "code: USAGE" in text


def test_human_view(handoff):
    _, text = handoff(to="alice", task="finish", env={"AURORA_OUTPUT": "human", "NO_COLOR": "1"})
    assert text.startswith("Handoff recorded")
    assert "handoff bench -> alice: finish" in text
