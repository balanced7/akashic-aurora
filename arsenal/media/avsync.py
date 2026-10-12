"""arsenal.media.avsync -- how far apart two recordings of the same moment are, in milliseconds, and whether the gap
grows (drift). Or the same question for one recording against a list of event times, such as the piano's note-ons.

Sync was measured by hand in 22 calls by 8 agents, and a sync.py was written three times, before this.

    offset(a, b)                          # same sound later in b -> positive offset_ms
    offset(a, None, a_track=0, b_track=1) # two tracks of one file: is the Discord track late?
    against_events(src, note_on_file_t)   # sound later than the events -> positive offset_ms
    against_session(src, "20261011-165503-f62d348c")   # the practice log, placed by jam.align's anchor

Method: each audio track is decoded once through ff as a 16 kHz mono stream and turned into an onset envelope (log
spectral flux, 32 ms window, 5 ms hop) block by block, so a 41-minute recording never sits in memory as samples.
Two envelopes are cross-correlated (Pearson per lag, every lag in +-max_offset_s), the peak is refined by a parabola,
and the confidence is the peak over the best peak outside the main lobe: a rhythm that repeats inside the search range
shows up as a confidence near 1. The same search over consecutive windows gives one offset per window; a line through
the confident ones gives the drift in ms per minute and the spread says whether the gap held steady.

Event lists become an envelope by placing, at every event time, the flux this method measures for a click at that
time, so the reported offset is the time from the event to the sound's attack.

Measured 2026-10-12: an AAC copy shifted with -itsoffset 0.083 comes back at 82.34 ms (the mp4 edit list rounds the
shift to 82.333 ms); a drift of 12 ms per minute reads 12.04; a click track against its own times, shifted by up to
400 ms either way, is off by at most 0.19 ms; a 41-minute OBS recording is read in 7.5 s. The practice log shows the
limit: every key sounds twice there (the keyboard on the mic, the synth on desktop audio, 70-95 ms apart), so the
confidence reads 1.0 and both lobes are listed in candidates. Dense piano also finds an onset within 50 ms for about a
third of its note-ons at any offset, so the match count is read against the same count at offsets 0.5-1.5 s away
(match_lift): 1.19 at the chosen lobe of the 41-minute take, 1.01-1.05 at wrong offsets.

A silent track, or a best match on the edge of the search, is refused rather than reported as an offset.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from . import ff, receipt
from .words import audio_tracks, parse_span, resolve_span, resolve_track

SAMPLE_RATE = 16000
HOP = 80                     # 5 ms
N_FFT = 512                  # 32 ms
BLOCK = 1 << 16              # samples per read from ffmpeg (~4 s)
GAIN = 100.0                 # log1p(GAIN * |X|): onsets count by ratio, not level
MIN_CONFIDENCE = 1.5         # a window counts toward drift only above this peak/second-peak ratio
MIN_PEAK = 0.05              # ... and with at least this correlation
WINDOW_SEARCH_S = 0.5        # windows search this far either side of the whole-span offset
MIN_EVENTS_PER_WINDOW = 4
TOL_MS = 50.0                # an event is matched when an audio onset lies this close after the offset
SMOOTH = 9                   # Hann taps (45 ms) on both envelopes before correlating: the rounder peak
                             # interpolates to 0.2 ms on click tracks, against 1.4 ms unsmoothed (measured)
CONF_CAP = 99.0
CHANCE_SHIFTS_S = (-1.5, -1.25, -1.0, -0.75, -0.5, 0.5, 0.75, 1.0, 1.25, 1.5)
MIN_LIFT = 1.1               # matched / matched by chance: below this the matches say nothing about the offset.
                             # Dense piano matches a third of its note-ons within 50 ms at ANY offset; the 41-min
                             # practice take gives 1.19 at the chosen lobe and 1.01-1.05 at wrong offsets

BLIND = [
    "audio only: this compares sounds, not picture with sound (avsync.visual is v1), so 'A/V in sync' means the "
    "audio tracks agree with each other or with the event log",
    "a sound that repeats inside the search range (a steady beat, a loop) gives several equal peaks; the confidence "
    "says so (near 1) but the offset is then a guess between them",
    "one sound reaching the recording twice (a keyboard on the mic and its synth on desktop audio) gives two lobes of "
    "near-equal height: both are in candidates, and the chosen offset may be either",
    "the attack of a real instrument rises over a few ms; the offset is measured to that attack, not to the key press",
    "matched counts events with an onset within tol_ms; on dense music many match at any offset, so read it against "
    "matched_chance (the same count at offsets 0.5-1.5 s away) and match_lift, never alone",
    "the search sees only +-max_offset_s: a true offset beyond it can come back as a weak peak somewhere inside",
    "gaps inside an audio track are not filled: the sample count is the clock after the first sample",
    "times count from the file's first timestamp (format start_time), the same clock as arsenal.media.frames",
]


# =================================================================================================
# onset envelope, streamed
# =================================================================================================

def flux(blocks: Iterable["np.ndarray"], *, n_fft: Optional[int] = None, hop: Optional[int] = None) -> "np.ndarray":
    """Log spectral flux of a mono float signal given in blocks. Frame i is centred on sample i*hop."""
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view
    n_fft, hop = n_fft or N_FFT, hop or HOP
    win = np.hanning(n_fft + 1)[:-1].astype(np.float32)
    carry = np.zeros(n_fft // 2, np.float32)
    prev = None
    out = []
    for x in blocks:
        buf = np.concatenate([carry, np.asarray(x, np.float32)])
        n = (len(buf) - n_fft) // hop + 1
        if n <= 0:
            carry = buf
            continue
        fr = sliding_window_view(buf, n_fft)[::hop][:n]
        mag = np.log1p(GAIN * np.abs(np.fft.rfft(fr * win, axis=1)))
        first = mag[:1] if prev is None else prev[None]
        out.append(np.maximum(np.diff(np.vstack([first, mag]), axis=0), 0.0).sum(axis=1))
        prev = mag[-1]
        carry = buf[n * hop:]
    return np.concatenate(out) if out else np.zeros(0)


def _decode_args(path, track: int, t0: float, dur: Optional[float]) -> List[str]:
    return ["-v", "error", *(["-ss", f"{t0:.6f}"] if t0 else []), "-i", str(path),
            *(["-t", f"{dur:.6f}"] if dur else []), "-map", f"0:a:{track}", "-vn", "-sn", "-dn",
            "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"]


def envelope(path, track: int = 0, t0: float = 0.0, dur: Optional[float] = None) -> "np.ndarray":
    """Onset envelope of one audio track over [t0, t0+dur), one value per 5 ms, streamed from ffmpeg."""
    import numpy as np
    proc = ff.popen(_decode_args(path, track, t0, dur))

    def blocks() -> Iterator["np.ndarray"]:
        rest = b""
        while True:
            raw = proc.stdout.read(BLOCK * 4)
            if not raw:
                break
            raw = rest + raw
            cut = len(raw) - len(raw) % 4
            rest = raw[cut:]
            yield np.frombuffer(raw[:cut], np.float32)

    try:
        env = flux(blocks())
    finally:
        ff.finish(proc, timeout=60)
    return env


def _require_sound(env: "np.ndarray", path, track: int, t0: float, t1: float) -> None:
    """A silent track (a muted mic, a Discord track nobody spoke on) correlates as all zeros, whose argmax is the
    search edge: refuse it instead of reporting that edge as an offset."""
    if env.size == 0 or float(env.max()) <= 0.0:
        raise ff.MediaError(f"audio track {track} of {Path(path).name} is silent over {t0:g}-{t1:g} s: there is no "
                            f"onset to line up")


# =================================================================================================
# correlation
# =================================================================================================

def ncc_valid(x: "np.ndarray", y: "np.ndarray") -> "np.ndarray":
    """r[k] = Pearson correlation of x with y[k : k+len(x)], for every k where x fits inside y."""
    import numpy as np
    from scipy.signal import correlate
    n = len(x)
    x = x - x.mean()
    xn = float(np.sqrt((x * x).sum()))
    num = correlate(y, x, mode="valid")
    cs = np.concatenate([[0.0], np.cumsum(y, dtype=np.float64)])
    cs2 = np.concatenate([[0.0], np.cumsum(y.astype(np.float64) ** 2)])
    s, s2 = cs[n:] - cs[:-n], cs2[n:] - cs2[:-n]
    den = xn * np.sqrt(np.maximum(s2 - s * s / n, 1e-12))
    return num / np.where(den > 0, den, np.inf)


def _peak(r: "np.ndarray") -> Tuple[float, float, float]:
    """(refined index, peak value, confidence = peak / best peak outside the main lobe)."""
    import numpy as np
    i = int(np.argmax(r))
    peak = float(r[i])
    frac = 0.0
    if 0 < i < len(r) - 1:
        den = r[i - 1] - 2 * r[i] + r[i + 1]
        if den < 0:
            frac = float(np.clip(0.5 * (r[i - 1] - r[i + 1]) / den, -0.5, 0.5))
    lo = i
    while lo > 0 and r[lo - 1] <= r[lo]:
        lo -= 1
    hi = i
    while hi < len(r) - 1 and r[hi + 1] <= r[hi]:
        hi += 1
    outside = np.concatenate([r[:lo], r[hi + 1:]])
    second = float(outside.max()) if outside.size else 0.0
    if peak <= 0:
        conf = 0.0
    elif second <= 0:
        conf = CONF_CAP
    else:
        conf = min(peak / second, CONF_CAP)
    return i + frac, peak, conf


def _search(a: "np.ndarray", b: "np.ndarray", start: int, length: int, lag_lo: int, lag_hi: int):
    """Best lag (hops) of b against a[start:start+length], searching lags in [lag_lo, lag_hi] (b later = positive)."""
    lo = start + lag_lo
    hi = start + length + lag_hi
    if lo < 0 or hi > len(b) or start + length > len(a) or length < 20:
        return None
    r = ncc_valid(a[start:start + length], b[lo:hi])
    idx, peak, conf = _peak(r)
    return lag_lo + idx, peak, conf, r


def _lobes(r: "np.ndarray", lag_lo: int, hop_s: float, n: int = 3, min_sep_s: float = 0.05) -> List[dict]:
    """The n strongest separate peaks of a correlation curve: two sources of one sound (a key's thump on the mic and
    the synth on desktop audio) show up as two lobes of near-equal height."""
    import numpy as np
    if r.size < 3:
        return []
    m = np.flatnonzero((r[1:-1] >= r[:-2]) & (r[1:-1] >= r[2:])) + 1
    picked: List[int] = []
    sep = max(1, int(round(min_sep_s / hop_s)))
    for i in m[np.argsort(r[m])[::-1]]:
        if all(abs(int(i) - j) >= sep for j in picked):
            picked.append(int(i))
        if len(picked) == n:
            break
    return [{"offset_ms": round((lag_lo + i) * hop_s * 1000, 1), "peak": round(float(r[i]), 3)} for i in picked]


def _at_edge(r: "np.ndarray") -> bool:
    """The best lag sits on the first or last lag searched: the curve still rises past it, so it is no peak."""
    import numpy as np
    i = int(np.argmax(r))
    return i == 0 or i == r.size - 1


def _fit_drift(rows: List[dict], t0: float) -> dict:
    """A line through the confident windows' offsets (one pass of 3-MAD outlier rejection); its intercept is the
    offset at the span start t0."""
    import numpy as np
    used = [w for w in rows if w["used"]]
    if len(used) < 2:
        return {"drift_ms_per_min": None, "offset_at_start_ms": None, "spread_ms": None, "resid_ms": None,
                "windows_used": len(used), "drift_note": "fewer than 2 confident windows"}
    t = np.array([((w["file_t0"] + w["file_t1"]) / 2 - t0) / 60.0 for w in used])
    y = np.array([w["offset_ms"] for w in used])
    keep = np.ones(len(t), bool)
    for _ in range(2):
        slope, icpt = np.polyfit(t[keep], y[keep], 1) if keep.sum() >= 2 else (0.0, float(np.median(y)))
        res = y - (slope * t + icpt)
        mad = float(np.median(np.abs(res[keep] - np.median(res[keep])))) * 1.4826
        new = np.abs(res) <= max(3 * mad, 2.0)
        if new.sum() < 2 or (new == keep).all():
            break
        keep = new
    for w, k in zip(used, keep):
        w["used"] = bool(k)
    yk = y[keep]
    return {"drift_ms_per_min": round(float(slope), 3), "offset_at_start_ms": round(float(icpt), 2),
            "spread_ms": round(float(yk.max() - yk.min()), 2), "resid_ms": round(float(np.std(res[keep])), 2),
            "windows_used": int(keep.sum())}


def _windows(a, b, lag_c: float, window_s: float, t0: float, hop_s: float, search_s: float,
             counts: Optional["np.ndarray"] = None) -> List[dict]:
    """Offsets per consecutive window, each searched within +-search_s of the whole-span lag."""
    w = int(round(window_s / hop_s))
    k = int(round(search_s / hop_s))
    c = int(round(lag_c))
    rows = []
    for s in range(max(0, k - c), min(len(a), len(b) - c - k) - w + 1, w):
        found = _search(a, b, s, w, c - k, c + k)
        if found is None:
            continue
        lag, peak, conf, r = found
        n_ev = int(counts[s:s + w].sum()) if counts is not None else None
        enough = n_ev is None or n_ev >= MIN_EVENTS_PER_WINDOW
        edge = _at_edge(r)
        rows.append({"file_t0": round(t0 + s * hop_s, 3), "file_t1": round(t0 + (s + w) * hop_s, 3),
                     "offset_ms": round(lag * hop_s * 1000, 2), "peak": round(peak, 3),
                     "confidence": round(conf, 2), "events": n_ev, "edge": edge,
                     "used": bool(enough and not edge and conf >= MIN_CONFIDENCE and peak >= MIN_PEAK)})
    return rows


def _smooth(env: "np.ndarray") -> "np.ndarray":
    import numpy as np
    ker = np.hanning(SMOOTH + 2)[1:-1]
    return np.convolve(env, ker / ker.sum(), mode="same")


def _align(a: "np.ndarray", b: "np.ndarray", t0: float, max_offset_s: float, window_s: float,
           counts: Optional["np.ndarray"] = None) -> dict:
    hop_s = HOP / SAMPLE_RATE
    a, b = _smooth(a), _smooth(b)
    k = int(round(max_offset_s / hop_s))
    n = min(len(a), len(b))
    if n - 2 * k < int(round(2.0 / hop_s)):
        raise ff.MediaError(f"the span is too short for a +-{max_offset_s:g} s search: it needs at least "
                            f"{2 * max_offset_s + 2:g} s of audio")
    lag, peak, conf, r = _search(a[:n], b[:n], k, n - 2 * k, -k, k)
    if peak <= 0:
        raise ff.MediaError(f"the two signals share no onsets within +-{max_offset_s:g} s (best correlation "
                            f"{peak:.3f})")
    if _at_edge(r):
        raise ff.MediaError(f"the best match sits on the edge of the +-{max_offset_s:g} s search "
                            f"({lag * hop_s * 1000:+.0f} ms): the true offset is probably beyond it; widen "
                            f"max_offset_s")
    rows = _windows(a[:n], b[:n], lag, window_s, t0, hop_s, min(WINDOW_SEARCH_S, max_offset_s), counts)
    out = {"offset_ms": round(lag * hop_s * 1000, 2), "confidence": round(conf, 2), "peak": round(peak, 3),
           "candidates": _lobes(r, -k, hop_s)}
    out.update(_fit_drift(rows, t0))
    out["windows"] = rows
    return out


# =================================================================================================
# two signals
# =================================================================================================

def _span_for(path, track: Optional[int], span) -> Tuple[int, float, float]:
    streams, duration = audio_tracks(path)
    tr = resolve_track(streams, track, path)
    t0, t1 = resolve_span(span, duration)
    return tr, t0, t1


def offset(a, b=None, *, a_track: int = 0, b_track: Optional[int] = None, span=None, max_offset_s: float = 2.0,
           window_s: float = 30.0) -> dict:
    """How much later the same sound comes in b than in a (ms), with confidence, drift per minute and per-window
    offsets. b=None compares two tracks of a (b_track defaults to 1)."""
    same = b is None
    b = a if same else b
    if b_track is None:
        b_track = 1 if same else 0
    if same and a_track == b_track:
        raise ff.MediaError("comparing a track with itself: give b, or a different b_track")
    if max_offset_s <= 0 or window_s <= 2 * min(WINDOW_SEARCH_S, max_offset_s):
        raise ff.MediaError("max_offset_s must be > 0 and window_s longer than the window search")
    ta, t0, t1 = _span_for(a, a_track, span)
    tb_, _, _ = _span_for(b, b_track, (t0, t1) if span is not None else None)
    started = time.perf_counter()
    env_a = envelope(a, ta, t0, t1 - t0)
    _require_sound(env_a, a, ta, t0, t1)
    env_b = envelope(b, tb_, t0, t1 - t0)
    _require_sound(env_b, b, tb_, t0, t1)
    found = _align(env_a, env_b, t0, max_offset_s, window_s)
    elapsed = time.perf_counter() - started
    params = {"a_track": ta, "b_track": tb_, "span": [t0, t1] if span is not None else None,
              "max_offset_s": max_offset_s, "window_s": window_s, "window_search_s": WINDOW_SEARCH_S,
              "sample_rate": SAMPLE_RATE, "hop_ms": HOP * 1000 / SAMPLE_RATE, "n_fft": N_FFT,
              "min_confidence": MIN_CONFIDENCE, "min_peak": MIN_PEAK}
    payload = dict(found, meaning="offset_ms > 0: the same sound comes offset_ms later in b than in a",
                   reading=_reading(found, "b", "a", max_offset_s), span=[t0, t1], elapsed_s=round(elapsed, 2),
                   envelope_s=round(min(len(env_a), len(env_b)) * HOP / SAMPLE_RATE, 2))
    return receipt.result("avsync", a if same else [a, b], params, payload, BLIND, engine=_engine())


def _reading(found: dict, later: str, earlier: str, max_offset_s: float) -> str:
    off, conf = found["offset_ms"], found["confidence"]
    side = f"{later} is {abs(off):.1f} ms {'later' if off >= 0 else 'earlier'} than {earlier}"
    drift = found.get("drift_ms_per_min")
    tail = f", drift {drift:+.2f} ms/min over {found['windows_used']} windows" if drift is not None else ""
    others = ", ".join(f"{c['offset_ms']:+.0f}" for c in found.get("candidates", [])[1:])
    weak = "" if conf >= MIN_CONFIDENCE else (" (WEAK: two sources, a repeating sound, too little in common, or an "
                                              f"offset beyond +-{max_offset_s:g} s"
                                              + (f"; other lobes at {others} ms" if others else "") + ")")
    return f"{side} (confidence {conf:.1f}{weak}){tail}"


def _engine() -> dict:
    import importlib.metadata
    out = {}
    for dist in ("numpy", "scipy"):
        try:
            out[dist] = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            out[dist] = None
    return out


# =================================================================================================
# a signal against event times
# =================================================================================================

@lru_cache(maxsize=1)
def click_template() -> Tuple[Tuple[float, ...], int]:
    """(flux of a click, index of the click's own time in it): what one event looks like to this method."""
    import numpy as np
    sr, at = SAMPLE_RATE, 1.0
    rng = np.random.default_rng(7)
    x = np.zeros(int(2 * sr), np.float32)
    n = int(0.05 * sr)
    burst = rng.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / (0.012 * sr)).astype(np.float32)
    x[int(at * sr):int(at * sr) + n] += 0.3 * burst
    env = flux([x])
    i0 = int(round(at * sr / HOP))
    pre, post = 8, 24
    seg = env[i0 - pre:i0 + post]
    return tuple(float(v) for v in seg), pre


def event_envelope(times_s: Sequence[float], n: int, t0: float = 0.0,
                   weights: Optional[Sequence[float]] = None) -> Tuple["np.ndarray", "np.ndarray"]:
    """(envelope, events per hop) of n hops from t0: the click template placed at every event time, split between
    the two nearest hops so sub-hop times survive."""
    import numpy as np
    hop_s = HOP / SAMPLE_RATE
    imp = np.zeros(n + 2)
    counts = np.zeros(n)
    w = np.ones(len(times_s)) if weights is None else np.asarray(weights, float)
    pos = (np.asarray(times_s, float) - t0) / hop_s
    ok = (pos >= 0) & (pos < n - 1)
    p, wk = pos[ok], w[ok]
    i = np.floor(p).astype(int)
    f = p - i
    np.add.at(imp, i, wk * (1 - f))
    np.add.at(imp, i + 1, wk * f)
    np.add.at(counts, np.clip(np.rint(p).astype(int), 0, n - 1), 1)
    tmpl, pre = click_template()
    env = np.convolve(imp[:n], np.asarray(tmpl))[pre:pre + n]
    return env, counts


def onsets(env: "np.ndarray", t0: float = 0.0) -> "np.ndarray":
    """Attack times (s) picked from an onset envelope: local peaks above a moving median, moved back by the click
    template's own peak delay so they sit on the attack."""
    import numpy as np
    from scipy.ndimage import median_filter
    from scipy.signal import find_peaks
    if env.size < 3:
        return np.zeros(0)
    base = median_filter(env, size=61, mode="nearest")
    mad = float(np.median(np.abs(env - np.median(env)))) or 1e-9
    peaks, _ = find_peaks(env, height=base + 3 * mad, distance=4)
    tmpl, pre = click_template()
    delay = int(np.argmax(tmpl)) - pre
    return t0 + (peaks - delay) * HOP / SAMPLE_RATE


def _match(event_t: "np.ndarray", onset_t: "np.ndarray", offset_s: float, drift_per_s: float, ref_t: float,
           tol_s: float) -> Tuple[int, List[float]]:
    import numpy as np
    if onset_t.size == 0 or event_t.size == 0:
        return 0, []
    want = event_t + offset_s + drift_per_s * (event_t - ref_t)
    j = np.clip(np.searchsorted(onset_t, want), 1, len(onset_t) - 1)
    near = np.where(np.abs(onset_t[j - 1] - want) <= np.abs(onset_t[j] - want), onset_t[j - 1], onset_t[j])
    res = near - want
    hit = np.abs(res) <= tol_s
    return int(hit.sum()), [float(r) for r in res[hit]]


def _chance_rate(event_t: "np.ndarray", onset_t: "np.ndarray", offset_s: float, drift_per_s: float, ref_t: float,
                 tol_s: float, lo: float, hi: float) -> Optional[float]:
    """The share of events matched at offsets CHANCE_SHIFTS_S away from the found one (median), counting only events
    that land inside the audio there: what the match count is worth when nothing lines up."""
    import numpy as np
    rates = []
    for d in CHANCE_SHIFTS_S:
        want = event_t + offset_s + d + drift_per_s * (event_t - ref_t)
        keep = (want >= lo) & (want < hi)
        if keep.sum() >= MIN_EVENTS_PER_WINDOW:
            m, _ = _match(event_t[keep], onset_t, offset_s + d, drift_per_s, ref_t, tol_s)
            rates.append(m / keep.sum())
    return float(np.median(rates)) if rates else None


def _events_in(event_times_s: Sequence[float], weights: Optional[Sequence[float]]):
    """(sorted times, weights in the same order or None); malformed input fails closed."""
    import numpy as np
    try:
        raw = np.asarray([float(t) for t in event_times_s], float)
    except (TypeError, ValueError) as exc:
        raise ff.MediaError(f"event times must be numbers (file_t seconds): {exc}") from None
    if raw.size == 0:
        raise ff.MediaError("no event times given")
    if not np.isfinite(raw).all():
        raise ff.MediaError("event times hold NaN or infinity")
    order = np.argsort(raw, kind="stable")
    if weights is None:
        return raw[order], None
    w = np.asarray(weights, float)
    if w.shape != raw.shape:
        raise ff.MediaError(f"{w.size} weights for {raw.size} events: give one weight per event")
    return raw[order], w[order]


def against_events(src, event_times_s: Sequence[float], *, track: int = 0, span=None, max_offset_s: float = 2.0,
                   window_s: float = 60.0, weights: Optional[Sequence[float]] = None, tol_ms: float = TOL_MS,
                   _prior: Optional[dict] = None) -> dict:
    """How much later the sound comes than the event times (ms; times are file_t on src's clock), with drift per
    minute, and how many events found an audio onset within tol_ms once the offset is applied, against how many
    find one at offsets 0.5-1.5 s away (matched_chance, match_lift)."""
    ev, w = _events_in(event_times_s, weights)
    tr, t0, t1 = _span_for(src, track, span)
    started = time.perf_counter()
    audio = envelope(src, tr, t0, t1 - t0)
    _require_sound(audio, src, tr, t0, t1)
    t_end = t0 + len(audio) * HOP / SAMPLE_RATE
    inside = (ev >= t0 - max_offset_s) & (ev < t_end + max_offset_s)
    if inside.sum() < MIN_EVENTS_PER_WINDOW:
        raise ff.MediaError(f"only {int(inside.sum())} of {ev.size} events fall inside the audio "
                            f"({t0:.1f}-{t1:.1f} s): check the clock the times are on")
    ev_env, counts = event_envelope(ev, len(audio), t0, w)
    found = _align(ev_env, audio, t0, max_offset_s, window_s, counts)
    # offset_ms is the whole span's: the drift pivots about the span's middle. (Matching along the windows' line was
    # tried: on two-lobe audio the line sits between the lobes and catches both within tol_ms, a count that flatters.)
    off_s = found["offset_ms"] / 1000.0
    drift_s = (found["drift_ms_per_min"] or 0.0) / 60000.0
    mid, tol_s = (t0 + t_end) / 2, tol_ms / 1000.0
    on = onsets(audio, t0)
    in_audio = ev[(ev >= t0) & (ev < t_end)]
    matched, res = _match(in_audio, on, off_s, drift_s, mid, tol_s)
    chance = _chance_rate(in_audio, on, off_s, drift_s, mid, tol_s, t0, t_end)
    matched_chance = int(round(chance * in_audio.size)) if chance is not None else None
    lift = round(matched / matched_chance, 2) if matched_chance else None
    for c in found["candidates"]:
        c["matched"] = _match(in_audio, on, c["offset_ms"] / 1000.0, drift_s, mid, tol_s)[0]
    elapsed = time.perf_counter() - started
    absr = sorted(abs(r) * 1000 for r in res)
    params = {"track": tr, "span": [t0, t1] if span is not None else None, "max_offset_s": max_offset_s,
              "window_s": window_s, "window_search_s": WINDOW_SEARCH_S, "weights": weights is not None,
              "tol_ms": tol_ms, "sample_rate": SAMPLE_RATE, "hop_ms": HOP * 1000 / SAMPLE_RATE, "n_fft": N_FFT,
              "min_confidence": MIN_CONFIDENCE, "min_peak": MIN_PEAK,
              "min_events_per_window": MIN_EVENTS_PER_WINDOW, "chance_shifts_s": list(CHANCE_SHIFTS_S),
              "min_lift": MIN_LIFT}
    reading = _reading(found, "the sound", "the events", max_offset_s)
    if lift is not None and lift < MIN_LIFT:
        reading += (f"; the matches are no better than chance ({matched} matched, {matched_chance} at offsets "
                    f"0.5-1.5 s away)")
    payload = dict(found, meaning="offset_ms > 0: the sound comes offset_ms after the event time",
                   reading=reading, events=int(ev.size), events_in_audio=int(in_audio.size), matched=matched,
                   unmatched=int(in_audio.size - matched), matched_chance=matched_chance, match_lift=lift,
                   matched_meaning="events with an audio onset within tol_ms of event + offset_ms (+ the drift about "
                                   "the span's middle); each candidate's matched is the same count at its offset",
                   onsets=int(on.size),
                   match_resid_ms={"median": round(absr[len(absr) // 2], 2) if absr else None,
                                   "p90": round(absr[int(0.9 * (len(absr) - 1))], 2) if absr else None},
                   span=[t0, t1], elapsed_s=round(elapsed, 2))
    if _prior:
        payload["prior"] = _prior
    return receipt.result("avsync", src, params, payload, BLIND, engine=_engine())


# =================================================================================================
# the practice log
# =================================================================================================

def obs_start_epoch_ms(path) -> Optional[float]:
    """Recording start from an OBS file name ('2026-10-11 17-06-22.mp4', local time, whole seconds)."""
    import re
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})[ _](\d{2})-(\d{2})-(\d{2})", Path(path).stem)
    if not m:
        return None
    return datetime(*(int(g) for g in m.groups())).timestamp() * 1000


def session_anchor(info: dict) -> dict:
    """Where session t_ms 0 sits on the wall clock, by jam.align's ladder for a session on its own (no run, so no ack:
    L3 from the client's open time, else L4 from the server's, refused when buffered)."""
    from arsenal.jam import align
    meta = info.get("meta") or {}
    client = align.epoch_ms_of(meta.get("opened_at_client"))
    if client is not None:
        return {"method": "L3", "epoch_ms": client, "error_ms": align.ERROR_MS["L3"], "from": "opened_at_client"}
    if meta.get("buffered"):
        raise ff.MediaError("the session was buffered and has no opened_at_client: its open time can be far from its "
                            "first note (jam.align refuses it too)")
    opened = align.epoch_ms_of(info.get("opened_at"))
    if opened is None:
        raise ff.MediaError("the session has no open time")
    return {"method": "L4", "epoch_ms": opened, "error_ms": align.ERROR_MS["L4"], "from": "opened_at"}


def against_session(src, session: str, *, root=None, track: int = 0, span=None, max_offset_s: float = 2.0,
                    window_s: float = 60.0, tol_ms: float = TOL_MS) -> dict:
    """against_events with a practice session's note-ons, placed on src's clock by the session anchor and the OBS
    file-name time. offset_ms is then (file-name truncation, under 1 s) + (audio output latency) + (anchor error)."""
    from arsenal.performance import PerformanceStore
    store = PerformanceStore(root) if root else PerformanceStore()
    info = store.info(session)
    anchor = session_anchor(info)
    start = obs_start_epoch_ms(src)
    if start is None:
        raise ff.MediaError(f"cannot read a recording time from the name {Path(src).name!r} (OBS: "
                            f"'YYYY-MM-DD HH-MM-SS')")
    ons = [e for e in store.events(session) if e.get("kind") == "on"]
    shift_s = (anchor["epoch_ms"] - start) / 1000.0
    times = [e["t_ms"] / 1000.0 + shift_s for e in ons]
    st = Path(src).stat()
    prior = {"session": session, "anchor": anchor, "recording_start_epoch_ms": start,
             "recording_start_from": "OBS file name (local time, whole seconds: the true start is up to 1 s later)",
             "session_t0_in_file_s": round(shift_s, 3), "note_ons": len(ons),
             "mtime_epoch_ms": st.st_mtime_ns / 1e6}
    return against_events(src, times, track=track, span=span, max_offset_s=max_offset_s, window_s=window_s,
                          tol_ms=tol_ms, _prior=prior)


# =================================================================================================
# CLI: py -m arsenal.media avsync <a> [<b>] [--b-track 1] [--events session:<id> | --events times.json]
# =================================================================================================

def _load_times(spec: str) -> List[float]:
    """A JSON list of file_t seconds, or of {"t": seconds}, bare or under "times" / "events"."""
    try:
        data = json.loads(Path(spec).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ff.MediaError(f"cannot read event times from {spec}: {exc}") from None
    if isinstance(data, dict):
        data = data.get("times") or data.get("events") or []
    if not isinstance(data, list):
        raise ff.MediaError(f"{spec}: expected a list of event times")
    try:
        return [float(x["t"] if isinstance(x, dict) else x) for x in data]
    except KeyError:
        raise ff.MediaError(f"{spec}: every event object needs \"t\" (file_t seconds)") from None
    except (TypeError, ValueError) as exc:
        raise ff.MediaError(f"{spec}: event times must be numbers (file_t seconds): {exc}") from None


def cli(verb: str, argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="py -m arsenal.media avsync",
                                 description="audio/video sync: offset (ms) and drift between two recordings or two "
                                             "audio tracks, or one recording against MIDI note-ons / event times")
    ap.add_argument("a")
    ap.add_argument("b", nargs="?", help="second file (default: another track of a, see --b-track)")
    ap.add_argument("--a-track", type=int, default=0)
    ap.add_argument("--b-track", type=int, default=None, help="default 1 when b is omitted, else 0")
    ap.add_argument("--span", help="start-end on a's clock, e.g. 10:00-12:00")
    ap.add_argument("--max-offset", type=float, default=2.0, help="search +- this many seconds (default 2)")
    ap.add_argument("--window", type=float, default=None, help="drift window in s (default 30, 60 for events)")
    ap.add_argument("--events", help="session:<id> (practice log note-ons) or a JSON list of file_t seconds")
    ap.add_argument("--json", action="store_true", help="print the whole result")
    a = ap.parse_args(argv)
    span = parse_span(a.span) if a.span else None
    if a.events and a.events.startswith("session:"):
        res = against_session(a.a, a.events.split(":", 1)[1], track=a.a_track, span=span,
                              max_offset_s=a.max_offset, window_s=a.window or 60.0)
    elif a.events:
        res = against_events(a.a, _load_times(a.events), track=a.a_track, span=span, max_offset_s=a.max_offset,
                             window_s=a.window or 60.0)
    else:
        res = offset(a.a, a.b, a_track=a.a_track, b_track=a.b_track, span=span, max_offset_s=a.max_offset,
                     window_s=a.window or 30.0)
    if a.json:
        print(json.dumps(res, indent=2))
        return 0
    print(res["reading"])
    if "matched" in res:
        print(f"events {res['events_in_audio']} in the audio: {res['matched']} matched within "
              f"{res['params']['tol_ms']:g} ms, {res['unmatched']} not; by chance {res['matched_chance']} "
              f"(lift {res['match_lift']}); {res['onsets']} onsets heard")
        print("lobes: " + ", ".join(f"{c['offset_ms']:+.0f} ms (peak {c['peak']}, {c['matched']} matched)"
                                    for c in res["candidates"]))
    if res.get("spread_ms") is not None:
        print(f"window offsets spread {res['spread_ms']} ms (resid {res['resid_ms']} ms) over "
              f"{res['windows_used']}/{len(res['windows'])} windows")
    print(f"-> {res.get('receipt')}")
    return 0
