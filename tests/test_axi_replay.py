"""Pins for `replay` after the AXI conversion: what an agent and a person see.

Nothing here launches a harness: `replay run` is exercised with a stubbed runner.

Run: uv run pytest tests/test_axi_replay.py -q
"""

import argparse

import pytest

import agent_cli
from core.metaharness import cli, replay


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _ns(action, **kw):
    ns = argparse.Namespace(
        action=action, candidate="", scenario="", trials=1, parallel=1, budget_usd=None, redis_db=15,
        keep_sandbox=False, harness="", model="", effort="", parent="", hypothesis="", overlay="", json=False,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def _run(capsys, action, **kw):
    code = agent_cli.cmd_replay(_ns(action, **kw))
    return code, capsys.readouterr().out


def test_candidates_is_a_table_and_baseline_always_exists(capsys):
    code, text = _run(capsys, "candidates")
    assert code == 0
    assert "total: 1" in text
    assert "candidates[1]{name,harness,model,effort,hypothesis}:" in text
    assert "replay run --candidate baseline --scenario <id> --budget-usd 2" in text


def test_new_confirms_the_card(capsys):
    code, text = _run(capsys, "new", candidate="x", harness="codex-cli", model="gpt-5")
    assert code == 0
    assert "name: x\nharness: codex-cli\nmodel: gpt-5" in text


def test_live_db_is_refused_as_a_structured_usage_error(capsys):
    code, text = _run(capsys, "run", candidate="c", scenario="s", redis_db=0)
    assert code == 2
    assert "live store" in text
    assert "code: LIVE_DB_REFUSED" in text
    assert "replay run --candidate c --scenario s --redis-db 15" in text


def test_run_without_scenario_is_usage(capsys):
    code, text = _run(capsys, "run", candidate="c")
    assert code == 2
    assert "code: USAGE" in text


def test_run_reports_trials_and_total_cost(capsys, monkeypatch):
    fake = [
        {"trial": 1, "exit_reason": "ok", "wall_s": 3, "cost_usd": 0.25, "tokens_in": 10, "tokens_out": 5},
        {"trial": 2, "exit_reason": "ok", "wall_s": 4, "cost_usd": 0.5, "tokens_in": 10, "tokens_out": 5},
    ]
    monkeypatch.setattr(replay, "run", lambda *a, **k: fake)
    code = cli.replay_main(_ns("run", candidate="c", scenario="s", trials=2))
    text = capsys.readouterr().out
    assert code == 0
    assert "trials: 2\ncost_usd: 0.75" in text
    assert "grade run --candidate c --scenario s" in text


def test_human_candidates_is_a_table(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _run(capsys, "candidates")
    text = capsys.readouterr().out
    _, text = _run(capsys, "candidates")
    assert "Replay candidates" in text
    assert "baseline" in text
