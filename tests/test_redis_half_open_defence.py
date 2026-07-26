"""The Redis client must defend against HALF-OPEN connections.

Measured on the kimi wedge, 2026-07-26. Topology:

    runner ──(::1)──> wslrelay (host) ──> WSL/Docker ──> Redis container

kimi held 12 ESTABLISHED sockets that Redis had NO RECORD OF -- zero appeared in CLIENT LIST.
The relay stays alive and keeps ACKing after the container side dies, so the host TCP
connection is genuinely healthy, keepalive succeeds forever, and nothing is ever forwarded.
The main loop sat blocked in xread for 12+ hours while the heartbeat kept reporting a
perfectly live agent.

socket_keepalive CANNOT see this: it is answered by the relay. Only an application-level PING
can, because only Redis can answer one.

SCOPE, stated honestly: health_check_interval covers a connection that goes half-open while
IDLE IN THE POOL -- it is PINGed on next use, raises, and redis-py reconnects. It does NOT
cover a connection that dies WHILE ALREADY BLOCKED in a read. That path is still unexplained
(socket_timeout was set to 6.5s and demonstrably did not fire) and remains open.
"""
import os

import pytest

from core.foundation.redis_connection import connect_to_redis_with_fail_fast


def _client():
    c = connect_to_redis_with_fail_fast(timeout_seconds=3)
    if c is None:
        pytest.skip("Redis unreachable; this pin needs a live server")
    return c


def test_health_check_interval_is_configured():
    """Without this, a pooled connection to a dead peer is reused forever."""
    kw = _client().connection_pool.connection_kwargs
    hc = kw.get("health_check_interval")
    assert hc, (
        "health_check_interval is unset -- a half-open pooled connection would be reused "
        "silently. This is the defect that wedged kimi for 12 hours."
    )
    assert 0 < int(hc) <= 120, f"health check interval {hc}s is outside a useful range"


def test_socket_timeouts_are_bounded():
    """A read must not be able to wait indefinitely."""
    kw = _client().connection_pool.connection_kwargs
    st = kw.get("socket_timeout")
    assert st is not None, "socket_timeout unset -- reads could block forever"
    assert 0 < float(st) <= 60, f"socket_timeout {st}s is too long to fail usefully"


def test_keepalive_alone_is_not_relied_on():
    """Documents WHY keepalive is insufficient, so nobody 'simplifies' the health check away.

    keepalive is answered by whatever terminates the TCP connection. With Docker/WSL that is
    the relay, not Redis -- so keepalive can succeed indefinitely against a peer that can no
    longer reach the server. The health check is the only signal that reaches Redis itself.
    """
    kw = _client().connection_pool.connection_kwargs
    assert kw.get("socket_keepalive"), "keepalive should still be on -- it catches other faults"
    assert kw.get("health_check_interval"), (
        "keepalive is NOT sufficient on its own: it is answered by the relay, not by Redis"
    )
