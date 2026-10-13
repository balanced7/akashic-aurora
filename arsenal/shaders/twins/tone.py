"""CPU twins of the house tone modules: colour/tone.glsl and legacy/tone-superlinear.glsl.

WHY. A tone curve is the soft limiter between unbounded light and the screen's 0..1, an audio limiter with a soft knee.
Its numbers decide how every surface looks, so each GLSL curve has a numpy twin with the same name and maths, pinned
at fixed points computed from the published formulas (tests/test_glsl_twins_colour.py), and the GLSL is pinned to the
twin on SwiftShader. Inputs are scene-linear light (array-likes, last axis RGB); outputs are display-linear 0..1 (not
yet encoded) unless the name says otherwise.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; credits in colour/tone.glsl's header: Krzysztof
Narkowicz (the ACES fit, 2016), Khronos (PBR Neutral, Emmett Lalish, 2024), Lawlor and Genetti (hue-safe gamma, 2011).
"""
from __future__ import annotations

import numpy as np

TANH_LIMIT = 10.0       # tanh is 1.0 in float32 past about 9; the GLSL clamps here so no driver overflows exp() to NaN
ACES_LIMIT = 1000.0     # the ACES fit has already clipped to 1 by v = 7.24; the GLSL clamps here so v * v stays finite
PBR_F = 0.04            # PBR Neutral: a dielectric's Fresnel reflectance, the toe's floor
PBR_KNEE = 0.8 - PBR_F  # where peak compression starts (0.76)
PBR_DESAT = 0.15        # how fast compressed peaks drift toward white


def _v(x):
    return np.asarray(x, dtype=float)


def expose(lin, ev):
    """lin * 2^ev: camera stops, the only brightness knob before the display curve."""
    return _v(lin) * np.exp2(_v(ev))


def tmTanh(x):
    """tanh per channel: slope 1 at black, no toe, about 1.4 stops of headroom. Negative light is none."""
    return np.tanh(np.clip(_v(x), 0.0, TANH_LIMIT))


def tmExp(x):
    """1 - e^-x per channel: film density saturating."""
    return 1.0 - np.exp(-np.maximum(_v(x), 0.0))


def tmReinhard(x):
    """x / (1 + x) per channel."""
    x = np.maximum(_v(x), 0.0)
    return x / (1.0 + x)


def tmAcesFit(x):
    """Narkowicz's rational fit of the ACES look, with the 0.6 pre-scale that matches the reference inside."""
    v = np.clip(0.6 * _v(x), 0.0, ACES_LIMIT)
    return np.clip((v * (2.51 * v + 0.03)) / (v * (2.43 * v + 0.59) + 0.14), 0.0, 1.0)


def tmPbrNeutral(x):
    """Khronos PBR Neutral (the three.js NeutralToneMapping the piano renders with): a tiny toe, identity up to the
    knee, then only the peak channel is compressed and the colour drifts gently toward white. Hue never turns."""
    x = _v(x)
    low = np.min(x, axis=-1, keepdims=True)
    toe = np.where(low <= 2.0 * PBR_F, low - low * low / (4.0 * PBR_F), PBR_F)
    c = x - toe
    peak = np.max(c, axis=-1, keepdims=True)
    d = 1.0 - PBR_KNEE
    new_peak = 1.0 - d * d / (peak + d - PBR_KNEE)
    safe_peak = np.where(peak > PBR_KNEE, peak, 1.0)
    squeezed = c * (new_peak / safe_peak)
    g = 1.0 - 1.0 / (PBR_DESAT * (peak - new_peak) + 1.0)
    squeezed = squeezed * (1.0 - g) + new_peak * g
    return np.where(peak <= PBR_KNEE, c, squeezed)


def tmRootGain(x, gain):
    """gain * sqrt(x): makes faint accumulated glow legible without a filmic curve."""
    return _v(gain) * np.sqrt(np.maximum(_v(x), 0.0))


def displayHueSafeGamma(c, gamma):
    """Gamma on the colour's magnitude only: c * |c|^(1/gamma - 1). The direction (hue and saturation) is untouched,
    so the tint of thousands of summed dim emitters survives a lift that per-channel gamma would bleach."""
    c = _v(c)
    m = np.maximum(np.linalg.norm(c, axis=-1, keepdims=True), 1e-10)
    return c * np.power(m, 1.0 / _v(gamma) - 1.0)


def tmSuperlinear(x, k):
    """x + k x^2: the house's superlinear highlight (the bench chunk superlinear-highlight, k = 0.85), run before the
    tanh shoulder so mids sink while crests bloom."""
    x = _v(x)
    return x + x * x * _v(k)
