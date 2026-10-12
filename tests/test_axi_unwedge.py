"""Pins for `unwedge` after the AXI conversion: the verdict, the evidence, exit codes, human view.

Run: uv run pytest tests/test_axi_unwedge.py -q
"""

import argparse
import json

import pytest

import agent_cli
from core.comm import doctor


def _verdict(status="stalled", **ev):
    evidence = {"findings": [], "lane_health": None, "lane_depths": {}, "runner_status": "live", "locks": []}
    evidence.update(ev)
    return {
        "agent": "carol",
        "status": status,
        "verdict": f"carol: {status.upper()}",
        "recommendation": "sync: aurora bifrost-sync carol",
        "evidence": evidence,
    }


@pytest.fixture
def diag(monkeypatch):
    holder = {"r": _verdict()}
    monkeypatch.setattr(doctor, "unwedge", lambda agent: holder["r"])
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, **kw):
    ns = argparse.Namespace(agent="carol", json=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_unwedge(ns)
    return code, capsys.readouterr().out


def test_stuck_agent_is_status_verdict_evidence_exit_1(diag, capsys):
    page = {"grade": "page", "state": "lane_stall", "line": "carol lane stalled", "drill": "aurora mailbox"}
    diag["r"] = _verdict(findings=[page], lane_health={"age_s": 120.4, "depth": 7}, lane_depths={"work": 7, "sig": 0})
    code, text = _run(capsys)
    assert code == 1
    assert text.startswith("agent: carol\nstatus: stalled\n")
    assert "page_findings[1]{state,line,drill}:" in text
    assert "lane_cursor:\n  age_s: 120\n  depth: 7" in text
    assert "work: 7" in text
    assert "sig:" not in text  # zero depths say nothing


def test_healthy_agent_exits_0_with_no_evidence_noise(diag, capsys):
    diag["r"] = _verdict(status="healthy")
    code, text = _run(capsys)
    assert code == 0
    assert "page_findings" not in text
    assert "runner: live" in text


def test_json_unchanged(diag, capsys):
    code, text = _run(capsys, json=True)
    assert code == 1
    assert json.loads(text)["status"] == "stalled"


def test_human_view(diag, monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys)
    assert "carol: STALLED" in text
    assert "do: sync: aurora bifrost-sync carol" in text
