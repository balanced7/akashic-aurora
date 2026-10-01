"""roll/1 door: pack a recorded session, or read one back.

    py scripts/piano_roll_pack.py <session> [--write] [--keep-chords]

THE FORMAT ITSELF LIVES IN arsenal/roll.py, beside the store that writes it. It started here as
a script and for its first hours NOTHING CALLED IT: the 69 existing roll.txt files were a one-off
backfill, so every NEW session would have been written without one. Closing that gap meant
performance.close() had to reach the format, and a library importing a script inverts the
dependency -- so the format moved and this became a door. Two implementations of one format
drift; there is one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal.roll import API, pack_events, unpack  # noqa: E402,F401

PERF = ROOT / "state" / "arsenal" / "performance"


def pack(session: str, keep_chords: bool = False) -> str:
    """Read a session's events.jsonl off disk and return its roll/1 document."""
    src = PERF / session / "events.jsonl"
    events = []
    for line in src.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            continue  # a torn last line is not a reason to pack nothing
    return pack_events(events, session=session, keep_chords=keep_chords)


if __name__ == "__main__":
    s = sys.argv[1]
    txt = pack(s, "--keep-chords" in sys.argv)
    if "--write" in sys.argv:
        (PERF / s / "roll.txt").write_bytes(txt.encode("utf-8"))
    m, n, pd, c = unpack(txt)  # round-trip on every pack, not on faith
    print(
        f"{s}: {len(n):,} notes, {len(pd)} pedal spans, {len(c)} chord marks -> "
        f"{len(txt.encode()):,} bytes{' (written)' if '--write' in sys.argv else ''}"
    )
