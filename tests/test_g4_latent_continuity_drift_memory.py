"""G4.P2 latent ADV-033: `_continuity_drift()` with no notes used an unimported `get_agent_memory`.

The NameError was swallowed by the function's broad `except`, so the boot drift line never fired
when the caller let the function fetch the notes itself.
"""

import os
import time

import pytest

os.environ.setdefault("REDIS_DB", "15")

import agent_cli
from core.learning import agent_memory


class _FakeMemory:
    """Records how many days of decisions were asked for and holds none."""

    def __init__(self) -> None:
        self.calls: list[int] = []

    def get_decisions(self, days: int = 0) -> list[object]:
        """Return no notes, so every continuity organ reads as MISSING."""
        self.calls.append(days)
        return []


def test_continuity_drift_fetches_notes_from_agent_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """With notes=None the drift check reads the decisions itself and reports what is missing."""
    fake = _FakeMemory()
    monkeypatch.setattr(agent_cli, "_head_commit_epoch", time.time)
    monkeypatch.setattr(agent_memory, "get_agent_memory", lambda: fake)

    line = agent_cli._continuity_drift()

    assert fake.calls == [90]
    assert "[continuity DRIFT]" in line
    assert "where-we-are MISSING" in line
