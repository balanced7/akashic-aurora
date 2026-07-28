"""T114 -- THE ROSTER MUST SAY WHAT CODE IS ALIVE, NOT JUST THAT SOMETHING IS. RED first (M3).

CAUGHT LIVE 2026-07-28 06:10, by being wrong in public.

I landed T113 (the oversize-send spill), announced to the fleet that "the
8000-char clip is gone; nothing you send is truncated any more", and asked both
peers to prove it with a >8000-char round trip. They did. I hashed the raw
envelopes:

    1785231321038-0  frm=deepseek  8194 chars  spilled? False  clipped? TRUE
    1785231321715-0  frm=kimi      8161 chars  spilled? False  clipped? TRUE

Both still carried the OLD confession. Nothing spilled. Their runner processes
started before the commit and hold the previous packet_spec in memory, so the
fix was in git, in CI, and in my announcement -- and in none of the processes
that matter. deepseek's census detail was destroyed a SECOND time by the same
bug, in the act of testing the fix for it.

THE GAP IS NOT THE STALE PROCESS. Long-lived workers running old code is normal
and unavoidable. The gap is that NOTHING CAN SEE IT. The roster reports both
seats LIVE. It cannot report that they are LIVE ON OLD CODE. So a fix can be
committed, tested, pushed, announced and BELIEVED while every process that
matters still executes the defect, and the only way I found out was forensics on
raw stream envelopes after two peers did me the favour of testing my claim.

That is this whole night's shape one more time -- honest machinery reporting
into a void. The cost meter priced a vendor it could not see (T110). The spill
notice pointed at a door that did not exist (T113 P8). A collapse warning went to
a channel the reader does not have (T112 P11). And now a roster that measures
liveness but not what is alive.

  P1  A PROCESS STAMPS THE COMMIT IT IS RUNNING when it heartbeats.
  P2  THE ROSTER EXPOSES IT per seat.
  P3  A SEAT BEHIND HEAD IS MARKED STALE-CODE -- derived, not self-reported: a
      process running old code cannot be trusted to know that it is.
  P4  A SEAT AT HEAD IS NOT MARKED. No crying wolf; this arc has spent all night
      on false pages.
  P5  THE HUMAN RENDER SAYS IT, in the line an operator actually reads -- a
      finding that reaches only --json is the T112 P11 defect again.
  P6  UNKNOWN IS NOT STALE. A seat with no stamp (older build, foreign runner)
      must not be accused; absence of evidence gets its own word.
  P7  NEVER RAISES. Liveness is load-bearing; a version probe that can break a
      heartbeat is worse than no version probe.
"""

import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NS = "t114"


@pytest.fixture(autouse=True)
def _env():
    saved = {k: os.environ.get(k) for k in ("BIFROST_NAMESPACE", "BIFROST_INCARNATION")}
    os.environ["BIFROST_NAMESPACE"] = NS
    yield
    for k, v in saved.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


@pytest.fixture
def seat():
    from core.comm import liveness
    agent = f"t114{uuid.uuid4().hex[:6]}"
    wl = liveness.worklive(agent)
    if liveness._client() is None:
        pytest.skip("redis offline")
    yield agent, wl
    c = liveness._client()
    for k in c.scan_iter(match=f"{NS}:*{agent}*", count=200):
        c.delete(k)


# --------------------------------------------------------------- P1
def test_p1_a_process_stamps_the_commit_it_is_running(seat):
    from core.comm import liveness
    agent, wl = seat
    wl.set("thinking")
    rec = liveness._client().hgetall(f"{NS}:worklive:{agent}") or {}
    assert rec.get("code_sha"), (
        f"a heartbeat must carry the commit the process is EXECUTING, not just that it "
        f"is alive: {rec}")
    assert len(str(rec["code_sha"])) >= 7, f"a usable short sha, got {rec['code_sha']!r}"


# --------------------------------------------------------------- P2 / P3 / P4 / P6
def test_p2_p3_the_roster_derives_stale_code(seat):
    """DERIVED, never self-reported: a process running old code is exactly the process
    that cannot be trusted to know it is old."""
    from core.comm import liveness, roster
    agent, wl = seat
    wl.set("thinking")
    liveness._client().hset(f"{NS}:worklive:{agent}", "code_sha", "0" * 12)

    row = next((r for r in roster.roster(NS) if agent in r["seat"]), None)
    assert row is not None, f"seat {agent} missing from the roster entirely"
    assert row.get("code_state") == "stale", (
        f"a seat stamped with a commit that is not HEAD must read STALE: {row}")


def test_p4_a_seat_at_head_is_not_accused(seat):
    from core.comm import roster
    agent, wl = seat
    wl.set("thinking")                                  # stamps the real running sha
    row = next((r for r in roster.roster(NS) if agent in r["seat"]), None)
    assert row.get("code_state") != "stale", (
        f"a seat running HEAD must NOT be flagged -- a false staleness page is how the "
        f"real one gets ignored, which this arc has now proved twice: {row}")


def test_p6_unknown_is_not_stale(seat):
    """Absence of evidence gets its own word. An older build or a foreign runner writes
    no stamp, and must not be accused of running old code."""
    from core.comm import liveness, roster
    agent, wl = seat
    wl.set("thinking")
    liveness._client().hdel(f"{NS}:worklive:{agent}", "code_sha")
    row = next((r for r in roster.roster(NS) if agent in r["seat"]), None)
    assert row.get("code_state") == "unknown", (
        f"no stamp must read UNKNOWN, never STALE: {row}")


# --------------------------------------------------------------- P5
def test_p5_the_human_render_says_it(seat):
    """A finding that reaches only --json is the T112 P11 defect: a notice on a channel
    the reader does not use."""
    from core.comm import liveness, roster
    agent, wl = seat
    wl.set("thinking")
    liveness._client().hset(f"{NS}:worklive:{agent}", "code_sha", "0" * 12)
    text = "\n".join(roster.render_roster(NS))
    assert "stale-code" in text.lower() or "stale code" in text.lower(), (
        f"the operator-facing render must name it:\n{text}")


# --------------------------------------------------------------- P7
def test_p7_the_version_probe_never_breaks_a_heartbeat(monkeypatch):
    """Liveness is load-bearing. A version probe that can kill a heartbeat is worse than
    no version probe -- it converts an observability nicety into an outage."""
    from core.comm import liveness

    monkeypatch.setattr(liveness, "_running_code_sha", lambda: 1 / 0)
    agent = f"t114{uuid.uuid4().hex[:6]}"
    wl = liveness.worklive(agent)
    wl.set("thinking")                                   # must not raise
    if liveness._client() is not None:
        rec = liveness._client().hgetall(f"{NS}:worklive:{agent}") or {}
        assert rec.get("beat_ts"), "the heartbeat itself must still land"
        for k in liveness._client().scan_iter(match=f"{NS}:*{agent}*", count=200):
            liveness._client().delete(k)
