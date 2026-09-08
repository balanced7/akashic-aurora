"""Pins for the lesson anchor resolver (core/recall/anchors.py).

Build spec: docs/library/design/20260725_lesson-decay-reconciled-design_194ab2.md
(two rounds, claude + deepseek + kimi; Daniel's reframe).

WHY THIS EXISTS
---------------
A lesson is a claim about a system that moves. Measured 2026-07-25: 435 lessons, 92 citing a
repo path, 23 citing a path that no longer exists. And during that session the lesson
`intelligence_roadmap_and_spine1` fired into a live context prescribing work that was already
DONE, citing a roadmap that was GONE.

The resolver answers ONE question per anchor -- does this still hold? -- and its whole design
is about what it says when it CANNOT tell.

THE THREE CONFESSIONS (kimi, and they are the point):
  UNCHECKABLE  -- I have no anchor, or cannot evaluate this one. NOT "true".
  MISSING      -- the anchor resolved to nothing. The premise may have moved.
  STARVED      -- nothing at all was checkable. NOT "all clean".
A resolver that cannot confess its own blindness becomes the fourth organ this week to report
a confident zero (the token meter, the door-parity parser, the census OK-line).

ANCHORS ARE STABLE IDS, NEVER PATHS. deepseek measured path-anchoring at ~78% false positive:
two thirds of the 23 dead-path lessons cite `scripts/hooks/ -> agent/harness/hooks/` and are
ABOUT that migration -- dead path, current knowledge. Paths are the wrong anchor; that is why
stable ids exist.

PIN ANCHORS ARE DELIBERATELY UNCHECKABLE IN V1. Settled by probe, not argument: a test marked
`skipif(True)` whose body is `assert False` is listed by `pytest --co` alongside real tests,
and the run reports "1 passed, 1 skipped" with a GREEN exit code. Collection cannot
distinguish a guard from a ghost, and 69 of 313 test files here carry skips -- including a
class reading "pre-registered; impl pending (assertions frozen)". So a pin anchor resolves
only against an execution RECEIPT (ran-and-passed), and without one it confesses UNCHECKABLE
rather than reading a green suite as proof.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.recall import anchors  # noqa: E402


# --------------------------------------------------------------------------
# Anchor kinds are recognised structurally, never by guessing.
# --------------------------------------------------------------------------
def test_anchor_kinds_are_classified():
    assert anchors.classify("art_20260721_leadership-mechanics-x_225120") == "atom"
    assert anchors.classify("T070") == "task"
    assert anchors.classify("8232640") == "commit"
    assert anchors.classify("tests/test_t070_universal_isolation.py::test_x") == "pin"
    assert anchors.classify("docs/ARCHITECTURE.md") == "path"


def test_a_path_anchor_is_accepted_but_flagged_as_weak():
    """Paths are the WRONG anchor (78% false positive) -- usable, never authoritative."""
    v = anchors.resolve("docs/ARCHITECTURE.md", root=ROOT)
    assert v.kind == "path"
    assert v.weak is True, "a path anchor must declare itself weak, not pass as proof"


# --------------------------------------------------------------------------
# The confessions.
# --------------------------------------------------------------------------
def test_unknown_anchor_is_uncheckable_never_true():
    v = anchors.resolve("¿totally-unparseable?", root=ROOT)
    assert v.status == "UNCHECKABLE"
    assert v.status != "RESOLVED"


def test_pin_anchor_without_a_receipt_is_uncheckable_not_green():
    """The blind mode: a collected-but-skipped pin reads green. Refuse to read it as proof."""
    v = anchors.resolve("tests/test_t070_universal_isolation.py::test_spill_dir_is_isolated_too",
                        root=ROOT)
    assert v.status == "UNCHECKABLE", (
        "a pin with no execution receipt must NOT resolve -- a skipped pin is green"
    )
    assert "receipt" in v.detail.lower()


def test_pin_anchor_with_a_ran_and_passed_receipt_resolves():
    receipt = {"tests/test_t070_universal_isolation.py::test_spill_dir_is_isolated_too": "passed"}
    v = anchors.resolve("tests/test_t070_universal_isolation.py::test_spill_dir_is_isolated_too",
                        root=ROOT, receipts=receipt)
    assert v.status == "RESOLVED"


def test_a_skipped_pin_receipt_is_uncheckable_not_resolved():
    receipt = {"tests/test_x.py::test_y": "skipped"}
    v = anchors.resolve("tests/test_x.py::test_y", root=ROOT, receipts=receipt)
    assert v.status == "UNCHECKABLE", "SKIPPED must never read as RESOLVED"
    assert v.status != "MISSING", "skipped is blindness, not absence"


# --------------------------------------------------------------------------
# Real resolution against this repo.
# --------------------------------------------------------------------------
def test_a_live_commit_sha_resolves():
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    if not sha:
        return  # git unavailable: nothing to assert, and we do not fake it
    assert anchors.resolve(sha, root=ROOT).status == "RESOLVED"


def test_a_bogus_commit_sha_is_missing():
    assert anchors.resolve("deadbee", root=ROOT).status == "MISSING"


def test_a_gone_path_is_missing_and_a_live_one_resolves():
    assert anchors.resolve("docs/intelligence-roadmap.md", root=ROOT).status == "MISSING"
    assert anchors.resolve("docs/ARCHITECTURE.md", root=ROOT).status == "RESOLVED"


# --------------------------------------------------------------------------
# Lesson-level verdict: the banner, and STARVED.
# --------------------------------------------------------------------------
def test_a_lesson_with_no_anchors_is_starved_not_clean():
    report = anchors.review({"experiment_name": "x", "recommendation": "do a thing"}, root=ROOT)
    assert report.starved is True
    assert report.banner, "a starved review must still say something"
    # Assert the INTENT, not a substring: the banner must not claim the premise holds.
    # (First draft asserted "clean" was absent and failed on the banner "this is not a clean
    # bill" -- which says exactly the right thing. A pin that fails correct behaviour on a
    # keyword is a pin that will get loosened later for the wrong reason.)
    assert "holds" not in report.banner.lower()
    assert "unchecked" in report.banner.lower()


def test_a_lesson_whose_anchor_is_gone_banners():
    lesson = {"experiment_name": "x",
              "recommendation": "see docs/intelligence-roadmap.md for the plan"}
    report = anchors.review(lesson, root=ROOT)
    assert report.starved is False
    assert any(v.status == "MISSING" for v in report.verdicts)
    assert "MISSING" in report.banner


def test_review_never_retires_anything():
    """No auto-retirement, ever. deepseek: the second-order lesson outlives the ritual."""
    lesson = {"experiment_name": "x", "recommendation": "see docs/gone-forever.md"}
    report = anchors.review(lesson, root=ROOT)
    assert not hasattr(report, "retire"), "the resolver must not carry a retirement verdict"
    assert report.banner.startswith("["), "output is an advisory banner, not a decision"


# --------------------------------------------------------------------------
# The headline claims exactly what the verdict list supports -- never more.
# defer 00b3d351fb: `if missing:` raised "premise MISSING" when ANY strong anchor was gone, so
# a lesson with two RESOLVED strong anchors and one moved read as if its premise had vanished.
# JTMS (deepseek, 2026-07-27, build_system_and_tms_invalidation): a belief stands while at
# least one justification stands. Label-only -- verdicts and lesson-validity semantics are
# untouched; a gap is still named, it is just counted honestly.
# --------------------------------------------------------------------------
def _receipt_anchors(states):
    """Strong, hermetic anchors: pin receipts need neither git nor the filesystem, so these
    pins cannot go blind for a reason unrelated to the banner they test."""
    names = [f"tests/test_hypothetical_guard.py::test_{i}" for i in range(len(states))]
    return names, dict(zip(names, states))


def test_one_missing_among_resolved_strong_anchors_is_labelled_partial():
    """The defer's own example: three strong anchors, two RESOLVED, one gone -> '1 of 3'."""
    cites, receipts = _receipt_anchors(["passed", "passed", "failed"])
    report = anchors.review({"experiment_name": "x", "cites": cites},
                            root=ROOT, receipts=receipts)
    statuses = sorted(v.status for v in report.verdicts)
    assert statuses == ["MISSING", "RESOLVED", "RESOLVED"], statuses   # the pin's own premise
    assert all(not v.weak for v in report.verdicts)
    assert report.starved is False
    assert not report.banner.startswith("[premise MISSING"), (
        "two of three strong anchors still resolve; the headline may not claim the premise "
        f"is MISSING: {report.banner!r}"
    )
    assert "1 of 3" in report.banner, report.banner
    assert "MISSING" in report.banner, "the gap itself must still be named"


def test_a_moved_commit_beside_a_live_one_is_partial_not_missing():
    """Same rule through the real resolver: a live sha and a bogus one -> '1 of 2'."""
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    if not sha:
        return  # git unavailable: nothing to assert, and we do not fake it
    report = anchors.review({"experiment_name": "x", "cites": [sha, "deadbee"]}, root=ROOT)
    assert not report.banner.startswith("[premise MISSING"), report.banner
    assert "1 of 2" in report.banner, report.banner
    assert "deadbee" in report.banner, "the missing anchor is still named"


def test_all_strong_anchors_missing_still_reads_missing():
    """Guard against over-softening: every strong anchor gone is MISSING, and a WEAK path
    that happens to resolve does not rescue the premise -- weak is never authoritative."""
    cites, receipts = _receipt_anchors(["failed", "failed"])
    report = anchors.review({"experiment_name": "x", "cites": cites + ["docs/ARCHITECTURE.md"]},
                            root=ROOT, receipts=receipts)
    assert any(v.weak and v.status == "RESOLVED" for v in report.verdicts)
    assert report.banner.startswith("[premise MISSING"), report.banner
    assert "PARTIALLY" not in report.banner


def test_weak_missing_beside_a_live_strong_anchor_still_reads_may_have_moved():
    """Boundary: a gone PATH next to a live strong anchor is the weak-only branch, untouched."""
    cites, receipts = _receipt_anchors(["passed"])
    report = anchors.review({"experiment_name": "x",
                             "cites": cites + ["docs/intelligence-roadmap.md"]},
                            root=ROOT, receipts=receipts)
    assert report.banner.startswith("[premise may have moved"), report.banner
    assert "PARTIALLY" not in report.banner
