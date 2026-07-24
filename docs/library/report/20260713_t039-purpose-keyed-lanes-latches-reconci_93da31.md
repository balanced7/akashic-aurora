---
akashic_id: art_20260713_t039-purpose-keyed-lanes-latches-reconci_93da31
akashic_sha: dd3b929c7068
status: current
type: report
date: 2026-07-13
title: "T039 — Purpose-keyed lanes + latches — RECONCILIATION (fenced dual, 2026-07-13)"
gist: "Class: reconciled design (M1). The DESIGN decision record; build sub-slices register citing it. Halves (blind, neither saw the other): resea"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260713_claude-blind-half-t039-lanes-latches-des_d7a678
    rel: cites
  - target: art_20260713_deepseek-t039-lanes-latches-2026-07-13_8c485e
    rel: cites
  - target: art_20260713_t039-purpose-keyed-lanes-latches-shared_9a3e76
    rel: cites
  - target: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
    rel: cites
created: "2026-07-13T09:10:58"
updated: "2026-07-23T21:42:22"
---
<!-- GENERATED PROJECTION of art_20260713_t039-purpose-keyed-lanes-latches-reconci_93da31 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T039 — Purpose-keyed lanes + latches — RECONCILIATION (fenced dual, 2026-07-13)

Class: reconciled design (M1). The DESIGN decision record; build sub-slices register citing it.
Halves (blind, neither saw the other): research/reviewed/claude-t039-lanes-latches-2026-07-13.md
+ research/reviewed/deepseek-t039-lanes-latches-2026-07-13.md. Brief:
research/t039-lanes-latches-design-brief-2026-07-13.md. Rides docs/packet-spec-v1-2026-07.md (LAW).
Method: M1 fenced dual design. DESIGN ONLY — no build in this slice; build opens on Daniel's go
(ENGINE-FIRST satisfied: T029 exam CLOSED 2026-07-11).

## CONVERGED (both halves independently → high confidence, the architecture is settled)
- **Lane = a per-lane STREAM KEY** with the per-lane contract made STRUCTURAL: work seated + cursor'd
  + wake-belled; sig seatless-cursor + barge-in bell; trace an XTRIM ring, seatless, NO bell/cursor;
  test-* per-namespace. A pure **kind→lane router at the send door** picks the stream; unknown kind =
  REFUSED loud; senders cannot choose lanes.
- **Wake-listeners subscribe to the WORK lane ONLY** → wake-on-trace is impossible BY CONSTRUCTION
  (S2-NEW is structural, not policed).
- **Migration = strangler fig**: dual-write (router at the door writes legacy + lane) → cut consumers
  lane-by-lane, WORK/wake FIRST → retire legacy (ledger event). One-source-per-consumer + atomic
  cutover flag → no double-delivery; rollback = flip the flag. Acceptance = RB-25 S1-S5 per cutover +
  S2-NEW + S6 (HALT beats a trace flood) + S7 (per-flow seq / latch storm).
- **Latch v1 = causal + reference** (bundle DEFERRED). Index = a Redis key, ONE GET on the hot path.
  Expiry REUSES the L4 expectations engine (one temporal engine, two vocabularies). Fail-direction:
  enforce → stays BLOCKED loud + dead event; depend → proceeds degraded loud.
- **Networking prior-art grade (near-identical)**: QUIC multiplexed streams = ADOPT the HOL-avoidance
  rationale (the reason for lanes); DiffServ = ADOPT/ADAPT the AF/EF/BE classes (skip the IP bits);
  OTel span+links = ADOPT the shape (flow=trace_id LAW, ref-latch=link; skip the exporter, Phase 4);
  gRPC deadline propagation = ADAPT into L4 (deadline flows down the causal chain); SDN control/data
  split = ADOPT as the sig framing (sig=control plane, never starved by data); TCP/TIME_WAIT = SKIP
  (T038 token lifecycle); MTU/frag+checksum = DONE (T043).
- **Trace exemption (T043 inheritance)**: the send-door router, having routed to trace, emits WITHOUT
  len+sha except every 1000th packet (spot-check). 4-lane cap CONFIRMED; deletion ritual = drain
  consumers → remove router mapping → remove keys → ledger + docs.
- **Worst risk = a misrouted halt→trace→lost**; both guard it identically: a PURE tested router with a
  per-kind pin (control kinds → sig, NEVER trace) + sig REFUSE-WRITE (loud, never trimmed).

## DIVERGED → RESOLVED

### D-1 [→ claude, grounded in the bus's own history] Consumer-seat mechanism: EXTEND XREAD+RB-21, do NOT switch to consumer groups.
deepseek proposed a SHARED per-lane work stream (`...:work`) read via a Redis **consumer group**
(XREADGROUP). claude proposed keeping the EXISTING model — PER-AGENT per-lane inboxes
(`{ns}:work:inbox:{agent}`) read via XREAD + the stored cursor hash + the RB-21 generation-fenced Lua.
**RESOLUTION: claude's.** Two reasons: (1) a shared work stream + consumer group LOAD-BALANCES across
readers — exactly the "broadcast reached one agent" bug the bus header documents fixing; directed work
mail (handoff→claude vs →deepseek) REQUIRES per-agent addressing. (2) The XREAD+cursor+RB-21-generation
seat is drill-CERTIFIED across the RB-25 storm; replacing it with consumer groups rebuilds certified
safety code for no gain (same principle that kept T043 off the RB-21 Lua). So: add the LANE dimension to
the existing per-agent keys; keep XREAD + RB-21 generations. (Adopt nothing from XREADGROUP.)

### D-2 [SYNTHESIS — his DAG + her consumer behavior] Latch cycle-safety + blocked-consumer.
- **ADOPT deepseek's within-flow DAG constraint (the headline win):** a causal-latch's `from_id` must be
  in the SAME flow with `seq(from_id) < seq(new)`. Per-flow seq is monotonic, so a within-flow backward
  edge CANNOT cycle — cycle-freedom is BY CONSTRUCTION, no transitive-closure walk (claude's approach)
  needed. Cross-flow ENFORCEMENT latches are CUT from v1 (cross-flow gets reference-latches only, no
  enforce). Zero-ceremony, impossible-by-construction — strictly better than a runtime cycle check.
- **ADOPT claude's defer-not-HOL-block consumer behavior:** a work packet whose enforce-latch gate is
  unsatisfied is DEFERRED (advance cursor + buffer in a consumer-local blocked-set, re-check on the next
  drain + on an unlatch bell), NOT HOL-blocked (deepseek had the consumer BLPOP-wait, stalling the whole
  work lane). Rationale: HOL-blocking the work lane on a latch CONTRADICTS the QUIC/lanes rationale
  (Daniel's own steer). Reuse the T043 advance-and-buffer + Redis-durable pattern so a deferred packet
  survives restart. deepseek's within-flow constraint SHRINKS the block scope (only a same-flow
  predecessor gates), but a single work cursor still argues for defer over block across flows.
- L4 backstop (deepseek): the consumer's OWN ttl_s timeout fires the fail-direction even if the L4 sweep
  is down — guarantees forward progress. ADOPT.

### D-3 [SYNTHESIS] Trace spot-check counter.
Policy location = packet_spec (integrity SSOT) via `lane_wants_integrity(lane, counter)` (claude); the
counter is a **Redis per-namespace key** `{ns}:trace:spotcount` (deepseek) so "every 1000th" is globally
consistent across processes, not per-process. Door composes: router gives the lane, packet_spec gives the
policy, the Redis counter gives the global tick.

### D-4 [UNION] Risk guards — defense in depth.
Both worst-risk guards PLUS: halt keeps its EXISTING Redis control-key + doorbell hard-path (claude, spec
V1-HONESTY — a lost sig packet is not a lost halt); a runtime lane monitor samples each lane and alarms on
a kind/lane-role mismatch (deepseek); work-lane REFUSE-WRITE = no silent work loss at overflow (both).

## KEY SIGN (fence working): two blind halves produced the SAME lane architecture + the SAME worst-risk
+ the SAME guard. The only real fork (D-1 seat mechanism) resolves cleanly against the bus's documented
history; the latch fork (D-2) SYNTHESIZED into something better than either half alone.

## BUILD SUB-SLICES (register on Daniel's go; each fenced + gated, cite this doc)
- **T039a Lane router + keys + dual-write** (no consumer cutover yet): pure kind→lane table + per-lane
  key shapes + the trace integrity exemption (folds the T043 R5 debt) + dual-write at the door. Bars:
  router per-kind pins (control→sig never trace), trace exemption spot-check, dual-write leaves legacy
  intact.
- **T039b Consumer cutover** (strangler): wake-listener→work-bell-only, then runner→work+sig. Bars:
  RB-25 S1-S5 + S2-NEW + S6.
- **T039c Latch v1** (causal within-flow + reference): index, within-flow-seq DAG, L4 expiry, defer-not-
  block consumer, per-lane generations. Bars: L1-L3 (cycle refusal, expiry unblocks, ref never blocks) +
  S7. R8 migration law binds enforcement-latch families behind full-path v2 cutover.
- **T039d Retire legacy** + roster registry + deletion ritual (ledger event).

## OPEN FOR DANIEL (design gate)
1. Approve this design → register T039a-d (build opens; T029 exam already closed).
2. D-1 (keep XREAD+RB-21, not consumer groups) — confirm.
3. D-2 cross-flow ENFORCEMENT latches CUT from v1 (reference-only cross-flow) — confirm the scope.
4. Sequencing: lanes (T039a/b) BEFORE latches (T039c) BEFORE T038 tokens — confirm.
