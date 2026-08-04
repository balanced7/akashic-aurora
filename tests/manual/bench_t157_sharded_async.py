"""T157 after-measurement, same methodology as the recorded baseline.

Caller-side added latency per record() call. Baseline (note wire-perf-baseline) at 20 threads:
  A monolith (shipped) 7458us mean / 18492 p99 / 30854 max
"""
import os
import statistics
import sys
import tempfile
import threading
import time

sys.path.insert(0, r"E:\AI-Setup")
from scripts.wire_journal import WireJournal   # noqa: E402

N_THREADS, PER = 20, 200


def bench(writer, agents):
    d = tempfile.mkdtemp(prefix=f"wire_{writer}_{agents}_")
    lat, lock = [], threading.Lock()
    js = [WireJournal(journal_dir=d, agent=f"player{i:02d}", writer=writer)
          for i in range(N_THREADS)]

    def work(i):
        j = js[i] if agents > 1 else js[0]
        mine = []
        for _ in range(PER):
            t0 = time.perf_counter()
            j.record(status=200, model="m", usage={"total_tokens": 7})
            mine.append((time.perf_counter() - t0) * 1e6)
        with lock:
            lat.extend(mine)

    ts = [threading.Thread(target=work, args=(i,)) for i in range(N_THREADS)]
    t_wall = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    for j in js:
        j.flush()
    wall = time.perf_counter() - t_wall

    lat.sort()
    dropped = sum(j.dropped for j in js)
    return {
        "mean": statistics.mean(lat),
        "p99": lat[int(len(lat) * 0.99)],
        "max": lat[-1],
        "wall_s": wall,
        "dropped": dropped,
    }


print(f"{N_THREADS} threads x {PER} records = {N_THREADS*PER} calls, caller-side us\n")
print(f"{'strategy':<28} {'mean':>10} {'p99':>10} {'max':>10} {'wall s':>8} {'dropped':>8}")
for label, writer, agents in (
        ("A sync, 1 shard (shipped)", "sync", 1),
        ("B sync, sharded", "sync", 20),
        ("D async + sharded (new)", "async", 20),
):
    r = bench(writer, agents)
    print(f"{label:<28} {r['mean']:>10.1f} {r['p99']:>10.1f} {r['max']:>10.1f} "
          f"{r['wall_s']:>8.2f} {r['dropped']:>8}")
