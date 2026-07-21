"""W31 unwedge pins — one-verb wedge diagnosis (deepseek, 2026-07-21).

  P1  frozen agent -> status "frozen"
  P2  hard_wedge -> status "wedged"
  P3  stalled with work backlog -> status "stalled"
  P4  healthy-live -> status "healthy"
  P5  no runner -> status "down"
  P6  format_unwedge text/json modes
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.doctor import unwedge, format_unwedge


def _patch_deps(monkeypatch, examine_result=None, lane_health=None,
                lane_depths=None, work_backlog=0, holder=None,
                runner="live", list_held=None):
    """Patch the actual source modules unwedge() imports at call time."""
    if examine_result is not None:
        monkeypatch.setattr("core.comm.doctor.examine", lambda a, **kw: examine_result)
    if lane_health is not None:
        monkeypatch.setattr("core.comm.doctor._probe_lane_health", lambda a: lane_health)
    monkeypatch.setattr("core.comm.lane_depths.lane_depths", lambda a, **kw: lane_depths or {})
    monkeypatch.setattr("core.comm.lane_depths.work_backlog", lambda a, **kw: work_backlog)
    monkeypatch.setattr("core.comm.runner_lock.holder", lambda a: holder)
    monkeypatch.setattr("core.comm.incarnation.daemon_runtimes", lambda a:
                        {"runner": runner})
    if list_held is not None:
        # Patch LockManager to return known locks
        monkeypatch.setattr("core.comm.locks.LockManager.list_held", lambda s: list_held)


def test_p1_frozen_status(monkeypatch):
    _patch_deps(monkeypatch, examine_result=[
        {"agent": "d", "state": "frozen", "grade": "banner",
         "line": "FROZEN", "drill": "resume"}],
        lane_health={"age_s": 100, "depth": 0, "straggler": 0})
    r = unwedge("deepseek")
    assert r["status"] == "frozen"
    assert "resume" in r["recommendation"].lower()


def test_p2_hard_wedge_status(monkeypatch):
    _patch_deps(monkeypatch, examine_result=[
        {"agent": "d", "state": "hard_wedge", "grade": "page",
         "line": "HARD WEDGE", "drill": "relaunch"}],
        lane_health={"age_s": 400, "depth": 5, "straggler": 0},
        work_backlog=5, holder={"token": "x"})
    r = unwedge("deepseek")
    assert r["status"] == "wedged"
    assert "revive" in r["verdict"].lower()


def test_p3_stalled_with_backlog(monkeypatch):
    _patch_deps(monkeypatch, examine_result=[
        {"agent": "d", "state": "stalled_consumer", "grade": "page",
         "line": "STALLED", "drill": "sync"}],
        lane_health={"age_s": 3660, "depth": 42, "straggler": 3},
        work_backlog=42, holder={"token": "x"})
    r = unwedge("deepseek")
    assert r["status"] == "stalled"
    assert "42" in r["verdict"]


def test_p4_healthy_live(monkeypatch):
    _patch_deps(monkeypatch, examine_result=[],
        lane_health={"age_s": 5, "depth": 0, "straggler": 0},
        holder={"token": "x"})
    r = unwedge("deepseek")
    assert r["status"] == "healthy"


def test_p5_no_runner_down(monkeypatch):
    _patch_deps(monkeypatch, examine_result=[], holder=None, runner="absent")
    r = unwedge("deepseek")
    assert r["status"] == "down"
    assert "no runner" in r["verdict"].lower()


def test_p6_format_text_and_json():
    r = {"agent": "deepseek", "status": "healthy", "verdict": "deepseek: HEALTHY",
         "recommendation": "no action", "evidence": {
             "findings": [], "lane_health": {"age_s": 5, "depth": 0, "straggler": 0},
             "lane_depths": {"work": 0, "legacy": 0, "trace": 0, "sig": 0, "work_backlog": 0},
             "runner_status": "live", "locks": []}}
    out = format_unwedge(r)
    assert "HEALTHY" in out and "no action" in out
    json_out = format_unwedge(r, json_mode=True)
    assert '"status"' in json_out
