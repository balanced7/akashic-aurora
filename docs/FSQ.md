# Frequently anticipated skeptical questions

> The questions a skeptical engineer should ask about this project, answered before
> they're asked. Where an answer leans on a survey or an internal number, it links the
> record. If your skeptical question isn't here, we'd like it — open a Discussion.

## "Isn't this just RAG?"

RAG answers *what to retrieve*; this project's question is *did retrieving it change
the outcome*. The retrieval layer here is deliberately boring (deterministic ranking,
keyword-first, embeddings off by default). The parts that aren't RAG: injection at the
moment of action rather than prompt time, an outcome ledger, and a credit loop that
links the two — surfaced lessons get credited only when a just-failed action then
succeeds. Retrieval is the means; attribution is the point.

## "Why not just embeddings / a vector DB?"

We tried. Embeddings lost the ablation against a keyword heuristic on our own gold
fixture and stayed off by default ([fossil F2](FOSSILS.md#f2--embeddings-as-the-default-router-june-2026)).
They remain available behind a flag, and the shape-index work may earn them a
comeback — gated on beating the boring baseline on held-out lessons. If it doesn't
beat the yardstick, it doesn't ship.

## "Why append-only? Why not just Git?"

Git *is* part of the answer — the repo, its history, and the docs are half the record.
The other half is runtime state Git doesn't see: per-lesson usage counters, outcome
events, injection costs, cross-agent signals. The append-only rule exists because the
2026 consolidation literature documents memory that degrades under repeated LLM
rewriting (utility falling below a no-memory baseline —
[arXiv 2605.12978](https://arxiv.org/abs/2605.12978)); regenerating projections from
originals avoids that specific failure at the cost of storage, which is cheap.

## "How is this different from Mem0 / Zep / Letta?"

They're more mature products with better retrieval benchmarks, and we cite them. The
honest difference is what gets measured: their published evaluations are
retrieval-quality benchmarks; our survey found no published curation-quality or
outcome-attribution evidence from any of them (full record with citations in
[`research/reviewed/`](../research/reviewed/) — corrections welcome, that's a claim
about our search, not about the field). This project is an experiment in measuring the
thing we couldn't find measured. It may turn out their approach is right and the
measurement doesn't matter. That would be a result too.

## "How does this compare to Hermes / MoA?"

Different layer. Hermes Agent's Mixture-of-Agents composes *models at answer time*
(advisors + aggregator); this project manages *knowledge across time*. They're
complementary — our evening-review pattern (local drafts, frontier grading) is
MoA-shaped, and we adopted their tail-injection reasoning independently before reading
theirs. Their reported economics (≈6× latency, ≈80× token cost on cloud APIs) are why
our advisor tier runs on a local model instead.

## "Why deterministic ranking instead of an LLM judge?"

Because the judge would be judging its own kind. LLM-as-judge carries self-preference
and position bias, and intrinsic self-critique measurably degrades reasoning
([arXiv 2310.01798](https://arxiv.org/abs/2310.01798)); our faithfulness gate and
ranking are deterministic so every decision decomposes into inspectable components.
The cost: deterministic ranking misses semantic nuance an LLM would catch. We accept
that trade until the bench can prove an LLM judge earns its bias risk.

## "Where are the benchmarks?"

Internal and small, stated as such: 601 tests in CI, a live value funnel
(8 of ~130 tracked lessons hold all earned outcome credit; ~74% have surfaced five-plus
times with zero return), and honest ablation results where things lost. The real
benchmark — replaying recorded episodes memory-off / memory-on / perturbed — is
designed but not built ([`docs/leapfrog-plan.md`](leapfrog-plan.md)), and the prior art
it builds on is cited rather than claimed as novel
([fossil F6](FOSSILS.md#f6--our-replay-benchmark-is-novel-july-2026)). Until it exists,
we don't claim the memory helps at scale — the README's "not yet" section says exactly
that.

## "You're overengineering. This should be a SQLite database."

Partly guilty, and documented: the first version was triple-redundant Redis
([fossil F1](FOSSILS.md#f1--triple-redundant-redis-ha-april-2026)). Today the entire
core runs on the Python standard library with flat files; Redis is an optional
accelerator. The complexity that remains isn't in storage — it's in the measurement
loop (hooks, transcript synthesis, credit attribution), and each piece carries the
test that justifies it. Where we can't justify a piece, it goes to the fossil record.

## "What's actually novel here?"

Possibly nothing — and the project is built so that finding out is cheap. Our surveys
(≈200 cited findings) didn't find published systems doing outcome-credited,
action-time memory with curation gated on measured value; three specific assemblies
appear unclaimed (causal-utility measurement on real episodes, MDL-organized lesson
curation, structural indexing over a free-text lesson store). Every one of those is a
claim about *our search*, not the field. If you know prior art, pointing us to it is
the single most useful contribution you can make.

## "Why is a 7B local model involved? Isn't that tier too weak?"

For open-ended agentic work, yes — the Terminal-Bench gap between open and frontier
models is real and we don't pretend otherwise. The fleet runs *bounded* tasks
(seeded research, drafts against a fetch-before-cite contract) where the weak tier is
verifiable, and everything it produces is graded before it counts. The interesting
question — whether an independent weak critic catches things a strong generator's
self-check misses — is an open research task in the queue, not an assumption.
