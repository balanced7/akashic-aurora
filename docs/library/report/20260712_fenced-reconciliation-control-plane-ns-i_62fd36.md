---
akashic_id: art_20260712_fenced-reconciliation-control-plane-ns-i_62fd36
akashic_sha: 15a9b9a68445
status: draft
type: report
date: 2026-07-12
title: "Fenced reconciliation: control-plane ns-isolation + T040 endpoints (claude reconciler), 2026-07-12"
gist: "# Fenced reconciliation: control-plane ns-isolation + T040 endpoints (claude reconciler), 2026-07-12 Reconciles the two blind fenced duals t"
tenant: solo
visibility: fleet
seats: []
category: [coordination, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_control-plane-namespace-isolation-claude_fade67
    rel: cites
  - target: art_20260712_control-plane-namespace-isolation-deepse_1505e1
    rel: cites
  - target: art_20260712_t040-useful-endpoints-systems-claude-bli_a8dca5
    rel: cites
  - target: art_20260712_t040-endpoint-system-exploration-deepsee_7f533e
    rel: cites
  - target: art_20260712_t040-packet-spec-review-endpoint-ideatio_40168e
    rel: cites
  - target: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
    rel: cites
created: "2026-07-12T23:26:41"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260712_fenced-reconciliation-control-plane-ns-i_62fd36 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Fenced reconciliation: control-plane ns-isolation + T040 endpoints (claude reconciler), 2026-07-12

# Fenced reconciliation: control-plane ns-isolation + T040 endpoints (claude reconciler), 2026-07-12

Reconciles the two blind fenced duals that landed after deepseek's relaunch. Both converged strongly.
Halves:
- ns-isolation: research/claude-control-plane-ns-isolation-2026-07-12.md (was sealed) +
  research/reviewed/deepseek-control-plane-ns-isolation-2026-07-12.md
- endpoints: research/claude-t040-endpoints-2026-07-12.md (was sealed) +
  research/reviewed/deepseek-t040-endpoints-2026-07-12.md
Spec review (Daniel decision, separate): research/reviewed/deepseek-t040-review-2026-07-12.md.

===================================================================================================
## PART A — CONTROL-PLANE NAMESPACE ISOLATION  (strong convergence; deepseek's half is the base)
===================================================================================================

### Converged decision rule (independently identical)
- claude: "coordinates OVER THE BUS -> scope; protects a SHARED RESOURCE outside the bus -> global."
- deepseek: "the key is OF the agents in a namespace -> scope; OF the infrastructure -> global."
Same rule. Litmus (deepseek's, adopt it): *does the key move when a child sets BIFROST_NAMESPACE?
If it should, scope it; if it must NOT move because it crosses namespaces by design, keep it global.*
Independent convergence on **locks.py = GLOBAL** (shared filesystem) as the sole tricky exception is
the strongest signal the rule is right.

### Merged disposition (deepseek's is more complete — he grepped source; I trusted the brief)
| Module | Verdict | Reconciliation note |
|--------|---------|---------------------|
| expectations.py | **SCOPE** | both agree |
| runner_lock.py | **SCOPE** | deepseek resolves my T036 CAVEAT: the seat is single-consumer *per namespace* by design (RB-21), so scoping is correct and does NOT touch the per-session identity work — orthogonal axes. Caveat withdrawn. |
| liveness.py | **SCOPE** | both agree (BusLossGuard has no keys of its own — no change) |
| nudge.py | **SCOPE** | both agree |
| doctor.py | **SCOPE** | both agree (its stalled_since/paged keys must stay coherent with its scoped inputs; RECENT_INBOX_S I just added is a timescale const, unaffected) |
| turn_metrics.py | **SCOPE** | deepseek FOUND this (I missed it) — per-agent stats, `bifrost:turn_metrics:` |
| locks.py | **GLOBAL** | both agree — path locks protect the shared FS (cross-namespace); scoping would re-introduce the edit race. Add the WHY comment. |
| promoter.py | **GLOBAL** | deepseek corrected my tentative SCOPE: `bifrost:<msg_id>` is an event-log REF convention, not a Redis key prefix. No change. |
| launcher.py | **GLOBAL** | deepseek FOUND this (I missed it) — `bifrost:auto_revive` is cross-namespace infra (one launcher for all ns). Ties to the RB-28 auto-revival idea. |
| intent.py | **N/A** | deepseek grepped: no such file / no `bifrost:intent` key anywhere. Drop it. (my-side error — trusted the brief; lesson no_relocation_arg_needs_source_grep_gate.) |

Net: **6 SCOPE, 3 GLOBAL, 1 non-existent** (deepseek's tally; supersedes my 8-with-caveats).

### Mechanical pattern (identical): per-call `_ns()` + `_prefix()` functions, default "bifrost"
preserved, per-call not import-time, timescale constants untouched — exactly Fix A, generalized.
deepseek's anti-pattern warning (don't assign `_NS = getenv(...)` at module level) is worth keeping.

### Guardrail (adopt deepseek's — more concrete than mine): ships WITH the conversion as its
acceptance test: (1) a GLOBAL_MODULES allowlist {locks, promoter, launcher, bus-fallback}; (2) one
pin `tests/test_coordination_namespace_isolation.py` — for each SCOPED module a key lands under
`test_ns:*` not `bifrost:*`; each GLOBAL module stays `bifrost:*`; (3) a comment on every GLOBAL
`NS="bifrost"` stating WHY. My "no-new-hardcoded-bus-key check" folds into this as the lint half.

### Sequencing (converged): the conversion is a default-preserving internal refactor, no flag day,
**ships before the next multi-namespace drill** (prevents another drill-froze-prod). Prereq-coherent
with T039 lanes (nudge/steer packets land in the right ns because the keys are already scoped). T034
absorbs the GLOBAL_MODULES allowlist as a follow-up registration — do NOT double-build.

**READY TO BUILD** (mechanical, ~8 modules + pin, one PR). Recommend claude builds it (I hold Fix A +
the doctor scope already), deepseek reviews — or split the modules. No Daniel decision needed beyond
"go" (it's default-preserving hardening).

===================================================================================================
## PART B — T040 ENDPOINTS / SYSTEMS  (strong convergence on the core; complementary on the edges)
===================================================================================================

Both: everything is a PROJECTION of the packet stream, **ZERO new families**, dream-gate clean.
deepseek's SDN taxonomy (OBSERVER / GATE / ACTUATOR / SINK) is the better organizing frame — adopt it
as the classification; my "retire-a-poll-or-close-a-finding" heuristic stays as the *prioritizer*.

### Converged core (both proposed independently)
| Merged endpoint | claude | deepseek | shape |
|-----------------|--------|----------|-------|
| **Substrate Observer** (doctor-as-projection; retires the poll) | E1 | E1 SOP | OBSERVER |
| **Exam-bars as continuous monitors** (bars watch themselves) | E1-part | E2 EBCM | OBSERVER |
| **Recall goodput upgrade** (materialized recall vs re-rank-per-query) | E4 lineage-graph | E5 Recall-FIB | OBSERVER |
| **Expectation as a substrate service** | E3 deadline-monitor | E7 push-actuator | ACTUATOR |
| **UI as a packet-stream projection** (T002/T007/T033 become projection rules) | E9 | E4 ESUP | SINK |

### Complementary uniques (each half's distinct value — KEEP BOTH)
- **claude-only: Backpressure controller = the principled F3 fix.** deepseek proposed the ECN
  *congestion bit* in his spec review but not the controller; together = the complete F3 answer
  (mark congestion in the envelope + a controller that slows the hot lane instead of a global pause).
- **claude-only: Test-attach** (acceptance criteria travel WITH the work packet — method compiled to
  the wire).
- **deepseek-only: Bus Recorder/Replayer** (records the trace firehose; replays a time range into an
  isolated ns) — directly delivers the riding build's pin-10 deterministic replay (currently manual).
  The ONE justified new verb (`bus-replay`).
- **deepseek-only: Send-Door Gate** — elevates the riding-build send-door hardening into a GATE
  endpoint: one `send_door.validate(envelope)` home for all 9 pins (MTU/len+sha/frag/ACL/latch-DAG).
  Better than my "riding build" framing — it makes the send door a first-class, discoverable surface.

### Consciously EXCLUDED (deepseek's discipline, I concur): a separate control-bus / job-queue
(T038 owns dispatch) / API-gateway / notification channel — each recreates a split the substrate
removes. Good roster hygiene.

### Merged v1 T041 candidate list, sequenced behind the send-door hardening
1. **Send-Door Gate** — ships FIRST, IS the riding build (all 9 pins live here). [engine-first: after T029, which is now CERTIFIED]
2. **Substrate Observer** + **Backpressure controller** — with the T039 lane migration (observer retires the doctor poll; backpressure is the F3 fix the lanes want).
3. **Exam-bar monitor** + **Bus Recorder/Replayer** — anytime, passive trace consumers, low-risk; both pay off immediately (drill-4 K1-K5 go live; pin-10 replay becomes a script).
4. **Expectation actuator** — with the lanes (push-primary, sweep-fallback — my send-side auto-arm fix is its sender-side complement).
5. **UI Projector** — when Daniel lifts the UI pause (T002/T007/T033 collapse into projection rules).
6. **Test-attach** + **Recall-FIB** — v2 / behind the FM12 gate (context-delta family).

Family-roster impact of the whole set: **ZERO new families** (both halves independently). Cap intact.

===================================================================================================
## PART C — T040 SPEC REVIEW (deepseek's 6 findings — a DANIEL decision, not reconciled here)
===================================================================================================
deepseek's spec review (research/reviewed/deepseek-t040-review-2026-07-12.md) proposes, per prior art:
ADD priority/drop-precedence + an ECN congestion bit + an overflow column; MODIFY per-lane drop
behavior; CUT ttl as redundant. These are amendments to docs/packet-spec-v1-2026-07.md and gate the
spec's Daniel-approval. I have NOT independently re-derived them (they were deepseek's assigned Q1);
recommend I do a quick claude cross-check of the 6 before Daniel rules, so the spec goes to him
already-fenced. (The ECN bit pairs with the backpressure endpoint in Part B — coherent.)

===================================================================================================
## DECISIONS FOR DANIEL
===================================================================================================
1. **ns-isolation conversion** — approve "go"? It's default-preserving hardening, ships before the
   next drill, ready to build now (no design left).
2. **T040 spec amendments** — deepseek's 6 findings; want my cross-check first, then you rule?
3. **T041 endpoint v1 list** — the merged sequenced list above; which to green-light with the build.
4. **F3** — deepseek is ready to discuss the runaway-guard redesign; the reconciled answer is already
   emerging (ECN bit + backpressure controller = signal congestion, don't global-pause).

Engine-first is now SATISFIED (T029 certified) — these are buildable. The send-door hardening (Part B
#1) is the natural first build.
