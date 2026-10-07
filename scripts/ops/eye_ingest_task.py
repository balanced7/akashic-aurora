#!/usr/bin/env python
"""Keep THE EYE current, under the OS scheduler rather than by hand (2026-10-07).

WHY THIS EXISTS. The eye is the only searchable record of 1,604 transcripts and 56,385 events, and
for most of that corpus it is the only copy that still exists: 138 transcript files remain on the
harness disk against 1,673 sessions the index holds. Nothing scheduled its ingest. Measured on
2026-10-07, the first run of the night took in **3,717 new events** -- roughly six days of work that
had happened and was not findable. `TranscriptArchive-Daily` runs every day and succeeds, so the
BYTES were being preserved the whole time; only the findability rotted. Preserving a corpus you
cannot search is a backup, not a library.

This is the same failure mem_watch had, and the note on its installer says it plainly: *"A recorder
that has to be started by hand stops at the first reboot."* An index that has to be refreshed by
hand stops at the first busy day.

WHY A WRAPPER RATHER THAN `pyw agent_cli.py eye ingest` DIRECTLY. Under Task Scheduler a process
gets no console and CPython sets ``sys.stdout`` to **None**; ``print()`` then succeeds and discards
its output, so the whole coverage report would go nowhere every single day -- and the coverage report
is the only thing that would tell anyone the index had stopped being whole. That is item 0 of the
affordance-layer fence, closed 2026-10-06, and `repair_background_stdio` is its remedy. Calling it
FIRST, before importing anything that prints, is part of the contract.

WHAT IT WRITES. A dated receipt under ``state/eye/ingest-receipts/``, one JSON line per run, holding
the numbers that make a silent failure visible: files found vs taken, collisions, files that parsed
and yielded nothing, and the duration. Per the house drill doctrine a recovery path with no dated
receipt is presumed broken, and a scheduled task nobody reads is exactly that.

COST, measured: ~85 s for an incremental run even when only 3 events are new, because the connectome
is rebuilt in full every pass. Cheap daily; too expensive to be hourly, and filed as friction rather
than worked around here.

Install (does not run as admin, idempotent)::

    powershell -ExecutionPolicy Bypass -File scripts\\ops\\install_eye_ingest_task.ps1

Run by hand::

    py scripts\\ops\\eye_ingest_task.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    # At module scope, once. The lesson from gen_library.py earlier tonight: three lazy inserts
    # inside functions that happened to need `core` left the one caller that ran first unable to
    # import at all, and its guard failed open silently.
    sys.path.insert(0, str(ROOT))


def main() -> int:
    # FIRST, before argparse and before importing anything that prints at import time.
    from core.infrastructure.background_stdio import repair_background_stdio
    log = repair_background_stdio("eye-ingest")

    import json
    import time
    from datetime import datetime, timezone

    from core.eye import index as eye

    started = time.time()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[eye-ingest] {stamp} starting" + (f" (log: {log})" if log else ""))

    rc = 0
    try:
        rep = eye.ingest()
        cov = eye.corpus_coverage()
    except Exception as e:                                                 # noqa: BLE001
        # A crash must be a RECEIPT, not an exit code nobody sees. The whole point of this file is
        # that the task's output reaches a reader.
        rep, cov = {}, {}
        receipt = {"at": stamp, "ok": False,
                   "error": f"{type(e).__name__}: {e}",
                   "seconds": round(time.time() - started, 1)}
        rc = 1
    else:
        receipt = {
            "at": stamp,
            "ok": bool(rep.get("manifest_complete")),
            "seconds": round(time.time() - started, 1),
            "files_taken": cov.get("total"),
            "files_found": cov.get("found"),
            "shadowed": cov.get("shadowed"),
            # The two numbers worth waking up for. Both should be stable; a rise in either means a
            # plane is being eaten or a format has appeared that the index cannot read.
            "dropped_to_collision": cov.get("dropped_to_collision"),
            "files_yielded_nothing": rep.get("files_yielded_nothing"),
            "events_total": rep.get("events_total"),
            "events_new": rep.get("events_new"),
            "lines_unparsed": rep.get("lines_unparsed"),
            "files_failed": len(rep.get("files_failed") or []),
            "collisions": cov.get("collisions", [])[:5],
            "barren": [b.get("session") for b in (rep.get("barren") or [])][:10],
        }
        if not receipt["ok"]:
            rc = 1
        print(f"[eye-ingest] {receipt['events_new']:,} new event(s), "
              f"{receipt['files_taken']} file(s) taken of {receipt['files_found']} found, "
              f"{receipt['dropped_to_collision']} collision(s), "
              f"{receipt['files_yielded_nothing']} barren, {receipt['seconds']}s")

    out_dir = ROOT / "state" / "eye" / "ingest-receipts"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        # One file per MONTH, appended. A file per run buries the directory; a single file forever
        # makes the interesting part hard to reach.
        dest = out_dir / (datetime.now(timezone.utc).strftime("%Y-%m") + ".jsonl")
        with open(dest, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(receipt, ensure_ascii=False) + "\n")
        print(f"[eye-ingest] receipt -> {dest}")
    except OSError as e:
        # Never let the bookkeeping fail the job it is recording.
        print(f"[eye-ingest] WARN could not write receipt ({type(e).__name__}: {e})")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
