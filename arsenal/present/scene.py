"""present.scene.v1 -- load and validate a renderer-neutral slide scene.

Standalone on purpose (the same rule as arsenal/analysis.py): stdlib only, no arsenal.*
imports, and no renderer knowledge -- this module does not know what a <section>, a PDF
page, a video frame or a three.js plane is (the flow-lib rule, arsenal/web/lib/flow/README.md:6).
It knows three things: templates as named REGIONS in logical canvas units, atoms as
STRUCTURED payloads, and the refusals that keep a scene portable across render targets.

A scene:
    {"schema": "present.scene.v1", "title": str,
     "tokens": {...by role...},                 # optional; missing keys fall back to the family
     "order": [slide_id, ...],                  # optional; defaults to the slides' own order
     "sections": {sid: {"description": str, "start": slide_id}},   # optional
     "slides": [ {"id", "template", "background"?, "transition"?, "duration_s"?, "title"?,
                  "atoms": [ {"kind", "region", "id"?, ...payload} ], "provenance"?: {...}} ]}

Refusals come back from validate() as sentences a person can act on, prefixed
"slide <id>: E0n" or "deck: E0n".  Warnings come back from lint() prefixed "W0n".
The E/W codes are catalogued in docs/presentation-primitives.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from collections.abc import Iterator

SCHEMA = "present.scene.v1"

# ---------------------------------------------------------------- geometry (logical units)
CANVAS = {"w": 1920, "h": 1080}  # the only canvas; every region below is measured on it
MARGIN = 128  # craft.md: 128px edge margins are the standard
DIAGRAM_HOST = {"w": 1664, "h": 700}  # diagrams.md: one host div, 1664x700, at most 24 pinned children
MAX_PINNED = 24

# ---------------------------------------------------------------- vocabularies
ATOM_KINDS = (
    "headline",
    "label",
    "statement",
    "quote",
    "number",
    "list",
    "table",
    "code",
    "bars",
    "diagram",
    "timeline",
    "comparison",
    "group",
    "receipt",
    "note",
)

#: what a group or a comparison side may hold (a group inside a group is refused: E09)
NESTED_KINDS = ("number", "statement", "list", "quote", "code")

TOKEN_ROLES = {
    "palette": (
        "dark",
        "light",
        "accent",
        "accent_deep",
        "secondary",
        "muted",
        "muted_on_dark",
        "card",
        "card_on_dark",
        "line",
        "line_on_dark",
        "tint",
    ),
    "type": (
        "display",
        "h1",
        "h2",
        "h3",
        "body",
        "lede",
        "kicker",
        "quote",
        "number",
        "number_inline",
        "caption",
        "eyebrow",
        "code",
        "receipt",
        "node",
        "label",
    ),
    "face": ("sans", "mono"),
    "tone": ("accent", "secondary", "muted", "ghost"),  # ghost = does not exist today (I9)
    "mark": ("plain", "strong", "em", "accent", "muted", "code"),
    "background": ("light", "dark", "accent"),
}
HEADLINE_ROLES = ("display", "h1", "h2", "h3")
STATEMENT_ROLES = ("body", "lede", "kicker")
TABLE_ROLES = ("body", "caption")
TRANSITIONS = ("fade", "push", "magic")
EDGE_ROUTES = ("straight", "hv", "vh", "elbow")
EDGE_HEADS = ("end", "both", "none")
NUMBER_SCALES = ("hero", "inline")
ARRANGEMENTS = ("row", "column", "grid")
ORIENTATIONS = ("row", "column")
VERDICTS = ("left", "right", "none")


# ---------------------------------------------------------------- templates: regions in logical units
def _r(name: str, left: int, top: int, width: int, height: int, *accepts: str) -> dict[str, Any]:
    return {"name": name, "left": left, "top": top, "width": width, "height": height, "accepts": accepts}


_NOTE = _r("note", 0, 0, 0, 0, "note")  # takes no space on any target
_FOOTER = _r("footer", 128, 982, 1664, 34, "receipt")  # layout.md: one 24px row at bottom:64

TEMPLATES: dict[str, dict[str, Any]] = {
    "cover": {
        "background": "dark",
        "regions": [_r("stack", 128, 128, 1664, 824, "label", "headline", "statement"), _FOOTER, _NOTE],
    },
    "section": {
        "background": "dark",
        "regions": [_r("stack", 128, 128, 1664, 824, "label", "headline", "statement"), _NOTE],
    },
    "statement": {
        "background": "dark",
        "regions": [_r("stack", 128, 128, 1664, 792, "label", "headline", "quote", "statement"), _FOOTER, _NOTE],
    },
    "content": {
        "background": "light",
        "regions": [
            _r("heading", 128, 128, 1664, 148, "headline"),
            _r("lede", 128, 308, 1000, 90, "statement"),
            _r(
                "body",
                128,
                308,
                1664,
                612,
                "group",
                "table",
                "list",
                "timeline",
                "quote",
                "number",
                "code",
                "bars",
                "statement",
                "comparison",
            ),
            _r("kicker", 128, 781, 1000, 139, "statement", "quote"),
            _FOOTER,
            _NOTE,
        ],
    },
    "diagram": {
        "background": "light",
        "regions": [
            _r("heading", 128, 128, 1664, 70, "headline"),
            _r("host", 128, 214, 1664, 700, "diagram"),
            _FOOTER,
            _NOTE,
        ],
    },
    "comparison": {
        "background": "light",
        "regions": [
            _r("heading", 128, 128, 1664, 148, "headline"),
            _r("left", 128, 308, 816, 473, "comparison"),  # one comparison atom placed in `left`
            _r("right", 976, 308, 816, 473, "comparison"),  # spans both columns; `right` is its mirror
            _r("kicker", 128, 813, 1000, 107, "statement", "quote"),
            _FOOTER,
            _NOTE,
        ],
    },
    "closing": {
        "background": "dark",
        "regions": [
            _r("stack", 128, 128, 1664, 792, "label", "headline", "list", "quote", "statement"),
            _FOOTER,
            _NOTE,
        ],
    },
}

# ---------------------------------------------------------------- refusal patterns
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
#: a target unit inside a scene string (E03). Percent is left alone: the family's only share is a number field.
_UNIT_RE = re.compile(r"(?<![\w.\-])\d+(?:\.\d+)?\s?(?:px|pt|em|rem|vw|vh|vmin|vmax)\b")
#: keys that only a renderer may own (E03); an atom naming one has smuggled a projection into the scene
_FORBIDDEN_KEYS = frozenset(
    {
        "size",
        "font_size",
        "font-size",
        "font",
        "color",
        "colour",
        "style",
        "css",
        "html",
        "class",
        "px",
        "padding",
        "margin",
        "hex",
        "background",
    }
)
#: a diagram given as a picture (E04)
_PICTURE_KEYS = frozenset({"src", "image", "img", "svg", "base64", "url", "href", "data_uri"})
#: coordinates on an edge (I8: edges reference node ids; coordinates belong to the renderer)
_EDGE_COORD_KEYS = frozenset({"x1", "y1", "x2", "y2", "x", "y", "points"})
_FILE_LINE_RE = re.compile(r"\.(?:py|md|json|mjs|js|ts)\s*:\s*\d+")
_FORCED_BREAK_RE = re.compile(r"\n| \| ")


# ================================================================ public API
def load(path) -> dict:
    """Read a scene from a UTF-8 JSON file. Raises ValueError with the path on bad JSON."""
    p = Path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{p}: not valid JSON ({e.msg} at line {e.lineno} column {e.colno})") from None


def validate(scene: Any) -> list[str]:
    """Refusals, in words a person can act on. An empty list means the scene is renderable.

    Refusal codes: E01 unknown template / kind / role / tone / mark; E02 region not in the
    template or not accepting the atom; E03 a target unit, a renderer key, a payload given as
    a string, or geometry outside the canvas; E04 a diagram given as a picture; E05 note
    missing, doubled, misplaced or not last; E06 duplicate ids, order naming an unknown slide,
    a slide missing from order, a section starting on an unknown slide; E07 diagram graph
    (edge or bus to an unknown node, lane or label reference to an unknown id, malformed path);
    E08 table shape (shares, ragged rows); E09 nesting a kind a group or comparison cannot hold.
    """
    problems: list[str] = []
    if not isinstance(scene, dict):
        return ["deck: E01 the scene is not a JSON object"]
    if scene.get("schema") != SCHEMA:
        problems.append(f"deck: E01 schema is {scene.get('schema')!r}; this validator reads {SCHEMA!r}")
    if not isinstance(scene.get("title"), str) or not scene["title"].strip():
        problems.append("deck: E01 title is missing or empty")
    problems.extend(_check_tokens(scene.get("tokens")))
    problems.extend(_check_template_overrides(scene.get("templates")))

    slides = scene.get("slides")
    if not isinstance(slides, list) or not slides:
        problems.append("deck: E06 slides must be a non-empty list")
        return problems

    ids: list[str] = []
    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            problems.append(f"deck: E01 slide #{i + 1} is not an object")
            continue
        sid = slide.get("id")
        if not isinstance(sid, str) or not _ID_RE.match(sid):
            problems.append(f"deck: E06 slide #{i + 1} needs an id matching [a-z0-9][a-z0-9_-]* (got {sid!r})")
            sid = f"#{i + 1}"
        elif sid in ids:
            problems.append(f"deck: E06 duplicate slide id {sid!r}; every slide id must be unique")
        ids.append(sid)
        problems.extend(_check_slide(slide, sid))

    order = scene.get("order")
    if order is not None:
        if not isinstance(order, list):
            problems.append("deck: E06 order must be a list of slide ids")
        else:
            known = set(ids)
            for name in order:
                if name not in known:
                    problems.append(
                        f"deck: E06 order names an unknown slide {name!r}; add the slide or drop it from order"
                    )
            for sid in ids:
                if sid not in order:
                    problems.append(
                        f"deck: E06 slide {sid!r} is not in order, so no target would render it; add it or delete the slide"
                    )
            dup = {n for n in order if order.count(n) > 1}
            for name in sorted(dup):
                problems.append(f"deck: E06 order lists {name!r} more than once")
    sections = scene.get("sections")
    if sections is not None:
        if not isinstance(sections, dict):
            problems.append("deck: E06 sections must be an object {id: {description, start}}")
        else:
            for sec_id, sec in sections.items():
                if (
                    not isinstance(sec, dict)
                    or not isinstance(sec.get("description"), str)
                    or not sec.get("description", "").strip()
                ):
                    problems.append(f"deck: E06 section {sec_id!r} needs a one-sentence description")
                    continue
                if sec.get("start") not in ids:
                    problems.append(f"deck: E06 section {sec_id!r} starts on an unknown slide {sec.get('start')!r}")
    return problems


def lint(scene: Any) -> list[str]:
    """Warnings (never refusals): craft limits a renderer can still render past.

    W01 diagram headline over 38 characters; W02 label over 40 or receipt over 110 characters;
    W03 node text with more than 3 forced lines; W04 more than 24 pinned children estimated
    in a diagram host; W05 duration_s shorter than the note's spoken length; W06 a note cue
    naming no atom, node, lane or label on its slide; W07 a file:line inside node text
    (receipts belong in the footer); W08 a table wider than 4 columns; W09 a slide with
    no receipt on a template that has a footer.
    """
    out: list[str] = []
    if not isinstance(scene, dict):
        return out
    for slide in scene.get("slides") or []:
        if not isinstance(slide, dict):
            continue
        sid = slide.get("id", "?")
        tpl = slide.get("template")
        atoms = [a for a in (slide.get("atoms") or []) if isinstance(a, dict)]
        ids = set(_slide_ids(slide))
        has_footer = any(r["name"] == "footer" for r in TEMPLATES.get(tpl, {}).get("regions", []))
        if has_footer and not any(a.get("kind") == "receipt" for a in atoms):
            out.append(f"slide {sid}: W09 template {tpl!r} has a footer band and the slide carries no receipt")
        for a in atoms:
            kind = a.get("kind")
            if kind == "headline" and tpl == "diagram" and isinstance(a.get("text"), str) and len(a["text"]) > 38:
                out.append(f"slide {sid}: W01 diagram headline is {len(a['text'])} characters; the one-line cap is 38")
            if kind == "label" and isinstance(a.get("text"), str) and len(a["text"]) > 40:
                out.append(f"slide {sid}: W02 label is {len(a['text'])} characters; the eyebrow cap is 40")
            if kind == "receipt" and isinstance(a.get("text"), str) and len(a["text"]) > 110:
                out.append(f"slide {sid}: W02 receipt is {len(a['text'])} characters; the footer band holds 110")
            if kind == "table" and isinstance(a.get("columns"), list) and len(a["columns"]) > 4:
                out.append(
                    f"slide {sid}: W08 table has {len(a['columns'])} columns; more than 4 will not fit at caption role"
                )
            if kind == "diagram":
                for n in a.get("nodes") or []:
                    text = n.get("text") if isinstance(n, dict) else None
                    if not isinstance(text, str):
                        continue
                    lines = len(_FORCED_BREAK_RE.split(text))
                    if lines > 3:
                        out.append(f"slide {sid}: W03 node {n.get('id')!r} has {lines} forced lines; a node holds 3")
                    if _FILE_LINE_RE.search(text):
                        out.append(
                            f"slide {sid}: W07 node {n.get('id')!r} carries a file:line; receipts live in the footer"
                        )
                pinned = _pinned_estimate(a)
                if pinned > MAX_PINNED:
                    out.append(
                        f"slide {sid}: W04 diagram estimates {pinned} pinned children; a host holds {MAX_PINNED}"
                    )
            if kind == "note":
                words = len(str(a.get("script", "")).split())
                need = max(8.0, words / 2.5)
                d = slide.get("duration_s")
                if isinstance(d, (int, float)) and d < need:
                    out.append(
                        f"slide {sid}: W05 duration_s {d} is shorter than the note's {need:.0f} s at 2.5 words per second"
                    )
                for cue in a.get("cues") or []:
                    if isinstance(cue, dict) and cue.get("atom_id") not in ids:
                        out.append(
                            f"slide {sid}: W06 note cue names {cue.get('atom_id')!r}, which is no atom, node, lane or label on this slide"
                        )
    return out


def used_kinds(scene: Any) -> set[str]:
    """Every atom kind the deck uses, nested ones included (what a target must cover)."""
    kinds: set[str] = set()
    for slide in (scene.get("slides") or []) if isinstance(scene, dict) else []:
        for atom in iter_atoms(slide):
            if isinstance(atom.get("kind"), str):
                kinds.add(atom["kind"])
    return kinds


def coverage(scene: Any, manifest: Any) -> list[str]:
    """Invariant I6: a render target must say, per atom kind the deck uses, what it preserves,
    how it degrades, or what it drops; naming none of the three is refused at plan time (unknown
    is not a yes). `manifest` is an arsenal.module/v0 dict with an `atoms` table
    {kind: {preserves?, degrades?, drops?}}, each a non-empty sentence.
    """
    problems: list[str] = []
    if not isinstance(manifest, dict):
        return ["target: the manifest is not an object"]
    target = manifest.get("id", "?")
    table = manifest.get("atoms")
    if not isinstance(table, dict):
        return [f"target {target}: names no `atoms` table, so it covers nothing; add preserves/drops per atom kind"]
    for kind in sorted(used_kinds(scene)):
        row = table.get(kind)
        if not isinstance(row, dict) or not any(
            isinstance(row.get(k), str) and row[k].strip() for k in ("preserves", "degrades", "drops")
        ):
            problems.append(
                f"target {target}: names neither preserves, degrades nor drops for atom kind {kind!r}, which this deck uses"
            )
    return problems


def iter_atoms(slide: Any) -> Iterator[dict]:
    """The slide's atoms in order, then the atoms nested in groups and comparison sides."""
    for atom in (slide.get("atoms") or []) if isinstance(slide, dict) else []:
        if not isinstance(atom, dict):
            continue
        yield atom
        if atom.get("kind") == "group":
            for item in atom.get("items") or []:
                if isinstance(item, dict):
                    yield item
        elif atom.get("kind") == "comparison":
            for side in ("left", "right"):
                for item in ((atom.get(side) or {}).get("body") or []) if isinstance(atom.get(side), dict) else []:
                    if isinstance(item, dict):
                        yield item


# ================================================================ internals
def _check_tokens(tokens: Any) -> list[str]:
    out: list[str] = []
    if tokens is None:
        return out
    if not isinstance(tokens, dict):
        return ["deck: E01 tokens must be an object of roles"]
    palette = tokens.get("palette")
    if isinstance(palette, dict):
        for role, value in palette.items():
            if role not in TOKEN_ROLES["palette"]:
                out.append(
                    f"deck: E01 palette role {role!r} is not in the family ({', '.join(TOKEN_ROLES['palette'])})"
                )
            elif not (isinstance(value, str) and _HEX_RE.match(value)):
                out.append(f"deck: E01 palette role {role!r} must be a #RRGGBB colour, got {value!r}")
    scale = tokens.get("type_scale")
    if isinstance(scale, dict):
        for role, size in scale.items():
            if role not in TOKEN_ROLES["type"]:
                out.append(f"deck: E01 type role {role!r} is not in the family ({', '.join(TOKEN_ROLES['type'])})")
            elif not isinstance(size, (int, float)) or size < 24:
                out.append(
                    f"deck: E01 type role {role!r} is {size!r}; the floor is 24 logical units (nothing under 24)"
                )
    return out


def _check_template_overrides(overrides: Any) -> list[str]:
    """A deck may override REGION GEOMETRY of a family template, never its accepts."""
    out: list[str] = []
    if overrides is None:
        return out
    if not isinstance(overrides, dict):
        return ["deck: E01 templates must be an object {template: {regions: [...]}}"]
    for name, tpl in overrides.items():
        if name not in TEMPLATES:
            out.append(
                f"deck: E01 template override {name!r} names no family template; the family has {', '.join(TEMPLATES)}"
            )
            continue
        known = {r["name"] for r in TEMPLATES[name]["regions"]}
        for region in (tpl.get("regions") or []) if isinstance(tpl, dict) else []:
            rname = region.get("name") if isinstance(region, dict) else None
            if rname not in known:
                out.append(f"deck: E01 template {name!r} has no region {rname!r} to override")
            elif "accepts" in region:
                out.append(
                    f"deck: E01 template {name!r} region {rname!r}: accepts belongs to the family, override geometry only"
                )
    return out


def _regions(template: str) -> dict[str, dict[str, Any]]:
    return {r["name"]: r for r in TEMPLATES[template]["regions"]}


def _slide_ids(slide: dict) -> list[str]:
    ids: list[str] = []
    for atom in iter_atoms(slide):
        if isinstance(atom.get("id"), str):
            ids.append(atom["id"])
        if atom.get("kind") == "diagram":
            for key in ("nodes", "lanes", "labels", "paths"):
                for item in atom.get(key) or []:
                    if isinstance(item, dict) and isinstance(item.get("id"), str):
                        ids.append(item["id"])
    return ids


def _check_slide(slide: dict, sid: str) -> list[str]:
    out: list[str] = []
    pre = f"slide {sid}"
    tpl = slide.get("template")
    if tpl not in TEMPLATES:
        out.append(f"{pre}: E01 template {tpl!r} is not in the family; choose one of {', '.join(TEMPLATES)}")
        return out
    bg = slide.get("background")
    if bg is not None and bg not in TOKEN_ROLES["background"]:
        out.append(
            f"{pre}: E01 background {bg!r} is not a role; use one of {', '.join(TOKEN_ROLES['background'])} (never a colour)"
        )
    tr = slide.get("transition")
    if tr is not None and tr not in TRANSITIONS:
        out.append(f"{pre}: E01 transition {tr!r}; use one of {', '.join(TRANSITIONS)}")
    d = slide.get("duration_s")
    if d is not None and (not isinstance(d, (int, float)) or d <= 0):
        out.append(f"{pre}: E03 duration_s must be a positive number of seconds, got {d!r}")
    for key in slide:
        if key in _FORBIDDEN_KEYS - {"background"}:
            out.append(
                f"{pre}: E03 slide carries {key!r}; a slide names its template and its atoms, nothing a renderer owns"
            )

    atoms = slide.get("atoms")
    if not isinstance(atoms, list) or not atoms:
        out.append(f"{pre}: E05 atoms must be a non-empty list (at least a note)")
        return out
    regions = _regions(tpl)
    seen_ids: set[str] = set()
    notes: list[int] = []
    for i, atom in enumerate(atoms):
        where = f"{pre}: atom #{i + 1}"
        if not isinstance(atom, dict):
            out.append(f"{where}: E01 is not an object")
            continue
        kind = atom.get("kind")
        if kind not in ATOM_KINDS:
            out.append(
                f"{where}: E01 unknown atom kind {kind!r}; the family has {', '.join(ATOM_KINDS)} (a missing element is a family defect: extend the family, not the slide)"
            )
            continue
        where = f"{pre}: {kind}" + (f" {atom['id']!r}" if isinstance(atom.get("id"), str) else f" #{i + 1}")
        if "payload" in atom and isinstance(atom["payload"], str):
            out.append(
                f"{where}: E03 payload is a JSON string; the scene carries structured payloads (parse it into the atom's own fields)"
            )
            continue
        region = atom.get("region")
        if region not in regions:
            out.append(f"{where}: E02 template {tpl!r} has no region {region!r}; its regions are {', '.join(regions)}")
        elif kind not in regions[region]["accepts"]:
            out.append(
                f"{where}: E02 region {region!r} of template {tpl!r} does not accept {kind!r}; it accepts {', '.join(regions[region]['accepts'])}"
            )
        if kind == "note":
            notes.append(i)
            if region != "note":
                out.append(f"{where}: E05 the note belongs in region 'note', not {region!r}")
        out.extend(_check_units(atom, where, top=True))
        out.extend(_check_fields(atom, where, nested=False))
        for aid in _atom_ids(atom):
            if aid in seen_ids:
                out.append(
                    f"{where}: E06 duplicate id {aid!r} on this slide; ids are unique per slide (atoms, nodes, lanes, labels, paths)"
                )
            seen_ids.add(aid)
    if not notes:
        out.append(f"{pre}: E05 no note atom; every slide carries exactly one note (the script), last")
    elif len(notes) > 1:
        out.append(f"{pre}: E05 {len(notes)} note atoms; a slide carries exactly one")
    elif notes[0] != len(atoms) - 1:
        out.append(f"{pre}: E05 the note must be the last atom (it is #{notes[0] + 1} of {len(atoms)})")
    return out


def _atom_ids(atom: dict) -> list[str]:
    ids: list[str] = []
    if isinstance(atom.get("id"), str):
        ids.append(atom["id"])
    if atom.get("kind") == "diagram":
        for key in ("nodes", "lanes", "labels", "paths"):
            for item in atom.get(key) or []:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    ids.append(item["id"])
    elif atom.get("kind") == "group":
        for item in atom.get("items") or []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                ids.append(item["id"])
    elif atom.get("kind") == "comparison":
        for side in ("left", "right"):
            body = (atom.get(side) or {}).get("body") if isinstance(atom.get(side), dict) else None
            for item in body or []:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    ids.append(item["id"])
    return ids


def _check_units(value: Any, where: str, top: bool = False, path: str = "", in_code: bool = False) -> list[str]:
    """E03: no target unit in any string, no renderer key anywhere. Code lines are exempt:
    they quote source verbatim, and a quoted stylesheet is content, not layout."""
    out: list[str] = []
    if isinstance(value, dict):
        kind = value.get("kind") if top else None
        for key, v in value.items():
            if key in _FORBIDDEN_KEYS:
                out.append(
                    f"{where}: E03 key {key!r}{path} belongs to a renderer; a scene carries roles and tones, never sizes, colours or markup"
                )
                continue
            if top and key == "provenance":
                continue
            exempt = in_code or (kind == "code" and key == "lines")
            out.extend(_check_units(v, where, path=f"{path}.{key}", in_code=exempt))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.extend(_check_units(v, where, path=f"{path}[{i}]", in_code=in_code))
    elif isinstance(value, str) and not in_code:
        m = _UNIT_RE.search(value)
        if m:
            out.append(
                f"{where}: E03 target unit {m.group(0)!r} inside{path or ' the payload'}; geometry is logical units and text carries a role, never a size"
            )
    return out


def _check_runs(runs: Any, where: str, field: str) -> list[str]:
    out: list[str] = []
    if isinstance(runs, str):
        return out  # sugar: one plain run
    if not isinstance(runs, list) or not runs:
        return [f"{where}: E01 {field} must be a non-empty list of runs [{{text, mark}}] (or one string)"]
    for i, run in enumerate(runs):
        if isinstance(run, str):
            continue
        if not isinstance(run, dict) or not isinstance(run.get("text"), str):
            out.append(f"{where}: E01 {field}[{i}] needs a text string")
            continue
        mark = run.get("mark", "plain")
        if mark not in TOKEN_ROLES["mark"]:
            out.append(f"{where}: E01 {field}[{i}] mark {mark!r}; marks are {', '.join(TOKEN_ROLES['mark'])}")
    return out


def _check_tone(atom: dict, where: str, field: str = "tone") -> list[str]:
    tone = atom.get(field)
    if tone is not None and tone not in TOKEN_ROLES["tone"]:
        return [
            f"{where}: E01 {field} {tone!r}; tones are {', '.join(TOKEN_ROLES['tone'])} (ghost means: does not exist today)"
        ]
    return []


def _need_str(atom: dict, where: str, *fields: str) -> list[str]:
    return [
        f"{where}: E01 needs {f!r} as a non-empty string"
        for f in fields
        if not isinstance(atom.get(f), str) or not atom[f].strip()
    ]


def _check_fields(atom: dict, where: str, nested: bool) -> list[str]:
    kind = atom["kind"]
    out: list[str] = []
    if nested and kind not in NESTED_KINDS:
        return [f"{where}: E09 {kind!r} cannot be nested; a group or a comparison side holds {', '.join(NESTED_KINDS)}"]
    if kind == "headline":
        out += _need_str(atom, where, "text")
        if atom.get("role") is not None and atom["role"] not in HEADLINE_ROLES:
            out.append(f"{where}: E01 headline role {atom['role']!r}; roles are {', '.join(HEADLINE_ROLES)}")
    elif kind == "label":
        out += _need_str(atom, where, "text")
    elif kind == "statement":
        out += _check_runs(atom.get("runs"), where, "runs")
        if atom.get("role") is not None and atom["role"] not in STATEMENT_ROLES:
            out.append(f"{where}: E01 statement role {atom['role']!r}; roles are {', '.join(STATEMENT_ROLES)}")
    elif kind == "quote":
        out += _need_str(atom, where, "text", "attribution")
    elif kind == "number":
        if not isinstance(atom.get("value"), (str, int, float)):
            out.append(f"{where}: E01 number needs a value (a string like '47' or '53+')")
        out += _need_str(atom, where, "caption")
        if atom.get("scale") is not None and atom["scale"] not in NUMBER_SCALES:
            out.append(f"{where}: E01 number scale {atom['scale']!r}; scales are {', '.join(NUMBER_SCALES)}")
        out += _check_tone(atom, where)
    elif kind == "list":
        items = atom.get("items")
        if not isinstance(items, list) or not items:
            out.append(f"{where}: E01 list needs items: a non-empty list of runs")
        else:
            for i, item in enumerate(items):
                out += _check_runs(item, where, f"items[{i}]")
        if not isinstance(atom.get("ordered"), bool):
            out.append(f"{where}: E01 list needs ordered: true|false")
    elif kind == "table":
        out += _check_table(atom, where)
    elif kind == "code":
        lines = atom.get("lines")
        if not isinstance(lines, list) or not lines or not all(isinstance(x, str) for x in lines):
            out.append(f"{where}: E01 code needs lines: a non-empty list of strings")
        else:
            for m in atom.get("marks") or []:
                if not isinstance(m, dict) or not isinstance(m.get("line"), int) or not 1 <= m["line"] <= len(lines):
                    out.append(f"{where}: E01 code mark must name a line 1..{len(lines)}, got {m!r}")
                else:
                    out += _check_tone(m, where)
    elif kind == "bars":
        out += _check_bars(atom, where)
    elif kind == "diagram":
        out += _check_diagram(atom, where)
    elif kind == "timeline":
        if atom.get("orientation") not in ORIENTATIONS:
            out.append(f"{where}: E01 timeline orientation must be row|column")
        beats = atom.get("beats")
        if not isinstance(beats, list) or not beats:
            out.append(f"{where}: E01 timeline needs beats: [{{at, text, tone?}}]")
        else:
            for i, b in enumerate(beats):
                if not isinstance(b, dict) or not isinstance(b.get("at"), str):
                    out.append(f"{where}: E01 beat[{i}] needs at: the beat's name")
                    continue
                out += _check_runs(b.get("text"), where, f"beats[{i}].text")
                out += _check_tone(b, where)
    elif kind == "comparison":
        for side in ("left", "right"):
            s = atom.get(side)
            if not isinstance(s, dict) or not isinstance(s.get("title"), str):
                out.append(f"{where}: E01 comparison {side} needs {{title, body: [atoms]}}")
                continue
            out += _check_tone(s, where, "tone")
            for j, item in enumerate(s.get("body") or []):
                if not isinstance(item, dict) or item.get("kind") not in ATOM_KINDS:
                    out.append(f"{where}: E01 {side}.body[{j}] is not an atom of a known kind")
                    continue
                out += _check_fields(item, f"{where} {side}.body[{j}]", nested=True)
        if atom.get("verdict") is not None and atom["verdict"] not in VERDICTS:
            out.append(f"{where}: E01 verdict {atom['verdict']!r}; verdicts are {', '.join(VERDICTS)}")
    elif kind == "group":
        if atom.get("arrangement") not in ARRANGEMENTS:
            out.append(f"{where}: E01 group arrangement must be row|column|grid")
        items = atom.get("items")
        if not isinstance(items, list) or not items:
            out.append(f"{where}: E01 group needs items: a non-empty list of atoms")
        else:
            for j, item in enumerate(items):
                if not isinstance(item, dict) or item.get("kind") not in ATOM_KINDS:
                    out.append(f"{where}: E01 items[{j}] is not an atom of a known kind")
                    continue
                out += _check_fields(item, f"{where} items[{j}]", nested=True)
    elif kind == "receipt":
        out += _need_str(atom, where, "text")
    elif kind == "note":
        out += _need_str(atom, where, "script")
        for i, cue in enumerate(atom.get("cues") or []):
            if (
                not isinstance(cue, dict)
                or not isinstance(cue.get("atom_id"), str)
                or not isinstance(cue.get("text"), str)
            ):
                out.append(f"{where}: E01 cues[{i}] needs {{atom_id, text}}")
    return out


def _check_table(atom: dict, where: str) -> list[str]:
    out: list[str] = []
    cols = atom.get("columns")
    if not isinstance(cols, list) or not cols:
        return [f"{where}: E08 table needs columns: [{{title, share}}]"]
    total = 0.0
    for i, c in enumerate(cols):
        if (
            not isinstance(c, dict)
            or not isinstance(c.get("title"), str)
            or not isinstance(c.get("share"), (int, float))
        ):
            out.append(f"{where}: E08 columns[{i}] needs a title and a numeric share")
            continue
        total += c["share"]
    if out:
        return out
    if abs(total - 100) > 0.01:
        out.append(f"{where}: E08 column shares sum to {total:g}; they must sum to 100")
    rows = atom.get("rows")
    if not isinstance(rows, list) or not rows:
        out.append(f"{where}: E08 table needs rows: [[runs, ...], ...]")
        return out
    for r, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(cols):
            out.append(
                f"{where}: E08 row {r + 1} has {len(row) if isinstance(row, list) else 'no'} cells; the table has {len(cols)} columns"
            )
            continue
        for c, cell in enumerate(row):
            out += _check_runs(cell, where, f"rows[{r}][{c}]")
    if atom.get("role") is not None and atom["role"] not in TABLE_ROLES:
        out.append(f"{where}: E01 table role {atom['role']!r}; roles are {', '.join(TABLE_ROLES)}")
    return out


def _check_bars(atom: dict, where: str) -> list[str]:
    out: list[str] = []
    series = atom.get("series")
    if not isinstance(series, list) or not series:
        return [f"{where}: E01 bars needs series: [{{label, value, caption?, tone?}}]"]
    if not isinstance(atom.get("unit"), str):
        out.append(f"{where}: E01 bars needs unit: the value's unit as a string")
    top = 0.0
    for i, s in enumerate(series):
        if (
            not isinstance(s, dict)
            or not isinstance(s.get("label"), str)
            or not isinstance(s.get("value"), (int, float))
        ):
            out.append(f"{where}: E01 series[{i}] needs a label and a numeric value")
            continue
        top = max(top, float(s["value"]))
        out += _check_tone(s, where)
    mx = atom.get("max")
    if mx is not None and (not isinstance(mx, (int, float)) or mx < top):
        out.append(
            f"{where}: E01 bars max {mx!r} is below the largest value {top:g}; one scale per slide, and it must hold every bar"
        )
    return out


def _inside(x: Any, y: Any, w: Any = 0, h: Any = 0) -> bool:
    return (
        all(isinstance(v, (int, float)) for v in (x, y, w, h))
        and 0 <= x
        and 0 <= y
        and x + w <= DIAGRAM_HOST["w"]
        and y + h <= DIAGRAM_HOST["h"]
    )


def _check_diagram(atom: dict, where: str) -> list[str]:
    out: list[str] = []
    for key in atom:
        if key in _PICTURE_KEYS:
            out.append(
                f"{where}: E04 diagram carries {key!r}; a diagram is geometry (lanes, nodes, edges, buses, paths, labels), never a picture"
            )
    host = atom.get("host")
    if host != DIAGRAM_HOST:
        out.append(f"{where}: E03 diagram host must be {DIAGRAM_HOST} (logical units), got {host!r}")
    nodes = atom.get("nodes") or []
    paths = atom.get("paths") or []
    if not nodes and not paths:
        out.append(
            f"{where}: E04 diagram draws nothing (no nodes, no paths); a picture pasted in its place is refused, draw the geometry"
        )
        return out
    lane_ids: set[str] = set()
    for i, lane in enumerate(atom.get("lanes") or []):
        if not isinstance(lane, dict) or not isinstance(lane.get("id"), str):
            out.append(f"{where}: E07 lanes[{i}] needs an id")
            continue
        lane_ids.add(lane["id"])
        if not _inside(0, lane.get("y"), 0, lane.get("h")):
            out.append(
                f"{where}: E03 lane {lane['id']!r} (y {lane.get('y')!r}, h {lane.get('h')!r}) is outside the 1664x700 host"
            )
        out += _check_tone(lane, where)
    node_ids: set[str] = set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict) or not isinstance(n.get("id"), str):
            out.append(f"{where}: E07 nodes[{i}] needs an id")
            continue
        if n["id"] in node_ids:
            out.append(f"{where}: E06 duplicate node id {n['id']!r}")
        node_ids.add(n["id"])
        if not isinstance(n.get("text"), str):
            out.append(f"{where}: E01 node {n['id']!r} needs text")
        if (
            not _inside(n.get("x"), n.get("y"), n.get("w"), n.get("h"))
            or not (n.get("w") or 0) > 0
            or not (n.get("h") or 0) > 0
        ):
            out.append(
                f"{where}: E03 node {n['id']!r} box ({n.get('x')!r},{n.get('y')!r},{n.get('w')!r},{n.get('h')!r}) is not inside the 1664x700 host"
            )
        if n.get("lane") is not None and n["lane"] not in lane_ids:
            out.append(f"{where}: E07 node {n['id']!r} names lane {n['lane']!r}, which the diagram does not define")
        out += _check_tone(n, where)
    for i, e in enumerate(atom.get("edges") or []):
        if not isinstance(e, dict):
            out.append(f"{where}: E07 edges[{i}] is not an object")
            continue
        for end in ("from", "to"):
            if e.get(end) not in node_ids:
                out.append(f"{where}: E07 edges[{i}] {end} {e.get(end)!r} is no node id; edges reference node ids only")
        if set(e) & _EDGE_COORD_KEYS:
            out.append(f"{where}: E03 edges[{i}] carries coordinates; endpoints belong to the renderer (I8)")
        if e.get("route") is not None and e["route"] not in EDGE_ROUTES:
            out.append(f"{where}: E01 edges[{i}] route {e['route']!r}; routes are {', '.join(EDGE_ROUTES)}")
        if e.get("head") is not None and e["head"] not in EDGE_HEADS:
            out.append(f"{where}: E01 edges[{i}] head {e['head']!r}; heads are {', '.join(EDGE_HEADS)}")
        out += _check_tone(e, where)
    for i, b in enumerate(atom.get("buses") or []):
        if not isinstance(b, dict):
            out.append(f"{where}: E07 buses[{i}] is not an object")
            continue
        for end in ("from", "to"):
            names = b.get(end)
            if not isinstance(names, list) or not names or any(n not in node_ids for n in names):
                out.append(f"{where}: E07 buses[{i}] {end} must be a list of node ids, got {names!r}")
        for j, stub in enumerate(b.get("stubs") or []):
            if not isinstance(stub, dict) or stub.get("to") not in (b.get("to") or []):
                out.append(f"{where}: E07 buses[{i}] stubs[{j}] must name one of the bus's `to` nodes")
            else:
                out += _check_tone(stub, where)
        if b.get("head") is not None and b["head"] not in EDGE_HEADS:
            out.append(f"{where}: E01 buses[{i}] head {b['head']!r}; heads are {', '.join(EDGE_HEADS)}")
    for i, p in enumerate(paths):
        pts = p.get("points") if isinstance(p, dict) else None
        if (
            not isinstance(pts, list)
            or len(pts) < 2
            or not all(isinstance(pt, list) and len(pt) == 2 and _inside(pt[0], pt[1]) for pt in pts)
        ):
            out.append(f"{where}: E07 paths[{i}] needs points: at least two [x, y] pairs inside the 1664x700 host")
        if isinstance(p, dict):
            if p.get("head") is not None and p["head"] not in EDGE_HEADS:
                out.append(f"{where}: E01 paths[{i}] head {p['head']!r}")
            out += _check_tone(p, where)
    for i, lb in enumerate(atom.get("labels") or []):
        if not isinstance(lb, dict) or not isinstance(lb.get("text"), str):
            out.append(f"{where}: E01 labels[{i}] needs text")
            continue
        if not _inside(lb.get("x"), lb.get("y"), lb.get("w"), 0):
            out.append(
                f"{where}: E03 label {lb.get('id') or i!r} at ({lb.get('x')!r},{lb.get('y')!r}) w {lb.get('w')!r} is not inside the host"
            )
        if lb.get("for") is not None and lb["for"] not in node_ids | lane_ids:
            out.append(f"{where}: E07 label {lb.get('id') or i!r} is `for` {lb['for']!r}, which is no node or lane id")
    if atom.get("aria_label") is not None and not isinstance(atom["aria_label"], str):
        out.append(f"{where}: E01 aria_label must be a string (what the paths show, for targets that carry alt text)")
    return out


def _pinned_estimate(diagram: dict) -> int:
    """How many pinned children the slides projection would paint: lanes count twice (band and
    title), nodes and labels once, edges once, a bus as drop + bar + one stub per sink, and all
    paths as one svg."""
    lanes = diagram.get("lanes") or []
    n = 2 * len(lanes) if lanes else 0
    n += len(diagram.get("nodes") or []) + len(diagram.get("labels") or []) + len(diagram.get("edges") or [])
    for b in diagram.get("buses") or []:
        n += 2 + len(b.get("to") or []) if isinstance(b, dict) else 0
    if diagram.get("paths"):
        n += 1
    return n


__all__ = [
    "SCHEMA",
    "CANVAS",
    "MARGIN",
    "DIAGRAM_HOST",
    "MAX_PINNED",
    "ATOM_KINDS",
    "NESTED_KINDS",
    "TOKEN_ROLES",
    "TEMPLATES",
    "HEADLINE_ROLES",
    "STATEMENT_ROLES",
    "TABLE_ROLES",
    "TRANSITIONS",
    "load",
    "validate",
    "lint",
    "used_kinds",
    "coverage",
    "iter_atoms",
]
