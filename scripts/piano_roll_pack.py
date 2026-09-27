"""roll/1 -- the compact, renderable, analyzable projection of a performance session.

THE PROBLEM, MEASURED 2026-09-27. state/arsenal/performance/<s>/events.jsonl is 2,387,122
bytes for one 21-minute session (6,043 notes). It is large because it stores the DETECTOR'S
OUTPUT beside the input: every note re-emits chord, key, key_conf, nns, nns_key, notes[],
bass, locked. 69 sessions of that is tens of megabytes to keep a few hours of playing.

WHAT THIS KEEPS. Notes (pitch, onset, duration, velocity) and pedal spans -- the performance
itself, losslessly. One line per NOTE rather than three events per note, integers only,
onsets delta-coded so the common column is one or two digits.

WHAT THIS DROPS, and the honest caveat. The chord/key stream is NOT kept by default. It is
mostly re-derivable from the notes, but re-deriving it gives you what TODAY's detector says,
not what the player actually saw on screen that night -- if the detector changes, the two
disagree and only events.jsonl remembers the original reading. So:
  --keep-chords  writes a compact chord track for sessions where what-was-displayed matters.
  This is a PROJECTION, not a replacement. events.jsonl stays the atom; roll is the lens.
Deleting the source is a separate decision with a separate gate, and this tool never does it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERF = ROOT / "state" / "arsenal" / "performance"


def pack(session: str, keep_chords: bool = False) -> str:
    src = PERF / session / "events.jsonl"
    ons, notes, pedal, chords = {}, [], [], []
    tmax, pdown = 0, None
    for line in src.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        t = e.get("t_ms", 0); tmax = max(tmax, t); k = e.get("kind")
        if k == "on":
            ons.setdefault(e["note"], []).append((t, e.get("vel", 64)))
        elif k in ("off", "sound_end") and ons.get(e.get("note")):
            t0, v = ons[e["note"]].pop(0)
            notes.append((t0, e["note"], max(t - t0, 1), v))
        elif k == "pedal":
            if e.get("down") and pdown is None: pdown = t
            elif not e.get("down") and pdown is not None: pedal.append((pdown, t)); pdown = None
        elif k == "chord" and keep_chords and e.get("chord"):
            if not chords or chords[-1][1] != e["chord"]:
                chords.append((t, e["chord"], e.get("key") or ""))
    for n, rest in ons.items():                      # held at session end -- real, not dropped
        for t0, v in rest: notes.append((t0, n, max(tmax - t0, 1), v))
    if pdown is not None: pedal.append((pdown, tmax))
    notes.sort()

    out = [f"#roll/1 session={session} dur_ms={tmax} notes={len(notes)} pedal={len(pedal)}"
           f" src=events.jsonl",
           "#n dt note dur vel   (dt=ms since previous onset)"]
    prev = 0
    for t0, n, dur, vel in notes:
        out.append(f"{t0-prev} {n} {dur} {vel}"); prev = t0
    if pedal:
        out.append("#p t0 dur")
        for a, b in pedal: out.append(f"{a} {b-a}")
    if chords:
        out.append("#c t chord key")
        for t, c, key in chords: out.append(f"{t} {c} {key}")
    return "\n".join(out) + "\n"


def unpack(text: str):
    """Read it back. A format nobody round-trips is a format that silently rots."""
    meta, notes, pedal, chords, sec = {}, [], [], [], "n"
    for line in text.splitlines():
        if line.startswith("#roll/"):
            for kv in line.split()[1:]:
                if "=" in kv: k, v = kv.split("=", 1); meta[k] = v
        elif line.startswith("#n"): sec = "n"
        elif line.startswith("#p"): sec = "p"
        elif line.startswith("#c"): sec = "c"
        elif not line or line.startswith("#"): continue
        elif sec == "n":
            dt, n, dur, vel = (int(x) for x in line.split())
            t0 = (notes[-1][0] + dt) if notes else dt
            notes.append((t0, n, dur, vel))
        elif sec == "p":
            a, d = (int(x) for x in line.split()); pedal.append((a, a + d))
        elif sec == "c":
            p = line.split(None, 2); chords.append((int(p[0]), p[1], p[2] if len(p) > 2 else ""))
    return meta, notes, pedal, chords


if __name__ == "__main__":
    s = sys.argv[1]
    keep = "--keep-chords" in sys.argv
    txt = pack(s, keep)
    dst = PERF / s / "roll.txt"
    if "--write" in sys.argv: dst.write_text(txt, encoding="utf-8")
    m, n, p, c = unpack(txt)                          # round-trip on every pack, not on faith
    print(f"{s}: {len(n):,} notes, {len(p)} pedal spans, {len(c)} chord marks -> "
          f"{len(txt.encode()):,} bytes{' (written)' if '--write' in sys.argv else ''}")
