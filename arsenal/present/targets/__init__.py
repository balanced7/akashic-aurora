"""The built render targets of the present family: {module id: render(scene, out_dir, **opts) -> [Path]}.

Each target is an arsenal.module/v0 manifest in arsenal/modules/present.<name>.json plus one
module here. A render takes a VALIDATED scene dict (run scene.validate first; a renderer
raises on what the validator would have refused) and writes files under out_dir, returning
the paths it wrote. Options are the manifest's params by name (width, footnotes, autoplay,
plane_gap, verify_cdn, slide, created_at).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List
from collections.abc import Callable

from . import print_html, slides_html, three_js, ui_element

Render = Callable[..., list[Path]]

TARGETS: dict[str, Render] = {
    slides_html.MODULE_ID: slides_html.render,
    ui_element.MODULE_ID: ui_element.render,
    print_html.MODULE_ID: print_html.render,
    three_js.MODULE_ID: three_js.render,
}

#: what the door accepts after --to
ALIASES: dict[str, str] = {
    "slides": slides_html.MODULE_ID,
    "slides-html": slides_html.MODULE_ID,
    "html": slides_html.MODULE_ID,
    "ui": ui_element.MODULE_ID,
    "ui-element": ui_element.MODULE_ID,
    "panel": ui_element.MODULE_ID,
    "pdf": print_html.MODULE_ID,
    "print": print_html.MODULE_ID,
    "3d": three_js.MODULE_ID,
    "three": three_js.MODULE_ID,
    "three-js": three_js.MODULE_ID,
}

#: where the door puts each target under --out
SUBDIR: dict[str, str] = {
    slides_html.MODULE_ID: "project",
    ui_element.MODULE_ID: "ui",
    print_html.MODULE_ID: "print",
    three_js.MODULE_ID: "three",
}


def resolve(name: str) -> str:
    """A module id or an alias -> the module id, or ValueError naming the choices."""
    if name in TARGETS:
        return name
    if name in ALIASES:
        return ALIASES[name]
    if f"present.{name}" in TARGETS:
        return f"present.{name}"
    raise ValueError(f"no built target {name!r}; choose one of {', '.join(sorted(ALIASES))}")


__all__ = ["TARGETS", "ALIASES", "SUBDIR", "resolve"]
