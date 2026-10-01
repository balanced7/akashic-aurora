"""Shared plumbing for the present.* render targets (stdlib only; imports scene.py, nothing else).

What lives here is renderer knowledge the SCENE must never carry (invariant I5) but every target
needs: token resolution by role (with the family's own defaults), what a surface means (which
colour "muted" is on a dark slide), runs, the line-fit estimate (craft.md: 0.6 x size per
character), diagram geometry resolved from node ids to edge-midpoint segments (invariant I8:
coordinates belong to the renderer), and the byte writer (write_text would CRLF on Windows).

Nothing here knows what a <section>, a print page or a three.js plane is; those live in the
target modules.
"""

from __future__ import annotations

import html
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections.abc import Sequence

from .. import scene as sc

# ---------------------------------------------------------------- the family's defaults by role
DEFAULT_PALETTE: dict[str, str] = {
    "dark": "#13202B",
    "light": "#F6F7F5",
    "accent": "#C8762E",
    "accent_deep": "#9C5A1E",
    "secondary": "#3E7CA6",
    "muted": "#5A6B78",
    "muted_on_dark": "#9FB3C0",
    "card": "#FFFFFF",
    "card_on_dark": "#1C2E3D",
    "line": "#DDE2E1",
    "line_on_dark": "#2C4356",
    "tint": "#FBF3EA",
}
DEFAULT_TYPE: dict[str, int] = {
    "display": 160,
    "h1": 80,
    "h2": 64,
    "h3": 32,
    "body": 32,
    "lede": 32,
    "kicker": 32,
    "quote": 64,
    "number": 160,
    "number_inline": 80,
    "caption": 24,
    "eyebrow": 24,
    "code": 24,
    "receipt": 24,
    "node": 24,
    "label": 24,
}
DEFAULT_FONTS: dict[str, Any] = {
    "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600"
    "&family=JetBrains+Mono:wght@400;500&display=swap",
    "families": ["IBM Plex Sans", "JetBrains Mono"],
}
#: per type role: (weight, line-height, face, letter-spacing in logical units)
TYPE_STYLE: dict[str, tuple[int, float, str, int]] = {
    "display": (600, 1.0, "sans", -4),
    "h1": (600, 1.1, "sans", -2),
    "h2": (600, 1.1, "sans", -1),
    "h3": (600, 1.2, "sans", 0),
    "body": (400, 1.45, "sans", 0),
    "lede": (400, 1.4, "sans", 0),
    "kicker": (400, 1.45, "sans", 0),
    "quote": (400, 1.2, "sans", 0),
    "number": (600, 1.0, "mono", 0),
    "number_inline": (600, 1.0, "mono", 0),
    "caption": (400, 1.4, "sans", 0),
    "eyebrow": (500, 1.2, "mono", 2),
    "code": (400, 1.55, "mono", 0),
    "receipt": (400, 1.4, "mono", 0),
    "node": (500, 1.2, "sans", 0),
    "label": (400, 1.4, "sans", 0),
}
GAP = 32  # the flow gap between blocks on every template
DIAGRAM_GAP = 16  # 70 + 16 + 700 = 786 of the 792 budget (diagrams.md)
STACK_TEMPLATES = ("cover", "section", "statement", "closing")
HEADLINE_TAG = {"display": "h1", "h1": "h1", "h2": "h2", "h3": "h3"}
DEFAULT_HEADLINE_ROLE = {
    "cover": "display",
    "section": "h1",
    "statement": "h1",
    "closing": "h1",
    "content": "h2",
    "diagram": "h2",
    "comparison": "h2",
}
BUS_OFFSET = 24  # diagram-recipes.md: the bus bar sits 24 before the children's edge
HEAD_SHORTEN = 3  # diagrams.md: end a headed line 2-3 short of the target edge


def esc(text: Any) -> str:
    """HTML-escape (quotes included) so a payload string can never open a tag."""
    return html.escape("" if text is None else str(text), quote=True)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "face"


# ---------------------------------------------------------------- tokens and surfaces
def tokens(scene: dict) -> dict:
    """Resolve the deck's tokens over the family defaults: palette by role, type sizes by role,
    the two faces as CSS font stacks, and the Google Fonts href (None when the deck names fonts
    without one)."""
    t = scene.get("tokens") or {}
    palette = dict(DEFAULT_PALETTE)
    palette.update(t.get("palette") or {})
    sizes = dict(DEFAULT_TYPE)
    sizes.update(t.get("type_scale") or {})
    fonts = t.get("fonts") or None
    families = list((fonts or DEFAULT_FONTS).get("families") or DEFAULT_FONTS["families"])
    href = (fonts or DEFAULT_FONTS).get("href")
    sans = families[0] if families else "sans-serif"
    mono = families[1] if len(families) > 1 else "monospace"
    faces = {"sans": f"'{sans}', Verdana, sans-serif", "mono": f"'{mono}', 'Courier New', monospace"}
    return {"palette": palette, "type": sizes, "faces": faces, "families": families, "href": href}


def surface(background: str, palette: dict[str, str]) -> dict[str, str]:
    """What each role means on this background (projection idiom: colours by surface)."""
    p = palette
    common = {
        "accent": p["accent"],
        "secondary": p["secondary"],
        "tint": p["tint"],
        "tint_text": p["dark"],
        "tint_muted": p["muted"],
        "name": background,
    }
    if background == "dark":
        return {
            **common,
            "background": p["dark"],
            "text": p["light"],
            "muted": p["muted_on_dark"],
            "card": p["card_on_dark"],
            "line": p["line_on_dark"],
            "eyebrow": p["accent"],
        }
    if background == "accent":
        return {
            **common,
            "background": p["accent"],
            "text": p["dark"],
            "muted": p["dark"],
            "card": p["tint"],
            "line": p["accent_deep"],
            "eyebrow": p["dark"],
        }
    return {
        **common,
        "background": p["light"],
        "text": p["dark"],
        "muted": p["muted"],
        "card": p["card"],
        "line": p["line"],
        "eyebrow": p["accent_deep"],
    }


def tone_colour(tone: str | None, surf: dict[str, str], default: str | None = None) -> str:
    """The text or stroke colour a tone names. Ghost draws in accent (dashed, by the caller);
    muted is the surface's muted; None is the caller's default."""
    if tone == "accent" or tone == "ghost":
        return surf["accent"]
    if tone == "secondary":
        return surf["secondary"]
    if tone == "muted":
        return surf["muted"]
    return default if default is not None else surf["text"]


def slide_background(slide: dict) -> str:
    return slide.get("background") or sc.TEMPLATES[slide["template"]]["background"]


# ---------------------------------------------------------------- deck walking
def ordered_slides(scene: dict) -> list[dict]:
    slides = [s for s in scene.get("slides") or [] if isinstance(s, dict)]
    order = scene.get("order")
    if not order:
        return slides
    by_id = {s.get("id"): s for s in slides}
    return [by_id[i] for i in order if i in by_id]


def section_starts(scene: dict) -> dict[str, str]:
    """{slide_id: section description} for every slide that starts a section."""
    out: dict[str, str] = {}
    for sec in (scene.get("sections") or {}).values():
        if isinstance(sec, dict) and isinstance(sec.get("start"), str):
            out[sec["start"]] = str(sec.get("description") or "")
    return out


def note_of(slide: dict) -> dict | None:
    for a in slide.get("atoms") or []:
        if isinstance(a, dict) and a.get("kind") == "note":
            return a
    return None


def cue_map(slide: dict) -> dict[str, str]:
    note = note_of(slide)
    out: dict[str, str] = {}
    for c in (note or {}).get("cues") or []:
        if isinstance(c, dict) and isinstance(c.get("atom_id"), str):
            out[c["atom_id"]] = str(c.get("text") or "")
    return out


def duration_s(slide: dict) -> float:
    """The family default: max(8, words(note) / 2.5) unless the slide says otherwise."""
    d = slide.get("duration_s")
    if isinstance(d, (int, float)) and d > 0:
        return float(d)
    note = note_of(slide)
    words = len(str((note or {}).get("script", "")).split())
    return max(8.0, words / 2.5)


def atoms_by_region(slide: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for a in slide.get("atoms") or []:
        if isinstance(a, dict):
            out.setdefault(a.get("region"), []).append(a)
    return out


# ---------------------------------------------------------------- runs
def runs_list(runs: Any) -> list[tuple[str, str]]:
    """[(text, mark)] for a runs payload; a bare string is one plain run."""
    if isinstance(runs, str):
        return [(runs, "plain")]
    out: list[tuple[str, str]] = []
    for r in runs or []:
        if isinstance(r, str):
            out.append((r, "plain"))
        elif isinstance(r, dict):
            out.append((str(r.get("text", "")), r.get("mark") or "plain"))
    return out


def runs_text(runs: Any) -> str:
    return "".join(t for t, _ in runs_list(runs))


# ---------------------------------------------------------------- the line-fit estimate
def est_lines(text: str, width: float, size: float, weight: int = 400) -> int:
    """craft.md: about 0.6 x font-size per character (more for bold); a forced break is a line."""
    per_char = 0.6 * size * (1.08 if weight >= 600 else 1.0)
    cpl = max(1, int(width / per_char))
    lines = 0
    for para in str(text).split("\n"):
        lines += max(1, math.ceil(len(para) / cpl))
    return lines


# ---------------------------------------------------------------- diagram geometry (I8)
def _box(n: dict) -> tuple[float, float, float, float]:
    return float(n["x"]), float(n["y"]), float(n["w"]), float(n["h"])


def _mid(n: dict, side: str) -> tuple[float, float]:
    x, y, w, h = _box(n)
    return {"left": (x, y + h / 2), "right": (x + w, y + h / 2), "top": (x + w / 2, y), "bottom": (x + w / 2, y + h)}[
        side
    ]


def _overlap_x(a: dict, b: dict) -> bool:
    ax, _, aw, _ = _box(a)
    bx, _, bw, _ = _box(b)
    return ax < bx + bw and bx < ax + aw


def _overlap_y(a: dict, b: dict) -> bool:
    _, ay, _, ah = _box(a)
    _, by, _, bh = _box(b)
    return ay < by + bh and by < ay + ah


def edge_points(a: dict, b: dict, route: str | None) -> tuple[float, float, float, float]:
    """Where a connector from node a to node b starts and ends (diagrams.md, "Draw connectors
    from edge point to edge point"). Straight: side edges when the boxes are beside each other,
    top/bottom edges when one is above the other; when the source's centre line falls inside
    the target's span the line stays vertical (or horizontal) on that centre instead of
    slanting to a midpoint. hv: side edge into a top/bottom edge. vh: top/bottom into a side.
    elbow: side to side."""
    ax, ay, aw, ah = _box(a)
    bx, by, bw, bh = _box(b)
    acx, acy, bcx, bcy = ax + aw / 2, ay + ah / 2, bx + bw / 2, by + bh / 2
    dx, dy = bcx - acx, bcy - acy
    if route == "hv":
        x1, y1 = _mid(a, "right" if dx >= 0 else "left")
        x2, y2 = _mid(b, "top" if dy >= 0 else "bottom")
        return x1, y1, x2, y2
    if route == "vh":
        x1, y1 = _mid(a, "bottom" if dy >= 0 else "top")
        x2, y2 = _mid(b, "left" if dx >= 0 else "right")
        return x1, y1, x2, y2
    if route == "elbow":
        x1, y1 = _mid(a, "right" if dx >= 0 else "left")
        x2, y2 = _mid(b, "left" if dx >= 0 else "right")
        return x1, y1, x2, y2
    vertical = _overlap_x(a, b) or (not _overlap_y(a, b) and abs(dy) > abs(dx))
    if vertical:
        if bx <= acx <= bx + bw:
            x = acx
        elif ax <= bcx <= ax + aw:
            x = bcx
        else:
            return (acx, ay + ah if dy >= 0 else ay, bcx, by if dy >= 0 else by + bh)
        return (x, ay + ah if dy >= 0 else ay, x, by if dy >= 0 else by + bh)
    if by <= acy <= by + bh:
        y = acy
    elif ay <= bcy <= ay + ah:
        y = bcy
    else:
        return (ax + aw if dx >= 0 else ax, acy, bx if dx >= 0 else bx + bw, bcy)
    return (ax + aw if dx >= 0 else ax, y, bx if dx >= 0 else bx + bw, y)


def polyline(conn: dict) -> list[tuple[float, float]]:
    """The points a routed connector visits (hv: across then down; vh: down then across;
    elbow: three legs bending at the midpoint of the longer run)."""
    x1, y1, x2, y2 = conn["x1"], conn["y1"], conn["x2"], conn["y2"]
    route = conn.get("route") or "straight"
    if route == "hv":
        return [(x1, y1), (x2, y1), (x2, y2)]
    if route == "vh":
        return [(x1, y1), (x1, y2), (x2, y2)]
    if route == "elbow":
        if abs(x2 - x1) >= abs(y2 - y1):
            mx = (x1 + x2) / 2
            return [(x1, y1), (mx, y1), (mx, y2), (x2, y2)]
        my = (y1 + y2) / 2
        return [(x1, y1), (x1, my), (x2, my), (x2, y2)]
    return [(x1, y1), (x2, y2)]


def shorten(points: Sequence[tuple[float, float]], head: str, by: float = HEAD_SHORTEN) -> list[tuple[float, float]]:
    """Pull a headed line's end(s) back a few units so the arrowhead touches the box edge
    instead of poking into it."""
    pts = [tuple(p) for p in points]
    if len(pts) < 2 or by <= 0:
        return pts

    def pull(p_from, p_to):
        dx, dy = p_to[0] - p_from[0], p_to[1] - p_from[1]
        d = math.hypot(dx, dy)
        if d <= by:
            return p_to
        return (p_to[0] - dx / d * by, p_to[1] - dy / d * by)

    if head in ("end", "both"):
        pts[-1] = pull(pts[-2], pts[-1])
    if head == "both":
        pts[0] = pull(pts[1], pts[0])
    return pts


def _conn(x1, y1, x2, y2, *, head="end", route="straight", dashed=False, tone=None, kind="edge") -> dict:
    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "head": head,
        "route": route,
        "dashed": bool(dashed),
        "tone": tone,
        "kind": kind,
    }


def bus_parts(bus: dict, nodes: dict[str, dict]) -> list[dict]:
    """diagram-recipes.md, Rows: a drop from each parent, a bar 24 before the children's edge,
    one stub per child carrying the head. The recipe is vertical; it is mirrored when the
    children sit beside the parents (the same numbers turned on their side)."""
    sources = [nodes[i] for i in bus.get("from") or [] if i in nodes]
    sinks = [nodes[i] for i in bus.get("to") or [] if i in nodes]
    if not sources or not sinks:
        return []
    head = bus.get("head") or "end"
    tone, dashed = bus.get("tone"), bool(bus.get("dashed"))
    stubs = {s.get("to"): s for s in bus.get("stubs") or [] if isinstance(s, dict)}
    s_boxes = [_box(s) for s in sources]
    k_boxes = [_box(k) for k in sinks]
    below = min(y for _, y, _, _ in k_boxes) >= max(y + h for _, y, _, h in s_boxes)
    above = max(y + h for _, y, _, h in k_boxes) <= min(y for _, y, _, _ in s_boxes)
    right = min(x for x, _, _, _ in k_boxes) >= max(x + w for x, _, w, _ in s_boxes)
    left = max(x + w for x, _, w, _ in k_boxes) <= min(x for x, _, _, _ in s_boxes)
    if not (below or above or right or left):
        # overlapping in both axes: fall back on the larger centre delta
        scx = sum(x + w / 2 for x, _, w, _ in s_boxes) / len(s_boxes)
        scy = sum(y + h / 2 for _, y, _, h in s_boxes) / len(s_boxes)
        kcx = sum(x + w / 2 for x, _, w, _ in k_boxes) / len(k_boxes)
        kcy = sum(y + h / 2 for _, y, _, h in k_boxes) / len(k_boxes)
        if abs(kcy - scy) >= abs(kcx - scx):
            below, above = kcy >= scy, kcy < scy
        else:
            right, left = kcx >= scx, kcx < scx
    parts: list[dict] = []

    def stub_kw(sink: dict) -> dict:
        s = stubs.get(sink.get("id")) or {}
        return {"head": s.get("head") or head, "dashed": bool(s.get("dashed", dashed)), "tone": s.get("tone") or tone}

    if below or above:
        p_edge = max(y + h for _, y, _, h in s_boxes) if below else min(y for _, y, _, _ in s_boxes)
        c_edge = min(y for _, y, _, _ in k_boxes) if below else max(y + h for _, y, _, h in k_boxes)
        bar = c_edge - BUS_OFFSET if below else c_edge + BUS_OFFSET
        if abs(c_edge - p_edge) < 2 * BUS_OFFSET:
            bar = (p_edge + c_edge) / 2
        s_centres = [x + w / 2 for x, _, w, _ in s_boxes]
        k_centres = [x + w / 2 for x, _, w, _ in k_boxes]
        if len(sources) == 1 and len(sinks) == 1 and abs(s_centres[0] - k_centres[0]) < 1:
            return [_conn(s_centres[0], p_edge, k_centres[0], c_edge, **stub_kw(sinks[0]), kind="bus")]
        for cx in s_centres:
            parts.append(_conn(cx, p_edge, cx, bar, head="none", dashed=dashed, tone=tone, kind="bus"))
        lo, hi = min(s_centres + k_centres), max(s_centres + k_centres)
        parts.append(_conn(lo, bar, hi, bar, head="none", dashed=dashed, tone=tone, kind="bus"))
        for sink, cx in zip(sinks, k_centres):
            parts.append(_conn(cx, bar, cx, c_edge, **stub_kw(sink), kind="bus"))
        return parts
    p_edge = max(x + w for x, _, w, _ in s_boxes) if right else min(x for x, _, _, _ in s_boxes)
    c_edge = min(x for x, _, _, _ in k_boxes) if right else max(x + w for x, _, w, _ in k_boxes)
    bar = c_edge - BUS_OFFSET if right else c_edge + BUS_OFFSET
    if abs(c_edge - p_edge) < 2 * BUS_OFFSET:
        bar = (p_edge + c_edge) / 2
    s_centres = [y + h / 2 for _, y, _, h in s_boxes]
    k_centres = [y + h / 2 for _, y, _, h in k_boxes]
    if len(sources) == 1 and len(sinks) == 1 and abs(s_centres[0] - k_centres[0]) < 1:
        return [_conn(p_edge, s_centres[0], c_edge, k_centres[0], **stub_kw(sinks[0]), kind="bus")]
    for cy in s_centres:
        parts.append(_conn(p_edge, cy, bar, cy, head="none", dashed=dashed, tone=tone, kind="bus"))
    lo, hi = min(s_centres + k_centres), max(s_centres + k_centres)
    parts.append(_conn(bar, lo, bar, hi, head="none", dashed=dashed, tone=tone, kind="bus"))
    for sink, cy in zip(sinks, k_centres):
        parts.append(_conn(bar, cy, c_edge, cy, **stub_kw(sink), kind="bus"))
    return parts


def diagram_geometry(diagram: dict) -> dict:
    """Everything a renderer draws, in host units: lanes, nodes, connectors (edges and bus
    parts resolved to endpoints), paths (as given) and labels."""
    nodes = {n["id"]: n for n in diagram.get("nodes") or [] if isinstance(n, dict) and "id" in n}
    connectors: list[dict] = []
    for e in diagram.get("edges") or []:
        if not isinstance(e, dict) or e.get("from") not in nodes or e.get("to") not in nodes:
            continue
        route = e.get("route") or "straight"
        x1, y1, x2, y2 = edge_points(nodes[e["from"]], nodes[e["to"]], route)
        connectors.append(
            _conn(
                x1,
                y1,
                x2,
                y2,
                head=e.get("head") or "end",
                route=route,
                dashed=bool(e.get("dashed")),
                tone=e.get("tone"),
                kind="edge",
            )
        )
    for b in diagram.get("buses") or []:
        if isinstance(b, dict):
            connectors.extend(bus_parts(b, nodes))
    paths = []
    for p in diagram.get("paths") or []:
        if isinstance(p, dict) and isinstance(p.get("points"), list):
            paths.append(
                {
                    "id": p.get("id"),
                    "points": [(float(x), float(y)) for x, y in p["points"]],
                    "head": p.get("head") or "none",
                    "dashed": bool(p.get("dashed")),
                    "tone": p.get("tone"),
                }
            )
    return {
        "lanes": [l for l in diagram.get("lanes") or [] if isinstance(l, dict)],
        "nodes": list(nodes.values()),
        "connectors": connectors,
        "paths": paths,
        "labels": [l for l in diagram.get("labels") or [] if isinstance(l, dict)],
        "aria_label": diagram.get("aria_label"),
    }


def fmt(n: float) -> str:
    """A coordinate as the subset wants it: a bare number, integers without a trailing .0."""
    return f"{n:g}"


# ---------------------------------------------------------------- output
def write_bytes(path, text: str) -> Path:
    """Write UTF-8 with LF line endings, whatever the platform (write_text would CRLF)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    return p


BROWSER_RESET = (
    "{S}, {S} * {{ box-sizing: border-box }}\n"
    "{S} h1, {S} h2, {S} h3, {S} p, {S} ul, {S} ol, {S} table {{ margin: 0 }}\n"
    "{S} ul, {S} ol {{ padding-left: 40px }}\n"
    "{S} table {{ border-collapse: collapse }}\n"
    "{S} th, {S} td {{ padding: 0.35em 0.6em; border: 1px solid rgba(127,127,127,0.25); vertical-align: top; text-align: left }}\n"
    "{S} th {{ font-weight: 600 }}\n"
    "{S} aside {{ display: none }}\n"
)


def browser_reset_css(selector: str) -> str:
    """What a plain browser needs to show the artifact subset the way the slides page does:
    border-box sizing (a pinned node's width is its outer box), no default margins on text
    blocks, ruled table cells."""
    return BROWSER_RESET.replace("{S}", selector).replace("{{", "{").replace("}}", "}")
