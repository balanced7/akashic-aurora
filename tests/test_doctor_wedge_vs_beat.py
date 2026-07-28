"""Doctor wedge predicate pins -- RED first (M3).

THE DEFECT, self-demonstrated 2026-07-28: the doctor PAGED "claude#7d0ede0e: HARD WEDGE --
'sync' for 307s with a DEAD pulse" against the seat that was actively building, committing
and heartbeating the whole time. Two organs disagreeing, and the alarm believed the wrong one.

MECHANISM (doctor.py:295): `stuck = now - worklive.since_ts` -- since_ts is PHASE-ENTRY time
and is deliberately NOT refreshed by heartbeats (roster.heartbeat preserves it so "how long
in this phase" stays meaningful). So a seat that beats every turn while staying in one phase
looks arbitrarily "stuck" -- and the RB-27a progress pulse is a RUNNER organ that live seats
never write, so pulse_fresh is False for every seat by construction. Non-idle + old since_ts
+ no runner pulse = PAGE, forever, on a perfectly healthy seat.

This is the confident-zero disease wearing an alarm: a false page trains the fleet to ignore
pages, which is exactly how the real HARD WEDGE (deepseek's streams.py flush hang, same hour)
gets missed. The lesson hard_wedge_pages_hide_two_different_failures named this half; these
pins close it.

  P1  A BEATING SEAT IS NEVER WEDGED: fresh worklive beat (beat_ts recent) => no page, even
      with an ancient since_ts and no runner pulse. The beat IS the liveness evidence for a
      seat; demanding a runner-only organ from a non-runner is the category error.
  P2  A GENUINELY DEAD SEAT STILL PAGES: old since_ts AND stale beat AND no pulse => the
      page survives. Fixing the false positive must not blind the true one.
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENT = f"docpin_{uuid.uuid4().hex[:6]}"


def _examine(worklive, progress=None):
    from core.comm import doctor
    return doctor.examine(AGENT, probes={
        "now": time.time(),
        "worklive": lambda a: worklive,
        "progress": lambda a: progress,
    })


def _kinds(findings):
    # examine() returns findings keyed 'state' (not 'kind') -- read the producer, do not
    # assume the field name (fresh_eyes_read_the_label_generator_first).
    return {(f.get("state"), f.get("grade")) for f in findings}


def test_p1_beating_seat_never_pages_as_wedged():
    now = time.time()
    # A live seat: entered 'sync' an hour ago, has been beating every few seconds since,
    # and (being a seat, not a runner) writes NO RB-27a progress pulse.
    wl = {"phase": "sync", "since_ts": now - 3600, "beat_ts": now - 3}
    found = _examine(wl, progress=None)
    assert ("hard_wedge", "page") not in _kinds(found), (
        f"FALSE WEDGE PAGE: a seat beating 3s ago was paged as HARD WEDGE because since_ts "
        f"(phase entry) is old and it writes no runner pulse. The beat is the seat's liveness "
        f"evidence; demanding a runner organ from a non-runner is a category error -- and a "
        f"false page trains the fleet to ignore the real one. Findings: {found}")


def test_p2_truly_dead_seat_still_pages():
    now = time.time()
    # Genuinely dead: old phase entry, NO recent beat, no pulse.
    wl = {"phase": "thinking", "since_ts": now - 3600, "beat_ts": now - 3600}
    found = _examine(wl, progress=None)
    assert ("hard_wedge", "page") in _kinds(found), (
        f"MISSED REAL WEDGE: a seat with an old phase AND a stale beat AND no pulse must "
        f"still page -- silencing the false positive must not blind the true one. "
        f"Findings: {found}")


if __name__ == "__main__":
    test_p1_beating_seat_never_pages_as_wedged()
    test_p2_truly_dead_seat_still_pages()
    print("PASS")
