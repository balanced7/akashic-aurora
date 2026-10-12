"""Pins for `loop` after the AXI conversion: what an agent and a person see.

`loop run` is only exercised on its refusal and with a stubbed loop: nothing spends money.

Run: uv run pytest tests/test_axi_loop.py -q
"""

import argparse

import pytest

from core.metaharness import cli, loop, replay


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_SETUP", str(tmp_path / "state"))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, action, **kw):
    ns = argparse.Namespace(
        action=action, candidate="", iterations=1, proposals=3, trials=1, mode="structural", daily_usd=None,
        proposer_model="", json=False,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cli.loop_main(ns)
    return code, capsys.readouterr().out


def _chain():
    replay.create_candidate("baseline")
    replay.create_candidate("v1", parent="baseline", hypothesis="h1")
    replay.create_candidate("v2", parent="v1", hypothesis="h2")


def test_empty_archive_says_zero_with_a_capped_run_hint(capsys):
    code, text = _run(capsys, "archive")
    assert code == 0
    assert "total: 0\ncandidates: []" in text
    assert "loop run --candidate baseline --daily-usd 5" in text


def test_archive_rows_status_and_lineage(capsys):
    _chain()
    _, text = _run(capsys, "archive")
    assert "total: 3" in text
    assert "candidates[3]{name,parent,pass_rate,tokens,hypothesis}:" in text
    assert "v2,v1,null,null,h2" in text
    _, text = _run(capsys, "status")
    assert "candidates: 3" in text
    assert "spent_today_usd: 0" in text
    _, text = _run(capsys, "lineage", candidate="v2")
    assert "depth: 3" in text
    assert "lineage[3]: v2,v1,baseline" in text


def test_run_without_a_budget_is_refused_and_spends_nothing(capsys, monkeypatch):
    monkeypatch.setattr(loop, "run", lambda *a, **k: pytest.fail("the loop ran without a budget"))
    code, text = _run(capsys, "run")
    assert code == 2
    assert "code: USAGE" in text
    assert "--daily-usd 5" in text


def test_unknown_candidate_lineage_is_not_found(capsys):
    code, text = _run(capsys, "lineage", candidate="ghost")
    assert code == 1
    assert "code: NOT_FOUND" in text


def test_human_archive_is_a_table(capsys, monkeypatch):
    _chain()
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, "archive")
    assert "Candidate archive" in text
    assert "baseline" in text
