"""
RB-25 Drill 2 -- STORE-DIVERGENCE HEAL: pre-registered acceptance (committed BEFORE the
H2b fix, M3/T031). Runbook bars: docs/library/design/20260711_rb-25-engine-exam-runbook-pre-registered_9356ea.md drill 3 section
(H1/H2/H2b/H4), amended pre-drill to the reconciler's UNIDIRECTIONAL contract (File is
source of truth; deepseek fence review research/reviewed/deepseek-rb25-runbook-review-
2026-07-11.md).

Isolation is mandatory (REDIS_DB=15 + a temp file): the heal touches store keys, and the
live notes/ledger must never be a drill target. Every test cleans its db15 keyspace.

Contract frozen:
  HybridStore.heal_report() -> List[str]: the OPERATOR-FACING heal. Runs check_drift +
    reconcile, returns render lines. MUST include a File->Redis backfill line when Redis
    was behind (H2) AND a loud missing_in_file line when Redis holds orphan keys the
    contract refuses to backfill (H2b -- the gap surfaced honestly, not silently dropped).
    Empty list when the backends are in sync.

Run: py -m pytest tests/test_rb25_drill2_heal.py -q
"""
import os
import tempfile

import pytest

os.environ.setdefault("REDIS_DB", "15")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import HybridStore

try:
    _probe = HybridStore.create(file_path=os.path.join(tempfile.gettempdir(), "rb25d2probe.json"), db=15)
    _ONLINE = _probe.redis_available
except Exception:
    _ONLINE = False

pytestmark = pytest.mark.skipif(not _ONLINE, reason="drill needs a live Redis on db15")

_HAS_REPORT = hasattr(HybridStore, "heal_report")


@pytest.fixture()
def store():
    # check_drift/heal_report scan the FULL keyspace ("*"), so a shared db15 lets other
    # tests' residue leak into this drill's drift (exact-match assertions failed in the
    # full suite though they passed isolated). db15 is the DISPOSABLE test db -- clear it
    # whole at setup so the drill sees only its own injected divergence. The File side is
    # already isolated (a fresh temp file per test).
    d = tempfile.mkdtemp()
    s = HybridStore.create(file_path=os.path.join(d, "drill2.json"), db=15)
    for k in s._redis.keys("*"):
        s._redis.delete(k)
    yield s
    for k in s._redis.keys("*"):
        s._redis.delete(k)


def _diverge(s):
    """(a) File-ahead: key in File only (Redis was down mid-write). (b) Redis-only:
    key in Redis only -- the missing_in_file gap the contract deliberately never backfills."""
    s._file.set("rb25d2:file-ahead", "FILE_TRUTH")
    s._redis.set("rb25d2:redis-only", "REDIS_ORPHAN")


# --- H1: File-ahead divergence heals INTO Redis (the documented direction) ---

def test_h1_file_ahead_backfills_redis(store):
    _diverge(store)
    assert store.check_drift()["missing_in_redis"] == ["rb25d2:file-ahead"]
    rep = store.reconcile()
    assert rep["status"] == "success" and rep["written"]["kv"] >= 1
    assert store._redis.get("rb25d2:file-ahead") == "FILE_TRUTH", "File won, Redis backfilled"


# --- H2b (contract half): the Redis-only orphan is surfaced, NEVER backfilled into File ---

def test_h2b_redis_orphan_surfaced_and_file_untouched(store):
    _diverge(store)
    store.reconcile()
    assert store._file.get("rb25d2:redis-only") is None, \
        "File is source of truth -- a Redis-only key is NEVER written into File"
    assert store.check_drift()["missing_in_file"] == ["rb25d2:redis-only"], \
        "the gap stays reported after heal -- surfaced honestly, not silently dropped"


# --- H2 + H2b (render half): the operator-facing heal SAYS BOTH out loud ---

@pytest.mark.skipif(not _HAS_REPORT, reason="H2b render pre-registered; heal_report pending")
def test_h2_and_h2b_operator_report(store):
    _diverge(store)
    lines = store.heal_report()
    blob = " ".join(lines).lower()
    assert any("backfill" in l.lower() for l in lines), "H2: the File->Redis heal is announced"
    assert "rb25d2:redis-only" in blob or "missing_in_file" in blob or "orphan" in blob, \
        "H2b: the Redis-only gap is LOUD to the operator, not silently healed-around"


@pytest.mark.skipif(not _HAS_REPORT, reason="H2b render pre-registered; heal_report pending")
def test_heal_report_quiet_when_in_sync(store):
    # no divergence injected -> nothing to say
    assert store.heal_report() == [], "in-sync backends produce no operator noise"


# --- H4: the heal is idempotent (re-running after a heal is a safe no-op on the healed side) ---

def test_h4_reconcile_idempotent(store):
    _diverge(store)
    store.reconcile()
    rep2 = store.reconcile()
    assert rep2["status"] == "success", "re-running the heal never errors (durable, repeatable)"
