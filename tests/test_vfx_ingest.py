"""
Ingest: a pasted Shadertoy shader becomes one the bench can compile, and says what it changed.

The bar this file defends is mostly about RESTRAINT. The rewriter's job is to WRAP, not to edit --
it supplies a preamble, a set of #defines and a main(), and otherwise leaves a stranger's code
byte-for-byte alone. That matters because the obvious implementation (find/replace iTime -> u_time)
corrupts the exact things you cannot afford to corrupt: a comment mentioning iTime, an identifier
like iTimeout, a string. The GLSL preprocessor already knows where a token ends; the rewriter does
not have to learn.

The other bar is honesty about what will not work. iChannel textures, sound shaders and multi-pass
buffers have no surface here, and emitting a shader that references them yields a compile error
forty lines from the real problem.

Pure text: no server, no GPU, no browser.

Run: py -m pytest tests/test_vfx_ingest.py -q
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import vfx_ingest as V


SHADERTOY = """\
// A tunnel. iTime drives the march.
#define PI 3.14159

float box(vec3 p){ return length(p) - 1.0; }

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float t = iTime * 0.5;
    fragColor = vec4(uv, sin(t), 1.0);
}
"""


def test_a_shadertoy_shader_becomes_a_program():
    r = V.rewrite(SHADERTOY, name="tunnel")
    assert r["ok"] and r["kind"] == "shadertoy"
    out = r["src"]
    # #version must be the FIRST line of a GLSL program -- not merely present somewhere.
    assert out.splitlines()[0] == "#version 300 es"
    assert "precision highp float;" in out
    assert "out vec4 outColor;" in out
    assert "uniform vec2  u_res;" in out and "uniform float u_time;" in out
    assert "void main(){ mainImage(outColor, gl_FragCoord.xy); }" in out


def test_it_wraps_rather_than_edits():
    """The whole design claim in one assertion: the stranger's code is untouched."""
    r = V.rewrite(SHADERTOY, name="tunnel")
    assert SHADERTOY.strip() in r["src"], "the body was modified; a #define must do this work"


def test_an_identifier_that_merely_starts_with_itime_is_not_mangled():
    src = SHADERTOY.replace("float t = iTime * 0.5;",
                            "float iTimeout = 3.0; float t = iTime * 0.5 + iTimeout;")
    r = V.rewrite(src)
    assert r["ok"]
    assert "float iTimeout = 3.0;" in r["src"], "find/replace would have corrupted this"


def test_iresolution_stays_a_vec3_so_the_swizzles_survive():
    """Shadertoy's iResolution is a vec3. Porting it as u_res (a vec2) breaks .xy and .z, which is
    most real shaders -- and breaks them at the compile step, far from the cause."""
    r = V.rewrite(SHADERTOY)
    assert "#define iResolution vec3(u_res, 1.0)" in r["src"]


def test_it_reports_which_shims_the_shader_actually_used():
    r = V.rewrite(SHADERTOY)
    note = " ".join(r["notes"])
    assert "iTime" in note and "iResolution" in note
    assert "iMouse" not in note, "reporting shims the shader never touched is noise"


def test_a_second_version_line_is_removed():
    r = V.rewrite("#version 300 es\n" + SHADERTOY)
    assert r["ok"]
    assert r["src"].count("#version") == 1, "two #version lines is a hard compile error"
    assert any("#version" in n for n in r["notes"])


def test_a_duplicate_out_declaration_is_removed():
    r = V.rewrite(SHADERTOY.replace("#define PI 3.14159", "out vec4 fragColor;"))
    assert r["ok"]
    # Precisely: the DECLARATION goes, and the identically-spelled PARAMETER in mainImage's
    # signature stays. Counting the substring conflates the two and fails on a correct rewrite.
    assert not re.search(r"^\s*out\s+vec4\s+fragColor\s*;", r["src"], re.M), \
        "two fragment outputs is a link error"
    assert r["src"].count("out vec4 outColor;") == 1
    assert "out vec4 fragColor, in vec2 fragCoord" in r["src"], "the signature must survive"
    assert any("out declaration" in n for n in r["notes"])


def test_texture_channels_are_warned_about_not_silently_broken():
    src = SHADERTOY.replace("fragColor = vec4(uv, sin(t), 1.0);",
                            "fragColor = texture(iChannel0, uv);")
    r = V.rewrite(src)
    assert r["ok"], "still store it -- the user may want to strip the texture read by hand"
    assert any("iChannel" in w for w in r["warnings"])


def test_a_sound_shader_is_refused_by_name():
    r = V.rewrite("vec2 mainSound( in int samp, float time ){ return vec2(sin(time)); }")
    assert r["ok"] is False and "SOUND" in r["error"]


def test_a_bench_shader_passes_through_untouched():
    """Ingest must be safe to point at anything, including a .frag this bench wrote. Wrapping one
    would add a second main() and fail."""
    bench = ("#version 300 es\nprecision highp float;\nout vec4 outColor;\n"
             "uniform vec2 u_res;\nuniform float u_time;\n"
             "void main(){ outColor = vec4(u_time); }\n")
    r = V.rewrite(bench)
    assert r["ok"] and r["kind"] == "passthrough"
    assert r["src"] == bench, "passthrough must mean passthrough"
    assert r["src"].count("void main") == 1


def test_empty_and_nonsense_are_refused_with_a_reason():
    assert V.rewrite("")["ok"] is False
    assert V.rewrite("   \n  ")["ok"] is False
    r = V.rewrite("this is not a shader at all")
    assert r["ok"] is False and "mainImage" in r["error"]


def test_whitespace_variants_of_the_signature_are_recognised():
    for sig in ["void mainImage(out vec4 c, in vec2 f)",
                "void  mainImage ( out vec4 c , in vec2 f )",
                "void mainImage(\n    out vec4 c,\n    in vec2 f)"]:
        src = sig + "{ c = vec4(1.0); }"
        assert V.rewrite(src)["ok"] is True, "rejected a legal signature: " + sig


def test_summary_is_one_short_line_for_the_feed():
    assert "Shadertoy" in V.summary(V.rewrite(SHADERTOY))
    warned = V.rewrite(SHADERTOY.replace("sin(t)", "texture(iChannel0, uv).r"))
    assert "warning" in V.summary(warned)
    assert V.summary({"ok": False, "error": "nope"}).startswith("ingest failed")
