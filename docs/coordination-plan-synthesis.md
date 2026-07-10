# Multi-Agent Coordination Layer — Synthesis Plan

Status: current  (2026-07-09, P4: Active coordination design)

**Status:** execution plan (merges Claude's Tier-0–5 draft + deepseek-plumbing's grounded plan + the deep-research prior-art survey)
**Date:** 2026-07-04
**Ground truth:** `core/comm/*.py`, `core/foundation/store.py`, `core/foundation/ledger.py`, `core/events/*.py`, `security/acl.json`
**Inputs reconciled:** (A) Claude draft Tier 0–5 · (B) `docs/coordination-plan-deepseek.md` · (C) adversarially-verified prior-art survey (28 sources, 25 claims verified, 24 confirmed / 1 refuted)

---

## 1. Executive Summary + Honest Differentiation Verdict

We are building a **coordination layer** on top of a substrate that already exists and works: the Bifrost bus (`core/comm/bus.py`), advisory locks with fencing tokens (`core/comm/locks.py`), a CAS Store (`core/foundation/store.py`), an append-only Ledger / event firehose (`core/events/`), typed presence (`core/comm/control.py:set_activity`), a fidelity ladder (inform/steer/nudge/halt in `core/comm/nudge.py` + `control.py`), a singleton runner-lock + heartbeat (`core/comm/runner_lock.py`), a launcher (`core/comm/launcher.py`), and an ACL (`security/trust/`, `security/acl.json`).

Both independent design passes (Claude's Tier-0–5 draft and deepseek-plumbing's plan) **converged** on the same spine without coordinating: a **Sync+Plan barrier** with ACK snapshots and a human review board; structured state snapshotting for restart recovery; halt-as-write-gate; event-sourced coordination state on the Ledger; and a build order of **barrier → snapshotting → write-gate → extended primitives**. That convergence is the strongest signal in this document.

### The honest differentiation verdict (grounded in the survey)

The prior-art survey's single most consistent, unanimously-verified (3-0) finding: **no production LLM-agent framework or classical actor system interrupts and resumes mid-token or mid-reasoning.** Every mechanism that exists — LangGraph nodes, AutoGen turns, CrewAI flow methods, Temporal workflow tasks, Akka events — checkpoints at **discrete boundaries**. This directly shapes our design and bounds our claims:

- **What is NOT novel (reuse the primitive, don't reinvent):** event-sourced replay, snapshot-plus-replay recovery, deterministic-replay audit, owner/fate-sharing supervision, turn/boundary checkpointing, CAS/optimistic-locking for concurrent writers. These are mature. Temporal, Akka, Ray, and the ActiveGraph paper (arXiv:2605.21997, "The Log is the Agent") all validate our Ledger-first architecture — but they got there first. We adopt their patterns.

- **What IS genuinely differentiated (the build target):** the **swarm-level coordination fabric** — typed cognitive presence, the graded inform/steer/interrupt/halt fidelity ladder, and CAS/advisory-lock **barriers across many concurrent LLM runners**. The survey found **no** single-agent framework that broadcasts typed per-agent cognitive presence, offers a graded interrupt ladder, or coordinates many concurrent LLM writers at a barrier. **Honest caveat:** the survey rates this differentiation **medium confidence** — it is an *inferred gap* (the survey found no prior art for it) rather than an affirmatively-verified absence. No claim tested "does any framework implement typed cognitive presence?" So we should say "we found no prior art," not "this has never been done."

**Bottom line:** our value is the fabric that binds many runners, plus a human-in-the-loop control surface at a fidelity no surveyed framework offers. Everything underneath it (persistence, replay, recovery) is a well-composed reuse of solved primitives. That is a defensible, non-overclaiming story.

---

## 2. Reconciliation Table (Claude draft × deepseek plan × survey)

| Feature | Claude draft (Tier) | deepseek plan (§) | Agree? | Merged decision |
|---|---|---|---|---|
| **Sync+Plan barrier** (HALT→ACK+snapshot→review→graded release) | Tier 0 (flagship) | §1 | ✅ Full agreement | **BUILD as flagship.** Both specify identical phases. Merged spec in §3. |
| Structured task-snapshot schema (goal·plan·files·next·blockers·confidence) | Tier 0 | §1.2 / §2.2 | ✅ | Merge the two schemas → one canonical schema (§3.2). deepseek's is richer (adds `cognitive_context`, `tool_history`); Claude's is tighter. Take deepseek's fields, keep it bounded ~2–4KB. |
| Halt-as-write-gate (only orchestrator/gate writes shared keys during halt) | Tier 1 | §3.3 | ✅ | **BUILD.** Both frame it as the honest answer to "atomic write during halt." Queue edits, apply on ordered release. |
| CAS on shared-state writes | Tier 1 | §0.3 / §3.2 | ✅ | **REUSE — already exists** (`store.cas`, `store.update_atomic`). No build. |
| Event-sourced salient state on the Ledger | Tier 1 | §3.4 | ✅ | **BUILD (scoped).** Ledger exists; we don't yet use it for *mutable coordination keys*. Move only the 5–10 most critical keys; Store CAS stays for the rest. |
| Cognitive presence enrichment ({state}→{state,goal,tool,confidence,ETA,blocker}) | Tier 2 | §4.1 | ✅ | **EXTEND** `set_activity` with optional fields (`intent`, `tokens_used/limit`, `confidence`). Low-risk additive change. |
| Live cognitive dashboard | Tier 2 | §1.3 (board) | ✅ | Merge: the "coordination board" (barrier UI) and the "cognitive dashboard" are the **same UI** at different moments. Build one board that shows live presence AND halt snapshots. |
| Task-claiming / dispatch | Tier 3 | §4.2 | ✅ | **BUILD (lightweight).** First-claim-wins task board on Ledger + CAS. NOT contract-net. Survey note: Redis Streams consumer-groups (XREADGROUP/XCLAIM) may already give claim+reassign — evaluate before hand-rolling (open decision). |
| Consensus / voting | Tier 3 | §4.3 | ✅ (both say "keep tiny") | **BUILD minimal decision-record** (proposal→vote→decision). NO Raft/Paxos/PBFT. For 2 agents quorum is trivial. |
| Delegation-spawn (request a specialist via launcher) | Tier 3 | §4.4 | ✅ | **BUILD.** `kind=delegate` → launcher spawns with task as prompt, replies to `reply_to`. |
| Contention resolution (advisory locks + escalation) | Tier 3 | §0.2 / §3 | ✅ | **REUSE locks** (exist, with fencing tokens) + add escalation path. Locks are advisory — honest about that limit. |
| Heartbeat liveness | Tier 4 | §4.5 | ✅ | **REUSE** `runner_lock.py` (TTL heartbeat exists). |
| Crash / exhaustion detection | Tier 4 | §0.8 / §4.5 | ✅ | **REUSE** launcher exit-reason detection; **BUILD** stall detection (alive-but-stuck). |
| Task reassignment on failure | Tier 4 | §4.5 | ✅ | **BUILD.** On stall/crash, reassign via task board. Depends on task board + snapshots for context handoff. |
| Wake | Tier 4 | §0.10 (dispatcher) | ✅ | **REUSE** `bifrost_wake` / dispatcher doorbell. |
| Coordination audit / replay | Tier 5 | §4.6 | ✅ | **REUSE Ledger + promoter**; add coordination `kind`s to `SALIENT_KINDS`. Mostly config, not new subsystem. |
| Per-agent (targeted) halt | (implicit) | §1.3 | ⚠️ deepseek-only | **ADOPT.** deepseek adds `halt(targets=[...])` via per-agent flags. Useful. Include in barrier build. |
| Re-hydration on runner restart | (implicit in Tier 0 snapshot) | §2.3 | ⚠️ deepseek-only | **ADOPT.** Restart reads latest snapshot from Ledger, re-announces. Survey (Ray/Akka) confirms: a restarted runner never remembers prior work — recovery MUST come from the Ledger/Store checkpoint. |
| Mid-token / mid-reasoning durable resume | — | out of scope | ✅ both silent | **SKIP.** Survey: nobody does it. Snapshot/interrupt acts at **tool-round boundaries** only. |
| Idempotent-resume discipline | — | §2.3 (implicit) | ⚠️ neither explicit | **ADOPT from LangGraph's documented gotcha.** On resume the node re-runs from its start; side effects must be idempotent and placed AFTER the interrupt point. Neither draft flagged this — the survey did. Fold in as a build rule (§4). |
| CRDTs / OT | — | §5.6 (rejected) | ✅ both reject | **SKIP.** Correct call for 2–5 trusted local agents on one Redis. |
| Orchestrator / Raft / Paxos / full contract-net / DAG workflow engine | — | §6.3 (rejected) | ✅ both reject | **SKIP.** Peer-to-peer, self-organizing; over-engineered for our scale. |

**No hard conflicts surfaced.** The only deltas are features one draft named and the other left implicit (per-agent halt, re-hydration, idempotent-resume) — all folded in above.

---

## 3. FLAGSHIP SPEC — The Sync+Plan Barrier

The barrier turns today's single global flag (`control.pause()` sets `bifrost:control:paused`, every runner checks `is_paused()` at the top of its loop — confirmed at `control.py:34,54,78`) into a real **HALT → ACK → REVIEW → RELEASE** barrier. Every piece below ties to an existing primitive.

### 3.1 The ACK-barrier protocol

**Phase 1 — HALT.** A human (or coordinating agent) calls `halt(reason, targets=None)`:
1. Set the pause flag — **reuse** `control.pause()` (`control.py:54`). If `targets` is given, also set per-agent flags `bifrost:control:halted:<agent>` (**new**, extends the global flag; deepseek §1.3).
2. Broadcast a `kind=halt` message on the bus with `{reason, barrier_id, targets, deadline}` — **reuse** `bus.py` broadcast + doorbell.
3. Initialize a **Redis barrier key** `bifrost:control:barrier:<barrier_id>` = a hash tracking, per targeted agent, `{acked: bool, snapshot_id, ack_at}` — **new**, written by the control plane, updated by agents' ACKs (via CAS to avoid lost updates, `store.cas`).
4. Start a timeout (default **30s**).

**Phase 2 — Agent ACK + snapshot at a tool-round boundary.** Each targeted runner, on detecting the halt between tool rounds (the **same seam** `is_paused()`/`is_nudged()` is already checked — `control.py:9`), MUST:
1. Stop consuming new mail (already done by the `is_paused()` gate).
2. **Finish the current tool call — never kill it mid-flight.** Survey (unanimous) + deepseek §1.3: a `run_command` killed mid-execution corrupts state. Snapshots emit *after* the current tool completes. This is exactly the "boundary, not mid-token" constraint the survey mandates.
3. Emit a `kind=task_snapshot` message (schema §3.2) to the bus **and** promote it to the Ledger.
4. Write its ACK into the barrier key: `HSET bifrost:control:barrier:<id> <agent> {acked:true, snapshot_id, ack_at}`.

**Timeout / stalled agents (open decision #1 — leaning soft):** if an agent has not ACKed within 30s, the board marks it **stalled** (not force-released). The human decides. A truly dead agent's `runner_lock` TTL (20s, `runner_lock.py`) expires on its own, so stale ACKs auto-clear; the barrier does not wedge.

**Phase 3 — Human review board (§3.3).**

**Phase 4 — Graded release (§3.4).**

### 3.2 The structured snapshot schema (canonical, merged)

Bounded ~2–4KB. Full conversation is NOT embedded (it lives on the bus Streams); only a summary + last exchange. Stored as a `kind=task_snapshot` Ledger event; `snapshot:latest:<agent>` in the Store points at the newest id.

```json
{
  "agent_id": "deepseek",
  "barrier_id": "barrier:2026-07-04T14:22:00Z",
  "snapshot_id": "snap:deepseek:2026-07-04T14:22:01Z",
  "snapshot_type": "halt | round_end | task_end | manual | pre_compact",
  "state": "halted",
  "ack_at": "2026-07-04T14:22:01Z",
  "task": {
    "id": "task:coord-001",
    "goal": "Design the multi-agent coordination layer",
    "plan": ["Inventory substrate", "Survey prior art", "Design barrier", "Write doc"],
    "current_step_index": 2,
    "progress_pct": 60
  },
  "files": {
    "editing": ["docs/coordination-plan-deepseek.md"],
    "locked":  [{"path": "docs/coordination-plan-deepseek.md", "token": 47}],
    "recently_touched": ["core/comm/control.py", "core/comm/locks.py"]
  },
  "next_actions": [
    {"intent": "Write write-gate section", "tool": "write_file", "target": "docs/..."}
  ],
  "blockers": [],
  "confidence": 0.85,
  "cognitive_context": {
    "summary": "Mid-design; inventoried bus/locks/CAS/Ledger; now designing the barrier.",
    "key_findings": ["Event sourcing exists (Ledger)", "pause() is global, no per-agent ACK"],
    "open_questions": ["Halt at tool-round boundary vs mid-tool? -> boundary (survey)"]
  },
  "context_stats": {"estimated_tokens_used": 8500, "context_limit": 32000, "percent_full": 26.5}
}
```

Field↔primitive: `files.locked[].token` = the fencing token from `locks.acquire()` (`locks.py:79`), re-validated on resume via `locks.validate_token()` (`locks.py:135`). `context_stats` drives the pre-compaction snapshot trigger.

### 3.3 The human review board (what the UI shows)

One board, doubling as the live cognitive dashboard (Tier 2). Per agent:
- **Status:** running / halted / halted-stalled / never-acked (from the barrier key + presence TTL).
- **Goal** (one line) and **current step / progress %** (from `task`).
- **Files touched + conflict flag** — highlight when two agents list the same path in `files.editing`/`locked`.
- **Next intended action** (`next_actions[0]`) — surfaced BEFORE the tool fires, so the human can steer pre-action.
- **Blockers** and **confidence**.

Live (non-halt) mode reads from enriched `get_activities()` (Tier 2 presence). Halt mode reads the snapshots. Same board.

### 3.4 The graded release

Human issues a `kind=release` message (promoted to Ledger). Actions:
- **resume-all** — clear the global flag (`control.resume()`, `control.py:66`).
- **resume-selected** — clear per-agent halt flags for chosen agents, keep others halted.
- **re-plan** — attach `replan[<agent>] = "new instruction"`, delivered via **STEER** (`nudge.steer_push`) so the runner folds it into context on resume; then clear the halt.
- **reassign / handoff** — move a task to another agent (uses the task board + the halted agent's snapshot as the context package).
- **abort-task** — instruct an agent to abandon and re-scope.

Release payload:
```json
{"kind": "release", "action": "resume_selected", "barrier_id": "...",
 "agents": ["deepseek"], "replan": {"deepseek": "Do the write-gate section first"},
 "file_decisions": {"docs/x.md": [{"edit_id": "...", "decision": "apply"}]},
 "by": "user", "ts": "..."}
```
`file_decisions` is consumed by the write-gate (§4) to apply/discard queued edits in order **before** the gate reopens.

---

## 4. Per-Feature REUSE / BUILD / SKIP / EXTEND / ADOPT Verdicts

Each cites the survey where it bears on the call.

| Feature | Verdict | Rationale (survey-grounded) |
|---|---|---|
| Global pause flag | **REUSE** | `control.pause/is_paused` exists and works (`control.py`). |
| Per-agent targeted halt | **BUILD (small)** | Extends the flag with `bifrost:control:halted:<agent>`. |
| ACK barrier key + timeout | **BUILD** | New. The survey's distributed-barrier gap; nobody ships this for LLM swarms. |
| Task-snapshot schema + emit | **BUILD** | Snapshot = our LangGraph-equivalent, but coarser (per-round, not per-node) — the survey says coarse is the honest fit for open-ended agentic loops. |
| Snapshot storage / audit | **REUSE Ledger** | Genuine event sourcing already exists (`core/events/`). Survey (Temporal/Akka/ActiveGraph, 3-0): append-only log = source of truth. Don't reinvent. |
| Coordination replay ("what did the swarm decide and why") | **REUSE + tiny config** | Add coordination `kind`s to `SALIENT_KINDS` (currently `{handoff, decision, completion, blocker}`, `promoter.py:19`). Survey: deterministic replay from the log is a solved primitive. |
| **Mid-token / mid-reasoning durable resume** | **SKIP** | Survey's #1 unanimous finding: **no system does it.** Out of scope. Act at tool-round boundaries only. |
| **Idempotent-resume discipline** | **ADOPT (rule)** | From LangGraph's documented gotcha (re-runs the whole node on resume; verified 3-0, GitHub #4796/#6792). **Build rule:** any side effect performed around an interrupt/resume point must be idempotent (upsert / check-before-create) and placed AFTER the interrupt point. Applies to re-hydration and reassignment handoffs. |
| Re-hydration on restart | **BUILD** | Restart reads `snapshot:latest:<agent>`, re-announces. Survey (Ray max_restarts, Akka replay, 3-0): a restarted runner NEVER remembers prior work — recovery must come from the checkpoint, exactly as Ray requires manual checkpointing. |
| CAS on Store keys | **REUSE** | `store.cas` / `store.update_atomic` exist (`store.py:173,187`). Survey scope-gap: WATCH/MULTI/EXEC vs Lua vs CRDT tradeoffs produced no verified claim — so lean on the confirmed event-sourcing backbone, not on unverified CAS-vs-CRDT claims. |
| Halt-as-write-gate (queue edits, ordered apply) | **BUILD (~100 lines)** | Two-phase-commit variant; not novel but not present. The honest file-level answer (files aren't CAS-guarded; last-writer-wins today). |
| Event-sourced coordination state (5–10 hot keys) | **BUILD (scoped)** | Move task-status / assignment / resource-ownership from Store-LWW to Ledger projections. Survey validates the pattern; scope tightly (open decision #2). |
| Advisory locks + fencing tokens | **REUSE** | Exist (`locks.py`), correctly implemented (monotonic token, TTL). Honest limit: advisory — coordinates cooperating peers, not adversarial ones. |
| Cognitive presence enrichment | **EXTEND** | Add optional `intent`/`tokens`/`confidence` to `set_activity`. Survey (medium conf): typed cognitive presence is our differentiated territory — no prior art found (but not an affirmed absence). |
| Coordination board / dashboard UI | **BUILD (one UI)** | Merge barrier board + live dashboard. |
| Task board (first-claim-wins) | **BUILD (lightweight)** | NOT contract-net (survey: over-engineered for 2–5 trusted agents). **Evaluate Redis Streams consumer-groups (XREADGROUP/XCLAIM/XAUTOCLAIM) first** — the survey flags they likely already provide claim+failure-reassignment (open decision #3). |
| Consensus / voting | **BUILD (minimal decision-record)** | proposal→vote→decision. Survey: NO Raft/Paxos/PBFT for local trusted agents. |
| Delegation-spawn | **BUILD** | `kind=delegate` → launcher. Reuses `launcher.py`. |
| Stall detection + auto-recovery + escalation | **BUILD** | Launcher detects crash/exhaustion today; add alive-but-stuck detection + restart + escalate-after-3-crashes. |
| Heartbeat / wake | **REUSE** | `runner_lock.py` heartbeat + dispatcher doorbell. |
| CRDTs / OT | **SKIP** | Survey + both drafts reject. Correct for our scale. |
| Orchestrator / Raft / DAG engine / full contract-net | **SKIP** | Peer-to-peer, self-organizing. Over-engineered. |

---

## 5. Locked Build Order (each slice independently testable)

Dependency-ordered. **[NEW]** = net-new module; **[EXT]** = extends existing; **[CFG]** = config/wiring only.

**Phase A — Barrier foundation** (flagship; unlocks human review of live agent state)
- **A1 [EXT]** Per-agent halt flags + `halt(targets=[])` API. *Test:* halt one agent, resume-selected; others untouched.
- **A2 [NEW]** Barrier key + ACK protocol (agent writes ACK via CAS; 30s timeout → stalled). *Test:* 2 agents ACK within timeout; a non-acking agent shows stalled.
- **A3 [NEW]** Canonical `task_snapshot` schema + runner emits on halt at a tool-round boundary. *Test:* snapshot present within 1 tool-round of halt; emitted only after the in-flight tool completes.
- **A4 [NEW]** Coordination board UI (status, goal, files+conflict flag, next-action, blockers, confidence). *Test:* board renders real snapshots + conflict flag when two agents touch one path.
- **A5 [NEW]** Graded release (resume-all / resume-selected / re-plan via STEER / reassign / abort). *Test:* each release action verified end-to-end.
- **A6 [CFG]** Barrier audit: add `halt, task_snapshot, release` to `SALIENT_KINDS`. *Test:* replay the full barrier sequence from `EventQuery`.

**Phase B — Snapshotting & recovery** (depends on A3's schema)
- **B1 [NEW]** Snapshot round-trip to Ledger + `snapshot:latest:<agent>` Store projection. *Test:* emit→query→validate fields; latest-id matches.
- **B2 [EXT]** Auto-snapshot on round boundaries (every N rounds, default 5) + task-end.
- **B3 [NEW]** Re-hydration on runner start (idempotent per §4 rule; re-validate locks via fencing token; announce `kind=rehydrated`). *Test:* kill+restart runner → reads snapshot → re-announces; no double-executed side effects.
- **B4 [EXT]** Pre-compaction snapshot when `percent_full` > 80%. *Test:* at 85% context → snapshot then compaction.

**Phase C — Write gate** (depends on Phase A; active only during halt)
- **C1 [NEW]** Write-gate flag (halt → closed; resume → open). *Test:* write rejected during halt, accepted after.
- **C2 [NEW]** Edit queue (`queue_edit` / `drain_edits`) + same-path conflict detection. *Test:* two agents queue edits to one path → conflict list.
- **C3 [EXT]** Release consumes `file_decisions` (apply/discard/defer, ordered) before reopening the gate. *Test:* human picks winners; edits applied in order.
- **C4 [NEW]** Event-source the 5–10 critical coordination keys (task status/assignment/ownership) as Ledger projections. *Test:* concurrent transitions detected at projection time.

**Phase D — Extended primitives** (mostly independent; can parallelize after A)
- **D1 [EXT]** Presence enrichment (`intent`/`tokens`/`confidence` on `set_activity`) — feeds the live board. *Test:* board shows intent before tool fires.
- **D2 [NEW]** Task board (first-claim-wins on Ledger+CAS) — **or** adopt Redis consumer-groups (decide first). *Test:* first claim wins; second rejected.
- **D3 [NEW]** Stall detection + auto-restart + escalate-after-3-crashes. *Test:* stalled runner detected & restarted; 3 crashes → human alert.
- **D4 [NEW]** Task reassignment on failure (uses D2 board + snapshot as handoff package; idempotent per §4). *Test:* failed agent's task reclaimed with context.
- **D5 [NEW]** Delegation-spawn (`kind=delegate` → launcher). *Test:* delegated subtask spawned, replies to `reply_to`.
- **D6 [NEW]** Minimal decision-record (proposal→vote→decision). *Test:* quorum → decision recorded to Ledger.

---

## 6. Open Design Decisions (need a human call)

1. **Barrier ACK timeout: soft or hard?** Recommendation: **soft** (mark stalled, human decides; stale ACKs auto-clear via runner_lock TTL). The human should always have final say; a hard force-release risks discarding a snapshot mid-write. *Decide before A2.*

2. **How far to event-source coordination state?** Recommendation: start with **5–10 keys** (task status, agent assignment, resource ownership); leave everything else on Store CAS. Don't event-source the whole Store. *Decide before C4.* Note: the survey did not verify CAS-vs-CRDT-vs-event-sourcing tradeoffs (scope gap), so lean on the confirmed event-sourcing backbone and keep this scope small.

3. **Task board: hand-rolled first-claim-wins, or Redis Streams consumer-groups?** The survey flags that Redis consumer-groups (XREADGROUP + XCLAIM/XAUTOCLAIM) likely already provide claim + failure-driven reassignment as a built-in primitive — potentially subsuming D2 *and* part of D4 (reassignment). Recommendation: **spike the consumer-group approach before building D2 by hand.** *Decide before D2/D4.*

**Secondary (lower stakes):** snapshot = summary-only vs full conversation (lean summary + last exchange; full history is already on the bus); write-gate mandatory vs advisory during halt (lean mandatory — a real gate, not a suggestion); build task board before or alongside delegation (lean board first, it's simpler).
