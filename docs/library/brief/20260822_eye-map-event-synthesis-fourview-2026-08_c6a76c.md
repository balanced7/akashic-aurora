---
akashic_id: art_20260822_eye-map-event-synthesis-fourview-2026-08_c6a76c
akashic_sha: faf54665b5ba
schema_version: 1
status: current
type: brief
arc: T375
date: 2026-08-22
title: eye-map-event-synthesis-fourview-2026-08-22
gist: "# The Eye, the Map, and the Event Highway — four-view synthesis (2026-08-22) Commissioned by Daniil (\"do a deepseek fanout to make sure you "
visibility: fleet
body_type: markdown
seats: [claude, deepseek]
category: [memory, method, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-22T12:30:29"
updated: "2026-08-22T12:30:29"
---
<!-- GENERATED PROJECTION of art_20260822_eye-map-event-synthesis-fourview-2026-08_c6a76c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# eye-map-event-synthesis-fourview-2026-08-22

# The Eye, the Map, and the Event Highway — four-view synthesis (2026-08-22)

Commissioned by Daniil ("do a deepseek fanout to make sure you get everything" on the Eye
arc). FOUR independent views: Heimdall's N-version synthesis (persisted verbatim at
research/reviewed/the-eye-synthesis-heimdall-nversion-2026-08-22.md) + three Explore agents
(Eye code/history, spatial-knowledge interconnections, Simon/event arc). They converge on the
spine; this brief is the reconciled whole. Every claim traces to a source the agents cited.

## The headline the fanout surfaced

**The "map" everyone is excited about is three-quarters BUILT, and nobody in the conversation
remembered.** Simon's 08-22 "Google Maps for systems architecture" proposal, the deck's item C,
and the Eye's month-old unbuilt `eye map` slice are THE SAME THING. The pieces:

| map component | state | organ |
|---|---|---|
| zoom engine | **BUILT** | the Eye's S2 LOD pyramid (L4 era→L0 event, extractive, fidelity-by-construction) |
| trails | **BUILT** | routes / "the string through the forest" (T323 s1, core/eye/routes.py + routes.jsonl) |
| position ("you are here") | **BUILT** | the Eye's S6 inhabitant loop (per-incarnation cursor) |
| the practice that walks it | **ACTIVE** | Forest Walks (walk-01 banked) |
| event-topology DATA | **NEW/proposed** | Simon's AsyncAPI catalog (T379) |
| the render layer | **DESIGN-FENCE-PENDING** | `eye map` (designed as Eye S5, shipped as stats+overview instead) + fuma-docs |

So deck item C is not "build a map from scratch." It is "build the render layer over an organ
that already has the index, pyramid, trails, and position loop." Much smaller than it looked.

## The Eye (T278) — BUILT, S0–S7, Heimdall's daily toolset

**What it is:** the sensorium that makes the transcript corpus INHABITABLE terrain — "how does an
AI inhabit this system?" (v2 reframe, design 20260811_the-eye-design-v2_208b26). One door
(cmd_eye, agent_cli.py:2293), many verbs, over one SQLite projection (state/eye/eye.db).
Born from a wound: two operator directives died unnoticed; recovering them took nine guessed
searches. And the deeper wound — Daniil's own voice hides in queue-operation records, not
type:user rows (the operator-speech law, index.py:36-52).

**The stages (all shipped, each with a pin test test_t278_sN_*):**
- S0 index + coverage contract (never claims wholeness past a gap)
- S1 grammar door (find/get, T280 grammar: who= kind= edge= as_of= since= q= strict=)
- S2 pyramid — LOD, extractive-only (no LLM in path), L1 exchange / L2 session verbatim opener
- S3 freq — "HIS axis," utterance-counted, mechanical verdict (unheard→standing-directive)
- S4 connectome — edges remember formation + evidence grade (recorded/derived/inferred)
- S5 stats+overview (NOTE: design's S5 was `eye map`; shipped as stats+overview instead)
- S6 position — the inhabitant loop, per-incarnation cursor, inherit() as explicit succession
- S7 directive watcher — "closes its own founding wound," proposes-never-ratifies
- Plus T313 archive-reaching corpus, T323/T335 routes.

**The core principle:** "LOD as regenerable projection, fidelity by construction." Descent =
following citations (refs are literal event_ids), never re-search. Summaries EXTRACTIVE-ONLY so
they cannot invent a reference — "a stale summary is honest fog; a LYING summary is invisible
poison." Staleness always surfaces as fog, never silence.

**THE SCAR (load-bearing, and it closes a circle):** "regenerable" has one hard exception — the
`events` table is NOT disposable. v2 first shipped as wipe-and-rebuild on the design's own words,
and the first live run DESTROYED ≥219 events from two sessions whose transcripts had already
rotated off disk. For a rotated session, the projection IS the archive. Law now: migrations ADD
never DROP; derived tables (pyramid, edges) rebuild freely, `events` may not. **This incident is
where the lesson `a_rebuildable_projection_stops_being_one_when_its_source_rotates` was born — the
SAME lesson that fired to caution Simon's event-highway proposal on 2026-08-21 (stream-trimming
breaks rebuild-from-source). The house learned it by losing 219 events; the scar then guarded a
proposal made a month later.**

## The spatial stack — one engine, many scopes

THE TERRITORY = the corpus (atoms on Redis). Over it:
- **PUSH engine** = the recall funnel (BUILT, core/recall/at_action.py, 8 stages, 52/100 fire
  rate) — decides what you need at the moment of action.
- **PULL twin** = queriable-recall-fidelity-plane (DESIGNED) — fidelity as a dial (L0 line / L1
  excerpt+credits / L2 verbatim / L3 +lineage), a thin query plane over existing organs, shares
  the Ranker + credit loop with push. Both write recall_feedback; T369 evaluates both.
- **The trail RECORDING** = recall:outcome stream (BUILT) — per-action {at, cmd, ok, surfaced,
  agent, sid}. Recording exists; SENSING does not.
- **SENSING** = T378 proximity sensor (APPROVED, unbuilt) — reuses the funnel's stem/IDF engine
  with --scope trails; returns "who was here, what they tried, where they turned back"; loop
  alarm on same-signature failing repeats; gates G1 (youtube trail) / G2 (redelivery loop)
  pre-registered.
- **Intent-time** = T377 recall-at-choice (APPROVED, unbuilt) — recall at the prompt boundary,
  keyed on operator-text URLs/paths/verbs. Composes with T378: distilled lesson + evidential
  trail = navigation with lineage. Both born from the 08-22 captions miss.
- **The practice** = Forest Walks (ACTIVE) — predict-before-you-look, source-only, teach-back;
  walk notes leave "trails for proximity to read later." walk-01 P1/P2 banked, **P3 + teach-back
  RESERVED for Daniil — do not front-run.**

## The event architecture (Simon's 08-22 arc) — the north-star above it all

Simon's five chained insights (co-root, snowflake 644993333000798243, brief-answers law):
1. **Event-highway north-star** (note event-highway-northstar-for-t374) — make the event log the
   universal master, all state derived; the endgame of T374's master-declaration doctrine.
2. **AsyncAPI catalog** (T379, PROPOSED — only unapproved of the six) — exhaustive human-readable
   domain-event spec; the PRECONDITION for #1 (can't derive-all-from-events until cataloged).
3. **Checked-contract upgrade** (in T379) — validate spec-vs-reality both ways (sibling to
   check_kind_policy); attacks kind-fragmentation tickets T174/T175/T177.
4. **fuma-docs render** (note systems-map-render-layer-simon) — the map's presentation layer;
   the event-topology layer of deck-C.
5. **Kleppmann/Young required reading** (note event-arc-required-reading-kleppmann-young) —
   canonical theory. THE CONVERGENCE: the house discovered both principles by pain before the
   names — "atom is truth, projection derived" = Kleppmann's log-centric architecture;
   "supersession never deletion" = Young's "never mutate a published event, version instead."

## The task board (all 2026-08-22 unless noted)

- T374 two-store census + master-doctrine + reconciler (sync/async razor) — APPROVED
- T375 engineering forecast registry (deck-B, BUILD FIRST) — CLAIMED by claude; gains dies_when
- T376 fleet metabolism (deck-D) — APPROVED
- T369 recall eval suite (deck-A, LAST — inherits registry+map+metabolism) — APPROVED (08-21)
- T377 intent-time recall — APPROVED
- T378 proximity sensor v0 — APPROVED
- T379 AsyncAPI event catalog — PROPOSED (needs Daniil's letter)
- Build order: T375(B) → map(C) design fence → T376(D) → T369(A).
- Trader arc (paper-only): design r2 + case bench + C4 forensics; archivist LIVE; P1 gates Daniil.

## For the fresh seat

Everything above surfaces via boot + notes --json + task list. Heimdall's full Eye synthesis is
at research/reviewed/the-eye-synthesis-heimdall-nversion-2026-08-22.md. The three Explore agent
outputs (fuller detail with file:line pointers) are in this session's task transcripts. The one
thing to internalize: the map is a render layer over built organs, not a greenfield — and its
zoom engine (the Eye) has been running the whole time.
