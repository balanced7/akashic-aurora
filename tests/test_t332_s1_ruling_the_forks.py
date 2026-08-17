"""T332 s1 RED: Daniil's two rulings on the T176 forks, pinned before the rewire.

WHAT s1 REPORTED AND REFUSED TO DECIDE. The registry shipped 2026-08-16 (RED 9bfc5b80,
GREEN 6c22f2c7 -- NOT 66a95108, which is T323 s1's RED and is miscited in T332's own title;
this file is the correcting record) and its first live output found two things it was built
to surface and forbidden to settle: `ask` forked across three sets differing on `blocker`,
and `note`/`decision` living on multiple planes with opposite policies. The module says so in
its own closing paragraph -- "it does not pick a winner, because picking one is a policy
ruling and rulings belong to the operator."

RULING 1 (Daniil, 2026-08-17) -- THE FORK WAS A FALSE FORK, and the evidence is the producer
census. Exactly one site emits kind="blocker": the daemon's circuit breaker, at
scripts/bifrost_daemon.py:221 (runner child crash-looping) and :448 (runner down,
re-escalation). BOTH ARE `bus.broadcast(...)`. Never directed. That single fact dissolves the
disagreement, because the three sets are not one concept forked three ways -- they are three
DIFFERENT QUESTIONS wearing one name:

    agent/bifrost_pull.py:_ASK_KINDS     "does this need the seat to DO something?"  -> yes
    agent_cli.py:ASK_KINDS               "does a DIRECTED send auto-arm a deadline?" -> n/a
    core/comm/packet_spec.py:STALE_ASK_KINDS  "if stale, surfaced or dropped?"       -> MUST
                                                                                        surface

The middle one is n/a rather than no: agent_cli.py:5884 already REFUSES to arm an expectation
on a broadcast -- "a broadcast has no single answerer to redrive" -- so the machinery that set
gates structurally cannot apply to a message with no addressee. Its absence there was never a
hole. So there is exactly ONE real defect, in the third: a tripped circuit breaker that nobody
reads inside the 6h window is classified a stale NON-ask and skipped past by the cursor sweep.
The daemon shouting "runner down 40min" is the single message that must never be silently
dropped, and it was the only ask-shaped kind that could be.

THE PRECEDENT IS IN THAT FILE ALREADY. The T174 comment at packet_spec.py:366 records this
exact shape resolved once before: `ask` lived in one set alone, nothing emitted it, and the
predicate called it an ask while nothing treated it as one. The fix was not picking a winner.
It was making the token mean one thing. Hence: the three sets get names that say what they
gate, and `blocker` answers each independently (yes / n-a / yes).

WHY THE REGISTRY CALLED IT A FORK ANYWAY, which is its own small finding: forks() compares
memberships BY NAME, and by name it is one concept. It cannot see that the names lie. An
instrument that groups by identifier inherits every lie the identifiers tell.

RULING 2 (Daniil, 2026-08-17) -- THE PLANE BECOMES A REQUIRED ARGUMENT. `note` is on all
three planes with opposite policies and `decision` on two, and the chosen fix is to make the
ambiguous question unaskable rather than answered-by-convention: resolve() cannot be called
without naming the plane. This is the house's standing move (BoundaryOutcome, R14, KindVerdict
itself) -- make the bad state unrepresentable -- and it was chosen over renaming per plane
because renaming rewrites the meaning of records already stored under the bare name, which is
a migration event, not a store primitive. Additive beats migratory: durability over legibility
(note durability-over-legibility-2026-08-16).

Run: py -m pytest tests/test_t332_s1_ruling_the_forks.py -q
"""
from __future__ import annotations

import ast
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import kinds as K            # noqa: E402
from core.comm import packet_spec           # noqa: E402


# ============================================================ RULING 1: the three questions

def test_p1_the_stale_gate_set_says_what_it_gates():
    """The rename is the ruling. `STALE_ASK_KINDS` describes neither its members nor its
    effect -- it gates whether a stale message is SURFACED or DROPPED, and a blocker is not
    an ask. A name that lies is the defect class this whole arc exists to kill."""
    assert hasattr(packet_spec, "NEVER_DROP_WHEN_STALE"), (
        "the set that decides surfaced-vs-dropped must be named for that, not for 'ask'")
    assert not hasattr(packet_spec, "STALE_ASK_KINDS"), (
        "the old name must be GONE, not aliased -- an alias keeps the lie resolvable and "
        "lets the fork silently reappear under the name that caused it")


def test_p2_a_tripped_breaker_is_never_silently_dropped():
    """THE ONE REAL BEHAVIOUR CHANGE IN THE SLICE. The daemon's only two blocker producers
    are broadcasts about a dead or crash-looping runner. Before this, such a message going
    stale was classified a non-ask and skipped past by the cursor sweep."""
    assert packet_spec.never_drop_when_stale("blocker"), (
        "a tripped circuit breaker must survive the stale gate -- it is the message whose "
        "whole purpose is to still be there when someone finally looks")


def test_p3_t174s_invariant_survives_the_rename():
    """T174 retired the token `ask` from this set because it woke nobody and armed nothing.
    That ruling is older than this one and is NOT being reopened -- pinned explicitly rather
    than left to the exact-equality assertion it used to ride on."""
    assert not packet_spec.never_drop_when_stale("ask"), (
        "T174 retired kind='ask'; adding blocker must not smuggle it back")
    assert set(packet_spec.NEVER_DROP_WHEN_STALE) == {
        "question", "request", "handoff", "blocker"}


def test_p4_the_gate_surfaces_a_stale_blocker_instead_of_skipping_it():
    """The pin that tests the MECHANISM, not the membership. partition_stale is the live
    consumer of the set; a blocker must land in the surfaced bucket, not the dropped one."""
    # Real epoch-ms, not a small integer: message ids are "<ms>-<seq>" and msg_age_ms splits
    # on "-", so a negative timestamp parses to "" and reads as UNPARSEABLE -- which the gate
    # treats as fresh. The first draft of this pin failed for that reason instead of the one
    # it was testing, which is the pin-supplies-its-own-input class caught early.
    now = 1_786_900_000_000
    old = now - (7 * 3600 * 1000)          # 7h old, past the 6h default
    msgs = [{"id": f"{old}-0", "kind": "blocker"},
            {"id": f"{old}-1", "kind": "trace"}]
    fresh, surfaced, dropped = packet_spec.partition_stale(
        msgs, now_ms=now, stale_ms=6 * 3600 * 1000,
        id_of=lambda m: m["id"], kind_of=lambda m: m["kind"])
    assert fresh == []
    assert [m["kind"] for m in surfaced] == ["blocker"], (
        "the stale breaker must be surfaced for triage")
    assert [m["kind"] for m in dropped] == ["trace"], (
        "telemetry still skips -- the change is scoped to blocker, not a widening of the net")


def test_p5_the_redrive_set_says_it_is_about_directed_sends():
    """agent_cli's set gates ONE thing: whether a DIRECTED send auto-arms a reply deadline.
    `blocker` stays out -- not as an oversight, as a consequence. Broadcasts have no single
    answerer to redrive, and the CLI already refuses to arm one."""
    src = open(os.path.join(ROOT, "agent_cli.py"), encoding="utf-8").read()
    assert "AUTO_REDRIVE_KINDS" in src, "the set must be named for the machinery it gates"
    assert "ASK_KINDS = {" not in src, "the old ambiguous name must be gone"


def test_p5b_the_broadcast_refusal_that_makes_blocker_n_a_still_stands():
    """P5's reasoning depends on this guard existing. If it ever goes, `blocker`'s absence
    from the redrive set stops being a consequence and becomes an unexamined exclusion --
    so the reason is pinned, not just the conclusion."""
    src = open(os.path.join(ROOT, "agent_cli.py"), encoding="utf-8").read()
    assert "has no single answerer to redrive" in src, (
        "the broadcast-cannot-be-redriven refusal is the premise of the n/a ruling")


def test_p6_the_attention_bucket_says_it_is_about_attention():
    """bifrost_pull's set feeds the `N asks / M fyi / K traces` triage line. Its real question
    is 'must the seat DO something', and for a tripped breaker the answer was already yes --
    this site was right all along and only its name was wrong."""
    from agent import bifrost_pull
    assert hasattr(bifrost_pull, "_NEEDS_ATTENTION_KINDS"), (
        "the triage bucket must be named for attention, not for asks")
    assert not hasattr(bifrost_pull, "_ASK_KINDS"), "the old name must be gone"
    summary = bifrost_pull.kind_summary([{"kind": "blocker"}])
    assert summary["asks"] == 1, "a tripped breaker needs the seat to act"


def test_p7_the_registry_no_longer_reports_a_fork_that_was_ruled_on():
    """The loop closes here. A ruling that leaves the instrument still shouting 'FORK' has
    not been applied -- it has been remembered, which is the failure mode the registry was
    built to end."""
    assert "ask" not in K.forks(), (
        "the ask fork is ruled: three questions, three names, no shared concept left")


# ============================================================ RULING 2: the plane is required

def test_p8_you_cannot_ask_a_kind_question_without_naming_the_plane():
    """DANIIL'S RULING, as a type error. `note` means three different things and the old
    two-argument call could not tell which one was being asked about -- so it answered
    confidently about the bus every time, including when the caller meant a beat."""
    with pytest.raises(TypeError):
        K.resolve("note", "salient")        # type: ignore[call-arg]


def test_p9_a_plane_mismatch_is_unclassified_with_a_reason_never_a_silent_false():
    """The T176 law applied to the new argument: asking a bus-plane policy about a beat-plane
    kind is not a NO. Nobody ever decided it, and the caller is told which half was missing."""
    v = K.resolve("note", "salient", plane="beat_kind")
    assert v.classified is False, "a cross-plane question has no policy answer"
    assert v.value is None, "and must not hand back a False that reads as a decision"
    assert "plane" in v.why.lower(), f"the reason must name the mismatch, got: {v.why!r}"


def test_p10_the_same_kind_on_its_own_plane_still_answers():
    """The mirror of P9 -- the required argument must not break real questions."""
    v = K.resolve("note", "salient", plane="bus_kind")
    assert v.classified is True, "a bus note on a bus policy is a real, answerable question"
    assert v.value is False, "and the answer is a considered NO -- notes are not salient"


def test_p11_the_plane_vocabulary_does_not_fork_the_way_ask_did():
    """THE DEFECT THIS SLICE WOULD OTHERWISE CREATE. The registry names the planes
    bus_kind/event_kind/beat_kind; scripts/checkers/check_kind_policy.py's PLANES manifest
    has said bus/event/beat since T177. Shipping a required plane argument that accepts only
    one spelling would fork the plane vocabulary in the very commit that de-forks `ask`.
    Normalize at the door (the house rule for open boundaries): accept both, forever."""
    short = K.resolve("note", "salient", plane="bus")
    long = K.resolve("note", "salient", plane="bus_kind")
    assert (short.classified, short.value) == (long.classified, long.value)


def test_p12_an_unknown_plane_is_unclassified_not_an_exception():
    v = K.resolve("note", "salient", plane="no_such_plane")
    assert v.classified is False and v.value is None
    assert v.why, "an unclassified verdict without a reason is unrepresentable"


def test_p13_the_collision_stays_visible_after_the_ruling():
    """The ruling makes the collision unaskable, NOT invisible. plane_collisions() must still
    report note and decision -- the registry's census is how the next seat learns the planes
    overlap at all, and a ruling that erased the evidence would be a worse instrument."""
    collisions = K.plane_collisions()
    assert "note" in collisions and len(collisions["note"]) == 3
    assert "decision" in collisions, "the collision nobody had named stays on the record"


def test_p14_the_checker_manifest_knows_the_renamed_sets():
    """K-D in check_kind_policy FAILS a *KINDS set with no declared plane. The renames must
    land in that manifest in the SAME commit, or the guard that exists to catch exactly this
    fires on my own work -- which is the bedside test doing its job, twice before."""
    src = open(os.path.join(ROOT, "scripts", "checkers", "check_kind_policy.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    manifest: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "PLANES" for t in node.targets):
            manifest = ast.literal_eval(node.value)
            break
    assert manifest, "PLANES manifest not found -- K-D cannot run without it"
    for name in ("NEVER_DROP_WHEN_STALE", "AUTO_REDRIVE_KINDS"):
        assert name in manifest, f"{name} must declare its plane (K-D)"
    assert "STALE_ASK_KINDS" not in manifest, "the retired name must leave the manifest too"
