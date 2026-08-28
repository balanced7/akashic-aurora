"""RED pins -- the RECURRENCE dimension (Daniil's dimension #4).

PRE-REGISTRATION. Written and committed ALONE, before any implementation exists, per M3.
Every pin here MUST fail at commit time solely because `core.recall.dimensions.recurrence`
does not exist. If any pin passes before the module is written, the pin is broken.

WHAT THIS DIMENSION IS, in Daniil's words:
    "recall based on heuristic criteria, like if 3 loops of this toolcall occured this
     lesson might be applicable"
and, on why the site definition must be a parameter rather than a constant:
    "we can apply the branch prediction AT each toolcall or AT each repetition of x
     signatures or unique combinations and flags"

WHY THIS DIMENSION FIRST: it is mechanizable (a count over a trail we already record), the
data exists, and this session produced two live cases where a recurrence went undetected AT
THE MOMENT IT RECURRED -- `a_coverage_number_wearing_a_quality_label` (432.5h later) and
`recall_fires_where_commands_run_not_where_choices_are_made` (5.5 days later). Both were
noticed by a human afterwards. Nothing in the house saw either one happen.

SCOPE, and it is deliberately small: this module OBSERVES and COUNTS. It does not rank, does
not surface, does not write anywhere, and has no opinion about what should be recalled. It
produces evidence a shelf candidate can be built on. Any pin that would require it to decide
what a seat sees is out of scope and should be refused.

DECLARED SCOPE WIDENING, 2026-08-27, flagged by Heimdall at veto review rather than absorbed
silently: P12 requires this module to compute FREQUENCY as well as recurrence, which is more
than "observes and counts recurrence." It is forced rather than chosen -- Sunshine's condition
was episode/reset semantics DISTINGUISHING recurrence from frequency, and a distinction cannot
be proven without emitting both sides of it. The widening stops there: frequency is emitted as
an advisory retirement signal (`frequency_is_advisory`), never as a firing signal, per Navi's
finding that it routes to no moment. If a later slice wants frequency to fire anything, that is
a new dimension with its own gate, not an extension of this one.
"""

import importlib
import inspect
import ast

import pytest


MODULE = "core.recall.dimensions.recurrence"


def _mod():
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:  # pragma: no cover - the RED state
        pytest.fail(f"{MODULE} does not exist yet (expected while the gate is RED): {exc}")


def _resolve(name):
    mod = _mod()
    if not hasattr(mod, name):
        pytest.fail(f"{MODULE}.{name} is missing")
    return getattr(mod, name)


def _ev(sig, at, *, tool="run", args=(), flags=(), ok=True):
    """One observed action. `at` is a caller-supplied integer tick -- never a clock read."""
    return dict(signature=sig, at=at, tool=tool, args=tuple(args), flags=tuple(flags), ok=ok)


# ---------------------------------------------------------------------------
# Pin 1 -- counting actually counts. A constant-returning stub must fail.
# ---------------------------------------------------------------------------

def test_p1_distinct_recurrence_counts_are_distinguishable():
    count = _resolve("recurrence_counts")
    stream = [_ev("A", 1), _ev("A", 2), _ev("A", 3), _ev("B", 4)]
    got = count(stream, window=100)
    assert got["A"] == 3, got
    assert got["B"] == 1, got
    # the negative: a stub returning the same number for every signature fails here
    assert got["A"] != got["B"], "counts must discriminate between signatures"


# ---------------------------------------------------------------------------
# Pin 2 -- the window is bounded, explicit, and RIDES THE RESULT.
# ---------------------------------------------------------------------------

def test_p2_window_bounds_the_count_and_is_reported():
    count = _resolve("recurrence_counts")
    stream = [_ev("A", 1), _ev("A", 2), _ev("A", 50), _ev("A", 51)]
    narrow = count(stream, window=5, now=52)
    wide = count(stream, window=100, now=52)
    assert narrow["A"] == 2, f"window=5 at now=52 must see only ticks 50,51 -- got {narrow}"
    assert wide["A"] == 4, wide
    assert narrow["A"] != wide["A"], "an unbounded stub that ignores `window` fails here"

    report = _resolve("observe")(stream, window=5, now=52, threshold=2)
    for row in report["rows"]:
        assert row["window"] == 5, f"every row must carry the window that produced it: {row}"


# ---------------------------------------------------------------------------
# Pin 3 -- no naked counters. A count without its denominator is refused.
# ---------------------------------------------------------------------------

def test_p3_every_emission_carries_its_denominator():
    observe = _resolve("observe")
    stream = [_ev("A", 1), _ev("A", 2), _ev("A", 3), _ev("B", 4), _ev("C", 5)]
    report = observe(stream, window=100, now=6, threshold=3)

    assert report["signatures_observed"] == 3, report
    assert report["events_observed"] == 5, report
    for row in report["rows"]:
        assert "count" in row and "signatures_observed" in row, (
            f"a count rendered without the population it was drawn from is a naked counter: {row}")
        assert row["signatures_observed"] == 3, row


# ---------------------------------------------------------------------------
# Pin 4 -- SILENCE IS A ROW. Below-threshold is reported, not absent.
# ---------------------------------------------------------------------------

def test_p4_below_threshold_signatures_are_explicit_rows_not_absence():
    observe = _resolve("observe")
    stream = [_ev("A", 1), _ev("A", 2), _ev("A", 3), _ev("B", 4), _ev("B", 5)]
    report = observe(stream, window=100, now=6, threshold=3)

    by_sig = {r["signature"]: r for r in report["rows"]}
    assert "A" in by_sig and "B" in by_sig, (
        "a signature observed below threshold must still produce a ROW -- dropping it makes "
        "'not enough evidence' indistinguishable from 'never seen', which is the exact failure "
        "this house keeps paying for")
    assert by_sig["A"]["crossed"] is True, by_sig["A"]
    assert by_sig["B"]["crossed"] is False, by_sig["B"]
    assert by_sig["B"]["count"] == 2, by_sig["B"]
    # the negative: a stub that returns only crossed rows fails
    assert any(r["crossed"] is False for r in report["rows"]), (
        "at least one below-threshold row must survive into the report")


# ---------------------------------------------------------------------------
# Pin 5 -- the SITE DEFINITION is a parameter. This is the whole design.
# ---------------------------------------------------------------------------

def test_p5_site_definition_is_variable_not_hardcoded():
    """Daniil's load-bearing move: the site is not given to us, so it must be a variable.

    `git commit` and `git commit --no-verify` are ONE site under a coarse definition and TWO
    under a fine one. The dimension must count both ways on the same stream, because which
    definition predicts is an empirical question the shelf adjudicates -- not a constant.
    """
    observe = _resolve("observe")
    site_tool = _resolve("SITE_TOOL")
    site_tool_flags = _resolve("SITE_TOOL_FLAGS")

    stream = [
        _ev("x", 1, tool="commit", flags=()),
        _ev("x", 2, tool="commit", flags=()),
        _ev("x", 3, tool="commit", flags=("--no-verify",)),
    ]

    coarse = observe(stream, window=100, now=4, threshold=3, site=site_tool)
    fine = observe(stream, window=100, now=4, threshold=3, site=site_tool_flags)

    assert coarse["signatures_observed"] == 1, (
        f"under a tool-only site definition all three are one site -- got {coarse}")
    assert fine["signatures_observed"] == 2, (
        f"under a tool+flags definition --no-verify is its own site -- got {fine}")

    coarse_row = coarse["rows"][0]
    assert coarse_row["count"] == 3 and coarse_row["crossed"] is True, coarse_row
    assert all(r["crossed"] is False for r in fine["rows"]), (
        "splitting the site must split the evidence -- neither fine site reaches 3")


# ---------------------------------------------------------------------------
# Pin 6 -- threshold is a parameter, not the literal 3 from the example.
# ---------------------------------------------------------------------------

def test_p6_threshold_is_not_hardcoded_to_the_example_value():
    observe = _resolve("observe")
    stream = [_ev("A", i) for i in range(1, 6)]      # five occurrences
    for t, expect in ((2, True), (5, True), (6, False)):
        report = observe(stream, window=100, now=6, threshold=t)
        row = report["rows"][0]
        assert row["crossed"] is expect, f"threshold={t}: expected crossed={expect}, got {row}"
        assert report["threshold"] == t, report


# ---------------------------------------------------------------------------
# Pin 7 -- MARGINAL contribution is expressible, per the TAGE usefulness rule.
# ---------------------------------------------------------------------------

def test_p7_refuses_to_adjudicate_marginal_value_and_reports_containment_instead():
    """THIS PIN IS AN INVERSION, and the history matters more than the assertion.

    It was originally written to assert that the dimension could report whether a FINER site
    definition "added anything" over a coarser one -- borrowing TAGE's usefulness rule, which
    credits an entry only when it was right AND the alternative would have been wrong.

    Sunshine refuted it at the RED gate, before any implementation existed, and the refutation
    is arithmetic: under nested site definitions the counts are MONOTONE BY CONSTRUCTION. A fine
    site is a subset partition of its coarse parent, so its count can never exceed the parent's
    and it can never cross a threshold the parent did not already cross. The original pin's
    positive scenario was therefore IMPOSSIBLE, and because its assertions only required a key
    and a non-empty reason, a constant `fine_added=False` stub would have greened it. A vacuous
    pin wrapped around an unreachable narrative.

    So the finding, which is what the pin now encodes:

      A FINER SITE DEFINITION DOES NOT ADD REACH. IT ADDS DISCRIMINATION. Its value is firing
      only where appropriate where the coarse site fires everywhere -- which is a statement about
      OUTCOMES, not counts. And outcomes bring back the counterfactual: recall is an intervention
      on its own stream, so a trail cannot contain "what would have happened had only the coarse
      site fired" (Heimdall, and `replay_is_not_counterfactual_when_retrieval_changes_trace`).

    Counts cannot adjudicate marginal usefulness, and between NESTED sites they cannot adjudicate
    marginal reach either. The honest module therefore reports the containment relationship it can
    observe and REFUSES to emit a value verdict it cannot ground.
    """
    contains = _resolve("containment")
    site_tool = _resolve("SITE_TOOL")
    site_tool_flags = _resolve("SITE_TOOL_FLAGS")

    mixed = ([_ev("x", i, tool="commit", flags=("--no-verify",)) for i in range(1, 4)]
             + [_ev("x", i, tool="commit", flags=()) for i in range(4, 30)])
    rel = contains(mixed, fine=site_tool_flags, coarse=site_tool, window=100, now=30)

    # the observable, monotone fact -- and a stub returning constants fails both halves
    assert rel["coarse_count"] == 29, rel
    assert sorted(rel["fine_counts"]) == [3, 26], rel
    assert rel["monotone"] is True, "fine counts must never exceed the coarse count"
    assert sum(rel["fine_counts"]) == rel["coarse_count"], (
        "a partition must account for every observed event")

    # the refusal, stated as a value rather than an omission
    assert rel["marginal_value"] == "UNOBTAINABLE_FROM_COUNTS", (
        f"the module must REFUSE the verdict it cannot ground, loudly and by name: {rel}")
    assert rel["reason"], "the refusal must state its ground"


def test_p7b_module_exposes_no_usefulness_or_promotion_surface():
    """The prohibition, structural rather than behavioural: there must be no function here that
    a later slice can quietly call to get the verdict pin 7 just refused."""
    mod = _mod()
    forbidden = {"marginal_over", "fine_added", "usefulness", "usefulness_factor",
                 "promote", "promotion", "is_useful", "value_of"}
    present = sorted(n for n in dir(mod) if n in forbidden)
    assert not present, (
        f"these names offer a verdict this dimension cannot ground from counts: {present}")


# ---------------------------------------------------------------------------
# Pin 8 -- deterministic. No clock, no randomness, replayable.
# ---------------------------------------------------------------------------

def test_p8_no_wallclock_or_randomness_in_module_source():
    mod = _mod()
    tree = ast.parse(inspect.getsource(mod))
    forbidden_mods = {"random", "secrets", "datetime", "uuid"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] not in forbidden_mods, (
                    f"{a.name} makes replay non-deterministic; `now` is a caller-supplied tick")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in forbidden_mods, f"from {node.module} breaks replay determinism"
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert not (node.value.id == "time" and node.attr in {"time", "time_ns", "monotonic"}), (
                "reading the clock inside the dimension makes the same stream score differently "
                "on replay")


def test_p8b_same_stream_scores_identically_twice():
    observe = _resolve("observe")
    stream = [_ev("A", 1), _ev("A", 2), _ev("B", 3), _ev("A", 4)]
    a = observe(stream, window=100, now=5, threshold=2)
    b = observe(stream, window=100, now=5, threshold=2)
    assert a == b, "replay must be exact"


# ---------------------------------------------------------------------------
# Pin 9 -- the dimension CANNOT REACH a canonical writer. Structural, not behavioural.
# ---------------------------------------------------------------------------

def test_p9_module_imports_cannot_reach_a_canonical_writer():
    """Same property that made T370 Slice 0 acceptable, and it is stronger than a behaviour
    test: the module must be UNABLE to write, not merely observed not writing."""
    mod = _mod()
    tree = ast.parse(inspect.getsource(mod))
    allowed_roots = {"__future__", "dataclasses", "typing", "collections", "itertools", "math"}
    seen = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            seen += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                seen.append(node.module.split(".")[0])
    offenders = [s for s in seen if s not in allowed_roots]
    assert not offenders, (
        f"the recurrence dimension must be a pure function over a supplied stream; these imports "
        f"give it reach it must not have: {offenders}")


# ---------------------------------------------------------------------------
# Pin 10 -- an empty stream is UNEVALUATED, never a healthy zero.
# ---------------------------------------------------------------------------

def test_p10_empty_stream_is_unevaluated_not_a_clean_report():
    observe = _resolve("observe")
    report = observe([], window=100, now=1, threshold=3)
    assert report["state"] == "UNEVALUATED", (
        f"no data must read as UNEVALUATED, not as a clean zero -- a blind dimension that renders "
        f"as a healthy one is how an absence gets read as normal: {report}")
    assert report["rows"] == [], report

    live = observe([_ev("A", 1)], window=100, now=2, threshold=3)
    assert live["state"] == "OK", live
    assert live["state"] != report["state"], "the two states must actually differ"


# ===========================================================================
# PINS 11-14 -- required by Sunshine before implementation is approved.
# Added 2026-08-27 after his conditional veto. His four conditions, verbatim:
#   "subject isolation, episode/reset/progress semantics distinguishing
#    recurrence from frequency, the arm/site contract hash riding every result,
#    and bounded max_rows/refusal before I approve implementation."
# ===========================================================================


def _ev2(sig, at, *, subject="claude", episode="ep-1", tool="run", flags=()):
    return dict(signature=sig, at=at, subject=subject, episode=episode,
                tool=tool, args=(), flags=tuple(flags), ok=True)


# ---------------------------------------------------------------------------
# Pin 11 -- SUBJECT ISOLATION. Rill paid for this one with his fracture:
# attribution is not verification, and a record about seat Y must never be
# readable as a fact about seat X.
# ---------------------------------------------------------------------------

def test_p11_counts_do_not_cross_subjects():
    observe = _resolve("observe")
    stream = [_ev2("A", 1, subject="claude"), _ev2("A", 2, subject="claude"),
              _ev2("A", 3, subject="kimi")]

    mine = observe(stream, window=100, now=4, threshold=3, subject="claude")
    assert mine["rows"][0]["count"] == 2, (
        f"three occurrences across two seats must NOT sum into one seat count: {mine}")
    assert mine["rows"][0]["crossed"] is False, (
        "borrowing another seat occurrences to cross a threshold is the exact failure the "
        "subject law exists to prevent")

    for row in mine["rows"]:
        assert row["subject"] == "claude", f"every row must name its subject: {row}"

    # the negative: a subject-blind implementation sums to 3 and crosses
    blind = observe(stream, window=100, now=4, threshold=3, subject=None)
    assert blind["rows"][0]["count"] == 3, blind
    assert blind["state"] == "SUBJECT_UNSCOPED", (
        "an unscoped read is legal for diagnostics but must SAY SO by name, so a cross-subject "
        "number can never be mistaken for the seat own count")


# ---------------------------------------------------------------------------
# Pin 12 -- RECURRENCE IS NOT FREQUENCY, and one fixture proves it.
# This pin exists because two seats disagreed about whether they are one
# dimension: Navi called frequency a maintenance signal that should retire
# lessons rather than fire recall; Heimdall filed it as mechanically
# observable alongside loop-count. The module must be able to TELL THEM APART,
# which makes the disagreement decidable instead of rhetorical.
# ---------------------------------------------------------------------------

def test_p12_recurrence_resets_at_episode_boundary_frequency_does_not():
    observe = _resolve("observe")

    # THE SAME three occurrences, arranged two ways
    one_episode = [_ev2("A", i, episode="ep-1") for i in (1, 2, 3)]
    three_episodes = [_ev2("A", 1, episode="ep-1"),
                      _ev2("A", 2, episode="ep-2"),
                      _ev2("A", 3, episode="ep-3")]

    a = observe(one_episode, window=100, now=4, threshold=3)
    b = observe(three_episodes, window=100, now=4, threshold=3)
    ra, rb = a["rows"][0], b["rows"][0]

    # RECURRENCE is a position within one run progress -- it RESETS
    assert ra["count"] == 3 and ra["crossed"] is True, ra
    assert rb["count"] == 1, (
        f"recurrence must reset at the episode boundary -- the third loop of this toolcall is a "
        f"position in THIS run, not a lifetime tally: {rb}")
    assert rb["crossed"] is False, rb

    # FREQUENCY is a rate ACROSS runs -- it does not reset
    assert ra["frequency"] == 3 and rb["frequency"] == 3, (
        f"frequency must be identical for both arrangements -- it counts occurrences, not "
        f"positions: {ra} vs {rb}")

    # the discriminating assertion: a stub computing one number for both fails
    assert rb["count"] != rb["frequency"], (
        "recurrence and frequency must be SEPARATELY COMPUTED, not aliases -- if they cannot "
        "disagree on this fixture they are one dimension wearing two names")

    # and frequency must declare that it is not a firing signal
    assert b["frequency_is_advisory"] is True, (
        "frequency answers whether something is chronically recurring, which is a RETIREMENT "
        "question, not a fire-now question; the module must say so rather than let a caller "
        "assume symmetry with recurrence")


# ---------------------------------------------------------------------------
# Pin 13 -- the ARM/SITE CONTRACT HASH rides every result.
# Sunshine verified in source that evaluation_id does not hash arm identity or
# configuration, so two experiments differing ONLY in site definition collide
# and the second returns the first envelope. Nothing here may be identified by
# the words champion/challenger alone.
# ---------------------------------------------------------------------------

def test_p13_every_result_carries_its_arm_contract_hash():
    observe = _resolve("observe")
    arm_hash = _resolve("arm_contract_hash")
    site_tool = _resolve("SITE_TOOL")
    site_tool_flags = _resolve("SITE_TOOL_FLAGS")

    stream = [_ev2("x", i, tool="commit") for i in (1, 2, 3)]
    coarse = observe(stream, window=100, now=4, threshold=3, site=site_tool)
    fine = observe(stream, window=100, now=4, threshold=3, site=site_tool_flags)

    assert coarse["arm_hash"] and fine["arm_hash"], "every result must carry an arm hash"
    assert coarse["arm_hash"] != fine["arm_hash"], (
        "two runs differing ONLY in site definition MUST NOT share an arm hash -- this is the "
        "collision Sunshine found in the shelf evaluation_id, reproduced one layer down")

    # configuration is part of identity, not decoration
    w5 = observe(stream, window=5, now=4, threshold=3, site=site_tool)
    t2 = observe(stream, window=100, now=4, threshold=2, site=site_tool)
    assert w5["arm_hash"] != coarse["arm_hash"], "the window is part of the arm identity"
    assert t2["arm_hash"] != coarse["arm_hash"], "the threshold is part of the arm identity"

    # and the hash must be a pure function of the declared contract, not the data
    assert arm_hash(site=site_tool, window=100, threshold=3) == coarse["arm_hash"], (
        "the arm hash must be derivable from the contract ALONE, so a judgment can target a "
        "persisted arm identity without replaying the stream")


# ---------------------------------------------------------------------------
# Pin 14 -- BOUNDED OUTPUT, with refusal by name rather than silent truncation.
# Daniil scale invariant as Sunshine reads it: capability may grow
# combinatorially, activation cost and attention must stay bounded. A dimension
# returning an unbounded row set spends every other dimension budget.
# ---------------------------------------------------------------------------

def test_p14_row_output_is_bounded_and_truncation_is_declared():
    observe = _resolve("observe")
    stream = [_ev2(f"sig-{i}", i) for i in range(1, 51)]     # 50 distinct signatures

    got = observe(stream, window=100, now=51, threshold=1, max_rows=10)
    assert len(got["rows"]) == 10, f"max_rows must actually bound the output: {len(got)}"
    assert got["truncated"] is True, got
    assert got["signatures_observed"] == 50, (
        "the DENOMINATOR must survive truncation -- reporting 10 rows without saying 10 of 50 is "
        "how a bounded view gets read as a complete one")
    assert got["rows_omitted"] == 40, got

    small = observe(stream[:5], window=100, now=6, threshold=1, max_rows=10)
    assert small["truncated"] is False, small
    assert small["rows_omitted"] == 0, small
