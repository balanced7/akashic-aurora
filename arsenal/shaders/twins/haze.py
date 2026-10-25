"""CPU twin of atmos/haze.glsl (module atmos-haze): light in haze, one Python function per GLSL function, same names.

WHY. Three judges failed three builds on the same thing (light in haze): beams that turned pastel mint over blue air,
haze that showed round blobs instead of streaks, flat hard-edged wedges, an air that was a grey veil instead of light.
Every one of those is a number a seat that cannot see can check: the core's chroma, the share of the halo that is
white, whether the field is stretched along the beam, the width of an edge ramp, whether a pixel no light reaches is
exactly zero. This twin makes those checks possible on the CPU (tests/test_glsl_twins_haze.py), and the GLSL is pinned
to it pixel for pixel on SwiftShader.

Conventions as in the other twins: float64, vectors on the LAST axis, scalars or arrays broadcast like GLSL would per
pixel. Value noise and the phase function reuse their own twins (twins/noise.py, twins/volume.py), as the GLSL reuses
noise/value.glsl and volume/phase.glsl; the hot root reuses light.glowHotCoreTo3 (the vectorised glowHotCoreTo).

Apache-2.0, Akashic Aurora. Written fresh from the mathematics: single scattering and the slab radiance (Pharr, Jakob
and Humphreys, PBR 4th ed. ch. 11), the Henyey-Greenstein lobe (1941), equiangular sampling (Kulla and Fajardo, EGSR
2012). No corpus code.
"""
from __future__ import annotations

import numpy as np

from . import noise as N
from .colour import hueRotateOklch
from .light import glowHotCoreTo3
from .volume import phaseHG, phaseIso

# Seeds (the GLSL literals): the density field's two octaves, the floor band's billows and grain, the streak clumps.
SEED_DENSITY = (0x9E3779B9, 0x9E3779BA)
SEED_BAND = (0x2545F491, 0x2545F492)
SEED_STREAK = (0x3C6EF372, 0x3C6EF373)
SEED_STREAK3 = 0x3C6EF374
HAZE_G = 0.6                       # the haze's mean scattering cosine (forward, like droplets)
EXTINCTION = 0.035                 # per metre at haze amount 1: about 28 m of visibility
NEAR_LENS_M = 0.45                 # samples this close to a lens are whitened toward the light's peak
LENS_M = 0.06                      # the closest approach a lens allows (its size)
CONE_SAMPLES = 10
LAMP_SAMPLES = 6
STREAK3_AXIS = np.array([0.48, 0.64, 0.6])   # unit: the noise-space direction the distance walks along


def _f(x):
    return np.asarray(x, dtype=np.float64)


def _smoothstep(e0, e1, x):
    e0, e1, x = _f(e0), _f(e1), _f(x)
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _mix(a, b, t):
    return _f(a) * (1.0 - _f(t)) + _f(b) * _f(t)


def _len(v):
    return np.sqrt(np.sum(_f(v) * _f(v), axis=-1))


def _dot(a, b):
    return np.sum(_f(a) * _f(b), axis=-1)


def _out(x):
    return float(x) if np.ndim(x) == 0 else x


def _col(c, shape):
    """A colour broadcast to shape + (3,), negative channels read as 0 (GLSL max(col, 0))."""
    return np.broadcast_to(np.maximum(_f(c), 0.0), tuple(shape) + (3,))


# ------------------------------------------------------------------------------------------- the 2D field (any units)
def hazeDensity(p, floorY, hz, t):
    """exp(-max(y - floorY, 0) / hz.y) x (0.55 + 0.45 x two octaves of value noise at hz.x cells per unit, drifting
    hz.zw units per second). 0..1."""
    p, hz, t = _f(p), _f(hz), _f(t)
    cells = np.maximum(hz[..., 0], 1e-4)
    lift = np.maximum(hz[..., 1], 1e-4)
    q = (p - hz[..., 2:4] * np.asarray(t)[..., None]) * np.asarray(cells)[..., None]
    n = 0.6667 * N.noiseValue2(q, SEED_DENSITY[0]) + 0.3333 * N.noiseValue2(2.03 * q + np.array([17.13, 5.71]),
                                                                          SEED_DENSITY[1])
    height = np.exp(-np.maximum(p[..., 1] - _f(floorY), 0.0) / lift)
    return _out(height * (0.55 + 0.45 * (0.5 + 0.5 * n)))


def hazeFloorBand(p, floorY, thickness, t):
    """A low band: 1 at and below floorY, gone by a ragged top 0.7..1.3 thicknesses up, billows rising."""
    p, t = _f(p), _f(t)
    th = np.maximum(_f(thickness), 1e-4)
    h = (p[..., 1] - _f(floorY)) / th
    x = p[..., 0]
    billow = 0.5 + 0.5 * N.noiseValue2(np.stack(np.broadcast_arrays(x / (1.3 * th), 0.9 * h - 0.12 * t), -1),
                                       SEED_BAND[0])
    top = 0.7 + 0.6 * billow
    body = 1.0 - _smoothstep(0.15 * top, top, h)
    grain = 0.5 + 0.5 * N.noiseValue2(np.stack(np.broadcast_arrays(x / (0.45 * th) + 0.03 * t, 2.2 * h - 0.3 * t),
                                               -1), SEED_BAND[1])
    return _out(body * (0.7 + 0.3 * grain))


def _fade_near(r, along_len):
    return _smoothstep(0.5 * along_len, 3.0 * along_len, r)


def hazeStreak(p, root, clump, t):
    """Clumps stretched along the rays from `root`: clump = (along length, across angle, contrast, outward drift)."""
    p, root, clump, t = _f(p), _f(root), _f(clump), _f(t)
    d = p - root
    r = _len(d)
    u = d / np.maximum(r, 1e-6)[..., None]
    along_len = np.maximum(clump[..., 0], 1e-4)
    across = np.maximum(clump[..., 1], 1e-4)
    zq = (r - clump[..., 3] * t) / along_len
    q = np.concatenate([u / np.asarray(across)[..., None], np.asarray(zq)[..., None]], axis=-1)
    n = 0.65 * N.noiseValue3(q, SEED_STREAK[0]) + 0.35 * N.noiseValue3(q * np.array([2.0, 2.0, 1.7])
                                                                       + np.array([3.1, 7.7, 1.9]), SEED_STREAK[1])
    clumps = _smoothstep(0.38, 0.62, 0.5 + 0.5 * n)
    k = np.clip(clump[..., 2], 0.0, 1.0) * _fade_near(r, along_len)
    return _out(1.0 + (clumps - 1.0) * k)


def hazeBeamCoords(p, root, dir, reach):
    """(signed perpendicular distance, distance along dir / reach, angle from dir seen from the root)."""
    p, root, dir = _f(p), _f(root), _f(dir)
    a = dir / np.maximum(_len(dir), 1e-12)[..., None]
    d = p - root
    along = _dot(d, a)
    perp = a[..., 0] * d[..., 1] - a[..., 1] * d[..., 0]
    guard = np.where(np.abs(along) + np.abs(perp) < 1e-12, 1e-12, 0.0)
    return np.stack(np.broadcast_arrays(perp, along / np.maximum(_f(reach), 1e-6), np.arctan2(perp, along + guard)),
                    -1)


def hazePhase(towardViewer):
    """phaseHG(towardViewer, 0.6) / phaseHG(0, 0.6): 1 side-on."""
    return _out(_f(phaseHG(towardViewer, HAZE_G)) / phaseHG(0.0, HAZE_G))


# --------------------------------------------------------------------------------------------- 2D light in the haze
def hazeBeam(dPerpPx, along, col, level, dens, widthPx, phase):
    """A thin beam: the core line x (0.05 + 0.95 dens), the body x dens x phase x 0.30, the halo x (0.35 + 0.65 dens) x
    phase x 0.08, the root hot toward white; exactly zero 8 widths out, before the root and past the end."""
    d, along = np.abs(_f(dPerpPx)), _f(along)
    w = np.maximum(_f(widthPx), 1.0)
    core_w = np.maximum(0.9, 0.08 * w)
    body_w = 0.35 * w
    core = np.exp(-0.5 * (d / core_w) * (d / core_w))
    body = np.exp(-(d / body_w) * (d / body_w))
    halo = np.exp(-(np.sqrt(d * d + body_w * body_w) - body_w) / w)
    reach_out = 1.0 - _smoothstep(6.0 * w, 8.0 * w, d)
    start = _smoothstep(-0.012, 0.012, along)
    fall = np.exp(-0.9 * np.maximum(along, 0.0)) * (1.0 - _smoothstep(0.8, 1.0, along)) * start
    haze = np.clip(_f(dens), 0.0, 1.0)
    shown = 0.35 + 0.65 * haze
    seen = 0.05 + 0.95 * haze
    root = np.exp(-np.maximum(along, 0.0) / 0.012)
    scatter = np.maximum(_f(phase), 0.0)
    shape = np.broadcast(d, along, haze, scatter, w, _f(level)).shape
    tint = _col(col, shape)
    line = tint * np.asarray(core * seen)[..., None]
    shaft = tint * np.asarray(scatter * (0.30 * body * haze + 0.08 * halo * shown * (1.0 + 2.0 * root)))[..., None]
    hot = glowHotCoreTo3(tint, np.broadcast_to(6.0 * root, shape), np.ones(3)) * \
        np.asarray(np.maximum(core, body))[..., None]
    gain = np.maximum(_f(level), 0.0) * fall * reach_out
    return np.asarray(gain)[..., None] * (line + shaft + hot)


def hazeSheet(angle, halfAngle, along, col, level, dens, phase):
    """A sheet (a wedge from its root): a soft angular plateau, 0.5 at the half-angle, no outline; a white-hot root."""
    along = _f(along)
    hw = np.maximum(_f(halfAngle), 1e-4)
    a = np.abs(_f(angle)) / hw
    a2 = a * a
    across = (0.92 * np.exp(-0.693147 * a2 * a2) + 0.08 * np.exp(-np.maximum(a - 1.0, 0.0) / 0.6)) * \
        (1.0 - _smoothstep(1.7, 2.2, a))
    start = _smoothstep(-0.012, 0.012, along)
    fall = np.exp(-1.4 * np.maximum(along, 0.0)) * (1.0 - _smoothstep(0.8, 1.0, along)) * start
    haze = np.clip(_f(dens), 0.0, 1.0)
    root = np.exp(-np.maximum(along, 0.0) / 0.03)
    shape = np.broadcast(across, along, haze, _f(phase), _f(level)).shape
    tint = _col(col, shape)
    body = tint * np.asarray(across * (0.3 + 0.7 * haze) * np.maximum(_f(phase), 0.0))[..., None]
    hot = glowHotCoreTo3(tint, np.broadcast_to(6.0 * root, shape), np.ones(3)) * np.asarray(across)[..., None]
    return np.asarray(np.maximum(_f(level), 0.0) * fall)[..., None] * (body + hot)


def hazePoint(p, c, r, col, level, dens):
    """(0.7 Gaussian + 0.3 exponential skirt) x (0.35 + 0.65 dens), exactly zero beyond 3 radii."""
    x = _len(_f(p) - _f(c)) / np.maximum(_f(r), 1e-6)
    glow = (0.7 * np.exp(-2.0 * x * x) + 0.3 * np.exp(-2.5 * x)) * (1.0 - _smoothstep(2.0, 3.0, x))
    g = np.maximum(_f(level), 0.0) * glow * (0.35 + 0.65 * np.clip(_f(dens), 0.0, 1.0))
    return _col(col, np.shape(g)) * np.asarray(g)[..., None]


def hazePool(p, c, r, col, level):
    """An elliptical lit spot on a surface (radii r), exactly zero beyond 3 radii; no haze term."""
    x = _len((_f(p) - _f(c)) / np.maximum(_f(r), 1e-6))
    lit = (0.75 * np.exp(-2.0 * x * x) + 0.25 * np.exp(-3.0 * x)) * (1.0 - _smoothstep(2.0, 3.0, x))
    g = np.maximum(_f(level), 0.0) * lit
    return _col(col, np.shape(g)) * np.asarray(g)[..., None]


def hazeTint(light, dens):
    """The light's OKLCh hue turned by +20 degrees x dens (dens capped at 1.25), lightness and chroma kept."""
    return hueRotateOklch(np.maximum(_f(light), 0.0), np.clip(_f(dens), 0.0, 1.25) * (20.0 / 360.0))


# ----------------------------------------------------------------------------------------------- the 3D field (metres)
def hazeDensity3(p, floorY, hz, t):
    """hazeDensity in metres: the wind in x and z."""
    p, hz, t = _f(p), _f(hz), _f(t)
    cells = np.maximum(hz[..., 0], 1e-4)
    lift = np.maximum(hz[..., 1], 1e-4)
    wind = np.stack(np.broadcast_arrays(hz[..., 2], np.zeros_like(hz[..., 2]), hz[..., 3]), -1)
    q = (p - wind * np.asarray(t)[..., None]) * np.asarray(cells)[..., None]
    n = 0.6667 * N.noiseValue3(q, SEED_DENSITY[0]) + 0.3333 * N.noiseValue3(2.03 * q + np.array([17.13, 5.71, 11.3]),
                                                                          SEED_DENSITY[1])
    height = np.exp(-np.maximum(p[..., 1] - _f(floorY), 0.0) / lift)
    return _out(height * (0.55 + 0.45 * (0.5 + 0.5 * n)))


def hazeStreak3(p, src, clump, t):
    """hazeStreak in 3D around the light at src (lengths in metres)."""
    p, src, clump, t = _f(p), _f(src), _f(clump), _f(t)
    d = p - src
    r = _len(d)
    u = d / np.maximum(r, 1e-6)[..., None]
    along_len = np.maximum(clump[..., 0], 1e-4)
    across = np.maximum(clump[..., 1], 1e-4)
    q = u / np.asarray(across)[..., None] + STREAK3_AXIS * np.asarray((r - clump[..., 3] * t) / along_len)[..., None]
    clumps = _smoothstep(0.36, 0.64, 0.5 + 0.5 * N.noiseValue3(q, SEED_STREAK3))
    k = np.clip(clump[..., 2], 0.0, 1.0) * _fade_near(r, along_len)
    return _out(1.0 + (clumps - 1.0) * k)


def _cone_s(cos_a, one_minus_cos_hw):
    s = (1.0 - cos_a) / one_minus_cos_hw
    return np.exp(-0.693147 * s * s) * (1.0 - _smoothstep(2.0, 2.6, s))


def hazeConeProfile(p, apex, axis, halfAngle):
    """A spot's angular profile: 0.5 at halfAngle (at most 0.8 rad), a soft plateau, zero past about 1.6 half-angles."""
    v = _f(p) - _f(apex)
    cos_a = _dot(v, axis) / np.maximum(_len(v) * _len(axis), 1e-9)
    return _out(_cone_s(cos_a, 1.0 - np.cos(np.clip(_f(halfAngle), 1e-3, 0.8))))


def _cone_interval(ro, rd, t_max, apex, a, cos_edge):
    """The ray's chord [t0, t1] inside the forward nappe of the cone of support, and a mask of rays that have one."""
    co = ro - apex
    c2 = cos_edge * cos_edge
    da, oa = _dot(rd, a), _dot(co, a)
    qa = da * da - c2                                   # qa t^2 + 2 qh t + qc = 0 on the cone
    qh = da * oa - c2 * _dot(rd, co)
    qc = oa * oa - c2 * _dot(co, co)
    qa = np.where(np.abs(qa) < 1e-6, np.where(qa < 0.0, -1e-6, 1e-6), qa)
    spread = qh * qh - qa * qc
    ok = spread >= 0.0
    half_chord = np.sqrt(np.maximum(spread, 0.0))
    ra, rb = (-qh - half_chord) / qa, (half_chord - qh) / qa
    lo, hi = np.minimum(ra, rb), np.maximum(ra, rb)
    opening = qa > 0.0
    t0 = np.where(opening, np.where(da > 0.0, hi, -1e4), lo)
    t1 = np.where(opening, np.where(da > 0.0, 1e4, lo), hi)
    ok &= opening | (oa + da * 0.5 * (lo + hi) >= 0.0)
    t0 = np.maximum(t0, 0.0)
    t1 = np.minimum(t1, np.minimum(t_max, 1e4))
    ok &= t1 > t0
    return t0, t1, ok


def hazeCone(ro, rd, tMax, apex, axis, halfAngle, col, level, air, hz, clump, t, jitter):
    """Single scattering of a soft spot cone along the view ray: 10 stratified equiangular samples over the chord."""
    ro, rd, apex, axis, air = _f(ro), _f(rd), _f(apex), _f(axis), _f(air)
    shape = np.broadcast(ro[..., 0], rd[..., 0]).shape
    ro, rd = np.broadcast_to(ro, shape + (3,)), np.broadcast_to(rd, shape + (3,))
    a = axis / max(float(_len(axis)), 1e-9)
    one_minus = 1.0 - np.cos(np.clip(_f(halfAngle), 1e-3, 0.8))
    t0, t1, ok = _cone_interval(ro, rd, _f(tMax), apex, a, 1.0 - 2.6 * one_minus)
    t1 = np.where(ok, t1, t0 + 1.0)                       # a harmless chord where there is none (masked below)
    co = ro - apex
    delta = _dot(apex - ro, rd)
    D = np.maximum(_len(co + rd * delta[..., None]), LENS_M)
    th_a, th_b = np.arctan((t0 - delta) / D), np.arctan((t1 - delta) / D)
    dens0 = hazeDensity3(ro + rd * t0[..., None], air[1], hz, t)
    dens1 = hazeDensity3(ro + rd * t1[..., None], air[1], hz, t)
    amount = max(float(air[0]), 0.0)
    tint = np.maximum(_f(col), 0.0)
    peak = float(np.max(tint))
    total = np.zeros(shape + (3,))
    jit = np.broadcast_to(_f(jitter) - np.floor(_f(jitter)), shape)
    for i in range(CONE_SAMPLES):
        u = (i + jit) / CONE_SAMPLES
        ts = delta + D * np.tan(_mix(th_a, th_b, u))
        p = ro + rd * ts[..., None]
        v = p - apex
        r = np.sqrt(D * D + (ts - delta) * (ts - delta))
        prof = _cone_s(_dot(v, a) / r, one_minus)
        k = np.clip((ts - t0) / np.maximum(t1 - t0, 1e-6), 0.0, 1.0)
        sigma = amount * _mix(dens0, dens1, k) * hazeStreak3(p, apex, clump, t)
        phase = phaseHG(_dot(rd, -v / r[..., None]), HAZE_G) / phaseIso()
        through = np.exp(-EXTINCTION * amount * ts)
        near = np.exp(-(r / NEAR_LENS_M) * (r / NEAR_LENS_M))
        c = tint * (1.0 - near[..., None]) + peak * near[..., None]
        total += c * np.asarray(sigma * prof * phase * through)[..., None]
    scale = np.maximum(_f(level), 0.0) * (th_b - th_a) / (CONE_SAMPLES * D)
    return np.where(ok[..., None], total * np.asarray(scale)[..., None], 0.0)


def hazeSheet3(ro, rd, tMax, apex, axis, normal, halfAngle, thickness, col, level, air, hz, clump, t):
    """The analytic single scatter of a thin fan sheet; radiance falls as 1/r in the fan, edge-on views capped."""
    ro, rd, apex, axis, normal, air = _f(ro), _f(rd), _f(apex), _f(axis), _f(normal), _f(air)
    shape = np.broadcast(ro[..., 0], rd[..., 0]).shape
    ro, rd = np.broadcast_to(ro, shape + (3,)), np.broadcast_to(rd, shape + (3,))
    n = normal / max(float(_len(normal)), 1e-9)
    facing = _dot(rd, n)
    ok = np.abs(facing) >= 1e-6
    safe = np.where(ok, facing, 1.0)
    ts = _dot(apex - ro, n) / safe
    ok &= (ts > 0.0) & (ts < _f(tMax))
    p = ro + rd * ts[..., None]
    v = p - apex
    r = np.maximum(_len(v), LENS_M)
    x = np.arccos(np.clip(_dot(v, axis) / (r * max(float(_len(axis)), 1e-9)), -1.0, 1.0)) / \
        np.clip(_f(halfAngle), 1e-3, 1.4)
    x2 = x * x
    across = (0.92 * np.exp(-0.693147 * x2 * x2) + 0.08 * np.exp(-np.maximum(x - 1.0, 0.0) / 0.6)) * \
        (1.0 - _smoothstep(1.7, 2.2, x))
    amount = max(float(air[0]), 0.0)
    sigma = amount * hazeDensity3(p, air[1], hz, t) * hazeStreak3(p, apex, clump, t)
    phase = phaseHG(_dot(rd, -v / r[..., None]), HAZE_G) / phaseIso()
    through = np.exp(-EXTINCTION * amount * ts)
    lean = np.maximum(np.abs(facing), max(float(thickness), 0.05))
    tint = np.maximum(_f(col), 0.0)
    near = np.exp(-(r / NEAR_LENS_M) * (r / NEAR_LENS_M))
    c = tint * (1.0 - near[..., None]) + float(np.max(tint)) * near[..., None]
    g = np.maximum(_f(level), 0.0) * sigma * across * phase * through / (r * lean)
    return np.where(ok[..., None], c * np.asarray(g)[..., None], 0.0)


def hazeLamp(ro, rd, tMax, pos, reach, col, level, air, hz, t, jitter):
    """A point source of finite reach in the haze: 6 equiangular samples over the ray inside its reach."""
    ro, rd, pos, air = _f(ro), _f(rd), _f(pos), _f(air)
    shape = np.broadcast(ro[..., 0], rd[..., 0]).shape
    ro, rd = np.broadcast_to(ro, shape + (3,)), np.broadcast_to(rd, shape + (3,))
    R = max(float(reach), 1e-3)
    co = ro - pos
    delta = -_dot(co, rd)
    D2 = _dot(co, co) - delta * delta
    ok = D2 < R * R
    chord = np.sqrt(np.maximum(R * R - D2, 0.0))
    t0 = np.maximum(delta - chord, 0.0)
    t1 = np.minimum(delta + chord, _f(tMax))
    ok &= t1 > t0
    t1 = np.where(ok, t1, t0 + 1.0)
    D = np.maximum(np.sqrt(np.maximum(D2, 0.0)), LENS_M)
    th_a, th_b = np.arctan((t0 - delta) / D), np.arctan((t1 - delta) / D)
    dens0 = hazeDensity3(ro + rd * t0[..., None], air[1], hz, t)
    dens1 = hazeDensity3(ro + rd * t1[..., None], air[1], hz, t)
    amount = max(float(air[0]), 0.0)
    tint = np.maximum(_f(col), 0.0)
    peak = float(np.max(tint))
    total = np.zeros(shape + (3,))
    jit = np.broadcast_to(_f(jitter) - np.floor(_f(jitter)), shape)
    for i in range(LAMP_SAMPLES):
        u = (i + jit) / LAMP_SAMPLES
        ts = delta + D * np.tan(_mix(th_a, th_b, u))
        v = ro + rd * ts[..., None] - pos
        r = np.sqrt(D * D + (ts - delta) * (ts - delta))
        reach_out = 1.0 - _smoothstep(0.4 * R, R, r)
        k = np.clip((ts - t0) / np.maximum(t1 - t0, 1e-6), 0.0, 1.0)
        sigma = amount * _mix(dens0, dens1, k)
        phase = phaseHG(_dot(rd, -v / r[..., None]), HAZE_G) / phaseIso()
        through = np.exp(-EXTINCTION * amount * ts)
        near = np.exp(-(r / NEAR_LENS_M) * (r / NEAR_LENS_M))
        c = tint * (1.0 - near[..., None]) + peak * near[..., None]
        total += c * np.asarray(sigma * reach_out * phase * through)[..., None]
    scale = np.maximum(_f(level), 0.0) * (th_b - th_a) / (LAMP_SAMPLES * D)
    return np.where(ok[..., None], total * np.asarray(scale)[..., None], 0.0)
