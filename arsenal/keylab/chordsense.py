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

Events (dicts; `t` = seconds of input consumed when the event was decided):
  chord       {name, root, quality, bass, confidence, changed, t_change, numeral, figure, roman, function, key,
              tension}. numeral is the root-position reading (V7), figure the inversion (65), roman both (V65)
              name is 'N' (root / quality / bass None) for silence or drums only. t_change back-dates the change
              to the attack that started it (median error 9 ms, p90 40 ms on the synthetic set): beat matching
              wants the onset, not the moment the decision was safe. tension is what this chord carries now.
  key         {key, tonic, mode, confidence, chord, numeral, figure, roman, function}
  pedal       {pc, note, on, strength, since, chords, clash_s}: one pitch class held or re-struck while the
              chords move under it; its pull on the tension grows the longer it holds
  resolution  {from, to, chord, numeral}: tension that had built up falls back onto the tonic

Snapshot: {t, chord, key, key_confidence, tension, dissonance, pedal, pulse, chroma, notes, bass, energy,
tuning_cents}. pulse (0..1) is the harmonic attack strength of the latest frame (new notes, not drums): a
renderer can flash on it.

Audio front end: a causal anti-alias decimator to ~11-12 kHz; two Hann FFTs (a long one for the bass, a short
one for the treble) read as interpolated spectral PEAKS; a tuning-offset estimate (a circular mean of the
peaks' deviations from the A440 grid); the peaks binned on a log-frequency grid of three bins per semitone; a
causal harmonic / percussive split on that grid (a median over a short PAST window in time against a median
across frequency, soft mask), so drum hits and bass-drum sweeps stay out of the harmony. From the harmonic part:
a 12-bin chroma (everything sounding), a BASS chroma (65-250 Hz, weighted toward the lowest note) for
inversions and slash chords, an overtone-corrected note salience (for dissonance and the pedal) and a tonality
share (how much of the energy is harmonic at all: drums and noise read 'N').

Back end: templates for major, minor, 7, maj7, m7, sus2, sus4, dim, aug, add9 and 5, with the expected
overtones for audio and plain for notes, scored by correlation with the chroma; a bass term (root in the bass,
a chord tone in the bass = an inversion, a foreign bass = a penalty); an 'N' state; an online HMM forward filter
(a sticky self-transition) plus a hold rule, so labels do not flicker. A Krumhansl-Kessler key tracker on a
decayed chroma with hysteresis; roman numerals and function in that key (I, IV, V7, vi, bVII, V/V ...). Tension
0..1 from the chord's circle-of-fifths distance, its function and colour, the dissonance of what is sounding,
and the pedal.

Rules it was built under (the keylab licence firewall): numpy, scipy and the standard library only; no models,
no files, no I/O; causal (nothing ever looks ahead); bounded work per call, so it never blocks an audio loop.
At 48 kHz with hop 512 it runs far over 20x real time on one core (pinned by tests/test_keylab_chordsense.py).
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.ndimage import median_filter
from scipy.signal import butter, sosfilt, sosfilt_zi

# --- names and vocabulary ----------------------------------------------------------------------------------

SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
DEFAULT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]   # the common spellings

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
         "dim": -0.015, "aug": -0.030, "add9": -0.020, "5": -0.020}
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
_FIFTH_BELOW = (np.arange(12) - 7) % 12         # x[_FIFTH_BELOW][p] = x[p - 7]: the note whose 12th lands on p

# the overtone series folded to pitch classes: harmonic h of a tone lands this many semitones (mod 12) above it
_HARM_PC = (0, 0, 7, 0, 4, 7, 10, 0)            # h = 1..8: unison, octave, 12th, 2 oct, 17th, 19th, b21st, 3 oct
_HARM_DECAY = 0.6                               # amplitude of harmonic h ~ 0.6^(h-1) (Gomez 2006)

# interval-class roughness for the dissonance term: index = interval class 0..6 (ic1 = m2/M7, ic6 = tritone)
_IC_ROUGH = np.array([0.0, 1.0, 0.45, 0.12, 0.08, 0.02, 0.65])
_ROUGH = np.array([[_IC_ROUGH[min((i - j) % 12, (j - i) % 12)] for j in range(12)] for i in range(12)])


def note_names_for(key: Optional[Tuple[int, str]]) -> List[str]:
    """Spell pitch classes with flats in flat keys, sharps in sharp keys, the common spellings with no key."""
    if key is None:
        return DEFAULT_NAMES
    tonic, mode = key
    flat = tonic in (FLAT_KEYS_MAJOR if mode == "major" else FLAT_KEYS_MINOR)
    return FLATS if flat else SHARPS


def chord_name(root: int, quality: str, bass: Optional[int] = None, key: Optional[Tuple[int, str]] = None) -> str:
    names = note_names_for(key)
    s = names[root] + QUALITIES[quality][1]
    if bass is not None and bass != root:
        s += "/" + names[bass]
    return s


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
    LO_MIDI, HI_MIDI = 33, 100                  # A1 (55 Hz) .. E7 (2.6 kHz)
    BASS_LO, BASS_HI = 36, 59                   # C2 (65 Hz) .. B3 (247 Hz): above the bass drum's tail
    SPLIT_MIDI = 57                             # below: the long FFT's peaks; at and above: the short FFT's
    BINS_PER_SEMI = 3
    BASS_SIG, BASS_TAU_S = 0.3, 0.12            # the lowest bass peak above this share of the loudest = the bass
    ONSET_LAG_S = 0.065                         # how late the short window shows an attack (calibrated)
    TAIL_HOLD_S = 0.20                          # extra hold for a chord that may be the last one's ringing tail
    SAME_ROOT_HOLD_S = 0.25                     # extra hold when only the quality would change, not the root
    DOWNGRADE_HOLD_S = 1.0                      # ... and when it would only drop a tone of the chord held
    # pedal: audio counts a pitch class as sounding above this share of the loudest note salience; notes count
    # it while its key is down or it was struck within PEDAL_STRIKE_S. A run survives gaps of PEDAL_GAP_S and
    # becomes a pedal once it has lasted pedal_min_s over at least PEDAL_CHORDS different chords
    PEDAL_ON_AUDIO = 0.30
    PEDAL_STRIKE_S = 1.2
    PEDAL_GAP_S = {"audio": 1.2, "notes": 0.6}
    PEDAL_CHORDS = 3
    RING_OUT_S = 0.6                            # notes: a released key (no sustain pedal) fades over this...
    DAMP_S = 0.12                               # ...and much faster once a new chord is struck:
    CHORD_NOTES, CHORD_SPREAD_S = 3, 0.06       # this many keys within this long
    # key: announced after KEY_FIRST_S of tonal time; changed only when a rival leads by KEY_MARGIN for
    # KEY_DWELL_S
    KEY_FIRST_S, KEY_MARGIN, KEY_DWELL_S = 3.0, 0.05, 4.0

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
        self._roots = np.repeat(np.arange(12), nq)
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
        self._bass_cand: Optional[int] = None
        self._bass_since = 0.0
        self._inst: Optional[int] = None        # what each frame says on its own, and since when
        self._inst_since = 0.0
        # key
        self._key_acc = np.zeros(12)
        self._key_decay: Optional[float] = None
        self._key: Optional[Tuple[int, str]] = None
        self._key_conf = 0.0
        self._key_rival: Optional[Tuple[int, str]] = None
        self._key_rival_since = 0.0
        self._tonal_s = 0.0
        self._pending_key_event = False
        # tension, pedal, resolution
        self.tension = 0.0
        self._tension_peak = 0.0
        self._tt_memo: Tuple[object, float] = (None, 0.0)
        self._run_start = np.full(12, -1.0)     # pedal runs: start time per pitch class (-1 = none)
        self._last_seen = np.full(12, -1e9)
        self._run_heard = np.zeros((12, self._nstates), dtype=bool)   # the chords each run was heard over
        self._run_clash = np.zeros(12)          # seconds each run has clashed with the chord under it
        self._pedal: Optional[int] = None
        self._pedal_strength = 0.0
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
            self._sos = butter(8, 0.80 / self._decim, output="sos")
            self._zi = sosfilt_zi(self._sos) * 0.0
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
        self._semi_pc = (self.LO_MIDI + np.arange(self._nb // self.BINS_PER_SEMI)) % 12
        self._hk = max(5, int(round(self.hpss_s / self._dt))) | 1
        self._hring = np.zeros((self._hk, self._nb))
        self._hpos = 0
        self._tune_z = 0j
        self._chroma_s = np.zeros(12)
        self._bass_s = np.zeros(12)
        self._salience_s = np.zeros(12)
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
        self._fe_ready = True

    def feed(self, block) -> List[dict]:
        """Feed audio: float samples in -1..1, mono (n,) or (n, channels), any length. Returns the events
        decided inside this block (usually none)."""
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
            y, self._zi = sosfilt(self._sos, chunk, zi=self._zi)
            y = y[self._dphase::self._decim]
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

    @staticmethod
    def _peaks(x: np.ndarray, win: np.ndarray, norm: float, df: float, k0: int, k1: int):
        """Spectral peaks between bins k0..k1: (frequency, amplitude), parabolic interpolation on log magnitude."""
        mag = np.abs(np.fft.rfft(x * win)) * norm
        seg = mag[k0 - 1:k1 + 1]
        mid = seg[1:-1]
        floor = max(1e-5, 0.003 * float(mid.max(initial=0.0)))
        k = np.flatnonzero((mid > seg[:-2]) & (mid >= seg[2:]) & (mid > floor))
        if k.size == 0:
            return np.zeros(0), np.zeros(0)
        a = np.log(seg[k] + 1e-12)
        b = np.log(mid[k] + 1e-12)
        c = np.log(seg[k + 2] + 1e-12)
        den = a - 2 * b + c
        p = np.clip(np.where(den < -1e-12, 0.5 * (a - c) / np.where(den < -1e-12, den, -1.0), 0.0), -0.5, 0.5)
        return (k + k0 + p) * df, np.exp(b - 0.25 * (a - c) * p)

    def _audio_frame(self) -> List[dict]:
        ring = self._ring
        fl, al = self._peaks(ring, self._win_l, self._norm_l, self._df_l, *self._kl)
        fs, as_ = self._peaks(ring[-self._ns:], self._win_s, self._norm_s, self._df_s, *self._ks)
        keep_l, keep_s = fl < self._f_split, fs >= self._f_split
        f = np.concatenate((fl[keep_l], fs[keep_s]))
        amp = np.concatenate((al[keep_l], as_[keep_s]))
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
        # onset evidence BEFORE the median (which delays the harmony on purpose): the per-pitch-class rise of the
        # raw spectrum, kept ~0.8 s so a decided chord can be back-dated to the attack that started it
        raw = np.sqrt(np.bincount(self._bin_pc, weights=fine, minlength=12))
        rise = np.maximum(raw - self._raw_prev, 0.0)
        self._raw_prev = raw
        self._flux[self._fpos] = rise
        braw = np.sqrt(self._lowest_weighted(np.where(self._bass_bins, fine, 0.0)))
        self._bflux[self._fpos] = np.maximum(braw - self._braw_prev, 0.0)
        self._braw_prev = braw
        self._flux_t[self._fpos] = self._t
        self._fpos = (self._fpos + 1) % len(self._flux_t)
        energy = float(harm.sum())
        total = float(fine.sum())
        self._tonality += self._a_tonal * ((energy / total if total > 1e-9 else 0.0) - self._tonality)
        # note salience: each semitone minus what the overtones of the notes below it explain, so dissonance and
        # pedals are heard in the NOTES, not in their 12ths and 17ths
        semi = harm.reshape(-1, self.BINS_PER_SEMI).sum(axis=1)
        expl = np.zeros_like(semi)
        for off, g in ((12, 0.55), (19, 0.35), (24, 0.25), (28, 0.2)):
            expl[off:] += g * semi[:-off]
        sal = np.bincount(self._semi_pc, weights=np.maximum(semi - expl, 0.0), minlength=12)
        self._salience_s += self._a_sal * (sal - self._salience_s)
        chroma = np.bincount(self._bin_pc, weights=harm, minlength=12)
        bass = self._lowest_weighted(np.where(self._bass_bins, harm, 0.0))
        self._chroma_s += self._a_chroma * (chroma - self._chroma_s)
        self._bass_s += self._a_bass * (bass - self._bass_s)
        # silence is relative to the music (a slow peak follower) with an absolute floor
        self._ref_energy = max(energy, self._ref_energy * math.exp(-self._dt / 8.0), 1e-6)
        quiet = energy < max(2e-4, 0.03 * self._ref_energy)
        smax = float(self._salience_s.max())
        present = self._salience_s / smax if smax > 1e-12 else np.zeros(12)
        # when little of the energy is harmonic (drums, noise, applause), 'N' gets the benefit of the doubt
        n_boost = 2.0 * max(0.0, 0.55 - self._tonality)
        self._set_pulse(float(rise.sum()))
        return self._step(np.maximum(self._chroma_s, 0.0) ** self.gamma, self._bass_s.copy(), energy, quiet,
                          True, present, present > self.PEDAL_ON_AUDIO, n_boost)

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
            while self._t + self._dt <= t:
                self._t += self._dt
                out.extend(self._notes_frame())
            self._apply_note(ev, t)
        if now is not None:
            while self._t + self._dt <= now:
                self._t += self._dt
                out.extend(self._notes_frame())
        return out

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
        lowest = lowest_ringing = None
        dead = []
        for note, (vel, t_on, key_down, t_off, t_damp) in self._held.items():
            level = vel * math.exp(-(t - t_on) / 2.5)              # a struck string fades
            if key_down:
                level = max(level, 0.35 * vel)                     # a held key keeps sounding (organ, pads)
                down[note % 12] = True
            elif t_off is not None:
                level *= math.exp(-(t - t_off) / self.RING_OUT_S)
                if t_damp is not None:
                    level *= math.exp(-(t - t_damp) / self.DAMP_S)
            if level < 0.03:
                dead.append(note)
                continue
            chroma[note % 12] += level
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
        if lowest is not None:
            bass[lowest % 12] = 1.0
        energy = float(chroma.sum())
        present = chroma / chroma.max() if energy > 0 else np.zeros(12)
        # for the pedal a note is ON while its key is down or it was struck within PEDAL_STRIKE_S: what the
        # player keeps playing, not what merely rings
        pedal_on = down | (t - self._last_strike < self.PEDAL_STRIKE_S)
        self._set_pulse(self._strike_energy)
        self._strike_energy = 0.0
        return self._step(chroma ** self.gamma, bass, energy, energy < 0.05, False, present, pedal_on)

    def _set_pulse(self, x: float) -> None:
        """The harmonic attack strength of this frame, 0..1 against a slowly decaying peak (~5 s)."""
        self._pulse_ref = max(x, self._pulse_ref * math.exp(-self._dt / 5.0), 1e-9)
        self._pulse = x / self._pulse_ref

    # ---------------------------------------------------------------------------------------------- shared
    def _scores(self, c: np.ndarray, b: np.ndarray, harmonics: bool) -> np.ndarray:
        """The score of every chord state (and of N, last) for a compressed chroma c and a bass distribution b."""
        if self.sim == "pearson":
            c = c - c.mean()
        nrm = float(np.linalg.norm(c))
        s = np.empty(self._nstates)
        if nrm < 1e-12:
            s[:-1] = 0.0
        else:
            s[:-1] = (self._templates[harmonics] @ c) / (self._tnorm[harmonics] * nrm)
        bs = float(b.sum())
        if bs > 1e-12:
            bd = b / bs
            in_chord = self._tone_mask[:-1] @ bd                    # bass mass on the chord's own tones
            root_b = bd[self._roots]
            s[:-1] += 0.10 * root_b + 0.05 * (in_chord - root_b) - 0.10 * (1.0 - in_chord)
        s[:-1] += self._prior
        s[-1] = self.n_floor
        return s

    def _step(self, c: np.ndarray, b: np.ndarray, energy: float, quiet: bool, harmonics: bool,
              present: np.ndarray, pedal_on: np.ndarray, n_boost: float = 0.0) -> List[dict]:
        """One frame of the shared back end. c: compressed chroma; b: bass distribution; present: the pitch
        classes sounding as notes (0..1); pedal_on: the pitch classes the pedal detector counts as held;
        n_boost: extra weight for 'no chord' on non-tonal frames."""
        t = self._t
        self._frames += 1
        self._chroma, self._bass, self._energy, self._present = c, b, energy, present
        s = self._scores(c, b, harmonics)
        s[-1] += n_boost
        if quiet:
            s[-1] = 10.0                                            # silence: N, decisively
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
        out: List[dict] = []
        if best != self._label:
            # a new chord must lead the posterior clearly for min_hold_s, AND be what the frame itself says right
            # now: a chord passing through on its way to the next (G7 fading into Fmaj7 reads Fadd9 for a moment)
            # leads the posterior only briefly
            if best != self._cand:
                self._cand, self._cand_since = best, t
                self._cand_hold = self.min_hold_s + self._extra_hold(best)
            conf = float(post[best])
            if (t - self._cand_since >= self._cand_hold and conf >= 0.55 and inst == best
                    and conf > post[self._label] + 0.2):
                out.extend(self._change(best, self._new_bass(best, b), conf))
        else:
            self._cand = None
            self._label_conf = float(post[best])
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
        out.extend(self._update_tension(present, pedal_on, quiet))
        return out

    def _bass_of(self, state: int, b: np.ndarray) -> Optional[int]:
        """The bass to name with a chord: the dominant bass pitch class when it is a chord tone, else the root."""
        if state == self._N:
            return None
        root = int(self._roots[state])
        bs = float(b.sum())
        if bs <= 1e-12:
            return root
        bd = b / bs
        pc = int(np.argmax(bd))
        if bd[pc] < 0.4 or not self._tone_mask[state, pc]:
            return root
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
        self._cand = self._bass_cand = None
        root, quality = self._state_rq(state)
        if bass_only:
            t_change = self._bass_since
        else:
            t_change = self._inst_since if self._inst == state else self._cand_since
            if self._source == "audio" and root is not None:
                t_change = self._onset_before(t_change, chord_tones(root, quality))
        ev = self._chord_event(t, t_change)
        out = [ev]
        # resolution: tension that had built up falls back onto the tonic
        if (root is not None and not bass_only and prev != self._N and self._key is not None
                and ev["function"] == "tonic" and root == self._key[0]):
            to = self._tension_now(root, quality)
            if self._tension_peak >= 0.4 and self._tension_peak - to >= 0.15:
                out.append({"type": "resolution", "t": round(t, 4), "from": round(self._tension_peak, 3),
                            "to": round(to, 3), "chord": ev["name"], "numeral": ev["numeral"]})
                self._tension_peak = to
        return out

    def _chord_event(self, t: float, t_change: Optional[float] = None) -> dict:
        root, quality = self._state_rq(self._label)
        ev = {"type": "chord", "t": round(t, 4), "t_change": round(t if t_change is None else t_change, 4),
              "changed": True, "confidence": round(self._label_conf, 3)}
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
        return ev

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
        self._tonal_s += dt
        x = c / tot
        if harmonics:
            x = np.maximum(x - 0.15 * x[_FIFTH_BELOW], 0.0)          # the 12th must not overcount the dominant
        # the decided chord's own tones count too: they are the cleanest read of what is sounding
        chord = self._tone_mask[self._label] / self._tone_count[self._label]
        self._key_acc = self._key_decay * self._key_acc + dt * (0.6 * x + 0.4 * chord)
        if self._tonal_s < 1.0 or self._frames % 5:                 # 24 correlations every 5th frame is plenty
            return
        (bk, br), (_, r2), rs = self._key_scores()
        conf = float(np.clip((br - r2) / 0.15, 0.0, 1.0) * np.clip(br, 0.0, 1.0))
        cur = self._key
        if cur is None:
            if self._tonal_s >= self.KEY_FIRST_S and conf >= 0.25:
                self._key, self._key_conf = bk, conf
                self._pending_key_event = True
            return
        if bk == cur:
            self._key_conf, self._key_rival = conf, None
            return
        cur_r = rs[cur]
        if br - cur_r > self.KEY_MARGIN:
            if self._key_rival != bk:
                self._key_rival, self._key_rival_since = bk, self._t
            elif self._t - self._key_rival_since >= self.KEY_DWELL_S:
                self._key, self._key_conf, self._key_rival = bk, conf, None
                self._pending_key_event = True
        else:
            self._key_rival = None
            self._key_conf = float(np.clip((cur_r - br + 0.15) / 0.3, 0.0, 1.0))

    def _key_scores(self):
        """((key, r) best, (key, r) second, {key: r}): Pearson r of the decayed chroma with all 24 profiles."""
        a = self._key_acc - self._key_acc.mean()
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
            self._tt_memo = (memo, float(np.clip(v, 0.0, 1.0)))
        return self._tt_memo[1]

    def _tension_now(self, root: Optional[int], quality: Optional[str]) -> float:
        """The tension a chord carries right now: its function and colour in the key, the dissonance of what is
        sounding, and the pedal's pull (a soft OR, so it stays inside 0..1)."""
        if root is None:
            return 0.0
        base = 0.75 * self._tension_target(root, quality) + 0.35 * float(np.clip((self._diss - 0.05) / 0.45,
                                                                                   0.0, 1.0))
        ped = 0.0
        if self._pedal is not None:
            clash = 0.6 if self._pedal in chord_tones(root, quality) else 1.0
            ped = self._pedal_strength * clash
        return float(1.0 - (1.0 - min(base, 1.0)) * (1.0 - 0.75 * ped))

    def _update_tension(self, present: np.ndarray, pedal_on: np.ndarray, quiet: bool) -> List[dict]:
        t, dt = self._t, self._dt
        out: List[dict] = []
        # dissonance of what is sounding: interval-class roughness between the notes, weighted by their level
        w = np.where(present > 0.25, present, 0.0)
        norm = float(w.sum() ** 2 - (w * w).sum())
        self._diss = float(w @ _ROUGH @ w) / norm if norm > 1e-9 else 0.0
        # pedal: one pitch class held or re-struck (short gaps allowed) for pedal_min_s while at least
        # PEDAL_CHORDS different chords sound under it
        root, quality = self._state_rq(self._label)
        if not quiet:
            new = pedal_on & (self._run_start < 0)
            self._run_start[new] = t
            self._run_clash[new] = 0.0
            self._run_heard[new] = False
            self._last_seen[pedal_on] = t
            if root is not None:                                    # the chords it is HEARD over, and clashes
                self._run_heard[pedal_on, self._label] = True
                self._run_clash[pedal_on & ~self._tone_mask[self._label]] += dt
        self._run_start[(self._run_start >= 0) & (t - self._last_seen > self.PEDAL_GAP_S[self._source])] = -1.0
        dur = np.where(self._run_start >= 0, t - self._run_start, 0.0)
        ok = (dur >= self.pedal_min_s) & (self._run_heard.sum(axis=1) >= self.PEDAL_CHORDS)
        pedal = int(np.argmax(np.where(ok, dur, -1.0))) if ok.any() else None
        if pedal != self._pedal:
            names = note_names_for(self._key)
            if self._pedal is not None:
                out.append({"type": "pedal", "t": round(t, 4), "pc": self._pedal, "note": names[self._pedal],
                            "on": False, "strength": round(self._pedal_strength, 3)})
            self._pedal = pedal
            if pedal is not None:
                out.append({"type": "pedal", "t": round(t, 4), "pc": pedal, "note": names[pedal], "on": True,
                            "strength": 0.3, "since": round(float(self._run_start[pedal]), 4),
                            "chords": int(self._run_heard[pedal].sum()),
                            "clash_s": round(float(self._run_clash[pedal]), 2)})
        self._pedal_strength = 0.0 if self._pedal is None else float(
            np.clip(0.3 + (dur[self._pedal] - self.pedal_min_s) / self.pedal_ramp_s, 0.0, 1.0))
        # the continuous tension: rises in ~0.35 s, relaxes in ~0.8 s
        target = 0.0 if quiet else self._tension_now(root, quality)
        tau = 0.35 if target > self.tension else 0.8
        self.tension += (1.0 - math.exp(-dt / tau)) * (target - self.tension)
        # the peak a resolution falls FROM fades (~6 s), so an old climax cannot "resolve" a minute later
        self._tension_peak = max(self.tension, self._tension_peak * math.exp(-dt / 6.0))
        if self._pending_key_event:
            self._pending_key_event = False
            ev = {"type": "key", "t": round(t, 4), "key": key_name(*self._key), "tonic": self._key[0],
                  "mode": self._key[1], "confidence": round(self._key_conf, 3)}
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
        names = note_names_for(self._key)
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
