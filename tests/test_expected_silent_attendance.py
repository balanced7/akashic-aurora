"""An interactive seat mid-idle must read as PRESENT, not DOWN.

INCIDENT, 2026-09-23. Daniil reported Vandor (a Claude Code DESKTOP session -- interactive,
no persistent runner) "isn't responding." Vandor replied the moment he was messaged, so he
was never down -- but `sweep`/`route` rendered him UNATTENDED with "no beat, pulse, or
worklive". That is the ZERO-IS-NOT-NO collapse: a seat with no heartbeat THREAD emits no
beat between turns, and the instrument read that EXPECTED silence as a death claim.

attendance() has three beat-only probes (roster beat / progress pulse / worklive beat) and
an interactive seat scores zero on all three while it is merely waiting. But two NON-BEAT
organs already prove the seat EXISTS while emitting nothing: a held runner lock, and an
armed wake-seat file (the same two organs doctor._present_no_worklive already trusts).

THE FIX adds a fourth state, EXPECTED_SILENT: "present by a non-beat signal, emitting no
beat right now." It must be:
  - distinct from ATTENDED (nothing on the send/succession path may treat it as attending),
  - distinct from UNATTENDED (it is NOT a death claim -- the render must not print it as down),
  - only reachable when a NON-BEAT signal proves the seat EXISTS (silence alone still reads
    UNATTENDED -- silence is not evidence of presence).

Run:  py -m pytest tests/test_expected_silent_attendance.py -v
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import liveness as L


class FakeRedis:
    def __init__(self, kv=None):
        self.kv = dict(kv or {})

    def get(self, k):
        return self.kv.get(k)

    def keys(self, pattern):
        import fnmatch
        return [k for k in self.kv if fnmatch.fnmatch(k, pattern)]

    def set(self, k, v, ex=None, **kw):
        self.kv[k] = v
        return True


def _rec(beat_age_s: float, phase: str = "idle", seq: int = 1):
    return json.dumps({"phase": phase, "beat_ts": time.time() - beat_age_s, "seq": seq})


@pytest.fixture
def fake_bus(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(L, "_client", lambda *a, **k: fake)

    # Kill the beat-only probes so the verdict is decided by the NON-BEAT signal alone.
    monkeypatch.setattr(L, "progress_age", lambda *a, **k: None)
    import core.comm.roster as _roster
    monkeypatch.setattr(_roster, "roster", lambda *a, **k: [])
    return fake


def _no_presence(monkeypatch):
    # The absence case: no runner lock, no wake seat.
    def _holder(agent):
        return None
    def _seats(agent):
        if False:
            yield None
    monkeypatch.setattr("core.comm.runner_lock.holder", _holder)
    monkeypatch.setattr("core.comm.wake_seat.iter_seats", _seats)


@pytest.fixture
def absent(monkeypatch):
    """A seat with NO non-beat presence signal: lock unheld, no wake-seat file."""
    _no_presence(monkeypatch)


# ------------------------------------------------------------------ the new state
def test_silence_with_a_wake_seat_reads_present_not_down(fake_bus, monkeypatch):
    """The live Vandor shape: no beat on any rung, but an armed wake-seat file EXISTS."""
    def _holder(agent):
        return None
    def _seats(agent):
        yield ("/tmp/seat-abc", "abc123")
    monkeypatch.setattr("core.comm.runner_lock.holder", _holder)
    monkeypatch.setattr("core.comm.wake_seat.iter_seats", _seats)

    v = L.attendance("vandor")
    assert v.state == "EXPECTED_SILENT", (
        f"an armed, waiting seat read {v.state} ({v.reason}) -- silence with a presence "
        "signal must not be reported as UNATTENDED/down"
    )


def test_silence_with_a_held_lock_reads_present_not_down(fake_bus, monkeypatch):
    """The other non-beat presence signal: a held runner lock."""
    def _holder(agent):
        return {"pid": 123, "token": "t"}
    def _seats(agent):
        if False:
            yield None
    monkeypatch.setattr("core.comm.runner_lock.holder", _holder)
    monkeypatch.setattr("core.comm.wake_seat.iter_seats", _seats)

    v = L.attendance("vandor")
    assert v.state == "EXPECTED_SILENT", f"read {v.state} ({v.reason})"


def test_silence_without_any_signal_still_reads_unattended(fake_bus, absent):
    """ZERO-IS-NOT-NO does not mean silence becomes presence. No beat, no lock, no wake
    seat -> the seat is genuinely not provably here, and that stays UNATTENDED (a real
    death claim is still available for a runner whose beater died)."""
    v = L.attendance("vandor")
    assert v.state == "UNATTENDED", (
        f"silence with no presence signal read {v.state} -- must stay UNATTENDED, "
        "never be upgraded to presence on silence alone"
    )


def test_a_beat_still_wins_over_silence(fake_bus, monkeypatch):
    """EXPECTED_SILENT is a fall-through for when nothing beats. A fresh beat must still
    yield the STRONGER verdict ATTENDED."""
    pre = L._worklive_prefix()
    fake_bus.kv[pre + "vandor#abc12345"] = _rec(3.0)
    def _holder(agent):
        return None
    def _seats(agent):
        yield ("/tmp/seat-abc", "abc123")
    monkeypatch.setattr("core.comm.runner_lock.holder", _holder)
    monkeypatch.setattr("core.comm.wake_seat.iter_seats", _seats)

    v = L.attendance("vandor")
    assert v.state == "ATTENDED", f"a fresh beat read {v.state} -- beat must outrank silence"


def test_expected_silent_is_not_attended_for_the_send_path(absent):
    """The send door and succession gate test `state == "ATTENDED"`. EXPECTED_SILENT must
    NOT be accidentally equal to ATTENDED."""
    v = L.Attendance("EXPECTED_SILENT", "x", 1.0, "vandor")
    assert v.state != "ATTENDED"
    assert v.state not in ("UNATTENDED", "UNKNOWN")


# ------------------------------------------------------------------ the render
class _V:
    state = "EXPECTED_SILENT"
    reason = "present (lock/wake seat) but no beat now"
    beat_age_s = None
def test_awareness_route_renders_expected_silent_as_present(monkeypatch):
    """observe_route is the sweep/orient surface that printed UNATTENDED for Vandor. It
    must render EXPECTED_SILENT as PRESENT (no beat now), never 'down'. It imports
    attendance() locally (from core.comm.liveness) so patch the source module it reads."""
    monkeypatch.setattr(L, "attendance", lambda *a, **k: _V())
    monkeypatch.setattr(L, "live_incarnations", lambda *a, **k: ["vandor#abc12345"])

    import core.comm.awareness as A

    obs = A.observe_route("vandor")
    assert obs.status == "PRESENT", (
        f"route status {obs.status!r} -- an idle interactive seat must render PRESENT, "
        "not UNATTENDED"
    )
    assert "no beat" in obs.summary, obs.summary
