---
akashic_id: art_20260822_c-map-fence-opening_e0a674
akashic_sha: 9b0c63e5e969
schema_version: 1
status: current
type: map
date: 2026-08-22
title: c-map-fence-opening
gist: "# The Map — design fence opening position (C of the enablement deck) **Fence opened:** 2026-08-22 evening, by Vandor (claude), per Daniil's "
visibility: fleet
body_type: markdown
seats: []
category: [memory, method, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-22T14:47:14"
updated: "2026-08-22T14:47:14"
---
<!-- GENERATED PROJECTION of art_20260822_c-map-fence-opening_e0a674 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# c-map-fence-opening

# The Map — design fence opening position (C of the enablement deck)

**Fence opened:** 2026-08-22 evening, by Vandor (claude), per Daniil's B→C→D→A ruling
(note `attention-sequence-2026-08-22`: "the map second — visibility while building;
landmarks+trails+walks+case-bench+archivist rendered", with a design fence wanted
before build and Simon's eyes explicitly requested). Halves invited: Heimdall
(deepseek), Simon (co-root), Navi (kimi) if budget allows. Daniil gates ratification.

## Why this fence is unusually well-fed

Three independent descriptions of the same organ arrived within one day, from three
directions, none aware of the others when written:

1. **Simon's event-plane bid** (vandor chat, 2026-08-21/22, verbatim): "build out a
   human-readable map of all our domain events in an AsyncAPI spec file... visualize
   it using fuma-docs... behind a thin better-auth gateway so only me & Daniil can
   see... Think of it like a google maps equivalent for systems architecture." Plus
   his resources: Kleppmann (log-centric derived views) and Greg Young (versioning of
   event-sourced systems) — both already folded into T374 doctrine and T375's door
   (note `simon-event-map-and-resources-2026-08-22`).

2. **Heimdall's Eye synthesis** (bus 1787415921767-0, persisted at
   `research/reviewed/the-eye-synthesis-heimdall-nversion-2026-08-22.md`): the Eye is
   "a regenerable-projection LOD pyramid over an append-only event index... and it is
   the **zoom axis** of the map Simon and Daniil are now converging on." Built S0–S7,
   live in `core/eye/`, grammar door `eye find/look/go/zoom/freq/trace/stats/overview`.

3. **The trail plane** (T378, approved, gates G1/G2 pre-registered): proximity
   sensing over the `recall:outcome` stream — "who was here, what they tried, where
   they turned back, where they arrived." Daniil's founding phrasing (2026-08-21,
   verbatim): "sense what prior agents touched and reached for so we can hopefully
   use that to catch loops and missing logic sooner. We can walk prior work actions
   and see the reasoning and flow."

**The opening claim:** these are not three maps. They are three AXES of one map —
the event plane (what can happen and what it carries), the zoom axis (LOD from
atlas down to a single utterance), and the trail plane (who moved through here and
how it went). A design that builds any one of them as a standalone product will
rebuild the other two badly later.

## Opening position (attack this)

- **P1. One substrate, three projections.** The map renders FROM the append-only
  planes that already exist (events:raw, the Eye index, recall:outcome, the ledger)
  — it owns no truth, writes nothing, and every rendered view is regenerable (the
  T374 master/derived doctrine applied to cartography). If the map needs a write,
  the design is wrong.
- **P2. AsyncAPI as the event-plane CONTRACT, not just documentation.** Simon's spec
  file is the census instrument for T374's event half: enumerating domain events to
  write the spec IS the census of what rides the bus, and drift between spec and
  observed traffic becomes a doctor check (spec says X, wire carries Y — the same
  stamps-compare shape as the reconciler). The spec earns its keep as an instrument,
  or it is a brochure.
- **P3. The Eye is the zoom mechanism, not a sibling.** Deep links from map nodes
  resolve through the existing eye grammar (`eye go/zoom`); the map never grows its
  own transcript reader. LOD tiers reuse the Eye's pyramid.
- **P4. Trails render ON the map, sensed by T378.** The map shows trail segments as
  overlays (heat, termini, turn-backs); T378's sensor supplies them at intent-time.
  Map and sensor share the signature engine (enablement-first: no new engine).
- **P5. Render target v1: fuma-docs static behind better-auth (Simon's stack), fed
  by a generator script that runs at gate-time + on-demand — NOT a live service.**
  A live map service is a second store with a heartbeat; a regenerated static site
  is a projection with a timestamp. Live-ness arrives later, if ever, behind the
  same generator seam (the T375 fold lesson, applied to rendering).
- **P6. Ownership split offered:** Simon — AsyncAPI spec + fuma-docs render (his
  bid, his stack); Heimdall — Eye integration + the LOD/zoom contract; Vandor —
  trail overlay + the generator + T374 census join; Navi — adversarial pass on the
  whole (budget permitting). Daniil — ratification + the better-auth boundary call.

## Fence questions (each half answers, evidence over vibes)

- Q1. What does v1 SHOW on its front page? (My bid: the event map with live-ness
  badges per event kind + the deck's active tasks as landmarks + last-24h trail
  heat. Attack with a better front page.)
- Q2. Is AsyncAPI expressive enough for our bus semantics (lanes, dual-write,
  redelivery, ANSWER_KINDS settle) or does it need an extension convention?
- Q3. Where does the map LIVE — repo-generated static (my P5) vs bifrost UI tab vs
  both? What dies_when does each choice carry?
- Q4. What is deliberately NOT on the map v1? (Name the exclusions or scope creeps.)
- Q5. The forged-attribution class just closed for timestamps (T375). What is the
  map's equivalent lie, and which pin kills it? (My candidate: a rendered view
  without its generation stamp + source-plane cursor positions = a map that cannot
  be dated is a map that lies about now.)

## Process

Standard fence: halves filed blind to `research/in-flight/`, reconcile after two
counters or 48h, reconciled design → Daniil's gate. Registration at approval rides
T375 (the registry nags this fence's own forecast: see F-entries under task ref
C-map once approved).
