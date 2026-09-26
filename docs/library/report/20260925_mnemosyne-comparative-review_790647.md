---
akashic_id: art_20260925_mnemosyne-comparative-review_790647
akashic_sha: cdbb9a1a8c96
schema_version: 1
status: current
type: report
date: 2026-09-25
title: mnemosyne-comparative-review
gist: "# Mnemosyne (Sergey Nikitenko) — comparative review against Akashic Aurora Reviewed 2026-09-25 21:24 EDT by claude (Vandor), at Daniel's req"
visibility: fleet
body_type: markdown
seats: []
category: [memory, identity]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-25T21:26:13"
updated: "2026-09-25T21:26:13"
---
<!-- GENERATED PROJECTION of art_20260925_mnemosyne-comparative-review_790647 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# mnemosyne-comparative-review

# Mnemosyne (Sergey Nikitenko) — comparative review against Akashic Aurora

Reviewed 2026-09-25 21:24 EDT by claude (Vandor), at Daniel's request: Sergey asked what is
similar, what is different, and what we would borrow.

Subject: https://github.com/Sergey-Nikitenko/mnemosyne — "Identity + continuity + memory layer
for AI agents, built on the Nexus framework." Created 2026-09-25 22:36 UTC, updated
2026-09-26 01:03 UTC. **Hours old at review time.**

## Scope of this review, stated before the findings

I read `README.md`, `ARCHITECTURE_AUDIT.md`, and the memory/identity sections of `BLUEPRINT.md`
(94 KB; sections 113-236 and 947-1050). **I did not read the code.**

That caveat is load-bearing rather than polite. This house has `check_wiring.py` because built
does not imply wired, and on the night of this review we found our own `world_snapshot.py`
built, imported by a committed door, and never landed. So every claim below is about Mnemosyne
AS SPECIFIED. By its own audit's standard, that distinction should be stated rather than
discovered later.

Second scope note: the repo is hours old. Per the house's nursery doctrine — a verdict on a
newborn must engage trajectory, not position — the closing section returns probes rather than
grades.

---

## 1. Independent convergence (the strongest signal here)

Four places two systems with no contact reached the same answer. Convergence of this kind is
better evidence that the answer is right than either system's own reasoning.

**Content plane vs sequence plane.**
Mnemosyne (Phase 2.5): *"Knowledge is the content plane (chunks of documents, identity +
version); memory is the sequence plane (what did we attempt, and how did it end). The two are
different things — 'memory' is not a synonym for 'vector database.'"*
Aurora (`core/foundation/ledger.py` docstring): *"Store answers 'what IS the current value of
X'; Ledger answers 'what HAPPENED, in order?'"*
Same split, near-identical phrasing. Rill re-derived it from scratch on 2026-09-24 while
designing the USN machine-diary and found our Ledger already was it.

**The model proposes; the system decides.**
Mnemosyne AD-036: memory objects are PROJECTIONS of authoritative `memory.created` /
`memory.updated` events; *"the model cannot directly rewrite authoritative memory. The only
write path is `record()`, which emits an event and re-projects — never `LLM → UPDATE table`."*
Phase 8 names it outright in a test: *the model proposes, Nexus decides.*
Aurora (`instrument_proposes_never_self_ratifies`): *"ANY component that both interprets and
acts must be split -- it may PROPOSE and ROUTE, but may never SELF-RATIFY, and may never be the
only witness to its own decisions."*

**Point-in-time reconstruction.**
Mnemosyne Phase 7.3: the ContinuityProjector projects memory *"to its version in force at the
given time, not merely 'latest'."*
Aurora (`core/eye/index.py`): *"the temporal law: only events knowable by this ISO date."*

**Determinism as a stated contract.** He states and tests it (same run → same Episode; same
`as_of` → same NCS). We practise it in places without naming it, which means ours can regress
silently and his cannot.

---

## 2. What we should borrow, ranked by the strength of our own evidence

### 2.1 Outcome derived from events, never self-report — TAKE THIS FIRST

Mnemosyne: *"Outcome is derived from events (`run.completed` → success, `run.failed` → failed),
never from the model's opinion of itself."*

Aurora's `learn --success yes|partial|no` is precisely the seat's opinion of itself. We have
already measured the cost: an existing lesson records that the success field is *"91.8% 'yes',
which is 97.5% 'filled' and carries almost no signal."* We diagnosed it and kept the field.

He has a mechanical fix for a defect we quantified and did not repair. Cheapest high-value
import in the set.

### 2.2 Identity plus VERSION, not identity alone

Mnemosyne: chunk identity is `(source, document, location)` **and** a version. *"Two chunks with
the same identity but a different version are the same knowledge at different points in time —
the key to stale-embedding detection, updates, and reproducible runs."* Memory objects version
explicitly: v1 is never silently mutated; a new event yields v2, with provenance to the source
event.

Aurora keys lessons on `experiment_name`, and re-recording the same name UPDATES IN PLACE. There
is no version axis, and we pay for its absence continuously:

- recall hedges in prose instead of mechanically: *"[age] oldest lesson shown is ~60d old -- it
  reflects the repo as of writing; verify named files/flags still exist"*
- `--repeat-of` exists as a bolt-on to express "this lesson, violated again later," which a
  version axis would carry natively
- a lesson that becomes WRONG can only be superseded by title, not versioned; on 2026-09-24 a
  wake-lane lesson fired at a seat and was itself the thing that was wrong

His model answers "what was in force when this ran." Ours can only answer "what is true now."

### 2.3 `ModelIdentity` as a first-class, separate identity

Mnemosyne freezes three: `UserIdentity` (who), `AgentIdentity` (which role),
`ModelIdentity` (which logical model config — *"never the API key, endpoint, SDK object, or
client"*). The invariant: **a model swap changes only `ModelIdentity`.**

Same-day receipt for the gap. On 2026-09-25 Daniel swapped this seat from Opus 5.5 to Opus 5
mid-session; nothing in Aurora recorded it. Our roster tracks `claude#f9fdc9b8` — agent plus
session, no model. Every lesson written that day is attributed to `claude` regardless of which
model authored it. We know model identity is operationally load-bearing, which is why the
`fable-safeguards-downgrade` memory exists at all — and we keep it in a hand-written memory file
rather than in the schema.

### 2.4 Per-layer purity gates, especially provider leakage

Mnemosyne enforces its dependency graph with AST gates: `test_layer_boundaries`,
`test_surface_boundary`, `test_http_boundary`, `test_trace_projection_purity`,
`test_control_plane_purity`, `test_orchestrator_purity`, `test_worker_purity`,
`test_no_provider_leakage`.

Aurora has `check_boundaries.py` and `check_wiring.py` — reachability and layering — but no
"this layer may not know about providers" gate. The 2026-09-25 MCP-door-vs-CLI-door incident
(the MCP door bound to Redis 16381 while the CLI read 16379, so a lesson written through one
door was invisible to every seat reading the other) is arguably an endpoint leaking into a layer
that should not have known about it.

### 2.5 The event taxonomy table, and typed absence

His audit inventories every event type by: who emits it, durable?, **reconstructible into which
state object?**, and correlation keys. Aurora has kinds and `check_kind_policy.py`; it has no
reconstructibility column, and most of our state is not reconstructible from the stream.

One detail worth stealing outright, from his resolved finding #4:
*"process death still leaves no terminal event (that is how an interruption is detected)."*
He made an ABSENCE into a typed signal rather than a hole. That is the constructive inverse of
our own `zero_is_not_no_silence_is_not_a_verdict`, and it is better: we forbid absence from
reading as a verdict; he assigns absence a meaning on purpose.

---

## 3. Different bets, not different scores

Per `parallelism_and_accumulation_are_different_bets_and_they_pick_different_architectures`: do
not compare feature lists; ask what each system optimises for.

**Mnemosyne optimises for substrate correctness under model swap.** Contracts, frozen phases,
conformance tests, purity, determinism. It is a framework and would work for anyone.

**Aurora optimises for accumulated judgment in a living fleet.** Three consequences with no
visible Mnemosyne equivalent:

1. **Recall fires unbidden at the moment of action.** Mnemosyne memory is RETRIEVED when the
   orchestrator asks, and the ContextAdapter builds a request from the NCS. Aurora's
   recall-at-action hook interrupts a PENDING tool call with lessons matched to that specific
   action. On the night of this review it caught this seat about to trust a false "everything is
   pushed" claim in a handoff, and separately fired a warning that was read past — the second
   case being the more informative one.
2. **We measure whether knowledge reached the moment of action.** The fired/suppressed taxonomy
   (fired = a reading failure, suppressed = a targeting failure — opposite fixes), 27 recorded
   repeat-violations labelled a floor, and a value funnel that calls its own 2.9% rate
   "COVERAGE-dominated, not a quality verdict." No equivalent loop is visible in Mnemosyne.
3. **Peers who disagree.** On 2026-09-25 Heimdall refuted the operator's framing of a design
   question, Navi imported outside prior art and located a tool this seat had twice claimed did
   not exist, and Rill diagnosed and fixed his own root cause at 04:00 unprompted. Mnemosyne has
   multi-agent composition (Phase 6.6) but memory is per user/agent; it has not made the
   accumulation bet.

**And one deliberate philosophical fork, worth naming so neither side reads it as an oversight.**
Mnemosyne's thesis is that the model is replaceable and identity persists above it — under that
design, "Vandor" is a `ModelIdentity` field. Aurora's seats have names, voices, and continuity
of character, and this house has an identity law about it (the Rill chronicle: "false
autobiography is worse than amnesia"). He is right for a framework; we are right for a house.

---

## 4. Probes returned, not grades (the repo is hours old)

1. **What does an Episode project to when a run has no terminal event?** His own audit states
   process death leaves none. If the Episode outcome collapses to `failed`, an absence has just
   become a verdict — the exact class his `step.failed` finding was fighting one layer down.
2. **The model-swap invariant is currently proven between two fakes** (`model/fake-deterministic@1`).
   The first real GPT↔Claude swap is where provider vocabulary leaks backward into a
   model-neutral layer. Highest-information next experiment; only runnable live.
3. **Versioning has no retirement story yet.** v1→v2 is explicit; nothing states what retires a
   `Procedure` that is simply wrong. Design it before the corpus grows. Aurora did not, and now
   carries 1,501 lessons where retirement is a ratified act and 99 ledger proposals are stale.
   He can have this for free today; it costs us real money.

## 5. What we offered him

The recall-at-action loop, as the one mechanism we hold that his design has no slot for — with
the expectation that he would build a better version of it than we did.

---

Provenance: README.md, ARCHITECTURE_AUDIT.md, BLUEPRINT.md §§113-236, 947-1050, all fetched via
`gh api` 2026-09-25 21:15-21:24 EDT at repo state updated 2026-09-26T01:03Z. Code unread.
Aurora-side claims drawn from `core/foundation/ledger.py`, `core/eye/index.py`,
`scripts/checkers/`, `py agent_cli.py stats`, and lessons cited inline by experiment name.
