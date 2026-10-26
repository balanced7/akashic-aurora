"""CPU twin of core/shaping.glsl: the vocabulary of curves (ramps, impulses, pulses, gain, bumps, the soft absolute
value, the triangle wave, the remap and the inverse power). Pinned by tests/test_glsl_twins_core.py.

WHY. Most of the "magic" in the loved shaders is a well-chosen curve applied after a dull field (atlas craft secret 3):
AURORA's filaments are an inverse power of a mild noise, Cloud Ten's cores are a remap. A curve that misses its fixed
point (a gain that does not pass through one half, an impulse that peaks above 1) quietly changes every look that uses
it, so each curve is pinned here at the points its contract names. Like checking a tone control at its detents.

float32 throughout, like the GPU; names match the GLSL names. Apache-2.0, Akashic Aurora. Written fresh from the
mathematics (Quilez's "Remapping functions" catalogue and The Book of Shaders, chapter 5, taught the family).
"""

from __future__ import annotations

import numpy as np

F32 = np.float32


def _f(x):
    return np.asarray(x, dtype=F32)


def _scalar(x):
    x = np.asarray(x, dtype=F32)
    return x[()] if x.ndim == 0 else x


def shpLinstep(a, b, x):
    """How far x has come from a, over the length from a to b, clamped to [0, 1]."""
    a, b, x = _f(a), _f(b), _f(x)
    along, span = x - a, b - a
    return _scalar(np.clip(along / span, 0, 1))


def shpSmoother(a, b, x):
    """The quintic q(r) = 10r^3 - 15r^4 + 6r^5 of the linear ramp r: flat in slope and curvature at both ends.
    Evaluated from the nearer end (q(1 - r) = 1 - q(r)): straight through, 10 + r(6r - 15) cancels to about 1 as r
    nears 1 and float32 rounding makes the last approach to 1 jitter by a millionth; from the nearer end it never
    cancels, and the curve is exactly point-symmetric."""
    r = _f(shpLinstep(a, b, x))
    near = np.minimum(r, F32(1) - r)
    tail = near * near * near * (F32(10) + near * (F32(6) * near - F32(15)))
    return _scalar(np.where(r < F32(0.5), tail, F32(1) - tail))


def shpImpulse(x, k):
    """k x e^(1 - k x): 0 at x = 0, exactly 1 at x = 1/k, then an exponential tail."""
    reach = _f(k) * _f(x)
    return _scalar(reach * np.exp(F32(1) - reach))


def shpPulse(x, centre, halfWidth):
    """1 - r^2 (3 - 2r) with r = |x - centre| / halfWidth held at 1 beyond the half width: exactly 0 out there."""
    spread = np.minimum(np.abs(_f(x) - _f(centre)) / np.maximum(_f(halfWidth), F32(1e-9)), F32(1))
    return _scalar(F32(1) - spread * spread * (F32(3) - F32(2) * spread))


def shpGain(x, k):
    """Two mirrored power curves meeting at one half: half of (2 min(x, 1 - x))^k, reflected for the upper half."""
    u = np.clip(_f(x), 0, 1)
    arm = F32(0.5) * np.power(F32(2) * np.minimum(u, F32(1) - u), _f(k))
    return _scalar(np.where(u < F32(0.5), arm, F32(1) - arm))


def shpParabola(x, k):
    """(4 x (1 - x))^k, floored at 0 outside [0, 1] (pow of a negative base is undefined on the GPU)."""
    x = _f(x)
    bump = F32(4) * x * (F32(1) - x)
    return _scalar(np.power(np.maximum(bump, F32(0)), _f(k)))


def shpSoftAbs(x, k):
    """sqrt(x^2 + k): |x| with the crease at 0 rounded; it lifts |x| by at most sqrt(k), at x = 0."""
    x = _f(x)
    squared = x * x
    return _scalar(np.sqrt(squared + _f(k)))


def shpTri(x):
    """A triangle wave of period 1: 0 at whole numbers, 1 at halves, straight in between."""
    x = _f(x)
    cycle = x - np.floor(x)
    return _scalar(F32(1) - np.abs(F32(2) * cycle - F32(1)))


def shpRemap(v, a, b, c, d):
    """The fraction of the way from a to b that v has come, laid along c to d: a maps to c, b to d, nothing clamped."""
    v, a, b, c, d = (_f(t) for t in (v, a, b, c, d))
    along = (v - a) / (b - a)
    return _scalar(c + along * (d - c))


INV_POWER_CEILING_LOG2 = F32(64)  # (r/d)^k is held at or below 2^64


def shpInvPower(d, r, k):
    """(r / d)^k as exp2(k log2(r / d)), with r and d floored at 1e-30 (d at or below zero is the very centre) and the
    exponent held at 64, so the centre is a large finite number rather than Inf."""
    ratio = np.maximum(_f(r), F32(1e-30)) / np.maximum(_f(d), F32(1e-30))
    with np.errstate(over="ignore"):
        return _scalar(np.exp2(np.minimum(_f(k) * np.log2(ratio), INV_POWER_CEILING_LOG2)))
