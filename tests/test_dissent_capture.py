"""Slice 2 -- write-side dissent capture (recall confirmation-bias program).

Run: py tests/test_dissent_capture.py   (or via pytest)

Companion: docs/library/design/20260709_keeping-recall-honest-critic-vs-dialecti_1a5498.md. Slice 1 built a precise counter-finder that requires an
explicit stance signal (an `anti_pattern`), and on the real corpus it fired 0 times because there
were 0 anti-patterns -- the binding constraint is corpus content, not the reader. Slice 2 closes
that: it makes recording a known-bad reachable and near-free, so the corpus grows the disconfirmers
the finder needs.

What this proves:
  - draft_anti_pattern_slug auto-drafts a candidate NAME from a failure's own words (removes the
    'what do I even call it' cost -- the adoption lever).
  - tag_anti_pattern attaches an anti-pattern to an EXISTING lesson without clobbering its fields
    (re-recording would rewrite the whole hash; this is the safe merge path).
  - LOOP CLOSURE: before capture, recall stays silent (Slice 1 precision-first); after one tag, the
    SAME recall surfaces the counter. Writer feeds reader end-to-end.
"""
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.learning.learning_store import LearningStore, draft_anti_pattern_slug
from core.foundation.store import FileStore
from core.recall.at_action import recall_at


def _store():
    return LearningStore(store=FileStore(os.path.join(tempfile.mkdtemp(), "learn.json")))


def test_draft_anti_pattern_slug():
    # derives a snake_case slug from salient content tokens; generic failure-verbs are dropped
    s = draft_anti_pattern_slug(what_tried="used a blocking synchronous flush on every write")
    assert s and " " not in s and s == s.lower(), s
    assert "blocking" in s and "synchronous" in s, f"salient tokens should survive: {s}"
    # prefers root_cause (it names WHY it failed) over what_tried
    assert draft_anti_pattern_slug(what_tried="did a thing",
                                   root_cause="widget cache corrupted state").startswith("widget")
    assert draft_anti_pattern_slug() == "", "nothing meaningful to name -> empty (stay silent)"
    print("--- draft slug ---\n  auto-drafts a candidate name from failure words; empty when nothing to name OK")


def test_tag_anti_pattern_merges_without_clobber():
    ls = _store()
    ls.persist_learning_derived_from_experiment({
        "experiment_name": "flush_exp", "what_tried": "sync flush every write",
        "actual_outcome": "hung 48s", "recommendation": "make it async", "success": "no",
        "root_cause": "blocking IO on the hot path", "agent_id": "tester"})
    assert ls.tag_anti_pattern("flush_exp", "sync_flush_hot_path") is True
    rec = ls._load_experiment("flush_exp")
    assert rec.get("anti_pattern") == "sync_flush_hot_path"
    assert rec.get("what_tried") == "sync flush every write", "other fields must survive the tag (no clobber)"
    assert rec.get("recommendation") == "make it async", "the merge must not blank sibling fields"
    assert ls.tag_anti_pattern("nonexistent_exp", "x") is False, "tagging an unknown lesson -> False"
    print("--- tag merge ---\n  anti_pattern attached; what_tried/recommendation preserved; unknown -> False OK")


def test_capture_stores_but_does_not_mis_surface_as_counter():
    """Corrected loop (Slice 3): capturing an anti-pattern STORES + indexes it (available for the
    future action-warning channel), but it is NOT surfaced as a counter to an on-topic thesis -- an
    anti-pattern is a warning about an action, not a contradiction of a claim, so treating it as a
    thesis-counter only manufactured false balance. Recall stays silent (no hallucinated disagreement)."""
    ls = _store()
    ls.persist_learning_derived_from_experiment({
        "experiment_name": "use_sync_flush", "success": "yes", "agent_id": "tester",
        "recommendation": "flush synchronous writes to the ranker store for durability"})
    ls.persist_learning_derived_from_experiment({
        "experiment_name": "sync_flush_bad", "success": "no", "agent_id": "tester", "root_cause": "blocking IO",
        "recommendation": "synchronous flush on every write hung the ranker store for 48s; make it async"})
    assert ls.tag_anti_pattern("sync_flush_bad", "sync_flush_every_write") is True
    # capture worked: stored on the record + indexed as a documented anti-pattern
    assert ls._load_experiment("sync_flush_bad").get("anti_pattern") == "sync_flush_every_write"
    assert any("sync_flush_every_write" in str(a) for a in ls.load_documented_anti_patterns()), \
        "the anti-pattern should be indexed / discoverable for the action-warning channel"
    # ...but it is NOT surfaced as a counter to an on-topic thesis (the Slice 3 precision fix)
    res = recall_at(command="synchronous flush ranker store durability", learning_store=ls)
    assert res["counter"] is None, "an on-topic anti-pattern must NOT be surfaced as a thesis-counter"
    print("--- capture stored, not mis-surfaced ---\n  anti-pattern captured + indexed; recall stays silent "
          "(no false counter) OK")


if __name__ == "__main__":
    print("=" * 60)
    print("SLICE 2 -- WRITE-SIDE DISSENT CAPTURE")
    print("=" * 60)
    test_draft_anti_pattern_slug()
    test_tag_anti_pattern_merges_without_clobber()
    test_capture_stores_but_does_not_mis_surface_as_counter()
    print("\n" + "=" * 60)
    print("ALL SLICE 2 TESTS PASSED")
    print("=" * 60)
