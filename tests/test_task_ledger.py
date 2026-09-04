"""Tests for the governed task ledger (core/coord/task_ledger) — Slice A.

These assert the GATES reject their failure modes. The ledger is pure (timestamps passed in, never
read from the clock), so every case is deterministic. Run: py -m pytest tests/test_task_ledger.py -q
"""
import os
import tempfile

import pytest

from core.coord import task_ledger as TL


def fresh(tmp_path):
    # client=None → git-only, no Redis mirror (keeps the state-machine tests hermetic)
    return TL.TaskLedger(os.path.join(str(tmp_path), "tasks.json"), client=None)


class FakeRedis:
    """Minimal in-memory stand-in for the Redis mirror — get/set only, values as str (real Redis
    returns bytes; read paths decode both)."""
    def __init__(self):
        self.kv = {}
    def set(self, k, v):
        self.kv[k] = v
    def get(self, k):
        return self.kv.get(k)


def test_transition_validity_blocks_claim_before_approve(tmp_path):
    L = fresh(tmp_path)
    t = L.propose("x", at="t0")
    with pytest.raises(TL.LedgerError, match="illegal transition"):
        TL.claim(L, t["id"], "claude", at="t1")


def test_claim_blocked_on_unmet_dep(tmp_path):
    L = fresh(tmp_path)
    a = L.propose("a", at="t0")
    b = L.propose("b", deps=[a["id"]], at="t0")
    TL.approve(L, b["id"], at="t1")
    with pytest.raises(TL.LedgerError, match="deps not DONE"):
        TL.claim(L, b["id"], "claude", at="t2")


def test_done_requires_commit_and_verification(tmp_path):
    L = fresh(tmp_path)
    t = L.propose("x", at="t0")
    TL.approve(L, t["id"], at="t1")
    TL.claim(L, t["id"], "claude", at="t2")
    TL.start(L, t["id"], at="t3")
    TL.verifying(L, t["id"], at="t4")
    with pytest.raises(TL.LedgerError, match="no proof"):
        TL.done(L, t["id"], commit="", verified_by="", at="t5")
    # 8-hex fixtures: T297's done gate (598be034) refuses commits under 7 hex chars;
    # 'abc123', 'c' and 'x' predated the validator.
    TL.done(L, t["id"], commit="abc12345", verified_by="pytest", at="t6")
    assert L.get(t["id"])["status"] == TL.DONE
    assert L.get(t["id"])["commit"] == "abc12345"


def test_two_watch_gate_caps_the_third(tmp_path):
    # Was test_one_in_progress_gate_serializes (Phase 1, one at a time) until operator ruling
    # art_20260903_width-ruling-2026-09-03_369243 set the cap at TWO watches (ORG Part 3).
    # The full gauge pins live in tests/test_width_gauge.py; this row keeps the gate's
    # presence pinned HERE, beside the other ledger gates.
    L = fresh(tmp_path)
    a = L.propose("a", files=["a.py"], at="t0")
    b = L.propose("b", files=["b.py"], at="t0")   # disjoint files, so only the width gate applies
    c = L.propose("c", files=["c.py"], at="t0")
    for t in (a, b, c):
        TL.approve(L, t["id"], at="t1")
        TL.claim(L, t["id"], "claude", at="t2")
    TL.start(L, a["id"], at="t3")
    TL.start(L, b["id"], at="t3")                 # two watches are lawful (the ruling's point)
    with pytest.raises(TL.LedgerError, match="two-watch"):
        TL.start(L, c["id"], at="t3")


def test_file_clash_blocks_claim(tmp_path):
    L = fresh(tmp_path)
    a = L.propose("a", files=["shared.py"], at="t0")
    b = L.propose("b", files=["shared.py"], at="t0")
    for t in (a, b):
        TL.approve(L, t["id"], at="t1")
    TL.claim(L, a["id"], "claude", at="t2")   # a now holds shared.py
    with pytest.raises(TL.LedgerError, match="files held"):
        TL.claim(L, b["id"], "deepseek", at="t2")


def test_done_is_terminal(tmp_path):
    L = fresh(tmp_path)
    t = L.propose("x", at="t0")
    TL.approve(L, t["id"], at="t1")
    TL.claim(L, t["id"], "claude", at="t2")
    TL.start(L, t["id"], at="t3")
    TL.verifying(L, t["id"], at="t4")
    TL.done(L, t["id"], commit="cafe5150", verified_by="v", at="t5")
    with pytest.raises(TL.LedgerError, match="terminal|illegal"):
        L.transition(t["id"], TL.IN_PROGRESS, at="t6")


def test_persists_and_reloads(tmp_path):
    p = os.path.join(str(tmp_path), "tasks.json")
    L = TL.TaskLedger(p, client=None)
    t = L.propose("persist me", at="t0")
    L2 = TL.TaskLedger(p, client=None)   # reload from disk
    assert L2.get(t["id"])["title"] == "persist me"


# --- Slice B: Redis mirror + fast reads --------------------------------------------------------
def test_save_mirrors_to_redis(tmp_path):
    fake = FakeRedis()
    L = TL.TaskLedger(os.path.join(str(tmp_path), "tasks.json"), client=fake)
    L.propose("mirror me", at="t0")
    assert TL.REDIS_LEDGER_KEY in fake.kv
    mirrored = TL.json.loads(fake.kv[TL.REDIS_LEDGER_KEY])
    assert mirrored["tasks"][0]["title"] == "mirror me"


def test_read_ledger_prefers_redis(tmp_path):
    fake = FakeRedis()
    fake.set(TL.REDIS_LEDGER_KEY, TL.json.dumps({"seq": 1, "tasks": [{"id": "T001", "title": "from-redis",
             "status": TL.PROPOSED, "deps": [], "files": []}]}))
    # git file does NOT exist here; the read must come from Redis
    out = TL.read_ledger(os.path.join(str(tmp_path), "nope.json"), client=fake)
    assert out["tasks"][0]["title"] == "from-redis"


def test_read_ledger_falls_back_to_git_when_redis_empty(tmp_path):
    p = os.path.join(str(tmp_path), "tasks.json")
    TL.TaskLedger(p, client=None).propose("only-in-git", at="t0")   # writes git file, no mirror
    out = TL.read_ledger(p, client=FakeRedis())   # empty fake → must fall back to git
    assert out["tasks"][0]["title"] == "only-in-git"


def test_state_view_next_needs_deps_done(tmp_path):
    p = os.path.join(str(tmp_path), "tasks.json")
    L = TL.TaskLedger(p, client=None)
    a = L.propose("a", at="t0"); b = L.propose("b", deps=[a["id"]], at="t0")
    TL.approve(L, a["id"], at="t1"); TL.approve(L, b["id"], at="t1")
    v = TL.state_view(p, client=None)
    ids_next = {t["id"] for t in v["next"]}
    assert a["id"] in ids_next and b["id"] not in ids_next   # b blocked: dep a not DONE
    # finish a → b becomes next
    TL.claim(L, a["id"], "c", at="t2"); TL.start(L, a["id"], at="t3")
    TL.verifying(L, a["id"], at="t4"); TL.done(L, a["id"], commit="ab5ca1e0", verified_by="v", at="t5")
    v2 = TL.state_view(p, client=None)
    assert {t["id"] for t in v2["done"]} == {a["id"]}
    assert b["id"] in {t["id"] for t in v2["next"]}


def test_sync_redis_from_git(tmp_path):
    p = os.path.join(str(tmp_path), "tasks.json")
    TL.TaskLedger(p, client=None).propose("git-truth", at="t0")
    fake = FakeRedis()
    assert TL.sync_redis_from_git(p, client=fake) is True
    assert TL.json.loads(fake.kv[TL.REDIS_LEDGER_KEY])["tasks"][0]["title"] == "git-truth"


# --- Slice C: read-state-first formatter -------------------------------------------------------
def test_format_state_empty(tmp_path):
    s = TL.format_state(path=os.path.join(str(tmp_path), "none.json"), client=None)
    assert "empty" in s and "no governed tasks" in s


def test_format_state_shows_done_next_and_rule(tmp_path):
    p = os.path.join(str(tmp_path), "tasks.json")
    L = TL.TaskLedger(p, client=None)
    a = L.propose("done one", at="t0"); b = L.propose("next one", deps=[a["id"]], owner="claude", at="t0")
    for t in (a, b):
        TL.approve(L, t["id"], at="t1")
    TL.claim(L, a["id"], "claude", at="t2"); TL.start(L, a["id"], at="t3")
    TL.verifying(L, a["id"], at="t4"); TL.done(L, a["id"], commit="deadbeef", verified_by="v", at="t5")
    s = TL.format_state(agent="claude", path=p, client=None)
    assert "DONE" in s and "deadbeef" in s          # closed task shown with its commit
    assert "NEXT" in s and "next one" in s and "<- you" in s   # b claimable, tagged for its owner
    assert "obey THIS, not old messages" in s and "in DONE is closed" in s


# --- releasing a claim -------------------------------------------------------------------------
# PARKED was designed for work shelved MID-FLIGHT, so only IN_PROGRESS could reach it. But a task
# can sit CLAIMED and never start, and that is the state that actually accumulates: claiming is
# free, releasing is not. The only exits from CLAIMED were ABANDONED (destructive -- says the intent
# DIED when it merely DRIFTED) and APPROVED (takes no reason, so the shelving rationale is lost).
# Live receipt 2026-07-31: 21 ACTIVE tasks, 16 of them CLAIMED-not-started, none parkable without
# routing each through the single serialized IN_PROGRESS slot -- 16 false in_progress transitions
# written into a git-durable audit trail purely to reach a legal state.

def test_claimed_can_park_without_faking_a_start(tmp_path):
    L = fresh(tmp_path)
    t = L.propose("claimed but never started", files=["x.py"], at="t0")
    TL.approve(L, t["id"], at="t1")
    TL.claim(L, t["id"], "claude", at="t2")
    TL.park(L, t["id"], "wave 3 -- unpark after the grade", at="t3")
    got = L.get(t["id"])
    assert got["status"] == TL.PARKED
    assert got["owner"] == "claude"                              # parking is not disowning
    # the debt must survive the release AND stay reachable -- reason lives on the history entry,
    # not the task record, and _park_reason is what every surface reads it back through
    assert got["history"][-1]["reason"] == "wave 3 -- unpark after the grade"
    v = TL.ledger_view(path=None, ledger=L) if hasattr(TL, "ledger_view") else None
    if v:
        assert v["parked"][0]["reason"] == "wave 3 -- unpark after the grade"


def test_verifying_can_park(tmp_path):
    L = fresh(tmp_path)
    t = L.propose("awaiting verification", at="t0")
    TL.approve(L, t["id"], at="t1")
    TL.claim(L, t["id"], "claude", at="t2")
    TL.start(L, t["id"], at="t3")
    TL.verifying(L, t["id"], at="t4")
    TL.park(L, t["id"], "shelved before verification landed", at="t5")
    assert L.get(t["id"])["status"] == TL.PARKED


def test_parked_claim_frees_the_serialize_slot_but_keeps_its_files(tmp_path):
    L = fresh(tmp_path)
    a = L.propose("a", files=["shared.py"], at="t0")
    b = L.propose("b", files=["other.py"], at="t0")
    for t in (a, b):
        TL.approve(L, t["id"], at="t1")
        TL.claim(L, t["id"], "claude", at="t2")
    TL.park(L, a["id"], "shelved", at="t3")
    TL.start(L, b["id"], at="t4")                    # a parked claim must not block the slot
    assert L.get(b["id"])["status"] == TL.IN_PROGRESS
    assert L.files_held()["shared.py"] == a["id"]    # shelved work still owns its files
