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


# =================================================================================================
# 77e485bb23, second half: the CAS anchor was the WRONG NUMBER.
#
# T270 compared `seq` -- the task-id ALLOCATOR -- which only propose() advances. transition()
# saves with seq unchanged, so a transition never moved the anchor: transition-vs-transition and
# propose-vs-transition from two processes still ended in last-save-wins (verified at pristine
# HEAD: A's committed approval reverted to 'proposed' by B's stale save, no error anywhere).
# The anchor must be a per-SAVE revision (`rev`), so ANY write by ANY process is visible.
#
# And a compare-then-replace with no lock is a TOCTOU, not a CAS: two savers can both pass the
# check and both replace. The house primitive core.foundation.filelock.exclusive (born from the
# same silent-loss shape in the bridge inbox) closes that window across processes.
#
# Pins below are deterministic: the interleaving is sequenced by hand, like the T270 pins above.
# =================================================================================================

import json
import subprocess
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _statuses(p):
    return {t["id"]: t["status"] for t in TL.read_ledger(p, client=None)["tasks"]}


def _seed_two(p):
    A = _ledger(p)
    A.propose("one", at="t1")
    A.propose("two", at="t2")
    return A


def test_stale_transition_is_refused_not_clobbered(path):
    """A and B load the same ledger; A approves T001; B (stale) approves T002. B's save
    must be REFUSED -- it would write T001 back to 'proposed', erasing A's commit."""
    A = _seed_two(path)
    B = _ledger(path)                                   # same on-disk snapshot as A

    A.transition("T001", TL.APPROVED, by="user", at="t3")   # A commits

    with pytest.raises(TL.LedgerError) as exc_info:
        B.transition("T002", TL.APPROVED, by="user", at="t4")
    assert "lost-update" in str(exc_info.value), (
        "the refusal must name the lost-update so the caller knows to re-read")

    assert _statuses(path)["T001"] == TL.APPROVED, (
        "B's stale transition clobbered A's committed approval (seq never moved, so the "
        "old seq-anchored CAS could not see A's write)")


def test_stale_propose_after_peer_transition_is_refused(path):
    """A approves T001; B (stale) proposes. seq moved on B's side only, and the disk seq still
    equals B's watermark -- the old anchor passes and B writes T001 back as 'proposed'."""
    A = _ledger(path)
    A.propose("one", at="t1")
    B = _ledger(path)

    A.transition("T001", TL.APPROVED, by="user", at="t2")

    with pytest.raises(TL.LedgerError):
        B.propose("two", at="t3")

    assert _statuses(path)["T001"] == TL.APPROVED, (
        "B's stale propose silently reverted A's approval")


def test_rev_advances_on_every_save_not_only_on_propose(path):
    """The anchor is a per-SAVE revision. A transition moves it exactly like a propose does."""
    A = _ledger(path)
    A.propose("one", at="t1")
    with open(path, encoding="utf-8") as fh:
        first = json.load(fh)
    A.transition("T001", TL.APPROVED, by="user", at="t2")
    with open(path, encoding="utf-8") as fh:
        second = json.load(fh)
    assert first.get("rev") == 1 and second.get("rev") == 2, (first.get("rev"), second.get("rev"))
    assert first["seq"] == second["seq"] == 1, "seq is the id allocator; a transition leaves it"


def test_refused_instance_resyncs_to_disk_truth(path):
    """After a refusal the instance must mirror the DISK, not its own unwritten mutation: a
    retry on the same instance then re-decides against what is actually there. Without this
    the losing instance keeps a phantom task and an advanced seq in memory (poisoned), and the
    only long-lived writer in the house (scripts/shift_daemon.py) is refused forever."""
    A = _ledger(path)
    A.propose("one", at="t1")
    B = _ledger(path)
    A.transition("T001", TL.APPROVED, by="user", at="t2")

    with pytest.raises(TL.LedgerError):
        B.propose("two", at="t3")

    assert B.get("T001")["status"] == TL.APPROVED, "B still holds its stale snapshot"
    assert "T002" not in B.tasks, "B kept the phantom task its refused save never wrote"

    t = B.propose("two", at="t4")                       # same instance, now fresh: succeeds
    assert t["id"] == "T002"
    assert _statuses(path) == {"T001": TL.APPROVED, "T002": TL.PROPOSED}


def test_save_refuses_while_a_peer_holds_the_ledger_lock(path, monkeypatch):
    """The compare-then-replace runs under the ledger's sidecar lock (path + '.lock', the
    house filelock). While a peer holds it, a save WAITS (bounded) and then REFUSES -- it never
    proceeds unprotected, and it never touches the file."""
    from core.foundation import filelock
    A = _ledger(path)
    A.propose("one", at="t1")
    B = _ledger(path)
    monkeypatch.setattr(TL, "LOCK_TIMEOUT_S", 0.2, raising=False)

    with filelock.exclusive(path):                      # the peer, mid-save
        with pytest.raises(TL.LedgerError) as exc_info:
            B.propose("two", at="t2")
        assert "lock" in str(exc_info.value).lower()
        assert set(_statuses(path)) == {"T001"}, "a refused save must not have written"

    B.propose("two", at="t3")                           # lock released: the same write lands
    assert set(_statuses(path)) == {"T001", "T002"}


def test_lock_is_honoured_across_processes(path, tmp_path, monkeypatch):
    """The lock is arbitrated by the OS, not by one interpreter: a SEPARATE process holding
    the ledger lock keeps this process's save out until it lets go."""
    marker = str(tmp_path / "held")
    child_src = (
        "import sys, time\n"
        f"sys.path.insert(0, {_ROOT!r})\n"
        "from core.foundation import filelock\n"
        f"with filelock.exclusive({path!r}):\n"
        f"    open({marker!r}, 'w').close()\n"
        "    time.sleep(2.5)\n")
    A = _ledger(path)
    A.propose("one", at="t1")
    B = _ledger(path)
    monkeypatch.setattr(TL, "LOCK_TIMEOUT_S", 0.3, raising=False)

    proc = subprocess.Popen([sys.executable, "-c", child_src], cwd=_ROOT)
    try:
        deadline = time.monotonic() + 15
        while not os.path.exists(marker):
            assert proc.poll() is None, "lock-holder child died before taking the lock"
            assert time.monotonic() < deadline, "lock-holder child never signalled"
            time.sleep(0.02)
        with pytest.raises(TL.LedgerError):
            B.propose("two", at="t2")                   # child holds the lock: refused
        assert set(_statuses(path)) == {"T001"}
    finally:
        proc.wait(timeout=30)

    B.propose("two", at="t3")                           # child gone: the write lands
    assert set(_statuses(path)) == {"T001", "T002"}


def test_unreadable_anchor_refuses_instead_of_overwriting(path):
    """If the on-disk ledger cannot be read, the anchor is UNKNOWN -- save refuses rather
    than 'assume unchanged' and pave over it (the pre-fix fail-open; under the lock an
    unreadable file is never a peer mid-write, it is damage a human restores from git)."""
    A = _ledger(path)
    A.propose("one", at="t1")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{ this is not json")
    with pytest.raises(TL.LedgerError):
        A.propose("two", at="t2")
    with open(path, encoding="utf-8") as fh:
        assert fh.read() == "{ this is not json", "the damaged ledger was overwritten"


def test_conductor_reapplies_after_a_peer_write(tmp_path, monkeypatch):
    """The conductor door (every `task` verb) turns a lost-update refusal into a re-read and
    re-apply: two DISJOINT transitions from two processes both land, in order, with the gates
    re-evaluated against the fresh state. A gate refusal is an answer and is never retried."""
    from core.coord import conductor as C
    monkeypatch.setattr(C, "_broadcast", lambda *a, **k: None)
    p = str(tmp_path / "t.json")
    k = dict(client=None, path=p)
    C.propose("one", **k)
    C.propose("two", **k)

    real = C._ledger
    fired = []

    def _ledger_with_a_peer_in_the_gap(client="auto", path=None):
        led = real(client, path)
        if not fired:                                   # first load only: a peer writes AFTER it
            fired.append(1)
            TL.TaskLedger(p, client=None).transition("T001", TL.APPROVED, by="peer", at="t9")
        return led

    monkeypatch.setattr(C, "_ledger", _ledger_with_a_peer_in_the_gap)
    C.approve("T002", **k)                              # stale on first try; must re-apply

    assert _statuses(p) == {"T001": TL.APPROVED, "T002": TL.APPROVED}, (
        "the conductor either clobbered the peer's approval or surfaced the refusal instead "
        "of re-reading and re-applying")
    assert len(fired) == 1

    calls = []

    def _counting(client="auto", path=None):
        calls.append(1)
        return real(client, path)

    monkeypatch.setattr(C, "_ledger", _counting)
    C.claim("T001", "claude", **k)
    calls.clear()
    with pytest.raises(TL.LedgerError):                 # claimed -> claimed: a GATE refusal
        C.claim("T001", "claude", **k)
    assert len(calls) == 1, "a gate refusal is an answer; it must not be retried"
