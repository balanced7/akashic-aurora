"""PRE-REGISTERED ACCEPTANCE -- method drift reaches the one channel that is actually read.

THE RECURSION THIS CLOSES (2026-07-27). M3 compliance is now MEASURED (arc_scorecard, 30%
live). But arc_scorecard is a reader wired to the `wrap` verb, and I have not run `wrap` once
in this session -- exactly the defect it was built to expose. ship.py had the method checkers
and was impassable; the scorecard has the compliance number and rides a door nobody walks
through. A computed red with no channel, for the seventh time in one night.

Boot is the one channel with PROVEN readership: this session's boot line was read and acted on
(delta, mail, funnel) within the first minute.

THE RULE, from deepseek's round-2 attack: do not simply add traffic. Its walkthrough -- tool
call 1 helps, call 12 is skimmed, call 27 (the one that mattered) is dismissed because the
channel was devalued by 26 prior impressions. Its prescription is TRIGGER SELECTIVITY: check
every trigger, stay SILENT on the ones that do not fire, speak only when it matters.

So this line is silent while we are compliant and speaks when we drift. A boot line that
appears every session regardless of state is furniture; one that appears only on drift is a
signal.

  P1  BELOW threshold -> one line naming the measured rate
  P2  AT/ABOVE threshold -> COMPLETE SILENCE (no "all good" line -- that is the furniture)
  P3  no measurable window -> silence, never a fabricated healthy number
  P4  fail-open: a broken audit never breaks boot

Run: py -m pytest tests/test_boot_surfaces_method_drift.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_p1_drift_speaks(monkeypatch):
    from core.coord import method_drift
    monkeypatch.setattr(method_drift, "_stats",
                        lambda n: {"total": 30, "clean": 9, "violations": 21, "pct": 30.0})
    line = method_drift.boot_line(threshold=80.0)
    assert line and "30" in line, f"drift must name the measured rate, got {line!r}"
    assert "9/30" in line or "9 of 30" in line


def test_p2_compliance_is_silent(monkeypatch):
    """The hard part. An 'all good' line every session is how a channel becomes furniture,
    and furniture is why the one that mattered gets skimmed."""
    from core.coord import method_drift
    monkeypatch.setattr(method_drift, "_stats",
                        lambda n: {"total": 30, "clean": 29, "violations": 1, "pct": 96.7})
    assert method_drift.boot_line(threshold=80.0) == "", (
        "boot spoke while we were compliant -- a line that always appears is furniture, and "
        "trigger selectivity is the whole defence against banner-blindness")


def test_p3_no_window_is_silence_not_a_healthy_number(monkeypatch):
    from core.coord import method_drift
    monkeypatch.setattr(method_drift, "_stats",
                        lambda n: {"total": 0, "clean": 0, "violations": 0, "pct": 100.0})
    assert method_drift.boot_line(threshold=80.0) == "", (
        "an empty window rendered as compliance -- absence is not evidence")


def test_p4_a_broken_audit_never_breaks_boot(monkeypatch):
    from core.coord import method_drift

    def boom(n):
        raise RuntimeError("git unavailable")

    monkeypatch.setattr(method_drift, "_stats", boom)
    assert method_drift.boot_line(threshold=80.0) == "", "the reader must fail open, silently"
