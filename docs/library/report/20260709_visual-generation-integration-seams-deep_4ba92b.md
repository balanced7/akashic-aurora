---
akashic_id: art_20260709_visual-generation-integration-seams-deep_4ba92b
akashic_sha: eca83df55702
status: draft
type: report
date: 2026-07-09
title: Visual-generation integration seams -- DeepSeek report (verbatim)
gist: "# Visual-generation integration seams -- DeepSeek report (verbatim) Companion to research/reviewed/webagent-visualgen-sweep-2026-07-09.md (f"
tenant: solo
visibility: fleet
seats: []
category: [migration, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_visual-generation-repo-sweep-web-agent-v_78ec97
    rel: cites
  - target: art_20260709_visual-generation-integration-reconciled_3150cc
    rel: cites
  - target: art_20260717_story-generated-2026-07-17t05-16-07-7889_6557c1
    rel: cites
  - target: art_20260723_last-session-draft-auto-captured-2026-07_1dd6ee
    rel: cites
created: "2026-07-09T20:39:21"
updated: "2026-07-23T21:42:18"
---
<!-- GENERATED PROJECTION of art_20260709_visual-generation-integration-seams-deep_4ba92b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Visual-generation integration seams -- DeepSeek report (verbatim)

# Visual-generation integration seams -- DeepSeek report (verbatim)

Companion to research/reviewed/webagent-visualgen-sweep-2026-07-09.md (fenced web
verification of the external repos). This is the inside-the-codebase seam mapping,
delivered by the freshly-restarted runner (T018 bounce + T019 drained pipes active;
first attempt was lost to the T019 pipe-wedge). Detected by the P0 wake listener and
consumed through the normal door -- nothing eaten. Reconciliation:
docs/visual-gen-integration-2026-07.md.

---

I now have a complete picture of the codebase. Here's the full integration-seams mapping:

---

## Integration Seams Mapping — All 5 Capability Classes

### A. Partial/Real-time UI Updates (granular DOM patching)

**Seam:** `scripts/bifrost_ui.py:206-235` — the `_events()` method (SSE via `text/event-stream`) and the `_sse()` helper (`data:` lines). The browser reads these as `EventSource` and does a *full* log re-render (`#log innerHTML` append). The `bifrost_viz.js` `VizEngine` (line 118) also re-renders entire cards per frame via `requestAnimationFrame`.

**Replaces/upgrades:** The whole SSE+poll transport. Currently every message = full JSON → full DOM fragment. No granular patching exists. A websocket + DOM-diff (htmx, Alpine, or a signal-based renderer) would let individual message fields (`content`, `meta`, the HUD strip at `#hud`, the activity indicator at `#activity`, the current-episode panel at `#epi`) update independently.

**Smallest first slice:** Replace the SSE `EventSource` with a thin WebSocket shim in `bifrost_ui.py` (add a `/ws` endpoint via `websockets` or keep stdlib-only with a polling-fallback upgrade path). Patch ONE element live — the `#activity` typewriter strip — without touching `#log`. 

**Evidence gate:** Open two browser tabs; send a message in one. The other shows the activity indicator update within 200ms AND the message body — no full-page flicker, no log re-scroll jitter. Measure: `performance.now()` delta < 50ms for activity-only updates vs current ~150ms full re-render.

**Reasons NOT to:** 
1. **Maintenance surface.** SSE is 8 lines in stdlib. WebSockets bring a framing protocol, upgrade handshake, ping/pong keepalive, and reconnection logic. This is a solo dev project; stdlib-only is a deliberate architectural posture.
2. **The current polling fallback is already robust.** SSE reconnects natively on disconnect. WebSocket reconnection requires a JS state machine.
3. **Overlap risk.** The existing viz canvas already does granular frame updates (`_tick()` at line 182). Adding DOM-granularity to the chat log duplicates a pattern the canvas already solves — the cockpit is fundamentally a terminal-like stream, not a reactive app.

---

### B. Markdown/Outline → Slide Deck Generation

**Seam:** Two seams form the pipeline: (a) `core/narrative/chronicler.py:378-429` `_render()` writes `chronicles/story.md` — a Markdown document with `## Chapter Title` headers, each with `Beats: N · Critic: True/False` + summary bullets with `(source: ...)` pointers. (b) `agent_cli.py:1080-1141` `cmd_wrap()` produces `chronicles/last-session-draft.md` — shipped/learned/decided sections with git: and learn: source pointers.

**Replaces/upgrades:** This IS what a slide-deck generator consumes. The `chronicles/story.md` already has the structure: Atlas (overview), then per-chapter `## Title (track)` headings + `Span:` + summary bullets. A slide generator would read this file (or `story.index.json`) and map `## → slide title`, bullet list → slide body, `Span:` → footer. The `wrap` draft is a session-summary variant (one deck per session vs one deck per chronicle).

**Smallest first slice:** `scripts/gen_slides.py` (new): reads `chronicles/story.index.json`, maps chapters → reveal.js or pptx slides via `python-pptx`. First slice = ONE output format (HTML/deck via a self-contained `<script>` inline reveal.js), zero external services. CLI: `py scripts/gen_slides.py` → writes `chronicles/story.html` (a single-file presentation).

**Evidence gate:** Open `chronicles/story.html` in a browser; every chapter is one slide. Title matches `##` heading. Bullets are preserved. Clicking advances. Total chapters in deck = chapters in story.md (currently 31). If 31 slides render, gate passes.

**Reasons NOT to:**
1. **The wrap output is higher-value for this repo.** The `chronicles/story.md` is a project journal; the `last-session-draft.md` is an agent's working memory. Slide generation is an *external* consumption format — nice-to-have, not a system capability.
2. **python-pptx adds a non-trivial dependency.** The repo is aggressively stdlib-only. A reveal.js HTML deck needs no Python dependency (just JSON→HTML string), but a pptx output does.
3. **The story format is still evolving.** The chronicler is on v0 (see `story.md` line 3: `Version: 0`). Building an exporter before the format stabilizes means chasing schema changes.

---

### C. Chat-with-Data Chart Generation

**Seam:** `scripts/bifrost_viz.js:254-340` — the `bar-chart` and `code-tree` (file-touch heatmap) cards in the `CARD_REGISTRY`. These are pure canvas renders fed by `TraceData` (line 42), which ingests `kind=trace` events. The `TraceData` model already captures agent-activity counts, file-touch counts, and edges. A `data-chart` card would hook into the same `CARD_REGISTRY` pattern.

**Replaces/upgrades:** The existing cards are hardcoded to *trace* data (tool calls, thinking, file touches). A general data-chart card would read tabular data from a chat message (an agent says "here's a CSV" or the user drops a table) and auto-select chart type. It extends, not replaces, the existing `registerCard` pattern.

**Smallest first slice:** Add a `table-chart` card to `bifrost_viz.js` that listens for `kind=chat` messages containing markdown tables. Parse the first `|...|` table, auto-detect column types (numeric vs string), render a bar or line chart. Register via `registerCard()` at script load. 

**Evidence gate:** Send a chat message containing `| Month | Value |\n| Jan | 10 |\n| Feb | 25 |`. The viz canvas (toggled with 'v') shows a new card "Data Chart" with a bar chart of those two values. No table → the card shows "no tabular data yet."

**Reasons NOT to:**
1. **This is a feature for a data-analysis tool, not a coordination cockpit.** Bifrost's purpose is live agent collaboration. Charts from agent-produced tables are a demo feature, not a capability gap.
2. **Chart library dependency creep.** Auto chart-type selection that's actually *good* (not just "numeric Y-axis → bar") requires something like Vega-Lite or a small heuristic engine. The current viz cards are 40-line canvas functions.
3. **The data plane already exists.** An agent that wants charts can already write an HTML file and the user opens it. The value of embedding charts in the cockpit is low — the cockpit is for steering, not analysis.

---

### D. Code/Text → Architecture + Flow Diagrams

**Seam:** `scripts/gen_arch_index.py` (entire file, 92 lines) + `docs/ARCHITECTURE.md` (hand-maintained prose) → `docs/MODULE_INDEX.md` (auto-generated per-module index). The pipeline: `gen_arch_index.py` walks `core/*/` directories, extracts line-1 docstrings via `ast.get_docstring()`, and renders a Markdown index ordered by architectural layer (`CORE_ORDER` list, line 22-27).

**Replaces/upgrades:** `gen_arch_index.py` produces a *text index*, not a diagram. A diagram generator would read the same source (module docstrings + import graph via `ast.parse`) and render an SVG architecture diagram: boxes = modules (grouped by layer), edges = imports, labels = docstrings. This is a direct visual upgrade to the auto-generated index.

**Smallest first slice:** `scripts/gen_arch_diagram.py` (new): walks the same `core/*/` directories as `gen_arch_index.py`, builds an import graph by parsing each `.py` file's `ast.Import`/`ast.ImportFrom` nodes, renders an SVG with `<rect>` per module (grouped by layer / colored by `CORE_ORDER` position) and `<line>` edges for imports. Writes `docs/ARCHITECTURE.svg`. Zero external dependencies (pure `ast` + string-building).

**Evidence gate:** Run `py scripts/gen_arch_diagram.py`. Open `docs/ARCHITECTURE.svg`. Every `core/*/` module is a box. Boxes are grouped and colored by layer (foundation=blue, events=green, etc.). Lines connect importer→imported. If the SVG has >= number of modules in `gen_arch_index.py` output, gate passes.

**Reasons NOT to:**
1. **The text index is more actionable.** Agents read `MODULE_INDEX.md` to find what module does what. An SVG diagram is a human presentation artifact — it doesn't help agents navigate the codebase.
2. **Import-graph diagrams get noisy fast.** A 50+ module codebase produces a hairball. Filtering to "important" edges requires a salience heuristic that's a research project on its own.
3. **The ARCHITECTURE.md prose is the authoritative diagram.** It's maintained deliberately, not auto-generated, because architecture is about *design intent*, not just physical structure. An auto-diagram can contradict the prose.

---

### E. Multi-layer Editable Poster/Graphic Composition

**Seam:** There is **no direct seam** for this in the codebase. The closest analog is the viz canvas (`bifrost_viz.js:118-260`) which composites multiple layers: the dark background fill, card renders, grid overlays, and navigation labels. The aurora canvas (`aurora-shader.js`) is a separate WebGL layer at z:-2, composed under the viz canvas (z:-1) and the HTML cockpit (z:≥0). But none of this is *editable* — it's a render-only pipeline.

**Replaces/upgrades:** Nothing existing. This would be a net-new capability with no natural anchor in the codebase. The closest integration point would be extending the `/upload` endpoint (`bifrost_ui.py` POST `/upload`, line 296) and the dropbox (`DROPBOX = .../dropbox`) to accept a composition file format.

**Smallest first slice:** Unclear. Every other class has a file/function already waiting. This class would need: a canvas editor, layer management, export. That's a standalone application, not a capability to fold into a coordination cockpit.

**Evidence gate:** N/A — no seam exists to measure against.

**Reasons NOT to:**
1. **Zero codebase adjacency.** This is a graphic design tool. Bifrost is a multi-agent coordination cockpit. There is no shared data model, no shared transport, no shared user workflow.
2. **The dropbox already handles file sharing.** If someone needs a poster, they create it in an external tool and drop it in dropbox. The agents can read it.
3. **Maintenance mismatch.** A poster editor needs undo/redo, layer serialization, export formats, color pickers — UI infrastructure that would double the size of `bifrost_ui.py` (already 151KB) for a capability orthogonal to the project's purpose.

---

## Ranked by Value-to-Effort FOR THIS REPO

| Rank | Class | Value | Effort | Rationale |
|------|-------|-------|--------|-----------|
| **1** | **D — Architecture diagrams** | HIGH | LOW | `gen_arch_index.py` already does 80% of the work (AST walk, docstring extraction, layer ordering). Adding import edges → SVG is ~100 lines of pure stdlib Python. Value: every agent boot sees the architecture; a diagram is immediate orientation. The `ast` module is already imported. |
| **2** | **B — Slide deck generation** | MEDIUM | LOW | `chronicles/story.md` + `story.index.json` are the structured input already. A self-contained reveal.js HTML is ~80 lines of template + JSON→slide loop. Value: project storytelling (demos, retrospectives). The `chronicles/` directory is the natural output location. |
| **3** | **A — Real-time UI updates** | MEDIUM | MEDIUM | SSE works well enough that the pain is theoretical. The real upgrade would be HUD-strip granularity (activity indicators) — but that needs WebSocket infrastructure (new endpoint, JS state machine, reconnection), breaking the stdlib-only posture. Value: polish, not capability. |
| **4** | **C — Chat chart generation** | LOW | MEDIUM | The viz card registry exists, but auto chart-type selection needs heuristic logic or a library. Value: agents rarely produce tabular mid-conversation data (it's mostly prose, code, and traces). This is a demo feature, not a daily-driver. |
| **5** | **E — Poster composition** | NEGLIGIBLE | HIGH | No seam. No shared data model. No natural workflow. This would be building a separate application inside the cockpit. The dropbox already solves the file-sharing use case. |

**Top recommendation: do D first** (architecture diagrams from `gen_arch_index.py`). It's the clearest seam, the highest value-to-effort, and it directly improves agent orientation — which IS this repo's purpose. The AST walker, docstring extractor, and layer ordering are already written and proven. Adding an SVG render pass on the same data is a single afternoon slice that produces a durable artifact.
