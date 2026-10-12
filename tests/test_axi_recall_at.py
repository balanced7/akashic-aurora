"""Pins for `recall-at` after the AXI conversion: what an agent and a person see.

The PreToolUse hook's injected text is render()'s, pinned elsewhere (test_t048_recall_surfaces,
test_recall_at); these pin only the verb.

Run: uv run pytest tests/test_axi_recall_at.py -q
"""

import argparse

import pytest

import core.recall.at_action as at
from core.recall.surface import cmd_recall_at


def _lesson(name, text="restart the embedded redis", success="partial", agent="alice"):
    return {
        "text": text,
        "source": f"learn:experiment:{name}",
        "success": success,
        "agent_id": agent,
        "_use": {},
        "field": "recommendation",
    }


@pytest.fixture
def result(monkeypatch):
    holder = {"res": {}}
    monkeypatch.setattr(at, "recall_at", lambda **kw: holder["res"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, **kw):
    ns = argparse.Namespace(
        path=None, command="bus hangs", subject=None, gesture=None, domain=None, agent_id="bench",
        limit=3, hint_style="cli", json=False,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cmd_recall_at(ns)
    return code, capsys.readouterr().out


def test_lessons_are_a_table_with_status_author_and_source(result, capsys):
    result["res"] = {"lessons": [_lesson("bus_restart")], "locks": [], "verbs": [], "total": 1}
    code, text = _run(capsys)
    assert code == 0
    assert "command: bus hangs\ntotal: 1\n" in text
    assert "lessons[1]{status,by,lesson,source}:" in text
    assert "partial advice,alice,restart the embedded redis," in text
    assert "recall --full learn:experiment:bus_restart" in text
    assert "advice=a suggestion, not an observation" in text


def test_a_cut_list_says_how_many_and_how_to_see_the_rest(result, capsys):
    result["res"] = {"lessons": [_lesson("a")], "locks": [], "verbs": [], "total": 4}
    _, text = _run(capsys, limit=1)
    assert "total: 4\nshown: 1" in text
    assert "recall-at --command 'bus hangs' --limit 4" in text


def test_tool_hint_style_names_tools_not_cli_verbs(result, capsys):
    result["res"] = {"lessons": [_lesson("a")], "locks": [], "verbs": [], "total": 4}
    _, text = _run(capsys, hint_style="tool")
    assert 'knowledge_full(source="learn:experiment:a")' in text
    assert "recall_at(limit=4)" in text
    assert "agent_cli.py" not in text


def test_nothing_relevant_is_said_first(result, capsys):
    result["res"] = {"lessons": [], "locks": [], "verbs": [], "total": 0}
    code, text = _run(capsys)
    assert code == 0
    # core/comm/toolbox.py drops the relay when "nothing relevant" is in the first 80 characters.
    assert "nothing relevant" in text[:80]
    assert "total: 0" in text


def test_a_lock_is_named(result, capsys):
    result["res"] = {"lessons": [], "locks": [{"held_by": "bob", "reason": "x"}], "verbs": [], "total": 0}
    _, text = _run(capsys, path="core/comm/bus.py", command=None)
    assert "locked_by[1]: bob" in text


def test_a_failed_recall_is_not_an_empty_one(result, capsys):
    result["res"] = {"lessons": [], "locks": [], "verbs": [], "total": 0, "error": "ConnectionError"}
    code, text = _run(capsys)
    assert code == 0  # fail-soft, as before
    assert "code: RECALL_UNAVAILABLE" in text
    assert "NOT 'no relevant lessons'" in text


def test_human_view(result, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    result["res"] = {"lessons": [_lesson("bus_restart")], "locks": [{"held_by": "bob"}], "verbs": [], "total": 1}
    _, text = _run(capsys)
    assert "locked by bob" in text
    assert "partial advice by alice" in text
    assert "learn:experiment:bus_restart" in text
