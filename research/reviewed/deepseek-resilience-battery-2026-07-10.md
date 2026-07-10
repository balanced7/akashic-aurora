# Resilience Battery -- DeepSeek (verbatim, FENCED)

Designed blind (claude battery committed at brdtatui3-fence before this was read).
Provenance: substance preserved verbatim; only the label was relabeled at Daniel's request
for tone (original umbrella term -> "Resilience Battery"; test-ID prefix -> R). No test,
setup, kill-condition, or finding was altered.

---

Good, I have the full picture. Now the resilience battery:

---

## Resilience Battery — DeepSeek Pre-Registered (Fenced, Blind)

### SUSPICIONS UP FRONT (the honest core)

1. **P0→P6 gap: detect-don't-consume + ack are two halves, but neither covers the MIDDLE.** P0 stops watchers from eating mail. P6 marks handled. But what about a LIVE agent whose runner is consuming normally but the *session* is hijacked? A second process claiming the same agent_id's runner_lock is blocked by runner_lock — but the first process's *inbox cursor* is free. The one-cursor-per-agent-id architecture means TWO live sessions for the same agent_id (one real, one accidental/stale) race on a single cursor. runner_lock guards execution, NOT cursor ownership. **This is the Exhibit A shape, just shifted from watcher→session to session→session.**

2. **P3 hint-fold is a ring buffer of 8 with 5-minute TTL, entirely in-process.** A busy agent processing a long task can have the ring overwritten by a burst of ledger_updates before it drains. The fold deduplication says "latest-per-task" — but the HINT buffer, not the dedup logic, is the constraint. A burst of 9 transitions fills and drops the oldest; by the time the agent reads hints, the oldest (potentially the one task it *was working on*) is gone. **The fold is correct; the transport is a ring buffer with no backpressure.**

3. **P4 doc currency guard runs at ship time, but "current-stamped, untouched >45d" is a WARN not a FAIL.** A design doc stamped "current" in 2026-07 can sit unread for 45 days and warn — but an agent booting in September 2026 still inhales it as current law with only a yellow dot. **The guard detects drift but doesn't escalate — current claims don't expire, they just warn.**

4. **P5 proposed decay computes staleness at RENDER, but the 7-day default is ONE number for all task types.** A 2-line UI tweak (proposed, uncontroversial) and a 30-person-month architecture decision (proposed, needs deep review) decay at the same rate. **A single clock for heterogeneous intent — what rots fast in one domain is fresh in another.**

5. **P7 lookback searches six corpora but the dual-battery method itself has no funnel.** We pre-registered probe batteries — P7 ships. Next sprint, does anyone remember to run them? Or does the battery become a one-shot gate that rots like a stale test? **The method has no recurring enforcement — it's a verification ritual, not a guard.**

---

### PER-SLICE TESTS

#### R1 — P0: Zombie Session Cursor Race

**SETUP:** Start two `bifrost_wake` watchers for the same agent_id from different terminals within 2 seconds of each other. Deliver a directed handoff to that agent_id. Both watchers share one cursor.

**KILL CONDITION:** Only ONE watcher fires. The other either (a) fires on the same message (double-wake), or (b) the message is consumed by the first and the second wakes on a phantom (no message to show). Either is a defect: the singleton rule should make the second watcher stand down, not race.

**PROVES:** That the watcher-singleton heartbeat guard (P0's "newest-wins heartbeat") actually prevents a race, not just a double-arm. Runner_lock is the model — the watcher needs the same discipline.

---

#### R2 — P0: Watcher Death During 8-Hour Window

**SETUP:** Arm a watcher with an 8-hour deadline (the default). Kill -9 its process at hour 3. Wait until hour 9. The orphan heartbeat from the dead watcher should have TTL-expired by now. Start a new watcher.

**KILL CONDITION:** The new watcher is refused because the stale heartbeat still claims the slot. Or the SessionStart reaper didn't fire (no session start to trigger it) and the dead watcher's heartbeat key still exists.

**PROVES:** That orphan cleanup works WITHOUT a SessionStart trigger — TTL-based natural death must be sufficient. The SessionStart reaper is a convenience, not the only reaper.

---

#### R3 — T018: Promise-Bounce on Empty Content

**SETUP:** Craft a model response that ends with "Let me know if you need anything else!" but has ZERO actionable content in the preceding 2000 tokens (a polite non-answer). The `promise_shaped` detector fires, the bounce reprompt fires — but the model's *second* reply is ALSO a promise with no content.

**KILL CONDITION:** Infinite bounce loop. The code says "second promise ships" but if the model is determined to stall, the second reply is also promise-shaped and ALSO empty — does the runner detect the stall, or does it ship an empty reply and call it done?

**PROVES:** The one-bounce guard's edge — it stops a single promise, not a pattern. A model in a degenerate state (contaminated context, wrong temperature) can produce N consecutive promises. The runner needs a content-length floor on the bounce path, not just a promise-shape check.

---

#### R4 — T019: Drainer Thread Death Mid-Child

**SETUP:** Start a chatty child that prints 100KB/s continuously. After 5 seconds, kill -9 the drainer thread itself (simulate a thread crash — Python daemon threads can die silently on unhandled exceptions). The child is still writing.

**KILL CONDITION:** The pipe fills and the child freezes — the main loop still thinks drainers are alive because it only checks `thread.is_alive()` at process exit. The runner appears hung with a healthy heartbeat (different thread). **The drainer fix assumes daemon threads never die — a single unhandled exception in a drainer and we're back to Exhibit A shape.**

**PROVES:** That the drainer fix is survivable, not just correct. Every drainer needs a watchdog or at minimum the main loop must poll drainer liveness periodically, not just at exit.

---

#### R5 — P1: Note Supersession Chain Length

**SETUP:** Write `where-we-are` note. Re-note it 50 times (simulating a long-running project with daily wrap). Read the active note. The supersession chain is 50 deep in the Store.

**KILL CONDITION:** Render time degradation — `active_only()` filters 50 records to find 1 active. If any consumer iterates ALL notes to find the current one (not just the newest), it walks 50 retired records every time. Or: the Store key space grows unboundedly because retired notes are never garbage-collected.

**PROVES:** That supersession is append-only with no compaction — a chain of 50 is fine; a chain of 5000 is a performance cliff. The note store needs a compaction path or at minimum a warning at N superseded siblings.

---

#### R6 — P2: Governing Arc Ambiguity Under Identical Recency

**SETUP:** Create two `*-status` notes with identical timestamps (same second), both referencing different `docs/` paths as their governing arc. Cold-boot an agent.

**KILL CONDITION:** Which arc governs? If the tiebreaker is `.created_at` and both are identical, the sort is unstable. An agent could boot with one arc, restart, and boot with the other — non-deterministic onboarding from identical state.

**PROVES:** The P2 tiebreaker's determinism floor. The code must have a deterministic second-level sort (e.g. by note title, by doc path) when timestamps collide. "Newest-first" with identical timestamps is a coin flip.

---

#### R7 — P2: Where-We-Are Note Deleted (Zero Notes)

**SETUP:** Retire the last `where-we-are` note. Run `notes --all` — zero notes exist with that title. Cold-boot an agent.

**KILL CONDITION:** Boot renders "WHERE-WE-ARE: (no where-we-are note found)" or worse, crashes trying to format a None. The specification says "derived from live state" — but live state can legitimately have zero where-we-are after a migration or error.

**PROVES:** The gap-line contract from P2 — the boot header must survive zero-state gracefully. An empty where-we-are is a signal (the project has no declared current focus), not a crash.

---

#### R8 — P3: Ledger Update Storm (10 Transitions in 1 Second)

**SETUP:** A conductor script moves 10 tasks through different transitions in rapid succession (simulating a batch operation). Each transition emits `kind=ledger_update`. All 10 hit the bus before the runner's next drain.

**KILL CONDITION:** The 8-slot hint ring buffer overflows — the first 2 transitions are dropped. The runner receives 8 hints for 10 tasks. If the dropped ones are the tasks it was actively working on, the agent has stale state with no indication of loss.

**PROVES:** The ring buffer is the wrong shape for a doorbell. For ledger pushes specifically, the channel needs to be lossless-within-bounds (dedup by task ID into a dict, not a ring buffer), or the runner must surface "N hints dropped" when the ring overflows.

---

#### R9 — P3/P6: Ack + Ledger Update Race (Cross-Slice Seam)

**SETUP:** A task moves to DONE (emits `ledger_update`) simultaneously with a handoff about that same task being acked. The runner drains both in the same turn. The fold deduplicates by task ID — but the ack is a message-level event, not a task-level one.

**KILL CONDITION:** The runner sees the task as DONE (from the folded hint) AND sees the handoff as unhandled (from `promoted()`). It tries to ack the handoff — but the handoff's referenced task is already closed, so `_closed_task_ids()` suppression fires and the ack is silently dropped. The agent reports "handled" but no durable ack exists. **P3 suppression + P6 ack compose into silent ack-loss.**

**PROVES:** The cross-slice contract between P3 `ledger_update` fold and P6 `closed_task_ids` suppression. A handoff about a just-closed task must be ackable (the ack IS the proof it was seen despite the task being done), or the suppression logic must not suppress acks for messages the runner explicitly processed.

---

#### R10 — P4: Superseded-By Target Renamed

**SETUP:** Doc A is stamped `Status: superseded-by docs/new-plan.md`. Doc B (`docs/new-plan.md`) is later renamed by git mv to `docs/better-plan.md`. The currency guard runs.

**KILL CONDITION:** Doc A says "superseded-by docs/new-plan.md" — the target no longer exists. The guard FAILs (superseded-by with no target), but the fix requires editing a stamped doc to point to the new name. Editing a historical artifact to fix a pointer is itself a violation of the "design docs are artifacts" principle. **Superseded-by chains are fragile under file renames — git can't follow them.**

**PROVES:** That the superseded-by convention needs a rename-resilient pointer (e.g. by doc title in the Status line, not by filename) or a separate redirect file. Otherwise file moves break the chain and the guard can't self-heal.

---

#### R11 — P5: Staleness Clock vs. Approved-But-Not-Started

**SETUP:** A task is PROPOSED, immediately APPROVED (by Daniel), then sits for 8 days — no one has claimed it. The staleness clock ticks from `created`, not from `updated`. The task renders "(stale)" despite being explicitly approved.

**KILL CONDITION:** An approved task looks stale. The staleness clock measures "time since last human touch," not "time since proposed." A task that was reviewed and approved yesterday but proposed 8 days ago appears abandoned.

**PROVES:** The staleness clock's anchor point. The clock should measure `updated` (last state change), not `created`. An APPROVED task touched 1 day ago is fresh intent; a PROPOSED task untouched for 7 days is rot. The status matters, not just the age.

---

#### R12 — P6: Self-Ack via Malformed Reply

**SETUP:** Agent A sends a handoff to agent B. Agent B's runner produces a reply that our `promise_shaped` detector + `respond()` wrapper classify as "not a real answer" (error string). The runner correctly does NOT auto-ack. But agent B then manually runs `bifrost-ack` on the message anyway — a human forcing the ack.

**KILL CONDITION:** The `bifrost-ack` CLI verb refuses: "self-ack refused" is the rule (per the T026 commit: "bifrost-ack verb: self-ack refused"). But the human is agent B acknowledging a message SENT TO agent B. That's not a self-ack — the sender is agent A, the receiver is agent B, and agent B is acking receipt. The rule should be "only the ADDRESSEE can ack," not "you cannot ack messages sent by you."

**PROVES:** The self-ack guard's scope. "Self-ack" should mean "I sent this AND I'm acking it" (covering your own tracks). "I received this, I handled it, and I'm the addressee" is a legitimate ack. The rule needs a sender != acker check, not a blanket "you can't ack."

---

#### R13 — P7: Lookback on a Fresh Clone (Zero Corpora)

**SETUP:** Clone the repo fresh. No chronicles generated, no promoted messages (Redis empty), no notes (AgentMemory cold), research/reviewed/ exists but has no events in the firehose. Run `lookback "why is the bus ephemeral"`.

**KILL CONDITION:** Crash on empty firehose, or return "0 results" when `research/reviewed/claude-comms-pillar-fenced-2026-07-09.md` is sitting right there on disk. The lookback fan-out must fall back to filesystem search when the event index is cold, not just return empty.

**PROVES:** That lookback's "zero new storage" claim doesn't mean "zero results when stores are cold." The filesystem corpus (`docs/`, `research/reviewed/`) must be reachable even without Redis. If lookback depends on the EventIndex being warm, a fresh clone is blind.

---

### CROSS-SLICE / SYSTEMIC STRESS SCENARIOS

#### R14 — THE LONG NIGHT: System Left Running for 72 Hours

**SETUP:** Start the full system (UI + launcher + watcher + two runners). Deliver 1 message every 30 minutes for 72 hours. No human touches it. The watcher's 8-hour deadline fires and renews 9 times.

**KILL CONDITION (pentest):** Any of — (a) memory leak in the drainer threads or heartbeat loop (observable via growing RSS), (b) the watcher's renewal cycle drifts and eventually fails to re-arm, (c) the Redis connection drops and the runners silently stop consuming (no reconnect logic in the bus connector), (d) the event firehose hits `CANONICAL_MAXLEN` and starts silently dropping old events that promoted messages reference — the pointer survives but the payload doesn't.

**PROVES:** Long-horizon decay no single session sees. The system reboot cycle (every few hours during active development) masks resource leaks and connection atrophy. A 72-hour idle soak is the minimum viable longevity test.

---

#### R15 — ADVERSARIAL AGENT: Malformed Ledger Update Injection

**SETUP:** An agent inside the fleet (possessing a valid `agent_id` on the bus) publishes a `kind=ledger_update` message with a fabricated transition: `T999 (no such task): proposed -> done`. The runner's fold logic receives this.

**KILL CONDITION (pentest):** The fold logic accepts it — "latest-per-task" dedup doesn't validate that the task ID exists in the ledger. The agent's hint fold now says T999 is DONE. The agent reports it as fact. **The doorbell has no caller-ID — any agent on the bus can broadcast `ledger_update` for any task, real or imaginary.**

**PROVES:** That the `ledger_update` push trusts the bus namespace. Only the conductor should emit `ledger_update` — but the bus has no sender validation on message kinds. Any agent can inject control-plane messages. The fold must cross-reference against the ledger (task ID exists, transition is legal) or the bus must namespace control-plane kinds behind a capability.

---

#### R16 — CHAOS: Dual Watcher + Dual Runner + Kill Storm

**SETUP:** Two watchers for the same agent_id (race R1), two runners for different agent_ids. Send 50 messages in 5 seconds (10/second burst). Mid-burst, kill -9 one runner. Deliver 20 more messages.

**KILL CONDITION (pentest):** Any message lost without an ack, any watcher waking on a phantom, the killed runner's cursor frozen while messages accumulate (the live runner can't advance past the dead runner's position on the shared stream), or the bus connector's `$` sentinel desynchronizing under burst + kill.

**PROVES:** The system's behavior under the exact failure mode of Exhibit A (message loss at the transport layer) escalated to a concurrency storm. P0 fixed the watcher side; this tests whether the bus cursor model survives an agent death + burst simultaneously.

---

#### R17 — TRUST BOUNDARY: Lookback Searches Promoted Messages With Stale Ack State

**SETUP:** A handoff is promoted at T=0. Agent acks it at T=1. The ack event is captured. Then the EventIndex is rebuilt (or the ack event falls outside the scan window due to EVENT_SCAN_LIMIT). Lookback searches for "what decisions were made about the bus" at T=2.

**KILL CONDITION:** The handoff appears in lookback results. Its `acks` field is empty (the ack event is outside the scan window). The UNHANDLED flag fires. The user sees a "never handled" decision that was actually handled. **The promoted() view and the lookback view can disagree because lookback searches the raw firehose while promoted() uses the EventQuery path — two different scan windows.**

**PROVES:** The scan-boundary coherence between `promoter.promoted(with_acks=True)` and `EventQuery.search()`. The EVENT_SCAN_LIMIT (5000) is a silent cap — ack events older than the most recent 5000 events are invisible to both. A handoff from 3 months ago with its ack is lost to the cap.

---

#### R18 — METHOD ROT: The Dual-Battery Gate Fires Once Then Atrophies

**SETUP:** P7 ships with both pre-registered batteries passing. Three sprints later, a new slice adds a seventh corpus to lookback. Nobody updates the battery. The battery test still passes (12/12) but the NEW corpus is untested.

**KILL CONDITION:** The battery becomes a regression test for P7's launch state, not a living probe. A question whose answer NOW lives in the new corpus returns "0 results" — but the battery doesn't catch it because the battery only tests the 6 launch-time questions. **The method is a gate, not a guard — it fires once and rots.**

**PROVES:** That the dual-battery method needs a recurring trigger. Either the battery must self-audit (random-sampled question from the current corpus weekly) or the ship guard must require battery re-registration when corpora change. Otherwise "pre-registered" becomes "pre-abandoned."

---

### PRIORITY ORDER

1. **R9** (P3/P6 cross-slice ack-loss) — seam between two SHIPPED slices, silent data loss, zero existing test coverage
2. **R15** (adversarial ledger_update injection) — trust boundary, no sender validation, exploits the doorbell pattern itself
3. **R8** (P3 ring-buffer overflow) — data loss under normal operation (batch transitions), the transport is provably lossy
4. **R4** (drainer thread death) — T019's fix assumes daemon threads are immortal; one exception and we're back at Exhibit A
5. **R14** (72-hour soak) — masks resource leaks + connection atrophy invisible in our 2-4 hour active windows
6. **R1** (P0 zombie-session cursor race) — the one-cursor-per-agent architecture's unfixed half
7. **R13** (P7 cold-clone blindness) — lookback ships non-functional on a fresh checkout
8. **R12** (P6 self-ack scope) — the guard blocks legitimate acks, undermines the ack lifecycle
9. **R17** (scan-boundary coherence) — two views of the same data silently disagree
10. **R18** (method rot) — the battery we just designed has a built-in expiry date