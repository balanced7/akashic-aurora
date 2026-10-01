"""The present family's render targets: the Mail-and-Wake scene (22 slides) rendered to all
four built targets in a temp dir, and what each output must and must not contain.

The scene is tests/fixtures/present/mail-and-wake-v2.scene.json (PRESENT_SCENE=<path> overrides it
for a live deck), so the pins hold on any checkout and never name a session's temp directory. Pure Python, no
network (the three.js CDN URL is pinned, not fetched), no browser.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from arsenal.present import scene as sc
from arsenal.present import targets
from arsenal.present.__main__ import main as present_main
from arsenal.present.targets import _core, print_html, three_js, ui_element
from arsenal.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "present" / "mail-and-wake-v2.scene.json"
_OVERRIDE = os.environ.get("PRESENT_SCENE")
SCENE_PATH = Path(_OVERRIDE) if _OVERRIDE and Path(_OVERRIDE).exists() else FIXTURE
BUILT = ("present.slides-html", "present.ui-element", "present.pdf", "present.three-js")


@pytest.fixture(scope="module")
def scene() -> dict:
    s = sc.load(SCENE_PATH)
    assert sc.validate(s) == [], "the scene must validate before a renderer sees it"
    return s


@pytest.fixture(scope="module")
def slide_ids(scene) -> list:
    return [s["id"] for s in _core.ordered_slides(scene)]


@pytest.fixture(scope="module")
def rendered(scene, tmp_path_factory) -> dict:
    """{target id: (out_dir, [paths])} for all four targets, rendered once."""
    root = tmp_path_factory.mktemp("present")
    out = {}
    for mid, render in targets.TARGETS.items():
        out_dir = root / targets.SUBDIR[mid]
        out[mid] = (out_dir, render(scene, out_dir, created_at="2026-09-28T00:00:00Z"))
    return out


def _read(path: Path) -> str:
    data = path.read_bytes()
    assert b"\r\n" not in data, f"{path.name} has CRLF; every file is written as bytes with LF"
    return data.decode("utf-8")


# ---------------------------------------------------------------- every slide, every target
def test_four_targets_are_built_and_listed():
    assert set(targets.TARGETS) == set(BUILT)
    assert targets.resolve("slides") == "present.slides-html"
    assert targets.resolve("3d") == "present.three-js"
    with pytest.raises(ValueError):
        targets.resolve("hologram")


def test_every_slide_id_reaches_every_target(rendered, slide_ids):
    assert len(slide_ids) == 22
    out_dir, paths = rendered["present.slides-html"]
    names = {p.name for p in paths}
    for sid in slide_ids:
        assert f"{sid}.html" in names
        assert f'<section id="{sid}"' in _read(out_dir / "slides" / f"{sid}.html")
    out_dir, paths = rendered["present.ui-element"]
    for sid in slide_ids:
        assert f'id="present-{sid}"' in _read(out_dir / f"{sid}.html")
    out_dir, paths = rendered["present.pdf"]
    page = _read(paths[0])
    for sid in slide_ids:
        assert f'<section id="{sid}"' in page
    out_dir, paths = rendered["present.three-js"]
    deck = _deck_json(_read(paths[0]))
    assert [s["id"] for s in deck["slides"]] == slide_ids


def test_no_target_unit_inside_the_scene_atoms(scene):
    """Renderer knowledge never leaks back into the scene: no px/pt/em/rem/vw/vh in any atom
    payload string (code lines quote source and are exempt, as the validator says)."""
    hits = []

    def walk(value, path, in_code=False):
        if isinstance(value, dict):
            for k, v in value.items():
                if k == "provenance":
                    continue
                walk(v, f"{path}.{k}", in_code or (value.get("kind") == "code" and k == "lines"))
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}[{i}]", in_code)
        elif isinstance(value, str) and not in_code and sc._UNIT_RE.search(value):
            hits.append((path, sc._UNIT_RE.search(value).group(0)))

    for slide in scene["slides"]:
        for a in slide["atoms"]:
            walk(a, f"{slide['id']}.{a['kind']}")
    assert hits == []


# ---------------------------------------------------------------- slides-html: the subset
def test_slides_html_obeys_the_artifact_subset(rendered, slide_ids):
    out_dir, _paths = rendered["present.slides-html"]
    for sid in slide_ids:
        html = _read(out_dir / "slides" / f"{sid}.html")
        sizes = [int(m) for m in re.findall(r"font-size:\s*(\d+)px", html)]
        assert sizes and min(sizes) >= 24, (sid, sorted(set(sizes)))
        for forbidden in ("class=", "margin:", "<script", "<text", "var(", "<style", "z-index"):
            assert forbidden not in html, (sid, forbidden)
        assert not re.search(r"\d(?:em|rem|vw|vh)\b", html), sid
        # format.md lists line-height for text elements (h1-h3, p, ul, ol) only; on <table> it is an
        # `unsupported:` build error (found by the 2026-09-29 audit, the deck's one subset violation)
        assert not re.search(r"<table[^>]*line-height", html), f"{sid}: line-height on <table>"
        assert "padding:128px" in html, sid
        body = html.strip()
        assert body.startswith(f'<section id="{sid}"')
        assert body.endswith("</section>")
        assert body[: -len("</section>")].rstrip().endswith("</aside>"), f"{sid}: the note is the last child"
        assert html.count("<aside>") == 1
        for host in re.findall(r'<div style="position:relative; width:1664px; height:700px">(.*?)\n</div>', html, re.S):
            pinned = host.count("position:absolute") + host.count("<x-connector")
            assert pinned <= sc.MAX_PINNED, (sid, pinned)


def test_slides_html_deck_manifest_is_v4(rendered, slide_ids, scene):
    out_dir, _paths = rendered["present.slides-html"]
    deck = json.loads(_read(out_dir / "deck.json"))
    assert deck["v"] == 4
    assert deck["createdOnFiles"] == {"v": 1, "at": "2026-09-28T00:00:00Z"}
    assert deck["order"] == slide_ids
    assert set(deck["sections"]) == set(scene["sections"])
    assert set(deck["faces"]) == {"ibm-plex-sans", "jetbrains-mono"}
    assert deck["faces"]["ibm-plex-sans"]["href"].startswith("https://fonts.googleapis.com/")
    assert deck["designSystems"] == []
    for sid, desc in _core.section_starts(scene).items():
        assert f'data-section="{_core.esc(desc)}"' in _read(out_dir / "slides" / f"{sid}.html")


def test_diagram_connectors_start_at_box_edges(scene):
    rill = next(s for s in scene["slides"] if s["id"] == "rill")
    diagram = next(a for a in rill["atoms"] if a["kind"] == "diagram")
    g = _core.diagram_geometry(diagram)
    bus = [c for c in g["connectors"] if c["kind"] == "bus"]
    assert len(bus) == 4  # drop, bar, two stubs (a bus turned on its side)
    drop, bar, stub_k1, stub_k2 = bus
    assert (drop["x1"], drop["y1"]) == (380, 350)
    assert drop["x2"] == 538
    assert drop["head"] == "none"
    assert bar["x1"] == bar["x2"] == 538
    assert (bar["y1"], bar["y2"]) == (190, 510)
    assert stub_k1["dashed"]
    assert stub_k1["head"] == "none"
    assert stub_k1["tone"] == "accent"
    assert (stub_k2["x2"], stub_k2["y2"]) == (562, 510)
    assert stub_k2["head"] == "end"
    edges = [c for c in g["connectors"] if c["kind"] == "edge"]
    assert (edges[0]["x1"], edges[0]["y1"], edges[0]["x2"], edges[0]["y2"]) == (1102, 190, 1284, 190)


# ---------------------------------------------------------------- ui-element: the scale wrapper
def test_ui_fragment_scales_the_logical_layout(scene, tmp_path):
    slide = _core.ordered_slides(scene)[1]
    at_400 = ui_element.fragment(scene, slide, 400)
    assert "transform: scale(" in at_400
    assert "transform: scale(0.208333)" in at_400
    assert "width:400px; height:225px" in at_400
    at_1200 = ui_element.fragment(scene, slide, 1200)
    assert "transform: scale(0.625)" in at_1200
    assert "width:1200px; height:675px" in at_1200
    inner_400 = at_400.split("transform: scale(", 1)[1]
    inner_1200 = at_1200.split("transform: scale(", 1)[1]
    assert inner_400.split(")", 1)[1] == inner_1200.split(")", 1)[1], "the 1920x1080 layout inside is identical"
    assert "<script" not in at_400
    assert "width:1920px; height:1080px" in at_400
    note = _core.note_of(slide)
    assert f'title="{_core.esc(note["script"])}"' in at_400
    for atom_id, cue in _core.cue_map(slide).items():
        assert f'title="{_core.esc(cue)}"' in at_400, atom_id
    paths = ui_element.render(scene, tmp_path, width=400, slide=slide["id"])
    assert [p.name for p in paths] == [f"{slide['id']}.html"]


def test_ui_fragment_carries_the_deck_fonts(scene):
    """A panel opened alone, or on a host page that never loaded the deck's fonts, fell back to
    Verdana / Courier New with nothing declared (2026-09-29): the Google Fonts link travels with it."""
    slide = _core.ordered_slides(scene)[0]
    tk = _core.tokens(scene)
    frag = ui_element.fragment(scene, slide, 400)
    assert f'<link rel="stylesheet" href="{_core.esc(tk["href"])}">' in frag
    assert frag.count("<link") == 1
    assert frag.index("<link") < frag.index("<div")


# ---------------------------------------------------------------- pdf: one page per slide
def test_print_page_has_one_page_per_slide(rendered, slide_ids):
    _out_dir, paths = rendered["present.pdf"]
    page = _read(paths[0])
    assert page.count('<div class="page">') == len(slide_ids)
    assert page.count('<div class="footnote">') == len(slide_ids)
    assert "@page { size: 1920px 1080px; margin: 0 }" in page
    assert "break-after: page" in page
    assert "<script" not in page
    doc = print_html.__doc__.lower()
    assert "the browser's print" in doc
    assert "never launches a browser" in doc
    # 0.594 is what this deck's longest note (build, 1208 characters) needs by the family's estimate;
    # the old 0.6 floor rounded it up and let the footnote box clip the note (2026-09-29)
    scale = print_html.footnote_scale(json.loads(SCENE_PATH.read_text(encoding="utf-8")))
    assert print_html.MIN_SCALE <= scale <= print_html.MAX_SCALE
    assert print_html.MIN_SCALE == 0.5
    assert scale == 0.594
    assert "transform: scale(0.594)" in page
    assert print_html.footnote_overflow(json.loads(SCENE_PATH.read_text(encoding="utf-8"))) is None


def test_print_refuses_a_note_its_footnote_cannot_hold(scene, tmp_path):
    """A footnote that ends mid-sentence is a drop no manifest declared: past the floor the render
    refuses, names the slide, and points at --no-footnotes (which drops the note openly)."""
    import copy

    big = copy.deepcopy(scene)
    slide = _core.ordered_slides(big)[3]
    _core.note_of(slide)["script"] = "word " * 900
    overflow = print_html.footnote_overflow(big)
    assert overflow
    assert overflow.startswith(f"slide {slide['id']}:")
    assert "--no-footnotes" in overflow
    with pytest.raises(RuntimeError, match="present.pdf refuses: slide " + slide["id"]):
        print_html.render(big, tmp_path)
    assert not (tmp_path / "print.html").exists()
    assert print_html.render(big, tmp_path, footnotes=False)[0].exists()  # the open drop still renders


def test_print_without_footnotes_is_full_bleed(scene, tmp_path):
    path = print_html.render(scene, tmp_path, footnotes=False)[0]
    page = _read(path)
    assert "footnote" not in page
    assert "transform: scale(1)" in page


# ---------------------------------------------------------------- three-js: one script, one CDN
def _deck_json(page: str) -> dict:
    m = re.search(r"var DECK = (\{.*?\});\n\(function", page, re.S)
    assert m, "the deck data is one JSON literal on the page"
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_three_js_page_loads_one_pinned_script(rendered):
    _out_dir, paths = rendered["present.three-js"]
    page = _read(paths[0])
    scripts = re.findall(r'<script src="([^"]+)"', page)
    assert len(scripts) == 1
    assert scripts[0].startswith("https://cdnjs.cloudflare.com/ajax/libs/three.js/") or scripts[0].startswith(
        "https://cdn.jsdelivr.net/npm/three@"
    )
    assert scripts[0].endswith("/three.min.js")
    assert scripts[0] == three_js.cdn_url()
    assert page.count("<script") == 2  # the CDN script and the page's own
    assert paths[0].stat().st_size < three_js.SIZE_LIMIT
    assert "http://" not in page.replace("http://www.w3.org", "")
    deck = _deck_json(page)
    kinds = {op["t"] for s in deck["slides"] for op in s["ops"]}
    assert kinds == {"rect", "line", "text"}
    for s in deck["slides"]:
        assert s["note"]
        assert s["duration_s"] >= 8
        assert all(op["z"] >= 24 for op in s["ops"] if op["t"] == "text")
    assert "ArrowRight" in page
    assert "CanvasTexture" in page
    assert "caption" in page


def test_three_js_cdn_fallback_maps_versions():
    assert three_js._npm_version("r128") == "0.128.0"
    assert three_js.JSDELIVR.format(v="0.128.0") == "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"


NODE_HARNESS = r"""
var DECK = { faces: { sans: 'sans', mono: 'mono' } };
%s
var calls = [];
var ctx = { font: '', fillStyle: '', measureText: function (t) { return { width: t.length * 10 }; },
            fillText: function (t, x, y) { calls.push([t, x]); } };
var op = { x: 0, y: 0, w: 10000, z: 24, lh: 1.5, wt: 400, f: 'mono', c: '#000', a: 'left',
           r: [['    if x:', 'plain'], ['\n', 'plain'], ['        return', 'plain']] };
drawText(ctx, op, { ca: '#a', cm: '#m' });
var wrapped = { x: 0, y: 0, w: 95, z: 24, lh: 1.5, wt: 400, f: 'sans', c: '#000', a: 'left', r: [['aaaa bbbb cccc', 'plain']] };
var before = calls.length; drawText(ctx, wrapped, { ca: '#a', cm: '#m' });
process.stdout.write(JSON.stringify({ code: calls.slice(0, before), prose: calls.slice(before) }));
"""


@pytest.mark.skipif(__import__("shutil").which("node") is None, reason="node is not on PATH")
def test_three_js_draws_code_indentation(rendered, tmp_path):
    """The page's own drawText, run in node against a stub 2d context: a line that begins on
    purpose keeps its leading spaces (the deck's refusal slide has four indented code lines,
    which the texture used to draw flush left, 2026-09-29); a line the wrap opens still drops
    the space it wrapped on."""
    import subprocess

    page = _read(rendered["present.three-js"][1][0])
    start, end = page.index("  function fontFor("), page.index("  function head(")
    script = tmp_path / "drawtext.js"
    script.write_bytes((NODE_HARNESS % page[start:end]).encode("utf-8"))
    out = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    calls = json.loads(out.stdout)
    assert calls["code"][:2] == [["    ", 0], ["if", 40]], calls["code"]  # indentation drawn, first line
    assert ["        ", 0] in calls["code"]
    assert ["return", 80] in calls["code"]
    words = [c for c in calls["prose"] if c[0].strip()]
    assert words == [["aaaa", 0], ["bbbb", 50], ["cccc", 0]], calls["prose"]  # the wrapped line starts flush


# ---------------------------------------------------------------- manifests and the door
def test_built_manifests_say_exists_with_a_receipt():
    reg = load_registry()
    for mid in BUILT:
        m = reg.get(mid)
        assert m["status"] == "exists", mid
        assert m["receipts"], f"{mid}: exists needs a receipt"
        for kind in sc.ATOM_KINDS:
            row = m["atoms"][kind]
            assert row.get("preserves") or row.get("degrades") or row.get("drops"), (mid, kind)


def test_manifests_declare_what_the_renderers_do():
    """The drops and degrades the 2026-09-29 verification found undeclared, pinned so the tables
    cannot drift back: the shared section builder's degrades reach the panel and the print; the
    print footnote never carried cues; a texture has no alt text, no selectable text and flat
    table cells; a slide's title is shown by the HUD alone."""
    reg = load_registry()
    ui, pdf, three, page = (
        reg.get(m)["atoms"] for m in ("present.ui-element", "present.pdf", "present.three-js", "present.slides-html")
    )
    assert "strong" in ui["statement"]["degrades"]
    assert "plain text" in ui["table"]["degrades"]
    assert "italic" in ui["quote"]["degrades"]
    assert "accent" in ui["number"]["degrades"]
    assert "spaces" in ui["code"]["degrades"]
    assert "for" in ui["diagram"]["degrades"]
    assert "cues" in pdf["note"]["drops"]
    assert "accent" in pdf["number"]["degrades"]
    assert "0.5" in pdf["note"]["degrades"]
    assert "REFUSES" in pdf["note"]["degrades"]
    assert "plain text" in three["table"]["degrades"]
    assert "aria_label" in three["diagram"]["drops"]
    assert three["note"]["drops"] == "cues"
    assert "leading spaces" in three["code"]["preserves"]
    for kind in sc.ATOM_KINDS:
        if kind not in ("diagram", "note"):
            assert three[kind].get("drops", "").startswith("selectable text"), kind
    assert "aria_label" in page["diagram"]["degrades"]
    for mid in BUILT:
        assert "title" in reg.get(mid)["deck"], mid


def test_door_renders_and_writes_a_take(tmp_path, capsys):
    rc = present_main(
        ["render", str(SCENE_PATH), "--to", "ui", "--out", str(tmp_path), "--width", "1200", "--slide", "cover"]
    )
    assert rc == 0
    assert (tmp_path / "ui" / "cover.html").exists()
    takes = list((tmp_path / "takes").glob("*-present.ui-element.json"))
    assert len(takes) == 1
    take = json.loads(takes[0].read_text(encoding="utf-8"))
    assert take["target"] == "present.ui-element"
    assert len(take["scene"]["sha256"]) == 64
    cover = take["per_slide"]["cover"]
    assert "note" in cover["degraded"]
    assert "note" not in cover["preserved"]
    assert set(cover["preserved"]) == {"headline", "label", "statement", "receipt"}
    rc = present_main(["render", str(SCENE_PATH), "--to", "pdf", "--out", str(tmp_path), "--dry"])
    assert rc == 0
    assert not (tmp_path / "print").exists()
    out = capsys.readouterr().out
    assert "dry: nothing written" in out
    assert present_main(["targets", "--scene", str(SCENE_PATH)]) == 0
    assert "renderer built" in capsys.readouterr().out
