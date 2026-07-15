"""
Slice B0 -- the Bifrost transport bus.

Bar: a BROADCAST reaches ALL agents (the old shared-consumer-group bug is gone); a DIRECT message
reaches exactly one; the per-agent cursor advances (no re-delivery); the bus connects on the
CANONICAL port (not the old hardcoded 6379); and offline is EXPLICIT (no silent swallow).

Redis-backed tests use the real Redis in a throwaway namespace and skip if it's down; the offline
test needs no Redis. Run: py -m pytest tests/test_bifrost_bus.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus, Message


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_test_{uuid.uuid4().hex[:8]}"


def _cleanup(client, ns):
    keys = client.keys(f"{ns}:*")
    if keys:
        client.delete(*keys)


# ----------------------------------------------------------------- offline (no Redis needed)
def test_offline_is_explicit():
    b = Bus("x", client="dummy")      # any non-None client bypasses the real connect
    b._client = None                  # force offline
    assert b.online is False
    assert b.send("y", "chat", "hi") is None
    assert b.broadcast("k", "c") is None
    assert b.inbox() == []
    assert b.status()["online"] is False


# ----------------------------------------------------------------- redis-backed
def test_bus_connects_on_canonical_port():
    _client()                          # skip if down
    assert Bus("probe", client=None).online is True   # default path uses the canonical connector


def test_direct_delivery_reaches_one():
    c, ns = _client(), _ns()
    try:
        alice = Bus("alice", c, namespace=ns)
        bob = Bus("bob", c, namespace=ns)
        carol = Bus("carol", c, namespace=ns)
        mid = alice.send("bob", "chat", {"hi": "bob"})
        assert mid
        got = bob.inbox()
        assert len(got) == 1 and got[0].frm == "alice" and got[0].to == "bob"
        assert got[0].content == {"hi": "bob"}
        assert carol.inbox() == [], "a direct message must not reach a third agent"
    finally:
        _cleanup(c, ns)


def test_broadcast_reaches_all_but_not_sender():
    c, ns = _client(), _ns()
    try:
        alice = Bus("alice", c, namespace=ns)
        bob = Bus("bob", c, namespace=ns)
        dave = Bus("dave", c, namespace=ns)
        alice.broadcast("announce", {"news": "ship it"})
        for agent in (bob, dave):
            got = agent.inbox()
            assert len(got) == 1 and got[0].kind == "announce" and got[0].to == "*", \
                "EVERY agent must see the broadcast (the fan-out fix)"
        assert alice.inbox() == [], "the sender must not receive its own broadcast"
    finally:
        _cleanup(c, ns)


def test_cursor_advances_no_redelivery():
    c, ns = _client(), _ns()
    try:
        alice = Bus("alice", c, namespace=ns)
        bob = Bus("bob", c, namespace=ns)
        alice.send("bob", "chat", "m1")
        alice.send("bob", "chat", "m2")
        assert [m.content for m in bob.inbox()] == ["m1", "m2"]
        assert bob.inbox() == [], "already-read messages must not re-deliver"
        alice.send("bob", "chat", "m3")
        assert [m.content for m in bob.inbox()] == ["m3"], "only the new message is delivered"
    finally:
        _cleanup(c, ns)


def test_pending_does_not_consume():
    c, ns = _client(), _ns()
    try:
        alice = Bus("alice", c, namespace=ns)
        bob = Bus("bob", c, namespace=ns)
        alice.send("bob", "chat", "x")
        alice.broadcast("note", "y")
        assert bob.pending() == 2          # direct + broadcast, no consume
        assert len(bob.inbox()) == 2
        assert bob.pending() == 0          # now consumed
    finally:
        _cleanup(c, ns)


def test_content_and_meta_roundtrip():
    c, ns = _client(), _ns()
    try:
        a = Bus("a", c, namespace=ns)
        b = Bus("b", c, namespace=ns)
        a.send("b", "handoff", {"task": [1, 2, 3], "n": 4.5}, meta={"prio": "high"})
        m = b.inbox()[0]
        assert m.content == {"task": [1, 2, 3], "n": 4.5}
        # T073 Phase 1 (@9d04797): transport stamps frm_incarnation into meta,
        # diagnostic-only. The contract is sender meta RIDES THROUGH UNCHANGED
        # plus the stamp -- not exact equality (stale pre-T073 assert).
        assert m.meta.get("prio") == "high" and m.kind == "handoff"
        assert m.meta.get("frm_incarnation", "").startswith("a:"), \
            "transport must stamp the sender's incarnation (T073 Phase 1)"
    finally:
        _cleanup(c, ns)


if __name__ == "__main__":
    test_offline_is_explicit()
    print("offline test passed; redis-backed tests run under pytest")
