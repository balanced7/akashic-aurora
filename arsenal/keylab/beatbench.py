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


def beat_times(bpm: float, secs: float, offset: float = 0.0, ramp_to: Optional[float] = None) -> np.ndarray:
    """Beat times for a constant tempo, or a linear ramp from bpm to ramp_to over the whole case."""
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
               seed_bpm: Optional[float] = None, rng_seed: int = 7) -> Case:
    """Exact-ground-truth audio. style: click | drums | sparse (kick only on 1, hats off) | offbeat (hats
    on the 'and', the classic octave trap)."""
    rng = np.random.default_rng(rng_seed)
    beats = beat_times(bpm, secs, offset, ramp_to)
    buf = np.zeros(int(secs * rate) + rate, dtype=np.float32)
    kick, snare, hat, click = _kick(rate), _snare(rate, rng), _hat(rate, rng), _click(rate)
    for k, t in enumerate(beats):
        nxt = beats[k + 1] if k + 1 < len(beats) else t + 60.0 / bpm
        half = t + (nxt - t) * (0.5 + swing / 2)
        pos = k % 4
        if style == "click":
            _place(buf, click, t, rate, 1.0 if pos == 0 else 0.6)
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
                meta={"style": style, "swing": swing, "ramp_to": ramp_to, "noise": noise, "offset": offset})


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
    leads = [(b["t_beat"] - b["_at"]) * 1000 for b in result["beats"]]
    if leads:
        out["lead_ms"] = round(float(np.median(leads)), 1)
    if case.phase_known and len(case.beats):
        ref_t, est_t = _trim(case.beats, SKIP_FIRST), _trim(est, SKIP_FIRST)
        out["F"] = round(f_measure(est_t, ref_t), 3)
        out.update({k: round(v, 3) for k, v in cml_aml(est_t, ref_t).items()})
        lt = lock_time(est, case.beats)
        out["lock_s"] = round(lt, 2) if lt is not None else None
        if result.get("predictions"):
            out.update(prediction_error(result["predictions"], case.beats, after=lt if lt is not None else SKIP_FIRST))
    return out


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


def stratified_loops(per_cat: int = 30, rng_seed: int = 23) -> List[str]:
    """per_cat loop paths from each category (kick / tops / melodic), so a run is not dominated by melodic loops
    (most of the pool) and each class is scored with enough cases to mean something."""
    pool = find_bpm_loops()
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


def save_report(report: Dict, path: Optional[str] = None) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "state", "arsenal", "keylab", "receipts")
    path = path or os.path.join(root, f"beatbench-{stamp}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, default=str)
    return path
