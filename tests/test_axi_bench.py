"""Pins for `bench` (the S0 triage bench, not the AXI bench harness) after the AXI conversion.

triage_park is stubbed, so nothing here reads Redis.

Run: uv run pytest tests/test_axi_bench.py -q
"""

import argparse

import pytest

import agent_cli


def _entry(pid, frm="alice", content="please review a.py"):
    return {"parked_id": pid, "msg": {"id": "1-0", "frm": frm, "kind": "request", "content": content},
            "reason": "stale", "by": "bench", "parked_at": "2026-10-12T10:00:00+00:00"}  # fmt: skip


@pytest.fixture
def bench(monkeypatch):
    import core.comm.triage_park as tp

    state = {"bench": []}

    def unpark(agent, pid):
        for e in state["bench"]:
            if e["parked_id"] == pid:
                state["bench"].remove(e)
                return e
        return None

    monkeypatch.setattr(tp, "list_parked", lambda agent: list(state["bench"]))
    monkeypatch.setattr(tp, "unpark", unpark)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _bench(capsys, action="list", ref=""):
    code = agent_cli.cmd_bench(argparse.Namespace(agent_id="bench", action=action, ref=ref, reason="stale", by=""))
    return code, capsys.readouterr().out


def test_listing_counts_and_names_the_unpark_command(bench, capsys):
    bench["bench"] = [_entry("abc123")]
    code, text = _bench(capsys)
    assert code == 0
    assert "parked: 1" in text
    assert "bench[1]{parked_id,kind,from,reason,text}:" in text
    assert "abc123,request,alice,stale,please review a.py" in text
    assert "bench bench unpark abc123" in text


def test_empty_bench_is_an_explicit_zero(bench, capsys):
    code, text = _bench(capsys)
    assert code == 0
    assert "parked: 0\nbench: []" in text


def test_unpark_hands_back_the_whole_ask(bench, capsys):
    bench["bench"] = [_entry("abc123", content="x" * 1000)]
    code, text = _bench(capsys, "unpark", "abc123")
    assert code == 0
    assert "returned: abc123" in text
    assert "x" * 1000 in text  # the bench forgets it: nothing may be cut


def test_unpark_unknown_is_not_found(bench, capsys):
    code, text = _bench(capsys, "unpark", "nope")
    assert code == 1
    assert "code: NOT_FOUND" in text


def test_park_without_a_ref_is_a_usage_error(bench, capsys):
    code, text = _bench(capsys, "park")
    assert code == 2
    assert "code: USAGE" in text


def test_human_view_is_a_table(bench, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    bench["bench"] = [_entry("abc123")]
    _, text = _bench(capsys)
    assert "1 parked" in text
    assert "abc123" in text
