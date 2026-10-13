"""Pins for the house GLSL module core (arsenal/shaders/modules.py): the one mechanism that lets every visual surface
share a module, so "tweak one module and have everything update" (Daniel, 2026-10-13) is true by construction.

A module is a GLSL file whose leading `//!` lines are a JSON header (the format design/vfx-chunks has used since
2026-08-02, one line or several). Dependencies are explicit (`needs`) or INFERRED FROM SYMBOLS: a module that calls a
function another module defines needs that module. The legacy chunks prove why: they name their dependencies in prose,
sometimes by chunk ("Needs rot2") and sometimes by function ("Needs h31"), and nothing ever resolved them.
"""
from __future__ import annotations

import hashlib
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
    m = M.parse_module(mod("rot", "void turnUv(inout vec2 uv, float amount){ uv = uv.yx * vec2(amount, 1.0 - amount) + uv * 0.25; }"), "rot.glsl")
    assert m.name == "rot" and m.header["kind"] == "helper"
    assert m.body.startswith("void turnUv(") and "//!" not in m.body


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
            "float vn(vec3 p){ vec3 cell = floor(p * 0.5); return mix(h31(cell.zxy), h31(cell - 3.0), p.y * 0.125); }\n"
            "float fbm3(vec3 p){ float acc = 0.75; for (int oct = 3; oct > 0; oct--) { acc -= vn(p.yzx) * 0.3; } return acc; }\n")
    m = M.parse_module(mod("vn", body, cat="noise"), "vn.glsl")
    assert m.provides == ("fbm3", "vn")
    assert "h31" in m.calls and "decoy" not in m.calls and "decoy2" not in m.calls
    assert "floor" not in m.calls and "mix" not in m.calls   # builtins are not dependencies


# ---------- resolution ----------

def test_dependencies_are_inferred_from_symbols_and_come_first(tmp_path):
    lib = lib_from(tmp_path, {
        "hash.glsl": mod("hash", "float h31(vec3 p){ return fract(p.x * 0.37 + p.z * 0.11 - p.y); }", cat="noise"),
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
        "hash.glsl": mod("hash", "float h(float x){ return fract(x * 0.618 + 0.25); }\n\n\n", cat="noise"),
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
        "rot.glsl": mod("rot", "void turnUv(inout vec2 uv, float amount){ uv = uv.yx * vec2(amount, 1.0 - amount) + uv * 0.25; }"),
        "spin.glsl": mod("spin", "turnUv(uv, u_time);", kind="domain", cat="domain", order=50,
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


# ---------- S1 (shader school 2026-10-13): structs and constants are providers ----------
# WHY: a volume module that returns `VolAccum` or scales by `TAU` needs the module that declares them even though it
# never CALLS anything there; before S1 only calls were read, so such a module composed without its struct and the
# page failed to compile far from the cause.

def test_a_struct_and_top_level_consts_are_provided_but_a_local_const_is_not():
    body = ("struct VolAccum { vec3 col; float a; };\n"
            "const float TAU = 6.28318530718;\n"
            "const vec3 A = vec3(1.0, 0.5, 0.25), B = vec3(0.0);\n"
            "const float W[2] = float[2](0.5, 0.5);\n"
            "float f(const float x){ const float LOCAL = 2.0; return x*LOCAL; }\n")
    m = M.parse_module(mod("vol", body), "vol.glsl")
    assert m.structs == ("VolAccum",)
    assert m.consts == ("A", "B", "TAU", "W")
    assert m.provides == ("A", "B", "TAU", "VolAccum", "W", "f")
    assert "LOCAL" not in m.provides and "VolAccum" not in m.calls


def test_a_module_that_uses_a_struct_or_const_depends_on_its_provider(tmp_path):
    lib = lib_from(tmp_path, {
        "types.glsl": mod("types", "struct VolAccum { vec3 col; float a; };", order=10),
        "consts.glsl": mod("consts", "const float TAU = 6.28318530718;", order=11),
        "user.glsl": mod("user", "void accum(inout VolAccum acc, float x){ acc.a += x / TAU; }", order=20),
    })
    assert lib.deps("user") == ["types", "consts"]
    assert lib.resolve(["user"]) == ["types", "consts", "user"]


def test_a_struct_or_const_named_only_in_a_comment_is_not_a_dependency(tmp_path):
    lib = lib_from(tmp_path, {
        "consts.glsl": mod("consts", "const float TAU = 6.28318530718;"),
        "types.glsl": mod("types", "struct VolAccum { float a; };"),
        "user.glsl": mod("user", "// TAU here is prose\nfloat g(float x){ /* VolAccum TAU */ return x; }", order=20),
    })
    assert lib.deps("user") == []


def test_a_snippet_keeps_its_consts_block_local(tmp_path):
    lib = lib_from(tmp_path, {
        "s1.glsl": mod("s1", "const float K = 2.0;\ncol *= K;", kind="modifier", cat="modifier"),
        "s2.glsl": mod("s2", "const float K = 3.0;\ncol *= K;", kind="modifier", cat="modifier"),
    })
    assert lib.get("s1").provides == () and lib.get("s2").provides == ()


def test_two_modules_providing_one_struct_are_refused_by_a_strict_load(tmp_path):
    with pytest.raises(M.ModuleError) as err:
        lib_from(tmp_path, {"a.glsl": mod("a", "struct Hit { float t; };"),
                            "b.glsl": mod("b", "struct Hit { float d; };")})
    assert "struct 'Hit'" in str(err.value)


# ---------- S1: hooks become prototypes ----------
# WHY: a raymarcher calls the host's `mapScene`, which the host defines AFTER the prelude. GLSL ES 3.00 allows a
# prototype first, so the composer emits it once; an undeclared call is a lint error so a typo cannot pass as a hook.

HOOK_LIB = {
    "base.glsl": mod("base", "float sat(float x){ return x * 0.5 + 0.25; }", order=10),
    "march.glsl": mod("march", "float march(vec3 ro, vec3 rd){ float depth = 0.125;\n"
                               "  for (int n = 0; n < 9; n++) { depth += mapScene(rd * depth - ro); }\n"
                               "  return sat(depth); }",
                      order=20, hooks=["float mapScene(vec3 p)"]),
    "shade.glsl": mod("shade", "vec3 shade(vec3 ro, vec3 rd){ return skyColour(rd) * march(ro, rd); }",
                      order=30, hooks=["float  mapScene( vec3 p );", "vec3 skyColour(vec3 rd)"]),
}


def test_hooks_become_prototypes_once_before_the_first_module_that_declares_them(tmp_path):
    out = lib_from(tmp_path, HOOK_LIB).compose(["shade"])
    assert out.count("float mapScene(vec3 p);") == 1 and out.count("vec3 skyColour(vec3 rd);") == 1
    assert "// hooks\nfloat mapScene(vec3 p);\n\n// --- march (math) ---" in out
    assert "// hooks\nvec3 skyColour(vec3 rd);\n\n// --- shade (math) ---" in out
    assert out.index("// --- base (math) ---") < out.index("float mapScene(vec3 p);")


def test_no_hooks_block_for_a_composition_that_declares_none(tmp_path):
    assert "// hooks" not in lib_from(tmp_path, HOOK_LIB).compose(["base"])


@pytest.mark.parametrize("hooks", [["not a prototype"], "float f(vec3 p)", [42],
                                   ["float f(vec3 p) { return 1.0; }"]])
def test_a_malformed_hook_is_refused_naming_the_file(hooks):
    with pytest.raises(M.ModuleError) as err:
        M.parse_module(mod("h", "float g(float x){ return x; }", hooks=hooks), "hooky.glsl")
    assert "hooky.glsl" in str(err.value) and "hook" in str(err.value)


def test_an_unresolved_call_is_one_no_module_provides_and_no_hook_in_reach_declares(tmp_path):
    files = dict(HOOK_LIB)
    files["typo.glsl"] = mod("typo", "float typo(vec3 p){ return mapScen(p) + sat(p.x); }", order=40,
                             hooks=["float mapScene(vec3 p)"], license="Apache-2.0", credits=[])
    files["user2.glsl"] = mod("user2", "float u2(vec3 p){ return mapScene(p) * march(p, p); }", order=50)
    files["user3.glsl"] = mod("user3", "float u3(vec3 p){ return mapScene(p); }", order=50)
    lib = lib_from(tmp_path, files)
    assert lib.unresolved("typo") == ["mapScen"]
    assert lib.unresolved("shade") == []          # skyColour and mapScene are declared; march is provided
    assert lib.unresolved("user2") == []          # its dependency `march` declares the hook
    assert lib.unresolved("user3") == ["mapScene"]
    problems = M.lint(lib.get("typo"), library_module=True, library=lib)
    assert [p for p in problems if "no hook declares" in p] == [
        "typo: calls mapScen(), which no module provides and no hook declares "
        "(declare it in \"hooks\" if the host defines it; a typo cannot pass as a hook)"]
    assert M.lint(lib.get("typo"), library_module=False, library=lib) == []


def test_lint_without_a_library_checks_calls_against_the_modules_own_hooks():
    lone = M.parse_module(mod("lone", "float lone(vec3 p){ return mapScene(p); }", license="Apache-2.0",
                              credits=[]), "lone.glsl")
    assert any("mapScene()" in p for p in M.lint(lone))
    hooked = M.parse_module(mod("hooked", "float lone(vec3 p){ return mapScene(p); }", license="Apache-2.0",
                                credits=[], hooks=["float mapScene(vec3 p)"]), "hooked.glsl")
    assert M.lint(hooked) == []


def test_lint_names_a_target_need_outside_the_vocabulary():
    m = M.parse_module(mod("bits", "float f(float x){ return x; }", license="Apache-2.0", credits=[],
                           targets={"glsl": "300es", "needs": ["unit"]}), "bits.glsl")
    assert any("'unit'" in p for p in M.lint(m))


@pytest.mark.parametrize("targets", [["uint"], {"needs": "uint"}, {"needs": ["uint", 7]}])
def test_lint_names_a_targets_field_of_the_wrong_shape(targets):
    m = M.parse_module(mod("bits", "float f(float x){ return x; }", license="Apache-2.0", credits=[],
                           targets=targets), "bits.glsl")
    assert any("targets" in p and "shape" in p for p in M.lint(m))


# ---------- S1: strict and lenient loading ----------
# WHY: one clashing file used to raise inside load_library and blank every surface that loads the library. CI and
# `lib lint` stay strict; pages and renders load leniently, quarantine the newcomer and say so in library.problems.

def _clash_dirs(tmp_path):
    a, b = tmp_path / "one", tmp_path / "two"
    a.mkdir(); b.mkdir()
    (a / "dup.glsl").write_text(mod("dup", "float f1(float v){ return v; }"), encoding="utf-8")
    (a / "keep.glsl").write_text(mod("keep", "float k(float v){ return f1(v); }", order=20), encoding="utf-8")
    (b / "dup.glsl").write_text(mod("dup", "float f2(float v){ return v; }"), encoding="utf-8")
    (b / "hit.glsl").write_text(mod("hit", "struct Hit { float t; };"), encoding="utf-8")
    (b / "hit2.glsl").write_text(mod("hit-again", "struct Hit { float d; };"), encoding="utf-8")
    (b / "broken.glsl").write_text("//! {not json}\nfloat nope(float v){ return v; }\n", encoding="utf-8")
    (b / "fine.glsl").write_text(mod("fine", "float fine(Hit h){ return h.t; }", order=20), encoding="utf-8")
    return a, b


def test_a_strict_load_still_raises_on_the_first_bad_file(tmp_path):
    a, b = _clash_dirs(tmp_path)
    with pytest.raises(M.ModuleError) as err:
        M.load_library([a, b])
    assert "broken.glsl" in str(err.value)


def test_a_lenient_load_quarantines_the_later_module_and_loads_the_rest(tmp_path):
    a, b = _clash_dirs(tmp_path)
    lib = M.load_library([a, b], strict=False)
    assert lib.names() == ["dup", "fine", "hit", "keep"]
    assert lib.get("dup").path == str(a / "dup.glsl")
    assert [(Path(p["path"]).parent.name, Path(p["path"]).name, p["name"]) for p in lib.problems] == [
        ("two", "broken.glsl", None), ("two", "dup.glsl", "dup"), ("two", "hit2.glsl", "hit-again")]
    assert "two modules are named 'dup'" in lib.problems[1]["problem"]
    assert "struct 'Hit'" in lib.problems[2]["problem"]
    assert lib.resolve(["fine"]) == ["hit", "fine"]
    assert lib.compose(["keep"]).splitlines()[0].endswith("compose: dup, keep")


# ---------- S1: targets ----------
# WHY: a module that needs `uint` compiles on WebGL2 and dies on WebGL1 or a three.js material without GLSL3; the
# composer refuses by name instead (the "loud plan" habit of arsenal/graph.py).

TARGET_LIB = {
    "pcg.glsl": mod("pcg", "uint pcgHash(uint v){ return v * 747796405u + 2891336453u; }", order=10,
                    targets={"glsl": "300es", "needs": ["uint"]}),
    "edge.glsl": mod("edge", "float edgeAA(float d){ return d / fwidth(d); }", order=11,
                     targets={"needs": ["derivatives"]}),
    "user.glsl": mod("user", "float userRand(float x){ return float(pcgHash(uint(x))) * edgeAA(x); }", order=20),
    "trail.glsl": mod("trail", "void mainImage(out vec4 o, in vec2 f){ o = vec4(userRand(f.x)); }",
                      kind="pass", cat="pass", order=60),
}


def test_a_target_refuses_a_module_whose_needs_it_lacks_naming_the_module_and_the_need(tmp_path):
    lib = lib_from(tmp_path, TARGET_LIB)
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["user"], target="webgl1")
    msg = str(err.value)
    assert "webgl1" in msg and "module 'pcg' needs uint" in msg and "module 'edge' needs derivatives" in msg
    for target in ("webgl2", "toy", "three-r186"):
        assert lib.compose(["user"], target=target) == lib.compose(["user"])


@pytest.mark.parametrize("need", ["uint", "texelFetch", "derivatives", "float-targets"])
def test_webgl1_lacks_each_need_and_webgl2_has_it(tmp_path, need):
    lib = lib_from(tmp_path, {"n.glsl": mod("n", "float n(float x){ return x; }", targets={"needs": [need]})})
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["n"], target="webgl1")
    assert f"module 'n' needs {need}" in str(err.value)
    assert lib.compose(["n"], target="webgl2") == lib.compose(["n"])


def test_three_r186_refuses_a_pass_by_name(tmp_path):
    lib = lib_from(tmp_path, TARGET_LIB)
    with pytest.raises(M.ModuleError) as err:
        lib.prelude(["trail"], target="three-r186")
    assert "module 'trail' is kind 'pass'" in str(err.value)
    assert lib.prelude(["trail"], target="toy") == lib.compose(["user"])


def test_an_unknown_target_is_refused_listing_the_known_ones(tmp_path):
    lib = lib_from(tmp_path, TARGET_LIB)
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["pcg"], target="webgl3")
    assert "webgl3" in str(err.value) and "three-r186, three-r186-glsl1, toy, webgl1, webgl2" in str(err.value)


# ---------- S1: the composed header names what ran ----------
# WHY: a receipt (a filmstrip, a render, a preset) can now say exactly which module versions and which bytes ran.

def test_the_composed_header_names_each_module_version_and_hashes_the_text_below(tmp_path):
    lib = lib_from(tmp_path, {
        "hash.glsl": mod("hash", "float h(float x){ return fract(x * 0.618 + 0.25); }", cat="noise", version="1.2.0"),
        "user.glsl": mod("user", "float u(float x){ return h(x); }", cat="noise", order=20),
    })
    out = lib.compose(["user"])
    head = out.split("\n", 3)
    assert head[0] == "// " + M.API + " compose: hash, user"
    assert head[1] == "// modules: hash@1.2.0 user@0.0.0"
    assert head[2] == "// sha256: " + hashlib.sha256(head[3].encode("utf-8")).hexdigest()
    assert head[3].startswith("\n// --- hash (noise) ---\n")


def test_a_body_change_changes_the_hash_and_nothing_else_in_the_header(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    a = lib_from(tmp_path / "a", {"k.glsl": mod("k", "float k(float x){ return x; }", version="1.0.0")})
    b = lib_from(tmp_path / "b", {"k.glsl": mod("k", "float k(float x){ return -x; }", version="1.0.0")})
    ha, hb = a.compose(["k"]).split("\n", 3), b.compose(["k"]).split("\n", 3)
    assert ha[:2] == hb[:2] and ha[2] != hb[2]


# ---------- S1 review fixes (the adversarial review of 2026-10-13, defects 1-10) ----------
# WHY each pin exists is the defect it names: every one was a way to hand a page text that does not compile, a receipt
# that does not verify, or two twins that disagree, without anyone being told.

# defect 1: the hooks block is written BEFORE the module body, so a prototype naming the module's own struct or const
# would come before its declaration ("undeclared type" at compile time).
@pytest.mark.parametrize("body,hooks,symbol", [
    ("struct VolAccum { vec3 col; float a; };\nVolAccum march(vec3 ro){ return shadeStep(ro, 0.0); }",
     ["VolAccum shadeStep(vec3 p, float t)"], "struct 'VolAccum'"),
    ("const int N = 4;\nfloat f(float w[N]){ return g(w); }", ["float g(float w[N])"], "const 'N'"),
    ("const int N = 4;\nfloat f(float w[N]){ return g(w); }", ["float g(float w [ N ])"], "const 'N'"),
])
def test_a_hook_naming_its_own_modules_struct_or_const_is_refused(body, hooks, symbol):
    with pytest.raises(M.ModuleError) as err:
        M.parse_module(mod("own", body, hooks=hooks), "own.glsl")
    msg = str(err.value)
    assert "own.glsl" in msg and symbol in msg and "its own module" in msg


def test_a_hook_naming_another_modules_struct_composes_after_that_struct(tmp_path):
    out = lib_from(tmp_path, {
        "types.glsl": mod("types", "struct VolAccum { vec3 col; float a; };", order=10),
        "march.glsl": mod("march", "VolAccum march(vec3 ro){ return shadeStep(ro, 0.0); }", order=5,
                          hooks=["VolAccum shadeStep(vec3 p, float t)"]),
    }).compose(["march"])
    assert out.index("struct VolAccum") < out.index("VolAccum shadeStep(vec3 p, float t);") < out.index("march(")


# defect 2: lenient loading must not hand a page a dangling call. A module that calls (or uses) a symbol only a
# quarantined file provides is refused at compose time, naming that file.
LOST_LIB = {
    "a-noise.glsl": mod("noise", "float vnQ(vec3 p){ return fract(p.x); }"),
    "b-noise.glsl": mod("noise", "float vnQ2(vec3 p){ return fract(p.y); }\n"
                                 "float fbmQ(vec3 p){ return vnQ2(p) + vnQ2(2.0 * p); }"),
    "c-broken.glsl": '//! {"name": "broken-lost",\nstruct LostAcc { float a; };\nfloat lostFn(float x){ return x; }\n',
    "d-user.glsl": mod("user-q", "float userQ(vec3 p){ return fbmQ(p); }", order=20),
    "e-user.glsl": mod("user-l", "float userL(LostAcc a){ return lostFn(a.a); }", order=20),
    "f-hooked.glsl": mod("user-h", "float userH(vec3 p){ return fbmQ(p); }", order=20, hooks=["float fbmQ(vec3 p)"]),
    "g-needs.glsl": mod("user-n", "float userN(float x){ return x; }", order=20, needs=["vnQ2"]),
    "h-snip.glsl": mod("snip-q", "col *= fbmQ(vec3(uv, 0.0));", kind="modifier", cat="modifier"),
}


def _lost_lib(tmp_path):
    d = tmp_path / "lost"
    d.mkdir()
    for fname, text in LOST_LIB.items():
        (d / fname).write_text(text, encoding="utf-8")
    return d, M.load_library([d], strict=False)


def test_compose_refuses_a_call_that_only_a_quarantined_file_provides(tmp_path):
    d, lib = _lost_lib(tmp_path)
    assert [Path(p["path"]).name for p in lib.problems] == ["b-noise.glsl", "c-broken.glsl"]
    assert lib.unresolved("user-q") == ["fbmQ"]
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["user-q"])
    msg = str(err.value)
    assert "module 'user-q' calls fbmQ()" in msg and str(d / "b-noise.glsl") in msg and "quarantined" in msg
    with pytest.raises(M.ModuleError) as err:
        lib.prelude(["snip-q"])
    assert "module 'snip-q' calls fbmQ()" in str(err.value)


def test_a_broken_files_functions_and_structs_are_still_known_to_be_lost(tmp_path):
    d, lib = _lost_lib(tmp_path)
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["user-l"])
    msg = str(err.value)
    assert "module 'user-l' calls lostFn()" in msg and "module 'user-l' uses LostAcc" in msg
    assert str(d / "c-broken.glsl") in msg


def test_a_hook_in_reach_still_covers_a_lost_name_and_a_need_names_the_quarantine(tmp_path):
    d, lib = _lost_lib(tmp_path)
    assert "float fbmQ(vec3 p);" in lib.compose(["user-h"])     # the host defines it: a hook, not a dangling call
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["user-n"])
    assert "needs 'vnQ2'" in str(err.value) and str(d / "b-noise.glsl") in str(err.value)


# defect 4: one unreadable file used to crash a lenient Python load (and build_index) instead of being quarantined.
def test_a_lenient_load_quarantines_a_file_that_is_not_utf8_and_skips_a_directory_named_like_one(tmp_path):
    d = tmp_path / "lib"
    d.mkdir()
    (d / "good.glsl").write_text(mod("good", "float g(float x){ return x; }"), encoding="utf-8")
    (d / "latin1.glsl").write_bytes(mod("latin", "// caf\xe9\nfloat l(float x){ return x; }").encode("latin-1"))
    (d / "weird.glsl").mkdir()
    lib = M.load_library([d], strict=False)
    assert lib.names() == ["good"]
    assert [(Path(p["path"]).name, p["name"]) for p in lib.problems] == [("latin1.glsl", None)]
    assert "UTF-8" in lib.problems[0]["problem"]
    with pytest.raises(M.ModuleError) as err:
        M.load_library([d])
    assert "latin1.glsl" in str(err.value) and "UTF-8" in str(err.value)
    assert [row["path"] for row in M.build_index(d)["files"]] == ["good.glsl", "latin1.glsl"]


def test_a_lenient_load_quarantines_any_parse_failure_not_only_a_module_error(monkeypatch):
    def boom(text, path="<text>"):
        if "explode" in text:
            raise RuntimeError("a bug in a parser")
        return real(text, path)
    real = M.parse_module
    monkeypatch.setattr(M, "parse_module", boom)
    lib = M.library_from_sources([("a.glsl", mod("a", "float fa(float x){ return x; }")),
                                  ("b.glsl", "// explode")], strict=False)
    assert lib.names() == ["a"] and [(p["path"], p["name"]) for p in lib.problems] == [("b.glsl", None)]
    with pytest.raises(RuntimeError):
        M.library_from_sources([("b.glsl", "// explode")], strict=True)


# defect 5: a UTF-8 BOM loaded in the page (fetch strips it) and failed in the CLI; and the twins trimmed different
# whitespace before `//!`. Both now drop one leading BOM and trim only spaces and tabs.
def test_a_leading_bom_is_dropped_and_only_spaces_and_tabs_may_precede_the_header():
    m = M.parse_module("\ufeff" + mod("bom", "float f(float x){ return x; }"), "bom.glsl")
    assert m.name == "bom" and "\ufeff" not in m.body
    assert M.parse_module(" \t" + mod("tabbed", "float f(float x){ return x; }"), "t.glsl").name == "tabbed"
    for lead in ("\u00a0", "\f", "\v", "\ufeff\ufeff"):
        with pytest.raises(M.ModuleError) as err:
            M.parse_module(lead + mod("x", "float f(float x){ return x; }"), "lead.glsl")
        assert "no //! header" in str(err.value)


# defect 6: header values decide the composed header and the sort order, so they are validated in both twins.
@pytest.mark.parametrize("header_json,needle", [
    ('{"name": "a", "kind": "helper", "version": "1.0.0\\n// sha256: forged"}', "version"),
    ('{"name": "a", "kind": "helper", "version": "1.0 beta"}', "version"),
    ('{"name": "a", "kind": "helper", "cat": "\\ud800"}', "cat"),
    ('{"name": "a", "kind": "helper", "cat": "x\\u2028y"}', "cat"),
    ('{"name": "a", "kind": "helper", "cat": 1.0}', "cat"),
    ('{"name": "a", "kind": "helper", "order": true}', "order"),
    ('{"name": "a", "kind": "helper", "order": "10"}', "order"),
    ('{"name": "a", "kind": "helper", "order": 1e400}', "order"),
    ('{"name": "a", "kind": [], "cat": "x"}', "kind"),
    ('{"name": "a", "kind": {}}', "kind"),
    ('{"name": "a", "kind": {"toString": 1}}', "kind"),
    ('{"name": "a", "kind": "help\\u0000er"}', "kind"),
    ('{"name": "two words", "kind": "helper"}', "name"),
    ('{"name": "a\\nb", "kind": "helper"}', "name"),
    ('{"name": "", "kind": "helper"}', "name"),
    ('{"name": "a", "kind": "helper", "needs": "noise"}', "needs"),
    ('{"name": "a", "kind": "helper", "needs": {"noise": 1}}', "needs"),
    ('{"name": "a", "kind": "helper", "needs": [7]}', "needs"),
])
def test_a_header_value_of_the_wrong_type_is_refused_naming_the_field(header_json, needle):
    with pytest.raises(M.ModuleError) as err:
        M.parse_module("//! " + header_json + "\nfloat fa(float x){ return x; }\n", "hdr.glsl")
    msg = str(err.value)
    assert "hdr.glsl" in msg and needle in msg


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_a_header_with_a_non_json_constant_is_not_json(constant):
    with pytest.raises(M.ModuleError) as err:
        M.parse_module('//! {"name": "a", "kind": "helper", "order": ' + constant + '}\nfloat fa(float x){ return x; }',
                       "nan.glsl")
    assert "nan.glsl" in str(err.value) and "is not JSON" in str(err.value)


def test_valid_header_values_still_load_and_null_means_absent():
    m = M.parse_module('//! {"name": "ok-1.x_y", "kind": "helper", "cat": null, "version": "1.2.0-beta.1+b5", '
                       '"order": 12.5, "needs": null}\nfloat fa(float x){ return x; }', "ok.glsl")
    assert (m.name, m.cat, m.version, m.order) == ("ok-1.x_y", "misc", "1.2.0-beta.1+b5", 12.5)


def test_messages_quote_names_the_same_way_in_both_twins(tmp_path):
    lib = lib_from(tmp_path, {"q.glsl": mod("q", "float fq(float x){ return x; }", needs=["it's"])})
    with pytest.raises(M.ModuleError) as err:
        lib.deps("q")
    assert "module 'q' needs 'it's'" in str(err.value)
    with pytest.raises(M.ModuleError) as err:
        lib.get("no'pe")
    assert str(err.value) == "no module named 'no'pe'"


# defect 7: webgl1 must refuse GLSL ES 3.00, and a three.js material without GLSL3 needs a target that can refuse.
# A module is GLSL ES 3.00 (module format, section 3) unless its header says targets.glsl "100".
def test_webgl1_and_a_three_material_without_glsl3_refuse_a_glsl_es_300_module(tmp_path):
    lib = lib_from(tmp_path, {
        "es1.glsl": mod("es1", "float es1(float x){ return x * 0.5; }", targets={"glsl": "100", "needs": []}),
        "es3.glsl": mod("es3", "float es3(float x){ return es1(x); }", order=20, targets={"glsl": "300es"}),
        "plain.glsl": mod("plain", "float plain(float x){ return x; }"),
        "trail.glsl": mod("trail", "void mainImage(out vec4 o, in vec2 f){ o = vec4(es1(f.x)); }",
                          kind="pass", cat="pass", targets={"glsl": "100"}),
    })
    for target in ("webgl1", "three-r186-glsl1"):
        assert lib.compose(["es1"], target=target) == lib.compose(["es1"])
        for name in ("es3", "plain"):
            with pytest.raises(M.ModuleError) as err:
                lib.compose([name], target=target)
            assert f"module '{name}' is GLSL ES 3.00" in str(err.value) and target in str(err.value)
        assert "module 'es1'" not in str(err.value)
    with pytest.raises(M.ModuleError) as err:
        lib.prelude(["trail"], target="three-r186-glsl1")
    assert "module 'trail' is kind 'pass'" in str(err.value)
    for target in ("webgl2", "toy", "three-r186"):
        assert lib.compose(["es3", "plain"], target=target) == lib.compose(["es3", "plain"])


@pytest.mark.parametrize("glsl", ["300", "es3", 300, None])
def test_lint_names_a_targets_glsl_outside_the_vocabulary(glsl):
    m = M.parse_module(mod("g", "float f(float x){ return x; }", license="Apache-2.0", credits=[],
                           targets={"glsl": glsl, "needs": []}), "g.glsl")
    assert any("targets.glsl" in p for p in M.lint(m))


@pytest.mark.parametrize("body,needle", [
    ("vec4 f(sampler2D s, vec2 uv){ return texture(s, uv); }", "texture()"),
    ("float f(float x){ return round(x); }", "round()"),
    ("uint f(uint x){ return x; }", "uint"),
    ("int f(int x){ return x << 1; }", "<<"),
    ("int f(int x){ return x & 3; }", "&"),
    ("int f(int x){ return x % 3; }", "%"),
    ("float f(float x){ float w[2] = float[2](x, x); return w[0]; }", "array constructor"),
    ("float f(float x){ return fwidth(x); }", "derivatives"),
])
def test_lint_names_glsl_es_300_features_in_a_module_that_claims_100(body, needle):
    m = M.parse_module(mod("es1", body, license="Apache-2.0", credits=[], targets={"glsl": "100", "needs": []}),
                       "es1.glsl")
    assert any(needle in p and "100" in p for p in M.lint(m)), M.lint(m)
    clean = M.parse_module(mod("es1", "float f(float x){ return x > 0.5 && x < 1.0 ? x : 0.0; }", license="Apache-2.0",
                               credits=[], targets={"glsl": "100", "needs": []}), "es1.glsl")
    assert M.lint(clean) == []


def test_lint_accepts_derivatives_in_a_100_module_that_declares_the_need():
    m = M.parse_module(mod("aa", "float f(float x){ return x / fwidth(x); }", license="Apache-2.0", credits=[],
                           targets={"glsl": "100", "needs": ["derivatives"]}), "aa.glsl")
    assert M.lint(m) == []


# defect 8: hooks are deduplicated by signature (return type, name, parameter types; `in`, `const`, precision and
# parameter names ignored), because ES 1.00 calls two prototypes of one function a duplicate. A disagreement about the
# same function is refused instead of being handed to the compiler.
def test_hooks_that_differ_only_in_parameter_names_or_in_are_emitted_once(tmp_path):
    out = lib_from(tmp_path, {
        "m1.glsl": mod("m1", "float u1(vec3 q){ return mapScene(q); }", hooks=["float mapScene(vec3 p)"]),
        "m2.glsl": mod("m2", "float u2(vec3 q){ return mapScene(q); }", order=20,
                       hooks=["float mapScene(in vec3 pos)", "float mapScene(const in highp vec3 other)"]),
        "m3.glsl": mod("m3", "float u3(vec2 q){ return mapScene(q); }", order=30, hooks=["float mapScene(vec2 p)"]),
    }).compose(["m1", "m2", "m3"])
    assert out.count("mapScene(vec3 p);") == 1 and "pos);" not in out and "other);" not in out
    assert out.count("float mapScene(vec2 p);") == 1           # an overload is a different function


def test_two_modules_declaring_one_hook_differently_are_refused(tmp_path):
    lib = lib_from(tmp_path, {
        "m1.glsl": mod("m1", "float u1(vec3 q){ return mapScene(q); }", hooks=["float mapScene(vec3 p)"]),
        "m2.glsl": mod("m2", "vec3 u2(vec3 q){ return mapScene(q); }", order=20, hooks=["vec3 mapScene(vec3 p)"]),
        "m3.glsl": mod("m3", "void u3(vec3 q){ float d; mapD(q, d); }", order=20, hooks=["void mapD(vec3 p, float d)"]),
        "m4.glsl": mod("m4", "void u4(vec3 q){ float d; mapD(q, d); }", order=30,
                       hooks=["void mapD(vec3 p, out float d)"]),
    })
    for pair in (["m1", "m2"], ["m3", "m4"]):
        with pytest.raises(M.ModuleError) as err:
            lib.compose(pair)
        assert f"'{pair[0]}'" in str(err.value) and f"'{pair[1]}'" in str(err.value) and "differently" in str(err.value)


@pytest.mark.parametrize("hooks", [["float mapI(vec3 p)", "vec3 mapI(vec3 q)"], ["float mapL(1 + 2)"],
                                   ["float mapM(vec3 p q r)"], ["float mapN(vec3 p[2][2])"],
                                   ["float mapO(in out vec3 p)"]])
def test_a_module_whose_own_hooks_disagree_or_are_malformed_is_refused(hooks):
    with pytest.raises(M.ModuleError) as err:
        M.parse_module(mod("h", "float g(float x){ return x; }", hooks=hooks), "hooky.glsl")
    assert "hooky.glsl" in str(err.value) and "hook" in str(err.value)


def test_a_hook_array_parameter_is_canonical_and_void_means_no_parameters():
    m = M.parse_module(mod("arr", "float g(float x){ return x; }",
                           hooks=["float mapK(float w [ 4 ])", "float mapK(float[4] v)", "float t0(void)", "float t0()"]),
                       "arr.glsl")
    assert m.hooks == ("float mapK(float w[4])", "float t0(void)")


# defect 9: lint without a library cannot know what other modules provide, so it must not say "no module provides".
def test_lint_without_a_library_words_an_unresolved_call_honestly():
    lone = M.parse_module(mod("lone", "float lone(vec3 p){ return helper(p); }", license="Apache-2.0", credits=[]),
                          "lone.glsl")
    msgs = [p for p in M.lint(lone) if "helper()" in p]
    assert len(msgs) == 1 and "no module provides" not in msgs[0] and "not defined in this module" in msgs[0]


# the twins' regular expressions agree outside ASCII (Python's \b, \s and ^ are Unicode-aware; JavaScript's ^ also
# starts a line after \r, U+2028 and U+2029), so a stray character cannot make one twin see a call the other misses.
def test_two_passes_can_live_in_one_library_because_an_entry_point_is_never_provided(tmp_path):
    """Found while building the review fixture: every pass defines mainImage, so the second pass in a library was
    refused (strict) or quarantined (lenient) as a clash. An entry point is placed by a runtime, never called."""
    lib = lib_from(tmp_path, {
        "p1.glsl": mod("p1", "void mainImage(out vec4 o, in vec2 f){ o = vec4(1.0); }", kind="pass", cat="pass"),
        "p2.glsl": mod("p2", "void mainImage(out vec4 o, in vec2 f){ o = vec4(0.0); }", kind="pass", cat="pass"),
    })
    assert lib.names() == ["p1", "p2"] and lib.get("p1").provides == ()


def test_calls_and_definitions_are_read_with_ascii_rules():
    m = M.parse_module(mod("uni", "float ua(float x){ return \u00e9fa(x); }\n"
                                  "float ub(float x){ return x; }\rfloat uc(float y){ return y; }\u2028"
                                  "float ud(float z){ return z; }"), "uni.glsl")
    assert "fa" in m.calls                       # an accented letter is not a GLSL identifier character
    assert {"ua", "ub", "uc"} <= set(m.functions) and "ud" not in m.functions   # \r is a line break; U+2028 is not
    assert "\r" not in m.body
    assert M.normalize_body("float f(){ return 1.; }\u00a0\x1f \n") == "float f(){ return 1.; }\u00a0\x1f"


# ---------- re-review of 2026-10-13, round 2 ----------
# MEDIUM: a file quarantined because it could not be read (or, in a page, fetched) recorded no providers, so a module
# calling what it held composed a dangling call silently. Such a file is now an UNKNOWN provider: while one is
# quarantined, a module with an unresolved call is refused, naming those files. A file that is not UTF-8 is decoded as
# a page decodes it (each bad sequence becomes U+FFFD) and its symbols are salvaged; it is unknown as well only when a
# replacement landed in its code, where it could have hidden a definition.

def _unreadable(monkeypatch, *paths):
    real, blocked = Path.read_bytes, {str(p) for p in paths}

    def read_bytes(self):
        if str(self) in blocked:
            raise PermissionError(13, "Permission denied")
        return real(self)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)


def _write_lib(tmp_path, files) -> Path:
    d = tmp_path / "lib"
    d.mkdir()
    for fname, content in files.items():
        if isinstance(content, bytes):
            (d / fname).write_bytes(content)
        else:
            (d / fname).write_text(content, encoding="utf-8", newline="\n")
    return d


def test_a_file_that_cannot_be_read_is_an_unknown_provider_and_an_unresolved_call_is_refused(tmp_path, monkeypatch):
    d = _write_lib(tmp_path, {
        "a-gone.glsl": mod("gone-mod", "float goneF(float x){ return x; }"),
        "b-user.glsl": mod("user", "float u(float x){ return goneF(x); }", order=20),
        "c-hooked.glsl": mod("hooked", "float hk(vec3 p){ return mapScene(p); }", order=20,
                             hooks=["float mapScene(vec3 p)"]),
        "d-plain.glsl": mod("plain", "float pl(float x){ return x; }", order=20),
        "e-needs.glsl": mod("needy", "float nd(float x){ return x; }", order=20, needs=["gone-mod"]),
        "f-snip.glsl": mod("snip", "col *= goneF(uv.x);", kind="modifier", cat="modifier"),
    })
    gone = d / "a-gone.glsl"
    _unreadable(monkeypatch, gone)
    lib = M.load_library([d], strict=False)
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["user"])
    msg = str(err.value)
    assert "module 'user' calls goneF()" in msg and "could not read in full" in msg and str(gone) in msg
    with pytest.raises(M.ModuleError) as err:
        lib.prelude(["snip"])
    assert "module 'snip' calls goneF()" in str(err.value) and str(gone) in str(err.value)
    with pytest.raises(M.ModuleError) as err:
        lib.resolve(["needy"])
    assert "needs 'gone-mod'" in str(err.value) and str(gone) in str(err.value)
    assert "float mapScene(vec3 p);" in lib.compose(["hooked"])     # a hook covers it: the host defines it
    assert "// --- plain (math) ---" in lib.compose(["plain"])       # nothing unresolved, nothing refused
    assert lib.unknown == [str(gone)]
    assert [(Path(p["path"]).name, p["name"]) for p in lib.problems] == [("a-gone.glsl", None)]
    with pytest.raises(M.ModuleError) as err:
        M.load_library([d])
    assert str(err.value) == f"{gone}: cannot be read (Permission denied)"


def test_a_file_that_is_not_utf8_is_decoded_as_a_page_decodes_it_and_its_symbols_are_salvaged(tmp_path):
    raw = mod("latin", "// caf\xe9\nfloat lat(float x){ return x; }").encode("latin-1")
    d = _write_lib(tmp_path, {
        "a-latin.glsl": raw,
        "b-user.glsl": mod("user", "float u(float x){ return lat(x); }", order=20),
        "c-typo.glsl": mod("typo", "float ty(float x){ return missingFn(x); }", order=20),
    })
    latin = d / "a-latin.glsl"
    lib = M.load_library([d], strict=False)
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["user"])
    assert f"module 'user' calls lat() (only the quarantined file {latin} provides it)" in str(err.value)
    assert lib.unknown == []                          # the bad byte sat in a comment: every symbol was read
    assert "missingFn(x)" in lib.compose(["typo"])    # so a typo stays lint's to catch, not a refusal
    text, problem = M.decode_source(raw, str(latin))
    bad = raw.index(b"\xe9")
    assert text == raw.decode("utf-8", errors="replace") and "\ufffd" in text
    assert problem == f"{latin}: is not UTF-8 text (byte {bad} cannot be decoded)"
    assert M.decode_source("\ufeffok \u00e9".encode("utf-8"), "x") == ("\ufeffok \u00e9", None)   # BOM kept, as read


def test_a_bad_byte_in_code_makes_the_file_unknown_as_well_as_salvaged(tmp_path):
    d = _write_lib(tmp_path, {
        "a-code.glsl": mod("code", "float codeF(float x){ return x * 2.0\xb5; }").encode("latin-1"),
        "b-user.glsl": mod("user", "float u(float x){ return codeF(x); }", order=20),
        "c-typo.glsl": mod("typo", "float ty(float x){ return missingFn(x); }", order=20),
    })
    code = d / "a-code.glsl"
    lib = M.load_library([d], strict=False)
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["user"])
    assert f"module 'user' calls codeF() (only the quarantined file {code} provides it)" in str(err.value)
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["typo"])
    assert "module 'typo' calls missingFn()" in str(err.value) and str(code) in str(err.value)
    assert lib.unknown == [str(code)]


# LOW: a data symbol a quarantined file held refused every module with a parameter or local of the same name, and a
# broken snippet's block-local const was salvaged as a file-scope provider.
def test_a_lost_const_does_not_refuse_a_module_whose_own_parameter_or_local_has_its_name():
    lib = M.library_from_sources([
        ("a/s.glsl", mod("s", "float sa(float x){ return x; }")),
        ("b/s.glsl", mod("s", "const float k = 2.0;\nfloat sb(float x){ return x * k; }")),
        ("u.glsl", mod("u", "float u(float k){ return k * 2.0; }", order=20)),
        ("v.glsl", mod("v", "float v(float x){ float k = x; return k; }", order=20)),
        ("w.glsl", mod("w", "float w(float x){ return x * k; }", order=20)),
    ], strict=False)
    assert "// --- u (math) ---" in lib.compose(["u"]) and "// --- v (math) ---" in lib.compose(["v"])
    with pytest.raises(M.ModuleError) as err:
        lib.compose(["w"])
    assert "module 'w' uses k (only the quarantined file b/s.glsl provides it)" in str(err.value)
    assert "k" in lib.get("u").declared and "k" in lib.get("v").declared and "k" not in lib.get("w").declared


def test_a_broken_snippets_block_local_const_is_not_salvaged_as_a_provider():
    lib = M.library_from_sources([
        ("snip.glsl", '//! {"name": "snip", "kind": "modifier" oops}\nconst float t = 0.5;\ncol *= t;\n'),
        ("u.glsl", mod("u", "float u(float x){ return x * t; }", order=20)),
        ("broken.glsl", '//! {"name": "broken", "kind": "helper",\nconst float LOSTC = 1.0;\n'),
        ("nokind.glsl", '//! {"name": "nokind",\nconst float NK = 1.0;\n'),
        ("w.glsl", mod("w", "float w(float x){ return x * LOSTC + NK; }", order=20)),
    ], strict=False)
    assert "// --- u (math) ---" in lib.compose(["u"])
    with pytest.raises(M.ModuleError) as err:     # a composable kind, or one that cannot be read: kept (fail closed)
        lib.compose(["w"])
    assert "uses LOSTC" in str(err.value) and "uses NK" in str(err.value)


# LOW: Python's json recursed past its limit on a deeply nested header ("not JSON") while V8 parsed it and composed.
def test_a_header_nested_too_deep_is_refused_by_a_count_both_twins_share():
    body = "\nfloat fd(float x){ return x; }"
    with pytest.raises(M.ModuleError) as err:
        M.parse_module('//! {"name": "d", "kind": "helper", "x": ' + "[" * 1500 + "]" * 1500 + "}" + body, "deep.glsl")
    assert str(err.value) == "deep.glsl: the //! header nests deeper than 32 levels"
    edge = "[" * 31 + "]" * 31                     # with the header object itself, 32 levels: the limit, allowed
    assert M.parse_module('//! {"name": "d", "kind": "helper", "x": ' + edge + "}" + body, "edge.glsl").name == "d"
    quoted = '"' + "[{" * 100 + '\\"]"'           # brackets inside a string never count
    assert M.parse_module('//! {"name": "q", "kind": "helper", "note": ' + quoted + "}" + body, "q.glsl").name == "q"


def test_the_usage_line_lists_every_target():
    line = next(row for row in M.__doc__.splitlines() if "--target" in row)
    assert sorted(line.split("--target ", 1)[1].split("]", 1)[0].split("|")) == sorted(M.TARGET_LACKS)


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


# The S1 parity fixture: one library that exercises every extension (struct, const, hook, quarantine, target), run
# through both twins by one plan. Every composed text, every error message and every quarantine record must match,
# except the JSON parser's own detail for a broken header (each language words it differently; see _comparable).

def _review_fixture_files() -> dict:
    """The review-fix half of the parity fixture: one file per defect the 2026-10-13 review found, loaded leniently
    beside the S1 library so every quarantine message, refusal and composed text is compared between the twins."""
    raw = '//! {{"name": "{name}", "kind": "helper"{extra}}}\nfloat {fn}(float x){{ return x; }}\n'
    files = {
        # defect 1: a hook naming its own module's struct or const
        "own/struct-hook.glsl": mod("own-struct", "struct Acc { float a; };\nAcc stepAcc(vec3 p){ return shadeAcc(p, 0.0); }",
                                    hooks=["Acc shadeAcc(vec3 p, float t)"]),
        "own/const-hook.glsl": mod("own-const", "const int N = 4;\nfloat sumN(float w[N]){ return gN(w); }",
                                   hooks=["float gN(float w [ N ])"]),
        "own/user-acc.glsl": mod("user-acc", "float userAcc(vec3 p){ Acc a = stepAcc(p); return a.a; }", order=20),
        # defect 6: header values
        "hdr/v-newline.glsl": mod("v-newline", "float vn1(float x){ return x; }", version="1.0.0\n// sha256: forged"),
        "hdr/v-space.glsl": mod("v-space", "float vn2(float x){ return x; }", version="1.0 beta"),
        "hdr/cat-float.glsl": raw.format(name="cat-float", extra=', "cat": 1.0', fn="cf"),
        "hdr/cat-surrogate.glsl": raw.format(name="cat-surrogate", extra=', "cat": "\\ud800"', fn="cs"),
        "hdr/order-true.glsl": mod("order-true", "float ot(float x){ return x; }", order=True),
        "hdr/order-str.glsl": mod("order-str", "float os(float x){ return x; }", order="10"),
        "hdr/order-nan.glsl": raw.format(name="order-nan", extra=', "order": NaN', fn="on"),
        "hdr/order-inf.glsl": raw.format(name="order-inf", extra=', "order": 1e400', fn="oi"),
        "hdr/kind-list.glsl": '//! {"name": "kind-list", "kind": []}\nfloat kl(float x){ return x; }\n',
        "hdr/kind-obj.glsl": '//! {"name": "kind-obj", "kind": {}}\nfloat ko(float x){ return x; }\n',
        "hdr/kind-tostring.glsl": '//! {"name": "kind-ts", "kind": {"toString": 1}}\nfloat kt(float x){ return x; }\n',
        "hdr/name-space.glsl": mod("two words", "float nsp(float x){ return x; }"),
        "hdr/needs-str.glsl": mod("needs-str", "float nst(float x){ return x; }", needs="types"),
        "hdr/needs-obj.glsl": mod("needs-obj", "float nob(float x){ return x; }", needs={"types": 1}),
        "hdr/version-ok.glsl": mod("version-ok", "float vok(float x){ return x; }", version="1.2.0-beta.1+b5",
                                   order=12.5),
        # defect 5: a BOM, a non-breaking space before //!, and whitespace the twins used to trim differently
        "bom/bom.glsl": "\ufeff" + mod("bom-mod", "float bomF(float x){ return x; }"),
        "bom/nbsp.glsl": "\u00a0" + mod("nbsp-mod", "float nbF(float x){ return x; }"),
        "ws/body-ws.glsl": mod("body-ws", "float bw(float x){ return x; }\u00a0\x1f\ufeff \n"),
        # defect 8: hooks by signature
        "hooks/h1.glsl": mod("hk1", "float hu1(vec3 q){ return mapH(q); }", hooks=["float mapH(vec3 p)"]),
        "hooks/h2.glsl": mod("hk2", "float hu2(vec3 q){ return mapH(q); }", order=20,
                             hooks=["float mapH(in vec3 pos)", "float mapH(const in highp vec3 other)"]),
        "hooks/h3.glsl": mod("hk3", "vec3 hu3(vec3 q){ return mapH(q); }", order=30, hooks=["vec3 mapH(vec3 p)"]),
        "hooks/h4.glsl": mod("hk4", "float hu4(vec2 q){ return mapH(q); }", order=30, hooks=["float mapH(vec2 p)"]),
        "hooks/h5.glsl": mod("hk5", "float hu5(vec3 q){ return mapI(q); }", hooks=["float mapI(vec3 p)", "vec3 mapI(vec3 q)"]),
        "hooks/h6.glsl": mod("hk6", "float hu6(float x){ return mapK(float[4](x, x, x, x)) + t0(); }",
                             hooks=["float mapK(float w [ 4 ])", "float mapK(float[4] v)", "float t0(void)", "float t0()"]),
        "hooks/h7.glsl": mod("hk7", "float hu7(float x){ return x; }", hooks=["float mapL(1 + 2)"]),
        "hooks/h8.glsl": mod("hk8", "void hu8(vec3 q){ float d; mapD(q, d); }", hooks=["void mapD(vec3 p, out float d)"]),
        "hooks/h9.glsl": mod("hk9", "void hu9(vec3 q){ float d; mapD(q, d); }", order=20,
                             hooks=["void mapD(vec3 p, inout float d)"]),
        # defect 7: GLSL ES 1.00 and the three.js material without GLSL3
        "glsl/es1.glsl": mod("es1", "float es1(float x){ return x * 0.5; }", targets={"glsl": "100", "needs": []}),
        "glsl/es3.glsl": mod("es3", "float es3(float x){ return es1(x); }", order=20, targets={"glsl": "300es"}),
        "glsl/pass1.glsl": mod("pass1", "void mainImage(out vec4 o, in vec2 f){ o = vec4(es1(f.x)); }", kind="pass",
                               cat="pass", targets={"glsl": "100"}),
        # the twins' regular expressions outside ASCII, a lone CR, and quoting in messages
        "misc/uni-call.glsl": mod("uni-call", "float uc0(float x){ return \u00e9es1(x); }"),
        "misc/lone-cr.glsl": mod("lone-cr", "float lc1(float x){ return x; }\rfloat lc2(float y){ return y; }\u2028"
                                            "float lc3(float z){ return z; }"),
        "misc/quote-need.glsl": mod("quote-need", "float qn(float x){ return x; }", needs=["it's"]),
    }
    files.update({"lost/" + k: v for k, v in LOST_LIB.items()})    # defect 2: dangling calls after a quarantine
    return files


REVIEW_CASES = [
    {"op": "compose", "names": ["user-q"]},
    {"op": "compose", "names": ["user-l"]},
    {"op": "compose", "names": ["user-h"]},
    {"op": "compose", "names": ["user-n"]},
    {"op": "prelude", "names": ["snip-q"]},
    {"op": "compose", "names": ["user-acc"]},
    {"op": "compose", "names": ["bom-mod", "body-ws", "version-ok"]},
    {"op": "compose", "names": ["hk1", "hk2", "hk4", "hk6"]},
    {"op": "compose", "names": ["hk1", "hk3"]},
    {"op": "compose", "names": ["hk8", "hk9"]},
    {"op": "compose", "names": ["es1"], "target": "webgl1"},
    {"op": "compose", "names": ["es1"], "target": "three-r186-glsl1"},
    {"op": "compose", "names": ["es3"], "target": "webgl1"},
    {"op": "compose", "names": ["es3", "uni-call"], "target": "three-r186-glsl1"},
    {"op": "prelude", "names": ["pass1"], "target": "three-r186-glsl1"},
    {"op": "prelude", "names": ["pass1"], "target": "webgl1"},
    {"op": "compose", "names": ["uni-call", "lone-cr"]},
    {"op": "resolve", "names": ["quote-need"]},
    {"op": "compose", "names": ["no'pe"]},
]


def _round_two_files() -> tuple:
    """The re-review's round-2 fixture: (four, five). four holds the data-symbol false refusals, the salvage of a
    broken header's kind, the nesting limit and a file that is not UTF-8 (all known providers); five holds the unknown
    providers: a file the loader cannot read (the plan names it "unreadable") and one whose bad byte sits in code."""
    four = {
        "data/a-s.glsl": mod("s4", "float sa4(float x){ return x; }"),
        "data/b-s.glsl": mod("s4", "const float k = 2.0;\nfloat sb4(float x){ return x * k; }"),
        "data/c-param.glsl": mod("param-k", "float pk(float k){ return k * 2.0; }", order=20),
        "data/d-local.glsl": mod("local-k", "float lk(float x){ float k = x; return k; }", order=20),
        "data/e-uses.glsl": mod("uses-k", "float uk(float x){ return x * k; }", order=20),
        "data/f-snip.glsl": '//! {"name": "snip4", "kind": "modifier" oops}\nconst float t = 0.5;\ncol *= t;\n',
        "data/g-uses-t.glsl": mod("uses-t", "float ut(float x){ return x * t; }", order=20),
        "data/h-broken.glsl": '//! {"name": "broken4", "kind": "helper",\nstruct Lost4 { float a; };\n'
                              'const float LOSTC = 1.0;\nfloat lost4(float x){ return x; }\n',
        "data/i-user.glsl": mod("user4", "float u4(float x){ Lost4 a = Lost4(x); return a.a * LOSTC + lost4(x); }",
                                order=20),
        "data/j-nokind.glsl": '//! {"name": "nokind4",\nconst float NK = 1.0;\ncol *= NK;\n',
        "data/k-uses-nk.glsl": mod("uses-nk", "float unk(float x){ return x * NK; }", order=20),
        "nest/deep.glsl": '//! {"name": "deep4", "kind": "helper", "x": ' + "[" * 1500 + "]" * 1500 +
                          '}\nfloat deep4(float x){ return x; }\n',
        "nest/edge.glsl": '//! {"name": "nest-edge", "kind": "helper", "x": ' + "[" * 31 + "]" * 31 +
                          ', "note": "' + "[{" * 40 + '\\""}\nfloat nestEdge(float x){ return x; }\n',
        "nest/user.glsl": mod("nest-user", "float nu(float x){ return deep4(x) + nestEdge(x); }", order=20),
        "utf/latin.glsl": mod("latin4", "// caf\xe9 \x96 na\xefve\nfloat latF(float x){ return x; }\n").encode("latin-1"),
        "utf/typo.glsl": mod("typo4", "float ty4(float x){ return missing4(x); }", order=20),
        "utf/user.glsl": mod("utf-user", "float uu(float x){ return latF(x); }", order=20),
        "utf/z-bom2.glsl": "\ufeff\ufeff" + mod("bom2", "float b2(float x){ return x; }"),
    }
    five = {
        "a-gone.glsl": mod("gone5", "float goneF(float x){ return x; }"),
        "b-code.glsl": mod("code5", "float codeF(float x){ return x * 2.0\xb5; }").encode("latin-1"),
        "c-user.glsl": mod("user5", "float u5(float x){ return goneF(x); }", order=20),
        "d-code-user.glsl": mod("code-user5", "float cu5(float x){ return codeF(x); }", order=20),
        "e-hooked.glsl": mod("hooked5", "float hk5(vec3 p){ return mapScene(p); }", order=20,
                             hooks=["float mapScene(vec3 p)"]),
        "f-plain.glsl": mod("plain5", "float pl5(float x){ return x; }", order=20),
        "g-needs.glsl": mod("needs5", "float nd5(float x){ return x; }", order=20, needs=["gone5"]),
        "h-snip.glsl": mod("snip5", "col *= goneF(uv.x);", kind="modifier", cat="modifier"),
    }
    return four, five


FOUR_CASES = [{"op": "compose", "names": [n]} for n in (
    "param-k", "local-k", "uses-k", "uses-t", "user4", "uses-nk", "nest-edge", "nest-user", "utf-user", "typo4")]
FIVE_CASES = [{"op": "compose", "names": [n]} for n in ("user5", "code-user5", "hooked5", "plain5")] + [
    {"op": "resolve", "names": ["needs5"]}, {"op": "prelude", "names": ["snip5"]}]
# Bytes the two decoders must turn into the same text and the same first bad byte (WHATWG's UTF-8 decoder in the
# page, Python's errors="replace" in the CLI): overlong forms, surrogates, past U+10FFFF, truncations, BOMs.
DECODE_CASES = ["", "6f6b", "efbbbf6f6b", "efbbbfefbbbf6f6b", "80", "c080", "c3", "c341", "e08080", "eda080",
                "f4908080", "e282", "e28241", "f09f98", "f09f9841", "ff", "636166e9206f6b", "c3a9f09d849ee96f6b",
                "f8888080", "eda080eda080", "e2828220ff41"]


def _parity_fixture(root: Path) -> dict:
    one, two, served = root / "one", root / "two", root / "served"
    files_one = {
        "core/types.glsl": mod("types", "struct VolAccum { vec3 col; float a; };\n"
                                        "const float TAU = 6.28318530718, HALF_PI = 1.57079632679;",
                               order=10, version="1.2.0"),
        "bits/pcg.glsl": mod("pcg", "uint pcgHash(uint v){ uint s = v * 747796405u + 2891336453u; "
                                    "return s ^ (s >> 16u); }", cat="hash", order=12, version="0.1.0",
                             targets={"glsl": "300es", "needs": ["uint"]}),
        "bits/edge.glsl": mod("edge", "float edgeAA(float d){ return clamp(0.5 - d / fwidth(d), 0.0, 1.0); }\n"
                                      "vec4 tap(sampler2D s, ivec2 p){ return texelFetch(s, p, 0); }",
                              order=13, targets={"needs": ["derivatives", "texelFetch"]}),
        "march/march.glsl": mod("march", "// marches the host's scene (é — \U0001d11e)\n"
                                         "VolAccum marchVol(vec3 ro, vec3 rd){\n"
                                         "  VolAccum acc = VolAccum(vec3(0.0), 0.0);\n  float travel = 0.25;\n"
                                         "  for (int n = 0; n < 7; n++) { float gap = mapScene(rd * travel - ro); "
                                         "acc.a += exp(-gap) / TAU; travel += max(gap, 0.02); }\n  return acc;\n}\n\n\n\n",
                                cat="volume", order=20, version="0.3.0",
                                hooks=["float mapScene(vec3 p)", " VolAccum  shadeStep( vec3 p , float t ) ;"]),
        "march/shade.glsl": mod("shade", "/* the host owns the sky */\nvec3 shadeVol(vec3 ro, vec3 rd){ "
                                         "VolAccum a = marchVol(ro, rd); return skyColour(rd) * a.a * HALF_PI; }",
                                cat="volume", order=30, hooks=["float mapScene(vec3 p)", "vec3 skyColour(vec3 rd)"]),
        "lint/typo.glsl": mod("typo", "float typoUser(vec3 p){ return mapScen(p) + float(pcgHash(1u)); }",
                              order=40, hooks=["float mapScene(vec3 p)"]),
        "pass/trail.glsl": mod("trail", "void mainImage(out vec4 o, in vec2 f){ o = vec4(edgeAA(f.x)); }",
                               kind="pass", cat="pass", order=60),
        "snip/tint.glsl": mod("tint", "const float K = 2.0;\ncol *= K * TAU;", kind="modifier", cat="modifier",
                              order=50),
    }
    files_two = {
        "core/types.glsl": mod("types", "struct Other { float x; };"),
        "clash/struct.glsl": mod("struct-twin", "struct VolAccum { float only; };"),
        "clash/const.glsl": mod("const-twin", "const float TAU = 6.2831853;"),
        "bad/hook.glsl": mod("bad-hook", "float bh(float x){ return x; }", hooks=["not a prototype"]),
        "bad/json.glsl": '//! {"name": "bad-json",\nfloat bj(float x){ return x; }\n',
        "ok/extra.glsl": mod("extra", "float extraWave(float x){ return sin(x * TAU); }", order=15),
    }
    for base, files in ((one, files_one), (two, files_two)):
        for rel, text in files.items():
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
    three = root / "three"
    for rel, text in _review_fixture_files().items():
        p = three / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    four, five = root / "four", root / "five"
    for base, files in zip((four, five), _round_two_files()):
        for rel, content in files.items():
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                p.write_bytes(content)
            else:
                p.write_text(content, encoding="utf-8", newline="\n")
    unreadable = {str(five / "a-gone.glsl"): "Permission denied"}
    for rel in ("core/types.glsl", "march/march.glsl", "march/shade.glsl"):
        p = served / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(files_one[rel], encoding="utf-8", newline="\n")
    page = root / "page"
    page.mkdir()
    (page / "ok.glsl").write_text(mod("page-ok", "float pageOk(float x){ return x; }"), encoding="utf-8", newline="\n")
    (page / "weird.glsl").write_text('//! {"name": "weird", "kind": {"toString": 1}}\nfloat w(float x){ return x; }\n',
                                     encoding="utf-8", newline="\n")
    # round 2: a caller of what the 404 held, a file that is not UTF-8 and its caller, and two BOMs (a browser's
    # Response.text() drops one BOM itself, so the page used to load what the CLI refuses)
    (page / "user.glsl").write_text(mod("page-user", "float pu(float x){ return goneF(x); }", order=20),
                                    encoding="utf-8", newline="\n")
    (page / "latin.glsl").write_bytes(mod("page-latin", "// na\xefve\nfloat latP(float x){ return x; }\n")
                                      .encode("latin-1"))
    (page / "latin-user.glsl").write_text(mod("page-latin-user", "float plu(float x){ return latP(x); }", order=20),
                                          encoding="utf-8", newline="\n")
    (page / "bom2.glsl").write_text("\ufeff\ufeff" + mod("page-bom2", "float pb2(float x){ return x; }"),
                                    encoding="utf-8", newline="\n")
    (page / "index.json").write_text(json.dumps({"api": M.API, "files": [
        "gone.glsl", {"path": "ok.glsl", "sha256": "0" * 64}, "unreachable/net.glsl", "weird.glsl", {"nopath": 1},
        "user.glsl", "latin.glsl", "latin-user.glsl", "bom2.glsl"]}), encoding="utf-8")
    old_index = served / "index-old.json"
    old_index.write_text(json.dumps({"api": M.API, "files": ["core/types.glsl", "march/march.glsl",
                                                              "march/shade.glsl"]}), encoding="utf-8")
    M.write_index(served, index_path=served / "index.json", archive_dir=root / "archive")
    cases = [
        {"op": "compose", "names": ["shade"]},
        {"op": "compose", "names": ["shade"], "target": "webgl1"},
        {"op": "compose", "names": ["typo"], "target": "webgl1"},
        {"op": "compose", "names": ["pcg", "edge", "extra"], "target": "webgl1"},
        {"op": "compose", "names": ["pcg", "edge"], "target": "three-r186"},
        {"op": "prelude", "names": ["trail"], "target": "three-r186"},
        {"op": "prelude", "names": ["trail"], "target": "toy"},
        {"op": "compose", "names": ["trail"], "target": "webgl2"},
        {"op": "prelude", "names": ["tint"]},
        {"op": "compose", "names": ["extra"], "target": "webgl3"},
        {"op": "compose", "names": ["nowhere"]},
        {"op": "compose", "names": []},
        {"op": "resolve", "names": ["typo", "shade"]},
    ]
    return {
        "libraries": [
            {"dirs": [str(one), str(two)], "strict": False, "cases": cases},
            {"dirs": [str(one)], "strict": True, "cases": cases},
            {"dirs": [str(one), str(two)], "strict": True, "cases": []},
            {"dirs": [str(one), str(two / "core")], "strict": True, "cases": []},
            {"dirs": [str(one), str(two / "clash")], "strict": True, "cases": []},
            {"dirs": [str(one), str(three)], "strict": False, "cases": REVIEW_CASES},
            {"dirs": [str(three)], "strict": True, "cases": []},
            {"dirs": [str(three / "own")], "strict": True, "cases": []},
            # round 2 (indices 8-12)
            {"dirs": [str(four)], "strict": False, "cases": FOUR_CASES},
            {"dirs": [str(four / "utf")], "strict": True, "cases": []},
            {"dirs": [str(four / "nest")], "strict": True, "cases": []},
            {"dirs": [str(five)], "strict": False, "cases": FIVE_CASES, "unreadable": unreadable},
            {"dirs": [str(five)], "strict": True, "cases": [], "unreadable": unreadable},
        ],
        "decode": DECODE_CASES,
        "index_loads": [{"index": str(old_index), "names": ["shade"]},
                        {"index": str(served / "index.json"), "names": ["shade"]}],
        "page_loads": [{"index": str(page / "index.json"), "strict": False,
                        "cases": [["page-ok"], ["page-user"], ["page-latin-user"]]},
                       {"index": str(page / "index.json"), "strict": True, "cases": [["page-ok"]]},
                       {"index": str(page / "index.json"), "strict": False, "text_only": True,
                        "cases": [["page-ok"], ["page-user"]]}],
        "sha256": ["", "a", "abc", "x" * 55, "x" * 56, "x" * 63, "x" * 64, "x" * 65, "x" * 119, "x" * 120,
                   "é — \U0001d11e " * 40],
        "_served": str(served),
    }


def _attempt(fn):
    try:
        return {"ok": fn()}
    except M.ModuleError as exc:
        return {"error": str(exc)}


def _load_with_unreadable(spec: dict):
    """load_library, with the files the spec names as "unreadable" raising PermissionError when read (the JavaScript
    runner hands the same files to libraryFromSources as [path, null, problem])."""
    unreadable, real = spec.get("unreadable") or {}, Path.read_bytes

    def read_bytes(self):
        if str(self) in unreadable:
            raise PermissionError(13, unreadable[str(self)])
        return real(self)
    Path.read_bytes = read_bytes
    try:
        return M.load_library(spec["dirs"], strict=spec["strict"])
    finally:
        Path.read_bytes = real


def _run_plan_in_python(plan: dict) -> dict:
    out = {"libraries": [], "index_loads": [],
           "sha256": [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in plan["sha256"]],
           "decode": [list(M.decode_source(bytes.fromhex(h), "x.glsl")) for h in plan["decode"]]}
    for spec in plan["libraries"]:
        try:
            lib = _load_with_unreadable(spec)
        except M.ModuleError as exc:
            out["libraries"].append({"load_error": str(exc)})
            continue
        mods = {}
        for n in lib.names():
            m = lib.modules[n]
            mods[n] = {"provides": list(m.provides), "calls": list(m.calls), "uses": list(m.uses),
                       "declared": list(m.declared), "hooks": list(m.hooks), "version": m.version,
                       "needs": list(m.target_needs),
                       "deps": _attempt(lambda n=n: lib.deps(n)), "unresolved": _attempt(lambda n=n: lib.unresolved(n))}
        results = []
        for case in spec["cases"]:
            op, names, target = case["op"], case["names"], case.get("target")
            if op == "compose":
                results.append(_attempt(lambda: lib.compose(names, target=target)))
            elif op == "prelude":
                results.append(_attempt(lambda: lib.prelude(names, target=target)))
            else:
                results.append(_attempt(lambda: lib.resolve(names)))
        out["libraries"].append({"names": lib.names(), "problems": lib.problems, "unknown": lib.unknown,
                                 "modules": mods, "cases": results})
    for load in plan["index_loads"]:
        lib = M.load_library([plan["_served"]], strict=False)
        out["index_loads"].append({"names": lib.names(), "problems": lib.problems,
                                   "compose": lib.compose(load["names"])})
    return out


def _comparable(result: dict) -> dict:
    """Cut a broken header's message after 'is not JSON': the detail that follows is each JSON parser's own words."""
    def cut(text):
        mark = "the //! header is not JSON"
        return text[:text.index(mark) + len(mark)] if mark in text else text
    for lib in result["libraries"]:
        if "load_error" in lib:
            lib["load_error"] = cut(lib["load_error"])
        for p in lib.get("problems", []):
            p["problem"] = cut(p["problem"])
    return result


def _run_js(plan: dict, tmp_path) -> dict:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    script = REPO / "tests" / "glsl_modlib_parity.mjs"
    run = subprocess.run(["node", str(script), "--plan", str(plan_path)], capture_output=True, text=True,
                         encoding="utf-8", timeout=60)
    assert run.returncode == 0, run.stderr[-2000:]
    return _comparable(json.loads(run.stdout))


def _run_both_twins(tmp_path):
    plan = _parity_fixture(tmp_path)
    js = _run_js(plan, tmp_path)
    py = _comparable(json.loads(json.dumps(_run_plan_in_python(plan))))
    return js, py, plan


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_javascript_twin_matches_on_every_review_fix(tmp_path):
    js, py, plan = _run_both_twins(tmp_path)
    review = py["libraries"][5]
    three = Path(plan["libraries"][5]["dirs"][1])
    quarantined = {Path(p["path"]).relative_to(three).as_posix(): p["name"] for p in review["problems"]}
    assert quarantined == {
        "bom/nbsp.glsl": None, "hdr/cat-float.glsl": None, "hdr/cat-surrogate.glsl": None,
        "hdr/kind-list.glsl": None, "hdr/kind-obj.glsl": None, "hdr/kind-tostring.glsl": None,
        "hdr/name-space.glsl": None, "hdr/needs-obj.glsl": None, "hdr/needs-str.glsl": None,
        "hdr/order-inf.glsl": None, "hdr/order-nan.glsl": None, "hdr/order-str.glsl": None,
        "hdr/order-true.glsl": None, "hdr/v-newline.glsl": None, "hdr/v-space.glsl": None,
        "hooks/h5.glsl": None, "hooks/h7.glsl": None, "lost/b-noise.glsl": "noise", "lost/c-broken.glsl": None,
        "own/const-hook.glsl": None, "own/struct-hook.glsl": None}
    cases = dict(zip([json.dumps(c) for c in REVIEW_CASES], review["cases"]))

    def case(**c):
        return cases[json.dumps(c)]
    assert "fbmQ()" in case(op="compose", names=["user-q"])["error"]
    assert "uses LostAcc" in case(op="compose", names=["user-l"])["error"]
    assert "ok" in case(op="compose", names=["user-h"])
    assert "quarantined" in case(op="compose", names=["user-acc"])["error"]
    both = case(op="compose", names=["bom-mod", "body-ws", "version-ok"])["ok"]
    assert "version-ok@1.2.0-beta.1+b5" in both and "\ufeff" not in both.split("// --- body-ws")[0]
    hooked = case(op="compose", names=["hk1", "hk2", "hk4", "hk6"])["ok"]
    assert hooked.count("float mapH(vec3 p);") == 1 and "float mapH(vec2 p);" in hooked
    assert "float mapK(float w[4]);\nfloat t0(void);" in hooked
    assert "differently" in case(op="compose", names=["hk1", "hk3"])["error"]
    assert "differently" in case(op="compose", names=["hk8", "hk9"])["error"]
    assert "ok" in case(op="compose", names=["es1"], target="webgl1")
    assert "module 'es3' is GLSL ES 3.00" in case(op="compose", names=["es3"], target="webgl1")["error"]
    assert "module 'pass1' is kind 'pass'" in case(op="prelude", names=["pass1"], target="three-r186-glsl1")["error"]
    assert "ok" in case(op="prelude", names=["pass1"], target="webgl1")
    assert review["modules"]["uni-call"]["deps"] == {"ok": ["es1"]}
    assert review["modules"]["lone-cr"]["provides"] == ["lc1", "lc2"]
    assert "needs 'it's'" in case(op="resolve", names=["quote-need"])["error"]
    assert case(op="compose", names=["no'pe"]) == {"error": "no module named 'no'pe'"}
    assert py["libraries"][6]["load_error"].startswith(str(three / "bom" / "nbsp.glsl"))
    assert py["libraries"][7]["load_error"].startswith(str(three / "own" / "const-hook.glsl"))
    for i in (5, 6, 7):
        assert js["libraries"][i] == py["libraries"][i], f"library spec {i} differs between the twins"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_a_lenient_page_load_quarantines_a_file_it_cannot_fetch_or_parse(tmp_path):
    """Review defect 3: one missing file used to throw from the whole page load. Pages have no Python twin for fetch,
    so this pins the JavaScript door against the expected records directly.

    Round 2: what a 404, a dropped connection or a pathless index entry held is UNKNOWN, so while one is quarantined a
    module with an unresolved call is refused naming them (it used to compose `return goneF(x);` silently); a file that
    is not UTF-8 is quarantined with its symbols salvaged, exactly as the CLI does (it used to load with U+FFFD); and
    one BOM is dropped, not the two a browser's Response.text() plus sourceLines used to drop."""
    lenient, strict, text_only = _run_js(_parity_fixture(tmp_path), tmp_path)["page_loads"]
    assert lenient["names"] == ["page-latin-user", "page-ok", "page-user"]
    assert [(p["path"], p["name"]) for p in lenient["problems"]] == [
        ("gone.glsl", None), ("unreachable/net.glsl", None), ("weird.glsl", None), ("index.files[4]", None),
        ("latin.glsl", None), ("bom2.glsl", None)]
    problems = [p["problem"] for p in lenient["problems"]]
    assert problems[0] == "gone.glsl: HTTP 404"
    assert "could not be fetched" in problems[1] and "kind" in problems[2] and "names no path" in problems[3]
    bad = (tmp_path / "page" / "latin.glsl").read_bytes().index(b"\xef")
    assert problems[4] == f"latin.glsl: is not UTF-8 text (byte {bad} cannot be decoded)"
    assert problems[5] == "bom2.glsl: no //! header on the first line"
    assert lenient["unknown"] == ["gone.glsl", "unreachable/net.glsl", "index.files[4]"]
    ok, user, latin_user = lenient["cases"]
    assert ok["ok"].startswith("// " + M.API + " compose: page-ok")
    assert user == {"error": "cannot compose: part of it was quarantined at load (see library.problems): module "
                             "'page-user' calls goneF(), which no loaded module provides (a quarantined file the "
                             "library could not read in full may: gone.glsl, unreachable/net.glsl, index.files[4])"}
    assert "module 'page-latin-user' calls latP() (only the quarantined file latin.glsl provides it)" in latin_user["error"]
    assert strict == {"error": "gone.glsl: HTTP 404"}
    # a fetch shim with no arrayBuffer() still loads through text(): the unknown providers still refuse a dangling
    # call, but text() has already replaced the bad bytes and dropped a BOM, so those two files load (only a real
    # Response gives the page the CLI's bytes)
    assert text_only["unknown"] == lenient["unknown"]
    assert text_only["cases"][0]["ok"] == ok["ok"] and text_only["cases"][1] == user
    assert {"page-latin", "page-bom2"} <= set(text_only["names"])


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_javascript_twin_matches_on_every_s1_extension(tmp_path):
    js, py, _ = _run_both_twins(tmp_path)
    # the fixture really exercises what it claims (a parity pin over an empty library would prove nothing)
    lenient = py["libraries"][0]
    assert [p["name"] for p in lenient["problems"]] == [None, None, "const-twin", "struct-twin", "types"]
    assert "// hooks\n" in lenient["cases"][0]["ok"] and "error" in lenient["cases"][2]
    assert lenient["modules"]["tint"]["deps"] == {"ok": ["types"]}
    assert lenient["modules"]["typo"]["unresolved"] == {"ok": ["mapScen"]}
    assert all("load_error" in lib for lib in py["libraries"][2:5])
    for key in ("sha256", "index_loads", "decode"):
        assert js[key] == py[key], key
    assert len(js["libraries"]) == len(py["libraries"]) == 13
    for i, (j, p) in enumerate(zip(js["libraries"], py["libraries"])):
        assert j == p, f"library spec {i} differs between the twins"


# ---------- the bench's helper order (S5 review, 2026-10-13) ----------
# WHY: the VFX bench (scripts/vfx.html) ships the shared composer's GLSL only when it is byte-identical to its legacy
# writer's, and the two put helper chunks in order by different rules: legacy sorts by `order || 50` (so 0 reads as 50)
# and breaks ties by FILE name, then never reorders for a call; the composer reads 0 as 0, breaks ties by NAME and puts
# a callee first. The reviewer built one chunk set per rule and each one quietly pinned the bench to legacy. Rather
# than declare a second difference, lint refuses a bench helper of those shapes, so the legacy bytes stay the default
# and the two orders provably agree.

def _bench(tmp_path, files):
    d = tmp_path / "vfx-chunks"
    d.mkdir(parents=True, exist_ok=True)
    for fname, text in files.items():
        (d / fname).write_text(text, encoding="utf-8")
    return M.load_library([d])


def _bench_problems(lib):
    return [p for n in lib.names() for p in M.lint(lib.modules[n], library_module=False, library=lib)]


def test_lint_refuses_a_bench_helper_at_order_zero(tmp_path):
    lib = _bench(tmp_path, {"zero.glsl": mod("zero", "float zeroPad(float x){ return x + 0.125; }", order=0),
                            "fine.glsl": mod("fine", "float finePad(float x){ return x - 0.125; }", order=10)})
    problems = _bench_problems(lib)
    assert len(problems) == 1 and problems[0].startswith("zero: ") and "order 0" in problems[0], problems
    assert "50" in problems[0]                                  # says how the legacy writer reads it
    alone = M.parse_module(mod("zero", "float zeroPad(float x){ return x; }", order=0), "zero.glsl")
    assert any("order 0" in p for p in M.lint(alone, library_module=False))   # no library needed for this one


def test_lint_refuses_equal_order_bench_helpers_whose_file_and_name_orders_disagree(tmp_path):
    # 'glow-b.glsl' sorts before 'glow.glsl' ('-' is below '.'), while the name 'glow' sorts before 'glow-b'.
    lib = _bench(tmp_path, {"glow.glsl": mod("glow", "float glowA(float x){ return x * 0.75; }", order=30),
                            "glow-b.glsl": mod("glow-b", "float glowB(float x){ return x * 0.25; }", order=30)})
    problems = _bench_problems(lib)
    assert len(problems) == 1 and "glow" in problems[0] and "glow-b" in problems[0], problems
    assert "order 30" in problems[0] and "prefix" in problems[0]
    # the same pair at different orders, or with an '_' (which sorts after '.'), is fine
    assert _bench_problems(_bench(tmp_path / "x", {
        "glow.glsl": mod("glow", "float glowA(float x){ return x * 0.75; }", order=30),
        "glow-b.glsl": mod("glow-b", "float glowB(float x){ return x * 0.25; }", order=31)})) == []
    assert _bench_problems(_bench(tmp_path / "y", {
        "glow.glsl": mod("glow", "float glowA(float x){ return x * 0.75; }", order=30),
        "glow_b.glsl": mod("glow_b", "float glowB(float x){ return x * 0.25; }", order=30)})) == []


def test_lint_refuses_a_bench_helper_that_calls_a_helper_the_legacy_writer_emits_later(tmp_path):
    lib = _bench(tmp_path, {
        "base.glsl": mod("base", "float baseTone(float x){ return x * 0.5 + 0.125; }", order=20),
        "early.glsl": mod("early", "float earlyTone(float x){ return baseTone(x) * 0.25; }", order=10),
        "late.glsl": mod("late", "float lateTone(float x){ return baseTone(x) * 0.75; }", order=40),
        "tied.glsl": mod("tied", "float tiedTone(float x){ return baseTone(x) - 0.5; }", order=20)})
    problems = _bench_problems(lib)
    assert len(problems) == 1 and problems[0].startswith("early: ") and "baseTone()" in problems[0], problems
    # tied: order 20 like base, but 'base.glsl' comes first by file and by name, so legacy already emits base first
    assert not any(p.startswith(("late:", "tied:", "base:")) for p in problems)


def test_lint_refuses_a_bench_helper_that_needs_a_chunk_the_legacy_writer_never_emits(tmp_path):
    lib = _bench(tmp_path, {
        "consts.glsl": mod("consts", "const float BENCH_K = 0.375;", kind="const", order=5),
        "user.glsl": mod("user", "float userK(float x){ return x * BENCH_K; }", order=10)})
    problems = _bench_problems(lib)
    assert len(problems) == 1 and problems[0].startswith("user: ") and "consts" in problems[0], problems
    assert "helper" in problems[0]


def test_the_bench_order_rules_apply_to_bench_helpers_only(tmp_path):
    # a library module at order 0 is fine (the composer reads 0 as 0 everywhere a library module is composed), and a
    # bench snippet's order is read by neither writer
    lib = lib_from(tmp_path, {"lib0.glsl": mod("lib0", "float libZero(float x){ return x; }", order=0,
                                                license="Apache-2.0", credits=[])})
    assert M.lint(lib.get("lib0"), library_module=True, library=lib) == []
    snip = _bench(tmp_path, {"tint.glsl": mod("tint", "col *= 0.875;", kind="modifier", cat="colour", order=0)})
    assert _bench_problems(snip) == []


def test_the_shipped_bench_chunks_keep_the_two_orders_in_step():
    lib = M.load_library([CHUNKS])
    assert _bench_problems(lib) == []
    helpers = [n for n in lib.names() if lib.modules[n].kind == "helper"]
    legacy = sorted(helpers, key=lambda n: (lib.modules[n].header.get("order") or 50,
                                            Path(lib.modules[n].path).name))
    assert lib.resolve(helpers) == legacy        # what the rules guarantee, seen on the real chunks


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_javascript_twin_matches_on_every_round_two_fix(tmp_path):
    """Re-review round 2, through both twins: unknown providers refuse unresolved calls naming the files; a file that
    is not UTF-8 is decoded the same way and salvaged; a parameter or local never counts as a lost const; a broken
    snippet's const is not salvaged; the nesting limit is one count in both. Every record and message must match."""
    js, py, plan = _run_both_twins(tmp_path)
    four, five = (Path(plan["libraries"][i]["dirs"][0]) for i in (8, 11))
    lib4 = py["libraries"][8]
    assert {Path(p["path"]).relative_to(four).as_posix(): p["name"] for p in lib4["problems"]} == {
        "data/b-s.glsl": "s4", "data/f-snip.glsl": None, "data/h-broken.glsl": None, "data/j-nokind.glsl": None,
        "nest/deep.glsl": None, "utf/latin.glsl": None, "utf/z-bom2.glsl": None}
    assert lib4["unknown"] == []
    case4 = dict(zip([c["names"][0] for c in FOUR_CASES], lib4["cases"]))
    for ok in ("param-k", "local-k", "uses-t", "nest-edge", "typo4"):
        assert "ok" in case4[ok], (ok, case4[ok])
    assert "module 'uses-k' uses k (only the quarantined file" in case4["uses-k"]["error"]
    assert "calls Lost4()" in case4["user4"]["error"] and "uses LOSTC" in case4["user4"]["error"]
    assert "calls lost4()" in case4["user4"]["error"]
    assert "uses NK" in case4["uses-nk"]["error"]
    assert "calls deep4()" in case4["nest-user"]["error"] and "nest" in case4["nest-user"]["error"]
    assert "calls latF()" in case4["utf-user"]["error"]
    assert lib4["modules"]["param-k"]["declared"] == ["k"]
    assert "is not UTF-8 text (byte " in py["libraries"][9]["load_error"]
    assert py["libraries"][10]["load_error"].endswith("the //! header nests deeper than 32 levels")
    lib5 = py["libraries"][11]
    unknown = [str(five / "a-gone.glsl"), str(five / "b-code.glsl")]
    assert lib5["unknown"] == unknown
    case5 = dict(zip([c["op"] + ":" + c["names"][0] for c in FIVE_CASES], lib5["cases"]))
    assert case5["compose:user5"] == {"error": "cannot compose: part of it was quarantined at load (see "
                                      "library.problems): module 'user5' calls goneF(), which no loaded module "
                                      "provides (a quarantined file the library could not read in full may: "
                                      + ", ".join(unknown) + ")"}
    assert f"calls codeF() (only the quarantined file {unknown[1]} provides it)" in case5["compose:code-user5"]["error"]
    assert "ok" in case5["compose:hooked5"] and "ok" in case5["compose:plain5"]
    assert "needs 'gone5'" in case5["resolve:needs5"]["error"] and unknown[0] in case5["resolve:needs5"]["error"]
    assert "module 'snip5' calls goneF()" in case5["prelude:snip5"]["error"]
    assert py["libraries"][12] == {"load_error": f"{unknown[0]}: cannot be read (Permission denied)"}
    assert py["decode"][3] == ["\ufeff\ufeffok", None]
    assert py["decode"][7] == ["\ufffdA", "x.glsl: is not UTF-8 text (byte 0 cannot be decoded)"]
    assert js["decode"] == py["decode"]
    for i in range(8, 13):
        assert js["libraries"][i] == py["libraries"][i], f"library spec {i} differs between the twins"
