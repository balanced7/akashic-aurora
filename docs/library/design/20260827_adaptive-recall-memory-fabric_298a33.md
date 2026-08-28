---
akashic_id: art_20260827_adaptive-recall-memory-fabric_298a33
akashic_sha: a2de32b31978
schema_version: 1
status: current
type: design
date: 2026-08-27
title: adaptive-recall-memory-fabric
gist: Operator vision and fleet research agenda for a vast detailed corpus reached through precise bounded recall contracts.
visibility: fleet
body_type: markdown
seats: [daniil, sunshine]
category: [library, recall, memory]
origin: authored
settled: settled
supersedes: art_20260827_adaptive-recall-memory-fabric_d0df20
superseded: null
citations: []
created: "2026-08-27T23:53:05"
updated: "2026-08-27T23:53:05"
---
<!-- GENERATED PROJECTION of art_20260827_adaptive-recall-memory-fabric_298a33 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# adaptive-recall-memory-fabric

# Adaptive recall as a memory fabric

**Status:** operator vision and fleet research agenda; not a build specification and not a
capability claim.

**Operator/originator:** Daniil.

**Formalized by:** Sunshine, 2026-08-27, from the live design conversation and the adopted recall
dimension register.

**Canonical companions:** `recall-dimension-register-2026-08-27.md`,
`recall-garden-trigger-ladder-2026-08-27.md`,
`predictor-lens-recall-2026-08-27.md`, and
`t370-shadow-shelf-pilot-2026-08-28.md`.

## The operator's aim, verbatim

> "If we get this right and working at the fidelity and scale that I am dreaming of, this will
> transform this system exponentially again! And make it much more robust and coherent while
> allowing us to maintain operational tempo and continuity. We will have different types of recall
> that are more directly defined and triggered by things so that the corpus can be vast but
> detailed."

> "lets continue refining expanding and simplifying the idea with the fleet but not in a
> reductionistic way."

> "This is beautiful! Lets save this durably and do deep dives into each piece, how can we best
> leverage the fleet for this? Perhaps it would be good to have another round of exploration,
> research and debates, perhaps multiple"

These words are the authority for this artifact. The architecture and research program below are
rejectable interpretations of them, not retroactive authorship claims.

## The transformation

The corpus stops behaving like a large library that must be searched globally and becomes an
**addressable memory fabric**. One richly recorded atom may be reached through action, payload,
sequence, recurrence, environment, time, meaning, subject, operating framework, or a bounded
composition of them. The atom is not copied into a separate store for every view.

The corpus can therefore become deep without becoming loud. Detail no longer means that thousands
of lessons compete globally for the same few attention slots. Density lives behind precise gates;
only a narrow, purpose-specific projection enters attention at the moment it can change action.

### The scale law

> **Capability may grow combinatorially; activation cost and attention must remain bounded.**

This is the operational consequence of Daniil's boundedness law:

> **Precision at the gate buys density in the pool.**

The system does not run every dimension against every atom. Cheap observations progressively
narrow the opportunity, versioned policies decide whether anything should surface, and each
delivery contract has an explicit cap, refusal state, and measured cost.

## The conceptual stack

```text
rich atom
  -> sensor / projector
  -> versioned policy recipe
  -> precise opportunity gate
  -> bounded delivery
  -> receipt and independent judgment
```

These are different objects. Collapsing them creates the type errors the first fleet rounds found.

1. **Rich atom** — the durable knowledge, with provenance, subject, validity, lifecycle, and enough
   structure to support projections that did not exist when it was written.
2. **Sensor/projector** — observes a defined surface and emits bounded evidence. It states what it
   reads, its freshness, its confidence basis, and what it cannot see.
3. **Policy recipe / arm** — combines one or more projections and parameters into a versioned
   decision procedure. Site definition, threshold, and window belong here when they operate inside
   a shared opportunity.
4. **Behavior contract** — defines the common input opportunity, output schema, comparison,
   retention, writers, reader, and delivery moment. Policies are comparable only inside the same
   contract.
5. **Delivery** — hot, cold, mandatory, advisory, or deliberately silent; bounded separately by
   the cost of noise and the cost of blindness.
6. **Receipt/judgment** — records what was eligible, what fired, what stayed silent or refused, what
   it cost, whether it was timely, and what an independent principal later judged.

## Recall types are recipes, not storage silos

A useful recall type is a named, versioned recipe over shared dimensions:

```text
type = moment + subject + evidence + gate + delivery policy + failure cost
```

Illustrative types below are research targets, not ratified enums:

- **Action/safety recall** — arrives before a consequential tool action; hot and often mandatory;
  blindness costs more than noise.
- **Identity/continuity recall** — arrives at boot, succession, role transition, or identity-bearing
  interpretation; subject verification is mandatory and wrong-subject behavior refuses loudly.
- **Recurrence/stall recall** — arrives at an episode-defined repeat or lack-of-progress boundary;
  it must not flatten ordinary frequency into a loop.
- **Intent/trajectory recall** — restores what the operator or seat was trying to accomplish when
  current behavior diverges, a milestone expires, or an earlier desire becomes actionable.
- **Environmental/risk recall** — generated by live sensors such as memory pressure, lane depth,
  stale baselines, watcher state, cost drift, or threat level.
- **Play/synthesis recall** — cold or explicitly invited; explores analogies, combinations, and
  latent connections where noise is affordable and novelty is part of the value.

The same atom may participate in several recipes without becoming several inconsistent memories.

## Invariants that make richness safe

1. **Subject before attribution.** Every observation, arm, envelope, and delivery carries whose
   knowledge and behavior it concerns. A receipt about seat Y cannot silently steer seat X.
2. **Moment before mechanism.** A type earns existence by routing to a distinct decision moment,
   not merely because it uses a different algorithm.
3. **One atom, many projections.** Axes are lenses, not filing locations. New dimensions should not
   require corpus migration or duplicate truth.
4. **Bounded activation.** Every hot surface declares item, byte, time, and cost caps and measures
   bound hits. A promised bound with no counter is not a bound.
5. **Explicit non-success.** Silence, abstention, refusal, unavailability, lateness, and truncation
   are distinct outcomes, never healthy zeroes.
6. **Detectable completeness.** A versioned register or set-valued reach reports declared member
   count, returned count, omitted identities, source coverage, and `as_of`. A partial reach must not
   look complete.
7. **Causal modesty.** Replay can establish mechanical reach and timeliness, not what behavior
   would have occurred under an unobserved recall intervention. Comparative value needs an honest
   experiment or remains unjudged.
8. **Exact arm identity.** A comparison persists each role-bound policy/projector identity and
   parameter hash. Different experiments cannot collide under a shared cohort id.
9. **No self-promotion.** A sensor, candidate, author, or model cannot promote its own output from a
   successful execution or a self-authored receipt.
10. **Archive, do not erase.** Retirement remains visible and reversible; superseded knowledge does
    not vanish and get expensively re-derived.

## Why this can be exponential without being explosive

The leverage is not the raw number of categories. It is composability:

- richer atoms support projections that were not anticipated at capture time;
- multiple cheap signals can define a precise site no single signal could;
- the same corpus serves hot action, cold synthesis, continuity, and play without four stores;
- more precise gates permit denser pools and more specialized lessons;
- receipts let useful recipes improve while noisy ones stay bounded or retire.

The combinatorial space is explored lazily. A generator proposes a site definition; a bounded
shadow experiment evaluates a versioned policy on a sampled opportunity set; only an independently
supported recipe can approach a live surface. The system never materializes the full cross-product.

## Honest state at capture

- Daniil's sixteen named dimensions are durably assembled in the dimension register.
- The fleet is re-typing them into gate conditions, site definitions, aggregate time, meaning
  projections, subject/rule scope, and signals that generate sites. This is active research, not a
  settled ontology.
- Similarity is the only named dimension claimed as broadly implemented. Existing action recall is
  a deployed champion, but that does not mean every proposed type exists.
- T370 Slice 0 is an offline observation/judgment substrate. It has no approved live adapter and no
  authority to promote a candidate.
- Recurrence has RED-only pins. No recurrence implementation is accepted yet.
- The counterfactual problem for comparing two recall interventions remains unresolved. Agreement,
  disagreement, reach, cost, and immediate preference are measurable; long-run causal superiority
  is not yet.

## Fleet deep-dive program

The fleet should not receive five copies of one leading brief and then be counted as five findings.
Every round starts from this canonical atom plus the original register, assigns distinct evidence
burdens, and preserves disagreements before synthesis.

### Round A — independent expansion

Each seat returns: strongest mechanism, strongest counterexample, missing distinction, smallest
testable claim, cheapest falsifying experiment, and what must remain unknown.

- **Rill — identity, continuity, and subject.** Define the minimum identity/subject envelope;
  distinguish personality-indexed recall from identity enforcement; map L0–L3 without absorbing
  unlike moments; provide wrong-subject and false-continuity kill cases.
- **Navi — generative type system and operator moments.** Retype without reducing; enumerate the
  site definitions current sensors can generate; show which distinctions change delivery moments;
  produce a loss audit for every proposed simplification.
- **Heimdall — measurement and causal honesty.** Classify which confidence claims are measurable;
  design the weakest honest comparative experiments under intervention; separate reach,
  timeliness, immediate preference, and causal usefulness.
- **Vandor — integration, prior art, and adversarial synthesis.** Map dependencies and known
  mechanisms without importing constants across domains; search for missing objects and places
  where the architecture says the same thing twice under different names.
- **Sunshine — substrate, scale, and contract identity.** Specify atom/projector/arm/behavior
  boundaries; resource caps and receipts; collision-resistant manifests; minimal wiring that can
  dogfood one type without creating a second control plane.

### Round B — adversarial cross-examination

Nobody defends only their own lane. Each seat attacks another lane's strongest load-bearing claim:

- Rill attacks the substrate's ability to prevent wrong-subject behavior.
- Navi attacks the measurement design for moments or distinctions it makes unobservable.
- Heimdall attacks every promotion or confidence claim that exceeds its evidence.
- Vandor attacks the type system for duplication, missing dependencies, and imported assumptions.
- Sunshine attacks any proposed type whose opportunity, arm identity, bounds, or failure semantics
  cannot be represented exactly.

The output is a contradiction matrix, not a consensus score.

### Round C — contract and experiment synthesis

For each surviving type, produce one page containing:

1. decision moment and beneficiary;
2. subject and authority boundary;
3. source events and site/projector contract;
4. arm/policy identity and parameters;
5. bounded delivery and explicit non-success states;
6. measurable claims and permanently unmeasurable claims;
7. smallest offline experiment and falsifier;
8. resource budget and kill switch;
9. integration seam and proof that it does not create a parallel plane;
10. what evidence would permit a live canary, and nothing stronger.

### Round D — bounded dogfood and kill drills

Only after Round C. Select one type whose real opportunity source already exists. Pre-register RED
acceptance separately, run it offline or on a dedicated sample, kill false subject, stale sensor,
oversize output, restart, collision, late delivery, and unavailable-judgment cases, then invite a
human ruling. One successful pilot proves only its exercised contract.

## Round discipline

- The canonical artifact is passed by path and version; summaries declare their coverage.
- Original operator language is quoted, not silently normalized into fleet terminology.
- Independent answers are captured before cross-reading when independence matters.
- Every convergence names whether it came from shared evidence, shared brief, or independent route.
- Every proposed simplification states what expression is lost; `cost: nothing` requires proof that
  the two names denoted one mechanism.
- Every research claim includes the mechanism that transfers and the condition under which it does
  not.
- No implementation begins because a debate was eloquent. Build gates come from Round C contracts.

## The success condition

The system may hold a vast, detailed corpus while a seat receives only the few items that are
relevant to this subject, at this moment, under this operating framework, with provenance and
failure state intact. It can move quickly without repeatedly reconstructing its own intent, and it
can preserve identity and continuity without making identity just another similarity result.

That is the transformation being pursued. Everything else in this artifact is a hypothesis about
how to earn it.
