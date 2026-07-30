# Wake Substrate — Cross-Round Tension Map

Date: 2026-07-29
Purpose: preserve and resolve the independent round's disagreements before synthesis

Read `brief.md` and all three independent files before answering this round. Append a
short `## Cross-round response` to your own file. State only what changed, what held,
and why. Do not re-prove converged material.

## T1 — Who evaluates admission?

- Fable: pure shared function, hosted opportunistically; Redis lease serializes.
- DeepSeek: per-agent daemon is the admission host.
- Kimi: shared deterministic function + per-incarnation adapter + per-agent daemon
  supervisor.

Evidence constraint: a pure function is not a turn starter. A push-capable idle seat
still needs at least one live evaluator or external event hook. A global resident
dispatcher remains a fleet-wide delay failure domain and T073 previously rejected it.

Candidate reconciliation to attack:

- one pure admission library;
- role-addressed work evaluated by the per-agent daemon under a leader/admission lease;
- incarnation-addressed work evaluated by that incarnation's watcher/adapter;
- the same lease makes multiple evaluators safe;
- no global resident dispatcher;
- clocks/deadlines provide a zero-model timer trigger in addition to stream edges.

Question: does this preserve Fable's host-independence while giving DeepSeek's
supervision chain and Kimi's incarnation boundary? Name a counterexample.

## T2 — Registry authority versus projection

Fable proposes the presence card as the one surviving registry. Kimi flags duplication
with `launcher.AgentSpec`; DeepSeek places adapters under the daemon.

Evidence constraint: a presence card is TTL'd runtime self-report. It disappears when
the seat dies and cannot safely be the trusted authority for launch commands, auth
mode, or granted capabilities. Conversely, a static launcher row cannot prove a live
incarnation.

Candidate reconciliation to attack:

- one trusted static runtime-profile authority, migrated from/through Launcher rather
  than added beside it;
- presence card is the live projection and references `runtime_profile_id`;
- fleet model capability/cost profile remains separate from runtime/door profile;
- daemon/adapter consumes the profile; it does not own a second registry.

Question: which existing file/arc should become the trusted authority, and which fields
must be retired or projected?

## T3 — What is wake authority?

All reviewers found mailbox/claim alone incomplete:

- Fable: broadcast/class coverage gaps, bench, and clock-driven expectations; require a
  loss manifest.
- Kimi: committed-but-unacknowledged side effects require outcome evidence.
- DeepSeek: consumed is not equivalent to replied/acked for answerable work.

Evidence constraint: `core/comm/mailbox.py` is explicitly a rebuildable projection, not
the underlying authority. Its decision value comes from stream, cursor, ACK, and reply
evidence, and it must report lag/coverage honestly.

Candidate minimum input:

- mailbox projection caught up through the candidate logical message;
- role/directed claim + generation;
- ACK/reply/outcome evidence;
- expectation/deadline state;
- parked-bench and broadcast/class coverage;
- a loss manifest naming UNKNOWN sources.

Question: which of these belongs in S1 recorded snapshots, and which must gate only
live S3+ admission?

## T4 — Side effects and the ambiguous crash window

Kimi proposes a write-ahead side-effect journal. That records intent, but intent alone
cannot distinguish:

1. crash after intent, before effect;
2. crash after effect, before outcome/ACK.

Suppressing both can lose work; retrying both can double-execute.

Candidate reconciliation to attack:

- internal effects use a fenced transactional outbox/commit;
- external effects must accept an idempotency key at the effect boundary;
- non-idempotent external effects that return an ambiguous outcome become
  `ATTENTION_REQUIRED`; no automatic retry;
- write-ahead intent is evidence, not proof of effect.

Question: is any weaker contract honest? Map current bus reply sends and file writes to
these effect classes.

## T5 — Evidence corrections for synthesis

1. `BifrostAPI.work_drain()` uses cursor-based `Bus.wait`/XREAD. It is not a Redis PEL
   consumer. PEL/XAUTOCLAIM exists in `core/comm/role_queue.py` only.
2. Mailbox admission must not run a full `--rebuild` per decision. `query()` performs
   bounded incremental `catch_up`; T095's forward constraint is catch-up through the
   candidate position plus honest lag/coverage.
3. A 120-second blocking XREAD timeout is a lifecycle-check interval, not wake latency;
   a new event returns immediately.
4. New admission identity should use packet SHA/reply ID/idempotency key. The watcher's
   `(frm, ts, kind)` sidecar is a compatibility fallback, not the new contract.
5. Resident API runners already block on work and do not need a watcher to launch them.
   Their adapter result is `ALREADY_RESIDENT`; admission instrumentation must not add a
   second model turn.

State whether any conclusion in your first response changes under these corrections.

## T6 — Slice order

Common ground: S0, then shadow S1, then registry/conformance S2. Disagreement begins
after that.

Candidate reconciliation:

1. S0 reconciled contract/ownership.
2. S1 pure shadow admission + today's golden-trace replay + coverage/loss manifest.
3. S2 static runtime-profile authority, live projection, adapter conformance, ticket
   template, boot/task/total budgets, operator projection.
4. S2b wrap existing adapters in **shadow/observe-only** mode so real crash windows feed
   the next drills without changing wake behavior.
5. S3 admission lease/generation/outcome/effect-class recovery using real adapter
   observations.
6. Security gate: sender binding, rate/admission ceilings, data-not-authority.
7. S4a live existing-seat cutover behind kill switches.
8. S4b Codex live adapter only after an earlier **no-model feasibility spike** proves an
   owned App Server host.
9. S5 level-authority cutover with watcher/doorbell retained as latency accelerator.
10. S6 onboarding pack and conformance-renewal policy.

Question: name the first unsafe ordering edge or accept this sequence with amendments.
