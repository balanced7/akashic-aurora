"""Pins for `scout` after the AXI conversion: what an agent and a person see.

scout_ask is replaced in every case, so no model is called and no verdict is filed.

Run: uv run pytest tests/test_axi_scout.py -q
"""

import argparse

import pytest

import agent_cli

CLOSED = "no DEEPSEEK_API_KEY and no .secrets/deepseek.key -- the deepseek door is closed"


@pytest.fixture
def scout(monkeypatch):
    from core.fleet import scout as SC

    holder = {"r": None, "raise": None}

    def ask(q, **kw):
        if holder["raise"]:
            raise ValueError(holder["raise"])
        return holder["r"]

    monkeypatch.setattr(SC, "scout_ask", ask)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _result(answer="", ok=False, why=CLOSED):
    return {
        "answer": answer,
        "ask_id": "scout-abc123",
        "ok": ok,
        "tier": "blind",
        "pack_meta": {"sections": {"in_flight": 24, "locks": 0}},
        "why": why,
    }


def _scout(capsys, *words):
    ns = argparse.Namespace(
        text=list(words), wearer="deepseek", by="claude", blind=True, shape="descriptive", json=False
    )
    code = agent_cli.cmd_scout(ns)
    return code, capsys.readouterr().out


def test_a_closed_door_names_the_vault_command_and_the_adjudication(scout, capsys):
    scout["r"] = _result()
    code, text = _scout(capsys, "anyone", "on", "core/axi")
    assert code == 1
    assert "ok: false" in text
    assert "answer: null" in text
    assert "pack:\n  in_flight: 24\n  locks: 0" in text
    assert "secret deepseek.key" in text
    assert "resident adjudicate scout-abc123 --outcome confirmed|refuted" in text


def test_an_answer_is_cut_with_its_size(scout, capsys):
    scout["r"] = _result(answer="T401 is in flight. " * 80, ok=True, why="")
    code, text = _scout(capsys, "anyone")
    assert code == 0
    assert "chars total)" in text
    assert "secret " not in text


def test_a_refusal_is_on_stdout_with_the_blind_alternative(scout, capsys):
    scout["raise"] = "refused: 'deepseek' is not a resident"
    code, text = _scout(capsys, "anyone")
    assert code == 1
    assert "code: REFUSED" in text
    assert 'scout "anyone" --blind' in text


def test_no_question_is_a_usage_error(scout, capsys):
    code, text = _scout(capsys)
    assert code == 2
    assert "code: USAGE" in text


def test_human_view(scout, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    scout["r"] = _result()
    _, text = _scout(capsys, "anyone")
    assert "Scout · blind" in text
    assert "filed, unadjudicated" in text
