"""CPU twin of volume/integrate.glsl, volume/phase.glsl, volume/density.glsl and volume/march.glsl (modules
volume-integrate, volume-phase, volume-density, volume-march): one Python function per GLSL function, with the GLSL name.
Pinned by tests/test_glsl_twins_volume_atmos.py.

WHY. A volume is a promise about accounting: light gathered and light let through, step by step along a ray. The
promise that matters most -- the picture does not depend on how many steps were taken -- can only be checked by running
the same slab at one step and at a thousand, which a CPU does to twelve digits in a millisecond. The phase function's
promises (it integrates to one over the sphere, its mean cosine is g) are integrals too.

Conventions follow the twins of batch A: float64 (the mathematical reference; the GPU's 32-bit floats agree to a few
millionths), points and colours are numpy arrays whose LAST axis is the vector, GLSL `inout` arguments are mutated in
place and also returned. Two float32 spellings (volOpacityFactor32, phaseHG32) exist only so a test can show why the
GLSL is written the way it is. A hook the host defines in GLSL (densityAt) is passed here as a Python callable.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics: Beer-Lambert; Hillaire's energy-conserving segment
integral (SIGGRAPH 2015, "Physically based and unified volumetric rendering in Frostbite"); Henyey and Greenstein
(1941); as taught by research/reviewed/shader-school-2026-10-13/volumes-atmosphere.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Below this optical depth volOpacityFactor uses its series 1 - x/2 + x^2/6 - x^3/24 (truncation under 1e-10 here),
# because in 32-bit floats 1 - e^-x cancels to nothing for small x.
OPACITY_SERIES_BELOW = 0.01

# Henyey-Greenstein's asymmetry is clamped inside (-1, 1): at |g| = 1 the lobe is a delta and the formula is 0/0.
HG_G_LIMIT = 0.9999


def _f(x):
    return np.asarray(x, dtype=np.float64)


# ----------------------------------------------------------------------------------------- integrate (G1)
@dataclass
class VolAccum:
    """Front-to-back accumulator: L is the light gathered so far, T the transmittance so far (per channel)."""
    L: np.ndarray
    T: np.ndarray


def volAccumInit(shape=()) -> VolAccum:
    """L = 0, T = 1: nothing gathered, everything behind still visible. (`shape` is a twin convenience: one
    accumulator per pixel of an image; the GLSL takes no argument.)"""
    shape = tuple(shape)
    return VolAccum(np.zeros(shape + (3,)), np.ones(shape + (3,)))


def volTransmittance(sigmaT, dist):
    """Beer-Lambert: exp(-sigmaT * dist), the fraction of light that survives `dist` through extinction sigmaT."""
    return np.exp(-_f(sigmaT) * _f(dist))


def volTransmittance3(sigmaT, dist):
    """Per channel: exp(-sigmaT * dist) for a vec3 extinction (coloured attenuation)."""
    d = _f(dist)
    return np.exp(-_f(sigmaT) * (d[..., None] if d.ndim else d))


def volOpacityFactor(x):
    """(1 - e^-x) / x, equal to 1 at x = 0: the kernel of every exact segment integral. Scalar or array."""
    x = _f(x)
    small = np.abs(x) < OPACITY_SERIES_BELOW
    safe = np.where(small, 1.0, x)
    exact = (1.0 - np.exp(-safe)) / safe
    series = 1.0 - x * (0.5 - x * (1.0 / 6.0 - x / 24.0))
    out = np.where(small, series, exact)
    return float(out) if out.ndim == 0 else out


def volOpacityFactor32(x):
    """The GLSL's arithmetic in 32-bit floats (for the test that shows why the series branch exists)."""
    x = np.asarray(x, dtype=np.float32)
    one = np.float32(1.0)
    small = np.abs(x) < np.float32(OPACITY_SERIES_BELOW)
    safe = np.where(small, one, x)
    exact = (one - np.exp(-safe)) / safe
    series = one - x * (np.float32(0.5) - x * (np.float32(1.0 / 6.0) - x / np.float32(24.0)))
    return np.where(small, series, exact).astype(np.float32)


def volStepScatter(a: VolAccum, sigmaS, sigmaT, Lin, dt) -> VolAccum:
    """One segment of length dt, integrated exactly with constant coefficients: L += T sigmaS Lin dt F(sigmaT dt),
    then T *= exp(-sigmaT dt). Over a uniform slab any number of steps gives the same light."""
    dt = _f(dt)
    depth = _f(sigmaT) * dt
    a.L = a.L + a.T * _f(sigmaS) * _f(Lin) * dt * volOpacityFactor(depth)
    a.T = a.T * np.exp(-depth)
    return a


def volStepEmit(a: VolAccum, emission, sigmaT, dt) -> VolAccum:
    """One segment of a glowing, absorbing medium: L += T emission dt F(sigmaT dt), T *= exp(-sigmaT dt). With
    sigmaT = 0 it is the plain sum T emission dt (an aurora: pure emission)."""
    dt = _f(dt)
    depth = _f(sigmaT) * dt
    a.L = a.L + a.T * _f(emission) * dt * volOpacityFactor(depth)
    a.T = a.T * np.exp(-depth)
    return a


def volSaturated(a: VolAccum, eps):
    """True when every channel's transmittance is below eps: nothing behind can still show; stop marching."""
    return np.max(a.T, axis=-1) < eps


def volResolve(a: VolAccum, background):
    """L + T * background: the gathered light over what lies behind, dimmed by the medium."""
    return a.L + a.T * _f(background)


# ---------------------------------------------------------------------------------------------- phase (G2)
def phaseIso() -> float:
    """The isotropic phase function, 1 / (4 pi) per steradian."""
    return 0.25 / math.pi


def phaseHG(mu, g):
    """Henyey-Greenstein, normalised: (1 - g^2) / (4 pi (1 + g^2 - 2 g mu)^(3/2)), with mu = dot(viewRayDir,
    dirToLight) clamped to [-1, 1] and g clamped to +-HG_G_LIMIT. The denominator is spelled as the sum of squares
    (1 - g mu)^2 + g^2 (1 - mu^2), which rounding cannot drive negative."""
    cosine = np.clip(_f(mu), -1.0, 1.0)
    asym = np.clip(_f(g), -HG_G_LIMIT, HG_G_LIMIT)
    lean = 1.0 - asym * cosine
    spread = lean * lean + asym * asym * (1.0 - cosine * cosine)
    numerator = 1.0 - asym * asym
    out = numerator / (4.0 * math.pi * spread * np.sqrt(spread))
    return float(out) if np.ndim(out) == 0 else out


def phaseHG32(mu, g):
    """The GLSL's arithmetic in 32-bit floats (for the test that shows why the denominator is a sum of squares)."""
    f32 = np.float32
    c = np.clip(np.asarray(mu, dtype=f32), f32(-1.0), f32(1.0))
    k = np.clip(np.asarray(g, dtype=f32), f32(-HG_G_LIMIT), f32(HG_G_LIMIT))
    lean = f32(1.0) - k * c
    spread = lean * lean + k * k * (f32(1.0) - c * c)
    return ((f32(1.0) - k * k) / (f32(4.0 * math.pi) * spread * np.sqrt(spread))).astype(f32)


# -------------------------------------------------------------------------------------------- density (G4)
def densFromSDF(sdf, softness):
    """clamp(-sdf / softness, 0, 1): 0 outside the shape, ramping to 1 at depth `softness` inside. softness 0 is a hard
    edge (read as 1e-6)."""
    out = np.clip(-_f(sdf) / np.maximum(_f(softness), 1e-6), 0.0, 1.0)
    return float(out) if np.ndim(out) == 0 else out


# --------------------------------------------------------------------------------------------- march (G5)
def marchStepPoly(i, base, scale, power) -> float:
    """Layer i sits at base + scale * i^power (power > 0; layer 0 at base, a negative index read as 0)."""
    k = max(float(i), 0.0)
    return float(base) + float(scale) * (k ** float(power) if k > 0.0 else 0.0)


def volLightOneTap(p, toLight, dist, floorShadow, densityAt):
    """Visibility of the light from p in [floorShadow, 1]: Beer's law over the segment toward the light, its optical
    depth estimated by ONE density probe at the segment's midpoint (the midpoint rule: exact when the density varies
    linearly along the probe). densityAt is the host's hook: extinction per unit length at a point."""
    reach = np.maximum(_f(dist), 0.0)
    mid = _f(p) + (0.5 * reach)[..., None] * _f(toLight) if np.ndim(reach) else _f(p) + 0.5 * float(reach) * _f(toLight)
    sigma = np.maximum(_f(densityAt(mid)), 0.0)
    t = volTransmittance(sigma, reach)
    out = floorShadow * (1.0 - t) + t                    # GLSL mix(floorShadow, 1.0, t)
    return float(out) if np.ndim(out) == 0 else out
