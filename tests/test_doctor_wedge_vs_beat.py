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

  P1  A BEATING SEAT IS NEVER WEDGED: fresh worklive beat => no page, even with an ancient
      since_ts and no runner pulse. The beat IS work evidence for a SEAT (per-incarnation,
      single-threaded per turn, written by the turn itself).
  P2  A GENUINELY DEAD SEAT STILL PAGES: old since_ts AND stale beat AND no pulse => the
      page survives. Fixing the false positive must not blind the true one.
  P3  A RUNNER'S BEAT NEVER RETRACTS A PAGE (Sol's NO-GO on v1): a runner heartbeats on its
      OWN THREAD, so the beat proves PROCESS liveness, never WORK progress -- py-spy caught
      deepseek's MainThread hung in streams.py flush while its heartbeat thread beat on.
      For a bare agent id the progress pulse governs, unchanged.
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SEAT-shaped id (agent#sid8) -- the false page named "claude#7d0ede0e"; only a
# per-incarnation seat may retract a page with its beat (P3 pins the runner case).
AGENT = f"docpin#{uuid.uuid4().hex[:8]}"


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


def test_p3_runner_beat_thread_never_masks_a_real_wedge():
    """Sol's NO-GO on a12345f, and it is the sharpest finding of the arc: a RUNNER's
    heartbeat runs on its OWN THREAD (py-spy proved it live -- deepseek's MainThread blocked
    in streams.py flush while 'Thread-3 (_heartbeat)' kept beating). So for a runner the beat
    proves PROCESS liveness, never WORK progress, and counting it as alive_signal would mask
    the real wedge forever. Only a SEAT (per-incarnation id, single-threaded turn) may retract
    a page with its beat; for a bare agent id the PROGRESS PULSE governs."""
    from core.comm import doctor
    now = time.time()
    wl = {"phase": "thinking", "since_ts": now - 3600, "beat_ts": now - 2}   # beat thread alive
    found = doctor.examine("deepseek", probes={                              # BARE id = runner
        "now": now, "worklive": lambda a: wl, "progress": lambda a: None})
    assert ("hard_wedge", "page") in {(f.get("state"), f.get("grade")) for f in found}, (
        f"RUNNER WEDGE MASKED: a runner whose work thread is hung but whose heartbeat THREAD "
        f"still beats must PAGE -- the beat is process liveness, not work progress. This is "
        f"the exact streams.py flush wedge py-spy caught. Findings: {found}")


if __name__ == "__main__":
    test_p1_beating_seat_never_pages_as_wedged()
    test_p2_truly_dead_seat_still_pages()
    print("PASS")
