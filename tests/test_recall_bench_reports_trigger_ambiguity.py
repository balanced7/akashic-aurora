"""RED pins (W0.3-f3): recall@1 must be reported beside the cap that trigger ambiguity puts on it.

FOUND WHILE MERGING Navi's batch 3, before it went in. She built three sibling pairs
DELIBERATELY, and said so: "each with a byte-identical trigger and a different correct key." Three
triggers in the merged 25-moment set are now shared by moments whose right answers differ:

    core/comm/discord_guest_reply.py   N4, N7 (same answer) and N8 (different)
    core/comm/wake_seat.py             N13 and N14
    py scripts/mirror.py               N15 and N16

THE ARITHMETIC THIS FORCES. The bench drives the trigger and grades what comes back, so two
moments with a byte-identical trigger receive an IDENTICAL ranked list. Only one lesson can occupy
rank 1. So within such a group, the number of moments that can possibly hit at rank 1 is the size
of the LARGEST set sharing one expected answer -- not the size of the group. Measured on the merged
set: 18 scored positives across 13 distinct triggers, and the best achievable recall@1 is 15 of 18,
or 83%. A perfect engine scores 83% and the missing 17% is not a defect it could ever fix.

recall@5 is NOT capped this way, and the asymmetry is the whole reason this must be a separate
number rather than folded into the reachability ceiling: several of a group's answers can sit
inside one top-5 list quite legitimately.

WHY THIS IS A MEASUREMENT AND NOT A FLAW IN HER MOMENTS, which is the part worth being careful
about. If two genuinely different situations -- a cheaper-question audit and a hardcoded-lane
remediation, both on wake_seat.py -- produce a byte-identical trigger, then the trigger does not
carry enough information to identify the moment. That is a fact about the KEY, not about the
ranker. It is reach-map barrier 4 ("the query is the command, not the intent") turned into a
countable quantity, and it is the strongest evidence in the set that path-or-command alone is an
insufficient moment key. Deleting or editing her pairs to make the number look better would
destroy the only direct measurement we have of that.

SO THE RULE IS THE SAME ONE THIS BENCH ALREADY LIVES BY. An UNRESOLVED moment is excluded and
COUNTED rather than pointed at a plausible lesson. An unreachable positive is counted as
unmatchable rather than blamed on the gate. An ambiguous trigger is reported as a cap rather than
silently depressing a number nobody can explain. In every case the instrument says what it cannot
know instead of quietly folding it into what it can.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import bench  # noqa: E402


def _fake(reachable):
    def fn(*, path=None, command=None, limit=5, **kw):
        got = list(reachable.get(path or command or "", []))
        return {"lessons": [{"source": s, "text": "x"} for s in got[:limit]], "verbs": []}
    return fn


# Two moments on ONE trigger with DIFFERENT answers, plus two with the SAME answer, plus a loner.
MOMENTS = [
    {"id": "A1", "expect": "learn:experiment:a", "trigger": {"path": "shared.py"}},
    {"id": "A2", "expect": "learn:experiment:b", "trigger": {"path": "shared.py"}},
    {"id": "B1", "expect": "learn:experiment:c", "trigger": {"path": "twin.py"}},
    {"id": "B2", "expect": "learn:experiment:c", "trigger": {"path": "twin.py"}},
    {"id": "C1", "expect": "learn:experiment:d", "trigger": {"path": "alone.py"}},
    {"id": "Z1", "expect": "ABSTAIN", "trigger": {"path": "quiet.py"}},
]
REACHABLE = {
    "shared.py": ["learn:experiment:a", "learn:experiment:b"],
    "twin.py": ["learn:experiment:c"],
    "alone.py": ["learn:experiment:d"],
    "quiet.py": [],
}


def _score(k=5):
    return bench.score(MOMENTS, _fake(REACHABLE), k=k)


def test_the_result_carries_a_recall_at_1_cap():
    assert "ambiguity" in (_score().get("ceiling") or {}), \
        "recall@1 was reported with no statement of the cap trigger ambiguity puts on it"


def test_the_cap_counts_the_largest_shared_answer_per_trigger_group():
    """A1/A2 differ, so at most 1 of 2. B1/B2 agree, so BOTH can hit at rank 1. C1 is alone.
    Best achievable = 1 + 2 + 1 = 4 of 5 scored positives."""
    a = _score()["ceiling"]["ambiguity"]
    assert a["scored"] == 5, "an abstain leaked into the cap's denominator"
    assert a["best_possible_at_1"] == 4, f"expected 4, got {a['best_possible_at_1']}"
    assert abs(a["cap_at_1"] - 4 / 5) < 1e-9


def test_moments_sharing_one_trigger_AND_one_answer_are_not_penalised():
    """The subtle half. B1 and B2 share a trigger but agree on the answer, so they cost nothing.
    A cap that merely counted distinct triggers would wrongly charge them."""
    a = _score()["ceiling"]["ambiguity"]
    assert a["distinct_triggers"] == 3
    assert a["best_possible_at_1"] > a["distinct_triggers"], (
        "the cap charged a group that agrees on its answer; it must count the largest shared "
        "answer per trigger, not the number of triggers")


def test_the_contending_groups_are_NAMED():
    """A number says the key is insufficient. A list says WHICH situations the key cannot tell
    apart, and those are the moments that would need a richer trigger."""
    a = _score()["ceiling"]["ambiguity"]
    groups = a.get("contended") or []
    flat = {i for g in groups for i in g.get("ids", [])}
    assert flat == {"A1", "A2"}, f"the contended group was not named correctly: {groups}"


def test_a_set_with_no_shared_triggers_reports_no_cap():
    """RATCHET. The common case must read as uncapped, not as 100% of something."""
    clean = [m for m in MOMENTS if m["id"] in ("B1", "C1", "Z1")]
    a = bench.score(clean, _fake(REACHABLE), k=5)["ceiling"]["ambiguity"]
    assert a["cap_at_1"] == 1.0 and not a["contended"], \
        "a set with no contended trigger reported a cap anyway"


def test_recall_at_1_never_exceeds_its_own_cap():
    d = _score()
    r1 = d["recall_at_1"]
    cap = d["ceiling"]["ambiguity"]["cap_at_1"]
    if r1 is not None:
        assert r1 <= cap + 1e-9, f"recall@1 {r1} exceeded its structural cap {cap}"


def test_the_cap_is_shown_in_the_rendered_report():
    out = bench.render(_score(), {"seeded": len(MOMENTS), "target": 40})
    assert "AMBIGUOUS" in out.upper() or "CAP" in out.upper(), \
        "the cap is computed but never shown, so recall@1 still reads as uncapped"
