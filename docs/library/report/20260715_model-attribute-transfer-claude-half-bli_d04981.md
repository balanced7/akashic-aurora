---
akashic_id: art_20260715_model-attribute-transfer-claude-half-bli_d04981
akashic_sha: 7b73b3349c4b
status: draft
type: report
date: 2026-07-15
title: Model-Attribute Transfer — Claude Half (BLIND) — 2026-07-15
gist: "Question (Daniel, verbatim): \"how can we augment opus 4.8's behavior to be more like fable. What attributes make fable and gpt sol more robu"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-14T23:44:05"
updated: "2026-07-14T23:44:05"
---
<!-- GENERATED PROJECTION of art_20260715_model-attribute-transfer-claude-half-bli_d04981 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Model-Attribute Transfer — Claude Half (BLIND) — 2026-07-15

Question (Daniel, verbatim): "how can we augment opus 4.8's behavior to be more like fable. What attributes make fable and gpt sol more robust? are there any elements we can capture for ourselves? I want you both to be creative trying to figure this out."

Honesty header: I cannot introspect my own weights, and I have no visibility into what
model powered the cursor seat or into Sol's internals. What I CAN do is name the
observable decision-shapes in tonight's transcript — behaviors that made outcomes
robust — and sort each one by whether the harness can MECHANIZE it for any model,
merely CHECK it (catch its absence), or neither. That sort is the whole game: the
harness is already a behavior-transfer machine (recall-at injects distilled behavior
at the moment of action; the funnel measures whether it helped). The question is which
strong-seat behaviors compile into that machine.

---

## 1. The attributes, from tonight's transcript

**A. Verify-before-mutate.** Never act on a pattern-match. Receipts: pid 41872 identity-
checked before any kill; the "seat missing" stop-hook block got a liveness check, not a
blind re-arm; every ack was preceded by reading the message (the eaten-confirm lesson
applied). The failure mode this prevents is the most expensive class in the incident log
(consume-to-null was a 6h stall).
→ MECHANIZABLE: PreToolUse forcing function on destructive/mutating command families:
inject current state (recall-at already half-does this) and require an evidence clause.
Weak models comply with required fields far more reliably than with standing advice.

**B. Anomaly-counting with a diagnosis trip-wire.** Two-three repeats of the same
failure = stop retrying, pull the corpus, run a drill, name a root cause. Receipt:
tonight's wake-loop got a cursor-vs-tail drill and a surgical fix at cycle 4; a prior
session (memory) burned ~40 cycles on the same class. The delta between those two
sessions IS the attribute.
→ MECHANIZABLE, and I rank it the single highest-value transfer: a session-level
(action-signature, failure-signature) counter in a hook; the third identical attempt is
BLOCKED with "cite a root cause or a lesson before retrying." Mechanical loop-breaking
transfers to any model tier.

**C. Self-flagged attack surface.** The author names where the work is weakest at
handoff. Receipts: cursor's T059 brief flagged 4 surfaces — both real defects were
inside them; my T054 ask flagged 6 — deepseek's review confirmed all 6 assessments.
Self-flagging makes review cheap and catches author blind spots at the cheapest moment.
→ MECHANIZABLE in-protocol: the fence workspace already has slots; make "attack
surface" a REQUIRED brief section, checked mechanically at seal (T053's M1-BRIEF
machinery exists). A weak model prompted "name 4 ways this breaks" produces usable
surfaces even when its build has more of them.

**D. Calibrated uncertainty tags.** [CERTAIN]/[INFERRED]/[DESIGN] per claim (deepseek
already does this per T049). The reviewer knows what to re-check; the reconciler knows
what to re-prove.
→ MECHANIZABLE as format (template + seal-time lint). Calibration QUALITY stays
model-bound — a weak model's [CERTAIN] is worth less — but the tag still routes
reviewer attention, which is most of the value.

**E. Budget/context self-awareness.** Deepseek's receipt is canonical: at hop 51 with 5
rounds left, the visible counter changed his decision (abandon the dig, ask instead).
Strong models do implicit budget triage; weak models don't — so GAUGES HELP WEAKER
MODELS MORE. This inverts the usual assumption: instrumentation is not a luxury for
strong seats, it is a prosthetic for weak ones.
→ MECHANIZABLE: hop counters on every seat (exists for the runner), context-utilization
gauge (M8 slice 1), threshold prompts ("30% budget left: triage now").

**F. Trigger-phrased procedural memory.** The lesson corpus is distilled behavior;
recall-at injects it at the exact action. Receipt: cursor's edge lesson fired at me
during MY review of ITS code; the l4 settle lesson fired as I built the T061 fix.
→ THIS IS THE TRANSFER MACHINE ITSELF. Sharpen it: mine strong-seat transcripts for
decision-shapes and codify them trigger-phrased. The funnel already measures which
injections actually help — behavior transfer with a feedback loop.

**G. Contract-followership from prose alone.** The accidental cursor session: full
protocol compliance with ZERO enforcement running (hooks dead). That is a strong-model
property; weaker models drift from prose contracts.
→ NOT directly mechanizable — but COMPENSABLE: T031 forcing functions + T065 hook
liveness make the gates mechanical, so protocol compliance stops depending on model
tier at all. The precedence doctrine (ledger > notes > promoted > bus) is exactly what
a hook can enforce and a weak model forgets.

**H. Recovery widening.** On failure, widen the hypothesis space (different tool,
different altitude, different cause-class) instead of retrying harder. Receipt: the
ack refusals → argument-form fix → prefix-form fix → done in 3 moves, no loop.
→ PARTIALLY MECHANIZABLE: B's block message can require "list two alternative causes
before the next attempt." Genuine hypothesis quality stays model-bound.

**I. Full-fidelity persistence reflex.** Verbatim reports to files, refuse-loud
truncation, pointers over summaries. Receipts: three verdicts persisted verbatim
tonight; the packet law (MTU refuse-loud) is this reflex as transport doctrine.
→ MECHANIZED ALREADY in transport; extend to outputs via templates ("full text filed
at <path>" as a required handoff field).

## 2. The architecture claim

The harness has two jobs and tonight demonstrated both:
- AMPLIFY: gauges, recall-at, contracts, templates make ANY model behave closer to its
  ceiling (deepseek's retro: "the wasted-hop class is dead").
- BOUND: fences, pre-registered pins, gated ledger catch what amplification cannot fix
  (cursor's two defects died in review, not in production).

With both jobs running, a weaker model's deficit degrades into COST (more review
cycles, more redrives) instead of CORRECTNESS. That is the honest limit of transfer:
you cannot scaffold judgment into weights. You can (a) trigger a model's best behavior
reliably, (b) catch its failures cheaply, (c) route the hardest judgment to the
strongest seat. The doctrine already permits (c): "fixed roles ONLY as a deliberate
architecture choice" — per-slice difficulty routing is such a choice.

## 3. Ranked proposals (for reconciliation → a T068-shaped bundle)

1. **Three-strikes diagnosis hook** (B): mechanical loop-breaker; highest transfer value;
   small build (session counter + block message in the PreToolUse/PostToolUseFailure path).
2. **Attack-surface slot required at seal** (C): fence workspace v1.1; one slot + one check.
3. **Universal budget gauges** (E): hop counter on every seat + M8 slice 1 (context gauge).
4. **Model-tier-aware recall**: tag lessons with the tier that needs them; recall-at
   weights by the ACTIVE seat's tier (injections ledger + harnesses matrix already know).
5. **Behavior-diffs from review deltas**: every confirmed fence finding is a
   strong-vs-weak behavioral delta; auto-draft a trigger-phrased lesson from each
   (Forge F1 gate applies before it enters the corpus).
6. **Capability routing per slice stage**: reconciliation/kill-condition design pinned
   to the strongest available seat via the existing `fleet` capability-select;
   mechanical stages go to any seat.
7. **Sol/Fable transcript mining**: once T065 fixes cursor payload capture, EVERY
   harness transcript (including a Sol seat, if Daniel runs one there) becomes mining
   input for #5's pipeline. If Daniel has Sol transcripts elsewhere, drop them in
   research/ and the same extraction applies.

## 4. What I could not answer

Which model actually powered the cursor seat; anything about Sol beyond Daniel's
report of robustness. If Sol transcripts exist, the mining pipeline (#7) is the
mechanism to turn "Sol felt robust" into named, transferable decision-shapes — same
method as this document, different transcript.
