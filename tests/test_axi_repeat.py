"""Pins for `repeat` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_repeat.py -q
"""

import argparse

import pytest

import agent_cli
import core.learning.learning_store as ls_mod

_REPORT = {
    "count": 3,
    "caveat": "counts only repeats that were NOTICED",
    "most_violated": [("stage_paths", 2), ("port_check", 1)],
    "by_recall_outcome": {"silent": 1, "fired": 2},
    "entries": [
        {"of": "stage_paths", "elapsed_s": "6840", "recall_outcome": "fired"},
        {"of": "port_check", "elapsed_s": "466560", "recall_outcome": ""},
    ],
}


class _Store:
    report = _REPORT

    def repeat_report(self):
        return self.report

    def load_all_learnings_from_store(self):
        return [{"experiment_name": "stage_paths"}]

    def record_repeat(self, of, agent_id, what, recall_outcome):
        return {"of": of, "elapsed_s": 6840.0}


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(ls_mod, "LearningStore", _Store)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return _Store


def _run(capsys, **kw):
    ns = argparse.Namespace(source="", what="", recall_outcome="", agent="bob", report=False, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_repeat(ns)
    return code, capsys.readouterr().out


def test_the_report_counts_ranks_and_times(store, capsys):
    code, text = _run(capsys, report=True)
    assert code == 0
    assert text.startswith("total: 3\n")
    assert "by_recall_outcome:\n  fired: 2\n  silent: 1" in text
    assert "most_violated[2]{lesson,repeats}:\n  stage_paths,2" in text
    assert "fastest_broken[2]{lesson,after,recall}:\n  stage_paths,1.9h,fired\n  port_check,5.4d,unrecorded" in text
    assert "recall --full learn:experiment:stage_paths" in text


def test_no_repeats_is_a_zero(store, capsys, monkeypatch):
    monkeypatch.setattr(store, "report", {"count": 0, "caveat": "c"})
    _, text = _run(capsys, report=True)
    assert text.startswith("total: 0\n")


def test_recording_says_how_long_the_lesson_survived(store, capsys):
    code, text = _run(capsys, source="learn:experiment:stage_paths")
    assert code == 0
    assert text.startswith("recorded: stage_paths\nafter_learning: 1.9h\n")
    assert "repeat --report" in text


def test_errors_are_structured_on_stdout(store, capsys):
    code, text = _run(capsys)
    assert code == 2
    assert "code: USAGE" in text
    code, text = _run(capsys, source="nope")
    assert code == 2
    assert "code: NOT_FOUND" in text


def test_human_view(store, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    _, text = _run(capsys, report=True)
    assert "most violated" in text
    assert "stage_paths" in text
