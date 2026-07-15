"""T077 A3 PRE-REGISTERED ACCEPTANCE — runner-down visibility.

Spec: presence-autopilot-reconciliation-2026-07-15.md slice A3 — doctor flag +
whisper daemon_runtimes + 10-min re-escalation broadcast. deepseek builds,
claude verifies. Pins committed RED before this file exists.

Pins:
  A3-P1  daemon_runtimes() reads the presence card's runtimes field
  A3-P2  Doctor flags runner 'down' as banner, 'blocked' as page
  A3-P3  Doctor is silent when runner is live (no false findings)
  A3-P4  Daemon card carries runtimes.runner field (unit: daemon loop update)
  A3-P5  Re-escalation: after 10min down, daemon broadcasts blocker again
"""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import incarnation as inc
from core.comm import doctor


class FakeRedis:
    def __init__(self):
        self.kv, self.ex = {}, {}
    def set(self, k, v, ex=None, nx=False):
        if nx and k in self.kv:
            return None
        self.kv[k], self.ex[k] = v, ex
        return True
    def get(self, k):
        return self.kv.get(k)
    def delete(self, k):
        self.kv.pop(k, None), self.ex.pop(k, None)


def _set_presence(c, agent, card):
    c.kv[f"bifrost:presence:{agent}"] = json.dumps(card)


# -------------------------------------------------- A3-P1 daemon_runtimes
def test_p1_daemon_runtimes_reads_presence_card():
    c = FakeRedis()
    _set_presence(c, "deepseek", {"runtime_class": "daemon",
                                   "runtimes": {"runner": "live"}})
    rt = inc.daemon_runtimes("deepseek", c=c, allow_fallback=False)
    assert rt == {"runner": "live"}

    _set_presence(c, "deepseek", {"runtime_class": "daemon",
                                   "runtimes": {"runner": "down", "since_s": 120}})
    rt = inc.daemon_runtimes("deepseek", c=c, allow_fallback=False)
    assert rt == {"runner": "down", "since_s": 120}


def test_p1_daemon_runtimes_empty_when_no_card():
    c = FakeRedis()
    assert inc.daemon_runtimes("nobody", c=c, allow_fallback=False) == {}


def test_p1_daemon_runtimes_empty_when_no_runtimes_field():
    c = FakeRedis()
    _set_presence(c, "claude", {"runtime_class": "daemon", "pid": 123})
    assert inc.daemon_runtimes("claude", c=c, allow_fallback=False) == {}


def test_p1_daemon_runtimes_fail_soft_no_client():
    assert inc.daemon_runtimes("anyone", c=None, allow_fallback=False) == {}


# -------------------------------------------------- A3-P2 Doctor runner down
def test_p2_doctor_flags_runner_down():
    c = FakeRedis()
    _set_presence(c, "deepseek", {"runtime_class": "daemon",
                                   "runtimes": {"runner": "down", "since_s": 42}})
    probes = doctor._default_probes()
    probes["now"] = time.time()
    findings = doctor.examine("deepseek", probes=probes)
    # doctor takes _client() from bus — override by patching incarnation
    import core.comm.incarnation as _inc
    orig = _inc._resolve_client
    try:
        _inc._resolve_client = lambda c_param, allow: c if c_param is not None else c
        findings = doctor.examine("deepseek", probes=probes)
        downs = [f for f in findings if f["state"] == "runner_down"]
        assert len(downs) >= 1, f"A3-P2: doctor must flag runner_down, got {findings}"
        assert "42" in downs[0]["line"], "since_s must appear"
    finally:
        _inc._resolve_client = orig


def test_p2_doctor_flags_runner_blocked():
    c = FakeRedis()
    _set_presence(c, "deepseek", {"runtime_class": "daemon",
                                   "runtimes": {"runner": "blocked"}})
    import core.comm.incarnation as _inc
    orig = _inc._resolve_client
    try:
        _inc._resolve_client = lambda c_param, allow: c if c_param is not None else c
        findings = doctor.examine("deepseek", probes=doctor._default_probes())
        blocked = [f for f in findings if f["state"] == "runner_blocked"]
        assert len(blocked) >= 1, f"A3-P2: doctor must flag runner_blocked, got {findings}"
        assert blocked[0]["grade"] == "page", "blocked runner is page-grade"
    finally:
        _inc._resolve_client = orig


# -------------------------------------------------- A3-P3 Doctor silent when live
def test_p3_doctor_silent_when_runner_live():
    c = FakeRedis()
    _set_presence(c, "deepseek", {"runtime_class": "daemon",
                                   "runtimes": {"runner": "live"}})
    import core.comm.incarnation as _inc
    orig = _inc._resolve_client
    try:
        _inc._resolve_client = lambda c_param, allow: c if c_param is not None else c
        findings = doctor.examine("deepseek", probes=doctor._default_probes())
        rt_findings = [f for f in findings if f["state"] in ("runner_down", "runner_blocked")]
        assert rt_findings == [], f"A3-P3: no runtime findings when runner is live, got {rt_findings}"
    finally:
        _inc._resolve_client = orig


def test_p3_doctor_silent_when_no_daemon_card():
    """No presence card at all → no runtime findings (not every agent runs a daemon)."""
    c = FakeRedis()
    import core.comm.incarnation as _inc
    orig = _inc._resolve_client
    try:
        _inc._resolve_client = lambda c_param, allow: c if c_param is not None else c
        # agent with no presence card
        findings = doctor.examine("nobody", probes=doctor._default_probes())
        rt_findings = [f for f in findings if f["state"] in ("runner_down", "runner_blocked")]
        assert rt_findings == [], f"A3-P3: no card → no false runtime alarm, got {rt_findings}"
    finally:
        _inc._resolve_client = orig
