"""Pins for `bifrost-resume` after the AXI conversion: what the resume undid, or that it undid nothing.

Offline: control.pause_status and control.resume are stubbed.
Run: uv run pytest tests/test_axi_bifrost_resume.py -q
"""

import types

import pytest

import agent_cli


@pytest.fixture
def control(monkeypatch):
    from core.comm import control as C

    state = {"status": {"paused": False, "online": True, "soft": False}, "ok": True}
    monkeypatch.setattr(C, "pause_status", lambda: state["status"])
    monkeypatch.setattr(C, "resume", lambda targets=None: state["ok"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _resume(capsys):
    return agent_cli.cmd_bifrost_resume(types.SimpleNamespace()), capsys.readouterr().out


def test_resuming_a_pause_names_what_it_undid(control, capsys):
    control["status"] = {"paused": True, "online": True, "soft": True, "by": "user", "reason": "barge-in"}
    code, text = _resume(capsys)
    assert code == 0
    assert text.startswith("status: resumed\nwas_paused: true\npause_was: soft\npaused_by: user\n")
    assert "pause_reason: barge-in" in text


def test_nothing_to_resume_is_said_outright(control, capsys):
    code, text = _resume(capsys)
    assert code == 0
    assert text.startswith('status: "nothing to resume: the bus was not paused"\nwas_paused: false\n')


def test_an_offline_bus_is_a_structured_error(control, capsys):
    control["ok"] = False
    code, text = _resume(capsys)
    assert code == 1
    assert "code: BUS_OFFLINE" in text


def test_human_view(control, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    control["status"] = {"paused": True, "online": True, "soft": False, "by": "user"}
    _, text = _resume(capsys)
    assert text.startswith("Resume\n")
    assert "resumed" in text
