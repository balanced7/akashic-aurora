"""Pins for `roster` after the AXI conversion: seats, by-agent, the empty namespace, the human view.

Run: uv run pytest tests/test_axi_roster.py -q
"""

import argparse
import json

import pytest

import agent_cli
from core.comm import roster as ro


def _row(agent, state="LIVE", age=2.0, code="current"):
    return {
        "seat": f"{agent}#abcd1234",
        "agent": agent,
        "sid8": "abcd1234",
        "phase": "sync",
        "beat_ts": 1.0,
        "beat_age_s": age,
        "seq": 3,
        "state": state,
        "have": {},
        "code_sha": "",
        "code_state": code,
    }


@pytest.fixture
def seats(monkeypatch):
    holder = {"rows": []}
    monkeypatch.setattr(ro, "roster", lambda ns, **k: list(holder["rows"]))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, **kw):
    ns = argparse.Namespace(reap=False, by_agent=False, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_roster(ns)
    return code, capsys.readouterr().out


def test_seats_table_and_blind_spots(seats, capsys):
    seats["rows"] = [_row("alice"), _row("bob", state="DEAD", age=900.0)]
    code, text = _run(capsys)
    assert code == 0
    assert "seats: 2\nlive: 1\n" in text
    assert "seat_rows[2]{seat,state,phase,beat_age_s,code}:" in text
    assert "alice#abcd1234,LIVE,sync,2,current" in text
    assert "not_checked:" in text  # W84: the roster names what it did not check
    assert "unwedge bob" in text  # a seat that is not LIVE gets the drill-down


def test_empty_namespace_is_said_outright(seats, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert "seats: 0\n" in text
    assert "no seat has ever heartbeat" in text


def test_by_agent_states_churn(seats, capsys):
    seats["rows"] = [_row("alice")]
    code, text = _run(capsys, by_agent=True)
    assert code == 0
    assert "by_agent[1]{agent,state,live_seat,beat_age_s,dead,recent_deaths,churning}:" in text
    assert "alice,LIVE,abcd1234,2,0,0,false" in text


def test_json_unchanged(seats, capsys):
    seats["rows"] = [_row("alice")]
    _, text = _run(capsys, json=True)
    assert json.loads(text)[0]["seat"] == "alice#abcd1234"


def test_human_view(seats, monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    seats["rows"] = [_row("alice", age=150.0)]
    _, text = _run(capsys)
    assert "alice#abcd1234" in text
    assert "2m ago" in text
    assert "not checked:" in text
