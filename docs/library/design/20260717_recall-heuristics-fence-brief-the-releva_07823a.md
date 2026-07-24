---
akashic_id: art_20260717_recall-heuristics-fence-brief-the-releva_07823a
akashic_sha: a5afb31ec6b1
status: draft
type: design
date: 2026-07-17
title: Recall-heuristics fence brief — the relevance plane + the heuristic lifecycle (2026-07-17)
gist: "Class: research charter (T031-hook-1 style: the arc's artifacts cite this brief) ## Directive (Daniel, live chat 2026-07-17, verbatim) > \"an"
tenant: solo
visibility: fleet
seats: []
category: [recall, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_recall-vnext-closing-the-four-loops-2026_b93539
    rel: cites
  - target: art_20260717_claude-opening-position-recall-heuristic_4540cb
    rel: cites
  - target: art_20260717_recall-heuristics-reconciliation-heurist_72ca2b
    rel: cites
created: "2026-07-17T21:17:16"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260717_recall-heuristics-fence-brief-the-releva_07823a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Recall-heuristics fence brief — the relevance plane + the heuristic lifecycle (2026-07-17)

Class: research charter (T031-hook-1 style: the arc's artifacts cite this brief)

## Directive (Daniel, live chat 2026-07-17, verbatim)

> "analyze how we can improve our recall heuristics and performance in order to improve
> the effectiveness of recall. I want us to be able to refine our heuristics to have them
> grow in capability. research antivirus heuristics and web search heuristics to see what
> we can absorb and integrate, do this collaboratively with a fully enabled deepseek"

Decomposed: (1) recall effectiveness — better heuristics AND better performance;
(2) heuristics that GROW in capability — an adaptive/self-improving heuristic layer,
not another one-shot calibration; (3) absorb proven mechanisms from two mature
heuristic industries — antivirus engines and web search ranking; (4) claude+deepseek
live co-design, deepseek at his full grant.

## Scope — what this arc owns

THE RELEVANCE PLANE + THE HEURISTIC LIFECYCLE: how recall decides WHAT matches
(features, rules, ranking), and how those rules are authored, evaluated, promoted,
demoted, and retired over time so the system's matching improves from its own
history. Performance (latency/cost per recall decision) is in scope where it shapes
the ladder (cheap→expensive staging, caching, bounded work).

## Scope — what this arc does NOT rebuild (compose, don't compete)

- **recall-vNext (docs/recall-vnext-2026-07.md, T011, SHIPPED):** the four closed
  loops (curation/bench, trigger-aware relevance, credit aperture, acquisition) are
  the FLOOR this arc stands on. Its deferred list (trigger CONTRACTS v2, consolidation
  merge, cross-agent confirmed tier, injection token budget) is this arc's inheritance.
- **recall-networking reconciliation (research/reviewed/recall-networking-
  reconciliation-2026-07-12.md, PARKED at Daniel's gate):** the transport plane
  (N0 ECN wire, N1 rwnd, N2 AIMD, N3 FIB, N4 pay-rent, N5-N7). That record ruled
  "transport first, not a smarter ranker first" for the CONGESTION disease. This arc
  is the ranker/lifecycle layer that record deferred — it consumes N0's marks and C9's
  per-rule counters when they land, and must not fork their designs.
- **T060 moonshot network spine:** the PACKET plane (bus routing). Different plane.
- **T092 reasoning spine:** upstream capture corpus. R-d (capture asymmetry,
  adjudicated 2026-07-17: ToolBox-first + ALL_SEATS_CAPTURING pre-recall gate +
  liveness floor) is a standing pattern this arc generalizes: corpus-completeness
  gates recall eligibility (the AV "definition freshness" analog).
- **capture-for-recall note (ADR_0717202440_eeb5ce4d):** lesson FORM findings (fixed)
  and the OPEN routed requirement: recall_at needs CONTENT-CLASS matching (file →
  lesson class), not just path-token match. That requirement lands HERE.

## Evidence exhibits (live, this session 2026-07-17, before any design)

- E1 (miss, boot): boot --task "recall heuristics evolution: absorb antivirus +
  web-search ranking patterns..." surfaced 3 Windows process-lifecycle lessons
  (CTRL_BREAK, job objects) — zero relevance to the task string.
- E2 (miss, hook): recall-at-action fired the CTRL_BREAK lesson on a `git status`
  PowerShell call.
- E3 (hit, hook): recall-at-action fired bifrost_send_text_ordering +
  bifrost_send_supported_flags (useful 2x votes) on a `bifrost-send --help` call —
  exactly right, exactly when needed.
- E4 (measured, capture note): recall_at(path=scripts/run_job.py) surfaces only the
  advisory lock — NONE of the 9+ process-lifecycle/review-method lessons rank as
  relevant to the exact file they exist to guard. Tested before AND after form fix.
- E5 (funnel, cumulative): 27 active lessons | 1330 surfaced | useful=46 noise=9 |
  helped=34 | value 6.0% (lineage: 1.05% pre-vNext → 4.5% at networking fence → 6.0%).
- The gradient E1-E4 draws: lexical token overlap works in-domain (E3), fails
  cross-domain and at class boundaries (E1/E2/E4). The system has ONE fixed matching
  heuristic; nothing routes a context to a lesson CLASS, and no rule is ever
  born, tested, or retired. Value 6.0% means 94 of every 100 surfacings still buy
  nothing (E5).

## Protocol (collaborative-means-iterative; deepseek-fence-every-stage)

1. Round 0 (parallel): claude — code census + frontier research (AV + web search,
   external evidence persisted to research/reviewed/frontier-*.md); deepseek — own
   read of the live relevance machinery + own opening absorb-list + prepared counters.
2. Claude opening position: research/reviewed/claude-recall-heuristics-opening-2026-07-17.md.
3. Rounds on the live bus (handoff/reply kinds): hard counters, convergence-or-ruling
   per divergence, receipts cited (file:line, funnel numbers, replay results).
4. Co-authored reconciliation: research/reviewed/recall-heuristics-reconciliation-2026-07-17.md
   — absorb-map (AV→Aurora, search→Aurora), lifecycle architecture, sliced roster with
   pre-registered acceptance gates (method-baseline M-bars), open-for-Daniel items.
5. deepseek-review gate on the reconciliation before it parks at Daniel's approval gate.
6. deepseek's full reports persist verbatim (research/reviewed/deepseek-recall-heuristics-*.md).

Design-only arc: no engine code changes until Daniel approves the reconciled roster.
Method contracts honored: docs/pillar-analysis-method.md (triangulate → loop-altitude
diagnosis → evidence-disciplined fixes) and docs/method-baseline-2026-07.md.

## The one-sentence thesis this arc must confirm or break (pillar method step 7)

vNext gave recall ONE good static heuristic and closed the feedback loops around the
LESSONS; nothing closes a loop around the HEURISTICS — rules cannot be born, cannot
carry their own precision record, and cannot die, so the system's matching cannot
outgrow its first calibration.
