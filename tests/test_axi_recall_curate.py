"""Pins for `recall-curate` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_recall_curate.py -q
"""

import argparse

import pytest

from core.recall import curator, forge_optimizer
from core.recall.surface import cmd_recall_curate


def _rep(bench=(), ghosts=0):
    return {
        "corpus": 5,
        "surface_active": 4,
        "bench": [{"name": n, "surfaced": 12, "age_days": 9.0} for n in bench],
        "unbench": [],
        "credited_ghosts": [],
        "ghost_prune_count": ghosts,
        "forge_rollback": [],
        "forge_confirm": [],
        "forge_expire": [],
    }


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, **kw):
    ns = argparse.Namespace(
        apply=False, forge_audit=False, forge_check=None, draft=None, forge_propose=False,
        forge_proposals=False, limit=None, json=False,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = cmd_recall_curate(ns)
    return code, capsys.readouterr().out


def test_a_report_with_work_lists_it_and_says_how_to_apply(agent, capsys, monkeypatch):
    monkeypatch.setattr(curator, "curation_report", lambda: _rep(bench=["stale_one"], ghosts=2))
    code, text = _run(capsys)
    assert code == 0
    assert "to_bench: 1" in text
    assert "ghosts_to_prune: 2" in text
    assert "bench[1]{name,surfaced,credit,age_days}:\n  stale_one,12,0,9" in text
    assert "mode: report only" in text
    assert "recall-curate --apply" in text


def test_nothing_to_curate_is_said_outright(agent, capsys, monkeypatch):
    monkeypatch.setattr(curator, "curation_report", lambda: _rep())
    _, text = _run(capsys)
    assert "to_bench: 0" in text
    assert "result: nothing to curate" in text


def test_apply_reports_what_was_stamped(agent, capsys, monkeypatch):
    monkeypatch.setattr(curator, "curation_report", lambda: _rep(bench=["stale_one"]))
    monkeypatch.setattr(
        curator, "apply_curation", lambda rep: {"benched": ["stale_one"], "unbenched": [], "ghosts_pruned": 0}
    )
    _, text = _run(capsys, apply=True)
    assert "applied:\n  benched: 1\n  unbenched: 0\n  ghosts_pruned: 0" in text
    assert "help" not in text


def test_forge_check_without_a_draft_is_a_usage_error(agent, capsys):
    code, text = _run(capsys, forge_check="x")
    assert code == 2
    assert "code: USAGE" in text
    assert "--forge-check x --draft" in text


def test_no_pending_proposals_is_a_zero(agent, capsys, monkeypatch):
    monkeypatch.setattr(forge_optimizer, "pending_proposals", list)
    _, text = _run(capsys, forge_proposals=True)
    assert text.startswith("pending: 0")


def test_an_abstained_proposal_carries_its_warning(agent, capsys, monkeypatch):
    prop = {"experiment": "x", "verdict": "UNMEASURABLE", "by": "deepseek", "at": "t", "draft": "Use when a: b."}
    monkeypatch.setattr(forge_optimizer, "pending_proposals", lambda: [prop])
    _, text = _run(capsys, forge_proposals=True)
    assert "pending: 1" in text
    assert "the gate abstained" in text
    assert "--forge-check x --draft" in text


def test_human_view(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.setattr(curator, "curation_report", lambda: _rep(bench=["stale_one"]))
    _, text = _run(capsys)
    assert "to bench" in text
    assert "would bench" in text
    assert "stale_one" in text
