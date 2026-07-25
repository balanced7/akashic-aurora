"""
Pytest bootstrap for the test suite.

Puts the repo root AND this tests/ directory on sys.path so tests can import both
project packages (``core.*``, ``context.*``) and test-local helpers (``isolate_canonical``,
``narrative_metrics``, ``fixtures.*``) regardless of the invocation cwd. Previously
several tests only collected when pytest happened to be run from inside tests/ -- this
makes ``py -m pytest tests/`` from the repo root work the same way.

Backend isolation (Redis db 15 + temp AI_SETUP) stays opt-in per-test via
``import isolate_canonical`` so suites that intentionally exercise the real backends are
unaffected. Recall SCRATCH state is the one universal exception (see below).
"""
import os
import sys
import tempfile

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_TESTS)
for _p in (_ROOT, _TESTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Recall scratch state (warm cache / seen / impressions / flips / nudges / injections) is
# UNIVERSALLY isolated: core/recall/at_action.py and the hook scripts derive their state dir
# from this env var at import time. Without it, any test that transitively warms the cache
# (e.g. a hook main()) OVERWRITES the production cache file with isolated-store contents --
# live recall then serves [] until the TTL heals it (found 2026-07-02 by dogfooding: 64 green
# unit tests + a blank production cache). Unlike backend isolation, NO test ever legitimately
# wants the real recall scratch, so this one is unconditional.
os.environ.setdefault("AKASHIC_RECALL_STATE_DIR",
                      tempfile.mkdtemp(prefix="akashic_recall_test_"))

# ---------------------------------------------------------------------------
# T070: BACKEND ISOLATION IS NOW UNIVERSAL TOO (2026-07-25).
#
# It used to be opt-in per file via `import isolate_canonical`, on the reasoning that some
# suites "intentionally exercise the real backends". The census that ended that argument:
# 150 test files touch a default store or knowledge surface; EIGHT imported the helper. The
# other 142 were free to read and write canonical Redis db 0 and the live
# session_logs/store_state.json -- which is exactly the standing hazard every boot carried,
# "the pytest suite DESTROYS the live learning index, run repair_learning_index --check
# after ANY suite run".
#
# The opt-in never protected what it claimed to: isolate_canonical redirects Redis to
# **db 15**, not to nothing, so a test that wants a live Redis still gets one. Only a test
# asserting on CANONICAL CONTENT could break -- and those are flaky by construction, which
# T070 itself recorded (a boot under the flag read live data, "8 lesson(s)", and live notes
# leaked non-ASCII into an ASCII pin).
#
# The real cost was second-order: a suite that is dangerous to run is a suite nobody runs.
# It rotted unnoticed until CI was found red for over a day with the whole suite skipped.
# The hazard and the rot were one loop.
#
# So this mirrors the recall-scratch decision immediately above -- isolate by default, and
# make the escape hatch explicit rather than implicit-by-forgetting.
if not os.environ.get("AKASHIC_TEST_USE_CANONICAL"):
    import isolate_canonical  # noqa: F401,E402  (side-effect: temp AI_SETUP + db 15 + flush)
else:
    # Deliberate operator override, e.g. reproducing a canonical-state incident. Loud, so
    # nobody discovers afterwards that a run touched real data.
    print("[conftest] AKASHIC_TEST_USE_CANONICAL set -- tests will touch REAL backends. "
          "Run scripts/repair_learning_index.py --check afterwards.")
