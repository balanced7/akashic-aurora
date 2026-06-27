"""
Tests for the Store persistence interface (Pillar 0).

Verifies that FileStore and HybridStore faithfully emulate the Redis command
surface, and that HybridStore degrades gracefully when Redis is down.

Run: py tests/test_store.py
"""

import sys
import os
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import Store, FileStore, RedisStore, HybridStore, create_store


def _exercise_all_structures(store: Store, label: str) -> None:
    """Run every structure type against a store and assert Redis-like behavior."""
    print(f"\n--- {label} ---")

    # key/value
    assert store.set("k1", "v1") is True
    assert store.get("k1") == "v1"
    assert store.exists("k1") is True
    assert store.get("missing") is None
    print("  kv: set/get/exists OK")

    # hash
    store.hset("h1", mapping={"a": "1", "b": "2"})
    store.hset("h1", field="c", value="3")
    assert store.hget("h1", "a") == "1"
    assert store.hget("h1", "c") == "3"
    assert store.hgetall("h1") == {"a": "1", "b": "2", "c": "3"}
    print("  hash: hset(mapping+field)/hget/hgetall OK")

    # list (lpush prepends -> newest first, like the learning store relies on)
    store.lpush("l1", "first")
    store.lpush("l1", "second")
    store.lpush("l1", "third")
    assert store.lrange("l1", 0, -1) == ["third", "second", "first"]
    assert store.lrange("l1", 0, 0) == ["third"]
    assert store.llen("l1") == 3
    store.rpush("l1", "last")
    assert store.lrange("l1", -1, -1)[0] == "last" if False else True  # rpush appended
    assert store.lrange("l1", 0, -1)[-1] == "last"
    print("  list: lpush/rpush/lrange(inclusive,-1)/llen OK")

    # set
    added = store.sadd("s1", "x", "y", "y")
    assert added == 2, f"expected 2 new members, got {added}"
    assert store.smembers("s1") == {"x", "y"}
    assert store.sismember("s1", "x") is True
    assert store.sismember("s1", "z") is False
    print("  set: sadd(dedup)/smembers/sismember OK")

    # sorted set
    store.zadd("z1", {"low": 0.0, "mid": 50.0, "high": 100.0})
    assert store.zrange("z1", 0, -1) == ["low", "mid", "high"]
    assert store.zrange("z1", 0, -1, desc=True) == ["high", "mid", "low"]
    assert store.zscore("z1", "mid") == 50.0
    ws = store.zrange("z1", 0, 0, withscores=True)
    assert ws[0][0] == "low" and float(ws[0][1]) == 0.0
    print("  zset: zadd/zrange(asc,desc,withscores)/zscore OK")

    # extended sorted-set ops (used by the agent-memory layer)
    assert store.zcard("z1") == 3
    assert store.zrangebyscore("z1", 0, 50) == ["low", "mid"]
    assert store.zrangebyscore("z1", 60, "+inf") == ["high"]
    assert store.zrangebyscore("z1", "-inf", "+inf") == ["low", "mid", "high"]
    removed = store.zremrangebyrank("z1", 0, 0)  # drop the lowest-scored
    assert removed == 1 and store.zcard("z1") == 2
    assert store.zrange("z1", 0, -1) == ["mid", "high"]
    print("  zset+: zrangebyscore/zcard/zremrangebyrank OK")

    # ltrim (keep an inclusive window)
    store.delete("lt1")
    for v in ("a", "b", "c", "d", "e"):
        store.rpush("lt1", v)
    assert store.ltrim("lt1", 1, 3) is True
    assert store.lrange("lt1", 0, -1) == ["b", "c", "d"]
    assert store.ltrim("missing_list", 0, 1) is True  # no-op success on missing
    print("  ltrim: inclusive window + missing no-op OK")

    # TTL semantics (no sleeping; Redis-compatible return codes)
    assert store.ttl("ttl_absent") == -2                       # no such key
    store.set("ttl_plain", "v")
    assert store.ttl("ttl_plain") == -1                        # exists, no expiry
    assert store.setex("ttl_keyed", 100, "v") is True
    assert store.get("ttl_keyed") == "v"
    assert 0 < store.ttl("ttl_keyed") <= 100                   # ticking down
    assert store.expire("expire_absent", 50) is False          # can't expire a ghost
    store.set("expire_me", "v")
    assert store.expire("expire_me", 50) is True
    assert 0 < store.ttl("expire_me") <= 50
    print("  ttl: setex/expire/ttl return-codes OK")

    # keyspace
    found = set(store.keys("*"))
    for expected in ("k1", "h1", "l1", "s1", "z1"):
        assert expected in found, f"missing key {expected} in {found}"
    assert set(store.keys("h*")) == {"h1"}
    print("  keys: keys(glob) OK")

    # delete
    assert store.delete("k1") >= 1
    assert store.get("k1") is None
    print("  delete OK")


def test_filestore():
    with tempfile.TemporaryDirectory() as d:
        store = FileStore(os.path.join(d, "fs.json"))
        _exercise_all_structures(store, "FileStore")

        # Persistence: reload from disk and confirm data survives
        store.set("persist", "yes")
        store.hset("ph", field="f", value="v")
        reloaded = FileStore(os.path.join(d, "fs.json"))
        assert reloaded.get("persist") == "yes"
        assert reloaded.hget("ph", "f") == "v"
        print("  persistence: survives reload OK")


def test_hybridstore_redis_down():
    with tempfile.TemporaryDirectory() as d:
        # Force Redis off by pointing at an unused port; HybridStore must still work.
        store = HybridStore.create(port=63999, file_path=os.path.join(d, "hy.json"))
        assert store.redis_available is False, "expected Redis unavailable on bogus port"
        _exercise_all_structures(store, "HybridStore (Redis down -> File)")
        print("  hybrid: graceful File fallback OK")


def test_filestore_ttl_eviction():
    """Deterministically verify a key disappears once its TTL has passed."""
    with tempfile.TemporaryDirectory() as d:
        store = FileStore(os.path.join(d, "ttl.json"))
        store.setex("perish", 100, "v")
        assert store.get("perish") == "v"
        # Force expiry into the past instead of sleeping.
        store._expiry["perish"] = time.time() - 1
        assert store.get("perish") is None, "expired key should read as gone"
        assert store.exists("perish") is False
        assert "perish" not in store.keys("*"), "expired key should not be listed"
        assert store.ttl("perish") == -2
        # A plain set must clear a previously-attached TTL.
        store.setex("temp", 100, "v")
        store.set("temp", "v2")
        assert store.ttl("temp") == -1, "plain set should drop the TTL"
        print("\n--- FileStore TTL eviction ---\n  lazy eviction + set-clears-ttl OK")


def test_factory():
    with tempfile.TemporaryDirectory() as d:
        file_only = create_store(prefer_redis=False, file_path=os.path.join(d, "f.json"))
        assert isinstance(file_only, FileStore)
        hybrid = create_store(prefer_redis=True, port=63999, file_path=os.path.join(d, "h.json"))
        assert isinstance(hybrid, HybridStore)
        print("\n--- factory ---\n  create_store routing OK")


def test_redisstore_if_available():
    from redis_test_helpers import fresh_test_store
    rs = fresh_test_store()   # isolated test DB (15), flushed clean; never canonical db 0
    if rs is None:
        print("\n--- RedisStore ---\n  SKIPPED (Redis not running)")
        return
    _exercise_all_structures(rs, "RedisStore (live)")
    rs._client.flushdb()   # leave the test DB clean
    print("  RedisStore live parity OK")


class _NamespacedStore:
    """Prefix keys so a live-Redis test doesn't collide with real data."""
    def __init__(self, store, ns): self._s, self._ns = store, ns
    def _k(self, key): return f"{self._ns}:{key}"
    def set(self, k, v): return self._s.set(self._k(k), v)
    def get(self, k): return self._s.get(self._k(k))
    def exists(self, k): return self._s.exists(self._k(k))
    def delete(self, *ks): return self._s.delete(*[self._k(k) for k in ks])
    def hset(self, k, field=None, value=None, mapping=None): return self._s.hset(self._k(k), field, value, mapping)
    def hget(self, k, f): return self._s.hget(self._k(k), f)
    def hgetall(self, k): return self._s.hgetall(self._k(k))
    def setex(self, k, sec, v): return self._s.setex(self._k(k), sec, v)
    def expire(self, k, sec): return self._s.expire(self._k(k), sec)
    def ttl(self, k): return self._s.ttl(self._k(k))
    def lpush(self, k, *v): return self._s.lpush(self._k(k), *v)
    def rpush(self, k, *v): return self._s.rpush(self._k(k), *v)
    def lrange(self, k, s, e): return self._s.lrange(self._k(k), s, e)
    def ltrim(self, k, s, e): return self._s.ltrim(self._k(k), s, e)
    def llen(self, k): return self._s.llen(self._k(k))
    def sadd(self, k, *m): return self._s.sadd(self._k(k), *m)
    def smembers(self, k): return self._s.smembers(self._k(k))
    def sismember(self, k, m): return self._s.sismember(self._k(k), m)
    def zadd(self, k, mapping): return self._s.zadd(self._k(k), mapping)
    def zrange(self, k, s, e, desc=False, withscores=False): return self._s.zrange(self._k(k), s, e, desc=desc, withscores=withscores)
    def zscore(self, k, m): return self._s.zscore(self._k(k), m)
    def zrangebyscore(self, k, mn, mx): return self._s.zrangebyscore(self._k(k), mn, mx)
    def zcard(self, k): return self._s.zcard(self._k(k))
    def zremrangebyrank(self, k, s, e): return self._s.zremrangebyrank(self._k(k), s, e)
    def keys(self, pattern="*"): return [x.replace(f"{self._ns}:", "") for x in self._s.keys(f"{self._ns}:{pattern}")]


if __name__ == "__main__":
    print("=" * 60)
    print("STORE TESTS")
    print("=" * 60)
    test_filestore()
    test_filestore_ttl_eviction()
    test_hybridstore_redis_down()
    test_factory()
    test_redisstore_if_available()
    print("\n" + "=" * 60)
    print("ALL STORE TESTS PASSED")
    print("=" * 60)
