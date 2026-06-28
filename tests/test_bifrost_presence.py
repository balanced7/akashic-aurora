"""
Slice B3 (doors) -- presence + the MCP door tools.

Bar: agents that use the bus appear online (and expire when idle); presence is empty when offline;
and the MCP server (ai_setup_mcp.py, the door Cursor connects to) still imports cleanly with the
new bifrost_* tools registered.

Presence tests use real Redis (skip if down); the offline + MCP-import tests need no Redis.
Run: py -m pytest tests/test_bifrost_presence.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus


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


def _cleanup(c, ns):
    keys = c.keys(f"{ns}:*")
    if keys:
        c.delete(*keys)


def test_presence_offline_is_empty():
    b = Bus("x", client="dummy")
    b._client = None
    assert b.register() is False
    assert b.presence() == []


def test_mcp_server_imports_with_bifrost_tools():
    import ai_setup_mcp
    for t in ("bifrost_send", "bifrost_broadcast", "bifrost_inbox", "bifrost_presence"):
        assert hasattr(ai_setup_mcp, t), f"MCP tool {t} missing from the door"


def test_register_and_list():
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        b = Bus("bob", c, namespace=ns)
        assert a.register() and b.register()
        assert {p["agent"] for p in a.presence()} == {"alice", "bob"}
    finally:
        _cleanup(c, ns)


def test_using_the_bus_marks_you_online():
    c, ns = _client(), _ns()
    try:
        alice = Bus("alice", c, namespace=ns)
        bob = Bus("bob", c, namespace=ns)
        alice.send("bob", "chat", "hi")       # sending marks alice online
        bob.inbox()                            # reading marks bob online
        online = {p["agent"] for p in alice.presence()}
        assert "alice" in online and "bob" in online
    finally:
        _cleanup(c, ns)


def test_presence_expires(monkeypatch=None):
    """A short TTL means an idle agent drops off (the dead-inbox guard from the plan)."""
    c, ns = _client(), _ns()
    try:
        ghost = Bus("ghost", c, namespace=ns)
        ghost.register(ttl=1)
        assert "ghost" in {p["agent"] for p in ghost.presence()}
        import time
        time.sleep(1.2)
        assert "ghost" not in {p["agent"] for p in ghost.presence()}, "idle agent must expire"
    finally:
        _cleanup(c, ns)


def test_presence_carries_agent_card():
    c, ns = _client(), _ns()
    try:
        card = {"runtime_class": "api", "wake_mode": "runner", "door": "runner", "caps": ["review"]}
        g = Bus("gemini", c, namespace=ns, promote=False)
        g.register(card=card)
        rec = [p for p in g.presence() if p["agent"] == "gemini"][0]
        assert rec["runtime_class"] == "api" and rec["wake_mode"] == "runner"
        assert rec["door"] == "runner" and rec["caps"] == ["review"] and rec["last_seen"]
        g.send("someone", "chat", "hi")                  # an auto-touch heartbeat...
        rec2 = [p for p in g.presence() if p["agent"] == "gemini"][0]
        assert rec2["runtime_class"] == "api", "the card survives the auto-touch heartbeat"
    finally:
        _cleanup(c, ns)


def test_presence_backward_compat_bare_timestamp():
    c, ns = _client(), _ns()
    try:
        c.set(f"{ns}:presence:legacy", "2026-06-28T00:00:00", ex=60)   # old-style bare ts
        rec = [p for p in Bus("x", c, namespace=ns).presence() if p["agent"] == "legacy"][0]
        assert rec["last_seen"] == "2026-06-28T00:00:00" and "runtime_class" not in rec
    finally:
        _cleanup(c, ns)


if __name__ == "__main__":
    test_presence_offline_is_empty()
    test_mcp_server_imports_with_bifrost_tools()
    print("offline + MCP-import tests passed; redis presence tests run under pytest")
