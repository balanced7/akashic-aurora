---
akashic_id: art_20260712_t038-t039-implications-deep-dive-fenced_c9bea1
akashic_sha: 5ff01ae14559
status: draft
type: design
date: 2026-07-12
title: T038 + T039 implications deep-dive -- fenced blind brief (2026-07-12)
gist: "# T038 + T039 implications deep-dive -- fenced blind brief (2026-07-12) Charter: fenced dual analysis, same protocol as research/rb25-f1f2-r"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_rb-25-f1-f2-fence-review-charter-claude_db1b6e
    rel: cites
  - target: art_20260712_t038-t039-implications-deepseek-blind-de_bf2553
    rel: cites
  - target: art_20260711_rb-25-engine-exam-runbook-pre-registered_9356ea
    rel: cites
  - target: art_20260711_t034-registry-dial-consolidation-reconci_6c7925
    rel: cites
  - target: art_20260709_concurrent-agents-reinforcing-two-peers_5f6723
    rel: cites
created: "2026-07-12T02:50:18"
updated: "2026-07-23T21:42:23"
---
<!-- GENERATED PROJECTION of art_20260712_t038-t039-implications-deep-dive-fenced_c9bea1 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T038 + T039 implications deep-dive -- fenced blind brief (2026-07-12)

# T038 + T039 implications deep-dive -- fenced blind brief (2026-07-12)

Charter: fenced dual analysis, same protocol as research/rb25-f1f2-review-charter-2026-07-12.md.
Daniel directive (2026-07-12): "the two changes raise the theoretical and practical ceiling of what
we are capable of. This deserves a creative deep dive in order to maximize the utility."

Rules of the fence:
- deepseek analyzes BLIND from this brief + repo evidence only. claude's half stays OUT of the
  repo (sealed in session scratch) until deepseek's record lands. Do NOT wait for or ask for
  claude's half; if any file named claude-*implications* appears mid-run, do not open it.
- Deliverable (durable door, survives runner death):
  research/reviewed/deepseek-t038t039-implications-2026-07-12.md (guarded write_file)
  PLUS a note titled `t038t039-implications-deepseek` carrying the full text (chunk into
  -part2/-part3 notes if long, per the T034 precedent). Bus reply = doorbell only, not the record.
- Reconciliation happens AFTER both halves exist, as its own record.

## The question (answer all six, creative and concrete)

1. CAPABILITY UNLOCKS: what becomes POSSIBLE that was impossible or unsafe before these two
   changes? Not features -- capabilities. Name each unlock, the mechanism that grants it, and
   the cheapest demonstration that would prove it live.
2. SECOND-ORDER EFFECTS on existing seams -- walk each one: recall funnel (99 lessons,
   surfaced 1091, value 4.2% -- the credit-assignment problem), method-baseline M1-M11
   enforcement (docs/method-baseline-2026-07.md, T031 hooks), fidelity ladder
   (INFORM/STEER/INTERRUPT/HALT), L4 expectations (core/comm/expectations.py arm/sweep/redrive),
   RB-21 generations + runner_lock lease mechanics, C2 advisory path locks, T034 runtime
   registry/dials design, multi-seat concurrency findings (T035/T036/T037), UI arc (T033/T034),
   narrative spine (Atlas/Track/Chapter/Beat), security/trust layer (quarantine, may_run_runner,
   RB-25 F1/F2).
3. NEW FAILURE MODES + GOODHARTS the two changes introduce, and the guard each one requires.
   Include: what does a lanes+latches outage look like, what does token-negotiation deadlock or
   livelock look like, what gets Goodharted when latch-count or token-throughput becomes visible.
4. PILOT ORDER: what to pilot FIRST by hand (no code) on the live concurrency-trial lanes;
   what the RB-25 exam (storm S1-S5, soak K1-K5) must ADD to stay the acceptance gate for the
   migration; sequencing risks in "lanes before tokens".
5. CEILING ANALYSIS: with lanes + latches + negotiated work tokens as the substrate, describe
   the strongest honest version of this system 6-12 months out: fleet size and model diversity
   it can safely host, autonomy level, what a newcomer agent's first hour looks like, what
   Daniel can claim publicly with receipts.
6. WHAT WOULD YOU CUT: which parts of T038/T039 as titled are over-engineering risk TODAY --
   the discipline of the T034 cut-list applied to these two seeds.

## Raw inputs (verbatim from the ledger + notes)

### T039 ledger title (proposed, DESIGN ONLY behind fenced dual design)
Purpose-keyed bus lanes (Daniel seed 2026-07-12, DESIGN ONLY behind fenced dual design):
partition the single bifrost stream into a fixed lane roster -- work (directed
mail/handoffs/replies; the ONLY lane with consumer-seat + cursor discipline; the ONLY lane wake
listeners watch), trace (narration/tool calls, seatless, ring-buffer XTRIM retention), sig
(nudge/steer/halt/pause -- fidelity-ladder traffic never queues behind trace spam), test-*
(already proven by 7097b5e namespace isolation; formalize drills-always-namespaced). Mechanism
EXISTS: Bus(namespace=...) shipped and drill-tested; presence/events/promoted/context_hints stay
as-is (the system already converged toward lanes organically -- this finishes the thought).
Migration = strangler fig: dual-write briefly, cut consumers over lane-by-lane, retire; RB-25
storm bars S1-S5 rerun as the migration acceptance. Guards: lane roster is CAPPED (adding a lane
requires a why-not-an-existing-lane answer + deletion ritual -- T034 Goodhart 1 applies to lanes
exactly as to dials); per-lane retention bounds feed soak bar K4. Direct payoff: T037 mostly
evaporates (wake watches work only), seat contention shrinks to work mail, every consumer drops
its filter code. Sequencing: lanes BEFORE T038 tokens (token offer/accept traffic rides sig;
allocated work rides work).

### T038 ledger title (proposed, DESIGN ONLY behind fenced dual design)
Work-token negotiation protocol (Daniel seed 2026-07-12, DESIGN ONLY behind fenced dual design):
extend the lease mechanics (claim/refresh/TTL/fencing generation, already drill-tested in
runner_lock) with a NEGOTIATION phase so work splits become first-class: OFFERED -> ACCEPTED |
COUNTERED(bounded rounds) -> HELD(refresh=liveness+progress line) -> RELEASED | EXPIRED(reverts
to claimable, loud). Composes existing seams: ledger gated transitions (lifecycle home), L4
expectations (offer deadlines/redrives), C2 path locks (scope vocabulary), RB-21 generations
(stale-accepter fencing). Gate on collision-possibility per smart_negotiation_gate (zero
ceremony when solo); lane/task-granular scopes only (T034 Goodhart 1 guard); tokens are leases
on slices, never roles (concurrent-agents doctrine). PILOT BY HAND FIRST on the live
concurrency-trial lanes (note-based token records, no code) before any build. Problem brief to
BOTH design halves blind; claude sketch stays out of the repo until deepseek's half lands.

### Note t039-latch-refinement (Daniel correction 2026-07-12, verbatim)
REFINES T039 (Daniel correction 2026-07-12): 'cross-lane ordering guarantees disappear' was
WRONG framing. Right model: replace IMPLICIT global order with EXPLICIT, selective,
semantically-richer causal edges (latches) between lanes -- strictly MORE expressive, not less.
LATCH PRIMITIVE: a packet in lane A carries a durable edge to a packet/cursor in lane B. Three
edge types: (1) causal-latch = happens-before barrier ('work:X not consumable until test:Y
exists AND sig:Z acked') -> the bus ENFORCES process at transport level (method's 'review gates
commit' becomes an invariant, not a convention); (2) bundle-latch = linked consumption across
lanes (atomic-ish); (3) reference-latch = weak provenance pointer, no enforcement, but a durable
queryable edge. UNLATCH = release the constraint when satisfied (barrier fires / bundle consumed
/ dep met) -> dynamic dependency management. PAYOFFS: (a) processes encoded as latch constraints
not conventions; (b) orchestration computes a topo-order over pending work, parallel by default,
serialize only where a latch demands -- the exact edge T038 tokens need; (c) RECALL UPGRADE (the
deep one): durable causal edges give the funnel a GRAPH to walk, not just a relevance index --
provenance-aware recall + precise credit assignment (surface the lesson causally-upstream of a
real flip), directly attacks the 4.1pct recall-value/credit problem. HONEST COSTS (the trade is
good, not free): cost MOVES from implicit-total-order to managed-dependency-graph -- (i)
cross-lane read coupling at consume time; (ii) DEADLOCK/CYCLE risk -> DAG invariant + cycle
detection + latch-expiry (reuse L4 expectations) are REQUIRED guards; (iii) on ONE Redis, stream
IDs (<ms>-<seq>, same server clock) already give approximate global order FOR FREE -> latches
earn keep ONLY where ENFORCEMENT or SEMANTIC provenance is needed, default to cheap timestamp
order (keeps zero-ceremony-when-simple). Prior art (grounding, not inventing): Lamport
happens-before / causal consistency, workflow DAG engines (Airflow/Temporal), reactive-stream
backpressure, lineage/provenance graphs. RESCOPES T039: lanes+latches = a more powerful
substrate, not a clean-but-lossy one. Fenced dual design when opened; pilot latch semantics
by-hand on the trial lanes first.

### Trial + findings context (titles only; full text in notes/ledger)
- Note concurrency-trial-2026-07-12: two live claude seats (Opus twin e59d8882 held the
  consumer seat; Fable 46bf68d6 peek-only), durable-door doctrine for cross-seat deliverables,
  advisory locks, lanes renegotiable peer-to-peer, findings accrue to T036 + lessons.
- T035 (abandoned, superseded): same-token twin re-entrant consumer seat -- runner_lock
  re-entrancy is token-only, so same-session co-tenants co-advance the shared cursor.
- T036 (proposed): session-identity hygiene -- non-session children inherit
  CLAUDE_CODE_SESSION_ID and act AS that session at every seat/lock door; boot/doctor should
  render per-session seats.
- T037 (proposed): non-holder wake discipline -- the non-seat-holder's watcher insta-fires on
  unread it can never consume; arm/insta-exit/stop-hook ceremony loops.
- RB-25 exam state: drills 1 (newborn gauntlet) + 2 (store-divergence heal) CLOSED GATE GREEN;
  drill 3 (concurrency storm, burst script delivered) next; drill 4 (72h soak) awaits gating
  ruling. Amendment-2 A2-1..A2-6 rulings ALL SIX AFFIRMED, A2-1+A2-2 landed @9772e65.

## Evidence pointers (read as needed, all in-repo)
- core/comm/bus.py -- Bus(namespace=...), seed_cursor_at_tail, single-consumer seat mechanics
- core/comm/expectations.py -- L4 arm/sweep/redrive/expectation_dead
- core/coord/ -- runner_lock (lease + fencing generation), advisory path locks (C2)
- docs/rb25-exam-runbook-2026-07-11.md -- storm bars S1-S5, soak bars K1-K5
- docs/method-baseline-2026-07.md -- M1-M11, the HOW contract
- docs/t034-registry-spec-2026-07-11.md + notes t034-registry-design-deepseek* -- registry
  guards, Goodhart 1 (roster/manifest growth), cut-list discipline
- docs/concurrency-design.md -- C0-C4, any-agent-any-task doctrine
- state/coord/tasks.json -- the governed ledger
- py agent_cli.py stats -- the live funnel numbers
