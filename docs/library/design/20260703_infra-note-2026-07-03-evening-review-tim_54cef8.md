---
akashic_id: art_20260703_infra-note-2026-07-03-evening-review-tim_54cef8
akashic_sha: 3919cc270962
status: draft
type: design
date: 2026-07-03
title: "infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes"
gist: "# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes # stdout+stderr for the full 35m) -- the head"
tenant: solo
visibility: fleet
seats: []
category: [memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-03T23:11:34"
updated: "2026-07-03T23:11:34"
---
<!-- GENERATED PROJECTION of art_20260703_infra-note-2026-07-03-evening-review-tim_54cef8 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes

# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes
#   stdout+stderr for the full 35m) -- the headless process produced no output at all, an infra
#   hang not a content problem. See runlog-2026-07-03.md; 6 of 12 shift tasks hit this pattern.
#   Requeued as-is. Next shift: OLLAMA_KEEP_ALIVE set longer before relaunch (see where-we-are).
# TASK: What is the best local, always-on stack to VISUALIZE the live knowledge state (narrative spine, recall funnel, codex projections) in real time -- the uniquely-ours A1 slice?
feeds: A-series A1 (live visualization -- nobody else can visualize outcome-credited memory; portfolio gold + the assistant's "mind on screen")
seeds:
- https://github.com/r0x0r/pywebview
- https://d3js.org/
- https://cytoscape.org/
notes: |
  Trigger: a-series vision (ADR_0703095414) -- A1 = live viz of spine/funnel/codex, the ONE
  differentiator competitors structurally cannot copy (they have no outcome-credited memory to
  show). Runs FREE on the fleet now; BUILD is gated behind the S2 first pass like every a-series
  slice. Target: an always-on local panel that reads our Store/Ledger/funnel and renders, live:
  (1) the narrative spine (Atlas->Track->Chapter->Beat) as a navigable timeline/graph;
  (2) the recall funnel (surfaced->useful->helped->flips, value-rate trend);
  (3) codex/theme projections over the atoms. Chase, fetch-before-cite:
  (1) SHELL: pywebview vs a plain local FastAPI+browser tab vs Tauri(python?) -- always-on,
      low-friction, Windows 11, reads a live local process. Which is least ceremony for v0?
  (2) GRAPH/TIMELINE VIZ: D3 vs Cytoscape.js vs vis-network vs sigma.js for an evolving
      knowledge graph + a value-rate time series -- which handles incremental live updates
      (append a beat, don't re-layout the world) without a heavy framework?
  (3) LIVE TRANSPORT: how to push Store/Ledger deltas to the panel -- SSE vs WebSocket vs poll;
      our events are already an append-only firehose (core/events), so a tail->SSE bridge is the
      likely shape. Confirm the cheapest reliable pattern.
  (4) PRIOR ART: how do observability/graph-memory UIs (Letta's memory view, LangGraph Studio,
      Zep/Graphiti viz, generic MLflow/W&B live panels) structure real-time knowledge/agent viz
      -- what to borrow, what's overkill for a solo local tool.
  (5) READ-ONLY SAFETY: the panel observes, never mutates (no hidden write path from the UI).
  "Done" = a v0 stack pick (shell + viz lib + transport) with the install steps, one wireframe
  sketch of the three panes, and the cheapest live-update pattern for our append-only events.
