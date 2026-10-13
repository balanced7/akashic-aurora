"""Pins for the 2D drawing family of the house GLSL library (shader school batch B, 2026-10-13), and for the triangle
filament noise that the aurora's band and sheet tiers draw their footprint from.

WHAT THIS FAMILY IS. The pen, the ruler and the stencil (atlas family C), plus one fabric from family B:

    draw2/sdf2.glsl       exact 2D signed distances: circle, box, rounded box, segment, pointy-top hexagon
    draw2/aa.glsl         coverage from a distance: the one-pixel fill, the band, the phone-wire hairline, the threshold
    draw2/domain2.glsl    polar coordinates, centred repetition, the mirrored kaleidoscope (operators return the id)
    draw2/lattice.glsl    the pointy-top hex lattice by two rectangular grids, the border distance, axial coordinates
    draw2/pattern.glsl    the per-cell delay that turns a wave into a mosaic of whole tiles
    noise/triangle.glsl   octaves of a bent triangle wave on a turned, slowly churning domain: crease-y filaments

WHY THESE PINS. Every edge the house draws goes through these parts (Daniel's ruling R4: pixel perfect, un-aliased),
so a distance that is a bound where it claims to be exact, a coverage whose ink is not the line's true width, or a hex
lattice whose id is not constant across its cell would show up on every surface at once. A shader cannot print, so each
GLSL function has a CPU twin (arsenal/shaders/twins/draw2.py and triangle.py) with the same name, and the twin is held
to an independent reference: the exact distances to a brute-force distance from thousands of boundary points, the
coverages to a numerical box filter, the lattice to the nearest of all candidate centres, the noise to a second
writing of its own contract in plain Python. The slow test at the bottom renders a parity card on SwiftShader and holds
the GLSL to the twin pixel by pixel.

Like a calibration bench: the twin is the golden model, the brute force is the reference standard, and the SwiftShader
render is the device under test. All three must agree.

Apache-2.0, Akashic Aurora. Written fresh for the house; no corpus code.
"""
from __future__ import annotations

import importlib
import json
import math
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from arsenal.shaders import cards as K
from arsenal.shaders import modules as M

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "arsenal" / "web" / "glsl"
ATLAS = REPO / "arsenal" / "shaders" / "atlas.json"
F32 = np.float32

# file (under arsenal/web/glsl/) -> module name. The atlas plans the files and their functions; the names are ours.
FAMILY = {
    "noise/triangle.glsl": "noise-triangle",
    "draw2/sdf2.glsl": "draw2-sdf2",
    "draw2/aa.glsl": "draw2-aa",
    "draw2/domain2.glsl": "draw2-domain2",
    "draw2/lattice.glsl": "draw2-lattice",
    "draw2/pattern.glsl": "draw2-pattern",
}


def twin(area: str):
    """The twin module, imported inside each test so a missing twin fails that test by name (not the whole file)."""
    return importlib.import_module(f"arsenal.shaders.twins.{area}")


def close(a, b, tol=1e-6):
    return np.allclose(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64), rtol=tol, atol=tol)


RNG = np.random.default_rng(20261013)


# ===================================================================================== the brute-force references
def _polyline_distance(points, outline):
    """Distance from each point to the closed polyline `outline` (a dense ring of boundary points), in float64."""
    pts = np.asarray(points, dtype=np.float64)
    a = np.asarray(outline, dtype=np.float64)
    b = np.roll(a, -1, axis=0)
    ab = b - a
    ap = pts[:, None, :] - a[None, :, :]
    h = np.clip(np.sum(ap * ab, -1) / np.maximum(np.sum(ab * ab, -1), 1e-300), 0, 1)
    gap = ap - h[..., None] * ab
    return np.sqrt(np.min(np.sum(gap * gap, -1), axis=1))


def _inside(points, outline):
    """Even-odd point-in-polygon test against the outline ring."""
    pts = np.asarray(points, dtype=np.float64)
    a = np.asarray(outline, dtype=np.float64)
    b = np.roll(a, -1, axis=0)
    x, y = pts[:, 0:1], pts[:, 1:2]
    crosses = ((a[:, 1] > y) != (b[:, 1] > y)) & (
        x < (b[:, 0] - a[:, 0]) * (y - a[:, 1]) / np.where(b[:, 1] == a[:, 1], 1e-300, b[:, 1] - a[:, 1]) + a[:, 0])
    return (np.count_nonzero(crosses, axis=1) % 2) == 1


def _signed_reference(points, outline):
    d = _polyline_distance(points, outline)
    return np.where(_inside(points, outline), -d, d)


def _rounded_rectangle(half, r, n=4096):
    """The outline of a rectangle of half-size `half` whose corners are arcs of radius r (r = 0: sharp corners)."""
    pts = []
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    start = [0.0, 0.5 * math.pi, math.pi, 1.5 * math.pi]
    for (sx, sy), a0 in zip(corners, start):
        cx, cy = sx * (half[0] - r), sy * (half[1] - r)
        for k in range(n // 4):
            a = a0 + 0.5 * math.pi * k / (n // 4 - 1)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def _hexagon_outline(inradius, n_per_edge=1024):
    """A pointy-top hexagon: vertices at angles 30, 90, 150, ... degrees, circumradius 2 a / sqrt 3."""
    big = 2.0 * inradius / math.sqrt(3.0)
    verts = [(big * math.cos(math.radians(30 + 60 * k)), big * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    pts = []
    for k in range(6):
        (x0, y0), (x1, y1) = verts[k], verts[(k + 1) % 6]
        for j in range(n_per_edge):
            s = j / n_per_edge
            pts.append((x0 + s * (x1 - x0), y0 + s * (y1 - y0)))
    return np.array(pts)


# ================================================================================================ draw2/sdf2.glsl
def test_circle_is_the_distance_to_the_rim_negative_inside():
    d = twin("draw2")
    assert close(d.sd2Circle([0.0, 0.0], 0.5), -0.5)
    assert close(d.sd2Circle([3.0, 4.0], 2.0), 3.0)
    assert close(d.sd2Circle([0.0, -0.25], 0.25), 0.0)


def test_box_is_exact_inside_and_out_against_brute_force():
    d = twin("draw2")
    half = (0.7, 0.35)
    pts = RNG.uniform(-1.5, 1.5, (600, 2))
    ref = _signed_reference(pts, _rounded_rectangle(half, 0.0, n=8192))
    got = d.sd2Box(pts.astype(F32), np.array(half, F32))
    assert np.max(np.abs(got - ref)) < 2e-3
    assert close(d.sd2Box([0.0, 0.0], [0.7, 0.35]), -0.35)               # the centre: the nearer edge
    assert close(d.sd2Box([1.7, 1.35], [0.7, 0.35]), math.sqrt(2.0))     # outside a corner: distance to the corner


def test_round_box_keeps_its_outer_extent_and_is_exact():
    d = twin("draw2")
    half, r = (0.8, 0.4), 0.25
    assert close(d.sd2RoundBox([0.8, 0.0], half, r), 0.0) and close(d.sd2RoundBox([0.0, 0.4], half, r), 0.0)
    pts = RNG.uniform(-1.4, 1.4, (600, 2))
    ref = _signed_reference(pts, _rounded_rectangle(half, r, n=8192))
    got = d.sd2RoundBox(pts.astype(F32), np.array(half, F32), F32(r))
    assert np.max(np.abs(got - ref)) < 2e-3
    # a radius of zero is the box; a radius past the shorter half-size is held at it (a stadium, never inverted)
    assert close(d.sd2RoundBox(pts.astype(F32), np.array(half, F32), F32(0.0)), d.sd2Box(pts.astype(F32), half), 1e-6)
    assert close(d.sd2RoundBox(pts.astype(F32), np.array(half, F32), F32(9.0)),
                 d.sd2RoundBox(pts.astype(F32), np.array(half, F32), F32(0.4)), 1e-6)


def test_segment_gives_the_distance_and_the_parameter_along_it():
    d = twin("draw2")
    a, b = np.array([-1.0, 0.0], F32), np.array([1.0, 0.0], F32)
    assert close(d.sd2Segment([0.0, 0.5], a, b), [0.5, 0.5])
    assert close(d.sd2Segment([-3.0, 0.0], a, b), [2.0, 0.0])            # past a: the end cap, parameter held at 0
    assert close(d.sd2Segment([1.0, -2.0], a, b), [2.0, 1.0])
    pts = RNG.uniform(-2, 2, (500, 2)).astype(F32)
    a2, b2 = np.array([-0.3, 0.8], F32), np.array([0.9, -0.4], F32)
    got = d.sd2Segment(pts, a2, b2)
    line = np.linspace(0, 1, 20001)[:, None] * (b2 - a2) + a2
    gap = pts[:, None, :].astype(np.float64) - line[None]
    assert np.max(np.abs(got[:, 0] - np.sqrt(np.min(np.sum(gap * gap, -1), 1)))) < 1e-4
    assert np.all((got[:, 1] >= 0) & (got[:, 1] <= 1))
    # a segment of zero length is its point: finite, parameter 0
    assert close(d.sd2Segment([3.0, 4.0], [0.0, 0.0], [0.0, 0.0]), [5.0, 0.0])


def test_hexagon_is_exact_pointy_top_with_the_given_inradius():
    d = twin("draw2")
    a = 0.6
    assert close(d.sd2Hexagon([a, 0.0], a), 0.0, 1e-6)                    # flat sides left and right
    assert close(d.sd2Hexagon([0.0, 2 * a / math.sqrt(3)], a), 0.0, 1e-6)  # a vertex straight up
    assert close(d.sd2Hexagon([0.0, 0.0], a), -a)
    pts = RNG.uniform(-1.3, 1.3, (800, 2))
    ref = _signed_reference(pts, _hexagon_outline(a))
    got = d.sd2Hexagon(pts.astype(F32), F32(a))
    assert np.max(np.abs(got - ref)) < 1e-3
    # twelve-fold symmetric: the same value after a turn of 60 degrees or a mirror in either axis
    turn = np.array([[0.5, -math.sqrt(3) / 2], [math.sqrt(3) / 2, 0.5]])
    assert close(d.sd2Hexagon((pts @ turn.T).astype(F32), F32(a)), got, 1e-5)
    assert close(d.sd2Hexagon((pts * [-1, 1]).astype(F32), F32(a)), got, 1e-6)


def test_every_exact_distance_has_unit_slope_away_from_its_skeleton():
    d = twin("draw2")
    pts = RNG.uniform(-1.5, 1.5, (400, 2)).astype(np.float64)
    h = 1e-3
    shapes = [lambda p: d.sd2Circle(p, 0.5), lambda p: d.sd2Box(p, [0.6, 0.3]),
              lambda p: d.sd2RoundBox(p, [0.6, 0.3], 0.2), lambda p: d.sd2Segment(p, [-0.5, 0.2], [0.4, -0.3])[..., 0],
              lambda p: d.sd2Hexagon(p, 0.5)]
    for f in shapes:
        gx = (f((pts + [h, 0]).astype(F32)) - f((pts - [h, 0]).astype(F32))) / (2 * h)
        gy = (f((pts + [0, h]).astype(F32)) - f((pts - [0, h]).astype(F32))) / (2 * h)
        slope = np.sqrt(gx * gx + gy * gy)
        # a distance never climbs faster than 1 (it would be an overestimate a marcher oversteps); off the skeleton
        # (where two nearest points tie, the slope drops) an exact one climbs at exactly 1
        assert np.all(slope < 1.01) and np.mean(np.abs(slope - 1) < 0.01) > 0.9


# ================================================================================================ draw2/aa.glsl
def _box_filtered(d_centre, px, inside_fn, n=4001):
    """The numerical box filter: the fraction of a one-pixel-wide window around d_centre where inside_fn(d) holds."""
    offs = (np.arange(n) + 0.5) / n - 0.5
    return np.mean(inside_fn(d_centre + offs * px))


def test_fill_is_the_box_filtered_coverage_of_a_straight_edge():
    a = twin("draw2")
    px = 0.01
    for dc in (-0.02, -0.004, 0.0, 0.0025, 0.006, 0.03):
        assert close(a.aaFill(dc, px), _box_filtered(dc, px, lambda d: d < 0), 1e-3), dc
    assert a.aaFill(0.0, px) == 0.5 and a.aaFill(-0.005, px) == 1.0 and a.aaFill(0.005, px) == 0.0
    assert a.aaFill(0.3, 0.0) == 0.0 and a.aaFill(-0.3, 0.0) == 1.0          # no pixel size: a hard edge, finite


def test_stroke_is_the_box_filtered_band_and_its_ink_is_the_true_width():
    a = twin("draw2")
    px = 0.01
    for hw in (0.0, 0.0012, 0.004, 0.005, 0.013):
        for dc in (-0.02, -0.006, -0.001, 0.0, 0.0031, 0.011):
            ref = _box_filtered(dc, px, lambda d: np.abs(d) <= hw)
            assert close(a.aaStroke(dc, hw, px), ref, 2e-3), (hw, dc)
        ds = np.linspace(-0.1, 0.1, 200001)
        ink = np.sum(a.aaStroke(ds.astype(F32), F32(hw), F32(px))) * (ds[1] - ds[0])
        assert close(ink, 2 * hw, 2e-5), hw                                  # energy: a thin line fades, never vanishes
    assert a.aaStroke(0.0, 0.0, px) == 0.0
    assert a.aaStroke(0.0, 0.02, px) == 1.0 and close(a.aaStroke(0.02, 0.02, px), 0.5)
    assert a.aaStroke(0.0, -0.1, px) == 0.0                                  # a negative width is no line, not ink


def test_wire_is_never_thinner_than_a_pixel_and_fades_by_true_over_drawn_width():
    a = twin("draw2")
    px = 0.01
    ds = np.linspace(-0.1, 0.1, 200001).astype(F32)
    step = 0.2 / 200000                                                      # in float64: the float32 grid's step
    one = np.asarray(a.aaWire(ds, F32(1.0), F32(px)))
    for w in (0.05, 0.25, 0.6, 1.0, 2.5):
        cov = np.asarray(a.aaWire(ds, F32(w), F32(px)))
        assert close(np.sum(cov, dtype=np.float64) * step, w * px, 2e-5), w  # the ink is the true width
        if w < 1:
            assert close(cov, w * one, 1e-6)                                 # the one-pixel wire, dimmed: connected
            assert close(cov.max(), w, 1e-6)
        else:
            assert close(cov, a.aaStroke(ds, F32(0.5 * w * px), F32(px)), 1e-6)
    assert np.max(np.asarray(a.aaWire(ds, F32(0.0), F32(px)))) == 0.0


def test_step_thresholds_a_field_over_its_own_footprint():
    a = twin("draw2")
    fp = 0.02                                                                # the field changes 0.02 per pixel
    assert a.aaStep(0.5, 0.5, fp) == 0.5
    assert a.aaStep(0.5 - fp, 0.5, fp) == 0.0 and a.aaStep(0.5 + fp, 0.5, fp) == 1.0
    xs = np.linspace(0.4, 0.6, 2001)
    ys = np.asarray(a.aaStep(xs.astype(F32), F32(0.5), F32(fp)), dtype=np.float64)
    assert np.all(np.diff(ys) >= 0) and close(ys + ys[::-1], 1.0, 1e-6)       # monotone, point-symmetric
    # a field with no slope at all is a clean hard step, never undefined
    assert a.aaStep(0.7, 0.5, 0.0) == 1.0 and a.aaStep(0.3, 0.5, 0.0) == 0.0 and a.aaStep(0.5, 0.5, 0.0) == 0.5


# ================================================================================================ draw2/domain2.glsl
def test_polar_round_trips_and_the_angle_lies_in_minus_pi_to_pi():
    d = twin("draw2")
    pts = RNG.uniform(-3, 3, (2000, 2)).astype(F32)
    ra = d.domToPolar(pts)
    assert np.all(ra[:, 1] > -math.pi) and np.all(ra[:, 1] <= np.float32(math.pi))
    assert close(d.domFromPolar(ra), pts, 2e-5)
    assert close(d.domToPolar([0.0, 2.0]), [2.0, math.pi / 2])
    assert close(d.domToPolar([-1.0, 0.0]), [1.0, math.pi]) and close(d.domToPolar([-1.0, -0.0]), [1.0, math.pi])
    assert close(d.domToPolar([0.0, 0.0]), [0.0, 0.0])                        # the origin: angle 0, never undefined


def test_repeat_centres_every_cell_and_returns_its_integer_id():
    d = twin("draw2")
    period = np.array([0.4, 0.25], F32)
    pts = RNG.uniform(-5, 5, (3000, 2)).astype(F32)
    cid, local = d.domRepeat2(pts, period)
    assert np.all(cid == np.round(cid))
    assert np.all(local >= -0.5 * period - 1e-6) and np.all(local < 0.5 * period + 1e-6)
    assert close(local + cid * period, pts, 1e-5)
    cid0, local0 = d.domRepeat2(np.array([0.21, -0.13], F32), period)
    assert close(cid0, [1.0, -1.0]) and close(local0, [0.21 - 0.4, -0.13 + 0.25], 1e-6)


def test_kaleido_folds_into_one_mirrored_half_sector_and_numbers_the_sectors():
    d = twin("draw2")
    n = 6
    width = 2 * math.pi / n
    pts = RNG.uniform(-2, 2, (3000, 2)).astype(F32)
    idx, folded = d.domKaleido(pts, F32(n))
    ang = np.arctan2(folded[:, 1], folded[:, 0])
    assert np.all(ang >= -1e-5) and np.all(ang <= width / 2 + 1e-5)
    assert close(np.hypot(folded[:, 0], folded[:, 1]), np.hypot(pts[:, 0], pts[:, 1]), 1e-5)
    assert np.all((idx >= 0) & (idx < n) & (idx == np.round(idx)))
    # turning the input by a whole sector moves it to the next sector and leaves the folded point where it was
    c, s = math.cos(width), math.sin(width)
    turned = (pts @ np.array([[c, -s], [s, c]]).T).astype(F32)
    idx2, folded2 = d.domKaleido(turned, F32(n))
    assert close(folded2, folded, 1e-4)
    assert np.mean((idx2 - idx) % n == 1) > 0.99
    # mirroring the input across a sector's centre line leaves the folded point the same: adjacent halves reflect
    mirrored = pts * np.array([1, -1], F32)
    assert close(d.domKaleido(mirrored, F32(n))[1], folded, 1e-4)
    # sectors are whole: 5.6 sectors is 6
    assert close(d.domKaleido(pts, F32(5.6))[1], folded, 1e-6)


# ================================================================================================ draw2/lattice.glsl
def _nearest_hex_centre(pts):
    cands = []
    for j in range(-12, 13):
        for i in range(-12, 13):
            cands.append((i + 0.5 * j, j * math.sqrt(3) / 2))
    cands = np.array(cands)
    gap = pts[:, None, :] - cands[None]
    dist = np.sum(gap * gap, -1)
    order = np.sort(dist, axis=1)
    return cands[np.argmin(dist, 1)], order[:, 1] - order[:, 0]


def test_lat_hex_finds_the_nearest_centre_of_the_pointy_top_lattice():
    lat = twin("draw2")
    pts = RNG.uniform(-6, 6, (3000, 2))
    h = lat.latHex(pts.astype(F32))
    ref, margin = _nearest_hex_centre(pts)
    clear = margin > 1e-4                                                   # away from exact ties on a border
    assert close(h[clear, 2:], ref[clear], 1e-5)
    assert close(h[:, :2] + h[:, 2:], pts, 1e-5)                            # offset + centre = the point
    assert np.all(np.hypot(h[:, 0], h[:, 1]) <= 1 / math.sqrt(3) + 1e-5)    # never farther than a vertex


def test_hex_edge_is_half_at_the_centre_zero_on_the_border_and_matches_the_hexagon():
    lat = twin("draw2")
    assert close(lat.latHexEdge([0.0, 0.0]), 0.5)
    assert close(lat.latHexEdge([0.5, 0.0]), 0.0, 1e-6) and close(lat.latHexEdge([0.0, 1 / math.sqrt(3)]), 0.0, 1e-6)
    pts = RNG.uniform(-6, 6, (3000, 2)).astype(F32)
    off = lat.latHex(pts)[:, :2]
    edge = lat.latHexEdge(off)
    assert np.all(edge >= -1e-5) and np.all(edge <= 0.5 + 1e-6)
    assert close(edge, -lat.sd2Hexagon(off, F32(0.5)), 1e-5)                # one hexagon, two doors


def test_hex_axial_coordinates_are_unique_integers_and_count_steps():
    lat = twin("draw2")
    pts = RNG.uniform(-8, 8, (4000, 2)).astype(F32)
    centres = lat.latHex(pts)[:, 2:]
    ax = lat.latHexAxial(centres)
    assert np.all(ax == np.round(ax))
    back = np.stack([ax[:, 0] + 0.5 * ax[:, 1], ax[:, 1] * math.sqrt(3) / 2], -1)
    assert close(back, centres, 1e-5)                                      # the axial pair names exactly one centre
    assert lat.latHexSteps([0.0, 0.0], [1.0, 0.0]) == 1 and lat.latHexSteps([0.0, 0.0], [1.0, -1.0]) == 1
    assert lat.latHexSteps([0.0, 0.0], [1.0, 1.0]) == 2 and lat.latHexSteps([2.0, -1.0], [-1.0, 3.0]) == 4
    # the six neighbours are one step away and sit one unit from the centre
    for dq, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)):
        assert lat.latHexSteps([0.0, 0.0], [dq, dr]) == 1
        assert close(math.hypot(dq + 0.5 * dr, dr * math.sqrt(3) / 2), 1.0)


# ================================================================================================ draw2/pattern.glsl
def test_cell_delay_is_the_cell_centres_distance_over_the_speed():
    pat = twin("draw2")
    assert close(pat.patCellDelay([3.0, 4.0], [0.0, 0.0], 2.0), 2.5)
    assert close(pat.patCellDelay([1.0, 1.0], [1.0, 1.0], 0.7), 0.0)
    # whole tiles fire together: every point of a hex cell shares its delay, and neighbouring cells differ
    pts = RNG.uniform(-4, 4, (3000, 2)).astype(F32)
    h = pat.latHex(pts)
    delay = pat.patCellDelay(h[:, 2:], np.zeros(2, F32), F32(1.5))
    for key in {tuple(c) for c in np.round(h[:, 2:], 4)[:50]}:
        same = np.all(np.isclose(np.round(h[:, 2:], 4), key), axis=1)
        assert np.ptp(delay[same]) == 0.0
    assert np.isfinite(pat.patCellDelay([1.0, 0.0], [0.0, 0.0], 0.0))       # a speed of zero: very late, never Inf


# ================================================================================================ noise/triangle.glsl
def _o_tri(x):
    return 1.0 - abs(2.0 * (x - math.floor(x)) - 1.0)


def _o_turn(v, a):
    c, s = math.cos(a), math.sin(a)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def o_noise_triangle2(px, py, t, octaves):
    """The contract of noiseTriangle2 written a second time, in plain float64 Python, from its header's words."""
    n = min(octaves, 8)
    if n < 1:
        return 0.5
    phi = (1 + math.sqrt(5)) / 2
    q = (px, py)
    w = _o_turn((0.43 * px, 0.43 * py), 1.1)
    total = amp_sum = 0.0
    amp = 1.0
    spin = 0.5 * t
    for _ in range(n):
        field = (_o_tri(w[0] + 0.5 * _o_tri(w[1])) - 0.5, _o_tri(w[1] + 0.5 * _o_tri(w[0])) - 0.5)
        f = _o_turn(field, spin)
        q = (q[0] + 1.2 * f[0], q[1] + 1.2 * f[1])
        total += amp * _o_tri(q[0] + 0.5 * _o_tri(q[1]))
        amp_sum += amp
        amp *= 0.5
        q = _o_turn(q, 1.0)
        q = (q[0] * phi + 0.31, q[1] * phi - 0.47)
        w = _o_turn(w, -1.0)
        w = (w[0] * 1.41 - 0.23, w[1] * 1.41 + 0.19)
        spin *= -1.37
    return total / amp_sum


def test_triangle_noise_matches_its_contract_written_twice():
    tn = twin("triangle")
    pts = RNG.uniform(-6, 6, (64, 2))
    for octaves in (1, 3, 4, 8):
        for t in (0.0, 1.7):
            got = tn.noiseTriangle2(pts.astype(F32), F32(t), octaves)
            ref = np.array([o_noise_triangle2(x, y, t, octaves) for x, y in pts])
            assert np.max(np.abs(got - ref)) < 2e-4, (octaves, t)


def test_triangle_noise_stays_in_zero_one_centred_on_a_half():
    tn = twin("triangle")
    pts = RNG.uniform(-40, 40, (100000, 2)).astype(F32)
    for octaves in (1, 4, 8):
        n = tn.noiseTriangle2(pts, F32(0.7), octaves)
        assert n.min() >= 0.0 and n.max() <= 1.0
        assert abs(float(n.mean()) - 0.5) < 0.01
    assert tn.noiseTriangle2(np.array([0.3, 0.2], F32), F32(1.0), 0) == 0.5   # no octaves: the mean, flat
    assert close(tn.noiseTriangle2(pts[:200], F32(0.4), 12), tn.noiseTriangle2(pts[:200], F32(0.4), 8))


def test_triangle_noise_filaments_are_thin_and_sit_on_no_lattice():
    tn = twin("triangle")
    pts = RNG.uniform(-40, 40, (100000, 2)).astype(F32)
    n = tn.noiseTriangle2(pts, F32(0.7), 4)
    low = float(np.mean(n < 0.12))
    assert 0.001 < low < 0.03, low                                       # the bright creases are a thin set
    for lag in ((1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, 0.0)):
        m = tn.noiseTriangle2(pts + np.array(lag, F32), F32(0.7), 4)
        assert abs(np.corrcoef(n, m)[0, 1]) < 0.2, lag                    # the triangle waves' period never shows


def test_triangle_noise_is_continuous_with_creases_not_jumps():
    tn = twin("triangle")
    for octaves in (1, 4, 8):
        widest = []
        for h in (1e-3, 2.5e-4):
            xs = np.arange(-5, 5, h)
            line = np.stack([xs, 0.37 + 0.2 * xs], -1).astype(F32)
            widest.append(float(np.max(np.abs(np.diff(tn.noiseTriangle2(line, F32(0.3), octaves))))))
        assert widest[1] < 0.35 * widest[0], (octaves, widest)          # a quarter of the step, a quarter the change
        assert widest[0] / 1e-3 < 40                                     # a bounded slope: honest for derivatives


def test_triangle_noise_churns_in_place_one_octave_turning_every_four_pi():
    tn = twin("triangle")
    pts = RNG.uniform(-5, 5, (2000, 2)).astype(F32)
    one = tn.noiseTriangle2(pts, F32(0.3), 1)
    assert close(tn.noiseTriangle2(pts, F32(0.3 + 4 * math.pi), 1), one, 2e-5)
    a, b = tn.noiseTriangle2(pts, F32(0.0), 4), tn.noiseTriangle2(pts, F32(2.0), 4)
    assert float(np.mean(np.abs(a - b))) > 0.1                            # it moves
    assert abs(float(a.std()) - float(b.std())) < 0.02 and abs(float(a.mean()) - float(b.mean())) < 0.03


# ================================================================================================ the modules
def _atlas():
    return json.loads(ATLAS.read_text(encoding="utf-8"))


def _parse_signature(text):
    """'vec2 domRepeat2(inout vec2 p, vec2 period)' -> ('domRepeat2', 'vec2', ['inout vec2', 'vec2'])."""
    m = re.fullmatch(r"\s*(\w+)\s+(\w+)\s*\(([^()]*)\)\s*", text)
    if not m:
        return None
    params = []
    for raw in m.group(3).split(","):
        words = [w for w in raw.split() if w not in ("in", "const", "highp")]
        if words:
            params.append(" ".join(words[:-1]))
    return m.group(2), m.group(1), params


def _atlas_signatures(file):
    out = {}
    for part in _atlas()["parts"]:
        if part.get("module") != file:
            continue
        for piece in part["signature"].split(" / "):
            parsed = _parse_signature(piece)
            if parsed:
                out.setdefault(parsed[0], []).append((parsed[1], parsed[2]))
    return out


@pytest.fixture(scope="module")
def library():
    return M.load_library(strict=False)


def _module(lib, file):
    name = FAMILY[file]
    assert name in lib.modules, f"no module named {name} (expected in arsenal/web/glsl/{file}); " \
                                f"quarantined: {[p for p in lib.problems if file in p['path'].replace(chr(92), '/')]}"
    m = lib.modules[name]
    assert Path(m.path).resolve() == (LIB / file).resolve(), f"{name} lives in {m.path}, not {file}"
    return m


def _definitions(m):
    out = {}
    for d in M.DEFINITION_RE.finditer(M.strip_comments(m.body)):
        params = []
        for raw in d.group(3).split(","):
            words = [w for w in raw.split() if w not in ("in", "const", "highp")]
            if words:
                params.append(" ".join(words[:-1]))
        out.setdefault(d.group(2), []).append((d.group(1), params))
    return out


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_every_planned_p0_function_is_built_and_nothing_unplanned(library, file):
    m = _module(library, file)
    manifest = [f for row in _atlas()["manifest"] if row["file"] == file for f in row["functions"]]
    assert manifest, f"the atlas plans no P0 functions in {file}"
    planned = {f for p in _atlas()["parts"] if p.get("module") == file for f in p["functions"]} | set(manifest)
    defined = set(m.functions) | set(m.consts) | set(m.structs)
    assert set(manifest) <= defined, f"{file} lacks the planned {sorted(set(manifest) - defined)}"
    assert defined <= planned, f"not in the atlas for {file}: {sorted(defined - planned)}"


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_signatures_are_exactly_the_atlas_signatures(library, file):
    m = _module(library, file)
    defs, planned = _definitions(m), _atlas_signatures(file)
    for fn in m.functions:
        assert fn in planned, f"{fn} has no atlas signature"
        assert sorted(defs[fn]) == sorted(planned[fn]), f"{fn}: {defs[fn]} != planned {planned[fn]}"


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_headers_carry_every_library_field(library, file):
    m = _module(library, file)
    h = m.header
    parts = [p for p in _atlas()["parts"] if p.get("module") == file]
    assert h["name"] == FAMILY[file] and h["kind"] == "helper"
    assert h["cat"] in {p["category"] for p in parts} and h["family"] == h["cat"][0]
    assert re.fullmatch(r"\d+\.\d+\.\d+", h["version"]) and 10 <= h["order"] <= 30
    assert h["license"] == "Apache-2.0"
    assert isinstance(h["credits"], list) and h["credits"] and all("http" in c for c in h["credits"]), \
        "credits name who taught the technique, each with a link"
    assert h["cost"]["class"] in ("C0", "C1") and h["cost"]["tex"] == 0 and h["cost"].get("loop")
    for key in ("contract", "note"):
        assert isinstance(h[key], str) and len(h[key]) > 80, key
    assert h["status"] == "P0" and h["targets"]["glsl"] == "300es"
    assert set(h["targets"]["needs"]) <= set(M.KNOWN_NEEDS)
    code = M.strip_comments(m.body)
    uses_derivatives = any(re.search(rf"\b{d}\b", code) for d in M.DERIVATIVES)
    assert uses_derivatives == ("derivatives" in h["targets"]["needs"]), "declare derivatives exactly when used"
    assert h["card"] == f"{m.name}.card" and (LIB / "cards" / h["card"]).is_file()
    twin_path = h["twin"].split(":")[0]
    assert twin_path.startswith("arsenal/shaders/twins/") and (REPO / twin_path).is_file()
    p0 = [p for p in parts if p["status"] == "P0"]
    assert sorted(h["exemplars"]) == sorted({e for p in p0 for e in p["exemplars"]})
    assert h["learn"] and set(h["learn"]) <= {x for p in parts for x in p["learn"]}


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_every_glsl_function_has_a_twin_of_the_same_name(library, file):
    m = _module(library, file)
    path = m.header["twin"].split(":")[0]
    mod = importlib.import_module(path[:-3].replace("/", "."))
    for name in m.functions:
        assert hasattr(mod, name), f"{path} has no twin for {name}"


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_each_module_composes_and_lints_clean(library, file):
    m = _module(library, file)
    for target in ("toy", "webgl2", "three-r186"):
        text = library.compose([m.name], target=target)
        assert m.name in text.splitlines()[0]
    assert M.lint(m, library_module=True, library=library) == []


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_each_module_has_a_card_that_builds(library, file):
    m = _module(library, file)
    card = K.load_card(m.name)
    assert m.name in card.uses and card.note
    built = K.build_card(card, library=library)
    assert m.name in built["card"]["modules"]


def test_no_module_reaches_for_the_old_sine_hash_or_redefines_a_batch_a_function(library):
    """Reuse, never re-declare: PI and TAU come from core-const, triangle waves from core-shaping, rotation from
    core-rotate; a second definition anywhere would refuse the whole library."""
    for file in FAMILY:
        m = _module(library, file)
        code = M.strip_comments(m.body)
        assert "hashSine" not in code and not re.search(r"\bsin\s*\(\s*dot", code)
        assert not re.search(r"\bconst\s+float\s+(PI|TAU|PHI|SQRT3)\b", code)
    assert "core-shaping" in library.resolve(["noise-triangle"]) and "core-rotate" in library.resolve(["noise-triangle"])
    assert "core-const" in library.resolve(["draw2-lattice"])


# ====================================================================================== the GPU against the twin
PARITY_CARD = """\
//! {"card": "parity-2d", "uses": ["noise-triangle", "draw2-sdf2", "draw2-aa", "draw2-domain2", "draw2-lattice",
//!  "draw2-pattern"], "t": [0], "size": [448, 64],
//!  "note": "Not a house card: the 2D family's parity pattern, compared pixel by pixel with the CPU twin."}
// Apache-2.0, Akashic Aurora. Written fresh for the parity test.
void mainImage(out vec4 color, in vec2 pixel) {
    vec2 at = floor(pixel);
    int panel = int(at.x) / 64;
    vec2 local = pixel - vec2(64.0 * float(panel), 0.0);   // pixel centres, 0.5 .. 63.5
    vec2 p = local / 32.0 - 1.0;                            // -1 .. 1
    vec3 v = vec3(0.0);
    if (panel == 0) {
        v = vec3(noiseTriangle2(p * 3.0, 1.3, 4), noiseTriangle2(p * 2.0, 0.0, 1),
                 noiseTriangle2(p * vec2(5.0, 0.5), 2.0, 3));
    } else if (panel == 1) {
        v = 0.5 + 0.5 * vec3(sd2Circle(p, 0.6), sd2RoundBox(p, vec2(0.7, 0.4), 0.2), sd2Hexagon(p, 0.55));
    } else if (panel == 2) {
        vec2 seg = sd2Segment(p, vec2(-0.6, 0.3), vec2(0.5, -0.4));
        v = vec3(0.5 + 0.5 * seg.x, seg.y, 0.5 + 0.5 * sd2Box(p, vec2(0.5, 0.3)));
    } else if (panel == 3) {
        vec4 hex = latHex(p * 2.5);
        v = vec3(hex.xy + 0.5, 2.0 * latHexEdge(hex.xy));
    } else if (panel == 4) {
        vec2 q = p;
        float sector = domKaleido(q, 5.0);
        vec2 ra = domToPolar(p);
        v = vec3(0.5 + 0.5 * q, (sector + 0.5) / 5.0);
        v.z = 0.5 * v.z + 0.5 * (ra.y / 6.2831853 + 0.5);
    } else if (panel == 5) {
        float d = (local.x - 32.0) * 0.01;
        float x = 0.013 * local.x + 0.007 * local.y;
        v = vec3(aaFill(d, 0.08), aaStroke(d, 0.05 * local.y / 64.0, 0.08), aaWire(d, 2.0 * local.y / 64.0, 0.08));
        v.x = 0.5 * v.x + 0.5 * aaStep(x, 0.6);
    } else {
        vec2 q = p * 2.0;
        vec2 cell = domRepeat2(q, vec2(0.5, 0.4));
        vec4 hex = latHex(p * 3.0);
        vec2 ax = latHexAxial(hex.zw);
        v = vec3(q / vec2(0.5, 0.4) + 0.5, patCellDelay(cell, vec2(0.0), 8.0));
        v.z = 0.5 * v.z + 0.5 * fract((ax.x + 3.0 * ax.y) / 7.0 + 0.01);
    }
    color = vec4(v, 1.0);
}
"""


def _twin_parity_image():
    d, tn = twin("draw2"), twin("triangle")
    ys, xs = np.mgrid[0:64, 0:64]
    local = np.stack([xs + 0.5, ys + 0.5], -1).astype(F32)
    p = local / F32(32.0) - F32(1.0)
    out = np.zeros((64, 448, 3))
    out[:, 0:64] = np.stack([tn.noiseTriangle2(p * F32(3.0), F32(1.3), 4), tn.noiseTriangle2(p * F32(2.0), F32(0.0), 1),
                             tn.noiseTriangle2(p * np.array([5.0, 0.5], F32), F32(2.0), 3)], -1)
    out[:, 64:128] = 0.5 + 0.5 * np.stack([d.sd2Circle(p, F32(0.6)), d.sd2RoundBox(p, np.array([0.7, 0.4], F32), F32(0.2)),
                                           d.sd2Hexagon(p, F32(0.55))], -1)
    seg = d.sd2Segment(p, np.array([-0.6, 0.3], F32), np.array([0.5, -0.4], F32))
    out[:, 128:192] = np.stack([0.5 + 0.5 * seg[..., 0], seg[..., 1], 0.5 + 0.5 * d.sd2Box(p, np.array([0.5, 0.3], F32))], -1)
    hex_ = d.latHex(p * F32(2.5))
    out[:, 192:256] = np.concatenate([hex_[..., :2] + 0.5, 2.0 * d.latHexEdge(hex_[..., :2])[..., None]], -1)
    sector, q = d.domKaleido(p, F32(5.0))
    ra = d.domToPolar(p)
    out[:, 256:320] = np.concatenate([0.5 + 0.5 * q, (0.5 * (sector + 0.5) / 5.0 + 0.5 * (ra[..., 1] / 6.2831853 + 0.5))[..., None]], -1)
    dd = (local[..., 0] - F32(32.0)) * F32(0.01)
    x = F32(0.013) * local[..., 0] + F32(0.007) * local[..., 1]
    fp = math.hypot(0.013, 0.007)
    out[:, 320:384] = np.stack([0.5 * d.aaFill(dd, F32(0.08)) + 0.5 * d.aaStep(x, F32(0.6), F32(fp)),
                                d.aaStroke(dd, F32(0.05) * local[..., 1] / F32(64.0), F32(0.08)),
                                d.aaWire(dd, F32(2.0) * local[..., 1] / F32(64.0), F32(0.08))], -1)
    cell, q = d.domRepeat2(p * F32(2.0), np.array([0.5, 0.4], F32))
    hexc = d.latHex(p * F32(3.0))
    ax = d.latHexAxial(hexc[..., 2:])
    tag = (ax[..., 0] + 3.0 * ax[..., 1]) / 7.0 + 0.01
    out[:, 384:448] = np.concatenate([q / np.array([0.5, 0.4], F32) + 0.5,
                                      (0.5 * d.patCellDelay(cell, np.zeros(2, F32), F32(8.0))
                                       + 0.5 * (tag - np.floor(tag)))[..., None]], -1)
    return np.round(np.clip(out, 0, 1) * 255.0)[::-1]           # PNG rows run top down


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (the headless driver)")
def test_the_glsl_matches_its_twin_on_swiftshader(tmp_path):
    from PIL import Image
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "parity-2d.card").write_text(PARITY_CARD, encoding="utf-8", newline="\n")
    report = K.render_cards(["parity-2d"], cards_dir=cards_dir, out_root=tmp_path / "out",
                            allow_tracked=True, lock_wait_min=5, quiet=True)
    if report["driver"].get("error") and "lock" in str(report["driver"]["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {report['driver']['error']}")
    row = report["cards"][0]
    assert row["compile_ok"] is True and row["nan_pixels"] == 0, row
    png = sorted((tmp_path / "out" / "parity-2d").glob("t0*.png"))[0]
    gpu = np.asarray(Image.open(png).convert("RGB")).astype(np.float64)
    cpu = _twin_parity_image()
    miss = np.abs(gpu - cpu)
    smooth = miss[:, 0:192]                                       # noise and distances: continuous everywhere
    assert smooth.max() <= 3 and np.mean(smooth > 1) < 0.002, f"noise/distance drift: max {smooth.max()}"
    # the lattice, the fold, the coverage and the repetition jump at borders: a pixel on an exact tie may land in the
    # other cell on the GPU, so a few such pixels may differ; everywhere else they agree
    jumpy = miss[:, 192:448]
    assert np.mean(jumpy > 2) < 0.01, f"lattice/domain/aa drift: {np.mean(jumpy > 2):.4f} of pixels"
