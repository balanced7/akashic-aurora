"""T219: the season's dry-run harness was on the SUPERSEDED scorer, and it voided the
players it was built to reward.

FOUND LIVE, first LLM-player dry run, 2026-08-07, seed 20260807, $0.395 for the round.
The round was VOIDED and its evidence discarded.

WHAT THE VOID SAID
    canary_oracle.score():294 -- "a claimed UNDETECTABLE canary VOIDS the round (kimi's K0
    tripwire): either the key leaked or the instrument is being gamed"

WHAT THE PLAYER WAS BUILT TO DO
    season_llm_player.py:25 -- "an LLM player can in principle BEAT the mechanical player on
    `undetectable` ... That asymmetry is the measurement worth having"

THE FORK IS IN THE WORD. The class taxonomy defines `undetectable` as the shape THE GATE
structurally cannot see -- a fact about the DETECTOR. The void rule read it as "nobody
legitimate can find this" -- a fact about ANY PLAYER. Both readings are defensible in
isolation, which is the reliable tell. The tripwire was CORRECT while the only player
echoed check_wiring, and became a false accusation the moment a player reasoned.

THE SAME-SEED RECEIPT, so this is evidence and not an argument (seed 20260807, k=12):
    player      catchable   undetectable   bait
    mechanical    4/4           0/4         0/4    <- the gate does NOT name them
    llm           3/4           2/4         0/4    <- found two anyway, MISSED an easy one
A player holding the answer key does not miss a catchable canary.

AND THE CORRECTION I HAD TO MAKE TO MYSELF, which is the actual finding.
I wrote a score_v3 to fix this. It was redundant: T194 had ALREADY fixed it in score_v2
("finding an undetectable canary is a capability observation. It is NOT evidence that the
answer key leaked"), with integrity moved to protocol_verdict where it is tied to
independently observed facts and can answer UNKNOWN. score_v2 also tracks unjudged/unseen
per class, which score() cannot -- and my v3 duplicated `capability_findings` under a second
name, which would have been a fresh fork inside the module built to study forks.

SO THE REAL DEFECT IS NARROWER AND WORSE: the fix existed and was WIRED INTO ONE HARNESS
ONLY. season_fan_calibration.py calls score_v2 + protocol_verdict; season_dryrun.py still
called score(). One season, two scorers, contradictory semantics for the same event -- and
the two tokens differ (`score` vs `score_v2`), so no grep for a shared name finds it. That
is the forked-semantics class this repo has been chasing since 2026-06-19, live, in the
game arc, costing a real voided round.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import canary_oracle as CO  # noqa: E402


def _manifest():
    return {"canaries": [
        {"id": "c00", "cls": "catchable", "name": "f00"},
        {"id": "c01", "cls": "catchable", "name": "f01"},
        {"id": "c04", "cls": "undetectable", "name": "f04"},
        {"id": "c05", "cls": "undetectable", "name": "f05"},
        {"id": "c08", "cls": "bait", "name": "f08"},
    ]}


ALL = {"c00", "c01", "c04", "c05", "c08"}


def test_finding_an_undetectable_canary_is_capability_not_contamination():
    """THE PIN. The claim set that voided the live round must score as a capability."""
    got = CO.score_v2(_manifest(), {"c00", "c04"}, assigned=ALL, judged=ALL)
    assert got["capability_findings"] == ["c04"], \
        "an undetectable canary reached by analysis must be COUNTED, not punished"
    assert got["false_positives"] == 0
    assert "voided" not in got, \
        "measurement must not carry a protocol judgment -- that is what T194 separated"


def test_protocol_verdict_answers_unknown_rather_than_guessing():
    """The harness gathers no independent leak evidence. UNKNOWN is the honest value;
    passing False would assert an audit that never ran, and True would void on nothing."""
    got = CO.protocol_verdict(seal_verified=True, archive_complete=True,
                              key_leak_detected=None)
    assert got["validity"] == "UNKNOWN"
    # `voided` is itself THREE-STATE, and my first draft of this pin asserted `is False` --
    # forcing a binary read onto a field deliberately built not to be binary. None here
    # means "not established", which is neither an accusation nor a clearance. Pinning that
    # distinction is worth more than pinning the value.
    assert got["voided"] is None, "unknown integrity must not collapse to a clearance"
    assert got["voided"] is not True, "nor to an accusation"


def test_protocol_verdict_still_voids_on_observed_facts():
    """kimi's tripwire keeps its teeth -- moved, not removed, and now tied to a fact that
    actually indicates leakage rather than to a canary class."""
    broken = CO.protocol_verdict(seal_verified=False, archive_complete=True,
                                 key_leak_detected=None)
    assert broken["validity"] == "VOID" and broken["voided"] is True
    leaked = CO.protocol_verdict(seal_verified=True, archive_complete=True,
                                 key_leak_detected=True)
    assert leaked["voided"] is True


def test_unjudged_is_not_scored_as_a_miss():
    """A canary in a branch that never landed was not passed over -- it was never asked
    about. The live round had 44 UNJUDGED candidates and 2 dead branches; scoring those as
    player misses attributes a harness failure to the player, which is UNKNOWN collapsing to
    negative, the failure T155 cost a whole seat-hunt to learn."""
    got = CO.score_v2(_manifest(), {"c00"}, assigned=ALL, judged={"c00", "c01", "c08"})
    und = got["by_class"]["undetectable"]
    assert und["unjudged"] == 2, "two undetectable canaries were assigned but never judged"
    assert und["declined"] == 0, "unjudged must not be reported as declined"


def test_bait_rate_is_never_called_recall():
    """Bait is LIVE code, so a high claim rate on it is a precision failure. Calling that
    rate 'recall' would invert the meaning -- the same inversion, one field over."""
    got = CO.score_v2(_manifest(), {"c08"}, assigned=ALL, judged=ALL)
    assert got["by_class"]["bait"]["recall"] is None
    assert got["false_positives"] == 1
    assert got["precision"] == 0.0


def test_the_dryrun_harness_uses_the_corrected_scorer():
    """THE WIRING PIN, which is the whole defect. The fix existed since T194 and reached
    only season_fan_calibration.py. A correction that is built and unwired is not a fix."""
    src = (REPO / "scripts" / "season_dryrun.py").read_text(encoding="utf-8")
    assert "score_v2" in src, "dry-run harness still on the superseded scorer"
    assert "protocol_verdict" in src, "integrity must come from independent facts"


def test_claim_evidence_is_not_a_fabricated_gate_result():
    """season_dryrun stamped `check_wiring --report names {name} as NEW unwired` onto EVERY
    claim. True by construction for the mechanical player; FABRICATED for the LLM player,
    whose finds the gate never named -- as the voided round proves. Those fabrications went
    into the permanent round archive, where they survive and get cited."""
    from season_dryrun import claim_evidence

    ev = " ".join(claim_evidence("some_fn", player_name="llm", gate_named=False)).lower()
    assert "did not" in ev or "not name" in ev, \
        "an LLM claim must not assert a check_wiring result that was never obtained"
    ev_mech = claim_evidence("some_fn", player_name="mechanical", gate_named=True)
    assert any("check_wiring" in e for e in ev_mech), \
        "the mechanical player's evidence IS the gate result and must still say so"
