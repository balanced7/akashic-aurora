"""
Regression for recall brittleness (Cursor caught this): a multi-word query must
OR-match terms and rank by how many hit -- NOT require the whole phrase verbatim.

Run: py -m pytest tests/test_recall_match.py -q
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.learning.learning_store import LearningStore


def _store():
    return LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "s.json")))


def test_multiword_query_or_matches_and_ranks():
    ls = _store()
    ls.record_learning({"experiment_name": "salience_promotion",
                        "what_tried": "score events, promote salient ones to beats",
                        "recommendation": "threshold + cap + dedup", "category": "research"})
    ls.record_learning({"experiment_name": "track_routing",
                        "what_tried": "route beats to tracks", "recommendation": "heuristic baseline",
                        "category": "infrastructure"})
    # the phrase appears in NO single learning verbatim -> old code returned 0
    hits = ls.search_learnings_by_keyword("salience promotion consolidation track")
    assert hits, "multi-word query must OR-match, not require the whole phrase"
    # the salience lesson matches more terms -> ranks first
    assert hits[0]["id"] == "salience_promotion"
    # a single term still works
    assert any(h["id"] == "track_routing" for h in ls.search_learnings_by_keyword("track"))
    # empty query -> no results, no crash
    assert ls.search_learnings_by_keyword("   ") == []


if __name__ == "__main__":
    test_multiword_query_or_matches_and_ranks()
    print("recall multi-word match OK")
