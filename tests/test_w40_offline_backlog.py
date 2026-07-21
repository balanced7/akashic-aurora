"""W40 pins — doctor tri-state: absent vs stalled (deepseek, 2026-07-21).

Live receipt: census (a retired one-off task-agent) paged as STALLED CONSUMER
with leftover backlog and no live process. flightdeck rendered it "absent" in
the pulse column; doctor should tri-state:

  LIVE + idle + backlog past hysteresis = stalled_consumer PAGE  (unchanged)
  ABSENT (no worklive) + backlog         = offline_backlog DASHBOARD (never a page)
  LIVE + idle + backlog pre-hysteresis   = stalled_consumer DASHBOARD (unchanged)

  P1  absent agent with backlog -> offline_backlog dashboard, NOT page
  P2  present+idle agent with backlog past hysteresis -> stalled_consumer page
  P3  present+idle agent with backlog pre-hysteresis -> stalled_consumer dashboard
  P4  absent agent with NO backlog -> no finding
  P5  live census: retired ghost reads offline, not stalled
"""
import time
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.doctor import examine

_now = time.time()


def _probes(**over):
    base = dict(
        worklive=lambda a: {"phase": "idle", "detail": "", "turn": 3,
                            "since_ts": _now - 5, "beat_ts": _now - 1},
        progress=lambda a: None,
        backlog=lambda a: 0,
        stalled_since=lambda a, present: None,
        halted=lambda a: None,
        lane_health=lambda a: None,
        now=_now,
    )
    base.update(over)
    return base


def test_p1_absent_agent_backlog_is_offline_dashboard():
    """An agent with NO worklive record (presence TTL'd out) but leftover backlog
    gets a dashboard offline_backlog — never a page."""
    f = examine("census", probes=_probes(
        worklive=lambda a: None,       # absent — worklive TTL'd
        backlog=lambda a: 7,           # ghost mail
    ))
    pages = [x for x in f if x["grade"] == "page"]
    offline = [x for x in f if x["state"] == "offline_backlog"]
    assert len(pages) == 0, f"absent agent must never page; got: {pages}"
    assert len(offline) == 1
    assert offline[0]["grade"] == "dashboard"
    assert "GONE" in offline[0]["line"] or "OFFLINE" in offline[0]["line"]


def test_p2_present_idle_past_hysteresis_still_pages():
    """A LIVE agent with worklive, idle, and backlog past hysteresis STILL pages.
    The W40 gate must not false-negative a real stall."""
    f = examine("claude", probes=_probes(
        worklive=lambda a: {"phase": "idle", "detail": "", "turn": 3,
                            "since_ts": _now - 5, "beat_ts": _now - 1},
        backlog=lambda a: 5,
        stalled_since=lambda a, present: _now - 400,  # stalled for 400s
    ))
    pages = [x for x in f if x["state"] == "stalled_consumer" and x["grade"] == "page"]
    assert len(pages) == 1, "live idle agent past hysteresis must still page"


def test_p3_present_idle_pre_hysteresis_dashboards():
    """A LIVE agent with backlog but NOT past hysteresis gets dashboard, not page."""
    f = examine("deepseek", probes=_probes(
        worklive=lambda a: {"phase": "idle", "detail": "", "turn": 3,
                            "since_ts": _now - 5, "beat_ts": _now - 1},
        backlog=lambda a: 3,
        stalled_since=lambda a, present: _now - 30,   # only 30s
    ))
    pages = [x for x in f if x["state"] == "stalled_consumer" and x["grade"] == "page"]
    dash = [x for x in f if x["state"] == "stalled_consumer" and x["grade"] == "dashboard"]
    assert len(pages) == 0
    assert len(dash) == 1


def test_p4_absent_no_backlog_no_finding():
    """An absent agent with no backlog produces no finding — nothing to say."""
    f = examine("retired", probes=_probes(
        worklive=lambda a: None,
        backlog=lambda a: 0,
    ))
    offline = [x for x in f if x["state"] == "offline_backlog"]
    assert len(offline) == 0


def test_p5_live_census_offline_not_stalled():
    """The exact census shape: absent worklive + 7 backlog = offline, not stalled."""
    f = examine("census", probes=_probes(
        worklive=lambda a: None,
        backlog=lambda a: 7,
    ))
    stalled = [x for x in f if x["state"] == "stalled_consumer"]
    offline = [x for x in f if x["state"] == "offline_backlog"]
    assert len(stalled) == 0
    assert len(offline) == 1
