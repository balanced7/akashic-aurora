"""CPU twins of the house colour modules: colour/transfer.glsl, colour/oklab.glsl, legacy/hsv.glsl, colour/grade.glsl.

WHY. A shader cannot print, so each GLSL function here has a numpy twin with the same name and the same maths, in
float64. tests/test_glsl_twins_colour.py pins the twins to published values (the sRGB standard's formula, the OKLCH of
the sRGB primaries as CSS Color 4 publishes them) and then pins the GLSL to the twins on SwiftShader. Think of a twin
as the bench multimeter beside the oscilloscope: the scope shows the picture, the meter proves the voltage.

CONVENTIONS. Colours are array-likes whose last axis is RGB (or L, a, b / L, C, h); every function takes one colour or
a stack of them. Hue is in TURNS (0..1), as the palettes use it. Everything is scene-linear light unless the name says
otherwise (srgbEncode returns display code values; grdSCurveDisp takes and returns them).

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; credits are in each GLSL module's header:
IEC 61966-2-1 (sRGB), ITU-R BT.709 (luminance), Bjorn Ottosson's OKLab (2020, bottosson.github.io/posts/oklab),
Sam Hocevar's branch-free HSV (lolengine.net, 2013), the ASC and colourist practice for the grades.
"""
from __future__ import annotations

import numpy as np

TAU = 2.0 * np.pi

# sRGB (IEC 61966-2-1): the linear toe below the knee, the offset 2.4 power above it.
SRGB_KNEE_LIN = 0.0031308
SRGB_KNEE_ENC = 0.04045
REC709 = np.array([0.2126, 0.7152, 0.0722])

# OKLab (Ottosson 2020): linear sRGB -> cone response (LMS), cube root, -> L, a, b. And back.
OKLAB_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                     [0.2119034982, 0.6806995451, 0.1073969566],
                     [0.0883024619, 0.2817188376, 0.6299787005]])
OKLAB_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                     [1.9779984951, -2.4285922050, 0.4505937099],
                     [0.0259040371, 0.7827717662, -0.8086757660]])
OKLAB_M2_INV = np.array([[1.0, 0.3963377774, 0.2158037573],
                         [1.0, -0.1055613458, -0.0638541728],
                         [1.0, -0.0894841775, -1.2914855480]])
OKLAB_M1_INV = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                         [-1.2684380046, 2.6097574011, -0.3413193965],
                         [-0.0041960863, -0.7034186147, 1.7076147010]])

MAX_CHROMA_CEILING = 0.4     # above every sRGB chroma (the largest, magenta's, is about 0.32)
MAX_CHROMA_STEPS = 24        # bisection steps for oklchMaxChroma (the piano's own count)
CLIP_STEPS = 16              # bisection steps for oklchClip, over [0, C]
CUSP_STEPS = 24              # bisection steps along the hue hexagon in oklchCusp
POWERLESS_CHROMA = 1e-4      # below this a colour's hue means nothing (a grey); mixOklch takes the other end's hue


def _v(x):
    return np.asarray(x, dtype=float)


# ----------------------------------------------------------------------------------------- colour/transfer.glsl (H1)
def srgbEncode(lin):
    """Linear light to sRGB code values, exactly IEC 61966-2-1. Negative light is black; values above 1 continue."""
    x = np.maximum(_v(lin), 0.0)
    return np.where(x <= SRGB_KNEE_LIN, 12.92 * x, 1.055 * np.power(x, 1.0 / 2.4) - 0.055)


def srgbDecode(enc):
    """sRGB code values to linear light, the exact inverse of srgbEncode. Negative codes are black."""
    v = np.maximum(_v(enc), 0.0)
    return np.where(v <= SRGB_KNEE_ENC, v / 12.92, np.power((v + 0.055) / 1.055, 2.4))


def luminance(lin):
    """Relative luminance Y of linear Rec. 709 / sRGB light (the middle row of the sRGB-to-XYZ matrix)."""
    return np.asarray(_v(lin) @ REC709)


def cbrtSigned(x):
    """Cube root that keeps the sign, so OKLab stays finite for out-of-gamut (negative) light."""
    x = _v(x)
    return np.sign(x) * np.power(np.abs(x), 1.0 / 3.0)


# ------------------------------------------------------------------------------------------- colour/oklab.glsl (H2)
def oklabFromLinear(lin):
    return cbrtSigned(_v(lin) @ OKLAB_M1.T) @ OKLAB_M2.T


def linearFromOklab(lab):
    lms = _v(lab) @ OKLAB_M2_INV.T
    return (lms * lms * lms) @ OKLAB_M1_INV.T


def oklchFromOklab(lab):
    """(L, a, b) to (L, C, h) with h in turns, [0, 1). A grey (C = 0) has hue 0, never NaN."""
    lab = _v(lab)
    c = np.hypot(lab[..., 1], lab[..., 2])
    h = np.arctan2(lab[..., 2], lab[..., 1] + (c == 0.0)) / TAU
    h = h - np.floor(h)
    return np.stack([lab[..., 0], c, h], axis=-1)


def oklabFromOklch(lch):
    lch = _v(lch)
    angle = TAU * lch[..., 2]
    return np.stack([lch[..., 0], lch[..., 1] * np.cos(angle), lch[..., 1] * np.sin(angle)], axis=-1)


def _lin_from_lch(L, c, h):
    return linearFromOklab(oklabFromOklch(np.stack(np.broadcast_arrays(_v(L), _v(c), _v(h)), axis=-1)))


def mixOklab(a, b, t):
    """Blend two linear colours in OKLab; returns linear. Not gamut-clipped (OKLab mixes of in-gamut colours can step a
    hair outside sRGB). Commutes with gain: mixing 4a and 4b gives 4 times the mix of a and b."""
    t = _v(t)[..., None]
    return linearFromOklab(oklabFromLinear(a) * (1.0 - t) + oklabFromLinear(b) * t)


def hueDelta(h0, h1):
    """Signed shortest step from hue h0 to hue h1, in turns, in [-0.5, 0.5)."""
    d = _v(h1) - _v(h0) + 0.5
    return d - np.floor(d) - 0.5


def inGamut(lin, eps):
    """Every channel within [-eps, 1 + eps]."""
    lin = _v(lin)
    return np.all((lin >= -eps) & (lin <= 1.0 + eps), axis=-1)


def oklchMaxChroma(L, h, eps):
    """The largest chroma at lightness L and hue h (turns) whose colour is still inside sRGB (with tolerance eps), by
    MAX_CHROMA_STEPS of bisection on [0, MAX_CHROMA_CEILING]. The GLSL twin of the piano's maxChroma (piano.js)."""
    L, h = np.broadcast_arrays(_v(L), _v(h))
    lo, hi = np.zeros(L.shape), np.full(L.shape, MAX_CHROMA_CEILING)
    for _ in range(MAX_CHROMA_STEPS):
        mid = 0.5 * (lo + hi)
        ok = inGamut(_lin_from_lch(L, mid, h), eps)
        lo, hi = np.where(ok, mid, lo), np.where(ok, hi, mid)
    return lo


def _hexagon(u):
    """The fully saturated edge of the RGB cube (one channel 1, one 0) at HSV hue u: the only place a cusp can be."""
    u = _v(u)[..., None]
    k = np.array([1.0, 2.0 / 3.0, 1.0 / 3.0])
    p = u + k
    phase = p - np.floor(p)
    tent = np.abs(6.0 * phase - 3.0)
    return np.clip(tent - 1.0, 0.0, 1.0)


def _hue_of(lin):
    return oklchFromOklab(oklabFromLinear(lin))[..., 2]


def oklchCusp(h):
    """(L, C) of the most colourful sRGB colour of hue h (turns): the gamut's cusp. Bisection along the RGB cube's
    saturated hexagon, where OKLab hue rises with the HSV hue -- except in a sliver beside pure blue (264.05 to 264.19
    degrees), where it doubles back on the cyan-to-blue edge. So the search is split at the blue corner: a hue at or
    past blue's own is searched on the blue-to-magenta-to-red edges, where the brightest-chroma crossing lives."""
    h = _v(h)
    h_red, h_blue = _hue_of([1.0, 0.0, 0.0]), _hue_of([0.0, 0.0, 1.0])
    target = h - h_red
    target = target - np.floor(target)
    blue_at = (h_blue - h_red) % 1.0
    past_blue = target >= blue_at
    lo = np.where(past_blue, 2.0 / 3.0, 0.0)
    hi = np.where(past_blue, 1.0, 2.0 / 3.0)
    for _ in range(CUSP_STEPS):
        mid = 0.5 * (lo + hi)
        along = _hue_of(_hexagon(mid)) - h_red
        along = along - np.floor(along)
        below = along < target
        lo, hi = np.where(below, mid, lo), np.where(below, hi, mid)
    lab = oklabFromLinear(_hexagon(0.5 * (lo + hi)))
    return np.stack([lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])], axis=-1)


def oklchClip(lch):
    """OKLCH to linear sRGB inside the gamut: lightness clamped to [0, 1], then chroma reduced at fixed lightness and
    hue (CLIP_STEPS of bisection on [0, C]) until every channel is within [0, 1]. Hue never moves, unlike a per-channel
    clamp. Returns linear light in [0, 1]."""
    lch = _v(lch)
    L, c, h = np.clip(lch[..., 0], 0.0, 1.0), np.maximum(lch[..., 1], 0.0), lch[..., 2]
    full = _lin_from_lch(L, c, h)
    lo, hi = np.zeros(np.shape(L)), np.array(c, dtype=float)
    for _ in range(CLIP_STEPS):
        mid = 0.5 * (lo + hi)
        ok = inGamut(_lin_from_lch(L, mid, h), 0.0)
        lo, hi = np.where(ok, mid, lo), np.where(ok, hi, mid)
    clipped = np.where(inGamut(full, 0.0)[..., None], full, _lin_from_lch(L, lo, h))
    return np.clip(clipped, 0.0, 1.0)


def _unit_scale(*cols):
    """The gain that brings the brightest channel of these colours down to 1 (never up): HDR light is shaped in the unit
    cube and given its level back afterwards. Exact for OKLab work, which commutes with gain."""
    m = np.max(np.stack([np.max(_v(c), axis=-1) for c in cols], axis=0), axis=0)
    return np.maximum(m, 1.0)


def mixOklch(a, b, t):
    """Blend two linear colours in OKLCH: lightness and chroma lerp, hue takes the shorter arc, the result is
    gamut-clipped. A grey end (chroma below POWERLESS_CHROMA) borrows the other end's hue, so grey to teal stays teal
    rather than sweeping the wheel. HDR-safe: both ends share one gain into the unit cube and back."""
    s = _unit_scale(a, b)
    la = oklchFromOklab(oklabFromLinear(_v(a) / s[..., None]))
    lb = oklchFromOklab(oklabFromLinear(_v(b) / s[..., None]))
    ha = np.where(la[..., 1] < POWERLESS_CHROMA, lb[..., 2], la[..., 2])
    hb = np.where(lb[..., 1] < POWERLESS_CHROMA, ha, lb[..., 2])
    t = _v(t)
    L = la[..., 0] * (1.0 - t) + lb[..., 0] * t              # GLSL mix(x, y, t) = x (1 - t) + y t
    c = la[..., 1] * (1.0 - t) + lb[..., 1] * t
    h = ha + hueDelta(ha, hb) * t
    return oklchClip(np.stack(np.broadcast_arrays(L, c, h), axis=-1)) * s[..., None]


def hueRotateOklch(lin, turns):
    """Rotate hue by `turns` at constant OKLab lightness and chroma, then gamut-clip. HDR light is rotated at its own
    level (scaled into the unit cube, rotated and clipped there, scaled back)."""
    s = _unit_scale(lin)
    lch = oklchFromOklab(oklabFromLinear(_v(lin) / s[..., None]))
    lch = np.stack([lch[..., 0], lch[..., 1], lch[..., 2] + _v(turns)], axis=-1)
    return oklchClip(lch) * s[..., None]


# ---------------------------------------------------------------------------------------------- legacy/hsv.glsl (H3)
def hsvToRgb(hsv):
    """HSV (hue in turns) to RGB: the clamped triangle wave per channel, mixed toward white by 1 - S, scaled by V.
    Display knobs, not perception: V is the largest channel, not brightness."""
    hsv = _v(hsv)
    h, s, v = hsv[..., 0:1], hsv[..., 1:2], hsv[..., 2:3]
    p = h + np.array([1.0, 2.0 / 3.0, 1.0 / 3.0])
    ramp = np.abs((p - np.floor(p)) * 6.0 - 3.0)
    return v * (1.0 + (np.clip(ramp - 1.0, 0.0, 1.0) - 1.0) * s)


def rgbToHsv(rgb):
    """RGB to HSV (hue in turns) by the branch-free ordering the house pastes (two compare-and-swaps carrying the
    sextant's hue offset, with 1e-10 guards); a grey's hue is 0."""
    rgb = _v(rgb)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    green_leads = b <= g
    px = np.where(green_leads, g, b)
    py = np.where(green_leads, b, g)
    pz = np.where(green_leads, 0.0, -1.0)
    pw = np.where(green_leads, -1.0 / 3.0, 2.0 / 3.0)
    red_leads = px <= r
    qx = np.where(red_leads, r, px)
    qy = py
    qz = np.where(red_leads, pz, pw)
    qw = np.where(red_leads, px, r)
    spread = qx - np.minimum(qw, qy)
    tiny = 1.0e-10
    return np.stack([np.abs(qz + (qw - qy) / (6.0 * spread + tiny)), spread / (qx + tiny), qx], axis=-1)


# --------------------------------------------------------------------------------------------- colour/grade.glsl (H6)
def grdSaturation(lin, s):
    """Y + s (x - Y) with Rec. 709 luminance Y: s = 0 is the true grey, luminance never changes."""
    lin = _v(lin)
    y = luminance(lin)[..., None]
    return y + _v(s)[..., None] * (lin - y)


def grdAwayFrom(c, pivot, k):
    """Push a colour away from a pivot by k: c + k (c - pivot). Extrapolation is how a dull colour turns candy and a
    bright one overbright. Light cannot be negative, so the result is floored at 0."""
    c = _v(c)
    return np.maximum(c + _v(k)[..., None] * (c - _v(pivot)), 0.0)


def grdSCurveDisp(disp, amount):
    """A smoothstep S-curve on display (encoded) values, mixed in by amount: the classic finish after encode."""
    disp = _v(disp)
    x = np.clip(disp, 0.0, 1.0)
    curve = x * x * (3.0 - 2.0 * x)
    return disp + (curve - disp) * _v(amount)[..., None]
