"""A GLSL ES reader for the shader school: tokens with line numbers, then the shapes a dissector needs -- functions (with
the calls inside them), structs, global consts, #defines, uniforms, loops with their literal bounds, a call graph, and a
reachability walk from the entry points so dead code is flagged.

    from arsenal.shaders import glsl
    common = glsl.Program(common_src, file="common.glsl")
    image = glsl.Program(image_src, file="image.glsl", base=common)    # Common is prepended, so its #defines reach here
    unit = glsl.Unit([common, image])                                   # what the compiler sees for one pass
    unit.reachable()                                                    # names reachable from mainImage/mainCubemap/...

WHY A READER AND NOT A REGEX OVER THE TEXT. The corpus is ~335 shaders and ~165k lines written by people who golf, macro
and #if their code. A regex over raw text cannot tell a call from a word in a comment, a #define from code, the live
branch of an #if from the dead one, or a loop's body from the statement after it; every detector downstream
(arsenal/shaders/dissect.py) leans on those distinctions, so they are made once, here, and pinned by
tests/test_shader_dissect.py.

WHAT IT IS NOT. It is not a compiler. There is no type checking and no overload resolution (overloads share one name in
the call graph); macros are not expanded into the code (a function-like macro is a node in the call graph whose body is
read like a function's, and its own parameters are not identifiers of it: `#define WAVE(t) sin(t)` uses whatever it is
called with, never a macro named t; a function's parameter likewise shadows anything outside named like it, see
Fn.param_names; and a macro that calls a parameter calls what its caller passes there: with `#define APPLY(f, x) f(x)`,
`APPLY(bend, u.x)` is a call of bend by the caller, see Unit.calls); an #if it cannot evaluate keeps its first branch
(and says so in Program.unsure_ifs). GLSL block comments do not nest (GLSL ES 3.00 section 3.4: a comment ends at the
first */), and this reader follows the spec rather than guessing -- `/* a /* b */ code` leaves `code` as code, exactly
as the compiler would.

THE FLAT TEXT CONVENTION. Detectors match shapes of math with regular expressions over a function's *flat text*: its
active, comment-free tokens joined by single spaces (`t += d * 0.5`, `length ( p ) - r`). One space between every token
makes a pattern exact without whitespace games, and Fn.line_at() maps a match back to a source line.
"""
from __future__ import annotations

import bisect
import math
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

# ---------- tokens ----------

COMMENT, PP, STRING, NUMBER, IDENT, OP, OTHER = "comment", "pp", "string", "number", "ident", "op", "other"

# Hex first (else "0" lexes alone), then the float forms (1.5, 2., .5, each with an optional exponent, and 1e-3), then
# plain integers. Suffixes: u/U on integers, f/F (and h/H half) on floats -- GLSL ES ignores f, but golfers write it.
NUMBER_PATTERN = (r"(?:0[xX][0-9a-fA-F]+[uU]?"
                  r"|(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?[fFhH]?"
                  r"|\d+[eE][+-]?\d+[fFhH]?"
                  r"|\d+[uU]?)")

_TOKEN_RE = re.compile(
    # A preprocessor directive: '#' first on its line, to the end of the LOGICAL line (backslash-newline splices it on;
    # a block comment inside it may run across lines, as in C; a trailing // comment belongs to it).
    r"(?P<pp>^[ \t]*\#(?:[^\n\\/]+|\\\n|\\|/\*.*?(?:\*/|\Z)|/(?![/*]))*(?://(?:[^\n\\]|\\.)*)?)"
    r"|(?P<ws>[ \t\f\v\r]+|\n)"
    # Comments. A // comment ending in a backslash continues onto the next line (splicing happens before comments).
    r"|(?P<comment>//(?:[^\n\\]|\\.)*|/\*.*?(?:\*/|\Z))"
    r'|(?P<string>"(?:[^"\\\n]|\\.)*"?)'
    r"|(?P<number>" + NUMBER_PATTERN + r")"
    r"|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<op><<=|>>=|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\||\^\^|[-+*/%&|^]=|[-+*/%&|^!~<>=?:;,.(){}\[\]])"
    r"|(?P<other>.)",
    re.M | re.S)


class Token:
    """One lexeme: its kind (comment, pp, string, number, ident, op, other), its exact text, and the line it starts on."""
    __slots__ = ("kind", "text", "line")

    def __init__(self, kind: str, text: str, line: int):
        self.kind, self.text, self.line = kind, text, line

    def __repr__(self) -> str:
        return f"Token({self.kind}, {self.text!r}, line {self.line})"


def normalize_newlines(src: str) -> str:
    return (src or "").replace("\r\n", "\n").replace("\r", "\n")


def lex(src: str) -> List[Token]:
    """Every lexeme of a GLSL source with its 1-based line. Whitespace is dropped; comments and directives are kept."""
    out: List[Token] = []
    line = 1
    for m in _TOKEN_RE.finditer(normalize_newlines(src)):
        kind = m.lastgroup
        text = m.group()
        if kind == "ws":
            if text == "\n":
                line += 1
            continue
        if kind == PP:
            text = text.lstrip(" \t")
        out.append(Token(kind, text, line))
        if kind in (COMMENT, PP, STRING):
            line += text.count("\n")
    return out


def parse_number(text: str):
    """A GLSL literal's value: int for integer literals (hex included), float for anything with a '.' or exponent."""
    if text[:2] in ("0x", "0X"):
        return int(text.rstrip("uU"), 16)
    t = text.rstrip("uUfFhHlL")
    if any(c in t for c in ".eE"):
        return float(t)
    return int(t)


# ---------- the language's own names ----------

TYPES = frozenset("""
void bool int uint float double vec2 vec3 vec4 dvec2 dvec3 dvec4 bvec2 bvec3 bvec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4
mat2 mat3 mat4 mat2x2 mat2x3 mat2x4 mat3x2 mat3x3 mat3x4 mat4x2 mat4x3 mat4x4
sampler2D sampler3D samplerCube sampler2DShadow samplerCubeShadow sampler2DArray sampler2DArrayShadow
isampler2D isampler3D isamplerCube isampler2DArray usampler2D usampler3D usamplerCube usampler2DArray
""".split())
SCALAR_TYPES = frozenset({"float", "int", "uint", "bool"})
QUALIFIERS = frozenset("""
const in out inout uniform highp mediump lowp precise invariant flat smooth centroid noperspective layout
readonly writeonly coherent volatile restrict shared attribute varying
""".split())
KEYWORDS = frozenset("""
if else for while do switch case default break continue return discard struct precision true false
""".split())
BUILTIN_FUNCTIONS = frozenset("""
radians degrees sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh pow exp log exp2 log2 sqrt inversesqrt
abs sign floor trunc round roundEven ceil fract mod modf min max clamp mix step smoothstep isnan isinf
floatBitsToInt floatBitsToUint intBitsToFloat uintBitsToFloat packSnorm2x16 unpackSnorm2x16 packUnorm2x16
unpackUnorm2x16 packHalf2x16 unpackHalf2x16 length distance dot cross normalize faceforward reflect refract
matrixCompMult outerProduct transpose determinant inverse lessThan lessThanEqual greaterThan greaterThanEqual equal
notEqual any all not textureSize texture textureProj textureLod textureOffset texelFetch texelFetchOffset
textureProjOffset textureLodOffset textureProjLod textureProjLodOffset textureGrad textureGradOffset textureProjGrad
textureProjGradOffset texture2D texture2DLod textureCube textureCubeLod texture3D dFdx dFdy fwidth
bitfieldExtract bitfieldInsert bitfieldReverse bitCount findLSB findMSB uaddCarry usubBorrow umulExtended imulExtended
""".split())
ENTRY_POINTS = ("mainImage", "mainCubemap", "mainSound", "mainVR", "main")
TOPLEVEL = "(top level)"         # the pseudo-function holding everything outside functions (see Program._toplevel)
MAX_EXPANSION_DEPTH = 3          # a top-level macro that expands into another is followed this far, no further
# Shadertoy uniforms that are never negative: `min(iFrame, 0)` is IQ's way to stop a compiler unrolling a loop, and it
# is 0 -- the reader knows that much about them and nothing else.
NONNEGATIVE_UNIFORMS = frozenset({"iFrame", "iTime", "iGlobalTime", "iTimeDelta", "iSampleRate", "iFrameRate"})
# What Shadertoy's compiler defines before the first line of every pass.
PREDEFINED = {"GL_ES": "1", "__VERSION__": "300", "HW_PERFORMANCE": "1"}
ASSIGN_OPS = frozenset({"=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "|=", "^="})
UNKNOWN_BOUND_CAP = 10_000_000   # a computed trip count above this is treated as unbounded
GEOMETRIC_CAP = 4096             # a v *= k loop still running after this many steps is treated as unbounded


# ---------- constant expressions ----------

class _Unknown(Exception):
    pass


class _Signed:
    """A value known only by its sign: a uniform that is >= 0 (iFrame, iTime) or its negation (<= 0)."""
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


NONNEG, NONPOS = _Signed("NONNEG"), _Signed("NONPOS")

_BINARY = {"||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "<": 7, ">": 7, "<=": 7, ">=": 7,
           "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10}


def _num(v):
    if v is None or isinstance(v, _Signed):
        raise _Unknown
    return v


def _apply(op: str, a, b):
    a, b = _num(a), _num(b)
    if op == "+": return a + b
    if op == "-": return a - b
    if op == "*": return a * b
    if op == "/":
        if isinstance(a, int) and isinstance(b, int):
            return int(a / b)           # GLSL integer division truncates toward zero
        return a / b
    if op == "%": return math.fmod(a, b) if isinstance(a, float) or isinstance(b, float) else int(math.fmod(a, b))
    if op == "<": return int(a < b)
    if op == ">": return int(a > b)
    if op == "<=": return int(a <= b)
    if op == ">=": return int(a >= b)
    if op == "==": return int(a == b)
    if op == "!=": return int(a != b)
    if op == "&&": return int(bool(a) and bool(b))
    if op == "||": return int(bool(a) or bool(b))
    if op == "&": return int(a) & int(b)
    if op == "|": return int(a) | int(b)
    if op == "^": return int(a) ^ int(b)
    if op == "<<": return int(a) << int(b)
    if op == ">>": return int(a) >> int(b)
    raise _Unknown


def _call(name: str, args: list):
    if name in ("float", "double"):
        return args[0] if args and isinstance(args[0], _Signed) else float(_num(args[0]))
    if name in ("int", "uint"):
        return args[0] if args and isinstance(args[0], _Signed) else int(_num(args[0]))
    if name == "bool":
        return int(bool(_num(args[0])))
    if name in ("min", "max") and len(args) == 2:
        a, b = args
        signed = a if isinstance(a, _Signed) else b if isinstance(b, _Signed) else None
        if signed is not None:
            other = b if signed is a else a
            if isinstance(other, _Signed) or other is None:
                raise _Unknown
            # the anti-unroll idioms: min(iFrame, 0) == 0 and max(0, -iFrame) == 0
            if name == "min" and signed is NONNEG and other <= 0:
                return other
            if name == "max" and signed is NONPOS and other >= 0:
                return other
            raise _Unknown
        return min(_num(a), _num(b)) if name == "min" else max(_num(a), _num(b))
    vals = [_num(a) for a in args]
    one = {"abs": abs, "sqrt": math.sqrt, "floor": math.floor, "ceil": math.ceil, "exp": math.exp, "exp2": lambda x: 2.0 ** x,
           "log": math.log, "log2": math.log2, "sin": math.sin, "cos": math.cos, "tan": math.tan,
           "radians": math.radians, "degrees": math.degrees, "fract": lambda x: x - math.floor(x),
           "sign": lambda x: (x > 0) - (x < 0), "round": round, "trunc": math.trunc, "inversesqrt": lambda x: 1 / math.sqrt(x)}
    if name in one and len(vals) == 1:
        v = one[name](vals[0])
        return float(v) if name in ("floor", "ceil", "round", "trunc", "sign") and isinstance(vals[0], float) else v
    if name == "pow" and len(vals) == 2:
        return float(vals[0]) ** vals[1]
    if name == "mod" and len(vals) == 2:
        return vals[0] - vals[1] * math.floor(vals[0] / vals[1])
    if name == "clamp" and len(vals) == 3:
        return min(max(vals[0], vals[1]), vals[2])
    if name == "atan" and len(vals) in (1, 2):
        return math.atan(vals[0]) if len(vals) == 1 else math.atan2(vals[0], vals[1])
    raise _Unknown


class Evaluator:
    """A small integer/float constant folder over tokens: literals, + - * / % comparisons logic bit-ops ?:, parentheses,
    the scalar built-ins and casts, and names through `lookup(name) -> value | None` (None means unknown)."""

    def __init__(self, lookup: Callable[[str], object]):
        self.lookup = lookup
        self.t: Sequence[Token] = ()
        self.i = 0

    def evaluate(self, toks: Sequence[Token]):
        self.t, self.i = [t for t in toks if t.kind != COMMENT], 0
        if not self.t:
            return None
        try:
            v = self._ternary()
            if self.i != len(self.t) or isinstance(v, _Signed):
                return None
            return v
        except (_Unknown, ZeroDivisionError, OverflowError, ValueError, IndexError, TypeError, RecursionError):
            return None

    def _peek(self) -> Optional[str]:
        return self.t[self.i].text if self.i < len(self.t) else None

    def _expect(self, text: str) -> None:
        if self._peek() != text:
            raise _Unknown
        self.i += 1

    def _ternary(self):
        c = self._binary(1)
        if self._peek() == "?":
            self.i += 1
            a = self._ternary()
            self._expect(":")
            b = self._ternary()
            return a if _num(c) else b
        return c

    def _binary(self, min_prec: int):
        lhs = self._unary()
        while True:
            op = self._peek()
            prec = _BINARY.get(op)
            if prec is None or prec < min_prec:
                return lhs
            self.i += 1
            rhs = self._binary(prec + 1)
            lhs = _apply(op, lhs, rhs)

    def _unary(self):
        op = self._peek()
        if op in ("-", "+", "!", "~"):
            self.i += 1
            v = self._unary()
            if isinstance(v, _Signed) and op in ("-", "+"):
                return v if op == "+" else (NONPOS if v is NONNEG else NONNEG)
            v = _num(v)
            return {"-": -v, "+": v, "!": int(not v), "~": ~int(v)}[op]
        return self._primary()

    def _primary(self):
        if self.i >= len(self.t):
            raise _Unknown
        tok = self.t[self.i]
        self.i += 1
        if tok.text == "(":
            v = self._ternary()
            self._expect(")")
            return v
        if tok.kind == NUMBER:
            return parse_number(tok.text)
        if tok.kind == IDENT:
            if tok.text in ("true", "false"):
                return int(tok.text == "true")
            if self._peek() == "(":
                self.i += 1
                args = []
                if self._peek() != ")":
                    while True:
                        args.append(self._ternary())
                        if self._peek() == ",":
                            self.i += 1
                            continue
                        break
                self._expect(")")
                return _call(tok.text, args)
            v = self.lookup(tok.text)
            if v is None:
                raise _Unknown
            return v
        raise _Unknown


# ---------- directives ----------

_SPLICE_RE = re.compile(r"\\\n")
COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?(?:\*/|\Z)", re.S)
_DIRECTIVE_RE = re.compile(r"\s*#\s*([A-Za-z_]\w*)?(.*)", re.S)
_DEFINE_RE = re.compile(r"([A-Za-z_]\w*)(\([^)]*\))?(.*)", re.S)


@dataclass(eq=False)
class Directive:
    """One preprocessor line. For #define: name, params (None for an object-like macro) and body, comments removed and
    continuation lines joined. `active` says whether it sat in a live #if branch."""
    kind: str
    line: int
    end_line: int
    rest: str
    name: str = ""
    params: Optional[Tuple[str, ...]] = None
    body: str = ""
    active: bool = True
    _tokens: Optional[List[Token]] = field(default=None, repr=False)

    def body_tokens(self) -> List[Token]:
        if self._tokens is None:
            self._tokens = [Token(t.kind, t.text, self.line) for t in lex(self.body) if t.kind not in (COMMENT, PP)]
        return self._tokens


def parse_directive(tok: Token) -> Directive:
    clean = COMMENT_RE.sub(" ", _SPLICE_RE.sub("", tok.text))
    m = _DIRECTIVE_RE.match(clean)
    kind = (m.group(1) or "") if m else ""
    rest = (m.group(2) if m else "").strip()
    d = Directive(kind, tok.line, tok.line + tok.text.count("\n"), rest)
    if kind == "define":
        md = _DEFINE_RE.match(rest)
        if md:
            d.name = md.group(1)
            if md.group(2) is not None:
                d.params = tuple(p.strip() for p in md.group(2)[1:-1].split(",") if p.strip())
            d.body = md.group(3).strip()
    elif kind in ("undef", "ifdef", "ifndef"):
        words = rest.split()
        d.name = words[0] if words else ""
    return d


# ---------- program structure ----------

@dataclass
class Param:
    type: str
    name: str
    qualifiers: Tuple[str, ...] = ()
    array: str = ""


@dataclass
class Const:
    name: str
    type: str
    line: int
    file: str
    expr: List[Token] = field(default_factory=list, repr=False)
    const: bool = True
    qualifiers: Tuple[str, ...] = ()


@dataclass
class Struct:
    name: str
    line: int
    fields: List[Tuple[str, str]]


@dataclass
class Call:
    name: str
    idx: int                     # token index of the callee's name in its Fn.toks
    line: int
    args: List[Tuple[int, int]]  # token ranges of the arguments
    builtin: bool


@dataclass(eq=False)
class Loop:
    kind: str                    # for | while | do
    fn: str
    file: str
    line: int
    keyword: int                 # token index of `for`/`while`/`do`; the loop is toks[keyword:end]
    end: int
    header: Tuple[int, int]      # tokens inside for(...)/while(...)
    body: Tuple[int, int]        # the body's tokens (inside its braces when it has them)
    init: Optional[Tuple[int, int]] = None
    cond: Optional[Tuple[int, int]] = None
    step: Optional[Tuple[int, int]] = None
    var: Optional[str] = None
    start: object = None
    limit: object = None
    op: Optional[str] = None
    delta: object = None
    bound: Optional[int] = None  # literal trip count, when the reader can prove one
    note: str = ""               # why there is no bound, or what was assumed
    symbolic: Optional[dict] = None  # the bound is a parameter: {param, start, op, kind, amount}; see bound_with()
    parent: Optional["Loop"] = field(default=None, repr=False)
    depth: int = 0

    @property
    def full(self) -> Tuple[int, int]:
        return (self.keyword, self.end)

    def bound_with(self, limit) -> Optional[int]:
        """The trip count once a symbolic (parameter) limit is known."""
        if self.bound is not None or not self.symbolic or limit is None:
            return self.bound
        sy = self.symbolic
        return trip_count(sy["start"], sy["op"], limit, sy["kind"], sy["amount"])


@dataclass
class Stmt:
    """A statement fragment of a function body: split at ';', '{' and '}' outside parentheses. `text` is flat text
    (tokens joined by single spaces) without the trailing ';'."""
    a: int
    b: int
    text: str
    line: int


def _match_brackets(toks: Sequence[Token]) -> List[int]:
    """match[i] is the index of the bracket closing/opening toks[i], or -1. A stray closer drops unmatched openers."""
    match = [-1] * len(toks)
    stack: List[int] = []
    pair = {")": "(", "]": "[", "}": "{"}
    for i, t in enumerate(toks):
        if t.kind != OP:
            continue
        x = t.text
        if x in ("(", "[", "{"):
            stack.append(i)
        elif x in pair:
            while stack and toks[stack[-1]].text != pair[x]:
                stack.pop()
            if stack:
                j = stack.pop()
                match[i], match[j] = j, i
    return match


def split_top(toks: Sequence[Token], match: Sequence[int], a: int, b: int, sep: str,
              keep_empty: bool = False) -> List[Tuple[int, int]]:
    """Token ranges of toks[a:b] split at `sep` outside brackets. Empty parts are dropped unless keep_empty, which keeps
    every part in its place (a macro's arguments meet its parameters by position: `F(, x)` passes x second)."""
    out, cur, k = [], a, a
    while k < b:
        x = toks[k].text
        if x in ("(", "[", "{") and a <= match[k] < b and match[k] > k:
            k = match[k] + 1
            continue
        if x == sep:
            out.append((cur, k))
            cur = k + 1
        k += 1
    out.append((cur, b))
    return out if keep_empty else [(i, j) for i, j in out if j > i]


@dataclass(eq=False)
class Fn:
    """A function definition, or a macro read as one (kind 'macro'). Its body is toks[start:end] (inside the braces)."""
    name: str
    kind: str                    # function | macro
    ret: Optional[str]
    params: List[Param]
    line: int
    end_line: int
    file: str
    toks: List[Token] = field(repr=False)
    match: List[int] = field(repr=False)
    start: int = 0
    end: int = 0
    prog: Optional["Program"] = field(default=None, repr=False)
    calls: List[Call] = field(default_factory=list, repr=False)
    # A macro's calls of its own parameters (`#define APPLY(f, x) f(x)` calls f): not calls of anything named like the
    # parameter, but of whatever each caller passes in its place (Unit.calls).
    param_calls: List[Call] = field(default_factory=list, repr=False)
    object_like: bool = field(default=False, repr=False)    # a macro with no parameter list (`#define WHICH bend`)
    loops: List[Loop] = field(default_factory=list, repr=False)
    idents: Set[str] = field(default_factory=set, repr=False)
    locals: Dict[str, List[Token]] = field(default_factory=dict, repr=False)
    analysed: bool = field(default=False, repr=False)
    _flat: Optional[str] = field(default=None, repr=False)
    _offsets: Optional[List[int]] = field(default=None, repr=False)

    @property
    def param_names(self) -> Set[str]:
        """The names this function's or macro's own parameters bind in its body. In a macro a parameter is the argument
        it is called with; in a function it shadows any global, uniform or object-like #define of the same name (the
        preprocessor renames a parameter and its uses alike: `#define t iTime` makes `float f(float t)` a function of a
        parameter called iTime). Either way a token naming one is never a use of anything outside the body."""
        return {p.name for p in self.params if p.name}

    # --- flat text ---
    def text(self, a: int, b: int) -> str:
        return " ".join(t.text for t in self.toks[a:b])

    @property
    def flat(self) -> str:
        if self._flat is None:
            parts, offs, pos = [], [], 0
            for t in self.toks[self.start:self.end]:
                offs.append(pos)
                parts.append(t.text)
                pos += len(t.text) + 1
            self._flat, self._offsets = " ".join(parts), offs
        return self._flat

    def token_at(self, offset: int) -> int:
        """The token index (into toks) under a character offset of `flat`."""
        self.flat
        k = bisect.bisect_right(self._offsets, offset) - 1
        return self.start + max(k, 0)

    def line_at(self, offset: int) -> int:
        if self.start >= self.end:
            return self.line
        return self.toks[min(self.token_at(offset), self.end - 1)].line

    # --- statements ---
    def stmt_end(self, i: int, limit: Optional[int] = None) -> int:
        """Index one past the statement starting at toks[i] (a block, a loop, an if/else chain, or up to ';')."""
        toks, match = self.toks, self.match
        limit = self.end if limit is None else limit
        while True:
            if i >= limit:
                return limit
            x = toks[i].text
            if x == "{":
                return match[i] + 1 if match[i] > i else limit
            if x in ("for", "while") and i + 1 < limit and toks[i + 1].text == "(" and match[i + 1] > i:
                i = match[i + 1] + 1
                continue
            if x == "if" and i + 1 < limit and toks[i + 1].text == "(" and match[i + 1] > i:
                j = self.stmt_end(match[i + 1] + 1, limit)
                if j < limit and toks[j].text == "else":
                    i = j + 1
                    continue
                return j
            if x == "do":
                j = self.stmt_end(i + 1, limit)
                if j + 1 < limit and toks[j].text == "while" and toks[j + 1].text == "(" and match[j + 1] > j:
                    r = match[j + 1]
                    return min(r + 2 if r + 1 < limit and toks[r + 1].text == ";" else r + 1, limit)
                return j
            if x == "else":
                i += 1
                continue
            break
        k = i
        while k < limit:
            y = toks[k].text
            if y in ("(", "[", "{") and match[k] > k:
                k = match[k] + 1
                continue
            if y == ";":
                return k + 1
            if y == "}":
                return k
            k += 1
        return limit

    def statements(self, a: Optional[int] = None, b: Optional[int] = None,
                   exclude: Iterable[Tuple[int, int]] = ()) -> List[Stmt]:
        """Statement fragments of toks[a:b] (default: the whole body), skipping the token ranges in `exclude`."""
        a = self.start if a is None else a
        b = self.end if b is None else b
        ex = sorted(r for r in exclude if r[1] > r[0])
        out: List[Stmt] = []
        toks, match = self.toks, self.match

        def flush(i: int, j: int) -> None:
            if j > i and toks[j - 1].text == ";":
                j -= 1
            if j > i:
                out.append(Stmt(i, j, self.text(i, j), toks[i].line))

        cur, k, e = a, a, 0
        while k < b:
            while e < len(ex) and ex[e][1] <= k:
                e += 1
            if e < len(ex) and ex[e][0] <= k < ex[e][1]:
                flush(cur, k)
                k = cur = ex[e][1]
                continue
            x = toks[k].text
            if x in ("(", "[") and k < match[k] < b:
                k = match[k] + 1
                continue
            if x == ";":
                flush(cur, k + 1)
                cur = k + 1
            elif x in ("{", "}"):
                flush(cur, k)
                cur = k + 1
            k += 1
        flush(cur, b)
        return out

    def loop_statements(self, loop: Loop) -> List[Stmt]:
        """The loop's OWN statements: its body without nested loops, plus each comma part of a for-loop's step."""
        kids = [c.full for c in self.loops if c.parent is loop]
        out = self.statements(loop.body[0], loop.body[1], exclude=kids)
        if loop.step:
            for i, j in split_top(self.toks, self.match, loop.step[0], loop.step[1], ","):
                out.append(Stmt(i, j, self.text(i, j), self.toks[i].line))
        return out

    def enclosing_loops(self, idx: int) -> List[Loop]:
        """Loops of this function whose span contains token idx, outermost first."""
        return [lp for lp in self.loops if lp.keyword < idx < lp.end]


class Program:
    """One GLSL source (a Shadertoy pass, Common, or a .frag) read into its structure. `base` is the program prepended
    before it (Common for a pass): its #defines are live here and its consts resolve here."""

    def __init__(self, src: str, file: str = "image.glsl", base: Optional["Program"] = None,
                 predefined: Optional[Dict[str, str]] = None, _depth: int = 0):
        self.file = file
        self._depth = _depth
        self.src = normalize_newlines(src)
        self.base = base
        self.tokens = lex(self.src)
        self.directives: List[Directive] = []
        self.comments: List[Token] = []
        self.sig: List[Token] = []
        self.inactive_lines: Set[int] = set()
        self.unsure_ifs: List[int] = []
        self.defines: Dict[str, Directive] = {}
        if base is not None:
            self.defines.update(base.defines)
        else:
            for k, v in (PREDEFINED if predefined is None else predefined).items():
                self.defines[k] = Directive("define", 0, 0, f"{k} {v}", name=k, body=v)
        self.own_defines: Dict[str, Directive] = {}
        self.functions: Dict[str, List[Fn]] = {}
        self.prototypes: Set[str] = set()
        self.macros: Dict[str, Fn] = {}
        self.structs: Dict[str, Struct] = {}
        self.consts: Dict[str, Const] = {}
        self.globals: Dict[str, Const] = {}
        self.uniforms: Dict[str, str] = {}
        self.problems: List[str] = []
        self._value_cache: Dict[str, object] = {}
        self._preprocess()
        self.match = _match_brackets(self.sig)
        self._toplevel()
        self._macros()
        for fns in self.functions.values():
            for fn in fns:
                _analyse_fn(fn)
        for fn in self.macros.values():
            _analyse_fn(fn, loops=False)
        _analyse_fn(self.toplevel)

    # --- preprocessor ---
    def _pp_eval(self, expr: str) -> Optional[bool]:
        toks = [t for t in lex(expr) if t.kind not in (COMMENT, PP)]
        out: List[Token] = []
        i = 0
        while i < len(toks):
            t = toks[i]
            if t.text == "defined":
                if i + 1 < len(toks) and toks[i + 1].text == "(":
                    name = toks[i + 2].text if i + 2 < len(toks) else ""
                    i += 4
                else:
                    name = toks[i + 1].text if i + 1 < len(toks) else ""
                    i += 2
                out.append(Token(NUMBER, "1" if name in self.defines else "0", t.line))
                continue
            out.append(t)
            i += 1
        seen: Set[str] = set()

        def lookup(name: str):
            d = self.defines.get(name)
            if d is None:
                return 0                       # C: an unknown name in #if is 0
            if d.params is not None or name in seen:
                return None
            seen.add(name)
            try:
                return Evaluator(lookup).evaluate(d.body_tokens())
            finally:
                seen.discard(name)

        v = Evaluator(lookup).evaluate(out)
        return None if v is None else bool(v)

    def _preprocess(self) -> None:
        stack: List[List[bool]] = []       # [parent_active, a_branch_was_taken]
        active = True
        for tok in self.tokens:
            if tok.kind == PP:
                d = parse_directive(tok)
                k = d.kind
                d.active = active
                if k in ("if", "ifdef", "ifndef"):
                    cond = False
                    if active:
                        if k == "if":
                            cond = self._pp_eval(d.rest)
                        elif k == "ifdef":
                            cond = d.name in self.defines
                        else:
                            cond = d.name not in self.defines
                        if cond is None:
                            cond = True
                            self.unsure_ifs.append(d.line)
                    stack.append([active, bool(cond)])
                    active = active and bool(cond)
                elif k == "elif" and stack:
                    parent, taken = stack[-1]
                    cond = False
                    if parent and not taken:
                        cond = self._pp_eval(d.rest)
                        if cond is None:
                            cond = True
                            self.unsure_ifs.append(d.line)
                    stack[-1][1] = taken or bool(cond)
                    active = parent and bool(cond) and not taken
                elif k == "else" and stack:
                    parent, taken = stack[-1]
                    active = parent and not taken
                    stack[-1][1] = True
                elif k == "endif" and stack:
                    active = stack.pop()[0]
                elif active and k == "define" and d.name:
                    self.defines[d.name] = d
                    self.own_defines[d.name] = d
                elif active and k == "undef":
                    self.defines.pop(d.name, None)
                self.directives.append(d)
            elif tok.kind == COMMENT:
                self.comments.append(tok)
            elif active:
                self.sig.append(tok)
            else:
                self.inactive_lines.add(tok.line)
        if stack:
            self.problems.append(f"{self.file}: {len(stack)} #if without #endif")

    # --- top level ---
    def _skip_to_semicolon(self, i: int) -> int:
        sig, match = self.sig, self.match
        while i < len(sig):
            x = sig[i].text
            if x in ("(", "[", "{") and match[i] > i:
                i = match[i] + 1
                continue
            if x == ";":
                return i + 1
            i += 1
        return i

    def _skip_item(self, i: int) -> int:
        """Past a top-level item that is not a function: to its ';', or past a {...} block, whichever comes first --
        so one unrecognised construct can never swallow the functions after it."""
        sig, match = self.sig, self.match
        while i < len(sig):
            x = sig[i].text
            if x in ("(", "[") and match[i] > i:
                i = match[i] + 1
                continue
            if x == "{":
                return match[i] + 1 if match[i] > i else i + 1
            if x == ";":
                return i + 1
            i += 1
        return i

    def _toplevel(self) -> None:
        sig, match, n = self.sig, self.match, len(self.sig)
        stray: List[int] = []
        i = 0
        while i < n:
            t = sig[i]
            x = t.text
            if x == ";" or x == "}":
                stray.append(i)
                i += 1
                continue
            if x == "{":
                j = match[i] + 1 if match[i] > i else i + 1
                stray.extend(range(i, j))
                i = j
                continue
            if x == "precision":
                i = self._skip_to_semicolon(i)
                continue
            if x == "struct":
                i = self._struct(i)
                continue
            d = self.defines.get(x)
            if d is not None and d.params is not None and i + 1 < n and sig[i + 1].text == "(" and match[i + 1] > i:
                # A function-like macro invoked at top level usually GENERATES functions (DECL_FBM(fbm, 4, ...)).
                stray.extend(range(i, match[i + 1] + 1))
                self._expand_toplevel(d, i, match[i + 1])
                i = match[i + 1] + 1
                continue
            # A header: qualifiers, a type (maybe an array), a name -- then '(' for a function, else a declaration.
            k = i
            while k < n and (sig[k].kind == IDENT or sig[k].text in ("[", "]") or
                             (sig[k].kind == NUMBER and k > i and sig[k - 1].text == "[")):
                if sig[k].text == "[" and match[k] > k:
                    k = match[k] + 1
                    continue
                k += 1
            head = [s for s in sig[i:k] if s.kind == IDENT]
            if k < n and sig[k].text == "(" and len(head) >= 2 and match[k] > k and head[-1].text not in KEYWORDS:
                close = match[k]
                nxt = sig[close + 1].text if close + 1 < n else ""
                if nxt == "{" and match[close + 1] > close:
                    self._function(i, k, close, close + 1, match[close + 1])
                    i = match[close + 1] + 1
                    continue
                if nxt == ";":
                    self.prototypes.add(head[-1].text)
                    i = close + 2
                    continue
            end = self._skip_item(i)
            stray.extend(range(i, end))
            self._declaration(i, end)
            i = end
        # Everything outside functions, read as one pseudo-function. It is the entry point of last resort: golfers
        # define mainImage INSIDE a macro (a `#define` whose body is the entry's signature and opening brace) and write
        # its body at top level, and global initializers can call functions too.
        toks = [sig[k] for k in stray]
        self.toplevel = Fn(name=TOPLEVEL, kind="toplevel", ret="void", params=[], line=toks[0].line if toks else 1,
                           end_line=toks[-1].line if toks else 1, file=self.file, toks=toks,
                           match=_match_brackets(toks), start=0, end=len(toks), prog=self)

    def _expand_toplevel(self, d: Directive, i: int, close: int) -> None:
        """Expand one top-level macro invocation and keep the functions it defines (their lines = the invocation's)."""
        sig, match = self.sig, self.match
        args = [" ".join(t.text for t in sig[a:b]) for a, b in split_top(sig, match, i + 2, close, ",")]
        params = d.params or ()
        out = []
        for t in d.body_tokens():
            if t.kind == IDENT and t.text in params and params.index(t.text) < len(args):
                out.append(args[params.index(t.text)])
            else:
                out.append(t.text)
        text = " ".join(out).replace(" ## ", "").replace("##", "")
        line = sig[i].line
        try:
            sub = Program("\n" * (line - 1) + text, file=self.file, base=self)
        except RecursionError:
            return
        for name, fns in sub.functions.items():
            self.functions.setdefault(name, []).extend(fns)
            for fn in fns:
                fn.prog = self

    def _struct(self, i: int) -> int:
        sig, match = self.sig, self.match
        name = sig[i + 1].text if i + 1 < len(sig) and sig[i + 1].kind == IDENT else ""
        lb = i + 2 if name else i + 1
        if lb >= len(sig) or sig[lb].text != "{" or match[lb] < lb:
            return self._skip_to_semicolon(i)
        fields = []
        for a, b in split_top(sig, match, lb + 1, match[lb], ";"):
            words = [t.text for t in sig[a:b] if t.kind == IDENT and t.text not in QUALIFIERS]
            if len(words) >= 2:
                for fname in words[1:]:
                    fields.append((words[0], fname))
        if name:
            self.structs[name] = Struct(name, sig[i].line, fields)
        return self._skip_to_semicolon(match[lb] + 1)    # past `};` or `} declarators;`

    def _params(self, a: int, b: int) -> List[Param]:
        out = []
        for i, j in split_top(self.sig, self.match, a, b, ","):
            words = [t for t in self.sig[i:j]]
            quals = tuple(t.text for t in words if t.text in QUALIFIERS)
            rest = [t for t in words if t.text not in QUALIFIERS]
            idents = [t.text for t in rest if t.kind == IDENT]
            array = "".join(t.text for t in rest if t.text in ("[", "]") or (t.kind == NUMBER))
            if not idents or idents == ["void"]:
                continue
            ptype = idents[0]
            pname = idents[1] if len(idents) > 1 else ""
            out.append(Param(ptype, pname, quals, array))
        return out

    def _function(self, i: int, lp: int, rp: int, lb: int, rb: int) -> None:
        sig = self.sig
        head = [s.text for s in sig[i:lp] if s.kind == IDENT and s.text not in QUALIFIERS]
        name = head[-1]
        ret = head[-2] if len(head) >= 2 else "void"
        arr = "".join(s.text for s in sig[i:lp] if s.text in ("[", "]") or s.kind == NUMBER)
        fn = Fn(name=name, kind="function", ret=ret + arr, params=self._params(lp + 1, rp), line=sig[i].line,
                end_line=sig[rb].line, file=self.file, toks=sig, match=self.match, start=lb + 1, end=rb, prog=self)
        self.functions.setdefault(name, []).append(fn)

    def _declaration(self, i: int, end: int) -> None:
        sig, match = self.sig, self.match
        stop = end - 1 if end - 1 >= i and sig[end - 1].text == ";" else end
        quals = []
        k = i
        while k < stop and sig[k].text in QUALIFIERS:
            if sig[k].text == "layout" and k + 1 < stop and sig[k + 1].text == "(" and match[k + 1] > k:
                k = match[k + 1] + 1
                continue
            quals.append(sig[k].text)
            k += 1
        if k >= stop or sig[k].kind != IDENT:
            return
        dtype = sig[k].text
        k += 1
        if k < stop and sig[k].text == "[" and match[k] > k:
            dtype += self_text(sig, k, match[k] + 1)
            k = match[k] + 1
        for a, b in split_top(sig, match, k, stop, ","):
            if sig[a].kind != IDENT:
                continue
            name = sig[a].text
            eq = next((q for q in range(a, b) if sig[q].text == "="), None)
            expr = list(sig[eq + 1:b]) if eq is not None else []
            rec = Const(name, dtype, sig[a].line, self.file, expr, "const" in quals, tuple(quals))
            if "uniform" in quals:
                self.uniforms[name] = dtype
            elif "const" in quals:
                self.consts[name] = rec
            else:
                self.globals[name] = rec

    def _macros(self) -> None:
        for name, d in self.own_defines.items():
            toks = d.body_tokens()
            fn = Fn(name=name, kind="macro", ret=None, params=[Param("", p) for p in (d.params or ())], line=d.line,
                    end_line=d.end_line, file=self.file, toks=toks, match=_match_brackets(toks), start=0,
                    end=len(toks), prog=self, object_like=d.params is None)
            self.macros[name] = fn

    # --- constants ---
    def expand(self, toks: Sequence[Token], depth: int = 0) -> List[Token]:
        """Function-like macros in an expression expanded in place (NO_UNROLL(0) -> its body with 0 for the param)."""
        if depth > MAX_EXPANSION_DEPTH or not any(t.kind == IDENT and t.text in self.defines for t in toks):
            return list(toks)
        toks = list(toks)
        match = _match_brackets(toks)
        out: List[Token] = []
        i = 0
        while i < len(toks):
            t = toks[i]
            d = self.defines.get(t.text) if t.kind == IDENT else None
            if (d is not None and d.params is not None and i + 1 < len(toks) and toks[i + 1].text == "("
                    and match[i + 1] > i):
                close = match[i + 1]
                args = [toks[a:b] for a, b in split_top(toks, match, i + 2, close, ",")]
                body: List[Token] = [Token(OP, "(", t.line)]
                for bt in d.body_tokens():
                    if bt.kind == IDENT and bt.text in d.params and d.params.index(bt.text) < len(args):
                        body.extend([Token(OP, "(", t.line)] + args[d.params.index(bt.text)] + [Token(OP, ")", t.line)])
                    else:
                        body.append(bt)
                body.append(Token(OP, ")", t.line))
                out.extend(self.expand(body, depth + 1))
                i = close + 1
                continue
            out.append(t)
            i += 1
        return out

    def evaluate(self, toks: Sequence[Token], local: Optional[Dict[str, List[Token]]] = None):
        """The constant value of an expression, resolving names through `local`, this program's consts and #defines,
        then the base program's. None when anything in it is not a compile-time constant this reader can fold."""
        toks = self.expand(toks)
        seen: Set[str] = set()

        def lookup(name: str):
            if name in seen:
                return None
            seen.add(name)
            try:
                return self._lookup(name, local, lookup)
            finally:
                seen.discard(name)

        return Evaluator(lookup).evaluate(toks)

    def _lookup(self, name: str, local, lookup):
        if local is not None and name in local:
            return Evaluator(lookup).evaluate(local[name])
        if name in NONNEGATIVE_UNIFORMS:
            return NONNEG
        prog = self
        while prog is not None:
            c = prog.consts.get(name)
            if c is not None and c.expr:
                return Evaluator(lookup).evaluate(c.expr)
            prog = prog.base
        d = self.defines.get(name)
        if d is not None and d.params is None and d.body:
            return Evaluator(lookup).evaluate(self.expand(d.body_tokens()))
        return None

    def value_of(self, name: str):
        """A named constant's value (a const, an object-like #define, or the base program's), else None."""
        if name not in self._value_cache:
            self._value_cache[name] = self.evaluate([Token(IDENT, name, 0)])
        return self._value_cache[name]

    def all_functions(self) -> List[Fn]:
        return [fn for fns in self.functions.values() for fn in fns]

    def size(self) -> dict:
        lines = self.src.count("\n") + 1
        code_lines = {t.line for t in self.sig}
        comment_lines = set()
        for c in self.comments:
            comment_lines.update(range(c.line, c.line + c.text.count("\n") + 1))
        loops = [lp for fn in self.all_functions() for lp in fn.loops]
        return {"lines": lines, "code_lines": len(code_lines), "comment_lines": len(comment_lines - code_lines),
                "chars": len(self.src), "tokens": len(self.sig), "functions": len(self.all_functions()),
                "macros": len(self.macros), "structs": len(self.structs), "consts": len(self.consts),
                "loops": len(loops), "max_loop_depth": max((lp.depth + 1 for lp in loops), default=0),
                "inactive_lines": len(self.inactive_lines)}


def self_text(toks: Sequence[Token], a: int, b: int) -> str:
    return "".join(t.text for t in toks[a:b])


# ---------- inside a function ----------

def _after_parens(fn: Fn, lp: int) -> Optional[str]:
    """The text of the token after the ')' that closes the '(' at `lp`, or None at the body's end."""
    rp = fn.match[lp]
    return fn.toks[rp + 1].text if rp > lp and rp + 1 < fn.end else None


def _alias_target(fn: Fn, name: str) -> str:
    """Follow one-name object-like macros (`#define RET return`, `#define AND &&`) to what `name` stands for."""
    macros = getattr(fn.prog, "macros", None) or {}
    seen: Set[str] = set()
    while name not in seen:
        m = macros.get(name)
        if m is None or not m.object_like or m.end - m.start != 1:
            break
        seen.add(name)
        name = m.toks[m.start].text
    return name


def _analyse_fn(fn: Fn, loops: bool = True) -> None:
    if fn.analysed:
        return
    fn.analysed = True
    toks, match = fn.toks, fn.match
    own = fn.param_names
    for k in range(fn.start, fn.end):
        t = toks[k]
        if t.kind != IDENT:
            continue
        # A parameter is not an identifier of the body it belongs to (Fn.param_names), so the call graph never reaches
        # a macro through a parameter's name. In a macro it is not a call either: `#define APPLY(f, x) f(x)` calls what
        # the caller passes, not a function named f, so it is filed in fn.param_calls and Unit.calls makes it a call of
        # the caller's argument. (`#define DECL(name) float name(float v) {...}` DEFINES what name stands for: a name
        # after an identifier is being declared only when its ')' is followed by '{' or ';' and that identifier is not
        # an operator or keyword in disguise -- `#define JOIN(op, fx, v) (v op fx(v))`, `#define AND &&`,
        # `#define RET return` all CALL fx. Re-review, 2026-10-13.) In a function, a parameter's name followed by '('
        # can only be a function-like macro of that name, which is a call.
        if t.text in own and (fn.kind == "macro" or k + 1 >= fn.end or toks[k + 1].text != "("):
            if fn.kind == "macro" and k + 1 < fn.end and toks[k + 1].text == "(" and not (
                    k > fn.start and toks[k - 1].kind == IDENT and toks[k - 1].text not in KEYWORDS
                    and _after_parens(fn, k + 1) in ("{", ";")
                    and _alias_target(fn, toks[k - 1].text) not in KEYWORDS):
                fn.param_calls.append(Call(t.text, k, t.line, [], False))
            continue
        fn.idents.add(t.text)
        if t.text in KEYWORDS or k + 1 >= fn.end or toks[k + 1].text != "(":
            continue
        if k > fn.start and toks[k - 1].text == ".":
            continue                       # v.length() is a method, not a call
        lp = k + 1
        rp = match[lp] if match[lp] > lp else fn.end
        args = split_top(toks, match, lp + 1, rp, ",") if rp > lp + 1 else []
        fn.calls.append(Call(t.text, k, t.line, args, t.text in BUILTIN_FUNCTIONS or t.text in TYPES))
    if not loops:
        return
    fn.locals = _local_constants(fn)
    _find_loops(fn)
    for lp in fn.loops:
        _infer_bound(fn, lp)


def _arg_ranges(fn: Fn, c: Call) -> List[Tuple[int, int]]:
    """The token ranges of a call's arguments in fn, each in its place, empty ones included (a macro's parameters are
    matched by position)."""
    lp = c.idx + 1
    if lp >= fn.end or fn.toks[lp].text != "(":
        return []
    rp = fn.match[lp] if fn.match[lp] > lp else fn.end
    return split_top(fn.toks, fn.match, lp + 1, rp, ",", keep_empty=True) if rp > lp + 1 else []


def _arg_last_name(fn: Fn, rng: Tuple[int, int]) -> Optional[int]:
    """The token index of the name an argument puts right before the '(' a macro writes after that parameter: the
    argument's LAST token, when it is an identifier that is neither a keyword nor a field after '.'. `-bend` and
    `0.5 * bend` end in bend (`-bend(x)`, `0.5 * bend(x)`); `at.bend` and `bend * 0.5` name no call."""
    a, b = rng
    if b <= a:
        return None
    j = b - 1
    t = fn.toks[j]
    if t.kind != IDENT or t.text in KEYWORDS or (j > a and fn.toks[j - 1].text == "."):
        return None
    return j


def _local_constants(fn: Fn) -> Dict[str, List[Token]]:
    """Scalar locals declared once with an initializer and never assigned again: the reader may fold them."""
    toks, match = fn.toks, fn.match
    decls: Dict[str, List[List[Token]]] = {}
    writes: Dict[str, int] = {}
    for k in range(fn.start, fn.end - 2):
        t = toks[k]
        if t.text in SCALAR_TYPES and toks[k + 1].kind == IDENT and toks[k + 2].text == "=":
            e = k + 3
            while e < fn.end and toks[e].text not in (",", ";"):
                if toks[e].text in ("(", "[") and match[e] > e:
                    e = match[e]
                e += 1
            decls.setdefault(toks[k + 1].text, []).append(list(toks[k + 3:e]))
        if t.kind == IDENT and (toks[k + 1].text in ASSIGN_OPS or toks[k + 1].text in ("++", "--")
                               or (k > fn.start and toks[k - 1].text in ("++", "--"))):
            if not (k > fn.start and toks[k - 1].text == "."):
                writes[t.text] = writes.get(t.text, 0) + 1
    return {n: e[0] for n, e in decls.items() if len(e) == 1 and writes.get(n, 0) == 1}


def _find_loops(fn: Fn) -> None:
    toks, match = fn.toks, fn.match
    do_tails: Set[int] = set()
    found: List[Loop] = []
    for k in range(fn.start, fn.end):
        t = toks[k]
        if t.kind != IDENT or t.text not in ("for", "while", "do"):
            continue
        if t.text in ("for", "while"):
            if k in do_tails:
                continue
            lp = k + 1
            if lp >= fn.end or toks[lp].text != "(" or match[lp] < lp:
                continue
            rp = match[lp]
            b0 = rp + 1
            if b0 < fn.end and toks[b0].text == "{" and match[b0] > b0:
                body, end = (b0 + 1, match[b0]), match[b0] + 1
            else:
                end = fn.stmt_end(b0)
                body = (b0, end)
            lo = Loop(t.text, fn.name, fn.file, t.line, k, end, (lp + 1, rp), body)
            if t.text == "for":
                parts = _split_header(toks, match, lp + 1, rp)
                lo.init, lo.cond, lo.step = parts
            else:
                lo.cond = (lp + 1, rp)
            found.append(lo)
        else:
            b0 = k + 1
            if b0 < fn.end and toks[b0].text == "{" and match[b0] > b0:
                body, after = (b0 + 1, match[b0]), match[b0] + 1
            else:
                after = fn.stmt_end(b0)
                body = (b0, after)
            lo = Loop("do", fn.name, fn.file, t.line, k, after, (after, after), body)
            if after + 1 < fn.end and toks[after].text == "while" and toks[after + 1].text == "(" \
                    and match[after + 1] > after:
                do_tails.add(after)
                rp = match[after + 1]
                lo.header = lo.cond = (after + 2, rp)
                lo.end = rp + 2 if rp + 1 < fn.end and toks[rp + 1].text == ";" else rp + 1
            found.append(lo)
    found.sort(key=lambda lo: lo.keyword)
    stack: List[Loop] = []
    for lo in found:
        while stack and not (stack[-1].keyword < lo.keyword and lo.end <= stack[-1].end):
            stack.pop()
        lo.parent = stack[-1] if stack else None
        lo.depth = len(stack)
        stack.append(lo)
    fn.loops = found


def _split_header(toks, match, a: int, b: int):
    """for( init ; cond ; step ) -> three token ranges (None when a part is empty)."""
    cuts, k = [], a
    while k < b:
        x = toks[k].text
        if x in ("(", "[") and match[k] > k:
            k = match[k] + 1
            continue
        if x == ";":
            cuts.append(k)
        k += 1
    if len(cuts) != 2:
        return None, (a, b), None
    parts = [(a, cuts[0]), (cuts[0] + 1, cuts[1]), (cuts[1] + 1, b)]
    return tuple(p if p[1] > p[0] else None for p in parts)


_CMP = ("<", "<=", ">", ">=", "!=")
_FLIP = {"<": ">", ">": "<", "<=": ">=", ">=": "<=", "!=": "!="}


def _strip_cast(tt: List[Token]) -> List[Token]:
    """float(i) / int(i) / (i) -> i, so a condition like float(i) < 64. still names its variable."""
    while len(tt) >= 3 and tt[-1].text == ")" and (tt[0].text == "(" or (tt[0].text in SCALAR_TYPES and tt[1].text == "(")):
        tt = tt[1:-1] if tt[0].text == "(" else tt[2:-1]
    return tt


def _infer_bound(fn: Fn, lo: Loop) -> None:
    """Set lo.var/start/limit/op/delta/bound when the trip count is a compile-time fact; else explain in lo.note."""
    toks, match, prog = fn.toks, fn.match, fn.prog
    ev = lambda tt: prog.evaluate(tt, fn.locals)
    inits: Dict[str, Optional[List[Token]]] = {}
    if lo.init:
        for a, b in split_top(toks, match, lo.init[0], lo.init[1], ","):
            part = list(toks[a:b])
            eqs = [q for q, t in enumerate(part) if t.text == "="]
            if not eqs:
                names = [t.text for t in part if t.kind == IDENT and t.text not in TYPES and t.text not in QUALIFIERS]
                if names:
                    inits[names[-1]] = None
                continue
            # `s = i = 0.` gives every name in the chain the last right-hand side
            for q in eqs:
                if q > 0 and part[q - 1].kind == IDENT:
                    inits[part[q - 1].text] = part[eqs[-1] + 1:]
    # the condition: one comparison per && term; || defeats a bound
    if not lo.cond:
        lo.note = "no condition"
        return
    ca, cb = lo.cond
    if any(toks[q].text == "||" for q in range(ca, cb)):
        lo.note = "condition has ||"
        return
    terms = []
    for a, b in split_top(toks, match, ca, cb, "&&"):
        tt = list(toks[a:b])
        tt = _strip_cast(tt) if tt and tt[0].text == "(" and match[a] == b - 1 else tt
        depth = 0
        for q, t in enumerate(tt):
            if t.text in ("(", "["):
                depth += 1
            elif t.text in (")", "]"):
                depth -= 1
            elif depth == 0 and t.text in _CMP:
                terms.append((tt[:q], t.text, tt[q + 1:]))
                break
    # step updates from the header, keyed by variable
    steps: Dict[str, Tuple[str, List[Token]]] = {}
    if lo.step:
        for a, b in split_top(toks, match, lo.step[0], lo.step[1], ","):
            part = list(toks[a:b])
            _read_update(part, steps)
            # an increment buried in a golfed step: `O[i++] = ...`
            for q, t in enumerate(part):
                if t.kind != IDENT or t.text in steps:
                    continue
                if q + 1 < len(part) and part[q + 1].text in ("++", "--"):
                    steps[t.text] = ("add" if part[q + 1].text == "++" else "sub", [])
                elif q > 0 and part[q - 1].text in ("++", "--") and (q < 2 or part[q - 2].kind != IDENT):
                    steps[t.text] = ("add" if part[q - 1].text == "++" else "sub", [])
    best = None
    for lhs, op, rhs in terms:
        for side, other, o in ((lhs, rhs, op), (rhs, lhs, _FLIP[op])):
            side = _strip_cast(side)
            cond_delta, pre = 0, False
            if len(side) == 2 and side[1].text in ("++", "--") and side[0].kind == IDENT:
                var, cond_delta = side[0].text, (1 if side[1].text == "++" else -1)
            elif len(side) == 2 and side[0].text in ("++", "--") and side[1].kind == IDENT:
                var, cond_delta, pre = side[1].text, (1 if side[0].text == "++" else -1), True
            elif len(side) == 1 and side[0].kind == IDENT:
                var = side[0].text
            else:
                continue
            limit = ev(other)
            param = None
            if limit is None:
                # a bound passed in as a parameter (fbm(p, 6)): kept symbolic, resolved per call site by the dissector
                lim = _strip_cast(list(other))
                if len(lim) == 1 and lim[0].kind == IDENT and any(pp.name == lim[0].text for pp in fn.params):
                    param = lim[0].text
                else:
                    continue
            # where the variable starts
            if var in inits:
                start = ev(inits[var]) if inits[var] is not None else 0
                assumed = inits[var] is None
            else:
                prev = _last_assignment(fn, var, lo.keyword)
                if prev is None:
                    continue
                start, assumed = (ev(prev), False) if prev else (0, True)
            if start is None:
                continue
            # how it moves
            kind, amount = "add", cond_delta
            if var in steps:
                skind, stoks = steps[var]
                val = ev(stoks) if stoks else 1
                if val is None:
                    continue
                if skind == "add":
                    amount += val
                elif skind == "sub":
                    amount -= val
                elif skind in ("mul", "div") and cond_delta == 0:
                    kind, amount = skind, val
                else:
                    continue
            elif cond_delta == 0:
                upd = _body_update(fn, lo, var)
                if upd is None:
                    continue
                skind, val = upd
                if skind == "add":
                    amount = val
                elif skind == "sub":
                    amount = -val
                else:
                    kind, amount = skind, val
            if pre:
                start = start + cond_delta
            if param is not None:
                lo.symbolic = {"param": param, "start": start, "op": o, "kind": kind, "amount": amount, "var": var}
                lo.var, lo.start, lo.op, lo.delta = lo.var or var, start, o, amount
                continue
            n = trip_count(start, o, limit, kind, amount)
            if n is not None and (best is None or n < best[0]):
                best = (n, var, start, limit, o, amount, assumed)
    if best is None:
        if lo.symbolic:
            lo.note = f"bound is the parameter {lo.symbolic['param']!r}"
            return
        lo.note = lo.note or ("while loop" if lo.kind != "for" else "bound not a compile-time constant")
        return
    lo.bound, lo.var, lo.start, lo.limit, lo.op, lo.delta, assumed = best
    if assumed:
        lo.note = f"{lo.var} is declared without a value; assumed 0"


def _read_update(tt: List[Token], into: Dict[str, Tuple[str, List[Token]]]) -> None:
    if len(tt) == 2 and tt[0].kind == IDENT and tt[1].text in ("++", "--"):
        into[tt[0].text] = ("add" if tt[1].text == "++" else "sub", [])
    elif len(tt) == 2 and tt[1].kind == IDENT and tt[0].text in ("++", "--"):
        into[tt[1].text] = ("add" if tt[0].text == "++" else "sub", [])
    elif len(tt) >= 3 and tt[0].kind == IDENT and tt[1].text in ("+=", "-=", "*=", "/="):
        into[tt[0].text] = ({"+=": "add", "-=": "sub", "*=": "mul", "/=": "div"}[tt[1].text], tt[2:])
    elif len(tt) >= 5 and tt[0].kind == IDENT and tt[1].text == "=" and tt[2].text == tt[0].text \
            and tt[3].text in ("+", "-", "*", "/"):
        into[tt[0].text] = ({"+": "add", "-": "sub", "*": "mul", "/": "div"}[tt[3].text], tt[4:])


def _body_update(fn: Fn, lo: Loop, var: str) -> Optional[Tuple[str, object]]:
    """The single update of `var` among the loop's own statements (a while loop's `i++`), if exactly one exists."""
    found: Dict[str, Tuple[str, List[Token]]] = {}
    count = 0
    for st in fn.statements(lo.body[0], lo.body[1], exclude=[c.full for c in fn.loops if c.parent is lo]):
        tt = list(fn.toks[st.a:st.b])
        if tt and tt[-1].text == ";":
            tt = tt[:-1]
        mine: Dict[str, Tuple[str, List[Token]]] = {}
        _read_update(tt, mine)
        if var in mine:
            count += 1
            found = mine
    if count != 1:
        return None
    kind, stoks = found[var]
    val = fn.prog.evaluate(stoks, fn.locals) if stoks else 1
    return None if val is None else (kind, val)


def _last_assignment(fn: Fn, var: str, before: int) -> Optional[List[Token]]:
    """The right-hand side of the last plain `var = ...` before token index `before` in this function; [] when the
    variable is only declared without a value (`float i, d;` -- golfers rely on it reading 0); None when unseen."""
    toks, match = fn.toks, fn.match
    rhs = None
    if fn.prog is not None:
        g = fn.prog.globals.get(var)
        if g is not None and g.type in SCALAR_TYPES:
            rhs = list(g.expr)
    for k in range(fn.start + 1, min(before, fn.end)):
        if toks[k].text == var and toks[k].kind == IDENT and (k + 1 >= fn.end or toks[k + 1].text != "=") and (
                toks[k - 1].text in SCALAR_TYPES or (toks[k - 1].text == "," and _declares(fn, k))):
            rhs = []
    for k in range(fn.start, min(before, fn.end) - 1):
        if toks[k].text == var and toks[k + 1].text == "=" and not (k > fn.start and toks[k - 1].text == "."):
            e = k + 2
            while e < before and toks[e].text not in (",", ";", ")"):
                if toks[e].text in ("(", "[") and match[e] > e:
                    e = match[e]
                e += 1
            rhs = list(toks[k + 2:e])
    return rhs


def _declares(fn: Fn, k: int) -> bool:
    """Is toks[k] (just after a comma) a name in a scalar declaration statement like `float a, b, c;`?"""
    j = k - 1
    while j > fn.start and fn.toks[j].text not in (";", "{", "}", "("):
        j -= 1
    first = fn.toks[j + 1] if fn.toks[j].text in (";", "{", "}", "(") else fn.toks[j]
    return first.text in SCALAR_TYPES


def trip_count(start, op: str, limit, kind: str, amount) -> Optional[int]:
    """How many times `for (v = start; v OP limit; v = v (+|*) amount)` runs its body, or None if unbounded."""
    eps = 1e-7
    try:
        if kind == "add":
            if amount == 0:
                return None
            if op == "<":
                n = math.ceil((limit - start) / amount - eps) if amount > 0 else (None if start < limit else 0)
            elif op == "<=":
                n = (math.floor((limit - start) / amount + eps) + 1 if start <= limit else 0) if amount > 0 \
                    else (None if start <= limit else 0)
            elif op == ">":
                n = math.ceil((start - limit) / -amount - eps) if amount < 0 else (None if start > limit else 0)
            elif op == ">=":
                n = (math.floor((start - limit) / -amount + eps) + 1 if start >= limit else 0) if amount < 0 \
                    else (None if start >= limit else 0)
            elif op == "!=":
                q = (limit - start) / amount
                n = int(round(q)) if q >= 0 and abs(q - round(q)) < eps else None
            else:
                return None
        elif kind in ("mul", "div"):
            # geometric steps (v *= 2.) grow fast: simulate rather than fight logarithm rounding
            factor = amount if kind == "mul" else (1 / amount if amount else 0)
            if start <= 0 or factor <= 0 or factor == 1:
                return None
            test = {"<": lambda v: v < limit, "<=": lambda v: v <= limit * (1 + eps),
                    ">": lambda v: v > limit, ">=": lambda v: v >= limit * (1 - eps)}.get(op)
            if test is None:
                return None
            v, n = start, 0
            while test(v):
                n += 1
                v *= factor
                if n > GEOMETRIC_CAP:
                    return None
        else:
            return None
    except (ZeroDivisionError, ValueError, OverflowError, TypeError):
        return None
    if n is None:
        return None
    n = max(0, int(n))
    return n if n <= UNKNOWN_BOUND_CAP else None


# ---------- one pass as the compiler sees it ----------

class Unit:
    """The programs one pass compiles, in order (Common first). Function lookups see all of them; entry points come
    from the last (the pass itself): a function named like one (ENTRY_POINTS), else top-level code that calls functions
    (a mainImage built by a function-like macro). With neither, it depends on what the last program is:

    library=True   a file read on its own (`dissect file.glsl`): a library, whose user may call any function it defines,
                   so every one of them is an entry point.
    library=False  a Shadertoy pass: Shadertoy calls its mainImage (mainSound, mainCubemap) and nothing else, so a helper
                   runs only when the entry calls it. When the reader cannot find the entry (an object-like macro Common
                   defines builds it), nothing in the pass is known to run: there is no entry point, nothing is
                   reached, and every function the pass defines is listed as unreached by any entry point found."""

    def __init__(self, programs: Sequence[Program], library: bool = True):
        self.library = library
        self.programs = [p for p in programs if p is not None]
        self.functions: Dict[str, List[Fn]] = {}
        self.macros: Dict[str, Fn] = {}
        for p in self.programs:
            for name, fns in p.functions.items():
                self.functions.setdefault(name, []).extend(fns)
            self.macros.update(p.macros)
        if not any(e in self.program.functions for e in ENTRY_POINTS) and self.program.toplevel.calls:
            # no entry point among the functions: the top-level code is the entry (mainImage built by a macro)
            self.functions[TOPLEVEL] = [self.program.toplevel]
        self._calls: Dict[Fn, List[Call]] = {}
        self._summaries: Dict[str, Tuple[Dict[tuple, int], FrozenSet[str]]] = {}
        self.graph = self._graph()

    @property
    def program(self) -> Program:
        return self.programs[-1]

    def callables(self) -> Set[str]:
        return set(self.functions) | set(self.macros)

    def nodes(self, name: str) -> List[Fn]:
        """The definitions behind a name: a function's overloads, or the macro."""
        if name in self.functions:
            return self.functions[name]
        return [self.macros[name]] if name in self.macros else []

    def calls(self, fn: Fn) -> List[Call]:
        """fn's calls once macros expand: its own (Fn.calls), and, at each call it makes of a function-like macro whose
        expansion calls one of its parameters, the name fn passes in that parameter's position, whatever the names:
        with `#define APPLY(f, x) f(x)`, `APPLY(bend, u.x)` in mainImage is mainImage calling bend. Each is a Call at
        the argument's token, or at the macro call for a name the macro body writes (so it sits in the caller's
        loops), once per call the expansion makes (`f(f(x))` is two), with no arguments of its own (they are written in
        the macro). The rules, each as the preprocessor has it:

          * the name called is the argument's LAST token, which the expansion puts before '(' (_arg_last_name):
            APPLY(-bend, x) is -bend(x) and APPLY(0.5 * bend, x) is 0.5 * bend(x); an argument ending in a number, a
            ')' or a field after '.' names no call;
          * an argument is expanded before it is substituted, so an object-like macro whose whole body is one name
            stands for that name (`#define WHICH bend`: APPLY(WHICH, x) calls bend; Unit._alias);
          * a function-like macro passed in a called position is expanded with the arguments the body writes there,
            bound by position (`#define HAND(m, g, a) m(g, a)`: HAND(APPLY, bend, x) is APPLY(bend, x), so it calls
            APPLY and bend); a macro handing its own parameter on, bare or in an expression, is followed the same way
            (`#define OUTER(g, y) APPLY(-g, y)`: OUTER(bend, x) calls bend), and such a parameter is never the
            macro's own call, only its callers' (Unit._summary);
          * a macro is never expanded inside its own expansion: AGAIN(f, x) f(x) + AGAIN(bend, x) calls bend only if
            its caller passes it, and HAND(HAND, bend, x) leaves HAND(bend, x) unexpanded;
          * a parameter the body never calls is no call, whatever is passed there.

        Known limits, each with its probe (only the first moves a corpus row: 4dS3Wd lists fbm unreached):
          * a one-name macro called directly is not followed: `#define NOISE fbm`, then NOISE(p) leaves fbm unreached;
          * a '(' not written right after the parameter: `#define PASS(f) f`, then PASS(bend)(x) leaves bend unreached;
          * only a one-name body is followed: APPLY(NEG, x) with `#define NEG -bend` leaves bend unreached;
          * a macro call as the argument: APPLY(PICK(), x) with `#define PICK() bend` leaves bend unreached;
          * token pasting is read as plain tokens: V(bend) with `#define V(f) v##f(x)` calls bend, not vbend."""
        got = self._calls.get(fn)
        if got is None:
            got = list(fn.calls)
            own, opening = (fn.param_names, frozenset((fn.name,))) if fn.kind == "macro" else (set(), frozenset())
            for c in fn.calls:
                if not self._function_like(c.name):
                    continue
                env = []
                for rng in _arg_ranges(fn, c):
                    j = _arg_last_name(fn, rng)
                    t = fn.toks[j] if j is not None else None
                    # a macro's own parameter handed on is its callers' call (Unit._summary), never its own
                    env.append(None if t is None or t.text in own else ("n", self._alias(t.text), j, t.line))
                for v, times, _, _ in self._expand(c.name, tuple(env), opening, set()):
                    if v[0] != "n":
                        continue
                    _, name, idx, line = v
                    if idx is None:                  # a name written inside a macro body: the call is at the use
                        idx, line = c.idx, c.line
                    builtin = name in BUILTIN_FUNCTIONS or name in TYPES
                    got.extend(Call(name, idx, line, [], builtin) for _ in range(times))
            self._calls[fn] = got
        return got

    def _function_like(self, name: str) -> bool:
        m = self.macros.get(name)
        return m is not None and not m.object_like

    def _alias(self, name: str) -> str:
        """What an argument naming an object-like macro stands for once arguments are expanded: the one name that is
        the macro's whole body (`#define WHICH bend` stands for bend), followed through such macros, never into one
        already followed; anything else stands for itself."""
        seen: Set[str] = set()
        while name not in seen:
            m = self.macros.get(name)
            if m is None or not m.object_like or m.end - m.start != 1 or m.toks[m.start].kind != IDENT:
                break
            seen.add(name)
            name = m.toks[m.start].text
        return name

    def _expand(self, name: str, env: tuple, opening: FrozenSet[str], met: Set[str], times: int = 1,
                chain: FrozenSet[str] = frozenset()) -> Iterator[tuple]:
        """The calls the expansion of the function-like macro `name` makes of what its arguments carry. `env` holds one
        value per argument position: ("p", i), the i-th parameter of a macro being summarised; ("n", name, idx, line),
        a name (idx None when it is written inside a macro body); or None, nothing that can be called. Yields
        (value, times, via, args) per call: via is every macro whose expansion the call sits in, args the call's own
        argument values. A value naming a function-like macro is expanded in turn with those args, inside every macro
        of via (so none of them expands again). `met` gathers each macro the walk checked against `opening`."""
        recs, seen = self._summary(name, opening)
        met.update(seen)
        for (i, via, argv), t in sorted(recs.items(), key=lambda kv: kv[0][0]):
            v = env[i] if i < len(env) else None
            if v is None:
                continue
            n, via = times * t, chain | via
            args = tuple(env[a[1]] if a is not None and a[0] == "p" and a[1] < len(env)
                         else (a if a is not None and a[0] == "n" else None) for a in argv)
            yield v, n, via, args
            if v[0] == "n" and self._function_like(v[1]):
                yield from self._expand(v[1], args, opening | via, met, n, via)

    def _summary(self, name: str, opening: FrozenSet[str] = frozenset()) -> Tuple[Dict[tuple, int], FrozenSet[str]]:
        """What the function-like macro `name` calls through its own parameters when expanded: a count per
        (parameter position called, via, argument values of that call, in the same ("p", i) / ("n", ...) terms as
        Unit._expand). Its own calls of them (Fn.param_calls), plus each it hands on to another macro, bare or ending an
        expression, that calls it there or passes it to a macro it is handed (`#define OUTER(g, y) APPLY(-g, y)` calls
        g). Names the body itself writes are the macro's own calls (Unit.calls), not counted here. `opening` holds the
        macros whose expansion this one sits in: the preprocessor never expands a macro inside its own expansion, so
        one of those adds nothing. The second value is every macro the expansion met; an answer kept from an expansion
        that met none of `opening` is the same here, and only such answers are kept."""
        m = self.macros.get(name)
        if m is None or m.object_like or not m.params:
            return {}, frozenset()
        if name in opening:
            return {}, frozenset((name,))
        kept = self._summaries.get(name)
        if kept is not None and not kept[1] & opening:
            return kept
        pos = {p.name: i for i, p in enumerate(m.params) if p.name}
        here = frozenset((name,))

        def value(rng: Tuple[int, int]):
            j = _arg_last_name(m, rng)
            if j is None:
                return None
            t = m.toks[j].text
            return ("p", pos[t]) if t in pos else ("n", self._alias(t), None, None)

        recs: Dict[tuple, int] = {}
        for pc in m.param_calls:
            key = (pos[pc.name], here, tuple(value(r) for r in _arg_ranges(m, pc)))
            recs[key] = recs.get(key, 0) + 1
        met: Set[str] = {name}
        for c in m.calls:
            if not self._function_like(c.name):
                continue
            env = tuple(value(r) for r in _arg_ranges(m, c))
            for v, times, via, args in self._expand(c.name, env, opening | here, met):
                if v[0] == "p":
                    key = (v[1], via | here, args)
                    recs[key] = recs.get(key, 0) + times
        answer = (recs, frozenset(met))
        if not met & opening:
            self._summaries[name] = answer
        return answer

    def _graph(self) -> Dict[str, Set[str]]:
        names = self.callables()
        g: Dict[str, Set[str]] = {}
        for name in names:
            out: Set[str] = set()
            for fn in self.nodes(name):
                # fn.calls and fn.idents leave out the body's own parameters (_analyse_fn): a parameter named like a
                # macro or a function is never a use of it. What a caller passes to a macro that calls it is the
                # caller's call (Unit.calls).
                out.update(c.name for c in self.calls(fn) if c.name in names)
                out.update(i for i in fn.idents if i in self.macros)
            out.discard(name)
            g[name] = out
        return g

    def entries(self) -> List[str]:
        own = self.program.functions
        found = [e for e in ENTRY_POINTS if e in own]
        if found:
            return found
        if TOPLEVEL in self.functions:
            return [TOPLEVEL]
        return sorted(own) if self.library else []

    def reachable(self, entries: Optional[Iterable[str]] = None) -> Set[str]:
        stack = list(self.entries() if entries is None else entries)
        seen: Set[str] = set()
        while stack:
            n = stack.pop()
            if n in seen or n not in self.graph:
                continue
            seen.add(n)
            stack.extend(self.graph[n])
        return seen

    def dead(self) -> List[Fn]:
        """Functions of the pass's own program that no entry point reaches."""
        live = self.reachable()
        return [fn for fn in self.program.all_functions() if fn.name not in live]

    def value_of(self, name: str):
        return self.program.value_of(name)


def call_graph(unit: Unit) -> Dict[str, List[str]]:
    return {k: sorted(v) for k, v in sorted(unit.graph.items())}


def parse(src: str, file: str = "image.glsl", base: Optional[Program] = None) -> Program:
    return Program(src, file=file, base=base)
