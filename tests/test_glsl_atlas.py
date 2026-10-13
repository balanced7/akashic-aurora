"""Pins for the primitive atlas as data (arsenal/shaders/atlas.json, atlas.py, atlas_build.py): slice S0 of the shader
school build (research/in-flight/shader-school-2026-10-13/unified-architecture-draft.md section 15, rows of section 14).

WHY THESE PINS. The atlas draft is the parts list every later slice builds from: S3a writes its batch-A files, the lab
groups modules by its category ids, the dissector maps its tags onto its categories, and the Shelf links each loved
shader to the parts it teaches. A parts list is only useful if it is unambiguous, so these pins hold the properties
that make it so:

  - one category id means one bin, and one planned function name means one part (the composer refuses a library in
    which two modules define one function, so a doubled name in the plan is a future outage, not a style nit);
  - no planned name collides with a legacy bench chunk. The judge's ruling 3 (build-spec-reconciled.md) overruled the
    S2 rename of the chunks' `fbm3`: the library chooses its own name instead, so there is NO clash at all, not one
    clash "flagged for later";
  - the P0 set can be BUILT from P0 parts alone (the closure pins): every type a planned signature uses is itself
    planned no later than its users, and every part a P0 group tier requires is P0. The judge's rulings on the S0
    review (a: plan each such type as a struct part; b: promote what the P0 groups require) close the gaps the draft
    left, and each one is recorded, with its reason, in atlas.json's `rulings` list;
  - every exemplar is one of Daniel's 42 loved shaders, every module the library has built sits in a category the
    atlas knows, and every tag the dissector can emit lands on a category;
  - atlas.json is exactly what the converter makes of the draft, so the data cannot drift from the document it claims
    to encode (regenerate with `py -m arsenal.shaders.atlas_build` when the draft is revised), and the converter
    REFUSES a draft it cannot read cleanly rather than misfiling rows.

The corpus is other people's code and lives under state/ (gitignored); the pins that need it skip when it is absent.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ATLAS_JSON = REPO / "arsenal" / "shaders" / "atlas.json"
DRAFT = REPO / "research" / "in-flight" / "shader-school-2026-10-13" / "primitive-atlas-draft.md"
CHUNKS = REPO / "design" / "vfx-chunks"
SETS = REPO / "state" / "arsenal" / "shaders" / "corpus" / "sets.json"
DISSECT = REPO / "arsenal" / "shaders" / "dissect.py"

P0_GROUPS = {"finish", "aurora", "neon-line", "studio-object", "glow-xray", "hex-neon"}
RANK = {"P0": 0, "P1": 1, "P2": 2}

# After the judge's rulings on the S0 review: six struct parts added (ruling a), three parts promoted to P0 (ruling b).
# After the batch-A review (defect 3): three P0 parts for the six helpers the library built and the draft never planned.
# After the batch-B review (the judge's ruling c): six P0 recipe parts, one per group recipe module.
COUNTS_AFTER_RULINGS = {"parts": 581, "by_status": {"P0": 199, "P1": 265, "P2": 117}}

# Signatures the build settled where the draft wrote '...' or a parameter short, or that the build corrected (batch-A
# review, defect 3; batch-B review, defect 3 and the judge's ruling c): each is a ruling, so the atlas reads as the
# library is built.
BUILT_SIGNATURES = {
    "displayOut": "vec3 displayOut(vec3 sceneLin, vec2 pixel, vec2 res, float ev, int curve,",
    "audByteToDb": "float audByteToDb(float v)",
    "audByteToAmp": "float audByteToAmp(float v)",
    "fbmGrad3": "float fbmGrad3(vec3 p, int octaves, float lacunarity, float gain, uint seed)",
    "cellU2": "uvec2 cellU2(vec2 p)",
    "domRepeatLimited": "vec3 domRepeatLimited(inout vec3 p, vec3 period, vec3 idMin, vec3 idMax)",
    "camOrbit": "vec3 camOrbit(vec2 mouse01, float autoYaw, float radius, vec3 target)",
    "camOrthoRay": "vec3 camOrthoRay(vec2 p, mat3 basis, float scale, inout vec3 ro)",
    "rmRelaxed": "vec4 rmRelaxed(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, float omega, int maxSteps)",
    "rmBacktrack": "vec4 rmBacktrack(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, int maxSteps, int bisectSteps)",
}
# The group recipe modules (the judge's ruling c on the batch-B review): the atlas plans every function each provides.
RECIPE_MODULES = {"groups/aurora-band.glsl": "aurora", "groups/aurora-sheets.glsl": "aurora",
                  "groups/glow-xray.glsl": "glow-xray", "groups/hex-neon.glsl": "hex-neon",
                  "groups/neon-line.glsl": "neon-line", "groups/studio-object.glsl": "studio-object"}
# Helpers the library exposes by name that the draft never planned, and the module each one is built in.
BUILT_HELPERS = {"oklchMaxChroma": "colour/oklab.glsl", "oklchCusp": "colour/oklab.glsl",
                 "palPitchPiano": "colour/palette.glsl", "palPitchLumaMean": "colour/palette.glsl",
                 "noiseGradRamp2": "noise/gradient.glsl", "noiseGradRamp3": "noise/gradient.glsl"}


@pytest.fixture(scope="module")
def A():
    from arsenal.shaders import atlas
    return atlas


@pytest.fixture(scope="module")
def data(A):
    return A.load()


@pytest.fixture(scope="module")
def draft_text():
    if not DRAFT.exists():
        pytest.skip("the atlas draft has moved")
    return DRAFT.read_text(encoding="utf-8")


def planned(data):
    return {fn for p in data["parts"] for fn in p["functions"]}


def owners(data):
    return {fn: p for p in data["parts"] for fn in p["functions"]}


def groups(data):
    return {g["name"]: g for g in data["groups"]}


# A synthetic library function for the built-versus-planned pins. They need only its name, so it is a stub that shares
# no 12-token run with any corpus shader: the textbook linstep body the pins used before was a licence-line breach, and
# so was this stub with the parameters spelled (a, b, x), so they are spelled (lo, hi, x). A new file cannot be
# baselined; check with `py -m arsenal shader licence-line`.
STUB_LINSTEP = "float shpLinstep(float lo, float hi, float x) { return x; }\n"


def write_module(d: Path, fname: str, header: dict, body: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / fname).write_text("//! " + json.dumps(header) + "\n" + body, encoding="utf-8")


# The closure pin reads the draft's own signature cells with this small parser, independent of the converter's.
GLSL_BUILTIN_TYPES = frozenset("""void bool int uint float vec2 vec3 vec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4 bvec2 bvec3
bvec4 mat2 mat3 mat4 sampler2D sampler3D samplerCube""".split())
QUALIFIERS = frozenset("const highp mediump lowp inout out in".split())


def draft_types(row: str) -> set:
    """Every non-GLSL type a draft row's signature cell uses: return types, parameter types and struct field types."""
    sig = row.strip().strip("|").split("|")[0]
    found = set()
    for span in re.findall(r"`([^`]*)`", sig):
        span = span.strip()
        decls = []
        m = re.match(r"^struct\s+\w+\s*\{(.*)\}", span)
        if m:
            decls = [d.strip() for d in m.group(1).split(";")]
        else:
            m = re.match(r"^(.*?)\b[A-Za-z_]\w*\s*\((.*)\)\s*$", span)
            if not m:
                continue
            ret = [w for w in m.group(1).split() if w not in QUALIFIERS]
            if ret:
                found.add(ret[-1])
            decls = [a.strip() for a in m.group(2).split(",")]
        for d in decls:
            words = [w for w in d.split() if w not in QUALIFIERS]
            if len(words) >= 2:
                found.add(re.sub(r"\[.*$", "", words[0]))
    return {t for t in found if re.fullmatch(r"[A-Za-z_]\w*", t) and t not in GLSL_BUILTIN_TYPES}


# ---------- the file itself ----------

def test_atlas_json_parses_and_names_its_api_and_its_source():
    raw = json.loads(ATLAS_JSON.read_text(encoding="utf-8"))
    assert raw["api"] == "arsenal.shader-atlas/v1"
    assert raw["source"]["draft"].endswith("primitive-atlas-draft.md")
    assert raw["generated_by"] == "arsenal/shaders/atlas_build.py"


def test_thirteen_families_lettered_a_to_m(data):
    letters = [f["letter"] for f in data["families"]]
    assert letters == list("ABCDEFGHIJKLM")
    assert all(f["name"] for f in data["families"])


def test_category_ids_are_unique_well_formed_and_belong_to_a_family(data):
    ids = [c["id"] for c in data["categories"]]
    assert len(ids) == len(set(ids)), [i for i, n in Counter(ids).items() if n > 1]
    letters = {f["letter"] for f in data["families"]}
    for c in data["categories"]:
        assert re.fullmatch(r"[A-M]\d{1,2}", c["id"]), c["id"]
        assert c["family"] == c["id"][0] and c["family"] in letters
        assert c["name"] and c["module"].endswith(".glsl") and c["module"] in c["modules"]


def test_every_family_has_a_category_so_every_part_has_a_bin(data):
    have = {c["family"] for c in data["categories"]}
    assert have == {f["letter"] for f in data["families"]}


def test_row_counts_match_what_the_draft_declares(data):
    # Atlas draft section 2: "562 primitive rows ... By status: 184 rows P0, 265 P1, 113 P2". The draft's count covers
    # the rows that open with a signature; four more rows open with prose (host-level supersampling, P1; the atmosphere
    # LUT family, the ocean set and the TAA set, P2). They are parts too, and they are exactly the difference. These are
    # the DRAFT's statuses: a part a ruling promoted keeps the draft's status in `status_draft`.
    drafted = [p for p in data["parts"] if p["form"] != "ruling"]
    sig = Counter(p.get("status_draft", p["status"]) for p in drafted if p["form"] == "signature")
    assert (sum(sig.values()), sig["P0"], sig["P1"], sig["P2"]) == (562, 184, 265, 113)
    prose = sorted((p["status"], p["kind"]) for p in drafted if p["form"] == "prose")
    assert prose == [("P1", "idiom"), ("P2", "set"), ("P2", "set"), ("P2", "set")]
    assert len(drafted) == 566


def test_counts_after_the_rulings(data):
    # The review asked for these to be pinned: 81 categories (80 headings plus M1, family M's headless table) and the
    # per-status counts once the judge's rulings are applied (S0 acceptance's 184 P0 rows plus 3 promoted parts and 3
    # P0 struct parts).
    c = data["counts"]
    assert c["families"] == 13 and c["categories"] == 81 and len(data["categories"]) == 81
    assert c["parts"] == COUNTS_AFTER_RULINGS["parts"] == len(data["parts"])
    assert c["by_status"] == COUNTS_AFTER_RULINGS["by_status"]
    assert dict(Counter(p["status"] for p in data["parts"])) == COUNTS_AFTER_RULINGS["by_status"]


def test_every_part_is_complete(data):
    cats = {c["id"]: c for c in data["categories"]}
    ids = [p["id"] for p in data["parts"]]
    assert len(ids) == len(set(ids))
    for p in data["parts"]:
        assert p["category"] in cats, p["id"]
        assert p["family"] == cats[p["category"]]["family"], p["id"]
        assert p["status"] in {"P0", "P1", "P2"}, p["id"]
        assert p["cost"] is None or re.fullmatch(r"C[0-4]", p["cost"]), (p["id"], p["cost"])
        assert p["signature"] and p["contract"], p["id"]
        assert p["module"].endswith(".glsl") and p["module"] in cats[p["category"]]["modules"], p["id"]
        assert isinstance(p["learn"], list) and isinstance(p["exemplars"], list)
        assert isinstance(p["types"], list)
        for ptr in p["learn"]:
            assert re.match(r"(SR|NP|LM|VA|CP|PF|WS|GP) |study:|craft secret|arc-|house |shader-craft", ptr), ptr


def test_only_an_idiom_names_no_function(data):
    empty = sorted(p["kind"] for p in data["parts"] if not p["functions"])
    assert empty == ["idiom", "idiom"]  # host-level supersampling; the dwell-brightness idiom


# ---------- names: one owner per function, no clash with the legacy chunks ----------

def test_planned_function_names_are_unique_across_the_atlas(data):
    owners_ = {}
    doubled = []
    for p in data["parts"]:
        assert len(p["functions"]) == len(set(p["functions"])), p["id"]
        for fn in p["functions"]:
            if fn in owners_:
                doubled.append((fn, owners_[fn], p["id"]))
            owners_[fn] = p["id"]
    assert not doubled


def test_no_planned_name_collides_with_a_legacy_chunk(data):
    from arsenal.shaders import modules as M
    legacy = M.load_library([CHUNKS]).providers
    assert legacy, "the bench chunks define functions; an empty set means the loader did not find them"
    clash = sorted(planned(data) & set(legacy))
    assert not clash, f"planned names that a design/vfx-chunks file already defines: {clash}"


def test_the_fbm3_clash_is_resolved_by_the_library_choosing_its_own_name(data):
    # Ruling 3 of build-spec-reconciled.md: no rename of the legacy chunks tonight; the library avoids the clash.
    names = planned(data)
    assert "fbm3" not in names and "fbm2" not in names
    assert data["renames"]["fbm3"] in names and data["renames"]["fbm2"] in names
    row = next(r for r in data["collisions"] if "fbm3" in r["collides_with"])
    assert data["renames"]["fbm3"] in row["names"] and "ruling" in row


def test_the_fbm_ledger_row_reads_as_ruling_3_not_as_the_overruled_rename(data):
    # Review defect 5: the row's names said fbmGrad3 while its owner text still said "fbm3 ... after the legacy chunk's
    # functions are renamed (architecture slice S2)", the plan ruling 3 overruled.
    row = next(r for r in data["collisions"] if "fbm3" in r["collides_with"])
    assert "fbmGrad3" in row["owner"] and "noise/fbm.glsl" in row["owner"]
    assert "renamed" not in row["owner"] and "S2" not in row["owner"]
    assert "after the legacy chunk's functions are renamed" in row["owner_draft"]   # the draft's words, kept
    for r in data["collisions"]:
        assert "functions are renamed" not in r["owner"], r["proposed"]
        assert not re.search(r"(?<!\w)fbm[23](?!\w)", r["owner"].split(";")[0]), r["owner"]


def test_the_collision_ledger_is_encoded_and_its_owners_are_planned(data):
    rows = data["collisions"]
    assert len(rows) == 24          # every row of atlas draft section 1.1
    names = planned(data)
    for r in rows:
        assert r["proposed"] and r["names"], r
        for n in r["names"]:
            if n.endswith("*"):
                assert any(fn.startswith(n[:-1]) for fn in names), (r["proposed"], n)
            else:
                assert n in names, (r["proposed"], n)


# ---------- closure: the P0 set can be built from P0 parts alone ----------

def test_closure_every_type_a_signature_uses_is_planned_no_later_than_its_users(data, draft_text):
    # Review defect 1: StudioParams and PitchPalette (used by P0 parts) were planned nowhere, LitSurface only at P1
    # while P0 rigStudio takes it, and LightParams, OutdoorRig and Atmos were planned nowhere. Judge's ruling (a): plan
    # each as a struct part in the module of its first user, at the earliest status of any part that uses it.
    lines = draft_text.split("\n")
    own = owners(data)
    seen, gaps = set(), []
    for p in data["parts"]:
        if p["line"] is None:
            continue
        used = draft_types(lines[p["line"] - 1])
        seen |= used
        assert set(p["types"]) == used - set(p["functions"]), (p["id"], p["types"], used)
        for t in sorted(used):
            o = own.get(t)
            if o is None:
                gaps.append((p["id"], p["status"], t, "planned nowhere"))
            elif RANK[o["status"]] > RANK[p["status"]]:
                gaps.append((p["id"], p["status"], t, f"planned at {o['status']} by {o['id']}"))
    assert {"StudioParams", "PitchPalette", "LitSurface", "LightParams", "OutdoorRig", "Atmos",
            "VolAccum", "LitMaterial"} <= seen, "the signature parser found too few types to mean anything"
    assert not gaps


def test_ruling_a_plans_each_missing_type_as_a_struct_in_its_first_users_module(data):
    own = owners(data)
    expect = {  # type: (module of its first user, earliest status of its users, the users)
        "StudioParams": ("light/env.glsl", "P0", {"litStudioEnv", "rigStudio"}),
        "PitchPalette": ("colour/palette.glsl", "P0", {"palPitchFifths"}),
        "LitSurface": ("light/rigs.glsl", "P0", {"rigStudio", "rigOutdoor", "litResolveMaterial", "litShadeLight",
                                                  "litFurnace"}),
        "LightParams": ("motion/envelope.glsl", "P1", {"envStrikeSag", "musLight"}),
        "OutdoorRig": ("light/rigs.glsl", "P1", {"rigOutdoor"}),
        "Atmos": ("atmos/sky.glsl", "P2", {"atmosEarth"}),
    }
    rulings = {r["id"]: r for r in data["rulings"]}
    for t, (module, status, users) in expect.items():
        p = own[t]
        assert p["kind"] == "struct" and p["form"] == "ruling" and p["functions"] == [t], t
        assert (p["module"], p["status"]) == (module, status), (t, p["module"], p["status"])
        user_fns = {fn for u in p["users"] for fn in next(q for q in data["parts"] if q["id"] == u)["functions"]}
        assert users <= user_fns, (t, p["users"])
        r = rulings[p["ruling"]]
        assert r["kind"] in {"plan-struct", "split-struct"} and r["names"] == [t] and r["reason"], r
    # LitSurface was planned, but at P1 inside F11.01: it moves out to its own P0 part, and F11.01 keeps the rest.
    f11 = next(p for p in data["parts"] if p["id"] == "F11.01")
    assert f11["functions"] == ["LitMaterial", "litResolveMaterial"] and f11["status"] == "P1"
    assert rulings[own["LitSurface"]["ruling"]]["kind"] == "split-struct"


def test_ruling_b_promotes_what_the_p0_groups_require_and_records_why(data):
    own = owners(data)
    promoted = {r["names"][0]: r for r in data["rulings"] if r["kind"] == "promote"}
    assert set(promoted) == {"envBreath", "skyGradient", "patCellDelay"}
    for n, r in promoted.items():
        assert (r["from"], r["to"]) == ("P1", "P0") and r["reason"] and r["required_by"], r
        assert own[n]["status"] == "P0" and own[n]["status_draft"] == "P1" and r["id"] in own[n]["rulings"]
    assert own["patRadialWave"]["status"] == "P1"      # one alternative suffices; the judge chose patCellDelay


def test_closure_every_part_a_p0_group_tier_requires_is_p0(data):
    st = {fn: p["status"] for p in data["parts"] for fn in p["functions"]}
    gaps = []
    for g in data["groups"]:
        for t in g["tiers"]:
            if t["status"] != "P0":
                continue
            gaps += [(g["name"], t["name"], n, st[n]) for n in t["required"] if st[n] != "P0"]
            for options in t["alternatives"]:
                if not any(all(st[n] == "P0" for n in opt) for opt in options):
                    gaps.append((g["name"], t["name"], options))
    assert not gaps
    # What stays non-P0 inside the P0 groups is optional, an alternative with a P0 sibling, or in a P1 tier:
    left = {n for g in data["groups"] if g["name"] in P0_GROUPS for n in g["parts"] if st[n] != "P0"}
    assert left == {"glowToneBloom", "tmAgx", "warpShear2", "auroraVolume", "glowCompactWire", "rmClipToBox",
                    "patRadialWave", "latHexNeighbourMin", "cmpXor"}


def test_the_rulings_are_recorded_with_their_reasons(data):
    rulings = data["rulings"]
    ids = [r["id"] for r in rulings]
    assert len(ids) == len(set(ids))
    for r in rulings:
        assert r["kind"] and r["names"] and r["reason"] and r["source"], r
    kinds = Counter(r["kind"] for r in rulings)
    assert kinds["promote"] == 3 and kinds["plan-struct"] == 5 and kinds["split-struct"] == 1
    assert kinds["rename"] == 1 and kinds["ledger-owner"] == 1
    assert kinds["built-signature"] == len(BUILT_SIGNATURES) and kinds["plan-built"] == 3
    assert kinds["plan-recipe"] == len(RECIPE_MODULES)
    referenced = {x for p in data["parts"] for x in p.get("rulings", [])} | \
                 {x for m in data["manifest"] for x in m.get("rulings", [])} | \
                 {p["ruling"] for p in data["parts"] if "ruling" in p}
    assert referenced <= set(ids), sorted(referenced - set(ids))


# ---------- exemplars, groups, the build manifest ----------

def test_exemplars_name_shaders_from_the_atlas_legend(data):
    legend = {s["id"] for s in data["loved"]}
    assert len(legend) == 42
    used = {e for p in data["parts"] for e in p["exemplars"]} | {e for g in data["groups"] for e in g["exemplars"]}
    assert used and used <= legend, sorted(used - legend)


def test_every_exemplar_is_in_the_loved_set_when_the_corpus_is_present(data):
    if not SETS.exists():
        pytest.skip("the private corpus is not on this machine")
    loved = set(json.loads(SETS.read_text(encoding="utf-8")).get("loved") or [])
    if not loved:
        pytest.skip("the corpus has no loved set yet")
    used = {e for p in data["parts"] for e in p["exemplars"]} | {e for g in data["groups"] for e in g["exemplars"]}
    assert used <= loved, sorted(used - loved)
    assert {s["id"] for s in data["loved"]} == loved


def test_the_study_only_shader_is_marked(data):
    study_only = {s["id"] for s in data["loved"] if s["study_only"]}
    assert study_only == {"4s23zz"}


def test_twenty_five_groups_six_of_them_p0_and_their_parts_are_planned(data):
    groups_ = data["groups"]
    assert len(groups_) == 25 and len({g["name"] for g in groups_}) == 25
    assert {g["name"] for g in groups_ if g["status"] == "P0"} == P0_GROUPS
    names = planned(data)
    for g in groups_:
        assert set(g["parts"]) <= names, (g["name"], sorted(set(g["parts"]) - names))
        assert g["cost"] is None or re.fullmatch(r"C[0-4]", g["cost"])
        if g["status"] != "P2":
            assert g["parts"] and g["tiers"], g["name"]
        for t in g["tiers"]:
            alt = [n for options in t["alternatives"] for opt in options for n in opt]
            together = t["required"] + alt + t["optional"]
            assert len(together) == len(set(together)), (g["name"], t["name"], together)   # one mark per part
            assert set(together) == set(t["parts"]) and set(t["parts"]) <= set(g["parts"]), (g["name"], t["name"])
            assert re.fullmatch(r"C[0-4]", t["cost"] or "C0") and t["status"] in RANK


def test_group_tiers_carry_their_own_parts_cost_and_status(data):
    # Review defect 3: aurora was stored as one C3 group because of its P1 volume tier, so ruling 5's render-scale gate
    # would start its P0 band (C1) and sheets (C2) tiers at half scale. Each tier now carries its own cost and status.
    g = groups(data)["aurora"]
    tiers = {t["name"]: t for t in g["tiers"]}
    assert list(tiers) == ["band", "sheet", "volume"]
    assert (tiers["band"]["cost"], tiers["band"]["status"]) == ("C1", "P0")
    assert (tiers["sheet"]["cost"], tiers["sheet"]["status"]) == ("C2", "P0")
    assert (tiers["volume"]["cost"], tiers["volume"]["status"]) == ("C3", "P1")
    assert "auroraVolume" in tiers["volume"]["required"] and "auroraVolume" not in tiers["band"]["parts"]
    assert g["cost"] == "C2"           # the costliest tier that ships at the group's own status
    glass = {t["name"]: t for t in groups(data)["glass"]["tiers"]}
    assert (glass["analytic"]["cost"], glass["marched"]["cost"]) == ("C0", "C3")
    assert glass["marched"]["required"] == ["litGlassMarch"]
    finish = groups(data)["finish"]["tiers"]
    assert len(finish) == 1 and finish[0]["name"] is None and finish[0]["status"] == "P0"


def test_group_recipes_mark_optional_and_alternative_parts(data):
    def tier(name, t=None):
        return next(x for x in groups(data)[name]["tiers"] if x["name"] == t)

    fin = tier("finish")
    assert {"glowToneBloom", "tmAgx"} <= set(fin["optional"])                       # "optional", "when built"
    assert [["tmTanh"], ["tmExp"], ["tmAcesFit"], ["tmPbrNeutral"]] in fin["alternatives"]   # chosen by `curve`
    assert {"expose", "srgbEncode", "ditherOut", "dthIgn", "displayOut"} <= set(fin["required"])
    band = tier("aurora", "band")
    assert [["warpShear2"], ["warpFbm2"]] in band["alternatives"]
    assert [["noiseTriangle2"], ["fbmGrad2"]] in band["alternatives"]
    assert {"envBreath", "skyGradient", "auroraRays", "cmpAdd", "auroraProfile"} <= set(band["required"])
    neon = tier("neon-line")
    assert [["glowTwoGauss"], ["glowLorentz"], ["shpInvPower"], ["glowCompactWire"]] in neon["alternatives"]
    assert [["cmpMax"], ["cmpAdd"]] in neon["alternatives"]
    studio = tier("studio-object")
    assert [["rmClipToBox"], ["ixSphere"]] in studio["alternatives"]               # "P1; until then ixSphere"
    assert {"rigStudio", "litStudioEnv", "litFresnelSchlick", "nrmTetra", "nrmEps"} <= set(studio["required"])
    xray = tier("glow-xray")
    assert [["glowAccum"], ["glowEmitStep"]] in xray["alternatives"]              # "and/or"
    assert "glowStepCount" in xray["optional"]                                     # "as an optional rim"
    assert [["tmRootGain"], ["tmTanh"]] in xray["alternatives"]
    hexn = tier("hex-neon")
    assert [["patCellDelay"], ["patRadialWave"]] in hexn["alternatives"]
    assert [["palCos"], ["palPitchFifths"]] in hexn["alternatives"]
    assert [["cmpAdd"], ["cmpXor"]] in hexn["alternatives"]
    assert "latHexNeighbourMin" in hexn["optional"]
    assert {"aaStroke", "glowExp", "latHex", "hash21"} <= set(hexn["required"])
    fog = tier("volume-fog")
    assert [["fbmGrad3", "shpRemap"], ["densFromSDF"]] in fog["alternatives"]     # "fbm3 shaped by shpRemap, or ..."
    assert [["volLightOneTap"], ["volLightMarch"]] in fog["alternatives"]
    sky = tier("sky-dressing")
    assert "skyMountainSilhouette" in sky["optional"] and "skyGradient" in sky["required"]


def test_a_hook_named_in_a_recipe_is_a_hook_not_a_loose_name(data):
    # Review defect 4: glow-xray marches "over the hook `mapScene`" but recorded no hooks.
    g = groups(data)
    assert g["glow-xray"]["hooks"] == ["mapScene"] and "mapScene" not in g["glow-xray"]["other_names"]
    assert g["studio-object"]["hooks"] == ["mapScene", "materialAt"]
    assert g["studio-object"]["hook_signatures"]["mapScene"] == "float mapScene(vec3 p)"
    assert all("mapScene" not in x["other_names"] for x in data["groups"])


def test_the_build_manifest_is_exactly_the_p0_set(data):
    p0 = {fn for p in data["parts"] if p["status"] == "P0" for fn in p["functions"]}
    files = data["manifest"]
    # Atlas draft section 18: "Batch A is 31 files ...; batch B is 34 files (six of them group recipes)". The rulings
    # add two batch-B files (atmos/sky.glsl for skyGradient, draw2/pattern.glsl for patCellDelay) and names to four
    # existing rows; each touched row names its rulings.
    drafted = [f for f in files if not f.get("added_by_ruling")]
    assert Counter(f["batch"] for f in drafted) == {"A": 31, "B": 34}
    assert Counter(f["batch"] for f in files) == {"A": 31, "B": 36}
    assert sum(1 for f in files if f["batch"] == "B" and f["kind"] == "recipe") == 6
    assert len({f["file"] for f in files}) == len(files)
    listed = [fn for f in files for fn in f["functions"]]
    assert len(listed) == len(set(listed))
    assert set(listed) == p0, (sorted(set(listed) - p0), sorted(p0 - set(listed)))
    by_file = {f["file"]: f for f in files}
    assert by_file["light/env.glsl"]["functions"][0] == "StudioParams"     # a struct is declared before its users
    assert by_file["light/rigs.glsl"]["functions"][0] == "LitSurface"
    assert by_file["colour/palette.glsl"]["functions"][0] == "PitchPalette"
    assert "envBreath" in by_file["motion/envelope.glsl"]["functions"]
    assert by_file["atmos/sky.glsl"]["functions"] == ["skyGradient"] and by_file["atmos/sky.glsl"]["batch"] == "B"
    assert by_file["draw2/pattern.glsl"]["functions"] == ["patCellDelay"]
    for f in ("light/env.glsl", "light/rigs.glsl", "colour/palette.glsl", "motion/envelope.glsl", "atmos/sky.glsl",
              "draw2/pattern.glsl"):
        assert by_file[f]["rulings"], f


def test_a_part_listed_in_the_manifest_lives_in_the_manifest_file(data):
    where = {fn: f["file"] for f in data["manifest"] for fn in f["functions"]}
    for p in data["parts"]:
        for fn in p["functions"]:
            if fn in where:
                assert p["module"] == where[fn], (p["id"], fn, p["module"], where[fn])


# ---------- the dissector's tags ----------

def test_every_mapped_tag_lands_on_atlas_categories(data, A):
    cats = {c["id"] for c in data["categories"]}
    for table in ("exact", "groups"):
        for tag, ids in data["tags"][table].items():
            assert ids and set(ids) <= cats, (table, tag, ids)


def test_every_tag_the_dissector_can_emit_resolves_to_a_category(data, A):
    if not DISSECT.exists():
        pytest.skip("the dissector has not landed on this machine")
    tags = A.dissector_tags(DISSECT)
    assert len(tags) > 40, "the TAGS table was not read; the regex no longer fits dissect.py"
    missing = [t for t in tags if not A.categories_for_tag(t, data)]
    assert not missing


# ---------- built versus planned, against the module library ----------

def test_every_built_library_module_sits_in_an_atlas_category(data, A):
    from arsenal.shaders import modules as M
    lib = M.load_library()
    root = M.LIBRARY_DIR.resolve()
    built = [n for n, m in lib.modules.items() if root in Path(m.path).resolve().parents]
    if not built:   # the review: with no module built this pin checked nothing; say so instead of passing
        pytest.skip("arsenal/web/glsl/ holds no library module yet (the synthetic pin below exercises check_library)")
    assert A.check_library(data, lib) == []


def test_a_library_module_in_an_unknown_category_is_named(tmp_path, data, A):
    from arsenal.shaders import modules as M
    d = tmp_path / "glsl"
    write_module(d / "core", "shaping.glsl", {"name": "shaping", "kind": "helper", "cat": "A5", "family": "A"},
                 STUB_LINSTEP)
    write_module(d / "odd", "odd.glsl", {"name": "odd", "kind": "helper", "cat": "Z9"},
                 "float oddThing(float x) { return x; }\n")
    write_module(d / "fam", "fam.glsl", {"name": "fam", "kind": "helper", "cat": "B3", "family": "C"},
                 "float famThing(float x) { return x; }\n")
    problems = A.check_library(data, M.load_library([d]), library_dir=d)
    assert len(problems) == 2
    assert any("odd" in p and "Z9" in p for p in problems)
    assert any("fam" in p and "B3" in p for p in problems)


def test_built_state_compares_the_plan_with_the_library(tmp_path, data, A):
    from arsenal.shaders import modules as M
    d = tmp_path / "glsl"
    write_module(d / "core", "shaping.glsl", {"name": "shaping", "kind": "helper", "cat": "A5", "family": "A"},
                 STUB_LINSTEP)
    state = A.part_states(data, M.load_library([d]), library_dir=d)
    part = next(p for p in data["parts"] if "shpLinstep" in p["functions"])
    assert state[part["id"]] == "built"
    other = next(p for p in data["parts"] if "shpSmoother" in p["functions"])
    assert state[other["id"]] == "planned"


# ---------- the atlas follows the built library (batch-A review, defect 3) ----------
# WHY: the collision ledger and anything generated from the atlas read the atlas, not the library. When the library
# exposes a name the atlas does not plan, or takes parameters the atlas does not show, the two disagree silently: a
# later module could claim the name, and code generated from the atlas would call a function that does not exist.

# `in`, `const` and precision change nothing a caller does; `out` and `inout` do (batch-B review, defect 3: camOrthoRay's
# `out vec3 ro` became `inout`, so a caller following the atlas would pass ro uninitialised), so they stay in the type.
_QUALIFIERS = frozenset("in const highp mediump lowp".split())
_DECL = re.compile(r"([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\(([^()]*)\)")


def _param_types(params: str) -> list:
    """['vec3', 'inout float'] for 'in vec3 p, inout float k'; ['...'] for a signature the draft left short."""
    out = []
    for p in ([] if params.strip() in ("", "void") else params.split(",")):
        words = [w for w in p.split() if w not in _QUALIFIERS]
        if not words or words[0] == "...":
            out.append("...")
            continue
        direction = words.pop(0) + " " if words[0] in ("out", "inout") and len(words) > 1 else ""
        out.append(direction + re.sub(r"\[.*$", "", words[0]))
    return out


def _built_definitions(lib) -> dict:
    """Function name -> [(return type, parameter types)] for every definition in a library module."""
    from arsenal.shaders import modules as M
    root = M.LIBRARY_DIR.resolve()
    out: dict = {}
    for m in lib.modules.values():
        if root not in Path(m.path).resolve().parents:
            continue
        for d in M.DEFINITION_RE.finditer(M.strip_comments(m.body)):
            out.setdefault(d.group(2), []).append((d.group(1), _param_types(d.group(3))))
    return out


@pytest.fixture(scope="module")
def library():
    from arsenal.shaders import modules as M
    return M.load_library()


def test_every_name_the_built_library_provides_is_planned(data, A, library):
    have = A.library_providers(library)
    if not have:
        pytest.skip("arsenal/web/glsl/ holds no library module yet")
    assert sorted(set(have) - planned(data)) == []


def test_every_built_function_has_the_signature_the_atlas_shows(data, library):
    built = _built_definitions(library)
    if not built:
        pytest.skip("arsenal/web/glsl/ holds no library module yet")
    wrong, checked = [], 0
    for p in data["parts"]:
        for fn in p["functions"]:
            shown = [(ret, _param_types(params)) for ret, name, params in _DECL.findall(p["signature"]) if name == fn]
            if fn not in built or not shown:
                continue
            checked += 1
            if not any(s in built[fn] for s in shown):
                wrong.append((p["id"], fn, shown, built[fn]))
    assert checked >= 100, checked          # the batch-A library alone has well over a hundred
    assert wrong == []


def test_signatures_the_build_settled_are_rulings_that_keep_the_draft_text(data):
    own = owners(data)
    rulings = {r["id"]: r for r in data["rulings"]}
    for fn, spelled in BUILT_SIGNATURES.items():
        p = own[fn]
        assert spelled in p["signature"], (fn, p["signature"])
        assert "(...)" not in p["signature"] and ", ...)" not in p["signature"], p["signature"]
        rid = f"built-sig-{fn}"
        assert rid in p["rulings"], (fn, p.get("rulings"))
        r = rulings[rid]
        assert r["kind"] == "built-signature" and r["names"] == [fn] and r["part"] == p["id"]
        assert r["reason"] and r["source"] and r["to"] in p["signature"] and r["from"] in p["signature_draft"]
        assert r["from"] not in p["signature"]


def test_helpers_the_draft_never_planned_are_parts_at_their_modules_status(data, library):
    from arsenal.shaders import modules as M
    own = owners(data)
    rulings = {r["id"]: r for r in data["rulings"]}
    by_file = {f["file"]: f for f in data["manifest"]}
    cats = {c["id"]: c for c in data["categories"]}
    for fn, module in BUILT_HELPERS.items():
        p = own[fn]
        assert (p["module"], p["kind"], p["form"]) == (module, "function", "ruling"), (fn, p)
        assert module in cats[p["category"]]["modules"] and p["contract"] and p["signature"]
        r = rulings[p["ruling"]]
        assert r["kind"] == "plan-built" and fn in r["names"] and r["part"] == p["id"] and r["reason"] and r["source"]
        assert r["status"] == p["status"] and r["module"] == module
        path = M.LIBRARY_DIR / module
        if path.exists():       # at the status of its module: the header's own word
            header = M.parse_module(path.read_text(encoding="utf-8"), str(path)).header
            assert p["status"] == header["status"], (fn, p["status"], header["status"])
        if p["status"] == "P0":
            assert fn in by_file[module]["functions"] and p["ruling"] in by_file[module]["rulings"]
    # one part per module, the pair in it
    parts = {own[fn]["id"] for fn in BUILT_HELPERS}
    assert len(parts) == 3
    assert own["palPitchPiano"]["types"] == ["PitchPalette"]     # its struct is planned no later (the closure holds)


def _definitions_text(m) -> list:
    """'ret name(param, param)' for every function a module defines, in file order, whitespace normalised."""
    from arsenal.shaders import modules as M
    out = []
    for d in M.DEFINITION_RE.finditer(M.strip_comments(m.body)):
        params = ", ".join(" ".join(p.split()) for p in d.group(3).split(",")) if d.group(3).strip() else ""
        out.append(f"{d.group(1)} {d.group(2)}({params})")
    return out


def test_every_recipe_module_is_planned_function_for_function_with_its_built_signatures(data, library):
    # The judge's ruling (c) on the batch-B review: a group recipe exposes its entry and its own steps by name
    # (hexNeonCell, studioObjectRig, neonProfile, ...), the draft plans none of them, and a name nobody plans is a name
    # a later module can claim. So each recipe module is one P0 part: every function it provides, in the module
    # header's own category, at the module's status, its signature the built one, recorded by a plan-recipe ruling.
    from arsenal.shaders import modules as M
    root = M.LIBRARY_DIR.resolve()
    by_path = {Path(m.path).resolve().relative_to(root).as_posix(): m for m in library.modules.values()
               if root in Path(m.path).resolve().parents}
    built_recipes = {f for f, m in by_path.items() if m.kind == "recipe" and f.startswith("groups/")}
    assert built_recipes == set(RECIPE_MODULES), sorted(built_recipes ^ set(RECIPE_MODULES))
    own = owners(data)
    rulings = {r["id"]: r for r in data["rulings"]}
    cats = {c["id"]: c for c in data["categories"]}
    rows = {f["file"]: f for f in data["manifest"]}
    for file, group in RECIPE_MODULES.items():
        m = by_path[file]
        assert all(fn in own for fn in m.provides), (file, [fn for fn in m.provides if fn not in own])
        parts = {own[fn]["id"] for fn in m.provides}
        assert len(parts) == 1, (file, parts)
        p = own[m.provides[0]]
        assert set(p["functions"]) == set(m.provides), (file, p["functions"], m.provides)
        assert (p["module"], p["kind"], p["form"], p["status"]) == (file, "recipe", "ruling", m.header["status"])
        assert p["category"] == m.header["cat"] and file in cats[p["category"]]["modules"]
        assert p["signature"].split(" / ") == _definitions_text(m), file          # every built signature, as built
        r = rulings[p["ruling"]]
        assert r["kind"] == "plan-recipe" and r["part"] == p["id"] and r["module"] == file and r["group"] == group
        assert r["names"] == p["functions"] and r["reason"] and r["source"]
        assert file in groups(data)[group]["modules"]
        assert rows[file]["kind"] == "recipe" and rows[file]["functions"] == p["functions"]
        assert p["ruling"] in rows[file]["rulings"]


# ---------- queries and the door ----------

def test_queries_filter_by_family_category_and_status(data, A):
    assert all(p["family"] == "B" for p in A.query(data, family="B"))
    b3 = A.query(data, category="B3")
    assert b3 and all(p["category"] == "B3" for p in b3)
    assert len(A.query(data, status="P0")) == COUNTS_AFTER_RULINGS["by_status"]["P0"]
    assert len(A.query(data, family="h", status="p0")) == len(A.query(data, family="H", status="P0"))


def run_door(argv, capsys):
    from arsenal.shaders import atlas as _  # noqa: F401  (registers the verb)
    from arsenal.shaders import cli
    ns = cli.build_parser().parse_args(argv)
    rc = ns.fn(ns) or 0
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def test_the_atlas_verb_lists_the_p0_rows(capsys):
    rc, out, _ = run_door(["atlas", "--status", "P0", "--json"], capsys)
    rows = json.loads(out)
    assert rc == 0 and len(rows) == COUNTS_AFTER_RULINGS["by_status"]["P0"] and all(r["status"] == "P0" for r in rows)
    rc, out, _ = run_door(["atlas", "--status", "p0", "--family", "f", "--json"], capsys)    # filters ignore case
    assert rc == 0 and json.loads(out) and all(r["family"] == "F" for r in json.loads(out))


def test_the_atlas_verb_summarises_by_family_without_filters(capsys):
    rc, out, _ = run_door(["atlas"], capsys)
    assert rc == 0
    assert "Foundations" in out and f"{COUNTS_AFTER_RULINGS['parts']} parts" in out
    assert f"P0 {COUNTS_AFTER_RULINGS['by_status']['P0']}" in out


@pytest.mark.parametrize("argv", [["atlas", "--status", "P3"], ["atlas", "--family", "Z"],
                                  ["atlas", "--category", "ZZ9"], ["atlas", "--family", "B", "--category", "C1"]])
def test_the_atlas_verb_refuses_a_filter_that_names_nothing(argv, capsys):
    # Review defect 6: a bad filter printed "0 parts" and exited 0, so a typo looked like an empty bin.
    rc, out, err = run_door(argv, capsys)
    assert rc == 2 and "0 parts" not in out
    assert "atlas:" in err


def test_the_atlas_verb_is_loaded_by_the_shader_door():
    from arsenal.shaders import cli
    import inspect
    assert '"atlas"' in inspect.getsource(cli._load_extensions)


# ---------- the data is exactly what the converter makes of the draft ----------

def test_atlas_json_is_what_the_converter_makes_of_the_draft():
    if not DRAFT.exists():
        pytest.skip("the atlas draft has moved; regenerate from its new home")
    from arsenal.shaders import atlas_build
    fresh = atlas_build.build(DRAFT)
    stored = json.loads(ATLAS_JSON.read_text(encoding="utf-8"))
    assert fresh == stored, "atlas.json is stale: run py -m arsenal.shaders.atlas_build"


def test_atlas_json_has_lf_line_endings():
    assert b"\r\n" not in ATLAS_JSON.read_bytes()


# Review defect 2: a revised draft could misfile or drop rows without the converter noticing. Each mutation below is
# one the reviewer demonstrated (or its sibling); the converter must refuse it, never write a smaller or wrong atlas.
MALFORMED = [
    ("a category heading loses its dot, so its table would be filed under the category above",
     "### B6. Periodic", "### B6 Periodic"),
    ("a table row gains a leading space, which used to end the table and drop the rows after it",
     "\n| `float patCellDelay(", "\n | `float patCellDelay("),
    ("a blank line splits a primitive table, which used to drop the rest of it",
     "\n| `float patCellDelay(", "\n\n| `float patCellDelay("),
    ("a family heading loses its colon, so its categories would sit outside any family",
     "## 4. Family B: Noise", "## 4. Family B Noise"),
    ("a category heading names no module file", "### B6. Periodic and looping noise (`noise/periodic.glsl`)",
     "### B6. Periodic and looping noise"),
    ("a category's table header is altered, so its rows would belong to no table",
     "### B6. Periodic and looping noise (`noise/periodic.glsl`)\n\n| signature | contract | cost | loved | learn | P |",
     "### B6. Periodic and looping noise (`noise/periodic.glsl`)\n\n| signature | contract | cost | loved | learn | P"),
    ("a blank line splits the loved-shader legend", "\n| Hexagone | wsl3WB |", "\n\n| Hexagone | wsl3WB |"),
    ("a primitive row loses a cell", "| `float patCellDelay(vec2 cellId, vec2 centre, float speed)` |",
     "| `float patCellDelay(vec2 cellId, vec2 centre, float speed)` | | |"),
    ("a P0 group's recipe bullet loses its form, so the closure check would pass vacuously",
     "- **Recipe:** `camRay` → loop with `rmPassStep`", "- **Recipe**: `camRay` → loop with `rmPassStep`"),
    # The re-review: tables outside the primitive tables, and bullets inside multi-tier group cards, could still be
    # split or misread without a refusal (the pins on 25 groups and 42 shaders caught it at test time, but the converter
    # wrote the smaller atlas).
    ("a prose line splits the groups table, which used to keep 6 groups of 25",
     "\n| **volume-fog** |", "\nThe P1 groups follow.\n| **volume-fog** |"),
    ("two blank lines split the groups table, which used to keep 6 groups of 25",
     "\n| **volume-fog** |", "\n\n\n| **volume-fog** |"),
    ("a prose line splits the loved-shader legend, which used to keep 32 shaders of 42",
     "\n| Hexagone | wsl3WB |", "\nAnd the rest.\n| Hexagone | wsl3WB |"),
    ("two blank lines split the loved-shader legend, which used to keep 32 shaders of 42",
     "\n| Hexagone | wsl3WB |", "\n\n\n| Hexagone | wsl3WB |"),
    ("a tier bullet's colon slips outside the bold, so the P1 volume tier joined the P0 sheet tier",
     "- **Recipe, volume tier (family C, P1):**", "- **Recipe, volume tier (family C, P1)**:"),
    ("a tier bullet's label is misspelled, so the tier was dropped",
     "- **Recipe, volume tier (family C, P1):**", "- **Recipie, volume tier (family C, P1):**"),
    ("a recipe's continuation line loses its indent, so the rest of the tier was dropped",
     "\n  `volStepEmit` → `displayHueSafeGamma`.", "\n`volStepEmit` → `displayHueSafeGamma`."),
    ("a hooks bullet's colon slips outside the bold, so the hook signatures were dropped",
     "- **Hooks:** `float mapScene(vec3 p)`;", "- **Hooks**: `float mapScene(vec3 p)`;"),
    ("a hooks bullet loses its code spans, so the hook signatures were dropped",
     "- **Hooks:** `float mapScene(vec3 p)`; `vec3 materialAt(vec3 p, vec3 n, float id)`.",
     "- **Hooks:** float mapScene(vec3 p); vec3 materialAt(vec3 p, vec3 n, float id)."),
    ("a brief's tier loses its sentence break, so the marched tier joined the analytic tier",
     "`aaDiscriminantEdge`. Marched tier:", "`aaDiscriminantEdge`; Marched tier:"),
]


@pytest.mark.parametrize("why, old, new", MALFORMED, ids=[m[0][:40] for m in MALFORMED])
def test_the_converter_refuses_a_malformed_draft(tmp_path, draft_text, why, old, new):
    from arsenal.shaders import atlas_build
    text = draft_text.replace("\r\n", "\n")
    assert old in text, f"the mutation no longer fits the draft: {old[:60]!r}"
    bad = tmp_path / "draft.md"
    bad.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError):
        atlas_build.build(bad)


UNCLOSED = [
    ("a P0 recipe step loses its 'optional', so a P1 part becomes a requirement no ruling covers",
     "→ optional `latHexNeighbourMin` for oversized shapes", "→ `latHexNeighbourMin` for oversized shapes",
     "latHexNeighbourMin"),
    ("the draft itself makes a promoted part P0, so the promotion ruling is stale",
     "study:MsjfRG 6.7 | P1 |", "study:MsjfRG 6.7 | **P0** |", "envBreath"),
]


@pytest.mark.parametrize("why, old, new, named", UNCLOSED, ids=[u[0][:40] for u in UNCLOSED])
def test_the_converter_refuses_a_draft_whose_p0_set_is_not_closed(tmp_path, draft_text, why, old, new, named):
    # The closure is checked on every build, not only pinned on today's data: a revision that adds a P1 requirement
    # to a P0 group (or makes a ruling stale) stops at the converter until a judge rules.
    from arsenal.shaders import atlas_build
    text = draft_text.replace("\r\n", "\n")
    assert text.count(old) == 1, f"the mutation no longer fits the draft: {old[:60]!r}"
    bad = tmp_path / "draft.md"
    bad.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match=named):
        atlas_build.build(bad)


STALE_BUILT = [
    ("the draft now gives displayOut its res, so the built-signature ruling is stale",
     "`vec3 displayOut(vec3 sceneLin, vec2 pixel, float ev,", "`vec3 displayOut(vec3 sceneLin, vec2 pixel, vec2 res, float ev,",
     "displayOut"),
    ("the draft now plans oklchCusp itself, so the built-helper ruling is stale",   # in a P1 row: no manifest gap
     "| `vec3 gradeSaturationOklab(vec3 lin, float s)` |",
     "| `vec3 gradeSaturationOklab(vec3 lin, float s)` / `vec2 oklchCusp(float h)` |", "oklchCusp"),
]


@pytest.mark.parametrize("why, old, new, named", STALE_BUILT, ids=[s[0][:40] for s in STALE_BUILT])
def test_the_converter_refuses_a_built_library_ruling_the_draft_has_overtaken(tmp_path, draft_text, why, old, new,
                                                                              named):
    # A ruling that follows the library must not silently stack on a draft that already says the same thing (or now
    # plans the name itself, which would plan it twice): the converter names the stale ruling instead.
    from arsenal.shaders import atlas_build
    text = draft_text.replace("\r\n", "\n")
    assert text.count(old) == 1, f"the mutation no longer fits the draft: {old[:60]!r}"
    bad = tmp_path / "draft.md"
    bad.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match=named):
        atlas_build.build(bad)


def test_ruling_a_applies_to_a_type_a_revised_draft_introduces(tmp_path, draft_text):
    # Ruling (a) is a rule, not a list: a new type in a P0 signature becomes a P0 struct in its first user's module and
    # joins that module's manifest row ahead of its users.
    from arsenal.shaders import atlas_build
    old = "`vec3 litFloorPool(vec3 p, vec3 centre, float radius, vec3 col)`"
    text = draft_text.replace("\r\n", "\n")
    assert text.count(old) == 1
    bad = tmp_path / "draft.md"
    bad.write_text(text.replace(old, "`vec3 litFloorPool(vec3 p, PoolLight pl)`"), encoding="utf-8", newline="\n")
    atlas = atlas_build.build(bad)
    p = next(q for q in atlas["parts"] if q["functions"] == ["PoolLight"])
    assert (p["kind"], p["status"], p["module"]) == ("struct", "P0", "light/env.glsl")
    row = next(r for r in atlas["manifest"] if r["file"] == "light/env.glsl")
    assert row["functions"][:2] == ["PoolLight", "StudioParams"] or row["functions"][:2] == ["StudioParams",
                                                                                             "PoolLight"]
    assert atlas["counts"]["by_status"]["P0"] == COUNTS_AFTER_RULINGS["by_status"]["P0"] + 1


def _with_rows_after_volaccum(draft_text: str, rows) -> str:
    text = draft_text.replace("\r\n", "\n")
    anchor = next(line for line in text.split("\n") if line.startswith("| `struct VolAccum"))
    return text.replace(anchor, anchor + "\n" + "\n".join(rows), 1)


def test_ruling_a_plans_a_type_that_only_a_struct_field_uses(tmp_path, draft_text):
    # The re-review: a struct-only row whose field uses a type planned nowhere, where another row uses that struct, made
    # plan_types crash with IndexError (no function "takes" the type, only the struct does).
    from arsenal.shaders import atlas_build
    bad = tmp_path / "draft.md"
    bad.write_text(_with_rows_after_volaccum(draft_text, [
        "| `struct Wrap { Inner i; }` | test | C0 | — | — | P1 |",
        "| `float useWrap(Wrap w)` | test | C0 | — | — | P1 |",
    ]), encoding="utf-8", newline="\n")
    atlas = atlas_build.build(bad)
    own = {fn: p for p in atlas["parts"] for fn in p["functions"]}
    inner, wrap = own["Inner"], own["Wrap"]
    assert (inner["kind"], inner["status"], inner["module"]) == ("struct", "P1", wrap["module"])
    rule = next(r for r in atlas["rulings"] if r["names"] == ["Inner"])
    assert rule["kind"] == "plan-struct" and "Wrap" in rule["reason"]


def test_ruling_a_refuses_a_split_that_would_leave_a_hollow_part(tmp_path, draft_text):
    # The re-review: a row that declares only a struct, at a later status than a user, was split into a struct part and
    # a hollow part of kind 'function' with no functions. That needs a judge, not a silent empty row.
    from arsenal.shaders import atlas_build
    bad = tmp_path / "draft.md"
    bad.write_text(_with_rows_after_volaccum(draft_text, [
        "| `struct Solo { vec3 a; }` | test | C0 | — | — | P2 |",
        "| `float useSolo(Solo s)` | test | C0 | — | — | P1 |",
    ]), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="Solo"):
        atlas_build.build(bad)


def test_main_names_a_relative_out_path_inside_the_repo(tmp_path, monkeypatch, capsys):
    # The re-review: `--out arsenal/shaders/atlas.json`, typed relative from the repo root, wrote the file and then
    # crashed on out.relative_to(ROOT) (a relative path is never relative_to an absolute one), exiting 1.
    from arsenal.shaders import atlas_build
    root = tmp_path.resolve()
    monkeypatch.setattr(atlas_build, "ROOT", root)
    monkeypatch.setattr(atlas_build, "build", lambda draft: {"counts": {"parts": 1}})
    monkeypatch.chdir(root)
    (root / "sub").mkdir()
    assert atlas_build.main(["--out", "sub/atlas.json"]) == 0
    assert (root / "sub" / "atlas.json").read_text(encoding="utf-8") == '{\n "counts": {\n  "parts": 1\n }\n}\n'
    assert "wrote sub/atlas.json" in capsys.readouterr().out


def test_a_refused_draft_writes_nothing(tmp_path, draft_text):
    from arsenal.shaders import atlas_build
    bad = tmp_path / "draft.md"
    bad.write_text(draft_text.replace("### B6. Periodic", "### B6 Periodic", 1), encoding="utf-8", newline="\n")
    out = tmp_path / "atlas.json"
    with pytest.raises(ValueError):
        atlas_build.main(["--draft", str(bad), "--out", str(out)])
    assert not out.exists()
    good = tmp_path / "good.json"
    assert atlas_build.main(["--draft", str(DRAFT), "--out", str(good)]) == 0
    assert good.read_bytes() == ATLAS_JSON.read_bytes()
