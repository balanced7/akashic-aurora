"""W16 pins — lane-cursor health in doctor (deepseek, 2026-07-21).

Per-agent lane cursor age + depth + straggler count as doctor dashboard rows.
Uses W43 effective_cursor() as the building block.

  P1  lane-mode consumer: _probe_lane_health returns age_s, depth, straggler
  P2  legacy-only consumer (all-zero lane hash): returns None (no row)
  P3  a drained lane-mode agent: age shows recent, depth=0, straggler=0
  P4  a lagged lane: straggler counts legacy messages the shadow hasn't reached
  P5  Redis down: None (fail-open, no crash)
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ns_env(monkeypatch):
    ns = f"t-w16-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    return ns


def _online():
    from core.comm.bus import Bus
    return Bus("t-w16").online


@pytest.fixture()
def agents(monkeypatch):
    ns = _ns_env(monkeypatch)
    return ns


def test_p1_lane_mode_consumer_returns_health(monkeypatch, agents):
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    from core.comm.doctor import _probe_lane_health
    agent = f"t-w16-lane-{uuid.uuid4().hex[:6]}"
    b = Bus(agent)
    # Simulate a lane-mode consumer that advanced its lane cursor
    ts = int(time.time() * 1000) - 5000  # 5s ago
    b._client.hset(b.lane_cursor_key(), mapping={
        "inbox": f"{ts}-3",
        "bc": f"{ts}-1",
        "shadow_inbox": f"{ts}-2",
        "shadow_bc": "0",
        "sig_inbox": "0",
        "sig_bc": "0",
    })
    lh = _probe_lane_health(agent)
    assert lh is not None, "lane-mode consumer must return health"
    assert lh["age_s"] is not None and abs(lh["age_s"] - 5) < 5
    assert lh["depth"] >= 0
    assert lh["straggler"] >= 0


def test_p2_legacy_only_returns_none(monkeypatch, agents):
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    from core.comm.doctor import _probe_lane_health
    agent = f"t-w16-legacy-{uuid.uuid4().hex[:6]}"
    b = Bus(agent)
    # Legacy consumer has all-zero lane hash (virgin, never flipped)
    lh = _probe_lane_health(agent)
    assert lh is None, "legacy-only consumer must not show lane health row"


def test_p3_drained_lane_shows_healthy(monkeypatch, agents):
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    from core.comm.doctor import _probe_lane_health
    agent = f"t-w16-drained-{uuid.uuid4().hex[:6]}"
    b = Bus(agent)
    # Send one msg then advance lane to tail (fully drained)
    peer = Bus(f"{agent}-peer")
    peer.send(agent, "question", "already consumed")
    entries = b._client.xrevrange(f"{b.ns}:work:inbox:{agent}", count=1)
    if entries:
        tail = entries[0][0]
        ts = int(time.time() * 1000)
        b._client.hset(b.lane_cursor_key(), mapping={
            "inbox": str(tail),
            "bc": "0",
            "shadow_inbox": str(tail),
            "shadow_bc": "0",
            "sig_inbox": "0",
            "sig_bc": "0",
        })
    else:
        ts = int(time.time() * 1000)
        b._client.hset(b.lane_cursor_key(), mapping={
            "inbox": f"{ts}-1",
            "bc": "0",
            "shadow_inbox": f"{ts}-1",
            "shadow_bc": "0",
            "sig_inbox": "0",
            "sig_bc": "0",
        })
    lh = _probe_lane_health(agent)
    assert lh is not None
    assert lh["depth"] == 0, "drained lane: zero work backlog"
    assert lh["straggler"] == 0, "drained lane: zero stragglers"


def test_p4_lagged_lane_counts_stragglers(monkeypatch, agents):
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    from core.comm.doctor import _probe_lane_health
    agent = f"t-w16-lag-{uuid.uuid4().hex[:6]}"
    b = Bus(agent)
    # Seed a lane cursor that's BEHIND real mail
    # The lane inbox position is at a known old point
    old = int((time.time() - 3600) * 1000)  # 1h old
    b._client.hset(b.lane_cursor_key(), mapping={
        "inbox": f"{old}-0",
        "bc": "0",
        "shadow_inbox": f"{old}-0",
        "shadow_bc": "0",
        "sig_inbox": "0",
        "sig_bc": "0",
    })
    # Set the shared cursor to catch up through the shadow
    b._client.hset(b._cursor_key(), mapping={
        "inbox": f"{old}-0",
        "bc": "0",
    })
    # Send fresh messages that are beyond the shadow
    peer = Bus(f"{agent}-peer")
    for _ in range(3):
        peer.send(agent, "question", "fresh mail")
    lh = _probe_lane_health(agent)
    assert lh is not None
    assert lh["depth"] > 0 or lh["straggler"] > 0, "lagged consumer must show backlog"


def test_p5_redis_down_returns_none(monkeypatch):
    # Simulate Redis down: Bus.online returns False
    monkeypatch.setattr("core.comm.bus.Bus.online", False)
    from core.comm.doctor import _probe_lane_health
    assert _probe_lane_health("t-w16-down") is None
