"""CPU twin of composite/parity.glsl (atlas family K, part K3.01): cmpXor, the even-odd combination of coverages.
Pinned by tests/test_glsl_twins_groups_neon_studio_hex.py, which also holds the GLSL to this twin on SwiftShader.

WHY. The hex-neon group's graphic mood combines filled shapes by XOR; a parity that drifts (a clamp forgotten, a
form that is not associative) would make the same pile of shapes look different depending on the order a loop visits
them. The twin is the same line of maths on the CPU, so a test can check the truth table, the signed-product identity
and the Monte Carlo meaning of XOR on coverages.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; no corpus code.
"""
from __future__ import annotations

import numpy as np


def cmpXor(a, b):
    """a (1 - b) + b (1 - a), both clamped to [0, 1]: 1 - 2 cmpXor(a, b) = (1 - 2a)(1 - 2b)."""
    first = np.clip(np.asarray(a, dtype=np.float64), 0.0, 1.0)
    second = np.clip(np.asarray(b, dtype=np.float64), 0.0, 1.0)
    out = first + second - 2.0 * first * second
    return out[()] if out.ndim == 0 else out


__all__ = ["cmpXor"]
