"""
Slice V1 -- time-indexed EventQuery. The bar: window queries have TOTAL recall within
retention (fixes D1, the silent recall loss probe), with flat latency as the firehose grows.

Worst-cases are executable here:
  - recall beyond the old scan horizon (the actual bug)
  - empty stream / window entirely before or after all events / lo>hi swap
  - events exactly on each boundary (inclusive)
  - bounded growth (trim evicts oldest payloads in lockstep with the index)
  - backfill: rebuild_index() indexes events captured before the index existed
  - flat latency at N=100k (range-scan, not full replay)
  - graceful fallback: an EventLog with no Store still works (ledger scan)

Isolated: throwaway FileLedger + FileStore. Run: py -m pytest tests/test_event_index.py -q
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.ledger import FileLedger
from core.foundation.store import FileStore
from core.events.event_log import EventLog
from core.events.event_query import EventQuery
from core.events.event_index import EventIndex


def _ledger():
    return FileLedger(base_dir=tempfile.mkdtemp(prefix="evidx_"))


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _indexed_log(store=None):
    """An EventLog whose capture maintains the time index (store provided)."""
    return EventLog(_ledger(), store=store or _store())


def test_recall_beyond_scan_horizon():
    """THE bug (probe C): a small scan must NOT hide older in-window events."""
    el = _indexed_log()
    for i in range(8):
        el.capture("command", f"event {i}", at=f"2026-01-01T0{i}:00:00")
    eq = EventQuery(event_log=el, scan=3)        # tiny scan -- would cap the old path
    got = eq.events_in_window("2026-01-01T00:00:00", "2026-01-01T09:00:00")
    assert len(got) == 8, f"index must return ALL 8 in-window events, got {len(got)}"
    # oldest-first ordering preserved
    assert [e["summary"] for e in got] == [f"event {i}" for i in range(8)]


def test_empty_and_degenerate_windows():
    el = _indexed_log()
    eq = EventQuery(event_log=el, scan=3)
    assert eq.events_in_window("2026-01-01T00:00:00", "2026-01-01T01:00:00") == []  # empty stream
    for i in range(3):
        el.capture("command", f"e{i}", at=f"2026-06-01T0{i}:00:00")
    # window entirely before / after all events
    assert eq.events_in_window("2020-01-01T00:00:00", "2020-01-02T00:00:00") == []
    assert eq.events_in_window("2030-01-01T00:00:00", "2030-01-02T00:00:00") == []
    # lo > hi must be swapped, not return empty
    swapped = eq.events_in_window("2026-06-01T05:00:00", "2026-06-01T00:00:00")
    assert len(swapped) == 3, "lo>hi must swap and still return the window"


def test_inclusive_boundaries():
    el = _indexed_log()
    el.capture("command", "left edge", at="2026-01-01T01:00:00")
    el.capture("command", "middle", at="2026-01-01T02:00:00")
    el.capture("command", "right edge", at="2026-01-01T03:00:00")
    eq = EventQuery(event_log=el, scan=2)
    got = eq.events_in_window("2026-01-01T01:00:00", "2026-01-01T03:00:00")  # inclusive both ends
    assert {e["summary"] for e in got} == {"left edge", "middle", "right edge"}


def test_filters_in_window():
    el = _indexed_log()
    el.capture("file_edit", "edit A", at="2026-01-01T01:00:00", agent_id="alice")
    el.capture("command", "cmd B", at="2026-01-01T02:00:00", agent_id="bob")
    el.capture("file_edit", "edit C", at="2026-01-01T03:00:00", agent_id="bob")
    eq = EventQuery(event_log=el, scan=1)
    span = ("2026-01-01T00:00:00", "2026-01-01T09:00:00")
    assert {e["summary"] for e in eq.events_in_window(*span, kind="file_edit")} == {"edit A", "edit C"}
    assert {e["summary"] for e in eq.events_in_window(*span, agent="bob")} == {"cmd B", "edit C"}
    assert len(eq.events_in_window(*span, limit=2)) == 2


def test_bounded_growth_evicts_oldest_in_lockstep():
    store = _store()
    idx = EventIndex(store, maxlen=5)
    for i in range(12):
        idx.add({"id": f"id{i:02d}", "at": f"2026-01-01T00:{i:02d}:00", "summary": f"e{i}"})
    assert idx.count() == 5, "index capped at maxlen"
    # the 5 survivors are the NEWEST; the evicted payload keys are gone (no byid leak)
    survivors = idx.window("2026-01-01T00:00:00", "2026-01-01T01:00:00")
    assert [e["summary"] for e in survivors] == [f"e{i}" for i in range(7, 12)]
    assert idx.get("id00") is None and idx.get("id06") is None, "evicted payloads deleted"
    assert idx.get("id11") is not None


def test_rebuild_backfills_preexisting_events():
    """Events captured BEFORE an index existed must become queryable after rebuild."""
    ledger = _ledger()
    el_noidx = EventLog(ledger)                  # no store -> no index (old behavior)
    for i in range(6):
        el_noidx.capture("command", f"old {i}", at=f"2026-02-01T0{i}:00:00")
    # now attach an index over the SAME ledger and heal it
    store = _store()
    el = EventLog(ledger, store=store)
    assert el.index.count() == 0, "index starts cold"
    n = el.rebuild_index()
    assert n == 6, f"rebuild must backfill all 6 pre-existing events, got {n}"
    eq = EventQuery(event_log=el, scan=1)
    got = eq.events_in_window("2026-02-01T00:00:00", "2026-02-01T09:00:00")
    assert len(got) == 6, "backfilled events are now window-queryable"


def test_graceful_fallback_without_store():
    """A ledger-only EventLog (no index) still answers windows via the bounded scan."""
    el = EventLog(_ledger())                     # no store
    assert el.index is None
    for i in range(4):
        el.capture("command", f"e{i}", at=f"2026-03-01T0{i}:00:00")
    eq = EventQuery(event_log=el, scan=100)      # scan big enough -> recall holds
    got = eq.events_in_window("2026-03-01T00:00:00", "2026-03-01T09:00:00")
    assert len(got) == 4, "fallback path still correct when scan covers the events"


def test_flat_latency_at_scale():
    """Range-scan beats full replay: a 1-event window over a 100k index must be fast and
    return exactly 1 -- the whole point of the index (no O(n) scan per query)."""
    import json
    from datetime import datetime, timezone
    store = _store()
    idx = EventIndex(store, maxlen=200_000)
    base = 1_750_000_000
    # Build a 100k-entry index in ONE zadd (no per-key flush thrash), and materialize only
    # the single payload our narrow window will actually resolve -- the other 99 999 ids are
    # never fetched because they fall outside the window. This exercises the real query path
    # (zrangebyscore over 100k) without 100k disk writes.
    store.zadd("events:raw:tindex", {f"id{i}": base + i for i in range(100_000)})
    target = base + 50_000
    # Build the iso as tz-aware UTC so to_epoch round-trips back to `target` (the zset score).
    iso = datetime.fromtimestamp(target, tz=timezone.utc).isoformat()
    store.set(f"events:raw:byid:id50000", json.dumps(
        {"id": "id50000", "at": iso, "summary": "needle"}))
    t0 = time.perf_counter()
    got = idx.window(iso, iso)                   # 1-event-wide window deep in the middle
    dt = time.perf_counter() - t0
    assert len(got) == 1 and got[0]["summary"] == "needle", f"exactly the one in-window event, got {got}"
    assert dt < 1.0, f"range-scan must stay fast at 100k (took {dt:.3f}s)"


if __name__ == "__main__":
    for fn in [test_recall_beyond_scan_horizon, test_empty_and_degenerate_windows,
               test_inclusive_boundaries, test_filters_in_window,
               test_bounded_growth_evicts_oldest_in_lockstep,
               test_rebuild_backfills_preexisting_events,
               test_graceful_fallback_without_store, test_flat_latency_at_scale]:
        fn()
    print("ALL V1 TIME-INDEX TESTS PASSED")
