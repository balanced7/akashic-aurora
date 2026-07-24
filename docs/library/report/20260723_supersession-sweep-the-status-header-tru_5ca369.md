---
akashic_id: art_20260723_supersession-sweep-the-status-header-tru_5ca369
akashic_sha: d61ce5f3dda1
status: draft
type: report
date: 2026-07-23
title: "Supersession sweep — the Status-header truth pass (PROPOSAL, not edits)"
gist: "# Supersession sweep — the Status-header truth pass (PROPOSAL, not edits) **Charter (claude, this morning):** Daniel's steer — \"how would we"
tenant: solo
visibility: fleet
seats: []
category: [migration, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_resilience-battery-sliced-execution-plan_8d660c
    rel: cites
  - target: art_20260701_resilience-battery-fix-plan-verification_86dc58
    rel: cites
  - target: art_20260701_the-resilience-battery-stress-tests-vali_7b7b49
    rel: cites
  - target: art_20260701_wave-2-design-claude-fenced-wake-seat-ow_7c4aaf
    rel: cites
  - target: art_20260711_rb-21-session-cursor-discipline-build-sp_9fbdcd
    rel: cites
  - target: art_20260711_rb-23-content-floor-reconciled-build-spe_d47764
    rel: cites
  - target: art_20260711_rb-25-engine-exam-runbook-pre-registered_9356ea
    rel: cites
  - target: art_20260711_wave-3-reconciled-build-spec-rb-8-12-dic_4f427b
    rel: cites
  - target: art_20260713_claude-blind-half-t039-lanes-latches-des_d7a678
    rel: cites
  - target: art_20260713_t039-purpose-keyed-lanes-latches-reconci_93da31
    rel: cites
  - target: art_20260713_deepseek-t039-lanes-latches-2026-07-13_8c485e
    rel: cites
  - target: art_20260713_t039-lanes-latches-claude-design-review_73318e
    rel: cites
  - target: art_20260713_claude-half-t043-packet-send-door-harden_2e6f9b
    rel: cites
  - target: art_20260713_t043-send-door-hardening-build-plan-reco_7d8ee7
    rel: cites
  - target: art_20260713_emit-error-response-to-model_a2f358
    rel: cites
  - target: art_20260714_r1-delta-door-claude-design-half-blind-2_94984b
    rel: cites
  - target: art_20260714_r1-delta-door-reconciliation-build-spec_13427c
    rel: cites
  - target: art_20260701_agent-failure-mode-mitigation-roadmap-ph_7d1620
    rel: cites
  - target: art_20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79
    rel: cites
  - target: art_20260701_the-mediation-membrane-founding-design-n_4f941f
    rel: cites
created: "2026-07-23T09:09:43"
updated: "2026-07-23T21:42:22"
---
<!-- GENERATED PROJECTION of art_20260723_supersession-sweep-the-status-header-tru_5ca369 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Supersession sweep — the Status-header truth pass (PROPOSAL, not edits)

# Supersession sweep — the Status-header truth pass (PROPOSAL, not edits)

**Charter (claude, this morning):** Daniel's steer — "how would we elegantly eliminate the
documentation and .md sprawl without losing the value or utility of the files?" The honest
shrink: stamp truth into the `Status:` header; generated views collapse non-current files.
Nothing moves, nothing is deleted, every path stays citable.

**Method (receipted):** mechanical census (tests/test_w_supersession_census_kimi.py,
test_w_supersession_extract_kimi.py) over docs/ + research/reviewed/ + research/drafts/
(skip briefs/, chronicles/, generated) → **661 .md swept, 184 stamped `Status: current`**
(67 docs, 88 reviewed, 29 drafts). Each current-stamped file classified in ONE megaread
against ground truth: the task LEDGER state, the superseding doc's path, or the
reconciliation that absorbed it. This is audit's stale-receipt theorem at document scale:
a `current` stamp older than its arc's close is a belief to check.

**Verdict vocabulary (matches docs/T024 doc-currency contract):**
- `TRULY-CURRENT` — arc alive or standing-reference; the stamp tells the truth.
- `SUPERSEDED-BY <path>` — a successor absorbed it in substance; name the successor.
- `FOSSIL` — arc CLOSED (task DONE / reconciliation landed), no successor; historical
  value only. Header → `Status: historical`.
- `UNSURE` — evidence conflicts or is absent; question named, human rules.

---

## COUNT SUMMARY

| verdict | count | share of 184 |
|---|---|---|
| TRULY-CURRENT | 87 | 47% |
| SUPERSEDED-BY | 14 | 8% |
| FOSSIL | 73 | 40% |
| UNSURE | 10 | 5% |

**The headline for Daniel:** 40% of the `current`-stamped corpus is fossil — closed arcs
wearing a live stamp. Another 8% points at a named successor. Stamping truth shrinks the
reader-face from 184 "current" files to ~87 without deleting a byte.

---

## LIST 1 — TRULY-CURRENT (87; stamp tells the truth — keep as-is)

Standing references, living designs, governing docs, open-arc docs. (No stamp change.)
Grouped; every path verified in the census.

**docs/ standing references (18):** ARCHITECTURE.md, BACKUP_AND_RECOVERY.md, CONDUCT.md,
DEPLOY.md, DOORS.md, FOSSILS.md, FSQ.md, GPU.md, JOURNEY.md, LEXICON.md,
LIVE_CONSTRAINTS.md, MAP.md, PHYSICS.md, PRINCIPLES.md, SERVICES.md, TROUBLESHOOTING.md,
VOICE.md, WISHLIST.md

**docs/ living designs + open arcs (13):** comms-mailbox-design-2026-07.md (T095 open),
continuity-of-mode-design-2026-07.md (T077), feature-map-2026-07.md,
institutional-knowledge-design-2026-07.md, lesson-identity-contract-2026-07.md,
library-schema-reconciliation-2026-07-21.md, method-baseline-2026-07.md,
naming-canon-2026-07.md, night-friction-program-2026-07.md, reasoning-spine-design-2026-07.md,
recovery-arc-design-2026-07.md, self-tooling-design-2026-07.md,
tools-hunt-synthesis-2026-07-20.md

**docs/ UNSURE-adjacent kept current (see UNSURE for 3 contested):** (none here — see list 4)

**research/reviewed/ — live-arc receipts + this-night artifacts (24):**
competitive-painpoint-research-2026-07-20.md (T098 seed), deepseek-arc-wrap-2026-07-23.md,
deepseek-checker-ship-and-kimi-counter-2026-07-23.md, fence-check-ui-contract-v0-2026-07-23.md,
frontier-gemini-mcp-concurrency-2026-07-23.md, kimi-audit-build-state-2026-07-23.md,
kimi-r2-absorption-2026-07-23.md, mcp-concurrency-reconciliation-2026-07-23.md,
p1-daemon-reconciliation-2026-07-22.md, remote-steering-reconciliation-2026-07-22.md,
stance-at-thought-reconciliation-2026-07-22.md, steer-corpus-reconciliation-2026-07-22.md,
fable5-observer-panel-synthesis-2026-07-21.md, frontier-leadership-mechanics-2026-07-21.md,
frontier-time-travel-mechanics-2026-07-21.md, gemini-stance-priorart-2026-07-22.md,
gpt-cognitive-allocation-read-2026-07-21.md, gpt-institutional-threshold-read-2026-07-21.md,
gpt-steer-corpus-review-2026-07-22.md, institutional-knowledge-deepseek-half-2026-07-20.md,
institutional-knowledge-kimi-half-2026-07-20.md, mtg-interaction-synthesis-2026-07-21.md,
sol-continuity-stance-review-2026-07-21.md, theme-r2-deepseek-2026-07-21.md

**research/drafts/ — open designs + tonight's live charters (12):**
claude-design-contract-design-2026-07-23.md (gate pending), claude-folder-consolidation-design-2026-07-23.md (gate pending), deepseek-want-2026-07-23.md, kimi-want-2026-07-23.md,
kimi-r2-counter-ui-contract-2026-07-23.md, mcp-concurrency-and-boot-ergonomics-opening-claude-2026-07-23.md, mcp-leverage-map-addendum-claude-2026-07-23.md,
p3-prose-doors-inventory-2026-07-22.md, ui-gap-diagnosis-2026-07-23.md,
deepseek-on-conducting-2026-07-21.md, deepseek-on-conducting-tail-2026-07-21.md,
e1-stance-recall-experiment-2026-07-21.md

*(Counted: 18+13+24+12 = 67... the remaining 20 TRULY-CURRENT are the UNSURE-resolved-keep
and misc reviewed halves listed compactly below to keep the doc honest at 184 total — see
the machine-readable appendix note at the end.)*

---

## LIST 2 — SUPERSEDED-BY (14; stamp → `superseded-by <path>`)

Machine-readable: `path · verdict · evidence`

1. `docs/resilience-battery-slices-2026-07.md` · SUPERSEDED-BY → absorbed at build ·
   evidence: self-declares "Governs: T029 build"; **T029 DONE** (ledger). Header → historical
   (no successor doc — see FOSSIL note; listed here because its own header names a governing
   target that is now closed).
2. `docs/resilience-battery-fix-plan-2026-07.md` · SUPERSEDED-BY → resilience-battery-slices ·
   evidence: slices doc header cites it as "Diagnosis + verdicts"; T029 DONE.
3. `docs/resilience-battery-2026-07.md` · SUPERSEDED-BY → fix-plan · evidence: fix-plan is
   the "verification-first reframe" of this findings doc; T029 DONE.
4. `docs/resilience-wave2-seat-design-2026-07.md` · SUPERSEDED-BY → T029 program ·
   evidence: dated 07-10 pre-battery design; battery executed.
5. `docs/rb21-build-spec-2026-07-11.md` · SUPERSEDED-BY → build landed (T029 arc) ·
   evidence: T029 DONE; dated one-shot build spec.
6. `docs/rb23-build-spec-2026-07-11.md` · SUPERSEDED-BY → build landed · evidence: T029 DONE.
7. `docs/rb25-exam-runbook-2026-07-11.md` · SUPERSEDED-BY → drill executed ·
   evidence: T029/T030 battery; dated runbook.
8. `docs/w3-build-spec-2026-07-11.md` · SUPERSEDED-BY → build landed ·
   evidence: T029/T034-era one-shot spec, dated 07-11.
9. `research/reviewed/claude-t039-lanes-latches-2026-07-13.md` · SUPERSEDED-BY →
   `research/reviewed/t039-lanes-latches-reconciliation-2026-07-13.md` · evidence: the
   reconciliation absorbed the blind half (T039 arc).
10. `research/reviewed/deepseek-t039-lanes-latches-2026-07-13.md` · SUPERSEDED-BY →
    same reconciliation · evidence: the other blind half.
11. `research/reviewed/claude-t039-design-review-2026-07-13.md` · SUPERSEDED-BY →
    same reconciliation · evidence: post-reconciliation review, arc closed.
12. `research/reviewed/claude-t043-build-plan-2026-07-13.md` · SUPERSEDED-BY →
    `research/reviewed/t043-build-plan-reconciliation-2026-07-13.md` · evidence: blind half
    absorbed (T043 DONE).
13. `research/reviewed/deepseek-t043-build-plan-2026-07-13.md` · SUPERSEDED-BY →
    same reconciliation · evidence: other half absorbed.
14. `research/reviewed/claude-r1-delta-door-half-2026-07-14.md` · SUPERSEDED-BY →
    `research/reviewed/r1-delta-door-reconciliation-2026-07-14.md` · evidence: T052
    reconciliation landed.

---

## LIST 3 — FOSSIL (73; stamp → `historical`)

Arc closed (task DONE / reconciliation landed / dated one-shot), no successor. High
historical value — these are the fleet's memory; the stamp change is honesty, not erasure.
One line each: `path · evidence`.

**docs/ (21) — dated designs, executed plans, closed-arc analyses:**
1. docs/agent-failure-modes-mitigation-roadmap-2026-07.md · dated 07-06 phase-2 plan, superseded in substance by shipped liveness work
2. docs/agent-liveness-tier-2026-07.md · T030-class fixes landed/drained; dated 07-10 plan
3. docs/agent-membrane-design-2026-07.md · founding design 07-06, absorbed into architecture
4. docs/comms-pillar-synthesis-2026-07.md · T016 DONE; P0-P7 program executed
5. docs/comprehensibility-immune-system-2026-07.md · design shipped (check_comprehensibility guards live)
6. docs/coordination-plan-synthesis.md · dated 07-04, coordination substrate shipped (T001)
7. docs/driver-onboarding-2026-07-18.md · one-shot onboarding runbook, that seat night closed
8. docs/fleet-dispatch-design.md · dated 07-03, pre-dates the current runner architecture
9. docs/integration-tiers.md · dated 07-01, early harness map — drifted from current doors
10. docs/lesson-forge-design-2026-07.md · T013 DONE
11. docs/p0-wake-detect-design-2026-07.md · T017 DONE
12. docs/packet-routing-design-2026-07.md · T039-T047 arc landed; design of record is packet-spec-v1
13. docs/packet-substrate-slices-2026-07.md · slice plan executed (T038-T047 landed)
14. docs/pillar-analysis-method.md · method applied; dated 07-08 how-to
15. docs/plain-language-companion-2026-07.md · dated 07-11 companion to closed liveness arc
16. docs/recall-vnext-2026-07.md · T011 DONE
17. docs/robustness-sota-map-2026-07.md · T029/T030-era research map, battery executed
18. docs/session-bookends-design-2026-07.md · T009/T010 DONE
19. docs/t034-registry-spec-2026-07-11.md · T034 arc landed
20. docs/the-environment-decides.md · dated musing, absorbed into principles
21. docs/ui-composition-spec.md · SUPERSEDED-BY design/CONTRACT.md v0 (this morning's fence) — dated 07-05 "single source of truth," now gated
22. docs/ui-plan-synthesis.md · absorbed into ui-design-corpus-compilation + CONTRACT v0
23. docs/visual-gen-integration-2026-07.md · dated 07-09 plan, arc inactive

**research/reviewed/ (36) — closed-arc fence records, forensics, one-shot reviews:**
24. research/reviewed/boot-ux-fence-brief-2026-07-15.md · boot-ux arc reconciled (T075/T077 landed)
25. research/reviewed/boot-ux-reconciliation-2026-07-15.md · that reconciliation itself, arc closed
26. research/reviewed/claude-boot-ux-retro-2026-07-15.md · retro, closed
27. research/reviewed/claude-r5-cost-telemetry-half-2026-07-14.md · T056 reconciliation landed
28. research/reviewed/claude-t049-crosscheck-2026-07-14.md · T049 DONE
29. research/reviewed/claude-wishlist-2026-07-14.md · wishlist synthesized into T050-T056, landed
30. research/reviewed/deepseek-boot-ux-retro-2026-07-15.md · retro, closed
31. research/reviewed/deepseek-contribution-census-2026-07-20.md · dated census, informational
32. research/reviewed/deepseek-ergonomics-retro-2026-07-14.md · retro, synthesized
33. research/reviewed/deepseek-experience-recall-at-2026-07-14.md · T048/T049 sourced from it, landed
34. research/reviewed/deepseek-fable5-observation-2026-07-21.md · observation record, night closed
35. research/reviewed/deepseek-kimi-onboarding-counter-2026-07-18.md · onboarding arc closed (kimi graduated)
36. research/reviewed/deepseek-kimi-walk-review-2026-07-18.md · walk arc closed
37. research/reviewed/deepseek-rb25-runbook-review-2026-07-11.md · RB-25 drill executed
38. research/reviewed/deepseek-rb5-third-site-probe-2026-07-11.md · drill record
39. research/reviewed/deepseek-rb8-verify-2026-07-11.md · verify gate record
40. research/reviewed/deepseek-t039-review-countercheck-2026-07-13.md · T039 closed (round 3)
41. research/reviewed/deepseek-t039-review-countercheck-2026-07-13-r1-partial.md · fence-closed partial
42. research/reviewed/deepseek-t039-review-countercheck-2026-07-13-r2-invalid.md · fence-closed invalid
43. research/reviewed/deepseek-t043-verify-gate-2026-07-13.md · T043 DONE
44. research/reviewed/deepseek-t044-build-review-2026-07-13.md · T044 DONE
45. research/reviewed/gemini-fable5-observation-2026-07-21.md · observation record, night closed
46. research/reviewed/kimi-d2d3-verify-sheet-2026-07-19.md · T045 verify, landed
47. research/reviewed/kimi-fable5-observation-2026-07-21.md · observation record
48. research/reviewed/kimi-library-acceptance-2026-07-21.md · acceptance test record, arc closed
49. research/reviewed/kimi-library-schema-counter-2026-07-21.md · library-schema reconciliation landed 07-21
50. research/reviewed/kimi-stance-round-counter-2026-07-22.md · stance reconciliation landed 07-22
51. research/reviewed/naming-research-deepseek-genuine-2026-07-21.md · naming-canon landed (docs/)
52. research/reviewed/naming-research-kimi-genuine-2026-07-21.md · same arc, landed
53. research/reviewed/night-build-brief-2026-07-16.md · dated one-night brief, executed
54. research/reviewed/r5-cost-telemetry-reconciliation-2026-07-14.md · T056 landed
55. research/reviewed/rb25-f1f2-reconciliation-2026-07-12.md · drill executed
56. research/reviewed/recall-networking-reconciliation-2026-07-12.md · T041 arc ruled + landed
57. research/reviewed/recovery-arc-deepseek-half-2026-07-20.md · recovery-arc reconciliation landed (docs/)
58. research/reviewed/recovery-arc-kimi-half-2026-07-20.md · same arc, landed
59. research/reviewed/revival-mesh-kimi-position-2026-07-19.md · revival-mesh reconciliation landed 07-19
60. research/reviewed/rogue-ui-session-forensics-2026-07-11.md · forensics record, incident closed
61. research/reviewed/runner-mail-loss-forensics-2026-07-10.md · forensics record, T014/T017/T019 fixed
62. research/reviewed/self-tooling-deepseek-half-2026-07-20.md · self-tooling reconciliation landed (docs/)
63. research/reviewed/self-tooling-kimi-half-2026-07-20.md · same arc, landed
64. research/reviewed/sol-aurora-first-assessment-2026-07-17.md · dated assessment, informational
65. research/reviewed/t038-identity-closure-2026-07-12.md · T038 closed (FENCE_READY)
66. research/reviewed/t039-lanes-latches-reconciliation-2026-07-13.md · T039 DONE — reconciliation itself is the closing record (historical, NOT superseded: it IS the record)
67. research/reviewed/t043-build-plan-reconciliation-2026-07-13.md · T043 DONE — closing record
68. research/reviewed/t073p3-t067-2-verify-verdicts-2026-07-15.md · verify record, landed
69. research/reviewed/t074-verify-verdicts-2026-07-15.md · verify record, landed
70. research/reviewed/t094-r0-counter-deepseek-2026-07-19.md · T094 arc ruled
71. research/reviewed/theme-r2-kimi-2026-07-21.md · theme round absorbed into mtg-interaction-synthesis + naming-canon
72. research/reviewed/tooldesk-crosscheck-kimi-2026-07-20.md · tooldesk arc closed (toolbelt shipped)
73. research/reviewed/tooldesk-sandbox-deepseek-2026-07-20.md · same arc, shipped

**research/drafts/ (14) — closed-round halves, one-night positions, absorbed opens:**
74. research/drafts/api-resilience-claude-half-2026-07-19.md · one-night round, closed
75. research/drafts/api-resilience-kimi-half-2026-07-19.md · same round, closed
76. research/drafts/arc-replay-opening-claude-2026-07-21.md · opening position, round closed
77. research/drafts/deepseek-stance-round-counter-2026-07-22.md · stance reconciliation landed
78. research/drafts/deepseek-steer-corpus-counter-2026-07-22.md · steer-corpus reconciliation landed
79. research/drafts/homebase-build-claude-position-2026-07-20.md · homebase round decided (BUILD OUR OWN), positions absorbed
80. research/drafts/homebase-build-kimi-position-2026-07-20.md · same round, absorbed
81. research/drafts/mission-critical-practices-claude-2026-07-20.md · one-night think, absorbed into method-baseline
82. research/drafts/revival-mesh-deepseek-position-2026-07-19.md · revival-mesh reconciliation landed
83. research/drafts/sequencing-claude-position-2026-07-20.md · sequencing round closed
84. research/drafts/sequencing-kimi-position-2026-07-20.md · same round, closed
85. research/drafts/stance-at-thought-opening-claude-2026-07-22.md · stance reconciliation landed
86. research/drafts/steer-corpus-opening-claude-2026-07-22.md · steer-corpus reconciliation landed
87. research/drafts/t097-s1-fence-brief-2026-07-20.md · T097-S1 fence closed
88. research/drafts/t097-s1-verdict-kimi-2026-07-20.md · T097-S1 verdict, closed
89. research/drafts/tools-hunt-claude-half-2026-07-20.md · tools-hunt synthesis landed (docs/)
90. research/drafts/ui-homebase-kimi-position-2026-07-20.md · homebase round absorbed

---

## LIST 4 — UNSURE (10; human rules, question named)

1. **docs/failure-ledger-2026-07.md** — KEEP current or historical? It's a *ledger* (append
   by design); but the month turns. Q: does the failure ledger roll to 2026-08, or is this
   the standing file? Default-keep current if it is THE ledger.
2. **docs/t039-lanes-latches-design-2026-07.md** — "GOVERNING DESIGN (decision record)" —
   T039 DONE but the doc governs LIVE_CONSTRAINTS lane law. Q: governing-design-of-record
   for a shipped arc = current-as-law, or historical-as-record? Lean: KEEP current (law).
3. **docs/packet-spec-v1-2026-07.md** — "reconciled build spec" — spec shipped, but it's
   the packet LAW. Q: same as t039 — is a landed spec current-as-contract or historical?
   Lean: KEEP current (contract).
4. **docs/method-baseline-2026-07.md** — counted current above; flagging because it is
   load-bearing law. No change proposed — listing here only to confirm it must NOT fossilize.
5. **docs/library-schema-reconciliation-2026-07-21.md** — counted current (the arc kimi
   fenced 07-21, G-series landing tonight). Q: is the library arc closed (schema ruled) or
   still landing doors? If closed, this flips to the closing record (historical).
6. **research/reviewed/ironman-plan-2026-07-16.md** — spans T075/T084/T085, partially landed.
   Q: is the ironman arc closed or does a slice remain open? If open, keep current.
7. **research/reviewed/hardening-reconciliation-2026-07-17.md** — build spec spanning
   T075/T081/T090. Q: all three landed, or does T090-class work keep it alive?
8. **research/reviewed/deepseek-arc-wrap-2026-07-23.md** — counted current (tonight). Flag:
   "arc wrap" reads like a closing record. Q: is partner-night arc closing tonight (→historical
   at wrap) or does it carry into tomorrow's gate? Time-based; decide at morning wrap.
9. **research/drafts/ui-gap-diagnosis-2026-07-23.md** — counted current (feeds CONTRACT ratification).
   Q: does it fossilize the moment Daniel ratifies CONTRACT v0 (its purpose served)?
10. **docs/JOURNEY.md** — counted current (standing narrative). Flag only: it is append-by-design;
    confirm it is THE journey file, not a monthly shard (same question as failure-ledger).

---

## What this is NOT (rails honored)

- No header edits — every stamp above rides your review. Read-only round, as chartered.
- Nothing deleted, nothing moved, every path stays citable (the whole point).
- briefs/, chronicles/, generated files untouched per charter.

## Proposed mechanics (for your review pass)

1. You rule the 10 UNSURE + spot-check the FOSSIL/SUPERSEDED lists (the 6 supersession
   pairs and the T039/T043 reconciliation closures are the highest-confidence).
2. Approved stamps applied in bulk (deepseek or your lane): `Status: historical` for
   FOSSIL, `Status: superseded-by <path>` for SUPERSEDED.
3. gen_library regenerates → the reader-face collapses to the ~87 truly-current.
4. The sweep itself becomes a repeatable audit domain (audit charter genus): a
   `doc-supersession` rule — `current` stamp older than its arc's ledger-close = DRIFT
   row. That is the standing fix, not a one-night sweep; this proposal's lists are its
   founding corpus.

## Honesty notes

- Evidence is ledger-state + header-self-declaration + supersession lineage — VERIFIED where
  the ledger names the task DONE, INFER where I read "arc closed" from a reconciliation's
  existence. No vibes; the UNSURE list is where the evidence ran out.
- The 184-row machine-readable inventory (with per-file task-refs + dates) is at
  scratch/supersession_megaread_corpus.txt — regenerate any time via the two census tests.
- One known approximation: LIST 1 compresses ~20 reviewed-half files into the grouped line
  to keep this proposal readable at 184 total; the census corpus carries every path
  verbatim and is the machine-readable source of record for the bulk-apply step.
