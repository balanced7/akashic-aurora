"""Pins for `recall-prevention` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_recall_prevention.py -q
"""

import argparse

import pytest

from core.recall import prevention
from core.recall.surface import cmd_recall_prevention


def _report(rows=0, violated=None, surfaced=None, control=None):
    per = {
        f"learn:experiment:{k}": {"VIOLATED": n, "UNKNOWABLE": 0, "COMPLIED": 0} for k, n in (violated or {}).items()
    }
    return {
        "stage_rows": rows,
        "observations": rows,
        "prevention_candidates": rows,
        "control_arm": 0,
        "rescue_flips": 1 if rows else 0,
        "verdicts": {"VIOLATED": sum((violated or {}).values()), "UNKNOWABLE": 0, "COMPLIED": 0},
        "unattributed_repeats": [],
        "settled": 0,
        "coverage": 0.0,
        "contrast": {"success_rate_when_surfaced": surfaced, "success_rate_when_not_surfaced": control},
        "per_lesson": per,
        "confounds": ["exposure-bias: x", "COMPLIED is unprovable"],
    }


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _run(capsys, monkeypatch, rep):
    monkeypatch.setattr(prevention, "report", lambda: rep)
    code = cmd_recall_prevention(argparse.Namespace(json=False))
    return code, capsys.readouterr().out


def test_an_empty_stage_log_is_said_outright_without_confounds(agent, capsys, monkeypatch):
    code, text = _run(capsys, monkeypatch, _report())
    assert code == 0
    assert text.startswith("authority: observation only")
    assert "stage_rows: 0" in text
    assert "prevention_candidates: 0" in text
    assert "no action outcomes logged yet" in text
    assert "confounds" not in text
    assert "hooks status" in text


def test_counts_contrast_violations_and_confounds(agent, capsys, monkeypatch):
    _, text = _run(capsys, monkeypatch, _report(rows=10, violated={"stage_paths": 2}, surfaced=0.9, control=0.8))
    assert "stage_rows: 10" in text
    assert "raw_delta: 0.1" in text
    assert "violated[1]{lesson,times}:\n  stage_paths,2" in text
    assert "confounds[2]:" in text
    assert "repeat --report" in text


def test_human_view(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, monkeypatch, _report(rows=3, violated={"stage_paths": 1}))
    assert "observation only" in text
    assert "prevention candidates  3" in text
    assert "fired, then violated" in text
    assert "! exposure-bias: x" in text
