"""T045 (T039b stage 1) PRE-REGISTERED ACCEPTANCE -- wake listener cuts to the WORK LANE.

Committed RED before implementation (method pre-registration). Cites
docs/library/design/20260701_t039-purpose-keyed-lanes-latches-governi_7bc135.md (Daniel gate) -- amendments A4 (tail-at-flip),
P4 (work-bell kind filter). Live receipt motivating this stage: the 2026-07-14 infinite
wake loop (lesson wake_loop_from_unconsumed_broadcast) -- five watchers drowned in 1280
legacy trace broadcasts hunting one stranded handoff. Work-lane-only watching makes that
class UNREPRESENTABLE.

Pins:
  L1 lane stream shapes: work inbox + work broadcast, per packet_spec.lane_stream_key.
  L2 S2-NEW structural: a narration broadcast (legacy bc + trace ring) NEVER reaches a
     lane-mode watcher -- no skip logic involved; the packets simply aren't there.
  L3 wake on work: a dual-written handoff wakes the lane watcher.
  L4 missed-wake hole stays closed: UNCONSUMED legacy mail at arm time wakes IMMEDIATELY
     (the arm-time pending check -- T017 lineage; tail-seeding alone would reopen it).
  L5 A4 tail-at-flip: pre-existing lane backlog with NO legacy pending never wakes a
     fresh watcher (the dual-write soak is history, not mail).
  L6 P4 filter: lane-mode SKIP set adds note/status (informational work kinds must not
     wake idle seats); the legacy SKIP set is unchanged.

Redis-backed pins use throwaway namespaces (skip if down).
Run: py -m pytest tests/test_t045_wake_cutover.py -q
"""
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from core.comm import packet_spec as ps
from core.comm.bus import Bus
from core.comm.bifrost_api import BifrostAPI


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_t045_{uuid.uuid4().hex[:8]}"


def _lane_api(ns, agent="watcher", monkeypatch=None):
    api = BifrostAPI(agent, namespace=ns)
    return api


# ------------------------------------------------------------------ L1: key shapes
def test_lane_streams_shape(monkeypatch):
    _client()
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    api = BifrostAPI("alice", namespace=ns)
    streams = api._lane_streams()
    assert streams["inbox"] == f"{ns}:work:inbox:alice"
    assert streams["bc"] == f"{ns}:work:broadcast"


# ------------------------------------------------ L2: trace flood structurally invisible
def test_lane_watcher_blind_to_trace_flood(monkeypatch):
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("noisy", c, namespace=ns, promote=False)
    watcher = BifrostAPI("alice", namespace=ns)
    assert watcher.wake_block(timeout_ms=200) == []          # arm quiet (seeds lane tails)
    for _ in range(10):
        sender.broadcast("narration", "flood")               # legacy bc + trace ring only
    got = watcher.wake_block(timeout_ms=300)
    assert got == [], "trace broadcasts must be STRUCTURALLY invisible to a lane watcher"


# ------------------------------------------------------------------ L3: wake on work
def test_lane_watcher_wakes_on_handoff(monkeypatch):
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    watcher = BifrostAPI("alice", namespace=ns)
    assert watcher.wake_block(timeout_ms=200) == []          # arm quiet first
    sender.send("alice", "handoff", "work arrives")
    got = watcher.wake_block(timeout_ms=2000)
    assert got and str(got[0].kind) == "handoff"


# ------------------------------------ L4: unconsumed legacy mail at arm wakes immediately
def test_pending_legacy_mail_wakes_fresh_watcher(monkeypatch):
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.send("alice", "handoff", "sent BEFORE the watcher armed")
    fresh = BifrostAPI("alice", namespace=ns)                # arms AFTER the send
    got = fresh.wake_block(timeout_ms=500)
    assert got and str(got[0].kind) == "handoff", \
        "unconsumed legacy mail must wake a fresh watcher (the T017 hole stays closed)"


# ---------------------------------------------------- L5: lane backlog is soak, not mail
def test_lane_backlog_alone_never_wakes(monkeypatch):
    c = _client()
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    # backlog written straight to the lane key: legacy stays EMPTY (no pending mail)
    c.xadd(f"{ns}:work:inbox:alice", {"frm": "ghost", "to": "alice", "kind": "handoff",
                                      "content": '"old soak entry"', "ts": "0", "meta": "{}",
                                      "parts": "[]"})
    fresh = BifrostAPI("alice", namespace=ns)
    got = fresh.wake_block(timeout_ms=300)
    assert got == [], "A4 tail-at-flip: pre-arm lane history must never wake"


# ------------------------------------------------------------------ L6: P4 skip set
def test_lane_skip_set_adds_note_status():
    import bifrost_wake as bw
    assert {"note", "status"} <= bw.SKIP_KINDS_LANE
    assert {"trace", "steer", "resolved", "ledger_update"} <= bw.SKIP_KINDS_LANE
    assert "note" not in bw.SKIP_KINDS, "legacy skip set unchanged (strangler discipline)"


# ------------------------------------------- L7: pending check ignores skip-kind junk
def test_pending_check_not_trapped_by_legacy_junk(monkeypatch):
    """First live soak: unconsumed legacy TRACES made pending non-empty forever -- the lane
    cursor never seeded and the watcher busy-peeked legacy for its whole deadline."""
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    noisy = Bus("noisy", c, namespace=ns, promote=False)
    for _ in range(5):
        noisy.broadcast("trace", "junk that nothing will ever consume")
    watcher = BifrostAPI("alice", namespace=ns)
    assert watcher.wake_block(timeout_ms=200) == [], "junk-only pending must seed lanes, not trap"
    assert watcher._lane_since is not None, "lane cursor must have seeded despite pending junk"
    noisy.send("alice", "handoff", "real work after the junk")
    got = watcher.wake_block(timeout_ms=2000)
    assert got and str(got[0].kind) == "handoff", "lane watching must be LIVE after junk-seed"


def test_pending_skip_parity_with_lane_skip_set():
    from core.comm import bifrost_api
    import bifrost_wake as bw
    assert bifrost_api.PENDING_SKIP_KINDS == bw.SKIP_KINDS_LANE, \
        "drift here either traps the pending check on junk or wakes idle seats on noise"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
