"""T086-S6 PRE-REGISTERED ACCEPTANCE — durable reply dedup (Kafka consumer-offsets pattern).
Cites research/reviewed/t086-seat-reconciliation-2026-07-16.md (Fix-Class D:
durable reply dedup — answered-set survives runner restart; redelivered handoff
is skipped, not re-answered).

Pins:
  S6-D1  reply already sent → detected via Redis (fast path)
  S6-D2  reply already sent → detected via Store (durable backstop)
  S6-D3  mark_reply_sent writes to both Redis AND Store
  S6-D4  probe error → fail-open (not-sent → duplicate is cheaper than drop)

Run: py -m pytest tests/test_t086_s6_reply_dedup.py -q
"""
import os
import sys
import uuid

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _runner_module():
    import scripts.bifrost_runner_deepseek as r
    return r


def test_s6_d1_reply_already_sent_redis_fast_path(monkeypatch):
    """Redis EXISTS returns True → _reply_already_sent returns True."""
    r = _runner_module()

    class FakeBus:
        class _client:
            @staticmethod
            def exists(key):
                return True
        _client = _client()

    assert r._reply_already_sent(FakeBus(), "msg-1") is True


def test_s6_d2_reply_already_sent_store_backstop(monkeypatch):
    """Redis offline (exists raises), Store has the key → _reply_already_sent returns True."""
    r = _runner_module()

    class FakeBus:
        class _client:
            @staticmethod
            def exists(key):
                raise Exception("redis down")
        _client = _client()

    # Use a real FileStore (no Redis) as the durable backstop
    from core.foundation.store import FileStore
    store = FileStore()
    mid = f"t086s6-{uuid.uuid4().hex[:6]}"
    store.set(f"reply_sent:{mid}", "1")

    # Patch create_store to return our controlled store
    monkeypatch.setattr("core.foundation.store.create_store", lambda: store)
    assert r._reply_already_sent(FakeBus(), mid) is True

    # Cleanup
    store.delete(f"reply_sent:{mid}")


def test_s6_d3_mark_reply_sent_writes_both(monkeypatch):
    """_mark_reply_sent writes to Redis AND Store."""
    r = _runner_module()
    redis_written = {}
    store_written = {}

    class FakeBus:
        class _client:
            @staticmethod
            def set(key, value, ex=None, nx=None):
                redis_written["key"] = key
                redis_written["value"] = value
                return True
        _client = _client()

    from core.foundation.store import FileStore
    store = FileStore()
    monkeypatch.setattr("core.foundation.store.create_store", lambda: store)

    mid = f"t086s6-{uuid.uuid4().hex[:6]}"
    r._mark_reply_sent(FakeBus(), mid)

    # Redis written
    assert r.REPLY_SENT_PREFIX + mid in redis_written.get("key", ""), \
        f"Redis not written: {redis_written}"
    # Store written
    assert store.get(f"reply_sent:{mid}") == "1", \
        "Store not written"

    # Cleanup
    store.delete(f"reply_sent:{mid}")


def test_s6_d4_probe_error_fail_open(monkeypatch):
    """Both Redis AND Store raise → _reply_already_sent returns False (fail-open:
    a duplicate reply is cheaper than a dropped one)."""
    r = _runner_module()

    class FakeBus:
        class _client:
            @staticmethod
            def exists(key):
                raise Exception("redis down")
        _client = _client()

    # Make create_store raise too
    monkeypatch.setattr("core.foundation.store.create_store",
                        lambda: (_ for _ in ()).throw(RuntimeError("store down")))

    assert r._reply_already_sent(FakeBus(), "msg-any") is False
