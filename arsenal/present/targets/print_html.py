"""present.pdf -- one paged HTML document: @page size 1920px 1080px, one <section> per page with
break-after: page, and the note as a footnote block under each page.

THE PDF IS THE BROWSER'S PRINT OF THIS PAGE. Open print.html in Chrome or Edge, print to PDF
with margins none and background graphics on (the @page rule already asks for both). This
module never launches a browser and never shells out: it writes the HTML and stops. There is
no receipt for the PDF itself until a person prints one.

With footnotes on (the default, notes_as_footnotes=1) each page holds the slide scaled down
by one factor for the whole deck, chosen from the longest note so every footnote fits in two
columns at caption role, and the section description of a section's first page is the
footnote's first line. With footnotes off the slide is full-bleed and the notes and sections
are dropped, as the manifest says.

The scale is clamped to 0.5-0.85. The floor used to be 0.6 and bound SILENTLY: the
Mail-and-Wake deck's longest note (1208 characters) needs 0.594 by the family's own line-fit
estimate, so at 0.6 the footnote box (overflow hidden) would have clipped its last lines with
no word said. Now the floor is lower, and a note the floor still cannot hold REFUSES the
render naming the slide and the overflow, since a footnote that ends mid-sentence is a drop
the manifest never declared (--no-footnotes is the escape).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional

from .. import scene as sc
from . import _core as C
from . import slides_html
from ._core import esc

MODULE_ID = "present.pdf"
FOOT_SIDE = 64  # the footnote's side margins
FOOT_GAP = 16  # between the scaled slide and the footnote
FOOT_LINE = 34  # caption role 24 x 1.4
MIN_SCALE, MAX_SCALE = 0.5, 0.85


def _footnote_need(scene: dict):
    """(slide id, characters, lines, rows, px) for the longest note, by the family's line-fit estimate."""
    longest, who = 0, None
    for slide in scene.get("slides") or []:
        note = C.note_of(slide)
        n = len(str((note or {}).get("script", "")))
        if n > longest:
            longest, who = n, slide.get("id")
    col_w = (sc.CANVAS["w"] - 2 * FOOT_SIDE - 32) / 2
    cpl = max(1, int(col_w / (0.6 * 24)))
    lines = math.ceil(longest / cpl) if longest else 1
    rows = math.ceil(lines / 2) + 1  # + the section line
    need = rows * FOOT_LINE + FOOT_GAP + 48
    return who, longest, lines, rows, need


def footnote_scale(scene: dict) -> float:
    """One scale for the whole deck: room for the longest note in two 24px columns, clamped
    to MIN_SCALE..MAX_SCALE. Below MIN_SCALE the note would be clipped: `document()` refuses
    instead of clamping quietly."""
    _, _, _, _, need = _footnote_need(scene)
    s = (sc.CANVAS["h"] - need) / sc.CANVAS["h"]
    return max(MIN_SCALE, min(MAX_SCALE, round(s, 3)))


def footnote_overflow(scene: dict) -> Optional[str]:
    """A sentence naming the slide whose note cannot fit its footnote even at MIN_SCALE, or
    None when every note fits (by the estimate)."""
    who, longest, lines, rows, need = _footnote_need(scene)
    room = sc.CANVAS["h"] - round(sc.CANVAS["h"] * MIN_SCALE) - FOOT_GAP - 24
    if need <= room + 48:  # the same 48 the estimate reserves
        return None
    return (
        f"slide {who}: its note is {longest} characters ({lines} lines at caption role in two columns), "
        f"more than the footnote holds at the {MIN_SCALE:g} floor; shorten the note or render with "
        f"footnotes off (--no-footnotes), which drops it openly"
    )


def _css(tk: dict, scale: float, footnotes: bool) -> str:
    w, h = sc.CANVAS["w"], sc.CANVAS["h"]
    ox = round((w - w * scale) / 2)
    foot_top = round(h * scale) + FOOT_GAP
    p = tk["palette"]
    return (
        f"@page {{ size: {w}px {h}px; margin: 0 }}\n"
        "html, body { margin: 0; padding: 0; background: #FFFFFF; -webkit-print-color-adjust: exact; print-color-adjust: exact }\n"
        f"body {{ font-family: {tk['faces']['sans']} }}\n"
        + C.browser_reset_css(".page")
        + f".page {{ position: relative; width: {w}px; height: {h}px; overflow: hidden; background: #FFFFFF; "
        "break-after: page; page-break-after: always }\n"
        f".page > section {{ position: absolute; left: {ox}px; top: 0; transform-origin: 0 0; transform: scale({scale:g}) }}\n"
        + (
            f".footnote {{ position: absolute; left: {FOOT_SIDE}px; right: {FOOT_SIDE}px; top: {foot_top}px; bottom: 24px; "
            f"overflow: hidden; columns: 2; column-gap: 32px; font-size: 24px; line-height: 1.4; color: {p['muted']} }}\n"
            f".footnote .section {{ font-family: {tk['faces']['mono']}; font-weight: 500; font-size: 24px; line-height: 1.2; "
            f"letter-spacing: 2px; text-transform: uppercase; color: {p['accent_deep']}; column-span: all; margin-bottom: 12px }}\n"
            if footnotes
            else ""
        )
        + "@media screen { body { background: #6B7680 } .page { margin: 24px auto; box-shadow: 0 8px 32px rgba(0,0,0,.35) } }\n"
    )


def document(scene: dict, tk: Optional[dict] = None, footnotes: bool = True) -> str:
    tk = tk or C.tokens(scene)
    starts = C.section_starts(scene)
    if footnotes:
        overflow = footnote_overflow(scene)
        if overflow:
            raise RuntimeError(f"present.pdf refuses: {overflow}")
    scale = footnote_scale(scene) if footnotes else 1.0
    pages: List[str] = []
    for slide in C.ordered_slides(scene):
        sid = slide["id"]
        section = slides_html.section_html(
            scene, slide, tk, mode="browser", tag="section", section=starts.get(sid), aside=False
        )
        foot = ""
        if footnotes:
            note = C.note_of(slide)
            lines: List[str] = []
            if starts.get(sid):
                lines.append(f'<p class="section">{esc(starts[sid])}</p>')
            lines.append(f"<p>{esc((note or {}).get('script', ''))}</p>")
            foot = '\n<div class="footnote">' + "".join(lines) + "</div>"
        pages.append(f'<div class="page">\n{section}{foot}\n</div>')
    link = f'<link rel="stylesheet" href="{esc(tk["href"])}">\n' if tk.get("href") else ""
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{esc(scene.get('title', ''))}</title>\n{link}"
        f"<style>\n{_css(tk, scale, footnotes)}</style>\n</head>\n<body>\n" + "\n".join(pages) + "\n</body>\n</html>\n"
    )


def render(scene: dict, out_dir, footnotes: bool = True, **opts) -> List[Path]:
    """Write <out_dir>/print.html. The PDF is the browser's print of it; nothing is launched."""
    return [C.write_bytes(Path(out_dir) / "print.html", document(scene, footnotes=bool(footnotes)))]
