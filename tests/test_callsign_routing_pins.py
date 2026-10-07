"""A CALLSIGN THAT IS NOT AN ADDRESS IS A BLACK HOLE.

THE INCIDENT THAT PRODUCED THESE PINS, 2026-08-20. `doctor`, unprompted:

    vandor: OFFLINE -- 2 unread but the agent is GONE (no worklive, no runner, no wake seat)

Heimdall and Navi had been addressing the RATIFIED CALLSIGN for days. The seat is registered
under the AGENT ID. `residents.get()` maps agent_id -> callsign and there was no reverse; the
bus resolved nothing; so every send was cheerfully ACCEPTED into a Redis stream that no seat
drains and no watcher watches. Delivery succeeded every single time. Arrival never happened.

Two messages were recovered from that stream. The second, sent 13:29 and never read, was
Heimdall handing over the exact fact the out-of-band recovery design most needed -- that
scripts/ops/failsafe_watcher.py already exists and already runs on the one supervisor we do
not have to keep alive ourselves. The design question it answered was asked seven hours later,
by someone who could not hear the answer. That is the cost this file exists to prevent.

The defect is one plane over from R1's costume doctrine (the id is the law, the name is
costume): a name became an IDENTITY without becoming an ADDRESS.

WHAT THESE PINS HOLD:

  P1  the rescue itself -- a ratified callsign routes to its agent id
  P2  AN AGENT ID IS NEVER SHADOWED. The id is the address of record; a colliding callsign
      must not steal a real seat's mail. This is the pin that keeps the fix from becoming a
      worse bug than the one it closes.
  P3  IDEMPOTENCE. bus.send and bus.send_reply are separate paths (send_reply is lane-first
      and does NOT delegate), so resolution is applied at more than one seam. It is only safe
      to do that if resolving twice equals resolving once.
  P4  an unknown name passes through UNCHANGED -- this function rescues known aliases; it must
      never become a new way for mail to fail.
  P5  A STORE OUTAGE RETURNS THE LAST GOOD MAP, never an empty one. An empty map silently
      un-routes every callsign in the fleet, which is precisely the original defect wearing a
      different hat.
  P6  a RETIRED name still routes. `formerly:` is derived from the append-only log; mail to a
      name someone used to carry must reach the person who carried it.
  P7  the bus seam records `addressed_as`, so a callsign send is attributable and not
      silently rewritten.
"""

import time

import pytest

from core.comm.bus import Bus
from core.fleet import residents as R


@pytest.fixture()
def fake_registry(monkeypatch):
    """A known fleet, with the cache pre-warmed so no pin depends on live Redis state."""
    cache = {
        "at": time.time(),
        "alias": {"vandor": "claude", "heimdall": "deepseek", "navi": "kimi"},
        "ids": {"claude", "deepseek", "kimi"},
    }
    monkeypatch.setattr(R, "_ALIAS_CACHE", dict(cache))
    return cache


# ---- P1: the rescue --------------------------------------------------------
def test_p1_a_ratified_callsign_routes_to_its_agent_id(fake_registry):
    assert R.resolve_agent("vandor") == "claude"
    assert R.resolve_agent("Vandor") == "claude", "case is costume too"
    assert R.resolve_agent("HEIMDALL") == "deepseek"
    assert R.resolve_agent("  navi  ") == "kimi", "a typed name carries whitespace"


# ---- P2: the id is the address of record -----------------------------------
def test_p2_an_agent_id_is_never_shadowed_by_a_callsign(monkeypatch):
    """The fix must not become a worse defect than the one it closes: if someone's callsign
    collides with a real agent id, the REAL SEAT keeps its mail."""
    monkeypatch.setattr(R, "_ALIAS_CACHE", {
        "at": time.time(),
        "alias": {"deepseek": "kimi"},          # a hostile/careless collision
        "ids": {"claude", "deepseek", "kimi"},
    })
    assert R.resolve_agent("deepseek") == "deepseek", (
        "a callsign must never steal a live seat's address")


# ---- P3: idempotence, because two seams apply it ---------------------------
def test_p3_resolution_is_idempotent(fake_registry):
    for name in ("vandor", "claude", "heimdall", "deepseek", "stranger", ""):
        once = R.resolve_agent(name)
        assert R.resolve_agent(once) == once, (
            f"{name!r} -> {once!r} must be a fixed point; send and send_reply both resolve")


# ---- P4: never a new way to fail -------------------------------------------
def test_p4_an_unknown_name_passes_through_unchanged(fake_registry):
    assert R.resolve_agent("nobody-here") == "nobody-here"
    assert R.resolve_agent("") == ""
    assert R.resolve_agent(None) is None


# ---- P5: fail-open, and the specific shape of failing open -----------------
def test_p5_a_store_outage_keeps_the_last_good_map(monkeypatch):
    """An empty map is not a safe default -- it un-routes every callsign in the fleet, which
    IS the original defect. Degrade to stale, never to blank."""
    warm = {"at": time.time() - 10_000,          # stale: forces a rebuild attempt
            "alias": {"vandor": "claude"}, "ids": {"claude"}}
    monkeypatch.setattr(R, "_ALIAS_CACHE", dict(warm))

    def _boom():
        raise RuntimeError("redis is down")
    monkeypatch.setattr(R, "_store", _boom)

    assert R.resolve_agent("vandor") == "claude", (
        "a resolver outage must degrade to the last good answer, not to silence")


# ---- P6: a retired name still finds its person -----------------------------
def test_p6_a_formerly_name_still_routes(monkeypatch):
    monkeypatch.setattr(R, "_ALIAS_CACHE", {
        "at": time.time(),
        "alias": {"vandor": "claude", "fives": "claude"},   # 'fives' superseded
        "ids": {"claude"},
    })
    assert R.resolve_agent("fives") == "claude", (
        "supersession is not deletion: mail to a retired name reaches who carried it")


# ---- P7: the bus seam is attributable --------------------------------------
def test_p7_the_bus_records_the_name_that_was_typed(fake_registry):
    """`_resolve_recipient` touches no instance state, so it pins without a live bus."""
    to, meta = Bus._resolve_recipient(object(), "Vandor", {"probe": True})
    assert to == "claude"
    assert meta["addressed_as"] == "Vandor", (
        "a callsign send is rewritten for DELIVERY, never for the record -- the fleet must "
        "still be able to see which name was actually typed")
    assert meta["probe"] is True, "resolution must not eat the caller's meta"

    same, meta2 = Bus._resolve_recipient(object(), "claude", None)
    assert same == "claude" and (meta2 is None or "addressed_as" not in (meta2 or {})), (
        "an unaliased send gains no phantom attribution")
