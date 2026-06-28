"""
Slice W-c -- narrative health counters.

Bar: the best-effort paths become OBSERVABLE -- a successful route records which signal fired,
and a FORCED routing failure leaves a visible `route:error` trace instead of a silent no-op.
And the counters themselves are bullet-proof: bumping never raises into the path it observes.

Run: py -m pytest tests/test_narrative_health.py -q
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.health import bump, snapshot, reset, HEALTH_KEY
from core.narrative.beat_log import BeatLog
from core.narrative.track_router import RouteHint


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def test_bump_and_snapshot():
    store = _store()
    bump(store, "route:path")
    bump(store, "route:path")
    bump(store, "route:error", 3)
    snap = snapshot(store)
    assert snap["route:path"] == 2 and snap["route:error"] == 3
    # a non-int counter value is tolerated, not fatal
    store.hset(HEALTH_KEY, "weird", "abc")
    assert snapshot(store)["weird"] == "abc"
    reset(store)
    assert snapshot(store) == {}


def test_emit_records_which_signal_routed():
    """A successful route is observable: routing a commit by path bumps route:path."""
    store = _store(); bl = BeatLog(store)
    bl.emit("commit", "core change", "git:a", at="2026-01-01T00:00:00", hint=RouteHint(paths=["core/x.py"]))
    snap = snapshot(store)
    assert snap.get("route:path", 0) >= 1, f"expected a route:path counter, got {snap}"


def test_forced_routing_failure_is_visible():
    """The whole point of W-c: a routing exception no longer vanishes -- it bumps route:error."""
    import core.narrative.track_router as tr
    store = _store(); bl = BeatLog(store)

    class Boom:
        def route_one(self, *a, **k):
            raise RuntimeError("induced routing failure")

    orig = tr.get_track_router
    tr.get_track_router = lambda: Boom()
    try:
        beat = bl.emit("commit", "x", "git:x", at="2026-01-01T00:00:00", hint=RouteHint(paths=["core/x.py"]))
    finally:
        tr.get_track_router = orig
    assert beat is not None, "emit still succeeds (best-effort) even when routing blows up"
    assert snapshot(store).get("route:error", 0) >= 1, "the silent failure is now counted + visible"


def test_counters_never_raise():
    """A counter hiccup must never propagate into the host path."""
    class BadStore:
        def hget(self, *a, **k): raise RuntimeError("down")
        def hset(self, *a, **k): raise RuntimeError("down")
        def hgetall(self, *a, **k): raise RuntimeError("down")
        def delete(self, *a, **k): raise RuntimeError("down")

    bump(BadStore(), "x")          # must not raise
    bump(None, "x")                # None store -> no-op
    bump(_store(), "")             # empty metric -> no-op
    assert snapshot(BadStore()) == {}
    assert snapshot(None) == {}
    reset(BadStore())              # must not raise


if __name__ == "__main__":
    for fn in [test_bump_and_snapshot, test_emit_records_which_signal_routed,
               test_forced_routing_failure_is_visible, test_counters_never_raise]:
        fn()
    print("ALL W-c HEALTH TESTS PASSED")
