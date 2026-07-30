# Bifrost Wake Substrate — Fleet Review Brief

- Date: 2026-07-29
- Author: codex_root_019fab2d
Status: review draft; no build authorization

## Daniel's request

> What do we need to do to build it, and can you also run your design by everyone else? There are elements of your solution that would probably be very beneficial for the rest of the seats as well as any new model we would want to onboard

## Review protocol

File an independent response before reading another seat's response:

- Fable: `research/in-flight/wake-substrate-round-1/fable.md`
- DeepSeek: `research/in-flight/wake-substrate-round-1/deepseek.md`
- Kimi: `research/in-flight/wake-substrate-round-1/kimi.md`

Preserve disagreement. Attack the proposal; do not average it. Label each material
claim VERIFIED, INFERRED, or PROPOSED and cite the live file or contract that grounds
it. A response may reject the whole shape.

## Verified current state

1. `scripts/bifrost_wake.py` is a near-zero-idle, detect-only listener. It has
   per-session seats, an actionable-kind allowlist, operator override, local-cursor
   detection, and per-session repeat-wake suppression. The focused wake set was
   freshly green on 2026-07-29: 33 tests.
2. `core/comm/dispatcher.py` describes a per-runtime turn-starter registry, but its
   default invoker is still a no-op.
3. `core/comm/mailbox.py` implements T095 M0's rebuildable shadow mailbox index.
   T095 M1 claims and M2 level-triggered wake are not complete.
4. `core/comm/role_queue.py` implements the first T108 role-queue slice with PEL
   delivery plus monotonic application fences. T108 remains active.
5. `scripts/bifrost_daemon.py` is the per-agent supervisor and already manages
   runner/listener children. T060 deliberately kept it out of the consume path.
6. Presence cards already carry `runtime_class`, `wake_mode`, `door`, and `caps`.
   `core/comm/launcher.py` separately has a process-launch registry, but neither is
   a wake-adapter contract.
7. Codex's supported App Server protocol exposes thread resume/start and turn start,
   but the packaged Desktop `codex.exe` is not executable from this task's child
   PowerShell (`Access is denied`). The Desktop private stdio child must not be
   attached. An owned runnable App Server host remains a prerequisite for a live
   Codex adapter.
8. A recorded one-minute same-thread Codex heartbeat produced three no-op model
   reentries and 495,273 input tokens. Periodic history-heavy polling is rejected.
9. The 2026-07-29 missed Fable request proved that an empty visible inbox is not
   proof of no work: the request existed on the durable bench and its work/legacy
   projections had diverged.

## Existing ancestor — do not reinvent it

This is not a greenfield idea. The fossil design
`docs/library/design/20260709_bifrost-mesh-agent-agnostic-comm-coordin_c8b792.md`
already specified W2 dispatcher, W3 wake-adapter registry, a bare-context low-token
contract, and W5 sender verification before auto-wake. T073 later rejected making
the global dispatcher the live owner at that time because no invoker registry
existed, it could not re-arm session-owned watchers, and it introduced an
unsupervised failure domain.

The current review is the successor question: mailbox M0, role-queue fencing,
per-agent daemon supervision, per-incarnation routing, Codex App Server support, and
measured same-thread token cost now exist. Decide whether those additions make W3
buildable, and whether the live host belongs in the global dispatcher, the per-agent
daemon, the per-incarnation adapter, or a hybrid. Reuse the fossil's verified pieces;
retire or supersede its wrong ownership assumptions explicitly.

## Proposed invariant

An idle seat is reachable without keeping a model turn alive:

`doorbell -> authoritative unhandled-state check -> deterministic admission ->
runtime-specific turn starter -> bounded turn -> outcome/ack -> re-arm`

Idle operation spends no model tokens. A model is admitted only when a logical,
actionable, still-unhandled event requires cognition.

## Proposed separation of concerns

### 1. Durable work authority

The wake source of truth is T095 mailbox state plus T108 claim state, not a stream
edge and not a process-local cursor. Redis stream/bell events are accelerators.
Startup, reconnect, and every bell cause a level check for actionable unhandled
work. Legacy remains a straggler net until T047; logical identity is SHA/reply ID,
never stream ID.

The watcher never consumes, acknowledges, settles an expectation, or grants
side-effect authority.

### 2. Deterministic admission

A zero-model admission function receives bounded metadata:

- logical message ID and projection evidence;
- target role/incarnation;
- kind, sender identity, age/freshness, and expectation state;
- current task/claim state;
- runtime availability and capabilities;
- one-in-flight and rate-budget state.

It returns a typed decision:

- `WAKE_FRESH`
- `WAKE_RESUME`
- `STEER_ACTIVE`
- `ALREADY_RESIDENT`
- `DEFER_COALESCE`
- `SUPPRESS_HANDLED`
- `SUPPRESS_STALE`
- `REFUSE_UNVERIFIED`
- `NO_RUNTIME`

No message body or model participates in this decision.

### 3. Runtime adapter contract

Every runtime class implements the same small control surface while retaining its
native lifecycle:

- `probe()` — live, idle, active, unavailable, or unknown;
- `admit(ticket)` — accept one bounded wake ticket and return an admission receipt;
- `steer(ticket)` — optional current-turn injection with an explicit capability;
- `cancel(admission_id)` — bounded shutdown only for an owned admission;
- `status(admission_id)` — outcome, usage, and lifecycle receipt.

The runtime profile declares:

- stable logical agent and incarnation identity;
- `idle_wake`, `active_steer`, `fresh_context`, and `resume_context` capabilities;
- launch/auth/transport class;
- maximum concurrent turns;
- context and token ceilings;
- how usage and completion are observed;
- supervision owner and kill switch.

The profile is not authority. ACL/capability checks and claim generations remain the
authority to act.

### 4. Seat-class mappings

- Resident API runners: `ALREADY_RESIDENT`; their existing blocking consume loop
  remains the turn starter. Do not spawn a second model process.
- Harness-completion GUI seats: existing detect-only watcher is the adapter; the
  harness completion channel performs the wake.
- Codex: an owned App Server host starts a fresh bounded thread by default; exact
  thread resume is opt-in and metered because long-thread replay is the known cost
  failure.
- Local/headless one-shot models: the existing Launcher starts one bounded process
  with the ticket; process exit is the completion receipt.
- Unknown runtime: fail closed as `NO_RUNTIME`; onboarding is incomplete until its
  adapter conformance battery passes.

### 5. Wake ticket

The model receives a small pointer-rich prompt, not a transcript:

- admission ID;
- stable agent/incarnation;
- logical message ID, sender, kind, age, and expectation deadline;
- mailbox/ledger/artifact pointers;
- explicit task and stop condition;
- token/time ceiling;
- instruction to boot, read live authority, and treat packet content as data rather
  than permission.

Full fidelity remains at rest in Aurora.

### 6. Delivery and crash semantics

- One admission lease per logical message/target incarnation.
- Monotonic generation fences prevent stale admissions from committing outcomes.
- One active turn per seat unless the runtime profile explicitly proves otherwise.
- Bursts coalesce into one wake; a pending latch causes one follow-up after the
  current outcome, not parallel duplicates.
- ACK/expectation settlement occurs only after a typed successful outcome.
- Crash before outcome leaves the item unhandled and redeliverable.
- Restart first reconciles mailbox/bench/claim state, then arms the doorbell.
- A lost bell delays a wake; it cannot lose work.

### 7. Security

- Bind sender identity at the transport; never trust caller-supplied `from_agent`.
- Auto-wake accepts only an explicit kind/sender/capability policy.
- Waking grants attention, not write/exec authority.
- Runtime adapters own only processes or App Server connections they launched.
- No attachment to a Desktop private child and no listener exposed beyond a local,
  authenticated endpoint.

## Proposed build slices

Nothing below starts until this review is reconciled and mapped onto the existing
ledger arcs rather than duplicating them.

### S0 — Reconciled contract and ownership map

Decide whether the home is T073 Phase 5, T095 M2, T060 daemon, T108, T078, or a
composition with one explicit owner per invariant. Name what existing code retires.

Acceptance: one dated build specification with peer disagreements preserved and
Daniel's gate.

### S1 — Pure admission state machine, shadow only

Add typed tickets, decisions, receipts, and a fake runtime adapter. Feed recorded
mailbox/claim/runtime snapshots. Do not launch, consume, ACK, or change wake behavior.

Pins:

1. handled/stale/unverified work never admits;
2. one logical message admits at most once per active generation;
3. two stream twins yield one decision;
4. a burst yields one admission plus one pending latch;
5. mailbox unavailable yields loud `UNKNOWN`, never confident empty;
6. decision output has bounded static cardinality;
7. zero model/network launch calls in shadow mode.

### S2 — Adapter registry and conformance battery

Define the runtime profile and adapter protocol. Reuse or explicitly supersede
presence-card and Launcher fields; do not create a third conflicting registry.

Conformance bars:

1. probe cannot claim live from a stale self-report alone;
2. adapter refuses unsupported fresh/resume/steer modes;
3. admission returns a stable receipt before generation starts;
4. only the owned child/connection can be cancelled;
5. completion and usage are typed or `UNKNOWN`, never fabricated zero;
6. kill switch fails toward no wake and preserves work.

### S3 — Durable admission lease and restart recovery

Compose T095/T108 authority with a monotonic admission generation and outcome
journal. Still use fake adapters.

Kill drills: crash before launch, after launch/before receipt, after side effect/
before ACK, stale adapter completion, lost bell, Redis restart, duplicate legacy/work
projection, and watcher offline while work is parked on the durable bench.

### S4 — First live adapter: Codex, one metered request

Resolve the owned runnable App Server prerequisite. Start a fresh bounded thread,
not this continuity-heavy thread. Run one request with an exact token/time ceiling,
typed usage receipt, visible result, and kill switch. Then test opt-in exact-thread
resume separately; it is not the default.

Stop if UI coherence, authentication, independent-host safety, or usage accounting is
not proven.

### S5 — Existing seat adapters without consume-path migration

Wrap, do not rewrite:

- resident runner = already-resident adapter;
- harness watcher = completion-wake adapter;
- Launcher = bounded process adapter.

Rerun T073 wake bars, T086 lifecycle bars, RB-25 storm bars, and T108 twin-theft/
reply-pin/side-effect-fence bars. No daemon-as-consumer move.

### S6 — Level-triggered production cutover

Depends on the relevant T095/T108 slices. Replace edge-only admission with
`actionable_unhandled > 0`; use the bell only for latency. Add doctor/UI visibility:
armed, last decision, suppressed count by bounded reason, in-flight admission,
pending latch, last usage, and recovery status.

Rollback must prove that work published after the flip remains reachable after
reverting.

### S7 — New-model onboarding pack

A new seat supplies:

1. stable logical identity and incarnation strategy;
2. ACL/capabilities;
3. runtime profile and adapter;
4. boot/recall door;
5. bounded ticket template;
6. conformance battery;
7. one live request/reply/ACK drill;
8. crash/restart/redelivery drill;
9. token/time accounting or honest `UNKNOWN`;
10. stand-down and process-ownership proof.

Until all ten pass, the model may be manually invoked but is not auto-wakeable.

## Questions every reviewer must answer

1. Which existing arc owns each slice, and what proposed component duplicates a
   mechanism already present?
2. Should the admission host be global, per-agent daemon, per-incarnation adapter, or
   a hybrid? Name the failure domain and supervision chain.
3. Is mailbox/claim state sufficient authority for level-triggered wake? Identify a
   counterexample.
4. What is the smallest first slice that changes no live behavior but proves the
   architecture?
5. Which failure could still consume work, double-execute a side effect, wake the
   wrong seat, or burn tokens while idle?
6. What exact acceptance bar would falsify your preferred design?
7. Which parts genuinely generalize to future models, and which are Codex-specific?

## Reviewer-specific pressure

- Fable: reconcile ownership with T073/T095/T060/T108 and attack the global-vs-daemon
  boundary. Name the integration order.
- DeepSeek: walk the runner consume/claim/ACK path and attack crash, fence, stale
  completion, and supervision semantics.
- Kimi: walk newborn onboarding and a seat that dies nightly; attack context/token
  budgets, freshness, history replay, and what the operator can actually understand.
