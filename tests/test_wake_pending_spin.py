"""Pin: the wake watcher must not hot-spin while unconsumed mail is pending.

MEASURED 2026-07-25, live: an armed wake watcher burned 20% of one core CONTINUOUSLY while
idle, and reported "6,202,600 twin(s) deduped" over a 3.97h lifetime -- roughly 430 logical
duplicates per second on what is documented as a blocking read that costs ~nothing
(lesson: bifrost_event_driven_wake -- "blocks ~free until a message").

THE MECHANISM, in BifrostAPI._wake_block_lane:
  - on the first call `_lane_since` is None, so it does a 1ms PEEK at the shared cursor;
  - if that peek finds any wake-worthy pending mail it RETURNS IT IMMEDIATELY --
    without seeding `_lane_since`;
  - so the next call peeks again, finds the SAME mail (detect-only never consumes, by
    design: T017), and returns instantly again.

The blocking read therefore never blocks for as long as any wake-worthy mail sits
unconsumed on the shared cursor. The caller dedupes each batch as logical twins and loops
at full speed -- a hot spin whose only external symptom is a large twin counter and a warm
CPU. Claude had 26 unread at the time of measurement.

THE FIX: seed `_lane_since` BEFORE returning the pending batch. The pending mail is still
delivered exactly once (nothing is lost -- detect-only leaves it on the shared cursor for
the real consumer), and every subsequent call goes down the genuinely blocking lane path.

This pin asserts the SEAM, not the CPU: a second call with the same pending mail must not
re-peek. Timing assertions would be flaky; the state transition is exact.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.comm.bifrost_api import BifrostAPI  # noqa: E402


class _Msg:
    def __init__(self, kind="handoff", frm="deepseek"):
        self.kind, self.frm = kind, frm
        self.ts, self.content, self.meta, self.to = "2026-07-25T00:00:00+00:00", "x", {}, "claude"


class _Bus:
    """Minimal bus: a permanently-pending shared cursor, and a lane read that BLOCKS."""

    def __init__(self, pending):
        self.pending = list(pending)
        self.peeks = 0
        self.lane_waits = 0

    def wait(self, timeout_ms=0, limit=None, since=None, since_out=None, streams=None):
        if since is None:                 # the shared-cursor peek path
            self.peeks += 1
            return list(self.pending)     # detect-only: never drains
        self.lane_waits += 1              # the real blocking lane read
        return []

    def cursor(self):
        return {}

    def tail(self):
        return {}


def _api(bus):
    api = BifrostAPI.__new__(BifrostAPI)
    api.agent = "claude"
    api.bus = bus
    api._lane_since = None
    return api


def test_pending_mail_is_delivered_once_then_the_watcher_blocks(monkeypatch):
    bus = _Bus([_Msg()])
    api = _api(bus)
    monkeypatch.setattr(api, "_lane_tails", lambda: {"work": "0-0"}, raising=False)
    monkeypatch.setattr(api, "_lane_streams", lambda: {"inbox": "s"}, raising=False)

    first = api._wake_block_lane(timeout_ms=1)
    assert first, "wake-worthy pending mail must still wake the watcher the first time"
    assert bus.peeks == 1

    for _ in range(5):
        api._wake_block_lane(timeout_ms=1)

    assert bus.peeks == 1, (
        f"the shared cursor was re-peeked {bus.peeks} times -- pending mail that never "
        f"drains makes every call return instantly, which is the 20%-of-a-core hot spin"
    )
    assert bus.lane_waits >= 5, (
        "after the first delivery every call must go down the BLOCKING lane read"
    )


def test_a_quiet_bus_still_seeds_and_blocks(monkeypatch):
    """Regression guard: the no-pending path must keep working exactly as before."""
    bus = _Bus([])
    api = _api(bus)
    monkeypatch.setattr(api, "_lane_tails", lambda: {"work": "0-0"}, raising=False)
    monkeypatch.setattr(api, "_lane_streams", lambda: {"inbox": "s"}, raising=False)

    assert api._wake_block_lane(timeout_ms=1) == []
    assert api._lane_since is not None, "a quiet peek must seed the lane cursor"
    assert bus.lane_waits == 1


def test_skip_kind_pending_does_not_count_as_wake_worthy(monkeypatch):
    """Pre-existing behaviour (L7 parity) must survive the fix: trace junk never wakes."""
    from core.comm.bifrost_api import PENDING_SKIP_KINDS
    junk = next(iter(PENDING_SKIP_KINDS)) if PENDING_SKIP_KINDS else None
    if junk is None:
        return
    bus = _Bus([_Msg(kind=junk)])
    api = _api(bus)
    monkeypatch.setattr(api, "_lane_tails", lambda: {"work": "0-0"}, raising=False)
    monkeypatch.setattr(api, "_lane_streams", lambda: {"inbox": "s"}, raising=False)

    assert api._wake_block_lane(timeout_ms=1) == []
    assert api._lane_since is not None, "skip-kind pending must not trap the seed"
