---
akashic_id: art_20260701_robustness-sota-map-problem-types-owning_544d00
akashic_sha: 55bca77a1de4
status: current
type: design
date: 2026-07-01
title: "Robustness SOTA map -- problem types, owning fields, adopted practice per slice"
gist: "Class: reference Governs: practice adoption for T030 L1-L5 and remaining T029 waves (RB-8..RB-25). Method: claude web-verified pass + deepse"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T22:56:13"
updated: "2026-07-10T22:56:13"
---
<!-- GENERATED PROJECTION of art_20260701_robustness-sota-map-problem-types-owning_544d00 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Robustness SOTA map -- problem types, owning fields, adopted practice per slice

Class: reference
Governs: practice adoption for T030 L1-L5 and remaining T029 waves (RB-8..RB-25).
Method: claude web-verified pass + deepseek blind classification (fenced, from training
knowledge), reconciled. Evidence tags: [V] = web-verified this date; [K] = well-established
knowledge, not separately verified; [D] = deepseek blind pass (folded on arrival).
Daniel's directive 2026-07-10: "identify the logic types and problem types... research the
fields that best tackle these... integrate the state of the art per slice and logic type."

## 1. Problem-type taxonomy -> owning field -> SOTA -> our verdict

### P1. Message delivery semantics  (T030 L1 / RB-26; incident class A)
Formal type: at-most-once vs at-least-once delivery; the consume-vs-process commit point.
Field: distributed messaging / stream processing.
SOTA [V]: exactly-once DELIVERY is not achievable end-to-end; industry consensus is
at-least-once delivery + IDEMPOTENT CONSUMER = "exactly-once EFFECT". Kafka: disable
auto-commit, commit offsets only AFTER successful processing; idempotency key embedded in
the message; dedup registry consulted before side effects. (Confluent delivery-semantics
docs; idempotent-consumer pattern literature.)
Verdict: ADOPT wholesale -- L1's blind-converged design IS this pattern verbatim
(advance-after-handle = commit-after-processing; bus msg id = idempotency key; the P6 ack
tier = the dedup registry for asks). REJECT Kafka-style transactions and Redis consumer
groups (both halves already rejected them: one-runner-per-agent needs no group rebalance).
Design language upgrade only: name the pattern in the code.

### P2. Failure detection  (T030 L2 / RB-27; incident finding "presence lies")
Formal type: unreliable failure detectors; liveness vs readiness; heartbeat vs progress.
Field: distributed systems fault tolerance + operations practice.
SOTA: [K] Kubernetes separates liveness (process up) from readiness (able to serve) --
our presence-vs-progress split is exactly this distinction. [K] systemd's sd_notify
WATCHDOG keepalive = the intra-phase progress pulse deepseek designed. [V] Adaptive
thresholds: the phi-accrual failure detector (Hayashibara, Defago, Yared, Katayama;
shipped in Akka and, modified, Cassandra) replaces binary timeout with a suspicion level
fitted to observed inter-arrival history. [D] Theory floor: FLP impossibility (Fischer/
Lynch/Paterson 1985) + Chandra-Toueg unreliable failure detectors (1996) -- perfect
detection is impossible in async systems; every detector we build is a heuristic with
named false-positive/negative trade-offs, which is WHY the pulse (ground truth) and the
threshold (suspicion) stay separate. [D] The doctor half is SRE observability synthesis:
whitebox-vs-blackbox monitoring (Borgmon/SRE book), RED/USE/Four-Golden-Signals as the
canonical health-summary frames; our WEDGED/STALLED/MAIL-LOSS states are a fleet-domain
equivalent; push-not-pull is the right inversion at N=2 agents.
Verdict: ADOPT the k8s/systemd framing now (L2 as designed). ADAPT-LATER phi-accrual:
keep the fixed 300s wedge threshold until the soak shows false wedges on legitimately
long calls (F2); phi is the named upgrade path, not a v1 build. (Frugality: adaptive
stats for a 2-agent fleet is premature.)

### P3. Leases and mutual exclusion  (runner_lock; failure mode E1; L5)
Formal type: lease-based mutual exclusion; the paused-holder / expired-lease hazard.
Field: distributed coordination.
SOTA [V]: Kleppmann, "How to do distributed locking" (2016): a TTL lease WITHOUT a
fencing token is unsafe when correctness depends on it -- an expired-but-still-running
holder can act after a successor takes over. The fix is a MONOTONIC FENCING TOKEN issued
at acquisition and CHECKED AT THE RESOURCE, not at the lock. (His Redlock critique;
consensus systems only when the fleet outgrows one Redis.)
Verdict: ADAPT -- our E1 (lock-TTL overlap window double-consume) is the textbook unfenced
lease. Import the token, not a consensus system: runner_lock issues a generation counter;
the CURSOR WRITE (the resource that matters) carries it and a stale generation is refused.
Folds into L1's cursor-advance change as L1b, subject to deepseek design-review since it
extends the blind-converged design. REJECT ZooKeeper/etcd (fleet of two, one box).

### P4. Crash consistency + recovery design  (L1/L3; FileLedger/FileStore write paths)
Formal type: crash-only design; recovery path == startup path; atomic persistence.
Field: systems research / storage.
SOTA: [V] Crash-only software (Candea & Fox, HotOS IX 2003): the only stop is a crash,
the only start is recovery -- no separate graceful-shutdown logic to get wrong. [K] File
crash-consistency testing (ALICE / CrashMonkey lineage): the tmp-write + atomic-rename
pattern our FileLedger/FileStore already use is the standard primitive; the test question
is what survives a kill BETWEEN the write and the rename.
Verdict: ADOPT crash-only as the L1/L3 design stance (redelivery IS the startup path; the
launcher restarts rather than drains). The crash-point sweep asserts it. Current design
MATCHES SOTA already (os.replace); the sweep adds the missing proof.

### P5. Fault injection at scale  (the crash-point sweep; RB-25 drills)
Formal type: systematic fault injection; deterministic simulation testing (DST).
Field: distributed-systems testing.
SOTA [V]: FoundationDB pioneered DST -- run the whole system in a deterministic simulator,
BUGGIFY macros bias fault points toward danger (each fires ~25% deterministically);
TigerBeetle runs ~2 millennia of simulated time/day; Antithesis packages the approach as
a deterministic hypervisor; WarpStream applied it SaaS-wide; Jepsen is the black-box
cousin (real cluster + nemesis faults + linearizability checking).
Verdict: ADAPT, consciously scoped -- full DST needs deterministic scheduling we do not
have (Python threads + Redis). Our version: an in-process kill-point registry
(AKASHIC_KILLPOINT env: named points at every IO boundary of the consume->outcome
pipeline; the drill harness iterates points x seeds and asserts the L1 invariant each
time). BUGGIFY's lesson we keep: bias injection toward the dangerous windows, make each
run seed-reproducible. REJECT hypervisor-level DST (Antithesis-class) as out of budget --
named so the ceiling is visible. [D] Upgrade path if the sweep matures: lineage-driven
fault injection (Molly, Alvaro et al. 2015) searches for the MINIMAL fault combination
that violates an invariant instead of enumerating points -- noted, not built. [D] The
RB-25 drills are Netflix Game-Day methodology (planned chaos with pre-defined success
criteria), correctly run in dev not prod for a solo-operator system; RB-22's honest
scope: we pin the invariants we actually claim (no missed wakes, cursor correctness),
we do NOT build Jepsen linearizability checking for a bus that never promised it.

### P6. Property-based + model-based testing  (Wave 3; Store/Ledger/Index)
Formal type: executable specifications; stateful property testing; differential testing.
Field: software correctness engineering.
SOTA [V]: Amazon S3 ShardStore (Bornholt et al., SOSP 2021, "lightweight formal methods"):
for each component an EXECUTABLE REFERENCE MODEL (radically simpler implementation of the
same interface), property-tested against the real one, plus failure injection; caught 16
issues pre-production; the umbrella practice at AWS pairs this with TLA+/P for protocol
sketches (CACM "Systems Correctness Practices at AWS"). Python tooling: Hypothesis
RuleBasedStateMachine -- rules + invariants + automatic shrinking of failing op sequences.
Verdict: ADOPT two concrete instances, both frugal:
  (a) Store conformance suite -- ONE Hypothesis state machine driving the Store interface
      (set/get/sadd/srem/zadd/cas/...) against a dict-based reference model, run against
      FileStore AND RedisStore AND HybridStore. This is differential testing pointed
      straight at our standing dual-write divergence risk.
  (b) Note-supersession model -- invariant "exactly one active note per title" as a
      Hypothesis stateful test over re-note/retire/supersede ops (RB-8/9/10 acceptance
      generalized beyond hand-picked cases).
REJECT TLA+ for now: the cursor protocol is 3 operations; the Hypothesis machine + kill
sweep cover its state space at our scale. Named as the upgrade if the protocol grows.

### P7. Test-suite adequacy  (are the pins real?)
Formal type: mutation analysis.
Field: software testing research (DeMillo/Lipton/Sayward lineage; industrialized at
Google [K]).
SOTA [V]: mutmut is the maintained Python mutation tool; mutation score = fraction of
seeded defects the suite kills; surviving mutants mark decorative tests.
Verdict: ADOPT, scoped to the load-bearing modules only (core/trust, core/comm,
core/events, the guards) -- a full-repo run is noise + hours; the trust boundary is where
a decorative pin is dangerous.

### P8. Runtime verification  (invariant auditor + soak; fleet doctor)
Formal type: online monitoring of safety invariants; SLO-style detection.
Field: runtime verification / production monitoring practice.
SOTA: [K] monitors derived from explicit invariants, evaluated continuously against the
live system (the RV field's core move); ShardStore's "continuous validation" is the
storage-flavored version [V].
Verdict: ADOPT -- the fleet doctor grows an INVARIANT SET evaluated on a timer:
  every directed salient ask acked-or-flagged within threshold; byref members subset of
  tindex ids; exactly one active note per title; per-agent cursor <= newest stream id;
  CAS'd keys agree file-vs-redis; no lock held by a dead pid; no leftover pause older
  than its TTL.
The 72h soak (RB-25) runs WITH the auditor -- soak time becomes detection time.

### P9. Retry + request-reply over async messaging  (L4 / RB-29-sender)
Formal type: correlation, timeout, retry, dead-lettering.
Field: enterprise integration patterns (Hohpe & Woolf) [K]; cloud retry practice [K].
SOTA: correlation identifier on request and reply; reply timeout at the sender;
exponential backoff WITH JITTER on redrive; bounded attempts then dead-letter to a human
surface. Our P6 UNHANDLED flag IS the dead-letter surface, at the wrong timescale.
Verdict: ADOPT into L4: bifrost-send --expect-reply-within grows backoff+jitter and a
bounded redrive count (deepseek's 3), terminal state = loud UNHANDLED escalation now
(not 2h). Two-lane verb confusion (H6) is EIP's messaging-gateway ambiguity -- fix stays
doc-level until it bites again (unchanged).

### P10. Unicode identity + canonicalization  (RB-9; router confusables precedent)
Formal type: canonical equivalence; visual spoofing.
Field: Unicode security.
SOTA [K]: UTS #15 normalization (NFC at the write door -- exactly RB-9's design) and
UTS #39 confusable skeletons for spoof detection (repo precedent: test_router_confusables).
Verdict: ADOPT as designed; RB-9 already matches SOTA. Add UTS #39 skeleton comparison to
the title-match path only if the confusables test corpus shows a real collision.

### P11. Time and ordering  (RB-12 deterministic tiebreak; RB-14 staleness)
Formal type: total ordering without synchronized clocks; clock-skew hygiene.
Field: distributed systems time.
SOTA [K]: Lamport clocks / hybrid logical clocks for cross-node causality; total order via
(timestamp, unique-id) lexicographic tiebreak for single-writer streams; treat wall-clock
as untrusted input (undated/future-dated = its own bucket, never silently clamped).
Verdict: RB-12/RB-14 as designed MATCH the practice (tiebreak + flag-don't-clamp).
REJECT HLC -- one box, one conductor; named as the multi-node upgrade path.

### P12. Adversarial retrieval  (S5 incident; RB-17..RB-20 lookback quality)
Formal type: lexical relevance under keyword stuffing; benchmark rot.
Field: information retrieval.
SOTA [K]: our per-call IDF + length-saturation dampener is a hand-rolled member of the
BM25 family (IDF x saturating TF is BM25's exact shape) -- the v1 lexical SOTA baseline;
embeddings remain the named v2. Keyword-density gaming is the IR spam/adversarial
sub-field; periodic probe re-registration (RB-20) is standard benchmark hygiene against
overfitting/rot.
Verdict: current design MATCHES the lexical SOTA tier; name BM25 at the relevance seam so
the next reader recognizes it. No new build.

### P13. Fuzzing the parse surface  (hostile-input week)
Formal type: negative/malformed-input testing; grammar + coverage-guided fuzzing.
Field: security testing.
SOTA [K]: coverage-guided fuzzers (Atheris for Python) for parser-shaped code; for our
scale, adversarial grammar-driven cases from a REAL second identity (deepseek) cover the
trust-adjacent surface better than blind byte fuzzing.
Verdict: ADAPT -- deepseek hostile week as planned; Atheris named as the escalation if a
parser ever takes untrusted external input (today all senders are trusted ids).

## 2. Methodology audit (our process against the evidence)

- Pre-registered kill conditions == pre-registration in experimental science [K]:
  keeps us from tuning the test to the build. Already our discipline; keep. [D] Named
  anchors from the blind pass: Popperian falsification; clinical-trial pre-registration
  (FDAAA 2007); NeurIPS ML pre-registration (Pineau et al. 2020). The RB-4 strict-xfail
  flip is the pattern executed exactly.
- [D] RB-23's labeled endings corpus is a GLUE-style fixed human-labeled benchmark;
  operational addition adopted: track the BOUNCE RATE over time -- a rising rate means
  the promise-shape heuristic needs expansion, a low stable rate means it is done.
- Blind dual analysis -- RECONCILED verdict (both halves cited Knight & Leveson 1986
  independently [V][D]): convergence is a GATE, not a PROOF. The honest framing is
  FENCED, not "independent" -- we share the evidence base (same code, same forensics,
  same onboarding), we do not share the diagnosis. What convergence eliminates: "one
  reviewer missed the obvious." What it cannot eliminate: "the shared code/spec was the
  blind spot" (the Knight-Leveson trap -- correlated errors track SPEC ambiguity, and
  diagnosis-convergence from shared evidence is weaker than design-convergence).
  DIVERGENCE is the real signal: pause and reconcile, never pick a winner. The KILL
  DRILL stays the arbiter above any agreement. [D adds: second-opinion protocols in
  clinical medicine and aviation CRM are the human-factors lineage of the same rule.]
- Live-exercise-after-ship found 2 real bugs tonight that hermetic pins missed; this is
  ShardStore's "test against the real component" instinct [V]. Codify: every slice's
  close includes driving the real door verbs on the live store.

## 3. Integration deltas (what actually changes per slice)

  L1  (RB-26)  Name = idempotent consumer / commit-after-processing. No design change
               (blind-converged design already matches SOTA). ADD L1b: fencing token on
               the cursor write (P3) -- deepseek design-review gates it as a design delta.
               Drill harness = kill-point registry (P5), seed-reproducible, RECONCILED
               scope: the FIVE critical windows from the taxonomy (post-consume/pre-
               process; post-phase-flip/pre-send; between batch messages; post-process/
               pre-advance; post-reply/pre-ack) via named env-flag injection points --
               reproducible logical injection over random kill timing (SQLite's crash
               harness scaled to our loop; full-line instrumentation rejected as fragile).
  L2  (RB-27)  Pulse = watchdog-keepalive; doctor = liveness/readiness split + the P8
               invariant set. Fixed threshold now; phi-accrual named for the F2 upgrade.
  L3  (RB-28)  Launcher = supervision with restart-backoff+jitter; crash-only stance --
               no graceful-drain path built, restart is recovery.
  L4  (RB-29)  Correlation id + backoff-with-jitter + bounded redrive + loud dead-letter.
  L5  (RB-30)  Pause TTL + provenance (lease hygiene, P3 family); B2 stand-down after N
               dead beats.
  W3  (RB-8..12)  Add the Hypothesis suite, RECONCILED to five day-sized targets:
               (a) Store conformance differential vs a dict reference model, all three
               backends [claude/ShardStore]; (b) note-supersession one-active-per-title
               model [both halves]; (c) cursor monotonicity under random wait/inbox
               sequences [deepseek]; (d) delivery ordering under random direct+broadcast
               interleavings [deepseek]; (e) EventIndex trim invariance -- post-trim
               count==maxlen and events_for_ref returns only survivors [deepseek].
               Blanket suite conversion REJECTED (both halves). CAS design unchanged.
  W4  (RB-13..16) unchanged (render/clock discipline already matches P11).
  W5  (RB-17..20) name BM25 at the seam; no new build (P12).
  W6  (RB-21..25) soak runs WITH the P8 auditor; storm drills gain seeded determinism
               where feasible (P5).
  X1  (new, small) RECONCILED down from a scoped mutmut run to a ONE-SHOT hand-picked
               guard-mutation pass (~8 mutations, deepseek's list): flip RB-1's
               frm=="conductor", RB-2's addressee check, RB-4's dangling filter,
               RB-26's advance flag (etc.) -- each pin MUST fail; a survivor = a
               decorative pin = new pin-work. Run once before the liveness tier ships;
               full-suite mutation in CI rejected (hours of noise). Anchors: DeMillo/
               Lipton/Sayward 1978; Just et al. FSE 2014 (mutants proxy real faults).
  X2  (new, small) hostile-input week refined [D]: schema fuzzing (malformed JSON,
               missing fields, NUL, emoji storms), interleaving fuzzing (two writers on
               one cursor key), timing fuzzing (random delays at the seams) -- from his
               real identity; coverage-guided fuzzers (AFL++/Atheris lineage) named as
               the escalation only if untrusted external input ever arrives.

## 4. Sources (web-verified this date)

- Confluent, "Message Delivery Guarantees" + exactly-once semantics posts (Kafka EOS,
  idempotent consumer, commit-after-processing).
- Hayashibara, Defago, Yared, Katayama, "The phi accrual failure detector"; Akka failure
  detector docs; Cassandra usage.
- Kleppmann, "How to do distributed locking" (2016) -- fencing tokens, Redlock critique.
- FoundationDB simulation framework write-ups; Antithesis docs; TigerBeetle DST/VOPR;
  WarpStream DST post; asatarin/testing-distributed-systems index.
- Candea & Fox, "Crash-Only Software", HotOS IX (2003).
- Knight & Leveson, "An Experimental Evaluation of the Assumption of Independence in
  Multiversion Programming" (1986).
- Bornholt et al., "Using Lightweight Formal Methods to Validate a Key-Value Storage
  Node in Amazon S3", SOSP 2021; ACM Queue/CACM "Systems Correctness Practices at AWS".
- Hypothesis stateful-testing docs (RuleBasedStateMachine); mutmut (boxed/mutmut).
