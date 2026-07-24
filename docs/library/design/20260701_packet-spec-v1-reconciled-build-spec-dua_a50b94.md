---
akashic_id: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
akashic_sha: 6a6ea577454a
status: current
type: design
date: 2026-07-01
title: "Packet Spec v1 -- reconciled build spec (dual-half, dated)"
gist: deepseek Q1 (research/reviewed/deepseek-t040-review-2026-07-12.md) + claude cross-check (research/reviewed/claude-t040-spec-crosscheck-2026-
tenant: solo
visibility: fleet
seats: []
category: [bus, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_t040-packet-spec-review-endpoint-ideatio_40168e
    rel: cites
  - target: art_20260712_t040-spec-review-claude-cross-check-of-d_994a8e
    rel: cites
  - target: art_20260712_t040-packet-spec-v1-deepseek-blind-desig_cbdeba
    rel: cites
  - target: art_20260712_t040-packet-spec-v1-claude-half_30a58a
    rel: cites
  - target: art_20260701_t040-packet-spec-v1-fenced-dual-design-b_a9669a
    rel: cites
  - target: art_20260712_t038-t039-implications-reconciliation-re_4966b0
    rel: cites
  - target: art_20260701_comms-mailbox-over-the-log-t095-governin_06357f
    rel: cites
created: "2026-07-17T23:53:36"
updated: "2026-07-23T21:42:06"
---
<!-- GENERATED PROJECTION of art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Packet Spec v1 -- reconciled build spec (dual-half, dated)

deepseek Q1 (research/reviewed/deepseek-t040-review-2026-07-12.md) + claude cross-check
(research/reviewed/claude-t040-spec-crosscheck-2026-07-12.md): A add `pri`, B per-lane `overflow`,
C add `ecn`, D CUT `ttl` (refined: fold into deadline_ts + conditional DEADLINE_EXCEEDED reply),
E trace len+sha spot-check, F seq gap-window rebound off ttl. APPROVED by Daniel delegation 2026-07-13
("leave the order up to you, keep working"); amend D is the one reversible judgment call (refined cut
vs the mutual-exclusivity fallback -- flip on request). The riding build sub-slice may now register +
cite this spec. Net envelope: +1 field, ZERO new families.)
Class: build-spec (T031 hook 1 artifact -- every packet-substrate ship cites this)
Governs: T040 (and the envelope contract T038/T039/T041 build against)
Halves: research/reviewed/deepseek-t040-packet-spec-2026-07-12.md (blind)
+ research/reviewed/claude-t040-packet-spec-2026-07-12.md (sealed until his landed)
Charter: research/t040-packet-spec-brief-2026-07.md. Rulings D1-D6 of
research/reviewed/t038t039-implications-reconciliation-2026-07-12.md are inherited LAW.

## CONVERGED BLIND (both halves independently -- the spec's spine)

- v ABSENT = v1 implicit; v stamped by the SEND DOOR, never sender code; consumers
  DOWNGRADE unknown versions with one loud warning and never drop mail for schema alone.
- lane DERIVED from kind by a pure router table at the door; sender cannot choose lanes
  (test-* under drill env the only escape); unknown kind = REFUSED LOUD at send.
- deadline_ts absolute + consumer-cooperative skip (DEADLINE_EXCEEDED reply that never
  clears an expectation) with the L4 sweep authoritative.
- latch[] carries the D1 fail-direction PER LATCH (enforce -> expiry stays BLOCKED loud;
  depend -> proceeds degraded loud); DAG check at creation names the cycle path.
- frag {seq, of, whole_id} with DECLARED total ('of' required -- a missing fragment is
  detectable); reassembly consumer-side; timeout LOUD; duplicates idempotent.
- len + sha computed at the send door, validated at the consume door, canonical
  serialization order fixed; mismatch = DROP + integrity event + armed expectations stay
  armed (RB-29 extended: a corrupt reply must never clear its expectation).
- MTU refuse-loud at send (BUS_MAX_MESSAGE_BYTES dial, default 65536): NEVER truncate;
  identical pin shapes in both halves.
- idempotency_key generalizes the reply_sent sentinel; token offers will set it.
- Roster capped, T034-Goodhart-governed, deletion ritual with tombstones.

## RULINGS R1-R8 (where the halves diverged)

R1. FIELD NAME COLLISIONS (two designs under one name -- both resolved):
  - `class`: deepseek's class = packet FAMILY (semantic taxonomy); claude's class =
    sig fidelity rung. RULED: the field is `family` (deepseek's design, renamed for
    precision); the fidelity RUNG stays expressed by kind (halt/steer/nudge/pause are
    already kinds -- zero new field, zero ceremony). claude's class field is DELETED.
  - `ttl`: deepseek's ttl = seconds-of-useful-life (drop-expired at consume, loud event);
    claude's ttl = redrive/hop count. RULED: `ttl` = SECONDS (deepseek's), because the
    loop/retry bound ALREADY lives in L4's attempt counter -- duplicating it in the
    envelope was claude's error. Documented: loop-bounding is L4's job. [SUPERSEDED by amend D
    (2026-07-13): the ttl FIELD is now CUT -- on one machine (one clock) it is a strictly-less-precise
    deadline_ts; deadline_ts absorbs it, the door offers a `ts + within_s` convenience, and
    fire-and-forget content-freshness is preserved via the conditional DEADLINE_EXCEEDED reply. The
    loop-bound stays L4's job regardless.]
R2. FAMILIES SHIPPING IN v1. deepseek shipped 8; his OWN governance rule says no family
  without a live consumer -- and test-attach/directive-attach consume via token machinery
  that does not exist until T038. RULED by his own rule: v1 SHIPS families whose consumers
  exist TODAY -- status (UI/doctor), query/answer (substrate answers fleet-state), steer/
  nudge (regularized existing), dispatch (consumer = the ledger claim path, task_assigned
  audited). RESERVED with schemas named now: test-attach + directive-attach (ship with
  T038), ui-projection (ships with T041's consumer), context-delta (FM12 gate, LAST),
  offer/counter/accept/release (T038), order (post-T038). Cap: 12 families (10 named above
  + 2 headroom), counted as FAMILIES (kinds map onto families; vocabulary aligned).
R3. PER-FLOW seq. Reconciliation law says REQUIRED (FM-P1); deepseek deferred (true: no
  reorder risk until multiple lanes exist); claude shipped it with flow. RULED: the FIELD
  is DEFINED NOW in the v2 schema (spec is the contract lanes build against): int,
  REQUIRED-when-flow-present, per-flow monotonic, consumer holds N+1 awaiting N bounded
  by ttl then LOUD gap event. ENFORCEMENT ACTIVATES with the first multi-lane consumer
  (T039 build bar S7 exercises it). Spec-now, enforce-at-lanes.
R4. flow FORMAT + PROPAGATION (complementary halves folded): 32-lowercase-hex OTel
  trace-id format (deepseek -- OTLP-exportable as-is) AND door-side propagation (claude --
  reply/redrive/ack doors copy flow from the packet being answered; sender code never
  has to remember). Both are in.
R5. INTEGRITY COST HONESTY. deepseek required len+sha on ALL v2; claude exempted trace.
  RULED: len+sha REQUIRED on work/sig/test-*; on trace they are DIAL-OPTIONAL
  (PACKET_INTEGRITY_TRACE, default off) -- deepseek's own QoS0 doctrine ('no decision may
  depend on a trace delivery') means trace integrity is telemetry hygiene, not a safety
  property. latch[]/frag serialize as ABSENT when unused (no bytes, no ceremony --
  smallest legal v2 chat gains only v+len+sha). [amend E (2026-07-13): when PACKET_INTEGRITY_TRACE is
  OFF, the send door STILL stamps len+sha on every 1000th trace packet (dial) as a spot-check; the
  consume door logs a mismatch at WARNING (never DROP), so the implicit-ECN / telemetry-join wire can
  detect a corrupt trace stream at ~0.1% cost.]
R6. ROSTER HOME. deepseek: T034 manifest entries; claude: packet_spec.py. RULED middle
  path consistent with deepseek's OWN T034 cut #3 (don't absorb non-dials): schemas live
  in core/comm/packet_spec.py (code is the source of truth; families are contracts, not
  tunables); the T034 manifest carries the roster INDEX (name, status, introduced,
  removed) for discovery/audit/settings render. Guard checks the two agree.
R7. FIRST CUTOVER. Producer first = the runner send paths (both halves; highest volume,
  and len+sha there would have caught all three of tonight's silent losses). First
  consumer = the WATCHER (deepseek -- simplest consumer proves the dual window), then
  UI -> runner-consume -> doctor -> chronicler -> L4 sweep. Bounded window; retirement of
  v1 producers is a ledger event.
R8. MIGRATION ENFORCEMENT LAW (from deepseek's probe Q2, promoted to law): a consumer
  that ignores latch[] is a hole exactly the size of the migration window -- therefore
  NO enforcement-latch-bearing family may ship until every consumer on its path is v2.
  This sequences T038/T039 builds behind the consumer cutover, mechanically.

## THE v2 ENVELOPE (final field table)

Field           | Type/format                  | Req | Writer      | Validated at | On violation
v               | int >=1                      | v2  | send door   | consume      | downgrade+warn; fail CLOSED only if a stripped field is enforcement-required (R1/D1)
frm,to,kind,content,ts,meta,parts | (v1 fields, unchanged) | yes | sender/door | both | as today
flow            | 32 lowercase hex (OTel)      | opt | sender mints; DOORS propagate on reply/redrive/ack | send | bad format: REFUSED at send; bogus at consume: strip+warn+treat-as-root
seq             | int, per-flow monotonic      | when flow (enforced at first multi-lane consumer, R3) | sender (door helper next_seq) | consume | gap: hold N+1 bounded by min(remaining-to-deadline_ts, GAP_WINDOW 30s dial), then LOUD gap event + proceed [amend F; was bounded-by-ttl, rebound after the ttl cut]
lane            | work|sig|trace|test-*        | v2  | DOOR (kind->lane router) | send | unknown kind: REFUSED; lane/stream mismatch at consume: LOUD diagnostic
family          | roster name                  | opt (inferred from kind when absent) | sender | send | unknown: REFUSED; kind/family mismatch: LOUD flag
pri             | int 0-3 (default 2)          | opt | sender | consume (load-shed only) | drop-precedence WITHIN the work lane (0=latch/expectation lifecycle -> lose last; 3=best-effort -> dropped first). SPEC-NOW; enforcement activates at the first load-shedding consumer (like seq). [amend A]
deadline_ts     | float unix, absolute (absorbs the cut ttl) | opt | sender (L4 arm sets both; door offers a deadline_ts = ts + within_s convenience for the old relative form) | send + consume | past at send: REFUSED; past at consume: skip + stale_deadline event, AND a DEADLINE_EXCEEDED reply ONLY when an expectation is armed (fire-and-forget content just drops -- the old ttl behavior preserved); never clears expectations [amend D]
ecn             | bool (absent = 0, no bytes)  | opt | a CONGESTED consumer sets it on its REPLY | consume -> sender's rate controller | advisory congestion feedback: the sender's backpressure controller multiplicative-decreases the (agent,family) send rate. One bit, not a window/ACK scheme. [amend C]
latch[]         | [{id,type:causal|ref,gate,ttl_s,fail:enforce|depend,from_lane,from_id}] | opt | sender; latch layer stores | create + consume | cycle: REFUSED naming path; expiry: per `fail` (D1)
frag            | {seq,of,whole_id} or absent  | opt | send door (allow_frag=True opt-in) | send + consume | oversize w/o allow_frag: REFUSED loud; missing frag at FRAG_REASSEMBLY_TTL (300s dial): LOUD timeout, whole dropped; orphan: LOUD drop
len             | int bytes                    | v2 on work/sig/test-*; trace dial-optional (R5) | send door | consume | mismatch: DROP + integrity event, never delivered
sha             | 64-hex sha256, canonical order (frm,to,kind,content,ts,meta,parts; sort_keys, compact separators) | same as len | send door | consume | mismatch: DROP + integrity event; expectations stay armed
idempotency_key | str <=128                    | opt (redrives auto-set) | sender/redrive machinery | consume | duplicate key: sentinel skip (intended); overlong: REFUSED

Kill-switch: PACKET_INTEGRITY_ENABLED dial (default True, flip-provenanced per T034) --
False degrades to v1 integrity, LOUD, never silent.

## PER-LANE CONTRACT (folded)

lane   | QoS/DSCP  | seat                          | retention       | overflow (amend B)                              | wake | write ACL
work   | QoS1 / AF | RB-21 fenced single consumer  | maxlen 10000    | REFUSE-WRITE loud + door sets ecn (QoS1: NEVER silent-trim work) | YES (the only lane) | BUS_SEND non-quarantined
sig    | QoS1 / EF | directed per-agent, seatless  | maxlen 5000     | REFUSE-WRITE loud (carries halt/interrupt; MUST deliver) | no (runner checks between rounds + doorbell) | rung-gated by kind (halt/interrupt=admin+)
trace  | QoS0 / BE | none (firehose)               | XTRIM ring 5000 | XTRIM oldest (QoS0 firehose; today's Redis behavior, now explicit) | no   | may_run-gated (quarantined refused, F1)
test-* | QoS1      | as work, per namespace        | maxlen 10000, namespace TTL | REFUSE-WRITE (drill integrity) | in-namespace only | drill harness only
V1 HONESTY (claude half, folded): sig COMPLEMENTS the Redis control keys -- the hard HALT
path for an IDLE agent remains control-key + doorbell until a receipted decision unifies
them. sig is the signal RECORD lane; unification is not assumed.

CONSUMER-MODEL COMPATIBILITY (T095 stamp, 2026-07-18): cursor-based consumption
(RB-21 fenced seat + per-seat cursors) is the INITIAL consumer model of the work/sig
lanes, not part of the lane contract itself. The lanes are append-only ordered logs;
a message-state index consumer model (mailbox: derived per-message state + claims,
docs/comms-mailbox-design-2026-07.md) MAY be added as a non-breaking layer over the
same streams. T047 and any cutover decision must not hard-code cursor semantics into
the contract. (deepseek-comms-mailbox-2026-07-17.md sec 2 verdict, adopted.)

## RIDING BUILD DELIVERABLE (registers as its own M3 sub-slice citing this spec)

Pins (union of both halves -- 10):
1. MTU bounds triple (65535 ok / 65536 ok / 65537 REFUSED, None returned, stream tail
   unchanged, stderr teaching text exact).
2. len catches truncation (planted len=1000, content shortened -> DROP + event).
3. sha catches corruption (one flipped char -> DROP + event).
4. integrity kill-switch (False: delivered degraded LOUD; True: dropped).
5. frag roundtrip (200KB -> 4 fragments -> identical reassembly).
6. missing fragment -> fragment_timeout at TTL, whole dropped, missing seq NAMED.
7. reassembly TTL boundary honored (TTL-1 ok, TTL+1 orphaned loud).
8. RUNNER TOOL BRIDGE routes through the same MTU check (write_file/edit_file/
   knowledge_note args) -- refuse-loud replaces the ~4k silent clip AT THE BITE SITE.
9. Corrupt/DROPPED reply never clears an armed expectation (RB-29 extension pin).
10. Unknown envelope keys on a v1 consumer are preserved (not silently shed) -- the
    forward-compat floor the migration stands on.
Drill: replay tonight's three real clip payloads (the 2a-2c append, the knowledge_note
body, the oversized handoff) -> three loud refusals or clean frags, zero silent losses.

## CUT LIST (v1 refuses; union, reasons in the halves)

context-delta (FM12 gate first), bundle-latch fields, token families beyond reserved
names, order family, flow-deadline inheritance CALIBRATION (rule adopted, factor
measured after 100+ live flows -- deepseek's timing), OTLP exporter (Phase 4; the SHAPE
ships now), encryption/signing/compression, work-lane priority tiers, expression language
in latch.gate, sender-chosen lanes, schema registry service, vector clocks.

## PROBE BATTERY (merged -- ask these of any future envelope change)

P1 smallest legal packet (ceremony creep check -- R5 keeps a bare chat at +3 fields).
P2 does an enforcement latch survive every consumer on its path (R8 -- the migration law).
P3 len-right/sha-wrong and sha-right/len-wrong each named and handled (integrity is
   binary; disagreement indicates a computation bug, not corruption).
P4 which field, silently wrong, corrupts undetected (walk all; each has a validator+loud).
P5 which door rejects v=3 today and with what message (forward-compat designed, not ad hoc).
P6 can a quarantined id emit each family (ACL matrix row-by-row; newborn gauntlet probe).

## OPEN FOR DANIEL (the approval gate)

1. APPROVE this spec as law (T040 gate) -- build sub-slice then registers citing it.
2. Family cap 12 (R2) -- confirm or resize.
3. R5 trace-integrity default OFF -- confirm (cost honesty vs uniform integrity).
4. The R8 sequencing law binds T038/T039 build order to consumer cutover -- acknowledge.
