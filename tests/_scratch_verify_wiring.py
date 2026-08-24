"""Scratch: verify conductor_gate function-gate state precisely. Run then DELETE."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.checkers.check_wiring as cw


def test_precise():
    core_universe, reachable, unwired = cw.analyze()
    cg = "core/comm/conductor_gate.py"
    assert cg in reachable, "not reachable"
    cand = cw.candidate_modules(reachable, core_universe)
    _cand, prod, orphans, fn_stale = cw.function_level(reachable, core_universe)
    cg_orphans = [(m, n, lo) for m, n, lo in orphans if m == cg]
    print("conductor_gate in prod files:", cg in prod)
    print("conductor_gate orphans:", [n for _m, n, _lo in cg_orphans])
    # check baseline
    bl = cw.load_baseline()
    new_orphans = [(m, n, lo) for m, n, lo in orphans if f"{m}::{n}" not in bl]
    print("NEW orphans (would FAIL):", [(m, n) for m, n, _ in new_orphans if m == cg])
