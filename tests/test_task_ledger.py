"""Tests for the governed task ledger (core/coord/task_ledger) — Slice A.

These assert the GATES reject their failure modes. The ledger is pure (timestamps passed in, never
read from the clock), so every case is deterministic. Run: py -m pytest tests/test_task_ledger.py -q
"""
import os
import tempfile

import pytest

from core.coord import task_ledger as TL


def fresh(tmp_path):
    return TL.TaskLedger(os.path.join(str(tmp_path), "tasks.json"))


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
    TL.done(L, t["id"], commit="abc123", verified_by="pytest", at="t6")
    assert L.get(t["id"])["status"] == TL.DONE
    assert L.get(t["id"])["commit"] == "abc123"


def test_one_in_progress_gate_serializes(tmp_path):
    L = fresh(tmp_path)
    a = L.propose("a", files=["a.py"], at="t0")
    b = L.propose("b", files=["b.py"], at="t0")   # disjoint files, so only the serialize gate applies
    for t in (a, b):
        TL.approve(L, t["id"], at="t1")
        TL.claim(L, t["id"], "claude", at="t2")
    TL.start(L, a["id"], at="t3")
    with pytest.raises(TL.LedgerError, match="serialize"):
        TL.start(L, b["id"], at="t3")


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
    TL.done(L, t["id"], commit="c", verified_by="v", at="t5")
    with pytest.raises(TL.LedgerError, match="terminal|illegal"):
        L.transition(t["id"], TL.IN_PROGRESS, at="t6")


def test_persists_and_reloads(tmp_path):
    p = os.path.join(str(tmp_path), "tasks.json")
    L = TL.TaskLedger(p)
    t = L.propose("persist me", at="t0")
    L2 = TL.TaskLedger(p)   # reload from disk
    assert L2.get(t["id"])["title"] == "persist me"
