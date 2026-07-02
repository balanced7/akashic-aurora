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
