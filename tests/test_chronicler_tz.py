"""
Slice D4 -- timezone-safe chronicler comparison.

Bar: mixed naive/tz-aware timestamps sort by true instant and measure real gaps, instead of
string-mis-sorting and silently collapsing a cross-tz gap to 0.0 (the swallowed TypeError the
probe exposed). Strict no-regression: all-naive data behaves exactly as before.

Run: py -m pytest tests/test_chronicler_tz.py -q
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.foundation.timeutil import to_epoch, hours_between
from core.narrative.beat_log import BeatLog
from core.narrative.track_router import RouteHint
from core.narrative.chronicler import Chronicler, BoundaryDetector
from core.narrative.schema import Beat


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _chronicler(bl, store):
    # isolate the rendered story so tests never touch the real chronicles/ dir
    return Chronicler(beat_log=bl, store=store, chronicle_dir=tempfile.mkdtemp(prefix="chron_"))


def _beat(at):
    return Beat(id=f"b{at}", at=at, kind="note", summary="x", source="s", weight=1, track="ai-setup")


def test_to_epoch_naive_is_utc_deterministic():
    assert to_epoch("2026-01-01T00:00:00") == to_epoch("2026-01-01T00:00:00+00:00")
    # a -05:00 instant is LATER than the same wall-clock read as UTC -- string sort gets this wrong
    assert to_epoch("2026-01-01T10:00:00-05:00") > to_epoch("2026-01-01T12:00:00")
    assert "2026-01-01T10:00:00-05:00" < "2026-01-01T12:00:00"     # the WRONG string order, for contrast
    assert to_epoch("garbage") == 0.0


def test_hours_between_is_tz_safe_not_zero():
    # naive vs tz-aware -- the old code raised TypeError here and swallowed it to 0.0
    gap = hours_between("2026-01-01T10:00:00", "2026-01-01T16:00:00+00:00")
    assert abs(gap - 6.0) < 1e-6, f"cross-tz gap must be 6h, got {gap}"


def test_boundary_detected_across_mixed_tz_gap():
    """A >min_gap gap between a naive and a tz-aware beat MUST cut a chapter (was silently missed)."""
    bd = BoundaryDetector(min_gap_hours=4.0)
    assert bd.detect([_beat("2026-01-01T10:00:00"), _beat("2026-01-01T16:00:00+00:00")]) == [0, 1]  # 6h
    assert bd.detect([_beat("2026-01-01T10:00:00"), _beat("2026-01-01T11:00:00+00:00")]) == [0]     # 1h


def test_chronicle_segments_mixed_tz_correctly():
    store = _store(); bl = BeatLog(store)
    bl.emit("commit", "morning", "git:a", at="2026-01-01T10:00:00", hint=RouteHint(paths=["core/x.py"]))
    bl.emit("commit", "evening", "git:b", at="2026-01-01T16:00:00+00:00", hint=RouteHint(paths=["core/x.py"]))
    rep = _chronicler(bl, store).chronicle_all(now="2026-01-02T00:00:00")
    assert rep["total_beats"] == 2
    assert rep["chapters"] == 2, f"the 6h cross-tz gap should yield 2 chapters, got {rep['chapters']}"


def test_all_naive_unchanged_regression():
    """The fix must not alter all-naive behavior (the offset cancels in sorts and gaps)."""
    store = _store(); bl = BeatLog(store)
    bl.emit("commit", "a", "git:a", at="2026-01-01T10:00:00", hint=RouteHint(paths=["core/x.py"]))
    bl.emit("commit", "b", "git:b", at="2026-01-01T10:30:00", hint=RouteHint(paths=["core/x.py"]))  # 30m
    rep = _chronicler(bl, store).chronicle_all(now="2026-01-02T00:00:00")
    assert rep["chapters"] == 1, "two close all-naive beats stay one chapter"


def test_out_of_order_mixed_tz_sorts_by_instant():
    """Beats handed in the wrong order, with different offsets, chronicle in true-instant order.
    10:00-05:00 == 15:00Z, which is AFTER 12:00Z(naive). 3h apart -> one chapter, ordered."""
    store = _store(); bl = BeatLog(store)
    bl.emit("commit", "later", "git:late", at="2026-01-01T10:00:00-05:00", hint=RouteHint(paths=["core/x.py"]))
    bl.emit("commit", "earlier", "git:early", at="2026-01-01T12:00:00", hint=RouteHint(paths=["core/x.py"]))
    chron = _chronicler(bl, store)
    chron.chronicle_all(now="2026-01-02T00:00:00")
    idx = json.loads((chron.chronicle_dir / "story.index.json").read_text(encoding="utf-8"))
    commits = [c for ch in idx["chapters"] for c in ch["commits"]]
    assert commits == ["git:early", "git:late"], f"true-instant order expected, got {commits}"


if __name__ == "__main__":
    for fn in [test_to_epoch_naive_is_utc_deterministic, test_hours_between_is_tz_safe_not_zero,
               test_boundary_detected_across_mixed_tz_gap, test_chronicle_segments_mixed_tz_correctly,
               test_all_naive_unchanged_regression, test_out_of_order_mixed_tz_sorts_by_instant]:
        fn()
    print("ALL D4 TZ TESTS PASSED")
