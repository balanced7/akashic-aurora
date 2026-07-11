"""
T030 L2 -- the progress pulse (RB-27a) + fleet doctor (RB-27b), per the reconciled
L2 BUILD SPEC (docs/agent-liveness-tier-2026-07.md): the missing reader of the L1
worklive signals, with the three-reviewer paging table.

The law under test:
  PAGE-GRADE (the ONLY two): HARD WEDGE (phase=handling + pulse dead -- worker died
  inside a turn, not self-healing) and STALLED CONSUMER (idle + unread backlog aged
  past hysteresis -- deepseek's trigger, claude's hysteresis: single-sample falses on
  every Redis blip).
  DASHBOARD: wedged-with-live-pulse (long legit work, F2), self-reported errors
  (SELF-REPORTED beats INFERRED in rendering), unhandled counts.
  BANNER: fleet frozen (deliberate config state, not an emergency).
  Healthy fleet = ONE line. Every finding carries its drill-down.

Pre-registered per M3 (this file precedes the doctor). Hermetic: probes injected.
Run: py -m pytest tests/test_fleet_doctor.py -q
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _probes(**over):
    """A healthy-idle agent by default; tests override single facets."""
    base = dict(
        worklive=lambda a: {"phase": "idle", "detail": "", "turn": 3,
                            "since_ts": time.time() - 5, "beat_ts": time.time() - 1},
        progress=lambda a: None,                    # no pulse needed when idle
        backlog=lambda a: 0,                        # unread messages beyond the cursor
        stalled_since=lambda a, present: None,      # hysteresis first-seen (None = fresh)
        halted=lambda a: None,                      # None | {"reason":..., "age_s":...}
        now=time.time(),
    )
    base.update(over)
    return base


def test_healthy_fleet_is_one_line():
    from core.comm.doctor import examine_fleet
    rep = examine_fleet(["claude", "deepseek"], probes=_probes())
    assert rep["findings"] == []
    assert rep["summary"].count("\n") == 0 and "healthy" in rep["summary"].lower()


def test_hard_wedge_pages_when_pulse_is_dead():
    """The worker died inside a turn: handling phase aged past the wedge threshold and
    NO fresh pulse. Not self-healing -> the one always-page wedge state."""
    from core.comm.doctor import examine
    f = examine("deepseek", probes=_probes(
        worklive=lambda a: {"phase": "handling", "detail": "claude:handoff", "turn": 9,
                            "since_ts": time.time() - 400, "beat_ts": time.time() - 1},
        progress=lambda a: None))
    wedge = next(x for x in f if x["state"] == "hard_wedge")
    assert wedge["grade"] == "page"
    assert "drill" in wedge and wedge["drill"], "every finding carries its drill-down"


def test_long_legit_work_with_fresh_pulse_is_dashboard_only():
    """F2, solved: same aged handling phase, but the pulse is FRESH -- genuinely
    working. Never a page (the false wedge that would let auto-revive kill real work)."""
    from core.comm.doctor import examine
    f = examine("deepseek", probes=_probes(
        worklive=lambda a: {"phase": "handling", "detail": "long review", "turn": 9,
                            "since_ts": time.time() - 400, "beat_ts": time.time() - 1},
        progress=lambda a: {"age_s": 1.5, "generation": 4, "detail": "tool:read_file"}))
    assert not any(x["grade"] == "page" for x in f)
    working = next(x for x in f if x["state"] == "working")
    assert "pulse" in working["line"].lower()


def test_stalled_consumer_needs_hysteresis_not_single_sample():
    """Deepseek's trigger (aged backlog on an idle agent) + claude's hysteresis
    (first-seen must AGE before paging -- single-sample falses on Redis blips)."""
    from core.comm.doctor import examine
    now = time.time()
    fresh = examine("deepseek", probes=_probes(
        backlog=lambda a: 3,
        stalled_since=lambda a, present: now,          # first observed just now
        now=now))
    assert not any(x["grade"] == "page" for x in fresh), "fresh stall observes, never pages"
    assert any(x["state"] == "stalled_consumer" for x in fresh), "but it IS on the dashboard"
    aged = examine("deepseek", probes=_probes(
        backlog=lambda a: 3,
        stalled_since=lambda a, present: now - 300,    # stalled for 5 minutes
        now=now))
    stall = next(x for x in aged if x["state"] == "stalled_consumer")
    assert stall["grade"] == "page", "aged past hysteresis -> page-grade"


def test_self_reported_error_beats_inferred_in_rendering():
    from core.comm.doctor import examine
    f = examine("deepseek", probes=_probes(
        worklive=lambda a: {"phase": "error:oom-in-tool", "detail": "", "turn": 2,
                            "since_ts": time.time() - 10, "beat_ts": time.time() - 1},
        progress=lambda a: {"age_s": 2.0, "generation": 4, "detail": "trigger:oom-in-tool"}))
    rep = next(x for x in f if x["state"] == "self_reported_error")
    assert "oom-in-tool" in rep["line"], "the confessed reason is IN the line"


def test_frozen_fleet_is_banner_not_page():
    from core.comm.doctor import examine
    f = examine("deepseek", probes=_probes(
        halted=lambda a: {"reason": "rate limit auto-pause", "age_s": 7200}))
    frozen = next(x for x in f if x["state"] == "frozen")
    assert frozen["grade"] == "banner", "a pause is deliberate config state, not an emergency"
    assert "rate limit" in frozen["line"]


def test_pulse_primitives_round_trip():
    """RB-27a contract: pulse writes value {generation, detail} with a TTL; the reader
    returns age; a trigger value self-reports. Redis-backed; skips offline."""
    import pytest
    from core.comm import liveness
    from core.comm.bus import Bus
    import uuid
    agent = f"t-pulse-{uuid.uuid4().hex[:8]}"
    if not Bus(agent).online:
        pytest.skip("redis not available")
    try:
        assert liveness.pulse(agent, "tool:read_file", generation=7)
        rec = liveness.progress_read(agent)
        assert rec and rec["generation"] == 7 and rec["age_s"] < 3
        assert liveness.pulse_error(agent, "oom", generation=7)
        rec2 = liveness.progress_read(agent)
        assert rec2["detail"].startswith("trigger:oom")
    finally:
        try:
            Bus(agent)._client.delete(f"bifrost:progress:{agent}")
        except Exception:
            pass


def test_runner_wires_the_pulse_at_progress_points():
    """Structural: the runner pulses at on_trace (every tool call / thinking chunk --
    the REAL progress points) and flags starting/error worklive phases."""
    src = open(os.path.join(REPO, "scripts", "bifrost_runner_deepseek.py"),
               encoding="utf-8").read()
    assert "liveness.pulse(" in src, "the pulse rides the trace callback"
    assert "pulse_error(" in src, "caught-fatal self-reports (WATCHDOG=trigger equivalent)"
    assert '"starting"' in src, "boot-time wedge is distinguishable (starting phase)"
