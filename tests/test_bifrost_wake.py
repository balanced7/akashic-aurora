"""
B-wake2 -- the event-driven wake primitive (Bus.wait).

Bar: wait() returns a pending message immediately (no missed-message race), blocks then wakes on a
NEW message, times out cleanly to [], and DETECTS without consuming (the agent still inbox()es it).

Redis-backed (skip if down). Run: py -m pytest tests/test_bifrost_wake.py -q
"""
import os
import sys
import threading
import time
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


def test_wait_returns_pending_immediately_without_consuming():
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        b = Bus("bob", c, namespace=ns)
        a.send("bob", "chat", "wake up")
        got = b.wait(timeout_ms=2000)               # pending -> returns at once, advance=False
        assert len(got) == 1 and got[0].content == "wake up"
        assert [m.content for m in b.inbox()] == ["wake up"], "detect-only: inbox still delivers it"
    finally:
        _cleanup(c, ns)


def test_wait_times_out_to_empty():
    c, ns = _client(), _ns()
    try:
        b = Bus("bob", c, namespace=ns)
        t0 = time.time()
        assert b.wait(timeout_ms=300) == []
        assert time.time() - t0 < 3.0
    finally:
        _cleanup(c, ns)


def test_wait_wakes_on_a_new_message():
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        b = Bus("bob", c, namespace=ns)
        result = {}

        def waiter():
            result["msgs"] = b.wait(timeout_ms=5000)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.3)                              # block first, then a message arrives
        a.send("bob", "chat", "incoming")
        t.join(6)
        assert result.get("msgs") and result["msgs"][0].content == "incoming"
    finally:
        _cleanup(c, ns)


def test_wait_blocks_past_the_fast_socket_timeout():
    """Regression: the fail-fast client has a ~2-3s socket timeout; a blocking wait() longer than
    that must use a dedicated long-timeout client (else it aborts early and 'wakes' with nothing)."""
    c, ns = _client(), _ns()
    try:
        a = Bus("alice", c, namespace=ns)
        b = Bus("bob", c, namespace=ns)
        result = {}

        def waiter():
            result["m"] = b.wait(timeout_ms=8000)

        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(4.5)                              # well past the ~3s fail-fast socket timeout
        a.send("bob", "chat", "late but here")
        t.join(9)
        assert result.get("m") and result["m"][0].content == "late but here", \
            "wait() must keep blocking past the fast socket timeout"
    finally:
        _cleanup(c, ns)


if __name__ == "__main__":
    print("wake tests run under pytest (need redis)")
