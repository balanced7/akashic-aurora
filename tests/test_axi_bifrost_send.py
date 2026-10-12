"""Pins for `bifrost-send` after the AXI conversion: the delivery verdict is a field, not prose.

Offline: the bus is faked and the reply deadline is stubbed, so nothing touches Redis.
Run: uv run pytest tests/test_axi_bifrost_send.py -q
"""

import json
import types

import pytest

import agent_cli


class _Bus:
    reask = None

    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.online = True
        self.last_reask = None

    def register(self, card=None):
        pass

    def send(self, to, kind, text, meta=None):
        self.last_reask = _Bus.reask
        return _Bus.reask or "111-0"

    def broadcast(self, kind, text, meta=None):
        return "222-0"


def _args(**over):
    base = {
        "agent_id": "claude",
        "text": ["please", "review"],
        "text_file": None,
        "to": "deepseek",
        "kind": "request",
        "broadcast": False,
        "expect_reply_within": -1,
        "to_incarnation": None,
        "answers": None,
        "json": False,
    }
    base.update(over)
    return types.SimpleNamespace(**base)


@pytest.fixture
def bus(monkeypatch):
    import core.comm.bus as busmod
    from core.comm import expectations

    _Bus.reask = None
    monkeypatch.setattr(busmod, "Bus", _Bus)
    monkeypatch.setattr(expectations, "arm", lambda *a, **k: True)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return _Bus


def test_a_directed_ask_says_sent_and_when_a_reply_is_due(bus, capsys):
    assert agent_cli.cmd_bifrost_send(_args()) == 0
    text = capsys.readouterr().out
    assert text.startswith("status: sent\nto: deepseek\nkind: request\nid: 111-0\n")
    assert "reply_due_s: 1800" in text
    assert "--expect-reply-within 0 opts out" in text
    assert "bifrost-standby claude" in text  # next step: wait for the answer


def test_a_plain_chat_is_a_bare_confirmation(bus, capsys):
    assert agent_cli.cmd_bifrost_send(_args(kind="chat")) == 0
    text = capsys.readouterr().out
    assert "status: sent" in text
    assert "reply_due_s" not in text
    assert "help[" not in text


def test_a_collapsed_resend_is_not_called_sent(bus, capsys):
    bus.reask = "100-0"
    assert agent_cli.cmd_bifrost_send(_args()) == 0
    text = capsys.readouterr().out
    assert text.startswith("status: collapsed\n")
    assert "collapsed_onto: 100-0" in text
    assert "\nid:" not in text  # the original's id is not this send's id
    assert 'bifrost-nudge claude --to deepseek "<what changed>"' in text


def test_a_broadcast_says_so(bus, capsys):
    agent_cli.cmd_bifrost_send(_args(to="", kind="chat", broadcast=True))
    text = capsys.readouterr().out
    assert "to: *" in text
    assert "broadcast: true" in text


def test_missing_recipient_is_a_usage_error(bus, capsys):
    assert agent_cli.cmd_bifrost_send(_args(to="")) == 2
    text = capsys.readouterr().out
    assert "code: USAGE" in text
    assert "sent: false" in text
    assert "--to <peer>" in text


def test_json_is_unchanged(bus, capsys):
    agent_cli.cmd_bifrost_send(_args(json=True))
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("[bifrost-send] expecting a reply within 1800s [auto: directed ask")
    assert json.loads(lines[1]) == {
        "sent": True,
        "id": "111-0",
        "to": "deepseek",
        "kind": "request",
        "collapsed_onto": None,
        "expect_reply_within": 1800,
    }


def test_human_view_leads_with_the_verdict(bus, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    agent_cli.cmd_bifrost_send(_args())
    text = capsys.readouterr().out
    assert text.startswith("sent request to deepseek  111-0")
    assert "expects a reply within 30m (the default for a directed ask)" in text
