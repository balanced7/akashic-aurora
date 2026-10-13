"""CPU twin of hash/pcg.glsl and legacy/hash-sine.glsl: the dice under every procedural picture.
Pinned by tests/test_glsl_twins_hash_noise.py.

WHY. A GPU runs millions of pixels at once and pixel 1000 cannot wait for pixel 999, so graphics does not draw random
numbers from a sequence; it HASHES an address (a pixel, a lattice corner, a seed) straight to a number. A good hash is
like the bank-scrambling function in a DRAM controller: neighbouring addresses must land in unrelated places, or the
picture shows stripes. The house hash is integer arithmetic (Jarzynski and Olano's PCG family, JCGT 2020), so it gives
the same bits on every GPU; this twin gives the same bits again on the CPU, which is how a test that cannot see a
screen can still prove the dice are fair.

Integer maths runs in uint64 and is masked back to 32 bits after every multiply (two 32-bit factors never overflow 64
bits), so the results are bit-exact with GLSL's wrapping uint arithmetic. Vectors are numpy arrays whose LAST axis is
the vector (shape (..., 3) for a uvec3); scalars work too. Names match the GLSL names, so one grep finds both halves.

The sine hash (hashSine21, hashSine31) is the house's OLD dice, kept only so a surface can adopt the library without a
pixel moving. Its twin rounds like a 32-bit GPU but takes the sine exactly; real GPUs compute that sine differently
from one another, which is exactly why it is legacy.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics: Jarzynski and Olano's description of pcg3d and pcg4d,
Melissa O'Neill's PCG output permutation, and the research report research/reviewed/shader-school-2026-10-13/
noise-procedural.md sections 2.3 and 2.4.
"""
from __future__ import annotations

import numpy as np

MASK = np.uint64(0xFFFFFFFF)
LCG_MUL, LCG_ADD = np.uint64(1664525), np.uint64(1013904223)        # Numerical Recipes' LCG: pcg3d and pcg4d
PCG_MUL, PCG_ADD = np.uint64(747796405), np.uint64(2891336453)      # PCG's 32-bit LCG step
PCG_OUT_MUL = np.uint64(277803737)                                  # PCG's RXS-M-XS output multiplier
TAG_2D = 0x9E3779B9      # the third lane of the 2D wrappers (2^32 / golden ratio), so 2D never repeats a 3D slice
# XORed into the 3D wrappers' z lane (a word of pi's fraction, as the noise and warp tags are): without it hash31 of
# (cell, z) read the same dice as value and gradient noise at seed z, and as any direct pcg3d caller with a small lane.
TAG_3D = 0xEC4E6C89
SINE_K2 = (127.1, 311.7)
SINE_K3 = (127.1, 311.7, 74.7)
SINE_SCALE = 43758.5453123   # the same 32-bit float as the 43758.5453 some files write


def _u64(x):
    return np.asarray(x).astype(np.uint64) & MASK


def _u32(x):
    return (np.asarray(x, dtype=np.uint64) & MASK).astype(np.uint32)


def hashU1(x):
    """One 32-bit word in, one out: one PCG LCG step, then the output permutation (a right shift chosen by the top
    four bits, a multiply, a fold of the high bits down). A bijection on 32 bits with full avalanche."""
    lcg = (_u64(x) * PCG_MUL + PCG_ADD) & MASK
    mixed = (((lcg >> ((lcg >> np.uint64(28)) + np.uint64(4))) ^ lcg) * PCG_OUT_MUL) & MASK
    return _u32((mixed >> np.uint64(22)) ^ mixed)


def pcg3d(v):
    """Three lanes in, three out: an LCG step on every lane, each lane adds the product of the other two, the high
    halves fold down (xor with a 16-bit right shift), and the lanes cross-multiply once more."""
    lane = (_u64(v) * LCG_MUL + LCG_ADD) & MASK
    x, y, z = lane[..., 0], lane[..., 1], lane[..., 2]
    for fold in (True, False):
        x = (x + y * z) & MASK
        y = (y + z * x) & MASK
        z = (z + x * y) & MASK
        if fold:
            x, y, z = x ^ (x >> np.uint64(16)), y ^ (y >> np.uint64(16)), z ^ (z >> np.uint64(16))
    return _u32(np.stack([x, y, z], axis=-1))


def pcg4d(v):
    """Four lanes in, four out: pcg3d's recipe with the cyclic four-lane cross-multiply (x takes y times w)."""
    lane = (_u64(v) * LCG_MUL + LCG_ADD) & MASK
    x, y, z, w = lane[..., 0], lane[..., 1], lane[..., 2], lane[..., 3]
    for fold in (True, False):
        x = (x + y * w) & MASK
        y = (y + z * x) & MASK
        z = (z + x * y) & MASK
        w = (w + y * z) & MASK
        if fold:
            x, y = x ^ (x >> np.uint64(16)), y ^ (y >> np.uint64(16))
            z, w = z ^ (z >> np.uint64(16)), w ^ (w >> np.uint64(16))
    return _u32(np.stack([x, y, z, w], axis=-1))


def u01(x):
    """The top 24 bits over 2^24: a float in [0, 1) that a 32-bit float holds exactly and that never reaches 1.0
    (scaling all 32 bits by 2^-32 rounds the largest words up to exactly 1.0). Works lane by lane on any shape."""
    return (_u64(x) >> np.uint64(8)).astype(np.float64) * (1.0 / 16777216.0)


def cellU2(p):
    """floor(p) as two uint lanes: a negative cell wraps by two's complement (-1 is 0xFFFFFFFF), so it hashes fine."""
    return _u32(np.floor(np.asarray(p, dtype=np.float64)).astype(np.int64))


def cellU3(p):
    return cellU2(p)


def _with_lane(cells, lane_value):
    cells = np.asarray(cells, dtype=np.uint32)
    extra = np.full(cells.shape[:-1] + (1,), lane_value, dtype=np.uint32)
    return np.concatenate([cells, extra], axis=-1)


def hash21(p):
    """[0, 1) for the cell of a 2D point: pcg3d of (cell, TAG_2D), first lane. The 2D wrappers and the 3D ones meet
    only at z = TAG_2D ^ TAG_3D = 0x72791530, a cell no float32 can floor to (it is not a multiple of 128)."""
    return u01(pcg3d(_with_lane(cellU2(p), TAG_2D))[..., 0])


def hash22(p):
    return u01(pcg3d(_with_lane(cellU2(p), TAG_2D))[..., :2])


def _tagged_cell3(p):
    """The cell of a 3D point with TAG_3D XORed into its z lane: the 3D wrappers' own dice."""
    cells = cellU3(p).copy()
    cells[..., 2] ^= np.uint32(TAG_3D)
    return cells


def hash31(p):
    """[0, 1) for the cell of a 3D point: pcg3d of (cell.x, cell.y, cell.z ^ TAG_3D), first lane (hash33's .x)."""
    return u01(pcg3d(_tagged_cell3(p))[..., 0])


def hash33(p):
    return u01(pcg3d(_tagged_cell3(p)))


def _sine_hash(p, k, scale):
    """fract(sin(dot(k, p)) * scale), rounded like a 32-bit GPU at every step except the sine itself."""
    p = np.asarray(p, dtype=np.float64).astype(np.float32)
    phase = np.float32(k[0]) * p[..., 0]
    for i in range(1, len(k)):
        phase = (phase + np.float32(k[i]) * p[..., i]).astype(np.float32)
    wave = np.sin(phase.astype(np.float64)).astype(np.float32)
    big = (wave * np.float32(scale)).astype(np.float32)
    return (big - np.floor(big)).astype(np.float32).astype(np.float64)


def hashSine21(p):
    """LEGACY. The house's 2D sine hash with the (127.1, 311.7) constants, exactly as its surfaces write it."""
    return _sine_hash(p, SINE_K2, SINE_SCALE)


def hashSine31(p):
    """LEGACY. The house's 3D sine hash with the (127.1, 311.7, 74.7) constants (the bench chunk h31, First Light)."""
    return _sine_hash(p, SINE_K3, SINE_SCALE)
