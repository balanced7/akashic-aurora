"""The near-dup edge now PERSISTS (learn -> find_related -> mark_related).

The write door has ALWAYS warned on 5-dimension overlap at capture time (advisory print,
never blocks). What was missing: the computed edge evaporated with the console line, so the
consolidation/merge pass the warning points at had nothing durable to act on. This pins the
edge landing on the new record as `related_to` JSON (+ `related_stamped`), one-directional
new -> existing.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.learning.learning_store import LearningStore, find_related
from core.foundation.store import FileStore


def _store():
    return LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "learn.json")))


def test_mark_related_stamps_edge():
    ls = _store()
    base = {"experiment_name": "seam_fix_a", "what_tried": "moved the consolidator seam",
            "actual_outcome": "faithfulness gate now fires", "success": "yes",
            "recommendation": "route every source through the one consolidator seam",
            "agent_id": "t", "category": "architecture"}
    ls.persist_learning_derived_from_experiment(base)
    twin = dict(base, experiment_name="seam_fix_b")
    ls.persist_learning_derived_from_experiment(twin)
    related = find_related(twin, ls.load_all_learnings_from_store(), exclude_name="seam_fix_b")
    assert related and related[0]["experiment_name"] == "seam_fix_a", \
        f"the twin must be found before it can be stamped, got {related}"
    assert ls.mark_related("seam_fix_b", related) is True
    rec = ls._load_experiment("seam_fix_b")
    edges = json.loads(rec.get("related_to") or "[]")
    assert edges and edges[0]["experiment_name"] == "seam_fix_a" and edges[0]["dims"] >= 2, edges
    assert rec.get("related_stamped"), "stamp time must land with the edge"
    print("--- edge stamped ---\n  twin lesson carries related_to -> seam_fix_a durable OK")


def test_mark_related_noops_safely():
    ls = _store()
    assert ls.mark_related("ghost", [{"experiment_name": "x", "dims": 4, "matched": []}]) is False, \
        "unknown record -> no write, no raise"
    ls.persist_learning_derived_from_experiment({
        "experiment_name": "solo", "what_tried": "x", "actual_outcome": "y",
        "success": "yes", "recommendation": "z", "agent_id": "t"})
    assert ls.mark_related("solo", []) is False, "no edges -> no write"
    assert not (ls._load_experiment("solo") or {}).get("related_to")
    print("--- no-op safety ---\n  ghost record / empty edges -> False, record untouched OK")


if __name__ == "__main__":
    print("=" * 60)
    print("LEARN DEDUP EDGE PERSISTENCE")
    print("=" * 60)
    test_mark_related_stamps_edge()
    test_mark_related_noops_safely()
    print("\nALL DEDUP-STAMP TESTS PASSED")
