# Akashic Aurora

**Memory for AI agents that learns what actually helped** — lessons injected at the *moment of action*, credited by *outcome*, and challenged by *counter-evidence*.

[![CI](https://github.com/balanced7/akashic-aurora/actions/workflows/ci.yml/badge.svg)](https://github.com/balanced7/akashic-aurora/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](#quickstart)
[![Tests](https://img.shields.io/badge/tests-499%20green-brightgreen.svg)](tests/)

Most agent memory answers *"what did we store?"* This project answers a harder question: **did remembering it change the result?**

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

That `helped` counter feeds back into ranking: lessons with a track record rise; lessons surfaced often but never useful decay. The system runs on itself — the agents building this repo use it while building it, and the examples above are from that work, unedited.

## Quickstart

```bash
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
S4  PROJECTIONS   narrative spine (Beat→Chapter→Track→Atlas) · tag-governance CRDT ·
                  shared primitives: Ranker · Distiller · Consolidator · Faithfulness critic
S1–3 DOMAIN       LearningStore (lessons) · AgentMemory (decisions) · signal ledger · coordinator
S0  FOUNDATION    Store ("what IS true")  +  Ledger ("what HAPPENED, in order")
                  three interchangeable backends: Redis / File / Hybrid (fail-soft)
```

Design rules that hold it together:

- **One immutable substrate, many projections.** Raw records are append-only and never rewritten; everything readable (tags, chapters, digests) is regenerable *from* them. Corrections supersede; they never delete.
- **Multi-agent by default.** Claude and Cursor share the same lessons, message bus, and advisory locks on one repo — any agent, any task, no permanent ownership.
- **Fail soft, everywhere.** Redis down, embeddings absent, bus unreachable — every path degrades instead of breaking the agent, and a hook must never brick the action it decorates.
- **Names must not lie.** The vocabulary is written down ([`docs/LEXICON.md`](docs/LEXICON.md)) and enforced by guardrail scripts in CI.

## What's proven, tested, and not yet

Built in small **test-gated slices** — no capability lands without the test that proves it. **499 tests** run on every push (full suite + boundary checker + doc-freshness guard, against a live Redis service).

**Proven live (not just unit-tested)**
- The full recall loop, end to end: surface → impression → transcript-synthesized failure → outcome credit. First credited flip landed 2026-07-01, in-session, and the payload contract is pinned to live-captured fixtures.

**Solidly tested**
- Foundation (all three backends, CAS/atomic update, time unification, supersession) · shared primitives (Ranker, Distiller, Consolidator, faithfulness critic) · narrative spine (~100 tests incl. a fuzzed CRDT) · events · Bifrost bus + locks + git-guard · recall ranking, anti-repeat, warm cache, usefulness factor · the CLI/MCP door ("no silent verb" is itself a test).

**Tested with honest caveats**
- The faithfulness critic is characterized for zero false-positives on today's extractive output; discrimination on abstractive (LLM-written) text is unproven until an LLM writer exists.
- Embeddings pass unit + ablation gates but are **off by default**; the always-on path is deterministic.
- Concurrency mechanisms are unit-tested; a sustained two-process race at scale is not continuously exercised.

**Not yet**
- The Codex curator loop (topic-axis self-curation) — parts built and tested, the loop that ties them is queued.
- Whether surfaced lessons improve outcomes *at scale* — the credit mechanism is live; the numbers now need field time. The measurement plan (a replay benchmark over the append-only ledger) is [`docs/leapfrog-plan.md`](docs/leapfrog-plan.md).

## Where this is going

The field measures memory by retrieval quality. Nobody measures **causal memory utility** — *did this memory change the action and improve the outcome?* — because that takes action-time injection, an outcome ledger, and a credit loop all at once. All three are live here. The roadmap ([`docs/leapfrog-plan.md`](docs/leapfrog-plan.md), [`docs/ROADMAP.md`](docs/ROADMAP.md)):

1. **Grow the corpus** — capture lessons as a byproduct of work, not a chore (just-in-time prompts at the exact fail→success instant the hook already detects).
2. **Ledger Replay Bench** — replay recorded sessions with memory off / at session-start / at action-time and publish the outcome deltas, reproducibly.
3. **Dialectical recall v2** — a budget-bounded semantic gate for counter-evidence (yardstick already in the test suite).
4. **Local-first judges** — near-zero-marginal-cost consolidation and critique on local models.

## Contributing

Issues and PRs welcome — [`CONTRIBUTING.md`](CONTRIBUTING.md) explains the slice discipline (small change + its test + green gates), and [`AGENTS.md`](AGENTS.md) is the contract your *agent* reads. Good entry points: run the quickstart, then `py agent_cli.py discover` — every verb describes itself.

## About this project

I started out writing a simple session logger. One thing led to another, and somehow I've ended up building an agentic AI harness and knowledge base.

There's a lot I don't know yet. I'm not a professional programmer — I'm learning this field piece by piece, and this project is how: directing and steering state-of-the-art models to see if I can't make something special. The agents write most of the code. Since I can't personally vouch for every line, the rules are strict instead: nothing lands without a test, the full suite runs in CI on every push, and automated checks enforce the architecture. Trust the gates, not the author.

I hope you find it fascinating to poke around in — maybe even useful for your own work. If you'd like to use it, break it, or help make it better: let's connect.

— Daniel Ruban · [LinkedIn](https://www.linkedin.com/in/daniel-ruban-69873ab7/)

## The name

- **Akasha** — Sanskrit, the *aether*: the medium said to hold the record of everything. Here: the immutable, append-only substrate (Ledger + Store). The record is sacred; it is never rewritten.
- **Aurora** — the light that dawns across that sky. Here: the self-organizing knowledge that emerges over the record — ranked, distilled, recalled at the right instant.

*Order emerging luminously from the total record. Anti-entropy as a dawn that keeps coming.*

## License

[Apache License 2.0](LICENSE) — see also [`NOTICE`](NOTICE). © 2026 balanced7.
