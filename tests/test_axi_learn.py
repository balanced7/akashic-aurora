"""Pins for `learn` after the AXI conversion: the confirmation, its warnings as fields, the errors.

Run: uv run pytest tests/test_axi_learn.py -q
"""

import os
import tempfile
import types

import pytest

import agent_cli
from core.foundation.store import FileStore
from core.learning.learning_store import LearningStore


def _args(**kw):
    base = {
        "agent_id": "alice",
        "experiment": "port_clash",
        "tried": "ran the suite",
        "result": "hung at start",
        "expected": "",
        "recommend": "Use when tests hang at start: check that port 16379 is free first.",
        "category": "performance",
        "success": "yes",
        "confidence": "high",
        "anti_pattern": "",
        "json": False,
    }
    base.update(kw)
    return types.SimpleNamespace(**base)


@pytest.fixture
def learn(monkeypatch, capsys):
    import core.learning.learning_store as lsmod

    ls = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "l.json")))
    monkeypatch.setattr(lsmod, "get_learning_store", lambda *a, **k: ls)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")

    def run(**kw):
        env = kw.pop("env", {})
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        code = agent_cli.cmd_learn(_args(**kw))
        return code, capsys.readouterr().out

    return run


def test_confirmation_leads_with_recorded_and_has_no_hint(learn):
    code, text = learn()
    assert code == 0
    assert text.startswith("recorded: true\nlesson: port_clash\ncategory: performance\nsuccess: yes")
    assert "help[" not in text, "a plain confirmation answers itself"


def test_a_failure_offers_the_tag_command(learn):
    code, text = learn(experiment="blind_retry", success="no", recommend="Retry once, then stop.")
    assert code == 0
    assert "anti_pattern_hint:" in text
    assert "tag-anti-pattern alice --experiment blind_retry --name " in text


def test_a_related_lesson_is_a_structured_warning(learn):
    learn()
    code, text = learn(experiment="port_clash_again", success="no")
    assert code == 0
    assert "lesson: port_clash" in text
    assert "dims: " in text
    assert "recall --full learn:experiment:port_clash" in text


def test_missing_experiment_is_a_usage_error(learn):
    code, text = learn(experiment="")
    assert code == 2
    assert "code: USAGE" in text
    assert "learn alice --experiment" in text


def test_json_is_unchanged(learn):
    _, text = learn(json=True)
    assert text.strip() == '{"recorded": true, "experiment": "port_clash", "clipped": null}'


def test_human_view(learn):
    _, text = learn(env={"AURORA_OUTPUT": "human", "NO_COLOR": "1"})
    assert text.startswith("Lesson recorded")
    assert "recorded port_clash  performance  success: yes" in text
