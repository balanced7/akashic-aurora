"""Measure what WireJournal.record() actually costs on the CALLER'S thread.

The perf lane is designing a hot-path budget. A budget argued against a guess is worthless, so
this measures the shipped implementation: record() does makedirs + open + json.dumps + a lock
inline, on the thread that is mid-API-call. Question: how much, and does it get worse under the
concurrency a 20-player season implies?
"""
import os
import statistics
import sys
import tempfile
import threading
import time

sys.path.insert(0, r"E:\AI-Setup")
os.environ["AKASHIC_WIRE_DIR"] = tempfile.mkdtemp(prefix="wirebench-")

from scripts.wire_journal import WireJournal  # noqa: E402

SAMPLE = dict(
    model="deepseek-chat", status=200, attempt=0, stream=True,
    system_fingerprint="fp_3a9c1b", finish_reason="stop", service_tier="default",
    usage={"prompt_tokens": 12000, "completion_tokens": 800, "total_tokens": 12800,
           "prompt_cache_hit_tokens": 9000, "prompt_cache_miss_tokens": 3000,
           "completion_tokens_details": {"reasoning_tokens": 300}},
    headers={"x-ds-trace-id": "7d0a37b8dcabac6f7fa679e94984f73e", "x-cache": "Miss from cloudfront",
             "content-type": "text/event-stream", "server": "elb",
             "authorization": "SHOULD-NEVER-BE-KEPT"},
    ms_first_byte=430,
)


def bench(n, threads):
    j = WireJournal(journal_dir=tempfile.mkdtemp(prefix="wirebench-"))
    lat = []
    lock = threading.Lock()

    def worker(count):
        local = []
        for _ in range(count):
            t0 = time.perf_counter()
            j.record(**SAMPLE)
            local.append((time.perf_counter() - t0) * 1e6)   # microseconds
        with lock:
            lat.extend(local)

    per = n // threads
    ts = [threading.Thread(target=worker, args=(per,)) for _ in range(threads)]
    t0 = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wall = time.perf_counter() - t0
    lat.sort()
    return {
        "threads": threads,
        "calls": len(lat),
        "mean_us": statistics.mean(lat),
        "p50_us": lat[len(lat) // 2],
        "p99_us": lat[int(len(lat) * 0.99)],
        "max_us": lat[-1],
        "wall_s": wall,
        "dropped": j.dropped,
    }


print(f"{'threads':>8} {'calls':>7} {'mean us':>9} {'p50 us':>8} {'p99 us':>9} {'max us':>9} {'wall s':>7}")
for th in (1, 4, 8, 20):
    r = bench(4000, th)
    print(f"{r['threads']:>8} {r['calls']:>7} {r['mean_us']:>9.1f} {r['p50_us']:>8.1f} "
          f"{r['p99_us']:>9.1f} {r['max_us']:>9.1f} {r['wall_s']:>7.2f}")

# Does the allowlist actually hold under a real header set?
j = WireJournal(journal_dir=tempfile.mkdtemp(prefix="wirebench-"))
j.record(**SAMPLE)
raw = "".join(open(p, encoding="utf-8").read() for p in j.files())
print("\nauthorization header leaked to disk:", "SHOULD-NEVER-BE-KEPT" in raw)
print("x-ds-trace-id kept:", "7d0a37b8dcabac6f7fa679e94984f73e" in raw)
