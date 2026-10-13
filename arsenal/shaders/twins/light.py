"""CPU twins of the house light modules: arsenal/web/glsl/light/*.glsl (atlas family F, shader school batch B).

WHY. Lighting is an energy budget, and an energy bug hides on screen: a wrap term that adds light, a specular lobe
that dims as it sharpens, a shadow that darkens an open floor. Each GLSL function here has a numpy twin with the same
name and maths, so tests/test_glsl_twins_light.py can check the physics a contract claims (an integral over the
sphere, Snell's law, Beer-Lambert) on the CPU, and then pin the GLSL to the twin on SwiftShader.

Conventions, as in the modules: y is up; n is the unit surface normal, l the unit direction toward a light, v the unit
direction toward the eye; colours are linear light. Vectors are array-likes whose last axis is xyz (or rgb), so most
twins also take a whole array of directions at once. The scene-dependent twins (visSoftShadow, visAO) take the scene
as their first argument, a callable p -> signed distance, where the GLSL calls the host's mapScene hook.

A GLSL overload has two twin names: litFresnelSchlick(cosTheta, F0) is the float form and litFresnelSchlick3(F0,
cosTheta) the vec3 one.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; credits in each module's header.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

VIS_MAX_SHADOW_STEPS = 64       # visibility.glsl's constant loop ceiling (a literal 64 there)
BOX_EDGE_SHARP = 0.04           # env.glsl: a soft box's edge half-width at roughness 0 (in panel radii) ...
BOX_EDGE_ROUGH = 0.9            # ... and at roughness 1
STUDIO_BACK_FACING = 1e-4       # env.glsl: a box is skipped where 0.5 + 0.5 dot(dir, boxDir) is below this (its antipode)
UP = np.array([0.0, 1.0, 0.0])


def _v(x):
    return np.asarray(x, dtype=float)


def _dot(a, b):
    return np.sum(_v(a) * _v(b), axis=-1)


def _unit(v, fallback=(0.0, 1.0, 0.0)):
    """core-safe's safeNormalize: v / |v|, or the fallback when dot(v, v) <= 1e-24."""
    v = _v(v)
    sq = np.sum(v * v, axis=-1, keepdims=True)
    safe = np.where(sq > 1e-24, sq, 1.0)
    return np.where(sq > 1e-24, v / np.sqrt(safe), _v(fallback))


def _smoothstep(e0, e1, x):
    t = np.clip((_v(x) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _safe_pow(b, e):
    """core-safe's safePow: the base floored at 1e-30."""
    return np.power(np.maximum(_v(b), 1e-30), _v(e))


# ------------------------------------------------------------------------------------------------- light/diffuse.glsl
def litLambert(n, l):
    """max(n . l, 0): the cosine a slanted beam spreads by. Pi is folded into the light's colour."""
    return np.maximum(_dot(n, l), 0.0)


def litHalfLambert(n, l):
    """(0.5 n.l + 0.5)^2 (Valve, 2006): the back keeps its shape; not energy-conserving, a stylisation."""
    half = 0.5 * _dot(n, l) + 0.5
    return half * half


def litWrapDiffuse(n, l, w):
    """max((n.l + w) / (1 + w)^2, 0), w clamped to [0, 1]: wrapped past the terminator, total energy still Lambert's."""
    w = np.clip(_v(w), 0.0, 1.0)
    spread = 1.0 + w
    return np.maximum((_dot(n, l) + w) / (spread * spread), 0.0)


def litHemisphere(n, skyCol, groundCol):
    """mix(ground, sky, 0.5 + 0.5 n.y): the irradiance of a uniform sky dome over a uniform ground, exact unoccluded."""
    share = (0.5 + 0.5 * _v(n)[..., 1])[..., None]
    return _v(groundCol) + (_v(skyCol) - _v(groundCol)) * share


# ------------------------------------------------------------------------------------------------ light/specular.glsl
def litBlinnPhong(n, h, shininess):
    """(s + 8) / (8 pi) * max(n.h, 0)^s: the normalised Blinn-Phong BRDF lobe (per steradian)."""
    s = np.maximum(_v(shininess), 0.0)
    return (s + 8.0) / (8.0 * math.pi) * _safe_pow(np.maximum(_dot(n, h), 0.0), s)


# ------------------------------------------------------------------------------------------------- light/fresnel.glsl
def litFresnelSchlick(cosTheta, F0):
    """Schlick, float form: F0 + (1 - F0)(1 - cos)^5, the cosine clamped to [0, 1]."""
    m = np.clip(1.0 - _v(cosTheta), 0.0, 1.0)
    m2 = m * m
    return _v(F0) + (1.0 - _v(F0)) * (m2 * m2 * m)


def litFresnelSchlick3(F0, cosTheta):
    """Schlick, the vec3 overload litFresnelSchlick(vec3 F0, float cosTheta): per channel."""
    m = np.clip(1.0 - _v(cosTheta), 0.0, 1.0)[..., None]
    m2 = m * m
    F0 = _v(F0)
    return F0 + (1.0 - F0) * (m2 * m2 * m)


def litF0FromIor(ior):
    """((n - 1) / (n + 1))^2 against air (or for a relative index n); n floored at 0."""
    n = np.maximum(_v(ior), 0.0)
    r = (n - 1.0) / (n + 1.0)
    return r * r


def litRim(NoV, power):
    """(1 - clamp(NoV, 0, 1))^power: an art rim, never a Fresnel. The base is floored at 1e-30 (core-safe safePow)."""
    return _safe_pow(1.0 - np.clip(_v(NoV), 0.0, 1.0), power)


# -------------------------------------------------------------------------------------------------- light/lights.glsl
def litInverseSquare(dist, radius):
    """clamp(1 - (d/r)^4, 0, 1)^2 / max(d^2, 0.01^2): inverse square, windowed to reach zero at the radius."""
    d = np.maximum(_v(dist), 0.0)
    ratio = d / np.maximum(_v(radius), 1e-6)
    r2 = ratio * ratio
    window = np.clip(1.0 - r2 * r2, 0.0, 1.0)
    return window * window / np.maximum(d * d, 1e-4)


# --------------------------------------------------------------------------------------------------- light/glass.glsl
def litRefractTIR(i, n, eta):
    """Snell refraction of the unit direction i at a surface with unit normal n (either side), eta = n_from / n_to.
    Returns (True, t) with the refracted direction, or (False, mirror) under total internal reflection."""
    i, n = _v(i), _v(n)
    facing = -n if float(i @ n) > 0.0 else n
    cos_i = -float(i @ facing)
    sin2_t = eta * eta * (1.0 - cos_i * cos_i)
    if sin2_t > 1.0:
        return False, i + 2.0 * cos_i * facing
    return True, eta * i + (eta * cos_i - math.sqrt(1.0 - sin2_t)) * facing


def litSigmaFromColour(colourAtDist, dist):
    """-ln(c) / dist, c clamped to [1e-6, 1] and dist floored at 1e-6: white light becomes c after dist."""
    c = np.clip(_v(colourAtDist), 1e-6, 1.0)
    return -np.log(c) / max(float(dist), 1e-6)


# ---------------------------------------------------------------------------------------------------- light/glow.glsl
def glowAccum(acc, colour, d, minD):
    """acc + colour / max(d, minD) (minD floored at 1e-6): the 1/d halo, one march step's worth."""
    return _v(acc) + _v(colour) / max(float(d), max(float(minD), 1e-6))


def glowEmitStep(density, stepLen, k):
    """k * density * max(stepLen, 0): emission integrated over one step, so the sum is independent of the step count."""
    return float(k) * float(density) * max(float(stepLen), 0.0)


def glowExp(minDist, k):
    """exp(-k * max(minDist, 0)): closest-approach glow."""
    return np.exp(-_v(k) * np.maximum(_v(minDist), 0.0))


def glowLorentz(d, k):
    """k / (k + d^2), k floored at 1e-12: a needle core of height 1 and tails falling as k / d^2."""
    w = np.maximum(_v(k), 1e-12)
    return w / (w + _v(d) * _v(d))


def glowTwoGauss(d, coreHalo):
    """coreGain e^(-coreSharp d^2) + haloGain e^(-haloSharp d^2), coreHalo = (coreSharp, coreGain, haloSharp,
    haloGain): the house light-line profile."""
    ch = _v(coreHalo)
    d2 = _v(d) * _v(d)
    return ch[1] * np.exp(-ch[0] * d2) + ch[3] * np.exp(-ch[2] * d2)


def glowHotCore(tint, intensity):
    """i * mix(tint, vec3(max channel), i^2 / (1 + i^2)): the hottest channel climbs as i * peak, the others follow it
    toward white as the intensity passes 1."""
    i = max(float(intensity), 0.0)
    tint = np.maximum(_v(tint), 0.0)
    peak = float(np.max(tint))
    white = i * i / (1.0 + i * i)
    return i * (tint + (peak - tint) * white)


def glowStepCount(steps, maxSteps, k):
    """1 - (1 - s)^k with s = clamp(steps / max(maxSteps, 1), 0, 1) and k floored at 1e-3: marcher effort as light."""
    used = min(max(float(steps) / max(float(maxSteps), 1.0), 0.0), 1.0)
    return 1.0 - math.pow(1.0 - used, max(float(k), 1e-3))


# ----------------------------------------------------------------------------------------------------- light/env.glsl
@dataclass(frozen=True)
class StudioParams:
    """The GLSL struct StudioParams, field for field (light/env.glsl)."""
    keyDir: np.ndarray
    keyCol: np.ndarray
    fillDir: np.ndarray
    fillCol: np.ndarray
    boxSize: np.ndarray
    rimBright: float
    skyCol: np.ndarray
    horizonCol: np.ndarray
    floorCol: np.ndarray
    floorDrop: float
    poolRadius: float
    keyWrap: float


def studio_default() -> StudioParams:
    """A neutral product-shot studio (twin-only helper: the GLSL library has no preset function, by the atlas naming
    law; env.glsl's note spells the same StudioParams(...) constructor, and the cards build it card-locally)."""
    return StudioParams(
        keyDir=_unit([-0.55, 0.75, 0.4]), keyCol=_v([3.6, 3.3, 2.9]),
        fillDir=_unit([0.65, 0.55, -0.55]), fillCol=_v([0.55, 0.7, 1.0]),
        boxSize=_v([0.42, 0.28]), rimBright=0.8,
        skyCol=_v([0.008, 0.01, 0.016]), horizonCol=_v([0.07, 0.075, 0.09]),
        floorCol=_v([0.32, 0.27, 0.22]), floorDrop=1.0, poolRadius=1.1, keyWrap=0.3)


def litFloorPool(p, centre, radius, col):
    """col * exp(-|p.xz - centre.xz|^2 / radius^2): a Gaussian disc of light on a horizontal floor."""
    off = (_v(p)[..., [0, 2]] - _v(centre)[..., [0, 2]]) / max(float(radius), 1e-6)
    return _v(col) * np.exp(-np.sum(off * off, axis=-1, keepdims=True))


def panel_frame(boxDir):
    """The soft box's own axes: across (horizontal) and along, both perpendicular to its direction."""
    b = _v(boxDir)
    across = _unit(np.cross(UP, b), (1.0, 0.0, 0.0))
    return across, np.cross(b, across)


def _studio_box(d, boxDir, col, size, rim, rough):
    """One soft box, in the equal-area coordinates around its direction (so blur keeps its solid-angle energy)."""
    across, along = panel_frame(boxDir)
    facing = 0.5 + 0.5 * _dot(d, boxDir)
    lift = 1.0 / np.sqrt(np.maximum(facing, 1e-6))
    q = np.stack([_dot(d, across), _dot(d, along)], axis=-1) * lift[..., None]
    u = np.abs(q) / _v(size)
    u2 = u * u
    edge = np.power(np.maximum(np.sum(u2 * u2, axis=-1), 1e-20), 0.25)     # a rounded square: 1 on the panel's rim
    width = BOX_EDGE_SHARP + (BOX_EDGE_ROUGH - BOX_EDGE_SHARP) * rough
    # the smoothstep's skirt adds 0.2 width^2 of the panel's area; divide it out, relative to the sharp panel
    keep = (1.0 + 0.2 * BOX_EDGE_SHARP * BOX_EDGE_SHARP) / (1.0 + 0.2 * width * width)
    inside = (1.0 - _smoothstep(1.0 - width, 1.0 + width, edge)) * keep
    # straight away from the box the projection is 0 / 0 and would land on the panel's centre: never on the panel
    inside = np.where(facing < STUDIO_BACK_FACING, 0.0, inside)
    # the frame's light (1 + rim (1 - rough) edge^2 averages 1 + rim (1 - rough) / 2 over a panel) fades with roughness;
    # spread it back over the panel, so the total stays the sharp panel's 1 + rim / 2 at every roughness
    spread = (1.0 + 0.5 * rim) / (1.0 + 0.5 * rim * (1.0 - rough))
    frame = (1.0 + rim * (1.0 - rough) * np.minimum(edge * edge, 1.0)) * spread
    return _v(col) * (inside * frame)[..., None]


def litStudioEnv(dir, roughness, s: StudioParams):
    """A dark studio dome: skyCol overhead, horizonCol at the horizon, a floor with a pool of floorCol below that
    dissolves into the horizon, and two rim-bright soft boxes whose edges widen with roughness."""
    d = _unit(dir)
    rough = min(max(float(roughness), 0.0), 1.0)
    up = d[..., 1]
    dome = s.horizonCol + (s.skyCol - s.horizonCol) * _smoothstep(0.0, 0.6, up)[..., None]
    reach = s.floorDrop / np.maximum(-up, 1e-6)                 # along d to the floor plane, while d points down
    spot = d * reach[..., None]
    far = np.sqrt(np.sum(spot[..., [0, 2]] ** 2, axis=-1))
    haze = (1.0 - np.exp(-far / (4.0 * max(s.poolRadius, 1e-6))))[..., None]
    ground = s.horizonCol * haze + litFloorPool(spot, np.zeros(3), s.poolRadius, s.floorCol)
    base = np.where((up < 0.0)[..., None], ground, dome)
    return (base + _studio_box(d, s.keyDir, s.keyCol, s.boxSize, s.rimBright, rough)
            + _studio_box(d, s.fillDir, s.fillCol, s.boxSize, s.rimBright, rough))


# ---------------------------------------------------------------------------------------------------- light/rigs.glsl
@dataclass(frozen=True)
class LitSurface:
    """The GLSL struct LitSurface, field for field (light/rigs.glsl)."""
    diffuseColor: np.ndarray
    F0: np.ndarray
    alpha: float
    emissive: np.ndarray = field(default_factory=lambda: np.zeros(3))


def rigStudio(s: LitSurface, n, v, ao, sp: StudioParams):
    """Wrapped key + sky (hemisphere) + back + rim on the diffuse colour, plus the studio reflected along the mirror
    direction weighted by Fresnel, plus the emission. ao darkens the fills and the reflection, never the key."""
    n, v = _v(n), _v(v)
    NoV = min(max(float(n @ v), 0.0), 1.0)
    open_ = min(max(float(ao), 0.0), 1.0)
    key = sp.keyCol * litWrapDiffuse(n, sp.keyDir, sp.keyWrap)
    sky = litHemisphere(n, sp.skyCol, sp.floorCol) * open_
    back = sp.fillCol * litLambert(n, sp.fillDir) * open_
    rim = sp.horizonCol * litRim(NoV, 2.0) * open_
    diffuse = _v(s.diffuseColor) * (key + sky + back + rim)
    r = 2.0 * float(n @ v) * n - v
    rough = math.sqrt(min(max(float(s.alpha), 0.0), 1.0))
    F0 = _v(s.F0)
    grazing = min(max(50.0 * float(F0 @ np.full(3, 1.0 / 3.0)), 0.0), 1.0)
    fres = F0 + (litFresnelSchlick3(F0, NoV) - F0) * grazing
    spec = litStudioEnv(r, rough, sp) * fres * open_
    return diffuse + spec + _v(s.emissive)


# ---------------------------------------------------------------------------------------------- light/visibility.glsl
def visSoftShadow(scene, ro, rd, tRange, lightAngle, maxSteps):
    """Visibility of a light of angular radius lightAngle along rd from ro, in [0, 1]: the closest-approach penumbra
    (Aaltonen's triangulation between consecutive unbounding spheres where they meet, the classic h/t where they do not
    or where it degenerates), steps clamped to [span / (8 n), 1.5 span / n], at most min(maxSteps, 64) scene
    evaluations, smoothstepped."""
    ro, rd = _v(ro), _v(rd)
    tmin = max(float(tRange[0]), 0.0)
    tmax = max(float(tRange[1]), tmin)
    steps = min(max(int(maxSteps), 1), VIS_MAX_SHADOW_STEPS)
    span = tmax - tmin
    floor_step = span / (8.0 * steps)
    ceil_step = 1.5 * span / steps
    spread = math.tan(min(max(float(lightAngle), 1e-4), 1.5))
    lit, t, before, last = 1.0, tmin, 0.0, 0.0
    for i in range(VIS_MAX_SHADOW_STEPS):
        if i >= steps or t >= tmax:
            break
        h = float(scene(ro + rd * t))
        if h <= 0.0:
            lit = 0.0
            break
        angle = h / max(t, 1e-6)                     # Quilez's h / t
        # Aaltonen's triangulation only where the step stayed inside the last empty ball (the stride was that ball's
        # own radius, or less) and the two balls meet in a circle. A step clamped UP to the shortest stride leaves the
        # last ball behind: the balls then miss each other, or barely touch in a tiny circle, and the triangulated near
        # miss collapses toward 0, a black shadow on an unoccluded floor under a low light (batch-B review, defect 1)
        meet = 0.0 < last <= before and last < before + h and abs(h - before) < last
        if meet:
            y = min(max((last * last + h * h - before * before) / (2.0 * last), 0.0), h)
            miss = math.sqrt(max(h * h - y * y, 0.0))
            along = t - y
            if along > tmin:
                angle = miss / along
        lit = min(lit, angle / spread)
        if lit < 0.004:
            break
        before = h
        last = min(max(h, floor_step), ceil_step)
        t += last
    lit = min(max(lit, 0.0), 1.0)
    return lit * lit * (3.0 - 2.0 * lit)


def visAO(scene, p, n, reach, falloff):
    """Five taps along the normal at reach * (1..5) / 5; each tap's missing room (h - scene) / h clamped to [0, 1],
    weighted falloff^i (falloff clamped to [0, 1]); 1 - the weighted mean. 1 is fully open."""
    p, n = _v(p), _v(n)
    r = max(float(reach), 1e-6)
    fall = min(max(float(falloff), 0.0), 1.0)
    short, total, weight = 0.0, 0.0, 1.0
    for i in range(5):
        h = r * (i + 1) / 5.0
        room = float(scene(p + n * h))
        short += weight * min(max((h - room) / h, 0.0), 1.0)
        total += weight
        weight *= fall
    return 1.0 - short / total
