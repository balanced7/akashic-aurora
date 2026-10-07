"""RED pin: the DSH web seat must beat the WORKLIVE plane while idle
(T385 C1 / identity-activation S7). Fails by construction until a persistent
worklive beater exists for the web seat.

THE SEAM (measured 2026-08-26/28): the web host's plugin beats ROSTER presence
(bridge.py cmd_presence -> roster.heartbeat) but never the WORKLIVE key that the
send door, doctor, and bus route on -- so the seat reads OFFLINE and operator
mail stalls on global: 'UNATTENDED RECIPIENT: dsh_agent has no live seat'.
Presence is not the plane the router consults (attendance() probe 3). The
fence's law: presence proves liveness only; the worklive beat is the
idle-listening proof.

CONTRACT the fix must satisfy (per liveness.py):
- a persistent, idle-safe refresher: start_worklive_beater(agent, interval_s)
  returning a stop callable, runnable from the persistent MCP child so the seat
  beats even when no web session is active;
- interval < WORKLIVE_TTL (45s) so the record never flaps out;
- fail-open: a dead bus must never kill the loop (liveness._flush already
  swallows; the loop must too);
- the record carries code_sha (T114) so the roster can say alive-ON-WHAT.
"""
import time

import pytest

from core.comm import liveness


def _beater():
    import agent.harness.dsh_web_heartbeat as beat  # noqa: F401  (RED: does not exist yet)
    return beat


def test_web_seat_beater_entrypoint_exists():
    beat = _beater()
    assert callable(getattr(beat, "start_worklive_beater", None)), (
        "start_worklive_beater(agent, interval_s) missing -- the web seat has no idle beater"
    )


def test_idle_beater_keeps_worklive_fresh():
    beat = _beater()
    stop = beat.start_worklive_beater("dsh_agent", interval_s=5)
    try:
        time.sleep(7)
        age = liveness.worklive_beat_age("dsh_agent")
        assert age is not None, "no worklive record after beater start"
        assert age < liveness.WORKLIVE_TTL, (
            f"beat age {age:.1f}s >= TTL -- an idle web seat reads OFFLINE and "
            "operator mail stalls on global"
        )
    finally:
        stop()


def test_beater_loop_is_fail_open():
    # several flush cycles against whatever bus state exists; ANY raise fails the
    # test -- the beater is observability and must never wedge its own loop
    beat = _beater()
    stop = beat.start_worklive_beater("dsh_agent", interval_s=1)
    try:
        time.sleep(2.6)
    finally:
        stop()
