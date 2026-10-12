"""Pins for `bifrost-sync` after the AXI conversion: what an agent and a person see.

The bus is stubbed at agent.bifrost_pull, so nothing here reads Redis.

Run: uv run pytest tests/test_axi_bifrost_sync.py -q
"""

import argparse

import pytest

import agent_cli


def _msg(i, frm, kind, content):
    return {"id": f"{i}-0", "frm": frm, "kind": kind, "content": content, "pending_at_least": 0}


def _block(msgs, **extra):
    for m in msgs:
        m["pending_at_least"] = len(msgs)
    return {
        "bus_online": True,
        "agents_online": [],
        "pending": len(msgs),
        "messages": msgs,
        "locks": [],
        "pause_line": "",
        "expect_lines": [],
        "resume_line": "",
        **extra,
    }


@pytest.fixture
def bus(monkeypatch):
    import agent.bifrost_pull as bp

    state = {"block": _block([]), "consume": {"seat_held": False, "consumed": [], "stale_notice": None}}
    monkeypatch.setattr(bp, "collect_boot_bifrost", lambda *a, **k: state["block"])
    monkeypatch.setattr(bp, "consume_inbox", lambda *a, **k: state["consume"])
    monkeypatch.setattr(bp, "steer_facts_lines", lambda *a, **k: [])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _sync(capsys, **kw):
    ns = argparse.Namespace(agent_id="bench", limit=None, consume=False, json=False, digest=False, traces=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_bifrost_sync(ns)
    return code, capsys.readouterr().out


def test_peek_is_counts_then_a_message_table(bus, capsys):
    bus["block"] = _block([_msg(1, "alice", "request", "review a.py"), _msg(2, "bob", "chat", "build green")])
    code, text = _sync(capsys)
    assert code == 0
    assert "unread: 2" in text
    assert "asks: 1\nfyi: 1" in text
    assert "messages[2]{id,kind,from,text}:" in text
    assert "1-0,request,alice,review a.py" in text
    assert "bifrost-sync bench --consume" in text  # the ack command carries the agent id


def test_empty_inbox_says_zero(bus, capsys):
    code, text = _sync(capsys)
    assert code == 0
    assert "unread: 0\nmessages: []" in text


def test_long_body_is_cut_with_its_size_and_its_real_address(bus, capsys):
    bus["block"] = _block([_msg(7, "dave", "chat", "word " * 200)])
    _, text = _sync(capsys)
    assert "(truncated, 999 chars total)" in text
    assert "bifrost-fetch --get 7-0" in text


def test_twins_collapse_and_traces_fold(bus, capsys):
    bus["block"] = _block(
        [_msg(1, "kimi", "chat", "same"), _msg(2, "kimi", "chat", "same"), _msg(3, "sol", "trace", "t1"),
         _msg(4, "sol", "trace", "t2")]
    )  # fmt: skip
    _, text = _sync(capsys)
    assert "messages[1]{id,kind,from,text,copies}:" in text
    assert "1-0,chat,kimi,same,2" in text
    assert "folded[1]{from,kind,count}:" in text
    assert "sol,trace,2" in text
    assert "bifrost-sync bench --traces" in text


def test_offline_bus_points_at_the_durable_record(bus, capsys):
    bus["block"] = _block([], bus_online=False)
    code, text = _sync(capsys)
    assert code == 0
    assert "bus: offline" in text
    assert "promoted" in text


def test_seat_held_is_a_structured_error(bus, capsys):
    bus["consume"] = {"seat_held": True, "holder": "twin", "teach": "seat held by twin", "peeked": []}
    code, text = _sync(capsys, consume=True)
    assert code == 1
    assert "code: SEAT_HELD" in text
    assert "holder: twin" in text


def test_human_view_leads_with_what_needs_a_reply(bus, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    bus["block"] = _block([_msg(1, "alice", "request", "review a.py")])
    _, text = _sync(capsys)
    assert "1 unread" in text
    assert "1 need a reply" in text
    assert "alice" in text
    assert "review a.py" in text
