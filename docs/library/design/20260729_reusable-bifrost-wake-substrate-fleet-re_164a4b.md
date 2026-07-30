---
akashic_id: art_20260729_reusable-bifrost-wake-substrate-fleet-re_164a4b
akashic_sha: e63689bf2171
schema_version: 1
status: draft
type: design
arc: T095
date: 2026-07-29
title: reusable-bifrost-wake-substrate-fleet-reconciliation
gist: "# Reusable Bifrost Wake Substrate — Fleet Reconciliation - **Status:** fleet-reconciled design; awaits Daniil's explicit build gate; no live"
visibility: fleet
body_type: markdown
seats: [codex_root_019fab2d, claude, deepseek, kimi]
category: [substrate, memory, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260729_bifrost-wake-substrate-fleet-review-brie_ff924c
    rel: discusses
  - target: art_20260729_wake-substrate-round-1-fable-position_2032e2
    rel: discusses
  - target: art_20260729_wake-substrate-round-1-deepseek-position_53c4c3
    rel: discusses
  - target: art_20260729_wake-substrate-round-1-kimi-position_6aa1be
    rel: discusses
  - target: art_20260729_wake-substrate-round-1-tension-map_a94a14
    rel: discusses
created: "2026-07-29T20:12:03"
updated: "2026-07-29T20:12:03"
---
<!-- GENERATED PROJECTION of art_20260729_reusable-bifrost-wake-substrate-fleet-re_164a4b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# reusable-bifrost-wake-substrate-fleet-reconciliation

# Reusable Bifrost Wake Substrate — Fleet Reconciliation

- **Status:** fleet-reconciled design; awaits Daniil's explicit build gate; no
  live wake behavior changed
- **Date:** 2026-07-29
- **Participants:** Codex, Fable, DeepSeek, Kimi
- **Inputs:** `brief.md`, three independent positions, `tension-map.md`, and the
  cross-round responses appended to each position

## Decision

Build the wake path as a **shared deterministic admission engine plus
runtime-specific adapters**, not as a new global resident dispatcher.

The governing loop is:

> durable work becomes actionable → a cheap edge or level signal causes an
> evaluator to inspect authoritative state → exactly one fenced admission is
> recorded → the selected runtime starts or continues one bounded turn → the
> outcome is durably classified → the cheap listener re-arms.

This is reusable fleet infrastructure. Codex App Server is one adapter, not the
architecture. Existing API runners, desktop seats, CLI seats, and future models
all use the same admission, ticket, fencing, outcome, budget, and conformance
contracts.

The design belongs primarily to **T095 M2** (level-triggered mailbox/action
authority), with **T108** supplying role claims and monotonic generation fences,
**T060/T075** supplying lifecycle supervision, **T073** supplying the existing
dispatcher/adapter seam, and **T078** supplying runtime-door capability work.
Do not create a parallel task family or a second message authority.

## What the fleet agreed on

All three reviewers accepted the core shape after the cross-round:

1. No global model-bearing dispatcher and no single global failure domain.
2. One pure admission function may be evaluated by more than one local process;
   a Redis admission lease and monotonic generation serialize the result.
3. The per-agent daemon is the default evaluator for role-addressed work.
4. The per-incarnation watcher/adapter evaluates direct incarnation-addressed
   work before invoking its harness.
5. The current edge watcher remains the low-latency accelerator. A level check
   at startup, reconnect, deadline, and bounded lifecycle intervals is the
   correctness backstop.
6. Resident API runners already have a turn starter. Their decision is
   `ALREADY_RESIDENT`; the wake layer must not launch a second model turn.
7. A TTL presence card is a live projection, not trusted launch or capability
   authority.
8. New admission identity is `reply_id`, packet SHA, or an explicit idempotency
   key. The watcher's `(from, timestamp, kind)` tuple remains a compatibility
   fallback only.
9. Fresh bounded context is the fleet default. Resuming a long conversation is
   opt-in, metered, and justified by the request.
10. Boot cost and turn cost are separate budget lines.
11. Write-ahead intent is evidence, not proof that a side effect happened.
12. The first implementation slice is shadow-only and changes no live behavior.

## Runtime topology

### Shared admission library

The admission engine is a pure function over a versioned state snapshot:

```text
decision = admit(candidate, state_snapshot, runtime_profile, policy)
```

The same snapshot must always produce the same typed decision. The function
does not launch a process, consume a message, advance a cursor, call a model, or
perform a side effect.

### Local evaluators

- **Role-addressed work:** the target agent's daemon evaluates on its edge,
  heartbeat, startup, and reconnect opportunities.
- **Incarnation-addressed work:** that incarnation's watcher evaluates on its
  stream edge and lifecycle checks.
- **Resident runner:** evaluates for observability but returns
  `ALREADY_RESIDENT`; its existing blocking consume loop starts the turn.
- **Fully offline seat:** no process is invented. Durable work waits and the
  next daemon, watcher, boot, or doctor pass performs the level check. This is
  delayed, never lost.

Every evaluator uses the same admission lease, admission identity, generation
fence, and outcome store. A watcher/daemon race is therefore a duplicate
evaluation, not a duplicate turn.

If a future work class has a page-grade deadline that cannot tolerate a fully
offline seat until its next lifecycle opportunity, that requirement may justify
a tiny non-model clock/level scheduler. It does not justify a global model host,
and no such requirement is currently verified.

### Edge and level are complementary

The stream watcher is a **doorbell**: it gives immediate wake latency while it is
alive. The mailbox/action view is the **level authority**: it proves whether
actionable work still exists after restart, disconnect, or a missed edge.

The production design retains both:

```text
stream edge ─┐
startup ─────┤
reconnect ───┼─> pure admission check ─> fenced admission ─> adapter
deadline ────┤
lifecycle ───┘
```

## Identity and registry model

Four identities must remain separate:

1. **Model profile** — capability, cost, context, and policy facts in the fleet
   model roster.
2. **Logical role** — the sender-facing address that remains stable while seats
   move.
3. **Runtime profile** — trusted static facts about how a runtime can be
   launched, authenticated, probed, budgeted, and stopped.
4. **Incarnation** — the current live connection/process/session projection.

The trusted runtime-profile authority should be migrated through the existing
Launcher `AgentSpec` registry rather than creating a third registry. It owns:

- `runtime_profile_id` and version;
- runtime class and adapter type;
- launch/attach command or door;
- authentication and sender-binding requirements;
- allowed capabilities and work classes;
- fresh/resume context modes;
- boot and turn budget ceilings;
- maximum in-flight work;
- probe and conformance requirements;
- conformance expiry;
- kill switch and safe-stop behavior.

Presence remains TTL self-report and carries only live projection facts:

- logical agent/role;
- incarnation and session;
- `runtime_profile_id`;
- liveness, current state, and heartbeat;
- current admission/turn;
- watcher, daemon, and adapter health.

Static authority must survive the death of the seat it describes. Presence may
disappear without erasing the trusted profile.

## Admission authority and loss manifest

The mailbox is a rebuildable projection over durable records, not the sole
authority to act. Before a decision can be trusted, the snapshot must include:

- candidate packet identity and logical target;
- bounded mailbox catch-up through the candidate position;
- honest mailbox lag and coverage;
- role claim, owner, generation, and lease state;
- ACK, reply, and prior admission/outcome evidence;
- sender expectation and its deadline;
- durable bench state;
- direct, broadcast, and work-class coverage;
- seat liveness and current admission;
- runtime-profile and conformance freshness;
- boot and turn budgets;
- an explicit loss manifest for any source the decision cannot see.

If a required source is missing, stale, lagging past the candidate, or outside
declared coverage, the result is `REFUSE_UNVERIFIED` or `ATTENTION_REQUIRED`,
never a confident empty/suppress verdict.

Mailbox maintenance is bounded incremental `catch_up`, not a full rebuild before
every decision.

## Typed decisions and operator state

The machine contract should distinguish at least:

- `START_TURN`
- `STEER_ACTIVE`
- `ALREADY_RESIDENT`
- `DEFER_COALESCE`
- `SUPPRESS_HANDLED`
- `SUPPRESS_DUPLICATE`
- `SUPPRESS_STALE`
- `DEFER_BUSY`
- `DEFER_BUDGET`
- `DEFER_OFFLINE`
- `REFUSE_UNVERIFIED`
- `ATTENTION_REQUIRED`

`STEER_ACTIVE` is not a new model turn. It routes a bounded steer/nudge through
the existing fidelity path into the currently fenced incarnation. It requires
proof of the active admission and incarnation, produces a typed outcome, and
must not invoke a second runtime. `DEFER_COALESCE` means the candidate was
durably folded into an already pending admission; it is neither a duplicate nor
handled work.

The brief's earlier enum is deliberately migrated, not silently retired:

| Brief decision | Reconciled contract |
|---|---|
| `WAKE_FRESH` | `START_TURN` with required `context_mode=fresh` |
| `WAKE_RESUME` | `START_TURN` with explicit, metered `context_mode=resume` |
| `STEER_ACTIVE` | retained |
| `ALREADY_RESIDENT` | retained |
| `DEFER_COALESCE` | retained |
| `SUPPRESS_HANDLED` | retained |
| `SUPPRESS_STALE` | retained |
| `REFUSE_UNVERIFIED` | retained |
| `NO_RUNTIME` | `DEFER_OFFLINE` when a trusted profile exists; otherwise `ATTENTION_REQUIRED` |

For the operator projection, use four states:

- **ACTING** — admitted or already resident and processing;
- **WAITING** — valid work is held by budget, busy state, or offline runtime;
- **QUIET** — the candidate was already handled, duplicate, or non-actionable;
- **ATTENTION** — authority is unknown or a side effect has an ambiguous outcome.

Kimi and Fable preferred a three-bucket `WOKEN / HELD / REFUSED` projection.
The four-state projection preserves their distinction while avoiding the
misleading presentation of handled duplicates as refusals. The UI labels are
testable in S1 and do not change the machine contract.

The minimum human sentence is:

> Seat X is acting/waiting/quiet/needs attention; last admitted at T for reason
> R; boot cost B, turn cost N; M actionable items remain.

Every decision record also names the evaluator that made it.

## Versioned wake ticket

Every non-resident adapter receives the same small, versioned ticket:

- schema version;
- admission ID and candidate `reply_id`/SHA;
- logical target, selected runtime profile, and incarnation if directed;
- admission generation and evaluator identity;
- bounded task and reason for wake;
- expectation deadline and freshness evidence;
- boot ceiling and turn ceiling;
- fresh-context default or explicit metered resume;
- allowed capabilities and declared effect manifest;
- ACK/reply/outcome contract;
- source pointers needed for normal `boot`, not a second boot payload.

The ticket is a conformance artifact, not an expanding prompt. The first bar is
that a cold supported model produces the required typed outcome in at least
9/10 trials under a provisional 1,500-token ticket ceiling. The measured
distribution, not the provisional number, sets the final ceiling.

## Side-effect and crash contract

An admission may be safely retried only when its effect class proves that retry
cannot double-execute an irreversible action:

1. **Internal durable effects:** use a fenced transactional commit/outbox and
   verify the authoritative postcondition before retry.
2. **External effects with idempotency support:** pass the admission ID as the
   idempotency key at the effect boundary.
3. **External or local effects with an ambiguous outcome:** record the declared
   effect manifest, inspect verifiable postconditions, and route any remaining
   ambiguity to `ATTENTION_REQUIRED`. Do not auto-retry.

A Git commit, file diff, or reply-sent sentinel can be evidence for a
postcondition; it is not automatically a transaction with the admission store.
Bus replies do not become effectively-once until the receiver-facing send
boundary actually honors the admission/reply idempotency key.

If a work class requires automatic execution but cannot provide an idempotent
boundary or a provable postcondition, it is not eligible for unattended wake.

## Build sequence

### S0 — Register and freeze the contract

1. Register the slice under the existing owning tasks rather than inventing a
   parallel architecture.
2. Freeze the decision enum, snapshot schema, admission identity, lease/fence,
   ticket, outcome, effect classes, and loss manifest.
3. Name one authority and one projection for every field.
4. Record kill switches and rollback boundaries before implementation.

**Exit:** reconciled build specification and ledger ownership are explicitly
approved at Daniil's gate.

### S1 — Pure shadow admission

1. Implement the side-effect-free admission function and snapshot serializer.
2. Replay a golden trace containing the fleet's real wakes, missed request,
   benched work, broadcast visibility, duplicate edges, handled replies, and
   forgotten watcher re-arms.
3. Run daemon-default and watcher-edge evaluation over the same snapshots.
4. Emit decision, reason, evaluator, evidence coverage, lag, and operator state.
5. Spend zero model tokens and change no cursor, claim, launch, or ACK.

**Exit:** deterministic replay; no false confident-empty result; no live behavior
change; both evaluator paths agree.

### S2 — Runtime profiles, adapters, ticket, and conformance

1. Migrate the trusted static runtime-profile authority through Launcher.
2. Make presence reference `runtime_profile_id`.
3. Implement the adapter protocol in the existing dispatcher seam:
   `probe`, `admit/prepare`, `start_or_signal`, `collect_outcome`, `stop`.
4. Add the versioned wake ticket, split budgets, fresh-context default, kill
   switch, and operator projection.
5. Add conformance expiry; stale or missing conformance becomes unknown, not
   supported.

**Exit:** a new runtime can be described without code changes to admission; cold
ticket conformance passes; registry duplication is removed or explicitly
deprecated.

### P0 — Codex App Server feasibility spike

Run an early **no-model-call** spike proving the packaged App Server lifecycle,
one persistent stdin reader, thread/run correlation, cancellation, and cleanup.
This resolves the riskiest adapter unknown without moving Codex ahead of the
existing seats.

**Exit:** attach/launch/observe/stop works without a paid turn or orphan process.

### G1 — Passive-observation security gate

Before any observe-only wrapper reads live packets:

- bind sender identity to authenticated transport/session evidence;
- minimize and redact stored bodies;
- treat packet text as data, never launch authority;
- enforce adapter capability allowlists.

**Exit:** forged sender fields cannot select an adapter or elevate capability.

### S2b — Existing adapters in observe-only mode

Wrap resident runners and current watcher/harness paths without changing their
behavior. Record their real timing, exit, crash, duplicate, and re-arm windows.

**Exit:** shadow observations cover the actual adapters, not only fakes. Any
new crash window extends S3 before live cutover.

### S3 — Durable admission, recovery, and effect drills

1. Add admission lease, monotonic generation, outcome journal, and restart
   reconciliation.
2. Apply the three effect classes and manifests.
3. Kill at every boundary: before lease, after lease, before start, after start,
   after effect, before outcome, after outcome, before ACK, and during re-arm.
4. Test daemon death, watcher death, both dead, lease flap, stale predecessor,
   duplicate evaluators, and bench rehome.

**Exit:** stale generations cannot commit; one logical admission cannot produce
two eligible starts; ambiguous effects halt visibly; durable work survives all
kills.

### G2 — Live-adapter security and budget gate

- per-profile rate and concurrency ceilings;
- boot and turn budget enforcement before launch;
- command/argument allowlists;
- no shell interpolation from packet bodies;
- secret redaction and bounded outcome capture;
- explicit operator approval for privileged effect classes.

**Exit:** adversarial packets cannot launch arbitrary commands, bypass ceilings,
or smuggle authority through content.

### S4a — Existing-seat live cutover

Enable the shared admission contract for the current seats first, one runtime
profile at a time, behind independent kill switches. Resident runners remain
resident and must not receive a second turn starter.

**Exit:** shadow/live parity, no wrong-seat starts, no idle model spend, bounded
recovery, and clean rollback for every existing profile.

### S4b — Codex live adapter

Only after P0 and the S3/G2 gates, admit one metered Codex request through the
persistent App Server host. Reconcile thread/run IDs and token receipts before
expanding.

**Exit:** one request causes one bounded turn and one typed outcome; no orphan
host, duplicate turn, shared-reader race, or hidden resume cost.

### S5 — Level authority cutover

Make actionable durable state, not the survival of an edge event, the production
wake authority. Retain the watcher as the immediate edge evaluator and add level
checks on startup, reconnect, deadlines, and bounded lifecycle intervals.

**Exit:** missed edges and restarts delay work but do not lose it; idle level
checks spend no model tokens; manual re-arm is no longer correctness-critical.

### S6 — New-model onboarding pack and renewal

Ship:

- runtime-profile schema and examples;
- adapter SDK/protocol;
- versioned ticket schema;
- conformance battery;
- shadow replay harness;
- kill-drill battery;
- security checklist;
- budget/telemetry contract;
- presence projection contract;
- renewal and deprecation rules.

Conformance has a half-life. An expired profile is downgraded to unknown until it
passes again.

**Exit:** a new supported runtime reaches shadow mode by supplying a model
profile, logical-role mapping, runtime profile, adapter, and passing receipts;
the admission engine itself does not change.

## Acceptance bars

The substrate is not complete until fresh receipts show:

- zero model invocations for idle watch/level operation;
- one logical request produces at most one eligible turn start;
- stale generation cannot ACK, advance, or commit;
- a duplicate edge changes neither cost nor side effects;
- restart catches actionable work that arrived while every evaluator was down;
- unknown/lagging authority produces `REFUSE_UNVERIFIED`, never false quiet;
- broadcast, direct, bench, role, and incarnation coverage match the declared
  loss manifest;
- resident runners are never double-started;
- fresh bounded context is the default and resumed context is separately metered;
- boot and turn usage reconcile independently;
- every ambiguous non-idempotent effect becomes visible human attention;
- every adapter can be disabled independently and leaves no orphan;
- expired conformance removes live eligibility;
- operator state explains who evaluated, why, cost, queue depth, and next action.

## What each reviewer changed

- **Fable** forced ownership discipline: no new global subsystem, replay the
  real fleet day as the golden trace, cover bench/broadcast/deadline authority,
  and move sender binding ahead of packet observation. Fable conceded that a
  pure function still needs local evaluators and that presence cannot be static
  authority.
- **DeepSeek** supplied the real crash/fence windows and made the daemon the
  evaluator of record without making it exclusive. DeepSeek corrected its own
  PEL, mailbox-rebuild, latency, and legacy-dedup claims, adopted the static
  profile split, and promoted the watcher from bell to edge evaluator.
- **Kimi** made token and onboarding cost first-class: versioned small tickets,
  cold-model conformance, separate boot/turn ceilings, expiring conformance,
  nightly-death recovery, and legible operator state. Kimi withdrew
  write-ahead intent as a complete crash answer and accepted the effect-class
  contract.

## Final fleet gate

- **DeepSeek:** `ACCEPT`; no false claim, unsafe ordering edge, or missing
  crash/fence gate.
- **Kimi:** `ACCEPT`; no false claim, token/onboarding failure, or missing hard
  gate.
- **Fable:** returned two reds: the synthesis had silently omitted the brief's
  typed `STEER_ACTIVE` path, and S0 no longer named Daniil as the approving
  gate. Both are repaired above. Fable's receipt explicitly made acceptance
  conditional on those two exact repairs and reported no other false claim or
  unsafe edge.

## Preserved risks and disagreements

1. **Fully offline deadline latency:** durable work is safe, but no evaluator
   means no immediate action. Add a tiny scheduler only if a verified work class
   requires it.
2. **Operator labels:** three versus four buckets remains a presentation choice;
   S1 replay should test which one makes handled work and genuine refusal clear.
3. **Bus send idempotency:** the reply ID exists, but receiver-boundary
   effectively-once behavior is not yet proven.
4. **File and repository effects:** manifests and Git make many outcomes
   inspectable, but not automatically transactional. Ambiguity remains a stop
   condition.
5. **Codex App Server packaging:** the persistent single-reader host is a
   design requirement, not yet a fresh feasibility receipt.

## Immediate next move

The first buildable change is **S0 + S1 only**: register the ownership, freeze
the contract, implement a pure shadow evaluator, and replay the recorded fleet
trace. It is deliberately reversible, makes no live wake decision, and gives us
the evidence needed to size the remaining work before touching a runtime.
