"""
Test isolation for live-Redis tests.

Live tests must NEVER touch canonical data on db 0. These helpers hand back a
RedisStore / RedisLedger bound to the dedicated TEST logical DB (config.REDIS_TEST_DB,
default 15), flushed clean first. If Redis is down they return None so the caller skips.

This is the root-cause fix for the 2026-06-20 incident where running the suite against
the live Redis polluted the real knowledge store.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import REDIS_TEST_DB
from core.foundation.redis_connection import (
    DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT, probe_redis_reachable,
)
from core.foundation.store import RedisStore
from core.foundation.ledger import RedisLedger


def redis_up() -> bool:
    return probe_redis_reachable(DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)


def fresh_test_store():
    """A RedisStore on the isolated test DB, flushed clean. None if Redis is down."""
    if not redis_up():
        return None
    rs = RedisStore.connect(timeout_seconds=2.0, db=REDIS_TEST_DB)
    if not rs.is_available():
        return None
    rs._client.flushdb()   # safe: this is the tests-only DB, never canonical db 0
    return rs


def fresh_test_ledger():
    """A RedisLedger on the isolated test DB, flushed clean. None if Redis is down."""
    if not redis_up():
        return None
    rl = RedisLedger.connect(timeout_seconds=2.0, db=REDIS_TEST_DB)
    if not rl.is_available():
        return None
    rl._client.flushdb()
    return rl
