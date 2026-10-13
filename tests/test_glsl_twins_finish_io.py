"""The finish-and-io modules of the house GLSL library, pinned before they were written (shader school, 2026-10-13,
batch A, family 'finish-io'): post/vignette, post/dither, post/display-out, composite/blend, motion/envelope,
input/mouse, input/audio and sim/feedback, with their CPU twins (arsenal/shaders/twins/finish.py and envelope.py) and
their cards (arsenal/web/glsl/cards/<module>.card).

WHY. These are the parts every surface ends with (the display tail) or listens through (mouse, audio, the clock's
envelopes), so a wrong number here is wrong everywhere at once. Two kinds of pin:
  - the MODULE pins: each planned function exists with the planned signature (atlas.json; one fix, reported: displayOut
    takes the canvas size, because a vignette cannot be placed from a pixel alone), the header carries the house fields,
    lint is clean, every module composes, the recipe's params pass the param schema, every card parses and builds;
  - the TWIN pins: reference values from the mathematics and the standards (equal temperament, IEC 61966-2-1 sRGB, the
    Web Audio analyser's decibel mapping, Porter and Duff's over), plus the properties the contracts promise (black stays
    black through the dither, an 8-bit trail clears with the floor step and sticks without it, three flashes a second at
    most, over is associative).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest

from arsenal import params as P
from arsenal.shaders import cards as C
from arsenal.shaders import modules as M
from arsenal.shaders.twins import envelope as E
from arsenal.shaders.twins import finish as F

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "arsenal" / "web" / "glsl"

# file -> (module name, kind, atlas category, twin file, {function: signature}). Signatures are the atlas's
# (arsenal/shaders/atlas.json), word for word, except displayOut's added `vec2 res` (reported with the slice).
PLAN = {
    "post/vignette.glsl": ("post-vignette", "helper", "H7", "arsenal/shaders/twins/finish.py", {
        "vigCorner": "float vigCorner(vec2 uv01, float aspect, float amount)"}),
    "post/dither.glsl": ("post-dither", "helper", "H8", "arsenal/shaders/twins/finish.py", {
        "ditherOut": "vec3 ditherOut(vec3 enc, vec2 pixel, float levels)"}),
    "post/display-out.glsl": ("display-out", "recipe", "H9", "arsenal/shaders/twins/finish.py", {
        "displayOut": "vec3 displayOut(vec3 sceneLin, vec2 pixel, vec2 res, float ev, int curve, float saturation, "
                      "float vignette, float sCurve, float ditherLevels)"}),
    "composite/blend.glsl": ("composite-blend", "helper", "M1", "arsenal/shaders/twins/finish.py", {
        "cmpOver": "vec4 cmpOver(vec4 front, vec4 back)",
        "cmpOverPremul": "vec4 cmpOverPremul(vec4 front, vec4 back)",
        "cmpUnder": "void cmpUnder(inout vec4 acc, vec4 layer)",
        "cmpAdd": "vec3 cmpAdd(vec3 a, vec3 b)",
        "cmpScreen": "vec3 cmpScreen(vec3 a, vec3 b)",
        "cmpMax": "vec3 cmpMax(vec3 a, vec3 b)"}),
    "motion/envelope.glsl": ("motion-envelope", "helper", "I1", "arsenal/shaders/twins/envelope.py", {
        "envRamp": "float envRamp(float t, float start, float dur)",
        "envWindow": "float envWindow(float t, float a, float b, float soft)",
        "envCubicEase": "float envCubicEase(float x)",
        "envSineEase": "float envSineEase(float x)",
        "envFlashSafe": "float envFlashSafe(float sinceLastFlash)",
        "envBreath": "float envBreath(float x, float t, vec2 rates)"}),
    "input/mouse.glsl": ("input-mouse", "helper", "L1", "arsenal/shaders/twins/finish.py", {
        "mouseUntouched": "bool mouseUntouched(vec4 mouse)",
        "mouseHeld": "bool mouseHeld(vec4 mouse)",
        "mouseJustClicked": "bool mouseJustClicked(vec4 mouse)",
        "mouseDragOrigin": "vec2 mouseDragOrigin(vec4 mouse)"}),
    "input/audio.glsl": ("input-audio", "helper", "L2", "arsenal/shaders/twins/finish.py", {
        "audSpectrum": "float audSpectrum(sampler2D a, float u)",
        "audBand": "float audBand(sampler2D a, float hzLo, float hzHi, float sampleRate)",
        "midiToHz": "float midiToHz(float m)",
        "hzToMidi": "float hzToMidi(float hz)",
        "pianoKeyToHz": "float pianoKeyToHz(float key)",
        # P1 (atlas L2.05), built because audBand needs the byte-to-amplitude step; the atlas elides their parameters
        "audWave": "float audWave(sampler2D a, float u)",
        "audByteToDb": "float audByteToDb(float v)",
        "audByteToAmp": "float audByteToAmp(float v)"}),
    "sim/feedback.glsl": ("sim-feedback", "helper", "J6", "arsenal/shaders/twins/finish.py", {
        "simSanitize": "vec4 simSanitize(vec4 v, float bound, vec4 fallback)",
        "fbDecay": "vec3 fbDecay(vec3 prev, float keep, float floorStep)"}),
}
NAMES = [v[0] for v in PLAN.values()]
COST_CLASSES = {"C0", "C1", "C2", "C3", "C4"}


@pytest.fixture(scope="module")
def lib():
    return M.load_library(strict=False)


def _module_at(lib, rel):
    want = (LIB / rel).resolve()
    for m in lib.modules.values():
        if Path(m.path).resolve() == want:
            return m
    problems = [p for p in lib.problems if Path(p["path"]).resolve() == want]
    raise AssertionError(f"no module loaded from {rel}" + (f" (quarantined: {problems[0]['problem']})" if problems else ""))


def _signatures(m):
    out = {}
    for d in M.DEFINITION_RE.finditer(M.strip_comments(m.body)):
        if d.group(1) in M.NOT_A_TYPE:
            continue
        params = " ".join(d.group(3).split())
        out[d.group(2)] = f"{d.group(1)} {d.group(2)}({params})"
    return out


# ------------------------------------------------------------------------------------------------- module pins
@pytest.mark.parametrize("rel", sorted(PLAN))
def test_each_module_provides_the_planned_functions_with_the_planned_signatures(lib, rel):
    name, kind, _cat, _twin, sigs = PLAN[rel]
    m = _module_at(lib, rel)
    assert m.name == name
    assert m.kind == kind
    have = _signatures(m)
    for fn, sig in sigs.items():
        assert fn in have, f"{rel} does not define {fn}"
        assert have[fn] == sig, f"{rel}: {have[fn]!r} is not the planned {sig!r}"


@pytest.mark.parametrize("rel", sorted(PLAN))
def test_each_header_carries_the_house_fields(lib, rel):
    name, _kind, cat, twin, sigs = PLAN[rel]
    h = _module_at(lib, rel).header
    assert h["license"] == "Apache-2.0"
    assert h.get("public", True) is True
    assert h["cat"] == cat and h["family"] == cat[0]
    assert re.fullmatch(r"\d+\.\d+\.\d+", h["version"])
    assert isinstance(h["credits"], list) and h["credits"], "every one of these techniques was taught by someone"
    assert all(isinstance(c, str) and ("http" in c or "/" in c) for c in h["credits"]), "a credit carries a pointer"
    assert h["cost"]["class"] in COST_CLASSES and isinstance(h["cost"].get("tex"), int)
    for field in ("contract", "note"):
        assert isinstance(h[field], str) and len(h[field]) > 40
    assert h["targets"]["glsl"] == "300es" and isinstance(h["targets"]["needs"], list)
    assert h["card"] == f"{name}.card"
    assert h["twin"] == twin and (ROOT / twin).is_file()
    twin_mod = F if twin.endswith("finish.py") else E
    for fn in sigs:
        assert callable(getattr(twin_mod, fn, None)), f"{twin} has no twin for {fn}"
    assert h["status"] in ("P0", "P1", "P2")
    assert isinstance(h.get("exemplars", []), list) and isinstance(h.get("learn", []), list)


def test_audio_declares_texel_fetch_and_nothing_else_needs_a_special_target(lib):
    for rel, (name, *_rest) in PLAN.items():
        needs = _module_at(lib, rel).header["targets"]["needs"]
        assert needs == (["texelFetch"] if name == "input-audio" else []), f"{name}: targets.needs {needs}"


@pytest.mark.parametrize("rel", sorted(PLAN))
def test_each_module_lints_clean_in_the_library(lib, rel):
    m = _module_at(lib, rel)
    assert M.lint(m, library=lib) == []


@pytest.mark.parametrize("target", ["toy", "webgl2", "three-r186"])
def test_every_module_composes(lib, target):
    text = lib.compose(NAMES, target=target)
    for rel, (name, *_rest) in PLAN.items():
        assert f"{name}@" in text.splitlines()[1]


def test_display_out_params_pass_the_param_schema(lib):
    h = _module_at(lib, "post/display-out.glsl").header
    descriptors = P.params_from_module(h)
    assert P.check_descriptors(descriptors) == []
    assert [d["id"] for d in descriptors] == ["ev", "curve", "saturation", "vignette", "sCurve", "ditherLevels"]
    entry = " ".join(h["entry"].split())
    assert entry == PLAN["post/display-out.glsl"][4]["displayOut"]
    # the knobs the atlas's finish group names, with its defaults
    defaults = {d["id"]: d["default"] for d in descriptors}
    assert defaults == {"ev": 0, "curve": 0, "saturation": 1, "vignette": 0.25, "sCurve": 0, "ditherLevels": 256}
    curve = next(d for d in descriptors if d["id"] == "curve")
    assert [v["value"] for v in curve["values"]] == [0, 1, 2, 3]


@pytest.mark.parametrize("name", NAMES)
def test_each_module_has_a_card_that_parses_and_builds(lib, name):
    card = C.load_card(name)
    assert name in card.uses
    assert len(card.note) > 60
    shader = C.build_card(card, library=lib)
    assert name in shader["card"]["modules"]


# ---------------------------------------------------------------------------------------------- vignette twin
def test_vig_corner_is_one_at_the_centre_and_the_house_cubic_at_the_corner():
    for aspect in (1.0, 16 / 9, 21 / 9, 9 / 16):
        assert F.vigCorner((0.5, 0.5), aspect, 1.0) == pytest.approx(1.0, abs=1e-12)
        for corner in ((0, 0), (1, 0), (0, 1), (1, 1)):
            assert F.vigCorner(corner, aspect, 1.0) == pytest.approx(1 - 0.94 ** 3, abs=1e-9)
            assert F.vigCorner(corner, aspect, 0.6) == pytest.approx(1 - 0.6 * 0.94 ** 3, abs=1e-9)
    assert F.vigCorner((0.1, 0.9), 16 / 9, 0.0) == 1.0


def test_vig_corner_reproduces_the_legacy_chunk_at_amount_0_6():
    # design/vfx-chunks/vignette-cubic.glsl, recomputed independently from its maths
    rng = np.random.default_rng(7)
    for _ in range(200):
        u, v = rng.random(2)
        asp = float(rng.uniform(0.4, 3.0))
        vd = math.hypot((u - 0.5) * asp, v - 0.5) / math.hypot(0.5 * asp, 0.5)
        legacy = 1.0 + (1.0 - min(max(vd * 0.94, 0.0), 1.0) ** 3 - 1.0) * 0.60
        assert F.vigCorner((u, v), asp, 0.6) == pytest.approx(legacy, abs=1e-9)


def test_vig_corner_keeps_the_sides_of_a_widescreen_lit():
    # the bug the house chunk exists to prevent: normalising by 0.7071 instead of the real corner blacks out the sides
    side = F.vigCorner((0.0, 0.5), 16 / 9, 1.0)
    assert 0.44 < side < 0.46
    assert F.vigCorner((0.5, 0.75), 16 / 9, 1.0) > 0.985     # flat across the middle: under 1.5 % a quarter-height out


# ------------------------------------------------------------------------------------------------ dither twin
def _codes(enc, levels=256.0, size=64):
    ys, xs = np.mgrid[0:size, 0:size]
    pix = np.stack([xs + 0.5, ys + 0.5], axis=-1).reshape(-1, 2)
    out = np.array([F.ditherOut((enc, enc, enc), p, levels) for p in pix])
    return np.floor(out * (levels - 1.0) + 0.5)        # what an 8-bit UNORM write stores (round to nearest)


def test_dither_keeps_black_black_and_white_white():
    assert np.all(_codes(0.0) == 0)
    assert np.all(_codes(1.0) == 255)
    assert np.all(_codes(0.0, levels=16.0) == 0)


def test_dither_preserves_the_mean_and_spans_at_most_one_code_value():
    for code in (0.3, 1.5, 10.25, 100.5, 200.75, 254.6):
        enc = code / 255.0
        q = _codes(enc)
        assert abs(q.mean() - code) < 0.03, (code, q.mean())
        assert q.min() >= math.floor(code) - 1 and q.max() <= math.ceil(code) + 1


def test_dither_breaks_a_band_a_rounding_alone_would_leave():
    q = _codes(100.5 / 255.0)
    assert len(np.unique(q)) >= 2                       # rounding alone gives one code everywhere


def test_dither_off_below_two_levels_and_static_in_time():
    for levels in (0.0, 1.0):
        assert F.ditherOut((0.25, 0.5, 0.75), (10.5, 3.5), levels) == pytest.approx((0.25, 0.5, 0.75), abs=0)
    a = F.ditherOut((0.4, 0.4, 0.4), (17.5, 9.5), 256.0)
    b = F.ditherOut((0.4, 0.4, 0.4), (17.5, 9.5), 256.0)
    assert tuple(a) == tuple(b)                        # no clock in the signature, and no hidden one


# ------------------------------------------------------------------------------------------- display-out twin
def _srgb_oetf(x):
    return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def test_display_out_black_is_black_on_every_curve():
    for curve in range(4):
        for px in ((0.5, 0.5), (319.5, 179.5), (160.5, 90.5)):
            out = F.displayOut((0.0, 0.0, 0.0), px, (320.0, 180.0), 0.0, curve, 1.0, 0.25, 0.0, 256.0)
            assert np.all(np.floor(np.asarray(out) * 255 + 0.5) == 0)


def test_display_out_glow_field_grey_at_the_centre():
    # tanh, no vignette at the centre, sRGB encode, no S-curve: within one code value of the closed form
    want = _srgb_oetf(math.tanh(0.18)) * 255
    out = F.displayOut((0.18, 0.18, 0.18), (160.5, 90.5), (321.0, 181.0), 0.0, 0, 1.0, 0.25, 0.0, 256.0)
    assert np.all(np.abs(np.asarray(out) * 255 - want) <= 1.0001)
    flat = F.displayOut((0.18, 0.18, 0.18), (160.5, 90.5), (321.0, 181.0), 0.0, 0, 1.0, 0.25, 0.0, 0.0)
    assert np.asarray(flat) == pytest.approx(want / 255, abs=1e-6)


def test_display_out_exposure_is_stops_and_saturation_zero_is_grey():
    a = F.displayOut((0.1, 0.1, 0.1), (50.5, 50.5), (100.0, 100.0), 1.0, 1, 1.0, 0.0, 0.0, 0.0)
    b = F.displayOut((0.2, 0.2, 0.2), (50.5, 50.5), (100.0, 100.0), 0.0, 1, 1.0, 0.0, 0.0, 0.0)
    assert np.asarray(a) == pytest.approx(np.asarray(b), abs=1e-9)
    g = np.asarray(F.displayOut((0.8, 0.1, 0.05), (50.5, 50.5), (100.0, 100.0), 0.0, 3, 0.0, 0.0, 0.0, 0.0))
    assert g[0] == pytest.approx(g[1], abs=1e-9) and g[1] == pytest.approx(g[2], abs=1e-9)


def test_display_out_vignette_darkens_the_corner_only():
    centre = F.displayOut((0.5, 0.5, 0.5), (50.0, 50.0), (100.0, 100.0), 0.0, 0, 1.0, 1.0, 0.0, 0.0)
    corner = F.displayOut((0.5, 0.5, 0.5), (0.0, 0.0), (100.0, 100.0), 0.0, 0, 1.0, 1.0, 0.0, 0.0)
    plain = F.displayOut((0.5, 0.5, 0.5), (0.0, 0.0), (100.0, 100.0), 0.0, 0, 1.0, 0.0, 0.0, 0.0)
    assert np.asarray(centre) == pytest.approx(np.asarray(plain), abs=1e-9)
    assert np.all(np.asarray(corner) < np.asarray(plain) - 0.2)


def test_display_out_stays_inside_the_canvas_for_hot_and_negative_light():
    for scene in ((50.0, 3.0, 0.0), (-1.0, 0.5, 2.0), (1e6, 1e6, 1e6)):
        for curve in range(4):
            out = np.asarray(F.displayOut(scene, (10.5, 10.5), (64.0, 64.0), 2.0, curve, 2.0, 0.5, 1.0, 256.0))
            assert np.all(np.isfinite(out)) and np.all(out >= 0) and np.all(out <= 1)


# ------------------------------------------------------------------------------------------------- blend twin
def _premul(c):
    c = np.asarray(c, float)
    return np.concatenate([c[:3] * c[3], c[3:]])


def test_over_straight_alpha_reference_values():
    assert np.asarray(F.cmpOver((1, 0, 0, 0.5), (0, 0, 1, 1))) == pytest.approx((0.5, 0, 0.5, 1))
    assert np.asarray(F.cmpOver((1, 1, 1, 0), (0.2, 0.3, 0.4, 0.7))) == pytest.approx((0.2, 0.3, 0.4, 0.7))
    assert np.asarray(F.cmpOver((0.9, 0.1, 0.2, 1), (0.2, 0.3, 0.4, 0.7))) == pytest.approx((0.9, 0.1, 0.2, 1))
    assert np.asarray(F.cmpOver((1, 1, 1, 0), (1, 1, 1, 0))) == pytest.approx((0, 0, 0, 0))


def test_over_straight_and_premultiplied_agree_and_premultiplied_over_is_associative():
    rng = np.random.default_rng(11)
    for _ in range(100):
        a, b, c = rng.random((3, 4))
        assert _premul(F.cmpOver(a, b)) == pytest.approx(np.asarray(F.cmpOverPremul(_premul(a), _premul(b))), abs=1e-9)
        pa, pb, pc = _premul(a), _premul(b), _premul(c)
        left = F.cmpOverPremul(F.cmpOverPremul(pa, pb), pc)
        right = F.cmpOverPremul(pa, F.cmpOverPremul(pb, pc))
        assert np.asarray(left) == pytest.approx(np.asarray(right), abs=1e-9)


def test_under_front_to_back_equals_over_back_to_front_and_stops_when_opaque():
    rng = np.random.default_rng(5)
    layers = [_premul(np.append(rng.random(3), rng.uniform(0.1, 0.6))) for _ in range(6)]
    acc = np.zeros(4)
    for layer in layers:                                  # nearest first
        acc = F.cmpUnder(acc, layer)
    back = np.zeros(4)
    for layer in reversed(layers):                        # farthest first
        back = F.cmpOverPremul(layer, back)
    assert np.asarray(acc) == pytest.approx(back, abs=1e-9)
    full = np.array([0.3, 0.2, 0.1, 0.999])
    assert np.asarray(F.cmpUnder(full, (1.0, 1.0, 1.0, 1.0))) == pytest.approx(full, abs=0)


def test_add_screen_and_max():
    assert np.asarray(F.cmpAdd((0.5, 2.0, 0.0), (0.75, 1.0, 0.25))) == pytest.approx((1.25, 3.0, 0.25))
    assert np.asarray(F.cmpScreen((0.5, 0.0, 1.0), (0.5, 0.3, 0.2))) == pytest.approx((0.75, 0.3, 1.0))
    assert np.asarray(F.cmpScreen((4.0, -1.0, 0.5), (0.5, 0.5, 2.0))) == pytest.approx((1.0, 0.5, 1.0))
    assert np.asarray(F.cmpMax((0.5, 0.9, 0.0), (0.7, 0.1, 0.0))) == pytest.approx((0.7, 0.9, 0.0))
    rng = np.random.default_rng(3)
    for _ in range(50):
        a, b = rng.random((2, 3))
        assert np.asarray(F.cmpScreen(a, b)) == pytest.approx(np.asarray(F.cmpScreen(b, a)))
        assert np.all(np.asarray(F.cmpScreen(a, b)) >= np.maximum(a, b) - 1e-12)


# ------------------------------------------------------------------------------------------------- mouse twin
def _mouse(x=0.0, y=0.0, click_x=0.0, click_y=0.0, down=False, clicked=False):
    # the shader lab's iMouse (arsenal/web/shaderlab/toy-runtime.js mouseUniform): signs carry the button
    cx, cy = abs(click_x), abs(click_y)
    z = cx if down else -cx
    w = cy if clicked else -cy
    return (x, y, z + 0.0, w + 0.0)


def test_mouse_states_follow_the_shadertoy_convention():
    never = _mouse()
    assert F.mouseUntouched(never) and not F.mouseHeld(never) and not F.mouseJustClicked(never)
    assert tuple(F.mouseDragOrigin(never)) == (0.0, 0.0)
    click = _mouse(100, 50, 100, 50, down=True, clicked=True)
    assert not F.mouseUntouched(click) and F.mouseHeld(click) and F.mouseJustClicked(click)
    drag = _mouse(140, 70, 100, 50, down=True, clicked=False)
    assert F.mouseHeld(drag) and not F.mouseJustClicked(drag)
    assert tuple(F.mouseDragOrigin(drag)) == (100.0, 50.0)
    released = _mouse(140, 70, 100, 50)
    assert not F.mouseUntouched(released) and not F.mouseHeld(released) and not F.mouseJustClicked(released)
    assert tuple(F.mouseDragOrigin(released)) == (100.0, 50.0)


# ------------------------------------------------------------------------------------------------- audio twin
def _audio_texture(spectrum_bytes, width=512):
    tex = np.zeros((2, width), np.uint8)
    tex[0, :] = spectrum_bytes
    tex[1, :] = 128
    return tex


def test_equal_temperament_reference_values():
    assert F.midiToHz(69) == pytest.approx(440.0, abs=1e-9)
    assert F.midiToHz(60) == pytest.approx(261.6255653005986, abs=1e-9)
    assert F.midiToHz(21) == pytest.approx(27.5, abs=1e-9)
    assert F.pianoKeyToHz(1) == pytest.approx(27.5, abs=1e-9)
    assert F.pianoKeyToHz(49) == pytest.approx(440.0, abs=1e-9)
    assert F.pianoKeyToHz(88) == pytest.approx(4186.009044809578, abs=1e-6)
    for m in np.linspace(0, 127, 255):
        assert F.hzToMidi(F.midiToHz(m)) == pytest.approx(m, abs=1e-9)
    assert math.isfinite(F.hzToMidi(0.0)) and math.isfinite(F.hzToMidi(-5.0))


def test_spectrum_reads_row_zero_as_the_byte_over_255():
    ramp = np.arange(512) % 256
    tex = _audio_texture(ramp)
    for k in (0, 1, 100, 255, 300, 511):
        assert F.audSpectrum(tex, (k + 0.5) / 512) == pytest.approx(ramp[k] / 255.0, abs=1e-9)
    assert F.audSpectrum(tex, 100.0 / 512) == pytest.approx((ramp[99] + ramp[100]) / 2 / 255.0, abs=1e-9)
    assert F.audSpectrum(_audio_texture(np.zeros(512)), 0.3) == 0.0


def test_wave_and_byte_conversions_invert_the_analyser():
    # Web Audio: waveform byte = floor(128 (1 + x)), so 128 is silence; spectrum byte spans -100..-30 dB
    tex = np.zeros((2, 512), np.uint8)
    tex[1, :] = 128
    tex[1, 10], tex[1, 11] = 255, 0
    assert F.audWave(tex, 0.5) == 0.0
    assert F.audWave(tex, 10.5 / 512) == pytest.approx(255 / 128 - 1, abs=1e-12)
    assert F.audWave(tex, 11.5 / 512) == pytest.approx(-1.0, abs=1e-12)
    assert F.audByteToDb(0.0) == -100.0 and F.audByteToDb(1.0) == pytest.approx(-30.0)
    assert F.audByteToAmp(1.0) == pytest.approx(10 ** -1.5, rel=1e-12)
    assert F.audByteToAmp(0.5) == pytest.approx(10 ** -3.25, rel=1e-12)
    assert F.audByteToAmp(0.0) == 0.0


def test_band_is_the_mean_linear_magnitude_and_silence_is_zero():
    sr = 48000.0
    assert F.audBand(_audio_texture(np.zeros(512)), 100.0, 2000.0, sr) == 0.0
    # an empty channel (the runtime binds a 1x1 black texture) and a texture of no width both read silence
    assert F.audBand(np.zeros((1, 1), np.uint8), 100.0, 2000.0, sr) == 0.0
    assert F.audBand(np.zeros((2, 0), np.uint8), 100.0, 2000.0, sr) == 0.0
    assert F.audWave(np.zeros((1, 1), np.uint8), 0.3) == 0.0 and F.audSpectrum(np.zeros((1, 1), np.uint8), 0.3) == 0.0
    b = 200
    amp = 10 ** ((-100 + 70 * b / 255) / 20)               # the analyser's default -100..-30 dB mapping, inverted
    assert F.audBand(_audio_texture(np.full(512, b)), 100.0, 2000.0, sr) == pytest.approx(amp, rel=1e-9)
    # two bins, one loud, one silent: the mean is half the loud bin's amplitude (linear, not the mean of the bytes)
    spec = np.zeros(512)
    k = round(1000.0 * 2048 / sr)
    spec[k] = 255
    one = F.audBand(_audio_texture(spec), 1000.0, 1000.0 + sr / 2048, sr)
    assert one == pytest.approx(10 ** (-30 / 20) / 2, rel=1e-9)
    assert F.audBand(_audio_texture(spec), 1000.0 + sr / 2048, 1000.0, sr) == pytest.approx(one, rel=1e-12)


def test_band_wider_than_64_bins_takes_at_most_64_taps_and_never_reads_past_the_texture():
    sr = 44100.0
    tex = _audio_texture(np.full(512, 128))
    wide = F.audBand(tex, 0.0, 20000.0, sr)                 # 20 kHz is past texel 511 at 44.1 kHz
    assert wide == pytest.approx(10 ** ((-100 + 70 * 128 / 255) / 20), rel=1e-9)
    bins = F.audBandBins(0.0, 20000.0, sr, 512)             # the GLSL loop's tap plan, as the twin computes it
    assert 0 < len(bins) <= 64 and min(bins) == 0 and max(bins) <= 511
    assert F.audBandBins(1000.0, 1000.0, sr, 512) == [round(1000.0 * 2048 / sr)]


# ---------------------------------------------------------------------------------------------- feedback twin
def test_sanitize_replaces_non_finite_components_and_clamps_the_rest():
    fb = (0.1, 0.2, 0.3, 1.0)
    out = np.asarray(F.simSanitize((float("nan"), float("inf"), -float("inf"), 0.5), 10.0, fb))
    assert out == pytest.approx((0.1, 0.2, 0.3, 0.5))
    out = np.asarray(F.simSanitize((1e9, -1e9, 3.0, -3.0), 4.0, fb))
    assert out == pytest.approx((4.0, -4.0, 3.0, -3.0))


def test_fb_decay_reference_value_and_sign():
    assert np.asarray(F.fbDecay((1.0, 0.5, 0.0), 0.98, 1 / 255)) == pytest.approx(
        (0.98 - 1 / 255, 0.49 - 1 / 255, 0.0), abs=1e-12)
    assert np.asarray(F.fbDecay((0.001, -0.001, -1.0), 0.98, 1 / 255)) == pytest.approx(
        (0.0, 0.0, -0.98 + 1 / 255), abs=1e-12)


def _frames_to_clear(step, start_byte=255, frames=2000, half_up=True):
    b = start_byte
    for n in range(frames):
        v = step(b / 255.0)
        x = v * 255.0
        nb = math.floor(x + 0.5) if half_up else round(x)
        if nb == b:
            return None, b                                    # stuck: nothing changes any more
        b = nb
        if b == 0:
            return n + 1, 0
    return None, b


def test_an_8_bit_trail_sticks_without_the_floor_and_clears_with_it():
    for half_up in (True, False):
        frames, stuck = _frames_to_clear(lambda v: v * 0.98, half_up=half_up)
        assert frames is None and stuck in (24, 25)          # GP finding 6: about a tenth of full brightness
        frames, left = _frames_to_clear(lambda v: float(F.fbDecay((v, v, v), 0.98, 1 / 255)[0]), half_up=half_up)
        assert left == 0 and frames < 200


# ---------------------------------------------------------------------------------------------- envelope twin
def test_ramp_reference_values():
    assert E.envRamp(5.0, 2.0, 4.0) == pytest.approx(0.75)
    assert E.envRamp(1.0, 2.0, 4.0) == 0.0 and E.envRamp(9.0, 2.0, 4.0) == 1.0
    assert E.envRamp(1.9, 2.0, 0.0) == 0.0 and E.envRamp(2.1, 2.0, 0.0) == 1.0   # dur 0: an instant switch
    assert math.isfinite(E.envRamp(2.0, 2.0, 0.0))


def test_window_rises_at_a_and_falls_at_b_and_is_zero_outside():
    w = lambda t: E.envWindow(t, 1.0, 5.0, 1.0)
    assert w(0.5) == 0.0 and w(1.0) == 0.0 and w(5.0) == 0.0 and w(6.0) == 0.0
    assert w(1.5) == pytest.approx(0.5) and w(3.0) == pytest.approx(1.0) and w(4.5) == pytest.approx(0.5)
    assert math.isfinite(E.envWindow(1.0, 1.0, 5.0, 0.0)) and E.envWindow(3.0, 1.0, 5.0, 0.0) == 1.0


def test_eases_reference_values_and_symmetry():
    assert E.envCubicEase(0.25) == pytest.approx(0.0625) and E.envCubicEase(0.75) == pytest.approx(0.9375)
    assert E.envSineEase(0.25) == pytest.approx(0.5 - 0.5 * math.cos(math.pi / 4))
    for ease in (E.envCubicEase, E.envSineEase):
        assert ease(0.0) == 0.0 and ease(1.0) == pytest.approx(1.0) and ease(0.5) == pytest.approx(0.5)
        assert ease(-1.0) == 0.0 and ease(2.0) == pytest.approx(1.0)
        xs = np.linspace(0, 1, 401)
        ys = np.array([ease(x) for x in xs])
        assert np.all(np.diff(ys) >= -1e-12)
        assert ys == pytest.approx(1.0 - ys[::-1], abs=1e-12)


def test_flash_gate_allows_at_most_three_flashes_a_second():
    assert E.envFlashSafe(0.0) == 0.0 and E.envFlashSafe(1 / 3) == 0.0 and E.envFlashSafe(0.5) == 1.0
    assert E.envFlashSafe(1e6) == 1.0
    # a host that fires a flash on every frame the gate lets through at least 10 % (a WCAG "flash")
    dt, since, flashes = 1 / 240, 1e6, []
    for n in range(240 * 10):
        t = n * dt
        if E.envFlashSafe(since) >= 0.1:
            flashes.append(t)
            since = 0.0
        since += dt
    gaps = np.diff(flashes)
    assert len(flashes) > 10 and gaps.min() > 1 / 3
    assert max(sum(1 for f in flashes if s <= f < s + 1.0) for s in flashes) <= 3


def test_breath_stays_in_unit_range_mostly_on_and_still_when_the_rates_are_zero():
    xs = np.linspace(-3, 3, 241)
    vals = np.array([[E.envBreath(x, t, (0.1, 0.35)) for x in xs] for t in np.linspace(0, 20, 21)])
    assert vals.min() >= 0.0 and vals.max() <= 1.0
    assert 0.45 < vals.mean() < 0.85
    still = [E.envBreath(0.37, t, (0.0, 0.0)) for t in (0.0, 5.0, 50.0)]
    assert still[0] == pytest.approx(still[1]) == pytest.approx(still[2])
    # two timescales: the fast part changes more between two nearby instants than the slow part does
    slow = np.mean([abs(E.envBreath(x, 1.0, (0.1, 0.0)) - E.envBreath(x, 1.5, (0.1, 0.0))) for x in xs])
    fast = np.mean([abs(E.envBreath(x, 1.0, (0.0, 0.5)) - E.envBreath(x, 1.5, (0.0, 0.5))) for x in xs])
    assert fast > slow > 0


# ------------------------------------------------------------------------------- GPU parity (SwiftShader, slow)
@pytest.mark.slow
def test_display_out_card_matches_the_twin_within_one_code_value(tmp_path):
    """The display-out card rendered on SwiftShader against the twin, pixel by pixel (every third pixel each way, all
    four display curves): the tail's whole chain -- exposure, the four curves, saturation, the vignette, the sRGB
    encode and the static dither's mask -- must land on the same byte, or one byte off where a rounding sits on an
    exact half."""
    import shutil
    from PIL import Image
    if shutil.which("node") is None:
        pytest.skip("node is not on PATH (the headless driver)")
    report = C.render_cards(["display-out"], out_root=tmp_path / "cards", allow_tracked=True, lock_wait_min=5,
                            quiet=True)
    if report["driver"].get("error") and "lock" in str(report["driver"]["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {report['driver']['error']}")
    row = report["cards"][0]
    assert row["ok"], row
    card = C.load_card("display-out")
    w, h = card.size
    lit_codes = [7, 4, 6, 2, 3, 1, 5]                      # the card's rows: grey, red, yellow, green, cyan, blue, magenta
    for curve, t in enumerate(card.times):
        img = np.asarray(Image.open(tmp_path / "cards" / "display-out" / f"t{t:.2f}.png").convert("RGB")).astype(int)
        diffs = []
        for y in range(0, h, 3):
            for x in range(0, w, 3):
                px = np.array([x + 0.5, (h - 1 - y) + 0.5])          # a PNG's first row is the top; GL's y is up
                uv = px / np.array([w, h])
                row_index = min(max(int((1 - uv[1]) * 7), 0), 6)
                lit = lit_codes[row_index]
                prim = np.array([(lit // 4) % 2, (lit // 2) % 2, lit % 2], float)
                scene = 0.18 * 2 ** (-7 + 14 * uv[0]) * prim / np.dot(prim, [0.2126, 0.7152, 0.0722])
                out = np.asarray(F.displayOut(scene, px, (w, h), 0.0, curve, 1.0, 0.25, 0.0, 256.0))
                edge = abs((1 - uv[1]) * 7 + 0.5 - math.floor((1 - uv[1]) * 7 + 0.5) - 0.5) * h / 7
                s = min(max((edge - 0.4) / 0.8, 0.0), 1.0)
                want = np.floor(np.clip(out * s * s * (3 - 2 * s), 0, 1) * 255 + 0.5)
                diffs.append(np.abs(img[y, x] - want).max())
        diffs = np.array(diffs)
        assert diffs.max() <= 1, (curve, diffs.max())
        assert (diffs == 0).mean() > 0.995, (curve, (diffs == 0).mean())
