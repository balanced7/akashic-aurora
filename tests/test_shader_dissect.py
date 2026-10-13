"""Pins for the shader dissector: the GLSL reader (arsenal/shaders/glsl.py), the technique detectors
(arsenal/shaders/dissect.py) and the census (arsenal/shaders/census.py).

Every shader here is synthetic and written for this file: the real corpus is other people's code under their licence
and lives only under state/ (gitignored), so no fixture comes from it. The corpus is read in one place only, the last
section, which measures the licence line (no 12-token run shared with any corpus shader) over the dissector's files and
this one, through the house tool, in memory, reporting lines and corpus ids, never text.

Each detector has a POSITIVE fixture (the shape it exists to find) and a NEGATIVE one -- a near miss that shares the
surface features (a hash read at cell offsets that is not a noise, a fract(time) - 0.5 that is not a tiling, a loop
that accumulates a distance without marching) -- because the negatives are where a regex-shaped detector actually fails.
The fixtures are written fresh: same detectors, our own names and arrangements, so they hold no corpus code either.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from arsenal.shaders import census as K
from arsenal.shaders import cli
from arsenal.shaders import corpus as C
from arsenal.shaders import dissect as D
from arsenal.shaders import glsl as G


# ---------- helpers ----------

# The entry every fixture body lands in: `scr` is the centred screen point, `paint` the colour being built.
MAIN = """
void mainImage(out vec4 ink, in vec2 pxc) {
    vec3 paint = vec3(0.0);
    vec2 scr = (pxc + pxc - iResolution.xy) / iResolution.y;
    %s
    ink = vec4(paint, 1.0);
}
"""


def shader(helpers: str = "", body: str = "") -> str:
    return helpers + MAIN % body


def swap(src: str, *pairs) -> str:
    """str.replace that refuses a no-op: a fixture edited away from its anchor fails loudly, not silently."""
    for old, new in pairs:
        assert old in src, f"fixture anchor missing: {old!r}"
        src = src.replace(old, new)
    return src


def report(src: str) -> dict:
    return D.dissect_view(D.view_from_source(src, "image.glsl"))


def tags(src: str) -> set:
    return set(report(src)["tags"])


def evidence(src: str, tag: str) -> list:
    for t in report(src)["techniques"]:
        if t["tag"] == tag:
            return t["evidence"]
    return []


def pass_json(sid: str, passes: list) -> dict:
    return {"info": {"id": sid, "name": sid, "username": "tester"}, "renderpass": passes}


def rp(name, typ, code, inputs=(), outputs=()):
    return {"name": name, "type": typ, "code": code, "inputs": list(inputs), "outputs": list(outputs)}


BUF_A, BUF_B, IMG = "4dXGR8", "XsXGR8", "4dfGRr"

# A sphere-traced scene the lighting fixtures build on.
SCENE = """
float ball(vec3 at, float rad) { return length(at) - rad; }
float world(vec3 at) { return ball(at - vec3(0.0, 0.25, 0.0), 0.9); }
float travel(vec3 origin, vec3 dir) {
    float dist = 0.0;
    for (int hop = 0; hop < 64; ++hop) {
        float gap = world(origin + dist * dir);
        if (gap < 0.001) break;
        dist += gap;
    }
    return dist;
}
"""
SCENE_MAIN = ("vec3 cam = vec3(0.3, 0.4, -2.6); vec3 dir = normalize(vec3(scr, 1.5)); float dist = travel(cam, dir);"
              " paint = vec3(dist * 0.1);")

# A sine hash with constants of our own (the detector keys on fract(sin(..)) times a large number, not on any one set).
HASH = "float scramble(vec2 cell) { return fract(15731.743 * sin(dot(cell, vec2(41.3, 289.1)))); }\n"
VALUE_NOISE = HASH + """
float lattice(vec2 at) {
    vec2 base = floor(at);
    vec2 fpart = at - base;
    vec2 w = fpart * fpart * (3.0 - 2.0 * fpart);
    float c00 = scramble(base);
    float c10 = scramble(base + vec2(1.0, 0.0));
    float c01 = scramble(base + vec2(0.0, 1.0));
    float c11 = scramble(base + vec2(1.0, 1.0));
    float bottom = mix(c00, c10, w.x);
    float top = mix(c01, c11, w.x);
    return mix(bottom, top, w.y);
}
"""
FBM = VALUE_NOISE + """
float layered(vec2 at) {
    float total = 0.0;
    float amp = 0.5;
    for (int oct = 0; oct < 5; oct++) {
        total += amp * lattice(at);
        at = at * 2.0 + vec2(1.7, 9.2);
        amp *= 0.5;
    }
    return total;
}
"""


def fbm_with_octave_param() -> str:
    """FBM with its octave count passed in (layered(p, n)), so the loop bound is symbolic until a call site binds it."""
    return swap(FBM, ("float layered(vec2 at) {", "float layered(vec2 at, int octaves) {"), ("oct < 5", "oct < octaves"))


# ---------- the lexer ----------

def kinds_texts(src):
    return [(t.kind, t.text) for t in G.lex(src)]


def test_block_comments_do_not_nest_and_comment_markers_inside_comments_are_text():
    src = "/* a /* b */ int x; // c /* d\nfloat y; /* e // f */ z\n/* never closed"
    toks = G.lex(src)
    code = [(t.text, t.line) for t in toks if t.kind not in (G.COMMENT,)]
    # the first */ ends the comment (GLSL ES 3.4); `/*` after // opens nothing; // inside /* */ is text
    assert code == [("int", 1), ("x", 1), (";", 1), ("float", 2), ("y", 2), (";", 2), ("z", 2)]
    comments = [t.text for t in toks if t.kind == G.COMMENT]
    assert comments == ["/* a /* b */", "// c /* d", "/* e // f */", "/* never closed"]


def test_line_numbers_survive_multiline_comments_and_directives():
    src = "/* one\ntwo\nthree */ a\n#define F(x) \\\n   ((x) * 2.0)\nb\n"
    toks = {t.text: t.line for t in G.lex(src) if t.kind == G.IDENT}
    assert toks == {"a": 3, "b": 6}


def test_preprocessor_continuation_is_one_directive_with_its_comment_removed():
    src = "#define SQ(a) \\\n    ((a) * (a)) // squared\n#define N 4 /* four */\nfloat z = SQ(2.0);\n"
    toks = G.lex(src)
    pps = [t for t in toks if t.kind == G.PP]
    assert len(pps) == 2 and pps[0].line == 1 and pps[1].line == 3
    sq, n = G.parse_directive(pps[0]), G.parse_directive(pps[1])
    assert (sq.kind, sq.name, sq.params, sq.body) == ("define", "SQ", ("a",), "((a) * (a))")
    assert (n.name, n.params, n.body) == ("N", None, "4")
    assert [t.line for t in toks if t.text == "z"] == [4]


@pytest.mark.parametrize("text,value", [
    ("1e-3", 0.001), (".5", 0.5), ("2.", 2.0), ("1.5e+2", 150.0), ("0x1Fu", 31), ("10u", 10), ("3.0f", 3.0),
    ("7", 7), ("1.e2", 100.0), ("0.25", 0.25),
])
def test_numeric_forms_lex_as_one_number_each(text, value):
    toks = G.lex(f"x = {text};")
    nums = [t for t in toks if t.kind == G.NUMBER]
    assert len(nums) == 1 and nums[0].text == text
    assert G.parse_number(text) == value and type(G.parse_number(text)) is type(value)


def test_swizzles_and_member_access_are_not_numbers():
    assert kinds_texts("p.x + .5")[:3] == [("ident", "p"), ("op", "."), ("ident", "x")]
    assert kinds_texts("p.x + .5")[-1] == ("number", ".5")


def test_operators_lex_longest_first():
    ops = [t.text for t in G.lex("a <<= b; c += d++; e == f && g != h;") if t.kind == G.OP]
    assert ops == ["<<=", ";", "+=", "++", ";", "==", "&&", "!=", ";"]


# ---------- the preprocessor ----------

def test_if_branches_keep_only_the_live_code():
    src = """
#if 0
float dead() { return 1.0; }
#else
float live() { return 2.0; }
#endif
#if HW_PERFORMANCE == 0
float lowend() { return 0.0; }
#endif
#ifdef UNDEFINED_THING
float nope() { return 0.0; }
#elif defined(GL_ES)
float es() { return 0.0; }
#endif
"""
    prog = G.Program(src)
    assert set(prog.functions) == {"live", "es"}
    assert prog.inactive_lines


def test_common_defines_reach_the_pass_it_is_prepended_to():
    common = G.Program("#define STEPS 48\nconst float EPS = 0.001;", "common.glsl")
    image = G.Program("void mainImage(out vec4 ink, vec2 pxc) { for (int lap = 0; lap < STEPS; lap++) {} }", base=common)
    lp = image.functions["mainImage"][0].loops[0]
    assert lp.bound == 48
    assert image.value_of("EPS") == 0.001


# ---------- structure ----------

STRUCTURE = """
#define PI 3.14159
#define SCALE(x) ((x) * 2.0)
struct Hit { float d; int id; };
uniform float uGain;
const float K = 0.5, K2 = 2.0 * K;
vec3 gColor = vec3(1.0);
float helper(float x);
float helper(in float x) { return x * K; }
float viaMacro(float x) { return x; }
#define USE(x) viaMacro(x)
float unused(float x) { return x; }
Hit scene(vec3 p, out float m) { Hit h; h.d = length(p) - 1.0; h.id = 0; m = helper(h.d); return h; }
void mainImage(out vec4 ink, in vec2 pxc) {
    float m; Hit h = scene(vec3(pxc, 0.0), m);
    ink = vec4(USE(m) * SCALE(PI));
}
"""


def test_functions_structs_consts_defines_and_uniforms_are_extracted():
    prog = G.Program(STRUCTURE)
    scene = prog.functions["scene"][0]
    assert (scene.ret, [(p.type, p.name, p.qualifiers) for p in scene.params]) == \
        ("Hit", [("vec3", "p", ()), ("float", "m", ("out",))])
    assert scene.line == 13 and scene.end_line == 13
    assert {c.name for c in scene.calls if not c.builtin} == {"helper"}
    assert prog.structs["Hit"].fields == [("float", "d"), ("int", "id")]
    assert prog.value_of("K2") == 1.0
    assert prog.uniforms == {"uGain": "float"} and "gColor" in prog.globals
    assert "helper" in prog.prototypes and len(prog.functions["helper"]) == 1
    assert prog.macros["SCALE"].params[0].name == "x" and prog.value_of("PI") == pytest.approx(3.14159)


def test_call_graph_reaches_through_macros_and_flags_dead_code():
    unit = G.Unit([G.Program(STRUCTURE)])
    live = unit.reachable()
    assert {"mainImage", "scene", "helper", "USE", "viaMacro", "SCALE"} <= live
    assert [fn.name for fn in unit.dead()] == ["unused"]
    assert "viaMacro" in G.call_graph(unit)["USE"]


def test_a_toplevel_macro_that_generates_functions_is_read():
    src = """
#define DECL_ADD(name, k) float name(float x) { return x + k; }
DECL_ADD(addOne, 1.0)
DECL_ADD(addTwo, 2.0)
void mainImage(out vec4 ink, vec2 pxc) { ink = vec4(addOne(addTwo(pxc.x))); }
"""
    unit = G.Unit([G.Program(src)])
    assert {"addOne", "addTwo"} <= set(unit.program.functions)
    assert unit.program.functions["addOne"][0].line == 3
    assert not unit.dead()


def test_main_image_built_by_a_macro_falls_back_to_the_top_level_code():
    common = G.Program("#define ENTRY void mainImage(out vec4 ink, vec2 pxc) { float r = iResolution.x;\n",
                       "common.glsl")
    image = G.Program("float f(float x) { return x * 2.0; }\nENTRY ink = vec4(f(r)); }\n", base=common)
    unit = G.Unit([common, image])
    assert unit.entries() == [G.TOPLEVEL]
    assert "f" in unit.reachable()


# ---------- loops and their bounds ----------

@pytest.mark.parametrize("pre,header,bound", [
    ("", "for (int lap = 0; lap < 64; lap++)", 64),
    ("", "for (int lap = 0; lap <= 8; ++lap)", 9),
    ("#define STEPS 100\n", "for (int lap = 0; lap < STEPS; lap++)", 100),
    ("const int N = 5;\n", "for (int lap = 0; lap < N; lap++)", 5),
    ("#define FROM0 min(iFrame, 0)\n", "for (int lap = FROM0; lap < 4; lap++)", 4),
    ("#define NO_UNROLL(x) ((x) + max(0, -iFrame))\n", "for (int lap = NO_UNROLL(0); lap < 3; lap++)", 3),
    ("", "for (float span = 0.0; span < 1.0; span += 0.25)", 4),
    ("", "for (float span = 0.0; span < 1.0; span += 0.01)", 100),
    ("", "for (float lap; lap++ < 50.;)", 50),
    ("", "for (int lap = 10; lap > 0; lap--)", 10),
    ("", "for (float span = 1.0; span < 64.0; span *= 2.0)", 6),
    ("", "for (int lap = 0; lap < 99 && rem > 0.001; lap++)", 99),
    ("", "for (int lap = 0, j = 4; lap < 12; lap += 3)", 4),
    ("", "for (int lap = 0; float(lap) < 7.5; lap++)", 8),
])
def test_literal_loop_bounds(pre, header, bound):
    src = pre + "void mainImage(out vec4 ink, vec2 pxc) { float rem = 1.0, acc = 0.0; " + header + \
        " { acc += 0.1; } ink = vec4(acc); }"
    lp = G.Program(src).functions["mainImage"][0].loops[0]
    assert lp.bound == bound, lp.note


@pytest.mark.parametrize("header", [
    "while (pace < 10.0)",
    "for (int lap = 0; lap < 64 || pace < 1.0; lap++)",
    "for (int lap = 0; lap < int(iTime); lap++)",
])
def test_runtime_bounds_are_reported_unknown(header):
    # the step depends on pace itself, so no closed form exists (a constant step WOULD have one: += 0.1 runs 100 times)
    src = "void mainImage(out vec4 ink, vec2 pxc) { float pace = 0.0; " + header + \
        " { pace += 0.1 * (1.0 + sin(pace)); } ink = vec4(pace); }"
    lp = G.Program(src).functions["mainImage"][0].loops[0]
    assert lp.bound is None and lp.note


def test_a_bound_passed_as_a_parameter_is_symbolic_then_resolved_per_call_site():
    src = fbm_with_octave_param() + shader(body="paint = vec3(layered(scr, 6));")
    rep = report(src)
    lp = D.load  # keep a name live for readability below
    fbm = [e for e in evidence(src, "noise.fbm")][0]
    assert fbm["params"]["octaves"] == 6 and "from its call sites" in fbm["params"]["bound_note"]
    assert rep["passes"][0]["cost"]["heaviest"] == 6


def test_nested_loops_know_their_parent_and_the_body_after_an_unbraced_header():
    src = """void mainImage(out vec4 ink, vec2 pxc) {
    float tally = 0.0;
    for (int row = 0; row < 3; row++)
        for (int seat = 0; seat < 4; seat++) tally += 1.0;
    tally *= 2.0;
    ink = vec4(tally);
}"""
    fn = G.Program(src).functions["mainImage"][0]
    outer, inner = fn.loops
    assert inner.parent is outer and inner.depth == 1 and outer.bound * inner.bound == 12
    assert "tally *= 2.0" not in fn.text(*outer.body)


# ---------- detectors: one positive, one near-miss negative each ----------

FIXTURES = {
    "raymarch.sphere_trace": (
        shader(SCENE, SCENE_MAIN),
        # the loop still calls the distance function, but at a point that never moves with dist, and dist steps evenly
        shader(swap(SCENE, ("float gap = world(origin + dist * dir);", "float gap = world(vec3(float(hop), 0.0, 0.0));"),
                    ("dist += gap;", "dist += 0.1;")), SCENE_MAIN)),
    "raymarch.fixed_step": (
        shader("float haze(vec3 at) { return max(0.0, 0.7 - dot(at, at)); }",
               "vec3 cam = vec3(0.0, 0.0, -1.5); vec3 dir = normalize(vec3(scr, 1.2)); float along = 0.0; float fogged = 0.0;"
               " for (int tap = 0; tap < 24; tap++) { vec3 probe = cam + dir * along; fogged += 0.04 * haze(probe);"
               " along += 0.12; } paint = vec3(fogged);"),
        shader("", "float along = 0.0; for (int tap = 0; tap < 24; tap++) { paint += vec3(0.02 * along); along += 0.12; }")),
    "raymarch.jitter": (
        shader(swap(SCENE, ("float dist = 0.0;", "float dist = 0.05 * fract(sin(dot(dir.xy, vec2(41.3, 289.1))) * 15731.743);")),
               SCENE_MAIN),
        shader(swap(SCENE, ("float dist = 0.0;", "float dist = 0.05;")), SCENE_MAIN)),
    "sdf.sphere": (
        shader("float orb(vec3 q, float size) { return length(q) - size; }", "paint = vec3(orb(vec3(scr, 0.0), 0.5));"),
        shader("float orb(vec3 q, float size) { return 1.0 - length(q); }", "paint = vec3(orb(vec3(scr, 0.0), 0.5));")),
    "sdf.box": (
        shader("float crate(vec3 pos, vec3 extent) { vec3 over = abs(pos) - extent;"
               " float inner = max(over.x, max(over.y, over.z)); return length(max(over, 0.0)) + min(inner, 0.0); }",
               "paint = vec3(crate(vec3(scr, 0.0), vec3(0.4, 0.3, 0.2)));"),
        shader("float crate(vec3 pos, vec3 extent) { return length(min(pos, extent)); }",
               "paint = vec3(crate(vec3(scr, 0.0), vec3(0.4, 0.3, 0.2)));")),
    "sdf.torus": (
        shader("float ring(vec3 rq) { return length(vec2(length(rq.xy) - 0.7, rq.z)) - 0.15; }",
               "paint = vec3(ring(vec3(scr, 0.0)));"),
        shader("float ring(vec3 rq) { return length(vec2(rq.x, rq.y)) * 0.15; }", "paint = vec3(ring(vec3(scr, 0.0)));")),
    "sdf.capsule": (
        shader("float rod(vec3 pos, vec3 head, vec3 tail, float thick) { vec3 seg = tail - head; vec3 rel = pos - head;"
               " float along = clamp(dot(rel, seg) / dot(seg, seg), 0.0, 1.0); return distance(rel, seg * along) - thick; }",
               "paint = vec3(rod(vec3(scr, 0.0), vec3(-0.5), vec3(0.5), 0.1));"),
        shader("float rod(vec3 pos, vec3 head, vec3 tail, float thick) { vec3 seg = tail - head; vec3 rel = pos - head;"
               " float along = clamp(dot(rel, seg), 0.0, 1.0); return along * thick; }",
               "paint = vec3(rod(vec3(scr, 0.0), vec3(-0.5), vec3(0.5), 0.1));")),
    "sdf.cylinder": (
        shader("float column(vec3 spot) { return length(spot.yz) - 0.3; }", "paint = vec3(column(vec3(scr, 0.0)));"),
        shader("float column(vec3 spot) { return length(spot.yz) * 0.3; }", "paint = vec3(column(vec3(scr, 0.0)));")),
    "sdf.octahedron": (
        shader("float gem(vec3 spot, float size) { return 0.57735 * (abs(spot.x) + abs(spot.y) + abs(spot.z) - size); }",
               "paint = vec3(gem(vec3(scr, 0.0), 0.8));"),
        # the same |x|+|y|+|z| without the 1/sqrt(3) scale: a diamond-shaped bound, not the exact octahedron
        shader("float gem(vec3 spot, float size) { return abs(spot.x) + abs(spot.y) + abs(spot.z) - size; }",
               "paint = vec3(gem(vec3(scr, 0.0), 0.8));")),
    "sdf.named": (
        shader("float sdSlab(vec3 spot, vec2 dims) { return max(abs(spot.y) - dims.x, abs(spot.z) - dims.y); }",
               "paint = vec3(sdSlab(vec3(scr, 0.0), vec2(0.2, 0.6)));"),
        shader("float slabShape(vec3 spot, vec2 dims) { return max(abs(spot.y) - dims.x, abs(spot.z) - dims.y); }",
               "paint = vec3(slabShape(vec3(scr, 0.0), vec2(0.2, 0.6)));")),
    "sdf.smooth_min": (
        shader("float merge(float da, float db, float soft) { float blend = clamp(0.5 + 0.5 * (db - da) / soft, 0.0, 1.0);"
               " return mix(db, da, blend) - soft * blend * (1.0 - blend); }", "paint = vec3(merge(scr.x, scr.y, 0.3));"),
        shader("float merge(float da, float db, float soft) { return min(da, db) - soft; }",
               "paint = vec3(merge(scr.x, scr.y, 0.3));")),
    "domain.repeat": (
        shader("vec3 tile(vec3 spot, vec3 cell) { return spot - cell * round(spot / cell); }",
               "paint = tile(vec3(scr * 3.0, 0.0), vec3(1.0));"),
        # fract(x) - 0.5 inside a float triangle wave is not cell coordinates
        shader("float zigzag(float x) { return abs(fract(x * 0.5) - 0.5) * 2.0; }", "paint = vec3(zigzag(iTime));")),
    "domain.rotate2d": (
        shader("mat2 twist(float spin) { float cw = cos(spin), sw = sin(spin); return mat2(cw, sw, -sw, cw); }",
               "scr = twist(0.7) * scr; paint = vec3(scr, 0.0);"),
        # the same matrix shape, but its two entries are not a cosine and a sine of one angle
        shader("mat2 twist(float spin) { float gx = spin * 2.0, gy = spin; return mat2(gx, gy, -gy, gx); }",
               "scr = twist(0.7) * scr; paint = vec3(scr, 0.0);")),
    "domain.polar": (
        shader("", "float ang = atan(scr.y, scr.x); float rad = length(scr); paint = vec3(fract(ang * rad));"),
        shader("", "float ang = atan(scr.y / scr.x); paint = vec3(ang);")),
    "domain.kaleidoscope": (
        shader("", "float bearing = atan(scr.y, scr.x); float wedge = 6.28318 / 5.0;"
                   " bearing = abs(mod(bearing, wedge) - 0.5 * wedge); scr = length(scr) * vec2(cos(bearing), sin(bearing));"
                   " paint = vec3(scr, 0.0);"),
        shader("", "float ang = atan(scr.y, scr.x); float rad = length(scr); paint = vec3(sin(ang * 3.0) * rad);")),
    "normal.central_diff": (
        shader(SCENE + """
vec3 slope(vec3 spot) {
    vec2 nudge = vec2(0.0005, 0.0);
    float gx = world(spot + nudge.xyy) - world(spot - nudge.xyy);
    float gy = world(spot + nudge.yxy) - world(spot - nudge.yxy);
    float gz = world(spot + nudge.yyx) - world(spot - nudge.yyx);
    return normalize(vec3(gx, gy, gz));
}""", SCENE_MAIN + "paint = slope(cam + dir * dist);"),
        # four hash taps at a cell's corners: neighbours, but nothing is differenced
        shader(VALUE_NOISE, "paint = vec3(lattice(scr * 4.0));")),
    "normal.forward_diff": (
        shader(SCENE + """
vec3 slope(vec3 spot) {
    float nudge = 0.0005;
    float here = world(spot);
    return normalize(vec3(world(spot + vec3(nudge, 0.0, 0.0)) - here, world(spot + vec3(0.0, nudge, 0.0)) - here,
                          world(spot + vec3(0.0, 0.0, nudge)) - here));
}""", SCENE_MAIN + "paint = slope(cam + dir * dist);"),
        shader(VALUE_NOISE, "paint = vec3(lattice(scr * 4.0));")),
    "normal.tetrahedral": (
        shader(SCENE + """
vec3 slope(vec3 spot) {
    vec2 sgn = vec2(1.0, -1.0);
    float eps = 0.0007;
    vec3 sum = sgn.xyy * world(spot + eps * sgn.xyy);
    sum += sgn.yyx * world(spot + eps * sgn.yyx);
    sum += sgn.yxy * world(spot + eps * sgn.yxy);
    sum += sgn.xxx * world(spot + eps * sgn.xxx);
    return normalize(sum);
}""", SCENE_MAIN + "paint = slope(cam + dir * dist);"),
        shader(VALUE_NOISE, "paint = vec3(lattice(scr * 4.0));")),
    "normal.screen_space": (
        shader("", "vec3 surf = vec3(scr, 0.3 * cos(scr.y * 3.0)); paint = normalize(cross(dFdy(surf), dFdx(surf))) * 0.5 + 0.5;"),
        shader("", "vec3 surf = vec3(scr, 0.3 * cos(scr.y * 3.0)); paint = normalize(cross(surf, vec3(0.6, 0.0, 0.8)));")),
}

# Shadow marches are found by shape (a min of the closest miss over distance travelled) or, for a hard shadow that only
# answers hit or miss, by the name: so both fixtures are called inShadow.
SOFT = SCENE + """
float inShadow(vec3 origin, vec3 toward) {
    float lit = 1.0;
    float s = 0.015;
    for (int hop = 0; hop < 40; ++hop) {
        float closest = world(origin + s * toward);
        lit = min(lit, 10.0 * closest / s);
        if (lit < 0.002) break;
        s += max(closest, 0.03);
    }
    return max(lit, 0.0);
}
"""
HARD = SCENE + """
float inShadow(vec3 origin, vec3 toward) {
    float s = 0.015;
    for (int hop = 0; hop < 40; ++hop) {
        float closest = world(origin + s * toward);
        if (closest < 0.0005) return 0.0;
        s += closest;
    }
    return 1.0;
}
"""
AO = SCENE + """
float cavity(vec3 spot, vec3 up) {
    float dark = 0.0;
    float weight = 1.0;
    for (int ring = 1; ring <= 4; ring++) {
        float reach = 0.03 * float(ring * ring);
        float found = world(spot + up * reach);
        dark += weight * max(reach - found, 0.0);
        weight *= 0.6;
    }
    return 1.0 - clamp(dark * 2.5, 0.0, 1.0);
}
"""
NOT_AO = SCENE + """
float cavity(vec3 spot, vec3 up) {
    float dark = 0.0;
    for (int ring = 1; ring <= 4; ring++) { dark += 0.2 * world(spot); }
    return 1.0 - dark;
}
"""
LIT = SCENE_MAIN + " vec3 spot = cam + dir * dist; vec3 sun = normalize(vec3(0.6, 0.8, -0.3)); paint *= inShadow(spot, sun);"

FIXTURES.update({
    "lighting.soft_shadow": (shader(SOFT, LIT), shader(HARD, LIT)),
    "lighting.hard_shadow": (shader(HARD, LIT), shader(SOFT, LIT)),
    "lighting.ao": (shader(AO, SCENE_MAIN + "paint *= cavity(cam, dir);"),
                    shader(NOT_AO, SCENE_MAIN + "paint *= cavity(cam, dir);")),
    "lighting.diffuse": (
        shader("", "vec3 facing = normalize(vec3(scr, 1.0)); vec3 sun = normalize(vec3(0.3, 0.9, 0.2));"
                   " paint = vec3(0.9, 0.8, 0.7) * max(dot(facing, sun), 0.0);"),
        shader("", "vec3 facing = normalize(vec3(scr, 1.0)); vec3 sun = normalize(vec3(0.3, 0.9, 0.2));"
                   " paint = vec3(dot(facing, sun));")),
    "lighting.specular": (
        shader("", "vec3 mirror = reflect(normalize(vec3(scr, -1.2)), vec3(0.0, 0.6, 0.8)); vec3 sun = normalize(vec3(0.3, 0.9, 0.2));"
                   " float shine = pow(max(dot(mirror, sun), 0.0), 24.0); paint = vec3(shine);"),
        # a squared lobe is a soft wash, not a highlight
        shader("", "vec3 mirror = reflect(normalize(vec3(scr, -1.2)), vec3(0.0, 0.6, 0.8)); vec3 sun = normalize(vec3(0.3, 0.9, 0.2));"
                   " float shine = pow(max(dot(mirror, sun), 0.0), 2.0); paint = vec3(shine);")),
    "lighting.fresnel": (
        shader("", "vec3 facing = normalize(vec3(scr, -1.0)); vec3 view = vec3(0.0, 0.0, 1.0);"
                   " float rim = pow(1.0 - abs(dot(facing, view)), 4.0); paint = vec3(rim);"),
        # pow(1 - x, k) of a plain coordinate is a ramp, not a facing ratio
        shader("", "float ramp = pow(1.0 - scr.y, 3.0); paint = vec3(ramp);")),
    "lighting.fog": (
        shader("", "float depth = 8.0 * length(scr); paint = mix(paint, vec3(0.6, 0.7, 0.8), 1.0 - exp(-0.02 * depth * depth));"),
        shader("", "paint = mix(paint, vec3(0.6, 0.7, 0.8), 0.25);")),
    "noise.value": (
        shader(VALUE_NOISE, "paint = vec3(lattice(scr * 4.0));"),
        # one hash per cell (offset inside the cell, not to a corner) with a mix: cell colouring, not noise
        shader(HASH + "vec3 tileTint(vec2 at) { vec2 cell = floor(at); vec2 inside = fract(at);"
               " return mix(vec3(scramble(cell + 0.37)), vec3(0.2, 0.4, scramble(cell + 0.71)), inside.y); }",
               "paint = tileTint(scr * 4.0);")),
    "noise.gradient": (
        shader("vec2 slant(vec2 cell) { float heading = 6.2831 * fract(15731.743 * sin(dot(cell, vec2(41.3, 289.1))));"
               " return vec2(cos(heading), sin(heading)); }\n"
               "float ramps(vec2 at) { vec2 cell = floor(at); vec2 off = fract(at);"
               " vec2 w = off * off * off * (off * (off * 6.0 - 15.0) + 10.0);"
               " float g00 = dot(slant(cell), off); float g10 = dot(slant(cell + vec2(1.0, 0.0)), off - vec2(1.0, 0.0));"
               " float g01 = dot(slant(cell + vec2(0.0, 1.0)), off - vec2(0.0, 1.0));"
               " float g11 = dot(slant(cell + vec2(1.0, 1.0)), off - vec2(1.0, 1.0));"
               " return mix(mix(g00, g10, w.x), mix(g01, g11, w.x), w.y); }",
               "paint = vec3(0.5 + 0.5 * ramps(scr * 4.0));"),
        shader(VALUE_NOISE, "paint = vec3(lattice(scr * 4.0));")),
    "noise.simplex": (
        shader("float skewed(vec2 at) { const float skewK = 0.3660254; const float unskewK = 0.2113249;"
               " vec2 corner = floor(at + (at.x + at.y) * skewK); vec2 rel = at - corner + (corner.x + corner.y) * unskewK;"
               " return dot(rel, rel); }", "paint = vec3(skewed(scr * 4.0));"),
        shader(VALUE_NOISE, "paint = vec3(lattice(scr * 4.0));")),
    "noise.texture": (
        shader("float grainy(vec2 at) { vec2 cell = floor(at); vec2 off = fract(at); off = smoothstep(0.0, 1.0, off);"
               " return texture(iChannel0, (cell + off + 0.5) / 64.0).y; }", "paint = vec3(grainy(scr * 4.0));"),
        shader("", "paint = texture(iChannel0, scr * 0.5 + 0.5).rgb;")),
    "noise.fbm": (
        shader(FBM, "paint = vec3(layered(scr * 3.0));"),
        # five noise taps summed with no weight and no frequency step: a sum, not octaves
        shader(VALUE_NOISE + "float stack(vec2 at) { float total = 0.0; for (int oct = 0; oct < 5; oct++)"
               " { total += lattice(at + vec2(float(oct), 0.0)); } return total; }", "paint = vec3(stack(scr));")),
    "noise.domain_warp": (
        shader(FBM, "paint = vec3(layered(scr + layered(scr)));"),
        shader(FBM, "paint = vec3(layered(scr) + layered(scr * 2.0));")),
    "hash.sin_fract": (
        shader(HASH, "paint = vec3(scramble(scr));"),
        shader("float ripple(float x) { return fract(0.5 * sin(x * 3.0)); }", "paint = vec3(ripple(scr.x));")),
    "hash.integer": (
        shader("uint mixBits(uint v) { v ^= v << 7u; v *= 0x3a71c4d9u; v ^= v >> 13u; v *= 0x6e2b905fu;"
               " return v ^ (v >> 11u); }", "paint = vec3(float(mixBits(uint(pxc.x))) / 4294967295.0);"),
        shader("uint bump(uint v) { return v + 3u; }", "paint = vec3(float(bump(uint(pxc.x))));")),
    "hash.fract_dot": (
        shader("float jumble(vec2 at) { vec3 m = fract(vec3(at.x, at.y, at.x) * 0.1031); m += dot(m, m.zxy + 19.19);"
               " return fract(m.x * m.y + m.z); }", "paint = vec3(jumble(pxc));"),
        shader(HASH, "paint = vec3(scramble(scr));")),
})

FRACTAL_MAIN = "paint = vec3(ifs(vec3(scr, 0.5)));"
FIXTURES.update({
    "fractal.kifs": (
        shader("float ifs(vec3 z) { float k = 1.0; for (int lvl = 0; lvl < 7; lvl++) { z = abs(z) - vec3(0.4, 0.3, 0.6);"
               " z *= 1.7; k *= 1.7; } return (length(z) - 1.0) / k; }", FRACTAL_MAIN),
        # the fold repeats but the point is never scaled, rotated or offset: a mirror, not an IFS
        shader("float ifs(vec3 z) { for (int lvl = 0; lvl < 7; lvl++) { z = abs(z) - vec3(0.4, 0.3, 0.6); }"
               " return length(z) - 1.0; }", FRACTAL_MAIN)),
    "fractal.mandelbox": (
        shader("float ifs(vec3 fp) { vec3 seed = fp; float dr = 1.0; for (int lvl = 0; lvl < 9; lvl++) {"
               " fp = clamp(fp, -1.0, 1.0) * 2.0 - fp; float m2 = max(dot(fp, fp), 0.2);"
               " fp = fp * (2.2 / m2) + seed; dr = dr * 2.2 / m2 + 1.0; } return length(fp) / abs(dr); }", FRACTAL_MAIN),
        shader("float ifs(vec3 fp) { for (int lvl = 0; lvl < 9; lvl++) { fp = clamp(fp, -1.0, 1.0) * 0.9; }"
               " return length(fp); }", FRACTAL_MAIN)),
    "fractal.inversion": (
        shader("float ifs(vec3 fp) { float gain = 1.0; for (int lvl = 0; lvl < 7; lvl++) { fp = mod(fp + 1.0, 2.0) - 1.0;"
               " float shrink = 1.3 / max(dot(fp, fp), 0.05); fp *= shrink; gain *= shrink; }"
               " return 0.2 * length(fp.xz) / gain; }", FRACTAL_MAIN),
        shader("float ifs(vec3 fp) { for (int lvl = 0; lvl < 7; lvl++) { float lensq = dot(fp, fp); fp *= 0.7; }"
               " return length(fp); }", FRACTAL_MAIN)),
    "fractal.escape_time": (
        shader("", "vec2 zc = vec2(0.0); vec2 c0 = scr * 1.2 - vec2(0.5, 0.0); float esc = 0.0;"
                   " for (int it = 0; it < 80; it++) { zc = vec2(zc.x * zc.x - zc.y * zc.y, 2.0 * zc.x * zc.y) + c0;"
                   " if (length(zc) > 2.0) break; esc += 1.0; } paint = vec3(esc / 80.0);"),
        shader("", "vec2 zc = vec2(0.0); vec2 c0 = scr; for (int it = 0; it < 80; it++) { zc = vec2(zc.x + zc.y, zc.x - zc.y) + c0; }"
                   " paint = vec3(zc, 0.0);")),
    "fractal.mandelbulb": (
        shader("float ifs(vec3 start) { vec3 w = start; float rad = 0.0; for (int lvl = 0; lvl < 6; lvl++) {"
               " rad = length(w); if (rad > 2.0) break; float polar = 7.0 * asin(w.y / rad); float azim = 7.0 * atan(w.x, w.z);"
               " w = pow(rad, 7.0) * vec3(cos(polar) * sin(azim), sin(polar), cos(polar) * cos(azim)) + start; } return rad; }",
               FRACTAL_MAIN),
        shader("float ifs(vec3 start) { float rad = length(start); float polar = asin(start.y / rad);"
               " float azim = atan(start.x, start.z); return polar * azim; }", FRACTAL_MAIN)),
})

CELLS = """
float cells(vec2 at) {
    vec2 home = floor(at);
    vec2 inside = at - home;
    float best = 4.0;
    for (int dy = %s; dy %s; dy++) {
        for (int dx = %s; dx %s; dx++) {
            vec2 nb = vec2(dx, dy);
            vec2 delta = nb + jitter2(home + nb) - inside;
            best = min(best, length(delta));
        }
    }
    return best;
}
"""
JITTER2 = ("vec2 jitter2(vec2 cell) { return fract(15731.743 * sin(vec2(dot(cell, vec2(41.3, 289.1)),"
           " dot(cell, vec2(97.1, 157.7))))); }\n")
FIXTURES.update({
    "cellular.voronoi": (
        shader(JITTER2 + CELLS % ("-1", "<= 1", "-1", "<= 1"), "paint = vec3(cells(scr * 4.0));"),
        # the same search over cells 0..2: never looks at the neighbours on the negative side
        shader(JITTER2 + CELLS % ("0", "< 3", "0", "< 3"), "paint = vec3(cells(scr * 4.0));")),
    "color.cosine_palette": (
        shader("vec3 spectrum(float x) { vec3 base = vec3(0.55, 0.45, 0.5); vec3 swing = vec3(0.45, 0.5, 0.4);"
               " return base + swing * cos(6.28318 * (x * vec3(1.0, 0.9, 1.1) + vec3(0.1, 0.4, 0.7))); }",
               "paint = spectrum(scr.x);"),
        shader("vec3 spectrum(float x) { vec3 base = vec3(0.55, 0.45, 0.5); return base + 0.4 * cos(vec3(3.0) * x); }",
               "paint = spectrum(scr.x);")),
    "color.gamma": (shader("", "paint = pow(paint, vec3(1.0 / 2.2));"), shader("", "paint = pow(paint, vec3(2.0));")),
    "color.gamma_decode": (
        shader("", "vec3 sampled = pow(texture(iChannel0, scr).rgb, vec3(2.2)); paint = sampled * 0.8;"),
        shader("", "vec3 sampled = pow(texture(iChannel0, scr).rgb, vec3(0.45)); paint = sampled * 0.8;")),
    "color.srgb": (
        shader("vec3 encode(vec3 lin) { vec3 lo = lin * 12.92; vec3 hi = 1.055 * pow(lin, vec3(0.41666)) - 0.055;"
               " return mix(lo, hi, step(vec3(0.0031308), lin)); }", "paint = encode(paint);"),
        shader("vec3 encode(vec3 lin) { return mix(lin * 12.0, pow(lin, vec3(0.41666)), step(vec3(0.003), lin)); }",
               "paint = encode(paint);")),
    "color.dither": (
        shader("", "paint += (fract(15731.743 * sin(pxc.x * 0.0917 + pxc.y * 0.473)) - 0.5) / 255.0;"),
        shader("", "paint += 0.5 / 255.0;")),
    # The hue offsets ARE the formula. Spelled with floats, either textbook form (mod(h*6 + vec3(0,4,2), 6) - 3, or this
    # inline-offset one) is a 14+ token run of pure constants that corpus shaders also hold, so this fixture takes the
    # inline form with its leading 1 written as an int (the detector reads either spelling).
    "color.hsv": (
        shader("vec3 hueToRgb(float hue, float sat, float val) {"
               " vec3 ramp = abs(6.0 * fract(hue + vec3(1, 2.0 / 3.0, 1.0 / 3.0)) - 3.0);"
               " ramp = clamp(ramp - 1.0, 0.0, 1.0); return val * mix(vec3(1.0), ramp, sat); }",
               "paint = hueToRgb(scr.x, 1.0, 1.0);"),
        shader("vec3 hueToRgb(float hue) { vec3 ramp = vec3(abs(mod(hue * 6.0, 6.0) - 3.0)); return ramp; }",
               "paint = hueToRgb(scr.x);")),
    "color.vignette": (
        shader("", "vec2 vgn = pxc / iResolution.xy; paint *= pow(16.0 * vgn.x * vgn.y * (1.0 - vgn.x) * (1.0 - vgn.y), 0.15);"),
        shader("", "vec2 vgn = pxc / iResolution.xy; paint *= 1.0 - 0.5 * dot(vgn - 0.5, vgn - 0.5);")),
    "tonemap.reinhard": (shader("", "paint = paint / (1.0 + paint);"), shader("", "paint = paint / 2.0;")),
    "tonemap.aces": (
        shader("vec3 filmFit(vec3 hdr) { vec3 top = hdr * (2.51 * hdr + 0.03); vec3 bottom = hdr * (2.43 * hdr + 0.59) + 0.14;"
               " return clamp(top / bottom, 0.0, 1.0); }", "paint = filmFit(paint);"),
        shader("vec3 filmFit(vec3 hdr) { vec3 top = hdr * (2.0 * hdr + 0.03); vec3 bottom = hdr * (2.0 * hdr + 0.5) + 0.1;"
               " return clamp(top / bottom, 0.0, 1.0); }", "paint = filmFit(paint);")),
    "tonemap.filmic": (
        shader("vec3 curveHD(vec3 hdr) { vec3 lifted = max(hdr - 0.004, vec3(0.0)); vec3 top = lifted * (6.2 * lifted + 0.5);"
               " return top / (lifted * (6.2 * lifted + 1.7) + 0.06); }", "paint = curveHD(paint);"),
        shader("vec3 curveHD(vec3 hdr) { vec3 lifted = max(hdr - 0.004, vec3(0.0)); vec3 top = lifted * (3.0 * lifted + 0.5);"
               " return top / (lifted * (3.0 * lifted + 1.0)); }", "paint = curveHD(paint);")),
    "tonemap.tanh": (shader("", "paint = tanh(1.4 * paint);"), shader("", "float soft = tanh(scr.x); paint += vec3(soft);")),
    "tonemap.exposure": (shader("", "paint = 1.0 - exp(-1.8 * paint);"),
                         shader("", "float fade = 2.0; paint = mix(paint, vec3(0.9), 1.0 - exp(-0.15 * fade));")),
    "glow.march": (
        shader(swap(SCENE, ("dist += gap;", "dist += gap; halo += 0.02 / (0.05 + gap * gap);"),
                    ("float dist = 0.0;", "float dist = 0.0; float halo = 0.0;")), SCENE_MAIN),
        shader(swap(SCENE, ("dist += gap;", "dist += gap; halo += 0.02;"),
                    ("float dist = 0.0;", "float dist = 0.0; float halo = 0.0;")), SCENE_MAIN)),
    "glow.accumulate": (
        shader("", "for (int orb = 0; orb < 6; orb++) { float spoke = 1.047 * float(orb); vec2 orbit = 0.6 * vec2(sin(spoke), cos(spoke));"
                   " paint += vec3(0.6, 0.8, 1.0) * (0.003 / abs(length(scr - orbit) - 0.08)); }"),
        shader("", "for (int orb = 0; orb < 6; orb++) { paint += vec3(0.002 * float(orb)); }")),
    "volume.transmittance": (
        shader("", "float trans = 1.0; for (int tap = 0; tap < 12; tap++) { float dens = 0.4 + 0.3 * cos(scr.y * 5.0 + float(tap));"
                   " trans *= exp(-0.12 * dens); } paint = vec3(trans);"),
        shader("", "float level = 1.0; for (int tap = 0; tap < 12; tap++) { level *= 0.7; } paint = vec3(level);")),
    "volume.front_to_back": (
        shader("", "vec4 acc = vec4(0.0); for (int tap = 0; tap < 12; tap++) { float dens = 0.05 + 0.02 * float(tap);"
                   " vec4 layer = vec4(vec3(0.8, 0.7, 0.6) * dens, dens); acc += (1.0 - acc.w) * layer; } paint = acc.rgb;"),
        shader("", "vec4 acc = vec4(0.0); for (int tap = 0; tap < 12; tap++) { vec4 layer = vec4(0.1); acc += 0.5 * layer; }"
                   " paint = acc.rgb;")),
    "input.mouse": (shader("", "vec2 pointer = iMouse.xy / iResolution.y; paint = vec3(length(scr - pointer));"),
                    shader("", "paint = vec3(scr, 0.0);")),
    "animation.time": (shader("", "paint = vec3(0.5 + 0.5 * sin(iTime * 1.3));"), shader("", "paint = vec3(scr.x, scr.y, 0.2);")),
    "animation.frame": (
        shader("", "float tick = 0.02 * float(iFrame); paint = vec3(fract(tick));"),
        # min(iFrame, 0) is the anti-unroll idiom: it reads iFrame without animating anything
        shader("", "for (int lap = min(iFrame, 0); lap < 3; lap++) { paint += vec3(0.15); }")),
    "aa.supersample": (
        shader("#define GRID 3\nvec3 scene(vec2 q) { return vec3(q, 0.5); }",
               "vec3 sum3 = vec3(0.0); for (int sx = 0; sx < GRID; sx++) for (int sy = 0; sy < GRID; sy++) {"
               " vec2 jit = vec2(float(sx), float(sy)) / float(GRID) - 0.33;"
               " sum3 += scene((pxc + jit + pxc + jit - iResolution.xy) / iResolution.y); } paint = sum3 / float(GRID * GRID);"),
        shader("vec3 scene(vec2 q) { return vec3(q, 0.5); }",
               "vec3 sum3 = vec3(0.0); for (int sx = 0; sx < 3; sx++) { sum3 += scene(scr) * 0.3; } paint = sum3;")),
    "camera.lookat": (
        shader("", "vec3 cam = vec3(2.0, 1.5, 2.0); vec3 fwd = normalize(-cam);"
                   " vec3 side = cross(fwd, vec3(0.0, 1.0, 0.0)); side = normalize(side); vec3 upv = cross(side, fwd);"
                   " vec3 ray = normalize(scr.x * side + scr.y * upv + 1.8 * fwd); paint = 0.5 + 0.5 * ray;"),
        shader("", "vec3 fwd = vec3(0.0, 0.0, 1.0); vec3 upv = vec3(0.0, 1.0, 0.0); paint = normalize(cross(fwd, upv));")),
})

# Tags that only a multi-pass Shadertoy JSON can carry: fixtures are (positive, negative) shader dicts.
SINGLE = "void mainImage(out vec4 ink, in vec2 pxc) { ink = texture(iChannel0, pxc / iResolution.xy); }"
SELF_READ = "void mainImage(out vec4 ink, in vec2 pxc) { vec4 before = texelFetch(iChannel0, ivec2(pxc), 0); ink = 0.98 * before; }"
FLAT = "void mainImage(out vec4 ink, in vec2 pxc) { ink = vec4(0.5, 0.2, 0.1, 1.0); }"
JSON_FIXTURES = {
    "feedback.self": (
        pass_json("aaaaaa", [rp("Buffer A", "buffer", SELF_READ, [{"id": BUF_A, "type": "buffer", "channel": 0}], [{"id": BUF_A, "channel": 0}]),
                             rp("Image", "image", SINGLE, [{"id": BUF_A, "type": "buffer", "channel": 0}], [{"id": IMG, "channel": 0}])]),
        pass_json("aaaaab", [rp("Buffer A", "buffer", FLAT, [], [{"id": BUF_A, "channel": 0}]),
                             rp("Image", "image", SINGLE, [{"id": BUF_A, "type": "buffer", "channel": 0}], [{"id": IMG, "channel": 0}])])),
    "feedback.cycle": (
        pass_json("aaaaac", [rp("Buffer A", "buffer", SINGLE, [{"id": BUF_B, "type": "buffer", "channel": 0}], [{"id": BUF_A, "channel": 0}]),
                             rp("Buffer B", "buffer", SINGLE, [{"id": BUF_A, "type": "buffer", "channel": 0}], [{"id": BUF_B, "channel": 0}]),
                             rp("Image", "image", SINGLE, [{"id": BUF_B, "type": "buffer", "channel": 0}], [{"id": IMG, "channel": 0}])]),
        pass_json("aaaaad", [rp("Buffer A", "buffer", FLAT, [], [{"id": BUF_A, "channel": 0}]),
                             rp("Buffer B", "buffer", SINGLE, [{"id": BUF_A, "type": "buffer", "channel": 0}], [{"id": BUF_B, "channel": 0}]),
                             rp("Image", "image", SINGLE, [{"id": BUF_B, "type": "buffer", "channel": 0}], [{"id": IMG, "channel": 0}])])),
    "audio.input": (
        pass_json("aaaaae", [rp("Image", "image", "void mainImage(out vec4 ink, in vec2 pxc) {"
                                " float band = texture(iChannel0, vec2(pxc.x / iResolution.x, 0.1)).r; ink = vec4(vec3(band), 1.0); }",
                                [{"id": "x", "type": "music", "channel": 0}], [{"id": IMG, "channel": 0}])]),
        pass_json("aaaaaf", [rp("Image", "image", "void mainImage(out vec4 ink, in vec2 pxc) { ink = vec4(pxc.x / iResolution.x); }",
                                [{"id": "x", "type": "music", "channel": 0}], [{"id": IMG, "channel": 0}])])),
    "audio.sound_pass": (
        pass_json("aaaaag", [rp("Image", "image", FLAT, [], [{"id": IMG, "channel": 0}]),
                             rp("Sound", "sound", "vec2 mainSound(int samp, float time) {"
                                " float tone = sin(6.2831 * 220.0 * time) * exp(-2.0 * time); return vec2(tone, tone * 0.8); }")]),
        pass_json("aaaaah", [rp("Image", "image", "void mainImage(out vec4 ink, in vec2 pxc) { ink = vec4(vec3(sin(220.0) * 0.5 + 0.5), 1.0); }",
                                [], [{"id": IMG, "channel": 0}])])),
    "input.keyboard": (
        pass_json("aaaaai", [rp("Image", "image", "void mainImage(out vec4 ink, in vec2 pxc) {"
                                " vec2 keyAt = vec2(65.5 / 256.0, 0.25); float held = texture(iChannel1, keyAt).x; ink = vec4(held); }",
                                [{"id": "k", "type": "keyboard", "channel": 1}], [{"id": IMG, "channel": 0}])]),
        pass_json("aaaaaj", [rp("Image", "image", FLAT, [{"id": "k", "type": "keyboard", "channel": 1}], [{"id": IMG, "channel": 0}])])),
}


def test_every_tag_in_the_vocabulary_has_a_positive_and_a_negative_fixture():
    assert set(FIXTURES) | set(JSON_FIXTURES) == set(D.TAGS)
    assert not set(FIXTURES) & set(JSON_FIXTURES)


@pytest.mark.parametrize("tag", sorted(FIXTURES))
def test_detector_positive(tag):
    pos, _ = FIXTURES[tag]
    got = tags(pos)
    assert tag in got, f"{tag} not found; got {sorted(got)}"


@pytest.mark.parametrize("tag", sorted(FIXTURES))
def test_detector_negative(tag):
    _, neg = FIXTURES[tag]
    got = tags(neg)
    assert tag not in got, f"{tag} found in its near miss: {evidence(neg, tag)}"


@pytest.mark.parametrize("tag", sorted(JSON_FIXTURES))
def test_pass_level_detectors(tag):
    pos, neg = JSON_FIXTURES[tag]
    assert tag in D.dissect_view(D.view_from_json(pos))["tags"]
    assert tag not in D.dissect_view(D.view_from_json(neg))["tags"]


def test_audio_rows_say_spectrum_or_waveform():
    pos, _ = JSON_FIXTURES["audio.input"]
    ev = [t for t in D.dissect_view(D.view_from_json(pos))["techniques"] if t["tag"] == "audio.input"][0]["evidence"][0]
    assert ev["params"]["reads"] == ["spectrum"] and ev["params"]["type"] == "music"


def test_evidence_points_at_the_line_that_earned_it():
    src = shader(SCENE, SCENE_MAIN)
    ev = evidence(src, "raymarch.sphere_trace")[0]
    lines = src.split("\n")
    assert lines[ev["line"] - 1].strip().startswith("for (int hop = 0; hop < 64; ++hop)")
    assert ev["file"] == "image.glsl" and ev["params"]["steps"] == 64 and ev["params"]["df"] == "world"
    assert ev["params"]["hit_eps"] == "0.001"


def test_fbm_reports_octaves_lacunarity_and_gain_read_off_the_literals():
    ev = evidence(shader(FBM, "paint = vec3(layered(scr * 3.0));"), "noise.fbm")[0]["params"]
    assert (ev["octaves"], ev["lacunarity"], ev["gain"], ev["form"]) == (5, 2.0, 0.5, "loop")


def test_unrolled_fbm_with_a_rotation_matrix_is_measured():
    # the matrix turns and scales: sqrt(det) = sqrt(1.2^2 + 1.6^2) = 2, so the lacunarity is read as 2
    src = shader(VALUE_NOISE + """
const mat2 turnAndGrow = mat2(1.2, -1.6, 1.6, 1.2);
float ridges(vec2 at) {
    vec2 q = at;
    float h = 0.5 * lattice(q);
    q = turnAndGrow * q;
    h += 0.25 * lattice(q);
    q = turnAndGrow * q;
    h += 0.125 * lattice(q);
    q = turnAndGrow * q;
    h += 0.0625 * lattice(q);
    return h;
}""", "paint = vec3(ridges(scr));")
    ev = evidence(src, "noise.fbm")[0]["params"]
    assert (ev["octaves"], ev["gain"], ev["lacunarity"], ev["form"]) == (4, 0.5, 2.0, "unrolled")


PALETTE_FN = "vec3 unusedPalette(float x) { return vec3(0.4) + 0.6 * cos(6.28318 * (x + vec3(0.2, 0.5, 0.8))); }"


def test_a_technique_in_dead_code_is_not_counted():
    src = shader(HASH + PALETTE_FN, "paint = vec3(scramble(scr));")
    rep = report(src)
    assert "color.cosine_palette" not in rep["tags"]
    assert [d["name"] for d in rep["passes"][0]["dead"]] == ["unusedPalette"]
    # the same function, called, IS a palette: the dead copy was skipped for being dead, not for its shape
    assert "color.cosine_palette" in tags(shader(PALETTE_FN, "paint = unusedPalette(scr.x);"))


def test_a_volume_march_is_not_called_sphere_tracing():
    src = shader("""
float fog3(vec3 at) { return clamp(0.8 - length(at), 0.0, 1.0); }
vec4 haze(vec3 eye, vec3 dir) {
    vec4 acc = vec4(0.0);
    float along = 0.0;
    for (int hop = 0; hop < 48; hop++) {
        float rho = fog3(eye + along * dir);
        vec4 layer = vec4(vec3(0.9, 0.85, 0.8) * rho, 0.15 * rho);
        acc += (1.0 - acc.w) * layer;
        along += 0.04 + 0.1 * rho;
    }
    return acc;
}""", "paint = haze(vec3(0.0, 0.0, -2.0), normalize(vec3(scr, 1.0))).rgb;")
    got = tags(src)
    assert {"raymarch.fixed_step", "volume.front_to_back"} <= got and "raymarch.sphere_trace" not in got


def test_kifs_needs_the_point_to_carry_across_iterations():
    # mirror symmetry inside a loop over objects folds a FRESH point each pass: not an IFS
    src = shader("float row3(vec3 at) { float best = 100.0; for (int idx = 0; idx < 4; idx++) {"
                 " vec3 local = at - vec3(0.0, float(idx) * 1.5, 0.0); local = abs(local); local -= vec3(0.3);"
                 " best = min(best, length(local) - 0.15); } return best; }", "paint = vec3(row3(vec3(scr, 0.0)));")
    assert "fractal.kifs" not in tags(src)


# ---------- cost ----------

def test_cost_is_the_product_of_bounds_along_the_heaviest_call_path():
    src = shader(fbm_with_octave_param() + """
float terrain(vec3 at) { return at.y + 0.3 * layered(at.xz, 6); }
float probe(vec3 eye, vec3 dir) {
    float dist = 0.0;
    for (int hop = 0; hop < 100; hop++) {
        float gap = terrain(eye + dist * dir);
        if (gap < 0.0005) break;
        dist += 0.8 * gap;
    }
    return dist;
}
#define GRID 2
""", "for (int sx = 0; sx < GRID; sx++) for (int sy = 0; sy < GRID; sy++) {"
     " vec2 sub = pxc + vec2(float(sx), float(sy)) / float(GRID);"
     " vec3 eye = vec3(sub / iResolution.y, -2.0); paint += vec3(probe(eye, vec3(0.05, 0.0, 1.0))); }")
    cost = report(src)["passes"][0]["cost"]
    assert cost["heaviest"] == 2 * 2 * 100 * 6
    labels = [s["label"] for s in cost["path"] if s["kind"] == "loop"]
    assert labels == ["aa samples", "aa samples", "march", "fbm octaves"]
    assert cost["calls_per_pixel"] > 2 * 2 * 100 * 6
    # executed tokens: every token weighted by the trips around it, so it exceeds the bare product of the bounds
    assert cost["work"] > 10 * cost["heaviest"]


# ---------- census ----------

def _save(sid, name, code):
    C.save_shader(pass_json(sid, [rp("Image", "image", code, [], [{"id": IMG, "channel": 0}])]) |
                  {"info": {"id": sid, "name": name, "username": "tester", "date": "1700000000"}})


@pytest.fixture()
def corpus(tmp_path, monkeypatch):
    root = tmp_path / "state" / "arsenal" / "shaders" / "corpus"
    monkeypatch.setattr(C, "CORPUS", root)
    marchers = [("Mrch01", shader(SOFT, LIT)),
                ("Mrch02", shader(SOFT + "float extra(float x) { return x; }", LIT + " paint *= 0.9;")),
                ("Mrch03", shader(SOFT, LIT + " paint = paint * 0.8;"))]
    noisers = [("Nois01", shader(FBM, "paint = vec3(layered(scr + layered(scr)));")),
               ("Nois02", shader(FBM, "paint = vec3(layered(scr * 2.0 + layered(scr)));")),
               ("Nois03", shader(FBM, "paint = vec3(layered(scr * 3.0 + layered(scr)));"))]
    for sid, code in marchers + noisers:
        _save(sid, sid.lower(), code)
    sets = {"loved": ["Mrch01", "Nois01", "Gone01"]}
    (root / "sets.json").write_text(json.dumps(sets), encoding="utf-8")
    return root


def test_census_counts_tags_and_finds_the_two_families(corpus):
    res = K.run(C.all_ids(), "all")
    freq = {t["tag"]: t["shaders"] for t in res["tags"]}
    assert freq["raymarch.sphere_trace"] == 3 and freq["noise.fbm"] == 3 and freq["lighting.soft_shadow"] == 3
    fams = sorted(sorted(m["id"] for m in f["members"]) for f in res["families"])
    assert fams == [["Mrch01", "Mrch02", "Mrch03"], ["Nois01", "Nois02", "Nois03"]]
    assert all(f["characteristic"] for f in res["families"])
    pair = {(p["a"], p["b"]): p for p in res["group_pairs"]}
    assert pair[("lighting", "raymarch")]["both"] == 3


def test_census_writes_private_tables_and_lists_what_it_could_not_dissect(corpus):
    res = K.run(C.load_sets(corpus)["loved"], "loved")
    assert res["errors"] == [{"id": "Gone01", "error": "not in the corpus"}]
    # a set is placed in the CORPUS families: one loved shader in each lineage
    placed = sorted((f["corpus_size"], [m["id"] for m in f["in_set"]]) for f in res["corpus_families"])
    assert placed == [(3, ["Mrch01"]), (3, ["Nois01"])] and res["corpus_loners"] == []
    paths = K.write(res)
    md = Path(paths["markdown"]).read_text(encoding="utf-8")
    assert Path(paths["markdown"]).parent == corpus.parent / "census"
    assert "# Shader census: loved (2 shaders)" in md and "PRIVATE" in md and "## Families" in md
    assert "## Where this set sits in the corpus families" in md
    assert json.loads(Path(paths["json"]).read_text(encoding="utf-8"))["shaders"] == 2
    assert Path(paths["run"]).exists()


def test_cluster_is_deterministic_and_order_independent():
    rows = [{"id": f"s{i}", "name": "", "author": "", "tags": t} for i, t in enumerate(
        [["a.x", "b.y"], ["a.x", "b.y"], ["c.z"], ["c.z", "d.w"], ["a.x", "b.y", "e.v"]])]
    # weighted distances: s0-s4 0.56, s2-s3 0.62, across 1.0 -- a 0.65 cut makes exactly two families
    first = K.cluster(rows, 0.65)
    again = K.cluster(list(rows), 0.65)
    assert first == again
    assert sorted(map(sorted, ([rows[i]["id"] for i in g] for g in first))) == [["s0", "s1", "s4"], ["s2", "s3"]]


# ---------- the doors ----------

def test_verbs_register_through_the_cli_hook():
    cli._load_extensions()
    assert {"dissect", "census"} <= set(cli.VERBS)


def test_dissect_verb_reads_a_frag_file(tmp_path, capsys):
    frag = tmp_path / "scene.frag"
    frag.write_text(shader(SOFT, LIT), encoding="utf-8")
    assert cli.main(["dissect", str(frag)]) == 0
    out = capsys.readouterr().out
    assert "lighting.soft_shadow" in out and "COST" in out and "scene.frag:" in out
    assert cli.main(["dissect", str(frag), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["api"] == D.API


def test_census_verb_with_no_write_writes_nothing(corpus, capsys):
    assert cli.main(["census", "--no-write"]) == 0
    assert "census of all: 6 shaders" in capsys.readouterr().out
    assert not (corpus.parent / "census").exists()
    assert cli.main(["census", "--set", "nope"]) == 2


# ---------- the licence line: the dissector's own files carry no corpus code ----------

REPO = Path(__file__).resolve().parents[1]
DISSECTOR_FILES = ("arsenal/shaders/glsl.py", "arsenal/shaders/dissect.py", "arsenal/shaders/census.py",
                   "tests/test_shader_dissect.py")


@pytest.fixture(scope="module")
def corpus_index():
    from arsenal.shaders import licence_line as L
    index = L.build_index(REPO / "state" / "arsenal" / "shaders" / "corpus")
    if index is None:
        pytest.skip("the private corpus is absent (a fresh clone has none): nothing to measure against")
    return index


@pytest.mark.parametrize("rel", DISSECTOR_FILES)
def test_the_dissector_shares_no_12_token_run_with_the_corpus(rel, corpus_index, tmp_path):
    # The house measurement (py -m arsenal shader licence-line) over one file: a copy under arsenal/shaders/, a scope it
    # reads in full, since its scopes leave tests/ out. A breach is reported by line and corpus id only, never by text.
    from arsenal.shaders import licence_line as L
    copy = tmp_path / "arsenal" / "shaders" / Path(rel).name
    copy.parent.mkdir(parents=True)
    copy.write_bytes((REPO / rel).read_bytes())
    rep = L.scan(root=tmp_path, index=corpus_index)
    assert rep["scanned"]["files"] == 1
    breaches = [f"{rel}:{h['line']}-{h['end_line']} ({h['tokens']} tokens, {h['shape']}, corpus {h['corpus'][0]})"
                for h in rep["hits"] if not h["exempt"]]
    assert not breaches, f"{len(breaches)} run(s) of 12+ tokens shared with corpus shaders:\n" + "\n".join(breaches)
