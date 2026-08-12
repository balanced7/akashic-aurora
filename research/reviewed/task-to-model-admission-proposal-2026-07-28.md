# Task-to-model admission: cheapest capable, acceptance-gated

Status: **PROPOSAL — Daniel gate required.** This document authorizes no automatic
model calls, retries, task claims, or runner changes.

Date: 2026-07-28

Inputs:

- Daniel's directive: use the right model for the right task, let fast seats
  orchestrate without waiting on slow seats, and maximize capability without
  burning tokens.
- `research/reviewed/tempo-doctrine-2026-07-28.md`, including amendments A1-A3.
- Kimi's durable decision
  `kimi-routing-law-right-model-right-task-2026-07-28`
  (`ADR_0728030423_554e879c`).
- T078's settled order: meters before levers, then per-kind routing and thinking
  gates.
- The seed-2 demand-census replication in
  `research/reviewed/demand-census-kimi-judge-2026-07-28.md`.
- A bounded Codex/Terra code audit of the current roster, ledger, runners, and
  telemetry, followed by direct inspection of those seams.

## Decision in one sentence

Build a **deterministic admission clerk**, not an LLM orchestrator: for every
dependency-ready work unit, either do it on the host with zero model tokens or
select the cheapest currently proven capability class, dispatch all independent
units asynchronously, and escalate only when a pre-registered acceptance check
fails.

The scheduler decides *when and whether* a model is needed. Models do the
reasoning at the leaves. The Store/Ledger owns claims and outcomes; Bifrost wakes
and delivers; a mailbox remains a rebuildable projection.

## Why this is the smallest honest move

Most of the machinery already exists:

| Need | Existing seam | Current limit |
|---|---|---|
| Dependency and acceptance state | `core/coord/task_ledger.py` | Tasks have owner, dependencies, files, and acceptance, but no admission/model receipt. |
| Local capability selection | `core/fleet/roster.py` + `core/fleet/models.json` | Deterministic and read-only, but only local models; `glm-4.7-flash` is the only active local candidate today. |
| Local bounded call | `agent_cli.py fleet select/call` + `core/fleet/caller.py` | Manual one-shot; not connected to task claims, Bifrost, or acceptance. |
| Frontier execution | DeepSeek, Kimi, and Sol runners | Each runner has a fixed default model; no shared admission policy chooses among them. |
| Durable coordination | Store/Ledger, task claims, locks | Use these as authority; do not make mailbox state load-bearing. |
| Wake and delivery | Bifrost | Delivery mechanism, not the authority for claim or completion state. |
| Cost evidence | turn metrics, task costs, daily token journals | Task totals exist, but provider/model attribution is not yet normalized enough for routing economics. |
| Delegation | Existing launcher plus the designed `kind=delegate` seam | The design exists; admission and acceptance are not wired to it. |

The missing piece is therefore a small, pure decision seam plus a durable
receipt. A new queue, actor framework, learned router, or daemon rewrite would
duplicate working organs.

## The order of operations

1. **Read authority without a model.** Load the task/claim state, dependencies,
   current commit ancestor, locks, live capability cards, and the exact
   acceptance check.
2. **Form the ready set.** Reject stale, duplicate, already-satisfied, blocked,
   or overlapping work. Dispatch per ready dependency node, never per available
   seat.
3. **Try the zero-token path.** If a schema check, lookup, test, diff, or existing
   receipt answers the question, the host does it and no model is called.
4. **Admit the cheapest proven class.** Match required capabilities, risk,
   context, latency budget, and write authority. A class is a leased capability
   hat, not a permanent agent identity.
5. **Dispatch every independent admitted unit asynchronously.** Slow deep work
   blocks only its true successors. Fast seats may immediately claim another
   ready nonduplicate unit.
6. **Run acceptance before synthesis.** Deterministic checks run first. A model
   review is required only by the risk grade.
7. **Escalate once, explicitly.** A failed or ambiguous acceptance bar may move
   the unit to a stronger class with the failed receipt attached. No automatic
   retry loop and no symmetric fan-out.
8. **Close durably.** Record selection, usage, acceptance, and outcome on the
   Ledger/Store; project the result to Bifrost/mailboxes and dashboards.

This is the video-game-server shape Daniel identified: the control plane is
fast, deterministic, authoritative, and cheap; expensive simulation/reasoning
workers are replaceable and asynchronous.

## Four admission classes

These are policy classes, not fixed people:

| Class | Use when | Typical execution | Escalates when |
|---|---|---|---|
| `no_model` | State lookup, dependency walk, collision check, schema validation, deterministic transform, test execution, or an existing receipt resolves the unit. | Host code/tools. | The result is ambiguous or the acceptance check cannot decide. |
| `local_bounded` | Read-only, tightly scoped extraction/classification/search with a small context and mechanically checkable output. | The active proven local roster entry through the existing one-shot caller or a minimal-context subagent. | Capability missing, model unavailable, malformed output, timeout, or failed acceptance. |
| `api_fast` | Critical-path review, pin hunting, triage, bounded research, or a decision that quickly unlocks other ready nodes. | Any currently proven fast frontier seat that satisfies the capability and risk requirements. | The unit requires deep synthesis, remains contested, or fails its bar. |
| `api_frontier` | High-judgment ambiguity, cross-subsystem design, safety/security-sensitive work, deep audit, or contested integration. | Any currently proven deep seat with the required tools and authority. | Human gate when the decision is destructive, externally consequential, or still contested. |

`api_fast` and `api_frontier` describe the job's tolerance and required
capability. They must not hard-code “DeepSeek always does X” or “Fable alone may
commit.” The current seat/model map is runtime evidence and can change.

## Admission receipt

The first slice should emit a receipt and perform **no call**:

```json
{
  "work_id": "T123/U4",
  "ancestor": "git-sha",
  "artifact": "path or named decision",
  "dependencies": ["T122/U2"],
  "required_caps": ["read", "code-review"],
  "risk": "substrate",
  "acceptance": "exact command or decision rule",
  "admission_class": "api_fast",
  "selected_seat_or_model": "runtime selection",
  "selection_reason": "capability + latency + cost evidence",
  "context_refs": ["durable pointers only"],
  "context_budget_chars": 6000,
  "max_output_tokens": 800,
  "timeout_s": 300,
  "retry_budget": 0,
  "fallback_class": "api_frontier"
}
```

Required fields make token use legible before it happens:

- The artifact or decision being unlocked.
- The exact acceptance check.
- The smallest durable context references, not a copied conversation.
- A model/output/time ceiling.
- The fallback and why escalation is allowed.

No acceptance check means no model admission.

## Subagent admission

Spawn a subagent only when all four are true:

1. A named artifact or open decision will be unlocked.
2. The cheapest capable model can receive a role-scoped, minimal-context brief.
3. Output, timeout, and acceptance are bounded before spawn.
4. Independent decision space remains.

The parent retains claim, timeout, acceptance, and integration authority. A
subagent never creates another polling loop, claims unrelated ledger work, or
inherits the whole chat by default.

## What the demand census changes

Kimi's independent 30-case classification found:

- 15/30 cases (50%) wanted an authoritative non-lesson plane such as a note,
  atom, ledger record, or code/document.
- 8/30 cases (27%) needed no recalled knowledge at all.
- 9/30 cases (30%) wanted a lesson hit or miss.

Those are **recall-action census results, not a fleet-wide workload estimate**.
They still falsify a “call a model and inject lessons for every unit” default.
Admission must first route to the authoritative plane, and it must be able to
return `no_model` / `no_injection` as a successful decision.

## Meter prerequisite

Routing cannot optimize economics while cost rows can lie confidently.

- Commit `9574a6b` closes one concrete defect: Kimi/Sol scalar token payloads
  could increment turns while recording zero task tokens. RED pin `da8b72c`
  covers producer and consumer shapes.
- The remaining journal is still not a billing ledger:
  `scripts/runner_token_journal.py` stores one model string for a whole day and
  applies DeepSeek blended prices even when another provider/model produced the
  tokens.
- `core/comm/turn_metrics.py` and `core/coord/task_costs.py` retain token totals
  but not normalized provider/model selection per attributed unit.

Before automatic routing, preserve raw per-turn
`provider/model/prompt/completion/cache-hit/cache-miss` facts at the runner
boundary. Price lookup may be a separate projection; unknown price must remain
`UNKNOWN`, never zero.

## Minimal gated build

### S0 — make the meter honest

Normalize raw provider/model/usage records and prove every billed model turn has
a nonzero-or-explicitly-zero usage receipt. Keep provider billing
reconciliation separate from task-token estimates.

### S1 — pure admission, shadow mode

Add a pure deterministic function that consumes a work-unit envelope plus a
fleet snapshot and returns the receipt above. It may reuse
`core/fleet/roster.select`; it must not call a model, claim a task, or mutate a
cursor.

Shadow it on real ready units while the current conductor still routes manually.
Store the proposed receipt and the actual choice for comparison.

### S2 — one bounded local adapter

Only after S1 passes, allow `local_bounded` to invoke the existing local
one-shot caller with one output schema, one timeout, zero retries, and a
mechanical acceptance check. A failed bar returns to the parent with a receipt;
it does not self-escalate.

### S3 — frontier adapters

Reuse Bifrost/launcher delivery for `api_fast` and `api_frontier`. Claims,
selection, and outcomes remain durable even if a runner/session dies.
Introduce no new mailbox authority and no runner-specific queue.

## Pre-registered acceptance

S1 does not pass unless tests prove:

1. Same work envelope plus fleet snapshot yields the same receipt.
2. Unmet dependencies, stale ancestors, overlapping claims, missing acceptance,
   or missing capability yield `blocked`, with zero dispatch.
3. A deterministic lookup/test unit selects `no_model`.
4. A bounded read with a proven active local capability selects
   `local_bounded`; gated or unavailable models never win.
5. Independent ready nodes are all eligible in one scheduling pass; a slow node
   does not suppress siblings.
6. A seat/model is selected once per unit, not once per roster member.
7. Every admitted model unit names context, output, time, and retry ceilings.
8. A failed acceptance bar produces one explicit escalation candidate with the
   failed receipt attached.
9. Admission/claim/outcome survive runner death and can be rebuilt without the
   mailbox projection.
10. Shadow-mode telemetry records the recommended and actual class without
    triggering a model call.

The first automatic-call experiment should use a matched bounded pack and gate
on:

- zero unauthorized, duplicate, or stale dispatches;
- 100% usage attribution by provider and model;
- no reduction in acceptance rate or increase in reopen rate;
- lower median tokens per accepted unit than the current/manual route;
- review debt within the risk-graded tempo-doctrine limit.

Turns per hour and “all seats busy” are explicitly rejected success metrics.
Idle is cheaper than unnecessary work.

## Failure modes this design prevents

| Failure | Guard |
|---|---|
| Fast seats wait for a slow round to close. | Ready-node fan-out and asynchronous acceptance. |
| Every available seat gets the same task. | One selection per nonduplicate work unit. |
| Cheap models lower quality invisibly. | Pre-registered acceptance and explicit one-step escalation. |
| An LLM router burns tokens or hallucinates policy. | Pure deterministic admission; intelligence stays at the leaves. |
| Fixed agent roles become permanent ownership. | Capability/authority are leased runtime facts. |
| A crashed session loses work or mail state. | Claims, receipts, and outcomes live in Store/Ledger; Bifrost/mailboxes project them. |
| Retry storms burn the night. | Initial retry budget is zero; escalation is parent-owned and receipt-bearing. |
| Context history is copied into every worker. | Durable pointers plus explicit context budgets. |
| Cost optimization trusts a false zero. | Raw provider/model usage is a prerequisite and `UNKNOWN` stays distinct from zero. |

## Gate decision requested from Daniel

Approve or reject only this sequence:

1. finish honest per-provider/model metering;
2. build S1 pure admission in shadow mode;
3. review the shadow receipts and matched-pack economics;
4. separately gate S2 automatic local calls;
5. gate frontier adapters only after local admission survives failures.

This keeps tonight's tempo gains as operating discipline while the mechanical
router earns authority one falsifiable slice at a time.
