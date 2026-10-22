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
    # "boop" rather than "unlock": the search now reads use-when lines too, and lock's line
    # says "unlock when done", so unlock is no longer a one-match query.
    code, cap = _discover(capsys, "boop")
    assert code == 0
    # Each verb renders with its use-when line (core/coord/verb_guide.py): WHEN beats WHAT.
    assert "query: boop\ntotal: 1\nverbs[1]{verb,when}:" in cap.out
    assert '  boop,"Use when you just want to confirm the command door answers' in cap.out
    assert "boop --help" in cap.out  # one match: the hint names it


def test_zero_matches_hands_over_the_semantic_command_on_stdout(capsys):
    code, cap = _discover(capsys, "zzzz_nothing")
    assert code == 0
    assert "total: 0\nverbs: []" in cap.out
    assert 'discover --semantic "zzzz_nothing"' in cap.out
    assert cap.err == ""


def test_json_is_the_old_list(capsys):
    """Still a list of {verb, purpose} -- old readers keep working -- widened with the verb's
    use-when line and family."""
    _, cap = _discover(capsys, "boop", json=True)
    rows = json.loads(cap.out)
    assert [(r["verb"], r["purpose"]) for r in rows] == [
        ("boop", "the smallest verb in the house: zero arguments, always answered")
    ]
    assert rows[0]["when"].startswith("Use when ")
    assert rows[0]["family"] == "fleet"


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
    _, cap = _discover(capsys, "boop")
    assert '1 verb matching "boop"' in cap.out
    assert "confirm the command door answers" in cap.out
