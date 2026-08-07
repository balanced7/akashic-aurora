"""T219 RED: the oracle voids the players it was built to reward.

FOUND LIVE, first LLM-player dry run, 2026-08-07, seed 20260807, $0.395 for the round.

TWO MODULES WRITTEN FOR THE SAME SEASON, IN DIRECT CONTRADICTION:

  scripts/canary_oracle.py:294
    "a claimed UNDETECTABLE canary VOIDS the round (kimi's K0 tripwire): either the key
     leaked or the instrument is being gamed, and the round's evidence is worthless"

  scripts/season_llm_player.py:25
    "an LLM player can in principle BEAT the mechanical player on `undetectable` ...
     That asymmetry is the measurement worth having before twenty players multiply it."

The exact measurement one module exists to produce is the tripwire the other voids for.

THE FORK IS IN THE WORD. `undetectable` is defined by the class taxonomy as "the A5
string-dispatch shape, which THE GATE structurally CANNOT see" -- a statement about the
DETECTOR. The void rule reads it as "nobody legitimate can find this" -- a statement about
ANY PLAYER. Both readings are defensible in isolation, which is the tell.

The tripwire was CORRECT while the only player was mechanical: that player echoes
check_wiring by construction, so it cannot name an undetectable canary except by leakage.
It becomes a false accusation the moment a player reasons instead of echoing.

THE SAME-SEED RECEIPT, which is why this is not a judgement call (seed 20260807, k=12):

    player      catchable   undetectable   bait
    mechanical    4/4           0/4         0/4     <- the gate does NOT name them
    llm           3/4           2/4         0/4     <- found two anyway, MISSED an easy one

A player holding the answer key does not miss a catchable canary. Missing an easy one while
finding two hard ones is the signature of analysis, not of leakage. The round was voided
and its evidence discarded.

SECOND DEFECT, same run. season_dryrun.py:110 stamps every claim with

    "evidence": [f"check_wiring --report names {name} as NEW unwired"]

a hardcoded template. True by construction for the mechanical player; FABRICATED for the
LLM player, whose finds the gate never named -- as this very round proves. `evidence` means
"what the mechanical player observed" at the write site and "what the player observed" at
the read site, and the shared claim-shaper laundered one into the other. That is T216's
shape (a field accepted on one path, silently wrong on another) inside the season harness.
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
    """Four canaries, one per relevant class, ids mirroring a real round."""
    return {"canaries": [
        {"id": "c00", "cls": "catchable"},
        {"id": "c01", "cls": "catchable"},
        {"id": "c04", "cls": "undetectable"},
        {"id": "c05", "cls": "undetectable"},
        {"id": "c08", "cls": "bait"},
    ]}


def test_gate_echo_player_claiming_undetectable_still_voids():
    """kimi's K0 tripwire keeps its teeth where it was earned. A player that can only echo
    the detector cannot name an undetectable canary by analysis -- so a claim IS a leak
    signal, and preserving that is the whole reason this fix must not be a blanket removal.
    """
    out = CO.score_v3(_manifest(), ["c00", "c04"], player_kind="gate_echo")
    assert out["voided"] is True
    assert "leak" in out["void_reason"].lower()


def test_reasoning_player_beating_the_gate_is_scored_not_voided():
    """THE PIN. The same claim set from a REASONING player is the design goal, not fraud."""
    out = CO.score_v3(_manifest(), ["c00", "c04"], player_kind="reasoning")
    assert out["voided"] is False, (
        "voided a reasoning player for doing exactly what season_llm_player.py:25 says it "
        "should be able to do")
    assert out["gate_beating_finds"] == 1, \
        "an undetectable canary found by analysis must be COUNTED, not merely tolerated"
    assert out["catch_rate"] == 0.5, "catch_rate still measures the DETECTOR, unchanged"


def test_the_real_leak_signature_still_voids_a_reasoning_player():
    """Dropping the tripwire entirely would be the opposite error. A leaked key shows up as
    a claim set that is too good ACROSS classes -- including the bait, which no honest
    analysis claims, and with no misses to pay for it."""
    out = CO.score_v3(_manifest(), ["c00", "c01", "c04", "c05", "c08"],
                      player_kind="reasoning")
    assert out["voided"] is True
    assert "bait" in out["void_reason"].lower() or "every" in out["void_reason"].lower()


def test_a_bait_claim_is_precision_failure_not_automatically_a_leak():
    """One bait claim alongside ordinary misses is a wrong answer, which is a precision
    number -- not evidence of cheating. Conflating the two would make the season unable to
    report that its players are sometimes simply wrong."""
    out = CO.score_v3(_manifest(), ["c00", "c08"], player_kind="reasoning")
    assert out["false_positives"] == 1
    assert out["voided"] is False


def test_score_v3_keeps_the_old_headline_semantics():
    """catch_rate is still CATCHABLE-only. An undetectable canary missed remains the gate's
    blind spot rather than the pool's failure -- that rule was right and is untouched."""
    out = CO.score_v3(_manifest(), ["c00", "c01"], player_kind="reasoning")
    assert out["catch_rate"] == 1.0
    assert out["coverage_honesty"] == 1.0
    assert out["voided"] is False


def test_claim_evidence_is_not_a_fabricated_gate_result():
    """season_dryrun stamps a check_wiring sentence onto EVERY claim. For an LLM player the
    gate never named those functions -- the round that exposed this had the gate naming 0 of
    the 2 undetectable canaries the player claimed."""
    from season_dryrun import claim_evidence

    ev = claim_evidence("some_fn", player_name="llm", gate_named=False)
    joined = " ".join(ev).lower()
    assert "check_wiring" not in joined or "not" in joined, (
        "an LLM claim must not assert a check_wiring result that was never obtained")
    ev_mech = claim_evidence("some_fn", player_name="mechanical", gate_named=True)
    assert any("check_wiring" in e for e in ev_mech), \
        "the mechanical player's evidence IS the gate result and must still say so"
