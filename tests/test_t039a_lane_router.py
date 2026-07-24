"""T044 (T039a) PRE-REGISTERED ACCEPTANCE -- lane router + dual-write + trace exemption.

Committed BEFORE implementation (method-baseline pre-registration; T031 rule practiced).
Cites docs/library/design/20260701_t039-purpose-keyed-lanes-latches-governi_7bc135.md (Daniel gate 2026-07-13) and the LAW packet
spec (docs/library/design/20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94.md R5/R6 + amend E).

Bars:
  B1 per-kind router pins: every control kind -> sig, NEVER trace; unknown kind -> NO lane
     (legacy-only, loud) until cutover activates the spec's full refusal.
  B2 dual-write: send() writes legacy inbox AND the work-lane inbox; the legacy entry is
     field-identical; the bell rings ONCE (lane bells activate at T039b).
  B3 kill-switch: BIFROST_LANES_DUAL_WRITE=0 -> lane keys untouched, legacy unchanged.
  B4 trace exemption (R5 + amend E): trace-lane copy UNSTAMPED by default, every Nth stamped
     via the global spot counter; the legacy copy stays ALWAYS stamped.
  B5 key shapes: lane dimension inserted before the topology suffix.
  B6 reader census (A3): the governing doc names every live stream reader.

Redis-backed pins use the real Redis in a throwaway namespace (skip if down); pure pins
need no Redis.  Run: py -m pytest tests/test_t039a_lane_router.py -q
"""
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import packet_spec as ps
from core.comm.bus import Bus

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_t039a_{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------- B1: router table pins
CONTROL_KINDS = ["halt", "interrupt", "pause", "nudge", "steer"]
WORK_KINDS = ["handoff", "reply", "request", "question", "chat", "inform", "note",
              "answer", "dispatch", "status", "completion"]
TRACE_KINDS = ["trace", "thinking", "tool", "narration", "ledger_update", "resolved", "hint"]


@pytest.mark.parametrize("kind", CONTROL_KINDS)
def test_control_kind_routes_sig_never_trace(kind):
    lane = ps.lane_for(kind)
    assert lane == "sig", f"{kind} must ride sig (got {lane})"
    assert lane != "trace", f"a lost {kind} is the worst-case failure; NEVER trace"


@pytest.mark.parametrize("kind", WORK_KINDS)
def test_work_kind_routes_work(kind):
    assert ps.lane_for(kind) == "work"


@pytest.mark.parametrize("kind", TRACE_KINDS)
def test_trace_kind_routes_trace(kind):
    assert ps.lane_for(kind) == "trace"


def test_unknown_kind_has_no_lane_strangler_phase():
    """Until cutover an unmapped kind must NOT break its sender: no lane, legacy still flows.
    Full REFUSAL (spec end-state) activates at T039b/d once the soak proves the table."""
    assert ps.lane_for("zz_unmapped_kind_zz") is None


# ----------------------------------------------------- B2/B3: dual-write + kill-switch
def test_dual_write_work_lane_and_legacy_identical(monkeypatch):
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    ns = _ns()
    bus = Bus("agent-a", c, namespace=ns, promote=False)
    bus.send("agent-b", "handoff", "dual-write probe")
    legacy = c.xrevrange(f"{ns}:inbox:agent-b", count=1)
    lane = c.xrevrange(f"{ns}:work:inbox:agent-b", count=1)
    assert legacy and lane, "both streams must receive the packet"
    lf, wf = dict(legacy[0][1]), dict(lane[0][1])
    for k in ("frm", "to", "kind", "content", "len", "sha"):
        if k in lf or k in wf:
            assert lf.get(k) == wf.get(k), f"field {k} differs legacy vs lane"


def test_dual_write_killswitch_off_leaves_lanes_untouched(monkeypatch):
    """C6-7: BIFROST_LANES_DUAL_WRITE=0 disables lane writes in _emit() -- the same
    kill-switch semantics, now applied to the primary path instead of the advisory mirror."""
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "0")
    ns = _ns()
    bus = Bus("agent-a", c, namespace=ns, promote=False)
    bus.send("agent-c", "handoff", "killswitch probe")
    assert c.xrevrange(f"{ns}:inbox:agent-c", count=1), "legacy must flow"
    assert not c.exists(f"{ns}:work:inbox:agent-c"), "lane must be untouched when kill-switch is OFF"


def test_dual_write_rings_bell_once(monkeypatch):
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    bus = Bus("agent-a", c, namespace=_ns(), promote=False)
    rings = []
    monkeypatch.setattr(bus, "_ring_bell", lambda *a, **k: rings.append(a))
    bus.send("agent-d", "handoff", "bell probe")
    assert len(rings) == 1, "T039a must not double-ring (lane bells activate at T039b)"


# ------------------------------------------- B4: trace exemption (R5 + amend E, D-3)
def test_lane_wants_integrity_policy():
    assert ps.lane_wants_integrity("work", tick=1)
    assert ps.lane_wants_integrity("sig", tick=1)
    assert ps.lane_wants_integrity("test-x", tick=1)
    assert not ps.lane_wants_integrity("trace", tick=1)
    n = ps.trace_spot_interval()
    assert ps.lane_wants_integrity("trace", tick=n), "every Nth trace = spot-check"


def test_trace_lane_unstamped_but_legacy_stamped(monkeypatch):
    c = _client()
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", "1")
    ns = _ns()
    bus = Bus("agent-a", c, namespace=ns, promote=False)
    bus.broadcast("narration", "trace probe")
    legacy = dict(c.xrevrange(f"{ns}:broadcast", count=1)[0][1])
    ring = dict(c.xrevrange(f"{ns}:trace", count=1)[0][1])
    assert "sha" in legacy, "legacy copy stays stamped (byte-identical bar)"
    if "sha" in ring:  # only legal on a spot-check tick
        assert int(ring.get("spot_tick", -1)) % ps.trace_spot_interval() == 0


# --------------------------------------------------------------------- B5: key shapes
def test_lane_key_shapes():
    ns = "nsx"
    assert ps.lane_stream_key(ns, "work", to="alice") == "nsx:work:inbox:alice"
    assert ps.lane_stream_key(ns, "sig", to="alice") == "nsx:sig:inbox:alice"
    assert ps.lane_stream_key(ns, "trace") == "nsx:trace"
    assert ps.lane_stream_key(ns, "work") == "nsx:work:broadcast"


# ------------------------------------------------------------- B6: reader census (A3)
def test_reader_census_documented():
    p = os.path.join(REPO, "docs", "library", "design",
                     "20260701_t039-purpose-keyed-lanes-latches-governi_7bc135.md")  # migrated at P3
    doc = open(p, encoding="utf-8").read()
    for reader in ("bifrost_api", "wake listener", "core/comm/doctor.py",
                   "scripts/bifrost_ui.py", "scripts/bifrost_console.py", "bifrost_pull"):
        assert reader in doc, f"census table must name reader: {reader}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
