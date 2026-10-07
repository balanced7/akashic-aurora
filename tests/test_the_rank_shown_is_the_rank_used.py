"""RED pins: lookback orders by one number and prints a different one.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

FOUND BY TWO COLD READERS, independently, on 2026-10-07, while they were being used to measure
something else entirely (Contract B's acceptance test; see
`research/reviewed/contract-b-cold-read-test-2026-10-07.md`). Neither was asked about ranking.

  * One reported: *"Relevance ordering is not monotonic within a section in either verb -- in
    lookback's fences block the order was 0.382, 0.215, 0.248 ... Do not treat position as
    confidence."*
  * The same reader: *"`docs/ROADMAP.md` at rel **0.934** -- the single highest number in any output.
    It sits in L3 archive tagged `[doc:historical]` and is an older, unrelated roadmap. Raw relevance
    was actively misleading here."*

THE MECHANISM, and the ordering is not the broken half. `core/primitives/ranker.py:110-112`::

    score = sum(self.weights[k] * components[k] for k in components)
    scored.append(Scored(item=item, score=score, components=components))
    scored.sort(key=lambda s: s.score, reverse=True)

So rows are sorted by the WEIGHTED COMPOSITE of every signal -- relevance, importance, recency.
`core/recall/lookback.py` then publishes, as the row's `score`::

    "score": round(sc.components.get("relevance", 0.0), 3),

one COMPONENT of it. The renderer labels that `rel`. Both are internally honest and together they
mislead: a reader sees a sorted list beside a number that does not explain the sort, and has exactly
two ways to resolve the contradiction -- conclude the sorting is broken, or trust the biggest printed
number. The first reader did the first; the number that would have rewarded the second is an archived
roadmap at 0.934.

This is the same family as everything else found tonight -- `find --sort` re-sorting after asking
es.exe for an order, `--verify` comparing two recorded shas, a corpus report counting survivors, a
leak guard reporting clean because its import failed. In every case the instrument's output was about
a different quantity than the reader believed, and in every case the gap was invisible until someone
asked what the number actually measured. Here the gap is one line wide and sat between a correct
sorter and a correct component.

WHAT A FIX MUST NOT DO: hide the relevance component. It is the diagnostic that tells you WHY a row
matched, and the composite alone cannot. Both numbers, each named for what it is.

Run::

    py -m pytest tests/test_the_rank_shown_is_the_rank_used.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

QUERY = ("how is an agent's working context assembled and what gets built in wave 0 "
         "versus later waves")


def _hits():
    from core.recall.lookback import lookback
    return lookback(QUERY)


# ------------------------------------------------------------------ the defect
def test_rows_are_ordered_by_the_number_they_print():
    """THE PIN. Within a layer, the printed figure must not contradict the order.

    Measured on the fences layer: printed 0.382, 0.215, 0.248 while correctly sorted by a composite
    the reader never saw. A list that is sorted and looks unsorted teaches the reader to distrust the
    ordering, which is the one thing the ranker got right.
    """
    hits = _hits()
    assert hits, "lookback returned nothing for %r -- cannot measure ordering" % QUERY
    by_layer: dict = {}
    for h in hits:
        by_layer.setdefault(h.get("layer"), []).append(h.get("score"))
    bad = {lyr: scores for lyr, scores in by_layer.items()
           if [s for s in scores if s is not None] != sorted(
               [s for s in scores if s is not None], reverse=True)}
    assert not bad, (
        "the printed score decreases non-monotonically inside a layer, so position and number "
        "disagree: %r. Rows are sorted by ranker.py's weighted COMPOSITE (relevance + importance + "
        "recency) and the published `score` is the relevance COMPONENT alone." % bad)


def test_a_hit_carries_the_composite_that_actually_ordered_it():
    """The sort key must be on the row. Without it a reader cannot tell a correctly-ordered list from
    a broken one, and cannot audit the ranking at all."""
    hits = _hits()
    assert hits, "no hits to inspect"
    h = hits[0]
    assert ("rank" in h or "composite" in h or "relevance" in h), (
        "a hit publishes %r -- the number that determined its position is not among them, so the "
        "ordering is unauditable from the output" % sorted(h))


def test_the_relevance_component_survives():
    """The fix must ADD, not replace. Relevance answers "why did this match", which the composite
    cannot, and it is what a reader uses to spot a bad query."""
    hits = _hits()
    assert hits, "no hits to inspect"
    h = hits[0]
    assert ("relevance" in h or "score" in h), (
        "neither a relevance component nor a score is published: %r" % sorted(h))


# ------------------------------------------------------------------ ratchets
def test_the_ranker_itself_still_sorts_by_its_composite():
    """RATCHET. The sorter is the correct half and must stay correct -- this pin is about the REPORT.
    Asserted on the ranker directly so a change to lookback's display cannot quietly alter the
    ordering contract."""
    from core.primitives.ranker import Ranker
    items = [{"text": "alpha beta", "importance": 1, "timestamp": 0},
             {"text": "alpha beta gamma", "importance": 3, "timestamp": 0},
             {"text": "alpha", "importance": 2, "timestamp": 0}]
    scored = Ranker().rank(items, query="alpha beta")
    totals = [s.score for s in scored]
    assert totals == sorted(totals, reverse=True), (
        "Ranker.rank no longer returns rows best-first by its own composite: %r" % totals)


def test_every_hit_still_carries_its_drill():
    """RATCHET. The drill pointer is how a reader gets from a row to the document, and it is the
    reason the fences layer is worth having at all."""
    for h in _hits():
        assert h.get("drill"), "a hit has no drill pointer: %r" % h
