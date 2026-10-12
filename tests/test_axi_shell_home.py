"""Pins for `shell-home` after the AXI conversion: what an agent and a person see.

Every case runs against a throwaway HOME (tmp_path), never the real one: --set writes ~/.bashrc.

Run: uv run pytest tests/test_axi_shell_home.py -q
"""

import argparse

import pytest

import agent_cli


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    return tmp_path


def _sh(capsys, set_=None, clear=False):
    code = agent_cli.cmd_shell_home(argparse.Namespace(set=set_, clear=clear))
    return code, capsys.readouterr().out


def test_unset_says_where_shells_land_and_how_to_map_them(home, capsys):
    code, text = _sh(capsys)
    assert code == 0
    assert "home_mapping: null" in text
    assert "fresh_shells_land_at: the session launch dir" in text
    assert "profile_hook: absent" in text
    assert "shell-home --set <dir>" in text


def test_set_then_read_then_clear(home, capsys, tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    code, text = _sh(capsys, set_=str(target))
    assert code == 0
    assert "hook: installed into ~/.bashrc" in text
    _, text = _sh(capsys)
    assert "profile_hook: installed" in text
    assert "shell-home --clear" in text
    _, text = _sh(capsys, clear=True)
    assert "cleared: true" in text
    _, text = _sh(capsys, clear=True)
    assert "cleared: false\nreason: nothing set" in text


def test_a_missing_directory_is_a_usage_error(home, capsys, tmp_path):
    code, text = _sh(capsys, set_=str(tmp_path / "nope"))
    assert code == 2
    assert "code: USAGE" in text


def test_human_view(home, capsys, monkeypatch):
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    _, text = _sh(capsys)
    assert "Shell home" in text
    assert "profile hook" in text
