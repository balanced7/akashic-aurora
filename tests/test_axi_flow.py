"""Pins for `flow` after the AXI conversion: what an agent and a person see.

flow_trace is stubbed with a built tree, so nothing here reads Redis.

Run: uv run pytest tests/test_axi_flow.py -q
"""

import argparse

import pytest

import agent_cli


def _node(mid, frm, to, kind, offset=0, copies=1, children=(), **extra):
    return {"id": mid, "frm": frm, "to": to, "kind": kind, "offset_ms": offset, "copies": copies,
            "lanes": ["work"], "len": 40, "snippet": f'"{kind} from {frm}"', "children": list(children), **extra}  # fmt: skip


def _trace(flows, nodes):
    return {"flows": flows, "counts": {"flows": len(flows), "nodes": nodes, "copies": nodes, "dropped_by_window": 0}}


@pytest.fixture
def trace(monkeypatch):
    import core.comm.flow_trace as ft

    state = {"out": _trace([], 0)}
    monkeypatch.setattr(ft, "flow_trace", lambda agent, window_ms=0: state["out"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _flow(capsys, **kw):
    ns = argparse.Namespace(agent=None, window="6h", limit=12, json=False, fields=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_flow(ns)
    return code, capsys.readouterr().out


def test_a_reply_row_names_the_ask_it_answers(trace, capsys):
    reply = _node("2-0", "bob", "alice", "reply", offset=4200)
    ask = _node("1-0", "alice", "bob", "request", children=[reply])
    trace["out"] = _trace([{"flow": "1-0", "root": ask, "span_ms": 4200, "nodes": 2}], 2)
    code, text = _flow(capsys)
    assert code == 0
    assert "flows: 1" in text
    assert "rows[2]{id,answers,from,to,kind,gap,text}:" in text
    assert "1-0,null,alice,bob,request,0s,request from alice" in text
    assert "2-0,1-0,bob,alice,reply,4.2s,reply from bob" in text


def test_duplicates_get_a_copies_column(trace, capsys):
    trace["out"] = _trace(
        [{"flow": "1-0", "root": _node("1-0", "a", "b", "chat", copies=2), "span_ms": 0, "nodes": 1}], 1
    )
    _, text = _flow(capsys)
    assert "duplicated: 1" in text
    assert "{id,answers,from,to,kind,gap,copies,text}" in text
    assert "bifrost-fetch --get 1-0 --agent b" in text


def test_a_cut_list_says_how_many_and_how_to_see_all(trace, capsys):
    flows = [{"flow": f"{i}-0", "root": _node(f"{i}-0", "a", "b", "chat"), "span_ms": 0, "nodes": 1} for i in range(3)]
    trace["out"] = _trace(flows, 3)
    _, text = _flow(capsys, limit=2)
    assert "flows: 3\nshown: 2" in text
    assert "flow --window 6h --limit 3" in text


def test_empty_window_is_an_explicit_zero(trace, capsys):
    code, text = _flow(capsys)
    assert code == 0
    assert "flows: 0" in text
    assert "rows: []" in text
    assert "--window 1d" in text


def test_bad_window_is_a_usage_error(trace, capsys):
    code, text = _flow(capsys, window="soon")
    assert code == 2
    assert "code: USAGE" in text


def test_human_view_indents_answers(trace, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    reply = _node("2-0", "bob", "alice", "reply", offset=4200)
    trace["out"] = _trace([{"flow": "1-0", "root": _node("1-0", "alice", "bob", "request", children=[reply]),
                            "span_ms": 4200, "nodes": 2}], 2)  # fmt: skip
    _, text = _flow(capsys)
    assert "alice → bob" in text
    assert "  bob → alice" in text
