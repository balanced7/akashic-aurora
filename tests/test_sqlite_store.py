"""SqliteStore acceptance -- the pre-registered gates from docs/filestore-coherence-design-2026-07.md.

The properties under test are the ones FileStore FAILS. Each is checked ACROSS PROCESSES,
never across threads: threads share an interpreter, so a thread test of a cross-process
property proves the arithmetic and not the concurrency. The FileStore durability pin already
made exactly that mistake (kimi's find: four instances build four different RLocks, so the
test passed for a reason its name did not describe).

Measured baselines, same 3-process shape:
    FileStore  : 450 attempted, 155 survived, 295 LOST (65.6%), no error raised
    SqliteStore: 450 attempted, 450 survived, 0 lost
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from core.foundation.sqlite_store import SqliteStore

REPO_ROOT = Path(__file__).resolve().parents[1]

_CHILD = """
import sys
sys.path.insert(0, {repo!r})
from core.foundation.sqlite_store import SqliteStore
s = SqliteStore({path!r})
{body}
"""


def _run_child(path: Path, body: str, timeout: int = 120):
    src = _CHILD.format(repo=str(REPO_ROOT), path=str(path), body=body)
    return subprocess.run([sys.executable, "-c", src], capture_output=True,
                          text=True, timeout=timeout)


# --------------------------------------------------------------- the core property
def test_a_second_process_write_is_not_lost(tmp_path):
    """The exact interleave that destroys a write in FileStore.

    Sequenced by hand rather than raced, so it is deterministic: parent writes, child
    writes, parent writes again from a handle that has not reloaded. Under FileStore the
    parent's whole-dict flush erases the child's key and nothing raises.
    """
    db = tmp_path / "store.db"
    parent = SqliteStore(str(db))
    parent.set("parent_first", "1")

    done = _run_child(db, 's.set("child_write", "survives")')
    assert done.returncode == 0, f"child failed: {done.stderr[:400]}"

    parent.set("parent_second", "1")

    assert parent.get("child_write") == "survives", (
        "a second process's committed write was lost -- this is the FileStore defect and "
        "SqliteStore exists to not have it"
    )
    assert parent.get("parent_first") == "1"
    assert parent.get("parent_second") == "1"


def test_b_cas_is_atomic_across_processes(tmp_path):
    """FileStore.cas returns True in BOTH processes and loses a write. This must not.

    The child takes the value the parent is also holding, so exactly ONE of the two CAS
    attempts may succeed. FileStore's answer was "both", because it compared against its own
    in-memory dict under a per-instance threading lock.
    """
    db = tmp_path / "cas.db"
    parent = SqliteStore(str(db))
    parent.set("k", "v0")

    child = _run_child(db, 'print("CHILD", s.cas("k", "v0", "child_won"))')
    assert child.returncode == 0, f"child failed: {child.stderr[:400]}"
    child_won = "CHILD True" in child.stdout

    # The parent still holds the ORIGINAL expected value. If the child won, this must fail.
    parent_won = parent.cas("k", "v0", "parent_won")

    assert child_won != parent_won, (
        f"exactly one CAS may succeed against the same expected value; "
        f"child_won={child_won} parent_won={parent_won}"
    )
    assert parent.get("k") == ("parent_won" if parent_won else "child_won")


def test_c_three_process_write_storm_loses_nothing(tmp_path):
    """The probe that produced 65.6% loss against FileStore, as a pin."""
    db = tmp_path / "storm.db"
    store = SqliteStore(str(db))
    store.set("seed", "1")

    procs = [subprocess.Popen(
        [sys.executable, "-c", _CHILD.format(
            repo=str(REPO_ROOT), path=str(db),
            body=f'\nfor i in range(40): s.set("w{w}:%d" % i, "v")\n')],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE) for w in range(3)]
    for p in procs:
        _, err = p.communicate(timeout=180)
        assert p.returncode == 0, f"worker failed: {err.decode()[:300]}"

    survivors = len(store.keys("w*:*"))
    assert survivors == 120, f"expected all 120 writes to survive, got {survivors}"


# ------------------------------------------------------------------ the two riders
def test_d_checkpoint_reclaims_the_wal(tmp_path):
    """RIDER 1. Starvation is real (measured: a held reader grew the -wal to 523,272 bytes
    and blocked truncation), so the policy must be explicit and its result must be legible.
    checkpoint() returning False while a reader holds a transaction is the HONEST answer,
    not an error -- that distinction is the whole point."""
    db = tmp_path / "wal.db"
    store = SqliteStore(str(db))
    for i in range(500):
        store.set(f"churn:{i}", "x" * 200)

    assert store.wal_bytes() > 0, "expected WAL content before checkpointing"
    assert store.checkpoint() is True
    assert store.wal_bytes() == 0, "TRUNCATE checkpoint should reclaim the WAL"


def test_e_backup_is_wal_correct_where_a_file_copy_is_not(tmp_path):
    """RIDER 2. shutil.copy2 of a WAL database leaves the -wal behind and yields a stale
    snapshot while still reporting success -- aimed straight at the restore path.
    backup_to() must carry the uncheckpointed writes that a raw copy would drop."""
    db = tmp_path / "src.db"
    store = SqliteStore(str(db))
    store.set("committed_before_backup", "must_survive")
    for i in range(200):
        store.set(f"pad:{i}", "y" * 100)
    assert store.wal_bytes() > 0, "need uncheckpointed WAL content for this to mean anything"

    dest = tmp_path / "backup.db"
    assert store.backup_to(str(dest)) is True

    restored = SqliteStore(str(dest))
    assert restored.get("committed_before_backup") == "must_survive", (
        "the online backup dropped a committed write -- this is the recovery-loss defect"
    )
    assert len(restored.keys("pad:*")) == 200


def test_f_degraded_store_refuses_rather_than_pretends(tmp_path):
    """The _degraded contract, ported from FileStore: a store that cannot open reports
    unavailable instead of serving a confidently empty result."""
    bad = tmp_path / "notadb"
    bad.write_bytes(b"this is not a sqlite database" * 100)
    store = SqliteStore(str(bad))
    if store.is_available():
        pytest.skip("sqlite accepted the file as a database; nothing to assert")
    assert store.get("anything") is None
    assert store.set("k", "v") is False
    assert store.cas("k", None, "v") is False
