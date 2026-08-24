"""S2 ROSTER offline pins -- RED first (presence-offline API, the caps-update slice).

WHY: the ladder has no declared departure. A seat that ENDS deliberately renders STALE
for up to WORKLIVE_TTL_S (its last beat was fresh), then flips to DEAD -- a lie in both
directions: STALE says "maybe coming back", DEAD says "died unexplained". The DSH bridge's
--phase offline placeholder just BEATS with phase=offline, which keeps the key alive and
renders the dead seat LIVE -- the worst lie of the three. A declared offline state tells
doctor/router/render the truth: the seat LEFT, on purpose, at a known time.

  O1  IMMEDIATE: go_offline removes the worklive key NOW -- a departing seat must not
      render STALE for the rest of the TTL.
  O2  RENDERED: the seatseen witness carries offline_ts, so the roster renders OFFLINE
      (declared departure) instead of DEAD (unexplained expiry).
  O3  REVERSIBLE: the next heartbeat re-creates the worklive key and the seat is LIVE
      again -- offline is a state, not a tombstone.
  O4  RANKED: by_agent's best-row pick orders OFFLINE above DEAD but below STALE, and
      offline departures never count as churn deaths (churn is crash-loops, not goodbyes).
"""
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NS = f"t383off{uuid.uuid4().hex[:6]}"
AGENT = "claude"
SEAT_A = "aaaa1111"


def _ro():
    from core.comm import roster
    return roster


def _client():
    from core.comm.bus import get_bus
    return get_bus(AGENT)._client


def _mine(ns, ro):
    rows = ro.roster(ns)
    return [r for r in rows if r.get("seat") == f"{AGENT}#{SEAT_A}"]


def test_o1_offline_removes_worklive_immediately():
    ro = _ro()
    ns = NS + "o1"
    ro.heartbeat(ns, AGENT, SEAT_A, phase="building")
    assert _client().exists(f"{ns}:worklive:{AGENT}#{SEAT_A}")
    rep = ro.go_offline(ns, AGENT, SEAT_A)
    assert rep.get("ok"), f"go_offline must report ok: {rep}"
    assert not _client().exists(f"{ns}:worklive:{AGENT}#{SEAT_A}"), (
        "O1: the worklive key must be removed NOW -- a declared departure that lingers "
        "renders STALE for the rest of the TTL, which is a lie about a seat that LEFT")


def test_o2_offline_renders_offline_not_dead():
    ro = _ro()
    ns = NS + "o2"
    ro.heartbeat(ns, AGENT, SEAT_A, phase="building")
    ro.go_offline(ns, AGENT, SEAT_A)
    mine = _mine(ns, ro)
    assert mine and mine[0]["state"] == "OFFLINE", (
        f"O2: a declared departure must render OFFLINE, not DEAD -- DEAD claims an "
        f"unexplained expiry when the seat told us it left: {mine}")


def test_o3_next_heartbeat_revives():
    ro = _ro()
    ns = NS + "o3"
    ro.heartbeat(ns, AGENT, SEAT_A, phase="building")
    ro.go_offline(ns, AGENT, SEAT_A)
    assert _mine(ns, ro)[0]["state"] == "OFFLINE"
    ro.heartbeat(ns, AGENT, SEAT_A, phase="idle")
    mine = _mine(ns, ro)
    assert mine and mine[0]["state"] == "LIVE", (
        f"O3: offline must be reversible -- the next beat re-creates the worklive key and "
        f"the seat is LIVE again, not stuck offline: {mine}")


def test_o4_rank_and_no_churn_from_goodbyes():
    ro = _ro()
    ns = NS + "o4"
    ro.heartbeat(ns, AGENT, SEAT_A, phase="building", _beat_ts=time.time() - 120)
    ro.go_offline(ns, AGENT, SEAT_A, _beat_ts=time.time() - 60)
    groups = ro.by_agent(ro.roster(ns))
    mine = [g for g in groups if g["agent"] == AGENT]
    assert mine and mine[0]["state"] == "OFFLINE", (
        f"O4: the per-agent best row must render OFFLINE for an all-offline agent: {mine}")
    assert mine[0]["deaths_in_window"] == 0 and not mine[0]["churning"], (
        "O4: a declared goodbye must never count as a churn death -- churn flags crash "
        "loops, not departures")
