"""Pins for `graduate` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_graduate.py -q
"""

import argparse

import pytest

import agent_cli
import core.events.event_log as ev
import core.learning.learning_store as ls_mod
import core.recall.at_action as at


class _Lessons:
    def mark_graduated(self, exp, enforced, undo=False):
        return exp == "blanket_staging"


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(ls_mod, "get_learning_store", _Lessons)
    monkeypatch.setattr(at, "warm_cache", lambda *a, **k: 0)
    monkeypatch.setattr(ev, "capture_event", lambda *a, **k: None)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, **kw):
    ns = argparse.Namespace(agent_id="claude", experiment="blanket_staging", enforced_by="hook", undo=False, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_graduate(ns)
    return code, capsys.readouterr().out


def test_graduating_confirms_with_its_effect_and_no_hints(store, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert text.startswith("experiment: blanket_staging\ngraduated: true\nenforced_by: hook\n")
    assert "recall_slots: no (history kept)" in text
    assert "help" not in text


def test_undo(store, capsys):
    _, text = _run(capsys, undo=True, enforced_by=None)
    assert "graduated: false" in text
    assert "recall_slots: yes" in text


def test_missing_enforced_by_is_a_usage_error_with_the_fixed_command(store, capsys):
    code, text = _run(capsys, enforced_by=None)
    assert code == 2
    assert "missing --enforced-by" in text
    assert 'graduate claude --experiment blanket_staging --enforced-by "<automation>"' in text


def test_unknown_lesson_is_not_found(store, capsys):
    code, text = _run(capsys, experiment="nope")
    assert code == 1
    assert "code: NOT_FOUND" in text


def test_human_view(store, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys)
    assert "Graduate" in text
    assert "enforced by" in text
    assert "hook" in text
