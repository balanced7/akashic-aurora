"""RED pins for the app-package rung -- the rung the ladder did not have on 2026-08-24.

Every pin here is one registered falsifier from
docs/library/report/20260824_falsifiers-outage-fixes_d09856.md made executable. The
design law they enforce comes from the capstone of the instrument-honesty arc
([[the-stop-sign-and-the-green-light]]):

    a refusal must name a specific condition to fire; a confirmation can be produced
    by absence.

So the load-bearing function under test is `clear_refusals` -- the door that says NO --
and NOT the pass path. A check whose interesting behaviour is its pass path is usually a
check that cannot fail.

THE DEFECT THESE EXIST TO PREVENT: Sol's receipt for the 2026-08-24 repair reads
"11411 blocks, zero mismatches". If the block-map read fails and returns empty, then
"zero mismatches" over zero blocks is a PASS PRODUCED BY ABSENCE -- byte-for-byte the
`commits_since -> 0` defect (997f997a), which told every runner it was current for two
days because one emoji would not decode. Putting that defect inside the lever that
resurrects the conductor is the specific outcome these pins forbid.

Written BEFORE the implementation (M3 pre-registration). They are RED on arrival.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.fleet import app_package as ap

ROOT = Path(__file__).resolve().parents[1]


def _proof(*, files=2348, blocks=11411, size=629549194, mismatches=(),
           declared_blocks=11411, declared_files=2348):
    """A payload proof shaped like a real one. Defaults are the REAL numbers of
    Claude_1.28929.0.0, independently reproduced 2026-08-24 (2348 / 11411 /
    629549194) -- so a pin that passes here passes against the true magnitude, not
    against a toy."""
    return ap.PayloadProof(
        files=files, blocks=blocks, bytes=size,
        mismatches=list(mismatches),
        declared_files=declared_files, declared_blocks=declared_blocks)


PKG_OK = {"name": "Claude", "full_name": "Claude_1.28929.0.0_x64__pzs8sxrjxfjjc",
          "status": "Modified, NeedsRemediation",
          "install_location": r"C:\Program Files\WindowsApps\Claude_1.28929.0.0_x64__pzs8sxrjxfjjc"}


# ------------------------------------------------------------------ the pass path
# ONE pin for the pass, because the pass is the cheap half. Everything else is refusals.
def test_a_clean_proof_on_a_modified_package_has_no_refusals():
    assert ap.clear_refusals(PKG_OK, _proof(), elevated=True) == []


# ------------------------------------------------------------------ F1: mismatch
def test_F1_any_block_mismatch_refuses():
    """Corrupt one block and the rung must not clear the flag. Clearing the status on a
    damaged payload launches a corrupt app -- the one outcome worse than staying down."""
    r = ap.clear_refusals(PKG_OK, _proof(mismatches=["app.asar block 41"]), elevated=True)
    assert r, "a payload mismatch MUST refuse"
    assert any("mismatch" in x.lower() for x in r), r


# ------------------------------------------- F2: the pass produced by absence
def test_F2_empty_blockmap_refuses_and_does_not_read_as_zero_mismatches():
    """THE defect this module exists to prevent. Zero mismatches over zero blocks is
    not evidence of integrity; it is evidence of a failed read."""
    r = ap.clear_refusals(PKG_OK, _proof(files=0, blocks=0, size=0, mismatches=(),
                                         declared_files=0, declared_blocks=0),
                          elevated=True)
    assert r, "an EMPTY payload proof must refuse, never pass on 'no mismatches'"
    assert any(("no blocks" in x.lower() or "empty" in x.lower() or "zero" in x.lower())
               for x in r), r


def test_F2b_a_partial_verification_refuses():
    """The check ran but did not cover every declared block -- a cap, a timeout, an
    unreadable file. Absence of a mismatch in the part you read says nothing about the
    part you did not."""
    r = ap.clear_refusals(PKG_OK, _proof(blocks=9000, declared_blocks=11411),
                          elevated=True)
    assert r, "an INCOMPLETE verification must refuse"
    assert any(("incomplete" in x.lower() or "9000" in x) for x in r), r


def test_F2c_positive_counts_are_asserted_not_merely_absence_of_failure():
    """The rung must assert what it DID verify, not what it failed to find wrong.
    A file count of zero with a nonzero declared count is a broken read."""
    r = ap.clear_refusals(PKG_OK, _proof(files=0, declared_files=2348), elevated=True)
    assert r, "files=0 against a declared 2348 must refuse"


# ------------------------------------------------------------------ F3: no package
def test_F3_absent_package_refuses():
    """Aggregation over an empty set: no package found must never report success."""
    r = ap.clear_refusals(None, _proof(), elevated=True)
    assert r, "an absent package must refuse"
    assert any(("not found" in x.lower() or "absent" in x.lower() or "no package" in x.lower())
               for x in r), r


# ------------------------------------------------------------------ F5: elevation
def test_F5_unelevated_refuses_loudly_rather_than_no_opping_green():
    """ClearPackageStatus needs elevation. An unelevated run must REFUSE, not attempt
    the clear, silently fail, and hand back a green receipt."""
    r = ap.clear_refusals(PKG_OK, _proof(), elevated=False)
    assert r, "an unelevated run must refuse"
    assert any("elevat" in x.lower() for x in r), r


# --------------------------------------------------- only Modified earns a heal
def test_a_healthy_package_is_not_a_clear_candidate():
    """Status Ok: nothing to clear. The rung must not 'repair' a working package."""
    ok = dict(PKG_OK, status="Ok")
    r = ap.clear_refusals(ok, _proof(), elevated=True)
    assert r, "a healthy package must refuse the clear"


def test_an_unrecognised_bad_status_refuses_by_name_rather_than_guessing():
    """Nominal drift guard: a state we have no rung for must say so, not be silently
    treated as the one state we DO know how to fix."""
    weird = dict(PKG_OK, status="Tampered")
    r = ap.clear_refusals(weird, _proof(), elevated=True)
    assert r, "an unrecognised status must refuse"
    assert any("tampered" in x.lower() for x in r), \
        f"the refusal must NAME the state it does not handle, got {r}"


# ------------------------------------------------------------------ F6: receipt
def test_F6_the_receipt_carries_the_counts_it_actually_evaluated():
    """'verified' is a word. 2348/11411/629549194 is a receipt. A green must be
    traceable to a condition that was actually evaluated."""
    line = ap.proof_receipt(_proof())
    for n in ("2348", "11411", "629549194"):
        assert n in line, f"receipt must carry {n}: {line!r}"


def test_F6b_an_empty_proof_receipt_does_not_read_as_success():
    line = ap.proof_receipt(_proof(files=0, blocks=0, size=0, declared_files=0,
                                   declared_blocks=0)).lower()
    assert "verified" not in line or "0" in line, \
        f"an empty proof must not render as a bare 'verified': {line!r}"


# ------------------------------- F4: the oracle is a launch, not a status field
def test_F4_app_verification_is_a_launch_not_a_status_read():
    """Sol's step 6 was a real launch. If the rung proves recovery by re-reading the
    status field it just wrote, it is asking the gauge how it is feeling.

    A source pin: the app verifier must reach for a launch/process probe, and must not
    be satisfied by the package status alone."""
    src = (ROOT / "core" / "fleet" / "app_package.py").read_text(encoding="utf-8")
    fn = re.search(r"def verify_recovered\((.|\n)*?(?=\ndef |\Z)", src)
    assert fn, "verify_recovered must exist"
    body = fn.group(0)
    assert re.search(r"launch|Start-Process|process|running", body, re.I), \
        "verify_recovered must probe an actual launch"
    assert not re.search(r"return\s+.*status\s*==\s*[\"']Ok", body), \
        "verify_recovered must NOT be satisfied by the status field alone"


# ------------------------------------------------------ the revive ladder wiring
def test_the_ladder_has_an_app_rung_at_all():
    """2026-08-24: _ORDER was (redis, daemon, gateway). The application layer that
    HOSTS the conductor was not in the ladder's ontology, so !revive ran twice and
    reported that it ran while nothing it could see was wrong."""
    import scripts.revive as revive
    assert "app" in revive._ORDER, \
        "the ladder must have a rung at the application layer"


def test_converge_names_what_it_cannot_reach_instead_of_reporting_a_boring_run():
    """The sentence Daniil did not get at 12:05 on 2026-08-24. A lever that recovered
    nothing must not report 'touched NOTHING (a boring run is a successful run)' when
    the thing that was down is a thing it has no rung for."""
    import scripts.revive as revive
    src = (ROOT / "scripts" / "revive.py").read_text(encoding="utf-8")
    assert hasattr(revive, "unreachable_report"), \
        "converge must be able to name targets it has no rung for"
    assert "no rung" in src.lower(), \
        "the refusal must say, in words, that no rung reaches the fault"
