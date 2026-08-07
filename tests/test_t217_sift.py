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


def test_every_tier_states_its_blindness():
    """T200's fidelity contract: numbers never travel without their stated blindness, or
    the transport launders a caveated finding into an omniscient one."""
    pack = sift.evidence_pack("open", corpus={"a.py": "open\n"})
    assert pack.blind, "an evidence pack that claims no blindness is lying"


# --------------------------------------------------------------- hats, tier 1
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
    out = sift.summarise(n=5, n_ok=3, blind=["one branch never returned"])
    assert out.status == "partially", f"3 of 5 is not a binary outcome: {out.status}"
    assert out.detail["n"] == 5 and out.detail["n_ok"] == 3
    assert sift.summarise(n=5, n_ok=5, blind=["x"]).status == "done"
    assert sift.summarise(n=5, n_ok=0, blind=["x"]).status == "failed"


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
