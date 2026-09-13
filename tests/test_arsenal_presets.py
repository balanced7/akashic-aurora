"""Vandor's tests for the Play Night preset bank: header parsing, format rules, and the route."""
import json
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal.presets import list_presets, parse_preset  # noqa: E402
from arsenal.serve import App, Server  # noqa: E402

VALID = """#version 300 es
//! {"id": "demo-one", "name": "Demo One", "author": "Vandor", "tags": ["test"], "params": [{"k": 1, "name": "trails", "default": 0.5}, {"k": 3, "name": "zoom", "default": 0}]}
precision highp float;
uniform sampler2D u_video, u_prev;
uniform vec2 u_res;
uniform float u_time, u_bass, u_k1, u_k3;  // a trailing comment
in vec2 v_uv;
out vec4 outColor;
/* a block comment mentioning mediump must not count */
void main() {
  vec3 col = max(texture(u_prev, v_uv).rgb * 0.96 * u_k1 - 1.0 / 255.0, 0.0);
  for (int i = 0; i < 4; i++) { col += 0.01 * float(i) * u_bass; }
  outColor = vec4(col, 1.0);
}
"""


def _write(directory: Path, stem: str, text: str) -> Path:
    path = directory / f"{stem}.frag"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_valid_preset_has_no_problems(tmp_path):
    info = parse_preset(_write(tmp_path, "demo-one", VALID))
    assert info["problems"] == []
    assert info["name"] == "Demo One" and info["author"] == "Vandor" and info["tags"] == ["test"]
    assert info["params"] == [{"k": 1, "name": "trails", "default": 0.5}, {"k": 3, "name": "zoom", "default": 0}]
    assert info["url"] == "/web/presets/demo-one.frag"


def _problems(tmp_path, text, stem="demo-one"):
    return parse_preset(_write(tmp_path, stem, text))["problems"]


def test_each_format_rule_names_its_problem(tmp_path):
    cases = [
        (VALID.replace("#version 300 es", "#version 100", 1), "line 1"),
        ("\n" + VALID, "line 1"),
        (VALID.replace("//! {", "//! {oops", 1), "not JSON"),
        (VALID.replace('"id": "demo-one"', '"id": "other"', 1), "must equal the file name"),
        (VALID.replace('"author": "Vandor"', '"author": ""', 1), "non-empty author"),
        (VALID.replace("uniform vec2 u_res;", "uniform float u_res;", 1), "must be vec2"),
        (VALID.replace("in vec2 v_uv;", "in vec2 v_uv;\nuniform float u_nope;", 1), "not in the Play Night uniform list"),
        (VALID.replace("precision highp float;", "precision highp float;\nprecision mediump int;", 1), "highp only"),
        (VALID.replace("i < 4", "i < int(u_k1 * 8.0)", 1), "loop bound uses a uniform"),
        (VALID.replace("out vec4 outColor;", "out vec4 fragColor;", 1), "outColor"),
        (VALID.replace('{"k": 3, "name": "zoom"', '{"k": 1, "name": "zoom"', 1), "declared twice"),
        (VALID.replace('"default": 0}', '"default": 2}', 1), "default must be"),
        (VALID.replace('{"k": 3,', '{"k": 9,', 1), "whole number from 1 to 8"),
    ]
    for text, needle in cases:
        problems = _problems(tmp_path, text)
        assert any(needle in p for p in problems), (needle, problems)


def test_a_bad_file_name_is_a_problem(tmp_path):
    text = VALID.replace('"id": "demo-one"', '"id": "Demo_One"', 1)
    assert any("file name" in p for p in _problems(tmp_path, text, stem="Demo_One"))


def test_list_presets_sorts_by_name_and_tolerates_a_missing_dir(tmp_path):
    _write(tmp_path, "zeta", VALID.replace('"id": "demo-one", "name": "Demo One"', '"id": "zeta", "name": "Alpha"', 1))
    _write(tmp_path, "demo-one", VALID)
    assert [p["id"] for p in list_presets(tmp_path)] == ["zeta", "demo-one"]
    assert list_presets(tmp_path / "missing") == []


def test_presets_route_lists_broken_presets_with_their_problems(tmp_path):
    presets = tmp_path / "presets"
    presets.mkdir()
    _write(presets, "demo-one", VALID)
    _write(presets, "broken", "void main() {}\n")
    srv = Server(0, App([str(tmp_path)], takes_root=tmp_path / "takes", presets_dir=presets))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/api/presets", timeout=10) as r:
            listed = {p["id"]: p for p in json.loads(r.read())["presets"]}
    finally:
        srv.shutdown()
        srv.server_close()
    assert listed["demo-one"]["problems"] == []
    assert listed["broken"]["problems"]
