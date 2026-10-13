"""Pins for the licence line (arsenal/shaders/licence_line.py): no file git would commit shares a run of 12 normalised
tokens with any pass of any shader in the private corpus, except breaches declared in the baseline as pre-existing at
commit 9d6f29ff, which are still measured and reported as 'baseline' and may only shrink.

WHY THIS EXISTS. The corpus under state/arsenal/shaders/corpus/ is other people's code, most of it CC BY-NC-SA, and this
repository is public under Apache-2.0. "Techniques transfer, code does not" was kept by memory until tonight. The
reconciled build spec (research/in-flight/shader-school-2026-10-13/build-spec-reconciled.md, rulings 2 and 8) licenses
the house library Apache-2.0 on the strength of this test and forbids corpus code in any tracked file, so the test has to
be one that can fail.

HOW A GREEN STAYS HONEST. Every fixture written in this file is synthetic and is itself scanned against the real corpus
(this file is committable, so it is in scope). The real corpus is never copied into this file and never printed; the
calibration plants real corpus lines in every shape that matters, in a folder under state/ that is removed afterwards,
and proves the real scanner catches each one before the real-tree test believes its own result. Exempt hits (a bare
function signature, a declared textbook idiom) and baselined hits are still reported, never hidden.

SCOPE (judge's ruling a, 2026-10-13): every file git would commit, which is `git ls-files` plus the untracked files that
are not ignored, minus the top-level state/ folder (whose committed files are listed every run, and one under the corpus
folder fails the scan); every file is read whatever its extension, in UTF-32 or UTF-16 (by its byte-order mark), UTF-8
or cp1252, a binary file's printable text is read too, and a file that cannot be read fails the scan. Each file is read
three ways: without comments, with them, and with block comments read as code (a `/*` inside a quoted glob opens a
false comment that would otherwise hide the rest of the file).
"""
from __future__ import annotations

import codecs
import importlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CORPUS_ROOT = REPO / "state" / "arsenal" / "shaders" / "corpus"
ALLOW = REPO / "arsenal" / "shaders" / "licence_line_allow.json"
BASELINE = REPO / "arsenal" / "shaders" / "licence_line_baseline.json"
# Real corpus text may be written only under state/ (gitignored); the calibration plants its copies here and removes them.
CALIBRATION_HOME = REPO / "state" / "arsenal" / "shaders" / "licence-line-calibration"


def LL():
    """The module under test, imported per test so a missing mechanism fails each pin by name."""
    return importlib.import_module("arsenal.shaders.licence_line")


# A synthetic "corpus shader", written for this file. Line numbers matter to the pins below.
SYNTH = """// Synthetic fixture for the licence-line pins, written for this test file; it quotes no real shader.
// Licensed under Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
float ribbonField(vec3 p, vec3 a, vec3 b, float r, float k)
{
    vec3 d = abs(p - a) - b;
    return dot(d, vec3(0.3, 0.6, 0.1)) * k - r;
}
float zigzagWeave(vec2 q, float k)
{
    vec2 g = fract(q * k) - 0.5;
    float w = abs(g.x * 3.25 - g.y * 1.75) + sin(q.y * 7.0 + q.x * 2.0) * 0.125;
    return smoothstep(0.02, 0.0, w - 0.3);
}
void mainImage(out vec4 tint, in vec2 px)
{
    vec2 st = px / iResolution.yy;
    tint = vec4(vec3(zigzagWeave(st, 9.0)), 1.0);
}
"""
WEAVE_LINE = 11  # the line of SYNTH that the copies below take from
WEAVE = "float w = abs(g.x * 3.25 - g.y * 1.75) + sin(q.y * 7.0 + q.x * 2.0) * 0.125;"
# A second synthetic shader, so a pin can tell one corpus id from another.
SYNTH2 = """void mainImage(out vec4 tint, in vec2 px)
{
    float braid = cos(px.x * 0.031 + px.y * 0.047) * 2.5 - sin(px.y * 0.013) * 4.25;
    tint = vec4(braid);
}
"""
BRAID = "float braid = cos(px.x * 0.031 + px.y * 0.047) * 2.5 - sin(px.y * 0.013) * 4.25;"


def plant(tmp_path, house, corpus=None, allow=None):
    """A synthetic repo root, corpus and allowlist under tmp_path. Returns (root, corpus_root, allow_path)."""
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    for rel, text in house.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            p.write_bytes(text)
        else:
            p.write_text(text, encoding="utf-8", newline="\n")
    corpus_root = tmp_path / "corpus"
    for sid, passes in (corpus or {"Synth1": {"image.glsl": SYNTH}}).items():
        d = corpus_root / "shaders" / sid
        d.mkdir(parents=True, exist_ok=True)
        for fname, text in passes.items():
            (d / fname).write_text(text, encoding="utf-8", newline="\n")
    allow_path = tmp_path / "allow.json"
    allow_path.write_text(json.dumps({"api": "arsenal.licence-line-allow/v1", "entries": allow or []}),
                          encoding="utf-8", newline="\n")
    return root, corpus_root, allow_path


def scan_planted(tmp_path, house, baseline=None, old=None, **kw):
    """Scan a planted tree. `baseline` (a list of entries) is written beside it; `old` maps a path to its text at the
    baseline commit (absent: the file did not exist then), standing in for git in a tree that is not a repository."""
    root, corpus_root, allow_path = plant(tmp_path, house, **kw)
    extra = {}
    if baseline is not None:
        bpath = tmp_path / "baseline.json"
        bpath.write_text(json.dumps({"api": "arsenal.licence-line-baseline/v1", "commit": "9d6f29ff",
                                     "entries": baseline}), encoding="utf-8", newline="\n")
        extra["baseline_path"] = bpath
        if old is not None:
            extra["at_commit"] = lambda rels: {r: old.get(r) for r in rels}
    return LL().scan(root=root, corpus=corpus_root, allow_path=allow_path, **extra)


def breaches(report):
    return [h for h in report["hits"] if not h["exempt"] and h.get("verdict", "breach") == "breach"]


def caught_files(report):
    return {h["file"] for h in breaches(report)}


# ---------- the scanner catches what it must ----------

def test_a_reformatted_copy_inside_a_js_string_is_caught_with_its_line_and_corpus_id(tmp_path):
    house = {"arsenal/web/thing.js": (
        "// a house page that pastes a corpus line into a JS string, reformatted\n"
        "const FRAG = `\n"
        "  float w=abs(g.x*3.25-g.y*1.75)+sin(q.y*7.+q.x*2.)*.125;\n"
        "`;\n")}
    report = scan_planted(tmp_path, house)
    assert report["status"] == "breach"
    [hit] = breaches(report)
    assert hit["file"] == "arsenal/web/thing.js"
    assert (hit["line"], hit["end_line"]) == (3, 3)
    assert hit["corpus"] == ["Synth1"]
    assert hit["corpus_first"] == {"id": "Synth1", "pass": "image", "line": WEAVE_LINE}
    assert hit["tokens"] >= 12


@pytest.mark.parametrize("js", [
    # Each splits an 18-token copy into two 9-token halves, so only reading the string as GLSL can join them.
    'const F = "g.x * 3.25 - g.y" +\n  "* 1.75) + sin(q.y";\n',          # concatenated pieces
    "const F = ['g.x * 3.25 - g.y',\n  '* 1.75) + sin(q.y'].join('');\n",  # an array of lines
    "const F = 'g.x * 3.25 - g.y\\n* 1.75) + sin(q.y';\n",                # one string with a \\n escape
])
def test_glsl_held_in_js_strings_is_read_as_glsl(tmp_path, js):
    assert breaches(scan_planted(tmp_path, {"scripts/pieces.js": js}))


@pytest.mark.parametrize("text,caught", [
    ("vec3 g = fract(q * k) - 0.5; int", False),   # 11 shared tokens: g = fract ( q * k ) - 0.5 ;
    ("vec2 g = fract(q * k) - 0.5; int", True),    # 12 shared tokens: the run length is the line
])
def test_eleven_shared_tokens_pass_and_twelve_are_caught(tmp_path, text, caught):
    report = scan_planted(tmp_path, {"design/edge.glsl": text + "\n"})
    assert bool(breaches(report)) is caught, report["hits"]


def test_a_copy_pasted_inside_a_comment_is_still_caught(tmp_path):
    house = {"design/old.glsl": "#define KEEP 1\n// " + WEAVE + "\n"}
    [hit] = breaches(scan_planted(tmp_path, house))
    assert hit["line"] == 2


def test_a_copy_split_by_an_inserted_comment_is_still_caught(tmp_path):
    house = {"scripts/split.glsl":
             "float w = abs(g.x * 3.25 /* ours now */ - g.y * 1.75) + sin(q.y * 7.0 + q.x * 2.0) * 0.125;\n"}
    assert breaches(scan_planted(tmp_path, house))


def test_numbers_are_kept_but_their_spelling_is_normalised(tmp_path):
    ll = LL()
    assert [ll.norm_number(s) for s in ("1.", ".5", "0.50", "1e1", "0x10", "2u", "3")] == \
        ["1.0", "0.5", "0.5", "10.0", "16", "2u", "3"]
    respelled = {"design/a.glsl": "float w = abs(g.x * 3.250 - g.y * 1.75) + sin(q.y * 7. + q.x * 2.) * .125;\n"}
    assert breaches(scan_planted(tmp_path / "a", respelled))
    # Numbers carry the craft: the same shape with new constants is a different line, not a copy.
    new_constants = {"design/b.glsl": "float w = abs(g.x * 3.5 - g.y * 1.5) + sin(q.y * 6.0 + q.x * 2.5) * 0.25;\n"}
    assert not breaches(scan_planted(tmp_path / "b", new_constants))


def test_a_licence_sentence_that_lives_in_a_corpus_comment_is_not_corpus_code(tmp_path):
    house = {"design/notes.glsl":
             "// Licensed under Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.\n"
             "float ours = 2.0;\n"}
    report = scan_planted(tmp_path, house)
    assert report["hits"] == [] and report["status"] == "clean"


# ---------- defect 4 (review 2026-10-13): a // comment inside a one-line string ----------

# Three short commented lines: no single line reaches 12 tokens, so only reading the lines as lines can catch them.
COMMENTED = ("void mainImage(out vec4 tint, in vec2 px)\n{\n"
             "    vec2 cell = fract(px * 0.37);   // cell\n"
             "    float ring = length(cell) * 2.75;       // ring\n"
             "    float edge = step(ring, 0.4); // edge\n"
             "    tint = vec4(vec3(edge), 1.0);\n}\n")
COMMENTED_BODY = "\n".join(COMMENTED.split("\n")[2:5]) + "\n"


@pytest.mark.parametrize("rel,form", [
    ("design/multi.glsl", lambda b: b),
    ("arsenal/web/template.js", lambda b: "const S = `\n" + b + "`;\n"),
    ("arsenal/web/oneline.js", lambda b: "const S = " + json.dumps(b) + ";\n"),
    ("design/oneline.json", lambda b: json.dumps({"frag": b}) + "\n"),
])
def test_a_line_comment_inside_a_one_line_string_ends_at_the_escaped_line_break(tmp_path, rel, form):
    report = scan_planted(tmp_path, {rel: form(COMMENTED_BODY)}, corpus={"Mine2": {"image.glsl": COMMENTED}})
    assert rel in caught_files(report), report["hits"]


def test_a_hit_inside_a_one_line_string_reports_its_physical_line(tmp_path):
    """An escaped line break ends a // comment but is not a line of the file: the report names the line an editor
    shows, not the line of the GLSL held in the string."""
    house = {"arsenal/web/lines.js": "// one\n// two\nconst S = \"int a;\\nint b;\\n" + WEAVE + "\\n\";\n"}
    [hit] = breaches(scan_planted(tmp_path, house))
    assert (hit["line"], hit["end_line"]) == (3, 3)


# ---------- re-review 2 (2026-10-13): a block-comment opener inside a quoted span ----------

@pytest.mark.parametrize("rel,form", [
    # A backticked glob in a note, then the copy in a fence: the `/*` of the glob opens no comment.
    ("docs/globbed.md", lambda b: "Sketches live in `design/*.frag`.\n\n```glsl\n" + b + "```\n"),
    ("arsenal/web/picker.js", lambda b: 'input.accept = "audio/*";\nconst S = `\n' + b + "`;\n"),
    ("arsenal/web/mime.js", lambda b: "const any = '*/*';\nconst S = `\n" + b + "`;\n"),
    ("scripts/lib.py", lambda b: "GLOB = 'lib/*'\nS = '''\n" + b + "'''\n"),
])
def test_a_block_comment_opener_inside_a_quoted_span_does_not_hide_the_rest_of_the_file(tmp_path, rel, form):
    """The comment reader cannot see quotes, so `/*` in a glob or a MIME type opened a false block comment that ran to
    the end of the file: the code reading lost the copy and the full reading mixed its // prose into it. The third
    reading (every // dropped to the end of its line, the block markers blanked) still reads it as code."""
    report = scan_planted(tmp_path, {rel: form(COMMENTED_BODY)}, corpus={"Mine2": {"image.glsl": COMMENTED}})
    assert rel in caught_files(report), report["hits"]
    [hit] = breaches(report)
    body_line = form(COMMENTED_BODY).split("\n").index(COMMENTED_BODY.split("\n")[0]) + 1
    assert hit["line"] == body_line and "bare" in hit["modes"]


def test_many_line_comments_on_one_line_do_not_crash_the_scanner(tmp_path):
    """Each // inside a comment used to add a level of recursion; a few hundred on one line took the scan down."""
    house = {"design/slashes.glsl": "float x = 1.0; " + "// note " * 5000 + "\n",
             "arsenal/web/escaped.js": "const S = " + json.dumps("float y = 2.0; // a // b // c\n" * 2000) + ";\n"}
    report = scan_planted(tmp_path, house)
    assert report["status"] == "clean" and report["scanned"]["files"] == 2


# ---------- defect 6: commented-out corpus code is corpus code ----------

def test_commented_out_corpus_code_is_caught_when_a_house_file_uncomments_it(tmp_path):
    corpus = {"Ghost1": {"image.glsl": "void mainImage(out vec4 tint, in vec2 px)\n{\n"
                                       "    // float keep = dot(px, vec2(0.71, 0.29)) * 13.5 + 0.875;\n"
                                       "    tint = vec4(px.x);\n}\n"}}
    house = {"design/ghost.glsl": "float keep = dot(px, vec2(0.71, 0.29)) * 13.5 + 0.875;\n"}
    report = scan_planted(tmp_path, house, corpus=corpus)
    assert caught_files(report) == {"design/ghost.glsl"}


def test_a_banner_comment_beside_code_is_not_commented_out_code(tmp_path):
    """A `// =====` banner lexes as a run of `==`; beside a live `;` it once looked like code and flagged dozens of house
    test files whose only shared text was `; }` and a banner. Code shape is judged on the comment's own tokens."""
    corpus = {"Banner1": {"image.glsl": "void mainImage(out vec4 tint, in vec2 px)\n{\n    tint = vec4(px.x);\n}\n"
                                        "// " + "=" * 60 + "\nfloat other(float v) { return v * 0.5; }\n"}}
    house = {"tests/banner.test.mjs": "check(a, b);\n}\n\n// " + "=" * 70 + " settings\n"}
    assert scan_planted(tmp_path, house, corpus=corpus)["hits"] == []


def test_comparisons_in_a_corpus_comment_do_not_make_it_code(tmp_path):
    """The other half of the rule: `==` is a comparison, not an assignment, so a comment of parenthesised comparisons
    (one of the three code marks, not two) is not indexed as commented-out code."""
    corpus = {"Compare1": {"image.glsl": "void mainImage(out vec4 tint, in vec2 px)\n{\n"
                                         "    // keep (tint.x == px.y) and (px.x == tint.y) or (px.y == 0.5)\n"
                                         "    tint = vec4(px.x);\n}\n"}}
    house = {"docs/compare.md": "keep (tint.x == px.y) and (px.x == tint.y) or (px.y == 0.5)\n"}
    assert scan_planted(tmp_path, house, corpus=corpus)["hits"] == []


def test_a_prose_comment_in_the_corpus_is_still_not_indexed(tmp_path):
    corpus = {"Prose1": {"image.glsl": "// This shader draws a soft ring of light that breathes slowly over time, "
                                       "inspired by a lamp seen through fog on a winter night in the old town.\n"
                                       "void mainImage(out vec4 tint, in vec2 px) { tint = vec4(0.0); }\n"}}
    house = {"docs/notes.md": "This shader draws a soft ring of light that breathes slowly over time, inspired by a "
                              "lamp seen through fog on a winter night in the old town.\n"}
    assert scan_planted(tmp_path, house, corpus=corpus)["hits"] == []


# ---------- exemptions are declared, measured and reported, never hidden ----------

def test_a_bare_function_signature_is_reported_exempt_and_does_not_fail(tmp_path):
    house = {"arsenal/web/glsl/sdf/ribbon.glsl":
             "float ribbonField(vec3 p, vec3 a, vec3 b, float r, float k)\n"
             "{\n"
             "    return dot(p, a) + dot(b, vec3(r, k, 1.0));\n"
             "}\n"}
    report = scan_planted(tmp_path, house)
    assert report["status"] == "clean"
    [hit] = report["hits"]
    assert hit["exempt"] is True and hit["reasons"] == ["signature"]
    assert (hit["line"], hit["end_line"]) == (1, 2)


def test_a_signature_that_runs_on_into_a_copied_body_is_a_breach(tmp_path):
    house = {"arsenal/web/glsl/sdf/ribbon.glsl":
             "float ribbonField(vec3 p, vec3 a, vec3 b, float r, float k)\n"
             "{\n"
             "    vec3 d = abs(p - a) - b;\n"
             "    float e = 0.0;\n"
             "}\n"}
    report = scan_planted(tmp_path, house)
    assert report["status"] == "breach"
    [hit] = breaches(report)
    assert (hit["line"], hit["end_line"]) == (1, 3)


def test_a_call_with_the_same_tokens_as_a_signature_is_not_a_signature():
    ll = LL()
    toks = ll.streams("float d = ribbonField(p, a, b, r, k); vec3 f(vec3 p, float k) { return p * k; }")["code"]
    spans = [(toks[s].text, toks[e].text) for s, e in ll.signature_spans(toks)]
    assert spans == [("vec3", "{")]


def test_a_bare_loop_header_is_measured_by_shape_and_exempt_but_a_loop_body_is_not(tmp_path):
    """A counted loop header from initialiser to brace is exactly 12 tokens in every C-family file. The judge ruled it
    common tongue (2026-10-13), like a signature: still measured and reported, exempt with the reason "loop header".
    A run that carries on past the brace into the loop's body is code, and stays a breach."""
    corpus = {"Loop1": {"image.glsl": "void mainImage(out vec4 hue, in vec2 at) {\n    float acc = 0.25;\n"
                                      "    for (int j = 0; j < 37; j++) {\n        acc += float(j) * 0.5;\n    }\n"
                                      "    hue = vec4(acc);\n}\n"}}
    house = {"arsenal/web/count.js": "function f(n) {\n  let t = 0;\n  for (let j = 0; j < 37; j++) {\n"
                                     "    t += j * n;\n  }\n}\n"}
    report = scan_planted(tmp_path / "header", house, corpus=corpus)
    [hit] = report["hits"]
    assert hit["shape"] == "loop-header" and hit["exempt"] is True and hit["line"] == 3
    assert hit["reasons"] == ["loop header"] and report["status"] == "clean"
    body = {"arsenal/web/count.glsl": "float g() {\n    float acc = 0.25;\n    for (int j = 0; j < 37; j++) {\n"
                                      "        acc += float(j) * 0.5;\n    }\n    return acc;\n}\n"}
    report = scan_planted(tmp_path / "body", body, corpus=corpus)
    assert report["status"] == "breach" and any(h["shape"] == "code" for h in report["hits"])


def test_an_allowlisted_idiom_is_reported_exempt_with_its_source(tmp_path):
    entry = {"text": "vec2 g = fract(q * k) - 0.5;", "reason": "the cell-local coordinate every grid starts from",
             "source": "synthetic source for this test", "date": "2026-10-13"}
    report = scan_planted(tmp_path, {"design/grid.glsl": "vec2 g = fract(q * k) - 0.5; int\n"}, allow=[entry])
    assert report["status"] == "clean"
    [hit] = report["hits"]
    assert hit["exempt"] is True and hit["reasons"] == ["allowlist: synthetic source for this test"]


@pytest.mark.parametrize("missing", ["text", "reason", "source", "date"])
def test_an_allow_entry_missing_a_field_is_refused(tmp_path, missing):
    entry = {"text": "vec2 g = fract(q * k) - 0.5;", "reason": "r", "source": "s", "date": "2026-10-13"}
    del entry[missing]
    p = tmp_path / "allow.json"
    p.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
    with pytest.raises(ValueError, match=missing):
        LL().load_allow(p)


@pytest.mark.parametrize("bad,why", [
    ("vec2 g = fract(q * k) - 0.5;", "object"),                                      # a bare string, not an entry
    ({"text": "vec2 g = fract(q * k) - 0.5;\nfloat w = g.x;"}, "one line"),          # spans two lines
    ({"text": " + ".join(f"a{i}" for i in range(25)) + ";"}, "40 tokens"),          # 50 tokens on one line
])
def test_an_allow_entry_must_be_one_short_line_and_an_object(tmp_path, bad, why):
    """Defect 8: one entry must not be able to exempt a whole shader, and a malformed entry is refused by name."""
    if isinstance(bad, dict):
        bad = dict({"reason": "r", "source": "s", "date": "2026-10-13"}, **bad)
    p = tmp_path / "allow.json"
    p.write_text(json.dumps({"entries": [bad]}), encoding="utf-8")
    with pytest.raises(ValueError, match=why):
        LL().load_allow(p)


def test_the_shipped_allowlist_is_well_formed():
    data = json.loads(ALLOW.read_text(encoding="utf-8"))
    assert data.get("why"), "the allowlist says why it exists"
    for entry in LL().load_allow(ALLOW):
        assert entry["reason"] and entry["source"] and entry["date"]


# The one declared idiom (ruling d): the sine-fract hash over the pixel coordinate, as the shipped allowlist spells it.
HASH = "fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);"
# Ruled 2026-10-13 from the licence triage: the smoothstep cubic, as the Khronos reference page defines it.
SMOOTHSTEP = "x = x * x * (3.0 - 2.0 * x);"


def test_the_shipped_hash_idiom_exempts_the_bare_hash_and_nothing_more(tmp_path):
    """Ruling d: the classic hash constants are a textbook idiom only where the shared run is the hash and nothing else;
    a run that carries on into the code around it is a breach."""
    entries = json.loads(ALLOW.read_text(encoding="utf-8"))["entries"]
    # the exact ruled list: each entry is a claim a reviewer checks, so a new one must change this line on purpose
    assert [e["text"] for e in entries] == [HASH, SMOOTHSTEP]
    corpus = {"Hash1": {"image.glsl": "float pixelDither()\n{\n    return " + HASH + "\n}\n"}}
    bare = {"design/dither.glsl": "float n = " + HASH + "\n"}
    report = scan_planted(tmp_path / "a", bare, corpus=corpus, allow=entries)
    assert report["status"] == "clean" and [h["exempt"] for h in report["hits"]] == [True]
    more = {"design/dither.glsl": "float pixelDither()\n{\n    return " + HASH + "\n}\n"}
    assert scan_planted(tmp_path / "b", more, corpus=corpus, allow=entries)["status"] == "breach"


# ---------- scope: every file git would commit, any type, any encoding ----------

@pytest.mark.parametrize("rel,form", [
    ("tests/test_thing.py", lambda w: 'FRAG = """\n' + w + '\n"""\n'),             # defect 1: tests/ is committed
    ("research/reviewed/x/transcript.md", lambda w: "```glsl\n" + w + "\n```\n"),  # defect 1: so are archives
    (".claude/skills/x/ref.md", lambda w: "    " + w + "\n"),
    ("design/graph.json", lambda w: json.dumps({"code": w}) + "\n"),               # defect 2: any extension
    ("scripts/gen.py", lambda w: 'S = """\n' + w + '\n"""\n'),
    ("arsenal/web/notes.md", lambda w: "```glsl\n" + w + "\n```\n"),
    ("arsenal/web/piano/state/kept.js", lambda w: "const S = `\n" + w + "\n`;\n"),  # defect 5: only the top state/
    ("core/state/x.py", lambda w: 'S = """' + w + '"""\n'),
    ("Makefile", lambda w: "# " + w + "\n"),                                        # no extension at all
])
def test_a_copy_is_caught_in_any_committable_file(tmp_path, rel, form):
    report = scan_planted(tmp_path, {rel: form(WEAVE)})
    assert rel in caught_files(report), report["hits"]


def test_the_top_state_folder_and_git_store_are_never_read(tmp_path):
    house = {"state/arsenal/shaders/corpus/shaders/X/image.glsl": WEAVE + "\n", ".git/objects/x": WEAVE + "\n",
             "design/ours.glsl": "float ours = 2.0;\n"}
    report = scan_planted(tmp_path, house)
    assert report["hits"] == [] and report["scanned"]["files"] == 1


ENC_TEXT = "// © house, déjà vu\n" + WEAVE + "\n"
ENCODED = {
    "cp1252": ENC_TEXT.encode("cp1252"),
    "utf-16": ENC_TEXT.encode("utf-16"),                                   # PowerShell 5.1's -Encoding Unicode
    "utf-16-be-bom": codecs.BOM_UTF16_BE + ENC_TEXT.encode("utf-16-be"),
    "utf-8-sig": ENC_TEXT.encode("utf-8-sig"),
    # Re-review 2: FF FE 00 00 also starts with the UTF-16 mark, and decoding it as UTF-16 put a NUL after every
    # character, so the copy scanned clean as a file that had been read.
    "utf-32-le-bom": codecs.BOM_UTF32_LE + ENC_TEXT.encode("utf-32-le"),  # PowerShell 5.1's -Encoding UTF32
    "utf-32-be-bom": codecs.BOM_UTF32_BE + ENC_TEXT.encode("utf-32-be"),
}


@pytest.mark.parametrize("encoding", sorted(ENCODED))
def test_files_in_other_encodings_are_read(tmp_path, encoding):
    """Defect 3: PowerShell 5.1's Set-Content writes the ANSI code page; a copy must not hide behind one (c) sign."""
    report = scan_planted(tmp_path, {"design/enc.frag": ENCODED[encoding]})
    assert caught_files(report) == {"design/enc.frag"}
    assert report["scanned"]["files"] == 1
    assert [h["line"] for h in breaches(report)] == [2]


@pytest.mark.parametrize("broken", [
    codecs.BOM_UTF16_LE + "float x = 1.0;".encode("utf-16-le") + b"\x00",     # a UTF-16 mark, then an odd byte count
    codecs.BOM_UTF32_LE + "float x = 1.0;".encode("utf-32-le") + b"\x00\x00",  # a UTF-32 mark, then half a unit
    codecs.BOM_UTF16_BE + "float x = 1.0;".encode("utf-32-be"),              # a UTF-16 mark on UTF-32: NULs between
])
def test_an_unreadable_file_fails_the_scan_by_name(tmp_path, broken):
    report = scan_planted(tmp_path, {"design/broken.glsl": broken, "design/ours.glsl": "float ours = 2.0;\n"})
    assert report["status"] == "fail"
    assert [u["file"] for u in report["scanned"]["unreadable"]] == ["design/broken.glsl"]
    assert any("design/broken.glsl" in f for f in report["failures"])


def test_a_binary_file_is_named_and_its_printable_text_is_still_read(tmp_path):
    """Git's rule (a NUL in the first 8000 bytes) decides what is binary; it does not decide what is safe to skip. A
    copy held as plain bytes inside a binary is still a copy, and random bytes hold no 12-token run."""
    import random
    house = {"arsenal/web/glsl/thumb.png": b"\x89PNG\r\n\x1a\n\x00\x00" + WEAVE.encode(),
             "assets/noise.bin": random.Random(7).randbytes(300_000),
             "design/ours.glsl": "float ours = 2.0;\n"}
    report = scan_planted(tmp_path, house)
    assert report["scanned"]["binary_files"] == ["arsenal/web/glsl/thumb.png", "assets/noise.bin"]
    assert report["scanned"]["files"] == 1
    assert caught_files(report) == {"arsenal/web/glsl/thumb.png"}


@pytest.mark.parametrize("form", ["utf-16-le-no-bom", "utf-16-be-no-bom", "stray-nul"])
def test_text_that_git_calls_binary_is_still_read(tmp_path, form):
    """Re-review 2: UTF-16 without its byte-order mark, and a text file with one stray NUL, are binary by git's rule;
    both were counted and never read, so a copy in them scanned clean."""
    text = "// house notes\n" + WEAVE + "\n"
    raw = {"utf-16-le-no-bom": text.encode("utf-16-le"), "utf-16-be-no-bom": text.encode("utf-16-be"),
           "stray-nul": text.encode() + b"\0"}[form]
    report = scan_planted(tmp_path, {"design/odd.frag": raw})
    assert report["scanned"]["binary_files"] == ["design/odd.frag"]
    assert caught_files(report) == {"design/odd.frag"}
    assert [h["line"] for h in breaches(report)] == [2]


def test_the_fast_reading_and_the_exact_reading_agree():
    """The scan reads every file fast (token texts only) and re-reads a file exactly (with lines) only when it shares a
    window; the two readings must be the same tokens, or the fast one could miss what the exact one would catch."""
    ll = LL()
    samples = [SYNTH, COMMENTED, "const S = " + json.dumps(COMMENTED) + ";\n", "a /* b // c */ d // e /* f\ng */ h",
               "x = 'a' + 'b', y = \"c\",\n \"d\"; z = `e` /= 2.; /**\n * doc\n */ q = 0x1Fu + .5e-3f;",
               "url https://example.org/a//b /=/ */ /*/ end", "\\n\\t\\r 1.\\n2. // c\\n3.",
               "see `design/*.frag`\nfloat a = 1.0; // one\nfloat b = 2.0; /* two */ c */ d",
               "accept = 'audio/*'; '*/*' x = 1; // y\n/** doc\n * star\n */ z"]
    for s in samples:
        fast, exact = ll.token_texts(s), ll.streams(s)
        for mode in ("code", "full", "bare"):
            assert fast[mode] == [t.text for t in exact[mode]], (s, mode)


# ---------- the baseline: pre-existing breaches, measured every run, never allowed to grow ----------

def _entries(report, date="2026-10-13"):
    """Baseline entries for every breach in `report`, one per (file, corpus id), as the shipped baseline is built."""
    groups = {}
    for h in breaches(report):
        key = (h["file"], h["corpus"][0])
        n, t = groups.get(key, (0, 0))
        groups[key] = (n + 1, t + h["tokens"])
    return [{"file": f, "corpus": c, "breaches": n, "tokens": t, "date": date,
             "reason": "pre-existing at 9d6f29ff; triage pending Daniel"} for (f, c), (n, t) in sorted(groups.items())]


def test_a_baselined_breach_is_measured_and_reported_as_baseline_never_pass(tmp_path):
    house = {"design/old.glsl": WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", house))
    report = scan_planted(tmp_path / "b", house, baseline=entries, old=house)
    assert report["status"] == "baseline" and report["breaches"] == 0 and report["baselined"] == 1
    [hit] = report["hits"]
    assert hit["verdict"] == "baseline" and hit["file"] == "design/old.glsl"
    [entry] = report["baseline"]["entries"]
    assert entry["state"] == "held" and entry["measured"] == 1


def test_a_baseline_entry_whose_count_grows_fails(tmp_path):
    old = {"design/old.glsl": WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", old))
    grown = {"design/old.glsl": WEAVE + "\nint gap = 0;\nint gap2 = 1;\nint gap3 = 2;\n" + WEAVE + "\n"}
    report = scan_planted(tmp_path / "b", grown, baseline=entries, old=old)
    assert report["status"] == "breach" and report["breaches"] == 2
    assert report["baseline"]["entries"][0]["state"] == "grown"


def test_a_baseline_entry_whose_copy_lengthens_fails(tmp_path):
    old = {"design/old.glsl": WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", old))
    longer = {"design/old.glsl": WEAVE + "\n    return smoothstep(0.02, 0.0, w - 0.3);\n"}
    report = scan_planted(tmp_path / "b", longer, baseline=entries, old=old)
    assert report["status"] == "breach"
    assert report["baseline"]["entries"][0]["state"] == "grown"


def test_a_baselined_copy_swapped_for_a_different_copy_of_the_same_shader_fails(tmp_path):
    """Re-review 2: count and tokens alone let a declared copy be traded for another copy of the same shader that is
    no longer (here 31 tokens for 35). Each baselined hit must be part of a copy the file held at the commit."""
    old = {"design/old.glsl": WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", old))
    assert [(e["corpus"], e["breaches"], e["tokens"]) for e in entries] == [("Synth1", 1, 35)]
    swapped = {"design/old.glsl": "vec3 d = abs(p - a) - b;\nreturn dot(d, vec3(0.3, 0.6, 0.1)) * k - r;\n"}
    report = scan_planted(tmp_path / "b", swapped, baseline=entries, old=old)
    assert report["status"] == "breach"
    [hit] = report["hits"]
    assert hit["verdict"] == "breach" and hit["tokens"] == 31
    [entry] = report["baseline"]["entries"]
    assert entry["state"] == "changed"


def test_a_baselined_copy_that_shrinks_stays_baseline(tmp_path):
    """The other side of the same rule: a declared copy that is partly cleaned up is still part of what the commit
    held, so the debt only shrinks."""
    old = {"design/old.glsl": WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", old))
    shrunk = {"design/old.glsl": "float w = abs(g.x * 3.25 - g.y * 1.75) + sin(q.y;\nint ours = 2;\n"}
    report = scan_planted(tmp_path / "b", shrunk, baseline=entries, old=old)
    assert report["status"] == "baseline"
    [entry] = report["baseline"]["entries"]
    assert entry["state"] == "held" and entry["measured_tokens"] < entry["tokens"]


def test_a_new_copy_cannot_hide_in_the_entry_of_a_minor_id_it_shares(tmp_path):
    """Re-review 2: attribution preferred any declared id in a hit's ranking, not only one tied with its top id, so a
    new copy of shader Y that shares an idiom with the declared copy of shader X was absorbed by X's entry."""
    other = ("void mainImage(out vec4 tint, in vec2 px)\n{\n"
             "    float w = abs(g.x * 3.25 - g.y * 1.75) + cos(px.x * 0.5) * 9.5;\n    tint = vec4(w);\n}\n")
    corpus = {"Synth1": {"image.glsl": SYNTH}, "Other1": {"image.glsl": other}}
    old = {"design/old.glsl": WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", old, corpus=corpus))
    assert [(e["corpus"], e["breaches"], e["tokens"]) for e in entries] == [("Synth1", 1, 35)]
    now = {"design/old.glsl": "float w = abs(g.x * 3.25 - g.y * 1.75) + cos(px.x * 0.5) * 9.5;\n"}
    report = scan_planted(tmp_path / "b", now, baseline=entries, old=old, corpus=corpus)
    assert report["status"] == "breach"
    [hit] = report["hits"]
    assert hit["corpus"][0] == "Other1" and hit["verdict"] == "breach"
    # The hit is Other1's, so Synth1's entry measures nothing (were it absorbed there, the entry would read 'changed').
    [entry] = report["baseline"]["entries"]
    assert entry["state"] == "cleared"


def test_a_new_corpus_id_in_a_baselined_file_fails(tmp_path):
    corpus = {"Synth1": {"image.glsl": SYNTH}, "Synth2": {"image.glsl": SYNTH2}}
    old = {"design/old.glsl": WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", old, corpus=corpus))
    now = {"design/old.glsl": WEAVE + "\nint gap = 0;\n" + BRAID + "\n"}
    report = scan_planted(tmp_path / "b", now, baseline=entries, old=old, corpus=corpus)
    assert report["status"] == "breach"
    assert {(h["corpus"][0], h["verdict"]) for h in report["hits"]} == {("Synth1", "baseline"), ("Synth2", "breach")}


def test_a_file_new_since_the_baseline_commit_is_never_baselined(tmp_path):
    house = {"tests/test_new_tonight.py": 'S = """' + WEAVE + '"""\n'}
    entries = _entries(scan_planted(tmp_path / "a", house))
    report = scan_planted(tmp_path / "b", house, baseline=entries, old={})
    assert report["status"] == "breach"
    [entry] = report["baseline"]["entries"]
    assert entry["state"] == "invalid" and "9d6f29ff" in entry["why"]
    assert report["failures"]


def test_an_entry_declaring_more_than_the_commit_held_is_refused(tmp_path):
    old = {"design/old.glsl": WEAVE + "\n"}
    now = {"design/old.glsl": WEAVE + "\nint gap = 0;\nint gap2 = 1;\nint gap3 = 2;\n" + WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", now))          # declares 2, but the commit held 1
    report = scan_planted(tmp_path / "b", now, baseline=entries, old=old)
    assert report["status"] == "breach"
    assert report["baseline"]["entries"][0]["state"] == "invalid"


def test_without_the_commit_check_no_entry_is_applied(tmp_path):
    house = {"design/old.glsl": WEAVE + "\n"}
    entries = _entries(scan_planted(tmp_path / "a", house))
    report = scan_planted(tmp_path / "b", house, baseline=entries)   # no git, no stand-in: nothing can be verified
    assert report["status"] == "breach"
    assert report["baseline"]["entries"][0]["state"] == "unverified"


@pytest.mark.parametrize("field", ["file", "corpus", "breaches", "tokens", "date", "reason"])
def test_a_baseline_entry_missing_a_field_is_refused(tmp_path, field):
    entry = {"file": "design/a.glsl", "corpus": "X", "breaches": 1, "tokens": 12, "date": "2026-10-13",
             "reason": "pre-existing at 9d6f29ff; triage pending Daniel"}
    del entry[field]
    p = tmp_path / "baseline.json"
    p.write_text(json.dumps({"commit": "9d6f29ff", "entries": [entry]}), encoding="utf-8")
    with pytest.raises(ValueError, match=field):
        LL().load_baseline(p)


def test_the_shipped_baseline_is_well_formed():
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert data.get("why") and data["commit"] == "9d6f29ff"
    loaded = LL().load_baseline(BASELINE)
    for e in loaded["entries"]:
        assert e["reason"] == "pre-existing at 9d6f29ff; triage pending Daniel"
        assert e["date"] == "2026-10-13" and not e["file"].startswith("state/")


# ---------- the door ----------

def test_an_absent_corpus_skips_with_its_reason(tmp_path):
    root, _, allow_path = plant(tmp_path, {"design/a.glsl": "float x;\n"})
    report = LL().scan(root=root, corpus=tmp_path / "no-corpus-here", allow_path=allow_path)
    assert report["status"] == "skipped"
    assert "corpus" in report["reason"] and "absent" in report["reason"]


def test_the_report_counts_what_it_scanned_and_states_its_limit(tmp_path):
    report = scan_planted(tmp_path, {"design/a.glsl": "float ours = 2.0;\n", "scripts/b.js": "let x = 1;\n"})
    assert report["corpus"]["shaders"] == 1 and report["corpus"]["passes"] == 1
    assert report["corpus"]["shingles"] > 0
    assert report["scanned"]["files"] == 2 and report["scanned"]["tokens"] > 0
    assert report["scanned"]["discovery"] == "walk"
    assert "renamed" in report["limits"]


def test_a_consistent_rename_is_not_measured_and_the_report_says_so(tmp_path):
    """Defect 9 is a design limit, pinned so nobody reads a green as more than it is: identifiers are kept as written,
    so renaming short identifiers throughout breaks every window they sit in (here two names, five to eight tokens
    apart, leave no 12-token stretch untouched)."""
    renamed = WEAVE.replace("g.", "h.").replace("q.", "s.")
    report = scan_planted(tmp_path, {"design/renamed.glsl": renamed + "\n"})
    assert report["status"] == "clean"
    assert "verbatim" in report["limits"] and "renamed" in report["limits"]


def test_a_copy_whose_lines_carry_a_prefix_is_a_stated_limit(tmp_path):
    """Re-review 2: a prefix on every line (a diff's `+`, a Markdown quote's `> `, a Python `# `, `cat -n` numbers)
    breaks every window that crosses a line, so a copy of short lines held that way is not measured. A line of 12 or
    more tokens is still caught; the rest is a limit, and the report names it every run."""
    corpus = {"Mine2": {"image.glsl": COMMENTED}}
    unquoted = scan_planted(tmp_path / "a", {"docs/plain.md": COMMENTED_BODY}, corpus=corpus)
    assert caught_files(unquoted) == {"docs/plain.md"}
    quoted = "".join("> " + line + "\n" for line in COMMENTED_BODY.split("\n") if line)
    report = scan_planted(tmp_path / "b", {"docs/quoted.md": quoted}, corpus=corpus)
    assert report["status"] == "clean"
    assert "prefix" in report["limits"] and "diff" in report["limits"]


def test_a_corpus_file_committed_under_state_is_named():
    """Ruling a leaves the top-level state/ folder out of the scan, but a corpus file force-added there would be
    committed corpus text; any committed path under the corpus folder is a failure by name."""
    ll = LL()
    paths = ["state/arsenal/shaders/licence-line-triage.md", "state/arsenal/shaders/corpus/shaders/X/image.glsl",
             "state/arsenal/shaders/corpus-notes.md"]
    assert ll.corpus_leaks(paths, "state/arsenal/shaders/corpus") == [
        "state/arsenal/shaders/corpus/shaders/X/image.glsl"]


def test_the_verb_is_registered_and_exits_one_on_a_breach(tmp_path, capsys):
    from arsenal.shaders import cli
    root, corpus_root, allow_path = plant(tmp_path, {"design/edge.glsl": "vec2 g = fract(q * k) - 0.5; int\n"})
    args = ["licence-line", "--root", str(root), "--corpus", str(corpus_root), "--allow", str(allow_path), "--json"]
    assert cli.main(args) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "breach" and out["hits"][0]["file"] == "design/edge.glsl"
    (root / "design" / "edge.glsl").write_text("float ours = 2.0;\n", encoding="utf-8")
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "clean"


# ---------- the real corpus and the real tree ----------

@pytest.fixture(scope="module")
def real_index():
    if not (CORPUS_ROOT / "shaders").is_dir():
        pytest.skip(f"the private corpus is absent ({CORPUS_ROOT} does not exist: a fresh clone has none); "
                    "the licence line can only be measured where the corpus is")
    index = LL().build_index(CORPUS_ROOT)
    assert index is not None and index.passes, "the corpus folder exists but holds no passes"
    return index


@pytest.fixture(scope="module")
def real_report(real_index):
    return LL().scan(root=REPO, index=real_index)


@pytest.fixture
def calibration_dir():
    """A folder under state/ (gitignored) for real corpus copies; it is removed whatever the test does."""
    home = CALIBRATION_HOME / uuid.uuid4().hex
    home.mkdir(parents=True)
    try:
        yield home
    finally:
        shutil.rmtree(home, ignore_errors=True)
        try:
            CALIBRATION_HOME.rmdir()
        except OSError:
            pass


def _real_line(real_index):
    """One real corpus line of plain code (12 to 14 tokens, ASCII, no comment), read from disk and kept in memory."""
    ll = LL()
    for sid, _stem, path in real_index.passes:
        for raw in path.read_text(encoding="utf-8", errors="replace").split("\n"):
            if "//" in raw or "/*" in raw or not raw.strip().endswith(";") or not raw.isascii() or "for" in raw:
                continue
            toks = ll.streams(raw)["code"]
            if 12 <= len(toks) <= 14 and not ll.signature_spans(toks):
                return sid, raw.strip()
    raise AssertionError("no plain 12-14 token code line in the corpus")


def test_the_real_scanner_catches_real_corpus_lines_planted_in_every_shape(real_index, calibration_dir):
    """Defect 7: calibrate through discovery, decoding and real formatting, not on pre-normalised tokens."""
    sid, line = _real_line(real_index)
    plants = {
        "design/plain.frag": (line + "\n").encode(),
        "arsenal/web/tmpl.js": ("const S = `\n" + line + "\n`;\n").encode(),
        "design/graph.json": (json.dumps({"code": line}) + "\n").encode(),
        "scripts/gen.py": ('S = """\n' + line + '\n"""\n').encode(),
        "arsenal/web/notes.md": ("```glsl\n" + line + "\n```\n").encode(),
        "tests/test_planted.py": ("S = " + json.dumps(line) + "\n").encode(),
        "design/cp1252.frag": ("// © house\n" + line + "\n").encode("cp1252"),
        "scripts/utf16.js": ("const S = `\n" + line + "\n`;\n").encode("utf-16"),
        "arsenal/web/piano/state/kept.js": ("const S = `\n" + line + "\n`;\n").encode(),
    }
    root = calibration_dir / "repo"
    for rel, raw in plants.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    report = LL().scan(root=root, index=real_index)
    caught = {h["file"] for h in report["hits"] if not h["exempt"] and sid in h["corpus"]}
    missed = sorted(set(plants) - caught)
    assert not missed, f"the real scanner missed a real corpus line planted in: {missed}"
    assert report["scanned"]["files"] == len(plants) and not report["scanned"]["unreadable"]


def _real_commented_snippet(real_index):
    """Three or more consecutive real corpus lines, each of under 12 code tokens with a trailing // comment of its
    own, together at least 14 code tokens: only reading them as consecutive lines of code can catch them. Kept in
    memory; never printed."""
    ll = LL()
    for sid, _stem, path in real_index.passes:
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        for i in range(len(lines) - 3):
            group = lines[i:i + 3]
            ok, total = True, 0
            for raw in group:
                code, sep, note = raw.partition("//")
                n = len(ll.streams(code)["code"]) if sep else 0
                if not sep or "/*" in raw or "*/" in raw or not raw.isascii() or "for" in code or \
                        not ll.streams(note)["full"] or not 3 <= n < 12:
                    ok = False
                    break
                total += n
            if not ok or total < 14:
                continue
            snippet = "\n".join(group) + "\n"
            code = [t.text for t in ll.streams(snippet)["code"]]
            if all(hash(tuple(code[k:k + 12])) in real_index.hashes for k in range(len(code) - 11)):
                return sid, snippet
    raise AssertionError("no run of three commented short code lines in the corpus")


def test_a_real_commented_snippet_after_a_glob_path_is_caught(real_index, calibration_dir):
    """Re-review 2 on real text: a backticked glob in a note opened a false block comment, and real snippets in a
    fence after it were missed (103 of 137 caught, against 130 of 137 without the glob)."""
    sid, snippet = _real_commented_snippet(real_index)
    plants = {"docs/plain-note.md": "```glsl\n" + snippet + "```\n",
              "docs/globbed-note.md": "Sketches live in `design/*.frag`.\n\n```glsl\n" + snippet + "```\n",
              "arsenal/web/picker.js": 'input.accept = "audio/*";\nconst S = `\n' + snippet + "`;\n"}
    root = calibration_dir / "repo"
    for rel, text in plants.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    report = LL().scan(root=root, index=real_index)
    # Each plant holds nothing but the snippet, so any breach in it is the snippet (an idiom may rank `sid` past the
    # ten ids a hit names).
    caught = {h["file"] for h in report["hits"] if not h["exempt"]}
    missed = sorted(set(plants) - caught)
    assert not missed, f"the real scanner missed a real commented snippet of {sid} planted in: {missed}"


def test_a_whole_real_pass_held_as_a_one_line_string_is_covered_and_does_not_crash(real_index, calibration_dir):
    """Defect 4 on real text: every pass with many // comments, held as one JSON string, is read in full."""
    ll = LL()
    worst, crashed, checked = 1.0, 0, 0
    for sid, stem, path in real_index.passes:
        src = path.read_text(encoding="utf-8", errors="replace")
        if src.count("//") < 20:
            continue
        code = [t.text for t in ll.streams(src)["code"]]
        if len(code) < 200:
            continue
        held = "const S = " + json.dumps(src) + ";\n"
        try:
            st = ll.streams(held)
        except RecursionError:
            crashed += 1
            continue
        seen = set()
        for mode in ("code", "full"):
            t = [x.text for x in st[mode]]
            seen.update(tuple(t[i:i + 12]) for i in range(len(t) - 11))
        windows = [tuple(code[i:i + 12]) for i in range(len(code) - 11)]
        worst = min(worst, sum(w in seen for w in windows) / len(windows))
        checked += 1
    assert checked >= 20, f"only {checked} real passes had enough comments to test"
    assert crashed == 0, f"{crashed} real passes crashed the lexer when held as a one-line string"
    assert worst >= 0.999, f"a real pass held as a one-line string was only {worst:.1%} covered"


def test_real_commented_out_code_is_caught_when_uncommented(real_index, calibration_dir):
    """Defect 6 on real text: a real corpus comment that is code, planted as live code, is caught."""
    ll = LL()
    sources = [(sid, path.read_text(encoding="utf-8", errors="replace")) for sid, _stem, path in real_index.passes]
    live = set()   # every 12-token window of live corpus code, so the plant is code that lives ONLY in a comment
    for _sid, src in sources:
        code = [t.text for t in ll.streams(src)["code"]]
        live.update(hash(tuple(code[i:i + 12])) for i in range(len(code) - 11))
    found = None
    for sid, src in sources:
        for raw in src.split("\n"):
            s = raw.strip()
            if not s.startswith("//") or not s.isascii():
                continue
            body = s.lstrip("/").strip()
            toks = [t.text for t in ll.streams(body)["code"]]
            if 14 <= len(toks) <= 30 and {";", "=", "("} <= set(toks) and "for" not in toks and \
                    not any(hash(tuple(toks[i:i + 12])) in live for i in range(len(toks) - 11)):
                found = (sid, body)
                break
        if found:
            break
    assert found, "no commented-out code line found in the corpus"
    sid, body = found
    root = calibration_dir / "repo"
    (root / "design").mkdir(parents=True)
    (root / "design" / "ghost.glsl").write_text(body + "\n", encoding="utf-8", newline="\n")
    report = LL().scan(root=root, index=real_index)
    assert any(h["file"] == "design/ghost.glsl" and not h["exempt"] for h in report["hits"])


@pytest.mark.parametrize("rel", ["tests/test_glsl_licence_line.py", "arsenal/shaders/licence_line.py",
                                 "arsenal/shaders/licence_line_allow.json", "arsenal/shaders/licence_line_baseline.json"])
def test_the_licence_lines_own_files_share_no_run_with_the_real_corpus(real_index, rel):
    """Defect 10: this file's fixture once shared 17- and 24-token idiom runs with the corpus while claiming to quote
    no shader. The guard's own files are new tonight, so nothing of theirs can ever be baselined."""
    text = (REPO / rel).read_text(encoding="utf-8")
    allow = LL().load_allow(ALLOW)
    bad = [h for h in LL().scan_texts(real_index, [(rel, text)], allow=allow) if not h["exempt"]]
    assert not bad, "\n".join(LL().describe_hit(h) for h in bad)


def _git_list(*args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    out = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, env=env, check=True).stdout
    return {p for p in out.decode("utf-8").split("\0") if p}


def test_the_real_scope_is_every_file_git_would_commit_minus_state():
    """Ruling a: git ls-files plus untracked files that are not ignored, minus the top-level state/ folder."""
    def listing():
        return {p for p in _git_list("ls-files", "-z") | _git_list("ls-files", "-z", "--others", "--exclude-standard")
                if p.split("/", 1)[0] != "state"}
    before = listing()
    mode, files = LL().house_files(REPO)
    after = listing()
    got = {rel for rel, _origin in files}
    assert mode == "git"
    # Other seats write files while this runs: whatever stood still across the scan must match exactly.
    assert before & after <= got <= before | after
    assert "tests/test_glsl_licence_line.py" in got and "core/state/__init__.py" in got
    assert ".claude/skills/shader-craft/references/house-glsl-cookbook.md" in got
    assert not any(rel.startswith("state/") for rel in got)


def test_the_real_report_names_what_git_would_commit_under_state(real_report):
    """The re-review's observation for ruling a: files under the top-level state/ that git would commit are not
    scanned, so the report lists them every run, and one under the corpus folder fails the scan by name."""
    s = real_report["scanned"]
    committed = s["state_committed"]
    assert committed == sorted(committed) and all(p.startswith("state/") for p in committed)
    assert not LL().corpus_leaks(committed, "state/arsenal/shaders/corpus")


def test_no_house_file_shares_a_12_token_run_with_the_corpus_beyond_the_declared_baseline(real_report):
    report = real_report
    c, s, b = report["corpus"], report["scanned"], report["baseline"]
    print(f"\nlicence line: {report['status'].upper()}: {c['shaders']} corpus shaders, {c['passes']} passes, "
          f"{c['tokens']} tokens, {c['shingles']} distinct {report['run']}-token shingles "
          f"({c['comment_windows']} from commented-out code)")
    print(f"scanned {s['files']} text files ({s['discovery']}: {s['tracked']} tracked, {s['untracked']} untracked), "
          f"{s['tokens']} tokens; encodings {s['encodings']}; {len(s['binary_files'])} binary")
    print(f"baseline: {b['held']} held, {b['grown']} grown, {b['changed']} changed, {b['cleared']} cleared, "
          f"{b['invalid']} invalid, {b['unverified']} unverified; hits: {report['breaches']} breach, "
          f"{report['baselined']} baseline, {report['exempt']} exempt")
    for h in report["hits"]:
        print(LL().describe_hit(h))
    for e in b["entries"]:
        if e["state"] != "held":
            print(f"baseline entry {e['state']}: {e['file']} {e['corpus']} declared {e['breaches']} "
                  f"measured {e['measured']} {e.get('why', '')}")
    assert c["passes"] > 0 and s["files"] > 1000, "a green over nothing is not a green"
    assert s["discovery"] == "git", "the real tree is measured through git's own list of what it would commit"
    assert not s["unreadable"], f"unreadable files: {s['unreadable']}"
    assert b["invalid"] == 0 and b["unverified"] == 0, "every baseline entry must verify against 9d6f29ff"
    # The pin holds what the REPO carries: tracked files. A breach in an untracked file (another seat's work in
    # progress) is measured and printed here and by `py -m arsenal shader licence-line`, which exits 1 for it, but it
    # does not fail this pin: a test that fails on someone else's uncommitted file tests the machine, not the repo
    # (judge's ruling, 2026-10-13). Commit a file only after the CLI reads it clean.
    tracked = _git_list("ls-files", "-z")
    breaches = [h for h in report["hits"] if h["verdict"] == "breach"]
    bad = [h for h in breaches if h["file"].replace("\\", "/") in tracked]
    for h in breaches:
        if h not in bad:
            print("untracked, reported not pinned: " + LL().describe_hit(h))
    assert not bad and not report["failures"], (
        "corpus code in tracked house files beyond the declared baseline:\n" +
        "\n".join(LL().describe_hit(h) for h in bad) + "\n" + "\n".join(report["failures"]))
