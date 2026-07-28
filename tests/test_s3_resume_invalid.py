"""S3 pins -- RED first (M3). Discord resume semantics, NAMED: Resume vs Invalid Session.

Design: build-queue S3 (Daniel-gated) + the netcode doc's Discord transfer, verbatim mapping:
    RESUME          returning seat replays from its own cursor; a RESUMED MARKER separates
                    replay from live ("replayed N, now live") -- the half we LACKED.
    INVALID SESSION tombstoned/ended-by-record -> full re-boot; the seat must not consume,
                    arm, or re-arm -- and the refusal must SAY "invalid session", never
                    masquerade as seat contention (the naming half we lacked: claim_consumer
                    refuses a tombstoned self with the GENERIC seat-held teach today).
The sibling's stop-hook + wake-side tombstone stand-downs already exist (T086 S1/S1b);
these pins close the remaining naming/marker halves.

  P1  RESUME MARKER: a heartbeat after a long gap REPORTS the resume (resumed_after_s), so
      the sync render can say "RESUMED after Xs -- N unread accumulated, now live".
  P2  INVALID NAMED: a tombstoned session's consume attempt is refused with INVALID-SESSION
      language (ended by record; boot fresh; do not consume/arm) -- not the contention teach.
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture(autouse=True)
def _restore_incarnation_env():
    """Seat impersonation stays in this file (the T069 class -- sibling-swept on write)."""
    saved = {k: os.environ.get(k) for k in ("BIFROST_INCARNATION", "CLAUDE_CODE_SESSION_ID")}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


NS = f"t108s3{uuid.uuid4().hex[:6]}"
AGENT = "claude"
SEAT_A = "aaaa1111"


def test_p1_resume_marker_reported_after_gap():
    from core.comm import roster
    base = time.time() - 3600
    roster.heartbeat(NS, AGENT, SEAT_A, phase="sync", _beat_ts=base)
    hb = roster.heartbeat(NS, AGENT, SEAT_A, phase="sync")   # one hour later: a RESUME
    assert isinstance(hb, dict) and hb.get("resumed_after_s") and hb["resumed_after_s"] > 600, (
        f"RESUME UNMARKED: a beat after a 1h gap must report resumed_after_s (Discord's "
        f"'Resumed' marker -- replay and live are different states and the seat must know "
        f"which side of the line it is on). Got: {hb!r}")
    hb2 = roster.heartbeat(NS, AGENT, SEAT_A, phase="sync")  # immediate next beat: NOT a resume
    assert not (isinstance(hb2, dict) and hb2.get("resumed_after_s")), (
        f"a fresh consecutive beat must NOT report a resume: {hb2!r}")


def test_p2_tombstoned_consume_names_invalid_session():
    from core.comm import wake_seat
    from agent.bifrost_pull import consume_inbox
    sid = f"deadsess-{uuid.uuid4().hex[:8]}"
    os.environ["CLAUDE_CODE_SESSION_ID"] = sid
    os.environ["BIFROST_INCARNATION"] = sid
    wake_seat.write_tombstone(sid)
    res = consume_inbox(AGENT, limit=3)
    teach = str(res.get("teach") or "").lower()
    assert res.get("invalid_session") and "invalid session" in teach, (
        f"INVALID MASQUERADES AS CONTENTION: a tombstoned session's consume must be refused "
        f"with INVALID-SESSION language (ended by record; boot fresh; never consume/arm) -- "
        f"not the generic seat-held teach that blames a phantom holder. Got: {res!r}")
    assert not res.get("consumed"), "a tombstoned session must consume NOTHING"


if __name__ == "__main__":
    test_p1_resume_marker_reported_after_gap()
    test_p2_tombstoned_consume_names_invalid_session()
    print("PASS")
