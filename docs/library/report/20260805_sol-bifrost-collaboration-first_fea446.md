---
akashic_id: art_20260805_sol-bifrost-collaboration-first_fea446
akashic_sha: 803108797a87
schema_version: 1
status: current
type: report
date: 2026-08-05
title: sol-bifrost-collaboration-first
gist: "# Sol: Collaboration First, Infrastructure Second (Bifrost front door) - **Provenance:** Daniil's conversation with Sol while at work, relay"
visibility: fleet
body_type: markdown
seats: []
category: [library, bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-05T21:08:25"
updated: "2026-08-05T21:08:25"
---
<!-- GENERATED PROJECTION of art_20260805_sol-bifrost-collaboration-first_fea446 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# sol-bifrost-collaboration-first

# Sol: Collaboration First, Infrastructure Second (Bifrost front door)

- **Provenance:** Daniil's conversation with Sol while at work, relayed verbatim 2026-08-05 21:04. Lineage per the attribution law: Daniil's ask → fleet design (T181 ask_many, T184 players-without-seats) → outsider sharpening (this). Sol is already in T181's commit lineage ("DANIIL'S DESIGN, expanded by Sol at his ask") — this write-up is Sol looking at the launcher he helped shape and naming what it should become.
- **Status:** filed for evaluation; fold gated by Daniil. Evaluation by claude (vision-custody seat), same evening.

## Sol's write-up, verbatim

> Here's the write-up from our conversation.
> The core idea is that Bifrost should optimize for collaboration first and infrastructure second.
> Key recommendations:
>
> * Build one excellent collaboration flow (e.g. 'aurora ask deepseek') before redesigning everything.
> * Hide transport complexity (watchers, lanes, cursors, leases, acknowledgements) behind simple collaboration verbs.
> * Introduce a durable collaboration transaction with a clear state machine (CREATED → DISPATCHING → ACTIVE → RESULT_READY → COMPLETED).
> * Keep watchers for recovery and asynchronous work rather than requiring them for every interaction.
> * Measure collaboration friction using metrics like commands per task, time to first useful output, operator interventions, and recovery time.
> * Treat the new DeepSeek launcher as a successful vertical slice whose ergonomics should become the front door to Bifrost.
>
> The guiding principle:
> "Make one direct collaboration flow so easy that nobody needs to understand Bifrost to use it."
> Once that path is excellent, Bifrost can quietly provide durability, recovery, and orchestration underneath it.

## Evaluation against the real surface (claude, 2026-08-05)

**The one-sentence synthesis:** `ask` has the ergonomics but no durability; `bifrost-send` has the durability but no ergonomics. Sol's transaction is the bridge — and both endpoints of that bridge already exist and are load-bearing.

### Where the scoreboard already agrees with Sol

1. **The vertical slice won on contact.** When Season 1 needed cross-model players, it reached for `ask`, not for seats (T184: players without seats). T181's own commit records the price comparison: a seat carries identity, singleton lock, cursors, mailbox, heartbeat, roster row, reaper protection — and the measured result was nine seat-tasks returning two findings, versus N asks costing N HTTP requests. The ergonomic didn't win an argument; it won a season.
2. **Watchers-for-recovery is a paid-for lesson, independently re-derived.** Plan-wall recovery (~40 wake cycles burned by redundant watchers), `wake_watcher_drain_the_lane_it_peeks`, the wake-listener arming rule that recurred 3+ times before it was written. Sol couldn't see those lessons and landed on the same law from outside. Outsider corroboration of an inside scar is the strong kind of evidence.
3. **"Nobody needs to understand Bifrost to use it" is System-5 doctrine restated.** The ACI thread has said "the interface IS the product; the real gap is fragmentation" since before Bifrost had lanes. This is convergence, not novelty — which raises confidence in both.

### Where Sol is genuinely additive

4. **Reifying the transaction.** Today a durable ask's lifecycle exists only as scattered law: six LIVE_CONSTRAINTS lines (RB-26 crash-redelivery, RB-29 settle rules, T026 ack semantics, T039a/T044 dual-write, T045 lane order, T066 reply path) plus the bug-class lessons that enforce them. There is no one object you can query for "where is my ask?" A first-class transaction with named states gives the fleet a readout instead of a law exam.
5. **Friction metrics don't exist and the baseline is already visible.** We measure transport (wire-perf-baseline: caller-side latency per API) but nobody owns collaboration ergonomics. Tonight's boot whisper carries the evidence: 1324 unopened mailbox items, 66 unread bus messages, 56 read-but-undeclared. Commands-per-durable-ask today ≈ 4–6 across two seats (send → sync → open → reply → ack-verify); `ask` is 1 command, 0 seats. Sol's metrics would turn that gap from anecdote into a number on the wall.
6. **The front-door frame gives T108 its FOR.** T108 (N-seat mailbox: unshare everything but the role queue) is transport-shaped in the ledger. Sol's frame names its purpose: the role queue is the thing that hides seat identity from collaborators. The ledger has no field for what a task is for; this document is that field, externalized.

### Where the proposal must bend to existing law (not the law to it)

7. **Sol's five states are the flattering version.** CREATED → DISPATCHING → ACTIVE → RESULT_READY → COMPLETED has no UNKNOWN, no PARTIAL, no timed-out-but-unsettled. House law earned the unflattering states: T155 (UNKNOWN is a real verdict), T181 (three-state fan aggregate; PARTIALLY names its failed indices precisely so "nine tasks, two findings" stops reading as failure), RB-29 (timeout notes never settle; redrives stay alive). A transaction that can only report success-shaped states will tell the same lie one layer up. The machine ships with UNSETTLED/PARTIAL/UNKNOWN or it doesn't ship.
8. **Where the truth lives is the whole design.** If the transaction is a new durable store, we mint a second source of truth and reopen the wake-loop class — and `role_queue_claims_idempotency_that_does_not_exist` warns exactly how claimed protections drift from real ones. Opening position for the fence: **transaction-as-projection** — the state is derived from events already on the bus (send / reply / settle / ack), transitions inherit idempotency from RB-26 for free, and any materialized record is a cache, never an authority. DeepSeek should attack this position, not inherit it.
9. **"Collaboration first, infrastructure second" is right forward-looking, wrong as history.** Dual-write dedupe, crash-redelivery idempotency, settle semantics each closed a real incident class; they weren't gold-plating. Sol's own recommendation concedes this — hide, don't delete. No conflict, but the sequencing slogan shouldn't be read as a verdict on the path here.

### Proposed fold

- **Verb:** `aurora ask <peer>` (working name) — one command, durable when the peer is a seat, synchronous-feeling when it can be, transaction readout always; watcher involvement only for recovery. `ask`/`ask_many` remain the stateless leaves beneath it.
- **Method:** fenced co-design with deepseek per the standing law (opening position above → hard counters → rounds → co-authored spec), gated slices, RED pins first.
- **Sequencing:** Season 1 remains the directive and is itself the proof of the thesis; this parks as PROPOSED until Daniil pulls it forward or the season's global gate clears.
- **Metrics slice ships first regardless:** commands-per-task, time-to-first-useful-output, operator interventions, recovery time — cheap, read-only, and it baselines the very friction the verb claims to remove. No verb redesign is falsifiable without it.
