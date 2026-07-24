---
akashic_id: art_20260724_t105-agentic-quality-improvement-map_fe7c82
akashic_sha: abbe44c6d612
schema_version: 1
status: current
type: design
arc: sota-quality
date: 2026-07-24
title: t105-agentic-quality-improvement-map
gist: "T105 reconciled: claim-receipt verifier = the round's convergent tool (12/30 defects traced), skeleton-first boot, stance anchor+measure, order-as-lever; Q1-Q3 gated slices"
visibility: fleet
body_type: markdown
seats: [claude, deepseek, kimi]
category: [frontier, method, recall]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_sota-agentic-quality-research-round_8eb04e
    rel: discusses
  - target: art_20260724_sota-quality-claude-half-harness-steerin_f49a40
    rel: discusses
  - target: art_20260724_sota-quality-deepseek-half-builder-lens_c96889
    rel: discusses
  - target: art_20260724_sota-quality-kimi-half-audit-lens_6a0314
    rel: discusses
created: "2026-07-24T09:23:27"
updated: "2026-07-24T09:23:27"
---
<!-- GENERATED PROJECTION of art_20260724_t105-agentic-quality-improvement-map_fe7c82 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t105-agentic-quality-improvement-map

T105 RECONCILED — THE AGENTIC-QUALITY IMPROVEMENT MAP (three independent halves: claude web-grounded harness/steering lens · deepseek training-prior builder lens · kimi training-prior audit lens, evidence-anchored in OUR failure ledger). Daniel's charter verbatim: "research what the state of the art ways are of extracting the most fidelity and quality work out of agentic ai's. with that knowledge we can improve our steers and context / stance recall."

## HEADLINE CONVERGENCES (independent arrivals, ranked)

C1 — **THE CLAIM-RECEIPT VERIFIER (the round's strongest signal).** deepseek's #1 tool wish (verify_my_answer: auto-check files/tests a reply references before it ships) and kimi's #3 wish (ship.py extracts every commit claim and refuses without a matching live receipt) are THE SAME TOOL from opposite lenses — generation-side and gate-side of one mechanism. It already has two live receipts from our own week: premature_green_claim_gating and the checker charter's exits-0 claim. kimi's ledger archaeology: ~12 of ~30 classified defects trace to claim-verified-before-evidence-resolved. This mechanizes the single largest defect class we have.

C2 — **SKELETON-FIRST CONTEXT (three voices).** The 2026 context-engineering consensus (my web half: context quality beats prompt quality; minimal-first) = deepseek's calibrated answer (#5: boot fold's truncated lesson bodies are "tier-2 pretending to be tier-1" — subtly misleading, missing the contraindication clause) = the field-survey atom's six-source convergence. Fix shape: boot renders ONE LINE per lesson (title + trigger + status); knowledge_expand fetches full bodies on demand; boot shrinks ~6k -> ~1.5k tokens.

C3 — **STANCE: ANCHOR AT TOP, MEASURE THE DRIFT (two voices + the field).** deepseek #8 (stance block verbatim-stable at the very top — highest attention) + my web finding (30%+ stance self-consistency decay at 8-12 turns even with context intact; the field's mitigations = exactly our stance blocks, plus MEASUREMENT we lack). Daniel's "stance recall" concern, named and instrumented.

C4 — **CONTEXT ORDER IS A LEVER (deepseek #1 + my lost-in-the-middle finding).** Directive LAST before task (recency wins), stale lessons decay-labeled and sunk, recall-at injection after the tool contract. Zero token cost — pure reorder.

C5 — **STRUCTURED TRIGGERS BEAT PROSE MATCHING (deepseek #2 + my S6 + T094's direction).** Lessons gain a structured trigger field (symptom/file/command) so recall ranks deterministically instead of TF-IDF guessing.

## THE GATED SLICES (Daniel's word opens each)

Q1 (build-first tier — convergence x cheap x receipts-in-hand):
  Q1a claim-receipt verifier v1: ship.py gate extracts GREEN/DONE claims from the commit message, demands a matching live-run receipt (exit code or output path); refuse-loud. (kimi w3 + deepseek w1; ~150 lines; its own founding receipts already exist.)
  Q1b boot skeleton-first: one-line lesson skeleton + knowledge_expand door; kill truncated bodies. (deepseek's calibrated answer; touches build_autoboot_context + one new ToolBox/MCP verb.)
  Q1c boot order pass: stance block verbatim at top; CURRENT DIRECTIVE last-before-task; decay-stale lessons labeled + sunk. (Pure reorder + ~1 rule/lesson.)

Q2 (hardening tier):
  Q2a lesson trigger-condition field (schema addition; T094 absorbs).
  Q2b kata-runner (kimi w1): belt entries re-run live, stale VERIFIED stamps auto-detected (~200 lines; the audit domain's teeth).
  Q2c adversarial-pin-per-property law: method-baseline amendment -- every pin suite carries >=1 make-it-fail pin (kimi #3; the newborn-gauntlet generalized).
  Q2d stance-drift probe: kata scorer scores stance adherence per session window; stats trends it (my S5; gives Daniel the drift curve).

Q3 (opportunistic tier): few-shot charter examples (deepseek #7) · tool-error teaching-audit (~15-20 paths, deepseek #6) · think-budget tiers per task kind (deepseek #3) · compaction verb (my S1) · fence-matrix dashboard (kimi w2) · brief scaffold (my S3).

## STANDING AFFIRMATIONS (no build needed)
- T071-R1 relevance budget: designed, claimed, now frontier-affirmed twice over — the map's strongest UNBUILT asset; recommend it rides Q1b's build.
- Method-baseline M3/M5: kimi's archaeology shows the doctrine is right and the gap is ENFORCEMENT — Q1a + Q2c are the teeth.
- deepseek's session_diff wish = the T052 delta door, WHICH EXISTS — a discovery/ergonomics gap, not a build gap; fold into boot's door-advertisement line.

## HONESTY LEDGER
Seat halves are training-prior INFER (both self-labeled, zero invented citations; kimi's ledger-anchored claims VERIFIED against our own record). My half is search-grounded, not deep-read. The numeric field claims (30% drift, 40% pilot failure) are single-source. Nothing here ships without Daniel's word; every Q1-Q3 slice lands with pre-registered RED pins per its own C1 finding — this map eats its own cooking.
