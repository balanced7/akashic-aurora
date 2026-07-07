"""
Tests for HybridStore's Redis<->File reconciliation -- the surviving healing logic (the old
StoreReconciler wrapper + RedisSyncCoordinator facade were retired 2026-07-07; the capability is now
wired into cold-start boot, agent_cli cmd_boot).

Run: py tests/test_sync_reconciler.py
"""

import sys
import os
import tempfile

# Full test isolation BEFORE any foundation import: FILE store -> throwaway AI_SETUP dir, REDIS -> db 15.
_TMP_AI_SETUP = tempfile.mkdtemp(prefix="aisetup_test_")
os.makedirs(os.path.join(_TMP_AI_SETUP, "session_logs"), exist_ok=True)
os.environ["AI_SETUP"] = _TMP_AI_SETUP
os.environ.setdefault("REDIS_DB", "15")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore, RedisStore, HybridStore


def test_reconcile_redis_down():
    """With Redis down, check_drift reports it and reconcile is a safe no-op (File is already truth)."""
    with tempfile.TemporaryDirectory() as d:
        store = HybridStore.create(port=63999, file_path=os.path.join(d, "s.json"))
        assert store.redis_available is False
        drift = store.check_drift()
        assert drift["redis_available"] is False and drift["in_sync"] is False
        report = store.reconcile()
        assert report["status"] == "skipped"
        print("\n--- reconcile (Redis down) ---\n  safe no-op + drift report OK")


def test_reconcile_backfill_if_redis():
    """If Redis is up, check_drift detects File-ahead divergence and reconcile backfills Redis --
    exactly the drift-then-reconcile path the boot cold-start safety net runs."""
    rs = RedisStore.connect(timeout_seconds=2.0)
    if not rs.is_available():
        print("\n--- reconcile backfill ---\n  SKIPPED (Redis not running)")
        return
    import time
    ns = f"recon:{int(time.time())}"
    with tempfile.TemporaryDirectory() as d:
        fs = FileStore(os.path.join(d, "s.json"))
        # Seed the File backend with each structure type (Redis is empty of these keys).
        fs.set(f"{ns}:kv", "v")
        fs.hset(f"{ns}:h", mapping={"a": "1"})
        fs.rpush(f"{ns}:l", "x", "y")
        fs.sadd(f"{ns}:s", "m")
        fs.zadd(f"{ns}:z", {"mem": 5.0})
        hybrid = HybridStore(rs, fs)
        # the boot port's TRIGGER: drift must show these keys missing_in_redis
        drift_before = hybrid.check_drift()
        assert any(k.startswith(ns) for k in drift_before["missing_in_redis"]), drift_before
        report = hybrid.reconcile()
        assert report["status"] == "success", report
        # Redis now mirrors the File data.
        assert rs.get(f"{ns}:kv") == "v"
        assert rs.hget(f"{ns}:h", "a") == "1"
        assert rs.lrange(f"{ns}:l", 0, -1) == ["x", "y"]
        assert rs.sismember(f"{ns}:s", "m")
        assert rs.zscore(f"{ns}:z", "mem") == 5.0
        for k in rs.keys(f"{ns}*"):
            rs.delete(k)
        print(f"\n--- reconcile backfill (live Redis) ---\n  drift detected -> backfilled {report['written']} OK")


def main():
    print("=" * 60 + "\nHYBRIDSTORE RECONCILE TESTS\n" + "=" * 60)
    test_reconcile_redis_down()
    test_reconcile_backfill_if_redis()
    _teardown()
    print("\n" + "=" * 60 + "\nALL RECONCILE TESTS PASSED\n" + "=" * 60)


def _teardown():
    import shutil
    try:
        from redis_test_helpers import fresh_test_store
        fresh_test_store()   # flushes db 15 (no-op if Redis down)
    except Exception:
        pass
    shutil.rmtree(_TMP_AI_SETUP, ignore_errors=True)


if __name__ == "__main__":
    main()
