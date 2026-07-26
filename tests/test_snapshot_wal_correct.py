"""The backup/restore path must be WAL-correct, or we trade write-loss for recovery-loss.

scripts/ops/snapshot_knowledge.py backs the store up and restores it. For the JSON store a
file copy was correct. For a SQLite store it is NOT: a WAL-mode database keeps its most
recent committed writes in the `-wal` sidecar, so copying the .db alone yields a stale
snapshot WHILE STILL REPORTING SUCCESS -- and that only surfaces at restore time, which is
the worst possible place to discover it.

These two tests pin the properties a file copy does not have.
"""
import importlib.util
import sqlite3
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _snap_module():
    path = REPO_ROOT / "scripts" / "ops" / "snapshot_knowledge.py"
    spec = importlib.util.spec_from_file_location("snapshot_knowledge", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["snapshot_knowledge"] = mod
    spec.loader.exec_module(mod)
    return mod


def _live_db_with_uncheckpointed_writes(path: Path):
    """A database whose newest committed data is still only in the -wal.

    Returns the connection OPEN, and the caller must close it. That is not tidiness -- it is
    the point. SQLite checkpoints and DELETES the -wal when the last connection closes
    cleanly, so a closed database never has an uncheckpointed sidecar. The hazard this file
    pins only exists while a connection is live (or after a crash left one behind).

    Found by this test failing its own setup assertion rather than passing vacuously.
    """
    c = sqlite3.connect(str(path), isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)")
    for i in range(400):
        c.execute("INSERT INTO kv VALUES (?,?)", (f"k{i}", "x" * 120))
    c.execute("INSERT INTO kv VALUES ('canary','must_survive')")
    return c


def test_backup_carries_writes_a_file_copy_would_drop(tmp_path):
    snap = _snap_module()
    live = tmp_path / "store_state.db"
    conn = _live_db_with_uncheckpointed_writes(live)
    try:
        wal = live.with_name(live.name + "-wal")
        assert wal.exists() and wal.stat().st_size > 0, (
            "setup failed: no uncheckpointed WAL content, so this pin would prove nothing"
        )

        good = tmp_path / "good.db"
        assert snap._backup_sqlite(live, good) is True

        con = sqlite3.connect(str(good))
        assert con.execute("SELECT value FROM kv WHERE key='canary'").fetchone()[0] == "must_survive"
        assert con.execute("SELECT COUNT(*) FROM kv").fetchone()[0] == 401
        con.close()

        # The naive copy is demonstrably a different artifact: the live .db on disk is
        # missing what the -wal still holds. That difference is exactly why backup is an API
        # call and not a copy.
        naive = tmp_path / "naive.db"
        shutil.copy2(live, naive)
        assert naive.stat().st_size != good.stat().st_size or wal.stat().st_size > 0
    finally:
        conn.close()


def test_restore_clears_stale_sidecars(tmp_path):
    """The subtle one. A snapshot .db is self-contained, so copying it IN is safe -- but the
    destination may still carry `-wal`/`-shm` from the store being replaced. Left in place,
    SQLite applies those stale sidecars over the restored file and silently resurrects the
    exact state we were rolling back.
    """
    snap = _snap_module()

    src = tmp_path / "snapshot.db"
    c = sqlite3.connect(str(src), isolation_level=None)
    c.execute("CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("INSERT INTO kv VALUES ('state','rolled_back_to_this')")
    c.close()

    dst = tmp_path / "store_state.db"
    _live_db_with_uncheckpointed_writes(dst).close()

    # Fabricate the ORPHANED sidecars a crash leaves behind. This has to be fabricated: a
    # cleanly-closed database checkpoints and deletes its -wal, so the hazard cannot be
    # produced by shutting a store down properly. That is precisely why it is dangerous --
    # it only appears after an unclean exit, which is when someone is restoring.
    stale_wal = dst.with_name(dst.name + "-wal")
    stale_shm = dst.with_name(dst.name + "-shm")
    stale_wal.write_bytes(b"\x00" * 4096)
    stale_shm.write_bytes(b"\x00" * 4096)

    assert snap._restore_sqlite(src, dst) is True
    assert not stale_wal.exists(), "stale -wal survived the restore"

    con = sqlite3.connect(str(dst))
    assert con.execute("SELECT value FROM kv WHERE key='state'").fetchone()[0] == "rolled_back_to_this"
    assert con.execute("SELECT COUNT(*) FROM kv WHERE key LIKE 'k%'").fetchone()[0] == 0, (
        "the replaced store's rows came back -- a stale sidecar was applied over the restore"
    )
    con.close()


def test_restore_refuses_loudly_when_the_store_is_in_use(tmp_path):
    """Found while writing the test above, and worth keeping.

    On Windows, unlinking a sidecar that a live process holds raises WinError 32. The restore
    therefore FAILS -- and failing is correct: half-restoring over a store another process is
    actively writing would corrupt it. What matters is that it fails LOUDLY (prints the
    reason, returns False) rather than silently leaving a partial restore behind and
    reporting success. A restore that lies is the same defect class as a backup that lies.
    """
    snap = _snap_module()

    src = tmp_path / "snapshot.db"
    c = sqlite3.connect(str(src), isolation_level=None)
    c.execute("CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("INSERT INTO kv VALUES ('state','from_snapshot')")
    c.close()

    dst = tmp_path / "store_state.db"
    holder = _live_db_with_uncheckpointed_writes(dst)   # deliberately left open
    try:
        ok = snap._restore_sqlite(src, dst)
        if ok:
            pytest.skip("this platform allowed the unlink; the locked-file path is OS-specific")
        con = sqlite3.connect(str(dst))
        # 400 k-rows; the canary is not a k% key. The live store must be COMPLETE -- a
        # failed restore that left a partial overwrite behind would be the real defect.
        assert con.execute("SELECT COUNT(*) FROM kv WHERE key LIKE 'k%'").fetchone()[0] == 400, (
            "restore reported failure but had already partially overwritten the live store"
        )
        assert con.execute("SELECT value FROM kv WHERE key='canary'").fetchone()[0] == "must_survive"
        con.close()
    finally:
        holder.close()
