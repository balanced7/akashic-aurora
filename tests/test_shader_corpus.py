"""Pins for the shader school's corpus door (arsenal/shaders/corpus.py, arsenal/shaders/cli.py).

Every shader here is synthetic: the real corpus is other people's code under their licence and lives only under
state/ (gitignored), so a test never reads it, never prints it and never depends on it being present.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from arsenal.shaders import corpus as C
from arsenal.shaders import cli


def _shader(sid, name="Test", passes=None, code=None):
    passes = passes or [{"name": "Image", "type": "image", "code": code or "void mainImage(out vec4 o, in vec2 u){o=vec4(1);}",
                         "inputs": [], "outputs": [{"id": "4dfGRr", "channel": 0}]}]
    return {"ver": "0.1", "info": {"id": sid, "name": name, "username": "someone", "date": "1700000000",
                                   "likes": 3, "viewed": 10, "tags": ["t"], "description": "d"},
            "renderpass": passes}


def _bundle(tmp_path, **keys):
    b = {"schema": C.HARVEST_API}
    b.update(keys)
    p = tmp_path / "bundle.json"
    p.write_text(json.dumps(b), encoding="utf-8")
    return p


@pytest.fixture()
def corpus(tmp_path, monkeypatch):
    root = tmp_path / "corpus"
    monkeypatch.setattr(C, "CORPUS", root)  # every function resolves CORPUS at call time
    return root


def test_pass_stem_names_files_after_shadertoy_passes():
    assert C.pass_stem("Image") == "image"
    assert C.pass_stem("Buffer A") == "buffer_a"
    assert C.pass_stem("Cube A") == "cube_a"
    assert C.pass_stem("") == "pass"


@pytest.mark.parametrize("comment,want", [
    ("// The MIT License\n// Copyright (c) someone", "MIT"),
    ("/* License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License. */", "CC-BY-NC-SA"),
    ("// CC0: do what you like", "CC0"),
    ("// released into the public domain", "CC0"),
    ("// Creative Commons Attribution 4.0", "CC-BY"),
])
def test_licence_is_read_from_the_shaders_own_comments(comment, want):
    got = C.detect_license([comment + "\nvoid mainImage(out vec4 o, in vec2 u){}"])
    assert got["license"] == want and got["explicit"] is True


def test_no_licence_statement_means_the_shadertoy_default():
    got = C.detect_license(["void mainImage(out vec4 o, in vec2 u){ o = vec4(0); } // MITigation is not a licence"])
    assert got == {"license": C.DEFAULT_LICENSE, "explicit": False, "line": ""}


def test_licence_words_in_code_do_not_count_only_comments():
    got = C.detect_license(['float MIT = 1.0; void mainImage(out vec4 o, in vec2 u){ o = vec4(MIT); }'])
    assert got["explicit"] is False


def test_ingest_writes_shader_meta_and_one_glsl_per_pass(tmp_path, corpus):
    passes = [
        {"name": "Common", "type": "common", "code": "float k(){return 1.;}", "inputs": [], "outputs": []},
        {"name": "Buffer A", "type": "buffer", "code": "void mainImage(out vec4 o,in vec2 u){o=vec4(k());}",
         "inputs": [{"channel": 0, "type": "buffer", "id": "4dXGR8", "filepath": "/media/previz/buffer00.png",
                     "sampler": {"filter": "linear", "wrap": "clamp", "vflip": "true", "srgb": "false", "internal": "byte"}}],
         "outputs": [{"id": "4dXGR8", "channel": 0}]},
        {"name": "Image", "type": "image", "code": "void mainImage(out vec4 o,in vec2 u){o=texture(iChannel0,u);}",
         "inputs": [{"channel": 0, "type": "texture", "id": "XsXGRn", "filepath": "/media/a/abc123.png", "sampler": {}}],
         "outputs": [{"id": "4dfGRr", "channel": 0}]},
    ]
    report = C.ingest_bundle(_bundle(tmp_path, love_top=[dict(_shader("AbCd12", "Multi", passes), __rank=1)]))
    d = corpus / "shaders" / "AbCd12"
    assert report["shaders_written"] == 1
    assert sorted(p.name for p in d.iterdir()) == ["buffer_a.glsl", "common.glsl", "image.glsl", "meta.json", "shader.json"]
    assert "__rank" not in json.loads((d / "shader.json").read_text(encoding="utf-8"))
    meta = C.load_meta("AbCd12")
    assert meta["multipass"] is True and meta["pass_types"] == ["buffer", "common", "image"]
    assert meta["media"] == ["/media/a/abc123.png"]          # buffers are not media; textures are
    assert (corpus / "harvests" / (report["sha256"] + ".json")).exists()


def test_sets_merge_in_order_and_never_duplicate(tmp_path, corpus):
    C.ingest_bundle(_bundle(tmp_path, love_top=[dict(_shader("Bbbbb2"), __rank=2), dict(_shader("Aaaaa1"), __rank=1)],
                            loved_ids=["Zzzzz9", "Aaaaa1"]))
    C.ingest_bundle(_bundle(tmp_path, shaders=[_shader("Zzzzz9")], loved_ids=["Zzzzz9", "Aaaaa1", "Yyyyy8"]))
    sets = C.load_sets()
    assert sets["love_top"] == ["Aaaaa1", "Bbbbb2"]       # by rank, not by arrival
    assert sets["loved"] == ["Zzzzz9", "Aaaaa1", "Yyyyy8"]  # playlist order kept, the newcomer appended
    assert C.missing_ids() == {"loved": ["Yyyyy8"]}


def test_media_in_a_bundle_lands_by_basename_and_clears_missing(tmp_path, corpus):
    passes = [{"name": "Image", "type": "image", "code": "void mainImage(out vec4 o,in vec2 u){}", "outputs": [],
               "inputs": [{"channel": 0, "type": "texture", "filepath": "/media/a/feed01.png", "sampler": {}}]}]
    C.ingest_bundle(_bundle(tmp_path, shaders=[_shader("Ccccc3", passes=passes)]))
    assert C.missing_media() == ["/media/a/feed01.png"]
    C.ingest_bundle(_bundle(tmp_path, media={"/media/a/feed01.png": base64.b64encode(b"PNGBYTES").decode()}))
    assert (corpus / "media" / "feed01.png").read_bytes() == b"PNGBYTES"
    assert C.missing_media() == []


def test_a_bundle_with_the_wrong_schema_is_refused_before_anything_is_written(tmp_path, corpus):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"schema": "something-else", "shaders": [_shader("Ddddd4")]}), encoding="utf-8")
    with pytest.raises(ValueError):
        C.ingest_bundle(p)
    assert not corpus.exists()


@pytest.mark.parametrize("bad", ["../../x", "short", "toolong7", "a/b/c1", ""])
def test_a_shader_id_that_is_not_a_shadertoy_id_is_refused(corpus, bad):
    with pytest.raises(ValueError):
        C.save_shader(_shader(bad))


def test_resolve_finds_by_exact_id_or_name_substring(tmp_path, corpus):
    C.ingest_bundle(_bundle(tmp_path, shaders=[_shader("Eeeee5", "Protean Things"), _shader("Fffff6", "Other")]))
    assert C.resolve("Eeeee5") == ["Eeeee5"]
    assert C.resolve("protean") == ["Eeeee5"]
    assert C.resolve("nothing-like-it") == []


def test_cli_list_show_and_missing_answer_in_json(tmp_path, corpus, capsys):
    C.ingest_bundle(_bundle(tmp_path, shaders=[_shader("Ggggg7", "Glow")], loved_ids=["Ggggg7"]))
    assert cli.main(["list", "--set", "loved", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in rows] == ["Ggggg7"]
    assert cli.main(["show", "Glow", "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown[0]["sets"] == {"loved": 1} and shown[0]["license"]["explicit"] is False
    assert cli.main(["show", "no-such-shader"]) == 2
    capsys.readouterr()
    assert cli.main(["missing", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"ids": {}, "media": []}


def test_cli_ingest_from_clipboard_refuses_text_that_is_not_a_bundle(corpus, monkeypatch, capsys):
    monkeypatch.setattr(cli, "read_clipboard_text", lambda: "my shopping list")
    assert cli.main(["ingest", "--clipboard"]) == 2
    assert "does not hold a harvest bundle" in capsys.readouterr().err
    assert not corpus.exists()


def test_cli_ingest_from_clipboard_saves_a_bundle(corpus, monkeypatch, capsys):
    text = json.dumps({"schema": C.HARVEST_API, "shaders": [_shader("Hhhhh8")]})
    monkeypatch.setattr(cli, "read_clipboard_text", lambda: text)
    assert cli.main(["ingest", "--clipboard"]) == 0
    assert C.all_ids() == ["Hhhhh8"]


def test_the_corpus_lives_under_state_which_git_ignores():
    rel = C.CORPUS.relative_to(Path(C.ROOT))
    assert rel.parts[0] == "state"


def test_arsenal_main_routes_the_shader_verb(tmp_path, corpus, capsys):
    from arsenal.__main__ import main as arsenal_main
    assert arsenal_main(["shader", "missing", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"ids": {}, "media": []}


# ---------- the morning's one human step: the media snippet ----------

def _with_inputs(sid, inputs):
    passes = [{"name": "Image", "type": "image", "code": "void mainImage(out vec4 o,in vec2 u){}", "outputs": [],
               "inputs": inputs}]
    return _shader(sid, passes=passes)


def test_media_to_fetch_expands_cubemaps_and_skips_placeholders_and_what_we_hold(tmp_path, corpus):
    tex = "/media/a/" + "ab" * 32 + ".png"
    cube = "/media/a/" + "cd" * 32 + ".jpg"
    held = "/media/a/" + "ef" * 32 + ".png"
    inputs = [{"channel": 0, "type": "texture", "filepath": tex, "sampler": {}},
              {"channel": 1, "type": "cubemap", "filepath": cube, "sampler": {}},
              {"channel": 2, "type": "texture", "filepath": "/media/previz/buffer00.png", "sampler": {}},
              {"channel": 3, "type": "texture", "filepath": held, "sampler": {}}]
    C.ingest_bundle(_bundle(tmp_path, shaders=[_with_inputs("Mmmmm1", inputs)],
                            media={held: base64.b64encode(b"x").decode()}))
    stem = cube.rsplit(".", 1)[0]
    assert C.media_to_fetch() == sorted([tex, cube] + [f"{stem}_{k}.jpg" for k in range(1, 6)])


def test_harvest_js_media_prints_one_paste_that_fetches_and_saves_one_bundle(tmp_path, corpus, capsys):
    tex = "/media/a/" + "12" * 32 + ".png"
    C.ingest_bundle(_bundle(tmp_path, shaders=[_with_inputs("Nnnnn2", [{"channel": 0, "type": "texture",
                                                                         "filepath": tex, "sampler": {}}])]))
    assert cli.main(["harvest-js", "--media"]) == 0
    out = capsys.readouterr().out
    assert "window.__st" in out and json.dumps([tex]) in out
    assert "__st.download(" in out and cli.MEDIA_BUNDLE in out and "py -m arsenal shader ingest" in out


def test_harvest_js_media_says_so_when_nothing_is_missing(corpus, capsys):
    assert cli.main(["harvest-js", "--media"]) == 0
    assert "already holds every medium" in capsys.readouterr().err
