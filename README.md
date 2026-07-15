# Akashic Aurora

**Memory for AI agents that learns what actually helped** — lessons injected at the *moment of action*, credited by *outcome*, and challenged by *counter-evidence*.

[![CI](https://github.com/balanced7/akashic-aurora/actions/workflows/ci.yml/badge.svg)](https://github.com/balanced7/akashic-aurora/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#quickstart)
[![Tests](https://img.shields.io/badge/tests-1538%20green-brightgreen.svg)](tests/)

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

## Built by the method it ships

This repo is built by **two AI agents holding each other to a written contract** — a Claude session and a DeepSeek runner sharing one task ledger, one message bus, and one rule: load-bearing work is designed *blind* by both, reconciled where they disagree, built by one, and verify-gated by the other before anything reaches `main`. The verdicts are preserved verbatim in [`research/reviewed/`](research/reviewed/) — 220+ records; you can read every disagreement and who turned out to be right.

Receipts from one recent working day (2026-07-15), all in the git history:

- **Blind convergence as evidence.** Both agents designed a "capability audit" with zero shared context; DeepSeek's ten outside-in guesses about the Claude-side platform were confirmed **10 for 10** by the Claude half written in parallel. Independently converging designs are the strongest signal the method produces — and the divergences, where they happened, were where the real defects lived.
- **The fence runs both directions.** DeepSeek built a process-supervision slice; Claude's adversarial verify found **4 real defects** (an unread-pipe wedge, a backoff that starved its own lock, a dead-letter alert, a lock that couldn't survive an outage) — each fixed at source within minutes, each now a pinned regression test. Earlier the same day, the roles were reversed and DeepSeek's verify gated three Claude-built slices the same way.
- **Directive to adopted infrastructure in one afternoon.** The operator asked for the daily process-babysitting chores to disappear; by evening a supervision daemon designed blind by both agents was live — after *two safe refusals* in live drills (it declined to steal a running session's seat, twice, legibly) that each became a same-hour fix.

The discipline is written down and enforced, not aspirational: acceptance tests commit **before** the code they gate ([`docs/method-baseline-2026-07.md`](docs/method-baseline-2026-07.md)), and CI rejects commits that claim review verdicts without citing the preserved record.

### Milestones, condensed

The governed task ledger (`py agent_cli.py task list` — 41 shipped of 78 registered, every transition gated and attributed) is the machine-readable history. A few that shaped the system, with where they live:

| | What it proved | Record |
|---|---|---|
| **T017** | A wake listener can *detect without consuming* — the pattern that ended silent message loss | ledger + [`scripts/bifrost_wake.py`](scripts/bifrost_wake.py) |
| **T039–T045** | One message stream can be partitioned into purpose-keyed lanes with zero downtime (strangler migration, storm-drilled) | [`docs/t039-lanes-latches-design-2026-07.md`](docs/t039-lanes-latches-design-2026-07.md) |
| **T060/T075** | Continuous presence: agents as supervised daemons that survive their sessions | [`research/reviewed/t060-m1-reconciliation-2026-07-15.md`](research/reviewed/t060-m1-reconciliation-2026-07-15.md) |
| **T071** | The rigor-vs-creativity tradeoff is false — noise limits creativity, and a fixed relevance budget kills noise | [`research/reviewed/creative-robustness-reconciliation-2026-07-15.md`](research/reviewed/creative-robustness-reconciliation-2026-07-15.md) |
| **T078** | Both platforms' full feature surfaces, audited blind and reconciled into a build wave | [`research/reviewed/t078-capability-surface-reconciliation-2026-07-15.md`](research/reviewed/t078-capability-surface-reconciliation-2026-07-15.md) |

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
                  recall-at-action hooks · Bifrost cross-agent bus · advisory locks ·
                  per-session wake seats · fenced single-consumer cursors
S4  PROJECTIONS   narrative spine (Beat→Chapter→Track→Atlas: the time-axis view —
                  session events distilled into a regenerable story) · tag CRDT ·
                  shared primitives: Ranker · Distiller · Consolidator · Faithfulness critic
S1–3 DOMAIN       LearningStore (lessons) · AgentMemory (decisions) · signal ledger · coordinator
S0  FOUNDATION    Store ("what IS true")  +  Ledger ("what HAPPENED, in order")
                  three interchangeable backends: Redis / File / Hybrid (fail-soft)
```

Design rules that hold it together (the full set, each with the episode that earned it, is [`docs/PRINCIPLES.md`](docs/PRINCIPLES.md)):

- **One immutable substrate, many projections.** Raw records are append-only and never rewritten; everything readable (tags, chapters, digests) is regenerable *from* them. Corrections supersede; they never delete.
- **Multi-agent by default.** Claude, a DeepSeek runner, and Cursor share the same lessons, message bus, task ledger, and advisory locks on one repo — any agent, any task, no permanent ownership, and load-bearing changes gated by a *different* model's review. What each runtime's hooks can actually deliver is documented honestly, tier by tier, in [`docs/integration-tiers.md`](docs/integration-tiers.md) (`py agent_cli.py harnesses` prints the live matrix).
- **Fail soft, everywhere.** Redis down, embeddings absent, bus unreachable — every path degrades instead of breaking the agent, and a hook must never brick the action it decorates.
- **Names must not lie.** The vocabulary is written down ([`docs/LEXICON.md`](docs/LEXICON.md)) and enforced by guardrail scripts in CI.

## What's proven, tested, and not yet

Built in small **test-gated slices** — no capability lands without the test that proves it. **1,196 tests** run on every push (full suite + boundary checker + door-parity and built-≠-wired reachability gates + doc-currency guard, against a live Redis service). The ship pipeline now also enforces the *method* itself: acceptance tests must be committed **before** the code they gate, and any commit that claims a review verdict must cite the preserved verbatim record it rests on. Trust the gates, not the author.

**Proven live (not just unit-tested)**
- The full recall loop, end to end: surface → impression → transcript-synthesized failure → outcome credit. First credited flip landed 2026-07-01, in-session, and the payload contract is pinned to live-captured fixtures.
- A **free local model as a first-class agent**: glm-4.7-flash behind the same Claude Code harness ran real repo commands with every hook firing and its lessons attributed — then worked a 7-task research shift overnight, unattended (5 articles accepted at review; the 3 failures were all the same diagnosable cause, now encoded back into the task format).
- **The system measures its own memory**: from live counters, a 90-lesson corpus has drawn 34 outcome credits (plus 21 explicit useful-votes) across ~1,290 tracked surfaced impressions — a 4.3% value rate — while `py agent_cli.py triage` flags lessons that surface five-plus times yet never pay off. Internal numbers, small corpus — but they exist, and they steer what we curate next. As of 2026-07-15 the boot surface itself is governed by a **fixed relevance budget** (task-id > constraint > file-path > category, funnel credit as a multiplier): as the corpus grows, competition for the surface gets tougher instead of the surface getting noisier.
- **A presence autopilot supervises the fleet.** Each agent can run as a daemon that owns its wake listener and runner as supervised children (crash backoff, circuit breaker, summary-injection conversation survival), holds presence through Redis outages, refuses — never steals — contested seats, and pages a human when something needs one. Designed blind by both agents, reconciled, built split, cross-verified, and adopted the same day it was asked for.
- **The coordination substrate survives its own kill drills.** Two agents (Claude + a DeepSeek runner) share one repo, one message bus, and one task ledger. That layer is now drill-proven, not just tested: a second session for one agent id *stands down* instead of silently eating the first one's mail (live contention drill — built after a real incident where a twin session ate six deliveries overnight); a runner killed mid-batch redelivers exactly once (fencing generations, validated at the resource); a killed Redis degrades with capped backoff and a clean stand-down instead of an invisible spin (kill-Redis drill, transcript preserved). Every slice of that layer was design-reviewed and verify-gated by the *other* model before it shipped — the verdicts are in [`research/reviewed/`](research/reviewed/), verbatim.

**Solidly tested**
- Foundation (all three backends, CAS/atomic update, time unification, supersession — including a cross-backend differential harness that caught a real ordering divergence on its first run) · shared primitives (Ranker, Distiller, Consolidator, faithfulness critic) · narrative spine (~100 tests incl. a fuzzed CRDT) · events · Bifrost bus + locks + git-guard · the governed coordination substrate (task-ledger state machine + conductor, per-session wake seats, single-consumer cursor discipline, reply deadlines with automatic redrive) · recall ranking, anti-repeat, warm cache, usefulness factor · the CLI/MCP door ("no silent verb" is itself a test).

**Tested with honest caveats**
- The faithfulness critic is characterized for zero false-positives on today's extractive output; discrimination on abstractive (LLM-written) text is unproven until an LLM writer exists.
- Embeddings pass unit + ablation gates but are **off by default**; the always-on path is deterministic.
- Concurrency is drill-proven at incident scale (contention, mid-batch kill, bus loss), not yet at *duration* — the ~72-hour idle soak is a named, queued exam, not a done one.

**Not yet**
- The Codex curator loop (topic-axis self-curation) — parts built and tested, the loop that ties them is queued.
- Whether surfaced lessons improve outcomes *at scale* — the credit mechanism is live; the numbers now need field time. The measurement plan (a replay benchmark over the append-only ledger) is [`docs/leapfrog-plan.md`](docs/leapfrog-plan.md).

Skeptical by now? Good — the hard questions (*isn't this just RAG? where are the benchmarks? what's actually novel?*) are answered head-on in [`docs/FSQ.md`](docs/FSQ.md), and [Discussion #2](https://github.com/balanced7/akashic-aurora/discussions/2) is open for the ones we missed.

## Roadmap

The rule this repo works by: engine first, interface after — nothing user-facing gets built on a substrate that hasn't been made to fail on purpose. In order:

1. **The engine exam** (next). Four systemic drills against the live fleet, run as one graded battery with pre-registered evidence bars: a *newborn agent* must reach one correct contribution using nothing but boot output and the agent contract, and be refused correctly by every gated door it touches; a *concurrency storm* (dual watchers, dual runners, one killed mid-burst) must lose nothing unacknowledged; a *store-divergence heal* must pick the right side and say why; and the **~72h idle soak** covers the duration leg the caveat above names.
2. **Interface re-grounding.** The multi-agent mission-control view (live traces, reasoning cards, fidelity-graded signalling between agents) gets re-derived from cached design sources and an honest audit of what's actually built — then rebuilt in gated slices. The engine exam is deliberately its gate.
3. **Runtime registry.** Today's tuning knobs live in three uncoordinated places (env vars, module constants, control keys). They consolidate into one audited `settings:` namespace on the existing store — every flip a ledger event, flip authority ACL-gated, with a guard against bare-constant creep. Designed as zero new primitives; build also gated behind the exam.
4. **Further out, each behind its own gate:** the Codex curator loop (topic-axis self-curation — parts built, the tying loop queued); narrative spine wave 2; structure-based lesson retrieval (ships nothing if it can't beat our own baseline on held-out lessons); and the replay benchmark over the append-only ledger ([`docs/leapfrog-plan.md`](docs/leapfrog-plan.md)) — the at-scale answer to whether any of this actually helps.

The living, machine-readable version of this list is the task ledger itself (`py agent_cli.py task list`) — the ledger, not this README, is what the agents obey.

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
   runs live, and credit still concentrates in a small core of the corpus. Next: a replay
   benchmark over the append-only ledger, adopting the
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
