"""PRE-REGISTERED ACCEPTANCE -- the scorecard must confess blindness instead of reporting zero.

kimi's meta-guard, and it is the generalisable cure for the class we hit TEN times in one arc:
"that's not bad luck, that's a system property -- we build organs faster than we verify they
transduce." Its proposal: a scorecard self-check asserting each detector's target set is
non-empty over the window it claims to measure; a detector whose evidence class never occurs
renders UNCHECKABLE, not "(no signal)". The three confessions applied to the scorecard itself.

THE LIVE CASE THAT PROVES THE SHAPE. M10's detector was `startswith("scripts/check_")`. T104
moved every checker to scripts/checkers/, where that prefix cannot match (the char after
"check" is "e", not "_"). So M10 reported "(no signal)" -- indistinguishable from "no guards
were written" -- while guards were being written. The cheap, decisive test it failed:

    DOES THIS DETECTOR'S PREDICATE MATCH ANYTHING IN THE TREE AT ALL?

Zero repo-wide matches means the detector is looking for something that no longer exists. That
is blindness, and blindness must never render as absence.

The distinction this file enforces, because the two failure modes are not the same:
  * PATH-PREDICATE detectors (M6 records, M10 guards) have a checkable evidence class -- run the
    predicate over the whole tree. Empty => UNCHECKABLE.
  * MESSAGE-REGEX detectors (M1 fences, M4 drills, M5 live-exercise) read commit prose. They
    measure WHAT WE SAY and render green silence the moment we stop using a word. They are
    SELF-REPORT and must be labelled as such -- exactly the trap M3 sat in until it was made to
    read git.

  P1  a predicate matching nothing in the tree reads UNCHECKABLE, never zero
  P2  a predicate that matches files, with none in the window, reads a TRUE zero
  P3  message-regex detectors are labelled self-report, never presented as measurement
  P4  the meta-guard is itself fail-open: it never breaks the reader it audits

Run: py -m pytest tests/test_scorecard_confesses_blindness.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_p1_a_predicate_that_matches_nothing_is_unchecked(tmp_path):
    """The M10 case. A stale prefix must announce itself, not render as an empty world."""
    from scripts import arc_scorecard as sc
    v = sc.detector_health("guards", lambda p: p.startswith("scripts/check_THAT_MOVED/"),
                           root=str(tmp_path))
    assert v["status"] == "UNCHECKABLE", (
        "a detector whose predicate matches NOTHING in the tree reported a number -- that is "
        "blindness rendering as absence, the exact shape that hid M10 for a whole refactor")
    assert "matches nothing" in v["detail"].lower() or "no file" in v["detail"].lower()


def test_p2_a_live_predicate_with_an_empty_window_is_a_true_zero(tmp_path):
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "check_thing.py").write_text("x = 1\n", encoding="utf-8")
    from scripts import arc_scorecard as sc
    v = sc.detector_health("guards", lambda p: p.startswith("scripts/check_"),
                           root=str(tmp_path))
    assert v["status"] == "OK", (
        "the predicate matches real files, so a zero in the window means none were added -- "
        "that zero is information and must not be downgraded to UNCHECKABLE")


def test_p3_message_regex_detectors_are_labelled_self_report():
    """M4 and M5 count commits whose MESSAGE contains a word. They render green silence if we
    simply stop typing it -- the same trap M3 sat in until it was made to read git."""
    from scripts import arc_scorecard as sc
    assert "M4" in sc.SELF_REPORT and "M5" in sc.SELF_REPORT and "M1" in sc.SELF_REPORT
    assert "M3" not in sc.SELF_REPORT, "M3 reads git now -- it is measured, not self-reported"
    assert "M10" not in sc.SELF_REPORT


def test_p4_the_meta_guard_is_fail_open(tmp_path):
    from scripts import arc_scorecard as sc

    def boom(p):
        raise RuntimeError("bad predicate")

    v = sc.detector_health("guards", boom, root=str(tmp_path))
    assert v["status"] == "UNCHECKABLE", "a broken predicate confesses; it must not crash the reader"
