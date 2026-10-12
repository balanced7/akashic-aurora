"""Pins for `recall-counters` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_recall_counters.py -q
"""

import argparse
import json

import pytest

import agent_cli
import core.learning.learning_store as ls_mod
import core.recall.at_action as at


class _KV:
    def __init__(self, d):
        self.d = d

    def keys(self, pattern):
        return [k for k in self.d if k.startswith(pattern.rstrip("*"))]

    def get(self, k):
        return self.d.get(k)


class _Lessons:
    def load_all_learnings_from_store(self):
        return [{"experiment_name": "alive"}]


@pytest.fixture
def counters(monkeypatch):
    kv = _KV({})
    monkeypatch.setattr(at, "_store", lambda: kv)
    monkeypatch.setattr(ls_mod, "get_learning_store", _Lessons)
    monkeypatch.setattr(at, "canonicalize_source", lambda s, **kw: s)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return kv


def _run(capsys, fold=False):
    code = agent_cli.cmd_recall_counters(argparse.Namespace(fold=fold, agent_id="claude"))
    return code, capsys.readouterr().out


def test_clean_counters_say_so(counters, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert "bare_slugs_to_merge: 0" in text
    assert "result: counters are clean" in text
    assert "help" not in text


def test_a_report_counts_and_names_ghosts_and_points_at_fold(counters, capsys):
    counters.d = {
        "recall:use:learn:experiment:gone": json.dumps({"surfaced": 4}),
        "recall:use:learn:experiment:voted_gone": json.dumps({"useful": 2}),
    }
    _, text = _run(capsys)
    assert "mode: report only" in text
    assert "ghosts_to_prune: 1" in text
    assert "credited_ghosts_kept: 1" in text
    assert 'ghosts[1]: "learn:experiment:gone"' in text
    assert "recall-counters --fold" in text
    assert "triage" in text


def test_fold_reports_what_it_did(counters, capsys, monkeypatch):
    monkeypatch.setattr(at, "merge_use_counters", lambda **kw: 3)
    monkeypatch.setattr(
        at, "prune_ghost_counters", lambda **kw: {"pruned": ["learn:experiment:gone"], "kept_credited": []}
    )
    monkeypatch.setattr(at, "warm_cache", lambda: 0)
    import core.events.event_log as ev

    monkeypatch.setattr(ev, "capture_event", lambda *a, **k: None)
    _, text = _run(capsys, fold=True)
    assert text.startswith("merged: 3\npruned: 1\ncredited_ghosts_kept: 0")
    assert "help" not in text


def test_human_view(counters, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    counters.d = {"recall:use:learn:experiment:gone": json.dumps({"surfaced": 4})}
    _, text = _run(capsys)
    assert "ghosts to prune" in text
    assert "learn:experiment:gone" in text
