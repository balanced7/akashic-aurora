"""RED -> GREEN: TaskLedger.save() now compare-and-swaps on the on-disk seq.

The defect (deferred 77e485bb23): two processes each hold a TaskLedger loaded from the same
on-disk seq=N, both propose -> both compute seq=N+1 -> both save -> the second os.replace
clobbers the first's whole-file write, and both believe they succeeded (the FileStore
coherence class, on the governed allocator; live seq=367/T368 race).

The fix (T270): save() refuses when the file's seq has advanced past this instance's
watermark (_base_seq). A lost update is PREVENTED by refusal — the caller re-reads and
re-decides — rather than silently applied. This matches the house's CASConflict/LedgerError
pattern (core/foundation/store.py, tests/test_store_cas.py).

This pin is deterministic (no race): it SEQUENCES the interleaving by hand, like
test_filestore_coherence.py, and asserts the REFUSED contract.

Run: py -m pytest tests/test_task_ledger_cas.py -v
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import task_ledger as TL


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "tasks.json")


def _ledger(p):
    return TL.TaskLedger(p, client=None)


def test_second_proposer_is_refused_not_silently_lost(path):
    # A and B both open the SAME ledger file (fresh, seq=0) before either writes.
    A = _ledger(path)
    B = _ledger(path)     # B loads the SAME on-disk state A holds

    A.propose("task from A", at="t-a")   # A commits seq=1 to disk

    # B, still holding its stale seq=0 snapshot, tries to propose. The fix REFUSES it.
    with pytest.raises(TL.LedgerError) as exc_info:
        B.propose("task from B", at="t-b")
    assert "lost-update" in str(exc_info.value) or "advanced" in str(exc_info.value), (
        "the refusal must name the lost-update, so the caller knows to re-read")

    # A's committed task survived intact — nothing was clobbered.
    titles = {t["title"] for t in TL.read_ledger(path, client=None)["tasks"]}
    assert titles == {"task from A"}, f"A's commit was lost or corrupted: {titles}"


def test_refusal_is_loud_not_silent(path):
    """The dangerous half reversed: the pre-fix save() returned None (success) even while it was
    erasing a peer's commit. Post-fix, the losing save RAISES — a receipt that reports a write it
    would lose is gone; the caller is told instead of confidently continuing on stale state."""
    A = _ledger(path)
    B = _ledger(path)
    A.propose("A first", at="t-a")
    assert "A first" in {t["title"] for t in TL.read_ledger(path, client=None)["tasks"]}

    # B (stale) proposing does NOT silently destroy A — it raises.
    with pytest.raises(TL.LedgerError):
        B.propose("B second", at="t-b")

    titles = {t["title"] for t in TL.read_ledger(path, client=None)["tasks"]}
    assert "A first" in titles, "the refused write must not have clobbered the committed one"


def test_same_instance_sequential_proposes_still_succeed(path):
    """Regression guard: a single process proposing repeatedly advances its own watermark each
    save, so the CAS never false-positives on normal sequential use."""
    A = _ledger(path)
    A.propose("one", at="t1")
    A.propose("two", at="t2")
    A.propose("three", at="t3")
    titles = {t["title"] for t in TL.read_ledger(path, client=None)["tasks"]}
    assert titles == {"one", "two", "three"}
