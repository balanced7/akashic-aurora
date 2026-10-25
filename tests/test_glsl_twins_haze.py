"""Pins for light in haze: atmos/haze.glsl (module atmos-haze), the tone stage tmStage (colour/tone.glsl) and
glowHotCoreTo (light/glow.glsl), with their CPU twins (arsenal/shaders/twins/haze.py, tone.py, light.py) and the card.

WHY THESE PINS. Three judges failed three VJ builds on the same thing (research/reviewed/keylab-liberation-2026-10-22:
vj-void-star, vj-laser-sky, vj-virtual-stage-v0): beams that turned pastel mint over blue air, haze clouds made of round
blobs instead of streaks along the beams, flat hard-edged wedges with no white-hot root, and an air that was a grey veil
rather than light. Look v2 section 2 (vj-look-v2-hdr-2026-10-24.md) designs the shared module that fixes them. Each of
those failures is a measurable property, so each is pinned here on the CPU twin, by a route independent of the module's
own formula where one exists:
  * haze shows light, never is light: exactly zero where no light reaches (every profile has compact support), at any
    haze density, and no ambient term;
  * the core and body keep the light's chroma (no white anywhere but the root), and the halo adds no white over blue air
    (the Laser Sky mint mechanism);
  * the root's first percent runs above 1.0 and whitens; by an eighth of the reach it is the light's own colour again;
  * no hard edge: every cross-section ramps over a measurable width, with no step;
  * the haze texture is stretched along the beam (and stays put in the world when the beam turns);
  * the 3D equiangular estimator converges to a brute-force integral of the same integrand, and a ray that misses the
    light is exactly zero;
  * tmStage matches Look v2 1.4's written-out curve wherever that curve does not drift (heat 0, or below the knee) and
    keeps its peak everywhere; its drift to white runs at constant OKLab hue instead of the brief's linear mix (a
    departure Daniel rules on), and holds hue within 2 degrees on the six primaries at 1-20x;
  * glowHotCoreTo with white is glowHotCore, and whitens toward the colour it is given.
Round 2 (the round-1 judge's must-change list, research/reviewed/keylab-liberation-2026-10-22/vj-light-in-haze-2026-
10-25.md) adds, again by independent routes where they exist:
  * hazeStreak is dash-sized (about 40 per cent clump, dashes about one dash length long) with no seam round the light;
  * hazeBeamSwept is the shutter average of the still beam (checked against a dense average), zero beyond its support;
  * the core floor is a parameter, and the sheet body's pale/saturated choice does what it says;
  * the 3D light is exactly proportional to the haze amount (more haze never dims a beam);
  * hazeRing's closed form equals a sum over its arc, it lights the inside of a ring more than the outside, and it is
    exactly zero beyond its reach; hazeRing3's irradiance equals a ring of lamps and its estimator converges;
  * hazeBlueNoise is a blue-noise permutation of 256 ranks.
The slow test at the bottom renders a parity card on SwiftShader under the house GPU lock and compares the GLSL with
the twin pixel for pixel.

Apache-2.0, Akashic Aurora. Written fresh for the house; no corpus code.
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

from arsenal.shaders import cards as K
from arsenal.shaders import modules as M
from arsenal.shaders.twins import colour as C
from arsenal.shaders.twins import haze as Z
from arsenal.shaders.twins import light as L
from arsenal.shaders.twins import tone as T

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "arsenal" / "web" / "glsl"
ATLAS = REPO / "arsenal" / "shaders" / "atlas.json"

HAZE_SIGNATURES = {
    "hazeDensity": ("float", ["vec2", "float", "vec4", "float"]),
    "hazeFloorBand": ("float", ["vec2", "float", "float", "float"]),
    "hazeStreak": ("float", ["vec2", "vec2", "vec4", "float"]),
    "hazeBeamCoords": ("vec3", ["vec2", "vec2", "vec2", "float"]),
    "hazePhase": ("float", ["float"]),
    "hazeBeam": ("vec3", ["float", "float", "vec3", "float", "float", "float", "float", "float"]),
    "hazeBeamSwept": ("vec3", ["float", "float", "float", "vec3", "float", "float", "float", "float", "float"]),
    "hazeSheet": ("vec3", ["float", "float", "float", "vec3", "float", "float", "float", "float"]),
    "hazePoint": ("vec3", ["vec2", "vec2", "float", "vec3", "float", "float"]),
    "hazePool": ("vec3", ["vec2", "vec2", "vec2", "vec3", "float"]),
    "hazeTint": ("vec3", ["vec3", "float"]),
    "hazeRing": ("vec3", ["vec2", "vec2", "vec4", "vec2", "vec3", "float", "float"]),
    "hazeDensity3": ("float", ["vec3", "float", "vec4", "float"]),
    "hazeStreak3": ("float", ["vec3", "vec3", "vec4", "float"]),
    "hazeConeProfile": ("float", ["vec3", "vec3", "vec3", "float"]),
    "hazeCone": ("vec3", ["vec3", "vec3", "float", "vec3", "vec3", "float", "vec3", "float", "vec2", "vec4", "vec4",
                          "float", "float"]),
    "hazeSheet3": ("vec3", ["vec3", "vec3", "float", "vec3", "vec3", "vec3", "float", "float", "vec3", "float", "vec2",
                            "vec4", "vec4", "float"]),
    "hazeLamp": ("vec3", ["vec3", "vec3", "float", "vec3", "float", "vec3", "float", "vec2", "vec4", "float",
                          "float"]),
    "hazeRing3": ("vec3", ["vec3", "vec3", "float", "vec3", "vec3", "vec3", "vec3", "float", "vec2", "vec4", "float",
                           "float"]),
    "hazeBlueNoise": ("float", ["vec2"]),
}
NEW_ELSEWHERE = {"tmStage": ("colour-tone", "vec3", ["vec3", "float", "float"]),
                 "glowHotCoreTo": ("light-glow", "vec3", ["vec3", "float", "vec3"])}

GREEN = np.array([0.006, 1.0, 0.135])          # acid green, linear (the Berlin frames' brightest green, normalised)
VIOLET = np.array([0.55, 0.1, 1.0])
BLUE_AIR = np.array([0.008, 0.026, 0.156])     # the Berlin air #162d6d, linear
PRIMARIES = {"red": [1, 0, 0], "green": [0, 1, 0], "blue": [0, 0, 1], "cyan": [0, 1, 1], "magenta": [1, 0, 1],
             "yellow": [1, 1, 0]}


def _hue_deg(lin):
    return C.oklchFromOklab(C.oklabFromLinear(lin))[..., 2] * 360.0


def _hue_gap(a, b):
    return np.abs((np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0)


# --------------------------------------------------------------------------------------------- the modules themselves
@pytest.fixture(scope="module")
def library():
    return M.load_library(strict=False)


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


def test_the_haze_module_is_where_look_v2_puts_it_with_exactly_its_parts(library):
    m = library.modules["atmos-haze"]
    assert Path(m.path).resolve() == (LIB / "atmos" / "haze.glsl").resolve()
    defs = _definitions(m)
    assert sorted(defs) == sorted(HAZE_SIGNATURES), sorted(set(defs) ^ set(HAZE_SIGNATURES))
    for fn, sig in HAZE_SIGNATURES.items():
        assert defs[fn] == [sig], (fn, defs[fn])
    for fn, (module, ret, params) in NEW_ELSEWHERE.items():
        assert (ret, params) in _definitions(library.modules[module])[fn], fn


def test_the_header_carries_every_library_field(library):
    h = library.modules["atmos-haze"].header
    assert h["cat"] == "G7" and h["family"] == "G" and h["kind"] == "helper" and h["license"] == "Apache-2.0"
    assert re.fullmatch(r"\d+\.\d+\.\d+", h["version"]) and h["status"] == "P1"
    assert h["credits"] and all("http" in c for c in h["credits"])
    assert h["cost"]["class"] == "C1" and h["cost"]["tex"] == 0 and h["cost"]["loop"]
    assert h["contract"] and h["note"] and h["targets"] == {"glsl": "300es", "needs": ["uint"]}
    assert h["card"] == "atmos-haze.card" and (LIB / "cards" / h["card"]).is_file()
    assert h["twin"] == "arsenal/shaders/twins/haze.py" and (REPO / h["twin"]).is_file()
    for name in ("atmos-haze", "colour-tone", "light-glow"):
        path = Path(library.modules[name].path)
        assert b"\r" not in path.read_bytes(), path


def test_it_reuses_the_house_instead_of_redeclaring_it(library):
    deps = set(library.resolve(["atmos-haze"]))
    assert {"noise-value", "volume-phase", "light-glow", "colour-oklab", "hash-pcg"} <= deps, deps
    assert "colour-oklab" in set(library.resolve(["colour-tone"]))     # tmStage's drift is in OKLab
    m = library.modules["atmos-haze"]
    assert not m.consts and not m.structs, "no top-level names beyond the planned functions"


def test_each_module_composes_lints_clean_and_has_a_card_that_builds(library):
    for name in ("atmos-haze", "colour-tone", "light-glow"):
        m = library.modules[name]
        for target in ("toy", "webgl2", "three-r186"):
            assert name in library.compose([name], target=target).splitlines()[0]
        assert M.lint(m, library_module=True, library=library) == [], name
    card = K.load_card("atmos-haze")
    assert "atmos-haze" in card.uses and card.note
    assert "atmos-haze" in K.build_card(card, library=library)["card"]["modules"]


def test_the_atlas_plans_every_new_name_with_its_built_signature():
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    owner = {fn: p for p in atlas["parts"] for fn in p["functions"]}
    every = dict(HAZE_SIGNATURES, **{k: v[1:] for k, v in NEW_ELSEWHERE.items()})
    for fn, (ret, params) in every.items():
        assert fn in owner, f"the atlas does not plan {fn}"
        decl = re.search(rf"\b(\w+)\s+{fn}\s*\(([^()]*)\)", owner[fn]["signature"])
        assert decl, (fn, owner[fn]["signature"])
        types = [" ".join(p.split()[:-1]) for p in decl.group(2).split(",")] if decl.group(2).strip() else []
        assert (decl.group(1), types) == (ret, params), (fn, owner[fn]["signature"])
    haze = {owner[fn]["module"] for fn in HAZE_SIGNATURES}
    assert haze == {"atmos/haze.glsl"}
    assert owner["tmStage"]["module"] == "colour/tone.glsl" and owner["glowHotCoreTo"]["module"] == "light/glow.glsl"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
def test_the_browser_twin_composes_the_same_bytes():
    names = ["atmos-haze", "colour-tone", "light-glow"]
    lib = M.load_library([LIB])
    out = subprocess.run(["node", str(REPO / "tests" / "glsl_modlib_parity.mjs"), str(LIB), *names],
                         capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout == lib.prelude(names)


# ------------------------------------------------------------------------- haze shows light, never is light (zero)
def test_every_2d_part_is_exactly_zero_where_no_light_reaches():
    w = 10.0
    d = np.linspace(8.0 * w, 40.0 * w, 50)
    assert np.all(Z.hazeBeam(d, 0.4, GREEN, 3.0, 1.0, w, 5.0, 1.0) == 0.0)                 # 8 widths out, dense haze
    assert np.all(Z.hazeBeam(0.0, np.linspace(-1.0, -0.0121, 30), GREEN, 3.0, 1.0, w, 1.0, 1.0) == 0.0)   # behind root
    assert np.all(Z.hazeBeam(0.0, np.linspace(1.0, 3.0, 30), GREEN, 3.0, 1.0, w, 1.0, 1.0) == 0.0)       # past the end
    assert np.all(Z.hazeSheet(np.linspace(0.44, 3.0, 40), 0.2, 0.5, VIOLET, 1.0, 1.0, 3.0, 1.0) == 0.0)  # 2.2 half-angles
    rr = np.linspace(3.0, 9.0, 40)[:, None] * np.array([1.0, 0.0])
    assert np.all(Z.hazePoint(rr, [0.0, 0.0], 1.0, GREEN, 4.0, 1.0) == 0.0)
    assert np.all(Z.hazePool(rr * np.array([2.0, 1.0]), [0.0, 0.0], [2.0, 0.5], GREEN, 4.0) == 0.0)
    assert np.all(Z.hazeBeam(np.linspace(0, 20, 9), 0.5, GREEN, 0.0, 1.0, w, 1.0, 1.0) == 0.0)  # no light, no haze glow


def test_the_density_never_lights_anything_by_itself():
    # a dense haze field multiplies light; with no light the result is zero however dense the air is
    p = np.random.default_rng(1).uniform(-1, 1, size=(500, 2))
    dens = Z.hazeDensity(p, -1.0, [3.0, 0.5, 0.02, 0.0], 5.0)
    assert np.all((dens >= 0.0) & (dens <= 1.0))
    assert np.all(Z.hazeBeam(np.full(500, 300.0), 0.5, GREEN, 2.0, dens, 10.0, 1.0, 0.05) == 0.0)
    assert np.all(Z.hazePoint(p, [5.0, 5.0], 0.3, GREEN, 2.0, dens) == 0.0)


def test_the_3d_parts_are_exactly_zero_for_rays_that_miss_the_light():
    ro = np.array([0.0, 1.7, 0.0])
    rd = np.array([[0.0, 0.2, -1.0], [-1.0, 0.1, 0.0], [0.0, -0.3, 1.0]])
    rd = rd / np.linalg.norm(rd, axis=-1, keepdims=True)
    cone = Z.hazeCone(ro, rd, 60.0, [12.0, 9.0, -20.0], [0.2, -1.0, 0.1], 0.08, VIOLET, 200.0, [1.0, 0.0],
                      [0.4, 7.0, 0.1, 0.0], [1.5, 0.05, 0.8, 0.2], 1.0, 0.5)
    assert np.all(cone == 0.0)
    lamp = Z.hazeLamp(ro, rd, 60.0, [12.0, 2.0, -6.0], 3.0, VIOLET, 50.0, [1.0, 0.0], [0.4, 7.0, 0.1, 0.0], 1.0, 0.3)
    assert np.all(lamp == 0.0)
    for amount in (0.0, 1.0, 4.0):                     # the haze amount never turns a miss into a grey veil
        miss = Z.hazeCone(ro, rd, 60.0, [12.0, 9.0, -20.0], [0.2, -1.0, 0.1], 0.08, VIOLET, 200.0, [amount, 0.0],
                          [0.4, 7.0, 0.1, 0.0], [1.5, 0.05, 0.8, 0.2], 1.0, 0.5)
        assert np.all(miss == 0.0)


# ------------------------------------------------------------------------------- the colour stays in the beam
def test_the_core_body_and_halo_keep_the_lights_chroma_beyond_the_root():
    d = np.linspace(0.0, 60.0, 121)
    for along in (0.15, 0.4, 0.7):
        beam = Z.hazeBeam(d, along, GREEN, 2.0, 0.7, 10.0, 1.2, 0.05)
        lit = np.max(beam, axis=-1) > 0
        shape = beam[lit] / np.max(beam[lit], axis=-1, keepdims=True)
        assert np.allclose(shape, GREEN / GREEN.max(), atol=1e-5), along      # the same colour, only its level moves
    sheet = Z.hazeSheet(np.linspace(-0.3, 0.3, 61), 0.2, 0.5, VIOLET, 0.8, 0.6, 1.0, 1.0)   # pale 1: as given
    shape = sheet / np.max(sheet, axis=-1, keepdims=True)
    assert np.allclose(shape, VIOLET / VIOLET.max(), atol=2e-6)
    mid = Z.hazeBeam(0.0, 0.5, GREEN, 2.0, 0.7, 10.0, 1.2, 0.05)
    lch_mid, lch_col = (C.oklchFromOklab(C.oklabFromLinear(c / c.max())) for c in (mid, GREEN))
    assert abs(lch_mid[1] - lch_col[1]) < 1e-5 and _hue_gap(lch_mid[2] * 360, lch_col[2] * 360) < 1e-3


def test_a_green_beam_over_blue_air_stays_acid_green_not_mint():
    # The Laser Sky judge's mechanism: a wide glow of green laid over blue air turns mint (HSV saturation 0.49-0.52).
    # Here the beam adds no white, so over the Berlin air the brightest green keeps saturation >= 0.8 and the halo's
    # edge adds no grey to the air.
    d = np.linspace(0.0, 80.0, 161)
    seen = BLUE_AIR + Z.hazeBeam(d, 0.45, GREEN, 1.2, 0.8, 10.0, 1.0, 0.05)
    enc = C.srgbEncode(np.clip(T.tmStage(seen, 0.3, 1.0), 0.0, 1.0))
    hsv = C.rgbToHsv(enc)
    green = (hsv[..., 0] * 360 >= 85) & (hsv[..., 0] * 360 < 160) & (hsv[..., 1] >= 0.45) & (hsv[..., 2] >= 0.3)
    assert green.sum() >= 3
    top = hsv[green][np.argsort(hsv[green][:, 2])[-max(1, green.sum() // 4):]]
    assert top[:, 1].mean() >= 0.8, top
    added = seen - BLUE_AIR
    assert np.all(np.min(added, axis=-1) <= GREEN.min() / GREEN.max() * np.max(added, axis=-1) + 1e-12)


# --------------------------------------------------------------------------------------------- the white-hot root
def test_the_root_runs_hot_and_white_then_the_colour_returns():
    near = Z.hazeBeam(0.0, 0.006, GREEN, 1.5, 0.6, 10.0, 1.0, 0.05)
    assert near.max() > 1.0 and near.min() / near.max() > 0.7, near      # above SDR white and nearly white
    mid = Z.hazeBeam(0.0, 0.06, GREEN, 1.5, 0.6, 10.0, 1.0, 0.05)
    assert np.allclose(mid / mid.max(), GREEN / GREEN.max(), atol=0.02)   # 6 per cent along: its own colour again
    hot = [Z.hazeBeam(0.0, a, GREEN, 1.0, 0.6, 10.0, 1.0, 0.05).max() for a in (0.006, 0.015, 0.03)]
    assert hot[0] > hot[1] > hot[2] and hot[0] > 1.0                    # the first few per cent run above 1
    sheet_root = Z.hazeSheet(0.0, 0.2, 0.012, VIOLET, 0.6, 0.6, 1.0, 0.0)
    assert sheet_root.max() > 1.0 and sheet_root.min() / sheet_root.max() > 0.7
    shown = C.srgbEncode(np.clip(T.tmStage(sheet_root, 0.5, 1.0), 0.0, 1.0))
    sat = 1.0 - shown.min() / shown.max()
    luma = float(shown @ np.array([0.2126, 0.7152, 0.0722]))
    assert luma >= 0.95 and sat < 0.25, (luma, sat)                     # white-hot after the display stage


# --------------------------------------------------------------------------------------------------- no hard edge
def _ramp_width(x, y):
    """Distance between the 90 % and 10 % points of a falling edge (y normalised to its own maximum)."""
    y = np.asarray(y) / np.max(y)
    i90 = np.argmax(y < 0.9)
    i10 = np.argmax(y < 0.1)
    return x[i10] - x[i90]


def test_no_part_has_a_hard_edge():
    d = np.linspace(0.0, 80.0, 4001)
    beam = Z.hazeBeam(d, 0.5, GREEN, 1.0, 1.0, 12.0, 1.0, 0.05)[:, 1]
    body = Z.hazeBeam(d, 0.5, GREEN, 1.0, 1.0, 12.0, 1.0, 0.05)[:, 1] - Z.hazeBeam(d, 0.5, GREEN, 1.0, 1.0, 12.0, 0.0, 0.05)[:, 1]
    assert np.all(np.diff(beam) <= 1e-12)                                   # monotone falling away from the axis
    assert np.max(np.abs(np.diff(beam, 2))) < 2e-3 * beam.max()            # no step and no kink in the profile
    a = np.linspace(0.0, 0.5, 5001)
    sheet = Z.hazeSheet(a, 0.2, 0.5, VIOLET, 1.0, 1.0, 1.0, 0.0)[:, 2]
    assert np.all(np.diff(sheet) <= 1e-12)
    assert _ramp_width(a, sheet) >= 0.5 * 0.2, _ramp_width(a, sheet)        # the edge ramps over half a half-angle
    assert np.max(np.abs(np.diff(sheet))) < 0.01 * sheet.max()               # never a step (Void Star's outlines)
    assert _ramp_width(d, body) >= 0.25 * 12.0, _ramp_width(d, body)     # the body's edge ramps over 3+ px


# --------------------------------------------------------------------------------- the texture follows the beam
def _correlation_length(values, step):
    v = np.asarray(values) - np.mean(values)
    ac = np.correlate(v, v, mode="full")[len(v) - 1:]
    ac = ac / ac[0]
    below = np.argmax(ac < 0.5)
    return below * step


@pytest.mark.parametrize("clump, least", [([0.03, 0.01, 1.0, 0.0], 3.0),      # dashes 3+ cells long: the design
                                          ([0.06, 0.03, 1.0, 0.0], 1.5)])     # cells nearly as long as a dash
def test_the_clumps_are_stretched_along_the_rays_from_the_light(clump, least):
    root = np.array([0.0, -0.5])
    ratios = []
    for ang in np.radians([35.0, 60.0, 90.0, 125.0]):
        u = np.array([math.cos(ang), math.sin(ang)])
        n = np.array([-u[1], u[0]])
        lens_along, lens_across = [], []
        for r0 in np.linspace(0.4, 0.8, 9):
            s = np.linspace(-0.2, 0.2, 801)
            step = s[1] - s[0]
            along = Z.hazeStreak(root + np.outer(r0 + s, u), root, clump, 0.0)
            across = Z.hazeStreak(root + r0 * u + np.outer(s, n), root, clump, 0.0)
            lens_along.append(_correlation_length(along, step))
            lens_across.append(_correlation_length(across, step))
        ratios.append(np.mean(lens_along) / np.mean(lens_across))
    assert min(ratios) > least, ratios                       # long along every beam direction, short across it


def test_the_field_is_static_in_the_world_and_drifts_outward_at_its_speed():
    root = np.array([0.1, -0.6])
    p = np.random.default_rng(3).uniform(-0.5, 0.5, size=(400, 2))
    clump = np.array([0.05, 0.03, 0.9, 0.04])
    a = Z.hazeStreak(p, root, clump, 2.0)
    u = (p - root) / np.linalg.norm(p - root, axis=-1, keepdims=True)
    b = Z.hazeStreak(p + u * (clump[3] * 1.5), root, clump, 3.5)          # 1.5 s later, 1.5 s of drift further out
    far = np.linalg.norm(p - root, axis=-1) > 3.0 * clump[0] + 0.1
    assert np.max(np.abs(a - b)[far]) < 1e-9
    d0 = Z.hazeDensity(p, -5.0, [3.0, 50.0, 0.05, 0.0], 1.0)
    d1 = Z.hazeDensity(p + np.array([0.05, 0.0]) * 2.0, -5.0, [3.0, 50.0, 0.05, 0.0], 3.0)
    assert np.max(np.abs(d0 - d1)) < 1e-9                                 # the density drifts, never reseeds


def test_a_beam_crossing_the_clumps_breaks_into_dashes_along_itself():
    root = np.array([0.0, -0.5])
    for ang in np.radians([40.0, 75.0]):
        u = np.array([math.cos(ang), math.sin(ang)])
        s = np.linspace(0.3, 1.5, 2400)
        dens = Z.hazeStreak(root + np.outer(s, u), root, [0.05, 0.03, 1.0, 0.0], 0.0)
        line = Z.hazeBeam(0.0, s / 2.0, GREEN, 1.0, dens, 10.0, 1.0, 0.05)[:, 1]
        trend = Z.hazeBeam(0.0, s / 2.0, GREEN, 1.0, 1.0, 10.0, 1.0, 0.05)[:, 1]     # the same beam in even haze
        rel = line / trend
        assert rel.max() > 3.0 * rel.min()                               # bright in a clump, dim between them
        lit = rel > 0.5 * (rel.max() + rel.min())
        runs = np.count_nonzero(np.diff(lit.astype(int)) == 1)
        assert runs >= 4, runs                                           # several dashes, not one even rod


# ---------------------------------------------------------------------------------------- the 3D estimator is honest
def _brute_cone(ro, rd, t_max, apex, axis, hw, col, level, air, hz, clump, t, n=20000):
    # the same integrand, sampled uniformly and densely; the density is the module's documented approximation (linear
    # between the ends of the chord inside the cone), so this checks the equiangular estimator, not the noise
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    t0, t1, ok = Z._cone_interval(ro[None], rd[None], np.array([t_max]), apex, a, 1.0 - 2.6 * (1.0 - math.cos(hw)))
    t0, t1 = float(t0[0]), float(t1[0])
    ts = np.linspace(t0, t1, n + 1)[:-1] + 0.5 * (t1 - t0) / n
    p = ro + np.outer(ts, rd)
    v = p - apex
    r = np.maximum(np.linalg.norm(v, axis=-1), 1e-9)
    prof = Z.hazeConeProfile(p, apex, axis, hw)
    d0, d1 = Z.hazeDensity3(ro + rd * t0, air[1], hz, t), Z.hazeDensity3(ro + rd * t1, air[1], hz, t)
    sigma = air[0] * (d0 + (d1 - d0) * (ts - t0) / (t1 - t0)) * Z.hazeStreak3(p, apex, clump, t)
    phase = np.asarray([Z.phaseHG(x, 0.6) for x in np.sum(rd * -v / r[:, None], -1)]) / Z.phaseIso()
    through = np.exp(-0.035 * ts)                                  # the hall's visibility, not the haze amount
    near = np.exp(-(r / 0.45) ** 2)
    c = col * (1 - near[:, None]) + col.max() * near[:, None]
    return level * np.sum(c * (sigma * prof * phase * through / (r * r))[:, None], 0) * ((t1 - t0) / n)


def test_the_equiangular_cone_converges_to_the_brute_force_integral():
    ro = np.array([0.0, 1.7, 0.0])
    apex, axis = np.array([1.5, 9.0, -14.0]), np.array([-0.15, -1.0, 0.35])
    hz, clump = [0.4, 7.0, 0.0, 0.0], [1.5, 0.05, 0.0, 0.0]          # no clumps: a smooth integrand
    for target in ([1.0, 4.0, -12.5], [0.8, 0.5, -11.0]):
        rd = np.array(target) - ro
        rd = rd / np.linalg.norm(rd)
        jit = (np.arange(64) + 0.5) / 64
        est = np.mean([Z.hazeCone(ro, rd, 40.0, apex, axis, 0.12, VIOLET, 100.0, [1.0, 0.0], hz, clump, 0.0, j)
                       for j in jit], axis=0)
        ref = _brute_cone(ro, rd, 40.0, apex, axis, 0.12, VIOLET, 100.0, [1.0, 0.0], hz, clump, 0.0)
        assert ref.max() > 1e-3
        assert np.allclose(est, ref, rtol=0.03, atol=1e-6), (est, ref)


def test_forward_scattering_makes_a_beam_aimed_at_the_eye_brighter():
    ro = np.array([0.0, 1.7, 0.0])
    apex = np.array([0.0, 6.0, -12.0])
    toward = (ro - apex) / np.linalg.norm(ro - apex)
    side = np.array([1.0, 0.0, 0.0])
    look = np.array([0.0, 6.0, -12.0]) + 3.0 * toward - ro
    look_side = np.array([0.0, 6.0, -12.0]) + 3.0 * side - ro
    args = ([1.0, 0.0], [0.4, 7.0, 0.0, 0.0], [1.5, 0.05, 0.0, 0.0], 0.0, 0.5)
    at_eye = Z.hazeCone(ro, look / np.linalg.norm(look), 40.0, apex, toward, 0.15, GREEN, 50.0, *args)
    side_on = Z.hazeCone(ro, look_side / np.linalg.norm(look_side), 40.0, apex, side, 0.15, GREEN, 50.0, *args)
    assert at_eye.max() > 3.0 * side_on.max() > 0.0


def test_the_lamp_and_the_sheet_are_finite_bounded_and_honest():
    ro = np.array([0.0, 1.7, 0.0])
    pos = np.array([0.5, 2.5, -8.0])
    rd = (pos + np.array([0.3, 0.2, 0.0]) - ro)
    rd = rd / np.linalg.norm(rd)
    hz = [0.4, 7.0, 0.0, 0.0]
    est = np.mean([Z.hazeLamp(ro, rd, 40.0, pos, 4.0, GREEN, 30.0, [1.0, 0.0], hz, 0.0, j)
                   for j in (np.arange(64) + 0.5) / 64], axis=0)
    ts = np.linspace(0, 40, 40001)[:-1] + 0.0005
    p = ro + np.outer(ts, rd)
    v = p - pos
    r = np.linalg.norm(v, axis=-1)
    reach = 1.0 - Z._smoothstep(1.6, 4.0, r)
    phase = Z.phaseHG(np.sum(rd * -v / r[:, None], -1), 0.6) / Z.phaseIso()
    near = np.exp(-(r / 0.45) ** 2)
    c = GREEN * (1 - near[:, None]) + near[:, None]
    dens = Z.hazeDensity3(p, 0.0, hz, 0.0)
    ref = 30.0 * np.sum(c * (dens * reach * phase * np.exp(-0.035 * ts) / (r * r))[:, None], 0) * 0.001
    assert np.allclose(est, ref, rtol=0.05), (est, ref)
    # an edge-on sheet is a capped bright line, not infinity; off the fan it is zero
    apex, axis, normal = np.array([0.0, 3.0, -12.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    edge = Z.hazeSheet3(ro, np.array([0.0, 0.18, -1.0]) / np.linalg.norm([0.0, 0.18, -1.0]), 40.0, apex, axis,
                        normal, 0.5, 0.03, VIOLET, 5.0, [1.0, 0.0], hz, [1.5, 0.05, 0.0, 0.0], 0.0)
    assert np.all(np.isfinite(edge))
    below = Z.hazeSheet3(ro, np.array([0.0, -0.05, -1.0]) / np.linalg.norm([0.0, -0.05, -1.0]), 40.0, apex, axis,
                         normal, 0.5, 0.03, VIOLET, 5.0, [1.0, 0.0], hz, [1.5, 0.05, 0.0, 0.0], 0.0)
    assert np.all(below == 0.0)                                       # behind the fan's apex: no light there


# ----------------------------------------------------------------------------------------------------- the tone stage
def _own_spelling(x, heat):
    """tmStage at H = 1 spelled out a second time from its own contract (the peak toe, identity to the knee 0.8, PBR
    Neutral's peak compression, the drift to white at constant OKLab hue). It restates the module, so it pins the twin
    against a rewrite, not against the brief: _brief_written_out below is the independent statement."""
    x = np.maximum(np.asarray(x, float), 0.0)
    p = x.max()
    x = x * p / (p + 0.0015)
    pk = x.max()
    if pk <= 0.8:
        return x
    np_ = 1.0 - 0.04 / (pk + 0.2 - 0.8)
    y = x * np_ / pk
    g = 1.0 - 1.0 / (heat * (pk - np_) + 1.0)
    L_, a, b = C.oklabFromLinear(y)
    back = np.maximum(C.linearFromOklab([L_ + (np_ ** (1 / 3) - L_) * g, a * (1 - g), b * (1 - g)]), 0.0)
    return back * np_ / back.max()


def _brief_written_out(x, heat, H):
    """Look v2 1.4's tmStage, transcribed line for line from the build spec's pseudocode (its drift to white is the
    linear mix toward vec3(np)), for one colour x."""
    x = np.maximum(np.asarray(x, float), 0.0)
    p = x.max()
    x = x * p / (p + 0.0015)
    y = x / H
    pk, K = y.max(), 0.8
    if pk > K:
        d = 1.0 - K
        np_ = 1.0 - d * d / (pk + d - K)
        y = y * np_ / pk
        g = 1.0 - 1.0 / (heat * (pk - np_) + 1.0)
        y = y * (1.0 - g) + np_ * g
    return y * H


def test_tmstage_matches_the_brief_written_out_except_its_drift():
    # Independent of the module: the spec's pseudocode. Where the brief's curve does not drift (heat 0, or a colour
    # below the knee) the two agree exactly; above the knee they share the compressed peak and differ only in how the
    # colour whitens (constant OKLab hue here, a linear mix in the brief: Daniel's call 1 in the round-1 record).
    rng = np.random.default_rng(11)
    for _ in range(400):
        x = rng.uniform(0.0, 1.0, 3) * rng.choice([0.05, 0.5, 1.0, 3.0, 12.0])
        H = rng.choice([1.0, 2.0, 4.0])
        heat = rng.choice([0.15, 0.6, 0.8])
        # (above the knee tmStage takes its colour through OKLab and back even at heat 0: the house matrices round
        # trip to about 1e-6 of the peak, which is the tolerance here)
        assert np.allclose(T.tmStage(x, 0.0, H), _brief_written_out(x, 0.0, H), atol=2e-6 * max(1.0, H))
        ours, brief = T.tmStage(x, heat, H), _brief_written_out(x, heat, H)
        if brief.max() <= 0.8 * H + 1e-12:
            assert np.allclose(ours, brief, atol=1e-9)
        else:
            assert abs(ours.max() - brief.max()) < 1e-9


def test_tmstage_at_h1_matches_its_own_spelling():
    rng = np.random.default_rng(7)
    for _ in range(300):
        x = rng.uniform(0.0, 1.0, 3) * rng.choice([0.05, 0.5, 1.0, 3.0, 12.0])
        heat = rng.choice([0.0, 0.15, 0.6, 0.8])
        assert np.allclose(T.tmStage(x, heat, 1.0), _own_spelling(x, heat), atol=1e-9)
    body = np.array([0.05, 0.4, 0.2])
    assert np.allclose(T.tmStage(body, 0.8, 1.0), body * 0.4 / 0.4015, atol=1e-12)   # bodies pass (the toe only)
    peak = 5.0 * 5.0 / 5.0015                                                    # 5 after the peak toe
    assert abs(T.tmStage([5.0, 1.0, 0.2], 0.0, 1.0).max() - (1.0 - 0.04 / (peak - 0.6))) < 1e-9   # Neutral, knee 0.8


@pytest.mark.parametrize("heat", [0.15, 0.6, 0.8])
@pytest.mark.parametrize("H", [1.0, 4.0])
def test_tmstage_holds_hue_within_two_degrees_on_the_primaries(heat, H):
    for name, rgb in PRIMARIES.items():
        base = np.array(rgb, float)
        h0 = _hue_deg(base)
        for gain in np.geomspace(1.0, 20.0, 25):
            out = T.tmStage(base * gain, heat, H)
            assert out.max() <= H + 1e-9 and np.all(out >= 0.0)
            assert _hue_gap(_hue_deg(out), h0) <= 2.0, (name, gain, _hue_deg(out), h0)


def test_why_the_drift_is_in_oklab():
    # a linear-light mix toward grey (the obvious spelling) turns blue toward violet by far more than 2 degrees
    blue = np.array([0.0, 0.0, 1.0])
    mixed = blue * 0.4 + 0.6
    assert _hue_gap(_hue_deg(mixed), _hue_deg(blue)) > 15.0


def test_tmstage_spends_headroom_only_on_cores():
    x = np.array([[0.1, 0.3, 0.6], [2.0, 0.5, 0.1], [8.0, 6.0, 7.0]])
    for H in (1.0, 2.0, 4.0, 8.0):
        out = T.tmStage(x, 0.5, H)
        assert np.all(out <= H + 1e-9)
        assert np.allclose(out[0], T.tmStage(x[0], 0.5, 1.0), atol=1e-12)        # a body is the same at any H
    peaks = [T.tmStage(np.array([0.2, 1.0, 0.3]) * g, 0.6, 4.0).max() for g in np.geomspace(0.5, 30, 40)]
    assert np.all(np.diff(peaks) >= -1e-12)                                     # brighter in, never darker out


def test_glowhotcoreto_with_white_is_glowhotcore_and_whitens_toward_its_target():
    for tint in ([1.0, 0.35, 0.06], [0.12, 0.3, 1.0], [0.0, 0.0, 0.0]):
        for i in (0.0, 0.3, 1.0, 4.0, 12.0):
            assert np.allclose(L.glowHotCoreTo(tint, i, [1, 1, 1]), L.glowHotCore(tint, i), atol=1e-12)
            assert np.allclose(L.glowHotCoreTo(tint, i, [0, 0, 0]), L.glowHotCore(tint, i), atol=1e-12)
    ring, cyan_white = np.array([0.12, 0.3, 1.0]), np.array([0.62, 0.9, 1.0])
    hot = L.glowHotCoreTo(ring, 20.0, cyan_white)
    assert hot.max() == pytest.approx(20.0 * ring.max())                   # the shared peak channel leads at i * peak
    assert np.allclose(hot / hot.max(), cyan_white, atol=0.01)               # and the rest climb toward the target
    turn = _hue_gap(_hue_deg(hot), _hue_deg(ring))
    assert 15.0 < turn < 60.0, turn                                          # a ring core turns toward cyan


# --------------------------------------------------------------------------------------- round 2: dashes and motion
def test_the_streak_field_is_dash_sized_with_no_seam():
    # The round-1 judge: P1 had 5-18 dashes where Daniel's Berlin frames have 305-328. The field is now cut so about
    # 40 per cent of it is clump and a beam's bright runs are about one dash length long (median), wherever it points.
    root = np.array([0.0, -0.5])
    for clump in ([0.014, 0.008, 1.0, 0.0], [0.05, 0.02, 1.0, 0.0]):
        duty, runs = [], []
        for ang in np.radians(np.linspace(20.0, 160.0, 36)):
            u = np.array([math.cos(ang), math.sin(ang)])
            s = np.linspace(0.3, 0.9, 6000)
            on = Z.hazeStreak(root + np.outer(s, u), root, clump, 0.0) > 0.5
            duty.append(on.mean())
            edges = np.diff(np.r_[0, on.astype(int), 0])
            runs += list((np.nonzero(edges == -1)[0] - np.nonzero(edges == 1)[0]) * (s[1] - s[0]) / clump[0])
        assert 0.32 <= np.mean(duty) <= 0.48, np.mean(duty)
        assert 0.6 <= np.median(runs) <= 1.6, np.median(runs)
    # whole cells round the light: just either side of the angle where atan wraps, the field is continuous
    for r in (0.3, 0.6):
        a = Z.hazeStreak(root + r * np.array([math.cos(math.pi - 1e-7), math.sin(math.pi - 1e-7)]), root,
                         [0.02, 0.01, 1.0, 0.0], 0.0)
        b = Z.hazeStreak(root + r * np.array([math.cos(-math.pi + 1e-7), math.sin(-math.pi + 1e-7)]), root,
                         [0.02, 0.01, 1.0, 0.0], 0.0)
        assert abs(a - b) < 1e-4, (a, b)


def test_the_swept_beam_is_the_still_beam_averaged_over_the_shutter():
    # independent route: average the still beam over many positions across the sweep
    for d0, sweep in ((0.0, 6.0), (3.0, 10.0), (-12.0, 4.0), (25.0, 18.0)):
        xs = d0 + np.linspace(-0.5, 0.5, 4001) * sweep
        dense = Z.hazeBeam(xs, 0.4, GREEN, 1.0, 0.6, 8.0, 1.0, 0.05).mean(axis=0)
        swept = Z.hazeBeamSwept(d0, sweep, 0.4, GREEN, 1.0, 0.6, 8.0, 1.0, 0.05)
        assert np.allclose(swept, dense, rtol=0.01, atol=1e-6), (d0, sweep, swept, dense)
    d = np.linspace(-30.0, 30.0, 61)
    assert np.array_equal(Z.hazeBeamSwept(d, 0.0, 0.3, GREEN, 1.0, 0.5, 8.0, 1.0, 0.1),
                          Z.hazeBeam(d, 0.3, GREEN, 1.0, 0.5, 8.0, 1.0, 0.1))           # no sweep: the still beam
    far = np.linspace(8.0 * 8.0 + 5.0, 200.0, 40)                                       # 8 widths + half the sweep
    assert np.all(Z.hazeBeamSwept(far, 10.0, 0.4, GREEN, 3.0, 1.0, 8.0, 2.0, 1.0) == 0.0)
    # the same light, spread wider: the core's peak falls, its integral across the beam holds
    x = np.linspace(-60.0, 60.0, 2401)
    still = Z.hazeBeam(x, 0.4, GREEN, 1.0, 1.0, 8.0, 0.0, 1.0)[:, 1]
    moved = Z.hazeBeamSwept(x, 12.0, 0.4, GREEN, 1.0, 1.0, 8.0, 0.0, 1.0)[:, 1]
    assert moved.max() < 0.6 * still.max()
    assert abs(np.trapezoid(moved, x) / np.trapezoid(still, x) - 1.0) < 0.01


def test_the_core_floor_is_how_much_of_the_line_shows_in_clean_air():
    for floor in (0.05, 0.4, 1.0):
        clean = Z.hazeBeam(0.0, 0.5, GREEN, 1.0, 0.0, 10.0, 0.0, floor)       # phase 0: the core line alone
        dense = Z.hazeBeam(0.0, 0.5, GREEN, 1.0, 1.0, 10.0, 0.0, floor)
        assert clean[1] == pytest.approx(floor * dense[1], rel=1e-9)
    laser = Z.hazeBeam(0.0, 0.5, GREEN, 1.0, 0.0, 10.0, 1.0, 1.0)
    haze_only = Z.hazeBeam(0.0, 0.5, GREEN, 1.0, 0.0, 10.0, 1.0, 0.05)
    assert laser[1] > 10.0 * haze_only[1]                                    # a laser shows where haze would not


def test_the_sheet_body_is_saturated_or_pale_and_bright_as_asked():
    cyan_white = np.array([0.22, 0.84, 1.0])
    sat = Z.hazeSheet(0.0, 0.1, 0.3, cyan_white, 1.0, 0.5, 1.0, 0.0)
    pale = Z.hazeSheet(0.0, 0.1, 0.3, cyan_white, 1.0, 0.5, 1.0, 1.0)
    root = np.exp(-0.3 / 0.03)                                                # the hot root's share here (tiny)
    assert sat.min() < 1e-3 * sat.max() + root                                # the white part removed: pure hue
    assert sat.max() == pytest.approx(pale.max() / (1.0 + 3.0 * 0.22), rel=1e-3)   # same peak before the lift
    assert np.allclose(pale / pale.max(), cyan_white, atol=2e-3)              # pale keeps the colour as given
    lch_s, lch_p = (C.oklchFromOklab(C.oklabFromLinear(c)) for c in (sat, pale))
    assert lch_s[1] > lch_p[1] and lch_p[0] > lch_s[0]                       # more chroma, or more light
    for pale_k in (0.0, 1.0):                                                 # the root stays white-hot either way
        r = Z.hazeSheet(0.0, 0.2, 0.012, cyan_white, 0.6, 0.6, 1.0, pale_k)
        assert r.max() > 1.0 and r.min() / r.max() > 0.7


# ----------------------------------------------------------------------------- round 2: more haze, never dimmer
def test_the_3d_light_is_exactly_proportional_to_the_haze_amount():
    # The round-1 judge: haze 2 was dimmer than haze 1 and haze 0.15 gave half of haze 1's light, because the
    # transmittance grew with the amount. Now the amount scales only what the air scatters, so every 3D part is linear
    # in it: more haze is never a dimmer beam.
    ro = np.array([0.0, 1.7, 0.0])
    hz, clump = [0.4, 7.0, 0.1, 0.0], [1.5, 0.05, 0.8, 0.2]

    def ray_to(target):
        rd = np.array(target, float) - ro
        return rd / np.linalg.norm(rd)

    apex, axis = np.array([1.0, 9.0, -15.0]), np.array([-0.1, -1.0, 0.6])
    parts = {
        "cone": lambda a: Z.hazeCone(ro, ray_to(apex + 4.0 * axis / np.linalg.norm(axis)), 60.0, apex, axis, 0.15,
                                     VIOLET, 120.0, [a, 0.0], hz, clump, 1.0, 0.4),
        "lamp": lambda a: Z.hazeLamp(ro, ray_to([2.4, 6.3, -14.0]), 60.0, [2.0, 6.0, -14.0], 5.0, VIOLET, 30.0,
                                     [a, 0.0], hz, 1.0, 0.4),
        "ring3": lambda a: Z.hazeRing3(ro, ray_to([0.0, 13.5, -20.0]), 60.0, [0.0, 8.0, -20.0], [0.0, 0.0, 1.0],
                                       [6.0, 0.3, 7.0], VIOLET, 20.0, [a, 0.0], hz, 1.0, 0.4),
        "sheet3": lambda a: Z.hazeSheet3(ro, ray_to([0.3, 4.0, -12.0]), 60.0, [0.0, 2.0, -12.0], [0.0, 1.0, 0.0],
                                         [0.0, 0.0, 1.0], 0.6, 0.03, VIOLET, 5.0, [a, 0.0], hz, clump, 1.0),
    }
    for name, f in parts.items():
        one = f(1.0)
        assert one.max() > 0.0, name
        for a in (0.15, 0.5, 2.0):
            assert np.allclose(f(a), a * one, rtol=1e-9, atol=0.0), (name, a)


# ------------------------------------------------------------------------------- round 2: the ring lights the room
def test_the_ring_closed_form_is_the_sum_over_its_arc():
    ring = np.array([0.4, 0.01, 0.1, 0.3])
    pts = np.random.default_rng(5).uniform(-0.8, 0.8, size=(8, 2))
    for arc in ((0.0, 4.0), (1.0, 1.2), (3.0, 2.5), (-2.9, 0.4)):
        room, _ = Z.hazeRingSpan(pts, [0.0, 0.0], ring, arc)
        half = min(arc[1], math.pi)
        phis = np.linspace(arc[0] - half, arc[0] + half, 100001)
        q = 0.4 * np.stack([np.cos(phis), np.sin(phis)], -1)
        for p, got in zip(pts, room):
            inv = 1.0 / (np.sum((q - p) ** 2, -1) + 0.1 ** 2)
            want = 0.1 * 0.4 * np.trapezoid(inv, phis) / math.pi
            assert got == pytest.approx(want, rel=1e-4), (arc, p)
    on_band, _ = Z.hazeRingSpan([[0.4, 0.0]], [0.0, 0.0], ring, (0.0, 4.0))
    assert on_band[0] == pytest.approx(1.0, rel=0.04)                          # normalised to 1 on a closed band


def test_the_ring_glows_more_inside_than_outside_and_is_zero_beyond_its_reach():
    ring = np.array([0.4, 0.015, 0.1, 0.25])
    col = np.array([0.065, 0.05, 1.0])
    for e in (0.05, 0.1, 0.2):
        inside = Z.hazeRing([0.4 - e, 0.0], [0.0, 0.0], ring, (0.0, 4.0), col, 1.0, 0.7)
        outside = Z.hazeRing([0.4 + e, 0.0], [0.0, 0.0], ring, (0.0, 4.0), col, 1.0, 0.7)
        assert inside[2] > outside[2] > 0.0, e
    ang = np.linspace(0.0, 2.0 * math.pi, 50)
    for rr in (0.4 + 3 * 0.015 + 0.25 + 1e-6, 0.9, 2.0):                      # 3 half-widths plus the reach out
        p = rr * np.stack([np.cos(ang), np.sin(ang)], -1)
        assert np.all(Z.hazeRing(p, [0.0, 0.0], ring, (0.0, 4.0), col, 5.0, 1.0) == 0.0)
    # no haze, no glow beside the band (only the band's own tight glow, 0 beyond 3 half-widths)
    assert np.all(Z.hazeRing([[0.4 + 0.05, 0.0], [0.2, 0.0]], [0.0, 0.0], ring, (0.0, 4.0), col, 5.0, 0.0) == 0.0)
    # the colour is the light's: the haze takes the ring's hue, no white
    glow = Z.hazeRing([0.3, 0.1], [0.0, 0.0], ring, (0.0, 4.0), col, 1.0, 0.8)
    assert np.allclose(glow / glow.max(), col / col.max(), atol=1e-12)
    # an open arc: symmetric about its centre angle, dark at the far side of the gap
    a = Z.hazeRing([0.3 * math.cos(1.0 + 0.4), 0.3 * math.sin(1.0 + 0.4)], [0.0, 0.0], ring, (1.0, 1.2), col, 1.0, 0.8)
    b = Z.hazeRing([0.3 * math.cos(1.0 - 0.4), 0.3 * math.sin(1.0 - 0.4)], [0.0, 0.0], ring, (1.0, 1.2), col, 1.0, 0.8)
    gap = Z.hazeRing([0.4 * math.cos(1.0 + math.pi), 0.4 * math.sin(1.0 + math.pi)], [0.0, 0.0], ring, (1.0, 1.2), col,
                     1.0, 0.8)
    assert np.allclose(a, b, rtol=1e-9) and gap[2] < 0.2 * a[2]


def test_the_3d_ring_is_a_ring_of_lamps_and_its_estimator_converges():
    centre, normal, ring = np.array([0.0, 14.0, -46.0]), np.array([0.0, 0.0, 1.0]), np.array([12.0, 0.45, 15.0])
    pts = centre + np.random.default_rng(9).uniform(-20.0, 20.0, size=(6, 3))
    irr, _ = Z.hazeRingIrradiance(pts, centre, normal, ring)
    phis = np.linspace(0.0, 2.0 * math.pi, 100001)[:-1]
    lamps = centre + 12.0 * np.stack([np.cos(phis), np.sin(phis), 0.0 * phis], -1)
    for x, got in zip(pts, irr):
        assert got == pytest.approx(np.mean(1.0 / np.sum((lamps - x) ** 2, -1)), rel=0.01)   # softened by the band
    far = centre + np.array([0.0, 0.0, 400.0])
    assert Z.hazeRingIrradiance(far[None], centre, normal, ring)[0][0] == pytest.approx(1.0 / 400.0 ** 2, rel=2e-3)
    ro = np.array([0.0, 1.7, 12.0])
    hz = [0.3, 12.0, 0.0, 0.0]
    for target in ([0.0, 14.0, -46.0], [11.5, 14.0, -46.0], [6.0, 22.0, -40.0]):
        rd = np.array(target) - ro
        rd = rd / np.linalg.norm(rd)
        est = np.mean([Z.hazeRing3(ro, rd, 160.0, centre, normal, ring, VIOLET, 40.0, [1.0, 0.0], hz, 0.0, j)
                       for j in (np.arange(64) + 0.5) / 64], axis=0)
        bound = 12.0 + 15.0
        co = ro - centre
        mid = -co @ rd
        chord = math.sqrt(bound * bound - (co @ co - mid * mid))
        t0, t1 = max(mid - chord, 0.0), mid + chord
        ts = np.linspace(t0, t1, 100001)[:-1] + 0.5 * (t1 - t0) / 100000
        xs = ro + np.outer(ts, rd)
        irr, gap = Z.hazeRingIrradiance(xs, centre, normal, ring)
        v = xs - centre
        h = v @ normal
        in_plane = v - np.outer(h, normal)
        to_band = v - 12.0 * in_plane / np.linalg.norm(in_plane, axis=-1, keepdims=True)
        phase = Z.phaseHG(np.sum(rd * -to_band / np.linalg.norm(to_band, axis=-1, keepdims=True), -1), 0.6) / \
            Z.phaseIso()
        d0, d1 = Z.hazeDensity3(ro + rd * t0, 0.0, hz, 0.0), Z.hazeDensity3(ro + rd * t1, 0.0, hz, 0.0)
        sigma = d0 + (d1 - d0) * (ts - t0) / (t1 - t0)
        window = 1.0 - Z._smoothstep(0.35 * 15.0, 15.0, gap)
        ref = 40.0 * VIOLET * np.sum(sigma * irr * window * phase * np.exp(-0.035 * ts)) * (t1 - t0) / 100000
        assert np.allclose(est, ref, rtol=0.01), (target, est, ref)
    miss = np.array([0.0, -0.3, 1.0]) / np.linalg.norm([0.0, -0.3, 1.0])                 # looking away from the ring
    assert np.all(Z.hazeRing3(ro, miss, 160.0, centre, normal, ring, VIOLET, 40.0, [2.0, 0.0], hz, 0.0, 0.5) == 0.0)


def test_the_blue_noise_is_a_blue_permutation_of_256_ranks():
    xy = np.stack(np.meshgrid(np.arange(48) + 0.5, np.arange(48) + 0.5), -1)
    bn = Z.hazeBlueNoise(xy)
    assert np.all((bn > 0.0) & (bn < 1.0))
    tile = np.round(bn[:16, :16] * 256.0 - 0.5).astype(int)
    assert sorted(tile.ravel()) == list(range(256))                            # every threshold once
    assert np.array_equal(bn[:16, :16], bn[16:32, 32:48])                      # tiled every 16 pixels
    img = bn[:16, :16] - bn[:16, :16].mean()
    power = np.abs(np.fft.fft2(img)) ** 2
    f = np.hypot(*np.meshgrid(np.fft.fftfreq(16), np.fft.fftfreq(16)))
    assert power[(f > 0) & (f < 0.2)].mean() < 0.1 * power[f > 0].mean()      # little low-frequency energy: blue
    shifts = (bn[:, 1:] - bn[:, :-1]).ravel()
    assert np.mean(np.abs(shifts)) > 0.25                                      # neighbours far apart


# ------------------------------------------------------------------------------------------- GPU parity (SwiftShader)
PARITY_CARD = """//! {"card": "parity-haze", "uses": ["atmos-haze", "colour-tone", "light-glow"], "t": [0], "size": [768, 64],
//!  "note": "test fixture: twelve 64x64 panels of numbers the CPU twin recomputes; not a picture for people"}
// Apache-2.0, Akashic Aurora. A parity fixture: every pixel is a number the numpy twin recomputes.
vec3 parityShown(vec3 v) { return v / (1.0 + v); }
const vec3 PARITY_EYE = vec3(0.0, 1.7, 0.0);
const vec3 PARITY_SHEET_APEX = vec3(0.0, 0.5, -12.0);
const vec3 PARITY_SHEET_NORMAL = vec3(0.3, 0.0, -1.0);
const vec3 PARITY_SHEET_TINT = vec3(0.6, 0.2, 1.0);

vec3 parityRay(vec2 local) {
    return normalize(vec3((local.x - 32.0) / 40.0, (local.y - 20.0) / 40.0, -1.0));
}

void mainImage(out vec4 color, in vec2 pixel) {
    int panel = int(pixel.x) / 64;
    vec2 local = vec2(mod(pixel.x, 64.0), pixel.y);
    vec3 v;
    if (panel == 0) {
        vec2 p = (local / 64.0 - 0.5) * 2.0;
        v = vec3(hazeDensity(p, -0.8, vec4(3.0, 0.5, 0.05, -0.02), 3.7), hazeFloorBand(p, -0.6, 0.5, 2.3),
                 hazeStreak(p, vec2(0.1, -1.1), vec4(0.08, 0.03, 0.9, 0.02), 4.1));
    } else if (panel == 1) {
        float dens = 0.5 + 0.5 * sin(0.3 * local.x + 0.2 * local.y);
        v = parityShown(hazeBeam((local.x - 32.0) * 0.6, local.y / 64.0 * 1.12 - 0.06, vec3(0.05, 1.0, 0.15), 1.5,
                                 dens, 10.0, 1.3, 0.3));
    } else if (panel == 2) {
        float dens = 0.5 + 0.5 * cos(0.25 * local.x - 0.15 * local.y);
        v = parityShown(hazeSheet((local.x - 32.0) / 32.0 * 0.6, 0.2, local.y / 64.0 * 1.12 - 0.06,
                                  vec3(0.55, 0.1, 1.0), 0.7, dens, 0.9, 0.5));
    } else if (panel == 3) {
        vec2 p = (local - 32.0) / 16.0;
        float point = hazePoint(p, vec2(0.3, -0.2), 0.7, vec3(1.0, 0.6, 0.2), 2.0, 0.6).r;
        float pool = hazePool(p, vec2(-0.4, 0.5), vec2(1.2, 0.5), vec3(0.2, 0.5, 1.0), 1.5).b;
        vec3 frame = hazeBeamCoords(p, vec2(-1.5, -1.8), vec2(0.6, 1.0), 3.0);
        float third = local.y < 32.0 ? 0.5 + 0.2 * frame.x + 0.15 * frame.y + 0.05 * frame.z
                                     : hazePhase(local.x / 32.0 - 1.0) / 12.0;
        v = vec3(point / (1.0 + point), pool / (1.0 + pool), third);
    } else if (panel == 4) {
        float x = local.x / 64.0;
        float y = local.y / 64.0;
        if (local.y < 32.0) {
            v = parityShown(hazeTint(vec3(0.5, 0.1, 1.0) * (0.3 + 2.0 * x), 2.5 * y));
        } else if (local.x < 32.0) {
            float H = local.y < 48.0 ? 1.0 : 4.0;
            v = tmStage(vec3(4.0 * x + 0.1, x, 0.3) * (1.0 + 6.0 * (y - 0.5)), 0.6, H) / H;
        } else {
            v = parityShown(glowHotCoreTo(vec3(0.12, 0.3, 1.0), 6.0 * (x - 0.5), vec3(0.62, 0.9, 1.0)) * (y - 0.4));
        }
    } else if (panel == 5) {
        vec3 pw = vec3((local.x - 32.0) * 0.25, local.y * 0.15, -10.0);
        v = vec3(hazeDensity3(pw, 0.0, vec4(0.4, 6.0, 0.3, -0.2), 2.5),
                 hazeStreak3(pw, vec3(0.0, 9.0, -14.0), vec4(1.5, 0.05, 0.9, 0.3), 2.5),
                 hazeConeProfile(pw, vec3(0.0, 9.0, -14.0), vec3(0.1, -1.0, 0.4), 0.15));
    } else if (panel == 6) {
        vec3 rd = parityRay(local);
        float tMax = rd.y < 0.0 ? min(60.0, -1.7 / rd.y) : 60.0;
        v = parityShown(hazeCone(vec3(0.0, 1.7, 0.0), rd, tMax, vec3(2.0, 9.0, -15.0), vec3(-0.25, -1.0, 0.5), 0.12,
                                 vec3(0.25, 0.4, 1.0), 120.0, vec2(1.0, 0.0), vec4(0.4, 7.0, 0.2, 0.1),
                                 vec4(1.6, 0.05, 0.8, 0.25), 3.0, 0.37));
    } else if (panel == 7) {
        vec3 rd = parityRay(local);
        float tMax = rd.y < 0.0 ? min(60.0, -1.7 / rd.y) : 60.0;
        if (local.y < 32.0) {
            v = parityShown(hazeSheet3(PARITY_EYE, rd, tMax, PARITY_SHEET_APEX, vec3(0.0, 1.0, 0.0),
                                       PARITY_SHEET_NORMAL, 0.5, 0.03, PARITY_SHEET_TINT, 8.0, vec2(1.0, 0.0),
                                       vec4(0.4, 7.0, 0.2, 0.1), vec4(1.6, 0.05, 0.8, 0.25), 3.0));
        } else {
            v = parityShown(hazeLamp(vec3(0.0, 1.7, 0.0), rd, tMax, vec3(1.0, 3.0, -8.0), 5.0, vec3(1.0, 0.5, 0.1),
                                     30.0, vec2(1.0, 0.0), vec4(0.4, 7.0, 0.2, 0.1), 3.0, 0.61));
        }
    } else if (panel == 8) {
        float dens = 0.5 + 0.5 * sin(0.21 * local.x + 0.1 * local.y);
        if (local.y < 32.0) {
            v = parityShown(hazeBeamSwept((local.x - 32.0) * 0.7, 0.6 * local.y, 0.35, vec3(0.05, 1.0, 0.15), 1.4,
                                          dens, 9.0, 1.2, 0.3));
        } else {
            v = parityShown(hazeSheet((local.x - 32.0) / 32.0 * 0.5, 0.2, 0.3, vec3(0.22, 0.84, 1.0), 0.8, dens, 1.0,
                                      (local.y - 32.0) / 32.0));
        }
    } else if (panel == 9) {
        vec2 p = (local - 32.0) / 32.0 * 0.6;
        float dens = 0.6 + 0.4 * cos(0.17 * local.x - 0.11 * local.y);
        vec2 arc = local.y < 32.0 ? vec2(0.0, 3.2) : vec2(1.3, 1.1);
        v = parityShown(hazeRing(p, vec2(0.05, -0.02), vec4(0.3, 0.02, 0.08, 0.15), arc, vec3(0.3, 0.2, 1.0), 0.8,
                                 dens));
    } else if (panel == 10) {
        vec3 rd = parityRay(local);
        float tMax = rd.y < 0.0 ? min(60.0, -1.7 / rd.y) : 60.0;
        v = parityShown(hazeRing3(PARITY_EYE, rd, tMax, vec3(0.5, 4.0, -14.0), vec3(0.1, 0.0, 1.0), vec3(3.0, 0.15, 3.5),
                                  vec3(0.3, 0.2, 1.0), 25.0, vec2(1.0, 0.0), vec4(0.4, 7.0, 0.2, 0.1), 3.0,
                                  hazeBlueNoise(pixel)));
    } else {
        vec2 p = (local / 64.0 - 0.5) * 2.0;
        v = vec3(hazeStreak(p, vec2(-0.2, -1.2), vec4(0.05, 0.02, 1.0, 0.03), 2.2), hazeBlueNoise(pixel),
                 hazeStreak(p, vec2(0.1, 0.05), vec4(0.04, 0.05, 0.8, 0.0), 0.0));
    }
    color = vec4(v, 1.0);
}
"""


def _shown(v):
    return v / (1.0 + v)


def _twin_parity_image():
    ys, xs = np.mgrid[0:64, 0:64].astype(np.float64)
    lx, ly = xs + 0.5, ys + 0.5
    out = np.zeros((64, 768, 3))
    p = np.stack([(lx / 64.0 - 0.5) * 2.0, (ly / 64.0 - 0.5) * 2.0], -1)
    out[:, 0:64] = np.stack([Z.hazeDensity(p, -0.8, [3.0, 0.5, 0.05, -0.02], 3.7), Z.hazeFloorBand(p, -0.6, 0.5, 2.3),
                             Z.hazeStreak(p, [0.1, -1.1], [0.08, 0.03, 0.9, 0.02], 4.1)], -1)
    dens = 0.5 + 0.5 * np.sin(0.3 * lx + 0.2 * ly)
    out[:, 64:128] = _shown(Z.hazeBeam((lx - 32.0) * 0.6, ly / 64.0 * 1.12 - 0.06, [0.05, 1.0, 0.15], 1.5, dens, 10.0,
                                       1.3, 0.3))
    dens = 0.5 + 0.5 * np.cos(0.25 * lx - 0.15 * ly)
    out[:, 128:192] = _shown(Z.hazeSheet((lx - 32.0) / 32.0 * 0.6, 0.2, ly / 64.0 * 1.12 - 0.06, [0.55, 0.1, 1.0], 0.7,
                                         dens, 0.9, 0.5))
    p = np.stack([(lx - 32.0) / 16.0, (ly - 32.0) / 16.0], -1)
    point = Z.hazePoint(p, [0.3, -0.2], 0.7, [1.0, 0.6, 0.2], 2.0, 0.6)[..., 0]
    pool = Z.hazePool(p, [-0.4, 0.5], [1.2, 0.5], [0.2, 0.5, 1.0], 1.5)[..., 2]
    frame = Z.hazeBeamCoords(p, [-1.5, -1.8], [0.6, 1.0], 3.0)
    third = np.where(ly < 32.0, 0.5 + 0.2 * frame[..., 0] + 0.15 * frame[..., 1] + 0.05 * frame[..., 2],
                     Z.hazePhase(lx / 32.0 - 1.0) / 12.0)
    out[:, 192:256] = np.stack([point / (1 + point), pool / (1 + pool), third], -1)
    x, y = lx / 64.0, ly / 64.0
    tint = _shown(Z.hazeTint(np.array([0.5, 0.1, 1.0]) * (0.3 + 2.0 * x)[..., None], 2.5 * y))
    H = np.where(ly < 48.0, 1.0, 4.0)
    tm = T.tmStage(np.stack([4.0 * x + 0.1, x, np.full_like(x, 0.3)], -1) * (1.0 + 6.0 * (y - 0.5))[..., None], 0.6,
                   H) / H[..., None]
    hot = _shown(L.glowHotCoreTo3(np.array([0.12, 0.3, 1.0]), 6.0 * (x - 0.5), np.array([0.62, 0.9, 1.0]))
                 * (y - 0.4)[..., None])
    out[:, 256:320] = np.where((ly < 32.0)[..., None], tint, np.where((lx < 32.0)[..., None], tm, hot))
    pw = np.stack([(lx - 32.0) * 0.25, ly * 0.15, np.full_like(lx, -10.0)], -1)
    out[:, 320:384] = np.stack([Z.hazeDensity3(pw, 0.0, [0.4, 6.0, 0.3, -0.2], 2.5),
                                Z.hazeStreak3(pw, [0.0, 9.0, -14.0], [1.5, 0.05, 0.9, 0.3], 2.5),
                                Z.hazeConeProfile(pw, [0.0, 9.0, -14.0], [0.1, -1.0, 0.4], 0.15)], -1)
    rd = np.stack([(lx - 32.0) / 40.0, (ly - 20.0) / 40.0, -np.ones_like(lx)], -1)
    rd = rd / np.linalg.norm(rd, axis=-1, keepdims=True)
    t_max = np.where(rd[..., 1] < 0.0, np.minimum(60.0, -1.7 / np.where(rd[..., 1] < 0.0, rd[..., 1], -1.0)), 60.0)
    ro = np.array([0.0, 1.7, 0.0])
    out[:, 384:448] = _shown(Z.hazeCone(ro, rd, t_max, [2.0, 9.0, -15.0], [-0.25, -1.0, 0.5], 0.12, [0.25, 0.4, 1.0],
                                        120.0, [1.0, 0.0], [0.4, 7.0, 0.2, 0.1], [1.6, 0.05, 0.8, 0.25], 3.0, 0.37))
    sheet = _shown(Z.hazeSheet3(ro, rd, t_max, [0.0, 0.5, -12.0], [0.0, 1.0, 0.0], [0.3, 0.0, -1.0], 0.5, 0.03,
                                [0.6, 0.2, 1.0], 8.0, [1.0, 0.0], [0.4, 7.0, 0.2, 0.1], [1.6, 0.05, 0.8, 0.25], 3.0))
    lamp = _shown(Z.hazeLamp(ro, rd, t_max, [1.0, 3.0, -8.0], 5.0, [1.0, 0.5, 0.1], 30.0, [1.0, 0.0],
                             [0.4, 7.0, 0.2, 0.1], 3.0, 0.61))
    out[:, 448:512] = np.where((ly < 32.0)[..., None], sheet, lamp)
    dens = 0.5 + 0.5 * np.sin(0.21 * lx + 0.1 * ly)
    swept = _shown(Z.hazeBeamSwept((lx - 32.0) * 0.7, 0.6 * ly, 0.35, [0.05, 1.0, 0.15], 1.4, dens, 9.0, 1.2, 0.3))
    paled = _shown(Z.hazeSheet((lx - 32.0) / 32.0 * 0.5, 0.2, 0.3, [0.22, 0.84, 1.0], 0.8, dens, 1.0, (ly - 32.0) / 32.0))
    out[:, 512:576] = np.where((ly < 32.0)[..., None], swept, paled)
    p = np.stack([(lx - 32.0) / 32.0 * 0.6, (ly - 32.0) / 32.0 * 0.6], -1)
    dens = 0.6 + 0.4 * np.cos(0.17 * lx - 0.11 * ly)
    arc = np.where((ly < 32.0)[..., None], np.array([0.0, 3.2]), np.array([1.3, 1.1]))
    out[:, 576:640] = _shown(Z.hazeRing(p, [0.05, -0.02], [0.3, 0.02, 0.08, 0.15], arc, [0.3, 0.2, 1.0], 0.8, dens))
    pixel = np.stack([lx + 640.0, ly], -1)
    out[:, 640:704] = _shown(Z.hazeRing3(ro, rd, t_max, [0.5, 4.0, -14.0], [0.1, 0.0, 1.0], [3.0, 0.15, 3.5],
                                         [0.3, 0.2, 1.0], 25.0, [1.0, 0.0], [0.4, 7.0, 0.2, 0.1], 3.0,
                                         Z.hazeBlueNoise(pixel)))
    p = np.stack([(lx / 64.0 - 0.5) * 2.0, (ly / 64.0 - 0.5) * 2.0], -1)
    out[:, 704:768] = np.stack([Z.hazeStreak(p, [-0.2, -1.2], [0.05, 0.02, 1.0, 0.03], 2.2),
                                Z.hazeBlueNoise(np.stack([lx + 704.0, ly], -1)),
                                Z.hazeStreak(p, [0.1, 0.05], [0.04, 0.05, 0.8, 0.0], 0.0)], -1)
    return np.round(np.clip(out, 0, 1) * 255.0)[::-1]            # PNG rows run top down


PANELS = ("fields", "beam", "sheet", "point-pool-coords", "tint-tone-hotcore", "fields-3d", "cone", "sheet3-lamp",
          "swept-pale", "ring", "ring3", "streak-bluenoise")


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (the headless driver)")
def test_the_glsl_matches_its_twin_on_swiftshader(tmp_path):
    from PIL import Image
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "parity-haze.card").write_text(PARITY_CARD, encoding="utf-8", newline="\n")
    report = K.render_cards(["parity-haze"], cards_dir=cards_dir, out_root=tmp_path / "out", allow_tracked=True,
                            lock_wait_min=5, quiet=True)
    if report["driver"].get("error") and "lock" in str(report["driver"]["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {report['driver']['error']}")
    row = report["cards"][0]
    assert row["compile_ok"] is True and row["nan_pixels"] == 0, row
    png = sorted((tmp_path / "out" / "parity-haze").glob("t0*.png"))[0]
    gpu = np.asarray(Image.open(png).convert("RGB")).astype(np.float64)
    cpu = _twin_parity_image()
    miss = np.abs(gpu - cpu)
    for k, name in enumerate(PANELS):
        panel = miss[:, 64 * k:64 * (k + 1)]
        assert panel.max() <= 3 and np.mean(panel > 1) < 0.01, f"{name}: max {panel.max()}, " \
                                                              f"share > 1 {np.mean(panel > 1):.4f}"
