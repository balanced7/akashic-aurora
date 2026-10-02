"""G4.P2 latent fix: doctor's twin_sessions finding with a legacy seat file.

wake_seat.iter_seats() yields (path, None) for the legacy (session-less) seat file. The
twin-session check sliced every session id with s[:8], so a legacy seat beside a session
seat raised TypeError, the surrounding except swallowed it, and the twin finding vanished.
"""

import time
from typing import Any

import pytest

from core.comm import doctor, runner_lock, wake_seat


def _none(_agent: str, *_rest: object) -> None:
    return None


def _zero(_agent: str) -> int:
    return 0


def _idle(_agent: str) -> dict[str, Any]:
    return {"phase": "idle", "detail": "", "turn": 3, "since_ts": time.time() - 5, "beat_ts": time.time() - 1}


def _probes() -> dict[str, Any]:
    probes: dict[str, Any] = dict.fromkeys(
        ("progress", "stalled_since", "halted", "lane_health", "token_cost", "wire", "feed_failures", "stale_code"),
        _none,
    )
    probes.update(worklive=_idle, backlog=_zero, bench_count=_zero, now=time.time())
    return probes


def _two_seats(_agent: str) -> list[tuple[str, str | None]]:
    return [("legacy-seat.pid", None), ("session-seat.pid", "abcdef1234567890")]


def test_twin_sessions_survives_legacy_seat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report exactly one twin_sessions finding for a legacy seat beside a session seat."""
    monkeypatch.setenv("REDIS_DB", "15")
    monkeypatch.setattr(wake_seat, "iter_seats", _two_seats)
    monkeypatch.setattr(runner_lock, "holder", _none)

    findings = doctor.examine("g4latent_agent", probes=_probes())
    twins = [f for f in findings if "LIVE SESSIONS" in str(f)]
    assert len(twins) == 1, findings
    assert "abcdef12" in str(twins[0])
