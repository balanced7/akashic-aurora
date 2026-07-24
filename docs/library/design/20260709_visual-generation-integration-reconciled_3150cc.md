---
akashic_id: art_20260709_visual-generation-integration-reconciled_3150cc
akashic_sha: 07f49f08ff18
status: current
type: design
date: 2026-07-09
title: Visual Generation Integration -- Reconciled Plan (web sweep x codebase seams)
gist: "Date: 2026-07-09 Inputs: research/reviewed/webagent-visualgen-sweep-2026-07-09.md (fenced web verification of Daniel's candidate list -- all"
tenant: solo
visibility: fleet
seats: []
category: [migration, method, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_visual-generation-repo-sweep-web-agent-v_78ec97
    rel: cites
  - target: art_20260709_visual-generation-integration-seams-deep_4ba92b
    rel: cites
created: "2026-07-09T20:40:37"
updated: "2026-07-23T21:42:08"
---
<!-- GENERATED PROJECTION of art_20260709_visual-generation-integration-reconciled_3150cc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Visual Generation Integration -- Reconciled Plan (web sweep x codebase seams)

Date: 2026-07-09
Inputs: research/reviewed/webagent-visualgen-sweep-2026-07-09.md (fenced web verification of
Daniel's candidate list -- all 10 repos exist; 2 unlicensed, 1 code-less paper stub) +
research/reviewed/deepseek-visualgen-seams-2026-07-09.md (inside-the-codebase seam mapping).
Neither side saw the other's report.

## Where the two blind passes CONVERGE (highest confidence)

1. ARCHITECTURE DIAGRAMS FIRST (class D). DeepSeek ranks it #1 (gen_arch_index.py already
   does 80% of the work: AST walk, docstrings, layer order; adding import-edges -> SVG is
   ~100 lines of stdlib). The web sweep's top diagram picks are complementary, not
   competing: kroki/mermaid = deterministic token-free text->SVG rendering; next-ai-draw-io
   MCP = agent-authored diagrams as EDITABLE XML artifacts (ledger-friendly).
2. DECKS FROM WHAT WE ALREADY WRITE (class B). DeepSeek: chronicles/story.index.json ->
   single-file HTML deck, ~80 lines, zero deps. Web sweep: same conclusion from the other
   direction -- deterministic md->deck (marp/slidev) beats AI-layout services on cost and
   reviewability; steal ppt-agent's single-file export + Cocoon's self-contained-HTML house
   style. presenton (Apache-2.0, API+MCP, Ollama-capable) is the DEFERRED full tier, adopted
   only if the cheap tier proves insufficient for external optics.
3. SKIP CHARTS AND POSTERS (classes C, E). DeepSeek: C is a demo feature for a coordination
   cockpit, E has zero codebase adjacency. Web: C's candidate repos are unlicensed and dead
   anyway; E's is a paper stub with no code. Unanimous NOT-build.

## The one genuine TENSION, and its resolution (class A -- real-time UI)

DeepSeek argues against: SSE works, WebSockets add a reconnection state machine and break
the stdlib-only posture, the pain is theoretical. The web sweep's finding DISSOLVES rather
than contradicts this: partialupdate's Chrome-only spec is a no-go, but its PROTOCOL IDEA
(server streams named HTML fragments; client patches them at target markers) and datastar's
production framing are both SSE-NATIVE. No WebSockets. Resolution: keep the existing SSE
channel and teach its payloads to carry {target-id, fragment} patches, applied by ~30 lines
of dependency-free client JS -- granular #activity/#hud/#epi updates, no transport change,
no framework, posture intact. DeepSeek's own evidence gate (two tabs, <50ms element patch,
no log jitter) still applies.

## Proposed slices (each Daniel-gated; smallest diffs first)

V1 (class D, do first -- both passes agree): scripts/gen_arch_diagram.py -- pure-stdlib AST
    import-graph over core/*/, layered boxes + import edges -> docs/ARCHITECTURE.svg,
    regenerated like MODULE_INDEX (autogen = cannot rot; living-docs pattern). Also emit the
    same graph as mermaid text so the console can render it live later.
    GATE: every core module boxed + layer-colored; edges = real imports; count matches
    gen_arch_index; regenerating twice is byte-stable.

V2 (class B): scripts/gen_slides.py -- story.index.json -> ONE self-contained HTML deck
    (inline JS/CSS, offline, Cocoon-style export buttons), written to chronicles/story.html;
    optional wrap nudge ("session deck ready"). No python-pptx in v1 (stdlib posture; PPTX
    export deferred to marp-cli or presenton if ever needed).
    GATE: chapters in deck == chapters in story.md (31 today); opens from file:// offline;
    single file.

V3 (class A): SSE fragment-patch protocol in scripts/bifrost_ui.py -- events gain optional
    {target, html} patch shape; client applier patches those elements in place (log stream
    untouched). partialupdate's routing idea (include/exclude client ids) noted for the
    fidelity ladder later, not in v1.
    GATE: DeepSeek's -- two tabs open, activity strip updates <50ms without log re-render
    jitter; kill -9 the server mid-stream -> client recovers via native SSE reconnect.

V4 (class D+, evaluate after V1): `claude mcp add drawio` (next-ai-draw-io MCP, Apache-2.0,
    33k stars, active) for agent-INTERACTIVE diagrams; store the draw.io XML as atoms so
    diagrams are regenerable projections. Adopt only if V1's static SVG proves insufficient
    for design conversations.
    GATE: an agent produces + edits one architecture diagram via MCP; XML persisted +
    re-rendered identically.

NOT building (unanimous across both passes): WebSockets transport; chart cards (class C);
poster composition (class E); presenton now (deferred full tier); any code from unlicensed
repos (chart-agent, ChartAI -- ideas only); kroki sidecar now (mermaid script-tag in-console
covers the rendering need without a new service; revisit if server-side rendering is needed).

## Sequencing note

V1 dovetails with the comms-pillar P2 slice (boot orientation header): the architecture SVG
becomes the map the header points at. If Daniel wants one combined arc, P2+V1 is the natural
pairing.
