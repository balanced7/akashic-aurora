"""CPU twin of the 2D drawing modules (atlas family C, arsenal/web/glsl/draw2/): exact 2D distances (sdf2.glsl),
coverage from a distance (aa.glsl), polar coordinates, repetition and the kaleidoscope (domain2.glsl), the pointy-top
hex lattice (lattice.glsl) and the per-cell delay (pattern.glsl). Pinned by tests/test_glsl_twins_2d.py.

WHY. Every edge the house draws goes through these parts, so they are the ruler and the pen of every surface: a box
distance that is only a bound, a stroke whose ink is not the line's true width, or a hex id that changes inside its
own cell would show on every page at once, and a shader cannot print a number to say so. This file is the same maths
on the CPU in float32, like the GPU, so a test can hold each function to a brute-force reference. The bench multimeter
beside the oscilloscope.

Names match the GLSL names exactly (a grep for `latHex` finds both halves). Two departures, each because a CPU has to
be handed what a GPU reads for itself, or cannot write through an argument:
  * aaStep takes a third argument, `footprint`: the per-pixel change of x that the GLSL measures with dFdx and dFdy.
  * the domain operators that take `inout vec2 p` (domRepeat2, domKaleido) return a pair: (what the GLSL returns,
    the new p).
Everything works element-wise on arrays whose last axis holds the vector components.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; no corpus code.
"""
from __future__ import annotations

import numpy as np

F32 = np.float32
PI = F32(3.14159265358979323846)
TAU = F32(6.28318530717958647692)
SQRT3 = F32(1.73205080756887729353)


def _f(x):
    return np.asarray(x, dtype=F32)


def _scalar(x):
    """A 0-d result comes back as a numpy scalar, so `twin(0.5) == 1.0` reads naturally in a test."""
    x = np.asarray(x, dtype=F32)
    return x[()] if x.ndim == 0 else x


def _length(v):
    return np.sqrt(np.sum(v * v, axis=-1, dtype=F32)).astype(F32)


def _dot(a, b):
    return np.sum(a * b, axis=-1, dtype=F32).astype(F32)


# ---------------------------------------------------------------------------------------------- draw2/sdf2.glsl
def sd2Circle(p, r):
    """|p| - r: exact, negative inside."""
    return _scalar(_length(_f(p)) - _f(r))


def sd2Box(p, halfSize):
    """Fold into the first quadrant; q = |p| - halfSize. Outside: the length of q's positive part; inside: its largest
    (negative) component."""
    q = np.abs(_f(p)) - _f(halfSize)
    outside = _length(np.maximum(q, F32(0)))
    inside = np.minimum(np.maximum(q[..., 0], q[..., 1]), F32(0))
    return _scalar(outside + inside)


def sd2RoundBox(p, halfSize, cornerRadius):
    """The box shrunk by the corner radius, then grown by it again as a rounding: the outer extent stays halfSize.
    The radius is held in [0, the shorter half-size]."""
    half = _f(halfSize)
    r = np.clip(_f(cornerRadius), F32(0), np.min(half, axis=-1))
    q = np.abs(_f(p)) - half + r[..., None]
    outside = _length(np.maximum(q, F32(0)))
    inside = np.minimum(np.maximum(q[..., 0], q[..., 1]), F32(0))
    return _scalar(outside + inside - r)


def sd2Segment(p, a, b):
    """(distance, parameter): the parameter is the clamped projection of p on a -> b, 0 at a and 1 at b; a segment of
    zero length is its point (parameter 0)."""
    p, a, b = _f(p), _f(a), _f(b)
    pa, ba = p - a, b - a
    h = np.clip(_dot(pa, ba) / np.maximum(_dot(ba, ba), F32(1e-30)), F32(0), F32(1))
    gap = pa - ba * h[..., None]
    return np.stack([_length(gap), np.broadcast_to(h, gap.shape[:-1])], -1).astype(F32)


HEX_MIRROR = np.array([-0.5, 0.8660254037844386], dtype=F32)   # the normal of the mirror at 30 degrees


def sd2Hexagon(p, inradius):
    """Pointy-top hexagon of the given inradius (flat sides at x = +-inradius, vertices straight up and down). Folded
    by its symmetry into the wedge from 0 to 30 degrees, where the nearest boundary is the right-hand flat side or its
    upper vertex: abs() into the first quadrant, reflect across the 30-degree mirror, abs() of y once more."""
    q = np.abs(_f(p))
    a = _f(inradius)
    q = q - F32(2) * np.maximum(_dot(q, HEX_MIRROR), F32(0))[..., None] * HEX_MIRROR
    q = np.stack([q[..., 0], np.abs(q[..., 1])], -1)
    half_edge = a / SQRT3
    nearest = np.stack([np.broadcast_to(a, q.shape[:-1]), np.clip(q[..., 1], -half_edge, half_edge)], -1)
    return _scalar(_length(q - nearest) * np.sign(q[..., 0] - a))


# ---------------------------------------------------------------------------------------------- draw2/aa.glsl
def aaFill(d, px):
    """clamp(0.5 - d / px, 0, 1): the box-filtered coverage of the inside of a straight edge, one pixel of ramp. The
    pixel size is floored at 1e-6 (no pixel size is a hard edge, never a division by zero)."""
    d, px = _f(d), np.maximum(_f(px), F32(1e-6))
    with np.errstate(over="ignore"):
        return _scalar(np.clip(F32(0.5) - d / px, F32(0), F32(1)))


def aaStroke(d, halfWidth, px):
    """The band |d| <= halfWidth, box filtered: the coverage inside its outer edge minus the coverage inside its inner
    edge. Its ink (the integral over d) is exactly 2 * halfWidth, so a band thinner than a pixel fades instead of
    breaking. A negative half-width is no band."""
    hw = np.maximum(_f(halfWidth), F32(0))
    d = _f(d)
    return _scalar(_f(aaFill(d - hw, px)) - _f(aaFill(d + hw, px)))


def aaWire(d, widthPx, px):
    """Phone-wire antialiasing: the line is drawn at least one pixel wide and its opacity is true width / drawn width,
    so a hairline keeps its ink and stays connected."""
    w = np.maximum(_f(widthPx), F32(0))
    drawn = np.maximum(w, F32(1))
    return _scalar(_f(aaStroke(d, F32(0.5) * drawn * _f(px), px)) * (w / drawn))


def aaStep(x, edge, footprint):
    """The GLSL measures footprint itself as the length of (dFdx(x), dFdy(x)); the twin is handed it. A smoothstep from
    edge - footprint to edge + footprint, written out (floored at 1e-30, so a flat field is a clean hard step)."""
    x, edge = _f(x), _f(edge)
    fp = np.maximum(_f(footprint), F32(1e-30))
    with np.errstate(over="ignore", invalid="ignore"):
        t = np.clip(F32(0.5) + F32(0.5) * (x - edge) / fp, F32(0), F32(1))
    return _scalar(t * t * (F32(3) - F32(2) * t))


# ---------------------------------------------------------------------------------------------- draw2/domain2.glsl
def domToPolar(p):
    """(radius, angle) with the angle in (-pi, pi]; the origin gets angle 0 (atan(0, 0) is undefined in GLSL)."""
    p = _f(p)
    x, y = p[..., 0], p[..., 1]
    origin = (x == 0) & (y == 0)
    a = np.arctan2(y, np.where(origin, F32(1), x)).astype(F32)
    a = np.where(a <= -PI, PI, a)
    return np.stack([_length(p), a], -1).astype(F32)


def domFromPolar(ra):
    ra = _f(ra)
    r, a = ra[..., 0], ra[..., 1]
    return np.stack([r * np.cos(a), r * np.sin(a)], -1).astype(F32)


def domRepeat2(p, period):
    """Centred repetition. Returns (cell id, local p): id = floor(p / period + 0.5), local = p - id * period, in
    [-period / 2, period / 2). The period is floored at 1e-6 per axis."""
    p = _f(p)
    size = np.maximum(_f(period), F32(1e-6))
    cell = np.floor(p / size + F32(0.5)).astype(F32)
    return cell, (p - cell * size).astype(F32)


def domKaleido(p, sectors):
    """Returns (sector index in [0, n), folded p). n = max(round(sectors), 1) sectors of width TAU / n, sector 0 centred
    on +x; the angle is taken relative to its sector's centre line and folded with abs(), so the folded point lies
    between angle 0 and half a sector and adjacent sectors are mirror images."""
    n = np.maximum(np.floor(_f(sectors) + F32(0.5)), F32(1))
    width = TAU / n
    ra = domToPolar(p)
    index = np.floor(ra[..., 1] / width + F32(0.5)).astype(F32)
    local = np.abs(ra[..., 1] - index * width)
    folded = domFromPolar(np.stack([ra[..., 0], local], -1))
    return (index - n * np.floor(index / n)).astype(F32), folded


# ---------------------------------------------------------------------------------------------- draw2/lattice.glsl
HEX_ROW = np.array([1.0, SQRT3], dtype=F32)            # one cell of each rectangular grid
HEX_SHIFT = np.array([0.5, 0.5 * SQRT3], dtype=F32)    # where the second grid's centres sit


def latHex(p):
    """Pointy-top hexagons, centres 1 apart, by two rectangular grids: the nearer of the two grids' centres wins (the
    first grid on a tie). Returns (offset from that centre, the centre) as (x, y, z, w)."""
    p = _f(p)
    centre_a = (HEX_ROW * np.floor(p / HEX_ROW + F32(0.5))).astype(F32)
    centre_b = (HEX_ROW * np.floor((p - HEX_SHIFT) / HEX_ROW + F32(0.5)) + HEX_SHIFT).astype(F32)
    off_a, off_b = p - centre_a, p - centre_b
    near_a = (_dot(off_a, off_a) <= _dot(off_b, off_b))[..., None]
    return np.concatenate([np.where(near_a, off_a, off_b), np.where(near_a, centre_a, centre_b)], -1).astype(F32)


def latHexEdge(offset):
    """0.5 - max(|x|, |x| / 2 + sqrt3 / 2 |y|): the distance from a hex offset to its cell's border (0.5 at the centre,
    0 on the border); inside the cell it equals -sd2Hexagon(offset, 0.5)."""
    o = np.abs(_f(offset))
    norm = np.maximum(o[..., 0], F32(0.5) * o[..., 0] + F32(0.5) * SQRT3 * o[..., 1])
    return _scalar(F32(0.5) - norm)


def latHexAxial(centre):
    """The integer axial pair (q, r) of a centre: centre = q (1, 0) + r (1/2, sqrt3 / 2), rounded."""
    c = _f(centre)
    r = c[..., 1] * (F32(2) / SQRT3)
    q = c[..., 0] - F32(0.5) * r
    return np.floor(np.stack([q, r], -1) + F32(0.5)).astype(F32)


def latHexSteps(a, b):
    """Hex steps between two axial pairs: the largest of |dq|, |dr| and |dq + dr| (cube coordinates' third axis)."""
    d = _f(b) - _f(a)
    return _scalar(np.maximum(np.maximum(np.abs(d[..., 0]), np.abs(d[..., 1])), np.abs(d[..., 0] + d[..., 1])))


# ---------------------------------------------------------------------------------------------- draw2/pattern.glsl
def patCellDelay(cellId, centre, speed):
    """|cellId - centre| / speed, the speed floored at 1e-6: whole cells share one delay."""
    return _scalar(_length(_f(cellId) - _f(centre)) / np.maximum(_f(speed), F32(1e-6)))
