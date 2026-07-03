# Principles — the ideas that explain why the software is shaped this way

> Not architecture, not implementation — the working principles underneath both. Each
> one was *earned* by at least one documented episode ([JOURNEY.md](JOURNEY.md) tells
> the stories; [FOSSILS.md](FOSSILS.md) keeps the failures), and each names what would
> revise it. They are held as working principles, not laws: the moment evidence
> disagrees, the evidence wins and this file changes. Suggested by an outside reviewer
> who observed the project had started accumulating principles instead of features —
> which is, we think, the nicest thing anyone has said about it.

## 1. Runtime truth outranks documentation

When behavior and documentation disagree, capture the payload and trust reality. The
outcome-credit loop only exists because live capture contradicted the documented hook
behavior ([JOURNEY: the July 1 pivot](JOURNEY.md#the-pivot-that-made-the-whole-thesis-work-july-1),
[fossil F5](FOSSILS.md#f5--trusting-documented-payload-shapes-july-2026)).
*Would revise it:* a harness whose documentation proved reliably load-bearing across
versions — none observed yet.

## 2. Never rewrite the substrate

History is append-only. Corrections supersede; projections regenerate; nothing is
deleted. This is the project's center of gravity — everything above the ledger is
disposable *because* the ledger isn't — and it is also the specific defense against
consolidation drift documented in the 2026 literature
([arXiv 2605.12978](https://arxiv.org/abs/2605.12978)).
*Would revise it:* storage costs or privacy obligations that make full retention
untenable; the design answer would be encryption/tombstoning at the edge, not rewrites.

## 3. The yardstick before the mechanism

A mechanism must beat the boring baseline on our own data before it earns complexity.
Embeddings lost to a heuristic ([fossil F2](FOSSILS.md#f2--embeddings-as-the-default-router-june-2026));
the shape index ships nothing unless it beats baseline retrieval on held-out lessons.
*Would revise it:* nothing — but note the cost honestly: yardsticks delay shipping and
sometimes kill ideas that might have matured. We accept that trade.

## 4. Guards over discipline

If something matters, enforce it mechanically — CI checks, hooks, gates — because we
have watched every remember-to convention decay, in humans and agents alike
([JOURNEY: June 19](JOURNEY.md#the-audit-and-getting-religious-about-names-june-19)).
The corollary for agent systems: never rely on model compliance for a safety property
(models call tools they weren't offered; the deny lives in the harness).
*Would revise it:* a guard whose false-positive cost exceeds the failure it prevents —
guards are subject to the yardstick too.

## 5. One vocabulary, and names must not lie

A single written lexicon; a name must match behavior. We caught a class named `Bus`
that wasn't one, and now a guardrail script holds the line. Public naming follows the
field's standard vocabulary rather than invented terms.
*Would revise it:* nothing known; the failure mode (drift between name and reality)
recurs any time this relaxes.

## 6. Negative knowledge is knowledge

Failed approaches are recorded with the same care as successes — as `--anti-pattern`
lessons in the store and as [architectural fossils](FOSSILS.md) in the docs — because
the next contributor shouldn't have to rediscover why an idea that *sounds* reasonable
doesn't work here.
*Would revise it:* a fossil record so large it becomes its own reading burden; the
answer would be curation, not deletion (see principle 2).

## 7. Measured value steers curation — but never automates it

The funnel counts what was surfaced, voted, and outcome-credited; triage ranks the
corpus by measured value. The numbers *propose*; a judgment call *disposes*. Feeding
value metrics back into ranking or automated deletion is a Goodhart trap we've
explicitly declined ([JOURNEY: July 3](JOURNEY.md#the-system-measured-itself-and-we-didnt-love-the-answer-july-3)).
*Would revise it:* a replay benchmark strong enough to serve as a closed-loop oracle —
and even then, with the substrate as the safety net.

---

## The question underneath (speculative, and worth stating)

An outside reviewer, reading across the compaction work, the primitives research, and
this file, suggested the project is converging on a single question:

> **What is the smallest amount of information required to reliably recreate useful
> reasoning?**

Not facts — reasoning. It would explain why the same instincts keep recurring:
compression under a faithfulness floor, mined primitives, regenerable projections,
corrections as high-value signal, distrust of summaries that drift. The same reviewer
offered a mental model we're still chewing on: less a *memory system* than a
**knowledge compiler** — semantics preserved, representation changed, multiple targets
emitted (lessons, narrative, injections), always able to return to source. We record
both ideas here as *lenses, not claims*: if they keep predicting our own decisions
correctly, they'll earn a promotion out of this section.
