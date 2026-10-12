"""Pins for `scope` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_scope.py -q
"""

import argparse

import pytest

import agent_cli


class _Store:
    def __init__(self, rows):
        self.rows = {r["experiment_name"]: r for r in rows}

    def load_all_learnings_from_store(self):
        return list(self.rows.values())

    def _load_experiment(self, name):
        return self.rows.get(name)

    def set_scope(self, name, scope):
        self.rows[name]["scope"] = scope
        return True


@pytest.fixture
def store(monkeypatch):
    import core.learning.learning_store as ls_mod
    from core.learning import scope

    holder = _Store([])
    monkeypatch.setattr(ls_mod, "get_learning_store", lambda: holder)
    monkeypatch.setattr(scope, "proposals_now", lambda ls: [])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _scope(capsys, action, **kw):
    ns = argparse.Namespace(action=action, experiment="", scope="", kinds="", force=False, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_scope(ns)
    return code, capsys.readouterr().out


def test_tree_is_one_row_per_scope_with_the_total(store, capsys):
    store.rows = {
        "a": {"experiment_name": "a", "scope": "universal"},
        "b": {"experiment_name": "b", "scope": "universal"},
        "c": {"experiment_name": "c", "scope": "harness:codex-cli"},
    }
    code, text = _scope(capsys, "tree")
    assert code == 0
    assert "total: 3" in text
    assert "scopes[2]{level,scope,count,lessons}:" in text
    assert 'universal,universal,2,"a, b"' in text
    assert "scope proposals" in text


def test_empty_tree_and_no_proposals_say_zero(store, capsys):
    _, text = _scope(capsys, "tree")
    assert "total: 0\nscopes: []" in text
    _, text = _scope(capsys, "proposals")
    assert "total: 0\nproposals: []" in text
    assert "needs: " in text


def test_missing_lesson_and_missing_flag_are_structured_errors(store, capsys):
    code, text = _scope(capsys, "show", experiment="nope")
    assert code == 1
    assert "code: NOT_FOUND" in text
    code, text = _scope(capsys, "show")
    assert code == 2
    assert "code: USAGE" in text


def test_set_confirms_from_and_to_and_json_is_unchanged(store, capsys):
    store.rows = {"a": {"experiment_name": "a", "scope": "harness:codex-cli"}}
    code, text = _scope(capsys, "set", experiment="a", scope="universal")
    assert code == 0
    assert 'experiment: a\nfrom: "harness:codex-cli"\nto: universal' in text
    code, text = _scope(capsys, "show", experiment="a", json=True)
    assert text.strip() == '{"experiment": "a", "scope": "universal", "level": "universal"}'


def test_human_tree_is_a_table(store, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    store.rows = {"a": {"experiment_name": "a", "scope": "universal"}}
    _, text = _scope(capsys, "tree")
    assert "Lesson scopes" in text
    assert "level" in text
    assert "count" in text
