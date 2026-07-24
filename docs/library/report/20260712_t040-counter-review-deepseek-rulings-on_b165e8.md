---
akashic_id: art_20260712_t040-counter-review-deepseek-rulings-on_b165e8
akashic_sha: fdf103fc8a8b
status: draft
type: report
date: 2026-07-12
title: T040 counter-review — DeepSeek rulings on R1-R8 + slice-plan verdict
gist: "# T040 counter-review — DeepSeek rulings on R1-R8 + slice-plan verdict **Date:** 2026-07-12 **Class:** counter-review (fence cuts both ways "
tenant: solo
visibility: fleet
seats: []
category: [substrate, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
    rel: cites
  - target: art_20260712_t040-packet-spec-v1-deepseek-blind-desig_cbdeba
    rel: cites
  - target: art_20260701_packet-substrate-slice-plan-lanes-latche_cc7456
    rel: cites
  - target: art_20260712_t038-t039-implications-reconciliation-re_4966b0
    rel: cites
created: "2026-07-12T03:55:48"
updated: "2026-07-23T21:42:16"
---
<!-- GENERATED PROJECTION of art_20260712_t040-counter-review-deepseek-rulings-on_b165e8 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T040 counter-review — DeepSeek rulings on R1-R8 + slice-plan verdict

# T040 counter-review — DeepSeek rulings on R1-R8 + slice-plan verdict

**Date:** 2026-07-12
**Class:** counter-review (fence cuts both ways per A2-1 precedent)
**Refs:** reconciled spec = docs/packet-spec-v1-2026-07.md · my half = research/reviewed/deepseek-t040-packet-spec-2026-07-12.md · slice plan = docs/packet-substrate-slices-2026-07.md · implications reconciliation = research/reviewed/t038t039-implications-reconciliation-2026-07-12.md (D1-D6 LAW)

## RULINGS R1-R8

| R# | Ruling | Verdict | Why |
|----|--------|---------|-----|
| R1 | `class`→`family` + delete claude's rung + `ttl`=seconds | **AFFIRM** | Clean rename. "Family" is more precise than "class" (overloaded with Python/OOP). Claude's rung field correctly deleted — halt/steer/nudge are already kinds; adding a field that restates the kind is redundancy. My `ttl`=seconds design survives — L4 keeps loop-bounding per the attempt counter it already has. This is refinement, not reversal. |
| R2 | 8→6 families shipped, cap 12, by MY OWN rule | **AFFIRM** | My half §2.3: "No family may be added without a SPECIFIC consumer." test-attach and directive-attach consumers are T038 machinery that does not exist. Applying my own rule: status (UI/doctor), query/answer (substrate), steer/nudge (existing), dispatch (ledger claim path) — 6 ship. Cap 12 is generous given the 10-name + 2-headroom constraint. This is MY governance rule proving itself — exactly the immune-system pattern. |
| R3 | `seq` spec-now, enforce-at-lanes | **AFFIRM** | My half deferred seq to v2 because no reorder risk exists until multi-lane consumers ship. The reconciliation is sharper: DEFINE the field NOW in the spec because the spec IS the contract T039 lanes build against. Enforce later (first multi-lane consumer). Spec-now costs nothing; deferring enforcement is pragmatic and correct. Better than my half. |
| R4 | Flow format (OTel hex) + door-side propagation | **AFFIRM** | Not contested. My OTel 32-hex format adopted; Claude's door-side propagation (reply/redrive/ack copy flow) folded in. Both halves complement, neither overrides. |
| R5 | Trace integrity dial-optional (default OFF) | **AFFIRM** | My half required len+sha on ALL v2. The reconciliation applies MY OWN QoS0 doctrine: "no decision may depend on a trace delivery" (§3.1) → trace integrity is telemetry hygiene, not safety. Dial-optional + default-OFF is correct. I should have caught this — my QoS0 doctrine and my integrity requirement were in tension and I didn't reconcile them. Good catch. |
| R6 | Roster home = packet_spec.py + T034 INDEX | **AFFIRM** | My half put families in T034 manifest entries. The reconciliation is consistent with MY OWN T034 cut #3 (don't absorb non-dials into the registry): families are contracts/schemas, not tunable dials. Code is source of truth; manifest carries the INDEX for discovery/audit. Guard checks both agree. Better architecture — families belong with the packet parser, not the settings dial. |
| R7 | First cutover: runner-producer → watcher-consumer | **AFFIRM** | Converged. Both halves had the same ordering. Runner highest-volume producer, watcher simplest consumer. No override. |
| R8 | My probe Q2 promoted to migration LAW | **AFFIRM** | My probe Q2 asked what happens when a v=1 consumer ignores latch[]. Answer: enforcement hole = migration window size. Promoted to binding constraint: NO enforcement-latch-bearing family ships until every consumer on its path is v2. This correctly sequences T038/T039 behind consumer cutover. My insight, now a mechanical gate. |

**All eight AFFIRMED. Zero reversals.** The rulings are refinements, not overrides — they sharpen my half using my own governance rules (R2, R5, R6), converge on better naming (R1), adopt pragmatic enforcement timing (R3), and promote my own probe insight to law (R8). This is the fence working in both directions.

---

## ONE CORRECTION TO THE RECONCILED SPEC

The envelope table at docs/packet-spec-v1-2026-07.md lists `frm,to,kind,content,ts,meta,parts` as a single row spanning all v1 fields. This is a table-formatting artifact, not a design issue. No content change needed.

One naming nit: the field name `frm` (v1 legacy, 3-char abbreviation) should eventually standardize to `from` — but v1 compat requires `frm` survive unchanged. Queue as a v3 cosmetic, not a v2 concern. No amendment.

---

## SLICE-PLAN REVIEW (docs/packet-substrate-slices-2026-07.md)

VERDICT: **PASS — no amendments.** Each section evaluated below.

### § The arc in one sentence
**PASS.** Crisp, correct. "Packet (alphabet), lanes/latches/tokens (grammar: space/time/agency), networking specs (dictionary)" is the right framing. "Surface area shrinks toward one door" is the T041 thesis stated early.

### § Standing constraints
**PASS.** All six constraints are correct and correctly inherited from the reconciliation:

| Constraint | Status |
|------------|--------|
| ENGINE-FIRST (no build before RB-25 closes) | Correct. Design proceeds; build waits. Same parking rule T034 used. |
| T035 discriminator prerequisite | Correct. Multi-seat value depends on per-process identity. |
| Roster discipline (cap + deletion ritual) | Correct. T034 Goodhart-1 applied to lanes/families/latches/tokens. |
| Fail-direction law (D1/D6) | Correct. Enforcement CLOSED, dependency OPEN, kill-switch flip-provenanced. |
| Context-family FM12 gate | Correct. Highest-privilege family, trusted producers only. |
| Three irreducible invention cores | Correct. Latch DAG, token negotiation (CNP+lease+GRACE), roster deletion ritual. |

### § T040 slice scope
**PASS with one stale-name note.** The scope block says `class` and `per-family ACL classes` — pre-R1 artifacts from the brief, not the reconciled spec. Should read `family` and `per-family ACL`. Zero impact on scope correctness; fix when the spec is approved.

### § T039 slice scope
**PASS.** Correctly positioned: design after T040 spec. Lane roster (4 lanes), latch v1 (causal+reference only per both cut lists), DAG+TTL via L4 engine, kill-switch dial, latch index as one GET. Build bars correct: S1-S5 rerun + S2-NEW + S6 + S7 + L1-L3. Strangler migration correctly specified.

### § T038 slice scope
**PASS.** Correctly split: hand pilot NOW (zero code, note-based, drill-3 as workload), design after T040. Protocol shape correct: N=2 rounds, GRACE state, idempotency keys, C2 scope vocabulary, optional atomic lock-claim (D2 middle path — pilot decides), dispatch as audited override. CNP prior art (from reconciliation) correctly cited. Build bars correct: T1-T3 + S8.

### § T041 slice scope
**PASS.** Correctly positioned as design seed (post-T040). Pluggable endpoints thesis correct: module's ONLY cross-boundary interface = packet families. Surface-area reduction = ACI consummated. First candidates correctly named: substrate observer/projector, event-sourced UI, context-delta producer (behind FM12). Dream-gate: "new module lands with ZERO new verbs, discover output gets SHORTER."

### § Sequencing
**PASS.** Correct order: T040 design + T038 pilot + RB-25 exam (NOW) → T039 design → T039 build (post-exam) → latch v1 → T038 build → T041 design. Every arrow = fence→registration→build→verify→bars. No arrow skipped. Correct.

### § What this arc does NOT claim
**PASS.** Honest bounds: one machine, one Redis, N<10 agents. Per-lane temporal order + exact replay along declared edges only. At-least-once + idempotency, never exactly-once. "The ceiling raise is process expressiveness and safe concurrency with receipts — not distributed-systems scale, and it is stronger for saying so." This is M8 (honest bounds) applied to the arc. Correct.

### Slice-plan issues found: ZERO

The plan correctly inherits all reconciliation rulings, correctly sequences slices, correctly gates design-now/build-after-exam, and correctly bounds what the arc claims. One stale `class`→`family` note on T040 scope block (pre-reconciliation artifact, cosmetic). No amendments required.

---

## RELEASE: lock 156

My spec half at research/reviewed/deepseek-t040-packet-spec-2026-07-12.md is complete and no longer held by any advisory lock (all locks released in prior cycles; `agent_cli.py locks` confirmed clean). The file is untracked (`??` in git status) — it awaits your `git add` and commit. Land it verbatim (M6).

---

*End of counter-review.*
