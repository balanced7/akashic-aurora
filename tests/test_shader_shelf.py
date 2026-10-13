"""Pins for the Shelf (arsenal/shaders/shelf.py): Daniel's Loved shaders in the house tooling, in the only form the
licence line allows -- browsable, dissected, linked to the atlas parts and groups that rebuild them, never copied.

WHY THESE PINS. The Shelf joins five sources (the corpus meta, the dissector, the atlas, the study notes and the renders)
into one private index, state/arsenal/shaders/shelf/index.json. Four promises are worth a test each:

  * every entry is complete: a page can draw a card from it without a second lookup;
  * a shader whose own header forbids reuse is caught even when the corpus meta missed it (Warping's header says so in
    plain words, and the meta read it as Shadertoy's default), and such a shader is study only: its study note is listed,
    its images are not, whatever sits in the renders folder;
  * the dissector's tags land on atlas categories through the atlas's own table (dissect --atlas is that mapping);
  * nothing is written outside state/: the index is private, because it names other people's work.

Every shader, header and note here is synthetic and written for this file in our own words; the real corpus is read in
one test only (the last), which is skipped when the corpus is absent and writes nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from arsenal.shaders import cli
from arsenal.shaders import corpus as C
from arsenal.shaders import dissect as D
from arsenal.shaders import shelf as SH

ROOT = Path(__file__).resolve().parents[1]

# The fields a card needs, every one present on every entry.
REQUIRED = ("rank", "id", "title", "short", "author", "url", "licence", "study_only", "study_only_reason", "tags",
            "categories", "unmapped_tags", "groups", "parts", "atlas_links", "study", "renders")


# ------------------------------------------------------------------------------------------------ the fixture
def _shader(sid: str, name: str, code: str) -> dict:
    return {"ver": "0.1", "info": {"id": sid, "name": name, "username": "a.stranger", "date": "1700000000",
                                   "likes": 3, "viewed": 9, "tags": ["test"], "description": ""},
            "renderpass": [{"name": "Image", "type": "image", "code": code, "inputs": [],
                            "outputs": [{"id": "4dfGRr", "channel": 0}]}]}


BODY = "void mainImage(out vec4 ink, in vec2 at) { ink = vec4(at.x * 0.001, 0.2, 0.3, 1.0); }\n"

# Headers in our own words. QUIET waives everything; GARDEN reserves everything in a phrasing the corpus meta's own
# patterns do not know; SLOW names a plain licence and then warns a reader off a slow helper ("DO NOT USE"), which is a
# code comment, not a licence; RULED says nothing restrictive, but the atlas marks it study only by ruling.
QUIET = "// Released to the public domain (CC0). Take it.\n" + BODY
GARDEN = ("// Made by a.stranger. I keep every right to this piece.\n"
          "// You may not copy it, host it or sell it, here or anywhere.\n" + BODY)
SLOW = ("// License Creative Commons Attribution-NonCommercial-ShareAlike 3.0\n"
        "// the helper below is slow, DO NOT USE it in a hot loop\n" + BODY)
RULED = "// a plain sketch with no licence words at all\n" + BODY

SHADERS = [("abcDE1", "Quiet Field", QUIET), ("abcDE2", "Locked Garden", GARDEN), ("abcDE3", "Slow Helper", SLOW),
           ("abcDE4", "Ruled Out", RULED)]

ATLAS = {
    "api": "arsenal.shader-atlas/v1",
    "categories": [{"id": "B1", "name": "Lattice noise", "family": "B"}, {"id": "B3", "name": "Fractal sums", "family": "B"},
                   {"id": "C4", "name": "Folds and polar", "family": "C"}, {"id": "D1", "name": "Primitives", "family": "D"},
                   {"id": "D4", "name": "Repetition", "family": "D"}, {"id": "E3", "name": "Marching", "family": "E"},
                   {"id": "H1", "name": "Encoding", "family": "H"}],
    "parts": [{"id": "B3.01", "category": "B3", "family": "B", "functions": ["fbmShelfTest"], "module": "noise/fbm.glsl",
               "status": "P0", "cost": "C1", "exemplars": ["abcDE1"]},
              {"id": "D4.01", "category": "D4", "family": "D", "functions": ["repShelfTest"], "module": "sdf/rep.glsl",
               "status": "P1", "cost": "C0", "exemplars": ["abcDE2", "abcDE3"]}],
    "groups": [{"name": "fog-test", "line": "a test group", "status": "P0", "cost": "C2",
                "exemplars": ["abcDE1", "abcDE3"], "study_only": []},
               {"name": "garden-test", "line": "a study-only exemplar", "status": "P1", "cost": "C1",
                "exemplars": ["abcDE2", "abcDE4"], "study_only": ["abcDE4"]}],
    "loved": [{"id": "abcDE1", "short": "Quiet", "study_only": False},
              {"id": "abcDE2", "short": "Garden", "study_only": False},   # the header detector alone must catch it
              {"id": "abcDE3", "short": "Slow", "study_only": False},
              {"id": "abcDE4", "short": "Ruled", "study_only": True}],
    "tags": {"exact": {"noise.fbm": ["B3"], "color.gamma": ["H1"], "domain.repeat": ["D4", "C4"],
                       "raymarch.sphere_trace": ["E3"], "sdf.sphere": ["D1"]},
             "groups": {"noise": ["B1"]}},
}

FAKE_TAGS = {"abcDE1": ["noise.fbm", "color.gamma", "noise.value", "made.up_tag"],
             "abcDE2": ["domain.repeat"],
             "abcDE3": ["raymarch.sphere_trace", "sdf.sphere"],
             "abcDE4": []}

NOTE = """# Study: {name} ({sid})

- **Name:** {name}

## 1. What you see

A soft field.

## 4. Techniques

### 4.1 Soft circle -- `image.glsl:3`

words

### 4.2 Gradient ramp -- `image.glsl:4`

words

## 5. Craft secrets

More words.
"""


def _fake_dissect(sid, min_conf=D.MIN_CONF, corpus=None):
    return {"id": sid, "tags": list(FAKE_TAGS[sid]), "min_conf": min_conf}


def _png(path: Path) -> Path:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (8, 4), (20, 30, 40))
    im.putpixel((1, 1), (200, 10, 10))
    im.save(path)
    return path


def _receipt(d: Path, fps: int, ts=(1.0, 4.0)) -> None:
    frames = [{"t": t, "png": str(_png(d / f"t{t:.2f}.png")), "ms": 5, "bytes": 10, "flat": False, "mean_luma": 30.0}
              for t in ts]
    (d / "receipt.json").write_text(json.dumps({"api": "arsenal.shader-render/v1", "ok": True, "status": "done",
                                                "request": {"t": list(ts), "w": 480, "h": 270, "fps": fps},
                                                "frames": frames, "first_error": None}), encoding="utf-8")


def _filmstrip(d: Path, fps: int) -> None:
    sheet = _png(d / "filmstrip.png")
    frames = [{"t": t, "png": str(_png(d / "filmstrip" / f"t{t:.2f}.png"))} for t in (0.0, 8.0)]
    (d / "filmstrip.json").write_text(json.dumps({"api": "arsenal.shader-filmstrip/v1", "ok": True, "status": "done",
                                                  "request": {"t": [0.0, 8.0], "fps": fps, "frames": 2, "to": 8.0},
                                                  "frames": frames, "sheet": str(sheet)}), encoding="utf-8")


@pytest.fixture()
def world(tmp_path):
    """A synthetic corpus, atlas, study folder and renders folder, all under one temp state/ root."""
    state = tmp_path / "state"
    base = state / "arsenal" / "shaders"
    corpus = base / "corpus"
    for sid, name, code in SHADERS:
        C.save_shader(_shader(sid, name, code), corpus)
    (corpus / "sets.json").write_text(json.dumps({"loved": [s[0] for s in SHADERS], "_updated": ["x"]}),
                                      encoding="utf-8")
    study = base / "study"
    study.mkdir(parents=True)
    for sid, name, _ in SHADERS:
        (study / f"{sid}.md").write_text(NOTE.format(name=name, sid=sid), encoding="utf-8")
    renders = base / "renders"
    for sid, fps in (("abcDE1", 60), ("abcDE2", 60), ("abcDE3", 30), ("abcDE4", 60)):
        _receipt(renders / sid, fps)
        _filmstrip(renders / sid, fps)
    return {"tmp": tmp_path, "state": state, "corpus": corpus, "study": study, "renders": renders,
            "out": base / "shelf" / "index.json"}


def _build(w):
    return SH.build(corpus=w["corpus"], atlas=ATLAS, study_dir=w["study"], renders_dir=w["renders"],
                    dissect=_fake_dissect)


def _entry(index, sid):
    return next(e for e in index["shaders"] if e["id"] == sid)


# --------------------------------------------------------------------------------------- the index, entry by entry
def test_every_entry_is_complete_and_in_daniels_order(world):
    index = _build(world)
    assert index["api"] == SH.API and index["set"] == "loved"
    assert [e["id"] for e in index["shaders"]] == [s[0] for s in SHADERS]
    assert [e["rank"] for e in index["shaders"]] == [1, 2, 3, 4]
    for e in index["shaders"]:
        missing = [k for k in REQUIRED if k not in e]
        assert not missing, (e["id"], missing)
        assert e["title"] and e["author"] == "a.stranger" and e["url"].endswith("/view/" + e["id"])
        assert e["licence"]["name"], e["id"]
        assert e["study"]["path"] and e["study"]["url"] == f"/study/{e['id']}.md"
        assert e["study"]["headings"] and e["study"]["techniques"] == ["4.1 Soft circle -- `image.glsl:3`",
                                                                       "4.2 Gradient ramp -- `image.glsl:4`"]
        assert e["atlas_links"] >= 1, e["id"]


def test_tags_land_on_atlas_categories_through_the_atlas_table(world):
    e = _entry(_build(world), "abcDE1")
    cats = {c["id"]: c for c in e["categories"]}
    assert set(cats) == {"B3", "H1", "B1"}            # noise.value lands on its group's category (noise -> B1)
    assert cats["B3"]["name"] == "Fractal sums" and cats["B3"]["tags"] == ["noise.fbm"]
    assert e["unmapped_tags"] == ["made.up_tag"]      # named, never silently dropped
    assert [g["name"] for g in e["groups"]] == ["fog-test"]
    assert [p["id"] for p in e["parts"]] == ["B3.01"]
    assert e["atlas_links"] == 3 + 1 + 1


def test_a_rendered_entry_lists_its_stills_and_filmstrip_with_server_urls(world):
    r = _entry(_build(world), "abcDE1")["renders"]
    assert r["status"] == "rendered" and r["fps"] == 60
    assert [s["t"] for s in r["stills"]] == [1.0, 4.0]
    assert [s["url"] for s in r["stills"]] == ["/renders/abcDE1/t1.00.png", "/renders/abcDE1/t4.00.png"]
    assert all(Path(s["path"]).name.endswith(".png") for s in r["stills"])
    assert r["filmstrip"]["url"] == "/renders/abcDE1/filmstrip.png" and r["filmstrip"]["fps"] == 60


STAND_INS = [{"src": "/media/a/abc123.jpg", "kind": "texture", "reason": "load failed: procedural stand-in",
              "style": "photo"},
             {"src": "https://example.org/a-track", "kind": "audio", "reason": "no audio fed: silence"}]


def _add_substituted(path: Path, subs) -> None:
    rec = json.loads(path.read_text(encoding="utf-8"))
    rec["substituted"] = subs
    path.write_text(json.dumps(rec), encoding="utf-8")


def test_each_receipts_stand_ins_are_kept_so_a_card_can_badge_them(world):
    """The S6 review: 20 of the 41 rendered Loved shaders were drawn with procedural stand-in textures or silent audio,
    and the index dropped the receipts' `substituted` lists, so a stand-in render read as the real thing."""
    d = world["renders"] / "abcDE1"
    _add_substituted(d / "receipt.json", STAND_INS)
    _add_substituted(d / "filmstrip.json", STAND_INS[1:])
    index = _build(world)
    r = _entry(index, "abcDE1")["renders"]
    assert r["substituted"] == {"stills": STAND_INS, "filmstrip": STAND_INS[1:]}
    assert r["status"] == "rendered"                   # the status words are unchanged; the badge reads the list
    assert index["summary"]["stand_ins"] == ["abcDE1"]
    assert _entry(index, "abcDE3")["renders"]["substituted"] == {"stills": [], "filmstrip": []}   # none recorded


def test_stand_ins_keep_only_the_receipt_fields_a_badge_needs(world):
    d = world["renders"] / "abcDE1"
    odd = [{"src": "/media/a/x.png", "kind": "cubemap", "reason": "face 1 load failed: procedural stand-in",
            "style": "environment", "bytes": 123456, "debug": {"deep": True}}, "not a record", None]
    _add_substituted(d / "receipt.json", odd)
    r = _entry(_build(world), "abcDE1")["renders"]
    assert r["substituted"]["stills"] == [{"src": "/media/a/x.png", "kind": "cubemap",
                                           "reason": "face 1 load failed: procedural stand-in", "style": "environment"}]


def test_a_study_only_entry_carries_no_stand_ins_either(world):
    _add_substituted(world["renders"] / "abcDE2" / "receipt.json", STAND_INS)
    e = _entry(_build(world), "abcDE2")
    assert e["renders"]["substituted"] == {"stills": [], "filmstrip": []}
    assert ".png" not in json.dumps(e) and ".jpg" not in json.dumps(e)


def test_show_names_the_stand_ins(world, monkeypatch, capsys):
    _add_substituted(world["renders"] / "abcDE1" / "receipt.json", STAND_INS)
    SH.write(_build(world), world["out"], state_root=world["state"])
    monkeypatch.setattr(SH, "OUT", world["out"])
    cli._load_extensions()
    assert cli.main(["shelf", "show", "abcDE1"]) == 0
    shown = capsys.readouterr().out
    assert "stand-in" in shown and "procedural stand-in" in shown and "silence" in shown


def test_a_30_fps_render_is_listed_as_stale_not_as_current(world):
    r = _entry(_build(world), "abcDE3")["renders"]
    assert r["status"].startswith("stale") and r["fps"] == 30


def test_a_header_that_forbids_reuse_makes_the_shader_study_only_even_when_the_meta_missed_it(world):
    assert C.load_meta("abcDE2", world["corpus"])["license"]["license"] == C.DEFAULT_LICENSE  # the meta's miss
    e = _entry(_build(world), "abcDE2")
    assert e["study_only"] is True
    assert e["licence"]["name"] == "all-rights-reserved" and e["licence"]["corrected"] is True
    assert e["licence"]["meta"] == C.DEFAULT_LICENSE
    assert e["licence"]["restrictive"] and e["licence"]["restrictive"][0]["file"] == "image.glsl"
    assert "image.glsl:2" in e["study_only_reason"]     # names where it says so


@pytest.mark.parametrize("sid", ["abcDE2", "abcDE4"])
def test_a_study_only_entry_has_its_note_and_no_image_paths(world, sid):
    e = _entry(_build(world), sid)
    assert e["study_only"] is True and e["study_only_reason"]
    assert e["study"]["path"] and e["study"]["url"] == f"/study/{sid}.md"   # the note is how it is shown
    r = e["renders"]
    assert r["stills"] == [] and r["filmstrip"] is None and r["status"].startswith("withheld")
    text = json.dumps(e)
    assert ".png" not in text and "/renders/" not in text   # the PNGs on disk are never named


def test_an_atlas_ruling_alone_makes_a_shader_study_only(world):
    e = _entry(_build(world), "abcDE4")
    assert e["licence"]["restrictive"] == [] and e["licence"]["corrected"] is False
    assert "atlas" in e["study_only_reason"]


def test_a_code_comment_that_says_do_not_use_is_not_a_licence(world):
    e = _entry(_build(world), "abcDE3")
    assert e["study_only"] is False and e["licence"]["restrictive"] == []
    assert e["licence"]["name"] == "CC-BY-NC-SA"


def test_the_summary_names_study_only_stale_and_unrendered(world):
    (world["renders"] / "abcDE1" / "receipt.json").unlink()
    (world["renders"] / "abcDE1" / "filmstrip.json").unlink()
    (world["renders"] / "abcDE1" / "filmstrip.png").unlink()
    s = _build(world)["summary"]
    assert s["study_only"] == ["abcDE2", "abcDE4"]
    assert s["stale"] == ["abcDE3"] and s["not_rendered"] == ["abcDE1"]
    assert s["no_atlas_link"] == []


def test_a_loved_id_missing_from_the_corpus_and_a_missing_note_are_reported_not_fatal(world):
    sets = json.loads((world["corpus"] / "sets.json").read_text(encoding="utf-8"))
    sets["loved"].append("zzzZZ9")
    (world["corpus"] / "sets.json").write_text(json.dumps(sets), encoding="utf-8")
    (world["study"] / "abcDE3.md").unlink()
    index = SH.build(corpus=world["corpus"], atlas=ATLAS, study_dir=world["study"], renders_dir=world["renders"],
                     dissect=lambda sid, *a, **k: _fake_dissect(sid) if sid in FAKE_TAGS else {"tags": []})
    gone = _entry(index, "zzzZZ9")
    assert gone["missing_from_corpus"] is True and all(k in gone for k in REQUIRED)
    assert index["summary"]["missing_from_corpus"] == ["zzzZZ9"]
    assert _entry(index, "abcDE3")["study"]["missing"] is True


def test_a_meta_reading_the_shelf_cannot_confirm_stays_study_only_and_says_it_may_be_false(world):
    """corpus.detect_license reads "do not use" anywhere in a comment as all rights reserved, so a code comment can turn
    a shader's meta into all-rights-reserved. The Shelf keeps the stricter reading (no pictures costs little) but says
    it found no withholding phrase of its own, so a person can look."""
    code = "// keep the sign here: do not use abs() on this value\n" + BODY
    C.save_shader(_shader("abcDE5", "Meta Misread", code), world["corpus"])
    assert C.load_meta("abcDE5", world["corpus"])["license"]["license"] == "all-rights-reserved"
    sets = json.loads((world["corpus"] / "sets.json").read_text(encoding="utf-8"))
    sets["loved"].append("abcDE5")
    (world["corpus"] / "sets.json").write_text(json.dumps(sets), encoding="utf-8")
    FAKE_TAGS["abcDE5"] = ["noise.fbm"]
    try:
        e = _entry(_build(world), "abcDE5")
    finally:
        del FAKE_TAGS["abcDE5"]
    assert e["study_only"] is True and e["licence"]["restrictive"] == []
    assert "may be a false reading" in e["study_only_reason"]
    assert "do not use abs()" in e["study_only_reason"]       # names the line the meta read
    assert ".png" not in json.dumps(e)


# ------------------------------------------------------------------------------- the restrictive-header detector
@pytest.mark.parametrize("text,restrictive", [
    ("// (c) someone, 2040. All rights reserved.", True),
    ("// I am the only owner of this; you cannot use it in any product.", True),
    ("// you may not\n// redistribute this piece in any form", True),       # a phrase broken across two lines
    ("/* Please do not copy this shader. */", True),
    ("// Shared for educational purposes only.", True),
    ("// Used without my written permission is a no.", True),
    ("// MIT License. Permission is hereby granted, free of charge, to deal without restriction", False),
    # Old copyright boilerplate followed by a grant in the same comment is a licence, not a refusal.
    ("// Notice: Copyright (C) 2040 Some Lab. All rights reserved.\n//    Distributed under the MIT License.", False),
    ("// (C) 2040 Some Lab. All rights reserved.\nfloat k = 1.0;\n// Distributed under the MIT License.", True),
    ("// CC BY-NC-SA: you may not use the material for commercial purposes", False),  # NC, already a licence
    ("// this helper is slow - DO NOT USE", False),
    ("// don't change these numbers", False),
    ("float notAComment = 1.0; // all good here", False),
])
def test_restrictive_header_detector(text, restrictive):
    hits = SH.restrictive_lines({"image.glsl": text + "\n" + BODY})
    assert bool(hits) is restrictive, hits
    if hits:
        assert hits[0]["file"] == "image.glsl" and hits[0]["line"] >= 1 and hits[0]["kind"]


def test_restrictive_text_in_code_is_not_read_as_a_header():
    """Only comments are read, as corpus.detect_license does: a string of words in code is not a statement."""
    assert SH.restrictive_lines({"image.glsl": "#define ALL_RIGHTS_RESERVED 1\n" + BODY}) == []


# -------------------------------------------------------------------------------------------- dissect --atlas
def test_dissect_atlas_map_joins_tags_categories_groups_and_parts():
    m = D.atlas_map({"id": "abcDE3", "tags": ["raymarch.sphere_trace", "sdf.sphere", "nope.nothing"]}, ATLAS)
    assert m["tags"] == {"raymarch.sphere_trace": ["E3"], "sdf.sphere": ["D1"], "nope.nothing": []}
    assert [c["id"] for c in m["categories"]] == ["D1", "E3"]          # in the atlas's own category order
    assert m["unmapped"] == ["nope.nothing"]
    assert [g["name"] for g in m["groups"]] == ["fog-test"] and [p["id"] for p in m["parts"]] == ["D4.01"]


def test_dissect_atlas_map_uses_the_real_atlas_table_by_default():
    m = D.atlas_map({"id": "not-a-corpus-id", "tags": ["noise.fbm"]})
    assert [c["id"] for c in m["categories"]] == ["B3"] and m["groups"] == [] and m["parts"] == []


def test_the_dissect_verb_takes_atlas():
    cli._load_extensions()
    ns = cli.build_parser().parse_args(["dissect", "x.frag", "--atlas"])
    assert ns.atlas is True


# ------------------------------------------------------------------------------------- writing stays in state/
def _files(root: Path) -> set:
    return {p for p in root.rglob("*") if p.is_file()}


def test_nothing_is_written_outside_state(world):
    before = _files(world["tmp"])
    index = _build(world)
    path = SH.write(index, world["out"], state_root=world["state"])
    new = _files(world["tmp"]) - before
    assert new == {world["out"]} and path == world["out"]
    assert json.loads(world["out"].read_text(encoding="utf-8"))["count"] == 4
    assert all(p.resolve().is_relative_to(world["state"].resolve()) for p in new)


def test_write_refuses_a_path_outside_state(world):
    with pytest.raises(ValueError, match="state"):
        SH.write(_build(world), world["tmp"] / "elsewhere" / "index.json", state_root=world["state"])
    assert not (world["tmp"] / "elsewhere").exists()


def test_the_default_index_lives_under_state():
    assert SH.OUT == ROOT / "state" / "arsenal" / "shaders" / "shelf" / "index.json"
    assert SH.OUT.resolve().is_relative_to((ROOT / "state").resolve())


# --------------------------------------------------------------------------------------------------- the verb
def test_the_shelf_verb_parses_build_list_and_show():
    cli._load_extensions()
    parser = cli.build_parser()
    assert parser.parse_args(["shelf", "build"]).action == "build"
    assert parser.parse_args(["shelf", "list", "--json"]).json is True
    ns = parser.parse_args(["shelf", "show", "abcDE2"])
    assert ns.action == "show" and ns.target == "abcDE2"


def test_list_and_show_read_the_written_index(world, monkeypatch, capsys):
    SH.write(_build(world), world["out"], state_root=world["state"])
    monkeypatch.setattr(SH, "OUT", world["out"])
    cli._load_extensions()
    assert cli.main(["shelf", "list"]) == 0
    out = capsys.readouterr().out
    for sid, _, _ in SHADERS:
        assert sid in out
    assert "STUDY ONLY" in out and "abcDE1.md" in out     # each row names its study note
    assert cli.main(["shelf", "show", "abcDE2"]) == 0
    shown = capsys.readouterr().out
    assert "study only" in shown.lower() and "image.glsl:2" in shown
    assert cli.main(["shelf", "show", "nothing-like-it"]) == 2


# ------------------------------------------------------------------------------------------------ the real corpus
REAL_SETS = C.CORPUS / "sets.json"


@pytest.mark.skipif(not REAL_SETS.exists(), reason="the private corpus is absent on this machine")
def test_the_real_shelf_lists_all_42_loved_shaders_each_linked_to_the_atlas():
    loved = C.load_sets()["loved"]
    index = SH.build()                      # reads only; writes nothing
    ids = [e["id"] for e in index["shaders"]]
    assert ids == loved and len(ids) == 42
    for e in index["shaders"]:
        assert e["atlas_links"] >= 1, e["id"]
        assert e["licence"]["name"], e["id"]
        assert e["study"]["path"], e["id"]
    warping = _entry(index, "4s23zz")
    assert warping["study_only"] is True and warping["licence"]["corrected"] is True
    assert ".png" not in json.dumps(warping)
    assert index["summary"]["study_only"] == ["4s23zz"]
