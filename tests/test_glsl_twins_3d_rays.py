"""Pins for the 3D-rays family of the house GLSL library (atlas families D and E: distance shapes, combination, 3D
domains, analytic intersection, cameras, marchers, normals and 3D antialiasing) and their CPU twins.

WHY. A raymarcher is a chain of promises: the shape says "this is the distance", the combiner says "this is still at most
the distance", the domain operator says how much it stretched space, the marcher trusts all three and steps that far.
One promise broken anywhere shows up as holes, ghosts or a frozen GPU, far from its cause. A shader cannot be asked for a
number, so each GLSL function has a CPU TWIN (arsenal/shaders/twins/sdf.py and ray.py: numpy, float32, the same names)
and these tests hold the twins to references that do not share their formulas: polygon distances in the meridian plane
for the solids of revolution, the Euclidean projection onto the L1 ball for the octahedron, dense surface sampling for
the ellipsoid and the triangle, float64 quadratics for the intersections, finite differences for every derivative and
Lipschitz figure, a brute-force group of 120 matrices for the icosahedral fold. Like checking a new ohmmeter against a
reference resistor rather than against another ohmmeter of the same make.

The second half pins the modules against the atlas (arsenal/shaders/atlas.json, the authoritative plan): every planned
P0 function of each file is defined, nothing unplanned is exported, the header carries the fields of architecture
section 3.2, the marchers declare their hook, every loop has a literal bound, each module has a card that builds against
the house library, and lint finds nothing.

Apache-2.0, Akashic Aurora. Written fresh; no corpus code.
"""
from __future__ import annotations

import importlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

from arsenal.shaders import cards as K
from arsenal.shaders import modules as M

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "arsenal" / "web" / "glsl"
ATLAS = REPO / "arsenal" / "shaders" / "atlas.json"

# file -> module name: this family's eight files (the slice's own list)
MODULES = {
    "sdf/shapes.glsl": "sdf-shapes",
    "sdf/combine.glsl": "sdf-combine",
    "sdf/domain3.glsl": "sdf-domain3",
    "ray/intersect.glsl": "ray-intersect",
    "ray/camera.glsl": "ray-camera",
    "ray/march.glsl": "ray-march",
    "ray/normals.glsl": "ray-normals",
    "ray/aa3.glsl": "ray-aa3",
}
HOOKED = {"ray/march.glsl", "ray/normals.glsl"}
SCENE_HOOK = "float mapScene(vec3 p)"
F32 = np.float32
PHI = (1 + math.sqrt(5)) / 2


def twin(area: str):
    """The twin module, imported inside each test so a missing twin fails that test by name (not the whole file)."""
    return importlib.import_module(f"arsenal.shaders.twins.{area}")


def close(a, b, tol=1e-5):
    return np.allclose(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64), rtol=tol, atol=tol)


def rng(seed=7):
    return np.random.default_rng(seed)


def grad(f, p, h=1e-3):
    """Central-difference gradient in float64 of a scalar field f(p)."""
    p = np.asarray(p, dtype=np.float64)
    g = np.zeros(3)
    for i in range(3):
        e = np.zeros(3)
        e[i] = h
        g[i] = (float(f(p + e)) - float(f(p - e))) / (2 * h)
    return g


# ------------------------------------------------------------------------------------------- independent references
def seg_dist2(q, a, b):
    """Distance from 2D point q to the segment a-b, in float64."""
    q, a, b = (np.asarray(v, dtype=np.float64) for v in (q, a, b))
    ab = b - a
    s = np.clip(np.dot(q - a, ab) / max(np.dot(ab, ab), 1e-300), 0.0, 1.0)
    return float(np.linalg.norm(q - a - s * ab))


def inside_polygon(q, poly):
    """Even-odd ray cast: is 2D point q inside the closed polygon?"""
    x, y = q
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xc:
                inside = not inside
    return inside


def profile_sdf(p, poly, surface_edges):
    """Signed distance to a solid of revolution about y whose meridian profile is the closed polygon `poly` (in the
    half-plane radius >= 0, y); `surface_edges` lists the edge indices that are surface (the axis edge is not)."""
    q = (math.hypot(p[0], p[2]), p[1])
    d = min(seg_dist2(q, poly[i], poly[(i + 1) % len(poly)]) for i in surface_edges)
    return -d if inside_polygon(q, poly) else d


def polygon_sdf(q, poly):
    d = min(seg_dist2(q, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))
    return -d if inside_polygon(q, poly) else d


def l1_ball_projection(v, s):
    """The Euclidean projection of v onto {x : |x|_1 <= s} (Duchi, Shalev-Shwartz, Singer and Chandra, 2008)."""
    v = np.asarray(v, dtype=np.float64)
    if np.abs(v).sum() <= s:
        return v
    u = np.sort(np.abs(v))[::-1]
    css = np.cumsum(u)
    j = np.arange(1, len(u) + 1)
    rho = np.nonzero(u - (css - s) / j > 0)[0][-1]
    theta = (css[rho] - s) / (rho + 1)
    return np.sign(v) * np.maximum(np.abs(v) - theta, 0.0)


def random_points(n, scale=2.0, seed=7):
    return rng(seed).uniform(-scale, scale, size=(n, 3))


# ================================================================================================== distance shapes
def test_sphere_and_plane_and_torus_are_their_textbook_distances():
    s = twin("sdf")
    assert close(s.sdSphere([3.0, 4.0, 0.0], 1.0), 4.0)
    assert close(s.sdSphere([0.0, 0.0, 0.0], 0.75), -0.75)
    n = np.array([0.0, 0.6, 0.8])
    assert close(s.sdPlane([1.0, 2.0, 3.0], n, -1.0), 0.6 * 2 + 0.8 * 3 - 1.0)
    # the torus lies in the xz plane: its centre is the ring radius minus the tube radius away from the tube
    assert close(s.sdTorusY([0.0, 0.0, 0.0], 1.0, 0.25), 0.75)
    assert close(s.sdTorusY([1.0, 0.0, 0.0], 1.0, 0.25), -0.25)
    assert close(s.sdTorusY([0.0, 0.5, 1.0], 1.0, 0.25), 0.25)
    for a in np.linspace(0, 2 * np.pi, 9):
        for b in np.linspace(0, 2 * np.pi, 7):
            on = [(1 + 0.25 * np.cos(b)) * np.cos(a), 0.25 * np.sin(b), (1 + 0.25 * np.cos(b)) * np.sin(a)]
            assert abs(s.sdTorusY(on, 1.0, 0.25)) < 1e-5


def test_box_and_round_box_are_exact_inside_and_outside():
    s = twin("sdf")
    h = np.array([1.0, 0.5, 0.25])
    assert close(s.sdBox([2.0, 0.0, 0.0], h), 1.0)
    assert close(s.sdBox([2.0, 1.5, 0.0], h), math.sqrt(2.0))
    assert close(s.sdBox([0.0, 0.0, 0.0], h), -0.25)
    assert close(s.sdBox([0.9, 0.0, 0.0], h), -0.1)
    # the rounded box keeps its outer extent: a face centre is on the surface, a corner is rounded by r
    assert abs(s.sdRoundBox([1.0, 0.0, 0.0], h, 0.1)) < 1e-6
    corner = np.array([1.0, 0.5, 0.25])
    inner = corner - 0.1
    assert close(s.sdRoundBox(corner, h, 0.1), np.linalg.norm(corner - inner) - 0.1)
    for p in random_points(300, 2.0, seed=1):
        g = np.linalg.norm(grad(lambda q: s.sdBox(q.astype(F32), h), p))
        d = float(s.sdBox(p.astype(F32), h))
        if d > 0.01:
            assert abs(g - 1.0) < 2e-3, (p, g)               # Eikonal outside: an exact distance
        else:
            assert g < 1.0 + 2e-3, (p, g)                     # never faster than distance (1 off the medial creases)


def test_capsule_is_the_segment_distance_minus_the_radius_and_survives_a_zero_length_segment():
    s = twin("sdf")
    a, b = np.array([-1.0, 0.2, 0.0]), np.array([1.0, -0.3, 0.5])
    for p in random_points(300, 2.5, seed=2):
        ab = b - a
        k = np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0, 1)
        ref = np.linalg.norm(p - a - k * ab) - 0.3
        assert close(s.sdCapsule(p, a, b, 0.3), ref, 2e-5)
    v = s.sdCapsule([1.0, 0.0, 0.0], a * 0, a * 0, 0.5)
    assert np.isfinite(v) and close(v, 0.5)       # a == b is a sphere, not a NaN


@pytest.mark.parametrize("shape", ["cylinder", "cone", "cone_inverted", "cone_point"])
def test_solids_of_revolution_match_the_distance_to_their_meridian_profile(shape):
    s = twin("sdf")
    if shape == "cylinder":
        r, hh = 0.6, 0.8
        poly = [(0, -hh), (r, -hh), (r, hh), (0, hh)]
        fn = lambda p: s.sdCylinderY(p, r, hh)                       # noqa: E731
    else:
        h, rb, rt = {"cone": (0.7, 0.9, 0.3), "cone_inverted": (0.5, 0.2, 1.1), "cone_point": (0.6, 1.0, 0.0)}[shape]
        poly = [(0, -h), (rb, -h), (rt, h), (0, h)]
        fn = lambda p: s.sdConeCappedY(p, h, rb, rt)                  # noqa: E731
    for p in random_points(500, 2.0, seed=3):
        ref = profile_sdf(p, poly, [0, 1, 2])
        assert close(fn(p.astype(F32)), ref, 3e-5), (shape, p, fn(p), ref)


def test_round_cone_is_the_hull_of_two_spheres():
    s = twin("sdf")
    a, b, ra, rb = np.array([-0.6, -0.2, 0.1]), np.array([0.7, 0.5, -0.2]), 0.5, 0.2
    ss = np.linspace(0, 1, 4001)
    centres = a[None, :] + ss[:, None] * (b - a)[None, :]
    radii = ra + ss * (rb - ra)
    for p in random_points(300, 2.0, seed=4):
        ref = float(np.min(np.linalg.norm(p[None, :] - centres, axis=1) - radii))   # exact outside: a union of balls
        v = float(s.sdRoundConeAB(p, a, b, ra, rb))
        if ref > 0:
            assert close(v, ref, 2e-4), (p, v, ref)
        else:
            assert v <= 1e-5
    assert close(s.sdRoundConeAB(a, a, b, ra, rb), -ra)
    # one sphere inside the other: the hull is the bigger one
    assert close(s.sdRoundConeAB([2.0, 0.0, 0.0], [0.0, 0, 0], [0.1, 0, 0], 1.0, 0.2), 1.0)


def test_hex_prism_is_an_exact_extruded_hexagon_with_flat_top_and_bottom():
    s = twin("sdf")
    a, hd = 0.5, 0.3
    big = 2 * a / math.sqrt(3)
    hexagon = [(big * math.cos(k * math.pi / 3), big * math.sin(k * math.pi / 3)) for k in range(6)]
    assert close(s.sdHexPrismZ([0.0, a, 0.0], a, hd), 0.0)          # the apothem is along y: a flat edge on top
    for p in random_points(500, 1.5, seed=5):
        d2 = polygon_sdf((p[0], p[1]), hexagon)
        w = (d2, abs(p[2]) - hd)
        ref = min(max(w), 0.0) + math.hypot(max(w[0], 0.0), max(w[1], 0.0))
        assert close(s.sdHexPrismZ(p.astype(F32), a, hd), ref, 3e-5), p


def test_octahedron_is_exact_not_the_planar_bound():
    s = twin("sdf")
    size = 0.9
    worst_bound_gap = 0.0
    for p in random_points(800, 2.0, seed=6):
        if np.abs(p).sum() <= size:
            ref = (np.abs(p).sum() - size) / math.sqrt(3)
        else:
            ref = np.linalg.norm(p - l1_ball_projection(p, size))
        assert close(s.sdOctahedron(p.astype(F32), size), ref, 3e-5), p
        worst_bound_gap = max(worst_bound_gap, ref - (np.abs(p).sum() - size) / math.sqrt(3))
    assert worst_bound_gap > 0.1      # the cheap planar formula really is only a bound out there


def test_ellipsoid_bound_never_exceeds_the_true_distance_and_is_tight_near_the_surface():
    s = twin("sdf")
    radii = np.array([1.0, 0.5, 0.3])
    u = np.linspace(0, np.pi, 700)
    v = np.linspace(0, 2 * np.pi, 1400)
    uu, vv = np.meshgrid(u, v)
    surf = np.stack([radii[0] * np.sin(uu) * np.cos(vv), radii[1] * np.sin(uu) * np.sin(vv),
                     radii[2] * np.cos(uu)], axis=-1).reshape(-1, 3)
    spacing = 0.004
    for p in random_points(60, 1.6, seed=8):
        true = float(np.min(np.linalg.norm(surf - p[None, :], axis=1)))
        inside = np.sum((p / radii) ** 2) < 1
        bound = float(s.sbEllipsoid(p.astype(F32), radii))
        assert (bound < 0) == inside
        assert abs(bound) <= true + spacing, (p, bound, true)
    # tight near the surface: one hundredth of the smallest radius out along a few directions
    for d in ([1, 0, 0], [0, 1, 0], [1, 1, 1], [0.2, -1, 0.5]):
        d = np.array(d, dtype=np.float64)
        on = d / np.sqrt(np.sum((d / radii) ** 2))
        n = on / radii ** 2
        n /= np.linalg.norm(n)
        p = on + 0.003 * n
        assert close(s.sbEllipsoid(p.astype(F32), radii), 0.003, 1e-4)
    assert close(s.sbEllipsoid([0.0, 0.0, 0.0], radii), -0.3)        # no NaN at the centre: minus the smallest radius


@pytest.mark.parametrize("kind,faces", [(0, 6), (1, 8), (2, 12), (3, 20), (4, 14), (5, 32)])
def test_polyhedron_bound_has_its_faces_at_the_inradius_and_never_overestimates(kind, faces):
    s = twin("sdf")
    r = 0.8
    hits = set()
    dirs = rng(9).normal(size=(4000, 3))
    for d in dirs:
        d /= np.linalg.norm(d)
        hits.add(s.polyhedronFace(d, kind))
    assert len(hits) == faces
    pts = random_points(400, 2.0, seed=10)
    vals = np.array([float(s.sbPolyhedron(p.astype(F32), r, kind)) for p in pts])
    for i in range(len(pts) - 1):        # 1-Lipschitz: a bound
        assert abs(vals[i] - vals[i + 1]) <= np.linalg.norm(pts[i] - pts[i + 1]) * (1 + 1e-4) + 1e-6
    for n in s.polyhedronNormals(kind):
        assert abs(float(s.sbPolyhedron((r * n).astype(F32), r, kind))) < 1e-5     # every face centre is surface
    assert close(s.sbPolyhedron([0.0, 0.0, 0.0], r, kind), -r)


def test_superquadric_is_a_sphere_at_two_and_a_bound_for_every_exponent():
    s = twin("sdf")
    for p in random_points(100, 2.0, seed=11):
        assert close(s.sbSuperquadric(p.astype(F32), [1.0, 1.0, 1.0], 2.0), np.linalg.norm(p) - 1.0, 2e-5)
    for n in (1.0, 1.5, 4.0, 8.0, 24.0):
        pts = random_points(300, 2.0, seed=12)
        r = np.array([1.0, 0.6, 0.8])
        vals = [float(s.sbSuperquadric(p.astype(F32), r, n)) for p in pts]
        for i in range(len(pts) - 1):
            assert abs(vals[i] - vals[i + 1]) <= np.linalg.norm(pts[i] - pts[i + 1]) * (1 + 1e-4) + 1e-6, n
    far = float(s.sbSuperquadric([1e6, 3e5, 0.0], [1.0, 1.0, 1.0], 24.0))
    assert np.isfinite(far) and far > 0          # no overflow to Inf for a big exponent far away


def test_triangle_distance_is_exact_and_unsigned():
    s = twin("sdf")
    a, b, c = np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.2, 0.0]), np.array([0.3, 0.9, 0.4])
    g = np.linspace(0, 1, 401)
    uu, vv = np.meshgrid(g, g)
    keep = uu + vv <= 1
    tri = (a[None, :] + uu[keep][:, None] * (b - a)[None, :] + vv[keep][:, None] * (c - a)[None, :])
    for p in random_points(80, 1.5, seed=13):
        ref = float(np.min(np.linalg.norm(tri - p[None, :], axis=1)))
        v = float(s.udTriangle(p.astype(F32), a, b, c))
        assert v >= 0 and abs(v - ref) < 4e-3 and v <= ref + 1e-5, (p, v, ref)


# ======================================================================================================= combination
def test_booleans_follow_the_house_order_a_minus_b():
    s = twin("sdf")
    assert s.opUnion(0.3, -0.2) == F32(-0.2) and s.opIntersect(0.3, -0.2) == F32(0.3)
    assert s.opSubtract(-0.5, -0.2) == F32(0.2)            # a minus b: inside b is carved away
    assert s.opSubtract(-0.5, 0.4) == F32(-0.4)            # inside a, 0.4 from b: the carved face bounds it
    assert list(s.opPick([0.4, 2.0], [0.1, 5.0])) == [F32(0.1), F32(5.0)]
    assert list(s.opPick([0.1, 2.0], [0.1, 5.0])) == [F32(0.1), F32(2.0)]    # a tie keeps the first id


def test_xor_is_exact_on_both_sides():
    s = twin("sdf")
    xs = np.linspace(-3, 4, 7001)
    a = np.abs(xs) - 1.0                      # [-1, 1]
    b = np.abs(xs - 1.5) - 1.0                # [0.5, 2.5]
    inside = (a < 0) ^ (b < 0)
    boundary = np.array([-1.0, 0.5, 1.0, 2.5])
    ref = np.min(np.abs(xs[:, None] - boundary[None, :]), axis=1) * np.where(inside, -1, 1)
    got = np.array([float(s.opXor(float(u), float(v))) for u, v in zip(a, b)])
    assert np.max(np.abs(got - ref)) < 1e-5


def test_smooth_union_dips_by_exactly_k_is_rigid_and_conservative():
    s = twin("sdf")
    k = 0.2
    assert close(s.opSmin(0.5, 0.5, k), 0.5 - k)
    for gap in (0.8, 1.0, 3.0):                                      # beyond 4k apart: plain min
        assert s.opSmin(0.1, 0.1 + gap, k) == F32(0.1)
    xs = rng(14).uniform(-1, 1, size=(300, 2))
    for a, b in xs:
        v = float(s.opSmin(a, b, k))
        assert v <= min(a, b) + 1e-6 and v >= min(a, b) - k - 1e-6
        da = (float(s.opSmin(a + 1e-3, b, k)) - float(s.opSmin(a - 1e-3, b, k))) / 2e-3
        db = (float(s.opSmin(a, b + 1e-3, k)) - float(s.opSmin(a, b - 1e-3, k))) / 2e-3
        assert -1e-2 <= da <= 1 + 1e-2 and -1e-2 <= db <= 1 + 1e-2 and abs(da + db - 1) < 2e-2


def test_smooth_union_mix_weight_is_the_gradient_weight_of_b():
    s = twin("sdf")
    k = 0.25
    for a, b in rng(15).uniform(-1, 1, size=(200, 2)):
        m = s.opSminMix(a, b, k)
        assert close(m[0], s.opSmin(a, b, k))
        db = (float(s.opSmin(a, b + 1e-3, k)) - float(s.opSmin(a, b - 1e-3, k))) / 2e-3
        assert abs(float(m[1]) - db) < 2e-2 and 0 <= float(m[1]) <= 1
    assert close(s.opSminMix(0.3, 0.3, k)[1], 0.5)


def test_smooth_max_and_smooth_subtract_mirror_the_smooth_union():
    s = twin("sdf")
    for a, b in rng(16).uniform(-1, 1, size=(100, 2)):
        assert close(s.opSmax(a, b, 0.2), -s.opSmin(-a, -b, 0.2))
        assert close(s.opSsubtract(a, b, 0.2), s.opSmax(a, -b, 0.2))


def test_circular_smooth_union_draws_a_circular_fillet_between_perpendicular_planes():
    s = twin("sdf")
    k = 0.1
    rho = k / (1 - math.sqrt(0.5))
    assert close(s.opSminCircular(0.4, 0.4, k), 0.4 - k)
    # zero set of smin(x, y) in the plane, x = distance to one wall and y to the other: inside the fillet it is the
    # circle of radius rho centred at (rho, rho)
    for theta in np.linspace(0.05, math.pi / 2 - 0.05, 11):
        x, y = rho - rho * math.cos(theta), rho - rho * math.sin(theta)
        assert abs(float(s.opSminCircular(x, y, k))) < 2e-5, theta
    assert s.opSminCircular(0.0, rho + 0.01, k) == F32(0.0)          # rigid: no effect a fillet width apart


def test_exponential_smooth_union_is_order_independent_and_overflow_safe():
    s = twin("sdf")
    k = 0.15
    assert close(s.opSminExp(0.2, 0.2, k), 0.2 - k)
    for a, b, c in rng(17).uniform(-1, 1, size=(100, 3)):
        assert close(s.opSminExp(a, b, k), s.opSminExp(b, a, k))
        assert close(s.opSminExp(s.opSminExp(a, b, k), c, k), s.opSminExp(a, s.opSminExp(b, c, k), k), 3e-5)
    assert np.isfinite(s.opSminExp(-500.0, -400.0, 0.01))


def test_round_onion_scale_and_displace_are_their_one_liners():
    s = twin("sdf")
    assert close(s.opRound(0.5, 0.2), 0.3)
    assert close(s.opOnion(-0.3, 0.1), 0.2) and close(s.opOnion(0.05, 0.1), -0.05)
    assert close(s.opUniformScale(0.25, 4.0), 1.0)
    assert close(s.opDisplace(0.4, 0.1, 1.5), 0.2)
    # an honest Lipschitz figure keeps a displaced sphere a bound: amplitude 0.1, frequency 6 -> L = 0.6
    pts = random_points(300, 1.5, seed=18)
    f = lambda p: float(s.opDisplace(np.linalg.norm(p) - 0.8,                   # noqa: E731
                                     0.1 * np.sin(6 * p[0]) * np.sin(6 * p[1]) * np.sin(6 * p[2]), 0.6))
    vals = [f(p) for p in pts]
    for i in range(len(pts) - 1):
        assert abs(vals[i] - vals[i + 1]) <= np.linalg.norm(pts[i] - pts[i + 1]) + 1e-5


# =========================================================================================================== domains
def _rot(axis, angle):
    axis = np.asarray(axis, dtype=np.float64)
    axis /= np.linalg.norm(axis)
    x, y, z = axis
    c, s_ = math.cos(angle), math.sin(angle)
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s_, x * z * (1 - c) + y * s_],
                     [y * x * (1 - c) + z * s_, c + y * y * (1 - c), y * z * (1 - c) - x * s_],
                     [z * x * (1 - c) - y * s_, z * y * (1 - c) + x * s_, c + z * z * (1 - c)]])


def test_rigid_placement_undoes_rotation_then_position():
    s = twin("sdf")
    R = _rot([0.3, 1.0, -0.4], 1.1)
    pos = np.array([0.5, -1.0, 2.0])
    for q in random_points(50, 1.0, seed=19):
        world = R @ q + pos
        assert close(s.domRigid(world, R, pos), q, 3e-5)


def test_mirror_and_reflect_fold_space():
    s = twin("sdf")
    assert close(s.domMirror([-1.0, -2.0, -3.0], [1.0, 0.0, 1.0]), [1.0, -2.0, 3.0])
    n = np.array([0.0, 0.6, 0.8])
    p, side = s.domReflect([0.0, -1.0, 0.0], n, 0.2)        # dot = -0.6 + 0.2 = -0.4: folded, side -1
    assert side == F32(-1.0) and close(np.dot(p, n) + 0.2, 0.4)
    p, side = s.domReflect([0.0, 1.0, 0.0], n, 0.2)
    assert side == F32(1.0) and close(p, [0.0, 1.0, 0.0])


def test_twist_turns_by_rate_times_height_and_lip_twist_bounds_its_stretch():
    s = twin("sdf")
    q = s.domTwistY([1.0, 0.5, 0.0], 2.0)
    assert close(q[1], 0.5) and close(math.hypot(q[0], q[2]), 1.0)
    assert close(abs(math.atan2(q[2], q[0])), 1.0, 1e-5)          # turned by rate * y = 1 radian
    for k, R in ((1.0, 1.0), (3.0, 0.7), (0.5, 2.0)):
        worst = 0.0
        for p in rng(20).uniform(-R / math.sqrt(2), R / math.sqrt(2), size=(300, 3)):
            J = np.zeros((3, 3))
            for i in range(3):
                e = np.zeros(3)
                e[i] = 1e-4
                J[:, i] = (np.asarray(s.domTwistY(p + e, k), dtype=np.float64)
                           - np.asarray(s.domTwistY(p - e, k), dtype=np.float64)) / 2e-4
            worst = max(worst, np.linalg.svd(J, compute_uv=False)[0])
        lip = float(s.lipTwist(k, R))
        assert worst <= lip * (1 + 2e-3), (k, R, worst, lip)
        assert lip > math.sqrt(1 + (k * R) ** 2)       # the tempting formula is too small
    assert close(s.lipTwist(1.0, 1.0), PHI, 1e-5)


def test_bend_keeps_lengths_in_its_plane():
    s = twin("sdf")
    for p in random_points(50, 1.0, seed=21):
        q = s.domBend(p, 0.8)
        assert close(math.hypot(q[0], q[1]), math.hypot(p[0], p[1]), 3e-5) and close(q[2], p[2])


def test_repeat_returns_the_cell_id_and_a_centred_local_point():
    s = twin("sdf")
    period = np.array([1.0, 2.0, 0.5])
    for p in random_points(200, 5.0, seed=22):
        local, cell = s.domRepeat(p, period)
        assert np.all(np.abs(local) <= period / 2 + 1e-5)
        assert close(local + cell * period, p, 3e-5)
        assert np.all(cell == np.floor(cell))
    local, cell = s.domRepeatLimited([10.3, 0.2, -7.0], period, [-2.0, -2.0, -2.0], [2.0, 2.0, 2.0])
    assert list(cell) == [2.0, 0.0, -2.0] and close(local, [10.3 - 2.0, 0.2, -7.0 + 1.0])


def test_polar_repeat_names_the_sector_and_keeps_the_radius():
    s = twin("sdf")
    for p in rng(23).uniform(-2, 2, size=(200, 2)):
        local, sector = s.domPolar(p, 7.0)
        assert close(np.linalg.norm(local), np.linalg.norm(p), 3e-5)
        assert abs(math.atan2(local[1], local[0])) <= math.pi / 7 + 1e-5
        assert 0 <= sector < 7 and sector == math.floor(sector)
        back = math.atan2(local[1], local[0]) + sector * 2 * math.pi / 7
        assert close(math.cos(back), p[0] / np.linalg.norm(p), 1e-4)
    local, sector = s.domPolar(np.array([0.0, 0.0]), 5.0)        # the centre has no angle: no NaN
    assert np.all(np.isfinite(local)) and sector == 0


def test_repeat_survives_a_zero_period_like_its_2d_sibling():
    # Batch-B review, defect 9: domRepeat and domRepeatLimited had no floor on the period (a zero period gave NaN),
    # unlike draw2's domRepeat2, which floors each axis at 1e-6. Same floor here.
    s = twin("sdf")
    for period in ([0.0, 1.0, 0.5], [0.0, 0.0, 0.0], [-1.0, 1.0, 1.0]):
        for p in random_points(20, 3.0, seed=24):
            local, cell = s.domRepeat(p, period)
            assert np.all(np.isfinite(local)) and np.all(np.isfinite(cell)), (period, p, local, cell)
            floored = np.maximum(np.asarray(period, np.float32), F32(1e-6))
            assert np.all(np.abs(local) <= floored / 2 + 1e-5)
            local, cell = s.domRepeatLimited(p, period, [-2.0, -2.0, -2.0], [2.0, 2.0, 2.0])
            assert np.all(np.isfinite(local)) and np.all(np.isfinite(cell)), (period, p, local, cell)


def test_polar_repeat_rounds_a_count_that_is_not_whole():
    # Batch-B review, defect 9: domPolar used max(count, 1) unrounded, so 6.6 sectors gave six whole wedges and a
    # narrower seventh (a seam at a fixed angle), while domKaleido rounds. A count is a whole number of sectors.
    s = twin("sdf")
    for p in rng(25).uniform(-2, 2, size=(100, 2)):
        for count, whole in ((6.6, 7.0), (6.4, 6.0), (0.3, 1.0)):
            got, sector = s.domPolar(p, count)
            want, want_sector = s.domPolar(p, whole)
            assert close(got, want) and sector == want_sector, (count, p)


def test_icosahedral_fold_lands_in_one_chamber_and_is_invariant_under_all_120_symmetries():
    s = twin("sdf")
    n3 = np.array([-PHI / 2, -0.5, (PHI - 1) / 2])

    def mirror(n):
        n = n / np.linalg.norm(n)
        return np.eye(3) - 2 * np.outer(n, n)

    gens = [mirror(np.array([1.0, 0, 0])), mirror(np.array([0, 1.0, 0])), mirror(n3)]
    group, frontier, seen = [np.eye(3)], [np.eye(3)], {tuple(np.round(np.eye(3), 6).ravel())}
    while frontier:
        nxt = []
        for m in frontier:
            for g in gens:
                h = g @ m
                key = tuple(np.round(h, 6).ravel())
                if key not in seen:
                    seen.add(key)
                    group.append(h)
                    nxt.append(h)
        frontier = nxt
    assert len(group) == 120
    for p in random_points(150, 1.5, seed=24):
        f = np.asarray(s.domFoldIcosa(p), dtype=np.float64)
        assert f[0] >= -1e-5 and f[1] >= -1e-5 and np.dot(f, n3) >= -1e-5
        assert close(np.linalg.norm(f), np.linalg.norm(p), 3e-5)
        for g in group[::7]:
            assert close(s.domFoldIcosa(g @ p), f, 3e-4)
        assert close(s.domFoldIcosa(-f), f, 3e-4)          # the antipode, the longest way round, folds home too
    # the chamber's three corners: a 2-fold axis (z), a 5-fold vertex (0, 1, PHI) and a 3-fold face centre
    for corner in ([0.0, 0.0, 1.0], [0.0, 1.0, PHI], [1.0, 0.0, PHI * PHI]):
        c = np.array(corner) / np.linalg.norm(corner)
        assert close(s.domFoldIcosa(c), c, 1e-5)


def test_sphere_inversion_is_an_involution_with_its_scale():
    s = twin("sdf")
    for p in random_points(50, 2.0, seed=25):
        q, scale = s.domInvert3(p, 1.5, 1.0)
        assert close(np.linalg.norm(q) * np.linalg.norm(p), 1.5, 1e-4)
        back, scale2 = s.domInvert3(q, 1.5, scale)
        assert close(back, p, 1e-4) and close(scale2, 1.0, 1e-4)
    q, scale = s.domInvert3([0.0, 0.0, 0.0], 1.0, 1.0)
    assert np.all(np.isfinite(q)) and np.isfinite(scale)


def test_an_inverted_field_is_an_estimate_that_over_reports_by_at_most_its_stated_factor():
    """The contract: distance-after-inversion / scale can run up to 1 + 2 |p| d / radiusSq times faster than distance,
    where d is the distance after inversion; it does run faster somewhere (it is not a bound), and never beyond that."""
    s = twin("sdf")
    radius_sq = 1.0

    def after(p):
        q, scale = s.domInvert3(np.asarray(p, dtype=np.float64), radius_sq, 1.0)
        local, _cell = s.domRepeat(q, [0.6, 0.6, 0.6])
        return float(s.sdSphere(local, 0.16)), float(scale)

    faster = 0
    for p in random_points(400, 1.3, seed=31):
        if not 0.3 < np.linalg.norm(p) < 1.6:
            continue
        g = np.linalg.norm(grad(lambda x: after(x)[0] / after(x)[1], p, 1e-4))
        d_after, _scale = after(p)
        allowed = 1.0 + 2.0 * np.linalg.norm(p) * abs(d_after) / radius_sq
        assert g <= allowed * 1.02 + 1e-3, (p, g, allowed)
        faster += g > 1.05
    assert faster > 0


# ============================================================================================ analytic intersection
def _sphere_roots64(ro, rd, c, r):
    oc = np.asarray(ro, np.float64) - np.asarray(c, np.float64)
    rd = np.asarray(rd, np.float64)
    b = np.dot(oc, rd)
    disc = b * b - (np.dot(oc, oc) - r * r)
    if disc < 0:
        return None
    return -b - math.sqrt(disc), -b + math.sqrt(disc)


def test_ray_sphere_returns_both_roots_and_minus_one_on_a_miss():
    y = twin("ray")
    for i, (ro, rd) in enumerate(zip(random_points(200, 4.0, seed=26), rng(27).normal(size=(200, 3)))):
        rd /= np.linalg.norm(rd)
        c, r = np.array([0.3, -0.2, 0.1]), 1.1
        ref = _sphere_roots64(ro, rd, c, r)
        got = y.ixSphere(ro, rd, c, r)
        if ref is None:
            assert list(got) == [-1.0, -1.0]
        else:
            assert close(got, ref, 2e-4), (ref, got)


def test_ray_sphere_keeps_its_precision_for_a_small_sphere_far_away():
    y = twin("ray")
    ro, c, r = np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, -3000.0]), 0.05
    for off in (0.0, 0.01, 0.02, 0.03, 0.045):
        rd = np.array([off, 0.0, -3000.0])
        rd /= np.linalg.norm(rd)
        ref = _sphere_roots64(ro, rd, c, r)
        got = y.ixSphere(ro, rd, c, r)
        # the chord (what glass and halos read) to a hundredth of the radius, where b*b - (oc.oc - r*r) in float32
        # subtracts two numbers near 9e6 whose last bit is worth about 1
        assert abs(float(got[1] - got[0]) - (ref[1] - ref[0])) < 5e-4, (off, got, ref)


def test_ray_box_is_the_slab_method_with_the_entry_face_normal():
    y = twin("ray")
    half = np.array([1.0, 0.5, 0.8])
    for ro, rd in zip(random_points(300, 3.0, seed=28), rng(29).normal(size=(300, 3))):
        rd /= np.linalg.norm(rd)
        t1 = (-half - ro) / rd
        t2 = (half - ro) / rd
        near, far = np.max(np.minimum(t1, t2)), np.min(np.maximum(t1, t2))
        got, normal = y.ixBox(ro, rd, half)
        if near > far or far < 0:
            assert list(got) == [-1.0, -1.0]
        else:
            assert close(got, (near, far), 2e-4)
            axis = int(np.argmax(np.minimum(t1, t2)))
            want = np.zeros(3)
            want[axis] = -np.sign(rd[axis])
            assert close(normal, want)
    got, normal = y.ixBox([0.0, 0.2, 5.0], [0.0, 0.0, -1.0], half)      # zero components: no NaN
    assert close(got, (4.2, 5.8)) and close(normal, [0.0, 0.0, 1.0])


def test_ray_plane_and_slab():
    y = twin("ray")
    n = np.array([0.0, 1.0, 0.0])
    assert close(y.ixPlane([0.0, 2.0, 0.0], [0.0, -1.0, 0.0], n, 0.5), 2.5)          # plane y = -0.5
    assert y.ixPlane([0.0, 2.0, 0.0], [0.0, 1.0, 0.0], n, 0.5) == F32(-1.0)            # behind
    assert y.ixPlane([0.0, 2.0, 0.0], [1.0, 0.0, 0.0], n, 0.5) == F32(-1.0)            # parallel
    assert close(y.ixSlabY(0.0, 0.5, 1.0, 2.0), (2.0, 4.0))
    assert close(y.ixSlabY(1.5, 0.5, 1.0, 2.0), (0.0, 1.0))           # inside: entry clamped to 0
    near, far = y.ixSlabY(3.0, 0.5, 1.0, 2.0)                        # behind: a miss
    assert far < near
    near, far = y.ixSlabY(1.5, 0.0, 1.0, 2.0)                        # parallel, inside: all of the ray
    assert near == 0 and far > 1e20
    near, far = y.ixSlabY(5.0, 0.0, 1.0, 2.0)                        # parallel, outside: a miss
    assert far < near


def test_shell_gives_the_first_segment_inside_from_outside_inside_and_within():
    y = twin("ray")
    c, ri, ro_ = np.zeros(3), 1.0, 2.0
    assert close(y.ixShell([0.0, 0.0, 5.0], [0.0, 0.0, -1.0], c, ri, ro_), (3.0, 4.0))      # outside: to the inner
    assert close(y.ixShell([0.0, 0.0, 0.0], [0.0, 0.0, -1.0], c, ri, ro_), (1.0, 2.0))      # in the core: out
    assert close(y.ixShell([0.0, 0.0, 1.5], [0.0, 0.0, 1.0], c, ri, ro_), (0.0, 0.5))       # in the shell, outward
    assert close(y.ixShell([0.0, 0.0, 1.5], [0.0, 0.0, -1.0], c, ri, ro_), (0.0, 0.5))      # in the shell, inward
    assert close(y.ixShell([0.0, 1.5, 5.0], [0.0, 0.0, -1.0], c, ri, ro_),
                 (5.0 - math.sqrt(4 - 2.25), 5.0 + math.sqrt(4 - 2.25)))                    # grazing past the core
    near, far = y.ixShell([0.0, 3.0, 5.0], [0.0, 0.0, -1.0], c, ri, ro_)
    assert far < near


def test_clip_to_box_narrows_the_range_and_skip_is_honest():
    y = twin("ray")
    got = y.rmClipToBox([0.0, 0.0, 5.0], [0.0, 0.0, -1.0], [0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.0, 100.0])
    assert close(got, (4.0, 6.0))
    got = y.rmClipToBox([0.0, 3.0, 5.0], [0.0, 0.0, -1.0], [0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.0, 100.0])
    assert got[0] > got[1]
    got = y.rmClipToBox([0.0, 0.0, 5.0], [0.0, 0.0, -1.0], [0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.0, 4.5])
    assert close(got, (4.0, 4.5))
    assert y.bvCanSkip(1.0, 0.5) and not y.bvCanSkip(0.4, 0.5)


def test_planet_scale_sphere_from_radius_and_zenith_cosine():
    y = twin("ray")
    R = 6360.0
    for r0, mu in ((6361.0, 0.3), (6360.5, -0.01), (6400.0, -0.99)):
        ro = np.array([0.0, r0, 0.0])
        rd = np.array([math.sqrt(1 - mu * mu), mu, 0.0])
        ref = _sphere_roots64(ro, rd, np.zeros(3), R)
        got = y.ixSphereAlt(r0, mu, R)
        if ref is None:
            assert list(got) == [-1.0, -1.0]
        else:
            assert close(got, ref, 1e-3)


# ============================================================================================================ cameras
def test_look_at_is_right_handed_looks_down_minus_z_and_rolls_counter_clockwise():
    y = twin("ray")
    ro, target = np.array([3.0, 2.0, 4.0]), np.array([0.0, 0.5, 0.0])
    B = y.camLookAt(ro, target, 0.0)
    assert close(B.T @ B, np.eye(3)) and close(np.linalg.det(B), 1.0)
    fwd = (target - ro) / np.linalg.norm(target - ro)
    assert close(B @ np.array([0.0, 0.0, -1.0]), fwd)
    assert abs(B[1, 0]) < 1e-6 and B[1, 1] > 0                     # unrolled: right is level, up points up
    Br = y.camLookAt(ro, target, 0.3)
    assert close(Br[:, 2], B[:, 2])
    assert close(Br[:, 0], math.cos(0.3) * B[:, 0] + math.sin(0.3) * B[:, 1])
    Bup = y.camLookAt([0.0, 5.0, 0.0], [0.0, 0.0, 0.0], 0.0)          # straight down: still a basis, no NaN
    assert np.all(np.isfinite(Bup)) and close(Bup.T @ Bup, np.eye(3))


def test_camera_ray_is_unit_through_the_pixel_centre_and_the_pixel_angle_matches_it():
    y = twin("ray")
    B = np.eye(3)
    res = np.array([480.0, 270.0])
    focal = 1.8
    centre = y.camRay(res / 2, res, B, focal)
    assert close(centre, [0.0, 0.0, -1.0])
    for frag in ([0.5, 0.5], [479.5, 10.5], [200.5, 133.5]):
        assert close(np.linalg.norm(y.camRay(np.array(frag), res, B, focal)), 1.0)
    one = y.camRay(res / 2 + np.array([0.0, 1.0]), res, B, focal)
    angle = math.acos(float(np.dot(centre, one)))
    fov = 2 * math.atan(1 / focal)
    assert close(y.camPixelAngle(fov, 270.0), angle, 1e-3)
    assert close(y.camPixelAngle(fov, 270.0), 2 / (270.0 * focal), 1e-6)


def test_orbit_keeps_its_radius_and_poses_itself_when_the_mouse_is_untouched():
    y = twin("ray")
    target = np.array([0.0, 0.5, 0.0])
    for m in ([0.0, 0.0], [0.2, 0.7], [0.9, 0.1]):
        p = y.camOrbit(np.array(m), 1.3, 4.0, target)
        assert close(np.linalg.norm(p - target), 4.0)
    a = y.camOrbit(np.zeros(2), 0.0, 4.0, target)
    b = y.camOrbit(np.zeros(2), 1.0, 4.0, target)
    assert not close(a, b) and close(a[1], b[1]) and a[1] > target[1]    # untouched: auto-yaw, from a little above
    c = y.camOrbit(np.array([0.3, 0.6]), 0.0, 4.0, target)
    d = y.camOrbit(np.array([0.3, 0.6]), 5.0, 4.0, target)
    assert close(c, d)                                                    # touched: the mouse alone decides


def test_ortho_rays_are_parallel_and_offset_across_the_image_plane():
    y = twin("ray")
    B = y.camLookAt([0.0, 0.0, 5.0], [0.0, 0.0, 0.0], 0.0)
    rd0, ro0 = y.camOrthoRay(np.array([0.0, 0.0]), B, 2.0, np.array([0.0, 0.0, 5.0]))
    rd1, ro1 = y.camOrthoRay(np.array([0.5, -0.25]), B, 2.0, np.array([0.0, 0.0, 5.0]))
    assert close(rd0, rd1) and close(rd0, [0.0, 0.0, -1.0])
    assert close(ro0, [0.0, 0.0, 5.0]) and close(ro1, [1.0, -0.5, 5.0])


def test_lissajous_path_derivatives_are_exact_and_a_zero_frequency_axis_flies():
    y = twin("ray")
    amp, freq = np.array([1.0, 0.7, 0.5]), np.array([0.31, 0.41, 0.0])
    for t in (0.0, 1.3, 7.9):
        p, v, a = y.pathLissajous3(t, amp, freq)
        p1, _, _ = y.pathLissajous3(t + 1e-3, amp, freq)
        p0, _, _ = y.pathLissajous3(t - 1e-3, amp, freq)
        assert close(v, (np.asarray(p1, np.float64) - p0) / 2e-3, 2e-3)
        _, v1, _ = y.pathLissajous3(t + 1e-3, amp, freq)
        _, v0, _ = y.pathLissajous3(t - 1e-3, amp, freq)
        assert close(a, (np.asarray(v1, np.float64) - v0) / 2e-3, 2e-3)
        assert close(p[2], 0.5 * t) and close(v[2], 0.5) and close(a[2], 0.0)


def test_banked_frame_follows_the_velocity_and_leans_into_the_turn():
    y = twin("ray")
    vel, acc = np.array([0.0, 0.0, -2.0]), np.array([1.0, 0.0, 0.0])        # flying -z, turning toward +x
    level = y.camBanked(vel, np.zeros(3), 1.0)
    bank = y.camBanked(vel, acc, 0.5)
    for B in (level, bank):
        assert close(B.T @ B, np.eye(3)) and close(np.linalg.det(B), 1.0)
        assert close(B @ np.array([0.0, 0.0, -1.0]), [0.0, 0.0, -1.0])
    assert close(level[:, 1], [0.0, 1.0, 0.0])
    assert bank[0, 1] > 0.1                          # the up vector tilts toward the inside of the turn


def test_barrel_keeps_the_centre_and_scales_by_one_plus_k_r_squared():
    y = twin("ray")
    assert close(y.camBarrel(np.zeros(2), 0.3), [0.0, 0.0])
    p = np.array([0.6, -0.8])
    assert close(y.camBarrel(p, 0.25), p * (1 + 0.25))


# ============================================================================================================ marchers
def _sphere_scene(c=(0.0, 0.0, -5.0), r=1.0, scale=1.0):
    c = np.asarray(c, dtype=np.float32)
    return lambda p: F32(scale) * (np.linalg.norm(np.asarray(p, np.float32) - c) - F32(r))


def test_epsilon_is_half_a_pixel_footprint_with_a_floor():
    y = twin("ray")
    assert close(y.rmEpsilon(10.0, 0.002, 1e-4), 0.01)
    assert close(y.rmEpsilon(0.01, 0.002, 1e-4), 1e-4)


def test_sphere_trace_hits_the_first_surface_and_records_the_closest_angular_approach():
    y = twin("ray")
    scene = _sphere_scene()
    hit = y.rmSphereTrace([0.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 50.0], 0.004, 1.0, 96, scene)
    assert hit[3] == 1.0 and abs(hit[0] - 4.0) < 0.5 * 0.004 * 4.0 + 1e-4 and hit[1] < 20
    # a ray that misses the sphere by an angle of about 0.05 radians records about that much (the smallest d / t along
    # the ray is near (5 sin a - 1) / (5 cos a) for a ray at angle a from the centre)
    ang = math.asin(1.0 / 5.0) + 0.05
    rd = np.array([math.sin(ang), 0.0, -math.cos(ang)])
    miss = y.rmSphereTrace([0.0, 0.0, 0.0], rd, [0.0, 50.0], 0.004, 1.0, 96, scene)
    assert miss[3] == 0.0 and 0.03 < miss[2] < 0.06
    assert np.isfinite(miss[0]) and 3.0 < miss[0] < 7.0       # a miss reports where it came closest
    # the march cap holds: never more steps than asked
    capped = y.rmSphereTrace([0.0, 0.0, 0.0], rd, [0.0, 50.0], 0.004, 1.0, 5, scene)
    assert capped[1] <= 5 and capped[3] == 0.0
    # under-relaxation still lands on the surface
    under = y.rmSphereTrace([0.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 50.0], 0.004, 0.6, 96, scene)
    assert under[3] == 1.0 and abs(under[0] - 4.0) < 0.01 and under[1] > hit[1]
    # a camera inside a solid traces its inner wall (the sign at the start is kept), the way a refracted ray must
    inner = y.rmSphereTrace([0.0, 0.0, -5.0], [0.0, 0.0, -1.0], [0.0, 50.0], 0.004, 1.0, 96, scene)
    assert inner[3] == 1.0 and abs(inner[0] - 1.0) < 0.01


def test_relaxed_march_matches_the_plain_one_with_fewer_steps_along_a_floor_and_never_skips_a_thin_wall():
    y = twin("ray")
    floor = lambda p: F32(np.asarray(p, np.float32)[1] + F32(1.0))      # noqa: E731  plane y = -1
    rd = np.array([0.0, -0.05, -1.0])
    rd /= np.linalg.norm(rd)
    plain = y.rmSphereTrace([0.0, 0.0, 0.0], rd, [0.0, 100.0], 0.002, 1.0, 256, floor)
    relaxed = y.rmRelaxed([0.0, 0.0, 0.0], rd, [0.0, 100.0], 0.002, 1.6, 256, floor)
    assert plain[3] == 1.0 and relaxed[3] == 1.0
    for t in (plain[0], relaxed[0]):                              # both stop within half a pixel of the floor
        assert 0.0 <= float(floor(rd * t)) < 0.5 * 0.002 * t + 1e-6
    assert relaxed[1] < 0.75 * plain[1]
    # a thin slab across the ray: over-relaxation would leap it; the overlap check must catch that
    wall = lambda p: F32(abs(float(np.asarray(p)[2]) + 3.0) - 0.02)      # noqa: E731  |z + 3| - 0.02
    r = y.rmRelaxed([0.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 20.0], 0.002, 1.9, 256, wall)
    assert r[3] == 1.0 and abs(r[0] - 2.98) < 0.02


def _wall_at_five(p):
    """The half-space z < -5 is solid: its face stands 5 units ahead of the origin, looking down -z."""
    return F32(np.asarray(p, np.float32)[2] + F32(5.0))


@pytest.mark.parametrize("omega", [1.2, 1.6, 1.9])
@pytest.mark.parametrize("tilt", [0.0, 1e-4, 1e-3])
def test_relaxed_march_never_reports_a_hit_inside_a_solid_it_meets_head_on(omega, tilt):
    # Batch-B review, defect 2: head on, the over-relaxed step lands inside the wall (d < 0) and the overlap check tied
    # exactly (lastRadius + |d| == t - lastT), so the overshoot passed, and then d < eps accepted the negative d as a
    # hit: omega 1.6 reported t = 8.0, three units inside the wall; omega 1.2 reported 6.0. A step that lands inside
    # (d < 0) now always falls back to the plain step, like a gap between the spheres.
    y = twin("ray")
    rd = np.array([tilt, 0.0, -1.0], dtype=np.float32)
    rd /= np.linalg.norm(rd)
    hit = y.rmRelaxed(np.zeros(3, np.float32), rd, (0.0, 50.0), 0.001, omega, 96, _wall_at_five)
    plain = y.rmSphereTrace(np.zeros(3, np.float32), rd, (0.0, 50.0), 0.001, 1.0, 96, _wall_at_five)
    assert hit[3] == 1.0 and plain[3] == 1.0
    eps = 0.5 * 0.001 * float(hit[0])
    assert -1e-5 <= float(_wall_at_five(rd * hit[0])) < eps + 1e-5, (omega, tilt, hit)     # on the face, not inside
    assert abs(float(hit[0]) - float(plain[0])) < eps + 1e-4


@pytest.mark.parametrize("omega", [1.2, 1.6])
def test_relaxed_march_meets_a_ball_head_on_at_its_near_side(omega):
    y = twin("ray")
    ball = _sphere_scene(c=(0.0, 0.0, -6.0), r=1.0)              # its near side is 5 units ahead
    hit = y.rmRelaxed(np.zeros(3, np.float32), np.array([0.0, 0.0, -1.0], np.float32), (0.0, 50.0), 0.001, omega, 96,
                      ball)
    assert hit[3] == 1.0 and abs(float(hit[0]) - 5.0) < 0.5 * 0.001 * 5.0 + 1e-4, hit       # omega 1.2 said 6.0


def test_backtracking_march_survives_a_field_that_overestimates():
    y = twin("ray")
    liar = _sphere_scene(scale=1.4)                  # claims 1.4x the true distance: a plain march oversteps
    plain = y.rmSphereTrace([0.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 50.0], 0.002, 1.0, 96, liar)
    back = y.rmBacktrack([0.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 50.0], 0.002, 96, 12, liar)
    assert plain[3] == 1.0 and abs(plain[0] - 4.0) > 0.5          # it "hits" deep inside the solid
    assert back[3] == 1.0 and abs(back[0] - 4.0) < 0.01 and back[0] <= 4.0 + 1e-4   # never reported inside
    tangent = lambda p: F32(1.4) * (np.linalg.norm(np.asarray(p, np.float32) - F32([0, 1.0, -5])) - F32(1.0))  # noqa
    graze = y.rmBacktrack([0.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 50.0], 0.002, 96, 12, tangent)
    assert np.isfinite(graze[0]) and graze[1] <= 96 + 12


def test_step_helpers_and_the_secondary_origin():
    y = twin("ray")
    assert close(y.rmPassStep(-0.4, 0.01, 4.0), 0.11)
    assert y.rmPassStep(0.0, 0.0, 1.0) > 0                     # never zero
    assert close(y.rmHybridStep(0.3, 0.05), 0.3) and close(y.rmHybridStep(-0.1, 0.05), 0.05)
    assert close(y.rmJitterStart(1.0, 0.2, 0.25), 1.05)
    o = y.rmSecondaryOrigin(np.zeros(3), np.array([0.0, 1.0, 0.0]), -0.003, 1e-3, 1.0)
    assert close(o, [0.0, 0.006, 0.0])
    o = y.rmSecondaryOrigin(np.zeros(3), np.array([0.0, 1.0, 0.0]), 0.0, 1e-3, -1.0)
    assert close(o, [0.0, -0.002, 0.0])


def test_refine_pulls_hits_onto_one_offset_surface():
    y = twin("ray")
    scene = _sphere_scene()
    ro, rd = np.zeros(3), np.array([0.0, 0.0, -1.0])
    for t0 in (3.98, 4.0, 4.02):
        t = y.rmRefine(ro, rd, t0, 0.004, 3, scene)
        assert abs(float(scene(ro + rd * t)) - 0.5 * 0.004 * t) < 1e-4


# ============================================================================================================= normals
def test_tetrahedral_and_central_normals_agree_with_the_analytic_gradient():
    y = twin("ray")
    c = np.array([0.2, -0.1, 0.3])
    scene = lambda p: F32(np.linalg.norm(np.asarray(p, np.float32) - c) - 1.0)       # noqa: E731
    for d in rng(30).normal(size=(50, 3)):
        d /= np.linalg.norm(d)
        p = c + d
        assert close(y.nrmTetra(p, 1e-3, scene), d, 2e-3)
        assert close(y.nrmCentral(p, 1e-3, scene), d, 2e-3)
    flat = lambda p: F32(np.asarray(p)[1] * 0.0 + np.asarray(p)[2] - 1.0)             # noqa: E731
    assert np.all(np.isfinite(y.nrmTetra(np.zeros(3), 1e-3, lambda p: F32(0.0))))    # no gradient: no NaN
    # (float32: f is near -1 here, so each tap carries about 6e-8 of rounding against differences of 4e-3)
    assert close(y.nrmTetra(np.zeros(3), 1e-3, flat), [0.0, 0.0, 1.0], 1e-4)
    assert close(y.nrmTetra(np.zeros(3), -1e-3, flat), [0.0, 0.0, 1.0], 1e-4)         # a negative h still points out
    assert close(y.nrmTetra(np.zeros(3), -2.5, flat), [0.0, 0.0, 1.0], 1e-4)          # every tap twice: still symmetric


def test_normal_epsilon_follows_the_footprint():
    y = twin("ray")
    assert close(y.nrmEps(10.0, 0.002, 1.0), 0.02)
    assert close(y.nrmEps(10.0, 0.002, 3.0), 0.06)
    assert y.nrmEps(0.0, 0.002, 1.0) > 0


def test_curvature_is_the_sum_of_the_principal_curvatures():
    y = twin("ray")
    for R in (0.5, 1.0, 2.0):
        sphere = lambda p, R=R: F32(np.linalg.norm(np.asarray(p, np.float32)) - R)     # noqa: E731
        cyl = lambda p, R=R: F32(math.hypot(float(p[0]), float(p[2])) - R)          # noqa: E731
        assert close(y.nrmCurvature(np.array([0.0, R, 0.0]), 0.01, sphere), 2 / R, 2e-2)
        assert close(y.nrmCurvature(np.array([R, 0.3, 0.0]), 0.01, cyl), 1 / R, 2e-2)
    plane = lambda p: F32(np.asarray(p)[1])                                            # noqa: E731
    assert abs(float(y.nrmCurvature(np.array([0.3, 0.0, 0.1]), 0.01, plane))) < 1e-3


def test_facet_quantises_a_normal_to_a_unit_lattice_direction():
    y = twin("ray")
    a = y.nrmFacet(np.array([0.70, 0.71, 0.0]) / math.hypot(0.70, 0.71), 2.0)
    b = y.nrmFacet(np.array([0.72, 0.69, 0.0]) / math.hypot(0.72, 0.69), 2.0)
    assert close(a, b) and close(np.linalg.norm(a), 1.0)
    assert close(y.nrmFacet(np.array([0.0, 0.0, 1.0]), 3.0), [0.0, 0.0, 1.0])
    assert np.all(np.isfinite(y.nrmFacet(np.array([0.3, 0.3, 0.9]) / np.linalg.norm([0.3, 0.3, 0.9]), 0.2)))


# ====================================================================================================== antialiasing
def _disk_area_beyond(edge, radius, n=200000):
    """The fraction of a disk of `radius` lying beyond a straight line at signed distance `edge` from its centre
    (x > edge), by summing chord lengths over thin strips: no closed form shared with the twin."""
    dx = 2 * radius / n
    xs = -radius + dx * (np.arange(n) + 0.5)
    chord = 2 * np.sqrt(np.maximum(radius * radius - xs * xs, 0))
    return float(np.sum(np.where(xs > edge, chord, 0.0)) * dx / (math.pi * radius * radius))


def test_cone_coverage_is_one_for_every_hit_and_the_disk_area_beyond_half_a_pixel_out():
    y = twin("ray")
    px = 0.004
    assert y.aaConeCoverage(0.0, px) == 1.0 and y.aaConeCoverage(0.5 * px, px) == 1.0
    assert close(y.aaConeCoverage(1.0 * px, px), 0.5)
    assert y.aaConeCoverage(1.5 * px, px) == 0.0 and y.aaConeCoverage(10 * px, px) == 0.0
    prev = 1.0
    for a in np.linspace(0.5 * px, 1.5 * px, 21):
        c = float(y.aaConeCoverage(a, px))
        assert c <= prev + 1e-6
        prev = c
        # every hit stops within half a pixel (rmEpsilon), so for the ramp to meet the hits at 1 without a step the
        # edge is placed a whole pixel out: a - px from the centre of the pixel (a disk one pixel across), covered on
        # the far side of that edge
        want = _disk_area_beyond(a - px, 0.5 * px)
        assert abs(c - want) < 2e-3, (a / px, c, want)


def test_discriminant_edge_is_half_on_the_rim_and_one_pixel_wide():
    y = twin("ray")
    assert close(y.aaDiscriminantEdge(0.0, 0.01), 0.5)
    assert y.aaDiscriminantEdge(0.005, 0.01) == 1.0 and y.aaDiscriminantEdge(-0.005, 0.01) == 0.0
    assert close(y.aaDiscriminantEdge(0.0025, 0.01) + y.aaDiscriminantEdge(-0.0025, 0.01), 1.0)


# ================================================================================================ the modules
def _atlas():
    return json.loads(ATLAS.read_text(encoding="utf-8"))


def _planned(file):
    """(P0 functions the build manifest assigns to this file, every function the atlas plans in it at any status)."""
    a = _atlas()
    manifest = [f for m in a["manifest"] if m["file"] == file for f in m["functions"]]
    planned = {f for p in a["parts"] if p.get("module") == file for f in p["functions"]} | set(manifest)
    return manifest, planned


def _category(file):
    return next(c["id"] for c in _atlas()["categories"] if file in c["modules"])


@pytest.fixture(scope="module")
def house():
    return M.load_library(strict=False)


def _module(house, file):
    path = LIB / file
    assert path.is_file(), f"{file} is not built yet"
    name = MODULES[file]
    assert name in house.modules, f"{name} did not load: {[p for p in house.problems if file in p['path']]}"
    m = house.modules[name]
    assert Path(m.path).resolve() == path.resolve()
    return m


@pytest.mark.parametrize("file", sorted(MODULES))
def test_module_defines_every_planned_p0_function_and_nothing_unplanned(house, file):
    m = _module(house, file)
    manifest, planned = _planned(file)
    defined = set(m.functions) | set(m.consts) | set(m.structs)
    assert set(manifest) <= defined, f"missing: {sorted(set(manifest) - defined)}"
    assert defined <= planned, f"not in the atlas for {file}: {sorted(defined - planned)}"


@pytest.mark.parametrize("file", sorted(MODULES))
def test_module_header_carries_the_library_fields(house, file):
    m = _module(house, file)
    h = m.header
    assert h["name"] == MODULES[file] and h["kind"] == "helper"
    assert h["cat"] == _category(file) and h["family"] == ("D" if file.startswith("sdf/") else "E")
    assert re.fullmatch(r"\d+\.\d+\.\d+", h["version"])
    assert h["license"] == "Apache-2.0" and isinstance(h["credits"], list) and h["credits"]
    assert all("http" in c for c in h["credits"]), "every credit carries its URL"
    assert isinstance(h["cost"], dict) and h["cost"]["class"] in ("C0", "C1", "C2", "C3", "C4")
    for key in ("contract", "note"):
        assert isinstance(h[key], str) and len(h[key]) > 20, key
    assert h["targets"]["glsl"] == "300es" and set(h["targets"]["needs"]) <= set(M.KNOWN_NEEDS)
    assert h["card"] == f"{h['name']}.card" and h["status"] == "P0"
    assert isinstance(h.get("exemplars", []), list) and isinstance(h.get("learn", []), list) and h["learn"]
    code = M.strip_comments(m.body)
    uses_derivatives = any(re.search(rf"\b{d}\b", code) for d in M.DERIVATIVES)
    assert uses_derivatives == ("derivatives" in h["targets"]["needs"]), "declare derivatives exactly when used"
    if file in HOOKED:
        assert h["hooks"] == [SCENE_HOOK] and h["cost"].get("hooks", 0) >= 1
    else:
        assert not h.get("hooks")


@pytest.mark.parametrize("file", sorted(MODULES))
def test_every_glsl_function_has_a_twin_of_the_same_name(house, file):
    m = _module(house, file)
    path, _, fn = m.header["twin"].partition(":")
    assert path.startswith("arsenal/shaders/twins/") and path.endswith(".py")
    mod = importlib.import_module(path[:-3].replace("/", "."))
    for name in (fn,) if fn else tuple(m.functions) + tuple(m.consts):
        assert hasattr(mod, name), f"{path} has no twin for {name}"


@pytest.mark.parametrize("file", sorted(MODULES))
def test_every_loop_has_a_literal_bound(house, file):
    """The TDR floor: a loop's ceiling is a number in the text, whatever its start or its early break."""
    code = M.strip_comments(_module(house, file).body)
    for head in re.findall(r"\bfor\s*\(([^;]*);([^;]*);", code):
        assert re.search(r"<\s*\d+\s*$", head[1].strip()), f"{file}: loop condition '{head[1].strip()}'"
    assert not re.search(r"\bwhile\b", code)


@pytest.mark.parametrize("file", sorted(MODULES))
def test_module_composes_for_webgl2_and_lints_clean(house, file):
    m = _module(house, file)
    text = house.compose([m.name], target="webgl2")
    assert f"--- {m.name} " in text
    assert M.lint(m, library=house) == []


def test_the_scene_hook_is_emitted_once_before_its_first_user(house):
    text = house.compose(["ray-normals", "ray-march"], target="webgl2")
    assert text.count("float mapScene(vec3 p);") == 1
    assert text.index("float mapScene(vec3 p);") < text.index("rmSphereTrace(")


@pytest.mark.parametrize("file", sorted(MODULES))
def test_module_has_a_card_that_builds_against_the_house_library(house, file):
    name = MODULES[file]
    card = K.load_card(name)
    assert name in card.uses and card.note
    shader = K.build_card(card, library=house)
    assert name in shader["card"]["modules"]


# ======================================================================================== the GPU half (slow, locked)
# Batch-B review, defect 6: the light, volume and 2D families each compare their GLSL with their twins on SwiftShader;
# this family's GLSL was checked only by looking at its cards. One probe card (generated here, never tracked) evaluates
# every function of the eight modules at a few arguments and writes each result's float32 bits into pixels, 16 bits per
# pixel; the twins evaluate the same calls on the CPU. It renders on SwiftShader under the house GPU lock (render.py's
# driver, one burst), exactly as tests/test_glsl_twins_light.py does. Deselect with  py -m pytest -m "not slow".
PROBE_COLS = 8              # cases per row; each case is 6 pixels (3 channels x 2 halves of 32 bits)
BALL_C = np.array([0.3, 0.2, -6.0], dtype=np.float32)
LIAR_C = np.array([0.0, 0.0, -5.0], dtype=np.float32)

PROBE_GLSL = """
int probeScene = 0;      // 0: a ball over a floor; 1: a wall 5 ahead; 2: a ball claiming 1.4 times its distance

float mapScene(vec3 p) {
    if (probeScene == 1) {
        return p.z + 5.0;
    }
    if (probeScene == 2) {
        return 1.4 * (length(p - vec3(0.0, 0.0, -5.0)) - 1.0);
    }
    return min(length(p - vec3(0.3, 0.2, -6.0)) - 1.0, p.y + 1.0);
}

vec4 probeMarch(int scene, int which, vec3 ro, vec3 rd, float omega) {
    probeScene = scene;
    vec4 m = which == 0 ? rmSphereTrace(ro, rd, vec2(0.0, 50.0), 0.002, omega, 96)
           : (which == 1 ? rmRelaxed(ro, rd, vec2(0.0, 50.0), 0.002, omega, 96)
                         : rmBacktrack(ro, rd, vec2(0.0, 50.0), 0.002, 96, 12));
    probeScene = 0;
    return m;
}

vec3 probeNormal(int which, vec3 p, float h) {
    probeScene = 0;
    return which == 0 ? nrmTetra(p, h) : nrmCentral(p, h);
}

vec3 probeRepeat(vec3 p, vec3 period, int part) {
    vec3 cell = domRepeat(p, period);
    return part == 0 ? p : cell;
}

vec3 probeRepeatLimited(vec3 p, vec3 period, int part) {
    vec3 cell = domRepeatLimited(p, period, vec3(-2.0, -1.0, 0.0), vec3(2.0, 1.0, 0.0));
    return part == 0 ? p : cell;
}

vec3 probePolar(vec2 p, float count) {
    float sector = domPolar(p, count);
    return vec3(p, sector);
}

vec3 probeReflect(vec3 p, vec3 n, float offset, int part) {
    float side = domReflect(p, n, offset);
    return part == 0 ? p : vec3(side, 0.0, 0.0);
}

vec3 probeInvert(vec3 p, float radiusSq, float scale, int part) {
    vec3 q = domInvert3(p, radiusSq, scale);
    return part == 0 ? q : vec3(scale, 0.0, 0.0);
}

vec3 probeBox(vec3 ro, vec3 rd, vec3 halfSize, int part) {
    vec3 n = vec3(0.0);
    vec2 span = ixBox(ro, rd, halfSize, n);
    return part == 0 ? vec3(span, 0.0) : n;
}

vec3 probeOrtho(vec2 p, vec3 ro, float scale, int part) {
    vec3 origin = ro;
    vec3 dir = camOrthoRay(p, camLookAt(ro, vec3(0.0), 0.3), scale, origin);
    return part == 0 ? dir : origin;
}

vec3 probePath(float t, vec3 amp, vec3 freq, int part) {
    vec3 vel = vec3(0.0);
    vec3 acc = vec3(0.0);
    vec3 pos = pathLissajous3(t, amp, freq, vel, acc);
    return part == 0 ? pos : (part == 1 ? vel : acc);
}
"""


def _probe_scene(kind):
    """The probe's mapScene in float32, for the twins (their scene hook is their LAST argument)."""
    def scene(p):
        p = np.asarray(p, dtype=np.float32)
        if kind == 1:
            return F32(p[2] + F32(5.0))
        if kind == 2:
            return F32(F32(1.4) * (F32(np.linalg.norm(p - LIAR_C)) - F32(1.0)))
        return min(F32(np.linalg.norm(p - BALL_C)) - F32(1.0), F32(p[1] + F32(1.0)))
    return scene


def _v(*xs):
    return np.array(xs, dtype=np.float32)


def unit3(*xs):
    """A unit direction as a tuple of Python floats (the probe writes it as a GLSL literal)."""
    v = np.asarray(xs, dtype=np.float64)
    return tuple(float(c) for c in v / np.linalg.norm(v))


def _three(x):
    """Any twin result (a scalar, a 2- or 3-vector, a bool) as three floats, padded with zeros."""
    a = np.atleast_1d(np.asarray(x, dtype=np.float64)).ravel().tolist()
    return (a + [0.0, 0.0, 0.0])[:3]


def _rot(axis, angle):
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)


def _probe_groups():
    """(label, GLSL expression over the named args, {arg: (type, values)}, twin(**args) -> three floats)."""
    s, y = twin("sdf"), twin("ray")
    f1 = lambda vals: ("float", vals)          # noqa: E731
    v2 = lambda vals: ("vec2", vals)           # noqa: E731
    v3 = lambda vals: ("vec3", vals)           # noqa: E731
    i1 = lambda vals: ("int", vals)            # noqa: E731
    P = [(0.3, -0.4, 0.5), (1.5, 0.2, -0.7), (-0.1, 0.05, 0.02), (2.0, 1.0, -1.5)]
    R = _rot([0.3, 1.0, -0.4], 1.1).astype(np.float32)
    cols = [tuple(float(c) for c in R[:, i]) for i in range(3)]
    zero3 = np.zeros(3, dtype=np.float32)
    up = (0.0, 1.0, 0.0)
    toward = tuple(float(c) for c in (np.array([0.05, -0.1, -1.0]) / np.linalg.norm([0.05, -0.1, -1.0])))
    head_on = (0.0, 0.0, -1.0)
    tilted = tuple(float(c) for c in (np.array([1e-4, 0.0, -1.0]) / np.linalg.norm([1e-4, 0.0, -1.0])))
    floor_ray = tuple(float(c) for c in (np.array([0.0, -0.05, -1.0]) / np.linalg.norm([0.0, -0.05, -1.0])))
    plain, relaxed, backtrack = 0, 1, 2                      # probeMarch's marcher numbers
    ball_floor, wall, liar = 0, 1, 2                         # its scene numbers
    marches = [(ball_floor, plain, toward, 1.0), (ball_floor, plain, floor_ray, 0.7),
               (ball_floor, relaxed, floor_ray, 1.6), (wall, relaxed, head_on, 1.2), (wall, relaxed, head_on, 1.6),
               (wall, relaxed, tilted, 1.9), (wall, plain, head_on, 1.0), (ball_floor, relaxed, toward, 1.5),
               (liar, plain, head_on, 1.0), (liar, backtrack, head_on, 1.0)]
    g = [
        # ------------------------------------------------------------------------------------------- sdf/shapes
        ("sdSphere", "vec3(sdSphere(a, t), 0.0, 0.0)", {"a": v3(P), "t": f1([0.5, 1.0, 0.3, 2.0])},
         lambda a, t: _three(s.sdSphere(a, t))),
        ("sdBox", "vec3(sdBox(a, b), 0.0, 0.0)", {"a": v3(P), "b": v3([(0.4, 0.3, 0.6), (0.5, 0.5, 0.5)])},
         lambda a, b: _three(s.sdBox(a, b))),
        ("sdRoundBox", "vec3(sdRoundBox(a, b, t), 0.0, 0.0)",
         {"a": v3(P), "b": v3([(0.4, 0.3, 0.6)]), "t": f1([0.1, 0.05])},
         lambda a, b, t: _three(s.sdRoundBox(a, b, t))),
        ("sdPlane", "vec3(sdPlane(a, b, t), 0.0, 0.0)",
         {"a": v3(P), "b": v3([(0.0, 0.6, 0.8), up]), "t": f1([-1.0, 0.25])},
         lambda a, b, t: _three(s.sdPlane(a, b, t))),
        ("sdTorusY", "vec3(sdTorusY(a, t, u), 0.0, 0.0)", {"a": v3(P), "t": f1([0.8, 1.2]), "u": f1([0.2, 0.35])},
         lambda a, t, u: _three(s.sdTorusY(a, t, u))),
        ("sdCapsule", "vec3(sdCapsule(a, b, c, t), 0.0, 0.0)",
         {"a": v3(P), "b": v3([(-0.5, 0.0, 0.0), (0.2, 0.2, 0.2)]), "c": v3([(0.5, 0.3, 0.0), (0.2, 0.2, 0.2)]),
          "t": f1([0.25, 0.4])},
         lambda a, b, c, t: _three(s.sdCapsule(a, b, c, t))),
        ("sdCylinderY", "vec3(sdCylinderY(a, t, u), 0.0, 0.0)", {"a": v3(P), "t": f1([0.5, 0.8]), "u": f1([0.6, 0.3])},
         lambda a, t, u: _three(s.sdCylinderY(a, t, u))),
        ("sdConeCappedY", "vec3(sdConeCappedY(a, t, u, v), 0.0, 0.0)",
         {"a": v3(P), "t": f1([0.6, 1.0]), "u": f1([0.5, 0.7]), "v": f1([0.2, 0.0])},
         lambda a, t, u, v: _three(s.sdConeCappedY(a, t, u, v))),
        ("sdRoundConeAB", "vec3(sdRoundConeAB(a, b, c, t, u), 0.0, 0.0)",
         {"a": v3(P), "b": v3([(0.0, -0.3, 0.0)]), "c": v3([(0.4, 0.6, -0.2)]), "t": f1([0.4, 0.3]),
          "u": f1([0.15, 0.3])},
         lambda a, b, c, t, u: _three(s.sdRoundConeAB(a, b, c, t, u))),
        ("sdHexPrismZ", "vec3(sdHexPrismZ(a, t, u), 0.0, 0.0)", {"a": v3(P), "t": f1([0.5, 0.8]), "u": f1([0.3, 0.6])},
         lambda a, t, u: _three(s.sdHexPrismZ(a, t, u))),
        ("sdOctahedron", "vec3(sdOctahedron(a, t), 0.0, 0.0)", {"a": v3(P), "t": f1([0.7, 1.2])},
         lambda a, t: _three(s.sdOctahedron(a, t))),
        ("sbEllipsoid", "vec3(sbEllipsoid(a, b), 0.0, 0.0)", {"a": v3(P), "b": v3([(0.8, 0.4, 0.6), (1.0, 0.5, 0.25)])},
         lambda a, b: _three(s.sbEllipsoid(a, b))),
        ("sbPolyhedron", "vec3(sbPolyhedron(a, t, k), 0.0, 0.0)",
         {"a": v3(P + P[:2]), "t": f1([0.6, 0.8, 0.5, 1.0, 0.7, 0.9]), "k": i1([0, 1, 2, 3, 4, 5])},
         lambda a, t, k: _three(s.sbPolyhedron(a, t, k))),
        ("sbSuperquadric", "vec3(sbSuperquadric(a, b, t), 0.0, 0.0)",
         {"a": v3(P), "b": v3([(0.8, 0.6, 0.7)]), "t": f1([2.0, 4.0, 1.5, 8.0])},
         lambda a, b, t: _three(s.sbSuperquadric(a, b, t))),
        ("udTriangle", "vec3(udTriangle(a, b, c, d), 0.0, 0.0)",
         {"a": v3(P), "b": v3([(0.0, 0.0, 0.0)]), "c": v3([(1.0, 0.0, 0.2)]), "d": v3([(0.2, 0.9, -0.3)])},
         lambda a, b, c, d: _three(s.udTriangle(a, b, c, d))),
        # ------------------------------------------------------------------------------------------ sdf/combine
        ("opUnion opIntersect opSubtract", "vec3(opUnion(t, u), opIntersect(t, u), opSubtract(t, u))",
         {"t": f1([0.3, -0.2, 0.5]), "u": f1([-0.1, 0.4, 0.5])},
         lambda t, u: [float(s.opUnion(t, u)), float(s.opIntersect(t, u)), float(s.opSubtract(t, u))]),
        ("opXor opRound opOnion", "vec3(opXor(t, u), opRound(t, u), opOnion(t, u))",
         {"t": f1([0.3, -0.2, 0.5]), "u": f1([-0.1, 0.4, 0.05])},
         lambda t, u: [float(s.opXor(t, u)), float(s.opRound(t, u)), float(s.opOnion(t, u))]),
        ("opPick", "vec3(opPick(vec2(t, 1.0), vec2(u, 2.0)), 0.0)", {"t": f1([0.3, -0.2, 0.5]), "u": f1([-0.1, 0.4, 0.5])},
         lambda t, u: _three(s.opPick(_v(t, 1.0), _v(u, 2.0)))),
        ("opSmin opSmax opSsubtract", "vec3(opSmin(t, u, v), opSmax(t, u, v), opSsubtract(t, u, v))",
         {"t": f1([0.3, -0.2, 0.1, 0.0]), "u": f1([0.2, 0.4, 0.5, 0.0]), "v": f1([0.1, 0.2, 0.05, 0.3])},
         lambda t, u, v: [float(s.opSmin(t, u, v)), float(s.opSmax(t, u, v)), float(s.opSsubtract(t, u, v))]),
        ("opSminMix", "vec3(opSminMix(t, u, v), 0.0)",
         {"t": f1([0.3, -0.2, 0.1]), "u": f1([0.2, 0.4, 0.5]), "v": f1([0.1, 0.2, 0.05])},
         lambda t, u, v: _three(s.opSminMix(t, u, v))),
        ("opSminCircular opSminExp opDisplace", "vec3(opSminCircular(t, u, v), opSminExp(t, u, v), "
         "opDisplace(t, u, v))", {"t": f1([0.3, -0.2, 0.1]), "u": f1([0.2, 0.4, 0.5]), "v": f1([0.1, 0.2, 0.05])},
         lambda t, u, v: [float(s.opSminCircular(t, u, v)), float(s.opSminExp(t, u, v)),
                          float(s.opDisplace(t, u, v))]),
        ("opUniformScale", "vec3(opUniformScale(t, u), 0.0, 0.0)", {"t": f1([0.3, -0.2]), "u": f1([2.0, 0.5])},
         lambda t, u: _three(s.opUniformScale(t, u))),
        # ------------------------------------------------------------------------------------------ sdf/domain3
        ("domRigid", "domRigid(a, mat3(b, c, d), e)",
         {"a": v3(P), "b": v3([cols[0]]), "c": v3([cols[1]]), "d": v3([cols[2]]), "e": v3([(0.5, -1.0, 2.0)])},
         lambda a, b, c, d, e: _three(s.domRigid(a, np.stack([b, c, d], axis=1), e))),
        ("domMirror", "domMirror(a, b)", {"a": v3(P), "b": v3([(1.0, 0.0, 1.0), (0.0, 1.0, 0.0)])},
         lambda a, b: _three(s.domMirror(a, b))),
        ("domTwistY", "domTwistY(a, t)", {"a": v3(P), "t": f1([2.0, -0.7])}, lambda a, t: _three(s.domTwistY(a, t))),
        ("domBend", "domBend(a, t)", {"a": v3(P), "t": f1([0.8, -1.3])}, lambda a, t: _three(s.domBend(a, t))),
        ("lipTwist", "vec3(lipTwist(t, u), 0.0, 0.0)", {"t": f1([1.0, 3.0, -0.5]), "u": f1([1.0, 0.7, 2.0])},
         lambda t, u: _three(s.lipTwist(t, u))),
        ("domRepeat point", "probeRepeat(a, b, 0)", {"a": v3(P), "b": v3([(1.0, 2.0, 0.5), (0.0, 1.0, 0.7)])},
         lambda a, b: _three(s.domRepeat(a, b)[0])),
        ("domRepeat cell", "probeRepeat(a, b, 1)", {"a": v3(P), "b": v3([(1.0, 2.0, 0.5), (0.3, 1.0, 0.7)])},
         lambda a, b: _three(s.domRepeat(a, b)[1])),
        ("domRepeatLimited point", "probeRepeatLimited(a * 4.0, b, 0)", {"a": v3(P), "b": v3([(1.0, 2.0, 0.5)])},
         lambda a, b: _three(s.domRepeatLimited(a * F32(4.0), b, [-2.0, -1.0, 0.0], [2.0, 1.0, 0.0])[0])),
        ("domRepeatLimited cell", "probeRepeatLimited(a * 4.0, b, 1)", {"a": v3(P), "b": v3([(1.0, 2.0, 0.5)])},
         lambda a, b: _three(s.domRepeatLimited(a * F32(4.0), b, [-2.0, -1.0, 0.0], [2.0, 1.0, 0.0])[1])),
        ("domPolar", "probePolar(m, t)", {"m": v2([(0.3, -0.4), (-1.2, 0.5), (0.0, 0.0), (-0.7, -0.9)]),
                                          "t": f1([7.0, 5.0, 3.0, 6.6])},
         lambda m, t: (lambda q, k: [float(q[0]), float(q[1]), float(k)])(*s.domPolar(m, t))),
        ("domReflect point", "probeReflect(a, b, t, 0)",
         {"a": v3(P), "b": v3([(0.0, 0.6, 0.8)]), "t": f1([0.2, -0.5])},
         lambda a, b, t: _three(s.domReflect(a, b, t)[0])),
        ("domReflect side", "probeReflect(a, b, t, 1)",
         {"a": v3(P), "b": v3([(0.0, 0.6, 0.8)]), "t": f1([0.2, -0.5])},
         lambda a, b, t: _three(s.domReflect(a, b, t)[1])),
        ("domFoldIcosa", "domFoldIcosa(a)", {"a": v3(P + [(-0.3, -0.8, -0.5)])}, lambda a: _three(s.domFoldIcosa(a))),
        ("domInvert3 point", "probeInvert(a, t, u, 0)", {"a": v3(P), "t": f1([1.0, 2.5]), "u": f1([1.0, 0.5])},
         lambda a, t, u: _three(s.domInvert3(a, t, u)[0])),
        ("domInvert3 scale", "probeInvert(a, t, u, 1)", {"a": v3(P), "t": f1([1.0, 2.5]), "u": f1([1.0, 0.5])},
         lambda a, t, u: _three(s.domInvert3(a, t, u)[1])),
        # --------------------------------------------------------------------------------------- ray/intersect
        ("ixSphere", "vec3(ixSphere(a, b, c, t), 0.0)",
         {"a": v3([(0.0, 0.0, 0.0), (0.1, 0.0, 0.0), (0.0, 0.0, -6.0)]), "b": v3([toward, head_on, head_on]),
          "c": v3([(0.3, -0.3, -6.0), (0.0, 0.0, -6.0), (0.0, 0.0, -6.0)]), "t": f1([1.0, 0.5, 1.0])},
         lambda a, b, c, t: _three(y.ixSphere(a, b, c, t))),
        ("ixBox span", "probeBox(a, b, c, 0)",
         {"a": v3([(0.0, 0.0, 3.0), (2.0, 0.5, 0.0), (0.1, 0.1, 0.1)]),
          "b": v3([head_on, (-1.0, 0.0, 0.0), toward]), "c": v3([(0.5, 0.5, 0.5), (0.4, 0.8, 0.6), (1.0, 1.0, 1.0)])},
         lambda a, b, c: _three(y.ixBox(a, b, c)[0])),
        ("ixBox normal", "probeBox(a, b, c, 1)",
         {"a": v3([(0.0, 0.0, 3.0), (2.0, 0.5, 0.0)]), "b": v3([head_on, (-1.0, 0.0, 0.0)]),
          "c": v3([(0.5, 0.5, 0.5), (0.4, 0.8, 0.6)])},
         lambda a, b, c: _three(y.ixBox(a, b, c)[1])),
        ("ixPlane", "vec3(ixPlane(a, b, c, t), 0.0, 0.0)",
         {"a": v3([(0.0, 1.0, 0.0), (0.0, 1.0, 0.0), (0.0, -2.0, 0.0)]), "b": v3([floor_ray, (0.0, 1.0, 0.0), toward]),
          "c": v3([up]), "t": f1([1.0, 1.0, 1.0])},
         lambda a, b, c, t: _three(y.ixPlane(a, b, c, t))),
        ("ixSlabY", "vec3(ixSlabY(t, u, v, w), 0.0)",
         {"t": f1([0.0, 2.0, 0.5]), "u": f1([0.5, -0.25, 0.0]), "v": f1([1.0, 0.0, 0.0]), "w": f1([2.0, 1.0, 1.0])},
         lambda t, u, v, w: _three(y.ixSlabY(t, u, v, w))),
        ("ixShell", "vec3(ixShell(a, b, c, t, u), 0.0)",
         {"a": v3([(0.0, 0.0, 0.0), (0.0, 0.0, -6.0), (0.0, 0.0, -6.8)]), "b": v3([head_on]),
          "c": v3([(0.0, 0.0, -6.0)]), "t": f1([0.5]), "u": f1([1.0])},
         lambda a, b, c, t, u: _three(y.ixShell(a, b, c, t, u))),
        ("rmClipToBox", "vec3(rmClipToBox(a, b, c, d, m), 0.0)",
         {"a": v3([(0.0, 0.0, 3.0), (0.0, 3.0, 3.0)]), "b": v3([head_on]), "c": v3([(0.0, 0.0, -1.0)]),
          "d": v3([(0.5, 0.5, 0.5)]), "m": v2([(0.0, 20.0), (4.5, 5.0)])},
         lambda a, b, c, d, m: _three(y.rmClipToBox(a, b, c, d, m))),
        ("bvCanSkip", "vec3(bvCanSkip(t, u) ? 1.0 : 0.0, 0.0, 0.0)", {"t": f1([2.0, 0.5]), "u": f1([1.0, 1.0])},
         lambda t, u: _three(1.0 if y.bvCanSkip(t, u) else 0.0)),
        ("ixSphereAlt", "vec3(ixSphereAlt(t, u, v), 0.0)",
         {"t": f1([6371.5, 6371.5, 6500.0]), "u": f1([0.2, -1.0, -0.99]), "v": f1([6371.0, 6371.0, 6400.0])},
         lambda t, u, v: _three(y.ixSphereAlt(t, u, v))),
        # ----------------------------------------------------------------------------------------- ray/camera
        ("camLookAt", "camLookAt(a, b, t)[k]",
         {"a": v3([(2.0, 1.5, 3.0)] * 3 + [(0.0, 5.0, 0.0)] * 3), "b": v3([(0.0, 0.35, 0.0)]),
          "t": f1([0.0, 0.0, 0.0, 0.4, 0.4, 0.4]), "k": i1([0, 1, 2, 0, 1, 2])},
         lambda a, b, t, k: _three(y.camLookAt(a, b, t)[:, k])),
        ("camRay", "camRay(m, vec2(320.0, 180.0), camLookAt(a, vec3(0.0), 0.0), t)",
         {"m": v2([(160.5, 90.5), (0.5, 0.5), (300.0, 20.0)]), "a": v3([(2.0, 1.5, 3.0)]), "t": f1([1.7, 2.2, 1.0])},
         lambda m, a, t: _three(y.camRay(m, [320.0, 180.0], y.camLookAt(a, zero3, 0.0), t))),
        ("camPixelAngle", "vec3(camPixelAngle(t, u), 0.0, 0.0)", {"t": f1([1.0, 0.6]), "u": f1([180.0, 1080.0])},
         lambda t, u: _three(y.camPixelAngle(t, u))),
        ("camOrbit", "camOrbit(m, t, u, a)",
         {"m": v2([(0.0, 0.0), (0.25, 0.75), (0.9, 0.1)]), "t": f1([0.8, 0.8, 2.0]), "u": f1([3.0, 2.0, 4.0]),
          "a": v3([(0.0, 0.5, 0.0)])},
         lambda m, t, u, a: _three(y.camOrbit(m, t, u, a))),
        ("camOrthoRay dir", "probeOrtho(m, a, t, 0)",
         {"m": v2([(0.2, -0.3), (-1.0, 0.5)]), "a": v3([(2.0, 1.5, 3.0)]), "t": f1([2.0, 0.5])},
         lambda m, a, t: _three(y.camOrthoRay(m, y.camLookAt(a, zero3, 0.3), t, a)[0])),
        ("camOrthoRay origin", "probeOrtho(m, a, t, 1)",
         {"m": v2([(0.2, -0.3), (-1.0, 0.5)]), "a": v3([(2.0, 1.5, 3.0)]), "t": f1([2.0, 0.5])},
         lambda m, a, t: _three(y.camOrthoRay(m, y.camLookAt(a, zero3, 0.3), t, a)[1])),
        ("pathLissajous3", "probePath(t, a, b, k)",
         {"t": f1([1.3, 1.3, 1.3, 0.4]), "a": v3([(1.0, 0.5, 2.0)]), "b": v3([(0.7, 0.0, 1.9)]),
          "k": i1([0, 1, 2, 2])},
         lambda t, a, b, k: _three(y.pathLissajous3(t, a, b)[k])),
        ("camBanked", "camBanked(a, b, t)[k]",
         {"a": v3([(1.0, 0.2, -1.0)]), "b": v3([(0.3, 0.0, 0.4)]), "t": f1([0.5, 0.5, 0.5]), "k": i1([0, 1, 2])},
         lambda a, b, t, k: _three(y.camBanked(a, b, t)[:, k])),
        ("camBarrel", "vec3(camBarrel(m, t), 0.0)", {"m": v2([(0.3, -0.4), (1.2, 0.6)]), "t": f1([0.15, -0.1])},
         lambda m, t: _three(y.camBarrel(m, t))),
        # ------------------------------------------------------------------------------------------ ray/march
        ("rmEpsilon rmPassStep rmHybridStep", "vec3(rmEpsilon(t, u, 1e-4), rmPassStep(v, 0.01, u * 1000.0), "
         "rmHybridStep(v, u))", {"t": f1([10.0, 0.01, 3.0]), "u": f1([0.002, 0.004, 0.05]),
                                 "v": f1([-0.4, 0.3, 0.0])},
         lambda t, u, v: [float(y.rmEpsilon(t, u, 1e-4)), float(y.rmPassStep(v, 0.01, F32(u) * F32(1000.0))),
                          float(y.rmHybridStep(v, u))]),
        ("rmJitterStart", "vec3(rmJitterStart(t, u, v), 0.0, 0.0)",
         {"t": f1([1.0, 0.0]), "u": f1([0.2, 0.3]), "v": f1([0.25, 0.9])},
         lambda t, u, v: _three(y.rmJitterStart(t, u, v))),
        ("rmSecondaryOrigin", "rmSecondaryOrigin(a, b, t, 1e-3, u)",
         {"a": v3([(0.0, 0.0, 0.0), (1.0, 2.0, 3.0)]), "b": v3([up, (0.0, 0.6, 0.8)]), "t": f1([-0.003, 0.0]),
          "u": f1([1.0, -1.0])},
         lambda a, b, t, u: _three(y.rmSecondaryOrigin(a, b, t, 1e-3, u))),
        # the marchers: (t, steps, hit), then the smallest d / t; scene 0 a ball over a floor, 1 a wall head on (the
        # defect 2 case: rmRelaxed used to report 6 and 8 there), 2 a ball that claims 1.4 times its distance
        ("march t steps hit", "probeMarch(k, j, vec3(0.0), a, t).xyw",
         {"k": i1([c[0] for c in marches]), "j": i1([c[1] for c in marches]), "a": v3([c[2] for c in marches]),
          "t": f1([c[3] for c in marches])},
         lambda k, j, a, t: _march_twin(y, k, j, a, t)[[0, 1, 3]].tolist()),
        ("march closest", "vec3(probeMarch(k, j, vec3(0.0), a, t).z, 0.0, 0.0)",
         {"k": i1([0, 0, 0]), "j": i1([0, 1, 2]), "a": v3([unit3(0.3, 0.6, -0.75), unit3(0.3, 0.6, -0.75),
                                                          unit3(0.5, 0.2, -0.85)]),
          "t": f1([1.0, 1.6, 1.0])},
         lambda k, j, a, t: _three(_march_twin(y, k, j, a, t)[2])),
        ("rmRefine", "vec3(rmRefine(vec3(0.0), a, t, 0.002, 3), 0.0, 0.0)",
         {"a": v3([head_on, toward]), "t": f1([4.98, 5.0])},
         lambda a, t: _three(y.rmRefine(zero3, a, t, 0.002, 3, _probe_scene(0)))),
        # ---------------------------------------------------------------------------------------- ray/normals
        ("nrmTetra", "probeNormal(0, a, t)",
         {"a": v3([(0.3, 1.2, -6.0), (1.3, 0.2, -6.0), (0.0, -1.0, 0.0), (0.3, -0.5, -5.2)]),
          "t": f1([1e-3, 2e-3, 1e-3, -1e-3])},
         lambda a, t: _three(y.nrmTetra(a, t, _probe_scene(0)))),
        ("nrmCentral", "probeNormal(1, a, t)",
         {"a": v3([(0.3, 1.2, -6.0), (1.3, 0.2, -6.0), (0.0, -1.0, 0.0)]), "t": f1([1e-3, 2e-3, 1e-3])},
         lambda a, t: _three(y.nrmCentral(a, t, _probe_scene(0)))),
        ("nrmCurvature", "vec3(nrmCurvature(a, t), 0.0, 0.0)",
         {"a": v3([(0.3, 1.2, -6.0), (2.0, -1.0, 0.0)]), "t": f1([0.05, 0.05])},
         lambda a, t: _three(y.nrmCurvature(a, t, _probe_scene(0)))),
        ("nrmEps", "vec3(nrmEps(t, u, v), 0.0, 0.0)", {"t": f1([10.0, 0.0]), "u": f1([0.002, 0.002]), "v": f1([3.0, 1.0])},
         lambda t, u, v: _three(y.nrmEps(t, u, v))),
        ("nrmFacet", "nrmFacet(a, t)",
         {"a": v3([tuple(float(c) for c in _v(0.70, 0.71, 0.0) / np.linalg.norm([0.70, 0.71, 0.0])),
                   tuple(float(c) for c in _v(0.3, 0.3, 0.9) / np.linalg.norm([0.3, 0.3, 0.9]))]),
          "t": f1([2.0, 3.0])},
         lambda a, t: _three(y.nrmFacet(a, t))),
        # -------------------------------------------------------------------------------------------- ray/aa3
        ("aaConeCoverage aaDiscriminantEdge", "vec3(aaConeCoverage(t, 0.004), aaDiscriminantEdge(u, 0.01), 0.0)",
         {"t": f1([0.0, 0.003, 0.004, 0.0052, 0.01]), "u": f1([0.0, 0.0025, -0.0025, 0.004, -0.01])},
         lambda t, u: [float(y.aaConeCoverage(t, 0.004)), float(y.aaDiscriminantEdge(u, 0.01)), 0.0]),
    ]
    return g


def _march_twin(y, kind, which, rd, omega):
    scene = _probe_scene(kind)
    ro, rng_ = np.zeros(3, dtype=np.float32), (0.0, 50.0)
    if which == 0:
        return y.rmSphereTrace(ro, rd, rng_, 0.002, omega, 96, scene)
    if which == 1:
        return y.rmRelaxed(ro, rd, rng_, 0.002, omega, 96, scene)
    return y.rmBacktrack(ro, rd, rng_, 0.002, 96, 12, scene)


PROBE_DEFAULT_TOL = 1e-4    # float32 on SwiftShader against float32 on the CPU, relative to max(1, |value|)
# SwiftShader's sin and cos are approximations (measured here: 2.7e-4 off at -0.14 rad, through rotate2), so a result
# that goes through a rotation gets 1e-3; a wrong sign, a wrong axis or an unrounded sector count is off by far more.
TRIG_TOL = 1e-3
PROBE_TOLERANCE = {"sbSuperquadric": 1e-3, "march t steps hit": 1e-3, "march closest": 1e-3, "rmRefine": 1e-3,
                   "nrmTetra": 2e-3, "nrmCentral": 2e-3, "nrmCurvature": 2e-2, "ixSphereAlt": 3e-4,
                   "domInvert3 point": 3e-4, "domInvert3 scale": 3e-4, "opSminCircular opSminExp opDisplace": 3e-4,
                   "domTwistY": TRIG_TOL, "domBend": TRIG_TOL, "domPolar": TRIG_TOL, "camLookAt": TRIG_TOL,
                   "camOrbit": TRIG_TOL, "camOrthoRay dir": TRIG_TOL, "camOrthoRay origin": TRIG_TOL,
                   "pathLissajous3": TRIG_TOL}


def _probe_literal(kind, v):
    if kind == "int":
        return str(int(v))
    if kind == "float":
        return repr(float(v)) if math.isfinite(float(v)) else "0.0"
    return f"{kind}(" + ", ".join(repr(float(c)) for c in v) + ")"


def _probe_card(groups):
    decls, branches, n = [], [], 0
    for gi, (label, expr, args, _) in enumerate(groups):
        count = max(len(v) for _, v in args.values())
        local = []
        for arg, (kind, vals) in args.items():
            vals = list(vals) + [vals[-1]] * (count - len(vals))
            decls.append(f"const {kind} PROBE_G{gi}_{arg.upper()}[{count}] = {kind}[{count}]("
                         + ", ".join(_probe_literal(kind, v) for v in vals) + ");")
            local.append(f"{kind} {arg} = PROBE_G{gi}_{arg.upper()}[i];")
        branches.append(f"    if (i < {count}) {{ {' '.join(local)} return {expr}; }}  // {label}\n    i -= {count};")
        n += count
    rows = (n + PROBE_COLS - 1) // PROBE_COLS
    header = {"card": "rays-twin-probe", "uses": sorted(MODULES.values()), "t": [0], "size": [PROBE_COLS * 6, rows],
              "note": "TEST PROBE (tests/test_glsl_twins_3d_rays.py): float32 bits of every case, 16 bits per pixel."}
    body = "\n".join(decls) + "\n" + PROBE_GLSL + "\nvec3 probeCase(int i) {\n" + "\n".join(branches) + \
        "\n    return vec3(-7.0);   // padding past the last case: never decoded\n}\n\n" + """
void mainImage(out vec4 probeOut, in vec2 probeAt) {
    ivec2 cell = ivec2(probeAt);
    int caseIndex = cell.y * """ + str(PROBE_COLS) + """ + cell.x / 6;
    int slot = cell.x - (cell.x / 6) * 6;
    vec3 v = probeCase(caseIndex);
    float f = slot < 2 ? v.x : (slot < 4 ? v.y : v.z);
    uint bits = floatBitsToUint(f);
    uint half16 = (slot - (slot / 2) * 2 == 0) ? (bits >> 16u) : (bits & 65535u);
    probeOut = vec4(float(half16 >> 8u) / 255.0, float(half16 & 255u) / 255.0, 0.0, 1.0);
}
"""
    return "//! " + json.dumps(header) + "\n// Apache-2.0, Akashic Aurora. Generated by the test; never tracked.\n" + body, n


def _probe_decode(png: Path, n: int) -> np.ndarray:
    from PIL import Image
    with Image.open(png) as im:
        px = np.asarray(im.convert("RGB"), dtype=np.uint32)
    px = px[::-1]                                       # PNG row 0 is the top; fragment row 0 is the bottom
    out = np.zeros((n, 3), dtype=np.float32)
    for i in range(n):
        row, x0 = divmod(i, PROBE_COLS)
        for ch in range(3):
            hi = px[row, x0 * 6 + 2 * ch]
            lo = px[row, x0 * 6 + 2 * ch + 1]
            bits = (((hi[0] << 8) | hi[1]) << 16) | ((lo[0] << 8) | lo[1])
            out[i, ch] = np.array([bits], dtype=np.uint32).view(np.float32)[0]
    return out


def test_the_probe_covers_every_function_of_the_eight_modules(house):
    groups = _probe_groups()
    probed = {fn for _label, expr, _args, _twin in groups for fn in M.CALL_RE.findall(expr)}
    probed |= set(M.CALL_RE.findall(PROBE_GLSL))
    every = {fn for file in MODULES for fn in _module(house, file).functions}
    assert sorted(every - probed) == []


@pytest.fixture(scope="module")
def gpu(tmp_path_factory):
    import shutil
    if shutil.which("node") is None:
        pytest.skip("node is not on PATH (the headless driver)")
    groups = _probe_groups()
    text, n = _probe_card(groups)
    cards_dir = tmp_path_factory.mktemp("rays_probe_cards")
    (cards_dir / "rays-twin-probe.card").write_text(text, encoding="utf-8", newline="\n")
    out = tmp_path_factory.mktemp("rays_probe_out")
    report = K.render_cards(["rays-twin-probe"], cards_dir=cards_dir, out_root=out, allow_tracked=True,
                            lock_wait_min=5, quiet=True)
    driver = report["driver"]
    if driver.get("error") and "lock" in str(driver["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {driver['error']}")
    assert not driver.get("refused"), driver["refused"]
    row = report["cards"][0]
    assert row.get("compile_ok") is True, row
    receipt = json.loads(Path(row["receipt"]).read_text(encoding="utf-8"))
    return groups, _probe_decode(Path(receipt["card"]["frames"][0]["png"]), n)


def probe_disagreements(groups, got) -> list:
    """Every probe case where the GLSL's float32 result and the twin's differ by more than the label's tolerance."""
    i, bad = 0, []
    for label, _expr, args, twin_fn in groups:
        count = max(len(v) for _, v in args.values())
        for k in range(count):
            pick = {arg: vals[min(k, len(vals) - 1)] for arg, (kind, vals) in args.items()}
            call = {arg: (np.asarray(v, dtype=np.float32) if args[arg][0] in ("vec2", "vec3")
                          else (int(v) if args[arg][0] == "int" else float(v))) for arg, v in pick.items()}
            want = np.asarray(twin_fn(**call), dtype=np.float64).reshape(3)
            tol = PROBE_TOLERANCE.get(label, PROBE_DEFAULT_TOL) * np.maximum(1.0, np.abs(want))
            if not (np.all(np.isfinite(got[i])) and np.all(np.abs(got[i] - want) <= tol)):
                bad.append(f"{label}[{k}] {pick}: glsl {got[i].tolist()} twin {want.tolist()}")
            i += 1
    return bad


@pytest.mark.slow
def test_glsl_rays_and_sdf_modules_agree_with_their_twins_on_swiftshader(gpu):
    groups, got = gpu
    bad = probe_disagreements(groups, got)
    assert not bad, "\n".join(bad)
