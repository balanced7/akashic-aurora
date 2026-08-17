"""T176 s1 RED: total kind resolution -- an unlisted kind must never read as a decision.

THE DEFECT, in the ledger's own words: "because every policy is a membership test, a miss is
indistinguishable from a deliberate exclusion, so an unlisted kind is silently not-an-answer,
not-salient, not-wake-worthy." Census: 31 kinds, 14 hand-maintained policy sets across 11
files, 17/31 kinds in one set or fewer. Confirmed casualty on the record:
bifrost_review_kind_is_silent_2026_07_29.

THIS IS NOT NEW DOCTRINE. It is the invariant the house already enforces in three other
organs, applied to the taxonomy:
    BoundaryOutcome  -- a boundary that fails without saying why is unrepresentable (T170)
    R14              -- an evicted payload confesses; it never renders as "no event"
    coverage frame   -- a count without the scope it globbed is not a coverage claim
    T176 (this)      -- an unlisted kind resolves UNCLASSIFIED, never a silent False

DESIGN, per the fenced adversarial pass recorded in the ledger row: the vocabulary stays
OPEN (closing it creates a classification bottleneck and kills extensibility between
independently developed agents); registration stays SPARSE and PER-DIMENSION (declare a kind
wake-worthy without touching salience -- that orthogonality is the 14-set design's one real
virtue); RESOLUTION becomes TOTAL.

SCOPE OF s1, stated so the next seat does not think it was skipped: this slice builds the
registry, total resolution, and the coverage report, SEEDED FROM the live sets so behaviour
is byte-identical today. It deliberately does NOT rewire the 14 call sites -- that is s2, by
strangler fig, one door at a time with parity pins (the T044/T045 precedent).

FOUND WHILE SEEDING: "ask" appeared FORKED THREE WAYS. agent/bifrost_pull.py's _ASK_KINDS
carried `blocker`; agent_cli.py's ASK_KINDS and core/comm/packet_spec.py's STALE_ASK_KINDS
did not. The registry's job was not to resolve that (it needs a human ruling); it was to make
it IMPOSSIBLE TO MISS.

RULED 2026-08-17 (T332), and the answer inverted the question: the three sets were three
DIFFERENT questions sharing one word, not one concept in dispute. `plane` is now a required
argument to resolve(), which is why every call below names one. P7 was rewritten to pin the
fork-reporting MECHANISM against an injected fork rather than the resolved `ask` instance --
retiring a pin because its instance got fixed would quietly retire the instrument too.

Run: py -m pytest tests/test_t176_s1_kind_resolution.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import kinds as K  # noqa: E402


# ---------------------------------------------------------------- P1: totality
def test_p1_an_unknown_kind_resolves_unclassified_not_false():
    """THE WHOLE SLICE, in one assertion. A kind nobody registered is not a decision --
    it is an absence of one, and the caller must be able to tell the difference."""
    v = K.resolve("brand_new_kind_nobody_registered", "wake_worthy", plane="bus_kind")
    assert v.classified is False, "an unregistered kind cannot be classified"
    assert v.value is None, "an unclassified verdict carries NO policy answer, not False"
    assert v.why, "an unclassified verdict must say why -- silence is the defect"


def test_p1b_a_registered_kind_resolves_with_a_real_answer():
    yes = K.resolve("handoff", "wake_worthy", plane="bus_kind")
    assert yes.classified is True and yes.value is True
    no = K.resolve("trace", "wake_worthy", plane="bus_kind")
    assert no.classified is True and no.value is False, (
        "a kind registered in the dimension's universe but NOT in the set is a real NO -- "
        "that is the distinction the whole organ exists to make")


def test_p1c_resolve_never_returns_a_bare_bool():
    """The BoundaryOutcome discipline: the type itself makes the silent answer
    unrepresentable, so no call site can accidentally treat absence as denial."""
    for kind in ("handoff", "trace", "not_a_kind_at_all"):
        v = K.resolve(kind, "wake_worthy", plane="bus_kind")
        assert not isinstance(v, bool), f"resolve({kind!r}) returned a bare bool"
        assert hasattr(v, "classified") and hasattr(v, "value") and hasattr(v, "why")


# ---------------------------------------------------------------- P2: unknown dimension
def test_p2_an_unknown_dimension_is_also_unclassified_and_loud():
    v = K.resolve("handoff", "dimension_that_does_not_exist", plane="bus_kind")
    assert v.classified is False
    assert "dimension" in v.why.lower(), "the confession must name WHICH half was missing"


# ---------------------------------------------------------------- P3: parity, the safety pin
@pytest.mark.parametrize("dimension,expected", [
    ("wake_worthy", {"request", "handoff", "reply", "blocker", "question", "completion",
                     "nudge"}),
    ("answer", {"reply", "handoff", "completion"}),
    ("escalate", {"request", "handoff", "question", "blocker"}),
    ("salient", {"handoff", "decision", "completion", "blocker"}),
    ("flaggable", {"handoff", "blocker"}),
    ("long", {"handoff", "request", "question", "blocker"}),
    ("trace", {"trace", "steer", "nudge", "ledger_update", "resolved"}),
])
def test_p3_the_registry_reproduces_the_live_sets_exactly(dimension, expected):
    """s1 must be a NO-OP on behaviour. If the registry disagrees with the shipped set by
    one kind, some door changes its mind the day it is rewired -- and that is how a
    taxonomy slice becomes an outage."""
    assert K.members(dimension) == expected


# ---------------------------------------------------------------- P4: coverage is a number
def test_p4_coverage_reports_per_dimension_and_names_the_universe():
    cov = K.coverage()
    assert cov["dimensions"], "a coverage report with no dimensions is a broken instrument"
    wake = cov["dimensions"]["wake_worthy"]
    assert wake["members"] == 7
    assert wake["universe"] >= wake["members"]
    assert isinstance(cov["kinds_total"], int) and cov["kinds_total"] > 0
    # the frame that must ship with the number (the coverage-contract lesson)
    assert "sources" in cov, "a coverage claim must name where its sets came from"


# ---------------------------------------------------------------- P5: sparse, per-dimension
def test_p5_registration_is_sparse_and_orthogonal():
    """Declaring a kind wake-worthy must not make it salient. The 14-set design's one real
    virtue was orthogonality; the fix must not trade it away for tidiness."""
    assert K.resolve("nudge", "wake_worthy", plane="bus_kind").value is True
    assert K.resolve("nudge", "salient", plane="bus_kind").value is False, (
        "nudge is wake-worthy but NOT salient -- if these moved together the registry "
        "collapsed two independent dimensions into one")


# ---------------------------------------------------------------- P6: the three planes
def test_p6_the_three_planes_are_named_and_note_is_shown_colliding():
    """'note' means three things on three planes WITH OPPOSITE POLICIES. The registry does
    not resolve that -- it makes it impossible to miss."""
    planes = K.planes()
    assert set(planes) >= {"bus_kind", "event_kind", "beat_kind"}
    collisions = K.plane_collisions()
    assert "note" in collisions, (
        "'note' is a bus kind, an event kind and a beat kind -- the collision the row names")
    assert len(collisions["note"]) >= 2


# ---------------------------------------------------------------- P7: the fork it found
def test_p7_a_forked_concept_is_reported_not_silently_merged(monkeypatch):
    """Found while seeding: 'ask' was three sets that disagreed -- bifrost_pull's _ASK_KINDS
    carried `blocker`, agent_cli's ASK_KINDS and packet_spec's STALE_ASK_KINDS did not. One
    concept, three memberships, no duplicate token: W134's forked-semantics class. The
    registry must SURFACE the disagreement rather than pick a winner, because picking one
    is a policy ruling and this organ proposes, never ratifies.

    T332 UPDATE: Daniil ruled on the `ask` instance 2026-08-17, so this pin no longer asserts
    that specific fork -- tests/test_t332_s1_ruling_the_forks.py holds the ruling. What stays
    here is the MECHANISM, exercised against an injected fork, because deleting this pin when
    its instance got resolved would silently retire the instrument that found it. The ruling
    also found the instrument's edge: forks() groups by NAME, so `ask` was three honest
    questions sharing a word rather than one concept in dispute."""
    monkeypatch.setattr(K, "_FORKS", {
        "synthetic": [
            {"source": "a.py:X_KINDS", "members": frozenset({"one", "two"})},
            {"source": "b.py:Y_KINDS", "members": frozenset({"one"})},
        ],
    })
    forks = K.forks()
    assert "synthetic" in forks, "a live fork must be reported, never silently merged"
    f = forks["synthetic"]
    assert len(f["variants"]) >= 2, "a fork with one variant is not a fork"
    assert "two" in f["differs_on"], (
        "naming WHICH kind differs is what makes the report actionable instead of an alarm")


def test_p7b_the_ruled_fork_is_gone_from_the_live_report():
    """The other half: a ruling that leaves the instrument still shouting has not been
    applied, only remembered."""
    assert "ask" not in K.forks(), "the ask fork was ruled (T332) and must not still report"
