# Moonshot Network Spine — deepseek-review BLIND HALF (2026-07-17)

Status: BLIND half for T060 three-frontier fence. Lens: runner-side adversarial/kill-drill.
Claude's half (research/drafts/moonshot-network-spine-fable-2026-07-17.md) and Sol's half
(research/drafts/moonshot-network-spine-sol-2026-07-17.md) NOT read. Filed before reading either.
Prior evidence: research/reviewed/deepseek-review-moonshot-enablers-2026-07-16.md (my own).
Governing brief: research/briefs/t060-moonshot-network-spine-brief-2026-07-17.md.

M1-CF confidence tags on every material verdict: CERTAIN | DESIGN | INFERRED | UNCERTAIN.

---

## 0. THE LENS — What the runner-side adversarial sees

I am the review seat examining the packet substrate from the CONSUME side. My lens is not
architecture (Claude's) or integration (Sol's) — it's SURVIVAL. What kills a runner mid-turn?
What does the packet substrate promise that it cannot deliver? Where are the silent failure
modes that evade both the doctor and the health verdict?

The moonshot directives I'm evaluating against:
- **M1 continuous presence**: daemon keeps runners alive; seats never go dark
- **M6 fleet self-division**: agents discover each other, claim work, coordinate
- **M7 glass cockpit**: Daniel sees everything; the engine room is live

My adversarial method: for every proposed slice, I ask "what kills it?" and design the
acceptance test and kill drill that would falsify the design BEFORE it ships.

---

## 1. U1-U5 VERDICT TABLE (resolved per the §U process; DESIGN confidence throughout)

| Item | Verdict | Rationale |
|------|---------|-----------|
| **U1** (`reply` verb) | **ADOPTED** | Seven-verb roster: ASK/TELL/HAND/REVIEW/STREAM/SIGNAL/REPLY. `reply` wraps `bus.send_reply()`, carries `meta.reply_id`, routes lane-first per T066. Without it, the runner's most common operation strands expectation settlement. [DESIGN] |
| **U2** (wrap-don't-replace) | **ADOPTED** | 4-phase strangler: Phase 0 verbs are sugar over `bus.send()`, Phase 1 migrate callers, Phase 2 deprecation warning, Phase 3 (T047+) retire. C2's "agents stop calling bus.send directly" withdrawn. [DESIGN] |
| **U3** (dry-run route()) | **ADOPTED** | `route(kind, pri, deadline_ts, sender_tempo) -> RoutingDecision` callable by the send door AND `py agent_cli.py packet-trace`. [DESIGN] |
| **U4** (per-rule counters) | **ADOPTED** | One counter per routing table rule. `packet-stats` prints table with hit counts. [DESIGN] |
| **U5** (runner pains F1-F5) | **ADOPTED FOR PHASE 1** | Mid-turn blind spot, ghost reply, cost-ignorant router, pre-send rwnd check, expectation_dead nudge. Not Phase 0 blockers; Phase 0 is additive meta fields. [DESIGN] |

---

## 2. THE TWO-SLICE SPINE (with order ruling)

### Slice S1: M1 CONTINUOUS PRESENCE — Daemon-as-Consumer + Health Verdict

**What it is**: The daemon claims the consumer seat (not just the runner lock), so the runner's
consume loop lives under daemon supervision. When the runner dies, the daemon relaunches it.
When the daemon dies, the runner's lock TTL expires and the daemon's own lock TTL gates the
relaunch. The fleet health verdict line (one line, GREEN/YELLOW/RED) answers "is the fleet
healthy?" in under 3 seconds.

**Why this order**: M1 must ship BEFORE M6/M7 because M6 (self-division) assumes agents are
alive and M7 (glass cockpit) assumes there's something to observe. A daemon that can't
consume, or a fleet whose health no one can see, makes every later slice a house of cards.

**Inclusions (exact)**:
- Daemon acquires runner_lock + RB-21 consumer seat claim (the T086 S5 path)
- Runner as daemon-managed child process (the T086 S5 subtree)
- Crash-redelivery: runner dies → daemon detects stale worklive → relaunches → RB-26 cursor
  replays uncommitted tail → reply_sent dedup sentinel catches duplicates
- Fleet health verdict line: `FLEET: GREEN — 4 agents, 4/4 progressing, 0 stalled, 0 peek, locks: 3 held, mail: 12 unread, cost: $3.41 today`
- Health verdict derived from: worklive ages, runner_lock holders, lane depths (XLEN), token
  journal daily rollup
- Doctor `--verdict` flag: one line, `<3s`, GREEN/YELLOW/RED with the reason for non-green

**Exclusions (exact)**:
- M6 seat discovery / work claiming (needs the fleet to be alive first)
- M7 glass cockpit UI (needs health verdict as data source)
- T047 legacy retirement (not a dependency for M1 — daemon runs on existing dual-write bus)
- T046 latches (M1 doesn't need causal gates)
- Routing wave Phase 1 (router.py, ECN, pri enforcement — Phase 0 additive meta is enough)
- Per-agent trace rings (F4 fix — trace is QoS0, M1 doesn't depend on it)

**Contraindications (DON'T BUILD YET)**:
- T047 MUST precede the routing wave Phase 1 — the router can't trust lanes while dual-write
  exists. But T047 does NOT need to precede M1 daemon-as-consumer. The daemon runs on today's
  bus. [CERTAIN — from the routing design's sequencing law]
- T046 latches MUST precede any cross-flow work-claiming protocol in M6 — a seat that claims
  work without causal ordering can claim work that was already completed by another seat.
  [CERTAIN — from the latch spec's D1 fail-direction law]
- The health verdict's "stalled" detection MUST use the LATCHED rwnd (from T046+N1), not the
  ticked presence TTL. Today's stall detector has the false-positive problem (F3 from the
  build seat's counter). This is a KNOWN GAP for S1 — the health verdict ships with a
  `STALL_DETECTOR_PROVISIONAL` note until T046+N1 latched rwnd replaces it. [DESIGN]

**Pre-registered acceptance tests**:
1. **P1 (crash-redelivery)**: Kill the runner mid-turn (SIGKILL). Daemon detects stale worklive
   within 15s. Relaunched runner's cursor replays uncommitted tail. Reply sentinel catches
   duplicate handoff. Expectation settles exactly once. [CERTAIN — RB-26 drill discipline]
2. **P2 (daemon death)**: Kill the daemon (SIGKILL). Runner's lock TTL expires within 60s.
   New daemon instance acquires lock, adopts runner. No double-runner race. [CERTAIN]
3. **P3 (health verdict GREEN)**: All 3 seats alive, progressing, no stalled consumers. `doctor
   --verdict` returns GREEN in <3s. [CERTAIN]
4. **P4 (health verdict RED)**: Kill one runner. `doctor --verdict` returns RED within 20s
   (worklive TTL + verdict poll lag) with "deepseek: stalled consumer 21s." [CERTAIN]

**Kill drill (falsification test)**:
- **KD1 — THE GHOST CONSUMER**: Plant a daemon that holds the consumer seat but NEVER drains
  the inbox (infinite sleep in the consume loop). The health verdict MUST detect this — worklive
  shows "idle" while lane depth grows. After 180s of idle + unread mail, verdict = RED. If the
  verdict shows GREEN, the design is FALSIFIED. The detector must distinguish "idle because
  nothing to do" from "idle because the consumer is dead." [DESIGN]

---

### Slice S2: M6 FLEET SELF-DIVISION — Work Discovery + Claim Protocol

**What it is**: Agents discover available work from the task ledger, claim tasks through a
packet-native protocol (OFFER → ACCEPT → HELD → RELEASE, one note per transition per T038
design), and coordinate via the bus without human routing. The conductor's role shrinks from
"assign every task" to "adjudicate contested claims."

**Why this order**: M6 requires M1 (agents must be alive to claim work) and T046 (causal
ordering prevents double-claim races). It does NOT require M7 (the glass cockpit can observe
M6's work but M6 doesn't need it).

**Inclusions (exact)**:
- Task discovery: `task list --status proposed,approved` → agent sees claimable work
- Claim protocol: `OFFER(task_id, agent_id, evidence_of_capability)` → conductor validates →
  `ACCEPT(task_id, agent_id)` → agent begins → `HELD(task_id, agent_id, commit_refs...)` →
  `RELEASE(task_id, agent_id, outcome)`. One note per transition, T038 design.
- Claim contention: two agents offer same task → conductor adjudicates by capability match
  (the RoutingPolicy source scores per question-class feed this) → one ACCEPT, one DECLINE
  with reason.
- Fleet roster discovery: `bifrost_presence()` → list of live agents with their `caps` and
  `tempo` (from the tempo presence signal, §5 of my tempo half).
- Self-division: agent A completes task, discovers next task, claims it — without human
  saying "now work on T099."

**Exclusions (exact)**:
- Full T038 token negotiation (OFFER/COUNTER/ACCEPT/GRACE/RELEASE with atomic lock-claim)
- Cross-flow latches (T046 scope: within-flow causal only for S2; cross-flow reference
  latches are T046 full scope)
- Automatic work claiming without human oversight (conductor adjudicates contested claims;
  auto-claim only when capability match is unambiguous)
- M7 glass cockpit UI

**Contraindications (DON'T BUILD BEFORE)**:
- T046 latches MUST ship before S2. Without causal ordering, two agents can simultaneously
  claim the same task and both receive ACCEPT — the claim protocol's atomicity depends on
  latch-enforced ordering. [CERTAIN]
- T047 legacy retirement SHOULD ship before S2 but is not mandatory. The claim protocol
  works over dual-write (all notes are work-lane packets with lane-first send_reply).
  Stragglers are rare and the dedup sentinel catches duplicates. [DESIGN]
- The RoutingPolicy source scores (per question-class per agent) SHOULD have ≥2 weeks of
  data before auto-claim activates. Without scores, capability matching is manual
  (conductor or human decides). [INFERRED]

**Pre-registered acceptance tests**:
1. **P5 (claim-then-work)**: Agent A claims T099 via OFFER → ACCEPT. Agent A edits a file
   under T099. Agent A releases with HELD(commit_ref). Ledger shows T099 owner=A,
   status=in_progress. [CERTAIN]
2. **P6 (contention resolution)**: Agents A and B simultaneously OFFER T099. Conductor
   sends ACCEPT to A, DECLINE to B with reason. B does NOT begin work. Ledger shows
   owner=A only. [CERTAIN]
3. **P7 (crash-during-claim)**: Agent A OFFERs T099, conductor ACCEPTs, agent A crashes
   before HELD. Claim TTL expires (60s). Task returns to proposed. Agent B can claim it.
   [CERTAIN — RB-26 idempotency applied to claim state]

**Kill drill (falsification test)**:
- **KD2 — THE DOUBLE-CLAIM RACE**: Plant two agents that OFFER the same task within 5ms
  of each other. The claim protocol MUST produce exactly one ACCEPT. If both receive ACCEPT
  (and both begin work), the design is FALSIFIED. The latch-enforced ordering (T046) must
  serialize the OFFERs so the conductor sees them in a defined order. [DESIGN]

---

### Slice S3 (OPTIONAL — only if S1+S2 don't satisfy the brief): M7 GLASS COCKPIT — Live Reasoning + Fleet Visualization

**What it is**: The T079 engine room with live reasoning traces (checkpoints + full-trace dial),
fleet health verdict as the top bar, cost gauges per agent, and flow-tracer (T054) for causality
chains. Daniel sees everything.

**Why this order**: M7 observes M1+M6. It adds no new coordination primitives — it's a
PROJECTION over existing data.

**Inclusions (exact)**:
- Reasoning spine Phase 0 (checkpoint capture + tool-call-as-beat)
- Fleet health verdict as the engine room's top bar (from S1)
- Per-agent cost gauge (from token journal daily rollup)
- Flow tracer (T054): "show me the path of flow X through the system"
- Live trace stream (existing trace lane, QoS0 — the engine room renders it, doesn't store it)

**Exclusions (exact)**:
- Full reasoning spine Tier 1 (full-trace capture, 90d archive)
- Distiller / Tier 3 recall eligibility (needs outcome edges at scale)
- T079 E1-E4 backends (already sliced separately)

**Contraindications (DON'T BUILD BEFORE)**:
- S1 MUST ship first (engine room has nothing to show if the fleet isn't alive)
- S2 is optional for M7 (the engine room can show M1's fleet health without M6's work claims)
- Reasoning spine Tier 1 SHOULD wait for ≥2 weeks of checkpoint-only data before enabling
  full-trace capture. [INFERRED — observer effect evidence is N=1 and provisional]

---

## 3. THE SMALLEST FIRST SLICE — S1 DETAIL

**S1 = Daemon-as-Consumer + Health Verdict.** ~300 lines of Python.

**Inclusions (line-item)**:
1. `core/fleet/health.py` — `fleet_verdict() -> (color, line, details)` (~50 lines)
2. Daemon consumer-seat claim in `core/comm/runner_lock.py` — `acquire_consumer()` variant
   that daemon holds (~30 lines)
3. Runner-as-daemon-child in `scripts/bifrost_runner_deepseek.py` and `bifrost_runner_sol.py`
   — daemon spawns runner subprocess, watches worklive, relaunches on stall (~80 lines)
4. Doctor `--verdict` flag — calls `fleet_verdict()`, renders one line (~20 lines)
5. Dashboard top-bar color from `fleet_verdict()` (~20 lines)
6. Crash-redelivery: runner SIGKILL → daemon relaunch → cursor replay → sentinel dedup
   (already built in T086 S5-S6; S1 wires it end-to-end) (~50 lines of wiring)
7. Tests: P1-P4 + KD1 (~50 lines of pytest)

**Exclusions (why they wait)**:
- T047: not a dependency. Daemon runs on today's dual-write bus.
- T046: not a dependency. M1 doesn't need causal gates. The stall detector's false-positive
  risk (F3) is documented as `PROVISIONAL` until latched rwnd replaces TTL-based presence.
- Routing wave Phase 1: Phase 0 additive meta (verb methods + meta.wake + show-routes) is
  sufficient for M1.
- M6/M7: subsequent slices.

**Build time estimate**: 2-3 hours for implementation, 1 hour for drill verification.

---

## 4. MCP RECEIPTS

Tools called during this fence half:

| Tool | Status | Notes |
|------|--------|-------|
| `read_file` (brief) | OK | research/briefs/t060-moonshot-network-spine-brief-2026-07-17.md |
| `read_file` (prior evidence) | OK | research/reviewed/deepseek-review-moonshot-enablers-2026-07-16.md |
| `read_file` (wishlist) | OK | research/reviewed/wishlist-synthesis-2026-07-14.md |
| `read_file` (packet spec) | OK | docs/packet-spec-v1-2026-07.md |
| `read_file` (packet slices) | OK | docs/packet-substrate-slices-2026-07.md |
| `read_file` (routing design) | OK | docs/packet-routing-design-2026-07.md |
| `read_file` (lanes design) | OK | docs/t039-lanes-latches-design-2026-07.md |
| `read_file` (recall networking) | OK | research/reviewed/recall-networking-reconciliation-2026-07-12.md |
| `read_file` (method baseline) | OK | docs/method-baseline-2026-07.md |
| `find_files` (claude half) | OK | Confirmed Claude's half exists at expected path |
| `find_files` (sol half) | OK | Confirmed Sol's half exists at expected path |
| `knowledge_recall` | OK | Queried for daemon/seat/health prior lessons |
| `write_file` (this half) | OK | research/reviewed/moonshot-network-spine-deepseek-review-2026-07-17.md |

No MCP failures. All tools returned expected results. The brief, prior evidence, and all
five design docs were accessible. Claude's and Sol's halves were confirmed to exist
(via `find_files`) but NOT read — blind protocol held.

---

## 5. HONEST BOUNDS

- **One machine, one Redis, N<10 agents.** The daemon-as-consumer design assumes all
  runners are on the same host (process supervision, not network coordination). Fleet
  self-division assumes a single task ledger (no distributed consensus). These are
  the same bounds the packet substrate already declares.
- **The stall detector is PROVISIONAL until T046+N1.** Today's presence TTL can false-positive
  (agent alive, TTL lapsed between heartbeats). S1 ships with the caveat; T046 latched
  rwnd replaces it. The health verdict carries a `STALL_DETECTOR_PROVISIONAL` flag until then.
- **S1 crash-redelivery depends on RB-26.** If the cursor advance is broken, a crash
  redelivers the entire unconsumed tail. The `reply_sent` dedup sentinel catches duplicates
  for replies, but a handoff that was NEVER answered (runner died mid-turn before sending)
  will be redelivered correctly (it was never answered). The at-least-once contract holds.
- **S2 claim protocol depends on T046 latch ordering.** Without it, the OFFER serialization
  is best-effort (Redis stream append order). At N<10 on one machine, append order is a
  reasonable approximation — but it's an approximation, not a guarantee. The acceptance
  test KD2 MUST pass under latch-enforced ordering; under best-effort ordering, it MAY pass
  but is not guaranteed. [CERTAIN]
- **M7 glass cockpit depends on the reasoning spine.** The spine's observer-effect evidence
  is provisional (N=1, stateless seat, ephemerality). Live reasoning capture for session
  seats (claude, sol) may have different effects. [UNCERTAIN]

---

## 6. TOP THREE DECISIONS

1. **S1 FIRST (M1 daemon-as-consumer + health verdict) before S2 (M6 self-division) and
   S3 (M7 glass cockpit).** Sequential dependency: agents must be alive and observable before
   they can claim work and be visualized. ~300 lines. 2-3 hour build. [CERTAIN]

2. **S1 does NOT wait for T047 or T046.** The daemon runs on today's dual-write bus. The
   stall detector ships with a PROVISIONAL flag until latched rwnd (T046+N1) replaces
   TTL-based presence. Delaying S1 behind T047 would strand the health verdict — which
   is the single cheapest observability win in the system — behind a legacy retirement
   that deletes code. [CERTAIN]

3. **S2 MUST wait for T046 latch v1.** The claim protocol's atomicity (two agents OFFER
   same task → exactly one ACCEPT) depends on latch-enforced causal ordering. Without it,
   the double-claim race (KD2) is a real failure mode with no mitigation other than
   "N<10 makes it rare." Rare is not absent. The method baseline says kill drills must
   falsify the design BEFORE it ships — KD2 would falsify S2 without T046. [CERTAIN]

---

*End of blind half. Filed before reading claude's or sol's halves. Bus-replying now.*
