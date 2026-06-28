"""Optimistic compare-and-set on the Store (Concurrency design C3).

CAS is the lost-update guard: two agents read the same key, both compute a new value,
and the second writer is rejected instead of silently clobbering the first. Also the
mechanism that converges Redis/File in HybridStore. Tested hermetically on FileStore
(authoritative semantics), with a guarded live-Redis pass for the Lua path.

Run: py -m pytest tests/test_store_cas.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore, RedisStore, HybridStore, CASConflict


@pytest.fixture
def store(tmp_path):
    return FileStore(path=str(tmp_path / "cas.json"))


# ------------------------------------------------------------------- basic CAS
def test_cas_from_absent_then_value(store):
    assert store.cas("k", None, "v1") is True          # create-if-absent
    assert store.cas("k", None, "v2") is False          # already exists
    assert store.get("k") == "v1"


def test_cas_matches_expected(store):
    store.set("k", "a")
    assert store.cas("k", "a", "b") is True
    assert store.get("k") == "b"
    assert store.cas("k", "a", "c") is False            # stale expected -> rejected
    assert store.get("k") == "b"


# ----------------------------------------------------- the lost-update scenario
def test_lost_update_is_prevented(store):
    store.set("counter", "0")
    # two agents read the SAME starting value
    a_seen = store.get("counter")
    b_seen = store.get("counter")
    assert a_seen == b_seen == "0"
    # agent A writes first, with its expected
    assert store.cas("counter", a_seen, "1") is True
    # agent B's write is based on the now-stale value -> rejected (no silent clobber)
    assert store.cas("counter", b_seen, "1") is False
    assert store.get("counter") == "1"


def test_update_atomic_increments(store):
    store.set("n", "0")
    out = store.update_atomic("n", lambda cur: int(cur) + 1)
    assert out == "1" and store.get("n") == "1"


def test_update_atomic_noop_when_fn_returns_none(store):
    store.set("n", "7")
    assert store.update_atomic("n", lambda cur: None) == "7"
    assert store.get("n") == "7"


def test_update_atomic_raises_on_relentless_conflict(store):
    store.set("n", "0")
    calls = {"i": 0}

    def fn(cur):
        # simulate a peer winning the race on every attempt: bump the key before we cas
        calls["i"] += 1
        store.set("n", f"peer-{calls['i']}")
        return "mine"

    with pytest.raises(CASConflict):
        store.update_atomic("n", fn, retries=3)


# ----------------------------------------------------- Hybrid (Redis down -> File)
def test_hybrid_cas_uses_file_when_redis_down(tmp_path):
    h = HybridStore(None, FileStore(path=str(tmp_path / "h.json")))
    assert h.cas("k", None, "v1") is True
    assert h.cas("k", "v1", "v2") is True
    assert h.cas("k", "v1", "v3") is False              # stale -> rejected
    assert h.get("k") == "v2"


# ----------------------------------------------------- live Redis (isolated test DB 15)
def test_redis_cas_atomic_lua_path():
    from redis_test_helpers import fresh_test_store
    rs = fresh_test_store()          # db 15, flushed -- NEVER canonical db 0
    if rs is None:
        pytest.skip("Redis not available")
    key = f"test:cas:{uuid.uuid4().hex}"
    assert rs.cas(key, None, "v1") is True          # NX create
    assert rs.cas(key, None, "v2") is False
    assert rs.cas(key, "v1", "v2") is True           # Lua compare
    assert rs.cas(key, "v1", "v3") is False          # stale
    assert rs.get(key) == "v2"
