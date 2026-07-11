"""
Wave 3 / RB-11 + RB-12 -- pre-registered acceptance (committed BEFORE impl, M3/T031).
Spec: docs/w3-build-spec-2026-07-11.md sections RB-11, RB-12.

RB-11 migration idempotency pin-key + chain-length warning (render-side, threshold 50).
RB-12 deterministic ordering (created_at, title, id) + graceful empty state.

Contract frozen here:
  AgentMemory.run_migration_once(name, fn) -> bool        (True = ran; cas-guarded pin key)
  CHAIN_WARN_THRESHOLD = 50                               (module constant, future T034 dial)
  AgentMemory.get_long_chains(threshold=None) -> List[dict]
  get_decisions() sort = (created_at, title, id) descending, stable across calls/backends

Boot-render empty-state [GAP] lines are integration-pinned in the RB-12 impl commit itself
(they need the agent_cli render layer); the memory-layer half is pinned here.

Run: py -m pytest tests/test_w3_rb11_rb12.py -q
"""
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.foundation.store import DictStore
    from core.learning.agent_memory import (
        CHAIN_WARN_THRESHOLD, AgentMemory, Decision,
    )
    _BUILT = hasattr(AgentMemory, "run_migration_once") and \
        hasattr(AgentMemory, "get_long_chains")
except ImportError:
    _BUILT = False

pytestmark = pytest.mark.skipif(
    not _BUILT, reason="RB-11/RB-12 pins pre-registered; impl pending (assertions frozen)")


@pytest.fixture()
def mem():
    return AgentMemory(store=DictStore())


def _forge(mem, dec_id, title, created, superseded=False):
    d = Decision(id=dec_id, title=title, status="accepted", context="", decision="x",
                 rationale=[], alternatives=[], consequences={"positive": [], "negative": []},
                 created_at=created, session_id="", supersedes=None, superseded=superseded)
    mem.store.hset(mem.KEY_DECISIONS, field=dec_id, value=json.dumps(asdict(d)))
    mem.store.zadd(mem.KEY_DECISION_INDEX,
                   {dec_id: datetime.fromisoformat(created).timestamp()})


# ---------------- RB-11 ----------------

def test_migration_runs_once_and_only_once(mem):
    runs = []
    assert mem.run_migration_once("w3-test-mig", lambda: runs.append(1)) is True
    assert mem.run_migration_once("w3-test-mig", lambda: runs.append(1)) is False
    assert runs == [1], "second invocation is a no-op (cas-guarded pin key)"


def test_migration_pin_key_is_cas_guarded_per_name(mem):
    a, b = [], []
    mem.run_migration_once("mig-a", lambda: a.append(1))
    mem.run_migration_once("mig-b", lambda: b.append(1))
    assert a == [1] and b == [1], "pin keys are per-name, not global"


def test_chain_warning_boundary_51_not_49(mem):
    t = datetime(2026, 1, 1)
    for n, count in (("short-chain", 49), ("long-chain", 51)):
        for i in range(count):
            _forge(mem, "ADR_%s_%08d" % (n[:2], i), n,
                   t.replace(second=(i % 50), minute=i // 50).isoformat(),
                   superseded=(i < count - 1))
    long_titles = {c.get("title") for c in mem.get_long_chains()}
    assert "long-chain" in long_titles and "short-chain" not in long_titles
    assert CHAIN_WARN_THRESHOLD == 50


def test_default_read_path_does_not_scan_chains(mem):
    calls = []
    orig = mem.get_long_chains
    mem.get_long_chains = lambda *a, **k: (calls.append(1), orig(*a, **k))[1]
    mem.get_decisions(days=30)
    assert calls == [], "the warning scan is render-side, never on the default read"


# ---------------- RB-12 ----------------

def test_same_timestamp_ties_are_stable_and_total(mem):
    ts = datetime(2026, 3, 3, 3, 3, 3).isoformat()
    for i, title in enumerate(["zeta-status", "alpha-status", "mid-status"]):
        _forge(mem, "ADR_tie_%08d" % i, title, ts)
    orders = [tuple(d.id for d in mem.get_decisions(days=3650)) for _ in range(5)]
    assert len(set(orders)) == 1, "same corpus -> identical order, five reads"
    titles = [d.title for d in mem.get_decisions(days=3650)]
    assert titles == sorted(titles, reverse=True), \
        "(created_at, title, id) descending: title is the tiebreak at equal timestamps"


def test_empty_store_reads_are_calm(mem):
    assert mem.get_decisions(days=3650) == []
    assert mem.get_retired_titles() == [] if hasattr(mem, "get_retired_titles") else True
    assert mem.get_long_chains() == []
