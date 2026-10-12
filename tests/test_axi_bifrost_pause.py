"""Pins for `bifrost-pause` after the AXI conversion: hard or soft, and whether it ends by itself.

Offline: control.pause is stubbed.
Run: uv run pytest tests/test_axi_bifrost_pause.py -q
"""

import types

import pytest

import agent_cli


@pytest.fixture
def control(monkeypatch):
    from core.comm import control as C

    state = {"ok": True}
    monkeypatch.setattr(C, "pause", lambda reason="", by="user", ttl=None, soft=False: state["ok"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _pause(capsys, **over):
    ns = types.SimpleNamespace(reason="barge-in", by="user", ttl=600, soft=False, json=False)
    for k, v in over.items():
        setattr(ns, k, v)
    return agent_cli.cmd_bifrost_pause(ns), capsys.readouterr().out


def test_a_hard_pause_with_a_ttl(control, capsys):
    code, text = _pause(capsys)
    assert code == 0
    assert text.startswith("status: paused\nmode: hard\nself_heals_in_s: 600\n")
    assert 'in_flight_work: "abandoned' in text
    assert "bifrost-resume" in text


def test_a_soft_pause_without_a_ttl_says_it_never_ends_alone(control, capsys):
    _, text = _pause(capsys, soft=True, ttl=None)
    assert "mode: soft" in text
    assert "self_heals: never; holds until bifrost-resume" in text
    assert "finished first" in text


def test_an_offline_bus_is_a_structured_error(control, capsys):
    control["ok"] = False
    code, text = _pause(capsys)
    assert code == 1
    assert "code: BUS_OFFLINE" in text


def test_human_view(control, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _pause(capsys)
    assert text.startswith("PAUSED -- self-heals in 10m")
    assert "by user: barge-in" in text
