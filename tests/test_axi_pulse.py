"""Pins for `pulse` after the AXI conversion: readings by pressure, exit codes, empty, human.

Run: uv run pytest tests/test_axi_pulse.py -q
"""

import argparse
import json

import pytest

import agent_cli
from core.comm import doctor


def _pulse(readings):
    zones = {"critical": [], "elevated": [], "normal": [], "absent": []}
    for a, r in readings.items():
        zones[r["zone"]].append(a)
    return {"agents": list(readings), "zones": zones, "readings": readings, "summary": "pulse: test"}


@pytest.fixture
def fleet(monkeypatch):
    holder = {"p": _pulse({})}
    monkeypatch.setattr(doctor, "pulse", lambda agents=None: holder["p"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, **kw):
    ns = argparse.Namespace(agent=None, json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_pulse(ns)
    return code, capsys.readouterr().out


def test_rows_lead_with_the_worst_pressure(fleet, capsys):
    fleet["p"] = _pulse(
        {
            "alice": {"zone": "normal", "backlog": 2},
            "bob": {"zone": "elevated", "backlog": 12},
            "carol": {"zone": "absent", "backlog": 0},
        }
    )
    code, text = _run(capsys)
    assert code == 0
    assert "agents: 3\nelevated: 1\nnormal: 1\nno_lane: 1\n" in text
    assert "readings[3]{agent,zone,backlog}:\n  bob,elevated,12\n  alice,normal,2\n  carol,no lane,0" in text
    assert "unwedge bob" in text


def test_critical_exits_1(fleet, capsys):
    fleet["p"] = _pulse({"bob": {"zone": "critical", "backlog": 60}})
    code, text = _run(capsys)
    assert code == 1
    assert "critical: 1" in text


def test_no_agents_is_said_outright(fleet, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert "agents: 0" in text
    assert "0 agents seen" in text


def test_json_unchanged(fleet, capsys):
    fleet["p"] = _pulse({"alice": {"zone": "normal", "backlog": 2}})
    _, text = _run(capsys, json=True)
    assert json.loads(text)["readings"]["alice"]["backlog"] == 2


def test_human_view(fleet, monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    fleet["p"] = _pulse({"alice": {"zone": "normal", "backlog": 2}})
    _, text = _run(capsys)
    assert "pulse: test" in text
    assert "alice" in text
