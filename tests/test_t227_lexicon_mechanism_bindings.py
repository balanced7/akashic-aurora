"""T227 RED: bind each LEXICON term to the MECHANISMS that implement it, and audit the binding.

THE ARC THIS CLOSES. Tonight's proof: forked semantics is the DUAL of a homonym -- one
CONCEPT implemented by several MECHANISMS whose tokens deliberately differ -- so a token-level
tool hunts a shared token, which is exactly what this class is DEFINED by lacking. `drained`
binds three cursor families at bus.py:249/265/1201 and the token appears in none of them.
Corollary: the guard Daniil has asked for since 2026-06-19 CANNOT be a grep over source.

THE WAY THROUGH, contributed by claude#42d00626 and the best idea of the exchange:

    the fan DRAFTS the binding table  ->  a human RATIFIES  ->  a checker VERIFIES forever

That converts "costly to author" from a permanent human cost into a ONE-TIME fan cost, and it
IS the grep everyone wanted -- just pointed at a TABLE instead of at the source. Two things
make it affordable now that did not exist this morning: a measured BASE RATE (~1 in 14 terms
carry a genuine multi-mechanism sense, so the load-bearing vocabulary is 50-100 terms, not
thousands) and a CALIBRATED DRAFTER (sift's consensus floor, reproducing hand-adjudication
3/3).

REUSES EXISTING MACHINERY RATHER THAN ADDING ANY. `core/toolbelt/audit.py` already does
belief-vs-state with MATCH/DRIFT/UNKNOWN rows and a Domain protocol; `terms.lexicon_terms()`
already parses LEXICON.md. This is a new DOMAIN, not a new checker -- and after a night in
which the standing lesson was "check for the successor before writing one", building a
parallel auditor would have been the joke writing itself.

THREE RULES, and only the second is new work:
  R1 MISSING   -- a bound mechanism no longer resolves. The binding rotted.
  R2 UNCLAIMED -- something matches the concept's discover pattern and is NOT in its list.
                  THE RATCHET: a new mechanism joined the concept silently, which is exactly
                  how `drained` grew a third cursor family.
  R3 DOUBLE    -- one mechanism bound to two concepts: the dual of a homonym, and the thing
                  no token checker can see.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.toolbelt import lexicon_bindings as LB  # noqa: E402


# ------------------------------------------------------------------ the table
def test_the_binding_table_exists_and_is_machine_readable():
    """A binding table that only a human can read is a document, not a guard."""
    tbl = LB.load_bindings()
    assert tbl, "no bindings loaded"
    for concept, rec in tbl.items():
        assert rec.get("mechanisms"), f"{concept} binds nothing"
        assert rec.get("ratified_by"), (
            f"{concept} has no ratified_by -- a binding the fan DRAFTED and nobody ratified "
            f"is a claim, not a definition (T207: the therefore is not automatable)")


def test_drained_binds_the_three_cursor_families():
    """The arc's canonical case, and the reason a token search cannot find it: the word
    `drained` appears in NONE of the three keys it names."""
    tbl = LB.load_bindings()
    mechs = tbl["drained"]["mechanisms"]
    pats = " ".join(m["pattern"] for m in mechs)
    assert "cursor:seat:" in pats and "cursor:lane:" in pats, \
        "the seat and lane cursor families are the fork; both must be bound"
    assert len(mechs) >= 3


# ------------------------------------------------------------------ R1 MISSING
def test_a_mechanism_that_no_longer_resolves_is_drift():
    """The binding rotted -- a mechanism was renamed or deleted while the table still claims
    it. Cheap to check, and the failure mode a prose LEXICON cannot catch at all."""
    rows = LB.audit_bindings(bindings={
        "ghost": {"ratified_by": "test",
                  "mechanisms": [{"file": "core/comm/bus.py",
                                  "pattern": "a_symbol_that_does_not_exist_anywhere_xyzzy"}]}})
    assert any(r.verdict == "DRIFT" and r.rule == "MISSING" for r in rows), \
        [(r.verdict, r.rule) for r in rows]


def test_a_resolving_mechanism_is_a_match():
    rows = LB.audit_bindings(bindings={
        "real": {"ratified_by": "test",
                 "mechanisms": [{"file": "core/comm/bus.py", "pattern": "cursor:seat:"}]}})
    assert any(r.verdict == "MATCH" for r in rows)


# ------------------------------------------------------------------ R2 UNCLAIMED (the ratchet)
def test_an_unclaimed_mechanism_matching_the_pattern_is_drift():
    """THE RATCHET, and the rule that earns this whole build. A concept declares a `discover`
    pattern; anything matching it that is NOT in the mechanism list has joined the concept
    silently. That is precisely how `drained` grew a third cursor family with nobody noticing,
    and the reason W133 has been open since 2026-06-19."""
    rows = LB.audit_bindings(bindings={
        "cursorish": {"ratified_by": "test",
                      "discover": r"\{self\.ns\}:cursor:",
                      "discover_files": ["core/comm/bus.py"],
                      # deliberately binds only ONE of the three live families
                      "mechanisms": [{"file": "core/comm/bus.py",
                                      "pattern": "cursor:seat:"}]}})
    drift = [r for r in rows if r.verdict == "DRIFT" and r.rule == "UNCLAIMED"]
    assert drift, "an unlisted mechanism matching the discover pattern must be flagged"
    assert any("cursor:lane:" in str(r.detail) or "cursor:" in str(r.detail) for r in drift)


def test_a_fully_claimed_concept_raises_no_unclaimed_row():
    """The ratchet must go quiet once the table is complete, or nobody will keep it."""
    rows = LB.audit_bindings(bindings={
        "cursorish": {"ratified_by": "test",
                      "discover": r"\{self\.ns\}:cursor:seat:",
                      "discover_files": ["core/comm/bus.py"],
                      "mechanisms": [{"file": "core/comm/bus.py",
                                      "pattern": "cursor:seat:"}]}})
    assert not [r for r in rows if r.rule == "UNCLAIMED"]


# ------------------------------------------------------------------ R3 DOUBLE-BOUND
def test_one_mechanism_bound_to_two_concepts_is_drift():
    """The DUAL of a homonym, and the thing no token checker can see: two concepts quietly
    sharing one implementation means one of them is lying about what it is."""
    m = {"file": "core/comm/bus.py", "pattern": "cursor:seat:"}
    rows = LB.audit_bindings(bindings={
        "conceptA": {"ratified_by": "t", "mechanisms": [m]},
        "conceptB": {"ratified_by": "t", "mechanisms": [dict(m)]}})
    assert any(r.verdict == "DRIFT" and r.rule == "DOUBLE-BOUND" for r in rows)


# ------------------------------------------------------------------ honesty
def test_an_unreadable_file_is_unknown_never_drift():
    """UNKNOWN stays representable. A file this process cannot read is not evidence that a
    binding rotted -- reading it as DRIFT would be the absence-inference this whole arc is
    about, committed by the guard built to end it."""
    rows = LB.audit_bindings(bindings={
        "x": {"ratified_by": "t",
              "mechanisms": [{"file": "no/such/file/anywhere.py", "pattern": "z"}]}})
    assert any(r.verdict == "UNKNOWN" for r in rows)
    assert not any(r.verdict == "DRIFT" for r in rows)


def test_the_live_table_audits_clean_or_says_why():
    """THE POINT OF THE WHOLE THING, run against the real tree. Not asserting zero DRIFT --
    asserting that every row is EXPLAINED, so a human ratifying the table sees a located
    claim rather than a number."""
    rows = LB.audit_bindings()
    assert rows, "the live table produced no rows"
    for r in rows:
        assert r.verdict in {"MATCH", "DRIFT", "UNKNOWN"}
        if r.verdict != "MATCH":
            assert r.detail and r.rule, f"{r.entry_ref}: a non-MATCH row must locate itself"
