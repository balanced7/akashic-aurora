"""arsenal.keylab.chordsense -- hear the harmony live: chord, key, roman numeral, tension, pedal, resolution.

Daniel, 2026-10-23: "If we could somehow convert the audio to midi data, realtime audio chord analysis could
really help us match beat events to rythm and flow", and "think of some cool features ... more advanced chord
detection, or beautifying it somehow ... make a badass vj / visualization engine".

One theory, two ears. `feed(block)` listens to audio; `feed_notes(events)` listens to played notes (the keys).
Both reach the same back end: the same chord vocabulary and scorer, the same smoothing, the same key tracker and
the same tension model. A chord named from the loopback and a chord played on the KeyLab mean the same thing.

    cs = ChordSense(48000, 512)
    for block in blocks:                 # float audio, mono (n,) or (n, channels), any length
        for ev in cs.feed(block):        # events only when something CHANGES, never a stream of repeats
            ...
    cs.snapshot()                        # the continuous state for a renderer: read it every frame

    keys = ChordSense()                  # a second instance for the keys (one source per instance)
    keys.feed_notes([{"t": 0.0, "note": 60, "vel": 90}, {"t": 0.5, "note": 60, "vel": 0}], now=1.0)

Events (dicts; `t` = seconds of input consumed when the event was decided; `src` = 'audio' | 'keys'):
  chord       {name, root, quality, bass, confidence, changed, t_change, numeral, figure, roman, function, key,
              tension, pedal_pc}. numeral is the root-position reading (V7), figure the inversion (65), roman both
              (V65); name is 'N' (root / quality / bass None) for silence, drums, noise or a lone melody line.
              t_change back-dates the change to the attack that started it (median error 9 ms, p90 40 ms on the
              synthetic set): beat matching wants the onset, not the moment the decision was safe. tension is what
              this chord carries now. confidence (0..1) is an agreement margin, not a posterior: how far the
              chord's score leads the best RIVAL reading (Am or Em for C; not Cmaj7 or C5, which are colours of
              it), times the share of its tones sounding as notes, times how clearly tonal the sound is, times how
              little the bass note dwarfs the voices -- an ambiguous voicing (G-C-D: Gsus4 or Csus2?), a bare
              dyad, a chord under noise or under a bass 12 dB over it read low. Names follow the key: a root is
              spelled by the degree it sits on (borrowed and chromatic roots as lowered degrees: Bb, Eb, Ab in C;
              leading-tone diminished chords and minor's raised degrees as sharps: G#dim, F#m in A minor), a
              slash bass by its interval above the root. Before a key is known chords are spelled by common usage
              (C#m, G#m, D#dim; Db, Ab, Eb).
  key         {key, tonic, mode, confidence, chord, numeral, figure, roman, function}: confidence is the key's share
              of a softmax over all 24 keys' fits (the fast memory blended with a long one a key change does not
              reset): a key just reached on a few seconds' evidence is believed less than one that has stood.
  pedal       {pc, note, on, strength, since, chords, clash_s, clash, tension}: one pitch class really held or
              re-struck (not a previous chord's tail ringing over) through nearly every chord while the harmony
              moves under it (PEDAL_CHORDS different chord roots), AND clashing with it -- not a tone of the chord
              under it, or only the colour it gives it (Ab + a held Db reads Absus4) -- or held on as a drone over
              four roots or more; its pull on the tension grows the longer it holds. A common tone of a plain loop
              (the C of Am-F-C, of C-Am-F-Dm7-G7) is not a pedal.
  resolution  {from, to, chord, numeral, pedal_pc}: tension that had built up falls back onto the tonic

For the VJ engine (arsenal/keylab/vj.py, its Server-Sent Events contract) `to_vj_events(event)` maps each event to
the page's events: the existing chord event and two new ones --
  chord    {"t":"chord","src":"audio|keys","name","root","quality","pcs","bass","roman","key","conf","changed"}
           (quality in the engine's spelling: "maj", "m", "7", "maj7", "m7", "sus2", "sus4", "dim", "aug",
           "add9", "5"; 'N' = no chord: root, quality and bass null, pcs [])
  key      {"t":"key","name":"Db major","conf":0..1}                       the key, announced when it lands or moves
  tension  {"t":"tension","value":0..1,"pedal_pc":0..11|null}              with every chord, pedal and resolution

Snapshot: {t, chord, key, key_confidence, tension, dissonance, pedal, pulse, chroma, notes, bass, energy,
tuning_cents}. pulse (0..1) is the attack strength of the HARMONIC part of the latest frame (new notes, not
drums: drums alone never pulse): a renderer can flash on it.

Audio front end: a causal FIR anti-alias decimator to ~11-12 kHz; two Hann FFTs (a long one for the bass, a short
one for the treble) read as interpolated spectral PEAKS, each with its sinusoidality (how far it stands above the
local level of the spectrum: partials stand clear, the peaks of noise do not); a tuning-offset estimate (a circular
mean of the peaks' deviations from the A440 grid); the peaks binned on a log-frequency grid of three bins per
semitone; a causal harmonic / percussive split on that grid (a median over a short PAST window in time against a
median across frequency, soft mask), so drum hits and bass-drum sweeps stay out of the harmony; below C2 only what
held through the whole past window counts (a kick's tail swells and fades with every beat, a sub bass holds).
TONALITY = the sinusoidal share of the peak energy times its steady (harmonic) share, times a register factor (a
sound whose harmonic energy sits mostly above C6 -- 808 hats, a ride -- must be that much more tonal), with
hysteresis (0.08 on, 0.04 off: retuned on real pads and synth-chord loops): white or pink noise, a riser, vinyl
crackle, applause and hi-hat or shaker loops read 'N', and a chord does not drop to 'N' at a drum fill. The bass
NOTE (the lowest significant peak of 39-250 Hz: a sub bass at E1 is found by its fundamental) is taken out of the
harmony with its own harmonic series (a power law for its odd and one for its even partials, fitted to its
cleanest partials that are there: a square bass has no even ones, a hum or a low-passed sub stops after a few), so
a loud or bright bass cannot turn a maj7 into a 5; it comes back as a chord tone at half weight, or as a slash
under the voices when they do not carry it (G-B-D over a C bass is G/C, not Csus2). From what is left: a 12-bin
chroma, a BASS chroma (weighted toward the lowest note) for inversions and slash chords, and an overtone-corrected
note salience: the notes sounding, for dissonance, the pedal, and the rules that a chord needs two of its own
tones sounding (a melody note and its overtones is not a power chord; a dyad must hold longer than a triad) and
that a new chord is not built from a line's tail (a note struck before the newest one and fading: the last note
of a melody or a bass line ringing into the next). A chord already named holds through one or two of its own
notes for a few seconds (a staccato comp's top note, an arpeggio between its notes).

Back end: templates for major, minor, 7, maj7, m7, sus2, sus4, dim, aug, add9 and 5, with the expected
overtones for audio and plain for notes, scored by correlation with the chroma; a bass term (root in the bass,
a chord tone in the bass = an inversion, a foreign bass = a penalty); an 'N' state; an online HMM forward filter
(a sticky self-transition) plus a hold rule, so labels do not flicker. A Krumhansl-Kessler key tracker with two
memories (18 s for stability, 4 s to hear a modulation within ~5-8 s) and hysteresis, where a dominant 7th also
points at the tonic it resolves to, and the fast memory may move the key only when the rival's own tonic chord
has been heard lately more than the current key's (C-Bb-F-C stays C); roman numerals and function in that key (I,
IV, V7, vi, bVII, V/V ...).
Tension 0..1 from the chord's circle-of-fifths distance, its function and colour, the dissonance of what is
sounding, and the pedal.

Rules it was built under (the keylab licence firewall): numpy, scipy and the standard library only; no models,
no files, no I/O; causal (nothing ever looks ahead); bounded work per call, so it never blocks an audio loop (a
non-finite sample is heard as silence; the keys path jumps an idle gap, or a held one, in one step; a non-finite
time is refused). At 48 kHz with hop 512 it
runs far over 20x real time on one core (pinned by tests/test_keylab_chordsense.py).
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import firwin

# --- names and vocabulary ----------------------------------------------------------------------------------

SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
# with no key yet, chords are spelled the way charts usually spell them: major-family roots Db Eb F# Ab Bb, minor
# (and diminished) roots C# Eb F# G# Bb -- C#m and G#m, not Dbm and Abm; D#dim, the leading-tone chord of E
DEFAULT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MINOR_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]
DIM_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]

# quality -> (intervals from the root, display suffix, per-tone weight). The order is the scoring order.
QUALITIES: Dict[str, Tuple[Tuple[int, ...], str, Tuple[float, ...]]] = {
    "maj": ((0, 4, 7), "", (1.0, 1.0, 0.9)),
    "min": ((0, 3, 7), "m", (1.0, 1.0, 0.9)),
    "7": ((0, 4, 7, 10), "7", (1.0, 1.0, 0.8, 0.9)),
    "maj7": ((0, 4, 7, 11), "maj7", (1.0, 1.0, 0.8, 0.9)),
    "m7": ((0, 3, 7, 10), "m7", (1.0, 1.0, 0.8, 0.9)),
    "sus2": ((0, 2, 7), "sus2", (1.0, 0.95, 0.9)),
    "sus4": ((0, 5, 7), "sus4", (1.0, 0.95, 0.9)),
    "dim": ((0, 3, 6), "dim", (1.0, 1.0, 1.0)),
    "aug": ((0, 4, 8), "aug", (1.0, 1.0, 1.0)),
    "add9": ((0, 2, 4, 7), "add9", (1.0, 0.8, 1.0, 0.9)),
    "5": ((0, 7), "5", (1.0, 0.9)),
}
QUALITY_NAMES = list(QUALITIES)
# a small log-prior: the plain triads are the default reading, richer chords must earn their extra tone
PRIOR = {"maj": 0.0, "min": 0.0, "7": -0.010, "maj7": -0.015, "m7": -0.015, "sus2": -0.020, "sus4": -0.015,
         "dim": -0.015, "aug": -0.030, "add9": -0.020, "5": -0.040}
# the tension a chord's own colour carries (a dominant 7th's tritone, a suspension waiting to fall)
QUALITY_TENSION = {"maj": 0.0, "min": 0.05, "5": 0.0, "add9": 0.06, "maj7": 0.10, "m7": 0.08, "sus2": 0.14,
                   "sus4": 0.22, "7": 0.25, "dim": 0.38, "aug": 0.40}

# Krumhansl-Kessler probe-tone profiles (Krumhansl 1990); index 0 = the tonic
KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
KEYS = [(t, "major") for t in range(12)] + [(t, "minor") for t in range(12)]
FLAT_KEYS_MAJOR = {5, 10, 3, 8, 1, 6}           # F Bb Eb Ab Db Gb
FLAT_KEYS_MINOR = {2, 7, 0, 5, 10, 3}           # d g c f bb eb


def _kk_matrix() -> np.ndarray:
    """(24, 12): every key's profile, mean-removed and unit-norm, so the 24 correlations are one product."""
    rows = []
    for prof in (KK_MAJOR, KK_MINOR):
        p0 = prof - prof.mean()
        p0 = p0 / np.linalg.norm(p0)
        rows.extend(np.roll(p0, t) for t in range(12))
    return np.array(rows)


_KK = _kk_matrix()
_REF_DT = 512 / 48000.0                         # the frame p_stay and kappa are stated for
_DB_PER_NEPER = 20.0 / math.log(10.0)
_FIFTH_BELOW = (np.arange(12) - 7) % 12         # x[_FIFTH_BELOW][p] = x[p - 7]: the note whose 12th lands on p

# the overtone series folded to pitch classes: harmonic h of a tone lands this many semitones (mod 12) above it
_HARM_PC = (0, 0, 7, 0, 4, 7, 10, 0)            # h = 1..8: unison, octave, 12th, 2 oct, 17th, 19th, b21st, 3 oct
_HARM_DECAY = 0.6                               # amplitude of harmonic h ~ 0.6^(h-1) (Gomez 2006)

# interval-class roughness for the dissonance term: index = interval class 0..6 (ic1 = m2/M7, ic6 = tritone)
_IC_ROUGH = np.array([0.0, 1.0, 0.45, 0.12, 0.08, 0.02, 0.65])
_ROUGH = np.array([[_IC_ROUGH[min((i - j) % 12, (j - i) % 12)] for j in range(12)] for i in range(12)])


def note_names_for(key: Optional[Tuple[int, str]], quality: Optional[str] = None) -> List[str]:
    """Spell pitch classes with flats in flat keys, sharps in sharp keys; with no key, the common spellings for a
    chord of this quality (C#m, G#m, D#dim but Db, Ab, Eb)."""
    if key is None:
        if quality in ("min", "m7"):
            return MINOR_NAMES
        if quality == "dim":
            return DIM_NAMES
        return DEFAULT_NAMES
    tonic, mode = key
    flat = tonic in (FLAT_KEYS_MAJOR if mode == "major" else FLAT_KEYS_MINOR)
    return FLATS if flat else SHARPS


_LETTERS = "CDEFGAB"
_NATURAL = (0, 2, 4, 5, 7, 9, 11)
# the scale step (letters above the tonic) each degree is spelled on in a key: a chromatic root is a LOWERED degree
# (bII, bIII, bV, bVI, bVII: Db, Eb, Gb, Ab, Bb in C) -- except a diminished chord, the leading-tone chord of the
# degree above (C#dim, D#dim, F#dim, G#dim, A#dim in C); minor keys raise their 3rd, 6th and 7th (C#, F#, G# in A)
_STEP_MAJOR = (0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6)
_STEP_MINOR = (0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6)
_STEP_DIM = {1: 0, 3: 1, 6: 3, 8: 4, 10: 5}
_NO_FLAT_MINOR = {4: 2, 9: 5}                    # minor: the raised 3rd / 6th are sharps (C#, F# in A minor)
_ODD = {"Cb", "Fb", "E#", "B#"}
_STEP_OF_INTERVAL = (0, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6)   # a chord tone's letter above its root (b5 for 6)


def _spell(pc: int, letter_idx: int, sharp_context: bool) -> str:
    """pitch class pc on letter _LETTERS[letter_idx]; a double accidental, or Cb / Fb / E# / B#, is spelled as the
    plain enharmonic instead (a chord chart writes B, not Cb)."""
    acc = (pc - _NATURAL[letter_idx] + 6) % 12 - 6
    name = _LETTERS[letter_idx] + ("#" * acc if acc > 0 else "b" * -acc)
    if abs(acc) > 1 or name in _ODD:
        return (SHARPS if sharp_context else FLATS)[pc]
    return name


def _tonic_letter(key: Tuple[int, str]) -> int:
    return _LETTERS.index(note_names_for(key)[key[0]][0])


def spell_root(root: int, quality: Optional[str], key: Tuple[int, str]) -> Tuple[str, int]:
    """(name, letter index) of a chord root in a key, by the scale degree it sits on (see _STEP_MAJOR)."""
    tonic, mode = key
    degree = (root - tonic) % 12
    step = (_STEP_MAJOR if mode == "major" else _STEP_MINOR)[degree]
    if quality == "dim" and degree in _STEP_DIM:
        step = _STEP_DIM[degree]
    elif mode == "minor" and degree in _NO_FLAT_MINOR:
        step = _NO_FLAT_MINOR[degree]
    elif degree == 6 and quality in ("maj", "7", "aug", "5", "maj7", "add9", "sus2", "sus4"):
        step = 4                                 # the tritone substitute is bV (Gb7 in C); #iv (F#m, F#dim) stays
    li = (_tonic_letter(key) + step) % 7
    sharp = (root - _NATURAL[li]) % 12 in (1, 2)
    return _spell(root, li, sharp), li


def chord_name(root: int, quality: str, bass: Optional[int] = None, key: Optional[Tuple[int, str]] = None) -> str:
    """The chord's name: in a key by the key's spelling rules (borrowed and chromatic roots as lowered degrees: Bb,
    Eb, Ab in C major; leading-tone diminished chords sharp: G#dim in A minor), the bass by its interval above the
    root (D/F#, Ab/C); with no key, the common chart spellings (C#m, Db, D#dim)."""
    if key is None:
        names = note_names_for(None, quality)
        s = names[root] + QUALITIES[quality][1]
        if bass is not None and bass != root:
            s += "/" + names[bass]
        return s
    name, li = spell_root(root, quality, key)
    s = name + QUALITIES[quality][1]
    if bass is not None and bass != root:
        iv = (bass - root) % 12
        if iv in (8,) and quality == "aug":
            bl = (li + 4) % 7                    # the augmented 5th
        else:
            bl = (li + _STEP_OF_INTERVAL[iv]) % 7
        if iv not in [i for i in QUALITIES[quality][0]]:
            s += "/" + spell_note(bass, key)     # a foreign bass (G/C): spelled in the key
        else:
            s += "/" + _spell(bass, bl, "#" in name or (bass - _NATURAL[bl]) % 12 in (1, 2))
    return s


def spell_note(pc: int, key: Optional[Tuple[int, str]]) -> str:
    """A single pitch class (a pedal, a bass) in a key: diatonic degrees by the key's letters, the others as a
    lowered degree (or raised 3rd / 6th / 7th in minor)."""
    if key is None:
        return DEFAULT_NAMES[pc]
    return spell_root(pc, None, key)[0]


def key_name(tonic: int, mode: str) -> str:
    return note_names_for((tonic, mode))[tonic] + (" major" if mode == "major" else " minor")


def chord_tones(root: int, quality: str) -> List[int]:
    return [(root + i) % 12 for i in QUALITIES[quality][0]]


def _templates(harmonics: bool, gamma: float) -> np.ndarray:
    """(12 * Q, 12) templates, row = root * Q + quality index, compressed by the same power as the chroma."""
    rows = []
    for root in range(12):
        for q in QUALITY_NAMES:
            iv, _, w = QUALITIES[q]
            t = np.zeros(12)
            for k, i in enumerate(iv):
                pc = (root + i) % 12
                if harmonics:
                    for h, off in enumerate(_HARM_PC):
                        t[(pc + off) % 12] += w[k] * _HARM_DECAY ** h
                else:
                    t[pc] += w[k]
            rows.append(t ** gamma)
    return np.array(rows)


# --- roman numerals ----------------------------------------------------------------------------------------

_MAJOR_SCALE = frozenset((0, 2, 4, 5, 7, 9, 11))
_MINOR_SCALE = frozenset((0, 2, 3, 5, 7, 8, 10, 11))   # natural minor plus the raised 7th (harmonic minor: V, vii°)
_DEGREE_MAJOR = {0: "I", 1: "bII", 2: "II", 3: "bIII", 4: "III", 5: "IV", 6: "#IV", 7: "V", 8: "bVI", 9: "VI",
                 10: "bVII", 11: "VII"}
_DEGREE_MINOR = {0: "I", 1: "bII", 2: "II", 3: "III", 4: "#III", 5: "IV", 6: "#IV", 7: "V", 8: "VI", 9: "#VI",
                 10: "VII", 11: "VII"}
# the triad each degree carries in the key: a secondary dominant's target is named by it (never a diminished one)
_TRIAD_MAJOR = {0: "maj", 2: "min", 4: "min", 5: "maj", 7: "maj", 9: "min", 11: "dim"}
_TRIAD_MINOR = {0: "min", 2: "dim", 3: "maj", 5: "min", 7: "maj", 8: "maj", 10: "maj", 11: "dim"}
# the function of a chord whose tones all belong to the key, by the degree of its root
_FUNCTION_MAJOR = {0: "tonic", 2: "subdominant", 4: "tonic", 5: "subdominant", 7: "dominant", 9: "tonic",
                   11: "dominant"}
_FUNCTION_MINOR = {0: "tonic", 2: "subdominant", 3: "tonic", 5: "subdominant", 7: "dominant", 8: "subdominant",
                   10: "dominant", 11: "dominant"}
_LOWER = {"min", "m7", "dim"}
_NUM_SUFFIX = {"maj": "", "min": "", "7": "7", "maj7": "maj7", "m7": "7", "sus2": "sus2", "sus4": "sus4",
               "dim": "\u00b0", "aug": "+", "add9": "add9", "5": "5"}
_EXTENSION = {"add9": 2, "7": 10, "maj7": 11, "m7": 10}      # the tone a four-note chord adds to its triad
_COLOUR = {"7": (10,), "maj7": (11,), "m7": (10,), "sus4": (5,)}
_FUNCTION_TENSION = {"tonic": 0.0, "subdominant": 0.10, "dominant": 0.28, "secondary dominant": 0.30,
                     "borrowed": 0.20, "neapolitan": 0.30, "chromatic": 0.30}


def _plain_numeral(degree: int, quality: str, mode: str) -> str:
    base = (_DEGREE_MAJOR if mode == "major" else _DEGREE_MINOR)[degree]
    if degree == 6 and quality != "dim":
        base = "bV"
    if mode == "minor" and degree == 11 and quality != "dim":
        base = "#VII"
    if quality in _LOWER:
        base = base.lower()
    return base + _NUM_SUFFIX[quality]


def _figure(root: int, quality: str, bass: Optional[int]) -> str:
    """Figured-bass inversion mark: triads 6 / 64, sevenths 65 / 43 / 42; '' in root position or with no bass."""
    if bass is None or bass == root:
        return ""
    iv = (bass - root) % 12
    if quality in ("7", "maj7", "m7"):
        return {3: "65", 4: "65", 7: "43", 10: "42", 11: "42"}.get(iv, "")
    if quality in ("maj", "min", "dim", "aug"):
        return {3: "6", 4: "6", 6: "64", 7: "64", 8: "64"}.get(iv, "")
    return ""


def roman(root: int, quality: str, bass: Optional[int], tonic: int, mode: str) -> Tuple[str, str, str]:
    """(numeral, figure, function) of a chord in a key. numeral is the root-position reading ('V7', 'vi', 'bVII',
    'V/V', 'V7/IV'); figure is the inversion ('6', '64', '65', '43', '42' or ''); function is one of tonic,
    subdominant, dominant, secondary dominant, borrowed, neapolitan, chromatic.

    A chord whose tones all sit in the key's scale is diatonic and takes its function from its degree (the minor
    scale here includes the raised 7th, so V and vii° are diatonic in minor). Otherwise, one whose tones all sit
    in the PARALLEL mode's scale is borrowed (bVII, bVI, iv in major; the Dorian IV and a Picardy I in minor).
    Otherwise a major or dominant-7th chord a fifth above a degree carrying a major or minor triad is that
    degree's secondary dominant (V/V, V7/IV); bII is the neapolitan; anything else is chromatic."""
    degree = (root - tonic) % 12
    major = mode == "major"
    scale = _MAJOR_SCALE if major else _MINOR_SCALE
    other = _MINOR_SCALE - {11} if major else _MAJOR_SCALE
    tones = {(t - tonic) % 12 for t in chord_tones(root, quality)}
    fig = _figure(root, quality, bass)
    num = _plain_numeral(degree, quality, mode)
    if tones <= scale:
        return num, fig, (_FUNCTION_MAJOR if major else _FUNCTION_MINOR)[degree]
    if tones <= other:
        return num, fig, "borrowed"
    if quality in ("maj", "7"):
        target = (degree - 7) % 12
        tq = (_TRIAD_MAJOR if major else _TRIAD_MINOR).get(target)
        if target != 0 and tq in ("maj", "min"):
            return ("V7" if quality == "7" else "V") + "/" + _plain_numeral(target, tq, mode), fig, \
                "secondary dominant"
    if degree == 1 and quality == "maj":
        return num, fig, "neapolitan"
    return num, fig, "chromatic"


def full_roman(numeral: Optional[str], figure: str) -> Optional[str]:
    """numeral + inversion the way an analysis writes it: I + 6 = I6, V7 + 65 = V65, V7/V + 43 = V43/V,
    IVmaj7 + 42 = IVmaj42 (a seventh chord's figure replaces its 7)."""
    if numeral is None or not figure:
        return numeral
    head, slash, tail = numeral.partition("/")
    if head.endswith("7"):
        head = head[:-1]
    return head + figure + slash + tail


def _unit(x: float) -> float:
    """x clipped to 0..1 (a plain float: np.clip costs microseconds per scalar call)."""
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else float(x))


def _cof_distance(a: int, b: int) -> int:
    """Steps between two pitch classes around the circle of fifths (0..6)."""
    d = abs((a * 7) % 12 - (b * 7) % 12)
    return min(d, 12 - d)


# --- the engine --------------------------------------------------------------------------------------------

class ChordSense:
    """Streaming chord / key / tension analysis of audio blocks (`feed`) or played notes (`feed_notes`).

    One instance listens to ONE source, audio or notes, never both (their clocks differ). Make two instances to
    hear the loopback and the keys at once; they share every rule below.
    """

    # audio: chroma pitch range (MIDI), the bass band, and where the long FFT hands over to the short one
    LO_MIDI, HI_MIDI = 27, 100                  # D#1 (39 Hz) .. E7 (2.6 kHz)
    BASS_LO, BASS_HI = 27, 59                   # D#1 (39 Hz) .. B3 (247 Hz): a sub bass's fundamental is heard
    HARM_LO = 36                                # C2 (65 Hz): below it is the bass's register, never a chord voice
    SPLIT_MIDI = 57                             # below: the long FFT's peaks; at and above: the short FFT's
    BINS_PER_SEMI = 3
    MAX_SAMPLE = 1e5                            # a sample beyond this (or NaN / Inf) is not audio: silence
    PROM_HALF, PROM_DB = 12, (10.0, 20.0)       # a peak's sinusoidality: 0 at 10 dB over the local level, 1 at 20
    TONAL_ON, TONAL_OFF = 0.08, 0.04            # tonality hysteresis: chords are heard above ON, N below OFF
    REGISTER = (0.6, 0.1)                       # tonality counts in full with this share of the voices below C6
    N_BOOST = (0.25, 1.5)                       # below this tonality N gains this much per unit of tonality short
    CLEAR_TONALITY = 0.6                        # ... and at full confidence from this tonality up
    # the overtones a note explains in the semitones above it (offset, share): harmonics 2-8 of a bright tone
    _OVERTONES = ((12, 0.55), (19, 0.35), (24, 0.25), (28, 0.2), (31, 0.17), (34, 0.14), (36, 0.13))
    NOTE_ON, FEW_NOTES = 0.2, 1.0               # a pitch class sounds as a note above NOTE_ON; fewer than two of
    #                                             a chord's tones sounding costs it FEW_NOTES (it cannot win)
    LAW_FLOOR, LAW_MAX_H, LAW_Q = 0.02, 12, 0.8
    TWELFTH_SHARE = 0.5                         # a bass's 12ths give up this share of what its law predicts
    LOW_VOICE = 2.5                             # audio: a voice below C3 sounds only from 2.5 x NOTE_ON of the bass
    FADE_S, FADE = 0.2, (0.45, 0.8)              # audio: a note under 0.7 of its level of FADE_S ago is fading; a
    #                                             line's fading tail builds no new chord unless above 0.8 of the loudest
    TAILS_FROM_N_ONLY = True
    RISE, SYNC_S = 1.5, 0.15                    # a pitch class rising 1.5 times over FADE_S is being struck; notes
    #                                             struck within SYNC_S of each other are one attack
    VOICE_FLOOR = 0.10                          # voices quieter than this share of the bass note are its residue
    LONE_HOLD_S = 6.0                           # a chord holds through a lone note of its own this long (see _step)
    LONE_MIN_S = 0.3                            # ... once it has sounded in full this long
    DYAD_HOLD_S = 0.20                          # extra hold for a chord with only two of its tones sounding
    FOREIGN_BASS = (0.10, 0.03)                 # score cost of a bass outside the chord: normally / under a lone bass
    UNEXPLAINED = 0.10                          # a chord claiming a lone bass pays this per voice it leaves out
    CONF_MASK = (0.8, 0.12, 0.7)                # ... and lower (by up to 0.7) as the bass note dwarfs the voices: a
    #                                             bass share of 0.8 -> 0.92 is where a chord's colour gets lost
    CONF_MARGIN, CONF_TAU_S = 0.15, 0.25        # confidence: 1.0 needs this score lead over the best rival (and
    #                                             every tone sounding, in clear tonal sound), averaged over TAU
    BASS_SIG, BASS_TAU_S = 0.3, 0.12            # the lowest bass peak above this share of the loudest = the bass
    BASS_MIN = 0.1                              # ... when the bass band's loudest is this share of the loudest at all
    ONSET_LAG_S = 0.065                         # how late the short window shows an attack (calibrated)
    TAIL_HOLD_S = 0.20                          # extra hold for a chord that may be the last one's ringing tail
    SAME_ROOT_HOLD_S = 0.25                     # extra hold when only the quality would change, not the root
    DOWNGRADE_HOLD_S = 1.0                      # ... and when it would only drop a tone of the chord held
    # pedal: audio counts a pitch class as sounding above PEDAL_ON_AUDIO of the loudest note, and as HELD when it is
    # not a line's tail (struck before the newest note and fading); notes count it while its key is down or it was
    # struck within PEDAL_STRIKE_S, and as held while down, sustained, or struck again since the chord began. A run
    # survives gaps of PEDAL_GAP_S and becomes a pedal once it has lasted pedal_min_s over PEDAL_CHORDS different
    # chord roots, been held PEDAL_HELD of the time, sounded in all but PEDAL_MISS of the chord spans it ran through
    # (each span's first SPAN_SKIP_S, the last chord's tail, not counted) AND either clashed with the harmony for
    # PEDAL_CLASH of its held time (not a chord tone, or only the chord's colour: see _COLOUR) or held on as a drone
    # for PEDAL_DRONE_S over PEDAL_DRONE_ROOTS roots. A loop's common tone fits every chord it is in and leaves out a
    # chord or two: it is no pedal
    PEDAL_ON_AUDIO = 0.15
    PEDAL_STRIKE_S = 1.2
    PEDAL_GAP_S = {"audio": 1.2, "notes": 0.6}
    PEDAL_CHORDS, PEDAL_CLASH = 3, 0.15
    PEDAL_HELD = {"audio": 0.7, "notes": 0.85}
    PEDAL_MISS, SPAN_SKIP_S = 0.15, 0.35
    PEDAL_DRONE_S, PEDAL_DRONE_ROOTS = 16.0, 4
    RING_NOTE_ON = 0.5                          # notes: a released note ringing out counts as sounding above this
    RING_OUT_S = 0.6                            # notes: a released key (no sustain pedal) fades over this...
    DAMP_S = 0.12                               # ...and much faster once a new chord is struck:
    CHORD_NOTES, CHORD_SPREAD_S = 3, 0.06       # this many keys within this long
    # key: announced after KEY_FIRST_S of tonal time (with KEY_FIRST_CONF of the belief); changed when a rival leads
    # by KEY_MARGIN for KEY_DWELL_S in the long memory (key_tau), or by KEY_FAST_MARGIN for KEY_FAST_DWELL_S in the
    # last few seconds (KEY_FAST_TAU) -- the fast way only once the first key has stood KEY_SETTLE_S, when the
    # rival's own tonic chord has been heard lately (KEY_TONIC: at least 0.4 s of it, 1.25 x the key's own) and the
    # rival leads the two memories blended too (KEY_BLEND_MARGIN), unless the key's tonic has gone (under KEY_GONE).
    # A dominant 7th adds DOMINANT_PULL of evidence for the tonic it resolves to. Confidence is the key's share of a
    # softmax (KEY_SHARPNESS) over all 24 keys' fits, the fast memory blended with a long one never reset
    KEY_FIRST_S, KEY_MARGIN, KEY_DWELL_S = 3.0, 0.05, 4.0
    KEY_FAST_TAU, KEY_FAST_MARGIN, KEY_FAST_DWELL_S = 4.0, 0.20, 1.2
    KEY_TONIC, KEY_BLEND_MARGIN, KEY_GONE = (0.4, 1.25), 0.0, 0.1
    KEY_SETTLE_S = 6.0
    KEY_SHARPNESS, KEY_FIRST_CONF = 12.0, 0.12
    DOMINANT_PULL = 0.5

    def __init__(self, rate: int = 48000, hop: int = 512, *, frame_s: float = 0.02, p_stay: float = 0.985,
                 kappa: float = 40.0, n_floor: float = 0.50, min_hold_s: float = 0.12, bass_hold_s: float = 0.30,
                 hpss_s: float = 0.30, key_tau: float = 18.0, pedal_min_s: float = 8.0, pedal_ramp_s: float = 30.0,
                 gamma: float = 0.6, sim: str = "pearson"):
        """rate / hop: the audio clock (feed may still be given any block length). frame_s: the analysis period
        (audio frames are whole hops: at 48 kHz / 512 that is every second hop). p_stay / kappa: the HMM's
        stickiness and evidence sharpness, per 512-sample frame at 48 kHz (scaled to the actual clock). n_floor:
        the score a chord must beat to be named at all. min_hold_s / bass_hold_s: how long a new chord / a new
        bass under the same chord must lead before it is named. hpss_s: the past window of the harmonic split.
        key_tau: the key's memory (seconds). pedal_min_s / pedal_ramp_s: how long before a held pitch class is
        a pedal, and how long its pull takes to reach full strength. gamma: chroma compression. sim: 'pearson'
        (default) or 'cos' template matching."""
        if rate <= 0 or hop <= 0 or frame_s <= 0:
            raise ValueError("rate, hop and frame_s must be positive")
        if sim not in ("pearson", "cos"):
            raise ValueError("sim must be 'pearson' or 'cos'")
        self.rate, self.hop, self.frame_s = int(rate), int(hop), float(frame_s)
        self.p_stay, self.kappa, self.n_floor = p_stay, kappa, n_floor
        self.min_hold_s, self.bass_hold_s, self.hpss_s = min_hold_s, bass_hold_s, hpss_s
        self.key_tau, self.pedal_min_s, self.pedal_ramp_s = key_tau, pedal_min_s, pedal_ramp_s
        self.gamma, self.sim = gamma, sim
        self._source: Optional[str] = None
        templates = {True: _templates(True, gamma), False: _templates(False, gamma)}
        if sim == "pearson":
            templates = {k: v - v.mean(axis=1, keepdims=True) for k, v in templates.items()}
        self._templates = templates
        self._tnorm = {k: np.linalg.norm(v, axis=1) for k, v in templates.items()}
        nq = len(QUALITY_NAMES)
        self._tone_mask = np.zeros((12 * nq + 1, 12), dtype=bool)   # the last row is N: no tones
        for r in range(12):
            for qi, q in enumerate(QUALITY_NAMES):
                self._tone_mask[r * nq + qi, chord_tones(r, q)] = True
        self._tone_count = np.maximum(self._tone_mask.sum(axis=1), 1)
        self._tone_f = self._tone_mask[:-1].astype(float)
        self._not_tone = (~self._tone_mask[:-1]).astype(float).T   # (12, states): the pitch classes a chord lacks
        self._roots = np.repeat(np.arange(12), nq)
        # colours of one chord: the same root, one's tones containing the other's (C, C5, Cmaj7, Cadd9); N is a
        # rival of everything and everything of N
        tm = self._tone_mask.astype(int)
        common = tm @ tm.T
        cnt = tm.sum(axis=1)
        roots = np.append(self._roots, -1)
        self._nested = ((common == cnt[:, None]) | (common == cnt[None, :])) & (roots[:, None] == roots[None, :])
        # a held pitch class CLASHES with a chord when it is not one of its tones, or is only its colour: the 9th of
        # sus2 / add9, the 4th of sus4, the 7th of a seventh chord (what the held note itself would make of a triad)
        self._clash_mask = ~self._tone_mask[:-1]
        for r in range(12):
            for qi, q in enumerate(QUALITY_NAMES):
                for iv in _COLOUR.get(q, ()):
                    self._clash_mask[r * nq + qi, (r + iv) % 12] = True
        self._key_chord = self._tone_mask / self._tone_count[:, None]
        # (states, 24): the keys whose TONIC chord each state is -- a major-family chord on a major tonic, a minor
        # one on a minor tonic, a power chord or a sus half each way (N is nobody's)
        self._tonic_of = np.zeros((12 * nq + 1, 24))
        for r in range(12):
            for qi, q in enumerate(QUALITY_NAMES):
                both = q in ("5", "sus2", "sus4")
                if q not in ("min", "m7", "dim"):
                    self._tonic_of[r * nq + qi, KEYS.index((r, "major"))] = 0.5 if both else 1.0
                if q not in ("maj", "7", "maj7", "aug", "add9"):
                    self._tonic_of[r * nq + qi, KEYS.index((r, "minor"))] = 0.5 if both else 1.0
        for r in range(12):
            self._key_chord[r * nq + QUALITY_NAMES.index("7"), (r + 5) % 12] += self.DOMINANT_PULL
        self._support = np.full(12 * nq, 3.0)  # sounding tones per chord state, as of the last frame
        self._prior = np.tile(np.array([PRIOR[q] for q in QUALITY_NAMES]), 12)
        self._nstates = 12 * nq + 1             # the last state is N
        self._N = self._nstates - 1
        self._post = np.full(self._nstates, 1.0 / self._nstates)
        self._t = 0.0                           # seconds of input consumed
        self._frames = 0
        self._dt = 0.0
        # the decided chord (it starts at N, silently), the candidates waiting to replace it
        self._label = self._N
        self._label_bass: Optional[int] = None
        self._label_conf = 1.0
        self._cand: Optional[int] = None
        self._cand_since = 0.0
        self._cand_hold = min_hold_s
        self._cand_conf = 0.0
        self._clarity = 1.0                     # how clearly tonal the sound is (audio: from the tonality), 0..1
        self._unmasked = 1.0                    # ... and how little the bass note dwarfs the voices (audio)
        self._lone: Optional[int] = None
        self._full_t = 0.0                      # when the chord held last had two or more of its tones sounding
        self._label_t = 0.0                     # when the chord held was named
        self._bass_cand: Optional[int] = None
        self._bass_since = 0.0
        self._inst: Optional[int] = None        # what each frame says on its own, and since when
        self._inst_since = 0.0
        # key
        self._key_acc = np.zeros(12)
        self._key_fast = np.zeros(12)
        self._key_ever = np.zeros(12)
        self._key_decay: Optional[float] = None
        self._key: Optional[Tuple[int, str]] = None
        self._key_conf = 0.0
        self._key_rival: Optional[Tuple[int, str]] = None
        self._key_rival_since = 0.0
        self._tonic_acc = np.zeros(24)          # how much each key's tonic chord has been heard lately
        self._key_first_t = 0.0                 # when the first key was named
        self._tonal_s = 0.0
        self._pending_key_event = False
        # tension, pedal, resolution
        self.tension = 0.0
        self._tension_peak = 0.0
        self._tt_memo: Tuple[object, float] = (None, 0.0)
        self._run_start = np.full(12, -1.0)     # pedal runs: start time per pitch class (-1 = none)
        self._last_seen = np.full(12, -1e9)
        self._run_roots = np.zeros((12, 12), dtype=bool)   # the chord roots each run was heard over
        self._run_over = np.zeros(12)           # seconds each run has sounded over a chord ...
        self._run_clash = np.zeros(12)          # ... and of those, clashed with it (not one of its tones)
        self._run_held = np.zeros(12)           # seconds each run was really held (struck, or sounding fresh)
        self._held_since = np.full(12, -1.0)    # when each pitch class's current held streak began (-1 = none)
        self._held_last = np.full(12, -1e9)
        self._acc_held = np.zeros(12)           # seconds each pitch class has been held, ever (for span lookups)
        self._acc_ring = np.zeros((96, 12))     # ... its last ~2 s of frames
        self._acc_ring_t = np.full(96, -1e9)
        self._acc_pos = 0
        self._run_spans = np.zeros(12)          # chord spans each run has run through ...
        self._run_missed = np.zeros(12)         # ... and of those, the ones its note did not sound in
        self._span_onset: Optional[float] = None
        self._span_change: Optional[float] = None   # a chord change's onset, not yet accounted
        self._pedal: Optional[int] = None
        self._pedal_strength = 0.0
        self._last_held: Optional[np.ndarray] = None        # the last frame's held pitch classes (pedal)
        self._last_key_ev: Optional[np.ndarray] = None      # ... and its key evidence (a held chord's, repeated)
        # what the renderer reads
        self._chroma = np.zeros(12)
        self._bass = np.zeros(12)
        self._present = np.zeros(12)            # the pitch classes sounding as NOTES, 0..1
        self._energy = 0.0
        self._diss = 0.0
        self._pulse = 0.0
        self._pulse_ref = 1e-9
        self.tuning = 0.0                       # semitones off A440 (+ = sharp); audio only
        # notes front end
        self._held: Dict[int, list] = {}        # note -> [velocity 0..1, t_on, key_down, t_released, t_damped]
        self._sustain = False
        self._last_strike = np.full(12, -1e9)
        self._strike_energy = 0.0
        self._onsets: List[float] = []
        self._fe_ready = False                  # the audio front end is built on the first feed()

    # ---------------------------------------------------------------------------------------------- audio
    def _build_audio(self) -> None:
        self._decim = max(1, int(round(self.rate / 11500.0)))
        self._wrate = self.rate / self._decim
        if self._decim > 1:
            # a linear-phase FIR anti-alias filter: flat over the analysis band (up to 2.6 kHz), and whatever it
            # lets through above the new Nyquist folds back ABOVE that band; finite memory, so even a bad sample
            # could never poison it for longer than its length
            self._fir = firwin(12 * self._decim + 1, 0.80 / self._decim)
            self._fir_hist = np.zeros(len(self._fir) - 1)
        self._dphase = 0
        self._stride = max(1, int(round(self.frame_s * self.rate / self.hop)))
        self._dt = self.hop * self._stride / self.rate
        n_long = 1 << int(round(math.log2(self._wrate * 0.36)))     # 4096 at 11-12 kHz (~0.35 s)
        n_short = n_long // 2
        self._ns = n_short
        self._ring = np.zeros(n_long)
        self._win_l = np.hanning(n_long + 1)[:-1]
        self._win_s = np.hanning(n_short + 1)[:-1]
        self._norm_l = 2.0 / self._win_l.sum()
        self._norm_s = 2.0 / self._win_s.sum()
        self._df_l = self._wrate / n_long
        self._df_s = self._wrate / n_short
        f_lo = 440.0 * 2 ** ((self.LO_MIDI - 0.5 - 69) / 12)
        f_split = 440.0 * 2 ** ((self.SPLIT_MIDI - 0.5 - 69) / 12)
        f_hi = 440.0 * 2 ** ((self.HI_MIDI + 0.5 - 69) / 12)
        self._kl = (max(2, int(f_lo / self._df_l)), int(f_split / self._df_l) + 2)
        self._ks = (max(2, int(f_split / self._df_s) - 2), min(n_short // 2 - 1, int(f_hi / self._df_s) + 2))
        self._f_split = f_split
        self._nb = (self.HI_MIDI - self.LO_MIDI + 1) * self.BINS_PER_SEMI
        bin_midi = np.round(self.LO_MIDI + (np.arange(self._nb) - 1) / self.BINS_PER_SEMI).astype(int)
        self._bin_midi = bin_midi               # fine bin i is centred on MIDI LO + (i - 1) / BINS_PER_SEMI
        self._bin_pc = bin_midi % 12
        self._bass_bins = (bin_midi >= self.BASS_LO) & (bin_midi <= self.BASS_HI)
        bb = np.flatnonzero(self._bass_bins)
        self._bb = (int(bb[0]), int(bb[-1]) + 1)                   # the bass band, a contiguous run of fine bins
        self._hs = int(np.argmax(bin_midi >= self.HARM_LO))       # fine bins below this are the sub band
        self._c6 = int(np.argmax(bin_midi >= 84))                 # ... and from this one up, above the voices
        self._low_s = 1.0
        self._series_cache: Dict[int, tuple] = {}
        self._semi_pc = (self.LO_MIDI + np.arange(self._nb // self.BINS_PER_SEMI)) % 12
        self._semi_low = self.LO_MIDI + np.arange(self._nb // self.BINS_PER_SEMI) < 48     # below C3
        self._hk = max(5, int(round(self.hpss_s / self._dt))) | 1
        self._hring = np.zeros((self._hk, self._nb))
        self._hpos = 0
        self._tune_z = 0j
        self._chroma_s = np.zeros(12)
        self._bass_s = np.zeros(12)
        self._salience_s = np.zeros(12)
        self._sal_lo_s = np.zeros(12)
        self._sal_ring = np.zeros((max(1, int(round(self.FADE_S / self._dt))), 12))
        self._sal_pos = 0
        self._att_t = np.full(12, -1e9)                             # when each pitch class was last struck
        self._tonality = 0.0
        self._ref_energy = 1e-6
        nf = int(math.ceil(0.8 / self._dt)) + 1
        self._flux = np.zeros((nf, 12))
        self._flux_t = np.full(nf, -1e9)
        self._fpos = 0
        self._raw_prev = np.zeros(12)
        self._bflux = np.zeros((nf, 12))        # the same rise, in the bass band only
        self._braw_prev = np.zeros(12)
        self._a_chroma = 1.0 - math.exp(-self._dt / 0.06)
        self._a_bass = 1.0 - math.exp(-self._dt / self.BASS_TAU_S)
        self._a_sal = 1.0 - math.exp(-self._dt / 0.1)
        self._a_tonal = 1.0 - math.exp(-self._dt / 0.15)
        self._pending = 0
        self._tonal = False
        self._a1_s = 0.0
        self._hc_prev = np.zeros(12)
        hn = np.arange(2, 49)                                       # the bass's harmonics 2..48, as fine-bin offsets
        self._h_num = hn.astype(float)
        self._h_log = np.log(self._h_num)
        self._h_off = np.round(self.BINS_PER_SEMI * 12.0 * np.log2(hn)).astype(int)
        # the bass's 12ths (h = 3, 6, 12 ..) land on the fifth of the chord it usually carries, and a chord tone
        # there cannot be told from a brighter bass: they give up only half of what the law predicts
        self._h_share = np.where(np.round(12.0 * np.log2(hn)).astype(int) % 12 == 7, self.TWELFTH_SHARE, 1.0)
        offs = np.arange(-1, 5)[:, None]                            # search window: 1 bin flat .. 1-4 bins sharp
        self._h_win = (offs, offs <= 1 + (hn[None, :] >= 13) + (hn[None, :] >= 25) + (hn[None, :] >= 37))
        self._fe_ready = True

    def feed(self, block) -> List[dict]:
        """Feed audio: float samples in -1..1, mono (n,) or (n, channels), any length. Returns the events
        decided inside this block (usually none). A NaN, an Inf or an absurd sample is heard as silence."""
        if self._source not in (None, "audio"):
            raise ValueError("this ChordSense listens to notes; make another instance for audio")
        self._source = "audio"
        if not self._fe_ready:
            self._build_audio()
        x = np.asarray(block, dtype=np.float64)
        if x.ndim == 2:
            x = x.mean(axis=1)
        elif x.ndim != 1:
            raise ValueError("audio must be (n,) mono or (n, channels)")
        if x.size and not float(np.abs(x).max()) <= self.MAX_SAMPLE:          # NaN fails this comparison too
            # one NaN or Inf (a driver glitch, a bad plugin) must not silence the analysis for good, and nor may
            # an absurd value poison the loudness reference: a sample that is not audio is heard as silence
            x = np.where(np.abs(x) <= self.MAX_SAMPLE, x, 0.0)
        out: List[dict] = []
        period = self.hop * self._stride
        i, n = 0, len(x)
        while i < n:
            take = min(n - i, period - self._pending)
            self._push(x[i:i + take])
            i += take
            self._pending += take
            if self._pending >= period:
                self._pending = 0
                self._t += self._dt
                out.extend(self._audio_frame())
        return out

    def _push(self, chunk: np.ndarray) -> None:
        """Anti-alias, decimate (keeping the global sample grid across blocks) and append to the ring."""
        if self._decim > 1:
            xx = np.concatenate((self._fir_hist, chunk))
            self._fir_hist = xx[len(chunk):]
            y = np.convolve(xx, self._fir, mode="valid")[self._dphase::self._decim]
            self._dphase = (self._dphase - len(chunk)) % self._decim
        else:
            y = chunk
        m = len(y)
        if m == 0:
            return
        if m >= len(self._ring):
            self._ring[:] = y[-len(self._ring):]
        else:
            self._ring[:-m] = self._ring[m:]
            self._ring[-m:] = y

    def _lowest_weighted(self, band: np.ndarray) -> np.ndarray:
        """A bass-band spectrum as 12 pitch classes, the LOWEST significant note leading: everything above it
        fades by e per 4 semitones, so its own overtones and the left hand's chord tones count far less."""
        bmax = float(band.max())
        if bmax <= 0:
            return np.zeros(12)
        lowest = self._bin_midi[np.flatnonzero(band > self.BASS_SIG * bmax)[0]]
        wts = np.exp(-np.maximum(0, self._bin_midi - lowest) / 4.0)
        return np.bincount(self._bin_pc, weights=band * wts, minlength=12)

    @classmethod
    def _peaks(cls, x: np.ndarray, win: np.ndarray, norm: float, df: float, k0: int, k1: int,
               sinusoidality: bool = True):
        """Spectral peaks between bins k0..k1: (frequency, amplitude, sinusoidality 0..1), parabolic interpolation
        on log magnitude. Sinusoidality is how far a peak stands above the local level of the spectrum around it
        (the mean LOG magnitude over +-PROM_HALF bins, which a few strong partials barely move): a partial stands
        20-60 dB clear, while the peaks of noise (hiss, applause, a riser, a shaker) are mostly within ~10 dB of
        it, so noise never reads as tonal however long it lasts (see the tonality in _audio_frame)."""
        mag = np.abs(np.fft.rfft(x * win)) * norm
        seg = mag[k0 - 1:k1 + 1]
        mid = seg[1:-1]
        floor = max(1e-5, 0.003 * float(mid.max(initial=0.0)))
        k = np.flatnonzero((mid > seg[:-2]) & (mid >= seg[2:]) & (mid > floor))
        if k.size == 0:
            return np.zeros(0), np.zeros(0), np.zeros(0)
        w = cls.PROM_HALF if sinusoidality else 0
        lo, hi = max(0, k0 - 1 - w), min(len(mag), k1 + 1 + w)
        logm = np.log(mag[lo:hi] + 1e-12)
        kk = k + k0 - lo                                            # the peaks, in logm
        a, b, c = logm[kk - 1], logm[kk], logm[kk + 1]
        den = a - 2 * b + c
        p = np.minimum(np.maximum(np.where(den < -1e-12, 0.5 * (a - c) / np.where(den < -1e-12, den, -1.0), 0.0),
                                  -0.5), 0.5)
        if not sinusoidality:
            return (k + k0 + p) * df, np.exp(b - 0.25 * (a - c) * p), np.zeros(0)
        # the local level: a running mean of log magnitude (cumsum), centred on each peak
        cs = np.concatenate(([0.0], np.cumsum(logm)))
        a0 = np.maximum(kk - w, 0)
        a1 = np.minimum(kk + w + 1, hi - lo)
        prom_db = (b - (cs[a1] - cs[a0]) / (a1 - a0)) * _DB_PER_NEPER
        sinus = np.minimum(np.maximum((prom_db - cls.PROM_DB[0]) * (1.0 / (cls.PROM_DB[1] - cls.PROM_DB[0])), 0.0),
                           1.0)
        return (k + k0 + p) * df, np.exp(b - 0.25 * (a - c) * p), sinus

    def _audio_frame(self) -> List[dict]:
        ring = self._ring
        fl, al, _ = self._peaks(ring, self._win_l, self._norm_l, self._df_l, *self._kl, sinusoidality=False)
        fs, as_, ws = self._peaks(ring[-self._ns:], self._win_s, self._norm_s, self._df_s, *self._ks)
        keep_l, keep_s = fl < self._f_split, fs >= self._f_split
        f = np.concatenate((fl[keep_l], fs[keep_s]))
        amp = np.concatenate((al[keep_l], as_[keep_s]))
        # how much of the treble's peak energy is sinusoidal (the bass region's long window is left out: a kick's
        # sweep or a bass's attack there says nothing about whether the sound above is tonal)
        a_s = as_[keep_s]
        tot_s = float(a_s.sum())
        sinus_share = float(a_s @ ws[keep_s]) / tot_s if tot_s > 1e-12 else 0.0
        fine = np.zeros(self._nb)
        if f.size:
            midi = 69.0 + 12.0 * np.log2(f / 440.0)
            # tuning: a slowly decaying circular mean of the strong peaks' deviation from the A440 grid
            strong = (amp > 0.1 * amp.max()) & (f > 100) & (f < 2000)
            if strong.any():
                dev = midi[strong] - np.round(midi[strong])
                self._tune_z = 0.995 * self._tune_z + np.sum(amp[strong] * np.exp(2j * np.pi * dev))
                if abs(self._tune_z) > 1e-9:
                    self.tuning = float(np.angle(self._tune_z) / (2 * np.pi))
            idx = np.round((midi - self.tuning - self.LO_MIDI) * self.BINS_PER_SEMI).astype(int) + 1
            ok = (idx >= 0) & (idx < self._nb)
            fine = np.bincount(idx[ok], weights=amp[ok], minlength=self._nb)
        # causal harmonic / percussive split: the median over the PAST window in time against the median
        # across frequency; a soft mask, and never more than the frame itself holds (a fast release)
        # the ring holds each frame widened by one fine bin either way, so a partial whose interpolated pitch
        # jitters by a third of a semitone (noise under a low note) still counts as steady
        wide = fine.copy()
        np.maximum(wide[1:], fine[:-1], out=wide[1:])
        np.maximum(wide[:-1], fine[1:], out=wide[:-1])
        self._hring[self._hpos] = wide
        self._hpos = (self._hpos + 1) % self._hk
        h = np.partition(self._hring, self._hk // 2, axis=0)[self._hk // 2]
        p = median_filter(fine, size=17, mode="constant")
        h2 = h * h
        harm = np.minimum(fine, h) * (h2 / (h2 + p * p + 1e-18))
        # the sub band (below C2) holds a kick's tail as well as a sub bass. In the long window a kick swells and
        # fades with every beat (a 120 BPM kick's median there is ~25 times its minimum), a bass note holds: the sub
        # band keeps only what held through the WHOLE past window
        hs = self._hs
        med = harm
        harm = harm.copy()
        np.minimum(harm[:hs], self._hring[:, :hs].min(axis=0), out=harm[:hs])
        # onset evidence BEFORE the median (which delays the harmony on purpose): the per-pitch-class rise of the
        # raw spectrum, kept ~0.8 s so a decided chord can be back-dated to the attack that started it
        # (from C2 up: a kick's sweep and tail below it would back-date a chord to the kick)
        raw = np.sqrt(np.bincount(self._bin_pc[hs:], weights=fine[hs:], minlength=12))
        rise = np.maximum(raw - self._raw_prev, 0.0)
        self._raw_prev = raw
        self._flux[self._fpos] = rise
        braw = np.sqrt(self._lowest_weighted(np.where(self._bass_bins, fine, 0.0)))
        self._bflux[self._fpos] = np.maximum(braw - self._braw_prev, 0.0)
        self._braw_prev = braw
        self._flux_t[self._fpos] = self._t
        self._fpos = (self._fpos + 1) % len(self._flux_t)
        energy = float(harm.sum())
        # tonality: the share of the peak energy that is SINUSOIDAL (standing clear of the spectrum around it) times
        # the share that is STEADY (the harmonic split, judged from C2 up: a kick's tail is no reason to hear noise):
        # noise and drums ~0, a chord 0.5-0.8 even under drums. With hysteresis: 'tonal' switches on above TONAL_ON
        # and off only below TONAL_OFF, so a chord does not flicker to N and back at a drum fill, and a hiss or a
        # riser never reaches the chords
        total = float(fine[hs:].sum())
        steady = float(harm[hs:].sum()) / total if total > 1e-9 else 0.0
        # the bass NOTE (its fundamental and its harmonic series) comes out of the harmony: a loud or bright bass
        # must not turn maj7 into 5; it is heard in the bass chroma (the bass note, inversions, slash chords)
        upper, bpc, a1, voices = self._split_bass(harm, med)
        # ... and the register: chord voices live below C6. A sound whose harmonic energy sits mostly above it (an
        # 808 hat's metallic partials, a cymbal) must be that much more clearly tonal to be heard as chords
        utot = float(upper.sum())
        if utot > 1e-12:
            self._low_s += self._a_tonal * (float(upper[:self._c6].sum()) / utot - self._low_s)
        reg = min(1.0, max(self.REGISTER[1], self._low_s / self.REGISTER[0])) ** 2
        self._tonality += self._a_tonal * (sinus_share * steady * reg - self._tonality)
        if self._tonal and self._tonality < self.TONAL_OFF:
            self._tonal = False
        elif not self._tonal and self._tonality > self.TONAL_ON:
            self._tonal = True
        self._clarity = _unit(self._tonality / self.CLEAR_TONALITY)
        # note salience: each semitone of the voices minus what the overtones of the voices below it explain, so
        # dissonance and pedals are heard in the NOTES, not in their 12ths and 17ths. The bass's own series is already
        # out of the voices: explaining the voices by ITS overtones too took them twice (under a loud bass no voice
        # was left sounding)
        semi_v = voices.reshape(-1, self.BINS_PER_SEMI).sum(axis=1)
        expl = np.zeros_like(semi_v)
        for off, g in self._OVERTONES:
            expl[off:] += g * semi_v[:-off]
        sv = np.maximum(semi_v - expl, 0.0)
        sal_lo = np.bincount(self._semi_pc, weights=np.where(self._semi_low, sv, 0.0), minlength=12)
        self._sal_lo_s += self._a_sal * (sal_lo - self._sal_lo_s)
        self._salience_s += self._a_sal * (np.bincount(self._semi_pc, weights=sv, minlength=12) - self._salience_s)
        self._a1_s += self._a_sal * (a1 - self._a1_s)
        chroma = np.bincount(self._bin_pc, weights=upper, minlength=12)
        bass = self._lowest_weighted(np.where(self._bass_bins, harm, 0.0)) if bpc is not None else np.zeros(12)
        self._chroma_s += self._a_chroma * (chroma - self._chroma_s)
        self._bass_s += self._a_bass * (bass - self._bass_s)
        # the pulse: the harmonic part's attack strength (after the split, so drums alone never pulse)
        hc = np.sqrt(np.bincount(self._bin_pc, weights=harm, minlength=12))
        self._set_pulse(float(np.maximum(hc - self._hc_prev, 0.0).sum()) if self._tonal else 0.0)
        self._hc_prev = hc
        # silence is relative to the music (a slow peak follower) with an absolute floor
        self._ref_energy = max(energy, self._ref_energy * math.exp(-self._dt / 8.0), 1e-6)
        quiet = energy < max(2e-4, 0.03 * self._ref_energy)
        # the notes sounding (0..1): the upper voices against the loudest of them, counted only when they are
        # more than a residue of the bass's own overtones; and the bass note itself
        smax = max(float(self._salience_s.max()), self.VOICE_FLOOR * self._a1_s, 1e-12)
        dom = self._a1_s / (float(self._salience_s.max()) + self._a1_s + 1e-12)   # how much the bass dwarfs the voices
        self._unmasked = 1.0 - self.CONF_MASK[2] * _unit((dom - self.CONF_MASK[0]) / self.CONF_MASK[1])
        present = self._salience_s / smax
        # a voice in the bass's register (below C3) beside the bass note is mostly the last bass note ringing on: it
        # counts against the bass note itself (LOW_VOICE of it), not against the voices (a bass line is no dyads)
        hi = np.maximum(self._salience_s - self._sal_lo_s, 0.0)
        present = np.maximum(hi / smax, self._sal_lo_s / max(smax, self.LOW_VOICE * self._a1_s))
        # a line's tail: a note that was struck BEFORE the newest note sounding (by more than SYNC_S), and is now
        # fading (it kept under FADE of its level of FADE_S ago) -- the previous note of a melody or a bass line
        # ringing into the next. A new chord is not built from it unless it is still loud. Notes struck together
        # fade together and stay one chord (a Rhodes chord decays); a held or sustained note does not fade
        level = self._raw_prev * self._raw_prev                     # each pitch class's level (the plain spectrum)
        then = self._sal_ring[self._sal_pos].copy()
        self._sal_ring[self._sal_pos] = level
        self._sal_pos = (self._sal_pos + 1) % len(self._sal_ring)
        # (rising: still being struck -- by a real part of the sound, not a partial of another note landing there)
        struck = (level > self.RISE * then) & (level - then > 0.1 * float(level.max()))
        self._att_t[struck] = self._t
        fading = level < self.FADE[0] * then
        sounding = present > self.NOTE_ON
        newest = float(self._att_t[sounding].max()) if sounding.any() else -1e9
        loud = self._salience_s >= self.FADE[1] * max(smax, self._a1_s)     # against the bass note too
        old = fading & (self._att_t < newest - self.SYNC_S)
        tail = old & ~loud
        fresh = np.where(tail, np.minimum(present, 0.5 * self.NOTE_ON), present)
        bnote, lone = self._bass_note(self._bass_s, self._chroma_s)
        if bnote is not None:
            present[bnote] = 1.0
            if not fading[bnote]:
                fresh[bnote] = 1.0                                  # (a bass note fading out is the line moving on)
        # when little of the energy is harmonic (drums, noise, applause), 'N' gets the benefit of the doubt
        n_boost = self.N_BOOST[1] * max(0.0, self.N_BOOST[0] - self._tonality) if self._tonal else 2.0
        return self._step(self._harmony(self._chroma_s, bnote), self._bass_s.copy(), energy, quiet, True, present,
                          present > self.PEDAL_ON_AUDIO, n_boost, lone,
                          None if lone is None else self._harmony(self._chroma_s, None), fresh,
                          (present > self.PEDAL_ON_AUDIO) & ~old)

    def _bass_note(self, bass: np.ndarray, upper: np.ndarray) -> Tuple[Optional[int], Optional[int]]:
        """(the bass note's pitch class or None, the same when it is LONE: the voices above do not carry it)."""
        bsum = float(bass.sum())
        if bsum <= 1e-12:
            return None, None
        bp = int(np.argmax(bass))
        if bass[bp] < 0.4 * bsum:
            return None, None
        return bp, (bp if upper[bp] < 0.25 * float(upper.max()) else None)

    def _harmony(self, upper: np.ndarray, bnote: Optional[int]) -> np.ndarray:
        """The chroma the chords are scored on: the upper voices, and the bass note counted as a chord tone at half
        the strongest voice's weight (unless the voices already carry it more), compressed by gamma."""
        c = np.maximum(upper, 0.0)
        if bnote is not None:
            c = c.copy()
            c[bnote] = max(c[bnote], 0.5 * float(c.max()))
        return c ** self.gamma

    def _split_bass(self, harm: np.ndarray, med: np.ndarray) -> Tuple[np.ndarray, Optional[int], float, np.ndarray]:
        """(upper, bass pitch class, fundamental amplitude, voices): the harmonic spectrum with the bass note's own
        harmonic series taken out (see _series_take). The bass note is the lowest significant peak of the bass band
        in `harm` (where the sub band holds only what held through the past window: a kick's tail is not the bass);
        its series is read from `med` (the plain harmonic split). In `upper` (the chroma) the 12ths give up only
        half (the fifth of the chord usually sits there); in `voices` (the notes sounding) all of it, so a bass
        note's own 12th is never a second note (one note is not a power chord)."""
        b0, b1, hs = self._bb[0], self._bb[1], self._hs
        band = harm[b0:b1]
        bmax = float(band.max())
        if bmax <= self.BASS_MIN * float(harm.max()):
            upper = harm.copy()
            upper[:hs] = 0.0                                        # nothing in the bass band worth the name
            return upper, None, 0.0, upper
        i0 = self._lowest_peak(harm, band, bmax)
        a1 = float(med[i0])
        upper = harm.copy()
        upper[i0] = 0.0
        full, half = self._series_take(i0, a1, med)
        # a source in the sub band the bass note is not (yet): a new sub note before it has held through the window,
        # or a kick's tail. It is not the bass, but its partials are not voices either
        mband = med[b0:hs]
        if mband.size and float(mband.max()) > self.BASS_SIG * float(med[b0:b1].max()):
            i1 = self._lowest_peak(med, mband, float(mband.max()))
            if abs(i1 - i0) > 1:
                upper[i1] = 0.0
                f1, h1 = self._series_take(i1, float(med[i1]), med)
                full, half = full + f1, half + h1
        voices = np.maximum(upper - full, 0.0)
        np.maximum(upper - half, 0.0, out=upper)
        upper[:hs] = 0.0                                            # the sub band is the bass's alone
        voices[:hs] = 0.0
        return upper, int(self._bin_pc[i0]), a1, voices

    def _lowest_peak(self, x: np.ndarray, band: np.ndarray, bmax: float) -> int:
        """The fine bin of the lowest significant peak of a band starting at the bass band's first bin."""
        i0 = self._bb[0] + int(np.argmax(band > self.BASS_SIG * bmax))
        if i0 + 1 < self._nb and x[i0 + 1] > x[i0]:
            i0 += 1                                                 # the peak, not its shoulder
        return i0

    def _series_take(self, i0: int, a1: float, src: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """What the harmonic series of a bass note at fine bin i0 (fundamental a1) takes from the spectrum src: (all
        of it, with its 12ths giving up only TWELFTH_SHARE). Its partials' strength follows a power law a1 * h^-p,
        one law for the odd partials and one for the even (a square bass has no even partials at all: one law for
        both read it as a dull bass and left its 3rd, 5th, 7th .. in the harmony), read from the cleanest partials
        that are there (a hum or a low-passed sub stops after a few); the even partials are never taken as BRIGHTER
        than the odd (they are the root's octaves and the 12ths, where the chord's own root and fifth sit). Each
        partial gives up at most what its law predicts, so the chord's own partials stay."""
        zero = np.zeros(self._nb)
        cand, valid, cols, hlog, share, low, odd = self._series(i0)
        if not cols.size or a1 <= 0:
            return zero, zero
        vals = np.where(valid, src[cand], -1.0)
        j = np.argmax(vals, axis=0)
        obs = np.maximum(vals[j, cols], 0.0)
        ok = obs > self.LAW_FLOOR * a1
        p_odd = self._law(a1, obs, hlog, ok & low & odd, self.LAW_Q)
        p_even = self._law(a1, obs, hlog, ok & low & ~odd, self.LAW_Q)
        if p_odd is None and p_even is None:
            return zero, zero
        if p_odd is None:
            p_odd = p_even
        p_even = p_odd if p_even is None else max(p_even, p_odd)
        take = np.minimum(obs, a1 * np.exp(-np.where(odd, p_odd, p_even) * hlog))
        idx = cand[j, cols]
        return (np.bincount(idx, weights=take, minlength=self._nb),
                np.bincount(idx, weights=take * share, minlength=self._nb))

    @staticmethod
    def _law(a1: float, obs: np.ndarray, hlog: np.ndarray, m: np.ndarray, quantile: float = 0.8) -> Optional[float]:
        """The power-law exponent p (a1 * h^-p) read from the CLEANEST of the partials m: the 80th percentile of their
        exponents (a chord tone landing on a partial only makes that one look brighter); None with fewer than two."""
        if int(m.sum()) < 2:
            return None
        ph = np.log(a1 / obs[m]) / hlog[m]
        ph.sort()
        q = quantile * (ph.size - 1)                                # the 80th percentile, interpolated
        i = int(q)
        p = float(ph[i] + (ph[min(i + 1, ph.size - 1)] - ph[i]) * (q - i))
        return min(max(p, 0.5), 4.0)

    def _series(self, i0: int):
        """The bass note's harmonic series seen from fine bin i0 (cached per bin): for harmonics 2..48 inside the
        range, the candidate bins of each (a bin flat to 1-4 bins sharp: a string's partials run sharp, more so
        the higher they go) and which are valid, their columns, log h, the share each gives up, and h <= 12."""
        c = self._series_cache.get(i0)
        if c is None:
            idx = i0 + self._h_off
            ok = idx < self._nb
            cand = idx[ok][None, :] + self._h_win[0]
            valid = self._h_win[1][:, ok] & (cand < self._nb)
            c = (np.minimum(cand, self._nb - 1), valid, np.arange(int(ok.sum())), self._h_log[ok],
                 self._h_share[ok], self._h_num[ok] <= self.LAW_MAX_H, self._h_num[ok] % 2 == 1)
            self._series_cache[i0] = c
        return c

    # ---------------------------------------------------------------------------------------------- notes
    def feed_notes(self, events: Iterable, now: Optional[float] = None) -> List[dict]:
        """Feed played notes. Each event is a dict {t, note, vel} (vel 0 = note off, or give `on`: bool), a dict
        {t, sustain: 0..127} for the sustain pedal (CC64), or a tuple (t, note, vel); times in seconds, in
        order. `now` advances the clock past the last event: call feed_notes([], now=t) to let time pass."""
        if self._source not in (None, "notes"):
            raise ValueError("this ChordSense listens to audio; make another instance for notes")
        self._source = "notes"
        if self._dt == 0.0:
            self._dt = self.frame_s
        out: List[dict] = []
        for ev in events:
            t = float(ev["t"] if isinstance(ev, dict) else ev[0])
            if not math.isfinite(t):
                raise ValueError("a note event's time must be a finite number of seconds")
            self._advance(t, out)
            self._apply_note(ev, t)
        if now is not None:
            if not math.isfinite(float(now)):
                raise ValueError("now must be a finite number of seconds")
            self._advance(float(now), out)
        return out

    def _advance(self, until: float, out: List[dict]) -> None:
        """Step the notes clock to `until`, one frame at a time while anything sounds. Once nothing does and the
        state has settled (no chord, no pedal run, nothing pending), the rest of an idle gap is one analytic jump:
        a call after half an hour of silence costs what a call after a second does."""
        while self._t + self._dt <= until:
            if not self._held and self._settled():
                n = int(math.floor((until - self._t) / self._dt + 1e-9))
                if n > 0:
                    self._jump(n)
                return
            if self._held and self._steady_held():
                # keys held down and nothing else moving (a stuck note, a held organ chord): every frame would be
                # the same frame, so the gap is jumped too, all but its last frame, which runs as usual
                n = int(math.floor((until - self._t) / self._dt + 1e-9)) - 1
                if n > 50:
                    self._steady_jump(n)
                    continue
            self._t += self._dt
            out.extend(self._notes_frame())

    def _settled(self) -> bool:
        """True when a silent frame can no longer change anything but the clock and the decays."""
        return (self._label == self._N and self._cand is None and self._pedal is None
                and not self._pending_key_event and self._strike_energy == 0.0
                and bool((self._run_start < 0).all()) and self._post[self._N] > 0.999)

    def _steady_held(self) -> bool:
        """True when the held notes can no longer change: every one of them down, struck more than 3 s ago (its
        level at the floor a held key keeps), no chord, bass or key change pending, the chord held a second."""
        t = self._t
        for vel, t_on, key_down, t_off, t_damp in self._held.values():
            if not key_down or t_off is not None or t - t_on < 3.0:
                return False
        return (self._cand is None and self._bass_cand is None and not self._pending_key_event
                and self._strike_energy == 0.0 and t - self._label_t >= 1.0 and self._last_held is not None
                and (self._label == self._N or self._key is not None))      # (a first key is still to come)

    def _steady_jump(self, n: int) -> None:
        """n identical frames with keys held: the clock moves, the key memories take n more of the same evidence
        (a geometric sum), the pedal runs n more frames of the same notes, the tension relaxes to its target."""
        dt = self._dt
        span = n * dt
        self._t += span
        self._frames += n
        t = self._t
        if self._key_decay is not None and self._last_key_ev is not None and self._label != self._N:
            for name, d in (("_key_acc", self._key_decay), ("_key_fast", self._key_fast_decay),
                            ("_key_ever", self._key_decay)):
                dn = d ** n
                setattr(self, name, dn * getattr(self, name) + self._last_key_ev * (1.0 - dn) / (1.0 - d))
            dn = self._key_fast_decay ** n
            self._tonic_acc = dn * self._tonic_acc + dt * self._tonic_of[self._label] * (1.0 - dn) / (1.0 - self._key_fast_decay)
            self._tonal_s += span
        held = self._last_held
        live = self._run_start >= 0
        self._last_seen[held] = t
        self._held_last[held] = t
        self._run_held[held & live] += span
        self._acc_held[held] += span
        self._acc_ring[self._acc_pos] = self._acc_held
        self._acc_ring_t[self._acc_pos] = t
        self._acc_pos = (self._acc_pos + 1) % len(self._acc_ring_t)
        if self._label != self._N:
            self._run_over[held] += span
            through = (self._held_since >= 0) & (self._held_since <= self._label_t)
            self._run_clash[held & through & self._clash_mask[self._label]] += span
        target = self._tension_now(*self._state_rq(self._label))
        tau = 0.35 if target > self.tension else 0.8
        self.tension = target + (self.tension - target) * math.exp(-span / tau)
        self._tension_peak = max(self.tension, self._tension_peak * math.exp(-span / 6.0))
        self._pulse_ref = max(self._pulse_ref * math.exp(-span / 5.0), 1e-9)
        self._pulse = 0.0

    def _jump(self, n: int) -> None:
        """n silent frames at once: only the clock and the exponential decays move."""
        span = n * self._dt
        self._t += span
        self._frames += n
        self.tension *= math.exp(-span / 0.8)
        self._tension_peak = max(self.tension, self._tension_peak * math.exp(-span / 6.0))
        self._pulse_ref = max(self._pulse_ref * math.exp(-span / 5.0), 1e-9)
        self._pulse = 0.0
        self._label_conf = 1.0 - (1.0 - self._label_conf) * math.exp(-span / self.CONF_TAU_S)

    def _apply_note(self, ev, t: float) -> None:
        if isinstance(ev, dict):
            if "sustain" in ev:
                self._sustain = float(ev["sustain"]) >= 64
                if not self._sustain:
                    for v in self._held.values():                  # pedal up: released keys start to ring out
                        if not v[2] and v[3] is None:
                            v[3] = t
                return
            note = int(ev["note"])
            vel = float(ev.get("vel", 100))
            on = bool(ev.get("on", vel > 0))
        else:
            note, vel = int(ev[1]), float(ev[2])
            on = vel > 0
        if on:
            # a new CHORD attack (CHORD_NOTES keys within CHORD_SPREAD_S) damps whatever was only ringing out
            # (released, no sustain pedal): the hand has moved. A single melody note leaves the harmony ringing
            self._onsets = [x for x in self._onsets if t - x <= self.CHORD_SPREAD_S] + [t]
            if len(self._onsets) >= self.CHORD_NOTES:
                for v in self._held.values():
                    if v[3] is not None and v[4] is None:
                        v[4] = t
            level = max(0.05, min(1.0, vel / 127.0))
            self._held[note] = [level, t, True, None, None]
            self._last_strike[note % 12] = t
            self._strike_energy += level
        elif note in self._held:
            self._held[note][2] = False
            if not self._sustain:
                self._held[note][3] = t                            # released: it rings out, never cut dead

    def _notes_frame(self) -> List[dict]:
        t = self._t
        chroma = np.zeros(12)
        down = np.zeros(12, dtype=bool)
        holding = np.zeros(12, dtype=bool)      # a key down or on the sustain pedal (not only ringing out)
        lowest = lowest_ringing = None
        dead = []
        for note, (vel, t_on, key_down, t_off, t_damp) in self._held.items():
            level = self._level_of(note, t)
            if key_down:
                down[note % 12] = True
            if level < 0.03:
                dead.append(note)
                continue
            chroma[note % 12] += level
            if t_off is None:
                holding[note % 12] = True
            if level > 0.12:
                if t_off is None and (lowest is None or note < lowest):           # held, or on the pedal
                    lowest = note
                elif t_off is not None and (lowest_ringing is None or note < lowest_ringing):
                    lowest_ringing = note
        for note in dead:
            del self._held[note]
        # the bass is the lowest note still held (or sustained); only when none is, the lowest one ringing out
        bass = np.zeros(12)
        if lowest is None:
            lowest = lowest_ringing
        energy = float(chroma.sum())
        present = chroma / chroma.max() if energy > 0 else np.zeros(12)
        fresh = present
        if holding.any():
            # while keys are held, a note only ringing out after its release is the tail of a melody, not a voice:
            # a new chord counts it only while it is still loud (a legato line's last note is not its next chord)
            fresh = np.where(holding | (present >= self.RING_NOTE_ON), present, np.minimum(present, 0.5 * self.NOTE_ON))
        upper, bnote, lone = chroma, None, None
        if lowest is not None:
            bnote = lowest % 12
            bass[bnote] = 1.0
            # the voices above the bass: the same rule as audio (the bass is a chord tone at half weight, and a
            # bass the voices do not carry is a lone bass under the chord)
            upper = chroma.copy()
            upper[bnote] = max(0.0, upper[bnote] - self._level_of(lowest, t))
            if upper.max() > 0 and upper[bnote] < 0.25 * upper.max():
                lone = bnote
        # for the pedal a note is ON while its key is down or it was struck within PEDAL_STRIKE_S: what the
        # player keeps playing, not what merely rings
        pedal_on = down | (t - self._last_strike < self.PEDAL_STRIKE_S)
        # ... and HELD: down, on the sustain pedal, or struck again since the chord under it began (a note of the
        # previous chord struck a moment ago is that chord's tail, not a note held over this one)
        held = down | holding | (self._last_strike >= max(self._label_t, t - self.PEDAL_STRIKE_S))
        self._set_pulse(self._strike_energy)
        self._strike_energy = 0.0
        return self._step(self._harmony(upper, bnote), bass, energy, energy < 0.05, False, present, pedal_on,
                          0.0, lone, None if lone is None else self._harmony(upper, None), fresh, held)

    def _level_of(self, note: int, t: float) -> float:
        """How loud a struck note still sounds: a string fades; a held key keeps sounding (organ, pads); a released
        one rings out, and is damped fast once a new chord is struck."""
        vel, t_on, key_down, t_off, t_damp = self._held[note]
        level = vel * math.exp(-(t - t_on) / 2.5)
        if key_down:
            return max(level, 0.35 * vel)
        if t_off is not None:
            level *= math.exp(-(t - t_off) / self.RING_OUT_S)
            if t_damp is not None:
                level *= math.exp(-(t - t_damp) / self.DAMP_S)
        return level

    def _set_pulse(self, x: float) -> None:
        """The harmonic attack strength of this frame, 0..1 against a slowly decaying peak (~5 s)."""
        self._pulse_ref = max(x, self._pulse_ref * math.exp(-self._dt / 5.0), 1e-9)
        self._pulse = x / self._pulse_ref

    # ---------------------------------------------------------------------------------------------- shared
    def _match(self, c: np.ndarray, harmonics: bool) -> np.ndarray:
        """Template similarity of every chord state with a compressed chroma (Pearson or cosine)."""
        if self.sim == "pearson":
            c = c - c.mean()
        nrm = float(np.linalg.norm(c))
        if nrm < 1e-12:
            return np.zeros(self._nstates - 1)
        return (self._templates[harmonics] @ c) / (self._tnorm[harmonics] * nrm)

    def _scores(self, c: np.ndarray, b: np.ndarray, harmonics: bool, present: Optional[np.ndarray] = None,
                lone: Optional[int] = None, upper: Optional[np.ndarray] = None,
                fresh: Optional[np.ndarray] = None) -> np.ndarray:
        """The score of every chord state (and of N, last) for a compressed chroma c and a bass distribution b.
        present: the pitch classes sounding as notes; a chord needs at least two of its own tones among them (one
        note and its overtones is a melody note, not a power chord). lone: the bass's pitch class when the voices
        above do not carry it, and upper: the voices' compressed chroma without it -- a chord over a lone foreign
        bass can then read as a slash chord (G/C), not as whatever chord the bass could be the root of (Csus2).
        fresh: `present` without the notes that are only a line's ringing tail -- what a NEW chord must be built
        from; the chord already named is judged by everything still sounding (a decaying piano chord is still it)."""
        s = np.empty(self._nstates)
        s[:-1] = self._match(c, harmonics)
        sounding = None if present is None else (present > self.NOTE_ON).astype(float)
        newly = sounding if (fresh is None or (self.TAILS_FROM_N_ONLY and self._label != self._N))             else (fresh > self.NOTE_ON).astype(float)
        bs = float(b.sum())
        if bs > 1e-12:
            bd = b / bs
            in_chord = self._tone_mask[:-1] @ bd                    # bass mass on the chord's own tones
            root_b = bd[self._roots]
            bass_term = 0.10 * root_b + 0.05 * (in_chord - root_b)
            s[:-1] += bass_term - self.FOREIGN_BASS[0] * (1.0 - in_chord)
            if lone is not None and upper is not None:
                # a lone bass is EITHER a chord tone (counted at half weight: C2 under E-G-B is Cmaj7) -- and then
                # the chord must explain every voice above it -- OR a slash under the voices (G-B-D over C2 is G/C,
                # not Csus2): each chord takes whichever explains the sound better
                if sounding is not None:
                    voices = sounding.copy()
                    voices[lone] = 0.0
                    s[:-1] -= self.UNEXPLAINED * (voices @ self._not_tone)
                slash = self._match(upper, harmonics) + bass_term - self.FOREIGN_BASS[1] * (1.0 - in_chord)
                np.maximum(s[:-1], slash, out=s[:-1])
        s[:-1] += self._prior
        if sounding is not None:
            self._support = self._tone_f @ newly                    # how many of each chord's tones are sounding
            if self._label != self._N:
                self._support[self._label] = float(self._tone_f[self._label] @ sounding)
            s[:-1] -= self.FEW_NOTES * (self._support < 2)
        s[-1] = self.n_floor
        return s

    def _step(self, c: np.ndarray, b: np.ndarray, energy: float, quiet: bool, harmonics: bool,
              present: np.ndarray, pedal_on: np.ndarray, n_boost: float = 0.0,
              lone: Optional[int] = None, upper: Optional[np.ndarray] = None,
              fresh: Optional[np.ndarray] = None, pedal_held: Optional[np.ndarray] = None) -> List[dict]:
        """One frame of the shared back end. c: compressed chroma; b: bass distribution; present: the pitch
        classes sounding as notes (0..1); pedal_on: the pitch classes the pedal detector counts as held;
        n_boost: extra weight for 'no chord' on non-tonal frames; lone / upper: a bass pitch class the voices do
        not carry and the voices' chroma without it; fresh: present without a line's ringing tails (see _scores)."""
        t = self._t
        self._frames += 1
        self._chroma, self._bass, self._energy, self._present = c, b, energy, present
        self._lone = lone
        s = self._scores(c, b, harmonics, present, lone, upper, fresh)
        s[-1] += n_boost
        if quiet:
            s[-1] = 10.0                                            # silence: N, decisively
        elif self._label != self._N:
            # one or two notes left sounding, all of them tones of the chord being held (a melody note over the
            # chord's tail, a staccato comp's held top note, an arpeggio between its notes): that is no evidence for
            # another chord, nor for none -- the chord holds, for up to LONE_HOLD_S after it last sounded in full. A
            # note that is NOT one of its tones, silence or noise still end it
            on = present > self.NOTE_ON
            n_on = int(on.sum())
            if self._support[self._label] >= min(3, self._tone_count[self._label]):
                self._full_t = t
            elif ((not harmonics or self._tonal) and 1 <= n_on <= 2 and t - self._full_t <= self.LONE_HOLD_S
                    and self._full_t - self._label_t >= self.LONE_MIN_S
                    and not (on & ~self._tone_mask[self._label]).any()):
                s[self._label] = max(float(s[self._label]), float(s[:-1].max()) + 0.02, float(s[-1]) + 0.05)
        # online forward filter (a causal HMM): sticky self-transition, uniform jumps, emission exp(kappa * score).
        # p_stay and kappa are stated per REFERENCE frame and scaled to this clock, so they mean the same thing
        # in seconds at any rate, hop or frame_s
        k = self._dt / _REF_DT
        p_stay = self.p_stay ** k
        n = self._nstates
        post = p_stay * self._post + (1.0 - p_stay) * (1.0 - self._post) / (n - 1)
        post = post * np.exp(self.kappa * k * (s - s.max()))
        tot = float(post.sum())
        post = post / tot if tot > 0 else np.full(n, 1.0 / n)
        np.maximum(post, 1e-12, out=post)
        self._post = post
        inst = int(np.argmax(s))
        if inst != self._inst:
            self._inst, self._inst_since = inst, t
        best = int(np.argmax(post))
        # confidence = the agreement margin: how far the frames' score for a reading leads the best OTHER reading,
        # averaged over the last ~CONF_TAU_S (1.0 = a clear CONF_MARGIN lead, 0 = a coin toss or worse)
        a_conf = 1.0 - math.exp(-self._dt / self.CONF_TAU_S)
        out: List[dict] = []
        if best != self._label:
            # a new chord must lead the posterior clearly for min_hold_s, AND be what the frame itself says right
            # now: a chord passing through on its way to the next (G7 fading into Fmaj7 reads Fadd9 for a moment)
            # leads the posterior only briefly
            if best != self._cand:
                self._cand, self._cand_since = best, t
                self._cand_hold = self.min_hold_s + self._extra_hold(best)
                self._cand_conf = self._margin(s, best)
            else:
                self._cand_conf += a_conf * (self._margin(s, best) - self._cand_conf)
            pb = float(post[best])
            # two notes are not yet a chord: a reading with only two of its tones sounding (a power chord, a melody
            # note over the last one's tail) must hold DYAD_HOLD_S longer
            hold = self._cand_hold + (self.DYAD_HOLD_S if best != self._N and self._support[best] < 3 else 0.0)
            if (t - self._cand_since >= hold and pb >= 0.55 and inst == best
                    and pb > post[self._label] + 0.2):
                out.extend(self._change(best, self._new_bass(best, b), self._cand_conf))
        else:
            self._cand = None
            self._label_conf += a_conf * (self._margin(s, best) - self._label_conf)
            if best != self._N:
                # the same chord over a new bass (C -> C/E) has its own, slower hold, so a re-struck chord's bass
                # does not flicker
                nb = self._bass_of(best, b)
                if nb == self._label_bass:
                    self._bass_cand = None
                elif nb != self._bass_cand:
                    self._bass_cand, self._bass_since = nb, t
                elif t - self._bass_since >= self.bass_hold_s:
                    out.extend(self._change(best, nb, self._label_conf, bass_only=True))
        self._update_key(c, harmonics, quiet)
        out.extend(self._update_tension(present, pedal_on, quiet, pedal_held))
        return out

    def _margin(self, s: np.ndarray, state: int) -> float:
        """This frame's agreement with a reading, 0..1: how far its score leads the best RIVAL reading's (a chord
        that is not merely a thinner or richer colour of it: C's rivals are Am, Em or Am7, not Cmaj7 or C5),
        times the share of its tones sounding as notes (a dyad is two thirds of a triad), times how clearly tonal
        the sound is (noise and drums over the chord lower it)."""
        rival = float(np.max(np.where(self._nested[state], -np.inf, s)))
        m = _unit((float(s[state]) - rival) / self.CONF_MARGIN)
        if state != self._N:
            m *= min(1.0, float(self._support[state]) / float(self._tone_count[state])) * self._clarity
            m *= self._unmasked
        return m

    def _bass_of(self, state: int, b: np.ndarray) -> Optional[int]:
        """The bass to name with a chord: the dominant bass pitch class when it is a chord tone, or when it is a
        LONE bass under the chord (a pedal: G/C); else the root."""
        if state == self._N:
            return None
        root = int(self._roots[state])
        bs = float(b.sum())
        if bs <= 1e-12:
            return root
        bd = b / bs
        pc = int(np.argmax(bd))
        if bd[pc] < 0.4:
            return root
        if not self._tone_mask[state, pc]:
            return pc if pc == self._lone and bd[pc] >= 0.5 else root
        if pc != root and bd[root] > 0.6 * bd[pc]:
            return root                                             # the root nearly as loud: no slash
        return pc

    def _extra_hold(self, state: int) -> float:
        """How much longer than min_hold_s a candidate must lead. Same root, only the colour changing: real mixes
        thin and thicken a chord all the time (SAME_ROOT_HOLD_S); a THINNER reading of the chord being held (Am7 ->
        Am, G7 -> G5: an arpeggio between its 7ths) waits DOWNGRADE_HOLD_S; a chord that may be the last one's
        ringing tail waits TAIL_HOLD_S."""
        if state == self._N or self._label == self._N:
            return 0.0
        r, q = self._state_rq(state)
        lr, lq = self._state_rq(self._label)
        if r == lr:
            if set(chord_tones(r, q)) < set(chord_tones(lr, lq)):
                return self.DOWNGRADE_HOLD_S
            return self.SAME_ROOT_HOLD_S
        return self.TAIL_HOLD_S if self._may_be_tail(state) else 0.0

    def _may_be_tail(self, state: int) -> bool:
        """A four-note chord whose added tone (the 7th or 9th) belongs to the chord just left may be that chord's
        ringing tail over the new one (G7 into Fmaj7 reads Fadd9 for a moment): it must hold a little longer."""
        r, q = self._state_rq(state)
        pr, pq = self._state_rq(self._label)
        if q not in _EXTENSION or pr is None:
            return False
        return (r + _EXTENSION[q]) % 12 in chord_tones(pr, pq)

    def _new_bass(self, state: int, b: np.ndarray) -> Optional[int]:
        """The bass for a chord just decided. The long bass window lags the treble, so the bass chroma may still
        hold the previous chord's bass; a chord tone freshly ATTACKED in the bass band in the last 0.5 s wins."""
        bass = self._bass_of(state, b)
        if self._source != "audio" or state == self._N:
            return bass
        ok = (self._flux_t <= self._t + 1e-9) & (self._flux_t >= self._t - 0.5)
        rise = self._bflux[ok].sum(axis=0)
        tot = float(rise.sum())
        if tot <= 1e-12:
            return bass
        pc = int(np.argmax(rise))
        if rise[pc] >= 0.5 * tot and self._tone_mask[state, pc]:
            return pc
        return bass

    def _onset_before(self, t_ref: float, tones: Sequence[int]) -> float:
        """The attack that started a chord: the strongest rise of its own tones in the 0.7 s before the frames
        first read it, minus the short window's own lag."""
        ok = (self._flux_t <= t_ref + 1e-9) & (self._flux_t >= t_ref - 0.7)
        if not ok.any():
            return t_ref
        score = np.where(ok, self._flux[:, list(tones)].sum(axis=1), -1.0)
        j = int(np.argmax(score))
        if score[j] <= 0:
            return t_ref
        return max(0.0, float(self._flux_t[j]) - self.ONSET_LAG_S)

    def _state_rq(self, state: Optional[int]) -> Tuple[Optional[int], Optional[str]]:
        if state is None or state == self._N:
            return None, None
        nq = len(QUALITY_NAMES)
        return state // nq, QUALITY_NAMES[state % nq]

    def _change(self, state: int, bass_pc: Optional[int], conf: float, bass_only: bool = False) -> List[dict]:
        t = self._t
        prev = self._label
        self._label, self._label_bass, self._label_conf = state, bass_pc, conf
        if not bass_only:
            self._label_t = self._full_t = t
        self._cand = self._bass_cand = None
        root, quality = self._state_rq(state)
        if bass_only:
            t_change = self._bass_since
        else:
            t_change = self._inst_since if self._inst == state else self._cand_since
            if self._source == "audio" and root is not None:
                t_change = self._onset_before(t_change, chord_tones(root, quality))
        if not bass_only and root is not None:
            self._span_change = t_change
        ev = self._chord_event(t, t_change)
        out = [ev]
        # resolution: tension that had built up falls back onto the tonic
        if (root is not None and not bass_only and prev != self._N and self._key is not None
                and ev["function"] == "tonic" and root == self._key[0]):
            to = self._tension_now(root, quality)
            if self._tension_peak >= 0.4 and self._tension_peak - to >= 0.15:
                out.append({"type": "resolution", "t": round(t, 4), "src": self._src_name(),
                            "from": round(self._tension_peak, 3), "to": round(to, 3), "chord": ev["name"],
                            "numeral": ev["numeral"], "pedal_pc": self._pedal})
                self._tension_peak = to
        return out

    def _chord_event(self, t: float, t_change: Optional[float] = None) -> dict:
        root, quality = self._state_rq(self._label)
        ev = {"type": "chord", "t": round(t, 4), "src": self._src_name(),
              "t_change": round(t if t_change is None else t_change, 4), "changed": True,
              "confidence": round(self._label_conf, 3)}
        if root is None:
            ev.update({"name": "N", "root": None, "quality": None, "bass": None, "numeral": None, "figure": "",
                       "roman": None, "function": None})
        else:
            bass = self._label_bass if self._label_bass is not None else root
            ev.update({"name": chord_name(root, quality, bass, self._key), "root": root, "quality": quality,
                       "bass": bass, "numeral": None, "figure": "", "roman": None, "function": None})
            if self._key is not None:
                ev["numeral"], ev["figure"], ev["function"] = roman(root, quality, bass, *self._key)
                ev["roman"] = full_roman(ev["numeral"], ev["figure"])
        ev["key"] = key_name(*self._key) if self._key else None
        ev["tension"] = round(self._tension_now(root, quality), 3)     # what this chord carries, now
        ev["pedal_pc"] = self._pedal
        return ev

    def _src_name(self) -> str:
        return "keys" if self._source == "notes" else "audio"

    # ---------------------------------------------------------------------------------------------- key
    def _update_key(self, c: np.ndarray, harmonics: bool, quiet: bool) -> None:
        if quiet or self._label == self._N:
            return
        tot = float(c.sum())
        if tot <= 1e-12:
            return
        dt = self._dt
        if self._key_decay is None:
            self._key_decay = math.exp(-dt / self.key_tau)
            self._key_fast_decay = math.exp(-dt / self.KEY_FAST_TAU)
        self._tonal_s += dt
        x = c / tot
        if harmonics:
            x = np.maximum(x - 0.15 * x[_FIFTH_BELOW], 0.0)          # the 12th must not overcount the dominant
        # the decided chord's own tones count too: they are the cleanest read of what is sounding; a dominant 7th
        # also points at the tonic it resolves to (E7 says 'A', which A and D alone cannot)
        chord = self._key_chord[self._label]
        ev = dt * (0.6 * x + 0.4 * chord)
        self._last_key_ev = ev
        self._key_acc = self._key_decay * self._key_acc + ev
        self._key_fast = self._key_fast_decay * self._key_fast + ev
        self._key_ever = self._key_decay * self._key_ever + ev          # never reset: the confidence's memory
        # how much each key's own TONIC chord has been heard lately (the fast memory's time constant)
        self._tonic_acc *= self._key_fast_decay
        self._tonic_acc += dt * self._tonic_of[self._label]
        if self._tonal_s < 1.0 or self._frames % 5:                 # 24 correlations every 5th frame is plenty
            return
        (bk, br), _, rs = self._key_scores(self._key_acc)
        (fk, fr), _, frs = self._key_scores(self._key_fast)
        cur = self._key
        if cur is None:
            if self._tonal_s >= self.KEY_FIRST_S and self._key_belief(rs, frs, bk) >= self.KEY_FIRST_CONF:
                self._key = bk
                self._key_conf = self._key_belief(rs, frs, bk)
                self._key_first_t = self._t
                self._pending_key_event = True
            return
        # a rival key: one the long memory (key_tau) prefers to the current key by KEY_MARGIN, or one the last few
        # seconds (KEY_FAST_TAU) prefer by KEY_FAST_MARGIN -- a modulation shows there long before the long memory
        # turns over, and it must hold for its own, shorter dwell; but only when the rival's tonic chord has been
        # heard lately at least as much as the current key's (C-Bb-F-C keeps coming home to C: it is C with a
        # borrowed bVII, not F major; a key that has really gone has stopped coming home)
        rival, dwell = None, self.KEY_DWELL_S
        if bk != cur and br - rs[cur] > self.KEY_MARGIN:
            rival = bk
        if (fk != cur and fr - frs[cur] > self.KEY_FAST_MARGIN and (rival is None or rival == fk)
                and self._tonic_acc[KEYS.index(fk)] >= max(self.KEY_TONIC[0],
                                                           self.KEY_TONIC[1] * self._tonic_acc[KEYS.index(cur)])
                and self._t - self._key_first_t >= self.KEY_SETTLE_S
                and ((rs[fk] + fr) - (rs[cur] + frs[cur]) > 2 * self.KEY_BLEND_MARGIN
                     or self._tonic_acc[KEYS.index(cur)] < self.KEY_GONE)):
            rival, dwell = fk, self.KEY_FAST_DWELL_S
        if rival is not None and self._key_rival != rival:
            self._key_rival, self._key_rival_since = rival, self._t
        elif rival is not None and self._t - self._key_rival_since >= dwell:
            self._key, self._key_rival = rival, None
            # the long memory starts over from the recent past, so it does not drag the old key back
            self._key_acc = self._key_fast * (self.key_tau / self.KEY_FAST_TAU)
            self._pending_key_event = True
            rs = self._key_scores(self._key_acc)[2]
        elif rival is None:
            self._key_rival = None
        # confidence comes from the key evidence itself, never from the switching margin: how much of the belief
        # (a softmax over all 24 keys, the fast memory blended with a long one that a key change does not reset)
        # the key holds -- a key just switched to on a few seconds' evidence is not yet a confident one
        self._key_conf = self._key_belief(self._key_scores(self._key_ever)[2], frs, self._key)

    def _key_belief(self, rs: dict, frs: dict, key: Tuple[int, str]) -> float:
        """The share of a softmax over the 24 keys' correlations (long and fast memory blended) that `key` holds."""
        r = np.array([0.5 * (rs[k] + frs[k]) for k in KEYS])
        e = np.exp(self.KEY_SHARPNESS * (r - r.max()))
        return float(e[KEYS.index(key)] / e.sum())


    def _key_scores(self, acc: np.ndarray):
        """((key, r) best, (key, r) second, {key: r}): Pearson r of a decayed chroma with all 24 profiles."""
        a = acc - acc.mean()
        r = _KK @ (a / (float(np.linalg.norm(a)) + 1e-12))
        order = np.argsort(-r)
        return ((KEYS[order[0]], float(r[order[0]])), (KEYS[order[1]], float(r[order[1]])),
                {KEYS[i]: float(r[i]) for i in range(24)})

    # ---------------------------------------------------------------------------------------------- tension
    def _tension_target(self, root: Optional[int], quality: Optional[str]) -> float:
        """A chord's harmonic tension in the current key (0..1): its circle-of-fifths distance from the tonic,
        its function and its colour. Memoized: it only changes with the chord or the key."""
        if root is None:
            return 0.0
        memo = (root, quality, self._key)
        if memo != self._tt_memo[0]:
            qt = QUALITY_TENSION[quality]
            if self._key is None:
                v = 0.15 + qt
            else:
                tonic, mode = self._key
                fn = roman(root, quality, None, tonic, mode)[2]
                func = _FUNCTION_TENSION[fn]
                if fn == "tonic" and root != tonic:
                    func = 0.08                                     # vi and iii: tonic-ish, not home
                v = 0.30 * _cof_distance(root, tonic) / 6.0 + func + qt
            self._tt_memo = (memo, _unit(v))
        return self._tt_memo[1]

    def _tension_now(self, root: Optional[int], quality: Optional[str]) -> float:
        """The tension a chord carries right now: its function and colour in the key, the dissonance of what is
        sounding, and the pedal's pull (a soft OR, so it stays inside 0..1)."""
        if root is None:
            return 0.0
        base = 0.75 * self._tension_target(root, quality) + 0.35 * _unit((self._diss - 0.05) / 0.45)
        ped = 0.0
        if self._pedal is not None:
            clash = 0.6 if self._pedal in chord_tones(root, quality) else 1.0
            ped = self._pedal_strength * clash
        return float(1.0 - (1.0 - min(base, 1.0)) * (1.0 - 0.75 * ped))

    def _acc_at(self, when: float) -> np.ndarray:
        """The cumulative held seconds per pitch class as of `when` (the last frame at or before it, within ~2 s)."""
        ok = self._acc_ring_t <= when + 1e-9
        if not ok.any():
            return self._acc_ring[int(np.argmin(self._acc_ring_t))]
        return self._acc_ring[int(np.argmax(np.where(ok, self._acc_ring_t, -np.inf)))]

    def _update_tension(self, present: np.ndarray, pedal_on: np.ndarray, quiet: bool,
                        held: Optional[np.ndarray] = None) -> List[dict]:
        t, dt = self._t, self._dt
        out: List[dict] = []
        # dissonance of what is sounding: interval-class roughness between the notes, weighted by their level
        w = np.where(present > 0.25, present, 0.0)
        norm = float(w.sum() ** 2 - (w * w).sum())
        self._diss = float(w @ _ROUGH @ w) / norm if norm > 1e-9 else 0.0
        # pedal: one pitch class held or re-struck (short gaps allowed) for pedal_min_s while the harmony moves
        # under it -- at least PEDAL_CHORDS different chord ROOTS (Am, Am7 and Asus2 are one) -- really HELD for
        # PEDAL_HELD of that time (struck or sounding fresh, not a previous chord's tail ringing over), and CLASHING
        # with the harmony for PEDAL_CLASH of the time it is held over a chord: it is not one of the chord's tones,
        # or it is only the colour the held note itself gives the chord (Ab + a held Db reads Absus4, G + A Gadd9,
        # Eb-Gb-Bb + Db Ebm7: judged against the chord without it, it clashes). A common tone of a plain loop (the
        # C of Am-F-C: root, third or fifth of every chord it sounds in) never clashes, and a tone the loop leaves
        # out now and then (the C of C-Am-F-Dm7-G7) is not held through it: neither is a pedal
        root, quality = self._state_rq(self._label)
        held = pedal_on if held is None else held
        self._last_held = held
        if not quiet:
            new = pedal_on & (self._run_start < 0)
            self._run_start[new] = t
            self._run_clash[new] = 0.0
            self._run_over[new] = 0.0
            self._run_held[new] = 0.0
            self._run_roots[new] = False
            self._run_spans[new] = 0.0
            self._run_missed[new] = 0.0
            self._last_seen[pedal_on] = t
            self._run_held[held & (self._run_start >= 0)] += dt
            # a held streak: since when each pitch class has been held without a break. A note that came in
            # AFTER the chord under it was named is the next chord arriving (the label lags the attack), not a
            # note held through this one: it does not clash yet
            self._held_since[held & (self._held_since < 0)] = t
            self._held_last[held] = t
            # every chord span (onset to onset, >= 0.4 s): did each run's note sound in it at all? A pedal sounds
            # in every chord it runs through; a loop's common tone leaves one out (the C of C-Am-F-Dm7-G7, absent
            # from the G7), however short the gap
            self._acc_held[held] += dt
            self._acc_ring[self._acc_pos] = self._acc_held
            self._acc_ring_t[self._acc_pos] = t
            self._acc_pos = (self._acc_pos + 1) % len(self._acc_ring_t)
            if self._span_change is not None:
                onset, self._span_change = self._span_change, None
                # (its first SPAN_SKIP_S is the last chord's tail ringing over, which is not this chord's)
                inner = 0.0 if self._span_onset is None else onset - self._span_onset - self.SPAN_SKIP_S
                if inner >= 0.25:
                    inside = self._acc_at(onset) - self._acc_at(self._span_onset + self.SPAN_SKIP_S)
                    live = self._run_start >= 0
                    self._run_spans[live] += 1
                    self._run_missed[live & (inside < 0.25 * inner)] += 1
                self._span_onset = onset
            self._held_since[t - self._held_last > 0.3] = -1.0
            if root is not None:                                    # the roots it is HEARD over, and clashes
                self._run_roots[pedal_on, root] = True
                self._run_over[held] += dt
                through = (self._held_since >= 0) & (self._held_since <= self._label_t)
                self._run_clash[held & through & self._clash_mask[self._label]] += dt
        self._run_start[(self._run_start >= 0) & (t - self._last_seen > self.PEDAL_GAP_S[self._source])] = -1.0
        dur = np.where(self._run_start >= 0, t - self._run_start, 0.0)
        long_ = dur >= self.pedal_min_s
        pedal = None
        if long_.any():
            roots = self._run_roots.sum(axis=1)
            share = self._run_clash / np.maximum(self._run_over, 1e-9)
            lax = np.ones(12)
            if self._pedal is not None:
                lax[self._pedal] = 0.6                              # hysteresis: a pedal on stays on more easily
            clash = share >= self.PEDAL_CLASH * lax
            # ... or a DRONE: held through PEDAL_DRONE_S over PEDAL_DRONE_ROOTS roots or more, whether it fits the
            # chords or not. Daniel's Db under the end of Joy to the World is one: it fits most of the chords over it
            # and is struck with them, but it never stops. A loop's common tone leaves out a chord or two within a
            # few seconds (the C of C-Am-F-Dm7-G7), or runs over only three roots (the C of Am-F-C)
            drone = (dur >= self.PEDAL_DRONE_S) & (roots >= self.PEDAL_DRONE_ROOTS)
            ok = (long_ & (roots >= self.PEDAL_CHORDS) & (clash | drone)
                  & (self._run_held >= self.PEDAL_HELD[self._source] * lax * np.maximum(dur, 1e-9))
                  & (self._run_missed <= self.PEDAL_MISS / lax * self._run_spans))
            if ok.any():
                pedal = int(np.argmax(np.where(ok, dur, -1.0)))
        pedal_events: List[dict] = []
        if pedal != self._pedal:
            names = [spell_note(pc, self._key) for pc in range(12)]
            if self._pedal is not None:
                pedal_events.append({"type": "pedal", "t": round(t, 4), "src": self._src_name(), "pc": self._pedal,
                                     "note": names[self._pedal], "on": False,
                                     "strength": round(self._pedal_strength, 3)})
            self._pedal = pedal
            if pedal is not None:
                pedal_events.append({
                    "type": "pedal", "t": round(t, 4), "src": self._src_name(), "pc": pedal, "note": names[pedal],
                    "on": True, "strength": 0.3, "since": round(float(self._run_start[pedal]), 4),
                    "chords": int(self._run_roots[pedal].sum()), "clash_s": round(float(self._run_clash[pedal]), 2),
                    "clash": round(float(self._run_clash[pedal] / max(self._run_over[pedal], 1e-9)), 3)})
        self._pedal_strength = 0.0 if self._pedal is None else float(
            _unit(0.3 + (dur[self._pedal] - self.pedal_min_s) / self.pedal_ramp_s))
        # the continuous tension: rises in ~0.35 s, relaxes in ~0.8 s
        target = 0.0 if quiet else self._tension_now(root, quality)
        tau = 0.35 if target > self.tension else 0.8
        self.tension += (1.0 - math.exp(-dt / tau)) * (target - self.tension)
        # the peak a resolution falls FROM fades (~6 s), so an old climax cannot "resolve" a minute later
        self._tension_peak = max(self.tension, self._tension_peak * math.exp(-dt / 6.0))
        for ev in pedal_events:                                     # the tension the pedal leaves, as of now
            ev["tension"] = round(self.tension, 3)
            out.append(ev)
        if self._pending_key_event:
            self._pending_key_event = False
            ev = {"type": "key", "t": round(t, 4), "src": self._src_name(), "key": key_name(*self._key),
                  "tonic": self._key[0], "mode": self._key[1], "confidence": round(self._key_conf, 3)}
            if root is not None:                                    # the chord already sounding, in the new key
                cur = self._chord_event(t)
                ev.update({"chord": cur["name"], "numeral": cur["numeral"], "figure": cur["figure"],
                           "roman": cur["roman"], "function": cur["function"]})
            out.append(ev)
        return out

    # ---------------------------------------------------------------------------------------------- state
    @property
    def key(self) -> Optional[Tuple[int, str]]:
        """(tonic pitch class, 'major' | 'minor'), or None before the key is known."""
        return self._key

    def snapshot(self) -> dict:
        """The continuous state for a renderer. Cheap; call it every frame."""
        ev = self._chord_event(self._t)
        ev["changed"] = False
        names = [spell_note(pc, self._key) for pc in range(12)] if self._pedal is not None else None
        cmax = float(self._chroma.max())
        bsum = float(self._bass.sum())
        return {"t": round(self._t, 4), "chord": ev,
                "key": key_name(*self._key) if self._key else None,
                "key_confidence": round(self._key_conf, 3),
                "tension": round(self.tension, 4), "dissonance": round(self._diss, 4),
                "pedal": None if self._pedal is None else {"pc": self._pedal, "note": names[self._pedal],
                                                           "strength": round(self._pedal_strength, 3)},
                "pulse": round(min(1.0, self._pulse), 4),
                "chroma": [round(float(v) / cmax, 4) if cmax > 0 else 0.0 for v in self._chroma],
                "notes": [round(float(v), 4) for v in self._present],
                "bass": [round(float(v) / bsum, 4) if bsum > 0 else 0.0 for v in self._bass],
                "energy": round(self._energy, 6),
                "tuning_cents": round(100.0 * self.tuning, 1)}


# --- helpers -----------------------------------------------------------------------------------------------

def score_to_events(notes: Sequence[dict], ppq: int, bpm: float, t0: Optional[int] = None) -> List[dict]:
    """A score's notes ({pos, len, key, vel} in ticks, e.g. an FL Studio pattern) as time-ordered note events
    for `feed_notes`. Time 0 is the first note unless `t0` (a tick) is given."""
    if not notes:
        return []
    start = min(n["pos"] for n in notes) if t0 is None else t0
    sec = 60.0 / (bpm * ppq)
    evs = []
    for n in notes:
        on = (n["pos"] - start) * sec
        evs.append({"t": on, "note": int(n["key"]), "vel": int(max(1, n.get("vel", 100)))})
        evs.append({"t": on + max(1, n["len"]) * sec, "note": int(n["key"]), "vel": 0})
    evs.sort(key=lambda e: (e["t"], e["vel"] > 0))                 # offs before ons at the same instant
    return evs


_VJ_QUALITY = {"min": "m"}                                          # the VJ contract spells minor as theory does


def to_vj_events(event: dict, src: Optional[str] = None) -> List[dict]:
    """One chordsense event as the VJ engine's Server-Sent Events (the contract in arsenal/keylab/vj.py), so wiring
    chordsense into the engine is `for e in cs.feed(block): for v in to_vj_events(e): hub.publish(v)`.

    chord      -> chord {t, src, name, root, quality, pcs, bass, roman, key, conf, changed}, then
                  tension {t, value, pedal_pc}: the tension the new chord carries
    key        -> key {t, name, conf}
    pedal      -> tension {t, value, pedal_pc}: pedal_pc is the held pitch class, null once it is released
    resolution -> tension {t, value, pedal_pc}: value is where the tension fell to
    src: 'audio' or 'keys' (default: the event's own src). Anything else maps to []."""
    kind = event.get("type")
    s = src or event.get("src") or "audio"
    if kind == "chord":
        root, quality, bass = event["root"], event["quality"], event["bass"]
        pcs = [] if root is None else sorted(set(chord_tones(root, quality)) | ({bass} if bass is not None else set()))
        return [{"t": "chord", "src": s, "name": event["name"], "root": root,
                 "quality": _VJ_QUALITY.get(quality, quality), "pcs": pcs, "bass": bass, "roman": event["roman"],
                 "key": event["key"], "conf": event["confidence"], "changed": event["changed"]},
                {"t": "tension", "value": event["tension"], "pedal_pc": event.get("pedal_pc")}]
    if kind == "key":
        return [{"t": "key", "name": event["key"], "conf": event["confidence"]}]
    if kind == "pedal":
        return [{"t": "tension", "value": event.get("tension", 0.0), "pedal_pc": event["pc"] if event["on"] else None}]
    if kind == "resolution":
        return [{"t": "tension", "value": event["to"], "pedal_pc": event.get("pedal_pc")}]
    return []
