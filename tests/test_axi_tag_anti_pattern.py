"""Pins for `tag-anti-pattern` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_tag_anti_pattern.py -q
"""

import argparse
import json

import pytest

import agent_cli
import core.learning.learning_store as ls_mod


class _Lessons:
    def tag_anti_pattern(self, experiment, name, reason=""):
        return experiment == "blind_retry"


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(ls_mod, "get_learning_store", _Lessons)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, **kw):
    ns = argparse.Namespace(agent_id="claude", experiment="blind_retry", name="retry-loop", reason="", json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_tag_anti_pattern(ns)
    return code, capsys.readouterr().out


def test_tagging_confirms(store, capsys):
    code, text = _run(capsys, reason="locks the account")
    assert code == 0
    assert text.startswith("tagged: true\nexperiment: blind_retry\nanti_pattern: retry-loop\nrecall: warns on it now")
    assert "help" not in text


def test_an_unknown_lesson_is_not_found_and_names_learn(store, capsys):
    code, text = _run(capsys, experiment="nope")
    assert code == 1
    assert "code: NOT_FOUND" in text
    assert "learn claude --experiment nope" in text


def test_json_is_unchanged(store, capsys):
    code, text = _run(capsys, json=True)
    assert code == 0
    assert json.loads(text) == {"tagged": True, "experiment": "blind_retry", "anti_pattern": "retry-loop"}


def test_human_view(store, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys)
    assert "anti pattern" in text
    assert "retry-loop" in text
