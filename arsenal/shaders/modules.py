"""The house GLSL module core: one format, one resolver, one composer, so a change to a module reaches every surface.

    py -m arsenal shader lib list                  # every module the house has, by category
    py -m arsenal shader lib show <name>           # header, what it provides, what it needs (resolved)
    py -m arsenal shader lib compose <name>... [--target webgl2|webgl1|three-r186|three-r186-glsl1|toy]
                                                   # the dependency-ordered GLSL a host pastes under its preamble
    py -m arsenal shader lib lint                  # the shader-craft floors a module can be checked against blind
    py -m arsenal shader lib manifests [--write]   # each module as an arsenal.module/v0 manifest (the one registry)
    py -m arsenal shader lib index [--write]       # arsenal/web/glsl/index.json for pages, plus a content archive

WHY THIS EXISTS. Daniel, 2026-10-13: "synthesize across our concurrent creative arcs so we can have reusable structures,
methodology and a unified ui across all of them ... this way we can tweak one module and have everything update." On that
night the house had three module systems that never met (arsenal.module/v0 manifests, the `//!` chunk headers in
design/vfx-chunks, and the vfx graph/group/composition JSON), and every live surface inlined its own copy of the same hash
(Heimdall's blind census, research/reviewed/shader-school-2026-10-13/). This file is the meeting point:

  FORMAT. A module is a .glsl file whose LEADING `//!` lines are one JSON header -- the chunk format the bench has used
  since 2026-08-02, unchanged for a one-line header, extended to several lines for a library module that carries params,
  credits and a licence. Required: name, kind. Kind "helper" (and function/recipe/library/const) means the body is
  top-level GLSL (functions, consts) and can be COMPOSED; any other kind (source, modifier, domain, blend, mask) is a
  statement SNIPPET that only a chain compiler can place, so it is never composed -- its helpers form a PRELUDE instead.

  DEPENDENCIES ARE READ FROM THE CODE. A module needs every module that defines a function it calls, plus anything it
  names in `needs` (a module name or a function name). The legacy chunks are why: they wrote their dependencies in prose,
  once by chunk ("Needs rot2") and once by function ("Needs h31"), and nothing ever resolved either. Comments are stripped
  before reading, so a function named in a comment is not a dependency.

  COMPOSITION IS DETERMINISTIC BYTES. resolve() is a topological sort that breaks ties by (order, name), so the request
  order never matters and two surfaces asking for the same modules get the same text. The browser twin
  (arsenal/web/glsl/modlib.js) implements the same algorithm and a pin holds the two byte-identical, because "everything
  updates" is only true if a page and a CLI composing the same modules cannot disagree.

  ONE REGISTRY. manifest_for() turns a module into an arsenal.module/v0 manifest with a `shader` block, so GLSL modules
  live in the same registry as the media and present modules, validated by the same arsenal/registry.py.

S1 EXTENSIONS (shader school, 2026-10-13; research/in-flight/shader-school-2026-10-13/unified-architecture-draft.md 4.2
and the reconciled build spec beside it). Each one closes a way a page could break far from its cause:

  STRUCTS AND CONSTANTS ARE PROVIDERS. `struct VolAccum {` provides VolAccum and a top-level `const float TAU = ...`
  provides TAU (a comma list provides every name). A module that USES one anywhere -- any identifier token, comments
  stripped, not only a call -- depends on its provider. Only composable kinds provide them: a snippet's body sits inside
  a block of the chain compiler's main, so its consts are block-local.

  HOOKS BECOME PROTOTYPES. A header `"hooks": ["float mapScene(vec3 p)"]` names functions the HOST defines after the
  prelude. The composer writes each prototype once, in a `// hooks` block just before the first module that declares
  it (GLSL ES 3.00 allows a declaration before the definition). "Once" is by signature -- return type, name and
  parameter types; `in`, `const`, precision and parameter names never count -- because GLSL ES 1.00 calls two
  prototypes of one function a duplicate; two modules declaring one function differently are refused by name. A hook
  may not name a struct or const its own module declares (the block precedes the body, so the type would be
  undeclared): such a type lives in its own module. A call that no module provides and no hook in the module's reach
  declares is an unresolved call, and lint says so, so a typo cannot pass as a hook.

  STRICT AND LENIENT LOADING. load_library(strict=True) raises on the first bad file (CI and `lib lint`).
  strict=False, for pages and renders, quarantines the later file in path order -- a clash, a header that does not
  parse, a file that is not UTF-8 or cannot be read -- records it in library.problems and loads the rest: one bad
  file can no longer blank every surface. Path order is the path relative to its directory, POSIX-spelled, sorted by
  code point, directories in the order given (the browser twin uses the same rule).

  A QUARANTINE DOES NOT COMPOSE A DANGLING CALL. What a quarantined file would have provided is salvaged from its text
  (its functions; its structs and consts unless its kind is readable and not composable), and compose() and prelude()
  refuse a module that calls one, or uses one of its structs or consts outside a parameter or local of its own name,
  naming that file. A file whose text the library could not read in full -- unreadable on disk, not fetched by a
  page (a 404 from a stale index, a dropped connection), or holding an undecodable byte in its code -- is an UNKNOWN
  provider (library.unknown): while one is quarantined, any module with an unresolved call is refused, naming those
  files, because the call may have been theirs. (A struct such a file declared is caught when called, as a
  constructor; used only as a type it reaches the compiler, whose error names it.) Bytes are decoded as a page decodes
  them -- UTF-8, each malformed sequence replaced by U+FFFD, a BOM kept for the parser to drop -- so a file that is not
  UTF-8 gives both twins the same text and the same quarantine. A header nested deeper than MAX_HEADER_DEPTH is
  refused by a count both twins share (Python's json recursed out where JavaScript's JSON.parse did not).

  TARGETS. compose(names, target=...) refuses a module whose header `targets.needs` lists something the target lacks,
  naming the module and the need, instead of letting the shader fail to compile on that host. A module is GLSL ES 3.00
  (the module format says so) unless `targets.glsl` is "100", so webgl1 and a three.js RawShaderMaterial without
  glslVersion: THREE.GLSL3 ("three-r186-glsl1") take only modules that claim the ES 1.00 subset; lint checks the claim.

  THE COMPOSED HEADER. Line 1 is unchanged; line 2 names every module with its version; line 3 is the sha256 of all
  the text after line 3, so a receipt can name exactly what ran. The header values that reach it are validated at
  parse time in both twins (a name or version cannot carry a newline, a sort key cannot be a boolean or NaN).

  THE INDEX. A page cannot list a directory, so `lib index --write` writes arsenal/web/glsl/index.json (each library
  file with its sha256) and keeps a content-addressed copy of every module version under state/arsenal/glsl-archive/.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from arsenal import GLSL_MODULE_API, MODULE_PROTOCOL

API = GLSL_MODULE_API
ROOT = Path(__file__).resolve().parents[2]
LIBRARY_DIR = ROOT / "arsenal" / "web" / "glsl"           # the house library (Apache-2.0, our own code)
LEGACY_DIRS = (ROOT / "design" / "vfx-chunks",)            # the bench's chunks, read in place
DEFAULT_DIRS = (LIBRARY_DIR,) + LEGACY_DIRS
INDEX_PATH = LIBRARY_DIR / "index.json"                    # what modlib.loadLibrary reads in a page
ARCHIVE_DIR = ROOT / "state" / "arsenal" / "glsl-archive"  # <name>/<sha256>.glsl, every version ever indexed

FUNCTION_KINDS = frozenset({"helper", "function", "recipe", "library", "const"})
DEFAULT_ORDER = 50
DEFAULT_VERSION = "0.0.0"

# Kept in lockstep with arsenal/web/glsl/modlib.js (the parity pin compares their output byte for byte).
# Every pattern is ASCII by construction: whitespace is spelled [ \t\r\n\f\v] (Python's and JavaScript's \s disagree
# outside ASCII), word boundaries use re.A (JavaScript's \b is ASCII), and a definition starts a line by the lookbehind
# (?<![^\n]) instead of ^ with re.M (JavaScript's ^ also starts a line after \r, U+2028 and U+2029).
COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
DEFINITION_RE = re.compile(
    r"(?<![^\n])[ \t]*(?:(?:highp|mediump|lowp|const)[ \t\r\n\f\v]+)*([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]+"
    r"([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*\(([^()]*)\)[ \t\r\n\f\v]*\{", re.A)
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*\(", re.A)
BLANK_RUN_RE = re.compile(r"\n{3,}")
NOT_A_TYPE = frozenset({"return", "else", "if", "for", "while", "do", "switch", "case"})
ENTRY_POINTS = frozenset({"main", "mainImage", "mainCubemap", "mainSound", "mainVR"})   # placed by a runtime, never provided
# S1 providers and hooks. STRUCT_RE and CONST_RE run on top_level(code), where everything inside ( ) and { } is
# blanked, so a const inside a function or a parameter list is never seen and a comma list splits cleanly.
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*", re.A)
STRUCT_RE = re.compile(r"\bstruct[ \t\r\n\f\v]+([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*\{", re.A)
CONST_RE = re.compile(r"\bconst[ \t\r\n\f\v]+(?:(?:highp|mediump|lowp)[ \t\r\n\f\v]+)?[A-Za-z_][A-Za-z0-9_]*"
                      r"[ \t\r\n\f\v]*(?:\[[^\]]*\][ \t\r\n\f\v]*)?([^;]*);", re.A)
DECLARATOR_RE = re.compile(r"[ \t\r\n\f\v]*([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*(?:\[[^\]]*\][ \t\r\n\f\v]*)?=", re.A)
HOOK_RE = re.compile(r"(?:(?:highp|mediump|lowp) )?[A-Za-z_][A-Za-z0-9_]* ([A-Za-z_][A-Za-z0-9_]*)\([^()]*\)")
# One hook parameter is [qualifiers] type [name]: a type or name may carry one array size.
PARAM_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\[[A-Za-z0-9_]*\])?", re.A)
PARAM_DIRECTIONS = {"in": "", "out": "out ", "inout": "inout "}     # `in` is the default, so it never counts
PARAM_IGNORED = frozenset({"const", "highp", "mediump", "lowp"})    # the host template declares highp
# A name the module declares itself -- a parameter, a local, a field: `<type> <name>` before = ; , ) or [ -- so a
# use of it is not a use of a quarantined file's const of the same name (group 1 is checked against NOT_A_TYPE).
DECLARED_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]+([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*(?=[=;,)\[])",
                         re.A)
# The kind of a file whose header is not JSON, read for salvage only: a snippet's consts are block-local.
KIND_RE = re.compile(r'"kind"[ \t\r\n]*:[ \t\r\n]*"([^"\\]*)"')
MAX_HEADER_DEPTH = 32       # brackets and braces outside strings; a real header nests four deep

# Header values that reach the composed header or the sort order (both twins refuse the same ones). A name is a safe
# file name (it sorts by code unit in JavaScript and by code point in Python, which agree only on ASCII, and the
# archive writes <name>/); a version is a semantic version's characters, so "name@version" stays one token.
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*", re.A)
VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]*", re.A)
CONTROL_RE = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029\ud800-\udfff]")   # line breaks of any kind, lone surrogates

# What each target cannot do, in the words the refusal uses. webgl2 and toy (Shadertoy's WebGL2) lack nothing;
# three-r186 lacks nothing on a ShaderMaterial (three.js compiles it as GLSL ES 3.00) or with glslVersion:
# THREE.GLSL3, but a material is one pass. three-r186-glsl1 is a RawShaderMaterial without glslVersion, which three.js
# hands to WebGL as GLSL ES 1.00: the refusal the draft (4.3) promised for "a three.js material without GLSL3".
_ES1_LACKS = {
    "uint": "GLSL ES 1.00 has no unsigned integers",
    "texelFetch": "GLSL ES 1.00 has no texelFetch",
    "derivatives": "GLSL ES 1.00 has dFdx, dFdy and fwidth only through the OES_standard_derivatives extension",
}
TARGET_LACKS = {
    "webgl2": {},
    "toy": {},
    "three-r186": {},
    "three-r186-glsl1": dict(_ES1_LACKS),
    "webgl1": dict(_ES1_LACKS, **{"float-targets": "WebGL1 renders to float textures only through extensions"}),
}
TARGET_ES1_ONLY = {   # targets that compile GLSL ES 1.00: they take only a module whose targets.glsl is "100"
    "three-r186-glsl1": "a three.js RawShaderMaterial without glslVersion: THREE.GLSL3 is compiled as GLSL ES 1.00",
    "webgl1": "WebGL1 compiles GLSL ES 1.00 only",
}
_ONE_PASS = "a three.js material is one pass; a pass needs the multipass runtime"
TARGET_REFUSES_KINDS = {
    "three-r186": {"pass": _ONE_PASS},
    "three-r186-glsl1": {"pass": _ONE_PASS},
}
KNOWN_NEEDS = ("uint", "texelFetch", "derivatives", "float-targets")
GLSL_VERSIONS = ("100", "300es")

# Lint for a module that claims the GLSL ES 1.00 subset (targets.glsl "100"): the common ES 3.00-only features. A
# heuristic over the text, not a compiler; the compile check of the module's card is the proof.
ES3_ONLY_FUNCTIONS = frozenset("""
texture textureLod textureSize textureGrad textureOffset textureProj textureProjLod textureLodOffset textureProjOffset
textureProjLodOffset textureGradOffset textureProjGrad textureProjGradOffset texelFetch texelFetchOffset
sinh cosh tanh asinh acosh atanh trunc round roundEven isnan isinf modf floatBitsToInt floatBitsToUint intBitsToFloat
uintBitsToFloat packSnorm2x16 unpackSnorm2x16 packUnorm2x16 unpackUnorm2x16 packHalf2x16 unpackHalf2x16
outerProduct transpose determinant inverse
""".split())
ES3_ONLY_WORDS = frozenset("""
uint uvec2 uvec3 uvec4 switch layout flat smooth centroid usampler2D isampler2D sampler3D sampler2DArray
mat2x2 mat2x3 mat2x4 mat3x2 mat3x3 mat3x4 mat4x2 mat4x3 mat4x4
""".split())
ES3_ONLY_OPERATOR_RE = re.compile(r"<<|>>|%|~|(?<!&)&(?!&)|(?<!\|)\|(?!\|)|(?<!\^)\^(?!\^)")
ARRAY_CONSTRUCTOR_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*[ \t\r\n\f\v]*\[[^\]]*\][ \t\r\n\f\v]*\(", re.A)
DERIVATIVES = ("dFdx", "dFdy", "fwidth")

# GLSL ES 3.00 built-in functions, constructors and keywords that can precede "(": never a dependency.
BUILTINS = frozenset("""
radians degrees sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh pow exp log exp2 log2 sqrt inversesqrt
abs sign floor trunc round roundEven ceil fract mod modf min max clamp mix step smoothstep isnan isinf
floatBitsToInt floatBitsToUint intBitsToFloat uintBitsToFloat packSnorm2x16 unpackSnorm2x16 packUnorm2x16
unpackUnorm2x16 packHalf2x16 unpackHalf2x16 length distance dot cross normalize faceforward reflect refract
matrixCompMult outerProduct transpose determinant inverse lessThan lessThanEqual greaterThan greaterThanEqual equal
notEqual any all not textureSize texture textureProj textureLod textureOffset texelFetch texelFetchOffset
textureProjOffset textureLodOffset textureProjLod textureProjLodOffset textureGrad textureGradOffset textureProjGrad
textureProjGradOffset dFdx dFdy fwidth
float int uint bool vec2 vec3 vec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4 bvec2 bvec3 bvec4 mat2 mat3 mat4
mat2x2 mat2x3 mat2x4 mat3x2 mat3x3 mat3x4 mat4x2 mat4x3 mat4x4
if for while return switch do else main mainImage mainCubemap mainSound mainVR
""".split())


class ModuleError(ValueError):
    pass


def strip_comments(code: str) -> str:
    return COMMENT_RE.sub(" ", code)


def normalize_body(body: str) -> str:
    body = body.replace("\r\n", "\n").lstrip("\n").rstrip(" \t\r\n\f\v")   # not rstrip(): JavaScript's \s differs
    return BLANK_RUN_RE.sub("\n\n", body)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def top_level(code: str) -> str:
    """The code with everything inside ( ) and { } blanked, the outermost brackets kept: what GLSL sees at file scope.
    A stray closer is kept and never drives the depth below zero (the browser twin does exactly the same)."""
    out, depth = [], 0
    for ch in code:
        if ch == "(" or ch == "{":
            depth += 1
            out.append(ch if depth == 1 else " ")
        elif ch == ")" or ch == "}":
            out.append(ch if depth <= 1 else " ")
            depth = max(0, depth - 1)
        else:
            out.append(ch if depth == 0 else " ")
    return "".join(out)


def canonical_prototype(text: str) -> str:
    """One spelling per prototype, so two modules declaring one hook emit it once: single spaces, none around ( ) , ;,
    one after each comma, no trailing semicolon. "float  mapScene( vec3 p );" -> "float mapScene(vec3 p)"."""
    s = re.sub(r"[ \t\r\n\f\v]+", " ", text)
    s = re.sub(r" ?([(),;]) ?", r"\1", s)
    s = re.sub(r" ?\[ ?", "[", s)          # "float w [ 4 ]" -> "float w[4]"; the space after "]" stays
    s = re.sub(r" ?\]", "]", s)
    s = re.sub(r";+\Z", "", s)
    return s.strip(" ").replace(",", ", ")


def hook_signature(proto: str) -> Optional[Tuple[str, str, str]]:
    """(name, base, full) of a canonical prototype. base is what GLSL overloads on (the name and the parameter types);
    full adds the return type and out/inout. `in`, `const`, precision and parameter names never count, and `(void)` is
    `()`. None when a parameter is not `[qualifiers] type [name]`."""
    if not HOOK_RE.fullmatch(proto):
        return None
    open_ = proto.index("(")
    head, inner = proto[:open_].split(" "), proto[open_ + 1:-1]
    ret, name = head[-2], head[-1]
    types, full = [], []
    for param in ([] if inner in ("", "void") else inner.split(", ")):
        direction, rest = None, []
        for tok in param.split(" "):
            if tok in PARAM_DIRECTIONS:
                if direction is not None:
                    return None
                direction = PARAM_DIRECTIONS[tok]
            elif tok not in PARAM_IGNORED:
                rest.append(tok)
        if not 1 <= len(rest) <= 2 or not all(PARAM_TOKEN_RE.fullmatch(t) for t in rest):
            return None
        kind = rest[0]
        if len(rest) == 2 and "[" in rest[1]:
            if "[" in kind:
                return None                    # an array of arrays is not GLSL ES
            kind += rest[1][rest[1].index("["):]
        types.append(kind)
        full.append((direction or "") + kind)
    return name, f"{name}({','.join(types)})", f"{ret} {name}({','.join(full)})"


def _parse_hooks(header: dict, path: str, own_data: Dict[str, str]):
    """(prototypes, names, (base, full) keys). own_data maps each struct and const this module declares to its kind:
    a hook may not name one, because the hooks block is written before the module body."""
    raw = header.get("hooks")
    if raw is None:
        return (), (), ()
    if not isinstance(raw, list) or not all(isinstance(h, str) for h in raw):
        raise ModuleError(f'{path}: hooks must be a list of GLSL prototypes such as "float mapScene(vec3 p)"')
    hooks, names, keys, seen = [], [], [], {}
    for h in raw:
        proto = canonical_prototype(h)
        sig = hook_signature(proto)
        if sig is None:
            raise ModuleError(f"{path}: hook '{h}' is not a GLSL prototype (want \"float mapScene(vec3 p)\")")
        name, base, full = sig
        own = sorted((set(IDENT_RE.findall(full)) - {name, "out", "inout"}) & set(own_data))
        if own:
            what = own_data[own[0]]
            raise ModuleError(f"{path}: hook '{h}' names {what} '{own[0]}', which this module declares; the hooks block "
                              f"is written before the module body, so move the {what} to its own module")
        if base in seen:
            if seen[base][0] != full:
                raise ModuleError(f"{path}: hooks '{seen[base][1]}' and '{proto}' declare {name}() differently")
            continue
        seen[base] = (full, proto)
        hooks.append(proto)
        keys.append((base, full))
        if name not in names:
            names.append(name)
    return tuple(hooks), tuple(names), tuple(keys)


def _target_needs(header: dict) -> Tuple[str, ...]:
    t = header.get("targets")
    needs = t.get("needs") if isinstance(t, dict) else None
    return tuple(n for n in needs if isinstance(n, str)) if isinstance(needs, list) else ()


def _target_glsl(header: dict) -> str:
    """"100" only when the header claims the GLSL ES 1.00 subset; anything else is the module format's GLSL ES 3.00."""
    t = header.get("targets")
    return "100" if isinstance(t, dict) and t.get("glsl") == "100" else "300es"


@dataclass(frozen=True)
class Module:
    name: str
    path: str
    header: dict
    body: str
    provides: Tuple[str, ...]                 # every symbol it defines: functions, structs, top-level consts
    calls: Tuple[str, ...]                    # names it calls that it does not define (builtins left out)
    functions: Tuple[str, ...] = ()
    structs: Tuple[str, ...] = ()
    consts: Tuple[str, ...] = ()
    uses: Tuple[str, ...] = ()                # identifier tokens in the code and the hook prototypes, own ones out
    declared: Tuple[str, ...] = ()            # parameters, locals and fields it declares (see DECLARED_RE)
    hooks: Tuple[str, ...] = ()               # canonical prototypes, no semicolon, one per signature
    hook_names: Tuple[str, ...] = ()
    hook_keys: Tuple[Tuple[str, str], ...] = ()   # (base, full) per prototype, see hook_signature
    target_needs: Tuple[str, ...] = ()        # header targets.needs
    glsl: str = "300es"                       # header targets.glsl when it is "100"

    @property
    def kind(self) -> str:
        return str(self.header.get("kind"))

    @property
    def version(self) -> str:
        v = self.header.get("version")
        return v if isinstance(v, str) and v else DEFAULT_VERSION

    @property
    def cat(self) -> str:
        return str(self.header.get("cat") or "misc")

    @property
    def order(self) -> float:
        o = self.header.get("order")
        return DEFAULT_ORDER if o is None else float(o)     # validated finite; a float, as JavaScript sees it

    @property
    def composable(self) -> bool:
        return self.kind in FUNCTION_KINDS


def _source_lines(text: str) -> List[str]:
    """The text's lines: one leading UTF-8 BOM dropped (a page's fetch drops it, so the CLI must too), and \\r\\n and a
    lone \\r both read as a line break (JavaScript's ^ already treated \\r as one)."""
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _header_line_count(lines: List[str]) -> int:
    """How many leading lines are `//!` lines. Only spaces and tabs may precede the marker (lstrip() and trimStart()
    disagree on the rest of Unicode's whitespace)."""
    n = 0
    while n < len(lines) and lines[n].lstrip(" \t").startswith("//!"):
        n += 1
    return n


def _scan(code: str, composable: bool):
    """(functions, structs, consts) a comment-stripped body defines. Entry points are never provided: a runtime places
    them. Structs and consts count only at file scope of a composable module (a snippet's live in a block of main)."""
    functions = {m.group(2) for m in DEFINITION_RE.finditer(code)
                 if m.group(1) not in NOT_A_TYPE and m.group(2) not in ENTRY_POINTS}
    structs, consts = set(), set()
    if composable:
        scope = top_level(code)
        structs = set(STRUCT_RE.findall(scope))
        for decl in CONST_RE.findall(scope):
            for part in decl.split(","):
                d = DECLARATOR_RE.match(part)
                if d:
                    consts.add(d.group(1))
    return functions, structs, consts


def _reject_constant(name: str):
    raise ValueError(f"{name} is not a JSON value")


def _json_int(digits: str):
    # Python refuses to convert an integer of more than 4300 digits; JavaScript reads it as Infinity. Read it as a
    # float too, so an absurd order is "not a finite number" in both twins rather than "not JSON" in one.
    return int(digits) if len(digits) <= 4000 else float(digits)


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except OverflowError:
        return False


def _header_problem(header: dict) -> Optional[str]:
    """The first header value that would corrupt the composed header, the sort order or a refusal, worded exactly as
    modlib.js words it. null means absent for every optional field."""
    if not NAME_RE.fullmatch(header["name"]):
        return "the //! header's name must be letters, digits, '.', '_' or '-' (kebab-case for a library module)"
    kind, cat, version, order, needs = (header.get(k) for k in ("kind", "cat", "version", "order", "needs"))
    if not isinstance(kind, str) or CONTROL_RE.search(kind):
        return "the //! header's kind must be a string without control characters"
    if cat is not None and (not isinstance(cat, str) or CONTROL_RE.search(cat)):
        return "the //! header's cat must be a string without control characters"
    if version is not None and not (isinstance(version, str) and VERSION_RE.fullmatch(version)):
        return "the //! header's version must be letters, digits, '.', '+' or '-' (a semantic version such as \"1.2.0\")"
    if order is not None and (isinstance(order, bool) or not isinstance(order, (int, float)) or not _finite(order)):
        return "the //! header's order must be a finite number (not a boolean or a string)"
    if needs is not None and not (isinstance(needs, list) and all(isinstance(n, str) for n in needs)):
        return "the //! header's needs must be a list of module or function names"
    return None


def _header_text(lines: List[str], n: int) -> str:
    return " ".join(line.lstrip(" \t")[3:] for line in lines[:n])


def _json_depth(text: str) -> int:
    """How deep brackets and braces nest outside JSON strings. A count, not a parse, so both twins agree on any text
    (Python's json recursed out on a deep header that JavaScript's JSON.parse read)."""
    depth = deepest = 0
    in_string = escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "[" or ch == "{":
            depth += 1
            deepest = max(deepest, depth)
        elif ch == "]" or ch == "}":
            depth -= 1
    return deepest


def _parse_header_json(text: str, path: str):
    if _json_depth(text) > MAX_HEADER_DEPTH:
        raise ModuleError(f"{path}: the //! header nests deeper than {MAX_HEADER_DEPTH} levels")
    try:
        return json.loads(text, parse_constant=_reject_constant, parse_int=_json_int)
    except json.JSONDecodeError as exc:
        raise ModuleError(f"{path}: the //! header is not JSON ({exc.msg} at column {exc.colno})") from None
    except (ValueError, RecursionError) as exc:
        raise ModuleError(f"{path}: the //! header is not JSON ({exc})") from None


def parse_module(text: str, path: str = "<text>") -> Module:
    """A module from its source text. ModuleError (naming the file) when the header is missing, not JSON, nested too
    deep, unnamed, or carries a value of the wrong type, or when a hook is malformed."""
    lines = _source_lines(text)
    n = _header_line_count(lines)
    if not n:
        raise ModuleError(f"{path}: no //! header on the first line")
    header = _parse_header_json(_header_text(lines, n), path)
    if not isinstance(header, dict) or not isinstance(header.get("name"), str) or header.get("kind") in (None, ""):
        raise ModuleError(f"{path}: the //! header needs a name and a kind")
    problem = _header_problem(header)
    if problem:
        raise ModuleError(f"{path}: {problem}")
    body = "\n".join(lines[n:])
    code = strip_comments(body)
    functions, structs, consts = _scan(code, header["kind"] in FUNCTION_KINDS)
    own_data = dict({c: "const" for c in consts}, **{s: "struct" for s in structs})
    hooks, hook_names, hook_keys = _parse_hooks(header, str(path), own_data)
    own = functions | structs | consts
    provides = sorted(own)
    calls = sorted({c for c in CALL_RE.findall(code) if c not in BUILTINS} - own)
    scope = code + "\n" + "\n".join(hooks)
    uses = sorted(set(IDENT_RE.findall(scope)) - BUILTINS - own)
    declared = sorted({d.group(2) for d in DECLARED_RE.finditer(scope) if d.group(1) not in NOT_A_TYPE})
    return Module(header["name"], str(path), header, body, tuple(provides), tuple(calls),
                  functions=tuple(sorted(functions)), structs=tuple(sorted(structs)), consts=tuple(sorted(consts)),
                  uses=tuple(uses), declared=tuple(declared), hooks=hooks, hook_names=hook_names,
                  hook_keys=hook_keys, target_needs=_target_needs(header), glsl=_target_glsl(header))


def decode_source(data: bytes, path: str = "<bytes>") -> Tuple[str, Optional[str]]:
    """(text, problem): the bytes decoded as UTF-8 the way a page's TextDecoder decodes them -- each malformed
    sequence one U+FFFD, a leading BOM kept for the parser to drop -- and None, or why the file is not UTF-8, naming
    its first bad byte. modlib.decodeSource is the twin; the parity plan compares them on hostile bytes."""
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        return (data.decode("utf-8", errors="replace"),
                f"{path}: is not UTF-8 text (byte {exc.start} cannot be decoded)")


def _salvage_kind(header_text: str) -> Optional[str]:
    """The kind a broken file declares, if it can be read: from the header when it parses, else from a "kind" string
    in its text. None when neither says."""
    try:
        header = _parse_header_json(header_text, "")
    except ModuleError:
        found = KIND_RE.search(header_text)
        return found.group(1) if found else None
    if isinstance(header, dict) and isinstance(header.get("kind"), str):
        return header["kind"]
    return None


def _salvage_symbols(text: str, replaced: bool = False) -> Tuple[Tuple[str, ...], Tuple[str, ...], bool]:
    """(functions, structs and consts, known) that a quarantined file would have provided, read from its text after the
    `//!` lines. Structs and consts count unless the file's kind is readable and not composable (a snippet's consts
    are block-local); an unreadable kind keeps them, failing closed. known is False when the salvage itself failed,
    or when the text was decoded with replacements (replaced) and one sits in the code, where it could have hidden a
    definition. Never raises: a salvage lets compose() name this file instead of composing a dangling call."""
    try:
        lines = _source_lines(text)
        n = _header_line_count(lines)
        kind = _salvage_kind(_header_text(lines, n))
        code = strip_comments("\n".join(lines[n:]))
        functions, structs, consts = _scan(code, kind is None or kind in FUNCTION_KINDS)
        return tuple(sorted(functions)), tuple(sorted(structs | consts)), not (replaced and "\ufffd" in code)
    except Exception:  # noqa: BLE001 -- a salvage that fails makes the file unknown, which refuses more, never less
        return (), (), False


def _symbol_kind(m: Module, sym: str) -> str:
    return "function" if sym in m.functions else "struct" if sym in m.structs else "const"


@dataclass
class Library:
    modules: Dict[str, Module] = field(default_factory=dict)
    providers: Dict[str, str] = field(default_factory=dict)      # symbol -> the module that provides it
    data: Dict[str, str] = field(default_factory=dict)           # struct and const symbols only (used, not called)
    strict: bool = True
    problems: List[dict] = field(default_factory=list)           # quarantined files: {path, name, problem}
    lost: Dict[str, Tuple[str, bool]] = field(default_factory=dict)   # symbol a quarantined file had -> (path, data?)
    lost_modules: Dict[str, str] = field(default_factory=dict)        # name of a quarantined module -> its path
    unknown: List[str] = field(default_factory=list)   # quarantined files whose text could not be read in full

    def quarantine(self, path: str, name: Optional[str], problem: str,
                   functions: Sequence[str] = (), data: Sequence[str] = (), unknown: bool = False) -> None:
        """Record a file the library refused. Its symbols are remembered (the first quarantined file wins), so a
        module that calls one is refused at compose time naming this file, not handed to the compiler dangling. An
        unknown file (its text could not be read in full) may have held anything, so while one is recorded every
        unresolved call is refused, naming it."""
        self.problems.append({"path": path, "name": name, "problem": problem})
        for sym in functions:
            self.lost.setdefault(sym, (path, False))
        for sym in data:
            self.lost.setdefault(sym, (path, True))
        if name is not None:
            self.lost_modules.setdefault(name, path)
        if unknown:
            self.unknown.append(path)

    def _unknown_note(self) -> str:
        return f"a quarantined file the library could not read in full may: {', '.join(self.unknown)}"

    def add(self, m: Module) -> bool:
        """Add a module. A name or symbol clash raises when strict; when lenient the newcomer is quarantined."""
        problem = None
        if m.name in self.modules:
            problem = f"two modules are named '{m.name}': {self.modules[m.name].path} and {m.path}"
        else:
            for sym in m.provides:
                if sym in self.providers:
                    other = self.providers[sym]
                    problem = (f"{_symbol_kind(m, sym)} '{sym}' is provided by two modules: "
                               f"{other} ({self.modules[other].path}) and {m.name} ({m.path})")
                    break
        if problem:
            if self.strict:
                raise ModuleError(problem)
            self.quarantine(m.path, m.name, problem, m.functions, m.structs + m.consts)
            return False
        self.modules[m.name] = m
        for sym in m.provides:
            self.providers[sym] = m.name
        for sym in m.structs + m.consts:
            self.data[sym] = m.name
        return True

    def names(self) -> List[str]:
        return sorted(self.modules)

    def get(self, name: str) -> Module:
        if name not in self.modules:
            raise ModuleError(f"no module named '{name}'")      # not !r: JavaScript quotes the same way for any name
        return self.modules[name]

    def _key(self, name: str):
        return (self.modules[name].order, name)

    def deps(self, name: str) -> List[str]:
        """Direct dependencies: modules defining a function this one calls or a struct or const it uses, plus its
        `needs` (module or symbol names)."""
        m = self.get(name)
        out = {self.providers[c] for c in m.calls if c in self.providers and self.providers[c] != name}
        out |= {self.data[u] for u in m.uses if u in self.data}
        for need in m.header.get("needs") or []:
            if need in self.modules:
                out.add(need)
            elif need in self.providers:
                out.add(self.providers[need])
            else:
                where = self.lost_modules.get(need) or (self.lost[need][0] if need in self.lost else None)
                raise ModuleError(f"module '{name}' needs '{need}', which no module is named or defines" + (
                    f" (only the quarantined file {where} did; see library.problems)" if where else
                    f" ({self._unknown_note()}; see library.problems)" if self.unknown else ""))
        out.discard(name)
        return sorted(out, key=self._key)

    def resolve(self, names: Iterable[str]) -> List[str]:
        """Every module the request needs, dependencies first; ties broken by (order, name), so request order is moot."""
        closure, stack = set(), list(names)
        while stack:
            n = stack.pop()
            if n in closure:
                continue
            self.get(n)
            closure.add(n)
            stack.extend(self.deps(n))
        pending = {n: set(self.deps(n)) for n in closure}
        out = []
        while pending:
            ready = sorted((n for n, d in pending.items() if not d), key=self._key)
            if not ready:
                raise ModuleError("dependency cycle among: " + ", ".join(sorted(pending)))
            nxt = ready[0]
            out.append(nxt)
            del pending[nxt]
            for d in pending.values():
                d.discard(nxt)
        return out

    def unresolved(self, name: str) -> List[str]:
        """Calls that no module provides and no hook declares, counting the hooks of every module in this one's reach
        (its own and its dependencies': their prototypes are emitted before it). A typo cannot pass as a hook."""
        m = self.get(name)
        hooks = {h for n in self.resolve([name]) for h in self.modules[n].hook_names}
        return [c for c in m.calls if c not in self.providers and c not in hooks]

    def check_target(self, order: Sequence[str], target: Optional[str]) -> None:
        """Refuse, naming each module and what it needs, when the target cannot run part of this composition."""
        if target is None:
            return
        if target not in TARGET_LACKS:
            raise ModuleError(f"unknown target '{target}' (known: {', '.join(sorted(TARGET_LACKS))})")
        lacks, kinds = TARGET_LACKS[target], TARGET_REFUSES_KINDS.get(target, {})
        es1_only = TARGET_ES1_ONLY.get(target)
        refusals = []
        for n in order:
            m = self.modules[n]
            if m.kind in kinds:
                refusals.append(f"module '{n}' is kind '{m.kind}' ({kinds[m.kind]})")
            if es1_only and m.glsl != "100":
                refusals.append(f"module '{n}' is GLSL ES 3.00 ({es1_only}; a module written for both declares "
                                "targets.glsl \"100\")")
            refusals += [f"module '{n}' needs {need} ({lacks[need]})" for need in m.target_needs if need in lacks]
        if refusals:
            raise ModuleError(f"target '{target}' cannot take this composition: " + "; ".join(refusals))

    def check_quarantine(self, order: Sequence[str]) -> None:
        """Refuse a composition in which a module calls, or uses as a type or constant, a symbol that only a
        quarantined file provides: lenient loading must never hand a page a dangling call (the review of 2026-10-13
        found it composing one silently). While an unknown file is quarantined, every unresolved call is refused
        too, naming the unknown files: the call may have been theirs (the re-review found a 404 composing one). A
        hook in the module's reach still covers a call: the host defines it. A use of a lost struct or const is not
        counted where the module declares that name itself (a parameter or local named like it)."""
        if not self.lost and not self.unknown:
            return
        refusals = []
        for n in order:
            m, called = self.modules[n], []
            for c in self.unresolved(n):
                if c in self.lost:
                    called.append(c)
                    refusals.append(f"module '{n}' calls {c}() (only the quarantined file {self.lost[c][0]} "
                                    "provides it)")
                elif self.unknown:
                    refusals.append(f"module '{n}' calls {c}(), which no loaded module provides "
                                    f"({self._unknown_note()})")
            refusals += [f"module '{n}' uses {u} (only the quarantined file {self.lost[u][0]} provides it)"
                         for u in m.uses if u in self.lost and self.lost[u][1] and u not in self.providers
                         and u not in called and u not in m.declared]
        if refusals:
            raise ModuleError("cannot compose: part of it was quarantined at load (see library.problems): " +
                              "; ".join(refusals))

    def _emit(self, order: Sequence[str]) -> str:
        """Line 1 names the order (unchanged since v1), line 2 each module's version, line 3 the sha256 of every byte
        after line 3. Each hook prototype is written once per signature, just before the first module that declares
        it; two modules declaring one function differently are refused instead of handed to the compiler."""
        parts, emitted = [], {}
        for n in order:
            m = self.modules[n]
            fresh = []
            for h, (base, full) in zip(m.hooks, m.hook_keys):
                if base in emitted:
                    first_full, first_module, first_hook = emitted[base]
                    if first_full != full:
                        raise ModuleError(f"modules '{first_module}' and '{n}' declare the hook "
                                          f"{base[:base.index('(')]}() differently: '{first_hook}' and '{h}'")
                    continue
                emitted[base] = (full, n, h)
                fresh.append(h)
            if fresh:
                parts.append("// hooks\n" + "\n".join(h + ";" for h in fresh))
            parts.append(f"// --- {n} ({m.cat}) ---\n" + normalize_body(m.body))
        text = "\n" + "\n\n".join(parts) + "\n" if parts else ""
        head = [f"// {API} compose: " + ", ".join(order),
                "// modules:" + "".join(f" {n}@{self.modules[n].version}" for n in order),
                "// sha256: " + sha256_hex(text)]
        return "\n".join(head) + "\n" + text

    def compose(self, names: Iterable[str], target: Optional[str] = None) -> str:
        """The GLSL for these modules and everything they need, in dependency order. Snippets are refused, and so is
        any module the target cannot run (target None: no target check)."""
        order = self.resolve(names)
        self.check_target(order, target)
        self.check_quarantine(order)
        snippets = [n for n in order if not self.modules[n].composable]
        if snippets:
            raise ModuleError("cannot compose a snippet (" + ", ".join(
                f"{n}: kind '{self.modules[n].kind}'" for n in snippets) +
                "); a chain compiler places snippets -- use prelude() for the helpers they need")
        return self._emit(order)

    def prelude(self, names: Iterable[str], target: Optional[str] = None) -> str:
        """The composable modules these names need (snippets themselves left out): what a chain compiler pastes first.
        The target check covers the snippets too: they run on the same host, and so does the quarantine check."""
        order = self.resolve(names)
        self.check_target(order, target)
        self.check_quarantine(order)
        return self._emit([n for n in order if self.modules[n].composable])


def _add_source(lib: Library, path: str, text: str) -> None:
    """Parse one file into the library. Strict lets any failure raise; lenient quarantines whatever went wrong --
    a ModuleError or a bug in the parser alike, since a page must not blank over one file -- with what the file would
    have provided, so a module calling it is refused naming this file."""
    try:
        m = parse_module(text, path)
    except Exception as exc:  # noqa: BLE001 -- lenient means one file can never take the library down
        if lib.strict:
            raise
        problem = str(exc) if isinstance(exc, ModuleError) else f"{path}: {type(exc).__name__}: {exc}"
        functions, data, known = _salvage_symbols(text)
        lib.quarantine(path, None, problem, functions, data, unknown=not known)
        return
    lib.add(m)


def _add_bytes(lib: Library, path: str, data: bytes) -> None:
    """Decode one file's bytes as a page does and parse it. Bytes that are not UTF-8 quarantine the file (strict
    raises) with what its replaced text still shows it provided; it is unknown too if a replacement sits in code."""
    text, problem = decode_source(data, path)
    if problem is None:
        _add_source(lib, path, text)
        return
    if lib.strict:
        raise ModuleError(problem)
    functions, symbols, known = _salvage_symbols(text, replaced=True)
    lib.quarantine(path, None, problem, functions, symbols, unknown=not known)


def _add_unread(lib: Library, path: str, problem: Optional[str]) -> None:
    """A file named but not read (an OSError; in a page, a failed fetch): strict raises, lenient records it unknown."""
    problem = problem or f"{path}: could not be read"
    if lib.strict:
        raise ModuleError(problem)
    lib.quarantine(path, None, problem, unknown=True)


def library_from_sources(sources: Iterable[Sequence], strict: bool = True) -> Library:
    """A library from sources in load order: (path, text), (path, bytes) decoded as a page decodes them, or (path,
    None, problem) for a file that could not be read. Strict raises on the first bad file; lenient quarantines it (a
    broken header, a malformed hook, bytes that are not UTF-8, an unread file, or a name or symbol an earlier file
    already took) and loads the rest. modlib.libraryFromSources takes the same three shapes."""
    lib = Library(strict=strict)
    for source in sources:
        path, content = source[0], source[1]
        if content is None:
            _add_unread(lib, path, source[2] if len(source) > 2 else None)
        elif isinstance(content, (bytes, bytearray, memoryview)):
            _add_bytes(lib, path, bytes(content))
        else:
            _add_source(lib, path, content)
    return lib


def _module_files(d: Path) -> List[Path]:
    """The .glsl FILES under d in load order (a directory named x.glsl is not one): the POSIX path relative to d,
    sorted by code point."""
    return sorted((p for p in d.rglob("*.glsl") if p.is_file()), key=lambda p: p.relative_to(d).as_posix())


def load_library(dirs: Optional[Iterable] = None, strict: bool = True) -> Library:
    """Every module under dirs (default: the library, then the bench chunks). Strict raises a ModuleError naming the
    first bad file; lenient quarantines a file it cannot read (an unknown provider), decode or parse, and loads the
    rest. Files are read as bytes and decoded as a page decodes them, with no newline translation."""
    lib = Library(strict=strict)
    for d in (DEFAULT_DIRS if dirs is None else dirs):
        d = Path(d)
        if not d.exists():
            continue
        for p in _module_files(d):
            try:
                data = p.read_bytes()
            except OSError as exc:
                _add_unread(lib, str(p), f"{p}: cannot be read ({exc.strerror or exc})")
                continue
            _add_bytes(lib, str(p), data)
    return lib


# ---------- the index a page reads, and the archive a receipt can point into ----------

def _lf_bytes(p: Path) -> bytes:
    try:
        return p.read_bytes().replace(b"\r\n", b"\n")
    except OSError as exc:
        raise ModuleError(f"{p}: cannot be read ({exc.strerror or exc})") from None


def _write_atomic(dest: Path, data: bytes) -> None:
    """Write through a temporary file in the same folder and os.replace it into place: an interrupted write leaves
    the old file or nothing, never a truncated one. The temporary file is created 0666 so the umask narrows it as it
    narrows a plain write (tempfile.mkstemp forces 0600, which os.replace would keep: an owner-only index)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    for _ in range(100):
        tmp = str(dest.parent / f".{dest.name}.{secrets.token_hex(6)}.tmp")
        try:
            fd = os.open(tmp, flags, 0o666)
            break
        except FileExistsError:
            continue
    else:
        raise FileExistsError(f"{dest}: no free temporary name beside it")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _hash_of_file(p: Path) -> Optional[str]:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def build_index(library_dir: Path = LIBRARY_DIR) -> dict:
    """{api, files: [{path, sha256}]}: every .glsl under the library (not the bench chunks), POSIX paths relative to
    it, in load order. The hash is of the LF text, so a CRLF checkout (core.autocrlf) does not look stale."""
    library_dir = Path(library_dir)
    files = [] if not library_dir.exists() else [
        {"path": p.relative_to(library_dir).as_posix(), "sha256": hashlib.sha256(_lf_bytes(p)).hexdigest()}
        for p in _module_files(library_dir)]
    return {"api": API, "files": files}


def index_is_current(library_dir: Path = LIBRARY_DIR, index_path: Optional[Path] = None) -> bool:
    library_dir = Path(library_dir)
    index_path = Path(index_path) if index_path else library_dir / "index.json"
    try:
        return json.loads(index_path.read_text(encoding="utf-8")) == build_index(library_dir)
    except (OSError, ValueError):
        return False


def write_index(library_dir: Path = LIBRARY_DIR, index_path: Optional[Path] = None,
                archive_dir: Path = ARCHIVE_DIR) -> dict:
    """Write index.json and keep a copy of each module at <archive>/<name>/<sha256>.glsl. The archive only grows: a
    good copy is never rewritten, so a receipt naming a hash can always find the bytes that ran. Every write is
    atomic, and a copy whose bytes do not hash to its name (an interrupted write before writes were atomic) is
    rewritten rather than trusted for ever."""
    library_dir = Path(library_dir)
    index_path = Path(index_path) if index_path else library_dir / "index.json"
    index = build_index(library_dir)
    archived = []
    for row in index["files"]:
        p = library_dir / row["path"]
        data = _lf_bytes(p)
        try:
            name = parse_module(data.decode("utf-8"), str(p)).name
        except (ModuleError, UnicodeDecodeError):
            name = p.stem
        if not NAME_RE.fullmatch(name):   # a header name never steers a write outside (parse_module refuses it too)
            name = p.stem
        dest = Path(archive_dir) / name / f"{row['sha256']}.glsl"
        if _hash_of_file(dest) != row["sha256"]:
            _write_atomic(dest, data)
            archived.append(dest.as_posix())
    _write_atomic(index_path, (json.dumps(index, indent=2) + "\n").encode("utf-8"))
    return {"index": index, "archived": archived}


def _rel(path: str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def manifest_for(m: Module, library: Optional[Library] = None) -> dict:
    """The module as an arsenal.module/v0 manifest with a `shader` block (validated by arsenal/registry.py)."""
    h = m.header
    params = []
    for p in h.get("params") or []:
        row = {"name": p.get("name"), "unit": p.get("unit"), "range": p.get("range")}
        for opt in ("default", "uniform", "label", "step"):
            if opt in p:
                row[opt] = p[opt]
        params.append(row)
    return {
        "id": "glsl." + m.name,
        "version": str(h.get("version") or "0.1.0"),
        "protocol": MODULE_PROTOCOL,
        "engine": "browser",
        "inputs": [{"port": k, "type": "vfx." + str(t)} for k, t in (h.get("in") or {}).items()],
        "outputs": [{"port": k, "type": "vfx." + str(t)} for k, t in (h.get("out") or {}).items()],
        "params": params,
        "shader": {
            "api": API,
            "file": _rel(m.path),
            "kind": m.kind,
            "cat": m.cat,
            "provides": list(m.provides),
            "needs": library.deps(m.name) if library else list(h.get("needs") or []),
            "cost": h.get("cost"),
            "credits": list(h.get("credits") or []),
            "note": h.get("note"),
        },
        "licence": h.get("license") or h.get("licence") or "unstated",
        "degradation": {"on_failure": "bypass"},
        "receipts": [],
    }


_UNIFORM_RE = re.compile(r"^[ \t]*uniform\s+\w+\s+([A-Za-z_]\w*)", re.M)


def lint(m: Module, library_module: bool = True, library: Optional[Library] = None) -> List[str]:
    """The shader-craft floors a text-only seat can check (skill floors 1 and 6). Legacy bench chunks are exempt from
    those: they are fragments of the bench's own template and read its uniforms by design.

    Unresolved calls are checked against `library` when the module is in it (a call is fine if some module provides
    it or a hook in the module's reach declares it), and against the module alone otherwise.

    A bench HELPER chunk (library_module False) is held to the bench's helper order instead (S5 review, 2026-10-13).
    The bench ships the shared composer's GLSL only when it is byte-identical to its legacy writer's, and the two order
    helpers by different rules: legacy sorts by `order || 50` (0 reads as 50), breaks a tie by FILE name and never
    moves a helper for a call; the resolver reads 0 as 0, breaks a tie by name and puts a callee first. Any chunk on
    which they disagree would quietly pin the bench to legacy, so lint refuses it: order 0, two helpers of one order in
    one folder whose names and file names sort apart (one name a prefix of the other), and a helper that calls, uses or
    needs a chunk of its folder that the legacy writer emits after it, or never (it emits helpers only). A chunk that
    passes is in the same place in both orders."""
    if not library_module:
        if m.kind != "helper":
            return []          # only helpers are ordered: a snippet's order is read by neither writer
        bench = []
        order = m.header.get("order")
        if order == 0 and not isinstance(order, bool):
            bench.append(f"{m.name}: a bench helper at order 0; the bench's legacy writer reads it as 50 (order || 50) "
                         "and the shared composer as 0, so they would emit the helpers in different orders and the "
                         "bench would fall back to legacy (give it 1 or more)")
        if library is None or library.modules.get(m.name) is not m:
            return bench
        here = Path(m.path).parent
        mine = Path(m.path).name

        def legacy_key(b: Module):
            return (b.header.get("order") or DEFAULT_ORDER, Path(b.path).name)

        for name in sorted(library.modules):
            b = library.modules[name]
            if b is m or b.kind != "helper" or Path(b.path).parent != here or b.order != m.order or m.order == 0:
                continue
            theirs = Path(b.path).name
            if (theirs < mine) != (b.name < m.name) and b.name < m.name:   # said once, on the one named second
                bench.append(f"{m.name}: shares order {m.order:g} with {b.name}, and their file names sort the other way "
                             f"from their names (file {mine} before {theirs}, name {b.name} before {m.name}, as when "
                             "one name is a prefix of the other): the bench's legacy writer breaks the tie by file "
                             "name and the shared composer by name, so they would differ (rename one, or give them "
                             "different orders)")
        try:
            deps = library.deps(m.name)
        except ModuleError:
            deps = []          # a missing need is named by the resolver, below
        for d in deps:
            b = library.modules[d]
            if Path(b.path).parent != here:
                continue
            what = ", ".join([f"calls {c}()" for c in m.calls if library.providers.get(c) == d] +
                             [f"uses {u}" for u in m.uses if library.data.get(u) == d]) or f"needs {d}"
            if b.kind != "helper":
                bench.append(f"{m.name}: {what} from {d} ({Path(b.path).name}), a '{b.kind}' chunk; the bench's legacy "
                             "writer emits helper chunks only, so the shared composer would add it and the two would "
                             "differ (make it a helper)")
            elif legacy_key(b) > legacy_key(m):
                bench.append(f"{m.name}: {what} from {d} ({Path(b.path).name}), which the bench's legacy writer emits "
                             f"after it (order {legacy_key(b)[0]:g} against {legacy_key(m)[0]:g}); GLSL needs it "
                             f"declared first and the shared composer would move it, so the two would differ (give "
                             f"{m.name} a higher order than {d})")
        return bench
    problems = []
    h, code = m.header, strip_comments(m.body)
    if not (h.get("license") or h.get("licence")):
        problems.append(f"{m.name}: a library module states its license (house code is Apache-2.0)")
    if not isinstance(h.get("credits"), list):
        problems.append(f"{m.name}: a library module lists its credits (who taught the technique; [] if none)")
    if "#version" in code:
        problems.append(f"{m.name}: a module is a fragment -- no #version line (the host template owns line 1)")
    if re.search(r"\bprecision\s+\w+", code) or re.search(r"\b(mediump|lowp)\b", code):
        problems.append(f"{m.name}: no precision statement or qualifier (the host template declares highp; "
                        "mediump bands our hashes)")
    declared = {p.get("uniform") for p in h.get("params") or [] if p.get("uniform")}
    for u in _UNIFORM_RE.findall(code):
        if u not in declared:
            problems.append(f"{m.name}: uniform {u} is not declared as a param (a param names its uniform, so the "
                            "UI and every host can bind it)")
    t = h.get("targets")
    if t is not None and not (isinstance(t, dict) and (t.get("needs") is None or (
            isinstance(t["needs"], list) and all(isinstance(n, str) for n in t["needs"])))):
        problems.append(f"{m.name}: targets has the wrong shape (want {{\"glsl\": \"300es\", \"needs\": [...]}} with "
                        "string needs); the composer reads a wrong shape as no needs, so no target would refuse it")
    for need in m.target_needs:
        if need not in KNOWN_NEEDS:
            problems.append(f"{m.name}: targets.needs '{need}' is not one of {', '.join(KNOWN_NEEDS)} (an unknown "
                            "need passes every target, so a misspelt one would never refuse anything)")
    if isinstance(t, dict) and "glsl" in t and t["glsl"] not in GLSL_VERSIONS:
        problems.append(f"{m.name}: targets.glsl {json.dumps(t['glsl'])} is not \"100\" or \"300es\" (the composer "
                        "reads anything but \"100\" as GLSL ES 3.00, so webgl1 would refuse the module)")
    if m.glsl == "100":
        problems += _es1_claim_problems(m, code)
    if library is not None and library.modules.get(m.name) is m:
        try:
            missing = library.unresolved(m.name)
        except ModuleError as exc:
            problems.append(f"{m.name}: does not resolve ({exc})")
            missing = []
        for fn in missing:
            problems.append(f"{m.name}: calls {fn}(), which no module provides and no hook declares "
                            "(declare it in \"hooks\" if the host defines it; a typo cannot pass as a hook)")
    else:   # alone, lint cannot know what the other modules provide, so it says only what it checked
        for fn in (c for c in m.calls if c not in m.hook_names):
            problems.append(f"{m.name}: calls {fn}(), which is not defined in this module or declared in its hooks "
                            "(lint it with its library to check what the other modules provide)")
    return problems


def _es1_claim_problems(m: Module, code: str) -> List[str]:
    """What contradicts a module's claim to the GLSL ES 1.00 subset (targets.glsl "100"): the composer trusts the
    claim for webgl1 and three-r186-glsl1, so lint checks the common ES 3.00-only features against it."""
    claim = f"{m.name}: declares targets.glsl \"100\" but"
    calls = sorted(set(CALL_RE.findall(code)))
    out = [f"{claim} calls {c}(), which GLSL ES 1.00 does not have" for c in calls if c in ES3_ONLY_FUNCTIONS]
    out += [f"{claim} uses {w}, which GLSL ES 1.00 does not have"
            for w in sorted(set(IDENT_RE.findall(code)) & ES3_ONLY_WORDS)]
    out += [f"{claim} uses the operator {op}, which GLSL ES 1.00 reserves"
            for op in sorted(set(ES3_ONLY_OPERATOR_RE.findall(code)))]
    if ARRAY_CONSTRUCTOR_RE.search(code):
        out.append(f"{claim} uses an array constructor, which GLSL ES 1.00 does not have")
    if "derivatives" not in m.target_needs:
        out += [f"{claim} calls {c}() without declaring \"derivatives\" in targets.needs (GLSL ES 1.00 has it only "
                "through OES_standard_derivatives)" for c in calls if c in DERIVATIVES]
    return out


# ---------- the door: py -m arsenal shader lib ... ----------

def _register(sub) -> None:
    p = sub.add_parser("lib", help="the house GLSL module library: list, show, compose, lint, manifests, index")
    p.add_argument("action", choices=["list", "show", "compose", "lint", "manifests", "index"])
    p.add_argument("names", nargs="*")
    p.add_argument("--write", action="store_true", help="manifests: write arsenal/modules/glsl.<name>.json; "
                   "index: write arsenal/web/glsl/index.json and archive each module under state/arsenal/glsl-archive")
    p.add_argument("--dir", action="append", help="a module directory (default: arsenal/web/glsl + design/vfx-chunks)")
    p.add_argument("--target", choices=sorted(TARGET_LACKS), help="compose: refuse modules this host cannot run")
    p.set_defaults(fn=_cmd)


def _cmd(ns) -> int:
    from .cli import _print
    if ns.action == "index":
        current = index_is_current()
        report = write_index() if ns.write else {"index": build_index(), "archived": []}
        row = {"index": report["index"], "current": current, "written": bool(ns.write), "archived": report["archived"]}
        _print(row, ns.json, lambda r: (
            f"{len(r['index']['files'])} library files; index.json " +
            ("written" if r["written"] else "is current" if r["current"] else
             "is STALE: run py -m arsenal shader lib index --write") +
            (f"; {len(r['archived'])} new archive copies" if r["archived"] else "")))
        return 0 if (current or ns.write) else 1
    lib = load_library(ns.dir)
    target = getattr(ns, "target", None)
    if ns.action == "list":
        rows = [{"name": n, "cat": lib.modules[n].cat, "kind": lib.modules[n].kind, "file": _rel(lib.modules[n].path),
                 "provides": list(lib.modules[n].provides)} for n in lib.names()]
        def human(rs):
            out, cat = [f"{len(rs)} modules"], None
            for r in sorted(rs, key=lambda r: (r["cat"], r["name"])):
                if r["cat"] != cat:
                    cat = r["cat"]
                    out.append(f"[{cat}]")
                out.append(f"  {r['name']:<28} {r['kind']:<9} {', '.join(r['provides'])[:60]}")
            return "\n".join(out)
        _print(rows, ns.json, human)
        return 0
    if ns.action == "show":
        rows = [dict(manifest_for(lib.get(n), lib), resolved=lib.resolve([n])) for n in ns.names]
        _print(rows, ns.json, lambda rs: "\n\n".join(json.dumps(r, indent=1) for r in rs))
        return 0
    if ns.action == "compose":
        sys_out = (lib.compose(ns.names, target=target) if all(lib.get(n).composable for n in ns.names)
                   else lib.prelude(ns.names, target=target))
        _print({"glsl": sys_out}, ns.json, lambda r: r["glsl"].rstrip("\n"))
        return 0
    if ns.action == "lint":
        lib_root = LIBRARY_DIR.resolve()
        problems = []
        for n in lib.names():
            m = lib.modules[n]
            in_library = lib_root in Path(m.path).resolve().parents
            problems += lint(m, library_module=in_library, library=lib)
        _print({"problems": problems}, ns.json,
               lambda r: "\n".join(r["problems"]) or f"{len(lib.names())} modules, no floor broken")
        return 1 if problems else 0
    if ns.action == "manifests":
        out = [manifest_for(lib.get(n), lib) for n in (ns.names or lib.names())]
        if ns.write:
            target = ROOT / "arsenal" / "modules"
            for m in out:
                (target / f"{m['id']}.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8", newline="\n")
        _print(out, ns.json, lambda ms: f"{len(ms)} manifests" + (" written to arsenal/modules/" if ns.write else ""))
        return 0
    return 2


def _hook() -> None:
    from . import cli
    cli.VERBS["lib"] = _register


_hook()
