"""W0.3-f1 pins (RED first): an UNJUDGED lesson must rank NEUTRAL, not punished.

FOUND BY THE BENCH, which is the point of having built it. `recall-bench` on the 10-moment set
(6 scored, 3 abstains) reported recall@1 17%. Pinning `usefulness_factor` to a constant 1.0, at the
SAME show-nothing floor, took recall@1 to 33% -- so the rank-1 loss is caused by the usefulness
re-rank and not by the floor. The moment that moved is N3 (Navi's), where the correct lesson sat at
rank 4 behind three lessons that match the trigger less well.

THE ARITHMETIC, which is the whole finding. For a lesson with NO judgments at all
(useful = noise = helped = 0, surfaced = S):

    eff   = 0
    denom = max(S, 0) + 2 = S + 2
    rate  = (0 + 1) / (S + 2)
    factor = 0.5 + 1/(S + 2)

That is a strictly DECREASING function of the surfacing count and nothing else. Measured against
the live corpus, every value matches to three places:

    surfaced   1 -> 0.833      surfaced  13 -> 0.567
    surfaced   3 -> 0.700      surfaced  28 -> 0.533
    surfaced   6 -> 0.625      surfaced  72 -> 0.514

So N3's correct lesson (surfaced 72, useful 2, noise 1 -> 0.527) is multiplied DOWN past three
never-credited lessons whose only distinction is that they have barely been shown (0.833, 0.700,
0.625). The rule is documented as "surfaced-often-yet-never-useful" decay. It cannot tell that case
apart from "surfaced-often-and-never-JUDGED", and the house's measured judgment rate is 2.2%
(532 of 24,344), so in practice almost every lesson is the second case and decays purely by
exposure.

AND RECALL IS THE AGENT OF ITS OWN SUPPRESSION. `bump_surfaced` is called by `recall_at` itself
(core/recall/at_action.py:1772) on the surfacing path. So the loop closes with no external input:
recall shows a lesson, recall increments the count, the count lowers the multiplier, the lesson is
less likely to be shown at rank 1 next time. A lesson is punished for being relevant to a situation
that recurs, because recurrence is what produces impressions.

THE UPPER HALF OF THE RANGE IS DEAD. The docstring promises [0.5, 1.5]. To clear 1.0 at all needs
`useful` on more than HALF of all surfacings (verified: 6/10, 26/50, 51/100). The house's credit
rate is ~2%, so the reachable range is [0.5, 1.0] -- a pure penalty that can never reward. A
multiplier that only ever multiplies down is not a re-rank, it is a decay.

WHY THIS IS A VIRTUE SEVERED FROM ITS SIBLING, and the house already has the lens for it: the
exposure decay was designed to sit BESIDE a working judgment channel, where "surfaced often and
never credited" really would mean "not useful". Isolated from that sibling -- reach-map barrier 1,
feedback starvation, 7,219 outcome rows all `None` -- it inverted into an anti-relevance filter.
The fix must therefore pass the lens's own test: it must still behave correctly if the sibling is
RESTORED. These pins require both halves, so a future working feedback channel is not re-broken.

WHAT IS DELIBERATELY PRESERVED. The decay's INTENT is real and is not being removed: a lesson that
keeps firing and is repeatedly judged unhelpful SHOULD sink. P6 and P7 hold that line. The defect is
the conflation of "judged often, never useful" with "never judged", and only the conflation is
fixed. Absence of evidence must not be evidence of noise.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.at_action import usefulness_factor as uf  # noqa: E402

NEUTRAL = 1.0


# ---------------------------------------------------------------- P1-P3: unjudged is neutral
def test_an_unjudged_lesson_is_neutral_however_often_it_has_been_shown():
    """The core pin. An impression is not a judgment, so it carries no evidence either way."""
    for surfaced in (0, 1, 3, 6, 13, 28, 72, 200, 5000):
        assert uf({"surfaced": surfaced}) == NEUTRAL, (
            f"surfaced={surfaced} was punished to {uf({'surfaced': surfaced}):.3f} on no "
            "evidence; absence of judgment is not evidence of noise")


def test_two_unjudged_lessons_rank_equally_whatever_their_exposure():
    """If exposure alone moved the multiplier, relevance would be self-defeating: the lesson that
    matches a RECURRING situation earns the most impressions and so the deepest penalty."""
    assert uf({"surfaced": 1}) == uf({"surfaced": 72}), \
        "exposure alone reordered two lessons that carry no judgments between them"


def test_recall_surfacing_a_lesson_cannot_lower_its_own_future_rank():
    """`bump_surfaced` is called by recall_at itself (at_action.py:1772). If surfacing decays the
    multiplier, the loop is closed and self-reinforcing with no external input."""
    before = uf({"surfaced": 10})
    after = uf({"surfaced": 11})       # exactly one more impression, nothing else learned
    assert after == before, (
        "one more impression changed the ranking multiplier, so recall demotes what it shows")


# ---------------------------------------------------------------- P4-P5: real evidence must win
def test_a_credited_lesson_outranks_an_uncredited_one():
    """N3's live case, with the corpus's real counters. The correct lesson has been credited useful
    twice; the three that outranked it have never been credited at all."""
    right = uf({"surfaced": 72, "useful": 2, "noise": 1})     # the correct lesson for N3
    for usurper_surfaced in (1, 3, 6):                        # the three that beat it
        usurper = uf({"surfaced": usurper_surfaced})
        assert right > usurper, (
            f"a twice-credited lesson ({right:.3f}) ranked below a never-credited one "
            f"({usurper:.3f}, surfaced={usurper_surfaced})")


def test_the_boost_half_is_reachable_at_a_realistic_credit_rate():
    """A multiplier documented as [0.5, 1.5] that needs a >50% credit rate to exceed 1.0 has a dead
    upper half: the house's measured rate is ~2%. Ten impressions and two credits is a GOOD lesson
    in this house and must read as better than neutral."""
    assert uf({"surfaced": 10, "useful": 2}) > NEUTRAL, \
        "two credits in ten impressions could not clear neutral; the boost half is unreachable"


# ---------------------------------------------------------------- P6-P8: the decay's intent SURVIVES
def test_noise_votes_still_decay():
    """I LABELLED THIS A GREEN RATCHET AND IT IS RED. Recording that rather than quietly
    relabelling it, because the error is the same one the house has a lesson for: I predicted the
    behaviour by READING the function instead of running it, an hour after citing that very lesson
    to justify sweeping the floor instead of reasoning about it.

    The first line is genuinely green: 3 noise votes give 0.5, which is below neutral. The second
    line is red for a PRE-EXISTING reason that is not the defect this file is about. `rate` is
    clamped at 0, so `eff = -3` and `eff = -8` both floor the multiplier at exactly 0.5. The decay
    SATURATES at the first few noise votes, and a mildly-rejected lesson is suppressed exactly as
    hard as a catastrophically-rejected one.

    Kept in this file rather than split out, because the fix makes it fall out for free: once the
    rate is estimated over JUDGMENTS instead of impressions, more negative judgments move the
    estimate further down without needing the clamp to do the work. If a later fix satisfies
    everything else here and leaves this line red, that is a real finding and this docstring is the
    place it was predicted."""
    assert uf({"surfaced": 10, "noise": 3}) < NEUTRAL, "a noise-voted lesson stopped decaying"
    assert uf({"surfaced": 10, "noise": 8}) < uf({"surfaced": 10, "noise": 3}), \
        "more noise votes must decay further; the clamp saturates both cases at 0.5"


def test_judged_often_and_never_useful_still_decays():
    """The case the rule was WRITTEN for, and the one it must keep. Here `never useful` is a real
    observation rather than an absence: the lesson was judged twenty times and credited zero."""
    assert uf({"surfaced": 40, "noise": 20}) < NEUTRAL, \
        "the decay's actual purpose was removed instead of its conflation being fixed"


def test_more_credit_never_lowers_the_multiplier():
    """Monotone in the only direction that can be argued about."""
    seq = [uf({"surfaced": 20, "useful": u}) for u in range(0, 11)]
    assert seq == sorted(seq), f"credit was non-monotone: {[round(x, 3) for x in seq]}"


def test_the_automatic_contrastive_positive_still_counts():
    """`helped` is the automatic FAIL->SUCCESS credit and is the one signal the reader does not
    have to volunteer, so it must not be dropped by the fix."""
    assert uf({"surfaced": 10, "helped": 3}) > NEUTRAL, "the automatic positive stopped counting"


def test_credit_cannot_exceed_the_exposure_that_earned_it():
    """ADDED AFTER MUTATION TESTING, which is the only reason this pin exists. Five deliberate
    breakages were run against the finished fix; four were caught and one SURVIVED -- removing the
    `min(helped, surfaced)` cap changed nothing that any pin could see.

    The cap defends against join drift: a flip credited to a lesson that was barely shown. Under
    the OLD formula the cap also defended the documented upper bound, and the pre-existing pin
    `uf({"helped": 99, "surfaced": 1}) <= 1.5` was enough to notice it going. Under the new
    formula the bound is held by the confidence term instead, so removing the cap keeps the result
    inside [0.5, 1.5] and the old pin stays green while the protection is gone. A guard whose only
    witness was a side effect of the thing it guarded.

    What the cap still does is keep CONFIDENCE proportional to actual exposure: 99 helps on a
    lesson shown once is one observation, not ninety-nine, and must read as such."""
    once = uf({"surfaced": 1, "helped": 1})
    absurd = uf({"surfaced": 1, "helped": 99})
    assert absurd == once, (
        f"99 credits on a lesson shown once read as {absurd:.3f} rather than {once:.3f}; "
        "credit was counted beyond the exposure that could have earned it")


# ---------------------------------------------------------------- P9-P10: the contract itself
def test_the_range_holds_and_the_empty_case_is_neutral():
    assert uf(None) == NEUTRAL and uf({}) == NEUTRAL
    for u in ({"surfaced": 0}, {"surfaced": 9999}, {"useful": 99}, {"noise": 99},
              {"surfaced": 10, "useful": 5, "noise": 5, "helped": 5}):
        assert 0.5 <= uf(u) <= 1.5, f"{u} left the documented range at {uf(u)}"


def test_the_sibling_can_be_restored():
    """The virtue-isolation test, stated as a pin. If the judgment channel starts working, the rule
    must discriminate again -- a well-judged lesson and a badly-judged one with the SAME exposure
    must separate, and separate the right way round."""
    good = uf({"surfaced": 50, "useful": 20, "noise": 1})
    bad = uf({"surfaced": 50, "useful": 1, "noise": 20})
    assert good > NEUTRAL > bad, (
        f"with a restored feedback channel the rule still cannot separate good from bad "
        f"(good={good:.3f}, bad={bad:.3f})")
