"""T221 RED: low confidence is a FREE OPTION, and hedging everything is dominant.

FOUND 2026-08-07 by attacking the scoring rule before the season runs -- the rules-lawyering
phase every durable competition (AIxCC, CTF, Kaggle) has, where the organiser wants to be the
one who finds the dominant degenerate strategy.

THE EXPLOIT, measured against the real scorer, in BOTH policies:

    hedge   3 confirmed + 30 refuted, EVERY claim marked low-confidence  -> 6 points
    honest  3 confirmed +  1 refuted, marked high-confidence             -> 4 (v1) / 5 (v2)

The hedger wins while being wrong thirty times, and it is UNBOUNDED: 300 wrong claims cost
exactly as much as 30, which is nothing.

THE MECHANISM. `refuted_low_confidence = 0` floors the penalty for an honestly-flagged wrong
claim -- a good intention, and the reason is sound: nobody should be punished for saying "I
am not sure". But a CONFIRMED low-confidence claim still earns FULL points. So confidence
carries downside protection with no upside cost.

In competition terms that is a FREE OPTION, and a free option is always exercised. The
dominant strategy is to mark every claim low-confidence, spray, and keep the hits.

WHY THIS MATTERS MORE AT SCALE. With one mechanical player it is invisible -- that player
does not choose a confidence level. At twenty LLM players it is the first thing a
score-maximising prompt discovers, and it degrades the signal the whole season exists to
produce: the board fills with unfalsifiable low-confidence noise that costs its authors
nothing and costs the verifiers everything.

RELATED, and how this was found: the T217 hat ablation (result 40de626) measured `economist`
at second-highest UNIQUENESS and worst PRECISION -- a rarity-rewarded, truth-refuted lens
living inside my own tool. Looking for that disposition in the season's scoring is what
surfaced this.

NOT FIXED HERE. Scoring is a POLICY question under an established rule: v2_aixcc is
"PROPOSED (W2), not the default... Nothing selects it until Daniil rules". These pins state
the property the policy must satisfy; which knob buys it is the operator's call.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from core.season import scoring as S  # noqa: E402

#: The proposal that satisfies these properties. The DEFAULTS are marked xfail(strict=True)
#: rather than deleted: the exploit is real in both of them and the ruling is Daniil's, so
#: the gap stays visible in CI without turning it red. strict=True means that if a default
#: policy is ever fixed, the xfail FAILS loudly and nobody has to remember to come back.
FIXED = 'v3_confidence_priced'
OPEN = [pytest.param('v1_doc', marks=pytest.mark.xfail(strict=True,
            reason='T221 hedge exploit OPEN in the default policy -- awaiting Daniil ruling')),
        pytest.param('v2_aixcc', marks=pytest.mark.xfail(strict=True,
            reason='T221 hedge exploit OPEN in the v2 proposal -- awaiting Daniil ruling')),
        FIXED]


def _claims(player, hits, misses, confidence):
    out = []
    for i in range(hits):
        out.append({"player": player, "dedupe_key": f"{player}::h{i}",
                    "claim_class": "needs-caller", "outcome": "confirmed",
                    "confidence": confidence, "stream_id": f"1-{i}",
                    "evidence": [f"evidence {i}"]})
    for i in range(misses):
        out.append({"player": player, "dedupe_key": f"{player}::m{i}",
                    "claim_class": "needs-caller", "outcome": "refuted",
                    "confidence": confidence, "stream_id": f"2-{i}",
                    "evidence": [f"evidence m{i}"]})
    return out


def _totals(claims, policy):
    return S.score_round(claims, verifications=[], policy=policy)["totals"]


@pytest.mark.parametrize("policy_", OPEN)
def test_hedging_everything_must_not_beat_being_right(policy_):
    """THE PIN. Same three real findings; the hedger adds thirty wrong claims for free."""
    for policy in [policy_]:
        t = _totals(_claims("hedge", 3, 30, "low") + _claims("honest", 3, 1, "high"),
                    policy)
        assert t["hedge"] <= t["honest"], (
            f"[{policy}] a player wrong THIRTY times outscored one wrong once "
            f"({t['hedge']} vs {t['honest']}) -- low confidence is a free option")


@pytest.mark.parametrize("policy_", OPEN)
def test_wrong_low_confidence_claims_are_not_unboundedly_free(policy_):
    """Volume must eventually cost something. A floor that never bites at any volume is not
    a floor, it is an exemption -- and the honest-uncertainty intention does not require one:
    it requires that a FEW honest misses are cheap, not that infinite misses are."""
    for policy in [policy_]:
        few = _totals(_claims("p", 3, 2, "low"), policy)["p"]
        many = _totals(_claims("p", 3, 60, "low"), policy)["p"]
        assert many < few, (
            f"[{policy}] 60 wrong low-confidence claims scored the same as 2 ({many} vs "
            f"{few}) -- the cost of being wrong does not grow with how often you are wrong")


@pytest.mark.parametrize("policy_", OPEN)
def test_confidence_is_a_tradeoff_not_a_free_put(policy_):
    """The principled shape: if low confidence buys downside protection it must cost
    something on the upside, or it is never rational to claim high confidence. A
    low-confidence HIT should be worth less than a high-confidence hit."""
    for policy in [policy_]:
        lo = _totals(_claims("lo", 5, 0, "low"), policy)["lo"]
        hi = _totals(_claims("hi", 5, 0, "high"), policy)["hi"]
        assert lo < hi, (
            f"[{policy}] five low-confidence hits scored the same as five high-confidence "
            f"hits ({lo} vs {hi}) -- hedging carries no cost, so hedging is dominant")


@pytest.mark.parametrize("policy_", ["v1_doc", "v2_aixcc", FIXED])
def test_an_honest_low_confidence_miss_stays_cheap(policy_):
    """The GUARD ON THE FIX, and it is the reason refuted_low_confidence exists at all.
    Whatever bounds the exploit must NOT make honest uncertainty expensive -- punishing a
    player for flagging doubt would buy false confidence, which is strictly worse than noise
    because it is harder to filter.

    COMPARE LIKE WITH LIKE. The first draft of this pin measured a low-confidence player
    against a HIGH-confidence one and failed on v3 -- but that gap was the deliberate credit
    price on hedged HITS, not the cost of the miss. Two variables moved and the test
    attributed both to one. Holding confidence fixed isolates what this guard is actually
    about: does ADDING an honest miss hurt?
    """
    for policy in [policy_]:
        with_miss = _totals(_claims("c", 3, 1, "low"), policy)["c"]
        without = _totals(_claims("s", 3, 0, "low"), policy)["s"]
        assert with_miss >= without - 1, (
            f"[{policy}] one honestly-flagged miss cost more than a point "
            f"({with_miss} vs {without}) -- that buys false confidence instead of honest "
            f"reporting, and false confidence is worse than noise because it does not filter")
