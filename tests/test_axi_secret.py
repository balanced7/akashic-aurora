"""Pins for `secret` after the AXI conversion: the vault listing and the errors. Every case uses a
throwaway vault folder (AKASHIC_SECRETS_DIR); the capture window is never opened.

Run: uv run pytest tests/test_axi_secret.py -q
"""

import argparse
import io

import pytest

import agent_cli


@pytest.fixture
def vault(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(tmp_path))
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    (tmp_path / "openai.key").write_text("x" * 51, encoding="utf-8")
    return tmp_path


def _secret(capsys, target=None, **kw):
    ns = argparse.Namespace(target=target, stdin=False, fields=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    code = agent_cli.cmd_secret(ns)
    cap = capsys.readouterr()
    return code, cap.out + cap.err


def test_listing_counts_and_never_shows_contents(vault, capsys):
    code, text = _secret(capsys)
    assert code == 0
    assert "present: 1" in text
    assert "credentials[" in text
    assert "{name,state,bytes}:" in text
    assert "openai.key,present,51" in text
    assert "deepseek.key,absent,0" in text
    assert "x" * 51 not in text
    assert "secret <name> --stdin" in text


def test_fields_adds_the_description(vault, capsys):
    _, text = _secret(capsys, fields="what")
    assert "{name,state,bytes,what}:" in text
    assert "OpenAI API key" in text


def test_an_unknown_target_is_a_structured_error(vault, capsys):
    code, text = _secret(capsys, "../etc/passwd")
    assert code == 2
    assert "code: UNKNOWN_TARGET" in text


def test_stdin_capture_returns_a_byte_count_receipt(vault, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("sk-test-value\n"))
    code, text = _secret(capsys, "kimi.key", stdin=True)
    assert code == 0
    assert "saved: kimi.key\nbytes: 13" in text
    assert "sk-test-value" not in text
    monkeypatch.setattr("sys.stdin", io.StringIO("   "))
    code, text = _secret(capsys, "kimi.key", stdin=True)
    assert code == 2
    assert "code: INVALID" in text


def test_human_listing(vault, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _secret(capsys)
    assert "1 of " in text
    assert "51 B" in text
