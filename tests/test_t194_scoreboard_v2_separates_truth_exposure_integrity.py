"""PRE-REGISTERED ACCEPTANCE (T194) -- scoreboard v2 separates four facts.

Build spec and fence-lite reconciliation:
  research/in-flight/t194-scoreboard-v2-reconciliation-codex-2026-08-05.md

The current scorer carries a double inversion: missing every baseline-blind canary scores
``coverage_honesty=1.0``, while finding one voids the whole round as cheating.  That happens
because detector-relative truth, orchestration assignment, player judgment, and protocol
integrity are collapsed into one verdict.

V2 keeps v1 executable for replay and adds two pure functions:

  score_v2(manifest, claimed, assigned=..., judged=...)  # measurement only
  protocol_verdict(seal_verified=..., archive_complete=..., key_leak_detected=...)

  K1  missing baseline-blind items is recall 0, never honesty 1
  K2  finding a baseline-blind item is a capability finding, never a validity input
  K3  only observed seal/key failures VOID; missing integrity evidence is UNKNOWN
  K4  claimed, declined, unjudged and unseen remain four distinct counts
  K5  bait claims are false positives that lower precision; they never void
  K6  duplicate manifest ids and broken claimed<=judged<=assigned chains fail loudly
  K7  assigned non-canary findings stay reportable without inflating class recall
  K8  v1 and v2 disagree on the measured inversion over identical inputs

Run: py -m pytest tests/test_t194_scoreboard_v2_separates_truth_exposure_integrity.py -q
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import canary_oracle as C  # noqa: E402


def _item(i, cls):
    return {"id": i, "name": f"fn_{i}", "cls": cls, "shape": "test"}


def _manifest(*items):
    return {"universe": {"source": "test", "size": len(items)},
            "canaries": list(items)}


def test_k1_a_miss_is_zero_recall_not_perfect_honesty():
    m = _manifest(_item("u1", "undetectable"))
    got = C.score_v2(m, set(), assigned={"u1"}, judged={"u1"})

    assert got["by_class"]["undetectable"]["recall"] == 0.0
    assert got["by_class"]["undetectable"]["assigned_recall"] == 0.0
    assert "coverage_honesty" not in got


def test_k2_baseline_blind_success_is_capability_not_protocol():
    m = _manifest(_item("u1", "undetectable"))
    got = C.score_v2(m, {"u1"}, assigned={"u1"}, judged={"u1"})

    assert got["capability_findings"] == ["u1"]
    assert got["by_class"]["undetectable"]["recall"] == 1.0
    assert "voided" not in got and "void_reason" not in got

    integrity = C.protocol_verdict(
        seal_verified=True, archive_complete=True, key_leak_detected=False)
    assert integrity["validity"] == "VALID" and integrity["voided"] is False


@pytest.mark.parametrize(
    "facts, validity, voided",
    [
        ({"seal_verified": True, "archive_complete": True,
          "key_leak_detected": False}, "VALID", False),
        ({"seal_verified": False, "archive_complete": True,
          "key_leak_detected": False}, "VOID", True),
        ({"seal_verified": True, "archive_complete": True,
          "key_leak_detected": True}, "VOID", True),
        ({"seal_verified": True, "archive_complete": False,
          "key_leak_detected": False}, "UNKNOWN", None),
        ({"seal_verified": True, "archive_complete": True,
          "key_leak_detected": None}, "UNKNOWN", None),
    ],
)
def test_k3_protocol_integrity_is_evidence_three_state(facts, validity, voided):
    got = C.protocol_verdict(**facts)
    assert got["validity"] == validity
    assert got["voided"] is voided
    assert got["basis"], "a validity result must say which observed facts produced it"


def test_k4_four_absence_states_do_not_collapse():
    m = _manifest(*[_item(f"c{i}", "catchable") for i in range(1, 5)])
    got = C.score_v2(
        m,
        {"c1"},
        assigned={"c1", "c2", "c3"},
        judged={"c1", "c2"},
    )["by_class"]["catchable"]

    assert got["total"] == 4
    assert got["claimed"] == 1
    assert got["declined"] == 1
    assert got["unjudged"] == 1
    assert got["unseen"] == 1


def test_k5_bait_is_a_false_positive_not_a_void():
    m = _manifest(_item("u1", "undetectable"), _item("b1", "bait"))
    got = C.score_v2(
        m,
        {"u1", "b1"},
        assigned={"u1", "b1"},
        judged={"u1", "b1"},
    )

    assert got["false_positives"] == 1
    assert got["precision"] == 0.5
    assert "voided" not in got


def test_k6_duplicate_manifest_ids_and_broken_set_chains_refuse():
    duplicate = _manifest(_item("x", "catchable"), _item("x", "bait"))
    with pytest.raises(ValueError, match="duplicate"):
        C.score_v2(duplicate, set(), assigned=set(), judged=set())

    m = _manifest(_item("x", "catchable"))
    with pytest.raises(ValueError, match="claimed.*judged"):
        C.score_v2(m, {"x"}, assigned={"x"}, judged=set())
    with pytest.raises(ValueError, match="judged.*assigned"):
        C.score_v2(m, set(), assigned=set(), judged={"x"})


def test_k7_unknown_claim_is_assigned_and_judged_but_not_class_recall():
    m = _manifest(_item("c1", "catchable"))
    got = C.score_v2(
        m,
        {"outside"},
        assigned={"c1", "outside"},
        judged={"c1", "outside"},
    )

    assert got["unknown_claims"] == ["outside"]
    assert got["by_class"]["catchable"]["claimed"] == 0
    assert got["by_class"]["catchable"]["recall"] == 0.0
    assert got["precision"] == 0.0


def test_k8_old_and_new_scorers_disagree_on_identical_hard_class_claim():
    m = _manifest(_item("u1", "undetectable"))
    old = C.score(m, {"u1"})
    new = C.score_v2(m, {"u1"}, assigned={"u1"}, judged={"u1"})

    assert old["voided"] is True
    assert old["coverage_honesty"] == 0.0
    assert new["capability_findings"] == ["u1"]
    assert new["by_class"]["undetectable"]["recall"] == 1.0
    assert "voided" not in new
