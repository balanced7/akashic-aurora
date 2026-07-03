# The journey so far

> **Akashic Aurora** is an open-source memory layer for AI agents: lessons injected at
> the moment of action, credited by whether they changed the outcome, kept on an
> append-only substrate. This document is the human-readable history of its direction,
> decisions, and pivots — kept because the pivots are where the learning lives. New entries are appended at each
> arc's close, written at wrap time and reviewed by a human. The machine-generated
> version of this record is `py agent_cli.py story` (the narrative spine); this file is
> the curated telling. Abandoned decisions are preserved separately in the
> [fossil record](FOSSILS.md). First published as a Discussion, 2026-07-03.

## The one idea everything leans on

An outside reviewer of an early draft pointed out that the center of gravity here isn't
any feature — it's one sentence: **append-only substrate, regenerable projections.**
On reflection, they're right, so it goes first. The record of what happened is sacred
and never rewritten; everything above it — summaries, chapters, topic clusters, the
future shape index — is a projection that can be regenerated from the record. That's
what makes the rest of this document possible: summaries can be wrong, compaction can
be aggressive, experiments can fail, and nothing is lost. Everything is disposable
*because* the substrate isn't.

---

## Where it started (and what we over-built)

This began as a session logger. I was frustrated that every new agent session started
from zero — re-learning the project, re-making settled decisions — and I wanted agents
to stop repeating themselves. One thing led to another.

The first incarnation (April 2026, then called *BreakThrough Stack*) is preserved in
the history mostly as a warning to ourselves: triple-redundant Redis with HA failover,
sync pollers, a multi-agent communication mesh — infrastructure built with real
enthusiasm, before we knew what the system was actually *for*. Almost none of it
survived on its own terms. What survived was the itch: agents that keep what they learn.

*Lesson we kept: build the smallest architecture that can answer the research question.*

## The audit, and getting religious about names (June 19)

A codebase audit found what you'd expect: a clean-ish core surrounded by stale shells
and ~65 bare `except:` clauses. Two decisions from that week shaped everything after:

- **One vocabulary, written down.** A `LEXICON.md` with a single authoritative
  definition per term, and a ban on names that lie. We'd caught a class named `Bus`
  that wasn't one, and a `success:"True"` that wasn't either.
- **Guardrails over discipline.** `check_boundaries.py` enforces the rules in CI,
  because we'd already watched good intentions decay. The principle we wrote down then —
  *make the implicit explicit, then let a machine hold the line* — is still the most
  load-bearing sentence in the repo.

*Lesson we kept: make the implicit explicit, then let a machine hold the line.*

## The substrate decision (late June)

The refactor that followed split everything into a **Store** ("what is true") and an
append-only **Ledger** ("what happened, in order"), with the rule that the substrate is
sacred: nothing is ever rewritten, only superseded. At the time this was a
tidiness decision. It turned out to be the one we now lean on hardest — months later we
read the 2026 literature on memory systems whose repeated LLM consolidation drifts
knowledge into generic mush ([arXiv 2605.12978](https://arxiv.org/abs/2605.12978); our
full survey with citations is in `research/reviewed/`), and our architecture avoids
that particular source of drift by construction: re-distillation always consumes the originals, never the previous
summary. (The substrate preserves recoverability; projections and retrieval can still
drift in their own ways, and need their own guards — we don't claim immunity.) We'd
like to claim foresight; it was mostly conservatism.

*Lesson we kept: never rewrite the substrate; regenerate everything else.*

## The narrative spine, in gated slices (June 27)

One long day built the story layer — Beats, Chapters, Tracks, Themes — as small slices,
each with a benchmark bar it had to clear before landing (the routing slice shipped at
ARI 0.86 / WindowDiff 0.15 against a gold fixture). The honest highlight isn't what
worked, it's what didn't: **embeddings lost the ablation.** The "obviously better"
semantic routing underperformed the boring heuristic on that same fixture, so the
heuristic shipped as the default and embeddings stayed off. That set a pattern we've
kept: the fancy thing has to *beat the yardstick*, not just exist.

*Lesson we kept: fancy mechanisms don't survive unless they beat boring baselines.*

## Renaming, and letting go of ownership (June 28–29)

*BreakThrough Stack* became **Akashic Aurora** — Akasha for the immutable record,
Aurora for the knowledge that self-organizes above it. Same week, we dropped per-agent
file ownership entirely: any agent does any task, coordinated by transient advisory
locks and enforced at the door (git hooks that block blanket staging) rather than by
memory or convention. Then the repo went public — which forced the honesty that's now
house style: the README's "what's proven, tested, and not yet" section exists because
we couldn't vouch for everything and decided to say so.

*Lesson we kept: coordinate at the moment of contention, not by standing assignment.*

## The pivot that made the whole thesis work (July 1)

Our core question is whether injected memory *changes outcomes*. The design assumed the
harness would tell us when a tool call failed, so we could credit lessons that turned a
failure into a success. **Live payload capture proved the assumption false**: the hook
fires only on success; failures emit no event at all. Community docs said otherwise;
the captured payloads didn't care.

The pivot: synthesize the failure half from session transcripts (where failures *are*
recorded), watermark each failure so it can't be double-counted, and keep the direct
failure event as a fast path where it exists. The first outcome-credited lesson landed
live that evening; within the next two days the internal value rate (credited + voted
per surfaced impression) moved from 1.1% to 1.9% and lesson capture ran at ~105 new
lessons per week — small numbers on a small corpus, recorded here so later entries can
be compared against them. Two disciplines came out of that week and are now reflexes:
**capture payloads before trusting their shape**, and **an assumption is not a design
input until it has survived contact with a live system**.

*Lesson we kept: runtime truth outranks documentation.*

## Learning from the field, on purpose (July 2)

A three-agent survey of memory-and-context practice produced a ranked adoption plan,
and we shipped the top of it within a day: an injection ledger (pushed context should
never be hidden state, and its token cost should be measured), plan-time recall,
near-duplicate detection at write time. The survey also told us where to be humble:
our replay-benchmark idea had already been published by others that February — so
the plan changed from "novel benchmark" to "differentiate on real episodes and
cost-normalized value, and cite the prior art."

The same day, the harness layer got honest: a capability matrix of what each
agent-runtime can actually deliver (Cursor's hooks can't inject context before an
action — so there, lessons arrive one beat late, and the docs say so plainly).

*Lesson we kept: mine the field for sequencing, not just validation — and cite whoever got there first.*

## The fleet (July 2, evening)

A YouTube video about running Claude Code on local models turned into the project's
best economics decision: **frontier tokens for deciding, local tokens for gathering.**
A free 30B-class model on a single consumer GPU now runs behind the same harness —
same hooks, same memory, same outcome credit, its own agent identity — and works a
research queue unattended: fresh session per task, hard timeouts, drafts validated
against a fetch-before-cite contract, frontier review in the evening.

Its first overnight shift: seven tasks, five accepted articles, three timeouts — all
three the same cause (fetching full paper HTML blows the prefill budget at local
speeds), which the task format now routes around. The moment we trusted the setup was
watching the local model *refuse to make something up*: it couldn't fetch a paper, so
it marked every finding UNVERIFIED and moved on. The review caught the gap; a frontier
fetch closed it.

*Lesson we kept: frontier tokens for judgment, local tokens for gathering — and trust the gates, not the model.*

## Standing on 750 years of shoulders (July 3)

An idea about organizing knowledge by *shape* — reusable reasoning structures that
cross domain boundaries — felt novel for about an hour. The overnight research pass
traced the lineage from Llull (1274) through Leibniz, Wilkins, Ranganathan's facets,
Schank's primitives, and Cyc's $200M cautionary tale, and the pattern is remarkably
consistent: **invented universal vocabularies collapse; mined, small, operationally
grounded ones survive.** Program synthesis already does the mining computationally
(library learning under a compression objective), and one paper had even indexed a
text corpus by purpose-and-mechanism instead of topic, with measured gains.

So the plan adopted the field's laws rather than our first instincts: mine primitives
from our own corpus, never invent them; cap the vocabulary at tens; name and document
every one (the literature is blunt that undocumented abstractions *hurt*); and gate the
whole thing on beating our own baseline retrieval — if it doesn't, it ships nothing.

*Lesson we kept: mine vocabularies from usage; invented ones collapse at the boundary.*

## The system measured itself, and we didn't love the answer (July 3)

The first value-triage over live counters: of 127 tracked lessons, **8 hold every
earned credit, and 94 have surfaced five-plus times with zero return.** Small corpus,
internal numbers — but that's the honest shape of our memory today: most of what we
push isn't (yet) paying rent. We chose not to mass-delete; the literature's
over-deletion warnings (faithfulness-only metrics reward deletion —
[arXiv 2404.03278](https://arxiv.org/abs/2404.03278) — while utility-scored *selective*
deletion measurably helps — [arXiv 2505.16067](https://arxiv.org/abs/2505.16067))
earned a two-sided gate (faithfulness *and* coverage) before any retirement happens. The number's job is to steer the curation work, and to be
re-measured after it.

*Lesson we kept: measure before curating — the report proposes, judgment disposes.*

## Working principles (so far)

These are principles that *appear to hold* in our context — each earned from more than
one episode, none of them proven laws. Future entries should revise this list when the
evidence does.

- **Payload truth.** Capture what the system actually sends before designing against
  what the docs say it sends. This single habit has caught more wrong assumptions than
  everything else combined.
- **Enforce at the door.** Guards live in hooks and gates, not in model compliance or
  agent memory. Every time we've relied on "the agent will remember to," it eventually
  didn't.
- **Never rewrite the substrate.** (The thesis, restated as a rule.) Projections may be
  regenerated, superseded, or discarded; the record may only grow.
- **The yardstick before the mechanism.** Benchmarks first killed our embeddings, then
  our "novel" bench idea, then our hand-designed taxonomy instincts. Losing to the
  yardstick early is much cheaper than losing to reality later.
- *Working principle:* **corrections appear to produce the highest-value lessons** in
  our current corpus. We record every one; whether this holds as the corpus grows is
  exactly the kind of thing the funnel exists to check.

## Where we set off next

The replay benchmark over real recorded episodes (adopting the perturbation-stability
check we liked in the CMI paper, adding the confound control we didn't find there);
the gated consolidation pass; the shape index, if it earns its keep. Each with its bar
stated before the build starts. If we pivot again, this file gets the why.
