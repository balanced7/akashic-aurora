"""py -m arsenal.shaders.atlas_build [--check] [--out PATH] -- turn the primitive atlas draft (a Markdown document) into
atlas.json.

WHY A CONVERTER, NOT A HAND-TYPED JSON FILE. The atlas draft (research/in-flight/shader-school-2026-10-13/
primitive-atlas-draft.md) is the document people read and Daniel gates; atlas.json is the same parts list for machines
(the `atlas` verb, the lab, the dissector's tag map, the Shelf). Two hand-kept copies of one list drift the first time
someone edits one of them, so the data is GENERATED from the document and a pin (tests/test_glsl_atlas.py) fails when
atlas.json no longer equals what this file makes of the draft. Revise the draft, run this, commit both.

WHAT IT READS, all from the draft's own tables:
  - the family map (section 2) and the family headings ("## 3. Family A: Foundations");
  - each category heading ("### B3. Fractal sums (`noise/fbm.glsl`)") and its primitive table (signature, contract,
    cost, loved, learn, P), one PART per row;
  - the loved-shader legend (0.3), so exemplars are stored as shader ids, never as code;
  - the collision ledger (1.1), the groups (16.1 plus the recipe cards 16.2-16.8, read tier by tier, with each part
    marked required, optional or one of several alternatives) and the P0 build manifest (18).

IT REFUSES A DRAFT IT CANNOT READ CLEANLY. A revised draft can lose a heading's dot, indent a row, split a table with
a prose line or blank lines, or slip a bullet's colon outside its bold; read leniently, each of those silently files
rows under the wrong category or tier, or drops them. So every such shape raises ValueError naming the draft line, and
nothing is written: a malformed draft never becomes a smaller atlas. Every run of table lines anywhere in the draft must
be one whole table (header, |---| rule, rows, one indent), and every line of a group card or brief must be a bullet
with a known label, an indented continuation, or blank.

WHAT IT DECIDES, because the draft leaves it open (each is a table below, so a reviewer can overrule it in one line), and
every decision is recorded with its reason in atlas.json's `rulings` list:
  - RENAMES. The draft names the canonical fBm `fbm2`/`fbm3`, which collides with the bench chunk value-noise-3d. The
    judge's ruling 3 (build-spec-reconciled.md) keeps the chunks as they are and has the library choose its own name.
    The naming law already spells gradient noise `noiseGrad` and derivatives `Deriv` (`noiseGrad2Deriv`), so the
    fBm-of-gradient-noise pair becomes `fbmGrad2`/`fbmGrad3` and its derivative `fbmGrad2Deriv`; the chunk keeps `fbm3`.
    LEDGER_OWNER_RULINGS rewrites the one ledger row whose prose still describes the overruled rename.
  - THE P0 CLOSURE (the judge's rulings on the S0 review). The P0 set must be buildable from P0 parts alone. Ruling (a):
    every non-GLSL type a planned signature uses is planned, as a struct part in the module of its first user (in draft
    order), at the earliest status of any part that uses it; this is a rule, applied to every such type. Ruling (b):
    every part a P0 group tier requires is P0; PROMOTIONS names the parts promoted (the judge picked patCellDelay where
    the hex-neon recipe offers two P1 alternatives). The converter then CHECKS the closure and refuses a draft that
    breaks it, so a revision that adds a new P1 requirement to a P0 group stops here until a judge rules.
  - Which module FILE a part lives in, when its category heading names several files: section 18's manifest first,
    then MODULE_RULES (by name prefix), then the heading's first file.
  - Family M (compositing) has a table but no category heading; it becomes category M1.
  - The dissector's technique tags map onto categories through TAG_CATEGORIES (exact) and TAG_GROUP_CATEGORIES (by
    the tag's group, so a tag the dissector adds later still lands somewhere sensible).

THE LICENCE LINE. The draft is our own words: techniques described in prose and mathematics, loved shaders named by
short name and id. Nothing here reads the corpus, so nothing of other people's code can reach atlas.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

API = "arsenal.shader-atlas/v1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DRAFT = ROOT / "research" / "in-flight" / "shader-school-2026-10-13" / "primitive-atlas-draft.md"
RULINGS = ROOT / "research" / "in-flight" / "shader-school-2026-10-13" / "build-spec-reconciled.md"
DISSECT = HERE / "dissect.py"
OUT = HERE / "atlas.json"

# ---------- the decisions this converter makes (see the docstring) ----------

RENAMES: Dict[str, str] = {"fbm2": "fbmGrad2", "fbm3": "fbmGrad3", "fbm2Deriv": "fbmGrad2Deriv"}
RENAME_RULING = ("build-spec-reconciled.md ruling 3: no rename of the legacy chunks tonight; the library avoids the "
                 "clash by choosing its own name. The legacy chunk value-noise-3d keeps fbm3 and vn; the house "
                 "fBm of gradient noise is fbmGrad2/fbmGrad3 (the naming law's own vocabulary: noiseGrad, Deriv).")
RENAME_SOURCE = "build-spec-reconciled.md ruling 3"
JUDGE = "the judge's rulings on the S0 adversarial review, 2026-10-13 (the P0 closure gap)"

# The ledger row whose owner text describes the rename ruling 3 overruled: draft owner text (cleaned) -> (owner, why).
LEDGER_OWNER_RULINGS: Dict[str, Tuple[str, str]] = {
    "fbm3 in noise/fbm.glsl, after the legacy chunk's functions are renamed (architecture slice S2)": (
        "fbmGrad3 in noise/fbm.glsl; the legacy chunk value-noise-3d keeps fbm3 and vn",
        "ruling 3 renames no legacy chunk tonight, so the library takes its own name in the naming law's vocabulary "
        "(noiseGrad for gradient noise, as in noiseGrad2Deriv) and nothing clashes"),
}

# Judge's ruling (b): parts a P0 group tier needs that the draft left at P1, promoted to P0. Name -> why. The converter
# adds which group and tier need each one, and refuses a promotion that no P0 tier needs (a stale ruling).
PROMOTIONS: Dict[str, str] = {
    "envBreath": ("the aurora band tier (P0) requires it (`envBreath` along x, the two-timescale breathing of Aurora "
                  "Lights and AuroraBorealis) and names no alternative"),
    "skyGradient": ("the aurora band tier (P0) composites over it (`cmpAdd` over `skyGradient`) and names no "
                    "alternative"),
    "patCellDelay": ("the hex-neon recipe (P0) needs `patCellDelay` or `patRadialWave` for a per-cell size and the "
                     "draft left both at P1; one is enough, and the judge chose patCellDelay (Pretty Hip's per-cell "
                     "delay, the quantised mosaic wave front)"),
}

# Family M's table sits directly under its family heading.
SYNTHETIC_CATEGORIES: Dict[str, Tuple[str, str, List[str]]] = {
    "M": ("M1", "Compositing", ["composite/blend.glsl"]),
}

# Categories whose heading names several files: (name regex, file), first match wins. Anything section 18 places is
# placed by section 18 before these rules run.
MODULE_RULES: Dict[str, List[Tuple[str, str]]] = {
    "A1": [(r"^(PI|TAU|PHI|SQRT3)$", "core/const.glsl"), (r"^rotate", "core/rotate.glsl"), (r".", "core/safe.glsl")],
    "A2": [(r"^unrollBarrier$", "core/compile.glsl"), (r".", "core/int.glsl")],
    "A6": [(r"^hashSine", "legacy/hash-sine.glsl"), (r"^hashHoskins", "legacy/hash-hoskins.glsl"),
           (r".", "hash/pcg.glsl")],
    "A7": [(r"^testcard", "debug/testcards.glsl"), (r".", "debug/views.glsl")],
    "B1": [(r"^noiseValue", "noise/value.glsl"), (r"^noiseGrad", "noise/gradient.glsl"),
           (r"^noiseSimplex", "noise/simplex.glsl"), (r"^noiseTex", "noise/texture.glsl"),
           (r"^noise(Triangle|SineSum)", "noise/triangle.glsl")],
    "C7": [(r"^cx", "draw2/complex.glsl"), (r"^frac", "draw2/fractal2.glsl")],
    "G6": [(r"^stars", "atmos/stars.glsl"), (r".", "atmos/sky.glsl")],
    "H7": [(r"^vig", "post/vignette.glsl"), (r"^(bloom|blur|streak|karis)", "post/bloom.glsl"),
           (r".", "post/lens.glsl")],
    "I6": [(r"^seq", "motion/sequence.glsl"), (r".", "motion/mech.glsl")],
    "J4": [(r"^wave(Step|HeightNormal|CausticRatio)$", "sim/wave.glsl"), (r".", "sim/ocean.glsl")],
    "J5": [(r"^(ptc|clampLength|particle)", "sim/particle.glsl"), (r".", "sim/pattern.glsl")],
    "L1": [(r"^key", "input/keyboard.glsl"), (r".", "input/mouse.glsl")],
}

# The dissector's tags (arsenal/shaders/dissect.py TAGS) onto atlas categories. First id is the primary home.
TAG_CATEGORIES: Dict[str, List[str]] = {
    "raymarch.sphere_trace": ["E3"], "raymarch.fixed_step": ["G5", "E3"], "raymarch.jitter": ["E3", "B7"],
    "sdf.sphere": ["D1", "C1"], "sdf.box": ["D1", "C1"], "sdf.torus": ["D1"], "sdf.capsule": ["D1", "C1"],
    "sdf.cylinder": ["D1"], "sdf.octahedron": ["D1"], "sdf.named": ["D1"], "sdf.smooth_min": ["D3"],
    "domain.repeat": ["D4", "C4"], "domain.rotate2d": ["A1"], "domain.polar": ["C4"],
    "domain.kaleidoscope": ["C4"],
    "normal.central_diff": ["E4"], "normal.forward_diff": ["E4"], "normal.tetrahedral": ["E4"],
    "normal.screen_space": ["E4"],
    "lighting.soft_shadow": ["F5"], "lighting.hard_shadow": ["F5"], "lighting.ao": ["F5"],
    "lighting.diffuse": ["F1"], "lighting.specular": ["F2"], "lighting.fresnel": ["F3"], "lighting.fog": ["G7"],
    "noise.value": ["B1"], "noise.gradient": ["B1"], "noise.simplex": ["B1"], "noise.texture": ["B1"],
    "noise.fbm": ["B3"], "noise.domain_warp": ["B4"],
    "hash.sin_fract": ["A6"], "hash.integer": ["A6"], "hash.fract_dot": ["A6"],
    "fractal.kifs": ["D5", "C7"], "fractal.mandelbox": ["D5"], "fractal.inversion": ["D5", "C7"],
    "fractal.escape_time": ["C7"], "fractal.mandelbulb": ["D5"],
    "cellular.voronoi": ["B2"],
    "color.cosine_palette": ["H4"], "color.gamma": ["H1"], "color.gamma_decode": ["H1"], "color.srgb": ["H1"],
    "color.dither": ["H8", "B7"], "color.hsv": ["H3"], "color.vignette": ["H7"],
    "tonemap.reinhard": ["H5"], "tonemap.aces": ["H5"], "tonemap.filmic": ["H5"], "tonemap.tanh": ["H5"],
    "tonemap.exposure": ["H5"],
    "glow.march": ["F9"], "glow.accumulate": ["F9"],
    "volume.transmittance": ["G1"], "volume.front_to_back": ["G1", "M1"],
    "feedback.self": ["J6"], "feedback.cycle": ["J6"],
    "audio.input": ["L2"], "audio.sound_pass": ["L2"],
    "input.mouse": ["L1"], "input.keyboard": ["L1"],
    "animation.time": ["A3", "I1"], "animation.frame": ["A3"],
    "aa.supersample": ["E5"], "camera.lookat": ["E2"],
}
TAG_GROUP_CATEGORIES: Dict[str, List[str]] = {
    "raymarch": ["E3"], "sdf": ["D1"], "domain": ["C4", "D4"], "normal": ["E4"], "lighting": ["F1"],
    "noise": ["B1"], "hash": ["A6"], "fractal": ["D5", "C7"], "cellular": ["B2"], "color": ["H1"],
    "tonemap": ["H5"], "glow": ["F9"], "volume": ["G1"], "feedback": ["J6"], "audio": ["L2"], "input": ["L1"],
    "animation": ["I1"], "aa": ["C2", "E5"], "camera": ["E2"],
}

# ---------- small text helpers ----------

GLSL_TYPES = frozenset("""void bool int uint float vec2 vec3 vec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4 bvec2 bvec3 bvec4
mat2 mat3 mat4 sampler2D sampler3D const highp mediump lowp inout out in struct""".split())
GLSL_BUILTIN_TYPES = frozenset("""void bool int uint float vec2 vec3 vec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4 bvec2 bvec3
bvec4 mat2 mat3 mat4 mat2x2 mat2x3 mat2x4 mat3x2 mat3x3 mat3x4 mat4x2 mat4x3 mat4x4 sampler2D sampler3D samplerCube
sampler2DArray sampler2DShadow isampler2D usampler2D""".split())
QUALIFIERS = frozenset("const highp mediump lowp inout out in".split())
RANK = {"P0": 0, "P1": 1, "P2": 2}
IDENT = re.compile(r"^[A-Za-z_]\w*$")
TICKS = re.compile(r"`([^`]*)`")
CLASS = re.compile(r"\bC([0-4])\b")
REPORTS = "SR|NP|LM|VA|CP|PF|WS|GP"
SECTION = r"\d+(?:\.\d+)*(?:-\d+(?:\.\d+)*)?"
LEARN_PATTERNS = [
    re.compile(rf"\b(?:{REPORTS}) finding \d+"),
    re.compile(rf"\b(?:{REPORTS}) {SECTION}(?:, {SECTION}(?![\w.]))*(?: family [A-C]\b)?"),
    re.compile(r"study:\w+(?: \d+(?:\.\d+)*(?:-\d+(?:\.\d+)*)?)?"),
    re.compile(r"craft secret \d+"),
    re.compile(r"arc-[a-z]+(?:-[a-z]+)*(?: seam \d+)?(?: \([^)]*\))?"),
    re.compile(r"house chunk `?[\w-]+`?"),
    re.compile(r"shader-craft ceiling"),
]


def clean(text: str) -> str:
    """Markdown emphasis and code ticks off; one space between words."""
    return re.sub(r"\s+", " ", text.replace("**", "").replace("`", "")).strip()


def cells(line: str) -> List[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def strip_parens(text: str) -> str:
    """Remove every parenthetical (nested ones too): what is inside is commentary, not a name."""
    out, depth = [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def rename(name: str) -> str:
    return RENAMES.get(name, name)


def rename_text(text: str) -> str:
    for old, new in RENAMES.items():
        text = re.sub(rf"(?<![\w]){re.escape(old)}(?![\w])", new, text)
    return text


def names_in_signature(cell: str) -> List[str]:
    """The names a primitive row provides, as the draft spells them: each code span is a declaration, a bare name, a
    struct or a const list. Overloads in one row collapse to one name. RENAMES are applied by the caller."""
    out: List[str] = []
    for span in TICKS.findall(cell):
        span = span.strip()
        m = re.match(r"^const\s+\w+\s+(.+)$", span)
        if m:
            out += [n.strip() for n in m.group(1).split(",") if IDENT.match(n.strip())]
            continue
        m = re.match(r"^struct\s+(\w+)", span)
        if m:
            out.append(m.group(1))
            continue
        head = span.split("(")[0].strip().split()
        if head and IDENT.match(head[-1]) and head[-1] not in GLSL_TYPES:
            out.append(head[-1])
    return list(dict.fromkeys(out))


def types_in_signature(cell: str) -> List[str]:
    """Every non-GLSL type a signature cell USES (return, parameter and struct field types), in order of appearance.
    A struct the row declares counts as used only where a declaration in the row names it."""
    found: List[str] = []
    for span in TICKS.findall(cell):
        span = span.strip()
        m = re.match(r"^struct\s+\w+\s*\{(.*)\}", span)
        if m:
            decls = [d.strip() for d in m.group(1).split(";")]
        else:
            m = re.match(r"^(.*?)\b[A-Za-z_]\w*\s*\((.*)\)\s*$", span)
            if not m:
                continue
            ret = [w for w in m.group(1).split() if w not in QUALIFIERS]
            if ret:
                found.append(ret[-1])
            decls = [a.strip() for a in m.group(2).split(",")]
        for d in decls:
            words = [w for w in d.split() if w not in QUALIFIERS]
            if len(words) >= 2:
                found.append(re.sub(r"\[.*$", "", words[0]))
    return list(dict.fromkeys(t for t in found if IDENT.match(t) and t not in GLSL_BUILTIN_TYPES))


def cost_of(cell: str) -> Optional[str]:
    """The cost class to budget for: the largest class the cell names (a part that is C1 per sample but C3 overall is
    C3), so the lab's GPU gate never under-states a part."""
    found = CLASS.findall(cell)
    return f"C{max(int(c) for c in found)}" if found else None


def tex_of(cell: str) -> Optional[str]:
    m = re.search(r"\+T([^\s,;)]+)", cell)
    return m.group(1) if m else None


def learn_of(cell: str) -> Tuple[List[str], List[str]]:
    """(pointers into the house research and study notes, other primary sources named in prose)."""
    pointers: List[str] = []
    sources: List[str] = []
    for piece in cell.split(";"):
        rest = piece
        for pat in LEARN_PATTERNS:
            for m in pat.finditer(piece):
                hit = m.group(0)
                rest = rest.replace(hit, " ", 1)
                if re.match(rf"(?:{REPORTS}) \d", hit) and ", " in hit:
                    report, first = hit.split(" ", 1)[0], hit.split(" ", 1)[1]
                    suffix = re.search(r" family [A-C]$", first)
                    first = first[:suffix.start()] if suffix else first
                    for sec in first.split(", "):
                        pointers.append(f"{report} {sec}" + (suffix.group(0) if suffix else ""))
                else:
                    pointers.append(clean(hit))
        rest = clean(re.sub(r"\(`?[\w_]+`?\)", " ", rest)).strip(" ,.;")
        if rest and rest not in {"—", "-"} and re.search(r"[A-Za-z]{3}", rest):
            sources.append(rest)
    return pointers, sources


class Legend:
    """Short names of the 42 loved shaders, matched longest first and as whole phrases."""

    def __init__(self, rows: List[dict]):
        self.rows = rows
        self.by_short = {r["short"]: r["id"] for r in rows}
        self.order = sorted(self.by_short, key=len, reverse=True)

    def ids_in(self, cell: str) -> List[str]:
        text = " ".join(p for p in clean(cell).split(";") if not p.strip().lower().startswith("house"))
        text = strip_parens(text)
        found: List[Tuple[int, str]] = []
        for short in self.order:
            for m in re.finditer(rf"(?<![\w]){re.escape(short)}(?![\w])", text):
                found.append((m.start(), self.by_short[short]))
                text = text[:m.start()] + "\0" * len(short) + text[m.end():]
        seen, out = set(), []
        for _, sid in sorted(found):
            if sid not in seen:
                seen.add(sid)
                out.append(sid)
        return out


# ---------- the parser ----------

FAMILY_HEAD = re.compile(r"^## \d+\. Family ([A-M]): (.+)$")
CATEGORY_HEAD = re.compile(r"^### ([A-M]\d+)\. (.+)$")
MAP_LINE = re.compile(r"^([A-M])  (.+?) \.{2,} (.+)$")
PRIMITIVE_HEADER = "| signature | contract | cost | loved | learn | P |"
LEGEND_HEADER = "| short name | id | author | licence | passes |"
LEDGER_HEADER = "| proposed (report) | collides with | house owner and name | why |"
GROUPS_HEADER = "| group | one line | tiers and cost | exemplars | house landing | P |"
MANIFEST_HEADER = "| file (under `arsenal/web/glsl/`) | functions |"


TABLE_RULE = re.compile(r"\|(?:\s*:?-{3,}:?\s*\|)+")


def check_table_shapes(lines: List[str]) -> None:
    """Every run of lines that starts with '|' (outside fenced code) must be one whole table: a header, a |---| rule
    under it, then rows, all at one indent. A table split by a prose line or by blank lines leaves a run of rows with
    no header, which no reader would ever reach (table_rows looks for headers), so its rows would be dropped in silence:
    that run is refused here, wherever in the draft it sits."""
    i, fenced = 0, False
    while i < len(lines):
        if lines[i].lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if fenced or not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        start = i
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            i += 1
        run = lines[start:i]
        indent = len(run[0]) - len(run[0].lstrip())
        for k, line in enumerate(run):
            if len(line) - len(line.lstrip()) != indent:
                raise ValueError(f"draft line {start + k + 1}: a table row indented differently from its table; it "
                                 f"would end the table and drop the rows after it")
        if len(run) < 2 or not TABLE_RULE.fullmatch(run[1].strip()):
            raise ValueError(f"draft line {start + 1}: table rows with no header and |---| rule above them (a prose "
                             f"line or blank lines split a table, so these rows would be dropped): {run[0][:60]!r}")


def table_rows(lines: List[str], header: str, required: bool = True,
               offset: int = 0) -> Iterable[Tuple[int, List[str]]]:
    """Each data row of every table whose header line is exactly `header`. Refuses a table it cannot read whole: a
    missing header (when required), a row with the wrong number of cells, a missing |---| rule, an indented row, or a
    blank line followed by more rows (each used to end the table early and drop the rows after it)."""
    i, found = 0, False
    width = len(cells(header))
    while i < len(lines):
        if lines[i].strip() != header:
            i += 1
            continue
        found = True
        if i + 1 >= len(lines) or not TABLE_RULE.fullmatch(lines[i + 1].strip()):
            raise ValueError(f"draft line {offset + i + 2}: the table headed {header!r} has no |---| rule under it")
        i += 2
        while i < len(lines) and lines[i].startswith("|"):
            row = cells(lines[i])
            if len(row) != width:
                raise ValueError(f"draft line {offset + i + 1}: {len(row)} cells, the table has {width}")
            yield offset + i + 1, row
            i += 1
        end = lines[i] if i < len(lines) else ""
        after = lines[i + 1] if i + 1 < len(lines) else ""
        if end.lstrip().startswith("|") or (not end.strip() and after.lstrip().startswith("|")):
            raise ValueError(f"draft line {offset + i + 1}: the table headed {header!r} continues after an indented "
                             f"row or a blank line; rows past that point would be dropped")
    if required and not found:
        raise ValueError(f"the draft has no table headed {header!r}")


def parse_legend(lines: List[str]) -> List[dict]:
    text = "\n".join(lines)
    study_only = set(re.findall(r"\*\*([\w ]+?) is study-only\.\*\*", text))
    rows = []
    for _, (short, sid, _author, licence, _passes) in table_rows(lines, LEGEND_HEADER):
        rows.append({"id": clean(sid), "short": clean(short),
                     "study_only": clean(short) in study_only or "all rights reserved" in licence.lower()})
    return rows


def parse_families(lines: List[str]) -> List[dict]:
    summary = {}
    for line in lines:
        m = MAP_LINE.match(line)
        if m:
            summary[m.group(1)] = [s.strip() for s in m.group(3).split("·")]
    fams = []
    for line in lines:
        m = FAMILY_HEAD.match(line)
        if m:
            fams.append({"letter": m.group(1), "name": m.group(2).strip(), "summary": summary.get(m.group(1), [])})
    letters = [f["letter"] for f in fams]
    if not fams or len(set(letters)) != len(letters) or set(letters) != set(summary):
        raise ValueError(f"the family headings ({''.join(letters)}) and the family map ({''.join(sorted(summary))}) "
                         f"disagree: a '## N. Family X: Name' heading or a map line has lost its form")
    return fams


def parse_manifest(lines: List[str]) -> List[dict]:
    out, batches = [], []
    for i, line in enumerate(lines):
        m = re.match(r"^### Batch ([AB])\b", line)
        if m:
            batch = m.group(1)
            batches.append(batch)
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith(("### ", "## "))), len(lines))
            for _, (file_cell, fn_cell) in table_rows(lines[i:end], MANIFEST_HEADER, offset=i):
                files = [f for f in TICKS.findall(file_cell) if f.endswith(".glsl")]
                if not files:
                    raise ValueError(f"build manifest batch {batch}: a row names no .glsl file: {file_cell!r}")
                fns = [rename(f) for f in TICKS.findall(strip_parens(fn_cell)) if IDENT.match(f)]
                recipe = "recipe" in file_cell or not fns
                for f in files:
                    row = {"batch": batch, "file": f, "kind": "recipe" if recipe else "helper",
                           "functions": fns if len(files) == 1 else []}
                    if any(n in RENAMES for n in TICKS.findall(fn_cell)):
                        row["note"] = RENAME_RULING
                        row["rulings"] = ["ruling-3-rename"]
                    out.append(row)
    if sorted(batches) != ["A", "B"]:
        raise ValueError(f"the build manifest (section 18) should have one '### Batch A' and one '### Batch B' "
                         f"heading; found {batches}")
    return out


def parse_ledger(lines: List[str]) -> List[dict]:
    rows, used = [], set()
    for n, (proposed, collides, owner, why) in table_rows(lines, LEDGER_HEADER):
        spans = TICKS.findall(owner)
        names = [rename(s) for s in spans if re.match(r"^[A-Za-z_]\w*\*?$", s)]
        modules = [s for s in spans if s.endswith(".glsl")]
        row = {"proposed": clean(proposed), "collides_with": clean(collides), "owner": clean(owner),
               "names": list(dict.fromkeys(names)), "module": modules[0] if modules else None, "why": clean(why)}
        if any(s in RENAMES for s in spans):
            fix = LEDGER_OWNER_RULINGS.get(row["owner"])
            if fix is None:
                raise ValueError(f"draft line {n}: the ledger row for {row['proposed']!r} names a renamed function "
                                 f"in its owner text; add its corrected text to LEDGER_OWNER_RULINGS")
            used.add(row["owner"])
            row["owner_draft"], row["why_draft"] = row["owner"], row["why"]
            row["owner"], row["why"] = fix
            row["ruling"] = RENAME_RULING
            row["rulings"] = ["ruling-3-rename", "ruling-3-ledger-fbm"]
        rows.append(row)
    stale = sorted(set(LEDGER_OWNER_RULINGS) - used)
    if stale:
        raise ValueError(f"LEDGER_OWNER_RULINGS entries match no ledger row (the draft changed): {stale}")
    return rows


def module_for(fn: str, cat_id: str, heading_files: List[str], manifest: Dict[str, str]) -> Tuple[str, str]:
    if fn in manifest:
        return manifest[fn], "manifest"
    for pattern, f in MODULE_RULES.get(cat_id, []):
        if re.search(pattern, fn):
            return f, "rule"
    return heading_files[0], ("heading" if len(heading_files) == 1 else "first-of-heading")


def parse_parts(lines: List[str], legend: Legend, manifest: Dict[str, str]) -> Tuple[List[dict], List[dict]]:
    """Categories and their parts from the family sections. Strict: inside a family section every '### ' line must be a
    category heading of that family naming its module file, each category has exactly one primitive table, and every
    '|' line belongs to that table, so no row can be filed under the wrong category or dropped."""
    categories: List[dict] = []
    parts: List[dict] = []
    family: Optional[str] = None
    cat: Optional[dict] = None
    table = "none"            # the current category's table: "none" yet, "rule" (header seen), "open", "closed"
    count: Dict[str, int] = {}

    def close_category(where: str) -> None:
        if cat is not None and table == "none":
            raise ValueError(f"{where}: category {cat['id']} has no primitive table (its header must read exactly "
                             f"{PRIMITIVE_HEADER!r})")

    for i, line in enumerate(lines):
        where = f"draft line {i + 1}"
        if table in ("open", "rule") and not line.startswith("|"):
            if table == "rule":
                raise ValueError(f"{where}: the primitive table of {cat['id']} has no |---| rule under its header")
            table = "closed"
        m = FAMILY_HEAD.match(line)
        if m or line.startswith("## "):
            close_category(where)
            family, cat, table = (m.group(1) if m else None), None, "none"
            continue
        stripped = line.strip()
        if family is None:
            if CATEGORY_HEAD.match(line) or stripped == PRIMITIVE_HEADER:
                raise ValueError(f"{where}: a category heading or primitive table outside any family section (a "
                                 f"'## N. Family X: Name' heading above it has lost its form): {line[:80]!r}")
            continue
        if line.startswith("### "):
            m = CATEGORY_HEAD.match(line)
            if not m:
                raise ValueError(f"{where}: a '### ' heading inside family {family} that is not a category heading "
                                 f"('### B3. Name (`file.glsl`)'): {line[:80]!r}")
            close_category(where)
            cid = m.group(1)
            if cid[0] != family:
                raise ValueError(f"{where}: category {cid} sits under family {family}")
            if any(c["id"] == cid for c in categories):
                raise ValueError(f"{where}: category {cid} is headed twice")
            title = m.group(2)
            cut = title.find(" (`")
            name = title[:cut] if cut >= 0 else title
            heading = [f for f in TICKS.findall(title[cut:]) if f.endswith(".glsl")] if cut >= 0 else []
            if not heading:
                raise ValueError(f"{where}: category {cid}'s heading names no module file: {line[:80]!r}")
            cat = {"id": cid, "name": name.strip(), "family": cid[0], "heading_modules": heading,
                   "modules": list(heading)}
            categories.append(cat)
            table = "none"
            continue
        if stripped == PRIMITIVE_HEADER:
            if line != stripped:
                raise ValueError(f"{where}: an indented primitive table header")
            if cat is None:
                if family not in SYNTHETIC_CATEGORIES:
                    raise ValueError(f"{where}: family {family} has a primitive table with no category heading above "
                                     f"it (add one, or a SYNTHETIC_CATEGORIES entry)")
                cid, cname, cfiles = SYNTHETIC_CATEGORIES[family]
                cat = {"id": cid, "name": cname, "family": family, "heading_modules": [], "modules": list(cfiles)}
                categories.append(cat)
            elif table != "none":
                raise ValueError(f"{where}: a second primitive table under category {cat['id']} (the category "
                                 f"heading above it has probably lost its form)")
            table = "rule"
            continue
        if stripped.startswith("|"):
            if not line.startswith("|"):
                raise ValueError(f"{where}: an indented table row; it would end the table and drop the rows after it")
            if table != "rule" and table != "open":
                raise ValueError(f"{where}: a table row outside {cat['id'] if cat else family}'s primitive table (a "
                                 f"blank line or a malformed row closed the table above it): {line[:60]!r}")
            if table == "rule":
                if not TABLE_RULE.fullmatch(stripped):
                    raise ValueError(f"{where}: the primitive table of {cat['id']} has no |---| rule under its header")
                table = "open"
                continue
            row = cells(line)
            if len(row) != 6:
                raise ValueError(f"{where}: {len(row)} cells, a primitive row has 6")
            sig, contract, cost, loved, learn, status = row
            count[cat["id"]] = count.get(cat["id"], 0) + 1
            # The draft's own row counts (section 2) count rows that open with a signature; four rows open with prose
            # instead (a host-level loop and three named sets of functions). Both kinds are parts; `form` says which.
            form = "signature" if sig.lstrip().startswith("`") else "prose"
            idiom = "not a function" in sig
            kind = "idiom" if idiom else ("set" if form == "prose" else "function")
            drafted = [] if idiom else names_in_signature(sig)
            fns = [rename(n) for n in drafted]
            placed = [module_for(f, cat["id"], cat["heading_modules"] or cat["modules"], manifest) for f in fns]
            if len({p[0] for p in placed}) > 1:
                raise ValueError(f"{where}: one row spans several module files: {placed}")
            module, basis = placed[0] if placed else (cat["modules"][0], "heading")
            if module not in cat["modules"]:
                cat["modules"].append(module)
            pointers, sources = learn_of(learn)
            st = re.search(r"P([0-2])", status)
            if not st:
                raise ValueError(f"{where}: no status in {status!r}")
            part = {
                "id": f"{cat['id']}.{count[cat['id']]:02d}", "category": cat["id"], "family": cat["family"],
                "signature": rename_text(clean(sig.replace("**hook**", "").replace("**(legacy twin)**", ""))),
                "functions": fns, "contract": clean(contract), "cost": cost_of(cost), "cost_text": clean(cost),
                "tex": tex_of(cost), "hook": "hook" in sig or "hook" in cost, "status": f"P{st.group(1)}",
                "legacy": "(legacy twin)" in sig, "kind": kind, "form": form,
                "exemplars": legend.ids_in(loved), "loved_text": clean(loved), "learn": pointers,
                "sources": sources, "module": module, "module_basis": basis, "line": i + 1,
                "types": types_in_signature(sig),   # every type the row uses; trimmed to the ones it does not provide
            }
            renamed = {RENAMES[n]: n for n in drafted if n in RENAMES}
            if renamed:
                part["renamed_from"] = renamed
                part["rulings"] = ["ruling-3-rename"]
            parts.append(part)
            continue
    close_category(f"draft line {len(lines)}")
    for c in categories:
        c["module"] = c["modules"][0]
    return categories, parts


# ---------- groups: tiers, and each part marked required, optional or one of several alternatives ----------

OPTIONAL_BEFORE = re.compile(r"\boptional\s*\(?\s*$")
OPTIONAL_AFTER = re.compile(r"^\s*(?:\([^()]*\)\s*)?(?:as an? optional|when built)\b")
HOOK_BEFORE = re.compile(r"\bthe hooks?\s*$")
CONNECT_OR = re.compile(r"^\s*\(?\s*[,;]?\s*(?:or|and/or)\s*$")
CONNECT_UNTIL = re.compile(r"\buntil then\s*$")
CONNECT_LIST = re.compile(r"^\s*[,;]\s*$")
CONNECT_BIND = re.compile(r"^\s*(?:with|shaped by|from)\s*$")
BRIEF_END = re.compile(r"\.\s+(?:Knobs|Exemplars|Landing|Learn it)\b")
BRIEF_TIER = re.compile(r"(?:^|(?<=\.\s))([A-Z][a-z]+) tier:\s*")
ANY_TIER = re.compile(r"\b[A-Za-z]+ tier\b")
# The labels a group card's bullets carry (16.2-16.7); a recipe label may name a tier ("Recipe, band tier (...)").
CARD_LABELS = frozenset({"what", "recipe", "hooks", "knobs", "presets", "exemplars", "house landing", "debug views"})
CARD_BULLET = re.compile(r"^- \*\*(.+?):\*\* ?(.*)$")
BRIEF_BULLET = re.compile(r"^- \*\*(.+?) \((P\d)\)\.\*\* (.*)$")
HOOK_SIGNATURE = re.compile(r"^.*?\b([A-Za-z_]\w*)\s*\(.*\)\s*$")


def drop_commentary(text: str) -> str:
    """Parentheticals that hold no code span are commentary; drop them so they cannot hide a connector word."""
    prev = None
    while prev != text:
        prev, text = text, re.sub(r"\([^()`]*\)", " ", text)
    return text


def connector(text: str) -> str:
    """How two neighbouring parts in one recipe step relate: 'or' (alternatives), 'list' (a comma list: alternatives
    only under 'or' or 'chosen by'), 'bind' (used together: "X with Y", "X shaped by Y"), or 'sep' (both required)."""
    if "`" in text:
        return "sep"
    t = drop_commentary(text)
    if CONNECT_OR.match(t) or CONNECT_UNTIL.search(t):
        return "or"
    if CONNECT_LIST.match(t):
        return "list"
    if CONNECT_BIND.match(t):
        return "bind"
    return "sep"


def read_recipe(text: str, planned: set) -> dict:
    """One recipe (a chain of steps joined by arrows) as {parts (in recipe order), required, alternatives, optional,
    hooks, other}. `alternatives` is a list of choices; each choice is a list of options, each option the names used together
    ("fbm3 shaped by shpRemap, or densFromSDF" is [[fbmGrad3, shpRemap], [densFromSDF]]); building one option of each
    choice is enough. A name the step calls optional ("optional `X`", "`X` as an optional rim", "`X` when built") is
    optional; "`X` (P1; until then `Y`)" makes Y the stand-in alternative for X."""
    required: List[str] = []
    alternatives: List[List[List[str]]] = []
    optional: List[str] = []
    hooks: List[str] = []
    others: List[str] = []
    order: List[str] = []
    for step in text.split("→"):
        spans = [(m.start(), m.end(), m.group(1)) for m in TICKS.finditer(step)]
        items: List[Tuple[int, int, str]] = []
        opt: List[int] = []
        for k, (s, e, raw) in enumerate(spans):
            name = rename(raw.split("(")[0].strip())
            prev_end = spans[k - 1][1] if k else 0
            next_start = spans[k + 1][0] if k + 1 < len(spans) else len(step)
            if HOOK_BEFORE.search(step[prev_end:s]):
                hooks.append(name)
            elif IDENT.match(name) and name in planned:
                if OPTIONAL_BEFORE.search(step[prev_end:s]) or OPTIONAL_AFTER.match(step[e:next_start]):
                    opt.append(len(items))
                items.append((s, e, name))
                order.append(name)
            elif IDENT.match(name):
                others.append(name)
        optional += [items[k][2] for k in opt]
        seq = [k for k in range(len(items)) if k not in opt]
        units: List[List[int]] = []
        links: List[str] = []
        for j, k in enumerate(seq):
            kind = connector(step[items[seq[j - 1]][1]:items[k][0]]) if j else None
            if kind == "bind":
                units[-1].append(k)
            else:
                units.append([k])
                if j:
                    links.append(kind)
        runs: List[List[int]] = [[0]] if units else []
        run_links: List[List[str]] = [[]] if units else []
        for u in range(1, len(units)):
            if links[u - 1] in ("or", "list"):
                runs[-1].append(u)
                run_links[-1].append(links[u - 1])
            else:
                runs.append([u])
                run_links.append([])
        for run, rl in zip(runs, run_links):
            first = units[run[0]][0]
            lead_from = items[units[run[0] - 1][-1]][1] if run[0] else 0
            choice = "chosen by" in step[lead_from:items[first][0]]
            if len(run) > 1 and ("or" in rl or choice):
                alternatives.append([[items[k][2] for k in units[u]] for u in run])
            else:
                required += [items[k][2] for u in run for k in units[u]]
    required = list(dict.fromkeys(required))
    kept: List[List[List[str]]] = []
    for a in alternatives:
        if any(len(o) == 1 and o[0] in required for o in a):
            optional += [n for o in a for n in o if n not in required]   # the choice is met by a required part
        elif a not in kept:
            kept.append(a)
    alternatives = kept
    seen_alt = {n for a in alternatives for o in a for n in o}
    optional = [n for n in dict.fromkeys(optional) if n not in required and n not in seen_alt]
    marked = set(required) | seen_alt | set(optional)
    parts = [n for n in dict.fromkeys(order) if n in marked]
    return {"parts": parts, "required": required, "alternatives": alternatives, "optional": optional,
            "hooks": list(dict.fromkeys(hooks)), "other": list(dict.fromkeys(others))}


def _tier_piece(cell: str, tier: str) -> Optional[str]:
    """The piece of a 'tiers and cost' cell that names `tier` ("sheets (C2 over layers)" for the sheet tier)."""
    for piece in re.split(r",\s*(?![^()]*\))", clean(cell)):
        words = re.findall(r"[a-z]+", piece.lower())
        if any(w.startswith(tier) or tier.startswith(w) for w in words if len(w) > 2):
            return piece
    return None


def _tier_status(status_text: str, tier: str) -> Optional[str]:
    """A tier's status from the group's status cell ("P0 (band, sheets); P1 (volume)")."""
    for st, names in re.findall(r"P([0-2]) \(([^)]*)\)", clean(status_text)):
        for n in re.split(r",\s*", names.lower()):
            if n and (n.startswith(tier) or tier.startswith(n)):
                return f"P{st}"
    return None


def parse_groups(lines: List[str], legend: Legend, planned: set, manifest_rows: List[dict]) -> List[dict]:
    groups = []
    for _, (name, line, tiers, exemplars, landing, status) in table_rows(lines, GROUPS_HEADER):
        st = re.search(r"P([0-2])", status)
        if not st:
            raise ValueError(f"group {clean(name)!r} has no status in {status!r}")
        groups.append({"name": clean(name), "line": clean(line), "tiers_text": clean(tiers), "cost": cost_of(tiers),
                       "status": f"P{st.group(1)}", "status_text": clean(status),
                       "exemplars": legend.ids_in(exemplars),
                       "study_only": [s for s in legend.ids_in(exemplars)
                                      if any(r["id"] == s and r["study_only"] for r in legend.rows)],
                       "landing": clean(landing), "tiers": [], "parts": [], "debug": [], "hooks": [],
                       "hook_signatures": {}, "uses_groups": [], "other_names": []})
    by_name = {g["name"]: g for g in groups}
    recipes: Dict[str, List[Tuple[Optional[str], Optional[str], str]]] = {g["name"]: [] for g in groups}

    def note_others(g: dict, names: List[str]) -> None:
        for n in names:
            if n in by_name and n != g["name"]:
                if n not in g["uses_groups"]:
                    g["uses_groups"].append(n)      # a recipe that ends in another group (most end in `finish`)
            elif n not in g["other_names"] and n not in g["hooks"]:
                g["other_names"].append(n)          # knob names the recipe mentions

    def absorb_brief(g: dict, text: str) -> None:
        """A 16.8 brief holds its recipe inline, sometimes in named tiers ("Analytic tier: ... Marched tier: ..."),
        followed by knobs, exemplars and landing prose that name no part."""
        end = BRIEF_END.search(text)
        text = text[:end.start() + 1] if end else text
        heads = list(BRIEF_TIER.finditer(text))
        if len(ANY_TIER.findall(text)) != len(heads):
            raise ValueError(f"group {g['name']}: its brief names a tier I cannot read (each tier opens a sentence, "
                             f"'Marched tier: ...'), so one tier's parts would join another's: {text[:80]!r}")
        if not heads:
            recipes[g["name"]].append((None, None, text))
        for k, h in enumerate(heads):
            stop = heads[k + 1].start() if k + 1 < len(heads) else len(text)
            recipes[g["name"]].append((h.group(1).lower(), None, text[h.end():stop]))

    def absorb(g: dict, key: str, key_raw: str, text: str) -> None:
        if key == "brief":
            absorb_brief(g, text)
        elif key == "hooks":
            spans = TICKS.findall(text)
            if not spans:
                raise ValueError(f"group {g['name']}: its Hooks bullet names no hook as code "
                                 f"(`float mapScene(vec3 p)`), so the hook signatures would be lost: {text[:80]!r}")
            for span in spans:
                m = HOOK_SIGNATURE.match(span.strip())
                if not m:
                    raise ValueError(f"group {g['name']}: a hook in its Hooks bullet is not a signature: {span!r}")
                n = m.group(1)
                if n not in g["hooks"]:
                    g["hooks"].append(n)
                g["hook_signatures"][n] = clean(span)
        elif key.startswith("debug"):
            for span in TICKS.findall(text):
                n = rename(span.split("(")[0].strip())
                if IDENT.match(n) and n in planned:
                    if n not in g["debug"]:
                        g["debug"].append(n)
                elif IDENT.match(n):
                    note_others(g, [n])
        elif key.startswith("recipe"):
            m = re.match(r"^Recipe(?:, (\w+) tier(?: \((.*)\))?)?$", key_raw)
            if not m:
                raise ValueError(f"group {g['name']}: a recipe bullet I cannot read: {key_raw!r}")
            recipes[g["name"]].append((m.group(1).lower() if m.group(1) else None, m.group(2), text))

    # Cards 16.2-16.7: "### 16.4 neon-line (P0)" then "- **Label:** text" bullets with indented continuations.
    current = None
    bullet_key, bullet_raw, bullet_text = None, None, []

    def flush():
        if current is not None and bullet_key:
            absorb(current, bullet_key, bullet_raw, " ".join(bullet_text))

    # Inside a card or the briefs every line is a bullet of the expected form, an indented continuation of one, blank,
    # or a --- rule. Anything else (a bullet whose colon slipped outside the bold, a continuation that lost its indent)
    # is refused: read leniently, it vanished and its continuation lines joined the bullet above, moving a P1 tier's
    # parts into a P0 tier.
    in_briefs = False
    for n, line in enumerate(lines, 1):
        m = re.match(r"^### 16\.\d+ (.+)$", line)
        if m or line.startswith("## "):
            flush()
            bullet_key, bullet_raw, bullet_text = None, None, []
            title = m.group(1) if m else ""
            first = title.split(" (")[0].strip()
            current = by_name.get(first)
            in_briefs = title.startswith("The P1 and P2 groups")
            continue
        if not in_briefs and current is None:
            continue
        if in_briefs:
            b = BRIEF_BULLET.match(line)
            if b:
                flush()
                names = [x.strip() for x in b.group(1).split(",")]
                current = by_name.get(names[0]) if len(names) == 1 else None
                bullet_key, bullet_raw, bullet_text = "brief", None, [b.group(3)]
                continue
        else:
            b = CARD_BULLET.match(line)
            if b:
                label = b.group(1).lower()
                if label not in CARD_LABELS and not label.startswith("recipe"):
                    raise ValueError(f"draft line {n}: the {current['name']} card has a bullet label I do not know "
                                     f"({b.group(1)!r}; known: {', '.join(sorted(CARD_LABELS))})")
                flush()
                bullet_key, bullet_raw, bullet_text = label, b.group(1), [b.group(2)]
                continue
        if line.startswith("  ") and bullet_key:
            bullet_text.append(line.strip())
        elif line.strip() and line.strip() != "---":
            where = "the 16.8 briefs" if in_briefs else f"the {current['name']} card"
            form = "'- **name (P1).** text'" if in_briefs else "'- **Label:** text'"
            raise ValueError(f"draft line {n}: a line in {where} that is not a bullet ({form}), an indented "
                             f"continuation or blank, so its text would be lost or joined to the bullet above: "
                             f"{line[:60]!r}")
    flush()

    for g in groups:
        if not recipes[g["name"]] and g["status"] != "P2":
            raise ValueError(f"group {g['name']} ({g['status']}) has no recipe I can read (a '- **Recipe:**' bullet in "
                             f"its card, or its brief in 16.8): its parts could not be checked")
        for tier, paren, text in recipes[g["name"]]:
            r = read_recipe(text, planned)
            for n in r["hooks"]:
                if n not in g["hooks"]:
                    g["hooks"].append(n)
            note_others(g, r["other"])
            cost = cost_of(paren or "")
            if tier and cost is None:
                piece = _tier_piece(g["tiers_text"], tier)
                if piece is None:
                    raise ValueError(f"group {g['name']}: the {tier} tier names no cost, and the 16.1 table's "
                                     f"'tiers and cost' cell ({g['tiers_text']!r}) has no piece for it")
                cost = cost_of(piece)
            st = re.search(r"\bP([0-2])\b", paren or "")
            status = (f"P{st.group(1)}" if st else (_tier_status(g["status_text"], tier) if tier else None)) \
                or g["status"]
            g["tiers"].append({"name": tier, "cost": cost or g["cost"], "status": status,
                               "note": clean(paren) if paren else None,
                               "parts": r["parts"], "required": r["required"],
                               "alternatives": r["alternatives"], "optional": r["optional"]})
            for n in r["parts"]:
                if n not in g["parts"]:
                    g["parts"].append(n)
        g["other_names"] = [n for n in g["other_names"] if n not in g["hooks"]]
        ships = [t["cost"] for t in g["tiers"] if t["status"] == g["status"] and t["cost"]]
        if ships:
            g["cost"] = max(ships)       # the costliest tier that ships at the group's own status (ruling 5's gate)

    recipe_files = [r["file"] for r in manifest_rows if r["kind"] == "recipe"]
    for g in groups:
        mine = [f for f in recipe_files if Path(f).stem.startswith(g["name"])]
        if g["name"] == "finish":
            mine = [f for f in recipe_files if f.endswith("display-out.glsl")]
        g["modules"] = mine or [f"groups/{g['name']}.glsl"]
        g["modules_basis"] = "manifest" if mine else "convention"
    return groups


# ---------- the judge's rulings: promotions (b), struct parts (a), the manifest, and the closure check ----------

def apply_promotions(parts: List[dict], groups: List[dict], rulings: List[dict]) -> None:
    owner = {fn: p for p in parts for fn in p["functions"]}
    for name, why in PROMOTIONS.items():
        p = owner.get(name)
        if p is None:
            raise ValueError(f"PROMOTIONS names {name!r}, which the draft does not plan")
        if p["status"] == "P0":
            raise ValueError(f"PROMOTIONS names {name!r}, which the draft already makes P0: the ruling is stale")
        need = [{"group": g["name"], "tier": t["name"]} for g in groups for t in g["tiers"] if t["status"] == "P0"
                and (name in t["required"] or any(name in o for a in t["alternatives"] for o in a))]
        if not need:
            raise ValueError(f"PROMOTIONS names {name!r}, which no P0 group tier needs: the ruling is stale")
        rid = f"b-promote-{name}"
        p["status_draft"], p["status"] = p["status"], "P0"
        p.setdefault("rulings", []).append(rid)
        rulings.append({"id": rid, "kind": "promote", "names": list(p["functions"]), "part": p["id"],
                        "from": p["status_draft"], "to": "P0", "required_by": need,
                        "source": f"{JUDGE}, ruling (b)",
                        "reason": f"every part a P0 group requires is P0: {why}"})


def _and(names: List[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def plan_types(parts: List[dict], categories: List[dict], rulings: List[dict]) -> List[dict]:
    """Judge's ruling (a): every non-GLSL type a planned signature uses becomes a planned name, as a struct part in the
    module of its first user (draft order), at the earliest status of any part that uses it. A type the draft plans
    too late (LitSurface: P1, while P0 rigStudio takes it) moves out of its row into its own struct part; when the row
    declares nothing else, the split would leave an empty part, so the draft is refused for a judge to rule. A type
    that only a struct's field uses (no function takes it) is planned the same way, the struct counting as its user."""
    used = {p["id"]: list(p["types"]) for p in parts}
    order: List[str] = list(dict.fromkeys(t for p in parts for t in used[p["id"]]))
    cats = {c["id"]: c for c in categories}
    for t in order:
        users = sorted((p for p in parts if t in used[p["id"]]), key=lambda p: p["line"])
        earliest = min((p["status"] for p in users), key=RANK.get)
        owner = next((p for p in parts if t in p["functions"]), None)
        if owner is not None and RANK[owner["status"]] <= RANK[earliest]:
            continue
        first = users[0]
        cat = cats[first["category"]]
        n = sum(1 for p in parts if p["category"] == cat["id"]) + 1
        new_id = f"{cat['id']}.{n:02d}"
        user_ids = [p["id"] for p in users]
        # the functions that take it (a struct declared in the same row is a type, not a taker), else the structs whose
        # fields hold it (a struct-only row whose field type is planned nowhere has no other user)
        takers = list(dict.fromkeys(fn for p in users for fn in p["functions"] if fn != t and fn not in order)) \
            or list(dict.fromkeys(fn for p in users for fn in p["functions"] if fn != t)) or user_ids
        user_fns = _and(takers)
        use, their = ("uses", "its signature") if len(takers) == 1 else ("use", "their signatures")
        if owner is not None and owner["functions"] == [t]:
            early = next(p for p in users if p["status"] == earliest)
            raise ValueError(f"{owner['id']} declares only {t}, at {owner['status']}, but {early['id']} ({earliest}) "
                             f"takes it: splitting {t} out would leave {owner['id']} an empty part. A judge must rule "
                             f"(plan the row at {earliest}, or move {t}) before the draft builds")
        if owner is None:
            rid, kind = f"a-struct-{t}", "plan-struct"
            reason = (f"{user_fns} {use} {t}, which the draft plans nowhere; a part cannot be built "
                      f"before the type its signature uses, so {t} is planned in the module of its first user "
                      f"({first['id']}, {first['module']}) at the earliest status among its users ({earliest})")
            contract = (f"the {t} that {user_fns} {use}; planned by ruling (a) because the draft names it in "
                        f"{their} but plans it nowhere. Its fields are settled when its first user is built")
        else:
            rid, kind = f"a-split-{t}", "split-struct"
            owner["functions"] = [fn for fn in owner["functions"] if fn != t]
            owner.setdefault("rulings", []).append(rid)
            reason = (f"the draft declares {t} in {owner['id']} at {owner['status']}, but {first['id']} "
                      f"({', '.join(fn for fn in first['functions'])}) is {earliest} and takes it; {t} moves out of "
                      f"{owner['id']} into its own {earliest} struct part in the module of its first user "
                      f"({first['module']}), and {owner['id']} keeps the rest")
            contract = (f"the {t} that {user_fns} {use}; declared in the draft's {owner['id']} at "
                        f"{owner['status']}, planned on its own at {earliest} by ruling (a) because {first['id']} "
                        f"needs it first")
        part = {"id": new_id, "category": cat["id"], "family": cat["family"], "signature": f"struct {t}",
                "functions": [t], "contract": contract, "cost": None, "cost_text": "a type: no cost of its own",
                "tex": None, "hook": False, "status": earliest, "legacy": False, "kind": "struct", "form": "ruling",
                "exemplars": [], "loved_text": "", "learn": [], "sources": [], "module": first["module"],
                "module_basis": "ruling", "line": None, "types": [], "users": user_ids, "ruling": rid}
        at = max(k for k, p in enumerate(parts) if p["category"] == cat["id"]) + 1
        parts.insert(at, part)
        used[new_id] = []
        entry = {"id": rid, "kind": kind, "names": [t], "part": new_id, "module": first["module"],
                 "status": earliest, "users": user_ids, "source": f"{JUDGE}, ruling (a)", "reason": reason}
        if owner is not None:
            entry["from_part"], entry["from_status"] = owner["id"], owner["status"]
        rulings.append(entry)
    for p in parts:
        p["types"] = [t for t in used[p["id"]] if t not in p["functions"]]
    return parts


def apply_manifest_rulings(rows: List[dict], parts: List[dict]) -> None:
    """Every P0 name must be in a manifest file. Names the rulings made P0 join the row of their module (a struct first,
    so it is declared before its users); a module the manifest lacks gets a new batch-B row (batch B is 'the six P0
    groups and their parts', which is why rulings add parts). The manifest must then equal the P0 set exactly."""
    listed = {fn for r in rows for fn in r["functions"]}
    by_file = {r["file"]: r for r in rows}
    for p in parts:
        missing = [fn for fn in p["functions"] if fn not in listed] if p["status"] == "P0" else []
        if not missing:
            continue
        rid = p.get("ruling") or next((r for r in reversed(p.get("rulings", [])) if not r.startswith("ruling-3")),
                                      None)
        if rid is None:
            raise ValueError(f"P0 part {p['id']} ({', '.join(missing)}) is in no build-manifest file (section 18)")
        row = by_file.get(p["module"])
        if row is None:
            row = {"batch": "B", "file": p["module"], "kind": "helper", "functions": [], "added_by_ruling": True}
            at = next(k for k, r in enumerate(rows) if r["batch"] == "B" and r["kind"] == "recipe")
            rows.insert(at, row)
            by_file[p["module"]] = row
        if p["kind"] == "struct":
            row["functions"] = missing + row["functions"]
        else:
            row["functions"] = row["functions"] + missing
        row.setdefault("rulings", [])
        if rid not in row["rulings"]:
            row["rulings"].append(rid)
        listed |= set(missing)
    p0 = {fn for p in parts if p["status"] == "P0" for fn in p["functions"]}
    if listed != p0:
        raise ValueError(f"the build manifest and the P0 set disagree: manifest-only {sorted(listed - p0)}, "
                         f"P0-only {sorted(p0 - listed)}")


def check_closure(parts: List[dict], groups: List[dict]) -> None:
    """The P0 set must be buildable from P0 parts alone; refuse the draft (with every gap named) when it is not."""
    owner = {fn: p for p in parts for fn in p["functions"]}
    st = {fn: p["status"] for fn, p in owner.items()}
    by_name = {g["name"]: g for g in groups}
    gaps = []
    for p in parts:
        for t in p["types"]:
            o = owner.get(t)
            if o is None or RANK[o["status"]] > RANK[p["status"]]:
                gaps.append(f"{p['id']} ({p['status']}) uses type {t}, "
                            + ("planned nowhere" if o is None else f"planned at {o['status']} by {o['id']}"))
    for g in groups:
        for t in g["tiers"]:
            if t["status"] != "P0":
                continue
            label = g["name"] + (f" {t['name']} tier" if t["name"] else "")
            gaps += [f"{label} (P0) requires {n}, which is {st[n]}" for n in t["required"] if st[n] != "P0"]
            for choice in t["alternatives"]:
                if not any(all(st[n] == "P0" for n in opt) for opt in choice):
                    gaps.append(f"{label} (P0) needs one of {choice}, and none is P0")
        if g["status"] == "P0":
            gaps += [f"{g['name']} (P0) ends in group {u}, which is {by_name[u]['status']}"
                     for u in g["uses_groups"] if by_name[u]["status"] != "P0"]
    if gaps:
        raise ValueError("the P0 set cannot be built from P0 parts alone; a judge must rule on each gap (PROMOTIONS) "
                         "or the draft must change:\n  " + "\n  ".join(gaps))


def dissector_tags(path: Path = DISSECT) -> List[str]:
    """The tag names in dissect.py's TAGS table, read as text so a half-edited dissector cannot break the build."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^TAGS: Dict\[str, str\] = \{(.*?)^\}", text, re.S | re.M)
    return re.findall(r'^\s+"([a-z0-9_]+\.[a-z0-9_]+)":', m.group(1), re.M) if m else []


def build(draft: Path = DRAFT) -> dict:
    """The atlas as data, from the draft. Deterministic: the same draft gives the same dict, byte for byte once dumped.
    Raises ValueError on a draft it cannot read cleanly, or whose P0 set is not closed."""
    raw = draft.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = raw.split("\n")
    check_table_shapes(lines)
    legend = Legend(parse_legend(lines))
    manifest_rows = parse_manifest(lines)
    manifest = {fn: r["file"] for r in manifest_rows for fn in r["functions"]}
    families = parse_families(lines)
    categories, parts = parse_parts(lines, legend, manifest)
    planned = {fn for p in parts for fn in p["functions"]}
    groups = parse_groups(lines, legend, planned, manifest_rows)
    collisions = parse_ledger(lines)

    rulings: List[dict] = [
        {"id": "ruling-3-rename", "kind": "rename", "names": [RENAMES[k] for k in RENAMES], "renames": dict(RENAMES),
         "source": RENAME_SOURCE, "reason": RENAME_RULING},
        {"id": "ruling-3-ledger-fbm", "kind": "ledger-owner", "names": ["fbmGrad3"], "source": RENAME_SOURCE,
         "reason": ("the draft's ledger row for the canonical fBm says fbm3 goes in noise/fbm.glsl after slice S2 "
                    "renames the legacy chunk; ruling 3 overruled that rename, so the row's owner and why are "
                    "rewritten to match its names (the draft's words stay in owner_draft and why_draft)")},
    ]
    apply_promotions(parts, groups, rulings)
    plan_types(parts, categories, rulings)
    check_closure(parts, groups)
    apply_manifest_rulings(manifest_rows, parts)

    cat_ids = {c["id"] for c in categories}
    for table in (TAG_CATEGORIES, TAG_GROUP_CATEGORIES):
        for tag, ids in table.items():
            unknown = [c for c in ids if c not in cat_ids]
            if unknown:
                raise ValueError(f"tag {tag} maps to unknown categories {unknown}")
    if DISSECT.exists():
        orphans = [t for t in dissector_tags() if t not in TAG_CATEGORIES
                   and t.split(".")[0] not in TAG_GROUP_CATEGORIES]
        if orphans:
            raise ValueError(f"dissector tags with no atlas category: {orphans} (add them to TAG_CATEGORIES)")

    names = [fn for p in parts for fn in p["functions"]]
    if len(names) != len(set(names)):
        raise ValueError(f"names planned twice: {sorted({n for n in names if names.count(n) > 1})}")
    by_status: Dict[str, int] = {}
    for p in parts:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
    return {
        "api": API,
        "generated_by": "arsenal/shaders/atlas_build.py",
        "source": {"draft": draft.resolve().relative_to(ROOT).as_posix() if ROOT in draft.resolve().parents
                   else draft.as_posix(),
                   "draft_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                   "rulings": RULINGS.relative_to(ROOT).as_posix()},
        "note": ("The primitive atlas as data: families, categories, planned parts, groups, the collision ledger and "
                 "the dissector's tag map. Generated from the draft; do not edit by hand. Our own words only: loved "
                 "shaders appear as ids and short names, never as code. Where the data departs from the draft, a "
                 "ruling in `rulings` says why."),
        "renames": dict(RENAMES),
        "renames_why": RENAME_RULING,
        "counts": {"families": len(families), "categories": len(categories), "parts": len(parts),
                   "by_status": dict(sorted(by_status.items())), "functions": len(names), "groups": len(groups),
                   "collisions": len(collisions), "rulings": len(rulings)},
        "rulings": rulings,
        "families": families,
        "categories": categories,
        "parts": parts,
        "groups": groups,
        "collisions": collisions,
        "manifest": manifest_rows,
        "loved": legend.rows,
        "tags": {"exact": TAG_CATEGORIES, "groups": TAG_GROUP_CATEGORIES},
    }


def dumps(atlas: dict) -> str:
    return json.dumps(atlas, indent=1, ensure_ascii=False) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="py -m arsenal.shaders.atlas_build", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draft", default=str(DRAFT))
    ap.add_argument("--out", default=str(OUT), help="where to write (default: arsenal/shaders/atlas.json)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the output file is not what the draft makes")
    ns = ap.parse_args(argv)
    out = Path(ns.out)
    text = dumps(build(Path(ns.draft)))     # raises before anything is written when the draft is malformed
    current = out.read_text(encoding="utf-8") if out.exists() else ""
    if ns.check:
        print("atlas.json is current" if text == current else "atlas.json is stale: run py -m arsenal.shaders.atlas_build")
        return 0 if text == current else 1
    out.write_text(text, encoding="utf-8", newline="\n")
    data = json.loads(text)
    full = out.resolve()       # a relative --out is never relative_to the absolute ROOT; its resolved path is
    shown = full.relative_to(ROOT).as_posix() if ROOT in full.parents else str(out)
    print(f"wrote {shown}: {json.dumps(data['counts'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
