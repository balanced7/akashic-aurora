"""Pins for `focus` after the AXI conversion: the shown focus, no focus, set, clear, errors.

Run: uv run pytest tests/test_axi_focus.py -q
"""

import argparse

import pytest

import agent_cli
from core.coord import session_focus as SF


def _args(**kw):
    ns = argparse.Namespace(
        agent_id="bench", set="", clear=False, dismiss=False, quiet=False, health=False, session="s1", json=False
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def _run(capsys, **kw):
    code = agent_cli.cmd_focus(_args(**kw))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture(autouse=True)
def _agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _current(monkeypatch, st):
    monkeypatch.setattr(SF, "current", lambda sid: st)


def test_shown_focus_is_counts_and_a_clear_hint(monkeypatch, capsys):
    _current(monkeypatch, {"task": "T001", "calls": 5, "hits": 3, "misses": 2, "streak": 1, "nudges": 0})
    code, text, _ = _run(capsys)
    assert code == 0
    assert text.startswith("focus: T001\ncalls: 5\non_task_files: 3\nelsewhere: 2\nmiss_streak: 1\n")
    assert "focus bench --session s1 --clear" in text
    assert "drift_notes_sent" not in text  # only when a note was sent


def test_no_focus_is_said_outright(monkeypatch, capsys):
    _current(monkeypatch, None)
    code, text, _ = _run(capsys)
    assert code == 0
    assert text.startswith("focus: none\n")
    assert "--set T###" in text


def test_set_lists_the_watched_files(monkeypatch, capsys):
    monkeypatch.setattr(
        SF,
        "set_focus",
        lambda sid, tid, agent="": {"ok": True, "task": "T001", "title": "Fix it", "status": "proposed",
                                    "files": ["a.py", "b.py"], "note": ""},
    )  # fmt: skip
    code, text, _ = _run(capsys, set="T001")
    assert code == 0
    assert "focus: T001\nstatus: proposed\ntitle: Fix it\n" in text
    assert "drift_watched[2]: a.py,b.py" in text


def test_unknown_task_keeps_exit_2(monkeypatch, capsys):
    monkeypatch.setattr(
        SF, "set_focus", lambda sid, tid, agent="": {"ok": False, "error": "no task T999 in the ledger"}
    )
    code, text, _ = _run(capsys, set="T999")
    assert code == 2
    assert "code: NOT_FOUND" in text


def test_no_session_is_a_usage_error(monkeypatch, capsys):
    monkeypatch.setattr(SF, "this_session", lambda: "")
    code, text, _ = _run(capsys, session="")
    assert code == 2
    assert "code: NO_SESSION" in text


def test_clear_reports_what_was_attributed(monkeypatch, capsys):
    monkeypatch.setattr(SF, "clear_focus", lambda sid: {"ok": True, "was": "T001", "calls": 4, "hits": 4, "misses": 0})
    code, text, _ = _run(capsys, clear=True)
    assert code == 0
    assert text.startswith("checked_out: T001\ncalls: 4\n")


def test_json_unchanged(monkeypatch, capsys):
    _current(monkeypatch, None)
    _, text, _ = _run(capsys, json=True)
    assert text == "{}\n"


def test_human_view(monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _current(monkeypatch, {"task": "T001", "calls": 5, "hits": 3, "misses": 2, "streak": 1})
    _, text, _ = _run(capsys)
    assert "Focus · T001" in text
    assert "on task files" in text
