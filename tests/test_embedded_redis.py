"""The embedded Redis server: Aurora's bus on Python alone (core/foundation/embedded_redis.py).

WHAT IS PINNED. A machine with no Redis server must still have a working Bifrost bus -- mail,
consumer groups, blocking reads, Lua -- and it must survive restarts, because an inbox that
empties on reboot is not an inbox. And a machine that HAS a real Redis must never get a second,
embedded one started beside it: that splits the bus in two and squats on the port.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("fakeredis")
redis = pytest.importorskip("redis")

from core.foundation import embedded_redis as E  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _up(port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            return True
        except OSError:
            time.sleep(0.05)
    return False


@pytest.fixture
def server(tmp_path, monkeypatch):
    """Start/stop a real server subprocess on a throwaway port with a throwaway data dir."""
    port = _free_port()
    env = dict(os.environ, AKASHIC_EMBEDDED_REDIS_DIR=str(tmp_path),
               PYTHONPATH=str(ROOT))
    procs = []

    def start():
        p = subprocess.Popen([sys.executable, "-m", "core.foundation.embedded_redis",
                              "--port", str(port)], cwd=str(ROOT), env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(p)
        assert _up(port), "embedded redis did not come up"
        return redis.Redis(port=port, decode_responses=True, socket_timeout=10)

    def stop():
        time.sleep(E.FLUSH_INTERVAL * 3)      # let the flusher run (terminate is abrupt on Windows)
        p = procs[-1]
        p.terminate()
        p.wait(timeout=20)

    yield start, stop
    for p in procs:
        if p.poll() is None:
            p.kill()
            p.wait(timeout=20)


# ---------------------------------------------------------------------------- persistence

def test_bus_state_survives_a_restart(server):
    start, stop = server
    r = start()
    ids = [r.xadd("bifrost:inbox:claude", {"n": str(i)}) for i in range(3)]
    r.xgroup_create("bifrost:inbox:claude", "g", id="0")
    got = r.xreadgroup("g", "c", {"bifrost:inbox:claude": ">"}, count=2)
    assert [m[0] for m in got[0][1]] == ids[:2]
    r.hset("h", "f", "v")
    r.set("ttl", "x", ex=300)
    r.eval("redis.call('set', KEYS[1], ARGV[1])", 1, "lua", "wrote")
    r.set("gone", "1")
    r.delete("gone")
    stop()

    r = start()
    assert r.xlen("bifrost:inbox:claude") == 3
    assert r.xpending("bifrost:inbox:claude", "g")["pending"] == 2, "delivered-unacked lost"
    nxt = r.xreadgroup("g", "c", {"bifrost:inbox:claude": ">"}, count=5)
    assert [m[0] for m in nxt[0][1]] == ids[2:], "group read position lost"
    assert r.hget("h", "f") == "v" and r.get("lua") == "wrote"
    assert 0 < r.ttl("ttl") <= 300
    assert not r.exists("gone"), "a delete was not persisted"


def test_blocking_read_wakes_on_another_clients_write(server):
    start, _ = server
    r = start()
    port = r.connection_pool.connection_kwargs["port"]
    import threading

    def later():
        time.sleep(0.4)
        redis.Redis(port=port).xadd("wake", {"x": "y"})

    threading.Thread(target=later, daemon=True).start()
    t0 = time.monotonic()
    got = r.xread({"wake": "$"}, block=5000)
    assert got and got[0][1][0][1] == {"x": "y"}
    assert time.monotonic() - t0 < 3.0, "blocking read did not wake on the write"


def test_info_and_touch_exist(server):
    start, _ = server
    r = start()
    r.set("a", "1")
    assert r.info().get("aurora_backend") == "embedded"
    assert r.touch("a", "missing") == 1


# ---------------------------------------------------------------------------- backend choice

def test_backend_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("AKASHIC_REDIS_BACKEND", "external")
    assert E.configured_backend() == "external"
    assert E.record_backend(reachable=False) == "external"


def test_first_decision_is_recorded_and_sticks(monkeypatch, tmp_path):
    monkeypatch.delenv("AKASHIC_REDIS_BACKEND", raising=False)
    marker = tmp_path / "redis-backend"
    monkeypatch.setattr(E, "_marker", lambda: marker)
    assert E.configured_backend() is None
    assert E.record_backend(reachable=True) == "external"
    assert marker.read_text().strip() == "external"
    # a later outage must NOT flip a real-Redis checkout to embedded
    assert E.record_backend(reachable=False) == "external"


def test_never_starts_a_server_for_another_world_or_host(monkeypatch):
    monkeypatch.setattr(E, "_reachable", lambda *a, **k: False)
    spawned = []
    monkeypatch.setattr(E, "_spawn", lambda port: spawned.append(port))
    monkeypatch.setattr(E, "configured_backend", lambda: "embedded")
    monkeypatch.setattr(E, "is_own_world_port", lambda port: port == 16379)
    assert E.ensure_running("10.0.0.5", 16379, timeout=0.1) is False      # not this machine
    assert E.ensure_running("localhost", 16380, timeout=0.1) is False     # another world
    assert E.ensure_running("localhost", 54321, timeout=0.1) is False     # a throwaway test port
    assert spawned == []


def test_external_backend_never_starts_a_server(monkeypatch):
    monkeypatch.setattr(E, "_reachable", lambda *a, **k: False)
    spawned = []
    monkeypatch.setattr(E, "_spawn", lambda port: spawned.append(port))
    monkeypatch.setattr(E, "is_own_world_port", lambda port: True)
    monkeypatch.setenv("AKASHIC_REDIS_BACKEND", "external")
    assert E.ensure_running("localhost", 16379, timeout=0.1) is False
    assert spawned == []


# ---------------------------------------------------------------------------- first boot

def test_first_boot_seeds_the_file_store_once(tmp_path, monkeypatch):
    import fakeredis
    from types import SimpleNamespace
    data = tmp_path / "data"
    (data / "session_logs").mkdir(parents=True)
    (data / "session_logs" / "store_state.json").write_text(json.dumps({
        "kv": {"k": "v"},
        "hash": {"learn:experiment:x": {"actual": "it worked"}},
        "list": {"l": ["a", "b"]}, "set": {"s": ["m"]}, "zset": {"z": {"m": 2.0}},
        "__expiry__": {}}), encoding="utf-8")
    monkeypatch.setenv("AI_SETUP", str(data))
    import core.world as W
    monkeypatch.setattr(W, "current", lambda: SimpleNamespace(redis_port=16379))
    srv = fakeredis.FakeServer()
    path = tmp_path / "16379.sqlite3"
    assert E._seed_from_file_tier(srv, 16379, path) == 5
    from core.foundation.redis_connection import DEFAULT_REDIS_DB
    r = fakeredis.FakeRedis(server=srv, db=int(DEFAULT_REDIS_DB), decode_responses=True)
    assert r.hget("learn:experiment:x", "actual") == "it worked"
    assert r.lrange("l", 0, -1) == ["a", "b"] and r.zscore("z", "m") == 2.0
    assert E._seed_from_file_tier(fakeredis.FakeServer(), 16379, path) == 0, "seeded twice"


# ---------------------------------------------------------------------------- ledger backfill

def test_ledger_backfills_file_history_on_the_embedded_backend(tmp_path, monkeypatch):
    import fakeredis
    from core.foundation import ledger as L
    fl = L.FileLedger(str(tmp_path))
    fl.emit("events:raw", {"n": 1})
    fl.emit("events:raw", {"n": 2})
    rl = L.RedisLedger(fakeredis.FakeRedis(decode_responses=True))
    monkeypatch.setattr(E, "configured_backend", lambda: "embedded")
    L.HybridLedger._backfilled.clear()
    got = L.HybridLedger(rl, fl).consume("events:raw", after_id="0")
    assert [event for _id, event in got] == [{"n": 1}, {"n": 2}], got
    assert rl._client.xlen("events:raw") == 2
    # a second read must not copy the history again
    L.HybridLedger(rl, fl).consume("events:raw", after_id="0")
    assert rl._client.xlen("events:raw") == 2


def test_ledger_never_backfills_an_external_redis(tmp_path, monkeypatch):
    import fakeredis
    from core.foundation import ledger as L
    fl = L.FileLedger(str(tmp_path))
    fl.emit("events:raw", {"n": 1})
    rl = L.RedisLedger(fakeredis.FakeRedis(decode_responses=True))
    monkeypatch.setattr(E, "configured_backend", lambda: "external")
    L.HybridLedger._backfilled.clear()
    L.HybridLedger(rl, fl).consume("events:raw", after_id="0")
    assert rl._client.xlen("events:raw") == 0


def test_a_stopped_docker_redis_still_decides_external(monkeypatch, tmp_path):
    """First decision while the Docker Redis is merely stopped: still `external`, or an embedded
    server would take its port and the container could never start again."""
    monkeypatch.delenv("AKASHIC_REDIS_BACKEND", raising=False)
    monkeypatch.setattr(E, "_marker", lambda: tmp_path / "redis-backend")
    monkeypatch.setattr(E, "_has_redis_container", lambda: True)
    assert E.record_backend(reachable=False) == "external"


def test_no_redis_anywhere_decides_embedded(monkeypatch, tmp_path):
    monkeypatch.delenv("AKASHIC_REDIS_BACKEND", raising=False)
    monkeypatch.setattr(E, "_marker", lambda: tmp_path / "redis-backend")
    monkeypatch.setattr(E, "_has_redis_container", lambda: False)
    assert E.record_backend(reachable=False) == "embedded"


def test_incomplete_range_end_covers_the_whole_millisecond(server):
    """Redis reads a bare-ms UPPER bound as <ms>-<max seq>; fakeredis read it as <ms>-0 and
    dropped every later entry in that millisecond (it broke the bus's lane-twin windows)."""
    start, _ = server
    r = start()
    for s in range(3):
        r.xadd("ix", {"s": str(s)}, id=f"1000-{s}")
    r.xadd("ix", {"s": "x"}, id="1001-0")
    assert [i for i, _ in r.xrevrange("ix", max="1000", min="1000")] == ["1000-2", "1000-1", "1000-0"]
    assert [i for i, _ in r.xrange("ix", min="1000", max="1000")] == ["1000-0", "1000-1", "1000-2"]
    assert [i for i, _ in r.xrange("ix", min="1000-1", max="1001-0")] == ["1000-1", "1000-2", "1001-0"]
