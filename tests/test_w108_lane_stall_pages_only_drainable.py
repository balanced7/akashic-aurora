"""W108 RED pins — a LANE STALL page must mean somebody is expected to drain.

Live receipt, 2026-07-30: the doctor paged LANE STALL for five seats at once, every
turn, into the operator's console. Every one of those pages was unactionable:

  - gemini      -- deliberately PARKED, no runner, nobody expected to drain it
  - codex_root  -- working through its own task surface, no bus runner at all
  - claude      -- an interactive seat that drains on its next turn by construction

The offered cure (`bifrost-skip-to-now`, the doctor's own suggested drill) advances a
consume cursor past undelivered mail. The conductor came within one command of running
the sibling drill (`roster --reap`) against those same rows, which -- per cursor_grok's
verification, research/in-flight/roster-liveness-defect-grok-verification-2026-07-30.md
-- would have re-homed LIVE runners' per-incarnation seat mail. A false page whose only
remedy destroys data is worse than silence.

THE DEFECT IS AN INCONSISTENCY INSIDE ONE FUNCTION. `examine()` already grades the
UNREAD-BACKLOG finding by liveness: an absent agent renders "OFFLINE ... ghost mail" as
DASHBOARD and explicitly never pages, and a present-but-runnerless seat renders "consumes
on next turn/wake" as DASHBOARD and never pages. One hundred lines later the LANE-STALL
finding pages on depth and age ALONE, consulting no liveness signal whatsoever. Two
adjacent checks over the same seat, one of which knows the seat is gone.

The true signal the check was built for (the 2026-07-26 kimi receipt: a fresh pulse while
45h of work sat at depth 55) is a RUNNER that should be draining and is not. That signal
must survive; only the unactionable pages go.

  P1  ABSENT seat (no worklive, no other presence) + deep, old lane -> NOT page-grade.
  P2  PRESENT-but-no-worklive interactive seat + deep, old lane -> NOT page-grade.
  P3  LIVE RUNNER (worklive present) + deep, old lane -> STILL PAGES. The kimi receipt
      is the reason this check exists and it must not be weakened.
  P4  Whatever the grade, the finding is not silently dropped -- an absent seat's
      backlog stays VISIBLE as a dashboard row (graveyard-is-a-resource; T120 says a
      surface must not go quiet about what it holds).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEEP_OLD_LANE = {"age_s": 70000.0, "depth": 18, "straggler": 0,
                 "backlog_age_s": 70000.0}


def _probes(*, worklive):
    """Only the seams examine() reads; every other probe is neutralised so a pin is
    never red for a reason the test does not control (the W69 rule)."""
    return {
        "worklive": lambda a: worklive,
        "progress": lambda a: None,
        "backlog": lambda a: 0,
        "stalled_since": lambda a, present=None: None,
        "halted": lambda a: None,
        "lane_health": lambda a: dict(DEEP_OLD_LANE),
        "token_cost": lambda a: None,
        "stale_code": lambda a: None,
        "bench_count": lambda a: 0,
        "now": 1785460000.0,
    }


def _lane_stall(findings):
    return [f for f in findings if f.get("state") == "lane_stall"]


def test_p1_absent_seat_deep_lane_does_not_page(monkeypatch):
    """A retired/parked seat's backlog is ghost mail. Nobody is coming to drain it, so
    paging an operator about it is a demand with no possible action."""
    from core.comm import doctor
    monkeypatch.setattr(doctor, "_present_no_worklive", lambda a: False)
    findings = doctor.examine("t-w108-absent", probes=_probes(worklive={}))
    pages = [f for f in _lane_stall(findings) if f.get("grade") == "page"]
    assert not pages, (
        "an ABSENT seat (no worklive, no runner, no wake seat) must not page LANE "
        f"STALL -- nobody is expected to drain it. Got: {pages}")


def test_p2_present_no_worklive_seat_does_not_page(monkeypatch):
    """An interactive seat (claude) has no runner phase but IS alive via its armed
    watcher, and drains on its next turn by construction. examine() already knows this
    for the unread-backlog finding; the lane-stall finding must agree."""
    from core.comm import doctor
    monkeypatch.setattr(doctor, "_present_no_worklive", lambda a: True)
    findings = doctor.examine("t-w108-interactive", probes=_probes(worklive={}))
    pages = [f for f in _lane_stall(findings) if f.get("grade") == "page"]
    assert not pages, (
        "a present-but-runnerless seat consumes on its next turn/wake; a LANE STALL "
        f"page tells the operator to act on something already self-healing. Got: {pages}")


def test_p3_live_runner_with_stalled_lane_still_pages(monkeypatch):
    """The signal this check exists for: a runner that SHOULD be draining and is not.
    2026-07-26, kimi: pulse fresh the whole time, 45h of work at depth 55. This must
    remain page-grade or the fix has traded one blindness for another."""
    from core.comm import doctor
    monkeypatch.setattr(doctor, "_present_no_worklive", lambda a: True)
    live_runner = {"phase": "idle", "since_ts": 1785459900.0, "beat_ts": 1785459990.0,
                   "seq": 42}
    findings = doctor.examine("t-w108-runner", probes=_probes(worklive=live_runner))
    pages = [f for f in _lane_stall(findings) if f.get("grade") == "page"]
    assert pages, (
        "a LIVE RUNNER whose work lane has not moved in ~19h MUST still page -- that is "
        "the kimi receipt and the whole reason this finding exists")


def test_p4_absent_seat_backlog_stays_visible(monkeypatch):
    """Demoting the grade must not delete the fact. T120: a surface that goes quiet
    about what it holds manufactures false confidence."""
    from core.comm import doctor
    monkeypatch.setattr(doctor, "_present_no_worklive", lambda a: False)
    findings = doctor.examine("t-w108-absent-visible", probes=_probes(worklive={}))
    rows = _lane_stall(findings) + [f for f in findings
                                    if "lane" in str(f.get("state", ""))]
    assert rows, (
        "an absent seat's undrained lane must remain VISIBLE as a dashboard row; "
        "silencing the page must not silence the fact")
