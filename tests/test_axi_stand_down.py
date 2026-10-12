"""Pins for `stand-down` after the AXI conversion: the yield, the holder after it, or why not.

Offline: runner_lock is stubbed.
Run: uv run pytest tests/test_axi_stand_down.py -q
"""

import types

import pytest

import agent_cli


@pytest.fixture
def lock(monkeypatch):
    from core.comm import runner_lock

    state = {"token": "session:abc12345", "ok": True, "holder": None}
    monkeypatch.setattr(runner_lock, "session_holder_token", lambda: state["token"])
    monkeypatch.setattr(runner_lock, "stand_down", lambda agent, token: state["ok"])
    monkeypatch.setattr(runner_lock, "holder", lambda agent: state["holder"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _stand_down(capsys):
    return agent_cli.cmd_stand_down(types.SimpleNamespace(agent="claude")), capsys.readouterr().out


def test_a_yield_names_the_seat_and_its_free_holder(lock, capsys):
    code, text = _stand_down(capsys)
    assert code == 0
    assert text.startswith('agent: claude\nyielded: true\nby: "session:abc12345"\nholder_now: null\n')
    assert "successor_may_claim: true" in text


def test_no_session_is_a_structured_error_naming_the_variable(lock, capsys):
    lock["token"] = None
    code, text = _stand_down(capsys)
    assert code == 1
    assert "code: NO_SESSION" in text
    assert "yielded: false" in text
    assert "CLAUDE_CODE_SESSION_ID unset" in text


def test_a_failed_yield_is_not_called_yielded(lock, capsys):
    lock["ok"] = False
    lock["holder"] = {"token": "session:abc12345"}
    code, text = _stand_down(capsys)
    assert code == 1
    assert "code: NOT_YIELDED" in text
    assert "successor_may_claim: false" in text


def test_human_view(lock, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _stand_down(capsys)
    assert text.startswith("Stand-down\n")
    assert "claude" in text
