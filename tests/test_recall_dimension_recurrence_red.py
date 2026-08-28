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

def test_p7_reports_whether_the_fine_site_added_anything_over_the_coarse():
    """Marginal REACH -- and it is NOT marginal usefulness. The distinction is load-bearing.

    If a coarse site definition already crossed the threshold, the fine one firing on the same
    stream reached nothing new. The dimension must be able to SAY that, or a shelf built on it
    accumulates site definitions that duplicate coarser ones.

    WHAT THIS PIN DOES NOT CLAIM, per Heimdall 2026-08-27 and
    `replay_is_not_counterfactual_when_retrieval_changes_trace` (sol): it does NOT measure
    whether the finer lesson was USEFUL, and it must never be read that way. TAGE's usefulness
    counter can ask "was the finer context necessary" because a branch predictor observes an
    EXOGENOUS stream -- predicting does not change what executes next. RECALL IS AN INTERVENTION
    ON ITS OWN STREAM: surfacing a lesson changes the next tool call, so a trail recorded after a
    fire cannot contain the counterfactual "what would have happened had only the coarse site
    fired." Marginal REACH is a pure function of the observed stream and is obtainable. Marginal
    USEFULNESS is a counterfactual and is not. Do not let a later slice quietly promote one to
    the other.
    """
    marginal = _resolve("marginal_over")
    site_tool = _resolve("SITE_TOOL")
    site_tool_flags = _resolve("SITE_TOOL_FLAGS")

    # both definitions cross: the fine one added nothing
    same = [_ev("x", i, tool="commit", flags=("--no-verify",)) for i in range(1, 4)]
    verdict = marginal(same, fine=site_tool_flags, coarse=site_tool, window=100, now=4, threshold=3)
    assert verdict["fine_added"] is False, (
        f"when the coarse site already crossed, the fine site earns nothing: {verdict}")

    # only the fine definition isolates a crossing the coarse one buries
    mixed = ([_ev("x", i, tool="commit", flags=("--no-verify",)) for i in range(1, 4)]
             + [_ev("x", i, tool="commit", flags=()) for i in range(4, 30)])
    verdict2 = marginal(mixed, fine=site_tool_flags, coarse=site_tool,
                        window=100, now=30, threshold=3)
    assert "fine_added" in verdict2 and "reason" in verdict2, verdict2
    assert verdict2["reason"], "a marginal verdict must state its ground"


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
