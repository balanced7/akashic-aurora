"""The shader-craft skill must describe the code that exists, not the code that once did.

THE GUARANTEE THESE PIN: `.claude/skills/shader-craft/SKILL.md` and its cookbook are the
fold-back of the house's shader craft (the aurora bed, the geodesic avatar, the activity
line, the VFX bench, the sketches). A skill is loaded into a seat's context the moment a
shader is asked for, so a stale rule in it is a lie told at the exact moment it is trusted --
"the comment used to claim that global was read and it was not, which is the kind of small
lie that costs somebody an afternoon" (agent-avatar.js). Every repo path the skill names must
exist; every code line the cookbook quotes must still be in the file it names; the seam the
skill promises (isSupported / setState / setRate / destroy) must still be there; every sketch
must still speak the bench's dialect; every verb the loop names must still take the flags it
names. RED before the skill exists (P0), and RED again the day any of it drifts.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / ".claude" / "skills" / "shader-craft"
SKILL = SKILL_DIR / "SKILL.md"
COOKBOOK = SKILL_DIR / "references" / "house-glsl-cookbook.md"

# (file the cookbook says it quotes from, the exact line it quotes). Both directions are bound:
# the line must be in the source AND in the cookbook, so neither can drift without the other.
QUOTED = [
    ("scripts/activity-line.js",
     "void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0.0,1.0);}"),
    ("scripts/aurora-shader.js",
     "global.matchMedia('(prefers-reduced-motion: reduce)').matches"),
    ("scripts/aurora-shader.js", ".replace(/NPT/g,      String(NPT))"),
    ("scripts/aurora-shader.js",
     "float jit = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);"),
    ("scripts/aurora-shader.js",
     "outColor.rgb = mix(texture(u_history, uv).rgb, outColor.rgb, u_motion);"),
    ("design/vfx-sketches/fibshell.frag",
     "float aa = clamp(length(fwidth(m)) * sqrt(N) * 0.75, 0.02, 0.10);"),
    ("design/vfx-sketches/fibshell.frag", "for (int j = -26; j <= 26; j++) {"),
    ("scripts/agent-avatar.js",
     "if (sinceTick > 55) this._slowStreak = (this._slowStreak || 0) + 1;"),
    ("scripts/agent-avatar.js", "if ((this._slowStreak || 0) >= 45) {"),
]

# The seam the skill promises on every module: (file, [required tokens]).
SEAM = {
    "scripts/aurora-shader.js": ["isSupported", "setState(", "destroy(", "start("],
    "scripts/agent-avatar.js": ["isSupported", "setState(", "setRate(", "start("],
    "scripts/activity-line.js": ["isSupported", "setRate(", "start("],
}

# The verbs and flags the skill's loop names.
VERBS = {
    "scripts/vfx_render.py": ['add_parser("thumb"', 'add_parser("sheet"', 'add_parser("grid"',
                              'add_parser("state"', '"--t"', "--say", '"--frames"', '"--from"',
                              '"--to"'],
    "scripts/ui_shot.py": ["--label", "--fps", "--viewport"],
    "scripts/bifrost_ui.py": ['"/aurora-shader.js"', "aurora-fallback-hide", "isSupported()"],
}

_PATH_RE = re.compile(r"`((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.*-]+\.(?:js|py|md|frag|html|css))`")


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_p0_the_skill_and_its_cookbook_exist_with_the_house_frontmatter():
    assert SKILL.exists(), f"missing {SKILL}"
    assert COOKBOOK.exists(), f"missing {COOKBOOK}"
    head = SKILL.read_text(encoding="utf-8").split("---", 2)
    assert len(head) >= 3, "SKILL.md has no frontmatter block"
    fm = head[1]
    assert re.search(r"^name:\s*shader-craft\s*$", fm, re.M), fm
    assert re.search(r"^description:\s*Use when ", fm, re.M), "description must open with 'Use when'"


def test_p1_every_repo_path_the_skill_names_exists():
    missing = []
    for doc in (SKILL, COOKBOOK):
        for p in _PATH_RE.findall(doc.read_text(encoding="utf-8")):
            if "*" in p:
                # a glob names a family; the family's directory must exist and be non-empty
                d = REPO / Path(p).parent
                if not (d.is_dir() and any(d.glob(Path(p).name))):
                    missing.append(f"{doc.name}: {p}")
                continue
            if not (REPO / p).exists():
                missing.append(f"{doc.name}: {p}")
    assert not missing, "paths named by the skill that do not exist: " + ", ".join(missing)


def test_p2_every_line_the_cookbook_quotes_is_still_in_its_source_and_in_the_cookbook():
    book = COOKBOOK.read_text(encoding="utf-8")
    stale = []
    for rel, line in QUOTED:
        if line not in _read(rel):
            stale.append(f"{rel} no longer contains: {line[:60]}")
        if line not in book:
            stale.append(f"cookbook no longer quotes: {line[:60]}")
    assert not stale, "; ".join(stale)


def test_p3_the_seam_the_skill_promises_is_on_every_module():
    gone = []
    for rel, tokens in SEAM.items():
        src = _read(rel)
        for t in tokens:
            if t not in src:
                gone.append(f"{rel} lacks {t}")
    assert not gone, "; ".join(gone)


def test_p4_every_sketch_speaks_the_bench_dialect():
    bad = []
    for frag in sorted((REPO / "design" / "vfx-sketches").glob("*.frag")):
        src = frag.read_text(encoding="utf-8", errors="replace")
        if not src.lstrip().startswith("#version 300 es"):
            bad.append(f"{frag.name}: not #version 300 es")
        if "precision highp float;" not in src:
            bad.append(f"{frag.name}: no highp (our hashes band under mediump)")
        if "uniform float u_time;" not in src or "uniform vec2  u_res;" not in src:
            bad.append(f"{frag.name}: missing u_time/u_res")
    assert not bad, "; ".join(bad)


def test_p5_the_verbs_and_flags_the_loop_names_still_exist():
    gone = []
    for rel, tokens in VERBS.items():
        src = _read(rel)
        for t in tokens:
            if t not in src:
                gone.append(f"{rel} lacks {t}")
    assert not gone, "; ".join(gone)


def test_p6_the_skill_names_the_lessons_it_is_the_fold_back_of():
    text = SKILL.read_text(encoding="utf-8")
    for lesson in ("fibshell_shader_two_defect_classes", "rAF_throttle_reads_as_fps_freeze",
                   "claude_embedded_preview_crash_trigger_2026_08_12", "hud_fingerprint_diff_pattern"):
        assert lesson in text, f"SKILL.md does not name lesson {lesson}"
    assert "design/CONTRACT.md" in text, "SKILL.md must route taste to the design contract"
