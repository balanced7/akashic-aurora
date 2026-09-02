#!/usr/bin/env python3
"""Probe: do structured metrics surface anything a PNG does not?

Runs against real PNGs in design/vfx-snaps/ and design/vfx-thumbs/.
For each image, computes: contrast ratio (Michelson), spatial variance,
luminance histogram (16 buckets), bloom fraction (% pixels > 0.9 brightness),
and for pairs of images that are "before/after" of the same subject, a
per-frame delta score.

This is a self-test of Proposal A from the VFX agent-side report:
  "Structured output — the render returns DATA, not (just) a PNG"

Run: py scripts/vfx_probe_metrics.py
"""

from __future__ import annotations

import json
import os
import struct
import sys
import zlib
from collections import defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SNAPS = REPO / "design" / "vfx-snaps"
THUMBS = REPO / "design" / "vfx-thumbs"


def load_png(path):
    """Read a PNG and return (width, height, pixels_rgba) as a flat list of (r,g,b,a)."""
    with open(path, "rb") as fh:
        sig = fh.read(8)
        if sig[:4] != b"\x89PNG":
            return None, None, None
        width = height = None
        pixels = None
        while True:
            length_raw = fh.read(4)
            if len(length_raw) < 4:
                break
            length = struct.unpack(">I", length_raw)[0]
            chunk_type = fh.read(4).decode("ascii", errors="replace")
            chunk_data = fh.read(length)
            fh.read(4)  # CRC
            if chunk_type == "IHDR":
                width, height = struct.unpack(">II", chunk_data[:8])
            elif chunk_type == "IDAT" and width:
                if pixels is None:
                    pixels = bytearray()
                pixels.extend(chunk_data)
        if width and pixels:
            try:
                raw = zlib.decompress(bytes(pixels))
            except zlib.error:
                return width, height, None
            # Each row: filter byte + width*4 bytes
            stride = 1 + width * 4
            rgba = []
            for y in range(height):
                row_start = y * stride
                filt = raw[row_start]
                row_data = raw[row_start + 1:row_start + stride]
                # Only filter 0 (None) for simplicity — most PNGs use it
                if filt != 0:
                    # Try unfiltering or just skip — we want a signal, not perfection
                    return width, height, None
                for x in range(width):
                    off = x * 4
                    rgba.append((
                        row_data[off],
                        row_data[off + 1],
                        row_data[off + 2],
                        row_data[off + 3],
                    ))
            return width, height, rgba
        return width, height, None


def luminance(r, g, b):
    """BT.601 luminance."""
    return 0.299 * r + 0.587 * g + 0.114 * b


def contrast_ratio(pixels):
    """Michelson contrast: (Lmax - Lmin) / (Lmax + Lmin), on 5th/95th percentiles."""
    if not pixels:
        return None
    lums = sorted(luminance(r, g, b) for r, g, b, a in pixels if a > 64)
    if len(lums) < 100:
        return None
    n = len(lums)
    lo = lums[int(n * 0.05)]
    hi = lums[int(n * 0.95)]
    if hi + lo < 1:
        return 0.0
    return (hi - lo) / (hi + lo)


def spatial_variance(pixels, w, h):
    """Mean absolute difference between each pixel and its right neighbor — a proxy for texture."""
    if not pixels or w < 2:
        return None
    diffs = []
    for y in range(h):
        for x in range(w - 1):
            idx = y * w + x
            nxt = y * w + x + 1
            a0 = pixels[idx][3]
            a1 = pixels[nxt][3]
            if a0 < 64 or a1 < 64:
                continue
            l0 = luminance(*pixels[idx][:3])
            l1 = luminance(*pixels[nxt][:3])
            diffs.append(abs(l0 - l1))
    if not diffs:
        return None
    return sum(diffs) / len(diffs)


def luminance_histogram(pixels, buckets=16):
    """16-bucket luminance histogram, normalised to sum 1.0."""
    if not pixels:
        return None
    hist = [0] * buckets
    for r, g, b, a in pixels:
        if a < 64:
            continue
        lum = luminance(r, g, b)
        idx = min(int(lum / 255.0 * buckets), buckets - 1)
        hist[idx] += 1
    total = sum(hist)
    if total == 0:
        return None
    return [round(h / total, 4) for h in hist]


def bloom_fraction(pixels, threshold=0.9):
    """Fraction of non-transparent pixels above `threshold` brightness (0-1)."""
    if not pixels:
        return None
    count = 0
    total = 0
    for r, g, b, a in pixels:
        if a < 64:
            continue
        total += 1
        if luminance(r, g, b) / 255.0 >= threshold:
            count += 1
    if total == 0:
        return None
    return round(count / total, 5)


def pixel_delta(pixels_a, pixels_b):
    """Fraction of non-transparent pixels that differ by >10 luminance points between two images.
    Only compares pixels where BOTH are non-transparent."""
    if not pixels_a or not pixels_b or len(pixels_a) != len(pixels_b):
        return None
    diff_count = 0
    total = 0
    for (ra, ga, ba, aa), (rb, gb, bb, ab) in zip(pixels_a, pixels_b):
        if aa < 64 or ab < 64:
            continue
        total += 1
        if abs(luminance(ra, ga, ba) - luminance(rb, gb, bb)) > 10:
            diff_count += 1
    if total == 0:
        return None
    return round(diff_count / total, 5)


def compute(path):
    """Full metric suite for a single PNG."""
    w, h, px = load_png(path)
    if not px:
        return {"path": str(path), "error": "could not decode PNG", "w": w, "h": h}
    return {
        "path": str(path),
        "dims": f"{w}x{h}",
        "contrast_michelson": contrast_ratio(px),
        "spatial_variance": spatial_variance(px, w, h),
        "luminance_histogram_16": luminance_histogram(px),
        "bloom_frac_0.9": bloom_fraction(px),
    }


def main():
    # Pick the pairs that test the hypothesis.
    # (a) "look-geodesic-*" — three renders of the same avatar, same subject, different params
    # (b) "ingest-geodesic-original.png" — a contact sheet (many frames tiled)
    # (c) "feed-thinking.png" — a render from the feed
    # (d) "neon-*" — three renders of the neon composition at different stages

    groups = {
        "look-geodesic (3 param variations)": [
            SNAPS / "look-geodesic-original.png",
            SNAPS / "look-geodesic-neon-blue.png",
            SNAPS / "look-geodesic-ident-edges.png",
        ],
        "neon composition (3 stages)": [
            SNAPS / "neon-a-composing-claude.png",
            SNAPS / "neon-b-composing-blue.png",
            SNAPS / "neon-c-idle-blue.png",
        ],
        "contact sheets (ingest)": [
            SNAPS / "ingest-geodesic-original.png",
            SNAPS / "ingest-ringpulse.png",
        ],
        "feed renders": [
            SNAPS / "feed-thinking.png",
        ],
        "grid (param sweep)": [
            SNAPS / "grid-thick-x-gap.png",
        ],
    }

    for label, paths in groups.items():
        print(f"\n{'='*72}")
        print(f"GROUP: {label}")
        results = []
        for p in paths:
            r = compute(p)
            results.append(r)
            if "error" in r:
                print(f"  {os.path.basename(p)}: ERROR — {r['error']}")
                continue
            print(f"  {os.path.basename(p)} ({r['dims']}):")
            print(f"    contrast:  {r['contrast_michelson']}")
            print(f"    variance:  {r['spatial_variance']}")
            print(f"    bloom %:   {r['bloom_frac_0.9']}")
            hist = r.get("luminance_histogram_16")
            if hist:
                # show as a tiny sparkline
                max_h = max(hist)
                bar = "".join("█" if v > max_h * 0.6 else "▄" if v > max_h * 0.2 else "·" for v in hist)
                print(f"    lum hist:  {bar}")

        # Pairwise deltas between sequential renders in this group
        if len(results) >= 2:
            for i in range(len(results) - 1):
                a_path = paths[i]
                b_path = paths[i + 1]
                w_a, h_a, px_a = load_png(a_path)
                w_b, h_b, px_b = load_png(b_path)
                if not px_a or not px_b:
                    continue
                if len(px_a) != len(px_b):
                    print(f"  delta {os.path.basename(a_path)} → {os.path.basename(b_path)}: "
                          f"SKIP (different dimensions {w_a}x{h_a} vs {w_b}x{h_b})")
                    continue
                d = pixel_delta(px_a, px_b)
                print(f"  delta {os.path.basename(a_path)} → {os.path.basename(b_path)}: "
                      f"{d} ({d*100:.1f}% of non-transparent pixels changed by >10 lum)")

    # Summary: would any of these numbers have told the agent something the PNG did not?
    print(f"\n{'='*72}")
    print("JUDGEMENT: did the numbers surface anything actionable?")
    print("(This is the self-test of Proposal A — read the PNGs yourself and decide.)")
    print("")
    print("For each group:")
    print("1. Open the PNGs side by side. Do they look DIFFERENT?")
    print("2. Read the contrast/spatial variance/bloom numbers above.")
    print("3. If the numbers say 'big change' and the PNGs look the same, the metric is noise.")
    print("4. If the numbers say 'no change' and the PNGs look different, the metric is blind.")
    print("5. If the numbers say 'change here' and that matches what your eyes see, the metric")
    print("   carries signal — the agent could have known without opening the image.")


if __name__ == "__main__":
    main()
