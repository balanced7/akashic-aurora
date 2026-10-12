"""Pins for `flightdeck` after the AXI conversion: the agent rows, the drill, empty, human, --json.

Run: uv run pytest tests/test_axi_flightdeck.py -q
"""

import argparse
import json

import pytest

import agent_cli
from core.comm import doctor


def _deck(agents=("alice", "carol"), page_for=None, agent=None):
    rows = [
        {
            "id": a,
            "doctor_page": {"state": "lane_stall"} if a == page_for else None,
            "doctor_findings": int(a == page_for),
        }
        for a in agents
    ]
    fd = {
        "fleet": agent is None,
        "agents": rows,
        "sections": {
            "doctor": {"summary": "doctor: fleet healthy"},
            "pulse": {"summary": "pulse: normal", "zones": {"normal": ["alice"], "absent": ["carol"]}},
            "lane_health": {"alice": {"age_s": 3.2, "depth": 0}},
            "locks": {},
            "commits": [f"abc{i} commit {i}" for i in range(7)],
            "asks": {"alice": {"n_open": 2, "n_redriving": 0, "n_overdue": 1}},
            "turns": {},
            "last_turn": {},
        },
        "composed_of": ["doctor", "pulse", "lane_health", "locks", "commits", "asks", "turns", "last_turn"],
    }
    if agent:
        fd["agent"] = agent
        fd["sections"]["unwedge"] = {"status": "down", "verdict": f"{agent}: down", "recommendation": "start it"}
    return fd


@pytest.fixture
def deck(monkeypatch):
    holder = {"fd": _deck()}
    monkeypatch.setattr(doctor, "flightdeck", lambda agent=None: holder["fd"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, **kw):
    ns = argparse.Namespace(agent=None, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_flightdeck(ns)
    return code, capsys.readouterr().out


def test_agent_rows_and_sections(deck, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert "agents[2]{agent,pulse,status,findings,lane,locks}:" in text
    assert "alice,normal,ok,0,age 3s,0" in text
    assert "carol,legacy,ok,0,legacy,0" in text
    assert "open_asks[1]{agent,open,redriving,overdue}:" in text
    assert "commits_6h: 7" in text
    assert "recent_commits[5]" in text  # cut to five, with the count said
    assert "flightdeck --agent <agent>" in text


def test_a_paged_agent_gets_the_drill(deck, capsys):
    deck["fd"] = _deck(page_for="carol")
    _, text = _run(capsys)
    assert "carol,legacy,lane_stall,1,legacy,0" in text
    assert "flightdeck --agent carol" in text


def test_single_agent_detail(deck, capsys):
    deck["fd"] = _deck(agent="carol")
    _, text = _run(capsys, agent="carol")
    assert "detail:\n  agent: carol\n  status: down" in text


def test_empty_fleet_says_zero(deck, capsys):
    deck["fd"] = _deck(agents=())
    _, text = _run(capsys)
    assert "0 agents seen" in text


def test_json_unchanged(deck, capsys):
    _, text = _run(capsys, json=True)
    assert json.loads(text)["composed_of"][0] == "doctor"


def test_human_view(deck, monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    _, text = _run(capsys)
    assert "a view over: doctor + pulse" in text
    assert "Open asks" in text
