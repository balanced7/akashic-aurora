"""Practice verbs: an offline harmony engine over Daniel's piano practice log, so we can talk theory about HIS playing.

Read only. Sessions come from arsenal.performance.PerformanceStore (state/arsenal/performance, git-ignored); nothing
here writes into a session directory. Reports made from real sessions belong under
state/arsenal/receipts/practice-verbs/ (git-ignored too).

The live page names whatever sounds every few milliseconds. Offline we see the whole session in both directions:

1. sounding(events): one interval per struck note, from its on to its sound_end (the piano's own account of when the
   sound stopped: key release, pedal lift, re-strike, all-off). A log without sound_end events falls back to the
   release/pedal inference performance.summarize uses.
2. Harmonic windows, by dynamic programming over onset groups. A window's chord set is every pitch class heard for at
   least CHORD_SHARE of it; each pitch class the set gets wrong costs the milliseconds it is wrong (heard while left
   out, or missing while kept in) and each extra window costs WINDOW_PENALTY_MS (less at a pedal lift). So a pedalled
   arpeggio stays one window while its bass walks, a held sus2 followed by its add9 splits in two, and a quick passing
   note stays inside as a passing tone. A note counts as heard for at least HEARD_MIN_MS after its onset (a broken
   chord is heard as a chord). Silences of SILENCE_SPLIT_MS always split. A window under MIN_WINDOW_MS only survives
   as a whole isolated phrase, and such a phrase is dropped as a transient (counted, never named). After naming,
   touching windows with the same chord (root and suffix; the bass may move) merge into one.
3. Naming by the page's own code: arsenal/practice_theory.mjs slices piano.js's THEORY block and runs Theory.detect
   over every window, one node call per session. Names are spelled in the local key (Abm, not G#m, in Eb). A set detect
   leaves unnamed, and a slash chord over a bass that is not one of its tones, also gets an extended reading: a base
   chord plus b9/9/#9/11/#11/b13/13 on some root, bass-aware, always labelled "(reading)", never used without the
   notes that back every tone of it. Over a held bass a reading close in cost to detect's is the chord analysed.
4. Key areas: a 24-key Viterbi path over sliding pitch-class histograms, scored by Krumhansl-Kessler correlation with
   the piano key tracker's leading-tone rule (a minor key whose raised 7th hardly sounds ranks under its relative
   major) plus a scale-fit term, and a switch penalty, so a modulation registers and a passing borrowed chord does
   not. An area holding fewer than two chord roots has no progression of its own: it joins the area it touches, or the
   home key (the key with the most area time). Each window is numbered (arsenal.nashville) in its own key area.
5. Classification in the local key (diatonic, borrowed, modal, secondary dominant, chromatic), in the home key too
   when they differ, and findings: the Lydian 4, suspended vs plain dominants, pedal points, cadences, suspensions
   resolving, colour additions.
6. Voicing and touch per window: notes, polyphony, spread, register, velocity, pedal.

Verbs (py -m arsenal.practice <verb> [session|latest|today] [--json] [--out PATH] [--root DIR]), plain text by default,
times as m:ss from the session start, each output ending with plain words for the terms it used:
- sessions [all|today]: local start, length, notes, home key, key areas.
- brief [session]: the one Claude reads before talking to Daniel (under ~80 lines).
- chords [--min-seconds N], progressions [--n 2..4] [--min-count N] [--exact], keys, borrowed, colors.
- moment [session] m:ss [--window S]: notes, windows, key and numbers around a time.
- name <notes...> [--key K]: every reading of a voicing ("Ab3 Eb4 G4 Bb4 C5 D5", or MIDI numbers).
- compare <a> <b>, history [--days N].
- list, windows, harmony, analyze: the engine's own views.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from bisect import bisect_left, bisect_right
from datetime import date, datetime, timedelta
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import nashville
from .performance import PerformanceError, PerformanceStore, estimate_key

API = "arsenal.practice/v0"
HERE = Path(__file__).resolve().parent
BRIDGE = HERE / "practice_theory.mjs"
PIANO_JS = HERE / "web" / "piano.js"
RECEIPTS = HERE.parent / "state" / "arsenal" / "receipts" / "practice-verbs"

# Engine constants. Every one is written into the analysis, so each number can be reproduced by hand.
MAX_EVENT_T_MS = 7 * 24 * 3600 * 1000  # an event logged this long after the session's start is impossible (an epoch time
                             # written by mistake): it is dropped and counted, so one bad time cannot stretch a session
ONSET_GROUP_MS = 50          # note-ons within 50 ms of a group's first onset are one attack (a window can start there)
HEARD_MIN_MS = 700           # a note counts as heard for at least this long after its onset, while deciding where
                             # windows start and end (a broken chord is heard as one chord)...
GRACE_MS = 100               # ...except a grace note or crush sounding under this long, which is heard only while it sounds
CHORD_SOUND_MS = 250         # a pitch class is in a window's chord only if it really sounds there (key or pedal, not the
CHORD_SOUND_SHARE = 0.25     # heard extension) for this long, or this share of a shorter window
CRUSH_MS = 80                # a note struck this soon before a louder neighbour a half or whole step away...
CRUSH_VEL_RATIO = 0.6        # ...at most this share of its velocity is a crush (an ornament), not a chord tone
DEFINING_SOUND_MS = 250      # a note sounding less than this cannot make a chord borrowed, modal or a secondary dominant
SILENCE_SPLIT_MS = 700       # silence at least this long always ends a window
GROWTH_MS = 1000             # a window this short whose notes all belong to the next window, and which was still
GROWTH_STABLE_MS = 500       # gaining pitch classes this close to its end, is that window's start (an unfolding arpeggio)
WINDOW_PENALTY_MS = 600      # the cost of one more window, in pitch-class-milliseconds
PEDAL_DISCOUNT = 0.5         # ...times this when the pedal is lifted near the window's first attack
PEDAL_NEAR_MS = (-200, 400)  # "near": a lift from 200 ms before to 400 ms after the attack
MIN_WINDOW_MS = 400          # shorter windows are transients
SHORT_PENALTY_MS = 50000     # (a soft wall: shorter windows exist only as whole phrases)
MAX_WINDOW_MS = 90000        # the segmenter looks back this far
CHORD_SHARE = 0.5            # a pitch class heard for at least this share of a window is in its chord set
PASSING_MIN_SHARE = 0.05     # lighter pitch classes are not listed as passing tones
PASSING_MAX_MS = 400         # a chromatic passing note is held (key down) at most this long, struck alone...
PASSING_STEP_MS = 600        # ...and stepped into and out of, one way, by notes at most this far apart in time
NEIGHBOUR_STEP_MS = 1200     # ...or a step away from one note and back to it, each at most this far apart in time
BASS_FIGURE_MIN_MS = 150     # bass notes lowest for less than this are left out of a window's bass figure
BASS_HELD_SHARE = 0.6        # a bass lowest for at least this share of a window is held (else the bass moves)
READING_MARGIN = 1.0         # a reading rooted on a held bass (its 5th sounding) is the analysed chord when it costs at
                             # most this over detect's name for the same notes (Eb/Ab is Abmaj9 without its 3rd)
BASS_MAX_MIDI = 60           # a bass sits below middle C: a higher lowest note is a register figure, not a bass
LINE_SIM_SHARE = 0.25        # three or more pitch classes sounding together for less than this share of a window: no
                             # chord was held there (the notes came one or two at a time)...
LINE_STEP_SHARE = 0.5        # ...a line when at least this share of its single-note moves are steps, else a broken chord
LINE_MIN_ONSETS = 3          # a pedalled treble passage (nothing below middle C) of at least this many single notes...
LINE_SINGLE_SHARE = 0.75     # ...this share of its attacks single notes...
LINE_RUN_STEP_SHARE = 0.75   # ...and this share of its moves steps is a line (a run) too, although the pedal rings it on
RUN_MIN_NOTES = 5            # a note inside a one-way stepwise run this long (single notes at most RUN_STEP_MS apart,
RUN_STEP_MS = 1200           # key down at most RUN_HOLD_MS) is a passing note of the run when the key lacks it
RUN_HOLD_MS = 1000
CHORD_STRIKE_MS = 150        # notes struck within this long of each other are struck together
BASS_LINE_MAX_UPPER = 3      # a low bass walking through notes the voices above it lack, under at most this many pitch
                             # classes, is a bass line, not a chord...
WALK_STEP_MAX_MS = 1000      # ...and back-to-back windows this short, each on a new bass note under the same notes, are
                             # read together as one such walk
BUILD_MAX_MS = 4000          # a window this short whose notes all ring on under one pedal into the next, which only adds
                             # notes over the same bass, is that chord being built (F A C, then Eb, then G: one F11)
AREA_TONIC_MIN_MS = 1500     # a key area needs its tonic chord for this long, or two chord roots that the neighbouring
                             # key lacks (beyond one chord's own 3rd), else it is one chord's colour inside that key
RETURN_AREA_MS = 8000        # inside a key area, the parallel mode's 3rd back this long, with no sign of the area's own
RETURN_TONIC_MS = 4000       # 3rd and the tonic with that 3rd sounding this long, is its own key area (a return)
SECTION_GAP_MS = 5000        # this long with nothing sounding and the pedal up ends a section: key areas, key changes,
                             # cadences and moves never reach across it
SECTION_MIN_MS = 4000        # a shorter section (a stray note between two pauses) joins its nearer neighbour...
SECTION_JOIN_GAP_MS = 30000  # ...only across a pause shorter than this; after a longer pause it stays a section of its own
SECTION_IDLE_MS = 60000      # this long with nothing struck ends a section too, even while a held key or a pedal left
                             # down keeps notes sounding: the section ends this long after its last attack (so a stuck
                             # pedal or a key held for days costs what the playing costs, not what the clock does)
FRAGMENT_MAX_MS = 30000      # a section this short holding fewer than two chord roots is numbered in its own centre
FRAGMENT_FIT = 0.85          # ...when that centre's scale holds at least this share of what is heard there
SUS_HOLD_MS = 300            # a suspension: the sus chord complete and held this long, then a pause this long before
                             # its 3rd arrives (a chord rolled upward whose 3rd comes last is not a suspension)
KEY_FRAME_MS = 1000          # the key path has one step per second...
KEY_CONTEXT_MS = 10000       # ...each scoring the pitch classes heard in the 10 s around it
KEY_SWITCH_PENALTY = 3.0     # the path pays this (in summed score) per key change
KEY_MIN_HEARD_MS = 1500      # a step hearing less than this scores every key alike
KEY_FIT_WEIGHT = 1.0         # score += this * (share of the heard time inside the key's scale - 1)
KEY_SNAP_MS = 5000           # a key change moves to the nearest window start this close
AREA_ROOT_SHARE = 0.1        # a chord root counts toward an area's progression with at least this share of its chords
KEY_JOIN_MS = 5000           # a weak area joins a neighbour whose windows come this close
LT_SHARE = 0.25              # the leading-tone rule, with the numbers of nashville.js rankKeys and
LT_EDGE = 0.08               # performance.numbering_key: a minor key whose raised 7th sounded under a quarter of its
LT_FLOOR = 0.02              # tonic's time ranks up to LT_EDGE under its relative major, but no lower than LT_FLOOR
LT_FLOOR_FADE = 0.16         # above its parallel major once that major outscores the relative major
CADENCE_GAP_MS = 1500        # chords this close count as consecutive for cadences and resolutions
CADENCE_ARRIVAL_MS = 800     # a cadence's arrival chord lasts at least this long
PEDAL_POINT_MIN_MS = 4000    # a pedal point lasts at least this long...
PEDAL_POINT_FOREIGN_SHARE = 0.4  # ...with detect's chord rooted off the bass for at least this share of it, over two
PEDAL_POINT_MAX_PCS = 6      # different harmonies of at most this many pitch classes (a pedal wash holds every note),
                             # each with its 3rd or three notes struck together, one of them without the bass note...
PEDAL_POINT_HARMONY_MS = 1000  # ...and each held at least this long over the bass
LYDIAN_JOIN_MS = 300         # back-to-back Lydian 4 windows this close, on one root and bass, are one moment
DECEPTIVE_LEARNED = 3        # a deceptive move made this often from the same chord is the player's progression
BASS_LINE_MIN_NOTES = 4      # a bass moving by step one way through this many notes, window to window, is a bass line

KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
KEYS = [(t, m) for t in range(12) for m in ("major", "minor")]
LETTERS = "CDEFGAB"
LETTER_PC = (0, 2, 4, 5, 7, 9, 11)
PC_NEUTRAL = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
ODD_NAMES = {"E#", "B#", "Cb", "Fb"}

SCALES = {  # semitones above the tonic
    "major": {0, 2, 4, 5, 7, 9, 11}, "natural minor": {0, 2, 3, 5, 7, 8, 10}, "harmonic minor": {0, 2, 3, 5, 7, 8, 11},
    "melodic minor": {0, 2, 3, 5, 7, 9, 11}, "Mixolydian": {0, 2, 4, 5, 7, 9, 10}, "Lydian": {0, 2, 4, 6, 7, 9, 11},
    "Dorian": {0, 2, 3, 5, 7, 9, 10}, "Phrygian": {0, 1, 3, 5, 7, 8, 10},
}
KEY_FIT_SCALE = {"major": SCALES["major"], "minor": SCALES["natural minor"] | SCALES["harmonic minor"]}
MODAL_COLOUR = {"Mixolydian": "b7", "Lydian": "#4", "Dorian": "b3 and b7 over a natural 6", "Phrygian": "b2"}
SECONDARY_TARGETS = {"major": {2: "2m", 4: "3m", 5: "4", 7: "5", 9: "6m"},
                     "minor": {3: "b3", 5: "4m", 7: "5", 8: "b6", 10: "b7"}}
TENSIONS = {1: "b9", 2: "9", 3: "#9", 5: "11", 6: "#11", 8: "b13", 9: "13"}
TENSION_ORDER = (1, 2, 3, 5, 6, 8, 9)
ALTERED = {1, 3, 6, 8}
READING_BASES = ("", "m", "7", "maj7", "m7", "m7b5", "dim", "dim7", "aug", "sus4", "sus2", "7sus4", "6", "m6", "m(maj7)")
NO3_BASES = ("", "7", "maj7", "6")  # without its 3rd a chord has no quality: only these (major) forms are read so
SEVENTHS = ("7", "maj7", "m7", "m7b5", "7sus4", "m(maj7)", "dim7")
ADDED_NAMES = {10: "b7", 11: "maj7", 2: "9", 1: "b9", 3: "#9", 5: "11", 6: "#11", 8: "b13", 9: "13", 0: "root",
               4: "3rd", 7: "5th"}


# ============================================================================================== helpers
def _r(x, places: int = 3):
    return None if x is None else round(float(x), places)


def clock(ms: float) -> str:
    """m:ss from the first note, as summary.md writes times."""
    s = int(round(ms / 1000))
    return f"{s // 60}:{s % 60:02d}"


def parse_clock(text: str) -> float:
    """'1:15' or '75' (seconds) -> milliseconds. In m:ss the seconds stay under 60 ('1:75' is not a time)."""
    m = re.fullmatch(r"(?:(\d+):)?(\d+(?:\.\d+)?)", str(text).strip())
    if not m or (m.group(1) is not None and float(m.group(2)) >= 60):
        raise ValueError(f"not a time: {text!r} (use m:ss with seconds under 60, or seconds)")
    return (int(m.group(1) or 0) * 60 + float(m.group(2))) * 1000


def _signed(x: int) -> int:
    return (x + 6) % 12 - 6


def _sp_pc(sp) -> int:
    return (LETTER_PC[sp[0]] + sp[1]) % 12


def _sp_name(sp) -> str:
    return LETTERS[sp[0]] + ("#" * sp[1] if sp[1] > 0 else "b" * -sp[1])


def _sp(d) -> Optional[tuple]:
    return (d["letter"], d["acc"]) if d else None


def _parse_name(name: str) -> Optional[tuple]:
    if not name or name[0] not in LETTERS:
        return None
    acc = 0
    for ch in name[1:]:
        if ch == "#":
            acc += 1
        elif ch == "b":
            acc -= 1
        else:
            break
    return LETTERS.index(name[0]), acc


def _pearson(xs, ys) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else 0.0


def _union(intervals) -> List[list]:
    out: List[list] = []
    for a, b in sorted(intervals):
        if b <= a:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _cumulative(intervals: List[list], times: List[float]) -> List[float]:
    """Covered milliseconds before each time; intervals disjoint and sorted, times sorted."""
    out, acc, i = [], 0.0, 0
    for t in times:
        while i < len(intervals) and intervals[i][1] <= t:
            acc += intervals[i][1] - intervals[i][0]
            i += 1
        part = t - intervals[i][0] if i < len(intervals) and intervals[i][0] < t else 0.0
        out.append(acc + part)
    return out


def _overlap(intervals: List[list], a: float, b: float) -> float:
    return sum(max(0.0, min(y, b) - max(x, a)) for x, y in intervals)


def key_name(tonic: int, mode: str) -> str:
    return nashville.key_name_of(tonic, mode)


def parallel_key(key: str) -> str:
    """Same tonic letter, other mode: Ab major -> Ab minor, C# minor -> C# major."""
    tonic, mode = key.split(" ")
    return f"{tonic} {'minor' if mode == 'major' else 'major'}"


def pc_name(pc: int, key: Optional[str]) -> str:
    """A pitch class spelled as it reads in the key (Ab, not G#, in Eb major); neutral names without a key."""
    sp = _parse_name(PC_NEUTRAL[pc % 12])
    s = nashville.spell_in_key(sp, key) if key else None
    if s and (s["in_scale"] or (abs(s["acc"]) <= 1 and _sp_name((s["letter"], s["acc"])) not in ODD_NAMES)):
        sp = (s["letter"], s["acc"])
    return _sp_name(sp)


def midi_name(midi: Optional[int], key: Optional[str]) -> Optional[str]:
    if midi is None:
        return None
    name = pc_name(midi % 12, key)
    sp = _parse_name(name)
    return f"{name}{(midi - sp[1]) // 12 - 1}"


# ============================================================================================ sounding
def plausible_events(events) -> Tuple[List[dict], int]:
    """(events whose time is possible, how many were dropped): a time must be a finite number from 0 to MAX_EVENT_T_MS."""
    kept, dropped = [], 0
    for e in events:
        t = e.get("t_ms") if isinstance(e, dict) else None
        if isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) and 0 <= t <= MAX_EVENT_T_MS:
            kept.append(e)
        else:
            dropped += 1
    return kept, dropped


def sounding(events, end_ms: Optional[float] = None) -> dict:
    """Per-note sounding intervals: {notes: [{note, vel, on_ms, off_ms, end_ms, by}], pedal: [{down_ms, up_ms, value}],
    duration_ms, explicit_ends, held_at_end}. With sound_end events in the log they decide when each sound stopped (a
    pedal-held note sounds until its sound_end); without them a release ends a note unless the pedal is down, and a pedal
    lift ends every released note. A note still sounding when the log ends ends there (by 'still held'), or at end_ms
    when that is later (an open session: the page is still playing). Events at impossible times are left out
    (plausible_events). A note logged without a velocity has vel None."""
    evs = sorted(plausible_events(events)[0], key=lambda e: e["t_ms"])
    if end_ms is not None:
        end_ms = min(end_ms, MAX_EVENT_T_MS)
    duration_ms = max((e["t_ms"] for e in evs), default=0)
    explicit = any(e.get("kind") == "sound_end" for e in evs)
    notes: List[dict] = []
    open_: Dict[int, dict] = {}
    pedal: List[dict] = []
    pedal_down, pedal_since, pedal_value = False, 0, None

    def close(note: int, t: int, by: str) -> None:
        rec = open_.pop(note)
        rec["end_ms"], rec["by"] = max(t, rec["on_ms"]), by
        if rec["off_ms"] is None:
            rec["off_ms"] = rec["end_ms"]

    for e in evs:
        t, kind = e["t_ms"], e.get("kind")
        if kind == "on":
            n = e["note"]
            if n in open_:
                close(n, t, "repeat")
            vel = e.get("vel")
            rec = {"note": n, "vel": vel if isinstance(vel, (int, float)) and not isinstance(vel, bool) else None,
                   "on_ms": t, "off_ms": None, "end_ms": None, "by": None}
            open_[n] = rec
            notes.append(rec)
        elif kind == "off":
            rec = open_.get(e["note"])
            if rec and rec["off_ms"] is None:
                rec["off_ms"] = t
                if not explicit and not pedal_down:
                    close(e["note"], t, "release")
        elif kind == "pedal":
            if e.get("down") and not pedal_down:
                pedal_down, pedal_since, pedal_value = True, t, e.get("value")
            elif not e.get("down") and pedal_down:
                pedal_down = False
                pedal.append({"down_ms": pedal_since, "up_ms": t, "value": pedal_value})
                if not explicit:
                    for n in sorted(k for k, r in open_.items() if r["off_ms"] is not None):
                        close(n, t, "pedal")
        elif kind == "sound_end":
            rec = open_.get(e["note"])
            if rec and not (e.get("by") == "repeat" and rec["on_ms"] == t):  # a repeat's end logged after its new on
                close(e["note"], t, e.get("by") or "release")
    held_at_end = len(open_)
    if open_ and end_ms is not None and end_ms > duration_ms:
        duration_ms = int(end_ms)
    for n in sorted(open_):
        close(n, duration_ms, "still held")
    if pedal_down:
        pedal.append({"down_ms": pedal_since, "up_ms": duration_ms, "value": pedal_value})
    return {"notes": notes, "pedal": pedal, "duration_ms": duration_ms, "explicit_ends": explicit,
            "held_at_end": held_at_end}


def _step_timeline(notes: List[dict], lowest: bool) -> Tuple[List[int], list]:
    """(times, value from each time to the next): the lowest sounding MIDI note (None in silence), or the polyphony."""
    marks: Dict[int, List[tuple]] = {}
    for n in notes:
        if n["end_ms"] > n["on_ms"]:
            marks.setdefault(n["on_ms"], []).append((1, n["note"]))
            marks.setdefault(n["end_ms"], []).append((-1, n["note"]))
    times, values, count = [], [], {}
    for t in sorted(marks):
        for d, note in marks[t]:
            count[note] = count.get(note, 0) + d
            if count[note] <= 0:
                del count[note]
        times.append(t)
        values.append((min(count) if count else None) if lowest else sum(count.values()))
    return times, values


def _pc_count_timeline(notes: List[dict]) -> Tuple[List[int], list]:
    """(times, how many different pitch classes sound from each time to the next)."""
    marks: Dict[int, List[tuple]] = {}
    for n in notes:
        if n["end_ms"] > n["on_ms"]:
            marks.setdefault(n["on_ms"], []).append((1, n["note"] % 12))
            marks.setdefault(n["end_ms"], []).append((-1, n["note"] % 12))
    times, values, count = [], [], {}
    for t in sorted(marks):
        for d, pc in marks[t]:
            count[pc] = count.get(pc, 0) + d
            if count[pc] <= 0:
                del count[pc]
        times.append(t)
        values.append(len(count))
    return times, values


def sections_of(snd: dict) -> List[List[int]]:
    """[[start_ms, end_ms]]: stretches of playing separated by at least SECTION_GAP_MS with nothing sounding and the pedal
    up, or by more than SECTION_IDLE_MS with nothing struck. A section starts at its first note and ends when its last
    sound ends, or SECTION_IDLE_MS after its last attack when something is still sounding then."""
    spans = _union([(n["on_ms"], n["end_ms"]) for n in snd["notes"] if n["end_ms"] > n["on_ms"]] +
                   [(n["on_ms"], n["on_ms"] + 1) for n in snd["notes"] if n["end_ms"] <= n["on_ms"]])
    pedal = _union([(p["down_ms"], p["up_ms"]) for p in snd["pedal"]])
    out: List[List[int]] = []
    for a, b in spans:
        if out:
            gap_pedal = _overlap(pedal, out[-1][1], a)
            if a - out[-1][1] < SECTION_GAP_MS or gap_pedal >= a - out[-1][1]:
                out[-1][1] = max(out[-1][1], b)
                continue
        out.append([a, b])
    onsets = sorted(n["on_ms"] for n in snd["notes"])
    pieces: List[List[int]] = []
    for a, b in out:  # SECTION_IDLE_MS with nothing struck ends a section, whatever still sounds
        start = last = a
        for t in onsets[bisect_left(onsets, a):bisect_right(onsets, b)]:
            if t - last > SECTION_IDLE_MS:
                pieces.append([start, last + SECTION_IDLE_MS])
                start = t
            last = t
        pieces.append([start, min(b, last + SECTION_IDLE_MS)])
    out = pieces

    def gaps(i):
        return (out[i][0] - out[i - 1][1] if i > 0 else math.inf,
                out[i + 1][0] - out[i][1] if i + 1 < len(out) else math.inf)
    while len(out) > 1:  # a blip of a section (a stray note between pauses) joins the neighbour across the shorter pause,
        short = [i for i in range(len(out)) if out[i][1] - out[i][0] < SECTION_MIN_MS  # when that pause is short
                 and min(gaps(i)) < SECTION_JOIN_GAP_MS]
        if not short:
            break
        k = min(short, key=lambda i: out[i][1] - out[i][0])
        gap_before, gap_after = gaps(k)
        j = k - 1 if gap_before <= gap_after else k + 1
        lo, hi = min(k, j), max(k, j)
        out[lo:hi + 1] = [[out[lo][0], out[hi][1]]]
    return out


def _section_index(sections: List[List[int]], t: float) -> Optional[int]:
    k = bisect_right([s[0] for s in sections], t) - 1
    return k if k >= 0 and t <= sections[k][1] else None


def _timeline_in(times, values, a, b):
    """[(value, ms)] for a step timeline clipped to [a, b)."""
    out = []
    i = max(0, bisect_right(times, a) - 1)
    while i < len(times) and times[i] < b:
        lo, hi = max(times[i], a), min(times[i + 1] if i + 1 < len(times) else b, b)
        if hi > lo:
            out.append((values[i], hi - lo))
        i += 1
    return out


# ============================================================================================= windows
def _phrases(notes: List[dict]) -> List[dict]:
    """Stretches of sound separated by at least SILENCE_SPLIT_MS of silence: {start_ms, end_ms (the last sound's end),
    groups (onset group times before end_ms)}."""
    phrases: List[dict] = []
    for n in sorted(notes, key=lambda n: (n["on_ms"], n["note"])):
        if phrases and n["on_ms"] - phrases[-1]["end_ms"] < SILENCE_SPLIT_MS:
            p = phrases[-1]
            p["end_ms"] = max(p["end_ms"], n["end_ms"])
        else:
            p = {"start_ms": n["on_ms"], "end_ms": n["end_ms"], "onsets": []}
            phrases.append(p)
        p["onsets"].append(n["on_ms"])
    for p in phrases:
        groups: List[int] = []
        for t in p.pop("onsets"):
            if (not groups or t - groups[-1] > ONSET_GROUP_MS) and (t < p["end_ms"] or not groups):
                groups.append(t)
        p["groups"] = groups
    return phrases


def _heard(notes: List[dict]) -> Tuple[List[List[list]], List[list]]:
    """Per pitch class, when it is heard: while it sounds, and for at least HEARD_MIN_MS after its onset, but never past
    the end of the sound of its phrase (a broken chord is heard as a chord; silence is silence). This decides where
    windows start and end and what the key evidence hears; which pitch classes a held chord holds is decided on their
    real sound as well (_facts), so the extension never puts a note (a 38 ms grace note, a note that stopped just before
    the window) into a chord it does not sound in."""
    phrases = _phrases(notes)
    starts = [p["start_ms"] for p in phrases]
    per_pc: List[list] = [[] for _ in range(12)]
    for n in notes:
        p = phrases[bisect_right(starts, n["on_ms"]) - 1]
        per_pc[n["note"] % 12].append((n["on_ms"], max(n["end_ms"], min(n["on_ms"] + HEARD_MIN_MS, p["end_ms"]))))
    heard_pc = [_union(iv) for iv in per_pc]
    heard_any = _union([tuple(x) for iv in heard_pc for x in iv])
    return heard_pc, heard_any


def _segment_phrase(bounds: List[int], cum: List[List[float]], penalty: List[float], active: List[int]) -> List[int]:
    """Optimal window starts (indices into bounds) for one phrase; bounds[-1] is the phrase end."""
    m = len(bounds) - 1
    best = [0.0] + [math.inf] * m
    back = [0] * (m + 1)
    for j in range(1, m + 1):
        cj, bj = cum[j], bounds[j]
        for i in range(j - 1, -1, -1):
            if i < j - 1 and bounds[i] < bj - MAX_WINDOW_MS:
                break
            ci = cum[i]
            total = cj[12] - ci[12]
            cost = 0.0
            for pc in active:
                p = cj[pc] - ci[pc]
                cost += p if p < total - p else total - p
            if cost >= best[j]:
                break  # a window's cost only grows as it reaches further back, and best[i] >= 0
            if best[i] == math.inf:
                continue
            c = best[i] + cost + (penalty[i] if i else 0.0)
            if total < MIN_WINDOW_MS and not (i == 0 and j == m):
                c += SHORT_PENALTY_MS
            if c < best[j]:
                best[j], back[j] = c, i
    starts, j = [], m
    while j > 0:
        starts.append(back[j])
        j = back[j]
    return sorted(starts)


def harmonic_windows(snd: dict) -> dict:
    """{windows: [{start_ms, end_ms, heard_ms, share[12]}], transients: {count, ms}} (step 2 of the module docstring)."""
    notes = snd["notes"]
    heard_pc, heard_any = _heard(notes)
    lifts = sorted(p["up_ms"] for p in snd["pedal"])
    windows, transients = [], {"count": 0, "ms": 0}
    for ph in _phrases(notes):
        if ph["end_ms"] - ph["start_ms"] < MIN_WINDOW_MS:
            transients["count"] += 1
            transients["ms"] += ph["end_ms"] - ph["start_ms"]
            continue
        bounds = [g for g in ph["groups"] if g < ph["end_ms"]] + [ph["end_ms"]]
        per_pc = [_cumulative(heard_pc[pc], bounds) for pc in range(12)]
        anyc = _cumulative(heard_any, bounds)
        cum = [[per_pc[pc][k] for pc in range(12)] + [anyc[k]] for k in range(len(bounds))]
        active = [pc for pc in range(12) if per_pc[pc][-1] - per_pc[pc][0] > 0]
        penalty = []
        for b in bounds:
            near = bisect_left(lifts, b + PEDAL_NEAR_MS[0]) < bisect_right(lifts, b + PEDAL_NEAR_MS[1])
            penalty.append(WINDOW_PENALTY_MS * (PEDAL_DISCOUNT if near else 1.0))
        starts = _segment_phrase(bounds, cum, penalty, active)
        for n, i in enumerate(starts):
            j = starts[n + 1] if n + 1 < len(starts) else len(bounds) - 1
            total = cum[j][12] - cum[i][12]
            share = [(cum[j][pc] - cum[i][pc]) / total if total else 0.0 for pc in range(12)]
            windows.append({"start_ms": bounds[i], "end_ms": bounds[j], "heard_ms": total, "share": share, "merged": 1})
    return {"windows": windows, "transients": transients}


def _context(snd: dict, evs: List[dict]) -> dict:
    notes = snd["notes"]
    on_times = sorted((n["on_ms"], i) for i, n in enumerate(notes))
    chord_events = [e for e in evs if e.get("kind") == "chord"]
    low_t, low_v = _step_timeline(notes, lowest=True)
    poly_t, poly_v = _step_timeline(notes, lowest=False)
    longest = max((n["end_ms"] - n["on_ms"] for n in notes), default=0)
    sound = [_union([(n["on_ms"], n["end_ms"]) for n in notes if n["note"] % 12 == pc]) for pc in range(12)]
    down = [_union([(n["on_ms"], _key_end(n)) for n in notes if n["note"] % 12 == pc]) for pc in range(12)]
    return {"notes": notes, "on_times": on_times, "on_keys": [t for t, _ in on_times], "low": (low_t, low_v),
            "sound": sound, "sound_ends": [[iv[1] for iv in s] for s in sound],
            "down": down, "down_ends": [[iv[1] for iv in s] for s in down],
            "poly": (poly_t, poly_v), "pcpoly": _pc_count_timeline(notes),
            "pedal": [[p["down_ms"], p["up_ms"]] for p in snd["pedal"]],
            "lifts": sorted(p["up_ms"] for p in snd["pedal"]),
            "chords": chord_events, "live_t": [e["t_ms"] for e in chord_events], "longest": longest}


def _lift_near(lifts: List[int], t: float) -> bool:
    return bisect_left(lifts, t + PEDAL_NEAR_MS[0]) < bisect_right(lifts, t + PEDAL_NEAR_MS[1])


def _combine(a: dict, b: dict) -> dict:
    heard = a["heard_ms"] + b["heard_ms"]
    return {"start_ms": a["start_ms"], "end_ms": b["end_ms"], "heard_ms": heard,
            "share": [(a["share"][pc] * a["heard_ms"] + b["share"][pc] * b["heard_ms"]) / heard if heard else 0.0
                      for pc in range(12)],
            "merged": a["merged"] + b["merged"],
            "dropped": sorted(set(a.get("dropped") or ()) | set(b.get("dropped") or ()))} | \
        ({"tail": b["tail"], "tail_share": b["tail_share"]} if b.get("tail") else {})


def passing_tones(w: dict, ctx: dict, scale: set) -> set:
    """Pitch classes of a window that are chromatic passing or neighbour notes: outside the key's scale, never the bass,
    and every attack of them in the window short (key down under PASSING_MAX_MS) and stepped into and out of in one
    direction (F5 E5 Eb5 over an Ab chord in Eb major), or a step away from one note and back to it within
    NEIGHBOUR_STEP_MS each way, silent again when it returns (F5 G5 F5 over a Bb bass in Db major). They are left out
    of the chord."""
    a, b = w["start_ms"], w["end_ms"]
    near = _onsets_between(ctx, a - ctx["longest"] - PASSING_STEP_MS, b + PASSING_STEP_MS)
    out = set()
    for pc in w["pcs"]:
        if pc in scale or (w["bass"] is not None and pc == w["bass"] % 12):
            continue
        # every note of it sounding here, struck inside the window or ringing on into it under the pedal
        hits = [n for n in near if n["note"] % 12 == pc and n["on_ms"] < b and n["end_ms"] > a]
        if not hits or len({round(n["on_ms"] / ONSET_GROUP_MS) for n in hits if n["on_ms"] >= a}) >= 3:
            continue  # (a note struck again and again is a tone of its own, not a note passing through)
        ok = True
        for n in hits:
            voice = [m for m in near if m is not n and abs(m["note"] - n["note"]) <= 4]
            struck_with = [m for m in voice if abs(m["on_ms"] - n["on_ms"]) <= ONSET_GROUP_MS]
            before = [m for m in voice if m["on_ms"] < n["on_ms"] - ONSET_GROUP_MS]
            after = [m for m in voice if m["on_ms"] > n["on_ms"] + ONSET_GROUP_MS]
            prev = before[-1] if before else None
            nxt = after[0] if after else None
            if not struck_with and prev is not None and nxt is not None and prev["note"] == nxt["note"] and \
                    1 <= abs(n["note"] - prev["note"]) <= 2 and _key_end(n) - n["on_ms"] <= PASSING_MAX_MS and \
                    n["on_ms"] - prev["on_ms"] <= NEIGHBOUR_STEP_MS and nxt["on_ms"] - n["on_ms"] <= NEIGHBOUR_STEP_MS \
                    and n["end_ms"] <= nxt["on_ms"] + CRUSH_MS:
                continue  # a neighbour note: a step away from a note and straight back to it (F5 G5 F5), gone when
                # the note returns (one the pedal rings on against its return is a colour, not a neighbour)
            if struck_with or prev is None or nxt is None or \
                    (n["off_ms"] if n["off_ms"] is not None else n["end_ms"]) - n["on_ms"] > PASSING_MAX_MS or \
                    n["on_ms"] - prev["on_ms"] > PASSING_STEP_MS or nxt["on_ms"] - n["on_ms"] > PASSING_STEP_MS or \
                    not 1 <= abs(n["note"] - prev["note"]) <= 2 or not 1 <= abs(nxt["note"] - n["note"]) <= 2 or \
                    (n["note"] - prev["note"] > 0) != (nxt["note"] - n["note"] > 0):
                if not struck_with and _run_length(n, ctx) >= RUN_MIN_NOTES:
                    continue  # a note of a longer one-way scale run (C5 Db5 D5 Eb5 under the pedal): passing
                ok = False  # struck with a neighbour (a cluster), held, or not a one-way step line: a chord tone
                break
        if ok:
            out.add(pc)
    return out


def _key_end(n: dict) -> float:
    """When a note's key came up (its sound may ring on under the pedal)."""
    return n["off_ms"] if n["off_ms"] is not None else n["end_ms"]


def _sound_in(ctx: dict, pc: int, a: float, b: float, which: str = "sound") -> float:
    """Milliseconds pitch class pc really sounds (key or pedal) inside [a, b); with which='down', its keys are down."""
    ivs, ends = ctx[which][pc], ctx[which + "_ends"][pc]
    i, total = bisect_right(ends, a), 0.0
    while i < len(ivs) and ivs[i][0] < b:
        total += max(0.0, min(ivs[i][1], b) - max(ivs[i][0], a))
        i += 1
    return total


def _run_length(n: dict, ctx: dict) -> int:
    """How many single notes (n included) make the one-way stepwise run through n: each the next attack a half or whole
    step on in the same direction, at most RUN_STEP_MS later, struck alone. 0 when n is held longer than RUN_HOLD_MS."""
    if (n["off_ms"] if n["off_ms"] is not None else n["end_ms"]) - n["on_ms"] > RUN_HOLD_MS:
        return 0
    pool = _onsets_between(ctx, n["on_ms"] - RUN_STEP_MS * RUN_MIN_NOTES, n["on_ms"] + RUN_STEP_MS * RUN_MIN_NOTES + 1)

    def alone(m):
        return not any(x is not m and abs(x["on_ms"] - m["on_ms"]) <= ONSET_GROUP_MS and abs(x["note"] - m["note"]) <= 4
                       for x in pool)

    def walk(sign: int, later: bool) -> int:
        count, cur = 0, n
        while True:
            dt = (lambda m: m["on_ms"] - cur["on_ms"]) if later else (lambda m: cur["on_ms"] - m["on_ms"])
            nxt = [m for m in pool if ONSET_GROUP_MS < dt(m) <= RUN_STEP_MS and
                   1 <= ((m["note"] - cur["note"]) if later else (cur["note"] - m["note"])) * sign <= 2 and alone(m)]
            if not nxt:
                return count
            cur = min(nxt, key=dt)
            count += 1
    return max(1 + walk(s, False) + walk(s, True) for s in (1, -1))


def _ornament(n: dict, near: List[dict]) -> bool:
    """One attack heard as an ornament, not a chord tone:
    - a grace note: sounding under GRACE_MS;
    - a crush: struck at most CRUSH_MS before a louder note a half or whole step away, at most CRUSH_VEL_RATIO of its
      velocity;
    - a brush: struck within CRUSH_MS of such a neighbour (before or after it) and released at once, the pedal ringing
      it on: its key down under GRACE_MS while the neighbour's stays down at least twice as long, or softer by
      CRUSH_VEL_RATIO and released in under half the neighbour's time (G4 v33 for 50 ms, 40 ms after Ab4 v79)."""
    if n["end_ms"] - n["on_ms"] < GRACE_MS:
        return True
    key = _key_end(n) - n["on_ms"]
    for m in near:
        if m is n or not 1 <= abs(m["note"] - n["note"]) <= 2 or abs(m["on_ms"] - n["on_ms"]) > CRUSH_MS:
            continue
        softer = n["vel"] is not None and m["vel"] is not None and n["vel"] <= CRUSH_VEL_RATIO * m["vel"]
        m_key = _key_end(m) - m["on_ms"]
        if (m["on_ms"] > n["on_ms"] and softer) or (key < GRACE_MS and m_key >= max(GRACE_MS, 2 * key)) or \
                (softer and 2 * key < m_key):
            return True
    return False


def ornaments(w: dict, ctx: dict) -> set:
    """Pitch classes of a window heard only as ornaments: every attack of them inside the window is a grace note, a
    crush or a brush (_ornament), and none rings on from before the window. Never the bass. Left out of the chord."""
    a, b = w["start_ms"], w["end_ms"]
    near = _onsets_between(ctx, a - ctx["longest"] - 1, b + CRUSH_MS + 1)
    bass_pc = w["bass"] % 12 if w["bass"] is not None else None
    out = set()
    for pc in w["pcs"]:
        if pc == bass_pc:
            continue
        own = [n for n in near if n["note"] % 12 == pc and n["end_ms"] > a and n["on_ms"] < b]
        if not own or any(n["on_ms"] < a for n in own):
            continue
        if all(_ornament(n, near) for n in own):
            out.add(pc)
    return out


def merge_bass_walks(windows: List[dict], ctx: dict) -> List[dict]:
    """Short back-to-back windows (each under WALK_STEP_MAX_MS) over a low bass that changes every window, under the
    same few notes above it, are one bass line under those notes when they make one (Eb1 Bb0 Ab1 B0 under a repeated
    Bb-Eb): joined, and kept joined only if the joined window reads as a bass line."""
    out: List[dict] = []
    i = 0
    while i < len(windows):
        up = set(windows[i].get("upper_pcs") or ())
        j = i
        while j + 1 < len(windows):
            w, nxt = windows[j], windows[j + 1]
            if not (w["end_ms"] == nxt["start_ms"] and w["low_bass"] and nxt["low_bass"] and up and
                    len(up) <= BASS_LINE_MAX_UPPER and set(nxt.get("upper_pcs") or ()) == up and
                    _walk_short(w) and _walk_short(nxt) and w["bass"] % 12 != nxt["bass"] % 12):
                break
            j += 1
        if j > i:
            merged = windows[i]
            for w in windows[i + 1:j + 1]:
                merged = _combine(merged, w)
            _facts(merged, ctx)
            if merged["texture"] == "bass line":
                out.append(merged)
                i = j + 1
                continue
        out.append(windows[i])
        i += 1
    return out


def _walk_short(w: dict) -> bool:
    """A step of a bass walk: under WALK_STEP_MAX_MS for each bass note it holds."""
    return w["end_ms"] - w["start_ms"] < WALK_STEP_MAX_MS * max(1, len(w.get("figure") or ()))


def _building(w: dict, nxt: dict, ctx: dict) -> bool:
    """w is the start of nxt's chord being built: shorter than BUILD_MAX_MS, over the same bass, nxt only adds notes,
    the pedal stays down from just after w's first attack into nxt, and nothing sounding in w stops before nxt (a
    re-strike is not a stop). Adding the 3rd to a chord without one is a suspension, not a build."""
    a, b = w["start_ms"], nxt["start_ms"]
    pw, pn = set(w["pcs"]), set(nxt["pcs"])
    if w["end_ms"] != b or b - a >= BUILD_MAX_MS or not pw < pn or w["bass"] is None or nxt["bass"] is None or \
            w["bass"] % 12 != nxt["bass"] % 12:
        return False
    lo = a + PEDAL_NEAR_MS[1]
    if not any(d <= lo and u > b for d, u in ctx["pedal"]):
        return False
    for n in _onsets_between(ctx, a - ctx["longest"] - 1, b):
        if lo < n["end_ms"] < b and n["by"] != "repeat":
            return False
    thirds = {(w["bass"] + 3) % 12, (w["bass"] + 4) % 12}
    return bool(thirds & pw) or not thirds & pn


def _stable_ms(w: dict, ctx: dict) -> float:
    """How long before its end a window last gained a pitch class (notes sounding at its start count as present)."""
    a, b = w["start_ms"], w["end_ms"]
    notes, seen, last_new = ctx["notes"], set(), a
    lo = bisect_left(ctx["on_keys"], a - ctx["longest"] - 1)
    for _, i in ctx["on_times"][lo:bisect_left(ctx["on_keys"], b)]:
        m = notes[i]
        if m["on_ms"] < a:
            if m["end_ms"] > a:
                seen.add(m["note"] % 12)
        elif m["note"] % 12 not in seen:
            seen.add(m["note"] % 12)
            last_new = m["on_ms"]
    return b - last_new


def merge_growth(windows: List[dict], ctx: dict) -> List[dict]:
    """A short window (under GROWTH_MS) still gaining pitch classes when the next window starts, whose notes all belong to
    that next window, is the next window's beginning: an arpeggio unfolding, not a chord of its own. Across a pedal lift
    it must also share the next window's bass. A held sus2 before its add9 is stable, so it stays its own window."""
    ws = list(windows)
    k = 0
    while k < len(ws) - 1:
        w, nxt = ws[k], ws[k + 1]
        same_bass =w["bass"] is not None and nxt["bass"] is not None and w["bass"] % 12 == nxt["bass"] % 12
        if w["end_ms"] - w["start_ms"] < GROWTH_MS and w["end_ms"] == nxt["start_ms"] and \
                set(w["pcs"]) <= set(nxt["pcs"]) and (same_bass or not _lift_near(ctx["lifts"], w["end_ms"])) and \
                _stable_ms(w, ctx) < GROWTH_STABLE_MS:
            merged = _combine(w, nxt)
            _facts(merged, ctx)
            if merged["pcs"] == nxt["pcs"]:
                ws[k:k + 2] = [merged]
                k = max(0, k - 1)
                continue
        k += 1
    return ws


def _facts(w: dict, ctx: dict) -> None:
    """The numeric facts of a window: chord pitch classes, bass, the voicing handed to detect, touch, live events."""
    a, b = w["start_ms"], w["end_ms"]
    notes = ctx["notes"]
    drop = set(w.get("dropped") or ())  # passing notes and ornaments (passing_tones, ornaments), not chord tones
    ta, tb = w.get("tail") or (a, b)  # a chord built note by note under one pedal is named as it stands complete
    share = w.get("tail_share") or w["share"]
    sound_ms = [_sound_in(ctx, pc, ta, tb) for pc in range(12)]
    need = min(CHORD_SOUND_MS, CHORD_SOUND_SHARE * (tb - ta))
    heard_pcs = [pc for pc in range(12) if share[pc] >= CHORD_SHARE and pc not in drop]
    sounding_pcs = [pc for pc in heard_pcs if sound_ms[pc] >= need]  # a held chord holds only what really sounds
    lows: Dict[int, float] = {}
    figure: List[list] = []
    for note, ms in _timeline_in(*ctx["low"], a, b):
        if note is None:
            continue
        lows[note] = lows.get(note, 0) + ms
        if figure and figure[-1][0] == note:
            figure[-1][1] += ms
        else:
            figure.append([note, ms])
    kept: List[list] = []
    for note, ms in figure:
        if ms < BASS_FIGURE_MIN_MS:
            continue
        if kept and kept[-1][0] == note:
            kept[-1][1] += ms
        else:
            kept.append([note, ms])
    low_total = sum(lows.values())
    low_pcs: Dict[int, float] = {}
    for note, ms in lows.items():
        low_pcs[note % 12] = low_pcs.get(note % 12, 0) + ms
    bass_pc = min(low_pcs, key=lambda pc: (-low_pcs[pc], min(n for n in lows if n % 12 == pc))) if lows else None
    bass = min((n for n in lows if n % 12 == bass_pc), key=lambda n: (-lows[n], n)) if lows else None
    lo = bisect_left(ctx["on_keys"], a - ctx["longest"] - 1)
    struck = [notes[i] for _, i in ctx["on_times"][lo:bisect_left(ctx["on_keys"], b)] if notes[i]["end_ms"] > a]
    hits = [n for n in struck if a <= n["on_ms"] < b]
    pitches = [n["note"] for n in struck]
    polys = [c for c, _ in _timeline_in(*ctx["poly"], a, b)]
    together = sum(ms for c, ms in _timeline_in(*ctx["pcpoly"], a, b) if c >= 3)
    groups: List[list] = []
    for n in sorted(hits, key=lambda n: (n["on_ms"], n["note"])):
        if groups and n["on_ms"] - groups[-1][0] <= ONSET_GROUP_MS:
            groups[-1][1].append(n["note"])
        else:
            groups.append([n["on_ms"], [n["note"]]])
    singles = [g[1][0] for g in groups if len(g[1]) == 1]
    moves = [abs(x - y) for x, y in zip(singles, singles[1:]) if x != y]
    steps = sum(1 for m in moves if m <= 2)
    sim_share = together / (b - a) if b > a else 0.0
    low_bass = bass is not None and bass < BASS_MAX_MIDI
    bass_pc_ = bass % 12 if bass is not None else None
    strike = 0  # the most pitch classes struck together (within CHORD_STRIKE_MS), the bass note's own low octaves aside
    upper_ms: Dict[int, float] = {}  # sounding time per pitch class of the notes above the bass (its low octaves aside)
    top_fig = max((n for n, _ in kept), default=None) if low_bass else None
    over_fig: Dict[int, float] = {}  # ...and of the notes above the whole bass figure
    ordered = sorted((n for n in hits if not (n["note"] % 12 == bass_pc_ and n["note"] < BASS_MAX_MIDI)),
                     key=lambda n: n["on_ms"])
    for i, n in enumerate(ordered):
        strike = max(strike, len({m["note"] % 12 for m in ordered[i:] if m["on_ms"] - n["on_ms"] <= CHORD_STRIKE_MS}))
    fig_pcs = {n % 12 for n, _ in kept}
    for n in struck:
        ov = min(n["end_ms"], b) - max(n["on_ms"], a)
        if ov <= 0 or (n["note"] % 12 == bass_pc_ and n["note"] < BASS_MAX_MIDI):
            continue
        upper_ms[n["note"] % 12] = upper_ms.get(n["note"] % 12, 0) + ov
        if top_fig is not None and n["note"] > top_fig and not (n["note"] % 12 in fig_pcs and n["note"] < BASS_MAX_MIDI):
            over_fig[n["note"] % 12] = over_fig.get(n["note"] % 12, 0) + ov  # (a low octave of a bass note is the bass)
    need_w = min(CHORD_SOUND_MS, CHORD_SOUND_SHARE * (b - a))
    # the voicing's range counts notes that really sound in the window (the next chord's bass struck in its last
    # moment does not make this chord wide)
    pitches = [n["note"] for n in struck if min(n["end_ms"], b) - max(n["on_ms"], a) >= need_w] or pitches
    texture, bass_line = "chord", None
    above_fig = {pc for pc, ms in over_fig.items() if ms >= need_w}
    if len(heard_pcs) >= 3 and sim_share < LINE_SIM_SHARE:
        texture = "line" if moves and steps / len(moves) >= LINE_STEP_SHARE else "broken chord"
    elif low_bass and low_total and low_pcs[bass_pc] / low_total < BASS_HELD_SHARE and len(fig_pcs) >= 3 and \
            fig_pcs - above_fig and 0 < len(above_fig) <= BASS_LINE_MAX_UPPER:
        texture = "bass line"  # the lowest voice walks through notes the voices above it do not hold
        bass_line = {"notes": [n for n, _ in kept], "upper": sorted(above_fig)}
    elif not low_bass and len(heard_pcs) >= 3 and len(singles) >= LINE_MIN_ONSETS and groups and \
            len(singles) / len(groups) >= LINE_SINGLE_SHARE and moves and steps / len(moves) >= LINE_RUN_STEP_SHARE:
        texture = "line"  # a pedalled run in the treble: the pedal rings its notes on, but they came one at a time
    # notes that came one or two at a time keep every note the ear groups; a held chord keeps what really sounds
    chord_pcs = list(heard_pcs if texture in ("line", "broken chord") else sounding_pcs)
    if bass is not None and bass % 12 not in chord_pcs:
        chord_pcs.append(bass % 12)
    upper_pcs = sorted(pc for pc in chord_pcs if upper_ms.get(pc, 0) >= need_w)
    above: Dict[int, int] = {}
    for n in struck:
        pc = n["note"] % 12
        if bass is not None and n["note"] > bass and pc in chord_pcs and (pc not in above or n["note"] < above[pc]):
            above[pc] = n["note"]
    voicing = [bass] if bass is not None else []
    for pc in chord_pcs:
        if bass is None or pc != bass % 12:
            voicing.append(above.get(pc, (bass if bass is not None else 48) + (pc - (bass or 0)) % 12))
    if bass is not None and bass % 12 in above:
        voicing.append(above[bass % 12])
    vels = [n["vel"] for n in hits if n["vel"] is not None]
    attacks, pc_vel = [0] * 12, [None] * 12  # per pitch class: attacks in the window (a chord's octaves are one), top vel
    last_on = [None] * 12
    for n in sorted(hits, key=lambda n: n["on_ms"]):
        pc = n["note"] % 12
        if last_on[pc] is None or n["on_ms"] - last_on[pc] > ONSET_GROUP_MS:
            attacks[pc] += 1
            last_on[pc] = n["on_ms"]
        if n["vel"] is not None:
            pc_vel[pc] = max(pc_vel[pc] or 0, n["vel"])
    bass_onsets = 0  # attacks of the bass pitch class below middle C (its octaves together are one), one more when it
    if bass is not None:  # rings on into the window
        low = [n["on_ms"] for n in struck if n["note"] % 12 == bass % 12 and n["note"] < BASS_MAX_MIDI]
        group_t = None
        for t_on in sorted(t for t in low if t >= a):
            if group_t is None or t_on - group_t > ONSET_GROUP_MS:
                bass_onsets += 1
                group_t = t_on
        bass_onsets += any(t < a for t in low)
    chords, live_t = ctx["chords"], ctx["live_t"]
    lo_i, hi_i = bisect_left(live_t, a), bisect_left(live_t, b)
    named: Dict[str, float] = {}
    for k in range(max(0, lo_i - 1), hi_i):
        e = chords[k]
        end = chords[k + 1]["t_ms"] if k + 1 < len(chords) else b
        ms = min(end, b) - max(e["t_ms"], a)
        if e.get("chord") and ms > 0:
            named[e["chord"]] = named.get(e["chord"], 0) + ms
    w.update({
        "pcs": sorted(chord_pcs), "bass": bass,
        "bass_share": low_pcs[bass_pc] / low_total if bass is not None else 0.0,  # the bass pitch class, any octave
        "figure": kept, "detect_notes": sorted(set(voicing)),
        "low_bass": low_bass, "sound_ms": sound_ms, "strike_pcs": strike, "upper_pcs": upper_pcs, "bass_line": bass_line,
        "key_ms": [_sound_in(ctx, pc, a, b, "down") for pc in range(12)], "attacks": attacks, "pc_vel": pc_vel,
        "bass_onsets": bass_onsets,
        "texture": texture, "together_share": sim_share,
        "line": {"single_onsets": len(singles), "moves": len(moves), "steps": steps,
                 "notes": [n for g in groups for n in g[1]]},
        "touch": {"distinct_notes": len(set(pitches)), "max_polyphony": max(polys) if polys else 0,
                  "lowest": min(pitches) if pitches else None, "highest": max(pitches) if pitches else None,
                  "spread": (max(pitches) - min(pitches)) if pitches else 0,
                  "register": round(sum(n["note"] for n in hits) / len(hits)) if hits else None,
                  "onsets": len(hits), "vel_mean": _r(sum(vels) / len(vels), 1) if vels else None,
                  "vel_min": min(vels) if vels else None, "vel_max": max(vels) if vels else None,
                  "pedal_share": _r(_overlap(ctx["pedal"], a, b) / (b - a), 2) if b > a else 0.0},
        "live": {"events": sum(1 for e in chords[lo_i:hi_i] if e.get("chord")),
                 "names": [[n, _r(ms / 1000, 2)] for n, ms in sorted(named.items(), key=lambda kv: -kv[1])[:3]]},
    })


# ============================================================================================ key areas
def key_frames(snd: dict, sections: Optional[List[List[int]]] = None) -> dict:
    """Per second: {scores: {frame: [24]}, r: {frame: [24] or None}} for the pitch classes heard in the KEY_CONTEXT_MS
    around it (KEYS order). With sections, frames exist only inside sections (a pause of any length costs nothing), a
    frame hears only its own section, and a frame at a section's edge outside it hears nothing."""
    heard_pc, _ = _heard(snd["notes"])
    spans = sections or [[0, snd["duration_ms"]]]
    index: List[int] = []
    for s0, s1 in spans:
        k0 = int(s0 // KEY_FRAME_MS)
        index += [k for k in range(k0, max(k0 + 1, math.ceil(s1 / KEY_FRAME_MS))) if not index or k > index[-1]]
    centers = [(k + 0.5) * KEY_FRAME_MS for k in index]
    los, his = [], []
    for c in centers:
        lo, hi = max(0.0, c - KEY_CONTEXT_MS / 2), c + KEY_CONTEXT_MS / 2
        if sections:
            k = _section_index(sections, c)
            if k is None:
                lo = hi = max(los[-1] if los else 0.0, his[-1] if his else 0.0, c - KEY_CONTEXT_MS / 2)
            else:
                lo, hi = max(lo, sections[k][0]), min(hi, sections[k][1])
        lo = max(lo, los[-1] if los else 0.0)
        los.append(lo)
        his.append(max(hi, lo, his[-1] if his else 0.0))
    cum_lo = [_cumulative(heard_pc[pc], los) for pc in range(12)]
    cum_hi = [_cumulative(heard_pc[pc], his) for pc in range(12)]
    scores, rs = {}, {}
    for k, frame in enumerate(index):
        hist = [cum_hi[pc][k] - cum_lo[pc][k] for pc in range(12)]
        total = sum(hist)
        if total < KEY_MIN_HEARD_MS or sum(1 for h in hist if h > 0) < 3:
            scores[frame] = [0.0] * len(KEYS)
            rs[frame] = None
            continue
        r = {(t, m): _pearson([hist[(i + t) % 12] for i in range(12)], KK_MAJOR if m == "major" else KK_MINOR)
             for t, m in KEYS}
        row = []
        for t, m in KEYS:
            s = r[(t, m)]
            if m == "minor":
                tonic_w, lt_w = hist[t], hist[(t + 11) % 12]
                heard = min(1.0, lt_w / (LT_SHARE * tonic_w)) if tonic_w > 0 else 0.0
                r_rel, r_par = r[((t + 3) % 12, "major")], r[(t, "major")]
                raw = s
                s = raw - (1 - heard) * max(0.0, raw - r_rel + LT_EDGE)
                floor = min(raw, r_par + LT_FLOOR)
                if floor > s:
                    s += min(1.0, max(0.0, (r_par - r_rel) / LT_FLOOR_FADE)) * (floor - s)
            fit = sum(hist[(t + i) % 12] for i in KEY_FIT_SCALE[m]) / total
            row.append(s + KEY_FIT_WEIGHT * (fit - 1.0))
        scores[frame] = row
        rs[frame] = [r[key] for key in KEYS]
    return {"scores": scores, "r": rs}


def key_path(scores: List[List[float]]) -> List[int]:
    """Viterbi over the 24 keys: the most total score, less KEY_SWITCH_PENALTY per change."""
    n = len(KEYS)
    score = list(scores[0])
    back: List[List[int]] = []
    for row_scores in scores[1:]:
        top = max(range(n), key=lambda s: score[s])
        row, new = [], []
        for s in range(n):
            stay, switch = score[s], score[top] - KEY_SWITCH_PENALTY
            row.append(s if stay >= switch else top)
            new.append(max(stay, switch) + row_scores[s])
        back.append(row)
        score = new
    state = max(range(n), key=lambda s: score[s])
    path = [state]
    for row in reversed(back):
        state = row[state]
        path.append(state)
    return path[::-1]


def _areas_from_path(path: List[int], windows: List[dict], start_ms: int, end_ms: int, k0: int = 0,
                     section: int = 0) -> List[dict]:
    """Key areas along one section's key path (path[0] is frame k0); a change moves to the nearest window start."""
    starts = sorted(w["start_ms"] for w in windows if start_ms <= w["start_ms"] < end_ms)
    areas: List[dict] = []
    for k, s in enumerate(path):
        if areas and areas[-1]["state"] == s:
            continue
        t = (k0 + k) * KEY_FRAME_MS
        if areas and starts:
            i = bisect_left(starts, t)
            near = [x for x in starts[max(0, i - 1):i + 1] if abs(x - t) <= KEY_SNAP_MS]
            if near:
                t = min(near, key=lambda x: abs(x - t))
        t = min(max(t, start_ms), end_ms)
        if areas:
            areas[-1]["end_ms"] = t
        areas.append({"state": s, "start_ms": start_ms if not areas else t, "end_ms": end_ms, "section": section})
    return [a for a in areas if a["end_ms"] > a["start_ms"] or len(areas) == 1]


def _area_at(areas: List[dict], t: float) -> Optional[dict]:
    """The key area sounding at t, else the last one before it (t in a pause), else the first."""
    inside = next((a for a in areas if a["start_ms"] <= t < a["end_ms"]), None)
    if inside:
        return inside
    before = [a for a in areas if a["start_ms"] <= t]
    return before[-1] if before else (areas[0] if areas else None)


def _in_area(w: dict, area: dict) -> bool:
    mid = (w["start_ms"] + w["end_ms"]) / 2
    return area["start_ms"] <= mid < area["end_ms"] or (area["end_ms"] == area["start_ms"] == mid)


def _chord_time(areas: List[dict], windows: List[dict], skip=()) -> Dict[int, float]:
    """Window milliseconds per key state (silence does not count), leaving out windows inside the skip spans."""
    by: Dict[int, float] = {}
    for w in windows:
        mid = (w["start_ms"] + w["end_ms"]) / 2
        if any(a <= mid < b for a, b in skip):
            continue
        area = next((x for x in areas if _in_area(w, x)), None) or \
            next((x for x in areas if x["start_ms"] <= w["start_ms"] < x["end_ms"]), None)  # (held on past its area)
        if area:
            by[area["state"]] = by.get(area["state"], 0) + w["end_ms"] - w["start_ms"]
    return by


def _home(areas: List[dict], windows: List[dict], skip=()) -> Optional[int]:
    """The key state with the most chord time; ties go to the key that came first."""
    by = _chord_time(areas, windows, skip)
    if not by:
        return areas[0]["state"] if areas else None
    return max(by, key=lambda s: (by[s], -min(a["start_ms"] for a in areas if a["state"] == s)))


def _join_same(areas: List[dict]) -> List[dict]:
    out: List[dict] = []
    for a in areas:
        if out and out[-1]["state"] == a["state"] and out[-1].get("section") == a.get("section"):
            out[-1]["end_ms"] = a["end_ms"]
        else:
            out.append(dict(a))
    return out


def _area_roots(area: dict, windows: List[dict]) -> Dict[int, float]:
    """Chord (or broken-chord) root -> milliseconds, over the windows of three or more pitch classes in an area."""
    roots: Dict[int, float] = {}
    for w in windows:
        root = w.get("root_pc") if w.get("root_pc") is not None else w.get("implied_root")
        if _in_area(w, area) and root is not None and len(w["pcs"]) >= 3:
            roots[root] = roots.get(root, 0) + w["end_ms"] - w["start_ms"]
    return roots


def _fragment_centre(area: dict, windows: List[dict], heard_pc: Optional[List[List[list]]]) -> Optional[int]:
    """The key state of a short passage's own centre: the key on the root of its longest-held chord (minor when that
    chord is minor), when that key's scale holds FRAGMENT_FIT of what is heard there. None when nothing fits."""
    best, best_ms = None, 0.0
    for w in windows:
        root = w.get("root_pc") if w.get("root_pc") is not None else w.get("implied_root")
        if _in_area(w, area) and root is not None and len(w["pcs"]) >= 3 and w["end_ms"] - w["start_ms"] > best_ms:
            best, best_ms = w, w["end_ms"] - w["start_ms"]
    if best is None or heard_pc is None:
        return None
    root = best["root_pc"] if best.get("root_pc") is not None else best["implied_root"]
    mode = "minor" if (root + 3) % 12 in best["pcs"] and (root + 4) % 12 not in best["pcs"] else "major"
    prof = [_overlap(heard_pc[pc], area["start_ms"], area["end_ms"]) for pc in range(12)]
    total = sum(prof)
    fit = sum(prof[(root + i) % 12] for i in KEY_FIT_SCALE[mode]) / total if total else 0.0
    return KEYS.index((root, mode)) if fit >= FRAGMENT_FIT else None


def consolidate_areas(areas: List[dict], windows: List[dict],
                      heard_pc: Optional[List[List[list]]] = None) -> Tuple[List[dict], List[dict]]:
    """Areas holding fewer than two chord roots (each with AREA_ROOT_SHARE of the area's chord time; windows of three or
    more pitch classes) join a neighbour in the same section that they touch (within KEY_JOIN_MS). A short section
    (under FRAGMENT_MAX_MS) with no other area is numbered in its own centre, or kept as read and marked too short to
    call. Anything else joins the home key. (areas, absorbed)."""
    areas = [dict(a) for a in areas]
    absorbed: List[dict] = []
    checked = set()
    while len(areas) > 1:
        weak = None
        for i, area in enumerate(areas):
            if (area["state"], area["start_ms"]) in checked:
                continue
            roots = _area_roots(area, windows)
            total = sum(roots.values())
            strong = [r for r, ms in roots.items() if ms >= AREA_ROOT_SHARE * total]
            if len(strong) < 2:
                nroots = len(strong)
                weak = (i, f"{nroots} chord root{'s' if nroots != 1 else ''}: no progression of its own")
                break
            if not _established(areas, i, windows):
                weak = (i, "no tonic chord of its own, and no two chords that the key next to it lacks (beyond a "
                           "chord's own 3rd): one chord's colour, not a new key")
                break
        if weak is None:
            break
        i, why = weak
        area = areas[i]
        section = area.get("section")
        inside = [w for w in windows if _in_area(w, area)]
        first = inside[0]["start_ms"] if inside else area["start_ms"]
        last = inside[-1]["end_ms"] if inside else area["end_ms"]
        prev_ok = i > 0 and areas[i - 1].get("section") == section
        next_ok = i + 1 < len(areas) and areas[i + 1].get("section") == section
        before = [w for w in windows if prev_ok and _in_area(w, areas[i - 1])]
        after = [w for w in windows if next_ok and _in_area(w, areas[i + 1])]
        skip = [(a["start_ms"], a["end_ms"]) for a in absorbed if a.get("to_home")] + [(area["start_ms"], area["end_ms"])]
        home = _home(areas, windows, skip)
        if before and first - before[-1]["end_ms"] <= KEY_JOIN_MS:
            target = i - 1
        elif after and after[0]["start_ms"] - last <= KEY_JOIN_MS:
            target = i + 1
        else:
            target = None
        alone = not prev_ok and not next_ok
        if target is not None:
            absorbed.append({"state": area["state"], "start_ms": area["start_ms"], "end_ms": area["end_ms"],
                             "into": areas[target]["state"], "why": why})
            areas[target]["start_ms"] = min(areas[target]["start_ms"], area["start_ms"])
            areas[target]["end_ms"] = max(areas[target]["end_ms"], area["end_ms"])
            del areas[i]
        elif alone and area["end_ms"] - area["start_ms"] < FRAGMENT_MAX_MS:
            centre = _fragment_centre(area, windows, heard_pc)
            if centre is not None and centre != area["state"]:
                absorbed.append({"state": area["state"], "start_ms": area["start_ms"], "end_ms": area["end_ms"],
                                 "into": centre, "fragment": True,
                                 "why": why + "; a short passage after a pause, numbered in its own centre (its "
                                              "longest chord's root)"})
                area["state"] = centre
            elif centre is None:
                area["too_short"] = True
            checked.add((area["state"], area["start_ms"]))
        else:
            if home is not None and home != area["state"]:
                absorbed.append({"state": area["state"], "start_ms": area["start_ms"], "end_ms": area["end_ms"],
                                 "into": home, "to_home": True,
                                 "why": why + ", and it touches no other area: numbered in the home key"})
                area["state"] = home
            checked.add((area["state"], area["start_ms"]))
        areas = _join_same(areas)
    return areas, absorbed


def _established(areas: List[dict], i: int, windows: List[dict]) -> bool:
    """Whether key area i holds its key against the area next to it in its section: its tonic chord sounds for
    AREA_TONIC_MIN_MS, or at least two chord roots carry notes that the neighbouring key lacks beyond each chord's own
    3rd. (An F11 alone in Eb major is the 5 of 5 with its A, not a turn to Bb major.) Without a neighbour it holds."""
    area = areas[i]
    section = area.get("section")
    nb = areas[i - 1] if i > 0 and areas[i - 1].get("section") == section else \
        areas[i + 1] if i + 1 < len(areas) and areas[i + 1].get("section") == section else None
    if nb is None or nb["state"] == area["state"]:
        return True
    tonic = KEYS[area["state"]][0]
    inside = [w for w in windows if _in_area(w, area) and w.get("root_pc") is not None and len(w["pcs"]) >= 3]
    if sum(w["end_ms"] - w["start_ms"] for w in inside if w["root_pc"] == tonic) >= AREA_TONIC_MIN_MS:
        return True
    nt, nm = KEYS[nb["state"]]
    scale = {(nt + s) % 12 for s in KEY_FIT_SCALE[nm]}
    foreign = {w["root_pc"] for w in inside
               if set(w["pcs"]) - {(w["root_pc"] + 3) % 12, (w["root_pc"] + 4) % 12} - scale}
    return len(foreign) >= 2


def split_returns(areas: List[dict], windows: List[dict]) -> List[dict]:
    """A key area whose parallel mode comes back for a while is cut around that return: from the end of the last window
    with the area's own 3rd to the last window with the parallel 3rd, when that stretch has no window with the area's own
    3rd, lasts RETURN_AREA_MS, and holds the tonic with the parallel 3rd for RETURN_TONIC_MS (Eb minor, then 12 s of Eb
    and Eb/G, then Eb minor again). The return is an area of the parallel key, marked return."""
    out: List[dict] = []
    for area in areas:
        tonic, mode = KEYS[area["state"]]
        own, other = ((tonic + 3) % 12, (tonic + 4) % 12) if mode == "minor" else ((tonic + 4) % 12, (tonic + 3) % 12)
        cuts: List[tuple] = []
        state = {"since": area["start_ms"], "first": None, "last": None, "tonic_ms": 0.0}

        def flush():
            if state["first"] is not None and state["last"] - state["since"] >= RETURN_AREA_MS and \
                    state["tonic_ms"] >= RETURN_TONIC_MS:
                cuts.append((state["since"], state["last"]))
            state.update(first=None, last=None, tonic_ms=0.0)
        for w in windows:
            if not _in_area(w, area) or len(w["pcs"]) < 2:
                continue
            pcs = set(w["pcs"])
            if own in pcs:
                flush()
                state["since"] = w["end_ms"]
            elif other in pcs:
                state["first"] = state["first"] or w
                state["last"] = w["end_ms"]
                if tonic in pcs:
                    state["tonic_ms"] += w["end_ms"] - w["start_ms"]
        flush()
        t = area["start_ms"]
        parallel = KEYS.index((tonic, "major" if mode == "minor" else "minor"))
        for c0, c1 in cuts:
            if c0 > t:
                out.append({**area, "start_ms": t, "end_ms": c0})
            out.append({**area, "state": parallel, "start_ms": c0, "end_ms": c1, "return": True})
            t = c1
        if t < area["end_ms"] or not cuts:
            out.append({**area, "start_ms": t, "end_ms": area["end_ms"]})
    return out


ENHARMONIC_KEYS = {(8, "minor"): "Ab minor", (3, "minor"): "D# minor", (10, "minor"): "A# minor",
                   (6, "major"): "Gb major", (1, "major"): "C# major", (11, "major"): "Cb major"}


def key_namer(home_state: Optional[int]):
    """Key names spelled the home key's way where a key has two usual names: Ab minor (not G# minor) in a flat
    session, D# minor (not Eb minor) in a sharp one. Every name is one arsenal.nashville.parse_key reads."""
    home_bias = nashville.bias_of(*KEYS[home_state]) if home_state is not None else 0

    def name(state: int) -> str:
        tonic, mode = KEYS[state]
        plain = key_name(tonic, mode)
        alt = ENHARMONIC_KEYS.get((tonic, mode))
        if alt and home_bias and nashville.parse_key(plain)["bias"] != home_bias and \
                nashville.parse_key(alt)["bias"] == home_bias:
            return alt
        return plain
    return name


def _describe_areas(areas: List[dict], frames: dict, namer=None) -> List[dict]:
    namer = namer or (lambda s: key_name(*KEYS[s]))
    out = []
    for n, a in enumerate(areas):
        k0 = int(a["start_ms"] // KEY_FRAME_MS)
        k1 = max(k0 + 1, math.ceil(a["end_ms"] / KEY_FRAME_MS))
        rows = [(frames["scores"][k], frames["r"][k]) for k in range(k0, k1) if frames["r"].get(k) is not None]
        tonic, mode = KEYS[a["state"]]
        prev = areas[n - 1] if n else None
        pause = a["start_ms"] - prev["end_ms"] if prev and prev.get("section") != a.get("section") else 0
        row = {"key": namer(a["state"]), "tonic": tonic, "mode": mode, "start_ms": a["start_ms"],
               "end_ms": a["end_ms"], "at": clock(a["start_ms"]), "until": clock(a["end_ms"]),
               "seconds": _r((a["end_ms"] - a["start_ms"]) / 1000, 1), "section": a.get("section", 0),
               "after_pause_s": _r(pause / 1000, 1) if pause else None, "too_short": bool(a.get("too_short")),
               "return": bool(a.get("return")),
               "score": None, "r": None, "runner_up": None}
        if rows:
            mean = [sum(s[k] for s, _ in rows) / len(rows) for k in range(len(KEYS))]
            row["score"] = _r(mean[a["state"]])
            row["r"] = _r(sum(r[a["state"]] for _, r in rows) / len(rows))
            other = max((k for k in range(len(KEYS)) if k != a["state"]), key=lambda k: mean[k])
            row["runner_up"] = {"key": namer(other), "score": _r(mean[other])}
        out.append(row)
    return out


# ============================================================================================== naming
def run_theory(items: List[dict], source=None, node: Optional[str] = None,
               timeout: float = 120) -> Tuple[Optional[dict], Optional[str]]:
    """One node call: Theory.detect over every item ({notes, bias}). (answer, None) or (None, why)."""
    node = node or shutil.which("node")
    if not node:
        return None, "node not found on PATH"
    request = json.dumps({"source": str(source or PIANO_JS), "items": items})
    try:
        proc = subprocess.run([node, str(BRIDGE)], input=request, capture_output=True, text=True, encoding="utf-8",
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if proc.returncode != 0:
        return None, f"node exited {proc.returncode}: {proc.stderr.strip()[-300:]}"
    try:
        answer = json.loads(proc.stdout)
    except ValueError as exc:
        return None, f"unreadable bridge answer: {exc}"
    if not answer.get("ok"):
        return None, answer.get("error") or "bridge failed"
    return answer, None


def spell_detect(info: Optional[dict], key: Optional[str]) -> Optional[dict]:
    """detect's result spelled in the key the way the page spells its label: the root as nashville reads it (a
    chromatic root keeps detect's spelling unless the key's is as plain), every other tone moved by the same letter
    distance, a bass that would need a double accidental respelled on its own. {kind, name, root, suffix, bass, upper}."""
    if not info:
        return None
    root = _sp(info.get("root"))
    out = {"kind": info["kind"], "suffix": info.get("suffix") or "", "detect_name": info["name"],
           "cost": info.get("cost"), "root": root, "bass": _sp(info.get("bass")), "upper": _sp(info.get("upper"))}

    def in_key(sp, suffix=None):
        s = nashville.spell_in_key(sp, key, suffix=suffix) if key and sp else None
        if s and (s["in_scale"] or (abs(s["acc"]) <= 1 and _sp_name((s["letter"], s["acc"])) not in ODD_NAMES)):
            return s["letter"], s["acc"]
        return sp

    if info["kind"] == "cluster":
        out["name"] = " ".join(pc_name(_sp_pc(_parse_name(n)), key) for n in info["pcNames"])
        out["root"] = None
        return out
    new_root = in_key(root, out["suffix"] if info["kind"] == "chord" else None)
    by = new_root[0] - root[0]

    def moved(sp):
        letter = (sp[0] + by) % 7
        return letter, _signed(_sp_pc(sp) - LETTER_PC[letter])

    bass = moved(out["bass"]) if out["bass"] else None
    if bass and abs(bass[1]) > 1:
        bass = in_key(out["bass"])
    upper = moved(out["upper"]) if out["upper"] else None
    if any(abs(sp[1]) > 2 for sp in (new_root, bass, upper) if sp):
        new_root, bass, upper = root, out["bass"], out["upper"]
    out.update(root=new_root, bass=bass, upper=upper)
    if info["kind"] == "note":
        out["name"] = _sp_name(new_root)
    elif info["kind"] == "interval":
        out["name"] = f"{_sp_name(new_root)}-{_sp_name(upper)}"
    else:
        out["name"] = _sp_name(new_root) + out["suffix"] + ("/" + _sp_name(bass) if bass else "")
    return out


def _reading_suffix(base: str, ext: set) -> str:
    """A base chord plus tensions as a lead sheet writes it: maj7 + 9 + #11 -> maj9#11, m7 + 13 -> m7(13)."""
    ext = set(ext)
    suffix = base
    if base in SEVENTHS and 2 in ext and base != "dim7":
        suffix = {"7": "9", "maj7": "maj9", "m7": "m9", "m7b5": "m9b5", "7sus4": "9sus4", "m(maj7)": "m(maj9)"}[base]
        ext.discard(2)
        if 9 in ext and base in ("7", "maj7", "m7"):
            suffix = {"7": "13", "maj7": "maj13", "m7": "m13"}[base]
            ext.discard(9)
        elif 5 in ext and base in ("7", "m7"):
            suffix = {"7": "11", "m7": "m11"}[base]
            ext.discard(5)
    elif base == "7" and 9 in ext:
        suffix = "13"
        ext.discard(9)
    elif base in ("", "m", "6", "m6") and 2 in ext and (9 in ext or base in ("6", "m6")):
        suffix = "m6/9" if base.startswith("m") else "6/9"
        ext.discard(2)
        ext.discard(9)
    elif base in ("", "m") and 2 in ext:
        suffix = "add9" if base == "" else "m(add9)"
        ext.discard(2)
    altered = [TENSIONS[x] for x in TENSION_ORDER if x in ext and x in ALTERED]
    natural = [TENSIONS[x] for x in TENSION_ORDER if x in ext and x not in ALTERED]
    if not altered and not natural:
        return suffix
    if suffix.endswith(")"):
        return suffix[:-1] + "," + ",".join(altered + natural) + ")"
    if suffix in ("", "m"):
        tensions = altered + natural
        return ("add" if suffix == "" else "m(add") + tensions[0] + ("" if suffix == "" else ")") + \
            (f"({','.join(tensions[1:])})" if tensions[1:] else "")
    if suffix not in ("sus2", "sus4", "dim", "aug", "6", "m6", "add9", "6/9", "m6/9"):
        return suffix + "".join(altered) + (f"({','.join(natural)})" if natural else "")
    return suffix + "(" + ",".join(TENSIONS[x] for x in TENSION_ORDER if x in ext) + ")"


def extended_readings(pcs: List[int], bass_pc: Optional[int], templates: List[dict], roots=None) -> List[dict]:
    """Every base chord plus tensions that accounts for exactly these pitch classes, cheapest first:
    [{root_pc, base, suffix, tensions, no3, no5, cost}]. A base tone may be missing only if it is the 5th (+0.4) or, over
    a root in the bass with its 5th present, the 3rd of a major-family chord (+1.2, labelled no 3rd). b9 and #9 only over
    a dominant 7th; 11 over a major 3rd only without a 7th; b13 only over a b7. The costs follow detect's templates."""
    pcset = set(pcs)
    by_suffix: Dict[str, dict] = {}
    for t in templates:
        if t["suffix"] in READING_BASES and t["suffix"] not in by_suffix:
            by_suffix[t["suffix"]] = t
    out = []
    for root in (roots if roots is not None else sorted(pcset)):
        rel = {(p - root) % 12 for p in pcset}
        if 0 not in rel:
            continue
        for base, t in by_suffix.items():
            tones = {s for s, _ in t["tones"]}
            missing = tones - rel
            third = 4 if 4 in tones else 3 if 3 in tones else None
            no5 = 7 in missing
            no3 = third is not None and third in missing
            if missing - {7, third}:
                continue
            if no3 and (base not in NO3_BASES or bass_pc != root or no5):
                continue
            if no5 and len(pcset) < 4:
                continue  # root and two more notes, one of them standing in for a missing 5th, is too thin to name
            ext = rel - tones
            if not ext <= set(TENSIONS):
                continue
            dom = 4 in tones and 10 in tones
            if (1 in ext and not dom) or (3 in ext and (not dom or no3)) or (8 in ext and 10 not in tones):
                continue
            if 5 in ext and 4 in tones and (10 in tones or 11 in tones) and not (3 in ext and 10 in tones):
                continue  # (a dominant with both 3rds, #9 and 3, may carry the 11 too: Bb13#9(11))
            cost = t["cost"] + 0.45 * len(ext) + (0.4 if no5 else 0.0) + (1.2 if no3 else 0.0)
            if bass_pc is not None and bass_pc != root:
                iv = (bass_pc - root) % 12
                cost += 0.6 if iv in tones else 1.5
            out.append({"root_pc": root, "base": base, "suffix": _reading_suffix(base, ext),
                        "tensions": [TENSIONS[x] for x in TENSION_ORDER if x in ext], "no3": no3, "no5": no5,
                        "cost": round(cost, 3)})
    out.sort(key=lambda r: (r["cost"], r["root_pc"] != bass_pc, len(r["suffix"])))
    return out


def _base_tones(templates: List[dict], suffix: str) -> Optional[set]:
    t = next((t for t in templates if t["suffix"] == suffix), None)
    return {s for s, _ in t["tones"]} if t else None


def choose_reading(pcs: List[int], bass_pc: Optional[int], info: Optional[dict], templates: List[dict],
                   held: bool = True) -> Tuple[Optional[dict], bool]:
    """(the reading to show, whether it replaces detect's name) for a set of pitch classes over a bass.

    - An unnamed set (detect's cluster) takes its cheapest reading, preferring one whose 5th sounds and whose bass is its
      root or a chord tone.
    - A chord detect already roots on the bass keeps detect's name.
    - Otherwise a reading rooted on the bass, with its 5th sounding (its triad, or root and 5th), replaces detect's name
      when the bass is held and the reading costs at most READING_MARGIN more (Bb11/Ab over an Ab triad is Abadd9(#11);
      Eb/Ab is Abmaj9 without its 3rd).
    - Failing that, when detect's bass is not one of its chord's tones, an inversion reading (the bass one of its tones,
      nothing left out) replaces it when strictly cheaper (Bmaj9/G without its F# is Eb7b13/G)."""
    if not templates or len(pcs) < 3 or bass_pc is None or not info:
        return None, False
    found = extended_readings(pcs, bass_pc, templates)
    if not found:
        return None, False
    if info["kind"] == "cluster":
        backed = [r for r in found if not r["no5"] and r["cost"] < 90]
        return (backed or found)[0], True
    if info["kind"] != "chord":
        return None, False
    root = _sp_pc(_sp(info["root"]))
    cost = info.get("cost")
    if root == bass_pc or cost is None:
        return None, False
    tones = _base_tones(templates, info.get("suffix") or "")
    foreign = tones is not None and (bass_pc - root) % 12 not in tones

    on_bass = [r for r in found if r["root_pc"] == bass_pc and not r["no5"]]
    iv = (bass_pc - root) % 12
    if tones is not None and iv in tones and iv in (3, 4, 6, 7, 8):
        # detect's bass is its own 3rd or 5th: an inversion. With its 3rd sounding (Bbmaj9/D, C13/E, Ebmaj9/Bb,
        # Bbadd9/F) it stays. A sus chord over its 5th has no quality to invert, so a plainer reading on the bass,
        # strictly cheaper, with its 3rd and at most one unaltered tension, replaces it (A9sus4/E is Em7(11)).
        if 3 in tones or 4 in tones:
            return None, False
        on_bass = [r for r in on_bass if not r["no3"] and len(r["tensions"]) <= 1
                   and not set(r["tensions"]) & {"b9", "#9", "b13"}]
        if on_bass and held and on_bass[0]["cost"] < cost:
            return on_bass[0], True
    elif on_bass and held and on_bass[0]["cost"] <= cost + READING_MARGIN:
        return on_bass[0], True
    if foreign:
        inversions = [r for r in found if r["root_pc"] not in (bass_pc, root) and not r["no5"] and not r["no3"]
                      and (bass_pc - r["root_pc"]) % 12 in (_base_tones(templates, r["base"]) or set())]
        if inversions and inversions[0]["cost"] < cost:
            return inversions[0], True
    if on_bass:
        return on_bass[0], False
    return None, False


def over_third_reading(pcs: List[int], bass_pc: Optional[int], info: Optional[dict], templates: List[dict],
                       held: bool = True) -> Optional[dict]:
    """A chord detect names over its own 3rd (Bbm9/Db, Fm11/Ab) that the same notes give more cheaply as a chord rooted
    on the held bass, its 5th sounding, with at most two unaltered tensions (Dbmaj7(13); Abmaj13 without its 3rd when
    the Fm11 has no C either). That reading, or None. Whether it is used depends on the chords around it
    (resolve_over_third): the minor chord's own root just before or after keeps detect's name (Fm, then Fm9/Ab)."""
    if not held or not templates or len(pcs) < 3 or bass_pc is None or not info or info["kind"] != "chord" or \
            info.get("cost") is None:
        return None
    root = _sp_pc(_sp(info["root"]))
    tones = _base_tones(templates, info.get("suffix") or "")
    iv = (bass_pc - root) % 12
    if tones is None or iv not in (3, 4) or iv not in tones:
        return None
    found = [r for r in extended_readings(pcs, bass_pc, templates, roots=[bass_pc])
             if not r["no5"] and not (r["no3"] and len(set(pcs)) < 4) and len(r["tensions"]) <= 2
             and not set(r["tensions"]) & {"b9", "#9", "#11", "b13"} and r["cost"] < info["cost"]]
    return found[0] if found else None


def _take_reading(w: dict, reading: dict) -> None:
    w["reading"], w["from"], w["root_pc"], w["suffix"], w["no5"] = reading, "reading", reading["root_pc"], \
        reading["suffix"], False


def resolve_over_third(windows: List[dict]) -> None:
    """Each window holding an over_third_reading takes it unless the chord detect named is around it: the nearest
    chord or two-note shape before or after it (past short windows with no chord, and past more of the same shape over
    the same bass, within CADENCE_GAP_MS) is rooted on detect's root (Fm(add9), then Fm9/Ab: the Fm goes on over its
    3rd)."""
    def same_shape(x, w):
        return x.get("over_third") is not None and x["root_pc"] == w["root_pc"] and x["bass"] is not None and \
            x["bass"] % 12 == w["bass"] % 12

    def neighbour(k, step, w):
        edge = w["start_ms"] if step < 0 else w["end_ms"]
        k += step
        while 0 <= k < len(windows):
            x = windows[k]
            gap = edge - x["end_ms"] if step < 0 else x["start_ms"] - edge
            if gap > CADENCE_GAP_MS:
                return None
            if (x["root_pc"] is None and x["end_ms"] - x["start_ms"] <= CADENCE_GAP_MS) or same_shape(x, w):
                edge = x["start_ms"] if step < 0 else x["end_ms"]
                k += step
                continue
            return x if x["root_pc"] is not None and len(x["pcs"]) >= 2 else None  # (G#-A# over G#: the G# is there)
        return None
    switch = []
    for k, w in enumerate(windows):
        if w.get("over_third") is None or w["from"] != "detect":
            continue
        if not any(x is not None and x["root_pc"] == w["root_pc"] for x in (neighbour(k, -1, w), neighbour(k, 1, w))):
            switch.append(w)
    for w in switch:
        _take_reading(w, w["over_third"])


def _analyse(w: dict, info: Optional[dict], templates: List[dict]) -> None:
    """The chord a window is analysed as, key-independent: detect's, or an extended reading (choose_reading; a chord
    over its own 3rd keeps its bass-rooted reading in over_third, for resolve_over_third). A window whose notes were
    never held together (texture line or broken chord) is not analysed as a chord: detect's root is kept only as
    implied_root. no5: detect's name leaves out its 5th."""
    w["info"], w["reading"], w["from"] = info, None, "detect" if info else None
    w["root_pc"], w["suffix"], w["implied_root"], w["over_third"], w["no5"] = None, "", None, None, False
    bass_pc = w["bass"] % 12 if w["bass"] is not None else None
    if info and info["kind"] != "cluster":
        w["root_pc"], w["suffix"] = _sp_pc(_sp(info["root"])), info.get("suffix") or ""
    if info:
        held = w["bass_share"] >= BASS_HELD_SHARE
        reading, replace = choose_reading(w["pcs"], bass_pc, info, templates, held)
        w["reading"] = reading
        if replace:
            _take_reading(w, reading)
        elif info["kind"] == "chord":
            tones = _base_tones(templates, w["suffix"])
            w["no5"] = bool(tones and 7 in tones and (w["root_pc"] + 7) % 12 not in w["pcs"])
            w["over_third"] = over_third_reading(w["pcs"], bass_pc, info, templates, held)
    _apply_texture(w)


def _apply_texture(w: dict) -> None:
    if w.get("texture", "chord") != "chord" and w["from"] is not None:
        w["implied_root"] = w["root_pc"]
        w["root_pc"], w["suffix"], w["from"] = None, "", w["texture"]


ANALYSIS_KEYS = ("info", "reading", "from", "root_pc", "suffix", "implied_root", "over_third", "no5")  # a merge keeps these


def _identity(w: dict) -> tuple:
    if w["root_pc"] is None or len(w["pcs"]) < 3:
        return ("set", tuple(w["pcs"]))
    return ("chord", w["root_pc"], w["suffix"])


def merge_built(windows: List[dict], ctx: dict) -> List[dict]:
    """A chord built note by note under one pedal (_building, window to window) is one window, named as it stands
    complete, when the complete chord keeps the root of the first window (F A C, then Eb, then G: one F11). A build that
    ends on another root (Bb, then A, then G: Gm9/Bb) keeps its windows, because the first chord really sounded."""
    out: List[dict] = []
    i = 0
    while i < len(windows):
        j, best = i, i
        while j + 1 < len(windows) and _building(windows[j], windows[j + 1], ctx):
            j += 1
            if windows[i]["root_pc"] is not None and windows[j]["root_pc"] == windows[i]["root_pc"]:
                best = j
        if best == i:
            out.append(windows[i])
            i += 1
            continue
        merged = windows[i]
        for w in windows[i + 1:best + 1]:
            merged = _combine(merged, w)
        last = windows[best]
        merged["tail"], merged["tail_share"] = [last["start_ms"], last["end_ms"]], last["share"]
        _facts(merged, ctx)
        for k in ANALYSIS_KEYS:
            merged[k] = last[k]
        merged["built"] = best - i + 1
        out.append(merged)
        i = best + 1
    return out


def merge_same(windows: List[dict], ctx: dict) -> List[dict]:
    """Touching windows analysed as the same chord (the bass may move) become one window, when the merged window keeps
    the longer part's chord set and bass pitch class (so the longer part's name still holds)."""
    out: List[dict] = []
    for w in windows:
        prev = out[-1] if out else None
        if prev and prev["end_ms"] == w["start_ms"] and prev["info"] and w["info"] and _identity(prev) == _identity(w):
            merged = _combine(prev, w)
            _facts(merged, ctx)
            longer = prev if prev["end_ms"] - prev["start_ms"] >= w["end_ms"] - w["start_ms"] else w
            same_bass = (merged["bass"] is None) == (longer["bass"] is None) and \
                (merged["bass"] is None or merged["bass"] % 12 == longer["bass"] % 12)
            if merged["pcs"] == longer["pcs"] and same_bass and merged["texture"] == longer["texture"]:
                for k in ANALYSIS_KEYS:
                    merged[k] = longer[k]
                out[-1] = merged
                continue
        out.append(w)
    return out


# ======================================================================================= classification
def _third(rel: set) -> Optional[str]:
    return "major" if 4 in rel else "minor" if 3 in rel else None


def classify(pcs: List[int], root_pc: Optional[int], key: dict, next_root_pc: Optional[int] = None) -> dict:
    """{class, detail, fits[, target]} for a chord's pitch classes in a key ({key, tonic, mode}). Secondary dominants
    need a major 3rd on a root a 5th above a diatonic chord, and either a b7 or the next chord landing on that target."""
    tonic, mode = key["tonic"], key["mode"]
    rel = {(p - tonic) % 12 for p in pcs}
    fits = [name for name, scale in SCALES.items() if rel <= scale]
    parallel = parallel_key(key["key"])
    home_scales = ("major",) if mode == "major" else ("natural minor", "harmonic minor", "melodic minor")
    if any(s in fits for s in home_scales):
        return {"class": "diatonic", "detail": f"in {key['key']}", "fits": fits}
    rrel = {(p - root_pc) % 12 for p in pcs} if root_pc is not None else set()
    if root_pc is not None and _third(rrel) == "major" and 11 not in rrel:
        target = (root_pc - tonic - 7) % 12
        if target in SECONDARY_TARGETS[mode] and target != 0:
            label = SECONDARY_TARGETS[mode][target]
            lands = next_root_pc is not None and (next_root_pc - tonic) % 12 == target
            if 10 in rrel or lands:
                return {"class": "secondary dominant", "fits": fits, "target": label,
                        "detail": f"5 of {label}" + (", and it lands there" if lands else ", not followed by its target")}
    borrowed_from = ("natural minor", "harmonic minor") if mode == "major" else ("major",)
    if any(s in fits for s in borrowed_from):
        return {"class": "borrowed", "detail": f"borrowed from {parallel}", "fits": fits}
    tonic_name = key["key"].split(" ")[0]
    for mode_name in (("Mixolydian", "Lydian", "Dorian", "Phrygian") if mode == "major" else ("Dorian", "Phrygian")):
        if mode_name in fits:
            detail = f"{tonic_name} {mode_name} colour ({MODAL_COLOUR[mode_name]})"
            if root_pc is not None:
                core = {root_pc} | {(root_pc + i) % 12 for i in (3, 4, 7) if (root_pc + i) % 12 in pcs}
                if len(core) >= 2 and any({(p - tonic) % 12 for p in core} <= SCALES[s] for s in borrowed_from):
                    detail += f"; its triad is borrowed from {parallel}"
            return {"class": "modal", "detail": detail, "mode": mode_name, "fits": fits}
    return {"class": "chromatic", "detail": f"in neither {key['key']} nor {parallel}", "fits": fits}


# ============================================================================================== analysis
def analyze(events, theory_source=None, node: Optional[str] = None, end_ms: Optional[float] = None) -> dict:
    """The whole engine over one session's events. Pure apart from one node call (the page's Theory.detect). end_ms:
    when notes still sounding at the end of the log stop (an open session's 'now'); by default the last event."""
    NUMBERING.update(fallbacks=0, errors=0)
    evs, impossible = plausible_events(events)
    evs.sort(key=lambda e: e["t_ms"])
    snd = sounding(evs, end_ms)
    ctx = _context(snd, evs)
    seg = harmonic_windows(snd)
    windows = seg["windows"]
    raw_windows = len(windows)
    for w in windows:
        _facts(w, ctx)
    windows = merge_bass_walks(merge_growth(windows, ctx), ctx)
    sections = sections_of(snd) or [[0, snd["duration_ms"]]]
    sound_spans = _union([(n["on_ms"], n["end_ms"]) for n in snd["notes"]])
    frames = key_frames(snd, sections)
    provisional: List[dict] = []
    for si, (s0, s1) in enumerate(sections):
        k0 = int(s0 // KEY_FRAME_MS)
        k1 = max(k0 + 1, math.ceil(s1 / KEY_FRAME_MS))
        path = key_path([frames["scores"].get(k) or [0.0] * len(KEYS) for k in range(k0, k1)])
        provisional += _areas_from_path(path, windows, s0, s1, k0, si)
    for w in windows:
        area = _area_at(provisional, (w["start_ms"] + w["end_ms"]) / 2)
        drops = ornaments(w, ctx) if len(w["pcs"]) >= 3 else set()
        if area and len(w["pcs"]) >= 3:
            tonic, mode = KEYS[area["state"]]
            drops |= passing_tones(w, ctx, {(tonic + i) % 12 for i in KEY_FIT_SCALE[mode]})
        if drops:
            w["dropped"] = sorted(drops)
            _facts(w, ctx)

    items = []
    for w in windows:
        area = _area_at(provisional, (w["start_ms"] + w["end_ms"]) / 2)
        items.append({"notes": w["detect_notes"], "bias": nashville.bias_of(*KEYS[area["state"]]) if area else 0})
    answer, naming_error = run_theory(items, theory_source, node) if items else ({"templates": [], "results": []}, None)
    templates = answer["templates"] if answer else []
    for w, info in zip(windows, answer["results"] if answer else [None] * len(windows)):
        _analyse(w, info, templates)
    resolve_over_third(windows)
    grown_windows = len(windows)
    windows = merge_same(merge_built(windows, ctx), ctx)

    heard_pc, _ = _heard(snd["notes"])
    areas_raw, absorbed = consolidate_areas(provisional, windows, heard_pc)
    areas_raw = split_returns(areas_raw, windows)
    skip = [(a["start_ms"], a["end_ms"]) for a in absorbed if a.get("to_home")]
    home_state = _home(areas_raw, windows, skip)
    namer = key_namer(home_state)
    areas = _describe_areas(areas_raw, frames, namer)
    home = namer(home_state) if home_state is not None else None
    home_area = {"key": home, "tonic": KEYS[home_state][0], "mode": KEYS[home_state][1]} if home else None
    chord_ms = _chord_time(areas_raw, windows, skip)
    total_chord_ms = sum(chord_ms.values()) or 1
    for a in areas:
        a["relation"] = _relation(a, home_area)
    time_by_key = {namer(s): {"seconds": _r(ms / 1000, 1), "share": _r(ms / total_chord_ms, 2)}
                   for s, ms in sorted(chord_ms.items(), key=lambda kv: -kv[1])}

    rows = []
    for idx, w in enumerate(windows):
        area = _area_at(areas, (w["start_ms"] + w["end_ms"]) / 2)
        rows.append(_row(idx, w, area, home_area, windows[idx + 1] if idx + 1 < len(windows) else None))
    findings = _findings(rows, areas, ctx)
    pedal_stats = _pedal_stats(snd, rows)
    for row in rows:
        for k in [k for k in row if k.startswith("_")]:
            row.pop(k)
    live_named = sum(1 for e in ctx["chords"] if e.get("chord"))
    est = estimate_key([sum(b - a for a, b in iv) for iv in heard_pc])
    held_chords = sum(r["seconds"] for r in rows if r["kind"] == "chord" or r["analysed_from"] == "reading")
    return {
        "api": API,
        "duration_s": _r(snd["duration_ms"] / 1000),
        "notes": len(snd["notes"]),
        "sound_ends": "logged" if snd["explicit_ends"] else "inferred from releases and pedal lifts",
        "held_at_end": snd["held_at_end"],
        "impossible_events": impossible,
        "naming": {"source": "piano.js THEORY block via node (arsenal/practice_theory.mjs)" if answer
                   else f"unavailable ({naming_error})",
                   "readings": "extended readings over detect's own templates, labelled (reading)",
                   "numbered_from_parts": NUMBERING["fallbacks"], "unnumbered": NUMBERING["errors"]},
        "constants": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, tuple))
                      and k not in ("LETTER_PC", "TENSION_ORDER", "KK_MAJOR", "KK_MINOR")},
        "home_key": home,
        "chord_seconds": _r(held_chords, 1),
        "sections": [{"start_ms": s0, "end_ms": s1, "at": clock(s0), "until": clock(s1),
                      "pause_before_s": _r((s0 - sections[k - 1][1]) / 1000, 1) if k else None,
                      # nothing struck before this section, but notes still sounding (a held key, a pedal left down)
                      "sounding_before_s": _r(_overlap(sound_spans, sections[k - 1][1], s0) / 1000, 1) if k else None}
                     for k, (s0, s1) in enumerate(sections)],
        "sounding_after_s": _r(_overlap(sound_spans, sections[-1][1], snd["duration_ms"]) / 1000, 1),  # after the last
        # section ends (SECTION_IDLE_MS past its last attack), notes still sounding
        "keys": {"areas": areas, "home": home, "chord_time_by_key": time_by_key,
                 "absorbed": [{"key": namer(a["state"]), "at": clock(a["start_ms"]), "until": clock(a["end_ms"]),
                               "start_ms": a["start_ms"], "end_ms": a["end_ms"], "into": namer(a["into"]),
                               "fragment": bool(a.get("fragment")), "why": a["why"]} for a in absorbed],
                 "estimate": est and {"key": est["best"]["key"], "r": est["best"]["r"],
                                      "runner_up": est["runner_up"]["key"], "runner_up_r": est["runner_up"]["r"],
                                      "weights": "heard seconds per pitch class"}},
        "windows": rows,
        "segmentation": {"live_chord_events": live_named, "windows_before_merge": raw_windows,
                         "after_growth_merge": grown_windows,
                         "windows": len(rows), "live_events_per_window": _r(live_named / len(rows), 1) if rows else None,
                         "lines": sum(1 for r in rows if r["kind"] == "line"),
                         "broken_chords": sum(1 for r in rows if r["kind"] == "broken chord"),
                         "transients_dropped": seg["transients"]["count"],
                         "transient_seconds": _r(seg["transients"]["ms"] / 1000, 2)},
        "findings": findings,
        "pedal": pedal_stats,
    }


def _relation(area: dict, home: Optional[dict]) -> Optional[str]:
    """How a key area sits against the home key: 'home key', 'parallel minor', or its tonic's number there ('5')."""
    if not home:
        return None
    if area["key"] == home["key"]:
        return "home key"
    if area["tonic"] == home["tonic"]:
        return f"parallel {area['mode']} of {home['key']}"
    tonic = area["key"].split(" ")[0] + ("m" if area["mode"] == "minor" else "")
    if (area["tonic"] - home["tonic"]) % 12 == (9 if home["mode"] == "major" else 3) and area["mode"] != home["mode"]:
        return f"relative {area['mode']} of {home['key']}"
    got = _number(tonic, home["key"])
    return f"{got} of {home['key']}" if got else None


NUMBERING = {"fallbacks": 0, "errors": 0}  # how often arsenal.nashville could not number a name directly (per analysis)


def _number(name: Optional[str], key: Optional[str], kind: Optional[str] = None) -> Optional[str]:
    """A name's number in a key by arsenal.nashville. If nashville fails on a slash chord or an interval (it is shared
    code another build may be changing), the number is put together from its parts, each numbered on its own: the
    chord without its bass, then the bass (or the interval's top note) as a note."""
    if not name or not key:
        return None
    kind = kind if kind in ("note", "interval") else None
    try:
        got = nashville.nashville_from_name(name, key, kind=kind)
        return got["text"] if got else None
    except Exception:  # noqa: BLE001 -- any failure inside the shared numberer falls back to the parts
        NUMBERING["fallbacks"] += 1
    try:
        if kind == "interval" or ("-" in name and "/" not in name):
            lo, hi = name.split("-", 1)
            parts = [nashville.nashville_from_name(lo, key, kind="note"),
                     nashville.nashville_from_name(hi, key, kind="note")]
            return "-".join(p["text"] for p in parts) if all(parts) else None
        head, _, bass = name.partition("/")
        top = nashville.nashville_from_name(head, key, kind=kind)
        low = nashville.nashville_from_name(bass, key, kind="note") if bass else None
        if not top or (bass and not low):
            return None
        return top["text"] + (f"/{low['text']}" if low else "")
    except Exception:  # noqa: BLE001
        NUMBERING["errors"] += 1
        return None


NON_CHORD_CLASSES = ("diatonic", "note", None, "line", "broken chord", "bass line",  # classes not 'outside the key'
                     "passing bass")


def chord_marks(pcs: List[int], root_pc: Optional[int], suffix: str, reading: Optional[dict] = None,
                no5: bool = False) -> List[str]:
    """What a chord name leaves unsaid about its notes: 'no3' when a major or minor chord's 3rd is not sounding, 'no5'
    for a reading (or, with no5, detect's name) without its 5th."""
    if root_pc is None:
        return []
    marks = []
    rel = {(p - root_pc) % 12 for p in pcs}
    s = suffix or ""
    if (reading and reading.get("no3")) or ("sus" not in s and s != "5" and not s.startswith("dim")
                                             and 3 not in rel and 4 not in rel and len(rel) >= 3):
        marks.append("no3")
    if (reading and reading.get("no5")) or (no5 and not reading):
        marks.append("no5")
    return marks


def _run_scale(w: dict, key: Optional[str]) -> Optional[str]:
    """'Eb minor run' for a line of at least four different notes that all sit in its key area's scale (or its harmonic
    or melodic minor); None otherwise."""
    notes = w["line"]["notes"]
    pcs = {n % 12 for n in notes}
    if not key or len(pcs) < 4 or not pcs <= key_scale(key, wide_minor=True):
        return None
    return f"{key} run"


def _line_text(notes: List[int], key: Optional[str], limit: int = 8) -> str:
    names = [midi_name(n, key) for n in notes[:limit]]
    return " ".join(names) + (" ..." if len(notes) > limit else "")


def _light(w: dict, pc: int) -> bool:
    """A pitch class sounding too little to define a chord: under DEFINING_SOUND_MS of sound, or a soft brush (struck
    once, its key down under DEFINING_SOUND_MS while only the pedal rings it on, at most CRUSH_VEL_RATIO of the window's
    mean velocity)."""
    if (w.get("sound_ms") or [math.inf] * 12)[pc] < DEFINING_SOUND_MS:
        return True
    vel, mean = (w.get("pc_vel") or [None] * 12)[pc], (w.get("touch") or {}).get("vel_mean")
    return (w.get("attacks") or [2] * 12)[pc] == 1 and (w.get("key_ms") or [math.inf] * 12)[pc] < DEFINING_SOUND_MS \
        and vel is not None and bool(mean) and vel <= CRUSH_VEL_RATIO * mean


def _approach_bass(w: dict, nxt: Optional[dict], area: Optional[dict]) -> Optional[int]:
    """The next bass note (MIDI) when a short window's low bass is an approach note to it: the window under
    WALK_STEP_MAX_MS, its bass struck once, outside the key and not the 3rd, 5th or 7th of the chord named (A7/C# is a
    secondary dominant over its 3rd, not an approach) while every note above it is in the key, and the next window,
    straight after, on a low bass a half or whole step away (G1 between Db2 and F1 in Db major). Else None."""
    if not area or not nxt or w["bass"] is None or not w.get("low_bass") or w.get("bass_onsets") != 1 or \
            w["end_ms"] - w["start_ms"] >= WALK_STEP_MAX_MS or nxt["bass"] is None or not nxt.get("low_bass") or \
            nxt["start_ms"] - w["end_ms"] > CADENCE_GAP_MS or not 1 <= abs(nxt["bass"] - w["bass"]) <= 2:
        return None
    if w.get("root_pc") is not None and (w["bass"] - w["root_pc"]) % 12 in (3, 4, 6, 7, 8, 10, 11):
        return None
    scale = key_scale(area["key"], wide_minor=True)
    if w["bass"] % 12 in scale or any(pc not in scale for pc in w["pcs"] if pc != w["bass"] % 12):
        return None
    return nxt["bass"]


def _row(idx: int, w: dict, area: Optional[dict], home_area: Optional[dict], nxt: Optional[dict]) -> dict:
    key = area["key"] if area else None
    info, pcs, root_pc = w["info"], w["pcs"], w["root_pc"]
    texture = w.get("texture", "chord")
    spelled = spell_detect(info, key)
    bass_pc = w["bass"] % 12 if w["bass"] is not None else None
    reading = None
    if w["reading"]:
        r = w["reading"]
        name = pc_name(r["root_pc"], key) + r["suffix"] + (f"/{pc_name(bass_pc, key)}" if bass_pc not in (None, r["root_pc"])
                                                           else "")
        marks = [m for m, on in (("no 3rd", r["no3"]), ("no 5th", r["no5"])) if on]
        reading = {"name": name, "text": f"{name} ({', '.join(marks + ['reading'])})", "suffix": r["suffix"],
                   "tensions": r["tensions"], "no3": r["no3"], "no5": r["no5"], "cost": r["cost"],
                   "number": _number(name, key)}
    if spelled and spelled["kind"] == "cluster":
        display = reading["text"] if reading else f"{spelled['name']} (no chord name)"
    elif spelled and spelled["kind"] == "note":  # one pitch class: a note or its octaves, not a triad on it
        display = spelled["name"] + (" (octaves)" if len(set(w["detect_notes"])) > 1 else " (one note)")
    else:
        display = spelled["name"] if spelled else None
    detect_number = _number(spelled["name"], key, spelled["kind"]) if spelled and spelled["kind"] != "cluster" else None
    implied = None
    if texture != "chord" and w["from"] == texture:
        implied = display if not (reading and w["reading"] and (spelled or {}).get("kind") == "cluster") else reading["name"]
        if texture == "line":
            display = f"{_run_scale(w, key) or 'line'} {_line_text(w['line']['notes'], key)}"
        elif texture == "bass line":
            bl = w["bass_line"]
            display = (f"bass line {_line_text(bl['notes'], key)} under "
                       f"{'-'.join(pc_name(pc, key) for pc in bl['upper'])}")
        else:
            display = f"broken chord ({implied})" if implied else "broken chord"
    analysed = reading["name"] if w["from"] == "reading" else (
        spelled["name"] if spelled and spelled["kind"] != "cluster" and w["from"] == "detect" else None)
    number = reading["number"] if w["from"] == "reading" else (detect_number if w["from"] == "detect" else None)
    marks = chord_marks(pcs, root_pc, w["suffix"], w["reading"] if w["from"] == "reading" else None,
                        bool(w.get("no5")) and w["from"] == "detect") if analysed else []
    label = None
    if analysed:
        split = re.fullmatch(r"(.+)(/[A-G][#b]*)", analysed)  # the bass after the last slash (not the /9 of a 6/9)
        head, bass_name = (split.group(1), split.group(2)) if split else (analysed, "")
        label = head + "".join(f"({m})" for m in marks) + bass_name  # Gm(add9,11)(no5)/A, Gb6/9(no5)/Bb
    third = _third({(p - root_pc) % 12 for p in pcs}) if root_pc is not None else None
    next_root = nxt["root_pc"] if nxt and nxt["start_ms"] - w["end_ms"] <= CADENCE_GAP_MS and len(nxt["pcs"]) >= 3 \
        and nxt.get("texture", "chord") == "chord" else None  # a secondary dominant lands only on a chord
    bass_pc_ = w["bass"] % 12 if w["bass"] is not None else None
    light = sorted(pc for pc in pcs if pc != bass_pc_ and _light(w, pc))
    solid = [pc for pc in pcs if pc not in light]
    approach = _approach_bass(w, nxt, area)
    if texture == "bass line":
        cls = {"class": texture, "detail": "a bass line moving under held notes, not one chord", "fits": []}
    elif texture != "chord" and len(pcs) >= 3:
        cls = {"class": texture, "detail": "notes one or two at a time, never held together as a chord", "fits": []}
    elif area and len(pcs) >= 2:
        cls = classify(pcs, root_pc, area, next_root)
        if cls["class"] != "diatonic" and light and len(solid) >= 3:
            cls = classify(solid, root_pc, area, next_root)  # a note sounding a moment cannot take a chord outside the key
        if cls["class"] != "diatonic" and approach:
            cls = {"class": "passing bass", "fits": cls["fits"],
                   "detail": f"{midi_name(w['bass'], key)} in the bass is an approach note stepping to "
                             f"{midi_name(approach, key)}; the notes above it are in {key}"}
    else:
        cls = {"class": "note" if pcs else None, "detail": "", "fits": []}
    t = w["touch"]
    low = w.get("low_bass", True)
    if not low:
        motion = "figure"
    elif texture == "bass line":
        motion = "bass line"
    else:
        motion = "held" if w["bass_share"] >= BASS_HELD_SHARE else "moving"
    row = {
        "i": idx, "start_ms": w["start_ms"], "end_ms": w["end_ms"], "at": clock(w["start_ms"]),
        "seconds": _r((w["end_ms"] - w["start_ms"]) / 1000, 2), "heard_s": _r(w["heard_ms"] / 1000, 2),
        "merged_windows": w["merged"],
        "name": display, "analysed_as": analysed, "label": label, "marks": marks, "analysed_from": w["from"],
        "number": number,
        "detect": spelled and {"name": spelled["detect_name"], "kind": spelled["kind"], "cost": spelled["cost"],
                               "in_key": spelled["name"], "number": detect_number},
        "reading": reading, "implied": implied,
        "root": pc_name(root_pc, key) if root_pc is not None else None, "suffix": w["suffix"], "third": third,
        "kind": texture if texture != "chord" and w["from"] == texture else (spelled["kind"] if spelled else None),
        "texture": texture, "together_share": _r(w.get("together_share"), 2),
        "pcs": [pc_name(p, key) for p in sorted(pcs, key=lambda p: (p - (root_pc or 0)) % 12)],
        "passing": [[pc_name(pc, key), _r(w["share"][pc], 2)] for pc in range(12)
                    if pc not in pcs and PASSING_MIN_SHARE <= w["share"][pc] < CHORD_SHARE],
        "chromatic_passing": [pc_name(pc, key) for pc in w.get("dropped") or () if pc not in pcs],
        "bass": {"note": midi_name(w["bass"], key), "share": _r(w["bass_share"], 2), "low": low, "motion": motion,
                 "figure": [[midi_name(n, key), _r(ms / 1000, 2)] for n, ms in w["figure"]]},
        "key": key, "home": key == home_area["key"] if key and home_area else None,
        "class": cls["class"], "class_detail": cls.get("detail"), "fits": cls.get("fits"),
        "voicing": {"distinct_notes": t["distinct_notes"], "max_polyphony": t["max_polyphony"],
                    "lowest": midi_name(t["lowest"], key), "highest": midi_name(t["highest"], key),
                    "spread": t["spread"], "register": midi_name(t["register"], key), "onsets": t["onsets"],
                    "vel_mean": t["vel_mean"], "vel_min": t["vel_min"], "vel_max": t["vel_max"],
                    "pedal_share": t["pedal_share"]},
        "detect_notes": w["detect_notes"], "live": w["live"],
        "struck_together": w.get("strike_pcs", 0), "light_notes": [pc_name(pc, key) for pc in light],
        "bass_line": w.get("bass_line") and {"notes": [midi_name(n, key) for n in w["bass_line"]["notes"]],
                                             "under": [pc_name(pc, key) for pc in w["bass_line"]["upper"]]},
        "_pcs": pcs, "_root_pc": root_pc, "_area": area, "_bass_pc": bass_pc, "_bass": w["bass"], "_low_bass": low,
        "_upper": set(w.get("upper_pcs") or ()), "_strike": w.get("strike_pcs", 0),
    }
    if cls.get("target"):
        row["target"] = cls["target"]
    if key and home_area and key != home_area["key"] and len(pcs) >= 2 and texture == "chord":
        hkey = home_area["key"]
        home_cls = classify(pcs, root_pc, home_area, next_root)
        if home_cls["class"] != "diatonic" and light and len(solid) >= 3:
            home_cls = classify(solid, root_pc, home_area, next_root)
        if home_cls["class"] != "diatonic" and _approach_bass(w, nxt, home_area):
            home_cls = {"class": "passing bass", "detail": f"an approach note in the bass, the notes above it in {hkey}"}
        if w["from"] == "reading":
            r = w["reading"]
            home_name = pc_name(r["root_pc"], hkey) + r["suffix"] + (
                f"/{pc_name(bass_pc, hkey)}" if bass_pc not in (None, r["root_pc"]) else "")
            home_kind = "chord"
        else:
            home_spelled = spell_detect(info, hkey)
            home_name = home_spelled["name"] if home_spelled and home_spelled["kind"] != "cluster" else None
            home_kind = home_spelled["kind"] if home_spelled else None
        row["in_home_key"] = {"key": hkey, "name": home_name, "number": _number(home_name, hkey, home_kind),
                              "class": home_cls["class"], "detail": home_cls["detail"]}
    return row


def _pedal_stats(snd: dict, windows: List[dict]) -> dict:
    duration = snd["duration_ms"] or 1
    spans = snd["pedal"]
    down = sum(p["up_ms"] - p["down_ms"] for p in spans)
    lifts = sorted(p["up_ms"] for p in spans)
    starts = sorted(w["start_ms"] for w in windows if w["start_ms"] > 0)
    with_lift = sum(1 for s in starts
                    if bisect_left(lifts, s + PEDAL_NEAR_MS[0]) < bisect_right(lifts, s + PEDAL_NEAR_MS[1]))
    at_change = sum(1 for t in lifts
                    if bisect_left(starts, t - PEDAL_NEAR_MS[1]) < bisect_right(starts, t - PEDAL_NEAR_MS[0]))
    return {"percent_down": _r(100 * down / duration, 1), "presses": len(spans),
            "mean_down_s": _r(down / len(spans) / 1000, 2) if spans else None,
            "harmony_changes_with_a_lift": _r(with_lift / len(starts), 2) if starts else None,
            "lifts_at_a_harmony_change": _r(at_change / len(lifts), 2) if lifts else None}


# ============================================================================================== findings
def _rel(w: dict, pc: Optional[int]) -> Optional[int]:
    return None if pc is None or not w["_area"] else (pc - w["_area"]["tonic"]) % 12


def _moment(w: dict, **extra) -> dict:
    out = {"at": w["at"], "start_ms": w["start_ms"], "seconds": w["seconds"], "chord": w["name"],
           "analysed_as": w["analysed_as"], "label": w["label"], "number": w["number"], "key": w["key"]}
    out.update(extra)
    return out


ADDED_ORDER = {0: 0, 4: 1, 3: 1, 7: 2, 10: 3, 11: 3, 1: 4, 2: 4, 5: 5, 6: 5, 8: 6, 9: 6}


def _chordal(w: dict) -> bool:
    """Three or more pitch classes, or a root with its 5th: shapes that can depart in a cadence."""
    if w["_root_pc"] is None:
        return False
    rr = {(p - w["_root_pc"]) % 12 for p in w["_pcs"]}
    return len(rr) >= 3 or rr == {0, 7}


def _bass_degree(w: dict) -> Optional[str]:
    if w["_bass_pc"] is None or not w["key"]:
        return None
    return _degree(w["_bass_pc"], w["key"])


def _cadence(ws: List[dict], n: int) -> Optional[dict]:
    """The cadence (if any) from ws[n-1] into ws[n], judged on the bass as well as the roots:
    - 5 -> 1 (authentic): a root-position 5 (its bass on 5) moving to 1 with the bass on 1; 5sus -> 1 the same without
      the 3rd; 2 -> 5 -> 1 when a 2 chord comes first.
    - 5 over a 1 pedal -> 1: the 5 chord over the home note in the bass, resolving above it.
    - 4 -> 1 (plagal), 4m -> 1 (minor plagal), b7 -> 1, b6 -> b7 -> 1: the bass moves and arrives on 1.
    - 5 -> 6m (deceptive): a root-position 5 moving to the 6 chord, or to anything over the 6 in the bass.
    A two-note shape never arrives, and a pair over the same bass is no cadence (except the pedal form). A short moment
    with no chord over the arrival's own bass (its notes still unfolding) between the two is passed over."""
    a, b = ws[n - 1], ws[n]
    lead = n - 1
    if a["_root_pc"] is None and n >= 2 and a["end_ms"] - a["start_ms"] <= CADENCE_GAP_MS and \
            a["_bass_pc"] is not None and a["_bass_pc"] == b["_bass_pc"]:
        lead = n - 2
        a = ws[lead]
    area = a["_area"]
    if not area or b["_area"] is not area or b["start_ms"] - a["end_ms"] > CADENCE_GAP_MS:
        return None
    if a["_root_pc"] is None or b["_root_pc"] is None or not _chordal(a) or len(set(b["_pcs"])) < 3:
        return None
    if b["end_ms"] - b["start_ms"] < CADENCE_ARRIVAL_MS or a["_bass_pc"] is None or b["_bass_pc"] is None:
        return None
    tonic = area["tonic"]
    arel, brel = _rel(a, a["_root_pc"]), _rel(b, b["_root_pc"])
    bass_a, bass_b = (a["_bass_pc"] - tonic) % 12, (b["_bass_pc"] - tonic) % 12
    kind, chain = None, [a, b]
    names: Dict[int, tuple] = {}  # chain position -> (name, number) shown instead of the window's own label
    prev = ws[lead - 1] if lead >= 1 else None
    prev_ok = prev is not None and prev["_root_pc"] is not None and prev["_area"] is area and \
        a["start_ms"] - prev["end_ms"] <= CADENCE_GAP_MS and len(set(prev["_pcs"])) >= 3
    apcs = {(p - tonic) % 12 for p in a["_pcs"]}
    bpcs = {(p - tonic) % 12 for p in b["_pcs"]}
    six = 9 if area["mode"] == "major" else 8
    six_third = "minor" if area["mode"] == "major" else "major"
    nxt = ws[n + 1] if n + 1 < len(ws) else None
    if arel == 7 and brel == 0 and bass_b == 0:
        if bass_a == 7:
            kind = "5 -> 1 (authentic)" if a["third"] else "5sus -> 1 (suspended dominant)"
            if prev_ok and _rel(prev, prev["_root_pc"]) == 2:
                kind, chain = kind.replace("5", "2 -> 5", 1), [prev, a, b]
        elif bass_a == 0:
            kind = "5 over a 1 pedal -> 1"
    elif brel == 0 and bass_a == 0 and bass_b == 0 and {7, 11, 2} <= apcs and not {3, 4} & apcs and \
            11 not in bpcs and b["third"] and (4 if area["mode"] == "major" else 3) in bpcs:
        # the 5 chord's notes (Bb D F) over the home note in the bass, named from the bass (Ebmaj9 without its 3rd),
        # resolving above it: D to Eb, F to G
        kind = "5 over a 1 pedal -> 1"
        five = f"{pc_name((tonic + 7) % 12, a['key'])}{'7' if 5 in apcs else ''}/{pc_name(tonic, a['key'])}"
        names[0] = (five, _number(five, a["key"]))
    elif arel == 7 and bass_a == 7 and bass_b == six and brel == bass_b and b["third"] == six_third:
        kind = "5 -> 6m (deceptive)" if area["mode"] == "major" else "5 -> b6 (deceptive)"
    elif arel == 7 and bass_a == 7 and a["third"] and bass_b == six and brel == six and b["third"] is None and \
            nxt is not None and nxt["_area"] is area and nxt["start_ms"] - b["end_ms"] <= CADENCE_GAP_MS and \
            nxt["_root_pc"] == b["_root_pc"] and nxt["_bass_pc"] == b["_bass_pc"] and nxt["third"] == six_third:
        kind = "5 -> 6m (deceptive)" if area["mode"] == "major" else "5 -> b6 (deceptive)"  # through a sus on 6
        chain = [a, b, nxt]
    if kind and "deceptive" in kind:
        k = lead - 1  # a 6m -> 5 -> 6m neighbour motion never expected home: no deceptive cadence
        while k >= 0 and ws[k]["_root_pc"] == a["_root_pc"] and ws[k]["_area"] is area:
            k -= 1
        if k >= 0 and ws[k]["_area"] is area and ws[k]["_root_pc"] == b["_root_pc"] and \
                ws[k]["third"] == six_third and ws[k + 1]["start_ms"] - ws[k]["end_ms"] <= CADENCE_GAP_MS:
            return None
    elif brel == 0 and bass_b == 0 and bass_a != 0:
        if arel == 5:
            kind = "4m -> 1 (minor plagal)" if a["third"] == "minor" else "4 -> 1 (plagal)"
        elif arel == 10:
            if prev_ok and _rel(prev, prev["_root_pc"]) == 8:
                kind, chain = "b6 -> b7 -> 1 (Aeolian)", [prev, a, b]
            else:
                kind = "b7 -> 1"
    if not kind:
        return None
    k = lead - 1  # the chord before the move (past repeats of its first chord), for the learned-progression check
    while k >= 0 and ws[k]["_root_pc"] == a["_root_pc"] and ws[k]["_area"] is area:
        k -= 1
    before = ws[k] if k >= 0 and ws[k]["_area"] is area and ws[k]["_root_pc"] is not None and \
        ws[k + 1]["start_ms"] - ws[k]["end_ms"] <= CADENCE_GAP_MS else None
    return {"at": chain[0]["at"], "start_ms": chain[0]["start_ms"], "kind": kind, "key": b["key"],
            "end_ms": chain[-1]["end_ms"], "_before": _rel(before, before["_root_pc"]) if before else None,
            "chords": [names[i][0] if i in names else (c["label"] or c["analysed_as"] or c["name"])
                       for i, c in enumerate(chain)],
            "numbers": [names[i][1] if i in names else c["number"] for i, c in enumerate(chain)],
            "bass": [c["bass"]["note"] for c in chain]}


def _onsets_between(ctx: dict, a: float, b: float) -> List[dict]:
    lo, hi = bisect_left(ctx["on_keys"], a), bisect_left(ctx["on_keys"], b)
    return [ctx["notes"][i] for _, i in ctx["on_times"][lo:hi]]


def _suspension(a: dict, b: dict, ctx: dict) -> Optional[dict]:
    """A sus chord followed by the same root with its 3rd: counted only when the sus chord was complete and held
    SUS_HOLD_MS, and the 3rd came after a pause of SUS_HOLD_MS (not as the next note of an upward roll). It resolves
    when the 4th (or 2nd) leaves; otherwise the 3rd is added and the sus note kept."""
    ar = a["_root_pc"]
    arr = {(p - ar) % 12 for p in a["_pcs"]}
    brr = {(p - ar) % 12 for p in b["_pcs"]}
    no3_reading = a["analysed_from"] == "reading" and a["reading"]["no3"]
    if a["third"] is not None or not (5 in arr or 2 in arr) or not b["third"] or no3_reading:
        return None
    third_pc = (ar + (4 if b["third"] == "major" else 3)) % 12
    first: Dict[int, float] = {}  # when each of the sus chord's pitch classes arrived (a note ringing on from before
    for n in _onsets_between(ctx, a["start_ms"] - ctx["longest"] - 1, a["end_ms"]):  # counts only if it keeps sounding)
        pc = n["note"] % 12
        if pc not in a["_pcs"] or n["end_ms"] <= a["start_ms"]:
            continue
        if n["on_ms"] >= a["start_ms"] or n["end_ms"] >= min(a["end_ms"], a["start_ms"] + SUS_HOLD_MS):
            first[pc] = min(first.get(pc, math.inf), max(n["on_ms"], a["start_ms"]))
    complete_at = max(first.values()) if first else a["start_ms"]  # when the sus chord was complete
    held = a["end_ms"] - complete_at
    third_on = next((n["on_ms"] for n in _onsets_between(ctx, b["start_ms"] - ONSET_GROUP_MS, b["end_ms"])
                     if n["note"] % 12 == third_pc), None)
    if third_on is None or held < SUS_HOLD_MS:
        return None
    gesture = third_on  # the unbroken run of attacks (under SUS_HOLD_MS apart) that the 3rd arrives in
    for t in sorted({n["on_ms"] for n in _onsets_between(ctx, a["start_ms"], third_on)}, reverse=True):
        if gesture - t >= SUS_HOLD_MS:
            break
        gesture = t
    if gesture <= complete_at:
        return None  # the 3rd is the next note of the same roll that built the sus chord
    sus = "sus4" if 5 in arr else "sus2"
    tone = "4th" if sus == "sus4" else "2nd"
    resolves = (5 not in brr) if sus == "sus4" else (2 not in brr)
    note = (f"the {sus} resolves: its {tone} gives way to the {b['third']} 3rd" if resolves else
            f"the {b['third']} 3rd is added and the {tone} stays (the sus note is kept, so nothing resolves)")
    return {"at": a["at"], "start_ms": a["start_ms"], "from": a["label"] or a["analysed_as"],
            "to": b["label"] or b["analysed_as"], "key": b["key"], "numbers": [a["number"], b["number"]],
            "resolves": resolves, "held_s": _r(held / 1000, 2), "note": note}


def _chord_tone_intervals(w: dict) -> set:
    """Semitones above the analysed root of the chord's own 3rd, 5th and 7th (read from its name), not its tensions."""
    s = w["suffix"] or ""
    tones = {4 if w["third"] == "major" else 3} if w["third"] else set()
    tones.add(6 if ("dim" in s or "b5" in s) else 8 if ("aug" in s or "#5" in s) else 7)
    if s.startswith("maj") or "(maj" in s:
        tones.add(11)
    elif re.search(r"(^|[^a-z(])(7|9|11|13)", s) or s.startswith("m7") or s.startswith("m9") or s.startswith("m1"):
        tones.add(9 if s.startswith("dim7") else 10)
    return tones


def _different_harmonies(x: dict, y: dict) -> bool:
    """Two chords that are really different harmonies: neither's pitch classes all inside the other's (not one chord
    unfolding or gaining a note), and on different roots, or on one root with a 3rd each and more than one note apart
    (C, then Cm)."""
    px, py = set(x["_pcs"]), set(y["_pcs"])
    if px <= py or py <= px:
        return False
    return x["_root_pc"] != y["_root_pc"] or bool(x["third"] and y["third"] and len(px ^ py) > 1)


def _pedal_point(run: List[dict], ctx: dict) -> Optional[dict]:
    """A low bass note that really sounds (its own on-to-end intervals, below middle C) for PEDAL_POINT_MIN_MS while
    the chords above it are rooted elsewhere for PEDAL_POINT_FOREIGN_SHARE of the time."""
    pc = run[0]["_bass_pc"]
    s0, s1 = run[0]["start_ms"], run[-1]["end_ms"]
    by_note: Dict[int, List[tuple]] = {}
    for n in _onsets_between(ctx, s0 - ctx["longest"] - 1, s1):
        if n["note"] % 12 == pc and n["note"] < BASS_MAX_MIDI and n["end_ms"] > s0:
            by_note.setdefault(n["note"], []).append((max(n["on_ms"], s0), min(n["end_ms"], s1)))
    spans = _union([iv for ivs in by_note.values() for iv in ivs])
    held = sum(y - x for x, y in spans)
    if held < PEDAL_POINT_MIN_MS:
        return None
    note = max(by_note, key=lambda m: sum(y - x for x, y in _union(by_note[m])))
    first, last = spans[0][0], spans[-1][1]
    above: List[tuple] = []
    for w in run:
        if w["end_ms"] <= first or w["start_ms"] >= last:
            continue
        ident = (w["_root_pc"], w["suffix"]) if w["_root_pc"] is not None else tuple(w["_pcs"])
        if not above or above[-1][0] != ident:
            above.append((ident, w["label"] or w["analysed_as"] or w["name"]))
    over = [w for w in run if w["_root_pc"] is not None and w["end_ms"] > first and w["start_ms"] < last]
    foreign_ms = sum(min(w["end_ms"], last) - max(w["start_ms"], first) for w in over if w["_root_pc"] != pc)
    if foreign_ms < PEDAL_POINT_FOREIGN_SHARE * (last - first):
        return None
    if len({w["_root_pc"] for w in over}) < 2 and all((pc - w["_root_pc"]) % 12 in _chord_tone_intervals(w)
                                                      for w in over):
        return None  # one chord over its own 3rd, 5th or 7th is an inversion, not a pedal point
    # the chords above must change: two really different harmonies (_different_harmonies), each held
    # PEDAL_POINT_HARMONY_MS over the bass and each with its 3rd above the bass or three notes struck together, not a
    # pedal wash of the whole scale; and at least one of the two without the bass note (Fm over Eb). One chord with a
    # tune over its own root (Ab, with F G Eb in the melody), a chord unfolding over its 5th (Absus4 as a Db arpeggio
    # starts, then Dbadd9/Ab) or gaining a note over its 3rd (Em9/F#, then Em11/F#) is not a pedal point.
    held_as: Dict[tuple, list] = {}
    for w in over:
        if len(w["_pcs"]) <= PEDAL_POINT_MAX_PCS and len(w["_upper"]) >= 2 and \
                ({(w["_root_pc"] + 3) % 12, (w["_root_pc"] + 4) % 12} & w["_upper"] or w["_strike"] >= 3):
            slot = held_as.setdefault((w["_root_pc"], w["suffix"]), [0.0, w])
            slot[0] += min(w["end_ms"], last) - max(w["start_ms"], first)
            if w["end_ms"] - w["start_ms"] > slot[1]["end_ms"] - slot[1]["start_ms"]:
                slot[1] = w
    harmonies = [w for ms, w in held_as.values() if ms >= PEDAL_POINT_HARMONY_MS]
    if not any(_different_harmonies(x, y) and not (pc in x["_upper"] and pc in y["_upper"])
               for x, y in combinations(harmonies, 2)):
        return None
    out = {"at": clock(first), "start_ms": first, "seconds": _r(held / 1000, 1), "span_s": _r((last - first) / 1000, 1),
           "bass": midi_name(note, run[0]["key"]), "over": [x[1] for x in above], "key": run[0]["key"],
           "share_over_a_foreign_bass": _r(foreign_ms / (last - first), 2)}
    if len({x[0] for x in above}) < 2:
        out["note"] = "one chord held over a bass that is not its root"
    return out


def _dominant_over_4(ws: List[dict], idx: int) -> Optional[dict]:
    """A 4 chord without its 3rd that holds the whole 5 chord (Bb D F over Ab, no C) and whose bass then falls to 3 or 1
    is heard as the 5 chord over the 4 in the bass, not as the Lydian 4: {name, number, why}, or None."""
    w = ws[idx]
    area = w["_area"]
    tonic = area["tonic"]
    if w["_bass_pc"] is None or not w["_low_bass"] or (w["_bass_pc"] - tonic) % 12 != 5:
        return None
    rel = {(p - tonic) % 12 for p in w["_pcs"]}
    if 9 in rel or not {7, 11, 2} <= rel:
        return None
    t, nxt = w["end_ms"], None
    for x in ws[idx + 1:]:
        if x["start_ms"] - t > CADENCE_GAP_MS or x["_area"] is not area:
            break
        t = x["end_ms"]
        if x["_bass_pc"] is not None and x["_low_bass"] and x["_bass_pc"] != w["_bass_pc"]:
            nxt = x
            break
    if nxt is None or (nxt["_bass_pc"] - tonic) % 12 not in (4, 0) or nxt["_bass"] >= w["_bass"]:
        return None
    name = f"{pc_name((tonic + 7) % 12, w['key'])}7/{pc_name(w['_bass_pc'], w['key'])}"
    return {"name": name, "number": _number(name, w["key"]),
            "why": f"the 5 chord's notes over the 4 in the bass (no {pc_name((tonic + 9) % 12, w['key'])}, the 4 chord's "
                   f"3rd), the bass then falling to {nxt['bass']['note']}"}


def _lydian_moments(found: List[dict]) -> List[dict]:
    """Back-to-back Lydian 4 windows (LYDIAN_JOIN_MS apart, one root and bass) are one moment: its time is the sum of
    theirs, its name the longest one's."""
    groups: List[List[dict]] = []
    for w in found:
        last = groups[-1][-1] if groups else None
        if last and w["start_ms"] - last["end_ms"] <= LYDIAN_JOIN_MS and w["_root_pc"] == last["_root_pc"] and \
                w["_bass_pc"] == last["_bass_pc"]:
            groups[-1].append(w)
        else:
            groups.append([w])
    out = []
    for g in groups:
        longest = max(g, key=lambda x: x["seconds"])
        root = longest["_root_pc"]
        rr = {(p - root) % 12 for p in longest["_pcs"]}
        out.append(_moment(longest, at=g[0]["at"], start_ms=g[0]["start_ms"], seconds=_r(sum(x["seconds"] for x in g), 2),
                           span_s=_r((g[-1]["end_ms"] - g[0]["start_ms"]) / 1000, 2), windows=len(g),
                           note=f"the 4 chord with its #11 ({pc_name((root + 6) % 12, longest['key'])}): the Lydian "
                                f"sound" + ("" if 4 in rr else ", its 3rd left out")))
    return out


def _bass_lines(ws: List[dict]) -> List[dict]:
    """Low bass notes moving by half or whole steps one way, window to window (or inside a bass-line window), through at
    least BASS_LINE_MIN_NOTES notes with at least two half steps: [{at, until, start_ms, end_ms, notes, direction,
    chromatic, key, chords}]. (G Gb F E Eb under D7#5/F# and C9/E is a bass line walking down to its chord.)"""
    lines: List[dict] = []
    notes: List[dict] = []
    direction = 0

    def emit(seq: List[dict], sign: int) -> None:
        if len(seq) < BASS_LINE_MIN_NOTES:
            return
        moves = [_signed(b["pc"] - a["pc"]) for a, b in zip(seq, seq[1:])]
        if sum(1 for m in moves if abs(m) == 1) < 2:
            return
        key = seq[0]["w"]["key"]
        chords = []
        for n in seq:
            for x in n["ws"]:
                label = x["label"] or x["analysed_as"]
                if label and label not in chords:
                    chords.append(label)
        lines.append({"at": clock(seq[0]["start"]), "until": clock(seq[-1]["end"]), "start_ms": seq[0]["start"],
                      "end_ms": seq[-1]["end"], "notes": [midi_name(n["midi"], key) for n in seq],
                      "direction": "falling" if sign < 0 else "rising", "chromatic": all(abs(m) == 1 for m in moves),
                      "key": key, "chords": chords})
    for w in ws:
        if w["_bass_pc"] is None or not w["_low_bass"] or w["_area"] is None:
            continue
        seq = [_note_midi(x) for x in w["bass_line"]["notes"]] if w.get("bass_line") else [w["_bass"]]
        for m in seq:
            pc = m % 12
            if notes and (w["start_ms"] - notes[-1]["end"] > CADENCE_GAP_MS or w["_area"] is not notes[-1]["w"]["_area"]):
                emit(notes, direction)
                notes, direction = [], 0
            if notes and pc == notes[-1]["pc"]:
                notes[-1]["end"] = w["end_ms"]
                if w not in notes[-1]["ws"]:
                    notes[-1]["ws"].append(w)
                continue
            if notes:
                step = _signed(pc - notes[-1]["pc"])
                leap = abs(m - notes[-1]["midi"]) > 2  # the step taken with an octave jump (E3 to Eb2)
                jumps = sum(1 for x, y in zip(notes, notes[1:]) if abs(y["midi"] - x["midi"]) > 2)
                if abs(step) > 2 or (direction and (step > 0) != (direction > 0)) or (leap and jumps >= 1) or \
                        abs(m - notes[-1]["midi"]) > 14:
                    emit(notes, direction)  # a line takes at most one octave jump
                    notes, direction = ([notes[-1]], step) if abs(step) <= 2 and abs(m - notes[-1]["midi"]) <= 14 \
                        else ([], 0)
                else:
                    direction = step
            notes.append({"pc": pc, "midi": m, "start": w["start_ms"], "end": w["end_ms"], "w": w, "ws": [w]})
    emit(notes, direction)
    return lines


def _findings(ws: List[dict], areas: List[dict], ctx: dict) -> dict:
    lydian_windows, dominants, dyads_on_5, outside = [], [], [], []
    pedal_points, cadences, suspensions, colours = [], [], [], []
    bass_lines = _bass_lines(ws)
    for idx, w in enumerate(ws):
        area, root = w["_area"], w["_root_pc"]
        if root is None or len(w["_pcs"]) < 2 or not area:
            continue
        rr = {(p - root) % 12 for p in w["_pcs"]}
        rel = _rel(w, root)
        over4 = _dominant_over_4(ws, idx) if area["mode"] == "major" and rel == 5 and len(rr) >= 3 else None
        if over4:
            w["heard_as"] = over4
            dominants.append(_moment(w, form="with its major 3rd", bass=w["bass"]["note"], over="4",
                                     label=over4["name"], analysed_as=over4["name"], number=over4["number"],
                                     read_as=w["label"] or w["analysed_as"]))
            continue
        if area["mode"] == "major" and rel == 5 and 6 in rr and 3 not in rr and len(rr) >= 3:
            lydian_windows.append(w)
        if rel == 7 and len(rr) >= 3:
            form = ("with its major 3rd" if w["third"] == "major" else "minor (5m)" if w["third"] == "minor"
                    else "suspended" if (5 in rr or 2 in rr) else "open (no 3rd)")
            over = "its root" if w["_bass_pc"] == root else (_bass_degree(w) or "-")
            dominants.append(_moment(w, form=form, bass=w["bass"]["note"], over=over))
        elif rel == 7:
            dyads_on_5.append(_moment(w))
    lydian = _lydian_moments(lydian_windows)
    for w in ws:
        if w["class"] not in NON_CHORD_CLASSES and len(w["_pcs"]) >= 3:
            line = next((b for b in bass_lines if b["start_ms"] <= w["start_ms"] < b["end_ms"]), None)
            if line:
                w["on_bass_line"] = line["at"]
            outside.append(_moment(w, **{"class": w["class"], "detail": w["class_detail"],
                                         "on_bass_line": line["at"] if line else None}))

    for n in range(1, len(ws)):
        a, b = ws[n - 1], ws[n]
        cad = _cadence(ws, n)
        if cad:
            cadences.append(cad)
        if b["start_ms"] - a["end_ms"] > CADENCE_GAP_MS or a["_root_pc"] is None or b["_root_pc"] is None:
            continue
        ar, br = a["_root_pc"], b["_root_pc"]
        if ar == br and len(a["_pcs"]) >= 3 and len(b["_pcs"]) >= 3:
            sus = _suspension(a, b, ctx)
            if sus:
                suspensions.append(sus)
            elif a["third"] and a["third"] == b["third"] and set(b["_pcs"]) > set(a["_pcs"]):
                added = [ADDED_NAMES[(p - ar) % 12] for p in sorted(set(b["_pcs"]) - set(a["_pcs"]),
                                                                    key=lambda p: ADDED_ORDER[(p - ar) % 12])]
                colours.append({"at": a["at"], "start_ms": a["start_ms"], "from": a["label"] or a["analysed_as"],
                                "to": b["label"] or b["analysed_as"], "added": added, "key": b["key"],
                                "numbers": [a["number"], b["number"]]})

    # a deceptive move the player keeps making in one key (5 -> 6m, again and again) is a progression the ear has
    # learned, a habit more than a surprise: one entry, at its first time, with how often it came
    learned: Dict[tuple, List[dict]] = {}
    for c in cadences:
        if "deceptive" in c["kind"]:
            learned.setdefault((c["key"], c["kind"]), []).append(c)
    habits = {id(c): group for group in learned.values() if len(group) >= DECEPTIVE_LEARNED for c in group}
    kept = []
    for c in cadences:
        group = habits.get(id(c))
        if group and c is not group[0]:
            continue
        if group:
            c.update(times=len(group), habit=True, at_times=[x["at"] for x in group])
        kept.append(c)
    cadences = kept
    for c in cadences:
        c.pop("_before", None)
    run: List[dict] = []
    for w in ws + [None]:
        if run and (w is None or not w["_low_bass"] or w["_bass_pc"] != run[-1]["_bass_pc"] or
                    w["start_ms"] - run[-1]["end_ms"] > 1000):
            point = _pedal_point(run, ctx)
            if point:
                pedal_points.append(point)
            run = []
        if w is not None and w["_low_bass"] and w["_bass_pc"] is not None:
            run.append(w)

    by_key: Dict[str, dict] = {}
    dom_summary: Dict[str, dict] = {}
    for d in dominants:
        for slot in (dom_summary.setdefault(d["form"], {"windows": 0, "seconds": 0.0, "over_root_s": 0.0,
                                                        "chords": {}}),
                     by_key.setdefault(d["key"], {}).setdefault(d["form"], {"windows": 0, "seconds": 0.0,
                                                                            "over_root_s": 0.0, "over": {},
                                                                            "chords": {}})):
            slot["windows"] += 1
            slot["seconds"] = _r(slot["seconds"] + d["seconds"], 2)
            if d["over"] == "its root":
                slot["over_root_s"] = _r(slot["over_root_s"] + d["seconds"], 2)
            elif "over" in slot:
                slot["over"][d["over"]] = _r(slot["over"].get(d["over"], 0) + d["seconds"], 2)
            label = d["label"] or d["analysed_as"] or d["chord"]
            slot["chords"][label] = _r(slot["chords"].get(label, 0) + d["seconds"], 2)
    groups: Dict[tuple, dict] = {}
    for o in outside:  # the times a chord rides a bass line group apart from the times it does not
        slot = groups.setdefault((o["class"], o["label"] or o["analysed_as"] or o["chord"], o["number"], o["key"],
                                  o["detail"], bool(o["on_bass_line"])),
                                 {"times": [], "seconds": 0.0, "on_bass_line": o["on_bass_line"]})
        slot["times"].append(o["at"])
        slot["seconds"] = _r(slot["seconds"] + o["seconds"], 2)
    return {
        "modulations": [{"at": b["at"], "start_ms": b["start_ms"], "from": a["key"], "to": b["key"],
                         "after_pause_s": b.get("after_pause_s")}
                        for a, b in zip(areas, areas[1:])],
        "lydian_4": lydian,
        "dominants": {"summary": dom_summary, "by_key": by_key, "windows": dominants,
                      "two_note_shapes_on_5": {"windows": len(dyads_on_5),
                                               "seconds": _r(sum(d["seconds"] for d in dyads_on_5), 2)}},
        "outside_key": [{"class": c, "chord": name, "number": num, "key": k, "detail": det, **v}
                        for (c, name, num, k, det, _), v in sorted(groups.items(),
                                                                key=lambda kv: (-kv[1]["seconds"], str(kv[0][1])))],
        "pedal_points": pedal_points,
        "bass_lines": bass_lines,
        "cadences": cadences,
        "suspensions": suspensions,
        "colour_additions": colours,
    }


# ============================================================================================ rendering
def _pct(x) -> str:
    return "-" if x is None else f"{round(100 * x)}%"


def _chord_text(w: dict) -> str:
    text = w["name"] or "-"
    if w.get("reading") and w["detect"] and w["detect"]["kind"] != "cluster" and w.get("texture", "chord") == "chord":
        text += f" = {w['reading']['text']}" if w["analysed_from"] == "reading" else \
            f" (another reading: {w['reading']['text']})"
    elif w.get("marks") and w["analysed_from"] == "detect":
        text += f" ({', '.join(MARK_WORDS[m] for m in w['marks'])})"
    if w.get("heard_as"):
        text += f" (heard as {w['heard_as']['name']} = {w['heard_as']['number']}: {w['heard_as']['why']})"
    return text


MARK_WORDS = {"no3": "no 3rd", "no5": "no 5th"}


def render_windows(doc: dict, limit: Optional[int] = None, start_ms: float = 0, end_ms: float = math.inf) -> str:
    seg = doc["segmentation"]
    shown = [w for w in doc["windows"] if w["end_ms"] > start_ms and w["start_ms"] < end_ms][:limit]
    lines = [f"# Harmonic windows ({len(doc['windows'])})", "",
             f"{seg['live_chord_events']} live chord events merged into {seg['windows']} windows "
             f"({seg['live_events_per_window']} per window; {seg['windows_before_merge']} before same-chord merging); "
             f"{seg['transients_dropped']} isolated transients dropped ({seg['transient_seconds']} s). "
             f"Home key {doc['home_key']}.", "",
             "| at | s | chord | number | key | class | bass | live | notes | spread | vel | pedal |",
             "| ---: | ---: | :--- | :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |"]
    for w in shown:
        fig = w["bass"]["figure"]
        bass = w["bass"]["note"] or "-"
        if w["bass"]["motion"] in ("moving", "figure") and len(fig) > 1:
            bass = ("lowest " if w["bass"]["motion"] == "figure" else "") + " ".join(f[0] for f in fig[:6]) + \
                (" ..." if len(fig) > 6 else "")
        elif w["bass"]["motion"] == "figure":
            bass = f"lowest {bass}"
        key = (w["key"] + ("" if w["home"] else " *")) if w["key"] else "-"
        cls = w["class"] or "-"
        if w["class"] not in NON_CHORD_CLASSES:
            cls += f": {w['class_detail']}"
        if w.get("in_home_key") and w["in_home_key"]["class"] != "diatonic":
            cls += f" (in {w['in_home_key']['key']}: {w['in_home_key']['number']}, {w['in_home_key']['class']})"
        v = w["voicing"]
        lines.append(f"| {w['at']} | {w['seconds']} | {_chord_text(w)} | {w['number'] or '-'} | {key} | {cls} | {bass} | "
                     f"{w['live']['events']} | {v['distinct_notes']} | {v['spread']} | {v['vel_mean'] or '-'} | "
                     f"{_pct(v['pedal_share'])} |")
    rest = len([w for w in doc["windows"] if w["end_ms"] > start_ms and w["start_ms"] < end_ms]) - len(shown)
    if rest > 0:
        lines.append(f"\n({rest} more windows)")
    lines.append("\n`*` the window's key area differs from the home key.")
    return "\n".join(lines) + "\n"


def render_harmony(doc: dict) -> str:
    f = doc["findings"]
    seg = doc["segmentation"]
    lines = ["# Harmony", "", f"{doc['duration_s']} s, {doc['notes']} notes, {seg['windows']} harmonic windows "
             f"(from {seg['live_chord_events']} live chord events). Home key {doc['home_key']}.", "", "## Keys"]
    for a in doc["keys"]["areas"]:
        ru = a["runner_up"]
        lines.append(f"- {a['at']} to {a['until']}: {a['key']} ({a['relation']}" +
                     (f"; runner-up {ru['key']})" if ru else ")") +
                     (f", a new section after a {a['after_pause_s']} s pause" if a.get("after_pause_s") else "") +
                     (", too short to call" if a.get("too_short") else ""))
    for a in doc["keys"]["absorbed"]:
        lines.append(f"- ({a['at']} to {a['until']} read {a['key']} but kept in {a['into']}: {a['why']})")
    lines += ["", "## Lydian 4 (back-to-back windows on one root and bass are one moment)"]
    lines += [f"- {m['at']} ({m['seconds']} s" + (f", {m['windows']} windows" if m.get("windows", 1) > 1 else "") +
              f"): {m['chord']}" + (f" -> {m['analysed_as']}" if m['analysed_as'] != m['chord'] else "") +
              f" = {m['number']} in {m['key']}" for m in f["lydian_4"]] or ["- none"]
    over4 = [d for d in f["dominants"]["windows"] if d.get("read_as")]
    lines += [f"- (not a Lydian 4: {d['at']} {d['read_as']} is heard as {d['label']} = {d['number']}, the 5 chord over "
              f"the 4 in the bass)" for d in over4]
    lines += ["", "## Dominants (chords on 5, by key area, with the bass under them)"]
    lines += [f"- {x}" for x in _dominant_lines(f["dominants"])] or ["- none"]
    dy = f["dominants"]["two_note_shapes_on_5"]
    if dy["windows"]:
        lines.append(f"- (and {dy['windows']} two-note shapes on 5, {dy['seconds']} s, not counted above)")
    lines += ["", "## Outside the key (chords of three or more notes)"]
    for o in f["outside_key"][:25]:
        times = ", ".join(o["times"][:6]) + (" ..." if len(o["times"]) > 6 else "")
        lines.append(f"- {o['chord']} ({o['number'] or 'no number'} in {o['key']}): {o['class']}, {o['detail']}; "
                     f"{o['seconds']} s at {times}")
    if not f["outside_key"]:
        lines.append("- none")
    home_view = [w for w in doc["windows"] if w.get("in_home_key") and w["in_home_key"]["class"] != "diatonic"
                 and len(w["pcs"]) >= 3]
    if home_view:
        lines += ["", f"## Heard from the home key ({doc['home_key']})"]
        grouped: Dict[tuple, List[str]] = {}
        for w in home_view:
            h = w["in_home_key"]
            grouped.setdefault((h["name"] or w["name"], h["number"], h["class"], h["detail"]), []).append(w["at"])
        for (name, num, cls, det), times in sorted(grouped.items(), key=lambda kv: -len(kv[1]))[:15]:
            lines.append(f"- {name} = {num or 'no number'}: {cls}, {det} "
                         f"(at {', '.join(times[:6])}{' ...' if len(times) > 6 else ''})")
    lines += ["", "## Pedal points (a low bass note sounding while the chords above it are rooted elsewhere)"]
    lines += [f"- {p['at']} ({p['bass']} sounds {p['seconds']} s): under {' -> '.join(p['over'])}"
              for p in f["pedal_points"]] or ["- none"]
    lines += ["", "## Bass lines (the bass walking by step one way; chords on it are passing points)"]
    walking = [f"- {w['at']} ({w['seconds']} s): {w['name']} (inside one window)" for w in doc["windows"]
               if w.get("bass_line")]
    lines += [f"- {b['at']}-{b['until']}: {' '.join(b['notes'])} ({b['direction']} by "
              f"{'half steps' if b['chromatic'] else 'steps'}) under {', '.join(b['chords'][:6])}"
              for b in f.get("bass_lines") or []] + walking or ["- none"]
    lines += ["", "## Cadences"]
    lines += [f"- {c['at']}: {c['kind']}: {' -> '.join(c['chords'])} ({' -> '.join(str(x) for x in c['numbers'])} in "
              f"{c['key']}; bass {' -> '.join(str(b) for b in c['bass'])})" +
              (f"; {c['times']} times ({', '.join(c['at_times'][:6])}), a move he keeps making, so a habit more than a "
               f"surprise" if c.get("habit") else "") for c in f["cadences"]] or ["- none"]
    lines += ["", "## Suspensions (a held sus chord, then its 3rd)"]
    lines += [f"- {s['at']}: {s['from']} -> {s['to']} ({s['note']})" for s in f["suspensions"]] or ["- none"]
    lines += ["", "## Colour additions"]
    lines += [f"- {c['at']}: {c['from']} -> {c['to']} (adds {', '.join(c['added'])})" for c in f["colour_additions"]] \
        or ["- none"]
    p = doc["pedal"]
    lines += ["", "## Pedal",
              f"Down {p['percent_down']}% of the session, {p['presses']} presses ({p['mean_down_s']} s each). "
              f"{_pct(p['harmony_changes_with_a_lift'])} of harmony changes come with a pedal lift; "
              f"{_pct(p['lifts_at_a_harmony_change'])} of lifts land on a harmony change."]
    return "\n".join(lines) + "\n"


# ================================================================================================ verbs
# The verbs Claude (and Daniel) read before talking theory about his playing. Each one is a pure function from the
# analysis (plus the session's sounding notes) to a JSON-able dict, and a renderer to compact plain text. Times are
# m:ss from the session start; the session's start is shown in local time.
TIMELINE_MIN_S = 1.0         # the brief's timeline lists chords held at least this long, raised by half seconds...
TIMELINE_LINES = 8         # ...until the timeline fits in this many lines
LINE_WIDTH = 116
PROG_MIN_S = 0.5             # moves and loops count chords held at least this long
PROG_GAP_MS = 4000           # a longer gap between two chords, or a change of key area, ends a chord sequence
EVIDENCE_MS = 30000          # a key change's evidence compares the notes heard this long on either side of it
EVIDENCE_OTHER_SHARE = 0.06  # other notes whose share moves this much across a key change are listed too
KEY_CLOSE = 0.05             # a runner-up key this close in score makes a key area a close call
HOME_TIE_SHARE = 0.6         # a home key with less than this share of chord time is flagged...
HOME_TIE_MARGIN = 0.1        # ...as a near tie when the next key is within this share of it
ASK_SEPARATION_MS = 8000     # the brief's moments to ask about start at least this far apart
ASK_PER_KIND = 3             # candidates offered per kind of moment (the best that is far enough from the others wins)
ASK_PEDAL_MAX_OCTAVE = 3     # a pedal point to ask about sits below middle C
ASK_LOOP_CAP = 20           # a loop, however long, ranks under a key change, a cadence or a colour habit
ASK_MIN_AREA_S = 20         # a key change is a moment to ask about when both areas last this long
ASK_ARPEGGIO_NAMES = 8       # a moving-bass chord the live page renamed at least this often is an arpeggio to ask about
WIDE_SPREAD = 24             # a voicing spanning this many semitones (two octaves) or more is wide
PC_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PC_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
QUALITY_MARK = {"major": "", "minor": "m", "diminished": "°", "augmented": "+", "suspended": "sus", "power": "^5"}
QUALITY_PROBE = {"major": "", "minor": "m", "diminished": "dim", "augmented": "aug", "suspended": "sus4", "power": "5"}
LETTER_STEPS = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 5, 9: 5, 10: 6, 11: 6}  # letters above a root
FROM_ROOT = {0: "root", 1: "b9", 2: "9", 3: "m3", 4: "3rd", 5: "11", 6: "#11", 7: "5th", 8: "b13", 9: "13",
             10: "b7", 11: "maj7"}
COLOUR_ORDER = ("plain triad", "power chord (root and 5th)", "sus4", "sus2", "no 3rd", "add9", "6", "maj7", "b7 (plain 7th)",
                "9", "11", "#11", "13", "altered (b9, #9, b13)", "#5 (augmented)", "b5 (diminished)",
                "inversion (3rd, 5th or 7th in the bass)", "other bass note (not a chord tone)")
MODE_WORDS = {"Mixolydian": "the major scale with its 7th lowered: open, a little bluesy",
              "Lydian": "the major scale with its 4th raised: bright and floating",
              "Dorian": "the minor scale with its 6th raised: minor, but warm",
              "Phrygian": "the minor scale with its 2nd lowered: dark, with a Spanish edge"}
STEP_WORDS = {1: "a half step up", 2: "a whole step up", 3: "up a minor 3rd", 4: "up a major 3rd", 5: "up a 4th",
              6: "a tritone away", 7: "up a 5th", 8: "down a major 3rd", 9: "down a minor 3rd",
              10: "a whole step down", 11: "a half step down"}

# (term, pattern that shows the term was used, plain words, short words). A verb's output ends with the terms it used,
# once each. {placeholders} are examples in the session's home key (_glossary_examples), Eb major without one.
EXTENSION_RE = r"#11|add9|add#?11|maj7|maj9|maj13|(?:maj|m|\^|add|[A-G][#b]?|\(|,)(?:9|11|13)(?![\d:])"
GLOSSARY = (
    ("numbers", r"\bnumbers?\b", "chords named by their place in the key: 1 is the home chord, 4 the chord on the "
                                 "scale's 4th note, b7 a half step below the scale's 7th; m is minor, and X/Y (1/3 in "
                                 "numbers) puts chord X over the bass note Y.",
     "chords by their place in the key (1 home, m minor, X/Y chord X over bass Y)"),
    ("home key, key area", r"\bhome key\b|\bkey areas?\b|\bkey change\b",
     "the home key has the most chord time; a key area is a stretch with one key as home, and moving to a new one is "
     "a modulation.", "home key = most chord time; key area = a stretch with its own home"),
    ("diatonic", r"\bdiatonic\b", "built only from the notes of the key.", "only the key's notes"),
    ("borrowed", r"\bborrowed\b|\bparallel (?:minor|major|key)",
     "from the parallel key, the same home note in the other mode ({parallel} for {home}): outside the key, but still "
     "at home.", "from the parallel key ({parallel})"),
    ("relative", r"\brelative (?:minor|major)", "same notes, different home note ({rel_minor} and {rel_major}).",
     "same notes, other home note"),
    ("Lydian", r"\bLydian\b", "the major scale with its 4th raised: bright, floating. The Lydian 4 is the 4 chord with "
                              "its #11 ({sharp11} over {four} in {mkey}), a note the key already has (its 7th).",
     "the 4 chord with its #11 ({sharp11} over {four})"),
    ("modal", r"\bmodal\b|Mixolydian|Dorian|Phrygian",
     "a colour from a mode on the home note: Mixolydian lowers the major scale's 7th ({b7} in {mtonic}), Dorian raises "
     "the minor scale's 6th, Phrygian lowers its 2nd.", "a mode's colour on the home note"),
    ("chromatic", r"\bchromatic\b", "outside both the key and its parallel key.", "outside the key and its parallel"),
    ("secondary dominant", r"secondary dominant|\b5 of b?\d", "a major chord acting as the 5 of a chord other than 1 "
                                                             "('5 of 2m': {sec} pointing at {sec_target} in {mkey}).",
     "the 5 of a chord other than 1"),
    ("sus", r"\bsus|\bsuspended\b|\bresolv", "sus4 and sus2 put the 4th or the 2nd where the 3rd would be, neither "
                                             "major nor minor; the suspension resolves when the 3rd comes in "
                                             "({sus_from} -> {sus_to}).", "the 4th or 2nd in place of the 3rd"),
    ("dominant", r"\bdominants?\b", "the 5 chord, which pulls toward 1; suspended ({dom_sus} in {mtonic}) it pulls more "
                                    "softly.", "the 5 chord, pulling to 1"),
    ("pedal point", r"\bpedal points?\b", "one bass note held while the chords above it change.",
     "a held bass under changing chords"),
    ("bass line", r"\bbass lines?\b", "the lowest notes walking by step while the notes above hold or follow them; heard "
                                      "as a line, not as one chord.", "the bass walking by step"),
    ("extensions", EXTENSION_RE, "notes stacked on a chord: 9, 11, 13 are the 2nd, 4th and 6th an octave up; add9 adds "
                                 "the 9th without a 7th; #11 is the raised 4th ({sharp11} over {four}); maj7 is a half "
                                 "step below the root ({maj7} in {mtonic}), a plain 7 a whole step ({b7}).",
     "9, 11, 13 = the 2nd, 4th, 6th an octave up; maj7 a half step under the root"),
    ("inversion", r"\binversion\b|other bass note", "an inversion puts the chord's 3rd, 5th or 7th in the bass instead "
                                                    "of its root; any other bass note is a tension or a pedal.",
     "the 3rd, 5th or 7th in the bass"),
    ("reading", r"\breadings?\b", "a best-fit name worked out from every sounding note, where the page's namer left "
                                  "the notes unnamed or put them over an odd bass.", "a best-fit name from every note"),
    ("cadence", r"\bcadences?\b", "a move that lands on the home chord: 5 -> 1 is authentic (the strongest), 4 -> 1 "
                                  "plagal (the 'amen'); a deceptive cadence sets up 1 and lands on 6m instead.",
     "a landing on 1 (5 -> 1 authentic, 4 -> 1 plagal)"),
    ("colour addition", r"colour additions?", "the same chord with a note added ({add9} -> {maj9}).",
     "the same chord, a note added"),
    ("loop", r"\bloops?\b", "the same chords cycled back to back at least twice.", "chords cycled back to back"),
    ("power chord, no 3rd", r"power chord|\^5\b|no 3rd|\(no3\)|no 5th|\(no5\)",
     "a power chord (^5) is root and 5th only; 'no 3rd' (no3) means the name's major or minor is implied, not played; "
     "'no 5th' (no5) means the chord's 5th was left out.", "^5 root and 5th; (no3), (no5): that note not played"),
    ("^ in numbers", r"\d\^(?!5\b)[\dm]", "in a number, ^ joins the degree to a chord type that starts with a digit, "
                                          "so the two do not run together: 5^7 is the 5 chord with a 7th, 1^6/9 the 1 "
                                          "chord with a 6th and 9th.", "5^7 = the 5 chord with a 7th"),
    ("two-note shape", r"\b[A-G][#b]?-[A-G][#b]?\b|(?<![\d:])b?\d-b?\d(?![\d:])",
     "X-Y names two notes sounding without a third one ({mtonic}-{third}; 1-3 in numbers).", "two notes, no third"),
    ("line, broken chord", r"\bline\b|broken chord|\bruns?\b",
     "a line (or run) is notes one at a time, mostly by step (a melody or a scale run, even when the pedal rings it on); "
     "a broken chord is a chord's notes one or two at a time. Neither was held as a chord, so neither counts as one "
     "here.", "notes one at a time, not counted as chords"),
    ("section, pause", r"\bnew section\b|\bpause\b", "a section is a stretch of playing; a pause of "
                                                      f"{SECTION_GAP_MS // 1000} s or more (nothing sounding, pedal up) "
                                                      "starts a new one, and keys, cadences and moves never reach across "
                                                      "it.", f"a pause of {SECTION_GAP_MS // 1000} s or more starts a "
                                                             f"new section"),
    ("velocity", r"\bvelocity\b", "how hard a key was struck, 1 (softest) to 127.", "key force, 1 to 127"),
    ("semitone", r"\bsemitones?\b", "one key on the piano; 12 is an octave.", "one key; 12 an octave"),
    ("runner-up", r"runner-up|close call", "the next most likely key; a close one makes the key call uncertain.",
     "the next most likely key"),
)
GLOSSARY_CORE = ("numbers", "borrowed", "Lydian", "modal", "chromatic", "secondary dominant", "sus", "dominant",
                 "pedal point", "bass line", "extensions", "inversion", "cadence", "loop")  # theory words; the rest are
                                                                                            # reading aids


def _and(items: List[str]) -> str:
    items = list(items)
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else (items[0] if items else "")


def _note_midi(name: str) -> int:
    """'C#7' -> 97 (C4 = 60)."""
    m = re.fullmatch(r"([A-G])(#{1,2}|b{1,2})?(-?\d+)", name)
    acc = len(m.group(2) or "") * (1 if (m.group(2) or "").startswith("#") else -1)
    return (int(m.group(3)) + 1) * 12 + LETTER_PC[LETTERS.index(m.group(1))] + acc


def clock_tenths(ms: float) -> str:
    tenths = max(0, int(round(ms / 100)))
    return f"{tenths // 600}:{tenths % 600 / 10:04.1f}"


def _glossary_examples(key: Optional[str]) -> dict:
    """The glossary's examples in a key (a minor key's examples of major-key things come from its relative major)."""
    k = nashville.parse_key(key) if key else None
    tonic, mode = (k["tonic"], k["mode"]) if k else (3, "major")
    home = key_name(tonic, mode)
    major = tonic if mode == "major" else (tonic + 3) % 12
    mkey = key_name(major, "major")

    def n(i: int) -> str:
        return pc_name((major + i) % 12, mkey)
    return {"home": home, "parallel": parallel_key(home), "mkey": mkey, "mtonic": n(0), "third": n(4), "four": n(5),
            "sharp11": n(11), "maj7": n(11), "b7": n(10), "rel_minor": key_name((major + 9) % 12, "minor"),
            "rel_major": mkey, "sec": n(9) + "7", "sec_target": n(2) + "m", "sus_from": n(5) + "sus2",
            "sus_to": n(5) + "add9", "dom_sus": n(7) + "7sus4", "add9": n(0) + "add9", "maj9": n(0) + "maj9"}


def glossary(text: str, key: Optional[str] = None, max_lines: Optional[int] = None) -> List[str]:
    """'Words:' and one line per term the text used, in GLOSSARY order (nothing when it used none), its examples in the
    key given (the session's home key). With max_lines, a list longer than that keeps the theory words (GLOSSARY_CORE)
    whole and folds the reading aids into short 'also' lines."""
    ex = _glossary_examples(key)
    used = [(term, words.format(**ex), short.format(**ex)) for term, pattern, words, short in GLOSSARY
            if re.search(pattern, text)]
    if not used:
        return []
    full = ["", "Words:"] + [f"- {term}: {words}" for term, words, _ in used]
    if max_lines is None or len(full) <= max_lines:
        return full
    core = [f"- {term}: {words}" for term, words, _ in used if term in GLOSSARY_CORE]
    aids = [f"{term} = {short}" for term, _, short in used if term not in GLOSSARY_CORE]
    return ["", "Words:"] + core + (_wrap("- also: ", aids, indent="  ") if aids else [])


def _wrap(prefix: str, items: List[str], max_lines: Optional[int] = None, sep: str = "; ",
          indent: str = "    ") -> List[str]:
    """Items joined after a prefix, wrapped at LINE_WIDTH; with max_lines, the rest is counted as (+N more)."""
    lines: List[str] = []
    cur, fresh = prefix, True
    for k, item in enumerate(items):
        if not fresh and len(cur) + len(sep) + len(item) > LINE_WIDTH:
            if max_lines and len(lines) + 1 >= max_lines:
                lines.append(cur + f" (+{len(items) - k} more)")
                return lines
            lines.append(cur + sep.rstrip())
            cur, fresh = indent, True
        cur += item if fresh else sep + item
        fresh = False
    lines.append(cur)
    return lines


# ---------------------------------------------------------------------------------------------- sessions
def session_start(info: dict) -> Optional[datetime]:
    """When the playing started, in local time: the page's clock for a session buffered in the browser and uploaded
    later (meta.opened_at_client), else the server's opened_at, else the local time the session id starts with."""
    meta = info.get("meta") if isinstance(info.get("meta"), dict) else {}
    for text in (meta.get("opened_at_client"), info.get("opened_at")):
        if isinstance(text, str):
            try:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone()
            except ValueError:
                continue
    try:
        return datetime.strptime(str(info.get("session", ""))[:15], "%Y%m%d-%H%M%S").astimezone()
    except ValueError:
        return None


def _local(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "unknown time"


def resolve_sessions(store: PerformanceStore, selector: Optional[str] = None, today: Optional[date] = None) -> List[str]:
    """A session id, 'latest' (the default), or 'today': every session started on today's local date, oldest first. A
    session directory's path, or an id with a trailing slash (tab completion), is read as its id."""
    if selector not in (None, "", "latest", "today"):
        selector = str(selector).rstrip("/\\")
        if re.search(r"[/\\]", selector):
            selector = re.split(r"[/\\]", selector)[-1]
    if selector in (None, "", "latest"):
        latest = store.latest()
        if not latest:
            raise PerformanceError(f"no practice sessions under {store.root}")
        return [latest]
    if selector == "today":
        day = today or datetime.now().astimezone().date()
        found = []
        for row in store.list():
            try:
                start = session_start(store.info(row["session"]))
            except (PerformanceError, ValueError, OSError):
                continue
            if start and start.date() == day:
                found.append((start, row["session"]))
        if not found:
            raise PerformanceError(f"no practice sessions started today ({day.isoformat()})")
        return [sid for _, sid in sorted(found)]
    try:
        store.info(selector)  # UnknownSession for a bad id
    except (ValueError, OSError) as exc:
        raise PerformanceError(f"session {selector}: session.json is unreadable ({type(exc).__name__}: {exc})") from exc
    return [selector]


OPEN_TAIL_MS = 60000  # in an open session, notes still down are counted up to now, at most this long past the last event


def read_events(store: PerformanceStore, session: str) -> Tuple[List[dict], List[str]]:
    """(events, problems): a session's log read line by line. Unreadable lines (a crash mid-write) and events without a
    usable time, kind or note are skipped and counted, so one bad line never hides the rest of the session."""
    problems: List[str] = []
    try:
        raw = store.events(session)
    except (ValueError, OSError, TypeError):
        raw = None
    if raw is None:
        path = Path(store.root) / session / "events.jsonl"
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return [], [f"its events.jsonl could not be read ({type(exc).__name__})"]
        raw, bad = [], 0
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                raw.append(json.loads(line))
            except ValueError:
                bad += 1
        if bad:
            problems.append(f"{bad} unreadable log line{'s' if bad != 1 else ''} skipped")
    events, skipped, impossible = [], 0, 0
    for e in raw:
        ok = isinstance(e, dict) and isinstance(e.get("kind"), str) and isinstance(e.get("t_ms"), (int, float)) \
            and not isinstance(e.get("t_ms"), bool) and e["t_ms"] >= 0
        if ok and e["kind"] in ("on", "off", "sound_end"):
            ok = isinstance(e.get("note"), int) and not isinstance(e.get("note"), bool) and 0 <= e["note"] <= 127
        if ok and e["kind"] == "on" and not isinstance(e.get("vel", 0), (int, float)):
            ok = False
        if ok and not (math.isfinite(e["t_ms"]) and e["t_ms"] <= MAX_EVENT_T_MS):
            impossible += 1  # an epoch time written by mistake: kept, it would stretch the session over decades
            continue
        if ok:
            events.append(e)
        else:
            skipped += 1
    if skipped:
        problems.append(f"{skipped} event{'s' if skipped != 1 else ''} without a usable time, kind or note skipped")
    if impossible:
        problems.append(f"{impossible} event{'s' if impossible != 1 else ''} at an impossible time (more than "
                        f"{MAX_EVENT_T_MS // 86400000} days into the session) skipped")
    return events, problems


def load_session(store: PerformanceStore, session: str, theory_source=None, node: Optional[str] = None) -> dict:
    """{session, info, start, closed, events, problems, end_ms, snd, doc}: one session read and analysed. Every failure
    is a PerformanceError that names the session."""
    try:
        info = store.info(session)
    except (ValueError, OSError) as exc:
        raise PerformanceError(f"session {session}: session.json is unreadable ({type(exc).__name__}: {exc})") from exc
    events, problems = read_events(store, session)
    start, closed = session_start(info), bool(info.get("closed"))
    end_ms = None
    if not closed and start and events:
        elapsed = (datetime.now().astimezone() - start).total_seconds() * 1000
        last = max(e["t_ms"] for e in events)
        if elapsed > last:
            end_ms = min(elapsed, last + OPEN_TAIL_MS)
    try:
        doc = analyze(events, theory_source, node, end_ms)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise PerformanceError(f"session {session} could not be analysed ({type(exc).__name__}: {exc})") from exc
    return {"session": session, "info": info, "start": start, "closed": closed, "events": events,
            "problems": problems, "end_ms": end_ms, "snd": sounding(events, end_ms), "doc": {"session": session, **doc}}


def headline(sess: dict) -> str:
    doc = sess["doc"]
    bits = [f"played {_local(sess['start'])}", f"{clock(doc['duration_s'] * 1000)} long", f"{doc['notes']} notes"]
    if not sess["closed"]:
        bits.append("still open")
    return f"Session {sess['session']} ({', '.join(bits)})"


def sessions_data(store: PerformanceStore, which: str = "all", today: Optional[date] = None, theory_source=None,
                  node: Optional[str] = None) -> List[dict]:
    ids = resolve_sessions(store, "today", today)[::-1] if which == "today" else [r["session"] for r in store.list()]
    rows = []
    for sid in ids:
        try:
            sess = load_session(store, sid, theory_source, node)
        except PerformanceError as exc:
            rows.append({"session": sid, "error": str(exc), "started": "unknown time", "length": "-",
                         "duration_s": None, "notes": 0, "closed": None, "home_key": None, "key_areas": 0})
            continue
        doc = sess["doc"]
        rows.append({"session": sid, "started": _local(sess["start"]), "length": clock(doc["duration_s"] * 1000),
                     "duration_s": doc["duration_s"], "notes": doc["notes"], "closed": sess["closed"],
                     "home_key": doc["home_key"] if doc["notes"] and doc["chord_seconds"] else None,
                     "key_areas": len(doc["keys"]["areas"]) if doc["notes"] and doc["chord_seconds"] else 0,
                     "problems": sess["problems"]})
    return rows


def render_sessions(rows: List[dict]) -> str:
    lines = ["Sessions, newest first (start in local time)", "",
             f"{'started':<17} {'length':>6} {'notes':>6}  {'home key':<10} {'areas':>5}  session"]
    for r in rows:
        if r.get("error"):
            lines.append(f"{'?':<17} {'-':>6} {'-':>6}  {'-':<10} {'-':>5}  {r['session']}  (unreadable: {r['error']})")
            continue
        lines.append(f"{r['started']:<17} {r['length']:>6} {r['notes']:>6}  {(r['home_key'] or '-'):<10} "
                     f"{r['key_areas']:>5}  {r['session']}{'' if r['closed'] else '  (still open)'}"
                     f"{'  (' + '; '.join(r['problems']) + ')' if r.get('problems') else ''}")
    if not rows:
        lines.append("(none)")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------ chord helpers
def is_chord(w: dict) -> bool:
    """A window analysed as a chord (detect's chord or an extended reading): not a note, an interval or an unnamed set."""
    return bool(w.get("analysed_as")) and (w.get("kind") == "chord" or w.get("analysed_from") == "reading")


def _parts(w: dict) -> Optional[dict]:
    p = nashville.parse_chord(w["analysed_as"]) if w.get("analysed_as") else None
    return p if p and p["kind"] == "chord" else None


def _row_pcs(w: dict) -> List[int]:
    return [_sp_pc(_parse_name(n)) for n in w["pcs"]]


def harmony_name(w: dict) -> Optional[str]:
    """The analysed chord without its bass note: Ebmaj9/Bb -> Ebmaj9."""
    p = _parts(w)
    return _sp_name(p["root"]) + p["suffix"] if p else None


def harmony_number(w: dict) -> Optional[str]:
    return _number(harmony_name(w), w.get("key"))


def quality(suffix: str) -> str:
    """major, minor, diminished, augmented, suspended or power, from a chord suffix."""
    s = suffix or ""
    if s == "5":
        return "power"
    if "sus" in s:
        return "suspended"
    minor = s.startswith("m") and not s.startswith("maj")
    if s.startswith("dim") or (minor and "b5" in s):
        return "diminished"
    if s.startswith("aug") or "#5" in s:
        return "augmented"
    return "minor" if minor else "major"


def core_number(w: dict) -> Optional[str]:
    """The number with only its quality (4, 6m, 5sus, 7°): the level where a progression shows through its colours."""
    p = _parts(w)
    if not p or not w.get("key"):
        return None
    q = quality(p["suffix"])
    got = nashville.nashville_from_name(_sp_name(p["root"]) + QUALITY_PROBE[q], w["key"])
    return got["root"] + QUALITY_MARK[q] if got else None


def _degree(pc: int, key: str, name: Optional[str] = None) -> Optional[str]:
    """A note's degree read by its letter, as the chord numbers read a chord's bass: F# in Bb major is #5, Cb in Eb
    major is b6 (accidentals against the major scale on the tonic, as nashville numbers minor keys too)."""
    sp = _parse_name(name or pc_name(pc, key))
    tonic = _parse_name(key.split(" ")[0])
    d = (sp[0] - tonic[0]) % 7
    acc = _signed(_sp_pc(sp) - (_sp_pc(tonic) + LETTER_PC[d]))
    return ("#" * acc if acc > 0 else "b" * -acc) + str(d + 1)


def _spell_from_root(pc: int, root_sp: tuple, key: str) -> str:
    """A chord tone spelled by its letter distance from the root (Abm's 3rd is Cb, not B), unless that needs a double
    accidental."""
    letter = (root_sp[0] + LETTER_STEPS[(pc - _sp_pc(root_sp)) % 12]) % 7
    acc = _signed(pc - LETTER_PC[letter])
    return _sp_name((letter, acc)) if abs(acc) <= 1 else pc_name(pc, key)


def key_scale(key: str, wide_minor: bool = False) -> set:
    """Pitch classes of a key's scale: major, or natural minor (with wide_minor, harmonic and melodic minor too)."""
    k = nashville.parse_key(key)
    steps = SCALES["major"] if k["mode"] == "major" else (
        SCALES["natural minor"] | SCALES["harmonic minor"] | SCALES["melodic minor"] if wide_minor
        else SCALES["natural minor"])
    return {(k["tonic"] + i) % 12 for i in steps}


def outside_notes(w: dict, key: str) -> List[dict]:
    """The chord's notes that the key lacks, each with its degree in the key: [{note, degree}]."""
    scale = key_scale(key, wide_minor=True)
    p = _parts(w)
    tonic = nashville.parse_key(key)["tonic"]
    out = []
    for pc in sorted(set(_row_pcs(w)), key=lambda x: (x - tonic) % 12):
        if pc not in scale:
            name = _spell_from_root(pc, p["root"], key) if p else pc_name(pc, key)
            out.append({"note": name, "degree": _degree(pc, key, name)})
    return out


def _key_tag(key: Optional[str], home: Optional[str]) -> str:
    return "" if not key or key == home else f" in {key}"


# ----------------------------------------------------------------------------------------------- chords
def vocabulary(doc: dict, min_seconds: float = 0.0) -> dict:
    """Chords by time: letters (with their number and class in each key area they sounded in), and numbers without
    the bass across every key area."""
    home = doc.get("home_key")
    chords = [w for w in doc["windows"] if is_chord(w) and w["seconds"] >= min_seconds]
    other = sum(w["seconds"] for w in doc["windows"] if not is_chord(w))
    total = sum(w["seconds"] for w in chords)
    by_name: Dict[str, dict] = {}
    by_number: Dict[str, dict] = {}
    classes: Dict[str, float] = {}
    for w in chords:
        label = w.get("label") or w["analysed_as"]
        slot = by_name.setdefault(label, {"chord": label, "seconds": 0.0, "times": 0,
                                                     "first_at": w["at"], "first_ms": w["start_ms"], "reading": False,
                                                     "in": []})
        slot["seconds"] += w["seconds"]
        slot["times"] += 1
        slot["reading"] = slot["reading"] or w["analysed_from"] == "reading"
        place = next((p for p in slot["in"] if p["key"] == w["key"]), None)
        if not place:
            place = {"key": w["key"], "number": w["number"], "class": w["class"], "detail": w["class_detail"]}
            slot["in"].append(place)
        num = harmony_number(w) or "(no number)"
        ns = by_number.setdefault(num, {"number": num, "seconds": 0.0, "times": 0, "first_at": w["at"],
                                        "first_ms": w["start_ms"], "chords": []})
        ns["seconds"] += w["seconds"]
        ns["times"] += 1
        if harmony_name(w) not in ns["chords"]:
            ns["chords"].append(harmony_name(w))
        classes[w["class"]] = classes.get(w["class"], 0.0) + w["seconds"]

    def rows(d):
        out = sorted(d.values(), key=lambda s: (-s["seconds"], s["first_ms"]))
        for s in out:
            s["share"] = _r(s["seconds"] / total, 3) if total else None
            s["seconds"] = _r(s["seconds"], 2)
        return out
    return {"home_key": home, "min_seconds": min_seconds, "chord_seconds": _r(total, 1), "chord_windows": len(chords),
            "other_seconds": _r(other, 1),
            "classes": {c: _r(s / total, 3) for c, s in sorted(classes.items(), key=lambda kv: -kv[1])} if total else {},
            "chords": rows(by_name), "numbers": rows(by_number)}


def render_chords(sess: dict, data: dict) -> str:
    lines = [headline(sess), ""]
    if not sess["doc"]["notes"]:
        return "\n".join(lines + ["No notes logged yet."])
    home = data["home_key"]
    held = f"; chords held at least {data['min_seconds']} s" if data["min_seconds"] else ""
    lines += [f"Chords by time (home key {home}; numbers are in each chord's own key area{held})",
              f"{data['chord_seconds']} s of chords in {data['chord_windows']} harmonies; {data['other_seconds']} s "
              f"more of single notes, two-note shapes, lines and broken chords (notes never held together)."]
    if not data["chords"]:
        return "\n".join(lines + ["No chords held."])
    lines.append("Chord time by class: " + ", ".join(f"{c} {_pct(s)}" for c, s in data["classes"].items()) + ".")
    lines += ["", f"{'secs':>6} {'share':>5} {'times':>5} {'first':>5}  {'chord':<24} number and class"]
    for c in data["chords"]:
        places = "; ".join(f"{p['number'] or '-'}{_key_tag(p['key'], home)} {p['class']}" for p in c["in"])
        name = c["chord"] + (" ~" if c["reading"] else "")
        lines.append(f"{c['seconds']:>6.1f} {_pct(c['share']):>5} {c['times']:>5} {c['first_at']:>5}  {name:<24} "
                     f"{places}")
    lines += ["", "By number (bass left out; every key area together):"]
    for n in data["numbers"][:24]:
        lines.append(f"{n['seconds']:>6.1f} {_pct(n['share']):>5} {n['times']:>5} {n['first_at']:>5}  "
                     f"{n['number']:<18} {', '.join(n['chords'][:5])}")
    if any(c["reading"] for c in data["chords"]):
        lines.append("\n~ marks a reading.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------- progressions
SAME_HARMONY_OVERLAP = 0.75   # neighbouring chords sharing this much of the smaller chord's notes may be one harmony...
SAME_HARMONY_MAX_PCS = 5      # ...over a new bass only when both hold at most this many pitch classes (a pedal wash holds
                              # nearly every chord of the key, so over a new bass it is a new chord)...
SAME_HARMONY_SHORT_MS = 1000  # ...or when the new bass is shorter than this, on a note the chord already holds
SAME_HARMONY_MAX_MS = 10000   # a step merged from different chords spans at most this long


def _bass_pc_of(w: dict) -> Optional[int]:
    sp = _parse_name(re.sub(r"-?\d+$", "", w["bass"]["note"] or ""))
    return _sp_pc(sp) if sp else None


def _root_pc_of(w: dict) -> Optional[int]:
    p = _parts(w)
    return _sp_pc(p["root"]) if p else None


def same_harmony(a: dict, b: dict, roots=None) -> bool:
    """Whether chord b goes on with the harmony of chord a (roots: the analysed roots of the step a belongs to; a's own
    root by default):
    - over the same bass, with most notes shared: Fm(add9)/F -> Abmaj13/F, Fm7/Ab -> Ab6;
    - over a new bass, between chords of at most SAME_HARMONY_MAX_PCS pitch classes, when b's root already is the step's
      root (an inversion, or the bass leaving one: Bb -> Bb/D, Abmaj13/F -> Fm9/Ab);
    - or a bass note shorter than SAME_HARMONY_SHORT_MS on a note the chord already holds.
    A bass moving to a new chord's own root is a change (Cm over C -> Ebmaj7 over Eb -> Gm over G)."""
    pa, pb = set(_row_pcs(a)), set(_row_pcs(b))
    ba, bb = _bass_pc_of(a), _bass_pc_of(b)
    if not pa or not pb or ba is None or bb is None:
        return False
    overlap = len(pa & pb) / max(len(pa), len(pb))
    if not (overlap >= SAME_HARMONY_OVERLAP or pa <= pb or pb <= pa):
        return False
    if ba == bb:
        return True
    if (b.get("seconds") or 0) * 1000 < SAME_HARMONY_SHORT_MS and b.get("seconds") and bb in pa and pb <= pa | {bb}:
        return True
    if len(pa) > SAME_HARMONY_MAX_PCS or len(pb) > SAME_HARMONY_MAX_PCS:
        return False
    ra, rb = _root_pc_of(a), _root_pc_of(b)
    known = set(roots) if roots is not None else ({ra} if ra is not None else set())
    return rb is not None and rb in known


def is_harmony(w: dict) -> bool:
    """A chord that can be a step of a progression: over a low bass, or with three or more notes struck together. A
    melody played by the right hand alone, however the pedal rings it, is not."""
    return bool((w.get("bass") or {}).get("low", True) or (w.get("struck_together") or 0) >= 3)


def chord_sequences(doc: dict, exact: bool = False, min_seconds: float = PROG_MIN_S) -> List[List[dict]]:
    """Runs of chords (is_harmony) in time order, each chord a token (its number, or only its quality unless exact).
    Neighbouring chords with the same token, or that go on with one harmony (same_harmony, against every root of the
    step so far), merge into one step named by the token held longest, at that token's first time; a step merged from
    different chords spans at most SAME_HARMONY_MAX_MS. A gap over PROG_GAP_MS or a change of key area starts a new
    run."""
    seqs: List[List[dict]] = []
    cur: List[dict] = []
    last = None
    for w in doc["windows"]:
        if not is_chord(w) or w["seconds"] < min_seconds or not is_harmony(w):
            continue
        if w.get("heard_as"):  # a 4 chord's notes that are the 5 chord over the 4 bass move as the 5 chord
            w = {**w, "analysed_as": w["heard_as"]["name"], "label": w["heard_as"]["name"]}
        token = harmony_number(w) if exact else core_number(w)
        if token is None:
            continue
        if last is not None and (w["start_ms"] - last["end_ms"] > PROG_GAP_MS or w["key"] != last["key"]) and cur:
            seqs.append(cur)
            cur = []
        chord = w.get("label") or w["analysed_as"]
        root = _root_pc_of(w)
        on_root = root is not None and root == _bass_pc_of(w)  # a chord over its own root establishes that root
        step = cur[-1] if cur else None
        same_bass = step is not None and _bass_pc_of(step["_last"]) == _bass_pc_of(w)
        going_on = step is not None and same_harmony(step["_last"], w, step["_roots"])
        if step and ((token == step["_last_token"] and (same_bass or going_on)) or
                     (going_on and w["end_ms"] - step["start_ms"] <= SAME_HARMONY_MAX_MS)):
            step["end_ms"] = w["end_ms"]
            step["_time"][token] = step["_time"].get(token, 0.0) + w["seconds"]
            step["_first"].setdefault(token, (chord, w["at"], w["start_ms"]))
            step["_last"], step["_last_token"] = w, token
            if on_root:
                step["_roots"].add(root)
        else:
            cur.append({"token": token, "start_ms": w["start_ms"], "end_ms": w["end_ms"], "key": w["key"],
                        "_time": {token: w["seconds"]}, "_first": {token: (chord, w["at"], w["start_ms"])},
                        "_last": w, "_last_token": token, "_roots": {root} if root is not None else set()})
        last = w
    if cur:
        seqs.append(cur)
    out = []
    for seq in seqs:
        steps: List[dict] = []
        for step in seq:
            token = max(step["_time"], key=lambda t: step["_time"][t])
            chord, at, start = step["_first"][token]
            if steps and steps[-1]["token"] == token:
                steps[-1]["end_ms"] = step["end_ms"]
                continue
            steps.append({"token": token, "chord": chord, "at": at, "start_ms": start, "span_start_ms": step["start_ms"],
                          "end_ms": step["end_ms"], "key": step["key"],
                          "merged": sorted(step["_time"], key=lambda t: -step["_time"][t])})
        out.append(steps)
    return out


def find_loops(seqs: List[List[dict]]) -> List[dict]:
    """Cycles of 2 to 4 chords played back to back at least twice, grouped by rotation."""
    found: Dict[tuple, dict] = {}
    for seq in seqs:
        toks = [x["token"] for x in seq]
        i = 0
        while i < len(toks):
            hit = None
            for size in (2, 3, 4):
                cyc = toks[i:i + size]
                if len(cyc) < size or cyc[0] == cyc[-1] or len(set(cyc)) < 2 or \
                        (size == 4 and cyc[:2] == cyc[2:]):
                    continue
                reps = 1
                while toks[i + reps * size:i + (reps + 1) * size] == cyc:
                    reps += 1
                if reps >= 2:
                    hit = (size, reps, cyc)
                    break
            if not hit:
                i += 1
                continue
            size, reps, cyc = hit
            canon = min(tuple(cyc[k:] + cyc[:k]) for k in range(size))
            slot = found.setdefault(canon, {"numbers": cyc, "chords": [x["chord"] for x in seq[i:i + size]],
                                            "key": seq[i]["key"], "first_at": seq[i]["at"],
                                            "first_ms": seq[i]["start_ms"], "best_reps": 0, "runs": []})
            slot["best_reps"] = max(slot["best_reps"], reps)
            slot["runs"].append({"at": seq[i]["at"], "start_ms": seq[i]["start_ms"], "reps": reps,
                                 "seconds": _r((seq[i + reps * size - 1]["end_ms"] - seq[i]["start_ms"]) / 1000, 1)})
            i += reps * size
    return sorted(found.values(), key=lambda s: (-s["best_reps"] * len(s["numbers"]), s["first_ms"]))


def progression_data(doc: dict, ns=(2, 3, 4), min_count: int = 2, exact: bool = False) -> dict:
    seqs = chord_sequences(doc, exact) if doc["notes"] else []
    moves: Dict[str, List[dict]] = {}
    for n in ns:
        grams: Dict[tuple, dict] = {}
        for seq in seqs:
            for i in range(len(seq) - n + 1):
                part = seq[i:i + n]
                g = grams.setdefault(tuple(x["token"] for x in part),
                                     {"numbers": [x["token"] for x in part], "count": 0, "first_at": part[0]["at"],
                                      "first_ms": part[0]["start_ms"], "chords": [x["chord"] for x in part],
                                      "key": part[0]["key"], "keys": []})
                g["count"] += 1
                if part[0]["key"] not in g["keys"]:
                    g["keys"].append(part[0]["key"])
        moves[str(n)] = sorted((g for g in grams.values() if g["count"] >= min_count),
                               key=lambda g: (-g["count"], g["first_ms"]))
    return {"home_key": doc["home_key"] if doc["notes"] else None, "level": "exact" if exact else "quality",
            "min_count": min_count, "min_seconds": PROG_MIN_S, "sequences": len(seqs),
            "chords": sum(len(s) for s in seqs), "moves": moves, "loops": find_loops(seqs)}


def render_progressions(sess: dict, data: dict) -> str:
    lines = [headline(sess), ""]
    if not sess["doc"]["notes"]:
        return "\n".join(lines + ["No notes logged yet."])
    home = data["home_key"]
    level = "full numbers, bass left out" if data["level"] == "exact" else \
        "numbers with quality only: m minor, sus suspended, ° diminished, + augmented, ^5 power chord"
    lines += [f"Moves and loops ({level}; each in its own key area, home key {home})",
              f"{data['chords']} chords held {data['min_seconds']} s or more (repeats merged), in {data['sequences']} runs "
              f"(a gap over {PROG_GAP_MS // 1000} s or a key change starts a new run; arpeggios already merged)."]
    for n, rows in data["moves"].items():
        lines += ["", f"{n}-chord moves played at least {data['min_count']} times ({len(rows)}):"]
        for g in rows[:15]:
            lines.append(f"{g['count']:>4}x  first {g['first_at']:>5}  {' -> '.join(g['numbers']):<30} "
                         f"{' -> '.join(g['chords'])}{_key_tag(g['key'], home)}")
        if len(rows) > 15:
            lines.append(f"      ({len(rows) - 15} more)")
        if not rows:
            lines.append("  none")
    lines += ["", "Loops (the same chords cycled back to back):"]
    for loop in data["loops"][:10]:
        runs = ", ".join(f"{r['at']} x{r['reps']}" for r in loop["runs"][:6])
        lines.append(f"  {' -> '.join(loop['numbers'])} (and round again): up to {loop['best_reps']} times; runs at "
                     f"{runs}; e.g. {' -> '.join(loop['chords'])}{_key_tag(loop['key'], home)}")
    if not data["loops"]:
        lines.append("  none")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------ keys
def pc_profile(heard_pc: List[List[list]], a: float, b: float) -> List[float]:
    ms = [_overlap(iv, a, b) for iv in heard_pc]
    total = sum(ms)
    return [m / total if total else 0.0 for m in ms]


def _chord_ref(w: Optional[dict]) -> Optional[dict]:
    return w and {"at": w["at"], "chord": w.get("label") or w["analysed_as"], "number": w["number"], "key": w["key"]}


KEY_MOVE_SHARE = 0.03   # a note the two keys disagree on 'fades out' or 'comes in' when its share moves this much
KEY_STAY_SHARE = 0.02   # ...and 'still sounds' after the change when it keeps at least this share
RETURN_MIN_MS = 4000    # chords with the parallel key's 3rd (and not the area's own) this long in a row: the mode flips back


def _parallel_returns(area: dict, windows: List[dict]) -> List[dict]:
    """Stretches inside a key area where the parallel mode comes back: consecutive windows (chords or two-note shapes)
    holding the parallel key's 3rd and not the area's own 3rd, lasting RETURN_MIN_MS."""
    k = nashville.parse_key(area["key"])
    own, other = ((k["tonic"] + 3) % 12, (k["tonic"] + 4) % 12) if k["mode"] == "minor" else \
        ((k["tonic"] + 4) % 12, (k["tonic"] + 3) % 12)
    out, run = [], []
    inside = [w for w in windows if area["start_ms"] <= (w["start_ms"] + w["end_ms"]) / 2 < area["end_ms"]
              and len(w["pcs"]) >= 2]

    def flush():
        if run and run[-1]["end_ms"] - run[0]["start_ms"] >= RETURN_MIN_MS and any(is_chord(w) for w in run):
            out.append({"at": run[0]["at"], "until": clock(run[-1]["end_ms"]), "start_ms": run[0]["start_ms"],
                        "seconds": _r((run[-1]["end_ms"] - run[0]["start_ms"]) / 1000, 1),
                        "chords": [w.get("label") or w["analysed_as"] or w["name"] for w in run]})
    for w in inside:
        pcs = set(_row_pcs(w))
        if other in pcs and own not in pcs and (not run or w["start_ms"] - run[-1]["end_ms"] <= CADENCE_GAP_MS):
            run.append(w)
            continue
        flush()
        run = [w] if other in pcs and own not in pcs else []
    flush()
    return out


def key_evidence(doc: dict, snd: dict) -> dict:
    """Per key area: its most heard notes, notes outside its scale, top chords. Per key change: the notes the two keys
    disagree on, heard before and after (EVIDENCE_MS either side), and the chords on either side."""
    if not doc["notes"]:
        return {"areas": [], "changes": []}
    heard_pc, _ = _heard(snd["notes"])
    areas, windows = doc["keys"]["areas"], doc["windows"]
    rows, changes = [], []
    for a in areas:
        key = a["key"]
        prof = pc_profile(heard_pc, a["start_ms"], a["end_ms"])
        scale = key_scale(key)
        k = nashville.parse_key(key)
        inside = [w for w in windows if a["start_ms"] <= (w["start_ms"] + w["end_ms"]) / 2 < a["end_ms"]]
        voc = vocabulary({"home_key": doc["home_key"], "windows": inside})
        ru = a["runner_up"]
        row = {"key": key, "at": a["at"], "until": a["until"], "start_ms": a["start_ms"], "end_ms": a["end_ms"],
               "seconds": a["seconds"], "relation": a["relation"], "score": a["score"], "r": a["r"], "runner_up": ru,
               "close_call": bool(ru and a["score"] is not None and 0 <= a["score"] - ru["score"] <= KEY_CLOSE),
               "most_heard": [[pc_name(pc, key), _r(prof[pc], 3)]
                              for pc in sorted(range(12), key=lambda p: -prof[p])[:6] if prof[pc] > 0],
               "outside_scale": [[pc_name(pc, key), _degree(pc, key), _r(prof[pc], 3)]
                                 for pc in sorted(range(12), key=lambda p: -prof[p])
                                 if pc not in scale and prof[pc] >= 0.03],
               "chords": [[c["chord"], c["in"][0]["number"], c["seconds"]] for c in voc["chords"][:5]]}
        if k["mode"] == "minor":
            lt = (k["tonic"] + 11) % 12
            row["raised_7th"] = [pc_name(lt, key), _r(prof[lt], 3)]
        row["returns"] = _parallel_returns(a, windows)
        row["after_pause_s"] = a.get("after_pause_s")
        rows.append(row)
    for prev, nxt in zip(areas, areas[1:]):
        t = nxt["start_ms"]
        before = pc_profile(heard_pc, max(prev["start_ms"], min(t, prev["end_ms"]) - EVIDENCE_MS), prev["end_ms"])
        after = pc_profile(heard_pc, t, min(nxt["end_ms"], t + EVIDENCE_MS))
        sa, sb = key_scale(prev["key"]), key_scale(nxt["key"])
        tonic = nashville.parse_key(prev["key"])["tonic"]
        swapped = []
        for pc in sorted(sa ^ sb, key=lambda p: (p not in sa, (p - tonic) % 12)):
            owner = prev["key"] if pc in sa else nxt["key"]
            swapped.append({"note": pc_name(pc, owner), "belongs_to": owner, "before": _r(before[pc], 3),
                            "after": _r(after[pc], 3),
                            "as_expected": before[pc] > after[pc] if pc in sa else after[pc] > before[pc]})
        other = [{"note": pc_name(pc, nxt["key"]), "before": _r(before[pc], 3), "after": _r(after[pc], 3)}
                 for pc in range(12) if pc not in sa ^ sb and abs(after[pc] - before[pc]) >= EVIDENCE_OTHER_SHARE]
        last = [w for w in windows if is_chord(w) and prev["start_ms"] <= w["start_ms"] < min(t, prev["end_ms"])]
        first = [w for w in windows if is_chord(w) and w["start_ms"] >= t - 500 and w["key"] == nxt["key"]]
        old_scale = key_scale(prev["key"], wide_minor=True)
        arrival = next((w for w in first if w["start_ms"] < t + EVIDENCE_MS and w["class"] == "diatonic"
                        and not set(_row_pcs(w)) <= old_scale), None)  # the first chord that belongs to the new key
        first = [arrival] if arrival else first                        # only (not the old tonic heard over a new bass)
        nk = nashville.parse_key(nxt["key"])
        gone = [s["note"] for s in swapped if s["belongs_to"] == prev["key"] and s["before"] - s["after"] >= KEY_MOVE_SHARE
                and s["after"] < KEY_STAY_SHARE]
        arrived = [s["note"] for s in swapped if s["belongs_to"] == nxt["key"] and
                   s["after"] - s["before"] >= KEY_MOVE_SHARE]
        stayed = [s["note"] for s in swapped if s["belongs_to"] == prev["key"] and s["after"] >= KEY_STAY_SHARE]
        change = {"at": nxt["at"], "start_ms": t, "from": prev["key"], "to": nxt["key"],
                  "relation": nxt["relation"], "pause_s": nxt.get("after_pause_s"), "swapped": swapped,
                  "gone": gone, "arrived": arrived, "stayed": stayed}
        if nk["mode"] == "minor":
            lt = (nk["tonic"] + 11) % 12
            change["raised_7th"] = [pc_name(lt, prev["key"]), _r(before[lt], 3), _r(after[lt], 3)]
        changes.append({**change,
                        "agreeing": sum(1 for s in swapped if s["as_expected"]), "other": other,
                        "last_chord_before": _chord_ref(last[-1] if last else None),
                        "first_chord_after": _chord_ref(first[0] if first else None)})
    return {"areas": rows, "changes": changes}


def _change_notes(c: dict, limit: int = 4) -> str:
    moved = sorted((s for s in c["swapped"] if s["as_expected"]), key=lambda s: -abs(s["after"] - s["before"]))
    return ", ".join(f"{s['note']} {_pct(s['before'])} -> {_pct(s['after'])}" for s in moved[:limit])


def _ref_text(ref: Optional[dict], home: Optional[str] = None) -> str:
    if not ref:
        return "-"
    return f"{ref['chord']} ({ref['number'] or 'no number'}{_key_tag(ref['key'], home)})"


def render_keys(doc: dict, evidence: Optional[dict] = None) -> str:
    k = doc["keys"]
    lines = [f"Home key: {doc['home_key']} (the key with the most chord time)."]
    if k["estimate"]:
        e = k["estimate"]
        lines.append(f"Whole-session estimate (Krumhansl-Kessler, by heard time): {e['key']} (r {e['r']}), runner-up "
                     f"{e['runner_up']} (r {e['runner_up_r']}).")
    lines.append("Chord time by key: " + ", ".join(f"{key} {v['seconds']} s ({_pct(v['share'])})"
                                                   for key, v in k["chord_time_by_key"].items()) + ".")
    if evidence is None:
        lines += ["", f"{'from':>5} {'to':>5}  {'key':<10} {'relation':<28} {'secs':>6} {'score':>6}  runner-up"]
        for a in k["areas"]:
            ru = a["runner_up"]
            lines.append(f"{a['at']:>5} {a['until']:>5}  {a['key']:<10} {a['relation']:<28} {a['seconds']:>6} "
                         f"{a['score'] if a['score'] is not None else '-':>6}  "
                         f"{ru['key'] + ' ' + str(ru['score']) if ru else '-'}")
    else:
        changes = {c["start_ms"]: c for c in evidence["changes"]}
        lines += ["", "Key areas, with the evidence for each change:"]
        for n, a in enumerate(evidence["areas"]):
            c = changes.get(a["start_ms"]) if n else None
            if c:
                agree = f"{c['agreeing']} of {len(c['swapped'])} notes that differ moved the new key's way"
                lines += ["", f"{c['at']}  " + (f"new section after a {c['pause_s']} s pause: " if c.get("pause_s")
                                                else "key change: ") + f"{c['from']} -> {c['to']}"]
                if c["swapped"]:
                    lines += _wrap(f"    notes the keys disagree on (share of heard time, {EVIDENCE_MS // 1000} s "
                                   f"before -> after): ",
                                   [f"{s['note']} ({s['belongs_to']}) {_pct(s['before'])} -> {_pct(s['after'])}"
                                    for s in c["swapped"]], sep=", ", indent="      ")
                    lines.append(f"      {agree}")
                else:
                    lines.append("    the two keys share every note: only the home note moved")
                if c["other"]:
                    lines.append("    other notes that changed: " + ", ".join(
                        f"{o['note']} {_pct(o['before'])} -> {_pct(o['after'])}" for o in c["other"]))
                lines.append(f"    last chord before: {c['last_chord_before']['at'] + ' ' if c['last_chord_before'] else ''}"
                             f"{_ref_text(c['last_chord_before'])}; first after: "
                             f"{c['first_chord_after']['at'] + ' ' if c['first_chord_after'] else ''}"
                             f"{_ref_text(c['first_chord_after'])}")
            ru = a["runner_up"]
            lines += ["", f"{a['at']}-{a['until']}  {a['key']} ({a['relation']}), {a['seconds']} s; score "
                          f"{a['score']}" + (f", runner-up {ru['key']} {ru['score']}" if ru else "") +
                      (" (a close call)" if a["close_call"] else "")]
            lines.append("    most heard: " + ", ".join(f"{name} {_pct(s)}" for name, s in a["most_heard"]))
            if a["outside_scale"]:
                lines.append("    outside its scale: " + ", ".join(f"{name} ({deg}) {_pct(s)}"
                                                                   for name, deg, s in a["outside_scale"]))
            if a.get("raised_7th"):
                lines.append(f"    raised 7th {a['raised_7th'][0]}: {_pct(a['raised_7th'][1])} of heard time")
            for ret in a.get("returns", []):
                lines.append(f"    {ret['at']}-{ret['until']}: the parallel mode's 3rd comes back ({ret['seconds']} s: "
                             f"{', '.join(ret['chords'][:4])})")
            if a["chords"]:
                lines.append("    top chords: " + ", ".join(f"{name} {num or '-'} {secs} s" for name, num, secs in a["chords"]))
    if k["absorbed"]:
        lines += ["", "Read by pitch content but not kept as key areas:"]
        lines += [f"- {a['at']} to {a['until']}: {a['key']} -> {a['into']} ({a['why']})" for a in k["absorbed"]]
    return "\n".join(lines)


# -------------------------------------------------------------------------------------------- borrowed
def borrowed_data(doc: dict) -> dict:
    """Chords of three or more notes outside their key area's key, with their source and the notes that are outside;
    and, for key areas away from home, the chords that are outside the home key."""
    local, home_view = [], []
    for w in doc["windows"] if doc["notes"] else []:
        if not is_chord(w) or len(w["pcs"]) < 3:
            continue
        if w["class"] not in NON_CHORD_CLASSES:
            h = w.get("in_home_key")
            local.append({"at": w["at"], "start_ms": w["start_ms"], "seconds": w["seconds"],
                          "chord": w.get("label") or w["analysed_as"],
                          "number": w["number"], "key": w["key"], "class": w["class"], "source": w["class_detail"],
                          "outside_notes": outside_notes(w, w["key"]), "on_bass_line": w.get("on_bass_line"),
                          "in_home_class": h["class"] if h else None, "root": w.get("root"),
                          "light_notes": w.get("light_notes") or []})
        h = w.get("in_home_key")
        if h and h["class"] not in NON_CHORD_CLASSES:
            home_view.append({"at": w["at"], "start_ms": w["start_ms"], "seconds": w["seconds"],
                              "chord": h["name"] or w["analysed_as"], "number": h["number"], "key": h["key"],
                              "class": h["class"], "source": h["detail"], "area_key": w["key"],
                              "outside_notes": outside_notes(w, h["key"])})

    def group(moments):  # the times a chord rides a bass line make a group of their own (on_bass_line: that line)
        groups: Dict[tuple, dict] = {}
        for m in moments:
            g = groups.setdefault((m["chord"], m["number"], m["key"], m["class"], m["source"], bool(m.get("on_bass_line"))),
                                  {k: m[k] for k in ("chord", "number", "key", "class", "source", "outside_notes")} |
                                  {"times": [], "seconds": 0.0, "first_ms": m["start_ms"], "longest": None,
                                   "on_bass_line": m.get("on_bass_line")})
            g["times"].append(m["at"])
            g["seconds"] = _r(g["seconds"] + m["seconds"], 2)
            if not g["longest"] or m["seconds"] > g["longest"]["seconds"]:
                g["longest"] = {"at": m["at"], "start_ms": m["start_ms"], "seconds": m["seconds"]}
        return sorted(groups.values(), key=lambda g: g["first_ms"])
    by_class: Dict[str, float] = {}
    for m in local:
        by_class[m["class"]] = _r(by_class.get(m["class"], 0.0) + m["seconds"], 2)
    return {"home_key": doc["home_key"] if doc["notes"] else None, "moments": local, "groups": group(local),
            "from_home": group(home_view), "seconds_by_class": by_class}


def _notes_text(notes: List[dict]) -> str:
    return ", ".join(f"{n['note']} ({n['degree']})" for n in notes) or "none (only its chord shape)"


def render_borrowed(sess: dict, data: dict) -> str:
    lines = [headline(sess), ""]
    if not sess["doc"]["notes"]:
        return "\n".join(lines + ["No notes logged yet."])
    home = data["home_key"]
    lines.append(f"Outside the key (chords of three or more notes; each number is in the chord's own key area, home "
                 f"key {home})")
    titles = (("borrowed", "Borrowed from the parallel key"), ("modal", "Modal colour"),
              ("secondary dominant", "Secondary dominants"), ("chromatic", "Chromatic"))
    for cls, title in titles:
        groups = [g for g in data["groups"] if g["class"] == cls]
        if not groups:
            continue
        lines += ["", f"{title} ({sum(g['seconds'] for g in groups):.1f} s):"]
        for g in groups:
            times = ", ".join(g["times"][:8]) + (" ..." if len(g["times"]) > 8 else "")
            lines.append(f"  {g['chord']} = {g['number'] or 'no number'}{_key_tag(g['key'], home) or ' in ' + g['key']}, "
                         f"{g['seconds']} s at {times}: {g['source']}; outside notes {_notes_text(g['outside_notes'])}"
                         + (f" (riding the bass line at {g['on_bass_line']})" if g.get("on_bass_line") else ""))
    if not data["groups"]:
        lines += ["", "Every chord of three or more notes is inside its key area's key."]
    if data["from_home"]:
        lines += ["", f"Heard from the home key ({home}), in key areas away from home:"]
        for g in sorted(data["from_home"], key=lambda g: -g["seconds"])[:20]:
            times = ", ".join(g["times"][:6]) + (" ..." if len(g["times"]) > 6 else "")
            lines.append(f"  {g['chord']} = {g['number'] or 'no number'}, {g['seconds']} s at {times}: {g['class']}, "
                         f"{g['source']}; outside notes {_notes_text(g['outside_notes'])}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------- colours
def colour_tags(w: dict) -> List[str]:
    """What the sounding notes add to a chord, measured from its analysed root (COLOUR_ORDER names)."""
    p = _parts(w)
    if not p:
        return []
    root = _sp_pc(p["root"])
    rel = {(pc - root) % 12 for pc in _row_pcs(w)}
    if rel == {0, 7}:
        return ["power chord (root and 5th)"]
    maj3, has3 = 4 in rel, 3 in rel or 4 in rel
    seventh = 10 in rel or 11 in rel
    tags = []
    if not has3 and "sus" not in p["suffix"]:
        tags.append("no 3rd")  # a chord named major or minor whose 3rd is not sounding: open, not suspended
        if 2 in rel:
            tags.append("9" if seventh else "add9")
        if 5 in rel:
            tags.append("11")
    elif not has3:
        if "sus4" in p["suffix"] or ("sus2" not in p["suffix"] and 5 in rel):
            tags.append("sus4")  # Ebsus4(9): a sus4 with a 9th, not also a sus2
            if 2 in rel:
                tags.append("9" if seventh else "add9")
        elif 2 in rel:
            tags.append("sus2")
            if 5 in rel:
                tags.append("11")
        else:
            tags.append("no 3rd")
    elif rel <= {0, 3, 4, 7}:
        tags.append("plain triad")
    else:
        if 2 in rel:
            tags.append("9" if seventh else "add9")
        if 5 in rel:
            tags.append("11")
    if 9 in rel:
        tags.append("13" if seventh else "6")
    if 11 in rel:
        tags.append("maj7")
    if 10 in rel:
        tags.append("b7 (plain 7th)")
    if 6 in rel and (7 in rel or maj3 or not has3):
        tags.append("#11")
    elif 6 in rel:
        tags.append("b5 (diminished)")
    if 1 in rel or (3 in rel and maj3) or (8 in rel and 7 in rel):
        tags.append("altered (b9, #9, b13)")
    elif 8 in rel and maj3:
        tags.append("#5 (augmented)")
    bass = _parse_name(w["bass"]["note"] or "")
    if bass and _sp_pc(bass) != root:
        iv = (_sp_pc(bass) - root) % 12
        tags.append("inversion (3rd, 5th or 7th in the bass)" if iv in (3, 4, 7, 10, 11)
                    else "other bass note (not a chord tone)")
    return sorted(set(tags), key=COLOUR_ORDER.index)


def colour_data(doc: dict) -> dict:
    chords = [w for w in doc["windows"] if is_chord(w)] if doc["notes"] else []
    total = sum(w["seconds"] for w in chords)
    tags: Dict[str, dict] = {}
    for w in chords:
        for tag in colour_tags(w):
            slot = tags.setdefault(tag, {"colour": tag, "seconds": 0.0, "windows": 0, "first_at": w["at"], "chords": {}})
            slot["seconds"] += w["seconds"]
            slot["windows"] += 1
            label = w.get("label") or w["analysed_as"]
            slot["chords"][label] = slot["chords"].get(label, 0.0) + w["seconds"]
    rows = []
    for tag in COLOUR_ORDER:
        if tag in tags:
            s = tags[tag]
            rows.append({"colour": tag, "seconds": _r(s["seconds"], 1), "share": _r(s["seconds"] / total, 3),
                         "windows": s["windows"], "first_at": s["first_at"],
                         "top": [[c, _r(sec, 1)] for c, sec in sorted(s["chords"].items(), key=lambda kv: -kv[1])[:5]]})
    f = doc["findings"] if doc["notes"] else {"lydian_4": [], "dominants": {"summary": {}, "windows": [],
                                                                         "two_note_shapes_on_5": {"windows": 0}},
                                              "pedal_points": [], "suspensions": [], "colour_additions": []}
    tw = total or 1.0
    return {"chord_seconds": _r(total, 1), "colours": rows, "lydian_4": f["lydian_4"], "dominants": f["dominants"],
            "pedal_points": f["pedal_points"], "suspensions": f["suspensions"],
            "colour_additions": f["colour_additions"],
            "voicing": {"mean_notes": _r(sum(w["voicing"]["distinct_notes"] * w["seconds"] for w in chords) / tw, 1),
                        "mean_spread": _r(sum(w["voicing"]["spread"] * w["seconds"] for w in chords) / tw, 1),
                        "wide_share": _r(sum(w["seconds"] for w in chords if w["voicing"]["spread"] >= WIDE_SPREAD) / tw,
                                         2)} if chords else None}


def _dominant_lines(dom: dict, home: Optional[str] = None, split: bool = False, top_n: int = 3) -> List[str]:
    """Per key area: each form of the 5 chord, how long it sat over its own root, and over which other bass notes (a 5
    shape over the 1 or 4 in the bass is heard as that bass's chord first). split: one item per key area and form."""
    out = []
    by_key = dom.get("by_key") or {}
    for key in sorted(by_key, key=lambda k: (k != home, -sum(s["seconds"] for s in by_key[k].values()))):
        parts = []
        for form, s in sorted(by_key[key].items(), key=lambda kv: -kv[1]["seconds"]):
            top = ", ".join(f"{c} {sec} s" for c, sec in sorted(s["chords"].items(), key=lambda kv: -kv[1])[:top_n])
            over = [f"over its root {s['over_root_s']} s"] if s["over_root_s"] else []
            over += [f"over {deg} {sec} s" for deg, sec in sorted(s["over"].items(), key=lambda kv: -kv[1])]
            parts.append(f"{form}: {s['windows']} chord{'s' if s['windows'] != 1 else ''}, {s['seconds']} s "
                         f"({'; '.join(over)}: {top})")
        if split:
            out += [f"in {key}, {p}" for p in parts]
        else:
            out.append(f"in {key}: " + "; ".join(parts))
    return out


def render_colors(sess: dict, data: dict) -> str:
    lines = [headline(sess), ""]
    if not sess["doc"]["notes"]:
        return "\n".join(lines + ["No notes logged yet."])
    lines.append(f"Colour habits (share of {data['chord_seconds']} s of chords; a chord can count under several colours)")
    if data["colours"]:
        lines += ["", f"{'share':>5} {'secs':>6} {'chords':>6}  {'colour':<40} most played"]
        for c in data["colours"]:
            lines.append(f"{_pct(c['share']):>5} {c['seconds']:>6.1f} {c['windows']:>6}  {c['colour']:<40} "
                         f"{', '.join(f'{n} {s} s' for n, s in c['top'])}")
    else:
        lines.append("No chords held.")
    v = data["voicing"]
    if v:
        lines += ["", f"Voicing: chords average {v['mean_notes']} different notes over {v['mean_spread']} semitones; "
                      f"{_pct(v['wide_share'])} of chord time spans two octaves or more."]
    lyd = data["lydian_4"]
    lines += ["", f"Lydian 4 (the 4 chord with its #11): {len(lyd)} times, {sum(m['seconds'] for m in lyd):.1f} s"]
    lines += [f"  {m['at']} {m['analysed_as']} = {m['number']} in {m['key']}, {m['seconds']} s" + _page_said(m)
              for m in lyd]
    lines += ["", "Dominants (chords on 5):"]
    lines += [f"  {x}" for x in _dominant_lines(data["dominants"])] or ["  none"]
    sus = [d for d in data["dominants"]["windows"] if d["form"] == "suspended"]
    lines += [f"    suspended at {d['at']}: {d['label'] or d['analysed_as']} {d['seconds']} s in {d['key']} (bass "
              f"{d['bass']}, over {d['over']})" for d in sus[:10]]
    lines += ["", f"Pedal points ({len(data['pedal_points'])}; a low bass note sounding while the chords above change):"]
    lines += [f"  {p['at']} {p['bass']} sounds {p['seconds']} s: under {' -> '.join(p['over'])}"
              for p in sorted(data["pedal_points"], key=lambda p: -p["seconds"])] or ["  none"]
    resolving = sum(1 for s in data["suspensions"] if s.get("resolves"))
    lines += ["", f"Suspensions ({resolving} resolving, {len(data['suspensions']) - resolving} with the sus note "
                  f"kept):"]
    lines += [f"  {s['at']} {s['from']} -> {s['to']} ({' -> '.join(str(x) for x in s['numbers'])}): {s['note']}"
              for s in data["suspensions"]] or ["  none"]
    lines += ["", f"Colour additions ({len(data['colour_additions'])}):"]
    lines += [f"  {c['at']} {c['from']} -> {c['to']} (adds {', '.join(c['added'])})" for c in data["colour_additions"]] \
        or ["  none"]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------ touch
TOUCH_MIN_MS = 10000  # a session shorter than this has no notes-a-minute rate


def touch_data(doc: dict, snd: dict) -> Optional[dict]:
    notes = snd["notes"]
    if not notes:
        return None
    home = doc["home_key"]
    with_vel = [n for n in notes if n["vel"] is not None]
    vels = sorted(n["vel"] for n in with_vel)

    def q(p):
        return vels[min(len(vels) - 1, int(p * (len(vels) - 1) + 0.5))]
    buckets: Dict[int, List[float]] = {}
    for n in with_vel:
        buckets.setdefault(int(n["on_ms"] // 60000), []).append(n["vel"])
    minutes = max(1, math.ceil(snd["duration_ms"] / 60000))
    per_minute = [round(sum(buckets[m]) / len(buckets[m])) if m in buckets else None for m in range(min(minutes, 600))]
    loud = max(with_vel, key=lambda n: (n["vel"], -n["on_ms"])) if with_vel else None
    chords = [w for w in doc["windows"] if is_chord(w)]
    tw = sum(w["seconds"] for w in chords)
    wide = max((w for w in chords if w["seconds"] >= 1), key=lambda w: (w["voicing"]["spread"], -w["start_ms"]),
               default=None)
    low, high = min(n["note"] for n in notes), max(n["note"] for n in notes)
    return {"velocity": {"mean": round(sum(vels) / len(vels)), "p10": q(0.1), "p50": q(0.5), "p90": q(0.9),
                         "max": vels[-1], "loudest_at": clock_tenths(loud["on_ms"]), "per_minute": per_minute}
            if vels else None,
            "notes_per_minute": round(len(notes) / (snd["duration_ms"] / 60000))
            if snd["duration_ms"] >= TOUCH_MIN_MS else None,  # a rate over a few seconds means nothing
            "range": {"lowest": midi_name(low, home), "highest": midi_name(high, home), "semitones": high - low},
            "chords": {"mean_notes": _r(sum(w["voicing"]["distinct_notes"] * w["seconds"] for w in chords) / tw, 1),
                       "mean_spread": _r(sum(w["voicing"]["spread"] * w["seconds"] for w in chords) / tw, 1),
                       "widest": wide and {"at": wide["at"], "chord": wide["analysed_as"],
                                           "spread": wide["voicing"]["spread"], "lowest": wide["voicing"]["lowest"],
                                           "highest": wide["voicing"]["highest"]}} if tw else None,
            "pedal": doc["pedal"]}


def _touch_items(t: dict) -> List[str]:
    v, p = t["velocity"], t["pedal"]
    if v:
        per = v["per_minute"]
        items = [f"velocity mean {v['mean']} (middle 80% {v['p10']}-{v['p90']}, loudest {v['max']} at "
                 f"{v['loudest_at']}); mean by minute {' '.join(str(x) if x is not None else '-' for x in per[:20])}"
                 f"{' ...' if len(per) > 20 else ''}"]
    else:
        items = ["no velocities logged"]
    if p["presses"]:
        items.append(f"pedal down {p['percent_down']}%, {p['presses']} presses ({p['mean_down_s']} s each), "
                     f"{_pct(p['lifts_at_a_harmony_change'])} of lifts land on a harmony change")
    else:
        items.append("no pedal")
    items.append((f"{t['notes_per_minute']} notes a minute, " if t["notes_per_minute"] is not None else "") +
                 f"from {t['range']['lowest']} to {t['range']['highest']}")
    c = t["chords"]
    if c:
        wide = c["widest"]
        items.append(f"chords average {c['mean_notes']} notes over {c['mean_spread']} semitones" +
                     (f", widest {wide['spread']} at {wide['at']} ({wide['chord']}, {wide['lowest']} to "
                      f"{wide['highest']})" if wide else ""))
    return items


# ------------------------------------------------------------------------------------------------ moment
def moment_data(sess: dict, t_ms: float, half_ms: float) -> dict:
    doc, snd = sess["doc"], sess["snd"]
    lo, hi = max(0.0, t_ms - half_ms), t_ms + half_ms
    areas = doc["keys"]["areas"] if doc["notes"] else []
    area = _area_at(areas, t_ms)
    key = area["key"] if area else None
    windows = []
    for w in doc["windows"]:
        if w["end_ms"] > lo and w["start_ms"] < hi:
            windows.append({"at": w["at"], "until": clock(w["end_ms"]), "start_ms": w["start_ms"],
                            "seconds": w["seconds"], "chord": w["name"], "analysed_as": w["analysed_as"],
                            "label": w.get("label"), "texture": w.get("texture"),
                            "reading": w["reading"]["text"] if w["reading"] else None, "number": w["number"],
                            "key": w["key"], "class": w["class"], "detail": w["class_detail"], "pcs": w["pcs"],
                            "bass": w["bass"], "in_home_key": w.get("in_home_key"), "live": w["live"],
                            "merged_windows": w["merged_windows"], "heard_as": w.get("heard_as")})
    groups: List[dict] = []
    for n in sorted((n for n in snd["notes"] if lo <= n["on_ms"] < hi), key=lambda n: (n["on_ms"], n["note"])):
        if not groups or n["on_ms"] - groups[-1]["t_ms"] > ONSET_GROUP_MS:
            groups.append({"t_ms": n["on_ms"], "at": clock_tenths(n["on_ms"]), "notes": [], "vel": []})
        groups[-1]["notes"].append(n["note"])
        groups[-1]["vel"].append(n["vel"])
    for g in groups:
        order = sorted(range(len(g["notes"])), key=lambda i: g["notes"][i])
        g["notes"] = [midi_name(g["notes"][i], key) for i in order]
        g["vel"] = [min(g["vel"]), max(g["vel"])]
    sounding_now = sorted(n["note"] for n in snd["notes"] if n["on_ms"] <= t_ms < n["end_ms"])
    pedal = [{"at": clock_tenths(p[k + "_ms"]), "t_ms": p[k + "_ms"], "pedal": k} for p in snd["pedal"]
             for k in ("down", "up") if lo <= p[k + "_ms"] < hi]
    live: List[list] = []
    for e in sess["events"]:
        if e.get("kind") == "chord" and e.get("chord") and lo <= e["t_ms"] < hi:
            if live and live[-1][1] == e["chord"]:
                live[-1][2] += 1
            else:
                live.append([clock_tenths(e["t_ms"]), e["chord"], 1])
    return {"at": clock(t_ms), "from": clock(lo), "to": clock(hi), "home_key": doc["home_key"] if doc["notes"] else None,
            "in_pause": bool(areas) and not any(a["start_ms"] <= t_ms < a["end_ms"] for a in areas),
            "key_area": area and {
        k: area[k] for k in ("key", "at", "until", "relation", "runner_up")}, "windows": windows, "onsets": groups,
        "sounding_at": [midi_name(n, key) for n in sounding_now],
        "pedal_down_at": any(p["down_ms"] <= t_ms < p["up_ms"] for p in snd["pedal"]),
        "pedal": sorted(pedal, key=lambda p: p["t_ms"]), "live_page": live}


def render_moment(sess: dict, data: dict) -> str:
    lines = [headline(sess), ""]
    area = data["key_area"]
    lines.append(f"Moment {data['at']} ({data['from']} to {data['to']})" + (
        f", key area {area['key']} ({area['at']}-{area['until']}, {area['relation']}" +
        (f"; runner-up {area['runner_up']['key']})" if area["runner_up"] else ")") if area and sess["doc"]["notes"]
        else ""))
    if not sess["doc"]["notes"]:
        return "\n".join(lines + ["No notes logged yet."])
    lines += ["", "Harmony windows:"]
    for w in data["windows"]:
        name = w["chord"] or "-"
        if w["reading"] and w["reading"] != w["chord"]:
            used = bool(w["analysed_as"]) and w["reading"].startswith(w["analysed_as"] + " ")
            name += f" = {w['reading']}" if used else f" (another reading: {w['reading']})"
        if w.get("heard_as"):
            name += f" (heard as {w['heard_as']['name']} = {w['heard_as']['number']}: {w['heard_as']['why']})"
        bass = w["bass"]
        fig = " ".join(f[0] for f in bass["figure"][:6]) + (" ..." if len(bass["figure"]) > 6 else "")
        if bass.get("motion") == "figure":
            bass_txt = f"no low bass (lowest note mostly {bass['note']}, above middle C" + \
                (f"; lowest notes in turn {fig})" if len(bass["figure"]) > 1 else ")")
        elif bass["motion"] == "held" or len(bass["figure"]) < 2:
            bass_txt = f"bass {bass['note']}"
        else:
            bass_txt = "bass moving " + fig
        cls = w["class"] or "-"
        if w["class"] not in NON_CHORD_CLASSES:
            cls += f" ({w['detail']})"
        home = w.get("in_home_key")
        if home and home["class"] != "diatonic":
            cls += f"; in {home['key']} {home['number']}, {home['class']}"
        lines.append(f"  {w['at']}-{w['until']} {w['seconds']:>5} s  {name} = {w['number'] or '-'} in {w['key']}: "
                     f"{cls}; notes {' '.join(w['pcs'])}; {bass_txt}; live page {w['live']['events']} names" +
                     (f", {w['merged_windows']} pieces merged" if w["merged_windows"] > 1 else ""))
    if not data["windows"]:
        lines.append("  none (silence)")
    lines += ["", f"Sounding at {data['at']}: {' '.join(data['sounding_at']) or 'nothing'}; pedal "
                  f"{'down' if data['pedal_down_at'] else 'up'}."]
    if data["pedal"]:
        lines.append("Pedal: " + ", ".join(f"{p['pedal']} {p['at']}" for p in data["pedal"]))
    lines += ["", "Notes struck (onset, low to high, velocity):"]
    for g in data["onsets"][:80]:
        vel = f"v{g['vel'][0]}" if g["vel"][0] == g["vel"][1] else f"v{g['vel'][0]}-{g['vel'][1]}"
        lines.append(f"  {g['at']:>7}  {' '.join(g['notes'])}  {vel}")
    if len(data["onsets"]) > 80:
        lines.append(f"  ({len(data['onsets']) - 80} more onsets)")
    if not data["onsets"]:
        lines.append("  none")
    if data["live_page"]:
        lines += _wrap("Live page showed: ", [f"{at} {name}" + (f" x{n}" if n > 1 else "")
                                              for at, name, n in data["live_page"]], max_lines=4, sep=", ")
    return "\n".join(lines)


# -------------------------------------------------------------------------------------------------- name
_NOTE_ARG_RE = re.compile(r"^([A-Ga-g])(#{1,2}|b{1,2})?(-?\d)?$")


def parse_voicing(tokens) -> Tuple[List[int], int]:
    """Note names ('Ab3', 'C#5', or 'Ab C Eb G' stacked upward from octave 3) or MIDI numbers -> (midi notes, spelling
    bias of the names given: -1 flats, +1 sharps, 0)."""
    midis: List[int] = []
    flats = sharps = 0
    for tok in [t for x in tokens for t in re.split(r"[\s,]+", str(x).replace("♭", "b").replace("♯", "#")) if t]:
        if re.fullmatch(r"\d{1,3}", tok):
            midi = int(tok)
            if not 0 <= midi <= 127:
                raise ValueError(f"MIDI note out of range: {tok}")
        else:
            m = _NOTE_ARG_RE.match(tok)
            if not m:
                raise ValueError(f"not a note: {tok!r} (use names like Ab3 or C#5, or MIDI numbers)")
            acc = len(m.group(2) or "") * (1 if (m.group(2) or "").startswith("#") else -1)
            flats += acc < 0
            sharps += acc > 0
            semis = LETTER_PC[LETTERS.index(m.group(1).upper())] + acc
            if m.group(3) is not None:
                midi = (int(m.group(3)) + 1) * 12 + semis
            elif midis:
                midi = (midis[-1] // 12) * 12 + semis % 12
                while midi <= midis[-1]:
                    midi += 12
            else:
                midi = 48 + semis
            if not 0 <= midi <= 127:
                raise ValueError(f"note out of range: {tok}")
        midis.append(midi)
    return midis, (-1 if flats > sharps else 1 if sharps > flats else 0)


def name_data(tokens, key: Optional[str] = None, theory_source=None, node: Optional[str] = None) -> dict:
    """Every reading of a voicing: detect's name, the analysed name (the bass taken as held), and extended readings on
    every root, each numbered and classified in the key when one is given."""
    midis, bias = parse_voicing(tokens)
    if not midis:
        raise ValueError("give at least one note")
    kinfo = None
    if key:
        kinfo = nashville.parse_key(key)
        if not kinfo:
            raise ValueError(f"not a key: {key!r} (try 'Eb major' or 'C minor')")
        bias = kinfo["bias"]
    keyname = kinfo["name"] if kinfo else None
    kctx = {"key": keyname, "tonic": kinfo["tonic"], "mode": kinfo["mode"]} if kinfo else None
    answer, err = run_theory([{"notes": sorted(midis), "bias": bias}], theory_source, node)
    if err:
        raise RuntimeError(f"naming needs the page's Theory.detect through node: {err}")
    info, templates = answer["results"][0], answer["templates"]
    bass = min(midis)
    pcs = sorted({m % 12 for m in midis})

    def spell(pc):
        return pc_name(pc, keyname) if keyname else (PC_SHARP if bias > 0 else PC_FLAT)[pc]

    def note_name(m):
        name = spell(m % 12)
        return f"{name}{(m - _parse_name(name)[1]) // 12 - 1}"
    w = {"pcs": pcs, "bass": bass, "bass_share": 1.0}
    _analyse(w, info, templates)
    if w["over_third"] and w["from"] == "detect":
        _take_reading(w, w["over_third"])  # a voicing on its own: heard from its bass
    spelled = spell_detect(info, keyname)

    def reading_row(r):
        name = spell(r["root_pc"]) + r["suffix"] + (f"/{spell(bass % 12)}" if bass % 12 != r["root_pc"] else "")
        row = {"name": name, "root": spell(r["root_pc"]), "suffix": r["suffix"], "tensions": r["tensions"],
               "no3": r["no3"], "no5": r["no5"], "cost": r["cost"], "number": _number(name, keyname)}
        if kctx:
            cls = classify(pcs, r["root_pc"], kctx)
            row.update({"class": cls["class"], "detail": cls["detail"], "note": _reading_note(pcs, r["root_pc"], kctx)})
        return row
    readings = [reading_row(r) for r in extended_readings(pcs, bass % 12, templates)[:10]] if len(pcs) >= 3 else []
    if w["from"] == "reading":
        analysed = reading_row(w["reading"])
        analysed["from"] = "reading"
    elif spelled and spelled["kind"] != "cluster":
        analysed = {"name": spelled["name"], "number": _number(spelled["name"], keyname, spelled["kind"]),
                    "from": "detect"}
        if kctx and w["root_pc"] is not None and len(pcs) >= 2:
            cls = classify(pcs, w["root_pc"], kctx)
            analysed.update({"class": cls["class"], "detail": cls["detail"],
                             "note": _reading_note(pcs, w["root_pc"], kctx)})
    else:
        analysed = None
    root = w["root_pc"]
    stack = [[note_name(m), FROM_ROOT[(m - root) % 12] if root is not None else None] for m in sorted(midis)]
    fits = [key_name(t, m) for t, m in KEYS if set(pcs) <= key_scale(key_name(t, m))] if not kinfo else []
    return {"notes": [note_name(m) for m in sorted(midis)], "midi": sorted(midis), "key": keyname,
            "detect": spelled and {"name": spelled["name"], "kind": spelled["kind"], "raw": spelled["detect_name"],
                                   "number": _number(spelled["name"], keyname, spelled["kind"])
                                   if spelled["kind"] != "cluster" else None},
            "analysed": analysed, "from_root": stack, "readings": readings, "fits_keys": fits}


def _reading_note(pcs: List[int], root_pc: int, kctx: dict) -> Optional[str]:
    rel = (root_pc - kctx["tonic"]) % 12
    rr = {(p - root_pc) % 12 for p in pcs}
    if kctx["mode"] == "major" and rel == 5 and 6 in rr and 3 not in rr:
        return "the Lydian 4: the 4 chord with its #11"
    if rel == 7 and 3 not in rr and 4 not in rr and (5 in rr or 2 in rr):
        return "a suspended dominant: the 5 chord without its 3rd"
    return None


def render_name(data: dict) -> str:
    k = data["key"]
    lines = [f"Voicing: {' '.join(data['notes'])} (MIDI {' '.join(str(m) for m in data['midi'])})" +
             (f", in {k}" if k else "")]
    d = data["detect"]
    if d:
        lines.append(f"The piano page's namer says: {d['name']}" + (f" = {d['number']}" if d["number"] else "") +
                     (f" (raw {d['raw']})" if d["raw"] != d["name"] else ""))
    a = data["analysed"]
    if a:
        extra = [x for x in (a.get("class"), a.get("note")) if x]
        marks = [m for m, on in (("no 3rd", a.get("no3")), ("no 5th", a.get("no5"))) if on]
        lines.append(f"Analysed as: {a['name']}" + (f" ({', '.join(['reading'] + marks)})" if a["from"] == "reading"
                                                     else "") +
                     (f" = {a['number']}" if a.get("number") else "") + (f"; {'; '.join(extra)}" if extra else ""))
    if data["from_root"] and data["from_root"][0][1] is not None:
        lines.append("From the root: " + ", ".join(f"{n} {iv}" for n, iv in data["from_root"]))
    if data["readings"]:
        lines += ["", "Every reading, simplest first (cost: how much naming it takes; 'no 3rd'/'no 5th': a chord tone "
                      "left out):"]
        for n, r in enumerate(data["readings"], 1):
            marks = ", ".join(m for m, on in (("no 3rd", r["no3"]), ("no 5th", r["no5"])) if on)
            tail = "".join(f"  {x}" for x in (r.get("number"), r.get("class"), r.get("note")) if x)
            lines.append(f"{n:>3}. {r['name']:<22} cost {r['cost']:<5}{' (' + marks + ')' if marks else ''}{tail}")
    if data["fits_keys"]:
        lines += _wrap("", ["Every note fits these keys: " + data["fits_keys"][0]] + data["fits_keys"][1:], sep=", ")
    elif not k:
        lines.append("No single major or natural minor key holds every note.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------- brief
def caveats(sess: dict) -> List[str]:
    """What to keep in mind when reading this session's numbers."""
    doc, events = sess["doc"], sess["events"]
    out = list(sess.get("problems") or [])
    if doc.get("impossible_events") and not any("impossible time" in p for p in out):
        out.append(f"{doc['impossible_events']} event{'s' if doc['impossible_events'] != 1 else ''} at an impossible "
                   f"time skipped")
    if not sess["closed"]:
        out.append("the session is still open, so this covers only what was logged so far")
    if doc.get("held_at_end"):
        out.append(f"{doc['held_at_end']} note{'s were' if doc['held_at_end'] != 1 else ' was'} still sounding when the "
                   f"log ends" + (f"; counted up to now ({clock(sess['end_ms'])})" if sess.get("end_ms") else
                                  ", so how long they rang is unknown"))
    if not doc["notes"]:
        return out + ["no notes logged yet"]
    seg, areas = doc["segmentation"], doc["keys"]["areas"]
    held = [s for s in doc.get("sections", []) if s.get("sounding_before_s")]
    tail = doc.get("sounding_after_s")
    if held or tail:
        out.append("nothing was struck for " + ", ".join([f"{s['pause_before_s']:.0f} s before {s['at']}" for s in held[:4]]
                                                         + ([f"the last {tail:.0f} s"] if tail else []))
                   + (f" (+{len(held) - 4} more)" if len(held) > 4 else "")
                   + " while notes kept sounding (a key held down or the pedal left down?): no key area is read there")
    if sum(w["seconds"] for w in doc["windows"] if is_chord(w)) < 10:
        out.append("hardly any chords were held, so the key reading rests on single notes")
    by_key = list(doc["keys"]["chord_time_by_key"].items())
    if len(by_key) >= 2 and by_key[0][1]["share"] is not None and by_key[0][1]["share"] < HOME_TIE_SHARE:
        (k1, v1), (k2, v2) = by_key[:2]
        if v1["share"] - v2["share"] <= HOME_TIE_MARGIN:
            out.append(f"the home key is a near tie: {k1} {_pct(v1['share'])} vs {k2} {_pct(v2['share'])} of chord time")
        else:
            out.append(f"the home key {k1} holds only {_pct(v1['share'])} of chord time (next {k2} "
                       f"{_pct(v2['share'])})")
    for a in areas:
        ru = a["runner_up"]
        if ru and a["score"] is not None and 0 <= a["score"] - ru["score"] <= KEY_CLOSE:
            out.append(f"{a['at']}-{a['until']} {a['key']} is a close call with {ru['key']}")
        elif a["r"] is not None and a["r"] < 0.5 and not any(x["start_ms"] <= a["start_ms"] < x["end_ms"]
                                                            for x in doc["keys"]["absorbed"]):
            out.append(f"{a['at']}-{a['until']} {a['key']} is a weak key reading (r {a['r']})")
    for a in doc["keys"]["absorbed"]:
        if not a.get("fragment"):
            roots = a["why"].split(":")[0]
            why = "has no tonic chord of its own, only colour inside the key next to it" if "tonic chord" in a["why"] \
                else "has " + ("no chord root" if roots.startswith("0 ") else roots)
            out.append(f"{a['at']}-{a['until']} reads {a['key']} but {why}, so it is numbered in {a['into']}")
    if doc["sound_ends"] != "logged":
        out.append("when each note stopped sounding is inferred from key releases and pedal lifts")
    readings = sum(1 for w in doc["windows"] if w["analysed_from"] == "reading")
    if readings:
        out.append(f"{readings} chord names are readings")
    lines = [w for w in doc["windows"] if w.get("kind") in ("line", "broken chord")]
    if lines:
        out.append(f"{len(lines)} stretches ({sum(w['seconds'] for w in lines):.0f} s) are lines or broken chords, "
                   f"notes never held together, so they are left out of the chords")
    pauses = [s for s in doc.get("sections", []) if s.get("pause_before_s") and s not in held]
    if pauses:
        out.append("pauses (" + ", ".join(f"{s['pause_before_s']:.0f} s before {s['at']}" for s in pauses[:4]) +
                   ") start new sections; nothing reaches across them")
    for a in areas:
        doubt = lydian_doubt(doc, a)
        if doubt:
            out.append(f"{a['at']}-{a['until']} {a['key']} could be {doubt['four']} Lydian (the same notes): "
                       f"{doubt['four']}-rooted chords hold {doubt['four_s']} s against {doubt['tonic']}'s "
                       f"{doubt['tonic_s']} s, and {doubt['four']} is in the bass longer too")
    for a in areas:
        if a.get("too_short"):
            out.append(f"{a['at']}-{a['until']} {a['key']} is too short to call a key")
    for a in doc["keys"]["absorbed"]:
        if a.get("fragment"):
            out.append(f"{a['at']}-{a['until']} reads {a['key']} by pitch content, but it is a short passage after a "
                       f"pause, so it is numbered in its own centre, {a['into']}")
    if doc["naming"].get("numbered_from_parts"):
        out.append(f"{doc['naming']['numbered_from_parts']} numbers were put together from their parts (the shared "
                   f"numberer failed on them)")
    named = [e for e in events if e.get("kind") == "chord" and e.get("chord")]
    odd: Dict[str, int] = {}
    for e in named:
        area = next((a for a in areas if a["start_ms"] <= e["t_ms"] < a["end_ms"]), None)
        bias = nashville.parse_key(area["key"])["bias"] if area else 0
        if bias and len(e["chord"]) > 1 and e["chord"][1] == ("#" if bias < 0 else "b"):
            odd[e["chord"]] = odd.get(e["chord"], 0) + 1
    if odd:
        ex = ", ".join(sorted(odd, key=lambda c: -odd[c])[:3])
        out.append(f"{sum(odd.values())} live names used sharps in flat keys or flats in sharp keys (e.g. {ex}); "
                   f"respelled here in the key area")
    if named:
        out.append(f"the live page named {len(named)} chord shapes for these {seg['windows']} harmonies (it renames "
                   f"while notes unfold); names here come from whole windows")
    shown = [e.get("key") for e in events if e.get("kind") == "chord" and e.get("key")]
    flips = sum(1 for a, b in zip(shown, shown[1:]) if a != b)
    if flips >= 4:
        out.append(f"the page's key display changed {flips} times; the key areas here come from the whole session")
    if seg["transients_dropped"]:
        out.append(f"{seg['transients_dropped']} isolated blips under {MIN_WINDOW_MS / 1000} s left out")
    return out


def lydian_doubt(doc: dict, area: dict) -> Optional[dict]:
    """A major key area of ASK_MIN_AREA_S or more whose chords are rooted on its 4 longer than on its 1, with the 4 in
    the bass longer too (Eb-rooted chords and an Eb bass outweighing Bb in a Bb major area): the same notes are the 4's
    Lydian mode, and the 24-key model cannot weigh one against the other. {four, tonic, four_s, tonic_s} or None."""
    if area.get("mode") != "major" or (area.get("seconds") or 0) < ASK_MIN_AREA_S:
        return None
    tonic, four = area["tonic"], (area["tonic"] + 5) % 12
    root_s, bass_s = [0.0] * 12, [0.0] * 12
    for w in doc["windows"]:
        if not is_chord(w) or not area["start_ms"] <= (w["start_ms"] + w["end_ms"]) / 2 < area["end_ms"]:
            continue
        p = _parts(w)
        if p:
            root_s[_sp_pc(p["root"])] += w["seconds"]
        bass = _parse_name(re.sub(r"-?\d+$", "", w["bass"]["note"] or ""))
        if bass:
            bass_s[_sp_pc(bass)] += w["seconds"]
    if root_s[four] > root_s[tonic] and bass_s[four] > bass_s[tonic]:
        return {"four": pc_name(four, area["key"]), "tonic": pc_name(tonic, area["key"]), "four_s": _r(root_s[four], 1),
                "tonic_s": _r(root_s[tonic], 1)}
    return None


def _page_said(m: dict) -> str:
    """How the page's namer saw a findings moment whose analysed name differs from the window's name."""
    if m["chord"] == m["analysed_as"]:
        return ""
    if m["chord"] and m["chord"].endswith("reading)"):
        return " (a reading: the page's namer had no name for these notes)"
    return f" (the page's namer said {m['chord']})"


def _ask_candidate(category, start_ms, score, what, plain, ask, seconds=0.0, lead_ms=3000, covers=()) -> dict:
    replay = (max(0, start_ms - lead_ms), start_ms + max(seconds * 1000, 5000) + 3000)
    return {"category": category, "at": clock(start_ms), "start_ms": start_ms, "score": _r(score, 2),
            "replay": [clock(replay[0]), clock(replay[1])], "what": what, "plain": plain, "ask": ask,
            "_covers": [replay] + [tuple(c) for c in covers]}


CADENCE_ASK = {  # a cadence kind's start -> (score, plain words, question); the longest matching start wins
    "2 -> 5 -> 1": (26, "2, then 5, then home: the classic approach, each chord a 5th above the next.",
                    "Did you feel that landing coming, or did your hands find it?"),
    "2 -> 5sus -> 1": (24, "2, then the 5 chord without its 3rd, then home: a softened classic approach.",
                       "Did you feel that landing coming, or did your hands find it?"),
    "5 -> 1": (24, "the 5 chord lands on 1 with the bass moving from 5 to 1: the strongest way home.",
               "Did you feel that landing coming, or did your hands find it?"),
    "5sus -> 1": (20, "the 5 chord without its 3rd settles on 1: a softer landing than the full dominant.",
                  "Did you feel that landing coming, or did your hands find it?"),
    "5 over a 1 pedal": (24, "the 5 chord's notes sound over the home note in the bass, then settle into the 1 chord "
                             "above it: home arrives over a bass that never left.",
                         "Did you keep that bass note down on purpose while the top resolved?"),
    "5 -> 6m": (22, "the 5 chord sets up home, then lands on the 6m chord instead: a deceptive cadence, the ear "
                    "expected 1.", "Did you mean to dodge home there?"),
    "5 -> b6": (22, "the 5 chord sets up home, then lands on the b6 chord instead: a deceptive cadence, the ear "
                    "expected 1.", "Did you mean to dodge home there?"),
    "b6 -> b7 -> 1": (20, "b6, then b7, then home without a leading tone: the Aeolian way home.",
                      "Did that climb home feel planned?"),
    "b7 -> 1": (18, "the b7 chord steps up to 1 without the leading tone: a modal way home.",
                "Did that step home feel planned?"),
    "4m -> 1": (18, "the minor 4, borrowed from the parallel minor, settles on 1: a darker amen.",
                "Did you reach for the minor 4 on purpose there?"),
    "4 -> 1": (12, "the 4 chord settles on 1: the plagal 'amen' sound.", "Do you hear that 'amen' when you play it?"),
}


def ask_moments(doc: dict, evidence: dict, outside: dict, progressions: dict, limit: int = 3) -> List[dict]:
    """The moments most worth asking Daniel about, each with a time to replay and plain words: a key change, a chord
    from outside the key (not one that is at home in the home key, and not one riding a bass line), the Lydian 4
    (weighted by how often it comes), a cadence, a bass line, a suspended dominant, a pedal point, an arpeggio the live
    page chopped up, a loop, a suspension resolving. Up to ASK_PER_KIND candidates of each kind; one moment per kind,
    at least ASK_SEPARATION_MS apart, none inside the replay (or the return it mentions) of a moment already picked."""
    if not doc["notes"]:
        return []
    cands = []
    areas, f = doc["keys"]["areas"], doc["findings"]
    for i, c in enumerate(evidence["changes"]):
        prev, nxt = areas[i], areas[i + 1]
        covers: List[tuple] = []
        if min(prev["seconds"], nxt["seconds"]) < ASK_MIN_AREA_S or c.get("pause_s") or nxt.get("return"):
            continue  # after a pause it is a new section, not a key change to ask about
        pk, nk = nashville.parse_key(prev["key"]), nashville.parse_key(nxt["key"])
        old = [s["note"] for s in c["swapped"] if s["belongs_to"] == prev["key"]]
        new = [s["note"] for s in c["swapped"] if s["belongs_to"] == nxt["key"]]
        if pk["tonic"] == nk["tonic"]:
            plain = f"the home note stays {prev['key'].split(' ')[0]} but the mode turns {nk['mode']}"
            if c["gone"] or c["arrived"]:
                plain += (f": {_and(c['gone']) or 'nothing'} {'fade' if len(c['gone']) != 1 else 'fades'} out and "
                          f"{_and(c['arrived']) or 'nothing new'} {'come' if len(c['arrived']) != 1 else 'comes'} in")
            plain += f", a {'darker' if nk['mode'] == 'minor' else 'brighter'} colour on the same home."
            if c["stayed"]:
                plain += (f" {_and(c['stayed'])} still {'sound' if len(c['stayed']) != 1 else 'sounds'} after the "
                          f"change")
                lt = c.get("raised_7th")
                plain += (f" ({lt[0]} is {nxt['key']}'s raised 7th: the harmonic minor colour)." if lt and lt[0] in
                          c["stayed"] else ".")
            ret = next((r for r in evidence["areas"][i + 1].get("returns", [])), None)
            back = areas[i + 2] if i + 2 < len(areas) else None
            if back and back.get("return") and back.get("section") == nxt.get("section"):
                chords = list(dict.fromkeys(w.get("label") or w["analysed_as"] for w in doc["windows"]
                                            if is_chord(w) and back["start_ms"] <= w["start_ms"] < back["end_ms"]))
                plain += (f" At {back['at']}-{back['until']} the {prev['key'].split(' ')[1]} colour comes back for "
                          f"{back['seconds']} s" + (f" ({', '.join(chords[:3])})" if chords else "") + ".")
                covers.append((back["start_ms"], back["end_ms"]))
            elif ret:
                plain += (f" At {ret['at']}-{ret['until']} the {prev['key'].split(' ')[1]} colour comes back "
                          f"({', '.join(ret['chords'][:3])}).")
                covers.append((ret["start_ms"], ret["start_ms"] + ret["seconds"] * 1000))
        elif not c["swapped"]:
            plain = f"{prev['key']} and {nxt['key']} share every note; what moves is which note feels like home."
        else:
            doubt = lydian_doubt(doc, prev) if nk["mode"] == "major" and (nk["tonic"] - pk["tonic"]) % 12 == 5 else None
            if doubt:  # the first area may already have been the new tonic's Lydian: say both
                plain = (f"{', '.join(old)} in {prev['key']} becomes {', '.join(new)} in {nxt['key']}. Before the change "
                         f"{doubt['four']}-rooted chords already outweighed {doubt['tonic']} ones ({doubt['four_s']} s "
                         f"against {doubt['tonic_s']} s), so it may be {doubt['four']} Lydian turning plain "
                         f"{nxt['key']}, more than the home note moving from {doubt['tonic']} to {doubt['four']}.")
            else:
                plain = (f"the home note moves {STEP_WORDS[(nk['tonic'] - pk['tonic']) % 12]}, from "
                         f"{prev['key'].split(' ')[0]} to {nxt['key'].split(' ')[0]}. The keys differ by {len(old)} "
                         f"note{'s' if len(old) != 1 else ''}: {', '.join(old)} in {prev['key']}, {', '.join(new)} in "
                         f"{nxt['key']}.")
        heard = _change_notes(c)
        what = (f"{prev['key']} becomes {nxt['key']}" + (f" (heard: {heard})" if heard else "") +
                f"; {_ref_text(c['last_chord_before'])} -> {_ref_text(c['first_chord_after'])}")
        ask = "Did you decide to change key there, or did a chord lead you?"
        cands.append(_ask_candidate("key change", c["start_ms"], 40 + min(prev["seconds"], nxt["seconds"]) / 10, what, plain,
                             ask, lead_ms=8000, covers=covers))
    recurs: Dict[tuple, int] = {}  # how often a chord comes off a bass line
    for g in outside["groups"]:
        if not g.get("on_bass_line"):
            recurs[(g["chord"], g["key"])] = recurs.get((g["chord"], g["key"]), 0) + len(g["times"])

    def outside_score(m):
        lands = m["class"] == "secondary dominant" and "lands there" in (m["source"] or "")
        return min(38, 20 + min(12.0, 3 * m["seconds"]) + 2 * (recurs.get((m["chord"], m["key"]), 1) - 1) +
                   (4 if m["class"] in ("borrowed", "modal") or lands else 0))
    def held_outside(m):  # an outside note that is more than one soft brush (never ask about a finger slip)
        light = {_sp_pc(_parse_name(x)) for x in m.get("light_notes") or ()}
        return any(_sp_pc(_parse_name(o["note"])) not in light for o in m["outside_notes"])
    worth = [m for m in outside["moments"] if not m.get("on_bass_line") and m.get("in_home_class") != "diatonic"
             and held_outside(m)]
    for m in sorted(worth, key=lambda m: -outside_score(m))[:ASK_PER_KIND]:
        key, cls = m["key"], m["class"]
        notes = _notes_text(m["outside_notes"])
        parallel = parallel_key(key)
        if cls == "borrowed":
            src = (f"they come from {parallel}, the same home note in the other mode, so it shades the key "
                   f"{'darker' if key.endswith('major') else 'brighter'} without leaving home.")
        elif cls == "modal":
            mode = re.search(r"Mixolydian|Lydian|Dorian|Phrygian", m["source"] or "")
            src = (f"that is {key.split(' ')[0]} {mode.group(0)}, {MODE_WORDS[mode.group(0)]}." if mode
                   else f"{m['source']}.")
        elif cls == "secondary dominant":
            src = f"it acts as {m['source']}: a chord that points somewhere other than home."
        else:
            src = f"it belongs to neither {key} nor {parallel}: colour from further away."
        plain = f"{m['chord']} holds {notes}, which {key} does not have; {src}"
        times = recurs.get((m["chord"], m["key"]), 1)
        cands.append(_ask_candidate("outside the key", m["start_ms"], outside_score(m),
                             f"{m['chord']} = {m['number']} in {key}, held {m['seconds']} s ({m['source']})" +
                             (f"; {times} times this session" if times > 1 else ""), plain,
                             "What were you reaching for with that chord?", m["seconds"]))
    lyd = f["lydian_4"]
    for m in sorted(lyd, key=lambda m: -m["seconds"])[:ASK_PER_KIND]:
        p = nashville.parse_chord(m["analysed_as"])
        root = _sp_name(p["root"])
        top = _spell_from_root((_sp_pc(p["root"]) + 6) % 12, p["root"], m["key"])
        plain = (f"{root} is the 4 chord of {m['key']}, and {top} sits a raised 4th above it (its #11). {top} is "
                 f"already in {m['key']} (its 7th), so nothing leaves the key: that bright, floating edge is the "
                 f"Lydian sound." + (f" It comes {len(lyd)} times this session." if len(lyd) > 1 else ""))
        cands.append(_ask_candidate("Lydian 4", m["start_ms"], 18 + 2 * min(len(lyd), 8) + min(m["seconds"], 6.0),
                             f"{m['analysed_as']} = {m['number']} in {m['key']}, {m['seconds']} s" + _page_said(m), plain,
                             f"Do you hear the {top} on top as its own colour, or as part of the chord?", m["seconds"]))
    for c in f["cadences"]:
        prefix = max((k for k in CADENCE_ASK if c["kind"].startswith(k)), key=len, default=None)
        if not prefix or c.get("habit"):
            continue
        score, words, question = CADENCE_ASK[prefix]
        seconds = ((c.get("end_ms") or c["start_ms"]) - c["start_ms"]) / 1000
        cands.append(_ask_candidate("cadence", c["start_ms"], score,
                             f"{c['kind']}: {' -> '.join(c['chords'])} ({' -> '.join(str(x) for x in c['numbers'])} in "
                             f"{c['key']}; bass {' -> '.join(str(b) for b in c['bass'])})",
                             words, question, seconds))
    for b in f.get("bass_lines") or []:
        way = "half steps" if b["chromatic"] else "steps"
        plain = (f"the bass walks {' '.join(b['notes'])}, {b['direction']} by {way}, while the chords above follow it"
                 + (f" ({', '.join(b['chords'][:3])})" if b["chords"] else "") +
                 ": the chords that look outside the key are passing points on that line.")
        cands.append(_ask_candidate("bass line", b["start_ms"], 22 if b["chromatic"] else 16,
                             f"a bass line {' '.join(b['notes'])} in {b['key']}", plain,
                             f"Were you following the bass line {'down' if b['direction'] == 'falling' else 'up'}, or the "
                             f"chords on top?", (b["end_ms"] - b["start_ms"]) / 1000))
    sus = [d for d in f["dominants"]["windows"] if d["form"] == "suspended" and d["seconds"] >= 2]
    for d in sorted(sus, key=lambda d: -d["seconds"])[:ASK_PER_KIND]:
        p = nashville.parse_chord(d["analysed_as"])
        root, root_pc = _sp_name(p["root"]), _sp_pc(p["root"])
        tonic = d["key"].split(" ")[0]
        third = _spell_from_root((root_pc + 4) % 12, p["root"], d["key"])
        if d.get("over") == "1":
            over = f" It sits over {tonic} in the bass, so home and away sound at once."
        elif d.get("over") not in (None, "its root", "-"):
            over = f" It sits over the {d['over']} in the bass ({d['bass']})."
        else:
            over = ""
        if "sus2" in p["suffix"] and "sus4" not in p["suffix"]:
            stand_in = f"{_spell_from_root((root_pc + 2) % 12, p['root'], d['key'])} (its 2nd)"
        else:
            stand_in = f"{tonic} (the home note itself)"
        plain = (f"{root} is the 5 chord of {d['key']}; here {stand_in} takes the place of its 3rd, {third}, so it "
                 f"leans toward {tonic} without the full pull of {root}7.{over}")
        cands.append(_ask_candidate("suspended dominant", d["start_ms"], min(26.0, 8 + 2 * d["seconds"]),
                             f"{d['analysed_as']} = {d['number']} in {d['key']}, held {d['seconds']} s", plain,
                             "Were you avoiding the full dominant there, or just enjoying the hang?", d["seconds"]))
    low = [p for p in f["pedal_points"] if re.search(r"-?\d+$", p["bass"] or "") and
           int(re.search(r"-?\d+$", p["bass"]).group(0)) <= ASK_PEDAL_MAX_OCTAVE]  # a bass, not a held melody note
    for p in sorted(low, key=lambda p: -p["seconds"])[:ASK_PER_KIND]:
        plain = (f"{p['bass']} stays in the bass for {p['seconds']} s while the chords above it change: the ground "
                 f"holds still and the harmony moves over it.")
        cands.append(_ask_candidate("pedal point", p["start_ms"], min(30.0, 16 + p["seconds"]),
                             f"{p['bass']} under {' -> '.join(p['over'][:5])} in {p['key']}", plain,
                             "Was holding that bass note a plan, or where your left hand wanted to stay?",
                             p["seconds"]))
    arps = [w for w in doc["windows"] if is_chord(w) and w["bass"]["motion"] in ("moving", "figure")
            and w["seconds"] >= 2 and w["live"]["events"] >= ASK_ARPEGGIO_NAMES and len(w["bass"]["figure"]) >= 2
            and {_sp_pc(_parse_name(f[0])) for f in w["bass"]["figure"]} <= set(_row_pcs(w))]  # moving on chord tones
    for w in sorted(arps, key=lambda w: -w["live"]["events"])[:ASK_PER_KIND]:
        fig = w["bass"]["figure"]
        chord = w["label"] or w["analysed_as"]
        if w["bass"]["motion"] == "figure":
            first, last = fig[0][0], fig[-1][0]
            way = "falling" if _note_midi(first) > _note_midi(last) else "rising"
            plain = (f"one {chord} arpeggio {way} from {first} to {last}, all above middle C"
                     f"{' under the pedal' if w['voicing']['pedal_share'] >= 0.5 else ''}, over {w['seconds']} s (no "
                     f"low bass: the lowest note is part of the figure). The live page showed {w['live']['events']} "
                     f"chord names there; heard whole, it is one harmony.")
        else:
            figure = " ".join(x[0] for x in fig[:5])
            plain = (f"one {chord} spread over {w['seconds']} s over a bass walking {figure}. The live page showed "
                     f"{w['live']['events']} chord names there; heard whole, it is one harmony.")
        cands.append(_ask_candidate("arpeggio", w["start_ms"], min(20.0, 8 + 0.5 * w["live"]["events"]),
                             f"{w['analysed_as']} = {w['number']} in {w['key']}, rolled for {w['seconds']} s", plain,
                             "Were you thinking of it as one chord, or as a line?", w["seconds"]))
    loops = [loop for loop in progressions["loops"] if loop["best_reps"] >= 2]
    for loop in loops[:ASK_PER_KIND]:
        run = max(loop["runs"], key=lambda r: r["reps"])
        start = run.get("start_ms")
        if start is None:
            start = next((w["start_ms"] for w in doc["windows"] if w["at"] == run["at"]), 0)
        plain = (f"the same {len(loop['numbers'])} chords ({' -> '.join(loop['numbers'])}) cycled "
                 f"{run['reps']} times back to back.")
        cands.append(_ask_candidate("loop", start, min(ASK_LOOP_CAP, 10 + loop["best_reps"] * len(loop["numbers"])),
                             f"{' -> '.join(loop['chords'])} in {loop['key']}", plain,
                             "What keeps you coming back round that cycle?", run["seconds"] or 0))
    for s in [s for s in f["suspensions"] if s.get("resolves")][:ASK_PER_KIND]:
        plain = f"{s['from']} is held {s['held_s']} s, then {s['note']}: tension settling into rest."
        cands.append(_ask_candidate("suspension resolving", s["start_ms"], 18, f"{s['from']} -> {s['to']} in {s['key']}",
                             plain, "Do you feel that little settle when the 3rd comes in?"))
    picked: List[dict] = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if any(c["category"] == p["category"] or abs(c["start_ms"] - p["start_ms"]) < ASK_SEPARATION_MS or
               any(a <= c["start_ms"] < b for a, b in p["_covers"]) for p in picked):
            continue
        picked.append(c)
        if len(picked) == limit:
            break
    return [{k: v for k, v in c.items() if not k.startswith("_")} for c in picked]


def brief_data(sess: dict) -> dict:
    doc, snd = sess["doc"], sess["snd"]
    base = {"session": sess["session"], "played": _local(sess["start"]), "length": clock(doc["duration_s"] * 1000),
            "notes": doc["notes"], "closed": sess["closed"]}
    if not doc["notes"]:
        return {**base, "empty": True, "caveats": caveats(sess)}
    home = doc["home_key"]
    evidence = key_evidence(doc, snd)
    voc = vocabulary(doc)
    prog = progression_data(doc, (2, 3, 4), 2)
    outside = borrowed_data(doc)
    heard_pc, _ = _heard(snd["notes"])
    prof = pc_profile(heard_pc, 0, snd["duration_ms"] + 1)
    timeline = [{"at": w["at"], "start_ms": w["start_ms"], "seconds": w["seconds"],
                 "chord": w.get("label") or w["analysed_as"],
                 "number": w["number"], "key": w["key"], "reading": w["analysed_from"] == "reading",
                 "outside": w["class"] not in NON_CHORD_CLASSES,
                 "heard_as": (w.get("heard_as") or {}).get("name"), "heard_number": (w.get("heard_as") or {}).get("number")}
                for w in doc["windows"] if is_chord(w)]
    return {**base, "empty": False, "home_key": home,
            "home_share": (doc["keys"]["chord_time_by_key"].get(home) or {}).get("share"),
            "areas": [{**{k: a.get(k) for k in ("key", "at", "until", "start_ms", "end_ms", "seconds", "relation",
                                                "after_pause_s", "return", "section")},
                       "held_through": bool(a.get("after_pause_s") and 0 <= (a.get("section") or 0) < len(doc["sections"])
                                            and doc["sections"][a.get("section") or 0].get("sounding_before_s"))}
                      for a in doc["keys"]["areas"]],
            "bass_lines": doc["findings"].get("bass_lines") or [],
            "changes": evidence["changes"], "most_heard": [[pc_name(pc, home), _r(prof[pc], 3)] for pc in
                                                           sorted(range(12), key=lambda p: -prof[p])[:5]],
            "chord_seconds": voc["chord_seconds"], "other_seconds": voc["other_seconds"], "classes": voc["classes"],
            "timeline": timeline, "top_chords": voc["chords"][:8], "top_numbers": voc["numbers"][:8],
            "moves": {n: rows[:6] for n, rows in prog["moves"].items()}, "loops": prog["loops"][:3],
            "colours": colour_data(doc), "outside": outside, "cadences": doc["findings"]["cadences"],
            "touch": touch_data(doc, snd), "ask": ask_moments(doc, evidence, outside, prog), "caveats": caveats(sess)}


DOMINANT_ARRIVALS = ("5 -> 1", "5sus -> 1", "2 -> 5 -> 1", "2 -> 5sus -> 1", "5 over a 1 pedal -> 1")  # home from 5


def cadence_kinds(cadences: List[dict]) -> List[dict]:
    """Cadences by kind (its short name: '4 -> 1', every key area together), most often first: [{kind, count, first_at,
    first (the first cadence of the kind), times}]. A habit counts each of its times."""
    groups: Dict[str, dict] = {}
    for c in cadences:
        kind = c["kind"].split(" (")[0]
        g = groups.setdefault(kind, {"kind": kind, "count": 0, "first_at": c["at"], "first": c, "times": []})
        g["count"] += c.get("times") or 1
        g["times"] += c.get("at_times") or [c["at"]]
    return sorted(groups.values(), key=lambda g: (-g["count"], g["first"]["start_ms"]))


TIMELINE_PER_AREA = 5        # the brief's timeline shows each key area's longest chords, in time order: this many...
TIMELINE_PER_AREA_MIN = 3    # ...shrinking to this many when the brief runs long (an area under ASK_MIN_AREA_S: 2 at most)
TIMELINE_BARE_AREAS = 3      # key areas after a pause with no chord held long are named at most this many times


def _timeline_lines(data: dict, per_area: int) -> Tuple[List[str], int]:
    """(lines, chords left out): each key area's longest chords held TIMELINE_MIN_S or more, in time order; an area
    after a pause, and the parallel mode's return, say so in their headers."""
    lines, hidden, bare = [], 0, 0
    for a in data["areas"]:
        inside = [e for e in data["timeline"] if e["seconds"] >= TIMELINE_MIN_S and
                  a["start_ms"] <= e["start_ms"] + e["seconds"] * 500 < a["end_ms"]]
        k = per_area if (a["seconds"] or 0) >= ASK_MIN_AREA_S else min(per_area, 2)
        top = sorted(sorted(inside, key=lambda e: -e["seconds"])[:k], key=lambda e: e["start_ms"])
        hidden += len(inside) - len(top)
        tags = [t for t in (_after_pause(a), "the parallel mode back" if a.get("return") else None) if t]
        head = f"  [{a['key']}{', ' + ', '.join(tags) if tags else ''}] "
        items = [f"{e['at']} {e['chord']}{'~' if e['reading'] else ''} {e['number'] or '-'}{'*' if e['outside'] else ''}"
                 + (f" (heard as {e['heard_as']} {e['heard_number']})" if e.get("heard_as") else "") for e in top]
        if items:
            lines += _wrap(head, items, sep=" | ", indent="    ")
        elif tags:
            bare += 1
            if bare <= TIMELINE_BARE_AREAS:
                lines.append(head + "no chord held long")
    if bare > TIMELINE_BARE_AREAS:
        lines.append(f"  (+{bare - TIMELINE_BARE_AREAS} more key areas with no chord held long)")
    hidden += sum(1 for e in data["timeline"] if e["seconds"] < TIMELINE_MIN_S)
    return lines, hidden


def _after_pause(a: dict) -> Optional[str]:
    """'after a 12 s pause', or 'after 3540 s with nothing struck' when notes kept sounding through it."""
    if not a.get("after_pause_s"):
        return None
    return (f"after {a['after_pause_s']:.0f} s with nothing struck" if a.get("held_through")
            else f"after a {a['after_pause_s']:.0f} s pause")


BRIEF_MAX_LINES = 80  # the brief, glossary included, fits in this many lines
BRIEF_BUDGET = {"per_area": TIMELINE_PER_AREA, "changes": 6, "most": 2, "moves": 2, "outside": 5, "from_home": 2,
                "cadences": 2, "touch": 4, "caveats": 5, "words": 1}
BRIEF_TRIM = (("changes", 3), ("caveats", 3), ("outside", 3), ("from_home", 1), ("cadences", 1), ("moves", 1),
              ("most", 1), ("touch", 2), ("changes", 1), ("outside", 1), ("caveats", 1), ("words", 0),
              ("per_area", TIMELINE_PER_AREA_MIN))  # what gives way first when the brief runs long, and how far: the
                                                    # other parts, then the glossary's reading aids, the timeline last


def _brief_length(text: str) -> int:
    return len(text.rstrip("\n").splitlines())


def render_brief(sess: dict, data: dict) -> str:
    """The brief with its own words, parts trimmed in BRIEF_TRIM order until it fits in BRIEF_MAX_LINES."""
    budget = dict(BRIEF_BUDGET)
    text = _brief_with_words(sess, data, budget)
    for part, floor in BRIEF_TRIM:
        while _brief_length(text) > BRIEF_MAX_LINES and budget[part] > floor:
            budget[part] -= 1
            text = _brief_with_words(sess, data, budget)
    return text


def _brief_with_words(sess: dict, data: dict, budget: dict) -> str:
    body = _brief_text(sess, data, budget).rstrip("\n")
    room = None if budget["words"] else max(3, BRIEF_MAX_LINES - _brief_length(body))
    words = glossary(body, data.get("home_key"), room)
    return body + ("\n" + "\n".join(words) if words else "")


def _brief_text(sess: dict, data: dict, budget: dict) -> str:
    lines = [f"Brief: {headline(sess)}"]
    if data["empty"]:
        return "\n".join(lines + ["", "No notes logged yet.", "", f"Data caveats: {'; '.join(data['caveats'])}."])
    home = data["home_key"]
    other = f"{data['other_seconds']} s of single notes, two-note shapes, lines and broken chords"
    if not data["chord_seconds"]:
        lines += ["", f"Home key: none yet (no chord was held; the notes lean toward {home}). {other}.",
                  "Key areas: none yet (a key area needs chords held)."]
    else:
        lines += ["", f"Home key: {home} ({_pct(data['home_share'])} of chord time). {data['chord_seconds']} s of "
                      f"chords, {other}."]
        area_items = []
        for a in data["areas"]:
            notes = [x for x in ((None if a["relation"] in ("home key", None) else
                                  a["relation"].replace(" of " + home, "")),
                                 _after_pause(a), "a return" if a.get("return") else None) if x]
            area_items.append(f"{a['at']}-{a['until']} {a['key']}" + (f" ({', '.join(notes)})" if notes else ""))
        lines += _wrap(f"Key areas (numbers below are in each area's key; relation to {home}): ", area_items)
    changes = data["changes"][:budget["changes"]]
    for n, c in enumerate(changes):
        heard = _change_notes(c, 3)
        head = f"new section after a {c['pause_s']} s pause, " if c.get("pause_s") else ""
        more = len(data["changes"]) - len(changes)
        lines.append(f"  {c['at']} {head}{c['from']} -> {c['to']}: " + (f"{heard}; " if heard else "") +
                     f"{_ref_text(c['last_chord_before'])} -> {_ref_text(c['first_chord_after'])}" +
                     (f" (+{more} more changes: keys verb)" if more and n == len(changes) - 1 else ""))
    if data["chord_seconds"] < data["other_seconds"]:
        lines.append("Mostly single notes; most heard: " + ", ".join(f"{n} {_pct(s)}" for n, s in data["most_heard"]))

    tl, hidden = _timeline_lines(data, budget["per_area"])
    lines += ["", f"Held harmony (each key area's longest chords in time order, {hidden} more left out; * outside the "
                  f"key, ~ a reading):"]
    lines += tl or ["  none: no chords held that long"]

    if data["top_chords"]:
        lines.append("")
        lines += _wrap("Most time: ", [f"{c['chord']} {c['in'][0]['number'] or '-'}"
                                       f"{_key_tag(c['in'][0]['key'], home)} {c['seconds']:.1f} s"
                                       for c in data["top_chords"]], max_lines=budget["most"])
        lines += _wrap("By number (every key area together): ",
                       [f"{n['number']} {n['seconds']:.1f} s" for n in data["top_numbers"]], max_lines=1)
    moves = [f"loop {' -> '.join(x['numbers'])} up to x{x['best_reps']} at {x['first_at']} ({' '.join(x['chords'])})"
             for x in data["loops"][:2]]
    moves += [f"{' -> '.join(g['numbers'])} x{g['count']} (first {g['first_at']})"
              for n in ("4", "3", "2") for g in data["moves"].get(n, [])[:3 if n == "2" else 2]]
    if moves:
        lines += _wrap("Moves (quality only; a chord recoloured over its bass is one step): ", moves,
                       max_lines=budget["moves"])

    col = data["colours"]
    if col["colours"]:
        lines.append("")
        lines += _wrap("Colour (share of chord time): ", [f"{c['colour'].split(' (')[0]} {_pct(c['share'])}"
                                                          for c in col["colours"]], max_lines=2, sep=", ")
        lyd = col["lydian_4"]
        if lyd:
            longest = max(lyd, key=lambda m: m["seconds"])
            lines += _wrap(f"Lydian 4: {len(lyd)} times (longest {longest['at']} "
                           f"{longest['label'] or longest['analysed_as']} {longest['seconds']} s) at ",
                           [m["at"] for m in lyd], max_lines=1, sep=", ")
        dom = _dominant_lines(col["dominants"], home, split=True, top_n=2)
        if dom:
            lines += _wrap("Dominants on 5 (by key area; bass under them): ", dom, max_lines=2)
        pp = sorted(col["pedal_points"], key=lambda p: -p["seconds"])
        if pp:
            lines += _wrap(f"Pedal points: {len(pp)}, longest ", [f"{p['at']} {p['bass']} sounding {p['seconds']} s "
                                                                 f"under {' -> '.join(p['over'][:4])}" for p in pp[:2]],
                           max_lines=1)
        bl = data.get("bass_lines") or []
        if bl:
            lines += _wrap("Bass lines: ", [f"{b['at']}-{b['until']} {' '.join(b['notes'])} ({b['direction']} by "
                                           f"{'half steps' if b['chromatic'] else 'steps'}; chords above: "
                                           f"{', '.join(b['chords'][:3])})" for b in bl[:3]], max_lines=1)
        resolving = [s for s in col["suspensions"] if s.get("resolves")]
        kept = [s for s in col["suspensions"] if not s.get("resolves")]
        res = [f"{s['at']} {s['from']} -> {s['to']}" for s in resolving[:2]] + \
              [f"{s['at']} {s['from']} -> {s['to']} (sus kept)" for s in kept[:1]] + \
              [f"{c['at']} {c['from']} -> {c['to']}" for c in col["colour_additions"][:2]]
        if res:
            lines += _wrap(f"Suspensions ({len(resolving)} resolving, {len(kept)} with the sus note kept) and colour "
                           f"additions ({len(col['colour_additions'])}), e.g. ", res, max_lines=1)

    out = data["outside"]
    lines.append("")
    shown = [g for g in out["groups"] if not g.get("on_bass_line")]
    if out["groups"] and not shown:
        lines.append("Outside the key: only chords riding the bass lines above")
    if shown:
        top = sorted(shown, key=lambda g: -g["seconds"])[:budget["outside"]]
        lines.append("Outside the key" + (" (chords riding a bass line are left out: see Bass lines):"
                                           if len(shown) < len(out["groups"]) else ":"))
        for g in sorted(top, key=lambda g: g["first_ms"]):
            lines.append(f"  {', '.join(g['times'][:4])}{' ...' if len(g['times']) > 4 else ''} {g['chord']} = "
                         f"{g['number']}{_key_tag(g['key'], home) or ' in ' + g['key']} ({g['seconds']} s): "
                         f"{g['source']}; outside notes {_notes_text(g['outside_notes'])}")
    elif not out["groups"]:
        lines.append("Outside the key: nothing held as a chord (every chord of three or more notes fits its key area)")
    if out["from_home"]:
        items = [f"{g['chord']} = {g['number']} {g['class']} at {', '.join(g['times'][:3])}"
                 for g in sorted(out["from_home"], key=lambda g: -g["seconds"])[:6]]
        lines += _wrap(f"Heard from home {home}: ", items, max_lines=budget["from_home"])
    cad = cadence_kinds(data["cadences"])
    if cad:
        items = []
        for g in cad:
            c = g["first"]
            example = f"{' -> '.join(c['chords'])}{_key_tag(c['key'], home)} (bass {' -> '.join(str(b) for b in c['bass'])})"
            items.append(f"{g['kind']} x{g['count']} (first {g['first_at']}: {example})" + (", a habit" if c.get("habit")
                                                                                            else "")
                         if g["count"] > 1 else f"{g['first_at']} {g['kind']}: {example}")
        landings = sum(g["count"] for g in cad if g["kind"].endswith("-> 1"))
        if landings >= 3 and not any(g["kind"] in DOMINANT_ARRIVALS for g in cad):
            items.insert(0, f"{landings} landings on 1, none of them from the 5 chord")
        lines += _wrap("Cadences: ", items, max_lines=budget["cadences"])
    if data["touch"]:
        lines += [""] + _wrap("Touch: ", _touch_items(data["touch"]), max_lines=budget["touch"])

    lines += ["", "Ask Daniel about:"]
    for n, m in enumerate(data["ask"], 1):
        lines.append(f"{n}. {m['at']} (replay {m['replay'][0]}-{m['replay'][1]}), {m['category']}: {m['what']}.")
        lines.append(f"   In plain words: {m['plain'][0].upper() + m['plain'][1:]} Ask: {m['ask']}")
    if not data["ask"]:
        lines.append("  nothing stood out enough to ask about")
    lines += [""] + _wrap("Data caveats: ", data["caveats"], max_lines=budget["caveats"])
    return "\n".join(lines)


# -------------------------------------------------------------------------------------------------- compare
def profile(sess: dict) -> dict:
    doc = sess["doc"]
    voc, col = vocabulary(doc), colour_data(doc)
    tch = touch_data(doc, sess["snd"])
    cores: Dict[str, float] = {}
    for w in doc["windows"] if doc["notes"] else []:
        if is_chord(w) and core_number(w):
            cores[core_number(w)] = cores.get(core_number(w), 0.0) + w["seconds"]
    total = sum(cores.values()) or 1.0
    moves = progression_data(doc, (2,), 2)["moves"]["2"]
    dom = col["dominants"]["summary"]
    return {"session": sess["session"], "played": _local(sess["start"]), "length": clock(doc["duration_s"] * 1000),
            "notes": doc["notes"], "home_key": doc["home_key"] if doc["notes"] else None,
            "areas": [f"{a['at']} {a['key']}" for a in doc["keys"]["areas"]] if doc["notes"] else [],
            "chord_seconds": voc["chord_seconds"], "classes": voc["classes"],
            "numbers": {k: _r(v / total, 3) for k, v in sorted(cores.items(), key=lambda kv: -kv[1])},
            "letters": {c["chord"]: c["seconds"] for c in voc["chords"]},
            "colours": {c["colour"]: c["share"] for c in col["colours"]},
            "lydian_4": len(col["lydian_4"]), "pedal_points": len(col["pedal_points"]),
            "cadences": {g["kind"]: g["count"] for g in cadence_kinds(doc["findings"]["cadences"])} if doc["notes"] else {},
            "suspended_dominant_s": (dom.get("suspended") or {}).get("seconds", 0.0),
            "major_3rd_dominant_s": (dom.get("with its major 3rd") or {}).get("seconds", 0.0),
            "moves": {" -> ".join(g["numbers"]): g["count"] for g in moves},
            "touch": tch and {"velocity_mean": tch["velocity"]["mean"] if tch["velocity"] else None,
                              "pedal_percent": tch["pedal"]["percent_down"],
                              "notes_per_minute": tch["notes_per_minute"],
                              "mean_spread": tch["chords"]["mean_spread"] if tch["chords"] else None}}


def compare_data(a: dict, b: dict) -> dict:
    pa, pb = profile(a), profile(b)
    na, nb = pa["numbers"], pb["numbers"]
    shared = sorted(set(na) & set(nb), key=lambda t: -(na[t] + nb[t]))
    return {"a": pa, "b": pb,
            "numbers": {"shared": [[t, na[t], nb[t]] for t in shared],
                        "only_a": [[t, na[t]] for t in na if t not in nb], "only_b": [[t, nb[t]] for t in nb if t not in na],
                        "overlap": _r(sum(min(na.get(t, 0), nb.get(t, 0)) for t in set(na) | set(nb)), 3)},
            "letters_shared": sorted(set(pa["letters"]) & set(pb["letters"]),
                                     key=lambda c: -(pa["letters"][c] + pb["letters"][c])),
            "moves_shared": sorted(set(pa["moves"]) & set(pb["moves"]),
                                   key=lambda m: -(pa["moves"][m] + pb["moves"][m]))}


def _or_dash(x):
    return "-" if x is None else x


def render_compare(data: dict) -> str:
    a, b = data["a"], data["b"]
    width = 44

    def row(label, x, y):
        return f"{label:<26} {str(x):<{width}} {y}"

    def top(d, n=6, fmt=_pct):
        return ", ".join(f"{k} {fmt(v)}" for k, v in list(d.items())[:n]) or "-"
    ta, tb = a["touch"] or {}, b["touch"] or {}
    lines = [f"Compare: A = {a['session']} (played {a['played']}), B = {b['session']} (played {b['played']})", "",
             row("", "A", "B"), row("length, notes", f"{a['length']}, {a['notes']}", f"{b['length']}, {b['notes']}"),
             row("home key", a["home_key"] or "-", b["home_key"] or "-")]
    for i in range(max(len(a["areas"]), len(b["areas"]))):
        lines.append(row("key areas" if i == 0 else "", a["areas"][i] if i < len(a["areas"]) else "",
                         b["areas"][i] if i < len(b["areas"]) else ""))
    lines += [row("chord seconds", a["chord_seconds"], b["chord_seconds"]),
              row("chord time by class", top(a["classes"], 4), top(b["classes"], 4)),
              row("Lydian 4 (times)", a["lydian_4"], b["lydian_4"]),
              row("dominants: suspended s", a["suspended_dominant_s"], b["suspended_dominant_s"]),
              row("dominants: major 3rd s", a["major_3rd_dominant_s"], b["major_3rd_dominant_s"]),
              row("pedal points", a["pedal_points"], b["pedal_points"]),
              row("cadences (by kind)", top(a["cadences"], 3, lambda v: f"x{v}"), top(b["cadences"], 3, lambda v: f"x{v}")),
              row("velocity mean", _or_dash(ta.get("velocity_mean")), _or_dash(tb.get("velocity_mean"))),
              row("pedal down %", _or_dash(ta.get("pedal_percent")), _or_dash(tb.get("pedal_percent"))),
              row("notes a minute", _or_dash(ta.get("notes_per_minute")), _or_dash(tb.get("notes_per_minute"))),
              row("chord spread (semitones)", _or_dash(ta.get("mean_spread")), _or_dash(tb.get("mean_spread"))), ""]
    lines.append("Colour (share of chord time):")
    for colour in [c for c in COLOUR_ORDER if c in a["colours"] or c in b["colours"]]:
        lines.append(row("  " + colour.split(" (")[0], _pct(a["colours"].get(colour)), _pct(b["colours"].get(colour))))
    n = data["numbers"]
    lines += ["", f"Numbers (quality only; share of each session's chord time). Overlap {_pct(n['overlap'])}: the chord "
                  f"time the two sessions spend on the same numbers."]
    lines += _wrap("  both: ", [f"{t} {_pct(x)}/{_pct(y)}" for t, x, y in n["shared"]], max_lines=3, sep=", ")
    lines += _wrap("  only A: ", [f"{t} {_pct(x)}" for t, x in n["only_a"]] or ["-"], max_lines=2, sep=", ")
    lines += _wrap("  only B: ", [f"{t} {_pct(x)}" for t, x in n["only_b"]] or ["-"], max_lines=2, sep=", ")
    lines += _wrap("Chords (letters) in both: ", data["letters_shared"][:20] or ["none"], max_lines=2, sep=", ")
    lines += _wrap("Moves played at least twice in both: ",
                   [f"{m} ({a['moves'][m]}/{b['moves'][m]})" for m in data["moves_shared"]] or ["none"], max_lines=2)
    return "\n".join(lines)


# -------------------------------------------------------------------------------------------------- history
HISTORY_MIN_DAYS = 1 / 24  # history looks back at least an hour


def quality_label(suffix: str) -> str:
    return {"": "major triad", "m": "minor triad"}.get(suffix, suffix)


def history_data(store: PerformanceStore, days: float = 30, now: Optional[datetime] = None, theory_source=None,
                 node: Optional[str] = None) -> dict:
    """Across the sessions started in the last `days` days: chord numbers and letters by total time, when each chord
    quality was first played, and per-session growth."""
    now = now or datetime.now().astimezone()
    cutoff = now - timedelta(days=days)
    picked, skipped = [], []
    for row in store.list():
        try:
            start = session_start(store.info(row["session"]))
        except (PerformanceError, ValueError, OSError) as exc:
            skipped.append({"session": row["session"], "error": f"session.json is unreadable ({type(exc).__name__})"})
            continue
        if start and start >= cutoff:
            picked.append((start, row["session"]))
    numbers: Dict[str, dict] = {}
    letters: Dict[str, float] = {}
    qualities: Dict[str, dict] = {}
    growth = []
    for start, sid in sorted(picked):
        try:
            sess = load_session(store, sid, theory_source, node)
        except PerformanceError as exc:
            skipped.append({"session": sid, "error": str(exc)})
            continue
        doc = sess["doc"]
        chords = [w for w in doc["windows"] if is_chord(w)] if doc["notes"] else []
        seen_here, new_here = set(), []
        for w in chords:
            p = _parts(w)
            q = quality_label(p["suffix"]) if p else None
            if q:
                slot = qualities.setdefault(q, {"quality": q, "first_played": _local(start), "session": sid,
                                                "at": w["at"], "start_ms": w["start_ms"], "chord": w["analysed_as"],
                                                "seconds": 0.0, "sessions": [], "_order": (start, w["start_ms"])})
                slot["seconds"] = _r(slot["seconds"] + w["seconds"], 2)
                if sid not in slot["sessions"]:
                    slot["sessions"].append(sid)
                    if slot["session"] == sid and q not in new_here and len(growth) > 0:
                        new_here.append(q)
                seen_here.add(q)
            num = harmony_number(w)
            if num:
                ns = numbers.setdefault(num, {"number": num, "seconds": 0.0, "sessions": 0, "last": None,
                                              "first_played": _local(start)})
                ns["seconds"] = _r(ns["seconds"] + w["seconds"], 2)
                if ns["last"] != sid:
                    ns["sessions"] += 1
                    ns["last"] = sid
            label = w.get("label") or w["analysed_as"]
            letters[label] = _r(letters.get(label, 0.0) + w["seconds"], 2)
        chord_s = sum(w["seconds"] for w in chords)
        outside_s = sum(w["seconds"] for w in chords if w["class"] not in NON_CHORD_CLASSES)
        tch = touch_data(doc, sess["snd"])
        growth.append({"session": sid, "played": _local(start), "length": clock(doc["duration_s"] * 1000),
                       "home_key": doc["home_key"] if doc["notes"] else None, "chord_seconds": _r(chord_s, 1),
                       "qualities": len(seen_here), "new_qualities": new_here,
                       "numbers": len({harmony_number(w) for w in chords if harmony_number(w)}),
                       "outside_share": _r(outside_s / chord_s, 2) if chord_s else None,
                       "lydian_4": len(doc["findings"]["lydian_4"]) if doc["notes"] else 0,
                       "notes_per_minute": tch["notes_per_minute"] if tch else None,
                       "mean_spread": tch["chords"]["mean_spread"] if tch and tch["chords"] else None,
                       "cadences": {g["kind"]: g["count"] for g in cadence_kinds(doc["findings"]["cadences"])}
                       if doc["notes"] else {}})
    for ns in numbers.values():
        ns.pop("last")
    ordered = sorted(qualities.values(), key=lambda s: s["_order"])
    for q in ordered:
        q.pop("_order")
    return {"days": days, "since": _local(cutoff), "sessions": len(growth), "unreadable": skipped,
            "numbers": sorted(numbers.values(), key=lambda s: -s["seconds"]),
            "letters": [[c, s] for c, s in sorted(letters.items(), key=lambda kv: -kv[1])],
            "qualities": ordered,
            "growth": growth}


def render_history(data: dict) -> str:
    lines = [f"History: {data['sessions']} sessions started since {data['since']} (the last {data['days']:g} days)"]
    for s in data.get("unreadable", []):
        lines.append(f"(left out, unreadable: {s['error'] if s['session'] in s['error'] else s['session'] + ': ' + s['error']})")
    if not data["growth"]:
        return "\n".join(lines + ["", "No sessions in that time."])
    lines += ["", "Growth, oldest first (qualities: different chord types; outside: share of chord time outside the "
                  "key area's key):",
              f"{'played':<17} {'length':>6} {'home key':<10} {'chord s':>7} {'qualities':>9} {'numbers':>7} "
              f"{'outside':>7} {'Lydian 4':>8} {'notes/min':>9} {'spread':>6}  new qualities"]
    for g in data["growth"]:
        lines.append(f"{g['played']:<17} {g['length']:>6} {(g['home_key'] or '-'):<10} {g['chord_seconds']:>7} "
                     f"{g['qualities']:>9} {g['numbers']:>7} {_pct(g['outside_share']):>7} {g['lydian_4']:>8} "
                     f"{_or_dash(g['notes_per_minute']):>9} {_or_dash(g['mean_spread']):>6}  "
                     f"{', '.join(g['new_qualities']) or '-'}")
    kinds: Dict[str, List[int]] = {}
    for g in data["growth"]:
        for kind, count in (g.get("cadences") or {}).items():
            kinds.setdefault(kind, []).append(count)
    if kinds:
        items = [f"{k} x{sum(v)} in {len(v)} session{'s' if len(v) != 1 else ''}"
                 for k, v in sorted(kinds.items(), key=lambda kv: -sum(kv[1]))]
        landings = sum(sum(v) for k, v in kinds.items() if k.endswith("-> 1"))
        if landings >= 3 and not any(k in kinds for k in DOMINANT_ARRIVALS):
            items.append(f"none of the {landings} landings on 1 comes from the 5 chord")
        lines += [""] + _wrap("Cadences by kind: ", items, max_lines=3)
    lines += ["", "Numbers by total time (bass left out; each in its own key area):"]
    for n in data["numbers"][:25]:
        lines.append(f"  {n['seconds']:>7.1f} s  {n['number']:<18} in {n['sessions']} session"
                     f"{'s' if n['sessions'] != 1 else ''}, first {n['first_played']}")
    lines += ["", "Chord qualities, by when each was first played:"]
    for q in data["qualities"]:
        lines.append(f"  {q['quality']:<18} first {q['first_played']} at {q['at']} ({q['chord']}); "
                     f"{q['seconds']} s in {len(q['sessions'])} session{'s' if len(q['sessions']) != 1 else ''}")
    lines += [""] + _wrap("Chords (letters) by total time: ", [f"{c} {s:.1f} s" for c, s in data["letters"][:20]],
                          max_lines=3, sep=", ")
    return "\n".join(lines)


# ================================================================================================= CLI
def _parse_ns(text: str) -> Tuple[int, ...]:
    m = re.fullmatch(r"\s*([2-4])\s*(?:(?:\.\.|-)\s*([2-4]))?\s*", str(text))
    if m:
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        return tuple(range(min(lo, hi), max(lo, hi) + 1))
    parts = [p for p in re.split(r"[,\s]+", str(text)) if p]
    if parts and all(p in ("2", "3", "4") for p in parts):
        return tuple(sorted({int(p) for p in parts}))
    raise ValueError(f"--n takes 2, 3, 4, a range like 2..4, or a list like 2,3 (got {text!r})")


def _finish(args, payload, text: str) -> int:
    """Print (and with --out also write) JSON with --json, else the text followed by the words it used."""
    if getattr(args, "json", False) or args.verb == "analyze":
        text = json.dumps(payload, indent=2, ensure_ascii=False)
    elif "\nWords:\n" not in text:  # (the brief carries its own, fitted to its line cap)
        home = payload.get("home_key") if isinstance(payload, dict) else \
            next((p.get("home_key") for p in payload if isinstance(p, dict) and p.get("home_key")), None) \
            if isinstance(payload, list) else None
        text = text.rstrip("\n") + "\n".join([""] + glossary(text, home))
    text = text.rstrip("\n") + "\n"
    if getattr(args, "out", None):
        out = Path(args.out)
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8", newline="\n")
        except OSError as exc:
            print(f"--out {args.out} could not be written ({type(exc).__name__}: {exc})", file=sys.stderr)
            return 2
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


def _session_verb(args, sess: dict, t_ms: float = 0.0) -> Tuple[object, str]:
    """(JSON payload, text) of one session verb on one loaded session."""
    doc, verb, head = sess["doc"], args.verb, headline(sess)
    empty = "" if doc["notes"] else "\n\nNo notes logged yet."
    if verb == "brief":
        data = brief_data(sess)
        return data, render_brief(sess, data)
    if verb == "chords":
        data = {"session": sess["session"], **vocabulary(doc, args.min_seconds)}
        return data, render_chords(sess, data)
    if verb == "progressions":
        data = {"session": sess["session"], **progression_data(doc, _parse_ns(args.n), args.min_count, args.exact)}
        return data, render_progressions(sess, data)
    if verb == "keys":
        evidence = key_evidence(doc, sess["snd"])
        data = {"session": sess["session"], "home_key": doc["home_key"] if doc["notes"] else None, **doc["keys"],
                "evidence": evidence}
        return data, head + (empty or "\n\n" + render_keys(doc, evidence))
    if verb == "borrowed":
        data = {"session": sess["session"], **borrowed_data(doc)}
        return data, render_borrowed(sess, data)
    if verb == "colors":
        data = {"session": sess["session"], **colour_data(doc)}
        return data, render_colors(sess, data)
    if verb == "moment":
        data = {"session": sess["session"], **moment_data(sess, t_ms, args.window * 1000)}
        return data, render_moment(sess, data)
    if verb == "windows":
        lo = parse_clock(args.start) if args.start else 0
        hi = parse_clock(args.end) if args.end else math.inf
        return doc, head + (empty or "\n\n" + render_windows(doc, args.limit, lo, hi))
    if verb == "harmony":
        return doc, head + (empty or "\n\n" + render_harmony(doc))
    return doc, ""  # analyze


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["riff"]:  # riff analysis over a jam run: arsenal/practice_riff.py (jam-spec section 11)
        return __import__(f"{__package__}.practice_riff", fromlist=["main"]).main(argv[1:])
    parser = argparse.ArgumentParser(prog="py -m arsenal.practice",
                                     description="Harmony verbs over the piano practice log (read only).")
    sub = parser.add_subparsers(dest="verb", required=True)

    def add(verb: str, text: str, session: bool = True, root: bool = True):
        p = sub.add_parser(verb, help=text, description=text)
        if session:
            p.add_argument("session", nargs="?", default="latest",
                           help="a session id, latest (the default), or today (every session started today)")
        if root:
            p.add_argument("--root", help="the sessions directory (default: state/arsenal/performance)")
        p.add_argument("--json", action="store_true", help="print JSON instead of text")
        p.add_argument("--out", help="also write the output to this file")
        return p
    sub.add_parser("list", help="session ids, newest first (no analysis)").add_argument("--root")
    add("sessions", "sessions: local start time, length, notes, home key, key areas", session=False).add_argument(
        "which", nargs="?", default="all", choices=("all", "today"))
    add("brief", "the one page to read before talking to Daniel about a session")
    add("chords", "chord vocabulary by time: letters, numbers, class").add_argument(
        "--min-seconds", type=float, default=0.0, help="only chords held at least this long")
    p = add("progressions", "moves and loops in numbers, with first times")
    p.add_argument("--n", default="2..4", help="chords per move: 2, 3, 4, or a range like 2..4 (default)")
    p.add_argument("--min-count", type=int, default=2, help="moves played at least this many times (default 2)")
    p.add_argument("--exact", action="store_true", help="full numbers (4maj9#11) instead of quality only (4)")
    add("keys", "key areas with the evidence for each change")
    add("borrowed", "chords outside the key, with their source and times")
    add("colors", "colour habits: extensions, sus, Lydian 4, dominants, pedal points")
    p = add("moment", "notes, windows, key and numbers around a time", session=False)
    p.add_argument("where", nargs="+", metavar="[SESSION] M:SS", help="an optional session (default latest), then a time")
    p.add_argument("--window", type=float, default=5.0, help="seconds either side of the time (default 5)")
    p = add("name", "name a voicing: every reading, numbered in --key", session=False, root=False)
    p.add_argument("notes", nargs="+", help="note names with octaves (Ab3 Eb4 G4) or MIDI numbers")
    p.add_argument("--key", help="a key to number and classify in, e.g. 'Eb major' or 'C minor'")
    p = add("compare", "two sessions side by side: keys, vocabulary overlap, habits", session=False)
    p.add_argument("a")
    p.add_argument("b")
    add("history", "across sessions: chords by total time, first-seen qualities, growth", session=False).add_argument(
        "--days", type=float, default=30.0, help="sessions started in the last N days (default 30)")
    p = add("windows", "the session cut into harmonic windows, named and numbered")
    p.add_argument("--limit", type=int, default=None, help="show at most this many windows")
    p.add_argument("--from", dest="start", default=None, help="only windows from this time (m:ss)")
    p.add_argument("--to", dest="end", default=None, help="only windows before this time (m:ss)")
    add("harmony", "findings: keys, Lydian 4, dominants, borrowed chords, cadences, ...")
    add("analyze", "everything, as JSON")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # piped on Windows the console code page would mangle names like C°7
        if (getattr(stream, "encoding", "") or "").lower().replace("-", "") != "utf8":
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, ValueError, OSError):
                pass
    try:
        if getattr(args, "out", None) and Path(args.out).is_dir():
            raise ValueError(f"--out {args.out} is a directory; give a file path")
        if getattr(args, "root", None) and Path(args.root).exists() and not Path(args.root).is_dir():
            raise ValueError(f"--root {args.root} is a file; give the sessions directory")
        for name in ("session", "a", "b"):
            if getattr(args, name, None) is not None and not str(getattr(args, name)).strip():
                raise ValueError("an empty session: give a session id, latest or today")
        if args.verb == "list":
            for row in PerformanceStore(args.root).list():
                print(f"{row['session']}  {row['duration_s']:>8} s  {row['event_count']:>6} events"
                      f"{'' if row['closed'] else '  (open)'}")
            return 0
        if args.verb == "name":
            data = name_data(args.notes, args.key)
            return _finish(args, data, render_name(data))
        store = PerformanceStore(args.root)
        if args.verb == "sessions":
            rows = sessions_data(store, args.which)
            return _finish(args, rows, render_sessions(rows))
        if args.verb == "history":
            if not math.isfinite(args.days):
                raise ValueError(f"--days must be a number of days (got {args.days:g})")
            if not args.days >= HISTORY_MIN_DAYS:
                raise ValueError(f"--days must be at least {HISTORY_MIN_DAYS:.3f} (one hour; got {args.days:g})")
            data = history_data(store, args.days)
            return _finish(args, data, render_history(data))
        if args.verb == "compare":
            ids = [resolve_sessions(store, s) for s in (args.a, args.b)]
            if any(len(x) != 1 for x in ids):
                raise ValueError("compare takes two single sessions (an id or latest)")
            if ids[0] == ids[1]:
                raise ValueError(f"compare needs two different sessions (both are {ids[0][0]})")
            data = compare_data(load_session(store, ids[0][0]), load_session(store, ids[1][0]))
            return _finish(args, data, render_compare(data))
        t_ms = 0.0
        if args.verb == "moment":
            if len(args.where) > 2:
                raise ValueError("moment takes an optional session and one time: moment [SESSION] M:SS")
            selector, when = args.where if len(args.where) == 2 else ("latest", args.where[0])
            t_ms = parse_clock(when)
            if not math.isfinite(args.window):
                raise ValueError(f"--window must be a number of seconds (got {args.window:g})")
            if not args.window > 0:
                raise ValueError(f"--window must be more than 0 seconds (got {args.window:g})")
        else:
            selector = args.session
            if args.verb == "progressions":
                _parse_ns(args.n)
                if args.min_count < 1:
                    raise ValueError(f"--min-count must be at least 1 (got {args.min_count})")
            if args.verb == "windows":
                times = [parse_clock(text) if text else None for text in (args.start, args.end)]
                if None not in times and times[0] >= times[1]:
                    raise ValueError(f"--from {args.start} must come before --to {args.end}")
                if args.limit is not None and args.limit < 1:
                    raise ValueError(f"--limit must be at least 1 (got {args.limit})")
            if args.verb == "chords" and not (math.isfinite(args.min_seconds) and args.min_seconds >= 0):
                raise ValueError(f"--min-seconds must be a number of seconds, 0 or more (got {args.min_seconds:g})")
        ids = resolve_sessions(store, selector)
        payloads, texts = [], []
        for sid in ids:
            sess = load_session(store, sid)
            if args.verb == "moment" and sess["doc"]["notes"] and t_ms > sess["doc"]["duration_s"] * 1000 + 500:
                raise ValueError(f"{when} is after the end of session {sid} ({clock(sess['doc']['duration_s'] * 1000)} "
                                 f"long)")
            if args.verb == "windows" and args.start and sess["doc"]["notes"] and \
                    parse_clock(args.start) > sess["doc"]["duration_s"] * 1000 + 500:
                raise ValueError(f"--from {args.start} is after the end of session {sid} "
                                 f"({clock(sess['doc']['duration_s'] * 1000)} long)")
            payload, text = _session_verb(args, sess, t_ms)
            payloads.append(payload)
            texts.append(text)
    except PerformanceError as exc:
        print(f"{exc}; try: py -m arsenal.practice sessions", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    return _finish(args, payloads if selector == "today" else payloads[0], "\n\n\n".join(texts))


if __name__ == "__main__":
    sys.exit(main())
