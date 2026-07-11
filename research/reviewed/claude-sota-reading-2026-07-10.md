# Claude's SOTA deep-read assessment -- robustness program build implications

Status: fenced half (deepseek reads the same cache independently; reconcile on his reply).
Sources: research/sources-cache/* (neutral extractions) + ShardStore SOSP 2021 primary PDF
(pypdf text pass over the conformance/minimization sections).
Scope: Daniel's directive -- own assessment + interpretation, feeding the L1 build that
begins after reconciliation.

## 1. Verdict changes to the map after reading primary material

- P3 (leases/fencing) SHARPENED: Kleppmann's full text makes the mechanism non-negotiable
  in a way the summary softened: the token must be validated AT THE RESOURCE on EVERY
  write, and the delayed writer must be REFUSED (loudly), not merely raced. Checking lock
  expiry before writing is explicitly insufficient (pause can land between check and
  write). Consequence: L1b is not "carry a generation" -- it is "the cursor write itself
  is conditional on generation", which on Redis means a guarded write (Lua or
  WATCH/MULTI), not a plain HSET. Also his efficiency-vs-correctness split names our
  situation exactly: the runner lock is a CORRECTNESS lock (cursor integrity), so the
  fencing upgrade is mandatory, while single-instance Redis (not Redlock, not consensus)
  remains the right substrate at our scale -- matching his own recommendation shape.
- P1 (delivery) CONFIRMED with one precision: Kafka's at-least-once consumer is
  process-THEN-commit with the duplicate window explicitly between processing and
  commit. Batch commits widen it; per-record commits narrow it. RB-26's blind-converged
  per-message advance is the narrow variant -- keep it, and the drill must cover the
  "crash after reply, before advance" duplicate case as EXPECTED behavior (assert
  dedup-by-ack, not absence of redelivery).
- P4 (crash-only) SHARPENED: Candea-Fox's lease rule generalizes beyond the runner lock:
  EVERY held resource wants a TTL. Our pause flag (L5) and any future claim-style state
  should carry leases. Their caveat list adds one honest cost we should surface in the
  tier doc: crash-only recovery obscures root causes -- which is exactly why RB-28 keeps
  the launcher's exit-CLASSIFICATION and why runner last-words (line-buffered logs)
  matter; crash-only without forensics is anti-debuggability.
- P5 (fault injection) ADJUSTED by the FDB piece: the portable elements for a
  non-deterministic Python runtime are (a) seeded PRNG for every injection DECISION,
  (b) CHECK-phase invariants after chaos, (c) knob randomization (our env tunables --
  timeouts, ring sizes, thresholds -- randomized per drill run within bounds, logged
  with the seed), (d) BUGGIFY's shrunken-timeout trick: run drills with REPLY_TIMEOUT_SEC
  and wedge thresholds cranked DOWN so timeout paths actually exercise. NOT portable:
  time compression, deterministic scheduling, whole-cluster sim. The five-window kill
  harness stays the core; knob randomization is a cheap multiplier on it.
- P6 (PBT/models) EXTENDED by the primary PDF, three practices the summary missed:
  (a) TRUST DEFAULT RANDOMNESS -- introduce bias only with quantitative evidence it
  helps ("biasing risks baking our assumptions into the tests"); start the conformance
  machine unbiased, add bias only when coverage data demands it.
  (b) DESIGN FOR MINIMIZATION -- keep the machine deterministic; inject a controllable
  clock (no naked time.time() in the model path) so shrunk counterexamples replay.
  (c) COVERAGE-EROSION GUARD -- ShardStore tunes the alphabet when the interface grows.
  Our version can be structural: derive/check the state machine's rule set against the
  Store ABC's abstract methods, so a NEW Store verb without a conformance rule FAILS
  the suite. (This week's srem addition is the live example that would have tripped it.)
  Also their reference-model-as-mock insight: our existing FakeQuery/FakeLog test fakes
  should converge INTO the reference models -- one artifact, two jobs.
- P2 (failure detection): Akka's practical parameters transfer as DESIGN VOCABULARY even
  while we defer phi: our fixed wedge threshold is "threshold"; an
  acceptable-heartbeat-pause equivalent (grace for known-long operations, set per phase)
  is a cheaper F2 mitigation than full phi-accrual -- adopt as a per-phase grace map in
  L2 if the soak shows false wedges, BEFORE reaching for phi.
- Methodology (Knight-Leveson + Regehr) REFINED: correlation tracks SHARED STRUCTURE,
  not the mere fact of two analysts. Regehr's compilers diverged deeply below the spec
  (different IRs) and showed zero shared wrong results across ~300 bugs. Consequence for
  our dual passes: fence is necessary but structure-diversity is the multiplier --
  assign the two passes DIFFERENT ENTRY POINTS (one from code-forward, one from
  spec/docs-forward; or one designs from the failure taxonomy, one from the interface),
  so the shared substrate is smaller. Cheap process upgrade; propose to deepseek.

## 2. L1 (RB-26) + L1b build spec -- my concrete half

- Runner loop: bus.wait(advance=False); for each message, handle via _process_one then
  advance_past(m, generation) -- including immediately for fold/filtered kinds (they are
  handled by folding/ignoring; only a REPLY-owed message defers its advance until after
  the reply send).
- Bus.advance_past(msg_id, *, generation): guarded conditional write of the cursor hash
  field: succeeds iff generation >= stored generation AND msg_id > stored cursor
  (monotone in both). Implementation: single Lua script (EVAL) on the cursor key --
  atomic, no WATCH loop; stores (cursor, generation) side by side. Refusal RETURNS a
  loud status the runner logs and treats as stand-down (a fenced-out runner must stop
  consuming, mirroring the lock-loss path).
- runner_lock: acquisition INCRs bifrost:lockgen:<agent> and stores the generation in
  the lock value; heartbeat carries it; holder() exposes it. The generation is the
  fencing token; it survives lock expiry correctly because the NEXT acquisition INCRs.
- Dedup on redelivery: for kind=handoff, before answering, acks_for([id]) -- if this
  agent already acked, skip with a log line (idempotent receiver); other kinds tolerate
  duplicate replies (at-least-once accepted).
- Kill-window harness (drill = acceptance): killpoint(name) helper in the runner --
  os._exit(137) iff AKASHIC_KILLPOINT == name; five named points per the reconciled
  taxonomy windows. Harness (pytest, marked slow): for each window: spawn runner
  subprocess with the killpoint armed + a queued handoff -> assert death at the window
  -> relaunch unarmed -> assert exactly-one reply, ack present, cursor == final id,
  no duplicate ack. Seeded knob randomization round (BUGGIFY-lite) as a second pass.
- Out of scope for L1 (named): batch-boundary redelivery beyond per-message advance;
  sender-side redrive (L4); progress pulse (L2).

## 3. Launcher/restart implications (Candea-Fox -> L3)

No graceful-drain path gets built; restart IS recovery (already true). Add: exit
classification stays load-bearing (crash-only's debuggability cost is paid by forensics);
restart policy gains bounded exponential backoff with jitter to avoid crash-loop
hammering; every runner-held resource audited for TTL (lock: yes; pause: L5 adds it;
watcher seat: yes).

## 4. What I did NOT import (and why)

- Consumer groups / XACK (both halves already rejected; single consumer per inbox).
- Full deterministic simulation (no deterministic scheduler in Python; the five-window
  harness + seeded knobs capture the affordable 80%).
- phi-accrual now (per-phase grace map first; phi if grace fails).
- TLA+/Loom/Shuttle-class concurrency model checking (protocol is 3 ops; Hypothesis
  stateful + kill windows cover the reachable space at our scale).

## 5. Reconciliation asks for deepseek's half

Where I most expect/want his divergence: (a) the Lua-guarded cursor write vs a simpler
last-writer-wins-with-audit; (b) whether fold/filtered kinds should advance immediately
or also defer; (c) the structure-diversity process tweak; (d) whether the ack-dedup
check belongs in the runner or inside ack() itself.
