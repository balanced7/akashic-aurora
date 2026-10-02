"""W0.3-f2 pins (RED first): recall@k must never be reported without its CEILING.

WHY, AND IT IS THE SHARPEST THING THE BENCH HAS TAUGHT US. `recall-bench` reports recall@5 = 30%
on the 16-moment set. Every reader, including its author, reads that as "70 points of headroom from
better ranking". Measured, by sweeping k with the floor at zero:

    k=5    3 of 10    30%      <- what we report
    k=20   4 of 10    40%
    k=50   6 of 10    60%
    k=200  7 of 10    70%      <- the ceiling
    never  3 of 10             <- M1, M2, N8: the right lesson is not retrieved at ANY depth

So the 70 points of loss decompose into two populations that want completely different work:

    40 points   the right lesson IS retrieved, ranked below 5. A RANKING problem.
    30 points   the right lesson is never retrieved at all. A MATCHING problem
                (reach-map barrier 3, lexical-only matching). No gate, floor, margin or
                re-rank can ever recover these.

A single number hides that split, and the hiding is not harmless: it is the difference between
"keep improving the gate" and "the gate is nearly out of room, go fix the matcher". We nearly made
exactly that mistake tonight -- a floor sweep looked like it strictly dominated, shipped nothing,
and was then falsified on held-out moments (F-recall-floor-078, scored MISS).

THE SECOND REASON, from this same instrument's own history. W0.4's chrome_share is a RATIO whose
numerator turned out to be constant at 1,466 characters at every floor; the share rose from 4% to
35% purely because the denominator collapsed, which reads as a regression and was an 87% reduction
in reading burden. One misleading ratio per instrument is a mistake; two is a pattern, and the
pattern is reporting a fraction without the quantity that bounds it.

WHAT THE CEILING IS, precisely, so the pin is not arguing about definitions. It is the share of
SCORED positives whose expected lesson appears anywhere in the ranking when the show-nothing floor
is removed and the depth is large. It is a property of the corpus and the relevance function, NOT
of the reporting k and NOT of the gate. It must therefore be computed with floor 0 and a deep k,
or it silently measures the thing it is supposed to bound.

ABSTAINS AND EXCLUSIONS ARE NOT IN IT. A ceiling over positives answers "could the right answer
have arrived". An abstain moment has no right answer to reach, and an UNRESOLVED moment has no
established one, so folding either into the denominator would make the ceiling move when the
abstain count changes, which is incoherent.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import bench  # noqa: E402

UNCHECKABLE = getattr(bench, "UNCHECKABLE", "UNCHECKABLE")


# ---------------------------------------------------------------- a tiny hermetic corpus
def _fake_recall(reachable):
    """A stand-in retriever. `reachable` maps a trigger key -> the ordered sources it returns at
    unlimited depth. Nothing here touches Redis or the live corpus."""
    def fn(*, path=None, command=None, limit=5, **kw):
        key = path or command or ""
        got = list(reachable.get(key, []))
        return {"lessons": [{"source": s, "text": "x"} for s in got[:limit]], "verbs": []}
    return fn


MOMENTS = [
    # right answer at rank 1 -> delivered at any k
    {"id": "T1", "expect": "learn:experiment:a", "trigger": {"path": "p1"}},
    # right answer at rank 9 -> RANKABLE: retrieved, but not inside k=5
    {"id": "T2", "expect": "learn:experiment:b", "trigger": {"path": "p2"}},
    # right answer never returned -> UNMATCHABLE at any depth
    {"id": "T3", "expect": "learn:experiment:c", "trigger": {"path": "p3"}},
    # silence is correct; carries no right answer, so it is outside the ceiling
    {"id": "T4", "expect": "ABSTAIN", "trigger": {"path": "p4"}},
    # ground truth unsettled; excluded from scoring and from the ceiling
    {"id": "T5", "expect": "UNRESOLVED", "trigger": {"path": "p5"}},
]

REACHABLE = {
    "p1": ["learn:experiment:a"] + [f"learn:experiment:z{i}" for i in range(20)],
    "p2": [f"learn:experiment:z{i}" for i in range(8)] + ["learn:experiment:b"],
    "p3": [f"learn:experiment:z{i}" for i in range(20)],
    "p4": [f"learn:experiment:z{i}" for i in range(20)],
    "p5": [f"learn:experiment:z{i}" for i in range(20)],
}


def _score(k=5):
    return bench.score(MOMENTS, _fake_recall(REACHABLE), k=k)


# ---------------------------------------------------------------- P1-P3: the ceiling exists
def test_the_result_carries_a_ceiling():
    d = _score()
    assert "ceiling" in d, "recall@k was reported with nothing to bound it"


def test_the_ceiling_counts_reachable_positives_not_delivered_ones():
    """T1 and T2 are reachable (ranks 1 and 9); T3 is not. So 2 of 3 scored positives."""
    d = _score(k=5)
    assert d["ceiling"]["reachable"] == 2
    assert d["ceiling"]["scored"] == 3
    assert abs(d["ceiling"]["rate"] - 2 / 3) < 1e-9


def test_the_ceiling_is_independent_of_the_reporting_k():
    """It bounds recall@k, so it must not move when k moves. At k=1 only T1 is delivered and the
    ceiling is still 2 of 3."""
    for k in (1, 3, 5, 10):
        c = _score(k=k)["ceiling"]
        assert c["reachable"] == 2 and c["scored"] == 3, \
            f"the ceiling moved with k={k}, so it is measuring the gate it should bound"


# ---------------------------------------------------------------- P4-P6: the decomposition
def test_the_loss_is_split_into_ranking_and_matching():
    """The whole point. At k=5: T1 delivered, T2 retrieved-but-too-low, T3 never retrieved."""
    d = _score(k=5)
    s = d["ceiling"]
    assert s["delivered"] == 1, "delivered = the right answer inside the reported k"
    assert s["rankable"] == 1, "rankable = retrieved, ranked below k -- recoverable by re-ranking"
    assert s["unmatchable"] == 1, "unmatchable = never retrieved -- no gate or re-rank can help"
    assert s["delivered"] + s["rankable"] + s["unmatchable"] == s["scored"], \
        "the three buckets must partition the scored positives exactly"


def test_the_unmatchable_moments_are_NAMED_not_merely_counted():
    """A count tells you the matcher is failing. A list tells you WHERE, and these are the moments
    whose lessons want a trigger rewritten or a term mined. Naming them is what makes the number
    actionable rather than discouraging."""
    d = _score(k=5)
    assert d["ceiling"]["unmatchable_ids"] == ["T3"]


def test_an_abstain_or_unresolved_moment_is_outside_the_ceiling():
    """A ceiling over positives answers 'could the right answer have arrived'. An abstain has no
    right answer and UNRESOLVED has no established one, so neither may enter the denominator --
    otherwise the ceiling moves when the abstain count changes, which is incoherent."""
    d = _score()
    s = d["ceiling"]
    assert s["scored"] == 3, "an abstain or an excluded moment leaked into the ceiling"
    assert "T4" not in s["unmatchable_ids"] and "T5" not in s["unmatchable_ids"]


# ---------------------------------------------------------------- P7-P9: honesty at the edges
def test_a_ceiling_that_cannot_be_measured_says_so_rather_than_reading_zero():
    """ZERO IS NOT NO, the house rule this whole slice turns on. With no scored positives at all
    there is nothing to bound, and a rate of 0.0 would read as 'nothing is reachable' -- the most
    alarming possible reading of an empty set."""
    d = bench.score([MOMENTS[3]], _fake_recall(REACHABLE), k=5)   # one abstain, no positives
    assert d["ceiling"]["scored"] == 0
    assert d["ceiling"]["rate"] in (None, UNCHECKABLE), \
        f"an unmeasurable ceiling rendered as {d['ceiling']['rate']!r} instead of saying so"


def test_the_depth_the_ceiling_was_probed_at_is_declared():
    """The ceiling is only ever a LOWER bound on reachability, because it is measured at a finite
    depth. A reader must be able to see which depth, or the number is not reproducible and
    'unmatchable' silently means 'not in the first N'."""
    d = _score()
    probe = d["ceiling"].get("probe_depth")
    assert isinstance(probe, int) and probe >= 50, \
        "the probe depth must be declared and deep enough to be worth calling a ceiling"


def test_recall_never_exceeds_the_ceiling_it_reports():
    """The arithmetic that makes it a ceiling at all. If this ever fails, one of the two numbers is
    measured against a different denominator and both are wrong."""
    for k in (1, 3, 5, 10, 25):
        d = _score(k=k)
        r = d["recall_at_k"]
        if r is not None and d["ceiling"]["rate"] not in (None, UNCHECKABLE):
            assert r <= d["ceiling"]["rate"] + 1e-9, \
                f"recall@{k}={r} exceeded its own ceiling {d['ceiling']['rate']}"


def test_the_rendered_report_shows_the_ceiling_beside_the_number():
    """A field nobody reads is not a fix. The whole defect was a number printed alone, so the
    renderer is part of the contract."""
    d = _score()
    out = bench.render(d, {"seeded": len(MOMENTS), "target": 40})
    assert "CEILING" in out.upper(), "the ceiling is computed but not shown"
    for word in ("RANKABLE", "UNMATCHABLE"):
        assert word in out.upper(), f"the decomposition is computed but {word} is not shown"
