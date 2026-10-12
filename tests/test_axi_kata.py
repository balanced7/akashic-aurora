"""Pins for `kata` after the AXI conversion: the verdict, the evidence and each step's check.

The toolbelt is pointed at a temporary directory, so nothing touches data/verb-registry/.

Run: uv run pytest tests/test_axi_kata.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def belt(monkeypatch, tmp_path):
    from core.toolbelt import registry

    monkeypatch.setattr(registry, "default_root", lambda: str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    tb = registry.Toolbelt("tkata")
    tb.mint("good", [["locks"], ["alias", "tkata", "list"]])
    tb.mint("bad", [["locks"], ["alias", "tkata", "list", "--nope"]])
    tb.mint("done", [["locks"]], evidence="VERIFIED", tested_against="pin-1")
    return tb


def _kata(capsys, name):
    code = agent_cli.cmd_kata(argparse.Namespace(agent_id="tkata", name=name))
    return code, capsys.readouterr().out


def test_a_clean_kata_levels_up_and_says_from_what(belt, capsys):
    code, text = _kata(capsys, "good")
    assert code == 0
    assert "verdict: leveled up\nevidence: VERIFIED\nevidence_change: GUESS -> VERIFIED\nversion: 2" in text
    assert "steps_checked: 2" in text
    assert "run tkata good" in text


def test_a_failing_step_is_named_with_the_parser_error(belt, capsys):
    code, text = _kata(capsys, "bad")
    assert code == 1
    assert "verdict: failed\nevidence: GUESS\nevidence_change: none" in text
    assert "failed: 1" in text
    assert 'fail,alias tkata list --nope,"unrecognized arguments: --nope"' in text
    assert belt.get("bad")["evidence"] == "GUESS"


def test_the_parser_error_is_found_in_human_mode_too(belt, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    ok, results = agent_cli._kata_check([["alias", "tkata", "list", "--nope"]])
    assert not ok
    assert results[0][2] == "error: unrecognized arguments: --nope"


def test_already_verified_is_a_plain_confirmation(belt, capsys):
    code, text = _kata(capsys, "done")
    assert code == 0
    assert "verdict: already verified" in text
    assert "help" not in text


def test_unknown_alias_is_not_found(belt, capsys):
    code, text = _kata(capsys, "ghost")
    assert code == 1
    assert "code: NOT_FOUND" in text


def test_human_view_leads_with_the_verdict(belt, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    _, text = _kata(capsys, "bad")
    assert "✗ 1 step(s) fail the CLI's grammar; evidence stays GUESS" in text
    assert "unrecognized arguments: --nope" in text
