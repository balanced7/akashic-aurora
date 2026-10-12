"""Pins for `doctor` after the AXI conversion: findings, services, the quiet fleet, --json, human.

Offline: the fleet, services, ACL and link probes are stubbed (the H6 precedent in
test_t108_s4_reaper_hardening.py), so no store is read.

Run: uv run pytest tests/test_axi_doctor.py -q
"""

import json
from types import SimpleNamespace

import pytest

import agent_cli
from core.comm import doctor

FINDING = {
    "agent": "carol",
    "state": "ghost",
    "grade": "dashboard",
    "line": "carol: OFFLINE -- 1 unread but the agent is GONE",
    "drill": "aurora bifrost-skip-to-now carol --by <you> --reason 'ghost mail'",
}
SERVICES = [
    {"agent": "redis", "state": "service_live", "grade": "dashboard", "line": "service redis: LIVE -- bus backend",
     "drill": ""},
    {"agent": "daemon", "state": "service_down", "grade": "banner", "line": "service daemon: DOWN -- no live daemon",
     "drill": "start it"},
]  # fmt: skip


@pytest.fixture
def fleet(monkeypatch):
    state = {"findings": [], "agents": []}

    def examine_fleet(agents, page_notes=False):
        n = len(state["findings"])
        return {
            "agents": state["agents"],
            "findings": state["findings"],
            "summary": f"doctor: {n} finding(s) across {len(state['agents'])} agent(s) | watches 0/2",
        }

    monkeypatch.setattr(doctor, "examine_fleet", examine_fleet)
    monkeypatch.setattr(doctor, "known_agents", list)
    monkeypatch.setattr(doctor, "examine_services", lambda: SERVICES)
    from core.trust import registry

    monkeypatch.setattr(registry, "acl_status", lambda: {"floor_in_force": False})
    monkeypatch.setattr(registry, "expiring_grants", lambda within_h=72.0: [])
    from core.link import health

    monkeypatch.setattr(health, "health", lambda: {"in_use": False, "problems": []})
    import core.recall.at_action as aa

    monkeypatch.setattr(aa, "injections_by_family", lambda hours: {"total": 0, "families": {}})
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return state


def _run(capsys, **kw):
    ns = SimpleNamespace(agents=None, page=False, progress=False, json=False, deploy=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_doctor(ns)
    return code, capsys.readouterr().out


def test_findings_and_services_as_rows(fleet, capsys):
    fleet["agents"], fleet["findings"] = ["alice", "carol"], [FINDING]
    code, text = _run(capsys)
    assert code == 0
    assert "findings[1]{grade,agent,line,drill}:" in text
    assert "dashboard,carol," in text
    assert "services[2]{service,state,detail,start}:" in text
    assert "redis,live,bus backend,null" in text
    assert "daemon,down,no live daemon,start it" in text
    assert "unwedge carol" in text  # the drill-down names the agent with the finding


def test_quiet_fleet_says_zero_and_gives_no_hint(fleet, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert "findings: 0 findings" in text
    assert "help[" not in text  # a healthy fleet answers itself


def test_json_is_the_report(fleet, capsys):
    fleet["findings"] = [FINDING]
    _, text = _run(capsys, json=True)
    rep = json.loads(text)
    assert rep["findings"][0]["agent"] == "carol"
    assert rep["services"][0]["agent"] == "redis"


def test_human_view(fleet, monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "160")
    fleet["agents"], fleet["findings"] = ["carol"], [FINDING]
    _, text = _run(capsys)
    assert "doctor: 1 finding(s)" in text
    assert "dashboard" in text
    assert "drill:" in text
    assert "Services" in text
