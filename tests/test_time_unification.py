"""
Slice S5 -- one time function, and the re-score migration.

Bar: the six former `_epoch` copies all ARE `timeutil.to_epoch` now (true collapse, not parallel
copies); to_epoch is a drop-in (handles the numeric input `reinforce` passes); and the migration
re-scores the persisted zsets correctly + idempotently so windowed queries keep working after the
naive=UTC switch.

Run: py -m pytest tests/test_time_unification.py -q
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from core.foundation.store import FileStore
from core.foundation.timeutil import to_epoch
from core.narrative.beat_log import BeatLog
from core.narrative.track_router import RouteHint
from core.events.event_log import EventLog
from core.foundation.ledger import FileLedger
from migrate_time_scores import migrate_time_scores, TIMELINE, TINDEX


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def test_to_epoch_numeric_passthrough():
    assert to_epoch(1750000000) == 1750000000.0
    assert to_epoch(1750000000.5) == 1750000000.5     # the float `reinforce` passes
    assert to_epoch("2026-01-01T00:00:00") == to_epoch("2026-01-01T00:00:00+00:00")
    assert to_epoch("garbage") == 0.0


def test_all_copies_collapsed_to_one_fn():
    """The six modules must now share the SAME function object (no parallel _epoch copies)."""
    from core.events.event_query import _epoch as eq
    from core.events.event_index import _epoch as ei
    from core.narrative.beat_log import _epoch as bl
    from core.narrative.tag_governance import _epoch as tg
    from core.perspectives.reinforce import _epoch as rf
    for fn in (eq, ei, bl, tg, rf):
        assert fn is to_epoch, "each module's _epoch must be timeutil.to_epoch"
    # tag_audit's dead _epoch was removed entirely
    import core.narrative.tag_audit as ta
    assert not hasattr(ta, "_epoch"), "tag_audit's dead _epoch should be gone"


def test_migration_rescores_to_unified_epoch():
    store = _store(); bl = BeatLog(store)
    bl.emit("commit", "a", "git:a", at="2026-01-01T01:00:00", hint=RouteHint(paths=["core/x.py"]))
    bl.emit("commit", "b", "git:b", at="2026-01-01T05:00:00", hint=RouteHint(paths=["core/x.py"]))
    # tamper the timeline scores to garbage (simulating old local-interpreted / stale scores)
    ids = store.zrange(TIMELINE, 0, -1)
    store.zadd(TIMELINE, {bid: 999.0 for bid in ids})
    rep = migrate_time_scores(store)
    assert rep["timeline"] == 2
    # every score now equals to_epoch(beat.at)
    from core.narrative.schema import beat_key, Beat
    import json
    for bid, score in store.zrange(TIMELINE, 0, -1, withscores=True):
        b = Beat.from_dict(json.loads(store.get(beat_key(bid))))
        assert score == to_epoch(b.at), f"{bid} not re-scored"
    # idempotent: a second run yields identical scores
    before = dict(store.zrange(TIMELINE, 0, -1, withscores=True))
    migrate_time_scores(store)
    after = dict(store.zrange(TIMELINE, 0, -1, withscores=True))
    assert before == after, "migration must be idempotent"


def test_migration_restores_window_query_after_skew():
    """The actual point: after tampering scores, a window query misses events; migration fixes it."""
    from core.events.event_query import EventQuery
    # an indexed log on a shared store so the migration can re-score the tindex
    store = _store()
    el = EventLog(FileLedger(base_dir=tempfile.mkdtemp(prefix="s5_")), store=store)
    for i in range(4):
        el.capture("command", f"e{i}", at=f"2026-03-01T0{i}:00:00")
    eq = EventQuery(event_log=el, scan=1)
    span = ("2026-03-01T00:00:00", "2026-03-01T09:00:00")
    assert len(eq.events_in_window(*span)) == 4
    # tamper the tindex scores -> the window now misses them
    ids = store.zrange(TINDEX, 0, -1)
    store.zadd(TINDEX, {eid: 1.0 for eid in ids})
    assert len(eq.events_in_window(*span)) == 0, "skewed scores break the window (the bug)"
    # migrate -> recall restored
    migrate_time_scores(store)
    assert len(eq.events_in_window(*span)) == 4, "migration restores window recall"


def test_reinforce_decay_unaffected_for_naive():
    """reinforce's elapsed = now - last cancels the offset for all-naive inputs (no regression)."""
    from core.perspectives.reinforce import ReinforcedGraph
    g = ReinforcedGraph(_store(), half_life_seconds=3600)
    g.reinforce("a", "b", now="2026-01-01T00:00:00")
    s0 = g.strength("a", "b", now="2026-01-01T00:00:00")
    s1 = g.strength("a", "b", now="2026-01-01T01:00:00")   # one half-life later
    assert s1 < s0 and abs(s1 - s0 * 0.5) < 1e-6, "half-life decay still correct on naive iso"


if __name__ == "__main__":
    for fn in [test_to_epoch_numeric_passthrough, test_all_copies_collapsed_to_one_fn,
               test_migration_rescores_to_unified_epoch, test_migration_restores_window_query_after_skew,
               test_reinforce_decay_unaffected_for_naive]:
        fn()
    print("ALL S5 TIME-UNIFICATION TESTS PASSED")
