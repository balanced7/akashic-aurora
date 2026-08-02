"""RED FENCE (contract only -- the fix is DELIBERATELY NOT in this commit).

T108 U1: directed mail addressed to an incarnation is UNREACHABLE under the production
consume path. Codex Sol's live receipt, 2026-08-02, reproduced twice:

    "The per-seat stream executes under Bus.inbox(advance=True) ... It does NOT execute
     under BIFROST_CONSUME_LANE=work. work_drain() returned the packet from the work lane
     with _lane_src=work, while the seat-stream copy remained unread. No cursor:seat key
     and no seat_seen key were created."

And the consequence it measured, which is starvation rather than theft:

    "B did not receive A's body when BIFROST_INCARNATION was set; the incarnation filter
     held. B nevertheless advanced the shared work-lane cursor past A's packet. A then
     received nothing, while A's untouched seat stream still contained the packet."

THE GATE, core/comm/bus.py:806::

    if sid8 and since is None and streams is None:

Lane consumption always passes ``streams`` (bifrost_api.work_drain -> _lane_streams), so
the seat read is switched off in exactly the configuration the fleet actually runs. T108
slice 1 shipped the seat stream and the production path has never once read it.

WHY THE FIX IS NOT HERE. Reading the seat stream is the easy half and is nearly risk-free
on its own (codex measured ZERO cursor:seat keys, so it is a stream that only accumulates).
The dangerous half is the CURSOR: a seat read with no advance redelivers forever, which is
the wake-loop class that cost this project ~7 model turns in one night. A half-fix would be
worse than the defect. These pins therefore state the whole contract -- including the
advance -- so whoever implements it cannot ship only the safe half and call it done.

Run::

    py -m pytest tests/test_t108_u1_seat_stream_under_lane.py -q
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NS = "test-u1seat"
pytestmark = pytest.mark.xfail(
    reason="T108 U1 CONTRACT, not yet implemented: work_drain does not read the seat "
           "stream (bus.py:806 disables it whenever `streams` is passed). Committed RED "
           "as a pre-registered acceptance; remove this marker with the fix.",
    strict=True)


def _api(agent, incarnation):
    """A lane-consuming API for one incarnation, exactly as a runner constructs it."""
    os.environ["BIFROST_INCARNATION"] = incarnation
    os.environ["BIFROST_CONSUME_LANE"] = "work"
    from core.comm.bifrost_api import BifrostAPI
    return BifrostAPI(agent)


def test_directed_mail_reaches_its_incarnation_under_lane_consume():
    """THE DEFECT. A packet addressed to seat A must be readable by A while A consumes
    in lane mode -- the only mode production runs."""
    from core.comm.bus import Bus
    sender = Bus("sender", namespace=NS)
    a = _api("worker", "aaaaaaaa")
    sender.send("worker", "handoff", "for A only", meta={"to_incarnation": "aaaaaaaa"})

    got = a.work_drain(timeout_ms=50, limit=10)

    bodies = [str(getattr(m, "content", "")) for m in got]
    assert any("for A only" in b for b in bodies), (
        "directed mail invisible under CONSUME_LANE=work -- the seat stream holds it and "
        "the production consume path never reads it (bus.py:806)")


def test_seat_sourced_mail_is_labelled_seat():
    """Every source in work_drain stamps _lane_src so the consumer knows which cursor it
    may advance (sig auto-advances, work does not, legacy is a shadow). The seat stream is
    a FOURTH source and must be distinguishable, or a consumer will advance the wrong
    cursor and either lose mail or replay it."""
    from core.comm.bus import Bus
    sender = Bus("sender", namespace=NS)
    a = _api("worker2", "bbbbbbbb")
    sender.send("worker2", "handoff", "seat labelled", meta={"to_incarnation": "bbbbbbbb"})

    got = a.work_drain(timeout_ms=50, limit=10)
    seat_msgs = [m for m in got if (getattr(m, "meta", {}) or {}).get("_lane_src") == "seat"]

    assert seat_msgs, f"no message carried _lane_src=seat; got {[(getattr(m,'meta',{}) or {}).get('_lane_src') for m in got]}"


def test_a_twin_cannot_starve_the_seat():
    """CODEX'S MEASURED SCENARIO, and the reason this matters. Two incarnations of one
    agent: B drains and advances the SHARED work-lane cursor past a packet directed at A.
    A must still receive it -- its own seat stream is untouched and is precisely the
    recovery path T108 slice 1 was built to provide."""
    from core.comm.bus import Bus
    sender = Bus("sender", namespace=NS)
    a = _api("worker3", "cccccccc")
    sender.send("worker3", "handoff", "addressed to A", meta={"to_incarnation": "cccccccc"})

    b = _api("worker3", "dddddddd")      # the twin
    b.work_drain(timeout_ms=50, limit=10)          # B sweeps the shared lane cursor forward

    got = a.work_drain(timeout_ms=50, limit=10)
    assert any("addressed to A" in str(getattr(m, "content", "")) for m in got), (
        "a twin advancing the shared cursor STARVED the addressee -- delivery ownership "
        "failed even though the incarnation filter prevented content theft")


def test_seat_cursor_advances_only_after_processing():
    """THE HALF THAT MUST NOT BE SKIPPED. Directed mail is at-least-once: the seat cursor
    advances AFTER the consumer processes (RB-26 commit-after-processing), never
    automatically on read. Auto-advancing loses mail on a crash; never advancing
    redelivers forever, which is the wake-loop class. Draining twice without an explicit
    advance must therefore return the packet BOTH times."""
    from core.comm.bus import Bus
    sender = Bus("sender", namespace=NS)
    a = _api("worker4", "eeeeeeee")
    sender.send("worker4", "handoff", "redeliver me", meta={"to_incarnation": "eeeeeeee"})

    first = a.work_drain(timeout_ms=50, limit=10)
    second = a.work_drain(timeout_ms=50, limit=10)

    def has(ms):
        return any("redeliver me" in str(getattr(m, "content", "")) for m in ms)

    assert has(first), "first drain did not deliver"
    assert has(second), (
        "the seat cursor auto-advanced on read -- a crash between read and processing "
        "would lose the message (RB-26 requires commit-after-processing)")
