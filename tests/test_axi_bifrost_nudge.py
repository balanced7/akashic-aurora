"""Pins for `bifrost-nudge` after the AXI conversion: the mode, the peer and what it will do.

Offline: the bus and the nudge flags are faked.
Run: uv run pytest tests/test_axi_bifrost_nudge.py -q
"""

import json
import types

import pytest

import agent_cli


class _Bus:
    def __init__(self, agent_id):
        self.online = True

    def register(self, card=None):
        pass

    def send(self, to, kind, text, meta=None):
        return "333-0"


@pytest.fixture
def bus(monkeypatch):
    import core.comm.bus as busmod
    from core.comm import nudge

    monkeypatch.setattr(busmod, "Bus", _Bus)
    monkeypatch.setattr(nudge, "nudge", lambda *a, **k: None)
    monkeypatch.setattr(nudge, "steer_push", lambda *a, **k: None)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _nudge(capsys, **over):
    ns = types.SimpleNamespace(agent_id="claude", text=["look", "at", "X"], to="deepseek", mode="interrupt", json=False)
    for k, v in over.items():
        setattr(ns, k, v)
    return agent_cli.cmd_bifrost_nudge(ns), capsys.readouterr().out


def test_a_nudge_says_what_the_peer_will_do(bus, capsys):
    code, text = _nudge(capsys)
    assert code == 0
    assert text.startswith("status: sent\nto: deepseek\nmode: interrupt\nid: 333-0\n")
    assert "drops its current work" in text


def test_steer_does_not_drop_the_task(bus, capsys):
    _, text = _nudge(capsys, mode="steer")
    assert "mode: steer" in text
    assert "keeps going" in text


def test_a_bad_mode_names_the_valid_ones(bus, capsys):
    code, text = _nudge(capsys, mode="yell")
    assert code == 2
    assert "code: USAGE" in text
    assert "valid_modes[3]: interrupt,steer,inform" in text


def test_missing_peer_is_a_usage_error(bus, capsys):
    code, text = _nudge(capsys, to="")
    assert code == 2
    assert "sent: false" in text
    assert "--to <peer>" in text


def test_json_is_unchanged(bus, capsys):
    _, text = _nudge(capsys, json=True)
    assert json.loads(text) == {"sent": True, "id": "333-0", "to": "deepseek", "mode": "interrupt"}


def test_human_view(bus, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _nudge(capsys, mode="inform")
    assert text.startswith("inform sent to deepseek  333-0")
    assert "nothing is interrupted" in text
