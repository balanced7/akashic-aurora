"""Pins for `tool list` / `tool run` after the AXI conversion.

The play tier is pointed at a temporary directory, so nothing touches data/play/.

Run: uv run pytest tests/test_axi_tool.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def play(monkeypatch, tmp_path):
    from core.toolbelt import play_sandbox

    monkeypatch.setattr(play_sandbox, "PLAY", str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    (tmp_path / "tplay").mkdir()
    (tmp_path / "tplay" / "hello.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "tplay" / "boom.py").write_text("raise SystemExit(3)\n", encoding="utf-8")
    return tmp_path


def test_list_is_one_row_per_tool_with_the_ref_run_takes(play, capsys):
    agent_cli.cmd_tool_list(argparse.Namespace(agent=""))
    text = capsys.readouterr().out
    assert "play_tools: 2" in text
    assert "tools[2]{agent,tool,bytes,receipts}:" in text
    assert "tplay,boom,20,0" in text
    assert "tool run <agent>/<tool>" in text


def test_an_empty_seat_says_zero_and_where_tools_live(play, capsys):
    assert agent_cli.cmd_tool_list(argparse.Namespace(agent="nobody")) == 0
    text = capsys.readouterr().out
    assert "play_tools: 0\ntools: []" in text
    assert "where: data/play/nobody/<tool>.py" in text


def test_run_reports_the_receipt_fields(play, capsys):
    ns = argparse.Namespace(ref="tplay/boom", timeout=10, no_sandbox=False, args=[])
    assert agent_cli.cmd_tool_run(ns) == 1
    text = capsys.readouterr().out
    assert "tool: tplay/boom\nverdict: fail\nexit: 3" in text
    assert "evidence: GUESS" in text
    assert "receipt:" in text
    agent_cli.cmd_tool_list(argparse.Namespace(agent="tplay"))
    assert "tplay,boom,20,1" in capsys.readouterr().out  # the receipt counts


def test_missing_tool_and_bad_ref_are_structured(play, capsys):
    code = agent_cli.cmd_tool_run(argparse.Namespace(ref="tplay/ghost", timeout=0, no_sandbox=False, args=[]))
    assert code == 1
    assert "code: NOT_FOUND" in capsys.readouterr().out
    code = agent_cli.cmd_tool_run(argparse.Namespace(ref="bad", timeout=0, no_sandbox=False, args=[]))
    assert code == 1
    assert "code: USAGE" in capsys.readouterr().out


def test_bare_tool_is_a_usage_error(play, capsys):
    args = agent_cli.build_parser().parse_args(["tool"])
    assert args.fn(args) == 2
    assert "tool needs a subcommand" in capsys.readouterr().out


def test_human_view_is_a_table(play, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    agent_cli.cmd_tool_list(argparse.Namespace(agent=""))
    text = capsys.readouterr().out
    assert "hello" in text
    assert "receipts" in text
