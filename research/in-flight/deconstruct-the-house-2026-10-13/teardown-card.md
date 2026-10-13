# The teardown card (draft v1, 2026-10-13)

Daniel, 2026-10-13: "how do we expand reverse engineer into 'deconstruct and break down into first principles, required
steps and capibilities and verification' I want us to be able to reverse engineer and deconstruct anything, from
websites and api's to financial models to principles in the world." Then: "I love your deconstruct the house, yes!"
He saw Rimuru's Great Sage in it ("raphael deconstructing skills and upgrading them"), so the card speaks in Great
Sage's report voice: the voice is play, the substance underneath is strict.

## The eight rows (every teardown fills all eight; "unknown" is a valid, honest entry)

| row | question | example from a chip teardown |
|---|---|---|
| 1 Purpose | What is it for, and for whom? What outcome would make it worth keeping? | the market and workload it targets |
| 2 Observables | What can we see and measure from outside, without trusting its own description of itself? | the die shot, benchmarks |
| 3 Mechanism | How does it turn inputs into what we observe? | the microarchitecture |
| 4 First principles | The irreducible truths and constraints it rests on (laws, identities, protocols, incentives, the operator's values). Test each: can you name the evidence or law it rests on? If not, it is an assumption dressed as an axiom. | physics, the process node, Amdahl |
| 5 Capabilities | What would we need to HAVE to build or run it (skills, tools, data, access, money, time)? | the fab, the IP, the talent |
| 6 Required steps | In what order would we build it from nothing; what blocks what (the critical path)? | tape-out order |
| 7 Invariants and failure modes | What must always hold? How does it break, and what does a break look like from outside? | thermals, yield |
| 8 Verification | Predictions that COULD FAIL, each with the cheapest test that would show it. Run the cheap ones. | validation silicon |

Loop altitude (from docs/pillar-analysis-method.md): for anything with a value chain, name every link and ask whether
the signal flows back. A designed-open loop (measurement without actuation) is the most common real finding.

## Labels (on every claim)

- **observed**: you saw it in code, data, telemetry or a run, with a pointer (file:line, a command and its output, a
  receipt path, a commit).
- **inferred**: you reasoned it from observations; say from which.
- **unknown**: you did not look, could not look, or the evidence conflicts; say which, and where you stopped (the search
  boundary). A bounded negative stays bounded: "not found in X" never becomes "absent".

## The report voice (Great Sage)

Each subsystem's card closes with a short report in this shape. The words map one-to-one onto the labels, so the voice
cannot drift from the evidence:

> **Notice.** (observed facts, with pointers)
> **Analysis.** (inferences, each naming the observations it rests on)
> **Unknown.** (what we did not or could not see, and the search boundary)
> **Proposal.** (what to change, smallest first; a deletion is never proposed without the reason the part exists)
> **Verification.** (the predictions that could have failed, and whether they did)
> **Proceed?** YES / NO (the operator's gate: every proposal waits for Daniel)

## The traps (name them when you see them)

1. False first principles: assumptions dressed as axioms.
2. Chesterton's fence: never propose removing a part before stating why it exists.
3. Reductionism: some behaviour lives in the loop, not the parts.
4. The map is not the territory: only a prediction that could fail closes the gap.
5. Goodhart: verifying the metric instead of the thing.
