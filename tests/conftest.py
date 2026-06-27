"""
Pytest bootstrap for the test suite.

Puts the repo root AND this tests/ directory on sys.path so tests can import both
project packages (``core.*``, ``context.*``) and test-local helpers (``isolate_canonical``,
``narrative_metrics``, ``fixtures.*``) regardless of the invocation cwd. Previously
several tests only collected when pytest happened to be run from inside tests/ -- this
makes ``py -m pytest tests/`` from the repo root work the same way.

No side effects beyond sys.path: isolation (Redis db 15 + temp AI_SETUP) stays opt-in
per-test via ``import isolate_canonical`` so suites that intentionally exercise the real
backends are unaffected.
"""
import os
import sys

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_TESTS)
for _p in (_ROOT, _TESTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)
