"""CPU twin of the foundation modules (atlas family A, arsenal/web/glsl/core/ and debug/views.glsl): the constants,
the safe maths, rotation, floor-correct integers, the unroll barrier, frame-rate independent clocks, the 2D frame and
the debug views. Pinned by tests/test_glsl_twins_core.py.

WHY. The foundation is the power rail every other module draws from: a constant off by a rounding, a modulo that
doubles the tile at zero, or a decay that runs four times faster on the 240 Hz screen would show up in every surface at
once, and a shader cannot print a number to say so. This file is the same maths on the CPU, in float32 like the GPU, so
a test can hold each function to the mathematics' own fixed points. It is the bench multimeter beside the oscilloscope.

Names match the GLSL names exactly (a grep for `clkKeep` finds both halves). Where the GPU reads something a CPU has to
be handed, the twin takes it as an argument and says so: dbgSlice takes the filter width fwidth(d) would give, and
uvFootprint takes the coordinate at every pixel of an image and measures the change between neighbours itself.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; no corpus code.
"""
from __future__ import annotations

import numpy as np

F32 = np.float32

# ---------------------------------------------------------------------------------------------- core/const.glsl
PI = F32(3.14159265358979323846)       # half a turn, in radians
TAU = F32(6.28318530717958647692)      # a whole turn: 2 PI
PHI = F32(1.61803398874989484820)      # the golden ratio, (1 + sqrt 5) / 2: PHI * PHI = PHI + 1
SQRT3 = F32(1.73205080756887729353)    # the height of an equilateral triangle is SQRT3 / 2 of its side


def _f(x):
    return np.asarray(x, dtype=F32)


def _mix(x, y, a):
    """GLSL mix by its definition, x (1 - a) + y a, in float32."""
    return (x * (F32(1) - a) + y * a).astype(F32)


def _scalar(x):
    """A 0-d result comes back as a numpy scalar, so `twin(0.5) == 1.0` reads naturally in a test."""
    return x[()] if isinstance(x, np.ndarray) and x.ndim == 0 else x


# ---------------------------------------------------------------------------------------------- core/safe.glsl
def dot2(v):
    """dot(v, v): the squared length, over the last axis."""
    v = _f(v)
    return _scalar(np.sum(v * v, axis=-1, dtype=F32))


def safeDiv(n, d, eps):
    """n / d with |d| floored at eps and its sign kept (zero counts as positive)."""
    n, d, eps = _f(n), _f(d), _f(eps)
    den = np.where(d < 0, np.minimum(d, -eps), np.maximum(d, eps))
    return _scalar((n / den).astype(F32))


def safeNormalize(v, fallback):
    """v / |v| when dot(v, v) > 1e-24, else the fallback."""
    v, fallback = _f(v), _f(fallback)
    l2 = np.sum(v * v, axis=-1, keepdims=True, dtype=F32)
    ok = l2 > F32(1e-24)
    inv = F32(1) / np.sqrt(np.where(ok, l2, F32(1)))
    return np.where(ok, v * inv, fallback).astype(F32)


def safeSqrt(x):
    return _scalar(np.sqrt(np.maximum(_f(x), F32(0))))


def safeAcos(x):
    return _scalar(np.arccos(np.clip(_f(x), F32(-1), F32(1))).astype(F32))


def safePow(b, e):
    """pow on max(b, 1e-30): the GLSL pow is undefined for a negative base, and for a zero base with e <= 0."""
    with np.errstate(over="ignore", under="ignore"):
        return _scalar(np.power(np.maximum(_f(b), F32(1e-30)), _f(e)).astype(F32))


def _exponent_all_ones(v):
    """The IEEE 754 test a compiler cannot fold away: exponent bits all ones means Inf or NaN."""
    return (np.ascontiguousarray(_f(v)).view(np.int32) & 0x7F800000) == 0x7F800000


def finiteOr(v, fallback):
    """Each component of v that is NaN or Inf replaced by the same component of the fallback."""
    v, fallback = _f(v), _f(fallback)
    return np.where(_exponent_all_ones(v), fallback, v).astype(F32)


# ---------------------------------------------------------------------------------------------- core/rotate.glsl
def rotate2(a):
    """The matrix GLSL's mat2(c, s, -s, c) is (columns first), written row by row: rotate2(a) @ p turns p
    counter-clockwise by a radians."""
    a = F32(a)
    c, s = np.cos(a, dtype=F32), np.sin(a, dtype=F32)
    return np.array([[c, -s], [s, c]], dtype=F32)


# ---------------------------------------------------------------------------------------------- core/int.glsl
def imodFloor(a, b):
    """Floor modulo in [0, b) for any sign of a; b below 1 is read as 1. Written, like the GLSL, with % only on
    non-negative operands (the one case GLSL ES 3.00 defines), so the twin and the shader take the same path."""
    a = np.asarray(a, dtype=np.int64)
    b = np.maximum(np.asarray(b, dtype=np.int64), 1)
    below = -(a + 1)                                   # >= 0 when a < 0, and no overflow at the most negative int
    r = np.where(a >= 0, np.abs(a) % b, b - 1 - (np.abs(below) % b))
    r = r.astype(np.int32)
    return int(r) if r.ndim == 0 else r


def cellIndex(x):
    """int(floor(x)): the cell a coordinate is in, also for negative x."""
    r = np.floor(_f(x)).astype(np.int32)
    return int(r) if r.ndim == 0 else r


# ---------------------------------------------------------------------------------------------- core/compile.glsl
def unrollBarrier(n, frame):
    """n + min(frame, 0): n for every real frame number, which only the GPU compiler cannot see."""
    return n + min(frame, 0)


# ---------------------------------------------------------------------------------------------- core/clock.glsl
def clkPhase(tWrapped, hz):
    """fract(hz * t) in cycles, float32 like the GPU (for t, hz >= 0 the result is in [0, 1))."""
    x = (_f(hz) * _f(tWrapped)).astype(F32)
    return _scalar((x - np.floor(x)).astype(F32))


def clkKeep(keepPerSecond, dt):
    """pow(keepPerSecond, dt): the per-frame factor of a decay specified per second. No time keeps everything; a keep
    of zero (or less) loses everything after any time at all."""
    k, dt = _f(keepPerSecond), _f(dt)
    with np.errstate(divide="ignore", over="ignore", under="ignore", invalid="ignore"):
        powed = np.power(np.where(k > 0, k, F32(1)), dt).astype(F32)
    return _scalar(np.where(dt <= 0, F32(1), np.where(k <= 0, F32(0), powed)).astype(F32))


def clkAlpha(dt, tau):
    """1 - exp(-dt / tau): the blend weight of a one-pole smoother (an RC low-pass) with time constant tau seconds."""
    dt, tau = _f(dt), _f(tau)
    with np.errstate(over="ignore", under="ignore"):
        return _scalar((F32(1) - np.exp(-np.maximum(dt, F32(0)) / np.maximum(tau, F32(1e-9)))).astype(F32))


# ---------------------------------------------------------------------------------------------- core/frame.glsl
def uvCentered(fragCoord, res):
    """Pixels from the centre, times 2 / height: origin at the centre, y from -1 to 1, x scaled by the same factor."""
    fc, res = _f(fragCoord), _f(res)
    from_centre = fc - F32(0.5) * res[..., :2]
    return (from_centre * (F32(2) / res[..., 1:2])).astype(F32)


def uvPixel(res):
    """2 / res.y: one pixel in uvCentered units."""
    return _scalar((F32(2) / _f(res)[..., 1]).astype(F32))


def uvFootprint(field):
    """The GPU's max(length(dFdx(p)), length(dFdy(p))) for a coordinate given at every pixel of an image, shape
    (height, width, 2): the change to the next pixel along each axis (forward difference, the last row and column
    repeated), measured, the larger kept."""
    p = _f(field)
    across_x = np.diff(p, axis=1, append=p[:, -1:] + (p[:, -1:] - p[:, -2:-1]))
    across_y = np.diff(p, axis=0, append=p[-1:] + (p[-1:] - p[-2:-1]))
    widest = np.maximum(np.sum(across_x * across_x, -1), np.sum(across_y * across_y, -1))
    return np.sqrt(widest).astype(F32)


# ---------------------------------------------------------------------------------------------- debug/views.glsl
LUMA709 = np.array([0.2126, 0.7152, 0.0722], dtype=F32)   # ITU-R BT.709 weights: how bright each primary looks
MAGENTA = np.array([1, 0, 1], dtype=F32)
CYAN = np.array([0, 1, 1], dtype=F32)
BLUE = np.array([0, 0, 1], dtype=F32)
RED = np.array([1, 0, 0], dtype=F32)
WHITE = np.array([1, 1, 1], dtype=F32)

# The heat ramp's five stops, display-referred: black, violet, red-orange, amber, white. Their Rec. 709 luma is 0,
# 0.25, 0.50, 0.75, 1, so brightness climbs in even steps and (each step linear) never dips between them.
HEAT_STOPS = np.array([[0.00, 0.00, 0.00],
                       [0.40, 0.15, 0.85],
                       [1.00, 0.38, 0.25],
                       [1.00, 0.74, 0.20],
                       [1.00, 1.00, 1.00]], dtype=F32)


def dbgHeatRamp(t):
    """Piecewise-linear through HEAT_STOPS, as the GLSL's chain of mix() calls: each stop takes over across its
    quarter of [0, 1]."""
    s = (np.clip(_f(t), 0, 1) * F32(4))[..., None]
    col = np.broadcast_to(HEAT_STOPS[0], s.shape[:-1] + (3,)).astype(F32)
    for i in range(1, 5):
        w = np.clip(s - F32(i - 1), 0, 1)
        col = _mix(col, HEAT_STOPS[i], w)
    return col


def dbgHeatCount(count, budget):
    count, budget = _f(count), _f(budget)
    ramp = dbgHeatRamp(count / np.maximum(budget, F32(1e-6)))
    return np.where((count > budget)[..., None], MAGENTA, ramp).astype(F32)


def _bits(c):
    return np.ascontiguousarray(_f(c)).view(np.int32) & 0x7FFFFFFF


def dbgRangeScope(c):
    """Magenta for NaN, cyan for Inf, blue for negative, red above 1, else a grey that keeps the picture readable; the
    first that applies to any of the four channels wins, in that order."""
    c = _f(c)
    b = _bits(c)
    nan = np.any(b > 0x7F800000, axis=-1)
    inf = np.any(b == 0x7F800000, axis=-1)
    with np.errstate(invalid="ignore"):
        neg = np.any(c < 0, axis=-1)
        over = np.any(c > 1, axis=-1)
    grey = (F32(0.2) + F32(0.6) * np.clip(c[..., :3] @ LUMA709, 0, 1))[..., None] * np.ones(3, F32)
    out = np.where(over[..., None], RED, grey)
    out = np.where(neg[..., None], BLUE, out)
    out = np.where(inf[..., None], CYAN, out)
    return np.where(nan[..., None], MAGENTA, out).astype(F32)


def dbgNaN(c):
    c = _f(c)
    bad = np.any(_exponent_all_ones(c), axis=-1)
    return np.where(bad[..., None], MAGENTA, c).astype(F32)


def _linstep(a, b, x):
    along, span = x - a, b - a
    return np.clip(along / span, 0, 1)


def _smoothstep(a, b, x):
    t = _linstep(a, b, x)
    return t * t * (3 - 2 * t)


SLICE_INSIDE = np.array([0.92, 0.55, 0.22], dtype=F32)    # warm: the field is negative (inside the shape)
SLICE_OUTSIDE = np.array([0.25, 0.55, 0.92], dtype=F32)   # cool: positive (outside)


def dbgSlice(d, spacing, px):
    """The GLSL computes px = fwidth(d) itself; the twin is handed it. Warm inside, cool outside, darker with
    distance; a light iso-line every `spacing` (faded out once lines would be under 6 px apart, so a zoomed-out view
    shows tint rather than moire); a white zero line."""
    d, px = _f(d), np.maximum(_f(px), F32(1e-6))
    gap = np.maximum(_f(spacing), F32(1e-6))
    side = np.where((d < 0)[..., None], SLICE_INSIDE, SLICE_OUTSIDE)
    base = side * (F32(0.4) + F32(0.25) * np.exp(-np.abs(d) / (F32(3) * gap)))[..., None]
    band = d / gap + F32(0.5)
    ring = np.abs(band - np.floor(band) - F32(0.5)) * gap
    line_ink = (1 - _smoothstep(0.5 * px, 1.5 * px, ring)) * _smoothstep(3 * px, 6 * px, gap)
    zero_ink = 1 - _smoothstep(0.75 * px, 2 * px, np.abs(d))
    col = _mix(base, _mix(side, WHITE, F32(0.35)), line_ink[..., None])
    return _mix(col, WHITE, zero_ink[..., None])


R2 = np.array([0.7548776662466927, 0.5698402909980532], dtype=F32)   # 1/g and 1/g^2, g the plastic number


def dbgCells(local, cellId, period, px):
    """Local coordinate as red and green (0 at the cell's low edge, 1 at its high edge), the cell's id as a tint that
    differs between neighbours (a step of the R2 low-discrepancy sequence around a cosine hue wheel), and a white
    border one pixel wide."""
    local, cellId, period, px = _f(local), _f(cellId), _f(period), _f(px)
    at = local / period + F32(0.5)
    wheel = cellId @ R2
    wheel = wheel - np.floor(wheel)
    tint = F32(0.5) + F32(0.5) * np.cos(TAU * wheel[..., None] + np.array([0, 2, 4], dtype=F32) * (PI / F32(3)))
    col = F32(0.55) * np.concatenate([at, np.zeros(at.shape[:-1] + (1,), F32)], -1) + F32(0.45) * tint
    to_edge = F32(0.5) * period - np.abs(local)
    edge = np.min(to_edge, axis=-1)
    ink = 1 - _smoothstep(0.5 * px, 1.5 * px, edge)
    return _mix(col, WHITE, ink[..., None])
