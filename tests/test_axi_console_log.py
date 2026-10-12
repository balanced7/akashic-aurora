"""Pins for `console-log` after the AXI conversion: what an agent and a person see.

The promoter is stubbed, so nothing here reads the event log.

Run: uv run pytest tests/test_axi_console_log.py -q
"""

import argparse

import pytest

import agent_cli


def _ev(i, kind, **detail):
    return {"kind": kind, "at": f"2026-10-12T10:0{i}:00", "detail": detail, "_ref": f"event:events:raw:{i}-0"}


@pytest.fixture
def log(monkeypatch):
    import core.comm.promoter as pm

    state = {"evs": []}
    monkeypatch.setattr(pm, "console_events", lambda limit=20, **k: state["evs"][:limit])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _console_log(capsys, **kw):
    ns = argparse.Namespace(limit=None, since=None, until=None, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_console_log(ns)
    return code, capsys.readouterr().out


def test_each_kind_becomes_one_row(log, capsys):
    log["evs"] = [
        _ev(3, "file_drop", path="docs/spec.md", bytes=2048, by="user"),
        _ev(2, "bus_control", action="pause", reason="reviewing auth", by="user"),
        _ev(1, "interjection", text="cover nulls", to="claude", intent="steer", by="user"),
    ]
    code, text = _console_log(capsys)
    assert code == 0
    assert "count: 3" in text
    assert "events[3]{ref,kind,by,to,text}:" in text
    assert "file_drop,user,null,docs/spec.md (2048 bytes)" in text
    assert "pause,user,null,reviewing auth" in text
    assert '"interjection:steer",user,claude,cover nulls' in text


def test_a_full_page_says_there_is_more(log, capsys):
    log["evs"] = [_ev(i, "bus_control", action="resume", by="user") for i in range(3)]
    _, text = _console_log(capsys, limit=2)
    assert "count: 2\nmore: true" in text
    assert "console-log --limit 4" in text


def test_empty_is_an_explicit_zero(log, capsys):
    code, text = _console_log(capsys)
    assert code == 0
    assert "count: 0\nevents: []" in text


def test_json_is_the_raw_events(log, capsys):
    log["evs"] = [_ev(1, "bus_control", action="pause", by="user")]
    _, text = _console_log(capsys, json=True)
    assert '"action": "pause"' in text


def test_human_view_is_a_table(log, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    log["evs"] = [_ev(1, "interjection", text="cover nulls", to="claude", intent="steer", by="user")]
    _, text = _console_log(capsys)
    assert "user → claude" in text
    assert "cover nulls" in text
