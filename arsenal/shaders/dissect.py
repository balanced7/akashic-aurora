"""py -m arsenal shader dissect <id|path.json|path.frag> -- what a shader is made of: its techniques as tagged evidence
(file:line, a confidence, the numbers that matter), its cost, its dead code, its size.

WHY. Daniel, 2026-10-13: "break down the primitives and group them by category ... so we can have reusable structures."
Before the house can write a primitive library from what it loves, it has to know what the loved shaders are made of,
and reading 335 shaders by eye does not scale. So this file turns code into evidence: a raymarch loop is not "a
function called march", it is a loop whose body calls a distance function and advances t by what it returned; an fbm is
a loop accumulating noise with a frequency multiply and an amplitude decay, and its octaves, lacunarity and gain are read
off the literals. Every detector prefers the SHAPE of the math; a name alone can still earn a weak tag (0.5-0.65, see
below), which explain.py reports as inferred and never counts as a detection. Every tag carries the line that earned
it, so a reader can open the file and check -- census.py (the corpus-wide tables) depends on it.

HOW. arsenal/shaders/glsl.py reads each pass (Common prepended, as the compiler does) into functions, loops with literal
bounds, a call graph and a reachability walk. Detectors run over the LIVE functions only -- a technique in dead code is
not a technique the shader uses -- and match regular expressions over each function's flat text (tokens joined by one
space, see glsl.py). Confidence is a judgement scale, not a probability: 0.9+ the shape is unmistakable, 0.7-0.85 the
shape with one ambiguity, 0.5-0.65 a weaker shape or a name; MIN_CONF (0.5) is the floor for a tag to count.

COST. Three per-pixel views from the entry point down: the heaviest call path as the product of literal loop bounds
along it (an AA loop of 4 around a 128-step march whose distance function runs a 6-octave fbm = 3072), user-function
calls per pixel, and `work` -- tokens executed per pixel, each weighted by the trip counts around it. Bounds passed as
parameters (fbm(p, 6)) are resolved per call site. MEASURED, not assumed: against the 2026-10-13 `check` run (333
shaders, SwiftShader, 320x180) the Spearman rank correlations with ms/frame were code lines +0.82, work +0.78, calls per
pixel +0.77, heaviest path +0.50. That check times ONE frame right after compiling, and SwiftShader compiles at first
draw, so it mostly measures compile time (which tracks code size); the execution estimates wait on a second-frame
timing to be judged fairly.

THE ATLAS VIEW. `--atlas` places the tags in the house parts catalogue (arsenal/shaders/atlas.json): the categories its
tags land on, through the atlas's own tag table, plus the groups and parts the atlas names this shader as an exemplar of.
It is the bridge from "what this shader is made of" to "which house parts would rebuild it"; the Shelf (shelf.py) uses it.

THE LICENCE LINE. Output that quotes or summarises a corpus shader names other people's code: it is printed, or written
under state/arsenal/shaders/ (gitignored), never into a tracked file. The tests use synthetic shaders only.
"""
from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

from . import corpus as C
from . import glsl as G

API = "arsenal.shader-dissect/v1"
MIN_CONF = 0.5
EVIDENCE_SHOWN = 3              # evidence lines per technique in the human report
# Trips charged to a loop with no literal bound, in the work estimate only. Swept 1/8/16/32/64 against the
# 2026-10-13 check run: rank correlation 0.766/0.777/0.779/0.780/0.778 -- flat past 8, so the choice barely matters.
ASSUMED_TRIPS = 16

# ---------- the vocabulary: every tag a detector can emit, with what it means ----------

TAGS: Dict[str, str] = {
    "raymarch.sphere_trace": "a loop that calls a distance function and advances t by the distance it returned",
    "raymarch.fixed_step": "a loop that walks a ray (ro + rd*t) by a fixed or density-driven step, not a distance bound",
    "raymarch.jitter": "the march start offset by a hash/noise/blue-noise value (banding -> grain)",
    "sdf.sphere": "length(p) - r: sphere (3D) or circle (2D)",
    "sdf.box": "box distance: length(max(q,0)) tail or max of |p|-b components",
    "sdf.torus": "length(vec2(length(p.xz)-R, p.y)) - r",
    "sdf.capsule": "segment/capsule: the point projected onto the segment, the fraction clamped to [0, 1]",
    "sdf.cylinder": "length(p.xz) - r: infinite cylinder (or a 2D circle in a swizzle)",
    "sdf.octahedron": "(|x|+|y|+|z| - s) * 0.57735",
    "sdf.named": "a distance function named in the sdXxx/fXxx convention (name only)",
    "sdf.smooth_min": "a smooth union/intersection (polynomial, quadratic, exponential or power smin)",
    "domain.repeat": "domain repetition: mod(p+c/2,c)-c/2, p-c*round(p/c), fract(p)-0.5",
    "domain.rotate2d": "a 2D rotation matrix from the cosine and sine of one angle (or the golfed vec4-phase form)",
    "domain.polar": "polar coordinates: atan(y, x) with a radius",
    "domain.kaleidoscope": "a polar fold: the angle from atan is mod-ed, mirrored or snapped to sectors",
    "normal.central_diff": "normal by central differences: f(p+e)-f(p-e) per axis (6 taps in 3D)",
    "normal.forward_diff": "normal by forward differences: f(p+e)-f(p) per axis (4 taps in 3D)",
    "normal.tetrahedral": "normal by the tetrahedron technique: 4 taps along (+-1,+-1,+-1)",
    "normal.screen_space": "normal from screen derivatives: cross(dFdx(p), dFdy(p))",
    "lighting.soft_shadow": "a shadow march keeping min(res, k*h/t): penumbra from the closest miss",
    "lighting.hard_shadow": "a shadow march that only answers hit or miss",
    "lighting.ao": "ambient occlusion: a few distance samples along the normal, accumulated with decay",
    "lighting.diffuse": "a clamped N.L term",
    "lighting.specular": "a pow()'d specular lobe (Phong/Blinn)",
    "lighting.fresnel": "a Schlick-style pow(1 - dot(n,v), k) term",
    "lighting.fog": "distance fog: mix(col, fogColor, 1 - exp(-k*t))",
    "noise.value": "value noise: hashed lattice corners, interpolated",
    "noise.gradient": "gradient noise: dot(random gradient, offset) at lattice corners",
    "noise.simplex": "simplex noise: the skewed lattice (F2 0.366, G2 0.211 or the 3D 1/3, 1/6)",
    "noise.texture": "noise read from a texture (a lattice in a noise image, or texture taps in an fbm)",
    "noise.fbm": "fractal Brownian motion: octaves of noise with a frequency multiply and an amplitude decay",
    "noise.domain_warp": "noise sampled at a position displaced by noise (fbm(p + fbm(p)))",
    "hash.sin_fract": "the fract(sin(x) * 43758.5453) hash (precision-fragile on some GPUs)",
    "hash.integer": "an integer hash (uint mixing with xor/shift/multiply)",
    "hash.fract_dot": "a sine-free float hash (Hoskins: fract(p * .1031), dot(p, p.yzx + 33.33))",
    "fractal.kifs": "a kaleidoscopic IFS: abs() folds (or plane reflections) and a scale inside a loop",
    "fractal.mandelbox": "the Mandelbox box fold: clamp(p, -1, 1) * 2 - p",
    "fractal.inversion": "sphere inversion in a loop (Apollonian, Kleinian): p *= k / dot(p, p)",
    "fractal.escape_time": "a complex iteration z = z^2 + c (Mandelbrot/Julia)",
    "fractal.mandelbulb": "the Mandelbulb power formula in spherical coordinates",
    "cellular.voronoi": "voronoi/worley: a 3x3 (or 3x3x3) neighbour search for the nearest feature point",
    "color.cosine_palette": "a + b*cos(2pi*(c*t + d)) (or a half-plus-half cosine with per-channel phases)",
    "color.gamma": "gamma encode: pow(c, 1/2.2) or 0.4545, or sqrt(c)",
    "color.gamma_decode": "gamma decode: pow(c, 2.2)",
    "color.srgb": "the exact sRGB transfer curve (1.055, 0.0031308, 12.92)",
    "color.dither": "noise of about 1/255 added before output",
    "color.hsv": "the HSV-to-RGB conversion: abs(mod(h*6 + vec3(0,4,2), 6) - 3) - 1",
    "color.vignette": "the 16*u*v*(1-u)*(1-v) vignette",
    "tonemap.reinhard": "x / (1 + x)",
    "tonemap.aces": "the ACES filmic fit (2.51, 0.03, 2.43, 0.59, 0.14) or fitted matrices",
    "tonemap.filmic": "a filmic curve (Hejl-Dawson 6.2/1.7, Uncharted 2)",
    "tonemap.tanh": "tanh(color) as a soft clip",
    "tonemap.exposure": "1 - exp(-color * k)",
    "glow.march": "additive 1/d or exp(-d) accumulated inside a march",
    "glow.accumulate": "additive 1/d or exp(-d) accumulated in a non-march loop",
    "volume.transmittance": "transmittance multiplied down in a loop (T *= exp(-density*dt))",
    "volume.front_to_back": "front-to-back compositing: sum += c * (1 - sum.a)",
    "feedback.self": "a buffer that reads its own previous frame",
    "feedback.cycle": "buffers that read each other in a cycle",
    "audio.input": "a music/mic/stream input sampled (row 0 spectrum, row 1 waveform)",
    "audio.sound_pass": "the shader synthesizes its own audio in a Sound pass (mainSound)",
    "input.mouse": "iMouse read",
    "input.keyboard": "the keyboard texture read",
    "animation.time": "iTime (or iDate) drives something",
    "animation.frame": "iFrame used beyond the anti-unroll and init idioms",
    "aa.supersample": "an anti-aliasing loop: N x N samples offset inside the pixel",
    "camera.lookat": "a look-at camera basis from cross(forward, up)",
}
GROUPS: Dict[str, str] = {
    "raymarch": "ray marching", "sdf": "signed distance shapes and operators", "domain": "domain operators",
    "normal": "normal estimation", "lighting": "lighting", "noise": "noise", "hash": "hashes", "fractal": "fractals",
    "cellular": "cellular", "color": "colour", "tonemap": "tone mapping", "glow": "glow", "volume": "volumetrics",
    "feedback": "feedback buffers", "audio": "audio", "input": "input", "animation": "animation",
    "aa": "anti-aliasing", "camera": "camera",
}

# ---------- flat-text helpers (see glsl.py: tokens joined by single spaces) ----------

ID = r"[A-Za-z_]\w*"
NUM = r"(?:\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+(?:[eE][-+]?\d+)?)[fF]?"
ONE = r"(?:1(?:\.0*)?|1\.)"
ZERO = r"(?:0(?:\.0*)?|\.0+)"
TWO_PI = 2 * math.pi
TEXTURE_CALLS = frozenset({"texture", "textureLod", "texelFetch", "texture2D", "textureGrad", "texture2DLod",
                           "textureLodOffset", "texelFetchOffset", "textureOffset"})
AUDIO_TYPES = frozenset({"music", "musicstream", "mic", "soundcloud"})
TIME_UNIFORMS = frozenset({"iTime", "iGlobalTime", "iDate"})

_ASSIGN_RE = re.compile(
    r"^(?:(?:const|highp|mediump|lowp) )*(?:(?P<type>" + ID + r") (?=" + ID + r"(?: \[ [^\]]* \])? =(?!=)))?"
    r"(?P<var>" + ID + r")(?P<member>(?: \. " + ID + r"| \[ [^\]]* \])*) (?P<op>=|\+=|-=|\*=|/=) (?P<rhs>.+)$")
_EMBEDDED_RE = re.compile(r"\( (" + ID + r") = ((?:[^()]|\( [^()]* \))+?) \)")
_CALL_RE = re.compile(r"(?<!\. )\b(" + ID + r") \(")
_IDENT_RE = re.compile(r"(?<!\. )\b(" + ID + r")\b")
_NUMBER_RE = re.compile(r"(?<![\w.])(" + NUM + r")(?![\w.])")
NOT_CALLS = frozenset({"if", "for", "while", "return", "switch", "else"})


@dataclass
class Assign:
    type: Optional[str]
    var: str
    member: str
    op: str
    rhs: str


def assigns(text: str) -> List[Assign]:
    """The assignment a statement makes, plus any chained (`t += d = map(p)`) or parenthesised (`(d = f(p)) < e`)."""
    out: List[Assign] = []
    m = _ASSIGN_RE.match(text)
    depth = 0
    while m and depth < 4:
        a = Assign(m.group("type"), m.group("var"), m.group("member") or "", m.group("op"), m.group("rhs"))
        out.append(a)
        m = _ASSIGN_RE.match(a.rhs)
        depth += 1
    for e in _EMBEDDED_RE.finditer(text):
        out.append(Assign(None, e.group(1), "", "=", e.group(2)))
    return out


def calls_in(text: str) -> List[str]:
    return [c for c in _CALL_RE.findall(text) if c not in NOT_CALLS]


def idents_in(text: str) -> Set[str]:
    return set(_IDENT_RE.findall(text))


def numbers_in(text: str) -> List[float]:
    out = []
    for n in _NUMBER_RE.findall(text):
        try:
            out.append(float(n.rstrip("fF")))
        except ValueError:
            pass
    return out


def paren_inner(text: str, i: int) -> str:
    """The text inside the parenthesis opening at text[i] (flat text, so the inner spaces are trimmed)."""
    depth = 0
    for j in range(i, len(text)):
        c = text[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[i + 1:j].strip()
    return text[i + 1:].strip()


def split_args(inner: str) -> List[str]:
    out, depth, cur = [], 0, []
    for tok in inner.split(" "):
        if tok in ("(", "["):
            depth += 1
        elif tok in (")", "]"):
            depth -= 1
        if tok == "," and depth == 0:
            out.append(" ".join(cur))
            cur = []
        else:
            cur.append(tok)
    if cur:
        out.append(" ".join(cur))
    return out


def call_sites(text: str, names: Iterable[str]) -> Iterator[Tuple[int, str, str]]:
    """(offset, name, inner argument text) for every call to one of `names` in flat text."""
    names = set(names)
    if not names:
        return
    for m in _CALL_RE.finditer(text):
        if m.group(1) in names:
            yield m.start(), m.group(1), paren_inner(text, m.end() - 1)


def _depends(start: Iterable[str], target: str, deps: Dict[str, Set[str]]) -> bool:
    """Does any name in `start` reach `target` through the loop's assignments (x = f(y) makes x depend on y)?"""
    stack, seen = list(start), set()
    while stack:
        v = stack.pop()
        if v == target:
            return True
        if v in seen:
            continue
        seen.add(v)
        stack.extend(deps.get(v, ()))
    return False


# ---------- what a shader is, for the dissector ----------

@dataclass(eq=False)
class PassView:
    name: str
    type: str
    file: str
    prog: G.Program
    unit: G.Unit
    inputs: List[dict] = field(default_factory=list)
    outputs: List[dict] = field(default_factory=list)


@dataclass(eq=False)
class ShaderView:
    sid: str
    name: str
    author: str
    source: str
    passes: List[PassView]
    common: Optional[G.Program] = None


def view_from_json(shader: dict, source: str = "") -> ShaderView:
    info = shader.get("info") or {}
    rps = shader.get("renderpass") or []
    common = None
    for rp in rps:
        if rp.get("type") == "common":
            common = G.Program(rp.get("code") or "", file=C.pass_stem(rp.get("name") or "common") + ".glsl")
    passes = []
    for rp in rps:
        if rp.get("type") == "common":
            continue
        prog = G.Program(rp.get("code") or "", file=C.pass_stem(rp.get("name")) + ".glsl", base=common)
        # A Shadertoy pass, never a library: with no entry point found, none of its functions is walked as one.
        passes.append(PassView(rp.get("name") or "Image", rp.get("type") or "image", prog.file, prog,
                               G.Unit([common, prog], library=False),
                               [C._input_row(i) for i in rp.get("inputs") or []],
                               [{"id": o.get("id"), "channel": o.get("channel")} for o in rp.get("outputs") or []]))
    return ShaderView(info.get("id") or "", info.get("name") or "", info.get("username") or "", source, passes, common)


def view_from_source(code: str, file: str = "image.glsl", source: str = "") -> ShaderView:
    prog = G.Program(code, file=file)
    pv = PassView("Image", "image", file, prog, G.Unit([prog]))
    return ShaderView(Path(file).stem, Path(file).stem, "", source or file, [pv])


def load(target: str, corpus: Optional[Path] = None) -> ShaderView:
    """A corpus id (or a name that resolves to one), a Shadertoy JSON file, or a .frag/.glsl file."""
    p = Path(target)
    if p.suffix.lower() == ".json" and p.exists():
        return view_from_json(json.loads(p.read_text(encoding="utf-8")), str(p))
    if p.suffix.lower() in (".frag", ".glsl", ".fs", ".txt") and p.exists():
        return view_from_source(p.read_text(encoding="utf-8"), p.name, str(p))
    hits = C.resolve(target, corpus)
    if not hits:
        raise FileNotFoundError(f"no shader, file or corpus id matches {target!r}")
    sid = hits[0]
    return view_from_json(C.load_shader(sid, corpus), str(C._root(corpus) / "shaders" / sid / "shader.json"))


# ---------- evidence and the per-pass context ----------

@dataclass
class Evidence:
    tag: str
    file: str
    line: int
    conf: float
    detail: str
    params: dict = field(default_factory=dict)

    @property
    def group(self) -> str:
        return self.tag.split(".", 1)[0]

    def row(self) -> dict:
        return {"tag": self.tag, "file": self.file, "line": self.line, "conf": round(self.conf, 2),
                "detail": self.detail, "params": self.params}


class Ctx:
    """One pass as the detectors see it: its live functions, and what earlier detectors learned (which functions are
    distance functions, noises, hashes; which loops are marches) so later ones can lean on it."""

    def __init__(self, view: ShaderView, pv: PassView):
        self.view, self.pv, self.unit = view, pv, pv.unit
        self.live = self.unit.reachable()
        self.fns: List[G.Fn] = [fn for name in sorted(self.live) for fn in self.unit.nodes(name)]
        self.functions = [fn for fn in self.fns if fn.kind != "macro"]
        self.user = self.unit.callables()
        self.entries = set(self.unit.entries())
        self.df: Set[str] = set()
        self.scene: Set[str] = set()              # distance functions and everything they call
        self.noise: Set[str] = set()
        self.fbm: Set[str] = set()
        self.hash: Set[str] = set()
        self.march: Dict[int, dict] = {}          # id(loop) -> what the raymarch detector found
        self.loop_labels: Dict[int, str] = {}     # id(loop) -> a short name for the cost path
        self.evidence: List[Evidence] = []

    def add(self, tag: str, file: str, line: int, conf: float, detail: str, **params) -> None:
        assert tag in TAGS, tag
        self.evidence.append(Evidence(tag, file, line, round(min(conf, 0.99), 2), detail,
                                      {k: v for k, v in params.items() if v is not None}))

    def value(self, text: str, fn: Optional[G.Fn] = None):
        """The constant value of a flat-text expression in a function's scope, or None."""
        prog = fn.prog if fn is not None and fn.prog is not None else self.unit.program
        toks = [t for t in G.lex(text) if t.kind not in (G.COMMENT, G.PP)]
        return prog.evaluate(toks, fn.locals if fn is not None else None)

    def is_df_candidate(self, name: str) -> bool:
        if name not in self.user or name in self.entries or name in G.ENTRY_POINTS:
            return False
        for fn in self.unit.nodes(name):
            if fn.kind == "macro":
                return bool(fn.params)
            if fn.ret != "void" and fn.params:
                return True
        return False

    def loop_stmts(self, fn: G.Fn, loop: G.Loop) -> List[G.Stmt]:
        return fn.loop_statements(loop)

    def resolved_bound(self, fn: G.Fn, loop: G.Loop) -> Tuple[Optional[int], str]:
        """A loop's trip count: literal, or a parameter bound resolved from the call sites that reach it."""
        if loop.bound is not None:
            return loop.bound, ""
        if not loop.symbolic:
            return None, loop.note
        param = loop.symbolic["param"]
        idx = next((i for i, p in enumerate(fn.params) if p.name == param), None)
        if idx is None:
            return None, loop.note
        seen = set()
        for caller in self.fns:
            for c in caller.calls:
                if c.name != fn.name or idx >= len(c.args):
                    continue
                a, b = c.args[idx]
                v = caller.prog.evaluate(caller.toks[a:b], caller.locals)
                n = loop.bound_with(v)
                if n is not None:
                    seen.add(n)
        if not seen:
            return None, loop.note
        return max(seen), (f"{param} from its call sites: " + ", ".join(str(n) for n in sorted(seen)))


def _vec_vars(fn: G.Fn) -> Set[str]:
    """Names a function holds colours in: vec3/vec4 params and locals (and the out param of an entry point)."""
    out = {p.name for p in fn.params if p.type in ("vec3", "vec4")}
    out.update(re.findall(r"\bvec[34] (" + ID + r")\b(?! \()", fn.flat))
    return out


# ---------- detectors: raymarching ----------

_SDF_MATH_RE = re.compile(r"\b(?:length|min|max|abs|dot|distance) \(")
_SHADOW_NAME_RE = re.compile(r"shadow|shad$|^sha$|occl", re.I)
_AO_NAME_RE = re.compile(r"(?:^|_|[a-z])ao|occ|ambient", re.I)


def _march_shape(ctx: Ctx, fn: G.Fn, loop: G.Loop) -> Optional[dict]:
    """A sphere-tracing loop: a distance d from a distance function (or inline SDF math) of a point that depends on
    the variable the loop then advances by d."""
    stmts = ctx.loop_stmts(fn, loop)
    dvars: Dict[str, Tuple[Optional[str], Set[str]]] = {}
    deps: Dict[str, Set[str]] = {}
    for st in stmts:
        for a in assigns(st.text):
            ids = idents_in(a.rhs)
            deps.setdefault(a.var, set()).update(ids)
            if a.op != "=":
                continue
            df = next((c for c in calls_in(a.rhs) if ctx.is_df_candidate(c)), None)
            if df:
                dvars[a.var] = (df, ids - {df})
            elif _SDF_MATH_RE.search(a.rhs):
                dvars[a.var] = (None, ids)
    # a distance copied under another name (dist = res.x; currentDist = model.dist) is still the distance
    for st in stmts:
        for a in assigns(st.text):
            src = idents_in(a.rhs) & set(dvars)
            if a.op == "=" and a.var not in dvars and src and not calls_in(a.rhs):
                dvars[a.var] = dvars[sorted(src)[0]]
    for st in stmts:
        for a in assigns(st.text):
            if not (a.op == "+=" or (a.op == "=" and re.match(re.escape(a.var) + r" \+ ", a.rhs))):
                continue
            ids = idents_in(a.rhs)
            used = [v for v in dvars if v in ids and v != a.var]
            direct = [c for c in calls_in(a.rhs) if ctx.is_df_candidate(c)]
            if used:
                df, argids = dvars[used[0]]
            elif direct:
                df, argids = direct[0], ids
            else:
                continue
            if a.var in argids or _depends(argids, a.var, deps):
                dvar = used[0] if used else None
                return {"stmts": stmts, "adv": a.var, "dvar": dvar, "df": df, "dvars": dvars, "line": st.line,
                        "rhs": a.rhs, "member": a.member}
    return None


def detect_raymarch(ctx: Ctx) -> None:
    for fn in ctx.functions:
        for loop in fn.loops:
            shape = _march_shape(ctx, fn, loop)
            steps, why = ctx.resolved_bound(fn, loop)
            if shape is None:
                _fixed_step(ctx, fn, loop, steps)
                continue
            stmts, adv, dvar, df = shape["stmts"], shape["adv"], shape["dvar"], shape["df"]
            texts = [s.text for s in stmts] + ([fn.text(*loop.cond)] if loop.cond else [])
            hit = eps = far = None
            if dvar:
                for t in texts:
                    m = re.search(r"\b" + dvar + r"\b(?: \. \w+)?(?: \))? < (?:\( )?(" + NUM + r"(?: \* \w+)?|" + ID + r")", t)
                    if m and ("if (" in t or t is texts[-1]):
                        hit, eps = True, m.group(1)
                        break
                    m = re.search(r"\b" + dvar + r"\b(?: \. \w+)? > (" + NUM + r"|" + ID + r")", t)
                    if m and t is texts[-1]:
                        hit, eps = True, m.group(1)
                        break
            for t in texts:
                m = re.search(r"\b" + adv + r"\b > (" + NUM + r"|" + ID + r")", t) or \
                    (re.search(r"\b" + adv + r"\b < (" + NUM + r"|" + ID + r")", t) if t is texts[-1] else None)
                if m:
                    far = m.group(1)
                    break
            relax = None
            if dvar:
                m = re.fullmatch(re.escape(dvar) + r"(?: \. \w+)? \* (" + NUM + r")|(" + NUM + r") \* " + re.escape(dvar) +
                                 r"(?: \. \w+)?", shape["rhs"])
                if m:
                    relax = float((m.group(1) or m.group(2)).rstrip("fF"))
            conf = 0.8 if df else 0.65
            conf += 0.1 if hit else 0
            conf += 0.05 if far else 0
            soft = any(_soft_shadow_rhs(a) for s in stmts for a in assigns(s.text))
            role = "shadow" if (soft or _SHADOW_NAME_RE.search(fn.name)) else "march"
            info = {"role": role, "df": df, "adv": adv, "dvar": dvar, "steps": steps, "fn": fn, "loop": loop,
                    "soft": soft, "dvars": shape["dvars"]}
            ctx.march[id(loop)] = info
            if df:
                ctx.df.add(df)
            if role == "shadow":
                ctx.loop_labels[id(loop)] = "shadow march"
                continue
            ctx.loop_labels[id(loop)] = "march"
            ctx.add("raymarch.sphere_trace", fn.file, loop.line, conf,
                    f"{loop.kind}-loop in {fn.name}(): {adv} advances by "
                    + (f"{dvar} = {df}(...)" if df and dvar else f"{df}(...)" if df else f"inline distance {dvar}"),
                    steps=steps, df=df or "inline", advance=adv, hit_eps=eps, max_dist=far, step_scale=relax,
                    bound_note=why or None)
    # everything a distance function calls belongs to the scene
    scene, stack = set(), list(ctx.df)
    while stack:
        n = stack.pop()
        if n not in scene:
            scene.add(n)
            stack.extend(ctx.unit.graph.get(n, ()))
    ctx.scene = scene
    _march_jitter(ctx)


def _fixed_step(ctx: Ctx, fn: G.Fn, loop: G.Loop, steps) -> None:
    stmts = ctx.loop_stmts(fn, loop)
    for st in stmts:
        for a in assigns(st.text):
            if a.op != "+=" or a.member:
                continue
            A = re.escape(a.var)
            ray = re.compile(r"\b" + ID + r" \+ " + ID + r" \* " + A + r"\b|\b" + ID + r" \+ " + A + r" \* " + ID +
                             r"\b|\b" + A + r" \* " + ID + r" \+ " + ID + r"\b|\b" + ID + r" \* " + A + r" \+ " + ID + r"\b")
            if any(ray.search(s.text) for s in stmts if s is not st):
                ctx.loop_labels.setdefault(id(loop), "fixed-step march")
                ctx.march.setdefault(id(loop), {"role": "fixed", "adv": a.var, "fn": fn, "loop": loop, "dvar": None,
                                                "df": None, "steps": steps, "dvars": {}})
                ctx.add("raymarch.fixed_step", fn.file, loop.line, 0.65,
                        f"{loop.kind}-loop in {fn.name}(): the ray point moves with {a.var} += {a.rhs[:40]}",
                        steps=steps, advance=a.var)
                return


def _march_jitter(ctx: Ctx) -> None:
    noisy = ctx.hash | ctx.noise | TEXTURE_CALLS
    for info in list(ctx.march.values()):
        if info["role"] != "march":
            continue
        fn, loop, adv = info["fn"], info["loop"], info["adv"]
        for st in fn.statements(fn.start, loop.keyword):
            for a in assigns(st.text):
                if a.var != adv or a.op not in ("=", "+="):
                    continue
                cs = set(calls_in(a.rhs))
                if cs & noisy or re.search(r"fract \( sin \(|\biChannel\d\b|hash|rand|noise|dither", a.rhs, re.I):
                    ctx.add("raymarch.jitter", fn.file, st.line, 0.8,
                            f"{adv} starts at a per-pixel random offset: {adv} {a.op} {a.rhs[:50]}")
                    return


# ---------- detectors: distance shapes and domain operators ----------

_SDF_SHAPES = (
    ("sdf.box", re.compile(r"length \( max \( " + ID + r"(?: \. \w+)? , " + ZERO + r" \) \)"), 0.85,
     "length(max(q, 0.)) -- the exact box tail"),
    ("sdf.box", re.compile(r"max \( (\w+) \. x , max \( \1 \. y , \1 \. z \) \)"), 0.7,
     "the largest component of q -- a box interior"),
    ("sdf.torus", re.compile(r"length \( vec2 \( length \( \w+ \. \w\w \) - [\w.]+ , \w+ \. \w \) \) - "), 0.9,
     "length(vec2(length(p.xz) - R, p.y)) - r"),
    ("sdf.capsule", re.compile(r"clamp \( dot \( (\w+) , (\w+) \) / dot \( \2 , \2 \) , " + ZERO + r" , " + ONE +
                               r" \)"), 0.85, "a clamped projection onto a segment -- a capsule"),
    ("sdf.cylinder", re.compile(r"length \( \w+ \. (?:xz|zx|xy|yx|yz|zy) \) - (?:" + NUM + r"|\w+)(?! \.| \()"), 0.6,
     "length(p.xz) - r"),
    ("sdf.sphere", re.compile(r"length \( \w+(?: [-+] \w+)? \) - (?:" + NUM + r"|\w+)(?! \.| \(| \[)"), 0.75,
     "length(p) - r"),
)
_OCTA_RE = re.compile(r"abs \( \w+ \. x \) \+ abs \( \w+ \. y \) \+ abs \( \w+ \. z \)|dot \( abs \( \w+ \) , vec3 \( "
                      + ONE + r" \)")
_SDF_NAME_RE = re.compile(r"^(?:sd|ud|sdf_?|f(?=[A-Z]))(\w+)$")
_SDF_NAME_KINDS = (("sphere", "sdf.sphere"), ("box", "sdf.box"), ("cube", "sdf.box"), ("torus", "sdf.torus"),
                   ("capsule", "sdf.capsule"), ("cylinder", "sdf.cylinder"), ("octahedron", "sdf.octahedron"))
_SMIN = (
    ("polynomial", re.compile(r"mix \( [^;]*\) [-+] [^;]*?\b(\w+) \* \( " + ONE + r" - \1 \)"), 0.9),
    ("quadratic", re.compile(r"max \( (\w+) - abs \( (\w+) - (\w+) \) , " + ZERO + r" \)"), 0.85),
    ("exponential", re.compile(r"log2? \( exp2? \( - ?[\w.]+ \* \w+ \) \+ exp2? \( - ?[\w.]+ \* \w+ \) \)"), 0.9),
    ("power", re.compile(r"pow \( \( \w+ \* \w+ \) / \( \w+ \+ \w+ \) , " + ONE + r" / \w+ \)"), 0.85),
)
_SMIN_NAME_RE = re.compile(r"^(?:smin|smax|smoothmin|smoothmax|sminCubic|sminExp|sminPoly|opSmooth\w*|fOp\w*Soft\w*|"
                           r"smoothUnion|smoothSubtraction|smoothIntersection)$", re.I)
_REPEAT = (
    (re.compile(r"mod \( [^;]*?, (\w+(?: \. \w+)?) \) - (?:0?\.5 \* \1|\1 \* 0?\.5|\1 / 2\.?0*)\b"), 0.85,
     "mod(p + c/2, c) - c/2"),
    (re.compile(r"(\w+(?: \. \w+)?) - (\w+(?: \. \w+)?|" + NUM + r") \* round \( \1 / \2 \)"), 0.9, "p - c*round(p/c)"),
    (re.compile(r"fract \( [^;]*?\) - 0?\.5\b(?! \*)"), 0.6, "fract(p) - 0.5 cell coordinates"),
)
_REPEAT_NUM_RE = re.compile(r"mod \( [^;]*?, (" + NUM + r") \) - (" + NUM + r")")
_REPEAT_NAME_RE = re.compile(r"^(?:pMod\w*|opRep\w*|repeat\w*|rep)$", re.I)
_ROT_RES = (
    (re.compile(r"mat2 \( cos \( [^;]*?\) , -? ?sin \( [^;]*?\) , -? ?sin \( [^;]*?\) , cos \("), 0.9,
     "mat2(cos a, -sin a, sin a, cos a)"),
    (re.compile(r"mat2 \( cos \( [^;]*?\+ vec4 \( " + ZERO + r" , "), 0.9, "mat2 of cos(angle + phase vec4)"),
    (re.compile(r"mat2 \( (\w+) , -? ?(\w+) , -? ?\2 , \1 \)"), 0.75, "mat2(c, -s, s, c)"),
)


def _vector_vars(fn: G.Fn) -> Set[str]:
    out = {p.name for p in fn.params if p.type in ("vec2", "vec3", "vec4")}
    out.update(re.findall(r"\bvec[234] (" + ID + r")\b(?! \()", fn.flat))
    return out


def _lands_in_vector(fn: G.Fn, text: str, pos: int) -> bool:
    """Is the statement around text[pos] an assignment to a vec2/vec3/vec4 (or a vector return)?"""
    a = max(text.rfind(";", 0, pos), text.rfind("{", 0, pos), text.rfind("}", 0, pos)) + 1
    st = text[a:pos].strip()
    m = _ASSIGN_RE.match(st + " _")
    if m:
        return (m.group("type") or "") in ("vec2", "vec3", "vec4") or m.group("var") in _vector_vars(fn)
    return st.startswith("return") and (fn.ret or "") in ("vec2", "vec3", "vec4")


def detect_sdf(ctx: Ctx) -> None:
    for fn in ctx.fns:
        text = fn.flat
        found: Set[str] = set()
        for tag, rx, conf, what in _SDF_SHAPES:
            if tag in found:
                continue
            m = rx.search(text)
            if m:
                if tag == "sdf.sphere" and re.match(r"length \( \w+ \. ", m.group()):
                    continue
                found.add(tag)
                ctx.add(tag, fn.file, fn.line_at(m.start()), conf + (0.05 if fn.name in ctx.scene else 0),
                        f"{what} in {fn.name}()")
        m = _OCTA_RE.search(text)
        if m and re.search(r"0?\.577\d*", text):
            ctx.add("sdf.octahedron", fn.file, fn.line_at(m.start()), 0.85, f"|x|+|y|+|z| scaled by 0.577 in {fn.name}()")
        nm = _SDF_NAME_RE.match(fn.name)
        if nm and fn.kind != "macro":
            low = nm.group(1).lower()
            tag = next((t for k, t in _SDF_NAME_KINDS if k in low), "sdf.named")
            ctx.add(tag if tag not in found else "sdf.named", fn.file, fn.line, 0.6, f"named {fn.name}()")
        for variant, rx, conf in _SMIN:
            m = rx.search(text)
            if m:
                ctx.add("sdf.smooth_min", fn.file, fn.line_at(m.start()), conf, f"{variant} smooth min in {fn.name}()",
                        variant=variant)
                break
        else:
            if _SMIN_NAME_RE.match(fn.name):
                ctx.add("sdf.smooth_min", fn.file, fn.line, 0.6, f"named {fn.name}()", variant="named")
        for rx, conf, what in _REPEAT:
            m = rx.search(text)
            if m and _HSV_RE.search(text[max(0, m.start() - 10):m.end() + 40]):
                m = None                   # hsv-to-rgb's mod(h*6 + vec3(0,4,2), 6) - 3 is a colour, not a tiling
            if m and what.startswith("fract"):
                m = next((x for x in rx.finditer(text) if _lands_in_vector(fn, text, x.start())), None)
            if m:
                ctx.add("domain.repeat", fn.file, fn.line_at(m.start()), conf, f"{what} in {fn.name}()")
                break
        else:
            m = _REPEAT_NUM_RE.search(text)
            if m and _HSV_RE.search(text[max(0, m.start() - 10):m.end() + 40]):
                m = None
            if m and abs(float(m.group(1).rstrip("fF")) - 2 * float(m.group(2).rstrip("fF"))) < 1e-6:
                ctx.add("domain.repeat", fn.file, fn.line_at(m.start()), 0.8, f"mod(p, c) - c/2 in {fn.name}()")
            elif _REPEAT_NAME_RE.match(fn.name):
                ctx.add("domain.repeat", fn.file, fn.line, 0.65, f"named {fn.name}()")
        for rx, conf, what in _ROT_RES:
            m = rx.search(text)
            if m:
                if conf < 0.8:   # mat2(c,-s,s,c) needs c and s to be a cosine and a sine
                    c, s = m.group(1), m.group(2)
                    if not (re.search(r"\b" + c + r" = cos \(", text) and re.search(r"\b" + s + r" = sin \(", text)):
                        continue
                ctx.add("domain.rotate2d", fn.file, fn.line_at(m.start()), conf, f"{what} in {fn.name}()")
                break


# ---------- detectors: normals, shadows, occlusion ----------

_SWZ_OFF_RE = re.compile(r"([-+]) (?:[\w.]+ \* )?(\w+) \. ([xyzw]{2,3})\b")
_VEC_OFF_RE = re.compile(r"([-+]) vec([23]) \( ([^()]*?) \)")
_TETRA = {"xyy", "yyx", "yxy", "xxx"}


_COMP_OFF_RE = re.compile(r"^vec([23]) \( (.+) \)$")


def _offsets(arg: str) -> List[Tuple[str, str]]:
    """The per-axis offsets in a tap's argument: p + e.xyy, p - vec3(e, 0, 0), or vec3(p.x + e, p.y, p.z)."""
    out = [(m.group(1), m.group(3)) for m in _SWZ_OFF_RE.finditer(arg)]
    for m in _VEC_OFF_RE.finditer(arg):
        comps = [c.strip() for c in m.group(3).split(",")]
        for k, comp in enumerate(comps):
            c = comp.replace(" ", "")
            if c and not re.fullmatch(r"-?" + ZERO.replace(" ", ""), c):
                sign = m.group(1)
                if c.startswith("-"):
                    sign = "+" if sign == "-" else "-"
                out.append((sign, "axis" + "xyz"[k]))
                break
    m = _COMP_OFF_RE.match(arg.strip())
    if m and not out:
        for k, comp in enumerate(split_args(m.group(2))[:3]):
            mm = re.fullmatch(r"\w+ \. [xyzw] ([-+]) .+", comp.strip())
            if mm:
                out.append((mm.group(1), "axis" + "xyz"[k]))
    return out


def detect_normals(ctx: Ctx) -> None:
    for fn in ctx.functions:
        text = fn.flat
        m = re.search(r"cross \( dFd[xy] \( ", text)
        if m:
            ctx.add("normal.screen_space", fn.file, fn.line_at(m.start()), 0.9, f"cross(dFdx, dFdy) in {fn.name}()")
        groups: Dict[str, List[Tuple[int, str]]] = {}
        for off, name, inner in call_sites(text, ctx.user):
            if name == fn.name:
                continue
            args = split_args(inner)
            groups.setdefault(name, []).append((off, args[0] if args else ""))
        bonus = 0.05 if re.search(r"norm|nor$|^nor|grad", fn.name, re.I) else 0
        for callee, sites in groups.items():
            if len(sites) < 3:
                continue
            # a normal is a DIFFERENCE of taps; lattice corners (hash(i + vec2(1,0)) in a noise) are not
            differs = re.search(r"\b" + re.escape(callee) + r" \( [^;]*?\) (?:\. \w+ )?- ", text)
            plus, minus, swz = set(), set(), set()
            base = 0
            for _, arg in sites:
                offs = _offsets(arg)
                if not offs:
                    base += 1
                for sign, s in offs:
                    (plus if sign == "+" else minus).add(s)
                    swz.add(s)
            line = fn.line_at(sites[0][0])
            dfb = 0.05 if callee in ctx.df else 0
            if len(_TETRA & swz) >= 3 and "xxx" in swz:
                ctx.add("normal.tetrahedral", fn.file, line, 0.9 + dfb + bonus,
                        f"{len(sites)} taps of {callee}() along xyy/yyx/yxy/xxx in {fn.name}()", taps=len(sites), df=callee)
            elif len(plus & minus) >= 2 and differs:
                ctx.add("normal.central_diff", fn.file, line, 0.85 + dfb + bonus,
                        f"{len(sites)} taps of {callee}() at +-e per axis in {fn.name}()", taps=len(sites),
                        axes=len(plus & minus), df=callee)
            elif len(plus | minus) >= 2 and not (plus & minus) and base >= 1 and len(sites) <= 5 and differs:
                ctx.add("normal.forward_diff", fn.file, line, 0.8 + dfb + bonus,
                        f"{len(sites)} taps of {callee}() (one base, one per axis) in {fn.name}()", taps=len(sites),
                        df=callee)
        for loop in fn.loops:
            n, _ = ctx.resolved_bound(fn, loop)
            if n == 4 and re.search(r">> 1|0?\.5773", fn.text(loop.keyword, loop.end)) and \
                    re.search(r"\+= \w+ \* \w+ \(", fn.text(loop.keyword, loop.end)):
                ctx.add("normal.tetrahedral", fn.file, loop.line, 0.9, f"a 4-tap tetrahedral loop in {fn.name}()",
                        taps=4, form="loop")
                ctx.loop_labels[id(loop)] = "normal taps"


_OFFSET_POINT_RE = re.compile(r"\w+ \+ [\w.()]+ \* \w+|\w+ \+ \w+ \* [\w.()]+|\w+ \* [\w.()]+ \+ \w+")


def _soft_shadow_rhs(a: Assign) -> bool:
    if a.op != "=" or not a.rhs.startswith("min ( "):
        return False
    inner = paren_inner(a.rhs, a.rhs.index("("))
    args = split_args(inner)
    return len(args) == 2 and a.var in (args[0].split(" ")[0], args[1].split(" ")[0]) and " / " in inner


def detect_shadows_and_ao(ctx: Ctx) -> None:
    for fn in ctx.functions:
        for loop in fn.loops:
            info = ctx.march.get(id(loop))
            stmts = ctx.loop_stmts(fn, loop)
            calls_df = any(c for s in stmts for c in calls_in(s.text) if ctx.is_df_candidate(c))
            steps, _ = ctx.resolved_bound(fn, loop)
            soft = next(((s, a) for s in stmts for a in assigns(s.text) if _soft_shadow_rhs(a)), None)
            if soft and (calls_df or info):
                s, a = soft
                improved = bool(re.search(r"max \( " + ZERO + r" , \w+ - \w+ \)", a.rhs)) or \
                    any(re.search(r"= \w+ \* \w+ / \( 2\.?0* \* \w+ \)", x.text) for x in stmts)
                k = re.search(r"(" + NUM + r") \* \w+ / ", a.rhs)
                ctx.add("lighting.soft_shadow", fn.file, s.line, 0.9 if (info or _SHADOW_NAME_RE.search(fn.name)) else 0.8,
                        f"{a.var} = min({a.var}, ... / ...) in a march in {fn.name}()", steps=steps,
                        k=float(k.group(1).rstrip("fF")) if k else None, variant="improved" if improved else "classic")
                ctx.loop_labels[id(loop)] = "shadow march"
                continue
            if info and info["role"] == "shadow":
                ctx.add("lighting.hard_shadow", fn.file, loop.line, 0.7, f"a hit-or-miss shadow march in {fn.name}()",
                        steps=steps)
                continue
            if info:
                continue
            # ambient occlusion: distance taps at offsets along a direction, accumulated
            taps = []
            points = {a.var: a.rhs for s in stmts for a in assigns(s.text) if a.op == "=" and not a.member}
            for s in stmts:
                for a in assigns(s.text):
                    for off, name, inner in call_sites(a.rhs, [c for c in calls_in(a.rhs) if ctx.is_df_candidate(c)]):
                        arg = split_args(inner)[0] if inner else ""
                        if re.fullmatch(ID, arg) and arg in points:
                            arg = points[arg]          # the tap point was built first: aopos = nor*hr + pos
                        if _OFFSET_POINT_RE.search(arg):
                            taps.append((a.var, name))
            if not taps:
                continue
            dvars = {v for v, _ in taps}
            accum = None
            for s in stmts:
                for a in assigns(s.text):
                    if a.op in ("+=", "-=") and a.var not in dvars and (idents_in(a.rhs) & dvars or
                                                                       any(n in a.rhs for _, n in taps)):
                        accum = (s, a)
                        break
                if accum:
                    break
            if accum and (steps is None or steps <= 32):
                decay = any(re.search(r"\*= 0?\.\d+", s.text) for s in stmts)
                conf = 0.8 + (0.1 if _AO_NAME_RE.search(fn.name) else 0) + (0.05 if taps[0][1] in ctx.df else 0)
                ctx.add("lighting.ao", fn.file, loop.line, conf,
                        f"{steps or '?'} taps of {taps[0][1]}() along a direction, {accum[1].var} {accum[1].op} ... in {fn.name}()",
                        samples=steps, decay=decay or None)
                ctx.loop_labels[id(loop)] = "ao taps"


_DIFFUSE_RE = re.compile(r"(?:clamp|max) \( dot \( (\w+) , (\w+) \) , " + ZERO)
_SPEC_RE = re.compile(r"pow \( (?:clamp|max) \( dot \( [^;]*?\) , " + ZERO + r"(?: , " + ONE + r")? \) , (" + NUM +
                      r"|\w+) \)")
# pow(1 - dot(n, v), k), or of a variable NAMED for the facing ratio -- pow(1 - x, k) of any x is just a ramp
_FRESNEL_RE = re.compile(r"pow \( (?:clamp \( |max \( |abs \( |\( )?" + ONE + r" [-+] (?:(?:max \( |abs \( )?dot \(|"
                         r"(?i:\w*(?:fres|facing|ndotv|ndv|vdotn|nv|vn|cosv|costheta)\w*) [,)])")
_FOG_RE = re.compile(r"mix \( (\w+(?: \. \w+)?) , [^;]+ , " + ONE + r" - exp2? \( - ")


def detect_lighting(ctx: Ctx) -> None:
    for fn in ctx.fns:
        text = fn.flat
        m = _DIFFUSE_RE.search(text)
        if m:
            ctx.add("lighting.diffuse", fn.file, fn.line_at(m.start()), 0.6, f"clamped dot({m.group(1)}, {m.group(2)}) in {fn.name}()")
        for m in _SPEC_RE.finditer(text):
            e = ctx.value(m.group(1), fn) if not re.fullmatch(NUM, m.group(1)) else float(m.group(1).rstrip("fF"))
            if e is None or e >= 4:
                ctx.add("lighting.specular", fn.file, fn.line_at(m.start()), 0.8, f"pow(dot(..), {m.group(1)}) in {fn.name}()",
                        exponent=e)
                break
        m = _FRESNEL_RE.search(text)
        if m:
            ctx.add("lighting.fresnel", fn.file, fn.line_at(m.start()), 0.8, f"pow(1 - dot(..), k) in {fn.name}()")
        else:
            # two steps: a variable set to one minus a dot product (clamped or not), then raised to a power or cubed
            m = re.search(r"\b(\w+) = (?:clamp \( |max \( |abs \( )?" + ONE + r" [-+] (?:max \( |abs \( )?dot \(", text)
            if m and re.search(r"pow \( " + m.group(1) + r" ,|\b" + m.group(1) + r" \* " + m.group(1) + r" \* " +
                               m.group(1) + r"\b", text):
                ctx.add("lighting.fresnel", fn.file, fn.line_at(m.start()), 0.75,
                        f"{m.group(1)} = 1 - dot(..), raised to a power, in {fn.name}()")
        m = _FOG_RE.search(text)
        if m:
            ctx.add("lighting.fog", fn.file, fn.line_at(m.start()), 0.75, f"mix({m.group(1)}, fog, 1 - exp(-..)) in {fn.name}()")


# ---------- detectors: hashes, noise, fbm, warping ----------

_HASH_NAME_RE = re.compile(r"^(?:hash|rand|rnd|random|h\d\d|pcg|xxhash|lowbias|wang|murmur)\w*$", re.I)
_NOISE_NAME_RE = re.compile(r"noise|perlin|simplex|worley|cellular|voronoi|^vnoise|^gnoise", re.I)
_QUINTIC_RE = re.compile(r"\* \( \w+ \* \( \w+ \* 6\.?0* - 15\.?0* \) \+ 10\.?0* \)|6\.?0* \* \w+ - 15\.?0*")
_HERMITE_RE = re.compile(r"\* \( 3\.?0* - 2\.?0* \* \w+ \)|3\.?0* \* \w+(?: \* \w+)? - 2\.?0* \* \w+")
_BILERP_RE = re.compile(r"\+ \( (\w+) - (\w+) \) \* \w+")     # a + (b - a)*u: linear interpolation by hand
_SIMPLEX_RE = re.compile(r"0?\.36602\d*|0?\.21132\d*|sqrt \( 3\.?0* \) - " + ONE + r"|\( 3\.?0* - sqrt \( 3\.?0* \) \)")


def detect_hash(ctx: Ctx) -> None:
    for fn in ctx.fns:
        text = fn.flat
        hit = False
        for off, _, inner in call_sites(text, {"fract"}):
            if re.search(r"\bsin \(", inner) and (any(abs(n) >= 100 for n in numbers_in(inner)) or
                                                 any((ctx.value(i, fn) or 0) >= 100 for i in idents_in(inner) - {"sin"})):
                ctx.add("hash.sin_fract", fn.file, fn.line_at(off), 0.95, f"fract(sin(..) * big) in {fn.name}()")
                hit = True
                break
        signature = " ".join([fn.ret or ""] + [p.type for p in fn.params])    # uint ihash(uint x): the type is up here
        if re.search(r"\buint\b|\buvec[234]\b|floatBitsToUint", text + " " + signature) and \
                re.search(r" \^ | >> | << |\^=", text):
            if re.search(r"0x[0-9a-fA-F]{5,}|\b\d{6,}u?\b", text):
                m = re.search(r" \^ | >> | << |\^=", text)
                ctx.add("hash.integer", fn.file, fn.line_at(m.start()), 0.9, f"uint mixing (xor/shift/multiply) in {fn.name}()")
                hit = True
        elif re.search(r"<< 13 \) \^|\^ \( \w+ >> \d+ \)", text) and re.search(r"\b\d{5,}\b", text):
            m = re.search(r"<< 13|\^", text)
            ctx.add("hash.integer", fn.file, fn.line_at(m.start()), 0.85, f"int mixing (xor/shift/multiply) in {fn.name}()")
            hit = True
        m = re.search(r"fract \( [^;]*?\* (?:vec[234] \( )?0?\.1031", text)
        if m is None and "fract (" in text and "dot (" in text:
            m = re.search(r"\b33\.33\b", text)
        if m and not re.search(r"\bsin \(", text):
            ctx.add("hash.fract_dot", fn.file, fn.line_at(m.start()), 0.9, f"sine-free fract/dot hash in {fn.name}()")
            hit = True
        elif not hit and _HASH_NAME_RE.match(fn.name) and fn.kind != "toplevel" and "fract" in {c.name for c in fn.calls} \
                and not re.search(r"\bsin \(|\buint\b|floatBitsTo|\btexture|\btexelFetch", text):
            m = re.search(r"fract \(", text)
            ctx.add("hash.fract_dot", fn.file, fn.line_at(m.start()), 0.7,
                    f"a sine-free fract() hash in {fn.name}()", variant="fract-poly")
            hit = True
        if hit or (_HASH_NAME_RE.match(fn.name) and fn.kind != "toplevel"):
            ctx.hash.add(fn.name)


_CORNER_RE = re.compile(r"[-+] (?:vec[234] \( [^()]*?(?<![\w.])1(?:\.0*)?(?![\w.])|ivec[234] \(|1(?:\.0*)?(?![\w.])|"
                        r"\d{2,3}(?:\.0*)?(?![\w.])|\w+ \. [xyzw]{1,3}\b)")
# four corners fetched at once and interpolated by component: h = hash4(i); mix(mix(h.x, h.y, u.x), ...)
_CORNER_VEC_RE = re.compile(r"mix \( mix \( (\w+) \. [xyzw] , \1 \. [xyzw]")


def _lattice_corners(ctx: Ctx, fn: G.Fn) -> int:
    """How many hash taps in the function take a corner offset of their cell: i + vec2(1,0), n + 57., i + e.xy."""
    n = 0
    for c in fn.calls:
        if c.name in ctx.hash or (c.name == "fract" and "sin" in fn.text(*(c.args[0] if c.args else (0, 0)))):
            for a, b in c.args[:1]:
                if _CORNER_RE.search(fn.text(a, b)):
                    n += 1
    if _CORNER_VEC_RE.search(fn.flat):
        n += 1
    return n


def detect_noise(ctx: Ctx) -> None:
    for fn in ctx.fns:
        if fn.kind == "toplevel" or fn.name in ctx.entries:
            continue
        text = fn.flat
        names = {c.name for c in fn.calls}
        lattice = "floor" in names and ("fract" in names or re.search(r"\b\w+ - \w+ ;|= \w+ - floor", text))
        samples_tex = bool(names & TEXTURE_CALLS)
        samples_hash = bool(names & ctx.hash) or bool(re.search(r"fract \( sin \(", text))
        interp = ("quintic" if _QUINTIC_RE.search(text) else "hermite" if _HERMITE_RE.search(text)
                  else "smoothstep" if "smoothstep" in names else "linear" if "mix" in names or _BILERP_RE.search(text)
                  else None)
        kind = None
        if "floor" in names and _SIMPLEX_RE.search(text) and ("dot" in names):
            kind, conf = "noise.simplex", 0.9
        elif lattice and (samples_hash or samples_tex) and re.search(r"dot \( \w+ \( [^;]*?\) , |dot \( \w+ , \w+ - vec[23] \(",
                                                                    text) and not samples_tex:
            kind, conf = "noise.gradient", 0.85
        elif lattice and samples_tex and interp:
            kind, conf = "noise.texture", 0.85
        elif lattice and samples_hash and interp and _lattice_corners(ctx, fn) >= 1:
            # value noise taps the hash at the cell's corners: hash(i), hash(i + vec2(1,0)), ... -- a per-cell
            # hash(id + 0.1) with a mix is cell colouring, not noise
            kind, conf = "noise.value", 0.85
        elif _NOISE_NAME_RE.search(fn.name) and "floor" in names and interp and fn.kind == "function":
            kind, conf = "noise.value", 0.7       # a lattice with its own inline hash, named as a noise
        elif _NOISE_NAME_RE.search(fn.name) and samples_tex and fn.kind == "function" and \
                re.search(r"\breturn (?:texture|textureLod|texture2D) \(", text):
            kind, conf = "noise.texture", 0.8     # the noise IS a filtered texture read
        if kind:
            m = re.search(r"floor \(", text)
            if kind == "noise.simplex":
                what = f"simplex noise in {fn.name}(): a skewed lattice"
            elif kind == "noise.texture" and not lattice:
                what = f"noise read straight from a filtered texture in {fn.name}()"
            elif kind == "noise.texture":
                what = f"lattice noise in {fn.name}() with its corners read from a texture"
            else:
                what = (f"{'gradient' if kind == 'noise.gradient' else 'value'} noise in {fn.name}(): lattice corners, "
                        f"{interp or 'no'} interpolation")
            ctx.add(kind, fn.file, fn.line_at(m.start()) if m else fn.line, conf, what, interpolation=interp)
            ctx.noise.add(fn.name)
        elif _NOISE_NAME_RE.search(fn.name) and fn.kind == "function" and fn.ret not in ("void",):
            ctx.noise.add(fn.name)
        # the lattice-in-a-texture read: a texel-centred lookup, (cell + half a texel) over the noise image's size
        m = re.search(r"(?:texture|textureLod|texture2D) \( \w+ , [^;]*?\+ 0?\.5 \) / (?:256|64|32|1024)\.?0*", text)
        if m and kind != "noise.texture":
            ctx.add("noise.texture", fn.file, fn.line_at(m.start()), 0.85, f"a lattice read from a noise texture in {fn.name}()")
            ctx.noise.add(fn.name)


def _lacunarity(ctx: Ctx, fn: G.Fn, rhs: str, var: str, op: str) -> Optional[float]:
    """The frequency multiplier in an update of `var`: p *= 2., p = m * p * 2.02, f *= 1.9, p = p * mat2(..)."""
    if op == "*=":
        v = ctx.value(rhs, fn)
        if isinstance(v, (int, float)):
            return float(v)
        return _matrix_scale(ctx, fn, rhs)
    if op != "=" or not re.search(r"\b" + re.escape(var) + r"\b", rhs):
        return None
    nums = [float(n.rstrip("fF")) for n in re.findall(r"(?<![\w.])(" + NUM + r")(?![\w.])", rhs)]
    terms = [t for t in re.split(r" [-+] ", rhs) if re.search(r"\b" + re.escape(var) + r"\b", t)]
    if not terms:
        return None
    term = terms[0]
    factors = [f for f in term.split(" * ") if f.strip() != var]
    scale, known = 1.0, False
    for f in factors:
        v = ctx.value(f, fn)
        if isinstance(v, (int, float)):
            scale *= float(v)
            known = True
            continue
        ms = _matrix_scale(ctx, fn, f)
        if ms:
            scale *= ms
            known = True
    if not known and nums:
        return None
    return scale if known and scale != 1.0 else None


def _matrix_scale(ctx: Ctx, fn: G.Fn, expr: str) -> Optional[float]:
    """sqrt(|det|) of a literal mat2 (an fbm's rotation-and-scale matrix), resolved through consts and #defines."""
    text = expr.strip()
    for _ in range(3):
        if re.fullmatch(ID, text):
            for prog in (fn.prog, ctx.unit.program):
                c = prog.consts.get(text) or prog.globals.get(text) if prog else None
                if c is not None:
                    text = " ".join(t.text for t in c.expr)
                    break
                d = prog.defines.get(text) if prog else None
                if d is not None and d.params is None:
                    text = " ".join(t.text for t in d.body_tokens())
                    break
            else:
                return None
        else:
            break
    m = re.fullmatch(r"\(? ?mat2 \( (.+) \) ?\)?", text)
    if not m:
        return None
    parts = split_args(m.group(1))
    vals = [ctx.value(p, fn) for p in parts]
    if len(vals) != 4 or any(not isinstance(v, (int, float)) for v in vals):
        return None
    det = vals[0] * vals[3] - vals[1] * vals[2]
    return math.sqrt(abs(det)) if det else None


def _noiseish(ctx: Ctx, name: str) -> Optional[str]:
    """What kind of signal a call returns, for the fbm detector: 'noise' (a noise, or a function built on one),
    'texture', 'trig' (sin/cos), or None."""
    if name in ctx.noise or name in ctx.fbm:
        return "noise"
    if name in TEXTURE_CALLS:
        return "texture"
    if name in ("sin", "cos"):
        return "trig"
    for fn in ctx.unit.nodes(name):
        if fn.kind == "function" and fn.ret in ("float", "vec2", "vec3", "vec4"):
            if name in ctx.hash or _NOISE_NAME_RE.search(name):
                return "noise"
            if _reaches(ctx, name, ctx.noise | ctx.hash):
                return "derived"           # built on a noise or hash (a wave octave that calls a noise)
    return None


def _reaches(ctx: Ctx, name: str, targets: Set[str]) -> bool:
    """Does `name` call into `targets` -- without passing through a distance function? A march whose scene uses fbm
    returns a hit distance, not noise; only a function that uses the noise itself is built on it."""
    stack, seen = [name], set()
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n != name and n in targets:
            return True
        if n != name and n in ctx.df:
            continue
        stack.extend(ctx.unit.graph.get(n, ()))
    return False


def _outside_calls(rhs: str) -> str:
    """The expression with every call's arguments removed: `d * amp` stays, `f(p * 2.)` becomes `f()`."""
    out, i = [], 0
    for m in _CALL_RE.finditer(rhs):
        if m.start() < i:
            continue
        out.append(rhs[i:m.end()])
        inner = paren_inner(rhs, m.end() - 1)
        i = m.end() + len(inner) + (2 if inner else 1)
        out.append(")")
    out.append(rhs[i:])
    return "".join(out)


def detect_fbm(ctx: Ctx) -> None:
    for fn in ctx.functions:
        looped = False
        for loop in fn.loops:
            if id(loop) in ctx.march or id(loop) in ctx.loop_labels:
                continue
            stmts = ctx.loop_stmts(fn, loop)
            noisy: Dict[str, Tuple[str, str, str]] = {}      # var -> (source call, its kind, its argument text)
            for s in stmts:
                for a in assigns(s.text):
                    if a.op in ("=", "+=") and a.var not in noisy:
                        for off, name, inner in call_sites(a.rhs, set(calls_in(a.rhs))):
                            kind = _noiseish(ctx, name)
                            if kind:
                                noisy[a.var] = (name, kind, inner)
                                break
            accum = []
            for s in stmts:
                for a in assigns(s.text):
                    if not (a.op == "+=" or (a.op == "=" and re.match(re.escape(a.var) + r" \+ ", a.rhs))):
                        continue
                    outside = _outside_calls(a.rhs)
                    if not re.search(r" \* | / ", outside):
                        continue                    # an octave carries a weight: amp * noise(..), noise(..) / f
                    hit = None
                    for off, name, inner in call_sites(a.rhs, set(calls_in(a.rhs))):
                        kind = _noiseish(ctx, name)
                        if kind:
                            hit = (name, kind, inner, None)
                            break
                    if hit is None:
                        via = next((v for v in noisy if v != a.var and re.search(r"\b" + re.escape(v) + r"\b", outside)),
                                   None)
                        if via:
                            hit = noisy[via] + (via,)
                    if hit:
                        accum.append((s, a, outside) + hit)
            if not accum:
                continue
            s0, a0, outside, src_name, src_kind, arg, via = accum[0]
            arg_ids = idents_in(arg)
            amp_ids = idents_in(outside) - arg_ids - {src_name, a0.var, via}
            gain, lac_by_var = None, {}
            for s in stmts:
                for a in assigns(s.text):
                    if a.var == a0.var or a.var == via:
                        continue
                    if a.var in amp_ids and a.op in ("*=", "/=", "="):
                        v = ctx.value(a.rhs, fn) if a.op != "=" else None
                        if a.op == "=":
                            m = re.fullmatch(re.escape(a.var) + r" \* (" + NUM + r"|\w+)|(" + NUM + r"|\w+) \* " +
                                             re.escape(a.var), a.rhs)
                            v = ctx.value(m.group(1) or m.group(2), fn) if m else None
                        if isinstance(v, (int, float)) and v:
                            g = v if a.op != "/=" else 1 / v
                            if 0 < g < 1:
                                gain = round(float(g), 4)
                    if a.var in arg_ids:
                        L = _lacunarity(ctx, fn, a.rhs, a.var, a.op)
                        if L and L > 1:
                            lac_by_var[a.var] = L
                    if loop.var and a.op == "=":
                        pm = re.fullmatch(r"pow \( (" + NUM + r") , (?:float \( )?" + re.escape(loop.var) + r"(?: \))? \)",
                                          a.rhs)
                        if pm:
                            base = float(pm.group(1).rstrip("fF"))
                            if a.var in arg_ids and base > 1:
                                lac_by_var[a.var] = base
                            elif a.var in amp_ids and 0 < base < 1:
                                gain = base
            # the frequency multiplier per octave: the product over every variable scaled in the noise's argument
            lac = round(math.prod(lac_by_var.values()), 4) if lac_by_var else None
            implicit = re.search(r"/ (\w+)\b", outside)
            if gain is None and lac and implicit and implicit.group(1) in arg_ids:
                gain = round(1 / lac, 4)
            if gain is None and lac is None:
                continue
            octaves, why = ctx.resolved_bound(fn, loop)
            variant = ("ridged" if re.search(ONE + r" - abs \(", a0.rhs) else
                       "turbulence" if re.search(r"abs \( " + re.escape(src_name) + r" \(", a0.rhs) else None)
            conf = (0.95 if gain and lac else 0.85) - (0.15 if src_kind == "trig" else 0) - \
                (0.1 if src_kind == "derived" else 0)
            ctx.add("noise.fbm", fn.file, loop.line, conf,
                    f"{octaves or '?'} octaves of {src_name}() in {fn.name}(): {a0.var} += "
                    + (f"{via} * weight ({via} = {src_name}(..))" if via else f"weight * {src_name}(..)"),
                    octaves=octaves, lacunarity=lac, gain=gain, source=src_name, variant=variant, form="loop",
                    bound_note=why or None)
            if src_kind == "texture":
                ctx.add("noise.texture", fn.file, s0.line, 0.75, f"fbm octaves read from a texture in {fn.name}()")
            ctx.fbm.add(fn.name)
            ctx.loop_labels[id(loop)] = "fbm octaves"
            looped = True
        if not looped:
            _unrolled_fbm(ctx, fn)


def _unrolled_fbm(ctx: Ctx, fn: G.Fn) -> None:
    """Three or more octaves written out: weighted noise samples, each weight smaller than the last, summed into one
    variable, with the point scaled (often through a matrix) between them."""
    series: Dict[Tuple[str, str], List[Tuple[float, int]]] = {}
    lacs: List[float] = []
    for st in fn.statements(exclude=[lp.full for lp in fn.loops]):
        for a in assigns(st.text):
            m = re.fullmatch(r"(" + NUM + r") \* (.+)|(.+) \* (" + NUM + r")", a.rhs)
            if m and a.op in ("=", "+="):
                w = float((m.group(1) or m.group(4)).rstrip("fF"))
                body = m.group(2) or m.group(3)
                name = next((c for c in calls_in(body) if _noiseish(ctx, c) in ("noise", "texture", "derived")), None)
                if name:
                    series.setdefault((a.var, name), []).append((w, st.line))
                    continue
            L = _lacunarity(ctx, fn, a.rhs, a.var, a.op)
            if L and L > 1:
                lacs.append(L)
    for (var, name), ws in series.items():
        weights = [w for w, _ in ws]
        if len(weights) >= 3 and all(b < a for a, b in zip(weights, weights[1:])):
            ratios = sorted(b / a for a, b in zip(weights, weights[1:]))
            gain = round(ratios[len(ratios) // 2], 4)
            lac = round(sorted(lacs)[len(lacs) // 2], 4) if lacs else None
            ctx.add("noise.fbm", fn.file, ws[0][1], 0.85,
                    f"{len(weights)} octaves of {name}() written out in {fn.name}(): {var} += w * {name}(..)",
                    octaves=len(weights), gain=gain, lacunarity=lac, source=name, form="unrolled")
            ctx.fbm.add(fn.name)
            return


def _only_calls_to(expr: str, names: Set[str]) -> bool:
    """Is the expression nothing but calls to `names`, constants and constructors? (vec2(fbm(p), fbm(p + 5.2)),
    0.5 + 0.5*noise(p)) -- a wrapper of a noise, not something that merely mixes one in."""
    found = False
    rest, i = [], 0
    for m in _CALL_RE.finditer(expr):
        if m.start() < i:
            continue
        if m.group(1) in names:
            found = True
            rest.append(expr[i:m.start()])
            inner = paren_inner(expr, m.end() - 1)
            i = m.end() + len(inner) + (2 if inner else 1)
    rest.append(expr[i:])
    left = idents_in(" ".join(rest)) - {"vec2", "vec3", "vec4", "float", "abs"}
    return found and not left


def detect_domain_warp(ctx: Ctx) -> None:
    base = ctx.noise | ctx.fbm
    if not base:
        return
    # Thin wrappers are noise too: a function returning two fbm samples (at offset points) packed in a vec2. Only one whose
    # RETURN expression calls the noise counts -- calcNormal() or render() reach a noise but return something else.
    family = set(base)
    for _ in range(2):
        for fn in ctx.functions:
            if fn.name in family or fn.name in ctx.entries or fn.ret not in ("float", "vec2", "vec3", "vec4"):
                continue
            rets = [st.text[7:] for st in fn.statements() if st.text.startswith("return ")]
            if len(rets) == 1 and _only_calls_to(rets[0], family):
                family.add(fn.name)
    alt = "|".join(sorted(re.escape(n) for n in family))
    fam_call = re.compile(r"(?<!\. )\b(?:" + alt + r") \(")
    for fn in ctx.functions:
        text = fn.flat
        done = False
        for off, name, inner in call_sites(text, family):
            if fam_call.search(inner):
                ctx.add("noise.domain_warp", fn.file, fn.line_at(off), 0.9,
                        f"{name}() sampled at a point displaced by noise in {fn.name}()", form="nested")
                done = True
                break
        if done:
            continue
        # chained: q = vec2(fbm(p), fbm(p + k)); ... fbm(p + 4.*q). Only a DIRECT noise result taints a variable,
        # and the later sample must take it as a displacement (a + or - term), not merely depend on it somehow.
        tainted: Set[str] = set()       # holds a noise result directly
        hopped: Set[str] = set()        # one arithmetic step from one: p = q + 2.0*n
        for st in fn.statements():
            for a in assigns(st.text):
                sites = list(call_sites(a.rhs, family))
                for _, name, inner in sites:
                    if idents_in(inner) & (tainted | hopped):
                        ctx.add("noise.domain_warp", fn.file, st.line, 0.8,
                                f"{name}() sampled at a point displaced by noise in {fn.name}()", form="chained")
                        done = True
                        break
                    if a.var in idents_in(inner) and a.op in ("+=", "-=") and fn.name not in ctx.fbm and not a.member:
                        ctx.add("noise.domain_warp", fn.file, st.line, 0.75,
                                f"the coordinate displaced by noise ({a.var} {a.op} {name}({a.var}..)) in {fn.name}()",
                                form="self")
                        done = True
                        break
                if done:
                    break
                if a.op != "=" or a.member:
                    continue
                tainted.discard(a.var)
                hopped.discard(a.var)
                if sites:
                    tainted.add(a.var)
                elif idents_in(a.rhs) & tainted and set(calls_in(a.rhs)) <= {"vec2", "vec3", "vec4", "float"}:
                    hopped.add(a.var)
            if done:
                break


# ---------- detectors: folds and fractals ----------

def detect_folds(ctx: Ctx) -> None:
    for fn in ctx.functions:
        text = fn.flat
        atans = [c for c in fn.calls if c.name == "atan" and len(c.args) == 2]
        if atans:
            angle_vars = set()
            for st in fn.statements():
                for a in assigns(st.text):
                    if "atan (" in a.rhs:
                        angle_vars.add(a.var)
            kal = None
            for v in angle_vars:
                kal = re.search(r"mod \( " + v + r"\b|\b" + v + r" = abs \( " + v + r"\b|(?:floor|round) \( " + v +
                                r" / |\b" + v + r" -= [^;]*(?:floor|round) \(", text)
                if kal:
                    break
            kal = kal or re.search(r"mod \( atan \(", text)
            if kal:
                ctx.add("domain.kaleidoscope", fn.file, fn.line_at(kal.start()), 0.85,
                        f"the atan angle folded into sectors in {fn.name}()")
            else:
                ctx.add("domain.polar", fn.file, atans[0].line, 0.75 if "length (" in text else 0.6,
                        f"atan(y, x) in {fn.name}()")
        elif re.match(r"^pModPolar\w*$", fn.name):
            ctx.add("domain.kaleidoscope", fn.file, fn.line, 0.7, f"named {fn.name}()")
        for loop in fn.loops:
            if id(loop) in ctx.march or id(loop) in ctx.loop_labels:
                continue                   # a march, an AO/normal/fbm loop: not an iteration of a fold
            _fractal_loop(ctx, fn, loop)


def _fold_statements(ctx: Ctx, fn: G.Fn, loop: G.Loop) -> List[Tuple[G.Fn, G.Stmt]]:
    """The loop's own statements, plus those of loop-free functions it calls -- a fractal written as `p = foldStep(p)` keeps the
    whole fold in a helper, and the loop is only the iteration."""
    out = [(fn, s) for s in ctx.loop_stmts(fn, loop)]
    seen = {fn.name}
    for _, s in list(out):
        for a in assigns(s.text):
            # only p = foldStep(p): the helper IS the iteration step; a scene function called in a loop is not
            m = re.match(r"(" + ID + r") \( (.*) \)$", a.rhs)
            if a.op != "=" or not m or m.group(1) in seen or m.group(1) not in ctx.user or \
                    not re.search(r"\b" + re.escape(a.var) + r"\b", m.group(2)):
                continue
            seen.add(m.group(1))
            for cf in ctx.unit.nodes(m.group(1)):
                if cf.kind == "function" and not cf.loops:
                    out.extend((cf, x) for x in cf.statements())
    return out


_DOT_SELF_RE = re.compile(r"^dot \( (\w+)(?: \. \w+)? , \1(?: \. \w+)? \)$")


def _inversion(rows: List[Tuple[G.Fn, Assign, G.Stmt]]) -> Optional[G.Stmt]:
    """A sphere inversion p *= k / |p|^2, written directly or through r2 = dot(p,p); k = s/r2; p *= k."""
    dot_of: Dict[str, str] = {}
    for _, a, _ in rows:
        m = _DOT_SELF_RE.match(a.rhs)
        if a.op == "=" and m:
            dot_of[a.var] = m.group(1)

    def divides(rhs: str) -> Optional[str]:
        m = re.search(r"/ (?:(?:max|min|clamp) \( )?dot \( (\w+)(?: \. \w+)? , \1\b", rhs)
        if m:
            return m.group(1)
        for r2, p in dot_of.items():
            if re.search(r"/ (?:(?:max|min|clamp) \( )?" + re.escape(r2) + r"\b", rhs):
                return p
        return None

    via = {a.var: divides(a.rhs) for _, a, _ in rows if a.op == "=" and divides(a.rhs)}
    for _, a, s in rows:
        if a.op in ("*=", "=") and divides(a.rhs) == a.var and (a.op == "*=" or re.search(r"\b" + a.var + r"\b", a.rhs)):
            return s
        if a.op in ("*=", "=") and any(p == a.var and k != a.var and re.search(r"\b" + re.escape(k) + r"\b", a.rhs)
                                       for k, p in via.items()):
            if a.op == "*=" or re.search(r"\b" + re.escape(a.var) + r"\b", a.rhs):
                return s
        if a.op == "/=" and (dot_of.get(a.rhs) == a.var or _DOT_SELF_RE.match(a.rhs)):
            return s
    return None


_BOX_FOLD_RE = re.compile(r"clamp \( (\w+(?: \. \w+)?) , - ?[\w.]+ , [\w.]+ \) \* 2\.?0* - \1\b|"
                          r"abs \( (\w+(?: \. \w+)?) \+ [\w.]+ \) - abs \( \2 - [\w.]+ \) - \2\b")
_ESCAPE_RE = re.compile(r"vec2 \( (\w+) \. x \* \1 \. x - \1 \. y \* \1 \. y , 2\.?0* \* \1 \. x \* \1 \. y \)|"
                        r"mat2 \( (\w+) , - \2 \. y , \2 \. x \) \* \2\b|"
                        r"\b(?:cmul|cmult|cMul|cx_mul|cpow) \( (\w+) , \3 \)|\b(?:csqr|cx_sqr|csq) \(")


def _fractal_loop(ctx: Ctx, fn: G.Fn, loop: G.Loop) -> None:
    rows = [(f, a, s) for f, s in _fold_statements(ctx, fn, loop) for a in assigns(s.text)]
    ltext = " ; ".join(s.text for _, s in _fold_statements(ctx, fn, loop))
    iters, _ = ctx.resolved_bound(fn, loop)
    if iters is not None and iters < 2:
        return
    tagged = False
    m = _BOX_FOLD_RE.search(ltext)
    inv = _inversion(rows)
    if m:
        ctx.add("fractal.mandelbox", fn.file, loop.line, 0.9,
                f"box fold clamp(p,-1,1)*2-p{' and a sphere fold' if inv else ''} iterated in {fn.name}()",
                iterations=iters)
        tagged = True
    elif inv:
        f = next((f for f, _, s in rows if s is inv), fn)
        kali = bool(re.search(r"abs \( (\w+) \) / dot \( \1 , \1 \)", inv.text))
        ctx.add("fractal.inversion", f.file, inv.line, 0.85,
                ("abs(p) over its squared length, minus c (the Kali set)" if kali else
                 "sphere inversion: p scaled by k over its squared length") +
                f" iterated in {fn.name}()", iterations=iters, variant="kaliset" if kali else None)
        tagged = True
    m = _ESCAPE_RE.search(ltext)
    if m:
        bail = bool(re.search(r"dot \( (\w+) , \1 \) > |length \( \w+ \) > ", ltext))
        ctx.add("fractal.escape_time", fn.file, loop.line, 0.9 + (0.05 if bail else 0),
                f"z = z^2 + c iterated in {fn.name}()", iterations=iters)
        tagged = True
    if re.search(r"pow \( \w+ , [\w.]+ \)", ltext) and re.search(r"\ba(?:cos|sin) \(", ltext) and "atan (" in ltext:
        ctx.add("fractal.mandelbulb", fn.file, loop.line, 0.85, f"power formula in spherical coords in {fn.name}()",
                iterations=iters)
        tagged = True
    if not m and not tagged or not _BOX_FOLD_RE.search(ltext):
        _kifs(ctx, fn, loop, rows, iters)
    if tagged:
        ctx.loop_labels.setdefault(id(loop), "fractal iterations")


def _kifs(ctx: Ctx, fn: G.Fn, loop: G.Loop, rows, iters) -> None:
    """A kaleidoscopic IFS: an abs() fold (or a plane reflection) of a point, plus a scale, rotation or offset of it."""
    fold = plane = None
    scale = None
    moves = set()
    folded: Set[str] = set()
    for f, a, s in rows:
        if a.op in ("=", "-=", "+=") and re.search(r"\babs \( " + re.escape(a.var) + r"\b", a.rhs):
            fold = fold or (f, s)
            folded.add(a.var)
        if a.op == "-=" and re.search(r"2\.?0* \* min \( " + ZERO + r" , dot \( " + re.escape(a.var) + r" , (\w+) \) \) \* \w+",
                                      a.rhs):
            plane = plane or (f, s)
            folded.add(a.var)
    if not (fold or plane):
        return
    # the folded point must carry from one iteration to the next: a plain reset (p = q - c) inside the loop
    # means each pass folds a fresh point -- mirror symmetry in a loop over objects, not an IFS
    for f, a, s in rows:
        if f is fn and a.var in folded and a.op == "=" and not a.member and \
                not re.search(r"\b" + re.escape(a.var) + r"\b", a.rhs):
            return
    for f, a, s in rows:
        if a.var not in folded:
            continue
        if a.op == "*=":
            v = ctx.value(a.rhs, f)
            if isinstance(v, (int, float)) and v not in (0, 1):
                scale = scale or v
            elif re.fullmatch(ID, a.rhs) and not re.search(r"rot|mat|^m\d?$|^r$", a.rhs, re.I):
                scale = scale or a.rhs
            else:
                moves.add("rotation")
        elif a.op in ("-=", "+=") and not re.search(r"\babs \(|min \(", a.rhs):
            moves.add("offset")
        elif a.op == "=":
            mm = re.match(r"(?:(" + NUM + r"|\w+) \* )?" + re.escape(a.var) + r"(?: \* (" + NUM + r"|\w+))? [-+] ", a.rhs)
            if mm and (mm.group(1) or mm.group(2)):
                k = mm.group(1) or mm.group(2)
                v = ctx.value(k, f)
                scale = scale or (v if isinstance(v, (int, float)) else k)
            elif re.match(r"(?:rot\w*|rotate\w*|r2d|mat2) \( ", a.rhs) or re.search(r"\* (?:rot\w*|mat2) \(", a.rhs):
                moves.add("rotation")
    if not (scale or moves):
        return
    f, s = fold or plane
    conf = 0.85 if scale else 0.7
    what = "plane reflections" if plane and not fold else "abs() folds"
    extra = " and a scale" if scale else "".join(" and " + ("an " if m[0] in "aeiou" else "a ") + m
                                                   for m in sorted(moves))
    ctx.add("fractal.kifs", f.file, s.line, conf, f"{what}{extra} iterated in {fn.name}()",
            iterations=iters, scale=scale if isinstance(scale, (int, float)) else None)
    ctx.loop_labels.setdefault(id(loop), "fold iterations")


# ---------- detectors: cellular ----------

def detect_voronoi(ctx: Ctx) -> None:
    for fn in ctx.functions:
        for loop in fn.loops:
            kids = [c for c in fn.loops if c.parent is loop]
            for kid in kids:
                if not _neighbour_range(loop) or not _neighbour_range(kid):
                    continue
                inner = [s.text for c in fn.loops if c is kid or _inside(c, kid) for s in ctx.loop_stmts(fn, c)]
                text = " ; ".join(inner)
                dist = re.search(r"length \(|dot \( (\w+) , \1 \)|distance \(", text)
                pick = re.search(r"min \(|if \( \w+ < \w+", text)
                cell = re.search(r"\b(?:" + "|".join(re.escape(v) for v in (loop.var, kid.var) if v) + r")\b", text) \
                    if (loop.var or kid.var) else None
                feature = any(n in ctx.user or n in TEXTURE_CALLS for n in calls_in(text))
                if dist and pick and cell and feature:
                    d3 = any(_neighbour_range(g) for g in fn.loops if g.parent is kid)
                    f2 = len(set(re.findall(r"(\w+(?: \. \w)?) = min \( \1 ,", text))) >= 2 or \
                        bool(re.search(r"\b(\w+) = (\w+) ; \2 = ", text)) or bool(re.search(r"\. y = \w+ \. x", text))
                    smooth = bool(re.search(r"\+= exp2? \( -|exp2? \( - [^;]*\* \w+ \)", text))
                    cells = (_span(loop) or 3) * (_span(kid) or 3) * (3 if d3 else 1)
                    ctx.add("cellular.voronoi", fn.file, loop.line, 0.9,
                            f"a {'3x3x3' if d3 else '%dx%d' % (_span(loop) or 3, _span(kid) or 3)} neighbour search in {fn.name}()",
                            cells=cells, dims=3 if d3 else 2, f2=f2 or None, smooth=smooth or None)
                    ctx.loop_labels[id(loop)] = "voronoi cells"
                    break
            else:
                n, _ = ctx.resolved_bound(fn, loop)
                if n in (9, 25, 27) and re.search(r"% [35] (?:\) )?- [12]\b|/ [35] (?:\) )?- [12]\b",
                                                   fn.text(loop.keyword, loop.end)):
                    ctx.add("cellular.voronoi", fn.file, loop.line, 0.85, f"a {n}-cell flattened neighbour loop in {fn.name}()",
                            cells=n)
                    ctx.loop_labels[id(loop)] = "voronoi cells"


def _neighbour_range(lo: G.Loop) -> bool:
    return lo.bound is not None and 2 <= lo.bound <= 7 and isinstance(lo.start, (int, float)) and lo.start < 0


def _span(lo: G.Loop) -> Optional[int]:
    return lo.bound


def _inside(a: G.Loop, b: G.Loop) -> bool:
    p = a.parent
    while p is not None:
        if p is b:
            return True
        p = p.parent
    return False


# ---------- detectors: colour ----------

_GAMMA_RE = re.compile(r"pow \( [^;]*?, (?:vec[34] \( )?(" + ONE + r" / (?:2\.2\d*|2\.4|\w+)|0?\.45\d*|0?\.41666\d*)"
                       r"(?: \))? \)")
_HSV_RE = re.compile(r"mod \( [^;]*?\+ vec3 \( 0\.?0* , 4\.?0* , 2\.?0* \) , 6\.?0* \) - 3\.?0*|"
                     r"\+ vec[34] \( " + ONE + r" , 2\.?0* / 3\.?0* , " + ONE + r" / 3\.?0*")
_DECODE_RE = re.compile(r"pow \( [^;]*?, (?:vec[34] \( )?2\.2\d*(?: \))? \)")
_TEMPLATE_RE = re.compile(r"cos \( iTime \+ \w+ \. xyx \+ vec3 \( 0\.?0* , 2\.?0* , 4\.?0* \) \)")
_PHASE_RE = re.compile(r"(?:cos|sin) \( [^;]*?\+ vec[34] \( " + ZERO + r" , (" + NUM + r") , (" + NUM + r")")


def detect_palette(ctx: Ctx) -> None:
    for fn in ctx.fns:
        text = fn.flat
        m = _TEMPLATE_RE.search(text)
        if m:
            ctx.add("color.cosine_palette", fn.file, fn.line_at(m.start()), 0.95,
                    f"0.5 + 0.5*cos(iTime + uv.xyx + vec3(0,2,4)) -- the new-shader template, in {fn.name}()",
                    variant="template")
            continue
        found = False
        for mm in re.finditer(r"\* cos \( ", text):
            inner = paren_inner(text, mm.end() - 2)
            head = re.match(r"(.+?) \* \( ", inner)
            if not head:
                continue
            k = ctx.value(head.group(1), fn)
            stmt_start = max(text.rfind(";", 0, mm.start()), text.rfind("{", 0, mm.start()), text.rfind("return", 0, mm.start()))
            if isinstance(k, (int, float)) and abs(k - TWO_PI) < 0.01 and " + " in text[stmt_start:mm.start()]:
                ctx.add("color.cosine_palette", fn.file, fn.line_at(mm.start()), 0.95,
                        f"a + b*cos(2pi*(c*t + d)) in {fn.name}()", variant="iq")
                found = True
                break
        if found:
            continue
        m = _PHASE_RE.search(text)
        if m and re.search(r"0?\.5 \+ 0?\.5 \* (?:cos|sin) \(|\* (?:cos|sin) \(", text[max(0, m.start() - 30):m.end()]):
            ctx.add("color.cosine_palette", fn.file, fn.line_at(m.start()), 0.85,
                    f"a cosine with per-channel phase offsets (0, {m.group(1)}, {m.group(2)}) in {fn.name}()",
                    variant="phase")


def _color_statements(ctx: Ctx, fn: G.Fn) -> List[Tuple[G.Stmt, str, str]]:
    """(statement, assigned var, expression) for statements that write a colour: a vec3/vec4 variable or a return
    from a function returning vec3/vec4."""
    vec = _vec_vars(fn)
    out = []
    for st in fn.statements():
        if st.text.startswith("return ") and (fn.ret or "") in ("vec3", "vec4"):
            out.append((st, "return", st.text[7:]))
            continue
        for a in assigns(st.text):
            if a.var in vec:
                out.append((st, a.var, a.rhs))
                break
    return out


def detect_color_pipeline(ctx: Ctx) -> None:
    for fn in ctx.fns:
        text = fn.flat
        if re.search(r"\b2\.51\b", text) and re.search(r"\b2\.43\b", text) and re.search(r"0?\.59\b|0?\.14\b", text):
            m = re.search(r"\b2\.51\b", text)
            ctx.add("tonemap.aces", fn.file, fn.line_at(m.start()), 0.95, f"the ACES fit constants in {fn.name}()",
                    variant="narkowicz")
        elif re.search(r"0?\.59719\b", text) and re.search(r"0?\.35458\b|1\.60475\b", text):
            m = re.search(r"0?\.59719\b", text)
            ctx.add("tonemap.aces", fn.file, fn.line_at(m.start()), 0.95, f"the fitted ACES matrices in {fn.name}()",
                    variant="fitted")
        m = re.search(r"6\.2 \* \w+ \+ 0?\.5", text)
        if m and re.search(r"\b1\.7\b", text):
            ctx.add("tonemap.filmic", fn.file, fn.line_at(m.start()), 0.9, f"Hejl-Dawson 6.2/1.7 curve in {fn.name}()",
                    variant="hejl-dawson")
        elif all(re.search(r"(?<![\d.])" + k + r"\b", text) for k in (r"0?\.15", r"0?\.02", r"0?\.30?")) and \
                re.search(r"0?\.50?\b", text) and fn.ret in ("vec3", "float") and " / " in text and \
                re.search(r"tone|filmic|uncharted|hable", fn.name, re.I):
            ctx.add("tonemap.filmic", fn.file, fn.line, 0.8, f"the Uncharted 2 constants in {fn.name}()",
                    variant="uncharted2")
        m = re.search(r"\b1\.055\b", text)
        if m and re.search(r"0?\.0031308|12\.92", text):
            ctx.add("color.srgb", fn.file, fn.line_at(m.start()), 0.9, f"the exact sRGB curve in {fn.name}()")
        m = re.search(r"16\.?0* \* \w+ \. x \* \w+ \. y \* \( " + ONE + r" - \w+ \. x \) \* \( " + ONE + r" - \w+ \. y \)", text)
        if m:
            ctx.add("color.vignette", fn.file, fn.line_at(m.start()), 0.9, f"16uv(1-u)(1-v) vignette in {fn.name}()")
        m = _HSV_RE.search(text)
        if m:
            ctx.add("color.hsv", fn.file, fn.line_at(m.start()), 0.9, f"hsv-to-rgb in {fn.name}()")
        m = _DECODE_RE.search(text)
        if m:
            ctx.add("color.gamma_decode", fn.file, fn.line_at(m.start()), 0.8, f"pow(c, 2.2) in {fn.name}()")
        done = set()
        for st, var, rhs in _color_statements(ctx, fn):
            V = re.escape(var) if var != "return" else ID
            if "reinhard" not in done:
                m = re.search(r"\b(" + ID + r"(?: \. " + ID + r")?) / \( (?:" + ONE + r" \+ \1|\1 \+ " + ONE + r"|vec[34] \( "
                              + ONE + r" \) \+ \1|\1 \+ vec[34] \( " + ONE + r" \))\b", rhs) or \
                    re.search(r"/ \( " + ONE + r" \+ dot \(", rhs)
                if m:
                    ctx.add("tonemap.reinhard", fn.file, st.line, 0.9, f"x / (1 + x) on a colour in {fn.name}()")
                    done.add("reinhard")
            if "tanh" not in done and (rhs.startswith("tanh (") or re.search(r"tanh \( " + V + r"\b", rhs)):
                ctx.add("tonemap.tanh", fn.file, st.line, 0.85, f"tanh() on a colour in {fn.name}()")
                done.add("tanh")
            if "exposure" not in done and re.match(r"(?:vec[34] \( " + ONE + r" \) |" + ONE + r" )- exp2? \( - ", rhs):
                ctx.add("tonemap.exposure", fn.file, st.line, 0.8, f"1 - exp(-c) on a colour in {fn.name}()")
                done.add("exposure")
            if "gamma" not in done:
                m = _GAMMA_RE.search(rhs)
                if m:
                    g = m.group(1)
                    ok = True
                    gm = re.fullmatch(ONE + r" / (\w+)", g)
                    if gm and not re.fullmatch(r"2\.2\d*|2\.4", gm.group(1)):
                        v = ctx.value(gm.group(1), fn)
                        ok = isinstance(v, (int, float)) and 1.8 <= v <= 2.6
                    if ok:
                        ctx.add("color.gamma", fn.file, st.line, 0.95, f"pow(c, {g}) in {fn.name}()", form="pow")
                        done.add("gamma")
                elif var != "return" and re.match(r"sqrt \( " + V + r"\b", rhs):
                    ctx.add("color.gamma", fn.file, st.line, 0.65, f"{var} = sqrt({var}) in {fn.name}()", form="sqrt")
                    done.add("gamma")
            added = var != "return" and re.search(r"[-+]= " + re.escape(var) + r"\b|^", st.text) and \
                (re.match(re.escape(var) + r"(?: \. \w+)? (?:\+=|-=) ", st.text) or re.match(re.escape(var) + r" [-+] ", rhs))
            noisy = set(calls_in(rhs)) & (ctx.hash | ctx.noise | TEXTURE_CALLS | {"fract"})
            if "dither" not in done and added and noisy and \
                    re.search(r"/ 255\.?0*\b|\* 0?\.0039\d*|" + ONE + r" / 255\.?0*", rhs):
                ctx.add("color.dither", fn.file, st.line, 0.85, f"noise / 255 added to a colour in {fn.name}()")
                done.add("dither")
        if "dither" not in done and re.search(r"dither", fn.name, re.I) and fn.kind == "function":
            ctx.add("color.dither", fn.file, fn.line, 0.7, f"named {fn.name}()")


# ---------- detectors: glow and volumes ----------

def detect_glow_and_volume(ctx: Ctx) -> None:
    # functions that return an extinction factor exp(-x): a Beer-Lambert helper, transmittance(), ...
    extinction = {fn.name for fn in ctx.functions if re.search(r"\breturn exp2? \( - ", fn.flat)}
    for fn in ctx.functions:
        for loop in fn.loops:
            stmts = ctx.loop_stmts(fn, loop)
            info = ctx.march.get(id(loop))
            dist = set(info["dvars"]) if info else set()
            adv = info["adv"] if info else None
            for s in stmts:
                for a in assigns(s.text):
                    if a.op == "=" and (re.search(r"\b(?:length|distance|abs) \(", a.rhs) or
                                        any(ctx.is_df_candidate(c) for c in calls_in(a.rhs))):
                        dist.add(a.var)
            glow = vol_t = vol_f = None
            for s in stmts:
                for a in assigns(s.text):
                    if a.var == adv or a.var in dist:
                        continue
                    if glow is None and (a.op == "+=" or (a.op == "=" and re.match(re.escape(a.var) + r" \+ ", a.rhs))):
                        hit = None
                        if dist:
                            dalt = "|".join(re.escape(d) for d in dist)
                            hit = re.search(r"/ (?:abs \( )?(?:" + dalt + r")\b|/ \( [^()]*\b(?:" + dalt + r")\b", a.rhs) or \
                                re.search(r"exp2? \( - [^;]*\b(?:" + dalt + r")\b", a.rhs)
                        if hit is None and not info:
                            hit = re.search(r"/ (?:abs|length) \(", a.rhs)
                        if hit:
                            glow = (s, a, hit.group().startswith("exp"))
                    if vol_t is None and ((a.op == "*=" and re.match(r"exp2? \( - ", a.rhs)) or
                                          (a.op == "=" and re.match(re.escape(a.var) + r" \* exp2? \( - ", a.rhs)) or
                                          (a.op == "*=" and re.match(r"(\w+) \(", a.rhs) and
                                           re.match(r"(\w+) \(", a.rhs).group(1) in extinction)):
                        vol_t = (s, a)
                    if vol_f is None and (a.op == "+=" or re.match(re.escape(a.var) + r" \+ ", a.rhs)) and \
                            re.search(r"\( " + ONE + r" - \w+ \. (?:a|w) \)", a.rhs):
                        vol_f = (s, a)
            steps, _ = ctx.resolved_bound(fn, loop)
            if (vol_t or vol_f) and info and info.get("role") == "march":
                # it composites a volume: the step is driven by density, not bounded by a distance
                ctx.evidence = [e for e in ctx.evidence
                                if not (e.tag == "raymarch.sphere_trace" and e.file == fn.file and e.line == loop.line)]
                info["role"] = "volume"
                ctx.loop_labels[id(loop)] = "volume march"
                ctx.add("raymarch.fixed_step", fn.file, loop.line, 0.8,
                        f"a volume march in {fn.name}(): {info['adv']} steps by a density-driven amount", steps=steps,
                        advance=info["adv"], form="volume")
            if glow:
                s, a, is_exp = glow
                tag = "glow.march" if info and info.get("role") != "fixed" else "glow.accumulate"
                conf = (0.85 if tag == "glow.march" else 0.75) - (0.1 if is_exp else 0)
                ctx.add(tag, fn.file, s.line, conf, f"{a.var} += .. / distance in a loop in {fn.name}()", steps=steps)
            if vol_t and not (info or re.search(r"^t$|trans|shadow|vis|absorb|atten|^tr", vol_t[1].var, re.I)):
                vol_t = None               # exp(-x) decay in a loop that walks no ray: an envelope, a falloff
            if vol_t:
                s, a = vol_t
                ctx.add("volume.transmittance", fn.file, s.line, 0.85, f"{a.var} {a.op} exp(-..) in a loop in {fn.name}()",
                        steps=steps)
                ctx.loop_labels.setdefault(id(loop), "volume steps")
            if vol_f:
                s, a = vol_f
                ctx.add("volume.front_to_back", fn.file, s.line, 0.9, f"{a.var} += c * (1 - {a.var}.a) in {fn.name}()",
                        steps=steps)
                ctx.loop_labels.setdefault(id(loop), "volume steps")


# ---------- detectors: inputs, time, camera, anti-aliasing ----------

def _channel_aliases(prog: G.Program, ch: int) -> Set[str]:
    """iChannel<ch> and every object-like #define that only renames it, followed through renamings of renamings
    (`#define KEYS Pressed` beside `#define Pressed iChannel2`): each of those #defines names the channel and reads
    nothing; the read is where a name is used."""
    names = {f"iChannel{ch}"}
    while True:
        rx = re.compile(r"\(?\s*(?:" + "|".join(map(re.escape, sorted(names))) + r")\s*\)?")
        more = {name for name, d in prog.defines.items()
                if d.params is None and name not in names and rx.fullmatch(d.body or "")}
        if not more:
            return names
        names |= more


def _live_tokens(ctx: Ctx) -> Iterator[Tuple[G.Fn, G.Token]]:
    """Every token in the body of a live function or macro, except one naming the body's own parameter: a macro's
    parameter is the argument it is called with and a function's shadows a uniform of that name (glsl.Fn.param_names),
    so `#define WAVE(iTime) sin(iTime)` and `float f(float iTime)` read no clock."""
    for fn in ctx.fns:
        own = fn.param_names
        for t in fn.toks[fn.start:fn.end]:
            if t.text not in own:
                yield fn, t


def detect_inputs(ctx: Ctx) -> None:
    pv = ctx.pv
    uses: Dict[str, List[Tuple[G.Fn, int]]] = {}
    idents = [(fn, t) for fn, t in _live_tokens(ctx) if t.kind == G.IDENT]
    for fn, t in idents:
        uses.setdefault(t.text, []).append((fn, t.line))
    for inp in pv.inputs:
        ch, typ = inp.get("channel"), inp.get("type")
        if ch is None:
            continue
        names = sorted(_channel_aliases(pv.prog, ch))
        # The reads in the order the live code is walked (functions by name, tokens in place), never name by name: the
        # names are a set, and taking them in set order made the line cited hang on the hash seed. The body of the
        # #define that only renames the channel (`#define keyTex iChannel3`) names it and reads nothing: the read is
        # where keyTex is used.
        hits = [(fn, t.line) for fn, t in idents
                if t.text in names and not (fn.kind == "macro" and fn.name in names)]
        if typ in AUDIO_TYPES:
            reads = set()
            for fn in ctx.fns:
                for m in re.finditer(r"(?:texture|textureLod|texture2D) \( (?:" + "|".join(names) + r") , vec2 \( [^,]+ , (" +
                                     NUM + r") \)", fn.flat):
                    reads.add("spectrum" if float(m.group(1).rstrip("fF")) < 0.5 else "waveform")
                for m in re.finditer(r"texelFetch \( (?:" + "|".join(names) + r") , ivec2 \( [^,]+ , (\d) \)", fn.flat):
                    reads.add("spectrum" if m.group(1) == "0" else "waveform")
            line = hits[0][1] if hits else 1
            # bound but never read is reported below the floor: the shader does not USE audio. In a pass with no entry
            # point found, no code was followed, so "never read" would be a negative over a search that never ran.
            unread = (", bound; no entry point found, so no code was searched for a read" if not ctx.entries
                      else ", bound but never read")
            ctx.add("audio.input", hits[0][0].file if hits else pv.file, line, 0.95 if hits else 0.4,
                    f"{typ} on iChannel{ch}" + (f", read {len(hits)} time(s)" if hits else unread),
                    channel=ch, type=typ, reads=sorted(reads) or None)
        elif typ == "keyboard" and hits:
            ctx.add("input.keyboard", hits[0][0].file, hits[0][1], 0.95, f"keyboard on iChannel{ch}", channel=ch)
    if uses.get("iMouse"):
        fn, line = uses["iMouse"][0]
        ctx.add("input.mouse", fn.file, line, 0.95, f"iMouse read {len(uses['iMouse'])} time(s)")
    time_hits = [h for n in TIME_UNIFORMS for h in uses.get(n, [])]
    if time_hits:
        fn, line = min(time_hits, key=lambda h: (h[0].file, h[1]))
        ctx.add("animation.time", fn.file, line, 0.99, f"iTime/iDate read {len(time_hits)} time(s)", uses=len(time_hits))
    frames = 0
    first = None
    for fn in ctx.fns:
        if "iFrame" in fn.param_names:
            continue                       # every iFrame in this body is its own parameter (_live_tokens)
        for m in re.finditer(r"\biFrame\b", fn.flat):
            around = fn.flat[max(0, m.start() - 12):m.end() + 8]
            if re.search(r"min \( (?:iFrame|0\.?0*) , (?:0\.?0*|iFrame)|max \( 0\.?0* , - iFrame|iFrame (?:==|<|<=) [0-9]",
                         around) or re.search(r"float \( iFrame \) \)|- iFrame \)", around) and "min (" in around:
                continue
            frames += 1
            first = first or (fn, fn.line_at(m.start()))
    if frames:
        ctx.add("animation.frame", first[0].file, first[1], 0.8, f"iFrame read {frames} time(s) beyond the idioms",
                uses=frames)


def detect_camera_and_aa(ctx: Ctx) -> None:
    for fn in ctx.fns:
        text = fn.flat
        m = re.search(r"cross \( [^;]*?vec3 \( " + ZERO + r" , " + ONE + r" , " + ZERO + r" \)|cross \( \w+ , vec3 \( sin \( ",
                      text)
        if m and fn.kind != "macro":
            ctx.add("camera.lookat", fn.file, fn.line_at(m.start()), 0.85, f"a basis from cross(forward, up) in {fn.name}()")
    for fn in ctx.functions:
        if fn.name not in ctx.entries or len(fn.params) < 2:
            continue
        coord = fn.params[1].name
        for loop in fn.loops:
            if loop.parent is not None or not loop.var:
                continue
            body = fn.text(loop.keyword, loop.end)
            if re.search(r"\b" + re.escape(coord) + r"(?: \. \w+)? \+ [^;]*\b" + re.escape(loop.var) + r"\b", body) or \
                    re.search(r"vec2 \( float \( " + re.escape(loop.var) + r" \) , float \( \w+ \) \) / float \( \w+ \)", body):
                n, _ = ctx.resolved_bound(fn, loop)
                kid = next((c for c in fn.loops if c.parent is loop), None)
                k, _ = ctx.resolved_bound(fn, kid) if kid else (1, "")
                samples = (n or 0) * (k or 1) if n else None
                ctx.add("aa.supersample", fn.file, loop.line, 0.85,
                        f"{samples or '?'} samples per pixel offset from {coord} in {fn.name}()", samples=samples)
                ctx.loop_labels[id(loop)] = "aa samples"
                if kid:
                    ctx.loop_labels[id(kid)] = "aa samples"
                break


PASS_DETECTORS: Tuple[Tuple[str, Callable[[Ctx], None]], ...] = (
    ("hash", detect_hash),               # first: noise leans on the hash functions it finds
    ("noise", detect_noise),
    ("raymarch", detect_raymarch),       # before normals/shadows/glow: they lean on the marches and distance functions
    ("sdf", detect_sdf),
    ("normals", detect_normals),
    ("shadows_ao", detect_shadows_and_ao),
    ("lighting", detect_lighting),
    ("fbm", detect_fbm),
    ("domain_warp", detect_domain_warp),
    ("folds", detect_folds),
    ("voronoi", detect_voronoi),
    ("palette", detect_palette),
    ("color", detect_color_pipeline),
    ("glow_volume", detect_glow_and_volume),
    ("inputs", detect_inputs),
    ("camera_aa", detect_camera_and_aa),
)


def detect_feedback(view: ShaderView) -> List[Evidence]:
    """Buffers reading their own output (ping-pong history), and buffers reading each other in a cycle."""
    out: List[Evidence] = []
    for pv in view.passes:
        if pv.type == "sound" and "mainSound" in pv.prog.functions:
            fn = pv.prog.functions["mainSound"][0]
            out.append(Evidence("audio.sound_pass", pv.file, fn.line, 0.99, f"{pv.name} synthesizes audio in mainSound()"))
    owner = {o["id"]: pv for pv in view.passes for o in pv.outputs if o.get("id")}
    edges: Dict[str, Set[str]] = {pv.file: set() for pv in view.passes}
    for pv in view.passes:
        own = {o["id"] for o in pv.outputs if o.get("id")}
        for inp in pv.inputs:
            if inp.get("type") not in ("buffer", "cubemap") or inp.get("id") not in owner:
                continue
            src = owner[inp["id"]]
            if src is not pv:
                edges[pv.file].add(src.file)
                continue
            ch = inp.get("channel")
            names = _channel_aliases(pv.prog, ch)
            lines = sorted({t.line for t in pv.prog.sig if t.text in names})
            code = " ".join(t.text for t in pv.prog.sig)
            init = bool(re.search(r"iFrame (?:==|<|<=) \d|iFrame < \d|\( iFrame (?:==|<) ", code))
            state = bool(re.search(r"texelFetch \( (?:" + "|".join(names) + r") , ivec2 \( \d+ , \d+ \)", code))
            out.append(Evidence("feedback.self", pv.file, lines[0] if lines else 1, 0.95 if lines else 0.6,
                                f"{pv.name} reads its own previous frame on iChannel{ch}",
                                {k: v for k, v in {"channel": ch, "init_guard": init or None,
                                                   "state_pixels": state or None}.items() if v is not None}))
    # cycles between passes (A reads B, B reads A): Tarjan-free, the graph is tiny
    files = sorted(edges)
    reach = {f: set() for f in files}
    for f in files:
        stack = list(edges[f])
        while stack:
            g = stack.pop()
            if g not in reach[f]:
                reach[f].add(g)
                stack.extend(edges.get(g, ()))
    seen = set()
    for f in files:
        cyc = sorted({f} | {g for g in reach[f] if f in reach.get(g, set())})
        if len(cyc) > 1 and tuple(cyc) not in seen:
            seen.add(tuple(cyc))
            out.append(Evidence("feedback.cycle", cyc[0], 1, 0.95, "passes read each other in a cycle: " + " <-> ".join(cyc),
                                {"passes": cyc}))
    return out


# ---------- cost ----------

def _cost(ctx: Ctx) -> dict:
    """Three views of a pass's per-pixel cost, from the entry points down the call graph:

    heaviest        the product of loop trip counts along the heaviest call path (100 march steps x 6 fbm octaves)
    calls_per_pixel user-function calls one pixel makes, each weighted by the trip counts around it
    work            tokens one pixel executes: every token of every reached function weighted by the trip counts
                    around it (a loop with no literal bound counts ASSUMED_TRIPS), callees included -- the one that
                    tracks render time (see ASSUMED_TRIPS for the measurement)"""
    unit = ctx.unit
    memo: Dict[tuple, Tuple[float, list, float, float]] = {}
    active: Set[tuple] = set()
    sym_params = {}
    for name in unit.callables():
        ps = {lp.symbolic["param"] for fn in unit.nodes(name) for lp in fn.loops if lp.symbolic}
        if ps:
            sym_params[name] = ps

    def weigh(name: str, binding: Tuple[Tuple[str, object], ...]) -> Tuple[float, list, float, float]:
        key = (name, binding)
        if key in memo:
            return memo[key]
        if key in active:
            return (1.0, [], 0.0, 0.0)
        active.add(key)
        bind = dict(binding)
        best_w, best_path, calls, work = 1.0, [], 0.0, 0.0
        for fn in unit.nodes(name):
            def trips(lp: G.Loop) -> Optional[int]:
                if lp.bound is not None:
                    return lp.bound
                return lp.bound_with(bind.get(lp.symbolic["param"])) if lp.symbolic else None

            def mult(loops: Sequence[G.Loop]) -> Tuple[float, list]:
                w, path = 1.0, []
                for lp in loops:
                    n = trips(lp)
                    w *= n if n is not None else 1
                    path.append({"kind": "loop", "fn": fn.name, "file": fn.file, "line": lp.line, "bound": n,
                                 "label": ctx.loop_labels.get(id(lp), "loop")})
                return w, path
            # executed tokens: each token weighted by the trips of the loops around it
            fn_work = 0.0
            spans = [(lp.keyword, lp.end, trips(lp) if trips(lp) is not None else ASSUMED_TRIPS) for lp in fn.loops]
            for k in range(fn.start, fn.end):
                m = 1.0
                for a, b, n in spans:
                    if a <= k < b:
                        m *= n
                fn_work += m
            for lp in fn.loops:
                chain, p = [], lp
                while p is not None:
                    chain.insert(0, p)
                    p = p.parent
                w, path = mult(chain)
                if w > best_w:
                    best_w, best_path = w, path
            # unit.calls: a function the body hands to a macro that calls it is this body's call (glsl.Unit.calls)
            for c in unit.calls(fn):
                if c.builtin or c.name == name or c.name not in unit.graph:
                    continue
                encl = fn.enclosing_loops(c.idx)
                w, path = mult(encl)
                wm = 1.0
                for lp in encl:
                    n = trips(lp)
                    wm *= n if n is not None else ASSUMED_TRIPS
                sub_bind = []
                for k, p in enumerate(next(iter(unit.nodes(c.name))).params):
                    if p.name in sym_params.get(c.name, ()) and k < len(c.args):
                        a, b = c.args[k]
                        arg = fn.toks[a:b]
                        v = bind.get(arg[0].text) if len(arg) == 1 and arg[0].text in bind else \
                            fn.prog.evaluate(arg, fn.locals)
                        if v is not None:
                            sub_bind.append((p.name, v))
                sw, spath, scalls, swork = weigh(c.name, tuple(sorted(sub_bind)))
                calls += w * (1 + scalls)
                fn_work += wm * swork
                total = w * sw
                if total > best_w or (total == best_w and len(path) + len(spath) + 1 > len(best_path)):
                    best_w = total
                    best_path = path + [{"kind": "call", "fn": c.name, "file": fn.file, "line": c.line}] + spath
            work = max(work, fn_work)
        active.discard(key)
        memo[key] = (best_w, best_path, calls, work)
        return memo[key]

    best = (1.0, [], 0.0, 0.0)
    entry = None
    for e in sorted(unit.entries()):
        r = weigh(e, ())
        if entry is None or r[0] > best[0]:
            best, entry = r, e
    unknown = sum(1 for fn in ctx.functions for lp in fn.loops if ctx.resolved_bound(fn, lp)[0] is None)
    big = lambda v: int(round(v)) if v < 1e15 else v
    return {"entry": entry, "heaviest": big(best[0]), "path": best[1], "calls_per_pixel": big(best[2]),
            "work": big(best[3]), "unknown_loops": unknown, "text": _path_text(entry, best[1])}


def _path_text(entry: Optional[str], path: list) -> str:
    if not entry:
        return ""
    parts, factors = [entry], []
    for step in path:
        if step["kind"] == "call":
            parts.append(step["fn"])
        else:
            n = step["bound"]
            parts.append(f"[{step['label']} x{n if n is not None else '?'} {step['file']}:{step['line']}]")
            factors.append(str(n) if n is not None else "?")
    prod = " x ".join(factors) if factors else "1"
    return f"{prod}  ({' > '.join(parts)})"


# ---------- the report ----------

def dissect_view(view: ShaderView, min_conf: float = MIN_CONF) -> dict:
    evidence: List[Evidence] = []
    passes = []
    live_any: Dict[str, Set[str]] = {}
    for pv in view.passes:
        ctx = Ctx(view, pv)
        for _, det in PASS_DETECTORS:
            det(ctx)
        evidence.extend(ctx.evidence)
        for fn in ctx.fns:
            live_any.setdefault(fn.file, set()).add(fn.name)
        dead = [fn for fn in pv.prog.all_functions() if fn.name not in ctx.live]
        passes.append({"name": pv.name, "type": pv.type, "file": pv.file, "entries": pv.unit.entries(),
                       "size": pv.prog.size(), "dead": [{"name": f.name, "line": f.line} for f in dead],
                       "unsure_ifs": pv.prog.unsure_ifs, "problems": pv.prog.problems,
                       "cost": _cost(ctx), "call_graph": G.call_graph(pv.unit)})
    evidence.extend(detect_feedback(view))
    common = None
    if view.common is not None:
        live = live_any.get(view.common.file, set())
        dead = [fn for fn in view.common.all_functions() if fn.name not in live]
        common = {"file": view.common.file, "size": view.common.size(),
                  "dead": [{"name": f.name, "line": f.line} for f in dead]}
    best: Dict[Tuple[str, str, int], Evidence] = {}
    for e in evidence:
        k = (e.tag, e.file, e.line)
        if k not in best or e.conf > best[k].conf:
            best[k] = e
    by_tag: Dict[str, List[Evidence]] = {}
    for e in best.values():
        by_tag.setdefault(e.tag, []).append(e)
    techniques = []
    for tag in sorted(by_tag):
        ev = sorted(by_tag[tag], key=lambda e: (-e.conf, e.file, e.line))
        techniques.append({"tag": tag, "group": tag.split(".")[0], "conf": ev[0].conf, "count": len(ev),
                           "evidence": [e.row() for e in ev]})
    tags = [t["tag"] for t in techniques if t["conf"] >= min_conf]
    sizes = [p["size"] for p in passes] + ([common["size"]] if common else [])
    size = {k: sum(s[k] for s in sizes) for k in ("lines", "code_lines", "comment_lines", "chars", "functions", "loops")}
    size["passes"] = len(passes) + (1 if common else 0)
    size["dead_functions"] = sum(len(p["dead"]) for p in passes) + (len(common["dead"]) if common else 0)
    costs = [p["cost"] for p in passes]
    heaviest = max(costs, key=lambda c: c["heaviest"]) if costs else None
    return {"api": API, "id": view.sid, "name": view.name, "author": view.author, "source": view.source,
            "min_conf": min_conf, "tags": tags, "groups": sorted({t.split(".")[0] for t in tags}),
            "techniques": techniques, "passes": passes, "common": common, "size": size,
            "cost": {"heaviest": heaviest["heaviest"] if heaviest else 1,
                     "heaviest_pass": next((p["file"] for p in passes if p["cost"] is heaviest), None),
                     "path": heaviest["text"] if heaviest else "",
                     "calls_per_pixel": sum(c["calls_per_pixel"] for c in costs),
                     "work": sum(c["work"] for c in costs),
                     "unknown_loops": sum(c["unknown_loops"] for c in costs)}}


def dissect(target: str, min_conf: float = MIN_CONF, corpus: Optional[Path] = None) -> dict:
    return dissect_view(load(target, corpus), min_conf)


# ---------- the atlas view: where a dissection lands in the house parts catalogue ----------

def atlas_map(rep: dict, atlas: Optional[dict] = None) -> dict:
    """A dissection's tags placed in the primitive atlas (arsenal/shaders/atlas.json), for `dissect --atlas` and the Shelf.

    Two kinds of link, kept apart because they mean different things. CATEGORIES come from the evidence: each tag this
    dissection found lands on the categories the atlas's own tag table names (atlas.categories_for_tag), in the atlas's
    category order. GROUPS and PARTS come from the atlas's curation: the groups this shader exemplifies and the parts it
    teaches best, matched by its corpus id (a loose file has none). A tag the table does not place is listed in
    `unmapped`, never dropped, so a gap in the table is visible where it bites."""
    from . import atlas as A
    atlas = atlas if atlas is not None else A.load()
    order = {c["id"]: i for i, c in enumerate(atlas["categories"])}
    cats = {c["id"]: c for c in atlas["categories"]}
    tag_map: Dict[str, List[str]] = {}
    by_cat: Dict[str, List[str]] = {}
    for tag in rep.get("tags") or []:
        ids = A.categories_for_tag(tag, atlas)
        tag_map[tag] = ids
        for cid in ids:
            by_cat.setdefault(cid, []).append(tag)
    categories = [{"id": cid, "name": cats.get(cid, {}).get("name"), "family": cats.get(cid, {}).get("family"),
                   "tags": tags} for cid, tags in sorted(by_cat.items(), key=lambda kv: (order.get(kv[0], 10 ** 6), kv[0]))]
    sid = rep.get("id")
    groups = [{"name": g["name"], "status": g.get("status"), "cost": g.get("cost"), "line": g.get("line"),
               "study_only": sid in (g.get("study_only") or [])}
              for g in atlas.get("groups") or [] if sid and sid in (g.get("exemplars") or [])]
    parts = [{"id": p["id"], "category": p.get("category"), "functions": list(p.get("functions") or []),
              "module": p.get("module"), "status": p.get("status"), "cost": p.get("cost")}
             for p in atlas.get("parts") or [] if sid and sid in (p.get("exemplars") or [])]
    return {"tags": tag_map, "categories": categories, "unmapped": [t for t, ids in tag_map.items() if not ids],
            "groups": groups, "parts": parts}


def human_atlas(m: dict) -> str:
    out = [f"ATLAS  {len(m['categories'])} categories from the tags, {len(m['groups'])} groups and "
           f"{len(m['parts'])} parts from the atlas's exemplars"]
    for c in m["categories"]:
        out.append(f"  [{c['id']}] {c['name'] or '?'}  <- {', '.join(c['tags'])}")
    if m["unmapped"]:
        out.append("  no category for: " + ", ".join(m["unmapped"]))
    if m["groups"]:
        out.append("  groups: " + ", ".join(g["name"] + (" (study only)" if g["study_only"] else "") for g in m["groups"]))
    if m["parts"]:
        shown = [f"{p['id']} {'/'.join(p['functions'][:2]) or p['module']}" for p in m["parts"][:12]]
        out.append("  parts it teaches: " + "; ".join(shown) + (f" ... +{len(m['parts']) - 12}" if len(m["parts"]) > 12 else ""))
    return "\n".join(out)


def human(rep: dict, evidence: int = EVIDENCE_SHOWN) -> str:
    s = rep["size"]
    out = [f"{rep['name']} by {rep['author'] or '?'}  ({rep['id']})",
           f"  {s['passes']} pass(es), {s['lines']} lines ({s['code_lines']} code), {s['functions']} functions "
           f"({s['dead_functions']} dead), {s['loops']} loops"]
    shown = [t for t in rep["techniques"] if t["conf"] >= rep["min_conf"]]
    out.append(f"TECHNIQUES ({len(shown)} at conf >= {rep['min_conf']})")
    group = None
    for t in shown:
        if t["group"] != group:
            group = t["group"]
            out.append(f"  [{GROUPS.get(group, group)}]")
        out.append(f"    {t['tag']:<24} {t['conf']:.2f}  x{t['count']}")
        for e in t["evidence"][:evidence]:
            params = ", ".join(f"{k}={v}" for k, v in e["params"].items() if k != "bound_note")
            out.append(f"        {e['file']}:{e['line']}  {e['detail']}" + (f"  ({params})" if params else ""))
    weak = [t for t in rep["techniques"] if t["conf"] < rep["min_conf"]]
    if weak:
        out.append("  below the floor: " + ", ".join(f"{t['tag']} {t['conf']:.2f}" for t in weak))
    out.append("COST")
    for p in rep["passes"]:
        c = p["cost"]
        out.append(f"  {p['file']:<14} heaviest {c['heaviest']:,}  = {c['text']}")
        out.append(f"  {'':<14} ~{c['calls_per_pixel']:,} user calls/pixel, ~{c['work']:,} tokens executed/pixel" +
                   (f", {c['unknown_loops']} loop(s) with no literal bound" if c["unknown_loops"] else ""))
    dead = [(p["file"], d) for p in rep["passes"] for d in p["dead"]] + \
        ([(rep["common"]["file"], d) for d in rep["common"]["dead"]] if rep.get("common") else [])
    if dead:
        out.append("DEAD CODE  " + ", ".join(f"{f}:{d['line']} {d['name']}()" for f, d in dead[:12]) +
                   (f" ... +{len(dead) - 12}" if len(dead) > 12 else ""))
    notes = [f"{p['file']}: #if at line(s) {p['unsure_ifs']} could not be evaluated (first branch kept)"
             for p in rep["passes"] if p["unsure_ifs"]] + [x for p in rep["passes"] for x in p["problems"]]
    notes += [f"{p['file']}: no entry point found (no {'/'.join(G.ENTRY_POINTS[:3])} and no top-level code calling a "
              f"function), so none of its code was followed: no technique searched, no cost walked, every function it "
              f"defines listed dead"
              for p in rep["passes"] if not p["entries"]]
    if notes:
        out.append("NOTES  " + "; ".join(notes))
    return "\n".join(out)


# ---------- the door: py -m arsenal shader dissect ... ----------

def _register(sub) -> None:
    p = sub.add_parser("dissect", help="one shader's techniques (tagged, with file:line evidence), cost and dead code")
    p.add_argument("target", help="a corpus id or name, a Shadertoy .json, or a .frag/.glsl file")
    p.add_argument("--min-conf", type=float, default=MIN_CONF, help=f"floor for a tag to count (default {MIN_CONF})")
    p.add_argument("--evidence", type=int, default=EVIDENCE_SHOWN, help="evidence lines shown per technique")
    p.add_argument("--atlas", action="store_true",
                   help="also place the tags in the primitive atlas: categories, and the groups and parts it exemplifies")
    p.set_defaults(fn=_cmd)


def _cmd(ns) -> int:
    from .cli import _print
    try:
        rep = dissect(ns.target, ns.min_conf)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if getattr(ns, "atlas", False):
        rep["atlas"] = atlas_map(rep)
    _print(rep, ns.json, lambda r: human(r, ns.evidence) + ("\n" + human_atlas(r["atlas"]) if "atlas" in r else ""))
    return 0


def _hook() -> None:
    from . import cli
    cli.VERBS["dissect"] = _register


_hook()
