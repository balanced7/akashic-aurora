"""present.ui-element -- one slide (or every slide) as a self-contained HTML fragment for a
dashboard or a page: the logical 1920x1080 layout inside a CSS transform wrapper scaled to the
requested width, so the layout survives unchanged at 400 or 1200 wide (nothing reflows; the
slide is the slide, smaller).

The note becomes the panel's title attribute, and each cue becomes a title on the atom it
names (the manifest's declared degrade for the note). The fragment carries no <script>; its
one <style> is scoped to the panel's own id (border-box sizing and margin resets a plain
browser needs to show the subset the way the slides page does). Connectors are drawn in the
diagram's <svg>, since a plain browser draws no <x-connector>.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .. import scene as sc
from . import _core as C
from . import slides_html
from ._core import esc

MODULE_ID = "present.ui-element"
DEFAULT_WIDTH = 400


def fragment(
    scene: dict, slide: dict, width: int = DEFAULT_WIDTH, tk: dict | None = None, prefix: str = "present"
) -> str:
    """The panel for one slide at `width` logical units wide (height follows 16:9)."""
    if not isinstance(width, (int, float)) or width <= 0:
        raise ValueError(f"width must be a positive number of CSS pixels, got {width!r}")
    tk = tk or C.tokens(scene)
    k = width / sc.CANVAS["w"]
    height = round(width * sc.CANVAS["h"] / sc.CANVAS["w"])
    pid = f"{prefix}-{slide['id']}"
    note = C.note_of(slide)
    inner = slides_html.section_html(
        scene, slide, tk, mode="browser", tag="div", elem_id=pid, cues=C.cue_map(slide), aside=False
    )
    title = f' title="{esc(note.get("script"))}"' if note else ""
    reset = C.browser_reset_css(f"#{pid}")
    # The fonts travel with the fragment (a <link> in body is honoured by every browser and is
    # fetched once however many panels a page holds); without it the panel fell back to
    # Verdana / Courier New, a degrade no manifest had declared.
    fonts = f'<link rel="stylesheet" href="{esc(tk["href"])}">\n' if tk.get("href") else ""
    return (
        '<meta charset="utf-8">\n'  # harmless when embedded; right when opened alone
        + fonts
        + f'<div{title} style="position:relative; width:{width:g}px; height:{height}px; overflow:hidden">\n'
        f"<style>\n{reset}</style>\n"
        f'<div style="position:absolute; left:0; top:0; width:{sc.CANVAS["w"]}px; height:{sc.CANVAS["h"]}px; '
        f'transform-origin:0 0; transform: scale({k:.6g})">\n{inner}\n</div>\n</div>'
    )


def render(scene: dict, out_dir, width: int = DEFAULT_WIDTH, slide: str | None = None, **opts) -> list[Path]:
    """Write <out_dir>/<slide id>.html for one slide (`slide=<id>`) or for every slide."""
    out = Path(out_dir)
    tk = C.tokens(scene)
    slides = C.ordered_slides(scene)
    if slide is not None:
        slides = [s for s in slides if s.get("id") == slide]
        if not slides:
            raise ValueError(f"no slide {slide!r} in the scene")
    written: list[Path] = []
    for s in slides:
        written.append(C.write_bytes(out / f"{s['id']}.html", fragment(scene, s, int(width), tk) + "\n"))
    return written
