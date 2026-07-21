"""W25 pulse pins — LIFEWORKERS pressure-map (deepseek, 2026-07-21).

  P1  backlog >= 50 -> critical zone
  P2  backlog >= 10 -> elevated zone
  P3  backlog 0-9 -> normal zone
  P4  legacy-only (all-zero lane) -> absent zone
  P5  fleet summary with critical agent gets CRITICAL tag
  P6  json output includes zones + readings
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.doctor import pulse, format_pulse


@pytest.fixture()
def patched(monkeypatch):
    monkeypatch.setattr("core.comm.doctor.known_agents",
                        lambda: ["stormy", "busy", "calm", "legacy"])

    def _read_lane(self):
        a = self.agent_id
        if a == "legacy":
            return {"inbox": "0", "bc": "0", "sig_inbox": "0",
                    "sig_bc": "0", "shadow_inbox": "0", "shadow_bc": "0"}
        return {"inbox": "100-5", "bc": "0", "sig_inbox": "0",
                "sig_bc": "0", "shadow_inbox": "100-3", "shadow_bc": "0"}
    monkeypatch.setattr("core.comm.bus.Bus.read_lane_cursor", _read_lane)

    def _wb(agent, **kw):
        return {"stormy": 55, "busy": 12, "calm": 3, "legacy": 0}.get(agent, 0)
    monkeypatch.setattr("core.comm.lane_depths.work_backlog", _wb)

    monkeypatch.setattr("core.comm.bus.Bus.online", True)
    monkeypatch.setattr("core.comm.bus.Bus.__init__",
                        lambda s, a, **kw: setattr(s, "agent_id", a) or None)


def test_p1_critical(patched):
    p = pulse(["stormy"])
    assert "stormy" in p["zones"]["critical"]
    assert p["readings"]["stormy"]["backlog"] == 55


def test_p2_elevated(patched):
    p = pulse(["busy"])
    assert "busy" in p["zones"]["elevated"]


def test_p3_normal(patched):
    p = pulse(["calm"])
    assert "calm" in p["zones"]["normal"]


def test_p4_absent(patched):
    p = pulse(["legacy"])
    assert "legacy" in p["zones"]["absent"]
    assert not p["readings"]["legacy"]["has_lane"]


def test_p5_fleet_summary(patched):
    p = pulse()
    assert "CRITICAL" in p["summary"]
    assert "stormy" in p["summary"]


def test_p6_json(patched):
    out = format_pulse(pulse(), json_mode=True)
    assert '"critical"' in out and '"stormy"' in out
