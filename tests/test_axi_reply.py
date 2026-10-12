"""Pins for `reply` after the AXI conversion: every delivery verdict survives as a field.

Offline: operator_reply.reply is stubbed with each verdict it can return.
Run: uv run pytest tests/test_axi_reply.py -q
"""

import json
import types

import pytest

import agent_cli

SENT = {
    "ok": True,
    "id": "444-0",
    "delivery": "SENT_NO_FAILURE_RECORDED",
    "model_stamped": False,
    "why": "on the bus, nothing has confessed a failure -- which is not the same fact as the operator having read it",
}


@pytest.fixture
def verdict(monkeypatch):
    from core.comm import operator_reply as OR

    state = {"out": dict(SENT)}
    monkeypatch.setattr(OR, "reply", lambda body, sender=None, to=None, model=None: state["out"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.delenv("AKASHIC_OPERATOR_ID", raising=False)
    return state


def _reply(capsys, **over):
    ns = types.SimpleNamespace(
        text=["the", "fix", "is", "in"], text_file=None, to=None, as_seat=None, model=None, json=False
    )
    for k, v in over.items():
        setattr(ns, k, v)
    return agent_cli.cmd_reply(ns), capsys.readouterr().out


def test_sent_keeps_the_honest_verdict_word(verdict, capsys):
    code, text = _reply(capsys)
    assert code == 0
    assert text.startswith("sent: true\ndelivery: SENT_NO_FAILURE_RECORDED\nto: daniil\nid: 444-0\n")
    assert "not the same fact as the operator having read it" in text


def test_unknown_is_sent_but_unverified(verdict, capsys):
    verdict["out"] = {**SENT, "delivery": "UNKNOWN", "why": "sent, but the failure log could not be read"}
    code, text = _reply(capsys)
    assert code == 0
    assert "delivery: UNKNOWN" in text


def test_a_recorded_post_failure_is_an_error_with_the_id(verdict, capsys):
    verdict["out"] = {**SENT, "delivery": "FAILED", "why": "the bus took it but the Discord post FAILED: 400"}
    code, text = _reply(capsys)
    assert code == 1
    assert "code: FAILED" in text
    assert "sent: true" in text  # the bus took it; the operator did not get it
    assert "delivery: FAILED" in text
    assert "id: 444-0" in text


def test_a_refusal_is_an_error(verdict, capsys):
    verdict["out"] = {"ok": False, "why": "refusing an EMPTY reply", "delivery": "REFUSED", "id": None}
    code, text = _reply(capsys, text=[])
    assert code == 1
    assert "code: REFUSED" in text
    assert "sent: false" in text


def test_an_unreadable_text_file_is_a_usage_error(verdict, capsys):
    code, text = _reply(capsys, text_file="/nonexistent/r.txt")
    assert code == 2
    assert "code: USAGE" in text
    assert "path: /nonexistent/r.txt" in text


def test_json_is_unchanged(verdict, capsys):
    _, text = _reply(capsys, json=True)
    assert json.loads(text) == SENT


def test_human_view(verdict, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _reply(capsys)
    assert text.startswith("sent to daniil  444-0")
