"""Pins for `resident` after the AXI conversion: what an agent and a person see. The registry is
faked, so nothing here reads or writes the store.

Run: uv run pytest tests/test_axi_resident.py -q
"""

import argparse

import pytest

import agent_cli
from core.fleet import residents as R

ALICE = {"state": "ratified", "agent_id": "alice", "callsign": "Lantern", "receipts": ["alice_fix"],
         "family": "scouts", "team": "blue", "number": 7, "ratified_by": "operator", "formerly": []}  # fmt: skip
CAROL = {"state": "nominated", "agent_id": "carol", "callsign": "Ember", "receipts": ["carol_note"], "by": "bob"}
JOB = {"agent_id": "alice", "role": "Jester", "side": "Red", "exercise": "ex7", "by": "bob", "provenance": "assigned"}


class _Store:
    def lrange(self, key, a, b):
        return ["alice", "carol"]


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setattr(R, "get", lambda a: dict(ALICE) if a == "alice" else None)
    monkeypatch.setattr(R, "history", lambda a: [dict(CAROL)] if a == "carol" else [])
    monkeypatch.setattr(R, "current_role", lambda a: dict(JOB) if a == "alice" else None)
    monkeypatch.setattr(R, "roles", lambda **kw: [dict(JOB)] if kw.get("role") in (None, "Jester") else [])
    monkeypatch.setattr(R, "_store", _Store)
    monkeypatch.setattr(R, "designation", lambda a: "scouts | blue | 7 - Lantern" if a == "alice" else "")

    def nominate(**kw):
        raise ValueError("refused: receipt 'alice_fix' was authored by 'alice', not by the nominee 'dave'")

    monkeypatch.setattr(R, "nominate", nominate)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")


def _resident(capsys, sub=None, nominee="", **kw):
    ns = argparse.Namespace(sub=sub, nominee=nominee, family="", team="", agent="", role="", side="",
                            exercise="", provenance="")  # fmt: skip
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_resident(ns)
    cap = capsys.readouterr()
    return code, cap.out + cap.err


def test_show_splits_the_designation_into_fields(registry, capsys):
    code, text = _resident(capsys, "show", "alice")
    assert code == 0
    assert "callsign: Lantern" in text
    assert "ratified_by: operator" in text
    assert "operating_as:\n  role: Jester" in text


def test_a_pending_nomination_hints_the_ratify_command(registry, capsys):
    _, text = _resident(capsys, "show", "carol")
    assert "ratified: false" in text
    assert "resident ratify carol --callsign Ember --by <you>" in text


def test_bare_resident_is_the_roster(registry, capsys):
    code, text = _resident(capsys)
    assert code == 0
    assert "total: 2\nresidents[2]{agent,callsign,designation,ratified}:" in text
    assert "carol,Ember,null,false" in text


def test_empty_roles_is_an_explicit_zero(registry, capsys):
    _, text = _resident(capsys, "roles", role="Oracle")
    assert "total: 0\nassignments: []" in text


def test_a_refusal_is_a_structured_error_with_its_why(registry, capsys):
    code, text = _resident(
        capsys, "nominate", "dave", callsign="Moss", receipt=["alice_fix"], by="bob", vendor="", note="", number=None
    )
    assert code == 1
    assert "code: REFUSED" in text
    assert "not by the nominee" in text


def test_human_roster_is_a_table(registry, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _resident(capsys, "roster")
    assert "Residents · 2" in text
    assert "Lantern" in text
