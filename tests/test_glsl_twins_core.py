"""Pins for the foundation family of the house GLSL library (atlas family A: core maths, integers, compile guards,
clocks, the 2D frame, shaping curves, debug views) and their CPU twins.

WHY. These modules are the screws and the power rails: every other module stands on them, so a wrong constant, a
modulo that breaks at zero or a decay that changes with the frame rate would show up everywhere at once. A GPU cannot
be asked for a number from a test, so each GLSL function has a CPU TWIN in arsenal/shaders/twins/ (numpy, float32, the
same name as the GLSL function) and these tests hold the twins to reference values: the mathematics' own fixed points
(gain fixes one half, the impulse peaks at exactly 1 at x = 1/k), Python's floor modulo for negative integers, and the
frame-rate independence the clock parts exist for (a decay at 60 Hz and at 240 Hz lands on the same value after one
second). Like a bench multimeter calibrated against a reference cell before it is trusted on a circuit.

The second half pins the modules themselves against the atlas (arsenal/shaders/atlas.json, the authoritative plan):
every planned P0 function of each file is defined, nothing unplanned is exported, the header carries the fields of
architecture section 3.2, the constants in the GLSL text equal the twin's, each module has a card that builds against
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

# file -> module name: this family's nine files (the slice's own list)
MODULES = {
    "core/const.glsl": "core-const",
    "core/safe.glsl": "core-safe",
    "core/rotate.glsl": "core-rotate",
    "core/int.glsl": "core-int",
    "core/compile.glsl": "core-compile",
    "core/clock.glsl": "core-clock",
    "core/frame.glsl": "core-frame",
    "core/shaping.glsl": "core-shaping",
    "debug/views.glsl": "debug-views",
}
F32 = np.float32


def twin(area: str):
    """The twin module, imported inside each test so a missing twin fails that test by name (not the whole file)."""
    return importlib.import_module(f"arsenal.shaders.twins.{area}")


def close(a, b, tol=1e-6):
    return np.allclose(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64), rtol=tol, atol=tol)


# ================================================================================================ the core twins
def test_constants_are_the_float32_roundings_of_the_mathematics():
    c = twin("core")
    assert c.PI == F32(math.pi) and c.TAU == F32(2 * math.pi)
    assert c.PHI == F32((1 + math.sqrt(5)) / 2) and c.SQRT3 == F32(math.sqrt(3))
    # the golden ratio's defining identities, to float32 precision
    assert close(c.PHI * c.PHI, c.PHI + 1) and close(1 / c.PHI, c.PHI - 1)
    for v in (c.PI, c.TAU, c.PHI, c.SQRT3):
        assert isinstance(v, np.float32)


def test_dot2_is_the_squared_length_in_2d_and_3d():
    c = twin("core")
    assert c.dot2([3.0, 4.0]) == 25.0
    assert c.dot2([1.0, 2.0, 2.0]) == 9.0


def test_safe_div_floors_the_denominator_keeping_its_sign_and_zero_counts_as_positive():
    c = twin("core")
    assert c.safeDiv(6.0, 3.0, 1e-3) == F32(2.0)
    assert close(c.safeDiv(1.0, 0.0, 1e-3), 1000.0, 1e-5)
    assert close(c.safeDiv(1.0, -1e-6, 1e-3), -1000.0, 1e-5)
    assert close(c.safeDiv(-2.0, 1e-9, 1e-3), -2000.0, 1e-5)
    xs = np.linspace(-1, 1, 2001, dtype=F32)
    assert np.all(np.isfinite(c.safeDiv(F32(1.0), xs, F32(1e-4))))


def test_safe_normalize_returns_the_fallback_at_and_near_zero_and_a_unit_vector_otherwise():
    c = twin("core")
    fb = [0.0, 1.0]
    assert close(c.safeNormalize([3.0, 4.0], fb), [0.6, 0.8])
    assert close(c.safeNormalize([0.0, 0.0], fb), fb)
    assert close(c.safeNormalize([1e-13, 0.0], fb), fb)            # dot = 1e-26 <= 1e-24: fallback
    assert close(c.safeNormalize([1e-11, 0.0], fb), [1.0, 0.0])    # dot = 1e-22 > 1e-24: normalised
    assert close(c.safeNormalize([0.0, 0.0, 0.0], [0.0, 0.0, 1.0]), [0.0, 0.0, 1.0])
    assert close(c.safeNormalize([2.0, 0.0, 0.0], [0.0, 0.0, 1.0]), [1.0, 0.0, 0.0])


def test_safe_sqrt_acos_pow_stay_defined_at_their_edges():
    c = twin("core")
    assert c.safeSqrt(-1e-7) == 0.0 and c.safeSqrt(4.0) == 2.0
    one_ulp_over = np.nextafter(F32(1.0), F32(2.0))
    assert c.safeAcos(one_ulp_over) == 0.0
    assert close(c.safeAcos(-one_ulp_over), math.pi)
    assert close(c.safePow(2.0, 10.0), 1024.0)
    assert c.safePow(0.0, 0.0) == 1.0                    # the floor makes 0^0 the limit, not undefined
    assert c.safePow(-2.0, 2.2) == 0.0                   # a negative base is floored at 1e-30: (1e-30)^2.2 is 0


def test_finite_or_replaces_exactly_the_non_finite_components():
    c = twin("core")
    v = np.array([np.nan, np.inf, -np.inf, 0.25], dtype=F32)
    fb = np.array([1.0, 2.0, 3.0, 4.0], dtype=F32)
    assert np.array_equal(c.finiteOr(v, fb), np.array([1.0, 2.0, 3.0, 0.25], dtype=F32))
    big = np.array([3.4e38, -3.4e38, 0.0, -0.0], dtype=F32)        # the largest finite values pass untouched
    assert np.array_equal(c.finiteOr(big, fb), big)


def test_rotate2_turns_counter_clockwise_exactly_and_composes():
    c = twin("core")
    assert close(c.rotate2(math.pi / 2) @ np.array([1.0, 0.0], dtype=F32), [0.0, 1.0])
    for a in (0.3, 1.7, -2.4):
        m = c.rotate2(a)
        assert close(m.T @ m, np.eye(2)) and close(np.linalg.det(m), 1.0)
        assert close(c.rotate2(a) @ c.rotate2(0.5), c.rotate2(a + 0.5), 1e-5)
    eight = np.eye(2, dtype=F32)
    for _ in range(8):
        eight = eight @ c.rotate2(c.TAU / 8)
    assert close(eight, np.eye(2), 1e-5)                 # eight eighths of a turn come home


def test_imod_floor_is_python_floor_modulo_for_every_sign():
    c = twin("core")
    for b in range(1, 8):
        for a in range(-50, 51):
            assert c.imodFloor(a, b) == a % b, (a, b)
    assert c.imodFloor(-2**31, 7) == (-2**31) % 7        # INT_MIN: no overflow on the way
    assert c.imodFloor(2**31 - 1, 10) == (2**31 - 1) % 10
    assert c.imodFloor(5, 0) == 0 and c.imodFloor(-5, -3) == 0     # b below 1 is read as 1
    assert list(c.imodFloor(np.array([-3, 4]), np.array([4, 3]))) == [1, 1]
    assert list(c.imodFloor(np.array([-1, -5]), 4)) == [3, 3]


def test_cell_index_floors_where_int_would_truncate():
    c = twin("core")
    assert c.cellIndex(-0.5) == -1 and c.cellIndex(0.5) == 0 and c.cellIndex(-1.0) == -1 and c.cellIndex(2.999) == 2
    xs = np.linspace(-10, 10, 4001, dtype=F32)
    assert np.array_equal(c.cellIndex(xs), np.floor(xs).astype(np.int32))


def test_unroll_barrier_equals_n_for_any_real_frame():
    c = twin("core")
    for n in (1, 12, 64):
        for frame in (0, 1, 999999):
            assert c.unrollBarrier(n, frame) == n


def test_clk_phase_is_the_fraction_of_cycles_in_zero_to_one():
    c = twin("core")
    assert close(c.clkPhase(1.25, 2.0), 0.5)
    assert close(c.clkPhase(0.0, 7.0), 0.0)
    ts = np.linspace(0, 100, 10001, dtype=F32)
    ph = c.clkPhase(ts, F32(3.3))
    assert np.all((ph >= 0) & (ph < 1))


def test_clk_keep_decays_the_same_per_second_at_any_frame_rate():
    c = twin("core")
    keep = 0.2
    for fps in (30, 60, 144, 240):
        per_frame = np.float64(c.clkKeep(keep, 1.0 / fps))
        assert close(per_frame ** fps, keep, 1e-5), fps        # one second of frames keeps exactly keep
    # Oscillo Donut's phosphor: 0.85 per frame tuned at 60 Hz is 0.85^60 per second; at 240 Hz that is 0.85^(1/4)
    assert close(c.clkKeep(0.85 ** 60, 1.0 / 240), 0.85 ** 0.25, 1e-5)
    assert c.clkKeep(0.3, 0.0) == 1.0 and c.clkKeep(0.3, -0.1) == 1.0     # no time: nothing has faded
    assert c.clkKeep(0.0, 1.0 / 60) == 0.0                               # keep nothing: gone after any time


def test_clk_alpha_gives_one_step_response_whatever_the_frame_rate():
    c = twin("core")
    tau = 0.2
    for fps in (30, 60, 240):
        a = np.float64(c.clkAlpha(1.0 / fps, tau))
        y = 0.0
        for _ in range(fps // 2):                       # half a second of frames chasing a target of 1
            y += a * (1.0 - y)
        assert close(y, 1 - math.exp(-0.5 / tau), 1e-5), fps
    assert c.clkAlpha(0.0, tau) == 0.0
    assert c.clkAlpha(1.0 / 60, 0.0) == 1.0              # a zero time constant snaps


def test_the_2d_frame_is_centred_aspect_true_and_y_up():
    c = twin("core")
    res = (320.0, 180.0)
    assert close(c.uvCentered([160.0, 90.0], res), [0.0, 0.0])
    assert close(c.uvCentered([160.0, 180.0], res), [0.0, 1.0])       # top edge
    assert close(c.uvCentered([160.0, 0.0], res), [0.0, -1.0])
    assert close(c.uvCentered([320.0, 90.0], res), [320.0 / 180.0, 0.0])
    assert close(c.uvPixel(res), 2.0 / 180.0)


def test_uv_footprint_of_the_unwarped_frame_is_exactly_uv_pixel():
    c = twin("core")
    h, w = 36, 64
    ys, xs = np.mgrid[0:h, 0:w].astype(F32) + F32(0.5)
    field = c.uvCentered(np.stack([xs, ys], -1), (w, h))              # (h, w, 2): the frame at every pixel centre
    assert close(c.uvFootprint(field), c.uvPixel((w, h)), 1e-5)
    assert close(c.uvFootprint(field * 3.0), 3.0 * c.uvPixel((w, h)), 1e-5)  # a zoomed domain: three times wider


# ================================================================================================ the shaping twins
def test_linstep_and_smoother_ramp_from_a_to_b_and_clamp():
    s = twin("shaping")
    for f in (s.shpLinstep, s.shpSmoother):
        assert f(0.25, 0.75, 0.25) == 0.0 and f(0.25, 0.75, 0.75) == 1.0 and close(f(0.25, 0.75, 0.5), 0.5)
        assert f(0.25, 0.75, -3.0) == 0.0 and f(0.25, 0.75, 9.0) == 1.0
    assert close(s.shpLinstep(0.0, 1.0, 0.3), 0.3)
    # the quintic is flat in slope AND curvature at both ends (C2): its first term near each end is 10 h^3, nothing
    # linear or square. (A finite-difference slope at h = 1e-3 measures float32 rounding, not the curve.)
    for h in (0.01, 0.05):
        cubic = 10 * h ** 3 - 15 * h ** 4 + 6 * h ** 5
        assert close(s.shpSmoother(0.0, 1.0, h), cubic, 1e-4)
        assert abs((1 - np.float64(s.shpSmoother(0.0, 1.0, 1 - h))) - cubic) < 1e-6
    xs = np.linspace(0, 1, 1001)
    ys = np.asarray(s.shpSmoother(0.0, 1.0, xs), dtype=np.float64)
    assert np.all(np.diff(ys) >= -1e-7)                                    # monotone


def test_impulse_peaks_at_exactly_one_at_x_equals_one_over_k():
    s = twin("shaping")
    for k in (1.0, 4.0, 12.0):
        assert close(s.shpImpulse(1.0 / k, k), 1.0)
        xs = np.linspace(0, 4.0 / k, 4001)
        assert np.max(s.shpImpulse(xs, k)) <= 1.0 + 1e-6
    assert s.shpImpulse(0.0, 4.0) == 0.0


def test_pulse_is_one_at_its_centre_and_exactly_zero_beyond_its_half_width():
    s = twin("shaping")
    assert s.shpPulse(0.5, 0.5, 0.2) == 1.0
    assert s.shpPulse(0.7, 0.5, 0.2) == 0.0 and s.shpPulse(0.95, 0.5, 0.2) == 0.0 and s.shpPulse(-3.0, 0.5, 0.2) == 0.0
    assert close(s.shpPulse(0.6, 0.5, 0.2), 0.5)                 # half way out is half height (cubic symmetry)


def test_gain_fixes_zero_one_half_and_one_and_is_point_symmetric():
    s = twin("shaping")
    for k in (0.25, 1.0, 3.0):
        assert s.shpGain(0.0, k) == 0.0 and close(s.shpGain(0.5, k), 0.5) and s.shpGain(1.0, k) == 1.0
        xs = np.linspace(0, 1, 101)
        assert close(s.shpGain(1 - xs, k), 1 - np.asarray(s.shpGain(xs, k)), 1e-6)
    xs = np.linspace(0, 1, 101)
    assert close(s.shpGain(xs, 1.0), xs)                           # k = 1 is the diagonal
    assert s.shpGain(0.25, 3.0) < 0.25 < s.shpGain(0.25, 0.25)     # k > 1 is an S, k < 1 an inverse S


def test_parabola_is_a_zero_one_zero_bump():
    s = twin("shaping")
    for k in (0.5, 1.0, 2.0):
        assert s.shpParabola(0.0, k) == 0.0 and s.shpParabola(1.0, k) == 0.0 and close(s.shpParabola(0.5, k), 1.0)
    # the squared parabola is the Welch window Oscillo Donut weights its beam with: (1 - 4 j^2)^2, j = x - 1/2
    xs = np.linspace(0, 1, 101)
    assert close(s.shpParabola(xs, 2.0), (1 - 4 * (xs - 0.5) ** 2) ** 2, 1e-5)


def test_soft_abs_rounds_the_crease_and_never_dips_below_abs():
    s = twin("shaping")
    k = 0.04
    assert close(s.shpSoftAbs(0.0, k), math.sqrt(k))
    xs = np.linspace(-2, 2, 801)
    ys = np.asarray(s.shpSoftAbs(xs, k), dtype=np.float64)
    assert np.all(ys >= np.abs(xs) - 1e-7) and np.all(ys - np.abs(xs) <= math.sqrt(k) + 1e-7)
    assert close(s.shpSoftAbs(-1.3, k), s.shpSoftAbs(1.3, k))


def test_tri_is_a_unit_triangle_wave_rising_from_zero():
    s = twin("shaping")
    assert s.shpTri(0.0) == 0.0 and s.shpTri(0.5) == 1.0 and close(s.shpTri(0.25), 0.5) and close(s.shpTri(0.75), 0.5)
    xs = np.linspace(-3, 3, 601)
    assert close(s.shpTri(xs + 1.0), s.shpTri(xs), 1e-5)            # period 1
    assert close(s.shpTri(-0.25), 0.5)


def test_remap_refits_a_to_c_and_b_to_d_without_clamping():
    s = twin("shaping")
    assert close(s.shpRemap(0.2, 0.2, 0.6, 1.0, 3.0), 1.0) and close(s.shpRemap(0.6, 0.2, 0.6, 1.0, 3.0), 3.0)
    assert close(s.shpRemap(1.0, 0.2, 0.6, 1.0, 3.0), 5.0)          # past b keeps going: unclamped


def test_inv_power_is_one_at_the_radius_and_finite_at_the_centre():
    s = twin("shaping")
    for k in (2.0, 10.0):
        assert close(s.shpInvPower(0.3, 0.3, k), 1.0, 1e-5)        # every k passes through (r, 1)
        assert close(s.shpInvPower(0.6, 0.3, k), 2.0 ** -k, 1e-5)
    # AURORA's density at its floor: (0.7 / 0.1)^10 is large, but the centre itself stays finite
    for d in (0.0, -1.0, 1e-38):
        v = s.shpInvPower(d, 0.7, 10.0)
        assert np.isfinite(v) and v == F32(2.0 ** 64)              # held at 2^64: room for sums of thousands
    assert close(s.shpInvPower(0.1, 0.7, 10.0), 7.0 ** 10, 1e-4)


# ================================================================================================ the debug twins
def _luma(rgb):
    return np.asarray(rgb, dtype=np.float64) @ np.array([0.2126, 0.7152, 0.0722])


def test_heat_ramp_runs_black_to_white_with_brightness_that_only_climbs():
    c = twin("core")
    assert close(c.dbgHeatRamp(0.0), [0, 0, 0]) and close(c.dbgHeatRamp(1.0), [1, 1, 1])
    ts = np.linspace(0, 1, 1025)
    lum = _luma(c.dbgHeatRamp(ts))
    assert np.all(np.diff(lum) > 0)
    assert close(c.dbgHeatRamp(-1.0), [0, 0, 0]) and close(c.dbgHeatRamp(7.0), [1, 1, 1])


def test_heat_count_is_magenta_over_budget():
    c = twin("core")
    assert close(c.dbgHeatCount(10.0, 20.0), c.dbgHeatRamp(0.5))
    assert close(c.dbgHeatCount(21.0, 20.0), [1, 0, 1])


def test_range_scope_names_each_kind_of_bad_value_by_colour():
    c = twin("core")
    nan, inf = np.float32("nan"), np.float32("inf")
    assert close(c.dbgRangeScope([0.2, nan, 0.1, 1.0]), [1, 0, 1])          # NaN: magenta
    assert close(c.dbgRangeScope([0.2, 0.3, -inf, 1.0]), [0, 1, 1])         # Inf: cyan
    assert close(c.dbgRangeScope([0.2, -0.01, 0.1, 1.0]), [0, 0, 1])        # negative: blue
    assert close(c.dbgRangeScope([0.2, 0.3, 1.5, 1.0]), [1, 0, 0])          # above 1: red
    g = c.dbgRangeScope([0.5, 0.5, 0.5, 1.0])                               # in range: grey
    assert abs(g[0] - g[1]) < 1e-7 and abs(g[1] - g[2]) < 1e-7
    assert close(c.dbgRangeScope([nan, inf, -1.0, 2.0]), [1, 0, 1])         # NaN outranks the rest


def test_dbg_nan_paints_any_non_finite_pixel_magenta_and_passes_the_rest():
    c = twin("core")
    assert close(c.dbgNaN([0.1, 0.2, 0.3]), [0.1, 0.2, 0.3])
    for bad in ([np.nan, 0, 0], [0, np.inf, 0], [0, 0, -np.inf]):
        assert close(c.dbgNaN(np.array(bad, dtype=F32)), [1, 0, 1])


def test_dbg_slice_draws_a_white_zero_line_and_separates_inside_from_outside():
    c = twin("core")
    px = 0.01
    assert close(c.dbgSlice(0.0, 0.25, px), [1, 1, 1])
    inside, outside = c.dbgSlice(-0.12, 0.25, px), c.dbgSlice(0.12, 0.25, px)
    assert inside[0] > inside[2] and outside[2] > outside[0]                # warm inside, cool outside
    on_line = c.dbgSlice(0.25, 0.25, px)
    assert _luma(on_line) > _luma(c.dbgSlice(0.37, 0.25, px))              # an iso-line is brighter than between


def test_dbg_cells_shows_local_coordinates_tints_ids_and_draws_borders():
    c = twin("core")
    period = np.array([1.0, 1.0])
    border = c.dbgCells(np.array([0.4999, 0.0]), np.array([0.0, 0.0]), period, 0.01)
    assert close(border, [1, 1, 1], 1e-3)
    a = c.dbgCells(np.array([0.0, 0.0]), np.array([0.0, 0.0]), period, 0.01)
    b = c.dbgCells(np.array([0.0, 0.0]), np.array([1.0, 0.0]), period, 0.01)
    assert np.max(np.abs(np.asarray(a) - np.asarray(b))) > 0.1               # neighbouring cells get different tints
    lo = c.dbgCells(np.array([-0.3, -0.3]), np.array([0.0, 0.0]), period, 0.01)
    hi = c.dbgCells(np.array([0.3, 0.3]), np.array([0.0, 0.0]), period, 0.01)
    assert hi[0] > lo[0] and hi[1] > lo[1]                                   # local x is red, local y is green


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
    h = _module(house, file).header
    assert h["name"] == MODULES[file] and h["kind"] in ("helper", "const")
    assert h["cat"] == _category(file) and h["family"] == "A"
    assert re.fullmatch(r"\d+\.\d+\.\d+", h["version"])
    assert h["license"] == "Apache-2.0" and isinstance(h["credits"], list)
    assert isinstance(h["cost"], dict) and h["cost"]["class"] in ("C0", "C1", "C2", "C3", "C4")
    for key in ("contract", "note"):
        assert isinstance(h[key], str) and len(h[key]) > 20, key
    assert h["targets"]["glsl"] == "300es" and set(h["targets"]["needs"]) <= set(M.KNOWN_NEEDS)
    assert h["card"] == f"{h['name']}.card" and h["status"] == "P0"
    assert isinstance(h.get("exemplars", []), list) and isinstance(h.get("learn", []), list)
    code = M.strip_comments(_module(house, file).body)
    uses_derivatives = any(re.search(rf"\b{d}\b", code) for d in M.DERIVATIVES)
    assert uses_derivatives == ("derivatives" in h["targets"]["needs"]), "declare derivatives exactly when used"


@pytest.mark.parametrize("file", sorted(MODULES))
def test_every_glsl_function_has_a_twin_of_the_same_name(house, file):
    m = _module(house, file)
    path, _, fn = m.header["twin"].partition(":")
    assert path.startswith("arsenal/shaders/twins/") and path.endswith(".py")
    mod = importlib.import_module(path[:-3].replace("/", "."))
    for name in (fn,) if fn else tuple(m.functions) + tuple(m.consts):
        assert hasattr(mod, name), f"{path} has no twin for {name}"


def test_the_glsl_constants_equal_the_twin_constants(house):
    c = twin("core")
    m = _module(house, "core/const.glsl")
    found = dict(re.findall(r"const\s+float\s+(\w+)\s*=\s*([0-9.eE+-]+)\s*;", M.strip_comments(m.body)))
    assert set(found) == {"PI", "TAU", "PHI", "SQRT3"}
    for name, text in found.items():
        assert F32(float(text)) == getattr(c, name), name


@pytest.mark.parametrize("file", sorted(MODULES))
def test_module_composes_for_webgl2_and_lints_clean(house, file):
    m = _module(house, file)
    text = house.compose([m.name], target="webgl2")
    assert f"--- {m.name} " in text
    assert M.lint(m, library=house) == []


@pytest.mark.parametrize("file", sorted(MODULES))
def test_module_has_a_card_that_builds_against_the_house_library(house, file):
    name = MODULES[file]
    card = K.load_card(name)
    assert name in card.uses and card.note
    shader = K.build_card(card, library=house)
    assert name in shader["card"]["modules"]
