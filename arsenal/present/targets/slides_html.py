"""present.slides-html -- a scene to one <section> file per slide plus deck.json (v4).

The output is the closed subset of the slides artifact type (scratchpad deckref, format.md):
every style inline, no class, no <style> rules, no em/rem/var()/margin, nothing under 24px,
128px margins (padding:128px 128px 160px where the template has a footer band), the note as
the last-child <aside>, an <svg> only for lines that must be curved or many-bend paths and
never with <text>. Templates map REGIONS to markup (the projection idioms the synthesiser
wrote for the builders: scratchpad deck/v2/projection.slides-html.json); atoms map to markup by
KIND; a diagram is a pinned host (position:relative, 1664x700) holding lanes, painted <p>
nodes, <x-connector>s from box edge midpoints (diagram-recipes.md, Rows for buses) and <p>
labels.

`section_html()` is shared: present.ui-element and present.pdf call it in "browser" mode,
where connectors become one <svg> (a plain browser draws no <x-connector>) and the caller
takes the note (a title attribute, a footnote) instead of the aside.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import scene as sc
from . import _core as C
from ._core import esc, fmt

MODULE_ID = "present.slides-html"
MARKER_PATH = "M-3.2 -1.7 L0.8 0 L-3.2 1.7"  # diagrams.md: a fixed-size head, tip at refX
BAR_TRACK = 300  # bars: the tallest bar, inside a 480 row


class _Ctx:
    """What every atom painter needs: tokens, the surface, the template, the mode, the cues."""

    def __init__(self, tk: dict, surf: dict[str, str], slide: dict, mode: str, cues: dict[str, str]):
        self.tk = tk
        self.surf = surf
        self.tpl = slide["template"]
        self.sid = slide["id"]
        self.mode = mode  # "artifact" (the subset) or "browser" (ui, print)
        self.cues = cues
        self.markers: dict[str, str] = {}  # colour -> marker id, per slide

    @property
    def sans(self) -> str:
        return self.tk["faces"]["sans"]

    @property
    def mono(self) -> str:
        return self.tk["faces"]["mono"]

    def size(self, role: str) -> int:
        return int(self.tk["type"][role])

    def attrs(self, obj: dict) -> str:
        """A title attribute when a note cue names this atom, node, lane or label (browser mode
        only: the artifact subset does not list title, and the page keeps cues off the slide)."""
        if self.mode == "artifact":
            return ""
        cue = self.cues.get(cid) if isinstance(cid := obj.get("id"), str) else None
        return f' title="{esc(cue)}"' if cue else ""


def _style(*parts: str | None) -> str:
    return "; ".join(p for p in parts if p)


# ---------------------------------------------------------------- inline pieces
def runs_html(runs: Any, surf: dict[str, str]) -> str:
    """strong -> <b>, em -> <i>, accent/muted -> a coloured span, code -> <b> (the page allows
    no font on a span: the declared degrade)."""
    out: list[str] = []
    for text, mark in C.runs_list(runs):
        t = esc(text)
        if mark in ("strong", "code"):
            t = f"<b>{t}</b>"
        elif mark == "em":
            t = f"<i>{t}</i>"
        elif mark == "accent":
            t = f'<span style="color:{surf["accent"]}">{t}</span>'
        elif mark == "muted":
            t = f'<span style="color:{surf["muted"]}">{t}</span>'
        out.append(t)
    return "".join(out)


def _eyebrow(ctx: _Ctx, text: str, extra: str = "", attrs: str = "") -> str:
    st = _style(
        f"font-family:{ctx.mono}",
        f"font-size:{ctx.size('eyebrow')}px",
        "font-weight:500",
        "line-height:1.2",
        "letter-spacing:2px",
        f"color:{ctx.surf['eyebrow']}",
        extra,
    )
    return f'<p{attrs} style="{st}">{esc(text.upper())}</p>'


def _card_style(ctx: _Ctx, tone: str | None = None, *, flex: bool = True, padding: int = 40, gap: int = 16) -> str:
    s = ctx.surf
    paint = [f"background:{s['card']}", f"border:1px solid {s['line']}"]
    colour = None
    if tone == "accent":
        paint = [f"background:{s['tint']}", f"border:2px solid {s['accent']}"]
        colour = s["tint_text"]
    elif tone == "ghost":
        paint = [f"background:{s['tint']}", f"border:2px dashed {s['accent']}"]
        colour = s["tint_muted"]
    elif tone == "secondary":
        paint = [f"background:{s['card']}", f"border:2px solid {s['secondary']}"]
    elif tone == "muted":
        colour = s["muted"]
    return _style(
        "flex:1" if flex else None,
        *paint,
        "border-radius:16px",
        f"padding:{padding}px",
        "display:flex",
        "flex-direction:column",
        f"gap:{gap}px",
        f"color:{colour}" if colour else None,
    )


# ---------------------------------------------------------------- atoms by kind
def _headline(a: dict, ctx: _Ctx, region: str) -> str:
    role = a.get("role") or C.DEFAULT_HEADLINE_ROLE[ctx.tpl]
    wt, lh, _, ls = C.TYPE_STYLE[role]
    tag = C.HEADLINE_TAG[role]
    width = None if ctx.tpl == "diagram" else ("width:1620px" if region == "stack" else "width:1664px")
    st = _style(
        f"font-size:{ctx.size(role)}px",
        f"font-weight:{wt}",
        f"line-height:{lh}",
        f"letter-spacing:{ls}px" if ls else None,
        "white-space:nowrap" if ctx.tpl == "diagram" else None,
        width,
    )
    return f'<{tag}{ctx.attrs(a)} style="{st}">{esc(a.get("text"))}</{tag}>'


def _label(a: dict, ctx: _Ctx) -> str:
    return _eyebrow(ctx, str(a.get("text", "")), attrs=ctx.attrs(a))


def _statement(a: dict, ctx: _Ctx, region: str, nested: bool) -> str:
    role = a.get("role") or {"lede": "lede", "kicker": "kicker"}.get(region, "body")
    _, lh, _, _ = C.TYPE_STYLE[role]
    width = None
    if not nested:
        width = {"stack": 1560, "body": 1600}.get(region, 1000)
    st = _style(
        f"font-size:{ctx.size(role)}px",
        f"line-height:{lh}",
        f"color:{ctx.surf['muted']}" if role == "lede" else None,
        f"width:{width}px" if width else None,
    )
    return f'<p{ctx.attrs(a)} style="{st}">{runs_html(a.get("runs"), ctx.surf)}</p>'


def _attribution(ctx: _Ctx, a: dict) -> str:
    line = f"— {a.get('attribution', '')}"
    if a.get("ref"):
        line += f" · {a['ref']}"
    st = _style(
        f"font-family:{ctx.mono}", f"font-size:{ctx.size('caption')}px", "line-height:1.4", f"color:{ctx.surf['muted']}"
    )
    return f'<p style="{st}">{esc(line)}</p>'


def _quote(a: dict, ctx: _Ctx, region: str, nested: bool) -> str:
    big = region == "stack" and ctx.tpl == "statement"
    if big:
        st = _style(f"font-size:{ctx.size('quote')}px", "font-weight:400", "line-height:1.2", "width:1620px")
    else:
        st = _style(
            f"font-size:{ctx.size('body')}px",
            "font-style:italic",
            "line-height:1.45",
            None if nested else ("width:1560px" if region == "stack" else "width:1000px"),
            f"color:{ctx.surf['muted']}" if region == "stack" else None,
        )
    body = f'<p style="{st}">“{esc(a.get("text"))}”</p>' + _attribution(ctx, a)
    if nested:
        return body
    return f'<div{ctx.attrs(a)} style="display:flex; flex-direction:column; gap:12px">{body}</div>'


def _number(a: dict, ctx: _Ctx, nested: bool) -> str:
    hero = (a.get("scale") or "hero") == "hero"
    size = ctx.size("number" if hero else "number_inline")
    cap = ctx.size("body" if hero else "caption")
    colour = C.tone_colour(a.get("tone"), ctx.surf, default=ctx.surf["accent"])
    value = _style(
        f"font-family:{ctx.mono}", f"font-size:{size}px", "font-weight:600", "line-height:1", f"color:{colour}"
    )
    caption = _style(f"font-size:{cap}px", "line-height:1.4", f"color:{ctx.surf['muted']}")
    body = f'<p style="{value}">{esc(a.get("value"))}</p><p style="{caption}">{esc(a.get("caption"))}</p>'
    if nested:
        return body
    return f'<div{ctx.attrs(a)} style="display:flex; flex-direction:column; gap:8px">{body}</div>'


def _list(a: dict, ctx: _Ctx, nested: bool) -> str:
    tag = "ol" if a.get("ordered") else "ul"
    st = _style(None if nested else "width:1400px", f"font-size:{ctx.size('body')}px", "line-height:1.5")
    items = "".join(f"<li>{runs_html(item, ctx.surf)}</li>" for item in a.get("items") or [])
    return f'<{tag}{ctx.attrs(a)} style="{st}">{items}</{tag}>'


def _table(a: dict, ctx: _Ctx) -> str:
    size = ctx.size(a.get("role") or "caption")
    head: list[str] = []
    for i, col in enumerate(a.get("columns") or []):
        st = _style(f"width:{col['share']:g}%", "text-align:left", "padding:14px 20px" if i == 0 else None)
        head.append(f'<th style="{st}">{esc(col.get("title"))}</th>')
    rows = "".join(
        f'<tr style="background:{ctx.surf["card"]}">'
        + "".join(f"<td>{esc(C.runs_text(cell))}</td>" for cell in row)
        + "</tr>"
        for row in a.get("rows") or []
    )
    # No line-height here: format.md lists it for text elements (h1-h3, p, ul, ol) only, and a
    # <table> is not one, so it would be an `unsupported:` build error (the row height is the
    # editor's own 2.1 x font-size per line).
    st = _style("width:1664px", f"font-size:{size}px")
    return f'<table{ctx.attrs(a)} style="{st}"><tr>{"".join(head)}</tr>{rows}</table>'


def _code(a: dict, ctx: _Ctx) -> str:
    marks = {m["line"]: (m.get("tone") or "accent") for m in a.get("marks") or [] if isinstance(m, dict)}
    lines: list[str] = []
    for i, line in enumerate(a.get("lines") or [], 1):
        t = esc(line)
        tone = marks.get(i)
        if tone == "ghost":
            t = f'<span style="color:{ctx.surf["muted"]}"><i>{t}</i></span>'
        elif tone:
            t = f'<span style="color:{C.tone_colour(tone, ctx.surf)}">{t}</span>'
        lines.append(t)
    st = _style(
        f"font-family:{ctx.mono}",
        f"font-size:{ctx.size('code')}px",
        "line-height:1.55",
        "padding:32px",
        f"background:{ctx.surf['card']}",
        f"border:1px solid {ctx.surf['line']}",
        "border-radius:16px",
    )
    return f'<p{ctx.attrs(a)} style="{st}">{"<br>".join(lines)}</p>'


def _bars(a: dict, ctx: _Ctx) -> str:
    series = [s for s in a.get("series") or [] if isinstance(s, dict)]
    top = max([float(s.get("value", 0)) for s in series] + [0.0])
    mx = float(a.get("max") or top or 1.0)
    unit = str(a.get("unit") or "")
    cols: list[str] = []
    for s in series:
        tone = s.get("tone")
        colour = C.tone_colour(tone, ctx.surf, default=ctx.surf["secondary"])
        h = max(4, round(float(s.get("value", 0)) / mx * BAR_TRACK))
        value = _style(
            f"font-family:{ctx.mono}",
            f"font-size:{ctx.size('number_inline')}px",
            "font-weight:600",
            "line-height:1",
            f"color:{colour}",
        )
        if tone == "ghost":
            track = _style(
                f"height:{h}px",
                f"background:{ctx.surf['tint']}",
                f"border:2px dashed {ctx.surf['accent']}",
                "border-radius:8px",
            )
        else:
            track = _style(f"height:{h}px", f"background:{colour}", "border-radius:8px")
        label = _style(f"font-size:{ctx.size('caption')}px", "line-height:1.4")
        caption = _style(f"font-size:{ctx.size('caption')}px", "line-height:1.4", f"color:{ctx.surf['muted']}")
        cap_text = esc(s.get("caption")) if s.get("caption") else "&#160;"
        cols.append(
            '<div style="flex:1; display:flex; flex-direction:column; justify-content:flex-end; gap:8px">'
            f'<p style="{value}">{esc(str(s.get("value")) + (" " + unit if unit else ""))}</p>'
            f'<div style="{track}"></div>'
            f'<p style="{label}">{esc(s.get("label"))}</p>'
            f'<p style="{caption}">{cap_text}</p></div>'
        )
    return (
        f'<div{ctx.attrs(a)} style="display:flex; gap:48px; align-items:flex-end; height:480px">'
        + "".join(cols)
        + "</div>"
    )


def _timeline(a: dict, ctx: _Ctx) -> str:
    row = a.get("orientation") == "row"
    beats: list[str] = []
    for b in a.get("beats") or []:
        st = _card_style(ctx, b.get("tone"), flex=row, padding=24, gap=12)
        text = _style(f"font-size:{ctx.size('caption')}px", "line-height:1.4")
        beats.append(
            f'<div style="{st}">{_eyebrow(ctx, str(b.get("at", "")))}'
            f'<p style="{text}">{runs_html(b.get("text"), ctx.surf)}</p></div>'
        )
    box = "display:flex; gap:24px" if row else "display:flex; flex-direction:column; gap:16px"
    return f'<div{ctx.attrs(a)} style="{box}">{"".join(beats)}</div>'


def _comparison(a: dict, ctx: _Ctx) -> str:
    verdict = a.get("verdict") or "none"
    sides: list[str] = []
    for side in ("left", "right"):
        s = a.get(side) or {}
        tone = s.get("tone") or ("accent" if verdict == side else None)
        parts: list[str] = []
        if s.get("eyebrow"):
            parts.append(_eyebrow(ctx, str(s["eyebrow"])))
        parts.append(
            f'<h3 style="font-size:{ctx.size("h3")}px; font-weight:600; line-height:1.2">{esc(s.get("title"))}</h3>'
        )
        parts.extend(_atom(item, ctx, "body", nested=True) for item in s.get("body") or [] if isinstance(item, dict))
        sides.append(f'<div style="{_card_style(ctx, tone)}">{"".join(parts)}</div>')
    return f'<div{ctx.attrs(a)} style="flex:1; display:flex; gap:32px">{"".join(sides)}</div>'


def _group(a: dict, ctx: _Ctx) -> str:
    arr = a.get("arrangement") or "row"
    framed = a.get("framed", True)
    if arr == "row":
        box = "display:flex; gap:32px"
    elif arr == "column":
        box = "display:flex; flex-direction:column; gap:32px"
    else:
        box = f"display:grid; grid-template-columns:repeat({int(a.get('columns') or 3)}, 1fr); gap:32px"
    items: list[str] = []
    for item in a.get("items") or []:
        if not isinstance(item, dict):
            continue
        inner = _atom(item, ctx, "body", nested=True)
        if framed:
            items.append(f'<div{ctx.attrs(item)} style="{_card_style(ctx, None, flex=(arr == "row"))}">{inner}</div>')
        else:
            st = _style("flex:1" if arr == "row" else None, "display:flex", "flex-direction:column", "gap:8px")
            items.append(f'<div{ctx.attrs(item)} style="{st}">{inner}</div>')
    return f'<div{ctx.attrs(a)} style="{box}">{"".join(items)}</div>'


def _receipt(a: dict, ctx: _Ctx) -> str:
    st = _style(
        "position:absolute",
        "left:128px",
        "bottom:64px",
        "width:1664px",
        "height:34px",
        f"font-family:{ctx.mono}",
        f"font-size:{ctx.size('receipt')}px",
        "line-height:34px",
        f"color:{ctx.surf['muted']}",
    )
    return f'<p{ctx.attrs(a)} style="{st}">{esc(a.get("text"))}</p>'


# ---------------------------------------------------------------- the diagram host
def _stroke(tone: str | None, dashed: bool, ctx: _Ctx):
    colour = C.tone_colour(tone, ctx.surf, default=ctx.surf["muted"])
    return colour, (dashed or tone == "ghost")


def _xconnector(c: dict, ctx: _Ctx) -> str:
    colour, dashed = _stroke(c.get("tone"), c.get("dashed", False), ctx)
    st = _style(f"color:{colour}", "border-width:2px", "border-style:dashed" if dashed else None)
    route = f' route="{c["route"]}"' if c.get("route") and c["route"] != "straight" else ""
    return (
        f'<x-connector x1="{fmt(c["x1"])}" y1="{fmt(c["y1"])}" x2="{fmt(c["x2"])}" y2="{fmt(c["y2"])}"'
        f'{route} head="{c.get("head") or "end"}" style="{st}"></x-connector>'
    )


def _marker(ctx: _Ctx, colour: str) -> str:
    mid = ctx.markers.get(colour)
    if mid is None:
        mid = f"m-{ctx.sid}-{len(ctx.markers) + 1}"
        ctx.markers[colour] = mid
    return mid


def _svg(g: dict, ctx: _Ctx, include_connectors: bool) -> str:
    """Paths (many-bend lines the scene drew) as one <svg> the size of the host, first in the
    host; in browser mode the connectors join it, since nothing else would draw them."""
    items: list[tuple] = []
    for p in g["paths"]:
        colour, dashed = _stroke(p.get("tone"), p.get("dashed", False), ctx)
        items.append((C.shorten(p["points"], p["head"]), colour, dashed, p["head"], 4))
    if include_connectors:
        for c in g["connectors"]:
            colour, dashed = _stroke(c.get("tone"), c.get("dashed", False), ctx)
            items.append((C.shorten(C.polyline(c), c.get("head") or "end"), colour, dashed, c.get("head") or "end", 3))
    if not items:
        return ""
    body: list[str] = []
    for pts, colour, dashed, head, width in items:
        d = "M " + " L ".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
        attrs = [
            f'd="{d}"',
            'fill="none"',
            f'stroke="{colour}"',
            f'stroke-width="{width}"',
            'stroke-linecap="round"',
            'stroke-linejoin="round"',
        ]
        if dashed:
            attrs.append('stroke-dasharray="12 10"')
        if head in ("end", "both"):
            attrs.append(f'marker-end="url(#{_marker(ctx, colour)})"')
        if head == "both":
            attrs.append(f'marker-start="url(#{_marker(ctx, colour)})"')
        body.append(f"<path {' '.join(attrs)}/>")
    defs = "".join(
        f'<marker id="{mid}" orient="auto-start-reverse" markerWidth="5" markerHeight="5" refX="0.8" refY="2" overflow="visible">'
        f'<path d="{MARKER_PATH}" transform="translate(0 2)" fill="none" stroke="{colour}" stroke-width="1" '
        f'stroke-linecap="round" stroke-linejoin="round"/></marker>'
        for colour, mid in ctx.markers.items()
    )
    aria = f' aria-label="{esc(g["aria_label"])}"' if g.get("aria_label") else ""
    return (
        f'<svg style="position:absolute; left:0; top:0" width="{sc.DIAGRAM_HOST["w"]}" height="{sc.DIAGRAM_HOST["h"]}" '
        f'viewBox="0 0 {sc.DIAGRAM_HOST["w"]} {sc.DIAGRAM_HOST["h"]}"{aria}>'
        + (f"<defs>{defs}</defs>" if defs else "")
        + "".join(body)
        + "</svg>"
    )


def _node(n: dict, ctx: _Ctx) -> str:
    s = ctx.surf
    tone = n.get("tone")
    paint = [f"background:{s['card']}", f"border:1px solid {s['line']}"]
    colour = None
    if tone == "accent":
        paint = [f"background:{s['tint']}", f"border:2px solid {s['accent']}"]
        colour = s["tint_text"]
    elif tone == "ghost":
        paint = [f"background:{s['tint']}", f"border:2px dashed {s['accent']}"]
        colour = s["tint_muted"]
    elif tone == "secondary":
        paint = [f"background:{s['card']}", f"border:2px solid {s['secondary']}"]
    elif tone == "muted":
        colour = s["muted"]
    wt, lh, _, _ = C.TYPE_STYLE["node"]
    st = _style(
        "position:absolute",
        f"left:{fmt(n['x'])}px",
        f"top:{fmt(n['y'])}px",
        f"width:{fmt(n['w'])}px",
        f"height:{fmt(n['h'])}px",
        "padding:16px",
        *paint,
        "border-radius:8px",
        f"font-size:{ctx.size('node')}px",
        f"font-weight:{wt}",
        f"line-height:{lh}",
        f"color:{colour}" if colour else None,
    )
    text = "<br>".join(esc(part) for part in str(n.get("text", "")).split("\n"))
    return f'<p{ctx.attrs(n)} style="{st}">{text}</p>'


def _lane(lane: dict, ctx: _Ctx) -> str:
    s = ctx.surf
    tone = lane.get("tone")
    paint = [f"background:{s['card']}", f"border:1px solid {s['line']}"]
    if tone == "accent":
        paint = [f"background:{s['tint']}", f"border:2px solid {s['accent']}"]
    elif tone == "ghost":
        paint = [f"background:{s['tint']}", f"border:2px dashed {s['accent']}"]
    elif tone == "secondary":
        paint = [f"background:{s['card']}", f"border:2px solid {s['secondary']}"]
    st = _style(
        "position:absolute",
        "left:0px",
        f"top:{fmt(lane['y'])}px",
        f"width:{sc.DIAGRAM_HOST['w']}px",
        f"height:{fmt(lane['h'])}px",
        *paint,
        "border-radius:16px",
    )
    band = f'<div{ctx.attrs(lane)} style="{st}"></div>'
    if lane.get("title"):
        band += _eyebrow(
            ctx,
            str(lane["title"]),
            extra=_style("position:absolute", "left:16px", f"top:{fmt(lane['y'] + 16)}px", "width:200px"),
        )
    return band


def _dlabel(lb: dict, ctx: _Ctx) -> str:
    _, lh, _, _ = C.TYPE_STYLE["label"]
    st = _style(
        "position:absolute",
        f"left:{fmt(lb['x'])}px",
        f"top:{fmt(lb['y'])}px",
        f"width:{fmt(lb['w'])}px",
        f"font-size:{ctx.size('label')}px",
        f"line-height:{lh}",
        f"color:{ctx.surf['muted']}",
    )
    return f'<p{ctx.attrs(lb)} style="{st}">{esc(lb.get("text"))}</p>'


def _diagram(a: dict, ctx: _Ctx) -> str:
    g = C.diagram_geometry(a)
    parts: list[str] = []
    svg = _svg(g, ctx, include_connectors=(ctx.mode != "artifact"))
    if svg:
        parts.append(svg)
    parts.extend(_lane(lane, ctx) for lane in g["lanes"])
    parts.extend(_node(n, ctx) for n in g["nodes"])
    if ctx.mode == "artifact":
        parts.extend(_xconnector(c, ctx) for c in g["connectors"])
    parts.extend(_dlabel(label, ctx) for label in g["labels"])
    st = _style("position:relative", f"width:{sc.DIAGRAM_HOST['w']}px", f"height:{sc.DIAGRAM_HOST['h']}px")
    return f'<div{ctx.attrs(a)} style="{st}">\n' + "\n".join(parts) + "\n</div>"


def _atom(a: dict, ctx: _Ctx, region: str, nested: bool = False) -> str:
    kind = a.get("kind")
    if kind == "headline":
        return _headline(a, ctx, region)
    if kind == "label":
        return _label(a, ctx)
    if kind == "statement":
        return _statement(a, ctx, region, nested)
    if kind == "quote":
        return _quote(a, ctx, region, nested)
    if kind == "number":
        return _number(a, ctx, nested)
    if kind == "list":
        return _list(a, ctx, nested)
    if kind == "table":
        return _table(a, ctx)
    if kind == "code":
        return _code(a, ctx)
    if kind == "bars":
        return _bars(a, ctx)
    if kind == "diagram":
        return _diagram(a, ctx)
    if kind == "timeline":
        return _timeline(a, ctx)
    if kind == "comparison":
        return _comparison(a, ctx)
    if kind == "group":
        return _group(a, ctx)
    if kind == "receipt":
        return _receipt(a, ctx)
    if kind == "note":
        return ""  # the section writes the aside itself, last
    raise ValueError(f"slide {ctx.sid}: no markup for atom kind {kind!r} (validate the scene first)")


# ---------------------------------------------------------------- the section
def section_html(
    scene: dict,
    slide: dict,
    tk: dict | None = None,
    *,
    mode: str = "artifact",
    tag: str = "section",
    elem_id: str | None = None,
    section: str | None = None,
    cues: dict[str, str] | None = None,
    aside: bool = True,
) -> str:
    """One slide as markup. mode="artifact" is the subset (x-connector lines, an <aside>);
    mode="browser" draws lines in the svg, sizes the box explicitly, and adds a title per cue.
    `section` is the data-section description when this slide starts one."""
    tk = tk or C.tokens(scene)
    surf = C.surface(C.slide_background(slide), tk["palette"])
    ctx = _Ctx(tk, surf, slide, mode, cues or {})
    tpl = slide["template"]
    regions = sc.TEMPLATES[tpl]["regions"]
    has_footer = any(r["name"] == "footer" for r in regions)
    by = C.atoms_by_region(slide)
    parts: list[str] = []
    if tpl in C.STACK_TEMPLATES:
        parts += [_atom(a, ctx, "stack") for a in by.get("stack", [])]
    elif tpl == "content":
        parts += [_atom(a, ctx, "heading") for a in by.get("heading", [])]
        parts += [_atom(a, ctx, "lede") for a in by.get("lede", [])]
        body = [_atom(a, ctx, "body") for a in by.get("body", [])]
        if body:
            parts.append(
                '<div style="flex:1; display:flex; flex-direction:column; gap:32px">\n' + "\n".join(body) + "\n</div>"
            )
        parts += [_atom(a, ctx, "kicker") for a in by.get("kicker", [])]
    elif tpl == "diagram":
        parts += [_atom(a, ctx, "heading") for a in by.get("heading", [])]
        parts += [_atom(a, ctx, "host") for a in by.get("host", [])]
    elif tpl == "comparison":
        parts += [_atom(a, ctx, "heading") for a in by.get("heading", [])]
        parts += [_atom(a, ctx, "left") for a in by.get("left", []) + by.get("right", [])]
        parts += [_atom(a, ctx, "kicker") for a in by.get("kicker", [])]
    parts += [_atom(a, ctx, "footer") for a in by.get("footer", [])]
    note = C.note_of(slide)
    if aside and note:
        parts.append(f"<aside>{esc(note.get('script'))}</aside>")
    style = _style(
        f"background:{surf['background']}",
        f"color:{surf['text']}",
        f"font-family:{ctx.sans}",
        "padding:128px 128px 160px" if has_footer else "padding:128px",
        "display:flex",
        "flex-direction:column",
        "justify-content:center" if tpl in C.STACK_TEMPLATES else None,
        f"gap:{C.DIAGRAM_GAP}px" if tpl == "diagram" else f"gap:{C.GAP}px",
        *(("position:relative", "width:1920px", "height:1080px", "overflow:hidden") if mode != "artifact" else ()),
    )
    attrs = [f'id="{esc(elem_id or slide["id"])}"']
    if section:
        attrs.append(f'data-section="{esc(section)}"')
    if tag == "section":
        attrs.append(f'data-transition="{esc(slide.get("transition") or "fade")}"')
    return f'<{tag} {" ".join(attrs)} style="{style}">\n' + "\n".join(p for p in parts if p) + f"\n</{tag}>"


def deck_manifest(scene: dict, tk: dict | None = None, created_at: str | None = None) -> dict:
    """deck.json v4: order, sections, faces (the first family carries the Google Fonts href)."""
    tk = tk or C.tokens(scene)
    faces: dict[str, dict] = {}
    for i, family in enumerate(tk["families"]):
        entry: dict[str, str] = {"family": family}
        if i == 0 and tk.get("href"):
            entry["href"] = tk["href"]
        faces[C.slug(family)] = entry
    order = list(scene.get("order") or [s["id"] for s in scene.get("slides") or []])
    sections = {
        k: {"description": v.get("description", ""), "start": v.get("start")}
        for k, v in (scene.get("sections") or {}).items()
        if isinstance(v, dict)
    }
    return {
        "v": 4,
        "createdOnFiles": {"v": 1, "at": created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "title": scene.get("title", ""),
        "order": order,
        "sections": sections,
        "faces": faces,
        "designSystems": [],
    }


def render(scene: dict, out_dir, **opts) -> list[Path]:
    """Write <out_dir>/deck.json and <out_dir>/slides/<id>.html for every slide in order."""
    out = Path(out_dir)
    tk = C.tokens(scene)
    starts = C.section_starts(scene)
    written: list[Path] = []
    for slide in C.ordered_slides(scene):
        markup = section_html(scene, slide, tk, mode="artifact", section=starts.get(slide["id"]))
        written.append(C.write_bytes(out / "slides" / f"{slide['id']}.html", markup + "\n"))
    manifest = deck_manifest(scene, tk, created_at=opts.get("created_at"))
    written.insert(0, C.write_bytes(out / "deck.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"))
    return written
