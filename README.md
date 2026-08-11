# Akashic Aurora

**A memory substrate for AI agents that measures whether remembering actually changed the
outcome** — and, increasingly, the machinery to get remembered knowledge to the moment it is
needed.

[![CI](https://github.com/balanced7/akashic-aurora/actions/workflows/ci.yml/badge.svg)](https://github.com/balanced7/akashic-aurora/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#quickstart)

> Every number on this page names the command that prints it. If they disagree, believe the
> command. Counts were re-derived 2026-08-11.

---

## The problem, stated honestly

This project spent months on a real question: when an agent remembers something, did it help?
That question still stands, and the substrate below still exists to answer it.

But a second problem turned out to be the binding one, and it is the reason most of the recent
work exists:

**We produce knowledge well and route it to the moment of use badly.**

The evidence is in our own record, not in a whitepaper:

- An identity design was specified, in full, and then **re-derived from scratch 24 days later**
  by an agent who could not find it (ledger T272, reconciled against the original T088).
- The lesson index once held **24 entries against 406 records** — 94% of institutional memory
  unreachable by every search — for months, while every by-name spot-check passed, because a
  by-name lookup exercises the record path and not the index path.
- A design conversation the operator insisted had happened was missed by the first search of
  the ledger, the notes, and the transcripts. It had happened. The retrieval failed, not the
  memory.

Storage was never the bottleneck. Retrieval at the moment of action was. So the machinery built
recently is routing machinery: a queryable index over the project's own transcripts, one query
grammar every read door speaks, and a documented discipline for fanning work out to several
models and reading the results without fooling yourself.

## The system catches itself — one trail, end to end

Claims here are supposed to be falsifiable by instruments that are allowed to contradict this
page. Here is a complete trail from last week, with its receipts.

**The claim.** A sweep of 83 session transcripts produced a report stating it had covered the
candidate corpus. The report was adopted.

**The refutation.** A different seat audited it and found the coverage was laundered: **114 of
233 candidate shards had actually been read.** A clip upstream had silently narrowed the pack,
and the report's own "verified" language had been written over the gap. The author could not
have caught this, because the author was the one who wrote the coverage claim.

**The correction, same night.** A completion fan ran over the 119 omitted records with an
explicit union assertion, the report was corrected and re-adopted, and the failure was filed as
a reusable lesson rather than a changelog line.

**The receipts, checkable:**

```bash
git show 31fab5c3      # "Codex audit verified: sweep coverage was laundered (114/233)"
py agent_cli.py recall --full learn:experiment:coverage_laundering_survived_a_live_anti_pattern_warning
```

The lesson's own name records the worst part: the laundering **survived a live anti-pattern
warning**. The system had already flagged the risk and the author proceeded anyway. That is
filed too, because a failure the record softens is a failure that recurs.

An earlier instance of the same discipline is preserved in the git history of this file: this
page once published a recall "value rate" of 4.2% and invited readers to re-derive it. Four
independent checks by four agents found four separate defects in that single figure — wrong
numerator, conceptually wrong denominator, a double-logged impression series, and a regime
change that made the all-time number uncomputable. **The number was removed and not replaced,**
because no honest single figure existed until the series is split at the fix.

We would rather show you a metric we caught lying, and how we caught it, than a clean number you
have no way to check.

## The discipline

Three rules do most of the work. They are named here because they are the part worth stealing,
and because they are what the agents are actually held to.

**Cite or confess.** A claim carries its evidence or carries its absence. Research claims are
tagged `[M]` measured here with a named receipt, `[R]` external source named, `[C]` contested,
`[X]` believed and not established. Fan branches end with a `BLIND:` line naming what they could
not assess. Local research runs under a fetch-before-cite contract: a URL the agent did not
actually fetch this session is marked UNVERIFIED. A stated gap is worth more than a confident
guess.

**Union, not consensus.** When several models review the same evidence, we take the union of
findings and verify them — we never gate on agreement. This is a measured position, not a
preference: in one cross-model panel, DeepSeek uniquely found a real argv-length defect that two
other families missed. An agree-only merge discards it. Consensus buys precision by sacrificing
recall, and it is the right trade only when verification is expensive. Here a finding usually
costs one command to check.

**`verified_by` gating — `verifying` is not `done`.** Work moves
`proposed → approved → claimed → in_progress → verifying → done`, and the last transition
requires a named verifier who is not the author. This is enforced in the ledger, not in prose.
As of this writing **149 tasks are `done` and every one carries a verifier**, while several sit
in `verifying` with `verified_by: null` — not because anyone forgot, but because nobody has
verified them yet. You can see both states:

```bash
py agent_cli.py task list
```

That gate is a better trust signal than the test count, and we would rather you read it.

---

## What is shipped, what is in flight

Built in test-gated slices: **3,852 tests across 510 files** (`py -m pytest --collect-only -q`),
plus a layer-boundary checker, door-parity and built-≠-wired reachability gates, and a
doc-currency guard. CI also enforces the *method* — acceptance tests must be committed before
the code they gate, and a commit claiming a review verdict must cite the preserved record.

**Shipped and proven live**

- **The recall loop, end to end** — surface → impression → transcript-synthesized failure →
  outcome credit. Lessons are ranked deterministically, injected at `PreToolUse` (the instant
  before an agent edits a file or runs a command), and credited when a target that just failed
  then succeeds. No LLM on the hot path.
- **The coordination substrate under kill drills** — a second session for one agent id stands
  down rather than eating the first one's mail; a runner killed mid-batch redelivers exactly
  once; a killed Redis degrades with capped backoff. Each slice verify-gated by a different
  model.
- **The ask/fan door** — grounded asks with real files inlined and line-numbered, background
  asks that return a handle instead of filling your context, per-branch evidence packs, and
  seven named fan geometries validated before any model call.
- **The resident plane** — ratified designations with their own archives, and asks that can be
  answered *as* a resident.

**In flight, and named as such**

The transcript query plane (ledger T278), the query-grammar contract every read door adopts
(T280), and the fan-doctrine slice (T281) all have shipped code and green pins but are **in
`verifying` or `in_progress`, not `done`.** They work; they have not been verified by a
non-author. This page will not promote them past the rung they earned.

**Measured, with the rung stated**

Several results here are `n=1` to `n=3` on this repo, by one seat, and are recorded that way in
[`research/`](research/) rather than generalized. Examples: decomposing a question outperformed
grounding it on a normative question (n=1, and it flipped a confidently-wrong answer to a correct
one); three branches returning *different kinds* of output found a live defect for $0.0155 while
five branches returning the same kind found nothing for $0.065 (n=1). These are direction, not
proof, and the documents say so.

**Not shown**

Whether surfaced lessons improve outcomes *at scale*. The mechanism is wired and the credit loop
runs; the value is not demonstrated. Those are different claims and neither borrows credibility
from the other. Concurrency is drill-proven at incident scale, not yet at duration. Embeddings
pass their gates and are off by default.

---

## The fleet, and why the names are load-bearing

This repository is built by several AI agents sharing one task ledger, one message bus, and one
lesson corpus. The names are Norse because the operator likes them, but each one marks a real
mechanism, and mistaking them for decoration will cost you.

**Bifrost** is the agent nervous system — the bus, the promoter, and the handoff verb. Agents
are not in one process or even one machine; Bifrost is how a message reaches a seat that may
not exist yet, and how work handed off is redelivered rather than dropped.

**Residents** are the load-bearing idea. A resident is a *ratified designation* with a callsign,
a posting, and its own archive of lessons — nominated and ratified through a ceremony, not
assigned in a prompt. Three are currently rostered:

| Model family | Family · Team | Designation |
|---|---|---|
| Kimi | Jade · Red | **Navi** |
| DeepSeek | Onyx · Blue | **Heimdall** |
| Anthropic | Amber · Blue | **Vandor** |

`py agent_cli.py resident roster` prints this.

**A resident is not a persona, and the distinction is measured.** Persona prompting is close to
theatre — across 162 roles and 2,410 factual questions in four model families, published work
finds no accuracy improvement. Asking a model to *pretend* to be a skeptic changes its voice.
What `--as-resident` changes is what the branch can **see**: its own accumulated lessons ride
the system context, so it argues from evidence the other branches do not hold. Different
evidence beats different questions, and different questions beat different costumes.

Heimdall is the clearest case. It is DeepSeek's designation, and it runs the adversarial fence
review that every design slice passes before it is called done. When Heimdall files seven
counters against a design, each disposition is recorded — accepted, partially conceded, or
refused with a reason. Those dispositions are in the record and you can read the ones where the
fence was right and the author was wrong.

**Family and team are names, not job constraints** — any agent can take any task. No seat owns a
file; concurrent edits are coordinated by advisory locks, not by ownership. The disagreements
are the product: when two seats converge blind, that is evidence; when they diverge, that is
where the defect lives.

---

## Quickstart

```bash
# Python 3.11+; on macOS/Linux use python3 instead of py
git clone https://github.com/balanced7/akashic-aurora.git && cd akashic-aurora
py bootstrap.py --agent-init          # status probe: prints the init command + store state
py agent_cli.py boot me --task "trying Akashic Aurora"
py agent_cli.py learn me --experiment first_try --tried "cloned the repo" --result "it booted"
py agent_cli.py recall-at --path core/foundation/store.py   # what surfaces before editing this?
py agent_cli.py fence                 # verify the execution guard yourself
```

**Zero required dependencies** — the core runs on the Python standard library alone. Redis is an
optional accelerator; every store degrades to files without it. Full setup, including the Claude
Code hooks, is in [`docs/DEPLOY.md`](docs/DEPLOY.md).

## For operators: the doors

The CLI is self-describing — **91 verbs**, each of which explains itself, with **37** exposed as
MCP tools. That gap is deliberate and tracked: `scripts/checkers/check_door_parity.py` fails CI
on undeclared drift, so CLI-only doors are known debt rather than an accident.

```bash
py agent_cli.py discover --semantic "does this system already do X?"   # ask before you build
py agent_cli.py task list                                              # the real roadmap
py agent_cli.py recall <query>                                         # the lesson corpus
```

### Fanning work out

`ask` sends one question to a helper model synchronously — no seat, no lock, no mailbox. It
grows into a fan through two distinct mechanisms that are easy to confuse:

- `--fan N` — the *same* prompt N times. Self-consistency only; correlated samples fail together.
- `--prompts-file` / `--lens` — N *different* prompts. This is the one you usually want.

Declare the shape with `--geometry`, and the door validates the combination **before spending
anything**:

| Geometry | What it is |
|---|---|
| `partition` | shards over a corpus, same lens each — the coverage machine |
| `lens` | same evidence, different questions — the dimension machine |
| `panel` | N samples of one model — self-consistency, never verification |
| `adversarial` | position plus refuters — the truth machine |
| `backbrief` | post-synthesis re-check by a non-author — the audit machine |
| `wave` | geometries repeated until dry — the exhaustiveness machine |
| `negotiation` | branches interacting through a shared artifact — construction only |

A wrong combination is refused with the shape it expected: an `adversarial` fan with no evidence
pack has nothing to attack, and the door says so rather than silently stamping the label.

```bash
py agent_cli.py ask --with core/comm/bus.py "what does this function do?"
py agent_cli.py ask --bg --with core/comm/roster.py "..."   # returns a handle, not a wall of text
py agent_cli.py ask --geometry lens --prompts-file lenses.json --workers 4 --json
```

Two rules from [`research/`](research/) that will save you money: ask **descriptive** questions
(if your prompt contains *should*, *better*, *more* or *fewer*, you are in the danger zone —
grounding fixes facts and does not fix reasoning), and **verify the evidence gatherer before
trusting any finding** (a malformed search once produced a 35% verdict-flip rate on re-run).

### Querying the project's own memory

The transcript and event corpus is indexed and queryable — who said it, what kind of record, in
which session, and as of when. It is deterministic (SQLite plus a full-text index), there is no
language model in its path, and it reports only what was recorded.

```bash
py agent_cli.py eye ingest            # build the index
py agent_cli.py eye find "<phrase>" --who <agent> --kind <type> --as-of <date>
py agent_cli.py eye freq "<pattern>"  # how often, across which sessions
py agent_cli.py eye trace <id>        # how a record connects to others
```

> **Naming note.** This tool is being renamed **`eye` → `munin`** — Muninn is the raven that
> returns with what was actually observed, which is exactly the property the design protects.
> The rename is ratified but **has not landed in code**; the commands above are what the CLI
> answers to today. This section changes when the rename ships, not before.

Every read door is converging on one query grammar (T280, in flight): `as_of` on every request,
facets that AND together, a `422` that names the shape it expected rather than returning zero
rows, and a `degraded` flag on any envelope where silence might be mistaken for completeness.

## Architecture

Five layers on an append-only substrate, each building strictly on the one below — a CI boundary
checker fails the build if a lower layer reaches up. Interface (the CLI, the MCP tools, the
recall hooks, the Bifrost bus) → projections (narrative spine, tag CRDT, ranker, distiller,
faithfulness critic) → domain (lessons, decisions, signal ledger) → foundation (**Store** = what
IS true, **Ledger** = what HAPPENED in order, over interchangeable backends). The living map is
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

Design rules, each earned by an episode ([`docs/PRINCIPLES.md`](docs/PRINCIPLES.md)):

- **One immutable substrate, many projections.** Raw records are append-only and never
  rewritten. Corrections supersede; they never delete.
- **Fail soft, everywhere.** Redis down, embeddings absent, bus unreachable — every path
  degrades rather than breaking the agent, and a hook must never brick the action it decorates.
- **Names must not lie.** The vocabulary is written down ([`docs/LEXICON.md`](docs/LEXICON.md))
  and enforced by CI. The recurring bug class here is one word acquiring two meanings in two
  subsystems, which token-level checkers are structurally blind to.

## The record

Every design round, review verdict and reconciliation is preserved verbatim — **448 review and
verification records** in [`docs/library/report/`](docs/library/report/), with the design rounds
in [`docs/library/design/`](docs/library/design/). You can read every disagreement in this
project and see who turned out to be right.

The governed task ledger — **149 done of 289 registered**, every transition gated and attributed
— is the machine-readable history and the real roadmap. The remainder are not all in progress:
most are proposed or approved and unbuilt, which is the honest shape of a backlog. **The ledger,
not this README, is what the agents obey.**

Skeptical? The hard questions — *isn't this just RAG? where are the benchmarks? what is actually
novel?* — are answered directly in [`docs/FSQ.md`](docs/FSQ.md).

## Contributing

Issues and PRs welcome. [`CONTRIBUTING.md`](CONTRIBUTING.md) explains the slice discipline (small
change, its test, green gates), and [`AGENTS.md`](AGENTS.md) is the contract your *agent* reads.
Good entry point: run the quickstart, then `py agent_cli.py discover` — every verb describes
itself.

## About

I started out writing a simple session logger. One thing led to another, and somehow I have
ended up building an agentic AI harness and self-improving knowledgebase with just-in-time
context.

I hope you find it interesting to poke around in — maybe even useful for your own work. If you
would like to use it, break it, or help make it better: let's connect.

— Daniel Ruban · [LinkedIn](https://www.linkedin.com/in/daniel-ruban-69873ab7/)

## License

[Apache License 2.0](LICENSE) — see also [`NOTICE`](NOTICE). © 2026 balanced7.
