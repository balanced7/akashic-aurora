"""Pins for `provenance` after the AXI conversion: what an agent and a person see.

Run: uv run pytest tests/test_axi_provenance.py -q
"""

import argparse

import pytest

import agent_cli
from core.fleet import provenance

_REC = {
    **dict.fromkeys(provenance.FIELDS, "x"),
    "session_id": "s1",
    "agent_id": "alice",
    "harness": "shell",
    "harness_version": "unknown",
    "model": "unknown",
}


@pytest.fixture
def prov(monkeypatch):
    holder = {"rec": dict(_REC)}
    monkeypatch.setattr(provenance, "ensure", lambda session_id="", agent_id="": holder["rec"] if session_id else {})
    monkeypatch.setattr(provenance, "current_session_id", lambda env=None: "")
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return holder


def _run(capsys, session="s1", json_=False):
    code = agent_cli.cmd_provenance(argparse.Namespace(session=session, agent="", json=json_))
    return code, capsys.readouterr().out


def test_record_is_toon_with_the_unknown_fields_counted(prov, capsys):
    code, text = _run(capsys)
    assert code == 0
    assert "agent_id: alice" in text
    assert "unknown[2]: harness_version,model" in text  # pre-computed: what is still to learn
    assert "help[" not in text  # a record answers itself


def test_no_session_is_a_structured_error_with_exit_1(prov, capsys):
    code, text = _run(capsys, session="")
    assert code == 1
    assert "code: NO_SESSION" in text
    assert "provenance --session <id>" in text


def test_json_is_unchanged(prov, capsys):
    code, text = _run(capsys, json_=True)
    assert code == 0
    assert text.startswith('{"pointer": "prov:session:s1", "record": {"session_id": "s1"')


def test_human_view_lists_fields_without_the_agent_list(prov, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _run(capsys)
    assert "Provenance · s1" in text
    assert "alice" in text
    assert "unknown " not in text.splitlines()[-1]  # no trailing list of unknown fields
