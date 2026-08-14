"""
Redis Connection: Fail-fast connectivity primitive

Semantic Relationship: Connection gated_by ReachabilityProbe (fail-fast)

THE PROBLEM THIS SOLVES
-----------------------
redis-py's `socket_connect_timeout` is NOT reliably honored on Windows when the
port is filtered/unreachable: the OS performs TCP SYN retransmission across both
IPv6 (::1) and IPv4 (127.0.0.1), stalling the connect for ~48 seconds before
raising. Every module that did `redis.Redis(...).ping()` therefore hangs ~48s
whenever Redis is down (learning store, coordinator, sync coordinator).

THE FIX
-------
Gate the connection with a raw `socket.create_connection()` under our own hard
timeout FIRST. Only if the port is reachable do we hand off to redis-py. This
makes "Redis is down" a fast, predictable failure instead of a 48s stall.

This is the canonical connector. All backends and stores build on it so the
fail-fast guarantee lives in exactly one place.
"""

import os
import time
import socket
import logging
from typing import Optional, Any, Tuple

logger = logging.getLogger("redis_connection")

# Short-lived cache of reachability probes, keyed by (host, port). Without this,
# a startup that builds several Store/Ledger instances probes Redis once PER
# instance -- and when Redis is down each probe pays the full timeout, compounding
# to many seconds. Caching collapses a startup burst to a single probe per endpoint.
_REACHABILITY_CACHE: dict = {}
_REACHABILITY_TTL_SECONDS = 5.0


def clear_reachability_cache() -> None:
    """Forget cached probe results (e.g. after starting/stopping Redis)."""
    _REACHABILITY_CACHE.clear()

try:
    import redis
    REDIS_LIBRARY_AVAILABLE = True
except ImportError:
    REDIS_LIBRARY_AVAILABLE = False


def _resolve_default_redis_endpoint() -> Tuple[str, int]:
    """
    The single source of truth for "where is Redis?", resolved once.

    Semantic Relationship: RedisEndpoint derived_from Config (single authority)

    Priority: REDIS_HOST/REDIS_PORT env vars > config.py (the declared SSOT) >
    a safe fallback. This is why the foundation must NOT hardcode a port: callers
    that want a different endpoint set it in ONE place (config.py / env), and the
    whole stack follows -- no split-brain where writes go to a read-only replica.

    NOTE (topology, 2026-06-19): config.py declares 6380 the master; but
    services/redis_ha_manager.py declares 6379 the master. They contradict.
    Resolve the real topology and set it in config.py -- everything reads from here.
    """
    # Base = config.py (the SSOT); env vars override PER FIELD, so setting just
    # REDIS_PORT (or just REDIS_HOST) works. Fallback if config is unimportable.
    try:
        from config import REDIS_HOST as host, REDIS_PORT as port
    except Exception:
        host, port = "localhost", 6380

    # W156 (2026-08-14): the port is a property of the WORLD this checkout is, not of
    # a tracked constant. Measured that morning: a clean clone at E:/AI-Setup-Alpha
    # resolved its own repo root correctly and still dialled 16379 -- prod, 19,850 live
    # keys. A clone of Aurora was a second BODY on the SAME BRAIN. config stays the
    # fallback so an UNKNOWN checkout still reads; env still wins below, because the
    # suite and every ad-hoc probe steer with REDIS_PORT and demoting that would break
    # test isolation in order to add world isolation.
    try:
        from core.world import current as _world
        w = _world()
        if w.redis_port is not None:
            port = w.redis_port
        else:
            # Loud, never silent: silence here is the original defect in a new coat.
            print(f"[world] UNKNOWN checkout -- {w.why}; falling back to config "
                  f"REDIS_PORT={port}. Declare it: echo alpha > .aurora-world")
    except Exception as exc:                     # pragma: no cover - import guard
        print(f"[world] unresolved ({exc.__class__.__name__}); using config REDIS_PORT={port}")

    env_host, env_port = os.getenv("REDIS_HOST"), os.getenv("REDIS_PORT")
    if env_host:
        host = env_host
    if env_port and env_port.isdigit():
        port = int(env_port)
        # W156 guard, wired HERE and nowhere else because this is the ONLY path that can
        # point a twin at another world: the world resolver cannot produce a foreign port,
        # so an env override is the whole attack surface (a stale shell, a copied command,
        # a REDIS_PORT exported for one probe and never unset).
        #
        # Fires only when the port belongs to a DIFFERENT REGISTERED world. An unregistered
        # port stays silent on purpose -- the suite and every ad-hoc probe steer with
        # throwaway ports, and a guard that fought them would be disabled within a week.
        #
        # IT REFUSES THE OVERRIDE; IT DOES NOT RAISE. This resolver runs at module import
        # (DEFAULT_REDIS_PORT is computed at import time), and core/paths.py already wrote
        # the rule for this exact position: "a path helper that throws during import takes
        # down every door that imports it." A stale REDIS_PORT=16379 in one shell would
        # otherwise turn every command in the twin into an ImportError.
        #
        # So the safe branch is taken, loudly: drop the foreign override, keep the world's
        # own endpoint, and say both. The danger being prevented is a twin WRITING to prod;
        # declining the override removes that danger completely while leaving the process
        # alive, which a raise does not.
        try:
            from core.world import current, owner_of_port
            if owner_of_port(port) is not None:
                w = current()
                try:
                    w.assert_owns_port(port)
                except Exception as refusal:
                    print(f"[world] IGNORING REDIS_PORT={port}: {refusal}")
                    port = w.redis_port if w.redis_port is not None else port
        except ImportError:                          # pragma: no cover - import guard
            pass
    return host, port


DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT = _resolve_default_redis_endpoint()


def _resolve_default_redis_db() -> int:
    """Which logical DB? env REDIS_DB > config.REDIS_DB > 0. Tests set REDIS_DB=15
    so they run on an isolated DB and never touch canonical data on db 0."""
    env_db = os.getenv("REDIS_DB")
    if env_db and env_db.isdigit():
        return int(env_db)
    try:
        from config import REDIS_DB
        return REDIS_DB
    except Exception:
        return 0


DEFAULT_REDIS_DB = _resolve_default_redis_db()


def probe_redis_reachable(
    host: str = DEFAULT_REDIS_HOST,
    port: int = DEFAULT_REDIS_PORT,
    timeout_seconds: float = 0.5,
) -> bool:
    """
    Probe whether a Redis port is reachable, fail-fast.

    Semantic Relationship: Probe reports_reachability_of RedisPort

    Uses a raw socket connect bounded by our own timeout, so an unreachable
    host fails in `timeout_seconds` per resolved address (not ~48s). The default
    is short (0.5s): a live localhost Redis answers in well under a millisecond,
    so 0.5s is ample headroom while keeping the Redis-down path fast. A rare
    false "down" just falls back to File this once (re-probed after the cache TTL).

    Args:
        host: Redis host to probe
        port: Redis port to probe
        timeout_seconds: Hard per-address connect timeout (default 0.5s)

    Returns:
        True if the port accepted a TCP connection, False otherwise.
    """
    key = (host, port)
    cached = _REACHABILITY_CACHE.get(key)
    if cached is not None and (time.monotonic() - cached[0]) < _REACHABILITY_TTL_SECONDS:
        return cached[1]
    try:
        sock = socket.create_connection((host, port), timeout=timeout_seconds)
        sock.close()
        result = True
    except Exception as e:
        logger.debug(f"Redis not reachable at {host}:{port}: {type(e).__name__}: {e}")
        result = False
    _REACHABILITY_CACHE[key] = (time.monotonic(), result)
    return result


def connect_to_redis_with_fail_fast(
    host: str = DEFAULT_REDIS_HOST,
    port: int = DEFAULT_REDIS_PORT,
    timeout_seconds: float = 2.0,
    decode_responses: bool = True,
    probe_timeout_seconds: float = 0.5,
    db: int = DEFAULT_REDIS_DB,
) -> Optional[Any]:
    """
    Connect to Redis, returning a live client or None — never hangs.

    Semantic Relationship: Client derives_from ReachableRedis (or None)

    Order of operations:
    1. If redis-py isn't installed -> None.
    2. Raw-socket reachability probe (fast, fail-fast) -> if unreachable, None.
    3. Build the redis client and confirm with PING -> client or None.

    Two distinct timeouts on purpose: the reachability *probe* is short
    (`probe_timeout_seconds`, default 0.5s) so a Redis-down startup is fast, while
    the redis client's *socket* timeouts use `timeout_seconds` (default 2s) so real
    operations on a live Redis aren't made fragile.

    Args:
        host: Redis host
        port: Redis port
        timeout_seconds: Socket timeouts for the live redis client's operations
        decode_responses: Pass-through to redis-py (default True for str values)
        probe_timeout_seconds: Hard timeout for the reachability probe (default 0.5s)

    Returns:
        A connected redis.Redis client, or None if Redis is unavailable.
    """
    if not REDIS_LIBRARY_AVAILABLE:
        logger.debug("redis library not installed; skipping connection")
        return None

    if not probe_redis_reachable(host, port, probe_timeout_seconds):
        return None

    try:
        client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=decode_responses,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
            socket_keepalive=True,
            # HALF-OPEN DEFENCE (2026-07-26). PING a pooled connection that has been idle
            # this long before reusing it; a dead one raises and redis-py reconnects.
            #
            # Why socket_keepalive above is NOT enough, measured on the kimi wedge: our Redis
            # runs in Docker/WSL, so a client connects to `wslrelay` on the host and the relay
            # forwards to the container. When the container side dies, the relay stays alive
            # and keeps ACKing -- so the host TCP connection is genuinely healthy and keepalive
            # succeeds forever, while nothing is forwarded. Evidence: kimi held 12 ESTABLISHED
            # sockets that Redis had NO record of (zero in CLIENT LIST), and its main loop sat
            # blocked in xread for 12+ hours. Keepalive cannot see this; only an
            # application-level PING can, because only Redis can answer it.
            health_check_interval=int(
                os.getenv("AKASHIC_REDIS_HEALTH_CHECK_SEC", "30") or 30),
        )
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis reachable but PING failed at {host}:{port}: {e}")
        return None
