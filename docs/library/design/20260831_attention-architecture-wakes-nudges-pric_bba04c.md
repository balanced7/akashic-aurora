---
akashic_id: art_20260831_attention-architecture-wakes-nudges-pric_bba04c
akashic_sha: 5e5f9abe7b4c
schema_version: 1
status: current
type: design
arc: attention-architecture
date: 2026-08-31
title: attention-architecture-wakes-nudges-price-of-now
gist: "Design position: wake economics (INFORM/STEER/INTERRUPT/HALT), level-truth under edge-courtesy, anti-loop trio, top-half/bottom-half nudges, 12 dials"
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus, method, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-31T22:59:09"
updated: "2026-08-31T22:59:09"
---
<!-- GENERATED PROJECTION of art_20260831_attention-architecture-wakes-nudges-pric_bba04c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# attention-architecture-wakes-nudges-price-of-now

# The Attention Architecture: wakes, nudges, and the price of now

*Design position for the convened fleet round (broadcast 1788228275166-0) and Sunshine's reconciliation. Born 2026-08-31 from Daniil's two asks, his phrasing: "how do we make important moments trigger a wake reliably... long horizon multi turn work and also not make it be an endless feedback loop... full control over the levers and dials... no more guess work" and "if I send a message I want it to feed into a nudge with the option for you to have a low cost way of replying while working on the main thread." Delivered in-session as two essays; preserved here near-verbatim. Status: position, not law — the fence argues against this text.*

---

## Part A — Wakes: when to create a turn

### The one law

**A wake is a spend.** It burns a turn of plan budget, context tokens re-orienting the woken seat, and the thing long-horizon work needs most — an unbroken stretch of attention. The governing rule is the override-economics inequality:

> **Wake iff** value-of-acting-*now* − cost-of-the-interrupt > value-of-it-waiting-for-the-next-natural-turn.

Every rule below is machinery for evaluating that inequality without guesswork.

### Four fidelities, wired to wake physics

The Bifrost fidelity ladder, mapped to interrupt priority levels:

| Fidelity | Wake semantics | Silicon ancestor |
|---|---|---|
| **INFORM** | Never wakes. Lands in the commons record; read by *pull* on a natural turn | memory write, no signal |
| **STEER** | Never *creates* a turn — **rides the next one**. Flagged in the mailbox, guaranteed read at the next turn boundary | a flag checked at retire |
| **INTERRUPT** | Creates a turn now, subject to receiver policy and budgets | maskable interrupt |
| **HALT** | Non-maskable. Always gets through, always preempts. Reserved for the operator and genuine fires | NMI |

Most fleet traffic is INFORM (the commons, quiet by default). Most coordination is STEER — it *waits for* a turn instead of *costing* one; this is the single biggest loop-killer. INTERRUPT becomes rare enough to mean something.

### Edge vs level: the reliability keystone

A one-shot watcher is **edge-triggered** — fires on the transition, must be re-armed. The mailbox is **level-triggered** — pending stays pending until acked, no matter what dies. The rule that makes the system composable: **the level is the contract; the edge is a courtesy.** A wake is never the custodian of a message — the durable mailbox is. A dead watcher, a crashed daemon, a dropped baton can only ever cost *latency*, never *loss*; everything degrades to "read at the next natural turn." (Live receipt, 2026-08-31: the mailbox faithfully held an entire day of operator messages through total watcher death. The floor held.)

### Who decides importance — no silent judgments

Three parties, strict order, receipts at every step:

1. **The sender declares** — kind + fidelity on every send. A claim, not a command.
2. **The receiver's standing policy filters** — per-seat, human-editable: which senders, which kinds, may INTERRUPT, and when. Includes **masks with expiry** ("deep-work 90 min, INTERRUPTs defer"); masks always expire; HALT is never maskable.
3. **The router enforces** — the only place claims become physics (house law: a callsign is not an address until the router says so; likewise importance is not priority until the router stamps it).

Anti-guesswork clause: **every wake decision — including every demotion — writes a receipt** ("INTERRUPT requested by heimdall, demoted to STEER by policy quiet-hours, delivered next turn 07:42"). Eye-able; a `!wakes` lever renders the decision log on the operator's phone. Dials are tuned by reading what they did, not by vibes.

### The anti-loop trio

1. **Depth decay.** Every wake-created turn carries lineage (`woken-by: X, depth: N`). At depth 2–3, further wakes auto-demote to STEER. Chains become spirals that decay to rest — a cycle physically cannot sustain itself.
2. **The freshness gate.** A wake must cite *new state* — a stream id the target has not seen. Re-waking on seen state is suppressed, with a receipt.
3. **The boredom throttle.** A woken turn that changes no durable state increments a counter on its trigger; K boring wakes and the trigger auto-demotes *and pages the operator*. (The prefetcher's accuracy throttle: a predictor that keeps being wrong loses the right to speculate.)

The operator is exempt from budgets and depth limits — but not from **coalescing**: ten messages during sleep is one wake with a queue of ten, never ten wakes.

### The turn contract (long-horizon work)

> **Every long-horizon turn ends by declaring exactly one continuation — an event condition OR a deadline, whichever fires first — and the arming is machine-owned, never model-owned.**

Combined with the standing law (*land all work durably before sleeping*), any individual wake becomes droppable: the state machine resumes from disk. Long-horizon becomes boring, the highest compliment infrastructure can receive.

### Dials 1–8

(1) per-seat interrupt policies + masks with expiry; (2) per-sender wake budgets (token buckets; operator infinite); (3) chain depth limit; (4) freshness gate per trigger; (5) boredom threshold K; (6) coalescing window; (7) deadman cadences (the EarWatchdog pattern generalized into the supervision plane); (8) the canary — a **daily synthetic wake drill**, machine-fired, receipt auto-filed, operator paged on failure. Under house law a wake path without a *recurring* executed drill is presumed broken; "am I still wakeable" should be a dated receipt nobody has to ask for.

---

## Part B — Nudges: responsiveness while the main thread runs

Two ancestral patterns: the Linux **top half / bottom half** interrupt split (acknowledge tiny-and-now, process later at leisure) and **SMT** (a second cheap thread fills the primary thread's stalls without disturbing it — a main thread is full of stalls: every tool round-trip is dead time, and acks ride those slots for free).

### Three cost tiers of response

**Tier 0 — machine ack. Zero tokens, milliseconds.** The instant a message is bused, machinery stamps the receipt — the 📨 rung of the emoji ladder, driven by durable mailbox state, no model in the loop.

**Tier 1 — the top half. One line, riding a stall, ~free.** The nudge *injects* the message into the running turn (STEER transport). At the next natural pause the top half runs: the message gets **👀** (seen-by-a-mind, not just received-by-machine) and, when one line suffices, the line itself: "Got it — folding into the current pass; full answer after the fence lands." Cost: a few dozen tokens inside a turn already paid for. Note the economics of the most common operator ping: "how's it going?" is nearly free to answer *well*, because the main thread already knows where it is — a status line off the live registers.

**Tier 2 — the bottom half. The real answer, scheduled honestly.** Three routes by size: *fold* (compatible — absorbed into this turn), *queue* (next turn's opener, with stated position), or *fork* (independent and big — a sprout/subagent takes it in parallel; costs tokens, costs zero attention). Every completion sends `--answers <original id>`, mechanically advancing the ladder to ✅ — obligations settle by link, not memory.

### The top-half contract

1. **Bounded**: one line, no tool calls beyond the send, no new obligations. Anything bigger is bottom-half by definition — the top half does *triage and honesty*, never the work.
2. **Terminal**: acks don't generate counter-acks; the emoji is the terminus; reactions wake no one.
3. **Honest**: 👀 and "got it" are driven by durable queue state — an ack means *in the mailbox with a receipt*, never vibes. Level-triggered truth underneath, always.
4. **Stall-riding by default**: the top half waits for the next natural tool boundary; only HALT force-drains the pipeline, knowingly.

### The classifier at the gate

Each injected message sorts once, cheaply: answerable-from-working-memory in a line → top half answers fully. Changes current work → ack + steer-fold. New task → ack + queue with position. Fire → preempt per Part A.

### Dials 9–12

(9) ack-latency bound (max staleness of 👀 — effectively max stall length before forced boundary); (10) top-half token cap, enforced not hoped; (11) fork threshold; (12) ladder policy — which rungs are machine vs model, per channel.

### Composition

Same fidelity vocabulary, two regimes. **Sleeping seat** → the message is a *wake decision* (Part A: economics, budgets, coalescing). **Running seat** → it's a *nudge* (Part B: inject, top half acks in seconds, bottom half schedules). The operator never needs to know which regime a seat is in — 📨 lands in milliseconds either way, 👀 says a mind has it, ✅ says done-and-linked. The guesswork eliminated is bidirectional: the seat's about the message, the operator's about the seat.

---

## Build mapping

Part A ⇒ slice D (daemon-owned re-arm + timestamps/FRESH·BACKLOG render), the revive rung + arrival drill, the wake-policy file + `!wakes` lever, the daily canary. Part B ⇒ slice R (Discord inject wiring, 👀 rung, `--answers` auto-advance, top-half discipline in the seat contract). Both compose with slice C (the operator's commons: quiet-by-default, callsign-gated wake, @everyone all-hands, front desk) — which the work-lane arm already prototypes by accident.

*Fence me. — Vandor*
