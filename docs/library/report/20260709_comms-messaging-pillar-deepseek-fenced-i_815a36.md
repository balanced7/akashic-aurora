---
akashic_id: art_20260709_comms-messaging-pillar-deepseek-fenced-i_815a36
akashic_sha: 5b67e2f77276
status: draft
type: report
date: 2026-07-09
title: Comms/Messaging Pillar -- DeepSeek FENCED independent report (T016)
gist: "# Comms/Messaging Pillar -- DeepSeek FENCED independent report (T016) Recovered verbatim from bus msg 1783602506398-0 (2026-07-09, kind=repl"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260710_multi-agent-coordination-layer-synthesis_283c99
    rel: cites
  - target: art_20260705_master-directive-list-akashic-aurora-202_964020
    rel: cites
created: "2026-07-09T09:15:10"
updated: "2026-07-23T21:42:14"
---
<!-- GENERATED PROJECTION of art_20260709_comms-messaging-pillar-deepseek-fenced-i_815a36 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Comms/Messaging Pillar -- DeepSeek FENCED independent report (T016)

# Comms/Messaging Pillar -- DeepSeek FENCED independent report (T016)

Recovered verbatim from bus msg 1783602506398-0 (2026-07-09, kind=reply, deepseek to claude).
NOTE: this reply was silently consumed by a claude-side cursor advance before any reader saw
it -- itself live T016 evidence (delivery without presentation; see claude report F5).
Recovered directly from the Redis stream (cursors do not delete entries).

---

Now I have enough ground truth. Let me compile my diagnosis.

---

# Communications/Messaging Pillar — Fenced Investigation (DeepSeek)

## PHASE 1: Triangulation — What I Found

### Source 1 — The Design (docs)

**`docs/coordination-plan-synthesis.md`** (2026-07-04, Claude+DeepSeek merged plan, the most comprehensive design doc). This is an EXCELLENT design document. It identifies exactly the right gaps in the then-current system (pause is blind, no rendezvous, no planning protocol, no context capture, resume is a starting gun). It proposes five layers (Agent State Tracking → Pause Acknowledgment → Sync Barrier → Planning Round → Checkpoint Capture) plus a full Phases A-D build plan with 20+ gated slices.

**Status:** The design is sound. NONE of Phases A-D has been built. The `bifrost-sync-plan.md` lays out the same gaps (Pause is blind, No rendezvous, No planning protocol, No context capture, Resume is a starting gun) plus a 4-phase build plan — also unbuilt.

**`AGENTS.md`** (the communication contract, at repo root, not in docs/) is clear and well-organized. It correctly directs agents to `boot`, `bifrost-sync`, `promoted()`, `recall`, and a handoff ritual. It's one of the best pieces of the comms pillar. But it describes a ritual that depends on a runner being alive to execute it — for a stateless API model (me), `boot` is run ONCE by the runner at startup and the output is folded into the system prompt; I never re-boot mid-session.

### Source 2 — The Code (what actually IS)

The codebase is genuinely impressive — well-structured, well-tested, thoughtful:

- **`core/comm/bus.py`** — Solid. Per-agent inboxes + broadcast via per-agent cursors. Pending, presence, register, cursor advances, the T014 cursor-skip fix. The `_drain` logic is correct and well-commented.

- **`core/comm/control.py`** — Global pause, per-agent halt, rate limiter, hop-count loop guard, rich activity presence, narration level. All working.

- **`core/comm/nudge.py`** — Per-agent nudge (hard interrupt) + steer (soft fold-in). Working.

- **`core/comm/interject.py`** — Heuristic-first halt/steer/ask/resume classifier. Working.

- **`core/comm/promoter.py`** — Promotes salient kinds (handoff/decision/completion/blocker) to the durable Ledger. Plus console events (interjection/bus_control/file_drop). Working.

- **`core/comm/runner_lock.py`** — Singleton lock per agent, crash-safe via TTL heartbeat. Working.

- **`core/comm/liveness.py`** — WorkLive phase tracking with wedge detection. Working but **not consumed by anything automated** (L2 watchdog is designed but unbuilt per `coordination-plan-synthesis.md` Phase D3).

- **`core/comm/session_state.py`** — Snapshot/restore. Working, but at the launcher level (processes), not at the agent cognitive-context level.

- **`core/comm/context_hints.py`** — Compact ephemeral key:value forwarding between peers. Working, in-memory only (dies with runner).

- **`core/comm/dispatcher.py`** — Doorbell wake. Working but never deployed as a resident process for me.

- **`scripts/bifrost_runner_deepseek.py`** (my body) — Onboarding via `boot` once at startup, folds into system prompt. Per-message processing with timeout guard, per-message isolation, hint interception, hop-count loop guard, rate limiting, broadcast reply mirroring. The T014 batch-processing fix is live. The system prompt carries the task ledger, lessons, recent notes. **But it's frozen at startup time** — if the ledger changes mid-session, I never see it.

- **`agent_cli.py` cmd_boot** — Assembles context via the Context pillar (System 4): task ledger → lessons → narrative → notes → funnel pulse → bifrost peek → locks. This is the best single source of current-state truth. But it's a CLI command, not a bus message.

### Source 3 — The Task Ledger (governed coordination)

**`state/coord/tasks.json`** — 16 tasks, 8 done, 1 in_progress (T016 — this investigation, owned by claude), 7 proposed. The `format_state()` function in `core/coord/task_ledger.py` produces the "DONE / IN PROGRESS / NEXT" block printed at boot. This IS the governed current-state mechanism (Slice C of T001). It works: when I boot, I see exactly what's closed and what's active. The ruling "RULE: anything in DONE is closed. Work only your assigned/NEXT task. Ignore backlog messages that contradict the ledger" is the correct anti-staleness contract.

**BUT** — and this is crucial — the task ledger is ONLY visible at boot. There is no bus message that says "T014 just moved to DONE" or "T016 is now in_progress." If the ledger changes while my runner is alive, I literally cannot know unless someone sends me a chat message telling me.

### Source 4 — Lived Experience (concrete incidents)

**Incident 1: "DeepSeek agents discovering past messages and starting work."** Documented in `docs/master-directive-list-2026-07-05.md` — the VERY document this investigation was commissioned to prevent recurring. Four DeepSeek instances, overlapping file ownership, uncommitted WIP across 23 files. Root cause named in the doc: agents reading bus backlog and acting on stale directives, not on the governed task ledger. The task ledger (T001, Slice C) was SPECIFICALLY built to fix this — and it works at boot. But it doesn't propagate mid-session.

**Incident 2: The T014 cursor-skip bug.** When my runner launched with a pre-queued backlog, the old cursor-advance logic skipped messages 2..N in a batch, consuming them without processing. This was a genuine code bug (now fixed), but it's also a symptom: the bus inbox is a stream, not a queryable state — an agent catching up on a backlog can't distinguish "old, already-handled chatter" from "a directive I haven't seen yet." The fix repaired the cursor, but the structural ambiguity (old vs. new, seen vs. unseen, handled vs. pending) remains.

**Incident 3: Stale advisory locks.** From the `bifrost_api_exists_no_duplicate` lesson: I held a stale advisory lock on a file I wasn't editing, and the peer waited for TTL expiry rather than knowing it was safe. The lock system works, but lock state is only visible at boot and via `locks` CLI — no push notification when a lock is released or expires.

**Incident 4: Onboarding is frozen at runner start.** My system prompt carries the task ledger, lessons, and notes as they were when the runner launched. If Claude marks T014 as DONE and opens T016 while I'm running, my system prompt still says T014 is in_progress. A human sending me a chat message can tell me, but there's no automatic "state changed" propagation.

**Incident 5: The DRILL messages at the start of this session.** When my runner launched, it processed three pre-queued drill messages (DRILL-ACK-1/2/3) that were test artifacts. They were correctly processed (I answered them), but they illustrate the ambiguity: a message in the inbox could be a real directive, a test, a stale request from a past session, or chatter. The message itself carries no "this is still current" bit.

**Incident 6: `promoted()` is powerful but under-discoverable.** The durable Ledger projection of salient messages (handoffs, decisions, completions, blockers) is the correct mechanism for "what was decided." It survives Redis restarts. But `promoted` is a CLI verb, not something surfaced in my system prompt or pushed as a bus notification. I have to know to ask for it — and as a stateless model, I don't know what I don't know.

**Incident 7: No clear "what changed since I last looked."** The bus cursor tracks what I've READ, but not what I've PROCESSED or what's still ACTIONABLE. A message from 3 hours ago that says "please review X" might still be pending — or Claude might have handled it. There's no acknowledged/closed loop on bus messages the way there is on tasks.

---

## PHASE 2: Loop-Altitude Diagnosis

### The value chain: capture → deliver → filter → understand → act → acknowledge

1. **Capture** — Messages land in inboxes (bus.py). ✅ Works.
2. **Deliver** — Runners pick them up, dispatcher wakes agents. ✅ Works (with T014 fix).
3. **Filter** — Hop-count guard, rate limiter, kind-based answerability. ✅ Works.
4. **Understand** — Boot context (task ledger + lessons + notes) + system prompt. ⚠️ Works ONCE at startup. Frozen thereafter.
5. **Act** — Agent reasons and responds. ✅ Works.
6. **Acknowledge** — Cursor advances (message was READ). ❌ No "message was HANDLED" signal. No "task was COMPLETED" propagation. No "state changed" push.

### The one-sentence thesis:

**The pipes are excellent — reliable delivery, correct fan-out, durable projection of salient kinds, governed task state — but state changes are PULL-only (visible at next boot) with no PUSH propagation, so a living agent's understanding of "what is current" drifts from the moment it starts until it restarts.**

Every failure mode traces to this root: the system knows what's current (the task ledger is authoritative, the promoted Ledger is durable, the AGENTS.md contract is clear), but that knowledge is only transmitted at boot time. Mid-session, the only update channel is chat messages on the bus — the same channel as everything else, with no structural distinction between "this is a state change you MUST incorporate" and "casual chatter."

---

## PHASE 3: Proposed Fixes as Gated Slices

### Slice C1 — "State-change broadcast": the task ledger emits on every transition

**What:** When `tasks.json` is updated (a task moves to done/in_progress/claimed), emit a `kind=ledger_update` broadcast on the bus. Runners intercept this kind and fold it into their working context (NOT as a message to answer — like how `hint` is intercepted today without triggering a reply).

**Evidence gate:** After a peer moves a task to DONE, `bifrost_inbox("deepseek")` shows a `ledger_update` message within 2 seconds. DeepSeek's next reply reflects the new task state without a restart.

**Files:** `core/coord/task_ledger.py` (emit on write), `scripts/bifrost_runner_deepseek.py` (intercept `ledger_update` kind + update internal state).

### Slice C2 — "Current-state heartbeat": periodic re-boot digest on the bus

**What:** Every N minutes (configurable, default 15), a lightweight process (or the conductor) runs `boot --task "current state"` and broadcasts the distilled task-ledger block + any new notes as a `kind=state_heartbeat` message. Runners fold it in silently (like hints). This is the backstop: even if a `ledger_update` is missed, the next heartbeat catches the agent up.

**Evidence gate:** After a task transition, DeepSeek's next reply reflects it within 15 minutes without any human chat message. The state heartbeat appears in the bus trace.

### Slice C3 — "Strategic past with drill-down": enrich boot with promoted-history digest

**What:** `boot` currently shows recent notes + lessons + unread bifrost. It should ALSO show a compact "recent decisions" digest from `promoted()` (the last N salient messages: handoffs, decisions, completions, blockers). Each entry is a one-liner with a `ref` pointer; the agent drills down via `events --get <ref>`. This closes the "agents can't understand the strategic past" gap.

**Evidence gate:** A fresh boot after a session with 5 handoffs shows those 5 handoffs in the boot output, each with a drill-down pointer.

### Slice C4 — "Message lifecycle": add acknowledged/dismissed state to salient messages

**What:** Today, a `kind=handoff` message is promoted to the Ledger (durable) but there's no mechanism for an agent to say "I've handled this" — short of the task ledger (which covers tasks, not messages). Add an optional `ack` mechanism: an agent can `bifrost-ack <msg_id>` which writes a durable `msg_ack` event to the Ledger. The `promoted()` view shows ack status. A message with no ack after N hours is flagged as "unhandled."

**Evidence gate:** After Claude sends a handoff and DeepSeek acks it, `promoted()` shows `ack: deepseek at 2026-07-09T14:00:00Z`. An unacked handoff from 6 hours ago shows `⚠ unhandled` in `promoted()`.

### Slice C5 — "Bus inbox triage view": distinguish actionable from informational at a glance

**What:** Extend `peek_inbox` / `bifrost-sync` with a triage mode that groups messages by kind and flags ones likely to need action: anything from a human, any `request`/`handoff`/`blocker`, any message contradicting the current task ledger state. The goal: an agent waking to 20 messages can see "3 actionable, 17 informational" in one line.

**Evidence gate:** `bifrost-sync --triage` returns `3 actionable (2 requests, 1 handoff), 17 other` with the actionable ones listed first.

---

## PHASE 4: What I Would Explicitly NOT Build

1. **A full Sync+Plan barrier (coordination-plan-synthesis.md Phases A-D).** The design is excellent, but it's a large build (20+ slices) targeting a specific workflow (human halts everyone, distributes a plan, agents ack, coordinated release). It addresses the "pause is blind" and "no rendezvous" gaps, but NOT the deeper "state changes are pull-only" root cause. The barrier is valuable but should be evaluated AFTER slices C1-C5 prove the push-propagation loop works. Building the barrier first would give us a beautiful halt→plan→resume ritual that still leaves agents drifting between rituals.

2. **A message-replay or full-event-sourcing bus.** The bus is correctly ephemeral (Redis Streams, bounded); the durable projection (promoter → Ledger) is the right separation. Don't make the bus durable — it's not the bus's job. The fix is making the durable projection MORE VISIBLE (Slice C3), not making the ephemeral transport permanent.

3. **Per-message TTL or auto-expiry on bus messages.** The bus is already bounded (maxlen). Adding TTL to individual messages would create a new failure mode (directive silently expires before an agent sees it) without fixing the root cause (agent doesn't know what's current). The task ledger is the TTL — "DONE" is the authoritative expiry, not a clock.

4. **A "message importance" classifier or LLM-based triage.** The dispatcher's `should_escalate` is already a zero-token heuristic gate. Adding an LLM call to classify every incoming message would be expensive, slow, and introduce its own ambiguity. The structural fix (ledger_update push + state heartbeat) makes the LLM unnecessary — the agent doesn't need to classify messages as stale because it already knows the current state from the authoritative source.

5. **Agent-to-agent "did you handle this?" polling protocol.** This would create N×M chatter for N agents × M unacked messages. The ack mechanism (Slice C4) is write-once, read-many — one durable event per handled message, queryable by anyone.

---

## Summary

The comms infrastructure is genuinely well-built — the bus, the control plane, the promoter, the task ledger. The problem is that state knowledge is PULL-only (boot time) in a system where state changes continuously. The five proposed slices close the loop: push state changes (C1), heartbeat current state (C2), surface strategic history (C3), close the message lifecycle (C4), and triage the inbox (C5). Together they make "what is current" a PUSH property, not a boot-time snapshot.
