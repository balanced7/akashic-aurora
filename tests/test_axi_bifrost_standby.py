"""Pins for `bifrost-standby` after the AXI conversion: the drain, the seat and the listener.

Offline: consume_inbox and the expectations block are stubbed, and no listener is started.
Run: uv run pytest tests/test_axi_bifrost_standby.py -q
"""

import types

import pytest

import agent_cli
from agent import bifrost_pull as bp


@pytest.fixture
def inbox(monkeypatch, tmp_path):
    state = {"res": {"seat_held": False, "consumed": []}, "expect": []}
    monkeypatch.setattr(bp, "consume_inbox", lambda agent_id, limit=20: state["res"])
    monkeypatch.setattr(bp, "collect_boot_bifrost", lambda a, limit=1: {"expect_lines": state["expect"]})
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))  # the arming marker
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _standby(capsys, **over):
    ns = types.SimpleNamespace(agent_id="claude", session="s1", no_listen=True, limit=None)
    for k, v in over.items():
        setattr(ns, k, v)
    return agent_cli.cmd_bifrost_standby(ns), capsys.readouterr().out


def _msg(kind, frm, content):
    return {"kind": kind, "frm": frm, "content": content}


def test_drained_mail_is_counted_and_listed(inbox, capsys):
    inbox["res"] = {
        "seat_held": False,
        "consumed": [_msg("request", "deepseek", "review a.py"), _msg("chat", "kimi", "hi")],
    }
    code, text = _standby(capsys)
    assert code == 0
    assert text.startswith("seat: yours\ndrained: 2\nmail[2]:")
    assert "[request] from deepseek: review a.py" in text
    assert "listener: not armed (--no-listen)" in text
    assert "bifrost-standby claude\n" in text  # the command that arms it


def test_a_clean_inbox_is_an_explicit_zero(inbox, capsys):
    _, text = _standby(capsys)
    assert "drained: 0\nmail: []" in text


def test_expectations_ride_the_report(inbox, capsys):
    inbox["expect"] = ["EXPECTATION redrive #2: deepseek"]
    _, text = _standby(capsys)
    assert "expectations[1]:" in text
    assert "redrive #2" in text


def test_a_twin_holding_the_seat_is_reported_not_listened(inbox, capsys):
    inbox["res"] = {
        "seat_held": True,
        "holder": "session:twin",
        "teach": "seat held",
        "peeked": [_msg("chat", "a", "b")],
    }
    code, text = _standby(capsys, no_listen=False)
    assert code == 1
    assert 'seat: "held by session:twin"' in text
    assert "peeked: 1" in text
    assert 'listener: "not armed: the live twin' in text


def test_the_listener_exit_says_whether_it_was_a_wake(inbox, capsys, monkeypatch):
    monkeypatch.setattr(
        bp,
        "standby",
        lambda *a, **k: {
            "drained": 0,
            "decision": "listen",
            "listen_rc": 0,
            "report": [],
            "mail": [],
            "mail_lines": 0,
            "expect_lines": [],
        },
    )
    _, text = _standby(capsys, no_listen=False)
    assert "listener: exited" in text
    assert "listener_rc: 0" in text
    assert "woke_for: wake-worthy mail or deadline" in text
    assert "bifrost-sync claude" in text


def test_human_view(inbox, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    inbox["res"] = {"seat_held": False, "consumed": [_msg("request", "deepseek", "review a.py")]}
    _, text = _standby(capsys)
    assert text.startswith("drained 1 message")
    assert "[request] from deepseek: review a.py" in text
