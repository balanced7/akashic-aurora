"""roll/1 -- the compact, renderable, analyzable projection of a performance session.

THE PROBLEM, MEASURED 2026-09-27. state/arsenal/performance/<s>/events.jsonl is 2,387,122 bytes
for one 21-minute session (6,043 notes), and 36,328,836 bytes across 69 sessions. It is large
because it stores the DETECTOR'S OUTPUT beside the input: every note re-emits chord, key,
key_conf, nns, nns_key, notes[], bass and locked.

WHAT THIS KEEPS. Notes (pitch, onset, duration, velocity) and pedal spans -- the performance
itself, losslessly. One line per NOTE rather than three events per note, integers only, onsets
delta-coded so the common column is one or two digits. Measured: 2,387,122 -> 82,323 bytes (29x;
28,529 gzipped); the whole store 36,328,836 -> 1,882,466 (19.3x).

WHAT THIS DROPS, and the honest caveat. The chord/key stream is not kept by default. It is mostly
re-derivable from the notes, but re-deriving gives what TODAY's detector says, not what the player
actually saw that night -- if the detector changes, the two disagree and only events.jsonl
remembers the original reading. So keep_chords=True exists for sessions where what-was-displayed
matters. This is a PROJECTION, not a replacement: events.jsonl stays the atom, and nothing here
deletes a source.

WHY IT LIVES HERE rather than in scripts/. It was written as a script, and for its first hours
NOTHING CALLED IT -- the 69 existing files were a one-off backfill, so every new session would
have been written without one. Closing that gap means performance.close() must reach the format,
and a library importing a script inverts the dependency. The format therefore lives beside the
store that writes it, and scripts/piano_roll_pack.py is a thin door onto this module. One copy:
two implementations of a format drift, which is a lesson this repo has paid for elsewhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

API = "roll/1"


def pack_events(events: Iterable[dict[str, Any]], session: str = "", keep_chords: bool = False) -> str:
    """Note/pedal events -> roll/1 text. Pure: takes the events, returns the document."""
    ons: dict[int, list[tuple[int, int]]] = {}
    notes: list[tuple[int, int, int, int]] = []
    pedal: list[tuple[int, int]] = []
    chords: list[tuple[int, str, str]] = []
    tmax = 0
    pdown = None
    for e in events:
        if not isinstance(e, dict):
            continue
        t = int(e.get("t_ms") or 0)
        if t > tmax:
            tmax = t
        kind = e.get("kind")
        if kind == "on":
            ons.setdefault(int(e.get("note", -1)), []).append((t, int(e.get("vel", 64) or 64)))
        elif kind in ("off", "sound_end"):
            n = e.get("note")
            if n is not None and ons.get(n):  # ons.get(None) is falsy anyway
                t0, v = ons[n].pop(0)
                notes.append((t0, int(n), max(t - t0, 1), v))
        elif kind == "pedal":
            if e.get("down") and pdown is None:
                pdown = t
            elif not e.get("down") and pdown is not None:
                pedal.append((pdown, t))
                pdown = None
        elif kind == "chord" and keep_chords and e.get("chord") and (not chords or chords[-1][1] != e["chord"]):
            chords.append((t, str(e["chord"]), str(e.get("key") or "")))
    for n, rest in ons.items():  # held at session end -- real, not dropped
        for t0, v in rest:
            notes.append((t0, int(n), max(tmax - t0, 1), v))
    if pdown is not None:
        pedal.append((pdown, tmax))
    notes.sort()

    out = [
        f"#{API} session={session} dur_ms={tmax} notes={len(notes)} pedal={len(pedal)} src=events.jsonl",
        "#n dt note dur vel   (dt=ms since previous onset)",
    ]
    prev = 0
    for t0, n, dur, vel in notes:
        out.append(f"{t0 - prev} {n} {dur} {vel}")
        prev = t0
    if pedal:
        out.append("#p t0 dur")
        for a, b in pedal:
            out.append(f"{a} {b - a}")
    if chords:
        out.append("#c t chord key")
        for t, c, key in chords:
            out.append(f"{t} {c} {key}")
    return "\n".join(out) + "\n"


def unpack(text: str):
    """Read it back. A format nobody round-trips is a format that silently rots."""
    meta: dict[str, str] = {}
    notes: list[tuple[int, int, int, int]] = []
    pedal: list[tuple[int, int]] = []
    chords: list[tuple[int, str, str]] = []
    sec = "n"
    for line in text.splitlines():
        if line.startswith(f"#{API}"):
            for kv in line.split()[1:]:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    meta[k] = v
        elif line.startswith("#n"):
            sec = "n"
        elif line.startswith("#p"):
            sec = "p"
        elif line.startswith("#c"):
            sec = "c"
        elif not line or line.startswith("#"):
            continue
        elif sec == "n":
            dt, n, dur, vel = (int(x) for x in line.split())
            t0 = (notes[-1][0] + dt) if notes else dt
            notes.append((t0, n, dur, vel))
        elif sec == "p":
            a, d = (int(x) for x in line.split())
            pedal.append((a, a + d))
        elif sec == "c":
            p = line.split(None, 2)
            chords.append((int(p[0]), p[1], p[2] if len(p) > 2 else ""))
    return meta, notes, pedal, chords
