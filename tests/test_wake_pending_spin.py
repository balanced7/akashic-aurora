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
        self.ns = "test"  # needed by _lane_streams -> packet_spec.lane_stream_key

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


def test_seeding_over_undrainable_mail_is_ANNOUNCED(caplog, monkeypatch):
    """kimi's (d): the fix silences a loud symptom, so the alarm must move, not vanish.

    Before the fix the undrainable-mail condition announced itself at 20% of a core and a
    twin counter in the millions. Seeding makes the watcher block quietly while the SAME
    mail sits pending forever -- and it can mask newer mail behind it (deepseek's
    missed-wake attack). Without this warning the fix is the workaround Daniel's standing
    rule forbids: it removes the alarm without removing the condition.
    """
    import logging
    bus = _Bus([_Msg()])
    api = _api(bus)
    monkeypatch.setattr(api, "_lane_tails", lambda: {"work": "0-0"}, raising=False)
    monkeypatch.setattr(api, "_lane_streams", lambda: {"inbox": "s"}, raising=False)

    with caplog.at_level(logging.WARNING, logger="bifrost"):
        api._wake_block_lane(timeout_ms=1)

    assert any("undrainable" in r.getMessage() for r in caplog.records), (
        "seeding over non-empty pending was SILENT -- the condition persists with no signal"
    )
    assert api._pending_at_seed == 1


def test_quiet_seed_does_not_cry_wolf(caplog, monkeypatch):
    """The marker must fire ONLY on the real condition, or it becomes noise people mute."""
    import logging
    bus = _Bus([])
    api = _api(bus)
    monkeypatch.setattr(api, "_lane_tails", lambda: {"work": "0-0"}, raising=False)
    monkeypatch.setattr(api, "_lane_streams", lambda: {"inbox": "s"}, raising=False)

    with caplog.at_level(logging.WARNING, logger="bifrost"):
        api._wake_block_lane(timeout_ms=1)

    assert not [r for r in caplog.records if "undrainable" in r.getMessage()], (
        "a clean seed on a quiet bus must stay silent"
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


# ---- (c) DEEPSEEK: peek-count invariant audit ----------------------------------
def test_peek_count_passes_but_cpu_spin_could_still_live_elsewhere(monkeypatch):
    """(c) Can the peek-count invariant pass while real spin persists through another path?

    The test asserts on PEEK COUNT on the Bus.wait() path with `since=None` (the shared-
    cursor peek). That catches the _wake_block_lane hot loop. But a hot spin could also
    live OUTSIDE the fake bus in the real codebase:

    1. The CALLER (bifrost_wake.watch) dedupes batches as twins (S0-gamma). If the lane
       read returns non-empty batches that are all twins, the caller loops. The fake bus
       returns [] from its lane read, so this path is untested here.
    2. work_drain's sig-first drain could spin if sig-lane mail is permanently pending
       (skip-kind on the sig lane). That's a different path -- not _wake_block_lane.
    3. The RB-26 redelivery path: if the lane cursor advance fails, the same batch
       redelivers, and a naive caller would loop. The fake bus bypasses this.

    VERDICT: peek-count is a NECESSARY but not SUFFICIENT invariant. It catches the
    mechanism Claude measured (shared-cursor re-peek). It does NOT catch caller-level
    loops from twin dedup, sig-lane spin, or failed-advance redelivery. Each of those
    needs its own pin. The S0-gamma dedup pins exist; sig-lane and advance-failure
    loops are gaps.

    This test documents the gap -- it does not fail because peek-count IS correct
    for the seam it guards. But a green peek-count test is not proof the CPU is idle."""
    bus = _Bus([_Msg()])
    api = _api(bus)
    monkeypatch.setattr(api, "_lane_tails", lambda: {"work": "0-0"}, raising=False)
    monkeypatch.setattr(api, "_lane_streams", lambda: {"inbox": "s"}, raising=False)
    # Simulate: caller-level spin from twin dedup while lane read returns non-empty
    call_count = 0
    for _ in range(10):
        msgs = api._wake_block_lane(timeout_ms=1)
        call_count += 1
        if not msgs:
            break
    # With the fix, delivery happens once then the lane read blocks (returns [])
    assert call_count <= 2, (
        f"_wake_block_lane delivered {call_count} times before blocking -- "
        f"a caller-level spin would amplify this"
    )
    # But NOTE: a REAL caller with twin dedup could still spin if bus.wait(lane)
    # returned non-empty every time. This test's fake bus returns [] from lane
    # reads, so we can't assert on the caller here. The invariant holds at the
    # _wake_block_lane seam; caller-level spinning is a SEPARATE risk.


# ---- (a) DEEPSEEK: missed-wake attack ------------------------------------------
class _PhaseBus:
    """Bus that can change its pending set between calls -- for the missed-wake attack.

    Phase 1: wake-worthy mail pending (triggers the arm-time peek + seed)
    Phase 2: NEW mail lands on shared cursor ONLY (simulates dual-write partial:
             legacy write succeeded, work-lane write failed -- a straggler).
    The lane read always returns [] (simulating no work-lane traffic)."""

    def __init__(self):
        self.shared_pending = [_Msg(kind="request", frm="claude")]
        self.peeks = 0
        self.lane_waits = 0
        self.phase = 1

    def wait(self, timeout_ms=0, limit=None, since=None, since_out=None, streams=None):
        if since is None:                 # shared-cursor peek
            self.peeks += 1
            return list(self.shared_pending)
        # lane blocking read -- simulate empty work lane
        self.lane_waits += 1
        return []

    def cursor(self):
        return {}

    def tail(self):
        return {}


def test_new_mail_on_shared_cursor_between_calls_missed_by_lane_watcher(monkeypatch):
    """(a) Construct a case where the OLD code would deliver a wake the NEW code misses.

    SETUP: Phase 1 has wake-worthy mail (request). Phase 2 adds NEW mail (another
    request) on the shared cursor ONLY -- a legacy-lane straggler whose work-lane
    twin failed. In the OLD code, every call while _lane_since is None re-peeks the
    shared cursor and would catch the Phase 2 mail. In the NEW code, the lane
    watcher seeds after Phase 1 and only watches the (empty) work lane thereafter.

    This is NOT necessarily a bug: work_drain's legacy straggler net (R2) catches
    legacy-only mail when the consumer next runs. The watcher already woke the agent
    from Phase 1. But it IS a semantic narrowing the reviewer must see."""
    bus = _PhaseBus()
    api_new = _api(bus)
    monkeypatch.setattr(api_new, "_lane_tails", lambda: {"work": "0-0"}, raising=False)
    monkeypatch.setattr(api_new, "_lane_streams", lambda: {"inbox": "s"}, raising=False)

    # --- NEW code path ---
    first = api_new._wake_block_lane(timeout_ms=1)
    assert len(first) == 1 and first[0].kind == "request"
    assert bus.peeks == 1
    assert api_new._lane_since is not None, "seeded after first delivery"

    # Phase 2: NEW mail on shared cursor only (straggler)
    bus.shared_pending.append(_Msg(kind="request", frm="kimi"))

    second = api_new._wake_block_lane(timeout_ms=1)
    assert second == [], "lane read empty -- Phase 2 straggler invisible to lane watcher"
    assert bus.peeks == 1, "shared cursor NOT re-peeked"
    assert bus.lane_waits >= 1, "blocking lane read happened"

    # --- OLD code path (same starting state, separate bus) ---
    bus2 = _PhaseBus()
    api_old = _api(bus2)
    monkeypatch.setattr(api_old, "_lane_tails", lambda: {"work": "0-0"}, raising=False)
    monkeypatch.setattr(api_old, "_lane_streams", lambda: {"inbox": "s"}, raising=False)
    # Simulate old code: never seed _lane_since
    original_block_lane = api_old._wake_block_lane

    def old_wake_block_lane(timeout_ms):
        if api_old._lane_since is None:
            pending = api_old.bus.wait(timeout_ms=1, limit=10)
            from core.comm.bifrost_api import PENDING_SKIP_KINDS
            live = [m for m in pending
                    if str(getattr(m, "kind", "")) not in PENDING_SKIP_KINDS]
            # OLD: return WITHOUT seeding
            if live:
                return live
        nxt = {}
        msgs = api_old.bus.wait(timeout_ms=timeout_ms, since=api_old._lane_since,
                                since_out=nxt, streams=api_old._lane_streams())
        if nxt:
            api_old._lane_since.update(nxt)
        return msgs

    # Phase 1 for old code: finds Phase 1 mail
    old_first = old_wake_block_lane(timeout_ms=1)
    assert len(old_first) == 1 and old_first[0].kind == "request"
    assert api_old._lane_since is None, "OLD code: still unseeded after delivery"

    # Phase 2: add straggler
    bus2.shared_pending.append(_Msg(kind="request", frm="kimi"))

    # Old code's second call: re-peeks shared cursor, finds BOTH (Phase 1 never
    # consumed — detect-only — so it's still there alongside Phase 2)
    old_second = old_wake_block_lane(timeout_ms=1)
    assert len(old_second) == 2 and any(m.frm == "kimi" for m in old_second), (
        f"OLD code re-peeked shared cursor and found BOTH messages ({len(old_second)}); "
        f"the Phase 2 straggler would have been delivered as a wake. "
        f"NEW code missed it (lane-only read after seed)"
    )

    # THE MITIGATION (documented): work_drain's legacy straggler net (R2) catches
    # this. The watcher already woke the agent from Phase 1. For a straggler that
    # arrives during a QUIET period: the watcher disarms and rearms periodically
    # (T073 self-cycle), so the NEXT arm-time pending check catches it. The window
    # is: straggler lands while watcher is armed AND no other mail wakes it AND
    # the straggler isn't caught by work_drain before the consumer idles again.
    # This is narrow and accepted.
