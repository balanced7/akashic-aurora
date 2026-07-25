"""Pins for the learning-index repair (found 2026-07-25 while designing tunable personas).

406 lesson records existed; `learn:experiments:all` held 24. All three read paths in
learning_store.py iterate that one list -- keyword search, task recommendations, and
load_all_learnings_from_store (the "list ALL lessons" path) -- so 94% of the fleet's
institutional memory was unreachable by search. The records were never lost and stayed
individually retrievable by exact source, which is exactly why it went unnoticed: every
spot-check of a KNOWN lesson name passed while search answered from a fraction of the
corpus. kimi's audit hit the same wall from the other side and reported the conductor_*
lesson bodies "unreachable".

  Q1  a record missing from the index is DETECTED
  Q2  the repair is UNION-ONLY: an indexed name with no discoverable record is KEPT
  Q3  the repair is idempotent -- a healthy index plans no change
  Q4  the rebuilt index is newest-first (the list's documented semantic)
  Q5  search actually finds a lesson once its name is back in the index
"""
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from core.foundation.store import DictStore
from core.learning.learning_store import LearningStore

import repair_learning_index as rli


@pytest.fixture()
def ls():
    store = DictStore()
    s = LearningStore(store=store)
    for i, name in enumerate(("alpha_lesson", "beta_lesson", "gamma_lesson")):
        s.record_learning({"experiment_name": name, "what_tried": f"tried {i}",
                           "actual": f"result {i}", "recommendation": f"recommend {i}",
                           "agent_id": "claude", "success": "yes"})
    return s


def _starve(ls, keep):
    """Reproduce the live defect: records intact, index truncated."""
    ls.store.delete(rli.INDEX)
    if keep:
        ls.store.rpush(rli.INDEX, *keep)


def test_q1_missing_record_is_detected(ls):
    """Subset assertions on purpose: the injected store is not guaranteed empty (T070 --
    isolated instances still bind live backends), and a pin whose result depends on
    ambient store contents is not a pin."""
    _starve(ls, ["alpha_lesson"])
    _cur, found, missing, _union = rli.plan(ls)
    assert "beta_lesson" in found, "the record still exists"
    assert {"beta_lesson", "gamma_lesson"} <= set(missing), "both must be reported missing"
    assert "alpha_lesson" not in missing, "an already-indexed record is not 'missing'"


def test_q2_repair_is_union_only(ls):
    """An index entry whose record cannot be discovered must survive the rebuild.
    A repair that can lose data is worse than the defect it fixes."""
    _starve(ls, ["alpha_lesson", "ghost_lesson_no_record"])
    _cur, found, _missing, union = rli.plan(ls)
    assert "ghost_lesson_no_record" not in found
    assert "ghost_lesson_no_record" in union, "union-only: never drop an existing entry"


def test_q3_repair_is_idempotent(ls):
    """Apply the plan, then re-plan: a repaired index must report nothing left to do."""
    _starve(ls, [])
    _cur, _found, _missing, union = rli.plan(ls)
    ls.store.delete(rli.INDEX)
    ls.store.rpush(rli.INDEX, *union)
    _c2, _f2, missing2, union2 = rli.plan(ls)
    assert missing2 == [], "a repaired index reports nothing to repair"
    assert set(union2) == set(union), "re-planning a healthy index changes nothing"


def test_q4_rebuilt_index_is_newest_first(ls):
    _starve(ls, [])
    _cur, _found, _missing, union = rli.plan(ls)
    stamps = [rli._ts(ls, n) for n in union]
    assert stamps == sorted(stamps, reverse=True), \
        "learning_store.py:19 documents this list as newest-first"


def test_q5_search_finds_a_lesson_once_reindexed(ls):
    """The whole point: the record was always there; only the index hid it."""
    _starve(ls, ["alpha_lesson"])
    assert ls.search_learnings_by_keyword("gamma_lesson") == [], "reproduce the defect"
    _cur, _found, _missing, union = rli.plan(ls)
    ls.store.delete(rli.INDEX)
    ls.store.rpush(rli.INDEX, *union)
    hits = ls.search_learnings_by_keyword("gamma_lesson")
    assert hits and any(h.get("id") == "gamma_lesson" or h.get("experiment_name") == "gamma_lesson"
                        for h in hits), "findable by its own name after repair"
