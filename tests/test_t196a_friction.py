"""
T196a -- the friction reader: pre-registered acceptance (committed RED, before impl).

Spec: docs/library/design/20260805_t196-ask-transaction-spec_b59657.md. Sol's metrics
recommendation, fenced through deepseek (branch C + C2): measure collaboration friction
from evidence that already exists, claim nothing the anchors cannot show. This is the
falsifiability instrument for the whole T196 arc -- the verb redesign is not allowed to
call itself an improvement without a baseline from this reader.

Contract frozen here:
  expectations.snapshot(sender) -> Dict[oid, rec]     READ-ONLY armed records: never
      mutates, never consumes, never advances -- observation split from action (T025)
  friction.fold(terminal_events, open_records, *, now) -> report      PURE (no I/O):
      report["episodes"]: one row per episode --
          terminal rows from firehose events (kind expectation_settled_answered /
          expectation_dead / expectation_settled_done_task) -> outcome
          answered|dead|echo, peer from detail.to, redrives from detail attempt OR
          attempts (both spellings live), duration_s from event.at - detail.created
          ONLY when created is present -- an event without created yields
          duration_s None, NEVER 0.0 and NEVER a now-based guess
      open rows from snapshot records -> outcome open, state dispatched (attempt==0)
          or redriving (attempt>0), age_s from created
      report["agg"]: n_open n_answered n_dead n_echo n_closed, dead_rate (None when
          nothing closed -- a rate over zero is a lie), settle_p50_s/settle_p90_s over
          KNOWN durations only (None when none known), n_duration_unknown
      report["blind"]: NON-EMPTY list naming what this reader cannot see (no-silent-caps
          made structural: a report that names no blindness is claiming omniscience)
  friction.gather(agent, *, window_h=168, log=None, now=None) -> report   read-side
      compose: EventLog.scan + snapshot -> fold. ZERO writes to any stream or record.
  CLI door: agent_cli.py grows a `friction` verb.

Run: py -m pytest tests/test_t196a_friction.py -q
"""
import json
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from core.foundation.timeutil import now_iso, to_epoch  # noqa: E402

try:
    from core.comm import expectations
    from core.comm.bus import Bus
except ImportError:
    expectations = Bus = None

try:
    from core.comm import friction
    _BUILT = hasattr(friction, "fold") and hasattr(friction, "gather")
except ImportError:
    friction = None
    _BUILT = False

try:
    _ONLINE = bool(Bus and Bus("t196a-probe").online)
except Exception:
    _ONLINE = False


def _iso(epoch):
    import datetime
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).isoformat()


# --- P1: the seams exist (RED today: no friction module, no snapshot) ---

def test_seams_exist():
    assert friction is not None and _BUILT, \
        "core/comm/friction.py with fold() + gather() is the T196a deliverable"
    assert hasattr(expectations, "snapshot"), \
        "expectations.snapshot(sender) -- the read-only armed-record view"


pytestmark_live = pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline")
needs_built = pytest.mark.skipif(not _BUILT, reason="friction module pending (pins frozen)")


# --- P2: fold classifies, computes only honest durations, and names its blindness ---

@needs_built
def test_fold_classification_and_aggregates():
    t0 = 1_000_000.0
    now = t0 + 1000
    events = [
        {"kind": "expectation_settled_answered", "at": _iso(t0 + 100), "agent_id": "s",
         "refs": ["A1", "R1"],
         "detail": {"to": "peer1", "attempt": 1, "created": t0, "answer_id": "R1"}},
        {"kind": "expectation_dead", "at": _iso(t0 + 500), "agent_id": "s",
         "refs": ["A2"],
         "detail": {"to": "peer2", "attempts": 3}},                  # legacy: no created
        {"kind": "expectation_settled_done_task", "at": _iso(t0 + 300), "agent_id": "s",
         "refs": ["A3"],
         "detail": {"to": "peer1", "attempt": 0, "settle": "T042=done"}},   # no created
        {"kind": "boot", "at": _iso(t0 + 1), "agent_id": "s", "detail": {}},  # ignored
    ]
    open_records = {
        "A4": {"to": "peer1", "created": now - 50, "deadline_ts": now + 10, "attempt": 0},
        "A5": {"to": "peer2", "created": now - 900, "deadline_ts": now - 10, "attempt": 2},
    }
    rep = friction.fold(events, open_records, now=now)
    by_id = {e["ask_id"]: e for e in rep["episodes"]}
    assert set(by_id) == {"A1", "A2", "A3", "A4", "A5"}, "boot event never becomes an episode"

    assert by_id["A1"]["outcome"] == "answered" and by_id["A1"]["peer"] == "peer1"
    assert abs(by_id["A1"]["duration_s"] - 100) < 2 and by_id["A1"]["redrives"] == 1

    assert by_id["A2"]["outcome"] == "dead" and by_id["A2"]["redrives"] == 3
    assert by_id["A2"]["duration_s"] is None, \
        "no created -> duration UNKNOWN: never 0.0, never a now-based guess"

    assert by_id["A3"]["outcome"] == "echo" and by_id["A3"]["duration_s"] is None

    assert by_id["A4"]["outcome"] == "open" and by_id["A4"]["state"] == "dispatched"
    assert abs(by_id["A4"]["age_s"] - 50) < 2
    assert by_id["A5"]["outcome"] == "open" and by_id["A5"]["state"] == "redriving"

    agg = rep["agg"]
    assert (agg["n_open"], agg["n_answered"], agg["n_dead"], agg["n_echo"]) == (2, 1, 1, 1)
    assert agg["n_closed"] == 3
    assert abs(agg["dead_rate"] - (1 / 3)) < 1e-9
    assert agg["settle_p50_s"] == 100 and agg["n_duration_unknown"] == 2

    assert isinstance(rep["blind"], list) and rep["blind"], \
        "a report that names no blindness is claiming omniscience"


# --- P3: rates never fabricate -- nothing closed means dead_rate None, not 0.0 ---

@needs_built
def test_fold_rate_honesty_on_empty():
    rep = friction.fold([], {}, now=time.time())
    assert rep["agg"]["n_closed"] == 0
    assert rep["agg"]["dead_rate"] is None, \
        "0/0 rendered as 0.0 would read as 'nothing ever dies' -- the fabricated-total lie"
    assert rep["agg"]["settle_p50_s"] is None


# --- P4: snapshot is READ-ONLY observation (T025: observation split from action) ---

@needs_built
@pytestmark_live
def test_snapshot_reads_without_mutating():
    s = f"t196asnd-{uuid.uuid4().hex[:8]}"
    r = f"t196arcv-{uuid.uuid4().hex[:8]}"
    try:
        orig = Bus(s).send(r, "request", "measure me")
        assert expectations.arm(s, orig, r, "request", "measure me", 60)
        c = Bus(s)._client
        key = f"bifrost:expect:{s}"
        before = c.hgetall(key)
        snap = expectations.snapshot(s)
        assert str(orig) in {str(k) for k in snap}, "armed record visible"
        rec = snap[str(orig)]
        assert rec.get("to") == r and rec.get("created")
        assert c.hgetall(key) == before, "snapshot mutated nothing -- byte-identical hash"
        t0 = time.time()
        assert expectations.sweep(s, now=t0 + 61)["redriven"] == [str(orig)] or \
               expectations.sweep(s, now=t0 + 61)["redriven"] == [orig], \
            "the deadline still fires after snapshots: observing never settles"
    finally:
        try:
            c = Bus(s)._client
            for k in (f"bifrost:expect:{s}", f"bifrost:inbox:{s}", f"bifrost:inbox:{r}",
                      f"bifrost:cursor:{s}", f"bifrost:cursor:{r}",
                      f"bifrost:presence:{s}", f"bifrost:presence:{r}"):
                c.delete(k)
        except Exception:
            pass


# --- P5: gather composes without writing (zero-writes acceptance bar) ---

@needs_built
@pytestmark_live
def test_gather_zero_writes():
    s = f"t196agth-{uuid.uuid4().hex[:8]}"
    r = f"t196agrv-{uuid.uuid4().hex[:8]}"
    try:
        orig = Bus(s).send(r, "request", "friction probe")
        assert expectations.arm(s, orig, r, "request", "friction probe", 60)
        c = Bus(s)._client
        key = f"bifrost:expect:{s}"
        hash_before = c.hgetall(key)
        tail_before = Bus(s).tail()
        rep = friction.gather(s)
        assert any(e["ask_id"] == str(orig) and e["outcome"] == "open"
                   for e in rep["episodes"]), "the armed ask appears as an open episode"
        assert c.hgetall(key) == hash_before, "gather wrote nothing to the record"
        assert Bus(s).tail() == tail_before, "gather wrote nothing to the streams"
    finally:
        try:
            c = Bus(s)._client
            for k in (f"bifrost:expect:{s}", f"bifrost:inbox:{s}", f"bifrost:inbox:{r}",
                      f"bifrost:cursor:{s}", f"bifrost:cursor:{r}",
                      f"bifrost:presence:{s}", f"bifrost:presence:{r}"):
                c.delete(k)
        except Exception:
            pass


# --- P6: the door is wired (built != wired) ---

def test_door_wired():
    cli = open(os.path.join(_ROOT, "agent_cli.py"), encoding="utf-8").read()
    assert 'add_parser("friction"' in cli, "agent_cli.py grew the friction verb"
