"""arsenal.keylab.beatbench -- one instrument that judges every beat tracker on the same ground truth.

Built BEFORE any new tracker (A16 T4, Daniel 2026-10-22: "lets see what we can figure out for our own internal
beat detector"), so aubio, librosa and our own trackers are all scored by the same ruler.

The streaming contract every tracker meets (agreed with Heimdall for the blind pair beat_a.py / beat_b.py,
bus 1792703252595-0):

    tracker = Factory(rate, hop, seed_bpm=None)
    events  = tracker.feed(block)       # block: float32 mono numpy array of `hop` samples
    # OBSERVED beats: [{"t_beat": s, "bpm": float, "phase": 0..1, "confidence": 0..1, "is_downbeat": bool|None}]
    # every observed beat carries a finite bpm > 0 (check_tracker enforces it)
    ahead   = tracker.predict(now)      # EXPECTED beats after `now` (seconds of audio fed so far):
    # [{"t_beat": s, "bpm", "phase", "confidence"}] -- what the hub paints from, a few hundred ms early;
    # sorted, all in the future. The lights paint ahead[0] (beatsync), so the bench asks predict() after EVERY
    # block, exactly as beatsync does, and scores ahead[0]. predict() is required of contestants (check_tracker)
    # and optional only for the baselines; is_downbeat None means "this tracker does not claim meter" and is
    # never penalised -- downbeats are scored only for trackers that emit them.

Two different failures, scored apart: a missed OBSERVED beat is a detection failure (F, CMLt, AMLt); a wrong
EXPECTED beat is a phase-lock failure (pred_err_ms, pred_hit). The reconcile step picks the better tracker by
these numbers and the SHIPPABLE one by its licence profile -- two questions, never fused (Heimdall's rule).

Ground truth, three kinds:
  synthetic  clicks and drum patterns from numpy (exact beats, tempo ramps, swing, noise), always available;
  file       a render whose tempo is known (Daniel's FL exports). Tempo is exact; beat phase only when the case
             says so (`phase_known`), otherwise only the tempo metrics are scored;
  custom     any audio plus an annotation list of beat times.

Metrics, implemented from their published definitions (no GPL, no extra dependency):
  F-measure       hits within +-70 ms (Dixon 2007; the MIREX window)
  CMLt / AMLt     continuity at the correct metrical level / any allowed level, total (Hainsworth; Klapuri et
                  al. 2006; Davies et al. 2009 tech report "Evaluation methods for musical audio beat tracking")
  Acc1 / Acc2     tempo within 4% / within 4% of x1, x2, x1/2, x3, x1/3 (Gouyon et al. 2006)
  lock_s          first time after which the next 8 beats all hit (live behaviour, ours)
  lead_ms         median of t_beat - time it was announced; positive = predicted ahead (ours)
  octave_err      share of locked-state bpm reports off by x2 or x1/2 (ours)
  pred_err_ms     median |ahead[0] - the true next beat| over every block's predict(), asked >= 50 ms ahead,
                  after lock (ours): the beat the lights would actually paint
  pred_hit        share of those predictions within +-35 ms, the visual tolerance for lights (ours)
  bpm_spread / tempo_flips   steadiness of the DISPLAYED (reported) bpm; a tracker may smooth what it displays
  ibi_spread / ibi_flips     the same two definitions on 60 / inter-beat-interval of the observed beat TIMES:
                  the grid the beats really sit on, which display smoothing cannot hide (ours)
  bpm_missing     observed beats after the settle time with no usable bpm (counted, never silently dropped)
  realtime_x / cpu_x         audio seconds per wall second of the whole run / per CPU second (process_time) of
                  feed() + predict() per block, the work the live loop does (ours)
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

F_WINDOW = 0.07          # seconds
CONT_TOL = 0.175         # phase and period tolerance for the continuity metrics
TEMPO_TOL = 0.04         # Acc1 / Acc2 tolerance
SKIP_FIRST = 5.0         # seconds of each case not scored for beat metrics (the convention; lock_s covers it)
PRED_HIT_MS = 35.0       # a predicted beat within this lands visibly ON the beat

# CPU clock for the speed row: process time of feed() + predict(), the work the live loop does per block.
# A module attribute so a test can substitute a deterministic clock.
_cpu_clock = time.process_time


# --- ground truth ------------------------------------------------------------------------------------------

@dataclass
class Case:
    name: str
    audio: np.ndarray                  # float32 mono
    rate: int
    beats: np.ndarray                  # reference beat times, seconds (may be empty for tempo-only cases)
    bpm: float                         # reference tempo (median, for ramps)
    seed_bpm: Optional[float] = None   # what a database lookup would have given (None = no seed)
    phase_known: bool = True           # False = score tempo only
    source: str = "synthetic"
    meta: Dict = field(default_factory=dict)


def beat_times(bpm: float, secs: float, offset: float = 0.0, ramp_to: Optional[float] = None,
               step_at: Optional[float] = None, step_to: Optional[float] = None) -> np.ndarray:
    """Beat times for a constant tempo, a linear ramp from bpm to ramp_to over the whole case, or a sudden STEP
    to step_to at step_at seconds (a DJ transition / tempo automation; Daniel 2026-10-22: "have shifting bpm")."""
    if step_at is not None and step_to is not None:
        out, t = [], offset
        while t < secs:
            out.append(t)
            t += 60.0 / (bpm if t < step_at else step_to)
        return np.array(out)
    if ramp_to is None:
        period = 60.0 / bpm
        return np.arange(offset, secs, period)
    out, t = [], offset
    while t < secs:
        out.append(t)
        frac = t / secs
        cur = bpm + (ramp_to - bpm) * frac
        t += 60.0 / cur
    return np.array(out)


def _env(n: int, rate: int, decay_s: float) -> np.ndarray:
    return np.exp(-np.arange(n) / (decay_s * rate)).astype(np.float32)


def _kick(rate: int) -> np.ndarray:
    n = int(0.25 * rate)
    t = np.arange(n) / rate
    freq = 40 + 70 * np.exp(-t * 30)                         # pitch drop
    return (np.sin(2 * np.pi * np.cumsum(freq) / rate) * _env(n, rate, 0.08)).astype(np.float32)


def _snare(rate: int, rng: np.random.Generator) -> np.ndarray:
    n = int(0.18 * rate)
    noise = rng.standard_normal(n).astype(np.float32)
    tone = np.sin(2 * np.pi * 190 * np.arange(n) / rate).astype(np.float32)
    return (0.6 * noise * _env(n, rate, 0.05) + 0.4 * tone * _env(n, rate, 0.03)).astype(np.float32)


def _hat(rate: int, rng: np.random.Generator) -> np.ndarray:
    n = int(0.05 * rate)
    noise = rng.standard_normal(n).astype(np.float32)
    hp = np.diff(noise, prepend=0).astype(np.float32)        # crude high-pass
    return (0.35 * hp * _env(n, rate, 0.012)).astype(np.float32)


def _bass(rate: int) -> np.ndarray:
    """A loud sub-bass note: sharp attack, ~150 ms decay, 55 Hz with a slight drop -- the kind of hit that sits
    OFF the beat in half-time bass music and drags a note-chasing tracker."""
    n = int(0.22 * rate)
    t = np.arange(n) / rate
    freq = 55 + 15 * np.exp(-t * 40)
    return (np.sin(2 * np.pi * np.cumsum(freq) / rate) * _env(n, rate, 0.15)).astype(np.float32)


def _saw_bass(rate: int) -> np.ndarray:
    """The same note as _bass (pitch drop, envelope) with a SAWTOOTH waveform: harmonics all the way up the
    spectrum, like the buzzy bass of real half-time bass music. Round 1's grid trackers held the sine bass and
    lost the beat to this one (bright-bass probe, 2026-10-22), so round 2 scores both."""
    n = int(0.22 * rate)
    t = np.arange(n) / rate
    freq = 55 + 15 * np.exp(-t * 40)
    ph = np.cumsum(freq) / rate
    return ((2.0 * (ph % 1.0) - 1.0) * _env(n, rate, 0.15)).astype(np.float32)


# 16th positions (0-15 in a 4/4 bar) where the syncopated bass lands: never on a beat (0, 4, 8, 12).
SYNC_BASS_16THS = (3, 6, 10, 13, 15)


def _click(rate: int) -> np.ndarray:
    n = int(0.01 * rate)
    return (np.sin(2 * np.pi * 1500 * np.arange(n) / rate) * _env(n, rate, 0.003)).astype(np.float32)


def _place(buf: np.ndarray, sound: np.ndarray, t: float, rate: int, gain: float = 1.0) -> None:
    i = int(round(t * rate))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sound))
    buf[i:j] += gain * sound[: j - i]


def synth_case(name: str, bpm: float, secs: float = 30.0, rate: int = 44100, style: str = "drums",
               offset: float = 0.5, swing: float = 0.0, ramp_to: Optional[float] = None, noise: float = 0.0,
               seed_bpm: Optional[float] = None, rng_seed: int = 7, step_at: Optional[float] = None,
               step_to: Optional[float] = None, bass: str = "sine") -> Case:
    """Exact-ground-truth audio. style: click | drums | sparse (kick only on 1, hats off) | offbeat (hats
    on the 'and', the classic octave trap) | halftime_bass (kick on 1, snare on 3, soft quarter hats, and LOUD
    sub-bass hits on syncopated 16ths, never on a beat -- tonight's TYNAN failure, 2026-10-22)."""
    rng = np.random.default_rng(rng_seed)
    beats = beat_times(bpm, secs, offset, ramp_to, step_at, step_to)
    buf = np.zeros(int(secs * rate) + rate, dtype=np.float32)
    kick, snare, hat, click = _kick(rate), _snare(rate, rng), _hat(rate, rng), _click(rate)
    bass_note = _saw_bass(rate) if bass == "saw" else _bass(rate)
    for k, t in enumerate(beats):
        nxt = beats[k + 1] if k + 1 < len(beats) else t + 60.0 / bpm
        half = t + (nxt - t) * (0.5 + swing / 2)
        pos = k % 4
        if style == "click":
            _place(buf, click, t, rate, 1.0 if pos == 0 else 0.6)
        elif style == "halftime_bass":
            if pos == 0:
                _place(buf, kick, t, rate)
            if pos == 2:
                _place(buf, snare, t, rate, 0.9)
            _place(buf, hat, t, rate, 0.4)
            for sub in range(4):                              # this beat's four 16ths
                if pos * 4 + sub in SYNC_BASS_16THS:
                    _place(buf, bass_note, t + (nxt - t) * sub / 4, rate, 1.3)
        elif style == "sparse":
            if pos == 0:
                _place(buf, kick, t, rate)
        else:
            if pos in (0, 2):
                _place(buf, kick, t, rate)
            if pos in (1, 3):
                _place(buf, snare, t, rate, 0.8)
            if style == "offbeat":
                _place(buf, hat, half, rate, 1.4)
            else:
                _place(buf, hat, t, rate)
                _place(buf, hat, half, rate, 0.7)
    if noise:
        buf += (noise * rng.standard_normal(len(buf))).astype(np.float32)
    peak = float(np.max(np.abs(buf))) or 1.0
    audio = (buf / peak * 0.8)[: int(secs * rate)].astype(np.float32)
    ref_bpm = float(np.median(60.0 / np.diff(beats))) if len(beats) > 1 else bpm
    return Case(name, audio, rate, beats, ref_bpm, seed_bpm=seed_bpm, source="synthetic",
                meta={"style": style, "swing": swing, "ramp_to": ramp_to, "noise": noise, "offset": offset,
                      "step_at": step_at, "step_to": step_to, "bass": bass})


def synthetic_suite(rate: int = 44100, secs: float = 30.0) -> List[Case]:
    """The standing synthetic suite: easy, tempo range, octave traps, swing, a ramp, noise, sparse."""
    s = []
    for bpm in (70, 92, 120, 128, 140, 174):
        s.append(synth_case(f"drums_{bpm}", bpm, secs, rate))
    s.append(synth_case("click_100", 100, secs, rate, style="click"))
    s.append(synth_case("offbeat_hats_95", 95, secs, rate, style="offbeat"))
    s.append(synth_case("offbeat_hats_95_seeded", 95, secs, rate, style="offbeat", seed_bpm=95))
    s.append(synth_case("swing_110", 110, secs, rate, swing=0.33))
    s.append(synth_case("ramp_100_to_130", 100, secs, rate, ramp_to=130))
    s.append(synth_case("noisy_124", 124, secs, rate, noise=0.25))
    s.append(synth_case("sparse_kick_85", 85, secs, rate, style="sparse"))
    s.append(synth_case("dnb_174_seeded_87", 174, secs, rate, seed_bpm=87))   # a seed off by an octave
    return s


def drift_suite(rate: int = 44100, secs: float = 40.0) -> List[Case]:
    """Grid-holding under syncopation (Daniel 2026-10-22: "its drifting, i want our beat detection to detect the
    grid not just the spaced out notes"). Half-time drums with loud off-beat sub-bass; the tempo is constant, so
    any BPM spread or flip after lock is the tracker chasing notes instead of holding the grid."""
    s = []
    for bpm in (140, 150, 128):
        s.append(synth_case(f"halftime_bass_{bpm}", bpm, secs, rate, style="halftime_bass"))
    s.append(synth_case("halftime_bass_140_seeded", 140, secs, rate, style="halftime_bass", seed_bpm=140))
    s.append(synth_case("halftime_bass_140_noisy", 140, secs, rate, style="halftime_bass", noise=0.15))
    return s


def bright_drift_suite(rate: int = 44100, secs: float = 40.0) -> List[Case]:
    """Round 2 (pre-registered 2026-10-22): the drift suite with a BRIGHT (sawtooth) bass. Same patterns, tempi,
    seed and noise as drift_suite; only the bass timbre changes. A tracker must hold the beat here too, because
    real half-time bass music (TYNAN) has harmonic-rich bass, not a sine."""
    s = []
    for bpm in (140, 150, 128):
        s.append(synth_case(f"bright_bass_{bpm}", bpm, secs, rate, style="halftime_bass", bass="saw"))
    s.append(synth_case("bright_bass_140_seeded", 140, secs, rate, style="halftime_bass", seed_bpm=140, bass="saw"))
    s.append(synth_case("bright_bass_140_noisy", 140, secs, rate, style="halftime_bass", noise=0.15, bass="saw"))
    return s


def shift_suite(rate: int = 44100, secs: float = 40.0) -> List[Case]:
    """Real tempo changes the tracker must FOLLOW (not hold): a sudden step at 20 s. Scored by relock_s, the time
    from the step until 8 consecutive beats hit again. The drift metrics do not apply here, because the shift is
    real."""
    return [
        synth_case("shift_128_to_140", 128, secs, rate, step_at=20.0, step_to=140),
        synth_case("shift_140_to_128_halftime", 140, secs, rate, style="halftime_bass", step_at=20.0, step_to=128),
        synth_case("shift_120_to_150", 120, secs, rate, step_at=20.0, step_to=150),
        synth_case("shift_150_to_120_seeded", 150, secs, rate, step_at=20.0, step_to=120, seed_bpm=150),
    ]


# --- held-out bright-bass variants (round 2 revision) ----------------------------------------------------------
# The bright suite above is ONE timbre (a naive sawtooth with a hard cut at 220 ms), one pattern, three tempi, all
# public: a tracker can be tuned onto it. These cases come from a seed, and the gating seed is kept secret until
# scoring, so nobody can tune on them. Each case varies what a real bright bass varies: the timbre, the root and
# glide, whether the bass lands ON beats, sidechain pumping, the tempo, and where in the bar the audio starts.

BASS_TIMBRES = ("square", "saw_blep", "saw_pair", "fm", "soft_sine")
BASS_PATTERNS = ("offbeat", "onbeat", "sidechain")
BASS_ROOT_HZ = (35.0, 90.0)
VARIANT_BPM = (125.0, 175.0)
BASS_RELEASE_S = 0.005   # every bass note fades to zero over its last 5 ms: no hard-cut click at a note's end
BASS_ATTACK_S = 0.0015   # and rises from zero over 1.5 ms: a sharp onset without a waveform-step click
_OFFBEAT_16THS = (1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15)


def _polyblep(ph: np.ndarray, dt: np.ndarray) -> np.ndarray:
    """The polyBLEP residual of a unit downward step at phase 0 (Valimaki & Huovilainen 2007). Subtracted from a
    naive sawtooth it band-limits the jump, so the bass has no aliased fizz above the harmonics a real synth has."""
    out = np.zeros_like(ph)
    a = ph < dt
    x = ph[a] / dt[a]
    out[a] = x + x - x * x - 1.0
    b = ph > 1.0 - dt
    x = (ph[b] - 1.0) / dt[b]
    out[b] = x * x + x + x + 1.0
    return out


def _phase(freq: np.ndarray, rate: int, ph0: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    dt = freq / rate
    return (ph0 + np.cumsum(dt) - dt[0]) % 1.0, dt


def _blep_saw(freq: np.ndarray, rate: int, ph0: float = 0.5) -> np.ndarray:
    ph, dt = _phase(freq, rate, ph0)
    return 2.0 * ph - 1.0 - _polyblep(ph, dt)


def _blep_square(freq: np.ndarray, rate: int, ph0: float = 0.0) -> np.ndarray:
    ph, dt = _phase(freq, rate, ph0)
    sq = np.where(ph < 0.5, 1.0, -1.0)
    return sq + _polyblep(ph, dt) - _polyblep((ph + 0.5) % 1.0, dt)


def bass_note(timbre: str, f0: float, dur: float, rate: int, glide_from: Optional[float] = None,
              glide_s: float = 0.04, decay_s: Optional[float] = 0.2, detune: float = 0.008, fm_ratio: float = 1.0,
              fm_index: float = 3.0, drive: float = 4.0) -> np.ndarray:
    """One bass note, `dur` seconds long INCLUDING its 5 ms release (the last sample is exactly zero).
    timbre: square | saw_blep (band-limited saw) | saw_pair (two detuned saws, a reese) | fm | soft_sine (tanh).
    glide_from: start at this frequency and slide exponentially to f0 (time constant glide_s). decay_s None =
    sustained (a pad-like bass for sidechain pumping), else an exponential pluck decay."""
    n = max(4, int(round(dur * rate)))
    t = np.arange(n) / rate
    freq = np.full(n, float(f0))
    if glide_from:
        freq = f0 * (glide_from / f0) ** np.exp(-t / glide_s)
    if timbre == "square":
        y = _blep_square(freq, rate)
    elif timbre == "saw_blep":
        y = _blep_saw(freq, rate)
    elif timbre == "saw_pair":
        y = 0.5 * (_blep_saw(freq * (1 + detune), rate, 0.5) + _blep_saw(freq * (1 - detune), rate, 0.25))
    elif timbre == "fm":
        ph, _ = _phase(freq, rate)
        index = fm_index * (0.3 + 0.7 * np.exp(-t / 0.12))
        y = np.sin(2 * np.pi * ph + index * np.sin(2 * np.pi * ((ph * fm_ratio) % 1.0)))
    elif timbre == "soft_sine":
        ph, _ = _phase(freq, rate)
        y = np.tanh(drive * np.sin(2 * np.pi * ph)) / np.tanh(drive)
    else:
        raise ValueError(f"unknown bass timbre {timbre!r}; choose from {BASS_TIMBRES}")
    env = np.ones(n) if decay_s is None else np.exp(-t / decay_s)
    na, nr = max(1, int(round(BASS_ATTACK_S * rate))), max(2, int(round(BASS_RELEASE_S * rate)))
    env[:na] *= np.linspace(0.0, 1.0, na, endpoint=False)
    env[-nr:] *= np.linspace(1.0, 0.0, nr)
    return (y * env).astype(np.float32)


def _fold_into(f: float, lo: float = BASS_ROOT_HZ[0], hi: float = BASS_ROOT_HZ[1]) -> float:
    while f > hi:
        f /= 2.0
    while f < lo:
        f *= 2.0
    return f


def bass_positions(pattern: str, rng: np.random.Generator) -> List[int]:
    """The 16th positions (0-15 in a 4/4 bar) a bar of bass plays. offbeat never touches a beat; onbeat always
    plays beat one and maybe other beats, plus a few off-beat 16ths; sidechain holds long notes from beat one
    (and maybe beat three) that the ducking pumps."""
    if pattern == "offbeat":
        k = int(rng.integers(3, 7))
        return sorted(int(x) for x in rng.choice(_OFFBEAT_16THS, size=k, replace=False))
    if pattern == "onbeat":
        on = [0] + [b for b in (4, 8, 12) if rng.random() < 0.5]
        off = [int(x) for x in rng.choice(_OFFBEAT_16THS, size=int(rng.integers(1, 4)), replace=False)]
        return sorted(set(on + off))
    if pattern == "sidechain":
        return [0, 8] if rng.random() < 0.5 else [0]
    raise ValueError(f"unknown bass pattern {pattern!r}; choose from {BASS_PATTERNS}")


def _duck_curve(n: int, rate: int, beats: np.ndarray, depth: float, tau_s: float) -> np.ndarray:
    """Sidechain ducking: the gain drops to 1 - depth AT every beat (over a 5 ms ramp, so the drop is not a click)
    and recovers exponentially with time constant tau_s. The bass is quietest on the beat and swells between."""
    g = np.ones(n)
    pre = BASS_RELEASE_S
    for b in beats:
        i0, i1 = int(round((b - pre) * rate)), int(round((b + 6 * tau_s) * rate))
        lo, hi = max(0, i0), min(n, i1)
        if hi <= lo:
            continue
        t = np.arange(lo, hi) / rate - b
        dip = np.where(t < 0, depth * (1.0 + t / pre), depth * np.exp(-np.maximum(t, 0.0) / tau_s))
        g[lo:hi] = np.minimum(g[lo:hi], 1.0 - np.clip(dip, 0.0, depth))
    return g


def bright_variant_case(name: str, p: Dict, rate: int = 44100, secs: float = 40.0,
                        rng_seed: Sequence[int] = (0,)) -> Case:
    """One held-out bright-bass case from its parameters (see bright_variants_suite). The audio begins at a random
    16th (p["start16"], 1-15) of a bar after a whole bar of run-in, so it never starts on beat one and the first
    sounds are tails of notes already playing. Ground truth is exact, as in synth_case."""
    rng = np.random.default_rng(list(rng_seed))
    bpm = float(p["bpm"])
    period = 60.0 / bpm
    six = period / 4.0
    pre = 4 * period + int(p["start16"]) * six
    n_total = int((pre + secs + 1.0) * rate) + rate
    drums = np.zeros(n_total, dtype=np.float32)
    bass = np.zeros(n_total, dtype=np.float32)
    kick, snare, hat = _kick(rate), _snare(rate, rng), _hat(rate, rng)
    grid = np.arange(int((pre + secs + 1.0) / period) + 2) * period
    for k, t in enumerate(grid):
        pos = k % 4
        if p["drums"] == "halftime":
            if pos == 0:
                _place(drums, kick, t, rate)
            if pos == 2:
                _place(drums, snare, t, rate, 0.9)
            _place(drums, hat, t, rate, 0.4)
        else:                                                     # four on the floor
            _place(drums, kick, t, rate)
            if pos in (1, 3):
                _place(drums, snare, t, rate, 0.8)
            _place(drums, hat, t + period / 2, rate, 0.7)
    positions = bass_positions(p["pattern"], rng)
    phrase = [0] + [int(x) for x in rng.choice((0, 3, 5, 7, -2, -4), size=3)]   # semitones per bar, 4-bar phrase
    decay = None if p["pattern"] == "sidechain" else float(rng.uniform(0.08, 0.3))
    detune, fm_ratio = float(rng.uniform(0.004, 0.012)), float(rng.choice((0.5, 1.0, 2.0)))
    fm_index, drive = float(rng.uniform(1.5, 5.0)), float(rng.uniform(2.0, 6.0))
    starts, freqs = [], []
    for bar in range(len(grid) // 4 + 1):
        f = _fold_into(float(p["root_hz"]) * 2 ** (phrase[bar % 4] / 12.0))
        for pos in positions:
            starts.append(bar * 4 * period + pos * six)
            freqs.append(f)
    prev_f = freqs[0] * 2 ** (7 / 12.0) if freqs else None
    for i, (t0, f) in enumerate(zip(starts, freqs)):
        nxt = starts[i + 1] if i + 1 < len(starts) else t0 + 4 * period
        want = (nxt - t0) if p["pattern"] == "sidechain" else float(rng.integers(1, 4)) * six
        note = bass_note(p["timbre"], f, min(want, nxt - t0), rate,
                         glide_from=(prev_f if p.get("glide") else None), glide_s=float(p.get("glide_s", 0.04)),
                         decay_s=decay, detune=detune, fm_ratio=fm_ratio, fm_index=fm_index, drive=drive)
        _place(bass, note, t0, rate)
        prev_f = f
    if p["pattern"] == "sidechain":
        bass *= _duck_curve(n_total, rate, grid, float(p.get("duck_depth", 0.85)),
                            float(p.get("duck_tau_beats", 0.3)) * period).astype(np.float32)
    buf = drums + float(p["bass_gain"]) * bass
    if p.get("noise"):
        buf += (float(p["noise"]) * rng.standard_normal(n_total)).astype(np.float32)
    c0 = int(math.floor(pre * rate))                  # never past a beat that falls exactly on the first sample
    audio = buf[c0:c0 + int(secs * rate)]
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = (audio / peak * 0.8).astype(np.float32)
    shift = c0 / rate
    beats = grid[(grid >= shift) & (grid - shift < secs)] - shift
    meta = {**p, "style": "bright_variant", "bass_16ths": positions, "phrase_semitones": phrase,
            "decay_s": decay, "detune": detune, "fm_ratio": fm_ratio, "fm_index": fm_index, "drive": drive}
    return Case(name, audio, rate, beats, bpm, source="synthetic", meta=meta)


def bright_variants_suite(seed: int, n: int = 10, rate: int = 44100, secs: float = 40.0) -> List[Case]:
    """Round 2's HELD-OUT bright-bass row: n cases drawn from `seed`. The gating seed is kept secret until scoring,
    so no tracker can be tuned on these cases; any other seed is free for development. Every timbre and pattern
    appears (each cycles through a shuffled order), tempi are 125-175 BPM, roots 35-90 Hz, half the cases glide,
    and each case starts at a random 16th, never on beat one."""
    pick = np.random.default_rng(int(seed))
    order_t = [BASS_TIMBRES[i] for _ in range(math.ceil(n / len(BASS_TIMBRES)))
               for i in pick.permutation(len(BASS_TIMBRES))][:n]
    order_p = [BASS_PATTERNS[i] for _ in range(math.ceil(n / len(BASS_PATTERNS)))
               for i in pick.permutation(len(BASS_PATTERNS))][:n]
    cases = []
    for i in range(n):
        p = {"bpm": round(float(pick.uniform(*VARIANT_BPM)), 1), "timbre": order_t[i], "pattern": order_p[i],
             "root_hz": round(float(pick.uniform(*BASS_ROOT_HZ)), 2), "glide": bool(pick.random() < 0.5),
             "glide_s": round(float(pick.uniform(0.02, 0.08)), 3), "start16": int(pick.integers(1, 16)),
             "drums": "halftime" if pick.random() < 0.7 else "fourfloor",
             "bass_gain": round(float(pick.uniform(1.0, 1.6)), 2),
             "duck_depth": round(float(pick.uniform(0.6, 0.95)), 2),
             "duck_tau_beats": round(float(pick.uniform(0.2, 0.45)), 2),
             "noise": round(float(pick.uniform(0.0, 0.08)), 3) if pick.random() < 0.3 else 0.0}
        cases.append(bright_variant_case(f"bvar_{i:02d}_{p['timbre']}_{p['pattern']}_{p['bpm']:g}", p, rate, secs,
                                         rng_seed=(int(seed), i)))
    return cases


def file_case(path: str, bpm: float, phase_known: bool = False, offset: float = 0.0,
              seed_bpm: Optional[float] = None, max_secs: Optional[float] = 60.0) -> Case:
    """A real recording with a known tempo (e.g. an FL render). Mono-mixed; soundfile reads wav/flac/ogg/mp3."""
    import soundfile as sf
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    audio = data.mean(axis=1)
    if max_secs:
        audio = audio[: int(max_secs * rate)]
    secs = len(audio) / rate
    beats = beat_times(bpm, secs, offset) if phase_known else np.array([])
    return Case(os.path.basename(path), audio.astype(np.float32), rate, beats, float(bpm), seed_bpm=seed_bpm,
                phase_known=phase_known, source="file", meta={"path": path})


# --- metrics ------------------------------------------------------------------------------------------------

def _trim(b: np.ndarray, start: float) -> np.ndarray:
    return b[b >= start]


def f_measure(est: np.ndarray, ref: np.ndarray, window: float = F_WINDOW) -> float:
    """Greedy one-to-one matching within +-window (each reference beat matched at most once)."""
    if len(ref) == 0 and len(est) == 0:
        return 1.0
    if len(ref) == 0 or len(est) == 0:
        return 0.0
    used = np.zeros(len(est), dtype=bool)
    hits = 0
    for r in ref:
        d = np.abs(est - r)
        d[used] = np.inf
        j = int(np.argmin(d))
        if d[j] <= window:
            used[j] = True
            hits += 1
    p, rc = hits / len(est), hits / len(ref)
    return 0.0 if hits == 0 else 2 * p * rc / (p + rc)


def _continuity_total(est: np.ndarray, ref: np.ndarray, tol: float = CONT_TOL) -> float:
    """Share of reference beats matched by an estimate within tol of the local inter-beat interval, where the
    estimate's own interval also agrees within tol (the 'total' continuity variant)."""
    if len(ref) < 2 or len(est) < 2:
        return 0.0
    ok = 0
    for i in range(1, len(ref)):
        ibi = ref[i] - ref[i - 1]
        j = int(np.argmin(np.abs(est - ref[i])))
        if abs(est[j] - ref[i]) > tol * ibi or j == 0:
            continue
        if abs((est[j] - est[j - 1]) - ibi) <= tol * ibi:
            ok += 1
    return ok / (len(ref) - 1)


def _variants(ref: np.ndarray) -> List[np.ndarray]:
    """The allowed metrical variations for AML: as-is, off-beat, double, half (both phases)."""
    out = [ref]
    if len(ref) >= 2:
        mids = (ref[:-1] + ref[1:]) / 2
        out.append(mids)                                       # off-beat
        dbl = np.sort(np.concatenate([ref, mids]))
        out.append(dbl)                                        # double tempo
        out.append(ref[::2])                                   # half tempo, phase 0
        out.append(ref[1::2])                                  # half tempo, phase 1
    return out


def cml_aml(est: np.ndarray, ref: np.ndarray) -> Dict[str, float]:
    cmlt = _continuity_total(est, ref)
    amlt = max(_continuity_total(est, v) for v in _variants(ref)) if len(ref) else 0.0
    return {"CMLt": cmlt, "AMLt": max(cmlt, amlt)}


def tempo_acc(est_bpm: float, ref_bpm: float) -> Dict[str, bool]:
    if not est_bpm or not ref_bpm:
        return {"Acc1": False, "Acc2": False}
    def near(x):
        return abs(est_bpm - x) <= TEMPO_TOL * x
    return {"Acc1": near(ref_bpm), "Acc2": any(near(ref_bpm * k) for k in (1, 2, 0.5, 3, 1 / 3))}


def lock_time(est: np.ndarray, ref: np.ndarray, run: int = 8, window: float = F_WINDOW) -> Optional[float]:
    """The first reference beat from which `run` consecutive reference beats are all hit."""
    if len(est) == 0 or len(ref) < run:
        return None
    hit = np.array([np.min(np.abs(est - r)) <= window for r in ref])
    for i in range(len(ref) - run + 1):
        if hit[i:i + run].all():
            return float(ref[i])
    return None


# --- running a tracker ----------------------------------------------------------------------------------------

def dedupe(events: List[dict], merge: float = 0.05) -> List[dict]:
    """A tracker may re-announce the same beat as its prediction sharpens: keep the LAST word on each beat."""
    out: List[dict] = []
    for ev in sorted(events, key=lambda e: (e["t_beat"], e["_at"])):
        if out and ev["t_beat"] - out[-1]["t_beat"] < merge:
            if ev["_at"] >= out[-1]["_at"]:
                out[-1] = ev
        else:
            out.append(ev)
    return out


def run_tracker(factory: Callable, case: Case, hop: int = 512) -> Dict:
    """Feed the case block by block and, after EVERY block, ask predict() exactly as beatsync does; ahead[0] is
    the beat the lights would paint next, so that is the prediction scored (a tracker cannot be flattered by the
    bench picking a better item from its list, or by being asked only every 100 ms). Speed: the CPU time
    (process_time) of feed() + predict() per block is summed, alongside the wall time of the whole run."""
    tracker = factory(case.rate, hop, seed_bpm=case.seed_bpm)
    predict = getattr(tracker, "predict", None)
    can_predict = callable(predict)
    events: List[dict] = []
    preds: List[dict] = []
    proc = 0.0
    t0 = time.perf_counter()
    n_blocks = len(case.audio) // hop
    for b in range(n_blocks):
        block = case.audio[b * hop:(b + 1) * hop]
        at = (b + 1) * hop / case.rate
        c0 = _cpu_clock()
        out = tracker.feed(block)
        ahead = predict(at) if can_predict else None
        proc += _cpu_clock() - c0
        for ev in out or []:
            events.append({**ev, "_at": at})
        if ahead:
            preds.append({"asked_at": at, "t_next": float(ahead[0]["t_beat"])})
    wall = time.perf_counter() - t0
    beats = dedupe(events)
    audio_s = len(case.audio) / case.rate
    return {"beats": beats, "predictions": preds, "cpu_s": wall, "proc_s": proc, "audio_s": audio_s,
            "realtime_x": audio_s / wall if wall > 0 else float("inf"),
            "cpu_x": audio_s / proc if proc > 0 else float("inf")}


def _in_spans(x: np.ndarray, spans: Optional[Sequence]) -> np.ndarray:
    """Index of the span each time falls in, -1 outside all of them (no spans = everything in span 0)."""
    x = np.asarray(x, dtype=float)
    if not spans:
        return np.zeros(len(x), dtype=int)
    idx = np.full(len(x), -1, dtype=int)
    for k, (a, b) in enumerate(spans):
        idx[(x >= a) & (x < b) & (idx < 0)] = k
    return idx


def prediction_error(preds: List[dict], ref: np.ndarray, after: float, min_lead: float = 0.05,
                     spans: Optional[Sequence] = None) -> Dict:
    """For each prediction asked at time a (after lock), compare the predicted next beat with the TRUE next beat
    (the first reference beat after a). Predictions asked less than min_lead before that beat are skipped: too
    late to steer a light by, so they would only flatter the tracker. With spans (a real song's confirmed
    sections), only predictions asked inside a span whose true next beat is in the same span count."""
    ref = np.asarray(ref, dtype=float)
    errs = []
    for p in preds:
        a = p["asked_at"]
        if a < after:
            continue
        j = int(np.searchsorted(ref, a, side="right"))
        if j >= len(ref) or ref[j] - a < min_lead:
            continue
        if spans:
            sa, sb = _in_spans(np.array([a, ref[j]]), spans)
            if sa < 0 or sa != sb:
                continue
        errs.append(abs(p["t_next"] - ref[j]) * 1000)
    if not errs:
        return {}
    return {"pred_err_ms": round(float(np.median(errs)), 1),
            "pred_hit": round(sum(e <= PRED_HIT_MS for e in errs) / len(errs), 3)}


def _good_bpm(x) -> bool:
    try:
        return x is not None and not isinstance(x, bool) and math.isfinite(float(x)) and float(x) > 0
    except (TypeError, ValueError):
        return False


def score(case: Case, result: Dict) -> Dict:
    est = np.array([b["t_beat"] for b in result["beats"]])
    late = [b for b in result["beats"] if b["t_beat"] >= SKIP_FIRST]
    late_bpm = [float(b["bpm"]) for b in late if _good_bpm(b.get("bpm"))]
    est_bpm = float(np.median(late_bpm)) if late_bpm else (
        float(60.0 / np.median(np.diff(est))) if len(est) > 2 else 0.0)
    out = {"case": case.name, "ref_bpm": round(case.bpm, 2), "est_bpm": round(est_bpm, 2), **tempo_acc(est_bpm, case.bpm),
           "realtime_x": round(result["realtime_x"], 1)}
    if "cpu_x" in result:
        out["cpu_x"] = round(result["cpu_x"], 1) if math.isfinite(result["cpu_x"]) else result["cpu_x"]
    if late_bpm:
        # each locked-state bpm with its OWN beat (a beat with no bpm is counted by drift(), never misaligned here)
        octave = [abs(x - 2 * case.bpm) <= TEMPO_TOL * 2 * case.bpm or abs(x - case.bpm / 2) <= TEMPO_TOL * case.bpm / 2
                  for x in late_bpm]
        out["octave_err"] = round(sum(octave) / len(octave), 3)
    spans = (case.meta or {}).get("spans")
    out.update(drift(result["beats"], start=SKIP_FIRST))
    out.update(ibi_drift(result["beats"], start=SKIP_FIRST, spans=spans))
    leads = [(b["t_beat"] - b["_at"]) * 1000 for b in result["beats"]]
    if leads:
        out["lead_ms"] = round(float(np.median(leads)), 1)
    if case.phase_known and len(case.beats):
        ref_t, est_t = _trim(case.beats, SKIP_FIRST), _trim(est, SKIP_FIRST)
        if spans:
            # a real song is scored only inside the sections a person has confirmed by ear; quiet bits and
            # breakdowns between them have no reference beat, so neither side is counted there
            ref_t, est_t = ref_t[_in_spans(ref_t, spans) >= 0], est_t[_in_spans(est_t, spans) >= 0]
        out["F"] = round(f_measure(est_t, ref_t), 3)
        out.update({k: round(v, 3) for k, v in cml_aml(est_t, ref_t).items()})
        lt = lock_time(est, case.beats)
        out["lock_s"] = round(lt, 2) if lt is not None else None
        step_at = (case.meta or {}).get("step_at")
        if step_at is not None:
            after = case.beats[case.beats >= step_at]
            rl = lock_time(est, after)
            out["relock_s"] = round(rl - step_at, 2) if rl is not None else None
        if result.get("predictions"):
            out.update(prediction_error(result["predictions"], case.beats, after=lt if lt is not None else SKIP_FIRST,
                                        spans=spans))
    return out


FLIP_RATIO = 0.08   # a reported tempo jumping more than 8 % between consecutive beats counts as a flip


def _spread_flips(v: np.ndarray, seqs: Optional[List[np.ndarray]] = None) -> Tuple[float, int]:
    med = float(np.median(v))
    spread = float((np.percentile(v, 90) - np.percentile(v, 10)) / med) if med else 0.0
    flips = sum(int(np.sum(np.abs(s[1:] / s[:-1] - 1.0) > FLIP_RATIO)) for s in (seqs or [v]) if len(s) > 1)
    return spread, flips


def drift(beats: List[dict], start: float = SKIP_FIRST) -> Dict:
    """How steady the DISPLAYED tempo is once settled. Music made in a DAW has a constant grid, so on constant-
    tempo material any spread or flip is the tracker chasing notes rather than holding the grid.
      bpm_spread   (p90 - p10) / median of the reported bpm after `start`; 0 = rock steady
      tempo_flips  consecutive reported bpm values differing by more than FLIP_RATIO
      bpm_missing  beats after `start` that carry no usable bpm (missing, zero, negative, not finite): counted,
                   because dropping them silently would let a tracker hide its unsure beats from the two above"""
    late = [b for b in beats if b["t_beat"] >= start]
    vals = [float(b["bpm"]) for b in late if _good_bpm(b.get("bpm"))]
    out: Dict = {"bpm_missing": len(late) - len(vals)}
    if len(vals) < 3:
        return out
    spread, flips = _spread_flips(np.array(vals))
    out.update({"bpm_spread": round(spread, 4), "tempo_flips": flips})
    return out


def ibi_drift(beats: List[dict], start: float = SKIP_FIRST, spans: Optional[Sequence] = None) -> Dict:
    """Grid steadiness from the beat TIMES: bpm_spread and tempo_flips' own definitions applied to 60 / inter-beat
    interval of the observed (deduped) beats after `start`. A tracker may smooth the bpm it displays; it cannot
    smooth these without moving its beats. With spans (a real song's confirmed sections) an interval counts only
    when both of its beats lie in the same span, so a breakdown between sections is never read as a tempo change.
      ibi_spread  (p90 - p10) / median of 60 / IBI
      ibi_flips   consecutive 60 / IBI values (within one span) differing by more than FLIP_RATIO"""
    t = np.array(sorted(b["t_beat"] for b in beats if b["t_beat"] >= start), dtype=float)
    if len(t) < 2:
        return {}
    span = _in_spans(t, spans)
    seqs = []
    for k in sorted(set(span[span >= 0].tolist())):
        tk = t[span == k]
        ibi = np.diff(tk)
        ibi = ibi[ibi > 0]
        if len(ibi):
            seqs.append(60.0 / ibi)
    if not seqs or sum(len(s) for s in seqs) < 3:
        return {}
    spread, flips = _spread_flips(np.concatenate(seqs), seqs)
    return {"ibi_spread": round(spread, 4), "ibi_flips": flips}


def summarize(rows: List[Dict]) -> Dict:
    def num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)
    def mean(key):
        vals = [r[key] for r in rows if num(r.get(key))]
        return round(float(np.mean(vals)), 3) if vals else None
    def share(key):
        vals = [bool(r[key]) for r in rows if key in r]
        return round(sum(vals) / len(vals), 3) if vals else None
    def lowest(key):
        vals = [r[key] for r in rows if num(r.get(key))]
        return round(float(min(vals)), 3) if vals else None
    locks = [r["lock_s"] for r in rows if r.get("lock_s") is not None]
    return {"cases": len(rows), "F": mean("F"), "CMLt": mean("CMLt"), "AMLt": mean("AMLt"),
            "min_F": lowest("F"), "min_CMLt": lowest("CMLt"), "Acc1": share("Acc1"),
            "Acc2": share("Acc2"), "octave_err": mean("octave_err"), "lead_ms": mean("lead_ms"),
            "lock_s_median": round(float(np.median(locks)), 2) if locks else None,
            "never_locked": sum(1 for r in rows if "lock_s" in r and r["lock_s"] is None),
            "pred_err_ms": mean("pred_err_ms"), "pred_hit": mean("pred_hit"),
            "bpm_spread": mean("bpm_spread"), "tempo_flips": mean("tempo_flips"),
            "ibi_spread": mean("ibi_spread"), "ibi_flips": mean("ibi_flips"),
            "bpm_missing": sum(int(r.get("bpm_missing") or 0) for r in rows),
            "relock_s": mean("relock_s"),
            "never_relocked": sum(1 for r in rows if "relock_s" in r and r["relock_s"] is None),
            "realtime_x_min": min((r["realtime_x"] for r in rows), default=None),
            "cpu_x_min": min((r["cpu_x"] for r in rows if num(r.get("cpu_x"))), default=None)}


# --- reference trackers (baselines) ----------------------------------------------------------------------------

class AubioTracker:
    """Baseline row: aubio's online tracker (GPLv3+, optional; imported lazily, never vendored)."""

    def __init__(self, rate: int, hop: int, seed_bpm: Optional[float] = None):
        import aubio
        self.rate, self.hop = rate, hop
        self.t = aubio.tempo("default", hop * 2, hop, rate)

    def feed(self, block: np.ndarray) -> List[dict]:
        if self.t(block.astype(np.float32))[0]:
            return [{"t_beat": float(self.t.get_last_s()), "bpm": float(self.t.get_bpm()),
                     "confidence": float(self.t.get_confidence())}]
        return []


class LibrosaOffline:
    """Reference row, NOT live: librosa's offline dynamic-programming tracker (Ellis 2007, ISC licence) run on the
    whole case at the end. It sees the future, so it is an upper-bound-ish yardstick; its lead_ms is meaningless."""

    def __init__(self, rate: int, hop: int, seed_bpm: Optional[float] = None):
        self.rate, self.hop, self.seed, self.buf = rate, hop, seed_bpm, []

    def feed(self, block: np.ndarray) -> List[dict]:
        self.buf.append(block)
        return []

    def finish(self) -> List[dict]:
        import librosa
        y = np.concatenate(self.buf)
        kw = {"start_bpm": self.seed} if self.seed else {}
        tempo, frames = librosa.beat.beat_track(y=y, sr=self.rate, hop_length=self.hop, units="frames", **kw)
        times = librosa.frames_to_time(frames, sr=self.rate, hop_length=self.hop)
        bpm = float(np.atleast_1d(tempo)[0])
        return [{"t_beat": float(t), "bpm": bpm, "confidence": 1.0} for t in times]


def run_offline(factory: Callable, case: Case, hop: int = 512) -> Dict:
    r = run_tracker(factory, case, hop)
    tracker = factory(case.rate, hop, seed_bpm=case.seed_bpm)
    for b in range(len(case.audio) // hop):
        tracker.feed(case.audio[b * hop:(b + 1) * hop])
    t0, c0 = time.perf_counter(), _cpu_clock()
    evs = [{**e, "_at": len(case.audio) / case.rate} for e in tracker.finish()]
    r["beats"], r["cpu_s"], r["proc_s"] = dedupe(evs), time.perf_counter() - t0, _cpu_clock() - c0
    r["realtime_x"] = r["audio_s"] / r["cpu_s"] if r["cpu_s"] > 0 else float("inf")
    r["cpu_x"] = r["audio_s"] / r["proc_s"] if r["proc_s"] > 0 else float("inf")
    return r


TRACKERS: Dict[str, Dict] = {
    "aubio": {"factory": AubioTracker, "offline": False, "note": "GPLv3+, optional, baseline"},
    "librosa": {"factory": LibrosaOffline, "offline": True, "note": "offline reference, sees the future"},
}


def register(name: str, factory: Callable, offline: bool = False, note: str = "") -> None:
    TRACKERS[name] = {"factory": factory, "offline": offline, "note": note}


def _check_unique(names: Iterable[str], what: str = "case") -> None:
    seen, dup = set(), set()
    for n in names:
        (dup if n in seen else seen).add(n)
    if dup:
        raise ValueError(f"duplicate {what} names {sorted(dup)[:5]}: paired comparison matches by name, so every "
                         f"{what} name must be unique")


def bench(cases: Sequence[Case], names: Sequence[str], hop: int = 512, log: Callable[[str], None] = print) -> Dict:
    _check_unique(c.name for c in cases)
    report = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "hop": hop, "trackers": {}}
    for name in names:
        spec = TRACKERS[name]
        rows = []
        for case in cases:
            try:
                res = (run_offline if spec["offline"] else run_tracker)(spec["factory"], case, hop)
                rows.append(score(case, res))
            except ImportError as exc:
                log(f"[beatbench] {name}: unavailable ({exc}); row skipped")
                rows = None
                break
        if rows is None:
            report["trackers"][name] = {"unavailable": True, "note": spec["note"]}
            continue
        report["trackers"][name] = {"note": spec["note"], "summary": summarize(rows), "cases": rows}
        log(f"[beatbench] {name}: " + json.dumps(report["trackers"][name]["summary"]))
    return report


# --- the contract check both blind trackers run against themselves -------------------------------------------------

REQUIRED_KEYS = ("t_beat", "bpm", "phase", "confidence")


def check_tracker(factory: Callable, rate: int = 44100, hop: int = 512) -> List[str]:
    """Conformance with the streaming contract above. Returns problems; [] means it conforms.

    The lights paint from predict(), so a contestant must have one: called after every block (as beatsync calls
    it), whatever it returns must be sorted and strictly in the future, and once the tracker has locked on a plain
    120 BPM drum loop (8 consecutive observed beats on the true beat) it must never come back empty. Every observed
    beat must carry a finite bpm > 0."""
    problems: List[str] = []
    case = synth_case("contract_120", 120, secs=10.0, rate=rate)
    for seed in (None, 120.0):
        try:
            tr = factory(rate, hop, seed_bpm=seed)
        except Exception as exc:
            return [f"factory(rate, hop, seed_bpm={seed}) raised {type(exc).__name__}: {exc}"]
        pred = getattr(tr, "predict", None)
        if not callable(pred):
            problems.append("predict() missing: the lights paint from predict(), so every contestant needs one")
        seen = 0
        observed: List[dict] = []
        polls: List[Tuple[float, bool]] = []
        for b in range(len(case.audio) // hop):
            at = (b + 1) * hop / rate
            out = tr.feed(case.audio[b * hop:(b + 1) * hop])
            if not isinstance(out, list):
                problems.append(f"feed() returned {type(out).__name__}, not list")
                break
            for ev in out:
                seen += 1
                missing = [k for k in REQUIRED_KEYS if k not in ev]
                if missing:
                    problems.append(f"feed() event missing {missing}")
                if "is_downbeat" in ev and ev["is_downbeat"] not in (True, False, None):
                    problems.append("is_downbeat must be True, False or None")
                if not 0.0 <= float(ev.get("confidence", 0)) <= 1.0:
                    problems.append("confidence outside 0..1")
                if "bpm" in ev and not _good_bpm(ev["bpm"]):
                    problems.append("feed() event bpm must be a finite number > 0")
                if "t_beat" in ev:
                    observed.append({**ev, "_at": at})
            if not callable(pred):
                continue
            ahead = pred(at)
            if not isinstance(ahead, list):
                problems.append("predict() must return a list")
                ahead = []
            for p in ahead:
                missing = [k for k in REQUIRED_KEYS if k not in p]
                if missing:
                    problems.append(f"predict() item missing {missing}")
            times = [float(p["t_beat"]) for p in ahead if "t_beat" in p]
            if any(not math.isfinite(x) for x in times):
                problems.append("predict() returned a beat time that is not finite")
            elif any(x <= at for x in times):
                problems.append("predict() returned a beat at or before `now`: the lights would paint the past")
            if len(times) > 1 and any(np.diff(times) <= 0):
                problems.append("predict() beats must be sorted, earliest first (the lights paint ahead[0])")
            polls.append((at, bool(times)))
        if seen == 0:
            problems.append(f"no beats observed on a plain 120 bpm drum loop (seed={seed})")
        else:
            est = np.array([e["t_beat"] for e in dedupe(observed)])
            lt = lock_time(est, case.beats)
            if lt is None:
                problems.append(f"never locked on a plain 120 bpm drum loop (seed={seed})")
            elif callable(pred):
                ref_after = case.beats[case.beats >= lt]
                locked_at = float(ref_after[7]) if len(ref_after) > 7 else float(case.beats[-1])
                empty = [at for at, ok in polls if at >= locked_at and not ok]
                if empty:
                    problems.append(f"predict() came back empty after lock ({len(empty)} of the blocks after "
                                    f"{locked_at:.2f} s, seed={seed})")
        if problems:
            break
    return sorted(set(problems))


# --- real audio: BPM-labelled loops from Daniel's own sample packs (local, private, never committed) ---------------

import re as _re

_BPM_RE = _re.compile(r"(?<!\d)(\d{2,3})\s?bpm", _re.I)
# Three kinds, because they are not equally answerable: a loop WITH a kick marks the beat; a hats/tops/percussion
# loop with no kick leaves beat vs off-beat genuinely ambiguous in isolation (in a song, the kick settles it), so
# AMLt is the fair metric there; melodic loops have no drums at all.
_KICKY = ("drum loop", "drum fill", "breakbeat", "break", "groove", "kick", "full drum", "beat")
_TOPS = ("hat", "top", "perc", "shaker", "clap", "snare", "cymbal", "ride", "tamb", "conga", "bongo")


def parse_bpm(name: str) -> Optional[int]:
    m = _BPM_RE.search(name)
    if not m:
        return None
    bpm = int(m.group(1))
    return bpm if 60 <= bpm <= 200 else None


# Backslashes doubled: in a plain literal "\a" is BEL and "\t" is TAB, so until 2026-10-23 the temp entry matched nothing.
_NOT_A_PACK = ("\\appdata\\local\\temp\\", "pytest-of-", "\\$recycle.bin\\")


def find_bpm_loops(max_results: int = 200000) -> List[str]:
    """Loops whose FILE NAME carries a BPM, from the Everything index (no drive crawl). Reads the WHOLE index (a
    capped slice made the pool an arbitrary first-N that any stray file reshuffled) and skips temp, test and
    recycle-bin copies (the bench's own tests write 'Drum Loop N 120 BPM.wav' files that pytest keeps)."""
    from core.tools.everything import search
    r = search(r"regex:(?i)\d{2,3}\s?bpm.*\.(wav|flac|aiff?|mp3)$", max_results=max_results)
    return [p for p in r.paths if "loop" in p.lower() and parse_bpm(os.path.basename(p))
            and not any(x in p.lower() for x in _NOT_A_PACK)]


def receipt_case_names(paths: Iterable[str]) -> set:
    """The loop FILE NAMES a bench receipt scored (seeded twins and content-hash suffixes folded): the tuning set
    as it actually ran, independent of how the live index has drifted since."""
    import re as _re
    names = set()
    for rp in paths:
        rep_ = json.load(open(rp, encoding="utf-8"))
        for t in rep_.get("trackers", {}).values():
            for row in t.get("cases", []):
                n = row["case"].replace(" [seeded]", "")
                n = _re.sub(r" #[0-9a-f]{8}$", "", n)
                names.add(n.lower())
    return names


def loop_category(path: str) -> str:
    low = os.path.basename(path).lower()
    return "kick" if any(w in low for w in _KICKY) else "tops" if any(w in low for w in _TOPS) else "melodic"


def loop_pack(path: str) -> str:
    """The folder a loop sits in: the cluster for the paired bootstrap. Loops in one folder come from one pack and
    one production (same drummer, sounds, mix), so their per-loop differences are not independent; resampling
    whole folders keeps a big pack from passing for many independent witnesses."""
    return os.path.dirname(os.path.normcase(os.path.abspath(path)))


# --- content identity: the same loop at two paths is ONE loop -------------------------------------------------
# Sample packs get copied (the Desktop holds copies of packs that also live on F:), so a path says nothing about
# whether two loops are the same audio. Identity is (size, sha1 of the file bytes). Hashing every file in a
# several-GB pool on each run would be slow, so files are compared in stages: a file whose size no other file
# shares is unique without being read; files that share a size are compared on a 128 KB head+tail digest first,
# and only files that also share that are hashed in full. Digests are cached by (path, size, mtime).

HASH_CACHE_PATH: Optional[str] = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "state", "arsenal", "keylab", "content-hashes.json")
_HASH_MEM: Dict[str, Dict[str, str]] = {}
_HASH_LOADED = False
_PARTIAL = 65536


def _hash_cache() -> Dict[str, Dict[str, str]]:
    global _HASH_LOADED
    if not _HASH_LOADED:
        _HASH_LOADED = True
        if HASH_CACHE_PATH and os.path.exists(HASH_CACHE_PATH):
            try:
                with open(HASH_CACHE_PATH, encoding="utf-8") as f:
                    _HASH_MEM.update(json.load(f))
            except (OSError, ValueError):
                pass
    return _HASH_MEM


def _save_hash_cache() -> None:
    if not HASH_CACHE_PATH:
        return
    try:
        os.makedirs(os.path.dirname(HASH_CACHE_PATH), exist_ok=True)
        tmp = HASH_CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_HASH_MEM, f)
        os.replace(tmp, HASH_CACHE_PATH)
    except OSError:
        pass


def _stat_key(path: str) -> Optional[Tuple[str, int]]:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return f"{path}|{st.st_size}|{st.st_mtime_ns}", int(st.st_size)


def _digest(path: str, kind: str) -> Optional[str]:
    """kind 'sha1' = the whole file; 'partial' = size + first and last 64 KB (a cheap pre-filter only)."""
    sk = _stat_key(path)
    if sk is None:
        return None
    key, size = sk
    cache = _hash_cache()
    hit = cache.get(key, {}).get(kind)
    if hit:
        return hit
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            if kind == "sha1":
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            else:
                h.update(str(size).encode())
                h.update(f.read(_PARTIAL))
                if size > 2 * _PARTIAL:
                    f.seek(size - _PARTIAL)
                    h.update(f.read(_PARTIAL))
    except OSError:
        return None
    cache.setdefault(key, {})[kind] = h.hexdigest()
    return h.hexdigest()


def file_sha1(path: str) -> Optional[str]:
    return _digest(path, "sha1")


def content_key(path: str) -> Optional[Tuple[int, str]]:
    """(size, sha1 of the bytes): what makes two loop files the same loop."""
    sk = _stat_key(path)
    sha = file_sha1(path) if sk else None
    return (sk[1], sha) if sha else None


def dedupe_by_content(paths: Iterable[str]) -> Tuple[List[str], Dict[str, int]]:
    """Keep one path per distinct content, the first in sorted path order; drop paths that cannot be read. Returns
    (kept, counts) with counts {'unreadable', 'duplicates'}."""
    ordered = sorted(dict.fromkeys(paths))
    sized: Dict[int, List[str]] = {}
    bad, dup = set(), set()
    for p in ordered:
        sk = _stat_key(p)
        if sk is None:
            bad.add(p)
        else:
            sized.setdefault(sk[1], []).append(p)
    for group in sized.values():
        if len(group) < 2:
            continue                                         # a size nobody else has: unique without reading it
        by_partial: Dict[str, List[str]] = {}
        for p in group:
            d = _digest(p, "partial")
            if d is None:
                bad.add(p)
            else:
                by_partial.setdefault(d, []).append(p)
        for same in by_partial.values():
            if len(same) < 2:
                continue
            first_of: Dict[str, str] = {}
            for p in same:                                   # in sorted order: the first of each content is kept
                sha = file_sha1(p)
                if sha is None:
                    bad.add(p)
                elif sha in first_of:
                    dup.add(p)
                else:
                    first_of[sha] = p
    _save_hash_cache()
    kept = [p for p in ordered if p not in bad and p not in dup]
    return kept, {"unreadable": len(bad), "duplicates": len(dup)}


def stratified_loops(per_cat: int = 30, rng_seed: int = 23, exclude: Optional[Iterable[str]] = None,
                     pool: Optional[List[str]] = None, dedupe: bool = True,
                     exclude_names: Optional[set] = None) -> List[str]:
    """per_cat loop paths from each category (kick / tops / melodic), so a run is not dominated by melodic loops
    (most of the pool) and each class is scored with enough cases to mean something.

    dedupe=True (the default since round 2's revision): the pool is first reduced to one path per CONTENT (size +
    sha1), in sorted path order, so a loop copied into two folders can neither be drawn twice nor dodge an
    exclusion; `exclude` (paths) then drops every loop whose CONTENT matches an excluded file, wherever it lives.
    dedupe=False is the round-1 draw exactly as it ran (the index's order, no dedupe, exclusion by path); it
    exists so a held-out set can exclude precisely the loops round 1 tuned on."""
    pool = list(pool) if pool is not None else find_bpm_loops()
    if exclude_names:
        # by file name too: a copy of a tuned-on loop in another folder, or one the drifting index no longer
        # draws at the same seed, still never enters a held-out set
        pool = [p for p in pool if os.path.basename(p).lower() not in exclude_names]
    if not dedupe:
        pool = [p for p in pool if not exclude or p not in exclude]
    else:
        pool, _ = dedupe_by_content(pool)
        if exclude:
            excl = {k for k in (content_key(p) for p in exclude) if k}
            sizes = {k[0] for k in excl}
            def tuned_on(p):
                sk = _stat_key(p)
                return sk is not None and sk[1] in sizes and content_key(p) in excl
            pool = [p for p in pool if not tuned_on(p)]
            _save_hash_cache()
    rng = np.random.default_rng(rng_seed)
    rng.shuffle(pool)
    quota = {"kick": per_cat, "tops": per_cat, "melodic": per_cat}
    picked = []
    for p in pool:
        c = loop_category(p)
        if quota[c] > 0:
            picked.append(p)
            quota[c] -= 1
        if not any(quota.values()):
            break
    return picked


def held_out_exclusion(seeds: Iterable[int], per_cat: int = 30, pool: Optional[List[str]] = None) -> set:
    """Every loop a tuning draw at these seeds could have used: the round-1 draw exactly as it ran (dedupe=False)
    AND the deduped draw at the same seeds (what a round-2 builder gets for `--seed 7`). Returned as paths;
    stratified_loops excludes them by content."""
    pool = list(pool) if pool is not None else find_bpm_loops()
    out: set = set()
    for s in seeds:
        out |= set(stratified_loops(per_cat, rng_seed=int(s), pool=pool, dedupe=False))
        out |= set(stratified_loops(per_cat, rng_seed=int(s), pool=pool, dedupe=True))
    return out


class ManifestMismatch(ValueError):
    """A file named by a manifest is missing, unreadable, or no longer has the content the manifest recorded."""


def loop_suite(n: int = 40, rng_seed: int = 7, tile_secs: float = 30.0, paths: Optional[List[str]] = None,
               log: Callable[[str], None] = print, expect_sha1: Optional[Dict[str, str]] = None,
               strict: bool = False) -> List[Case]:
    """n loops sampled across packs and tempos, each tiled to tile_secs (loops loop seamlessly by design, and the
    trackers need time to lock). Tempo comes from the file name; phase is ASSUMED to start at t=0 (loops are cut
    to the grid). Third-party audio: evaluated in place, never copied into the repo.

    Each case is named `<file name> #<first 8 hex of its sha1>`, so two different loops that share a file name
    (common across packs) never collide when cases are paired by name. The sha1 is of the very bytes decoded.
    expect_sha1 {path: sha1} (a manifest) makes a changed file an error; strict=True makes ANY file that cannot be
    scored an error instead of a skip (a manifest run scores exactly its list or nothing)."""
    import io
    import soundfile as sf
    pool = paths if paths is not None else find_bpm_loops()
    rng = np.random.default_rng(rng_seed)
    by_pack: Dict[str, List[str]] = {}
    for p in pool:
        parts = p.replace("/", "\\").split("\\")
        pack = "\\".join(parts[:3]) if len(parts) > 3 else parts[0]
        by_pack.setdefault(pack, []).append(p)
    packs = sorted(by_pack)
    rng.shuffle(packs)
    chosen: List[str] = []
    while len(chosen) < n and any(by_pack[k] for k in packs):
        for k in packs:                                  # round-robin across packs, so no single pack dominates
            if by_pack[k] and len(chosen) < n:
                chosen.append(by_pack[k].pop(int(rng.integers(len(by_pack[k])))))
    cases = []
    loaded: Dict[str, str] = {}
    for p in chosen:
        try:
            with open(p, "rb") as f:
                raw = f.read()
            sha = hashlib.sha1(raw).hexdigest()
            if sha in loaded:                            # the same loop at a second path: one loop, scored once
                if strict:
                    raise ManifestMismatch(f"{p}: the same content as {loaded[sha]}")
                log(f"[beatbench] skip {os.path.basename(p)}: same content as {os.path.basename(loaded[sha])}")
                continue
            loaded[sha] = p
            if expect_sha1 is not None and expect_sha1.get(p) != sha:
                raise ManifestMismatch(f"{p}: content changed since the manifest was written "
                                       f"(sha1 {sha[:12]}, manifest {str(expect_sha1.get(p))[:12]})")
            data, rate = sf.read(io.BytesIO(raw), dtype="float32", always_2d=True)
        except ManifestMismatch:
            raise
        except Exception as exc:
            if strict:
                raise ManifestMismatch(f"{p}: cannot be read ({type(exc).__name__}: {exc})") from exc
            log(f"[beatbench] skip {os.path.basename(p)}: {type(exc).__name__}")
            continue
        mono = data.mean(axis=1)
        if len(mono) < rate:                            # under a second: a one-shot mislabelled as a loop
            if strict:
                raise ManifestMismatch(f"{p}: shorter than a second, not a loop")
            continue
        reps = int(math.ceil(tile_secs * rate / len(mono)))
        audio = np.tile(mono, reps)[: int(tile_secs * rate)].astype(np.float32)
        bpm = float(parse_bpm(os.path.basename(p)))
        name = f"{os.path.basename(p)} #{sha[:8]}"
        cat = loop_category(p)
        cases.append(Case(name, audio, int(rate), beat_times(bpm, tile_secs, 0.0), bpm, phase_known=True,
                          source="loop", meta={"path": p, "category": cat, "loop_secs": round(len(mono) / rate, 2),
                                               "sha1": sha, "size": len(raw), "pack": loop_pack(p)}))
    return cases


# --- manifests: a drawn set written down, so it can be scored again exactly ------------------------------------

MANIFEST_KIND = "beatbench-manifest"


def case_files(cases: Sequence[Case]) -> List[Dict]:
    """The files behind file-backed cases (seeded copies share their loop's file and appear once)."""
    out, seen = [], set()
    for c in cases:
        m = c.meta or {}
        if not m.get("path") or m["path"] in seen:
            continue
        seen.add(m["path"])
        out.append({"path": m["path"], "size": m.get("size"), "sha1": m.get("sha1"),
                    "category": m.get("category", c.source)})
    return out


def write_manifest(path: str, cases: Sequence[Case], suite: str, **params) -> str:
    """Write the drawn cases (path, size, sha1, category) and the draw's parameters; returns the manifest's own
    sha1 (the receipt of a gating run names it)."""
    doc = {"kind": MANIFEST_KIND, "version": 1, "suite": suite, "written_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           **params, "cases": case_files(cases)}
    raw = json.dumps(doc, indent=1, ensure_ascii=False).encode("utf-8")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(raw)
    return hashlib.sha1(raw).hexdigest()


def read_manifest(path: str) -> Tuple[Dict, str]:
    """(the manifest, the sha1 of its bytes). Raises ValueError on anything that is not a beatbench manifest."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        doc = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path} is not JSON: {exc}") from exc
    if doc.get("kind") != MANIFEST_KIND or not isinstance(doc.get("cases"), list):
        raise ValueError(f"{path} is not a beatbench manifest")
    return doc, hashlib.sha1(raw).hexdigest()


def manifest_loops(doc: Dict, tile_secs: float = 30.0, log: Callable[[str], None] = print) -> List[Case]:
    """Exactly the manifest's loops, each verified against its sha1; any missing or changed file is an error."""
    if doc.get("suite") != "loops":
        raise ValueError(f"manifest suite is {doc.get('suite')!r}, not 'loops'")
    paths = [c["path"] for c in doc["cases"]]
    cases = loop_suite(n=len(paths), paths=paths, tile_secs=tile_secs, log=log,
                       expect_sha1={c["path"]: c.get("sha1") for c in doc["cases"]}, strict=True)
    if len(cases) != len(paths):
        raise ValueError(f"manifest lists {len(paths)} loops, {len(cases)} were scored")
    return cases


def case_index(cases: Sequence[Case]) -> List[Dict]:
    """What a receipt records about every case: its name, kind, and for files the path and sha1 scored."""
    out = []
    for c in cases:
        m = c.meta or {}
        row = {"case": c.name, "source": c.source}
        for k in ("path", "sha1", "category", "pack", "truth"):
            if m.get(k) is not None:
                row[k] = m[k]
        out.append(row)
    return out


# --- round 2: paired comparison, and real recordings with listened-to ground truth -----------------------------

def paired(rows_c: List[Dict], rows_ref: List[Dict], key: str, n_boot: int = 4000, seed: int = 0,
           cluster=None) -> Dict:
    """Per-case paired difference contestant - reference on one metric, over the cases both scored (matched by
    case name, which must be unique). Returns the mean difference and a 95 % bootstrap interval. Round 2 replaced
    round 1's fixed margin on one draw of 30 loops (smaller than the draw-to-draw noise: beat_a's own kick F moved
    .17 between two draws) with this: the same loops for both trackers, judged loop by loop.

    cluster (a dict or a callable: case name -> cluster id) makes it a CLUSTER bootstrap: whole clusters (a loop's
    pack folder) are resampled, and each replicate's mean is over all the cases of the drawn clusters. Loops of
    one pack are not independent witnesses, and a plain bootstrap would treat them as if they were. Without a
    cluster the result is exactly the plain bootstrap of before."""
    _check_unique((r["case"] for r in rows_c), "contestant case")
    _check_unique((r["case"] for r in rows_ref), "reference case")

    def num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)
    ref = {r["case"]: r for r in rows_ref}
    pairs = [(r["case"], r[key] - ref[r["case"]][key]) for r in rows_c
             if num(r.get(key)) and r["case"] in ref and num(ref[r["case"]].get(key))]
    d = np.array([x for _, x in pairs], dtype=float)
    if not len(d):
        return {"n": 0}
    rng = np.random.default_rng(seed)
    if cluster is None:
        boots = d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(axis=1)
        extra: Dict = {}
    else:
        get = cluster if callable(cluster) else (lambda name: cluster.get(name, name))
        ids = [get(name) for name, _ in pairs]
        uniq = {c: i for i, c in enumerate(dict.fromkeys(ids))}
        ci = np.array([uniq[c] for c in ids])
        k = len(uniq)
        sums, counts = np.zeros(k), np.zeros(k)
        np.add.at(sums, ci, d)
        np.add.at(counts, ci, 1.0)
        draw = rng.integers(0, k, size=(n_boot, k))
        boots = sums[draw].sum(axis=1) / counts[draw].sum(axis=1)
        extra = {"clusters": int(k)}
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": int(len(d)), "mean": round(float(d.mean()), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            **extra}


PAIRED_KEYS = ("F", "CMLt", "bpm_spread", "ibi_spread")


def case_group(c: Case) -> str:
    """The paired comparison's group: a loop's category (kick / tops / melodic), 'seeded' when it ran with its
    true BPM as the seed; anything else by its source."""
    cat = (c.meta or {}).get("category", c.source)
    return f"{cat}{' seeded' if c.seed_bpm and c.source == 'loop' else ''}"


def paired_report(cases: Sequence[Case], report: Dict, vs: str, keys: Sequence[str] = PAIRED_KEYS,
                  log: Callable[[str], None] = print) -> Dict:
    """Every scored tracker against `vs`, case by case: per group and POOLED over all groups, each with a cluster
    bootstrap by loop pack folder when the cases are loops (a non-loop case is its own cluster)."""
    trackers = report["trackers"]
    if vs not in trackers or "cases" not in trackers[vs]:
        raise ValueError(f"--vs {vs}: the reference was not scored in this run")
    group = {c.name: case_group(c) for c in cases}
    packs = {c.name: (c.meta or {}).get("pack") for c in cases}
    cluster = {n: (p or n) for n, p in packs.items()} if any(packs.values()) else None
    ref_rows = trackers[vs]["cases"]
    out: Dict = {}
    for name, t in trackers.items():
        if name == vs or "cases" not in t:
            continue
        res: Dict = {}
        for g in sorted(set(group.values())) + ["pooled"]:
            rc = [r for r in t["cases"] if g == "pooled" or group.get(r["case"]) == g]
            rr = [r for r in ref_rows if g == "pooled" or group.get(r["case"]) == g]
            res[g] = {k: paired(rc, rr, k, cluster=cluster) for k in keys}
            f, c, sp = res[g]["F"], res[g]["CMLt"], res[g]["bpm_spread"]
            if f.get("n"):
                log(f"[paired] {name} - {vs} | {g:18} n {f['n']:3}"
                    f"{' clusters ' + str(f['clusters']) if 'clusters' in f else ''}  F {f['mean']:+.3f} {f['ci95']}  "
                    f"CMLt {c['mean']:+.3f} {c['ci95']}  spread {sp.get('mean', 0):+.3f} {sp.get('ci95')}")
        out[name] = res
    return out


RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "state", "arsenal", "keylab", "recordings")


FIT_N_FFT = 2048
FIT_RELATIVES = (("x1/2", 0.5), ("x2", 2.0), ("x2/3", 2.0 / 3.0), ("x3/2", 1.5), ("x4/5", 0.8))


def _flux_env(audio: np.ndarray, rate: int, hop: int = 256, n_fft: int = FIT_N_FFT,
              low_hz: Optional[float] = None) -> np.ndarray:
    """Log-magnitude spectral flux per frame (frame i = samples [i*hop, i*hop + n_fft)); low_hz keeps only the bins
    below it (the kick band)."""
    win = np.hanning(n_fft)
    frames = max(0, 1 + (len(audio) - n_fft) // hop)
    sel = np.fft.rfftfreq(n_fft, 1.0 / rate) < low_hz if low_hz else slice(None)
    env = np.zeros(frames)
    prev = None
    for i in range(frames):
        mag = np.log1p(100.0 * np.abs(np.fft.rfft(audio[i * hop:i * hop + n_fft] * win)))[sel]
        if prev is not None:
            env[i] = np.maximum(mag - prev, 0.0).mean()
        prev = mag
    return env


@functools.lru_cache(maxsize=16)
def frame_time_offset(rate: int, hop: int = 256, n_fft: int = FIT_N_FFT) -> float:
    """CALIBRATED frame-time convention: seconds from a flux frame's first sample (i * hop / rate) to the onset
    whose flux peaks in that frame, measured on synthetic clicks at known times over a faint noise floor.

    The old convention put the frame at its window CENTRE (i * hop + n_fft / 2); the log-magnitude flux actually
    peaks while an onset is still entering the right-hand edge of the window, so every grid fitted under the old
    convention sat early. Clicks are spread across a hop so the quantisation averages out; the median is used."""
    rng = np.random.default_rng(5)
    secs = 12.0
    buf = (1e-4 * rng.standard_normal(int(secs * rate))).astype(np.float32)
    click = _click(rate)
    times = 0.5 + np.arange(20) * 0.5 + (np.arange(20) % 8) * hop / (8.0 * rate)
    times = np.round(times * rate) / rate                       # exactly where _place puts them
    for t in times:
        _place(buf, click, float(t), rate)
    env = _flux_env(buf, rate, hop, n_fft)
    frame_t = np.arange(len(env)) * hop / rate
    lags = []
    for t in times:
        sel = np.where((frame_t > t - n_fft / rate - 0.02) & (frame_t < t + 0.1))[0]
        if len(sel):
            lags.append(t - frame_t[sel[int(np.argmax(env[sel]))]])
    return float(np.median(lags))


def onset_envelope(audio: np.ndarray, rate: int, hop: int = 256, low_hz: Optional[float] = None
                   ) -> Tuple[np.ndarray, np.ndarray]:
    """(times, envelope): the flux with each frame placed at the onset time it stands for (calibrated)."""
    env = _flux_env(audio, rate, hop, FIT_N_FFT, low_hz)
    t = np.arange(len(env)) * hop / rate + frame_time_offset(rate, hop, FIT_N_FFT)
    return t, env


def _resultant(env: np.ndarray, t: np.ndarray, bpm: float) -> float:
    """How strongly the onsets repeat at this tempo: the resultant length of the onset-weighted phases, 0..1."""
    z = (env * np.exp(2j * np.pi * t * bpm / 60.0)).sum() / (env.sum() + 1e-12)
    return float(abs(z))


def _refine_bpm(env: np.ndarray, t: np.ndarray, bpm: float, rel: float = 0.01) -> Tuple[float, float]:
    """(tempo, score): the best tempo within +-rel of bpm, by a 0.02 BPM scan and then a 0.002 BPM scan within
    +-0.04 BPM of its winner."""
    best = (_resultant(env, t, bpm), float(bpm))
    for k, step in enumerate((0.02, 0.002)):
        lo, hi = (bpm * (1 - rel), bpm * (1 + rel)) if k == 0 else (best[1] - 0.04, best[1] + 0.04)
        for b in np.arange(lo, hi + step / 2, step):
            s = _resultant(env, t, float(b))
            if s > best[0]:
                best = (s, float(b))
    return best[1], best[0]


def _comb(env: np.ndarray, t: np.ndarray, period: float, res_s: float = 0.001, smooth_s: float = 0.006
          ) -> Tuple[np.ndarray, int]:
    nb = max(16, int(round(period / res_s)))
    x = (t % period) / period * nb
    i0 = np.floor(x).astype(int)
    fr = x - i0
    hist = (np.bincount(i0 % nb, weights=env * (1 - fr), minlength=nb)
            + np.bincount((i0 + 1) % nb, weights=env * fr, minlength=nb))
    sig = max(0.5, smooth_s / period * nb)
    ks = np.arange(-int(4 * sig) - 1, int(4 * sig) + 2)
    sm = np.zeros(nb)
    for k, w in zip(ks, np.exp(-0.5 * (ks / sig) ** 2)):
        sm += w * np.roll(hist, k)
    return sm, nb


def comb_sharpness(env: np.ndarray, t: np.ndarray, bpm: float) -> float:
    """How tall the folded onset pile is at this tempo (peak / total). Exactly the right tempo stacks every beat's
    onsets on the same phase; a tempo off by a hair smears them, at every harmonic at once."""
    sm, _ = _comb(env, t, 60.0 / bpm)
    return float(sm.max() / (sm.sum() + 1e-12))


def _sharpen_bpm(env: np.ndarray, t: np.ndarray, bpm: float, span: float = 0.15, step: float = 0.005) -> float:
    grid = np.arange(bpm - span, bpm + span + step / 2, step)
    return float(grid[int(np.argmax([comb_sharpness(env, t, float(b)) for b in grid]))])


def comb_phase(env: np.ndarray, t: np.ndarray, period: float, res_s: float = 0.001, smooth_s: float = 0.006
               ) -> float:
    """The phase (seconds into a beat, 0..period) at which the onsets pile up most: every frame's flux is folded
    onto one beat by its time modulo the period (linear interpolation between 1 ms bins), smoothed by a +-6 ms
    Gaussian, and the peak is taken (parabolic refinement). This is the onset-sum (comb) argmax over phase; unlike
    the fundamental's angle it is not pulled toward the off-beat by hats and snares."""
    sm, nb = _comb(env, t, period, res_s, smooth_s)
    j = int(np.argmax(sm))
    y0, y1, y2 = sm[(j - 1) % nb], sm[j], sm[(j + 1) % nb]
    den = y0 - 2 * y1 + y2
    delta = 0.5 * (y0 - y2) / den if den < 0 else 0.0
    return float(((j + delta) / nb * period) % period)


def fit_grid(audio: np.ndarray, rate: int, bpm_lo: float = 60.0, bpm_hi: float = 200.0, hop: int = 256,
             bpm: Optional[float] = None, n_peaks: int = 3) -> Dict:
    """OFFLINE reference grid for a real recording: the constant tempo and first beat that best fit the WHOLE
    track's onsets (it sees the future, so it is a reference, never a tracker). Electronic music made in a DAW
    holds one tempo, which is what makes a whole-track fit trustworthy. The result is only ground truth after a
    person has listened to the click render and said it sits on the beat (annotate -> confirm).

    It admits doubt: `candidates` lists the best tempo, the next strongest peaks, and the best tempo's x1/2, x2,
    x2/3, x3/2 and x4/5 relatives, each with its score and its own first beat, because this score alone cannot
    tell a tempo from its relatives; a person decides by ear. bpm=X forces the tempo to exactly X and fits only
    the phase (the candidates are still listed, for the record)."""
    t, env = onset_envelope(audio, rate, hop)
    env = np.maximum(env - np.median(env), 0.0)
    fps = rate / hop
    grid = np.arange(bpm_lo, bpm_hi, 0.05)
    curve = np.array([_resultant(env, t, float(b)) for b in grid])
    found: List[Dict] = []

    def add(b: float, s: float, rel: str) -> None:
        for c in found:
            if abs(c["bpm"] / b - 1) < 0.004:
                if rel not in c["rel"]:
                    c["rel"].append(rel)
                return
        found.append({"bpm": b, "score": s, "rel": [rel]})

    peaks = [i for i in range(len(curve)) if (i == 0 or curve[i] >= curve[i - 1])
             and (i == len(curve) - 1 or curve[i] >= curve[i + 1])]
    peaks.sort(key=lambda i: -curve[i])
    best_b, best_s = _refine_bpm(env, t, float(grid[peaks[0]])) if peaks else (120.0, 0.0)
    add(best_b, best_s, "best")
    for name, r in FIT_RELATIVES:
        b, s = _refine_bpm(env, t, best_b * r)
        add(b, s, name)
    for i in peaks[1:]:
        if sum(1 for c in found if "peak" in c["rel"]) >= n_peaks - 1:
            break
        if all(abs(float(grid[i]) / c["bpm"] - 1) > 0.02 for c in found):
            b, s = _refine_bpm(env, t, float(grid[i]))
            if all(abs(b / c["bpm"] - 1) > 0.02 for c in found):   # a side lobe of a tempo already listed: skip
                add(b, s, "peak")
    for c in found:
        c["bpm"] = _sharpen_bpm(env, t, c["bpm"])            # the resultant finds the tempo, the comb pins it
        c["first_beat"] = round(comb_phase(env, t, 60.0 / c["bpm"]), 4)
        c["bpm"], c["score"] = round(c["bpm"], 3), round(c["score"], 4)
    found.sort(key=lambda c: (0 if "best" in c["rel"] else 1, -c["score"]))
    if bpm is not None:
        use_bpm, fit = float(bpm), _resultant(env, t, float(bpm))
        first = comb_phase(env, t, 60.0 / use_bpm)
    else:
        use_bpm, fit, first = found[0]["bpm"], best_s, found[0]["first_beat"]
    return {"bpm": round(float(use_bpm), 3) if bpm is None else float(bpm), "first_beat": round(float(first), 4),
            "fit": round(float(fit), 4), "fps": round(fps, 2), "bpm_forced": float(bpm) if bpm is not None else None,
            "frame_offset_ms": round(frame_time_offset(rate, hop, FIT_N_FFT) * 1000, 2),
            "method": "whole-track resultant for tempo, onset-comb argmax for phase, calibrated frame time",
            "candidates": found}


def _flux_envelopes(audio: np.ndarray, rate: int, hop: int = 256):
    n_fft = FIT_N_FFT
    win = np.hanning(n_fft)
    frames = 1 + (len(audio) - n_fft) // hop
    freqs = np.fft.rfftfreq(n_fft, 1.0 / rate)
    low = freqs < 150.0
    env_lo, env_all, rms = np.zeros(frames), np.zeros(frames), np.zeros(frames)
    prev = None
    for i in range(frames):
        seg = audio[i * hop:i * hop + n_fft]
        mag = np.log1p(100.0 * np.abs(np.fft.rfft(seg * win)))
        if prev is not None:
            d = np.maximum(mag - prev, 0.0)
            env_lo[i], env_all[i] = d[low].mean(), d.mean()
        prev = mag
        rms[i] = np.sqrt(np.mean(seg ** 2))
    # the calibrated frame-time convention (see frame_time_offset), not the window centre
    t = np.arange(frames) * hop / rate + frame_time_offset(rate, hop, n_fft)
    return t, env_lo, env_all, rms


def fit_sections(audio: np.ndarray, rate: int, bpm: Optional[float] = None, quiet_db: float = 4.0,
                 min_len_s: float = 6.0) -> Dict:
    """OFFLINE reference grids for a real song, ONE PER SECTION. Real tracks re-enter after a breakdown at a phase
    of their own (Daniel's ear check on Hard Driver, 2026-10-23: the click "lagged" in the intro and was early by
    about 100 ms after the quiet part, a jump of about 150 ms; one whole-track grid cannot sit on both). Sections
    are the loud stretches between quiet ones; each gets its own phase (and a tempo within +-0.5 % of the song's),
    fitted to the kick band where the kick is clear, else to all bands. Quiet stretches get no reference beats and
    are not scored. Still a REFERENCE: ground truth only after the ear check."""
    t, env_lo, env_all, rms = _flux_envelopes(audio, rate)
    song = fit_grid(audio, rate, *((bpm - 0.3, bpm + 0.3) if bpm else ()))
    loud = 20 * np.log10(np.convolve(rms, np.ones(64) / 64, mode="same") + 1e-9)
    is_loud = loud > np.median(loud) - quiet_db
    sections = []
    start = None
    for i, on in enumerate(list(is_loud) + [False]):
        if on and start is None:
            start = i
        elif not on and start is not None:
            a, b = t[start], t[min(i, len(t) - 1)]
            if b - a >= min_len_s:
                sections.append([float(a), float(b)])
            start = None
    out = []
    for a, b in sections:
        sel = (t >= a) & (t < b)
        best = None
        for env, band in ((env_lo, "kick"), (env_all, "all")):
            e = np.maximum(env[sel] - np.median(env[sel]), 0.0)
            for bp in np.arange(song["bpm"] * 0.995, song["bpm"] * 1.005, 0.01):
                period = 60.0 / bp
                z = (e * np.exp(2j * np.pi * t[sel] / period)).sum() / (e.sum() + 1e-12)
                if best is None or abs(z) > best[0] * (1.15 if band == "all" else 1.0):
                    best = (abs(z), bp, (np.angle(z) / (2 * np.pi)) % 1.0 * period, band)
            if best[3] == "kick" and best[0] > 0.12:
                break                     # a clear kick decides; only fall back to all bands when it is weak
        out.append({"start": round(a, 3), "end": round(b, 3), "bpm": round(float(best[1]), 3),
                    "first_beat": round(float(best[2]), 4), "fit": round(float(best[0]), 3), "band": best[3]})
    return {"bpm": song["bpm"], "sections": out}


def section_beats(sections: List[Dict]) -> np.ndarray:
    beats = []
    for sec in sections:
        period = 60.0 / sec["bpm"]
        k0 = math.ceil((sec["start"] - sec["first_beat"]) / period)
        tb = sec["first_beat"] + k0 * period
        while tb < sec["end"]:
            beats.append(tb)
            tb += period
    return np.array(sorted(beats))


def render_clicks(audio: np.ndarray, rate: int, bpm: float, first_beat: float, path: str,
                  beats: Optional[np.ndarray] = None) -> str:
    """The recording with a click on every reference beat (accent on every 4th), for the listen check."""
    import soundfile as sf
    out = audio.astype(np.float32).copy() * 0.6
    click = _click(rate)
    if beats is None:
        beats = np.arange(first_beat, len(out) / rate, 60.0 / bpm)
    for k, t in enumerate(beats):
        _place(out, click, float(t), rate, 0.9 if k % 4 == 0 else 0.5)
    sf.write(path, np.clip(out, -1, 1), rate)
    return path


_STAMP_RE = _re.compile(r"^(\d{8}-\d{6})(?!\d)")


def recording_stamp(path: str) -> Optional[str]:
    """The YYYYMMDD-HHMMSS stamp beatsync.record puts at the start of every recording's file name, or None."""
    m = _STAMP_RE.match(os.path.basename(path))
    return m.group(1) if m else None


def check_stamp(since: str) -> str:
    if not _STAMP_RE.match(since or "") or len(since) != 15:
        raise ValueError(f"since must be a YYYYMMDD-HHMMSS stamp like 20261023-120000, not {since!r}")
    time.strptime(since, "%Y%m%d-%H%M%S")                       # a real date and time, or ValueError
    return since


def _load_json(path: str) -> Optional[Dict]:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def recording_truth(path: str, confirmed_only: bool = True) -> Optional[Tuple[str, Dict]]:
    """The ground truth a recording carries: a TAPPED answer key (`<file>.tapkey.json`, sections from the hand's
    taps) when one is present and confirmed, else the fitted grid (`<file>.beats.json`). (kind, meta) or None."""
    tk = _load_json(path + ".tapkey.json")
    if tk and tk.get("sections") and (tk.get("confirmed") or not confirmed_only):
        return "tapkey", tk
    meta = _load_json(path + ".beats.json")
    if meta and (meta.get("confirmed") or not confirmed_only):
        return "grid", meta
    return None


def recording_suite(root: Optional[str] = None, confirmed_only: bool = True, max_secs: float = 90.0,
                    since: Optional[str] = None, manifest: Optional[Dict] = None,
                    log: Callable[[str], None] = print) -> List[Case]:
    """Daniel's own recordings (beatsync.record or `beat --save`; state/, never committed) that carry ground truth:
    a confirmed tapped key `<file>.tapkey.json` (preferred) or a confirmed grid `<file>.beats.json`. Only
    confirmed ground truth is scored unless asked.

    since='YYYYMMDD-HHMMSS' keeps only recordings whose file-name stamp is at or after it (the held-out real-song
    set is the recordings made after the pre-registration). manifest (read_manifest's doc, suite 'real') scores
    exactly its listed files, each verified by sha1, and makes a missing truth an error. A recording whose capture
    had a timing gap (`<file>.rec.json`) is never scored. Every recording scored is named in the log."""
    import glob
    import io
    import soundfile as sf
    if manifest is not None:
        if manifest.get("suite") != "real":
            raise ValueError(f"manifest suite is {manifest.get('suite')!r}, not 'real'")
        paths = [c["path"] for c in manifest["cases"]]
        expect = {c["path"]: c.get("sha1") for c in manifest["cases"]}
    else:
        paths = sorted(glob.glob(os.path.join(root or RECORDINGS_DIR, "*.flac")))
        expect = None
    if since:
        check_stamp(since)
        late = [p for p in paths if (recording_stamp(p) or "") >= since]
        for p in sorted(set(paths) - set(late)):
            log(f"[beatbench] real: not scored (recorded before {since} or no stamp): {os.path.basename(p)}")
        paths = late
    cases = []
    for p in paths:
        truth = recording_truth(p, confirmed_only)
        timing = _load_json(p + ".rec.json")
        problem = None
        if truth is None:
            problem = "no confirmed ground truth" if confirmed_only else "no ground truth"
        elif timing and timing.get("gap"):
            problem = f"capture gap of {timing.get('gap_ms')} ms"
        if problem:
            if manifest is not None:
                raise ManifestMismatch(f"{p}: {problem}")
            log(f"[beatbench] real: not scored ({problem}): {os.path.basename(p)}")
            continue
        kind, meta = truth
        with open(p, "rb") as f:
            raw = f.read()
        sha = hashlib.sha1(raw).hexdigest()
        if expect is not None and expect.get(p) != sha:
            raise ManifestMismatch(f"{p}: content changed since the manifest was written")
        data, rate = sf.read(io.BytesIO(raw), dtype="float32", always_2d=True)
        audio = data.mean(axis=1)[: int(max_secs * rate)]
        secs = len(audio) / rate
        if meta.get("sections"):
            secs_ = [s for s in meta["sections"] if s["start"] < secs]
            beats = section_beats(secs_)
            beats = beats[beats < secs]
            meta = {**meta, "spans": [[s["start"], min(s["end"], secs)] for s in secs_]}
        else:
            first = float(meta["first_beat"]) % (60.0 / float(meta["bpm"]))
            beats = beat_times(float(meta["bpm"]), secs, first)
        log(f"[beatbench] real: scoring {os.path.basename(p)} ({kind} ground truth, "
            f"{'confirmed' if meta.get('confirmed') else 'NOT confirmed'}, {float(meta['bpm']):.2f} BPM, "
            f"sha1 {sha[:10]})")
        cases.append(Case(os.path.basename(p), audio, int(rate), beats, float(meta["bpm"]),
                          seed_bpm=meta.get("seed_bpm"), phase_known=True, source="recording",
                          meta={**meta, "path": p, "sha1": sha, "size": len(raw), "truth": kind}))
    return cases


# --- tapped answer keys: the hand's taps, straightened -------------------------------------------------------------

TAP_GAP_BEATS = 2.2      # a pause longer than this many beats ends a stretch of tapping
TAP_MIN_TAPS = 8         # a stretch needs this many taps to count


def tap_stretches(taps: Sequence[float], gap_beats: float = TAP_GAP_BEATS, min_taps: int = TAP_MIN_TAPS
                  ) -> Tuple[List[List[float]], int]:
    """Split taps into steady stretches: a pause longer than gap_beats beats (the stretch's own median interval so
    far) starts a new one. Stretches with fewer than min_taps taps are dropped. Returns (stretches, dropped taps)."""
    taps = sorted(float(x) for x in taps)
    out: List[List[float]] = []
    cur: List[float] = []
    for t in taps:
        if not cur:
            cur = [t]
            continue
        iv = np.diff(cur[-9:])
        iv = iv[(iv > 0.2) & (iv < 2.0)]
        gap = t - cur[-1]
        limit = gap_beats * float(np.median(iv)) if len(iv) else 2.0
        if gap > limit:
            out.append(cur)
            cur = [t]
        else:
            cur.append(t)
    if cur:
        out.append(cur)
    keep = [s for s in out if len(s) >= min_taps]
    return keep, sum(len(s) for s in out) - sum(len(s) for s in keep)


def fit_tap_line(taps: Sequence[float]) -> Dict:
    """A straight line through one steady stretch: beat number k (taps rounded onto the median interval, so a
    skipped tap is a skipped beat, not a slow one) against tap time, least squares. Returns the period, the time
    of beat 0, and the taps' scatter about the line (jitter, ms, RMS)."""
    t = np.asarray(sorted(taps), dtype=float)
    p0 = float(np.median(np.diff(t)))
    k = np.round((t - t[0]) / p0)
    a = np.vstack([k, np.ones_like(k)]).T
    (period, t0), *_ = np.linalg.lstsq(a, t, rcond=None)
    resid = t - (t0 + k * period)
    return {"period": float(period), "t0": float(t0), "k_last": int(k[-1]),
            "jitter_ms": float(np.sqrt(np.mean(resid ** 2)) * 1000)}


def kick_onsets(audio: np.ndarray, rate: int, hop: int = 256, low_hz: float = 150.0) -> np.ndarray:
    """Kick-band onset times (offline): peaks of the < 150 Hz flux above median + 1.5 std, at least 80 ms apart,
    placed with the calibrated frame time."""
    t, env = onset_envelope(audio, rate, hop, low_hz=low_hz)
    if len(env) < 3:
        return np.array([])
    thr = float(np.median(env) + 1.5 * np.std(env))
    pk = [i for i in range(1, len(env) - 1) if env[i] > thr and env[i] >= env[i - 1] and env[i] > env[i + 1]]
    out: List[float] = []
    for i in pk:
        if out and t[i] - out[-1] < 0.08:
            continue
        out.append(float(t[i]))
    return np.array(out)


def tap_key(path: str, write: bool = True, gap_beats: float = TAP_GAP_BEATS, min_taps: int = TAP_MIN_TAPS,
            render: bool = True) -> Dict:
    """An answer key made by ear, from a `beat --save` session: the taps in `<file>.hand.json` (seconds into the
    audio) are split into steady stretches (a pause > gap_beats beats starts a new one; >= min_taps taps each),
    and each stretch gets a straight line: its BPM, its tap jitter (ms), and the offset between the taps and the
    kick-band onsets (median, ms; + = the taps land AFTER the kicks). Each stretch becomes a section with a span,
    exactly the shape recording_suite scores. Written to `<file>.tapkey.json`, unconfirmed; with render=True a
    `<file> TAPKEY CLICKS.wav` is rendered to listen to before `confirm --tapkey`.

    The taps are NOT shifted onto the kicks: the offset is reported for a person to judge, because a kick is not
    always the beat. A recording whose capture had a timing gap is refused (the taps would not line up)."""
    import soundfile as sf
    hand = _load_json(path + ".hand.json")
    if not hand or not hand.get("taps"):
        raise ValueError(f"no taps for {os.path.basename(path)}: tap along with `beat --save --hand` first "
                         f"(it writes {os.path.basename(path)}.hand.json)")
    timing = hand.get("timing") or _load_json(path + ".rec.json")
    if timing and timing.get("gap"):
        raise ValueError(f"{os.path.basename(path)}: the capture had a timing gap ({timing.get('gap_ms')} ms "
                         f"between sample time and wall time), so the taps cannot be placed on the audio")
    stretches, dropped = tap_stretches(hand["taps"], gap_beats, min_taps)
    if not stretches:
        raise ValueError(f"no steady stretch of >= {min_taps} taps in {os.path.basename(path)}.hand.json")
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    audio = data.mean(axis=1)
    dur = len(audio) / rate
    kicks = kick_onsets(audio, rate)
    out = []
    for s in stretches:
        line = fit_tap_line(s)
        per = line["period"]
        offs = []
        for x in s:
            if len(kicks):
                j = int(np.argmin(np.abs(kicks - x)))
                if abs(kicks[j] - x) <= 0.25 * per:
                    offs.append(x - kicks[j])
        out.append({"start": round(max(0.0, s[0] - per / 2), 3), "end": round(min(dur, s[-1] + per / 2), 3),
                    "bpm": round(60.0 / per, 3), "first_beat": round(line["t0"], 4), "taps": len(s),
                    "jitter_ms": round(line["jitter_ms"], 1),
                    "kick_offset_ms": round(float(np.median(offs)) * 1000, 1) if offs else None,
                    "kick_matched": round(len(offs) / len(s), 2)})
    weights = np.array([s["taps"] for s in out], dtype=float)
    doc = {"method": "tapped answer key: a least-squares line through each steady stretch of taps",
           "source": os.path.basename(path) + ".hand.json", "taps": len(hand["taps"]), "dropped_taps": dropped,
           "bpm": round(float(np.average([s["bpm"] for s in out], weights=weights)), 3),
           "sections": out, "spans": [[s["start"], s["end"]] for s in out], "confirmed": False}
    if render:
        clicks = os.path.splitext(path)[0] + " TAPKEY CLICKS.wav"
        render_clicks(audio, rate, doc["bpm"], 0.0, clicks, beats=section_beats(out))
        doc["clicks"] = clicks_record(clicks, doc)
    if write:
        with open(path + ".tapkey.json", "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1)
    return doc


# --- the listen check: what was rendered must be what is confirmed ------------------------------------------------

def grid_params(meta: Dict) -> Dict:
    """The part of a sidecar that decides where the clicks go."""
    if meta.get("sections"):
        return {"sections": [{k: s[k] for k in ("start", "end", "bpm", "first_beat")} for s in meta["sections"]]}
    return {"bpm": meta.get("bpm"), "first_beat": meta.get("first_beat")}


def clicks_record(clicks_path: str, meta: Dict) -> Dict:
    return {"path": clicks_path, "sha1": file_sha1_uncached(clicks_path), "grid": grid_params(meta)}


def file_sha1_uncached(path: str) -> Optional[str]:
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def clicks_mismatch(meta: Dict) -> Optional[str]:
    """Why this sidecar cannot be confirmed as listened to, or None: the CLICKS file it records must still exist
    with the same bytes, and the grid in the sidecar must be the grid those clicks were rendered from."""
    rec = meta.get("clicks")
    if not rec:
        return "it does not record which CLICKS render was listened to (made before render records existed)"
    if rec.get("grid") != grid_params(meta):
        return "its grid was changed after the CLICKS file was rendered"
    sha = file_sha1_uncached(rec.get("path") or "")
    if sha is None:
        return f"the CLICKS file is missing: {rec.get('path')}"
    if sha != rec.get("sha1"):
        return "the CLICKS file on disk is not the one rendered for this grid"
    return None


def save_report(report: Dict, path: Optional[str] = None) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "state", "arsenal", "keylab", "receipts")
    path = path or os.path.join(root, f"beatbench-{stamp}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, default=str)
    return path
