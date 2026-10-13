"""CPU twin of atmos/fog.glsl, atmos/aurora.glsl and atmos/sky.glsl (modules atmos-fog, atmos-aurora, atmos-sky): one
Python function per GLSL function, with the GLSL name. Pinned by tests/test_glsl_twins_volume_atmos.py.

WHY. The sky is where a scene's colour story starts and where its distance ends, and the aurora is the house's
signature subject (the project is named after it). Their promises are measurable without a screen: fog over a then b
equals fog over a + b (Beer's law composes), the aurora's emission peaks at exactly one a few kilometres above its hem
and decays by e per scale height, its colours are the spectral lines the CIE observer sees, and the sky is exactly the
zenith colour overhead. This twin lets a seat that cannot see check every one of them.

Conventions as in the batch-A twins: float64, vectors on the LAST axis, scalars or arrays broadcast like GLSL would
per pixel. auroraRays reuses the value-noise twin (twins/noise.py), as the GLSL reuses noise/value.glsl.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the physics as taught by
research/reviewed/shader-school-2026-10-13/volumes-atmosphere.md (sections 4.1, 5.1 and 7): Lawlor and Genetti's
emissive aurora model (2011), the NOAA SWPC aurora tutorial, the CIE 1931 standard observer, Inigo Quilez's fog
articles. No corpus code.
"""
from __future__ import annotations

import numpy as np

from . import noise as N
from .volume import volTransmittance

# ----------------------------------------------------------------------------------------------- aurora constants
# The hem's rise: emission switches on over about the scale height of the air near 100 km, where each kilometre lower
# the air is denser and stops the incoming electrons sooner.
AURORA_RISE_KM = 6.0

# Each emission line's colour: its wavelength through the CIE 1931 2-degree observer into linear sRGB (IEC 61966-2-1),
# the negative channel clipped (no display shows a spectral line), brightest channel 1. Brightness is not here: the
# profile carries it, so these only choose the hue.
LINE_GREEN_5577 = np.array([0.222, 1.0, 0.0])          # atomic oxygen 557.7 nm: the curtain's body
LINE_RED_6300 = np.array([1.0, 0.0, 0.0])              # atomic oxygen 630.0 nm: the slow, high crown
# The lower fringe of an energetic display: ionised nitrogen's 427.8 nm violet band plus a share of molecular
# nitrogen's red first-positive bands (about 670 nm), which together read as the purple-pink hem in photographs.
FRINGE_N2_RED_SHARE = 0.7
LINE_FRINGE = np.array([0.125 + FRINGE_N2_RED_SHARE, 0.0, 1.0])

# Rays: two rows of 1D value noise (a whole-number row of 2D value noise is exactly 1D value noise), drifting in
# opposite directions at unrelated rates, the fine row about three times denser.
RAYS_FINE_SCALE = 3.1
RAYS_DRIFT = (-0.21, 0.53)        # along-units per second, coarse and fine
RAYS_FINE_ROW = 7.0
RAYS_COARSE_SHARE = 0.55
RAYS_EDGES = (0.5, 0.9)           # 0 below the first, 1 above the second: about half dark, one place in 16 bright

# Sky: the horizon band's sharpness away from the sun and toward a low sun (exponents on 1 - sin(elevation)), and the
# sun elevation (as sin) by which the warm horizon has gone.
SKY_BAND_AWAY, SKY_BAND_TOWARD = 6.0, 1.5
SKY_WARM_UNTIL = 0.6


def _f(x):
    return np.asarray(x, dtype=np.float64)


def _smoothstep(e0, e1, x):
    t = np.clip((_f(x) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _out(x):
    return float(x) if np.ndim(x) == 0 else x


# ------------------------------------------------------------------------------------------------------- fog (G7)
def fogExp(col, fogCol, dist, k):
    """mix(col, fogCol, 1 - exp(-k dist)): the surface seen through `dist` of uniform fog. A negative distance or
    density is read as no fog."""
    t = volTransmittance(np.maximum(_f(k), 0.0), np.maximum(_f(dist), 0.0))
    t = t[..., None] if np.ndim(t) else t
    return _f(fogCol) * (1.0 - t) + _f(col) * t                 # GLSL mix(fogCol, col, t)


# ---------------------------------------------------------------------------------------------------- aurora (G8)
def auroraProfile(altKm, lowerEdgeKm, scaleHKm):
    """Emission against altitude, 0 at and below the hem, (1 - e^(-z/rise)) e^(-z/H) above it (z the height above the
    hem), divided by its own peak so the brightest altitude is exactly 1; far above it decays by e per scale height H."""
    h = np.maximum(_f(scaleHKm), 1e-3)
    above = np.maximum(_f(altKm) - _f(lowerEdgeKm), 0.0)
    shape = (1.0 - np.exp(-above / AURORA_RISE_KM)) * np.exp(-above / h)
    settle = AURORA_RISE_KM / (AURORA_RISE_KM + h)             # e^(-z/rise) at the peak
    peak = (1.0 - settle) * settle ** (AURORA_RISE_KM / h)
    return _out(shape / peak)


def auroraLineColor(altKm, energetic):
    """Linear RGB of the emission at an altitude: the 557.7 nm green body (switching on between 92 and 108 km, where
    collisions stop quenching it, gone by 250), the 630 nm red crown (taking over from about 160 to 260 km) and, scaled
    by `energetic` in [0, 1], the purple nitrogen fringe (full below 96 km, gone by 112), so an energetic hem is purple
    under the green. The weights are shares of a unit of emission; multiply by auroraProfile for brightness."""
    alt = _f(altKm)
    green = _smoothstep(92.0, 108.0, alt) * (1.0 - _smoothstep(170.0, 250.0, alt))
    red = _smoothstep(160.0, 260.0, alt)
    fringe = np.clip(_f(energetic), 0.0, 1.0) * (1.0 - _smoothstep(96.0, 112.0, alt))
    return (green[..., None] * LINE_GREEN_5577 + red[..., None] * LINE_RED_6300
            + np.asarray(fringe)[..., None] * LINE_FRINGE)


def auroraRays(along, t, seed):
    """Field-aligned striation in [0, 1]: two rows of 1D value noise along the curtain, drifting at their own rates,
    mixed, then thresholded so most of the curtain is between rays and a few places are bright cores. It has no
    height coordinate: multiply a curtain by it and every ray runs the curtain's full height."""
    x, tt = _f(along), _f(t)
    x, tt = np.broadcast_arrays(x, tt)
    coarse = 0.5 + 0.5 * N.noiseValue2(np.stack([x + RAYS_DRIFT[0] * tt, np.zeros_like(x)], -1), seed)
    fine = 0.5 + 0.5 * N.noiseValue2(np.stack([RAYS_FINE_SCALE * x + RAYS_DRIFT[1] * tt,
                                               np.full_like(x, RAYS_FINE_ROW)], -1), seed)
    lit = RAYS_COARSE_SHARE * coarse + (1.0 - RAYS_COARSE_SHARE) * fine
    return _out(_smoothstep(RAYS_EDGES[0], RAYS_EDGES[1], lit))


# ------------------------------------------------------------------------------------------------------- sky (G6)
def skyGradient(rd, toSun, zenith, horizon, sunTint):
    """A sky from three colours: exactly `zenith` overhead, the horizon colour at and below the horizon, the band
    between them thin away from the sun and wide toward it. While the sun is low (or below the horizon) the horizon
    toward it takes sunTint; once the sun has climbed past sin(elevation) = 0.6 the horizon keeps `horizon` all
    round. Below the horizon a direction takes the colour of the horizon in its azimuth (no seam under a ground)."""
    rd, sun = _f(rd), _f(toSun)
    up = np.clip(rd[..., 1], 0.0, 1.0)
    flat = np.concatenate([rd[..., :1], np.maximum(rd[..., 1:2], 0.0), rd[..., 2:]], axis=-1)
    flat = flat / np.sqrt(np.maximum(np.sum(flat * flat, axis=-1, keepdims=True), 1e-12))
    facing = 0.5 + 0.5 * np.sum(flat * sun, axis=-1)
    low_sun = 1.0 - _smoothstep(0.0, SKY_WARM_UNTIL, sun[..., 1])
    f2 = facing * facing
    glow = low_sun * f2 * f2
    horizon_col = _f(horizon) * (1.0 - glow[..., None]) + _f(sunTint) * glow[..., None]
    sharp = SKY_BAND_AWAY * (1.0 - glow) + SKY_BAND_TOWARD * glow
    band = (1.0 - up) ** sharp
    return _f(zenith) * (1.0 - band[..., None]) + horizon_col * band[..., None]
