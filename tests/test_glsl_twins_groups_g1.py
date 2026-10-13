"""Pins for the first slice of the house GLSL library's GROUP recipes (shader school batch B, groups g1, 2026-10-13):
the aurora group's two P0 tiers, groups/aurora-band.glsl (painted on the sky, atlas VA 7.2 family A) and
groups/aurora-sheets.glsl (a stack of sheets over one 2D footprint, family B), and groups/glow-xray.glsl (a pass-through
march that lights everything it passes near, with the host's scene as the mapScene hook). Written BEFORE the recipes.

WHAT A GROUP IS. A recipe module (kind "recipe"): one entry function that wires library parts into a look, and a header
whose params become the Lab Inspector's knobs (arsenal/web/lib/params-ui.js over params.js). Because the recipe CALLS the
parts rather than copying them, a fix to noiseTriangle2 or auroraProfile reaches every surface that wears the look.
Hardware picture: a reference design on a datasheet, the application circuit that shows which parts to wire and with
which component values, while the parts themselves stay on the shelf.

WHY THESE PINS. Three kinds:
  - MODULE pins: each recipe is where the atlas plans it, its header carries the house fields, its one function is its
    entry, its params are the entry's trailing arguments in order (each with a label, a unit, a default, a group and a
    uniform), the descriptors pass the param schema, lint is clean, it composes for every WebGL2 target, it is built
    from the atlas's required parts (reused, never re-declared), and its hooks are declared;
  - CARD pins: each recipe's card renders it at its defaults (the card's consts ARE the header's defaults, the
    Workbench Stage's binding convention), at 480x270 for t = 0, 2 and 4;
  - TWIN pins: the promises the contracts make, measured on the CPU: black stays black below the hem, a sharp hem
    and a fading top, colour in physical order (or analogous with one coral accent), a quality tier that changes cost
    and not exposure, a lake that is the sky's mirror, glow that does not depend on the step size, a budget that acts
    as opacity. The slow test at the bottom renders a parity card on SwiftShader and compares the GLSL with the twins.

THE LOOK FIX (2026-10-13). The groups review found the aurora wrong in ways a picture shows and a number can hold: light
hanging under the band's hems (rows of hills with glowing outlines), a silver hem, the sheets' rays leaning out from the
frame's centre, a sky that reshaped in a second, IGN hatching, speckle at the knob corners and smudges at t = 0. Each
has a pin below that fails on the recipes as they were (checked against a copy of the old twin) and holds on the fix.
Recipe uniforms follow Vandor's ruling (b): u_<recipeCamel>_<param>.

Apache-2.0, Akashic Aurora. Written fresh for the house; no corpus code.
"""
from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from arsenal import params as P
from arsenal.shaders import cards as K
from arsenal.shaders import modules as M

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "arsenal" / "web" / "glsl"
ATLAS = REPO / "arsenal" / "shaders" / "atlas.json"

AURORA_TWIN = "arsenal/shaders/twins/groups_aurora.py"
GLOW_TWIN = "arsenal/shaders/twins/groups_glow.py"

# file -> the plan: module name, atlas group (and tier), category, entry signature, how many leading entry arguments
# are host inputs rather than params, the uniform prefix, the hooks the host defines, whether it takes uint seeds.
PLAN = {
    "groups/aurora-band.glsl": dict(
        name="aurora-band", group="aurora", tier="band", cat="G8", twin=AURORA_TWIN,
        entry="vec3 auroraBand(vec2 pixel, vec2 res, float clock, float intensity, float hemHeight, "
              "float curtainWidth, float fold, float rays, float fringe, int palette, float sky, int curtains, "
              "int view)",
        lead=3, prefix="u_auroraBand_", hooks=(), uint=True, cost={"C1"}),
    "groups/aurora-sheets.glsl": dict(
        name="aurora-sheets", group="aurora", tier="sheet", cat="G8", twin=AURORA_TWIN,
        entry="vec3 auroraSheets(vec2 pixel, vec2 res, vec3 ro, mat3 basis, float focal, float clock, "
              "float intensity, float hemHeight, float curtainWidth, float fold, float rays, float fringe, "
              "int palette, float sky, float lake, int layers, int view)",
        lead=6, prefix="u_auroraSheets_", hooks=("float mapScene(vec3 p)", "float densityAt(vec3 p)"), uint=True,
        cost={"C2"}),
    "groups/glow-xray.glsl": dict(
        name="glow-xray", group="glow-xray", tier=None, cat="F9", twin=GLOW_TWIN,
        entry="vec3 glowXray(vec2 pixel, vec2 res, vec3 ro, mat3 basis, float focal, int budget, float passthrough, "
              "float density, float sparkWidth, int palette, float hueSpeed, float rim, int view)",
        lead=5, prefix="u_glowXray_", hooks=("float mapScene(vec3 p)",), uint=False, cost={"C2"}),
}
NAMES = [v["name"] for v in PLAN.values()]
ENTRY_RE = re.compile(r"^\s*(\w+)\s+(\w+)\s*\((.*)\)\s*$", re.S)


def _atlas():
    return json.loads(ATLAS.read_text(encoding="utf-8"))


def _group(name):
    return next(g for g in _atlas()["groups"] if g["name"] == name)


def _tier(plan):
    g = _group(plan["group"])
    return g["tiers"][0] if plan["tier"] is None else next(t for t in g["tiers"] if t["name"] == plan["tier"])


@pytest.fixture(scope="module")
def library():
    return M.load_library(strict=False)


def _module(lib, file):
    name = PLAN[file]["name"]
    assert name in lib.modules, f"no module named {name} (expected in arsenal/web/glsl/{file}); quarantined: " \
                                f"{[p for p in lib.problems if file in str(p.get('path', '')).replace(chr(92), '/')]}"
    m = lib.modules[name]
    assert Path(m.path).resolve() == (LIB / file).resolve(), f"{name} lives in {m.path}, not {file}"
    return m


def _args(signature):
    """[(type, name)] of a GLSL signature's parameters."""
    m = ENTRY_RE.match(signature)
    assert m, signature
    out = []
    for raw in m.group(3).split(","):
        words = [w for w in raw.split() if w not in ("in", "const", "highp")]
        out.append((" ".join(words[:-1]), words[-1]))
    return m.group(1), m.group(2), out


# ============================================================================================== the modules themselves
@pytest.mark.parametrize("file", sorted(PLAN))
def test_each_recipe_is_where_the_atlas_puts_it(library, file):
    plan = PLAN[file]
    assert file in _group(plan["group"])["modules"], f"the atlas does not place {file} in group {plan['group']}"
    m = _module(library, file)
    assert m.kind == "recipe"


@pytest.mark.parametrize("file", sorted(PLAN))
def test_headers_carry_every_library_field(library, file):
    plan = PLAN[file]
    m = _module(library, file)
    h = m.header
    assert h["cat"] == plan["cat"] and h["family"] == plan["cat"][0]
    assert re.fullmatch(r"\d+\.\d+\.\d+", h["version"]) and h["order"] >= 50
    assert h["license"] == "Apache-2.0" and h.get("public", True) is True
    assert isinstance(h["credits"], list) and h["credits"] and all("http" in c for c in h["credits"]), \
        "every credit names who taught the technique, with a link"
    assert h["cost"]["class"] in plan["cost"] and h["cost"]["tex"] == 0 and h["cost"]["loop"]
    for field in ("contract", "note"):
        assert isinstance(h[field], str) and len(h[field]) > 200, field
    assert h["targets"]["glsl"] == "300es" and ("uint" in h["targets"]["needs"]) == plan["uint"]
    assert h["card"] == f"{plan['name']}.card" and (LIB / "cards" / h["card"]).is_file()
    assert h["twin"].split(":")[0] == plan["twin"] and (REPO / plan["twin"]).is_file()
    assert h["status"] == "P0"
    group_exemplars = set(_group(plan["group"])["exemplars"])
    assert h["exemplars"] and set(h["exemplars"]) <= group_exemplars
    assert h["learn"] and isinstance(h["learn"], list)
    assert isinstance(h.get("debug"), list) and h["debug"], "a group lists its debug views (atlas section 16)"


@pytest.mark.parametrize("file", sorted(PLAN))
def test_the_one_function_is_the_entry_and_matches_the_header(library, file):
    plan = PLAN[file]
    m = _module(library, file)
    assert " ".join(m.header["entry"].split()) == plan["entry"]
    _ret, fn, _ = _args(plan["entry"])
    assert m.functions == (fn,), f"{file} defines {m.functions}: a recipe is one entry (a helper would be a name " \
                                 "another module could clash with; it belongs in its family's module)"
    d = next(M.DEFINITION_RE.finditer(M.strip_comments(m.body)))
    assert f"{d.group(1)} {d.group(2)}({' '.join(d.group(3).split())})" == plan["entry"]


@pytest.mark.parametrize("file", sorted(PLAN))
def test_params_are_the_entry_tail_and_pass_the_param_schema(library, file):
    plan = PLAN[file]
    h = _module(library, file).header
    _ret, _fn, args = _args(plan["entry"])
    tail = args[plan["lead"]:]
    params = h["params"]
    assert [p["name"] for p in params] == [a[1] for a in tail], "params map one to one onto the entry's tail, in order"
    for p, (gtype, _name) in zip(params, tail):
        for field in ("name", "label", "unit", "default", "group", "uniform"):
            assert field in p, f"{p.get('name')}: no {field}"
        assert p["uniform"] == plan["prefix"] + p["name"]
        if "choices" in p:
            assert gtype == "int" and p["unit"] == "choice"
            assert [c["value"] for c in p["choices"]] == list(range(len(p["choices"]))), \
                "choice values are 0..n-1, so the Stage's index binding and the value agree"
        else:
            assert "range" in p and "step" in p and p["range"][0] <= p["default"] <= p["range"][1]
            assert gtype == ("int" if p["unit"] == "count" else "float"), p["name"]
    descriptors = P.params_from_module(h)
    assert P.check_descriptors(descriptors) == []
    assert [d["uniform"] for d in descriptors] == [p["uniform"] for p in params]
    assert P.check_descriptors(P.params_from_module(h, "inst")) == []


def _recipe_camel(name):
    head, *rest = name.split("-")
    return head + "".join(w[:1].upper() + w[1:] for w in rest)


@pytest.mark.parametrize("file", sorted(PLAN))
def test_uniforms_are_named_u_recipe_param(library, file):
    """Vandor's ruling (b), 2026-10-13: a recipe knob's uniform is u_<recipeCamel>_<param>, one rule for every group,
    so two recipes on one page never collide and a host can derive the name from the header without a table."""
    m = _module(library, file)
    for p in m.header["params"]:
        assert p["uniform"] == f"u_{_recipe_camel(m.name)}_{p['name']}", p["uniform"]


def test_the_cost_knobs_are_marked():
    marked = {}
    lib = M.load_library(strict=False)
    for file, plan in PLAN.items():
        marked[plan["name"]] = {p["name"] for p in _module(lib, file).header["params"] if p.get("cost")}
    assert marked == {"aurora-band": {"curtains"}, "aurora-sheets": {"layers"}, "glow-xray": {"budget"}}


@pytest.mark.parametrize("file", sorted(PLAN))
def test_each_recipe_lints_clean_and_composes_for_every_webgl2_target(library, file):
    m = _module(library, file)
    assert M.lint(m, library_module=True, library=library) == []
    for target in ("toy", "webgl2", "three-r186"):
        text = library.compose([m.name], target=target)
        assert m.name in text.splitlines()[0]


@pytest.mark.parametrize("file", sorted(PLAN))
def test_each_recipe_is_wired_from_the_atlas_parts(library, file):
    """Every required part of the tier is reached (the recipe or a part it calls provides it), and of each pair of
    alternatives at least one; the recipe calls the parts, it never copies them. The display curve at the end of a
    chain ('tmRootGain or tmTanh through finish') belongs to the host's finish, so the recipe's card may supply it."""
    plan = PLAN[file]
    m = _module(library, file)
    reach = {fn for n in library.resolve([m.name]) for fn in library.modules[n].provides}
    card_reach = {fn for n in K.build_card(K.load_card(m.name), library=library)["card"]["modules"]
                  for fn in library.modules[n].provides}
    finish = {"tmRootGain", "tmTanh", "displayOut"}
    tier = _tier(plan)
    missing = sorted(set(tier["required"]) - reach)
    assert not missing, f"{plan['name']} does not reach the tier's required parts {missing}"
    for alternatives in tier["alternatives"]:
        names = {fn for alt in alternatives for fn in alt}
        seen = reach | (card_reach if names <= finish else set())
        assert any(set(alt) <= seen for alt in alternatives), f"none of {alternatives} is used"
    code = M.strip_comments(m.body)
    assert not re.search(r"\bconst\s+float\s+(PI|TAU|PHI|SQRT3)\b", code), "PI and TAU come from core-const"
    assert "hashSine" not in code and not re.search(r"\bsin\s*\(\s*dot", code), "hashes come from hash-pcg"
    assert not re.search(r"^\s*uniform\b", code, re.M), "the entry takes its params as arguments; hosts bind them"


@pytest.mark.parametrize("file", sorted(PLAN))
def test_each_recipe_declares_the_hooks_its_host_must_define(library, file):
    plan = PLAN[file]
    m = _module(library, file)
    assert tuple(sorted(m.hooks)) == tuple(sorted(plan["hooks"]))
    assert m.header["cost"].get("hooks", 0) == len(plan["hooks"])
    text = library.compose([m.name], target="toy")
    for proto in plan["hooks"]:
        assert text.count(proto + ";") == 1, f"{proto} emitted {text.count(proto + ';')} times"


def test_the_aurora_tiers_share_one_palette_choice_and_debug_vocabulary(library):
    band = _module(library, "groups/aurora-band.glsl").header
    sheets = _module(library, "groups/aurora-sheets.glsl").header
    pal = [next(p for p in h["params"] if p["name"] == "palette")["choices"] for h in (band, sheets)]
    assert pal[0] == pal[1], "one palette menu for both tiers, so a look can move between them"
    assert [c["label"].split(" ")[0] for c in pal[0]][:2] == ["House", "Physical"]


# ============================================================================================================ cards
@pytest.mark.parametrize("name", NAMES)
def test_each_card_drives_its_recipe_at_the_header_defaults(library, name):
    file = next(f for f, p in PLAN.items() if p["name"] == name)
    h = _module(library, file).header
    card = K.load_card(name)
    assert name in card.uses and len(card.note) > 200
    assert card.size == (480, 270) and {0.0, 2.0, 4.0} <= set(card.times)
    body = M.strip_comments(card.body)
    _ret, fn, _ = _args(PLAN[file]["entry"])
    assert re.search(rf"\b{fn}\s*\(", body), f"the card never calls {fn}"
    for p in h["params"]:
        m = re.search(rf"^\s*const\s+(float|int)\s+{p['uniform']}\s*=\s*([^;]+);", body, re.M)
        assert m, f"the card holds no const {p['uniform']} (the Stage binds a knob by replacing it)"
        kind, value = m.group(1), float(m.group(2))
        assert kind == ("int" if ("choices" in p or p["unit"] == "count") else "float")
        assert value == pytest.approx(float(p["default"])), f"{p['uniform']} = {value}, the header says {p['default']}"
        assert re.search(rf"\b{p['uniform']}\b", body.split(m.group(0), 1)[1]), f"{p['uniform']} is never passed on"
    built = K.build_card(card, library=library)
    assert name in built["card"]["modules"]


# ========================================================================================================= the twins
def _aurora():
    from arsenal.shaders.twins import groups_aurora
    return groups_aurora


def _glow():
    from arsenal.shaders.twins import groups_glow
    return groups_glow


def _defaults(file):
    lib = M.load_library(strict=False)
    return {p["name"]: p["default"] for p in _module(lib, file).header["params"]}


def _grid(w, h):
    ys, xs = np.mgrid[0:h, 0:w]
    return np.stack([xs + 0.5, ys + 0.5], -1).astype(np.float64)


def _band(pixels, res, clock, **over):
    a = _aurora()
    k = dict(_defaults("groups/aurora-band.glsl"))
    k.update(over)
    return a.auroraBand(pixels, res, clock, k["intensity"], k["hemHeight"], k["curtainWidth"], k["fold"], k["rays"],
                        k["fringe"], k["palette"], k["sky"], k["curtains"], k["view"])


def test_twin_params_match_the_headers():
    """The twins carry the recipes' constants; the header defaults are the ones the twins are pinned at. Both tiers
    default to the physical palette (a green body under a red crown, what a real aurora looks like) with no energetic
    fringe, and the sheets to 36 layers (the count at which their stepping is faint grain)."""
    a = _aurora()
    for file in ("groups/aurora-band.glsl", "groups/aurora-sheets.glsl"):
        d = _defaults(file)
        assert d["palette"] == a.PHYSICAL == 1 and d["view"] == 0 and d["fringe"] == 0
    assert _defaults("groups/aurora-sheets.glsl")["layers"] == 36
    assert len(a.PALETTES) == 3 and all(len(v) == 3 for v in a.PALETTES[:1] + a.PALETTES[2:])
    assert a.PALETTES[1] is None, "palette 1 is the physical one: auroraLineColor, not a ramp"


LUMA = np.array([0.2126, 0.7152, 0.0722])


def _finished(lin):
    """The cards' house tail without the vignette and the dither: tmSuperlinear at 0.85, tanh, the sRGB encode."""
    from arsenal.shaders.twins import colour as C
    from arsenal.shaders.twins import tone as TN
    return np.asarray(C.srgbEncode(np.clip(TN.tmTanh(TN.tmSuperlinear(lin, 0.85)), 0.0, 1.0)), dtype=np.float64)


def _curtain_colours(tier, res, clock, **over):
    """The finished colour of every pixel where the curtain, not the sky, is the light: its own light above 3 per cent
    of the frame's brightest and five times the sky behind it."""
    lit = tier(_grid(int(res[0]), int(res[1])), res, clock, **over)
    sky = tier(_grid(int(res[0]), int(res[1])), res, clock, **dict(over, intensity=0.0))
    own = (lit - sky) @ LUMA
    mask = (own > 0.03 * own.max()) & (own > 5.0 * (sky @ LUMA))
    return _finished(lit)[mask]


def _saturation(rgb):
    top = rgb.max(-1)
    return (top - rgb.min(-1)) / np.maximum(top, 1e-9)


# ---- aurora band
RES = np.array([160.0, 90.0])


def test_band_is_finite_non_negative_and_a_pure_function_of_its_inputs():
    px = _grid(160, 90)
    for clock in (0.0, 7.3, 1234.5):
        c = _band(px, RES, clock)
        assert c.shape == (90, 160, 3) and np.all(np.isfinite(c)) and c.min() >= 0.0
        assert np.array_equal(c, _band(px, RES, clock)), "no hidden state, no clock in a hash"


def test_band_nothing_glows_below_its_hem():
    """Review 2026-10-13, band defect 1: the hem's line of light was symmetric about the hem, so 44 to 77 per cent of
    its peak hung just below it and the curtains read as two rows of hills with glowing outlines. The lower edge is
    where the falling electrons stop: below every curtain's (ragged) edge the recipe adds exactly nothing, at any
    height, count, palette or fringe, and the sky shows through unchanged."""
    a = _aurora()
    px = _grid(160, 90)
    y = (2.0 * px[..., 1] - RES[1]) / RES[1]
    x = (2.0 * px[..., 0] - RES[0]) / RES[1]
    for hem_height, curtains, clock, over in ((0.6, 1, 3.0, {}), (0.6, 2, 0.0, {}), (1.2, 3, 7.7, {}),
                                              (0.9, 2, 2.0, dict(fringe=1.0)), (0.9, 2, 2.0, dict(palette=0))):
        lit = _band(px, RES, clock, hemHeight=hem_height, curtains=curtains, **over)
        sky = _band(px, RES, clock, hemHeight=hem_height, curtains=curtains, intensity=0.0, **over)
        lowest = np.min([a.bandHemLine(x, clock, hem_height, 1.0, RES[0] / RES[1], k)
                         - a.bandRag(x, RES[0] / RES[1], k) for k in range(curtains)], axis=0)
        below = y < lowest
        assert below.mean() > 0.1
        assert np.array_equal(lit[below], sky[below]), "light below the hem: the outline is back"
        assert np.all(lit >= sky), "an aurora only adds light (optically thin): stars show through it"
    assert np.all(_band(px, RES, 3.0, sky=0.0, intensity=0.0) == 0.0), "sky 0 and intensity 0 is pure black"


def test_band_hem_is_sharp_and_the_top_fades():
    """Brightness against the height above the local hem, averaged along one curtain: none at all below the ragged
    edge, half its peak within a short climb, a long soft fade above (auroraProfile seen through the fabric, plus the
    lower border's own thin bright layer)."""
    a = _aurora()
    res = np.array([1600.0, 900.0])
    xs = np.linspace(-1.7, 1.7, 400)
    above = np.linspace(-0.2, 1.2, 141)
    hem = a.bandHemLine(xs, 5.0, 1.0, 1.0, res[0] / res[1])
    p = np.stack(np.broadcast_arrays(xs[None, :], hem[None, :] + above[:, None]), -1)
    pixel = (p * res[1] + res) / 2.0
    light = _band(pixel, res, 5.0, hemHeight=1.0, sky=0.0, rays=0.0, curtains=1).sum(-1).mean(-1)
    peak = light.max()
    assert np.all(light[above < -0.03] == 0.0), "nothing below the ragged edge"
    rise = above[np.argmax(light > 0.5 * peak)]
    assert -0.03 < rise < 0.06, f"the hem takes {rise:.3f} frame units to reach half its peak"
    assert light[above > 0.9].max() < 0.2 * peak, "the top fades"


def test_band_physical_palette_is_green_under_red():
    a = _aurora()
    alts = np.linspace(106.0, 300.0, 60)
    hue = a.bandHue(alts, palette=1)
    redness = hue[:, 0] / np.maximum(hue[:, 1], 1e-9)
    assert np.all(np.diff(redness) >= -1e-12) and redness[0] < 0.3 and redness[-1] > 3.0


def _hue_deg(lin):
    from arsenal.shaders.twins import colour as C
    lab = C.oklabFromLinear(np.asarray(lin, dtype=np.float64))
    return np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360.0


def test_band_house_palette_is_analogous_with_one_coral_accent():
    """The shader-craft ceiling: neighbours on the wheel, never a rainbow; two cool against one warm, and the warm one
    is the house's own coral token. Review 2026-10-13, band defect 2: the coral fringe straddled the hem and added to
    the ice cyan on the same pixels, a near-complement, so the hem read silver. The fringe is now an emitter of its own
    in a thin layer at the bottom, and the body begins where it ends: the two never light the same altitude."""
    a = _aurora()
    alts = np.linspace(106.5, 300.0, 120)
    cool = _hue_deg(a.bandHue(alts, palette=0))
    assert np.all((cool > 180.0) & (cool < 300.0)) and np.ptp(cool) < 100.0, (cool.min(), cool.max())
    token = np.array([0xE0, 0x72, 0x4F]) / 255.0                       # --wb-coral, arsenal/web/lib/workbench
    from arsenal.shaders.twins import colour as C
    assert np.allclose(C.srgbEncode(a.CORAL), token, atol=0.002), "the accent is the house coral token"
    assert np.all((_hue_deg(a.CORAL) > 20.0) & (_hue_deg(a.CORAL) < 50.0)), "coral: a warm orange-pink"
    from arsenal.shaders.twins import atmos as AT
    z = np.linspace(-5.0, 60.0, 6501)
    for fringe in (0.1, 0.35, 1.0):
        low = a.fringeEmission(z, fringe)
        body = AT.auroraProfile(z, a.fringeKm(fringe), a.BAND_SCALE_H)
        assert low.max() > 0.0 and np.all(low[z > a.fringeKm(fringe)] == 0.0) and np.all(low[z <= 0.0] == 0.0)
        assert np.all(low * body == 0.0), "the fringe and the body never share an altitude"
    assert np.all(a.fringeEmission(z, 0.0) == 0.0), "no fringe asked, none drawn"


def test_aurora_is_never_silver_and_never_blown_to_white():
    """Review 2026-10-13, band defect 2 (hem saturation 0.09 to 0.30 in the PNG) and the brief: no silver, never blown
    to white. Measured in the finished picture (the cards' superlinear highlight and tanh), over every pixel the curtain
    lights: the physical and chromatic palettes keep their colour (the least saturated two per cent above 0.6, no pixel
    whose weakest channel passes 0.35); the house palette, whose ice cyan is pale by design, keeps the least saturated
    two per cent above 0.4 and every weakest channel under 0.8."""
    res = np.array([240.0, 135.0])
    cases = [(_band, {}, "physical"), (_band, dict(palette=2), "chromatic"), (_band, dict(fringe=1.0), "physical"),
             (_band, dict(palette=0), "house"), (_band, dict(palette=0, fringe=1.0), "house"),
             (_sheets, {}, "physical"), (_sheets, dict(palette=2), "chromatic"), (_sheets, dict(palette=0), "house")]
    for tier, over, kind in cases:
        for clock in (0.0, 4.0):
            rgb = _curtain_colours(tier, res, clock, **over)
            sat, white = np.percentile(_saturation(rgb), 2), rgb.min(-1).max()
            floor, ceiling = (0.4, 0.8) if kind == "house" else (0.6, 0.35)
            assert sat > floor and white < ceiling, (tier.__name__, over, clock, round(sat, 3), round(white, 3))


def test_band_intensity_scales_the_light_through_the_hue_safe_lift():
    """The glow lift (displayHueSafeGamma) bends magnitude only: doubling the intensity multiplies the aurora's light
    by exactly 2^(1/gamma), and never turns its hue."""
    a = _aurora()
    px = _grid(80, 45)
    res = np.array([80.0, 45.0])
    one = _band(px, res, 2.0, sky=0.0, intensity=1.0)
    two = _band(px, res, 2.0, sky=0.0, intensity=2.0)
    lit = one.sum(-1) > 1e-6
    assert lit.mean() > 0.1
    assert np.allclose(two[lit], one[lit] * 2.0 ** (1.0 / a.BAND_GLOW_GAMMA), rtol=1e-9)


def _frame_corr(tier, res, t0, t1):
    px = _grid(int(res[0]), int(res[1]))
    x, y = tier(px, res, t0, sky=0.0).sum(-1).ravel(), tier(px, res, t1, sky=0.0).sum(-1).ravel()
    return np.corrcoef(x, y)[0, 1]


def test_band_drifts_slowly_never_freezes_and_never_visibly_loops():
    res = np.array([120.0, 68.0])
    assert _frame_corr(_band, res, 10.0, 10.05) > 0.97, "a twentieth of a second later the curtain has barely moved"
    assert _frame_corr(_band, res, 10.0, 11.0) > 0.88, "a second later it is the same curtain"
    assert _frame_corr(_band, res, 10.0, 400.0) < 0.6, "minutes later it is another curtain"
    late = [_frame_corr(_band, res, 10.0, 10.0 + lag) for lag in range(20, 620, 50)]
    assert max(late) < 0.7, f"incommensurate rates: no lag from 20 s to 10 min brings the picture back ({late})"


def test_band_debug_views_are_what_their_names_say():
    px = _grid(80, 45)
    res = np.array([80.0, 45.0])
    fabric = _band(px, res, 2.0, view=1)
    assert np.allclose(fabric[..., 0], fabric[..., 1]) and np.allclose(fabric[..., 1], fabric[..., 2]), "grey"
    assert fabric.max() > 0.0
    bands = _band(px, res, 2.0, view=2)
    assert np.all(np.isfinite(bands)) and bands.max() > 0.0


# ---- aurora sheets
def _sheets(pixels, res, clock, ro=(0.0, 0.0, 0.0), target=(0.0, 0.22, -1.0), focal=1.8, **over):
    a = _aurora()
    from arsenal.shaders.twins import ray as R
    k = dict(_defaults("groups/aurora-sheets.glsl"))
    k.update(over)
    basis = R.camLookAt(np.array(ro, dtype=np.float32), np.array(target, dtype=np.float32), 0.0)
    return a.auroraSheets(pixels, res, np.array(ro), basis, focal, clock, k["intensity"], k["hemHeight"],
                          k["curtainWidth"], k["fold"], k["rays"], k["fringe"], k["palette"], k["sky"], k["lake"],
                          k["layers"], k["view"])


SRES = np.array([96.0, 54.0])


def test_sheets_are_finite_non_negative_and_static_per_pixel():
    px = _grid(96, 54)
    c = _sheets(px, SRES, 4.0)
    assert c.shape == (54, 96, 3) and np.all(np.isfinite(c)) and c.min() >= 0.0
    assert np.array_equal(c, _sheets(px, SRES, 4.0)), "the jitter is a function of the pixel alone"


def test_sheets_a_quality_tier_changes_cost_not_exposure():
    px = _grid(96, 54)
    means = {n: _sheets(px, SRES, 4.0, sky=0.0, layers=n).mean() for n in (16, 36, 48)}
    assert means[36] > 0.0
    for n in (16, 48):
        assert abs(means[n] / means[36] - 1.0) < 0.2, means


def test_sheets_rays_stand_straight_up_their_curtains(monkeypatch):
    """Review 2026-10-13, sheets defect 1: the rays were read once per pixel, where its ray meets the hem's sheet, so a
    world column's ray factor changed as it climbed the stack (the same column is met on each sheet by a different
    pixel, whose hem point lies elsewhere) and the rays leaned outward from the centre of the frame. A ray belongs to
    its column: every sheet reads the rays at the plan point where that sheet is met (9 rays per curtain width along
    x), so the factor is a function of the world column alone and the ray stands straight up the curtain."""
    a = _aurora()
    from arsenal.shaders.twins import ray as R
    from arsenal.shaders.twins import volume as V
    calls = []
    real = a.A.auroraRays

    def spy(along, t, seed):
        calls.append(np.array(along, dtype=np.float64, copy=True))
        return real(along, t, seed)
    monkeypatch.setattr(a.A, "auroraRays", spy)
    res = np.array([96.0, 54.0])
    px = np.array([[x, y] for x in (5.5, 30.5, 61.5, 90.5) for y in (20.5, 33.5, 50.5)])
    d = _defaults("groups/aurora-sheets.glsl")
    _sheets(px, res, 4.0, view=4)                                        # jitter off: each sheet at its own height
    hem, count = d["hemHeight"], d["layers"]
    assert len(calls) == count, "one read of the rays per sheet, none once per pixel"
    basis = R.camLookAt(np.zeros(3, np.float32), np.array([0.0, 0.22, -1.0], np.float32), 0.0)
    look = a._cam_ray(px, res, basis, 1.8)
    spacing = a.SHEET_TOP * hem / float(count - 1) ** a.SHEET_POWER
    for i, along in enumerate(calls):
        h = V.marchStepPoly(i, hem, spacing, a.SHEET_POWER)
        plan_x = look[:, 0] * h / (2.0 * look[:, 1] + 0.4)                # where this sheet is met, eye at the origin
        assert np.allclose(along, a.SHEET_RAYS[0] * plan_x / d["curtainWidth"], rtol=1e-9, atol=1e-9), i


def test_sheets_drift_slowly_never_freeze_and_never_visibly_loop():
    """Review 2026-10-13, sheets defect 2: the sky reshaped in about a second (frame correlation 0.71 at half a second,
    0.37 at one). Slow churn, slow rays, arcs that drift."""
    res = np.array([120.0, 68.0])
    assert _frame_corr(_sheets, res, 10.0, 10.5) > 0.95
    assert _frame_corr(_sheets, res, 10.0, 11.0) > 0.9, "a second later it is the same sky"
    assert _frame_corr(_sheets, res, 10.0, 300.0) < 0.6, "minutes later it is another sky"
    late = [_frame_corr(_sheets, res, 10.0, 10.0 + lag) for lag in range(20, 620, 50)]
    assert max(late) < 0.7, f"no lag from 20 s to 10 min brings the picture back ({late})"


def test_sheets_stepping_is_faint_grain_not_hatching(monkeypatch):
    """Review 2026-10-13, sheets defect 3: at the default layers the static IGN jitter showed as a regular diagonal
    hatching. Against the converged stack (the same stack averaged over 8 even jitter values), the picture's error is
    under 2 codes of 8 bits (RMS over the curtain) and has no structure a neighbour can predict."""
    a = _aurora()
    res = np.array([240.0, 135.0])
    px = _grid(240, 135)
    pic = _finished(_sheets(px, res, 4.0, sky=0.0, lake=0.0)) @ LUMA
    ref = 0.0
    for j in range(8):
        monkeypatch.setattr(a, "sheetJitter", lambda pixel, j=j: np.full(np.shape(pixel)[:-1], (j + 0.5) / 8.0))
        ref = ref + _finished(_sheets(px, res, 4.0, sky=0.0, lake=0.0)) @ LUMA / 8.0
    lit = ref > 0.05 * ref.max()
    err = np.where(lit, pic - ref, 0.0)
    assert 255.0 * np.sqrt(np.mean(err[lit] ** 2)) < 2.0
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1), (0, 2), (2, 0), (2, 1), (1, 2), (0, 3), (3, 0)):
        both = lit & np.roll(np.roll(lit, dy, 0), dx, 1)
        r = np.corrcoef(err[both], np.roll(np.roll(err, dy, 0), dx, 1)[both])[0, 1]
        assert abs(r) < 0.25, f"the error at offset ({dy}, {dx}) predicts its neighbour: r = {r:.2f}"


def test_sheets_fine_creases_blur_instead_of_aliasing():
    """Review 2026-10-13, sheets defect 4: the picture depends on hem height over curtain width, and past about 5 the
    creases went under a pixel and the knob ranges reached a speckle mess. The footprint now fades its creases and
    widens its arcs by the plan depth a pixel spans, and the ranges stop at 6.25: at every corner of the knobs, one
    sample a pixel agrees with nine (3 x 3, box) to within 8 per cent of the curtain's light."""
    lib = M.load_library(strict=False)
    knobs = {p["name"]: p for p in _module(lib, "groups/aurora-sheets.glsl").header["params"]}
    hems, widths = knobs["hemHeight"]["range"], knobs["curtainWidth"]["range"]
    assert hems[1] / widths[0] <= 6.25
    res = np.array([160.0, 90.0])
    ys, xs = np.mgrid[0:270, 0:480]
    fine = np.stack([(xs + 0.5) / 3.0, (ys + 0.5) / 3.0], -1)
    for hem in hems:
        for width in widths:
            over = dict(view=4, sky=0.0, lake=0.0, hemHeight=hem, curtainWidth=width)
            one = _finished(_sheets(_grid(160, 90), res, 4.0, **over)) @ LUMA
            many = (_finished(_sheets(fine, res, 4.0, **over)) @ LUMA).reshape(90, 3, 160, 3).mean(axis=(1, 3))
            lit = many > 0.02
            error = np.mean(np.abs(one - many)[lit]) / np.mean(many[lit])
            assert error < 0.08, (hem, width, round(float(error), 3))


def test_sheets_every_frame_shows_arcs_across_the_sky():
    """Review 2026-10-13, sheets defect 5: the default t = 0 frame read as scattered smudges with a dark eye. The
    footprint is now a few long arcs (lines of constant depth, meandering) carrying the filament field's creases: at any
    time the curtains (rays off, so the gaps between rays do not count) light nearly every column of the sky."""
    res = np.array([240.0, 135.0])
    px = _grid(240, 135)
    for clock in (0.0, 2.0, 4.0, 37.0):
        light = _sheets(px, res, clock, sky=0.0, lake=0.0, rays=0.0).sum(-1)
        columns = light.max(0)
        assert np.mean(columns > 0.1 * columns.max()) > 0.9, clock


def test_sheets_below_the_horizon_mirror_the_sky_in_the_lake():
    """lake 0: below the horizon is the sky's own horizon colour (a host draws its ground); lake k: the curtains and
    sky above the horizon, mirrored, times k. A level camera on the water sees each pixel's mirror twin exactly (with
    the static jitter off: it belongs to the pixel, not the direction)."""
    res = np.array([64.0, 64.0])
    px = _grid(64, 64)
    level = dict(target=(0.0, 0.0, -1.0), focal=1.2, view=4)
    k = 0.6
    mirrored = _sheets(px, res, 4.0, lake=k, **level)
    plain = _sheets(px, res, 4.0, lake=0.0, **level)
    top, bottom = mirrored[32:], mirrored[:32][::-1]        # rows run bottom up: row 32 + i mirrors row 31 - i
    assert np.allclose(bottom, k * top, rtol=1e-6, atol=1e-9)
    sky_only = _sheets(px, res, 4.0, lake=0.0, intensity=0.0, **level)
    assert np.allclose(plain[:32], sky_only[:32]), "no lake, no curtain below the horizon"
    assert mirrored[32:].max() > 1.5 * sky_only[32:].max(), "there is a curtain above to mirror"


def test_sheets_colour_climbs_the_stack_in_order():
    a = _aurora()
    px = _grid(96, 54)
    idx = _sheets(px, SRES, 4.0, view=1)
    assert np.all(np.isfinite(idx)) and idx.max() > 0.0
    fr = np.linspace(0.0, 1.0, 50)
    house = a.sheetHue(fr, palette=0)
    hue = _hue_deg(house)
    assert np.all(np.diff(hue) > -1e-9) and np.ptp(hue) < 100.0, "hem to top climbs the wheel one way, analogous"
    phys = a.sheetHue(fr, palette=1)
    assert phys[0, 1] > phys[0, 0] and phys[-1, 0] > phys[-1, 1], "green at the hem, red at the top"


def test_sheets_debug_views_differ_from_the_picture_where_promised():
    px = _grid(96, 54)
    pic = _sheets(px, SRES, 4.0)
    no_avg = _sheets(px, SRES, 4.0, view=3)
    no_jit = _sheets(px, SRES, 4.0, view=4)
    foot = _sheets(px, SRES, 4.0, view=2)
    assert not np.allclose(pic, no_avg) and not np.allclose(pic, no_jit)
    assert np.allclose(foot[..., 0], foot[..., 1]) and foot.max() > 0.0, "the footprint alone is a grey field"


# ---- glow-xray
def _shell_scene(p):
    """A ball's skin (an onion of a sphere of radius 0.8, 0.02 thick) and a ring around it, centred at the origin."""
    p = np.asarray(p, dtype=np.float64)
    ball = np.abs(np.linalg.norm(p, axis=-1) - 0.8) - 0.02
    ring = np.hypot(np.hypot(p[..., 0], p[..., 2]) - 1.3, p[..., 1]) - 0.05
    return np.minimum(ball, ring)


def _xray(pixels, res, scene=_shell_scene, ro=(0.0, 0.6, 4.0), **over):
    g = _glow()
    from arsenal.shaders.twins import ray as R
    k = dict(_defaults("groups/glow-xray.glsl"))
    k.update(over)
    basis = R.camLookAt(np.array(ro, dtype=np.float32), np.zeros(3, np.float32), 0.0)
    return g.glowXray(pixels, res, np.array(ro), basis, 2.0, k["budget"], k["passthrough"], k["density"],
                      k["sparkWidth"], k["palette"], k["hueSpeed"], k["rim"], k["view"], scene)


XRES = np.array([64.0, 48.0])


def test_xray_is_finite_non_negative_and_dark_where_nothing_is_near():
    px = _grid(64, 48)
    c = _xray(px, XRES)
    assert np.all(np.isfinite(c)) and c.min() >= 0.0 and c.max() > 0.1
    corners = np.concatenate([c[:4, :4].ravel(), c[-4:, -4:].ravel()])
    assert corners.max() < 0.02 * c.max(), "a ray that passes nothing gathers (almost) nothing"


def test_xray_glow_is_an_integral_not_a_step_count():
    """glowEmitStep weights each step by its length, so a finer march gathers the same light (the 1/d-per-step
    alternative would brighten as the steps shrink)."""
    px = _grid(48, 36)
    res = np.array([48.0, 36.0])
    coarse = _xray(px, res, passthrough=0.008, budget=160, rim=0.0)
    fine = _xray(px, res, passthrough=0.004, budget=160, rim=0.0)
    assert abs(fine.sum() / coarse.sum() - 1.0) < 0.12


def test_xray_the_budget_is_the_opacity():
    px = _grid(48, 36)
    res = np.array([48.0, 36.0])
    light = [_xray(px, res, budget=b, rim=0.0).sum(-1) for b in (24, 48, 96, 160)]
    for a, b in zip(light, light[1:]):
        assert np.all(b >= a - 1e-12), "more budget never dims a pixel"
    assert light[0].sum() < 0.9 * light[-1].sum(), "a short budget stops rays before the back of the scene"


def test_xray_hue_encodes_depth():
    g = _glow()
    flat = g.xrayHue(np.array([-1.0, 1.0]), 0, 0.0)
    assert np.allclose(flat[0], flat[1]), "hue speed 0: one colour at every depth"
    moving = g.xrayHue(np.array([-1.0, 1.0]), 0, 0.35)
    assert not np.allclose(moving[0], moving[1]), "front and back walls take different colours"
    near = _hue_deg(g.xrayHue(np.linspace(-0.8, 0.8, 41), 0, 0.35))
    assert np.all((near > 240.0) & (near < 345.0)), "the house palette is cool around the scene's centre"
    assert np.all(g.xrayHue(np.linspace(-8.0, 8.0, 400), 0, 0.35) >= 0.0)


def test_xray_steps_view_is_the_heat_of_the_loop():
    from arsenal.shaders.twins import core as C
    px = _grid(32, 24)
    res = np.array([32.0, 24.0])
    heat = _xray(px, res, view=1)
    steps = _glow().xraySteps(px, res, np.array((0.0, 0.6, 4.0)), _basis((0.0, 0.6, 4.0)), 2.0,
                              96, 0.012, 3.0, _shell_scene)
    assert steps.shape == (24, 32) and steps.min() >= 1 and steps.max() <= 96
    assert np.allclose(heat, C.dbgHeatCount(steps, 96.0))


def _basis(ro):
    from arsenal.shaders.twins import ray as R
    return R.camLookAt(np.array(ro, dtype=np.float32), np.zeros(3, np.float32), 0.0)


# =========================================================================================== the GPU against the twin
PARITY_CARD = """\
//! {"card": "parity-groups-g1", "uses": ["aurora-band", "aurora-sheets", "glow-xray"], "t": [0], "size": [800, 90],
//!  "note": "Not a house card: the g1 groups' parity pattern, five 160x90 panels compared pixel by pixel with the
//!  CPU twins (tanh of the scene light, no finish): the band and the sheets at their defaults with a fringe, the
//!  x-ray, then the band in the house palette with three curtains and a full fringe, and the sheets' footprint view."}
// Apache-2.0, Akashic Aurora. Written fresh for the parity test.
float densityAt(vec3 p) { return 0.0; }
float mapScene(vec3 p) {
    float ball = abs(length(p) - 0.8) - 0.02;
    float ring = length(vec2(length(p.xz) - 1.3, p.y)) - 0.05;
    return min(ball, ring);
}
void mainImage(out vec4 color, in vec2 pixel) {
    int panel = int(pixel.x) / 160;
    vec2 local = pixel - vec2(160.0 * float(panel), 0.0);
    vec2 res = vec2(160.0, 90.0);
    vec3 sheetsEye = vec3(0.0);
    mat3 sheetsBasis = camLookAt(sheetsEye, vec3(0.0, 0.22, -1.0), 0.0);
    vec3 c;
    if (panel == 0) {
        c = auroraBand(local, res, 5.0, 1.2, 0.6, 1.0, 0.5, 0.75, 0.5, 1, 1.0, 2, 0);
    } else if (panel == 1) {
        c = auroraSheets(local, res, sheetsEye, sheetsBasis, 1.8, 4.0, 1.2, 1.0, 0.8, 0.5, 0.8, 0.5, 1, 1.0, 0.55, 36,
                         0);
    } else if (panel == 2) {
        vec3 ro = vec3(0.0, 0.6, 4.0);
        c = glowXray(local, res, ro, camLookAt(ro, vec3(0.0), 0.0), 2.0, 96, 0.012, 3.0, 0.015, 0, 0.35, 0.35, 0);
    } else if (panel == 3) {
        c = auroraBand(local, res, 37.0, 1.0, 0.9, 0.7, 0.8, 1.0, 1.0, 0, 1.0, 3, 0);
    } else {
        c = auroraSheets(local, res, sheetsEye, sheetsBasis, 1.8, 9.0, 1.2, 1.6, 0.5, 0.9, 0.8, 0.0, 1, 1.0, 0.55, 36,
                         2);
    }
    color = vec4(tanh(clamp(c, 0.0, 10.0)), 1.0);
}
"""


def _twin_parity_image():
    a, g = _aurora(), _glow()
    from arsenal.shaders.twins import ray as R
    res = np.array([160.0, 90.0])
    px = _grid(160, 90)
    out = np.zeros((90, 800, 3))
    out[:, 0:160] = a.auroraBand(px, res, 5.0, 1.2, 0.6, 1.0, 0.5, 0.75, 0.5, 1, 1.0, 2, 0)
    eye = np.zeros(3)
    basis = R.camLookAt(eye.astype(np.float32), np.array([0.0, 0.22, -1.0], np.float32), 0.0)
    out[:, 160:320] = a.auroraSheets(px, res, eye, basis, 1.8, 4.0, 1.2, 1.0, 0.8, 0.5, 0.8, 0.5, 1, 1.0, 0.55, 36, 0)
    ro = np.array([0.0, 0.6, 4.0])
    out[:, 320:480] = g.glowXray(px, res, ro, _basis(ro), 2.0, 96, 0.012, 3.0, 0.015, 0, 0.35, 0.35, 0, _shell_scene)
    out[:, 480:640] = a.auroraBand(px, res, 37.0, 1.0, 0.9, 0.7, 0.8, 1.0, 1.0, 0, 1.0, 3, 0)
    out[:, 640:800] = a.auroraSheets(px, res, eye, basis, 1.8, 9.0, 1.2, 1.6, 0.5, 0.9, 0.8, 0.0, 1, 1.0, 0.55, 36, 2)
    return np.round(np.tanh(np.clip(out, 0.0, 10.0)) * 255.0)[::-1]       # PNG rows run top down


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (the headless driver)")
def test_the_glsl_matches_its_twins_on_swiftshader(tmp_path):
    from PIL import Image
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "parity-groups-g1.card").write_text(PARITY_CARD, encoding="utf-8", newline="\n")
    report = K.render_cards(["parity-groups-g1"], cards_dir=cards_dir, out_root=tmp_path / "out",
                            allow_tracked=True, lock_wait_min=5, quiet=True)
    if report["driver"].get("error") and "lock" in str(report["driver"]["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {report['driver']['error']}")
    row = report["cards"][0]
    assert row["compile_ok"] is True and row["nan_pixels"] == 0, row
    png = sorted((tmp_path / "out" / "parity-groups-g1").glob("t0*.png"))[0]
    gpu = np.asarray(Image.open(png).convert("RGB")).astype(np.float64)
    cpu = _twin_parity_image()
    panels = (("band", slice(0, 160)), ("sheets", slice(160, 320)), ("xray", slice(320, 480)),
              ("band house, 3 curtains, fringe 1", slice(480, 640)), ("sheets footprint view", slice(640, 800)))
    for name, cols in panels:
        miss = np.abs(gpu[:, cols] - cpu[:, cols])
        # measured 2026-10-13: every pixel of every panel within one 8-bit code. The margin lets a pixel on a crease
        # (float32 against float64 through a steep transfer) differ by two; a broken wiring differs everywhere
        assert miss.max() <= 2 and np.mean(miss > 1) < 0.005, \
            f"{name}: {np.mean(miss > 1):.4f} of pixels off by more than one code, worst {miss.max()}"
