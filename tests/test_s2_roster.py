"""S2 ROSTER pins -- RED first (M3). The lobby: per-seat liveness the whole fleet can read.

Design: build-queue synthesis S2 (Daniel-gated) + kimi's fence position P1 (the heartbeat
must be PROVABLY LIVE -- freshness-windowed, never replayed) + W84 (every diagnostic renders
checked / NOT-checked) + T5 (the directory carries no payload).

WHY: the reaper (S4) triggers on "heartbeat TTL expired" and TONIGHT NO CLAUDE SEAT
PUBLISHES A HEARTBEAT AT ALL -- the roster is the reaper's only sensor, the router's input
for bare-role mail, and the UI's honesty about who is actually reachable (Sol rendered
"sleeping" precisely because nothing touched its presence between turns).

  P1  PROVABLY-LIVE (kimi): a beating seat renders LIVE; a seat whose beat is OLDER than
      the freshness window renders STALE even while its key still exists. Key-exists is
      not alive; recent-beat is alive.
  P2  DEAD: no key (or TTL-expired) renders DEAD/absent -- never LIVE by default.
  P3  W84 CONTRACT: the roster render names WHAT IT CHECKED and WHAT IT DID NOT. A roster
      that cannot confess its blind spots is unwedge all over again.
  P4  HAVE-SUMMARY (T3, torrent bitfield): each row carries the seat's consumed-through
      positions so a successor can DIFF a dead seat's inventory instead of guessing.
  P5  MONOTONIC BEAT: heartbeat() never writes a beat_ts older than the stored one (a
      replayed/duplicated beat cannot resurrect a stale seat -- kimi's never-replayed half).
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NS = f"t108ro{uuid.uuid4().hex[:6]}"
AGENT = "claude"
SEAT_A = "aaaa1111"
SEAT_B = "bbbb2222"


def _ro():
    from core.comm import roster
    return roster


def _client():
    from core.comm.bus import get_bus
    return get_bus(AGENT)._client


def test_p1_provably_live_vs_stale():
    ro = _ro()
    ro.heartbeat(NS, AGENT, SEAT_A, phase="building")
    rows = ro.roster(NS)
    mine = [r for r in rows if r.get("seat") == f"{AGENT}#{SEAT_A}"]
    assert mine and mine[0]["state"] == "LIVE", f"fresh beat must render LIVE: {mine}"
    # Replay the same seat with an ANCIENT beat via the raw key (simulating a stale key
    # that has not yet TTL'd): state must be STALE, not LIVE. Key-exists != alive.
    ro.heartbeat(NS, AGENT, SEAT_B, phase="idle", _beat_ts=time.time() - 3600)
    rows = ro.roster(NS)
    other = [r for r in rows if r.get("seat") == f"{AGENT}#{SEAT_B}"]
    assert other and other[0]["state"] == "STALE", (
        f"a beat older than the freshness window must render STALE even while the key "
        f"exists -- key-exists is not alive (kimi P1): {other}")


def test_p2_dead_seat_never_live():
    ro = _ro()
    rows = ro.roster(NS + "d")
    assert all(r.get("state") != "LIVE" for r in rows), (
        f"an empty namespace must contain no LIVE seats: {rows}")


def test_p3_w84_contract_in_render():
    ro = _ro()
    ro.heartbeat(NS + "w", AGENT, SEAT_A, phase="idle")
    lines = ro.render_roster(NS + "w")
    joined = "\n".join(lines).lower()
    assert "checked" in joined and "not checked" in joined, (
        "W84: the roster must render what it CHECKED and what it did NOT -- a roster that "
        "cannot confess its blind spots is unwedge all over again:\n" + "\n".join(lines))


def test_p4_have_summary_present():
    ro = _ro()
    ro.heartbeat(NS + "h", AGENT, SEAT_A, phase="building")
    rows = ro.roster(NS + "h")
    mine = [r for r in rows if r.get("seat") == f"{AGENT}#{SEAT_A}"]
    assert mine and "have" in mine[0], (
        f"each row carries the seat's consumed-through positions (torrent bitfield, T3) so "
        f"a successor can DIFF a dead seat's inventory: {mine}")


def test_p5_replayed_beat_cannot_resurrect():
    ro = _ro()
    ns = NS + "m"
    ro.heartbeat(ns, AGENT, SEAT_A, phase="building")
    fresh = ro.roster(ns)[0]["beat_ts"]
    ro.heartbeat(ns, AGENT, SEAT_A, phase="building", _beat_ts=time.time() - 3600)
    after = ro.roster(ns)[0]["beat_ts"]
    assert float(after) >= float(fresh), (
        "MONOTONIC BEAT violated: a replayed/older heartbeat overwrote a fresher one -- a "
        "replay could resurrect a stale seat or mask a death (kimi P1, never-replayed half)")


def test_p6_just_died_seat_renders_dead_not_absent():
    """kimi F1: an expired worklive key made a seat VANISH -- dead indistinguishable from
    never-existed, the confident-zero in the reaper's own sensor. A seat that has EVER
    beaten must render DEAD (with its last beat age) after its worklive expires."""
    ro = _ro()
    ns = NS + "x"
    ro.heartbeat(ns, AGENT, SEAT_A, phase="building")
    # simulate expiry: delete the worklive key (TTL reaping), leaving history only
    _client().delete(f"{ns}:worklive:{AGENT}#{SEAT_A}")
    rows = ro.roster(ns)
    mine = [r for r in rows if r.get("seat") == f"{AGENT}#{SEAT_A}"]
    assert mine and mine[0]["state"] == "DEAD", (
        f"JUST-DIED SEAT INVISIBLE: worklive expired and the seat vanished from the roster "
        f"instead of rendering DEAD -- absence-as-dead is fine for the reaper's predicate, "
        f"never for the render's claim (kimi F1). rows={rows}")


def test_p7_have_summary_reads_through_the_bus_door():
    """kimi F2: have-summaries were built from RAW hgetall on hardcoded key strings --
    duplicated key-format knowledge and an unverified read stamped into the inventory a
    successor diffs against (T1). The seat-cursor half must agree with the Bus's own
    door-derived read after a real slice-1 consume."""
    import os as _os
    from core.comm.bus import Bus
    ro = _ro()
    ns = NS + "b"
    sender = Bus("deepseek", namespace=ns)
    if not sender.online:
        print("SKIPPED (Redis not running)")
        return
    sender.send(AGENT, "note", "seat-mail", meta={"to_incarnation": SEAT_A})
    _os.environ["BIFROST_INCARNATION"] = SEAT_A
    _os.environ["CLAUDE_CODE_SESSION_ID"] = SEAT_A
    b = Bus(AGENT, namespace=ns)
    b.inbox(advance=True)                       # real consume advances the seat cursor
    ro.heartbeat(ns, AGENT, SEAT_A, phase="sync")
    rows = ro.roster(ns)
    mine = [r for r in rows if r.get("seat") == f"{AGENT}#{SEAT_A}"][0]
    door_val = str(b._client.hget(b._seat_cursor_key(SEAT_A), "seat") or "0")
    assert str(mine["have"].get("seat_inbox")) == door_val != "0", (
        f"HAVE-SUMMARY DOOR MISMATCH: roster's seat_inbox={mine['have'].get('seat_inbox')} "
        f"vs the Bus door's {door_val} -- the bitfield must be built through the organ that "
        f"owns the key, not a raw parallel format (kimi F2 / T1).")


def test_p8_live_window_derives_from_the_seats_own_cadence():
    """kimi F3: FRESH_S=45 was an unjustified dial -- a wedged loop renders LIVE for 45s.
    LIVE's window must derive from the seat's OWN observed cadence: a seat beating every
    ~2s whose last beat is 20s old is STALE (20 >> 2x cadence), even though 20 < 45."""
    ro = _ro()
    ns = NS + "c"
    base = time.time() - 30
    for i in range(6):                          # establish ~2s cadence, ending 20s ago
        ro.heartbeat(ns, AGENT, SEAT_A, phase="building", _beat_ts=base + i * 2)
    rows = ro.roster(ns)
    mine = [r for r in rows if r.get("seat") == f"{AGENT}#{SEAT_A}"][0]
    assert mine["state"] == "STALE", (
        f"LIVE OVERCLAIMS (kimi F3): seat cadence ~2s, last beat ~20s ago, and the roster "
        f"still says {mine['state']} because a fixed 45s dial ignores the seat's own "
        f"rhythm. The false-LIVE window must be bounded by the seat's real cadence. {mine}")


if __name__ == "__main__":
    test_p1_provably_live_vs_stale()
    test_p2_dead_seat_never_live()
    test_p3_w84_contract_in_render()
    test_p4_have_summary_present()
    test_p5_replayed_beat_cannot_resurrect()
    print("PASS")
