"""Pins for `py -m arsenal shader explain` (arsenal/shaders/explain.py): one shader's FINDING LEDGER.

WHY THESE PINS. Daniel, 2026-10-13: "I want us to know how to reverse engineer anything." The discipline the house took
from morluto/rea is that every conclusion says HOW it is known: seen in the code, seen in a render, measured, inferred,
or not known at all; that it points at the evidence that earned it; that it says where the search stopped; and that a
repeat with nothing changed returns the earlier answer instead of doing the work twice. The promises worth a test each:

  * every claim carries one of five labels, at least one evidence id, its search boundary and a confidence from one
    fixed scale (high / moderate / low); the dissector's own number travels apart, as `score`;
  * only a raw fact is an observation: a pass or input the configuration declares, a uniform or declared channel read
    on the line cited, a function present at a line, a receipt's report, a measurement. Every reading is `inferred`:
    a technique the dissector recognises by the shape of its math, a function name alone (never counted as a
    technique), the static cost, a prediction from the media folder, the study note and its corroboration section;
  * a read is a token of LIVE code: a line in a function no entry point reaches, in an #if branch the preprocessor
    drops, a #define that only renames the channel (or renames a renaming), or a function's or macro's own parameter
    named like an alias or a uniform is never an observed read (the first live read is cited, or the declaration with
    "no read found"); a macro Common defines is live code of the pass that uses it, an alias counts only where its own
    pass (or Common) defines it, and a #define continued over several lines is cited whole;
  * a function handed to a macro that calls it (`#define APPLY(f, x) f(x)` ... `APPLY(bend, x)`) is called by the code
    that hands it over, whatever the parameter is named, so it is never observed unreached; handed to a parameter the
    body never calls, it is not called;
  * a pass in which the reader finds no entry point is said as an unknown, and nothing about it is observed or live,
    its own helpers included: no dead list, no "no read found" over code the reader never followed, no cost estimate
    (its cost is unknown), and a channel row there cites the configuration, not the dissector's placeholder line;
  * the cost question names only what the claims hold (a static estimate, SwiftShader timing), and is unresolved when
    neither exists;
  * "what is it made of" is answered only by a technique recognised from the shape of the math; reads, declarations
    and function names alone leave it partial;
  * a code evidence id names the shader, the SHA-256 (first 8 hex) of the pass source, the pass and a line range, and the
    line it names is really where the technique is; a channel declared but never read cites the configuration, never
    line 1;
  * a render claim names the receipt by its own sha8 and gives the receipt's path; timing is labelled measured and says
    SwiftShader, because CPU timing never stands for GPU timing;
  * a study-note claim is always `inferred` and its id carries the note's sha8, so it goes stale when the note changes;
  * the unknowns are said out loud: inputs drawn by stand-ins, silence fed to an audio input, a Sound pass never run,
    the times never rendered, and the detector groups that found nothing ("not detected by dissect v1", never "absent");
  * the checklist never says "answered" while the runtime reports an input or pass it could not draw;
  * the routing rule for the artifact is in the ledger (a feedback buffer walks from a reset, never jumps);
  * a repeat with unchanged inputs returns the cached ledger and says so; a change to ANY input it was made from (a pass,
    shader.json, meta.json, a media file (each of a cubemap's six faces), a receipt, the study note, its corroboration
    section, the dissector's version or code, this verb's code, the floor) re-analyses;
  * the ledger is private: it is written under state/ or refused.

Every shader, receipt and note here is synthetic and written for this file in our own words; the real corpus is never
read by these tests.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from arsenal.shaders import cli
from arsenal.shaders import corpus as C
from arsenal.shaders import dissect as D
from arsenal.shaders import explain as X

LABELS = {"observed-in-code", "observed-in-render", "measured", "inferred", "unknown"}
OUT_A, OUT_IMG = "4dXGR8", "4dfGRr"          # the ids Shadertoy gives Buffer A's and Image's outputs

# ------------------------------------------------------------------------------------------------ the fixture
# A single-pass scene: a sphere traced through a distance function, a time-driven camera, a gamma encode. The line
# numbers matter to one test: `length(spot) - radius` is on line 2.
LANTERN = """// a small lantern, written for the explain pins
float bead(vec3 spot, float radius) { return length(spot) - radius; }
float field(vec3 spot) { return bead(spot - vec3(0.0, 0.1, 0.0), 0.7); }
float walk(vec3 start, vec3 heading) {
    float went = 0.0;
    for (int stride = 0; stride < 48; ++stride) {
        float clearance = field(start + went * heading);
        if (clearance < 0.002) break;
        went += clearance;
    }
    return went;
}
float spare(float k) { return k * 3.0; }
void mainImage(out vec4 glow, in vec2 at) {
    vec2 lens = (at + at - iResolution.xy) / iResolution.y;
    vec3 viewer = vec3(0.0, 0.2, -2.4 + 0.3 * sin(iTime));
    float far = walk(viewer, normalize(vec3(lens, 1.4)));
    vec3 tone = vec3(exp(-0.4 * far));
    glow = vec4(pow(tone, vec3(0.4545)), 1.0);
}
"""

# A two-buffer piece: Buffer A keeps its own last frame (feedback) and samples a texture; Image reads Buffer A and a
# music stream; a Sound pass makes a tone. Common holds a helper.
COMMON = "float ease(float k) { return k * k * (3.0 - 2.0 * k); }\n"
TRAIL = """void mainImage(out vec4 keep, in vec2 px) {
    vec4 before = texelFetch(iChannel0, ivec2(px), 0);
    vec4 grain = texture(iChannel1, px / iResolution.xy);
    keep = 0.97 * before + 0.03 * grain * ease(0.5);
}
"""
SHOW = """void mainImage(out vec4 seen, in vec2 px) {
    vec2 uv = px / iResolution.xy;
    float level = texture(iChannel1, vec2(uv.x, 0.25)).r;
    seen = texture(iChannel0, uv) + vec4(vec3(level), 0.0);
}
"""
TONE = """vec2 mainSound(int samp, float time) {
    float hum = sin(6.2831 * 196.0 * time) * exp(-1.5 * time);
    return vec2(hum, hum * 0.9);
}
"""
GRAIN_SRC = "/media/a/0123456789abcdef0123456789abcdef.png"
STREAM_SRC = "/media/a/fedcba9876543210fedcba9876543210.mp3"


def _shader(sid: str, name: str, passes: list) -> dict:
    return {"ver": "0.1", "info": {"id": sid, "name": name, "username": "a.stranger", "date": "1700000000",
                                   "likes": 1, "viewed": 2, "tags": ["test"], "description": ""},
            "renderpass": passes}


def _rp(name, typ, code, inputs=(), outputs=()):
    return {"name": name, "type": typ, "code": code, "inputs": list(inputs), "outputs": list(outputs)}


def _inp(channel, typ, ident=None, src=None):
    return {"channel": channel, "type": typ, "id": ident, "filepath": src, "sampler": {}, "published": 1}


SINGLE = _shader("xpAAA1", "Paper Lantern", [_rp("Image", "image", LANTERN, [], [{"id": OUT_IMG, "channel": 0}])])
MULTI = _shader("xpBBB2", "Echo Pool", [
    _rp("Common", "common", COMMON),
    _rp("Buffer A", "buffer", TRAIL, [_inp(0, "buffer", OUT_A), _inp(1, "texture", "t1", GRAIN_SRC)],
        [{"id": OUT_A, "channel": 0}]),
    _rp("Image", "image", SHOW, [_inp(0, "buffer", OUT_A), _inp(1, "music", "m1", STREAM_SRC)],
        [{"id": OUT_IMG, "channel": 0}]),
    _rp("Sound", "sound", TONE),
])

NOTE = """# Study note: xpAAA1 "Paper Lantern"

## 1. What you see (inferred from the code, not rendered)

A lit bead.

## 4. Techniques

### 4.1 A bead traced by its distance

words of our own

### 4.2 Gamma on the way out

```
### not a heading: inside a fence
```

## 5. Craft secrets

More words.

## Corroboration (2026-10-13)

**Confirmed by render (2)**
- The bead sits a little above the middle.
- The edge fades into the dark.

**Contradicted (1)**
- The light is cool, not warm.
"""

# A function named like a box distance whose body is not one: the name alone must never pass for a detection.
NAMED_ONLY = """float sdBox(vec3 p, vec3 b) { return p.x * 0.0 + b.y; }
void mainImage(out vec4 tint, in vec2 at) { tint = vec4(sdBox(vec3(at, 0.0), vec3(1.0))); }
"""
# A buffer that declares its own output as an input and never reads it; and two buffers that read each other.
UNREAD = """void mainImage(out vec4 c, in vec2 p) {
    c = vec4(p / iResolution.xy, 0.5, 1.0);
}
"""
PASS_ON = """void mainImage(out vec4 c, in vec2 p) {
    c = texture(iChannel0, p / iResolution.xy);
}
"""
OUT_B = "XsXGR8"                              # the id Shadertoy gives Buffer B's output
# The box-by-name scene plus a clock: a read and a name, and no shape the dissector knows.
NAMED_CLOCK = """float sdBox(vec3 p, vec3 b) { return p.x * 0.0 + b.y; }
void mainImage(out vec4 tint, in vec2 at) { tint = vec4(sdBox(vec3(at, 0.0), vec3(1.0)) * sin(iTime)); }
"""
CLOCK_ONLY = """void mainImage(out vec4 o, in vec2 u) { o = vec4(0.5 + 0.5 * sin(iTime)); }
"""
# Buffer A's only read of its own last frame sits in a function nothing calls; then the same with a live read too.
DEAD_READ = """vec4 unused(vec2 q) { return texture(iChannel0, q); }
void mainImage(out vec4 c, in vec2 p) {
    c = vec4(p / iResolution.xy, 0.5, 1.0);
}
"""
DEAD_AND_LIVE = """vec4 unused(vec2 q) { return texture(iChannel0, q); }
void mainImage(out vec4 c, in vec2 p) {
    c = 0.9 * texture(iChannel0, p / iResolution.xy);
}
"""
# The read sits in an #if branch the preprocessor drops (line 3).
INACTIVE_READ = """void mainImage(out vec4 c, in vec2 p) {
#if 0
    c = texture(iChannel0, p / iResolution.xy);
#else
    c = vec4(p / iResolution.xy, 0.5, 1.0);
#endif
}
"""
# A keyboard channel renamed by a #define on line 1 and read on line 3.
KEYS = """#define keyTex iChannel1
void mainImage(out vec4 c, in vec2 p) {
    float down = texelFetch(keyTex, ivec2(65, 0), 0).r;
    c = vec4(down, p / iResolution.xy, 1.0);
}
"""
# Buffer A reads its own last frame only through a macro Common defines on line 1 (T), used in mainImage.
COMMON_READ = """#define T texture(iChannel0, px / iResolution.xy)
float settle(float k) { return k * 0.98; }
"""
BUF_VIA_COMMON = """void mainImage(out vec4 keep, in vec2 px) {
    keep = settle(1.0) * T;
}
"""
# Buffer A renames the clock (`#define T iTime`) and never uses it; Image has a plain variable T on line 3 and reads the
# clock itself on line 4. Buffer A's alias is not Image's name.
BUF_ALIAS_ONLY = """#define T iTime
void mainImage(out vec4 c, in vec2 p) {
    c = vec4(p / iResolution.xy, 0.5, 1.0);
}
"""
IMG_PLAIN_T = """void mainImage(out vec4 o, in vec2 u) {
    vec2 uv = u / iResolution.xy;
    float T = 0.5;
    o = vec4(uv, T * sin(iTime), 1.0);
}
"""
# Common's macro names a channel alias each pass defines for itself (SELF_CH): expanded in Buffer A it reads Buffer A's
# iChannel0, its own last frame; Image's SELF_CH is another channel and must not count for Buffer A.
COMMON_ALIAS_MACRO = """#define FETCH_OWN(q) texelFetch(SELF_CH, ivec2(q), 0)
"""
BUF_DEFINES_ALIAS = """#define SELF_CH iChannel0
void mainImage(out vec4 c, in vec2 p) {
    c = 0.95 * FETCH_OWN(p);
}
"""
IMG_DEFINES_ALIAS = """#define SELF_CH iChannel1
void mainImage(out vec4 c, in vec2 p) {
    c = texture(iChannel0, p / iResolution.xy);
}
"""
# Common's macro is written over two lines; the read of iChannel0 is on the second (line 2).
COMMON_LONG_MACRO = """#define PREV(q) \\
    texelFetch(iChannel0, ivec2(q), 0)
"""
BUF_USES_LONG = """void mainImage(out vec4 c, in vec2 p) {
    c = 0.95 * PREV(p);
}
"""
# Every pass is one object-like macro Common defines, so the reader finds no entry point in any pass.
COMMON_BUILDS = """float lift(float k) { return k * 0.5 + 0.25; }
float spare(float k) { return k * 3.0; }
#define BUFFERA void mainImage(out vec4 c, in vec2 p) { c = 0.9 * texture(iChannel0, p / iResolution.xy); }
#define IMAGE void mainImage(out vec4 o, in vec2 u) { o = texture(iChannel0, u / iResolution.xy) * lift(sin(iTime)); }
"""
# Image renames the clock (`#define t iTime`, line 1) and only calls WAVE with a constant. WAVE's PARAMETER is also
# called t: inside WAVE, t is whatever the caller passes, never the clock, so no clock is read anywhere. WAVE sits in
# Common (line 1) or in Image's own file (line 2). The control, WAVE_K, names the alias in its body and does read it.
WAVE_T = "#define WAVE(t) (0.5 + 0.5 * sin(t))\n"
WAVE_K = "#define WAVE(k) (0.5 + 0.5 * sin(k * t))\n"
IMG_RENAMES_T = """#define t iTime
void mainImage(out vec4 o, in vec2 u) {
    o = vec4(WAVE(2.0));
}
"""
# Common renames the clock and defines WAVE(t); Image calls WAVE with a constant and reads the clock itself through t on
# line 3, so the macro t IS reached, and WAVE's body (common.glsl line 2) holds a t that is still only its parameter.
COMMON_T_AND_WAVE = "#define t iTime\n" + WAVE_T
IMG_READS_T = """void mainImage(out vec4 o, in vec2 u) {
    o = vec4(WAVE(2.0));
    o.a = fract(t);
}
"""
# Image's t is an expression, not an alias (`#define t (iTime * 2.0)`), and WAVE's parameter is also called t: nothing
# ever expands the macro t, so no clock is read (probe p1f). WAVE sits in Common or in Image's own file.
IMG_EXPR_T = """#define t (iTime * 2.0)
void mainImage(out vec4 o, in vec2 u) {
    o = vec4(WAVE(2.0));
}
"""
# A FUNCTION parameter named like the clock's alias (t) or like the clock itself (iTime) shadows it; the variants with a
# real read put it on line 5 (probe p1g).
FN_PARAM_T = """#define t iTime
float swell(float t) { return 0.25 + 0.75 * cos(t); }
void mainImage(out vec4 hue, in vec2 spot) {
    hue = vec4(swell(0.5));
}
"""
FN_PARAM_T_READ = FN_PARAM_T.replace("    hue = vec4(swell(0.5));\n", "    hue = vec4(swell(0.5));\n    hue.b = fract(t);\n")
FN_PARAM_ITIME = FN_PARAM_T.replace("#define t iTime\n", "// no alias here\n").replace("float t", "float iTime") \
    .replace("cos(t)", "cos(iTime)")
# Two renamings in a row: KEYS renames Pressed, Pressed renames iChannel2 (or NOW2 renames Now, Now renames the clock);
# both #defines only rename, and the read is on line 4 (probe p4c).
CHAIN_KEYS = """#define Pressed iChannel2
#define KEYS Pressed
void mainImage(out vec4 o, in vec2 u) {
    o = vec4(texelFetch(KEYS, ivec2(39, 0), 0).x);
}
"""
CHAIN_CLOCK = """#define Now iTime
#define NOW2 Now
void mainImage(out vec4 o, in vec2 u) {
    o = vec4(fract(NOW2));
}
"""
# Image's entry is built by Common's PAINT (the reader cannot see it), and Image has helpers of its own: one reads the
# audio input (line 2), one runs a literal loop (probes p3e and p2b).
COMMON_PAINTS = "#define PAINT void mainImage(out vec4 o, in vec2 u) { o = vec4(u.x / iResolution.x); }\n"
IMG_HELPERS = """float loudness() {
    return texture(iChannel1, vec2(0.05, 0.25)).x;
}
float ridge(float k) {
    float acc = 1.5;
    for (int lap = 2; lap < 11; lap += 1) { acc -= cos(k + 0.3 * float(lap)) / 4.0; }
    return acc;
}
PAINT
"""
CUBE_SRC = "/media/a/0a1b2c3d4e5f60718293a4b5c6d7e8f9.jpg"
SKY = """void mainImage(out vec4 c, in vec2 p) {
    c = texture(iChannel0, vec3(p / iResolution.xy - 0.5, 1.0));
}
"""


def _cite_at(monkeypatch, tag: str, line: int) -> None:
    """Make the dissector cite `tag` at `line` (above the floor): the latent cases the ledger must not trust."""
    real = D.dissect_view

    def wrapped(view, min_conf=D.MIN_CONF):
        rep = real(view, min_conf)
        for t in rep["techniques"]:
            if t["tag"] == tag:
                t["conf"] = 0.95
                for e in t["evidence"]:
                    e["line"], e["conf"] = line, 0.95
        return rep
    monkeypatch.setattr(D, "dissect_view", wrapped)


def _png(path: Path) -> Path:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (8, 4), (20, 30, 40))
    im.putpixel((1, 1), (200, 10, 10))
    im.save(path)
    return path


def _receipt(d: Path, name: str, api: str, ts, *, history=False, substituted=(), unsupported=(), ok=True,
             warm_ms=12.5, flat=False) -> Path:
    frames = []
    for t in ts:
        frames.append({"t": float(t), "png": str(_png(d / f"{name}-t{t:.2f}.png")), "ms": 40, "bytes": 99,
                       "frame": int(round(t * 60)), "frames_walked": int(round(t * 60)) + 1 if history else 1,
                       "reset": bool(history), "jumped": not history, "mean_luma": 31.5 + t, "flat": bool(flat)})
    rec = {"api": api, "id": d.name, "name": "x", "author": "a.stranger", "license": "CC0", "ok": ok,
           "status": "done" if ok else "error", "request": {"t": [float(t) for t in ts], "w": 320, "h": 180, "fps": 60},
           "renderer": "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)",
           "software_renderer": True,
           "compile": {"ok": ok, "drawable": ok, "warnings": [],
                       "passes": [{"name": "Image", "type": "image", "ok": ok, "parity": "full",
                                   "firstError": None if ok else "ERROR: 0:3: something", "mappedLog": ""}]},
           "frames": frames if ok else [], "substituted": list(substituted), "unsupported": list(unsupported),
           "errors": [], "first_error": None if ok else "Image: ERROR: 0:3: something", "history": history,
           "timings": {"warm_ms": warm_ms, "frame_ms": [40 for _ in ts]}}
    out = d / f"{name}.json"
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return out


@pytest.fixture()
def world(tmp_path, monkeypatch):
    state = tmp_path / "state"
    corpus = state / "arsenal" / "shaders" / "corpus"
    for s in (SINGLE, MULTI):
        C.save_shader(s, corpus)
    renders = state / "arsenal" / "shaders" / "renders"
    study = state / "arsenal" / "shaders" / "study"
    ledger = state / "arsenal" / "shaders" / "ledger"
    a, b = renders / "xpAAA1", renders / "xpBBB2"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    _receipt(a, "receipt", "arsenal.shader-render/v1", (1.0, 4.0))
    _receipt(a, "filmstrip", "arsenal.shader-filmstrip/v1", [i * 8.0 / 7 for i in range(8)])
    _receipt(b, "receipt", "arsenal.shader-render/v1", (1.0, 4.0), history=True,
             substituted=[{"src": GRAIN_SRC, "kind": "texture", "reason": "load failed: procedural stand-in",
                           "style": "photo"},
                          {"src": STREAM_SRC, "kind": "audio", "reason": "no audio fed: silence"}],
             unsupported=[{"what": "sound playback", "name": "Sound",
                           "reason": "the Sound pass compiles but is never played"}])
    study.mkdir(parents=True)
    (study / "xpAAA1.md").write_text(NOTE, encoding="utf-8", newline="\n")
    for attr, val in (("CORPUS", corpus),):
        monkeypatch.setattr(C, attr, val)
    monkeypatch.setattr(X, "STATE_ROOT", state)
    monkeypatch.setattr(X, "RENDERS", renders)
    monkeypatch.setattr(X, "STUDY", study)
    monkeypatch.setattr(X, "LEDGER", ledger)
    return {"state": state, "corpus": corpus, "renders": renders, "study": study, "ledger": ledger}


def _sha8(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:8]


def _by_label(ledger: dict, label: str) -> list:
    return [c for c in ledger["claims"] if c["label"] == label]


def _tagged(ledger: dict, tag: str) -> list:
    return [c for c in ledger["claims"] if c.get("tag") == tag]


def _code_lines(ledger: dict, claim: dict, world: dict) -> list:
    """The source lines a claim's code evidence ids name, read back from the corpus files."""
    out = []
    for ev in claim["evidence"]:
        m = re.fullmatch(re.escape(ledger["id"]) + r"@([0-9a-f]{8}):(\w+):(\d+)-(\d+)", ev)
        if m:
            text = (world["corpus"] / "shaders" / ledger["id"] / f"{m.group(2)}.glsl").read_text(encoding="utf-8")
            out += text.split("\n")[int(m.group(3)) - 1:int(m.group(4))]
    return out


# the uniform or channel each raw-read tag must show on the line it cites (the test's own table, not the module's)
RAW_TOKENS = {"animation.time": r"\b(iTime|iGlobalTime|iDate)\b", "animation.frame": r"\biFrame\b",
              "input.mouse": r"\biMouse\b", "audio.sound_pass": r"\bmainSound\b",
              "feedback.self": r"\biChannel\d\b", "audio.input": r"\biChannel\d\b", "input.keyboard": r"\biChannel\d\b"}


# ------------------------------------------------------------------------------------------------ the shape
def test_every_claim_is_labelled_evidenced_and_bounded(world):
    for sid in ("xpAAA1", "xpBBB2"):
        led = X.explain(sid)
        assert led["claims"], sid
        ids = [c["id"] for c in led["claims"]]
        assert len(ids) == len(set(ids)), "claim ids are unique"
        for c in led["claims"]:
            assert c["label"] in LABELS, c
            assert c["evidence"] and all(isinstance(e, str) and e for e in c["evidence"]), c
            assert c["boundary"].strip(), c
            assert c["claim"].strip(), c
        assert led["counts"] == {lab: len(_by_label(led, lab)) for lab in X.LABELS}
        assert tuple(X.LABELS) == ("observed-in-code", "observed-in-render", "measured", "inferred", "unknown")


def test_confidence_is_one_fixed_scale_and_the_detector_number_travels_apart_as_score(world):
    """Before: dissect floats, "high", "unrated" and None shared one field. Now every claim says high, moderate or low,
    and a claim the dissector fed carries the dissector's own number (a judgement scale, not a probability) as score."""
    assert tuple(X.CONFIDENCE) == ("high", "moderate", "low")
    for sid in ("xpAAA1", "xpBBB2"):
        led = X.explain(sid)
        for c in led["claims"]:
            assert c["confidence"] in X.CONFIDENCE, c
            if "score" in c:
                assert isinstance(c["score"], float) and 0.0 <= c["score"] <= 1.0, c
                assert c.get("tag"), "only a dissector-fed claim carries a score"
        scored = [c for c in led["claims"] if c.get("kind") in ("technique", "name_only")]
        assert all(c["confidence"] == X.confidence_band(c["score"]) for c in scored if c["kind"] == "technique")
        assert all(c["confidence"] == "low" for c in scored if c["kind"] == "name_only")
    assert (X.confidence_band(0.95), X.confidence_band(0.8), X.confidence_band(0.6)) == ("high", "moderate", "low")


# ------------------------------------------------------------------------------------------------ the label rule
def test_only_raw_facts_are_observed_and_every_reading_is_inferred(world):
    """THE RULE. observed-in-code is for what the code or the configuration says outright: a pass, an input, a uniform
    or declared channel read on the cited line, a function present at a line, functions nothing reaches. A technique the
    dissector RECOGNISES (a sphere trace, a box distance, a gamma curve) is its interpretation of the math: inferred.
    Before this pin the lantern's sphere trace, sphere distance and gamma were all labelled observed-in-code."""
    led = X.explain("xpAAA1")
    for tag in ("raymarch.sphere_trace", "sdf.sphere", "color.gamma"):
        rows = _tagged(led, tag)
        assert rows and all(c["label"] == "inferred" and c["kind"] == "technique" for c in rows), (tag, rows)
        assert all("score" in c for c in rows)
    clock = _tagged(led, "animation.time")
    assert clock and all(c["label"] == "observed-in-code" and c["kind"] == "read" for c in clock), clock
    for sid in ("xpAAA1", "xpBBB2"):
        led = X.explain(sid)
        for c in led["claims"]:
            if c["label"] == "observed-in-code":
                assert c.get("kind") in ("config", "read", "declared", "dead"), c
                assert not re.search(r"stand-in|would|predict", c["claim"]), "a prediction is never an observation"
            if c.get("kind") == "read":
                lines = _code_lines(led, c, world)
                assert lines and all(re.search(RAW_TOKENS[c["tag"]], ln) for ln in lines), (c, lines)
            if c.get("tag") and c["tag"] not in RAW_TOKENS and c["tag"] != "feedback.cycle":
                assert c["label"] in ("inferred", "unknown"), c
            if any(e.startswith("study:") for e in c["evidence"]):
                assert c["label"] == "inferred", c
            if c.get("kind") == "cost":
                assert c["label"] == "inferred", c


def test_a_function_name_alone_is_inferred_and_never_answers_what_it_is_made_of(world):
    """`sdBox` whose body is no box: the dissector tags it by name (score 0.6, above its 0.5 floor). Before this pin the
    ledger said `observed-in-code 0.6 "sdf.box: box distance ..."` and counted it toward "made of: answered"."""
    C.save_shader(_shader("xpDDD4", "Name Alone", [_rp("Image", "image", NAMED_ONLY, [], [{"id": OUT_IMG, "channel": 0}])]),
                  world["corpus"])
    led = X.explain("xpDDD4")
    named = [c for c in led["claims"] if c.get("kind") == "name_only"]
    assert named, led["claims"]
    for c in named:
        assert c["label"] == "inferred" and c["confidence"] == "low", c
        assert "function name only; shape not matched" in c["boundary"], c
        assert "sdBox" in c["claim"]
    assert not [c for c in led["claims"] if c["label"].startswith("observed") and c.get("tag", "").startswith("sdf.")]
    made = next(q for q in led["checklist"] if q["key"] == "made_of")
    assert made["status"] == "partial", made
    assert not set(made["claims"]) & {c["id"] for c in named} or "name" in made["because"], made
    sdf = next(c for c in led["claims"] if c.get("kind") == "not_detected" and c.get("group") == "sdf")
    assert "name" in sdf["claim"], "the group's miss says a name suggests it, without counting the name"


@pytest.mark.parametrize("code", ["named_clock", "clock_only"])
def test_reads_and_declarations_alone_never_answer_what_it_is_made_of(world, code):
    """"What is it made of?" is answered by a technique recognised from the shape of the math, nothing less. Before this
    pin the box-by-name scene plus one iTime read said `made_of answered ('1 read or declared outright')`, and so did
    a shader whose only claim was a clock read (20 of 335 corpus shaders)."""
    src = NAMED_CLOCK if code == "named_clock" else CLOCK_ONLY
    C.save_shader(_shader("xpHHH8", "Clock Face", [_rp("Image", "image", src, [], [{"id": OUT_IMG, "channel": 0}])]),
                  world["corpus"])
    led = X.explain("xpHHH8")
    assert not [c for c in led["claims"] if c.get("kind") == "technique"], "the fixture has no shape dissect knows"
    clock = _tagged(led, "animation.time")
    assert clock and clock[0]["kind"] == "read", clock
    if code == "named_clock":
        assert [c for c in led["claims"] if c.get("kind") == "name_only"], led["claims"]
    made = next(q for q in led["checklist"] if q["key"] == "made_of")
    assert made["status"] == "partial", made
    assert "shape" in made["because"] and clock[0]["id"] in made["claims"], made
    for sid in ("xpAAA1", "xpBBB2", "xpHHH8"):        # the rule, over every ledger here
        led = X.explain(sid)
        made = next(q for q in led["checklist"] if q["key"] == "made_of")
        techniques = {c["id"] for c in led["claims"] if c.get("kind") == "technique"}
        assert (made["status"] == "answered") == bool(techniques), (sid, made)


def _feedback_rows(led: dict) -> list:
    return [c for c in led["claims"] if c.get("tag") == "feedback.self"]


def test_a_read_in_a_function_no_entry_point_reaches_is_never_observed(world):
    """The dissector finds a buffer's own-frame read in every token of the pass, dead functions included. Before this
    pin a Buffer A whose only iChannel0 read sat in a dead unused() got observed-in-code 'reads its own previous frame
    (first at buffer_a.glsl:1)' beside observed 'unused() line 1 no entry point reaches'. Now that read is not a
    sighting: the claim cites the configuration and says the only read is in code nothing reaches."""
    C.save_shader(_shader("xpJJJ9", "Dead Echo", [
        _rp("Buffer A", "buffer", DEAD_READ, [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    led = X.explain("xpJJJ9")
    sha = _sha8((world["corpus"] / "shaders" / "xpJJJ9" / "shader.json").read_bytes())
    dead = [c for c in led["claims"] if c.get("kind") == "dead" and "buffer_a.glsl" in c["claim"]]
    assert dead and "unused()" in dead[0]["claim"], led["claims"]
    own = _feedback_rows(led)
    assert own, led["claims"]
    for c in own:
        assert c["kind"] != "read", c
        assert c["evidence"] == [f"config:xpJJJ9@{sha}:buffer_a:iChannel0"], c
        assert c["kind"] == "declared" and "no read" in c["claim"] and "unused()" in c["claim"], c
    observed_lines = [e for c in led["claims"] if c["label"] == "observed-in-code" and c.get("kind") == "read"
                      for e in c["evidence"] if e.endswith(":1-1")]
    assert not observed_lines, observed_lines


def test_a_dead_read_beside_a_live_one_cites_the_live_line(world):
    """When the dissector's first line is in dead code but the pass also reads the channel live, the ledger cites the
    live line, the one a reader can open and see used."""
    C.save_shader(_shader("xpKKK1", "Half Dead Echo", [
        _rp("Buffer A", "buffer", DEAD_AND_LIVE, [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    led = X.explain("xpKKK1")
    own = _feedback_rows(led)
    assert own and all(c["kind"] == "read" and c["label"] == "observed-in-code" for c in own), own
    code = [e for c in own for e in c["evidence"] if e.startswith("xpKKK1@")]
    assert code and all(e.endswith(":buffer_a:3-3") for e in code), code
    assert "buffer_a.glsl:3" in own[0]["claim"], own


def test_a_read_on_an_inactive_line_is_never_observed(world, monkeypatch):
    """A line inside an #if branch the preprocessor drops is not code the GPU runs. The ledger used to check only that
    the cited line's TEXT holds the channel; a row pointed into a dropped branch passed as an observed read."""
    C.save_shader(_shader("xpLLL2", "Dropped Echo", [
        _rp("Buffer A", "buffer", INACTIVE_READ, [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    _cite_at(monkeypatch, "feedback.self", 3)
    led = X.explain("xpLLL2")
    own = _feedback_rows(led)
    assert own, led["claims"]
    for c in own:
        assert c["kind"] == "declared" and "no read" in c["claim"] and "#if" in c["claim"], c
        assert not any(e.startswith("xpLLL2@") for e in c["evidence"]), c


def test_a_renaming_define_is_not_the_read(world, monkeypatch):
    """`#define keyTex iChannel1` names the channel; the read is where keyTex is used. Before this pin two corpus
    keyboard reads cited the #define line, so 'each read checked on the line cited' overstated what was checked."""
    C.save_shader(_shader("xpMMM3", "Key Press", [
        _rp("Image", "image", KEYS, [_inp(1, "keyboard", "k1")], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    _cite_at(monkeypatch, "input.keyboard", 1)
    led = X.explain("xpMMM3")
    keys = _tagged(led, "input.keyboard")
    assert keys and keys[0]["kind"] == "read", keys
    lines = _code_lines(led, keys[0], world)
    assert lines and not any(ln.lstrip().startswith("#") for ln in lines), lines
    assert all("texelFetch(keyTex" in ln for ln in lines), lines


def test_a_read_through_a_common_macro_is_a_read(world):
    """Common is prepended to every pass, so a macro Common defines and a pass uses is that pass's live code. Before
    this pin the ledger searched only the pass files for a live read, never common.glsl, and wrote observed-in-code
    'no read found in the live code of buffer_a.glsl' about a buffer that reads its own frame through Common's macro
    (7 rows in 4 corpus shaders). Now the read is cited where it sits: common.glsl line 1."""
    C.save_shader(_shader("xpPPP6", "Common Echo", [
        _rp("Common", "common", COMMON_READ),
        _rp("Buffer A", "buffer", BUF_VIA_COMMON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    led = X.explain("xpPPP6")
    own = _feedback_rows(led)
    assert own, led["claims"]
    for c in own:
        assert c["kind"] == "read" and c["label"] == "observed-in-code", c
        assert "no read found" not in c["claim"] and "first at common.glsl:1" in c["claim"], c
    code = [e for c in own for e in c["evidence"] if e.startswith("xpPPP6@")]
    assert code and all(e.endswith(":common:1-1") for e in code), code
    lines = _code_lines(led, own[0], world)
    assert lines and all("iChannel0" in ln for ln in lines), lines


def test_a_common_macro_reads_through_the_using_passs_own_alias(world):
    """A macro is expanded where the pass uses it, so a Common macro that names SELF_CH reads whatever channel the using
    pass defines SELF_CH as. Buffer A defines it as iChannel0 (its own frame); Image defines it as iChannel1. The read
    is common.glsl line 1, seen through Buffer A's alias and only Buffer A's."""
    C.save_shader(_shader("xpSSS9", "Borrowed Macro", [
        _rp("Common", "common", COMMON_ALIAS_MACRO),
        _rp("Buffer A", "buffer", BUF_DEFINES_ALIAS, [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", IMG_DEFINES_ALIAS, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]),
        world["corpus"])
    led = X.explain("xpSSS9")
    own = _feedback_rows(led)
    assert own and all(c["kind"] == "read" and c["label"] == "observed-in-code" for c in own), own
    assert "no read found" not in own[0]["claim"] and "first at common.glsl:1" in own[0]["claim"], own
    code = [e for c in own for e in c["evidence"] if e.startswith("xpSSS9@")]
    assert code and all(e.endswith(":common:1-1") for e in code), code


@pytest.mark.parametrize("where", ["common", "own"])
@pytest.mark.parametrize("macro, reads", [(WAVE_T, False), (WAVE_K, True)], ids=["param-t", "param-k"])
def test_a_macro_parameter_named_like_the_alias_is_not_a_read(world, monkeypatch, where, macro, reads):
    """Image renames the clock (`#define t iTime`) and calls WAVE(2.0). When WAVE's own parameter is called t, the t in
    its body is the argument, 2.0, never the clock. Before the first fix every token in a macro body that matched the
    using pass's alias counted, the parameter too, and the ledger wrote observed-in-code 'iTime/iDate read 1 time(s)
    (first at common.glsl:1 ...)' about a shader that reads no clock (latent: no corpus row). glsl.py's call graph took
    the parameter for a use of the macro t as well, so the dissector reported that read in the first place; now nothing
    reaches `#define t iTime`, the dissector reports no clock, and the ledger has no clock row at all (the ledger's own
    guard is pinned by the next test). The control, a parameter called k beside a t in the body, still reads the clock
    through Image's alias, and stays observed."""
    sid = f"xpW{where[0]}{'r' if reads else 'n'}1"
    passes = [_rp("Image", "image", IMG_RENAMES_T if where == "common" else
                  IMG_RENAMES_T.replace("#define t iTime\n", "#define t iTime\n" + macro), [],
                  [{"id": OUT_IMG, "channel": 0}])]
    if where == "common":
        passes.insert(0, _rp("Common", "common", macro))
    C.save_shader(_shader(sid, f"Wave {where} {reads}", passes), world["corpus"])
    _cite_at(monkeypatch, "animation.time", 1)
    led = X.explain(sid)
    clock = _tagged(led, "animation.time")
    wave = ":common:1-1" if where == "common" else ":image:2-2"
    if reads:
        assert clock and clock[0]["kind"] == "read" and clock[0]["label"] == "observed-in-code", clock
        assert any(e.endswith(wave) for e in clock[0]["evidence"]), clock
    else:
        assert not clock, clock


def test_a_macro_parameter_stays_no_read_where_the_alias_it_is_named_like_is_reached(world):
    """The ledger's own guard (a macro's parameter is never a live token), kept covered now that the call graph no
    longer reaches an alias through a parameter's name: here Image reads the clock through t on line 3, so `#define t
    iTime` IS reached and the dissector cites it (common.glsl:1, a #define that only renames). The first live read the
    ledger finds must be image.glsl:3, never WAVE's body on common.glsl:2, whose t is WAVE's argument."""
    C.save_shader(_shader("xpWxr1", "Wave Reached", [
        _rp("Common", "common", COMMON_T_AND_WAVE),
        _rp("Image", "image", IMG_READS_T, [], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    led = X.explain("xpWxr1")
    clock = _tagged(led, "animation.time")
    assert clock and clock[0]["kind"] == "read" and clock[0]["label"] == "observed-in-code", clock
    code = [e for e in clock[0]["evidence"] if e.startswith("xpWxr1@")]
    assert code == [code[0]] and code[0].endswith(":image:3-3"), clock
    assert "image.glsl:3" in clock[0]["claim"] and "common.glsl:2" not in clock[0]["claim"], clock


@pytest.mark.parametrize("where", ["common", "own"])
def test_a_macro_parameter_named_like_a_macro_that_is_not_an_alias_reaches_nothing(world, where):
    """`#define t (iTime * 2.0)` is not a renaming, so before this pin the iTime in its body counted as a read wherever
    t was reached, and the call graph reached t through WAVE's parameter t: the ledger wrote observed-in-code
    'iTime/iDate read 1 time(s) (first at image.glsl:1)' about a shader that never expands t (probe p1f; latent, no
    corpus row). Now t is never reached, and no clock row is observed."""
    sid = f"xpX{where[0]}f1"
    img = IMG_EXPR_T if where == "common" else IMG_EXPR_T.replace("#define t (iTime * 2.0)\n",
                                                                   "#define t (iTime * 2.0)\n" + WAVE_T)
    passes = [_rp("Image", "image", img, [], [{"id": OUT_IMG, "channel": 0}])]
    if where == "common":
        passes.insert(0, _rp("Common", "common", WAVE_T))
    C.save_shader(_shader(sid, f"Expr {where}", passes), world["corpus"])
    led = X.explain(sid)
    observed = [c for c in _tagged(led, "animation.time") if c["label"] == "observed-in-code"]
    assert not observed, observed


@pytest.mark.parametrize("code, line", [(FN_PARAM_T, None), (FN_PARAM_T_READ, 5), (FN_PARAM_ITIME, None)],
                         ids=["alias-named-parameter", "with-a-real-read", "parameter-named-iTime"])
def test_a_function_parameter_named_like_the_clock_is_not_a_read(world, code, line):
    """A function's parameter shadows the uniform or alias it is named like: `float swell(float t)` beside `#define t
    iTime` becomes `float swell(float iTime)`, whose iTime is its argument. Before this pin the ledger cited swell's line
    2 as an observed clock read (probe p1g; tdSXzD has five such functions, though the line it cites today is a real
    read), and a parameter named iTime itself read as the clock on line 1. Now only the real read on line 5 is cited,
    and with none there is no observed clock row."""
    sid = f"xpF{'r' if line else 'n'}{'i' if 'iTime)' in code.split(chr(10))[1] else 't'}1"
    C.save_shader(_shader(sid, "Swell", [_rp("Image", "image", code, [], [{"id": OUT_IMG, "channel": 0}])]),
                  world["corpus"])
    led = X.explain(sid)
    clock = _tagged(led, "animation.time")
    if line is None:
        assert not [c for c in clock if c["label"] == "observed-in-code"], clock
        return
    assert clock and clock[0]["kind"] == "read" and clock[0]["label"] == "observed-in-code", clock
    cited = [e for e in clock[0]["evidence"] if e.startswith(sid + "@")]
    assert cited and all(e.endswith(f":image:{line}-{line}") for e in cited), clock


@pytest.mark.parametrize("code, tag, inputs", [
    (CHAIN_KEYS, "input.keyboard", [("keyboard", 2)]),
    (CHAIN_CLOCK, "animation.time", []),
], ids=["keyboard", "clock"])
def test_an_alias_of_an_alias_cites_the_real_read(world, code, tag, inputs):
    """Both #defines only rename. Before this pin only one level of renaming was followed: the ledger cited line 2
    (`#define KEYS Pressed`, `#define NOW2 Now`) as an observed read (probe p4c; latent, no corpus row). The read is the
    use on line 4."""
    sid = f"xpC{tag[0]}{tag[-1]}1"
    C.save_shader(_shader(sid, "Chain", [_rp("Image", "image", code, [_inp(ch, typ, "k") for typ, ch in inputs],
                                             [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    led = X.explain(sid)
    rows = _tagged(led, tag)
    assert rows and rows[0]["kind"] == "read" and rows[0]["label"] == "observed-in-code", rows
    cited = [e for e in rows[0]["evidence"] if e.startswith(sid + "@")]
    assert cited and all(e.endswith(":image:4-4") for e in cited), rows
    assert all(not ln.lstrip().startswith("#") for ln in _code_lines(led, rows[0], world)), rows


def test_a_helper_in_a_pass_with_no_entry_point_is_never_live(world):
    """Image's entry is built by Common's PAINT, and Image has helpers of its own. Before this pin the reader walked from
    every helper as if each were an entry point, so beside 'image.glsl: the reader found no entry point ... none of its
    code was followed as live' the ledger wrote observed-in-code 'music on iChannel1, read 1 time(s) (first at
    image.glsl:2)' (probe p3e), and the dissector's cost walked ridge's loop (heaviest 9) under a claim saying no call
    graph was walked (p2b). Now nothing in the pass is live: the audio row cites the configuration and says the read is
    unknown, the helpers are listed as unreached only as a reading, and no estimate exists."""
    C.save_shader(_shader("xpHHH1", "Helper Macro", [
        _rp("Common", "common", COMMON_PAINTS),
        _rp("Image", "image", IMG_HELPERS, [_inp(1, "music", "m1", STREAM_SRC)], [{"id": OUT_IMG, "channel": 0}])]),
        world["corpus"])
    led = X.explain("xpHHH1")
    sha = _sha8((world["corpus"] / "shaders" / "xpHHH1" / "shader.json").read_bytes())
    audio = _tagged(led, "audio.input")
    assert audio, led["claims"]
    for c in audio:
        assert c["label"] != "observed-in-code", c
        assert c["evidence"] == [f"config:xpHHH1@{sha}:image:iChannel1"], c
        assert "entry point" in c["claim"], c
    assert not [c for c in led["claims"] if c.get("kind") == "cost" and c["claim"].startswith("image.glsl")]
    blind = [c for c in led["claims"] if c.get("kind") == "cost_unknown"]
    assert len(blind) == 1 and blind[0]["claim"].startswith("image.glsl:"), blind
    dead = [c for c in led["claims"] if c.get("kind") == "dead" and c["claim"].startswith("image.glsl")]
    assert dead and all(c["label"] == "inferred" for c in dead), dead
    assert "loudness()" in dead[0]["claim"] and "ridge()" in dead[0]["claim"], dead


# bend is handed to a macro that calls it: under the parameter's own name (the re-review's probe E6), under another
# name, and after an argument holding commas inside nested parentheses; then (second re-review) inside an expression,
# through an object-like macro naming it, and to a function-like macro that a second macro is handed and calls. The
# control hands it to a macro whose body never calls that parameter.
@pytest.mark.parametrize("sid, macro, use, dead", [
    ("xpPsn1", "#define APPLY2(bend, v) bend(v)", "APPLY2(bend, at.x / iResolution.x)", False),
    ("xpPon1", "#define APPLY(f, x) f(x)", "APPLY(bend, at.x / iResolution.x)", False),
    ("xpPnp1", "#define LATER(x, f) f(x)", "LATER(clamp(at.x, 0.0, (at.y * 2.0)) / iResolution.x, bend)", False),
    ("xpPsx1", "#define FLIP(bend, v) bend(v)", "FLIP(-bend, at.x / iResolution.x)", False),
    ("xpPox1", "#define FLIP(f, v) f(v)", "FLIP(0.5 * bend, at.x / iResolution.x)", False),
    ("xpPsa1", "#define PICKED bend\n#define FLIP(bend, v) bend(v)", "FLIP(PICKED, at.x / iResolution.x)", False),
    ("xpPsh1", "#define RUNS(bend, v) bend(v)\n#define WITH(m, g, a) m(g, a)", "WITH(RUNS, bend, at.x)", False),
    ("xpPoh1", "#define RUNS(q, v) q(v)\n#define WITH(m, g, a) m(g, a)", "WITH(RUNS, bend, at.x)", False),
    ("xpPnc1", "#define KEEP(f, x) (x)", "KEEP(bend, at.x / iResolution.x)", True),
], ids=["same-name", "other-name", "nested-parentheses", "same-name-negated", "scaled", "same-name-alias",
        "same-name-macro-passed-a-macro", "macro-passed-a-macro", "not-called"])
def test_a_function_passed_to_a_macro_that_calls_it_is_not_called_dead(world, sid, macro, use, dead):
    """Before this pin the first fix made a macro's parameter followed by '(' stop being a call of a function named like
    it, but never followed the argument the caller passes there: with `#define APPLY2(bend, v) bend(v)` and mainImage
    calling APPLY2(bend, ...), the ledger wrote observed-in-code 'image.glsl: 1 function(s) no entry point reaches:
    bend() line 1' (probe E6; latent, no corpus row). Under another name HEAD made the same claim, and corpus shaders
    hand distance functions to a march macro that way. Now the function the caller passes is the caller's call; handed
    to a parameter the body never calls, it is still observed unreached. The second re-review found the same false claim
    where the parameter shares bend's name and the argument is `-bend` (probe S1), an object-like macro naming bend
    (S2), or a macro handed to a macro (S3: WITH(RUNS, bend, x) is RUNS(bend, x), which is bend(x)), all of which HEAD
    got right only through the shared name; and under other names (L4b, U3), which HEAD got wrong too."""
    src = ("float bend(float v) { return v * v; }\n" + macro + "\nvoid mainImage(out vec4 ink, in vec2 at) {\n"
           "    ink = vec4(" + use + ");\n}\n")
    C.save_shader(_shader(sid, "Passed On", [_rp("Image", "image", src, [], [{"id": OUT_IMG, "channel": 0}])]),
                  world["corpus"])
    led = X.explain(sid)
    rows = [c for c in led["claims"] if c.get("kind") == "dead"]
    if not dead:
        assert not rows, rows
        return
    assert len(rows) == 1 and rows[0]["label"] == "observed-in-code", rows
    assert "bend() line 1" in rows[0]["claim"], rows


def test_a_read_in_a_continued_define_cites_the_whole_define(world):
    """glsl.py files every token of a #define written over several lines under its first line, so a read on a
    continuation line was cited as `common:1-1`, a line holding only `#define PREV(q) \\` (wsByWV, common.glsl:835,
    whose macro runs to line 840). The evidence id now names the define's whole span, which does hold the read."""
    C.save_shader(_shader("xpTTT1", "Long Define", [
        _rp("Common", "common", COMMON_LONG_MACRO),
        _rp("Buffer A", "buffer", BUF_USES_LONG, [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    led = X.explain("xpTTT1")
    own = _feedback_rows(led)
    assert own and all(c["kind"] == "read" and c["label"] == "observed-in-code" for c in own), own
    code = [e for c in own for e in c["evidence"] if e.startswith("xpTTT1@")]
    assert code and all(e.endswith(":common:1-2") for e in code), code
    assert any("iChannel0" in ln for ln in _code_lines(led, own[0], world)), _code_lines(led, own[0], world)


def test_an_alias_from_another_pass_is_not_a_read_here(world, monkeypatch):
    """`#define T iTime` in Buffer A renames the clock for Buffer A (and Common's aliases for every pass), never for
    Image. Before this pin the ledger collected aliases from every pass and applied them to every pass, so Image's plain
    `float T = 0.5;` on line 3 was cited as an observed clock read; the read is on line 4."""
    C.save_shader(_shader("xpQQQ7", "Borrowed Name", [
        _rp("Buffer A", "buffer", BUF_ALIAS_ONLY, [], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", IMG_PLAIN_T, [], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    _cite_at(monkeypatch, "animation.time", 2)
    led = X.explain("xpQQQ7")
    clock = _tagged(led, "animation.time")
    assert clock and clock[0]["kind"] == "read" and clock[0]["label"] == "observed-in-code", clock
    code = [e for e in clock[0]["evidence"] if e.startswith("xpQQQ7@")]
    assert code and all(e.endswith(":image:4-4") for e in code), code
    assert "image.glsl:4" in clock[0]["claim"] and "image.glsl:3" not in clock[0]["claim"], clock


def test_a_pass_with_no_entry_point_is_never_observed_dead_or_unread(world):
    """Each pass is one macro Common defines (`IMAGE`, `BUFFERA`), so the reader finds no entry point in any pass and
    follows none of their code. Before this pin the ledger still wrote observed-in-code 'common.glsl: 2 function(s) no
    pass reaches' (a corpus shader built this way had 18 of its 195 'dead' names reached), observed-in-code 'no read
    found' about Buffer A's own frame, and no unknown saying the reader found no entry point."""
    C.save_shader(_shader("xpRRR8", "Built By Macro", [
        _rp("Common", "common", COMMON_BUILDS),
        _rp("Buffer A", "buffer", "BUFFERA\n", [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", "IMAGE\n", [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]),
        world["corpus"])
    led = X.explain("xpRRR8")
    no_entry = [c for c in led["claims"] if c.get("kind") == "no_entry"]
    assert {f for c in no_entry for f in ("buffer_a.glsl", "image.glsl") if c["claim"].startswith(f)} == \
        {"buffer_a.glsl", "image.glsl"}, no_entry
    assert all(c["label"] == "unknown" and "entry point" in c["claim"] for c in no_entry), no_entry
    dead = [c for c in led["claims"] if c.get("kind") == "dead"]
    assert dead and all(c["label"] == "inferred" and "entry point" in c["boundary"] for c in dead), dead
    own = _feedback_rows(led)
    assert own, "the dissector reports Buffer A's self-wiring; the ledger must still say something about it"
    for c in own:
        assert c["label"] != "observed-in-code" and "no read found" not in c["claim"], c
        assert "entry point" in c["claim"], c
    assert not [c for c in led["claims"] if c["label"] == "observed-in-code" and c.get("kind") in ("read", "dead")]


def test_a_pass_with_no_entry_point_gets_no_cost_estimate(world):
    """The static cost walks the call graph from a pass's entry point. Before this pin a pass in which the reader found
    none still got inferred (moderate) 'heaviest path 1 = ; ~0 user calls and ~0 tokens executed per pixel', bounded
    'along the call graph from the entry' (4 corpus claims: fsXXzX's three passes and cdG3Wd's image.glsl). Now its cost
    is an unknown that says why, and the cost question on the checklist still cites it."""
    C.save_shader(_shader("xpRRR9", "Built By Macro Too", [
        _rp("Common", "common", COMMON_BUILDS),
        _rp("Buffer A", "buffer", "BUFFERA\n", [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", "IMAGE\n", [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]),
        world["corpus"])
    led = X.explain("xpRRR9")
    for f in ("buffer_a.glsl", "image.glsl"):
        about = [c for c in led["claims"] if c["claim"].startswith(f + ":") and "cost" in c["claim"]]
        assert about, (f, led["claims"])
        for c in about:
            assert c["label"] == "unknown" and "entry point" in c["claim"], c
            assert "heaviest path" not in c["claim"] and "from the entry" not in c["boundary"], c
    costs = [c["id"] for c in led["claims"] if "static cost" in c["claim"]]
    q = next(q for q in led["checklist"] if q["key"] == "cost")
    assert costs and set(costs) <= set(q["claims"]), (costs, q)
    # a pass the reader did follow keeps its estimate
    led = X.explain("xpAAA1")
    est = [c for c in led["claims"] if c.get("kind") == "cost"]
    assert est and all(c["label"] == "inferred" and "heaviest path" in c["claim"] for c in est), est


def test_a_channel_row_in_a_pass_with_no_entry_point_cites_the_configuration(world):
    """Image is one macro Common defines, and is wired to an audio input. The dissector followed none of Image's code,
    so its below-floor audio row points at image.glsl line 1, a placeholder (the line holds `IMAGE`). Before this pin
    the ledger said the reading sat 'at image.glsl:1' and cited `image:1-1` (cdG3Wd); it said 'in the configuration
    (iChannel1)' before the no-entry rule. A channel is a fact of the configuration, so that is what the row cites."""
    C.save_shader(_shader("xpUUU2", "Deaf Macro", [
        _rp("Common", "common", COMMON_BUILDS),
        _rp("Image", "image", "IMAGE\n", [_inp(1, "music", "m1", STREAM_SRC)], [{"id": OUT_IMG, "channel": 0}])]),
        world["corpus"])
    led = X.explain("xpUUU2")
    sha = _sha8((world["corpus"] / "shaders" / "xpUUU2" / "shader.json").read_bytes())
    audio = _tagged(led, "audio.input")
    assert audio, led["claims"]
    for c in audio:
        assert c["label"] != "observed-in-code", c
        assert c["evidence"] == [f"config:xpUUU2@{sha}:image:iChannel1"], c
        assert "in the configuration (iChannel1)" in c["claim"] and "image.glsl:1" not in c["claim"], c
        assert "entry point" in c["claim"], c


def test_the_media_folder_prediction_is_its_own_inferred_claim(world):
    """Whether a render will draw a stand-in is a prediction from the corpus's media folder, not a fact in the code.
    Before this pin it rode inside an observed-in-code input claim ("..., so a render draws a stand-in")."""
    led = X.explain("xpBBB2")
    media = [c for c in led["claims"] if c.get("kind") == "media"]
    grain = Path(GRAIN_SRC).name
    assert len([c for c in media if grain in c["claim"]]) == 1, media
    row = next(c for c in media if grain in c["claim"])
    assert row["label"] == "inferred" and "does not hold" in row["claim"] and "stand-in" in row["claim"]
    assert any(e.startswith("config:xpBBB2@") and e.endswith(":buffer_a:iChannel1") for e in row["evidence"])
    for c in led["claims"]:
        if " reads iChannel" in c["claim"]:
            assert "stand-in" not in c["claim"] and "hold" not in c["claim"], c


def test_a_cubemap_is_six_files_in_the_cache_and_the_prediction(world):
    """The shader JSON names only a cubemap's first face; the other five are <hash>_1 .. _5 (corpus.media_to_fetch).
    Before this pin the cache key and the 'corpus holds this file' prediction looked at the first file alone, so faces
    arriving later rebuilt nothing and one face present read as the author's whole cubemap."""
    C.save_shader(_shader("xpNNN4", "Sky Box", [
        _rp("Image", "image", SKY, [_inp(0, "cubemap", "c1", CUBE_SRC)], [{"id": OUT_IMG, "channel": 0}])]),
        world["corpus"])
    media = world["corpus"] / "media"
    media.mkdir(parents=True, exist_ok=True)
    stem, ext = Path(CUBE_SRC).name.rsplit(".", 1)
    faces = [f"{stem}.{ext}"] + [f"{stem}_{k}.{ext}" for k in range(1, 6)]

    def claim(led):
        rows = [c for c in led["claims"] if c.get("kind") == "media"]
        assert len(rows) == 1 and rows[0]["label"] == "inferred", rows
        return rows[0]["claim"]

    first = X.explain("xpNNN4")
    assert set(first["cache"]["inputs"]["media"]) == set(faces), first["cache"]["inputs"]["media"]
    assert "does not hold" in claim(first) and "stand-in" in claim(first)
    (media / faces[0]).write_bytes(b"face 0, our own bytes")
    one = X.explain("xpNNN4")
    assert one["cached"] is False
    assert "1 of" in claim(one) and "can feed the author's" not in claim(one), claim(one)
    for f in faces[1:5]:
        (media / f).write_bytes(f"{f}, our own bytes".encode())
    five = X.explain("xpNNN4")
    assert five["cached"] is False and five["cache"]["key"] != one["cache"]["key"], "a face arriving re-analyses"
    assert "5 of" in claim(five) and "can feed the author's" not in claim(five), claim(five)
    (media / faces[5]).write_bytes(b"face 5, our own bytes")
    six = X.explain("xpNNN4")
    assert six["cached"] is False and "can feed the author's" in claim(six) and "does not" not in claim(six), claim(six)


def test_a_pass_reports_the_lines_a_reader_counts(world):
    """LANTERN is 20 lines ending in a newline; the ledger said 21 (it counted the empty string after the last one)."""
    led = X.explain("xpAAA1")
    assert len(LANTERN.splitlines()) == 20
    row = next(c for c in led["claims"] if c.get("kind") == "config" and " pass of " in c["claim"])
    assert " pass of 20 lines " in row["claim"], row
    assert any(e.endswith(":image:1-20") for e in row["evidence"]), row


def test_a_channel_declared_but_never_read_cites_the_configuration_not_line_1(world):
    """A buffer whose own output is wired back in but never read: the dissector keeps the tag and points at line 1,
    which holds no read. The ledger cites the declaration instead and says no read was found. A cycle between two
    buffers is a fact of the wiring too: it cites the inputs that close it, never line 1 of a file."""
    C.save_shader(_shader("xpEEE5", "Unread Loop", [
        _rp("Buffer A", "buffer", UNREAD, [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    led = X.explain("xpEEE5")
    sha = _sha8((world["corpus"] / "shaders" / "xpEEE5" / "shader.json").read_bytes())
    own = _tagged(led, "feedback.self")
    assert own, led["claims"]
    for c in own:
        assert c["evidence"] == [f"config:xpEEE5@{sha}:buffer_a:iChannel0"], c
        assert "no read" in c["claim"] and c["label"] == "observed-in-code" and c["kind"] == "declared", c
    route = next(r for r in led["route"] if r["route"] == "buffer feedback")
    assert route["evidence"] == [f"config:xpEEE5@{sha}:buffer_a:iChannel0"], route

    C.save_shader(_shader("xpFFF6", "Two Mirrors", [
        _rp("Buffer A", "buffer", PASS_ON, [_inp(0, "buffer", OUT_B)], [{"id": OUT_A, "channel": 0}]),
        _rp("Buffer B", "buffer", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_B, "channel": 0}]),
        _rp("Image", "image", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    led = X.explain("xpFFF6")
    sha = _sha8((world["corpus"] / "shaders" / "xpFFF6" / "shader.json").read_bytes())
    cyc = _tagged(led, "feedback.cycle")
    assert cyc and all(c["kind"] == "declared" for c in cyc), cyc
    assert set(cyc[0]["evidence"]) == {f"config:xpFFF6@{sha}:buffer_a:iChannel0", f"config:xpFFF6@{sha}:buffer_b:iChannel0"}
    tags_at_line_1 = [c for c in led["claims"] if c.get("tag", "").startswith("feedback.")
                      and any(e.endswith(":1-1") for e in c["evidence"])]
    assert not tags_at_line_1, tags_at_line_1


def test_the_ledger_is_written_under_state_and_refused_outside_it(world, tmp_path):
    led = X.explain("xpAAA1")
    path = Path(led["ledger_path"])
    assert path == world["ledger"] / "xpAAA1.json" and path.is_file()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["id"] == "xpAAA1" and stored["claims"] == led["claims"]
    with pytest.raises(ValueError, match="outside"):
        X.explain("xpAAA1", ledger_dir=tmp_path / "elsewhere")


def test_code_evidence_ids_name_the_pass_sha_and_a_line_range_that_holds_the_technique(world):
    led = X.explain("xpAAA1")
    sha = _sha8(LANTERN.encode("utf-8"))
    code = [c for c in led["claims"] if c.get("tag")]
    assert {"raymarch.sphere_trace", "sdf.sphere", "color.gamma", "animation.time"} <= {c["tag"] for c in code}
    lines = LANTERN.split("\n")
    for c in code:
        for ev in c["evidence"]:
            m = re.fullmatch(r"xpAAA1@([0-9a-f]{8}):image:(\d+)-(\d+)", ev)
            assert m, ev
            assert m.group(1) == sha
            lo, hi = int(m.group(2)), int(m.group(3))
            assert 1 <= lo <= hi <= len(lines)
    sphere = next(c for c in code if c["tag"] == "sdf.sphere")
    lo = int(sphere["evidence"][0].rsplit(":", 1)[1].split("-")[0])
    assert "length(spot) - radius" in lines[lo - 1]


def test_configuration_is_read_alongside_the_code(world):
    """Inputs are judged from the shader's own declaration (its JSON), never from a sampler's name."""
    led = X.explain("xpBBB2")
    cfg = [c for c in led["claims"] if " reads iChannel" in c["claim"] or " pass of " in c["claim"]]
    joined = " ".join(c["claim"] for c in cfg)
    assert "iChannel1" in joined and "texture" in joined and "music" in joined
    assert "its own previous frame" in joined, "Buffer A's self-read comes from the declaration, not a name"
    shader_sha = _sha8((world["corpus"] / "shaders" / "xpBBB2" / "shader.json").read_bytes())
    for c in cfg:
        assert c["label"] == "observed-in-code"
        assert any(e.startswith("config:") for e in c["evidence"]), c
        for e in c["evidence"]:
            if e.startswith("config:"):
                assert re.fullmatch(r"config:xpBBB2@" + shader_sha + r":(common|buffer_a|image|sound):(pass|iChannel\d)", e), e


def test_render_claims_cite_the_receipt_by_its_sha_and_path_and_timing_is_swiftshader(world):
    led = X.explain("xpAAA1")
    rec = world["renders"] / "xpAAA1" / "receipt.json"
    film = world["renders"] / "xpAAA1" / "filmstrip.json"
    shas = {_sha8(rec.read_bytes()): rec, _sha8(film.read_bytes()): film}
    seen = _by_label(led, "observed-in-render") + _by_label(led, "measured")
    assert _by_label(led, "observed-in-render") and _by_label(led, "measured")
    for c in seen:
        renders = [e for e in c["evidence"] if e.startswith("render:")]
        assert renders, c
        for e in renders:
            assert e[len("render:"):] in shas, e
            assert str(shas[e[len("render:"):]]) in c["paths"], c
    timing = [c for c in _by_label(led, "measured") if "ms" in c["claim"]]
    assert timing and all("SwiftShader" in c["claim"] + c["boundary"] for c in timing)
    assert any("GPU" in c["claim"] for c in _by_label(led, "unknown")), "GPU timing is listed as unknown"


def test_study_note_claims_are_always_inferred_and_point_at_their_heading(world):
    """A study id carries the note's sha8, so an id copied out of an old ledger goes stale when the note changes (before:
    `study:xpAAA1#4.1` stayed the same through any edit). The corroboration section is cited too, and is inferred:
    it is an earlier check of the note against renders, read here, not re-run."""
    led = X.explain("xpAAA1")
    note = world["study"] / "xpAAA1.md"
    sha = _sha8(note.read_bytes())
    study = [c for c in led["claims"] if any(e.startswith("study:") for e in c["evidence"])]
    assert {e for c in study for e in c["evidence"]} == {f"study:xpAAA1@{sha}#4.1", f"study:xpAAA1@{sha}#4.2",
                                                         f"study:xpAAA1@{sha}#corroboration-2026-10-13"}
    assert all(c["label"] == "inferred" for c in study)
    assert all(str(world["study"] / "xpAAA1.md") in c["paths"] or "xpAAA1.md" in " ".join(c["paths"]) for c in study)
    corr = next(c for c in study if c.get("kind") == "corroboration")
    assert "Confirmed by render (2)" in corr["claim"] and "Contradicted (1)" in corr["claim"], corr
    intent = next(q for q in led["checklist"] if q["key"] == "intent")
    assert corr["id"] in intent["claims"]
    note.write_text(NOTE.replace("words of our own", "other words of our own"), encoding="utf-8", newline="\n")
    again = X.explain("xpAAA1")
    new_sha = _sha8(note.read_bytes())
    assert new_sha != sha
    assert all(f"@{new_sha}#" in e for c in again["claims"] for e in c["evidence"] if e.startswith("study:"))
    led_b = X.explain("xpBBB2")
    assert any("study note" in c["claim"].lower() for c in _by_label(led_b, "unknown")), "a missing note is an unknown"


def test_unknowns_name_stand_ins_silence_the_sound_pass_unrendered_time_and_detector_misses(world):
    led = X.explain("xpBBB2")
    unknown = _by_label(led, "unknown")
    text = "\n".join(c["claim"] for c in unknown)
    assert "0123456789abcdef0123456789abcdef.png" in text and "stand-in" in text
    assert "silence" in text.lower()
    assert "Sound pass" in text and "never" in text
    assert re.search(r"never rendered", text), text
    assert "not detected by dissect v1" in text
    assert not re.search(r"\babsent\b", text), "a detector that found nothing does not prove absence"
    missing = [c for c in unknown if "not detected by dissect v1" in c["claim"]]
    assert all("search" in c["boundary"].lower() or "searched" in c["boundary"].lower() for c in missing)
    # stand-ins are tied to the pass and channel the configuration declares
    grain = next(c for c in unknown if "0123456789abcdef0123456789abcdef.png" in c["claim"])
    assert "Buffer A" in grain["claim"] and "iChannel1" in grain["claim"]


def test_time_never_rendered_is_bounded_by_what_the_receipts_cover(world):
    led_a = X.explain("xpAAA1")
    unk_a = "\n".join(c["claim"] for c in _by_label(led_a, "unknown"))
    assert "t > 8" in unk_a, unk_a                     # the filmstrip ran to 8 s
    led_b = X.explain("xpBBB2")
    unk_b = "\n".join(c["claim"] for c in _by_label(led_b, "unknown"))
    assert "t > 4" in unk_b and "between" in unk_b     # two stills, no filmstrip


def test_no_receipt_means_never_rendered_and_the_look_question_stays_open(world):
    for f in (world["renders"] / "xpAAA1").iterdir():
        f.unlink()
    led = X.explain("xpAAA1")
    assert not _by_label(led, "observed-in-render") and not _by_label(led, "measured")
    assert any("never rendered" in c["claim"] for c in _by_label(led, "unknown"))
    look = next(q for q in led["checklist"] if q["key"] == "look")
    assert look["status"] == "unresolved"


def test_the_route_rules_travel_with_the_ledger(world):
    single = {r["route"]: r for r in X.explain("xpAAA1")["route"]}
    assert "single-pass" in single and "jump" in single["single-pass"]["rule"]
    multi = {r["route"]: r for r in X.explain("xpBBB2")["route"]}
    assert {"buffer feedback", "sound pass", "texture inputs", "audio-reactive"} <= set(multi)
    assert "walk from a reset" in multi["buffer feedback"]["rule"] and "never jump" in multi["buffer feedback"]["rule"]
    assert "compile" in multi["sound pass"]["rule"]
    assert "silence" in multi["audio-reactive"]["rule"]
    for r in multi.values():
        assert r["evidence"], r


def test_a_jumped_still_of_a_feedback_shader_is_flagged(world):
    d = world["renders"] / "xpBBB2"
    _receipt(d, "receipt", "arsenal.shader-render/v1", (1.0, 4.0), history=False)
    led = X.explain("xpBBB2")
    assert any("jump" in c["claim"] and "feedback" in c["claim"] for c in _by_label(led, "unknown"))


def test_the_checklist_is_revisited_with_honest_statuses(world):
    led = X.explain("xpBBB2")
    keys = {q["key"]: q for q in led["checklist"]}
    assert {"made_of", "wiring", "look", "motion", "cost", "intent", "sound"} <= set(keys)
    assert all(q["status"] in ("answered", "partial", "unresolved") for q in keys.values())
    assert keys["cost"]["status"] != "answered", "SwiftShader cannot answer GPU cost"
    assert keys["sound"]["status"] == "unresolved"
    assert keys["look"]["status"] == "partial", "a picture drawn with a stand-in is not quite the shader"
    assert keys["intent"]["status"] == "unresolved"
    a = {q["key"]: q for q in X.explain("xpAAA1")["checklist"]}
    assert a["intent"]["status"] == "partial" and a["made_of"]["status"] == "answered"
    assert a["look"]["status"] == "answered" and a["motion"]["status"] == "answered"
    assert "sound" not in a, "no audio question for a shader with no audio"


def _cost_question(sid: str) -> dict:
    return next(q for q in X.explain(sid)["checklist"] if q["key"] == "cost")


def test_the_cost_question_names_only_the_answers_the_claims_hold(world):
    """The cost line was one template whatever the ledger held: 'a static estimate and SwiftShader timing; GPU timing is
    unknown'. 290 corpus shaders have no timing claim, and for fsXXzX (no entry point in any pass, never rendered) it
    opened by naming a static estimate that does not exist. Now it names what the claims hold; with neither an estimate
    nor a timing there is no answer at all, so the question is unresolved."""
    C.save_shader(_shader("xpZZZ1", "Built Untimed", [
        _rp("Common", "common", COMMON_BUILDS),
        _rp("Buffer A", "buffer", "BUFFERA\n", [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", "IMAGE\n", [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]),
        world["corpus"])
    q = _cost_question("xpZZZ1")
    assert q["status"] == "unresolved", q
    assert not q["because"].startswith("a static estimate") and "SwiftShader timing" not in q["because"], q
    assert "no static estimate for 2 pass(es) with no entry point found" in q["because"], q
    assert "GPU timing is unknown" in q["because"], q
    C.save_shader(_shader("xpZZZ2", "Untimed", [_rp("Image", "image", CLOCK_ONLY, [], [{"id": OUT_IMG, "channel": 0}])]),
                  world["corpus"])
    q = _cost_question("xpZZZ2")
    assert q["status"] == "partial" and q["because"].startswith("a static estimate; "), q
    assert "SwiftShader timing" not in q["because"], q
    q = _cost_question("xpAAA1")                       # an estimate and a timed receipt: both are named
    assert q["status"] == "partial" and q["because"].startswith("a static estimate and SwiftShader timing; "), q


@pytest.mark.parametrize("trouble", ["unsupported", "flat"])
def test_look_and_motion_are_never_answered_while_the_runtime_could_not_draw_everything(world, trouble):
    """Before this pin a receipt listing an input drawn black and a pass never run still gave look "answered, every
    input fed"; and motion stayed "answered" over a flat frame. Both are partial now, with the reason said."""
    d = world["renders"] / "xpAAA1"
    if trouble == "unsupported":
        _receipt(d, "receipt", "arsenal.shader-render/v1", (1.0, 4.0),
                 unsupported=[{"what": "input", "name": "Image", "type": "keyboard", "channel": 0,
                               "reason": "unknown input type: black"},
                              {"what": "pass", "name": "Buffer E", "type": "buffer",
                               "reason": "unknown pass type or buffer name"}])
    else:
        _receipt(d, "filmstrip", "arsenal.shader-filmstrip/v1", [i * 8.0 / 7 for i in range(8)], flat=True)
    led = X.explain("xpAAA1")
    keys = {q["key"]: q for q in led["checklist"]}
    assert keys["look"]["status"] == "partial", keys["look"]
    assert keys["motion"]["status"] == "partial", keys["motion"]
    if trouble == "unsupported":
        rows = [c for c in led["claims"] if c.get("kind") == "unsupported"]
        assert len(rows) == 2 and all(c["label"] == "unknown" for c in rows), rows
        assert {c["id"] for c in rows} <= set(keys["look"]["claims"]) & set(keys["motion"]["claims"])
        assert "every input fed" not in keys["look"]["because"]
        assert "support" in keys["look"]["because"] and "support" in keys["motion"]["because"]
    else:
        assert "flat" in keys["motion"]["because"]


def test_motion_is_partial_when_a_feedback_shader_was_reached_by_a_jump(world):
    """A filmstrip of a shader that keeps a frame, drawn by jumping to each t, is not the author's motion."""
    keep = TRAIL.replace(" * ease(0.5)", "").replace("texture(iChannel1, px / iResolution.xy)", "vec4(0.5)")
    C.save_shader(_shader("xpGGG7", "Kept Frame", [
        _rp("Buffer A", "buffer", keep, [_inp(0, "buffer", OUT_A)], [{"id": OUT_A, "channel": 0}]),
        _rp("Image", "image", PASS_ON, [_inp(0, "buffer", OUT_A)], [{"id": OUT_IMG, "channel": 0}])]), world["corpus"])
    d = world["renders"] / "xpGGG7"
    d.mkdir(parents=True)
    _receipt(d, "filmstrip", "arsenal.shader-filmstrip/v1", [i * 8.0 / 7 for i in range(8)], history=False)
    led = X.explain("xpGGG7")
    assert [c for c in led["claims"] if c.get("kind") == "jump_conflict"]
    motion = next(q for q in led["checklist"] if q["key"] == "motion")
    assert motion["status"] == "partial" and "jump" in motion["because"], motion


# ------------------------------------------------------------------------------------------------ the cache
def test_a_repeat_with_unchanged_inputs_returns_the_cached_ledger_and_says_so(world, monkeypatch):
    first = X.explain("xpAAA1")
    assert first["cached"] is False

    def boom(*a, **k):
        raise AssertionError("the dissector ran again on unchanged inputs")
    monkeypatch.setattr(D, "dissect_view", boom)
    again = X.explain("xpAAA1")
    assert again["cached"] is True
    assert again["claims"] == first["claims"] and again["cache"]["key"] == first["cache"]["key"]
    assert "cached" in X.summary(again).lower() and "unchanged" in X.summary(again).lower()


# each input a ledger is made from: (what changes, the shader it changes for, the cache-key entry that must move)
CHANGES = {
    "pass": ("xpAAA1", "passes"), "config": ("xpAAA1", "config"), "meta": ("xpAAA1", "meta"),
    "media": ("xpBBB2", "media"), "receipt": ("xpAAA1", "receipts"), "filmstrip": ("xpAAA1", "receipts"),
    "receipt_removed": ("xpAAA1", "receipts"), "study": ("xpAAA1", "study"),
    "corroboration": ("xpAAA1", "corroboration"), "dissect_version": ("xpAAA1", "dissect"),
    "dissect_code": ("xpAAA1", "dissect"), "explain_code": ("xpAAA1", "explain"), "min_conf": ("xpAAA1", "min_conf"),
}


def test_the_code_hash_covers_every_module_the_ledger_is_computed_by():
    """The dissector (dissect.py, glsl.py) and the readers explain leans on: shelf.py (study_facts, licence_for) and
    corpus.py (pass_stem, _input_row). Before: shelf.py and corpus.py were outside the key."""
    assert {p.name for p in X.CODE["dissect"]} >= {"dissect.py", "glsl.py"}
    assert {p.name for p in X.CODE["explain"]} >= {"explain.py", "shelf.py", "corpus.py"}
    assert all(Path(p).is_file() for paths in X.CODE.values() for p in paths)


@pytest.mark.parametrize("change", sorted(CHANGES))
def test_a_changed_input_is_analysed_afresh(world, change, monkeypatch, tmp_path):
    """Change each input once; the cache must notice. Before this pin a new media file and an edited meta.json (its
    licence reading) came back `cached: True` with the old licence and the old "does not hold this file"."""
    sid, entry = CHANGES[change]
    shader_dir = world["corpus"] / "shaders" / sid
    if change in ("dissect_code", "explain_code"):          # point the code hash at copies we are free to edit
        key = "dissect" if change == "dissect_code" else "explain"
        copies = []
        for p in X.CODE[key]:
            copies.append(tmp_path / p.name)
            copies[-1].write_bytes(Path(p).read_bytes())
        monkeypatch.setitem(X.CODE, key, tuple(copies))
    first = X.explain(sid)
    assert first["cached"] is False and X.explain(sid)["cached"] is True
    min_conf = D.MIN_CONF
    if change == "pass":
        changed = json.loads(json.dumps(SINGLE))
        changed["renderpass"][0]["code"] = LANTERN.replace("0.4545", "0.4546")
        C.save_shader(changed, world["corpus"])
    elif change == "config":                                # shader.json alone; the pass files and meta.json untouched
        p = shader_dir / "shader.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        data["info"]["description"] = "a new description"
        p.write_text(json.dumps(data), encoding="utf-8")
    elif change == "meta":
        p = shader_dir / "meta.json"
        meta = json.loads(p.read_text(encoding="utf-8"))
        meta["name"] = "Paper Lantern Renamed"
        meta["license"] = {"license": "all-rights-reserved", "explicit": True, "line": "all rights reserved"}
        p.write_text(json.dumps(meta), encoding="utf-8")
    elif change == "media":
        m = world["corpus"] / "media" / Path(GRAIN_SRC).name
        m.parent.mkdir(parents=True, exist_ok=True)
        m.write_bytes(b"our own bytes, standing in for a picture")
    elif change in ("receipt", "filmstrip"):
        p = world["renders"] / sid / f"{'receipt' if change == 'receipt' else 'filmstrip'}.json"
        rec = json.loads(p.read_text(encoding="utf-8"))
        rec["frames"][0]["mean_luma"] = 99.0
        p.write_text(json.dumps(rec), encoding="utf-8")
    elif change == "receipt_removed":
        (world["renders"] / sid / "filmstrip.json").unlink()
    elif change == "study":                                 # outside the corroboration section
        (world["study"] / f"{sid}.md").write_text(NOTE.replace("words of our own", "other words of our own"),
                                                  encoding="utf-8", newline="\n")
    elif change == "corroboration":                         # inside it, nothing else
        (world["study"] / f"{sid}.md").write_text(NOTE + "- The halo is wider than the note says.\n",
                                                  encoding="utf-8", newline="\n")
    elif change == "dissect_version":
        monkeypatch.setattr(D, "API", "arsenal.shader-dissect/v2")
    elif change in ("dissect_code", "explain_code"):
        target = X.CODE["dissect" if change == "dissect_code" else "explain"][-1]
        target.write_bytes(target.read_bytes() + b"\n# a fix\n")
    elif change == "min_conf":
        min_conf = 0.6
    again = X.explain(sid, min_conf=min_conf)
    assert again["cached"] is False and again["cache"]["key"] != first["cache"]["key"], change
    assert again["cache"]["inputs"][entry] != first["cache"]["inputs"][entry], (change, entry)
    moved = {k for k in first["cache"]["inputs"] if again["cache"]["inputs"].get(k) != first["cache"]["inputs"][k]}
    if change == "study":
        assert "corroboration" not in moved, "an edit outside the section leaves its own hash alone"
    if change == "meta":
        assert again["licence"] == "all-rights-reserved" != first["licence"] and again["name"] == "Paper Lantern Renamed"
    if change == "media":
        held = [c["claim"] for c in again["claims"] if c.get("kind") == "media" and Path(GRAIN_SRC).name in c["claim"]]
        assert held and "holds" in held[0] and "does not hold" not in held[0], held
    if change == "corroboration":
        assert "study" in moved and "corroboration" in moved
    assert X.explain(sid, min_conf=min_conf)["cached"] is True, "and the new ledger is itself cached"


# ------------------------------------------------------------------------------------------------ the door
def test_the_verb_is_registered_and_prints_the_summary_first(world, capsys):
    cli._load_extensions()
    assert "explain" in cli.VERBS
    assert cli.main(["explain", "xpAAA1"]) == 0
    out = capsys.readouterr().out
    first = out.strip().splitlines()[0]
    assert "xpAAA1" in first
    assert re.search(r"claims?\s*:?\s*\d+", out) and "unknown" in out and "checklist" in out.lower()
    assert "ledger" in out.lower()
    assert cli.main(["explain", "xpAAA1", "--detail", "full"]) == 0
    full = capsys.readouterr().out
    assert full.strip().splitlines()[0].split("[")[0].rstrip() == first.split("[")[0].rstrip(), \
        "full detail still opens with the summary"
    study_41 = re.compile(r"study:xpAAA1@[0-9a-f]{8}#4\.1\b")
    assert study_41.search(full) and not study_41.search(out)
    assert len(full.splitlines()) > len(out.splitlines())
    assert cli.main(["explain", "xpAAA1", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["id"] == "xpAAA1" and data["cached"] is True
    assert cli.main(["explain", "no-such-shader"]) == 2


def test_an_ambiguous_name_is_refused_not_chosen(world, capsys):
    """Never choose an example on the user's behalf: two shaders match 'e', so the verb names both and stops."""
    cli._load_extensions()
    assert cli.main(["explain", "e"]) == 2          # "Echo Pool" and "Paper Lantern" both contain an "e"
    err = capsys.readouterr().err
    assert "xpAAA1" in err and "xpBBB2" in err


def test_the_cli_load_list_names_explain():
    import inspect
    assert '"explain"' in inspect.getsource(cli._load_extensions)
