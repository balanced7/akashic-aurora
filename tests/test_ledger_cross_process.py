"""Pins for FileLedger across PROCESSES (L0, 2026-09-24), registered before the fix.

WHY. The DuckDB deep dive's fit lane compared session_logs/ledger/*.jsonl with the Redis
copies exported to state/bus-export for 2026-09-10..24: 410 of 18,170 recall outcomes and
36 of 1,430 firehose events never reached the file. Almost every loss sat within 0.5 s of
another write. The mechanism is in FileLedger.emit: it reads the WHOLE file, appends one row
in memory, and rewrites the file through one fixed tmp name plus os.replace, guarded only by
a threading.RLock that another process cannot see. Two processes read the same state, both
rewrite, and the last os.replace wins; the other row is gone. On Windows os.replace also
fails outright while any reader holds the file open, and that error was logged and
swallowed, so emit() returned an id for a row that was never written.

These pins run real processes (not threads) against one stream file, because the defect
lives between processes. Greppable context: research/reviewed/duckdb-lane-fit-2026-09-24.md,
research/reviewed/duckdb-deep-dive-synthesis-2026-09-24.md (slice L0).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.foundation.ledger import FileLedger  # noqa: E402

WORKER = r"""
import json, os, sys, time
sys.path.insert(0, {repo!r})
from core.foundation.ledger import FileLedger
base, stream, who, n, go, maxlen = sys.argv[1:7]
maxlen = None if maxlen == "none" else int(maxlen)
led = FileLedger(base)
deadline = time.time() + 30
while not os.path.exists(go) and time.time() < deadline:
    time.sleep(0.002)
ids = [led.emit(stream, {{"who": who, "i": i}}, maxlen=maxlen) for i in range(int(n))]
print(json.dumps(ids))
"""


def _race(tmp_path, stream, writers, per_writer, maxlen="none"):
    """Start `writers` processes that emit `per_writer` events each, all at the same instant."""
    go = tmp_path / "go"
    code = WORKER.format(repo=str(REPO))
    procs = [subprocess.Popen([sys.executable, "-c", code, str(tmp_path), stream, f"w{k}",
                               str(per_writer), str(go), str(maxlen)],
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
             for k in range(writers)]
    time.sleep(0.8)                      # let every interpreter reach the start line
    go.write_text("go")
    returned = []
    for p in procs:
        out, err = p.communicate(timeout=180)
        assert p.returncode == 0, f"writer crashed: {err[-800:]}"
        returned.extend(json.loads(out.strip().splitlines()[-1]))
    return returned


def _rows(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_concurrent_processes_lose_no_rows(tmp_path):
    writers, per = 6, 60
    returned = _race(tmp_path, "race", writers, per)
    rows = _rows(tmp_path / "race.jsonl")
    got = {(r["event"]["who"], r["event"]["i"]) for r in rows}
    want = {(f"w{k}", i) for k in range(writers) for i in range(per)}
    missing = want - got
    assert not missing, f"{len(missing)} of {len(want)} rows lost between processes, e.g. {sorted(missing)[:5]}"
    assert len(rows) == len(want), f"{len(rows)} rows on disk for {len(want)} emits (duplicates?)"
    assert len(set(returned)) == len(returned), "two emits were handed the same id"


def test_ids_are_unique_and_ordered_on_disk(tmp_path):
    _race(tmp_path, "order", 4, 40)
    ids = [int(r["id"]) for r in _rows(tmp_path / "order.jsonl")]
    assert len(ids) == len(set(ids)), "duplicate ids on disk"
    assert ids == sorted(ids), "file is not in id order"


def test_concurrent_trim_keeps_the_newest_and_stays_near_the_cap(tmp_path):
    cap = 50
    _race(tmp_path, "capped", 4, 60, maxlen=cap)
    rows = _rows(tmp_path / "capped.jsonl")
    ids = [int(r["id"]) for r in rows]
    assert cap <= len(rows) <= cap + max(1, cap // 10), f"{len(rows)} rows kept for maxlen={cap}"
    assert ids == list(range(ids[0], ids[0] + len(ids))), "trim must keep a contiguous newest run"
    assert ids[-1] == 240, f"newest id should be 240 after 240 emits, got {ids[-1]}"


def test_emit_appends_instead_of_rewriting_the_file(tmp_path):
    """An append keeps the same file; a rewrite plus os.replace swaps in a new one."""
    led = FileLedger(str(tmp_path))
    for i in range(200):
        led.emit("big", {"i": i})
    before = os.stat(tmp_path / "big.jsonl").st_ino
    led.emit("big", {"i": 200})
    after = os.stat(tmp_path / "big.jsonl").st_ino
    assert before == after, "emit rewrote the whole file (os.replace) instead of appending one line"


def test_a_torn_last_line_does_not_swallow_the_next_record(tmp_path):
    """A power cut can leave a half-written last line. The next emit must still be readable."""
    led = FileLedger(str(tmp_path))
    for i in range(3):
        led.emit("torn", {"i": i})
    with open(tmp_path / "torn.jsonl", "a", encoding="utf-8") as fh:
        fh.write('{"id": "4", "event": {"i": ')   # no closing brace, no newline
    new_id = led.emit("torn", {"i": 99})
    events = led.consume("torn", after_id="0", count=100)
    assert (new_id, {"i": 99}) in events, f"record after a torn line was lost: {events}"
    assert int(new_id) > 3, "id must stay above every complete record"


def test_a_lock_timeout_returns_the_newest_id_not_zero(tmp_path, monkeypatch):
    """Found by the DeepSeek fence on de217307: a LockTimeout before the tail read returned
    "0", which a caller would use as a cursor and replay the whole stream from."""
    import contextlib
    from core.foundation import filelock, ledger as ledger_mod
    led = FileLedger(str(tmp_path))
    for i in range(3):
        led.emit("busy", {"i": i})

    @contextlib.contextmanager
    def always_busy(target, *, timeout=10.0):
        raise filelock.LockTimeout("held elsewhere")
        yield  # pragma: no cover

    monkeypatch.setattr(ledger_mod.filelock, "exclusive", always_busy)
    returned = led.emit("busy", {"i": 3})
    assert returned == "3", f"a failed emit must hand back the newest id on disk, got {returned!r}"
    assert [e["i"] for _id, e in led.consume("busy", after_id="0")] == [0, 1, 2]


def test_emit_survives_a_reader_holding_the_file_open(tmp_path):
    """On Windows os.replace fails while another handle is open; an append must not."""
    led = FileLedger(str(tmp_path))
    led.emit("held", {"i": 0}, maxlen=3)
    with open(tmp_path / "held.jsonl", "r", encoding="utf-8") as reader:
        reader.readline()
        for i in range(1, 6):
            led.emit("held", {"i": i}, maxlen=3)
    got = [e["i"] for _id, e in led.consume("held", after_id="0", count=100)]
    assert got[-1] == 5 and 5 in got, f"the newest row was lost while a reader held the file: {got}"
