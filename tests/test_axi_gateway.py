"""Pins for `gateway status` after the AXI conversion. The process census is faked; nothing is
killed or launched (restart is never called here).

Run: uv run pytest tests/test_axi_gateway.py -q
"""

import argparse
from pathlib import Path

import pytest

import agent_cli
from core.comm import wake_seat as WS

HERE = Path(agent_cli.__file__).resolve().parent
OURS = f"python {HERE / 'scripts' / 'bifrost_runner_discord.py'}"


@pytest.fixture(autouse=True)
def _agent(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _census(monkeypatch, snap):
    monkeypatch.setattr(WS, "process_snapshot", lambda: snap)
    monkeypatch.setattr(WS, "script_processes", lambda s, script: sorted(s))


def _status():
    return agent_cli.cmd_gateway(argparse.Namespace(action="status", json=False))


def test_not_running_is_data_and_keeps_exit_1(monkeypatch, capsys):
    _census(monkeypatch, {})
    assert _status() == 1
    out = capsys.readouterr().out
    assert out.startswith("state: not running")
    assert "count: 0" in out
    assert "gateway restart" in out


def test_live_gateways_are_rows_with_their_root(monkeypatch, capsys):
    _census(
        monkeypatch, {41: {"cmdline": OURS}, 42: {"cmdline": "python /elsewhere/scripts/bifrost_runner_discord.py"}}
    )
    assert _status() == 0
    out = capsys.readouterr().out
    assert "state: live" in out
    assert "count: 2" in out
    assert "41,this repo" in out
    assert "42,FOREIGN /elsewhere" in out


def test_an_unreadable_census_is_unknown_not_absent(monkeypatch, capsys):
    def boom():
        raise WS.CensusUnavailable("no ps")

    monkeypatch.setattr(WS, "process_snapshot", boom)
    assert _status() == 3
    out = capsys.readouterr().out
    assert "code: CENSUS_UNAVAILABLE" in out


def test_human_view(monkeypatch, capsys):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _census(monkeypatch, {})
    _status()
    assert "not running" in capsys.readouterr().out
