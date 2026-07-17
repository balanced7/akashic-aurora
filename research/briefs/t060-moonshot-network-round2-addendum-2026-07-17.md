# T060 Round 2 Addendum — Cross-Critique, Cadence, and Control Fidelity

Status: active work order, 2026-07-17
Parent brief: `research/briefs/t060-moonshot-network-spine-brief-2026-07-17.md`
Coordinator: `codex_root`

This addendum does not revise the three blind halves. It starts the disclosed
cross-critique round after all three halves were filed.

## CHARTER

Reconcile the first-slice disagreement in the T060 moonshot/network spine while
dogfooding a bounded WORK → CHECKPOINT → SYNC → RULE → RESUME cadence. Convert
Daniel's request for Codex-like steer/nudge fidelity into an explicit control-plane
contract, and use the RED/BLUE/Jester experiment to attack that contract before any
load-bearing networking code is changed.

The three lenses remain:

- Fable/Claude: architecture, operator legibility, moonshot coherence.
- DeepSeek Review: adversarial runner reality, failure modes, executable drills.
- Sol/Codex: MCP-native newcomer, product-control fidelity, integration and parity.

## INPUTS

Read all three halves before filing a cross-critique:

- `research/drafts/moonshot-network-spine-fable-2026-07-17.md`
- `research/reviewed/moonshot-network-spine-deepseek-review-2026-07-17.md`
- `research/drafts/moonshot-network-spine-sol-2026-07-17.md`

Read the adversarial evidence:

- `research/reviewed/jester-red-deepseek-2026-07-16.md`
- `research/reviewed/jester-blue-deepseek-review-2026-07-16.md`
- `research/reviewed/gemini-jester-red-2026-07-16.md`
- `research/reviewed/jester-synthesis-claude-2026-07-16.md`
- `research/reviewed/hardening-reconciliation-2026-07-17.md`
- `docs/failure-ledger-2026-07.md`, especially C1-3 and C1-4

Inspect the live fidelity seam:

- `core/comm/nudge.py`
- `agent_cli.py::cmd_bifrost_nudge`
- `ai_setup_mcp.py::bifrost_nudge`
- `docs/coordination-plan-synthesis.md` §3

External product evidence, used only for the behavior being emulated:

- OpenAI's current Codex manual, Prompting → “Steering and queuing”: **Steer**
  appends a message to the current run; **Queue** holds it for the next run.
  <https://learn.chatgpt.com/docs/prompting.md>
- The current Codex app-server lifecycle describes `turn/steer` as appending input
  to the in-flight turn without creating a new turn, distinct from
  `turn/interrupt` cancellation.

Live experiment receipts to treat as data:

- Native Aurora MCP core coordination calls work in the Sol/Codex seat.
- Native `note` and `notes` currently fail because the MCP Namespace defaults omit
  `retire` and `all`; CLI fallback was declared and used.
- A virgin `codex_root` cursor had to consume **10,009** historical packets before
  current peer replies appeared. This is a freshness failure, not merely ceremony.

## RULES

1. Apply M1-CC literally. Each cross-critique must name:
   - what another half caught that yours missed;
   - what another half got wrong, with evidence;
   - what all three halves missed.
2. Preserve the blind records. Write a new file; do not edit any half or
   `docs/packet-routing-design-2026-07.md`.
3. Tag claims `CERTAIN`, `INFERRED`, `DESIGN`, or `UNCERTAIN`.
4. Fidelity controls **when** a message is considered, never whether its content is
   true. Source, capability, evidence, and current ledger state still govern trust.
5. The Jester has no nudge, steer, halt, blocker, or decision authority. Treat that
   restriction as evidence that these are privileged control-plane operations.
6. No hard interrupt is used in this round. C1-3 proves that the current runner can
   replace and lose an active task. A hard rung is not eligible for live dogfood until
   checkpoint/suspend/restore exists or the target explicitly declares itself idle.
7. No T047 cutover, router enforcement, wake-policy change, or latch code may begin
   in round 2. Reconciliation must first choose and pre-register the first safe slice.
8. Each writer locks only its own output and releases it after filing.

## THE QUESTION

Which first slice honestly maximizes moonshot leverage while remaining reversible
under N=3 MCP-native frontier models?

Adjudicate these three competing openings:

1. Fable: additive seven-verb surface + dry-run/counters, then T047.
2. DeepSeek Review: T047 + interactive-consumer migration + per-agent trace first.
3. Sol/Codex: shadow-only composer/dry-run first, then T047 after a live intent and
   consumer census.

Also answer:

- Is per-agent trace a new lane (and therefore roster growth) or partitioned
  retention inside one trace family? Name the deletion/rollback ritual either way.
- Can an interactive MCP seat safely peek lane-only mail without creating a second
  consumer truth or an unbounded newborn backlog?
- Should capability/cost select a packet destination, or propose a T038 ownership
  transition that is accepted before transport? State the authority boundary.
- What is the smallest truthful M1/M6/M7 demonstration the three-seat panel can run
  before any destructive cutover?
- What provenance and anti-poisoning fields keep a high-fidelity steer from becoming
  a high-authority lie?

## CONTROL-FIDELITY CANDIDATE (ATTACK THIS)

Aurora already has three targeted modes, but their delivery contract is incomplete.
Round 2 must either amend or reject this candidate:

| Mode | Scheduling meaning | Required receiver behavior | Ack |
|---|---|---|---|
| `inform` / queue | Consider on the next turn; never displace current work | Preserve order, expiry, and source; show as pending | delivery receipt only |
| `steer` | Append to the current run at the next tool-round boundary; no new task/run | Fold into active context, dedupe application, preserve plan/tool history and locks | `adopted`, `deferred`, or `conflict`, with active task id |
| `interrupt` | Suspend at the next safe round boundary | Finish current tool call; emit bounded checkpoint; suspend active span; service interrupt; explicitly restore/replan/abort | checkpoint id + disposition required |
| `halt` / barrier | Stop targeted or fleet dispatch after safe boundaries | ACK barrier, stop consuming, await governed release | barrier ACK required |

Every targeted control packet should carry or derive:

```text
signal_id, mode, from, to, task_id, active_span_id, sent_at, expires_at,
reason, expected_action, ack_required, supersedes, provenance, capability_grant
```

The receiver records `received_at`, `applied_at`, `disposition`, and (for interrupt)
`checkpoint_id` plus `resume_of`. Payload prose never grants itself authority.

Candidate invariants:

- Same `signal_id` applies at most once even if carrier and Redis control flag both arrive.
- `steer` never creates a new task, resets the plan, drops tool history, or releases locks.
- `interrupt` never kills an in-flight tool call and never replaces work without a
  durable checkpoint.
- Expired signals are visible as expired, not silently applied or silently discarded.
- Higher fidelity requires equal or stronger sender capability and audit, not merely a
  different message `kind` supplied by the sender.
- An authoritative-looking payload from an unprivileged or adversarial seat remains
  untrusted content.

## SLICE CADENCE TO DOGFOOD

One panel cycle is:

1. **WORK** — one bounded artifact or one testable hypothesis; no opportunistic edits.
2. **CHECKPOINT** — file the artifact and emit a concise receipt containing task,
   artifact, open questions, locks, and next intended action.
3. **SYNC** — consume only fresh control/work traffic; compare receipts, not chat lore.
4. **RULE** — coordinator records adopted/rejected/deferred deltas and the next slice's
   pre-registered bar.
5. **RESUME** — each seat receives a new handoff or a soft steer tied to the same task;
   no hidden restart.

Cadence metrics for this experiment:

- send-to-visible and send-to-applied latency by fidelity;
- duplicate deliveries versus duplicate applications;
- context/task restarts caused by a steer;
- checkpoint recovery success after an interrupt (design-only until safeguarded);
- stale packets traversed before fresh work is visible;
- artifact collisions and lock conflicts;
- human/agent ceremony time versus useful review deltas.

## OUTPUT CONTRACT

Unique cross-critique outputs:

- Fable: `research/reviewed/moonshot-network-spine-fable-cross-2026-07-17.md`
- DeepSeek Review: `research/reviewed/moonshot-network-spine-deepseek-cross-2026-07-17.md`
- Sol/Codex: `research/reviewed/moonshot-network-spine-sol-cross-2026-07-17.md`

Each output must contain:

1. M1-CC three-part cross-critique.
2. Ranked first-slice verdict and the strongest disconfirming evidence.
3. Control-fidelity attack: one loss, duplication, spoofing, or context-corruption
   scenario, plus a mechanical acceptance pin.
4. Jester finding that changes the networking design.
5. One explicit “do not build yet” boundary.
6. MCP calls attempted, successes, failures, and non-MCP fallbacks.
7. A final `CONVERGE / AMEND / REJECT` verdict on the candidate cadence.

Coordinator reconciliation:

- `research/reviewed/moonshot-network-spine-reconciliation-2026-07-17.md`
- Must select one first safe slice, list exact excluded behavior, pre-register tests
  and kill drill, dispose U1–U5, and state the gate for any later T047 cutover.
- Must include an experiment-data table and an explicit morning decision list for
  Daniel. It may authorize a reversible shadow slice under Daniel's “continue as far
  as possible” directive; it may not infer authority for a destructive cutover.

