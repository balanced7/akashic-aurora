"""arsenal.boost -- the REFEREE: make a dark frame legible, and measure whether it has structure.

WHY THIS EXISTS. On 2026-09-18 two observers disagreed about a frame whose whole signal sat in the
bottom 5% of the luma range (std 0.0055): a vision model said "concentric rings", an eye said
"near-uniform with a faint diagonal smear". Arguing settles nothing -- what both readers need is the
SAME frame with its range stretched so the structure is visible or provably absent, plus a number
that needs no eyes at all.

boost()  is the stretched view: percentile-stretch luma to the full 0..1 range and return it as an
         image. A frame whose content hides in the dark becomes readable; a frame with no content
         becomes an empty field, and that emptiness is itself the answer.
annuli() is the number: the mean luma of concentric annuli, centre to edge. A MONOTONE fall is a
         glow or a gradient; a rise AWAY from the centre followed by a fall is radial banding --
         rings, a mandala, an iris. radial_summary() adds the `banded` verdict and a reason in
         words, because a number that cannot explain itself is an absence rendering as normal.

These are FLOORS' cousin: floors say what a frame is NOT (dead, blown, flat, illegible); the
referee says what a frame IS (a glow, a banded figure, or nothing). Neither is taste -- both are
numpy over luma, reproducible and free.

Standalone-ish: depends on arsenal.floors (which is numpy+av only), adds no new dependency.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from .floors import luma

API = "arsenal.boost/v0"


def boost(rgb: np.ndarray, lo_pct: float = 1, hi_pct: float = 99) -> np.ndarray:
    """Percentile-stretch the luma to the full range and return it as a uint8 RGB image. The 1/99
    percentiles are the clamp points so one stray hot pixel cannot flatten the stretch; the result
    preserves the input shape and is meant for an eye, not for a metric (the metric is annuli)."""
    lum = luma(rgb)
    lo = float(np.percentile(lum, lo_pct))
    hi = float(np.percentile(lum, hi_pct))
    span = max(hi - lo, 1e-6)
    stretched = np.clip((lum - lo) / span, 0.0, 1.0)
    return (np.dstack([stretched, stretched, stretched]) * 255).astype(np.uint8)


def annuli(rgb: np.ndarray, bands: int = 6, center: Optional[Tuple[float, float]] = None) -> List[float]:
    """Mean luma of `bands` concentric annuli, centre to edge, each one sixth of the normalised
    radius. `center` is (x, y) in pixels; default is the frame centre. Returns a list of means, or
    None entries for an empty annulus (which only happens for a degenerate image)."""
    lum = luma(rgb)
    h, w = lum.shape
    cx = w / 2 if center is None else float(center[0])
    cy = h / 2 if center is None else float(center[1])
    yy, xx = np.mgrid[0:h, 0:w]
    rr = np.sqrt(((yy - cy) / (h / 2)) ** 2 + ((xx - cx) / (w / 2)) ** 2)
    width = 1.0 / bands
    out: List[float] = []
    for i in range(bands):
        band = (rr >= i * width) & (rr < (i + 1) * width)
        out.append(round(float(lum[band].mean()), 6) if band.any() else None)
    return out


def radial_summary(rgb: np.ndarray, bands: int = 6,
                   center: Optional[Tuple[float, float]] = None) -> dict:
    """The verdict with the numbers beside it. `banded` is True when brightness RISES away from the
    centre before falling -- the signature of a ring, a mandala or an iris, as opposed to a glow
    (monotone fall) or a flat field. The reason is a sentence, never a bare flag."""
    a = annuli(rgb, bands=bands, center=center)
    non_monotone = any((a[i] or 0) > (a[i - 1] or 0) + 1e-9 for i in range(1, len(a)))
    if non_monotone:
        reason = "radial banding: brightness rises away from the centre and then falls"
    elif all(abs(v - a[0]) < 1e-6 for v in a):
        reason = "flat: no radial structure at all"
    else:
        reason = "a glow or gradient: monotone fall away from the centre"
    return {"api": API, "annuli": a, "bands": bands, "banded": bool(non_monotone), "reason": reason}
