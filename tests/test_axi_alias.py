"""Pins for `alias` after the AXI conversion: what an agent and a person see.

The toolbelt is pointed at a temporary directory, so nothing touches data/verb-registry/.

Run: uv run pytest tests/test_axi_alias.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def belt(monkeypatch, tmp_path):
    from core.toolbelt import registry

    monkeypatch.setattr(registry, "default_root", lambda: str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return tmp_path


def _alias(capsys, action, name="", **kw):
    ns = argparse.Namespace(
        agent_id="tbelt",
        action=action,
        name=name,
        step=[],
        evidence="GUESS",
        tested_against=None,
        why="",
        family="UNSORTED",
        reason="",
        fields=None,
        json=False,
    )
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_alias(ns)
    return code, capsys.readouterr().out


def test_mint_says_what_happened_and_how_to_run_it(belt, capsys):
    code, text = _alias(capsys, "mint", "land", step=["status", "locks"], family="RHYTHM")
    assert code == 0
    assert "alias: land\nresult: minted\nversion: 1" in text
    assert "run tbelt land" in text
    assert "kata tbelt land" in text  # GUESS: the way to prove it is offered
    _, text = _alias(capsys, "mint", "land", step=["status"], family="RHYTHM")
    assert "result: superseded\nversion: 2" in text
    _, text = _alias(capsys, "mint", "land", step=["status"], family="RHYTHM")
    assert "result: unchanged\nversion: 2" in text


def test_list_is_a_table_with_totals(belt, capsys):
    _alias(capsys, "mint", "scan", step=["locks"], evidence="VERIFIED", tested_against="pin-1")
    code, text = _alias(capsys, "list")
    assert code == 0
    assert "active: 1" in text
    assert "aliases[1]{name,family,version,evidence,steps}:" in text
    assert "scan,UNSORTED,1,VERIFIED,locks" in text
    _, text = _alias(capsys, "list", fields="tested_against")
    assert "{name,family,version,evidence,steps,tested_against}" in text
    assert "pin-1" in text


def test_empty_toolbelt_is_said_outright(belt, capsys):
    code, text = _alias(capsys, "list")
    assert code == 0
    assert "active: 0" in text
    assert "aliases: []" in text
    assert "alias tbelt mint <name>" in text


def test_refusals_are_structured(belt, capsys):
    code, text = _alias(capsys, "retire", "ghost")
    assert code == 1
    assert "code: NOT_FOUND" in text
    code, text = _alias(capsys, "mint", "bad", step=["nosuchverb"])
    assert code == 1
    assert "code: REFUSED" in text
    code, text = _alias(capsys, "mint", "")
    assert code == 2
    assert "code: USAGE" in text


def test_human_view_shows_the_table(belt, capsys, monkeypatch):
    _alias(capsys, "mint", "scan", step=["locks"], evidence="VERIFIED")
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    _, text = _alias(capsys, "list")
    assert "1 active of a quota of 20" in text
    assert "scan" in text
    assert "v1" in text
    assert "VERIFIED" in text
