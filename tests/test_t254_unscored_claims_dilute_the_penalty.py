"""T254 -- volume erases the refuted penalty, because unscored claims count in its denominator.

FOUND BY RUNNING THE RULE, NOT READING IT. Reading predicted "a diluted penalty". The measured
result was NO penalty at all, which is a different finding and a worse one. The lesson that
said so (`attack_your_own_scoring_rule_before_the_players_do`) surfaced from recall at the
moment of the investigation and was followed.

MEASURED, both policies that enable the graduated penalty -- including v3_confidence_priced,
which is the PROPOSED FIX for the low-confidence hedge exploit:

    honest  (3 refuted of  3 claims)  ->  -15 points
    flooder (3 refuted of 63 claims)  ->    0 points

Both players were refuted exactly three times. 3/63 = 0.048, times a -5 worst case, rounds to
zero. Sixty unadjudicated claims erase the penalty for three real ones.

THE PADDING DOES NOT HAVE TO BE VALID. Forty claims carrying an entirely undefined outcome
string do the same job, and `score_round` reports `unscored: 60` in the same breath -- it KNOWS
it did not score them, and counts them in the denominator anyway.

WHY THIS IS NOT COVERED BY THE HEDGE FIX. The hedge exploit is "mark everything low-confidence".
This one is "submit noise faster than it can be adjudicated", and it composes with the hedge
rather than being blocked by it. Both live in the same rate, one through the numerator and one
through the denominator.

Same defect shape as the recall value rate audited the same day -- denominator counts events,
numerator requires an adjudication to have happened -- but attached to POINTS instead of a
dashboard, which makes it silently adversarial: a player who outruns the reviewers lowers their
own penalty, and the cheapest way to outrun reviewers is to submit garbage.
"""
import pytest

from core.season.scoring import POLICIES, score_round

GRADUATED = [n for n, p in POLICIES.items() if p.get("graduated_penalty")]


def claim(player, i, outcome, confidence="high"):
    return {"player": player, "dedupe_key": f"{player}-k{i}", "claim_class": "defect",
            "outcome": outcome, "confidence": confidence,
            "stream_id": f"{i:06d}-0", "evidence": "e"}


@pytest.mark.parametrize("policy", GRADUATED)
@pytest.mark.parametrize("padding_outcome", ["unverified", "zzz_not_a_real_outcome",
                                             "unverifiable", ""])
def test_padding_cannot_change_the_penalty_for_the_same_refuted_claims(policy, padding_outcome):
    """The exploit, stated as the invariant it violates.

    Two players refuted the SAME number of times must be penalised the same. What else they
    submitted -- especially what nobody adjudicated -- is not evidence about their accuracy in
    either direction.
    """
    honest = [claim("honest", i, "refuted") for i in range(3)]
    flooder = ([claim("flooder", 100 + i, "refuted") for i in range(3)]
               + [claim("flooder", 200 + i, padding_outcome) for i in range(60)])

    r = score_round(honest + flooder, policy=policy)

    # Compare the REFUTED-claim points, not the totals. Padding may legitimately carry its own
    # cost -- `unverifiable` is -1 each in v2_aixcc, so 60 of them is -60 and the flooder ends
    # up WORSE overall. That is the system working. The invariant under test is narrower and
    # truer: what a player pays FOR BEING REFUTED must not depend on what else they submitted.
    def refuted_points(player):
        return sum(c.get("points") or 0 for c in r["claims"]
                   if c.get("player") == player and c.get("outcome") == "refuted")

    assert refuted_points("flooder") == refuted_points("honest"), (
        f"[{policy}/{padding_outcome!r}] identical refuted counts were penalised differently: "
        f"honest={refuted_points('honest')} flooder={refuted_points('flooder')}. Padding with "
        f"unadjudicated claims changed the refuted penalty, so volume buys immunity.")


@pytest.mark.parametrize("policy", GRADUATED)
def test_a_refuted_claim_still_costs_something(policy):
    """The guard against fixing this by making the penalty disappear for everyone."""
    totals = score_round([claim("p", 1, "refuted")], policy=policy)["totals"]
    assert totals.get("p", 0) < 0, f"[{policy}] a refuted claim must still cost: {totals}"


@pytest.mark.parametrize("policy", GRADUATED)
def test_the_graduated_penalty_still_grades(policy):
    """It must stay GRADUATED over the adjudicated set, or the fix has removed the feature.

    A player refuted on all of their adjudicated claims should fare worse than one refuted on
    a minority of them.
    """
    all_bad = [claim("allbad", i, "refuted") for i in range(4)]
    mixed = ([claim("mixed", 50 + i, "refuted") for i in range(1)]
             + [claim("mixed", 60 + i, "confirmed") for i in range(3)])
    totals = score_round(all_bad + mixed, policy=policy)["totals"]
    assert totals["allbad"] < 0
    assert totals["allbad"] < totals["mixed"], (
        f"[{policy}] the penalty must still grade over ADJUDICATED claims: {totals}")


@pytest.mark.parametrize("policy", GRADUATED)
def test_a_player_with_no_adjudicated_claims_does_not_explode(policy):
    """Narrowing a denominator is how a ZeroDivisionError gets introduced."""
    totals = score_round([claim("ghost", i, "unverified") for i in range(5)], policy=policy)["totals"]
    assert totals.get("ghost", 0) == 0, f"[{policy}] unadjudicated-only player: {totals}"


def test_the_flat_policy_is_unaffected():
    """v1_doc has no graduated penalty, so its behaviour must not move at all."""
    honest = [claim("honest", i, "refuted") for i in range(3)]
    flooder = ([claim("flooder", 100 + i, "refuted") for i in range(3)]
               + [claim("flooder", 200 + i, "unverified") for i in range(60)])
    totals = score_round(honest + flooder, policy="v1_doc")["totals"]
    assert totals["honest"] == totals["flooder"] == 3 * POLICIES["v1_doc"]["refuted"], totals
