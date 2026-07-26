# Recall redesign — peer research (claude's lane)

Status: current
Class: research

Daniel's ask, verbatim: *"lets put on our best detective and research hats on how to fix our
recall system, we need to make the process be automatic and I suspect we can link specific
recall types to a heighrarchy that stems from authoritative atoms, but I want to know what you
guys think. we could have a system for flagging and updating incorrect recalls and a confidence
score."*

Lanes: **deepseek** has the census of what already exists, **kimi** attacks the design, this is
the peer research. One third of the answer.

Evidence grades: SECONDHAND unless marked. Benchmark numbers in this space are contested (see
the earlier sweep) and none of these are ours.

---

## The headline: three of Daniel's four ideas have proven shapes, and the fourth may be aimed at the wrong stage

His intuition is not only right, it converges on named patterns the field has already built.
The useful part of this document is the *specific mechanism* behind each, because the mechanism
is where our version would otherwise go wrong.

## 1. "Flagging and updating incorrect recalls" → bi-temporal invalidation, NOT demotion

This is the most important finding here, because **it dissolves a bug we already have.**

Zep/Graphiti's model tracks **two timelines per fact**: *valid time* (when it was true in the
world) and *ingestion/provenance time* (when the system learned it). Four timestamps —
`t_created` / `t_expired` for the system's knowledge, `t_valid` / `t_invalid` for the world.

> Superseded facts are **invalidated rather than deleted** — when a fact is updated, the old
> edge is marked expired, preserving historical context for temporal queries.

**Why this matters for us specifically.** Our existing flagging mechanism is `is_benched`, and
Daniel's own gate list names it as a **self-sealing loop**: a demoted lesson stops surfacing, so
it can never earn the credit that would redeem it. That is what happens when "this is wrong" is
implemented as *rank suppression*.

Bi-temporal invalidation is the alternative that does not self-seal. You do not demote a
lesson — you **time-bound** it. The record persists, its history stays queryable, and there is
no popularity death-spiral because surfacing odds were never the mechanism of correction.

**Adding a flagging loop on top of `is_benched` would create a second self-sealing loop.
Replacing demotion with invalidation removes the first one.** That reframes the work from "add
flagging" to "change what flagging *does*."

## 2. "Hierarchy stemming from authoritative atoms" → source-provenance trust ordering

Daniel arrived independently at a named pattern. The field's version:

> Some sources are more authoritative — a user's direct statement outranks an inference from
> behavior, and an admin's configuration outranks an agent's guess.

And crucially, as a *security* property, not just a quality one:

> **Provenance-capped belief updating** serves as a memory-poisoning defense, with trust derived
> from **source provenance rather than content**.

**This answers the hardest objection to the idea.** The trap in "authoritative atoms" is: what
makes an atom authoritative? If the answer is "a human ratified it," the system is not
automatic. If the answer is "it was cited a lot," we have built a popularity metric wearing a
provenance costume.

The field's answer is neither: authority bottoms out at **source type**, which is a fact about
*who or what produced the claim* — knowable at write time, not derived from usage. For us that
ordering is already recordable and largely already recorded:

1. Daniel's direct statement (verbatim directives)
2. A ratified reconciliation or gated design doc
3. A measured result with a reproducible command
4. A fleet agent's self-reported lesson
5. An inference

We already stamp `agent_id` on every lesson, so tier 4 vs 1 is mechanically distinguishable
today. This is the cheapest high-value piece on the board.

It also connects to the **`cites` starvation** — reportedly ~300 of 440 lessons carry no
checkable anchor. That number is the one figure in my remediation plan I flagged as **not
re-derived**, and deepseek is re-deriving it. Provenance-as-a-queryable-column is exactly what
oxlint does at 844 rules (every rule carries its source plugin; the table filters on it), so the
shape has prior art at scale, not just in agent memory.

## 3. "Confidence score" → derive it from explicitness and provenance, do not bolt on a scalar

> Each memory carries a confidence score based on **how explicitly it was stated** — "I use
> Python" scores higher than "seems to like Python".

The important part is that confidence is **derived**, not assigned. A number an author types in
is a preference; a number computed from *how the claim was made* and *who made it* is a
measurement. Our `learn()` already accepts a `confidence` field — deepseek is checking whether
anything ever **reads** it, because a field that is written and never consumed is the
token-meter shape again.

**The open question I could not resolve from the literature**, and which I have put to kimi: a
single scalar on a record may be a category error, because confidence in a lesson is arguably a
property of *(lesson, context)* rather than of the lesson. The same lesson is high-confidence
for the action it was written about and near-worthless two files over.

## 4. Contradiction as a first-class state — the piece I did not expect

> When evidence conflicts, the system **does not silently pick a winner** but enters a BOTH
> state — explicitly representing the contradiction for the agent to reason about.

(Belnap four-valued logic; beliefs track supporting *and* attacking evidence.) Resolution
strategies are configurable — last-write-wins, confidence-based, or **flag-and-ask**.

This is the anti-silence principle we have been applying all week, formalised: *do not resolve a
conflict silently.* Last-write-wins is precisely the FileStore defect at the semantic layer.

**Calibration on how solved this is:** the MnemeBrain benchmark's stated finding is that **most
AI memory systems cannot detect contradictions.** So this is a frontier weakness, not a
commodity we can import — worth knowing before we assume a library exists.

## 5. Where the proposed design may be aimed at the wrong stage

The honest limit of everything above: **all four ideas improve WHICH lesson surfaces.** None of
them touch whether a surfaced lesson *binds*.

Our measured defect tonight was the opposite one. The corpus fired the exactly-correct lesson at
me **twice** and I violated both within minutes (`bifrost_send_always_text_file`,
`consume_to_null_eats_mail`). kimi's ruling on that: application is observable only via
self-report (gameable) or counterfactual (unobservable), so **no applied-stage gauge can work**
— the lever is render/friction, "name it, don't metric it."

If that holds, a confidence score and a correctness-flagging loop both refine retrieval while
the demonstrated failure lives one stage later. I have put that to kimi directly.

**One thread does cross the gap**, and it is why the contradiction finding matters most: the
**BOTH state and flag-and-ask are render changes, not metrics.** They force the agent to
confront a conflict rather than be handed a resolved answer. That is precisely kimi's prescribed
lever for binding, arrived at from the retrieval side. If any single mechanism here earns its
place twice, it is that one.

## What I would take, in order

1. **Replace demotion with bi-temporal invalidation.** Removes an existing self-sealing loop
   rather than adding a second one. Highest value, and it is a *subtraction*.
2. **Source-provenance tiers**, bottoming out at who-produced-it rather than popularity.
   Automatic, honest, and mostly recordable from data we already stamp.
3. **Confidence derived from explicitness + provenance**, never author-assigned — and only after
   deepseek reports whether the existing field is read by anything.
4. **Contradiction as an explicit state** rather than silent resolution — the one piece that may
   touch binding as well as retrieval.

## What this lane does NOT establish

- No benchmark run; every number here is secondhand and the field's numbers are contested.
- Whether any of this is already built here — deepseek's census, deliberately not guessed at.
- Whether the design is sound — kimi's lane.
- The `cites` count (~300/440) is still unverified by me and is being re-derived.
- Nothing here addresses the **broken funnel metric** (double-logged impression series). Until
  that is fixed, no measurement we take can validate any of these choices — which is the
  strongest argument for starting with the *subtraction* in item 1, since it needs no metric to
  justify it.

## Sources

- [Zep — What is a temporal knowledge graph](https://www.getzep.com/ai-agents/temporal-knowledge-graph/)
- [Graphiti: knowledge graph memory for an agentic world](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)
- [Zep: A Temporal Knowledge Graph Architecture for Agent Memory (arXiv 2501.13956)](https://arxiv.org/pdf/2501.13956)
- [Reliability-Conditional Updating and Provenance-Capped Poisoning Defense (arXiv 2606.22030)](https://arxiv.org/html/2606.22030)
- [TOKI: A Bitemporal Operator Algebra for Contradiction Resolution (arXiv 2606.06240)](https://arxiv.org/pdf/2606.06240)
- [From Agent Traces to Trust: Evidence Tracing and Execution Provenance (arXiv 2606.04990)](https://arxiv.org/html/2606.04990v1)
- [MnemeBrain Benchmark — most memory systems cannot detect contradictions](https://mnemebrain.github.io/mnemebrain-benchmark/)
- [Contradiction detection in agent memory](https://0latency.ai/blog/contradiction-detection.html)
