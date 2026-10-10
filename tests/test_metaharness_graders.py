"""Graders and verdicts (meta-harness task 05).

Pinned here:
  * the paired statistics: deterministic cluster bootstrap, exact McNemar, power, Pareto;
  * code graders score 100% on fixtures: a known-good fix passes, no change fails, a cheat that
    rewrites its own oracle test is graded against the REAL oracle and flagged;
  * a known-better and a known-worse candidate are classified correctly, and a candidate does
    not beat its own rerun;
  * the pairwise judge counts a win only when both orders agree, and a model criterion stays
    out of the verdict until it is calibrated against person labels;
  * no grader file is writable once a scenario is sealed for a run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metaharness_fixtures import build_world, fake_candidate  # noqa: E402

from core.metaharness import corpus, graders, replay, stats  # noqa: E402

PYTEST = [sys.executable, "-m", "pytest"]


# --------------------------------------------------------------------------- stats
def test_bootstrap_is_deterministic_and_brackets_the_mean():
    d = [0.1, 0.2, 0.0, 0.3, 0.1, 0.2]
    m, lo, hi = stats.bootstrap_ci(d)
    assert stats.bootstrap_ci(d) == (m, lo, hi)
    assert lo <= m <= hi
    assert stats.verdict(m, lo, hi) == stats.BETTER
    assert stats.verdict(0.0, -0.1, 0.1) == stats.CANT_TELL
    assert stats.verdict(-0.2, -0.3, -0.1, higher_is_better=False) == stats.BETTER


def test_trials_are_averaged_inside_a_scenario_first():
    a = {"s1": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0], "s2": [1]}
    b = {"s1": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1], "s2": [1]}
    assert stats.paired_diffs(a, b) == {"s1": 1.0, "s2": 0.0}, "ten trials of one task are one scenario"


def test_mcnemar_exact():
    a = {f"s{i}": False for i in range(6)}
    b = {f"s{i}": True for i in range(6)}
    assert stats.mcnemar_exact(a, b) == {"b10": 0, "b01": 6, "p": pytest.approx(0.03125)}
    assert stats.mcnemar_exact(a, a)["p"] == 1.0


def test_power_grows_with_scenarios_and_the_detectable_change_shrinks():
    assert stats.power(200, 3, 0.1) > stats.power(50, 3, 0.1)
    assert stats.min_detectable(50, 3) > stats.min_detectable(200, 3)
    assert 0.10 <= stats.min_detectable(50, 3) <= 0.20, "the plan's estimate: 50 x 3 sees roughly 10-15 points"


def test_pareto_front():
    rows = {"a": {"pass": 0.8, "cost": 2.0}, "b": {"pass": 0.7, "cost": 1.0}, "c": {"pass": 0.6, "cost": 3.0}}
    assert sorted(stats.pareto(rows, {"pass": True, "cost": False})) == ["a", "b"]


# --------------------------------------------------------------------------- code graders on fixtures
@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    return build_world(tmp_path, n=6)


def _run_and_grade(name: str, mode: str, world, trials: int = 1, judge=None) -> list[dict]:
    repo, ids, agent = world
    fake_candidate(name, agent, mode)
    return [
        graders.grade_run(Path(r["run_dir"]), s, repo=repo, runner=PYTEST, judge=judge)
        for s in ids
        for r in replay.run(name, s, trials=trials, repo=repo)
    ]


def test_code_graders_are_exact_on_fixtures(world):
    good = _run_and_grade("good", "good", world)
    bad = _run_and_grade("bad", "bad", world)
    assert {g["functional"]["score"] for g in good} == {1.0}
    assert {g["functional"]["score"] for g in bad} == {0.0}
    assert {g["integrity"]["score"] for g in good + bad} == {1.0}
    # good touches every module while each scenario's reference touches one: full recall, low precision
    assert {g["correctness"]["recall"] for g in good} == {1.0}
    assert {g["correctness"]["score"] for g in bad} == {0.0}


def test_a_cheat_is_graded_against_the_real_oracle_and_flagged(world):
    cheat = _run_and_grade("cheat", "cheat", world)
    assert {g["functional"]["score"] for g in cheat} == {0.0}, "rewriting the test must not pass the oracle"
    assert all(g["integrity"]["score"] == 0.0 for g in cheat)
    assert any("edited oracle test" in f for g in cheat for f in g["integrity"]["flags"])


def test_better_and_worse_are_classified_and_a_rerun_shows_nothing(world):
    _, ids, _ = world
    _run_and_grade("bad", "bad", world)
    _run_and_grade("good", "good", world)
    _run_and_grade("good2", "good", world)
    _run_and_grade("verbose", "verbose", world)
    up = graders.compare("bad", "good", ids)
    assert up["criteria"]["functional"]["verdict"] == stats.BETTER
    assert up["criteria"]["functional"]["mcnemar"]["b01"] == len(ids)
    down = graders.compare("good", "bad", ids)
    assert down["criteria"]["functional"]["verdict"] == stats.WORSE
    assert down["pareto"] in ("dominated", "trade-off")
    assert graders.noise_check("good", "good2", ids)["ok"] is True
    costly = graders.compare("good", "verbose", ids)
    assert costly["criteria"]["tokens"]["verdict"] == stats.WORSE
    assert costly["criteria"]["functional"]["verdict"] == stats.CANT_TELL
    assert (graders.verdicts_dir() / "good__vs__verbose.json").exists()


def test_one_scenario_is_never_decisive(world):
    _, ids, _ = world
    _run_and_grade("bad", "bad", world)
    _run_and_grade("good", "good", world)
    v = graders.compare("bad", "good", ids[:1])
    assert v["criteria"]["functional"]["verdict"] == stats.CANT_TELL


# --------------------------------------------------------------------------- the model judge
def test_the_pairwise_judge_needs_both_orders_to_agree():
    always_first = lambda _p: "1"  # noqa: E731  # pure position bias
    assert graders.pairwise("t", "x", "y", "quality", always_first) == "tie"

    def prefers_longer(p: str) -> str:
        one = p.split("CHANGE 1:")[1].split("CHANGE 2:")[0]
        two = p.split("CHANGE 2:")[1].split("Which is better")[0]
        return "1" if len(one) > len(two) else "2"

    assert graders.pairwise("t", "a long careful change", "x", "quality", prefers_longer) == "1"


def test_model_criteria_stay_out_until_calibrated(world):
    _, ids, _ = world
    def judge(_p):
        return (
            '{"conventions": 5, "readable": 5, "minimal": 5, "no_hacks": 5, "verified": 4, "judgement": 4, "scope": 4}'
        )
    _run_and_grade(
        "bad",
        "bad",
        world,
        judge=lambda _p: (
            '{"conventions": 1, "readable": 1, "minimal": 1, "no_hacks": 1, "verified": 1, "judgement": 1, "scope": 1}'
        ),
    )
    _run_and_grade("good", "good", world, judge=judge)
    v = graders.compare("bad", "good", ids)
    assert v["criteria"]["quality"]["verdict"] == "uncalibrated"
    for _ in range(graders.CALIBRATION_MIN):
        graders.add_label("quality", "2", "2")
    assert graders.agreement("quality")["calibrated"] is True
    v = graders.compare("bad", "good", ids)
    assert v["criteria"]["quality"]["verdict"] == stats.BETTER
    assert v["criteria"]["quality"]["grader"] == "model"


def test_a_disagreeing_judge_never_calibrates():
    for i in range(20):
        graders.add_label("process", "1", "2" if i % 3 else "1")
    a = graders.agreement("process")
    assert a["n"] == 20
    assert a["calibrated"] is False


# --------------------------------------------------------------------------- out of reach
@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores file modes")
def test_no_grader_file_is_writable_once_sealed(world):
    _, ids, agent = world
    fake_candidate("good", agent, "good")
    replay.run("good", ids[0], trials=1, repo=world[0])  # run_one seals before launching
    d = corpus.scenario_dir(ids[0])
    for p in [*(d / "oracle").rglob("*"), *(d / "reference").rglob("*")]:
        with pytest.raises(PermissionError):
            p.open("a").close() if p.is_file() else (p / "new").write_text("x")
    corpus.unseal(ids[0])
    (d / "oracle" / "tests.txt").open("a").close()
