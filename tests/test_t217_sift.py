"""T217 RED pins -- sift, the nested ask.

PRE-REGISTERED ACCEPTANCE. Committed BEFORE core/coord/sift.py exists, so git holds
evidence the bar was set first (M3; the arc scorecard measured 30% clean and named this
exact drift -- pins landing WITH their implementation prove nothing about ordering).

Every pin here is a law bought with a receipt on 2026-08-06/07, cited inline. None is a
style preference.

THE L7 TRAP IS THE POINT OF test_evidence_pack_runs_on_the_real_repo: a pin that supplies
its own inputs tests the mechanism, not the wiring. It bit the prior seat three times in
one night (worst: timeline's pins fed dicts straight in, never exercised the parse, and
git's bare-epoch strings stamped the whole history at 1970). So at least one pin here runs
the real extractor over the real tree.
"""
from __future__ import annotations

import pytest  # noqa: F401  (used by the pins below)

# DELIBERATELY A HARD IMPORT. The first draft of this file used
# pytest.importorskip(...) and the suite answered "exit 5, no tests ran" -- a RED pin that
# SKIPS is not red, it is invisible, and the run reports green while testing nothing. That
# is the env_self_splits_hygiene_vs_exposes lesson exactly ("converts a real bug's loudest
# witness into a green test"), caught here on my own pins before commit.
from core.coord import sift


# --------------------------------------------------------------- evidence, tier 0
def test_evidence_pack_uses_word_boundaries():
    """L2, measured: the prior seat's fan was fed 'provenance' as usages of 'prove' and
    'DeepSeek' as usages of 'deep'. The word-boundary re-run FLIPPED 7 OF 20 VERDICTS
    (35% artifact rate) and dropped 7 of 40 terms for having no real usages at all.

    A detector whose evidence gatherer is wrong produces confident, well-formed, wrong
    answers -- the most expensive failure shape there is.
    """
    corpus = {
        "a.py": "provenance is not the word\nprove it\nimproved things\n",
        "b.py": "PROVE loudly\nunapproved\n",
    }
    pack = sift.evidence_pack("prove", corpus=corpus)
    hay = " ".join(o["text"] for o in pack.occurrences).lower()
    assert "provenance" not in hay, "substring match leaked provenance into 'prove'"
    assert "improved" not in hay and "unapproved" not in hay
    assert len(pack.occurrences) == 2, f"expected the 2 real usages, got {pack.occurrences}"


def test_evidence_pack_is_content_addressed():
    """The hash gate below is only as good as the address. Same corpus -> same sha;
    one changed byte -> different sha."""
    corpus = {"a.py": "open the door\n"}
    p1 = sift.evidence_pack("open", corpus=corpus)
    p2 = sift.evidence_pack("open", corpus=corpus)
    p3 = sift.evidence_pack("open", corpus={"a.py": "open the gate\n"})
    assert p1.sha == p2.sha, "identical input must hash identically"
    assert p1.sha != p3.sha, "changed evidence must change the address"
    assert len(p1.sha) >= 8


def test_evidence_pack_runs_on_the_real_repo():
    """L7 ANTI-TRAP -- the only pin here fed by reality instead of by me.

    'drained' is a KNOWN fork (three cursor families; cost 6 turns + a fleet pause), so it
    must have real usages at real file:line. A pack that parses my hand-built dict but
    dies on the actual tree is the timeline defect wearing a new hat.
    """
    pack = sift.evidence_pack("drained")
    assert pack.occurrences, "no real usages of a term known to span 6 files"
    for o in pack.occurrences[:20]:
        assert isinstance(o["line"], int) and o["line"] > 0, f"bad line number: {o}"
        assert o["file"] and not o["file"].startswith("b'"), f"undecoded path: {o}"


def test_vendored_vocabulary_never_enters_the_corpus():
    """FOUND BY RUNNING IT, not by thinking about it -- which is the L7 point.

    The first live pack reported `drained` in 67 files against a measured 6. The breakdown:
    56 tests / 51 docs / 27 source / 2 ComfyUI-Zluda -- a VENDORED third-party project with
    its own pyproject.toml living inside the tree. Its authors' use of `drained` is not our
    vocabulary in any sense the question means, and feeding it to a fan would have produced
    confident, well-formed findings about a stranger's codebase.

    This is the L2 failure one level up: the evidence gatherer, not the helper, was wrong.
    """
    pack = sift.evidence_pack("drained")
    bad = [o["file"] for o in pack.occurrences if "ComfyUI" in o["file"]]
    assert not bad, f"vendored third-party vocabulary leaked into the corpus: {bad[:3]}"


def test_every_occurrence_carries_its_plane_and_exclusions_are_counted():
    """Merging source/test/doc/vendor under one label 'occurrence' is itself a
    forked-semantics bug -- committed by the fork detector, which is why the plane rides on
    the occurrence instead of being resolved silently at scan time.

    And an exclusion must be COUNTED: 'no silent caps' applies to corpus membership as much
    as to result truncation. Absence that was a decision must not read as absence in fact.
    """
    pack = sift.evidence_pack("drained", planes=("source",))
    assert pack.occurrences
    assert all(o["plane"] == "source" for o in pack.occurrences)
    assert any("EXCLUDED BY PLANE" in b for b in pack.blind), \
        "dropped a large share of the corpus without saying so"

    docs = sift.evidence_pack("drained", planes=("doc",))
    assert docs.occurrences, "doc plane should be selectable, not merely discardable"
    assert docs.sha != pack.sha, "different planes must be different addresses"


def test_capping_samples_across_files_instead_of_truncating():
    """FOUND BY LOOKING AT WHAT THE FAN WOULD ACTUALLY SEE, which is a different act from
    checking that the cap works.

    The cap was honest about its SIZE (120 of 665, stated in blind) and silently dishonest
    about its SHAPE: it kept the first 120 in filesystem walk order, so 'open' reached the
    helper as 26 of 163 files with agent_cli.py alone supplying 47 occurrences. A helper
    reading that sample would correctly report that `open` means opening a file -- a
    well-formed, confident, unrepresentative answer produced by a truncation nobody
    described as a sample.

    A cap is a SAMPLE, and a sample that is not spread is a lie about the corpus.
    """
    corpus = {f"f{i}.py": "open one\nopen two\nopen three\n" for i in range(40)}
    pack = sift.evidence_pack("open", corpus=corpus, max_occurrences=20)
    files = {o["file"] for o in pack.occurrences}
    assert len(pack.occurrences) == 20
    assert len(files) >= 15, (
        f"cap kept only {len(files)} distinct files of 40 -- that is truncation wearing a "
        f"sample's clothes")


def test_junction_pack_shows_writer_and_reader_together():
    """THE SECOND EVIDENCE MODE, and the reason it exists is a measured negative result.

    The first live round ran drained/open/lock through 7 hats. The `junction` hat voted
    NO_FORK on BOTH drained and open -- including drained, whose three cursor families
    provably DO meet (T198, 6 turns + a fleet pause). It did not find the junction that IS
    the documented defect.

    The helpers said why, in their own BLIND lists: they wanted "the actual callers that
    unpack the drained integer" and "runtime branching logic where the fork would produce
    silent failures". A one-line-per-file breadth sample can ENUMERATE SENSES; it is
    structurally incapable of showing a PRODUCER AND ITS CONSUMER TOGETHER, which is what a
    junction is.

    Reading that NO_FORK as evidence against the junction hypothesis would have been
    inferring absence from a blind instrument -- the house disease, one level up.

    So: a junction pack pairs WRITE sites with READ sites and carries surrounding context.
    """
    corpus = {
        "producer.py": "def f():\n    out['drained'] = len(msgs)\n    return out\n",
        "consumer.py": "def g(rep):\n    if rep['drained'] > 0:\n        wake()\n",
        "unrelated.py": "# drained is discussed here but never read or written\n",
    }
    pack = sift.junction_pack("drained", corpus=corpus)
    assert pack.junctions, "found no writer/reader pair for a term that plainly has one"
    j = pack.junctions[0]
    assert j["writes"] and j["reads"], "a junction needs BOTH sides or it is not a junction"
    wf = {w["file"] for w in j["writes"]}
    rf = {r["file"] for r in j["reads"]}
    assert "producer.py" in wf and "consumer.py" in rf
    assert pack.sha and pack.blind


def test_junction_pack_excludes_its_own_pattern_definitions_and_comments():
    """L7's text-scanning trap, one level up, and it fired on the first live run.

    The prior seat's version: "a prohibition worth pinning is worth documenting, and
    documenting it puts the forbidden token in the file", which reddened four pins on the
    docstrings explaining their own compliance.

    Mine: a lexical junction detector CONTAINS its own patterns as string literals, so
    sift.py matched itself as a reader of `drained` -- the instrument measuring the
    instrument. The very first cross-file crossing reported for drained was
    `agent/bifrost_pull.py -> core/coord/sift.py`, pointing at my regex on line 307.

    A comment is also not a write. `# out["drained"] = ...` describes an assignment; it
    does not perform one, and counting prose as mechanism is how a docstring becomes
    evidence of a defect.
    """
    corpus = {
        "real.py": "out['x'] = 1\n",
        "reader.py": "if d['x'] > 0:\n    pass\n",
        "commentary.py": "# out['x'] = 1 is how you would write it\n",
        "patterns.py": "PAT = r\"\\['x'\\]\\s*=\"   # a detector's own literal\n",
    }
    pack = sift.junction_pack("x", corpus=corpus, exclude_self=False)
    cited = {w["file"] for j in pack.junctions for w in j["writes"]}
    assert "commentary.py" not in cited, "a comment describing a write counted as a write"
    assert "real.py" in cited, "dropped the genuine write while filtering"

    # and the module never reports itself
    live = sift.junction_pack("drained")
    selfhits = [j["crossing"] for j in live.junctions if "coord/sift.py" in j["crossing"]]
    assert not selfhits, f"the detector matched its own source: {selfhits[:2]}"


def test_junction_pack_reports_no_junction_rather_than_inventing_one():
    """UNKNOWN must stay representable. A term used only in prose has no junction, and
    saying so is a real answer -- collapsing 'I cannot see one' into 'there is none' is the
    T155 failure that made a beating-but-wedged seat read as running."""
    corpus = {"a.py": "# the word cursor appears only in this comment\n"}
    pack = sift.junction_pack("cursor", corpus=corpus)
    assert pack.junctions == []
    assert any("no writer/reader pair" in b.lower() or "no junction" in b.lower()
               for b in pack.blind), "must SAY it found none, not merely return empty"


def test_every_tier_states_its_blindness():
    """T200's fidelity contract: numbers never travel without their stated blindness, or
    the transport launders a caveated finding into an omniscient one."""
    pack = sift.evidence_pack("open", corpus={"a.py": "open\n"})
    assert pack.blind, "an evidence pack that claims no blindness is lying"


# --------------------------------------------------------------- hats, tier 1
def test_a_retired_hat_stays_retired_with_its_reason():
    """ABLATION OUTCOME, pre-registered at 1f31575, measured at 40de626.

    `economist` scored 1/3 precision on the hand-adjudicated terms, reaching FORK on all
    three including BOTH false positives, with the second-highest uniqueness in the pool and
    ZERO marginal contribution. It was manufacturing exactly the lone-hat FORK that
    CONSENSUS_FLOOR exists to suppress.

    The retirement carries its REASON in the tree, because a hat removed without one is a
    hat someone re-adds reasonably in three weeks. Same discipline as the negative results
    pinned in terms.py's BLIND list.
    """
    assert "economist" not in sift.DEFAULT_HATS
    assert "economist" in sift.RETIRED_HATS
    assert "precision" in sift.RETIRED_HATS["economist"]
    with pytest.raises(KeyError):
        sift.hat_prompt("economist", sift.evidence_pack("x", corpus={"a.py": "x\n"}))


def test_hats_are_descriptive_not_normative():
    """L1, measured (T207, pre-registered at b02f46a): grounded factual lookups were
    correct 5/5 with citations; ONE normative question ('should this count MORE kinds or
    FEWER?') came back confidently wrong with real, accurate citations. It failed by
    equivocating on a word.

    The tell is should/better/more/fewer. Ask what the code DOES; draw the therefore
    yourself. The jester is exempt: its whole job is an argument, and it is read as an
    argument, never as a verdict.
    """
    for name, prompt in sift.DEFAULT_HATS.items():
        if name == "jester":
            continue
        low = prompt.lower()
        for banned in (" should ", " better ", " more kinds", " fewer"):
            assert banned not in low, f"hat {name!r} outsources the therefore: {banned!r}"


def test_curator_pairs_vary_hats_within_a_pair_on_one_term():
    """claude#42d00626, point 2: two curators wearing different hats on DIFFERENT terms
    cannot be diffed at all. Only same-term overlap is computable, and it yields dissent
    that points at a WORD rather than at a methodology."""
    pairs = sift.curator_pairs("open", list(sift.DEFAULT_HATS))
    assert pairs, "no pairs produced"
    for a, b in pairs:
        assert a["term"] == b["term"] == "open", "a pair must sit on ONE term"
        assert a["hat"] != b["hat"], "hats must vary WITHIN the pair, not across pairs"


# --------------------------------------------------------------- the gate, tier 2
def test_flip_rate_refuses_when_evidence_hashes_differ():
    """THE LOAD-BEARING PIN. claude#42d00626's catch, and he shipped the bug one tier
    down the same night (T216, 54bc84c): --with was accepted on the fan path and SILENTLY
    dropped, so five helpers answered well-formed about zero files.

    Curator disagreement has THREE causes: real ambiguity, curation artifact, and INPUT
    DIVERGENCE. Compute a flip rate across mismatched inputs and you measure transport
    noise and report it as curation signal -- the same defect, one tier up.

    Refusal must be LOUD and must name the mismatch. Silence here would be the T216
    failure reproduced by the very thing built to catch it.
    """
    d1 = {"term": "open", "hat": "junction", "evidence_sha": "aaaaaaaa", "verdict": "FORK"}
    d2 = {"term": "open", "hat": "linguist", "evidence_sha": "bbbbbbbb", "verdict": "NO_FORK"}
    out = sift.compare_dossiers([d1, d2])
    assert out["flip_rate"] is None, "computed a rate over inputs that were not identical"
    assert out["refused"], "refused silently -- the caller cannot tell a refusal from agreement"
    assert "aaaaaaaa" in out["refused"] and "bbbbbbbb" in out["refused"], \
        "refusal must name BOTH hashes so the divergence is locatable"


def test_flip_rate_computes_when_hashes_match():
    """The gate must not be a wall: identical evidence, differing verdicts = real signal."""
    d1 = {"term": "open", "hat": "junction", "evidence_sha": "cafebabe", "verdict": "FORK"}
    d2 = {"term": "open", "hat": "linguist", "evidence_sha": "cafebabe", "verdict": "NO_FORK"}
    out = sift.compare_dossiers([d1, d2])
    assert out["refused"] is None
    assert out["flip_rate"] == 1.0, "one disagreeing pair over one pair = 1.0"
    assert out["dissents"], "a disagreement must surface in dissents"


def test_a_verdict_resting_on_one_hat_against_five_renders_contested():
    """MEASURED DEFECT, first cost-blind sample (pre-registered at b73a757).

    Two of three FORK verdicts were false positives and both had one shape: the curator
    promoted a LONE dissenting hat over a five-or-six hat NO_FORK consensus. `behaviour`
    (intended vs actual) and `remain` (continue-to-be vs residual) are ordinary English
    polysemy that 6-of-7 and 5-of-7 hats respectively rejected.

    The effect on the headline was not cosmetic: untriaged the sample showed a +43 point
    spread effect, triaged it showed +14, and those fall on OPPOSITE SIDES of the
    pre-registered 20-point line. A curation tier that reports only the winning label,
    without the margin it won by, will keep doing this.

    So the tally rides in the verdict. One-against-five is CONTESTED, never FORK.
    """
    lopsided = {"term": "behaviour", "hat": "outsider", "evidence_sha": "aa11",
                "verdict": "FORK", "tally": {"FORK": 1, "NO_FORK": 6}}
    assert sift.settle_verdict(lopsided) == "CONTESTED"

    solid = {"term": "capabilities", "hat": "outsider", "evidence_sha": "aa11",
             "verdict": "FORK", "tally": {"FORK": 5, "NO_FORK": 2}}
    assert sift.settle_verdict(solid) == "FORK", \
        "a real majority must survive -- this guard must not eat the genuine finding"

    # No tally reported: the margin is UNKNOWN and must not be invented in either direction.
    assert sift.settle_verdict({"verdict": "FORK"}) == "FORK"


def test_contested_is_not_silently_folded_into_agreement():
    """A CONTESTED term is a finding about the EVIDENCE being genuinely ambiguous, which is
    the second of the three causes of disagreement. Folding it into NO_FORK would discard
    exactly the cases most worth a human read."""
    same = "bb22"
    ds = [
        {"term": "t1", "hat": "a", "evidence_sha": same, "verdict": "CONTESTED"},
        {"term": "t1", "hat": "b", "evidence_sha": same, "verdict": "CONTESTED"},
    ]
    out = sift.compare_dossiers(ds)
    assert out["agreements"], "both curators agreed the term is contested"
    assert out["agreements"][0]["verdicts"] == ["CONTESTED"]


def test_two_abstentions_are_not_agreement():
    """HEDGING SWEEP, proposed by claude#42d00626 after T221: "any place we let an agent hedge
    (confidence, UNCLEAR, UNKNOWN, PARTIALLY) and score it, check whether hedging is
    dominant." Ran it against this module first and it fired.

    Two curators who both said UNCLEAR rendered as AGREEMENT, and the pair counted in the
    flip-rate DENOMINATOR at 0.0 -- so an abstention silently improved the very number I
    published as the curation tier's artifact rate. In the cost-blind sample `grants` and
    `lease` were both UNCLEAR/UNCLEAR and sat in "agreement (8)".

    Two people saying "I do not know" is not consensus. It is a shared blind spot with no
    verdict, and calling it agreement is the same lie as calling UNKNOWN a negative -- which
    this repo has now paid for at T155, T141 and T179.

    His deeper point is why this matters beyond one function: we spend all night TEACHING
    helpers to abstain, because L1 makes abstention the correct answer under uncertainty. If
    a scored surface then makes abstention free, we pay for exactly the behaviour we praise,
    and the praise hides it.
    """
    same = "cc33"
    out = sift.compare_dossiers([
        {"term": "t1", "hat": "a", "evidence_sha": same, "verdict": "UNCLEAR"},
        {"term": "t1", "hat": "b", "evidence_sha": same, "verdict": "UNCLEAR"},
    ])
    assert [a["term"] for a in out["agreements"]] == [], \
        "two abstentions counted as consensus"
    assert [d["term"] for d in out["dissents"]] == [], "nor is it dissent -- nobody decided"
    assert [u["term"] for u in out["undecided"]] == ["t1"]
    assert out["flip_rate"] is None, \
        "a flip rate over zero deciding pairs is not 0.0, it is undefined"


def test_the_flip_rate_denominator_counts_only_deciding_pairs():
    """The artifact rate must be per-DECISION. Leaving abstentions in the denominator lets a
    tier improve its own score by declining to answer -- hedging made profitable in the one
    metric that is supposed to catch bad curation."""
    same = "dd44"
    ds = [
        {"term": "real1", "hat": "a", "evidence_sha": same, "verdict": "FORK"},
        {"term": "real1", "hat": "b", "evidence_sha": same, "verdict": "NO_FORK"},
        {"term": "real2", "hat": "a", "evidence_sha": same, "verdict": "NO_FORK"},
        {"term": "real2", "hat": "b", "evidence_sha": same, "verdict": "NO_FORK"},
        {"term": "punt", "hat": "a", "evidence_sha": same, "verdict": "UNCLEAR"},
        {"term": "punt", "hat": "b", "evidence_sha": same, "verdict": "UNCLEAR"},
    ]
    out = sift.compare_dossiers(ds)
    assert out["flip_rate"] == 0.5, (
        f"1 dissent over 2 DECIDING pairs is 0.5, not {out['flip_rate']} -- an abstention "
        f"must not dilute the artifact rate")
    assert len(out["undecided"]) == 1
    assert any("undecided" in b.lower() or "abstain" in b.lower() for b in out["blind"]), \
        "a report with undecided terms must say so where the rate is read"


def test_dissent_is_rendered_before_agreement():
    """The prior seat's §7: 'you are the bottleneck, not the helpers'. Dissent-first was
    his highest-leverage UNBUILT feature -- read the one disagreement, skip the four
    consensuses. Ordering is the whole ergonomic win, so it is pinned, not left to taste.
    """
    same = "d00dfeed"
    ds = [
        {"term": "t1", "hat": "a", "evidence_sha": same, "verdict": "FORK"},
        {"term": "t1", "hat": "b", "evidence_sha": same, "verdict": "FORK"},
        {"term": "t2", "hat": "a", "evidence_sha": same, "verdict": "FORK"},
        {"term": "t2", "hat": "b", "evidence_sha": same, "verdict": "NO_FORK"},
    ]
    out = sift.compare_dossiers(ds)
    assert [d["term"] for d in out["dissents"]] == ["t2"]
    assert [a["term"] for a in out["agreements"]] == ["t1"]
    assert out["render_order"][0] == "dissents", "consensus must not be read first"


# --------------------------------------------------------------- L3, the corrected law
def test_implausible_rate_triggers_triage_and_never_discards():
    """POINT 3 of the veteran's clipped note, recovered from
    research/in-flight/_note_to_fresh_seat_3.txt and corrected by its author:

      'L3 is a PRIOR AGAINST COMMON DEFECTS. If a defect class genuinely affects 40% of a
       corpus, L3 tells you to doubt your harness -- and that is exactly the reasoning
       that would have made me disbelieve the 408-way docstring audit BEFORE triaging it.
       That audit's 37 percent was PARTLY REAL. So: use L3 to trigger a triage sample,
       never to discard a result.'

    So the flag is advisory and the findings SURVIVE it. A law that eats real defects to
    protect a prior is worse than the harness bug it guards against.
    """
    same = "beefbeef"
    ds = []
    for i in range(10):
        v = "FORK" if i < 9 else "NO_FORK"
        ds.append({"term": f"t{i}", "hat": "a", "evidence_sha": same, "verdict": v})
        ds.append({"term": f"t{i}", "hat": "b", "evidence_sha": same, "verdict": "NO_FORK"})
    out = sift.compare_dossiers(ds)
    assert out["triage_required"] is True, "90% dissent must raise the alarm"
    assert out["triage_reason"], "an alarm with no reason cannot be acted on"
    assert len(out["dissents"]) == 9, "triage must SAMPLE the findings, never drop them"


# --------------------------------------------------------------- the aggregate
def test_aggregate_is_three_state_never_binary():
    """ask_many's own docstring earned this: 'a binary fan verdict discards the partial
    result, which is exactly how nine tasks, two findings reads as failure instead of as
    two findings.' Branch failed -> partial -> done, in that order
    (boundary_outcome_ok_includes_partial_double_strike: .ok includes partials, and that
    trap struck twice in one hour)."""
    part = sift.summarise(n=5, n_ok=3, blind=["one branch never returned"])
    full = sift.summarise(n=5, n_ok=5, blind=["x"])
    none = sift.summarise(n=5, n_ok=0, blind=["x"])

    assert (part.ok, part.partial) == (True, True), "3 of 5 must be PARTIAL, not binary"
    assert (full.ok, full.partial) == (True, False)
    assert none.ok is False
    assert part.detail["n"] == 5 and part.detail["n_ok"] == 3
    assert part.why, "a partial that cannot say what is missing is the T170 defect"

    # THE DOUBLE-STRIKE, pinned as a behaviour rather than as a comment. `.ok` is True for
    # BOTH the partial and the full run, so branching on .ok silently treats 3-of-5 as
    # success -- that trap hit twice in one hour on 2026-08-05 (a timeout rendered as
    # CLOSED.ECHO because the CLI echo-branch tested o.ok). Truthiness is the safe test.
    assert part.ok == full.ok, "precondition: .ok cannot separate partial from done"
    assert bool(part) is False and bool(full) is True, \
        "a partial must be FALSY so callers that ignore partiality fail closed"


def test_no_silent_caps():
    """'If a workflow bounds coverage (top-N, no-retry, sampling), log what was dropped --
    silent truncation reads as covered-everything when it did not.' Tonight's W137 is the
    same law on the transport plane: a clip with no pointer is unrecoverable BY DESIGN."""
    corpus = {"a.py": "\n".join(f"open {i}" for i in range(500))}
    pack = sift.evidence_pack("open", corpus=corpus, max_occurrences=10)
    assert len(pack.occurrences) == 10
    assert pack.truncated is True
    assert any("490" in b or "500" in b for b in pack.blind), \
        "capped evidence must say HOW MUCH it dropped, in its own blind list"
