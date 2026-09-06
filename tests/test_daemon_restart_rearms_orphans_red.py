"""RED: a daemon restart must re-arm the listeners it orphaned.

LIVE INCIDENT, 2026-09-06 ~03:52 (this pin exists because it happened, unattended):
the claude autopilot daemon self-restarted to pick up a commit. It owns its wake listener as a
managed child, so the restart killed the listener. `write_rearm_trigger` is by contract
"written ONLY on a deadline self-cycle -- never on mail exits and never on stand-downs" (R18),
so a KILLED listener leaves NO trigger. `consume_rearms` then had no input, stayed idle and
correct, and the seat was deaf until a human noticed. Operator was asleep.

The class (arm-never-happened) is uncovered by construction because the recovery mechanism's
only input is produced by the component that died. This slice closes the most common INSTANCE:
at startup the daemon enumerates sessions that a DIFFERENT component says are alive -- the
`.alive` activity marker, touched at SessionStart by the session's own lifecycle, not by the
watcher -- and writes the trigger the existing spawner already knows how to consume.

It does NOT close the class. A session whose daemon never starts still produces no input; that
remains the out-of-band enumerator's job (Wake Doctrine T1/S1, operator-gated).
"""
from __future__ import annotations

import os
import pytest


def _alive(tmp, agent, sid):
    p = os.path.join(tmp, f"bifrost_wake_{agent}_{sid}.alive")
    open(p, "w").write("1")
    return p


def test_startup_rearms_a_session_that_is_alive_but_seatless(tmp_path):
    """The incident, pinned: .alive present, no .pid seat -> a trigger must be written."""
    from core.comm import daemon_state as ds
    tmp = str(tmp_path)
    _alive(tmp, "claude", "sess-orphaned")
    n = ds.rearm_orphaned_sessions("claude", tmp=tmp)
    trig = os.path.join(tmp, "bifrost_wake_claude_sess-orphaned.rearm")
    assert n == 1, "an alive-but-seatless session must be re-armed after a daemon restart"
    assert os.path.exists(trig), "the trigger the existing spawner consumes must be written"


def test_a_seated_session_is_left_alone(tmp_path):
    """Idempotence + no double-arm: a session that still holds its seat is not disturbed."""
    from core.comm import daemon_state as ds
    from core.comm import wake_seat
    tmp = str(tmp_path)
    _alive(tmp, "claude", "sess-seated")
    seat = wake_seat.seat_path("claude", "sess-seated", tmp)
    os.makedirs(os.path.dirname(seat), exist_ok=True)
    open(seat, "w").write("4242")
    n = ds.rearm_orphaned_sessions("claude", tmp=tmp)
    assert n == 0, "a seated session already has a live watcher -- re-arming would double-arm"
    assert not os.path.exists(os.path.join(tmp, "bifrost_wake_claude_sess-seated.rearm"))


def test_only_own_agent_is_touched(tmp_path):
    """A daemon may never re-arm another agent's seats (membrane law)."""
    from core.comm import daemon_state as ds
    tmp = str(tmp_path)
    _alive(tmp, "deepseek", "sess-theirs")
    n = ds.rearm_orphaned_sessions("claude", tmp=tmp)
    assert n == 0
    assert not os.path.exists(os.path.join(tmp, "bifrost_wake_deepseek_sess-theirs.rearm"))


def test_existing_trigger_is_not_duplicated(tmp_path):
    """If a trigger already exists the count must not inflate -- safe to re-run."""
    from core.comm import daemon_state as ds
    tmp = str(tmp_path)
    _alive(tmp, "claude", "sess-twice")
    assert ds.rearm_orphaned_sessions("claude", tmp=tmp) == 1
    assert ds.rearm_orphaned_sessions("claude", tmp=tmp) == 0, "idempotent on re-run"
