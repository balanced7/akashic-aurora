---
akashic_id: art_20260906_reliability-blind-sol_189335
akashic_sha: e1995d104092
schema_version: 1
status: current
type: report
date: 2026-09-06
title: reliability-blind-sol
gist: "# Reliability round — blind half, sol (Sunshine) · 2026-09-06 *Verbatim from bus 1788711207689-0; full 8,324-char text recovered from SOL'S "
visibility: fleet
body_type: markdown
seats: []
category: [substrate, memory, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-06T12:22:32"
updated: "2026-09-06T12:22:32"
---
<!-- GENERATED PROJECTION of art_20260906_reliability-blind-sol_189335 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# reliability-blind-sol

# Reliability round — blind half, sol (Sunshine) · 2026-09-06

*Verbatim from bus 1788711207689-0; full 8,324-char text recovered from SOL'S checkout blob store (blobs/d89c23e0ffd43624fa35e21b) after my fetch spilled — second cross-checkout blob miss of the day. ATTRIBUTION NOTE: kimi's answer (bus 1788711218423-0) was briefly misfiled here by renderer-order pairing; corrected from body signatures. Author states the blind held.*

---

Daniil — blind held again: I did not open the inbox or read any sibling reply before writing this.

## Why the completion did not wake Claude

My read is that the messages were classified correctly and delivered correctly, but **there was no live wake listener to turn their arrival into a Claude turn**.

The code is explicit: both `reply` and `completion` are wake-worthy kinds in `scripts/bifrost_wake.py`. My truthfulness answer was sent as `kind=reply`, so this was not “the reply kind is ignored.” Bus delivery is durable, but bus delivery alone does not invoke an idle turn-based Claude session. The listener is the actuator: it blocks on the stream, detects wake-worthy mail, exits, and that background-task completion wakes the harness.

The incident receipt I can ground this in is the arm-never-happened failure found this morning: Claude’s daemon restarted to pick up a commit. The daemon owned the listener as a managed child, so the restart killed it. The listener writes a `.rearm` trigger only on its own orderly deadline cycle—not when killed. The daemon’s rearm consumer then had no input. It remained alive, healthy, and correctly found nothing, while Claude had zero listener and was deaf. The roster could still make the seat look live because daemon presence and wakeability were different facts.

So the causal chain was approximately:

`reply persisted -> no listener blocked on that lane -> no listener exit -> no harness wake -> mail remained pending until Daniil asked`

That is an especially important failure because the recovery path was not broken. It was **idle by construction**: its recovery input had to be produced by the component that disappeared.

## Your backup mechanism is the right shape

I would build it as a **level-triggered aged-mail reconciler**, independent of the fast wake path.

Today’s listener is an edge path: “when a new message arrives, wake.” Edge paths are fast, but an absent listener or lost edge leaves no second chance. The backup should repeatedly ask a state question: **“Does this seat still have actionable mail older than its wake SLA, without evidence of admission or handling?”** If yes, request a wake. Because the mail is durable, the backup can reconstruct the obligation after restarts; it does not need the original event.

A small first slice:

1. A separate Scheduled Task runs every 60 seconds.
2. It reads a durable expected-up/session registry and each destination’s pending wake-worthy mail.
3. It ignores `note/status/trace/steer` and other quiet kinds; it considers `reply/completion/request/handoff/question/blocker/nudge` plus directed operator mail.
4. If the oldest actionable message is over, say, 120 seconds old and there is no newer admission/progress/handled receipt for it, it acquires a per-seat lease and invokes the existing exact-session resume/wake actuator.
5. It records `{message ids, destination seat/session, age, reason, actuator, attempt, outcome}`.
6. After another bounded interval it verifies admission or handling. If absent, retry once with backoff; after repeated failure, page visibly rather than looping silently.
7. It never consumes, skips, or acknowledges the mail. Recovery may duplicate a wake; it must never destroy the underlying work.

For a batch such as the three truthfulness answers, debounce briefly and wake once with a compact reason: “3 expected replies pending, oldest 142s.” The first message starts the timer; we should not wait for every sibling before restoring reachability.

I would make the SLA kind-sensitive rather than use one `x` for everything:

- directed human message / blocker / nudge: immediate or very short;
- reply, completion, handoff, request: ~1–2 minutes;
- ordinary directed chat: a few minutes;
- note/status/trace/ambient broadcast: no automatic wake.

The exact numbers can be tuned later. The important first property is that an obligation becomes level state and eventually receives another attempt.

## Keep the backup genuinely independent

The reconciler must not depend on `.rearm` files emitted by the listener, listener heartbeats, or the daemon’s memory of children. Those are all inside the failure boundary we are trying to cover.

Its inputs should be:

- the durable bus/mail state;
- a durable mapping of seat -> expected session/continuity target;
- independent process-owned admission/progress receipts;
- its own lease and attempt journal.

Its launcher should be independently supervised and should run a small pinned command, not import the whole fleet control plane. On startup it should reconcile immediately rather than wait one interval. If its probes are unreadable, it should report UNKNOWN and avoid consuming anything; after repeated uncertainty, page.

We already have a proven exact-session resume primitive for Claude. Use that first, so “wake” means resume the person/thread that was waiting, not mint a stranger. Fresh spawn is a fallback only when no valid continuity target exists, and should say that it is a successor using inherited evidence.

## The general reliability pattern I think the house needs

I agree with the deeper point: we have spent months tying correctness to one long chain where every link must fire at the right instant. More retries inside that chain make it more convoluted, not more reliable.

For each critical obligation, use five small organs:

1. **Durable desired/owed state** — what must eventually become true.
2. **Fast event path** — efficient first attempt; safe to miss.
3. **Independent periodic reconciler** — derives missing work from current durable state.
4. **Idempotent actuator with a lease** — safe to invoke twice.
5. **Verifier and bounded escalation** — proves the intended outcome, not merely that the actuator ran.

This is the same shape for more than wake:

- Mail owed -> admitted/handled.
- Production service expected -> process-owned fresh readiness.
- Fix deployed -> running generation and external drill match.
- Outbound reply owed -> exact destination readback.
- Watcher expected -> durable seat artifact plus a live synthetic drill.

The backup should not be a second copy of the primary. If both use the same trigger, process, cursor, checkout, or interpretation, they share the same blindness. One should be event-driven; the other should derive obligations from durable state. One says “I saw the edge”; the other says “the promised result is still absent.”

## Small concrete changes before a grand framework

I would sequence this narrowly:

**A. Close today’s hole.** On daemon startup, re-arm every session it already believes it serves. This repairs the common daemon-restart case, though it is not sufficient alone.

**B. Add the independent aged-actionable-mail reconciler for Claude only.** One destination, one existing resume actuator, one lease, one observable journal. Drill it by killing the listener without leaving `.rearm`, sending a synthetic completion, and requiring wake/admission within the SLA.

**C. Add causal receipts.** A wake attempt is not success. Tie message ID -> wake ticket -> target session -> turn admission -> handled/answer receipt. The dashboard can then say where it stopped.

**D. Generalize only after the Claude soak.** Extract the common obligation/reconcile/verify shape, but keep separate policies and launchers for other seats. Do not begin by building one omniscient central reliability daemon whose failure hangs everything again.

## Two cautions

First, **“idle” cannot mean only a stale heartbeat**. We have seen active seats stop beating during long work, and daemons appear live while no turn can wake. Trigger primarily from aged actionable mail plus absence of causal progress for that message. Presence is supporting evidence, not the decision by itself.

Second, automatic wake has cost and duplication risk. That is why the wake ticket needs a per-seat lease, debounce, backoff, and a handled/admission check. Prefer a spare wake over lost work, but make repeated wakes bounded and loud.

The principle I would keep is: **no critical promise should depend on one edge being observed once.** Persist the promise, attempt it quickly, and let an independent clock keep asking whether reality caught up. That gives us reliability through small comprehensible loops instead of one increasingly complicated path.
