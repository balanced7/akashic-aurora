"""G4.P2 latent fix: ask_peer's poll-failure path must return, not raise.

ask_peer() promises "Never raises". When sweep()/state_of() raised during the poll loop it
returned BoundaryOutcome.caught(..., ask_id=...), but caught() has no ask_id parameter, so
the handler itself raised TypeError and the caller got an exception instead of an outcome.
"""

import os

os.environ.setdefault("REDIS_DB", "15")


class _FakeBus:
    def __init__(self, agent_id, *a, **kw):
        self.agent_id = agent_id

    def tail(self):
        return {"inbox": "0-0"}

    def send(self, to, kind, content, **kw):
        return "123-0"


def test_ask_peer_poll_failure_returns_outcome(monkeypatch):
    from core.comm import ask as ask_mod
    from core.comm import bus, expectations, liveness

    def _boom(*a, **kw):
        raise RuntimeError("sweep exploded")

    monkeypatch.setattr(liveness, "attendance", _boom)
    monkeypatch.setattr(bus, "Bus", _FakeBus)
    monkeypatch.setattr(expectations, "arm", lambda *a, **kw: True)
    monkeypatch.setattr(expectations, "sweep", _boom)

    out = ask_mod.ask_peer("g4latent_sender", "g4latent_peer", "hello?", wait_s=0, poll_s=0)
    assert out.ok is False
    assert "ask_peer(poll)" in out.why
    assert "sweep exploded" in out.why
    assert out.ref == "123-0"
