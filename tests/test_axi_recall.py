"""Pins for `recall` and `list` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_recall.py -q
"""

import argparse

import pytest

import agent_cli


class _Store:
    def __init__(self, rows):
        self.rows = rows

    def load_all_learnings_from_store(self):
        return list(self.rows)

    def search_learnings_by_keyword(self, query, agent=None):
        return [r for r in self.rows if query in r["experiment_name"] or query in r.get("recommendation", "")]


def _lesson(name, rec="do the thing", **extra):
    return {"experiment_name": name, "category": "testing", "recommendation": rec, **extra}


@pytest.fixture
def store(monkeypatch):
    import core.learning.learning_store as ls_mod
    from core.learning import scope

    holder = _Store([])
    monkeypatch.setattr(ls_mod, "get_learning_store", lambda: holder)
    monkeypatch.setattr(scope, "current_context", lambda: None)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _recall(capsys, query="", **kw):
    ns = argparse.Namespace(query=query, json=False, full=None, tree=False, agent=None, limit=25, fields=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_recall(ns)
    return code, capsys.readouterr().out


def test_default_schema_is_four_columns(store, capsys):
    store.rows = [_lesson("port_clash", "check port 16379")]
    code, text = _recall(capsys, "port")
    assert code == 0
    assert "total: 1" in text
    assert "lessons[1]{name,category,status,lesson}:" in text
    assert "port_clash,testing,active,check port 16379" in text
    assert "recall --full learn:experiment:port_clash" in text  # one lesson: the real source


def test_zero_matches_is_said_outright(store, capsys):
    code, text = _recall(capsys, "zzz")
    assert code == 0
    assert "query: zzz\ntotal: 0\nlessons: []" in text


def test_a_cut_list_gives_the_total_and_how_to_see_the_rest(store, capsys):
    store.rows = [_lesson(f"l{i:02d}") for i in range(30)]
    _, text = _recall(capsys, limit=25, cmd="list")
    assert "total: 30" in text
    assert "shown: 25" in text
    assert "list --limit 30" in text


def test_long_lesson_text_is_cut_with_its_size_and_a_real_full_hint(store, capsys):
    store.rows = [_lesson("long_one", "x " * 400), _lesson("short_one")]
    _, text = _recall(capsys)
    assert "(truncated, 799 chars total)" in text
    assert "recall --full learn:experiment:long_one" in text


def test_fields_adds_columns_and_rejects_unknown_ones(store, capsys):
    store.rows = [_lesson("a", success="yes")]
    _, text = _recall(capsys, fields="success")
    assert "{name,category,status,lesson,success}" in text
    code, text = _recall(capsys, fields="bogus")
    assert code == 2
    assert "unknown field(s) bogus" in text


def test_graduated_and_benched_are_statuses(store, capsys):
    store.rows = [_lesson("g", graduated="hook"), _lesson("b", benched="2026-10-01")]
    _, text = _recall(capsys)
    assert "g,testing,graduated," in text
    assert "b,testing,benched," in text


def test_full_record_not_found_is_a_structured_error(store, capsys, monkeypatch):
    import core.recall.at_action as at

    monkeypatch.setattr(at, "full_record", lambda src: None)
    code, text = _recall(capsys, full="learn:experiment:nope")
    assert code == 1
    assert "code: NOT_FOUND" in text


def test_human_view_lists_each_lesson(store, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    store.rows = [_lesson("port_clash", "check port 16379")]
    _, text = _recall(capsys, "port")
    assert '1 lesson matching "port"' in text
    assert "port_clash  testing  active" in text
    assert "check port 16379" in text
