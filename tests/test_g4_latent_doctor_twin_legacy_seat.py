"""G4.P2 latent fix: doctor's twin_sessions finding with a legacy seat file.

wake_seat.iter_seats() yields (path, None) for the legacy (session-less) seat file. The
twin-session check sliced every session id with s[:8], so a legacy seat beside a session
seat raised TypeError, the surrounding except swallowed it, and the twin finding vanished.
"""

import os
import time

os.environ.setdefault("REDIS_DB", "15")


def _probes():
    return {
        "worklive": lambda a: {
            "phase": "idle",
            "detail": "",
            "turn": 3,
            "since_ts": time.time() - 5,
            "beat_ts": time.time() - 1,
        },
        "progress": lambda a: None,
        "backlog": lambda a: 0,
        "stalled_since": lambda a, present: None,
        "halted": lambda a: None,
        "lane_health": lambda a: None,
        "token_cost": lambda a: None,
        "wire": lambda a: None,
        "feed_failures": lambda a: None,
        "stale_code": lambda a: None,
        "bench_count": lambda a: 0,
        "now": time.time(),
    }


def test_twin_sessions_survives_legacy_seat(monkeypatch):
    from core.comm import doctor, runner_lock, wake_seat

    seats = [("/tmp/legacy.pid", None), ("/tmp/s1.pid", "abcdef1234567890")]
    monkeypatch.setattr(wake_seat, "iter_seats", lambda agent: seats)
    monkeypatch.setattr(runner_lock, "holder", lambda agent: None)

    findings = doctor.examine("g4latent_agent", probes=_probes())
    twins = [f for f in findings if "LIVE SESSIONS" in str(f)]
    assert len(twins) == 1, findings
    assert "abcdef12" in str(twins[0])
