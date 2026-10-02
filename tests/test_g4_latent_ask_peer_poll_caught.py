"""G4.P2 latent fix: ask_peer's poll-failure path must return, not raise.

ask_peer() promises "Never raises". When sweep()/state_of() raised during the poll loop it
returned BoundaryOutcome.caught(..., ask_id=...), but caught() has no ask_id parameter, so
the handler itself raised TypeError and the caller got an exception instead of an outcome.
"""

import pytest

from core.comm import ask as ask_mod
from core.comm import bus, expectations, liveness


class _SweepError(RuntimeError):
    """Stands in for a Redis error raised while polling."""


class _FakeBus:
    """Just enough Bus for ask_peer's send+arm step."""

    def __init__(self, agent_id: str, *_args: object, **_kwargs: object) -> None:
        self.agent_id = agent_id

    def tail(self) -> dict[str, str]:
        """Return an empty-inbox anchor."""
        return {"inbox": "0-0"}

    def send(self, *_args: object, **_kwargs: object) -> str:
        """Return a fixed message id."""
        return "123-0"


def _boom(*_args: object, **_kwargs: object) -> None:
    raise _SweepError


def _armed(*_args: object, **_kwargs: object) -> bool:
    return True


def test_ask_peer_poll_failure_returns_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn a poll-time exception into a failed outcome carrying the message id."""
    monkeypatch.setenv("REDIS_DB", "15")
    monkeypatch.setattr(liveness, "attendance", _boom)
    monkeypatch.setattr(bus, "Bus", _FakeBus)
    monkeypatch.setattr(expectations, "arm", _armed)
    monkeypatch.setattr(expectations, "sweep", _boom)

    out = ask_mod.ask_peer("g4latent_sender", "g4latent_peer", "hello?", wait_s=0, poll_s=0)
    assert out.ok is False
    assert "ask_peer(poll)" in out.why
    assert "_SweepError" in out.why
    assert out.ref == "123-0"
