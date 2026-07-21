"""
S0-gamma-b · CLI consume path auto-park (bifrost-sync --consume stale-gate).

Mirror of S0-beta's D2 auto-park block (bifrost_runner_deepseek.py:1150-1165)
at the session door's consume path (agent/bifrost_pull.consume_inbox). Stale
asks are partitioned via packet_spec, parked to the durable bench via
triage_park.park(), and excluded from the consumed batch.

AUTHORSHIP: deepseek's build package (write-gated seat, night-run 2026-07-21),
applied + fenced by claude. Fence amendment A2: the original pins planted
staleness via meta.sent_ts, which packet_spec.msg_age_ms NEVER reads -- age
derives from the stream id '{ms}-{seq}' (kimi D2). Stale plants here ride
explicit old stream ids (the test_doctor_dead_runner_visibility.py pattern).

Laws pinned (RED before the agent/bifrost_pull.py edit exists):
  G1. STALE ASKS PARKED -- bifrost-sync --consume parks stale asks to bench,
      returns only fresh messages. Restart-safe (bench is Redis-backed).
  G2. NON-ASK NEVER PARKED -- stale informs/traces are not parked (no bench
      pollution); they're simply excluded from consumed.
  G3. FAIL-OPEN -- consume still returns fresh messages when parking cannot run.
  G4. SENDER NOTIFIED (RB-29) -- park() notifies the sender; no extra CLI work.
  G5. FRESH MAIL UNTOUCHED -- fresh messages return normally in consumed.

Run: py -m pytest tests/test_s0_gamma_b_cli_park.py -q
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ns_env(monkeypatch):
    ns = f"t-s0g-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    monkeypatch.delenv("BIFROST_CONSUME_LANE", raising=False)   # pins ride the legacy path
    return ns


def _online():
    from core.comm.bus import Bus
    return Bus("t-gamma-b").online


def _plant_stale(ns, agent, kind, content, frm="t-gamma-b-snd"):
    """A GENUINELY old message: explicit ancient stream id (age = now - id ms)."""
    from core.comm.bus import Bus
    c = Bus(agent)._client
    old_ms = int(time.time() * 1000) - 48 * 3600 * 1000          # 48h old
    c.xadd(f"{ns}:inbox:{agent}",
           {"kind": kind, "frm": frm, "to": agent, "content": content,
            "ts": "2026-07-19T00:00:00+00:00"},
           id=f"{old_ms}-{uuid.uuid4().int % 1000}")


# --- G1: stale asks parked, fresh returned ---------------------------------

def test_stale_asks_parked_fresh_returned(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    from core.comm import triage_park
    agent = f"t-gamma-b-{uuid.uuid4().hex[:6]}"
    stale_id = f"s0g-{uuid.uuid4().hex[:4]}-stale"
    fresh_id = f"s0g-{uuid.uuid4().hex[:4]}-fresh"
    _plant_stale(ns, agent, "question", f"stale ask: {stale_id}")
    Bus(f"{agent}-peer").send(agent, "handoff", f"fresh ask: {fresh_id}")
    from agent.bifrost_pull import consume_inbox
    result = consume_inbox(agent, limit=20)
    contents = [c.get("content", "") for c in result.get("consumed", [])]
    assert not any(stale_id in c for c in contents), "stale ask excluded from consumed"
    assert any(fresh_id in c for c in contents), "fresh ask still delivered"
    parked = [e["msg"].get("content", "") for e in triage_park.list_parked(agent)]
    assert any(stale_id in c for c in parked), "stale ask parked to durable bench"


# --- G2: non-ask stale not parked ------------------------------------------

def test_non_ask_stale_not_parked(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm import triage_park
    agent = f"t-gamma-b-{uuid.uuid4().hex[:6]}"
    bench_before = triage_park.count(agent)
    _plant_stale(ns, agent, "inform", "stale inform")
    _plant_stale(ns, agent, "trace", "stale trace")
    from agent.bifrost_pull import consume_inbox
    result = consume_inbox(agent, limit=20)
    assert triage_park.count(agent) == bench_before, \
        "stale informs/traces never park to bench"
    contents = [c.get("content", "") for c in result.get("consumed", [])]
    assert not any("stale inform" in c for c in contents), \
        "stale non-ask excluded from consumed (skip, not deliver)"


# --- G3: fail-open ----------------------------------------------------------

def test_consume_survives_park_failure(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    agent = f"t-gamma-b-{uuid.uuid4().hex[:6]}"
    fresh_id = f"s0g-{uuid.uuid4().hex[:4]}-ok"
    _plant_stale(ns, agent, "question", "stale ask that will fail to park")
    Bus(f"{agent}-peer").send(agent, "question", f"fresh: {fresh_id}")
    import core.comm.triage_park as tp

    def boom(*a, **k):
        raise RuntimeError("bench backend down")
    monkeypatch.setattr(tp, "park", boom)
    from agent.bifrost_pull import consume_inbox
    result = consume_inbox(agent, limit=20)
    contents = [c.get("content", "") for c in result.get("consumed", [])]
    assert any(fresh_id in c for c in contents), \
        "fresh mail still returned even when park raises"


# --- G4: sender notified (RB-29) -------------------------------------------

def test_sender_notified_on_cli_auto_park(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    sender = f"t-gamma-b-snd-{uuid.uuid4().hex[:6]}"
    agent = f"t-gamma-b-rcv-{uuid.uuid4().hex[:6]}"
    _plant_stale(ns, agent, "question", "stale ask from sender", frm=sender)
    from agent.bifrost_pull import consume_inbox
    consume_inbox(agent, limit=20)
    inbox = Bus(sender)._client.xrevrange(f"{ns}:inbox:{sender}", count=10)
    joined = " ".join(str(f) for _sid, f in inbox)
    assert "parked" in joined.lower(), "RB-29: sender notified their ask was parked"


# --- G5: fresh mail untouched ----------------------------------------------

def test_fresh_mail_returned_normally(monkeypatch):
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm.bus import Bus
    agent = f"t-gamma-b-{uuid.uuid4().hex[:6]}"
    expected = [f"msg-{uuid.uuid4().hex[:4]}-{i}" for i in range(3)]
    for e in expected:
        Bus(f"{agent}-peer").send(agent, "inform", e)
    from agent.bifrost_pull import consume_inbox
    result = consume_inbox(agent, limit=20)
    contents = [c.get("content", "") for c in result.get("consumed", [])]
    for e in expected:
        assert any(e in c for c in contents), f"fresh message '{e}' returned in consumed"
