"""T337 RED: the scorecard must not render UNRECORDED as ABSENT.

DANIIL'S FRAME, 2026-08-17: "KPI's have a nasty habit of being good at one thing and missing a
heard of elephants." This is one of ours, found in our own instrument, on the same night.

THE LIVE INSTANCE. Tonight's scorecard reported M5 (live-exercise after ship) and M6 (verbatim
preservation) as "(no signal)". Both had fired. T335 was exercised live against the real door and
its journal line read by hand; four fence halves were persisted verbatim to research/reviewed/.
Neither was annotated, so the instrument rendered performed-but-unannotated identically to
never-performed -- and the wrap read it as absence.

THE PROPER NAME, from the statistics pass: this is MISSING-NOT-AT-RANDOM aliased as a false
negative. Missingness depends on the very state being measured (a busy slice is exactly the one
that skips its annotation), so the bias is not noise -- it points one way. The prescribed minimum
instrumentation is a third state: "not recorded / unknown", distinct from "not performed".

WHICH IS T176's LAW, ONE PLANE OVER. We ruled this morning that an unlisted kind must resolve
UNCLASSIFIED and never a silent False, because absence of a decision is not a decision. The
scorecard does exactly what we forbade the taxonomy to do, and it does it to the instrument we
steer the method by.

THE DISCRIMINATOR the fix turns on, and it is already in the code: metrics in SELF_REPORT have no
detector at all -- their signal exists only if a human or agent wrote it down. For those, silence
CANNOT mean zero; it can only mean unknown. For a MEASURED metric, silence is a real, earned zero.
Same word today, two different epistemic states.

Run: py -m pytest tests/test_t337_scorecard_unrecorded_is_not_absent.py -q
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SRC = open(os.path.join(ROOT, "scripts", "arc_scorecard.py"), encoding="utf-8").read()


def test_p1_a_self_reported_metric_renders_unrecorded_not_no_signal():
    """The whole slice. A metric whose only signal is an annotation cannot report a zero -- it can
    only report that nobody wrote it down."""
    assert "UNRECORDED" in SRC, (
        "self-reported metrics must render UNRECORDED; '(no signal)' claims a measurement that "
        "was never taken")


# A source-shaped pin cannot see through the ways Python lets one string be written. The first
# drafts of P2/P3 failed because the required phrase is split across an f-string join
# ("this is NOT " f"evidence of absence"), so it never appears contiguously in the file -- the
# same blindness that made a grep for '"answers":' miss reply_meta["answers"] = m.id earlier
# tonight, and the same one that let a write hide behind a helper call in T336's P6. Three
# instances, one class. NORM collapses quotes, joins and whitespace so the pin reads what the
# program will PRINT rather than how it happens to be typed.
NORM = re.sub(r"\s+", " ", re.sub(r"[\"']\s*(?:f?[\"'])?", "", SRC)).lower()


def test_p2_unrecorded_says_it_is_not_evidence_of_absence():
    """A label alone still reads as a zero to a tired reader at 3am. The render must carry the
    epistemic claim in words, not just the word."""
    assert "unrecorded" in NORM, "UNRECORDED not rendered"
    assert "not evidence of absence" in NORM, (
        "the UNRECORDED render must SAY it is not evidence of absence -- otherwise the rename "
        "moves the lie rather than removing it")


def test_p3_the_two_states_are_distinguished_by_whether_a_detector_exists():
    """SELF_REPORT is the discriminator already in this file: those metrics have no detector, so
    their silence can only be unknown. A MEASURED metric's silence is an earned zero and must
    keep saying so -- collapsing both into UNRECORDED would be the same error pointing the other
    way, and would make a real zero unactionable."""
    assert "SELF_REPORT = " in SRC, "the self-reported set must stay declared in this file"
    branch = re.search(r"elif\s+mid\s+in\s+SELF_REPORT\s*:", SRC)
    assert branch, (
        "UNRECORDED must be gated on SELF_REPORT membership, not applied to every silent "
        "metric -- a measured zero and an unrecorded unknown are different findings")
    assert SRC.index("UNRECORDED") > branch.start(), (
        "the UNRECORDED render must sit INSIDE the SELF_REPORT branch")


def test_p4_a_measured_metric_keeps_its_honest_zero():
    """The guard against over-correcting: MEASURED metrics (M3, M11) compute from git and their
    silence IS a finding. If the fix swallowed those into 'unknown' we would have traded a false
    negative for a false unknown, which is worse -- it makes a real zero unactionable."""
    assert "MEASURED" in SRC, "the measured/self-reported split must stay visible in the render"
