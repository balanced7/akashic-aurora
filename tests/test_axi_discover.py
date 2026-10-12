"""Pins for `discover` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_discover.py -q
"""

import argparse
import json

import pytest

import agent_cli


@pytest.fixture(autouse=True)
def agent_mode(monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _discover(capsys, query="", **kw):
    ns = argparse.Namespace(query=query, json=False, semantic=False)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_discover(ns)
    return code, capsys.readouterr()


def test_a_search_is_a_verbs_table_with_the_total(capsys):
    code, cap = _discover(capsys, "unlock")
    assert code == 0
    assert "query: unlock\ntotal: 1\nverbs[1]{verb,purpose}:" in cap.out
    assert "  unlock,release your advisory path-lock" in cap.out
    assert "unlock --help" in cap.out  # one match: the hint names it


def test_zero_matches_hands_over_the_semantic_command_on_stdout(capsys):
    code, cap = _discover(capsys, "zzzz_nothing")
    assert code == 0
    assert "total: 0\nverbs: []" in cap.out
    assert 'discover --semantic "zzzz_nothing"' in cap.out
    assert cap.err == ""


def test_json_is_the_old_list(capsys):
    _, cap = _discover(capsys, "unlock", json=True)
    assert json.loads(cap.out) == [{"verb": "unlock", "purpose": "release your advisory path-lock"}]


def test_semantic_unknown_is_never_a_no(capsys, monkeypatch):
    from core.coord import capability_search

    monkeypatch.setattr(
        capability_search,
        "find",
        lambda q: {"exists": "UNKNOWN", "confident": False, "why": "door closed", "model": None, "usd": None},
    )
    code, cap = _discover(capsys, "who am I", semantic=True)
    assert code == 0
    assert "exists: UNKNOWN\nconfident: false" in cap.out
    assert "method: " in cap.out
    assert 'discover --semantic "who am I"' in cap.out  # not confident: ask again


def test_human_view_is_a_table(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, cap = _discover(capsys, "unlock")
    assert '1 verb matching "unlock"' in cap.out
    assert "release your advisory path-lock" in cap.out
