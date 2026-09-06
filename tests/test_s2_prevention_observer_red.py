"""RED pins for S2 -- the prevention observer (recall's AAR).

Spec: docs/library/design/20260905_s2-the-eye-wired-outcome-observer-recall_6abac5.md
Fenced by Heimdall (bus 1788654202356-0); his corrections are pinned here, not just prosed.

WHY THIS FILE EXISTS
--------------------
`_log_outcome_stage` (at_action.py:973) has been writing the contrastive record for weeks and
NOBODY CONSUMES IT. Its own docstring: "the credited-flip numerator counts RESCUE, never
PREVENTION ... the single most valuable thing a lesson can do (stop the failure from happening
at all) was invisible to the only value metric the system had." Live counts today: 18 flips vs
3414 prevention candidates. The value metric sees 18 events and is blind to 3414.

THE TWO CORRECTIONS THAT ARE PINNED, NOT ASSUMED
------------------------------------------------
1. ABSENCE IS NOT COMPLIANCE (learn:clause_evidence_is_only_as_sound_as_the_id_namespace):
   "the join is directional and BOTH directions fail ... absence never means 'not done' and
   presence never means 'done'." A missing repeat does NOT license a COMPLIED verdict. The
   deterministic join can mint VIOLATED (positive evidence) and must fall to UNKNOWABLE
   everywhere else. P2 is the pin that stops a comfortable lie.
2. BOTH SIDES THROUGH THEIR REAL PRODUCERS
   (learn:a_pin_that_feeds_both_producers_one_hand_built_shape_proves_the_seam_not_the_wire):
   the stage side is written by `_log_outcome_stage`, the repeat side by
   `LearningStore.record_repeat`. A hand-built dict would prove the seam, not the wire.
"""
from __future__ import annotations

import json
import os
import pytest

pytestmark = pytest.mark.usefixtures("_isolated_stage")

VERDICTS = {"COMPLIED", "VIOLATED", "INAPPLICABLE", "UNKNOWABLE"}


@pytest.fixture
def _isolated_stage(tmp_path, monkeypatch):
    """Point the stage dir at a temp tree so pins never read the live 6051 rows."""
    from core.recall import at_action as aa
    stage = tmp_path / "stage"
    stage.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(aa, "_STAGE_DIR", str(stage), raising=False)
    return stage


def _write_stage_via_producer(session, target, *, ok, sources, flipped=False):
    """P8: construct the stage side through its REAL producer, never a hand-built dict."""
    from core.recall import at_action as aa
    aa._log_outcome_stage(session, target, ok, surfaced_sources=sources,
                          flipped=flipped, credited=0, agent_id="claude")


# --------------------------------------------------------------------------- P1
def test_p1_join_refuses_an_unresolvable_lesson_pointer():
    """A repeat's target must resolve; an unresolvable pointer never enters the observation.

    record_repeat already raises on an unknown lesson ("without a resolvable target it is just
    an unverifiable claim"). The observer must not re-open that hole by accepting a stage row
    whose source names a lesson the corpus does not have.
    """
    from core.recall import prevention
    rows = prevention.observe(sources_resolver=lambda s: False)   # nothing resolves
    assert rows == [] or all(r["verdict"] == "UNKNOWABLE" for r in rows), \
        "an unresolvable lesson pointer must never yield a settled verdict"


# --------------------------------------------------------------------------- P2
def test_p2_absence_of_a_repeat_is_never_compliance():
    """THE pin. No COMPLIED may be minted from the mere absence of a repeat.

    This is the directional-join law. If this pin ever goes green by inventing COMPLIED from
    silence, the instrument has started lying in the one direction it must not.
    """
    from core.recall import prevention
    _write_stage_via_producer("s-p2", "py agent_cli.py boot claude", ok=True,
                              sources=["learn:experiment:alpha"])
    rows = prevention.observe(repeats={})          # no repeats at all
    assert rows, "a prevention candidate should be observed"
    assert not any(r["verdict"] == "COMPLIED" for r in rows), \
        "absence of a repeat is not evidence of compliance -- must be UNKNOWABLE"
    assert all(r["verdict"] in VERDICTS for r in rows)


# --------------------------------------------------------------------------- P3
def test_p3_violated_needs_positive_evidence_and_carries_its_citation():
    """VIOLATED is minted ONLY from a filed repeat, and the row must cite it."""
    from core.recall import prevention
    _write_stage_via_producer("s-p3", "py scripts/mirror.py msg", ok=True,
                              sources=["learn:experiment:beta"])
    repeats = {"learn:experiment:beta": [{"id": "beta:20260905T000000:abcd1234",
                                          "recall_outcome": "fired", "at": "2026-09-05T00:00:00"}]}
    rows = prevention.observe(repeats=repeats)
    viol = [r for r in rows if r["verdict"] == "VIOLATED"]
    assert viol, "a filed repeat against a surfaced lesson must yield VIOLATED"
    assert viol[0].get("evidence"), "a VIOLATED row must carry its repeat citation"


# --------------------------------------------------------------------------- P4
def test_p4_denominator_law_unknowable_never_enters_a_rate():
    """UNKNOWABLE is excluded from every rate and reported as coverage beside it."""
    from core.recall import prevention
    for i in range(3):
        _write_stage_via_producer(f"s-p4-{i}", "cmd", ok=True, sources=["learn:experiment:g"])
    rep = prevention.report(repeats={})
    assert "coverage" in rep, "a rate without its coverage is the confident-zero disease"
    for key, val in rep.get("rates", {}).items():
        assert 0.0 <= val <= 1.0
    settled = rep.get("settled", 0)
    assert rep["rates"] == {} or settled > 0, \
        "no rate may be published on a fully-unsettled sample"


# --------------------------------------------------------------------------- P5
def test_p5_control_arm_is_computed_not_assumed():
    """The contrastive arm (success AND NOT surfaced) must be counted from the log."""
    from core.recall import prevention
    _write_stage_via_producer("s-p5", "cmd-a", ok=True, sources=["learn:experiment:h"])
    _write_stage_via_producer("s-p5", "cmd-b", ok=True, sources=[])      # control arm
    rep = prevention.report(repeats={})
    assert rep["control_arm"] >= 1, "success-without-surfaced rows are the control arm"
    assert rep["prevention_candidates"] >= 1


# --------------------------------------------------------------------------- P6
def test_p6_observer_writes_nothing_to_recall_or_the_corpus(monkeypatch):
    """Read-only: the observer must not record feedback or mutate lesson state."""
    from core.recall import at_action as aa
    from core.recall import prevention
    called = []
    monkeypatch.setattr(aa, "record_feedback",
                        lambda *a, **k: called.append(a) or True, raising=False)
    _write_stage_via_producer("s-p6", "cmd", ok=True, sources=["learn:experiment:i"])
    prevention.observe(repeats={})
    assert not called, "the observer must never write credit -- observation, not adjudication"


# --------------------------------------------------------------------------- P7
def test_p7_determinism_same_input_same_output():
    """Seeded/ordered: same stage state + same repeats => byte-identical report."""
    from core.recall import prevention
    for i in range(4):
        _write_stage_via_producer(f"s-p7-{i}", f"cmd{i}", ok=True,
                                  sources=[f"learn:experiment:j{i%2}"])
    a = json.dumps(prevention.report(repeats={}), sort_keys=True, default=str)
    b = json.dumps(prevention.report(repeats={}), sort_keys=True, default=str)
    assert a == b, "an unre-auditable number is not evidence"


# --------------------------------------------------------------------------- P8
def test_p8_confounds_are_named_in_the_output_itself():
    """Exposure bias and self-selection must ride WITH the number, not in a doc.

    The stage log's own rule: "BOTH feedback loops are confounded (the positive by
    self-inflation; the negative by exposure-bias)". A report that omits them invites the
    steer its docstring forbids.
    """
    from core.recall import prevention
    _write_stage_via_producer("s-p8", "cmd", ok=True, sources=["learn:experiment:k"])
    rep = prevention.report(repeats={})
    conf = " ".join(rep.get("confounds", [])).lower()
    assert "exposure" in conf, "exposure bias must be named beside the rate"
    assert rep.get("steers") is False, "this observation may never feed ranking"
