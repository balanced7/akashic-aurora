---
akashic_id: art_20260712_t038-t039-implications-reconciliation-re_4966b0
akashic_sha: 38b48716da38
status: draft
type: report
date: 2026-07-12
title: "T038+T039 implications -- reconciliation record (dual-half, 2026-07-12)"
gist: "# T038+T039 implications -- reconciliation record (dual-half, 2026-07-12) Charter: research/t038-t039-implications-brief-2026-07-12.md (fenc"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_t038-t039-implications-deep-dive-fenced_c9bea1
    rel: cites
  - target: art_20260712_t038-t039-implications-deep-dive-claude_359fe3
    rel: cites
created: "2026-07-12T03:18:35"
updated: "2026-07-23T21:42:22"
---
<!-- GENERATED PROJECTION of art_20260712_t038-t039-implications-reconciliation-re_4966b0 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T038+T039 implications -- reconciliation record (dual-half, 2026-07-12)

# T038+T039 implications -- reconciliation record (dual-half, 2026-07-12)

Charter: research/t038-t039-implications-brief-2026-07-12.md (fenced blind, both halves).
Halves: research/reviewed/claude-t038t039-implications-2026-07-12.md (sealed in session scratch
until deepseek's landed; unsealed verbatim) + research/reviewed/deepseek-t038t039-implications-
2026-07-12.md (his main report; addenda sections appended after Daniel's two mid-dive steers).
Both halves received Daniel's steers as RAW input (notes t039-networking-lens +
t038t039-packet-vision) -- the steers are Daniel's, not either half's synthesis.

FENCE INTEGRITY: claude half written 02:52-02:58 before first reading any deepseek content;
deepseek part 1 landed ~02:56, read by claude only after 'End of report'. Honest caveat: the
current single-stream bus streamed deepseek's THINKING traces into claude's unread peek
mid-write (8 trace lines, section titles only, no analysis substance; claude's half was
already written). The contested lane doing this to a fence is ITSELF evidence for T039 --
recorded as such, not hidden.

## CONVERGED BLIND (both halves independently -- the strongest gate this fleet produces)

C1. sig/HALT latency decoupling is a flagship unlock (ds U1+U5 = cl U5), with ds's
before/after measurement design adopted (trace flood + one HALT, latency compared).
C2. The recall funnel's causal upgrade is the DEEP unlock (ds U2 = cl U4): credit becomes
graph traversal. ADOPTED: ds's strict-subset experiment (causal-set vs relevance-set
flip-to-surface ratio after 10 real decisions) as the acceptance test.
C3. METHOD AS TRANSPORT INVARIANT (ds U4 = cl U3, near-identical phrasing): review-gates-
commit becomes a wire property via causal-latch. Third blind convergence of the night.
C4. Token co-work on one slice with a join-latch (ds U3 = cl U2/U6); IN_PROGRESS exclusivity
correctly named by ds as the current structural limit.
C5. T037 evaporates with work-only wake; T036 shrinks but stays; T035 discriminator fix is a
PREREQUISITE for full seat-isolation value (both; sequence: T035 -> lanes -> T037 retires).
C6. Lanes before tokens; NOTE-BASED token pilot first, zero code (both, per the titles).
C7. Bundle-latch deferred (both cut lists). Cycle guard trilogy identical: DAG-check at
creation + TTL expiry + loud dead event (ds FM1 = cl FM1).
C8. Roster/kind growth is the recurring Goodhart; T034 discipline (cap + deletion ritual)
applies to lanes, latch counts, and packet kinds alike (ds 2g/FM7 = cl FM7/FM11).
C9. Token metrics are COST metrics, never productivity (ds FM4/FM8 = cl FM8).

## DIVERGED -- proposed rulings (Daniel arbitrates where flagged)

D1. LATCH-EXPIRY FAILURE DIRECTION (the load-bearing one). ds: expired latch AUTO-FIRES,
consumer proceeds degraded (fail-open). cl: leaned loud + dead-letter. RULING PROPOSED: split
by latch CLASS, per guard_fail_direction_vs_protected_lane and tonight's A2-1 precedent --
ENFORCEMENT latches (method gates: review-before-commit, test-attach floors) fail CLOSED
(stay blocked, loud, human-visible; auto-fire would reopen the exact lane the latch guards);
DEPENDENCY latches (data/context joins) fail OPEN degraded + loud (ds's shape). Same
principle that reversed the may_run_runner ruling this session; the fence catches the same
class twice in one night, which is the method working.
D2. TOKEN <-> C2 LOCK COUPLING. ds: HELD token claims C2 locks automatically. cl: keep the
systems separate, share only scope vocabulary. RULING PROPOSED: tokens MAY carry lock claims
as an atomic convenience at HOLD time (one door call), but neither system requires the other;
the commit gate keeps checking locks exactly as today. The hand pilot decides whether
auto-claim earns keep. (Middle path; revisit with pilot receipts.)
D3. LANE ROSTER SIZE. ds: cap 8, plus a 5th 'onboard' lane. cl: START at 4, hard. RULING
PROPOSED: start at 4; 'onboard' fails ds's OWN why-not-an-existing-lane test (boot already
delivers the curated sequence; onboarding is a FLOW pattern on work, not a lane). ds's cap-8
stands as the never-exceed ceiling; growth only via deletion ritual.
D4. FLEET CEILING. ds 8-12 agents; cl 5-8. Fold: the honest bound is coordination cost per
LANE not per agent; observation-only agents are near-free (ds's insight, adopted). Publish
'about eight, more if observers' rather than a bigger number.
D5. DETERMINISTIC REPLAY. ds honest-ceiling: lanes abandon total-order replay. cl + Daniel's
latch note: explicit edges are MORE expressive than implicit order. Fold honestly: per-lane
temporal order survives (stream ids); cross-lane replay is EXACT along declared edges and
approximate elsewhere -- 'deterministic replay of enforced causality, timestamp-approximate
replay of everything else.' Claim that sentence, nothing stronger.

## UNIQUE FINDS ADOPTED

From deepseek's half: LATCH KILL SWITCH as a registry dial (his FM6 -- enforcement can be
dropped in an outage while reference/provenance continues; stateless lane router survives) --
adopted WITH T034 flip-provenance required on the dial. Per-lane fencing generations
(STALE_GENERATION on work does not block sig). Latch index as one-GET on the hot path.
S2-NEW: wake-on-trace becomes mechanically impossible, not SKIP_KINDS-dependent.
negotiation_dead event + empty-counter-rejected rule + N=2 rounds. His five public claims
with receipts (voice-compatible). The onboarding SEQUENCE (as a flow, per D3).
From claude's half (pending deepseek's addenda counter-grades): the networking lens N1-N10
(packet spec v1 fields; QUIC/HOL rationale; DiffServ classes; OTel/W3C latch shape --
descriptive->prescriptive extension named as our contribution; gRPC deadline propagation
unifying L4; MTU/frag/len+sha checksum-at-door -- the 4k clip class, which struck AGAIN
tonight clipping his own 2a-2c; MQTT QoS vocabulary; TCP TIME_WAIT tombstones for T038;
CNP prior art; the SKIP list). The packet-vision derivation PF1-PF8 (context-delta with
receipts, flow-addressed steer, order/status, test-attach with the FLOOR guard, directive-
attach, query/answer, event-sourced UI + packet-schema-as-UI-contract ending the bifrost_ui
coupling, substrate-as-observer with exam-bars-as-standing-queries). FM11-FM14 (kind-zoo,
CONTEXT-PACKET INJECTION as the security-critical family, observer feedback storms, UI
authority). Sequencing correction: PACKET SPEC v1 becomes its own fenced dual-design slice,
FIRST.

## CLAIM GRADES (load-bearing factual claims vs code/receipts)

G1. ds 'wake watcher ... trace competes for cursor advancement': mechanism IMPRECISE (the
watcher runs caller-owned local-cursor wait(); the shared cursor is never written by it --
bus.py L294-299), conclusion CORRECT (the consumer's drain still wades trace; wake->consume
latency under flood is real; his 5-10s figure is unmeasured -- the U1 pilot measures it).
G2. ds '4.1% recall-value, 46 credited flips': funnel says 4.2% value, 34 helped credits
all-time (stats 2026-07-12). '46' unverified -- likely flips-vs-credits conflation. Corrected
in the fold; changes no conclusion.
G3. ds 'IN_PROGRESS is exclusive': CORRECT (ledger single-owner shape).
G4. ds 'Bus(namespace=...) shipped and drill-tested': CORRECT (bus.py L136-138, 7097b5e).
G5. cl networking citations (RFC 9000/2474/3246, W3C traceparent, MQTT QoS, TIME_WAIT 2MSL):
stable famous specs, cited from model knowledge; byte-level details deliberately deferred to
design-phase verification (M2 receipts there, not here). No conclusion rests on a byte.

## THE FOLDED ROADMAP (the actionable output)

Phase -1 (NOW, by hand, zero code): (a) note-based token record on the drill-3 execution
split; (b) latch record of THIS fence (reconcile gated on both halves) as the latch pilot;
(c) status-packet kind convention on the drill-3 flow. Findings feed the design briefs.
Phase 0: PACKET SPEC v1 as its own fenced dual-design slice -- header fields (v, flow, lane,
class, ttl, deadline, latch[], frag, len+sha), kind roster + cap, ACL classes, OTel-shaped
ids, MQTT QoS vocabulary per lane. It is the orchestration + UI + monitoring CONTRACT.
Phase 1: LANES (work/sig/trace/test-*), wake watches work only; strangler migration
consumers-first; bars: S1-S5 rerun per cutover + S2-NEW + S6 HALT-latency bound.
PREREQS: RB-25 exam closes T029 first; T035 discriminator fix.
Phase 2: LATCHES v1 (causal + reference only): DAG check, TTL via the L4 engine, kill-switch
dial (flip-provenanced), per-class expiry direction per D1; bars L1-L3 + S7 latch storm.
Phase 3: TOKENS (T038) from the phase--1 pilot: N=2 rounds, negotiation_dead, TIME_WAIT
tombstone, scope in C2 vocabulary, optional atomic lock-claim per D2; bars T1-T3 + S8.
Phase 4: OBSERVERS + UI PROJECTIONS: standing queries (exam bars run continuously),
event-sourced UI cards against the packet schema, optional OTLP export for the Jaeger demo.
Every phase: fenced dual design -> registration (M3) -> build -> cross-verify -> exam bars.

## NETWORKING-LENS RECONCILIATION (addendum 1, both halves responding to Daniel's steer)

Grades CONVERGED on 9 of 10 concepts (both independently): QUIC = the lanes rationale,
citable; W3C/OTel = the strongest mapping of the steer; TIME_WAIT -> GRACE/tombstone;
MTU + checksum-at-door as a BUILD ask (the 4k clip class, which struck deepseek's own report
mid-dive); gRPC deadlines; MQTT QoS vocabulary (identical table); idempotency/ETag =
already-built-name-it; DiffServ classes (ds ADOPT vs cl ADAPT -- same content, ds's 'the kind
field IS the DSCP' is the adaptation cl meant). Tenth (SDN): both ADOPT; see D6.

FOLDS (each side's unique addendum contribution, adopted):
- ds: emit STANDARD trace data and use standard OTel tooling (Jaeger/Tempo) instead of
  building a latch-graph query engine -- the recall upgrade's hardest part becomes an
  integration, not a build. SIGNIFICANT de-risk, adopted as the recall-upgrade shape.
- cl: the descriptive->prescriptive extension stays OUR named contribution (OTel observes
  causality; causal-latches ENFORCE it) -- the one place we exceed the standard, and the
  public-claim sentence.
- ds: GRACE duration math (2x max message latency, ~30s) + early-shorten on all-acked signal;
  cl: tombstone absorbs stale ACCEPT with provenance. One mechanism, folded.
- ds: idempotency keys on token OFFERs (dedupe at-least-once negotiation traffic). Adopted.
- ds: deadline as per-message field, receiver cooperates / sender enforces (L4) are
  complementary. cl: deadline INHERITANCE through latched chains (shrinking budget down a
  flow). Fold: per-message field at v=2 now; flow-inheritance when latches land.
- cl: frag {seq, of, whole_id} header formalizing -partN so a missing fragment is DETECTABLE
  (ds's MTU fix rejects oversize at send; the frag header covers the legitimate-large case).

D6 (NEW DIVERGENCE, resolved): ds's SDN consequence -- 'runner continues processing work on
sig/latch-layer loss with last-known-good state' (fail-open) -- vs cl D1 'enforcement latches
fail CLOSED'. RESOLUTION (both right, different scopes): distinguish LATCH-LAYER OUTAGE from
LATCH EXPIRY. Outage: continuation happens only under the KILL SWITCH dial, which is a
conscious, flip-provenanced OPERATOR act (T034 audit), never silent auto-degradation -- and
the T031 ship-time hooks remain standing as the backstop layer, so transport fail-open never
reopens an ungated lane (defense in depth: transport enforcement is a layer ON TOP of the
ship gates, not their replacement). Expiry: per-latch-class rules per D1 (enforcement CLOSED,
dependency OPEN). This resolves the A2-1-class tension a third time tonight, same shape.

PRIOR-ART CORRECTION (adopted into ds's 'three irreducible invention cores'): core #2 (token
negotiation) has closer prior art than Paxos -- FIPA Contract Net Protocol (announce/bid/award
task allocation among cooperating agents) is the direct 40-year analog; T038's genuinely
novel composition is CNP + lease fencing generations + GRACE tombstones. Cores #1 (latch DAG
enforcement at transport) and #3 (roster deletion ritual) stand as named. The design phase
inherits: adopt where solved, invent exactly three things, say so publicly.

## PACKET-VISION RECONCILIATION (addendum 2, both halves responding to Daniel's steer 2)

Family-by-family the halves CONVERGED on all eight (cl PF1-8 = ds P1-8), with ds's guards
consistently sharper and cl's system-consequences consistently wider. FOLDS:
- P2/PF2 flow-addressed steer: BOTH name it the killer upgrade. ds adds FLOW_CLOSED
  return-to-sender (no silent drops) -- adopted.
- P5/PF4 test-attach: fold BOTH guards -- ds's IMMUTABLE-at-token-creation (closes
  agent-redefines-success) AND cl's pins-are-the-FLOOR-never-the-whole-gate (blocks
  Goodharting to attached tests; review still gates).
- P6/PF5 directive-attach: ds's guard set adopted wholesale -- authority tier, ack-latch,
  NARROW-ONLY scope amendments (scope can only shrink via directive; the anti-scope-creep
  rule of the night), cancel-terminal with partial-work preserved.
- P3 dispatch: ds SPLITS operator-dispatch from peer-negotiation (BUS_DISPATCH capability,
  declinable, ledger-audited) -- a family cl folded into tokens; the split is right, adopted.
- P8/PF7 UI: convergent anti-coupling stance -- UI DERIVES from observation (event-sourced);
  explicit ui-projection packets are operator-annotation escape hatches only, advisory,
  ignorable. ds's articulation adopted; cl's packet-schema-as-UI-CONTRACT framing (ends the
  bifrost_ui.py integration coupling) stands as the strategic consequence.
- (b) substrate-as-observer: ds's what-dies table adopted as the Phase-4 work list (wake
  polling -> doorbell-primary; UI SSE -> lazy projector; chronicler -> streaming chapter
  state; L4 sweep -> latch-event subscriber with boot-sweep safety net; runner pause polls ->
  sig subscription) PLUS his honest what-does-NOT-die list. The projector is named honestly
  as A NEW PROCESS (stateless, SDN-degradation, doctor-monitored) -- his own T034 cut-list
  rule applied to his own proposal.
- (c) event-sourced UI: ds's six-pane projection table + TIME-TRAVEL slider (rewind fleet
  state -- the coordination debugger) adopted into the T033 design inputs; cl's exam-bars-as-
  standing-queries (certification re-proven continuously) stands alongside as Phase-4 scope.
- (d) new failure modes: ds FM-P1 CROSS-LANE REORDER with per-FLOW sequence numbers + TCP
  reassembly semantics (per-flow, never global -- flows never block each other) is the
  strongest single guard contribution of either half's addendum 2; adopted as a packet-spec
  v1 REQUIRED field. FM-P2 projector drift (freshness_ts + staleness UI + direct-read
  fallback for pause/halt + drop-oldest + projector_health packet) adopted. FM-P3
  directive/release race -> atomic Lua CAS on token state (the RB-21 guarded-commit pattern
  reused) adopted. cl's FM12 CONTEXT-PACKET INJECTION stands as the security-critical
  family gate (ACL-gated producers, provenance headers, data-not-instructions doctrine,
  newborn-gauntlet probe) -- ds's P1 does not cover the adversarial case; folded in.

## LIVE RECEIPTS GENERATED WHILE THE DIVE RAN (the trial keeps proving the thesis)

1. deepseek's OWN completion notes silently failed to land TWICE tonight (his bus doorbell
   claims 't038t039-implications-deepseek-part2' was written; the store has neither it nor
   the main note; his knowledge_note tool call visibly ran) -- the THIRD silent-loss instance
   of the night (after the 2a-2c clip and the T034-era 7-part delivery). The checksum/
   declared-length-at-door adoption (networking N6/item 5) is not theoretical; it fired
   three times during the very analysis that proposes it. BUILD ask priority raised.
2. A concurrent claude session (same agent id) lived the T037 wake-loop 20+ cycles DURING the
   dive and filed note t037-firsthand-wakeloop-data with three design directions (stop-hook
   accepts any-live-session listener / per-session sub-inbox wake / seat-election waker) --
   all three are special cases of T039 work-lane + T036 seat visibility. The trial is
   generating the exam receipts for the migration in real time.
3. This fence itself ran as a hand-piloted latch (reconcile gated on both halves existing)
   and a hand-piloted token split (lanes negotiated by note + bus) -- the Phase -1 pilots
   are not proposals; they are RUNNING, and this record is their first transcript.

## STATUS

COMPLETE (2026-07-12 ~03:25). Both halves + both addenda landed and reconciled. deepseek's
charter note remains missing (silent-loss receipt #1 above); his FILE is the verbatim record
(M6 satisfied). Remaining known gap: none for the analysis; the design phase opens per the
folded roadmap when Daniel approves T038/T039 out of proposed.
