"""RED fence for the SQLite/WAL cutover.

These tests pin the seven independently reproduced cutover defects plus the
FileStore/SqliteStore parity coverage missing from test_store_differential.py.
They are intentionally not xfailed: the cutover implementation earns green by
making every assertion true.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation import migrate_to_sqlite as migration  # noqa: E402
from core.foundation.sqlite_store import SqliteStore  # noqa: E402
from core.foundation.store import FileStore, HybridStore, RedisStore, create_store  # noqa: E402


def _payload(**overrides):
    data = {
        "kv": {},
        "hash": {},
        "list": {},
        "set": {},
        "zset": {},
        "__expiry__": {},
    }
    data.update(overrides)
    return data


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _main_rc(argv) -> int:
    try:
        return int(migration.main(argv))
    except SystemExit as exc:
        return int(exc.code or 0)


def test_d1_end_to_end_migration_cannot_succeed_with_target_only_data(tmp_path):
    """Success means an exact shadow; an existing target may instead be refused loudly."""
    source_path = tmp_path / "source.json"
    db_path = tmp_path / "target.db"
    _write_json(source_path, _payload(kv={"live": "new"}))

    seeded = SqliteStore(str(db_path))
    seeded.set("live", "old")
    seeded.set("ghost", "stale")
    seeded.close()

    rc = _main_rc(["--json", str(source_path), "--db", str(db_path)])
    result = SqliteStore(str(db_path))
    try:
        exact_shadow = (
            result.get("live") == "new"
            and not result.exists("ghost")
            and set(result.keys("*")) == {"live"}
        )
    finally:
        result.close()

    assert rc != 0 or exact_shadow, (
        "migration returned success while stale target-only data survived"
    )


def test_d2_verify_rejects_and_names_target_only_structures_and_expiry(tmp_path):
    source_path = tmp_path / "source.json"
    db_path = tmp_path / "target.db"
    _write_json(source_path, _payload())

    target = SqliteStore(str(db_path))
    target.set("ghost:kv", "value")
    target.hset("ghost:hash", mapping={"field": "value"})
    target.rpush("ghost:list", "value")
    target.sadd("ghost:set", "value")
    target.zadd("ghost:zset", {"value": 1.0})
    target._conn.execute(
        "INSERT INTO expiry(key, expires_at) VALUES(?, ?)",
        ("ghost:ttl", time.time() + 120),
    )
    target.close()

    ok, problems = migration.verify(source_path, db_path)
    joined = "\n".join(problems)
    expected_names = {
        "ghost:kv",
        "ghost:hash",
        "ghost:list",
        "ghost:set",
        "ghost:zset",
        "ghost:ttl",
    }

    assert not ok, "source-subset equality is not bidirectional verification"
    assert all(name in joined for name in expected_names), (
        f"verification did not name every target-only structure/expiry: {problems!r}"
    )


def test_d3_expired_source_key_is_not_resurrected_permanently(tmp_path):
    source_path = tmp_path / "source.json"
    db_path = tmp_path / "target.db"
    _write_json(
        source_path,
        _payload(
            kv={"expired": "dead"},
            __expiry__={"expired": time.time() - 60},
        ),
    )

    migration.migrate(source_path, db_path)
    target = SqliteStore(str(db_path))
    try:
        value = target.get("expired")
        ttl = target.ttl("expired")
    finally:
        target.close()
    verify_ok, problems = migration.verify(source_path, db_path)

    assert (value, ttl, verify_ok) == (None, -2, True), (
        "logically expired source data must remain absent after migration; "
        f"got value={value!r}, ttl={ttl}, verify={verify_ok}, problems={problems!r}"
    )


def test_d4_advertised_rollback_preserves_post_cutover_write(tmp_path, monkeypatch):
    """The documented rollback is selecting JSON again; post-flip writes must survive it."""
    json_path = tmp_path / "cutover.json"
    monkeypatch.setenv("AKASHIC_STORE_BACKEND", "sqlite")

    selected = create_store(prefer_redis=False, file_path=str(json_path))
    selected.set("post_flip", "must-survive")
    selected.close()

    monkeypatch.delenv("AKASHIC_STORE_BACKEND", raising=False)
    rolled_back = create_store(prefer_redis=False, file_path=str(json_path))
    try:
        value = rolled_back.get("post_flip")
    finally:
        rolled_back.close()

    assert value == "must-survive", (
        "stopping use of SQLite stranded a write made after cutover"
    )


class _AvailabilityProbe:
    def __init__(self, available: bool):
        self.available = available
        self.close_calls = 0

    def is_available(self) -> bool:
        return self.available

    def close(self) -> None:
        self.close_calls += 1


def test_d5_sqlite_selector_reaches_both_hybrid_factory_branches(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_STORE_BACKEND", "sqlite")
    durable_tiers = []

    for available in (False, True):
        cache = _AvailabilityProbe(available)
        monkeypatch.setattr(
            RedisStore,
            "connect",
            classmethod(lambda cls, **kwargs: cache),
        )
        store = create_store(
            prefer_redis=True,
            file_path=str(tmp_path / f"hybrid-{available}.json"),
        )
        durable_tiers.append(store._file)
        store.close()

    assert all(isinstance(tier, SqliteStore) for tier in durable_tiers), (
        "AKASHIC_STORE_BACKEND=sqlite must select SQLite inside HybridStore "
        "whether Redis is available or unavailable"
    )


def test_d6_sqlite_durable_tier_survives_full_hybrid_reconcile(tmp_path):
    cache = FileStore(str(tmp_path / "cache.json"))
    durable = SqliteStore(str(tmp_path / "durable.db"))
    durable.set("kv", "value")
    durable.hset("hash", mapping={"field": "value"})
    durable.rpush("list", "a", "b")
    durable.sadd("set", "a", "b")
    durable.zadd("zset", {"a": 1.0, "b": 2.0})
    durable.setex("leased", 120, "value")
    hybrid = HybridStore(cache, durable)

    try:
        report = hybrid.reconcile()
        observed = {
            "kv": cache.get("kv"),
            "hash": cache.hgetall("hash"),
            "list": cache.lrange("list", 0, -1),
            "set": cache.smembers("set"),
            "zset": cache.zrange("zset", 0, -1, withscores=True),
            "leased": cache.get("leased"),
            "ttl": cache.ttl("leased"),
        }
    finally:
        durable.close()

    assert report["status"] == "success"
    assert observed == {
        "kv": "value",
        "hash": {"field": "value"},
        "list": ["a", "b"],
        "set": {"a", "b"},
        "zset": [("a", 1.0), ("b", 2.0)],
        "leased": "value",
        "ttl": observed["ttl"],
    }
    assert 0 < observed["ttl"] <= 120


class _CloseProbe:
    def __init__(self):
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


def test_d7_hybrid_close_delegates_to_cache_and_sqlite_exactly_once(tmp_path):
    cache = _CloseProbe()
    durable = SqliteStore(str(tmp_path / "durable.db"))
    durable_close_calls = 0
    original_close = durable.close

    def tracked_durable_close():
        nonlocal durable_close_calls
        durable_close_calls += 1
        original_close()

    durable.close = tracked_durable_close
    hybrid = HybridStore(cache, durable)

    try:
        hybrid.close()
        assert (cache.close_calls, durable_close_calls) == (1, 1)
        assert not durable.is_available(), "SQLite connection remained usable after wrapper close"
    finally:
        original_close()


def _normalized_snapshot(snapshot):
    return {
        "kv": snapshot["kv"],
        "hash": snapshot["hash"],
        "list": snapshot["list"],
        "set": {key: sorted(values) for key, values in snapshot["set"].items()},
        "zset": snapshot["zset"],
        "expiry_keys": sorted(snapshot["expiry"]),
    }


def test_file_and_sqlite_complete_snapshot_parity_is_bidirectional(tmp_path):
    """Complete snapshots make source-only and target-only drift equally observable."""
    file_store = FileStore(str(tmp_path / "store.json"))
    sqlite_store = SqliteStore(str(tmp_path / "store.db"))
    operations = [
        ("set", ("kv", "value")),
        ("hset", ("hash",), {"mapping": {"field": "value"}}),
        ("rpush", ("list", "a", "b")),
        ("sadd", ("set", "a", "b")),
        ("zadd", ("zset", {"a": 1.0, "b": 2.0})),
        ("setex", ("leased", 120, "value")),
    ]

    try:
        for operation in operations:
            method, args, *maybe_kwargs = operation
            kwargs = maybe_kwargs[0] if maybe_kwargs else {}
            file_result = getattr(file_store, method)(*args, **kwargs)
            sqlite_result = getattr(sqlite_store, method)(*args, **kwargs)
            assert file_result == sqlite_result

        file_snapshot = _normalized_snapshot(file_store.snapshot())
        sqlite_snapshot = _normalized_snapshot(sqlite_store.snapshot())
        ttl_delta = abs(file_store.ttl("leased") - sqlite_store.ttl("leased"))
    finally:
        sqlite_store.close()

    assert file_snapshot == sqlite_snapshot
    assert ttl_delta <= 1
