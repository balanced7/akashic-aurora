"""
Tests for the BeatLog (Slice 1) -- Beats accreting on a time-ordered timeline.

Isolated: injects a temp FileStore, so it never touches Redis or canonical data.

Run: py tests/test_narrative_beat_log.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog, TIMELINE
from core.narrative.schema import Edge


def _log():
    return BeatLog(FileStore(os.path.join(tempfile.mkdtemp(), "s.json")))


def test_emit_and_count():
    log = _log()
    b = log.emit("learning", "memoization beat +52%", "learn:experiment:perf",
                 at="2026-06-27T10:00:00")
    assert b is not None and b.kind == "learning" and b.weight == 4  # default for learning
    assert log.count() == 1
    print("  emit + count OK")


def test_source_required_and_kind_coerced():
    log = _log()
    assert log.emit("learning", "no source", "") is None, "source-less beat must be refused"
    b = log.emit("bogus_kind", "x", "git:abc123")
    assert b is not None and b.kind == "note", "unknown kind coerces to 'note'"
    assert log.count() == 1
    print("  source required + kind coercion OK")


def test_time_order_recent_and_window():
    log = _log()
    log.emit("note", "first", "ledger:s:1", at="2026-06-01T09:00:00")
    log.emit("decision", "middle", "ledger:s:2", at="2026-06-15T09:00:00")
    log.emit("milestone", "latest", "git:deadbee", at="2026-06-27T09:00:00")
    recent = log.recent(limit=2)
    assert [b.summary for b in recent] == ["latest", "middle"], "recent = newest first"
    win = log.in_window("2026-06-10T00:00:00", "2026-06-20T00:00:00")
    assert [b.summary for b in win] == ["middle"], "window filters by time"
    print("  recent (newest-first) + time-window OK")


def test_weight_defaults_and_override():
    log = _log()
    assert log.emit("milestone", "m", "git:1").weight == 5
    assert log.emit("commit", "c", "git:2").weight == 2
    assert log.emit("commit", "big", "git:3", weight=4).weight == 4, "override honored"
    print("  weight defaults + override OK")


def test_roundtrip_with_edges():
    log = _log()
    b = log.emit("learning", "themed", "learn:experiment:x",
                 themes=["local-first"], relates=[Edge("member_of", "narr:theme:local-first")])
    loaded = log.recent(1)[0]
    assert loaded.themes == ["local-first"]
    assert loaded.relates[0].type == "member_of" and isinstance(loaded.relates[0], Edge)
    print("  round-trip through the store (themes + edges) OK")


def main():
    print("=" * 60)
    print("BEATLOG TESTS (Slice 1)")
    print("=" * 60)
    test_emit_and_count()
    test_source_required_and_kind_coerced()
    test_time_order_recent_and_window()
    test_weight_defaults_and_override()
    test_roundtrip_with_edges()
    print("\n" + "=" * 60)
    print("ALL BEATLOG TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
