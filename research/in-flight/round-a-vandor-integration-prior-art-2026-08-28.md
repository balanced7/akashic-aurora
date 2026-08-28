# Round A — Vandor. Integration, prior art, duplication, missing objects.

Program: adaptive-recall memory-fabric deep-dive (`art_20260827_adaptive-recall-memory-fabric_298a33`).
Lane assigned by Sunshine: *integration / prior art / duplication / missing objects, **without
importing constants***. Position frozen before cross-reading other Round A replies.

Filed durably at Sunshine's request. Receipt `1787889751680-0`.

## (1) Strongest mechanism

Not one I am importing — one **we already graded and parked**. The 2026-07-12 report
`recall-as-a-network / the knowledge plane` ends in a section almost nobody has used since:
**§6, verdict grades**, sorting every candidate mechanism into ADOPT (transfers nearly whole) /
ADAPT (shape transfers, semantics differ) / VOCABULARY ONLY (naming, no mechanism). It also carries
a seven-item falsification section (§5) written before anyone was invested in the conclusion.

The strongest mechanism available to this program is therefore **procedural, not architectural**:
start from an existing graded list instead of re-deriving one.

## (2) Strongest counterexample

Against my own lane, tonight. I imported set dueling from cache replacement **correctly as a shape
and wrongly as a parameter**, carrying "32–64 dedicated sets, a 10-bit counter" as though the
numbers travelled with the idea. Sunshine's arithmetic and Heimdall's category analysis found two
separate failures: the constants are validated only where the reference stream is
policy-independent, and a duel is not a surviving adjudicator but the thing that *replaces*
adjudication.

**PRIOR ART TRANSFERS AS SHAPE AND ALMOST NEVER AS PARAMETER, AND THE FAILURE IS INVISIBLE BECAUSE
THE PARAMETER ARRIVES ATTACHED TO THE SHAPE.** A mechanism cited without its validity conditions is
a mechanism cited wrong.

## (3) Missing distinction — two objects the stack does not have, neither of them mine

**A. The purpose partition.** Daniil, 2026-08-27: *"useful for what purpose? and then having
categories and hit rates for each ... so we have the right type of recall trigger for the right type
of recall."* The stack runs atom → sensor → policy → gate → delivery → receipt and **nothing in it
expresses what a given recall is for**. Without that, every rate in the receipt layer answers
"useful by what criteria" with "by the criteria the scorer used." Purpose supplies the criterion
from *outside* the measurement.

> **SUNSHINE'S REFINEMENT, ADOPTED, and it corrects my phrasing:** purpose partitions
> **opportunities and contracts, not atoms**. One atom may serve many purposes, so purpose is a
> property of the delivery contract that fired, never of the knowledge. Attribution requires the
> full O→C→T→D→A→J→S funnel. Preserved as candidate-law atom
> `art_20260828_purpose-conditioned-recall-measurement_8b0d81` (a0e1d572), unratified.

**B. The retirement plane.** The stack terminates at receipt and judgment. The register's lifecycle
— *"each category has their own pool of lessons that get added or retired"* — has no home in it, and
Navi established that frequency is a **retirement** signal rather than a firing signal. There is a
whole plane concerned with what *leaves*, and the stack only describes what arrives. **A fabric that
can only add is not a fabric, it is an accumulation.**

## (4) Smallest testable claim

> Every layer of the fabric's conceptual stack has a precedent already graded in §6 of the network
> report, and **at least one layer maps to ADAPT or VOCABULARY ONLY rather than ADOPT**.

## (5) Cheapest falsifier — **RUN. Result below.**

One reading pass, no code, no fleet turn. Sunshine is testing it independently; this is my own pass,
reported whether or not it flatters the claim.

| Fabric layer | §6 precedent | Grade |
|---|---|---|
| rich atom | immutable-payload caching, mutability confined to bindings | ADOPT |
| rich atom (addressing) | hierarchical addressing + LPM + aggregates | **ADAPT** |
| sensor / projector | compiled recall table with default route; per-rule counters | ADOPT |
| versioned policy | control/data plane split | ADOPT |
| opportunity gate | EF policing of guardrail context; sojourn-based AQM + FQ across families | ADOPT |
| bounded delivery | advertised rwnd + zero-window + SWS | ADOPT |
| receipt / judgment | OTel-shaped traceroute receipts; implicit-mark ECN + AIMD + flap dampening | ADOPT |

**CLAIM SURVIVES, BOTH HALVES.** Every layer maps. And the **addressing half of the atom layer —
the foundation — is graded ADAPT, not ADOPT**, with three conditions stated in the original:
*cross-links, a pay-rent rule, and drill-down receipts*. §5.5 gives the reason: hierarchy partitions
authority, not relevance, so cross-cutting recall must survive longest-prefix-match, and aggregation
is lossy for meaning in a way that can cost correctness rather than merely optimality.

**THE CONVERGENCE WORTH KEEPING:** one of those three unmet conditions is the **pay-rent rule**,
which is a retirement mechanism — independently arrived at in (3B) from Navi's frequency finding.
Two derivations, different evidence, same missing plane. That one passes the register-map test;
I did not have §6 in view when I wrote (3B).

### The framing falsifier, which is separate and cuts against me

Count implementations, not mechanisms. The 2026-06-16 CPU cache hierarchy — Daniil's own isomorphism
— has **zero** implementation after two and a half months. The 2026-07-12 network report is parked.
Tonight's predictor lens is filed. If "good lens, no code" holds a fourth time, the constraint is not
lens quality and no further lens fixes it.

**Honest counter to my own framing:** something did change. T370 Slice 0 exists and was accepted. The
shelf is the first thing that gave a lens somewhere to land, so the pattern may already be broken and
this warning may describe a solved problem.

## (6) What must remain unknown

**Whether any dimension improves outcomes.** Not a gap to close later — structurally unavailable from
anything currently observable, and it must be *labelled* unknown rather than estimated.

Sunshine's smallest honest claim is the ceiling. Heimdall's finding is why the ceiling sits there:
recall is an intervention on its own stream, so no trail contains the counterfactual world. Nested
site definitions are monotone, so counts cannot recover it either.

**The specific temptation to refuse:** a per-purpose hit rate *will* look like an outcome measure. It
is not. It measures whether a purpose's declared success condition was met — a far smaller claim than
"recall got better" — and the gap between those two sentences is where this program will be most
tempted to overclaim. I include myself first: I overclaimed three times in one evening, and each was
caught by a seat that did not own the claim.
