"""The shader-craft skill's reverse-engineering section must route every shader artifact the house meets, and name
only surfaces that exist.

THE GUARANTEE THESE PIN. `.claude/skills/shader-craft/SKILL.md` gains a section "Dissecting a shader (reverse
engineering)" and a reference, `references/dissecting-shaders.md`, with the routing table for shader artifacts (which tool
first, and the one rule that keeps the reading honest), the observation / inference / unknown rule, the SwiftShader timing
rule and the rebuild rule. A routing table that names a verb that is not there sends a seat down a dead end at the moment
it trusted the table, so: every repo path the reference names exists; every verb it names is registered; every route
the explain verb can put in a ledger (arsenal/shaders/explain.py ROUTES) has a row in the table, so the ledger and the
skill cannot drift apart. The section links to the house reverse-engineering skill, whose discipline it specialises.
RED before the section exists; RED again the day any of it drifts.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / ".claude" / "skills" / "shader-craft"
SKILL = SKILL_DIR / "SKILL.md"
REF = SKILL_DIR / "references" / "dissecting-shaders.md"
RE_SKILL = ".claude/skills/reverse-engineering/SKILL.md"

# the same path rule as tests/test_shader_craft_skill_cites_live_surfaces.py
_PATH_RE = re.compile(r"`((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.*-]+\.(?:js|mjs|py|md|frag|html|css|glsl|card))`")

# every artifact the routing table must have a row for (the words a row's first cell must contain)
ROUTES = ("single-pass", "buffer feedback", "sound pass", "cubemap pass", "texture inputs", "audio-reactive",
          "house module", "group", "three.js", "video or screenshot")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _table_rows(text: str) -> list:
    return [ln for ln in text.splitlines() if ln.startswith("|") and not re.match(r"^\|\s*-", ln)]


def test_p0_the_section_and_its_reference_exist_and_link_the_house_re_skill():
    text = _read(SKILL)
    assert "## Dissecting a shader (reverse engineering)" in text
    assert "references/dissecting-shaders.md" in text
    assert REF.is_file(), f"missing {REF}"
    assert RE_SKILL in text or RE_SKILL in _read(REF), "link the house reverse-engineering skill"
    assert (REPO / RE_SKILL).is_file()


def test_p1_every_path_the_reference_and_the_section_name_exists():
    missing = []
    for doc in (SKILL, REF):
        for p in _PATH_RE.findall(_read(doc)):
            if "*" in p:
                d = REPO / Path(p).parent
                if not (d.is_dir() and any(d.glob(Path(p).name))):
                    missing.append(f"{doc.name}: {p}")
                continue
            if not ((REPO / p).exists() or (SKILL_DIR / p).exists() or (doc.parent / p).exists()):
                missing.append(f"{doc.name}: {p}")
    assert not missing, "paths named that do not exist: " + ", ".join(missing)


def test_p2_the_routing_table_has_a_row_for_every_shader_artifact():
    rows = _table_rows(_read(REF))
    firsts = [r.split("|")[1].lower() for r in rows if r.count("|") >= 3]
    gone = [route for route in ROUTES if not any(route in f for f in firsts)]
    assert not gone, f"routing table lacks a row for: {gone}"


def test_p3_every_route_the_explain_verb_writes_has_a_row():
    from arsenal.shaders import explain as X
    rows = " ".join(r.split("|")[1].lower() for r in _table_rows(_read(REF)) if r.count("|") >= 3)
    gone = [name for name in X.ROUTES if name.lower() not in rows]
    assert not gone, f"explain.ROUTES names routes the skill's table does not: {gone}"


def test_p4_the_rules_are_stated():
    ref = _read(REF)
    low = ref.lower()
    for label in ("observed-in-code", "observed-in-render", "measured", "inferred", "unknown"):
        assert label in ref, f"the reference must define the label {label}"
    assert "swiftshader timing never stands for gpu timing" in low
    assert "design choice" in low, "the rebuild rule separates observation from our own design choices"
    assert "not detected by dissect" in low, "a detector that found nothing is not proof of absence"
    assert "walk from a reset" in low and "never jump" in low
    assert "silence" in low and "stand-in" in low


def test_p6_the_reference_states_the_ledger_rules_the_explain_verb_applies():
    """The reference teaches what the ledger does, so it drifts the day the verb's rules change. Since 2026-10-13 (the
    technical review of the explain verb): a technique the dissector recognises from the shape of the math is inferred,
    not observed, and a function name alone is never a finding; a study id carries the note's sha8; the cache covers
    meta.json and the media files too. RED until the reference says so."""
    from arsenal.shaders import explain as X
    ref = _read(REF)
    rows = {r.split("|")[1].strip(): r for r in _table_rows(ref) if r.count("|") >= 4}
    assert not re.search(r"names?\s+(?:only\s+ever\s+)?adds?\s+confidence|lets\s+names\s+add\s+confidence", ref, re.I), \
        "a name never adds confidence: the ledger reports a name alone as inferred (" + X.NAME_ONLY_BOUNDARY + ")"
    assert "shape" in rows.get("inferred", "").lower(), "the inferred row must name the dissector's shape readings"
    assert "matched the shape" not in rows.get("observed-in-code", ""), "observed-in-code is raw facts only"
    # An example the reference labels observed-in-code must be a raw fact (a uniform or channel read on a live line, a
    # pass or input the configuration declares), never a technique reading. Before: '"The march is 64 steps" is
    # observed-in-code with a line' taught the very rule the ledger had just stopped applying.
    examples = re.findall(r"[\"“]([^\"”\n]+)[\"”]\s+(?:is|are)\s+(?:an?\s+)?observed-in-code", ref, re.I)
    examples += re.findall(r"observed-in-code[^.\n]{0,12}?[:(]\s*[\"“]([^\"”\n]+)[\"”]", ref, re.I)
    technique = re.compile(r"march|step|octave|fbm|noise|sphere|trace|distance|sdf|gamma|palette|fold|fractal|"
                           r"voronoi|shadow|normal|technique|shape|loop", re.I)
    taught = [e for e in examples if technique.search(e)]
    assert not taught, f"a technique reading is inferred, not observed-in-code: {taught}"
    forms = re.findall(r"study:<id>(.)", ref)
    assert forms and all(f == "@" for f in forms), "a study id carries the note's sha8: study:<id>@<sha8>#<section>"
    assert re.search(r"config:<id>@[^`]*:pass\b", ref), "name both config id forms: ...:<pass>:pass and ...:iChannel<n>"
    assert "meta.json" in ref, "the cache paragraph must name meta.json (and the media files) among the inputs"


def test_p7_the_label_table_names_every_reading_the_verb_makes_inferred_or_unknown():
    """The explain verb labels three more things than the table said: a read the dissector reports that no live line
    holds (kind read_unchecked) is inferred; the dead-function list is inferred when the reader could not follow the
    whole pass (an #if it could not evaluate, code it could not follow, no entry point found); and a pass with no entry
    point the reader recognises is an unknown. Before: the observed row listed 'the functions no entry point reaches'
    with no exception, and the inferred row named neither reading (review rr[1], 2026-10-13). RED until it says so."""
    rows = {r.split("|")[1].strip(): r for r in _table_rows(_read(REF)) if r.count("|") >= 4}
    obs, inf, unk = (rows.get(k, "").lower() for k in ("observed-in-code", "inferred", "unknown"))
    assert "no live line" in inf or "no line of live code" in inf, "the inferred row must name an unconfirmed read"
    assert "dead" in inf and "follow" in inf, "the inferred row must name the dead list the reader could not confirm"
    assert "follow" in obs, "the observed row's dead-function clause holds only where the reader followed every pass"
    assert "entry point" in unk, "the unknown row must name a pass in which the reader found no entry point"


def test_p5_every_verb_the_reference_names_is_registered():
    ref = _read(REF)
    shader_cli = _read(REPO / "arsenal" / "shaders" / "cli.py")
    for verb in ("explain", "dissect", "render", "filmstrip", "check", "card"):
        assert f"py -m arsenal shader {verb}" in ref, f"the reference should name `shader {verb}`"
    assert '"explain"' in shader_cli and '"cards"' in shader_cli
    media = _read(REPO / "arsenal" / "media" / "__main__.py")
    assert '"filmstrip"' in media and "py -m arsenal.media filmstrip" in ref
    top = _read(REPO / "arsenal" / "__main__.py")
    for verb in ("boost", "floors"):
        assert f'sub.add_parser("{verb}"' in top and f"py -m arsenal {verb}" in ref
