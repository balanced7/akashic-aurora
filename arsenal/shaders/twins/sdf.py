"""CPU twin of the distance-field modules (atlas family D: arsenal/web/glsl/sdf/shapes.glsl, combine.glsl, domain3.glsl):
the shapes, the ways of combining them and the ways of folding space before them. Pinned by
tests/test_glsl_twins_3d_rays.py.

WHY. A distance field is a promise ("no surface is closer than this"), and a marcher steps exactly that far on trust. A
shape that over-reports by a hair leaves holes that crawl as the camera moves; a combiner that changes the order of its
arguments carves the wrong solid; a twist without its stretch factor punches through. None of that can be printed from a
shader, so this file is the same maths on the CPU, in float32 like the GPU, where a test can measure it against
references that share none of its formulas. The bench multimeter beside the oscilloscope.

Names match the GLSL names exactly (a grep for `opSmin` finds both halves). Where GLSL writes through an `inout`
parameter, the twin returns the written value first and the function's own return value second: domRepeat(p, period)
returns (p, cellId). Matrices are numpy 3x3 arrays whose COLUMNS are what the GLSL mat3's columns are, so `M @ v` here is
`M * v` there. polyhedronNormals and polyhedronFace are twin-only helpers that expose sbPolyhedron's face table to a test.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; no corpus code.
"""
from __future__ import annotations

import math

import numpy as np

F32 = np.float32
PHI = F32((1.0 + math.sqrt(5.0)) / 2.0)


def _f(x):
    return np.asarray(x, dtype=F32)


def _s(x):
    """A 0-d result as a numpy float32 scalar, so `twin(...) == 1.0` reads naturally in a test."""
    x = np.asarray(x, dtype=F32)
    return x[()] if x.ndim == 0 else x


def _len(v):
    v = _f(v)
    return F32(np.sqrt(np.sum(v * v, dtype=F32)))


def _clamp(x, lo, hi):
    return np.minimum(np.maximum(_f(x), F32(lo)), F32(hi))


def _mix(x, y, a):
    x, y, a = _f(x), _f(y), _f(a)
    return (x * (F32(1) - a) + y * a).astype(F32)


# ============================================================================================== sdf/shapes.glsl
def sdSphere(p, r):
    return _s(_len(p) - F32(r))


def sdBox(p, halfSize):
    beyond = np.abs(_f(p)) - _f(halfSize)
    outside = _len(np.maximum(beyond, F32(0)))
    inside = min(float(np.max(beyond)), 0.0)
    return _s(outside + F32(inside))


def sdRoundBox(p, halfSize, cornerRadius):
    r = F32(cornerRadius)
    return _s(sdBox(p, _f(halfSize) - r) - r)


def sdPlane(p, unitNormal, offset):
    return _s(np.dot(_f(p), _f(unitNormal)) + F32(offset))


def sdTorusY(p, ringRadius, tubeRadius):
    p = _f(p)
    meridian = np.array([math.hypot(float(p[0]), float(p[2])) - float(ringRadius), float(p[1])], dtype=F32)
    return _s(_len(meridian) - F32(tubeRadius))


def sdCapsule(p, a, b, r):
    p, a, b = _f(p), _f(a), _f(b)
    fromA, run = p - a, b - a
    along = float(np.dot(fromA, run)) / max(float(np.dot(run, run)), 1e-12)
    along = min(max(along, 0.0), 1.0)
    return _s(_len(fromA - run * F32(along)) - F32(r))


def _extrude(d2, axial):
    """The box pattern in two dimensions: the positive part's length plus the clamped interior."""
    w = np.array([d2, axial], dtype=F32)
    return F32(min(max(float(w[0]), float(w[1])), 0.0)) + _len(np.maximum(w, F32(0)))


def sdCylinderY(p, r, halfHeight):
    p = _f(p)
    radial = math.hypot(float(p[0]), float(p[2])) - float(r)
    return _s(_extrude(radial, abs(float(p[1])) - float(halfHeight)))


def sdConeCappedY(p, h, rBottom, rTop):
    p = _f(p)
    q = np.array([math.hypot(float(p[0]), float(p[2])), float(p[1])], dtype=F32)
    h, rB, rT = F32(h), F32(rBottom), F32(rTop)
    capRadius = rB if q[1] < 0 else rT
    toCap = np.array([q[0] - min(q[0], capRadius), abs(q[1]) - h], dtype=F32)
    foot = np.array([rB, -h], dtype=F32)
    side = np.array([rT - rB, h + h], dtype=F32)
    along = min(max(float(np.dot(q - foot, side)) / float(np.dot(side, side)), 0.0), 1.0)
    toSide = q - foot - side * F32(along)
    inside = toSide[0] < 0 and toCap[1] < 0
    nearest = math.sqrt(min(float(np.dot(toCap, toCap)), float(np.dot(toSide, toSide))))
    return _s(-nearest if inside else nearest)


def sdRoundConeAB(p, a, b, ra, rb):
    p, a, b = _f(p), _f(a), _f(b)
    ra, rb = F32(ra), F32(rb)
    axis = b - a
    length = _len(axis)
    if length <= abs(ra - rb):                       # one ball holds the other: the hull is the bigger ball
        return _s(min(_len(p - a) - ra, _len(p - b) - rb))
    up = axis / length
    rel = p - a
    y = F32(np.dot(rel, up))
    x = _len(rel - up * y)
    slope = (ra - rb) / length                       # sine of the cone's half-angle
    lean = F32(math.sqrt(max(1.0 - float(slope) * float(slope), 0.0)))
    along = -x * slope + y * lean                    # position along the tangent line
    if along < 0:
        return _s(math.hypot(float(x), float(y)) - ra)
    if along > length * lean:
        return _s(math.hypot(float(x), float(y - length)) - rb)
    return _s(x * lean + y * slope - ra)


def sdHexPrismZ(p, apothem, halfDepth):
    p = _f(p)
    a = F32(apothem)
    q = np.abs(p[:2]).astype(F32)
    mirror = np.array([-math.sqrt(3.0) / 2.0, 0.5], dtype=F32)          # the 60-degree line's normal, facing up-left
    below = min(float(np.dot(q, mirror)), 0.0)
    q = q - F32(2.0 * below) * mirror                                    # q now lies between 60 and 120 degrees
    halfEdge = a / F32(math.sqrt(3.0))
    toEdge = np.array([q[0] - min(max(float(q[0]), -float(halfEdge)), float(halfEdge)), q[1] - a], dtype=F32)
    d2 = _len(toEdge) * (F32(1) if toEdge[1] > 0 else F32(-1))
    return _s(_extrude(d2, abs(float(p[2])) - float(halfDepth)))


def sdOctahedron(p, s):
    q = np.abs(_f(p))
    s = F32(s)
    over = F32(np.sum(q)) - s                        # how far past the face plane, measured along (1, 1, 1)
    third = over / F32(3)
    if q[0] < third:
        w = q
    elif q[1] < third:
        w = q[[1, 2, 0]]
    elif q[2] < third:
        w = q[[2, 0, 1]]
    else:
        return _s(over / F32(math.sqrt(3.0)))
    along = min(max(0.5 * float(w[2] - w[1] + s), 0.0), float(s))
    return _s(_len(np.array([w[0], w[1] - s + along, w[2] - along], dtype=F32)))


def sbEllipsoid(p, radii):
    p, radii = _f(p), _f(radii)
    stretched = _len(p / radii)
    if stretched < 1:
        return _s((stretched - F32(1)) * F32(np.min(radii)))
    slope = _len(p / (radii * radii))
    return _s(stretched * (stretched - F32(1)) / max(slope, F32(1e-20)))


_GROUP_AXES, _GROUP_DIAGONALS, _GROUP_DODECA, _GROUP_ICOSA = 1, 2, 4, 8
_KIND_GROUPS = (_GROUP_AXES, _GROUP_DIAGONALS, _GROUP_DODECA, _GROUP_DIAGONALS | _GROUP_ICOSA,
                _GROUP_AXES | _GROUP_DIAGONALS, _GROUP_DIAGONALS | _GROUP_DODECA | _GROUP_ICOSA)


def _face_table():
    """The 19 face directions (up to sign) of the solids sbPolyhedron knows, in the orientation where (0, 1, PHI) is an
    icosahedron vertex (the same orientation domFoldIcosa folds into), and the group bit of each: built from the face
    number exactly as the GLSL builds them (axes; the diagonal and its three single flips; cyclic shifts of
    (0, 1, +-PHI) and of (0, PHI, +-(PHI - 1)))."""
    tail = PHI - F32(1)
    out = []
    for face in range(19):
        if face < 3:
            v, bit = np.eye(3, dtype=F32)[face], _GROUP_AXES
        elif face < 7:
            corner = face - 3
            v = np.array([-1 if corner == 1 else 1, -1 if corner == 2 else 1, -1 if corner == 3 else 1], dtype=F32)
            bit = _GROUP_DIAGONALS
        else:
            member = face - 7 if face < 13 else face - 13
            flip = F32(1) if (member & 1) == 0 else F32(-1)
            seed = (np.array([0, 1, flip * PHI], dtype=F32) if face < 13
                    else np.array([0, PHI, flip * tail], dtype=F32))
            v = np.roll(seed, -(member >> 1))            # .yzx for one shift, .zxy for two
            bit = _GROUP_DODECA if face < 13 else _GROUP_ICOSA
        out.append(((v / _len(v)).astype(F32), bit))
    return out


def polyhedronNormals(solidKind):
    """Twin-only: the face directions (up to sign) sbPolyhedron uses for this kind."""
    groups = _KIND_GROUPS[min(max(int(solidKind), 0), len(_KIND_GROUPS) - 1)]
    return [n for n, bit in _face_table() if bit & groups]


def polyhedronFace(p, solidKind):
    """Twin-only: which face (normal index, side) is farthest out along p: the face p looks through."""
    best, face = -1e30, None
    for i, n in enumerate(polyhedronNormals(solidKind)):
        d = float(np.dot(_f(p), n))
        if abs(d) > best:
            best, face = abs(d), (i, 1 if d >= 0 else -1)
    return face


def sbPolyhedron(p, r, solidKind):
    reach = max(abs(float(np.dot(_f(p), n))) for n in polyhedronNormals(solidKind))
    return _s(F32(reach) - F32(r))


def sbSuperquadric(p, r, n):
    q = np.abs(_f(p) / _f(r))
    n = F32(n)
    biggest = max(float(np.max(q)), 1e-20)
    scaled = q / F32(biggest)                                            # every part <= 1: no overflow for big n
    norm = F32(biggest) * F32(np.sum(np.power(scaled, n), dtype=F32)) ** (F32(1) / n)
    stretch = F32(3.0) ** F32(max(1.0 / float(n) - 0.5, 0.0))           # how much faster than distance an Lp norm runs
    return _s((norm - F32(1)) * F32(np.min(_f(r))) / stretch)


def udTriangle(p, a, b, c):
    p, a, b, c = _f(p), _f(a), _f(b), _f(c)
    ab, bc, ca = b - a, c - b, a - c
    pa, pb, pc = p - a, p - b, p - c
    normal = np.cross(ab, ca).astype(F32)
    edgeSides = (np.sign(np.dot(np.cross(ab, normal), pa)) + np.sign(np.dot(np.cross(bc, normal), pb))
                 + np.sign(np.dot(np.cross(ca, normal), pc)))
    if edgeSides < 2:
        def seg(v, e):
            t = min(max(float(np.dot(v, e)) / max(float(np.dot(e, e)), 1e-20), 0.0), 1.0)
            return float(np.dot(v - e * F32(t), v - e * F32(t)))
        return _s(math.sqrt(min(seg(pa, ab), seg(pb, bc), seg(pc, ca))))
    return _s(abs(float(np.dot(normal, pa))) / max(float(_len(normal)), 1e-20))


# ============================================================================================= sdf/combine.glsl
def opUnion(a, b):
    return _s(min(F32(a), F32(b)))


def opIntersect(a, b):
    return _s(max(F32(a), F32(b)))


def opSubtract(a, b):
    return _s(max(F32(a), -F32(b)))


def opXor(a, b):
    a, b = F32(a), F32(b)
    return _s(max(min(a, b), -max(a, b)))


def opPick(a, b):
    a, b = _f(a), _f(b)
    return b.copy() if b[0] < a[0] else a.copy()


def _quadraticBlend(a, b, k):
    """(how far the two are inside the blend, 0..1; the blend's width): the quadratic kernel, normalised so that the
    junction dips by exactly k."""
    width = F32(4) * max(F32(k), F32(1e-20))
    inside = max(width - abs(F32(a) - F32(b)), F32(0)) / width
    return F32(inside), width


def opSmin(a, b, k):
    inside, width = _quadraticBlend(a, b, k)
    return _s(min(F32(a), F32(b)) - inside * inside * width * F32(0.25))


def opSminMix(a, b, k):
    inside, width = _quadraticBlend(a, b, k)
    d = min(F32(a), F32(b)) - inside * inside * width * F32(0.25)
    half = F32(0.5) * inside
    weightB = half if F32(a) < F32(b) else F32(1) - half
    return np.array([d, weightB], dtype=F32)


def opSmax(a, b, k):
    return _s(-opSmin(-F32(a), -F32(b), k))


def opSsubtract(a, b, k):
    return _s(opSmax(a, -F32(b), k))


def opSminCircular(a, b, k):
    radius = max(F32(k), F32(1e-20)) / F32(1.0 - math.sqrt(0.5))       # the fillet's radius
    gap = min(abs(F32(a) - F32(b)) / radius, F32(1))
    lift = F32(1) - F32(0.5) * (gap + F32(math.sqrt(max(2.0 - float(gap) * float(gap), 0.0))))
    return _s(min(F32(a), F32(b)) - radius * lift)


def opSminExp(a, b, k):
    k = max(F32(k), F32(1e-20))
    near = min(F32(a), F32(b))
    return _s(near - k * F32(math.log2(1.0 + 2.0 ** (-abs(float(a) - float(b)) / float(k)))))


def opRound(d, r):
    return _s(F32(d) - F32(r))


def opOnion(d, thickness):
    return _s(abs(F32(d)) - F32(thickness))


def opUniformScale(dAtScaledPoint, scale):
    return _s(F32(dAtScaledPoint) * F32(scale))


def opDisplace(d, displacement, lipschitz):
    return _s((F32(d) + F32(displacement)) / (F32(1) + F32(lipschitz)))


# ============================================================================================= sdf/domain3.glsl
def domRigid(p, rotation, position):
    return _s(_f(rotation).T @ (_f(p) - _f(position)))


def domMirror(p, axisMask):
    p = _f(p)
    return _s(_mix(p, np.abs(p), axisMask))


def _turn(x, y, angle):
    c, s = F32(math.cos(float(angle))), F32(math.sin(float(angle)))
    return c * F32(x) - s * F32(y), s * F32(x) + c * F32(y)


def domTwistY(p, rate):
    p = _f(p)
    x, z = _turn(p[0], p[2], F32(rate) * p[1])
    return np.array([x, p[1], z], dtype=F32)


def lipTwist(rate, maxRadius):
    shear = abs(F32(rate)) * F32(maxRadius)
    return _s(F32(0.5) * (shear + F32(math.sqrt(float(shear) * float(shear) + 4.0))))


def domBend(p, rate):
    p = _f(p)
    x, y = _turn(p[0], p[1], F32(rate) * p[0])
    return np.array([x, y, p[2]], dtype=F32)


def domRepeat(p, period):
    p, period = _f(p), np.maximum(_f(period), F32(1e-6))          # the period floored per axis, as domRepeat2's
    cell = np.floor(p / period + F32(0.5)).astype(F32)
    return (p - period * cell).astype(F32), cell


def domRepeatLimited(p, period, idMin, idMax):
    p, period = _f(p), np.maximum(_f(period), F32(1e-6))
    cell = np.clip(np.floor(p / period + F32(0.5)), _f(idMin), _f(idMax)).astype(F32)
    return (p - period * cell).astype(F32), cell


def domPolar(p, count):
    p = _f(p)
    count = max(np.floor(F32(count) + F32(0.5)), F32(1))           # a whole number of sectors, as domKaleido's
    wedge = F32(2.0 * math.pi) / count
    angle = F32(0) if (p[0] == 0 and p[1] == 0) else F32(math.atan2(float(p[1]), float(p[0])))
    turns = np.floor(angle / wedge + F32(0.5))
    x, y = _turn(p[0], p[1], -turns * wedge)
    sector = turns - count * np.floor(turns / count)                  # 0 .. count-1
    return np.array([x, y], dtype=F32), F32(sector)


def domReflect(p, n, offset):
    p, n = _f(p), _f(n)
    side = F32(np.dot(p, n)) + F32(offset)
    if side < 0:
        return (p - F32(2) * side * n).astype(F32), F32(-1)
    return p.copy(), F32(1)


ICOSA_MIRROR = np.array([-0.5 * float(PHI), -0.5, 0.5 * (float(PHI) - 1.0)], dtype=F32)


def domFoldIcosa(p):
    q = _f(p).copy()
    for _ in range(5):
        q[0], q[1] = abs(q[0]), abs(q[1])
        behind = min(float(np.dot(q, ICOSA_MIRROR)), 0.0)
        q = (q - F32(behind + behind) * ICOSA_MIRROR).astype(F32)
    return q


def domInvert3(p, radiusSq, scale):
    p = _f(p)
    factor = F32(radiusSq) / max(F32(np.dot(p, p)), F32(1e-20))
    return (p * factor).astype(F32), F32(scale) * factor
