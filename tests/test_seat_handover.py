"""PRE-REGISTERED ACCEPTANCE -- a retiring session must be able to YIELD its seat.

THE LIVE INCIDENT (2026-07-28). Daniel opened a fresh seat to replace an exhausted one and
reported: "the watcher for your session keeps consuming things meant for the new seat." He was
right, and the mechanism is not what either of us assumed.

The RB-21 consumer seat works exactly as designed -- it serialises consumption to ONE session per
agent id. The defect is WHICH one it serialises to:

  * claim_consumer() takes the seat on every consume, TTL 1800s
  * refresh_consumer() is wired into the STOP HOOK, so it renews on EVERY TURN END
  * session_exit() releases the seat, but ONLY on a clean SessionEnd

A retiring session that keeps being invoked -- by stop-hook re-arm demands, by background task
notifications, by the operator asking one more question -- renews its claim on every one of those
turns. It never reaches a clean SessionEnd, so it never releases. Its successor is refused the
seat and SILENTLY degraded to peek, while the outgoing session keeps draining the shared cursor.

A DYING SESSION OUT-COMPETES ITS SUCCESSOR PURELY BY STILL BREATHING.

The aggravating detail: the harness caused the renewals it was harmed by. The stop hook kept
demanding the retiring seat re-arm a wake watcher, and every demanded turn refreshed the very
lock the session was trying to give up.

THE PRIMITIVE ALREADY EXISTS AND IS HALF-WIRED. wake_seat.write_tombstone/is_tombstoned records
"this session is done by RECORD, not by inference", and free_if_dead() consults it to free a
provably-dead holder. claim_consumer() does NOT. So a session can be tombstoned and still
re-claim the seat on its next consume. Twelfth instance this arc of a guard that exists, is
correct, and is unwired at the one end that matters.

  P1  a TOMBSTONED session cannot CLAIM the seat -- closes the re-claim hole
  P2  stand_down() releases the seat AND tombstones, in one call, so a live session can yield
      without waiting for a clean SessionEnd that may never arrive
  P3  stand_down() is idempotent and safe when we do not hold the seat
  P4  a normal session still claims -- the guard is not weakened into uselessness
  P5  HANDOVER: the successor claims IMMEDIATELY after the predecessor stands down, with no
      TTL wait, and the retiree cannot snatch it back. That is the whole point.

Run: py -m pytest tests/test_seat_handover.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENT = "t-handover-agent"


@pytest.fixture()
def seat(monkeypatch, tmp_path):
    monkeypatch.setenv("BIFROST_NAMESPACE", f"t-handover-{os.getpid()}")
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setenv("TMP", str(tmp_path))
    from core.comm import runner_lock as rl
    return rl


@pytest.fixture()
def sid():
    """A session-id prefix unique PER RUN.

    The tombstone is durable by design -- a file AND a namespace record -- so fixed ids make
    these pins pass once and fail forever afterwards, which is precisely how a guard silently
    stops guarding. A result nobody can re-run is not a result.
    """
    return uuid.uuid4().hex[:8]


def test_p1_a_tombstoned_session_cannot_claim(seat, sid, tmp_path):
    from core.comm import wake_seat
    wake_seat.write_tombstone(f"{sid}a", str(tmp_path))
    ok, _gen, _info = seat.claim_consumer(AGENT, f"session:{sid}a")
    assert ok is False, (
        "a session tombstoned as DONE still took the consumer seat -- that is the re-claim hole "
        "that let a retiring seat keep draining its successor's mail")


def test_p2_stand_down_releases_and_tombstones(seat, sid, tmp_path):
    from core.comm import wake_seat
    assert seat.claim_consumer(AGENT, f"session:{sid}b")[0] is True
    assert seat.stand_down(AGENT, f"session:{sid}b") is True
    assert seat.holder(AGENT) is None, "stand_down did not release the seat"
    assert wake_seat.is_tombstoned(f"{sid}b", str(tmp_path)) is True, (
        "stand_down released but left no tombstone -- the next consume would re-claim and the "
        "session would take the seat straight back")


def test_p3_stand_down_is_idempotent_and_safe_without_the_seat(seat, sid):
    assert seat.stand_down(AGENT, f"session:{sid}c") is True
    assert seat.stand_down(AGENT, f"session:{sid}c") is True


def test_p4_a_normal_session_still_claims(seat, sid):
    ok, _gen, _info = seat.claim_consumer(AGENT, f"session:{sid}d")
    assert ok is True, "the guard was weakened -- a live untombstoned session must still claim"


def test_p5_the_successor_claims_immediately_after_handover(monkeypatch, sid):
    """THE POINT. Without this, a fresh seat waits out a 1800s TTL while its mail is drained
    by the session it replaced.

    Self-contained on purpose: this pin sets its own temp root BEFORE touching the modules, so
    the tombstone is written and read through one root. Sharing the class fixture made it fail
    on a path split while the behaviour itself was correct -- a red pin caused by the harness
    is worse than no pin, because the next seat debugs the product instead of the test.
    """
    import tempfile
    d = tempfile.mkdtemp(prefix="handover-")
    monkeypatch.setenv("TEMP", d)
    monkeypatch.setenv("TMP", d)
    monkeypatch.setenv("BIFROST_NAMESPACE", f"t-handover-p5-{sid}")
    from core.comm import runner_lock as seat
    # Explicit TTL: SESSION_CONSUMER_TTL is scaled() and the test timescale can compress it to
    # near-zero, which expires the seat between two calls and destroys the contention this pin
    # depends on. Pin the behaviour, not the clock.
    old, new = f"session:{sid}old", f"session:{sid}new"
    assert seat.claim_consumer(AGENT, old, ttl=600)[0] is True
    assert seat.claim_consumer(AGENT, new, ttl=600)[0] is False, "precondition: seat contended"
    seat.stand_down(AGENT, old)
    assert seat.claim_consumer(AGENT, new, ttl=600)[0] is True, (
        "the successor could not take the seat after a clean hand-over")
    assert seat.claim_consumer(AGENT, old, ttl=600)[0] is False, (
        "the stood-down session re-took the seat -- exactly the live symptom Daniel reported")
