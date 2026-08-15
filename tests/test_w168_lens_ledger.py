"""W168 pins: score fan lenses by what SURVIVED, not by whether the model replied.

Daniil asked for this on 2026-08-11 -- the route journal's own docstring says so: "the
substrate for per-route funnel counters (fan vs solo tokens-per-confirmed-finding -- Daniil
2026-08-11, 'quantify the impact delta')". The substrate landed. The counters never did.

THE MOTIVATING EVIDENCE IS IN THE JOURNAL ITSELF, two lines apart, 2026-08-14:

    09:22:52  geometry=lens  n=5  n_ok=5  $0.0163   30s
    09:27:20  geometry=lens  n=5  n_ok=5  $0.0692  135s

The first is the fan where ALL FIVE branches abstained ("the prompt contains no digest
text") and produced nothing -- the pack never reached them. The second produced the
extraction plan, the seam hypothesis and the game-engine analysis that settled an
architecture decision. The journal scores them IDENTICALLY, and on its only signal the
useless one looks BETTER: four times faster and a quarter the cost.

`n_ok` means the model replied. It has never meant the reply was worth anything.

FOUR THINGS THIS MUST NOT DO, each earned:

1. TREAT AN HONEST ABSTENTION AS A MISS. All five branches in that first fan were RIGHT to
   abstain -- they refused to invent citations from aggregates quoted in the question. A
   scorer that counts those as failures would train the fleet toward confident fabrication,
   which is the opposite of what the findings preset exists for.

2. LET UNVERIFIED CLAIMS COUNT AS WINS. The ledger already carries this finding (T254):
   "unscored claims dilute the refuted rate to zero, so volume erases the penalty." A lens
   that emits fifty unchecked findings must not outrank one that emitted two confirmed ones.

3. PUT A NUMBER ON THIN EVIDENCE. `llm_player_recall_is_noise_at_n1_while_precision_and_
   capability_are_stable` -- with one round per lens, any rate is noise. UNRATED is the
   honest verdict and it is not a placeholder for zero.

4. GATE A LENS OFF FOREVER. A lens that stops running can never earn its way back, and the
   sample that condemned it is exactly the sample that was too small to trust. Gating keeps
   an exploration floor.

And it RECOMMENDS, never enforces (instrument_proposes_never_self_ratifies): a structural
scorer has no business silencing a lens until a human has read its ledger.
"""
import pytest

from core.coord import lens_ledger as L


def _rec(lens, outcome, fan="f1"):
    return L.LensRun(lens=lens, geometry="lens", outcome=outcome, fan_id=fan, note="")


# ---------------------------------------------------------------- vocabulary

def test_v1_the_four_outcomes_are_distinct_states():
    """confirmed/refuted are the SCORED pair; abstained and unverified are neither."""
    assert L.SCORED == frozenset({"confirmed", "refuted"})
    assert "abstained" not in L.SCORED and "unverified" not in L.SCORED


def test_v2_an_unknown_outcome_is_refused_not_coerced():
    """A silent coercion to 'unverified' would hide a caller bug as a coverage gap."""
    with pytest.raises(ValueError):
        L.LensRun(lens="x", geometry="lens", outcome="probably-fine", fan_id="f", note="")


# ---------------------------------------------------------------- scoring

def test_s1_hit_rate_is_confirmed_over_VERIFIED_not_over_total():
    """The T254 rule. Fifty unverified findings must not dilute two refutations to noise."""
    runs = [_rec("A", "confirmed"), _rec("A", "refuted")] + [_rec("A", "unverified")] * 50
    s = L.score(runs, min_verified=2)["A"]
    assert s.verified_n == 2
    assert s.hit_rate == 0.5
    assert s.unverified_n == 50


def test_s2_below_min_verified_the_rate_is_UNRATED_never_zero():
    """A lens with one checked finding has no rate. UNRATED is a verdict, not a placeholder."""
    s = L.score([_rec("A", "refuted")], min_verified=3)["A"]
    assert s.hit_rate is None
    assert s.verdict == "UNRATED"
    assert "too few" in s.why.lower() or "1" in s.why


def test_s3_an_abstention_is_NOT_a_miss():
    """All five branches abstained honestly on 2026-08-14 rather than fabricate. Counting
    that as failure would train the fleet toward confident invention."""
    runs = [_rec("A", "abstained")] * 5
    s = L.score(runs, min_verified=1)["A"]
    assert s.hit_rate is None, "abstentions must not produce a rate"
    assert s.abstained_n == 5
    assert "abstain" in s.why.lower()


def test_s4_abstentions_are_reported_as_a_SIGNAL_not_hidden():
    """A lens that always abstains is telling you the pack is wrong, not that the lens is."""
    s = L.score([_rec("A", "abstained")] * 5, min_verified=1)["A"]
    assert s.abstained_n == 5
    assert s.verdict == "ABSTAINING"


def test_s5_a_lens_with_only_unverified_runs_is_UNSCORED_and_says_who_should_check():
    s = L.score([_rec("A", "unverified")] * 9, min_verified=2)["A"]
    assert s.verdict == "UNSCORED"
    assert s.hit_rate is None
    assert "verif" in s.why.lower()


def test_s6_scores_are_per_lens_not_per_fan():
    """The journal records fans. A fan of five is five different questions, and collapsing
    them is what made the failed fan and the decisive one look identical."""
    runs = [_rec("A", "confirmed"), _rec("B", "refuted"),
            _rec("A", "confirmed"), _rec("B", "refuted")]
    s = L.score(runs, min_verified=2)
    assert set(s) == {"A", "B"}
    assert s["A"].hit_rate == 1.0 and s["B"].hit_rate == 0.0


# ---------------------------------------------------------------- gating

def test_g1_a_proven_loser_is_recommended_for_deprioritising():
    runs = [_rec("dud", "refuted")] * 6 + [_rec("good", "confirmed")] * 6
    plan = L.gate(L.score(runs, min_verified=3), floor=0.0)
    assert plan["good"] == "run"
    assert plan["dud"] == "deprioritise"


def test_g2_an_UNRATED_lens_is_never_gated_off():
    """The sample that would condemn it is the sample too small to trust."""
    runs = [_rec("new", "refuted")]
    plan = L.gate(L.score(runs, min_verified=5), floor=0.0)
    assert plan["new"] == "run"


def test_g3_the_exploration_floor_keeps_sampling_a_loser():
    """A lens gated to zero can never earn its way back -- the sample that condemned it is
    frozen forever. The floor is what makes the ledger a measurement rather than a verdict."""
    runs = [_rec("dud", "refuted")] * 10
    plan = L.gate(L.score(runs, min_verified=3), floor=0.2)
    assert plan["dud"] == "explore"


def test_g4_gating_is_a_RECOMMENDATION_and_says_so():
    """instrument_proposes_never_self_ratifies: no lens gets silenced by arithmetic alone."""
    out = L.render(L.score([_rec("dud", "refuted")] * 6, min_verified=3),
                   L.gate(L.score([_rec("dud", "refuted")] * 6, min_verified=3), floor=0.0))
    assert "recommend" in out.lower()
    assert "not enforced" in out.lower() or "advisory" in out.lower()


# ---------------------------------------------------------------- render

def test_r1_the_render_shows_the_UNVERIFIED_gap_not_only_the_rate():
    """The coverage gap is the honest headline: a ledger of mostly-unchecked findings is a
    ledger that has not earned its numbers."""
    runs = [_rec("A", "confirmed")] * 2 + [_rec("A", "unverified")] * 20
    out = L.render(L.score(runs, min_verified=2), {})
    assert "20" in out
    assert "unverified" in out.lower()


def test_r2_an_empty_ledger_says_so_rather_than_rendering_a_table_of_nothing():
    assert "no runs" in L.render({}, {}).lower()


def test_s7_a_confirmed_finding_outranks_the_abstention_signal():
    """FOUND BY RUNNING IT on today's real fan. The first cut checked abstentions BEFORE
    thin-evidence, so a lens with 1 confirmed and 1 abstained rendered as ABSTAINING --
    burying the only lens that had produced a surviving finding.

    Abstention describes the PACK. A verified outcome describes the LENS. The second is
    about the thing being scored, so it wins."""
    runs = [_rec("A", "confirmed"), _rec("A", "abstained")]
    s = L.score(runs, min_verified=5)["A"]
    assert s.verdict == "UNRATED", "a confirmed finding must not read as ABSTAINING"
    assert s.confirmed_n == 1
    assert "abstention" in s.why.lower(), "the abstention is still reported, just not the headline"


def test_s8_ABSTAINING_still_fires_when_NOTHING_was_verified():
    """The signal must survive the fix: a lens that only ever abstained is telling you the
    pack is broken, and that is worth its own verdict."""
    s = L.score([_rec("A", "abstained")] * 4, min_verified=5)["A"]
    assert s.verdict == "ABSTAINING"


# ---------------------------------------------------------------- lens identity

PACK = "MEASURED DIGEST\n8336 lines, 87 verbs, build_parser 1250 lines.\n\n"
FOOT = "\n\nLead with your strongest claim. Mark [ASSUMED] where you cannot see the code."


def test_i1_a_lens_is_named_by_what_DIFFERS_not_by_the_shared_pack():
    """With the pack riding inside each prompt (the only arrangement that delivers it,
    since --prompt-file does not compose with --lens), every branch shares its opening
    text. prompt[:300] would name them all identically."""
    prompts = [PACK + "RIGHT-SIZING: what are the modules?" + FOOT,
               PACK + "THE MISSING SEAM: what should be shared?" + FOOT,
               PACK + "GAME ENGINE LENS: what transfers?" + FOOT]
    ids = L.lens_identity(prompts)
    assert len(set(ids)) == 3, f"branches were not distinguished: {ids}"
    assert "right-sizing" in ids[0]
    assert "seam" in ids[1]
    assert "game" in ids[2]


def test_i2_the_shared_FOOTER_is_trimmed_too():
    """Lens text usually sits between a shared pack and a shared contract. Including the
    footer buries the distinguishing part past the width limit."""
    ids = L.lens_identity([PACK + "ALPHA QUESTION" + FOOT, PACK + "BETA QUESTION" + FOOT])
    assert all("lead-with-your-strongest" not in i for i in ids), ids


def test_i3_identical_prompts_are_named_INDISTINCT_rather_than_faked():
    """A panel fan (self-consistency) has no lens delta. Inventing distinct names would
    make N samples of one question look like N questions -- exactly the collapse this
    ledger exists to undo."""
    ids = L.lens_identity(["same question"] * 3)
    assert all(i.startswith("indistinct-branch-") for i in ids), ids
    assert len(set(ids)) == 3, "they are still distinguishable positionally"


def test_i4_a_single_prompt_still_gets_a_name():
    assert L.lens_identity(["find the bug in the parser"])[0].startswith("find-the-bug")


def test_i5_empty_input_is_empty_not_a_crash():
    assert L.lens_identity([]) == []
