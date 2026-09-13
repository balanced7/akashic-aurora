"""arsenal.analysis -- PyAV probe, hardware-decode evidence, and audio feature extraction.

Kernel API v0. See arsenal/FIRST-LIGHT-SPEC.md, section "analysis.py (PyAV)".

This module is standalone: it does not import any other arsenal.* module, so it works
whether or not arsenal/__init__.py exists yet.
"""
from __future__ import annotations

import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

import av
from av.codec.hwaccel import HWAccel

# state/arsenal/ lives next to this file's package, not at the process cwd, so this module
# behaves the same whether it's run from E:\AI-Setup or imported from anywhere else.
_REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_ROOT = _REPO_ROOT / "state" / "arsenal"
CACHE_DIR = STATE_ROOT / "cache"

# ffmpeg's own "unspecified" sentinel for each colour enum (libavutil pixfmt.h). PyAV hands
# these back as the raw ints from the bitstream/container; only the sentinel (or a bare
# None, which some codec contexts return) means "we don't know" -- everything else is a
# real value read off the file and is passed through untouched, never renamed or guessed.
_COLOR_RANGE_UNSPECIFIED = 0
_COLOR_UNSPECIFIED = 2  # shared by primaries, transfer (trc) and matrix (colorspace)

# The fixed set of ffmpeg pixel-format names that name an opaque GPU-resident surface
# (av_hwdevice_get_type_name-adjacent). Any other format PyAV reports (yuv420p, nv12 that
# was downloaded to system memory, ...) means the decode is software.
_HW_PIX_FMTS = {
    "d3d11", "d3d12", "cuda", "vaapi", "dxva2_vld", "qsv",
    "videotoolbox", "vulkan", "drm_prime", "mediacodec", "opencl", "vdpau",
}

HOP_TICKS = 480
WINDOW_TICKS = 2048
FEATURE_SAMPLE_RATE = 48000
FEATURE_NAMES = ["rms", "bass", "mid", "high", "flux"]
BANDS_HZ = {"bass": (20.0, 150.0), "mid": (150.0, 2000.0), "high": (2000.0, 16000.0)}
_LOG_EPS = 1e-12


def _format_tb(frac) -> str:
    """A Fraction (or anything Fraction() accepts) as an exact 'num/den' string."""
    frac = Fraction(frac)
    return f"{frac.numerator}/{frac.denominator}"


def _color_field(value, unspecified: int) -> Optional[int]:
    """Pass a real PyAV colour int through as-is; the documented 'unspecified' sentinel
    (or PyAV itself returning None) becomes None. Never a guessed/default value."""
    if value is None or value == unspecified:
        return None
    return value


def _computed_with() -> dict:
    major, minor, micro = av.library_versions["libavcodec"]
    return {
        "engine": "ffmpeg",
        "binding": f"PyAV {av.__version__}",
        "libavcodec": f"{major}.{minor}.{micro}",
    }


# ---------------------------------------------------------------------------
# probe
# ---------------------------------------------------------------------------

def probe(path: str) -> dict:
    """Read container/stream/codec metadata with PyAV's real attributes.

    Colour metadata (primaries/transfer/matrix/range) is None whenever the file itself
    doesn't declare it -- it is never guessed from pix_fmt, codec, or anything else.
    """
    abspath = os.path.abspath(path)
    size = os.path.getsize(abspath)

    with av.open(abspath) as container:
        duration = {
            "ticks": container.duration,  # int, in av.time_base units, or None if unknown
            "timebase": _format_tb(Fraction(1, av.time_base)),
        }

        video = None
        if container.streams.video:
            vs = container.streams.video[0]
            cc = vs.codec_context
            video = {
                "index": vs.index,
                "codec": cc.name,
                "width": cc.width,
                "height": cc.height,
                "pix_fmt": cc.format.name if cc.format else None,
                "rate": _format_tb(vs.average_rate) if vs.average_rate else None,
                "timebase": _format_tb(vs.time_base),
                "primaries": _color_field(cc.color_primaries, _COLOR_UNSPECIFIED),
                "transfer": _color_field(cc.color_trc, _COLOR_UNSPECIFIED),
                "matrix": _color_field(cc.colorspace, _COLOR_UNSPECIFIED),
                "range": _color_field(cc.color_range, _COLOR_RANGE_UNSPECIFIED),
            }

        audio = None
        if container.streams.audio:
            aus = container.streams.audio[0]
            cc = aus.codec_context
            audio = {
                "index": aus.index,
                "codec": cc.name,
                "rate": cc.rate,
                "channels": cc.channels,
                "layout": cc.layout.name if cc.layout else None,
                "timebase": _format_tb(aus.time_base),
            }

        return {
            "api": "arsenal.probe/v0",
            "path": abspath,
            "size": size,
            "container": container.format.name,
            "duration": duration,
            "video": video,
            "audio": audio,
        }


# ---------------------------------------------------------------------------
# hw_decode_evidence
# ---------------------------------------------------------------------------

def hw_decode_evidence(path: str, devices=("d3d12va", "d3d11va"), frames: int = 30) -> dict:
    """Decode a few frames per device with PyAV 17's real hwaccel API and report the frame
    format PyAV actually returns. Never raises: each device's failure is recorded on its
    own entry instead.
    """
    abspath = os.path.abspath(path)
    tried = []
    ok_device = None

    for device in devices:
        entry = {"device": device, "ok": False, "frames": 0, "frame_format": None, "error": None}
        try:
            # is_hw_owned=True keeps the decoded frame as the opaque GPU surface, so its
            # format name IS the evidence (e.g. "d3d11"/"d3d12"). PyAV's default
            # (is_hw_owned=False) auto-downloads every frame to a system-memory format
            # (nv12, for these devices) before we ever see it, which erases the signal.
            hwaccel = HWAccel(device_type=device, allow_software_fallback=True, is_hw_owned=True)
            with av.open(abspath, hwaccel=hwaccel) as container:
                if not container.streams.video:
                    entry["error"] = "no video stream"
                else:
                    vstream = container.streams.video[0]
                    count = 0
                    frame_format = None
                    for frame in container.decode(vstream):
                        count += 1
                        frame_format = frame.format.name
                        if count >= frames:
                            break
                    entry["frames"] = count
                    entry["frame_format"] = frame_format
                    entry["ok"] = frame_format in _HW_PIX_FMTS
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: never raise, ever
            entry["error"] = f"{type(exc).__name__}: {exc}"
        tried.append(entry)
        if entry["ok"] and ok_device is None:
            ok_device = device

    return {"tried": tried, "ok_device": ok_device}


# ---------------------------------------------------------------------------
# audio_features
# ---------------------------------------------------------------------------

def _cache_path(abspath: str, size: int, mtime_ns: int) -> Path:
    key = hashlib.sha1(f"{abspath}|{size}|{mtime_ns}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.json"


def _write_cache(cache_file: Path, result: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = cache_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(result), encoding="utf-8")
    tmp.replace(cache_file)  # atomic on both POSIX and Windows


def _no_audio_result(abspath: str, size: int, mtime_ns: int) -> dict:
    return {
        "api": "arsenal.features/v0",
        "clock": "media",
        "epoch": 0,
        "timebase": _format_tb(Fraction(1, FEATURE_SAMPLE_RATE)),
        "hop_ticks": HOP_TICKS,
        "window_ticks": WINDOW_TICKS,
        "start_ticks": 0,
        "names": FEATURE_NAMES,
        "frames": [],
        "no_audio": True,
        "normalization": "per-band p5..p99 of dB mapped to 0..1, clipped",
        "source": {
            "path": abspath, "size": size, "mtime": mtime_ns,
            "audio_stream": None, "sample_rate_in": None, "channels_in": None,
        },
        "computed_with": _computed_with(),
    }


def audio_features(path: str, *, progress: Optional[Callable[[float], None]] = None) -> dict:
    """Mono 48kHz band/rms/flux features, hop 480 / window 2048 / Hann, cached on disk.

    start_ticks is the first audio frame's pts rescaled EXACTLY (fractions.Fraction, never
    a float) to a 1/48000 timebase.
    """
    abspath = os.path.abspath(path)
    st = os.stat(abspath)
    size, mtime_ns = st.st_size, st.st_mtime_ns

    cache_file = _cache_path(abspath, size, mtime_ns)
    if cache_file.exists():
        if progress:
            progress(1.0)
        return json.loads(cache_file.read_text(encoding="utf-8"))

    # Throttle progress callbacks to ~0.5% steps so a long clip doesn't fire thousands of
    # Python-level calls for no benefit.
    last_bucket = [-1]

    def report(value: float) -> None:
        if progress is None:
            return
        bucket = int(value * 200)
        if bucket != last_bucket[0]:
            last_bucket[0] = bucket
            progress(min(1.0, max(0.0, value)))

    with av.open(abspath) as container:
        if not container.streams.audio:
            result = _no_audio_result(abspath, size, mtime_ns)
            _write_cache(cache_file, result)
            if progress:
                progress(1.0)
            return result

        astream = container.streams.audio[0]
        sample_rate_in = astream.codec_context.rate
        channels_in = astream.codec_context.channels
        total_duration_s = (
            float(Fraction(container.duration, av.time_base)) if container.duration else None
        )

        resampler = av.AudioResampler(format="flt", layout="mono", rate=FEATURE_SAMPLE_RATE)

        chunks = []
        first_pts, first_tb = None, None
        for frame in container.decode(astream):
            if first_pts is None:
                first_pts = frame.pts if frame.pts is not None else 0
                first_tb = frame.time_base
            for out in resampler.resample(frame):
                arr = out.to_ndarray()
                if arr.size:
                    chunks.append(arr.reshape(-1))
            if total_duration_s and frame.pts is not None:
                t = float(frame.pts * frame.time_base)
                report(0.5 * min(1.0, t / total_duration_s))
        for out in resampler.resample(None):  # flush swresample's internal buffer
            arr = out.to_ndarray()
            if arr.size:
                chunks.append(arr.reshape(-1))

        samples = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)

        if first_pts is None:
            start_ticks = 0
        else:
            # Exact rational rescale to 1/48000 ticks -- Fraction arithmetic throughout,
            # round() on a Fraction is exact (no float ever enters this computation).
            start_ticks = round(Fraction(first_pts) * first_tb * FEATURE_SAMPLE_RATE)

        rows = _extract_features(samples, lambda v: report(0.5 + 0.5 * v))

        result = {
            "api": "arsenal.features/v0",
            "clock": "media",
            "epoch": 0,
            "timebase": _format_tb(Fraction(1, FEATURE_SAMPLE_RATE)),
            "hop_ticks": HOP_TICKS,
            "window_ticks": WINDOW_TICKS,
            "start_ticks": start_ticks,
            "names": FEATURE_NAMES,
            "frames": rows,
            "normalization": "per-band p5..p99 of dB mapped to 0..1, clipped",
            "source": {
                "path": abspath, "size": size, "mtime": mtime_ns,
                "audio_stream": astream.index,
                "sample_rate_in": sample_rate_in, "channels_in": channels_in,
            },
            "computed_with": _computed_with(),
        }

    _write_cache(cache_file, result)
    if progress:
        progress(1.0)
    return result


def _normalize_db(db: np.ndarray) -> np.ndarray:
    """p5..p99 of dB -> 0..1, clipped. A flat/silent feature (p99==p5) normalises to 0."""
    p5, p99 = np.percentile(db, [5, 99])
    span = p99 - p5
    if span < 1e-9:
        return np.zeros_like(db)
    return np.clip((db - p5) / span, 0.0, 1.0)


def _extract_features(samples: np.ndarray, progress: Callable[[float], None]) -> list:
    """Vectorised hop/window framing + band power/rms/flux, chunked so a one-hour clip
    (~360k frames) never materialises the full windowed matrix (which alone would be
    several GB) -- only one chunk of it at a time.
    """
    n = samples.shape[0]
    if n < WINDOW_TICKS:
        return []

    n_frames = (n - WINDOW_TICKS) // HOP_TICKS + 1
    hann = np.hanning(WINDOW_TICKS).astype(np.float32)
    freqs = np.fft.rfftfreq(WINDOW_TICKS, d=1.0 / FEATURE_SAMPLE_RATE)
    band_masks = {name: (freqs >= lo) & (freqs < hi) for name, (lo, hi) in BANDS_HZ.items()}

    rms_db = np.empty(n_frames, dtype=np.float64)
    band_db = {name: np.empty(n_frames, dtype=np.float64) for name in BANDS_HZ}
    flux_db = np.empty(n_frames, dtype=np.float64)

    # A view over every possible window start (stride 1); selecting every HOP-th row below
    # copies only the chunk being processed, not the whole thing.
    all_windows = sliding_window_view(samples, WINDOW_TICKS)
    prev_last_mag = None  # magnitude spectrum of the frame just before this chunk

    chunk_frames = 4096
    for start in range(0, n_frames, chunk_frames):
        end = min(start + chunk_frames, n_frames)
        raw = all_windows[np.arange(start, end) * HOP_TICKS]  # (chunk, WINDOW_TICKS)

        rms = np.sqrt(np.mean(raw.astype(np.float64) ** 2, axis=1))
        rms_db[start:end] = 20.0 * np.log10(rms + _LOG_EPS)

        mag = np.abs(np.fft.rfft(raw * hann, axis=1))  # (chunk, n_bins)
        for name, mask in band_masks.items():
            power = np.sum(mag[:, mask].astype(np.float64) ** 2, axis=1)
            band_db[name][start:end] = 10.0 * np.log10(power + _LOG_EPS)

        # Positive spectral flux against the previous frame; the very first frame of the
        # whole clip has no predecessor, so it diffs against itself (-> flux 0).
        ref_row = prev_last_mag if prev_last_mag is not None else mag[0:1]
        shifted = np.vstack([ref_row, mag[:-1]])
        flux = np.sum(np.clip(mag - shifted, 0.0, None), axis=1)
        flux_db[start:end] = 20.0 * np.log10(flux.astype(np.float64) + _LOG_EPS)
        prev_last_mag = mag[-1:].copy()

        progress(end / n_frames)

    matrix = np.stack(
        [
            _normalize_db(rms_db),
            _normalize_db(band_db["bass"]),
            _normalize_db(band_db["mid"]),
            _normalize_db(band_db["high"]),
            _normalize_db(flux_db),
        ],
        axis=1,
    )
    return np.round(matrix, 4).tolist()
