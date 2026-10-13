"""Pins for the house GLSL module core (arsenal/shaders/modules.py): the one mechanism that lets every visual surface
share a module, so "tweak one module and have everything update" (Daniel, 2026-10-13) is true by construction.

A module is a GLSL file whose leading `//!` lines are a JSON header (the format design/vfx-chunks has used since
2026-08-02, one line or several). Dependencies are explicit (`needs`) or INFERRED FROM SYMBOLS: a module that calls a
function another module defines needs that module. The legacy chunks prove why: they name their dependencies in prose,
sometimes by chunk ("Needs rot2") and sometimes by function ("Needs h31"), and nothing ever resolved them.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from arsenal.shaders import modules as M

REPO = Path(__file__).resolve().parents[1]
CHUNKS = REPO / "design" / "vfx-chunks"


def mod(name, body, kind="helper", cat="math", **extra):
    header = {"name": name, "kind": kind, "cat": cat, "order": extra.pop("order", 10)}
    header.update(extra)
    return "//! " + json.dumps(header) + "\n" + body


def lib_from(tmp_path, files):
    d = tmp_path / "lib"
    d.mkdir(exist_ok=True)
    for fname, text in files.items():
        (d / fname).write_text(text, encoding="utf-8")
    return M.load_library([d])


# ---------- parsing ----------

def test_a_one_line_header_parses_and_the_body_excludes_it():
    m = M.parse_module(mod("rot", "void pR(inout vec2 p,float a){ p=cos(a)*p+sin(a)*vec2(p.y,-p.x); }"), "rot.glsl")
    assert m.name == "rot" and m.header["kind"] == "helper"
    assert m.body.startswith("void pR(") and "//!" not in m.body


def test_a_header_may_span_several_leading_lines():
    text = ('//! {"name": "multi", "kind": "helper",\n'
            '//!  "cat": "noise", "order": 10,\n'
            '//!  "credits": ["someone, an article"]}\n'
            'float f(float x){ return x; }\n')
    m = M.parse_module(text, "multi.glsl")
    assert m.header["credits"] == ["someone, an article"] and m.body.strip() == "float f(float x){ return x; }"


@pytest.mark.parametrize("text", ["float f(){return 1.;}\n", "//! {not json}\nfloat f(){return 1.;}\n",
                                  '//! {"kind": "helper"}\nfloat f(){return 1.;}\n'])
def test_a_missing_or_broken_header_is_refused_naming_the_file(text):
    with pytest.raises(M.ModuleError) as err:
        M.parse_module(text, "broken.glsl")
    assert "broken.glsl" in str(err.value)


def test_provides_and_calls_are_read_from_code_not_comments():
    body = ("// float decoy(vec3 p){ return 0.; } and decoy2(\n"
            "/* vec3 alsoDecoy(vec2 q){} */\n"
            "float vn(vec3 p){ vec3 i=floor(p); return mix(h31(i), h31(i+1.), fract(p.x)); }\n"
            "float fbm3(vec3 p){ float s=0.; for(int k=0;k<4;k++){ s+=vn(p); p*=2.; } return s; }\n")
    m = M.parse_module(mod("vn", body, cat="noise"), "vn.glsl")
    assert m.provides == ("fbm3", "vn")
    assert "h31" in m.calls and "decoy" not in m.calls and "decoy2" not in m.calls
    assert "floor" not in m.calls and "mix" not in m.calls   # builtins are not dependencies


# ---------- resolution ----------

def test_dependencies_are_inferred_from_symbols_and_come_first(tmp_path):
    lib = lib_from(tmp_path, {
        "hash.glsl": mod("hash", "float h31(vec3 p){ return fract(sin(dot(p,vec3(1,2,3)))*4.); }", cat="noise"),
        "noise.glsl": mod("noise", "float vn(vec3 p){ return h31(floor(p)); }", cat="noise"),
        "fbm.glsl": mod("fbm", "float fbm(vec3 p){ return vn(p)+.5*vn(2.*p); }", cat="noise", order=20),
    })
    assert lib.resolve(["fbm"]) == ["hash", "noise", "fbm"]
    assert lib.deps("fbm") == ["noise"]


def test_resolution_does_not_depend_on_request_order(tmp_path):
    lib = lib_from(tmp_path, {
        "a.glsl": mod("a", "float fa(float x){ return x; }", order=30),
        "b.glsl": mod("b", "float fb(float x){ return x; }", order=10),
        "c.glsl": mod("c", "float fc(float x){ return fa(x)+fb(x); }", order=50),
    })
    assert lib.resolve(["c", "a", "b"]) == lib.resolve(["b", "c"]) == ["b", "a", "c"]
    assert lib.compose(["c"]) == lib.compose(["a", "b", "c"])


def test_explicit_needs_are_honoured_even_without_a_call(tmp_path):
    lib = lib_from(tmp_path, {
        "consts.glsl": mod("consts", "const float TAU = 6.28318530718;"),
        "ring.glsl": mod("ring", "float ring(vec2 p){ return abs(length(p)-1.)*TAU; }", needs=["consts"]),
    })
    assert lib.resolve(["ring"]) == ["consts", "ring"]


def test_a_cycle_is_refused_naming_its_members(tmp_path):
    lib = lib_from(tmp_path, {
        "x.glsl": mod("x", "float fx(float v){ return fy(v); }"),
        "y.glsl": mod("y", "float fy(float v){ return fx(v); }"),
    })
    with pytest.raises(M.ModuleError) as err:
        lib.resolve(["x"])
    assert "cycle" in str(err.value) and "x" in str(err.value) and "y" in str(err.value)


def test_a_missing_dependency_is_refused_naming_who_needs_it(tmp_path):
    lib = lib_from(tmp_path, {"r.glsl": mod("r", "float fr(float v){ return v; }", needs=["nowhere"])})
    with pytest.raises(M.ModuleError) as err:
        lib.resolve(["r"])
    assert "nowhere" in str(err.value) and "r" in str(err.value)


def test_two_modules_with_one_name_are_refused_naming_both_files(tmp_path):
    a, b = tmp_path / "one", tmp_path / "two"
    a.mkdir(); b.mkdir()
    (a / "dup.glsl").write_text(mod("dup", "float f1(float v){ return v; }"), encoding="utf-8")
    (b / "dup.glsl").write_text(mod("dup", "float f2(float v){ return v; }"), encoding="utf-8")
    with pytest.raises(M.ModuleError) as err:
        M.load_library([a, b])
    assert "one" in str(err.value) and "two" in str(err.value)


def test_two_modules_defining_one_function_are_refused(tmp_path):
    with pytest.raises(M.ModuleError) as err:
        lib_from(tmp_path, {"p.glsl": mod("p", "float same(float v){ return v; }"),
                            "q.glsl": mod("q", "float same(float v){ return -v; }")})
    assert "same" in str(err.value)


# ---------- composition ----------

def test_compose_is_deterministic_bytes_with_a_marker_per_module(tmp_path):
    lib = lib_from(tmp_path, {
        "hash.glsl": mod("hash", "float h(float x){ return fract(sin(x)*4.); }\n\n\n", cat="noise"),
        "user.glsl": mod("user", "float u(float x){ return h(x); }", cat="noise", order=20),
    })
    out = lib.compose(["user"])
    assert out == lib.compose(["user"])
    assert out.splitlines()[0].startswith("// " + M.API + " compose: hash, user")
    assert "// --- hash (noise) ---" in out and "// --- user (noise) ---" in out
    assert out.index("float h(") < out.index("float u(")
    assert "\r" not in out and out.endswith("\n") and "\n\n\n\n" not in out


def test_a_snippet_cannot_be_composed_but_its_helpers_form_a_prelude(tmp_path):
    lib = lib_from(tmp_path, {
        "rot.glsl": mod("rot", "void pR(inout vec2 p,float a){ p=cos(a)*p+sin(a)*vec2(p.y,-p.x); }"),
        "spin.glsl": mod("spin", "pR(uv, u_time);", kind="domain", cat="domain", order=50,
                         **{"in": {"uv": "vec2"}, "out": {"uv": "vec2"}}),
    })
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["spin"])
    assert "snippet" in str(err.value)
    assert lib.prelude(["spin"]) == lib.compose(["rot"])


# ---------- manifests: one registry for the whole house ----------

def test_a_module_becomes_an_arsenal_module_v0_manifest_the_registry_accepts(tmp_path):
    from arsenal.registry import validate_manifest
    lib = lib_from(tmp_path, {
        "tone.glsl": mod("tone", "vec3 tone(vec3 c, float k){ return tanh(c*k); }", kind="helper", cat="tone",
                         params=[{"name": "exposure", "unit": "ratio", "range": [0.1, 4.0], "default": 1.0}],
                         license="Apache-2.0", credits=["the tunnel shader Daniil pasted 2026-08-02"],
                         **{"in": {"col": "vec3"}, "out": {"col": "vec3"}}),
    })
    m = M.manifest_for(lib.get("tone"), lib)
    assert m["id"] == "glsl.tone" and m["protocol"] == "arsenal.module/v0" and m["engine"] == "browser"
    assert m["inputs"] == [{"port": "col", "type": "vfx.vec3"}] and m["outputs"] == [{"port": "col", "type": "vfx.vec3"}]
    assert m["params"][0]["name"] == "exposure" and m["params"][0]["default"] == 1.0
    assert m["shader"]["provides"] == ["tone"] and m["shader"]["api"] == M.API
    assert m["licence"] == "Apache-2.0"
    assert validate_manifest(m, "tone") == []


def test_the_registry_refuses_a_shader_block_from_another_api():
    from arsenal.registry import validate_manifest
    m = {"id": "glsl.x", "version": "0.1.0", "protocol": "arsenal.module/v0", "engine": "browser",
         "shader": {"api": "something/else", "provides": []}}
    assert any("shader" in p for p in validate_manifest(m, "x"))


# ---------- the real legacy chunks resolve for the first time ----------

def test_every_legacy_chunk_parses_and_its_prose_dependencies_now_resolve():
    lib = M.load_library([CHUNKS])
    assert len(lib.names()) >= 30
    assert lib.deps("value-noise-3d") == ["hash31"]                     # "Needs h31." (a FUNCTION name)
    assert set(lib.deps("orbit-swarm")) >= {"segment-distance", "rot2"}  # "Needs segment-distance and rot2."
    assert "value-noise-3d" in lib.deps("noise-mask")                    # "Needs value-noise-3d."
    assert "rot2" in lib.deps("torus-ring")
    for name in lib.names():
        lib.resolve([name])   # no missing dependency and no cycle anywhere


def test_the_filmic_finish_group_resolves_in_one_call():
    lib = M.load_library([CHUNKS])
    group = json.loads((REPO / "design" / "vfx-groups.json").read_text(encoding="utf-8"))["filmic finish"]
    assert set(lib.resolve(group)) >= set(group)


# ---------- lint: the shader-craft floors a module can be checked against blind ----------

@pytest.mark.parametrize("body,needle", [
    ("#version 300 es\nfloat f(float x){ return x; }", "#version"),
    ("precision mediump float;\nfloat f(float x){ return x; }", "precision"),
    ("uniform float u_secret;\nfloat f(float x){ return x*u_secret; }", "uniform"),
])
def test_lint_names_the_floor_a_library_module_breaks(body, needle):
    m = M.parse_module(mod("bad", body, license="Apache-2.0", credits=[]), "bad.glsl")
    assert any(needle in p for p in M.lint(m, library_module=True))


def test_lint_wants_a_licence_and_credits_on_library_modules_only():
    m = M.parse_module(mod("plain", "float f(float x){ return x; }"), "plain.glsl")
    assert any("license" in p for p in M.lint(m, library_module=True))
    assert any("credits" in p for p in M.lint(m, library_module=True))
    assert M.lint(m, library_module=False) == []


def test_a_param_uniform_declared_in_the_header_is_allowed():
    m = M.parse_module(mod("ok", "uniform float u_gain;\nfloat f(float x){ return x*u_gain; }",
                           license="Apache-2.0", credits=[],
                           params=[{"name": "gain", "unit": "ratio", "range": [0, 2], "uniform": "u_gain"}]), "ok.glsl")
    assert M.lint(m, library_module=True) == []


# ---------- the browser twin composes the same bytes ----------

@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_javascript_twin_composes_byte_identical_source():
    lib = M.load_library([CHUNKS])
    names = ["orbit-swarm", "noise-mask", "torus-ring"]
    py_prelude = lib.prelude(names)
    script = REPO / "tests" / "glsl_modlib_parity.mjs"
    out = subprocess.run(["node", str(script), str(CHUNKS), *names], capture_output=True, text=True,
                         encoding="utf-8", timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout == py_prelude
