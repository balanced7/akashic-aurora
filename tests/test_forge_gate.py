"""Forge F1 gate (core/recall/forge.py) -- characterization.

The discipline this must prove (design sec.4/sec.9 F1, dual-derived and locked):
  - a DEGRADED edit (loses the terms that earned credit) is REJECTED on axis 1,
  - a GOOD edit (keeps credited matching, stops noise matching) PASSES with axis-2 improvement,
  - floors: token budget (40%), parseable trigger clause,
  - an equal-value rewrite is REJECTED (churn is not progress),
  - rehab class (never credited): axis 1 vacuous, axis 2 improvement carries the PASS,
  - FAIL stamps the durable rejected-edit buffer; PASS + apply swaps text reversibly
    (previous text retained, provisional stamped, rollback restores).

Injected fakes + FileStore-backed LearningStore only -- never canonical Redis.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.forge import gate_edit, apply_edit

FLOOR = 0.05   # explicit floor for determinism (the calibrated default is env-tunable)

INCUMBENT = ("Use when editing the consolidator seam pipeline, before refactoring: route "
             "every source through the one consolidator seam quickly. Don't when prototyping.")
GOOD_EDIT = ("Use when editing the consolidator seam, before refactoring: route every "
             "source through the one consolidator seam. Don't when prototyping.")
DEGRADED_EDIT = ("Use when editing code, before refactoring: be careful and think twice. "
                 "Don't when prototyping.")
NO_TRIGGER_EDIT = "Route every source through the one consolidator seam."
BLOATED_EDIT = INCUMBENT + (" Also always remember to check the logs, update the docs, "
                            "ping the fleet, snapshot the store, rotate the ledger, and "
                            "review every single downstream consumer module carefully "
                            "before and after every change you ever make anywhere.")


class _FakeStore:
    def __init__(self, recs):
        self._recs = recs
    def load_all_learnings_from_store(self):
        return list(self._recs)


def _corpus():
    return _FakeStore([
        {"experiment_name": "seam_guard", "success": "yes", "recommendation": INCUMBENT},
        {"experiment_name": "noisy_lesson", "success": "yes",
         "recommendation": "Use when running any pipeline task quickly, before starting: "
                           "check the pipeline configuration first. Don't when offline."},
        {"experiment_name": "redis_probe", "success": "no",
         "recommendation": "Use when a filtered port hangs connect, before blaming code: "
                           "probe reachability first. Don't when the port is known-open."},
    ])


# seam_guard: credited on the consolidator path; noise on an unrelated pipeline command.
EVENTS = [{"kind": "flip", "at": "2026-07-08T10:00:00",
           "detail": {"target": "p:core/primitives/consolidator.py", "credited": 2,
                      "sources": ["learn:experiment:seam_guard"]}}]
INJECTIONS = [
    {"at": 1.0, "t": "p:core/primitives/consolidator.py", "s": ["learn:experiment:seam_guard"]},
    {"at": 2.0, "t": "c:py run pipeline task quickly", "s": ["learn:experiment:seam_guard"]},
]


def _gate(exp, draft, store=None, events=EVENTS, injections=INJECTIONS):
    return gate_edit(exp, draft, learning_store=store or _corpus(),
                     events=events, injections=injections, min_relevance=FLOOR)


def test_degraded_edit_rejected_on_axis1():
    rep = _gate("seam_guard", DEGRADED_EDIT)
    assert rep["verdict"] == "FAIL", rep
    assert rep["axis1"]["lost"], "dropping the credited terms must lose the credited context"
    assert any("axis 1" in r for r in rep["reasons"]), rep["reasons"]
    print("\n--- degraded edit ---\n  loses credited context -> FAIL on axis 1 OK")


def test_good_edit_passes_with_axis2_improvement():
    rep = _gate("seam_guard", GOOD_EDIT)
    assert rep["verdict"] == "PASS", rep
    assert rep["axis1"]["kept"] == rep["axis1"]["credited_contexts"] == 1
    assert rep["axis2"]["improved"] and not rep["axis2"]["regressed"], rep["axis2"]
    assert rep["axis2"]["incumbent_hits"] > rep["axis2"]["variant_hits"]
    print("--- good edit ---\n  keeps credited match, stops noise match -> PASS OK")


def test_equal_rewrite_is_churn_not_progress():
    rep = _gate("seam_guard", INCUMBENT)
    assert rep["verdict"] == "FAIL", rep
    assert any("no measurable improvement" in r for r in rep["reasons"]), rep["reasons"]
    print("--- equal rewrite ---\n  identical text -> FAIL (churn gate) OK")


def test_floor_checks_budget_and_trigger():
    rep = _gate("seam_guard", BLOATED_EDIT)
    assert rep["verdict"] == "FAIL" and not rep["checks"]["budget"]["ok"], rep["checks"]
    rep2 = _gate("seam_guard", NO_TRIGGER_EDIT)
    assert rep2["verdict"] == "FAIL" and not rep2["checks"]["trigger"]["ok"], rep2["checks"]
    print("--- floors ---\n  40% token budget + trigger-clause parseability enforced OK")


def test_rehab_class_vacuous_axis1_axis2_carries():
    # noisy_lesson: never credited (no flip events), fires on an unrelated target it never helped
    inj = [{"at": 3.0, "t": "c:py run pipeline task quickly", "s": ["learn:experiment:noisy_lesson"]}]
    # genuinely tightened: the promiscuous terms (pipeline/task/quickly) are GONE -- that
    # removal is the whole point of forging a noisy lesson
    tightened = ("Use when configuring cron schedules, before starting: check the "
                 "schedule configuration first. Don't when offline.")
    rep = gate_edit("noisy_lesson", tightened, learning_store=_corpus(),
                    events=[], injections=inj, min_relevance=FLOOR)
    assert rep["axis1"]["vacuous"] is True and rep["axis1"]["credited_contexts"] == 0
    assert rep["verdict"] == "PASS" and rep["axis2"]["improved"], rep
    print("--- rehab class ---\n  vacuous axis 1; axis-2 improvement carries the PASS OK")


def test_unmeasurable_abstains_without_poisoning_the_buffer():
    """Red-team drill finding (2026-07-09): a never-credited lesson whose recorded contexts
    all pre-date the current matcher regime gives the gate NOTHING to judge with (incumbent
    0 hits). That is an abstention, not a refutation -- verdict UNMEASURABLE, no reject stamp."""
    from core.learning.learning_store import LearningStore
    from core.foundation.store import FileStore
    ls = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "learn.json")))
    ls.persist_learning_derived_from_experiment({
        "experiment_name": "seam_guard", "what_tried": "x", "actual_outcome": "y",
        "success": "yes", "recommendation": INCUMBENT, "agent_id": "t"})
    # contexts that match NOTHING in the incumbent under the floor -> inc 0, var 0
    stale_inj = [{"at": 1.0, "t": "c:npm publish widget bundle tonight",
                  "s": ["learn:experiment:seam_guard"]}]
    rep = gate_edit("seam_guard", GOOD_EDIT, learning_store=ls,
                    events=[], injections=stale_inj, min_relevance=FLOOR)
    assert rep["verdict"] == "UNMEASURABLE", rep
    assert "rejected_stamped" not in rep, "abstention must not stamp the reject buffer"
    assert not json.loads(ls._load_experiment("seam_guard").get("forge_rejected") or "[]")
    print("--- unmeasurable ---\n  zero current-regime evidence -> abstain, buffer untouched OK")


def test_variant_adding_noise_hits_still_fails_regressed():
    """The abstention must not open a hole: a variant that MATCHES a context the incumbent
    did not is measurable badness -> FAIL (regressed), even for a never-credited lesson."""
    stale_inj = [{"at": 1.0, "t": "c:npm publish widget bundle tonight",
                  "s": ["learn:experiment:seam_guard"]}]
    grabby = ("Use when you publish any widget bundle tonight, before starting: route "
              "every source through the one seam. Don't when prototyping.")
    rep = _gate("seam_guard", grabby, events=[], injections=stale_inj)
    assert rep["verdict"] == "FAIL" and rep["axis2"]["regressed"], rep
    print("--- regression guard ---\n  variant grabbing new noise contexts -> FAIL OK")


def test_unknown_lesson_fails_closed():
    rep = _gate("ghost_lesson", GOOD_EDIT)
    assert rep["verdict"] == "FAIL" and any("no active lesson" in r for r in rep["reasons"])
    print("--- unknown lesson ---\n  fails closed with a teaching reason OK")


def test_reject_stamp_and_apply_rollback_roundtrip():
    from core.learning.learning_store import LearningStore
    from core.foundation.store import FileStore
    ls = LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "learn.json")))
    ls.persist_learning_derived_from_experiment({
        "experiment_name": "seam_guard", "what_tried": "x", "actual_outcome": "y",
        "success": "yes", "recommendation": INCUMBENT, "agent_id": "t"})
    # FAIL path stamps the durable rejected buffer
    rep = gate_edit("seam_guard", DEGRADED_EDIT, learning_store=ls,
                    events=EVENTS, injections=INJECTIONS, min_relevance=FLOOR)
    assert rep["verdict"] == "FAIL" and rep.get("rejected_stamped") is True
    buf = json.loads(ls._load_experiment("seam_guard").get("forge_rejected") or "[]")
    assert buf and DEGRADED_EDIT[:60] in buf[0]["draft"], buf
    # PASS + apply swaps the text reversibly
    rep2 = gate_edit("seam_guard", GOOD_EDIT, learning_store=ls,
                     events=EVENTS, injections=INJECTIONS, min_relevance=FLOOR)
    assert rep2["verdict"] == "PASS"
    assert apply_edit("seam_guard", GOOD_EDIT, rep2, learning_store=ls) is True
    rec = ls._load_experiment("seam_guard")
    assert rec.get("recommendation") == GOOD_EDIT
    assert rec.get("forge_previous_text") == INCUMBENT and rec.get("forge_provisional")
    # rollback restores the incumbent and clears the provisional watch
    assert ls.rollback_forge_edit("seam_guard") is True
    rec2 = ls._load_experiment("seam_guard")
    assert rec2.get("recommendation") == INCUMBENT and not rec2.get("forge_provisional")
    print("--- stamp/apply/rollback ---\n  reject buffered; apply reversible; rollback restores OK")


def test_apply_refuses_without_pass():
    assert apply_edit("seam_guard", GOOD_EDIT, {"verdict": "FAIL"}) is False
    print("--- apply guard ---\n  apply refuses a non-PASS report OK")


if __name__ == "__main__":
    print("=" * 60)
    print("FORGE F1 GATE")
    print("=" * 60)
    test_degraded_edit_rejected_on_axis1()
    test_good_edit_passes_with_axis2_improvement()
    test_equal_rewrite_is_churn_not_progress()
    test_floor_checks_budget_and_trigger()
    test_rehab_class_vacuous_axis1_axis2_carries()
    test_unmeasurable_abstains_without_poisoning_the_buffer()
    test_variant_adding_noise_hits_still_fails_regressed()
    test_unknown_lesson_fails_closed()
    test_reject_stamp_and_apply_rollback_roundtrip()
    test_apply_refuses_without_pass()
    print("\nALL FORGE F1 GATE TESTS PASSED")
