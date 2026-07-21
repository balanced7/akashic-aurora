"""W43 pins — unread gauges become lane-aware (kimi's cursor-divergence find).

Live receipts 2026-07-21: doctor paged kimi 'STALLED CONSUMER -- 28 unread' over mail
the seat had drained; claude's session-hook line said '8 unread' straight through
consumes; root cause measured live -- lane consume advances the LANE hash while the
SHARED cursor freezes, and every gauge compared the shared cursor alone.

The fix: Bus.effective_cursor() = per-field max(shared, lane SHADOW fields) -- the
shadow IS work_drain's legacy-stream position. Gauges (doctor backlog, Bus.pending)
derive from it. Hypothesis (a) from kimi's W43 confirmed; (b) ruled out for claude.

  P1  legacy-only agent (all-zero lane hash): effective == shared, byte-identical
  P2  lane-ahead agent: effective rides the shadow fields
  P3  doctor backlog reads 0 for a lane-drained agent whose shared cursor lags
  P4  a REAL unread (beyond both cursors) still counts -- no false negatives
  P5  pending() honors per-stream floors (direct vs broadcast never cross-compare)
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ns_env(monkeypatch):
    ns = f"t-w43-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    return ns


def _online():
    from core.comm.bus import Bus
    return Bus("t-w43").online


def test_p1_legacy_only_byte_identical(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    b = Bus(f"t-w43-leg-{uuid.uuid4().hex[:6]}")
    assert b.effective_cursor() == b.cursor(), \
        "all-zero lane hash -> effective is exactly the shared cursor"


def test_p2_lane_shadow_wins_when_ahead(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    b = Bus(f"t-w43-lane-{uuid.uuid4().hex[:6]}")
    ahead = f"{int(time.time() * 1000)}-5"
    b._client.hset(b.lane_cursor_key(), "shadow_inbox", ahead)
    eff = b.effective_cursor()
    assert eff["inbox"] == ahead, "shadow ahead of shared -> effective rides the shadow"


def test_p3_doctor_backlog_zero_for_lane_drained(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    from core.comm.doctor import _probe_backlog
    agent = f"t-w43-drained-{uuid.uuid4().hex[:6]}"
    b = Bus(agent)
    Bus(f"{agent}-peer").send(agent, "question", "already drained via the lane")
    tail = b._client.xrevrange(b._inbox_key(agent), count=1)[0][0]
    # simulate the lane-mode drain: shadow advanced to tail, shared cursor untouched
    b._client.hset(b.lane_cursor_key(), "shadow_inbox", str(tail))
    assert _probe_backlog(agent) == 0, \
        "lane-drained mail never pages as a stalled backlog (the W40/W43 lie)"


def test_p4_real_unread_still_counts(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    from core.comm.doctor import _probe_backlog
    agent = f"t-w43-real-{uuid.uuid4().hex[:6]}"
    Bus(f"{agent}-peer").send(agent, "question", "genuinely unread")
    assert _probe_backlog(agent) == 1, "mail beyond BOTH cursors still counts"


def test_p5_pending_per_stream_floors(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    agent = f"t-w43-mix-{uuid.uuid4().hex[:6]}"
    b = Bus(agent)
    peer = Bus(f"{agent}-peer")
    peer.send(agent, "question", "direct drained")
    peer.broadcast("note", "broadcast fresh")
    tail = b._client.xrevrange(b._inbox_key(agent), count=1)[0][0]
    b._client.hset(b.lane_cursor_key(), "shadow_inbox", str(tail))
    # direct is lane-drained; the broadcast is genuinely unread
    assert b.pending() == 1, \
        "per-stream floors: drained direct excluded, fresh broadcast still counts"
