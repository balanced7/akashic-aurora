"""Pin the First Light shader to its contract (FIRST-LIGHT-SPEC.md -> "Uniforms").

Written by Navi (kimi) to give the "it compiles" claim a mechanical receipt, not
just a careful read. Two invariants that must survive any edit to the effect:

  1. #version 300 es is the absolute FIRST line. A standalone GLSL ES .frag that
     is compiled directly (not concatenated as a chunk) is rejected by ANGLE on
     D3D11 if anything precedes #version ("#version directive must occur on the
     first line of the shader"). This is the bug the live run caught, now pinned
     so it cannot regress silently.

  2. Every uniform in the spec's Uniforms list is declared. The page drives the
     shader by name; a renamed or dropped uniform breaks the live mapping before
     anyone eyeballs a pixel. Unused uniforms (u_bass) are legal and optimised
     out, so "declared" is the bar, not "used".

Contract source: arsenal/FIRST-LIGHT-SPEC.md -> "Uniforms (the contract with the shader)".
The uniform list is hard-coded here (blind pin): the page and the shader both
answer to the spec, so if the spec changes this test is the thing that breaks.
"""

import re
from pathlib import Path

import pytest

SHADER = Path(__file__).resolve().parent.parent / "arsenal" / "web" / "shaders" / "first-light.frag"

# The spec's Uniforms list, in spec order. Names only; types are asserted loosely
# below where cheap, but the contract the page actually reads is the NAME.
SPEC_UNIFORMS = [
    ("u_video",      "sampler2D"),
    ("u_res",        "vec2"),
    ("u_video_res",  "vec2"),
    ("u_time",       "float"),
    ("u_pulse",      "float"),
    ("u_hue",        "float"),
    ("u_intensity",  "float"),
    ("u_bass",       "float"),
    ("u_mid",        "float"),
    ("u_high",       "float"),
    ("u_flux",       "float"),
]


def _source() -> str:
    return SHADER.read_text(encoding="utf-8")


def test_shader_exists():
    assert SHADER.is_file(), f"missing shader: {SHADER}"


def test_version_is_the_absolute_first_line():
    lines = _source().splitlines()
    # Cap the leading-blank-line hazard too: line 1 must be exactly the directive,
    # not even leading whitespace (ANGLE is strict about position, and a trailing
    # comment is fine but a leading one is not).
    assert lines[0] == "#version 300 es", (
        f"line 1 must be exactly '#version 300 es'; got {lines[0]!r}"
    )


def test_every_spec_uniform_is_declared():
    src = _source()
    missing = [name for name, _ in SPEC_UNIFORMS if name not in src]
    assert not missing, f"spec uniforms not declared in the shader: {missing}"


def test_every_declared_uniform_matches_the_contract_type():
    # Loose type check: each spec uniform must appear with a 'uniform <type> <name>'
    # declaration (allowing a shared declaration like 'uniform float u_bass, u_mid, ...').
    src = _source()
    for name, glsl_type in SPEC_UNIFORMS:
        # A shared declaration declares several names after one type. Check that the
        # name is announced as a uniform of the right type somewhere on a line whose
        # type matches (allow the multi-name 'uniform float a, b, c' form).
        declared = re.search(
            rf"^\s*uniform\s+{re.escape(glsl_type)}\s+[^;]*\b{re.escape(name)}\b",
            src,
            re.MULTILINE,
        )
        assert declared, (
            f"{name} must be declared as 'uniform {glsl_type} {name}' "
            f"(or in a shared 'uniform {glsl_type} ...' line)"
        )


def test_no_loop_bounds_to_inject():
    # House floor: loop bounds are constant, never a uniform or a runtime value.
    # This shader currently has no loops at all; assert that if a loop ever appears,
    # its bound is a literal, not a uniform name.
    src = _source()
    for name, _ in SPEC_UNIFORMS:
        m = re.search(
            rf"for\s*\([^;]*;\s*[^;]*\b{re.escape(name)}\b\s*[;)]",
            src,
        )
        assert not m, f"loop bound uses uniform {name!r}; loop bounds must be constant"


@pytest.mark.parametrize("name,_type", SPEC_UNIFORMS)
def test_no_highp_violation_in_shared_declarations(name, _type):
    # The floor says highp always. This is a structural pin, not a compiler: it
    # asserts the file opens with the house setup and never lowers precision.
    src = _source()
    assert "precision highp float;" in src, "precision highp float; must be present"
    # No mediump/lowp anywhere (the house rule; our hashes band under mediump).
    assert "mediump" not in src, "mediump found: the house floor forbids it"
    assert "lowp" not in src, "lowp found: the house floor forbids it"
