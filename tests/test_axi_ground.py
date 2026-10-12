"""Pins for `ground` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_ground.py -q
"""

import argparse
import sys

import pytest

import agent_cli

VERB = {
    "mode": "verb",
    "subject": "s1",
    "target": {"kind": "verb", "name": "recall"},
    "observed_at": "2026-10-12T00:00:00Z",
    "rungs": [
        {
            "name": "declared",
            "state": "observed",
            "claim": "classified shared",
            "source": "parity",
            "drill": "x --report",
        },
        {"name": "exercised", "state": "partial", "claim": "3 test files", "source": "scan", "drill": ""},
    ],
    "blind": ["no receipt resolver"],
}

SEAT = {
    "mode": "continuity",
    "subject": "s1",
    "target": {"kind": "seat", "name": "s1"},
    "observed_at": "2026-10-12T00:00:00Z",
    "identity_verdict": {"claim": "continuity evidence is not an identity verdict"},
    "regions": [
        {"name": "designation", "state": "absent", "authority": "registry", "bounds": {"shown": 0, "matched": 0}},
        {
            "name": "lessons",
            "state": "observed",
            "authority": "authorship",
            "bounds": {"shown": 1, "matched": 1},
            "items": [{"experiment": "port_clash", "gist": "check the port", "source": "learn:x"}],
            "drill": "uv run agent_cli.py recall x --agent s1 --json",
        },
        {
            "name": "handoffs",
            "state": "absent",
            "authority": "attribution",
            "bounds": {"shown": 0, "matched": 0},
            "drill": "inbound: prose, not a command",
            "blind": ["no outbound reader"],
        },
    ],
}


@pytest.fixture
def result(monkeypatch):
    from core.coord import ground

    holder = {"r": VERB}

    def fake(target, subject, continuity):
        if target == "seat:s1" and not continuity:
            raise ValueError("seat grounding requires the explicit --continuity mode")
        sys.stdout = sys.stderr  # what the door-parity census does to this process
        return holder["r"]

    monkeypatch.setattr(ground, "ground", fake)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _ground(capsys, target="verb:recall", continuity=False):
    ns = argparse.Namespace(target=target, agent="s1", continuity=continuity, json=False)
    code = agent_cli.cmd_ground(ns)
    return code, capsys.readouterr().out


def test_verb_rungs_are_rows_on_stdout(result, capsys):
    code, text = _ground(capsys)
    assert code == 0
    assert "rungs[2]{rung,state,claim,source}:" in text
    assert "exercised,partial,3 test files,scan" in text
    assert "blind_total: 1" in text
    assert "  x --report" in text


def test_continuity_regions_items_and_command_drills_only(result, capsys):
    result["r"] = SEAT
    _, text = _ground(capsys, "seat:s1", continuity=True)
    assert "identity_verdict: not computed" in text
    assert "lessons,observed,authorship,1,1" in text
    assert "items[1]{region,item}:" in text
    assert "port_clash: check the port" in text
    assert "handoffs: no outbound reader" in text
    assert "recall x --agent s1 --json" in text
    assert "inbound: prose" not in text


def test_seat_without_continuity_is_a_usage_error_naming_the_flag(result, capsys):
    code, text = _ground(capsys, "seat:s1")
    assert code == 2
    assert "code: USAGE" in text
    assert "ground seat:s1 --continuity --agent s1" in text


def test_human_view(result, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _ground(capsys)
    assert "Ground · verb:recall" in text
    assert "blind: no receipt resolver" in text
