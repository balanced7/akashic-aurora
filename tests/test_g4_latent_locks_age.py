"""G4.P2 latent ADV-033: `locks` computed each lock's age with an unimported `time`.

The NameError was swallowed by the surrounding `except Exception`, so the `[Ns old, ttl Ns]`
annotation never appeared in the human `locks` listing.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.comm import locks


class _FakeLockManager:
    def __init__(self, agent: str) -> None:
        self.agent = agent

    def list_locks(self) -> list[dict[str, object]]:
        return [{"path": "core/x.py", "agent": "codex", "token": "t1", "ts": time.time() - 30, "ttl": 600}]


def test_locks_listing_shows_lock_age(monkeypatch, capsys):
    monkeypatch.setattr(locks, "LockManager", _FakeLockManager)
    args = argparse.Namespace(agent_id="claude", json=False)

    assert agent_cli.cmd_locks(args) == 0

    out = capsys.readouterr().out
    assert "core/x.py  <- codex" in out
    assert "s old, ttl 600s]" in out
