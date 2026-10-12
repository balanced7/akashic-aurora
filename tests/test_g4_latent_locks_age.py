"""G4.P2 latent ADV-033: `locks` computed each lock's age with an unimported `time`.

The NameError was swallowed by the surrounding `except Exception`, so the lock's age never
appeared in the `locks` listing. Since the AXI conversion the age is a column (`age_s`) in agent
mode and "age" in human mode; both are pinned here, along with the definitive empty state.
"""

import argparse
import os
import time
from unittest import mock

import pytest

os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.comm import locks


def _held(monkeypatch, held):
    manager = mock.Mock()
    manager.return_value.list_locks.return_value = held
    monkeypatch.setattr(locks, "LockManager", manager)


def test_locks_listing_shows_lock_age(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A held lock is listed with its age and ttl."""
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    _held(monkeypatch, [{"path": "core/x.py", "agent": "codex", "token": "t1", "ts": time.time() - 30, "ttl": 600}])

    assert agent_cli.cmd_locks(argparse.Namespace(agent_id="claude", json=False)) == 0

    out = capsys.readouterr().out
    assert "locks[1]{path,agent,ttl_s,age_s}:" in out
    row = next(line for line in out.splitlines() if line.startswith("  core/x.py"))
    path, agent, ttl, age = row.strip().split(",")
    assert (path, agent, ttl) == ("core/x.py", "codex", "600")
    assert 29 <= int(age) <= 40
    assert "yours: 0" in out
    assert "unlock claude <path>" in out


def test_locks_human_view_shows_age_and_expiry(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AURORA_OUTPUT", "human")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("COLUMNS", "120")
    _held(monkeypatch, [{"path": "core/x.py", "agent": "claude", "ts": time.time() - 30, "ttl": 600}])

    agent_cli.cmd_locks(argparse.Namespace(agent_id="claude", json=False))

    out = capsys.readouterr().out
    assert "claude (you)" in out
    assert "expires in" in out
    assert "9m" in out


def test_no_locks_is_said_outright(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AURORA_OUTPUT", "agent")
    _held(monkeypatch, [])

    assert agent_cli.cmd_locks(argparse.Namespace(agent_id=None, json=False)) == 0

    out = capsys.readouterr().out
    assert out.startswith("locks: 0 advisory path-locks held")
    assert "lock <agent_id> <path>" in out
