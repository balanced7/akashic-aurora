---
akashic_id: art_20260714_design-brief-r5-cost-telemetry-per-slice_30947f
akashic_sha: 34f2bab84c06
status: current
type: design
date: 2026-07-14
title: "Design brief — R5 Cost Telemetry per slice (T056; full fence, M1-BRIEF format)"
gist: "Tier: FULL FENCE per M1-LITE gate 1a — the join stamps the TASK LEDGER's write path (a coordination primitive); blind halves + reconciliatio"
tenant: solo
visibility: fleet
seats: []
category: [coordination, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_wishlist-synthesis-both-seats-one-map-20_90759f
    rel: cites
  - target: art_20260714_deepseek-r5-cost-telemetry-design-half-b_85a3eb
    rel: cites
  - target: art_20260714_r5-cost-telemetry-claude-design-half-bli_48d395
    rel: cites
  - target: art_20260714_r5-cost-telemetry-reconciliation-build-s_d7f3a8
    rel: cites
created: "2026-07-14T10:44:26"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260714_design-brief-r5-cost-telemetry-per-slice_30947f -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Design brief — R5 Cost Telemetry per slice (T056; full fence, M1-BRIEF format)

Tier: FULL FENCE per M1-LITE gate 1a — the join stamps the TASK LEDGER's write path
(a coordination primitive); blind halves + reconciliation. (The render half alone would
be fence-lite; the stamp half drags the whole slice up — under-fencing is never the
fall-through.)

## (1) CHARTER
DESIGN fence: architect the cost-telemetry join — turn_metrics into the ledger render —
so every slice's price is visible ("per-arc ROI for Daniel; the frugality directive made
measurable", wishlist S4).

## (2) INPUTS
DESIGN ONLY — no join code exists; cite only these artifacts and existing seams:
- research/reviewed/wishlist-synthesis-2026-07-14.md (S4 + R5 sections)
- core/comm/turn_metrics.py (what is actually counted today — read it, name what exists;
  fabricating counters that do not exist = M1-PV invalidation)
- core/coord/task_ledger.py (transition machinery, format_state render, the seq)
- The shipped hop counter (T050 Q4) and the delta door's cost-metric ruling (D5:
  tool-calls-avoided as an outcome metric) for vocabulary consistency
- docs/method-baseline-2026-07.md (M1-CF tags; M8 honest bounds)

## (3) RULES OF ENGAGEMENT
Full M1: blind halves, REFUTE-FIRST your own candidates, M1-CF tag per decision.
claude reconciles (M1-PV first). Deliverables:
- deepseek half -> research/reviewed/deepseek-r5-cost-telemetry-half-2026-07-14.md (guarded write)
- claude half   -> research/reviewed/claude-r5-cost-telemetry-half-2026-07-14.md
- reconciliation -> research/reviewed/r5-cost-telemetry-reconciliation-2026-07-14.md

## (4) THE QUESTION
Design the cost join. Decide, minimum:
(a) WHAT gets stamped: which turn_metrics counters (and/or other cheap observables:
    commits in the task's window? fence rounds? bus messages?) constitute a slice's
    "cost" — honest about what the counters can and cannot attribute (two agents work
    concurrent tasks: how is cost attributed, or is per-task attribution refused loudly
    in favor of per-WINDOW cost?);
(b) WHEN stamps land: which lifecycle transitions snapshot the counters (claim? start?
    done?) and where they live (fields on the task record? ledger events? both?);
(c) the RENDER: what `task list` / format_state shows per task (and what the wrap-time
    arc scorecard gains); size discipline per the packet law;
(d) BACKFILL: tasks closed before this ships render what? (strangler: no fabricated
    costs — absent stamps render absent);
(e) FAILURE modes: counter reset/rollover mid-task, a task spanning runner restarts,
    Redis loss of metrics state — refuse-loud vs degrade-honest per case;
(f) the GOODHART guard: costs visible per-slice invites optimizing the NUMBER — name
    the guard (T034 lineage: never codify pace; the metric is for ROI reading, not
    agent scoring).

## (5) OUTPUT CONTRACT
Markdown design half at your deliverable path (guarded write). Per-decision M1-CF tags.
Bus reply: POINTER ONLY (path + one-line stance).
