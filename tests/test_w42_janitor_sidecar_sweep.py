"""W42 pins — the janitor sweeps a reaped seat's sidecars (gamma-a orphan .seen files).

gamma-a's fence (deepseek, 2026-07-21) named this: a dead session without a live watcher
leaves bifrost_wake_<agent>_<session>.seen in tempdir until reboot -- "acceptable litter,
file a WISH." W42 is that sweep: when the janitor KILLS or CLEANS a seat, it removes the
same session's .seen (wake-dedup) and .alive (activity marker) alongside the .pid, using
the same session-scoped naming. A SKIP (assumed-alive) touches nothing.

  P1  a cleaned dead seat's .seen + .alive are removed with its .pid
  P2  a skipped (assumed-alive) seat's sidecars SURVIVE (fail-open, never reap live state)
  P3  the sweep is best-effort: a missing sidecar is silent, no raise
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.comm.wake_seat as ws


def _seat_set(tmp, agent, sid, pid):
    """Write the .pid + .seen + .alive trio for one session; return their paths."""
    pidp = ws.seat_path(agent, sid, str(tmp))
    seenp = os.path.join(str(tmp), f"bifrost_wake_{agent}_{sid}.seen")
    alivep = ws.activity_marker_path(agent, sid, str(tmp))
    with open(pidp, "w") as f:
        f.write(str(pid))
    for p in (seenp, alivep):
        with open(p, "w") as f:
            f.write("x")
    return pidp, seenp, alivep


def test_p1_cleaned_seat_sweeps_sidecars(tmp_path):
    agent = "twjan"
    # a DEAD seat: pid present, but the process snapshot says it's gone -> reap=clean
    pidp, seenp, alivep = _seat_set(tmp_path, agent, "deadsess1", 999999)
    res = ws.janitor(agent, my_session="mysess", tmp=str(tmp_path),
                     snapshot_fn=lambda: {},           # empty snapshot: pid not alive
                     kill_fn=lambda p: True)
    actions = {os.path.basename(p): a for p, a, _ in res}
    assert actions.get(os.path.basename(pidp)) in ("clean", "kill")
    assert not os.path.exists(pidp), "the .pid is reaped"
    assert not os.path.exists(seenp), "W42: the .seen sidecar swept with it"
    assert not os.path.exists(alivep), "W42: the .alive marker swept with it"


def test_p2_skipped_seat_keeps_sidecars(tmp_path, monkeypatch):
    agent = "twjan2"
    pidp, seenp, alivep = _seat_set(tmp_path, agent, "livesess", os.getpid())
    # snapshot unavailable -> K8 assume-alive -> skip; sidecars must survive
    res = ws.janitor(agent, my_session="other", tmp=str(tmp_path),
                     snapshot_fn=lambda: None,
                     kill_fn=lambda p: True)
    actions = {a for _, a, _ in res}
    assert "skip" in actions
    assert os.path.exists(seenp) and os.path.exists(alivep), \
        "an assumed-alive seat's sidecars are never reaped (fail-open)"


def test_p3_missing_sidecar_is_silent(tmp_path):
    agent = "twjan3"
    pidp = ws.seat_path(agent, "nosidecars", str(tmp_path))
    with open(pidp, "w") as f:
        f.write("999999")
    # no .seen / .alive written -- the sweep must not raise
    res = ws.janitor(agent, my_session="mysess", tmp=str(tmp_path),
                     snapshot_fn=lambda: {}, kill_fn=lambda p: True)
    assert res and not os.path.exists(pidp)
