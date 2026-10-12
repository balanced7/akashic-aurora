"""Pins for `seat-identity` after the AXI conversion: bound, env-resolved, no session, clear.

Bindings go to a tmp dir (TMPDIR), never the machine's temp dir.

Run: uv run pytest tests/test_axi_seat_identity.py -q
"""

import argparse
import tempfile

import pytest

import agent_cli


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(tempfile, "tempdir", None)  # re-read TMPDIR
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    monkeypatch.setenv("AKASHIC_AGENT_ID", "bench")
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.delenv("BIFROST_INCARNATION", raising=False)


def _run(capsys, agent_id="", session="sess-0001-test", clear=False):
    code = agent_cli.cmd_seat_identity(argparse.Namespace(agent_id=agent_id, session=session, clear=clear))
    return code, capsys.readouterr().out


def test_declare_then_show_resolves_from_the_binding(capsys):
    code, text = _run(capsys, agent_id="alice")
    assert code == 0
    assert text.startswith("declared: alice\nseat: alice\n")
    assert "resolved_from: binding" in text
    assert "help[" not in text  # bound: nothing left to do
    _, text = _run(capsys)
    assert "seat: alice" in text


def test_env_resolution_says_there_is_no_binding_and_how_to_make_one(capsys):
    code, text = _run(capsys, session="sess-0002-test")
    assert code == 0
    assert "resolved_from: env" in text
    assert "binding: none" in text
    assert "seat-identity bench --session sess-0002-test" in text


def test_no_session_is_an_error_exit_1(capsys):
    code, text = _run(capsys, session="")
    assert code == 1
    assert "code: NO_SESSION" in text


def test_invalid_id_is_refused(capsys):
    code, text = _run(capsys, agent_id="bad id!")
    assert code == 1
    assert "code: INVALID_ID" in text


def test_clear_says_what_it_did(capsys):
    _run(capsys, agent_id="alice")
    code, text = _run(capsys, clear=True)
    assert code == 0
    assert text.startswith("binding: cleared\n")
    _, text = _run(capsys, clear=True)
    assert text.startswith("binding: none (nothing to clear)")
