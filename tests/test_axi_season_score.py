"""Pins for `season-score` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_season_score.py -q
"""

import argparse
import json

import pytest

import agent_cli

_EV = ["core/comm/bus.py:1"]
_ROUND = {
    "claims": [
        {"player": "alice", "dedupe_key": "k1", "claim_class": "structural", "outcome": "confirmed",
         "stream_id": "1785850000001-0", "evidence": _EV},
        {"player": "bob", "dedupe_key": "k1", "claim_class": "structural", "outcome": "confirmed",
         "stream_id": "1785850900000-0", "evidence": _EV},
        {"player": "bob", "dedupe_key": "k2", "claim_class": "needs-door", "outcome": "confirmed",
         "stream_id": "1785850000003-0", "evidence": _EV},
        {"player": "carol", "dedupe_key": "k4", "claim_class": "needs-door", "outcome": "confirmed",
         "stream_id": "1785850000005-0", "evidence": []},
    ]
}  # fmt: skip


@pytest.fixture
def round_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    f = tmp_path / "round.json"
    f.write_text(json.dumps(_ROUND), encoding="utf-8")
    return f


def _run(capsys, **kw):
    ns = argparse.Namespace(policies=False, round_file=None, compare=False, json=False, policy="v1_doc")
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_season_score(ns)
    return code, capsys.readouterr().out


def test_score_is_standings_plus_why_unscored(round_file, capsys):
    code, text = _run(capsys, round_file=str(round_file))
    assert code == 0
    assert "policy: v1_doc\nclaims: 4\nunscored: 1" in text
    assert "totals[2]{player,points}:\n  alice,4\n  bob,3\n" in text  # unscored is not zero: no row
    assert "unscored_claims[1]{player,dedupe_key,reason}:" in text
    assert 'carol,k4,"unscored: no resolvable evidence lines"' in text
    assert "--compare" in text


def test_compare_flags_a_changed_order(round_file, capsys):
    _, text = _run(capsys, round_file=str(round_file), compare=True)
    assert "players[2]{player,v1_doc,v2_aixcc,delta}:" in text
    assert "bob,3,7,4" in text
    assert "rank_v1_doc[2]: alice,bob" in text
    assert "rank_v2_aixcc[2]: bob,alice" in text
    assert "order_changed: true" in text


def test_no_claims_is_a_usage_error(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    code, text = _run(capsys)
    assert code == 2
    assert "code: USAGE" in text
    assert "season-score --policies" in text


def test_policies_lists_default_and_proposed(capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    _, text = _run(capsys, policies=True)
    assert "policies[" in text
    assert "v1_doc,default," in text
    assert "v2_aixcc,proposed," in text


def test_json_is_unchanged(round_file, capsys):
    _, text = _run(capsys, round_file=str(round_file), json=True)
    assert json.loads(text)["totals"] == {"alice": 4, "bob": 3}


def test_human_compare_calls_out_the_order_change(round_file, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys, round_file=str(round_file), compare=True)
    assert "rank v2_aixcc : bob > alice" in text
    assert "the policies change the order" in text
    assert "+4" in text
