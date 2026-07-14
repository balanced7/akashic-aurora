"""T045 stage 2 (T039b) PRE-REGISTERED ACCEPTANCE -- the CONSUME side cuts to the WORK LANE.

Committed RED before implementation (method pre-registration; acceptance commit <= impl
commit). Cites research/claude-t045-stage2-scope-2026-07-14.md (reconciled on deepseek's
AMBER fence, fold CONFIRMed 2026-07-14) and docs/t039-lanes-latches-design-2026-07.md
(T039b bars A4/P3/P4/M2). Fence record: research/reviewed/
deepseek-t045-stage2-scope-review-2026-07-14.md.

REGISTERED SEAM CONTRACT (the build must land exactly these surfaces):
  * Bus.advance_to(..., cursor_key=None) -- optional override; default = shared legacy
    cursor (zero change for legacy callers); lane consumers pass the lane key.
    [deepseek fence refinement, adopted]
  * Bus.lane_cursor_key(agent=None) -> "{ns}:cursor:lane:{agent}" (inbox/bc field
    structure mirroring the shared cursor).  [fence Q1, adopted]
  * BifrostAPI.work_drain(timeout_ms=..., since_out=None) -- the runner/session consume
    door in lane mode. Gated by BIFROST_CONSUME_LANE=work (unset = legacy path
    byte-identical, strangler discipline). Drains sig BETWEEN work packets (P3); includes
    the legacy fallback while dual-write is ON (R2) and the lane-aware pending check so it
    is load-bearing with dual-write OFF (R7).

Pins (R1-R10; expected RED today -- the seam does not exist yet):
  R1  lane handoff drains end-to-end; advance via cursor_key; re-drain sees nothing.
  R2  dual-write ON + lane write FAILS + legacy delivers -> still drained (safety net).
  R3  at-least-once: no advance -> redelivery; advance(cursor_key) -> gone.
  R4  consume-door integrity on the lane path: corrupted sha packet is NEVER delivered.
  R5  P3: a sig packet enqueued after work1 is seen before work2.
  R6  P4 parity: note/status reach the drain but never wake an idle lane seat.
  R7  lane-aware pending check with DUAL-WRITE OFF: pre-arm lane-only mail still drains
      (proves the check load-bearing, not masked by the legacy twin).
  R8  the shared legacy cursor is NEVER written in lane mode.
  R9  tails-read fault at seed never replays lane history (stage-1 F2: "$" not "0").
  R10 cursor init at flip: fresh consumer seeds at tails (no replay); RETURNING consumer
      resumes from its lane cursor, never the shared one.

Redis-backed pins use throwaway namespaces (skip if down) -- CI without Redis skips,
matching stage 1. Run: py -m pytest tests/test_t045_runner_cutover.py -q
"""
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

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
    return f"bifrost_t045s2_{uuid.uuid4().hex[:8]}"


def _lane_mode(monkeypatch, dual_write="1"):
    monkeypatch.setenv("BIFROST_CONSUME_LANE", "work")
    monkeypatch.setenv("BIFROST_LANES_DUAL_WRITE", dual_write)


def _kinds(drained):
    """kind sequence from a work_drain result (accepts list or {'work':[],'sig':[]})."""
    if isinstance(drained, dict):
        seq = list(drained.get("sig", [])) + list(drained.get("work", []))
    else:
        seq = list(drained or [])
    return [str(getattr(m, "kind", m.get("kind") if isinstance(m, dict) else "?")) for m in seq]


# ------------------------------------------------------------ R1: end-to-end lane drain
def test_r1_lane_handoff_drains_and_advances(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    api = BifrostAPI("alice", namespace=ns)
    sender.send("alice", "handoff", "stage-2 work")
    got = api.work_drain(timeout_ms=1500)                 # RED: work_drain does not exist
    assert "handoff" in _kinds(got)
    # advance through the LANE cursor, then the packet must be gone
    key = api.bus.lane_cursor_key()                       # RED: lane_cursor_key missing
    api.bus.advance_to(inbox=str(getattr((got if isinstance(got, list) else got["work"])[0], "id", "")),
                       cursor_key=key)                    # RED: cursor_key param missing
    again = api.work_drain(timeout_ms=200)
    assert "handoff" not in _kinds(again), "consumed work must not redeliver after lane advance"


# ---------------------------------------- R2: lane write fails, legacy still delivers
def test_r2_lane_write_failure_falls_back_to_legacy(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch, dual_write="1")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    monkeypatch.setattr(sender, "_lane_write",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("lane down")),
                        raising=True)
    sender.send("alice", "handoff", "legacy-only by lane-write failure")
    api = BifrostAPI("alice", namespace=ns)
    got = api.work_drain(timeout_ms=1500)
    assert "handoff" in _kinds(got), \
        "dual-write ON + lane write failed + legacy delivered -> the strangler net must catch it"


# ------------------------------------------------- R3: at-least-once cursor semantics
def test_r3_no_advance_means_redelivery(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.send("alice", "handoff", "must survive a crash-before-advance")
    api = BifrostAPI("alice", namespace=ns)
    first = api.work_drain(timeout_ms=1500)
    assert "handoff" in _kinds(first)
    # simulate crash-before-advance: NO advance_to; a fresh consumer instance re-drains
    api2 = BifrostAPI("alice", namespace=ns)
    second = api2.work_drain(timeout_ms=1500)
    assert "handoff" in _kinds(second), "un-advanced lane packet must redeliver (RB-26 parity)"


# ------------------------------------------------------- R4: integrity DROP on lane path
def test_r4_corrupted_sha_never_delivered(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.send("alice", "handoff", "payload to corrupt")
    lane_key = f"{ns}:work:inbox:alice"
    entries = c.xrange(lane_key)
    assert entries, "test precondition: lane dual-write must have landed the packet"
    eid, fields = entries[-1]
    if "sha" in fields:
        c.xdel(lane_key, eid)
        fields["sha"] = "0" * len(fields["sha"])
        c.xadd(lane_key, fields)
    else:
        pytest.skip("packet carries no sha field in this namespace -- integrity path unarmed")
    api = BifrostAPI("alice", namespace=ns)
    got = api.work_drain(timeout_ms=800)
    assert "handoff" not in _kinds(got), \
        "T043 consume door on the LANE path: bad sha packets DROP loudly, never deliver"


# ------------------------------------------------------------- R5: P3 sig-interleave
def test_r5_sig_seen_before_second_work_packet(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.send("alice", "handoff", "work-1")
    sender.send("alice", "nudge", "sig lands AFTER work-1")   # nudge routes to sig lane
    sender.send("alice", "handoff", "work-2")
    api = BifrostAPI("alice", namespace=ns)
    seen = []
    for _ in range(4):
        seen += _kinds(api.work_drain(timeout_ms=800))
        if seen.count("handoff") >= 2:
            break
    assert "nudge" in seen and "handoff" in seen
    assert seen.index("nudge") < len(seen) - 1 - seen[::-1].index("handoff"), \
        "P3: the sig packet must be drained BEFORE the second work packet (EF beats AF)"


# ----------------------------------------- R6: note/status never wake an idle lane seat
def test_r6_note_status_drain_but_never_wake(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    watcher = BifrostAPI("alice", namespace=ns)
    assert watcher.wake_block(timeout_ms=200) == []       # arm quiet (stage-1 surface)
    sender.send("alice", "note", "informational")
    sender.send("alice", "status", "informational too")
    assert watcher.wake_block(timeout_ms=400) == [], "P4: note/status must not wake idle seats"
    api = BifrostAPI("alice", namespace=ns)
    got = api.work_drain(timeout_ms=800)                  # RED: work_drain does not exist
    ks = _kinds(got)
    assert "note" in ks and "status" in ks, "informational kinds still DRAIN (they are mail, not wakes)"


# ------------------------- R7: lane-aware pending check load-bearing (dual-write OFF)
def test_r7_pre_arm_lane_only_mail_drains_without_dual_write(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch, dual_write="0")               # THE point: no legacy twin mask
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.send("alice", "handoff", "lane-only, sent BEFORE the consumer exists")
    api = BifrostAPI("alice", namespace=ns)               # fresh consumer arms AFTER send
    got = api.work_drain(timeout_ms=800)
    assert "handoff" in _kinds(got), \
        "fence R7: with dual-write OFF the lane-aware pending check alone must catch pre-arm mail"


# ------------------------------------------- R8: shared cursor untouched in lane mode
def test_r8_shared_cursor_never_written_in_lane_mode(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.send("alice", "handoff", "drain me in lane mode")
    api = BifrostAPI("alice", namespace=ns)
    shared_key = api.bus._cursor_key()
    before = c.hgetall(shared_key)
    got = api.work_drain(timeout_ms=1500)
    assert _kinds(got), "precondition: something drained"
    lane_key = api.bus.lane_cursor_key()
    api.bus.advance_to(inbox="9999999999999-0", cursor_key=lane_key)
    after = c.hgetall(shared_key)
    assert before == after, "lane-mode consume/advance must NEVER touch the shared legacy cursor"
    assert c.hgetall(lane_key), "the lane cursor key must hold the advance"


# ------------------------------------ R9: tails fault never replays history (F2 fix)
def test_r9_tails_fault_seeds_new_only_never_history(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    monkeypatch.setenv("BIFROST_WAKE_LANE", "work")
    ns = _ns()
    c.xadd(f"{ns}:work:inbox:alice", {"frm": "ghost", "to": "alice", "kind": "handoff",
                                      "content": '"ancient soak history"', "ts": "0",
                                      "meta": "{}", "parts": "[]"})
    api = BifrostAPI("alice", namespace=ns)
    real_xrevrange = c.xrevrange
    calls = {"n": 0}

    def flaky_xrevrange(*a, **k):
        calls["n"] += 1
        raise ConnectionError("simulated redis blip during tails read")
    monkeypatch.setattr(api.bus._client, "xrevrange", flaky_xrevrange, raising=False)
    got = api.wake_block(timeout_ms=300)
    monkeypatch.setattr(api.bus._client, "xrevrange", real_xrevrange, raising=False)
    assert calls["n"] > 0, "test precondition: the fault actually hit the tails read"
    assert got == [], \
        "stage-1 F2: a tails-read fault must seed '$'-equivalent (new-only), never replay history"


# ----------------------------------------------- R10: cursor init at flip (fresh/return)
def test_r10_fresh_seeds_at_tails_returning_reads_lane_cursor(monkeypatch):
    c = _client()
    _lane_mode(monkeypatch)
    ns = _ns()
    c.xadd(f"{ns}:work:inbox:alice", {"frm": "ghost", "to": "alice", "kind": "handoff",
                                      "content": '"pre-flip history"', "ts": "0",
                                      "meta": "{}", "parts": "[]"})
    fresh = BifrostAPI("alice", namespace=ns)
    assert _kinds(fresh.work_drain(timeout_ms=300)) == [], \
        "R10a: first boot into lane mode seeds at tails -- history is soak, not mail"
    sender = Bus("boss", c, namespace=ns, promote=False)
    sender.send("alice", "handoff", "post-flip real work")
    got = fresh.work_drain(timeout_ms=1500)
    assert "handoff" in _kinds(got)
    wid = str(getattr((got if isinstance(got, list) else got["work"])[0], "id", ""))
    fresh.bus.advance_to(inbox=wid, cursor_key=fresh.bus.lane_cursor_key())
    returning = BifrostAPI("alice", namespace=ns)         # simulates a runner restart
    assert "handoff" not in _kinds(returning.work_drain(timeout_ms=300)), \
        "R10b: a RETURNING consumer resumes from its lane cursor -- no re-delivery of consumed work"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
