"""Pins for `promoted` after the AXI conversion: what an agent and a person see.

The promoter is stubbed, so nothing here reads the event log.

Run: uv run pytest tests/test_axi_promoted.py -q
"""

import argparse

import pytest

import agent_cli


def _ev(i, frm, to, kind, content, **extra):
    return {
        "at": f"2026-10-12T10:0{i}:00+00:00",
        "detail": {"frm": frm, "to": to, "kind": kind, "content": content},
        "refs": [f"bifrost:{i}-0"],
        "_ref": f"event:events:raw:{i}-1",
        "acks": [],
        **extra,
    }


@pytest.fixture
def page(monkeypatch):
    import core.comm.promoter as pm

    state = {"evs": [], "more": False}
    monkeypatch.setattr(pm, "promoted_page", lambda **k: (state["evs"], state["more"]))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _promoted(capsys, **kw):
    ns = argparse.Namespace(limit=None, since=None, until=None, json=False, fields=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_promoted(ns)
    return code, capsys.readouterr().out


def test_rows_are_ref_kind_route_and_text(page, capsys):
    page["evs"] = [_ev(1, "alice", "bob", "handoff", "cache refactor")]
    code, text = _promoted(capsys)
    assert code == 0
    assert "count: 1" in text
    assert "unhandled: 0" in text
    assert "messages[1]{ref,kind,from,to,text}:" in text
    assert "events --get event:events:raw:1-1" in text  # one row: the real ref


def test_unhandled_and_acked_become_a_status_column(page, capsys):
    page["evs"] = [
        _ev(1, "alice", "bob", "handoff", "a", unhandled=True, age_hours=9.0),
        _ev(2, "carol", "bob", "blocker", "b", acks=[{"by": "bob", "at": "2026-10-12T11:00:00"}]),
    ]
    _, text = _promoted(capsys)
    assert "unhandled: 1" in text
    assert "{ref,kind,from,to,status,text}" in text
    assert "unhandled 9h" in text
    assert "acked by bob" in text
    assert "bifrost-ack <agent_id> bifrost:1-0" in text


def test_a_full_page_says_there_is_more(page, capsys):
    page["evs"], page["more"] = [_ev(1, "a", "b", "decision", "x")], True
    _, text = _promoted(capsys, limit=1)
    assert "more: true" in text
    assert "promoted --limit 2" in text


def test_empty_is_an_explicit_zero(page, capsys):
    code, text = _promoted(capsys)
    assert code == 0
    assert "count: 0" in text
    assert "messages: []" in text


def test_fields_adds_columns_and_rejects_unknown_ones(page, capsys):
    page["evs"] = [_ev(1, "alice", "bob", "handoff", "x")]
    _, text = _promoted(capsys, fields="at")
    assert "{ref,at,kind,from,to,text}" in text
    code, text = _promoted(capsys, fields="bogus")
    assert code == 2
    assert "unknown field(s) bogus" in text


def test_human_view_is_a_table(page, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    page["evs"] = [_ev(1, "alice", "bob", "handoff", "cache refactor", unhandled=True, age_hours=9.0)]
    _, text = _promoted(capsys)
    assert "1 unhandled" in text
    assert "alice → bob" in text
    assert "cache refactor" in text
