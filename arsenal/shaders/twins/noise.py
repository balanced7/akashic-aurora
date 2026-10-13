"""CPU twin of noise/value.glsl, noise/gradient.glsl, noise/fbm.glsl, noise/warp.glsl and noise/dither-masks.glsl.
Pinned by tests/test_glsl_twins_hash_noise.py.

WHY. Noise is the house's fabric: clouds, fire, aurora folds and marble are all a smooth random field, summed over
scales (fBm), bent by itself (a warp) and shaped by a curve. A field that quietly changes its range, grows brighter
with more octaves or keeps a grid showing changes every look built on it, so each promise is measured here on the CPU:
gradient noise is exactly zero on the lattice, both noises stay inside [-1, 1], an fBm of one octave is its base noise,
a warp of amount zero is a plain fBm. The slow parity test renders the GLSL on SwiftShader and compares it with this
twin pixel for pixel.

The noises run in float64 (the mathematical reference); the GPU's 32-bit floats agree to a few millionths. The dither
masks round like the GPU (float32 at every step), because their double fract amplifies rounding and a twin that rounded
differently would not be a twin. Points are numpy arrays whose LAST axis is the vector; seeds are ints or uint32 arrays.
GLSL `out` parameters come back as extra return values (warpNested2 returns value, q, r).

Apache-2.0, Akashic Aurora. Written fresh from the mathematics: Ken Perlin's "Improving Noise" (2002), Inigo Quilez's
articles on fBm and domain warping, F. Kenton Musgrave's fractal terrain notes, Jorge Jimenez's interleaved gradient
noise and Martin Roberts' R2 sequence, as taught by research/reviewed/shader-school-2026-10-13/noise-procedural.md.
"""
from __future__ import annotations

import math

import numpy as np

from . import hash as H

# Gradient noise. 2D: eight unit gradients at 22.5 + 45k degrees (never on an axis or a diagonal), chosen by the top
# three bits of the corner's hash. 3D: Perlin's twelve cube-edge midpoints (+-1, +-1, 0) and permutations, chosen by
# the hash modulo 12. The scales put each noise's exact supremum just under 1 (2D: 0.66082 before scaling; 3D with the
# edge set and the quintic fade: 1.03635), so neither ever leaves [-1, 1].
GRAD2_LONG, GRAD2_SHORT = math.cos(math.pi / 8.0), math.sin(math.pi / 8.0)
GRAD2_SCALE = 1.5132
GRAD3_SCALE = 0.9649

# One seed, one independent field PER KIND. Value noise, gradient noise and the 3D hash wrappers all hash with pcg3d or
# pcg4d, so each kind XORs its own tag into the seed lane; otherwise they read the same dice (value noise at seed 0 was
# exactly 2 hash31(cell, 0) - 1 on the lattice, and a value corner's sign was its gradient's y sign: batch-A review,
# defect 1). The tags are words of pi's fraction after the warps' three, and differ pairwise in bits 16-31 by a
# pattern that is neither all zeros nor all ones, so no seed or cell z of magnitude below 2^16 meets another kind.
NOISE_TAG_VALUE2 = 0x03707344
NOISE_TAG_VALUE3 = 0xA4093822
NOISE_TAG_GRAD2 = 0x299F31D0
NOISE_TAG_GRAD3 = 0x082EFA98

# fBm octave hygiene: every octave turns by the golden angle (2D) or by the golden angle about the axis (1, 2, 3) (3D),
# so no two octaves' lattices line up; its lacunarity is detuned upward by an irregular 0 to 2 per cent; it steps off
# the lattice by a fixed offset (gradient noise is zero at the origin in EVERY octave, a visible pinch without it);
# and it hashes with its own seed.
FBM_MAX_OCTAVES = 8
GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))
TURN2_C, TURN2_S = math.cos(GOLDEN_ANGLE), math.sin(GOLDEN_ANGLE)
TURN3 = np.array([[-0.61327110, -0.29340157, 0.73335808],      # rows; GLSL's mat3 takes the columns
                  [0.78979268, -0.24097777, 0.56405429],
                  [0.01122858, 0.92511904, 0.37951111]])
FBM_OFFSET2 = np.array([19.19, -7.31])
FBM_OFFSET3 = np.array([19.19, -7.31, 11.57])

# Warps: each fBm in a warp hashes with its own stream, derived from the caller's seed by hashU1 and a tag.
WARP_TAG_X, WARP_TAG_Y, WARP_TAG_FINAL = 0x243F6A88, 0x85A308D3, 0x13198A2E    # pi's first 96 fractional bits
WARP_OFFSET_Y = np.array([57.3, -21.9])     # "two fBm at far-apart offsets": where the y component is read

# Dither masks.
IGN_K = (0.06711056, 0.00583715, 52.9829189)                 # Jimenez 2014
R2_K = (0.7548776662466927, 0.5698402909980532)              # 1/rho and 1/rho^2, rho the plastic number


def _p(p):
    return np.asarray(p, dtype=np.float64)


def _seed(seed, shape):
    return np.broadcast_to(np.asarray(seed, dtype=np.uint64) & np.uint64(0xFFFFFFFF), shape).astype(np.uint32)


def _lane(seed, shape, tag):
    """The seed lane a kind hashes with: seed ^ its tag (one kind's dice never another's)."""
    return _seed(seed, shape) ^ np.uint32(tag)


def _fade(t):
    """Perlin's quintic 6t^5 - 15t^4 + 10t^3: flat in slope AND curvature at both ends, so no grid in the shading."""
    cube = t * t * t
    return cube * (10.0 + t * (6.0 * t - 15.0))


def _lerp(a, b, t):
    return a + (b - a) * t


def _corner_cells(p):
    """(cell as uint32 lanes, fractional position) for a point."""
    p = _p(p)
    base = np.floor(p)
    return H.cellU2(p), p - base


def _plus(cells, offset):
    """cells + a small integer offset per lane, wrapping like GLSL's uint addition."""
    return (cells.astype(np.uint64) + np.asarray(offset, dtype=np.uint64)).astype(np.uint64) & np.uint64(0xFFFFFFFF)


# ------------------------------------------------------------------------------------------------- value noise
def _value_corner2(cells, seed):
    words = H.pcg3d(np.concatenate([cells, seed[..., None].astype(np.uint64)], axis=-1))[..., 0]
    return 2.0 * H.u01(words) - 1.0


def noiseValue2(p, seed):
    """Signed value noise: a random value in [-1, 1) at every lattice corner (pcg3d of (cell, seed ^ NOISE_TAG_VALUE2)),
    blended by the quintic fade. Equal to its corner value on the lattice; within [-1, 1)."""
    cells, f = _corner_cells(p)
    s = _lane(seed, f.shape[:-1], NOISE_TAG_VALUE2)
    a = _value_corner2(_plus(cells, (0, 0)), s)
    b = _value_corner2(_plus(cells, (1, 0)), s)
    c = _value_corner2(_plus(cells, (0, 1)), s)
    d = _value_corner2(_plus(cells, (1, 1)), s)
    u = _fade(f)
    return _lerp(_lerp(a, b, u[..., 0]), _lerp(c, d, u[..., 0]), u[..., 1])


def _value_corner3(cells, seed):
    words = H.pcg4d(np.concatenate([cells, seed[..., None].astype(np.uint64)], axis=-1))[..., 0]
    return 2.0 * H.u01(words) - 1.0


def noiseValue3(p, seed):
    """The 3D version: eight corners hashed by pcg4d of (cell, seed ^ NOISE_TAG_VALUE3)."""
    cells, f = _corner_cells(p)
    s = _lane(seed, f.shape[:-1], NOISE_TAG_VALUE3)
    u = _fade(f)
    v = {k: _value_corner3(_plus(cells, k), s) for k in
         ((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1))}
    near = _lerp(_lerp(v[0, 0, 0], v[1, 0, 0], u[..., 0]), _lerp(v[0, 1, 0], v[1, 1, 0], u[..., 0]), u[..., 1])
    far = _lerp(_lerp(v[0, 0, 1], v[1, 0, 1], u[..., 0]), _lerp(v[0, 1, 1], v[1, 1, 1], u[..., 0]), u[..., 1])
    return _lerp(near, far, u[..., 2])


# ---------------------------------------------------------------------------------------------- gradient noise
def noiseGradRamp2(cells, corner, stream, in_cell):
    """One corner's ramp: the gradient of corner (0 or 1 per axis) of the cell, picked by the top three bits of
    pcg3d(cell + corner, stream).x, dotted with the offset from that corner. Zero AT the corner, which is why gradient
    noise crosses zero on every lattice point. `stream` is the already-tagged lane (noiseGrad2 passes seed ^ its tag)."""
    word = H.pcg3d(np.concatenate([_plus(cells, corner), stream[..., None].astype(np.uint64)], axis=-1))[..., 0]
    d = in_cell - np.asarray(corner, dtype=np.float64)
    swap = ((word >> 29) & 1).astype(bool)
    gx = np.where(swap, GRAD2_SHORT, GRAD2_LONG)
    gy = np.where(swap, GRAD2_LONG, GRAD2_SHORT)
    gx = np.where(((word >> 30) & 1).astype(bool), -gx, gx)
    gy = np.where(((word >> 31) & 1).astype(bool), -gy, gy)
    return gx * d[..., 0] + gy * d[..., 1]


def noiseGrad2(p, seed):
    """Improved Perlin gradient noise in 2D: zero on the lattice, quintic fade, within [-1, 1] (extreme about 0.9999).
    Hashes with seed ^ NOISE_TAG_GRAD2."""
    cells, f = _corner_cells(p)
    s = _lane(seed, f.shape[:-1], NOISE_TAG_GRAD2)
    r = {k: noiseGradRamp2(cells, k, s, f) for k in ((0, 0), (1, 0), (0, 1), (1, 1))}
    u = _fade(f)
    return GRAD2_SCALE * _lerp(_lerp(r[0, 0], r[1, 0], u[..., 0]), _lerp(r[0, 1], r[1, 1], u[..., 0]), u[..., 1])


def noiseGradRamp3(cells, corner, stream, in_cell):
    """One corner's ramp in 3D: Perlin's edge gradient number (pcg4d(cell + corner, stream).x mod 12): k >> 2 names
    the plane (xy, xz, yz), bits 0 and 1 the two signs. Each dot product is one add: no multiplies. `stream` is the
    already-tagged lane (noiseGrad3 passes seed ^ its tag)."""
    word = H.pcg4d(np.concatenate([_plus(cells, corner), stream[..., None].astype(np.uint64)], axis=-1))[..., 0]
    d = in_cell - np.asarray(corner, dtype=np.float64)
    k = word % np.uint32(12)
    plane = k >> 2
    s0 = np.where((k & 1).astype(bool), -1.0, 1.0)
    s1 = np.where((k & 2).astype(bool), -1.0, 1.0)
    a = np.where(plane == 2, d[..., 1], d[..., 0])
    b = np.where(plane == 0, d[..., 1], d[..., 2])
    return s0 * a + s1 * b


def noiseGrad3(p, seed):
    """Improved Perlin gradient noise in 3D (Perlin 2002: edge gradients, quintic fade), within [-1, 1]. Hashes with
    seed ^ NOISE_TAG_GRAD3."""
    cells, f = _corner_cells(p)
    s = _lane(seed, f.shape[:-1], NOISE_TAG_GRAD3)
    r = {k: noiseGradRamp3(cells, k, s, f) for k in
         ((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1))}
    u = _fade(f)
    near = _lerp(_lerp(r[0, 0, 0], r[1, 0, 0], u[..., 0]), _lerp(r[0, 1, 0], r[1, 1, 0], u[..., 0]), u[..., 1])
    far = _lerp(_lerp(r[0, 0, 1], r[1, 0, 1], u[..., 0]), _lerp(r[0, 1, 1], r[1, 1, 1], u[..., 0]), u[..., 1])
    return GRAD3_SCALE * _lerp(near, far, u[..., 2])


# ----------------------------------------------------------------------------------------------------- fractal sums
def gainFromHurst(hurst, lacunarity):
    """lacunarity^(-hurst): H = 1 gives 0.5 at L = 2 (mountains and clouds), H = 0.5 gives 0.707 (brown)."""
    return np.power(np.asarray(lacunarity, dtype=np.float64), -np.asarray(hurst, dtype=np.float64))[()]


def fbmDetune(i):
    """Octave i's lacunarity multiplier: 1 + 0.02 * fract(0.618... * (i + 1)), an irregular 0 to 2 per cent."""
    return 1.0 + 0.02 * ((0.6180339887 * (i + 1)) % 1.0)


def _octave_seed(seed, i, shape):
    return ((_seed(seed, shape).astype(np.uint64) + np.uint64(i)) & np.uint64(0xFFFFFFFF)).astype(np.uint32)


def fbmGrad2(p, octaves, lacunarity, gain, seed):
    """Normalised fBm of noiseGrad2: the sum of gain^i * noise(octave i) divided by the sum of gain^i, i.e. by
    (1 - G^n)/(1 - G), so its range stays inside [-1, 1] whatever the octave count. At most 8 octaves (the GLSL loop's
    constant ceiling); 0 or fewer gives 0."""
    q = _p(p).copy()
    shape = q.shape[:-1]
    total, amp, amps = np.zeros(shape), 1.0, 0.0
    for i in range(min(int(octaves), FBM_MAX_OCTAVES)):
        total = total + amp * noiseGrad2(q, _octave_seed(seed, i, shape))
        amps += amp
        amp *= gain
        step = lacunarity * fbmDetune(i)
        x, y = q[..., 0], q[..., 1]
        q = np.stack([(TURN2_C * x - TURN2_S * y) * step, (TURN2_S * x + TURN2_C * y) * step], axis=-1) + FBM_OFFSET2
    return total / amps if amps > 0 else total


def fbmGrad3(p, octaves, lacunarity, gain, seed):
    """The 3D version: the golden-angle turn about the axis (1, 2, 3) between octaves."""
    q = _p(p).copy()
    shape = q.shape[:-1]
    total, amp, amps = np.zeros(shape), 1.0, 0.0
    for i in range(min(int(octaves), FBM_MAX_OCTAVES)):
        total = total + amp * noiseGrad3(q, _octave_seed(seed, i, shape))
        amps += amp
        amp *= gain
        q = (q @ TURN3.T) * (lacunarity * fbmDetune(i)) + FBM_OFFSET3
    return total / amps if amps > 0 else total


# ------------------------------------------------------------------------------------------------------------ warps
def _stream(seed, tag):
    return H.hashU1((np.asarray(seed, dtype=np.uint64) ^ np.uint64(tag)) & np.uint64(0xFFFFFFFF))


def warpFinalSeed(seed):
    """The stream of the LAST fBm in warpFbm2 and warpNested2 (twin-only helper; the GLSL writes it inline)."""
    return _stream(seed, WARP_TAG_FINAL)


def warpVec2(p, octaves, seed):
    """A 2D displacement with two decorrelated components: two fBm (lacunarity 2, gain 0.5) read at far-apart offsets
    and hashed with unrelated streams. Each component is within [-1, 1], typically within +-0.5."""
    p = _p(p)
    x = fbmGrad2(p, octaves, 2.0, 0.5, _stream(seed, WARP_TAG_X))
    y = fbmGrad2(p + WARP_OFFSET_Y, octaves, 2.0, 0.5, _stream(seed, WARP_TAG_Y))
    return np.stack([x, y], axis=-1)


def warpFbm2(p, amount, octaves, seed):
    """One-level warp: fbm(p + amount * warpVec2(p)). Three fBm calls."""
    p = _p(p)
    return fbmGrad2(p + amount * warpVec2(p, octaves, seed), octaves, 2.0, 0.5, warpFinalSeed(seed))


def warpNested2(p, amount, octaves, seed):
    """Two-level warp (five fBm calls): q = warpVec2(p), r = warpVec2(p + amount q) on the next seed, value =
    fbm(p + amount r). Returns (value, q, r): q and r are free colour data (how far and which way the fabric moved)."""
    p = _p(p)
    q = warpVec2(p, octaves, seed)
    r = warpVec2(p + amount * q, octaves, (np.asarray(seed, dtype=np.uint64) + 1) & 0xFFFFFFFF)
    return fbmGrad2(p + amount * r, octaves, 2.0, 0.5, warpFinalSeed(seed)), q, r


# ------------------------------------------------------------------------------------------------------ dither masks
F32 = np.float32


def _fract32(x):
    x = np.asarray(x, dtype=F32)
    return (x - np.floor(x)).astype(F32)


def dthIgn(pixel):
    """Jimenez's interleaved gradient noise, fract(52.98 * fract(dot((0.0671, 0.00584), pixel))), in [0, 1), rounded
    like the GPU (float32 at every step). Static: the same pixel always gets the same value."""
    p = np.asarray(pixel, dtype=np.float64).astype(F32)
    ramp = _fract32(F32(IGN_K[0]) * p[..., 0] + F32(IGN_K[1]) * p[..., 1])
    return _fract32(F32(IGN_K[2]) * ramp).astype(np.float64)


def dthR2(pixel):
    """Roberts' R2 mask on the integer pixel: fract(fract(x / rho) + fract(y / rho^2)), each axis reduced before the
    sum so 32-bit floats stay within a few ten-thousandths out to an 8K canvas."""
    cell = np.floor(np.asarray(pixel, dtype=np.float64)).astype(F32)
    a = _fract32(cell[..., 0] * F32(R2_K[0]))
    b = _fract32(cell[..., 1] * F32(R2_K[1]))
    return _fract32(a + b).astype(np.float64)


def dthTriFromUniform(u):
    """The triangle distribution's inverse CDF: a uniform u in [0, 1) becomes a triangular value in [-1, 1) with the
    same RANK, so a blue or low-discrepancy mask keeps its spatial pattern while its histogram becomes a triangle."""
    u = np.clip(np.asarray(u, dtype=np.float64), 0.0, 1.0)      # as the GLSL clamps: never a NaN under the root
    out = np.where(u < 0.5, np.sqrt(2.0 * u) - 1.0, 1.0 - np.sqrt(2.0 - 2.0 * u))
    return out[()] if out.ndim == 0 else out
