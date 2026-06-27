"""
Tests for StoreReconciler (the surviving kernel of the old sync coordinator)
and the deprecated RedisSyncCoordinator facade.

Run: py tests/test_sync_reconciler.py
"""

import sys
import os
import tempfile

# Full test isolation BEFORE any foundation import, so even the facade's internal
# default store (RedisSyncCoordinator) cannot touch canonical data. Redirect BOTH:
#   - the FILE store -> a throwaway AI_SETUP dir
#   - the REDIS logical DB -> db 15
# Root-cause fix for the 2026-06-20 pollution (the old after-the-fact _cleanup scrub
# was the band-aid that failed: it wrote to canonical, then tried to undo it).
_TMP_AI_SETUP = tempfile.mkdtemp(prefix="aisetup_test_")
os.makedirs(os.path.join(_TMP_AI_SETUP, "session_logs"), exist_ok=True)
os.environ["AI_SETUP"] = _TMP_AI_SETUP
os.environ.setdefault("REDIS_DB", "15")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore, RedisStore, HybridStore
from core.state.sync_reconciler import StoreReconciler, sync_state_reconciling_divergence
from core.state.redis_sync_coordinator import RedisSyncCoordinator, SignalType


def test_reconciler_redis_down():
    """With Redis down, reconciliation is a safe no-op (File is already truth)."""
    with tempfile.TemporaryDirectory() as d:
        store = HybridStore.create(port=63999, file_path=os.path.join(d, "s.json"))
        rec = StoreReconciler(store)
        assert rec.can_reconcile is False
        drift = rec.check_divergence()
        assert drift["applicable"] is True and drift["redis_available"] is False
        report = rec.reconcile_divergence()
        assert report["status"] == "skipped"
        print("\n--- reconciler (Redis down) ---\n  safe no-op + drift report OK")


def test_reconciler_backfill_if_redis():
    """If Redis is up, reconcile backfills File data into an empty Redis."""
    rs = RedisStore.connect(timeout_seconds=2.0)
    if not rs.is_available():
        print("\n--- reconciler backfill ---\n  SKIPPED (Redis not running)")
        return
    import time
    ns = f"recon:{int(time.time())}"
    with tempfile.TemporaryDirectory() as d:
        fs = FileStore(os.path.join(d, "s.json"))
        # Seed the File backend with each structure type.
        fs.set(f"{ns}:kv", "v")
        fs.hset(f"{ns}:h", mapping={"a": "1"})
        fs.rpush(f"{ns}:l", "x", "y")
        fs.sadd(f"{ns}:s", "m")
        fs.zadd(f"{ns}:z", {"mem": 5.0})
        hybrid = HybridStore(rs, fs)
        before = rs.exists(f"{ns}:kv")
        report = hybrid.reconcile()
        assert report["status"] == "success", report
        # Redis now mirrors the File data.
        assert rs.get(f"{ns}:kv") == "v"
        assert rs.hget(f"{ns}:h", "a") == "1"
        assert rs.lrange(f"{ns}:l", 0, -1) == ["x", "y"]
        assert rs.sismember(f"{ns}:s", "m")
        assert rs.zscore(f"{ns}:z", "mem") == 5.0
        drift = hybrid.check_drift()
        # cleanup
        for k in rs.keys(f"{ns}*"):
            rs.delete(k)
        print(f"\n--- reconciler backfill (live Redis) ---\n  backfilled {report['written']}, was_present={before} OK")


def test_facade_delegates():
    """The deprecated facade still works, delegating to Bus/LearningStore/Store."""
    c = RedisSyncCoordinator("recon_test_agent")
    assert c.emit_signal(SignalType.ACTION, {"action_name": "t"}) is True
    assert c.signal_count == 1
    ok = c.record_learning(
        experiment_name="recon_facade_exp", what_tried="x", expected_outcome="y",
        actual_outcome="z", category="verification", success="yes")
    assert ok is True
    assert c.publish_status({"phase": "test"}) is True
    instances = c.load_active_instances_from_registry()
    assert c.instance_id in instances, "heartbeat should register the instance"
    stats = c.get_stats()
    assert stats["signals_emitted"] == 1
    health = c.health_check()
    assert "sync_status" in health
    print("\n--- facade delegation ---\n  emit/learn/status/stats/health via primitives OK")


def main():
    print("=" * 60)
    print("SYNC RECONCILER + FACADE TESTS")
    print("=" * 60)
    test_reconciler_redis_down()
    test_reconciler_backfill_if_redis()
    test_facade_delegates()
    _teardown()
    print("\n" + "=" * 60)
    print("ALL SYNC RECONCILER TESTS PASSED")
    print("=" * 60)


def _teardown():
    """Discard the throwaway isolation: flush the test Redis DB + remove the temp dir.
    No canonical scrubbing needed -- nothing canonical was ever written."""
    import shutil
    try:
        from redis_test_helpers import fresh_test_store
        fresh_test_store()   # flushes db 15 (no-op if Redis down)
    except Exception:
        pass
    shutil.rmtree(_TMP_AI_SETUP, ignore_errors=True)


if __name__ == "__main__":
    main()
