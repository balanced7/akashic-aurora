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
    """Two writers, two key shapes -- read the producers, do not assume (the standing
    rule, and the reason the first draft of these pins used hgetall on a JSON string):
      liveness.WorkLive._flush -> {ns}:worklive:{agent}        JSON, the RUNNERS' key
      roster.heartbeat         -> {ns}:worklive:{agent}#{sid8} JSON, the SEATS' key
    The stale processes that started this are runners; the roster shows seats. Both get
    stamped, so both are answerable."""
    from core.comm import liveness, roster
    agent, sid = f"t114{uuid.uuid4().hex[:6]}", uuid.uuid4().hex
    if liveness._client() is None:
        pytest.skip("redis offline")
    roster.heartbeat(NS, agent, sid, phase="thinking")
    yield agent, sid[:8], liveness.worklive(agent)
    c = liveness._client()
    for k in c.scan_iter(match=f"{NS}:*{agent}*", count=200):
        c.delete(k)


def _seat_doc(agent, sid8):
    import json as _json
    from core.comm import liveness
    return _json.loads(liveness._client().get(f"{NS}:worklive:{agent}#{sid8}") or "{}")


def _set_seat_sha(agent, sid8, sha):
    import json as _json
    from core.comm import liveness
    d = _seat_doc(agent, sid8)
    d["code_sha"] = sha
    if sha is None:
        d.pop("code_sha", None)
    liveness._client().set(f"{NS}:worklive:{agent}#{sid8}", _json.dumps(d), ex=60)


# --------------------------------------------------------------- P1
def test_p1_a_process_stamps_the_commit_it_is_running(seat):
    """BOTH writers, because the processes that were running stale code are RUNNERS
    (bare-agent key) while the roster renders SEATS (#sid8 key). Stamping only the one
    I happened to be looking at would leave the actual offenders invisible."""
    import json as _json
    from core.comm import liveness
    agent, sid8, wl = seat
    wl.set("thinking")
    runner = _json.loads(liveness._client().get(f"{NS}:worklive:{agent}") or "{}")
    assert runner.get("code_sha"), f"the RUNNER heartbeat must carry its commit: {runner}"
    assert len(str(runner["code_sha"])) >= 7, f"a usable short sha: {runner['code_sha']!r}"
    assert _seat_doc(agent, sid8).get("code_sha"), "the SEAT heartbeat must carry it too"


# --------------------------------------------------------------- P2 / P3 / P4 / P6
def test_p2_p3_the_roster_derives_stale_code(seat):
    """DERIVED, never self-reported: a process running old code is exactly the process
    that cannot be trusted to know it is old."""
    from core.comm import roster
    agent, sid8, wl = seat
    _set_seat_sha(agent, sid8, "0" * 12)

    row = next((r for r in roster.roster(NS) if agent in r["seat"]), None)
    assert row is not None, f"seat {agent} missing from the roster entirely"
    assert row.get("code_state") == "stale", (
        f"a seat stamped with a commit that is not HEAD must read STALE: {row}")


def test_p4_a_seat_at_head_is_not_accused(seat):
    from core.comm import roster
    agent, sid8, wl = seat                              # fixture already beat the real sha
    row = next((r for r in roster.roster(NS) if agent in r["seat"]), None)
    assert row.get("code_state") != "stale", (
        f"a seat running HEAD must NOT be flagged -- a false staleness page is how the "
        f"real one gets ignored, which this arc has now proved twice: {row}")


def test_p6_unknown_is_not_stale(seat):
    """Absence of evidence gets its own word. An older build or a foreign runner writes
    no stamp, and must not be accused of running old code."""
    from core.comm import roster
    agent, sid8, wl = seat
    _set_seat_sha(agent, sid8, None)
    row = next((r for r in roster.roster(NS) if agent in r["seat"]), None)
    assert row.get("code_state") == "unknown", (
        f"no stamp must read UNKNOWN, never STALE: {row}")


# --------------------------------------------------------------- P5
def test_p5_the_human_render_says_it(seat):
    """A finding that reaches only --json is the T112 P11 defect: a notice on a channel
    the reader does not use."""
    from core.comm import roster
    agent, sid8, wl = seat
    _set_seat_sha(agent, sid8, "0" * 12)
    text = "\n".join(roster.render_roster(NS))
    assert "stale-code" in text.lower() or "stale code" in text.lower(), (
        f"the operator-facing render must name it:\n{text}")


# --------------------------------------------------------------- P7
def test_p7_the_version_probe_never_breaks_a_heartbeat(monkeypatch):
    """Liveness is load-bearing. A version probe that can kill a heartbeat is worse than
    no version probe -- it converts an observability nicety into an outage."""
    from core.comm import liveness

    import json as _json

    def _boom():
        raise RuntimeError("git is gone")

    monkeypatch.setattr(liveness, "_running_code_sha", _boom)
    agent = f"t114{uuid.uuid4().hex[:6]}"
    wl = liveness.worklive(agent)
    wl.set("thinking")                                   # must not raise
    if liveness._client() is not None:
        rec = _json.loads(liveness._client().get(f"{NS}:worklive:{agent}") or "{}")
        assert rec.get("beat_ts"), "the heartbeat itself must still land"
        for k in liveness._client().scan_iter(match=f"{NS}:*{agent}*", count=200):
            liveness._client().delete(k)
