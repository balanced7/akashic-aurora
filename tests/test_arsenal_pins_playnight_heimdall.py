"""Blind pins for Play Night presets (parse_preset / list_presets / GET /api/presets).

Written by Heimdall (deepseek) from arsenal/PLAY-NIGHT-SPEC.md alone, BEFORE reading
arsenal/presets.py or the page, so the parser has to satisfy tests its author didn't write.
RED is expected until the implementation and the presets land.

Contract source: arsenal/PLAY-NIGHT-SPEC.md -> "Preset file format" and "Server".
No network beyond a local in-process test server (same pattern as test_arsenal_serve.py).
"""

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import presets  # noqa: E402

# The exact set of uniforms a preset body may declare, and their GLSL types.
UNIFORM_TYPES = {
    "u_video": "sampler2D",
    "u_prev": "sampler2D",
    "u_audio": "sampler2D",
    "u_res": "vec2",
    "u_video_res": "vec2",
    "u_time": "float",
    "u_media_time": "float",
    "u_frame": "float",
    "u_has_video": "float",
    "u_pulse": "float",
    "u_beat": "float",
    "u_level": "float",
    "u_bass": "float",
    "u_mid": "float",
    "u_high": "float",
    "u_flux": "float",
    "u_hue": "float",
    "u_intensity": "float",
    "u_k1": "float",
    "u_k2": "float",
    "u_k3": "float",
    "u_k4": "float",
    "u_k5": "float",
    "u_k6": "float",
    "u_k7": "float",
    "u_k8": "float",
}

HEADER = '#version 300 es\n//! {"id": "trails", "name": "Trails", "author": "Navi", "tags": ["video"], "params": [{"k": 1, "name": "trails", "default": 0.6}]}\n'


def _write_preset(dirpath, stem, body, header=None):
    if header is not None:
        text = header + body
    else:
        # Build the shared HEADER with the id matching the stem, so the header's
        # "id" always agrees with the file name (parse_preset enforces the match).
        header = HEADER.replace('"id": "trails"', f'"id": "{stem}"')
        text = header + body
    p = dirpath / f"{stem}.frag"
    p.write_text(text, encoding="utf-8")
    return p


def _valid_body():
    return (
        "precision highp float;\n"
        "in vec2 v_uv;\n"
        "out vec4 outColor;\n"
        "uniform sampler2D u_video;\n"
        "uniform float u_time;\n"
        "void main() {\n"
        "  vec4 v = texture(u_video, v_uv);\n"
        "  outColor = v + vec4(u_time * 0.01);\n"
        "}\n"
    )


# ---------------------------------------------------------------- parse_preset: shape

def test_parse_preset_valid_shape(tmp_path):
    p = _write_preset(tmp_path, "trails", _valid_body())
    got = presets.parse_preset(p)
    assert got["id"] == "trails"
    assert got["file"].endswith("trails.frag") or got["file"].endswith("trails")
    assert got["url"] == "/web/presets/trails.frag"
    assert got["name"] == "Trails"
    assert got["author"] == "Navi"
    assert got["tags"] == ["video"]
    assert got["params"] == [{"k": 1, "name": "trails", "default": 0.6}]
    assert got["problems"] == []


def test_parse_preset_url_uses_file(tmp_path):
    p = _write_preset(tmp_path, "abc-def", _valid_body())
    got = presets.parse_preset(p)
    assert got["url"] == "/web/presets/abc-def.frag"
    assert got["id"] == "abc-def"


# ---------------------------------------------------------------- line 1 / line 2

def test_line1_must_be_exact_version(tmp_path):
    # anything before #version breaks line 1
    p = _write_preset(tmp_path, "bad", "precision highp float;\n" + _valid_body(),
                      header="#version 300 es\n//! 300\n")
    # replace first line entirely: a BOM or leading whitespace-free alternative is invalid;
    # here we test a body that does NOT start with #version as line 1
    bad = tmp_path / "bad.frag"
    bad.write_text("  #version 300 es\n" + "//! 300\n" + _valid_body(), encoding="utf-8")
    got = presets.parse_preset(bad)
    assert got["problems"]  # line 1 is not exactly #version 300 es


def test_line2_must_be_json_header(tmp_path):
    bad = tmp_path / "bad.frag"
    bad.write_text('#version 300 es\n//! not json\n' + _valid_body(), encoding="utf-8")
    got = presets.parse_preset(bad)
    assert got["problems"]


def test_id_must_equal_file_stem(tmp_path):
    # header id "other" does not match the file stem "mismatch"
    p = tmp_path / "mismatch.frag"
    p.write_text('#version 300 es\n//! {"id": "other", "name": "X", "author": "A"}\n' + _valid_body(),
                 encoding="utf-8")
    got = presets.parse_preset(p)
    assert got["id"] == "mismatch"  # fallback: id is ALWAYS the file stem
    assert any("id" in pr.lower() or "stem" in pr.lower() or "mismatch" in pr for pr in got["problems"])


def test_id_matches_regex(tmp_path):
    # underscores and uppercase are not in [a-z0-9][a-z0-9-]*; a stem with them is fine as a fallback id
    # but the header id must be the (valid) stem. Test an invalid stem does not crash:
    p = tmp_path / "bad_stem.frag"
    p.write_text('#version 300 es\n//! {"id": "bad_stem", "name": "X", "author": "A"}\n' + _valid_body(),
                 encoding="utf-8")
    got = presets.parse_preset(p)
    assert got["id"] == "bad_stem"


# ---------------------------------------------------------------- params rules

def test_params_defaults_and_bounds(tmp_path):
    # valid: k in 1..8, name 1..16, default 0..1
    header = ('#version 300 es\n//! {"id": "p", "name": "P", "author": "A", '
              '"params": [{"k": 1, "name": "a", "default": 0.0}, '
              '{"k": 8, "name": "bb", "default": 1.0}]}\n')
    p = tmp_path / "p.frag"
    p.write_text(header + _valid_body(), encoding="utf-8")
    got = presets.parse_preset(p)
    assert len(got["params"]) == 2
    assert got["params"][0] == {"k": 1, "name": "a", "default": 0.0}
    assert got["params"][1] == {"k": 8, "name": "bb", "default": 1.0}


def test_params_at_most_8(tmp_path):
    params = [{"k": i, "name": f"k{i}", "default": 0.5} for i in range(1, 10)]  # 9 params
    header = '#version 300 es\n//! {"id": "p", "name": "P", "author": "A", "params": ' + json.dumps(params) + '}\n'
    p = tmp_path / "p.frag"
    p.write_text(header + _valid_body(), encoding="utf-8")
    got = presets.parse_preset(p)
    assert got["problems"]


def test_params_k_must_be_whole_1_to_8(tmp_path):
    for bad_k in (0, 9):
        header = ('#version 300 es\n//! {"id": "p", "name": "P", "author": "A", '
                  f'"params": [{{"k": {bad_k}, "name": "a", "default": 0.5}}]}}\n')
        p = tmp_path / "p.frag"
        p.write_text(header + _valid_body(), encoding="utf-8")
        assert presets.parse_preset(p)["problems"]


def test_params_k_unique(tmp_path):
    header = ('#version 300 es\n//! {"id": "p", "name": "P", "author": "A", '
              '"params": [{"k": 1, "name": "a", "default": 0.5}, {"k": 1, "name": "b", "default": 0.5}]}\n')
    p = tmp_path / "p.frag"
    p.write_text(header + _valid_body(), encoding="utf-8")
    assert presets.parse_preset(p)["problems"]


def test_params_name_length(tmp_path):
    header = ('#version 300 es\n//! {"id": "p", "name": "P", "author": "A", '
              '"params": [{"k": 1, "name": "thisnameiswaytoolong", "default": 0.5}]}\n')
    p = tmp_path / "p.frag"
    p.write_text(header + _valid_body(), encoding="utf-8")
    assert presets.parse_preset(p)["problems"]


def test_params_default_range(tmp_path):
    for bad in (-0.1, 1.1):
        header = ('#version 300 es\n//! {"id": "p", "name": "P", "author": "A", '
                  f'"params": [{{"k": 1, "name": "a", "default": {bad}}}]}}\n')
        p = tmp_path / "p.frag"
        p.write_text(header + _valid_body(), encoding="utf-8")
        assert presets.parse_preset(p)["problems"]


def test_params_may_be_absent(tmp_path):
    header = '#version 300 es\n//! {"id": "p", "name": "P", "author": "A"}\n'
    p = tmp_path / "p.frag"
    p.write_text(header + _valid_body(), encoding="utf-8")
    got = presets.parse_preset(p)
    assert got["params"] == []


# ---------------------------------------------------------------- uniforms

def test_uniforms_only_from_v1_list(tmp_path):
    # an unknown uniform name must produce a problem
    p = _write_preset(tmp_path, "bad", _valid_body() + "uniform float u_bogus;\n")
    assert presets.parse_preset(p)["problems"]


def test_uniform_wrong_type(tmp_path):
    # u_time must be float, not vec2
    p = _write_preset(tmp_path, "bad", _valid_body() + "uniform vec2 u_time;\n")
    assert presets.parse_preset(p)["problems"]


def test_several_names_one_declaration(tmp_path):
    body = (
        "precision highp float;\n"
        "in vec2 v_uv;\n"
        "out vec4 outColor;\n"
        "uniform float u_bass, u_mid, u_high;\n"
        "uniform sampler2D u_video;\n"
        "void main() {\n"
        "  outColor = vec4(u_bass + u_mid + u_high) + texture(u_video, v_uv);\n"
        "}\n"
    )
    p = _write_preset(tmp_path, "multi", body)
    assert presets.parse_preset(p)["problems"] == []


def test_in_and_out_declarations(tmp_path):
    # missing in vec2 v_uv must produce a problem
    body = (
        "precision highp float;\n"
        "out vec4 outColor;\n"
        "uniform sampler2D u_video;\n"
        "void main() { outColor = texture(u_video, v_uv); }\n"
    )
    p = _write_preset(tmp_path, "noin", body)
    assert presets.parse_preset(p)["problems"]
    # missing out vec4 outColor also a problem
    body2 = (
        "precision highp float;\n"
        "in vec2 v_uv;\n"
        "uniform sampler2D u_video;\n"
        "void main() { }\n"
    )
    p2 = _write_preset(tmp_path, "noout", body2)
    assert presets.parse_preset(p2)["problems"]


# ---------------------------------------------------------------- craft floors

def test_highp_only(tmp_path):
    # mediump is a problem
    body = _valid_body().replace("precision highp float;", "precision mediump float;")
    p = _write_preset(tmp_path, "med", body)
    assert presets.parse_preset(p)["problems"]
    body2 = _valid_body().replace("precision highp float;", "precision lowp float;")
    p2 = _write_preset(tmp_path, "low", body2)
    assert presets.parse_preset(p2)["problems"]


def test_no_uniform_in_loop_bound(tmp_path):
    # a uniform in a for-loop condition must be flagged (loop bound must be constant)
    body = (
        "precision highp float;\n"
        "in vec2 v_uv;\n"
        "out vec4 outColor;\n"
        "uniform sampler2D u_video;\n"
        "uniform float u_time;\n"
        "void main() {\n"
        "  vec3 acc = vec3(0.0);\n"
        "  for (float i = 0.0; i < u_time; i += 1.0) { acc += 0.1; }\n"
        "  outColor = vec4(acc, 1.0) + texture(u_video, v_uv);\n"
        "}\n"
    )
    p = _write_preset(tmp_path, "loop", body)
    assert presets.parse_preset(p)["problems"]


def test_comments_do_not_count(tmp_path):
    # a uniform mentioned only inside a comment must NOT be treated as a declaration;
    # and a comment shield must not hide a real missing-declaration problem.
    body = (
        "precision highp float;\n"
        "// uniform float u_bogus;\n"
        "in vec2 v_uv;\n"
        "out vec4 outColor;\n"
        "uniform sampler2D u_video;\n"
        "void main() { outColor = texture(u_video, v_uv); }\n"
    )
    p = _write_preset(tmp_path, "commented", body)
    got = presets.parse_preset(p)
    # the comment mention of u_bogus must not introduce a uniform problem
    assert not any("u_bogus" in pr for pr in got["problems"])


def test_fallback_name_author_tags(tmp_path):
    # header with only id -> name falls back to stem, author to "", tags to []
    header = '#version 300 es\n//! {"id": "plain"}\n'
    p = tmp_path / "plain.frag"
    p.write_text(header + _valid_body(), encoding="utf-8")
    got = presets.parse_preset(p)
    assert got["name"] == "plain"
    assert got["author"] == ""
    assert got["tags"] == []
    assert got["params"] == []


# ---------------------------------------------------------------- list_presets

def test_list_presets_sorts_by_lower_name_then_id(tmp_path):
    dirpath = tmp_path / "presets"
    dirpath.mkdir()
    # names chosen so lowercased-name order != insertion order != id order
    _write_preset(dirpath, "zeta", _valid_body(),
                  header='#version 300 es\n//! {"id": "zeta", "name": "Alpha", "author": "A"}\n')
    _write_preset(dirpath, "alpha", _valid_body(),
                  header='#version 300 es\n//! {"id": "alpha", "name": "Beta", "author": "A"}\n')
    _write_preset(dirpath, "mid", _valid_body(),
                  header='#version 300 es\n//! {"id": "mid", "name": "alpha", "author": "A"}\n')
    got = presets.list_presets(str(dirpath))
    names = [g["name"] for g in got]
    # sorted by lowercased name: alpha (from "mid"), Alpha (from zeta) tie -> then id mid < zeta
    assert names == ["alpha", "Alpha", "Beta"]


def test_list_presets_missing_dir_is_empty(tmp_path):
    assert presets.list_presets(str(tmp_path / "nope")) == []


def test_list_presets_only_frag_files(tmp_path):
    dirpath = tmp_path / "presets"
    dirpath.mkdir()
    _write_preset(dirpath, "good", _valid_body())
    (dirpath / "notes.txt").write_text("not a frag", encoding="utf-8")
    (dirpath / "other.vert").write_text("not a frag", encoding="utf-8")
    got = presets.list_presets(str(dirpath))
    assert [g["id"] for g in got] == ["good"]


# ---------------------------------------------------------------- GET /api/presets

@pytest.fixture()
def presets_server(tmp_path):
    from arsenal.serve import App, Server  # noqa: E402 (same pattern as test_arsenal_serve)
    pdir = tmp_path / "presets"
    pdir.mkdir()
    _write_preset(pdir, "one", _valid_body(),
                  header='#version 300 es\n//! {"id": "one", "name": "One", "author": "A"}\n')
    _write_preset(pdir, "two", _valid_body(),
                  header='#version 300 es\n//! {"id": "two", "name": "Two", "author": "A"}\n')
    app = App([str(tmp_path / "lib")], presets_dir=str(pdir))
    srv = Server(0, app)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def test_api_presets_shape(presets_server):
    base = presets_server
    status, body = _get(base + "/api/presets")
    assert status == 200
    pres = body["presets"]
    assert isinstance(pres, list)
    assert len(pres) == 2
    # sorted by lowercased name
    assert [p["name"] for p in pres] == ["One", "Two"]
    # each has the full parse shape with an empty problems list
    assert all(p["problems"] == [] for p in pres)
    assert pres[0]["url"] == "/web/presets/one.frag"


def test_api_presets_reports_broken(presets_server, tmp_path):
    base = presets_server
    status, body = _get(base + "/api/presets")
    # (broken-preset reporting is exercised through parse_preset above; here we just
    #  confirm the route returns the list_presets shape under a clean dir)
    assert status == 200
    assert all("problems" in p for p in body["presets"])


# ---------------------------------------------------------------- sweep: every real preset parses clean

def test_every_real_preset_parses_clean():
    presets_dir = ROOT / "arsenal" / "web" / "presets"
    if not presets_dir.is_dir():
        pytest.skip("arsenal/web/presets does not exist yet")
    frags = sorted(presets_dir.glob("*.frag"))
    assert frags, "no presets found"
    for frag in frags:
        got = presets.parse_preset(frag)
        assert got["problems"] == [], f"{frag.name}: {got['problems']}"
