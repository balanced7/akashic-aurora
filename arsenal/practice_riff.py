"""Riff analysis: Daniel's notes read against a jam run's bars and chords, so we can talk about what he played over a
loop (jam-spec section 11; the music behind it is design-music.md section 9).

Read only, like the other practice verbs. Runs come from state/arsenal/jam/runs/<run>/ (run.json + events.jsonl, written
by the jam store), sessions from arsenal.performance.PerformanceStore. Nothing here writes to the practice log; only
--save writes, and only state/arsenal/jam/riffs/<run>.json.

    py -m arsenal.practice riff [RUN|latest] [--session SESSION] [--root DIR] [--jam-root DIR]
                                [--card CARD --key KEY --bpm N --from m:ss [--to m:ss]]
                                [--bars A-B] [--pass N] [--json] [--out FILE] [--save]

The pipeline (11.3), for each run lined up with a session:
1. Timeline. The run's segments, settings and def versions (from events.jsonl: the start line and every `next` change)
   expand into slot instances [start, end) in session t_ms, each with its pass, bar and the slot's chord facts.
2. His notes: practice.sounding(events). Attacks are note-ons within ONSET_GROUP_MS; the top line is each attack's
   highest note at C4 or above (with backing `full`, above the backing's top voice, at most A4 + 1). A top-line note
   lasts until the next top-line onset or its key release, capped at 2 beats: the pedal never stretches it.
3. Grid and weight from the tempo map (arsenal/jam/tempomap.py): grid class, metric weight w_m, note weight w.
4. Which chord (with anticipations), 5. the class and label of every note, 6. the scale per slot with the naming gate,
7. landings, 8. top-note degrees by bar, 9. his own reading of struck chords (piano.js Theory.detect through
   practice_theory.mjs, one node call), 10. per pass facts, 11. phrases, 12. card checks, 13. the loopback guard,
14. highlights. Then talking points (T1-T7, T10, T13, T14), one question and one thing to try (11.4).

Counting, everywhere in the output: `pass`, `bar` (inside the pass) and `run_bar` count from 1; `beat` is the position
inside the bar from 0 (a pickup phrase's beat is negative, before its bar line); `slot` counts from 0 as in def.slots.

Alignment (11.2) is the L1-L4 ladder: L1 an ack from the page whose log.session is the session; L2 the session's
meta.page_id and meta.t0_perf_ms against an ack of that page; L3 meta.opened_at_client; L4 the server's opened_at
(refused for a buffered session). --card/--from gives `assumed`.

Choices this module makes where the spec leaves room (all written into the output's constants):
- A slot's classes, labels and landings count the top line (the melody); `all_notes` counts every note of his.
- Shares fold a rub into colour and a slide-in into outside (the words Daniel sees, MUSIC 9.6).
- A phrase's `bars` counts the phrase and its breath (the gap after it, at most one phrase gap), to the nearest half
  bar, so a two-bar phrase in a two-bar loop reads 2 whatever its last note's length.
- The scale naming gate extends MUSIC 9.7's table to every candidate (SCALE_CANDIDATES: own notes, notes used with).
- His own reading uses only attacks of 3 or more notes (a melody is not read as a chord).
- The loopback guard rebuilds Claude's notes through arsenal/groove_bridge.mjs when it answers; otherwise from the def:
  each chord's downbeat strikes (bass always, the upper voices when humanize is 0), ties skipped.
- Free play (no run) has no grid: a nominal FREE_BEAT_MS beat, no passing class, phrases in seconds, no T10 or T14.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import time
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import nashville
from . import practice as pr
from .jam import DEF_API, RIFF_API
from .jam import schemas
from .jam import tempomap as tm
from .jam.resolve import tone_name
from .performance import PerformanceError, PerformanceStore

HERE = Path(__file__).resolve().parent
DEFAULT_JAM_ROOT = HERE.parent / "state" / "arsenal" / "jam"
GROOVE_BRIDGE = HERE / "groove_bridge.mjs"

# ============================================================================================ constants (11.3, 11.4)
ONSET_GROUP_MS = pr.ONSET_GROUP_MS  # 50: note-ons this close to an attack's first onset belong to that attack
LINE_MIN_NOTE = 60                  # C4: the top line starts here...
LINE_FULL_MAX = 70                  # ...or above backing full's top voice, at most A4 + 1
LINE_LEN_CAP_BEATS = 2              # a note's length is capped here (the pedal never stretches it)
GRID_TOL = 0.08                     # beat
METRIC_WEIGHTS = {"downbeat": 1.0, "beat3": 0.8, "beat": 0.6, "offbeat": 0.4, "other": 0.3}
WEIGHT_LEN = (0.25, 2.0)            # w = w_m * clamp(length in beats, 0.25, 2)
ANTICIPATE_MAX = (0.5, 300)         # min(0.5 beat, 300 ms)
ONSET_EPS_MS = 1.0                  # the log keeps whole ms: an onset this close before a bar or chord line is on it
PASSING_MAX_BEATS = 1               # a passing rub is shorter than this...
PASSING_W_MAX = 0.6                 # ...on a weaker position than this...
PASSING_STEP = 2                    # ...and steps at most this many semitones...
PASSING_WITHIN_BEATS = 0.5          # ...to a chord tone or colour within this long after it ends
SLIDE_IN_MAX = (0.5, 300)           # a slide-in lasts at most min(0.5 beat, 300 ms)...
SLIDE_IN_RESOLVE_BEATS = 1          # ...and the next top-line note, this soon, is a half step away
SCALE_MIN_NOTES = 12
SCALE_SIZE_COST = 0.04
SCALE_UNUSED_COST = 0.05
SCALE_UNUSED_SHARE = 0.02
MODE_OWN_NOTE_MIN = 0.05
PENT_LEFT_OUT_MAX = 0.03
LANDING_BEFORE = (0.5, 300)         # a landing is his first top-line onset from min(0.5 beat, 300 ms) before a chord...
LANDING_AFTER_MS = 250              # ...to 250 ms after it
PHRASE_GAP = (1, 600)               # a top-line gap of max(1 beat, 600 ms) ends a phrase
PHRASE_MAX_BARS = 4                 # a longer phrase splits at its longest inner gap...
PHRASE_SPLIT_MIN_BEATS = 0.5        # ...of at least this long
CONTOUR_STEP = 3
CONTOUR_FLAT_RANGE = 4
READING_MIN_NOTES = 3
LOOPBACK_MS = 15
LOOPBACK_SHARE = 0.5
MIN_ONSETS = 8
CHAT_POINTS = 6
TP_WEIGHTS = {"T1": 1.0, "T2": 1.1, "T3": 0.9, "T4": 1.0, "T5": 1.0, "T6": 0.8, "T7": 0.8, "T10": 0.8, "T13": 0.8,
              "T14": 0.7}
SALIENCE_COUNT = 5
CONCEPT_BOOST = 1.25
REPEAT_DAMP = 0.5
T1_LABEL_SHARE = 0.2
T1_MIN = 4
T3_MIN_PHRASES = 6
T5_MIN = 2
T6_MAX_RATE = 1 / 200
T6_MIN_NOTES = 100
T7_MIN = 3
T10_MIN_PHRASES = 6
T13_MIN_PASSES = 4
T13_MIN_CHANGE = 0.10
T13_MIN_PASS_NOTES = 4    # a pass counts toward T13 only when it holds his playing (top-line notes)
T13_MIN_NOTES = 8         # and each side of the comparison needs this many top-line notes
TRY_EARLY_MIN_PHRASES = 3  # try rule 4 ("start one phrase a beat early") needs a few phrases to speak of
T14_MIN = 3
QUESTION_RARE_LANDING = 0.10
QUESTION_WEIGHTS = {"rub": 1.0, "outside": 0.9, "landing": 0.8}
QUESTION_REPLAY_S = 4
TRY_CONCEPT_MIN = 2
TRY_HELD_RUBS = 3
TRY_TARGET_LOW = 70                 # Bb4: his register, where a target note is offered
HIGHLIGHTS = 3
HIGHLIGHT_LEAD_S = 3
HIGHLIGHT_SECONDS = 6
ALIGN_ERROR_MS = {"L1": 2.0, "L2": 2.0, "L3": 50.0, "L4": 150.0}
FREE_BEAT_MS = 1000.0
FREE_W_M = 0.6
FORBIDDEN_WORDS = ("wrong", "mistake", "error", "score", "best", "should", "correct")
THEORY_WORDS = ("Lydian", "Dorian", "Mixolydian", "Aeolian", "Phrygian", "Locrian", "pentatonic", "blues", "diminished",
                "whole tone", "melodic minor", "harmonic minor", "altered", "borrowed", "modal", "chromatic",
                "secondary dominant")

# (name, intervals above the root, own-note groups (one note of each group carries MODE_OWN_NOTE_MIN), notes used with)
SCALE_CANDIDATES = (
    ("major", (0, 2, 4, 5, 7, 9, 11), ((5,),), (4, 11)),
    ("Dorian", (0, 2, 3, 5, 7, 9, 10), ((9,),), (3,)),
    ("Phrygian", (0, 1, 3, 5, 7, 8, 10), ((1,),), ()),
    ("Lydian", (0, 2, 4, 6, 7, 9, 11), ((6,),), ()),
    ("Mixolydian", (0, 2, 4, 5, 7, 9, 10), ((10,),), ()),
    ("Aeolian", (0, 2, 3, 5, 7, 8, 10), ((8,),), (3,)),
    ("Locrian", (0, 1, 3, 5, 6, 8, 10), ((6,),), (3,)),
    ("melodic minor", (0, 2, 3, 5, 7, 9, 11), ((11,),), (3, 9)),
    ("Lydian dominant", (0, 2, 4, 6, 7, 9, 10), ((6,), (10,)), ()),
    ("altered", (0, 1, 3, 4, 6, 8, 10), ((1, 3), (8,)), ()),
    ("harmonic minor", (0, 2, 3, 5, 7, 8, 11), ((11,),), (3, 8)),
    ("Phrygian dominant", (0, 1, 4, 5, 7, 8, 10), ((1,),), (4,)),
    ("major pentatonic", (0, 2, 4, 7, 9), None, ()),
    ("minor pentatonic", (0, 3, 5, 7, 10), None, ()),
    ("minor blues", (0, 3, 5, 6, 7, 10), ((6,),), (3,)),
    ("major blues", (0, 2, 3, 4, 7, 9), ((3,),), (4,)),
    ("whole-half diminished", (0, 1, 3, 4, 6, 7, 9, 10), ((1,), (3,)), (9,)),
    ("whole tone", (0, 2, 4, 6, 8, 10), ((6,), (8,)), (4,)),
)
PENT_LEFT_OUT = {"major pentatonic": (5, 11), "minor pentatonic": (2, 8)}  # the two notes of its parent scale it drops

CHORD_LABELS = {0: "R", 3: "b3", 4: "3", 5: "4", 6: "b5", 7: "5", 8: "#5", 9: "6", 10: "b7", 11: "7"}
INTERVAL_LABELS = {0: "R", 1: "b9", 2: "9", 3: "b3", 4: "3", 5: "11", 6: "#11", 7: "5", 8: "b13", 9: "13", 10: "b7",
                   11: "7"}
ROLE_INTERVALS = {"1": 0, "b3": 3, "3": 4, "4": 5, "#4": 6, "5": 7, "b6": 8, "6": 9, "b7": 10, "7": 11, "b9": 1, "9": 2,
                  "#9": 3, "11": 5, "#11": 6, "b13": 8, "13": 9}
CLASSES = ("in_chord", "colour", "rub", "passing", "slide_in", "outside")
WORD_OF = {"in_chord": "in_chord", "colour": "colour", "passing": "colour", "rub": "colour", "slide_in": "outside",
           "outside": "outside"}
CONTROL_WORDS = {"in_chord": "in the chord", "colour": "a colour", "rub": "a rub", "passing": "a colour",
                 "slide_in": "outside", "outside": "outside"}
METHOD_WORDS = {"L1": "the page's own clock", "L2": "the page clock the session named", "L3": "the page's wall clock",
                "L4": "the server's open time (approximate)", "assumed": "the start time you gave (assumed)"}


class RiffError(Exception):
    """A guard (11.5): the message is printed and the verb exits with `code`."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


# ============================================================================================== helpers
def _r(x, places: int = 3):
    return None if x is None else round(float(x), places)


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _half(x: float) -> float:
    """Rounded to the nearest half, halves up (1.75 -> 2.0)."""
    return math.floor(x * 2 + 0.5) / 2


def _fmt(x) -> str:
    """2.0 -> '2', 1.5 -> '1.5'."""
    x = float(x)
    return str(int(x)) if x == int(x) else f"{x:g}"


def _times(n: int) -> str:
    return f"{n} time" if n == 1 else f"{n} times"


def _iso_epoch_ms(text) -> Optional[float]:
    if not isinstance(text, str):
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp() * 1000


def _local(epoch_ms: Optional[float]) -> str:
    if epoch_ms is None:
        return "an unknown time"
    return datetime.fromtimestamp(epoch_ms / 1000).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _median(values: Sequence[float]) -> Optional[float]:
    v = sorted(values)
    if not v:
        return None
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def _p90(values: Sequence[float]) -> Optional[float]:
    v = sorted(values)
    return v[max(0, math.ceil(0.9 * len(v)) - 1)] if v else None


def _pc_of_name(name: str) -> Optional[int]:
    sp = pr._parse_name(name or "")
    return pr._sp_pc(sp) if sp else None


def _degree(number: Optional[str]) -> Optional[str]:
    m = re.match(r"^(#{1,2}|b{1,2})?[1-7]", number or "")
    return m.group(0) if m else None


def replay_command(session: str, t_ms: float, seconds: float) -> str:
    return f"py -m arsenal.pianocue replay {session} {pr.clock(max(0.0, t_ms))} --seconds {_fmt(seconds)}"


def save_command(session: str, t_ms: float) -> str:
    return f"py -m arsenal.pianocue template save-from-moment {session} {pr.clock(t_ms)}"


# ========================================================================================= chord facts
def slot_facts(slot: dict) -> dict:
    """What a slot's chord means for his notes (MUSIC 9.5): tones T (chord_pcs), scale S, rubs A, labels."""
    tones = slot.get("tones_pc") or {}
    root = tones.get("root", slot.get("bass_pc", 0))
    chord = set(slot.get("chord_pcs") or tones.values())
    key = slot.get("key")
    kinfo = nashville.parse_key(key) if key else None
    key_pcs = pr.key_scale(kinfo["name"]) if kinfo else set()
    scale = set(slot.get("scale") or ()) or set(key_pcs)
    rel = {r: (pc - root) % 12 for r, pc in tones.items()}
    dominant = rel.get("third") == 4 and rel.get("seventh") == 10
    sus = "sus" in tones
    rubs = {pc for pc in scale if pc not in chord and (pc - 1) % 12 in chord}
    if dominant:
        rubs -= {(root + 1) % 12, (root + 8) % 12}
    if sus and (root + 4) % 12 in scale and (root + 4) % 12 not in chord:
        rubs.add((root + 4) % 12)
    voicings = slot.get("voicings") or {}
    return {"root": root, "bass": slot.get("bass_pc", root), "chord": chord, "scale": scale, "rubs": rubs,
            "dominant": dominant, "sus": sus, "major_third": rel.get("third") == 4,
            "roles": {pc: r for r, pc in tones.items()}, "key": kinfo["name"] if kinfo else key,
            "key_scale": key_pcs, "name": slot.get("name"), "number": slot.get("n"), "class": slot.get("class"),
            "full_top": max(voicings.get("full") or [0]) or None, "slot": slot}


def tone_label(f: dict, pc: int) -> str:
    """A pitch class's name over the chord: R b3 3 4 b5 5 #5 6 b7 7 for chord tones, b9 9 #9 11 #11 b13 13 for colours."""
    i = (pc - f["root"]) % 12
    role = f["roles"].get(pc)
    if role == "root":
        return "R"
    if role in ("third", "fifth", "sixth", "seventh"):
        return "6" if role == "seventh" and i == 9 else CHORD_LABELS.get(i, INTERVAL_LABELS[i])
    if role == "sus":
        return "4" if i == 5 else "2" if i == 2 else INTERVAL_LABELS[i]
    if role in ("ninth", "eleventh", "thirteenth"):
        return pr.TENSIONS.get(i, INTERVAL_LABELS[i])
    if i == 3 and f["major_third"]:
        return "#9"
    if i == 5 and f["sus"]:
        return "4"
    return INTERVAL_LABELS[i]


def bass_label(f: dict, pc: int) -> str:
    return INTERVAL_LABELS[(pc - f["bass"]) % 12]


def score_scales(hist: Dict[int, float]) -> List[dict]:
    """Every candidate scale scored over a weighted interval histogram (shares summing to 1), best first (MUSIC 9.7)."""
    out = []
    for order, (name, steps, own, used_with) in enumerate(SCALE_CANDIDATES):
        coverage = sum(hist.get(i, 0.0) for i in steps)
        unused = sum(1 for i in steps if hist.get(i, 0.0) < SCALE_UNUSED_SHARE)
        score = coverage - SCALE_SIZE_COST * (len(steps) - 5) - SCALE_UNUSED_COST * unused
        out.append({"name": name, "score": score, "order": order, "steps": steps, "own": own, "with": used_with})
    out.sort(key=lambda c: (-round(c["score"], 9), c["order"]))
    return out


def scale_gate(cand: dict, hist: Dict[int, float]) -> Tuple[bool, Optional[int], float]:
    """(named, own interval, its share): the honesty gate. A mode is named only when its own note carries
    MODE_OWN_NOTE_MIN of the weight (and the notes it is used with sound); a pentatonic only when all 5 degrees are used
    and the two notes it leaves out carry PENT_LEFT_OUT_MAX or less."""
    if cand["own"] is None:
        used = all(hist.get(i, 0.0) > 0 for i in cand["steps"])
        left = sum(hist.get(i, 0.0) for i in PENT_LEFT_OUT[cand["name"]])
        return used and left <= PENT_LEFT_OUT_MAX + 1e-9, None, left
    first_i, first_share, ok = None, 0.0, True
    for group in cand["own"]:
        i = max(group, key=lambda g: hist.get(g, 0.0))
        share = hist.get(i, 0.0)
        if first_i is None:
            first_i, first_share = i, share
        ok = ok and share >= MODE_OWN_NOTE_MIN - 1e-9
    ok = ok and all(hist.get(i, 0.0) > 0 for i in cand["with"])
    return ok, first_i, first_share


def scale_for_class(pcs: Sequence[int], root: Optional[int], key: str, cls: Optional[str], suffix: str = "",
                    fits: Sequence[str] = (), detail: str = "", target: Optional[str] = None) -> List[int]:
    """A chord's scale S from its practice.classify class (MUSIC 9.5 table), for chords read from his own playing.
    Any chord tone missing from S replaces the scale note a half step from it."""
    k = nashville.parse_key(key)
    tonic, mode = k["tonic"], k["mode"]
    on = lambda base, steps: {(base + s) % 12 for s in steps}  # noqa: E731
    rel = {(p - root) % 12 for p in pcs} if root is not None else set()
    if cls == "borrowed":
        options = ("natural minor", "harmonic minor") if mode == "major" else ("major",)
        name = next((s for s in fits if s in options), options[0])
        scale = on(tonic, pr.SCALES[name])
    elif cls == "modal":
        name = next((m for m in ("Mixolydian", "Lydian", "Dorian", "Phrygian") if m in (detail or "")), None)
        scale = on(tonic, pr.SCALES[name]) if name else pr.key_scale(k["name"])
    elif cls == "secondary dominant" and root is not None:
        minor_target = bool(target) and target.endswith("m")
        scale = on(root, (0, 1, 4, 5, 7, 8, 10) if minor_target else (0, 2, 4, 5, 7, 9, 10))
    elif cls == "chromatic" and root is not None:
        s = suffix or ""
        if "m7b5" in s:
            steps = (0, 2, 3, 5, 6, 8, 10)
        elif "dim" in s:
            steps = (0, 2, 3, 5, 6, 8, 9, 11)
        elif "sus" in s:
            steps = (0, 2, 4, 5, 7, 9, 10)
        elif 3 in rel and 9 in rel and 10 not in rel:
            steps = (0, 2, 3, 5, 7, 9, 11)
        elif 3 in rel:
            steps = (0, 2, 3, 5, 7, 9, 10)
        elif 4 in rel and 10 in rel:
            steps = (0, 2, 4, 6, 7, 9, 10)
        else:
            steps = (0, 2, 4, 6, 7, 9, 11)
        scale = on(root, steps)
    else:
        scale = pr.key_scale(k["name"])
        if mode == "minor" and (tonic + 11) % 12 in pcs:
            scale = on(tonic, pr.SCALES["harmonic minor"])
    for pc in pcs:
        if pc not in scale:
            for nb in ((pc - 1) % 12, (pc + 1) % 12):
                if nb in scale and nb not in pcs:
                    scale.discard(nb)
                    break
            scale.add(pc)
    return sorted(scale)


# ==================================================================================== runs and sessions
def _read_jsonl(path: Path) -> Tuple[List[dict], int]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], 0
    out, bad = [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(obj, dict):
            out.append(obj)
        else:
            bad += 1
    return out, bad


def load_run(jam_root, run_id: str) -> dict:
    """{run, lines, defs {version: def}, acks, problems} for one run directory. The def versions come from the start
    line and every `next` change; a segment naming a version with no def is a guard (exit 2)."""
    runs_dir = Path(jam_root) / "runs"
    if not isinstance(run_id, str) or not schemas.RUN_ID_RE.match(run_id):
        raise RiffError(f"not a run id: {run_id!r} (runs are named like 20300101-000000-0a1b2c3d)")
    path = runs_dir / run_id / "run.json"
    if not path.is_file():
        raise RiffError(f"no run {run_id} under {runs_dir}")
    try:
        run = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RiffError(f"run {run_id}: run.json is unreadable ({type(exc).__name__}: {exc})") from exc
    problems = []
    try:
        schemas.validate_run(run)
    except schemas.JamSchemaError as exc:
        problems.append(f"run.json does not match the run schema at {exc.field}")
    if not isinstance(run, dict) or not run.get("segments") or not isinstance(run.get("beats_per_bar"), int):
        raise RiffError(f"run {run_id} has no tempo segments yet (a pending run never started)")
    lines, bad = _read_jsonl(path.parent / "events.jsonl")
    if bad:
        problems.append(f"{bad} unreadable line{'s' if bad != 1 else ''} in events.jsonl skipped")
    defs, acks = {}, []
    for line in lines:
        kind = line.get("kind")
        if kind in ("start", "change") and isinstance(line.get("def"), dict) and \
                (kind == "start" or line.get("op") == "next"):
            defs[int(line.get("version") or 1)] = line["def"]
        elif kind == "ack":
            acks.append(line)
    missing = sorted({s.get("def_version") for s in run["segments"]} - set(defs))
    if missing:
        raise RiffError(f"run {run_id}: events.jsonl carries no def for version {', '.join(map(str, missing))}")
    return {"run": run, "lines": lines, "defs": defs, "acks": acks, "problems": problems}


def list_runs(jam_root) -> List[dict]:
    """Every readable run.json under jam_root/runs, newest first (by created_at, then id)."""
    runs_dir = Path(jam_root) / "runs"
    out = []
    if not runs_dir.is_dir():
        return out
    for d in runs_dir.iterdir():
        if not (d.is_dir() and schemas.RUN_ID_RE.match(d.name)):
            continue
        try:
            run = json.loads((d / "run.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(run, dict):
            run.setdefault("run", d.name)
            out.append(run)
    out.sort(key=lambda r: (str(r.get("created_at") or ""), r["run"]), reverse=True)
    return out


def session_window(info: dict) -> Tuple[Optional[float], Optional[float]]:
    """The session's wall-clock span in epoch ms: from the page's open time (opened_at_client) or the server's."""
    meta = info.get("meta") if isinstance(info.get("meta"), dict) else {}
    start = _iso_epoch_ms(meta.get("opened_at_client"))
    if start is None:
        start = info["opened_ns"] / 1e6 if _num(info.get("opened_ns")) and info["opened_ns"] > 0 else \
            _iso_epoch_ms(info.get("opened_at"))
    if start is None:
        return None, None
    length = max(float(info.get("last_t_ms") or 0), float(info.get("duration_s") or 0) * 1000)
    return start, start + length


def run_end_epoch(loaded: dict) -> float:
    """Where the run's analysis stops: its stop, else its stop bar, else (still running) now."""
    run = loaded["run"]
    m, segs = run["beats_per_bar"], run["segments"]
    if _num(run.get("stopped_epoch_ms")):
        return float(run["stopped_epoch_ms"])
    if isinstance(run.get("stop_bar"), int):
        return tm.t_epoch(segs, m, run["stop_bar"])
    bar0 = tm.t_epoch(segs, m, 0)
    return max(bar0, min(time.time() * 1000, bar0 + 6 * 3600 * 1000))


def run_window(loaded: dict) -> Tuple[float, float]:
    """A run's wall-clock span for finding sessions (MUSIC 9.1): one bar before bar 0 to two beats after the stop."""
    run = loaded["run"]
    m, segs = run["beats_per_bar"], run["segments"]
    bar0 = tm.t_epoch(segs, m, 0)
    end = run_end_epoch(loaded)
    return bar0 - tm.bar_ms(tm.segment_at(segs, 0)["bpm"], m), end + 2 * tm.beat_ms(tm.segment_at_epoch(segs, end)["bpm"])


# ============================================================================================ alignment
class Clock:
    """Epoch ms <-> session t_ms through clock pairs (anchors), each used near its own time."""

    def __init__(self, method: str, anchors: List[Tuple[float, float]], error_ms: Optional[float], page_id=None,
                 output_latency_ms=None):
        self.method = method
        self.anchors = sorted(anchors)
        self._epochs = [e for e, _ in self.anchors]
        self._ts = [t for _, t in self.anchors]
        self.error_ms = error_ms
        self.page_id = page_id
        self.output_latency_ms = output_latency_ms

    @staticmethod
    def _nearest(values: List[float], x: float) -> int:
        i = bisect_left(values, x)
        if i <= 0:
            return 0
        if i >= len(values):
            return len(values) - 1
        return i if values[i] - x < x - values[i - 1] else i - 1

    def t_of(self, epoch_ms: float) -> float:
        e, t = self.anchors[self._nearest(self._epochs, epoch_ms)]
        return t + (epoch_ms - e)

    def epoch_of(self, t_ms: float) -> float:
        k = self._nearest(self._ts, t_ms)
        e, t = self.anchors[k]
        return e + (t_ms - t)

    @property
    def approx(self) -> bool:
        return self.method in ("L4", "assumed")


def align(loaded: dict, session: str, info: dict) -> Clock:
    """The L1-L4 ladder (11.2, DATA 7.3) for one run against one session."""
    run, acks = loaded["run"], loaded["acks"]
    meta = info.get("meta") if isinstance(info.get("meta"), dict) else {}
    latency = next((a["output_latency_ms"] for a in reversed(acks) if _num(a.get("output_latency_ms"))), None)
    usable = [a for a in acks if _num(a.get("bar_epoch_ms")) and _num(a.get("perf_ms"))]
    owner = run.get("owner_page_id")

    def prefer_owner(pairs):
        mine = [p for p in pairs if p[2] == owner]
        return mine or pairs

    l1 = prefer_owner([(a["bar_epoch_ms"], a["perf_ms"] - a["log"]["t0_perf_ms"], a.get("page_id")) for a in usable
                       if isinstance(a.get("log"), dict) and a["log"].get("session") == session
                       and _num(a["log"].get("t0_perf_ms"))])
    method, pairs = None, []
    if l1:
        method, pairs = "L1", l1
    elif meta.get("page_id") and _num(meta.get("t0_perf_ms")):
        pairs = [(a["bar_epoch_ms"], a["perf_ms"] - meta["t0_perf_ms"], a.get("page_id")) for a in usable
                 if a.get("page_id") == meta["page_id"]]
        method = "L2" if pairs else None
    if method is None:
        client = _iso_epoch_ms(meta.get("opened_at_client"))
        if client is not None:
            method, pairs = "L3", [(client, 0.0, None)]
        elif meta.get("buffered"):
            raise RiffError(f"session {session} was buffered in the browser and has no meta.opened_at_client, so run "
                            f"{run.get('run')} cannot be lined up with it (L4 is refused for a buffered session)")
        else:
            opened = info["opened_ns"] / 1e6 if _num(info.get("opened_ns")) and info["opened_ns"] > 0 else \
                _iso_epoch_ms(info.get("opened_at"))
            if opened is None:
                raise RiffError(f"session {session} has no open time to line run {run.get('run')} up with")
            method, pairs = "L4", [(opened, 0.0, None)]
    offsets = [t - e for e, t, _ in pairs]
    spread = max(offsets) - min(offsets)
    error = max(ALIGN_ERROR_MS[method], round(spread, 1))
    pages = sorted({p for _, _, p in pairs if p})
    return Clock(method, [(e, t) for e, t, _ in pairs], error, pages[0] if pages else None, latency)


# ============================================================================================ timelines
def grid_of(beat: float, meter: int) -> Tuple[str, float]:
    """(grid class, metric weight w_m) of a beat position inside a bar (11.3 step 3)."""
    p = beat - math.floor(beat)
    if p <= GRID_TOL or p >= 1 - GRID_TOL:
        whole = int(round(beat)) % meter
        if whole == 0:
            return "beat", METRIC_WEIGHTS["downbeat"]
        return "beat", METRIC_WEIGHTS["beat3"] if meter == 4 and whole == 2 else METRIC_WEIGHTS["beat"]
    if abs(p - 0.5) <= GRID_TOL:
        return "offbeat", METRIC_WEIGHTS["offbeat"]
    if min(abs(p - 1 / 3), abs(p - 2 / 3)) <= GRID_TOL:
        return "triplet", METRIC_WEIGHTS["other"]
    if min(abs(p - 0.25), abs(p - 0.75)) <= GRID_TOL:
        return "sixteenth", METRIC_WEIGHTS["other"]
    return "free", METRIC_WEIGHTS["other"]


class RunTimeline:
    """A run's slot instances in session t_ms (11.3 step 1), and the bar position of any session time."""

    grid = True

    def __init__(self, loaded: dict, clock: Clock, end_epoch: Optional[float] = None):
        run = loaded["run"]
        self.loaded, self.clock = loaded, clock
        self.m = run["beats_per_bar"]
        self.segs = sorted(run["segments"], key=lambda s: s["from_bar"])
        self.defs = loaded["defs"]
        self.settings = sorted(run.get("settings") or [{"from_bar": 0}], key=lambda s: s.get("from_bar", 0))
        self.mode = run.get("mode")
        self.end_epoch = run_end_epoch(loaded) if end_epoch is None else end_epoch
        self._facts: Dict[tuple, dict] = {}
        spans: List[dict] = []
        for s in self.segs:
            ident = (s["def_version"], s["def_from_bar"])
            if not spans or ident != (spans[-1]["version"], spans[-1]["from_bar"]):
                d = self.defs[s["def_version"]]
                spans.append({"version": s["def_version"], "from_bar": s["def_from_bar"], "cycle": d["cycle_beats"],
                              "offset": 0})
        for k in range(1, len(spans)):
            prev = spans[k - 1]
            used = max(0, spans[k]["from_bar"] - prev["from_bar"])
            prev_passes = math.ceil(used * self.m / prev["cycle"] - 1e-9)
            spans[k]["offset"] = prev["offset"] + prev_passes
        self.spans = spans
        self._span_from = [sp["from_bar"] for sp in spans]
        self.bar0_t = clock.t_of(tm.t_epoch(self.segs, self.m, 0))
        self.instances = self._build()
        self.starts = [inst["start_t"] for inst in self.instances]
        self.start_t = self.bar0_t
        self.end_t = clock.t_of(self.end_epoch)
        end_pos = tm.bar_at(self.segs, self.m, self.end_epoch)
        self.bars = end_pos["bar"] + (1 if end_pos["beat"] > 1e-3 else 0)

    def span_at(self, bar: int) -> dict:
        return self.spans[max(0, bisect_right(self._span_from, bar) - 1)]

    def facts(self, version, i) -> dict:
        key = (version, i)
        if key not in self._facts:
            self._facts[key] = slot_facts(self.defs[version]["slots"][i])
        return self._facts[key]

    def settings_at(self, bar: int) -> dict:
        chosen = self.settings[0]
        for s in self.settings:
            if s.get("from_bar", 0) <= bar:
                chosen = s
        return chosen

    def _build(self) -> List[dict]:
        m, segs, out = self.m, self.segs, []
        bar = 0
        while bar < 1_000_000:
            b0 = tm.t_epoch(segs, m, bar)
            if b0 >= self.end_epoch - tm.EPS_MS:
                break
            sp = self.span_at(bar)
            if bar < sp["from_bar"]:
                bar += 1
                continue
            d = self.defs[sp["version"]]
            cycle = d["cycle_beats"]
            cb = ((bar - sp["from_bar"]) * m) % cycle
            k = self.spans.index(sp)
            cut = tm.t_epoch(segs, m, self.spans[k + 1]["from_bar"]) if k + 1 < len(self.spans) else math.inf
            for i, sl in enumerate(d["slots"]):
                if not (cb - tm.EPS_BEATS <= sl["at_beat"] < cb + m - tm.EPS_BEATS):
                    continue
                x = max(0.0, sl["at_beat"] - cb)
                start = tm.t_epoch(segs, m, bar, x)
                endpos = x + sl["beats"]
                whole = math.floor(endpos / m + tm.EPS_BEATS)
                end = min(tm.t_epoch(segs, m, bar + whole, max(0.0, endpos - whole * m)), cut, self.end_epoch)
                if end <= start + tm.EPS_MS:
                    continue
                f = self.facts(sp["version"], i)
                out.append({"key": (sp["version"], i), "slot": i, "def_version": sp["version"], "facts": f,
                            "start_e": start, "end_e": end, "start_t": self.clock.t_of(start),
                            "end_t": self.clock.t_of(end),
                            "pass": sp["offset"] + math.floor((bar - sp["from_bar"]) * m / cycle) + 1,
                            "run_bar": bar + 1, "bar": math.floor(cb / m) + 1,
                            "beat_ms": tm.beat_ms(tm.segment_at(segs, bar)["bpm"]), "bar_ix": bar})
            bar += 1
        for n, inst in enumerate(out):
            inst["i"] = n
        return out

    def position(self, t_ms: float) -> dict:
        """{pass, run_bar, bar, beat, beat_ms, grid, w_m, bar_ix} of a session time."""
        epoch = self.clock.epoch_of(t_ms) + ONSET_EPS_MS
        pos = tm.bar_at(self.segs, self.m, epoch)
        bar = pos["bar"]
        s = tm.segment_at(self.segs, bar)
        beat = max(0.0, pos["beat"] - ONSET_EPS_MS / tm.beat_ms(s["bpm"]))
        grid, w_m = grid_of(beat, self.m)
        sp = self.span_at(bar)
        if bar < 0:
            p, cbar = 0, None
        else:
            rel = max(0, bar - sp["from_bar"]) * self.m
            p = sp["offset"] + math.floor(rel / sp["cycle"]) + 1
            cbar = math.floor((rel % sp["cycle"]) / self.m) + 1
        return {"pass": p, "run_bar": bar + 1, "bar": cbar, "beat": beat, "beat_ms": tm.beat_ms(s["bpm"]), "grid": grid,
                "w_m": w_m, "bar_ix": bar}

    def beats_between(self, t1: float, t2: float) -> float:
        a = tm.bar_at(self.segs, self.m, self.clock.epoch_of(t1))
        b = tm.bar_at(self.segs, self.m, self.clock.epoch_of(t2))
        return (b["bar"] - a["bar"]) * self.m + b["beat"] - a["beat"]

    def bar_line_after(self, t_ms: float) -> float:
        pos = tm.bar_at(self.segs, self.m, self.clock.epoch_of(t_ms))
        return self.clock.t_of(tm.t_epoch(self.segs, self.m, pos["bar"] + 1))

    def bar_t(self, bar_ix: int) -> float:
        return self.clock.t_of(tm.t_epoch(self.segs, self.m, bar_ix))

    def threshold(self, inst: Optional[dict]) -> int:
        """The top line's lowest note at an instance: C4, or above backing full's top voice (at most A4 + 1)."""
        if inst is None:
            return LINE_MIN_NOTE
        st = self.settings_at(inst["bar_ix"])
        backing = st.get("backing")
        if self.mode == "try" and st.get("try_backing") in ("ghosts", "bass"):
            backing = st.get("try_backing")
        top = inst["facts"]["full_top"]
        if backing == "full" and top:
            return min(LINE_FULL_MAX, max(LINE_MIN_NOTE, top + 1))
        return LINE_MIN_NOTE


def _tones_from_pcs(pcs: Sequence[int], root: int) -> Dict[str, int]:
    """Roles for a chord read from his playing (free play): the tones_pc a def would carry."""
    rel = {(p - root) % 12: p for p in pcs}
    tones = {"root": root}
    third = 4 if 4 in rel else 3 if 3 in rel else None
    if third is not None:
        tones["third"] = rel[third]
    elif 5 in rel:
        tones["sus"] = rel[5]
    elif 2 in rel:
        tones["sus"] = rel[2]
    if 7 in rel:
        tones["fifth"] = rel[7]
    elif 6 in rel and third == 3:
        tones["fifth"] = rel[6]
    elif 8 in rel and third == 4:
        tones["fifth"] = rel[8]
    if 10 in rel:
        tones["seventh"] = rel[10]
    elif 11 in rel:
        tones["seventh"] = rel[11]
    for i, role in ((1, "ninth"), (2, "ninth"), (3, "ninth"), (5, "eleventh"), (6, "eleventh"), (8, "thirteenth"),
                    (9, "thirteenth")):
        p = (root + i) % 12
        if p in pcs and p not in tones.values() and role not in tones:
            tones["sixth" if i == 9 and "seventh" not in tones else role] = p
    return tones


class FreeTimeline:
    """Free play (11.7): the chords practice.analyze read from his own playing stand in for the loop's slots."""

    grid = False
    m = 4
    mode = None

    def __init__(self, doc: dict, duration_ms: float):
        home = doc.get("home_key")
        self.instances: List[dict] = []
        self._facts: Dict[tuple, dict] = {}
        self.slot_keys: List[tuple] = []
        for row in doc.get("windows") or []:
            if not pr.is_chord(row):
                continue
            key = row.get("key") or home
            pcs = [p for p in (_pc_of_name(n) for n in row.get("pcs") or []) if p is not None]
            root = _pc_of_name(row.get("root") or "")
            if not key or not nashville.parse_key(key) or root is None or len(pcs) < 2:
                continue
            bass_name = (row.get("bass") or {}).get("note")
            bass_pc = pr._note_midi(bass_name) % 12 if bass_name else root
            name = row.get("analysed_as") or row.get("name")
            skey = (key, name)
            if skey not in self._facts:
                chord = sorted(set(pcs) | {bass_pc})
                slot = {"name": name, "n": row.get("number"), "key": key, "tones_pc": _tones_from_pcs(pcs, root),
                        "bass_pc": bass_pc, "chord_pcs": chord, "class": row.get("class"),
                        "scale": scale_for_class(chord, root, key, row.get("class"), row.get("suffix") or "",
                                                 row.get("fits") or (), row.get("class_detail") or "",
                                                 row.get("target"))}
                self._facts[skey] = slot_facts(slot)
                self.slot_keys.append(skey)
            self.instances.append({"key": skey, "slot": self.slot_keys.index(skey), "def_version": None,
                                   "facts": self._facts[skey], "start_t": float(row["start_ms"]),
                                   "end_t": float(row["end_ms"]), "pass": None, "run_bar": None, "bar": None,
                                   "beat_ms": FREE_BEAT_MS, "bar_ix": None})
        self.instances.sort(key=lambda x: x["start_t"])
        for n, inst in enumerate(self.instances):
            inst["i"] = n
        self.starts = [x["start_t"] for x in self.instances]
        self.start_t, self.end_t = 0.0, float(duration_ms) + 1
        self.bars = 0

    def facts(self, version, i) -> dict:
        return self._facts[self.slot_keys[i]]

    def position(self, t_ms: float) -> dict:
        return {"pass": None, "run_bar": None, "bar": None, "beat": None, "beat_ms": FREE_BEAT_MS, "grid": None,
                "w_m": FREE_W_M, "bar_ix": None}

    def beats_between(self, t1: float, t2: float) -> float:
        return (t2 - t1) / FREE_BEAT_MS

    def threshold(self, inst) -> int:
        return LINE_MIN_NOTE


# ============================================================================================ his notes
def _window_ms(beat_ms: float, rule: Tuple[float, float]) -> float:
    return min(rule[0] * beat_ms, rule[1])


def read_notes(tl, snd: dict, lo_t: float, hi_t: float) -> Tuple[List[dict], List[dict], List[List[dict]]]:
    """(notes, top line, attacks) of his inside [lo_t, hi_t): positions, top line, lengths, weights, the chord each
    note is heard against (with anticipations) and its class and label (11.3 steps 2-5)."""
    recs = []
    for n in snd["notes"]:
        if lo_t <= n["on_ms"] < hi_t:
            end = n["end_ms"] if n["off_ms"] is None else min(n["off_ms"], n["end_ms"])
            recs.append({"note": n["note"], "on": float(n["on_ms"]), "key_end": float(end), "vel": n["vel"],
                         "top": False, "flags": []})
    recs.sort(key=lambda r: (r["on"], r["note"]))
    insts, starts = tl.instances, tl.starts
    attacks: List[List[dict]] = []
    for r in recs:
        r["pos"] = tl.position(r["on"])
        if attacks and r["on"] - attacks[-1][0]["on"] <= ONSET_GROUP_MS:
            attacks[-1].append(r)
        else:
            attacks.append([r])
    for group in attacks:
        hi = max(group, key=lambda r: r["note"])
        i = bisect_right(starts, group[0]["on"] + ONSET_EPS_MS) - 1
        inst = insts[i] if i >= 0 else (insts[0] if insts else None)
        if hi["note"] >= tl.threshold(inst):
            hi["top"] = True
    tops = [r for r in recs if r["top"]]
    top_on = [r["on"] for r in tops]
    for k, r in enumerate(tops):
        r["next_top"] = tops[k + 1] if k + 1 < len(tops) else None
    for r in recs:
        beat_ms = r["pos"]["beat_ms"]
        if not r["top"]:
            j = bisect_right(top_on, r["on"])
            r["next_top"] = tops[j] if j < len(tops) else None
            end = r["key_end"]
        else:
            end = min(r["key_end"], r["next_top"]["on"] if r["next_top"] else math.inf)
        r["len_ms"] = max(0.0, min(end - r["on"], LINE_LEN_CAP_BEATS * beat_ms))
        r["len_beats"] = r["len_ms"] / beat_ms
        r["w"] = r["pos"]["w_m"] * min(WEIGHT_LEN[1], max(WEIGHT_LEN[0], r["len_beats"]))
        r["inst"], r["flags"] = _judge(tl, r)
    for r in recs:
        if r["inst"] is not None:
            _classify_into(r, r["inst"]["facts"])
    return recs, tops, attacks


def _judge(tl, r: dict) -> Tuple[Optional[dict], List[str]]:
    """The slot instance a note is heard against (MUSIC 9.4): the one sounding, or the next when the note anticipates
    it (the change at most min(0.5 beat, 300 ms) away, the note in the next chord and not in the current one)."""
    insts, t, pc = tl.instances, r["on"], r["note"] % 12
    if not insts:
        return None, []
    i = bisect_right(tl.starts, t + ONSET_EPS_MS) - 1
    if i < 0:
        nxt = insts[0]
        if tl.grid and nxt["start_t"] - t <= _window_ms(nxt["beat_ms"], ANTICIPATE_MAX) + ONSET_EPS_MS:
            return nxt, (["anticipates"] if pc in nxt["facts"]["chord"] else [])
        return None, []
    cur = insts[i]
    nxt = insts[i + 1] if i + 1 < len(insts) else None
    sounding = t + ONSET_EPS_MS < cur["end_t"]
    if tl.grid and nxt is not None \
            and ONSET_EPS_MS < nxt["start_t"] - t <= _window_ms(cur["beat_ms"], ANTICIPATE_MAX) + ONSET_EPS_MS \
            and pc in nxt["facts"]["chord"] and not (sounding and pc in cur["facts"]["chord"]):
        return nxt, ["anticipates"]
    return cur, ([] if sounding else ["in a rest"])


def _sits(r: dict) -> bool:
    """A note that is a chord tone or a colour against the chord it is heard against."""
    if r is None or r.get("inst") is None:
        return False
    f, pc = r["inst"]["facts"], r["note"] % 12
    return pc in f["chord"] or (pc in f["scale"] and pc not in f["rubs"])


def classify_note(r: dict, f: dict) -> Tuple[str, Optional[str]]:
    """(class, slide direction) of a note against chord facts f (11.3 step 5, first match wins)."""
    pc, nxt, beat_ms = r["note"] % 12, r.get("next_top"), r["pos"]["beat_ms"]
    if pc in f["chord"]:
        return "in_chord", None
    if pc in f["rubs"]:
        if r["len_beats"] < PASSING_MAX_BEATS and r["pos"]["w_m"] < PASSING_W_MAX and nxt is not None \
                and 1 <= abs(nxt["note"] - r["note"]) <= PASSING_STEP \
                and nxt["on"] - (r["on"] + r["len_ms"]) <= PASSING_WITHIN_BEATS * beat_ms + 1 and _sits(nxt):
            return "passing", None
        return "rub", None
    if pc in f["scale"]:
        return "colour", None
    if r["len_ms"] <= _window_ms(beat_ms, SLIDE_IN_MAX) + 1 and nxt is not None \
            and nxt["on"] - r["on"] <= SLIDE_IN_RESOLVE_BEATS * beat_ms + 1 and abs(nxt["note"] - r["note"]) == 1 \
            and _sits(nxt):
        return "slide_in", "below" if nxt["note"] > r["note"] else "above"
    return "outside", None


def _classify_into(r: dict, f: dict) -> None:
    cls, direction = classify_note(r, f)
    pc = r["note"] % 12
    r["class"], r["direction"] = cls, direction
    r["label"], r["bass_label"] = tone_label(f, pc), bass_label(f, pc)
    r["name"] = pr.midi_name(r["note"], f["key"])
    if cls == "slide_in":
        r["flags"] = r["flags"] + [f"from {direction}"]
    if cls == "outside" and pc in f["key_scale"]:
        r["flags"] = r["flags"] + ["in the key, not this chord"]


# ============================================================================================ one block
def _in_filter(pos: dict, opts: dict) -> bool:
    if opts.get("pass") is not None and pos.get("pass") != opts["pass"]:
        return False
    bars = opts.get("bars")
    return not bars or (pos.get("run_bar") is not None and bars[0] <= pos["run_bar"] <= bars[1])


def _count(items, key) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for x in items:
        k = key(x)
        if k is not None:
            out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def _landing(tl, tops: List[dict], top_on: List[float], inst: dict):
    """(note, class, label) of his first top-line onset from just before an instance's start to 250 ms after it."""
    lo = inst["start_t"] - _window_ms(inst["beat_ms"], LANDING_BEFORE)
    j = bisect_left(top_on, lo - 1e-6)
    if j >= len(tops) or tops[j]["on"] > inst["start_t"] + LANDING_AFTER_MS + 1e-6:
        return None
    r = tops[j]
    if r["inst"] is inst:
        return r, r["class"], r["label"]
    cls, _ = classify_note(r, inst["facts"])
    return r, cls, tone_label(inst["facts"], r["note"] % 12)


def _slot_scale(f: dict, tops: List[dict]) -> Optional[dict]:
    """The scale his top line made over a slot (11.3 step 6), with the naming gate."""
    total = sum(r["w"] for r in tops)
    if len(tops) < SCALE_MIN_NOTES or total <= 0:
        return None
    hist: Dict[int, float] = {}
    for r in tops:
        i = (r["note"] - f["root"]) % 12
        hist[i] = hist.get(i, 0.0) + r["w"] / total
    cands = score_scales(hist)
    best, runner = cands[0], cands[1]
    named, own_i, own_share = scale_gate(best, hist)
    root = pr.pc_name(f["root"], f["key"])
    own_pc = (f["root"] + own_i) % 12 if own_i is not None else None
    return {"best": f"{root} {best['name']}", "score": _r(best["score"]), "runner_up": f"{root} {runner['name']}",
            "margin": _r(best["score"] - runner["score"]), "named": bool(named),
            "own_note": pr.pc_name(own_pc, f["key"]) if own_pc is not None else None,
            "own_label": tone_label(f, own_pc) if own_pc is not None else None,
            "own_count": sum(1 for r in tops if r["note"] % 12 == own_pc) if own_pc is not None else None,
            "own_share": _r(own_share), "notes": len(tops),
            "say": f"{root} {best['name']}" if named else f"the notes of {f['key']}"}


def _contour(notes: List[int]) -> str:
    if len(notes) < 2 or max(notes) - min(notes) <= CONTOUR_FLAT_RANGE:
        return "flat"
    k, start, end, hi, lo = len(notes), notes[0], notes[-1], max(notes), min(notes)
    peak, trough = notes.index(hi) / (k - 1), notes.index(lo) / (k - 1)
    if end >= start + CONTOUR_STEP and peak >= 2 / 3:
        return "rising"
    if end <= start - CONTOUR_STEP and trough >= 2 / 3:
        return "falling"
    if 1 / 3 <= peak < 2 / 3 and start <= hi - CONTOUR_STEP and end <= hi - CONTOUR_STEP:
        return "arch"
    if 1 / 3 <= trough < 2 / 3 and start >= lo + CONTOUR_STEP and end >= lo + CONTOUR_STEP:
        return "valley"
    return "wave"


def _split_phrases(tl, tops: List[dict]) -> List[List[dict]]:
    """Top-line gaps of max(1 beat, 600 ms) end a phrase; a phrase over 4 bars splits at its longest inner gap."""
    groups: List[List[dict]] = []
    for r in tops:
        if groups:
            prev = groups[-1][-1]
            gap = r["on"] - (prev["on"] + prev["len_ms"])
            if gap >= max(PHRASE_GAP[0] * prev["pos"]["beat_ms"], PHRASE_GAP[1]) - 0.5:
                groups.append([r])
                continue
            groups[-1].append(r)
        else:
            groups.append([r])
    out: List[List[dict]] = []
    stack = list(reversed(groups))
    while stack:
        g = stack.pop()
        span = tl.beats_between(g[0]["on"], g[-1]["on"] + g[-1]["len_ms"]) / tl.m if tl.grid else 0
        gaps = [((g[k + 1]["on"] - (g[k]["on"] + g[k]["len_ms"])) / g[k]["pos"]["beat_ms"], k) for k in range(len(g) - 1)]
        gaps = [x for x in gaps if x[0] >= PHRASE_SPLIT_MIN_BEATS]
        if span > PHRASE_MAX_BARS and gaps:
            _, k = max(gaps, key=lambda x: (x[0], -x[1]))
            stack.append(g[k + 1:])
            stack.append(g[:k + 1])
        else:
            out.append(g)
    return out


def _phrases(tl, tops: List[dict]) -> List[dict]:
    groups = _split_phrases(tl, tops)
    out = []
    for n, g in enumerate(groups):
        s, e = g[0], g[-1]
        gap = max(PHRASE_GAP[0] * e["pos"]["beat_ms"], PHRASE_GAP[1])
        breath_end = min(groups[n + 1][0]["on"] if n + 1 < len(groups) else math.inf, e["on"] + e["len_ms"] + gap)
        notes = [r["note"] for r in g]
        key = s["inst"]["facts"]["key"] if s.get("inst") else None
        ph = {"at": pr.clock(s["on"]), "t_ms": s["on"], "notes": len(g),
              "range": [pr.midi_name(min(notes), key), pr.midi_name(max(notes), key)], "contour": _contour(notes),
              "landing": {"class": e.get("class"), "label": e.get("label"), "name": e.get("name")},
              "_last": e, "_first": s}
        if tl.grid:
            pos, m = s["pos"], tl.m
            line = tl.bar_line_after(s["on"])
            pickup = pos["beat"] >= m - 1 - 1e-6 and e["on"] + e["len_ms"] > line + 1
            if pickup:
                at_line = tl.position(line + 0.01)
                ph.update(pas=at_line["pass"], bar=at_line["bar"], beat=_r(-(m - pos["beat"]), 3))
            else:
                ph.update(pas=pos["pass"], bar=pos["bar"], beat=_r(pos["beat"], 3))
            ph["pass"] = ph.pop("pas")
            ph["bars"] = _half(tl.beats_between(s["on"], breath_end) / m)
            ph["pickup"] = bool(pickup)
        else:
            ph["seconds"] = _r((min(breath_end, e["on"] + e["len_ms"] + gap) - s["on"]) / 1000, 1)
            ph["pickup"] = False
        out.append(ph)
    return out


def _concepts(tl, card: Optional[dict], variant, version) -> List[dict]:
    """The card's concept notes (11.4): its checks' roles, its landing, and the #11 on a lydian card."""
    if version is None or not card:
        return []
    d = tl.defs[version]
    items = []
    for c in card.get("checks") or []:
        if c.get("variant") != variant or not isinstance(c.get("slot"), int) or c["slot"] >= len(d["slots"]):
            continue
        f = tl.facts(version, c["slot"])
        base = f["bass"] if c.get("relative_to") == "bass" else f["root"]
        items.append((c["slot"], (base + ROLE_INTERVALS.get(c.get("role"), 0)) % 12, f"check {c.get('id')}"))
    landing = d.get("landing")
    if isinstance(landing, dict) and isinstance(landing.get("slot"), int) and isinstance(landing.get("pc"), int):
        items.append((landing["slot"], landing["pc"] % 12, "landing"))
    if "lydian" in (card.get("tags") or []):
        for i in range(len(d["slots"])):
            f = tl.facts(version, i)
            pc = (f["root"] + 6) % 12
            if pc in f["chord"] or pc in f["scale"]:
                items.append((i, pc, "lydian"))
    seen, out = set(), []
    for slot, pc, source in items:
        if (slot, pc) in seen:
            continue
        seen.add((slot, pc))
        f = tl.facts(version, slot)
        out.append({"slot": slot, "pc": pc, "note": pr.pc_name(pc, f["key"]), "label": tone_label(f, pc),
                    "source": source})
    return out


def analyse_block(tl, snd: dict, opts: Optional[dict] = None, card: Optional[dict] = None, variant=None) -> dict:
    """Everything 11.3 reports for one run (or free play), before readings, highlights and talking points."""
    opts = opts or {}
    insts_all = tl.instances
    lead = _window_ms(insts_all[0]["beat_ms"], ANTICIPATE_MAX) if tl.grid and insts_all else 0
    recs, tops, attacks = read_notes(tl, snd, tl.start_t - lead, tl.end_t)
    insts = [x for x in insts_all if _in_filter(x, opts)]
    counted = [r for r in recs if r["inst"] is not None and _in_filter(r["pos"], opts)]
    tops_c = [r for r in counted if r["top"]]
    top_on = [r["on"] for r in tops]
    landings = {x["i"]: _landing(tl, tops, top_on, x) for x in insts}

    slot_meta: Dict[tuple, dict] = {}
    for x in insts_all:
        slot_meta.setdefault(x["key"], {"facts": x["facts"], "slot": x["slot"], "def_version": x["def_version"],
                                        "insts": []})
    for x in insts:
        slot_meta[x["key"]]["insts"].append(x)
    versions = sorted({x["def_version"] for x in insts_all if x["def_version"] is not None})
    slots = []
    for sk, s in slot_meta.items():
        f = s["facts"]
        st = [r for r in tops_c if r["inst"]["key"] == sk]
        sa = [r for r in counted if r["inst"]["key"] == sk]
        land = [landings[x["i"]] for x in s["insts"] if landings.get(x["i"])]
        block = {"slot": s["slot"], "name": f["name"], "number": f["number"], "class": f["class"],
                 "instances": len(s["insts"]),
                 "classes": {c: sum(1 for r in st if r["class"] == c) for c in CLASSES},
                 "all_notes": {c: sum(1 for r in sa if r["class"] == c) for c in CLASSES},
                 "labels": _count(st, lambda r: r["label"]), "bass_labels": _count(st, lambda r: r["bass_label"]),
                 "landings": _count(land, lambda x: x[2]), "reharmonized": [],
                 "outside": [{"at": pr.clock(r["on"]), "t_ms": r["on"], "name": r["name"], "beats": _r(r["len_beats"], 2),
                              "in_key": "in the key, not this chord" in r["flags"]}
                             for r in st if r["class"] == "outside"],
                 "rubs": [{"at": pr.clock(r["on"]), "t_ms": r["on"], "name": r["name"], "beats": _r(r["len_beats"], 2),
                           "against": pr.pc_name((r["note"] - 1) % 12 if (r["note"] - 1) % 12 in f["chord"]
                                                 else (r["note"] + 1) % 12, f["key"])}
                          for r in st if r["class"] == "rub"],
                 "passing": [{"at": pr.clock(r["on"]), "t_ms": r["on"], "name": r["name"],
                              "beats": _r(r["len_beats"], 2)} for r in st if r["class"] == "passing"],
                 "scale": _slot_scale(f, st)}
        if len(versions) > 1:
            block["def_version"] = s["def_version"]
        block["_key"], block["_facts"], block["_tops"] = sk, f, st
        slots.append(block)

    out = {"coverage": {}, "slots": slots, "passes": [], "phrases": _phrases(tl, tops_c),
           "anticipations": [{"at": pr.clock(r["on"]), "t_ms": r["on"], "to_slot": r["inst"]["slot"],
                              "early_ms": _r(r["inst"]["start_t"] - r["on"], 1), "name": r["name"]}
                             for r in counted if "anticipates" in r["flags"]] if tl.grid else [],
           "slide_ins": [{"at": pr.clock(r["on"]), "t_ms": r["on"], "name": r["name"],
                          "to": r["next_top"]["name"] if r["next_top"] else None, "direction": r["direction"]}
                         for r in counted if r["class"] == "slide_in"],
           "_recs": counted, "_tops": tops_c, "_attacks": attacks, "_insts": insts, "_landings": landings, "_tl": tl}

    if tl.grid:
        bars_set = set()
        for x in insts:
            last = tl.position(max(x["start_t"], x["end_t"] - ONSET_EPS_MS - 1))["bar_ix"]  # the bar it ends in
            bars_set.update(b for b in range(x["bar_ix"], last + 1) if _in_filter({"pass": x["pass"], "run_bar": b + 1}, opts))
        out["coverage"] = {"passes": len({x["pass"] for x in insts}), "bars": len(bars_set),
                           "bars_with_his_notes": len({r["pos"]["bar_ix"] for r in counted} & bars_set),
                           "notes": len(counted), "top_line_notes": len(tops_c)}
        out["degrees_by_bar"] = _degrees(tl, insts, tops_c)
        out["passes"] = _passes(tl, insts, counted, attacks, snd, bars_set)
    else:
        out["coverage"] = {"chords_read": len(insts), "notes": len(counted), "top_line_notes": len(tops_c)}
    return out


def _degrees(tl, insts: List[dict], tops: List[dict]) -> dict:
    """The top line's degree per bar (11.3 step 8): per pass, and the label that wins each bar in the most passes."""
    cells: Dict[tuple, Dict[str, float]] = {}
    for r in tops:
        if r["pos"]["bar"] is None:
            continue
        c = cells.setdefault((r["pos"]["pass"], r["pos"]["bar"]), {})
        c[r["label"]] = c.get(r["label"], 0.0) + r["w"]
    version_of = {}
    for x in insts:
        version_of.setdefault(x["pass"], x["def_version"])
    passes, by_version = [], {}
    for p in sorted(version_of):
        v = version_of[p]
        nbars = int(tl.defs[v]["cycle_beats"] // tl.m)
        row = []
        for b in range(1, nbars + 1):
            c = cells.get((p, b))
            row.append(max(c.items(), key=lambda kv: (kv[1], kv[0]))[0] if c else None)
        passes.append(row)
        by_version.setdefault(v, []).append((p, row))
    most = []
    for v, rows in by_version.items():
        nbars = len(rows[0][1])
        mp = []
        for b in range(nbars):
            wins, weight = {}, {}
            for p, row in rows:
                if row[b] is not None:
                    wins[row[b]] = wins.get(row[b], 0) + 1
                    weight[row[b]] = weight.get(row[b], 0.0) + cells[(p, b + 1)][row[b]]
            mp.append(max(wins, key=lambda k: (wins[k], weight[k], k)) if wins else None)
        most.append({"def_version": v, "most_played": mp})
    out = {"most_played": most[0]["most_played"] if most else [], "passes": passes}
    if len(most) > 1:
        out["by_def"] = most
    return out


def _passes(tl, insts: List[dict], recs: List[dict], attacks: List[List[dict]], snd: dict, bars_set: set) -> List[dict]:
    """Per pass (11.3 step 10): range, velocity, shares, rests, pedal, onsets per bar, and at most one picking fact."""
    rows = []
    seen_colours: set = set()
    for p in sorted({x["pass"] for x in insts}):
        px = [x for x in insts if x["pass"] == p]
        t0, t1 = min(x["start_t"] for x in px), max(x["end_t"] for x in px)
        bars = sorted(b for b in bars_set if tl.position(tl.bar_t(b) + 1)["pass"] == p)
        pr_all = [r for r in recs if r["pos"]["pass"] == p]
        pr_top = [r for r in pr_all if r["top"]]
        key = px[0]["facts"]["key"]
        vels = [r["vel"] for r in pr_all if r["vel"] is not None]
        weight = {"in_chord": 0.0, "colour": 0.0, "outside": 0.0}
        counts = {"in_chord": 0, "colour": 0, "outside": 0}
        for r in pr_top:
            weight[WORD_OF[r["class"]]] += r["w"]
            counts[WORD_OF[r["class"]]] += 1
        total = sum(weight.values())
        notes = [r["note"] for r in pr_top]
        pedal = sum(pr._overlap([[s["down_ms"], s["up_ms"]]], t0, t1) for s in snd["pedal"])
        with_notes = {r["pos"]["bar_ix"] for r in pr_all}
        colours = {r["label"] for r in pr_top if WORD_OF[r["class"]] == "colour"}
        new_colours = sorted(colours - seen_colours) if seen_colours or p != min(x["pass"] for x in insts) else []
        seen_colours |= colours
        pass_attacks = sum(1 for a in attacks if a[0] in pr_all)
        rows.append({"pass": p, "range": [pr.midi_name(min(notes), key), pr.midi_name(max(notes), key)] if notes else None,
                     "vel_median": _median(vels), "vel_p90": _p90(vels),
                     "shares": {k: _r(v / total, 3) if total else 0.0 for k, v in weight.items()}, "counts": counts,
                     "rests": sum(1 for b in bars if b not in with_notes), "pedal": _r(pedal / (t1 - t0), 2) if t1 > t0 else 0.0,
                     "onsets_per_bar": _r(pass_attacks / len(bars), 1) if bars else None, "notes": len(pr_all),
                     "top_line_notes": len(pr_top), "fact": None,
                     "_span": (max(notes) - min(notes)) if notes else -1, "_colour_w": weight["colour"],
                     "_new": new_colours})
    if len(rows) >= 2:
        picks = (("_span", "your widest top line"), ("vel_p90", "your strongest touch"),
                 ("_colour_w", "your most colour"))
        for field, words in picks:
            vals = [r[field] for r in rows if r[field] is not None]
            if not vals or max(vals) <= 0:
                continue
            top = next(r for r in rows if r[field] == max(vals))
            if top["fact"] is None:
                top["fact"] = words
        first_new = next((r for r in rows[1:] if r["_new"]), None)
        if first_new is not None and first_new["fact"] is None:
            first_new["fact"] = f"a new colour: {first_new['_new'][0]}"
            first_new["fact_label"] = first_new["_new"][0]
    for r in rows:
        for k in ("_span", "_colour_w", "_new"):
            r.pop(k)
    return rows


# ================================================================================= readings and loopback
def apply_readings(blocks: List[dict], theory_source=None, node: Optional[str] = None) -> None:
    """His own reading (11.3 step 9): Theory.detect over the notes of his struck chords (attacks of 3 or more notes)
    in each slot instance, one node call for every block. A root or bass that differs from the loop's is reharmonized."""
    items, where = [], []
    for b in blocks:
        b["readings"] = "no struck chords of 3 or more notes"
        counted = {id(r) for r in b["_recs"]}
        per_inst: Dict[int, Tuple[dict, set, float]] = {}
        for a in b["_attacks"]:
            if len(a) < READING_MIN_NOTES or id(a[0]) not in counted or a[0]["inst"] is None:
                continue
            inst = a[0]["inst"]
            got = per_inst.setdefault(inst["i"], (inst, set(), a[0]["on"]))
            got[1].update(r["note"] for r in a)
        for inst, notes, first in per_inst.values():
            k = nashville.parse_key(inst["facts"]["key"])
            items.append({"notes": sorted(notes), "bias": nashville.bias_of(k["tonic"], k["mode"]) if k else 0})
            where.append((b, inst, sorted(notes), first))
    if not items:
        return
    answer, why = pr.run_theory(items, theory_source, node)
    for b in {id(w[0]): w[0] for w in where}.values():
        b["readings"] = "piano.js Theory.detect via node" if answer else f"unavailable ({why})"
    if not answer:
        return
    for (b, inst, notes, first), info in zip(where, answer["results"]):
        f = inst["facts"]
        spelled = pr.spell_detect(info, f["key"])
        if not spelled or spelled["kind"] != "chord" or not spelled.get("root"):
            continue
        root_pc = pr._sp_pc(spelled["root"])
        bass_pc = pr._sp_pc(spelled["bass"]) if spelled.get("bass") else root_pc
        if root_pc == f["root"] and not (bass_pc != f["bass"] and min(notes) < pr.BASS_MAX_MIDI):
            continue
        number = pr._number(spelled["name"], f["key"])
        entry = {"at": pr.clock(first), "t_ms": first, "pass": inst["pass"], "played": spelled["name"],
                 "played_number": number, "over": f["name"], "over_number": f["number"],
                 "text": f"over {f['number'] or f['name']} you played {number or spelled['name']}"}
        inst["_reharm"] = entry
        for s in b["slots"]:
            if s["_key"] == inst["key"]:
                s["reharmonized"].append(entry)


def _def_onsets(tl) -> List[Tuple[float, int]]:
    """Claude's notes rebuilt from the def when groove_bridge.mjs cannot answer: every chord's downbeat strikes. The bass
    always; the upper voices when humanize is 0 (a rolled or humanized upper voice can sit past LOOPBACK_MS) and the
    groove strikes them together (hold, ballad); a note held over from the chord before (hold, or upper: same) is not
    struck again."""
    out, prev = [], None
    for x in tl.instances:
        st = tl.settings_at(x["bar_ix"])
        backing, groove = st.get("backing") or "comp", st.get("groove") or "hold"
        if tl.mode == "try":
            if st.get("try_backing") == "ghosts":
                prev = None
                continue
            if st.get("try_backing") == "bass":
                backing = "bass"
        if st.get("muted"):
            prev = None
            continue
        voicings = x["facts"]["slot"].get("voicings") or {}
        notes = list(voicings.get(backing) or voicings.get("comp") or voicings.get("bass") or [])
        if not notes:
            prev = None
            continue
        bass, upper = notes[0], notes[1:] if backing != "bass" else []
        joined = prev is not None and abs(prev[0]["end_e"] - x["start_e"]) < 1 and prev[0]["def_version"] == x["def_version"]
        if not (joined and groove == "hold" and prev[1] == bass):
            out.append((x["start_t"], bass))
        tie_upper = joined and (groove == "hold" or x["facts"]["slot"].get("upper_same"))
        if (st.get("humanize") if _num(st.get("humanize")) else 0.6) == 0 and groove in ("hold", "ballad"):
            out.extend((x["start_t"], u) for u in upper if not (tie_upper and u in prev[2]))
        prev = (x, bass, upper)
    return out


def _bridge_onsets(tl, node: Optional[str] = None) -> Tuple[Optional[List[Tuple[float, int]]], Optional[str]]:
    """Claude's notes from arsenal/groove_bridge.mjs (J2), its run form: one node call for bars 0..the stop, `flat`
    for every struck note (no carries, no ticks) with its epoch_ms through the tempo map. (onsets, None) or
    (None, why)."""
    node = node or shutil.which("node")
    if not node:
        return None, "node not found on PATH"
    run = {**tl.loaded["run"], "segments": tl.segs, "settings": tl.settings}
    request = {"run": run, "defs": {str(v): d for v, d in tl.defs.items()}, "from_bar": 0, "to_bar": max(0, tl.bars),
               "flat": True}
    try:
        proc = subprocess.run([node, str(GROOVE_BRIDGE)], input=json.dumps(request), capture_output=True, text=True,
                              encoding="utf-8", timeout=60)
        answer = json.loads(proc.stdout or "{}")
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(answer, dict) or not answer.get("ok") or not isinstance(answer.get("notes"), list):
        return None, (answer.get("error") if isinstance(answer, dict) else None) or f"exit {proc.returncode}, no notes"
    onsets = []
    for e in answer["notes"]:
        if isinstance(e, dict) and isinstance(e.get("midi"), int) and _num(e.get("epoch_ms")) \
                and e["epoch_ms"] < tl.end_epoch:
            onsets.append((tl.clock.t_of(e["epoch_ms"]), e["midi"]))
    return onsets, None


def loopback(tl, snd: dict, node: Optional[str] = None, rebuild: Optional[str] = None) -> dict:
    """The loopback guard (11.3 step 13): more than half of Claude's onsets met by one of his at the same pitch within
    LOOPBACK_MS means the loop may be echoing into the log. rebuild: None (the bridge when it answers, else the def),
    'def' or 'bridge'."""
    onsets, source, why = None, None, None
    if rebuild in (None, "bridge") and GROOVE_BRIDGE.is_file():
        onsets, why = _bridge_onsets(tl, node)
        source = "groove_bridge.mjs" if onsets is not None else None
    elif rebuild == "bridge":
        why = f"{GROOVE_BRIDGE.name} is not built yet"
    if onsets is None:
        onsets, source = _def_onsets(tl), "the def's downbeat strikes" + (f" ({why})" if why else "")
    his: Dict[int, List[float]] = {}
    for n in snd["notes"]:
        his.setdefault(n["note"], []).append(float(n["on_ms"]))
    for v in his.values():
        v.sort()
    matched = 0
    for t, note in onsets:
        seq = his.get(note) or []
        j = bisect_left(seq, t - LOOPBACK_MS)
        if j < len(seq) and seq[j] <= t + LOOPBACK_MS:
            matched += 1
    share = matched / len(onsets) if onsets else 0.0
    suspected = share > LOOPBACK_SHARE
    return {"suspected": suspected, "mirrored_share": _r(share, 2), "claude_onsets": len(onsets), "source": source,
            "say": "the loop may be echoing into the log (MIDI loopback)" if suspected else None}


# ================================================================================ checks and highlights
def card_checks(tl, block: dict, card: Optional[dict], variant, version) -> List[dict]:
    """The card's checks (DATA 2.8), each passing or not, with its say line and the counts behind it."""
    if not card or version is None:
        return []
    out = []
    d = tl.defs[version]
    for c in card.get("checks") or []:
        if c.get("variant") != variant or not isinstance(c.get("slot"), int) or c["slot"] >= len(d["slots"]):
            continue
        f = tl.facts(version, c["slot"])
        pc = ((f["bass"] if c.get("relative_to") == "bass" else f["root"]) + ROLE_INTERVALS.get(c.get("role"), 0)) % 12
        mine = [r for r in block["_recs"] if r["inst"]["slot"] == c["slot"] and r["inst"]["def_version"] == version]
        count = sum(1 for r in mine if r["note"] % 12 == pc)
        landed = sum(1 for x in block["_insts"] if x["slot"] == c["slot"] and x["def_version"] == version
                     and block["_landings"].get(x["i"]) and block["_landings"][x["i"]][0]["note"] % 12 == pc)
        want = c.get("want") or "present"
        ok = count >= 1 if want == "present" else landed >= 1 if want == "landing" else count == 0
        # the note is spelled from the chord's own tones (jam-rulings), as the card names it: Cb over Abm(add9), not B
        note = tone_name(d["slots"][c["slot"]], c.get("role"), c.get("relative_to") or "root") or pr.pc_name(pc, f["key"])
        out.append({"id": c.get("id"), "slot": c["slot"], "role": c.get("role"), "want": want, "pass": ok,
                    "note": note, "count": count, "landings": landed, "say": c.get("say")})
    return out


def card_landing(tl, block: dict, version) -> Optional[dict]:
    """The card's landing (house idea): how often his first note on the landing chord was the note it names."""
    if version is None:
        return None
    landing = tl.defs[version].get("landing")
    if not isinstance(landing, dict) or not isinstance(landing.get("slot"), int) or not isinstance(landing.get("pc"), int):
        return None
    f = tl.facts(version, landing["slot"])
    insts = [x for x in block["_insts"] if x["slot"] == landing["slot"] and x["def_version"] == version]
    # only the times he played over the chord: passes before he joined or after he stopped are not misses
    played = {r["inst"]["i"] for r in block["_recs"]} | {i for i, ld in block["_landings"].items() if ld}
    heard = [x for x in insts if x["i"] in played]
    landed = sum(1 for x in heard if block["_landings"].get(x["i"])
                 and block["_landings"][x["i"]][0]["note"] % 12 == landing["pc"] % 12)
    # spelled from the chord's own tones (jam-rulings); a def recorded before resolve named it is spelled here the same way
    note = landing.get("note") or tone_name(tl.defs[version]["slots"][landing["slot"]], landing.get("role"),
                                            landing.get("relative_to") or "root") or pr.pc_name(landing["pc"], f["key"])
    return {"slot": landing["slot"], "name": f["name"], "note": note,
            "label": tone_label(f, landing["pc"] % 12), "pull": landing.get("pull"), "instances": len(heard),
            "instances_all": len(insts), "landed": landed}


def highlights(block: dict, session: str) -> List[dict]:
    """The top slot instances (11.3 step 14) by new colour labels + 2 x reharmonized + the velocity peak's z-score."""
    recs = block["_recs"]
    vels = [r["vel"] for r in recs if r["vel"] is not None]
    mean = sum(vels) / len(vels) if vels else 0.0
    std = math.sqrt(sum((v - mean) ** 2 for v in vels) / len(vels)) if vels else 0.0
    by_inst: Dict[int, List[dict]] = {}
    for r in recs:
        by_inst.setdefault(r["inst"]["i"], []).append(r)
    seen, cands = set(), []
    for x in sorted(block["_insts"], key=lambda x: x["start_t"]):
        rx = by_inst.get(x["i"], [])
        new = []
        for r in rx:
            if r["top"] and r["class"] in ("colour", "passing") and r["label"] not in seen:
                seen.add(r["label"])
                new.append(r)
        reharm = x.get("_reharm")
        loud = [r for r in rx if r["vel"] is not None]
        peak = max(loud, key=lambda r: (r["vel"], -r["on"])) if loud else None
        z = (peak["vel"] - mean) / std if peak is not None and std > 0 else 0.0
        score = len(new) + 2 * (1 if reharm else 0) + z
        if score <= 0 or not rx:
            continue
        f = x["facts"]
        if reharm:
            t, why = reharm["t_ms"], f"you played {reharm['played']} over {f['name']}"
            evidence = {"played": reharm["played"], "name": f["name"]}
        elif new:
            note = pr.pc_name(new[0]["note"] % 12, f["key"])
            t, why = new[0]["on"], f"new colour: {note} ({new[0]['label']}) for the first time"
            evidence = {"note": note, "label": new[0]["label"]}
        else:
            t, why = peak["on"], f"a peak in your touch (velocity {peak['vel']})"
            evidence = {"velocity": peak["vel"]}
        cands.append((-score, t, {"at": pr.clock(t), "t_ms": t, "slot": x["slot"], "pass": x["pass"], "name": f["name"],
                                  "why": why, "evidence": evidence, "rank": _r(score, 3),
                                  "replay": replay_command(session, t - HIGHLIGHT_LEAD_S * 1000, HIGHLIGHT_SECONDS),
                                  "save": save_command(session, t)}))
    cands.sort(key=lambda c: (c[0], c[1]))
    return [c[2] for c in cands[:HIGHLIGHTS]]


# ============================================================================ talking points (11.4)
def _label_words(label: Optional[str]) -> str:
    return "root" if label == "R" else str(label)


def _span_words(tl, r: dict) -> Tuple[str, float]:
    """('2 beats', 2.0) on a loop's grid, ('1.4 seconds', 1.4) in free play, where there is no beat."""
    if tl.grid:
        beats = max(0.5, _half(r["len_beats"]))
        return f"{_fmt(beats)} beat{'' if beats == 1 else 's'}", beats
    seconds = _r(r["len_ms"] / 1000, 1)
    return f"{_fmt(seconds)} second{'' if seconds == 1 else 's'}", seconds


def _against(f: dict, pc: int) -> str:
    return pr.pc_name((pc - 1) % 12 if (pc - 1) % 12 in f["chord"] else (pc + 1) % 12, f["key"])


def talking_points(block: dict, session: str, run_id: Optional[str], concepts: List[dict],
                   last_types: Sequence[str] = ()) -> List[dict]:
    """Every talking point whose gate passes, with its salience: type weight x min(1, count/5) x 1.25 for the card's
    concept note x 0.5 when the card's last saved riff made the same type of point. Counts, never percentages."""
    tl, slots, recs, phrases = block["_tl"], block["slots"], block["_recs"], block["phrases"]
    concept_set = {(c["slot"], c["pc"]) for c in concepts}
    pts: List[dict] = []

    def add(kind, count, text, times, evidence, concept=False):
        sal = TP_WEIGHTS[kind] * min(1.0, count / SALIENCE_COUNT) * (CONCEPT_BOOST if concept else 1.0) \
            * (REPEAT_DAMP if kind in last_types else 1.0)
        if sal <= 0:
            return
        times = sorted(times)
        pts.append({"type": kind, "run": run_id, "text": text, "times": [pr.clock(t) for t in times[:6]],
                    "replay": replay_command(session, times[0] - HIGHLIGHT_LEAD_S * 1000, HIGHLIGHT_SECONDS)
                    if times else None, "evidence": evidence, "salience": _r(sal), "concept": bool(concept)})

    for s in slots:
        f, tops = s["_facts"], s["_tops"]
        colour = [r for r in tops if r["class"] == "colour"]
        cw = sum(r["w"] for r in colour)
        if colour and cw > 0:
            by: Dict[str, List[dict]] = {}
            for r in colour:
                by.setdefault(r["label"], []).append(r)
            label, rs = max(by.items(), key=lambda kv: (sum(r["w"] for r in kv[1]), len(kv[1]), kv[0]))
            if sum(r["w"] for r in rs) / cw >= T1_LABEL_SHARE and len(rs) >= T1_MIN:
                note = pr.pc_name(rs[0]["note"] % 12, f["key"])
                where = f"{s['name']} ({s['number']})" if s["number"] else s["name"]
                add("T1", len(rs), f"Over {where} your top line leaned on the {_label_words(label)}, {note}: "
                    f"{len(rs)} of {len(tops)} notes, first at {pr.clock(rs[0]['on'])}.", [r["on"] for r in rs],
                    {"name": s["name"], "number": s["number"], "label": label, "note": note, "count": len(rs),
                     "notes": len(tops), "first": pr.clock(rs[0]["on"])}, (s["slot"], rs[0]["note"] % 12) in concept_set)
        sc = s["scale"]
        if sc and sc["named"]:
            degree = _degree(s["number"])
            where = f"the {degree} chord ({s['name']})" if degree else s["name"]
            if sc["own_note"]:
                own_pc = _pc_of_name(sc["own_note"])
                times = [r["on"] for r in tops if r["note"] % 12 == own_pc]
                add("T2", sc["own_count"], f"Over {where} your notes made one scale ({sc['best']}): the "
                    f"{sc['own_note']}, its {_label_words(sc['own_label'])}, came {_times(sc['own_count'])}.", times,
                    {"name": s["name"], "degree": degree, "scale": sc["best"], "note": sc["own_note"],
                     "label": sc["own_label"], "count": sc["own_count"]}, (s["slot"], own_pc) in concept_set)
            else:
                add("T2", sc["notes"], f"Over {where} your notes kept to five ({sc['best']}), {sc['notes']} of them "
                    f"in all.", [r["on"] for r in tops], {"name": s["name"], "degree": degree, "scale": sc["best"],
                                                          "count": sc["notes"]})
        if s["class"] == "borrowed":
            hits: Dict[int, List[dict]] = {}
            for r in tops:
                pc = r["note"] % 12
                if r["class"] in ("outside", "slide_in") and pc in f["key_scale"] and pc not in f["scale"]:
                    hits.setdefault(pc, []).append(r)
            if hits:
                pc, rs = max(hits.items(), key=lambda kv: (len(kv[1]), -kv[0]))
                if len(rs) >= T5_MIN:
                    name = pr.pc_name(pc, f["key"])
                    word = f"{name} natural" if len(name) == 1 else name
                    has = next((pr.pc_name(q, f["key"]) for q in sorted(f["scale"])
                                if abs(pr._signed(q - pc)) == 1 and pr.pc_name(q, f["key"])[0] == name[0]), None)
                    where = f"{s['name']} ({s['number']}, borrowed)" if s["number"] else f"{s['name']} (borrowed)"
                    add("T5", len(rs), f"Over {where} you played {word}, the key's note, {_times(len(rs))}"
                        + (f"; the chord's scale has {has}." if has else "."), [r["on"] for r in rs],
                        {"name": s["name"], "number": s["number"], "note": name, "count": len(rs), "scale_note": has},
                        (s["slot"], pc) in concept_set)

    if len(phrases) >= T3_MIN_PHRASES:
        col = [p for p in phrases if p["landing"]["class"] in ("colour", "passing")]
        if col:
            labels = _count(col, lambda p: p["landing"]["label"])
            mostly = next(iter(labels))
            add("T3", len(col), f"{len(col)} of your {len(phrases)} phrases landed on a colour, mostly the "
                f"{_label_words(mostly)}.", [p["t_ms"] for p in col],
                {"landed": len(col), "phrases": len(phrases), "label": mostly},
                any((p["_last"]["inst"]["slot"], p["_last"]["note"] % 12) in concept_set for p in col))

    rubs = [(s, r) for s in slots for r in s["_tops"]
            if r["class"] == "rub" and (tl.grid or r["len_beats"] >= PASSING_MAX_BEATS)]
    if rubs:
        s, r = max(rubs, key=lambda sr: (sr[1]["len_beats"], -sr[1]["on"]))
        f, pc = s["_facts"], r["note"] % 12
        name = pr.pc_name(pc, f["key"])
        span, amount = _span_words(tl, r)
        text = (f"At {pr.clock(r['on'])} you held {name} over {s['name']} for {span}: it rubs a half step against the "
                f"{_against(f, pc)}.")
        passing = [q for s2 in slots for q in s2["_tops"] if q["class"] == "passing" and q["note"] % 12 == pc]
        times = [r["on"]]
        evidence = {"at": pr.clock(r["on"]), "note": name, "name": s["name"], "length": amount,
                    "against": _against(f, pc), "count": len(rubs)}
        if passing:
            text += f" At {pr.clock(passing[0]['on'])} the same {name} passed quickly."
            times.append(passing[0]["on"])
            evidence["passing_at"] = pr.clock(passing[0]["on"])
        add("T4", len(rubs), text, times, evidence, (s["slot"], pc) in concept_set)

    out_n = sum(1 for r in recs if r["class"] in ("outside", "slide_in"))
    if len(recs) >= T6_MIN_NOTES and out_n < len(recs) * T6_MAX_RATE:
        keys = sorted({x["facts"]["key"] for x in block["_insts"]})
        key_text = keys[0] if len(keys) == 1 else "the loop's keys"
        add("T6", len(recs), (f"None of your {len(recs)} notes left {key_text}." if out_n == 0 else
                              f"Only {out_n} of your {len(recs)} notes left {key_text}."), [],
            {"notes": len(recs), "outside": out_n, "key": key_text})

    slides = sorted((r for r in recs if r["class"] == "slide_in"), key=lambda r: r["on"])
    if len(slides) >= T7_MIN:
        targets = _count(slides, lambda r: f"{pr.pc_name(r['next_top']['note'] % 12, r['inst']['facts']['key'])}|{r['direction']}")
        top_target, k = next(iter(targets.items()))
        tname, direction = top_target.split("|")
        first = pr.clock(slides[0]["on"])
        if k == len(slides):
            text = f"You slid into {tname} from a half step {direction} {len(slides)} times, first at {first}."
        else:
            text = (f"You slid into a note from a half step away {len(slides)} times, most often into {tname} from "
                    f"{direction} ({k}), first at {first}.")
        add("T7", len(slides), text, [r["on"] for r in slides],
            {"count": len(slides), "target": tname, "direction": direction, "most": k, "first": first},
            any((r["inst"]["slot"], r["next_top"]["note"] % 12) in concept_set for r in slides))

    if tl.grid and len(phrases) >= T10_MIN_PHRASES:
        lengths = _count(phrases, lambda p: _fmt(p["bars"]))
        bars_text, k = next(iter(lengths.items()))
        pickups = sum(1 for p in phrases if p["pickup"])
        add("T10", k, f"Your phrases were mostly {bars_text} bar{'' if bars_text == '1' else 's'} ({k} of "
            f"{len(phrases)}), and " + (f"{pickups} started with a pickup." if pickups else "none started with a pickup."),
            [p["t_ms"] for p in phrases], {"bars": float(bars_text), "count": k, "phrases": len(phrases),
                                           "pickups": pickups})

    passes = block.get("passes") or []
    # only passes that hold his playing: a loop that ran before he joined, or on after he stopped, is not growth
    played = [p for p in passes if p["top_line_notes"] >= T13_MIN_PASS_NOTES]
    if tl.grid and len(played) >= T13_MIN_PASSES:
        head, tail = played[:2], played[-2:]
        a, na = sum(p["counts"]["colour"] for p in head), sum(p["top_line_notes"] for p in head)
        b, nb = sum(p["counts"]["colour"] for p in tail), sum(p["top_line_notes"] for p in tail)
        if na >= T13_MIN_NOTES and nb >= T13_MIN_NOTES and abs(b / nb - a / na) >= T13_MIN_CHANGE:
            p1, p2 = head[0]["pass"], head[-1]["pass"]
            q1, q2 = tail[0]["pass"], tail[-1]["pass"]
            pair = lambda x, y: f"{x}-{y}" if y == x + 1 else f"{x} and {y}"  # noqa: E731
            last_two = [p["pass"] for p in passes[-2:]] == [q1, q2]
            where = "the last two" if last_two else f"passes {pair(q1, q2)}"
            add("T13", max(a, b), f"Colour notes went from {a} of {na} in passes {pair(p1, p2)} to {b} of {nb} in "
                f"{where}.", [], {"from": a, "from_notes": na, "passes": [p1, p2], "to": b, "to_notes": nb,
                                  "to_passes": [q1, q2]})

    ants = block["anticipations"]
    if tl.grid and len(ants) >= T14_MIN:
        add("T14", len(ants), f"You arrived early on the chord change {len(ants)} times.", [a["t_ms"] for a in ants],
            {"count": len(ants)})
    order = list(TP_WEIGHTS)
    pts.sort(key=lambda p: (-p["salience"], order.index(p["type"])))
    return pts


def question_candidates(block: dict, session: str, concepts: List[dict]) -> List[dict]:
    """Ambiguous moments to ask about (11.4): a held rub, an outside note of a beat or more, a rare landing."""
    concept_set = {(c["slot"], c["pc"]) for c in concepts}
    out = []

    def add(kind, r, slot, weight, text, evidence):
        sal = QUESTION_WEIGHTS[kind] * weight * (CONCEPT_BOOST if (slot, r["note"] % 12) in concept_set else 1.0)
        out.append({"text": text, "at": pr.clock(r["on"]), "t_ms": r["on"], "kind": kind, "salience": _r(sal),
                    "replay": replay_command(session, r["on"] - QUESTION_REPLAY_S * 1000, 2 * QUESTION_REPLAY_S),
                    "evidence": evidence})

    for s in block["slots"]:
        f = s["_facts"]
        for r in s["_tops"]:
            name = pr.pc_name(r["note"] % 12, f["key"])
            if r["class"] == "rub":
                add("rub", r, s["slot"], max(0.5, r["len_beats"]),
                    f"At {pr.clock(r['on'])} the {name} rubbed against the {_against(f, r['note'] % 12)} in {s['name']}. "
                    f"Did you want that rub?", {"note": name, "name": s["name"], "against": _against(f, r["note"] % 12)})
            elif r["class"] == "outside" and r["len_beats"] >= 1 - 1e-6:
                span, amount = _span_words(block["_tl"], r)
                add("outside", r, s["slot"], r["len_beats"],
                    f"At {pr.clock(r['on'])} the {name} sat outside {s['name']} for {span}. Was that a sound you were "
                    f"reaching for?", {"note": name, "name": s["name"], "length": amount})
    lands = [(x, block["_landings"][x["i"]]) for x in block["_insts"] if block["_landings"].get(x["i"])]
    if lands:
        per = _count(lands, lambda xv: xv[1][1])
        for x, (r, cls, label) in lands:
            if per[cls] / len(lands) < QUESTION_RARE_LANDING:
                f = x["facts"]
                name = pr.pc_name(r["note"] % 12, f["key"])
                add("landing", r, x["slot"], 1.0,
                    f"At {pr.clock(r['on'])} you landed on {name}, the {_label_words(label)} of {f['name']}, which you "
                    f"did only {_times(per[cls])}. Did you mean that landing?",
                    {"note": name, "label": label, "name": f["name"], "count": per[cls]})
    out.sort(key=lambda q: (-q["salience"], q["t_ms"]))
    return out


def choose_try(block: dict, card: Optional[dict], concepts: List[dict], point_types: Sequence[str], version) -> dict:
    """One thing to try (11.4): the first rule that applies."""
    tl, tops = block["_tl"], block["_tops"]
    for c in concepts:
        c["count"] = sum(1 for r in tops if r["inst"]["slot"] == c["slot"] and r["note"] % 12 == c["pc"]
                         and r["inst"]["def_version"] == version)
    low = [c for c in concepts if c["count"] < TRY_CONCEPT_MIN]
    if low and version is not None:
        c = low[0]
        bar = int(tl.defs[version]["slots"][c["slot"]]["at_beat"] // tl.m) + 1
        target = TRY_TARGET_LOW + (c["pc"] - TRY_TARGET_LOW) % 12
        return {"text": f"Land your top note on {c['note']} in bar {bar}.", "rule": 1,
                "card": {"id": (card or {}).get("id"), "target_notes": [target], "bar": bar},
                "evidence": {"note": c["note"], "bar": bar, "count": c["count"]}}
    rubs = [r for r in tops if r["class"] == "rub"]
    if len(rubs) >= TRY_HELD_RUBS:
        common = _count(rubs, lambda r: r["note"] % 12)
        pc = next(iter(common))
        f = next(r["inst"]["facts"] for r in rubs if r["note"] % 12 == pc)
        tone = _against(f, pc)
        return {"text": f"Let the rub pass quickly, or step it down to {tone}.", "rule": 2,
                "card": {"id": (card or {}).get("id")}, "evidence": {"note": pr.pc_name(pc, f["key"]), "tone": tone,
                                                                     "count": len(rubs)}}
    if "T6" in point_types and block["_insts"]:
        f = block["_insts"][0]["facts"]
        third = next((pc for pc, role in f["roles"].items() if role == "third"), None)
        if third is not None:
            return {"text": f"Slide into the 3rd of {f['name']} from a half step below.", "rule": 3,
                    "card": {"id": (card or {}).get("id"),
                             "target_notes": [TRY_TARGET_LOW + (third - TRY_TARGET_LOW) % 12]},
                    "evidence": {"role": "3rd", "name": f["name"]}}
    phrases = block["phrases"]
    if tl.grid and len(phrases) >= TRY_EARLY_MIN_PHRASES and all(
            p.get("beat") is not None and abs(p["beat"]) <= GRID_TOL and not p["pickup"] for p in phrases):
        return {"text": "Start one phrase a beat early.", "rule": 4, "card": {"id": (card or {}).get("id")},
                "evidence": {"phrases": len(phrases)}}
    if card and card.get("try"):
        return {"text": card["try"], "rule": 5, "card": {"id": card.get("id")}, "evidence": {"card_try": card["try"]}}
    words = "Keep the loop going and follow" if tl.grid else "Pick"
    return {"text": f"{words} one note you like into the next chord.", "rule": 5, "card": None, "evidence": {}}


# ================================================================================================ riff
RUN_ORDER = ("run", "card", "mode", "key", "bpm", "beats_per_bar", "alignment", "window", "loopback", "coverage",
             "readings", "slots", "degrees_by_bar", "passes", "phrases", "anticipations", "slide_ins", "checks",
             "card_landing", "concept", "highlights", "enough", "say", "problems", "notes")


def constants() -> dict:
    return {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, str, tuple, dict))
            and k not in ("RUN_ORDER",)}


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def _note_out(r: dict) -> dict:
    pos = r["pos"]
    return {"t_ms": r["on"], "at": pr.clock_tenths(r["on"]), "pass": pos["pass"], "bar": pos["bar"],
            "run_bar": pos["run_bar"], "beat": _r(pos["beat"]), "note": r["note"], "name": r["name"], "top": r["top"],
            "slot": r["inst"]["slot"], "class": r["class"], "label": r["label"], "bass_label": r["bass_label"],
            "w": _r(r["w"]), "grid": pos["grid"], "beats": _r(r["len_beats"]), "vel": r["vel"], "flags": r["flags"]}


def _last_types(jam_root, card_id: Optional[str], run_id: Optional[str]) -> List[str]:
    """The talking-point types of the card's last saved riff (for REPEAT_DAMP)."""
    if not card_id:
        return []
    best = None
    for path in sorted((Path(jam_root) / "riffs").glob("*.json")):
        if path.stem == run_id:
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(doc, dict) or not any(((b.get("card") or {}).get("id") == card_id)
                                                for b in doc.get("runs") or [] if isinstance(b, dict)):
            continue
        if best is None or str(doc.get("saved_at") or "") > str(best.get("saved_at") or ""):
            best = doc
    return [p.get("type") for p in (best or {}).get("talking_points") or [] if isinstance(p, dict)]


def run_block(loaded: dict, session: str, info: dict, snd: dict, opts: Optional[dict] = None,
              clock: Optional[Clock] = None, node: Optional[str] = None, rebuild: Optional[str] = None) -> dict:
    run = loaded["run"]
    clock = clock or align(loaded, session, info)
    tl = RunTimeline(loaded, clock)
    duration = float(info.get("last_t_ms") or 0) or float(snd["duration_ms"])
    if clock.method != "assumed" and (tl.end_t <= 0 or tl.start_t >= duration + 1):
        raise RiffError(f"run {run.get('run')} ({pr.clock(max(0.0, tl.start_t))} to {pr.clock(max(0.0, tl.end_t))} on "
                        f"the session's clock) does not overlap session {session}")
    card = run.get("card_snapshot") if isinstance(run.get("card_snapshot"), dict) else None
    variant = (run.get("card") or {}).get("variant")
    version = tl.segs[0]["def_version"]
    block = analyse_block(tl, snd, opts, card, variant)
    ref = run.get("card") or {}
    bpms = sorted({s["bpm"] for s in tl.segs})
    concepts = _concepts(tl, card, variant, version)
    block.update({
        "run": run.get("run"),
        "card": {"id": ref.get("id"), "rev": ref.get("rev"), "variant": variant, "title": ref.get("title")}
        if ref.get("id") else None,
        "mode": run.get("mode"), "key": run.get("key") or tl.defs[version].get("key"), "bpm": bpms,
        "beats_per_bar": tl.m,
        "alignment": {"method": clock.method, "error_ms": clock.error_ms, "bar0_t_ms": _r(tl.bar0_t, 1),
                      "approx": clock.approx, "output_latency_ms": clock.output_latency_ms, "page_id": clock.page_id,
                      "anchors": len(clock.anchors)},
        "window": {"from": pr.clock(max(0.0, tl.start_t)), "to": pr.clock(max(0.0, tl.end_t)),
                   "from_t_ms": _r(tl.start_t, 1), "to_t_ms": _r(tl.end_t, 1), "stop_bar": run.get("stop_bar"),
                   "stop_reason": run.get("stop_reason")},
        "loopback": loopback(tl, snd, node, rebuild),
        "checks": card_checks(tl, block, card, variant, version),
        "card_landing": card_landing(tl, block, version),
        "problems": list(loaded.get("problems") or []),
        "_card": card, "_concepts": concepts, "_version": version})
    if clock.approx:
        for x in block["anticipations"] + block["phrases"]:
            x["approx"] = True
    return block


def finish(session: str, info: Optional[dict], blocks: List[dict], jam_root, free: Optional[dict] = None,
           theory_source=None, node: Optional[str] = None) -> dict:
    """Readings, highlights, talking points, the question and the try over every block; the output document."""
    every = blocks + ([free] if free else [])
    apply_readings(every, theory_source, node)
    points, questions, tries = [], [], []
    for b in every:
        b["highlights"] = highlights(b, session)
        n = len(b["_recs"])
        b["enough"] = n >= MIN_ONSETS
        concepts = b.get("_concepts") or []
        if not b["enough"]:
            b["say"] = f"not enough playing inside the loop to talk about ({n} notes)"
            b["concept"] = []
            continue
        card = b.get("_card")
        pts = talking_points(b, session, b.get("run"), concepts,
                             _last_types(jam_root, (card or {}).get("id"), b.get("run")))
        points += pts
        for q in question_candidates(b, session, concepts):
            q["run"] = b.get("run")
            questions.append(q)
        t = choose_try(b, card, concepts, [p["type"] for p in pts], b.get("_version"))
        t["run"] = b.get("run")
        tries.append((len(b["_tops"]), t))
        b["concept"] = [{k: c[k] for k in ("slot", "note", "label", "source", "count") if k in c} for c in concepts]
    order = list(TP_WEIGHTS)
    points.sort(key=lambda p: (-p["salience"], order.index(p["type"])))
    questions.sort(key=lambda q: (-q["salience"], q["t_ms"]))

    def shaped(b):
        b["notes"] = [_note_out(r) for r in b["_recs"]]
        head = {k: b[k] for k in RUN_ORDER if k in b}
        head.update({k: v for k, v in b.items() if k not in head})
        return _strip(head)

    start, _ = session_window(info or {})
    doc = {"api": RIFF_API, "constants": constants(), "session": session, "session_start": _local(start),
           "runs": [shaped(b) for b in blocks]}
    if free is not None:
        doc["free_play"] = shaped(free)
    doc.update({"talking_points": points[:CHAT_POINTS],
                "question": questions[0] if questions else None,
                "try": max(tries, key=lambda x: x[0])[1] if tries else None})
    return doc


# ------------------------------------------------------------------------------------------ finding runs
def _session_rows(store: PerformanceStore) -> List[Tuple[str, dict]]:
    rows = []
    for row in store.list():
        try:
            rows.append((row["session"], store.info(row["session"])))
        except (PerformanceError, OSError, ValueError):
            continue
    return rows


def _candidates(store: PerformanceStore, loaded: dict, rows=None) -> List[Tuple[str, dict]]:
    """Sessions a run overlaps on the wall clock, best first: one its acks name, then by overlap. An ack naming a
    session that does not overlap (a clock or copy mix-up) is not a match: the no-overlap guard reports it."""
    named = {a["log"]["session"] for a in loaded["acks"] if isinstance(a.get("log"), dict) and a["log"].get("session")}
    r0, r1 = run_window(loaded)
    found = []
    for sid, info in rows if rows is not None else _session_rows(store):
        s0, s1 = session_window(info)
        overlap = min(r1, s1) - max(r0, s0) if s0 is not None else -math.inf
        if overlap > 0:
            found.append((sid not in named, -overlap, sid, info))
    found.sort(key=lambda x: (x[0], x[1], x[2]))
    return [(sid, info) for _, _, sid, info in found]


def _no_overlap(store: PerformanceStore, loaded: dict, rows=None) -> RiffError:
    r0, r1 = run_window(loaded)
    near = []
    for sid, info in rows if rows is not None else _session_rows(store):
        s0, s1 = session_window(info)
        if s0 is not None:
            near.append((min(abs(s0 - r1), abs(r0 - s1)), sid, s0, s1))
    near.sort()
    lines = [f"no practice session overlaps run {loaded['run'].get('run')}, which played from {_local(r0)} to "
             f"{_local(r1)}"]
    if near:
        lines.append("nearest sessions: " + "; ".join(f"{sid} ({_local(s0)}, {pr.clock(s1 - s0)} long)"
                                                     for _, sid, s0, s1 in near[:3]))
    return RiffError("\n".join(lines))


def _read_session(store: PerformanceStore, session: str) -> Tuple[dict, dict, List[str]]:
    info = store.info(session)
    events, problems = pr.read_events(store, session)
    return info, pr.sounding(events), problems


def _card_def(card: str, key: Optional[str], jam_root: Path) -> Tuple[dict, Optional[dict]]:
    path = Path(card)
    if path.suffix.lower() == ".json" and path.is_file():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RiffError(f"--card {card}: unreadable ({type(exc).__name__}: {exc})") from exc
        if not isinstance(d, dict) or d.get("api") != DEF_API:
            raise RiffError(f"--card {card} is not a resolved def ({DEF_API})")
        return d, None
    cpath = jam_root / "deck" / "cards" / f"{card}.json"
    if not cpath.is_file():
        raise RiffError(f"no card {card} under {cpath.parent}")
    cdoc = json.loads(cpath.read_text(encoding="utf-8"))
    try:
        from .jam import resolve as jam_resolve  # built by phase J3
    except ImportError as exc:
        raise RiffError("resolving a card needs arsenal/jam/resolve.py, which is not built yet; pass a resolved def "
                        "file (*.json) as --card") from exc
    try:
        return jam_resolve.Resolver().resolve(cdoc, key=key), cdoc
    except (jam_resolve.ResolveError, jam_resolve.BridgeUnavailable) as exc:
        raise RiffError(f"--card {card} could not be resolved ({exc})") from exc


def riff(run: Optional[str] = None, session: Optional[str] = None, root=None, jam_root=None, card: Optional[str] = None,
         key: Optional[str] = None, bpm: Optional[float] = None, start: Optional[str] = None, end: Optional[str] = None,
         bars: Optional[Tuple[int, int]] = None, pass_: Optional[int] = None, rebuild: Optional[str] = None,
         node: Optional[str] = None, theory_source=None) -> dict:
    """The riff document for one invocation form of 11.1 (see main). Raises RiffError for the 11.5 guards."""
    store = PerformanceStore(root)
    jam_root = Path(jam_root) if jam_root else DEFAULT_JAM_ROOT
    opts = {"bars": bars, "pass": pass_}

    def one_session(selector) -> str:
        ids = pr.resolve_sessions(store, selector)
        if len(ids) != 1:
            raise RiffError(f"--session takes one session (an id or latest); {selector} names {len(ids)}")
        return ids[0]

    if card:
        if not start:
            raise RiffError("--card needs --from m:ss (where the grid starts in the session)")
        d, cdoc = _card_def(card, key, jam_root)
        sid = one_session(session or "latest")
        info, snd, problems = _read_session(store, sid)
        t0 = pr.parse_clock(start)
        t1 = pr.parse_clock(end) if end else float(snd["duration_ms"]) + 1
        if t1 <= t0:
            raise RiffError(f"--from {start} must come before --to {end}")
        tempo = (cdoc or {}).get("tempo") or {}
        loaded = {"run": {"run": None, "mode": "loop", "key": d.get("key"), "beats_per_bar": d["beats_per_bar"],
                          "segments": [{"from_bar": 0, "bpm": float(bpm or tempo.get("bpm") or 66), "epoch_ms": t0,
                                        "def_version": 1, "def_from_bar": 0}],
                          "settings": [{"from_bar": 0, "backing": d.get("backing") or "comp", "groove": "hold",
                                        "humanize": 0.6}],
                          "stopped_epoch_ms": t1, "card": {"id": (cdoc or d.get("card") or {}).get("id"),
                                                           "rev": (cdoc or d.get("card") or {}).get("rev"),
                                                           "variant": (d.get("card") or {}).get("variant"),
                                                           "title": (cdoc or d.get("card") or {}).get("title")},
                          "card_snapshot": cdoc},
                  "defs": {1: d}, "acks": [], "lines": [], "problems": problems}
        if key and nashville.parse_key(key) and d.get("key") and nashville.parse_key(key)["name"] != \
                nashville.parse_key(d["key"])["name"]:
            loaded["problems"].append(f"the def is in {d['key']}, not {key}")
        block = run_block(loaded, sid, info, snd, opts, Clock("assumed", [(0.0, 0.0)], None), node, rebuild)
        return finish(sid, info, [block], jam_root, theory_source=theory_source, node=node)

    rows = _session_rows(store)
    if run is None and session:
        sid = one_session(session)
        info, snd, problems = _read_session(store, sid)
        blocks = []
        for r in list_runs(jam_root):
            if r.get("mode") not in ("loop", "try"):
                continue
            try:
                loaded = load_run(jam_root, r["run"])
            except RiffError:
                continue
            if sid in [c[0] for c in _candidates(store, loaded, rows)]:
                blocks.append(run_block(loaded, sid, info, snd, opts, node=node, rebuild=rebuild))
        blocks.sort(key=lambda b: b["_tl"].start_t)
        if blocks:
            return finish(sid, info, blocks, jam_root, theory_source=theory_source, node=node)
        events, _ = pr.read_events(store, sid)
        analysed = pr.analyze(events, theory_source, node)
        tl = FreeTimeline(analysed, snd["duration_ms"])
        free = analyse_block(tl, snd)
        free.update({"mode": "free play", "key": analysed.get("home_key"),
                     "chords": "chords read from your own playing", "problems": problems})
        return finish(sid, info, [], jam_root, free=free, theory_source=theory_source, node=node)

    if run in (None, "latest"):
        wanted = one_session(session) if session else None
        for r in list_runs(jam_root):
            if r.get("mode") not in ("loop", "try") or not (r.get("state") == "stopped" or r.get("closed")):
                continue
            try:
                loaded = load_run(jam_root, r["run"])
            except RiffError:
                continue
            ids = [c[0] for c in _candidates(store, loaded, rows)]
            if ids and (wanted is None or wanted in ids):
                sid = wanted or ids[0]
                break
        else:
            raise RiffError(f"no stopped loop or try run under {jam_root / 'runs'} overlaps "
                            f"{'session ' + wanted if wanted else 'a practice session'}")
    else:
        loaded = load_run(jam_root, run)
        if session:
            sid = one_session(session)
        else:
            found = _candidates(store, loaded, rows)
            if not found:
                raise _no_overlap(store, loaded, rows)
            sid = found[0][0]
    info, snd, problems = _read_session(store, sid)
    block = run_block(loaded, sid, info, snd, opts, node=node, rebuild=rebuild)
    block["problems"] += problems
    return finish(sid, info, [block], jam_root, theory_source=theory_source, node=node)


def save(doc: dict, jam_root=None) -> List[Path]:
    """--save: state/arsenal/jam/riffs/<run>.json per run, holding that run's block and its talking points."""
    folder = (Path(jam_root) if jam_root else DEFAULT_JAM_ROOT) / "riffs"
    written = []
    stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    for b in doc.get("runs") or []:
        if not b.get("run"):
            continue
        one = {**doc, "saved_at": stamp, "runs": [b],
               "talking_points": [p for p in doc.get("talking_points") or [] if p.get("run") == b["run"]],
               "question": doc["question"] if (doc.get("question") or {}).get("run") == b["run"] else None,
               "try": doc["try"] if (doc.get("try") or {}).get("run") == b["run"] else None}
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{b['run']}.json"
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(one, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
        written.append(path)
    return written


# ================================================================================ render and wording guard
def render(doc: dict) -> str:
    """The chat-ready block: coverage, up to 6 talking points with times, checks, highlights, the question, the try."""
    out: List[str] = []
    for b in doc.get("runs") or []:
        card = b.get("card") or {}
        what = f"{card['title']} ({card['id']})" if card.get("id") else "a loop with no card"
        bpm = "-".join(_fmt(x) for x in (b["bpm"][0], b["bpm"][-1])) if len(b["bpm"]) > 1 else _fmt(b["bpm"][0])
        a, c = b["alignment"], b["coverage"]
        out.append(f"Riff on {what}: {b['mode']} in {b['key']} at {bpm} bpm, run {b['run'] or '(no run)'}.")
        within = f", within {_fmt(a['error_ms'])} ms" if a.get("error_ms") is not None else ""
        level = f": {a['method']}{within}" if a["method"] != "assumed" else ""
        out.append(f"Session {doc['session']} ({doc['session_start']}), lined up by {METHOD_WORDS[a['method']]}{level}.")
        out.append(f"{c['passes']} passes, {c['bars']} bars, {c['notes']} notes of yours ({c['top_line_notes']} in "
                   f"the top line), from {b['window']['from']} to {b['window']['to']}.")
        if b["loopback"]["suspected"]:
            out.append(f"Heads up: {b['loopback']['say']}.")
        if not b.get("enough"):
            out.append(b["say"])
        out += [f"Note: {p}" for p in b.get("problems") or []]
    free = doc.get("free_play")
    if free:
        out.append(f"Free play in session {doc['session']} ({doc['session_start']}): no loop, so no beat to measure "
                   f"against. {free['coverage']['chords_read']} chords read from your own playing, "
                   f"{free['coverage']['notes']} notes of yours.")
        if not free.get("enough"):
            out.append(free["say"])
    if doc.get("talking_points"):
        out.append("")
        out.append("Talking points:")
        for p in doc["talking_points"]:
            out.append(f"- {p['text']}")
            if p.get("replay"):
                out.append(f"    replay: {p['replay']}")
    checks = [(b, ch) for b in doc.get("runs") or [] for ch in b.get("checks") or []]
    landings = [b["card_landing"] for b in doc.get("runs") or [] if b.get("card_landing")]
    if checks or landings:
        out.append("")
        out.append("Card checks:")
        for _, ch in checks:
            if ch["pass"]:
                out.append(f"- {ch['say'] or ch['id']}" + (f" ({_times(ch['count'])})" if ch["want"] == "present" else ""))
            elif ch["want"] == "present":
                out.append(f"- {ch['id']}: {ch['note']} did not come up this time")
            elif ch["want"] == "landing":
                out.append(f"- {ch['id']}: no landing on {ch['note']} this time")
            else:
                out.append(f"- {ch['id']}: {ch['note']} came up {_times(ch['count'])}")
        for ld in landings:
            if ld["instances"]:
                out.append(f"- the landing ({ld['note']}, the {_label_words(ld['label'])} of {ld['name']}): you "
                           f"started on it {ld['landed']} of the {ld['instances']} times you played over it")
            else:
                out.append(f"- the landing ({ld['note']}, the {_label_words(ld['label'])} of {ld['name']}): you did "
                           f"not play over that chord this time")
            if ld.get("pull"):
                out.append(f"    {ld['pull']}")
    hl = [(b, h) for b in (doc.get("runs") or []) + ([free] if free else []) for h in b.get("highlights") or []]
    if hl:
        out.append("")
        out.append("Highlights:")
        for _, h in hl:
            out.append(f"- {h['at']} over {h['name']}: {h['why']}")
            out.append(f"    replay: {h['replay']}")
            out.append(f"    keep it: {h['save']}")
    if doc.get("question"):
        out.append("")
        out.append(f"A question: {doc['question']['text']}")
        out.append(f"    replay: {doc['question']['replay']}")
    if doc.get("try"):
        out.append("")
        out.append(f"One thing to try: {doc['try']['text']}")
    return "\n".join(out).rstrip("\n") + "\n"


SENTENCE_KEYS = ("text", "why", "fact", "say")
_TOKEN_RE = re.compile(r"[A-Za-z#]*\d[A-Za-z0-9#:./\-]*")


def sentences(doc: dict) -> List[str]:
    """The prose this module writes (the card's own lines are the card's words, not ours)."""
    out = [p["text"] for p in doc.get("talking_points") or []]
    if doc.get("question"):
        out.append(doc["question"]["text"])
    if doc.get("try") and doc["try"].get("rule") != 5:
        out.append(doc["try"]["text"])
    for b in (doc.get("runs") or []) + ([doc["free_play"]] if doc.get("free_play") else []):
        out += [h["why"] for h in b.get("highlights") or []]
        out += [p["fact"] for p in b.get("passes") or [] if p.get("fact")]
        if b.get("say"):
            out.append(b["say"])
    return out


def _leaves(obj, strings: set, numbers: set) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k not in SENTENCE_KEYS:
                _leaves(v, strings, numbers)
    elif isinstance(obj, list):
        for v in obj:
            _leaves(v, strings, numbers)
    elif isinstance(obj, str):
        strings.add(obj)
    elif _num(obj):
        numbers.add(round(float(obj), 3))


def _backed(token: str, strings: set, numbers: set) -> bool:
    if token in strings:
        return True
    try:
        return round(float(token), 3) in numbers
    except ValueError:
        pass
    parts = [p for p in re.split(r"[-/]", token) if p]
    return len(parts) > 1 and all(_backed(p, strings, numbers) for p in parts)


def wording_problems(doc: dict, text: Optional[str] = None) -> List[str]:
    """The wording guard (11.4): no forbidden word or % anywhere in the render; every number in our sentences is a
    field of the JSON; theory names only in brackets after the plain words."""
    text = render(doc) if text is None else text
    problems = []
    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{word}\b", text, re.I):
            problems.append(f"forbidden word {word!r}")
    if "%" in text:
        problems.append("forbidden token '%'")
    strings, numbers = set(), set()
    _leaves(doc, strings, numbers)
    for s in sentences(doc):
        for tok in _TOKEN_RE.findall(s):
            tok = tok.rstrip(".:,;")
            if tok and not _backed(tok, strings, numbers):
                problems.append(f"{tok!r} in {s!r} is not a field of the JSON")
        bare = re.sub(r"\([^)]*\)", "", s)
        for word in THEORY_WORDS:
            if word in bare:
                problems.append(f"theory name {word!r} outside brackets in {s!r}")
    return problems


# ================================================================================================ CLI
def _parse_bars(text: str) -> Tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", text or "")
    if not m or int(m.group(1)) < 1 or (m.group(2) and int(m.group(2)) < int(m.group(1))):
        raise ValueError(f"--bars takes A-B with 1 <= A <= B (got {text!r})")
    return int(m.group(1)), int(m.group(2) or m.group(1))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="py -m arsenal.practice riff",
                                     description="His notes against a jam run's bars and chords (read only).")
    parser.add_argument("run", nargs="?", default=None,
                        help="a run id or latest (the default; with --session alone, every run in that session)")
    parser.add_argument("--session", help="a session id or latest")
    parser.add_argument("--root", help="the sessions directory (default: state/arsenal/performance)")
    parser.add_argument("--jam-root", help="the jam directory (default: state/arsenal/jam)")
    parser.add_argument("--card", help="a card id (or a resolved def file) he played along with, with no run")
    parser.add_argument("--key", help="with --card: the key he played it in")
    parser.add_argument("--bpm", type=float, help="with --card: the tempo")
    parser.add_argument("--from", dest="start", help="with --card: m:ss where bar 1 starts in the session")
    parser.add_argument("--to", dest="end", help="with --card: m:ss where he stopped")
    parser.add_argument("--bars", help="only run bars A-B (counted from 1)")
    parser.add_argument("--pass", dest="pass_", type=int, help="only pass N (counted from 1)")
    parser.add_argument("--rebuild", choices=("auto", "def", "bridge"), default="auto",
                        help="how the loopback guard rebuilds Claude's notes (default: the groove bridge if it answers)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--out", help="also write the output to this file")
    parser.add_argument("--save", action="store_true", help="write state/arsenal/jam/riffs/<run>.json")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if (getattr(stream, "encoding", "") or "").lower().replace("-", "") != "utf8":
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, ValueError, OSError):
                pass
    try:
        if args.out and Path(args.out).is_dir():
            raise ValueError(f"--out {args.out} is a directory; give a file path")
        if args.pass_ is not None and args.pass_ < 1:
            raise ValueError(f"--pass counts from 1 (got {args.pass_})")
        if args.bpm is not None and not (math.isfinite(args.bpm) and 30 <= args.bpm <= 240):
            raise ValueError(f"--bpm must be 30..240 (got {args.bpm:g})")
        bars = _parse_bars(args.bars) if args.bars else None
        doc = riff(args.run, args.session, args.root, args.jam_root, args.card, args.key, args.bpm, args.start,
                   args.end, bars, args.pass_, None if args.rebuild == "auto" else args.rebuild)
    except RiffError as exc:
        print(exc, file=sys.stderr)
        return exc.code
    except PerformanceError as exc:
        print(f"{exc}; try: py -m arsenal.practice sessions", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n" if args.json else render(doc)
    if args.save:
        for path in save(doc, args.jam_root):
            print(f"saved {path}", file=sys.stderr)
    if args.out:
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text, encoding="utf-8", newline="\n")
        except OSError as exc:
            print(f"--out {args.out} could not be written ({type(exc).__name__}: {exc})", file=sys.stderr)
            return 2
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
