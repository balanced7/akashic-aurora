"""Pins for `bifrost-drain` after the AXI conversion: what was asked of which runner, and for how long.

Offline: control.drain is stubbed.
Run: uv run pytest tests/test_axi_bifrost_drain.py -q
"""

import types

import pytest

import agent_cli


@pytest.fixture
def control(monkeypatch):
    from core.comm import control as C

    state = {"ok": True}
    monkeypatch.setattr(C, "drain", lambda agent, by="user", reason="": state["ok"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _drain(capsys, reason="new code"):
    code = agent_cli.cmd_bifrost_drain(types.SimpleNamespace(agent_id="claude", to="deepseek", reason=reason))
    return code, capsys.readouterr().out


def test_a_drain_says_which_runner_and_when_it_clears(control, capsys):
    code, text = _drain(capsys)
    assert code == 0
    assert text.startswith("status: requested\nrunner: deepseek\nclears_in_s: 300\n")
    assert "finish the message in hand" in text
    assert "after_exit: relaunch it" in text
    assert "reason: new code" in text


def test_an_offline_bus_is_a_structured_error(control, capsys):
    control["ok"] = False
    code, text = _drain(capsys)
    assert code == 1
    assert "code: BUS_OFFLINE" in text
    assert "requested: false" in text


def test_human_view(control, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _drain(capsys, reason="")
    assert text.startswith("Drain\n")
    assert "deepseek" in text
    assert "reason" not in text
