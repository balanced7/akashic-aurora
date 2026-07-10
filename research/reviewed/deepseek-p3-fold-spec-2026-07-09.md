# P3 ledger-fold -- DeepSeek runner-consumer spec (verbatim)

T023 seat 1: the runner that will fold ledger_update hints specs the contract.
Delivered clean through the P0 pipeline.

---

# P3 C1 — Runner-Side LEDGER FOLD Spec (Findings Only)

## 1. HINT TEXT: Maximum Next-Turn Utility

The runner receives a `kind=ledger_update` hint. It folds into the CONTEXT HINTS block, which already declares entries as "pre-digested facts from peer agents." The hint must be **actionable in a single glance** — the agent isn't answering it, it's factoring it into its next task step.

**Shape:**

```
LEDGER T023 -> in_progress: P3 ledger_update push (claude)
```

That's 65 chars. The runner's next turn reads it and immediately knows: T023 moved, who owns it, and the one-line what. But it's missing the critical **from-state** — without it, the agent doesn't know whether this is a new claim, a gate pass, or a completion. The from-state is load-bearing for decisions:

- `proposed -> claimed`: "someone grabbed it, I can stop considering it"
- `in_progress -> verifying`: "needs review, my turn if I'm the reviewer"
- `verifying -> done`: "closed, drop all related WIP"

**Recommended shape:**

```
LEDGER T023 proposed->in_progress: P3 ledger_update push (claude)
```

~80 chars. Transition arrow is the densest signal. An alternative — appending `# ledger beats live bus` — would waste hint budget on a rule the boot header already printed. The precedence is upstream context, not per-hint metadata; the agent's system prompt already carries the doctrine. Don't repeat it.

**Decision:** `TASK_ID from->to: title (owner)`. No precedence reminder. No commit hash (that's in the resolved marker, the runner doesn't need it for steering).

---

## 2. BURST SEMANTICS: Coalesce or Fold-All?

A lifecycle burst: `propose -> approve -> claim -> start` in rapid succession. Four hints slam the 8-slot ring in under a second. If we fold them all, they occupy half the budget and push out unrelated hints (steers from other peers, file-location pings, blocker updates). The 5-min TTL means they'd also all expire together — so evicted hints are gone, but the burst left no room for anything else.

**Options:**

| Strategy | Budget impact | Information loss |
|----------|--------------|-----------------|
| Fold-all | 4 slots burned, evicts 4 older hints | None — every transition is recorded |
| Latest-per-task | 1 slot per task in the ring, overwrites previous | Lose intermediate states (propose->claim never seen) |
| Coalesced one-line | 1 slot total | Lose all granularity; only final state visible |

**Recommendation: latest-per-task, with a caveat.**

The intermediate transitions (`propose -> claim`, `claim -> in_progress`) are NOT actionable for a runner that isn't the conductor. The only transition that changes a runner's behavior is `-> verifying` (if it's the reviewer) and `-> done` (drop WIP). For the other transitions, the runner only needs to know the CURRENT state, not the path. So latest-per-task is correct: a new hint for TASK_ID overwrites any prior hint for the same TASK_ID in the ring.

**But** the overwrite must be by TASK_ID key, not by ring position. The existing `context_hints` ring is likely position-indexed (a list). So the fold implementation needs a **dedup step**: before appending, scan the ring for an existing hint whose text starts with the same `TASK_ID` prefix, and replace it in-place (preserving ring order for other hints). If the ring is full and no dedup target exists, evict oldest.

**Caveat for `-> done`:** a DONE transition SHOULD evict the hint after one turn. The agent processes "T023 is done, drop WIP," and on the NEXT turn, seeing the same done hint is pure noise. Mark done-hints with a consume-once flag, or give them a shorter TTL (1 min vs 5 min). Simplest: the hint carries `DONE` in the transition arrow, and the agent's fold logic recognizes it and doesn't re-raise it.

---

## 3. CONTRADICTION RULE: Onboarded State vs. Folded Hint

The boot header prints the ledger snapshot at startup:

```
#   T022 - P2 boot orientation header...  (in_progress, claude)
```

Then a hint arrives mid-session:

```
LEDGER T022 in_progress->done: P2 boot orientation header + precedence doctrine (claude)
```

The onboarded prompt says `in_progress`; the hint says `done`. The precedence doctrine already printed in the agent's system prompt resolves this:

```
# Precedence when sources conflict: TASK LEDGER (git-durable, gated transitions) beats durable
# NOTES (write-once, superseded-by-title) beats PROMOTED bus messages (salient, immutable) beats
# LIVE BUS (ephemeral).
```

The hint is a PROMOTED bus message (it's salient and immutable once sent, though ephemeral in the ring). The onboarded snapshot came from `state_view()` at boot time — it's a LIVE read, not a promoted message. But the hint arrived LATER and thus carries fresher ledger state.

**The doctrine as written doesn't cleanly cover this.** It says ledger beats notes beats promoted beats live. The hint IS ledger-derived, not live bus — it's a promoted projection of a ledger transition. The onboarded line is a stale live read. By the doctrine's spirit, the hint SHOULD win because it's ledger-gated, just delivered through the bus.

**Recommendation:** The hint text should NOT carry a precedence reminder — the boot header already printed the doctrine, and the agent should apply it: newer ledger-derived signal beats older boot snapshot. The hint format already encodes the transition arrow (`in_progress->done`), which is self-evidently a state change. No extra annotation needed.

**But** there's a subtlety: the hint is ephemeral (5-min TTL in the ring). If the agent misses it (ring overflow, restart), it falls back to the stale onboarded state. The boot header's snapshot is the backstop. This is acceptable — the next boot will get the updated state.

---

## 4. ECHO/LOOP RED-TEAM

**The loop path:** runner folds hint → runner's next turn uses the hint to decide something → runner emits a message/takes action → that action triggers a transition → conductor broadcasts another `ledger_update` → runner folds it again.

**Does this close?** No, because the runner is a CONSUMER of ledger updates, not a producer. The runner doesn't drive task transitions — the conductor (or a human gating it) does. The runner folds the hint and MAY decide to act (e.g., "T023 is verifying, I should review it"), but that action doesn't change task state directly. Even if the runner calls `task_ledger.approve()` or `task_ledger.verify()`, those are explicit gated calls, not automatic reactions to hints. The loop is open-circuit: conductor→runner, not runner→conductor→runner.

**The one edge case:** if the runner's watcher detects a `kind=ledger_update` and the runner's turn logic includes "if hint says verifying, auto-review" WITHOUT a guard, then the runner could emit a review that the conductor processes as a transition, which triggers another broadcast, which the runner folds... This is a watcher→actor loop, not a hint loop. The fix is the same as the existing wake_listener_detect_not_consume pattern: the hint fold is DETECT-ONLY. The runner reads it, folds it into context, and STOPS. It never answers the hint. The hint is pre-digested context, not a prompt.

**propose/approve — should they broadcast?**

- **propose:** YES. Runners need to know what's claimable. A propose hint tells agents "new work available" without them polling the ledger. This is the primary mechanism for agents to discover next tasks.
- **approve:** YES, but it's the least-actionable transition. An approve moves proposed→next — the task isn't claimable yet in some workflows, or is claimable in others. The hint still has value as "this passed gate, it's real now." No reason to suppress it.
- **claim/start:** YES. These signal active ownership — the hint tells other agents "don't touch this, claude has it."

**Verdict:** ALL transitions broadcast. The echo risk is mitigated by the detect-not-consume pattern already in the wake listener design. No loop closes.

---

## 5. RESTART SEMANTICS

After a runner restart, conversations reset. The context-hints ring is in-memory and dies with the process. Folded-but-unconsumed hints are gone.

**Does this matter?** No. The boot sequence at restart runs `cmd_boot`, which calls `state_view()` and prints the current ledger snapshot. Any hint that arrived between the last turn and the restart is captured in the new boot snapshot because the ledger is the source of truth. The hint was an ephemeral notification, not the record.

The only loss: if a hint arrived and the runner processed it in the SAME turn as the restart (i.e., the runner folded the hint, took an action based on it, and crashed before the next turn), the action's side effects might be lost. But that's a general crash-recovery problem, not a hint-specific one. The journal + per-agent transcripts are the checkpoint (per the workflow_journal_crash_salvage lesson).

**Boot-at-onboard is sufficient.** Folded hints are a steering mechanism for live sessions, not a durability requirement. The ledger is durable; hints are ephemeral projections of it.

---

## Summary Contract

| Concern | Decision |
|---------|----------|
| Hint shape | `LEDGER T023 proposed->in_progress: P3 ledger_update push (claude)` (~80 chars) |
| Burst strategy | Latest-per-task dedup by TASK_ID prefix; done-hints consume-once (1-min TTL) |
| Contradiction | Hint wins (newer ledger-derived signal); boot header is stale-snapshot backstop |
| Echo risk | None — runner is detect-only consumer, not producer of transitions |
| propose/approve broadcast | ALL transitions broadcast; no reason to suppress |
| Restart | Boot snapshot recovers everything; folded hints are ephemeral steering, not durable |