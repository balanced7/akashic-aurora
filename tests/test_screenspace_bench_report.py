"""Reporter: extract the REAL measured numbers from Heimdall's bench on this host."""


def test_report_bench_numbers():
    from tests.screenspace.bench_observe_latency import (
        _substrate_kind,
        _measure_capture_l5,
        _measure_l0_l3_v2,
        _BENCHABLE,
    )
    from core.screenspace.capture import _load_mss

    print("\n=== [bench-report] observe latency on THIS host ===")
    print(f"substrate kind = {_substrate_kind()}")
    print(f"mss importable  = {_load_mss() is not None}")
    print(f"benchable       = {_BENCHABLE}")

    l5_mn, l5_p95, l5_n = _measure_capture_l5()
    (l0_mn, l0_p95, l0_n), (l3_mn, l3_p95, l3_n) = _measure_l0_l3_v2()

    print(f"L5 full-screen capture: min={l5_mn:.2f}ms  p95={l5_p95:.2f}ms  n={l5_n}")
    print(f"L0 peek (v2):           min={l0_mn:.3f}ms  p95={l0_p95:.3f}ms  n={l0_n}")
    print(f"L3 delta (v2):          min={l3_mn:.3f}ms  p95={l3_p95:.3f}ms  n={l3_n}")
    print("=== [bench-report] end ===")

    # Reporting instrument, not an assertion.
    assert True
