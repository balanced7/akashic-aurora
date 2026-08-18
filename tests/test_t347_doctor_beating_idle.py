"""T347 acceptance pins — alive is not working (RED committed alone, M3).

LIVE RECEIPT 2026-08-17: doctor printed "deepseek#23444-de: long work in
'running' (571s) but the worklive BEAT is fresh (2s ago) -- genuinely working,
not wedged" for a runner measuring 0.00s CPU delta over 6s with no outbound
socket and an empty backlog. Idle, not working — the operator was told otherwise.

ROOT: doctor.examine's seat test is `"#" in agent`. The S2 law it implements
("only a SEAT may retract a page with its beat") is correct — but seats are
agent#<sid8> (8 hex, per-incarnation interactive) while RUNNER incarnations are
agent#<pid>-<suffix> (deepseek#23444-de, kimi#34276-ki), and both contain "#".
Sol's NO-GO (pinned for BARE ids in test_doctor_wedge_vs_beat.py P3: a runner's
heartbeat is its OWN THREAD, process liveness never work progress) was reopened
one door over by the classifier.

The law under pin, two-sided:
  TRUE seat (#sid8)          — beat retracts (S2 fix, untouched; P1 there).
  RUNNER (bare OR #pid-...)  — pulse governs. Beat-only on long work earns a
                               distinct third state that names both signals and
                               says "alive is not working" — never the
                               "genuinely working" verdict (T176/T337: absence
                               of work evidence must not render as work).

Run:  py -m pytest tests/test_t347_doctor_beating_idle.py -v
"""

from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import doctor  # noqa: E402
from core.comm import liveness  # noqa: E402

RUNNER_ID = "deepseek#23444-de"          # the receipt's exact shape
SEAT_ID = "docpin#abcd1234"              # 8-hex sid = true seat contract


def _examine(agent, worklive, progress=None):
    return doctor.examine(agent, probes={
        "now": time.time(),
        "worklive": lambda a: worklive,
        "progress": lambda a: progress,
    })


def _states(findings):
    return {(f.get("state"), f.get("grade")) for f in findings}


def _lines(findings):
    return " | ".join(f.get("line", "") for f in findings)


def _long_beat_only_wl():
    now = time.time()
    return {"phase": "running", "since_ts": now - liveness.DEFAULT_WEDGE_S - 120,
            "beat_ts": now - 2}


def test_p1_runner_incarnation_beat_only_is_never_genuinely_working():
    f = _examine(RUNNER_ID, _long_beat_only_wl(), progress=None)
    assert "genuinely working" not in _lines(f), (
        "RUNNER-IN-SEAT-COSTUME: a #pid-suffix runner incarnation with a fresh "
        "beat and NO pulse rendered as 'genuinely working' — the beat is its "
        "heartbeat THREAD, the exact evidence class Sol's no-go excluded "
        "(live receipt 2026-08-17)")


def test_p2_runner_beat_only_earns_the_third_state_naming_both_signals():
    f = _examine(RUNNER_ID, _long_beat_only_wl(), progress=None)
    hits = [x for x in f if x.get("state") == "beating_unproven"]
    assert hits, (f"beat-only long work on a runner incarnation must yield the "
                  f"distinct 'beating_unproven' finding; got {_states(f)}")
    line = hits[0].get("line", "").lower()
    # T282: a verdict names the signals it keyed on — both of them.
    assert "beat" in line and "pulse" in line, (
        "the third state must name BOTH signals: fresh beat, dead/absent pulse")
    assert "alive" in line and "working" in line, (
        "the third state must say the discriminating sentence: alive is not working")


def test_p3_true_seat_beat_still_retracts():
    """S2's fix stays: a #sid8 interactive seat writes worklive from its own
    turn, so its beat IS work evidence (P1 of test_doctor_wedge_vs_beat.py)."""
    f = _examine(SEAT_ID, _long_beat_only_wl(), progress=None)
    assert ("hard_wedge", "page") not in _states(f), (
        "REGRESSION: the fix demoted true seats — a beating #sid8 seat must "
        "never page as wedged")
    assert not any(x.get("state") == "beating_unproven" for x in f), (
        "REGRESSION: the third state fired on a true seat; it is a runner verdict")


def test_p4_runner_fresh_pulse_still_earns_genuinely_working():
    now = time.time()
    wl = {"phase": "running", "since_ts": now - liveness.DEFAULT_WEDGE_S - 120,
          "beat_ts": now - 2}
    prog = {"age_s": 3, "detail": "reviewing T335"}
    f = _examine(RUNNER_ID, wl, progress=prog)
    assert "genuinely working" in _lines(f), (
        "pulse evidence is work evidence — the fix must not demote it")


def test_p5_runner_dead_both_still_pages_hard_wedge():
    now = time.time()
    wl = {"phase": "handling", "since_ts": now - liveness.DEFAULT_WEDGE_S - 120,
          "beat_ts": now - 9999}
    f = _examine(RUNNER_ID, wl, progress=None)
    assert ("hard_wedge", "page") in _states(f), (
        "dead pulse + dead beat must keep paging HARD WEDGE — the fix must not "
        "soften the true-wedge branch")
