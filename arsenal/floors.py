"""arsenal.floors -- visual FLOORS: pinned assertions on pixels, so an eye is never spent on
what a histogram can catch.

WHY. In 3D/shader work an agent cannot see its own work in the loop, so every visual defect
costs a render-look cycle. Two defects found by eye on this repo's own receipts are pure
statistics: a visualizer that goes near-black in silence, and a keyboard whose glow clips to
white. Both are cheap numpy checks. This module makes them mechanical; taste stays with the
eye.

HONEST BOUNDS. These are FLOORS, not a quality score: they fail when a frame is dead, blown
out, illegible or blank, and they pass plenty of ugly frames. Contrast uses relative-luminance
approximation over sRGB values -- adequate for a floor, not a standards-compliance check.
Regions are FRACTIONS of the frame (x, y, w, h in 0..1) so a floor survives a resolution change.

Standalone: numpy + av only, no arsenal.* imports (the analysis.py rule).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import av

API = "arsenal.floors/v0"

# The Play page's canvas occupies the left ~60% of the frame; the piano-dev portrait frames
# put the keyboard in the bottom band. Fractions, because both page and viewport can change.
CANVAS_REGION = (0.0, 0.06, 0.60, 0.86)
KEYBOARD_REGION = (0.0, 0.72, 1.0, 0.24)


def load_rgb(path) -> np.ndarray:
    """Decode the first frame of an image or a video via PyAV (no Pillow dependency)."""
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            return frame.to_ndarray(format="rgb24")
    raise ValueError(f"no frame decoded from {path}")


def crop(rgb: np.ndarray, region: Optional[Tuple[float, float, float, float]]) -> np.ndarray:
    if region is None:
        return rgb
    h, w = rgb.shape[0], rgb.shape[1]
    x, y, rw, rh = region
    x0, y0 = int(np.clip(x, 0, 1) * w), int(np.clip(y, 0, 1) * h)
    x1 = int(np.clip(x + rw, 0, 1) * w) or w
    y1 = int(np.clip(y + rh, 0, 1) * h) or h
    return rgb[y0:max(y0 + 1, y1), x0:max(x0 + 1, x1)]


def luma(rgb: np.ndarray) -> np.ndarray:
    """Relative luminance, 0..1, from sRGB values (un-gamma'd values are NOT corrected here;
    a floor does not need the exact transfer function, and pretending otherwise would be worse)."""
    f = rgb[:, :, :3].astype(np.float32) / 255.0
    return 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]


# --------------------------------------------------------------------------- floors
def floor_not_dead(rgb: np.ndarray, *, region=None, min_mean: float = 0.020,
                   min_peak: float = 0.15) -> dict:
    """A frame with no content must not render as black. Caught live: the Play canvas in
    visualizer mode with silent input read as a void on the aurora-ribbons receipt."""
    lum = luma(crop(rgb, region))
    mean, peak = float(lum.mean()), float(lum.max())
    return {"floor": "not_dead", "region": region, "min_mean": min_mean, "min_peak": min_peak,
            "measured": {"mean": round(mean, 4), "peak": round(peak, 4)},
            "pass": bool(mean >= min_mean and peak >= min_peak)}


def floor_not_blown(rgb: np.ndarray, *, region=None, max_clipped: float = 0.08,
                    clip_at: int = 250) -> dict:
    """Bright objects must keep their edges. Caught live: the piano keyboard's glow clipped
    to white and dissolved the keys into haze."""
    patch = crop(rgb, region)
    clipped = float((patch[:, :, :3] >= clip_at).all(axis=2).mean())
    return {"floor": "not_blown", "region": region, "max_clipped": max_clipped,
            "measured": {"clipped_fraction": round(clipped, 4)},
            "pass": bool(clipped <= max_clipped)}


def floor_variety(rgb: np.ndarray, *, region=None, min_std: float = 0.010) -> dict:
    """A frame must contain something -- one flat colour is a rendering failure, not minimalism."""
    lum = luma(crop(rgb, region))
    std = float(lum.std())
    return {"floor": "variety", "region": region, "min_std": min_std,
            "measured": {"std": round(std, 4)}, "pass": bool(std >= min_std)}


def floor_legibility(rgb: np.ndarray, *, region=None, min_contrast: float = 4.5) -> dict:
    """Text/labels must stand off their background. Contrast is (Lhi+.05)/(Llo+.05) using the
    5th/95th luminance percentiles of the region -- percentile-based so one stray pixel cannot
    carry the verdict."""
    lum = luma(crop(rgb, region))
    lo = float(np.percentile(lum, 5))
    hi = float(np.percentile(lum, 95))
    ratio = (hi + 0.05) / (lo + 0.05)
    return {"floor": "legibility", "region": region, "min_contrast": min_contrast,
            "measured": {"contrast": round(ratio, 2)}, "pass": bool(ratio >= min_contrast)}


FLOORS = {
    "not_dead": floor_not_dead,
    "not_blown": floor_not_blown,
    "variety": floor_variety,
    "legibility": floor_legibility,
}

#: Floors belong to TARGETS, not to a single checklist: legibility on a canvas region is a
#: category error (a canvas is not text) and produced a 4.47-vs-4.5 false positive on a frame
#: that reads fine. Sample a gate on the frames it should PASS before trusting its red.
SETS = {
    "canvas": ["not_dead", "variety", "not_blown"],
    "label": ["legibility"],
    "frame": list(FLOORS),
}


def check(path, *, region=None, floors: Optional[List[str]] = None, **kw) -> dict:
    """Run the named floors (default: all) over one frame. Returns a receipt-shaped dict.

    Thresholds are filtered per floor by SIGNATURE (inspect), so passing min_contrast to a
    batch that also runs not_dead is legal -- an unknown kwarg is dropped, never raised."""
    import inspect
    rgb = load_rgb(path)
    names = floors or list(FLOORS)
    results = []
    for name in names:
        fn = FLOORS[name]
        accepted = inspect.signature(fn).parameters
        kwargs = {k: v for k, v in kw.items() if k in accepted}
        try:
            # region is ALWAYS passed: a receipt that prints a region it did not measure is
            # a label disagreeing with its own number (caught by the first evidence run).
            results.append(fn(rgb, region=region, **kwargs))
        except Exception as exc:                       # a broken floor is a FAILED floor, loudly
            results.append({"floor": name, "pass": False,
                            "error": f"{type(exc).__name__}: {exc}"})
    return {"api": API, "frame": str(path), "size": [rgb.shape[1], rgb.shape[0]],
            "region": region, "results": results,
            "pass": all(r["pass"] for r in results),
            "not_measured": ["taste, composition and intent -- these floors only catch dead, "
                             "blown, flat and illegible frames"]}


def check_many(paths, *, region=None, floors: Optional[List[str]] = None, **kw) -> List[dict]:
    return [check(p, region=region, floors=floors, **kw) for p in paths]


def sweep(directory, *, pattern: str = "*.jpg", region=None, **kw) -> List[dict]:
    """Every matching frame in a directory, sorted -- the batch form a lane or a report uses."""
    d = Path(directory)
    if not d.is_dir():
        return []
    return check_many(sorted(d.glob(pattern)), region=region, **kw)
