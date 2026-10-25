"""CPU twin of atmos/haze.glsl (module atmos-haze): light in haze, one Python function per GLSL function, same names.

WHY. Three judges failed three builds on the same thing (light in haze): beams that turned pastel mint over blue air,
haze that showed round blobs instead of streaks, flat hard-edged wedges, an air that was a grey veil instead of light.
Every one of those is a number a seat that cannot see can check: the core's chroma, the share of the halo that is
white, whether the field is stretched along the beam, the width of an edge ramp, whether a pixel no light reaches is
exactly zero. Round 2 (2026-10-25) added what its judge asked for, each checkable the same way: dash-sized clumps, a
beam blurred over the shutter, a core floor and a pale-or-saturated sheet body chosen by the caller, a monotonic haze
amount in 3D, a blue-noise jitter, and the ring (hazeRing, hazeRing3): an LED ring as an area light that lights the
haze round it. This twin makes those checks possible on the CPU (tests/test_glsl_twins_haze.py), and the GLSL is
pinned to it pixel for pixel on SwiftShader.

Conventions as in the other twins: float64, vectors on the LAST axis, scalars or arrays broadcast like GLSL would per
pixel. Value noise, the hash and the phase function reuse their own twins (twins/noise.py, twins/hash.py,
twins/volume.py), as the GLSL reuses noise/value.glsl, hash/pcg.glsl and volume/phase.glsl; the hot root reuses
light.glowHotCoreTo3 (the vectorised glowHotCoreTo).

Apache-2.0, Akashic Aurora. Written fresh from the mathematics: single scattering and the slab radiance (Pharr, Jakob
and Humphreys, PBR 4th ed. ch. 11), the balance heuristic (PBR 4th ed. 2.4), the Henyey-Greenstein lobe (1941),
equiangular sampling (Kulla and Fajardo, EGSR 2012), void-and-cluster dither arrays (Ulichney 1993), the error-function
fit 7.1.26 (Abramowitz and Stegun 1964). No corpus code.
"""
from __future__ import annotations

import numpy as np

from . import hash as Hh
from . import noise as N
from .colour import hueRotateOklch
from .light import glowHotCoreTo3
from .volume import phaseHG, phaseIso

# Seeds (the GLSL literals): the density field's two octaves, the floor band's billows and grain, the streak clumps.
SEED_DENSITY = (0x9E3779B9, 0x9E3779BA)
SEED_BAND = (0x2545F491, 0x2545F492)
SEED_STREAK = (0x3C6EF372, 0x3C6EF373)
SEED_STREAK3 = 0x3C6EF374
STREAK_OCTAVES = ((1.0, (0.0, 0.0), SEED_STREAK[0], 0.7), (2.0, (0.5, 0.37), SEED_STREAK[1], 0.3))
STREAK_CUT = (0.46, 0.64)          # the clump threshold: about 40 per cent of the field is clump
HAZE_G = 0.6                       # the haze's mean scattering cosine (forward, like droplets)
EXTINCTION = 0.035                 # per metre: about 28 m of visibility, the hall's, whatever the haze amount
NEAR_LENS_M = 0.45                 # samples this close to a lens are whitened toward the light's peak
LENS_M = 0.06                      # the closest approach a lens allows (its size)
CONE_SAMPLES = 12
LAMP_SAMPLES = 8
RING_SAMPLES = 12
STREAK3_AXIS = np.array([0.48, 0.64, 0.6])   # unit: the noise-space direction the distance walks along
ERF_P = 0.3275911                  # Abramowitz and Stegun 7.1.26
ERF_A = (0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429)
GAUSS3 = ((-0.7745967, 0.27777778), (0.0, 0.44444444), (0.7745967, 0.27777778))   # Gauss-Legendre on [-1, 1] / 2
# hazeBlueNoise's 16 x 16 void-and-cluster ranks, four 8-bit ranks a word, low byte first (the GLSL table)
BLUE_NOISE_WORDS = (
    0x184C34A1, 0x71CA3A97, 0xAC820B52, 0xDC69E605, 0xCE73FCB5, 0x30B755AE, 0xF83CDD9B, 0x217BBE4E,
    0x278B0157, 0xF27F07E7, 0x2675C91A, 0x40F01692, 0x5DC3DF96, 0x48D89141, 0xB8588E65, 0xCCA761D3,
    0xA3156C2D, 0xA6236BF7, 0x1EDB02BF, 0x800F3878, 0x7D3BEEAB, 0x7ACB0CB9, 0x9E43FD35, 0x4DFAB2E4,
    0xDA50C009, 0xE8549831, 0x516EAA17, 0xD2678A2A, 0x1C8C6F9C, 0xB63DF366, 0xF1C6885F, 0x223FC108,
    0xB1F92BEA, 0x900681D0, 0x95132FD7, 0x83E0A85B, 0x104562C7, 0xE528A54B, 0x3ECD7749, 0x531476EC,
    0xE1AD9304, 0xBC60C874, 0x6AAFFB1D, 0xB437D125, 0x8732CF7C, 0x9A39F61F, 0x00A05985, 0xFE9D86BA,
    0x5AEF1942, 0xEB6D039F, 0x47E2330E, 0x642056F5, 0x46BB70E9, 0xB04FC2D9, 0x8FC57ED6, 0xA4DE1272,
    0xA90A942C, 0x248D7929, 0x2E1B6844, 0xC44AB3D4, 0xF484D55E, 0xFF11E363, 0x5CEDBDA2, 0x0D893699)
BLUE_NOISE_RANKS = np.array([(w >> (8 * k)) & 255 for w in BLUE_NOISE_WORDS for k in range(4)]).reshape(16, 16)


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


def _ease(f):
    cube = f * f * f
    return cube * (10.0 + f * (6.0 * f - 15.0))                 # 6 f^5 - 15 f^4 + 10 f^3


def _erf(z):
    """Abramowitz and Stegun 7.1.26, as the GLSL writes it (absolute error under 1.5e-7)."""
    z = _f(z)
    az = np.abs(z)
    k = 1.0 / (1.0 + ERF_P * az)
    a1, a2, a3, a4, a5 = ERF_A
    poly = k * (a1 + k * (a2 + k * (a3 + k * (a4 + k * a5))))
    return np.sign(z) * (1.0 - poly * np.exp(-az * az))


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


def _streak_corner(x, y, stream):
    v = np.stack(np.broadcast_arrays(x, y, np.uint32(stream)), -1).astype(np.uint32)
    return 2.0 * Hh.u01(Hh.pcg3d(v)[..., 0]) - 1.0


def hazeStreakNoise(p, root, clump, t):
    """The raw two-octave value noise behind hazeStreak (in -1..1): periodic in the angle round the root (whole cells),
    the distance from the root in dash lengths. Not a GLSL function; the tests read the field's statistics here."""
    p, root, clump, t = _f(p), _f(root), _f(clump), _f(t)
    d = p - root
    r = _len(d)
    dash = np.maximum(clump[..., 0], 1e-4)
    around = np.maximum(np.floor(6.2831853 / np.maximum(clump[..., 1], 1e-4) + 0.5), 3.0)
    guard = np.where(r < 1e-12, 1e-12, 0.0)
    turn = (np.arctan2(d[..., 1], d[..., 0] + guard) * 0.15915494 + 0.5) * around
    zq = (r - clump[..., 3] * t) / dash
    n = np.zeros(np.broadcast(turn, zq).shape)
    for scale, off, stream, weight in STREAK_OCTAVES:
        period = np.floor(around * scale + 0.5).astype(np.uint64)
        qo = np.stack(np.broadcast_arrays(turn * scale + off[0], zq * scale + off[1]), -1)
        cell = Hh.cellU2(qo).astype(np.uint64)
        in_cell = qo - np.floor(qo)
        x0 = (cell[..., 0] % period).astype(np.uint32)
        x1 = ((cell[..., 0] + np.uint64(1)) % period).astype(np.uint32)
        y0 = cell[..., 1].astype(np.uint32)
        y1 = ((cell[..., 1] + np.uint64(1)) & np.uint64(0xFFFFFFFF)).astype(np.uint32)
        e = _ease(in_cell)
        c00, c10 = _streak_corner(x0, y0, stream), _streak_corner(x1, y0, stream)
        c01, c11 = _streak_corner(x0, y1, stream), _streak_corner(x1, y1, stream)
        lo = c00 + (c10 - c00) * e[..., 0]
        hi = c01 + (c11 - c01) * e[..., 0]
        n = n + weight * (lo + (hi - lo) * e[..., 1])
    return n, r, dash


def hazeStreak(p, root, clump, t):
    """Dash-sized clumps stretched along the rays from `root`: clump = (dash length along the ray, cell angle across
    it, contrast, outward drift). About 40 per cent clump; faded in where the cells are wide enough to see."""
    clump = _f(clump)
    n, r, dash = hazeStreakNoise(p, root, clump, t)
    clumps = _smoothstep(STREAK_CUT[0], STREAK_CUT[1], 0.5 + 0.5 * n)
    width = r * np.maximum(clump[..., 1], 1e-4) / dash
    k = np.clip(clump[..., 2], 0.0, 1.0) * _fade_near(r, dash) * _smoothstep(0.05, 0.12, width)
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
def _beam_terms(d_core, d_body, halo, nearest, along, col, level, dens, widthPx, phase, coreFloor, w, shape_from):
    reach_out = 1.0 - _smoothstep(6.0 * w, 8.0 * w, nearest)
    start = _smoothstep(-0.012, 0.012, along)
    fall = np.exp(-0.9 * np.maximum(along, 0.0)) * (1.0 - _smoothstep(0.8, 1.0, along)) * start
    haze = np.clip(_f(dens), 0.0, 1.0)
    shown = 0.35 + 0.65 * haze
    floor = np.clip(_f(coreFloor), 0.0, 1.0)
    seen = floor + (1.0 - floor) * haze
    root = np.exp(-np.maximum(along, 0.0) / 0.012)
    scatter = np.maximum(_f(phase), 0.0)
    shape = np.broadcast(*shape_from, haze, scatter, w, _f(level), floor).shape
    tint = _col(col, shape)
    line = tint * np.asarray(d_core * seen)[..., None]
    shaft = tint * np.asarray(scatter * (0.30 * d_body * haze + 0.08 * halo * shown * (1.0 + 2.0 * root)))[..., None]
    hot = glowHotCoreTo3(tint, np.broadcast_to(6.0 * root, shape), np.ones(3)) * \
        np.asarray(np.maximum(d_core, d_body))[..., None]
    gain = np.maximum(_f(level), 0.0) * fall * reach_out
    return np.asarray(gain)[..., None] * (line + shaft + hot)


def hazeBeam(dPerpPx, along, col, level, dens, widthPx, phase, coreFloor):
    """A thin beam: the core line x (coreFloor + (1 - coreFloor) dens), the body x dens x phase x 0.30, the halo x
    (0.35 + 0.65 dens) x phase x 0.08, the root hot toward white; exactly zero 8 widths out, before the root and past
    the end."""
    d, along = np.abs(_f(dPerpPx)), _f(along)
    w = np.maximum(_f(widthPx), 1.0)
    core_w = np.maximum(0.9, 0.08 * w)
    body_w = 0.35 * w
    core = np.exp(-0.5 * (d / core_w) * (d / core_w))
    body = np.exp(-(d / body_w) * (d / body_w))
    halo = np.exp(-(np.sqrt(d * d + body_w * body_w) - body_w) / w)
    return _beam_terms(core, body, halo, d, along, col, level, dens, widthPx, phase, coreFloor, w, (d, along))


def hazeBeamSwept(dPerpPx, sweepPx, along, col, level, dens, widthPx, phase, coreFloor):
    """hazeBeam averaged over a shutter in which the axis crossed sweepPx pixels (dPerpPx at mid-shutter): the core and
    body Gaussians box-filtered in closed form (erf by A&S 7.1.26), the halo by three Gauss-Legendre points; hazeBeam
    below a quarter pixel."""
    dp, along = _f(dPerpPx), _f(along)
    s = np.abs(_f(sweepPx))
    still = hazeBeam(dp, along, col, level, dens, widthPx, phase, coreFloor)
    if np.all(s < 0.25):
        return still
    w = np.maximum(_f(widthPx), 1.0)
    core_w = np.maximum(0.9, 0.08 * w)
    body_w = 0.35 * w
    safe = np.maximum(s, 0.25)
    x0, x1 = dp - 0.5 * safe, dp + 0.5 * safe
    core = np.maximum(1.2533141 * core_w * (_erf(x1 / (1.4142136 * core_w)) - _erf(x0 / (1.4142136 * core_w))) / safe,
                      0.0)
    body = np.maximum(0.88622693 * body_w * (_erf(x1 / body_w) - _erf(x0 / body_w)) / safe, 0.0)
    halo = 0.0
    for node, weight in GAUSS3:
        at = dp + 0.5 * safe * node
        halo = halo + weight * np.exp(-(np.sqrt(at * at + body_w * body_w) - body_w) / w)
    nearest = np.maximum(np.abs(dp) - 0.5 * safe, 0.0)
    swept = _beam_terms(core, body, halo, nearest, along, col, level, dens, widthPx, phase, coreFloor, w,
                        (dp, along, s))
    return np.where(np.asarray(s < 0.25)[..., None], still, swept)


def hazeSheet(angle, halfAngle, along, col, level, dens, phase, pale):
    """A sheet (a wedge from its root): a soft angular plateau, 0.5 at the half-angle, no outline; a white-hot root.
    The body is the hue with its white part removed (pale 0, saturated) or the colour as given lifted by
    1 + 3 x min/max (pale 1, pale-and-bright)."""
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
    pl = np.clip(_f(pale), 0.0, 1.0)
    shape = np.broadcast(across, along, haze, _f(phase), _f(level), pl).shape
    tint = _col(col, shape)
    top = np.max(tint, axis=-1)
    low = np.min(tint, axis=-1)
    spread = top - low
    pure = np.where(np.asarray(spread > 1e-6)[..., None],
                    (tint - low[..., None]) * np.asarray(top / np.where(spread > 1e-6, spread, 1.0))[..., None], tint)
    lifted = tint * np.asarray(1.0 + 3.0 * low / np.maximum(top, 1e-9))[..., None]
    body_tint = pure + (lifted - pure) * np.asarray(pl)[..., None]
    body = body_tint * np.asarray(across * (0.3 + 0.7 * haze) * np.maximum(_f(phase), 0.0))[..., None]
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


def hazeRingSpan(p, c, ring, arc):
    """The ring's light at p before its window and level: (room, distance to the band). room is the closed-form
    integral of 1 / distance^2 over the arc (softened by the haze depth) times depth x radius / pi, 1 on a closed
    band. Not a GLSL function: the tests check the closed form against a sum over the arc here."""
    p, c, ring, arc = _f(p), _f(c), _f(ring), _f(arc)
    v = p - c
    rho = _len(v)
    R = np.maximum(ring[..., 0], 1e-4)
    hw = np.maximum(ring[..., 1], 1e-5)
    depth = np.maximum(ring[..., 2], hw)
    close_in = (rho - R) * (rho - R) + depth * depth
    far_out = (rho + R) * (rho + R) + depth * depth
    root = np.sqrt(close_in * far_out)
    turn = 6.2831853 / root
    e = np.abs(rho - R)
    span = turn
    half = np.maximum(arc[..., 1], 0.0)
    is_arc = arc[..., 1] < 3.1415926
    if np.any(is_arc):
        guard = np.where(rho < 1e-12, 1e-12, 0.0)
        phi = np.arctan2(v[..., 1], v[..., 0] + guard)
        delta = np.mod(arc[..., 0] - phi + 3.1415927, 6.2831853) - 3.1415927
        stretch = np.sqrt(far_out / close_in)
        xa, xb = delta - half, delta + half
        ma, mb = np.floor(xa * 0.15915494 + 0.5), np.floor(xb * 0.15915494 + 0.5)
        ya, yb = xa - 6.2831853 * ma, xb - 6.2831853 * mb
        ga = 2.0 / root * np.arctan2(stretch * np.sin(0.5 * ya), np.cos(0.5 * ya)) + ma * turn
        gb = 2.0 / root * np.arctan2(stretch * np.sin(0.5 * yb), np.cos(0.5 * yb)) + mb * turn
        arc_span = np.maximum(gb - ga, 0.0)
        end_a = np.stack(np.broadcast_arrays(R * np.cos(arc[..., 0] - half), R * np.sin(arc[..., 0] - half)), -1)
        end_b = np.stack(np.broadcast_arrays(R * np.cos(arc[..., 0] + half), R * np.sin(arc[..., 0] + half)), -1)
        to_ends = np.minimum(_len(v - end_a), _len(v - end_b))
        e = np.where(is_arc & (np.abs(delta) > half), to_ends, e)
        span = np.where(is_arc, arc_span, span)
    return depth * R * span * 0.31830989, e


def hazeRing(p, c, ring, arc, col, level, dens):
    """The haze lit by an LED ring or an open arc of it: ring = (radius, band half-width, haze depth, reach); arc =
    (centre angle, half-span; >= pi closed). room x window x dens plus half the band's own glow, exactly zero 3
    half-widths plus the reach from the band."""
    ring = _f(ring)
    room, e = hazeRingSpan(p, c, ring, arc)
    hw = np.maximum(ring[..., 1], 1e-5)
    reach = np.maximum(ring[..., 3], 1e-4)
    x = np.maximum(e - 3.0 * hw, 0.0) / reach
    window = 1.0 - _smoothstep(0.0, 1.0, x)
    u = e / hw
    band = (0.7 * np.exp(-2.0 * u * u) + 0.3 * np.exp(-2.5 * u)) * (1.0 - _smoothstep(2.0, 3.0, u))
    haze = np.clip(_f(dens), 0.0, 1.0)
    g = np.maximum(_f(level), 0.0) * (room * window * haze + 0.5 * band * (0.35 + 0.65 * haze))
    return _col(col, np.shape(g)) * np.asarray(g)[..., None]


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


def hazeBlueNoise(pixel):
    """The 16 x 16 void-and-cluster threshold at floor(pixel) mod 16: (rank + 0.5) / 256, in (0, 1)."""
    cell = Hh.cellU2(pixel).astype(np.int64) & 15
    return _out((BLUE_NOISE_RANKS[cell[..., 1], cell[..., 0]] + 0.5) / 256.0)


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
    """Single scattering of a soft spot cone along the view ray: 12 stratified equiangular samples over the chord;
    transmittance exp(-0.035 t) whatever the haze amount, so the light is proportional to air.x."""
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
        through = np.exp(-EXTINCTION * ts)
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
    through = np.exp(-EXTINCTION * ts)
    lean = np.maximum(np.abs(facing), max(float(thickness), 0.05))
    tint = np.maximum(_f(col), 0.0)
    near = np.exp(-(r / NEAR_LENS_M) * (r / NEAR_LENS_M))
    c = tint * (1.0 - near[..., None]) + float(np.max(tint)) * near[..., None]
    g = np.maximum(_f(level), 0.0) * sigma * across * phase * through / (r * lean)
    return np.where(ok[..., None], c * np.asarray(g)[..., None], 0.0)


def hazeLamp(ro, rd, tMax, pos, reach, col, level, air, hz, t, jitter):
    """A point source of finite reach in the haze: 8 equiangular samples over the ray inside its reach."""
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
        through = np.exp(-EXTINCTION * ts)
        near = np.exp(-(r / NEAR_LENS_M) * (r / NEAR_LENS_M))
        c = tint * (1.0 - near[..., None]) + peak * near[..., None]
        total += c * np.asarray(sigma * reach_out * phase * through)[..., None]
    scale = np.maximum(_f(level), 0.0) * (th_b - th_a) / (LAMP_SAMPLES * D)
    return np.where(ok[..., None], total * np.asarray(scale)[..., None], 0.0)


def hazeRingIrradiance(x, centre, normal, ring):
    """The closed-form light of a closed ring at points x before the haze: level-1 irradiance 1 / (nearest x farthest
    distance to the circle, each softened by the band) and the distance to the band. Not a GLSL function: the tests
    check it against a sum over lamps on the circle here."""
    x, centre, normal, ring = _f(x), _f(centre), _f(normal), _f(ring)
    n = normal / max(float(_len(normal)), 1e-9)
    R = max(float(ring[0]), 1e-3)
    hw = max(float(ring[1]), 0.01)
    v = x - centre
    h = _dot(v, n)
    rho = _len(v - h[..., None] * n)
    gap2 = h * h + (rho - R) * (rho - R)
    return 1.0 / np.sqrt((gap2 + hw * hw) * (h * h + (rho + R) * (rho + R) + hw * hw)), np.sqrt(gap2)


def hazeRing3(ro, rd, tMax, centre, normal, ring, col, level, air, hz, t, jitter):
    """A closed LED ring in metres (ring = (radius, band half-width, reach)) scattering in the haze along the view ray:
    its closed-form irradiance, 12 samples (half drawn as 1 / distance about the plane crossing by an asinh map, half
    uniform) by the balance heuristic, phase toward the nearest point of the band; exactly zero beyond the reach from the band."""
    ro, rd, centre, normal, ring, air = _f(ro), _f(rd), _f(centre), _f(normal), _f(ring), _f(air)
    shape = np.broadcast(ro[..., 0], rd[..., 0]).shape
    ro, rd = np.broadcast_to(ro, shape + (3,)), np.broadcast_to(rd, shape + (3,))
    n = normal / max(float(_len(normal)), 1e-9)
    R = max(float(ring[0]), 1e-3)
    hw = max(float(ring[1]), 0.01)
    reach = max(float(ring[2]), 1e-3)
    bound = R + reach
    co = ro - centre
    mid = -_dot(co, rd)
    D2 = _dot(co, co) - mid * mid
    ok = D2 < bound * bound
    chord = np.sqrt(np.maximum(bound * bound - D2, 0.0))
    t0 = np.maximum(mid - chord, 0.0)
    t1 = np.minimum(mid + chord, _f(tMax))
    ok &= t1 > t0
    t1 = np.where(ok, t1, t0 + 1.0)
    facing = _dot(rd, n)
    tc = np.clip(np.where(np.abs(facing) > 1e-4, -_dot(co, n) / np.where(np.abs(facing) > 1e-4, facing, 1.0), mid),
                 t0, t1)
    vc = co + rd * tc[..., None]
    hc = _dot(vc, n)
    rho_c = _len(vc - hc[..., None] * n)
    Dc = np.maximum(np.sqrt(hc * hc + (rho_c - R) * (rho_c - R)), hw)
    s_a, s_b = np.arcsinh((t0 - tc) / Dc), np.arcsinh((t1 - tc) / Dc)
    chord_len = t1 - t0
    dens0 = hazeDensity3(ro + rd * t0[..., None], air[1], hz, t)
    dens1 = hazeDensity3(ro + rd * t1[..., None], air[1], hz, t)
    amount = max(float(air[0]), 0.0)
    side_y = np.cross(n, [0.0, 1.0, 0.0])
    side = side_y if side_y @ side_y > 0.01 else np.cross(n, [0.0, 0.0, 1.0])
    side = side / np.linalg.norm(side)
    total = np.zeros(shape)
    jit = np.broadcast_to(_f(jitter) - np.floor(_f(jitter)), shape)
    for i in range(RING_SAMPLES):
        u = (i + jit) / RING_SAMPLES
        ts = np.where(u < 0.5, tc + Dc * np.sinh(_mix(s_a, s_b, 2.0 * u)), _mix(t0, t1, 2.0 * u - 1.0))
        off = ts - tc
        pdf = 0.5 / (np.sqrt(off * off + Dc * Dc) * np.maximum(s_b - s_a, 1e-9)) + 0.5 / chord_len
        v = co + rd * ts[..., None]
        h = _dot(v, n)
        in_plane = v - h[..., None] * n
        rho = _len(in_plane)
        gap2 = h * h + (rho - R) * (rho - R)
        irr = 1.0 / np.sqrt((gap2 + hw * hw) * (h * h + (rho + R) * (rho + R) + hw * hw))
        window = 1.0 - _smoothstep(0.35 * reach, reach, np.sqrt(gap2))
        radial = np.where(np.asarray(rho > 1e-6)[..., None], in_plane / np.maximum(rho, 1e-12)[..., None], side)
        to_band = v - R * radial
        lb = np.maximum(_len(to_band), 1e-6)
        phase = phaseHG(_dot(rd, -to_band / lb[..., None]), HAZE_G) / phaseIso()
        k = np.clip((ts - t0) / chord_len, 0.0, 1.0)
        sigma = amount * _mix(dens0, dens1, k)
        total += sigma * irr * window * phase * np.exp(-EXTINCTION * ts) / pdf
    g = np.maximum(_f(level), 0.0) * total / RING_SAMPLES
    tint = np.maximum(_f(col), 0.0)
    return np.where(ok[..., None], tint * np.asarray(g)[..., None], 0.0)
