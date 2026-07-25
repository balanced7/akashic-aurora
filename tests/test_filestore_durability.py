"""Pins for FileStore durability under concurrent writers and unreadable state.

WHY THIS EXISTS
---------------
2026-07-25, reported live by codex during read-only research: parallel `recall --full` calls
logged WinError 32 replacing session_logs/store_state.json.tmp; moments later a
`recall-feedback` vote ran, and store_state.json -- 9MB -- was found to be **164 bytes**,
containing only the vote object. No repair was attempted. Redis was authoritative and healthy.

Reproduced exactly before fixing (500 lessons, 108963 bytes -> 98 bytes, 1 key):

    _load()  catches the parse error, logs a WARNING, and returns -- leaving self._data as
             the empty dict from __init__.
    _flush() then writes that empty dict over the file, because it always serialises the
             WHOLE in-memory state.

So an unreadable file becomes total destruction on the very next write. That is fail-open at
the foundation layer: the read error is survivable, the write it licenses is not.

Two further defects found in the same path, both pinned here:
  - every process used the SAME `store_state.json.tmp`, so concurrent writers interleaved
    into one temp file (codex's "Extra data: line 1 column 9128218" is that signature);
  - the guard around read-modify-write is `threading.RLock()`, which is in-process only,
    while five-plus processes write this file (CLI calls, two runners, the UI, codex).

NOT FIXED HERE, and deliberately not claimed: two healthy processes that both load, both
mutate, and both flush still lose each other's writes (last-writer-wins over a stale
snapshot). That is a coherence problem needing reload-under-lock, and it is a separate slice.
These pins cover the DESTRUCTIVE classes only.
"""
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.foundation.store import FileStore  # noqa: E402


def _seed(path: Path, n: int = 50) -> int:
    s = FileStore(path=str(path))
    for i in range(n):
        s.set(f"lesson:{i}", "x" * 100)
    return path.stat().st_size


# --------------------------------------------------------------------------
# The incident itself.
# --------------------------------------------------------------------------
def test_unreadable_state_is_never_overwritten(tmp_path):
    """codex's incident: a failed load must not license a destructive write."""
    p = tmp_path / "store_state.json"
    size_before = _seed(p)

    # Corrupt it the way two interleaved writers do: trailing extra JSON.
    with open(p, "a", encoding="utf-8") as f:
        f.write('{"kv":{}}')

    s2 = FileStore(path=str(p))
    s2.set("recall:vote", "useful")

    assert p.stat().st_size >= size_before, (
        f"the corrupt file was overwritten: {size_before} -> {p.stat().st_size} bytes"
    )


def test_unreadable_state_preserves_the_original_bytes(tmp_path):
    """Whatever else happens, the unreadable bytes must remain recoverable somewhere."""
    p = tmp_path / "store_state.json"
    _seed(p)
    original = p.read_bytes()
    with open(p, "a", encoding="utf-8") as f:
        f.write('{"kv":{}}')
    corrupted = p.read_bytes()

    s2 = FileStore(path=str(p))
    s2.set("recall:vote", "useful")

    recoverable = [p.read_bytes()] + [
        q.read_bytes() for q in tmp_path.iterdir() if q != p and q.is_file()
    ]
    assert any(original[:200] in blob for blob in recoverable), (
        "the original records are not recoverable from any file on disk"
    )
    assert any(blob == corrupted for blob in recoverable), (
        "the exact corrupt bytes were discarded -- forensics are impossible"
    )


def test_degraded_store_still_serves_reads_and_writes_in_memory(tmp_path):
    """Fail CLOSED on persistence, not on the caller. A hook must never brick its action."""
    p = tmp_path / "store_state.json"
    _seed(p)
    with open(p, "a", encoding="utf-8") as f:
        f.write('{"kv":{}}')

    s2 = FileStore(path=str(p))
    assert s2.set("k", "v") is True
    assert s2.get("k") == "v", "a degraded store must still work in memory"


def test_healthy_store_still_persists_normally(tmp_path):
    """The guard must not cost the ordinary path."""
    p = tmp_path / "store_state.json"
    s = FileStore(path=str(p))
    s.set("a", "1")
    s.set("b", "2")
    assert FileStore(path=str(p)).get("a") == "1"
    assert FileStore(path=str(p)).get("b") == "2"


def test_empty_or_absent_file_is_not_treated_as_corruption(tmp_path):
    """A fresh store and a zero-byte file are normal, not incidents."""
    p = tmp_path / "store_state.json"
    FileStore(path=str(p)).set("first", "1")
    assert FileStore(path=str(p)).get("first") == "1"

    p2 = tmp_path / "empty.json"
    p2.write_text("", encoding="utf-8")
    s = FileStore(path=str(p2))
    s.set("k", "v")
    assert FileStore(path=str(p2)).get("k") == "v"


# --------------------------------------------------------------------------
# The temp-file collision that produced the corruption in the first place.
# --------------------------------------------------------------------------
def test_temp_file_is_unique_per_writer(tmp_path):
    """A shared .tmp path lets concurrent writers interleave into one file."""
    p = tmp_path / "store_state.json"
    a, b = FileStore(path=str(p)), FileStore(path=str(p))
    ta, tb = a._temp_path(), b._temp_path()
    assert ta != tb, f"both writers share a temp path: {ta}"
    assert str(p) not in (str(ta), str(tb))


def test_flush_leaves_no_temp_files_behind(tmp_path):
    p = tmp_path / "store_state.json"
    s = FileStore(path=str(p))
    for i in range(10):
        s.set(f"k{i}", "v")
    leftovers = [q.name for q in tmp_path.iterdir() if ".tmp" in q.name]
    assert not leftovers, f"temp files leaked: {leftovers}"


def test_concurrent_writers_never_produce_an_unparseable_file(tmp_path):
    """The end-state must always be valid JSON, whoever wins the race."""
    import threading

    p = tmp_path / "store_state.json"
    FileStore(path=str(p)).set("seed", "1")
    stores = [FileStore(path=str(p)) for _ in range(4)]
    errors: list[Exception] = []

    def hammer(st, tag):
        try:
            for i in range(25):
                st.set(f"{tag}:{i}", "v" * 50)
        except Exception as exc:  # a store write must never raise at the caller
            errors.append(exc)

    threads = [threading.Thread(target=hammer, args=(s, f"t{n}")) for n, s in enumerate(stores)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"writes raised: {errors}"
    json.loads(p.read_text(encoding="utf-8"))  # must parse
