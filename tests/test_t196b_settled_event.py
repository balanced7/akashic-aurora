"""
T196b -- durable ANSWERED evidence: pre-registered acceptance (committed RED, before impl).

Spec: docs/library/design/20260805_t196-ask-transaction-spec_b59657.md (claude + deepseek
fence R1). The asymmetry this closes: DEAD gets a durable firehose event
(`expectation_dead`) and ECHO gets one (`expectation_settled_done_task`), but ANSWERED --
the state most asks end in -- leaves only a TTL'd settle marker and a trimmable stream
entry (bus maxlen ~10k). Fence branch A's fatal: terminal truth must not live in
trimmable evidence. Terminal states get durable events; ANSWERED was the gap.

Contract frozen here:
  expectations._emit_settled(sender, oid, rid, rec) -> None   (module-level seam,
      parallel to _emit_dead: spyable, best-effort, NEVER raises into the sweep)
  fires on EVERY answer-settle transition -- both the linked path and the FIFO
      fallback settle through the same atomic transition, so one seam covers both
  the durable event:
      kind = "expectation_settled_answered"
      refs = [<original ask id>, <answering message id>]   (ask first, answer second)
      detail carries: to, attempt, created  -- `created` because the expectation
      record is DELETED at settle, so episode duration must be computable from the
      terminal event ALONE (T196a reads it; a terminal event that forces a join
      against a deleted record is evidence that trims itself)
  parity: _emit_dead's event ALSO carries `created` in detail (same reason -- a dead
      episode's duration is as real as an answered one's)

Run: py -m pytest tests/test_t196b_settled_event.py -q
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.comm import expectations
    from core.comm.bus import Bus
    _BUILT = hasattr(expectations, "arm") and hasattr(expectations, "sweep")
except ImportError:
    expectations = Bus = None
    _BUILT = False

try:
    _ONLINE = bool(Bus and Bus("t196b-probe").online)
except Exception:
    _ONLINE = False

pytestmark = [
    pytest.mark.skipif(not _BUILT, reason="expectations module absent"),
    pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline"),
]


@pytest.fixture()
def pair():
    """(sender, recipient), teardown of every touched key (idiom: test_t030_l4)."""
    s = f"t196bsnd-{uuid.uuid4().hex[:8]}"
    r = f"t196brcv-{uuid.uuid4().hex[:8]}"
    for aid in (s, r):
        b = Bus(aid)
        b.advance_to(bc=b.tail().get("bc"), generation=0)
    yield s, r
    try:
        c = Bus(s)._client
        for k in (f"bifrost:expect:{s}", f"bifrost:inbox:{s}", f"bifrost:inbox:{r}",
                  f"bifrost:cursor:{s}", f"bifrost:cursor:{r}",
                  f"bifrost:presence:{s}", f"bifrost:presence:{r}"):
            c.delete(k)
    except Exception:
        pass


def _arm(s, r, within=60, content="answer me"):
    orig = Bus(s).send(r, "request", content)
    assert orig
    assert expectations.arm(s, orig, r, "request", content, within)
    return orig


# --- P1: the seam exists (RED today: there is no _emit_settled) ---

def test_seam_exists_parallel_to_emit_dead():
    assert hasattr(expectations, "_emit_settled"), \
        "T196b seam missing: _emit_settled(sender, oid, rid, rec), parallel to _emit_dead"


# --- P2: a LINKED settle fires the seam once, with [ask id, answer id] ---

def test_linked_settle_emits_once_with_both_ids(pair, monkeypatch):
    s, r = pair
    seen = []
    monkeypatch.setattr(expectations, "_emit_settled",
                        lambda sender, oid, rid, rec: seen.append((sender, oid, rid, rec)))
    t0 = time.time()
    orig = _arm(s, r)
    Bus(r).send(s, "reply", "the answer", meta={"answers": orig})
    res = expectations.sweep(s, now=t0 + 5)
    assert res["cleared"] == [orig]
    assert len(seen) == 1, "one settle transition -> exactly one durable-evidence emit"
    sender, oid, rid, rec = seen[0]
    assert sender == s and oid == orig
    assert rid, "the answering message id rides along -- the readout's answer pointer"
    assert isinstance(rec, dict) and rec.get("to") == r, \
        "the record (with created/attempt) is handed to the emit BEFORE deletion"


# --- P3: the FIFO-fallback settle fires the same seam ---

def test_fifo_settle_also_emits(pair, monkeypatch):
    s, r = pair
    seen = []
    monkeypatch.setattr(expectations, "_emit_settled",
                        lambda sender, oid, rid, rec: seen.append(oid))
    t0 = time.time()
    orig = _arm(s, r)
    Bus(r).send(s, "reply", "unlinked answer")          # no meta.answers
    res = expectations.sweep(s, now=t0 + 5)
    assert res["cleared"] == [orig]
    assert seen == [orig], "FIFO fallback is a settle like any other: durable evidence"


# --- P4: the durable event's shape (kind, refs order, created in detail) ---

def test_event_shape_kind_refs_created(pair, monkeypatch):
    s, r = pair
    calls = []
    import core.events.event_log as event_log
    monkeypatch.setattr(event_log, "capture_event",
                        lambda kind, summary, **kw: calls.append((kind, summary, kw)))
    t0 = time.time()
    orig = _arm(s, r)
    Bus(r).send(s, "reply", "the answer", meta={"answers": orig})
    expectations.sweep(s, now=t0 + 5)
    settled = [c for c in calls if c[0] == "expectation_settled_answered"]
    assert len(settled) == 1, "kind is expectation_settled_answered"
    kind, summary, kw = settled[0]
    refs = kw.get("refs") or []
    assert len(refs) == 2 and refs[0] == str(orig), \
        "refs = [ask id, answer id], ask FIRST (stable order: attribution depends on it)"
    detail = kw.get("detail") or {}
    assert detail.get("created"), \
        "created rides the terminal event: the record is deleted at settle, so episode " \
        "duration must be computable from this event ALONE (T196a reads it)"
    assert kw.get("agent_id") == s


# --- P5: parity -- the DEAD event also carries created (same duration argument) ---

def test_dead_event_carries_created(pair, monkeypatch):
    s, r = pair
    calls = []
    import core.events.event_log as event_log
    monkeypatch.setattr(event_log, "capture_event",
                        lambda kind, summary, **kw: calls.append((kind, kw)))
    t0 = time.time()
    orig = _arm(s, r, within=60)
    now = t0 + 61
    for _ in range(expectations.REDRIVES):
        assert expectations.sweep(s, now=now)["redriven"] == [orig]
        now += 3600
    assert expectations.sweep(s, now=now)["dead"] == [orig]
    dead = [c for c in calls if c[0] == "expectation_dead"]
    assert len(dead) == 1
    assert (dead[0][1].get("detail") or {}).get("created"), \
        "a dead episode's duration is as real as an answered one's"


# --- P6: the emit is best-effort -- a raising emit never breaks the sweep ---

def test_emit_failure_never_breaks_settle(pair, monkeypatch):
    s, r = pair

    def _boom(*a, **k):
        raise RuntimeError("firehose down")

    monkeypatch.setattr(expectations, "_emit_settled", _boom)
    t0 = time.time()
    orig = _arm(s, r)
    Bus(r).send(s, "reply", "the answer", meta={"answers": orig})
    res = expectations.sweep(s, now=t0 + 5)
    assert res["cleared"] == [orig], \
        "telemetry must never eat the transition: settle succeeds, evidence is lost loudly " \
        "in the emit's own try/except, never by wedging the sweep"
