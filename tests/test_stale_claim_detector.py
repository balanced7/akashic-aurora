"""RED: the stale-claim detector -- a lesson's ANCHORS can resolve while its CLAIM is false.

THE LIVE RECEIPT, 2026-08-16. A blind-half study cited
`the_oldest_wish_was_never_filed_as_one`, whose central finding is "WISHLIST holds 130 open
wishes and NOT ONE is about naming coherence". Every anchor resolved -- the wishlist exists,
the citations are real, the lesson is honest. And the claim had been false for nine days:
W133 was filed on 2026-08-07 BY THE SESSION THAT WROTE THE LESSON. I nearly re-filed the
operator's oldest wish on the strength of a citation that checked out.

THE GAP THIS FILLS, named by deepseek in July and unbuilt since
(research:web:build_system_and_tms_invalidation): our anchor resolver answers "does this
source EXIST?" and never "does this source still SUPPORT the claim?" -- RAG CiteCheck's
second dimension, which that research explicitly flagged as the tier-4 problem we do not
attempt. JTMS supplies the other half: a belief stands while at least one justification
stands, so a lesson is suspect only when its own evidence has moved, not merely aged.

THE DETECTABLE SUBCLASS, and it is deliberately narrow: claims of COUNT or ABSENCE over a
named artifact -- "130 wishes and not one is X", "zero entries", "nothing cites Y", "no
guard exists". Those are mechanically re-checkable against the artifact at HEAD. Claims of
judgement are not, and this detector must not pretend otherwise; it PROPOSES a re-read, it
never retracts a lesson (instrument_proposes_never_self_ratifies).

Run: py -m pytest tests/test_stale_claim_detector.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import staleness as S  # noqa: E402


# ---------------------------------------------------------------- P1: it finds the shape
def test_p1_absence_claims_are_detected_with_their_artifact():
    """The claim must be located AND the artifact it speaks about named, or a reviewer
    cannot re-check it."""
    text = ("WISHLIST holds 130 open wishes and NOT ONE is about naming coherence -- "
            "the organ built to catch friction has never been pointed at it.")
    claims = S.extract_checkable_claims(text)
    assert claims, "an explicit count-plus-absence claim was not detected"
    c = claims[0]
    assert c["kind"] in ("absence", "count")
    assert "wishlist" in c["artifact"].lower()


def test_p1b_judgement_claims_are_left_alone():
    """A detector that flags opinions will be turned off within a week. Only mechanically
    re-checkable shapes qualify."""
    text = ("He root-causes twice, and that is an epistemologist's skill rather than a "
            "manager's -- most people stop at the first why.")
    assert S.extract_checkable_claims(text) == []


# ---------------------------------------------------------------- P2: the live case
def test_p2_the_receipt_case_is_flagged_stale():
    """The exact lesson that nearly cost us: anchors resolve, claim is false."""
    verdict = S.recheck_claim({
        "kind": "absence",
        "artifact": "docs/WISHLIST.md",
        "needle": "naming coherence",
        "quote": "NOT ONE is about naming coherence",
    })
    assert verdict["still_holds"] is False, (
        "W133 has been in WISHLIST since 2026-08-07 -- the absence claim is refuted")
    assert verdict["evidence"], "a refutation must carry the line that refutes it"


def test_p2b_a_claim_that_still_holds_says_so_affirmatively():
    verdict = S.recheck_claim({
        "kind": "absence",
        "artifact": "docs/WISHLIST.md",
        "needle": "zzz_a_phrase_that_appears_nowhere_zzz",
        "quote": "nothing about zzz",
    })
    assert verdict["still_holds"] is True
    assert verdict["checked"] is True, "an affirmative all-clear, distinguishable from a skip"


# ---------------------------------------------------------------- P3: honest unreachables
def test_p3_a_missing_artifact_is_unevaluable_not_stale():
    """Absence of evidence is not evidence of staleness -- the confident-zero disease in
    detector form. A vanished artifact means UNCHECKABLE."""
    verdict = S.recheck_claim({
        "kind": "absence", "artifact": "docs/THIS_FILE_IS_GONE.md",
        "needle": "anything", "quote": "nothing about anything",
    })
    assert verdict["checked"] is False
    assert verdict["still_holds"] is None, "unknown is not False"
    assert "unreachable" in verdict["why"].lower() or "missing" in verdict["why"].lower()


# ---------------------------------------------------------------- P4: proposes, never acts
def test_p4_the_detector_has_no_write_path():
    """It surfaces a re-read; it does not retract, bench, or edit a lesson. Five arrivals in
    this house have landed on instrument_proposes_never_self_ratifies."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(S))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & {"subprocess", "shutil", "requests", "redis"})
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            called.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
    for forbidden in ("write_text", "bench", "mark_benched", "retract", "learn", "system"):
        assert forbidden not in called, f"the detector calls {forbidden!r}"


# ---------------------------------------------------------------- P5: the report is a frame
def test_p5_the_sweep_reports_its_own_scope():
    rep = S.sweep(limit=25)
    assert "examined" in rep and "checkable" in rep
    assert rep["examined"] >= 0
    assert "scope" in rep, "a coverage claim must state what it globbed (the frame law)"
    for item in rep.get("stale", []):
        assert item.get("lesson") and item.get("evidence"), \
            "every flagged lesson names itself and the line that refutes it"
