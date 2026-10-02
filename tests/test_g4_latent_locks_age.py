"""G4.P2 latent ADV-033: `locks` computed each lock's age with an unimported `time`.

The NameError was swallowed by the surrounding `except Exception`, so the `[Ns old, ttl Ns]`
annotation never appeared in the human `locks` listing.
"""

import argparse
import os
import time
from unittest import mock

import pytest

os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.comm import locks


def test_locks_listing_shows_lock_age(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A held lock is listed with its age and ttl."""
    held = [{"path": "core/x.py", "agent": "codex", "token": "t1", "ts": time.time() - 30, "ttl": 600}]
    manager = mock.Mock()
    manager.return_value.list_locks.return_value = held
    monkeypatch.setattr(locks, "LockManager", manager)
    args = argparse.Namespace(agent_id="claude", json=False)

    assert agent_cli.cmd_locks(args) == 0

    out = capsys.readouterr().out
    assert "core/x.py  <- codex" in out
    assert "s old, ttl 600s]" in out
