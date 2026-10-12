"""Pins for `triage` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_triage.py -q
"""

import argparse

import pytest

import agent_cli
from core.recall import funnel


def _t(protect=(), cost=(), ghosts=()):
    return {
        "corpus_lessons": 4,
        "tracked": len(protect) + len(cost) + len(ghosts),
        "tracked_lessons": len(protect) + len(cost),
        "ghosts": [{"source": g, "surfaced": 3, "useful": 0, "helped": 0, "noise": 0} for g in ghosts],
        "dormant_count": 1,
        "min_surfaced": 5,
        "protect": [{"source": p, "helped": 1, "useful": 2, "surfaced": 9} for p in protect],
        "cost_no_return": [{"source": c, "surfaced": 12, "window_tokens_approx": 300} for c in cost],
        "noise_voted": [],
        "watch_count": 0,
        "window_injected_tokens_approx": 300,
    }


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, monkeypatch, t):
    monkeypatch.setattr(funnel, "triage", lambda min_surfaced=5: t)
    code = agent_cli.cmd_triage(argparse.Namespace(min_surfaced=5, json=False))
    return code, capsys.readouterr().out


def test_buckets_are_counted_and_tabled_with_a_next_step(agent, capsys, monkeypatch):
    t = _t(protect=["learn:experiment:core"], cost=["learn:experiment:costly"], ghosts=["learn:experiment:gone"])
    code, text = _run(capsys, monkeypatch, t)
    assert code == 0
    assert text.startswith("authority: review only")
    assert "  protect: 1\n  cost_no_return: 1" in text
    assert 'protect[1]{source,helped,useful,surfaced}:\n  "learn:experiment:core",1,2,9' in text
    assert 'cost_no_return[1]{source,surfaced,window_tokens}:\n  "learn:experiment:costly",12,300' in text
    assert "graduate <agent_id> --experiment costly" in text
    assert "recall-counters --fold" in text


def test_nothing_tracked_is_said_outright(agent, capsys, monkeypatch):
    _, text = _run(capsys, monkeypatch, _t())
    assert "  protect: 0" in text
    assert "result: nothing tracked yet" in text


def test_human_view(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    _, text = _run(capsys, monkeypatch, _t(protect=["learn:experiment:core"]))
    assert "review only" in text
    assert "protect -- earned credit" in text
    assert "learn:experiment:core" in text
