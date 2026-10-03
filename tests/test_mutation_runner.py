"""RED pins: W128 + W236 -- the reusable mutation runner, with every NULL species it must name.

WHY THIS EXISTS. docs/method-baseline-2026-07.md asks EVERY slice to mutation-test its pins.
There is no runner, so every seat hand-rolls the same patch-run-restore loop, and the
hand-roll has now produced SIX false results across two sessions -- every one of them a
harness failure rather than a subject failure, and at least two of them a WRONG CONCLUSION
rather than a retry.

THREE DISTINCT WAYS A HARNESS CAN SAY "SURVIVED" AND BE WRONG. They look identical from the
outside, which is the whole problem, and each wish names a different one:

  1. NULL-APPLY (W236)    -- the patch never reached the file. sed ate the backslash escapes;
                             the anchor carried a comment or a newline and matched nothing;
                             the mutant produced a SyntaxError, which pytest reports as a
                             COLLECTION error rather than FAILED lines, so a FAILED-line
                             parser scores it as survived.
  2. NULL-SEMANTIC (W128) -- the patch landed and changed nothing observable. T159's M1
                             survived because EXCEPTIONS is a subset of unreachable, so the
                             clause removes zero modules today. W128's closing line: "a report
                             that cannot say 'this mutation changed nothing' will eventually be
                             used to delete a good pin."
  3. BLIND DETECTOR       -- NOT in either wish, found 2026-10-02 building this. The mutation
                             landed, parsed, and genuinely broke tests, and the harness still
                             said SURVIVED because it scored the run by matching output text
                             (`" failed" not in out`). Under `-q --no-header` pytest emits no
                             lowercase counts line at all: a clean run is ~80 characters of
                             dots and a failing run ends in UPPERCASE FAILED lines, so the
                             detector returned the same answer in both directions. Six of six
                             mutations reported SURVIVED against pins that were in fact fine.

A runner built to W128 exactly as written reports all of species 1 as SURVIVED. A runner built
to W128+W236 still reports species 3 as SURVIVED. All three are pinned here.

THE VERDICT VOCABULARY, and SURVIVED is deliberately the narrowest one:
    CAUGHT           suite went red and the expected pin fired
    CAUGHT-BY-OTHER  suite went red but a different pin fired (the expectation is wrong, or
                     the mutation is broader than intended) -- never silently counted as CAUGHT
    SURVIVED         the mutant landed, parses, and the suite stayed green
    NULL-APPLY       the mutant never landed; says nothing about the pins
    NULL-SEMANTIC    the mutant landed but a declared probe proves it changed nothing

SELF-CALIBRATION, TWO-SIDED, BEFORE ANY VERDICT IS BELIEVED. A harness that cannot fail loudly
is the same defect class as a pin that cannot fail.
    CANARY       an injected guaranteed-failure must be reported RED. If it is not, the
                 detector is blind (species 3) and every SURVIVED this run would be a lie.
    NULL CONTROL an injected provable no-op must be reported GREEN. If it is not, the suite is
                 non-deterministic and every CAUGHT this run would be a coin flip.
Either calibration failing means the run REFUSES to report verdicts at all.

Run::

    py -m pytest tests/test_mutation_runner.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.mutate import run_spec  # noqa: E402


# --------------------------------------------------------------------------- a toy subject
SUBJECT = '''\
"""A tiny subject with one guarded branch and one unguarded one."""


def classify(n):
    if n < 0:
        return "negative"
    return "nonnegative"


def unguarded(n):
    """Nothing asserts on this; a mutation here must read as SURVIVED, not CAUGHT."""
    return n * 2
'''

TESTS = '''\
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from subject import classify


def test_negative_is_negative():
    assert classify(-1) == "negative"


def test_zero_is_nonnegative():
    assert classify(0) == "nonnegative"
'''


@pytest.fixture
def bench(tmp_path):
    """A self-contained repo: one subject module, one test file that guards half of it."""
    (tmp_path / "subject.py").write_text(SUBJECT, encoding="utf-8")
    (tmp_path / "test_subject.py").write_text(TESTS, encoding="utf-8")
    return tmp_path


def _spec(**mut):
    mut.setdefault("label", mut.get("file", "m"))
    return {"mutations": [mut]}


def _one(bench, **mut):
    res = run_spec(_spec(**mut), tests="test_subject.py", repo=bench)
    assert res["calibration"]["ok"] is True, res["calibration"]
    return res["results"][0]


# --------------------------------------------------------------------------- the happy path
def test_a_mutation_a_pin_guards_is_CAUGHT(bench):
    r = _one(bench, file="subject.py", anchor='return "negative"',
             replacement='return "nonnegative"', expect="test_negative_is_negative")
    assert r["verdict"] == "CAUGHT", r


def test_the_wrong_pin_firing_is_not_quietly_counted_as_CAUGHT(bench):
    """A mutation that reddens the suite via a DIFFERENT pin than expected means either the
    expectation or the mutation is wrong. Folding it into CAUGHT hides both."""
    r = _one(bench, file="subject.py", anchor='return "negative"',
             replacement='return "nonnegative"', expect="test_zero_is_nonnegative")
    assert r["verdict"] == "CAUGHT-BY-OTHER", r


def test_an_unguarded_mutation_is_SURVIVED(bench):
    r = _one(bench, file="subject.py", anchor="return n * 2", replacement="return n * 3")
    assert r["verdict"] == "SURVIVED", r


# --------------------------------------------------------------------------- W236: NULL-APPLY
def test_a_missing_anchor_is_NULL_APPLY_not_SURVIVED(bench):
    """W236's core ask. sed eating an escape, or an anchor carrying a comment, produces a
    mutation that never ran -- which says NOTHING about the pins and must never be scored
    as though the pins were blind."""
    r = _one(bench, file="subject.py", anchor="this text appears nowhere",
             replacement="irrelevant")
    assert r["verdict"] == "NULL-APPLY", r
    assert "anchor" in r["detail"].lower(), r["detail"]


def test_an_ambiguous_anchor_is_NULL_APPLY(bench):
    """Two matches means the runner cannot know which site it mutated.

    The replacement must DIFFER from the anchor. The first version used
    replacement == anchor, so removing the ambiguity check entirely still produced
    NULL-APPLY via the identical-replacement check -- the pin passed for the wrong reason and
    the runner's own self-mutation caught it ('stop refusing an ambiguous anchor' SURVIVED).
    """
    r = _one(bench, file="subject.py", anchor="return", replacement="return  ")
    assert r["verdict"] == "NULL-APPLY", r
    assert "ambiguous" in r["detail"].lower(), (
        "refused for some reason other than ambiguity, so this does not pin the count "
        "check: %r" % r["detail"])


def test_a_mutant_that_does_not_parse_is_NULL_APPLY_not_SURVIVED(bench):
    """W236 names this one specifically: a SyntaxError yields a pytest COLLECTION error, not
    FAILED lines, so a FAILED-line parser scores it as survived."""
    r = _one(bench, file="subject.py", anchor='return "negative"',
             replacement='return "negative" ((((')
    assert r["verdict"] == "NULL-APPLY", r
    assert "parse" in r["detail"].lower() or "syntax" in r["detail"].lower(), r["detail"]


def test_a_replacement_identical_to_the_anchor_is_NULL_APPLY(bench):
    """The file is byte-identical afterwards, so nothing was tested."""
    r = _one(bench, file="subject.py", anchor="return n * 2", replacement="return n * 2")
    assert r["verdict"] == "NULL-APPLY", r


# --------------------------------------------------------------------- W128: NULL-SEMANTIC
def test_a_declared_probe_that_does_not_move_is_NULL_SEMANTIC(bench):
    """W128's species: the mutant LANDED and changed nothing observable. The runner cannot
    infer semantic nullity -- that is undecidable -- so the spec DECLARES a probe whose value
    must move if the mutation is live, and the runner checks it."""
    r = _one(bench, file="subject.py", anchor="return n * 2", replacement="return n*2",
             probe="__import__('subject').unguarded(21)")
    assert r["verdict"] == "NULL-SEMANTIC", r


def test_SURVIVED_always_declares_that_semantic_nullity_was_not_ruled_out(bench):
    """W128's closing line is the requirement: a report that cannot say 'this changed nothing'
    will eventually be used to delete a good pin. With no probe the runner CANNOT say it, so
    it must say THAT, every time, rather than letting SURVIVED read as 'the pin is blind'."""
    r = _one(bench, file="subject.py", anchor="return n * 2", replacement="return n * 3")
    assert r["verdict"] == "SURVIVED"
    assert r.get("semantic_null_ruled_out") is False, r
    assert "probe" in r["detail"].lower(), r["detail"]


def test_a_probe_that_moves_leaves_the_verdict_alone(bench):
    r = _one(bench, file="subject.py", anchor="return n * 2", replacement="return n * 3",
             probe="__import__('subject').unguarded(21)")
    assert r["verdict"] == "SURVIVED", r
    assert r.get("semantic_null_ruled_out") is True, r


# ------------------------------------------------------------------ today: the blind detector
def test_the_verdict_comes_from_the_exit_code_not_from_matching_output(bench, monkeypatch):
    """THE 2026-10-02 SPECIES, pinned by DRIVING THE DETECTOR rather than hoping the real
    runner emits the right shape.

    The first version of this pin ran the toy bench and asserted CAUGHT. That is not a pin:
    this pytest DOES print a lowercase counts line on failure, so a text-scoring runner reads
    it correctly here and the pin passes anyway. The runner's own self-mutation proved it --
    'score by output text instead of the exit code' SURVIVED, the single most important
    mutation in the set, against the pin written specifically to catch it.

    So substitute a detector that returns the shape that actually broke things: a NONZERO
    exit code with output containing no failure vocabulary at all. Any runner scoring on text
    calls this green.
    """
    import scripts.mutate as M
    calls = {"n": 0}
    real = M._run_tests

    def fake(tests, repo, timeout=600):
        calls["n"] += 1
        if "canary" in str(tests):
            return 1, "canary went red"          # calibration must still pass
        if calls["n"] <= 3:
            return 0, "..... [100%]"             # baseline + null control: genuinely green
        # the mutation run: RED, with innocuous output and no counts line
        return 1, "..F.. [100%]"

    monkeypatch.setattr(M, "_run_tests", fake)
    res = M.run_spec(_spec(file="subject.py", anchor="return n * 2", replacement="return n * 3"),
                     tests="test_subject.py", repo=bench)
    assert res["calibration"]["ok"] is True, res["calibration"]
    r = res["results"][0]
    assert r["verdict"] == "CAUGHT", (
        "a nonzero exit code was scored green -- the runner is matching output text instead "
        "of reading the exit code: %r" % (r,))
    assert r["returncode"] == 1, r
    assert real is not M._run_tests  # sanity: the substitution was live


def test_the_runner_refuses_when_its_canary_is_not_caught(bench, monkeypatch):
    """Two-sided calibration, side one. If an injected guaranteed-failure does not read as
    RED, the detector is blind and every SURVIVED this run would be a lie. Refuse, loudly,
    rather than emit verdicts nobody should trust."""
    import scripts.mutate as M
    monkeypatch.setattr(M, "_run_tests", lambda *a, **k: (0, "everything is fine"))
    res = M.run_spec(_spec(file="subject.py", anchor="return n * 2", replacement="return n * 3"),
                     tests="test_subject.py", repo=bench)
    assert res["calibration"]["ok"] is False, res["calibration"]
    assert not res["results"], "verdicts were reported despite a blind detector"
    assert "canary" in json.dumps(res["calibration"]).lower()


def test_the_runner_refuses_when_the_null_control_reads_as_red(bench, monkeypatch):
    """Side two. If a provable no-op reddens the suite, the suite is non-deterministic and
    every CAUGHT this run is a coin flip."""
    import scripts.mutate as M
    monkeypatch.setattr(M, "_run_tests", lambda *a, **k: (1, "FAILED something"))
    res = M.run_spec(_spec(file="subject.py", anchor="return n * 2", replacement="return n * 3"),
                     tests="test_subject.py", repo=bench)
    assert res["calibration"]["ok"] is False, res["calibration"]
    assert not res["results"]


def test_a_red_baseline_refuses_before_anything_is_mutated(bench):
    """Mutating a tree that is already red cannot produce a readable verdict.

    Assert on the REASON, not merely that it refused. The first version checked
    `"baseline" in json.dumps(calibration)` -- but the report always carries a "baseline"
    key, so the assertion was true whichever check did the refusing. With the baseline check
    removed the NULL CONTROL refused instead (the target is red, so a no-op stays red) and
    the pin still passed. The runner's own self-mutation caught it.
    """
    (bench / "test_subject.py").write_text(
        TESTS + "\n\ndef test_already_broken():\n    assert False\n", encoding="utf-8")
    res = run_spec(_spec(file="subject.py", anchor="return n * 2", replacement="return n * 3"),
                   tests="test_subject.py", repo=bench)
    cal = res["calibration"]
    assert cal["ok"] is False, cal
    assert cal["baseline"]["green"] is False, cal
    assert "baseline" in (cal.get("why") or "").lower(), (
        "refused, but not FOR the baseline -- the baseline check is not what is pinned "
        "here: %r" % cal.get("why"))
    assert cal["canary"] is None and cal["null_control"] is None, (
        "calibration continued past a red baseline instead of refusing immediately: %r" % cal)


# --------------------------------------------------------------------------- hygiene
def test_every_file_is_restored_byte_for_byte(bench):
    """A mutation harness that leaks is worse than none: the next run measures the mutant."""
    before = (bench / "subject.py").read_bytes()
    run_spec({"mutations": [
        {"label": "a", "file": "subject.py", "anchor": 'return "negative"',
         "replacement": 'return "nonnegative"'},
        {"label": "b", "file": "subject.py", "anchor": "nope", "replacement": "x"},
        {"label": "c", "file": "subject.py", "anchor": "return n * 2",
         "replacement": "return n * 3 ((("},
    ]}, tests="test_subject.py", repo=bench)
    assert (bench / "subject.py").read_bytes() == before, "the subject was left mutated"


def test_the_mutated_line_is_reported(bench):
    """W236 asks for it explicitly: print the mutated line. Reading the diff is what caught
    the 'Fffd' no-op that started this whole class."""
    r = _one(bench, file="subject.py", anchor="return n * 2", replacement="return n * 3")
    assert "return n * 3" in (r.get("mutated_line") or ""), r


def test_results_are_structured_not_only_printed(bench):
    """A verdict a caller cannot read is a verdict that gets eyeballed."""
    r = _one(bench, file="subject.py", anchor="return n * 2", replacement="return n * 3")
    for k in ("label", "verdict", "detail", "file"):
        assert k in r, (k, r)
    json.dumps(r)
