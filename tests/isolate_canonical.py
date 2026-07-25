"""
Import this FIRST in any test that may touch a DEFAULT store/ledger/memory.

It gives the test process a clean, throwaway knowledge layer, BEFORE the foundation
resolves its defaults:
  - the FILE store  -> a per-process temp AI_SETUP dir (fresh every run)
  - the REDIS DB    -> logical db 15 (REDIS_TEST_DB), FLUSHED clean on import

So tests can never read or write canonical data (the live knowledge store on db 0 /
the real session_logs/store_state.json). This is the root-cause fix for the
2026-06-20 incident where running the suite polluted the canonical knowledge store.

Why flush db 15 here: the temp AI_SETUP dir is fresh per run, but the Redis test DB
is a *shared, persistent* logical DB. Without a flush, Redis-backed state (blockers,
decisions, signals) accumulates across test runs and makes count-based assertions
flaky. Flushing on import guarantees each isolated test process starts empty.

Usage (must precede `from core.foundation...`):

    import sys, os
    import isolate_canonical            # noqa: F401  (side-effect: isolates + flushes)
    sys.path.insert(0, <project root>)
    from core.foundation.store import ...
"""
import os
import sys
import tempfile

# Make config importable regardless of the importing test's own path setup.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if not os.environ.get("_AISETUP_TEST_ISOLATED"):
    _tmp = tempfile.mkdtemp(prefix="aisetup_test_")
    os.makedirs(os.path.join(_tmp, "session_logs"), exist_ok=True)
    os.environ["AI_SETUP"] = _tmp
    try:
        from config import REDIS_TEST_DB
        os.environ["REDIS_DB"] = str(REDIS_TEST_DB)
    except Exception:
        os.environ["REDIS_DB"] = "15"
    # Side channels that derive their own root instead of reading AI_SETUP must be redirected
    # EXPLICITLY. agent_cli.py:83 builds the spill dir from `__file__` -- the location of
    # agent_cli.py, which is always the real repo -- so redirecting AI_SETUP cannot reach it.
    # Found 2026-07-25: a T070 acceptance run that left the STORE clean (434 -> 434) still
    # wrote state/spill/actual_outcome-*.txt into canonical. Verifying the store and missing
    # the side channel is how the hazard got reported retired while a hole remained.
    os.environ["AKASHIC_SPILL_DIR"] = os.path.join(_tmp, "spill")
    os.makedirs(os.environ["AKASHIC_SPILL_DIR"], exist_ok=True)
    os.environ["_AISETUP_TEST_ISOLATED"] = "1"

    # Start from an empty test DB so Redis-backed state can't accumulate across runs.
    try:
        import redis
        from config import REDIS_HOST, REDIS_PORT
        redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=int(os.environ["REDIS_DB"]),
                    socket_connect_timeout=0.5).flushdb()
    except Exception:
        pass   # Redis down -> file-only isolation is enough
