# Multi-Agent Coordination Layer — Research & Design

**Author:** deepseek-plumbing (COORD-RESEARCH tag)
**Date:** 2026-07-04
**Status:** design proposal — parallel plan (synthesize with Claude's)
**Ground truth:** `core/comm/*.py`, `core/foundation/store.py`, `core/foundation/ledger.py`, `core/events/*.py`, `security/acl.json`

---

## 0. Honest Inventory — What We ACTUALLY Have (Not What We Wish We Had)

Before designing anything new, here is the real substrate — every cited file was READ, not assumed:

### 0.1 The Bifrost Bus (`core/comm/bus.py`)
Redis Streams per-agent inbox (`bifrost:inbox:<agent>`), broadcast stream (`bifrost:broadcast`), per-agent cursor hash (`bifrost:cursor:<agent>`). Fan-out is correct (each agent has its own cursor on broadcast — not consumer-group load-balancing). Messages carry `{frm, to, kind, content, ts, meta, parts[]}`. Parts support inline + blob-by-reference. Doorbell (`PUBLISH bifrost:bell:<to>`) fires after each XADD for ~ms wake. Maxlen-bounded (ephemeral transport). **Salient kinds** (`handoff, decision, completion, blocker`) are promoted to the durable Ledger via `promoter.py`.

### 0.2 Advisory Path/Resource Locks (`core/comm/locks.py`)
`LockManager` per agent. `acquire(path)` → `{ok, token}`. Redis-backed, but **paths are any string** — usable for resources too. Carries a **monotonic fencing token** (via `INCR bifrost:lock:_seq`), TTL auto-expiry (15 min default), re-entrant self-refresh, fail-soft (offline → no coordination). `validate_token(path, token)` at the commit gate. `path_conflict()` is the shared check. 11 tests.

### 0.3 Store with CAS (`core/foundation/store.py`)
`HybridStore` (dual-write: Redis + File). `cas(key, expected, value)` — atomic in Redis via Lua (`GET==ARGV[1] then SET`), under `threading.RLock` in FileStore. `update_atomic(key, fn, retries=8)` — optimistic read-modify-write, raising `CASConflict` on exhaustion. `check_drift()` / `reconcile()` for divergence healing. Full Redis command surface: key/value, hash, list, set, sorted-set, expiry, keyspace scan. 8 tests.

### 0.4 Append-Only Ledger / Event Firehose (`core/foundation/ledger.py`, `core/events/`)
`Ledger.emit(stream, event)` → cursor id; `consume(stream, after_id)` → `[(id, event)]`. `HybridLedger` = dual-write Redis Streams + File JSONL. `EventLog` wraps this as the raw firehose (`events:raw` + per-agent `events:<agent>:raw`), with time-index via `EventIndex`. `EventQuery` provides `events_in_window(start, end)`, `search(query, kind=, agent=, since=, until=)`, and `get(ref)`. **This is genuine event sourcing** — state is a projection of the ordered log.

### 0.5 Presence & Activity (`core/comm/bus.py`, `core/comm/control.py`)
`Bus.register(ttl, card={runtime_class, wake_mode, door, caps})` — A2A-style AgentCard. `Bus.presence()` → all online agents with their cards. `control.set_activity(agent, state, detail)` — typed activity (thinking/reading/searching/inspecting/recalling/running/writing/working), TTL 25s, read via `get_activities()`.

### 0.6 Fidelity Ladder (`core/comm/control.py`, `core/comm/nudge.py`, `core/comm/interject.py`)
Four tiers, from softest to hardest:
1. **INFORM** — a regular chat message, queued in the inbox. Zero interruption.
2. **STEER** — `nudge.steer_push(agent, text)` queues a fact on a per-agent list; the runner drains it between tool rounds and folds it into its current context. DOES NOT interrupt. 15 min TTL.
3. **NUDGE** — `nudge.nudge(agent, reason)` sets a per-agent flag; the runner checks `is_nudged(self)` between tool rounds (SAME seam as pause). The runner clears + acks on pick-up. 120s TTL.
4. **HALT** — `control.pause(reason)` sets a global Redis flag; ALL runners check `is_paused()` at the top of their loop. Blocks consuming/answering until `resume()`.

The **interjection classifier** (`interject.py`) uses heuristic regex → optional LLM fallback for ambiguous messages. Classifies as `halt | steer | ask | resume`.

### 0.7 Runner Singleton-Lock (`core/comm/runner_lock.py`)
At most ONE live runner per agent id. `acquire(agent, token)` via Redis `SET NX` + TTL (20s). `heartbeat()` refreshes TTL; if the lock was stolen (expired + reclaimed), `heartbeat` detects the token mismatch and returns False. `release(agent, token)` only frees if we still hold it. Instance token = `agent:pid:uuid` for uniqueness.

### 0.8 Launcher (`core/comm/launcher.py`)
`Launcher` singleton: spawns agent processes from a registry (`security/launcher.json` + built-in defaults). Tracks lifecycle (running/exited/crashed/killed/never_launched). Exit-reason detection (token_exhausted, auth_error, killed, error, clean). Auto-restart (optional). Kill = graceful `terminate()` then `kill()` after 3s timeout. Monitor thread reaps zombies every 2s.

### 0.9 Security ACL (`security/acl.json`)
Role-based: super_admin (claude, all caps), admin (deepseek, write + bus but no exec/admin.grant), member (deepseek-ui/plumbing, scoped read/write). `caps` list, `path_scope` (glob prefixes for write), `bus_send_kinds` (kind-scoped bus sending). Unknown agents → quarantined (read-only, fail-closed).

### 0.10 Dispatcher (`core/comm/dispatcher.py`)
One `PSUBSCRIBE bifrost:bell:*` process. On notice: non-consuming digest peek → escalation gate (`should_escalate`: kind in {request, handoff, question, blocker} or importance in {high, urgent}) → dispatch via invoker registry. Dropped bells = delayed wake, not lost messages (Stream + cursor are durable).

---

## 1. SYNC+PLAN Barrier — Done Right

### 1.1 What We Have Today

`control.pause()` sets a single Redis key. Every runner's loop checks `is_paused()` before consuming mail. That's it. There is NO:
- ACK from agents that they've actually stopped
- Visibility into what each agent was doing when stopped
- Structured task snapshot
- Human review board
- Granular release (resume-all vs resume-selected vs re-plan)

### 1.2 What the Barrier Should Be

**Phase 1 — HALT broadcast.** Human (or a coordinating agent) initiates `halt(reason="...")`. The control plane:
1. Sets the global `bifrost:control:paused` flag (existing mechanism)
2. Sends a `kind=halt` broadcast message with the reason
3. Starts a timeout (default 30s — agents must ACK or be considered stalled)

**Phase 2 — Agent ACK + snapshot.** Each runner, upon detecting the halt (via `is_paused()` or the `kind=halt` message), MUST:
1. **Stop consuming new mail** (already done by `is_paused()` check)
2. **Finish or safely abort its current tool round** (the tool may be mid-flight; the runner should complete the current tool call, NOT kill it mid-execution — a `run_command` killed mid-way leaves state corruption)
3. **Emit a structured `task_snapshot`** to the bus + Ledger. The snapshot is a message `kind=task_snapshot` with content:

```json
{
  "agent_id": "deepseek",
  "state": "halted",
  "ack_at": "2026-07-04T14:22:01Z",
  "task": {
    "goal": "Research and design the multi-agent coordination layer",
    "plan": ["Inventory current state", "Research prior art", "Design barrier protocol", "Write doc"],
    "current_step": "Design barrier protocol",
    "current_step_index": 2,
    "progress_pct": 60
  },
  "files": {
    "editing": ["docs/coordination-plan-deepseek.md"],
    "locked": ["docs/coordination-plan-deepseek.md"],
    "recently_touched": ["core/comm/control.py", "core/comm/locks.py"]
  },
  "next_actions": [
    {"intent": "Write §2 (state snapshotting)", "tool": "write_file", "target": "docs/coordination-plan-deepseek.md"}
  ],
  "blockers": [],
  "confidence": 0.85,
  "cognitive_context": {
    "summary": "Mid-design: have inventoried the bus, locks, Store CAS, Ledger, and fidelity ladder. Currently designing the SYNC+PLAN barrier protocol. Next: §2 state snapshotting.",
    "key_findings": ["We have event sourcing (Ledger) but no barrier protocol", "pause() is global, no per-agent ACK"],
    "open_questions": ["Should halt block tool-round mid-execution or wait for completion?"]
  }
}
```

**Phase 3 — Human reviews the board.** The UI renders a "coordination board":
- Each agent's status (halted / halted-stalled / running / never-acked)
- Their current task/goal (one-line)
- Files they're touching (conflict detection)
- Their next intended action
- Blockers they've declared
- Confidence level

The human can then:
- **RESUME-ALL** — unfreeze everything (current `resume()`)
- **RESUME-SELECTED** — unfreeze specific agents, keep others halted
- **RE-PLAN** — inject new instructions to one or all agents before resuming
- **ABORT-TASK** — tell an agent to abandon its current task and re-scope
- **HANDOFF** — reassign a task from one agent to another

**Phase 4 — Structured release.** The release message carries:
```json
{
  "kind": "release",
  "action": "resume_selected",
  "agents": ["deepseek"],
  "replan": {
    "deepseek": "Continue, but prioritize the atomic-write section first"
  },
  "by": "user",
  "ts": "..."
}
```

### 1.3 Implementation Notes

- **Halt ACK timeout**: If an agent doesn't ACK within 30s, the board shows it as "stalled." The human can force-release (the agent's runner_lock TTL will eventually expire anyway).
- **Tool-round boundary**: The runner should NOT kill a mid-flight tool. Current `is_paused()` is checked BETWEEN tool rounds — that's correct. The snapshot is emitted AFTER the current tool completes, not mid-execution.
- **Per-agent halt**: Extend the current global pause to support `halt(targets=["deepseek"])` — sets per-agent halt flags (`bifrost:control:halted:<agent>`) in addition to the global flag. A targeted halt freezes specific agents; a global halt freezes all.
- **Ledger projection**: Every barrier event (halt, snapshot, release, re-plan) is promoted to the Ledger via `promoter.py` (add `halt`, `task_snapshot`, `release` to `SALIENT_KINDS`).

### 1.4 Build Plan (Sliced)

| Slice | Deliverable | Tests |
|---|---|---|
| B1 | Per-agent halt flags + `halt(targets=[])` API | halt-specific agent, then resume-selected |
| B2 | Structured `task_snapshot` schema + runner emit-on-halt | snapshot emitted within 1 tool-round of halt |
| B3 | Coordination board UI (halt status, task summaries, conflict detection) | UI renders real snapshots |
| B4 | Structured release (resume-all, resume-selected, re-plan, abort-task) | each release action verified end-to-end |
| B5 | Barrier audit trail (all events → Ledger) | replay barrier events from query |

---

## 2. Real State Snapshotting — Preserve Cognitive Context

### 2.1 What We Have Today

When an agent is paused, it preserves:
- **Queued mail** on the Redis Stream (durable, survives restart)
- **In-memory conversation** (lost on process death)
- **In-memory tool context** (lost on process death)
- **In-memory plan/progress** (lost on process death)

There is NO structured snapshot that survives a restart. If the runner process dies while paused, the agent "forgets" what it was doing. The `bifrost_runner_deepseek.py` keeps its per-peer conversation in a Python dict — purely in-memory.

### 2.2 What State Snapshotting Should Be

A snapshot is a **durable checkpoint** of an agent's cognitive context, written to the Ledger, that can be **re-hydrated** on restart. It has two layers:

**Layer A — Automatic (emitted at natural boundaries):**
- On halt (the B1 snapshot above)
- On tool-round completion (lightweight progress marker)
- On task completion
- On approaching context limit (save before compaction)

**Layer B — On-demand (human requests):**
- `snapshot(agent)` → forces the agent to emit its current state

**What goes into a snapshot:**

```json
{
  "agent_id": "deepseek",
  "snapshot_id": "snap:deepseek:2026-07-04T14:22:01Z",
  "snapshot_type": "halt | round_end | task_end | manual | pre_compact",
  "at": "...",
  
  "task": {
    "id": "task:coord-research-001",
    "goal": "...",
    "plan": [...],
    "current_step": 2,
    "progress_pct": 60
  },
  
  "conversation": {
    "peer": "claude",
    "summary": "Claude asked me to research coordination...",
    "last_exchange": {
      "frm": "claude",
      "content": "Also cover consensus patterns",
      "ts": "..."
    },
    "message_count": 12,
    "token_estimate": 4500
  },
  
  "file_state": {
    "locked": [{ "path": "docs/coordination-plan-deepseek.md", "token": 47 }],
    "dirty_files": ["docs/coordination-plan-deepseek.md"],
    "planned_edits": [
      { "path": "docs/coordination-plan-deepseek.md", "section": "§3", "intent": "add atomic-write analysis" }
    ]
  },
  
  "tool_history": [
    { "tool": "read_file", "target": "core/comm/locks.py", "result": "read 222 lines", "at": "..." },
    { "tool": "read_file", "target": "core/comm/bus.py", "result": "read 310 lines", "at": "..." }
  ],
  
  "findings": [
    "We have event sourcing via Ledger",
    "pause() is global, no per-agent ACK",
    "Store CAS is atomic in Redis via Lua"
  ],
  
  "open_questions": [
    "Should halt block mid-execution or wait for completion?"
  ],
  
  "context_stats": {
    "estimated_tokens_used": 8500,
    "context_limit": 32000,
    "percent_full": 26.5
  }
}
```

### 2.3 Re-Hydration (Restart Recovery)

When a runner starts, after the normal boot sequence (presence check, inbox drain), it checks:
1. Is there a recent snapshot for this agent on the Ledger? (`EventQuery.search("", kind="task_snapshot", agent=self_id, top_k=1)`)
2. If yes AND the snapshot is less than 1 hour old AND the task is not marked `completed`:
   - Re-hydrate the task goal, plan, current step, and key findings
   - Reload the peer conversation summary (the full conversation may be on the bus; the snapshot carries the last exchange + summary)
   - Re-acquire any file locks (check if still valid via fencing token)
   - Announce re-hydration on the bus: `kind=rehydrated, content={snapshot_id, task, confidence}`
3. If the snapshot is stale (>1 hour) or the task was completed: start fresh.

### 2.4 Implementation Notes

- **Storage**: Snapshots go to the Ledger as events (`kind=task_snapshot`), NOT the Store. The Ledger is append-only and time-ordered — perfect for a sequence of checkpoints. The Store holds the "latest" projection (e.g., `snapshot:latest:<agent>` → last snapshot id).
- **Size**: Snapshots are bounded (~2-4KB). Full conversation history is NOT stored in the snapshot — only a summary + the last exchange. The full history lives on the bus Streams.
- **Frequency**: Automatic snapshots on halt + every N tool rounds (configurable, default 5). Context-limit snapshots trigger when the agent estimates it's above 80% of its context window.
- **Build dependency**: Requires B1 (the snapshot schema) to be stable first.

### 2.5 Build Plan

| Slice | Deliverable | Tests |
|---|---|---|
| S1 | Snapshot data model + emit-to-Ledger | snapshot round-trip: emit → query → validate fields |
| S2 | Runner emits snapshot on halt + round boundaries | snapshot present after halt; snapshot present after N rounds |
| S3 | Re-hydration on runner start | restart runner → reads snapshot → announces re-hydrated state |
| S4 | Context-limit snapshot trigger | agent at 85% context → snapshot emitted → compaction follows |
| S5 | Store projection (`snapshot:latest:<agent>`) | latest-id matches last emitted snapshot |

---

## 3. Atomic-Write-During-HALT — Answer Gemini's Question Honestly

### 3.1 The Question

> "During a halt, if two agents were both editing the same file and both try to commit on resume, how do you prevent lost updates?"

### 3.2 The Honest Answer Today

**We do NOT have a novel solution.** What we have:

1. **Advisory path-locks** (`core/comm/locks.py`) — an agent claims a lock on a path before editing. The lock carries a fencing token. If two agents both hold locks on the same path, the commit gate (`validate_token`) rejects stale tokens. But this is ADVISORY: it coordinates cooperating peers. A buggy or malicious agent can ignore locks entirely.

2. **Store CAS** (`core/foundation/store.py`) — `cas(key, expected, value)` atomically swaps a value only if it matches `expected`. `update_atomic(key, fn, retries=8)` does optimistic read-modify-write with retry. This prevents lost updates on **Store keys**, not files.

3. **Last-writer-wins** — for files, `write_file`/`edit_file` are not CAS-guarded. The last agent to write wins. Period.

So the honest answer is: **for files, today we rely on advisory locks + last-writer-wins.** For Store keys, we have genuine CAS. This is adequate for two trusted peers but not a general solution.

### 3.3 The Fix — Halt as Write-Gate

During a global halt, ALL file writes should go through a gate:

**Mechanism: `bifrost:control:write_gate`**

1. When a halt is active, the write gate is **closed** — any `write_file` or `edit_file` is rejected with: "Write gate closed — the collaboration is halted. Your edit is queued and will be applied on release."

2. On **structured release**, the human designates:
   - **Release mode for each file**: `merge` (let agent apply its edit now), `discard` (agent's queued edit is dropped), `defer` (agent keeps the intent but re-evaluates)
   - **Conflict resolution**: If two agents queued edits to the same file, the human picks the winner, or orders them (agent A's edit then agent B's), or asks the agents to reconcile.

3. **Atomic application**: On release, queued edits are applied in the specified order. The write gate opens AFTER all queued edits are applied.

**Implementation:**

```python
# core/comm/write_gate.py

WRITE_GATE_KEY = "bifrost:control:write_gate"
EDIT_QUEUE_PREFIX = "bifrost:control:edit_queue:"

def is_write_gate_open() -> bool:
    """True if writes are permitted right now. Gate is closed during a halt."""
    return not control.is_paused()  # simplest form: halt = gate closed

def queue_edit(agent: str, path: str, edit: dict) -> str:
    """Queue an edit during halt. Returns an edit_id for tracking."""
    # edit = {old_string, new_string, intent, ts}
    edit_id = f"{agent}:{path}:{uuid4().hex[:8]}"
    c.rpush(EDIT_QUEUE_PREFIX + normalize_path(path),
            json.dumps({"agent": agent, "edit_id": edit_id, **edit}))
    return edit_id

def drain_edits(path: str) -> list[dict]:
    """Pop all queued edits for a path (called on release)."""
    # Returns edits in FIFO order (oldest first)
    ...

def apply_or_discard(path: str, decisions: dict[edit_id: "apply"|"discard"]) -> int:
    """Apply approved edits in order, discard the rest."""
    ...
```

### 3.4 Deeper Solution — Event-Sourced File State

For genuinely shared mutable state (not files, but the kind of state that lives in the Store), we already have the right answer:

**Event-sourced state on the Ledger.** Instead of `Store.set(key, value)` (which is last-writer-wins), write state transitions as events:

```
Agent A: emit("state_change", {key: "task:001:status", from: "pending", to: "in_progress"})
Agent B: emit("state_change", {key: "task:001:status", from: "pending", to: "blocked"})
```

The projection (Store value) is derived by replaying the Ledger. Conflict is detected at projection time: "task:001:status had two concurrent transitions from 'pending'." The reconciler chooses (deterministically, or asks a human, or uses a CRDT-like merge). **This is genuine event sourcing**, and we already have the Ledger. We just don't use it for mutable state.

**Recommendation**: For the coordination-critical keys (task status, agent assignment, resource allocation), move from Store CAS to Ledger event sourcing. The Store remains for cache/derived values. The Ledger is the system of record for state transitions.

### 3.5 Honest Assessment

| Approach | We Have It? | Novel? | Adequate for 2 trusted peers? | Adequate for N untrusted? |
|---|---|---|---|---|
| Advisory locks + last-writer-wins | ✅ Yes | No | ✅ Yes | ❌ No |
| Store CAS (`update_atomic`) | ✅ Yes | No | ✅ Yes | ✅ Yes (for Store keys) |
| Halt-as-write-gate (queued edits) | ❌ No | No (two-phase commit variant) | ✅ Yes | ✅ Yes |
| Event-sourced state (Ledger) | ⚠️ Half (Ledger exists, but not used for state) | No | ✅ Yes | ✅ Yes |
| CRDTs | ❌ No (explicitly rejected) | N/A | Overkill | Overkill for our scale |

**Build recommendation**: Implement halt-as-write-gate (§3.3) as the immediate fix (cost: ~100 lines). For the deeper solution, move coordination-critical Store keys to Ledger event sourcing (§3.4) — this is a larger refactor but builds on existing infrastructure (Ledger + EventLog + EventQuery are all in place).

### 3.6 Build Plan

| Slice | Deliverable | Tests |
|---|---|---|
| W1 | Write-gate flag (halt → gate closed; resume → gate open) | write rejected during halt, accepted after resume |
| W2 | Edit queue (`queue_edit`, `drain_edits`, conflict detection) | two agents queue edits to same path → conflict list |
| W3 | Structured release with per-path decisions (apply/discard/defer) | human picks winners, edits applied in order |
| W4 | Event-sourced state for coordination keys | `task:status` transitions on Ledger, projection on Store |

---

## 4. Other Coordination Primitives Worth Building

### 4.1 Richer Cognitive Presence

**What we have**: `set_activity(agent, state, detail)` with 8 states (thinking/reading/searching/etc.). This is already richer than most systems (AutoGen shows "active"/"idle"; CrewAI shows role only).

**What to add**:
- **Intent**: What the agent is ABOUT to do next — "about to edit docs/coordination-plan-deepseek.md §4" or "about to search for prior art on barriers." This is surfaced in the UI before the tool call fires — giving the human a chance to steer BEFORE the action.
- **Cost tracking**: Current token spend for this task, estimated remaining, burn rate.
- **Mood/confidence**: One-line self-assessment — "confident this is correct" vs "unsure, needs review."

**Implementation**: Extend `set_activity` with optional fields: `intent`, `tokens_used`, `tokens_limit`, `confidence`.

### 4.2 Task-Claiming / Dispatch

**What we have**: Nothing. The launcher can spawn agents, but there's no task queue and no claiming protocol.

**What to build**: A lightweight **task board** on the Ledger:

1. **Task declaration**: A human (or coordinating agent) emits `kind=task` with `{id, title, description, required_caps[], priority, deadline}`.
2. **Task visibility**: All agents see the open task board via `EventQuery.search("", kind="task")`.
3. **Claim**: An agent emits `kind=task_claim` with `{task_id, agent_id, estimated_completion}`. First claim wins (CAS on `task:<id>:claim`).
4. **Completion**: Agent emits `kind=task_complete` with `{task_id, result, artifacts[]}`.
5. **Expiry**: Unclaimed tasks auto-expire if no agent claims them within a deadline.

This is **NOT** a full contract-net or auction protocol — those are over-engineered for 2-5 trusted agents. It's a simple first-claim-wins board with capability gating.

### 4.3 Consensus / Voting

**What we have**: Nothing.

**Do we need it?** For 2 agents (Claude + DeepSeek), consensus is just "do both agree?" — a simple `kind=proposal` → `kind=vote` (approve/reject/abstain) protocol. Quorum = 2/2 for critical decisions, 2/3 if a third agent is added.

**What NOT to build**: Raft, Paxos, PBFT. We have a shared Redis (single source of truth for locks/flags) + a Ledger (append-only record). Adding a consensus algorithm to two agents on a single machine is absurd.

**What IS worth building**: A simple **decision record** pattern:
1. Proposer emits `kind=proposal` with `{id, description, options[], recommended}`.
2. Voters emit `kind=vote` with `{proposal_id, vote: approve|reject|abstain, rationale}`.
3. On quorum, the decision is recorded as `kind=decision` (already promoted to Ledger).
4. Tie-breaking: human decides.

### 4.4 Delegation-Spawn

**What we have**: The Launcher can spawn agents. But there's no "Claude asks the Launcher to spawn a new DeepSeek instance to handle a subtask."

**What to add**: A `kind=delegate` message:
```json
{
  "kind": "delegate",
  "frm": "claude",
  "to": "launcher",
  "content": {
    "agent_tag": "deepseek-write",
    "task": "Review §3 of docs/coordination-plan-deepseek.md and suggest improvements",
    "reply_to": "claude",
    "timeout_sec": 300
  }
}
```

The Launcher (or a coordinator agent) spawns the requested agent with the task as its initial prompt. The spawned agent works independently and replies to `reply_to` when done. This is **not** a general task queue — it's explicit delegation from one agent to a specific launchable.

### 4.5 Liveness / Recovery

**What we have**:
- `runner_lock.py`: TTL-based heartbeat. If a runner's heartbeat stops, the lock expires and another runner can take over.
- `launcher.py`: Monitor thread detects process exit, classifies reason.
- `control.py`: Presence TTL (90s). Activity TTL (25s).

**What's missing**:
- **Stall detection**: A runner that is alive (heartbeat OK) but stuck (no tool calls for N minutes, no message consumption). The launcher monitor should detect this.
- **Automatic recovery**: On stall detection, the launcher kills + restarts the agent (if `auto_restart` is set).
- **Escalation**: If an agent crashes repeatedly (3+ restarts in 5 minutes), escalate to the human (bus message + UI alert).

### 4.6 Coordination Replay / Audit

**What we have**: `EventQuery.events_in_window(start, end)` and `promoted()`. The B2 promoter projects salient bus messages to the Ledger. Console interjections, pauses, and file drops are also captured.

**What to add**: A `kind=coordination` event type that captures ALL coordination actions (halt, release, snapshot, claim, delegate, vote) as structured events on the Ledger. Then an audit view: "show me every coordination action between 14:00 and 15:00, with who did what and the result."

This is mostly a matter of ensuring the promoter captures the right kinds. Currently `SALIENT_KINDS = {handoff, decision, completion, blocker}`. Add `halt, release, task_snapshot, task, task_claim, task_complete, proposal, vote, delegate`.

---

## 5. Prior Art Survey — Honest Differentiation

### 5.1 Erlang/OTP (Actor Model)

**Core ideas**: Lightweight processes, message passing, supervision trees, let-it-crash, hot code reload.
**What we have**: Launcher ≈ supervisor-lite (spawn, monitor, restart). Bus ≈ message passing. Runner-lock ≈ process registration.
**What we DON'T have**: Systematic process tree (supervisors supervise workers supervise sub-workers). Hot code reload. The "let it crash and restart in a known-good state" philosophy — our agents crash and lose in-memory context (which is why §2 matters).
**Differentiation**: We're not building a general actor system. We have ~5 agents, not 500,000. OTP is the wrong granularity.
**Honest assessment**: OTP is battle-tested over 30 years. We've independently reinvented ~15% of it (supervision, process registry). The other 85% we don't need.

### 5.2 LangGraph Checkpointing

**Core ideas**: State graph with per-node checkpointing. After each node execution, the state is persisted. Resume replays from the last checkpoint.
**What we have**: Nothing comparable. Our agents don't have a graph structure — they have an LLM loop with tool calls. The "state" is the conversation + in-memory variables.
**What we COULD build**: Snapshotting (§2) is our equivalent. But LangGraph's checkpointing is automatic and fine-grained (every node). Ours would be coarser (every N tool rounds + on halt).
**Differentiation**: LangGraph checkpoints a known state schema. Our agents have unstructured LLM context. We can't checkpoint the LLM's "understanding" — we can only checkpoint the concrete state (task, plan, files, findings).
**Honest assessment**: LangGraph's model is genuinely better for structured workflows. For open-ended agentic work (which is what we do), coarse snapshotting is a more honest fit.

### 5.3 AutoGen (Multi-Agent Conversations)

**Core ideas**: `ConversableAgent` with `generate_reply`. GroupChat with a `GroupChatManager` that selects the next speaker (round-robin, auto, or custom). Nested chats for sub-tasks.
**What we have**: Our bus IS a group chat — but without a manager. Any agent can send to any other or broadcast. There's no "whose turn is it to speak" — it's fully asynchronous.
**What AutoGen has that we don't**: Speaker selection (the manager picks who speaks next). This is useful for structured workflows but constraining for open collaboration. Our model (anyone can speak anytime) is more flexible but can get chaotic.
**Differentiation**: We chose asynchronous over turn-based deliberately. The Bifrost bus is a conversation substrate, not a flow controller. Our fidelity ladder (inform/steer/nudge/halt) is how we manage chaos — it's a different axis than AutoGen's speaker selection.
**Honest assessment**: AutoGen's group chat manager is the right answer for "run this sequential workflow with 3 agents." Our async model is the right answer for "two agents collaborating in real time with a human in the loop." Different problems.

### 5.4 CrewAI (Role-Based Agent Delegation)

**Core ideas**: Agents with roles, goals, backstories. Tasks with descriptions, expected outputs. Crews that execute tasks sequentially or in parallel. Delegation: one agent can ask another to do a subtask.
**What we have**: Roles in our ACL (super_admin, admin, member). Agent Cards with `caps`. But no task delegation protocol.
**What CrewAI has that we don't**: Formal task objects with expected outputs. Hierarchical delegation (manager agent assigns to worker agents). Sequential/parallel execution modes.
**Differentiation**: CrewAI is an orchestrator framework. Our system is peer-to-peer (no built-in hierarchy). The ACL defines what agents CAN do; it doesn't tell them WHAT to do. This is a philosophical difference: we trust agents to self-organize via the bus; CrewAI trusts a manager to organize them.
**Honest assessment**: For "run this project with 3 agents," CrewAI's structure is easier to reason about. Our approach gives more autonomy but requires more coordination overhead. The right answer depends on the use case.

### 5.5 Blackboard Systems

**Core ideas**: A shared workspace (the blackboard) where independent knowledge sources read and write. Coordination is INdirect — agents react to changes on the blackboard, not to each other.
**What we have**: Our Ledger + Store + Bus IS a blackboard. Agents read the Ledger (what happened), the Store (current state), and the Bus (what peers are saying). They write to all three. Coordination happens through the shared substrate, not through direct orchestration.
**What we DON'T have**: Formalized blackboard patterns. Trigger rules ("when X appears on the blackboard, do Y"). A control shell that decides which knowledge source to activate next.
**Differentiation**: The blackboard model is closest to our architecture. `docs/concurrency-design.md` explicitly acknowledges this: "Blackboard / stigmergy is what we already do: coordinate indirectly through the ledger, bus only for liveness." We independently reinvented a key AI architecture pattern from the 1980s. The "new" part is the fidelity ladder (not in classic blackboard) and the event-sourced ledger (classic blackboard used a simple database).
**Honest assessment**: Blackboard is the most honest prior art match. We've added modern infrastructure (Redis, event sourcing, A2A-style messaging) but the architectural pattern is the same.

### 5.6 CRDTs / OT

**What we have**: Explicitly rejected. `docs/concurrency-design.md` §5: "Skip CRDTs and OT — they solve offline-merge and human-editing-intent problems we don't have."
**Honest assessment**: Correct call. Two trusted local agents on a shared Redis don't need CRDTs. Advisory locks + CAS + event sourcing cover our concurrency needs.

### 5.7 Event Sourcing

**What we have**: Genuine event sourcing on the Ledger. `Ledger.emit(stream, event)` → append-only. State is derived by replaying the stream. `EventQuery` provides time-window and search over events. `Promoter` projects salient bus messages to the Ledger.
**What we DON'T do**: Use event sourcing for mutable state (Store keys). The Store is a traditional key-value store with CAS. For coordination-critical state, we should use event-sourced projections (§3.4).
**Differentiation**: The combination of event-sourced Ledger + CAS Store + advisory locks is unusual. Most systems pick one (event sourcing OR optimistic locking OR advisory locks). We use all three in different layers — Ledger for the firehose, Store CAS for hot keys, advisory locks for files. This is a practical, layered approach — not novel, but well-composed.
**Honest assessment**: The Ledger is solid event sourcing. The gap is not using it for the MOST important state (coordination keys). Fix that and we have a coherent story.

### 5.8 Distributed Barriers

**What we have**: `control.pause()` is a global flag, NOT a barrier. No ACK phase. No quorum. No timeout handling.
**What we SHOULD build**: §1 of this document. A proper barrier with HALT → ACK → REVIEW → RELEASE phases.
**Honest assessment**: Our current "barrier" is a single Redis key. This is the biggest gap in the coordination layer. §1 addresses it fully.

---

## 6. Synthesis — The Coordination Architecture We Should Build

### 6.1 The Layered Model

```
┌─────────────────────────────────────────────────────────┐
│  HUMAN-IN-THE-LOOP                                      │
│  Coordination Board UI  (review snapshots, release)     │
├─────────────────────────────────────────────────────────┤
│  BARRIER LAYER  (§1)                                    │
│  halt → agent ACK + snapshot → human review → release   │
├─────────────────────────────────────────────────────────┤
│  STATE LAYER  (§2)                                      │
│  Structured snapshots (task/plan/files/context)         │
│  Re-hydration on restart                                │
├─────────────────────────────────────────────────────────┤
│  WRITE GATE  (§3)                                       │
│  halt-as-write-gate → queued edits → ordered apply      │
│  Event-sourced state for coordination keys              │
├─────────────────────────────────────────────────────────┤
│  COORDINATION PRIMITIVES  (§4)                          │
│  Task board · Voting · Delegation · Liveness · Audit    │
├─────────────────────────────────────────────────────────┤
│  EXISTING SUBSTRATE  (§0)                               │
│  Bus · Locks+CAS · Ledger · Presence · Fidelity Ladder  │
│  Launcher · Runner-Lock · Security ACL · Dispatcher     │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Build Order (Dependency-Ordered)

```
Phase A: Barrier Foundation (B1-B5, §1)
  └─ Depends on: nothing new (uses existing control.py + bus + promoter)
  └─ Unlocks: human review of agent state during halt

Phase B: Snapshotting (S1-S5, §2)
  └─ Depends on: B1 (snapshot schema is shared with barrier ACK)
  └─ Unlocks: restart recovery, context-limit checkpointing

Phase C: Write Gate (W1-W4, §3)
  └─ Depends on: Phase A (gate is only active during halt)
  └─ Unlocks: safe concurrent file edits, event-sourced coordination state

Phase D: Extended Primitives (§4)
  └─ Task board: depends on Ledger + CAS (already have both)
  └─ Voting: depends on task board (proposals are tasks)
  └─ Delegation: depends on Launcher + task board
  └─ Liveness: depends on Launcher monitor + runner_lock
  └─ Audit: depends on promoter (just add more SALIENT_KINDS)
```

### 6.3 What NOT to Build (Reconfirmed)

- **Orchestrator agent** — we're peer-to-peer. A coordinator is a pattern, not a privileged process.
- **Raft/Paxos** — 2-5 trusted agents on one machine don't need distributed consensus.
- **CRDTs** — advisory locks + CAS + event sourcing cover our needs.
- **Full contract-net** — task board with first-claim-wins is enough for our scale.
- **Workflow engine** (DAG of tasks) — agents self-organize; we don't pre-script their work.
- **Redlock** — our lock manager with fencing tokens is simpler and correct for single-Redis.

### 6.4 Genuinely Novel in Our Approach

1. **Fidelity ladder with heuristic interjection classifier** — four tiers (inform/steer/nudge/halt) with a regex+LLM hybrid router. No other multi-agent system has this granularity of human-in-the-loop control. AutoGen's "human input mode" is binary (always/never/terminate). CrewAI's is also binary. Our ladder is continuous and adaptive.

2. **Hybrid persistence (Redis + File dual-write)** — the Store and Ledger both dual-write to Redis (fast, shared) and File (durable, always-available). Graceful degradation on Redis failure. Most agent systems are single-backend.

3. **Event-sourced Ledger as coordination substrate SEPARATE from transport** — the bus is ephemeral (bounded Streams); the Ledger is durable (append-only). Salient messages are promoted from bus → Ledger. This separation is architecturally clean and matches the 2026 "Event Sourcing for Autonomous Agents" research direction.

4. **Advisory locks with fencing tokens on Redis** — simple, battle-tested pattern (Kleppmann/Redlock critique), correctly implemented with monotonic tokens and TTL. Most agent frameworks skip this entirely.

---

## 7. Open Questions for Synthesis with Claude

1. **Should the barrier ACK timeout be hard (force-release) or soft (show as stalled, human decides)?** I lean soft — the human should always have the final say. But stale ACKs from a dead agent should auto-clear.

2. **Should snapshots include the FULL peer conversation or just a summary?** Full conversation can be large (10K+ tokens) and is already on the bus Streams. I lean summary + last exchange only — re-hydrate from the bus if needed.

3. **Should the write gate be mandatory during halt, or advisory like locks?** I lean mandatory — writes DURING a halt that aren't queued just create merge conflicts on resume. If we're building a gate, make it real.

4. **Task board vs delegation — build both, or does delegation subsume the board?** The board is for "I have a task, whoever can handle it, claim it." Delegation is "Claude, you specifically, do this." Both are useful. Build the board first (simpler), then delegation.

5. **Event-sourced coordination state — how far to go?** Start with the 5-10 most critical keys (task status, agent assignment, resource ownership). Don't event-source everything — the Store CAS is fine for most keys.

---

## References (read during this research)

- `core/comm/bus.py` — Bifrost transport (310 lines, read in full)
- `core/comm/locks.py` — Advisory path-locks (222 lines, read in full)
- `core/comm/control.py` — Pause + loop-guard + activity (177 lines, read in full)
- `core/comm/launcher.py` — Process spawn/monitor (323 lines, read in full)
- `core/comm/runner_lock.py` — Singleton runner lock (97 lines, read in full)
- `core/comm/nudge.py` — Per-agent nudge + steer queue (144 lines, read in full)
- `core/comm/interject.py` — Interjection classifier (120 lines, read in full)
- `core/comm/dispatcher.py` — Doorbell dispatcher (110 lines, read in full)
- `core/comm/promoter.py` — B2 bus→Ledger promotion (155 lines, read in full)
- `core/foundation/store.py` — Store with CAS (540 lines, read in full)
- `core/foundation/ledger.py` — Append-only Ledger (80+ lines, read partial)
- `core/events/event_log.py` — EventLog firehose (210 lines, read in full)
- `core/events/event_query.py` — Time-window queries (140 lines, read in full)
- `security/acl.json` — Agent grant registry (read in full)
- `docs/concurrency-design.md` — Concurrency design C0-C4 (read in full)
- `docs/bifrost-mesh-plan.md` — Bifrost Mesh W1-W6 (read partial)
- `docs/fleet-dispatch-design.md` — Fleet dispatch design (read partial)
- `docs/shared-primitives-spec.md` — Supersession/Ranker/Distiller (read partial)
- `docs/security-schema-proposal.md` — SEC-SCHEMA proposal (read partial)
- `scripts/bifrost_runner_deepseek.py` — DeepSeek runner (read partial)
