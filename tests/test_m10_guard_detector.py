"""PRE-REGISTERED ACCEPTANCE -- M10's guard detector went blind in a directory move.

MEASURED 2026-07-27. arc_scorecard renders "M10 guards for new law: (no signal)" for a window
in which scripts/checkers/check_pointer_promises.py was demonstrably ADDED. The detector is

    guards = _added_files(days, "scripts/check_")

and _added_files matches with startswith(). T104 moved the checkers to scripts/checkers/, and
"scripts/checkers/check_boundaries.py".startswith("scripts/check_") is FALSE -- the character
after "check" is "e", not "_". Verified both ways in a live shell.

So a guard was born, the organ measured nothing, and it reported that as no-signal. Eighth
confident-zero found in one night, and this one was created by a refactor that touched neither
the detector nor its test.

WHAT THIS FILE DELIBERATELY DOES NOT DO. scripts/ship_gate.py shipped the same window and is a
guard in spirit -- but it is not a check_* checker, so it does not match even the CORRECTED
prefix. Widening M10's definition until it counts my own work would be adjusting the instrument
to flatter the operator, which is the one move that would make this whole method loop worthless.
The definition stays; only the provably-stale path is repaired.

  P1  a guard added under the CURRENT location (scripts/checkers/) is detected
  P2  the legacy location still counts, so historical windows do not silently lose their guards
  P3  a non-guard file is NOT counted -- the definition is not widened to flatter anyone

Run: py -m pytest tests/test_m10_guard_detector.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _match(path):
    """The detector's own predicate, applied to one path."""
    import importlib
    sc = importlib.import_module("scripts.arc_scorecard")
    return sc.is_guard_path(path)


def test_p1_a_guard_in_the_current_location_is_detected():
    assert _match("scripts/checkers/check_pointer_promises.py"), (
        "a guard added under scripts/checkers/ is invisible to M10 -- the prefix was left "
        "behind by the T104 move and the organ has been reporting no-signal ever since")


def test_p2_the_legacy_location_still_counts():
    assert _match("scripts/check_boundaries.py"), (
        "historical windows must not silently lose their guards when the detector is repaired")


def test_p3_the_definition_is_not_widened_to_flatter_us():
    assert not _match("scripts/ship_gate.py"), (
        "ship_gate.py is a guard in spirit but not a check_* checker. Counting it would be "
        "adjusting the instrument until it agrees with the operator -- the failure mode that "
        "makes a self-measured method loop worthless")
    assert not _match("core/comm/doctor.py")
