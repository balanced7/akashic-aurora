---
akashic_id: art_20260714_deepseek-r5-cost-telemetry-design-half-b_85a3eb
akashic_sha: 10b9b311bc7c
status: draft
type: report
date: 2026-07-14
title: "DeepSeek R5 Cost Telemetry — Design Half (blind, 2026-07-14)"
gist: "Tier: FULL FENCE (M1-LITE gate 1a: stamps the task ledger's write path — coordination primitive) Confidence tags: CERTAIN / DESIGN / INFERRE"
tenant: solo
visibility: fleet
seats: []
category: [coordination, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_design-brief-r5-cost-telemetry-per-slice_30947f
    rel: cites
created: "2026-07-14T10:47:53"
updated: "2026-07-23T21:42:14"
---
<!-- GENERATED PROJECTION of art_20260714_deepseek-r5-cost-telemetry-design-half-b_85a3eb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek R5 Cost Telemetry — Design Half (blind, 2026-07-14)

Tier: FULL FENCE (M1-LITE gate 1a: stamps the task ledger's write path — coordination primitive)
Confidence tags: CERTAIN / DESIGN / INFERRED / UNCERTAIN per M1-CF
Inputs: as listed in research/r5-cost-telemetry-design-brief-2026-07-14.md §(2)

---

## REFUTE-FIRST: candidates considered and rejected

### R1. Per-agent counter accumulation with per-task attribution
**Rejected.** CERTAIN. The wishlist asks for per-arc ROI — "Daniel sees ROI per slice."
This requires per-TASK cost stamps, not per-agent running totals. Two agents working
concurrent tasks (e.g., claude builds T052 while deepseek reviews T051) share the same
turn_metrics streams. A per-agent counter doesn't know which task a turn served — you
can attribute "deepseek used 12 turns today" but not "5 of those were for T051."

Counter-argument: "just partition by task claim window." But the task lifecycle
(claimed→in_progress→verifying→done) overlaps with the runner's turn loop — the runner
doesn't pause to "switch tasks" between turns. A single runner session spans multiple
tasks if tasks are small, or multiple sessions span one task if it's large. The
attribution boundary is genuinely fuzzy.

### R2. Per-WINDOW cost (abandon per-task entirely)
**Rejected.** DESIGN. Per-window cost (e.g., "today: 47 turns, 12 fence rounds") is
honest about attribution but defeats the purpose: the wishlist explicitly asks for
per-arc ROI. "This sprint cost 200 turns" is less useful than "T052 cost 8 turns,
T055 cost 3." Per-window is the FALLBACK render (honest refusal), not the design.

### R3. Stamp at claim (snapshot counters at claim transition)
**Rejected.** CERTAIN. Claim happens BEFORE any work. A task can be claimed, sit idle
for days, then start. The claim-time snapshot captures the counters from OTHER tasks'
work (the agent was doing T051 when it claimed T052). Worse: if two agents claim
concurrently, both snapshots see each other's in-flight turns — the attribution is
doubly wrong.

### R4. Stamp at done (snapshot counters at close)
**Rejected.** DESIGN. Done is too late to differentiate: the counters include every
turn from claim→done, which for a small task (verification only) may be 1 turn, and
for a build task may be 50. That IS the right span, but the stamp is at the wrong end
of the pipeline — it captures ALL turns in the window, including turns for OTHER tasks
the same agent touched during the span (a reviewer reviews two tasks in one session).
The stamp at done doesn't know which turns were for THIS task.

### R5. Require per-turn task tagging (the runner declares which task each turn serves)
**Rejected.** CERTAIN. This is the correct attribution mechanism but it's a runner
surface change, not a ledger one — and the DeepSeek runner is stateless (no task
awareness in its loop). Adding task-tagging to every runner's turn loop is a
cross-cutting change with fleet-wide blast radius. Wrong slice — belongs to a
future "task-aware runners" arc, not the cost telemetry join.

### R6. Materialize cost from git history (commit count + diff size)
**Rejected.** CERTAIN. Commits are free (squash vs many-small). A fence round is one
commit; a bug fix is one commit. Diff size measures churn, not cost — a one-line bug
fix that took 20 turns of investigation looks cheaper than a 200-line mechanical rename
that took one turn. Git is a proxy so lossy it's misleading.

### R7. Materialize cost from the event_log firehose
**Rejected.** DESIGN. The event_log has `turn_metrics` events per turn with agent, kind,
duration, and tool_count. Querying "all turn_metrics events between two timestamps for
agent X" IS attribution-ready — the firehose has the data. But scanning a time-bounded
firehose per task at render time is O(turns-in-window), and the firehose is capped at
100k events. For long-lived tasks spanning many sessions, the window may exceed the cap.
Viable as a BACKFILL path for recent tasks; not the primary mechanism.

---

## DECISION 1: WHAT gets stamped — the task-cost record's shape

### D1a. Per-agent, per-task cost ACCUMULATOR (not a single snapshot)

The stamp is NOT a one-time snapshot at a lifecycle transition. It's an ACCUMULATOR
that aggregates turns across the task's entire active window. Two mechanisms:

**A. At each turn close (the HOT path):** if the runner's agent_id matches a task's
owner AND that task is IN_PROGRESS or VERIFYING, increment the task's cost counters.
This is a checked-increment: two Redis calls (read task status + HINCRBY on the cost
hash). Fail-open — a metrics hiccup never blocks the turn.

**B. At done transition (the COLD wrap-up):** finalize the accumulator into the task
record's durable fields. This is the stamp that survives Redis loss.

**CERTAIN** (citation-grounded):
- `turn_metrics.record()` at `core/comm/turn_metrics.py:113-133` already fires at
  every turn close with `{agent, ask_kind, duration_s, progress_points, outcome,
  prompt_len_band, tool_count, tokens?}`. This is the injection point for the
  hot-path increment (mechanism A).
- `task_ledger.transition()` at `core/coord/task_ledger.py:169-217` is the one guarded
  mutation. The DONE transition (lines 210-214) already stamps `commit` and
  `verified_by` — adding cost fields here is the natural extension (mechanism B).
- The task record schema at `state/coord/tasks.json` has `{id, title, owner, status,
  commit, verified_by, history[], created, updated}`. Cost fields are new top-level
  keys: `cost_turns`, `cost_duration_s`, `cost_tool_calls`, `cost_tokens` (absent =
  pre-T056 task; backfill rule below).

### D1b. The counters (four fields, minimal)

| Field | Source | What it counts |
|-------|--------|----------------|
| `cost_turns` | `turn_metrics.record()` per-turn increment | Number of model turns attributed to this task |
| `cost_duration_s` | `turn_metrics.record()` `duration_s` sum | Wall-clock seconds of model thinking (not human wait time) |
| `cost_tool_calls` | `turn_metrics.record()` `tool_count` sum | Tool invocations (reads, writes, searches — the agent's "actions") |
| `cost_tokens` | `turn_metrics.record()` `tokens` dict (prompt+completion) | Token consumption (optional; present only when the model reports it) |

**Why these four, not more:**
- Turns = the coarse unit (one model invocation = one turn). Already recorded.
- Duration = the time unit. Already recorded.
- Tool calls = the action unit. Already recorded.
- Tokens = the financial unit. Already recorded (optional — DeepSeek reports; Claude may not).

**What is deliberately NOT counted:**
- Fence rounds (a process cost, not a task cost — belongs to the method baseline's own metrics)
- Human time (unmeasurable from inside the system)
- Bus messages (the bus is infrastructure; counting per-task messages would require
  per-message task tagging — R5 territory)
- "Cognitive load" signals (reread rate, coordination ratio — these are health signals for
  the agent membrane, not task cost)

**CERTAIN.** The four fields exist in `turn_metrics.record()` today. No new counters to
fabricate — this is a JOIN, not a new measurement surface.

---

## DECISION 2: attribution — the concurrent-agent problem

### D2. OWNER-BASED attribution with honest refusal

A turn is attributed to a task IFF:
1. The runner's `agent_id` matches the task's `owner` field, AND
2. The task's `status` is IN_PROGRESS or VERIFYING, AND
3. At most ONE such task exists for that owner (the one-in-progress gate already
   enforces this globally — Phase 1 sequential-correct).

If zero tasks match (agent has no active task): the turn is UNATTRIBUTED. No cost
is stamped — the counters simply don't increment for that turn.

If multiple tasks match (should not happen under the one-in-progress gate, but
defensively): attribute to NONE — honest refusal. The turn's cost is lost to task
attribution (it still exists in the agent's turn_metrics stream; just not stamped
on any task).

**CERTAIN.** The one-in-progress gate at `task_ledger.py:203-207` guarantees at most
one IN_PROGRESS task globally. The VERIFYING status can overlap with another agent's
IN_PROGRESS (the reviewer and builder are different agents with different owners).
So: per-owner, at most one active task. The gate is already enforced — we just read it.

### D2a. The concurrent-agent case (two agents, two tasks, overlapping windows)

claude owns T052 (IN_PROGRESS), deepseek owns T051 (VERIFYING). Both agents are
active concurrently. claude's turns increment T052's counters; deepseek's turns
increment T051's counters. No cross-contamination — attribution is by owner, not
by global window.

**CERTAIN.** The `owner` field on tasks is the attribution key. It already exists
and is enforced (only the owner can claim a task).

### D2b. The multi-session case (one task, many runner sessions)

A task spans multiple runner restarts (e.g., a build task takes two sessions).
The accumulator lives in Redis (hot path) and is finalized to the task record at
done (cold wrap-up). Each session's turns increment the same accumulator — the
cost accumulates across sessions correctly because the task's `owner` doesn't change.

**CERTAIN.** The Redis accumulator is keyed by task ID, not session. It survives
runner restarts.

---

## DECISION 3: WHEN stamps land — the lifecycle placement

### D3a. HOT PATH: increment at turn close (best-effort, fail-open)

In `turn_metrics.record()`, after recording the row: if the agent has an active
task (owner match + IN_PROGRESS/VERIFYING), HINCRBY the task's cost hash in Redis.

The check: one `read_ledger()` call (Redis GET, ~0.1ms) to find the one active
task for this agent. If found, three HINCRBY calls (turns, duration×100 as int,
tool_calls) + one HINCRBY for tokens if present. Four Redis ops total. Fail-open:
any Redis error = skip the increment; the turn still recorded.

**DESIGN.** The `record()` function already has a try/except at line 113. The
increment sits inside the same try block — one additional Redis call, same fail-open
contract.

### D3b. COLD WRAP-UP: finalize at done transition

When `task_ledger.transition(tid, DONE)` fires:
1. Read the task's cost accumulator from Redis (`{ns}:task_cost:{tid}`).
2. Write the accumulated values into the task record as `cost_turns`, `cost_duration_s`,
   `cost_tool_calls`, `cost_tokens`.
3. Delete the Redis accumulator key (cleanup).
4. If the accumulator doesn't exist (Redis loss mid-task, or pre-T056 task): write
   `cost_turns: null` (backfill rule, Decision 6).
5. The `save()` call persists to git — the cost is now durable.

**CERTAIN** (citation-grounded to `task_ledger.py:210-214` — the done gate already
stamps `commit` and `verified_by`; adding cost fields is the same pattern).

### D3c. Why NOT at verifying transition

Verifying is a checkpoint, not the end. A task may bounce verifying→in_progress→verifying
multiple times. Stamping cost at each verifying transition would double-count turns
from the first pass. Only DONE finalizes.

### D3d. Why NOT at claim or start

Claim happens before work; start is too early (the accumulator should be zero at
start, but we don't need to STAMP zero — absence IS zero per the backfill rule).

---

## DECISION 4: the RENDER — what `format_state` shows

### D4a. Per-task cost line (in the DONE section)

```
DONE (closed — do NOT redo):
  T052 - R1 Delta door  @88751bb  cost: 8 turns · 142s · 37 tools · 24k tok
  T051 - Something      @abc1234  cost: 3 turns · 28s · 12 tools
```

Fields render only when present: `cost_turns` is always rendered (it's the headline);
`cost_duration_s` renders as human-readable (142s, not 142.37); `cost_tool_calls` renders;
`cost_tokens` renders with k/M suffix. Absent fields (null or missing key) are simply
absent from the render — no "?s" placeholders.

### D4b. Active task cost line (in the IN PROGRESS section)

```
IN PROGRESS:
  T056 - R5 Cost telemetry  (in_progress, deepseek)  cost so far: 12 turns · 204s · 51 tools
```

The "so far" is read from the Redis accumulator directly (not the task record).
If the accumulator is missing: render nothing (the task just started, or Redis is down).

### D4c. Budget discipline

The cost line is ONE line per task, ≤120 chars. If it overflows, the token count
drops (least important). If it still overflows, drop the duration. The turn count
is the minimum viable cost signal — it always renders.

### D4d. Summary line

The existing summary line `(done N | active M | next P | proposed Q | blocked R)`
gains an aggregate: `(done 31 [cost: 420 turns · 3.2k tools] | active 1 [12 turns so far] | ...)`.

**CERTAIN.** `format_state` at `task_ledger.py:304-356` already renders the
read-state-first block. The cost join adds per-task lines and one summary aggregate.
Existing format preserved; cost is additive.

---

## DECISION 5: the GOODHART guard

### D5. Costs are READ-ONLY, never gated

The cost fields on a task record are NEVER used to gate any transition. A task with
high cost can still be marked DONE. A task with zero cost (backfill) can still be
marked DONE. The cost is an observation, not a permission.

**CERTAIN.** The done gate at `task_ledger.py:210-214` already checks `commit` and
`verified_by` — adding cost to the gate would be a new gate, which is explicitly NOT
the design.

### D5a. The metric READS ROI, never scores agents

The cost fields are per-TASK, not per-AGENT. There is no "deepseek's average cost"
render. The aggregation is per-arc (from task titles' prefixes: T045-T049 = lane arc,
T052 = delta door, T055 = pre-flight). The wrap-time scorecard groups by arc prefix
and renders per-arc totals — but never per-agent.

**CERTAIN.** The T034 lineage (never codify pace) extends to cost: the ledger render
shows per-task cost so Daniel can read ROI per slice. It does NOT show an agent
leaderboard. If a future surface adds per-agent aggregation, it must be explicitly
gated — the cost schema does not prevent it, but the DEFAULT render does not do it.

### D5b. Honest bounds (M8)

- Duration is wall-clock model time, NOT human time. A 142s task means the model spent
  142 seconds processing — not that Daniel waited 142 seconds (parallel work, async).
- Tool count is calls, not usefulness. A 50-tool task may be efficient (reads are cheap)
  or wasteful (re-reading the same file). The number is honest about what happened;
  interpreting it is the reader's job.
- Tokens are provider-reported, not independently verified. The field is optional.
- All counters are best-effort. Redis loss, runner crash, or an unattributed turn
  means the cost is UNDER-reported, never over-reported.

---

## DECISION 6: BACKFILL — tasks closed before T056

### D6. Pre-T056 tasks render absent cost

Tasks with `cost_turns: null` (or missing key) render NO cost line. The task appears
identically to how it renders today. The absent field IS the signal: "this task predates
cost telemetry."

### D6a. No backfill from event_log

The event_log firehose has `turn_metrics` events going back to the start of recording
(2026-07-07), but attributing them to tasks retroactively requires the same "which task
was this turn for?" question — and the answer wasn't recorded at the time. Backfill
would fabricate attribution. Honest refusal: pre-T056 tasks carry no cost.

**CERTAIN.** The brief §(4)(d) explicitly asks: "tasks closed before this ships render
what? (strangler: no fabricated costs — absent stamps render absent)." This matches.

---

## DECISION 7: FAILURE modes

### D7a. Redis loss mid-task
The accumulator (`{ns}:task_cost:{tid}`) disappears. Subsequent turns still fire
HINCRBY (which creates the key anew with value 1). The cost is UNDER-reported by
the turns lost during the outage window. At done, the final accumulator value is
written — the task record shows partial cost. This is honest: the system reports
what it measured.

### D7b. Runner crash mid-turn
`turn_metrics.record()` fires at turn CLOSE. A crash before close = the turn never
recorded → no cost increment. The turn's work is lost anyway (reply never sent).
Under-report matches reality.

### D7c. Task spanning runner restarts
The accumulator is keyed by task ID in Redis, not by process. A restart picks up
the same accumulator. No double-count, no gap — the accumulator survives the process.

### D7d. Counter rollover
Python ints don't roll over. The Redis HINCRBY values are strings representing ints.
For a task with >2^63 turns (impossible), it would fail. Not a real failure mode.

### D7e. Two runners for the same agent (should be impossible — S4 duplicate guard)
If the guard fails: both runners increment the same task's accumulator. The cost is
OVER-reported (each turn counted twice). The guard's failure is the real bug; the
cost over-report is a symptom, not a separate problem.

---

## DECISION 8: what the cost telemetry does NOT do

- It does NOT score agents (D5a).
- It does NOT gate any transition (D5).
- It does NOT backfill pre-T056 tasks (D6).
- It does NOT measure "value" or "quality" — 8 turns that ship a buggy feature cost
  the same as 8 turns that ship a clean one. Cost ≠ value.
- It does NOT track human time, coordination overhead, or fence-round latency.
- It does NOT replace the progress bars (turn_metrics.estimate) — cost is retrospective;
  progress is prospective. Both exist; neither replaces the other.
