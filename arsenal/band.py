"""Claude's band for FL Studio: pattern sets (bass, drums, comp, pad) written as JSON, Standard MIDI Files and a baked
module for the VFX Script "Claude Band" patch.

Daniel improvises; FL plays these lines through his own instruments. Nothing here talks to FL, opens a port or
writes into an Image-Line folder: every file lands in this repo (state/arsenal/band, arsenal/fl/vfx/generated) and
Daniel drags or copies it himself. Research: research/in-flight/fl-jam-bridge-2026-09-14/.

THE PATTERN CONTRACT (version 1; the VFX Script build reads exactly this)
  {"version": 1, "id": str, "title": str, "key": "Db major", "bpm_hint": number, "meter": [4, 4],
   "length_beats": number (whole bars), "chords": [{"beat", "name": "Gbmaj9", "nns": "4maj9"}],
   "lanes": {"bass": {"notes": [...]}, "drums": {"notes": [...]}, "comp": {"notes": [...]}, "pad": {"notes": [...]}}}
  note = {"beat": number, "len": number, "note": 0..127, "vel": 1..127}
  - Beats are quarter notes from the pattern start; a pattern loops. Integral beats are written as ints.
  - All four lanes are always present; a lane that is off has "notes": [].
  - Drums are General MIDI numbers (36 kick, 37 side stick, 38 snare, 42 closed hat, 44 pedal hat, 46 open hat,
    49 crash, 51 ride, toms 41 43 45 47 48 50); the VFX script remaps them for FPC or Addictive Drums 2.
  - Within a lane, notes are sorted by (beat, note), every note ends by length_beats, and two notes of one pitch
    never overlap (normalize_notes). A "playlist" is pattern sets plus a current index; a switch lands on the next
    bar line of the running loop (next_bar_line), never mid-bar.
  - Note names in this module are scientific: MIDI 60 = C4. FL's piano roll labels MIDI 60 as C5.

REGISTERS
  bass E1..G2 (MIDI 28..43); comp and pad C3..B4 (48..71), so everything from C5 (72) up is Daniel's. A shell comp
  (--shell) keeps to C3..E4 (48..64) and two notes, leaving most of the octave above middle C to his left hand.

CHORD LOOPS (make)
  "Gbmaj9 | Bbm11 | Ab11/Gb | Dbadd9" or "4maj9 - 6m11 - 5^11/4 - 1add9" with --key "Db major".
  - A "|" marks bar lines: the chords between two bars share that bar equally ("Gmaj9 A/G | F#m9 Bm9").
    Without "|", chords are separated by spaces or " - " and each lasts one bar.
  - "Chord:beats" sets a length ("Db13sus4:2 Db7b9:2"); "%" repeats the chord before it.
  - Numbers follow arsenal/nashville.py: degrees from the key's tonic with major-scale accidentals ("b7", "b6maj9#11"
    in a minor key), "^" joins a suffix digit ("5^7"), "/4" is the bass degree, a leading "-" is a minor mark.
  - The loop must add up to whole bars. --bars repeats it (or cuts it short); without --key the key is estimated.

STYLES AND THEIR RHYTHMS (4/4; beats within a bar or within a chord)
  bass ("a change" = the next chord has another bass note)
    roots-on-1   the chord's bass note (the slash bass if any) on 1 of every bar and at each chord change, held
    root-fifth   bass note on 1, the chord's fifth on 3 (a segment shorter than 4 beats keeps just the bass note)
    walking      quarter notes: bass note, chord tones stepping toward the approach, and on the last beat before
                 a change a half step below (rising) or above (falling) the next bass note. Before a change the
                 approach is an 8th and the next bass note steps in early on the and of 4, tied over the bar line
                 (the top of the chord loop strikes its 1 again, so a pattern started cold has its downbeat)
    pocket       the neo-soul pocket, a two-bar cell with rests, locked to the neo-soul kick (1, the a of 2, the
                 and of 3). Bar A: bass note on 1, a short ghost of it on the a of 1, the fifth (below where it
                 fits) on the and of 2, clear before the kick, the 7th (or 6th) with the kick on the and of 3,
                 and a half-step approach into a change on the a of 4. Bar B: bass note held on 1, the fifth on
                 the and of 2, an octave pop on 3 where it fits, the 7th with the kick on the and of 3, then the
                 next bass note anticipated on the and of 4 (restruck on the 1). Shorter chords: bass note,
                 ghost, and a step into the next on the last and
    gospel       bass note on 1, its octave (or fifth where the octave leaves E1..G2) on the and of 2, then:
                 where the bass note stays, bass note on 3 and a chromatic triplet run on 4 into the next;
                 into a phrase top (every 4 bars in a loop of 8 bars or more, else every 2, the loop top
                 included: the key drop and the turnaround), bass note on 3, then a chromatic run that lands on
                 the next bass note early, tied over the bar line as in walking: 16ths on the a of 3, 4 and the e
                 of 4 landing on the and of 4, or with brushes (a triplet ride) triplets from the last triplet of
                 3 landing on the ride's skip, the last triplet of 4;
                 into any other change, a chord tone on 3 and one half step into the next bass note on 4, which
                 lands on its 1: no run, room for the piano's own slides
    offbeat      house bass: the bass note on every and (the kick keeps the beats), nothing on the beat
    pedal        one note under every chord: the key's tonic (the first bass note without a key), once a bar
    synth-pulse  straight 8ths on the bass note
    none         an empty lane
  drums (velocities humanised; "laid back" = 10 ticks late at 480 PPQ)
    ballad        kick 1, side stick (37) 3, soft closed hats in 8ths
    neo-soul      kick 1, a2 (1.75) and the and of 3; snare 2 and 4 laid back; ghost snares on the a of 3 and 4;
                  16th hats swung (default swing 0.58); open hat on the and of 4. Bass, comp and pad notes on an
                  odd 16th move with the swing onto the hat's own tick (no flam), and their ends follow
                  (swing_amount, _swing_notes); other drum styles do not swing, so nothing else moves
    halftime      kick 1 and the and of 3; snare 3; 8th hats (a kick pickup on the a of 4 every second bar)
    four-on-floor kick every beat, snare 2 and 4, a soft closed hat on each beat and an open hat (46) on each and
    brushes       ride (51) "ding, ding-da ding" with triplet skips, pedal hat (44) and a feathered snare on 2 and
                  4, feathered kick on 1 and 3
    ambient       sparse: kick on 1 every other bar, a side stick on the and of 3 in every second bar of four,
                  crash (49) at each 4-bar phrase top and a crescendo ride swell over the last two beats of each
                  phrase (the swell is ambient's fill)
    none          an empty lane
    --fill        the last bar's beats 3-4 become a snare-and-tom fill and a crash lands on the loop top
                  (softer for ballad and brushes; ambient keeps its swell)
    Other meters get a plain groove (kick on 1, snare at the half bar, 8th hats) shaded by the style's dynamics.
  comp  voice-led rootless voicings (3rd and 7th first, then colour tones), up to 4 notes, in a rhythm that follows
        the drum style (COMP_RHYTHMS; "top 2" = the voicing's two highest notes, bars alternate A and B):
          ballad         1 held three beats; top 2 touched softly on 4
          neo-soul       A: pushed a 16th early (held 1.5), a stab on the a of 3. B: pushed, a short stab on the and
                         of 2, then space. The loop's first 1 is never pushed (nothing to push from)
          halftime       1 held 1.4, a stab with the snare on 3; B adds top 2 on the and of 4
          four-on-floor  house stabs on 1, the and of 2 and 4 (3-3-2)
          brushes        Charleston: 1 and the and of 2
          ambient        a whole-bar hold
          none           1 held 1.75 beats, restruck on the and of 3 (other meters: 1 held 1.75, restruck on the
                         and of 3 only in a bar of 4 beats or more)
        Every chord change and bar line is struck; a rhythm hit under 3/4 beat after an off-rhythm change is left
        out, and every strike ends before the next one.
        --shell voices the comp as two-note shells instead: the 3rd (or sus tone) and the 7th (or the next colour
        tone), in C3..E4 (KEYS_SHAPE["shell"]), same rhythm
  pad   the same voice leading, up to 5 notes, held for the whole chord
  Voice leading treats the loop as a ring: the voicings are chosen together (least total movement, top voice
  included) so the last chord leads back into the first as smoothly as any other change. A minor second is never
  stacked with its lower note below G3, and low thirds and seconds are kept wide (LIL).

LIVENESS (reproducible: the same arguments always give the same notes)
  - HUMANIZE INVARIANT: velocity shading is drawn from random.Random("<id>/<bar>/<lane>"), one generator per bar
    per lane (Humanizer), never one sequence for the whole set. A bar's shading depends only on the set's id, that
    bar and that lane, so editing bar 2 never reshuffles bar 7, repeats of a line are not stamped copies, and the
    whole set rebuilds from its id.
  - --dropout P (0..1): bar k (never the first, never right after another dropout bar) rests when
    random.Random("<id>/dropout/<k>").random() < 1 - (1 - P) ** PHRASE_WEIGHT[k % 4], so a rest leans on the last
    bar of each 4-bar phrase (a breath before the phrase top), then its 2nd bar, as the VFX band's Dropout does.
    In a rest bar every lane except bass is silent, by the VFX
    band's Dropout rules: a note starting in a bar's last 8th and ringing over its bar line is a push that belongs
    to the next bar, so a push into a rest bar rests and a push out of one plays whole; a held comp or pad chord
    that would ring past the rest bar is struck again on the bar after. 0 (the default) means no holes.

WRITERS
  - pattern-set JSON: <state>/patterns/<id>.json, stamped "generator": GENERATOR_VERSION (the stamp is dropped on
    load). A stored set wins over a seed of the same id, so show, export-mid and export-vfx warn on stderr when a
    stored set comes from an older generator (no stamp counts as 1); `seeds --write` rebuilds the seeds
  - Standard MIDI Files, written by hand with struct: <id>.mid (type 1, 480 PPQ: a conductor track with the
    tempo, meter, key signature and chord markers, then one track per lane: bass ch 1, comp ch 2, pad ch 3,
    drums ch 10) and <id>-<lane>.mid (type 1, one track with tempo and notes: drag it onto that channel's
    piano roll; hold Shift to skip FL's import dialog, leave "Blend with existing data" off to replace)
  - the baked VFX module (export-vfx), in the format arsenal/fl/vfx/arsenal_band.py imports as `arsenal_patterns`
    (ASCII only, no file I/O needed inside FL):
        VERSION = 1
        LIVE_PATH = None, or the path given with --live-path (the playlist the band's "Live file" checkbox follows)
        DRUM_MAPS = {}
        PATTERNS = [ <pattern set dicts in playlist order; the band's Pattern knob picks the index> ]
    plus the live playlist twin arsenal_live.json: {"version": 1, "rev": <content hash>, "current": <0-based>,
    "patterns": [...]}. Default folder: arsenal/fl/vfx/generated/. At most 64 sets and 4096 notes per lane (the
    band's limits). Copying the module into FL's [User Data Folder]/VFX Script/Python is Daniel's step.

CLI (py -m arsenal.band <verb> --help; every verb takes --state DIR, default state/arsenal/band or
$ARSENAL_BAND_STATE)
  make LOOP --key K --bpm N --bars N --bass STYLE --drums STYLE [--comp] [--shell] [--pad] [--fill] [--swing S]
       [--dropout P] [--meter 4/4] [--title T] [--id ID] [--out DIR] [--add]
  seeds [--write] [--add]      the six starter sets, explained; --write saves them into the store
  list                         stored pattern sets and seeds
  show ID [--bars-per-line N]  a text grid of the lanes
  export-mid ID [--out DIR]    .mid files (default <state>/mid/<id>/)
  export-vfx [--out FILE] [--live-path PATH] [--no-write-seeds]
                               the baked module and live JSON from the playlist; when it is empty, the seeds, which
                               are also saved into the store as `seeds --write` would (--no-write-seeds skips that)
  playlist add ID [--at POS] | list | rm ID-or-POS | current POS     (positions count from 1)
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import random
import re
import struct
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import nashville as nv

PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parent
DEFAULT_STATE = REPO / "state" / "arsenal" / "band"
VFX_OUT = PACKAGE / "fl" / "vfx" / "generated" / "arsenal_patterns.py"
VFX_LIVE_NAME = "arsenal_live.json"
VFX_MAX_PATTERNS = 64        # arsenal/fl/vfx/arsenal_band.py MAX_PATTERNS
VFX_MAX_NOTES = 4096         # arsenal/fl/vfx/arsenal_band.py MAX_NOTES_PER_LANE
STATE_ENV = "ARSENAL_BAND_STATE"

VERSION = 1
GENERATOR_VERSION = 2        # bump whenever make_pattern_set writes other notes for the same arguments
GENERATOR_KEY = "generator"  # the stamp PatternStore.save adds to a stored file (never part of a loaded set)
PPQ = 480
LANES = ("bass", "drums", "comp", "pad")
CHANNELS = {"bass": 0, "comp": 1, "pad": 2, "drums": 9}
BASS_RANGE = (28, 43)        # E1..G2
KEYS_RANGE = (48, 71)        # C3..B4
SHELL_RANGE = (48, 64)       # C3..E4: a shell comp keeps out of the octave above middle C
BASS_STYLES = ("roots-on-1", "root-fifth", "walking", "pocket", "gospel", "offbeat", "pedal", "synth-pulse", "none")
DRUM_STYLES = ("ballad", "neo-soul", "halftime", "four-on-floor", "brushes", "ambient", "none")
BPM_BY_DRUMS = {"ballad": 66, "neo-soul": 84, "halftime": 72, "four-on-floor": 118, "brushes": 88, "ambient": 62,
                "none": 80}
NEO_SOUL_SWING = 0.58
LAY_BACK = 10 / PPQ          # a laid-back backbeat: 10 ticks late (about 12 ms at 84 BPM)
GAP = 0.05                   # beats of air before the next strike
MIN_LEN = 1 / 32
MAX_BARS = 64
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

KICK, STICK, SNARE, HAT, PEDAL, OPEN_HAT, CRASH, RIDE = 36, 37, 38, 42, 44, 46, 49, 51
TOM_HI, TOM_HI_MID, TOM_LOW_MID, TOM_LOW, TOM_FLOOR_HI, TOM_FLOOR_LOW = 50, 48, 47, 45, 43, 41
GM_NAMES = {35: "kick2", 36: "kick", 37: "stick", 38: "snare", 39: "clap", 40: "snare2", 41: "tom41", 42: "hat",
            43: "tom43", 44: "pedal", 45: "tom45", 46: "open", 47: "tom47", 48: "tom48", 49: "crash", 50: "tom50",
            51: "ride", 53: "bell", 57: "crash2"}
KIT_ORDER = (57, 49, 51, 53, 46, 42, 44, 50, 48, 47, 45, 43, 41, 39, 40, 38, 37, 35, 36)

SHARP_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLAT_NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")


class BandError(ValueError):
    pass


# ================================================================================================ numbers and time
def q(beat: float) -> float:
    """A beat snapped to the 480 PPQ tick grid (so the JSON, the .mid and the grid agree)."""
    return round(round(beat * PPQ) / PPQ, 6)


def _num(x: float):
    x = q(x)
    return int(x) if x == int(x) else x


def parse_meter(text) -> Tuple[int, int]:
    if isinstance(text, (list, tuple)):
        n, d = text
    else:
        m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", str(text))
        if not m:
            raise BandError(f"a meter reads like 4/4, not {text!r}")
        n, d = int(m.group(1)), int(m.group(2))
    if not (isinstance(n, int) and 1 <= n <= 32 and d in (2, 4, 8, 16)):
        raise BandError(f"unsupported meter {n}/{d}")
    return n, d


def beats_per_bar(meter: Sequence[int]) -> float:
    """Quarter-note beats in one bar: 4/4 -> 4, 3/4 -> 3, 6/8 -> 3, 12/8 -> 6, 7/8 -> 3.5."""
    n, d = meter
    return n * 4 / d


def is_whole_bars(beats: float, meter: Sequence[int]) -> bool:
    bars = beats / beats_per_bar(meter)
    return bars >= 1 and abs(bars - round(bars)) < 1e-6


def next_bar_line(position: float, meter: Sequence[int]) -> float:
    """The first bar line strictly after `position` (beats since the loop began; it may run past the loop's length).
    A switch requested exactly on a downbeat waits for the following bar, so a change never lands half-heard."""
    bpb = beats_per_bar(meter)
    return q((math.floor(position / bpb + 1e-9) + 1) * bpb)


def midi_name(note: int, flats: bool = True) -> str:
    return (FLAT_NAMES if flats else SHARP_NAMES)[note % 12] + str(note // 12 - 1)


# ===================================================================================================== chords
def _clean(text: str) -> str:
    return str(text).strip().replace("♭", "b").replace("♯", "#").replace("Δ", "maj")


def suffix_tones(suffix: str) -> Dict[str, int]:
    """A chord suffix -> {role: semitones above the root}. Roles: 1 3 5 (or 2/4 for sus), 7 or 6, 9 b9 #9 11 #11
    13 b13. "maj9#11", "m11", "13sus4", "7(#9,b13)", "m7b5", "dim7", "6/9", "add9", "5" (power), "11" (dominant
    eleventh, third left out), "alt"."""
    raw = suffix
    s = _clean(suffix).replace("^", "").replace("(", "").replace(")", "").replace(",", "").replace(" ", "")
    s = s.replace("ø7", "m7b5").replace("ø", "m7b5").replace("°7", "dim7").replace("°", "dim")
    if s.startswith("-"):
        s = "m" + s[1:]

    def take(prefix: str) -> bool:
        nonlocal s
        if s.startswith(prefix):
            s = s[len(prefix):]
            return True
        return False

    quality, maj7 = "major", False
    if take("maj") or (s[:1] == "M" and take("M")):
        maj7 = True
    elif take("min") or take("mi") or take("m"):
        quality = "minor"
        if take("maj") or (s[:1] == "M" and take("M")):
            maj7 = True
    elif take("dim"):
        quality = "dim"
    elif take("aug") or take("+"):
        quality = "aug"

    ext = None
    m = re.match(r"(6/9|69|13|11|9|7|6|5)", s)
    if m:
        ext = "6/9" if m.group(1) == "69" else m.group(1)
        s = s[m.end():]
    if ext == "5" and (quality != "major" or maj7):
        raise BandError(f"cannot read the chord suffix {raw!r}")

    tones = {"1": 0, "3": {"major": 4, "minor": 3, "dim": 3, "aug": 4}[quality],
             "5": {"major": 7, "minor": 7, "dim": 6, "aug": 8}[quality]}
    if ext == "5":
        if s:
            raise BandError(f"cannot read the chord suffix {raw!r} (at {s!r})")
        return {"1": 0, "5": 7}
    if ext in ("7", "9", "11", "13"):
        tones["7"] = 11 if maj7 else 9 if (quality == "dim" and ext == "7") else 10
        if ext in ("9", "11", "13"):
            tones["9"] = 2
        if ext == "11" or (ext == "13" and quality == "minor"):
            tones["11"] = 5
        if ext == "13":
            tones["13"] = 9
        if ext == "11" and quality == "major":
            del tones["3"]                      # a dominant or major eleventh leaves the third out
    elif ext == "6":
        tones["6"] = 9
    elif ext == "6/9":
        tones["6"], tones["9"] = 9, 2
    elif maj7 and quality == "minor":
        tones["7"] = 11                          # "mmaj" without a digit still means the major seventh

    while s:
        if take("sus4") or take("sus"):
            tones.pop("3", None)
            tones.pop("11", None)
            tones["4"] = 5
        elif take("sus2"):
            tones.pop("3", None)
            tones["2"] = 2
        elif take("add9") or take("add2"):
            tones["9"] = 2
        elif take("add#11"):
            tones["#11"] = 6
        elif take("add11") or take("add4"):
            tones["11"] = 5
        elif take("add13") or take("add6"):
            tones["13"] = 9
        elif take("alt"):
            tones.pop("9", None)
            tones.pop("5", None)
            tones.update({"b9": 1, "#9": 3, "b13": 8})
            tones.setdefault("7", 10)
        elif take("omit3") or take("no3"):
            tones.pop("3", None)
        elif take("omit5") or take("no5"):
            tones.pop("5", None)
        elif take("maj7"):
            tones["7"] = 11
        elif take("b5"):
            tones["5"] = 6
        elif take("#5"):
            tones["5"] = 8
        elif take("b9"):
            tones.pop("9", None)
            tones["b9"] = 1
        elif take("#9"):
            tones.pop("9", None)
            tones["#9"] = 3
        elif take("#11"):
            tones.pop("11", None)
            tones["#11"] = 6
        elif take("b13"):
            tones.pop("13", None)
            tones["b13"] = 8
        elif take("7"):
            tones.setdefault("7", 10)
        else:
            raise BandError(f"cannot read the chord suffix {raw!r} (at {s!r})")
    return tones


_NUMBER_RE = re.compile(r"^(#{1,2}|b{1,2})?([1-7])(?!\d)(.*)$")
_NUMBER_BASS_RE = re.compile(r"^(.*)/(#{1,2}|b{1,2})?([1-7])$")


def _acc(text: Optional[str]) -> int:
    text = text or ""
    return len(text) if text.startswith("#") else -len(text)


def _spelled(letter: int, pc: int) -> str:
    acc = (pc - nv.LETTER_PC[letter] + 6) % 12 - 6
    return nv.LETTERS[letter] + ("#" * acc if acc > 0 else "b" * -acc)


def _key_info(key: Optional[str]) -> Optional[Dict]:
    if key is None:
        return None
    k = nv.parse_key(key)
    if not k:
        raise BandError(f'cannot read the key {key!r} (try "Db major" or "Bb minor")')
    letter = nv.LETTERS.index(k["name"][0])
    return {**k, "letter": letter}


def _degree(key: Dict, acc: int, degree: int) -> Tuple[int, str]:
    letter = (key["letter"] + degree - 1) % 7
    pc = (key["tonic"] + nv.LETTER_PC[degree - 1] + acc) % 12
    return pc, _spelled(letter, pc)


def parse_chord_token(token: str, key: Optional[Dict]) -> Dict:
    """One chord (a name, or a Nashville number with a key) -> {name, root, bass, suffix, tones}."""
    tok = _clean(token)
    m = _NUMBER_RE.match(tok)
    if m:
        if key is None:
            raise BandError(f"{token!r} is a Nashville number: give --key to read it")
        pc, root_name = _degree(key, _acc(m.group(1)), int(m.group(2)))
        rest, bass_pc, bass_name = m.group(3), pc, None
        bm = _NUMBER_BASS_RE.match(rest)
        if bm:
            rest = bm.group(1)
            bass_pc, bass_name = _degree(key, _acc(bm.group(2)), int(bm.group(3)))
        suffix = rest.replace("^", "")
        if suffix.startswith("-"):
            suffix = "m" + suffix[1:]
        name = root_name + suffix + ("/" + bass_name if bass_name else "")
        return {"name": name, "root": pc, "bass": bass_pc, "suffix": suffix, "tones": suffix_tones(suffix)}
    parsed = nv.parse_chord(tok)
    if not parsed or parsed["kind"] != "chord":
        raise BandError(f"cannot read {token!r} as a chord")
    root_sp, bass_sp = parsed["root"], parsed["bass"]
    root = (nv.LETTER_PC[root_sp[0]] + root_sp[1]) % 12
    bass = (nv.LETTER_PC[bass_sp[0]] + bass_sp[1]) % 12 if bass_sp else root
    suffix = parsed["suffix"]
    head = _spelled(root_sp[0], root)
    name = head + suffix + ("/" + _spelled(bass_sp[0], bass) if bass_sp else "")
    return {"name": name, "root": root, "bass": bass, "suffix": suffix, "tones": suffix_tones(suffix)}


def _split_duration(token: str) -> Tuple[str, Optional[float]]:
    m = re.fullmatch(r"(.+):(\d+(?:\.\d+)?)", token)
    if not m:
        return token, None
    beats = float(m.group(2))
    if beats <= 0:
        raise BandError(f"{token!r}: a chord needs a length above 0 beats")
    return m.group(1), beats


def parse_loop(text: str, key: Optional[str] = None, meter=(4, 4)) -> List[Dict]:
    """A chord loop -> one cycle of chords, each {name, root, bass, suffix, tones, beat, dur, input}."""
    k = _key_info(key)
    bpb = beats_per_bar(meter)
    text = _clean(text)
    if not text:
        raise BandError("the chord loop is empty")
    groups: List[Tuple[List[str], bool]] = []
    if "|" in text:
        for seg in text.split("|"):
            toks = [t for t in re.split(r"\s+", seg.strip()) if t and t != "-"]
            if toks:
                groups.append((toks, True))
    else:
        for tok in re.split(r"\s+-\s+|\s+", text):
            if tok and tok != "-":
                groups.append(([tok], False))
    cycle, beat, previous = [], 0.0, None
    for toks, is_bar in groups:
        items = [_split_duration(t) for t in toks]
        explicit = sum(d for _, d in items if d is not None)
        implicit = [d for _, d in items if d is None]
        if implicit:
            share = ((bpb if is_bar else bpb * len(implicit)) - explicit) / len(implicit)
            if share <= 1e-9:
                raise BandError(f"the chords {' '.join(toks)!r} leave no room in a bar of {bpb:g} beats")
        for tok, dur in items:
            dur = share if dur is None else dur
            if tok == "%":
                if previous is None:
                    raise BandError('"%" repeats the chord before it, and there is none')
                chord = {k2: v for k2, v in previous.items() if k2 not in ("beat", "dur")}
            else:
                chord = parse_chord_token(tok, k)
                chord["input"] = tok
            chord.update(beat=q(beat), dur=q(dur))
            cycle.append(chord)
            previous = chord
            beat += dur
    if not cycle:
        raise BandError("the chord loop is empty")
    if not is_whole_bars(beat, meter):
        raise BandError(f"the chords add up to {beat:g} beats, not whole bars of {bpb:g}")
    return cycle


def estimate_key(cycle: List[Dict]) -> str:
    """The major or minor key that numbers the most chords diatonically (ties: the last chord's root as tonic,
    then the first's, then major)."""
    best = None
    for tonic in range(12):
        for mode in ("major", "minor"):
            name = nv.key_name_of(tonic, mode)
            score = 0.0
            for c in cycle:
                r = nv.nashville_from_name(c["name"], name)
                if r and r["diatonic"]:
                    score += 3
                elif r and r["acc"] == 0:
                    score += 1
            if cycle[-1]["root"] == tonic:
                score += 1.5
            if cycle[0]["root"] == tonic:
                score += 1
            if mode == "major":
                score += 0.25
            if best is None or score > best[0]:
                best = (score, name)
    return best[1]


def _expand(cycle: List[Dict], total: float) -> List[Dict]:
    cycle_len = cycle[-1]["beat"] + cycle[-1]["dur"]
    out, offset = [], 0.0
    while offset < total - 1e-9:
        for i, c in enumerate(cycle):
            start = offset + c["beat"]
            if start >= total - 1e-9:
                break
            out.append({**c, "beat": q(start), "dur": q(min(c["dur"], total - start)), "cycle_index": i})
        offset += cycle_len
    return out


def _segments(timeline: List[Dict], bpb: float, total: float) -> List[Tuple[float, float, Dict, Dict]]:
    """Chords cut at bar lines: (start, end, chord, the chord sounding at `end`, wrapping to the loop top)."""
    starts = []
    for c in timeline:
        s, e = c["beat"], c["beat"] + c["dur"]
        cuts = [s] + [q(b * bpb) for b in range(int(math.ceil(s / bpb + 1e-9)), int(math.floor(e / bpb - 1e-9)) + 1)
                      if s + 1e-9 < b * bpb < e - 1e-9]
        for i, cs in enumerate(cuts):
            ce = cuts[i + 1] if i + 1 < len(cuts) else e
            starts.append((q(cs), q(ce), c))
    out = []
    for s, e, c in starts:
        nxt = next((c2 for c2 in timeline if c2["beat"] <= e + 1e-9 < c2["beat"] + c2["dur"]), timeline[0])
        if e >= total - 1e-9:
            nxt = timeline[0]
        out.append((s, e, c, nxt))
    return out


# ===================================================================================================== lanes
def normalize_notes(notes: Iterable[Dict], length: float) -> List[Dict]:
    """Snap to ticks, clamp velocities, keep notes inside the loop, drop a quieter same-pitch duplicate, cut a note
    short where the next note of its pitch starts, and sort by (beat, note)."""
    ordered = sorted(notes, key=lambda n: (q(n["beat"]), int(n["note"]), -int(n["vel"])))
    last: Dict[int, Dict] = {}
    kept = []
    for n in ordered:
        b = q(n["beat"])
        if b < 0 or b >= length - 1e-9:
            continue
        pitch = int(n["note"])
        if not 0 <= pitch <= 127:
            continue
        item = {"beat": b, "len": q(max(0.0, min(float(n["len"]), length - b))), "note": pitch,
                "vel": max(1, min(127, int(round(n["vel"]))))}
        prev = last.get(pitch)
        if prev is not None:
            if prev["beat"] == b:
                continue
            if prev["beat"] + prev["len"] > b:
                prev["len"] = q(b - prev["beat"])
        kept.append(item)
        last[pitch] = item
    return [{"beat": _num(n["beat"]), "len": _num(n["len"]), "note": n["note"], "vel": n["vel"]}
            for n in kept if n["len"] >= MIN_LEN - 1e-9]


class Humanizer:
    """Velocity shading for one lane, seeded per (seed, bar, lane): each bar draws from its own
    random.Random("<seed>/<bar>/<lane>"), so a bar's shading never depends on what the other bars hold (the
    HUMANIZE INVARIANT in the module header). Within a bar, notes draw in the order the lane adds them."""

    def __init__(self, seed: str, lane: str, bpb: float):
        self.seed, self.lane, self.bpb = str(seed), lane, float(bpb)
        self._bars: Dict[int, random.Random] = {}

    def bar_of(self, beat: float) -> int:
        return int(math.floor(q(beat) / self.bpb + 1e-9))

    def rng(self, beat: float) -> random.Random:
        bar = self.bar_of(beat)
        if bar not in self._bars:
            self._bars[bar] = random.Random(f"{self.seed}/{bar}/{self.lane}")
        return self._bars[bar]

    def vel(self, beat: float, vel: float, spread: int) -> int:
        return max(1, min(127, int(round(vel)) + self.rng(beat).randint(-spread, spread)))


def _place(pc: int, prev: Optional[int], lo: int = BASS_RANGE[0], hi: int = BASS_RANGE[1],
           center: float = 35.5) -> int:
    options = [p for p in range(lo, hi + 1) if p % 12 == pc % 12]
    return min(options, key=lambda p: ((abs(p - prev) if prev is not None else 0) + 0.3 * abs(p - center), p))


def _nearest_in_range(pc: int, near: int, lo: int = BASS_RANGE[0], hi: int = BASS_RANGE[1]) -> int:
    options = [p for p in range(lo, hi + 1) if p % 12 == pc % 12]
    return min(options, key=lambda p: (abs(p - near), -p))


def _chord_pcs(chord: Dict, roles=("1", "3", "4", "2", "5", "7", "6")) -> List[int]:
    return sorted({(chord["root"] + chord["tones"][r]) % 12 for r in roles if r in chord["tones"]} | {chord["bass"]})


def bass_lane(timeline: List[Dict], style: str, bpb: float, total: float, human: Humanizer,
              pedal_pc: Optional[int] = None, scale_pcs: Sequence[int] = (), feel: str = "straight") -> List[Dict]:
    """One bass line over `timeline`. The line is played through once to find the note it ends on, then generated
    for real starting from there, so the loop's seam is voice-led like every other change. feel "triplet" (under
    the brushes' triplet ride) puts the gospel runs on triplets."""
    if style == "none":
        return []
    if style not in BASS_STYLES:
        raise BandError(f"unknown bass style {style!r}; one of {', '.join(BASS_STYLES)}")
    if style == "pedal":
        pc = timeline[0]["bass"] if pedal_pc is None else pedal_pc
        p = _place(pc, None, center=31)
        notes, bar = [], 0.0
        while bar < total - 1e-9:
            notes.append({"beat": bar, "len": min(bpb, total - bar) - GAP, "note": p,
                          "vel": human.vel(bar, 90 if bar == 0 else 84, 5)})
            bar += bpb
        return normalize_notes(notes, total)
    _, end = _bass_pass(timeline, style, bpb, total, Humanizer("scout", "bass", bpb), None, scale_pcs, feel)
    notes, _ = _bass_pass(timeline, style, bpb, total, human, end, scale_pcs, feel)
    return normalize_notes(notes, total)


def _tie_anticipations(notes: List[Dict]) -> List[Dict]:
    """An anticipation (a note marked "tie" with the beat it lands on) holds over the change: the next note of its
    pitch that starts on that beat is folded into it. At the end of a pass there is no such note, so the top of the
    loop strikes its 1 again."""
    out = [dict(n) for n in notes]
    for n in out:
        land = n.pop("tie", None)
        if land is None:
            continue
        land = q(land)
        follow = next((m for m in out if m is not n and m["note"] == n["note"] and abs(q(m["beat"]) - land) < 1e-9),
                      None)
        if follow is not None:
            n["len"] = q(follow["beat"] + follow["len"] - n["beat"])
            follow["drop"] = True
    return [n for n in out if not n.pop("drop", False)]


def _bass_pass(timeline: List[Dict], style: str, bpb: float, total: float, human: Humanizer,
               prev: Optional[int], scale_pcs: Sequence[int], feel: str = "straight") -> Tuple[List[Dict], Optional[int]]:
    lo, hi = BASS_RANGE
    notes: List[Dict] = []
    bars_total = max(1, int(round(total / bpb)))
    phrase = 4 if bars_total >= 8 and bars_total % 4 == 0 else 2 if bars_total % 2 == 0 else 1

    def add(beat, length, note, vel, spread=5, tie=None):
        item = {"beat": beat, "len": length, "note": note, "vel": human.vel(beat, vel, spread)}
        if tie is not None:
            item["tie"] = tie
        notes.append(item)

    def phrase_top(beat: float) -> bool:
        """A bar line that opens a phrase (every 4 bars in a loop of 8 or more, else every 2), the loop top included:
        where the key drops and where the loop turns around."""
        bars = beat / bpb
        return abs(bars - round(bars)) < 1e-9 and (int(round(bars)) % bars_total) % phrase == 0

    def step_into(target: int, p0: int) -> int:
        """A half step below a rising target (above a falling one), kept inside E1..G2."""
        approach = target - 1 if target >= p0 else target + 1
        if not lo <= approach <= hi:
            approach = target + 1 if approach < lo else target - 1
        return approach

    for s, e, chord, nxt in _segments(timeline, bpb, total):
        d = e - s
        p0 = _place(chord["bass"], prev)
        on_bar = abs(s / bpb - round(s / bpb)) < 1e-9
        accent = 100 if on_bar else 94
        changes = nxt is not chord and nxt["bass"] % 12 != chord["bass"] % 12
        if style == "roots-on-1":
            add(s, d - GAP, p0, accent)
            prev = p0
        elif style == "root-fifth":
            if d >= 4 - 1e-9:
                add(s, 2 - GAP, p0, accent)
                fifth = (chord["root"] + chord["tones"].get("5", 7)) % 12
                pf = _nearest_in_range(fifth, p0 + 5)
                add(s + 2, d - 2 - GAP, pf, 86)
                prev = pf
            else:
                add(s, d - GAP, p0, accent)
                prev = p0
        elif style == "synth-pulse":
            t = s
            while t < e - 1e-9:
                beat_in_bar = (t % bpb)
                vel = 106 if beat_in_bar < 1e-9 else 94 if abs(beat_in_bar - round(beat_in_bar)) < 1e-9 else 78
                add(t, min(0.42, e - t - 0.02), p0, vel, 3)
                t = q(t + 0.5)
            prev = p0
        elif style == "offbeat":
            whole = math.floor(s + 1e-9)
            t = q(whole + 0.5 if s <= whole + 0.5 + 1e-9 else whole + 1.5)   # the first and at or after s
            played = False
            while t < e - 1e-9:
                beat_in_bar = t % bpb
                vel = 96 if beat_in_bar > bpb - 1 else 90 if int(beat_in_bar) % 2 == 0 else 84
                add(t, min(0.4, e - t - 0.02), p0, vel, 3)
                played = True
                t = q(t + 1)
            if not played:                         # a chord too short to reach an and still sounds its bass note
                add(s, max(MIN_LEN, min(0.4, d - 0.02)), p0, 84, 3)
            prev = p0
        elif style == "pocket":
            target = _place(nxt["bass"], p0)
            fifth = _nearest_in_range((chord["root"] + chord["tones"].get("5", 7)) % 12, p0 - 5)
            if fifth == p0:
                fifth = _nearest_in_range((chord["root"] + chord["tones"].get("5", 7)) % 12, p0 + 7)
            colour = next((chord["tones"][r] for r in ("7", "6", "4", "3") if r in chord["tones"]), 7)
            seventh = _nearest_in_range((chord["root"] + colour) % 12, p0 - 2)
            if seventh in (p0, fifth):
                seventh = p0 + 12 if p0 + 12 <= hi else fifth
            step = step_into(target, p0) if changes else fifth
            bar_index = int(math.floor(s / bpb + 1e-9))
            if d >= 4 - 1e-9 and bpb == 4 and bar_index % 2 == 0:            # bar A
                add(s, 0.7, p0, 102)
                add(s + 0.75, 0.15, p0, 42, 3)
                add(s + 1.5, 0.2, fifth, 84)                                  # clear before the kick on the a of 2
                add(s + 2.5, 0.4, seventh, 88)                                # with the kick on the and of 3
                add(s + 3.75, 0.2, step if changes else p0, 72 if changes else 44, 3)
                prev = step if changes else p0
            elif d >= 4 - 1e-9 and bpb == 4:                                  # bar B
                add(s, 1.0, p0, 100)
                add(s + 1.5, 0.2, fifth, 80)
                pop = p0 + 12 if p0 + 12 <= hi else None
                if pop is not None and pop != fifth:
                    add(s + 2, 0.2, pop, 70, 4)
                add(s + 2.5, 0.3, seventh, 86)
                add(s + 3.5, 0.3, target if changes else fifth, 86 if changes else 70)
                prev = target if changes else fifth
            else:                                                             # a short chord, or another meter
                add(s, min(0.7, d - GAP), p0, accent)
                last = p0
                if d >= 1.5 - 1e-9:
                    add(s + 0.75, 0.15, p0, 42, 3)
                if d >= 3 - 1e-9 and fifth != step:
                    add(s + 1.5, 0.4, fifth, 82)
                if d >= 2 - 1e-9:
                    add(e - 0.5, 0.3, step, 80)
                    last = step
                prev = last
        elif style == "walking":
            n = int(math.floor(d + 1e-9))
            if n < 2:
                add(s, d - GAP, p0, accent)
                prev = p0
                continue
            target = _place(nxt["bass"], p0)
            approach = step_into(target, p0)
            line = [p0]
            chord_set = set(_chord_pcs(chord))
            pool = [(p, 0.0 if p % 12 in chord_set else 0.75) for p in range(lo, hi + 1)
                    if p % 12 in chord_set or p % 12 in scale_pcs]
            span = approach - p0
            arch = 0.0 if abs(span) > 3 else (3.0 if p0 + 3 <= hi else -3.0)   # a short move walks an arch
            for i in range(1, n - 1):
                frac = i / (n - 1)
                aim = p0 + span * frac + arch * math.sin(math.pi * frac)
                choices = [pc for pc in pool if pc[0] != line[-1] and pc[0] != approach] or pool
                line.append(min(choices, key=lambda pc: (abs(pc[0] - aim) + pc[1] + (1.5 if pc[0] in line else 0),
                                                         pc[0]))[0])
            line.append(approach if approach != line[-1] else (target + 1 if approach == target - 1 else target - 1))
            early = changes and e - 0.5 >= s + (n - 1) + 0.25 - 1e-9 and line[-1] != target
            for i, p in enumerate(line):
                length = (d - (n - 1)) if i == n - 1 else 1.0
                if i == n - 1 and early:
                    add(s + i, (e - 0.5) - (s + i) - GAP, p, 86, 6)
                else:
                    add(s + i, min(0.92, length - 0.02), p, accent if i == 0 else 84, 6)
            if early:                              # the next bass note steps in on the and of 4, tied over
                add(e - 0.5, 0.45, target, 96, 4, tie=e)
                prev = target
            else:
                prev = line[-1]
        elif style == "gospel" and changes and d >= 2 - 1e-9 and phrase_top(e):
            # Into a phrase top (the key drop, the turnaround) the run moves early and the next bass note is
            # anticipated, tied over: 16ths landing on the and of 4, or under a triplet ride a triplet run landing on
            # the ride's skip (the last triplet of 4).
            target = _place(nxt["bass"], p0)
            triplet = feel == "triplet"
            land = e - (1 / 3 if triplet else 0.5)
            if d >= 4 - 1e-9:
                partner = p0 + 12 if p0 + 12 <= hi else p0 - 12 if p0 - 12 >= lo else _nearest_in_range(
                    (chord["root"] + chord["tones"].get("5", 7)) % 12, p0 + 7)
                if target >= p0:
                    run = [target - 3, target - 2, target - 1] if target - 3 >= lo else [target + 3, target + 2, target + 1]
                else:
                    run = [target + 3, target + 2, target + 1] if target + 3 <= hi else [target - 3, target - 2, target - 1]
                third_beat = p0
                if run[0] == p0:
                    fifth = _nearest_in_range((chord["root"] + chord["tones"].get("5", 7)) % 12, p0 - 5)
                    third = _nearest_in_range((chord["root"] + chord["tones"].get("3", chord["tones"].get("4", 4)))
                                              % 12, p0 + 4)
                    third_beat = next((p for p in (fifth, third) if p not in (p0, partner)), partner)
                step_len = 1 / 3 if triplet else 0.25
                run_start = land - 3 * step_len
                add(s, 1.4, p0, 104)
                add(s + 1.5, 0.45, partner, 82)
                add(s + 2, min(0.7, run_start - (s + 2) - 0.04), third_beat, 92)
                if d > 4 + 1e-9 and run_start - (s + 4) >= 0.25:
                    add(s + 4, run_start - (s + 4) - GAP, p0, 88)
                for i, p in enumerate(run):                  # a chromatic run, landing early
                    add(run_start + i * step_len, step_len - 0.03, p, 78 + 6 * i, 3)
            else:
                approach = step_into(target, p0)
                add(s, (land - 0.5 if not triplet else land - 1 / 3) - s - 0.05, p0, accent)
                add(land - (0.5 if not triplet else 1 / 3), 0.45 if not triplet else 0.3, approach, 84)
            add(land, e - land - 0.05, target, 98, 4, tie=e)  # the next bass note, early and tied over
            prev = target
        elif style == "gospel" and changes and d >= 2 - 1e-9:
            # Any other change: no run, no anticipation. Bass note, its octave on the and of 2, a chord tone on 3
            # and one half step into the next bass note on 4, which lands on its 1 (room for the piano's own slides).
            target = _place(nxt["bass"], p0)
            approach = step_into(target, p0)
            if d >= 4 - 1e-9:
                partner = p0 + 12 if p0 + 12 <= hi else p0 - 12 if p0 - 12 >= lo else _nearest_in_range(
                    (chord["root"] + chord["tones"].get("5", 7)) % 12, p0 + 7)
                fifth = _nearest_in_range((chord["root"] + chord["tones"].get("5", 7)) % 12, p0 - 5)
                third_beat = next((p for p in (p0, fifth) if p not in (partner, approach)), fifth)
                add(s, 1.4, p0, 104)
                add(s + 1.5, 0.45, partner, 82)
                add(s + 2, 0.9, third_beat, 92)
                if d > 4 + 1e-9:
                    add(s + 3, e - 1 - (s + 3) - GAP, p0, 88)
                add(e - 1, 0.9, approach, 84)
            else:
                add(s, d - 1.05, p0, accent)
                add(e - 1, 0.9, approach, 84)
            prev = approach
        elif style == "gospel":
            target = _place(nxt["bass"], p0)
            if d >= 4 - 1e-9:
                partner = p0 + 12 if p0 + 12 <= hi else p0 - 12 if p0 - 12 >= lo else _nearest_in_range(
                    (chord["root"] + chord["tones"].get("5", 7)) % 12, p0 + 7)
                if target >= p0:
                    run = [target - 3, target - 2, target - 1] if target - 3 >= lo else [target + 3, target + 2, target + 1]
                else:
                    run = [target + 3, target + 2, target + 1] if target + 3 <= hi else [target - 3, target - 2, target - 1]
                third_beat = p0
                if run[0] == p0:            # a minor-third walk starts on the root: sound another chord tone on 3
                    fifth = _nearest_in_range((chord["root"] + chord["tones"].get("5", 7)) % 12, p0 - 5)
                    third = _nearest_in_range((chord["root"] + chord["tones"].get("3", chord["tones"].get("4", 4)))
                                              % 12, p0 + 4)
                    third_beat = next((p for p in (fifth, third) if p not in (p0, partner)), partner)
                add(s, 1.4, p0, 104)
                add(s + 1.5, 0.45, partner, 82)
                add(s + 2, 0.9, third_beat, 92)
                for i, p in enumerate(run):
                    add(s + 3 + i / 3, 0.3, p, 78 + 6 * i, 3)
                if d > 4 + 1e-9:
                    add(s + 4, d - 4 - GAP, p0, 88)
                prev = run[-1]
            elif d >= 2 - 1e-9:
                approach = target - 1 if target >= p0 and target - 1 >= lo else target + 1
                add(s, d - 0.55, p0, accent)
                add(s + d - 0.5, 0.45, approach, 84)
                prev = approach
            else:
                add(s, d - GAP, p0, accent)
                prev = p0
        else:
            raise BandError(f"unknown bass style {style!r}; one of {', '.join(BASS_STYLES)}")
    return _tie_anticipations(notes), prev


def _tile(notes: List[Dict], cycle_len: float, total: float, human: Humanizer) -> List[Dict]:
    """Repeat one pass of a line to fill the loop, cutting the last pass at `total`; repeats get a light new
    velocity shading (drawn from the repeat's own bars) so the copies do not sound stamped."""
    out = []
    for k in range(int(math.ceil(total / cycle_len - 1e-9))):
        for n in notes:
            beat = n["beat"] + k * cycle_len
            if beat < total - 1e-9:
                vel = n["vel"] if k == 0 else human.vel(beat, n["vel"], 2)
                out.append({"beat": beat, "len": min(n["len"], total - beat), "note": n["note"], "vel": vel})
    return normalize_notes(out, total)


def _swing16(position: float, amount: float) -> float:
    """A 16th-note position pushed late on its offbeat (position = k * 0.25 beats; amount 0.5 is straight)."""
    k = round(position / 0.25)
    return position + ((amount - 0.5) * 0.5 if k % 2 else 0.0)


def swing_amount(drums: str, bpb: float, swing: Optional[float]) -> float:
    """The 16th swing drum_lane plays for this style and meter (0.5 = straight): only neo-soul in 4/4 swings its
    hats and ghost snares (NEO_SOUL_SWING unless --swing says otherwise)."""
    if drums != "neo-soul" or bpb != 4:
        return 0.5
    return NEO_SOUL_SWING if swing is None else swing


def _swung_onset(beat: float, amount: float, bpb: float) -> float:
    """A beat on an odd 16th moved late exactly as drum_lane moves the hat on it (bar start + _swing16 of the place
    in the bar), so the two share a tick; every other beat (8ths, triplets) stays where it is."""
    k = beat * 4
    if amount == 0.5 or abs(k - round(k)) > 1e-6 or round(k) % 2 == 0:
        return beat
    bar = math.floor(beat / bpb + 1e-9) * bpb
    return bar + _swing16(beat - bar, amount)


def _swing_warp(beat: float, amount: float) -> float:
    """The swing as a time map: 8ths stay, the 16th between two 8ths moves late by the swing, and the time between
    stretches or squeezes to fit. Never earlier than the beat, and order-keeping, so a swung note's end is placed
    without running into the next note."""
    d = (amount - 0.5) * 0.5
    base = math.floor(beat * 2 + 1e-9) / 2
    x = beat - base
    if x <= 0.25:
        return base + x * (0.25 + d) / 0.25
    return base + 0.25 + d + (x - 0.25) * (0.25 - d) / 0.25


def _swing_notes(notes: List[Dict], amount: float, bpb: float) -> List[Dict]:
    """Bass, comp or pad notes in the drums' swing: a note starting on an odd 16th starts with the hat there, and
    its end follows the swing's time map, never past where the next onset of the lane now starts."""
    if amount == 0.5 or not notes:
        return notes
    onsets = sorted({q(n["beat"]) for n in notes})
    moved = {b: _swung_onset(b, amount, bpb) for b in onsets}
    out = []
    for n in notes:
        b = q(n["beat"])
        nb = moved[b]
        if nb == b:
            out.append(dict(n))
            continue
        end = b + n["len"]
        ne = _swing_warp(end, amount)
        i = onsets.index(b) + 1
        if i < len(onsets) and end <= onsets[i] + 1e-9:
            ne = min(ne, moved[onsets[i]] - (onsets[i] - end))
        out.append({**n, "beat": nb, "len": max(MIN_LEN, ne - nb)})
    return out


def drum_lane(style: str, bpb: float, total: float, human: Humanizer, swing: Optional[float] = None,
              fill: bool = False) -> List[Dict]:
    if style == "none":
        return []
    if style not in DRUM_STYLES:
        raise BandError(f"unknown drum style {style!r}; one of {', '.join(DRUM_STYLES)}")
    notes: List[Dict] = []
    bars = int(round(total / bpb))
    swing = NEO_SOUL_SWING if (swing is None and style == "neo-soul") else (0.5 if swing is None else swing)
    soft = style in ("ballad", "brushes", "ambient")

    def add(beat, note, vel, length=0.1, spread=4):
        notes.append({"beat": beat, "len": length, "note": note, "vel": human.vel(beat, vel, spread)})

    phrase = min(4, bars)
    for bar in range(bars):
        b = bar * bpb
        if style == "ambient":
            if bar % 2 == 0:
                add(b, KICK, 72, 0.5)
            if bar % 4 == 1:
                add(b + min(2.5, bpb - 0.5), STICK, 46)
            if bar % phrase == 0:
                add(b, CRASH, 76, min(3.5, bpb * phrase - 0.5), 3)
            if bar % phrase == phrase - 1 or bar == bars - 1:
                start = max(0.0, bpb - 2)
                steps = int(round((bpb - start) / 0.25))
                for i in range(steps):
                    add(b + start + i * 0.25, RIDE, 18 + (88 - 18) * i / max(1, steps - 1), 0.1, 2)
            continue
        if bpb != 4:
            scale = 0.75 if soft else 1.0
            add(b, KICK, 100 * scale)
            if bpb >= 2:
                add(b + math.floor(bpb / 2), STICK if style == "ballad" else SNARE, 96 * scale)
            t = 0.0
            while t < bpb - 1e-9:
                add(b + t, RIDE if style == "brushes" else HAT, (70 if abs(t - round(t)) < 1e-9 else 46) * scale)
                t += 0.5
            continue
        if style == "ballad":
            add(b, KICK, 96)
            add(b + 2, STICK, 86)
            for i in range(8):
                add(b + i * 0.5, HAT, 60 if i % 2 == 0 else 38)
        elif style == "neo-soul":
            add(b, KICK, 102)
            add(b + 1.75, KICK, 72)
            add(b + 2.5, KICK, 88)
            add(b + 1 + LAY_BACK, SNARE, 104)
            add(b + 3 + LAY_BACK, SNARE, 106)
            add(b + _swing16(2.75, swing), SNARE, 32, 0.08, 3)
            add(b + _swing16(3.75, swing), SNARE, 28, 0.08, 3)
            accents = (80, 34, 56, 36)
            for i in range(16):
                if i == 14:
                    add(b + 3.5, OPEN_HAT, 62, 0.2)
                    continue
                add(b + _swing16(i * 0.25, swing), HAT, accents[i % 4], 0.08, 5)
        elif style == "halftime":
            add(b, KICK, 104)
            add(b + 2.5, KICK, 84)
            if bar % 2 == 1:
                add(b + 3.75, KICK, 64)
            add(b + 2, SNARE, 110)
            for i in range(8):
                add(b + i * 0.5, HAT, 72 if i % 2 == 0 else 44)
        elif style == "four-on-floor":
            for i in range(4):
                add(b + i, KICK, 110 if i == 0 else 102)
                add(b + i, HAT, 44, 0.1, 3)                  # a soft closed hat on the beat closes the open one
                add(b + i + 0.5, OPEN_HAT, 80, 0.4)
            add(b + 1, SNARE, 100)
            add(b + 3, SNARE, 100)
        elif style == "brushes":
            for t, v in ((0, 70), (1, 78), (1 + 2 / 3, 52), (2, 70), (3, 78), (3 + 2 / 3, 52)):
                add(b + t, RIDE, v, 0.2)
            add(b + 1, PEDAL, 58)
            add(b + 3, PEDAL, 58)
            add(b + 1, SNARE, 40, 0.1, 3)
            add(b + 3, SNARE, 42, 0.1, 3)
            add(b, KICK, 44, 0.1, 3)
            add(b + 2, KICK, 38, 0.1, 3)

    if fill and style != "ambient" and bpb == 4 and bars >= 1:
        last = total - bpb
        notes = [n for n in notes if n["beat"] < last + 2 - 1e-9]
        scale = 0.7 if soft else 1.0
        for i, v in enumerate((58, 66, 74, 84)):
            add(last + 2 + i * 0.25, SNARE, v * scale)
        for i, (tom, v) in enumerate(((TOM_HI, 92), (TOM_HI_MID, 96), (TOM_LOW, 102), (TOM_FLOOR_LOW, 110))):
            add(last + 3 + i * 0.25, tom, v * scale)
        add(last + 3.75, KICK, 90 * scale)
        notes = [n for n in notes if not (n["beat"] == 0 and n["note"] in (HAT, RIDE))]
        add(0, CRASH, 104 * scale, 1.5)
    return normalize_notes(notes, total)


# Lowest clear note per interval (pianocue_voicing.mjs's table, widened for a band under a pianist: seconds and
# thirds sit higher). A minor second below MUD_FLOOR is refused outright, not just penalised.
LIL = {1: 55, 2: 53, 3: 50, 4: 48, 5: 45, 6: 46, 7: 34}
MUD_FLOOR = 55               # G3: no minor second is stacked with its lower note under this
KEYS_SHAPE = {"comp": {"size": 4, "center": 60.0, "max_span": 14, "ideal_span": 10},
              "pad": {"size": 5, "center": 58.0, "max_span": 19, "ideal_span": 14},
              "shell": {"size": 2, "center": 55.5, "max_span": 11, "ideal_span": 8, "range": SHELL_RANGE}}
SEAM_CANDIDATES = 12         # voicings kept per chord for the ring search

# Comp rhythms by drum style: bar variants (A, B, ...) of (beat in the bar, length, velocity, voices); voices 0 is
# the whole voicing, 2 its top two notes; a negative beat is a push that early before the bar (or chord) starts.
COMP_RHYTHMS = {
    "none": [[(0, 1.75, 74, 0), (2.5, 1.25, 62, 0)]],
    "ballad": [[(0, 2.9, 66, 0), (3, 0.9, 50, 2)]],
    "neo-soul": [[(-0.25, 1.5, 74, 0), (2.75, 0.75, 64, 0)],
                 [(-0.25, 0.75, 72, 0), (1.5, 0.45, 58, 0)]],
    "halftime": [[(0, 1.4, 72, 0), (2, 0.45, 76, 0)],
                 [(0, 1.4, 70, 0), (2, 0.45, 74, 0), (3.5, 0.4, 56, 2)]],
    "four-on-floor": [[(0, 0.6, 76, 0), (1.5, 0.6, 70, 0), (3, 0.45, 66, 0)]],
    "brushes": [[(0, 0.9, 70, 0), (1.5, 0.45, 60, 0)]],
    "ambient": [[(0, 3.9, 56, 0)]],
}


def voicing_pcs(chord: Dict, size: int) -> List[int]:
    """The pitch classes a keys voicing uses, most important first: the 3rd (or sus tone) and the 7th (or 6th),
    an altered 5th, colour tones (b9 #9 13 b13 #11 11 9), the 5th, then the root only when fewer than four other
    tones exist. A slash chord's bass is not doubled when three other tones remain."""
    tones, root = chord["tones"], chord["root"]
    order = [r for r in ("3", "4", "2", "7", "6") if r in tones]
    if "5" in tones and tones["5"] != 7:
        order.append("5")
    order += [r for r in ("b9", "#9", "13", "b13", "#11", "11", "9") if r in tones]
    if "5" in tones and "5" not in order:
        order.append("5")
    pcs: List[int] = []
    for r in order:
        pc = (root + tones[r]) % 12
        if pc not in pcs and pc != root % 12:
            pcs.append(pc)
    if chord["bass"] != root:
        without = [p for p in pcs if p != chord["bass"]]
        if len(without) >= 3:
            pcs = without
    if (len(pcs) < 4 and "b9" not in tones) or len(pcs) < 2:
        pcs.append(root % 12)
    return pcs[:size]


def is_muddy(v: Sequence[int]) -> bool:
    """A minor second stacked with its lower note below G3 (MUD_FLOOR): refused in every keys voicing."""
    return any(b - a == 1 and a < MUD_FLOOR for a, b in zip(v, v[1:]))


def _roughness(v: Sequence[int], chord: Dict) -> float:
    pen = 0.0
    for a, b in zip(v, v[1:]):
        iv = b - a
        if iv in LIL and a < LIL[iv]:
            pen += 8.0
        if iv == 1:
            pen += 1.5
    if "b9" not in chord["tones"]:
        pen += 3.0 * sum(1 for a, b in itertools.combinations(v, 2) if b - a == 13)
    return pen


def _movement(prev: Sequence[int], cur: Sequence[int]) -> float:
    if len(prev) == len(cur):
        return float(sum(abs(a - b) for a, b in zip(prev, cur)))
    there = sum(min(abs(c - p) for p in prev) for c in cur)
    back = sum(min(abs(p - c) for c in cur) for p in prev)
    return (there + back) / 2.0


def _voicing_candidates(chord: Dict, shape: Dict) -> List[Tuple[float, List[int]]]:
    """(standing cost, voicing) for one chord, cheapest first: roughness, spacing and the pull to the lane's centre.
    Muddy voicings are refused unless nothing else fits the span."""
    lo, hi = shape.get("range", KEYS_RANGE)
    pcs = voicing_pcs(chord, shape["size"])
    options = [[p for p in range(lo, hi + 1) if p % 12 == pc] for pc in pcs]
    clear, muddy = [], []
    for combo in itertools.product(*options):
        v = sorted(combo)
        span = v[-1] - v[0]
        if span > shape["max_span"]:
            continue
        mean = sum(v) / len(v)
        cost = (_roughness(v, chord) + 0.3 * abs(span - shape["ideal_span"]) * (len(v) > 2)
                + 0.6 * abs(mean - shape["center"]))
        (muddy if is_muddy(v) else clear).append((round(cost, 6), v))
    found = sorted(clear or muddy)
    if not found:                                          # the span limit refused everything: stack upward
        v, floor = [], lo
        for pc in pcs:
            p = floor + (pc - floor) % 12
            v.append(p if p <= hi else p - 12)
            floor = p
        return [(0.0, sorted(v))]
    return found[:SEAM_CANDIDATES]


def _lead_cost(a: Sequence[int], b: Sequence[int]) -> float:
    return _movement(a, b) + 0.3 * abs(b[-1] - a[-1])


def voice_lead(chords: List[Dict], lane: str, ring: bool = True) -> List[List[int]]:
    """Voicings in C3..B4 (a "shell": C3..E4) for a chord sequence with the least total movement between neighbours
    (top voice weighted a little extra), plus a pull toward the lane's register centre, even spacing and no muddy
    low intervals. lane is a KEYS_SHAPE name: comp, pad or shell. ring=True counts the move from the last chord back
    to the first, as a looping pattern plays it, so the seam is voice-led like every other change."""
    if not chords:
        return []
    shape = KEYS_SHAPE[lane]
    cands = [_voicing_candidates(chord, shape) for chord in chords]
    n = len(cands)
    if n == 1:
        return [cands[0][0][1]]
    edges = [[[_lead_cost(a, b) for _, b in cands[i + 1]] for _, a in cands[i]] for i in range(n - 1)]
    seam = [[_lead_cost(a, b) for _, b in cands[0]] for _, a in cands[-1]] if ring else None
    best = None
    for j0, (c0, _) in enumerate(cands[0]):
        cost = [c0 + edges[0][j0][j] + cands[1][j][0] for j in range(len(cands[1]))]
        back: List[List[int]] = [[j0] * len(cands[1])]
        for i in range(1, n - 1):
            nxt_cost, nxt_back = [], []
            for k in range(len(cands[i + 1])):
                j = min(range(len(cands[i])), key=lambda j: (cost[j] + edges[i][j][k], j))
                nxt_cost.append(cost[j] + edges[i][j][k] + cands[i + 1][k][0])
                nxt_back.append(j)
            cost, back = nxt_cost, back + [nxt_back]
        for k in range(len(cands[-1])):
            total = cost[k] + (seam[k][j0] if ring else 0.0)
            path = [k]
            for i in range(n - 2, -1, -1):
                path.append(back[i][path[-1]])
            path.reverse()
            key = (round(total, 6), [cands[i][p][1] for i, p in enumerate(path)])
            if best is None or key < best:
                best = key
    return best[1]


def _comp_strikes(timeline: List[Dict], style: str, bpb: float, total: float, swing: float = 0.5) -> List[List]:
    """[beat, length, velocity, voices, cycle index] for the comp lane in the drum style's rhythm (COMP_RHYTHMS),
    strikes on odd 16ths moved late with the drums' swing."""
    strikes: List[List] = []
    for s, e, c, _ in _segments(timeline, bpb, total):
        d = e - s
        i = c["cycle_index"]
        if bpb != 4 or style not in COMP_RHYTHMS:
            strikes.append([s, min(1.75, d - GAP), 74, 0, i])
            if d >= 4 - 1e-9:
                strikes.append([s + 2.5, min(1.25, d - 2.5 - GAP), 62, 0, i])
            continue
        bar = int(math.floor(s / bpb + 1e-9))
        variant = COMP_RHYTHMS[style][bar % len(COMP_RHYTHMS[style])]
        start = bar * bpb
        hits = []
        for off, ln, vel, voices in variant:
            at = q(start + max(0.0, off))
            if s - 1e-9 <= at < e - 1e-9:
                hits.append([at, ln, vel, voices, off < 0])
        if not hits or abs(hits[0][0] - s) > 1e-9:            # a change off the rhythm is still struck
            off, ln, vel, _ = variant[0]
            hits = [[s, ln, vel, 0, off < 0]] + [h for h in hits if h[0] - s >= 0.75 - 1e-9]
        for at, ln, vel, voices, push in hits:
            if push and at > 1e-9:
                at = q(at + variant[0][0])
            strikes.append([at, min(ln, e - at - GAP if not push else ln), vel, voices, i])
    for st in strikes:                                        # in the pocket with the swung hats, not a flam ahead
        swung = _swung_onset(st[0], swing, bpb)
        if swung != st[0]:
            st[0], st[1] = swung, _swing_warp(st[0] + st[1], swing) - swung
    strikes.sort(key=lambda x: x[0])
    for k, st in enumerate(strikes):                          # every strike ends before the next one
        limit = (strikes[k + 1][0] - st[0] - 0.02) if k + 1 < len(strikes) else (total - st[0] - GAP)
        st[1] = min(st[1], limit)
    return [st for st in strikes if st[1] >= MIN_LEN - 1e-9]


def keys_lane(timeline: List[Dict], cycle: List[Dict], lane: str, bpb: float, total: float,
              human: Humanizer, style: str = "none", swing: float = 0.5, shell: bool = False) -> List[Dict]:
    """The comp (rhythm by drum style) or pad (held chords) lane. Voicings are led around the part of the chord
    loop the pattern plays, as a ring; shell=True voices the comp as two-note shells (KEYS_SHAPE["shell"]). Onsets
    on odd 16ths follow the drums' swing."""
    played = max(c["cycle_index"] for c in timeline) + 1
    voicings = voice_lead(cycle[:played], "shell" if shell and lane == "comp" else lane)
    notes: List[Dict] = []

    def strike(beat, length, voicing, vel):
        for p in voicing:
            notes.append({"beat": beat, "len": length, "note": p, "vel": human.vel(beat, vel, 3)})

    if lane == "pad":
        for c in timeline:
            strike(c["beat"], c["dur"] - GAP, voicings[c["cycle_index"]], 62)
        notes = _swing_notes(notes, swing, bpb)
    else:
        for at, length, vel, voices, i in _comp_strikes(timeline, style, bpb, total, swing):
            v = voicings[i]
            strike(at, length, v[-voices:] if voices and len(v) > voices else v, vel)
    return normalize_notes(notes, total)


PHRASE_WEIGHT = (0.5, 0.75, 0.5, 2.25)  # arsenal/fl/vfx/arsenal_band.py PHRASE_WEIGHT: bar 4 of a phrase rests most


def dropout_bars(seed_id: str, bars: int, amount: float) -> List[int]:
    """The 0-based bars that rest under --dropout `amount`: never bar 0, never two in a row, each decided by
    random.Random("<id>/dropout/<bar>") so the holes are the same every time the set is built. As in the VFX band, a
    rest leans on the last bar of each 4-bar phrase (bars 4, 8, ... counted from 1), then the 2nd: a bar's chance is
    1 - (1 - amount) ** PHRASE_WEIGHT[bar % 4], so 0 still means none and 1 every other bar."""
    if not 0 <= amount <= 1:
        raise BandError("--dropout runs from 0 (no rest bars) to 1 (every other bar rests)")
    out: List[int] = []
    for bar in range(1, int(bars)):
        if out and out[-1] == bar - 1:
            continue
        chance = 1 - (1 - amount) ** PHRASE_WEIGHT[bar % 4]
        if amount > 0 and random.Random(f"{seed_id}/dropout/{bar}").random() < chance:
            out.append(bar)
    return out


def _rest_bars(notes: List[Dict], rests: Sequence[int], bpb: float, total: float, sustain: bool) -> List[Dict]:
    """Silence whole bars in a lane, as the VFX band's Dropout does. A note that starts in a bar's last 8th and
    rings over its bar line is a push and belongs to the next bar: a push into a rest bar rests, a push out of one
    plays whole. Any other note sounding into a rest bar is cut at its bar line. With sustain (comp, pad) the part
    of a silenced note that would ring past its rest bar is struck again on the bar after."""
    rest = set(rests)
    bars = max(1, int(round(total / bpb)))
    out = []
    for n in notes:
        start, end = q(n["beat"]), q(n["beat"] + n["len"])
        bar = int(math.floor(start / bpb + 1e-9))
        line = q((bar + 1) * bpb)
        push = line - start <= 0.5 + 1e-9 and end > line + 1e-9
        owner = (bar + 1) % bars if push else bar
        if owner in rest:                                    # it belongs to a rest bar: only what rings past it
            after = q((bar + 2 if push else bar + 1) * bpb)
            pieces = [(after, end)] if sustain and end > after + 1e-9 else []
        else:
            pieces = [(start, end)]
        for r in sorted(rest):
            bs, be = q(r * bpb), q((r + 1) * bpb)
            kept = []
            for s, e in pieces:
                if e <= bs + 1e-9 or s >= be - 1e-9 or (push and s == start and r == bar):
                    kept.append((s, e))                      # clear of this rest bar, or a push out of it
                    continue
                if s < bs - 1e-9:
                    kept.append((s, bs))
                if sustain and e > be + 1e-9:
                    kept.append((be, e))
            pieces = kept
        out += [{**n, "beat": s, "len": q(e - s)} for s, e in pieces]
    return normalize_notes(out, total)


# ================================================================================================= pattern sets
def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower().replace("#", "sharp")).strip("-")
    return (s or "pattern")[:64].strip("-")


def make_pattern_set(loop: str, key: Optional[str] = None, bpm: Optional[float] = None, bars: Optional[int] = None,
                     bass: str = "roots-on-1", drums: str = "ballad", comp: bool = False, pad: bool = False,
                     fill: bool = False, swing: Optional[float] = None, meter="4/4", title: Optional[str] = None,
                     pid: Optional[str] = None, dropout: float = 0.0, shell: bool = False) -> Dict:
    """Generate a pattern set (the contract above) from a chord loop. Deterministic: the same arguments give the
    same set, humanised velocities (seeded per id, bar and lane) and dropout bars included. shell=True voices the
    comp as two-note shells below E4."""
    if bass not in BASS_STYLES:
        raise BandError(f"unknown bass style {bass!r}; one of {', '.join(BASS_STYLES)}")
    if drums not in DRUM_STYLES:
        raise BandError(f"unknown drum style {drums!r}; one of {', '.join(DRUM_STYLES)}")
    if swing is not None and not 0.5 <= swing <= 0.75:
        raise BandError("--swing runs from 0.5 (straight) to 0.75 (a dotted feel)")
    if not (isinstance(dropout, (int, float)) and 0 <= dropout <= 1):
        raise BandError("--dropout runs from 0 (no rest bars) to 1 (every other bar rests)")
    meter = parse_meter(meter)
    bpb = beats_per_bar(meter)
    key_name = _key_info(key)["name"] if key else None
    cycle = parse_loop(loop, key_name, meter)
    if key_name is None:
        key_name = estimate_key(cycle)
    cycle_bars = int(round((cycle[-1]["beat"] + cycle[-1]["dur"]) / bpb))
    bars = cycle_bars if bars is None else int(bars)
    if not 1 <= bars <= MAX_BARS:
        raise BandError(f"--bars runs from 1 to {MAX_BARS}")
    total = q(bars * bpb)
    bpm = float(BPM_BY_DRUMS[drums] if bpm is None else bpm)
    if not 20 <= bpm <= 300:
        raise BandError("--bpm runs from 20 to 300")
    tonic_name = key_name.split()[0]
    title = title or f"{key_name} {drums}, {bass} bass"
    pid = pid or slug(title)
    if not ID_RE.match(pid):
        raise BandError(f"an id is lowercase letters, digits and dashes (at most 64), not {pid!r}")

    timeline = _expand(cycle, total)
    k = nv.parse_key(key_name)
    scale = [(k["tonic"] + i) % 12 for i in (nv.LETTER_PC if k["mode"] == "major" else nv.MINOR_SCALE)]
    cycle_len = q(cycle[-1]["beat"] + cycle[-1]["dur"])
    bass_human = Humanizer(pid, "bass", bpb)
    feel = "triplet" if drums == "brushes" else "straight"
    swung = swing_amount(drums, bpb, swing)                # bass, comp and pad sit in the drums' swing
    if bass != "pedal" and total > cycle_len + 1e-9:       # one voice-led pass of the chord loop, repeated
        once = bass_lane(_expand(cycle, cycle_len), bass, bpb, cycle_len, bass_human, k["tonic"], scale, feel)
        bass_notes = _tile(once, cycle_len, total, bass_human)
    else:
        bass_notes = bass_lane(timeline, bass, bpb, total, bass_human, k["tonic"], scale, feel)
    lanes = {
        "bass": normalize_notes(_swing_notes(bass_notes, swung, bpb), total),
        "drums": drum_lane(drums, bpb, total, Humanizer(pid, "drums", bpb), swing=swing, fill=fill),
        "comp": keys_lane(timeline, cycle, "comp", bpb, total, Humanizer(pid, "comp", bpb), drums, swung, shell)
        if comp else [],
        "pad": keys_lane(timeline, cycle, "pad", bpb, total, Humanizer(pid, "pad", bpb), swing=swung) if pad else [],
    }
    rests = dropout_bars(pid, bars, dropout)
    if rests:                                              # the bass plays on through every rest bar
        lanes["drums"] = _rest_bars(lanes["drums"], rests, bpb, total, sustain=False)
        lanes["comp"] = _rest_bars(lanes["comp"], rests, bpb, total, sustain=True)
        lanes["pad"] = _rest_bars(lanes["pad"], rests, bpb, total, sustain=True)
    chords = []
    for c in timeline:
        number = nv.nashville_from_name(c["name"], key_name)
        chords.append({"beat": _num(c["beat"]), "name": c["name"], "nns": number["text"] if number else ""})
    return {"version": VERSION, "id": pid, "title": title, "key": key_name,
            "bpm_hint": int(bpm) if bpm == int(bpm) else round(bpm, 3), "meter": list(meter), "length_beats": _num(total), "chords": chords,
            "lanes": {lane: {"notes": lanes[lane]} for lane in LANES}}


def validate_pattern_set(ps) -> Dict:
    """Check a pattern set against the contract; raise BandError listing every problem."""
    problems: List[str] = []
    if not isinstance(ps, dict):
        raise BandError("a pattern set is a JSON object")
    if ps.get("version") != VERSION:
        problems.append(f"version must be {VERSION}")
    if not (isinstance(ps.get("id"), str) and ID_RE.match(ps["id"])):
        problems.append("id must be lowercase letters, digits and dashes")
    for field in ("title", "key"):
        if not isinstance(ps.get(field), str):
            problems.append(f"{field} must be a string")
    bpm = ps.get("bpm_hint")
    if not (isinstance(bpm, (int, float)) and not isinstance(bpm, bool) and bpm > 0):
        problems.append("bpm_hint must be a number above 0")
    try:
        meter = parse_meter(ps.get("meter"))
    except (BandError, TypeError, ValueError):
        problems.append("meter must be [beats, 2|4|8|16]")
        meter = None
    length = ps.get("length_beats")
    if not (isinstance(length, (int, float)) and not isinstance(length, bool) and length > 0):
        problems.append("length_beats must be a number above 0")
        length = None
    elif meter and not is_whole_bars(length, meter):
        problems.append(f"length_beats {length} is not whole bars of {beats_per_bar(meter):g}")
    chords = ps.get("chords")
    if not isinstance(chords, list):
        problems.append("chords must be a list")
    else:
        for i, c in enumerate(chords):
            if not (isinstance(c, dict) and isinstance(c.get("name"), str) and isinstance(c.get("nns"), str)
                    and isinstance(c.get("beat"), (int, float)) and not isinstance(c.get("beat"), bool)):
                problems.append(f"chords[{i}] needs beat, name and nns")
            elif length is not None and not 0 <= c["beat"] < length:
                problems.append(f"chords[{i}] beat {c['beat']} is outside the loop")
    lanes = ps.get("lanes")
    if not isinstance(lanes, dict):
        problems.append("lanes must be an object")
    else:
        for lane in lanes:
            if lane not in LANES:
                problems.append(f"unknown lane {lane!r}")
        for lane in LANES:
            body = lanes.get(lane)
            if not (isinstance(body, dict) and isinstance(body.get("notes"), list)):
                problems.append(f"lanes.{lane}.notes must be a list")
                continue
            for i, n in enumerate(body["notes"]):
                where = f"lanes.{lane}.notes[{i}]"
                if not isinstance(n, dict):
                    problems.append(f"{where} must be an object")
                    continue
                vals = [n.get(k) for k in ("beat", "len", "note", "vel")]
                if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in vals):
                    problems.append(f"{where} needs numeric beat, len, note and vel")
                    continue
                beat, ln, note, vel = vals
                if not (isinstance(note, int) and 0 <= note <= 127):
                    problems.append(f"{where} note must be an integer 0..127")
                if not (isinstance(vel, int) and 1 <= vel <= 127):
                    problems.append(f"{where} vel must be an integer 1..127")
                if ln <= 0:
                    problems.append(f"{where} len must be above 0")
                if length is not None and not (0 <= beat < length and beat + ln <= length + 1e-6):
                    problems.append(f"{where} does not fit inside the {length}-beat loop")
    if problems:
        raise BandError("; ".join(problems))
    return ps


def lint(ps: Dict) -> List[str]:
    """Register and overlap warnings (the generator never produces them; hand-edited sets might)."""
    out = []
    ranges = {"bass": BASS_RANGE, "comp": KEYS_RANGE, "pad": KEYS_RANGE}
    for lane, (lo, hi) in ranges.items():
        bad = sorted({n["note"] for n in ps["lanes"][lane]["notes"] if not lo <= n["note"] <= hi})
        if bad:
            out.append(f"{lane}: notes outside {midi_name(lo)}..{midi_name(hi)}: {bad}")
    for lane in LANES:
        ends: Dict[int, float] = {}
        for n in sorted(ps["lanes"][lane]["notes"], key=lambda n: (n["beat"], n["note"])):
            if ends.get(n["note"], -1) > n["beat"] + 1e-9:
                out.append(f"{lane}: note {n['note']} overlaps itself at beat {n['beat']}")
            ends[n["note"]] = n["beat"] + n["len"]
    return out


# ================================================================================================= seeds
SEEDS = (
    {"id": "db-ballad-lift", "title": "Db ballad lift", "loop": "4maj9 - 6m11 - 5^11/4 - 1add9", "key": "Db major",
     "bpm": 66, "bars": 8, "bass": "roots-on-1", "drums": "ballad", "pad": True, "fill": True,
     "why": "the 4 opens wide, the 6m11 sighs, and the 5 over the 4 bass hangs like a question before the add9 home"},
    {"id": "eb-neosoul-pocket", "title": "Eb neo-soul pocket", "loop": "1maj9 - 4maj9#11 - 6m11 - 5sus",
     "key": "Eb major", "bpm": 84, "bars": 8, "bass": "pocket", "drums": "neo-soul", "comp": True,
     "why": "Lydian #11 shimmer on the 4, a pocket bass with holes to play into, the 5sus never quite resolving"},
    {"id": "d-halftime-sunrise", "title": "D halftime sunrise", "loop": "1add9 - 5/7 - 6m9 - 4maj9", "key": "D major",
     "bpm": 72, "bars": 8, "bass": "root-fifth", "drums": "halftime", "pad": True, "fill": True,
     "why": "the 5/7 walks the bass down D-C#-B, then the 4maj9 opens the sky: a worship halftime with room on top"},
    {"id": "f-to-d-drop", "title": "F to D minor-third drop",
     "loop": "Fmaj9 | Dm9 | Bbmaj9 | C13sus4 | Dmaj9 | Bm11 | Gmaj9#11 | A13sus4 C13sus4", "key": "F major",
     "bpm": 76, "bars": 8, "bass": "gospel", "drums": "brushes", "comp": True, "shell": True,
     "why": "four bars in F, then the floor drops a minor third to D; C13sus4 in the last bar lifts it back home"},
    {"id": "bbm-lament", "title": "Bbm lament", "loop": "1m11 | 1m9/b7 | b6maj9#11 | 5^7sus4 5^7b9",
     "key": "Bb minor", "bpm": 60, "bars": 8, "bass": "roots-on-1", "drums": "ambient", "pad": True,
     "why": "the lament bass Bb-Ab-Gb-F under a Bbm11 that never lets go; the F7b9 pulls straight back into the minor"},
    {"id": "gb-real-v7", "title": "Gb gospel house, a real V7", "loop": "1maj9 - 6m9 - 2m9 - 5^7", "key": "Gb major",
     "bpm": 118, "bars": 8, "bass": "offbeat", "drums": "four-on-floor", "comp": True,
     "why": "three lush minor-nine colours, then a plain Db7 with its F and Cb: the tritone's tension, sounded, not hinted"},
)


def seed(seed_id: str) -> Dict:
    for s in SEEDS:
        if s["id"] == seed_id:
            return make_pattern_set(s["loop"], key=s["key"], bpm=s["bpm"], bars=s["bars"], bass=s["bass"],
                                    drums=s["drums"], comp=s.get("comp", False), pad=s.get("pad", False),
                                    fill=s.get("fill", False), title=s["title"], pid=s["id"],
                                    dropout=s.get("dropout", 0.0), shell=s.get("shell", False))
    raise KeyError(seed_id)


# ================================================================================================= store + playlist
def state_root(arg: Optional[str] = None) -> Path:
    return Path(arg or os.environ.get(STATE_ENV) or DEFAULT_STATE)


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def dump_json(ps: Dict) -> str:
    """Pattern-set JSON with one note per line (readable diffs, small files)."""
    head = {k: v for k, v in ps.items() if k not in ("chords", "lanes")}
    lines = ["{"]
    for k, v in head.items():
        lines.append(f"  {json.dumps(k)}: {json.dumps(v)},")
    lines.append('  "chords": [')
    lines += [f"    {json.dumps(c)}{',' if i < len(ps['chords']) - 1 else ''}" for i, c in enumerate(ps["chords"])]
    lines.append("  ],")
    lines.append('  "lanes": {')
    for li, lane in enumerate(LANES):
        notes = ps["lanes"][lane]["notes"]
        if not notes:
            lines.append(f'    {json.dumps(lane)}: {{"notes": []}}{"," if li < len(LANES) - 1 else ""}')
            continue
        lines.append(f'    {json.dumps(lane)}: {{"notes": [')
        lines += [f"      {json.dumps(n)}{',' if i < len(notes) - 1 else ''}" for i, n in enumerate(notes)]
        lines.append(f'    ]}}{"," if li < len(LANES) - 1 else ""}')
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines) + "\n"


class PatternStore:
    def __init__(self, root: Optional[str] = None):
        self.root = state_root(root)
        self.patterns = self.root / "patterns"
        self.playlist_path = self.root / "playlist.json"

    def path(self, pid: str) -> Path:
        if not ID_RE.match(pid):
            raise BandError(f"not a pattern id: {pid!r}")
        return self.patterns / f"{pid}.json"

    def save(self, ps: Dict, out_dir: Optional[Path] = None) -> Path:
        """Write the set, stamped with "generator": GENERATOR_VERSION so a later band.py can tell it is out of date."""
        validate_pattern_set(ps)
        path = (Path(out_dir) / f"{ps['id']}.json") if out_dir else self.path(ps["id"])
        _write_atomic(path, dump_json({**ps, GENERATOR_KEY: GENERATOR_VERSION}))
        return path

    def stale_note(self, pid: str) -> Optional[str]:
        """A warning when the stored file for pid was written by an older generator than this band.py (a file with no
        stamp predates stamps: generator 1). None for a current file, or when nothing is stored (the seed is used)."""
        path = self.path(pid)
        if not path.is_file():
            return None
        try:
            stamp = json.loads(path.read_text(encoding="utf-8")).get(GENERATOR_KEY, 1)
        except (ValueError, AttributeError):
            return None
        if isinstance(stamp, int) and not isinstance(stamp, bool) and stamp >= GENERATOR_VERSION:
            return None
        again = ("py -m arsenal.band seeds --write" if any(s["id"] == pid for s in SEEDS)
                 else "make it again with the same arguments")
        return (f"{path} was written by generator version {stamp}, older than this band.py (version "
                f"{GENERATOR_VERSION}), so its notes may be out of date; if it came from band.py, rebuild it: {again}")

    def stored(self) -> List[str]:
        if not self.patterns.is_dir():
            return []
        return sorted(p.stem for p in self.patterns.glob("*.json") if ID_RE.match(p.stem))

    def load(self, pid: str) -> Dict:
        """A stored pattern set, or a seed of that id (a stored file wins)."""
        path = self.path(pid)
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data.pop(GENERATOR_KEY, None)
                return validate_pattern_set(data)
            except ValueError as exc:
                raise BandError(f"{path} is not a valid pattern set: {exc}")
        try:
            return seed(pid)
        except KeyError:
            raise BandError(f"no pattern set {pid!r}; try: py -m arsenal.band list")

    def exists(self, pid: str) -> bool:
        return self.path(pid).is_file() or any(s["id"] == pid for s in SEEDS)

    # ---- playlist: {"version": 1, "current": 0-based index, "items": [ids]}
    def playlist(self) -> Dict:
        if not self.playlist_path.is_file():
            return {"version": VERSION, "current": 0, "items": []}
        data = json.loads(self.playlist_path.read_text(encoding="utf-8"))
        items = [i for i in data.get("items", []) if isinstance(i, str)]
        current = data.get("current", 0)
        current = current if isinstance(current, int) and 0 <= current < max(1, len(items)) else 0
        return {"version": VERSION, "current": current, "items": items}

    def save_playlist(self, pl: Dict) -> None:
        _write_atomic(self.playlist_path, json.dumps(pl, indent=2) + "\n")

    def playlist_add(self, pid: str, at: Optional[int] = None) -> Dict:
        if not self.exists(pid):
            raise BandError(f"no pattern set {pid!r}; make it first, or try: py -m arsenal.band list")
        pl = self.playlist()
        index = len(pl["items"]) if at is None else at - 1
        if not 0 <= index <= len(pl["items"]):
            raise BandError(f"--at runs from 1 to {len(pl['items']) + 1}")
        pl["items"].insert(index, pid)
        if pl["items"] and index <= pl["current"] and len(pl["items"]) > 1:
            pl["current"] += 1
        self.save_playlist(pl)
        return pl

    def playlist_rm(self, target: str) -> Tuple[Dict, str]:
        pl = self.playlist()
        if target in pl["items"]:
            index = pl["items"].index(target)
        elif re.fullmatch(r"\d+", target) and 1 <= int(target) <= len(pl["items"]):
            index = int(target) - 1
        else:
            raise BandError(f"{target!r} is neither an id nor a position in the playlist")
        removed = pl["items"].pop(index)
        if index < pl["current"] or pl["current"] >= len(pl["items"]):
            pl["current"] = max(0, pl["current"] - 1)
        self.save_playlist(pl)
        return pl, removed

    def playlist_current(self, position: int) -> Dict:
        pl = self.playlist()
        if not 1 <= position <= len(pl["items"]):
            raise BandError(f"the playlist has positions 1..{len(pl['items'])}")
        pl["current"] = position - 1
        self.save_playlist(pl)
        return pl


# ================================================================================================= MIDI files
def vlq(n: int) -> bytes:
    """A MIDI variable-length quantity (0..0x0FFFFFFF)."""
    if not 0 <= n <= 0x0FFFFFFF:
        raise ValueError(f"{n} does not fit a variable-length quantity")
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def _meta(kind: int, payload: bytes) -> bytes:
    return bytes((0xFF, kind)) + vlq(len(payload)) + payload


def _track(events: List[Tuple[int, int, bytes]], end_tick: int) -> bytes:
    """events: (tick, order, message); order 0 meta, 1 note-off, 2 note-on, so a repeated pitch releases first."""
    data = bytearray()
    last = 0
    for tick, _, msg in sorted(events, key=lambda e: (e[0], e[1])):
        data += vlq(tick - last) + msg
        last = tick
    data += vlq(max(0, end_tick - last)) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def key_signature(key: str) -> Tuple[int, int]:
    """(sharps as + / flats as -, 0 major | 1 minor) for a key name."""
    k = nv.parse_key(key)
    if not k:
        return 0, 0
    rel_major = k["tonic"] if k["mode"] == "major" else (k["tonic"] + 3) % 12
    fifths = rel_major * 7 % 12
    sf = fifths if fifths < 6 else fifths - 12 if fifths > 6 else (6 if k["bias"] >= 0 else -6)
    return sf, 0 if k["mode"] == "major" else 1


def _conductor_events(ps: Dict, markers: bool) -> List[Tuple[int, int, bytes]]:
    n, d = ps["meter"]
    usec = max(1, min(0xFFFFFF, int(round(60_000_000 / float(ps["bpm_hint"])))))
    sf, mi = key_signature(ps["key"])
    ev = [(0, 0, _meta(0x51, usec.to_bytes(3, "big"))),
          (0, 0, _meta(0x58, bytes((n, int(math.log2(d)), 24, 8)))),
          (0, 0, _meta(0x59, struct.pack(">bB", sf, mi)))]
    if markers:
        for c in ps["chords"]:
            ev.append((int(round(c["beat"] * PPQ)), 0, _meta(0x06, c["name"].encode("utf-8"))))
    return ev


def _note_events(notes: List[Dict], channel: int) -> List[Tuple[int, int, bytes]]:
    ev = []
    for n in notes:
        on = int(round(n["beat"] * PPQ))
        off = max(on + 1, int(round((n["beat"] + n["len"]) * PPQ)))
        ev.append((on, 2, bytes((0x90 | channel, n["note"], n["vel"]))))
        ev.append((off, 1, bytes((0x80 | channel, n["note"], 64))))
    return ev


def midi_bytes(ps: Dict, lane: Optional[str] = None) -> bytes:
    """A Standard MIDI File, type 1 at 480 PPQ. lane=None: a conductor track (name, tempo, meter, key, chord
    markers) and one track per lane. lane="bass": one track holding the tempo, meter, key and that lane's notes."""
    end = int(round(ps["length_beats"] * PPQ))
    if lane is None:
        tracks = [_track([(0, 0, _meta(0x03, ps["title"].encode("utf-8")))] + _conductor_events(ps, True), end)]
        for name in LANES:
            ev = [(0, 0, _meta(0x03, name.encode("utf-8")))] + _note_events(ps["lanes"][name]["notes"], CHANNELS[name])
            tracks.append(_track(ev, end))
    else:
        ev = [(0, 0, _meta(0x03, f"{ps['title']} - {lane}".encode("utf-8")))] + _conductor_events(ps, False)
        tracks = [_track(ev + _note_events(ps["lanes"][lane]["notes"], CHANNELS[lane]), end)]
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), PPQ)
    return header + b"".join(tracks)


def export_mid(ps: Dict, out_dir: Path) -> List[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    path = out_dir / f"{ps['id']}.mid"
    path.write_bytes(midi_bytes(ps))
    written.append(path)
    for lane in LANES:
        if ps["lanes"][lane]["notes"]:
            path = out_dir / f"{ps['id']}-{lane}.mid"
            path.write_bytes(midi_bytes(ps, lane))
            written.append(path)
    return written


# ================================================================================================= VFX module
def _check_vfx_limits(patterns: List[Dict]) -> None:
    if not patterns:
        raise BandError("no pattern sets to export")
    if len(patterns) > VFX_MAX_PATTERNS:
        raise BandError(f"the VFX band holds at most {VFX_MAX_PATTERNS} pattern sets, not {len(patterns)}")
    for ps in patterns:
        validate_pattern_set(ps)
        for lane in LANES:
            if len(ps["lanes"][lane]["notes"]) > VFX_MAX_NOTES:
                raise BandError(f"{ps['id']}: the {lane} lane has more than {VFX_MAX_NOTES} notes; use fewer bars")


def vfx_module_text(patterns: List[Dict], current: int = 0, live_path: Optional[str] = None) -> str:
    """The baked `arsenal_patterns` module that arsenal/fl/vfx/arsenal_band.py imports: VERSION, LIVE_PATH,
    DRUM_MAPS and PATTERNS. JSON syntax is valid Python here (the sets hold only strings, numbers, lists and
    dicts), and json.dumps escapes anything outside ASCII, so the file stays ASCII as FL wants."""
    _check_vfx_limits(patterns)
    body = ",\n".join(dump_json(ps).rstrip("\n") for ps in patterns)
    listing = "\n".join(f"#   {i:>2}  {ps['id']}: {ps['title']} ({ps['key']}, {ps['bpm_hint']} BPM)"
                        for i, ps in enumerate(patterns))
    text = (
        "# arsenal_patterns: the pattern module the arsenal band VFX Script imports.\n"
        "# GENERATED by `py -m arsenal.band export-vfx` (Akashic Aurora repo, arsenal/band.py); edits are overwritten.\n"
        "# Copy it to [User Data Folder]/VFX Script/Python/arsenal_patterns.py, then Reload in the band.\n"
        "# Format and contract: arsenal/band.py and arsenal/fl/vfx/arsenal_patterns.py. Keep it ASCII.\n"
        f"# Pattern knob index -> set (the playlist's current set is {int(current)}):\n"
        f"{listing}\n\n"
        f"VERSION = {VERSION}\n"
        f"LIVE_PATH = {'None' if live_path is None else ascii(str(live_path))}\n"
        "DRUM_MAPS = {}\n"
        f"PATTERNS = [\n{body}\n]\n"
    )
    return "".join(ch if ord(ch) < 128 else "?" for ch in text)


def vfx_live_text(patterns: List[Dict], current: int = 0) -> str:
    """The live playlist the band's "Live file" checkbox follows: {"version", "rev", "current", "patterns"}."""
    _check_vfx_limits(patterns)
    body = json.dumps(patterns, sort_keys=True)
    rev = hashlib.sha1(f"{current}:{body}".encode("utf-8")).hexdigest()[:12]
    return json.dumps({"version": VERSION, "rev": rev, "current": int(current), "patterns": patterns}) + "\n"


def export_vfx(store: PatternStore, out: Optional[Path] = None, live_path: Optional[str] = None,
               write_seeds: bool = True) -> Tuple[Path, Path, List[str], int]:
    """Write arsenal_patterns.py and arsenal_live.json (beside it) from the playlist, or from the seeds when the
    playlist is empty; then, unless write_seeds is False, the seeds are also saved into the store as `seeds
    --write` does (same-id files overwritten), so show, export-mid and the playlist find them. Returns (module,
    live file, ids, current)."""
    pl = store.playlist()
    ids = pl["items"] or [s["id"] for s in SEEDS]
    current = pl["current"] if pl["items"] else 0
    if not pl["items"] and write_seeds:
        for pid in ids:
            store.save(seed(pid))
    patterns = [store.load(pid) for pid in ids]
    out = Path(out) if out else VFX_OUT
    module = vfx_module_text(patterns, current, live_path)
    live = vfx_live_text(patterns, current)
    _write_atomic(out, module)
    twin = out.with_name(VFX_LIVE_NAME)
    _write_atomic(twin, live)
    return out, twin, ids, current


# ================================================================================================= text grid
def _flats(key: str) -> bool:
    k = nv.parse_key(key)
    return not k or k["bias"] <= 0


def _chord_at(chords: List[Dict], beat: float) -> Optional[Dict]:
    current = None
    for c in chords:
        if c["beat"] <= beat + 1e-9:
            current = c
    return current


def _bass_symbol(note: int, chord: Optional[Dict]) -> str:
    if chord is None:
        return "o"
    try:
        parsed = parse_chord_token(chord["name"], None)
    except BandError:
        return "o"
    interval = (note - parsed["root"]) % 12
    if interval == 0:
        return "R"
    for role, semis in parsed["tones"].items():
        if semis % 12 == interval:
            return role if role in ("3", "5", "7", "6", "2", "4") else "x"
    return "/" if note % 12 == parsed["bass"] else "a"


def render_grid(ps: Dict, bars_per_line: int = 4) -> str:
    """The lanes as a 16th-note grid. Bass: R 3 5 7 6 = chord tones, x = a colour tone, a = approach or passing
    tone, - = held. Drums: X loud, x, g ghost (under 50). Keys: # struck, - held. Off-grid notes (swing, triplets)
    sit in their nearest 16th."""
    meter = ps["meter"]
    bpb = beats_per_bar(meter)
    per_bar = int(round(bpb * 4))
    total_cells = int(round(ps["length_beats"] * 4))
    bars = int(round(ps["length_beats"] / bpb))
    flats = _flats(ps["key"])
    lines = [f"{ps['id']}: {ps['title']}  ({ps['key']}, {ps['bpm_hint']} BPM, {bars} bars of {meter[0]}/{meter[1]})",
             "grid = 16ths; note names C4 = MIDI 60 (FL's piano roll calls it C5)"]

    def cell(beat: float) -> int:
        return min(total_cells - 1, max(0, int(round(beat * 4))))

    def row_blank() -> List[str]:
        return ["."] * total_cells

    rows: List[Tuple[str, List[str]]] = []
    chord_row = [" "] * total_cells
    for i, c in enumerate(ps["chords"]):
        start = cell(c["beat"])
        end = cell(ps["chords"][i + 1]["beat"]) if i + 1 < len(ps["chords"]) else total_cells
        text = c["name"][: max(1, end - start)]
        for j, ch in enumerate(text):
            chord_row[start + j] = ch
    rows.append(("chord", chord_row))
    beat_row = []
    for k in range(total_cells):
        pos = k % per_bar
        beat_row.append(str(pos // 4 + 1) if pos % 4 == 0 else ".")
    rows.append(("beat", beat_row))

    bass = ps["lanes"]["bass"]["notes"]
    if bass:
        r = [" "] * total_cells
        for n in bass:
            s, e = cell(n["beat"]), max(cell(n["beat"]) + 1, int(round((n["beat"] + n["len"]) * 4)))
            for k in range(s + 1, min(e, total_cells)):
                if r[k] == " ":
                    r[k] = "-"
            r[s] = _bass_symbol(n["note"], _chord_at(ps["chords"], n["beat"]))
        rows.append(("bass", [ch if ch != " " else "." for ch in r]))
    drums = ps["lanes"]["drums"]["notes"]
    present = sorted({n["note"] for n in drums}, key=lambda p: (KIT_ORDER.index(p) if p in KIT_ORDER else 99, p))
    for pitch in present:
        r = row_blank()
        loud = [0] * total_cells
        for n in drums:
            if n["note"] == pitch:
                k = cell(n["beat"])
                loud[k] = max(loud[k], n["vel"])
        for k, v in enumerate(loud):
            if v:
                r[k] = "X" if v >= 100 else "x" if v >= 50 else "g"
        rows.append((GM_NAMES.get(pitch, f"gm{pitch}"), r))
    for lane in ("comp", "pad"):
        notes = ps["lanes"][lane]["notes"]
        if not notes:
            continue
        r = row_blank()
        for n in notes:
            s, e = cell(n["beat"]), int(round((n["beat"] + n["len"]) * 4))
            for k in range(s + 1, min(e, total_cells)):
                if r[k] == ".":
                    r[k] = "-"
            r[s] = "#"
        rows.append((lane, r))

    label_w = max(len(name) for name, _ in rows) + 2
    for first in range(0, bars, bars_per_line):
        last = min(bars, first + bars_per_line)
        lines.append("")
        header = " " * label_w
        for b in range(first, last):
            header += "|" + str(b + 1).ljust(per_bar)
        lines.append(header)
        for name, r in rows:
            text = name.ljust(label_w)
            for b in range(first, last):
                text += "|" + "".join(r[b * per_bar:(b + 1) * per_bar])
            lines.append(text.rstrip())
        lo, hi = first * bpb, last * bpb
        if bass:
            names = [midi_name(n["note"], flats) for n in bass if lo <= n["beat"] < hi]
            collapsed: List[str] = []
            for nm in names:
                if collapsed and collapsed[-1].split("x")[0] == nm:
                    head, _, count = collapsed[-1].partition("x")
                    collapsed[-1] = f"{head}x{int(count or 1) + 1}"
                else:
                    collapsed.append(nm)
            lines.append("  bass notes: " + " ".join(collapsed))
        for lane in ("comp", "pad"):
            notes = ps["lanes"][lane]["notes"]
            if not notes:
                continue
            parts = []
            for c in ps["chords"]:
                if lo <= c["beat"] < hi:
                    near = [n["beat"] for n in notes if c["beat"] - 0.25 - 1e-6 <= n["beat"] <= c["beat"] + 1e-6]
                    struck = max(near) if near else None                 # a pushed chord is struck a 16th early
                    v = sorted(n["note"] for n in notes if struck is not None and abs(n["beat"] - struck) < 1e-6)
                    parts.append(f"{c['name']} {' '.join(midi_name(p, flats) for p in v)}")
            lines.append(f"  {lane} voicings: " + " | ".join(parts))
    return "\n".join(lines)


# ================================================================================================= CLI
def _utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def _range_text(notes: List[Dict], flats: bool) -> str:
    if not notes:
        return ""
    lo, hi = min(n["note"] for n in notes), max(n["note"] for n in notes)
    return f", {midi_name(lo, flats)}..{midi_name(hi, flats)}"


def summary_lines(ps: Dict) -> List[str]:
    flats = _flats(ps["key"])
    bars = int(round(ps["length_beats"] / beats_per_bar(ps["meter"])))
    out = [f"{ps['id']}: \"{ps['title']}\" ({ps['key']}, {ps['bpm_hint']} BPM, {bars} bars of "
           f"{ps['meter'][0]}/{ps['meter'][1]})"]
    seen, chart = set(), []
    for c in ps["chords"]:
        label = f"{c['name']} ({c['nns']})" if c["nns"] else c["name"]
        if label not in seen:
            seen.add(label)
            chart.append(label)
    out.append("  chords  " + " | ".join(chart))
    for lane in LANES:
        notes = ps["lanes"][lane]["notes"]
        out.append(f"  {lane:<6}  " + (f"{len(notes)} notes{_range_text(notes, flats) if lane != 'drums' else ''}"
                                        if notes else "off"))
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="py -m arsenal.band",
                                 description="Claude's band for FL Studio: pattern sets as JSON, .mid and a VFX module")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state", help=f"the band's state folder (default: state/arsenal/band or ${STATE_ENV})")
    sub = ap.add_subparsers(dest="verb", required=True)

    mk = sub.add_parser("make", parents=[common], help='generate a pattern set: "4maj9 - 6m11 - 5^11/4 - 1add9"')
    mk.add_argument("loop", help='chords or Nashville numbers; "|" marks bar lines, "chord:beats" sets a length')
    mk.add_argument("--key", help='e.g. "Db major", "Bb minor" (needed for numbers; estimated otherwise)')
    mk.add_argument("--bpm", type=float, help="the tempo hint (default by drum style)")
    mk.add_argument("--bars", type=int, help="loop length in bars (default: the chord loop's)")
    mk.add_argument("--meter", default="4/4")
    mk.add_argument("--bass", choices=BASS_STYLES, default="roots-on-1")
    mk.add_argument("--drums", choices=DRUM_STYLES, default="ballad")
    mk.add_argument("--comp", action="store_true", help="add the comp lane (restruck voicings)")
    mk.add_argument("--shell", action="store_true",
                    help="voice the comp as two-note shells (3rd and 7th) in C3..E4, leaving middle C's octave free")
    mk.add_argument("--pad", action="store_true", help="add the pad lane (held voicings)")
    mk.add_argument("--fill", action="store_true", help="a drum fill in the last bar and a crash on the loop top")
    mk.add_argument("--swing", type=float, help="16th swing 0.5..0.75 (neo-soul defaults to 0.58)")
    mk.add_argument("--dropout", type=float, default=0.0,
                    help="0..1: the chance a bar rests for everything but the bass (never bar 1, never two in a row; "
                         "leaning on the last bar of each 4-bar phrase)")
    mk.add_argument("--title")
    mk.add_argument("--id", dest="pid", help="the pattern id (default: from the title)")
    mk.add_argument("--out", help="write the JSON into this folder instead of the store")
    mk.add_argument("--add", action="store_true", help="also append it to the playlist")

    sd = sub.add_parser("seeds", parents=[common], help="the six starter pattern sets, explained")
    sd.add_argument("--write", action="store_true", help="save them into the store (overwrites same-id files)")
    sd.add_argument("--add", action="store_true", help="append them to the playlist (implies --write)")

    sub.add_parser("list", parents=[common], help="stored pattern sets and seeds")

    sh = sub.add_parser("show", parents=[common], help="a text grid of a pattern set's lanes")
    sh.add_argument("id")
    sh.add_argument("--bars-per-line", type=int, default=4)
    sh.add_argument("--json", action="store_true", help="print the pattern set's JSON instead")

    em = sub.add_parser("export-mid", parents=[common], help="write .mid files (type 1, 480 PPQ)")
    em.add_argument("id")
    em.add_argument("--out", help="folder (default: <state>/mid/<id>)")

    ev = sub.add_parser("export-vfx", parents=[common],
                        help="write arsenal_patterns.py and arsenal_live.json for the VFX Script band")
    ev.add_argument("--out", help=f"module file (default: {VFX_OUT.relative_to(REPO).as_posix()}); "
                                  f"{VFX_LIVE_NAME} is written beside it")
    ev.add_argument("--live-path", help="LIVE_PATH in the module: where FL will find the live JSON (default None)")
    ev.add_argument("--no-write-seeds", action="store_true",
                    help="with an empty playlist, do not also save the seeds into the store")

    pl = sub.add_parser("playlist", help="the pattern sets a jam steps through")
    pl_sub = pl.add_subparsers(dest="pl_verb", required=True)
    pa = pl_sub.add_parser("add", parents=[common], help="append (or insert --at POS) a pattern set")
    pa.add_argument("id")
    pa.add_argument("--at", type=int, help="1-based position to insert at")
    pl_sub.add_parser("list", parents=[common], help="the playlist, > marks the current set")
    pr = pl_sub.add_parser("rm", parents=[common], help="remove by id or 1-based position")
    pr.add_argument("target")
    pc = pl_sub.add_parser("current", parents=[common], help="set the current set by 1-based position")
    pc.add_argument("position", type=int)
    return ap


def _warn_stale(store: PatternStore, ids: Sequence[str]) -> None:
    for pid in ids:
        note = store.stale_note(pid)
        if note:
            print(f"warning: {note}", file=sys.stderr)


def _print_playlist(store: PatternStore, out) -> None:
    pl = store.playlist()
    if not pl["items"]:
        print(f"the playlist is empty ({store.playlist_path})", file=out)
        return
    for i, pid in enumerate(pl["items"]):
        mark = ">" if i == pl["current"] else " "
        try:
            ps = store.load(pid)
            detail = f"{ps['title']} ({ps['key']}, {ps['bpm_hint']} BPM)"
        except BandError as exc:
            detail = f"MISSING: {exc}"
        print(f"{mark} {i + 1:>2}. {pid:<24} {detail}", file=out)


def main(argv=None, out=None) -> int:
    _utf8_streams()
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    store = PatternStore(getattr(args, "state", None))
    try:
        if args.verb == "make":
            ps = make_pattern_set(args.loop, key=args.key, bpm=args.bpm, bars=args.bars, bass=args.bass,
                                  drums=args.drums, comp=args.comp, pad=args.pad, fill=args.fill, swing=args.swing,
                                  meter=args.meter, title=args.title, pid=args.pid, dropout=args.dropout,
                                  shell=args.shell)
            path = store.save(ps, Path(args.out) if args.out else None)
            for line in summary_lines(ps):
                print(line, file=out)
            if args.dropout:
                bars = int(round(ps["length_beats"] / beats_per_bar(ps["meter"])))
                rests = dropout_bars(ps["id"], bars, args.dropout)
                print("  dropout " + (f"bars {', '.join(str(b + 1) for b in rests)} rest; the bass plays on"
                                      if rests else "no bar rests at this amount"), file=out)
            if not args.key:
                print(f"  (key estimated as {ps['key']}; pass --key to set it)", file=out)
            print(f"wrote {path}", file=out)
            if args.add:
                if args.out:
                    print("not added to the playlist: --out writes outside the store", file=sys.stderr)
                else:
                    store.playlist_add(ps["id"])
                    print(f"added {ps['id']} to the playlist", file=out)
            print(f"next: py -m arsenal.band show {ps['id']}  |  py -m arsenal.band export-mid {ps['id']}", file=out)
            return 0
        if args.verb == "seeds":
            for s in SEEDS:
                print(f"{s['id']:<20} {s['key']:<9} {s['loop']}", file=out)
                print(f"{'':<20} {s['drums']} drums, {s['bass']} bass: {s['why']}", file=out)
                if args.write or args.add:
                    path = store.save(seed(s["id"]))
                    print(f"{'':<20} wrote {path}", file=out)
                if args.add:
                    store.playlist_add(s["id"])
            return 0
        if args.verb == "list":
            stored = store.stored()
            for pid in stored:
                ps = store.load(pid)
                print(f"stored  {pid:<24} {ps['title']} ({ps['key']}, {ps['bpm_hint']} BPM)", file=out)
            for s in SEEDS:
                tag = "seed*" if s["id"] in stored else "seed "
                print(f"{tag}   {s['id']:<24} {s['title']} ({s['key']}, {s['bpm']} BPM)", file=out)
            if any(s["id"] in stored for s in SEEDS):
                print("* a stored file of the same id is used instead of the seed", file=out)
            return 0
        if args.verb == "show":
            ps = store.load(args.id)
            _warn_stale(store, [args.id])
            if args.json:
                out.write(dump_json(ps))
                return 0
            print(render_grid(ps, max(1, args.bars_per_line)), file=out)
            for warning in lint(ps):
                print(f"warning: {warning}", file=sys.stderr)
            return 0
        if args.verb == "export-mid":
            ps = store.load(args.id)
            _warn_stale(store, [args.id])
            folder = Path(args.out) if args.out else store.root / "mid" / ps["id"]
            for path in export_mid(ps, folder):
                print(f"wrote {path}", file=out)
            print(f"In FL: set the tempo to {ps['bpm_hint']} BPM, then drag each {ps['id']}-<lane>.mid onto that "
                  f"channel's piano roll (Shift skips the import dialog; leave Blend off to replace).", file=out)
            return 0
        if args.verb == "export-vfx":
            seeding = not store.playlist()["items"] and not args.no_write_seeds
            path, twin, ids, current = export_vfx(store, Path(args.out) if args.out else None, args.live_path,
                                                  write_seeds=not args.no_write_seeds)
            print(f"wrote {path} and {twin.name}: {len(ids)} pattern sets; the playlist's current set is Pattern "
                  f"knob {current} ({ids[current]})", file=out)
            if seeding:
                print(f"the playlist is empty: saved the {len(ids)} seeds into {store.patterns} as well", file=out)
            _warn_stale(store, ids)
            for i, pid in enumerate(ids):
                print(f"  Pattern knob {i:>2}: {pid}", file=out)
            print("To install: copy arsenal_patterns.py to [User Data Folder]/VFX Script/Python/ and press the band's "
                  "Reload (this command never writes into FL's folders).", file=out)
            return 0
        if args.verb == "playlist":
            if args.pl_verb == "add":
                store.playlist_add(args.id, args.at)
            elif args.pl_verb == "rm":
                _, removed = store.playlist_rm(args.target)
                print(f"removed {removed}", file=out)
            elif args.pl_verb == "current":
                store.playlist_current(args.position)
            _print_playlist(store, out)
            return 0
    except BandError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
