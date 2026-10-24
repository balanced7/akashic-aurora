"""arsenal.keylab.tempo -- beat + BPM analysis from a live audio stream, seeded from BPM databases.

T4 beat/BPM lane (delegated under the KeyLab Control Center build watch).

This module is PURE ANALYSIS. It reads audio (WASAPI loopback or a caller-supplied sample buffer),
measures the beat, and emits per-beat dicts::

    {"bpm": float, "beat_phase": float, "confidence": float, "source": str}

where ``source`` is one of "seed" | "refined" | "snapped" | "offline".

HARD BOUNDARY: this module must never import ``winmidi``, ``protocol`` or ``ledframe`` -- nothing in the
T4 lane ever touches the KeyLab port. The hub subscribes to these beat events; the port is owned elsewhere.
The boundary is enforced by tests/test_keylab_tempo_boundary.py (AST import scan), so it is a machine
check, not a promise.

Licence: ``aubio`` (aubio-ledfx) is GPLv3+ and is imported LAZILY inside a function (never at module top),
because the licence call is still open with the operator. ``numpy`` and ``pyaudiowpatch`` are likewise
optional at import time -- this module imports cleanly with no heavy deps present, and only the functions
that need them pull them in.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

# --- constants ------------------------------------------------------------------------------------

DEFAULT_HOP = 512          # samples per analysis block
DEFAULT_WIN = 1024         # aubio tempo window
# Band into which tempo values are octave-folded before clustering (a "normal" dance-music BPM range).
FOLD_LO, FOLD_HI = 70.0, 140.0
# snap_to_octave factors: allow 1/2, 2/3, 1, 3/2 and 2x multiples of the detected tempo.
OCTAVE_FACTORS: Tuple[float, ...] = (0.5, 2.0 / 3.0, 1.0, 1.5, 2.0)
BPM_MIN, BPM_MAX = 40.0, 300.0
# A lone value further than this (fraction) from the cluster median is discarded as an outlier.
OUTLIER_FRAC = 0.08
# librosa warmup: buffer ~ this many seconds of audio for the seeded one-shot measurement.
WARMUP_SECONDS = 15.0


# --- the per-beat event record -------------------------------------------------------------------

@dataclass
class SourceBpm:
    """One BPM answer from one database, before fusion."""
    name: str              # e.g. "getsongbpm", "acousticbrainz", "deezer"
    bpm: float             # raw reported tempo (may be an octave off)
    weight: float = 1.0     # relative weight of this source in the cluster
    confidence: float = 0.5 # how much we trust this source alone

    def __post_init__(self) -> None:
        self.bpm = float(self.bpm)


@dataclass
class SeedResult:
    """The fused seed: the cluster median, its confidence, and how many sources agreed."""
    bpm: float
    confidence: float          # 0..1 -- how many sources agreed within tolerance
    source_count: int          # how many sources answered at all
    sources: List[SourceBpm] = field(default_factory=list)

    @property
    def is_strong(self) -> bool:
        return self.source_count >= 2 and self.confidence >= 0.5


# --- pure analysis primitives (no external deps) -------------------------------------------------

def fold_to_band(bpm: float, lo: float = FOLD_LO, hi: float = FOLD_HI) -> float:
    """Fold a tempo into [lo, hi) by doubling/halving, so half/double collapse to the same octave."""
    bpm = float(bpm)
    if bpm <= 0:
        return bpm
    while bpm >= hi:
        bpm /= 2.0
    while bpm < lo:
        bpm *= 2.0
    return bpm


def snap_to_octave(detected: float, anchor: float,
                   factors: Sequence[float] = OCTAVE_FACTORS) -> float:
    """Return the multiple of `detected` nearest `anchor` in log2 space, clamped to [BPM_MIN, BPM_MAX].

    This is the deterministic half/double fix: if the live detector locked to 2x (or 1/2, 3/2, 2/3)
    the true tempo, this folds it back onto the seed's octave before any tempo-derived animation.
    """
    detected = float(detected)
    anchor = float(anchor)
    if detected <= 0 or anchor <= 0:
        return detected
    best = detected
    best_dist = math.inf
    for f in factors:
        cand = detected * f
        if cand < BPM_MIN or cand > BPM_MAX:
            continue
        d = abs(math.log2(cand) - math.log2(anchor))
        if d < best_dist:
            best_dist = d
            best = cand
    return clamp_bpm(best)


def clamp_bpm(bpm: float) -> float:
    return max(BPM_MIN, min(BPM_MAX, float(bpm)))


def median(values: Sequence[float]) -> float:
    """Plain median (no numpy). Returns the middle value of a sorted copy."""
    if not values:
        raise ValueError("median of empty sequence")
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def fuse_bpm(sources: Sequence[SourceBpm],
             local: Optional[float] = None,
             outlier_frac: float = OUTLIER_FRAC) -> SeedResult:
    """Octave-fold every DB value (plus the optional local measurement) into one band, drop a lone
    outlier, and return the cluster median as the seed with a confidence = agreement strength.

    Per the fusion design: do NOT naive-average. Fold, cluster, median. A single-source seed is
    "weak"; 2+ sources agreeing within tolerance is "trusted".
    """
    vals: List[float] = []
    named: List[SourceBpm] = []
    for s in sources:
        if s.bpm <= 0:
            continue
        vals.append(fold_to_band(s.bpm))
        named.append(s)
    if local is not None and local > 0:
        vals.append(fold_to_band(local))
        named.append(SourceBpm(name="local", bpm=local, weight=1.0, confidence=1.0))

    if not vals:
        return SeedResult(bpm=0.0, confidence=0.0, source_count=0, sources=list(named))

    med = median(vals)

    # Discard a lone outlier: a value more than outlier_frac from the median, ONLY when it is alone
    # against a cluster of >=2. A single value is never an "outlier" (it is the whole seed).
    kept = [v for v in vals]
    if len(vals) >= 2:
        if all(abs(v - med) / med > outlier_frac for v in vals):
            # everything disagrees; keep the median as-is rather than inventing a cluster
            pass
        else:
            # drop values far from the median, but only if a cluster remains
            cluster = [v for v in vals if abs(v - med) / med <= outlier_frac * len(vals)]
            kept = cluster if cluster else vals

    seed = median(kept)
    nearest = [v for v in vals if abs(v - seed) / seed <= outlier_frac]
    # confidence scales with how many of the answering sources agree (0..1)
    confidence = len(nearest) / len(vals) if vals else 0.0
    if source_count := len(named):
        confidence = min(1.0, (len(nearest) / source_count) * (source_count / 2.0 + 0.5))

    return SeedResult(bpm=seed, confidence=min(1.0, confidence),
                      source_count=source_count or 0, sources=named)


def normalize_title(title: str) -> str:
    """Strip dirty SMTC decorations -- remix tags, 'feat.', bracket tags -- before querying a DB."""
    import re
    s = re.sub(r"\s*[\(\[].*?[\)\]]", "", title)      # drop (remix), [explicit], ...
    s = re.sub(r"\b(feat\.?|ft\.?)\s+.*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+(remix|radio edit|acoustic|instrumental)$", "", s, flags=re.IGNORECASE)
    return " ".join(s.split())


# --- database lookup (fail-soft, cached) ----------------------------------------------------------

# Keyed sources need a key (read from env, so it never lands in the repo). Keyless sources (2+3)
# work regardless. A key-absent run must still return whatever keyless sources answer.
def _get_getsongbpm_key() -> Optional[str]:
    import os
    return os.environ.get("GETSONGBPM_API_KEY") or os.environ.get("GET_SONG_BPM_KEY")


def _fetch_json(url: str, headers: Optional[dict] = None, timeout: float = 8.0) -> Optional[dict]:
    """Best-effort JSON GET through urllib (stdlib -- no requests dep). Returns None on any failure."""
    import json
    import urllib.request
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def lookup(artist: str, title: str, offline: bool = False) -> List[SourceBpm]:
    """Fetch BPM answers from the DB chain for "Artist - Title", each fail-soft and isolated.

    Priority: GetSongBPM (keyed) -> MusicBrainz -> AcousticBrainz (keyless, pre-2022 catalog) ->
    Deezer (keyless, low-weight). A missing key or a network failure simply skips that source.
    With offline=True, no network call is made and the result is empty (the local measurement is
    the only ground truth).
    """
    if offline:
        return []

    title_clean = normalize_title(title)
    found: List[SourceBpm] = []

    # Source 1 -- GetSongBPM (keyed; skip if no key).
    key = _get_getsongbpm_key()
    if key:
        try:
            from urllib.parse import quote
            q = f"song:{title_clean} artist:{artist}"
            u = f"https://api.getsong.co/search/?api_key={key}&type=both&lookup={quote(q)}"
            data = _fetch_json(u)
            if data and data.get("search") and data["search"][0].get("id"):
                song_url = f"https://api.getsong.co/song/?api_key={key}&id={data['search'][0]['id']}"
                song = _fetch_json(song_url)
                tempo = (song or {}).get("song", {}).get("tempo")
                try:
                    if tempo not in (None, "", "0"):
                        found.append(SourceBpm(name="getsongbpm", bpm=float(tempo), weight=1.0, confidence=0.8))
                except (TypeError, ValueError):
                    pass
        except Exception:
            pass

    # Source 2 -- MusicBrainz -> AcousticBrainz (keyless).
    try:
        from urllib.parse import quote
        mb_query = 'query=artist:"%s" AND recording:"%s"&fmt=json&limit=3' % (artist, title_clean)
        mb_url = "https://musicbrainz.org/ws/2/recording/?" + quote(mb_query, safe='=&\": ')
        # MusicBrainz asks for a contact in the User-Agent; the project page serves, so no personal address is sent
        mb = _fetch_json(mb_url, headers={"User-Agent": "AkashicKeyLab/1.0 ( https://github.com/balanced7/akashic-aurora )"})
        mbid = None
        for rec in (mb or {}).get("recordings", []):
            if rec.get("id"):
                mbid = rec["id"]
                break
        if mbid:
            ab = _fetch_json(f"https://acousticbrainz.org/api/v1/{mbid}/low-level")
            bpm = (ab or {}).get("rhythm", {}).get("bpm")
            if isinstance(bpm, (int, float)) and bpm > 0:
                found.append(SourceBpm(name="acousticbrainz", bpm=float(bpm), weight=0.8, confidence=0.6))
    except Exception:
        pass

    # Source 3 -- Deezer (keyless, low-weight; bpm 0 == missing, vote only).
    try:
        from urllib.parse import quote
        dz = _fetch_json(f"https://api.deezer.com/search?q={quote(f'{artist} {title_clean}')}")
        track_id = (dz or {}).get("data", [{}])[0].get("id")
        if track_id:
            t = _fetch_json(f"https://api.deezer.com/track/{track_id}")
            bpm = (t or {}).get("bpm")
            if isinstance(bpm, (int, float)) and bpm > 0:
                found.append(SourceBpm(name="deezer", bpm=float(bpm), weight=0.4, confidence=0.3))
    except Exception:
        pass

    return found


# --- live detection (lazy heavy deps) -------------------------------------------------------------

def _import_aubio():
    """Lazy aubio import -- GPLv3+, kept inside a function so this module never imports it at top level."""
    import aubio  # noqa: WPS433  (deliberate: GPL dependency is opt-in at call time)
    return aubio


def tempo_from_samples(samples: Sequence[float], hop: int = DEFAULT_HOP,
                       win: int = DEFAULT_WIN, rate: int = 44100,
                       aubio=None) -> Tuple[bool, float]:
    """Run one aubio.tempo block over a float buffer. Returns (beat_occurred, current_bpm_estimate).

    ``aubio`` may be passed in (already imported) to avoid the lazy import on every block.
    """
    if aubio is None:
        aubio = _import_aubio()
    tempo = _tempo_obj(aubio, hop, win, rate)
    import numpy as np
    arr = np.ascontiguousarray(np.asarray(samples, dtype=np.float32))
    beat = bool(tempo(arr)[0])
    return beat, float(getattr(tempo, "get_bpm", lambda: 0.0)())


# Cache a single aubio tempo object per (hop, win, rate) so the live loop is not re-allocating it.
_tempo_cache: Dict[Tuple[int, int, int], object] = {}


def _tempo_obj(aubio, hop: int, win: int, rate: int):
    key = (hop, win, rate)
    obj = _tempo_cache.get(key)
    if obj is None:
        obj = aubio.tempo("default", win, hop, rate)
        _tempo_cache[key] = obj
    return obj


class BeatTracker:
    """Streaming beat tracker: feeds audio blocks, emits per-beat events with seed-aware refinement.

    Usage::

        seed = fuse_bpm(lookup("Shift K3Y", "On My Mind")).bpm
        tracker = BeatTracker(seed_bpm=seed, rate=48000, offline=False)
        for block in audio_blocks:
            for ev in tracker.push(block):
                print(ev)   # {"bpm": ..., "beat_phase": ..., "confidence": ..., "source": ...}

    When a seed is present, the raw aubio BPM is octave-snapped back to the seed's octave
    (source "snapped"); when there is no seed, the raw aubio BPM is emitted (source "refined").
    This makes the deterministic half/double fix without ever injecting a prior into aubio
    (aubio.tempo has no start_bpm parameter).
    """

    def __init__(self, seed_bpm: Optional[float] = None, rate: int = 44100,
                 hop: int = DEFAULT_HOP, win: int = DEFAULT_WIN, offline: bool = False,
                 now: Optional[Callable[[], float]] = None):
        self.seed_bpm = float(seed_bpm) if seed_bpm and seed_bpm > 0 else None
        self.rate = rate
        self.hop = hop
        self.win = win
        self.offline = offline
        self._now = now or time.perf_counter
        self._last_beat_time: Optional[float] = None
        self._aubio = None   # imported lazily on first push

    def _ensure_aubio(self):
        if self._aubio is None:
            self._aubio = _import_aubio()
        return self._aubio

    def push(self, samples: Sequence[float]) -> List[dict]:
        """Feed one analysis block. Returns the list of per-beat events emitted by this block (0 or 1)."""
        import numpy as np

        arr = np.asarray(samples, dtype=np.float32)
        if arr.size == 0:
            return []
        if arr.ndim > 1:
            arr = arr.mean(axis=1)  # fold stereo to mono
        arr = np.ascontiguousarray(arr)
        # silence guard: don't lock onto near-silence (mirrors beatsync's std() gate)
        if float(arr.std()) < 1e-5:
            return []

        aubio = self._ensure_aubio()
        tempo = _tempo_obj(aubio, self.hop, self.win, self.rate)
        beat = bool(tempo(arr)[0])
        if not beat:
            return []

        raw_bpm = float(getattr(tempo, "get_bpm", lambda: 0.0)())
        now = self._now()
        if self.seed_bpm:
            bpm = snap_to_octave(raw_bpm, self.seed_bpm)
            source = "snapped" if abs(bpm - raw_bpm) > 1e-6 else "seed"
        else:
            bpm = clamp_bpm(raw_bpm)
            source = "refined"

        # beat_phase: fraction of a beat period elapsed since the last beat, 0..1 (folded from wall-clock).
        beat_phase = 0.0
        if self._last_beat_time is not None and bpm > 0:
            period = 60.0 / bpm
            beat_phase = ((now - self._last_beat_time) % period) / period
        self._last_beat_time = now

        # confidence: seed strength bleeds into the emitted confidence; raw refined beats are modest.
        confidence = 0.8 if (self.seed_bpm and source in ("seed", "snapped")) else 0.5

        return [{
            "bpm": round(bpm, 3),
            "beat_phase": round(beat_phase, 4),
            "confidence": confidence,
            "source": source,
        }]


def warmup_bpm(samples: Sequence[float], seed: float, rate: int = 44100,
               start_bpm: Optional[float] = None, std_bpm: float = 1.0) -> float:
    """One-shot librosa tempo on a ~15s warmup buffer, seeded with the fused DB value.

    librosa.feature.tempo accepts a start_bpm prior, which is where the DB seed genuinely helps
    (aubio has no such prior). Returns the locked anchor BPM, snapped to the seed's octave.
    This function is the ONLY place the seed touches the librosa path; the live loop stays aubio.
    """
    import numpy as np
    import librosa

    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.mean(axis=1)
    sr = rate
    # onset envelope drives the tempo estimate; start_bpm is the seeded prior from the DB fusion.
    try:
        onset = librosa.onset.onset_strength(y=arr, sr=sr)
        tempo = float(librosa.feature.tempo(
            onset_envelope=onset, sr=sr,
            start_bpm=float(start_bpm if start_bpm else seed),
            std_bpm=std_bpm, aggregate=np.median, max_tempo=BPM_MAX)[0])
    except Exception:
        # librosa missing or failed -- fall back to the seed itself.
        return float(seed)

    # snap the librosa result onto the seed's octave so warmup and live march agree.
    return snap_to_octave(tempo, seed)


def _loopback_stream(pa, rate: int, ch: int, hop: int):
    """Open a WASAPI loopback stream (lazy pyaudiowpatch import)."""
    inst = pa.PyAudio()
    try:
        dev = inst.get_default_wasapi_loopback()
    except Exception:
        for d in inst.get_loopback_device_info_generator():  # type: ignore[attr-defined]
            return inst, dev, inst.open(format=pa.paFloat32, channels=ch, rate=rate, input=True,
                                        input_device_index=d["index"], frames_per_buffer=hop)
        raise RuntimeError("no WASAPI loopback device found")
    stream = inst.open(format=pa.paFloat32, channels=ch, rate=rate, input=True,
                       input_device_index=dev["index"], frames_per_buffer=hop)
    return inst, dev, stream


def run(artist: str = "", title: str = "", secs: Optional[float] = None,
        rate: int = 0, offline: bool = False, seed_bpm: Optional[float] = None) -> int:
    """Convenience entry: seed from the DB (unless offline), then stream loopback emitting beat events.

    This is the analysis-only analogue of beatsync.run() -- it prints per-beat events (dict) and NEVER
    opens the KeyLab port. Its output is what the hub will later subscribe to.
    """
    import numpy as np

    # Seed from the DB chain (unless offline), fused to one trusted value.
    sources = lookup(artist, title, offline=offline)
    seed = fuse_bpm(sources, local=None).bpm if sources else None
    if seed_bpm:
        seed = seed_bpm
    if seed:
        print(f"seed: {seed:6.2f} BPM  (from {len(sources)} source(s); offline={offline})")

    if offline:
        # Offline: no loopback, but still exercise the analysis path on a synthetic buffer.
        tracker = BeatTracker(seed_bpm=seed, rate=rate or 44100, offline=True)
        synth = _synthetic_click(rate or 44100, seed or 120.0, 2.0)
        evs = []
        hop = DEFAULT_HOP
        for i in range(0, len(synth) - hop, hop):
            evs.extend(tracker.push(synth[i:i + hop]))
        for ev in evs[:10]:
            print(f"  beat event {ev}")
        print(f"offline run: {len(evs)} beat events from synthetic {seed or 120.0:.2f} BPM click")
        return 0

    # Live: WASAPI loopback (lazy pyaudiowpatch).
    try:
        import pyaudiowpatch as pa
    except Exception:
        print("pyaudiowpatch not available; run with --offline or install it")
        return 2
    try:
        inst, dev, stream = _loopback_stream(pa, rate or 44100, 2, DEFAULT_HOP)
    except Exception as e:
        print(f"loopback open failed: {e}")
        return 2
    actual_rate = int(dev["defaultSampleRate"]) if rate == 0 else rate
    ch = int(dev.get("maxInputChannels", 2) or 2)

    tracker = BeatTracker(seed_bpm=seed, rate=actual_rate, offline=False)
    t_end = (time.perf_counter() + secs) if secs else None
    beats = 0
    try:
        while t_end is None or time.perf_counter() < t_end:
            raw = stream.read(DEFAULT_HOP, exception_on_overflow=False)
            frames = np.frombuffer(raw, dtype=np.float32)
            if ch > 1:
                frames = frames.reshape(-1, ch).mean(axis=1)
            for ev in tracker.push(frames):
                beats += 1
                print(f"  beat event {ev}")
    except KeyboardInterrupt:
        pass
    finally:
        try:
            stream.stop_stream(); stream.close(); inst.terminate()
        except Exception:
            pass
    print(f"done -- {beats} beat events")
    return 0


def _synthetic_click(rate: int, bpm: float, seconds: float) -> List[float]:
    """Synthesize a click track at a target BPM (for offline analysis testing). No external deps."""
    period = 60.0 / bpm
    n = int(rate * seconds)
    out = [0.0] * n
    t = 0.0
    while t < seconds:
        i = int(t * rate)
        if i < n:
            out[i] = 1.0
        t += period
    return out
