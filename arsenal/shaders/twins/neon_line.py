"""CPU twin of groups/neon-line.glsl, the neon-line group recipe (atlas section 16.4): neonProfile, neonPathStep and
neonLine. Pinned by tests/test_glsl_twins_groups_neon_studio_hex.py, which also holds the GLSL to this twin on
SwiftShader.

WHY. A line's look is two promises that a screenshot cannot check: the core is its width in pixels at any scale (its
ink, integrated across it, is widthPx), and defocus spreads light without adding any. Both are integrals, so they are
pinned here on the CPU. The parts the recipe calls come from their own twins (aaWire and sd2Segment from draw2.py,
the glow shapes from light.py, the inverse power from shaping.py), so a change there reaches this file the way it
reaches the shader. Arrays broadcast: d, energy and depth may be arrays of any shape, and acc has a trailing rgb axis.

Apache-2.0, Akashic Aurora. Written fresh from the recipe's contract; no corpus code.
"""
from __future__ import annotations

import numpy as np

from arsenal.shaders.twins import draw2, light, shaping

HALO_GAIN = 0.55                           # the halo's height against the core's, at the line
TWO_GAUSS = (24.0, 1.0, 3.0, 0.18)         # the house light line (gyre-flight), normalised by its height 1.18


def _v(x):
    return np.asarray(x, dtype=np.float64)


def neonProfile(dPx, haloPx, profile):
    """1 at the line, falling with x = dPx / haloPx: 0 two Gaussians, 1 Lorentzian, 2 inverse power, 3 none."""
    halo = _v(haloPx)
    x = np.maximum(_v(dPx), 0.0) / np.where(halo > 0.0, halo, 1.0)
    if profile == 3:
        out = np.zeros(np.broadcast(x, halo).shape)
    elif profile == 1:
        out = _v(light.glowLorentz(x, 0.0625))
    elif profile == 2:
        out = _v(shaping.shpInvPower(x + 0.35, 0.35, 2.0))
    else:                                  # 0, and any value the GLSL does not name, is the house light line
        out = _v(light.glowTwoGauss(x, TWO_GAUSS)) / 1.18
    out = np.where(halo > 0.0, out, 0.0)
    return out[()] if out.ndim == 0 else out


def neonPathStep(p, a, b, s, best):
    """(distance, curve parameter) of the nearer of `best` and the segment a..b, the parameter running s[0] to s[1]."""
    here = draw2.sd2Segment(_v(p).astype(np.float32), _v(a).astype(np.float32), _v(b).astype(np.float32))
    here = _v(here)
    best = _v(best)
    s = _v(s)
    along = s[0] + (s[1] - s[0]) * here[..., 1]
    nearer = here[..., 0] < best[..., 0]
    return np.stack([np.where(nearer, here[..., 0], best[..., 0]), np.where(nearer, along, best[..., 1])], -1)


def _hot_core_over_heat(hue, heat):
    """glowHotCore(hue, heat) / heat, element by element: mix(hue, peak, heat^2 / (1 + heat^2)); the hue itself where
    heat is 0. (light.glowHotCore is the scalar twin; a test holds the two equal.)"""
    peak = np.max(hue, axis=-1, keepdims=True)
    h = _v(heat)[..., None]
    white = h * h / (1.0 + h * h)
    return np.where(h > 1e-4, hue + (peak - hue) * white, hue)


def neonLine(acc, d, px, tint, energy, depth, widthPx, haloPx, profile, coreHeat, combine, defocus, view):
    """One line's light combined into acc: energy * (hot core * core + tint * 0.55 * halo), the core a wire of widthPx
    pixels and the halo a profile of haloPx pixels, both spread by 1 + 3 defocus depth at the same total light."""
    pixel = max(float(px), 1e-6)
    spread = 1.0 + 3.0 * np.clip(_v(defocus), 0.0, 1.0) * np.clip(_v(depth), 0.0, 1.0)
    across = np.abs(_v(d))
    core = _v(draw2.aaWire(across, max(float(widthPx), 0.0) * spread, pixel)) / spread
    halo = _v(neonProfile(across / pixel, max(float(haloPx), 0.0) * spread, profile)) / spread
    hue = np.maximum(_v(tint), 0.0)
    power = np.maximum(_v(energy), 0.0)
    heat = max(float(coreHeat), 0.0) * power
    core, halo, power = np.broadcast_arrays(core, halo, power)
    core_colour = _hot_core_over_heat(np.broadcast_to(hue, core.shape + (3,)), np.broadcast_to(heat, core.shape))
    if view == 1:
        out = np.repeat(core[..., None], 3, axis=-1)
    elif view == 2:
        out = hue * (HALO_GAIN * power * halo)[..., None]
    else:
        out = power[..., None] * (core_colour * core[..., None] + hue * (HALO_GAIN * halo)[..., None])
    acc = _v(acc)
    return acc + out if combine == 1 else np.maximum(acc, out)


__all__ = ["neonProfile", "neonPathStep", "neonLine"]
