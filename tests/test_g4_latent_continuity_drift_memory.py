"""G4.P2 latent ADV-033: `_continuity_drift()` with no notes used an unimported `get_agent_memory`.

The NameError was swallowed by the function's broad `except`, so the boot drift line never fired
when the caller let the function fetch the notes itself.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.learning import agent_memory


class _FakeMemory:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def get_decisions(self, days: int = 0) -> list[object]:
        self.calls.append(days)
        return []


def test_continuity_drift_fetches_notes_from_agent_memory(monkeypatch):
    fake = _FakeMemory()
    monkeypatch.setattr(agent_cli, "_head_commit_epoch", lambda: time.time())
    monkeypatch.setattr(agent_memory, "get_agent_memory", lambda *a, **k: fake)

    line = agent_cli._continuity_drift()

    assert fake.calls == [90]
    assert "[continuity DRIFT]" in line
    assert "where-we-are MISSING" in line
