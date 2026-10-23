"""arsenal.keylab.beatbench -- one instrument that judges every beat tracker on the same ground truth.

Built BEFORE any new tracker (A16 T4, Daniel 2026-10-22: "lets see what we can figure out for our own internal
beat detector"), so aubio, librosa and our own trackers are all scored by the same ruler.

The streaming contract every tracker meets (agreed with Heimdall for the blind pair beat_a.py / beat_b.py,
bus 1792703252595-0):

    tracker = Factory(rate, hop, seed_bpm=None)
    events  = tracker.feed(block)       # block: float32 mono numpy array of `hop` samples
    # OBSERVED beats: [{"t_beat": s, "bpm": float, "phase": 0..1, "confidence": 0..1, "is_downbeat": bool|None}]
    ahead   = tracker.predict(now)      # EXPECTED beats after `now` (seconds of audio fed so far):
    # [{"t_beat": s, "bpm", "phase", "confidence"}] -- what the hub paints from, a few hundred ms early
    # predict() is optional for baselines; is_downbeat None means "this tracker does not claim meter" and is
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
  pred_err_ms     median |predicted next beat - the true next beat|, asked >= 50 ms ahead, after lock (ours)
  pred_hit        share of those predictions within +-35 ms, the visual tolerance for lights (ours)
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

F_WINDOW = 0.07          # seconds
CONT_TOL = 0.175         # phase and period tolerance for the continuity metrics
TEMPO_TOL = 0.04         # Acc1 / Acc2 tolerance
SKIP_FIRST = 5.0         # seconds of each case not scored for beat metrics (the convention; lock_s covers it)
PREDICT_EVERY_S = 0.1    # how often the bench asks predict()
PRED_HIT_MS = 35.0       # a predicted beat within this lands visibly ON the beat


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
    tracker = factory(case.rate, hop, seed_bpm=case.seed_bpm)
    can_predict = callable(getattr(tracker, "predict", None))
    every = max(1, int(round(PREDICT_EVERY_S * case.rate / hop)))
    events: List[dict] = []
    preds: List[dict] = []
    t0 = time.perf_counter()
    n_blocks = len(case.audio) // hop
    for b in range(n_blocks):
        block = case.audio[b * hop:(b + 1) * hop]
        at = (b + 1) * hop / case.rate
        for ev in tracker.feed(block) or []:
            events.append({**ev, "_at": at})
        if can_predict and b % every == 0:
            ahead = [p for p in (tracker.predict(at) or []) if p["t_beat"] > at]
            if ahead:
                preds.append({"asked_at": at, "t_next": min(p["t_beat"] for p in ahead)})
    cpu = time.perf_counter() - t0
    beats = dedupe(events)
    return {"beats": beats, "predictions": preds, "cpu_s": cpu, "audio_s": len(case.audio) / case.rate,
            "realtime_x": (len(case.audio) / case.rate) / cpu if cpu > 0 else float("inf")}


def prediction_error(preds: List[dict], ref: np.ndarray, after: float, min_lead: float = 0.05) -> Dict:
    """For each prediction asked at time a (after lock), compare the predicted next beat with the TRUE next beat
    (the first reference beat after a). Predictions asked less than min_lead before that beat are skipped: too
    late to steer a light by, so they would only flatter the tracker."""
    errs = []
    for p in preds:
        if p["asked_at"] < after:
            continue
        future = ref[ref > p["asked_at"]]
        if not len(future) or future[0] - p["asked_at"] < min_lead:
            continue
        errs.append(abs(p["t_next"] - future[0]) * 1000)
    if not errs:
        return {}
    return {"pred_err_ms": round(float(np.median(errs)), 1),
            "pred_hit": round(sum(e <= PRED_HIT_MS for e in errs) / len(errs), 3)}


def score(case: Case, result: Dict) -> Dict:
    est = np.array([b["t_beat"] for b in result["beats"]])
    bpms = [b.get("bpm") for b in result["beats"] if b.get("bpm")]
    late = [b for b in result["beats"] if b["t_beat"] >= SKIP_FIRST]
    est_bpm = float(np.median([b["bpm"] for b in late if b.get("bpm")])) if any(b.get("bpm") for b in late) else (
        float(60.0 / np.median(np.diff(est))) if len(est) > 2 else 0.0)
    out = {"case": case.name, "ref_bpm": round(case.bpm, 2), "est_bpm": round(est_bpm, 2), **tempo_acc(est_bpm, case.bpm),
           "realtime_x": round(result["realtime_x"], 1)}
    if bpms:
        locked = [x for b, x in zip(result["beats"], bpms) if b["t_beat"] >= SKIP_FIRST]
        if locked:
            octave = [abs(x - 2 * case.bpm) <= TEMPO_TOL * 2 * case.bpm or abs(x - case.bpm / 2) <= TEMPO_TOL * case.bpm / 2
                      for x in locked]
            out["octave_err"] = round(sum(octave) / len(octave), 3)
    out.update(drift(result["beats"], start=SKIP_FIRST))
    leads = [(b["t_beat"] - b["_at"]) * 1000 for b in result["beats"]]
    if leads:
        out["lead_ms"] = round(float(np.median(leads)), 1)
    if case.phase_known and len(case.beats):
        ref_t, est_t = _trim(case.beats, SKIP_FIRST), _trim(est, SKIP_FIRST)
        spans = (case.meta or {}).get("spans")
        if spans:
            # a real song is scored only inside the sections a person has confirmed by ear; quiet bits and
            # breakdowns between them have no reference beat, so neither side is counted there
            def inside(x):
                keep = np.zeros(len(x), dtype=bool)
                for a, b in spans:
                    keep |= (x >= a) & (x < b)
                return x[keep]
            ref_t, est_t = inside(ref_t), inside(est_t)
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
            out.update(prediction_error(result["predictions"], case.beats, after=lt if lt is not None else SKIP_FIRST))
    return out


FLIP_RATIO = 0.08   # a reported tempo jumping more than 8 % between consecutive beats counts as a flip


def drift(beats: List[dict], start: float = SKIP_FIRST) -> Dict:
    """How steady the reported tempo is once settled. Music made in a DAW has a constant grid, so on constant-
    tempo material any spread or flip is the tracker chasing notes rather than holding the grid.
      bpm_spread   (p90 - p10) / median of the reported bpm after `start`; 0 = rock steady
      tempo_flips  consecutive reported bpm values differing by more than FLIP_RATIO"""
    vals = [float(b["bpm"]) for b in beats if b.get("bpm") and b["t_beat"] >= start]
    if len(vals) < 3:
        return {}
    v = np.array(vals)
    med = float(np.median(v))
    spread = float((np.percentile(v, 90) - np.percentile(v, 10)) / med) if med else 0.0
    flips = int(np.sum(np.abs(v[1:] / v[:-1] - 1.0) > FLIP_RATIO))
    return {"bpm_spread": round(spread, 4), "tempo_flips": flips}


def summarize(rows: List[Dict]) -> Dict:
    def mean(key):
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float)) and not isinstance(r.get(key), bool)]
        return round(float(np.mean(vals)), 3) if vals else None
    def share(key):
        vals = [bool(r[key]) for r in rows if key in r]
        return round(sum(vals) / len(vals), 3) if vals else None
    locks = [r["lock_s"] for r in rows if r.get("lock_s") is not None]
    return {"cases": len(rows), "F": mean("F"), "CMLt": mean("CMLt"), "AMLt": mean("AMLt"), "Acc1": share("Acc1"),
            "Acc2": share("Acc2"), "octave_err": mean("octave_err"), "lead_ms": mean("lead_ms"),
            "lock_s_median": round(float(np.median(locks)), 2) if locks else None,
            "never_locked": sum(1 for r in rows if "lock_s" in r and r["lock_s"] is None),
            "pred_err_ms": mean("pred_err_ms"), "pred_hit": mean("pred_hit"),
            "bpm_spread": mean("bpm_spread"), "tempo_flips": mean("tempo_flips"),
            "relock_s": mean("relock_s"),
            "never_relocked": sum(1 for r in rows if "relock_s" in r and r["relock_s"] is None),
            "realtime_x_min": min((r["realtime_x"] for r in rows), default=None)}


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
    t0 = time.perf_counter()
    evs = [{**e, "_at": len(case.audio) / case.rate} for e in tracker.finish()]
    r["beats"], r["cpu_s"] = dedupe(evs), time.perf_counter() - t0
    r["realtime_x"] = r["audio_s"] / r["cpu_s"] if r["cpu_s"] > 0 else float("inf")
    return r


TRACKERS: Dict[str, Dict] = {
    "aubio": {"factory": AubioTracker, "offline": False, "note": "GPLv3+, optional, baseline"},
    "librosa": {"factory": LibrosaOffline, "offline": True, "note": "offline reference, sees the future"},
}


def register(name: str, factory: Callable, offline: bool = False, note: str = "") -> None:
    TRACKERS[name] = {"factory": factory, "offline": offline, "note": note}


def bench(cases: Sequence[Case], names: Sequence[str], hop: int = 512, log: Callable[[str], None] = print) -> Dict:
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
    """Conformance with the streaming contract above. Returns problems; [] means it conforms."""
    problems: List[str] = []
    case = synth_case("contract_120", 120, secs=10.0, rate=rate)
    for seed in (None, 120.0):
        try:
            tr = factory(rate, hop, seed_bpm=seed)
        except Exception as exc:
            return [f"factory(rate, hop, seed_bpm={seed}) raised {type(exc).__name__}: {exc}"]
        seen = 0
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
            pred = getattr(tr, "predict", None)
            if callable(pred) and b % 20 == 0:
                ahead = pred(at)
                if not isinstance(ahead, list):
                    problems.append("predict() must return a list")
                for p in ahead or []:
                    missing = [k for k in REQUIRED_KEYS if k not in p]
                    if missing:
                        problems.append(f"predict() item missing {missing}")
        if seen == 0:
            problems.append(f"no beats observed on a plain 120 bpm drum loop (seed={seed})")
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


def find_bpm_loops(max_results: int = 6000) -> List[str]:
    """Loops whose FILE NAME carries a BPM, from the Everything index (no drive crawl)."""
    from core.tools.everything import search
    r = search(r"regex:(?i)\d{2,3}\s?bpm.*\.(wav|flac|aiff?|mp3)$", max_results=max_results)
    return [p for p in r.paths if "loop" in p.lower() and parse_bpm(os.path.basename(p))]


def loop_category(path: str) -> str:
    low = os.path.basename(path).lower()
    return "kick" if any(w in low for w in _KICKY) else "tops" if any(w in low for w in _TOPS) else "melodic"


def stratified_loops(per_cat: int = 30, rng_seed: int = 23, exclude: Optional[set] = None) -> List[str]:
    """per_cat loop paths from each category (kick / tops / melodic), so a run is not dominated by melodic loops
    (most of the pool) and each class is scored with enough cases to mean something. `exclude` drops paths (a
    held-out draw excludes every loop that was ever used for tuning)."""
    pool = [p for p in find_bpm_loops() if not exclude or p not in exclude]
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


def loop_suite(n: int = 40, rng_seed: int = 7, tile_secs: float = 30.0, paths: Optional[List[str]] = None,
               log: Callable[[str], None] = print) -> List[Case]:
    """n loops sampled across packs and tempos, each tiled to tile_secs (loops loop seamlessly by design, and the
    trackers need time to lock). Tempo comes from the file name; phase is ASSUMED to start at t=0 (loops are cut
    to the grid). Third-party audio: evaluated in place, never copied into the repo."""
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
    for p in chosen:
        try:
            data, rate = sf.read(p, dtype="float32", always_2d=True)
        except Exception as exc:
            log(f"[beatbench] skip {os.path.basename(p)}: {type(exc).__name__}")
            continue
        mono = data.mean(axis=1)
        if len(mono) < rate:                            # under a second: a one-shot mislabelled as a loop
            continue
        reps = int(math.ceil(tile_secs * rate / len(mono)))
        audio = np.tile(mono, reps)[: int(tile_secs * rate)].astype(np.float32)
        bpm = float(parse_bpm(os.path.basename(p)))
        name = os.path.basename(p)
        cat = loop_category(p)
        cases.append(Case(name, audio, int(rate), beat_times(bpm, tile_secs, 0.0), bpm, phase_known=True,
                          source="loop", meta={"path": p, "category": cat, "loop_secs": round(len(mono) / rate, 2)}))
    return cases


# --- round 2: paired comparison, and real recordings with listened-to ground truth -----------------------------

def paired(rows_c: List[Dict], rows_ref: List[Dict], key: str, n_boot: int = 4000, seed: int = 0) -> Dict:
    """Per-case paired difference contestant - reference on one metric, over the cases both scored (matched by
    case name). Returns the mean difference and a 95 % bootstrap interval. Round 2 replaced round 1's fixed
    margin on one draw of 30 loops (smaller than the draw-to-draw noise: beat_a's own kick F moved .17 between two
    draws) with this: the same loops for both trackers, judged loop by loop."""
    ref = {r["case"]: r for r in rows_ref}
    d = np.array([r[key] - ref[r["case"]][key] for r in rows_c
                  if isinstance(r.get(key), (int, float)) and r["case"] in ref
                  and isinstance(ref[r["case"]].get(key), (int, float))], dtype=float)
    if not len(d):
        return {"n": 0}
    rng = np.random.default_rng(seed)
    boots = d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": int(len(d)), "mean": round(float(d.mean()), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)]}


RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "state", "arsenal", "keylab", "recordings")


def fit_grid(audio: np.ndarray, rate: int, bpm_lo: float = 60.0, bpm_hi: float = 200.0, hop: int = 256) -> Dict:
    """OFFLINE reference grid for a real recording: the constant tempo and first beat that best fit the WHOLE
    track's onsets (it sees the future, so it is a reference, never a tracker). Electronic music made in a DAW
    holds one tempo, which is what makes a whole-track fit trustworthy. The result is only ground truth after a
    person has listened to the click render and said it sits on the beat (annotate -> confirm)."""
    n_fft = 2048
    win = np.hanning(n_fft)
    frames = 1 + (len(audio) - n_fft) // hop
    env = np.zeros(frames)
    prev = None
    for i in range(frames):
        mag = np.log1p(100.0 * np.abs(np.fft.rfft(audio[i * hop:i * hop + n_fft] * win)))
        if prev is not None:
            env[i] = np.maximum(mag - prev, 0.0).mean()
        prev = mag
    env = np.maximum(env - np.median(env), 0.0)
    fps = rate / hop
    t = (np.arange(frames) * hop + n_fft / 2) / rate
    best = None
    for bpm in np.arange(bpm_lo, bpm_hi, 0.05):
        period = 60.0 / bpm
        ph = np.exp(2j * np.pi * t / period)
        z = (env * ph).sum() / (env.sum() + 1e-12)
        score = abs(z)
        if best is None or score > best[0]:
            best = (score, bpm, (np.angle(z) / (2 * np.pi)) % 1.0 * period)
    score, bpm, first = best
    # the octave this score cannot tell apart: report the alternatives too, a person decides by ear
    return {"bpm": round(float(bpm), 3), "first_beat": round(float(first), 4), "fit": round(float(score), 4),
            "fps": round(fps, 2)}


def _flux_envelopes(audio: np.ndarray, rate: int, hop: int = 256):
    n_fft = 2048
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
    t = (np.arange(frames) * hop + n_fft / 2) / rate
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


def recording_suite(root: Optional[str] = None, confirmed_only: bool = True, max_secs: float = 90.0) -> List[Case]:
    """Daniel's own recordings (beatsync.record; state/, never committed) that carry a sidecar
    `<file>.beats.json` {"bpm", "first_beat", "confirmed"}. Only confirmed ground truth is scored unless asked."""
    import glob
    import soundfile as sf
    cases = []
    for p in sorted(glob.glob(os.path.join(root or RECORDINGS_DIR, "*.flac"))):
        side = p + ".beats.json"
        if not os.path.exists(side):
            continue
        meta = json.load(open(side, encoding="utf-8"))
        if confirmed_only and not meta.get("confirmed"):
            continue
        data, rate = sf.read(p, dtype="float32", always_2d=True)
        audio = data.mean(axis=1)[: int(max_secs * rate)]
        secs = len(audio) / rate
        if meta.get("sections"):
            secs_ = [s for s in meta["sections"] if s["start"] < secs]
            beats = section_beats(secs_)
            meta = {**meta, "spans": [[s["start"], min(s["end"], secs)] for s in secs_]}
        else:
            first = float(meta["first_beat"]) % (60.0 / float(meta["bpm"]))
            beats = beat_times(float(meta["bpm"]), secs, first)
        cases.append(Case(os.path.basename(p), audio, int(rate), beats, float(meta["bpm"]),
                          seed_bpm=meta.get("seed_bpm"), phase_known=True, source="recording",
                          meta={"path": p, **meta}))
    return cases


def save_report(report: Dict, path: Optional[str] = None) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "state", "arsenal", "keylab", "receipts")
    path = path or os.path.join(root, f"beatbench-{stamp}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, default=str)
    return path
