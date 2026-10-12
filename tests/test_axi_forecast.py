"""Pins for `forecast` after the AXI conversion: what an agent and a person see.

The registry path is fixed inside the repo, so these pins swap the registry class for one
that writes to a temporary file.

Run: uv run pytest tests/test_axi_forecast.py -q
"""

import argparse
import time

import pytest

import agent_cli
from core.coord import forecast_registry as fr


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    tmp = str(tmp_path / "forecasts.jsonl")
    real = fr.ForecastRegistry

    class _Tmp(real):
        def __init__(self, path=None, **kw):
            super().__init__(tmp, **kw)

    monkeypatch.setattr(fr, "ForecastRegistry", _Tmp)
    return _Tmp()


def _run(capsys, action="list", **kw):
    ns = argparse.Namespace(
        action=action, id_pos=None, id=None, task="", by="claude", statement="", metric=None, target=None,
        horizon=None, mechanism="", dies_when="", observed="", evidence="", verdict=None, calibration=False, fields=None,
    )  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_forecast(ns)
    return code, capsys.readouterr().out


def _bet(reg, fid, by="claude", horizon=None, statement="the thing happens"):
    reg.register(
        id=fid, task_ref="T1", registered_by=by, expectation={"statement": statement},
        horizon_ts=horizon if horizon is not None else time.time() + 86400, mechanism="m", dies_when="never",
    )  # fmt: skip


def test_list_counts_rows_and_the_overdue_nag(registry, capsys):
    _bet(registry, "F1")
    _bet(registry, "F2", by="kimi", horizon=time.time() - 86400)
    registry.score("F1", scored_by="claude", observed="x", evidence_ref="", verdict="voided")
    code, text = _run(capsys)
    assert code == 0
    assert "total: 2\nopen: 1\nscored:\n  voided: 1\noverdue: 1" in text
    assert "forecasts[2]{id,verdict,by,horizon}:" in text
    assert "F1,voided,claude," in text
    assert "the thing happens" not in text  # statements are a --fields column
    assert "forecast list --fields statement" in text
    assert "F2,open,kimi," in text
    assert "forecast score F2 --verdict" in text
    assert "forecast list --calibration" in text


def test_calibration_tables(registry, capsys):
    _bet(registry, "F2", by="kimi", horizon=time.time() - 86400)
    _, text = _run(capsys, calibration=True)
    assert "overdue_forecasts[1]{id,by,horizon}:" in text
    assert "F2,kimi," in text


def test_empty_registry_says_zero(registry, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert "total: 0\nopen: 0\noverdue: 0\nforecasts: []" in text
    assert "forecast register --id <id>" in text


def test_long_statements_are_cut_with_their_size(registry, capsys):
    _bet(registry, "F1", statement="word " * 80)
    _, text = _run(capsys, fields="statement")
    assert "(truncated, 399 chars total)" in text
    code, text = _run(capsys, fields="bogus")
    assert code == 2
    assert "unknown field(s) bogus" in text


def test_errors_are_structured(registry, capsys):
    code, text = _run(capsys, action="register")
    assert code == 2
    assert "code: USAGE" in text
    code, text = _run(capsys, action="score", id_pos="F9", verdict="hit")
    assert code == 1
    assert "code: REFUSED" in text
    assert "no forecast 'F9' registered" in text


def test_register_confirms_what_was_stored(registry, capsys):
    code, text = _run(capsys, action="register", id="F7", statement="s", dies_when="d", horizon="+1d")
    assert code == 0
    assert "registered: F7\nby: claude" in text
    assert "dies_when: d" in text


def test_human_view(registry, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _bet(registry, "F1")
    _, text = _run(capsys)
    assert "1 forecasts · 1 open" in text
    assert "F1" in text
