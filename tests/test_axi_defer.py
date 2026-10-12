"""Pins for `defer` after the AXI conversion: the list, the empty queue, filing and discharging.

The queue is pointed at a temporary file and the fleet roster is stubbed, so nothing touches
state/coord/defer_queue.json or Redis.

Run: uv run pytest tests/test_axi_defer.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def queue(monkeypatch, tmp_path):
    from core.comm import doctor
    from core.coord import defer_queue as dq

    monkeypatch.setattr(dq, "QUEUE_PATH", str(tmp_path / "defer_queue.json"))
    monkeypatch.setattr(doctor, "known_agents", lambda: ["claude", "kimi"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return dq


def _defer(capsys, me="claude", cmd=(), **kw):
    ns = argparse.Namespace(
        agent_id=me, cmd_text=list(cmd), needs="exec", why="", list=False, done=None, receipt="", fields=None
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_defer(ns)
    return code, capsys.readouterr().out


def test_list_is_a_table_with_the_count_and_whose_queue(queue, capsys):
    item = queue.add("kimi", "run the full suite", needs="exec", why="baseline")
    code, text = _defer(capsys, list=True)
    assert code == 0
    assert "seat: claude\nseat_status: known\npending: 1" in text
    assert "items[1]{id,needs,by,filed,cmd}:" in text
    assert f"{item['id']},exec,kimi," in text
    assert 'defer claude --done <id> --receipt "what happened"' in text
    _, text = _defer(capsys, list=True, fields="why")
    assert "{id,needs,by,filed,cmd,why}" in text
    assert "baseline" in text


def test_an_unknown_seat_is_named_as_such(queue, capsys):
    queue.add("kimi", "x")
    _, text = _defer(capsys, me="ghost-seat", list=True)
    assert "seat: ghost-seat" in text
    assert "UNKNOWN to the fleet roster (known: claude, kimi)" in text


def test_empty_queue_says_zero_and_names_the_seat(queue, capsys):
    code, text = _defer(capsys, list=True)
    assert code == 0
    assert "pending: 0\nitems: []" in text
    assert "seat: claude" in text


def test_file_and_discharge_confirm(queue, capsys):
    code, text = _defer(capsys, cmd=["run", "the", "suite"])
    assert code == 0
    assert "needs: exec\ncmd: run the suite" in text
    item_id = queue.pending()[0]["id"]
    code, text = _defer(capsys, done=item_id, receipt="green")
    assert code == 0
    assert f"discharged: {item_id}\nby: claude\nreceipt: green" in text


def test_errors_are_structured_and_keep_exit_2(queue, capsys):
    code, text = _defer(capsys, done="nope", receipt="x")
    assert code == 2
    assert "code: NOT_FOUND" in text
    queue.add("kimi", "x")
    code, text = _defer(capsys, done=queue.pending()[0]["id"])
    assert code == 2
    assert "code: USAGE" in text
    code, text = _defer(capsys)
    assert code == 2
    assert "defer needs the command itself" in text


def test_human_view_names_the_seat_and_shows_a_table(queue, capsys, monkeypatch):
    queue.add("kimi", "run the full suite " * 20)
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "160")
    _, text = _defer(capsys, list=True)
    assert "seat claude  known" in text
    assert "truncated" in text
