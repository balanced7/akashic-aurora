"""Latency probe — measure the §5 bars on THIS host (DESKTOP-5886HDP, real 4K).

Not an assertion file (yet). This is the measurement instrument that turns the
§5 pre-registered bars (capture <100ms p95, L0/L3 <5ms server-side) into REAL
numbers on a real display host. The bench harness (tests/screenspace/bench_*.py)
will wrap these measurements as asserts-that-score; this probe is the first
cut proving the numbers are measurable HERE, not just on "some future desktop".
"""

import statistics
import time


def _measure(fn, n=50):
    samples = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)  # ms
    samples.sort()
    return {
        "n": n,
        "p50": statistics.median(samples),
        "p95": samples[int(n * 0.95) - 1],
        "min": samples[0],
        "max": samples[-1],
    }


def test_measure_capture_latency():
    from core.screenspace.capture import screen

    def _cap():
        f = screen()
        assert f is not None

    # One warmup, then 50 timed.
    screen()
    stats = _measure(_cap, n=50)
    print("\n--- [latency] capture.screen() (mss one-shot, 4K) ---")
    print(f"n={stats['n']}  p50={stats['p50']:.2f}ms  p95={stats['p95']:.2f}ms  "
          f"min={stats['min']:.2f}  max={stats['max']:.2f}")
    print(f"§5 bar: <100ms p95  ->  {'PASS' if stats['p95'] < 100 else 'FAIL'}")
    # This probe REPORTS; the bar assert belongs to the bench harness, not here.
    assert True


def test_measure_l0_l3_latency():
    from core.screenspace import peek, delta

    def _l0():
        peek(level="L0")

    def _l3():
        delta(since_gen=0)

    peek(level="L0")  # warm
    s0 = _measure(_l0, n=50)
    s3 = _measure(_l3, n=50)
    print("\n--- [latency] L0 pulse / L3 delta (gen-clock, server-side) ---")
    print(f"L0 peek:   p50={s0['p50']:.3f}ms  p95={s0['p95']:.3f}ms")
    print(f"L3 delta:  p50={s3['p50']:.3f}ms  p95={s3['p95']:.3f}ms")
    print(f"§5 bar: <5ms server-side  ->  "
          f"{'PASS' if s0['p95'] < 5 and s3['p95'] < 5 else 'FAIL (or needs cache, F2)'}")
    assert True
