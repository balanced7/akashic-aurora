"""Daniil's steer: "multiple instances of things for performance reasons instead of one monolith."

Measured, not argued. Four write strategies, same payload, same 20-thread fleet-scale load:

  A MONOLITH  -- what shipped: one lock, one file handle, json.dumps on the caller's thread
  B SHARDED   -- one journal instance per writer: no shared lock, no shared handle
  C ASYNC     -- caller enqueues, ONE background writer owns all serialization and IO
  D SHARDED+ASYNC -- N queues, N writers: no shared lock AND no serialization on the hot path

The question is not "which is fastest" but "what does the CALLER pay", because the caller is a
thread in the middle of an API call.
"""
import json
import os
import queue
import statistics
import sys
import tempfile
import threading
import time

sys.path.insert(0, r"E:\AI-Setup")
from scripts.wire_journal import WireJournal  # noqa: E402

THREADS = 20
CALLS = 4000

SAMPLE = dict(
    model="deepseek-chat", status=200, attempt=0, stream=True,
    system_fingerprint="fp_3a9c1b", finish_reason="stop", service_tier="default",
    usage={"prompt_tokens": 12000, "completion_tokens": 800, "total_tokens": 12800,
           "prompt_cache_hit_tokens": 9000, "prompt_cache_miss_tokens": 3000,
           "completion_tokens_details": {"reasoning_tokens": 300}},
    headers={"x-ds-trace-id": "7d0a37b8dcabac6f7fa679e94984f73e", "x-cache": "Miss",
             "content-type": "text/event-stream", "authorization": "NEVER-KEEP"},
    ms_first_byte=430,
)


def _run(make_writer, teardown=None):
    """make_writer(i) -> callable the i-th thread calls per record. Returns caller-side latencies."""
    lat, lock = [], threading.Lock()

    def worker(i):
        write = make_writer(i)
        local = []
        for _ in range(CALLS // THREADS):
            t0 = time.perf_counter()
            write(SAMPLE)
            local.append((time.perf_counter() - t0) * 1e6)
        with lock:
            lat.extend(local)

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    t0 = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wall = time.perf_counter() - t0
    if teardown:
        teardown()
    lat.sort()
    return {"mean": statistics.mean(lat), "p50": lat[len(lat) // 2],
            "p99": lat[int(len(lat) * 0.99)], "max": lat[-1], "wall": wall}


# ---- A: monolith (shipped) -------------------------------------------------
_mono = WireJournal(journal_dir=tempfile.mkdtemp(prefix="A-"))
A = _run(lambda i: (lambda s: _mono.record(**s)))

# ---- B: sharded, one instance per writer -----------------------------------
_bdir = tempfile.mkdtemp(prefix="B-")
_shards = [WireJournal(journal_dir=os.path.join(_bdir, f"s{i}")) for i in range(THREADS)]
B = _run(lambda i: (lambda s: _shards[i].record(**s)))

# ---- C: async, one background writer ---------------------------------------
_cq = queue.Queue(maxsize=10000)
_cdir = tempfile.mkdtemp(prefix="C-")
_cstop = threading.Event()
_cdropped = [0]


def _c_writer():
    f = open(os.path.join(_cdir, "wire.jsonl"), "a", encoding="utf-8")
    while not (_cstop.is_set() and _cq.empty()):
        try:
            rec = _cq.get(timeout=0.05)
        except queue.Empty:
            continue
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    f.close()


_ct = threading.Thread(target=_c_writer, daemon=True)
_ct.start()


def _c_put(s):
    try:
        _cq.put_nowait(dict(s))          # hot path: a dict copy and an enqueue. Nothing else.
    except queue.Full:
        _cdropped[0] += 1                 # backpressure DROPS and COUNTS; never blocks the call


C = _run(lambda i: _c_put, teardown=lambda: (_cstop.set(), _ct.join(timeout=5)))

# ---- D: sharded + async ----------------------------------------------------
_ddir = tempfile.mkdtemp(prefix="D-")
NW = 4                                    # 4 writers for 20 threads -- shards, not one-per-thread
_dqs = [queue.Queue(maxsize=10000) for _ in range(NW)]
_dstop = threading.Event()


def _d_writer(k):
    f = open(os.path.join(_ddir, f"wire-{k}.jsonl"), "a", encoding="utf-8")
    q = _dqs[k]
    while not (_dstop.is_set() and q.empty()):
        try:
            rec = q.get(timeout=0.05)
        except queue.Empty:
            continue
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    f.close()


_dts = [threading.Thread(target=_d_writer, args=(k,), daemon=True) for k in range(NW)]
for t in _dts:
    t.start()


def _d_make(i):
    q = _dqs[i % NW]

    def put(s):
        try:
            q.put_nowait(dict(s))
        except queue.Full:
            pass
    return put


D = _run(_d_make, teardown=lambda: (_dstop.set(), [t.join(timeout=5) for t in _dts]))

print(f"{'strategy':<26}{'mean us':>10}{'p50 us':>10}{'p99 us':>11}{'max us':>11}{'wall s':>9}")
for name, r in (("A monolith (shipped)", A), ("B sharded instances", B),
                ("C async, 1 writer", C), ("D sharded + async", D)):
    print(f"{name:<26}{r['mean']:>10.1f}{r['p50']:>10.1f}{r['p99']:>11.1f}"
          f"{r['max']:>11.1f}{r['wall']:>9.2f}")
print(f"\nspeedup on caller-side mean vs monolith:  "
      f"B {A['mean']/B['mean']:.1f}x   C {A['mean']/C['mean']:.1f}x   D {A['mean']/D['mean']:.1f}x")
print(f"C dropped under backpressure: {_cdropped[0]}")
