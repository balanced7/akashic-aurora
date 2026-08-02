#!/usr/bin/env python3
"""Turn a pasted Shadertoy shader into one the bench can compile, and SAY WHAT IT CHANGED.

WHY THIS IS A MODULE AND NOT A FUNCTION IN THE SERVER. Two callers want it -- the CLI ingest verb
and (next) a paste box in the page -- and the bench's standing rule is one implementation behind
both, so a pasted shader cannot compile differently depending on which door it came through. It
also has no dependencies, which means its pins run in milliseconds without a server, a GPU or a
browser: the translation is pure text, and pure text is the part worth testing exhaustively.

THE TRANSLATION. Shadertoy hands you a function; the bench wants a program.

    Shadertoy                          the bench
    ---------                          ---------
    void mainImage(out vec4 fragColor, #version 300 es / precision highp float
                   in vec2 fragCoord)  out vec4 outColor; + void main(){...}
    iTime                              u_time
    iResolution (vec3!)                vec3(u_res, 1.0)
    fragCoord                          gl_FragCoord.xy  (passed in by the wrapper)

Most of that is #define, deliberately. A textual substitution over the source would corrupt the
one thing you cannot afford to corrupt -- a string, a comment mentioning iTime, an identifier like
`iTimeout` -- whereas a #define is applied by the GLSL preprocessor, which already knows what a
token boundary is. The rewriter's job is to WRAP, not to edit.

WHAT IT REFUSES TO PRETEND. iChannel textures, sound shaders and multi-pass buffers are not wired
into this bench. Emitting a shader that references them produces a compile error forty lines from
the real problem; saying "this one needs a texture you do not have" is one sentence and correct.
Every ingest returns `notes` (what was done) and `warnings` (what will not work), because a
translation you cannot inspect is a translation you have to debug by bisecting a stranger's code.
"""
from __future__ import annotations

import re

# The bench's contract, and only the parts every shader needs. A sketch that does not declare the
# avatar's other uniforms is fine: getUniformLocation returns null for an undeclared uniform and
# the renderer already treats that as harmless, so a Shadertoy port does not have to pretend to be
# an avatar style to run next to one.
PREAMBLE = """#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;
"""

# iResolution is a vec3 on Shadertoy (z is the pixel aspect, effectively always 1.0). Defining it
# as a vec3 rather than as u_res keeps `.xy`, `.x` and the occasional `.z` all working -- porting
# it as a vec2 breaks exactly the shaders that use the swizzle, which is most of them.
SHIMS = [
    ("iTime", "(u_time)"),
    ("iResolution", "vec3(u_res, 1.0)"),
    ("iMouse", "vec4(0.0)"),
    ("iTimeDelta", "(1.0 / 60.0)"),
    ("iFrameRate", "(60.0)"),
    ("iFrame", "(int(u_time * 60.0))"),
    ("iSampleRate", "(44100.0)"),
    ("iDate", "vec4(2026.0, 1.0, 1.0, u_time)"),
]

_MAIN_IMAGE = re.compile(r"\bvoid\s+mainImage\s*\(", re.S)
_MAIN_SOUND = re.compile(r"\bvec2\s+mainSound\s*\(")
_MAIN_VR = re.compile(r"\bvoid\s+mainVR\s*\(")
_CHANNEL = re.compile(r"\biChannel\d\b")
_VERSION_LINE = re.compile(r"^\s*#version\b.*$", re.M)
_OUT_DECL = re.compile(r"^\s*out\s+vec4\s+(\w+)\s*;\s*$", re.M)
_BENCH_MAIN = re.compile(r"\bvoid\s+main\s*\(\s*(void)?\s*\)")


def rewrite(src, name=""):
    """Wrap Shadertoy source for the bench.

    Returns {ok, src, notes[], warnings[], kind}. `kind` is 'shadertoy' when a mainImage was
    wrapped, 'passthrough' when the source was already a complete bench shader -- ingest has to be
    safe to point at anything, including a .frag this bench wrote, or it becomes a verb you have to
    think before using.
    """
    raw = str(src or "")
    if not raw.strip():
        return {"ok": False, "error": "empty source", "notes": [], "warnings": []}

    notes, warnings = [], []

    # Refuse the shader TYPES this bench has no surface for, by name, before touching the text.
    if _MAIN_SOUND.search(raw):
        return {"ok": False, "error": "this is a Shadertoy SOUND shader (mainSound) -- the bench "
                                      "renders images, so there is nothing here to draw",
                "notes": [], "warnings": []}

    body = raw
    # A pasted shader sometimes arrives with a #version already on it (copied from a port rather
    # than from Shadertoy). #version must be the first line of the program, so a second one is a
    # hard compile error -- and ours has to win, because the rest of the preamble assumes 300 es.
    if _VERSION_LINE.search(body):
        body = _VERSION_LINE.sub("", body, count=1)
        notes.append("removed a #version line (the bench supplies #version 300 es)")

    # Two `out vec4` declarations is a link error. Ported shaders often carry one; strip it and let
    # the wrapper's outColor be the single output.
    out_names = _OUT_DECL.findall(body)
    if out_names:
        body = _OUT_DECL.sub("", body)
        notes.append("removed a duplicate out declaration (%s); the bench writes outColor"
                     % ", ".join(out_names))

    if _CHANNEL.search(body):
        warnings.append("uses iChannel textures, which this bench does not wire up -- it will not "
                        "compile until those reads are removed or replaced")
    if _MAIN_VR.search(body):
        warnings.append("declares mainVR; it is ignored, the flat mainImage is what renders")

    has_main_image = bool(_MAIN_IMAGE.search(body))
    # Already a bench shader? Then the honest move is to leave it alone. Wrapping it would add a
    # second main() and fail, and 'ingest refused my own file' is a bad first experience with a
    # verb whose whole purpose is to accept whatever you paste.
    if not has_main_image:
        if _BENCH_MAIN.search(body) and "outColor" in body:
            return {"ok": True, "src": raw, "kind": "passthrough",
                    "notes": ["already a complete bench shader -- stored unchanged"],
                    "warnings": warnings}
        return {"ok": False, "error": "no mainImage(out vec4, in vec2) and no bench main() -- this "
                                      "does not look like a fragment shader",
                "notes": notes, "warnings": warnings}

    shim = "\n".join("#define %s %s" % (k, v) for k, v in SHIMS)
    used = [k for k, _ in SHIMS if re.search(r"\b%s\b" % k, body)]
    if used:
        notes.append("mapped " + ", ".join(used) + " onto the bench's uniforms")
    notes.append("wrapped mainImage in a main() that writes outColor")

    tag = ("// ingested: %s\n" % name) if name else ""
    out = (PREAMBLE + "\n" + tag + shim + "\n\n" + body.strip() +
           "\n\nvoid main(){ mainImage(outColor, gl_FragCoord.xy); }\n")
    return {"ok": True, "src": out, "kind": "shadertoy", "notes": notes, "warnings": warnings}


def summary(result):
    """One line for the feed. The reason a render exists travels with it, so it has to be short
    enough to sit above a picture without becoming the picture."""
    if not result.get("ok"):
        return "ingest failed: " + str(result.get("error", ""))
    bits = []
    if result.get("kind") == "passthrough":
        bits.append("stored unchanged")
    else:
        bits.append("translated from Shadertoy")
    if result.get("warnings"):
        bits.append("%d warning(s)" % len(result["warnings"]))
    return "; ".join(bits)
