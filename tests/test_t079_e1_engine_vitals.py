"""T079-E1 PRE-REGISTERED ACCEPTANCE -- gauge_snapshot(), the engine room's pulse.

Spec: t079-engine-room-reconciliation-2026-07-15.md slice E1 (claude builds,
deepseek verifies; his Zone-1 gauge table is the contract). One call, one dict,
pure READER over existing signals -- presence card (+runtimes), W1 token journal,
pager unread count, daemon liveness. The UI polls this at 2s; it must be cheap
and it must NEVER raise.

Pins:
  P1  gauge_snapshot(agent) returns the five gauge keys: heartbeat, runtimes,
      tokens, pages, daemon_live -- always, even with no client (fail-open shape)
  P2  heartbeat derives from the presence card: absent -> offline; fresh ts ->
      active; stale ts -> idle (thresholds per his Zone-1 table: 5m idle)
  P3  runtimes passes the daemon card's field through verbatim (live/down/blocked)
  P4  tokens reads today's W1 journal when present (prompt/completion), zeros absent
  P5  pages = unread pager count
  P6  no client + no files -> a well-formed all-quiet snapshot, never an exception

Run: py -m pytest tests/test_t079_e1_engine_vitals.py -q
"""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.comm import engine_vitals as ev
except ImportError:
    ev = None


def _built():
    assert ev is not None, "E1 build target core/comm/engine_vitals.py missing (RED until built)"


class FakeRedis:
    def __init__(self):
        self.kv, self.lists = {}, {}
    def get(self, k):
        return self.kv.get(k)
    def set(self, k, v, ex=None):
        self.kv[k] = v
    def exists(self, k):
        return 1 if k in self.kv else 0
    def lrange(self, k, a, b):
        L = self.lists.get(k, [])
        return L[a:] if b == -1 else L[a:b + 1]


AGENT = "e1drill"


def _snap(c, **kw):
    return ev.gauge_snapshot(AGENT, c=c, **kw)


def test_p1_shape_always():
    _built()
    for c in (FakeRedis(), None):
        s = ev.gauge_snapshot(AGENT, c=c, allow_fallback=False)
        assert set(s) >= {"heartbeat", "runtimes", "tokens", "pages", "daemon_live"}, \
            f"P1: gauge keys missing from {s}"


def test_p2_heartbeat_states():
    _built()
    c = FakeRedis()
    assert _snap(c)["heartbeat"] == "offline", "P2: no presence card -> offline"
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    c.set(f"bifrost:presence:{AGENT}", json.dumps({"ts": now}))
    assert _snap(c)["heartbeat"] == "active", "P2: fresh presence -> active"
    old = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 900))
    c.set(f"bifrost:presence:{AGENT}", json.dumps({"ts": old}))
    assert _snap(c)["heartbeat"] == "idle", "P2: 15m-stale presence -> idle"


def test_p3_runtimes_passthrough():
    _built()
    c = FakeRedis()
    c.set(f"bifrost:presence:{AGENT}", json.dumps(
        {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
         "runtimes": {"runner": "blocked", "listener": "live"}}))
    assert _snap(c)["runtimes"] == {"runner": "blocked", "listener": "live"}


def test_p4_tokens_from_journal(tmp_path):
    _built()
    c = FakeRedis()
    day = time.strftime("%Y-%m-%d")
    p = tmp_path / f"runner_{AGENT}_{day}.json"
    p.write_text(json.dumps({"prompt": 1234, "completion": 567}))
    s = ev.gauge_snapshot(AGENT, c=c, journal_dir=str(tmp_path))
    assert s["tokens"]["prompt"] == 1234 and s["tokens"]["completion"] == 567
    s2 = ev.gauge_snapshot(AGENT, c=c, journal_dir=str(tmp_path / "nope"))
    assert s2["tokens"] == {"prompt": 0, "completion": 0}, "P4: absent journal -> zeros"


def test_p5_pages_count():
    _built()
    c = FakeRedis()
    c.lists["bifrost:pages"] = [json.dumps({"ts": time.time(), "agent": "x", "text": "t"})] * 3
    assert _snap(c)["pages"] == 3


def test_p6_never_raises():
    _built()
    class Hostile:
        def __getattr__(self, _):
            raise RuntimeError("boom")
    s = ev.gauge_snapshot(AGENT, c=Hostile())
    assert s["heartbeat"] == "offline" and s["pages"] == 0, "P6: hostile client -> quiet snapshot"
