"""
Hand-labeled gold fixture for the narrative spine (the local benchmark).

A realistic multi-domain Beat sequence with GOLD `track` labels, covering five segments
(ai-setup → research → stemroller → vision → ai-setup) with four real switches. A few
beats carry weak/misleading signals on purpose (honest misses) so a perfect score is
impossible — the heuristic should land ARI ≥ 0.70, not 1.0.

Each row: (gold_track, kind, paths, category, task, summary). The `source` is synthesized.
Reused across slices; when a real Beat exposes a missing case, add it here FIRST.
"""

# (gold, kind, paths, category, task, summary)
_ROWS = [
    # ---- Segment A: ai-setup (knowledge harmonization) ----
    ("ai-setup", "commit", ["core/foundation/store.py"], "", "", "Add TTL + zset ops to Store"),
    ("ai-setup", "learning", [], "refactoring_methodology", "", "backward-compat deprecated-alias strategy, zero breaks"),
    ("ai-setup", "commit", ["config.py", "core/foundation/redis_connection.py"], "", "", "Fix Redis port single source of truth"),
    ("ai-setup", "learning", [], "project_management", "", "semantic refactoring progress, 160 methods renamed"),
    ("ai-setup", "commit", ["context/project_context.py"], "", "", "Context pillar phase 1 onto Store"),
    ("ai-setup", "decision", [], "infrastructure", "harmonize knowledge store", "make Redis 16379 the canonical master"),
    ("ai-setup", "commit", ["scripts/snapshot_knowledge.py"], "", "", "knowledge snapshot/restore tool"),
    ("ai-setup", "learning", [], "testing", "", "robustness suite found the distiller source-less bug"),
    ("ai-setup", "note", [], "", "", "back to the harmonization pass"),                # no signal -> persist (ai-setup)
    ("ai-setup", "milestone", ["scripts/harmonize_knowledge.py"], "", "", "knowledge harmonized to 6 canonical lessons"),

    # ---- Segment B: research (narrative prior-art) ----
    ("research", "note", [], "", "", "starting to dig into the background reading"),                # weak 1st beat -> off-by-one switch (honest segmentation error)
    ("research", "learning", [], "knowledge_representation", "narrative prior art", "design lessons: reflection, bi-temporal, regenerate-from-atoms"),
    ("research", "note", [], "", "narrative prior art", "reading the Zep temporal knowledge graph paper on arxiv"),
    ("research", "learning", [], "research", "narrative prior art", "track inference == conversation disentanglement"),
    ("research", "note", [], "", "", "RAPTOR recursive tree is our skeleton analogue"),
    ("research", "learning", [], "knowledge_representation", "", "cross-domain analogues: PARA + Zettelkasten == Tracks + Themes"),
    ("research", "decision", [], "research", "", "adopt heuristic-first TrackRouter, embeddings later"),
    ("research", "milestone", [], "research", "narrative prior art", "prior-art research pass complete"),

    # ---- Segment C: stemroller (AMD/ZLUDA fork) ----
    ("stemroller", "commit", ["stemroller/src/main.js"], "", "", "AMD ZLUDA fork build setup"),
    ("stemroller", "milestone", ["stemroller/.github/workflows/build.yml"], "", "", "StemRoller AMD build passed CI"),
    ("stemroller", "learning", [], "infrastructure", "stemroller amd", "ZLUDA needs the HIP SDK on PATH"),
    ("stemroller", "learning", [], "infrastructure", "", "HIP SDK install notes"),       # honest MISS: infra/no-domain-kw -> routes ai-setup
    ("stemroller", "commit", ["stemroller/src/audio.js"], "", "", "wire demucs stem separation"),
    ("stemroller", "note", [], "", "stemroller", "stemroller demo recorded, vocals isolated"),

    # ---- Segment D: vision (ComfyUI / Florence-2) ----
    ("vision", "commit", ["ComfyUI-Zluda/nodes.py"], "", "", "ComfyUI node for Florence-2"),
    ("vision", "learning", [], "code_patterns", "vision florence", "Florence-2 OCR pipeline on DirectML"),
    ("vision", "commit", ["vision_engine.py"], "", "", "vision engine scan windows"),
    ("vision", "decision", [], "infrastructure", "vision", "use DirectML for Florence-2 inference"),
    ("vision", "learning", [], "research", "", "evaluating vision-language model quality"),   # honest MISS: research category -> routes research
    ("vision", "milestone", ["models/vision/florence2/config.json"], "", "", "Florence-2 deployed"),
    ("vision", "note", [], "", "", "comfyui workflow saved"),

    # ---- Segment E: ai-setup (narrative spine build) ----
    ("ai-setup", "commit", ["core/narrative/schema.py"], "", "", "Slice 0 narrative schema"),
    ("ai-setup", "learning", [], "project_management", "narrative spine", "Slice 0 schema validated against the 66-type vocab"),
    ("ai-setup", "commit", ["core/narrative/beat_log.py"], "", "", "Slice 1 BeatLog + hooks"),
    ("ai-setup", "learning", [], "testing", "", "beatlog isolated tests green"),
    ("ai-setup", "commit", ["tests/narrative_metrics.py", "tests/fixtures/narrative_fixture.py"], "", "", "Slice 2 fixture + metrics"),
    ("ai-setup", "note", [], "", "", "stretch break, then back to it"),                 # no signal -> persist (ai-setup)
    ("research", "note", [], "", "narrative spine", "is our narrative design truly novel vs Amory?"),  # honest MISS: 'narrative' -> routes ai-setup
    ("ai-setup", "commit", ["agent_cli.py"], "", "", "agent_cli list command + recall"),
    ("ai-setup", "decision", [], "project_management", "narrative spine", "build each slice test-first against acceptance bars"),
    ("ai-setup", "commit", ["docs/narrative-spine-plan.md"], "", "", "Mirror progress: narrative plan"),
    ("ai-setup", "milestone", ["core/narrative/track_router.py"], "", "", "Slice 2 TrackRouter clears the bar"),
]


def gold_rows():
    """Yield dicts: at, kind, summary, source, paths, category, task, gold."""
    rows = []
    for i, (gold, kind, paths, category, task, summary) in enumerate(_ROWS):
        hh = f"{i // 24:02d}"          # spread across days so timestamps stay valid
        at = f"2026-06-{1 + i // 24:02d}T{i % 24:02d}:00:00"
        src = (f"git:sha{i:03d}" if kind in ("commit", "milestone") and paths
               else f"learn:experiment:exp_{i:03d}" if kind in ("learning", "decision")
               else f"ledger:narr:{i:03d}")
        rows.append({
            "at": at, "kind": kind, "summary": summary, "source": src,
            "paths": paths, "category": category, "task": task, "gold": gold,
        })
    return rows


GOLD_TRACKS = sorted({r[0] for r in _ROWS})
