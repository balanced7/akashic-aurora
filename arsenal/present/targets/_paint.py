"""A flow-layout ESTIMATOR in logical units, for targets that paint pixels (present.three-js).

The slides page lays a slide out with flex flow, so no atom carries a position. A canvas
needs one. This module walks the same template regions with the same gaps and the family's
line-fit estimate (craft.md: 0.6 x size per character) and emits a flat draw list per slide --
rects, lines and text boxes in 1920x1080 units -- that a renderer paints top to bottom. Text
wraps in the renderer (it can measure glyphs); the estimate only decides where the next block
starts. Marks survive: a text op carries its runs, so strong, em, accent, muted and code draw
as themselves.

Ops (short keys keep the page small):
  {"t":"rect","x","y","w","h","f"?:fill,"s"?:stroke,"sw"?,"d"?:dashed,"r"?:radius}
  {"t":"line","p":[[x,y],...],"c":colour,"sw"?,"d"?:dashed,"h":"end|both|none"}
  {"t":"text","x","y","w","z":size,"wt":weight,"lh","f":"sans|mono","c":colour,"a"?:align,"ls"?,"r":[[text,mark],...]}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from collections.abc import Sequence

from .. import scene as sc
from . import _core as C

CANVAS_W, CANVAS_H = sc.CANVAS["w"], sc.CANVAS["h"]
L = sc.MARGIN
W = CANVAS_W - 2 * sc.MARGIN  # 1664
BAR_ROW, BAR_TRACK = 480, 300
FOOTER_Y = 982


class Painter:
    def __init__(self, tk: dict, surf: dict[str, str]):
        self.tk = tk
        self.surf = surf
        self.ops: list[dict] = []

    def probe(self) -> Painter:
        return Painter(self.tk, self.surf)

    def size(self, role: str) -> int:
        return int(self.tk["type"][role])

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=1, dashed=False, r=0) -> None:
        op: dict[str, Any] = {"t": "rect", "x": _n(x), "y": _n(y), "w": _n(w), "h": _n(h)}
        if fill:
            op["f"] = fill
        if stroke:
            op["s"] = stroke
            if sw != 1:
                op["sw"] = sw
        if dashed:
            op["d"] = 1
        if r:
            op["r"] = r
        self.ops.append(op)

    def line(self, pts: Sequence[tuple[float, float]], colour: str, sw=2, dashed=False, head="none") -> None:
        op: dict[str, Any] = {"t": "line", "p": [[_n(x), _n(y)] for x, y in pts], "c": colour, "h": head}
        if sw != 2:
            op["sw"] = sw
        if dashed:
            op["d"] = 1
        self.ops.append(op)

    def text(
        self,
        x,
        y,
        w,
        runs: Any,
        role: str | None = None,
        *,
        size=None,
        weight=None,
        lh=None,
        face=None,
        colour=None,
        align="left",
        ls=None,
        upper=False,
    ) -> float:
        """Emit a text box and return its estimated height."""
        if role:
            r_wt, r_lh, r_face, r_ls = C.TYPE_STYLE[role]
            size = size or self.size(role)
            weight = weight or r_wt
            lh = lh or r_lh
            face = face or r_face
            ls = r_ls if ls is None else ls
        size = size or self.size("body")
        weight = weight or 400
        lh = lh or 1.4
        face = face or "sans"
        rl = [[t.upper() if upper else t, m] for t, m in C.runs_list(runs)]
        text = "".join(t for t, _ in rl)
        op: dict[str, Any] = {
            "t": "text",
            "x": _n(x),
            "y": _n(y),
            "w": _n(w),
            "z": size,
            "wt": weight,
            "lh": lh,
            "f": face,
            "c": colour or self.surf["text"],
            "r": rl,
        }
        if align != "left":
            op["a"] = align
        if ls:
            op["ls"] = ls
        self.ops.append(op)
        return C.est_lines(text, w, size, weight) * size * lh


def _n(v) -> float:
    v = float(v)
    return int(v) if v.is_integer() else round(v, 2)


# ---------------------------------------------------------------- atoms
def _measure(p: Painter, a: dict, w: float, region: str, nested: bool = False) -> float:
    return paint_atom(p.probe(), a, 0, 0, w, region, nested)


def _headline(p: Painter, a: dict, x, y, w, region: str, tpl: str) -> float:
    role = a.get("role") or C.DEFAULT_HEADLINE_ROLE[tpl]
    width = 1620 if region == "stack" else w
    return p.text(x, y, width, a.get("text", ""), role)


def _label(p: Painter, a: dict, x, y, w) -> float:
    return p.text(x, y, w, a.get("text", ""), "eyebrow", colour=p.surf["eyebrow"], upper=True)


def _statement(p: Painter, a: dict, x, y, w, region: str, nested: bool) -> float:
    role = a.get("role") or {"lede": "lede", "kicker": "kicker"}.get(region, "body")
    width = w if nested else min(w, {"stack": 1560, "body": 1600}.get(region, 1000))
    colour = p.surf["muted"] if role == "lede" else None
    return p.text(x, y, width, a.get("runs"), role, colour=colour)


def _attribution(p: Painter, a: dict, x, y, w) -> float:
    line = f"— {a.get('attribution', '')}" + (f" · {a['ref']}" if a.get("ref") else "")
    return p.text(x, y, w, line, "caption", face="mono", colour=p.surf["muted"])


def _quote(p: Painter, a: dict, x, y, w, region: str, tpl: str, nested: bool) -> float:
    text = f"“{a.get('text', '')}”"
    if region == "stack" and tpl == "statement":
        h = p.text(x, y, min(w, 1620), text, "quote")
    else:
        width = w if nested else min(w, 1560 if region == "stack" else 1000)
        colour = p.surf["muted"] if region == "stack" else None
        h = p.text(x, y, width, [[text, "em"]], "body", colour=colour)
    return h + 12 + _attribution(p, a, x, y + h + 12, w)


def _number(p: Painter, a: dict, x, y, w) -> float:
    hero = (a.get("scale") or "hero") == "hero"
    role = "number" if hero else "number_inline"
    colour = C.tone_colour(a.get("tone"), p.surf, default=p.surf["accent"])
    h = p.text(x, y, w, str(a.get("value", "")), role, colour=colour)
    cap = p.text(x, y + h + 8, w, a.get("caption", ""), "body" if hero else "caption", colour=p.surf["muted"])
    return h + 8 + cap


def _list(p: Painter, a: dict, x, y, w, nested: bool) -> float:
    width = w if nested else min(w, 1400)
    size = p.size("body")
    total = 0.0
    for i, item in enumerate(a.get("items") or [], 1):
        bullet = f"{i}." if a.get("ordered") else "•"
        p.text(x, y + total, 44, bullet, "body", lh=1.5)
        h = p.text(x + 48, y + total, width - 48, item, "body", lh=1.5)
        total += h
    return total


def _table(p: Painter, a: dict, x, y, w) -> float:
    size = p.size(a.get("role") or "caption")
    cols = a.get("columns") or []
    xs: list[float] = []
    cx = x
    for c in cols:
        xs.append(cx)
        cx += w * float(c.get("share", 0)) / 100
    pad_x, pad_y = 0.6 * size, 0.35 * size

    def row_h(cells: list[str], weight: int) -> float:
        lines = max(
            C.est_lines(t, (xs[i + 1] if i + 1 < len(xs) else x + w) - xs[i] - 2 * pad_x, size, weight)
            for i, t in enumerate(cells)
        )
        return lines * size * 1.4 + 2 * pad_y

    cy = y
    titles = [str(c.get("title", "")) for c in cols]
    h = row_h(titles, 600)
    for i, t in enumerate(titles):
        cw = (xs[i + 1] if i + 1 < len(xs) else x + w) - xs[i]
        p.text(xs[i] + pad_x, cy + pad_y, cw - 2 * pad_x, t, "caption", size=size, weight=600)
    cy += h
    p.line([(x, cy), (x + w, cy)], p.surf["line"], sw=1)
    for row in a.get("rows") or []:
        cells = [C.runs_text(cell) for cell in row]
        h = row_h(cells, 400)
        p.rect(x, cy, w, h, fill=p.surf["card"])
        for i, t in enumerate(cells):
            cw = (xs[i + 1] if i + 1 < len(xs) else x + w) - xs[i]
            p.text(xs[i] + pad_x, cy + pad_y, cw - 2 * pad_x, t, "caption", size=size)
        cy += h
        p.line([(x, cy), (x + w, cy)], p.surf["line"], sw=1)
    return cy - y


def _code(p: Painter, a: dict, x, y, w) -> float:
    lines = a.get("lines") or []
    size = p.size("code")
    lh = size * 1.55
    h = len(lines) * lh + 64
    p.rect(x, y, w, h, fill=p.surf["card"], stroke=p.surf["line"], r=16)
    marks = {m["line"]: (m.get("tone") or "accent") for m in a.get("marks") or [] if isinstance(m, dict)}
    for i, line in enumerate(lines, 1):
        tone = marks.get(i)
        colour = p.surf["muted"] if tone == "ghost" else (C.tone_colour(tone, p.surf) if tone else None)
        p.text(
            x + 32, y + 32 + (i - 1) * lh, w - 64, [[line, "em" if tone == "ghost" else "plain"]], "code", colour=colour
        )
    return h


def _bars(p: Painter, a: dict, x, y, w) -> float:
    series = [s for s in a.get("series") or [] if isinstance(s, dict)]
    if not series:
        return 0
    top = max(float(s.get("value", 0)) for s in series)
    mx = float(a.get("max") or top or 1.0)
    unit = str(a.get("unit") or "")
    cw = (w - 48 * (len(series) - 1)) / len(series)
    floor = y + BAR_ROW - (34 + 8 + 34)  # label and caption rows under the track
    for i, s in enumerate(series):
        cx = x + i * (cw + 48)
        tone = s.get("tone")
        colour = C.tone_colour(tone, p.surf, default=p.surf["secondary"])
        h = max(4, round(float(s.get("value", 0)) / mx * BAR_TRACK))
        if tone == "ghost":
            p.rect(cx, floor - h, cw, h, fill=p.surf["tint"], stroke=p.surf["accent"], sw=2, dashed=True, r=8)
        else:
            p.rect(cx, floor - h, cw, h, fill=colour, r=8)
        p.text(
            cx,
            floor - h - 8 - p.size("number_inline"),
            cw,
            f"{s.get('value')} {unit}".strip(),
            "number_inline",
            colour=colour,
        )
        p.text(cx, floor + 8, cw, s.get("label", ""), "caption")
        if s.get("caption"):
            p.text(cx, floor + 8 + 34 + 8, cw, s["caption"], "caption", colour=p.surf["muted"])
    return BAR_ROW


def _card_paint(p: Painter, tone: str | None) -> tuple[str, str, int, bool, str | None]:
    s = p.surf
    if tone == "accent":
        return s["tint"], s["accent"], 2, False, s["tint_text"]
    if tone == "ghost":
        return s["tint"], s["accent"], 2, True, s["tint_muted"]
    if tone == "secondary":
        return s["card"], s["secondary"], 2, False, None
    if tone == "muted":
        return s["card"], s["line"], 1, False, s["muted"]
    return s["card"], s["line"], 1, False, None


def _timeline(p: Painter, a: dict, x, y, w) -> float:
    beats = [b for b in a.get("beats") or [] if isinstance(b, dict)]
    if not beats:
        return 0
    row = a.get("orientation") == "row"
    pad, gap = 24, 12
    if row:
        cw = (w - 24 * (len(beats) - 1)) / len(beats)
        heights = []
        for b in beats:
            q = p.probe()
            heights.append(
                pad
                + q.text(0, 0, cw - 2 * pad, b.get("at", ""), "eyebrow")
                + gap
                + q.text(0, 0, cw - 2 * pad, b.get("text"), "caption")
                + pad
            )
        h = max(heights)
        for i, b in enumerate(beats):
            cx = x + i * (cw + 24)
            fill, stroke, sw, dashed, colour = _card_paint(p, b.get("tone"))
            p.rect(cx, y, cw, h, fill=fill, stroke=stroke, sw=sw, dashed=dashed, r=16)
            eh = p.text(
                cx + pad, y + pad, cw - 2 * pad, b.get("at", ""), "eyebrow", colour=p.surf["eyebrow"], upper=True
            )
            p.text(cx + pad, y + pad + eh + gap, cw - 2 * pad, b.get("text"), "caption", colour=colour)
        return h
    cy = y
    for b in beats:
        q = p.probe()
        h = (
            pad
            + q.text(0, 0, w - 2 * pad, b.get("at", ""), "eyebrow")
            + gap
            + q.text(0, 0, w - 2 * pad, b.get("text"), "caption")
            + pad
        )
        fill, stroke, sw, dashed, colour = _card_paint(p, b.get("tone"))
        p.rect(x, cy, w, h, fill=fill, stroke=stroke, sw=sw, dashed=dashed, r=16)
        eh = p.text(x + pad, cy + pad, w - 2 * pad, b.get("at", ""), "eyebrow", colour=p.surf["eyebrow"], upper=True)
        p.text(x + pad, cy + pad + eh + gap, w - 2 * pad, b.get("text"), "caption", colour=colour)
        cy += h + 16
    return cy - y - 16


def _comparison(p: Painter, a: dict, x, y, w, min_h: float) -> float:
    verdict = a.get("verdict") or "none"
    cw = (w - 32) / 2
    pad, gap = 40, 16
    sides = []
    for side in ("left", "right"):
        s = a.get(side) or {}
        tone = s.get("tone") or ("accent" if verdict == side else None)
        q = p.probe()
        h = pad
        if s.get("eyebrow"):
            h += q.text(0, 0, cw - 2 * pad, s["eyebrow"], "eyebrow") + gap
        h += q.text(0, 0, cw - 2 * pad, s.get("title", ""), "h3") + gap
        for item in s.get("body") or []:
            h += paint_atom(q, item, 0, 0, cw - 2 * pad, "body", nested=True) + gap
        sides.append((s, tone, h - gap + pad))
    h = max([min_h] + [sh for _, _, sh in sides])
    for i, (s, tone, _) in enumerate(sides):
        cx = x + i * (cw + 32)
        fill, stroke, sw, dashed, colour = _card_paint(p, tone)
        p.rect(cx, y, cw, h, fill=fill, stroke=stroke, sw=sw, dashed=dashed, r=16)
        cy = y + pad
        if s.get("eyebrow"):
            cy += (
                p.text(cx + pad, cy, cw - 2 * pad, s["eyebrow"], "eyebrow", colour=p.surf["eyebrow"], upper=True) + gap
            )
        cy += p.text(cx + pad, cy, cw - 2 * pad, s.get("title", ""), "h3", colour=colour) + gap
        for item in s.get("body") or []:
            cy += paint_atom(p, item, cx + pad, cy, cw - 2 * pad, "body", nested=True) + gap
    return h


def _group(p: Painter, a: dict, x, y, w) -> float:
    items = [i for i in a.get("items") or [] if isinstance(i, dict)]
    if not items:
        return 0
    arr = a.get("arrangement") or "row"
    framed = a.get("framed", True)
    pad = 40 if framed else 0
    cols = len(items) if arr == "row" else (1 if arr == "column" else int(a.get("columns") or 3))
    cw = (w - 32 * (cols - 1)) / cols
    rows: list[list[dict]] = [items[i : i + cols] for i in range(0, len(items), cols)]
    cy = y
    for row in rows:
        heights = [_measure(p, item, cw - 2 * pad, "body", nested=True) + 2 * pad for item in row]
        h = max(heights)
        for i, item in enumerate(row):
            cx = x + i * (cw + 32)
            if framed:
                p.rect(cx, cy, cw, h, fill=p.surf["card"], stroke=p.surf["line"], r=16)
            paint_atom(p, item, cx + pad, cy + pad, cw - 2 * pad, "body", nested=True)
        cy += h + 32
    return cy - y - 32


def _diagram(p: Painter, a: dict, x, y) -> float:
    g = C.diagram_geometry(a)
    s = p.surf
    for lane in g["lanes"]:
        fill, stroke, sw, dashed, _ = _card_paint(p, lane.get("tone"))
        p.rect(x, y + lane["y"], sc.DIAGRAM_HOST["w"], lane["h"], fill=fill, stroke=stroke, sw=sw, dashed=dashed, r=16)
        if lane.get("title"):
            p.text(x + 16, y + lane["y"] + 16, 200, lane["title"], "eyebrow", colour=s["eyebrow"], upper=True)
    for n in g["nodes"]:
        fill, stroke, sw, dashed, colour = _card_paint(p, n.get("tone"))
        p.rect(x + n["x"], y + n["y"], n["w"], n["h"], fill=fill, stroke=stroke, sw=sw, dashed=dashed, r=8)
        p.text(x + n["x"] + 16, y + n["y"] + 16, n["w"] - 32, str(n.get("text", "")), "node", colour=colour)
    for c in g["connectors"]:
        colour = C.tone_colour(c.get("tone"), s, default=s["muted"])
        pts = C.shorten([(x + px, y + py) for px, py in C.polyline(c)], c.get("head") or "end")
        p.line(pts, colour, sw=3, dashed=bool(c.get("dashed")) or c.get("tone") == "ghost", head=c.get("head") or "end")
    for path in g["paths"]:
        colour = C.tone_colour(path.get("tone"), s, default=s["text"])
        pts = C.shorten([(x + px, y + py) for px, py in path["points"]], path["head"])
        p.line(pts, colour, sw=4, dashed=bool(path.get("dashed")) or path.get("tone") == "ghost", head=path["head"])
    for lb in g["labels"]:
        p.text(x + lb["x"], y + lb["y"], lb["w"], lb.get("text", ""), "label", colour=s["muted"])
    return sc.DIAGRAM_HOST["h"]


def _receipt(p: Painter, a: dict) -> float:
    return p.text(L, FOOTER_Y, W, a.get("text", ""), "receipt", lh=34 / p.size("receipt"), colour=p.surf["muted"])


def paint_atom(
    p: Painter, a: dict, x, y, w, region: str, nested: bool = False, tpl: str = "content", min_h: float = 0
) -> float:
    kind = a.get("kind")
    if kind == "headline":
        return _headline(p, a, x, y, w, region, tpl)
    if kind == "label":
        return _label(p, a, x, y, w)
    if kind == "statement":
        return _statement(p, a, x, y, w, region, nested)
    if kind == "quote":
        return _quote(p, a, x, y, w, region, tpl, nested)
    if kind == "number":
        return _number(p, a, x, y, w)
    if kind == "list":
        return _list(p, a, x, y, w, nested)
    if kind == "table":
        return _table(p, a, x, y, w)
    if kind == "code":
        return _code(p, a, x, y, w)
    if kind == "bars":
        return _bars(p, a, x, y, w)
    if kind == "diagram":
        return _diagram(p, a, x, y)
    if kind == "timeline":
        return _timeline(p, a, x, y, w)
    if kind == "comparison":
        return _comparison(p, a, x, y, w, min_h)
    if kind == "group":
        return _group(p, a, x, y, w)
    if kind == "receipt":
        return _receipt(p, a)
    if kind == "note":
        return 0
    raise ValueError(f"no paint for atom kind {kind!r} (validate the scene first)")


# ---------------------------------------------------------------- the slide
def paint_slide(scene: dict, slide: dict, tk: dict | None = None, section: str | None = None) -> dict:
    """The draw list for one slide, plus what a viewer shows around it (title, note, section)."""
    tk = tk or C.tokens(scene)
    surf = C.surface(C.slide_background(slide), tk["palette"])
    p = Painter(tk, surf)
    tpl = slide["template"]
    regions = {r["name"]: r for r in sc.TEMPLATES[tpl]["regions"]}
    has_footer = "footer" in regions
    bottom = 920 if has_footer else CANVAS_H - sc.MARGIN
    by = C.atoms_by_region(slide)
    gap = C.DIAGRAM_GAP if tpl == "diagram" else C.GAP

    def stack(atoms: list[dict], region: str, y: float) -> float:
        for a in atoms:
            y += paint_atom(p, a, L, y, W, region, tpl=tpl) + gap
        return y

    if tpl in C.STACK_TEMPLATES:
        atoms = by.get("stack", [])
        heights = [_measure_tpl(p, a, W, "stack", tpl) for a in atoms]
        total = sum(heights) + gap * max(0, len(atoms) - 1)
        stack(atoms, "stack", sc.MARGIN + max(0.0, (bottom - sc.MARGIN - total) / 2))
    elif tpl == "content":
        y = stack(by.get("heading", []), "heading", sc.MARGIN)
        y = stack(by.get("lede", []), "lede", y)
        kickers = by.get("kicker", [])
        kick_h = sum(_measure_tpl(p, a, W, "kicker", tpl) + gap for a in kickers) - (gap if kickers else 0)
        y = stack(by.get("body", []), "body", y)
        if kickers:
            stack(kickers, "kicker", max(y, bottom - kick_h))
    elif tpl == "diagram":
        stack(by.get("heading", []), "heading", sc.MARGIN)
        host = regions["host"]
        for a in by.get("host", []):
            paint_atom(p, a, host["left"], host["top"], host["width"], "host", tpl=tpl)
    elif tpl == "comparison":
        stack(by.get("heading", []), "heading", sc.MARGIN)
        left = regions["left"]
        y = left["top"]
        for a in by.get("left", []) + by.get("right", []):
            y += paint_atom(p, a, L, y, W, "left", tpl=tpl, min_h=left["height"]) + gap
        kick = regions["kicker"]
        stack(by.get("kicker", []), "kicker", max(y, kick["top"]))
    for a in by.get("footer", []):
        paint_atom(p, a, L, FOOTER_Y, W, "footer", tpl=tpl)
    note = C.note_of(slide)
    return {
        "id": slide["id"],
        "title": slide.get("title") or slide["id"],
        "bg": surf["background"],
        "ca": surf["accent"],
        "cm": surf["muted"],
        "section": section,
        "transition": slide.get("transition") or "fade",
        "duration_s": round(C.duration_s(slide), 1),
        "note": str((note or {}).get("script", "")),
        "ops": p.ops,
    }


def _measure_tpl(p: Painter, a: dict, w: float, region: str, tpl: str) -> float:
    return paint_atom(p.probe(), a, 0, 0, w, region, tpl=tpl)
