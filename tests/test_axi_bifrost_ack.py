"""Pins for `bifrost-ack` after the AXI conversion: the ack, or the refusal, as fields.

Offline: the promoter's verdict and ack are stubbed.
Run: uv run pytest tests/test_axi_bifrost_ack.py -q
"""

import json
import types

import pytest

import agent_cli


@pytest.fixture
def promoter(monkeypatch):
    from core.comm import promoter as P

    state = {"allowed": (True, ""), "ok": True}
    monkeypatch.setattr(P, "resolve_ack_ref", lambda agent, ref: ref.removeprefix("bifrost:"))
    monkeypatch.setattr(P, "ack_verdict", lambda agent, mid: state["allowed"])
    monkeypatch.setattr(P, "ack", lambda agent, mid, note="": state["ok"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _ack(capsys, **over):
    ns = types.SimpleNamespace(agent_id="claude", msg_id="123-0", note="took it", json=False)
    for k, v in over.items():
        setattr(ns, k, v)
    return agent_cli.cmd_bifrost_ack(ns), capsys.readouterr().out


def test_an_ack_is_a_bare_confirmation(promoter, capsys):
    code, text = _ack(capsys)
    assert code == 0
    assert text == 'acked: true\nmsg_id: "bifrost:123-0"\nby: claude\nnote: took it\n'


def test_a_refusal_is_a_structured_error_with_its_reason(promoter, capsys):
    promoter["allowed"] = (False, "bifrost:123-0 has no promoted record -- only salient messages carry acks")
    code, text = _ack(capsys)
    assert code == 1
    assert "code: REFUSED" in text
    assert "acked: false" in text
    assert "no promoted record" in text
    assert "promoted --limit 10" in text


def test_an_unrecorded_ack_is_not_called_acked(promoter, capsys):
    promoter["ok"] = False
    code, text = _ack(capsys)
    assert code == 1
    assert "code: NOT_RECORDED" in text


def test_json_is_unchanged(promoter, capsys):
    code, text = _ack(capsys, json=True)
    assert code == 0
    assert json.loads(text) == {"acked": True, "msg_id": "123-0", "by": "claude"}


def test_human_view(promoter, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _ack(capsys)
    assert text.startswith("Acked\n")
    assert "bifrost:123-0" in text
