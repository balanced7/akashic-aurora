"""Pins for `grade` after the AXI conversion: what an agent and a person see.

No model grader runs here: `--judge` is never set.

Run: uv run pytest tests/test_axi_grade.py -q
"""

import argparse

import pytest

from core.metaharness import cli


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, action, **kw):
    ns = argparse.Namespace(
        action=action, candidate="", against="", scenario=None, judge=False, scenarios_n=50, trials=3, delta=0.0,
        criterion="", person="", judge_call="", ref="", json=False,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cli.grade_main(ns)
    return code, capsys.readouterr().out


def test_power_is_numbers_without_hints(capsys):
    code, text = _run(capsys, "power", scenarios_n=40, trials=3, delta=0.15)
    assert code == 0
    assert "target_power: 0.8\nmin_detectable_change_points: 17.5" in text
    assert "change_points: 15\npower_for_change: 0.66" in text
    assert "help[" not in text


def test_label_then_agreement_counts_and_says_the_bar(capsys):
    code, text = _run(capsys, "label", criterion="quality", person="better", judge_call="worse")
    assert code == 0
    assert "n: 1" in text
    assert "calibrated: false" in text
    _, text = _run(capsys, "agreement")
    assert "graders[2]{criterion,n,agreement,calibrated}:" in text
    assert "needs: 10+ labels at 80%+ agreement" in text


def test_run_with_nothing_to_grade_says_zero_and_how_to_make_runs(capsys):
    code, text = _run(capsys, "run", candidate="baseline", scenario=["T1"])
    assert code == 0
    assert "graded: 0" in text
    assert "replay run --candidate baseline --scenario T1 --budget-usd 2" in text


def test_missing_arguments_are_usage_errors(capsys):
    code, text = _run(capsys, "compare", candidate="b")
    assert code == 2
    assert "code: USAGE" in text
    code, _ = _run(capsys, "label")
    assert code == 2


def test_compare_gives_the_verdict_and_the_review_hint(capsys):
    _, text = _run(capsys, "compare", candidate="b", against="baseline", scenario=["T1"])
    assert "pareto: no difference shown" in text
    assert "grade run --candidate b --scenario T1" in text  # no graded runs: grade first


def test_human_power_view(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "power", scenarios_n=40, trials=3)
    assert "Grading power" in text
    assert "17.5" in text
