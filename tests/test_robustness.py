"""
Robustness suite — finds failures that single-pass unit tests miss.

Techniques (no external deps; deterministic via a fixed seed):
  1. model-based fuzzing      : random op sequences vs a reference model
  2. cross-backend equivalence: FileStore vs HybridStore(redis-down) must agree
  3. property invariants       : Ranker/Distiller must always hold their contracts
  4. corruption resilience     : a garbage store file must degrade, not crash
  5. backward-compat loading   : old-shape records (missing new fields) must load
  6. concurrency               : parallel writes must not lose data or crash

Run: py tests/test_robustness.py
"""

import sys
import os
import json
import random
import string
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore, HybridStore
from core.primitives.ranker import Ranker
from core.primitives.distiller import Distiller

random.seed(20260620)  # reproducible


def _rnd_word(n=5):
    return "".join(random.choice(string.ascii_lowercase) for _ in range(n))


# ---------- 1. model-based fuzzing of the Store ----------
def test_store_model_fuzz(iterations=1500):
    with tempfile.TemporaryDirectory() as d:
        s = FileStore(os.path.join(d, "fuzz.json"))
        kv, hashes, sets, zsets = {}, {}, {}, {}
        keys = [f"k{i}" for i in range(6)]
        for _ in range(iterations):
            op = random.choice(["set", "get", "delete", "hset", "hget", "sadd",
                                "smembers", "zadd", "zscore", "zcard"])
            k = random.choice(keys)
            if op == "set":
                v = _rnd_word(); s.set(k, v); kv[k] = v
            elif op == "get":
                assert s.get(k) == kv.get(k), f"kv mismatch {k}: {s.get(k)} != {kv.get(k)}"
            elif op == "delete":
                s.delete(k)
                for m in (kv, hashes, sets, zsets):
                    m.pop(k, None)
            elif op == "hset":
                f, v = _rnd_word(3), _rnd_word()
                s.hset(k, field=f, value=v); hashes.setdefault(k, {})[f] = v
            elif op == "hget":
                f = _rnd_word(3)
                assert s.hget(k, f) == hashes.get(k, {}).get(f), f"hash mismatch {k}.{f}"
            elif op == "sadd":
                m = _rnd_word(3); s.sadd(k, m); sets.setdefault(k, set()).add(m)
            elif op == "smembers":
                assert s.smembers(k) == sets.get(k, set()), f"set mismatch {k}"
            elif op == "zadd":
                m, sc = _rnd_word(3), round(random.uniform(0, 100), 2)
                s.zadd(k, {m: sc}); zsets.setdefault(k, {})[m] = sc
            elif op == "zscore":
                m = _rnd_word(3)
                assert s.zscore(k, m) == zsets.get(k, {}).get(m), f"zscore mismatch {k}.{m}"
            elif op == "zcard":
                assert s.zcard(k) == len(zsets.get(k, {})), f"zcard mismatch {k}"
    print(f"\n--- model fuzz ({iterations} ops) ---\n  Store matches reference model throughout OK")


# ---------- 2. cross-backend equivalence ----------
def test_cross_backend_equivalence(iterations=800):
    with tempfile.TemporaryDirectory() as d:
        a = FileStore(os.path.join(d, "a.json"))
        b = HybridStore.create(port=63999, file_path=os.path.join(d, "b.json"))  # redis down
        assert b.redis_available is False
        keys = [f"k{i}" for i in range(5)]
        for _ in range(iterations):
            k = random.choice(keys)
            op = random.choice(["set", "hset", "sadd", "zadd", "delete"])
            if op == "set":
                v = _rnd_word(); a.set(k, v); b.set(k, v)
            elif op == "hset":
                f, v = _rnd_word(3), _rnd_word(); a.hset(k, field=f, value=v); b.hset(k, field=f, value=v)
            elif op == "sadd":
                m = _rnd_word(3); a.sadd(k, m); b.sadd(k, m)
            elif op == "zadd":
                m, sc = _rnd_word(3), round(random.uniform(0, 9), 1); a.zadd(k, {m: sc}); b.zadd(k, {m: sc})
            elif op == "delete":
                a.delete(k); b.delete(k)
        for k in keys:
            assert a.get(k) == b.get(k), f"kv differ at {k}"
            assert a.hgetall(k) == b.hgetall(k), f"hash differ at {k}"
            assert a.smembers(k) == b.smembers(k), f"set differ at {k}"
            assert a.zrange(k, 0, -1, withscores=True) == b.zrange(k, 0, -1, withscores=True), f"zset differ at {k}"
    print("\n--- cross-backend equivalence ---\n  FileStore == HybridStore(redis-down) OK")


# ---------- 3. property invariants ----------
def test_distiller_invariants(rounds=400):
    d = Distiller()
    for _ in range(rounds):
        n = random.randint(0, 12)
        items = []
        for i in range(n):
            it = {"text": _rnd_word(random.randint(1, 40))}
            if random.random() < 0.8:
                it["source"] = f"s{i}"
            items.append(it)
        budget = random.randint(0, 200)
        out = d.distill(items, token_budget=budget)
        assert out.approx_tokens <= budget, f"over budget: {out.approx_tokens}>{budget}"
        assert all(e.get("source") for e in out.entries), "included entry without source"
        with_src = {it["source"] for it in items if it.get("source")}
        assert set(out.included_sources) | set(out.dropped_sources) == with_src, "lost a source"
    print(f"\n--- distiller invariants ({rounds} rounds) ---\n  always within budget, no source lost OK")


def test_ranker_invariants(rounds=400):
    r = Ranker()
    for _ in range(rounds):
        n = random.randint(0, 12)
        items = []
        for i in range(n):
            it = {"text": _rnd_word(8), "importance": random.randint(1, 5)}
            if random.random() < 0.3:
                it["superseded"] = True
            items.append(it)
        active = [it for it in items if not it.get("superseded")]
        out = r.rank(items, query=random.choice(["", _rnd_word(8)]), now=1.0)
        assert len(out) == len(active), "superseded leaked into ranking"
        scores = [s.score for s in out]
        assert scores == sorted(scores, reverse=True), "not sorted best-first"
        assert all(set(s.components) == {"relevance", "importance", "recency", "relationship"} for s in out)
    print(f"\n--- ranker invariants ({rounds} rounds) ---\n  superseded excluded, sorted, components present OK")


# ---------- 4. corruption resilience ----------
def test_filestore_corruption_resilience():
    """CONTRACT CHANGED 2026-07-25 -- deliberately, after a live data-loss incident.

    This test used to assert that a corrupt store file "recovers" by being overwritten:
    `assert FileStore(p).get("k") == "v", "recovered data persists"`. That behaviour is
    exactly the defect codex reported -- a 9MB store_state.json found at 164 bytes holding
    one vote, because a failed load left _data empty and the next set() flushed the empty
    dict over the file. Reproduced at 108963 -> 98 bytes.

    "Recovery" that discards the unreadable data is not resilience; it is silent
    destruction, and it is worst precisely when the file was large and the corruption was
    superficial (a trailing partial write from a concurrent writer). The store now REFUSES
    to persist over bytes it could not parse.

    What resilience still means here, and is asserted below: never crash on load, stay
    fully usable in memory, and keep the original bytes recoverable.
    """
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "corrupt.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json @#$%")
        original = open(p, encoding="utf-8").read()

        s = FileStore(p)               # must not crash on load
        assert s.get("anything") is None, "corrupt file should read as empty"
        s.set("k", "v")                # must stay usable in memory
        assert s.get("k") == "v", "a degraded store still serves its own writes"

        # The corrupt bytes survive: either still in place, or in the forensic copy.
        on_disk = [open(os.path.join(d, f), encoding="utf-8", errors="replace").read()
                   for f in os.listdir(d)]
        assert any(original in blob for blob in on_disk), \
            "the unreadable bytes were destroyed -- this is the 2026-07-25 incident"
    print("\n--- corruption resilience ---\n"
          "  garbage store file: no crash, usable in memory, original bytes preserved OK")


# ---------- 5. backward-compat loading ----------
def test_backward_compat_record_loading():
    from core.learning.agent_memory import Decision, Experience
    # records written before Phase B lack supersedes/superseded
    old_decision = {"id": "ADR_x", "title": "t", "status": "accepted", "context": "",
                    "decision": "d", "rationale": [], "alternatives": [], "consequences": {},
                    "created_at": "2026-01-01T00:00:00", "session_id": ""}
    dec = Decision(**old_decision)     # must not crash; defaults applied
    assert dec.superseded is False and dec.supersedes is None
    old_exp = {"id": "exp_x", "task": "t", "approach": "", "result": "ok", "success": True,
               "score": 0, "learnings": [], "timestamp": "2026-01-01T00:00:00", "session_id": ""}
    exp = Experience(**old_exp)
    assert exp.superseded is False
    print("\n--- backward-compat ---\n  old-shape records load with new-field defaults OK")


# ---------- 6. concurrency ----------
def test_concurrent_writes():
    with tempfile.TemporaryDirectory() as d:
        s = FileStore(os.path.join(d, "concurrent.json"))
        n_threads, per = 8, 50

        def worker(tid):
            for i in range(per):
                s.sadd("shared", f"t{tid}_m{i}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads: t.start()
        for t in threads: t.join()
        members = s.smembers("shared")
        assert len(members) == n_threads * per, f"lost updates: {len(members)}/{n_threads*per}"
    print("\n--- concurrency ---\n  parallel writes: no lost updates, no crash OK")


if __name__ == "__main__":
    print("=" * 60)
    print("ROBUSTNESS SUITE")
    print("=" * 60)
    test_store_model_fuzz()
    test_cross_backend_equivalence()
    test_distiller_invariants()
    test_ranker_invariants()
    test_filestore_corruption_resilience()
    test_backward_compat_record_loading()
    test_concurrent_writes()
    print("\n" + "=" * 60)
    print("ALL ROBUSTNESS CHECKS PASSED")
    print("=" * 60)
