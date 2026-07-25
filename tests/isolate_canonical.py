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
from pathlib import Path

# Make config importable regardless of the importing test's own path setup.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

def _already_redirected() -> bool:
    """Is isolation ACTUALLY in force -- not merely claimed?

    The flag `_AISETUP_TEST_ISOLATED` used to guard this whole block, which meant a process
    that merely INHERITED the flag skipped isolation and ran against canonical while every
    reader believed it was isolated. It is a claim, not proof.

    This cost the corpus twice on 2026-07-25: fixture lessons written into canonical Redis
    db 0 at 14:25 (vector unidentified at the time), and at 20:11 the live learning index
    collapsed to FIVE entries -- 437 lessons, 98% of the corpus, invisible to every keyword
    search -- when a peer ran the full suite through an exec door that pre-set the flag.

    So: verify the CONDITION. AI_SETUP must point somewhere other than the real repo, and
    REDIS_DB must not be the canonical logical db. The flag is kept only as a cheap
    re-entrancy marker; it is never the authority.
    """
    ai = os.environ.get("AI_SETUP")
    db = os.environ.get("REDIS_DB")
    if not ai or not db:
        return False
    try:
        if Path(ai).resolve() == Path(_ROOT).resolve():
            return False          # pointed at the live repo: not isolated, whatever the flag says
    except Exception:
        return False              # cannot tell -> assume NOT isolated (fail safe, not silent)
    return str(db).strip() not in ("", "0")


if not _already_redirected():
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
