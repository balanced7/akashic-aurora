"""flightdeck pins — cockpit one-pager (deepseek, LIFEWORKERS, 2026-07-21).

  P1  fleet mode renders every known agent in compact rows
  P2  single-agent mode includes unwedge detail
  P3  pulse zone column reflects pressure zone per agent
  P4  lane column shows W16 age/depth/straggler
  P5  recent commits section present
  P6  JSON mode outputs structured sections
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.doctor import flightdeck, format_flightdeck


def _setup_locks(monkeypatch):
    """Flightdeck does `from core.comm import locks` at call time."""
    class _MockLM:
        def __init__(self, agent):
            self._agent = agent
        def list_held(self):
            return ["docs/WISHLIST.md"] if self._agent == "claude" else []
    # Patch the CONSTRUCTOR so LockManager(agent) returns our mock
    monkeypatch.setattr("core.comm.locks.LockManager", _MockLM)


def _setup_commits(monkeypatch):
    class _R:
        stdout = "abc1234 ship W16 lane-health\n5678def build pulse verb\n"
        returncode = 0
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _R())


@pytest.fixture()
def patched(monkeypatch):
    monkeypatch.setattr("core.comm.doctor.examine_fleet", lambda **kw: {
        "summary": "doctor: 1 page, 0 banner, 2 dashboard across 2 agent(s)",
        "agents": ["claude", "deepseek"],
        "findings": [
            {"agent": "claude", "state": "stalled_consumer", "grade": "page",
             "line": "claude: STALLED", "drill": "sync"},
            {"agent": "deepseek", "state": "lane_health", "grade": "dashboard",
             "line": "deepseek: lane cursor", "drill": "mailbox"},
        ],
        "pages": [{"agent": "claude", "state": "stalled_consumer", "grade": "page",
                    "line": "STALLED", "drill": "sync"}],
    })
    monkeypatch.setattr("core.comm.doctor.pulse", lambda agents=None: {
        "summary": "pulse: 1 elevated (claude), 1 normal",
        "zones": {"critical": [], "elevated": ["claude"],
                  "normal": ["deepseek"], "absent": []},
        "readings": {"claude": {"backlog": 12, "zone": "elevated", "has_lane": True},
                     "deepseek": {"backlog": 3, "zone": "normal", "has_lane": True}},
    })
    monkeypatch.setattr("core.comm.doctor._probe_lane_health", lambda a: {
        "claude": {"age_s": 1800, "depth": 12, "straggler": 0},
        "deepseek": {"age_s": 120, "depth": 3, "straggler": 0},
    }.get(a))
    monkeypatch.setattr("core.comm.doctor.unwedge", lambda a: {
        "agent": a, "status": "stalled" if a == "claude" else "healthy",
        "verdict": f"{a}: STALLED" if a == "claude" else f"{a}: HEALTHY",
        "recommendation": "sync" if a == "claude" else "none",
        "evidence": {"findings": [
            {"grade": "page", "state": "stalled", "line": "STALLED"} if a == "claude"
            else {"grade": "dashboard", "state": "ok", "line": "ok"}
        ], "runner_status": "live"},
    })
    _setup_locks(monkeypatch)
    _setup_commits(monkeypatch)


def test_p1_fleet_mode_renders_all_agents(patched):
    fd = flightdeck()
    assert len(fd["agents"]) == 2 and fd["fleet"] is True


def test_p2_single_agent_includes_unwedge(patched):
    fd = flightdeck(agent="claude")
    assert fd["fleet"] is False
    assert fd["sections"]["unwedge"]["status"] == "stalled"


def test_p3_pulse_zones_in_output(patched):
    out = format_flightdeck(flightdeck())
    assert "elevated" in out and "normal" in out


def test_p4_lane_column_shows_data(patched):
    out = format_flightdeck(flightdeck())
    assert "age 1800s" in out or "d=12" in out


def test_p5_commits_section(patched):
    out = format_flightdeck(flightdeck())
    assert "recent commits" in out.lower()


def test_p6_json_output(patched):
    out = format_flightdeck(flightdeck(), json_mode=True)
    assert '"fleet"' in out and '"sections"' in out
