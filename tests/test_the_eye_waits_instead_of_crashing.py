"""RED pins: a second ingest crashes the first-come-first-served way instead of waiting.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

FOUND BY ACCIDENT, 2026-10-07, which is the only reason it was found at all. Daniel asked me to
register the eye-ingest scheduled task. I registered it, then verified it the honest way -- by firing
it through the REAL Windows scheduler rather than by hand, because a `pyw` launch from a shell
inherits stdio and gives a false all-clear (the lesson from closing item 0 of the affordance fence).

While doing that I left a hand-launched ingest running and triggered the task 17 seconds later. The
receipts:

    2026-10-07T12:28:18Z  ok=True   51.8s  events_new=119
    2026-10-07T12:28:35Z  ok=False   6.2s  error=OperationalError: database is locked

So the collision was mine. The CRASH is not.

WHAT IS ACTUALLY WRONG. `core/eye/index.py:_connect` opens the db with
``sqlite3.connect(str(p))`` and sets ``PRAGMA journal_mode=WAL``, and never sets ``busy_timeout``.
Python's default is **5 seconds**. A full ingest holds its write transaction for 40-85 seconds. So any
second writer that arrives during a pass gives up after 5 s and raises, when the correct behaviour --
and the behaviour WAL exists to make cheap -- is to WAIT.

WHY THIS MATTERS NOW RATHER THAN IN THE ABSTRACT. The task was registered minutes before this was
found, and it is set to fire daily at 12:20 AND at every logon. The ways it can overlap something are
ordinary, not exotic:

  * a logon trigger firing while the daily run is still going;
  * an agent running `py agent_cli.py eye ingest` by hand during the scheduled pass;
  * any of the read verbs (`eye find`, `eye stats`, `zoom`, `trace`) holding a read while the writer
    wants the lock.

``MultipleInstances=IgnoreNew`` in the task definition guards the task against ITSELF and against
nothing else. It cannot see a hand-run.

AND THE FAILURE IS CHEAP TO MISREAD. The scheduled task reports `LastTaskResult: 1`. A daily task
that shows red for a transient lock is the EphemeralArchive shape all over again -- a correct-looking
failure that recurs forever and trains everyone to stop reading the number. This house already has
that problem once today; it does not need it twice.

THE ONE GOOD PIECE OF NEWS, recorded because it is the thing that made this diagnosable: the receipt
mechanism worked under the real scheduler. The failing run WROTE A RECEIPT NAMING ITS OWN ERROR,
under `pyw` with no console, which is exactly what `repair_background_stdio` plus the receipt file
were built to do. Without them this would have been an exit code nobody ever saw.

Run::

    py -m pytest tests/test_the_eye_waits_instead_of_crashing.py -q
"""
from __future__ import annotations

import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------------ the defect
def test_the_connection_sets_a_busy_timeout():
    """THE PIN. WAL without a busy timeout is half a concurrency story.

    WAL lets readers and a writer coexist; it does not let two WRITERS coexist, and the second one's
    only civilised option is to wait. Python's default wait is 5 s against a pass that holds its
    transaction for 40-85 s, so the default is a guaranteed crash rather than a timeout.
    """
    import core.eye.index as ix
    src = Path(ix.__file__).read_text(encoding="utf-8", errors="replace")
    i = src.index("def _connect")
    block = src[i:i + 1200].lower()
    assert "busy_timeout" in block or "timeout=" in block, (
        "_connect sets journal_mode=WAL and leaves busy_timeout at sqlite's 5s default, while an "
        "ingest holds its write transaction for 40-85s. Measured 2026-10-07: a second ingest "
        "starting 17s into a 51.8s pass died with 'OperationalError: database is locked' and the "
        "scheduled task reported LastTaskResult: 1.")


def test_a_second_writer_waits_rather_than_raising():
    """BEHAVIOURAL, not textual -- the pin above can be satisfied by a comment.

    Opens two connections through the organ's own `_connect`, holds a write on the first for longer
    than sqlite's default patience, and requires the second to still get through. This is the
    production shape: the scheduled pass is the long writer and the hand-run is the second one.
    """
    import core.eye.index as ix
    db = ROOT / "state" / "eye" / "_busy_probe.db"
    if db.exists():
        db.unlink()
    hold_seconds = 7.0          # > sqlite's 5s default, << the 40-85s a real pass takes
    errors: list = []
    started = threading.Event()

    def _hold():
        con = ix._connect(db)
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('probe','1')")
            started.set()
            time.sleep(hold_seconds)
            con.commit()
        except Exception as e:                                             # noqa: BLE001
            errors.append("holder: %s: %s" % (type(e).__name__, e))
        finally:
            con.close()

    t = threading.Thread(target=_hold, daemon=True)
    t.start()
    assert started.wait(30), "the holding writer never acquired its transaction"
    time.sleep(0.5)

    t0 = time.time()
    try:
        con2 = ix._connect(db)
        try:
            con2.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('second','1')")
            con2.commit()
        finally:
            con2.close()
    except sqlite3.OperationalError as e:
        waited = time.time() - t0
        t.join(timeout=30)
        try:
            db.unlink()
        except OSError:
            pass
        pytest.fail(
            "the second writer raised %r after only %.1fs while the first held the write for %.0fs. "
            "It must WAIT. This is the exact failure the registered eye-ingest task hit on its first "
            "real scheduler run (LastTaskResult: 1, receipt error 'database is locked')."
            % (str(e), waited, hold_seconds))
    t.join(timeout=30)
    try:
        db.unlink()
    except OSError:
        pass
    assert not errors, errors


# ------------------------------------------------------------------ ratchets
def test_wal_is_still_on():
    """RATCHET. WAL is what lets the read verbs keep working during an ingest; a busy timeout is an
    addition to it, never a replacement for it."""
    import core.eye.index as ix
    db = ROOT / "state" / "eye" / "_wal_probe.db"
    if db.exists():
        db.unlink()
    con = ix._connect(db)
    try:
        mode = con.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        con.close()
        try:
            db.unlink()
        except OSError:
            pass
    assert str(mode).lower() == "wal", "journal_mode is %r, not WAL" % (mode,)


def test_the_task_wrapper_still_records_a_failure_rather_than_swallowing_it():
    """RATCHET on the thing that made this diagnosable at all.

    The wrapper caught the OperationalError, wrote `ok=False` with the error text into the dated
    receipt, and returned non-zero -- under `pyw`, with no console. That behaviour is why this defect
    has a measurement instead of a shrug, and it must not be traded away while fixing the lock.
    """
    src = (ROOT / "scripts" / "ops" / "eye_ingest_task.py").read_text(
        encoding="utf-8", errors="replace")
    assert "repair_background_stdio" in src, "the task no longer repairs its dead stdio"
    assert '"error"' in src or "'error'" in src, (
        "the task no longer records the error text in its receipt, so a crash becomes an exit code "
        "nobody sees")
