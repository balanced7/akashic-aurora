"""The house GLSL module core: one format, one resolver, one composer, so a change to a module reaches every surface.

    py -m arsenal shader lib list                  # every module the house has, by category
    py -m arsenal shader lib show <name>           # header, what it provides, what it needs (resolved)
    py -m arsenal shader lib compose <name>...     # the dependency-ordered GLSL a host pastes under its preamble
    py -m arsenal shader lib lint                  # the shader-craft floors a module can be checked against blind
    py -m arsenal shader lib manifests [--write]   # each module as an arsenal.module/v0 manifest (the one registry)

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
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from arsenal import GLSL_MODULE_API, MODULE_PROTOCOL

API = GLSL_MODULE_API
ROOT = Path(__file__).resolve().parents[2]
LIBRARY_DIR = ROOT / "arsenal" / "web" / "glsl"           # the house library (Apache-2.0, our own code)
LEGACY_DIRS = (ROOT / "design" / "vfx-chunks",)            # the bench's chunks, read in place
DEFAULT_DIRS = (LIBRARY_DIR,) + LEGACY_DIRS

FUNCTION_KINDS = frozenset({"helper", "function", "recipe", "library", "const"})
DEFAULT_ORDER = 50

# Kept in lockstep with arsenal/web/glsl/modlib.js (the parity pin compares their output byte for byte).
COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
DEFINITION_RE = re.compile(
    r"^[ \t]*(?:(?:highp|mediump|lowp|const)\s+)*([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)\s*\{",
    re.M)
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
BLANK_RUN_RE = re.compile(r"\n{3,}")
NOT_A_TYPE = frozenset({"return", "else", "if", "for", "while", "do", "switch", "case"})

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
    body = body.replace("\r\n", "\n").lstrip("\n").rstrip()
    return BLANK_RUN_RE.sub("\n\n", body)


@dataclass(frozen=True)
class Module:
    name: str
    path: str
    header: dict
    body: str
    provides: Tuple[str, ...]
    calls: Tuple[str, ...]

    @property
    def kind(self) -> str:
        return str(self.header.get("kind"))

    @property
    def cat(self) -> str:
        return str(self.header.get("cat") or "misc")

    @property
    def order(self) -> float:
        o = self.header.get("order", DEFAULT_ORDER)
        return o if isinstance(o, (int, float)) else DEFAULT_ORDER

    @property
    def composable(self) -> bool:
        return self.kind in FUNCTION_KINDS


def parse_module(text: str, path: str = "<text>") -> Module:
    """A module from its source text. ModuleError (naming the file) when the header is missing, not JSON, or unnamed."""
    lines = text.replace("\r\n", "\n").split("\n")
    head = []
    while len(head) < len(lines) and lines[len(head)].lstrip().startswith("//!"):
        head.append(lines[len(head)])
    if not head:
        raise ModuleError(f"{path}: no //! header on the first line")
    try:
        header = json.loads(" ".join(line.lstrip()[3:] for line in head))
    except json.JSONDecodeError as exc:
        raise ModuleError(f"{path}: the //! header is not JSON ({exc.msg} at column {exc.colno})") from None
    if not isinstance(header, dict) or not isinstance(header.get("name"), str) or not header.get("kind"):
        raise ModuleError(f"{path}: the //! header needs a name and a kind")
    body = "\n".join(lines[len(head):])
    code = strip_comments(body)
    provides = sorted({m.group(2) for m in DEFINITION_RE.finditer(code) if m.group(1) not in NOT_A_TYPE})
    calls = sorted({c for c in CALL_RE.findall(code) if c not in BUILTINS} - set(provides))
    return Module(header["name"], str(path), header, body, tuple(provides), tuple(calls))


@dataclass
class Library:
    modules: Dict[str, Module] = field(default_factory=dict)
    providers: Dict[str, str] = field(default_factory=dict)

    def add(self, m: Module) -> None:
        if m.name in self.modules:
            raise ModuleError(f"two modules are named {m.name!r}: {self.modules[m.name].path} and {m.path}")
        for fn in m.provides:
            if fn in self.providers:
                raise ModuleError(f"function {fn!r} is defined by two modules: {self.providers[fn]} "
                                  f"({self.modules[self.providers[fn]].path}) and {m.name} ({m.path})")
        self.modules[m.name] = m
        for fn in m.provides:
            self.providers[fn] = m.name

    def names(self) -> List[str]:
        return sorted(self.modules)

    def get(self, name: str) -> Module:
        if name not in self.modules:
            raise ModuleError(f"no module named {name!r}")
        return self.modules[name]

    def _key(self, name: str):
        return (self.modules[name].order, name)

    def deps(self, name: str) -> List[str]:
        """Direct dependencies: modules defining a function this one calls, plus its `needs` (module or function names)."""
        m = self.get(name)
        out = {self.providers[c] for c in m.calls if c in self.providers and self.providers[c] != name}
        for need in m.header.get("needs") or []:
            if need in self.modules:
                out.add(need)
            elif need in self.providers:
                out.add(self.providers[need])
            else:
                raise ModuleError(f"module {name!r} needs {need!r}, which no module is named or defines")
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

    def _emit(self, order: Sequence[str]) -> str:
        parts = [f"// {API} compose: " + ", ".join(order)]
        for n in order:
            m = self.modules[n]
            parts.append(f"// --- {n} ({m.cat}) ---\n" + normalize_body(m.body))
        return "\n\n".join(parts) + "\n"

    def compose(self, names: Iterable[str]) -> str:
        """The GLSL for these modules and everything they need, in dependency order. Snippets are refused."""
        order = self.resolve(names)
        snippets = [n for n in order if not self.modules[n].composable]
        if snippets:
            raise ModuleError("cannot compose a snippet (" + ", ".join(
                f"{n}: kind {self.modules[n].kind!r}" for n in snippets) +
                "); a chain compiler places snippets -- use prelude() for the helpers they need")
        return self._emit(order)

    def prelude(self, names: Iterable[str]) -> str:
        """The composable modules these names need (snippets themselves left out): what a chain compiler pastes first."""
        return self._emit([n for n in self.resolve(names) if self.modules[n].composable])


def load_library(dirs: Optional[Iterable] = None) -> Library:
    lib = Library()
    for d in (DEFAULT_DIRS if dirs is None else dirs):
        d = Path(d)
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.glsl")):
            lib.add(parse_module(p.read_text(encoding="utf-8"), str(p)))
    return lib


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


def lint(m: Module, library_module: bool = True) -> List[str]:
    """The shader-craft floors a text-only seat can check (skill floors 1 and 6). Legacy bench chunks are exempt:
    they are fragments of the bench's own template and read its uniforms by design."""
    if not library_module:
        return []
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
    return problems


# ---------- the door: py -m arsenal shader lib ... ----------

def _register(sub) -> None:
    p = sub.add_parser("lib", help="the house GLSL module library: list, show, compose, lint, manifests")
    p.add_argument("action", choices=["list", "show", "compose", "lint", "manifests"])
    p.add_argument("names", nargs="*")
    p.add_argument("--write", action="store_true", help="manifests: write arsenal/modules/glsl.<name>.json")
    p.add_argument("--dir", action="append", help="a module directory (default: arsenal/web/glsl + design/vfx-chunks)")
    p.set_defaults(fn=_cmd)


def _cmd(ns) -> int:
    from .cli import _print
    lib = load_library(ns.dir)
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
        sys_out = lib.compose(ns.names) if all(lib.get(n).composable for n in ns.names) else lib.prelude(ns.names)
        _print({"glsl": sys_out}, ns.json, lambda r: r["glsl"].rstrip("\n"))
        return 0
    if ns.action == "lint":
        lib_root = LIBRARY_DIR.resolve()
        problems = []
        for n in lib.names():
            m = lib.modules[n]
            in_library = lib_root in Path(m.path).resolve().parents
            problems += lint(m, library_module=in_library)
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
