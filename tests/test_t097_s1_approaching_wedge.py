"""
T097-S1 · P-S1-0 (kimi fence verdict 2026-07-20; deepseek concur) -- sub-threshold
wedge visibility. Slice 0 of the T098 build-our-own plan.

THE GAP: doctor.examine() is SILENT for a non-idle agent stuck in [0, DEFAULT_WEDGE_S)
with a DEAD pulse -- the exact window where C1-8's 25-40 min stall lived invisibly in
its first minutes. A mission face that renders this window as "fleet healthy" bakes the
C1-8/C10 disease into the new program on day one. A sub-threshold stall must surface as a
DASHBOARD "approaching wedge" (visible, not silent) -- and NEVER as a page (still self-healing).

Pre-registered per M3 (RED before the doctor branch + APPROACHING_WEDGE_S exist).
Hermetic: probes injected, no Redis. Run: py -m pytest tests/test_t097_s1_approaching_wedge.py -q
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _probes(**over):
    """A healthy-idle agent by default; tests override single facets (mirrors test_fleet_doctor)."""
    base = dict(
        worklive=lambda a: {"phase": "idle", "detail": "", "turn": 3,
                            "since_ts": time.time() - 5, "beat_ts": time.time() - 1},
        progress=lambda a: None,
        backlog=lambda a: 0,
        stalled_since=lambda a, present: None,
        halted=lambda a: None,
        now=time.time(),
    )
    base.update(over)
    return base


def test_subthreshold_deadpulse_stall_surfaces_as_approaching_wedge_dashboard():
    """P-S1-0 (the gap-closer): non-idle 250s with a DEAD pulse -> a DASHBOARD
    'approaching_wedge' finding (today this window is pure silence)."""
    from core.comm.doctor import examine
    f = examine("deepseek", probes=_probes(
        worklive=lambda a: {"phase": "handling", "detail": "claude:handoff", "turn": 9,
                            "since_ts": time.time() - 250, "beat_ts": time.time() - 1},
        progress=lambda a: None))
    aw = next((x for x in f if x["state"] == "approaching_wedge"), None)
    assert aw is not None, "sub-threshold dead-pulse stall must be VISIBLE, not silent"
    assert aw["grade"] == "dashboard", "approaching (not yet past threshold) -> dashboard, never page"
    assert aw["drill"], "every finding carries its drill-down"
    assert not any(x["grade"] == "page" for x in f), "sub-threshold never pages (still self-healing)"


def test_fresh_pulse_subthreshold_stays_silent():
    """Guard: a non-idle sub-threshold agent WITH a fresh pulse is genuinely working early --
    no finding (never turn normal early work into dashboard noise)."""
    from core.comm.doctor import examine
    f = examine("deepseek", probes=_probes(
        worklive=lambda a: {"phase": "handling", "detail": "review", "turn": 9,
                            "since_ts": time.time() - 250, "beat_ts": time.time() - 1},
        progress=lambda a: {"age_s": 1.5, "generation": 4, "detail": "tool:read_file"}))
    assert not any(x["state"] == "approaching_wedge" for x in f), "fresh pulse = working, not approaching"


def test_below_approaching_floor_stays_silent():
    """Guard: very early non-idle work (30s) stays silent -- approaching-wedge has a floor so
    momentary phase transitions don't spam the dashboard."""
    from core.comm.doctor import examine
    f = examine("deepseek", probes=_probes(
        worklive=lambda a: {"phase": "handling", "detail": "just started", "turn": 9,
                            "since_ts": time.time() - 30, "beat_ts": time.time() - 1},
        progress=lambda a: None))
    assert not any(x["state"] == "approaching_wedge" for x in f), "below the floor -> still silent"


def test_past_threshold_still_pages_not_approaching():
    """Guard (no regression of the existing law): a 400s dead-pulse stall is STILL a hard_wedge
    PAGE, not downgraded to approaching_wedge."""
    from core.comm.doctor import examine
    f = examine("deepseek", probes=_probes(
        worklive=lambda a: {"phase": "handling", "detail": "claude:handoff", "turn": 9,
                            "since_ts": time.time() - 400, "beat_ts": time.time() - 1},
        progress=lambda a: None))
    assert any(x["state"] == "hard_wedge" and x["grade"] == "page" for x in f), "past threshold still pages"
    assert not any(x["state"] == "approaching_wedge" for x in f), "past threshold is a wedge, not 'approaching'"
