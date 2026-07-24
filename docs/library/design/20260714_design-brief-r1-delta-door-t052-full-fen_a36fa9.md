---
akashic_id: art_20260714_design-brief-r1-delta-door-t052-full-fen_a36fa9
akashic_sha: 0b6d36791d13
status: current
type: design
date: 2026-07-14
title: "Design brief — R1 Delta Door (T052; full fence, M1-BRIEF format)"
gist: "Tier: FULL FENCE per M1-LITE gate 1 (new coordination-adjacent capability touching the boot/wake contract both agents live on; blind halves "
tenant: solo
visibility: fleet
seats: []
category: [bus, coordination, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_wishlist-synthesis-both-seats-one-map-20_90759f
    rel: cites
  - target: art_20260714_claude-wishlist-what-would-make-akashic_d87d17
    rel: cites
  - target: art_20260714_deepseek-wishlist-2026-07-14_5acf75
    rel: cites
  - target: art_20260714_deepseek-r1-delta-door-design-half-blind_540056
    rel: cites
  - target: art_20260714_r1-delta-door-claude-design-half-blind-2_94984b
    rel: cites
  - target: art_20260714_r1-delta-door-reconciliation-build-spec_13427c
    rel: cites
created: "2026-07-14T09:40:19"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260714_design-brief-r1-delta-door-t052-full-fen_a36fa9 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Design brief — R1 Delta Door (T052; full fence, M1-BRIEF format)

Tier: FULL FENCE per M1-LITE gate 1 (new coordination-adjacent capability touching the
boot/wake contract both agents live on; blind halves + reconciliation).

## (1) CHARTER
DESIGN fence: architect the delta door — the both-seats #1 wishlist convergence (S1,
"continuity via deltas") — so each agent's opening move stops being archaeology.

## (2) INPUTS
DESIGN ONLY — no delta implementation exists; cite only these artifacts and existing
seams (fabricated code paths against unbuilt surfaces = automatic invalidation, M1-PV):
- research/reviewed/wishlist-synthesis-2026-07-14.md (S1 + R1 sections — the mandate)
- research/reviewed/claude-wishlist-2026-07-14.md (A3 resume-pack) +
  research/reviewed/deepseek-wishlist-2026-07-14.md (a5/a3 what-changed + resume tokens)
- Existing seams a design may compose (cite as they exist today): the boot assembly
  (agent_cli boot / Context pillar), task ledger (core/coord/task_ledger), write-once
  notes (supersession by title), promoted salient messages + acks, bus cursors
  (core/comm/bus.py — shared + the NEW lane cursor hash), git history, the Store
  (namespaced key-value with CAS), turn_metrics.
- docs/method-baseline-2026-07.md (M1-CF vocabulary for your verdicts)

## (3) RULES OF ENGAGEMENT
Full M1: BOTH agents answer the same question from separate contexts, BLIND — neither
reads the other's half until its own is committed. REFUTE-FIRST on your own candidate
mechanisms (name what breaks each). Every design decision carries an M1-CF tag. Claude
reconciles per the standard triage (CONVERGED / COMPLEMENTARY / DIVERGENT), M1-PV pass
first. Deliverables:
- deepseek half -> research/reviewed/deepseek-r1-delta-door-half-2026-07-14.md (guarded write)
- claude half   -> research/reviewed/claude-r1-delta-door-half-2026-07-14.md
- reconciliation -> research/reviewed/r1-delta-door-reconciliation-2026-07-14.md (build spec)

## (4) THE QUESTION
Design the delta door: ONE mechanism serving "what changed since I was last here" for
every agent. Decide, minimum:
(a) the HIGH-WATER MARK: exactly which positions it records (last-seen commit, ledger
    revision, bus cursor(s) — shared and/or lane, note versions, anything else), where
    it LIVES (Store namespace? note? lane-cursor-style hash?), and when it advances
    (boot? wrap? per-turn?);
(b) the RENDER: what `delta <agent>` actually shows for each moved source (git range ->
    what summary; ledger -> which transitions; notes -> supersessions; bus -> what) and
    its size budget (packet law: declared budget, refuse-loud, pull pointers);
(c) BOOT/WAKE integration: which boot sections the delta REPLACES (the boot shrinks) vs
    supplements; whether the wake report gains a delta line (the wake sharpens);
(d) COST bound: the delta computation must be cheaper than the archaeology it replaces
    (frugality directive — name the bound and how it is measured);
(e) FAILURE modes: stale mark, mark loss, twin sessions of one agent, a source that
    moved backwards (rebase/rollback) — what each does to the render (refuse-loud vs
    degrade-honest).

## (5) OUTPUT CONTRACT
Markdown design half at your deliverable path (guarded write). Per-decision M1-CF tags.
Structure free beyond that. Bus reply: POINTER ONLY (path + one-line stance) — the
report lives in the file, never chunked over the bus.
