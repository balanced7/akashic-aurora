"""
S0-alpha · the triage PARK (scry-to-bottom substrate).
Cites docs/recovery-arc-design-2026-07.md S0 (= deepseek BULKHEAD-0 ∪ kimi R4 ∪ claude B1)
+ the Canon: triage = scry-to-bottom — stale asks are BOTTOMED, never dropped.

Laws pinned (RED before core/comm/triage_park.py exists):
  1. PARK IS DURABLE — a parked ask lands on a durable per-agent surface with a receipt
     event; park returns the entry so the caller can advance its cursor past it.
  2. SCRY-TO-BOTTOM — unpark returns the message INTACT (bottomed ≠ dropped; the
     graveyard-is-a-resource law applies to the triage bench too).
  3. LOUD, NEVER SILENT (RB-29) — parking notifies the SENDER (a note: "your ask was
     parked: stale"); an expectation is settled by visible triage, not by vanishing.
  4. THE DOCTOR SEES THE BENCH — parked>0 renders a dashboard line with a drill.
Redis-backed in an isolated namespace; skips offline (pulse-test precedent).
Run: py -m pytest tests/test_s0_triage_park.py -q
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ns_env(monkeypatch):
    ns = f"t-s0-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    return ns


def _online():
    from core.comm.bus import Bus
    return Bus("t-park").online


def test_park_is_durable_and_receipted(monkeypatch):
    import pytest
    _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm import triage_park
    msg = {"id": "1000-0", "frm": "t-sender", "to": "t-agent", "kind": "question",
           "content": "an old ask", "ts": "2026-07-18T00:00:00"}
    entry = triage_park.park("t-agent", msg, reason="stale 72h", by="t-test")
    assert entry["parked_id"], "park returns the entry (caller advances its cursor past it)"
    bench = triage_park.list_parked("t-agent")
    assert len(bench) == 1 and bench[0]["msg"]["content"] == "an old ask"
    assert bench[0]["reason"] == "stale 72h"


def test_scry_to_bottom_unpark_returns_intact(monkeypatch):
    import pytest
    _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm import triage_park
    msg = {"id": "2000-0", "frm": "t-sender", "to": "t-agent", "kind": "handoff",
           "content": "bottomed, not dropped", "ts": "2026-07-18T00:00:00"}
    e = triage_park.park("t-agent", msg, reason="test", by="t-test")
    back = triage_park.unpark("t-agent", e["parked_id"])
    assert back["msg"] == msg, "unpark returns the message INTACT (scry-to-bottom law)"
    assert triage_park.list_parked("t-agent") == [], "the bench forgets what it returned"


def test_parking_notifies_the_sender_loudly(monkeypatch):
    import pytest
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm import triage_park
    from core.comm.bus import Bus
    msg = {"id": "3000-0", "frm": "t-sender", "to": "t-agent", "kind": "question",
           "content": "will be parked", "ts": "2026-07-18T00:00:00"}
    triage_park.park("t-agent", msg, reason="stale", by="t-test")
    inbox = Bus("t-sender")._client.xrevrange(f"{ns}:inbox:t-sender", count=5)
    joined = " ".join(str(f) for _sid, f in inbox)
    assert "parked" in joined.lower(), "RB-29: the sender HEARS about the parking (never silent)"


def test_doctor_renders_the_bench(monkeypatch):
    import pytest
    _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm import triage_park, doctor
    msg = {"id": "4000-0", "frm": "t-sender", "to": "t-agent", "kind": "question",
           "content": "benched", "ts": "2026-07-18T00:00:00"}
    triage_park.park("t-agent", msg, reason="stale", by="t-test")
    findings = doctor.examine("t-agent")
    bench = [f for f in findings if f["state"] == "triage_bench"]
    assert bench and bench[0]["grade"] == "dashboard", "the doctor sees the bench"
    assert "1" in bench[0]["line"] and bench[0]["drill"], "count + drill in the line"
