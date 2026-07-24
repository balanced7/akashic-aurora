---
akashic_id: art_20260709_bifrost-sync-plan-protocol_c70323
akashic_sha: ee8003625069
status: superseded
type: design
date: 2026-07-09
title: "Bifrost Sync & Plan Protocol"
gist: "Design drafted 2026-07-04 by DeepSeek during a live multi-agent session (user request: \"global pause + synchronize + plan feature\" for bette"
tenant: solo
visibility: fleet
seats: []
category: [bus, coordination, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: art_20260710_multi-agent-coordination-layer-synthesis_283c99
citations:
  - target: art_20260710_multi-agent-coordination-layer-synthesis_283c99
    rel: cites
created: "2026-07-09T23:27:59"
updated: "2026-07-23T21:42:04"
---
<!-- GENERATED PROJECTION of art_20260709_bifrost-sync-plan-protocol_c70323 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **SUPERSEDED** -- succeeded by `art_20260710_multi-agent-coordination-layer-synthesis_283c99`. This version is preserved as a receipt.

# Bifrost Sync & Plan Protocol

Design drafted 2026-07-04 by DeepSeek during a live multi-agent session
(user request: "global pause + synchronize + plan feature" for better
coordination).  Claude and the user reviewed / will review on next boot.

---

## Current State (what we have)

| Primitive | File | Mechanism | Gap |
|---|---|---|---|
| Global Pause | `core/comm/control.py` | One Redis flag; all runners poll it | Fire-and-forget — no per-agent acknowledgment |
| Per-agent Nudge | `core/comm/nudge.py` | Redis flag + kind=nudge message | Only targets ONE agent at a time |
| Per-agent Steer | `core/comm/nudge.py` | Redis queue, drained between rounds | Soft only; no sync |
| Runner Lock | `core/comm/runner_lock.py` | TTL lease, singleton per agent | Crash-safe, but only guards duplicate runners |
| Advisory Path-locks | `core/comm/locks.py` | Fencing-token, per-file | File-level only, not task-level |
| Launcher | `core/comm/launcher.py` | Spawn/kill/monitor processes | No coordinated start/stop; no session save/restore |
| Dispatcher | `core/comm/dispatcher.py` | Doorbell wake via pub/sub | Wake only, no rendezvous |
| Interject Classifier | `core/comm/interject.py` | halt/steer/ask/resume from text | Human intent only |

All use the same Redis-backed, fail-open, advisory trust model.

---

## The Five Gaps

1. **Pause is blind.** The UI sets the flag. Each runner independently polls.
   Nobody knows if Agent X has actually stopped or is stuck mid-tool-call.

2. **No rendezvous.** Even when all agents are paused, resuming is chaotic —
   each agent independently notices the flag is gone and races back.

3. **No planning protocol.** No structured "here's the new plan → feedback →
   commit → go" flow. Chat messages just land in the inbox alongside everything.

4. **No context capture.** When you interrupt a stateless agent (DeepSeek), its
   working memory evaporates. On resume it has no idea what it was doing.

5. **Resume is a starting gun, not a starting block.** Everyone sprints from
   slightly different positions.

---

## Design: Five Layers

### LAYER 1 — Agent State Tracking

New in `control.py`:

    bifrost:control:agent_state:<agent> → {state, context, since, last_action}

**State machine:** `running → pausing → paused → acknowledged → running`

Each runner writes its state every loop iteration (TTL 30s — crashed agent
auto-clears).  `pausing` = "I saw the flag, finishing my current tool call."
`paused` = "safely stopped, here's what I was doing."  `acknowledged` = "I've
read the plan, ready to proceed."

The UI `/status` already returns per-agent signals — extend with a state field.
Roster pills get a state indicator (◐ pausing, ◼ paused, ✓ acknowledged).

### LAYER 2 — Pause Acknowledgment

When the human hits Pause:

1. Global flag set (existing)
2. Each agent transitions `running → pausing → paused`
3. UI polls `/status` — live progress banner:
   ```
   ⏸ Pausing... Claude ◐ (finishing read_file) · DeepSeek ◼ paused ✓
   ```
4. Once ALL agents reach `paused`, banner: **"All agents stopped. Plan below."**
5. Agent stuck in `pausing` >30s → UI warns: "Claude hasn't stopped — may be in
   a long operation."

### LAYER 3 — Sync Barrier (Rendezvous)

New `SyncBarrier` class in `control.py`:

    bifrost:sync:barrier:<id>:arrived  → SET of agent_ids
    bifrost:sync:barrier:<id>:expected → INT
    bifrost:sync:barrier:<id>:status   → "gathering" | "ready" | "released"

API:
```python
barrier = SyncBarrier("plan-round-1", expected=3, ttl=60)
barrier.arrive(agent_id)   # agent: "I'm here, waiting"
barrier.wait_all(timeout)  # coordinator: blocks until all arrived
barrier.release()          # everyone proceeds
```

### LAYER 4 — Planning Round Protocol

New bus message kinds:

| Kind | Direction | Purpose |
|---|---|---|
| `plan_directive` | Human → all | The plan text |
| `plan_response` | Agent → human | Questions, concerns, confirmations |
| `plan_commit` | Human → all | "Proceed with the plan" |

Full workflow:
```
1. Human hits Pause
2. Agents → paused ✓ (Layer 1+2)
3. Barrier created (Layer 3)
4. Human types plan → plan_directive broadcast
5. Each agent: reads plan, transitions to acknowledged
6. Agents reply with plan_response
7. Human reads responses, adjusts if needed
8. Human hits "Commit & Resume" → plan_commit broadcast + resume()
9. Barrier releases → all agents start together with plan in context
```

### LAYER 5 — Checkpoint Capture (lighter-weight)

On pause, each agent writes a checkpoint to `bifrost:control:agent_state:<agent>`:
```json
{
  "state": "paused",
  "context": "Editing bifrost_ui.py CSS for iso-cube variant, lines 650-800",
  "since": "2026-07-04T02:30:00",
  "last_action": "read_file bifrost_ui.py:650-800"
}
```

On resume, the runner reads its checkpoint and splices it into the incoming plan.
For stateless API agents (DeepSeek) this is critical — it's the only memory
between turns.

---

## UI Changes (`scripts/bifrost_ui.py`)

Surgical additions, reusing existing SSE + poll architecture:

1. **Enhanced banner** — per-agent pause progress
2. **Plan panel** — appears below banner when paused + all acknowledged;
   textarea + "Distribute Plan" / "Commit & Resume" buttons
3. **Resume button gating** — only active when all agents are `paused` or
   `acknowledged` (with "Override & Resume" escape hatch)
4. **New `/sync/status` endpoint** — per-agent state grid for polling

---

## Implementation Order

| Phase | What | Effort | Delivers |
|---|---|---|---|
| P1 | Agent state tracking + runner changes + UI banner | ~2h | See who's stopped |
| P2 | SyncBarrier in control.py | ~1h | Rendezvous primitive |
| P3 | Planning round (bus kinds + UI composer + agent response display) | ~2h | Plan→feedback→commit→go |
| P4 | Checkpoint capture/restore | ~1h | Stateless agents remember context |

---

## Design Principles

1. **Same trust model.** Advisory, fail-open on Redis errors — matching
   `control.py`, `nudge.py`, `runner_lock.py`, `locks.py`.
2. **Redis is the shared whiteboard.** All coordination state in Redis keys with
   TTLs. Bus = messages; control plane = coordination.
3. **The UI is the cockpit, not the controller.** Browser polls `/status`;
   coordination logic lives in `control.py`.
4. **Human is the coordinator.** Future: a designated "coordinator agent" could
   fill this role automatically.
5. **Crash-safe by default.** All keys have TTLs; barriers auto-expire; system
   degrades gracefully to current "blind pause" if anything fails.

---

## Session Save/Restore (shipped 2026-07-04 alongside this plan)

`core/comm/launcher.py` gained `save_session()` / `restore_session()` and an
auto-save hook on every launch/kill.  State file: `state/bifrost-session.json`.

UI: "💾 Save" and "🔄 Restore" buttons in the launcher panel — one click to
snapshot today's running agents, one click tomorrow to spin them back up.
