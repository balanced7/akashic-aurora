"""PRE-REGISTERED ACCEPTANCE for the recall repair. Written BEFORE the implementation.

Daniel: "Lets come up with tests so we can empirically tell if the system is working after we
build it then lets build it."

These are expected to FAIL on the current implementation. That is the point -- a test that
passes before the fix is measuring something other than the fix. Each one is run and its
failure recorded before any code changes, so we know it discriminates.

TWO PROPERTIES, both defects found by measurement on 2026-07-26.

A. RETRIEVAL MUST NOT BE O(n) IN STORE READS.
   load_all_learnings_from_store reads the whole index then does ONE STORE READ PER LESSON,
   and core/recall/at_action.py calls it on the PreToolUse path. Measured: 455 lessons =
   220ms/query, 0.483ms/lesson, extrapolating to 483 SECONDS per query at a million.

   These tests count STORE OPERATIONS rather than wall time, deliberately. A timing assertion
   is flaky, machine-dependent, and passes on a fast laptop while the complexity class stays
   wrong. Counting reads measures the ACTUAL property -- does the work scale with corpus size --
   and it gives the same answer on any machine.

B. RETIREMENT MUST NOT SELF-SEAL.
   is_benched suppresses a lesson's rank, so a demoted lesson stops surfacing and can never
   earn the credit that would redeem it. at_action.py:697 already documents this. The repair
   is to adopt the EXISTING type-agnostic bi-temporal lifecycle (core/codex/lifecycle.py),
   where supersede() closes valid_to and persists BOTH nodes so the old one stays queryable.
"""
import time
from typing import Any, Dict, List

import pytest

from core.foundation.store import FileStore


# --------------------------------------------------------------------------- counting store
class CountingStore(FileStore):
    """A store that records how many read operations it served.

    Wrapping the real FileStore rather than faking one keeps the semantics honest -- the test
    exercises the same code path production does, and only observes it.
    """

    def __init__(self, path):
        super().__init__(path)
        self.reads = 0

    def _count(self):
        self.reads += 1

    def get(self, key):
        self._count()
        return super().get(key)

    def hgetall(self, key):
        self._count()
        return super().hgetall(key)

    def lrange(self, key, start, end):
        self._count()
        return super().lrange(key, start, end)

    def keys(self, pattern="*"):
        self._count()
        return super().keys(pattern)


def _seed(store, n: int) -> None:
    """n lessons through the real learning-store write path."""
    from core.learning.learning_store import LearningStore
    ls = LearningStore(store=store)
    for i in range(n):
        ls.record_learning({
            "experiment_name": f"seeded_lesson_{i:05d}",
            "what_was_tried": f"attempt {i}",
            "result": "it worked" if i % 2 == 0 else "it did not",
            "recommendation": f"use approach {i} when condition {i % 7} holds",
            "success": "yes" if i % 2 == 0 else "no",
            "agent_id": "test",
        })


def _retrieve(store) -> List[Dict[str, Any]]:
    from core.learning.learning_store import LearningStore
    return LearningStore(store=store).load_all_learnings_from_store()


# ============================================================ A. retrieval complexity
def test_a1_retrieval_reads_do_not_scale_with_corpus_size(tmp_path):
    """THE CORE SCALING PROPERTY, expressed so it cannot pass by accident.

    Retrieval at 4x the corpus must not cost ~4x the store reads. A pushdown implementation
    answers a query with a bounded number of store operations regardless of corpus size; the
    current materialise-everything implementation cannot.

    The threshold is deliberately generous -- 2x reads for 4x data would still pass. This is
    not a micro-benchmark, it is a complexity-class assertion, and anything genuinely O(n)
    fails it by a wide margin.
    """
    small = CountingStore(str(tmp_path / "small.json"))
    _seed(small, 50)
    small.reads = 0
    _retrieve(small)
    reads_small = small.reads

    large = CountingStore(str(tmp_path / "large.json"))
    _seed(large, 200)
    large.reads = 0
    _retrieve(large)
    reads_large = large.reads

    assert reads_small > 0, "sanity: retrieval should touch the store at all"
    growth = reads_large / max(reads_small, 1)
    assert growth < 2.0, (
        f"retrieval reads scale with corpus size: {reads_small} reads at 50 lessons -> "
        f"{reads_large} at 200 ({growth:.1f}x for 4x the data). A query must not "
        f"materialise the corpus; push the filter and top-k into the store."
    )


def test_a2_a_bounded_query_does_not_read_every_lesson(tmp_path):
    """Asking for a few lessons must not read all of them.

    This is the same defect from the caller's side: even when recall wants the top handful,
    the current path loads all N first. Independent of test a1 because a store could scale
    sub-linearly and still over-read on a small request.
    """
    store = CountingStore(str(tmp_path / "bounded.json"))
    n = 150
    _seed(store, n)
    store.reads = 0
    items = _retrieve(store)
    assert len(items) == n, "sanity: the corpus is the size we seeded"
    assert store.reads < n, (
        f"a retrieval read the store {store.reads} times for {n} lessons -- at least once per "
        f"lesson. The read path has no filter pushdown and no top-k."
    )


def test_a3_retrieval_latency_stays_flat_enough_to_sit_on_the_hot_path(tmp_path):
    """A wall-time guard, kept LOOSE and secondary to the read counts above.

    Timing assertions are flaky by nature, so this only catches an order-of-magnitude
    regression -- the kind that makes the PreToolUse hook unusable. The read-count tests are
    the real acceptance; this one exists because latency is what a human actually feels.
    """
    store = CountingStore(str(tmp_path / "latency.json"))
    _seed(store, 300)
    t0 = time.perf_counter()
    _retrieve(store)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.25, (
        f"retrieval over 300 lessons took {elapsed*1000:.0f}ms. This runs on every tool call; "
        f"at 10x the corpus it would be unusable."
    )


# ============================================================ B. retirement must not self-seal
def _retire(store, name: str, reason: str = "surfaced often, never credited") -> None:
    """Retire through the REAL path.

    Corrected after the first pre-build run: my first version set a `benched` key and
    re-recorded the lesson. That is wrong twice over -- re-recording rewrites the whole hash
    from a fixed field set (so extra keys are dropped), and the real door is mark_benched,
    which does a targeted partial-hset. The test failed on its own sanity assertion rather
    than on the property, which is the failure mode a pre-build run exists to catch.
    """
    from core.learning.learning_store import LearningStore
    assert LearningStore(store=store).mark_benched(name, reason), "bench path did not fire"


def test_b1_a_retired_lesson_remains_queryable_by_id(tmp_path):
    """THE ANTI-SELF-SEALING PROPERTY, and the whole point of the repair.

    Retirement must remove a lesson from ROUTINE SURFACING without removing it from the
    record. Wikidata keeps deprecated statements and simply does not return them by default;
    core/codex/lifecycle.supersede persists BOTH nodes so the old one stays queryable and
    inbound links forward. A retirement that makes a lesson unreachable destroys the evidence
    needed to ever un-retire it.
    """
    store = CountingStore(str(tmp_path / "retire.json"))
    _seed(store, 5)
    name = "seeded_lesson_00002"
    _retire(store, name)

    from core.learning.learning_store import LearningStore
    rec = LearningStore(store=store)._load_experiment(name)
    assert rec, "a retired lesson must still be retrievable by id -- retirement is not deletion"
    assert rec.get("experiment_name") == name or rec.get("experiment") == name


def test_b2_retirement_records_why_and_when(tmp_path):
    """Retirement must carry a REASON and a TIME, not just a flag.

    CORRECTED AFTER THE PRE-BUILD RUN, and the correction is the point. My first version
    asserted on `benched_at` / `benched_reason` and failed -- which looked like a missing
    feature. It is not: mark_benched already stamps `benched` with an ISO TIMESTAMP (the flag
    IS the time) and `bench_reason`. Building to satisfy the original assertion would have
    added duplicate timestamp fields to a system that already had them.

    This now asserts the property against the fields that actually exist.
    """
    store = CountingStore(str(tmp_path / "why.json"))
    _seed(store, 5)
    name = "seeded_lesson_00003"
    _retire(store, name, reason="never credited across 40 surfacings")

    from core.learning.learning_store import LearningStore
    rec = LearningStore(store=store)._load_experiment(name) or {}
    when = str(rec.get("benched") or rec.get("valid_to") or "")
    why = str(rec.get("bench_reason") or rec.get("superseded_by") or "")
    assert when and when.lower() not in ("true", "1"), (
        f"retirement must record WHEN, not a bare boolean -- got {when!r}"
    )
    assert why, "retirement must record WHY -- a reasonless flag can be obeyed but not reviewed"


def test_b3_a_benched_lesson_can_still_earn_its_way_back(tmp_path):
    """THE SELF-SEAL, stated precisely -- and it is subtler than 'there is no way back'.

    An unbench path DOES exist and is deliberate: mark_benched(undo=True), and the curator's
    documented rule is "UNBENCHES on any new credit (helped/useful/engaged), so a quiet
    guardian that finally fires earns its slot back."

    The loop is that the TRIGGER is unreachable. Credit is earned by SURFACING, and
    at_action.py excludes benched lessons from the recall surfaces -- so a benched lesson
    cannot accumulate the credit that would unbench it. The mechanism is sound; its input is
    cut off. at_action.py:697 already documents this.

    So the property is not "can it be un-benched by hand" (it can) but "can it earn its way
    back without a human", which is what Daniel means by automatic. This test asserts the
    honest minimum: a benched lesson must remain REACHABLE by the credit path, so the
    documented unbench rule has an input at all.
    """
    store = CountingStore(str(tmp_path / "revive.json"))
    _seed(store, 5)
    name = "seeded_lesson_00004"
    _retire(store, name)

    from core.learning.learning_store import LearningStore, is_benched
    ls = LearningStore(store=store)
    assert is_benched(ls._load_experiment(name) or {}), "sanity: benched before we test revival"

    # The manual door works -- this is not the defect.
    assert ls.mark_benched(name, undo=True), "the undo door must exist"
    assert not is_benched(ls._load_experiment(name) or {}), "undo must clear the bench"

    # THE ACTUAL PROPERTY: while benched, is the lesson still visible to the path that awards
    # credit? If recall surfaces exclude it, the documented "unbench on new credit" rule can
    # never fire on its own, and retirement is one-way in practice however reversible it is
    # in principle.
    ls.mark_benched(name, "re-benched for the surfacing check")
    from core.recall import at_action
    surfaced = at_action._project_items(ls.load_all_learnings_from_store())
    names = {str(i.get("source") or i.get("experiment") or "") for i in surfaced}
    assert any(name in n for n in names), (
        "a benched lesson is invisible to the surface that awards credit, so the documented "
        "'unbench on new credit' rule has no possible input. The mechanism is sound and its "
        "trigger is unreachable -- that is the self-seal, and it is why retirement must be "
        "time-bounding (still queryable, still creditable) rather than rank suppression."
    )
