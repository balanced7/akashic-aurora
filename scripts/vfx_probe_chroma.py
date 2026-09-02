#!/usr/bin/env python3
"""Probe: chroma-aware structured metrics over real bench PNGs.

This is the self-test of deepseek VFX Report Proposal A: structured render output.
The previous probe (vfx_probe_metrics.py) was luminance-only and proved blind to hue --
Michelson contrast identical to sixteen digits across three visibly different images.
THIS probe adds chroma metrics and a per-pair delta to answer the question the first
one could not: "did the change register, and in what direction?"

Run: py scripts/vfx_probe_chroma.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# Use Pillow -- the hand-rolled PNG decoder in the original probe handled only filter 0
# and every canvas.toDataURL image here is filter 2 (Up) on every row. Pillow was installed
# the whole time. The lesson is filed; we use Pillow.
try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Pillow + numpy required: py -m pip install Pillow numpy", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parent.parent
SNAPS = REPO / "design" / "vfx-snaps"


def load_png(path):
    """Return (w, h, pixels_rgba) as numpy array, or None."""
    try:
        im = Image.open(path).convert("RGBA")
        return im.width, im.height, np.array(im)
    except Exception as e:
        return None, None, None


# ---- luminance (BT.601) for backward comparison ----
def luminance(r, g, b):
    return 0.299 * r + 0.587 * g + 0.114 * b


# ---- CHROMA METRICS (the ones the first probe lacked) ----
def chroma_metrics(px):
    """Return {mean_hue_deg, mean_saturation, mean_chroma} for non-transparent pixels."""
    if px is None or px.size == 0:
        return {}
    r, g, b, a = px[:,:,0].astype(float), px[:,:,1].astype(float), px[:,:,2].astype(float), px[:,:,3]
    mask = a > 64
    if mask.sum() < 100:
        return {}
    r, g, b = r[mask], g[mask], b[mask]
    # Perceptual chroma: C = sqrt((R-G)^2 + (G-B)^2 + (B-R)^2) / sqrt(2)
    chroma = np.sqrt((r - g)**2 + (g - b)**2 + (b - r)**2) / np.sqrt(2)
    # Hue: atan2 of (b - r) vs (r - 2g + b) -- the opponent-colour hue
    # Simpler: use the standard RGB-to-HSL hue approximation
    c_max = np.maximum(np.maximum(r, g), b)
    c_min = np.minimum(np.minimum(r, g), b)
    delta = c_max - c_min
    saturation = np.where(c_max > 0, delta / c_max, 0.0)
    # Hue in degrees, 0-360
    hue = np.zeros_like(r)
    # R is max
    mask_r = (c_max == r) & (delta > 0)
    hue[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6)
    # G is max
    mask_g = (c_max == g) & (delta > 0)
    hue[mask_g] = 60.0 * (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2)
    # B is max
    mask_b = (c_max == b) & (delta > 0)
    hue[mask_b] = 60.0 * (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4)

    return {
        "mean_hue_deg": round(float(np.mean(hue)), 1) if hue.any() else None,
        "circular_mean_hue_deg": round(circular_mean_hue(hue), 1) if hue.any() else None,
        "mean_saturation": round(float(np.mean(saturation)), 4),
        "mean_chroma": round(float(np.mean(chroma)), 2),
        "chroma_std": round(float(np.std(chroma)), 2),
    }


def circular_mean_hue(hue_deg):
    """Circular mean of hue angles in degrees."""
    rad = np.deg2rad(hue_deg)
    s, c = np.sin(rad).mean(), np.cos(rad).mean()
    return float(np.rad2deg(np.arctan2(s, c)) % 360)


# ---- luminance metrics (from the original probe, for comparison) ----
def contrast_ratio(px):
    """Michelson contrast on 5th/95th percentiles, BT.601 luma."""
    if px is None:
        return None
    r, g, b, a = px[:,:,0], px[:,:,1], px[:,:,2], px[:,:,3]
    mask = a > 64
    if mask.sum() < 100:
        return None
    lums = sorted(luminance(r[mask], g[mask], b[mask]))
    n = len(lums)
    lo, hi = lums[int(n * 0.05)], lums[int(n * 0.95)]
    if hi + lo < 1:
        return 0.0
    return round((hi - lo) / (hi + lo), 4)


def spatial_variance(px, w, h):
    """Mean abs diff between adjacent pixels, luma."""
    if px is None or w < 2:
        return None
    r, g, b, a = px[:,:,0].astype(float), px[:,:,1].astype(float), px[:,:,2].astype(float), px[:,:,3]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    # right neighbors
    diffs = np.abs(luma[:, :-1] - luma[:, 1:])
    # only where BOTH pixels are non-transparent
    valid = (a[:, :-1] > 64) & (a[:, 1:] > 64)
    if valid.sum() == 0:
        return None
    return round(float(diffs[valid].mean()), 4)


def bloom_fraction(px, threshold=0.9):
    """Fraction of non-transparent pixels above threshold brightness."""
    if px is None:
        return None
    r, g, b, a = px[:,:,0].astype(float), px[:,:,1].astype(float), px[:,:,2].astype(float), px[:,:,3]
    mask = a > 64
    if mask.sum() == 0:
        return None
    luma = luminance(r[mask], g[mask], b[mask])
    return round(float((luma / 255.0 >= threshold).mean()), 5)


def luminance_histogram(px, buckets=16):
    """16-bucket luminance histogram, normalised."""
    if px is None:
        return None
    r, g, b, a = px[:,:,0].astype(float), px[:,:,1].astype(float), px[:,:,2].astype(float), px[:,:,3]
    mask = a > 64
    if mask.sum() == 0:
        return None
    luma = luminance(r[mask], g[mask], b[mask])
    hist, _ = np.histogram(luma, bins=buckets, range=(0, 255))
    total = hist.sum()
    if total == 0:
        return None
    return [round(float(h / total), 4) for h in hist]


def chroma_histogram(px, buckets=16):
    """16-bucket chroma histogram (the axis the first probe was blind to)."""
    if px is None:
        return None
    r, g, b, a = px[:,:,0].astype(float), px[:,:,1].astype(float), px[:,:,2].astype(float), px[:,:,3]
    mask = a > 64
    if mask.sum() == 0:
        return None
    chroma = np.sqrt((r[mask] - g[mask])**2 + (g[mask] - b[mask])**2 + (b[mask] - r[mask])**2) / np.sqrt(2)
    hist, _ = np.histogram(chroma, bins=buckets, range=(0, 255))
    total = hist.sum()
    if total == 0:
        return None
    return [round(float(h / total), 4) for h in hist]


def pixel_delta(px_a, px_b, lum_threshold=10):
    """Fraction of non-transparent pixels differing by >lum_threshold luma points."""
    if px_a is None or px_b is None or px_a.shape != px_b.shape:
        return None
    luma_a = 0.299 * px_a[:,:,0].astype(float) + 0.587 * px_a[:,:,1].astype(float) + 0.114 * px_a[:,:,2].astype(float)
    luma_b = 0.299 * px_b[:,:,0].astype(float) + 0.587 * px_b[:,:,1].astype(float) + 0.114 * px_b[:,:,2].astype(float)
    valid = (px_a[:,:,3] > 64) & (px_b[:,:,3] > 64)
    if valid.sum() == 0:
        return None
    diff_count = (np.abs(luma_a - luma_b) > lum_threshold) & valid
    return round(float(diff_count.sum() / valid.sum()), 5)


def chroma_delta(px_a, px_b, chroma_threshold=5.0):
    """Fraction of non-transparent pixels whose CHROMA differs > chroma_threshold."""
    if px_a is None or px_b is None or px_a.shape != px_b.shape:
        return None
    r_a, g_a, b_a, a_a = px_a[:,:,0].astype(float), px_a[:,:,1].astype(float), px_a[:,:,2].astype(float), px_a[:,:,3]
    r_b, g_b, b_b, a_b = px_b[:,:,0].astype(float), px_b[:,:,1].astype(float), px_b[:,:,2].astype(float), px_b[:,:,3]
    chroma_a = np.sqrt((r_a - g_a)**2 + (g_a - b_a)**2 + (b_a - r_a)**2) / np.sqrt(2)
    chroma_b = np.sqrt((r_b - g_b)**2 + (g_b - b_b)**2 + (b_b - r_b)**2) / np.sqrt(2)
    valid = (a_a > 64) & (a_b > 64)
    if valid.sum() == 0:
        return None
    diff_count = (np.abs(chroma_a - chroma_b) > chroma_threshold) & valid
    return round(float(diff_count.sum() / valid.sum()), 5)


# ---- full suite ----
def compute(path):
    """Full metric suite for a single PNG."""
    w, h, px = load_png(path)
    if px is None:
        return {"path": str(path), "error": "could not decode PNG"}
    return {
        "path": str(path),
        "dims": f"{w}x{h}",
        # luminance (backward-compatible with the original probe)
        "contrast_michelson": contrast_ratio(px),
        "spatial_variance": spatial_variance(px, w, h),
        "bloom_frac_0.9": bloom_fraction(px),
        "luminance_histogram_16": luminance_histogram(px),
        # CHROMA (new -- the axis the first probe proved blind to)
        "chroma": chroma_metrics(px),
        "chroma_histogram_16": chroma_histogram(px),
    }


def sparkline(hist):
    """Tiny ASCII bar for a histogram."""
    if not hist:
        return "(none)"
    max_h = max(hist)
    chars = "▁▂▃▄▅▆▇█"
    if max_h == 0:
        return "·" * len(hist)
    return "".join(chars[min(int(v / max_h * 7), 7)] for v in hist)


def main():
    # The natural experiment: three renders with shape, motion, frame, and time FIXED,
    # only the palette changed. This is the ideal test of "did the metrics notice the
    # thing taste notices?"
    triplet = [
        SNAPS / "look-geodesic-original.png",
        SNAPS / "look-geodesic-neon-blue.png",
        SNAPS / "look-geodesic-ident-edges.png",
    ]
    names = [p.stem for p in triplet]

    print("=" * 72)
    print("VFX PROBE: CHROMA-AWARE METRICS (deepseek Proposal A self-test)")
    print("=" * 72)
    print()
    print("TEST GROUP: look-geodesic triplet")
    print("  These three renders have shape, motion, frame, and time HELD FIXED.")
    print("  Only the palette changed (original → neon-blue → ident-edges).")
    print("  A luminance-only metric suite scored them IDENTICAL.")
    print("  Taste sees three different images. Does THIS probe see what taste sees?")
    print()

    results = []
    for p in triplet:
        r = compute(p)
        results.append(r)
        print(f"  {p.name} ({r.get('dims','?')} / {os.path.getsize(p)} bytes):")
        print(f"    luminance  contrast={r['contrast_michelson']}  "
              f"spatial_var={r['spatial_variance']}  bloom={r['bloom_frac_0.9']}")
        print(f"    lum_hist   {sparkline(r.get('luminance_histogram_16'))}")
        ch = r.get("chroma", {})
        if ch:
            print(f"    CHROMA     hue={ch.get('circular_mean_hue_deg')}°  "
                  f"sat={ch.get('mean_saturation')}  C={ch.get('mean_chroma')}  "
                  f"σ={ch.get('chroma_std')}")
            print(f"    chrom_hist {sparkline(r.get('chroma_histogram_16'))}")
        else:
            print(f"    CHROMA     (no signal -- <100 opaque pixels)")
        print()

    # Pairwise deltas -- the core of Proposal A: "did it change?"
    print("-" * 72)
    print("PAIRWISE DELTAS (luminance AND chroma)")
    print("  These answer: 'did the change register?' without opening the image.")
    print()

    for i in range(len(results)):
        for j in range(i+1, len(results)):
            a_path, b_path = triplet[i], triplet[j]
            _, _, px_a = load_png(a_path)
            _, _, px_b = load_png(b_path)
            if px_a is None or px_b is None:
                print(f"  {names[i]} → {names[j]}: SKIP (decode error)")
                continue
            if px_a.shape != px_b.shape:
                print(f"  {names[i]} → {names[j]}: SKIP (dims differ)")
                continue
            lum_d = pixel_delta(px_a, px_b)
            chr_d = chroma_delta(px_a, px_b)
            print(f"  {names[i]} → {names[j]}:")
            print(f"    luminance_delta = {lum_d}  ({lum_d*100:.1f}% pixels >10 luma diff)")
            print(f"    chroma_delta    = {chr_d}  ({chr_d*100:.1f}% pixels >5 chroma diff)")
            if lum_d is not None and lum_d < 0.01 and chr_d is not None and chr_d > 0.01:
                print(f"    ★ FINDING: luminance says 'no change', chroma says {chr_d*100:.1f}% changed.")
                print(f"      The first probe was blind to this. A chroma-aware probe is NOT.")
            print()

    # ---- Feed render (a single render -- what does it surface?) ----
    feed = SNAPS / "feed-thinking.png"
    if feed.exists():
        print("-" * 72)
        print("SINGLE-RENDER TELEMETRY: feed-thinking.png")
        r = compute(feed)
        ch = r.get("chroma", {})
        print(f"  contrast={r['contrast_michelson']}  bloom={r['bloom_frac_0.9']}  "
              f"hue={ch.get('circular_mean_hue_deg')}°  sat={ch.get('mean_saturation')}")
        # Solid-colour detection (Proposal F)
        if r['bloom_frac_0.9'] is not None and r['bloom_frac_0.9'] < 0.001:
            print(f"  ★ WARNING: render appears nearly uniform (bloom < 0.1%). "
                  f"Proposal F would flag this as a possible silent failure.")
        print()

    # ---- Ingest contact sheets (multi-frame -- what do metrics say about MOTION?) ----
    print("-" * 72)
    print("CONTACT SHEETS: do the metrics see MOTION?")
    for name in ["ingest-geodesic-original.png", "ingest-ringpulse.png"]:
        p = SNAPS / name
        if not p.exists():
            continue
        r = compute(p)
        print(f"  {name} ({r.get('dims','?')}):")
        print(f"    spatial_var={r['spatial_variance']}  bloom={r['bloom_frac_0.9']}")
        # Contact sheets are tiled frames; high spatial variance = lots of edges between
        # frames, which is the quantitative signature of motion in a still image.
        ch = r.get("chroma", {})
        if ch:
            print(f"    chroma mean_S={ch.get('mean_saturation')}  "
                  f"σ_C={ch.get('chroma_std')}")
        print()

    # ---- Judgement ----
    print("=" * 72)
    print("JUDGEMENT")
    print("=" * 72)
    print()
    print("Does the chroma-aware probe surface what the luminance-only probe missed?")
    print()
    lum_deltas = []
    chr_deltas = []
    for i in range(len(results)):
        for j in range(i+1, len(results)):
            _, _, px_a = load_png(triplet[i])
            _, _, px_b = load_png(triplet[j])
            if px_a is not None and px_b is not None and px_a.shape == px_b.shape:
                ld = pixel_delta(px_a, px_b)
                cd = chroma_delta(px_a, px_b)
                if ld is not None: lum_deltas.append(ld)
                if cd is not None: chr_deltas.append(cd)

    if lum_deltas and chr_deltas:
        avg_lum = sum(lum_deltas)/len(lum_deltas)
        avg_chr = sum(chr_deltas)/len(chr_deltas)
        print(f"  Average luminance delta across the triplet: {avg_lum:.4f} ({avg_lum*100:.1f}%)")
        print(f"  Average chroma delta    across the triplet: {avg_chr:.4f} ({avg_chr*100:.1f}%)")
        if avg_chr > avg_lum * 2:
            print(f"  ★ Chroma delta is {avg_chr/avg_lum:.1f}x the luminance delta.")
            print(f"    Proposal A is validated: luminance-only metrics are BLIND to this change.")
            print(f"    The agent NEEDS chroma to answer 'did it change?' without a human.")
        elif avg_chr > avg_lum:
            print(f"  Chroma delta is {avg_chr/avg_lum:.1f}x luminance. Mild validation.")
        else:
            print(f"  Luminance delta exceeds chroma. Huh -- unexpected. Look at the PNGs.")
    print()
    print("If the chroma numbers differ where the luminance numbers agree, Proposal A is right:")
    print("structured render output MUST include chroma. The first probe proved the blind spot;")
    print("this probe fills it.")


if __name__ == "__main__":
    main()
