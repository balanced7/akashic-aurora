"""CPU twin of noise/triangle.glsl: the triangle filament noise, octaves of a bent triangle wave on a turned, slowly
churning domain. Pinned by tests/test_glsl_twins_2d.py.

WHY. The aurora's band and sheet tiers evaluate their footprint field dozens of times a pixel, so it must be pure
arithmetic (no texture, no hash) and it must have thin creases that a steep transfer can light as filaments. A twin in
float32 lets a test measure what the eye cannot from one picture: that the field stays in [0, 1] centred on a half, that
its creases are a thin set, that the triangle waves' period never shows as a lattice, and that one octave turns back
on itself exactly every 4 pi of the churn clock.

The same name as the GLSL function; float32 like the GPU. Apache-2.0, Akashic Aurora. Written fresh from the
mathematics; no corpus code.
"""

from __future__ import annotations

import numpy as np

from .shaping import shpTri

F32 = np.float32
PHI = F32(1.61803398874989484820)
OCTAVE_COS, OCTAVE_SIN = F32(np.cos(1.0)), F32(np.sin(1.0))  # the octaves turn by one radian
WARP_COS, WARP_SIN = F32(np.cos(1.1)), F32(np.sin(1.1))  # the warp's coordinate starts turned by 1.1 rad
WARP_SCALE = F32(0.43)  # ... and 0.43 as fine as p
WARP_STRIDE = F32(1.41)
WARP_AMOUNT = F32(1.2)
BEND = F32(0.5)
GAIN = F32(0.5)
SPIN_RATE, SPIN_STEP = F32(0.5), F32(-1.37)  # radians per unit of t, and the per-octave factor
Q_STEP = np.array([0.31, -0.47], dtype=F32)
W_STEP = np.array([-0.23, 0.19], dtype=F32)


def _turn(v, c, s):
    return np.stack([c * v[..., 0] - s * v[..., 1], s * v[..., 0] + c * v[..., 1]], -1).astype(F32)


def noiseTriangle2(p, t, octaves):
    """The filament field in [0, 1]: sum over min(octaves, 8) octaves of 0.5^i * shpTri(q.x + 0.5 shpTri(q.y)), over the
    sum of 0.5^i, where q is p pushed by a warp field read on a slower, differently turned copy of p. Fewer than one
    octave is the field's mean, 0.5."""
    p = np.asarray(p, dtype=F32)
    n = min(int(octaves), 8)
    if n < 1:
        return F32(0.5) if p.ndim == 1 else np.full(p.shape[:-1], F32(0.5))
    q = p.copy()
    w = _turn(p, WARP_COS, WARP_SIN) * WARP_SCALE
    total = np.zeros(p.shape[:-1], F32)
    amp, amp_sum = F32(1), F32(0)
    spin = F32(SPIN_RATE * F32(t))
    for _ in range(n):
        field = np.stack(
            [
                shpTri(w[..., 0] + BEND * shpTri(w[..., 1])) - F32(0.5),
                shpTri(w[..., 1] + BEND * shpTri(w[..., 0])) - F32(0.5),
            ],
            -1,
        ).astype(F32)
        q = q + WARP_AMOUNT * _turn(field, np.cos(spin, dtype=F32), np.sin(spin, dtype=F32))
        total = total + amp * shpTri(q[..., 0] + BEND * shpTri(q[..., 1]))
        amp_sum = amp_sum + amp
        amp = amp * GAIN
        q = _turn(q, OCTAVE_COS, OCTAVE_SIN) * PHI + Q_STEP
        w = _turn(w, OCTAVE_COS, -OCTAVE_SIN) * WARP_STRIDE + W_STEP
        spin = F32(spin * SPIN_STEP)
    out = (total / amp_sum).astype(F32)
    return out[()] if out.ndim == 0 else out
