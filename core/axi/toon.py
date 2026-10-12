"""TOON encoder -- Token-Oriented Object Notation, the agent-mode output format.

AXI (https://axi.md) asks an agent-facing CLI to print TOON on stdout: the same data as JSON in
about 40% fewer tokens, because a uniform list states its field names once in a header instead
of on every row. This module turns plain Python data into TOON, following TOON spec 4.4
(https://github.com/toon-format/spec). It encodes only; nothing in Aurora reads TOON back.

Conformance is measured, not claimed: tests/test_axi_toon.py runs the spec's own encode
fixtures (tests/fixtures/toon/encode, MIT, copied unchanged) against this encoder.

Host-type mapping (spec section 3 asks for it to be documented):
    dict / Mapping           -> object, keys converted with str()
    list / tuple / set       -> array (a set in sorted order when its items sort)
    bool / None / int / float -> booleans, null, numbers; NaN and infinities -> null
    str                      -> string
    datetime / date          -> ISO 8601 string
    anything else            -> str(value)
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import math
import re
from collections.abc import Mapping
from decimal import Decimal

__all__ = ["encode"]

_UNQUOTED_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
_NUMERIC_LIKE = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?", re.IGNORECASE)
_DELIM_SYMBOL = {",": "", "\t": "\t", "|": "|"}


def encode(value, *, delimiter: str = ",", indent: int = 2) -> str:
    """Encode `value` as a TOON document (no trailing newline, per spec section 12)."""
    if delimiter not in _DELIM_SYMBOL:
        raise ValueError("delimiter must be ',', '\\t' or '|'")
    if indent < 1:
        raise ValueError("indent must be at least 1")
    return "\n".join(_Encoder(delimiter, indent).root(_normalize(value)))


# ------------------------------------------------------------------ normalization (section 3)


def _normalize(v):
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(v, Decimal):
        return _normalize(float(v)) if v.is_finite() else None
    if isinstance(v, Mapping):
        return {str(k): _normalize(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_normalize(x) for x in v]
    if isinstance(v, (set, frozenset)):
        items = list(v)
        with contextlib.suppress(TypeError):  # mixed types keep their iteration order
            items.sort()
        return [_normalize(x) for x in items]
    if isinstance(v, (_dt.datetime, _dt.date, _dt.time)):
        return v.isoformat()
    return str(v)


def _is_primitive(v) -> bool:
    return v is None or isinstance(v, (bool, int, float, str))


# ------------------------------------------------------------------ primitives (sections 2, 7)


def _number(n) -> str:
    if isinstance(n, bool):
        return "true" if n else "false"
    if isinstance(n, int):
        return str(n)
    if n == 0:
        return "0"
    if n.is_integer() and abs(n) < 1e21:
        return str(int(n))
    text = repr(n)  # shortest round-trip digits
    if 1e-6 <= abs(n) < 1e21:
        if "e" in text or "E" in text:
            text = format(Decimal(text), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    mantissa, _, exp = text.lower().partition("e")
    if not exp:  # repr chose plain digits; force the exponent form for this range
        mantissa, _, exp = f"{n:e}".partition("e")
    if "." in mantissa:
        mantissa = mantissa.rstrip("0").rstrip(".")
    sign = "-" if exp.startswith("-") else "+"
    return f"{mantissa}e{sign}{exp.lstrip('+-').lstrip('0') or '0'}"


def _escape(s: str) -> str:
    out = []
    for ch in s:
        code = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        elif 0xD800 <= code <= 0xDFFF:
            raise ValueError("unpaired surrogate cannot be encoded in TOON")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def _needs_quotes(s: str, delimiter: str) -> bool:
    return (
        s == ""
        or s[0] in " \t"
        or s[-1] in " \t"
        or s in ("true", "false", "null")
        or bool(_NUMERIC_LIKE.fullmatch(s))
        or any(c in s for c in ':"\\[]{}')
        or any(ord(c) < 0x20 for c in s)
        or delimiter in s
        or s[0] in "-#"
    )


def _key(k: str) -> str:
    return k if _UNQUOTED_KEY.fullmatch(k) else _escape(k)


# ------------------------------------------------------------------ shapes (sections 9.3, 9.5)


def _column_kind(values) -> str | None:
    """'prim' (uniform-primitive), 'nested' (nested-uniform) or None (disqualifies a table)."""
    if all(_is_primitive(v) for v in values):
        return "prim"
    if not all(isinstance(v, dict) and v for v in values):
        return None
    keys = set(values[0])
    if any(set(v) != keys for v in values):
        return None
    for k in values[0]:
        if _column_kind([v[k] for v in values]) is None:
            return None
    return "nested"


def _fields(rows):
    """The field list for uniform objects: [(name, subfields or None)], first row's order."""
    out = []
    for k in rows[0]:
        col = [r[k] for r in rows]
        out.append((k, _fields(col) if _column_kind(col) == "nested" else None))
    return out


def _uniform_objects(rows) -> bool:
    if not rows or not all(isinstance(r, dict) and r for r in rows):
        return False
    keys = set(rows[0])
    if any(set(r) != keys for r in rows):
        return False
    return all(_column_kind([r[k] for r in rows]) is not None for k in rows[0])


def _keyed_tabular(obj: dict) -> bool:
    return len(obj) >= 2 and _uniform_objects(list(obj.values()))


class _Encoder:
    def __init__(self, delimiter: str, indent: int):
        self.d = delimiter
        self.sym = _DELIM_SYMBOL[delimiter]
        self.indent = indent

    # -- leaves
    def prim(self, v) -> str:
        if v is None:
            return "null"
        if isinstance(v, (bool, int, float)):
            return _number(v)
        return _escape(v) if _needs_quotes(v, self.d) else v

    def pad(self, depth: int) -> str:
        return " " * (self.indent * depth)

    def field_list(self, fields) -> str:
        parts = []
        for name, sub in fields:
            parts.append(_key(name) + (self.field_list(sub) if sub else ""))
        return "{" + self.d.join(parts) + "}"

    def cells(self, row, fields) -> list[str]:
        out = []
        for name, sub in fields:
            out.extend(self.cells(row[name], sub) if sub else [self.prim(row[name])])
        return out

    # -- root (section 5)
    def root(self, v) -> list[str]:
        if isinstance(v, dict):
            if _keyed_tabular(v):
                return self.keyed("", v, 0)
            return self.obj(v, 0)
        if isinstance(v, list):
            if not v:
                return ["[]"]
            return self.array("", v, 0)
        if isinstance(v, str) and v.startswith("﻿"):
            return [_escape(v)]  # a leading U+FEFF would read as a byte-order mark
        return [self.prim(v)]

    # -- objects (section 8)
    def obj(self, o: dict, depth: int) -> list[str]:
        lines = []
        for k, v in o.items():
            lines.extend(self.field(_key(k), v, depth))
        return lines

    def field(self, key: str, v, depth: int) -> list[str]:
        pad = self.pad(depth)
        if _is_primitive(v):
            return [f"{pad}{key}: {self.prim(v)}"]
        if isinstance(v, dict):
            if _keyed_tabular(v):
                return self.keyed(key, v, depth)
            return [f"{pad}{key}:", *self.obj(v, depth + 1)]
        if not v:
            return [f"{pad}{key}: []"]
        return self.array(key, v, depth)

    def keyed(self, key: str, o: dict, depth: int) -> list[str]:
        rows = list(o.values())
        fields = _fields(rows)
        lines = [f"{self.pad(depth)}{key}[{len(o)}:{self.sym}]{self.field_list(fields)}:"]
        for k, row in o.items():
            lines.append(f"{self.pad(depth + 1)}{_key(k)}: {self.d.join(self.cells(row, fields))}")
        return lines

    # -- arrays (section 9)
    def header(self, key: str, n: int) -> str:
        return f"{key}[{n}{self.sym}]"

    def inline(self, arr) -> str:
        return self.d.join(self.prim(x) for x in arr)

    def array(self, key: str, arr: list, depth: int) -> list[str]:
        pad = self.pad(depth)
        head = self.header(key, len(arr))
        if all(_is_primitive(x) for x in arr):
            return [f"{pad}{head}: {self.inline(arr)}"]
        if _uniform_objects(arr):
            fields = _fields(arr)
            row_pad = self.pad(depth + 1)
            return [
                f"{pad}{head}{self.field_list(fields)}:",
                *(f"{row_pad}{self.d.join(self.cells(row, fields))}" for row in arr),
            ]
        lines = [f"{pad}{head}:"]
        for item in arr:
            lines.extend(self.item(item, depth + 1))
        return lines

    def item(self, v, depth: int) -> list[str]:
        """One list item at `depth` (sections 9.2, 9.4, 10)."""
        pad = self.pad(depth)
        if _is_primitive(v):
            return [f"{pad}- {self.prim(v)}"]
        if isinstance(v, list):
            head = self.header("", len(v))
            if all(_is_primitive(x) for x in v):
                return [f"{pad}- {head}: {self.inline(v)}" if v else f"{pad}- {head}:"]
            lines = [f"{pad}- {head}:"]
            for x in v:
                lines.extend(self.item(x, depth + 1))
            return lines
        if not v:
            return [f"{pad}-"]
        # Object as a list item: its fields stand at depth+1, the first one on the hyphen line.
        lines = []
        for i, (k, x) in enumerate(v.items()):
            field = self.field(_key(k), x, depth + 1)
            if i == 0:
                field[0] = f"{pad}- {field[0][len(self.pad(depth + 1)) :]}"
            lines.extend(field)
        return lines
