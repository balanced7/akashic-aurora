"""CPU twin of the ray modules (atlas family E: arsenal/web/glsl/ray/intersect.glsl, camera.glsl, march.glsl,
normals.glsl, aa3.glsl): from a pixel to a point on a surface, its normal and how much of the pixel it covers. Pinned by
tests/test_glsl_twins_3d_rays.py.

WHY. The ray modules are the part of a 3D shader that turns distance promises into pictures, and they fail in ways a
screenshot cannot explain: a marcher that steps one epsilon too far shows a halo of floor colour around every object, a
sphere intersection written the short way loses a small marble seen from far away, a pixel angle off by a factor of two
makes every distant normal sparkle. This file runs the same maths on the CPU, in float32 like the GPU, so a test can
compare it with float64 references, finite differences and the textbook's own fixed points.

Names match the GLSL names exactly. A function that calls the host's scene hook (`float mapScene(vec3 p)` in GLSL)
takes it here as its LAST argument, a Python callable of a 3-vector; the march loops run the same constant caps (256
steps, 16 bisections, 8 refinements) and the same epsilon floor (1e-4) as the GLSL. Where GLSL writes through an `out`
or `inout` parameter, the twin returns the function's own value first and the written values after it: ixBox returns
((tNear, tFar), entryNormal). Matrices are numpy 3x3 arrays whose COLUMNS are the GLSL mat3's columns.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; no corpus code.
"""
from __future__ import annotations

import math

import numpy as np

F32 = np.float32
TAU = F32(2.0 * math.pi)
MARCH_CAP = 256          # every march loop's literal bound in the GLSL
BISECT_CAP = 16
REFINE_CAP = 8
EPS_FLOOR = F32(1e-4)    # rmSphereTrace's and rmRelaxed's smallest hit threshold, in scene units


def _f(x):
    return np.asarray(x, dtype=F32)


def _s(x):
    x = np.asarray(x, dtype=F32)
    return x[()] if x.ndim == 0 else x


def _len(v):
    v = _f(v)
    return F32(np.sqrt(np.sum(v * v, dtype=F32)))


def _normalize(v, fallback):
    v = _f(v)
    l2 = float(np.sum(v * v, dtype=F32))
    return (v / F32(math.sqrt(l2))).astype(F32) if l2 > 1e-24 else _f(fallback)


def _v2(x, y):
    return np.array([x, y], dtype=F32)


MISS = _v2(-1.0, -1.0)


# =========================================================================================== ray/intersect.glsl
def ixSphere(ro, rd, centre, r):
    ro, rd, centre = _f(ro), _f(rd), _f(centre)
    fromCentre = ro - centre
    along = F32(np.dot(fromCentre, rd))
    across = fromCentre - rd * along                     # the centre's perpendicular offset from the ray
    room = F32(r) * F32(r) - F32(np.dot(across, across))
    if room < 0:
        return MISS.copy()
    half = F32(math.sqrt(float(room)))
    return _v2(-along - half, -along + half)


def ixBox(roLocal, rdLocal, halfSize):
    ro, rd, half = _f(roLocal), _f(rdLocal), _f(halfSize)
    steady = np.where(np.abs(rd) < F32(1e-12), F32(1e-12), rd).astype(F32)
    perUnit = F32(1) / steady
    middle = -ro * perUnit
    spread = np.abs(perUnit) * half
    enter = middle - spread
    leave = middle + spread
    near = F32(max(enter))
    far = F32(min(leave))
    if near > far or far < 0:
        return MISS.copy(), np.zeros(3, dtype=F32)
    if enter[0] >= max(enter[1], enter[2]):
        axis = np.array([1, 0, 0], dtype=F32)
    elif enter[1] >= enter[2]:
        axis = np.array([0, 1, 0], dtype=F32)
    else:
        axis = np.array([0, 0, 1], dtype=F32)
    return _v2(near, far), (-np.sign(steady) * axis).astype(F32)


def ixPlane(ro, rd, n, offset):
    facing = F32(np.dot(_f(rd), _f(n)))
    if abs(facing) < 1e-8:
        return F32(-1.0)
    t = -(F32(np.dot(_f(ro), _f(n))) + F32(offset)) / facing
    return F32(t) if t >= 0 else F32(-1.0)


def ixSlabY(oy, dy, y0, y1):
    oy, dy, y0, y1 = F32(oy), F32(dy), F32(y0), F32(y1)
    if abs(dy) < 1e-12:
        within = min(y0, y1) <= oy <= max(y0, y1)
        return _v2(0.0, 1e30) if within else _v2(1.0, -1.0)
    ta, tb = (y0 - oy) / dy, (y1 - oy) / dy
    return _v2(max(min(ta, tb), F32(0)), max(ta, tb))


def ixShell(o, d, c, rIn, rOut):
    outer = ixSphere(o, d, c, rOut)
    if outer[1] < 0:
        return _v2(1.0, -1.0)
    start = max(outer[0], F32(0))
    inner = ixSphere(o, d, c, rIn)
    if inner[1] < start:
        return _v2(start, outer[1])
    if start < inner[0]:
        return _v2(start, inner[0])
    return _v2(inner[1], outer[1])


def rmClipToBox(ro, rd, centre, halfSize, tRange):
    box, _ = ixBox(_f(ro) - _f(centre), rd, halfSize)
    if box[1] < 0:
        return _v2(1.0, -1.0)
    return _v2(max(F32(tRange[0]), box[0]), min(F32(tRange[1]), box[1]))


def bvCanSkip(boundDistance, bestSoFar):
    return bool(F32(boundDistance) > F32(bestSoFar))


def ixSphereAlt(r0, mu0, R):
    r0, mu0, R = F32(r0), F32(mu0), F32(R)
    half = r0 * mu0                                   # the ray's half-coefficient: t^2 + 2 half t + gap = 0
    gap = (r0 - R) * (r0 + R)                         # r0^2 - R^2 without subtracting two huge squares
    room = half * half - gap
    if room < 0:
        return MISS.copy()
    root = F32(math.sqrt(float(room)))
    big = -(half + (root if half >= 0 else -root))    # the root that adds magnitudes, never cancels
    if abs(big) < 1e-30:
        return _v2(0.0, 0.0)
    small = gap / big
    return _v2(min(big, small), max(big, small))


# ============================================================================================== ray/camera.glsl
def camLookAt(ro, target, roll):
    forward = _normalize(_f(target) - _f(ro), [0.0, 0.0, -1.0])
    helper = np.array([0, 0, 1], dtype=F32) if abs(forward[1]) > 0.999 else np.array([0, 1, 0], dtype=F32)
    right = _normalize(np.cross(forward, helper), [1.0, 0.0, 0.0])
    up = np.cross(right, forward).astype(F32)
    c, s = F32(math.cos(float(roll))), F32(math.sin(float(roll)))
    rolledRight = c * right + s * up
    rolledUp = c * up - s * right
    return np.stack([rolledRight, rolledUp, -forward], axis=1).astype(F32)


def camRay(fragCoord, res, basis, focal):
    frag, res = _f(fragCoord), _f(res)
    uv = (F32(2) * frag - res) / res[1]
    return _normalize(_f(basis) @ np.array([uv[0], uv[1], -F32(focal)], dtype=F32), [0.0, 0.0, -1.0])


def camPixelAngle(fovY, heightPx):
    return _s(F32(2) * F32(math.tan(0.5 * float(fovY))) / F32(heightPx))


def camOrbit(mouse01, autoYaw, radius, target):
    m = _f(mouse01)
    untouched = float(np.dot(m, m)) < 1e-10
    yaw = F32(autoYaw) if untouched else (m[0] - F32(0.5)) * TAU
    pitch = F32(0.3) if untouched else (m[1] - F32(0.5)) * F32(2.8)
    cp = F32(math.cos(float(pitch)))
    offset = np.array([cp * F32(math.sin(float(yaw))), F32(math.sin(float(pitch))), cp * F32(math.cos(float(yaw)))],
                      dtype=F32)
    return (_f(target) + F32(radius) * offset).astype(F32)


def camOrthoRay(p, basis, scale, ro):
    basis = _f(basis)
    p = _f(p) * F32(scale)
    return (-basis[:, 2]).astype(F32), (_f(ro) + basis @ np.array([p[0], p[1], 0.0], dtype=F32)).astype(F32)


def pathLissajous3(t, amp, freq):
    t, amp, freq = F32(t), _f(amp), _f(freq)
    flight = np.abs(freq) <= F32(1e-6)
    phase = freq * t
    pos = np.where(flight, amp * t, amp * np.sin(phase))
    vel = np.where(flight, amp, amp * freq * np.cos(phase))
    acc = np.where(flight, F32(0), -amp * freq * freq * np.sin(phase))
    return pos.astype(F32), vel.astype(F32), acc.astype(F32)


def camBanked(vel, acc, bankGain):
    forward = _normalize(vel, [0.0, 0.0, -1.0])
    upHint = np.array([0, 1, 0], dtype=F32) + F32(bankGain) * _f(acc)
    right = _normalize(np.cross(forward, upHint), [1.0, 0.0, 0.0])
    up = np.cross(right, forward).astype(F32)
    return np.stack([right, up, -forward], axis=1).astype(F32)


def camBarrel(p, k):
    p = _f(p)
    return (p * (F32(1) + F32(k) * F32(np.dot(p, p)))).astype(F32)


# ================================================================================================ ray/march.glsl
def rmEpsilon(t, pixelAngle, epsMin):
    return _s(max(F32(epsMin), F32(0.5) * F32(pixelAngle) * F32(t)))


def _at(ro, rd, t):
    return (_f(ro) + _f(rd) * F32(t)).astype(F32)


def rmSphereTrace(ro, rd, tRange, pixelAngle, omega, maxSteps, mapScene):
    stride = min(max(F32(omega), F32(0.1)), F32(1.0))
    t = F32(tRange[0])
    outward, steps, hit = F32(1), 0, 0
    closest, closestT = F32(1e10), t
    for i in range(MARCH_CAP):
        if i >= maxSteps:
            break
        d = F32(mapScene(_at(ro, rd, t)))
        if i == 0 and d < 0:
            outward = F32(-1)                          # started inside a solid: trace its inner wall
        d = outward * d
        steps += 1
        ratio = d / max(t, F32(1e-6))
        if ratio < closest:
            closest, closestT = ratio, t
        if d < rmEpsilon(t, pixelAngle, EPS_FLOOR):
            hit = 1
            break
        t = F32(t + stride * d)
        if t > F32(tRange[1]):
            break
    return np.array([t if hit else closestT, steps, max(closest, F32(0)), hit], dtype=F32)


def rmRelaxed(ro, rd, tRange, pixelAngle, omega, maxSteps, mapScene):
    stride = min(max(F32(omega), F32(1.0)), F32(1.95))
    t = F32(tRange[0])
    outward, steps, hit = F32(1), 0, 0
    closest, closestT = F32(1e10), t
    lastT, lastR = t, F32(0)
    for i in range(MARCH_CAP):
        if i >= maxSteps:
            break
        d = F32(mapScene(_at(ro, rd, t)))
        if i == 0 and d < 0:
            outward = F32(-1)
        d = outward * d
        steps += 1
        # the relaxed step landed inside a solid (d < 0: an exact tie of the overlap check, head on, used to let it pass
        # and the negative d then counted as a hit), or the two spheres leave a gap: take the plain step instead
        if stride > 1 and i > 0 and (d < 0 or lastR + abs(d) < t - lastT):
            t = F32(lastT + lastR)
            stride = F32(1)
            continue
        ratio = d / max(t, F32(1e-6))
        if ratio < closest:
            closest, closestT = ratio, t
        if d < rmEpsilon(t, pixelAngle, EPS_FLOOR):
            hit = 1
            break
        lastT, lastR = t, d
        t = F32(t + stride * d)
        if t > F32(tRange[1]):
            break
    return np.array([t if hit else closestT, steps, max(closest, F32(0)), hit], dtype=F32)


def rmBacktrack(ro, rd, tRange, pixelAngle, maxSteps, bisectSteps, mapScene):
    t = F32(tRange[0])
    outward, steps, hit = F32(1), 0, 0
    closest, closestT = F32(1e10), t
    lastT = t
    for i in range(MARCH_CAP):
        if i >= maxSteps:
            break
        d = F32(mapScene(_at(ro, rd, t)))
        if i == 0 and d < 0:
            outward = F32(-1)
        d = outward * d
        steps += 1
        if d < 0:                                      # stepped through a surface: it lies between lastT and t
            outsideT, insideT = lastT, t
            for j in range(BISECT_CAP):
                if j >= bisectSteps:
                    break
                middle = F32(0.5) * (outsideT + insideT)
                steps += 1
                if outward * F32(mapScene(_at(ro, rd, middle))) < 0:
                    insideT = middle
                else:
                    outsideT = middle
            t, hit = outsideT, 1
            closest = F32(0)
            break
        ratio = d / max(t, F32(1e-6))
        if ratio < closest:
            closest, closestT = ratio, t
        if d < rmEpsilon(t, pixelAngle, EPS_FLOOR):
            hit = 1
            break
        lastT = t
        t = F32(t + d)
        if t > F32(tRange[1]):
            break
    return np.array([t if hit else closestT, steps, max(closest, F32(0)), hit], dtype=F32)


def rmPassStep(d, passthrough, density):
    return _s(max(F32(passthrough) + abs(F32(d)) / max(F32(density), F32(1e-6)), F32(1e-4)))


def rmHybridStep(sdf, adaptive):
    return _s(max(F32(sdf), F32(adaptive)))


def rmJitterStart(tStart, dt, u):
    return _s(F32(tStart) + F32(u) * F32(dt))


def rmSecondaryOrigin(p, n, fAtHit, epsMin, side):
    push = F32(side) * F32(2) * max(F32(epsMin), abs(F32(fAtHit)))
    return (_f(p) + _f(n) * push).astype(F32)


def rmRefine(ro, rd, t, pixelAngle, iters, mapScene):
    t = F32(t)
    for j in range(REFINE_CAP):
        if j >= iters:
            break
        t = F32(t + F32(mapScene(_at(ro, rd, t))) - F32(0.5) * F32(pixelAngle) * t)
    return _s(t)


# ============================================================================================== ray/normals.glsl
def _first_tap(h, taps):
    """The loop start the GLSL uses: 0 for any h above -1, -taps below (every tap twice, still symmetric)."""
    whole = int(min(float(h), 0.0))                   # int() truncates toward zero, like GLSL int()
    return taps * min(max(whole, -1), 0)


def _tetra_corner(index):
    high, low = (index >> 1) & 1, index & 1
    ky, kz = F32(2 * high - 1), F32(2 * low - 1)
    return np.array([ky * kz, ky, kz], dtype=F32)


def nrmTetra(p, h, mapScene):
    reach = max(abs(F32(h)), F32(1e-7))
    total = np.zeros(3, dtype=F32)
    for tap in range(_first_tap(h, 4), 4):
        corner = _tetra_corner((tap + 4) & 3)
        total += corner * F32(mapScene((_f(p) + corner * reach).astype(F32)))
    return _normalize(total, [0.0, 1.0, 0.0])


def nrmEps(t, pixelAngle, materialScale):
    return _s(F32(materialScale) * max(F32(pixelAngle) * F32(t), F32(1e-5)))


def nrmCentral(p, h, mapScene):
    reach = max(abs(F32(h)), F32(1e-7))
    total = np.zeros(3, dtype=F32)
    for tap in range(_first_tap(h, 6), 6):
        index = (tap + 6) % 6
        axis = np.zeros(3, dtype=F32)
        axis[index >> 1] = F32(2 * (index & 1) - 1)
        total += axis * F32(mapScene((_f(p) + axis * reach).astype(F32)))
    return _normalize(total, [0.0, 1.0, 0.0])


def nrmCurvature(p, h, mapScene):
    reach = max(abs(F32(h)), F32(1e-7))
    around = F32(0)
    for tap in range(_first_tap(h, 4), 4):
        corner = _tetra_corner((tap + 4) & 3)
        around += F32(mapScene((_f(p) + corner * reach).astype(F32)))
    taps = F32(4 - _first_tap(h, 4))
    centre = F32(mapScene(_f(p)))
    return _s((around - taps * centre) / (F32(0.5) * taps * reach * reach))


def nrmFacet(n, steps):
    n = _f(n)
    return _normalize(np.floor(n * F32(steps) + F32(0.5)), n)


# ================================================================================================== ray/aa3.glsl
def aaConeCoverage(minDistOverT, pixelAngle):
    x = 2.0 * float(minDistOverT) / max(float(pixelAngle), 1e-12) - 2.0
    x = min(max(x, -1.0), 1.0)
    return _s((math.acos(x) - x * math.sqrt(max(1.0 - x * x, 0.0))) / math.pi)


def aaDiscriminantEdge(disc, px):
    x = min(max(-2.0 * float(disc) / max(float(px), 1e-12), -1.0), 1.0)
    return _s((math.acos(x) - x * math.sqrt(max(1.0 - x * x, 0.0))) / math.pi)
