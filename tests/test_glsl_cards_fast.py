"""Fast pins for module test cards (arsenal/shaders/cards.py): parsing, composition, refusals, the NaN probe's shader,
the picture checks, and the receipt a render leaves -- everything except the GPU, which tests/test_glsl_cards.py covers.

A CARD is the test pattern a module draws of itself, the way a TV engineer puts colour bars on a screen so a fault shows
as a wrong bar instead of "the picture looks off". It lives in arsenal/web/glsl/cards/<module-name>.card (NOT .glsl, so
the module loader never mistakes it for a module): a `//!` JSON header, then a Shadertoy mainImage body. The card verb
composes Common from the house library (modules.load_library().compose(uses)) and Image from the body.

The fixtures under tests/fixtures/glsl_cards/ are written fresh for these tests (Apache-2.0): a synthetic library of
three modules the house has not built yet (core-const, core-shaping, debug-views), the two EXAMPLE cards (a curve plot and a
ramp-and-field card), and three detector drills (NaN, flat, does-not-compile) for the slow test.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from arsenal.shaders import cards as K
from arsenal.shaders import cli
from arsenal.shaders import modules as M
from arsenal.shaders import render as R
from arsenal.shaders import serve as S

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "tests" / "fixtures" / "glsl_cards"
FIX_LIB = FIX / "lib"
FIX_CARDS = FIX / "cards"
FIX_DRILLS = FIX / "drills"
SWIFT = "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)"

BODY = "void mainImage(out vec4 color, in vec2 pixel) {\n    color = vec4(shpGain(0.5, 2.0));\n}\n"


def card_text(header: dict, body: str = BODY) -> str:
    return "//! " + json.dumps(header) + "\n" + body


def fix_lib():
    return M.load_library([FIX_LIB], strict=False)


# ---------------------------------------------------------------------------------------------------------- parsing

def test_a_one_line_header_parses_with_its_defaults():
    c = K.parse_card(card_text({"card": "core-shaping"}), "core-shaping.card")
    assert c.name == "core-shaping"
    assert c.uses == ("core-shaping",)          # a card named after a module uses that module unless it says otherwise
    assert c.times == (0.0,) and c.size == (320, 180) and c.note == ""
    assert c.body == BODY and "//!" not in c.body


def test_a_header_may_span_several_lines_like_a_module_header():
    text = ('//! {"card": "core-shaping", "uses": ["core-shaping", "core-const"],\n'
            '//!  "t": [0, 2.5], "size": [160, 90],\n'
            '//!  "note": "look for the S"}\n' + BODY)
    c = K.parse_card(text, "core-shaping.card")
    assert c.uses == ("core-shaping", "core-const") and c.times == (0.0, 2.5) and c.size == (160, 90)
    assert c.note == "look for the S" and c.body == BODY
    wrapped = K.parse_card('//! {"card": "x", "uses": [], "note": "one line\n//!   and the next"}\n' + BODY, "x.card")
    assert wrapped.note == "one line and the next"     # the continuation's indent does not survive into the note


def test_crlf_and_a_bom_read_as_the_same_card():
    plain = K.parse_card(card_text({"card": "x", "uses": []}), "x.card")
    crlf = K.parse_card("﻿" + card_text({"card": "x", "uses": []}).replace("\n", "\r\n"), "x.card")
    assert crlf.body == plain.body and crlf.header == plain.header


@pytest.mark.parametrize("text,why", [
    (BODY, "no //! header"),
    ("//! {not json}\n" + BODY, "not JSON"),
    (card_text({"uses": []}), "needs \"card\""),
    (card_text({"card": "../escape"}), "letters, digits"),
    (card_text({"card": "x", "uses": "core-shaping"}), '"uses"'),
    (card_text({"card": "x", "uses": [1]}), '"uses"'),
    (card_text({"card": "x", "t": 2}), '"t"'),
    (card_text({"card": "x", "t": [-1]}), '"t"'),
    (card_text({"card": "x", "t": [True]}), '"t"'),
    (card_text({"card": "x", "t": []}), '"t"'),
    (card_text({"card": "x", "size": [320]}), '"size"'),
    (card_text({"card": "x", "size": [0, 180]}), '"size"'),
    (card_text({"card": "x", "size": [320.5, 180]}), '"size"'),
    (card_text({"card": "x", "note": 3}), '"note"'),
    (card_text({"card": "x"}, "void main() { }\n"), "mainImage"),
    (card_text({"card": "x"}, "// void mainImage(out vec4 c, in vec2 f) {}\nvoid main() {}\n"), "mainImage"),
])
def test_a_bad_card_is_refused_naming_the_file_and_the_field(text, why):
    with pytest.raises(K.CardError) as err:
        K.parse_card(text, "x.card")
    assert "x.card" in str(err.value) and why in str(err.value)


def test_the_card_name_must_match_its_file_name():
    with pytest.raises(K.CardError) as err:
        K.parse_card(card_text({"card": "core-shaping"}), "some/dir/other-name.card")
    assert "other-name" in str(err.value) and "core-shaping" in str(err.value)


def test_cards_are_listed_by_name_and_found_by_name(tmp_path):
    for n in ("b-card", "a-card"):
        (tmp_path / f"{n}.card").write_text(card_text({"card": n, "uses": []}), encoding="utf-8")
    (tmp_path / "not-a-card.glsl").write_text("//! {}\n", encoding="utf-8")
    assert K.list_cards(tmp_path) == ["a-card", "b-card"]
    assert K.load_card("b-card", tmp_path).name == "b-card"
    with pytest.raises(K.CardError, match="no card named 'c-card'"):
        K.load_card("c-card", tmp_path)
    with pytest.raises(K.CardError):
        K.card_path("../b-card", tmp_path)       # a name is a name, never a path


def test_a_card_is_never_read_as_a_module(tmp_path):
    """The reason a card is .card and not .glsl: load_library walks *.glsl, and a card body (a mainImage program) in
    the module library would be a module with no header, which strict loading refuses and blanks every surface."""
    lib = tmp_path / "glsl"
    (lib / "cards").mkdir(parents=True)
    (lib / "core").mkdir()
    (lib / "core" / "shaping.glsl").write_text((FIX_LIB / "core" / "shaping.glsl").read_text(encoding="utf-8"),
                                               encoding="utf-8")
    (lib / "cards" / "core-shaping.card").write_text((FIX_CARDS / "core-shaping.card").read_text(encoding="utf-8"),
                                                     encoding="utf-8")
    loaded = M.load_library([lib], strict=True)
    assert loaded.names() == ["core-shaping"] and not loaded.problems
    assert K.CARDS_DIR == M.LIBRARY_DIR / "cards"


# ------------------------------------------------------------------------------------------------------ composition

def test_build_card_composes_common_from_the_library_and_image_from_the_body():
    lib = fix_lib()
    shader = K.build_card("debug-views", library=lib, cards_dir=FIX_CARDS)
    card = K.load_card("debug-views", FIX_CARDS)
    common, image = shader["renderpass"]
    assert common == {"name": "Common", "type": "common", "code": lib.compose(["debug-views"], target="toy"),
                      "inputs": [], "outputs": [], "description": ""}
    assert image["name"] == "Image" and image["type"] == "image" and image["code"] == card.body
    assert image["inputs"] == [] and image["outputs"] == [{"id": "4dfGRr", "channel": 0}]
    # the dependency closure travels with the card: debug-views calls core-shaping and uses core-const's TAU
    facts = shader["card"]
    assert facts["api"] == K.CARD_API and facts["name"] == "debug-views" and facts["uses"] == ["debug-views"]
    assert facts["modules"] == ["core-const", "core-shaping", "debug-views"]
    assert facts["composed_sha256"] in common["code"].splitlines()[2]
    assert facts["t"] == [0.0, 1.0] and facts["size"] == [320, 180] and facts["probe"] is False
    # Shadertoy-shaped: the runtime and render.py read it as any saved shader
    assert R.unwrap_json(shader) is shader
    assert shader["info"]["id"] == "card-debug-views"
    assert not R.SHADERTOY_ID.fullmatch(shader["info"]["id"])   # never mistaken for someone's published shader


def test_build_card_takes_lib_dirs_when_no_library_is_given():
    a = K.build_card("core-shaping", cards_dir=FIX_CARDS, lib_dirs=[FIX_LIB])
    b = K.build_card("core-shaping", library=fix_lib(), cards_dir=FIX_CARDS)
    assert a == b


def test_a_card_that_uses_no_module_has_no_common_pass(tmp_path):
    (tmp_path / "bare.card").write_text(card_text({"card": "bare", "uses": []},
                                                  "void mainImage(out vec4 c, in vec2 f) { c = vec4(1.0); }\n"),
                                        encoding="utf-8")
    shader = K.build_card("bare", library=fix_lib(), cards_dir=tmp_path)
    assert [p["type"] for p in shader["renderpass"]] == ["image"] and shader["card"]["modules"] == []


def test_a_missing_module_is_refused_naming_it_and_the_card(tmp_path):
    (tmp_path / "ghost.card").write_text(card_text({"card": "ghost", "uses": ["core-shaping", "noise-ghost"]}),
                                         encoding="utf-8")
    with pytest.raises(K.CardError) as err:
        K.build_card("ghost", library=fix_lib(), cards_dir=tmp_path)
    msg = str(err.value)
    assert "'ghost'" in msg and "'noise-ghost'" in msg


def test_a_quarantined_module_is_refused_naming_its_file(tmp_path):
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "a.glsl").write_text('//! {"name": "first", "kind": "helper"}\nfloat f(float x) { return x; }\n',
                                    encoding="utf-8")
    (lib_dir / "b.glsl").write_text('//! {"name": "second", "kind": "helper"}\nfloat f(float x) { return -x; }\n',
                                    encoding="utf-8")
    (tmp_path / "second.card").write_text(card_text({"card": "second"}), encoding="utf-8")
    lib = M.load_library([lib_dir], strict=False)
    assert "second" in lib.lost_modules                  # b.glsl lost the clash over f(), loading leniently
    with pytest.raises(K.CardError) as err:
        K.build_card("second", library=lib, cards_dir=tmp_path)
    assert "'second'" in str(err.value) and "quarantined" in str(err.value) and "b.glsl" in str(err.value)


def test_a_missing_module_says_when_files_were_quarantined(tmp_path):
    """A file whose header does not parse has no name the loader can know, so the refusal points at the problems."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "c.glsl").write_text('//! {"name": "gone", "kind": "helper"\nfloat h() { return 1.0; }\n',
                                    encoding="utf-8")
    (tmp_path / "gone.card").write_text(card_text({"card": "gone"}), encoding="utf-8")
    with pytest.raises(K.CardError) as err:
        K.build_card("gone", library=M.load_library([lib_dir], strict=False), cards_dir=tmp_path)
    assert "'gone'" in str(err.value) and "c.glsl" in str(err.value)


def test_a_card_calling_a_module_it_does_not_use_is_refused_naming_the_module_to_add(tmp_path):
    body = "void mainImage(out vec4 c, in vec2 f) { c = vec4(dbgHeatRamp(f.x), 1.0); }\n"
    (tmp_path / "core-shaping.card").write_text(card_text({"card": "core-shaping"}, body), encoding="utf-8")
    with pytest.raises(K.CardError) as err:
        K.build_card("core-shaping", library=fix_lib(), cards_dir=tmp_path)
    assert "dbgHeatRamp" in str(err.value) and "'debug-views'" in str(err.value)


def test_a_composition_the_library_refuses_becomes_a_card_error(tmp_path):
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "snip.glsl").write_text('//! {"name": "snip", "kind": "modifier"}\ncol *= 0.5;\n', encoding="utf-8")
    (tmp_path / "snip.card").write_text(card_text({"card": "snip"}), encoding="utf-8")
    with pytest.raises(K.CardError) as err:
        K.build_card("snip", library=M.load_library([lib_dir], strict=False), cards_dir=tmp_path)
    assert "snip" in str(err.value) and "snippet" in str(err.value)


def test_both_example_cards_build_against_the_fixture_library():
    lib = fix_lib()
    assert K.list_cards(FIX_CARDS) == ["core-shaping", "debug-views"]
    for name in K.list_cards(FIX_CARDS):
        shader = K.build_card(name, library=lib, cards_dir=FIX_CARDS)
        assert shader["card"]["modules"], name


def test_every_house_card_parses_and_builds_against_the_house_library():
    """Fast half of the slow test: a card that names a module the library lacks fails here, without a GPU."""
    names = K.list_cards()
    if not names:
        pytest.skip("no cards yet under arsenal/web/glsl/cards")
    lib = M.load_library(strict=False)
    for name in names:
        K.build_card(name, library=lib)


# ------------------------------------------------------------------------------------------------------- the NaN probe

def test_the_probe_wraps_the_card_and_paints_non_finite_pixels_magenta():
    lib = fix_lib()
    plain = K.build_card("core-shaping", library=lib, cards_dir=FIX_CARDS)
    probe = K.build_card("core-shaping", library=lib, cards_dir=FIX_CARDS, probe=True)
    assert probe["renderpass"][0] == plain["renderpass"][0]            # Common untouched
    code = probe["renderpass"][1]["code"]
    assert code == K.probe_code(plain["renderpass"][1]["code"])
    assert len(re.findall(r"\bvoid\s+mainImage\s*\(", code)) == 1      # one entry point: the wrapper
    for needle in ("isnan", "isinf", "floatBitsToUint", "0x7f800000u", "vec4(1.0, 0.0, 1.0, 1.0)", "0.5"):
        assert needle in code, needle
    assert probe["card"]["probe"] is True and probe["info"]["id"] == "card-core-shaping-nan"
    # the card's own entry point is renamed, so the only mainImage left is the wrapper's, after the card's code
    wrapped = K.probe_code("void mainImage(out vec4 a, in vec2 b) { a = vec4(1.0); }")
    before, _, after = wrapped.partition("void mainImage")
    assert "mainImage" not in before and "mainImage" not in after


# ---------------------------------------------------------------------------------------------------- picture checks

def _png(path: Path, pixels, size=(16, 8)) -> Path:
    from PIL import Image
    im = Image.new("RGB", size)
    im.putdata(pixels if isinstance(pixels, list) else [pixels] * (size[0] * size[1]))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
    return path


def test_flat_means_every_channel_barely_varies(tmp_path):
    w, h = 16, 8
    flat = K.image_facts(_png(tmp_path / "flat.png", (102, 102, 102)))
    assert flat["flat"] is True and max(flat["std"]) < K.FLAT_STD
    dither = K.image_facts(_png(tmp_path / "dither.png", [(100 + (i % 2), 100, 100) for i in range(w * h)]))
    assert dither["flat"] is True                     # a one-level dither is still one flat colour
    ramp = K.image_facts(_png(tmp_path / "ramp.png", [(i * 2, 0, 0) for i in range(w * h)]))
    assert ramp["flat"] is False
    line = [(15, 17, 20)] * (w * h)
    for x in range(w):
        line[3 * w + x] = (90, 150, 255)              # one thin line on a dark plot is a picture, not a flat frame
    assert K.image_facts(_png(tmp_path / "line.png", line))["flat"] is False


def test_magenta_is_counted_and_a_dimmed_picture_never_is(tmp_path):
    w, h = 16, 8
    px = [(128, 0, 128)] * (w * h)                    # the probe's brightest finite pixel: half of pure magenta
    for i in range(5):
        px[i] = (255, 0, 255)
    assert K.magenta_pixels(_png(tmp_path / "probe.png", px)) == 5
    assert K.magenta_pixels(_png(tmp_path / "none.png", (128, 0, 128))) == 0


# ------------------------------------------------------------------------------------- rendering, with a fake driver

class FakeLab:
    def __init__(self, port):
        self.port = port

    def __enter__(self):
        return "http://127.0.0.1:1"

    def __exit__(self, *exc):
        return False


def _fake_driver(monkeypatch, tmp_path, picture):
    """render.run_jobs stood in by a function that 'draws' with Pillow: picture(job, t, probe) -> list of RGB pixels."""
    seen = {"jobs": [], "calls": 0}

    def run_jobs(jobs, label, lock_wait_min=10, quiet=False):
        seen["calls"] += 1
        seen["jobs"] += list(jobs)
        rows = {}
        for job in jobs:
            q = parse_qs(urlparse(job.url).query)
            times = [float(t) for t in q["t"][0].split(",")]
            probe = job.prefix == K.PROBE_PREFIX
            frames = []
            for t in times:
                path = _png(Path(job.out_dir) / f"{job.prefix}t{t:.2f}.png", picture(job, t, probe), job.size)
                frames.append({"t": t, "file": str(path), "ms": 12, "bytes": path.stat().st_size, "frames": 1,
                               "frame": 0, "reset": False, "jumped": True})
            rows[job.key] = {"key": job.key, "url": job.url, "status": "done", "wall_ms": 50, "frames": frames,
                             "render": {"ok": True, "renderer": SWIFT, "warmMs": 1.5,
                                        "compile": {"ok": True, "drawable": True, "warnings": [],
                                                    "passes": [{"name": "Image", "type": "image", "key": "image",
                                                                "ok": True, "parity": "full"}]}}}
        return {"run_dir": str(tmp_path / "run"), "software": {"webgl": {"renderer": SWIFT}}, "chrome": "fake",
                "rows": rows, "bursts": [{"n": 1}], "refused": None, "error": None}

    monkeypatch.setattr(R, "run_jobs", run_jobs)
    monkeypatch.setattr(R, "_Lab", FakeLab)
    monkeypatch.setattr(S, "JOBS", tmp_path / "jobs")
    return seen


def _gradient(job, t, probe):
    w, h = job.size
    return [(min(255, x * 4) // (2 if probe else 1), 40, 90 // (2 if probe else 1)) for _ in range(h) for x in range(w)]


def test_render_plans_two_jobs_per_card_and_writes_a_receipt(monkeypatch, tmp_path):
    seen = _fake_driver(monkeypatch, tmp_path, _gradient)
    out = tmp_path / "out"
    report = K.render_cards(["core-shaping", "debug-views"], cards_dir=FIX_CARDS, lib_dirs=[FIX_LIB],
                            out_root=out, allow_tracked=True, quiet=True)
    assert seen["calls"] == 1                                  # every card in one run: run_jobs makes the bursts
    keys = [j.key for j in seen["jobs"]]
    assert keys == ["card-core-shaping", "card-core-shaping-nan", "card-debug-views", "card-debug-views-nan"]
    assert [j.prefix for j in seen["jobs"]] == ["", K.PROBE_PREFIX] * 2
    assert {Path(j.out_dir) for j in seen["jobs"]} == {out / "core-shaping", out / "debug-views"}
    assert all(j.allow_tracked for j in seen["jobs"])         # out lies outside state/, as the caller allowed
    dv = [j for j in seen["jobs"] if j.key == "card-debug-views"][0]
    assert dv.size == (320, 180) and "t=0,1" in dv.url and "/lab/render.html?" in dv.url
    probe_job = [j for j in seen["jobs"] if j.key == "card-debug-views-nan"][0]
    src = parse_qs(urlparse(probe_job.url).query)["src"][0]             # http://127.0.0.1:1/jobs/<file>.json
    staged = json.loads((tmp_path / "jobs" / urlparse(src).path.rsplit("/", 1)[-1]).read_text(encoding="utf-8"))
    assert "floatBitsToUint" in staged["renderpass"][-1]["code"]
    rows = {r["name"]: r for r in report["cards"]}
    assert set(rows) == {"core-shaping", "debug-views"}
    for name, row in rows.items():
        assert row["ok"] is True and row["compile_ok"] is True and row["flat"] is False and row["nan_pixels"] == 0
        receipt = json.loads((out / name / "receipt.json").read_text(encoding="utf-8"))
        assert R.validate_receipt(receipt) == []
        assert receipt["card"]["ok"] is True and receipt["card"]["name"] == name
        assert receipt["license"] == "Apache-2.0" and receipt["source"]["path"] == str(out / name / "card.json")
        assert (out / name / "card.json").is_file() and (out / name / "probe.json").is_file()
        frames = receipt["card"]["frames"]
        assert [f["t"] for f in frames] == list(K.load_card(name, FIX_CARDS).times)
        assert all(Path(f["png"]).is_file() and Path(f["nan_png"]).is_file() for f in frames)
        assert row["ms"] == 1.5                               # the warm frame: per-frame cost without the compile


def test_nan_and_flat_make_a_card_fail(monkeypatch, tmp_path):
    def picture(job, t, probe):
        w, h = job.size
        if "core-shaping" in job.key and probe:
            return [(255, 0, 255) if i < 7 else (20, 20, 20) for i in range(w * h)]
        if "debug-views" in job.key:
            return [(60, 60, 60)] * (w * h)
        return _gradient(job, t, probe)
    _fake_driver(monkeypatch, tmp_path, picture)
    report = K.render_cards(["core-shaping", "debug-views"], cards_dir=FIX_CARDS, lib_dirs=[FIX_LIB],
                            out_root=tmp_path / "out", allow_tracked=True, quiet=True)
    rows = {r["name"]: r for r in report["cards"]}
    assert rows["core-shaping"]["nan_pixels"] == 7 and rows["core-shaping"]["ok"] is False
    assert rows["core-shaping"]["flat"] is False
    assert rows["debug-views"]["flat"] is True and rows["debug-views"]["ok"] is False
    assert rows["debug-views"]["nan_pixels"] == 0


def test_a_card_that_does_not_build_is_reported_and_the_rest_still_render(monkeypatch, tmp_path):
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    for p in FIX_CARDS.glob("*.card"):
        (cards_dir / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    (cards_dir / "ghost.card").write_text(card_text({"card": "ghost", "uses": ["noise-ghost"]}), encoding="utf-8")
    seen = _fake_driver(monkeypatch, tmp_path, _gradient)
    report = K.render_cards(K.list_cards(cards_dir), cards_dir=cards_dir, lib_dirs=[FIX_LIB],
                            out_root=tmp_path / "out", allow_tracked=True, quiet=True)
    rows = {r["name"]: r for r in report["cards"]}
    assert rows["ghost"]["ok"] is False and "noise-ghost" in rows["ghost"]["error"]
    assert rows["core-shaping"]["ok"] is True and "card-ghost" not in [j.key for j in seen["jobs"]]


def test_out_outside_state_is_refused_before_any_render_unless_allowed(monkeypatch, tmp_path):
    seen = _fake_driver(monkeypatch, tmp_path, _gradient)
    with pytest.raises(K.CardError) as err:
        K.render_cards(["core-shaping"], cards_dir=FIX_CARDS, lib_dirs=[FIX_LIB], out_root=tmp_path / "out")
    assert "outside" in str(err.value) and seen["calls"] == 0
    assert K.CARDS_OUT == R.STATE / "cards"


# ------------------------------------------------------------------------------------------------------------- the verb

def test_the_card_verb_is_registered():
    import inspect
    assert '"cards"' in inspect.getsource(cli._load_extensions)
    cli._load_extensions()
    assert "card" in cli.VERBS
    ns = cli.build_parser().parse_args(["card", "--all", "--render", "--json"])
    assert ns.all and ns.render and ns.json and ns.name is None
    ns = cli.build_parser().parse_args(["card", "core-shaping"])
    assert ns.name == "core-shaping" and not ns.render


def test_the_verb_builds_a_card_without_rendering(tmp_path, capsys):
    out = tmp_path / "out"
    code = cli.main(["card", "debug-views", "--cards-dir", str(FIX_CARDS), "--dir", str(FIX_LIB), "--out", str(out),
                     "--allow-tracked", "--json"])
    assert code == 0
    shader = json.loads((out / "debug-views" / "card.json").read_text(encoding="utf-8"))
    assert shader["card"]["modules"] == ["core-const", "core-shaping", "debug-views"]
    printed = json.loads(capsys.readouterr().out)
    assert printed["cards"][0]["name"] == "debug-views" and printed["cards"][0]["card_json"].endswith("card.json")


def test_the_verb_refuses_a_missing_module_with_exit_2(tmp_path, capsys):
    (tmp_path / "ghost.card").write_text(card_text({"card": "ghost", "uses": ["noise-ghost"]}), encoding="utf-8")
    code = cli.main(["card", "ghost", "--cards-dir", str(tmp_path), "--dir", str(FIX_LIB), "--out",
                     str(tmp_path / "out"), "--allow-tracked"])
    assert code == 2 and "noise-ghost" in capsys.readouterr().err


def test_the_verb_needs_a_name_or_all(capsys):
    assert cli.main(["card"]) == 2
    assert cli.main(["card", "x", "--all"]) == 2
