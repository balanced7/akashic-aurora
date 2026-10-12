"""Pins for `shadow` after the AXI conversion: the flattened preview and the usage errors.

Run: uv run pytest tests/test_axi_shadow.py -q
"""

import argparse
import json

import pytest

import agent_cli

SEND = json.dumps({"to": "kimi", "kind": "request", "text": "please rerun the suite"})


@pytest.fixture(autouse=True)
def agent_mode(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _shadow(capsys, target="toolbox:bifrost_send", args_json=SEND, agent="tshadow", as_json=False):
    ns = argparse.Namespace(target=target, agent=agent, args_json=args_json, json=as_json)
    code = agent_cli.cmd_shadow(ns)
    return code, capsys.readouterr().out


def test_preview_is_flat_and_says_nothing_ran(capsys):
    code, text = _shadow(capsys)
    assert code == 0
    assert 'subject: tshadow\naction: "toolbox:bifrost_send"\ntarget: "seat:kimi"\nfidelity: "message:request"' in text
    assert "allowed: " in text
    assert "effects[" in text
    assert "{certainty,effect,claim}" in text
    assert "bifrost.message.enqueue" in text
    assert "executed: nothing (a preview has no effects)" in text
    assert "help" not in text  # a detail view answers itself


def test_json_is_the_full_record(capsys):
    _, text = _shadow(capsys, as_json=True)
    assert json.loads(text)["schema"] == "intent.shadow.v1"


@pytest.mark.parametrize(
    ("kw", "said"),
    [
        ({"args_json": "{bad"}, "--args-json must be one JSON object"),
        ({"args_json": "[1]"}, "must decode to one JSON object"),
        ({"target": "toolbox:delete_everything"}, "unsupported intent-shadow action"),
    ],
)
def test_usage_errors_are_structured_and_exit_2(capsys, kw, said):
    code, text = _shadow(capsys, **kw)
    assert code == 2
    assert "code: USAGE" in text
    assert said in text


def test_missing_subject(capsys, monkeypatch):
    monkeypatch.delenv("AKASHIC_AGENT_ID", raising=False)
    code, text = _shadow(capsys, agent="")
    assert code == 2
    assert "subject is required" in text
