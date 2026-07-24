---
akashic_id: art_20260713_t039-purpose-keyed-lanes-latches-shared_9a3e76
akashic_sha: a2e4408060e2
status: current
type: design
date: 2026-07-13
title: "T039 — Purpose-keyed lanes + latches — SHARED DESIGN BRIEF (blind fence, 2026-07-13)"
gist: "Class: design brief (M1 — handed IDENTICALLY + BLIND to both halves: claude + deepseek). Produces: two blind halves → reconciliation → desig"
tenant: solo
visibility: fleet
seats: []
category: [bus, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_t039-purpose-keyed-lanes-latches-governi_7bc135
    rel: cites
  - target: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
    rel: cites
created: "2026-07-13T09:05:34"
updated: "2026-07-23T21:42:23"
---
<!-- GENERATED PROJECTION of art_20260713_t039-purpose-keyed-lanes-latches-shared_9a3e76 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T039 — Purpose-keyed lanes + latches — SHARED DESIGN BRIEF (blind fence, 2026-07-13)

Class: design brief (M1 — handed IDENTICALLY + BLIND to both halves: claude + deepseek).
Produces: two blind halves → reconciliation → design doc docs/t039-lanes-latches-design-2026-07.md
→ registered build sub-slices. DESIGN ONLY (no build in this slice).
Governs: T039. Rides the LAW packet spec (docs/packet-spec-v1-2026-07.md) — the envelope, the
lane field, and the PER-LANE CONTRACT are already LAW; this slice designs the MECHANISM + latches.

## The one-sentence problem
The bus is ONE Redis stream today. Partition it into a fixed, capped lane roster (work / trace /
sig / test-*) so control traffic never queues behind trace spam and wake-listeners watch only
directed mail — AND add a LATCH primitive (explicit causal edges between lanes) so process rules
("review gates commit") become transport invariants, not conventions. Design the mechanism, the
migration, and the latch semantics, grading networking prior-art to avoid heavy invention.

## Inherited LAW (do NOT re-litigate — design WITHIN these)
From docs/packet-spec-v1-2026-07.md (reconciled, LAW):
- `lane` is DERIVED from `kind` by a PURE ROUTER TABLE at the send door; senders cannot choose
  lanes (test-* under a drill env is the only escape); unknown kind = REFUSED loud.
- PER-LANE CONTRACT (already fixed):
  work | QoS1/AF | RB-21 fenced single consumer | maxlen 10000 | overflow REFUSE-WRITE loud + ecn
       | the ONLY lane wake-listeners watch | ACL: BUS_SEND non-quarantined
  sig  | QoS1/EF | directed per-agent, seatless | maxlen 5000 | overflow REFUSE-WRITE loud
       | no wake (runner checks between rounds + doorbell) | ACL: rung-gated by kind (halt/interrupt=admin+)
  trace| QoS0/BE | none (firehose) | XTRIM ring 5000 | overflow XTRIM oldest | no wake | ACL: may_run-gated
  test-*| QoS1  | as work, per namespace | maxlen 10000 + ns TTL | REFUSE-WRITE | in-namespace wake only
- latch[] envelope field EXISTS: [{id,type:causal|ref,gate,ttl_s,fail:enforce|depend,from_lane,from_id}];
  cycle at creation = REFUSED naming the path; expiry per `fail` (enforce→stays BLOCKED loud; depend→
  proceeds degraded loud). (D1 fail-direction law is inherited.)
- flow = 32-hex OTel trace_id; ref-latch = OTel "link"; doors propagate flow on reply/redrive/ack.
- per-FLOW seq is DEFINED now, ENFORCED at the first multi-lane consumer (T039 build bar S7).
- R8 MIGRATION LAW: no enforcement-latch-bearing family ships until EVERY consumer on its path is v2.
- Roster CAPPED (T034 Goodhart): adding a lane needs a why-not-an-existing answer + a deletion ritual.
- T043 (shipped) DEFERRED to this slice: R5 lane-optional integrity (len+sha REQUIRED on work/sig/
  test-*, DIAL-OPTIONAL on trace) + amend-E trace spot-check (every 1000th trace packet) ACTIVATE with
  the lane router. Today T043 stamps integrity on ALL packets; the router must add the trace exemption.

## Daniel's steers (verbatim seeds — honor these)
1. NETWORKING-LENS (t039-networking-lens): "the bus+latch system is very similar to NETWORKING. Use
   established networking/API principles to avoid heavy invention." GRADE each mapping wholesale-adopt /
   adapt / skip: DiffServ/DSCP (lanes as QoS), QUIC multiplexed streams (head-of-line blocking is THE
   lanes rationale), TCP state machine + TIME_WAIT (token lifecycle — T038, note only), MTU/frag +
   checksum-at-door (T043, DONE), W3C Trace Context / OTel span+links (latch provenance), gRPC deadline
   propagation (L4 inherited through causal chains), SDN control/data-plane split (sig = control plane).
2. LATCH-REFINEMENT (t039-latch-refinement): lanes REPLACE implicit global order with EXPLICIT selective
   causal edges — strictly MORE expressive. Edge types: (1) causal-latch = happens-before barrier the
   bus ENFORCES at transport level; (3) reference-latch = weak provenance pointer, queryable, no
   enforce. [bundle-latch = DEFERRED per both cut lists — v1 latch = causal + ref ONLY.] UNLATCH =
   release when satisfied. GUARDS REQUIRED: DAG invariant + cycle detection + latch-expiry (REUSE the L4
   expectations engine — one temporal-constraint engine, two vocabularies). KEY HONESTY: on one Redis,
   stream IDs (<ms>-<seq>, one clock) ALREADY give approximate global order for FREE → latches earn keep
   ONLY where ENFORCEMENT or SEMANTIC PROVENANCE is needed; default to cheap timestamp order (zero-
   ceremony-when-simple). Payoff: durable causal edges give the recall funnel a GRAPH to walk (precise
   credit assignment — attacks the 4.5% recall-value problem).
3. EVERYTHING-IS-A-PACKET (t038t039-packet-vision): the packet is the universal quantum of coordination.
   Lanes are the substrate under that. (Family design is T041/T038, not this slice — but the lane roster
   must not preclude those families.)

## What THIS slice must design (answer all; be concrete)
A. LANE MECHANISM: how does the single stream become 4 lanes? The Bus(namespace=...) mechanism EXISTS
   and is drill-tested — is a lane a namespace, a stream-suffix, a separate stream key, or a consumer-
   group? Give the exact Redis key shape per lane and how the kind→lane router at the door writes to it.
   How do per-agent cursors, the RB-21 fenced consumer seat, and the doorbell change per lane (work has
   a seat; sig/trace do not)?
B. MIGRATION (strangler fig, NO flag day): dual-write → cut consumers lane-by-lane → retire. What is the
   exact cutover order (which consumer moves first)? How do you dual-write without double-delivery? What
   is the rollback? RB-25 storm bars S1-S5 rerun per-lane-cutover are the acceptance — plus S2-NEW
   (wake-on-trace MECHANICALLY impossible), S6 (HALT latency bound under a trace flood), S7 (per-flow
   seq / latch storm: mid-burst kill, successor recomputes frontier, no lost unlatch).
C. LATCH v1 (causal + ref): where does the latch index live (the spec says "one GET on the hot path")?
   How is the DAG cycle check done AT CREATION (naming the path)? How does latch-expiry REUSE L4? What
   does a consumer do when it reads a work packet whose causal-latch gate is not yet satisfied (block?
   how? for how long? fail-direction)? Per-lane fencing generations — how do they compose with RB-21?
D. NETWORKING PRIOR-ART GRADE: for EACH of the 7 mappings above, state ADOPT-WHOLESALE / ADAPT / SKIP
   with a one-line why. Name the specific thing adopted (e.g. "QUIC: adopt the per-stream independent
   delivery so a stalled work packet never blocks a sig packet; skip QUIC's own wire format").
E. THE TRACE EXEMPTION (T043 inheritance): the router must apply R5 (trace = integrity dial-optional +
   every-1000th spot-check). Where does that live — the router, the send door, or packet_spec?
F. ROSTER DISCIPLINE + CUT LIST: confirm the 4-lane cap. What is the deletion ritual for a lane? What is
   explicitly CUT from v1 (name it, so scope stays honest)?
G. RISKS / KILL-CONDITIONS: what is the worst failure this design can cause, and what guard catches it?
   (e.g. a lane router bug misrouting a halt to the trace ring → HALT lost. How is that impossible?)

Produce a tight, structured design (A–G). This is peer engineering. The other half is answering the
SAME brief blind; convergence = confidence, divergence = a real fork to reconcile.
