"""CPU twin of the finish and io modules of the house GLSL library: post/vignette (post-vignette), post/dither
(post-dither), post/display-out (display-out), composite/blend (composite-blend), input/mouse (input-mouse),
input/audio (input-audio) and sim/feedback (sim-feedback). One function per GLSL function, with the GLSL name, in
float64. Pinned by tests/test_glsl_twins_finish_io.py.

WHY. These are the parts every surface ends with (the display tail) or listens through (the mouse, the audio texture),
so a wrong number here is wrong on every page at once, and a shader cannot print. This file is the same maths on the
CPU so a test can hold each part to the standards it implements: IEC 61966-2-1 sRGB through the finish, Porter and
Duff's over, the Web Audio analyser's decibel mapping, equal temperament, and the 8-bit staircase a feedback trail
lives on. The bench multimeter beside the oscilloscope.

Where the GPU reads something a CPU must be handed, the twin takes it as an argument: the audio texture is a (rows,
width) array of bytes (row 0 the spectrum, row 1 the waveform), sampled as WebGL samples a 2-row texture with linear
filtering and clamp-to-edge. cmpUnder's `inout` accumulator comes back as the return value. Functions the GLSL takes
from other modules (finiteOr from twins/core.py, dthIgn and dthTriFromUniform from twins/noise.py, the tone curves
from twins/tone.py, the encode and grades from twins/colour.py) come from their own twins, so a
change there reaches this file the way it reaches the shader.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; no corpus code.
"""
from __future__ import annotations

import math
from typing import List

import numpy as np


def _v(x) -> np.ndarray:
    return np.asarray(x, dtype=np.float64)


def _clamp(x, lo, hi):
    return np.minimum(np.maximum(x, lo), hi)


def _mix(a, b, t):
    return a + (b - a) * t


# Sibling twins, imported when first used: a twin of a module this one composes with is that module's own file.
def _core():
    from arsenal.shaders.twins import core
    return core


def _noise():
    from arsenal.shaders.twins import noise
    return noise


def _colour():
    from arsenal.shaders.twins import colour
    return colour


def _tone():
    from arsenal.shaders.twins import tone
    return tone


# ------------------------------------------------------------------------------------------- post/vignette.glsl
def vigCorner(uv01, aspect, amount):
    """The house cubic: 1 at the centre, 1 - 0.8306 * amount in every corner, flat across the middle."""
    uv = _v(uv01)
    from_centre = (uv - 0.5) * np.array([aspect, 1.0])
    corner_reach = math.hypot(0.5 * aspect, 0.5)
    reach = float(np.hypot(from_centre[0], from_centre[1])) / corner_reach
    fall = min(max(0.94 * reach, 0.0), 1.0)
    return 1.0 + ((1.0 - fall * fall * fall) - 1.0) * amount


# --------------------------------------------------------------------------------------------- post/dither.glsl
def ditherOut(enc, pixel, levels):
    """Triangular dither of one code value on an encoded colour, from a still mask; half a code value of uniform noise
    near 0 and 1, so black and white survive the rounding. levels < 2 is off."""
    enc = _v(enc)
    if levels < 2.0:
        return enc
    steps = levels - 1.0
    noise = _noise()
    mask = float(noise.dthIgn(_v(pixel)))
    tri = float(noise.dthTriFromUniform(np.asarray(mask)))
    half_step = 0.499 * (2.0 * mask - 1.0)
    room = _clamp(np.minimum(enc, 1.0 - enc) * steps, 0.0, 1.0)
    n = _mix(half_step, tri, room)
    return _clamp(enc + n / steps, 0.0, 1.0)


# ---------------------------------------------------------------------------------------- post/display-out.glsl
def displayOut(sceneLin, pixel, res, ev, curve, saturation, vignette, sCurve, ditherLevels):
    """The house tail: expose, display curve, saturation, vignette, sRGB encode, S-curve, static dither."""
    c, t = _colour(), _tone()
    light = _v(t.expose(np.maximum(_v(sceneLin), 0.0), ev))
    curve = int(curve)
    if curve == 1:
        shown = t.tmExp(light)
    elif curve == 2:
        shown = t.tmAcesFit(light)
    elif curve == 3:
        shown = t.tmPbrNeutral(light)
    else:
        shown = t.tmTanh(light)
    shown = _v(c.grdSaturation(_v(shown), saturation))
    pixel, res = _v(pixel), _v(res)
    shown = shown * vigCorner(pixel / res, res[0] / res[1], vignette)
    enc = _v(c.srgbEncode(_clamp(shown, 0.0, 1.0)))
    enc = _clamp(_v(c.grdSCurveDisp(enc, sCurve)), 0.0, 1.0)
    return ditherOut(enc, pixel, ditherLevels)


# ----------------------------------------------------------------------------------------- composite/blend.glsl
def cmpOver(front, back):
    """Porter-Duff over, straight alpha in and out."""
    f, b = _v(front), _v(back)
    behind = b[3] * (1.0 - f[3])
    alpha = f[3] + behind
    if alpha <= 0.0:
        return np.zeros(4)
    rgb = (f[:3] * f[3] + b[:3] * behind) / alpha
    return np.append(rgb, alpha)


def cmpOverPremul(front, back):
    """Porter-Duff over, premultiplied alpha."""
    f, b = _v(front), _v(back)
    return f + b * (1.0 - f[3])


def cmpUnder(acc, layer):
    """Front-to-back: the premultiplied layer goes behind the accumulator; an accumulator at alpha >= 0.998 is left
    alone. Returns the new accumulator (GLSL: inout)."""
    acc, layer = _v(acc), _v(layer)
    if acc[3] >= 0.998:
        return acc.copy()
    return acc + layer * (1.0 - acc[3])


def cmpAdd(a, b):
    return _v(a) + _v(b)


def cmpScreen(a, b):
    da, db = _clamp(_v(a), 0.0, 1.0), _clamp(_v(b), 0.0, 1.0)
    return 1.0 - (1.0 - da) * (1.0 - db)


def cmpMax(a, b):
    return np.maximum(_v(a), _v(b))


# --------------------------------------------------------------------------------------------- input/mouse.glsl
def mouseUntouched(mouse) -> bool:
    return bool(np.all(_v(mouse) == 0.0))


def mouseHeld(mouse) -> bool:
    return bool(_v(mouse)[2] > 0.0)


def mouseJustClicked(mouse) -> bool:
    return bool(_v(mouse)[3] > 0.0)


def mouseDragOrigin(mouse):
    return np.abs(_v(mouse)[2:4])


# --------------------------------------------------------------------------------------------- input/audio.glsl
FFT_SIZE = 2048            # the analyser's transform: bin k is k * sampleRate / FFT_SIZE hertz
MAX_TAPS = 64              # audBand's loop bound
LOG2_10 = 3.321928094887362


def _row_sample(a, u, row):
    """texture(a, vec2(u, row centre)).x for a 2-row byte texture: linear filtering along the row, clamp to edge."""
    tex = np.asarray(a)
    width = tex.shape[1]
    x = u * width - 0.5
    i0 = math.floor(x)
    f = x - i0
    j0, j1 = min(max(i0, 0), width - 1), min(max(i0 + 1, 0), width - 1)
    v0, v1 = float(tex[row, j0]) / 255.0, float(tex[row, j1]) / 255.0
    return v0 + (v1 - v0) * f


def audSpectrum(a, u):
    """Row 0 at u: the analyser's byte over 255 (decibels mapped to 0..1)."""
    return _row_sample(a, u, 0)


def audWave(a, u):
    """Row 1 at u, back in -1..1; byte 128 (silence) reads exactly 0, and so does a texture without a second row."""
    if np.asarray(a).shape[0] < 2:
        return 0.0
    return _row_sample(a, u, 1) * (255.0 / 128.0) - 1.0


def audByteToDb(v):
    """One spectrum byte (0..1) to decibels, through the analyser's default -100..-30 dB range."""
    return -100.0 + 70.0 * v


def audByteToAmp(v):
    """One spectrum byte (0..1) to linear amplitude; byte 0 is silence, 0."""
    return 2.0 ** (audByteToDb(v) * (LOG2_10 / 20.0)) if v > 0.0 else 0.0


def audBandBins(hzLo, hzHi, sampleRate, width) -> List[int]:
    """The bins audBand's loop reads, in order: every bin of the band, or 64 spread evenly across a wider one.
    (Twin-only: the GLSL computes the same plan inside its loop.)"""
    last = float(width - 1)
    bins_per_hz = FFT_SIZE / sampleRate
    k_lo = min(max(math.floor(min(hzLo, hzHi) * bins_per_hz + 0.5), 0.0), last)
    k_hi = min(max(math.floor(max(hzLo, hzHi) * bins_per_hz + 0.5), k_lo), last)
    bins = k_hi - k_lo + 1.0
    stride = max(1.0, math.ceil(bins / MAX_TAPS))
    taps = math.floor((bins - 1.0) / stride) + 1.0
    return [int(k_lo + i * stride) for i in range(MAX_TAPS) if i < taps]


def audBand(a, hzLo, hzHi, sampleRate):
    """Mean linear magnitude over the bins of [hzLo, hzHi] (at most 64 taps)."""
    tex = np.asarray(a)
    if tex.shape[1] < 1:
        return 0.0                                     # nothing bound: silence
    plan = audBandBins(hzLo, hzHi, sampleRate, tex.shape[1])
    return sum(audByteToAmp(float(tex[0, k]) / 255.0) for k in plan) / len(plan)


def midiToHz(m):
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0)


def hzToMidi(hz):
    return 69.0 + 12.0 * math.log2(max(hz, 0.001) / 440.0)


def pianoKeyToHz(key):
    return 440.0 * 2.0 ** ((key - 49.0) / 12.0)


# -------------------------------------------------------------------------------------------- sim/feedback.glsl
def simSanitize(v, bound, fallback):
    """finiteOr, then clamp to [-bound, bound]."""
    safe = _v(_core().finiteOr(_v(v).astype(np.float32), _v(fallback).astype(np.float32)))
    return _clamp(safe, -bound, bound)


def fbDecay(prev, keep, floorStep):
    """Scale by keep, then one floorStep off the magnitude, never crossing zero."""
    p = _v(prev)
    return np.sign(p) * np.maximum(np.abs(p) * keep - floorStep, 0.0)
