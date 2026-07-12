# Packet Substrate — slice plan (lanes, latches, tokens, packets)

Status: current  (2026-07-12)
Class: arc plan (slice roster + gates; NOT a design doc — designs are produced per-slice
behind the fence)
Governs: T038, T039, T040, T041 (the packet-substrate arc)
Source analysis: research/reviewed/t038t039-implications-reconciliation-2026-07-12.md
(+ both halves: research/reviewed/claude-t038t039-implications-2026-07-12.md,
research/reviewed/deepseek-t038t039-implications-2026-07-12.md)
Daniel steers (raw, persisted): notes t039-latch-refinement, t039-networking-lens,
t038t039-packet-vision, t040-pluggable-endpoints-vision
Method: docs/method-baseline-2026-07.md — every slice fenced dual design (M1), registered
before impl (M3), verbatim peer records (M6), gated ship citing the reconciled spec (T031
hook 1).

## The arc in one sentence

Give the substrate a language — packet (alphabet), lanes/latches/tokens (grammar: space/
time/agency), networking specs (dictionary) — so process, orchestration, monitoring,
acceptance, and the UI become things said IN the substrate instead of conventions kept
beside it, and the system's usable surface area shrinks toward one door.

## Standing constraints (inherited by every slice)

- ENGINE-FIRST: no lane/latch/token BUILD ships before the RB-25 exam closes T029 (the
  certified baseline the migration bars are measured against). DESIGN slices may open now
  (same parking rule T034 used).
- T035 discriminator fix (per-process token identity) precedes any multi-seat build value.
- Roster discipline everywhere (T034 Goodhart 1): lanes capped (start 4), packet kinds/
  families capped, latch count is a COST metric, token stats never a leaderboard. Adding
  requires why-not-an-existing; removing has a ritual.
- Fail-direction law (reconciliation D1/D6, the A2-1 principle): enforcement latches fail
  CLOSED; dependency latches fail OPEN degraded + loud; transport fail-open exists only
  under the flip-provenanced kill-switch dial, with T031 ship hooks as the standing
  backstop layer.
- Context-family packets are the highest-privilege family (FM12): trusted producers only,
  provenance headers mandatory, data-not-instructions consumer doctrine, newborn-gauntlet
  probe added when the family ships.
- Three irreducible invention cores (everything else adopts prior art): latch DAG
  enforcement, token negotiation (CNP + lease fencing + GRACE), roster deletion ritual.

## Slices

### T040 — Packet Spec v1 (fenced dual design; DESIGN NOW; the arc's contract)
The single most load-bearing artifact: the orchestration contract, the UI contract, AND
the monitoring contract. Both halves blind from a shared brief; reconciled spec lands as
docs/packet-spec-v1-2026-07.md and every later ship cites it.
Scope: envelope header (v, flow, lane, class, ttl, deadline_ts, latch[], frag{seq,of,
whole_id}, len, sha, idempotency_key); kind/family roster + cap + deletion ritual;
per-lane delivery contract in MQTT QoS + DiffServ vocabulary (trace=QoS0/BE, work=QoS1/AF,
sig=EF); per-family ACL classes (context = trusted-only; sig rungs authority-gated);
OTel/W3C-shaped ids (flow=trace_id, packet=span, ref-latch=link) so the causal record is
exportable to standard viewers; per-FLOW sequence numbers (FM-P1); the v1->v2 dual-version
migration rule (no flag days).
RIDES THIS SLICE (early build deliverable, three silent-loss receipts on 2026-07-12
alone): send-door MTU rejection (BUS_MAX_MESSAGE_BYTES dial, LOUD refusal, no silent
clipping ever again), declared len+sha validated at consume, -partN fragmentation
formalized so a missing fragment is DETECTABLE.
Gate: dual-half reconciled spec + Daniel approval; build sub-slice registered (M3) citing
the spec.

### T039 — Purpose-keyed lanes + latches (approved; design behind fence AFTER T040 spec)
Lanes route packets — the spec defines what a packet is, so spec first. Design: lane
roster work/trace/sig/test-* semantics; latch v1 = causal + reference ONLY (bundle
deferred per both cut lists); DAG-at-creation + TTL via the L4 engine (one temporal-
constraint engine, two vocabularies); kill-switch dial (flip-provenanced); latch index =
one GET on the hot path; per-lane fencing generations.
Build (post-exam): strangler migration consumers-first; bars = S1-S5 rerun per lane
cutover + S2-NEW (wake-on-trace mechanically impossible) + S6 (HALT latency bound under
trace flood) + S7 (latch storm: mid-burst kill, successor recomputes frontier, no lost
unlatch) + L1-L3 (cycle refusal, expiry unblocks, ref never blocks).

### T038 — Work-token negotiation (approved; hand pilot NOW, design after T040)
HAND PILOT opens immediately (zero code, per the title): note-based token records on the
live concurrency-trial lanes — the drill-3 storm execution split (deepseek authored the
burst script, claude executes) is the designated pilot workload. OFFER -> ACCEPT ->
HELD(+progress lines referencing artifacts) -> RELEASED, one note per transition. The
2026-07-12 implications fence itself already ran as the first informal pilot (latch:
reconcile gated on both halves; token: lane split negotiated peer-to-peer) — its
transcript is the reconciliation record.
Design (post-T040): N=2 rounds, negotiation_dead + empty-counter-rejected, GRACE state
(TIME_WAIT: 2x max message latency, early-shorten on all-acked), idempotency keys on
offers, scope in C2 vocabulary with optional atomic lock-claim (D2 middle path — pilot
decides), operator DISPATCH as the audited override family (BUS_DISPATCH, declinable),
directive-attach amendments NARROW-ONLY.
Build bars: T1-T3 + S8 (offer contention: exactly one HELD, stale accepter refused by
generation, expiry reverts loudly).

### T041 — Pluggable engine/module endpoints (proposed; design seed AFTER T040 lands)
Daniel steer 3 (note t040-pluggable-endpoints-vision): a module's ONLY cross-boundary
interface is the packet families it emits/receives. Adding functionality = registering
families against the spec (no new CLI verbs, no new Python API surface); removing =
deletion ritual over its families. Surface-area reduction is the ACI thesis consummated:
CLI, MCP, UI, engines, observers all become projections of ONE contract. First candidates
when opened: the substrate observer/projector (status/query/answer families; standing
queries replacing doctor polls; exam bars as continuous monitors), the event-sourced UI
projection (T033/T002 consumers), context-delta producer (the recall funnel — behind the
FM12 gate). Dream-gate at design time: a new module lands with ZERO new verbs, and the
system's discover output gets SHORTER, not longer.

## Sequencing

NOW (parallel): T040 fenced design | T038 hand pilot on drill-3 | RB-25 exam continues
(drill 3 storm -> drill 4 soak; closes T029).
THEN: T039 design (against the spec) -> post-exam lane migration build (bars above) ->
latch v1 -> T038 build (from pilot receipts) -> T041 design (observers/UI/context
producers as first pluggable endpoints).
Every arrow = fence -> registration -> build -> cross-verify -> bars. No arrow skips.

## What this arc does NOT claim

One machine, one Redis, N<10 agents. Per-lane temporal order + exact replay along
declared edges only ('deterministic replay of enforced causality, timestamp-approximate
elsewhere'). At-least-once + idempotency, never exactly-once. The ceiling raise is
process expressiveness and safe concurrency with receipts — not distributed-systems
scale, and it is stronger for saying so.
