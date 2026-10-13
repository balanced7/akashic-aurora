"""Pins for the colour family of the house GLSL library (shader school batch A, atlas family H): the CPU twins against
reference values, and the GLSL modules against their twins on SwiftShader.

WHAT IS PINNED, AND AGAINST WHAT.
  * Transfer (colour/transfer.glsl): the IEC 61966-2-1 sRGB curve at points computed to 40 digits from the standard's
    formula; the round trip under 1e-6; Rec. 709 luminance weights; the signed cube root.
  * Perception (colour/oklab.glsl): OKLCH of the sRGB primaries as CSS Color 4 and colorjs publish them; white at
    L = 1; the round trip under 1e-5 in gamut; the gamut clip never moves hue by more than 1e-4 turns; the cusp search
    is never beaten by a brute-force scan, including the sliver beside pure blue where OKLab hue doubles back.
  * Legacy HSV (legacy/hsv.glsl): the primaries and the round trip on the CPU; on the GPU, the module against the very
    text First Light pastes today (read from arsenal/web/shaders/first-light.frag at test time, never copied).
  * Tone (colour/tone.glsl, legacy/tone-superlinear.glsl): each curve at fixed points computed to 30 digits; the
    superlinear twin against the bench chunk's own statement on the GPU.
  * Palettes (colour/palette.glsl) and grading (colour/grade.glsl): defining properties (endpoints, constant lightness,
    luminance kept, fixed points).
  * The pitch palette: palPitchFifths three ways -- the GLSL module rendered on SwiftShader, the Python twin, and the
    piano page's own JavaScript (arsenal/web/piano.js, executed in node from the file as it stands, read-only) -- within
    1/255 per channel for all twelve pitch classes.

SLOW TESTS. The GPU half renders one probe card on SwiftShader under the house GPU lock (render.py's driver, one burst).
The probe writes every result's float32 bits into pixels (two pixels per channel, 16 bits each), so the comparison is
exact to the GPU's own arithmetic rather than to 8-bit colour. Deselect with  py -m pytest -m "not slow".
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from arsenal.shaders.twins import colour as C
from arsenal.shaders.twins import palette as P
from arsenal.shaders.twins import tone as T

REPO = Path(__file__).resolve().parents[1]
GLSL = REPO / "arsenal" / "web" / "glsl"
PIANO_JS = REPO / "arsenal" / "web" / "piano.js"
FIRST_LIGHT = REPO / "arsenal" / "web" / "shaders" / "first-light.frag"
SUPERLINEAR_CHUNK = REPO / "design" / "vfx-chunks" / "superlinear-highlight.glsl"
ONE_CODE = 1.0 / 255.0

MODULES = {   # module name -> file, as the atlas plans them
    "colour-transfer": "colour/transfer.glsl",
    "colour-oklab": "colour/oklab.glsl",
    "legacy-hsv": "legacy/hsv.glsl",
    "colour-palette": "colour/palette.glsl",
    "colour-tone": "colour/tone.glsl",
    "legacy-tone-superlinear": "legacy/tone-superlinear.glsl",
    "colour-grade": "colour/grade.glsl",
}


def close(a, b, tol):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.all(np.abs(a - b) <= tol))


def rng():
    return np.random.default_rng(20261013)


# ------------------------------------------------------------------------------------------------------ transfer (H1)
# IEC 61966-2-1 at points, computed to 40 digits with Python's decimal module from the standard's piecewise formula.
SRGB_ENCODE = [(0.0, 0.0), (0.0005, 0.00646), (0.0031308, 0.040449936), (0.01, 0.0998528227341283365671),
               (0.18, 0.4613561295004416498628), (0.5, 0.7353569830524494906166), (1.0, 1.0)]
SRGB_DECODE = [(0.0, 0.0), (0.02, 0.001547987616099071207430), (0.04045, 0.003130804953560371517028),
               (0.2, 0.03310476657088504597126), (0.5, 0.2140411404822324424031), (1.0, 1.0)]


@pytest.mark.parametrize("lin,enc", SRGB_ENCODE)
def test_srgb_encode_at_reference_points(lin, enc):
    assert close(C.srgbEncode([lin, lin, lin]), [enc] * 3, 1e-9)


@pytest.mark.parametrize("enc,lin", SRGB_DECODE)
def test_srgb_decode_at_reference_points(enc, lin):
    assert close(C.srgbDecode([enc, enc, enc]), [lin] * 3, 1e-9)


def test_srgb_round_trip_under_1e6_including_hdr():
    x = np.linspace(0.0, 4.0, 40001).reshape(-1, 1).repeat(3, axis=1)
    assert np.max(np.abs(C.srgbDecode(C.srgbEncode(x)) - x)) < 1e-6
    v = np.linspace(0.0, 1.0, 10001).reshape(-1, 1).repeat(3, axis=1)
    assert np.max(np.abs(C.srgbEncode(C.srgbDecode(v)) - v)) < 1e-6


def test_srgb_negative_light_is_black_never_nan():
    assert close(C.srgbEncode([-0.5, -1e-9, 0.0]), [0.0, 0.0, 0.0], 0.0)
    assert close(C.srgbDecode([-0.5, -1e-9, 0.0]), [0.0, 0.0, 0.0], 0.0)


def test_luminance_is_rec709_on_linear_values():
    assert math.isclose(C.luminance([1.0, 1.0, 1.0]), 1.0, abs_tol=1e-12)
    assert close([C.luminance([1, 0, 0]), C.luminance([0, 1, 0]), C.luminance([0, 0, 1])], [0.2126, 0.7152, 0.0722],
                 1e-12)


def test_cbrt_signed_keeps_the_sign():
    assert close(C.cbrtSigned([-8.0, 27.0, 0.0]), [-2.0, 3.0, 0.0], 1e-12)
    assert close(C.cbrtSigned([-1e-9, 1e-9, -0.125]), [-1e-3, 1e-3, -0.5], 1e-12)


# --------------------------------------------------------------------------------------------------- perception (H2)
# OKLCH of the sRGB primaries, as CSS Color 4 / colorjs publish them (L, C, hue in degrees).
OKLCH_PRIMARIES = {
    "red": ([1, 0, 0], (0.627955, 0.257683, 29.2339)),
    "green": ([0, 1, 0], (0.866440, 0.294827, 142.4953)),
    "blue": ([0, 0, 1], (0.452014, 0.313214, 264.0520)),
}


@pytest.mark.parametrize("name", sorted(OKLCH_PRIMARIES))
def test_oklch_of_the_primaries_matches_the_published_values(name):
    rgb, (L, Cc, hdeg) = OKLCH_PRIMARIES[name]
    lch = C.oklchFromOklab(C.oklabFromLinear(rgb))
    assert abs(lch[0] - L) < 1e-5 and abs(lch[1] - Cc) < 1e-5, lch
    assert abs(lch[2] * 360.0 - hdeg) < 1e-3, lch


def test_oklab_white_and_grey():
    assert close(C.oklabFromLinear([1, 1, 1]), [1.0, 0.0, 0.0], 1e-6)
    lab = C.oklabFromLinear([0.18, 0.18, 0.18])
    assert close(lab, [0.18 ** (1 / 3), 0.0, 0.0], 1e-6)   # a grey's lightness is the cube root of its luminance


def test_oklab_round_trip_under_1e5_in_gamut():
    x = rng().random((5000, 3))
    assert np.max(np.abs(C.linearFromOklab(C.oklabFromLinear(x)) - x)) < 1e-5


def test_oklch_polar_form_round_trips_and_uses_turns():
    lab = C.oklabFromLinear(rng().random((2000, 3)))
    lch = C.oklchFromOklab(lab)
    assert np.all((lch[..., 2] >= 0.0) & (lch[..., 2] < 1.0))
    assert np.max(np.abs(C.oklabFromOklch(lch) - lab)) < 1e-12
    assert C.oklchFromOklab([0.5, 0.0, 0.0])[2] == 0.0       # a grey's hue is defined as 0, never NaN


@pytest.mark.parametrize("h0,h1,d", [(0.9, 0.1, 0.2), (0.1, 0.9, -0.2), (0.25, 0.5, 0.25), (0.0, 0.5, -0.5),
                                     (0.3, 0.3, 0.0), (0.99, 0.01, 0.02)])
def test_hue_delta_is_the_signed_shortest_arc(h0, h1, d):
    got = C.hueDelta(h0, h1)
    assert -0.5 <= got < 0.5 and abs(got - d) < 1e-12


def test_in_gamut_with_tolerance():
    assert C.inGamut([0.0, 0.5, 1.0], 0.0)
    assert not C.inGamut([-1e-3, 0.5, 1.0], 0.0)
    assert C.inGamut([-1e-5, 0.5, 1.00001], 1e-4)
    assert not C.inGamut([0.2, 0.5, 1.01], 1e-4)


def test_mix_oklab_endpoints_and_scale():
    a, b = np.array([0.9, 0.1, 0.05]), np.array([0.05, 0.2, 0.8])
    # 1e-6, not 1e-9: Ottosson's published matrices carry 10 digits, so a trip through OKLab is good to ~1e-7
    assert close(C.mixOklab(a, b, 0.0), a, 1e-6) and close(C.mixOklab(a, b, 1.0), b, 1e-6)
    mid = C.oklabFromLinear(C.mixOklab(a, b, 0.5))[0]
    assert abs(mid - 0.5 * (C.oklabFromLinear(a)[0] + C.oklabFromLinear(b)[0])) < 1e-7
    assert close(C.mixOklab(4 * a, 4 * b, 0.3), 4 * C.mixOklab(a, b, 0.3), 1e-9)   # OKLab mixing commutes with gain


def test_mix_oklch_takes_the_short_arc_and_keeps_lightness():
    a = C.linearFromOklab(C.oklabFromOklch([0.7, 0.1, 0.95]))
    b = C.linearFromOklab(C.oklabFromOklch([0.7, 0.1, 0.05]))
    mid = C.oklchFromOklab(C.oklabFromLinear(C.mixOklch(a, b, 0.5)))
    assert abs(mid[0] - 0.7) < 1e-6 and abs(mid[1] - 0.1) < 1e-6
    assert abs(C.hueDelta(mid[2], 0.0)) < 1e-6                          # through red (hue 0), not round the wheel
    assert close(C.mixOklch(a, b, 0.0), a, 1e-6) and close(C.mixOklch(a, b, 1.0), b, 1e-6)


def test_mix_oklch_a_grey_end_takes_the_colours_hue():
    grey, teal = np.array([0.2, 0.2, 0.2]), C.linearFromOklab(C.oklabFromOklch([0.75, 0.1, 0.52]))
    for t in (0.25, 0.5, 0.75):
        h = C.oklchFromOklab(C.oklabFromLinear(C.mixOklch(grey, teal, t)))[2]
        assert abs(C.hueDelta(h, 0.52)) < 1e-4


def test_mix_oklch_is_safe_for_hdr_light():
    a, b = np.array([0.9, 0.3, 0.1]), np.array([0.1, 0.4, 0.9])
    assert close(C.mixOklch(6 * a, 6 * b, 0.4), 6 * C.mixOklch(a, b, 0.4), 1e-6)


def test_oklch_max_chroma_brackets_the_gamut_edge():
    for L, h in [(0.5, 0.1), (0.8, 0.4), (0.3, 0.73), (0.95, 0.31)]:
        c = C.oklchMaxChroma(L, h, 0.0)
        assert C.inGamut(C.linearFromOklab(C.oklabFromOklch([L, c, h])), 1e-6)
        assert not C.inGamut(C.linearFromOklab(C.oklabFromOklch([L, c + 1e-5, h])), 0.0)


@pytest.mark.parametrize("name", sorted(OKLCH_PRIMARIES))
def test_oklch_cusp_of_a_primary_is_the_primary(name):
    # At the primary's OWN hue, computed, not the published hue: the cusp jumps at pure blue's exact hue (264.05202
    # degrees). Just below it the most colourful colour is (0, 0.04, 1) at chroma 0.288, just above it blue itself at
    # 0.313, so the published 264.0520 (rounded down by 0.00002 degrees) lands on the other side of the jump.
    rgb, (L, Cc, _hdeg) = OKLCH_PRIMARIES[name]
    cusp = C.oklchCusp(C.oklchFromOklab(C.oklabFromLinear(rgb))[2])
    assert abs(cusp[0] - L) < 1e-5 and abs(cusp[1] - Cc) < 1e-5, cusp


def test_oklch_cusp_jumps_at_pure_blue():
    h_blue = C.oklchFromOklab(C.oklabFromLinear([0, 0, 1]))[2]
    assert abs(C.oklchCusp(h_blue - 1e-6)[1] - 0.2878) < 1e-3       # the far crossing on the cyan-to-blue edge
    assert abs(C.oklchCusp(h_blue + 1e-6)[1] - 0.3132) < 1e-3       # blue itself, then the blue-to-magenta edge


def test_oklch_cusp_is_never_beaten_by_a_scan_even_beside_blue():
    # Includes 264.05 to 264.19 degrees, where OKLab hue doubles back along the cyan-to-blue edge of the RGB cube and a
    # plain bisection lands on the wrong (less colourful) crossing.
    hues = list(np.linspace(0.0, 1.0, 73, endpoint=False)) + list(np.linspace(264.03, 264.21, 10) / 360.0)
    for h in hues:
        cusp = C.oklchCusp(h)
        scan = max(C.oklchMaxChroma(L, h, 0.0) for L in np.linspace(0.3, 0.99, 139))
        assert cusp[1] >= scan - 2e-4, (h * 360, cusp, scan)
        assert C.inGamut(C.linearFromOklab(C.oklabFromOklch([cusp[0], cusp[1], h])), 1e-5)


def test_oklch_clip_keeps_hue_and_lightness_and_lands_in_gamut():
    r = rng()
    lch = np.stack([r.uniform(0.05, 0.95, 3000), r.uniform(0.0, 0.5, 3000), r.random(3000)], axis=-1)
    for row in lch:
        lin = C.oklchClip(row)
        assert np.all(lin >= 0.0) and np.all(lin <= 1.0)
        back = C.oklchFromOklab(C.oklabFromLinear(lin))
        assert abs(back[0] - row[0]) < 1e-5
        assert back[1] <= row[1] + 1e-6
        if back[1] > 1e-3:
            assert abs(C.hueDelta(back[2], row[2])) <= 1e-4


def test_oklch_clip_leaves_an_in_gamut_colour_alone():
    lin = np.array([0.6, 0.3, 0.2])
    assert close(C.oklchClip(C.oklchFromOklab(C.oklabFromLinear(lin))), lin, 1e-6)


def test_hue_rotate_oklch():
    lin = np.array([0.5, 0.3, 0.2])
    assert close(C.hueRotateOklch(lin, 0.0), lin, 1e-6)
    assert close(C.hueRotateOklch(lin, 1.0), lin, 1e-6)
    before = C.oklchFromOklab(C.oklabFromLinear(lin))
    after = C.oklchFromOklab(C.oklabFromLinear(C.hueRotateOklch(lin, 0.25)))
    assert abs(after[0] - before[0]) < 1e-6 and abs(after[1] - before[1]) < 1e-6   # this rotation stays in gamut
    assert abs(C.hueDelta(before[2], after[2]) - 0.25) < 1e-6
    assert close(C.hueRotateOklch(5 * lin, 0.3), 5 * C.hueRotateOklch(lin, 0.3), 1e-6)   # HDR keeps its level


# ------------------------------------------------------------------------------------------------- legacy HSV (H3)
def test_hsv_primaries_and_value():
    assert close(C.hsvToRgb([0.0, 1.0, 1.0]), [1, 0, 0], 1e-7)
    assert close(C.hsvToRgb([1 / 3, 1.0, 1.0]), [0, 1, 0], 1e-7)
    assert close(C.hsvToRgb([2 / 3, 1.0, 1.0]), [0, 0, 1], 1e-7)
    assert close(C.hsvToRgb([0.5, 0.0, 0.4]), [0.4, 0.4, 0.4], 1e-12)       # no saturation is grey at V
    assert close(C.rgbToHsv([0.2, 0.6, 0.4]), [5 / 12, 2 / 3, 0.6], 1e-9)


def test_hsv_round_trip_and_grey_hue():
    x = rng().random((3000, 3)) * 0.98 + 0.01
    assert np.max(np.abs(C.hsvToRgb(C.rgbToHsv(x)) - x)) < 1e-6
    assert C.rgbToHsv([0.3, 0.3, 0.3])[0] == 0.0


# ------------------------------------------------------------------------------------------------------- tone (H5)
# 30-digit references (mpmath) from each curve's published formula.
TONE_POINTS = {
    "tmTanh": [(0.18, 0.178080868117330199761), (1.0, 0.761594155955764888119), (4.0, 0.999329299739067043792)],
    "tmExp": [(0.18, 0.164729788588727978688), (1.0, 0.632120558828557678404), (4.0, 0.981684361111265819706)],
    "tmReinhard": [(0.18, 0.152542372881355932203), (1.0, 0.5), (4.0, 0.8)],
    "tmAcesFit": [(0.18, 0.140119567263307908111), (1.0, 0.673290473407364114553), (4.0, 0.934211203127411141402)],
    "tmPbrNeutral": [(0.18, 0.14), (1.0, 0.869090909090909090909)],
}


@pytest.mark.parametrize("fn,x,y", [(f, x, y) for f, pts in TONE_POINTS.items() for x, y in pts])
def test_tone_curves_at_fixed_points(fn, x, y):
    assert close(getattr(T, fn)([x, x, x]), [y] * 3, 1e-9)


def test_tm_pbr_neutral_on_colour():
    assert close(T.tmPbrNeutral([4.0, 2.0, 0.4]), [0.983255813953488372, 0.639951387047775293, 0.365307845523204829],
                 1e-9)
    assert close(T.tmPbrNeutral([0.05, 0.5, 0.3]), [0.015625, 0.465625, 0.265625], 1e-12)   # below the knee: toe only
    assert close(T.tmPbrNeutral([0.5, 0.3, 0.2]), [0.46, 0.26, 0.16], 1e-12)


def test_tone_curves_stay_finite_for_huge_and_negative_light():
    for fn in ("tmTanh", "tmExp", "tmReinhard", "tmAcesFit", "tmPbrNeutral"):
        y = getattr(T, fn)([1e6, 0.0, 1e30])
        assert np.all(np.isfinite(y)) and np.all(y <= 1.0 + 1e-12), (fn, y)
    for fn in ("tmTanh", "tmExp", "tmReinhard", "tmAcesFit"):
        assert close(getattr(T, fn)([-1.0, -1e-6, 0.0]), [0.0, 0.0, 0.0], 0.0), fn


def test_expose_root_gain_and_superlinear():
    assert close(T.expose([0.18, 0.5, 1.0], 1.0), [0.36, 1.0, 2.0], 1e-12)
    assert close(T.expose([0.18, 0.5, 1.0], -2.0), [0.045, 0.125, 0.25], 1e-12)
    assert close(T.tmRootGain([0.25, 1.0, 0.0], 0.5), [0.25, 0.5, 0.0], 1e-12)
    assert close(T.tmSuperlinear([1.0, 0.5, 0.0], 0.85), [1.85, 0.7125, 0.0], 1e-12)


def test_display_hue_safe_gamma_bends_magnitude_only():
    c = np.array([0.02, 0.01, 0.005])
    out = T.displayHueSafeGamma(c, 2.2)
    assert close(out / np.linalg.norm(out), c / np.linalg.norm(c), 1e-12)         # same direction: same hue
    assert abs(np.linalg.norm(out) - np.linalg.norm(c) ** (1 / 2.2)) < 1e-12
    assert close(T.displayHueSafeGamma([0.0, 0.0, 0.0], 2.2), [0.0, 0.0, 0.0], 0.0)


# ---------------------------------------------------------------------------------------------------- grading (H6)
def test_grd_saturation_keeps_luminance_and_zero_is_true_grey():
    c = np.array([0.8, 0.2, 0.05])
    y = C.luminance(c)
    assert close(C.grdSaturation(c, 0.0), [y, y, y], 1e-12)
    for s in (0.0, 0.5, 1.0, 2.0):
        assert abs(C.luminance(C.grdSaturation(c, s)) - y) < 1e-12
    assert close(C.grdSaturation(c, 1.0), c, 1e-12)


def test_grd_away_from_extrapolates_and_never_goes_negative():
    c, grey = np.array([0.6, 0.4, 0.3]), np.array([0.5, 0.5, 0.5])
    assert close(C.grdAwayFrom(c, grey, 0.0), c, 1e-12)
    assert close(C.grdAwayFrom(c, grey, 1.0), [0.7, 0.3, 0.1], 1e-12)
    assert close(C.grdAwayFrom(c, grey, 3.0), [0.9, 0.1, 0.0], 1e-12)                # 0.3 + 3(-0.2) is clamped at 0


def test_grd_s_curve_disp():
    x = np.array([0.0, 0.25, 0.5])
    assert close(C.grdSCurveDisp(x, 0.0), x, 0.0)
    assert close(C.grdSCurveDisp(x, 1.0), [0.0, 0.15625, 0.5], 1e-12)
    assert close(C.grdSCurveDisp(x, 0.5), [0.0, 0.203125, 0.5], 1e-12)


# --------------------------------------------------------------------------------------------------- palettes (H4)
RAINBOW = ([0.5] * 3, [0.5] * 3, [1.0] * 3, [0.0, 1 / 3, 2 / 3])


def test_pal_cos_reference_points_and_loop():
    a, b, c, d = RAINBOW
    assert close(P.palCos(0.0, a, b, c, d), [1.0, 0.25, 0.25], 1e-12)
    assert close(P.palCos(0.5, a, b, c, d), [0.0, 0.75, 0.75], 1e-12)
    assert close(P.palCos(1.0, a, b, c, d), P.palCos(0.0, a, b, c, d), 1e-12)    # whole-number c loops seamlessly


def test_pal_cos_linear_is_the_same_palette_decoded():
    a, b, c, d = RAINBOW
    for t in np.linspace(0, 1, 11):
        assert close(P.palCosLinear(t, a, b, c, d), C.srgbDecode(P.palCos(t, a, b, c, d)), 1e-12)


def test_pal_oklch_holds_lightness_and_sweeps_hue():
    for t in np.linspace(0.0, 1.0, 25):
        lch = C.oklchFromOklab(C.oklabFromLinear(P.palOklch(t, 0.72, 0.1, 0.1, 1.0)))
        assert abs(lch[0] - 0.72) < 1e-5 and abs(lch[1] - 0.1) < 1e-5
        assert abs(C.hueDelta(lch[2], 0.1 + t)) < 1e-5


def test_pal_ramp3_passes_through_its_stops():
    a, b, c = np.array([0.0, 0.42, 0.69]), np.array([0.01, 0.12, 1.0]), np.array([0.08, 0.03, 0.83])
    assert close(P.palRamp3(0.0, a, b, c), a, 1e-6)
    assert close(P.palRamp3(0.5, a, b, c), b, 1e-6)
    assert close(P.palRamp3(1.0, a, b, c), c, 1e-6)
    assert close(P.palRamp3(-1.0, a, b, c), a, 1e-6) and close(P.palRamp3(2.0, a, b, c), c, 1e-6)
    assert close(P.palRamp3(0.25, a, b, c), C.mixOklab(a, b, 0.5), 1e-9)


def test_pal_heat_powers():
    assert close(P.palHeatPowers(0.5, [1.0, 2.0, 4.0]), [0.5, 0.25, 0.0625], 1e-12)
    assert close(P.palHeatPowers(1.0, [1.0, 2.0, 4.0]), [1.0, 1.0, 1.0], 1e-12)
    assert close(P.palHeatPowers(-1.0, [1.0, 2.0, 4.0]), [0.0, 0.0, 0.0], 1e-12)


def test_pitch_palette_walks_the_circle_of_fifths_from_200_degrees():
    pp = P.palPitchPiano()
    # C is 200 degrees; each fifth adds 30; G (7) is one fifth up, D (2) two, F (5) one down.
    for pc, deg in [(0, 200), (7, 230), (2, 260), (5, 170), (6, 20)]:
        lch = C.oklchFromOklab(C.oklabFromLinear(P.palPitchFifths(pc, 4.0, pp)))
        assert abs(C.hueDelta(lch[2], deg / 360.0)) < 1e-4, (pc, lch[2] * 360)


def test_pitch_palette_luma_target_is_the_geometric_mean_it_claims():
    pp = P.palPitchPiano()
    assert abs(pp.lumaTarget - P.palPitchLumaMean(pp)) < 1e-9


def test_pitch_palette_ignores_octave_like_the_piano_and_rounds_the_pitch():
    pp = P.palPitchPiano()
    assert close(P.palPitchFifths(3.0, 1.0, pp), P.palPitchFifths(3.0, 7.0, pp), 0.0)
    assert close(P.palPitchFifths(15.2, 4.0, pp), P.palPitchFifths(3.0, 4.0, pp), 0.0)


# --------------------------------------------------------------------------- the piano's own palette (node, read-only)
# Runs the colour section of arsenal/web/piano.js as it stands (between its "colour" and "framing" banners), with
# stand-ins only for what the section touches outside itself: THREE.Color (a holder), Theory.mod, and storage.
PIANO_HARNESS = r"""
import { readFileSync } from "node:fs";
import vm from "node:vm";
const src = readFileSync(process.argv[2], "utf8");
const take = (re, what) => { const m = src.match(re); if (!m) throw new Error("piano.js: cannot find " + what); return m; };
const start = take(/^\/\/ -+ colour --$/m, "the colour banner").index;
const end = take(/^\/\/ -+ framing --$/m, "the framing banner").index;
const helpers = take(/^const clamp = .*$/m, "clamp")[0] + "\n" + take(/^const lerp = .*$/m, "lerp")[0] + "\n";
const sandbox = {
  Math, Map, JSON, Number, Array,
  THREE: { Color: class { setRGB(r, g, b) { this.r = r; this.g = g; this.b = b; return this; } } },
  Theory: { mod: (a, n) => ((a % n) + n) % n },
  safeGet: () => null,
};
const tail = `
;(() => {
  const rgb = [], lch = [];
  for (let p = 0; p < 12; p++) { const c = noteColor(60 + p, 100); rgb.push([c.r, c.g, c.b]); lch.push(noteLch(60 + p, 100)); }
  return JSON.stringify({ mode: COLOUR.mode, rgb, lch, lumaMean: pitchLumaMean });
})()`;
process.stdout.write(vm.runInNewContext(helpers + src.slice(start, end) + tail, sandbox));
"""


@pytest.fixture(scope="module")
def piano_palette(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node is not on PATH (needed to run the piano's own palette)")
    script = tmp_path_factory.mktemp("piano") / "piano_palette.mjs"
    script.write_text(PIANO_HARNESS, encoding="utf-8")
    run = subprocess.run(["node", str(script), str(PIANO_JS)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    out = json.loads(run.stdout)
    assert out["mode"] == "pitch"
    return out


def test_python_twin_matches_the_pianos_own_palette_within_one_code(piano_palette):
    pp = P.palPitchPiano()
    assert abs(pp.lumaTarget - piano_palette["lumaMean"]) < 1e-6
    for pc in range(12):
        twin = P.palPitchFifths(float(pc), 4.0, pp)
        js = np.array(piano_palette["rgb"][pc])
        assert close(twin, js, ONE_CODE), (pc, twin, js)
        shown = lambda v: C.srgbEncode(T.tmPbrNeutral(v))      # noqa: E731  what the piano's canvas shows
        assert close(shown(twin), shown(js), ONE_CODE), pc


# ------------------------------------------------------------------------------------------- module files and cards
@pytest.mark.parametrize("name", sorted(MODULES))
def test_each_module_exists_with_its_header_and_its_card(name):
    path = GLSL / MODULES[name]
    assert path.is_file(), path
    head = " ".join(line[3:] for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("//!"))
    header = json.loads(head)
    assert header["name"] == name and header["family"] == "H" and header["license"] == "Apache-2.0"
    for field in ("kind", "cat", "version", "credits", "cost", "contract", "note", "targets", "card", "twin", "status"):
        assert field in header, (name, field)
    assert (GLSL / "cards" / header["card"]).is_file(), header["card"]


# ======================================================================================== the GPU half (slow, locked)
# Each group: a GLSL call on per-case inputs, and the twin that should agree. Inputs are const arrays in the probe, so
# each library function has ONE call site however many cases it has (a long chain of inlined calls compiles slowly).
V3_UNIT = [(0.0, 0.0031308, 0.18), (0.5, 1.0, 0.0005), (0.01, 0.25, 0.75), (2.0, 4.0, -0.25)]
V3_ENC = [(0.0, 0.04045, 0.2), (0.5, 1.0, 0.02), (0.7353569830524495, 0.9, 0.1)]
V3_COLOURS = [(0.8, 0.2, 0.05), (0.05, 0.4, 0.9), (0.3, 0.3, 0.3), (1.0, 1.0, 0.0), (0.02, 0.6, 0.15),
              (0.6, 0.05, 0.7)]
V3_HDR = [(0.18, 0.18, 0.18), (1.0, 1.0, 1.0), (4.0, 2.0, 0.4), (0.05, 0.5, 0.3), (12.0, 0.5, 0.02),
          (0.0, 0.0, 0.0)]
V3_LCH = [(0.7, 0.4, 0.1), (0.5, 0.3, 0.73), (0.9, 0.25, 0.31), (0.3, 0.05, 0.6), (0.62, 0.0, 0.5)]
F_T = [0.0, 0.2, 0.5, 0.85, 1.0]
# HSV cases that put every channel on its sloped ramp somewhere (a hue where all three clamp proves nothing: the
# 2026-10-13 drill rewrote the hue offset and a clamped-only set stayed bit-identical).
V3_HSV = [(0.0, 1.0, 1.0), (0.05, 0.9, 0.8), (0.123, 0.8, 0.6), (0.2, 0.7, 0.9), (0.3, 1.0, 0.5), (0.4, 0.5, 0.8),
          (0.45, 0.65, 0.75), (0.55, 0.85, 0.6), (0.62, 0.3, 0.95), (0.7, 0.6, 1.0), (0.777, 0.4, 0.9),
          (0.8, 0.9, 0.7), (0.9, 0.55, 0.45), (0.95, 0.2, 0.3), (0.5, 0.0, 0.4)]
V3_GLOW = [(0.18, 0.18, 0.18), (1.0, 2.0, 4.0), (0.123, 0.456, 0.789), (1.234, 2.345, 3.456), (0.0456, 0.0789, 0.0123),
           (0.333, 0.666, 0.999), (5.55, 7.77, 9.99), (0.271, 0.314, 0.161)]
V3_RGB_FOR_HSV = V3_COLOURS + [(0.9, 0.35, 0.1), (0.1, 0.35, 0.9), (0.35, 0.9, 0.1), (0.123, 0.456, 0.789),
                               (0.789, 0.123, 0.456), (0.456, 0.789, 0.123), (0.3, 0.3, 0.31)]


def _lin(v):
    return np.asarray(v, dtype=float)


def _groups():
    """(label, glsl expression over a/b/t, {arg: (type, values)}, twin(a, b, t) -> 3 floats). One case per row."""
    a3 = lambda vals: ("vec3", vals)                       # noqa: E731
    f1 = lambda vals: ("float", vals)                      # noqa: E731
    pp = P.palPitchPiano()
    rainbow = "vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.0, 0.33333334, 0.6666667)"
    rb = ([0.5] * 3, [0.5] * 3, [1.0] * 3, [0.0, 0.33333334, 0.6666667])
    ember = (_lin([0.0, 0.42, 0.69]), _lin([0.01, 0.12, 1.0]), _lin([0.08, 0.03, 0.83]))
    groups = [
        ("srgbEncode", "srgbEncode(a)", {"a": a3(V3_UNIT)}, lambda a, b, t: C.srgbEncode(a)),
        ("srgbDecode", "srgbDecode(a)", {"a": a3(V3_ENC)}, lambda a, b, t: C.srgbDecode(a)),
        ("luminance", "vec3(luminance(a), 0.0, 0.0)", {"a": a3(V3_COLOURS)},
         lambda a, b, t: [C.luminance(a), 0.0, 0.0]),
        ("cbrtSigned", "cbrtSigned(a)", {"a": a3([(-8.0, 27.0, 0.0), (0.001, -0.125, 0.5)])},
         lambda a, b, t: C.cbrtSigned(a)),
        ("oklabFromLinear", "oklabFromLinear(a)", {"a": a3(V3_COLOURS)}, lambda a, b, t: C.oklabFromLinear(a)),
        ("linearFromOklab", "linearFromOklab(a)", {"a": a3([(0.7, 0.1, -0.05), (0.45, -0.03, -0.3), (1.0, 0.0, 0.0)])},
         lambda a, b, t: C.linearFromOklab(a)),
        ("oklchFromOklab", "oklchFromOklab(a)", {"a": a3([(0.7, 0.1, -0.05), (0.45, -0.03, -0.3), (0.5, 0.0, 0.0)])},
         lambda a, b, t: C.oklchFromOklab(a)),
        ("oklabFromOklch", "oklabFromOklch(a)", {"a": a3(V3_LCH)}, lambda a, b, t: C.oklabFromOklch(a)),
        ("mixOklab", "mixOklab(a, b, t)", {"a": a3(V3_COLOURS[:5]), "b": a3(V3_COLOURS[1:6]), "t": f1(F_T)},
         lambda a, b, t: C.mixOklab(a, b, t)),
        ("mixOklch", "mixOklch(a, b, t)", {"a": a3(V3_COLOURS[:5]), "b": a3(V3_COLOURS[1:6]), "t": f1(F_T)},
         lambda a, b, t: C.mixOklch(a, b, t)),
        ("hueDelta", "vec3(hueDelta(a.x, a.y), 0.0, 0.0)", {"a": a3([(0.9, 0.1, 0), (0.1, 0.9, 0), (0.0, 0.5, 0)])},
         lambda a, b, t: [C.hueDelta(a[0], a[1]), 0.0, 0.0]),
        ("inGamut", "vec3(inGamut(a, t) ? 1.0 : 0.0, 0.0, 0.0)",
         {"a": a3([(0.0, 0.5, 1.0), (-1e-3, 0.5, 1.0), (-1e-5, 0.5, 1.00001)]), "t": f1([0.0, 0.0, 1e-4])},
         lambda a, b, t: [1.0 if C.inGamut(a, t) else 0.0, 0.0, 0.0]),
        ("oklchClip", "oklchClip(a)", {"a": a3(V3_LCH)}, lambda a, b, t: C.oklchClip(a)),
        ("hueRotateOklch", "hueRotateOklch(a, t)", {"a": a3(V3_COLOURS[:5]), "t": f1([0.0, 0.25, 0.5, 0.8, 1.0])},
         lambda a, b, t: C.hueRotateOklch(a, t)),
        ("oklchMaxChroma", "vec3(oklchMaxChroma(a.x, a.y, a.z), 0.0, 0.0)",
         {"a": a3([(0.5, 0.1, 0.0), (0.8, 0.4, 1e-4), (0.3, 0.73, 0.0)])},
         lambda a, b, t: [C.oklchMaxChroma(a[0], a[1], a[2]), 0.0, 0.0]),
        ("oklchCusp", "vec3(oklchCusp(t), 0.0)", {"t": f1([0.0812, 0.3958, 0.7334, 0.7337, 0.55, 0.95])},
         lambda a, b, t: [*C.oklchCusp(t), 0.0]),
        ("hsvToRgb", "hsvToRgb(a)", {"a": a3(V3_HSV)}, lambda a, b, t: C.hsvToRgb(a)),
        ("rgbToHsv", "rgbToHsv(a)", {"a": a3(V3_RGB_FOR_HSV)}, lambda a, b, t: C.rgbToHsv(a)),
        ("house hsv2rgb", "probeHouseHsv2rgb(a)", {"a": a3(V3_HSV)}, lambda a, b, t: C.hsvToRgb(a)),
        ("house rgb2hsv", "probeHouseRgb2hsv(a)", {"a": a3(V3_RGB_FOR_HSV)}, lambda a, b, t: C.rgbToHsv(a)),
        ("expose", "expose(a, t)", {"a": a3(V3_HDR[:3]), "t": f1([1.0, -2.0, 0.5])}, lambda a, b, t: T.expose(a, t)),
        ("tmTanh", "tmTanh(a)", {"a": a3(V3_HDR + [(1e6, 90.0, 1e30)])}, lambda a, b, t: T.tmTanh(a)),
        ("tmExp", "tmExp(a)", {"a": a3(V3_HDR)}, lambda a, b, t: T.tmExp(a)),
        ("tmReinhard", "tmReinhard(a)", {"a": a3(V3_HDR)}, lambda a, b, t: T.tmReinhard(a)),
        ("tmAcesFit", "tmAcesFit(a)", {"a": a3(V3_HDR)}, lambda a, b, t: T.tmAcesFit(a)),
        ("tmPbrNeutral", "tmPbrNeutral(a)", {"a": a3(V3_HDR)}, lambda a, b, t: T.tmPbrNeutral(a)),
        ("tmRootGain", "tmRootGain(a, t)", {"a": a3(V3_HDR[:3]), "t": f1([0.5, 1.0, 3.094])},
         lambda a, b, t: T.tmRootGain(a, t)),
        ("displayHueSafeGamma", "displayHueSafeGamma(a, t)",
         {"a": a3([(0.02, 0.01, 0.005), (0.0, 0.0, 0.0), (2.0, 1.0, 0.5)]), "t": f1([2.2, 2.2, 0.8])},
         lambda a, b, t: T.displayHueSafeGamma(a, t)),
        ("tmSuperlinear", "tmSuperlinear(a, t)", {"a": a3(V3_GLOW), "t": f1([0.85] * len(V3_GLOW))},
         lambda a, b, t: T.tmSuperlinear(a, t)),
        ("house superlinear", "probeHouseSuperlinear(a)", {"a": a3(V3_GLOW)},
         lambda a, b, t: T.tmSuperlinear(a, 0.85)),
        ("grdSaturation", "grdSaturation(a, t)", {"a": a3(V3_COLOURS[:4]), "t": f1([0.0, 0.5, 1.0, 2.0])},
         lambda a, b, t: C.grdSaturation(a, t)),
        ("grdAwayFrom", "grdAwayFrom(a, b, t)",
         {"a": a3(V3_COLOURS[:3]), "b": a3([(0.5, 0.5, 0.5)] * 3), "t": f1([0.0, 1.0, 3.0])},
         lambda a, b, t: C.grdAwayFrom(a, b, t)),
        ("grdSCurveDisp", "grdSCurveDisp(a, t)", {"a": a3([(0.0, 0.25, 0.5), (0.75, 1.0, 0.1)] * 2),
                                                  "t": f1([0.0, 0.5, 1.0, 0.3])},
         lambda a, b, t: C.grdSCurveDisp(a, t)),
        ("palCos", f"palCos(t, {rainbow})", {"t": f1(F_T)}, lambda a, b, t: P.palCos(t, *rb)),
        ("palCosLinear", f"palCosLinear(t, {rainbow})", {"t": f1(F_T)}, lambda a, b, t: P.palCosLinear(t, *rb)),
        ("palOklch", "palOklch(t, 0.72, 0.1, 0.1, 1.0)", {"t": f1(F_T)},
         lambda a, b, t: P.palOklch(t, 0.72, 0.1, 0.1, 1.0)),
        ("palRamp3", "palRamp3(t, vec3(0.0, 0.42, 0.69), vec3(0.01, 0.12, 1.0), vec3(0.08, 0.03, 0.83))",
         {"t": f1(F_T)}, lambda a, b, t: P.palRamp3(t, *ember)),
        ("palHeatPowers", "palHeatPowers(t, vec3(1.0, 2.0, 4.0))", {"t": f1([0.0, 0.5, 1.0, 1.5])},
         lambda a, b, t: P.palHeatPowers(t, [1.0, 2.0, 4.0])),
        ("palPitchFifths", "palPitchFifths(t, 4.0, palPitchPiano())", {"t": f1([float(i) for i in range(12)])},
         lambda a, b, t: P.palPitchFifths(t, 4.0, pp)),
        ("palPitchLumaMean", "vec3(palPitchLumaMean(palPitchPiano()), palPitchPiano().lumaTarget, 0.0)",
         {"t": f1([0.0])}, lambda a, b, t: [P.palPitchLumaMean(pp), pp.lumaTarget, 0.0]),
    ]
    return groups


DEFAULT_TOL = 1e-4          # float32 on SwiftShader against float64: far below one 8-bit code (3.9e-3)
TRIG_TOL = 5e-4             # GLSL ES lets sin and cos be approximate; SwiftShader's measured 9e-5 here (2026-10-13)
TRIG_GROUPS = ("oklabFromOklch", "mixOklch", "oklchClip", "hueRotateOklch", "oklchMaxChroma", "palCos", "palCosLinear",
               "palOklch")
TOLERANCE = dict({g: TRIG_TOL for g in TRIG_GROUPS}, palPitchFifths=ONE_CODE)
LEGACY_PAIRS = [("hsvToRgb", "house hsv2rgb"), ("rgbToHsv", "house rgb2hsv"), ("tmSuperlinear", "house superlinear")]
PROBE_COLS = 8              # cases per row; each case is 6 pixels (3 channels x 2 halves of 32 bits)


def _glsl_float(x: float) -> str:
    return repr(float(x)) if math.isfinite(x) else "0.0"


def _glsl_value(kind: str, v) -> str:
    if kind == "float":
        return _glsl_float(v)
    return "vec3(" + ", ".join(_glsl_float(c) for c in v) + ")"


def _house_texts() -> str:
    """The house's own pasted text, read now from the files that hold it and renamed so it cannot clash: First Light's
    HSV pair and the bench chunk's superlinear statement. Never written anywhere but the probe in a temp folder."""
    fl = FIRST_LIGHT.read_text(encoding="utf-8")
    out = []
    for fn, new in (("rgb2hsv", "probeHouseRgb2hsv"), ("hsv2rgb", "probeHouseHsv2rgb")):
        m = re.search(r"^vec3 " + fn + r"\(vec3 c\) \{\n(?:.*\n)*?\}\n", fl, re.M)
        assert m, f"first-light.frag no longer defines {fn} the way this pin reads it"
        out.append(m.group(0).replace(fn + "(", new + "("))
    chunk = [ln for ln in SUPERLINEAR_CHUNK.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("//")]
    assert chunk == ["col += col * col * 0.85;"], chunk
    out.append("vec3 probeHouseSuperlinear(vec3 col) {\n    " + chunk[0] + "\n    return col;\n}\n")
    return "\n".join(out)


def _probe_card(groups) -> str:
    decls, branches, n = [], [], 0
    for gi, (label, expr, args, _) in enumerate(groups):
        count = max(len(v) for _, v in args.values())
        local = []
        for arg, (kind, vals) in args.items():
            vals = list(vals) + [vals[-1]] * (count - len(vals))
            decls.append(f"const {kind} PROBE_G{gi}_{arg.upper()}[{count}] = {kind}[{count}]("
                         + ", ".join(_glsl_value(kind, v) for v in vals) + ");")
            local.append(f"{kind} {arg} = PROBE_G{gi}_{arg.upper()}[i];")
        branches.append(f"    if (i < {count}) {{ {' '.join(local)} return {expr}; }}  // {label}\n    i -= {count};")
        n += count
    rows = (n + PROBE_COLS - 1) // PROBE_COLS
    uses = sorted(MODULES)
    header = {"card": "colour-twin-probe", "uses": uses, "t": [0], "size": [PROBE_COLS * 6, rows],
              "note": "TEST PROBE (tests/test_glsl_twins_colour.py): float32 bits of every case, 16 bits per pixel."}
    body = "\n".join(decls) + "\n\n" + _house_texts() + "\n" + "vec3 probeCase(int i) {\n" + "\n".join(branches) + \
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


def _decode(png: Path, n: int) -> np.ndarray:
    from PIL import Image
    with Image.open(png) as im:
        px = np.asarray(im.convert("RGB"), dtype=np.uint32)
    px = px[::-1]                                       # PNG row 0 is the top; fragment row 0 is the bottom
    out = np.zeros((n, 3), dtype=np.float32)
    for i in range(n):
        y, x0 = divmod(i, PROBE_COLS)
        for ch in range(3):
            hi = px[y, x0 * 6 + 2 * ch]
            lo = px[y, x0 * 6 + 2 * ch + 1]
            bits = (((hi[0] << 8) | hi[1]) << 16) | ((lo[0] << 8) | lo[1])
            out[i, ch] = np.array([bits], dtype=np.uint32).view(np.float32)[0]
    return out


@pytest.fixture(scope="module")
def gpu(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node is not on PATH (the headless driver)")
    from arsenal.shaders import cards as K
    groups = _groups()
    text, n = _probe_card(groups)
    cards_dir = tmp_path_factory.mktemp("probe_cards")
    (cards_dir / "colour-twin-probe.card").write_text(text, encoding="utf-8", newline="\n")
    out = tmp_path_factory.mktemp("probe_out")
    report = K.render_cards(["colour-twin-probe"], cards_dir=cards_dir, out_root=out, allow_tracked=True,
                            lock_wait_min=5, quiet=True)
    driver = report["driver"]
    if driver.get("error") and "lock" in str(driver["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {driver['error']}")
    assert not driver.get("refused"), driver["refused"]
    row = report["cards"][0]
    assert row.get("compile_ok") is True, row
    receipt = json.loads(Path(row["receipt"]).read_text(encoding="utf-8"))
    png = Path(receipt["card"]["frames"][0]["png"])
    return groups, _decode(png, n)


@pytest.mark.slow
def test_glsl_modules_agree_with_their_twins_on_swiftshader(gpu):
    groups, got = gpu
    i, bad = 0, []
    for label, _expr, args, twin in groups:
        count = max(len(v) for _, v in args.values())
        for k in range(count):
            pick = {arg: vals[min(k, len(vals) - 1)] for arg, (kind, vals) in args.items()}
            want = np.asarray(twin(_lin(pick["a"]) if "a" in pick else None,
                                   _lin(pick["b"]) if "b" in pick else None,
                                   float(pick["t"]) if "t" in pick else None), dtype=float).reshape(3)
            tol = TOLERANCE.get(label, DEFAULT_TOL)
            if not (np.all(np.isfinite(got[i])) and np.all(np.abs(got[i] - want) <= tol)):
                bad.append(f"{label}[{k}] {pick}: glsl {got[i].tolist()} twin {want.tolist()} (tol {tol})")
            i += 1
    assert not bad, "\n".join(bad)


def _rows(groups, label):
    start = 0
    for name, _e, args, _t in groups:
        count = max(len(v) for _, v in args.values())
        if name == label:
            return slice(start, start + count)
        start += count
    raise KeyError(label)


@pytest.mark.slow
@pytest.mark.parametrize("module_fn,house", LEGACY_PAIRS)
def test_legacy_twins_are_bit_identical_to_the_house_text_they_replace(gpu, module_fn, house):
    # A legacy twin promises that a surface can swap its pasted copy for the module without one pixel moving: the same
    # inputs through the module and through the house's own text give the same float32 bits on the GPU.
    groups, got = gpu
    mine, theirs = got[_rows(groups, module_fn)], got[_rows(groups, house)]
    assert np.array_equal(mine.view(np.uint32), theirs.view(np.uint32)), (mine, theirs)


@pytest.mark.slow
def test_glsl_twin_and_piano_agree_on_every_pitch_class(gpu, piano_palette):
    groups, got = gpu
    start = 0
    for label, _e, args, _t in groups:
        if label == "palPitchFifths":
            break
        start += max(len(v) for _, v in args.values())
    pp = P.palPitchPiano()
    for pc in range(12):
        glsl, twin = got[start + pc].astype(float), np.asarray(P.palPitchFifths(float(pc), 4.0, pp))
        js = np.asarray(piano_palette["rgb"][pc])
        assert close(glsl, twin, ONE_CODE) and close(glsl, js, ONE_CODE) and close(twin, js, ONE_CODE), \
            (pc, glsl, twin, js)
