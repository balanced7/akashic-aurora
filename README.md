# Akashic Aurora

**Memory for AI agents that learns what actually helped** — lessons injected at the *moment of action*, credited by *outcome*, and challenged by *counter-evidence*.

[![CI](https://github.com/balanced7/akashic-aurora/actions/workflows/ci.yml/badge.svg)](https://github.com/balanced7/akashic-aurora/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#quickstart)
[![Tests](https://img.shields.io/badge/tests-601%20green-brightgreen.svg)](tests/)

Most agent memory answers *"what did we store?"* and is graded on retrieval quality. Whether a remembered lesson actually **changed what the agent did — and whether that helped** — usually goes unmeasured, because measuring it takes three things at once: injection at the moment of action, an outcome record, and a credit loop connecting them.

**Akashic Aurora is an experimental memory substrate that measures whether remembered knowledge changes agent outcomes.** Everything else in this repository — the append-only ledger, the narrative spine, the faithfulness gates, a local-model fleet that gathers research evidence overnight — exists to serve that one measurement, or to keep us honest when we're wrong about it.

A "lesson" here is an operational unit, not a general fact: *what was tried, what failed, what fixed it, and the trigger for when to apply it* — the kind of knowledge whose impact on an outcome can actually be attributed.

---

## Why this exists

Memory layers for coding agents all follow the same recipe: capture the session, compress it, inject it at the *start* of the next one, and measure retrieval quality. That leaves three problems open (surveyed against the field, mid-2026):

| | Typical memory layers | Akashic Aurora |
|---|---|---|
| **When knowledge arrives** | Session start / prompt time | The instant before the agent edits a file or runs a command (`PreToolUse`) |
| **What gets rewarded** | Retrieval relevance, access frequency | **Outcome**: when a target that just *failed* then *succeeds*, the lessons surfaced for it are credited — automatically, contrastively |
| **Confirmation bias** | Retrieval maximizes agreement with the query | **Dialectical recall**: the strongest genuine *counter*-lesson is surfaced alongside the thesis; provenance tags mark every claim `worked / unverified / anti-pattern` |
| **Ranking** | Embedding / LLM scoring | **Deterministic and auditable** — every ranking decomposes into inspectable components; no LLM on the hot path |
| **Trust** | Assumed | **Enforced**: a no-LLM faithfulness gate blocks any lesson whose source pointer doesn't resolve to a real record |

None of this replaces your agent's native memory — it sits underneath it, as the layer that closes the loop from *remembering* to *provably helping*.

## See it work

This is a real injection, captured while an agent was editing this very repo. The moment before the tool ran, the hook attached:

```
Recall-at-action (Akashic) - facts relevant to what you're about to do:
[worked claude] Build the yardstick + a real-corpus probe before the mechanism; trust the
  curated fixture and treat any... (source: learn:experiment:eval_harness_before_fix)
[anti-pattern claude] An on-topic anti-pattern != a contradiction of a thesis; topic-adjacency
  conflates with stance.... (source: learn:experiment:recall_dissent_slice3_precision)
... 3 of 5 relevant lesson(s) shown — `recall-at --limit 5` for the rest,
    or `recall --full <source>` for any one's whole record
```

And this is the feedback loop closing — a lesson was surfaced for a failing target, the retry succeeded, and the credit landed with no human in the loop:

```
recall:use:learn:experiment:faith1_faithfulness_critic  =>  {"surfaced": 5, "helped": 1}
```

That `helped` counter feeds back into ranking: lessons with a track record rise; lessons surfaced often but never useful decay. The agents building this repo use it while they build it — the examples above are from that work, unedited.

## Quickstart

```bash
# Python 3.11+; on macOS/Linux use python3 instead of py
git clone https://github.com/balanced7/akashic-aurora.git && cd akashic-aurora
py bootstrap.py --agent-init            # status probe: prints the init command + Redis/lesson state
py agent_cli.py boot me --task "trying Akashic Aurora"
py agent_cli.py learn me --experiment first_try --tried "cloned the repo" --result "it booted"
py agent_cli.py recall-at --path core/foundation/store.py   # what would surface before editing this?
```

**Zero required dependencies** — the core runs on the Python standard library alone. Redis is an optional accelerator (`pip install -r requirements.txt`); every store degrades gracefully to files when it's absent. On macOS/Linux use `python3` for `py`. Full setup, including the Claude Code hooks, is in [`docs/DEPLOY.md`](docs/DEPLOY.md).

## How the loop works

```
        ┌──────────────────────────────────────────────────────────────┐
        │  agent is about to act (edit file / run command)             │
        └──────────────┬───────────────────────────────────────────────┘
                       ▼
   SURFACE   rank active lessons for this exact target (deterministic; show
             nothing below a relevance floor; ≤3; anti-repeat per session;
             faithfulness-gated; provenance-tagged; counter-lesson if one exists)
                       ▼
   ACT       the action runs; an impression links {target → lessons shown}
                       ▼
   RESOLVE   on success after a just-failed attempt of the same target, the
             surfaced lessons are credited `helped` (consume-on-credit — one
             failure can never be farmed; first-try success credits nothing)
             "failed" = a tool_result recorded with is_error in the transcript;
             "succeeded" = the post-tool event arriving (it only fires on
             success), with user-cancelled runs excluded
                       ▼
   RE-RANK   usefulness factor [0.5×–1.5×] folds the track record into every
             future ranking — proven lessons rise, noise decays
```

The failure signal itself is *synthesized from the session transcript* (hook events only fire on success — a fact this project discovered by capturing live payloads and pinning them as contract-test fixtures in [`tests/test_claude_hook_contract.py`](tests/test_claude_hook_contract.py)).

## The architecture in one view

Each layer builds strictly on the one below; a CI boundary checker fails the build if a lower layer reaches up.

```
S5  INTERFACE     agent_cli.py (one self-describing CLI) · the same verbs as MCP tools ·
                  recall-at-action hooks · Bifrost cross-agent bus · advisory locks
S4  PROJECTIONS   narrative spine (Beat→Chapter→Track→Atlas: the time-axis view —
                  session events distilled into a regenerable story) · tag CRDT ·
                  shared primitives: Ranker · Distiller · Consolidator · Faithfulness critic
S1–3 DOMAIN       LearningStore (lessons) · AgentMemory (decisions) · signal ledger · coordinator
S0  FOUNDATION    Store ("what IS true")  +  Ledger ("what HAPPENED, in order")
                  three interchangeable backends: Redis / File / Hybrid (fail-soft)
```

Design rules that hold it together (the full set, each with the episode that earned it, is [`docs/PRINCIPLES.md`](docs/PRINCIPLES.md)):

- **One immutable substrate, many projections.** Raw records are append-only and never rewritten; everything readable (tags, chapters, digests) is regenerable *from* them. Corrections supersede; they never delete.
- **Multi-agent by default.** Claude and Cursor share the same lessons, message bus, and advisory locks on one repo — any agent, any task, no permanent ownership. What each runtime's hooks can actually deliver is documented honestly, tier by tier, in [`docs/integration-tiers.md`](docs/integration-tiers.md) (`py agent_cli.py harnesses` prints the live matrix).
- **Fail soft, everywhere.** Redis down, embeddings absent, bus unreachable — every path degrades instead of breaking the agent, and a hook must never brick the action it decorates.
- **Names must not lie.** The vocabulary is written down ([`docs/LEXICON.md`](docs/LEXICON.md)) and enforced by guardrail scripts in CI.

## What's proven, tested, and not yet

Built in small **test-gated slices** — no capability lands without the test that proves it. **601 tests** run on every push (full suite + boundary checker + doc-freshness guard, against a live Redis service).

**Proven live (not just unit-tested)**
- The full recall loop, end to end: surface → impression → transcript-synthesized failure → outcome credit. First credited flip landed 2026-07-01, in-session, and the payload contract is pinned to live-captured fixtures.
- A **free local model as a first-class agent**: glm-4.7-flash behind the same Claude Code harness ran real repo commands with every hook firing and its lessons attributed — then worked a 7-task research shift overnight, unattended (5 articles accepted at review; the 3 failures were all the same diagnosable cause, now encoded back into the task format).
- **The system measures its own memory**: `py agent_cli.py triage` reports, from live counters, that 8 lessons currently hold all earned credit while 94 have surfaced five-plus times with zero return. Internal numbers, small corpus — but they exist, and they steer what we curate next.

**Solidly tested**
- Foundation (all three backends, CAS/atomic update, time unification, supersession) · shared primitives (Ranker, Distiller, Consolidator, faithfulness critic) · narrative spine (~100 tests incl. a fuzzed CRDT) · events · Bifrost bus + locks + git-guard · recall ranking, anti-repeat, warm cache, usefulness factor · the CLI/MCP door ("no silent verb" is itself a test).

**Tested with honest caveats**
- The faithfulness critic is characterized for zero false-positives on today's extractive output; discrimination on abstractive (LLM-written) text is unproven until an LLM writer exists.
- Embeddings pass unit + ablation gates but are **off by default**; the always-on path is deterministic.
- Concurrency mechanisms are unit-tested; a sustained two-process race at scale is not continuously exercised.

**Not yet**
- The Codex curator loop (topic-axis self-curation) — parts built and tested, the loop that ties them is queued.
- Whether surfaced lessons improve outcomes *at scale* — the credit mechanism is live; the numbers now need field time. The measurement plan (a replay benchmark over the append-only ledger) is [`docs/leapfrog-plan.md`](docs/leapfrog-plan.md).

## The fleet

Frontier tokens are for **deciding**; local tokens are for **gathering**. A free local model
(glm-4.7-flash on a single consumer GPU, ~25 tok/s) runs behind the *same* Claude Code
harness — same hooks, same recall, same outcome credit, its own agent identity — and works
a research queue all day: one fresh session per task, hard timeouts, drafts validated
against a fetch-before-cite contract ([`research/`](research/)). A frontier agent reviews in
the evening: accept with corrections, requeue with feedback, escalate what local prefill
can't handle. ("Review" here means a frontier *agent* grades each draft against the
fetch-before-cite contract and stamps its verdict — corrections and rejection reasons
included — into the file itself; it is not human peer review and we don't present it as
such.) Discovery runs through a self-hosted SearXNG, so the whole shift costs
nothing but electricity. The first unattended overnight shift produced five accepted
research articles — the reviews, verdicts and all, are in
[`research/reviewed/`](research/reviewed/).

> The project's full history — direction, decision making, and the pivots that taught us
> the most — is kept human-readable in [`docs/JOURNEY.md`](docs/JOURNEY.md).

## The facets we chose, and where they've led

We picked three questions our field surveys suggested were underexplored. The survey
records — every finding with its citation — are in [`research/reviewed/`](research/reviewed/);
**if you know prior art we missed, we'd genuinely like the pointer.**

1. **Outcome-credited memory.** We set out to measure whether injected lessons change
   results, not just whether retrieval looks relevant. The first design assumed the
   harness reported tool failures; live payload capture proved it doesn't (failures emit
   no event at all), so we pivoted to synthesizing the failure half from session
   transcripts — that pivot is why the credit loop works. So far, internally: the loop
   runs live, and credit concentrates in a small core (8 of 127 tracked lessons hold all
   of it). Next: a replay benchmark over the append-only ledger, adopting the
   perturbation-stability check we liked in [CMI (2605.17641)](https://arxiv.org/abs/2605.17641)
   and adding the error-trace confound control we didn't find there
   ([`docs/leapfrog-plan.md`](docs/leapfrog-plan.md)).
2. **Curation by compression.** The goal is a corpus that gets *better, not bigger* —
   compress only as far as the knowledge still does its job. We deferred MDL as the live
   objective once when the corpus was too small to support it (that was the right call at
   the time), and revived the plan now that usage data exists to weight it. Our survey of
   consolidation practice found retrieval benchmarks published everywhere and curation-
   quality evidence almost nowhere — which made us cautious: retirement here waits for a
   two-sided gate (faithfulness *and* coverage), because the literature shows repeated
   LLM consolidation can drive utility below a no-memory baseline.
3. **Retrieval by structure.** The most transformational reading we did: analogical
   retrieval fails on surface bias in humans and LLMs alike, and program-synthesis
   library learning already mines reusable abstractions from solved corpora under a
   compression objective. We're attempting that assembly for a free-text lesson store —
   gated honestly: if the shape index doesn't beat our own baseline retrieval on held-out
   lessons, it ships nothing. Recipe and sources: the knowledge-primitives record in
   [`research/reviewed/`](research/reviewed/).

## Contributing

Issues and PRs welcome — [`CONTRIBUTING.md`](CONTRIBUTING.md) explains the slice discipline (small change + its test + green gates), and [`AGENTS.md`](AGENTS.md) is the contract your *agent* reads. Good entry points: run the quickstart, then `py agent_cli.py discover` — every verb describes itself.

Writeups from the most salient research runs — the local-fleet build, the memory-that-measures-itself numbers, what 750 years of failed universal knowledge schemes teach an agent memory system — are published in [**Discussions**](https://github.com/balanced7/akashic-aurora/discussions) as they land.

## About this project

I started out writing a simple session logger. One thing led to another, and somehow I've ended up trying to build an agentic AI harness/ Self Improving Knowledgebase w/ Just In Time Context



I hope you find this project fascinating to poke around in — maybe even useful for your own work. If you'd like to use it, break it, or help make it better: let's connect!

— Daniel Ruban · [LinkedIn](https://www.linkedin.com/in/daniel-ruban-69873ab7/)

## License

[Apache License 2.0](LICENSE) — see also [`NOTICE`](NOTICE). © 2026 balanced7.
