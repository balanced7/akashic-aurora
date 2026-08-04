"""PRE-REGISTERED ACCEPTANCE (T157) -- the wire journal write path, sharded and async.

MEASURED BASELINE (note wire-perf-baseline, 4000 calls, identical payload, caller-side added
latency per API round trip):

  threads ->  mean/p99 us
  1       ->   251/770        4 -> 1702/3673      8 -> 3477/8086     20 -> 8266/21891

Cost grows ~linearly with concurrency: a lock convoy. record() does makedirs + open + json.dumps
+ rotate under a threading.Lock INLINE on the caller's thread -- the thread that is mid-API-call.

Four strategies at 20 threads (mean/p99/max us):
  A monolith (shipped) 7458/18492/30854      B sharded-only 3055/5281/7052
  C async, 1 writer       0.8/2.3/405        D sharded+async   0.8/1.9/96

Two defects wearing one costume, and they need different fixes: work on the WRONG THREAD (only a
non-blocking enqueue fixes it) and a SHARED RESOURCE (only sharding fixes it -- 2.4x on the mean
but 4.2x on the WORST case, because a single background writer is itself a serialization point
under burst). Ship both.

THE ARCHITECTURAL PRIZE IS NOT SPEED. Sharding PER AGENT buys ISOLATION, which matters more at
fleet scale than microseconds: a runaway player cannot starve the writer or blind every other
player, attribution is free (the shard IS the agent), and per-player retention and quota become
expressible. For a season where some players are semi-trusted BY DESIGN, blast-radius containment
is the point. Daniil, 2026-08-04: "I don't want things stalled on performance because we built
things in singlethreaded ways."

  P1  records SHARD BY AGENT -- two agents' records land in different shards
  P2  ROTATION IS PER SHARD -- a runaway agent cannot evict another agent's history. This is the
      isolation property stated as a test; without it sharding is just a naming convention.
  P3  the CALLER no longer does the work: record() under concurrency costs a fraction of the
      synchronous path. Relative, not absolute, so the pin measures the architecture and not the
      machine it happens to run on.
  P4  BACKPRESSURE DROPS AND COUNTS. A full queue never blocks an API call and never raises; the
      drop is counted, because a silent drop is a measured zero (the hazard this repo has been
      bitten by twice).
  P5  NO LOSS in normal operation -- everything accepted is readable after flush()
  P6  THE SEAM: AKASHIC_WIRE_WRITER=sync restores the shipped synchronous path exactly. The
      operator asked for changes reversible WITHOUT a revert; one env var is that.
  P7  LEGACY JOURNALS STAY READABLE -- files written under the old flat scheme are still returned
      by files() and read_all(). A telemetry store that loses its history on upgrade is worse
      than the convoy.
  P8  a per-agent read is a FILE SELECTION, and it still verifies the in-record agent, so a
      sanitisation collision can never return another agent's rows.

Run: py -m pytest tests/test_t157_wire_sharded_async.py -q
"""
import json
import os
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _wj():
    import importlib
    from scripts import wire_journal
    return importlib.reload(wire_journal)


def _mk(tmp_path, agent, **kw):
    WJ = _wj()
    return WJ.WireJournal(journal_dir=str(tmp_path), agent=agent, **kw)


# --------------------------------------------------------------------------- P1

def test_p1_records_shard_by_agent(tmp_path):
    a = _mk(tmp_path, "alice")
    b = _mk(tmp_path, "bob")
    a.record(status=200, model="m")
    b.record(status=200, model="m")
    a.flush(); b.flush()

    files = a.files()
    assert files, "nothing was written"
    owners = {}
    for p in files:
        rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
        owners[p] = {r.get("agent") for r in rows}

    assert not any(len(v) > 1 for v in owners.values()), (
        f"a single file holds records from more than one agent -- not sharded: {owners}")
    assert len({frozenset(v) for v in owners.values()}) >= 2, (
        f"both agents' records landed in the same shard: {owners}")


# --------------------------------------------------------------------------- P2

def test_p2_rotation_is_per_shard(tmp_path):
    """A runaway agent must not be able to delete another agent's history.

    This is the whole isolation argument. If rotation stays global, sharding is decoration.
    """
    WJ = _wj()
    quiet = WJ.WireJournal(journal_dir=str(tmp_path), agent="quiet")
    quiet.record(status=200, model="m")
    quiet.flush()
    quiet_before = [p for p in quiet.files() if "quiet" in p]
    assert quiet_before, "the quiet agent wrote nothing to begin with"

    old_files, old_bytes = WJ.MAX_FILES, WJ.MAX_BYTES
    try:
        WJ.MAX_FILES, WJ.MAX_BYTES = 2, 200          # force the loud agent to roll and evict
        loud = WJ.WireJournal(journal_dir=str(tmp_path), agent="loud")
        for _ in range(60):
            loud.record(status=200, model="m", error="x" * 200)
        loud.flush()
    finally:
        WJ.MAX_FILES, WJ.MAX_BYTES = old_files, old_bytes

    still = [p for p in quiet.files() if "quiet" in p]
    assert still, (
        "the loud agent's rotation deleted the quiet agent's history -- rotation is still global, "
        "so one runaway player can blind every other player")


# --------------------------------------------------------------------------- P3

def test_p3_the_caller_no_longer_does_the_work(tmp_path):
    """Relative to the synchronous writer, measured in the same process on the same machine."""
    WJ = _wj()

    def bench(writer, tag, threads=8, per=120):
        j = WJ.WireJournal(journal_dir=str(tmp_path / tag), agent="a", writer=writer)
        lat, lock = [], threading.Lock()

        def work():
            mine = []
            for _ in range(per):
                t0 = time.perf_counter()
                j.record(status=200, model="m")
                mine.append(time.perf_counter() - t0)
            with lock:
                lat.extend(mine)

        ts = [threading.Thread(target=work) for _ in range(threads)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        j.flush()
        return sum(lat) / len(lat)

    sync_mean = bench("sync", "s")
    async_mean = bench("async", "a")
    assert async_mean * 5 < sync_mean, (
        f"the enqueue is not buying the caller anything: async {async_mean*1e6:.1f}us vs sync "
        f"{sync_mean*1e6:.1f}us. The convoy is the caller doing the write on the request thread; "
        f"if this ratio collapses, the work moved back onto that thread.")


# --------------------------------------------------------------------------- P4

def test_p4_backpressure_drops_and_counts(tmp_path):
    """Never block an API call. Never raise. But never drop SILENTLY either."""
    j = _mk(tmp_path, "flood", queue_size=4)
    j.pause()                                   # hold the writer so the queue must fill
    try:
        t0 = time.perf_counter()
        for _ in range(400):
            assert j.record(status=200, model="m") in (True, False)
        elapsed = time.perf_counter() - t0
    finally:
        j.resume()

    assert elapsed < 2.0, (
        f"record() blocked for {elapsed:.2f}s against a full queue -- backpressure is reaching "
        f"the caller, which is the API thread")
    assert j.dropped > 0, (
        "the queue was capped at 4 and 400 records were pushed against a paused writer, yet "
        "nothing was counted as dropped -- a silent drop renders as a measured zero")


# --------------------------------------------------------------------------- P5

def test_p5_nothing_is_lost_in_normal_operation(tmp_path):
    j = _mk(tmp_path, "seat")
    for i in range(200):
        j.record(status=200, model="m", response_id=f"r{i:04d}")
    j.flush()

    ids = {r.get("response_id") for r in j.read_all()}
    missing = [f"r{i:04d}" for i in range(200) if f"r{i:04d}" not in ids]
    assert not missing, f"{len(missing)} record(s) accepted and never written: {missing[:5]}"
    assert j.dropped == 0, f"dropped {j.dropped} with an idle queue"


# --------------------------------------------------------------------------- P6

def test_p6_the_seam_restores_the_shipped_behaviour(tmp_path, monkeypatch):
    """One env var, no revert. The operator's standing requirement for risky work."""
    monkeypatch.setenv("AKASHIC_WIRE_WRITER", "sync")
    WJ = _wj()
    j = WJ.WireJournal(journal_dir=str(tmp_path), agent="seat")
    assert j.writer_kind == "sync", f"env did not select the sync writer (got {j.writer_kind!r})"

    j.record(status=200, model="m", response_id="r1")
    # synchronous means it is on disk the instant record() returns, with no flush
    assert any(r.get("response_id") == "r1" for r in j.read_all()), (
        "the sync writer did not write through -- the seam does not actually restore the "
        "shipped behaviour")

    monkeypatch.setenv("AKASHIC_WIRE_WRITER", "async")
    WJ2 = _wj()
    assert WJ2.WireJournal(journal_dir=str(tmp_path), agent="seat").writer_kind == "async"


# --------------------------------------------------------------------------- P7

def test_p7_legacy_journals_stay_readable(tmp_path):
    """Files written by the pre-T157 flat writer must not vanish on upgrade."""
    day = time.strftime("%Y%m%d")
    legacy = tmp_path / f"wire-{day}-001.jsonl"
    legacy.write_text(json.dumps({"ts": 1, "agent": "old", "status": 200}) + "\n",
                      encoding="utf-8")

    j = _mk(tmp_path, "new")
    j.record(status=201, model="m")
    j.flush()

    assert str(legacy) in [os.path.abspath(p) for p in j.files()], (
        "files() no longer returns pre-T157 segments")
    agents = {r.get("agent") for r in j.read_all()}
    assert "old" in agents and "new" in agents, (
        f"legacy records became unreadable after the shard migration: {agents}")


# --------------------------------------------------------------------------- P8

def test_p8_agent_read_is_a_selection_and_still_verifies(tmp_path):
    """Sanitisation can collide; the in-record agent field is authoritative."""
    a = _mk(tmp_path, "team/one")               # sanitises to something safe
    b = _mk(tmp_path, "team:one")               # may sanitise to the SAME thing
    a.record(status=200, model="m", response_id="A")
    b.record(status=200, model="m", response_id="B")
    a.flush(); b.flush()

    rows = a.read_all(agent="team/one")
    assert rows, "the scoped read returned nothing"
    assert {r.get("response_id") for r in rows} == {"A"}, (
        f"a scoped read leaked another agent's rows through a sanitisation collision: "
        f"{[(r.get('agent'), r.get('response_id')) for r in rows]}")
