"""The param schema's Python twin: validate, the URL codec, the unit-aware formatter, slider curves, the descriptor check
and params_from_module, matching arsenal/web/lib/params.js rule for rule.

Why a twin: one descriptor describes a knob everywhere it appears -- the GLSL uniform, the slider, the URL, the preset --
and Python is where renders, receipts and the preset store live. If the two sides disagreed, a preset saved in the page
would be refused or silently changed by a render. tests/fixtures/params/verdicts.json pins both: tests/test_params_schema.py
runs it here, tests/params_schema.test.mjs runs it in node. Change a rule in one twin and the same rule in the other.

The rules (the JS header says the same):
  - Numbers snap to the step grid counted from min, rounding half up; without a step they keep 6 decimals, or as many as
    min and max need (up to 9), and rounding never takes them out of the range (count and bits imply a step of 1). Out
    of range clamps and is a problem; a snap is not.
  - A missing value takes the default without a problem; None, a wrong type or an unknown choice takes the default and is
    a problem. Unknown keys are dropped and listed, sorted.
  - A derived param is computed from the others after they are validated; a value given for it is ignored. Its
    expression has at most MAX_TOKENS tokens.
  - Arithmetic is plain IEEE doubles in the same order as the JS twin, and decimal text is built from integers, never
    from format() (which rounds ties to even where JS's toFixed does not). An int is read as the double JSON.parse
    would make of it: one too big for a float is an infinity, and choices and range ends compare as doubles.
  - The descriptor check refuses choices that are not distinct both as values and as URL text, and a uniform the host
    binds itself (HOUSE_UNIFORMS).
  - A bool is never a number here (Python's True == 1 would otherwise let a toggle pass as a range).
  - Message text and problem order match the JS twin even on unusual input: unknown keys sort by UTF-16 code units.

Python callers get ints back for values on an integer grid (count, bits, a step of 1 from an integer min), so a render can
bind them to an int uniform without a cast; JSON and the fixture see the same numbers either way.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

PARAMS_API = "arsenal.params/v1"
# The house refusal text for a control locked while recording (the looks registry's REC_BLOCKED; a test keeps them equal).
REC_REFUSAL_TEXT = "Stop recording to change this."

TYPES = ("range", "choice", "toggle", "colour", "vec")
CURVES = ("linear", "log", "exp")
NUMERIC_UNITS = ("ratio", "px", "world", "rad", "turns", "deg", "hz", "sec", "per-sec", "stops", "kelvin", "nm", "db",
                 "count", "bits")
_UNIT_SYMBOL = {"ratio": "", "px": "px", "world": "units", "rad": "rad", "turns": "turns", "deg": "°", "hz": "Hz",
                "sec": "s", "per-sec": "/s", "stops": "stops", "kelvin": "K", "nm": "nm", "db": "dB", "count": "",
                "bits": "bits"}
_TIGHT = {"%", "°", "×", "/s"}
_SIGNED = {"stops", "db"}
_INTEGER_UNITS = {"count", "bits"}
_EPS = 1e-6
_P10 = [1.0, 10.0, 100.0, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9]
_FREE_DECIMALS = 6
_EXP_K = 4.0
_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.]*")
_INSTANCE_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_UNIFORM_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# The uniforms the shader host binds on every surface (unified architecture draft, section 6); a param never takes one.
HOUSE_UNIFORMS = ("u_res", "u_time", "u_dt", "u_frame", "u_mouse")
_NUM_RE = re.compile(r"[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?")
_SAFE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~,:")
_MISSING = object()


def _as_double(x) -> float:
    """A number as the double JavaScript would hold: an int too big for a float (json.loads makes 10**400 from 1 and 400
    zeros, where JSON.parse makes Infinity) is an infinity, never an OverflowError."""
    try:
        return float(x)
    except OverflowError:
        return math.inf if x > 0 else -math.inf


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(_as_double(v))


def _round_half_up(x: float) -> int:
    return math.floor(x + 0.5)


def _clamp(x, a, b):
    return min(max(x, a), b)


# ------------------------------------------------------------------------------------------------ decimal text --
def decimals_of(x: float) -> int:
    """How many decimals a number needs (0.05 -> 2, 100 -> 0, 1e-7 -> 7), up to 9. A scaled value that still rounds to
    zero is never "close enough": without that rule 1e-7 counted as a whole number and a step of 1e-7 snapped 0.5 to 1."""
    a = abs(float(x))
    for d, p in enumerate(_P10):
        s = a * p
        n = _round_half_up(s)
        if n == 0 and a != 0:
            continue
        if abs(s - n) < 1e-6:
            return d
    return len(_P10) - 1


def _fixed(x: float, dec: int) -> str:
    """x with exactly `dec` decimals, rounded half away from zero, built from an integer (same text as the JS twin)."""
    x = float(x)
    d = dec
    while d > 0 and abs(x) * _P10[d] >= 1e15:
        d -= 1
    n = _round_half_up(abs(x) * _P10[d])
    if n == 0:
        return "0." + "0" * d if d else "0"
    digits = str(n).rjust(d + 1, "0")
    body = digits[:len(digits) - d] + "." + digits[len(digits) - d:] if d else digits
    return ("-" if x < 0 else "") + body


def _strip(s: str) -> str:
    return s.rstrip("0").rstrip(".") if "." in s else s


def _round_to(x: float, dec: int):
    n = _round_half_up(abs(float(x)) * _P10[dec])
    if n == 0:
        return 0 if dec == 0 else 0.0
    if dec == 0:
        return -n if x < 0 else n
    return (-n if x < 0 else n) / _P10[dec]


def _num_text(x) -> str:
    return _strip(_fixed(x, _FREE_DECIMALS))


def _show(v) -> str:
    """A value as plain words for a message, the same on both twins."""
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        x = _as_double(v)
        if math.isfinite(x):
            return _num_text(x)
        return "NaN" if math.isnan(x) else ("Infinity" if x > 0 else "-Infinity")
    if v is None:
        return "null"
    return "a list" if isinstance(v, (list, tuple)) else "an object"


# ------------------------------------------------------------------------------------------------- descriptors --
def _implied_unit(t):
    return {"toggle": "bool", "choice": "choice", "colour": "colour"}.get(t)


def _clone(v):
    if isinstance(v, (list, tuple)):
        return [_clone(x) for x in v]
    if isinstance(v, dict):
        return {k: _clone(x) for k, x in v.items()}
    return v


def normalize_descriptor(d: dict) -> dict:
    """Every field of the shape present, nothing shared with the input."""
    t = d.get("type")
    rng = None
    r = d.get("range")
    if isinstance(r, dict) and t in ("range", "vec", "colour"):
        rng = {"min": r.get("min"), "max": r.get("max"), "step": r.get("step")}
    vals = None
    if t == "choice" and isinstance(d.get("values"), list):
        vals = [{"value": (o or {}).get("value"), "label": (o or {}).get("label")} for o in d["values"]]
    order = d.get("order")
    return {
        "id": d.get("id"), "group": d.get("group") if d.get("group") is not None else "params",
        "label": d.get("label") if d.get("label") is not None else d.get("id"), "type": t,
        "unit": d.get("unit") if d.get("unit") is not None else _implied_unit(t), "range": rng,
        "default": _clone(d.get("default")), "curve": d.get("curve") if d.get("curve") is not None else "linear",
        "values": vals, "help": d.get("help") if d.get("help") is not None else "", "recBlocked": bool(d.get("recBlocked")),
        "order": order if _is_num(order) else 0, "uniform": d.get("uniform"), "derived": d.get("derived"),
        "cost": bool(d.get("cost")), "source": dict(d["source"]) if isinstance(d.get("source"), dict) else None,
    }


def _bounds(d: dict):
    """(min, max) as the doubles the JS twin holds (2**60 + 1 is 2**60 there), so every comparison and every curve
    agrees with it; a missing or non-numeric end is passed through for the caller to refuse."""
    r = d.get("range") if isinstance(d.get("range"), dict) else {}
    lo, hi = r.get("min"), r.get("max")
    if d.get("type") == "colour":
        return (_as_double(lo) if _is_num(lo) else 0, _as_double(hi) if _is_num(hi) else 1)
    return (_as_double(lo) if _is_num(lo) else lo), (_as_double(hi) if _is_num(hi) else hi)


def _grid(d: dict):
    """The grid a value snaps to: (step or None, decimals that keep grid points exact). Without a step,
    _FREE_DECIMALS or as many as min and max need (up to 9): [1e-7, 1e-3] at 6 decimals turned its own min into 0."""
    r = d.get("range") if isinstance(d.get("range"), dict) else {}
    step = r.get("step") if _is_num(r.get("step")) and r.get("step") > 0 else None
    if step is None and d.get("unit") in _INTEGER_UNITS:
        step = 1
    lo, hi = _bounds(d)
    ends = max(decimals_of(lo) if _is_num(lo) else 0, decimals_of(hi) if _is_num(hi) else 0)
    if step is None:
        return None, max(_FREE_DECIMALS, ends)
    return step, max(decimals_of(step), ends)


def _quantise(x, lo, hi, grid):
    step, dec = grid
    v = _clamp(float(x), lo, hi)
    if step is not None:
        v = lo + _round_half_up((v - lo) / step) * step
    v = _round_to(v, dec)
    if v > hi and step is not None:
        v = _round_to(v - step, dec)
    if step is None:
        v = _clamp(v, lo, hi)   # an end past 9 decimals: rounding must not leave the range
    return v + 0  # never -0.0


def _default_of(d: dict):
    v = d.get("default")
    t = d.get("type")
    if t == "range" and _is_num(v):
        lo, hi = _bounds(d)
        return _quantise(v, lo, hi, _grid(d))
    if t in ("vec", "colour") and isinstance(v, (list, tuple)):
        lo, hi = _bounds(d)
        g = _grid(d)
        return [_quantise(x, lo, hi, g) if _is_num(x) else x for x in v]
    return _clone(v)


def _same_choice(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        # Compared as doubles, as the JS twin must: 2**60 + 1 and 2**60 are one number once JSON.parse has read them.
        return _as_double(a) == _as_double(b)
    return isinstance(a, str) and isinstance(b, str) and a == b


def _same_value(a, b) -> bool:
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(
            _same_scalar(x, y) for x, y in zip(a, b))
    return _same_scalar(a, b)


def _same_scalar(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    return a == b


def _problem(pid, code, message):
    return {"id": pid, "code": code, "message": message}


def _utf16_key(k) -> bytes:
    return str(k).encode("utf-16-be", "surrogatepass")


# -------------------------------------------------------------------------------------------------- validation --
def validate_value(d: dict, value=_MISSING) -> dict:
    """One value against one descriptor -> {value, problem}. Leave `value` out for "not given"."""
    label = d.get("label") if d.get("label") is not None else d.get("id")
    t = d.get("type")

    def fallback(code, message):
        return {"value": _default_of(d), "problem": _problem(d.get("id"), code, message)}

    if value is _MISSING:
        return {"value": _default_of(d), "problem": None}
    if t == "toggle":
        return {"value": value, "problem": None} if isinstance(value, bool) else fallback("type", f"{label} must be on or off.")
    if t == "choice":
        for o in d.get("values") or []:
            if _same_choice(o.get("value"), value):
                return {"value": o.get("value"), "problem": None}
        return fallback("choice", f'{label} "{_show(value)[:40]}" is not one of its choices.')
    if t in ("vec", "colour"):
        n = 3 if t == "colour" else (len(d["default"]) if isinstance(d.get("default"), list) else 0)
        if not isinstance(value, (list, tuple)):
            return fallback("type", f"{label} must be {n} numbers.")
        if len(value) != n:
            return fallback("length", f"{label} must have {n} parts.")
        if not all(_is_num(x) for x in value):
            return fallback("type", f"{label} must be {n} numbers.")
        lo, hi = _bounds(d)
        g = _grid(d)
        nums = [float(x) for x in value]   # the doubles the JS twin holds (2**60 + 1 is 2**60 there)
        out = [_quantise(x, lo, hi, g) for x in nums]
        if any(x < lo - _EPS or x > hi + _EPS for x in nums):
            if t == "colour":
                message = (f"{label} channels must be from {_num_text(lo)} to {_num_text(hi)}; "
                           f"using {', '.join(_num_text(x) for x in out)}.")
            else:
                scalar = {**d, "type": "range"}
                message = (f"{label} must be from {format_value(scalar, lo)} to {format_value(scalar, hi)}; "
                           f"using {format_value(d, out)}.")
            return {"value": out, "problem": _problem(d.get("id"), "range", message)}
        return {"value": out, "problem": None}
    if not _is_num(value):
        return fallback("type", f"{label} must be a number.")
    value = float(value)   # the double the JS twin holds (2**60 + 1 is 2**60 there)
    lo, hi = _bounds(d)
    out = _quantise(value, lo, hi, _grid(d))
    if value < lo - _EPS or value > hi + _EPS:
        return {"value": out, "problem": _problem(
            d.get("id"), "range",
            f"{label} must be from {format_value(d, lo)} to {format_value(d, hi)}; using {format_value(d, out)}.")}
    return {"value": out, "problem": None}


def validate(descriptors, values) -> dict:
    """Every descriptor gets a legal value (given, snapped, clamped or defaulted), derived params are computed, and every
    departure from what was given is a problem -> {ok, values, problems}."""
    items = descriptors if isinstance(descriptors, list) else []
    lead = []
    src = values
    if src is None:
        src = {}
    elif not isinstance(src, dict):
        lead.append(_problem("", "values", "Settings must be an object of names and values."))
        src = {}
    out: Dict[str, Any] = {}
    per: List[Optional[dict]] = [None] * len(items)
    for i, d in enumerate(items):
        if d.get("derived"):
            out[d["id"]] = None
            continue
        r = validate_value(d, src[d["id"]] if d["id"] in src else _MISSING)
        out[d["id"]] = r["value"]
        per[i] = r["problem"]
    for i, d in enumerate(items):
        if not d.get("derived"):
            continue
        x = _evaluate(d["derived"], out)
        if _is_num(x):
            lo, hi = _bounds(d)
            out[d["id"]] = _quantise(x, lo, hi, _grid(d))
            continue
        out[d["id"]] = _default_of(d)
        label = d.get("label") if d.get("label") is not None else d["id"]
        per[i] = _problem(d["id"], "derived", f"{label} could not be worked out from {d['derived']}; using its default.")
    known = {d["id"] for d in items}
    # Sorted by UTF-16 code units, as JavaScript's sort() orders them (by code point "Ａ" would come before "😀").
    unknown = [_problem(k, "unknown", f"{k} is not a setting here.")
               for k in sorted((k for k in src if k not in known), key=_utf16_key)]
    problems = lead + [p for p in per if p] + unknown
    return {"ok": not problems, "values": out, "problems": problems}


# ------------------------------------------------------------------------------------------ derived expressions --
_FUNCS = {"min": (2, math.inf), "max": (2, math.inf), "clamp": (3, 3), "abs": (1, 1), "floor": (1, 1)}
# At most this many tokens (the JS twin's MAX_TOKENS): a derived param is a short formula, and the cap bounds how deep the
# parser and evaluator recurse, so this twin refuses what the JS twin refuses instead of hitting the recursion limit.
MAX_TOKENS = 128
_TOK_NUM = re.compile(r"[0-9]+(\.[0-9]+)?|\.[0-9]+")
_TOK_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")


class _ExprError(ValueError):
    pass


def _tokenize(src: str):
    out, i = [], 0
    while i < len(src):
        c = src[i]
        if c in " \t":
            i += 1
            continue
        if len(out) == MAX_TOKENS:   # a token past the cap starts here
            raise _ExprError(f"longer than {MAX_TOKENS} tokens")
        m = _TOK_NUM.match(src, i)
        if m:
            out.append(("num", float(m.group(0))))
            i = m.end()
            continue
        m = _TOK_ID.match(src, i)
        if m:
            out.append(("id", m.group(0)))
            i = m.end()
            continue
        if c in "+-*/(),":
            out.append((c, None))
            i += 1
            continue
        raise _ExprError(f'unexpected "{c}"')
    return out


def _parse_expr(src: str):
    toks = _tokenize(str(src))
    k = 0

    def peek():
        return toks[k][0] if k < len(toks) else "end"

    def take(t):
        nonlocal k
        if peek() != t:
            raise _ExprError(f"expected {t}")
        k += 1

    def expr():
        nonlocal k
        a = term()
        while peek() in ("+", "-"):
            op = toks[k][0]
            k += 1
            a = ("bin", op, a, term())
        return a

    def term():
        nonlocal k
        a = unary()
        while peek() in ("*", "/"):
            op = toks[k][0]
            k += 1
            a = ("bin", op, a, unary())
        return a

    def unary():
        nonlocal k
        if peek() == "-":
            k += 1
            return ("neg", unary())
        return primary()

    def primary():
        nonlocal k
        t = peek()
        if t == "num":
            v = toks[k][1]
            k += 1
            return ("num", v)
        if t == "(":
            k += 1
            e = expr()
            take(")")
            return e
        if t == "id":
            name = toks[k][1]
            k += 1
            if peek() != "(":
                return ("id", name)
            k += 1
            args = []
            if peek() != ")":
                args.append(expr())
                while peek() == ",":
                    k += 1
                    args.append(expr())
            take(")")
            arity = _FUNCS.get(name)
            if not arity:
                raise _ExprError(f"no function called {name}")
            if len(args) < arity[0] or len(args) > arity[1]:
                raise _ExprError(f"{name} takes {arity[0]} arguments")
            return ("call", name, args)
        raise _ExprError("expected a number, a name or (")

    tree = expr()
    if k != len(toks):
        raise _ExprError("unexpected text at the end")
    return tree


def _ids_in(node, out=None):
    out = [] if out is None else out
    kind = node[0]
    if kind == "id":
        out.append(node[1])
    elif kind == "neg":
        _ids_in(node[1], out)
    elif kind == "bin":
        _ids_in(node[2], out)
        _ids_in(node[3], out)
    elif kind == "call":
        for a in node[2]:
            _ids_in(a, out)
    return out


def _run(node, env):
    kind = node[0]
    if kind == "num":
        v = node[1]
    elif kind == "id":
        v = env.get(node[1])
    elif kind == "neg":
        v = -_run(node[1], env)
    elif kind == "bin":
        a, b = _run(node[2], env), _run(node[3], env)
        op = node[1]
        if op == "/":
            if b == 0:
                raise _ExprError("division by zero")
            v = a / b
        else:
            v = a + b if op == "+" else a - b if op == "-" else a * b
    else:
        xs = [_run(a, env) for a in node[2]]
        f = node[1]
        v = (min(xs) if f == "min" else max(xs) if f == "max" else _clamp(xs[0], xs[1], xs[2]) if f == "clamp"
             else abs(xs[0]) if f == "abs" else float(math.floor(xs[0])))
    if not _is_num(v):
        raise _ExprError("not a finite number")
    return float(v)


_PARSED: Dict[str, Any] = {}


def _evaluate(src: str, env: dict) -> float:
    try:
        if src not in _PARSED:
            _PARSED[src] = _parse_expr(src)
        return _run(_PARSED[src], env)
    except (_ExprError, OverflowError, TypeError, RecursionError):   # RecursionError: belt and braces under the cap
        return math.nan


# ------------------------------------------------------------------------------------------- descriptor check --
def check_descriptors(descriptors) -> List[dict]:
    """What is wrong with the descriptors themselves -> [{id, code, message}]. Codes per descriptor, in this order: id or
    duplicate, type, unit, range, curve, values, default, derived, uniform (the JS twin keeps the same order)."""
    if not isinstance(descriptors, list):
        return [_problem("", "descriptors", "Descriptors must be a list.")]
    out: List[dict] = []
    seen, uniforms = set(), set()
    by_id: Dict[str, dict] = {}
    for d in descriptors:
        if isinstance(d, dict) and isinstance(d.get("id"), str) and d["id"] not in by_id:
            by_id[d["id"]] = d
    for d in descriptors:
        pid = d["id"] if isinstance(d, dict) and isinstance(d.get("id"), str) else ""

        def add(code, message):
            out.append(_problem(pid, code, message))

        if not isinstance(d, dict):
            add("descriptor", "A descriptor must be an object.")
            continue
        if not _ID_RE.fullmatch(pid):
            add("id", f'"{pid}" is not a usable id (a letter, then letters, digits, _ or .).')
        elif pid in seen:
            add("duplicate", f"{pid} is described twice.")
        seen.add(pid)
        t = d.get("type")
        if t not in TYPES:
            add("type", f"{pid} has no known type ({', '.join(TYPES)}).")
            continue
        numeric = t in ("range", "vec")
        unit = d.get("unit")
        if numeric:
            if unit is None:
                add("unit", f"{pid} needs a unit (the number means nothing without one).")
            elif unit not in NUMERIC_UNITS:
                add("unit", f'{pid} has an unknown unit "{_show(unit)}".')
        elif unit is not None and unit != _implied_unit(t):
            add("unit", f'a {t} takes the unit "{_implied_unit(t)}" or none.')
        r = d.get("range")
        step = r.get("step") if isinstance(r, dict) else None
        # min below max as the doubles JSON.parse makes: 2**60 and 2**60 + 1 are one number to the JS twin
        shape_ok = (isinstance(r, dict) and _is_num(r.get("min")) and _is_num(r.get("max"))
                    and _as_double(r["min"]) < _as_double(r["max"]) and (step is None or (_is_num(step) and step > 0)))
        range_ok = False
        if numeric:
            if shape_ok:
                range_ok = True
            else:
                add("range", f"{pid} needs a range with min below max and a positive step.")
        elif t == "colour":
            if r is None or shape_ok:
                range_ok = True
            else:
                add("range", f"{pid} has a broken range.")
        curve = d.get("curve") if d.get("curve") is not None else "linear"
        if curve not in CURVES:
            add("curve", f'{pid} has an unknown curve "{_show(curve)}".')
        elif curve == "log" and not (range_ok and r["min"] > 0):
            add("curve", f"{pid}: a log curve needs a range above zero.")
        values_ok = True
        if t == "choice":
            vs = d.get("values")
            values_ok = (isinstance(vs, list) and len(vs) > 0
                         and all(isinstance(o, dict) and isinstance(o.get("label"), str)
                                 and (isinstance(o.get("value"), str) or _is_num(o.get("value"))) for o in vs)
                         and all(next(j for j, p in enumerate(vs) if _same_choice(p.get("value"), o.get("value"))) == i
                                 for i, o in enumerate(vs))
                         # distinct as URL text too: "1" and 1 both write x=1, and the URL brings back only the first
                         and len({codec_text(d, o.get("value")) for o in vs}) == len(vs))
            if not values_ok:
                add("values", f"{pid} needs a list of distinct choices, each a value and a label.")
        if not _default_ok(d, range_ok, values_ok):
            add("default", f"{pid} has a default that is not one of its own legal values.")
        if d.get("derived") is not None:
            bad = t != "range" or not isinstance(d["derived"], str)
            if not bad:
                try:
                    for name in _ids_in(_parse_expr(d["derived"])):
                        target = by_id.get(name)
                        if target is None or target is d or target.get("derived") or target.get("type") != "range":
                            bad = True
                except (_ExprError, RecursionError):
                    bad = True
            if bad:
                add("derived", f"{pid} is derived from something that is not a plain number param here.")
        if d.get("uniform") is not None:
            u = d["uniform"]
            if not isinstance(u, str) or not _UNIFORM_RE.fullmatch(u) or u.startswith("gl_") or "__" in u:
                add("uniform", f'{pid}: "{_show(u)}" is not a GLSL name a uniform can have.')
            elif u in HOUSE_UNIFORMS:
                add("uniform", f"{pid}: {u} is a house uniform the host binds itself.")
            elif u in uniforms:
                add("uniform", f"{pid}: the uniform {u} is already bound to another param.")
            else:
                uniforms.add(u)
    return out


def _default_ok(d, range_ok, values_ok) -> bool:
    v = d.get("default")
    t = d.get("type")
    if t == "toggle":
        return isinstance(v, bool)
    if t == "choice":
        return values_ok and any(_same_choice(o.get("value"), v) for o in d["values"])
    lo, hi = _bounds(d)

    def inside(x):
        return _is_num(x) and (not range_ok or lo - _EPS <= float(x) <= hi + _EPS)

    if t == "range":
        return inside(v)
    if t == "colour":
        return isinstance(v, list) and len(v) == 3 and all(inside(x) for x in v)
    return isinstance(v, list) and 2 <= len(v) <= 4 and all(inside(x) for x in v)


# ---------------------------------------------------------------------------------------- params from a module --
def _type_of_param(p: dict) -> str:
    if p.get("type") in TYPES:
        return p["type"]
    if isinstance(p.get("choices"), list):
        return "choice"
    if p.get("unit") == "bool":
        return "toggle"
    if p.get("unit") == "colour":
        return "colour"
    if isinstance(p.get("default"), list):
        return "vec"
    return "range"


def _choices_of(p: dict):
    out = []
    for i, c in enumerate(p["choices"]):
        if isinstance(c, dict):
            out.append({"value": c.get("value"), "label": str(c["label"] if c.get("label") is not None else c.get("value"))})
        elif isinstance(c, str):
            out.append({"value": i, "label": c})
        else:
            out.append({"value": c, "label": _show(c)})
    return out


def _namespace_expr(src: str, names, inst: str) -> str:
    def swap(m):
        j = m.end()
        while j < len(src) and src[j] in " \t":
            j += 1
        nxt = src[j] if j < len(src) else ""
        return f"{inst}.{m.group(0)}" if m.group(0) in names and nxt != "(" else m.group(0)
    return _TOK_ID.sub(swap, src)


def params_from_module(header: dict, instance_id: Optional[str] = None) -> List[dict]:
    """Descriptors for a recipe's `params`, one per entry argument in header order. With an instance id every uniform is
    namespaced (u_<instance>_<name>) and every id is <instance>.<name>, so two instances of one recipe never share a
    slider; with None a single-instance surface binds short names (u_<name>, or the uniform its header declares)."""
    if instance_id is not None and not (isinstance(instance_id, str) and _INSTANCE_RE.fullmatch(instance_id)):
        raise ValueError(f'instance id "{_show(instance_id)}" must be a letter then letters or digits (no _ or .)')
    inst = instance_id
    params = header.get("params") if isinstance(header, dict) and isinstance(header.get("params"), list) else []
    names = {p.get("name") for p in params if isinstance(p, dict) and isinstance(p.get("name"), str)}
    out = []
    for i, p in enumerate(params):
        # Without a string name there is no id or uniform to make ("None" here and "undefined" in JS would disagree).
        if not isinstance(p, dict) or not isinstance(p.get("name"), str):
            raise ValueError(f"param {i} of the header needs a name")
        name = p["name"]
        t = _type_of_param(p)
        rng = None
        if t in ("range", "vec") or (t == "colour" and p.get("range") is not None):
            r = p.get("range")
            lo, hi = (r[0], r[1]) if isinstance(r, list) else ((r or {}).get("min"), (r or {}).get("max"))
            step = p.get("step")
            if step is None and isinstance(r, dict):
                step = r.get("step")
            rng = {"min": lo, "max": hi, "step": step}
        group = p.get("group") if p.get("group") is not None else "params"
        derived = p.get("derived") if isinstance(p.get("derived"), str) and p.get("derived") else None
        if derived and inst:
            derived = _namespace_expr(derived, names, inst)
        out.append({
            "id": f"{inst}.{name}" if inst else name,
            "group": f"{inst}.{group}" if inst else group,
            "label": p.get("label") if p.get("label") is not None else name,
            "type": t,
            "unit": p.get("unit") if p.get("unit") is not None else _implied_unit(t),
            "range": rng,
            "default": _clone(p.get("default")),
            "curve": p.get("curve") if p.get("curve") is not None else "linear",
            "values": _choices_of(p) if t == "choice" else None,
            "help": p.get("help") if p.get("help") is not None else "",
            "recBlocked": bool(p.get("recBlocked")),
            "order": i,
            "uniform": f"u_{inst}_{name}" if inst else (p["uniform"] if isinstance(p.get("uniform"), str) else f"u_{name}"),
            "derived": derived,
            "cost": bool(p.get("cost")),
            "source": {"module": header.get("name") if isinstance(header.get("name"), str) else None,
                       "param": name, "instance": inst},
        })
    return out


# ------------------------------------------------------------------------------------------------ the formatter --
def _percent_mode(d) -> bool:
    return d.get("unit") == "ratio" and _bounds(d)[1] <= 1


def _symbol_of(d) -> str:
    if d.get("unit") == "ratio":
        return "%" if _percent_mode(d) else "×"
    return _UNIT_SYMBOL.get(d.get("unit"), "")


def _display_decimals(d) -> int:
    r = d.get("range") if isinstance(d.get("range"), dict) else {}
    step = r.get("step")
    if _is_num(step) and step > 0:
        return min(decimals_of(step), 4)
    return 0 if d.get("unit") in _INTEGER_UNITS else 2


def _shown_number(d, x) -> str:
    if not _is_num(x):
        return _show(x)
    dec, v = _display_decimals(d), float(x)
    if _percent_mode(d):
        v = v * 100
        dec = max(0, dec - 2)
    s = _fixed(v, dec)
    if d.get("unit") in _SIGNED and not s.startswith("-") and re.search(r"[1-9]", s):
        s = "+" + s
    return s


def _srgb_byte(x) -> str:
    c = _clamp(float(x), 0.0, 1.0) if _is_num(x) else 0.0
    e = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return format(_clamp(_round_half_up(e * 255), 0, 255), "02x")


def format_parts(d: dict, value) -> dict:
    """The number and its unit apart -> {text, unit}, for a readout that sets them side by side."""
    t = d.get("type")
    if t == "toggle":
        return {"text": "On" if value is True else "Off", "unit": ""}
    if t == "choice":
        for o in d.get("values") or []:
            if _same_choice(o.get("value"), value):
                return {"text": str(o.get("label")), "unit": ""}
        return {"text": _show(value), "unit": ""}
    if t == "colour":
        ok = isinstance(value, (list, tuple)) and len(value) == 3
        return {"text": "#" + "".join(_srgb_byte(x) for x in value) if ok else _show(value), "unit": ""}
    if t == "vec":
        text = ", ".join(_shown_number(d, x) for x in value) if isinstance(value, (list, tuple)) else _show(value)
        return {"text": text, "unit": _symbol_of(d)}
    return {"text": _shown_number(d, value), "unit": _symbol_of(d)}


def format_value(d: dict, value) -> str:
    """"40%", "+1.5 stops", "0.25, -0.50 units", "#ffbc89", "On", "ACES fit"."""
    parts = format_parts(d, value)
    text, unit = parts["text"], parts["unit"]
    if not unit:
        return text
    return text + unit if unit in _TIGHT else f"{text} {unit}"


# ---------------------------------------------------------------------------------------------- slider curves --
def position_to_value(d: dict, p: float) -> float:
    """A slider position in [0, 1] to a value (not yet snapped; validate_value snaps it)."""
    lo, hi = _bounds(d)
    t = _clamp(float(p), 0.0, 1.0) if _is_num(p) else 0.0
    curve = d.get("curve") or "linear"
    if curve == "log" and lo > 0 and hi > 0:
        return lo * (hi / lo) ** t
    if curve == "exp":
        return lo + (hi - lo) * (math.exp(_EXP_K * t) - 1) / (math.exp(_EXP_K) - 1)
    return lo + (hi - lo) * t


def value_to_position(d: dict, v: float) -> float:
    """The inverse of position_to_value, clamped to [0, 1]."""
    if not _is_num(v):
        return 0.0
    lo, hi = _bounds(d)
    if v <= lo:
        return 0.0
    if v >= hi:
        return 1.0
    curve = d.get("curve") or "linear"
    if curve == "log" and lo > 0 and hi > 0:
        return math.log(v / lo) / math.log(hi / lo)
    if curve == "exp":
        return math.log(1 + (v - lo) / (hi - lo) * (math.exp(_EXP_K) - 1)) / _EXP_K
    return (v - lo) / (hi - lo)


# ------------------------------------------------------------------------------------------------ the URL codec --
def _utf8(ch: str) -> bytes:
    if 0xD800 <= ord(ch) <= 0xDFFF:   # a lone surrogate: what TextEncoder writes for it
        ch = "�"
    return ch.encode("utf-8")


def _esc(s) -> str:
    out = []
    for ch in str(s):
        if ch in _SAFE:
            out.append(ch)
        else:
            out.extend(f"%{b:02X}" for b in _utf8(ch))
    return "".join(out)


def _unesc(s: str) -> str:
    buf = bytearray()
    i = 0
    hexdigits = "0123456789abcdefABCDEF"
    while i < len(s):
        c = s[i]
        if c == "%" and len(s[i + 1:i + 3]) == 2 and all(h in hexdigits for h in s[i + 1:i + 3]):
            buf.append(int(s[i + 1:i + 3], 16))
            i += 3
            continue
        if c == "+":
            buf.append(0x20)
            i += 1
            continue
        buf.extend(_utf8(c))
        i += 1
    return buf.decode("utf-8", "replace")


def codec_text(d: dict, v) -> str:
    """The text one value is written as in a URL."""
    t = d.get("type")
    if t == "toggle":
        return "1" if v else "0"
    if t == "choice":
        return v if isinstance(v, str) else _num_text(v) if _is_num(v) else _show(v)
    if t in ("vec", "colour"):
        dec = _grid(d)[1]
        return ",".join(_strip(_fixed(x, dec)) for x in (v if isinstance(v, (list, tuple)) else []))
    return _strip(_fixed(v, _grid(d)[1]))


def _read_text(d: dict, text: str):
    t = d.get("type")
    if t == "toggle":
        low = text.lower()
        return True if low in ("1", "true", "on", "yes") else False if low in ("0", "false", "off", "no") else text
    if t == "choice":
        for o in d.get("values") or []:
            if codec_text(d, o.get("value")) == text:
                return o.get("value")
        return text
    if t in ("vec", "colour"):
        parts = text.split(",")
        return [_to_number(p) for p in parts] if all(_NUM_RE.fullmatch(p) for p in parts) else text
    return _to_number(text) if _NUM_RE.fullmatch(text) else text


def _to_number(text: str):
    x = float(text)
    if x == 0 and text.startswith("-"):
        return -0.0   # Number("-0") is -0 in the JS twin; int(-0.0) would lose the sign
    return int(x) if math.isfinite(x) and x == int(x) and abs(x) < 2 ** 53 and re.fullmatch(r"[+-]?[0-9]+", text) else x


def encode(descriptors, values, all: bool = False) -> str:  # noqa: A002 -- the JS twin's option name
    """The validated values as a query string ("intensity=1.5&layers=30"); only non-default values unless all=True."""
    items = descriptors if isinstance(descriptors, list) else []
    r = validate(items, values)
    parts = []
    for d in items:
        if d.get("derived"):
            continue
        v = r["values"][d["id"]]
        if not all and _same_value(v, _default_of(d)):
            continue
        parts.append(_esc(d["id"]) + "=" + _esc(codec_text(d, v)))
    return "&".join(parts)


def decode(descriptors, query) -> dict:
    """The values a query string holds (typed where readable; text it cannot read stays a string for validate to name).
    Reads + as a space, keeps the first of repeated keys, ignores keys it does not know."""
    items = descriptors if isinstance(descriptors, list) else []
    q = query if isinstance(query, str) else ""
    if q.startswith("?"):
        q = q[1:]
    seen: Dict[str, str] = {}
    for part in q.split("&"):
        if not part:
            continue
        key, eq, rest = part.partition("=")
        key = _unesc(key)
        if key and key not in seen:
            seen[key] = _unesc(rest) if eq else ""
    out = {}
    for d in items:
        if not d.get("derived") and d["id"] in seen:
            out[d["id"]] = _read_text(d, seen[d["id"]])
    return out


def from_url(descriptors, query) -> dict:
    """validate(descriptors, decode(descriptors, query))."""
    return validate(descriptors, decode(descriptors, query))
