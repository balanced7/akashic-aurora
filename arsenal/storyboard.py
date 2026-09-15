"""arsenal.storyboard -- dynamic capture: score a video's motion, segment it, sheet it.

WHY THIS EXISTS. A single screenshot cannot judge a time-driven visual (a slow procedural
preset reads as a black frame), and a full video ingest costs what a *preview* should not.
So: score consecutive frames cheaply, segment the score curve into SETTLED runs and
TRANSITIONS -- each transition carrying its own length -- pick representatives, de-duplicate
near-identical frames, and write a contact sheet plus a manifest that declares its own
thresholds and denominators. The sheet is a SAMPLE, never the video; the manifest says what
fraction of the take it represents.

Reader note: a seat with vision reads the SHEET (and the picked frames). The low-res proxy is
for humans and for future video-capable readers.

Standalone by the same rule as analysis.py: numpy + av only, no arsenal.* imports.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

import numpy as np

import av

_REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_ROOT = _REPO_ROOT / "state" / "arsenal"
API = "arsenal.storyboard/v0"

# Defaults are DECLARED in every manifest (they are the sampling rule, not hidden knobs).
DEFAULT_FPS = 5.0
DEFAULT_WIDTH = 480
DEFAULT_LOW = 0.020          # below this (for settle_frames) a stretch is SETTLED
DEFAULT_HIGH = 0.080         # above this a frame is inside a TRANSITION
DEFAULT_SETTLE_FRAMES = 3
DEFAULT_MAX_HAMMING = 6      # dHash distance at or under which two frames are the same moment
DEFAULT_MAX_PALETTE = 0.06   # ...and the palette must agree too (dHash is blind on flat frames)


# --------------------------------------------------------------------------- signatures
def signature(rgb: np.ndarray) -> tuple:
    """(luma, histogram) for one RGB uint8 frame, reduced to a small fixed shape.

    Luma is a strided downscale (cheap, aspect-preserving enough for a difference signal);
    the histogram is per-channel, 8 bins, L1-normalised, so a global brightness shift does
    not read as a cut the way raw pixel difference would."""
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError("signature() wants an RGB uint8 frame")
    h, w = rgb.shape[0], rgb.shape[1]
    step_y = max(1, h // 32)
    step_x = max(1, w // 32)
    small = rgb[::step_y, ::step_x, :3].astype(np.float32)
    luma = (0.299 * small[:, :, 0] + 0.587 * small[:, :, 1] + 0.114 * small[:, :, 2]) / 255.0
    hist = np.concatenate([
        np.histogram(small[:, :, c], bins=8, range=(0, 256))[0].astype(np.float32)
        for c in range(3)
    ])
    total = float(hist.sum()) or 1.0
    return luma, hist / total


def change_score(prev: tuple, cur: tuple) -> float:
    """A single 0..1-ish change number between two signatures: half pixel motion, half
    distribution shift. Both halves are bounded, so the score is comparable across videos."""
    p_luma, p_hist = prev
    c_luma, c_hist = cur
    n = min(p_luma.shape[0], c_luma.shape[0]), min(p_luma.shape[1], c_luma.shape[1])
    mad = float(np.abs(p_luma[: n[0], : n[1]] - c_luma[: n[0], : n[1]]).mean())
    l1 = float(np.abs(p_hist - c_hist).sum()) / 2.0
    return round(0.5 * mad + 0.5 * l1, 6)


def scores_for(sigs: List[tuple]) -> List[float]:
    """One score per frame after the first; scores[i] describes the step INTO frame i+1."""
    return [change_score(sigs[i - 1], sigs[i]) for i in range(1, len(sigs))]


# --------------------------------------------------------------------------- segmentation
@dataclass
class Segment:
    kind: str               # "settled" | "transition"
    start_s: float
    end_s: float
    duration_ms: int
    peak_score: float
    frames: int

    def as_dict(self) -> dict:
        return asdict(self)


def segment(scores: List[float], times: List[float], *, low: float = DEFAULT_LOW,
            high: float = DEFAULT_HIGH, settle_frames: int = DEFAULT_SETTLE_FRAMES) -> List[Segment]:
    """Hysteresis segmentation of the score curve.

    A run of frames at or below ``low`` (at least ``settle_frames`` long) is SETTLED; a run
    whose peak reaches ``high`` is a TRANSITION and it ends only when the curve has been
    quiet for ``settle_frames`` frames -- so a slow fade registers as ONE long transition
    rather than two hundred tiny ones. Every transition reports its own length in
    milliseconds, which is the tag this artefact exists to carry.
    """
    if not scores:
        return []
    segs: List[Segment] = []
    i, n = 0, len(scores)
    quiet_run = 0
    cur_kind = "settled" if scores[0] <= low else "transition"
    cur_start = 0
    for i in range(n):
        s = scores[i]
        if s <= low:
            quiet_run += 1
        else:
            quiet_run = 0
        if cur_kind == "transition" and quiet_run >= settle_frames:
            segs.append(_mk("transition", cur_start, i - quiet_run + 1, scores, times))
            cur_kind, cur_start = "settled", i - quiet_run + 1
        elif cur_kind == "settled" and s > low and quiet_run == 0:
            # a rising edge opens a transition only if it will reach high; open, then judge
            if any(x >= high for x in scores[i:i + settle_frames + 1]) or s >= high:
                segs.append(_mk("settled", cur_start, i - 1, scores, times))
                cur_kind, cur_start = "transition", i
    segs.append(_mk(cur_kind, cur_start, n - 1, scores, times))
    return [s for s in segs if s.duration_ms >= 0]


def _mk(kind: str, a: int, b: int, scores: List[float], times: List[float]) -> Segment:
    b = max(a, b)
    window = scores[a:b + 1] or [0.0]
    t0 = times[a]
    t1 = times[min(b + 1, len(times) - 1)]
    return Segment(kind=kind, start_s=round(t0, 3), end_s=round(t1, 3),
                   duration_ms=int(round((t1 - t0) * 1000)), peak_score=round(max(window), 6),
                   frames=b - a + 1)


def pick_representatives(segs: List[Segment], scores: List[float], times: List[float]) -> List[dict]:
    """One frame per settled run (its middle) and one per transition (its peak)."""
    picks: List[dict] = []
    for seg in segs:
        a_idx = _index_at(times, seg.start_s)
        b_idx = min(_index_at(times, seg.end_s), len(scores) - 1)
        if seg.kind == "transition":
            window = scores[a_idx:b_idx + 1] or [0.0]
            peak = a_idx + int(np.argmax(window))
        else:
            peak = (a_idx + b_idx) // 2
        picks.append({"frame_index": peak, "t_s": round(times[min(peak, len(times) - 1)], 3),
                      "kind": seg.kind, "score": round(scores[min(peak, len(scores) - 1)], 6),
                      "segment_ms": seg.duration_ms})
    return picks


def _index_at(times: List[float], t: float) -> int:
    if not times:
        return 0
    return int(np.clip(np.searchsorted(times, t, side="left"), 0, len(times) - 1))


# --------------------------------------------------------------------------- dedupe
def dhash(rgb: np.ndarray) -> int:
    """64-bit difference hash: robust to scale and small brightness shifts, cheap to compare."""
    h, w = rgb.shape[0], rgb.shape[1]
    ys = np.linspace(0, h - 1, 9).astype(int)
    xs = np.linspace(0, w - 1, 9).astype(int)
    small = rgb[np.ix_(ys, xs)][:, :, :3].astype(np.float32)
    luma = 0.299 * small[:, :, 0] + 0.587 * small[:, :, 1] + 0.114 * small[:, :, 2]
    bits = (luma[:, 1:] > luma[:, :-1]).flatten()
    out = 0
    for b in bits:
        out = (out << 1) | int(bool(b))
    return out


def hamming(a: int, b: int) -> int:
    return int(bin(a ^ b).count("1"))


def palette(rgb: np.ndarray) -> tuple:
    """Normalised mean RGB (0..1) -- the colour half of 'is this the same moment'.

    Required because dHash encodes GRADIENT DIRECTION, so a flat frame hashes the same no
    matter its colour: solid red and solid blue are hash-identical. A pin caught that on the
    first run (see tests/test_storyboard.py::test_dedupe_*), and the fix is to demand that
    structure AND palette agree before two frames may be called the same moment."""
    small = rgb[::max(1, rgb.shape[0] // 32), ::max(1, rgb.shape[1] // 32), :3].astype(np.float32)
    return tuple(round(float(c) / 255.0, 4) for c in small.reshape(-1, 3).mean(axis=0))


def palette_delta(a: tuple, b: tuple) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


def dedupe(picks: List[dict], hashes: dict, palettes: dict,
           *, max_hamming: int = DEFAULT_MAX_HAMMING,
           max_palette: float = DEFAULT_MAX_PALETTE) -> List[dict]:
    """Drop picks whose frame is visually the same moment as one already kept: same structure
    (dHash within max_hamming) AND same palette (max channel delta within max_palette)."""
    kept: List[dict] = []
    for p in picks:
        idx = p["frame_index"]
        h, pal = hashes.get(idx), palettes.get(idx)
        if h is None or pal is None:
            continue
        same = any(
            hamming(h, hashes[k["frame_index"]]) <= max_hamming
            and palette_delta(pal, palettes[k["frame_index"]]) <= max_palette
            for k in kept if hashes.get(k["frame_index"]) is not None
        )
        if not same:
            kept.append(p)
    return kept


# --------------------------------------------------------------------------- IO
def _write_png(rgb: np.ndarray, path: Path) -> bool:
    """PNG out via libavcodec's own encoder -- no Pillow dependency. Returns success."""
    try:
        with av.open(str(path), mode="w", format="image2") as out:
            stream = out.add_stream("png", rate=1)
            stream.width, stream.height = rgb.shape[1], rgb.shape[0]
            stream.pix_fmt = "rgb24"
            frame = av.VideoFrame.from_ndarray(np.ascontiguousarray(rgb), format="rgb24")
            for packet in stream.encode(frame):
                out.mux(packet)
            for packet in stream.encode():
                out.mux(packet)
        return True
    except Exception:
        return False


def _contact_sheet(frames: List[np.ndarray], cols: int = 3) -> Optional[np.ndarray]:
    """A labelled-by-position mosaic: every kept frame at the same size, row by row."""
    if not frames:
        return None
    th, tw = 180, 320
    rows = (len(frames) + cols - 1) // cols
    sheet = np.zeros((rows * th, cols * tw, 3), dtype=np.uint8)
    for i, f in enumerate(frames):
        ys = np.linspace(0, f.shape[0] - 1, th).astype(int)
        xs = np.linspace(0, f.shape[1] - 1, tw).astype(int)
        thumb = f[np.ix_(ys, xs)][:, :, :3]
        r, c = divmod(i, cols)
        sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = thumb
    return sheet


def analyse(path: str, *, fps: float = DEFAULT_FPS, width: int = DEFAULT_WIDTH,
            low: float = DEFAULT_LOW, high: float = DEFAULT_HIGH,
            settle_frames: int = DEFAULT_SETTLE_FRAMES,
            max_hamming: int = DEFAULT_MAX_HAMMING) -> dict:
    """Decode cheap, score, segment, pick, de-dup. Returns the manifest (no files written)."""
    times: List[float] = []
    sigs: List[tuple] = []
    frames_at_pick: dict = {}
    palettes_at_pick: dict = {}
    src = Path(path)
    with av.open(str(src)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        rate = float(stream.average_rate or 25)
        stride = max(1, int(round(rate / max(0.5, fps))))
        for i, frame in enumerate(container.decode(stream)):
            if i % stride:
                continue
            rgb = frame.to_ndarray(format="rgb24")
            if rgb.shape[1] > width:                      # keep the analysis cheap
                xs = np.linspace(0, rgb.shape[1] - 1, width).astype(int)
                rgb = rgb[:, xs]
            times.append(float(frame.time or (i / rate)))
            sigs.append(signature(rgb))
            frames_at_pick[i // stride] = dhash(rgb)
            palettes_at_pick[i // stride] = palette(rgb)
    scores = scores_for(sigs)
    segs = segment(scores, times[1:], low=low, high=high, settle_frames=settle_frames)
    picks = pick_representatives(segs, scores, times[1:])
    kept = dedupe(picks, frames_at_pick, palettes_at_pick, max_hamming=max_hamming)
    return {
        "api": API, "source": str(src), "source_bytes": src.stat().st_size if src.exists() else None,
        "sampling": {"fps": fps, "width": width, "low": low, "high": high,
                     "settle_frames": settle_frames, "max_hamming": max_hamming},
        "frames_examined": len(sigs), "scores": scores, "segments": [s.as_dict() for s in segs],
        "picks": kept, "picks_before_dedupe": len(picks),
        "transitions": sum(1 for s in segs if s.kind == "transition"),
        "settled": sum(1 for s in segs if s.kind == "settled"),
        "not_measured": [
            "audio: this is a visual change score only",
            "a strobe can produce false transitions; a slow fade registers as one long transition",
            "the sheet is a SAMPLE of the take -- see picks/total for the fraction it represents",
        ],
    }


def storyboard(path: str, *, fps: float = DEFAULT_FPS, width: int = DEFAULT_WIDTH,
               out_dir: Optional[str] = None, write_frames: bool = False, **kw) -> dict:
    """analyse() + files: <out>/storyboard.png (contact sheet), <out>/storyboard.json,
    and optionally one PNG per kept pick (write_frames=True)."""
    manifest = analyse(path, fps=fps, width=width, **kw)
    out = Path(out_dir) if out_dir else STATE_ROOT / "storyboards" / Path(path).stem
    out.mkdir(parents=True, exist_ok=True)
    manifest["out_dir"] = str(out)

    keep = {p["frame_index"] for p in manifest["picks"]}
    thumbs: List[np.ndarray] = []
    if keep:
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stride = max(1, int(round(float(stream.average_rate or 25) / max(0.5, fps))))
            for i, frame in enumerate(container.decode(stream)):
                if i % stride or (i // stride) not in keep:
                    continue
                rgb = frame.to_ndarray(format="rgb24")
                thumbs.append(rgb)
                if write_frames:
                    _write_png(rgb, out / f"frame-{i // stride:05d}.png")
    sheet = _contact_sheet(thumbs)
    manifest["sheet_written"] = bool(sheet is not None and _write_png(sheet, out / "storyboard.png"))
    (out / "storyboard.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(out / "storyboard.json")
    return manifest
