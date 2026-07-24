---
akashic_id: art_20260710_source-pierre-zemb-diving-into-foundatio_f16884
akashic_sha: 20fd3b4232ac
status: draft
type: design
date: 2026-07-10
title: "SOURCE: Pierre Zemb, \"Diving into FoundationDB's Simulation Framework\""
gist: "# SOURCE: Pierre Zemb, \"Diving into FoundationDB's Simulation Framework\" # URL: https://pierrezemb.fr/posts/diving-into-foundationdb-simulat"
tenant: solo
visibility: fleet
seats: []
category: []
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:31:52"
updated: "2026-07-10T23:31:52"
---
<!-- GENERATED PROJECTION of art_20260710_source-pierre-zemb-diving-into-foundatio_f16884 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: Pierre Zemb, "Diving into FoundationDB's Simulation Framework"

# SOURCE: Pierre Zemb, "Diving into FoundationDB's Simulation Framework"
# URL: https://pierrezemb.fr/posts/diving-into-foundationdb-simulation/
# Neutral extraction (claude, 2026-07-10). LOCAL READING COPY -- gitignored, never committed.

## Core Architecture

FoundationDB runs identical production code in simulation by swapping interface implementations. A global g_network pointer holds an INetwork interface -- Net2 for production (real TCP via Boost.ASIO) or Sim2 for simulation (in-memory buffers). Network operations become memory operations with deterministic delays from deterministicRandom(), a seeded PRNG replacing all randomness sources.

## Single-Threaded Event Loop

The simulator executes hundreds of concurrent actors in one thread through cooperative multitasking. When actors wait() on futures, they suspend and return control to the event loop. Once all actors block: the loop identifies the next scheduled event, advances the simulated clock to that timestamp, resumes waiting actors. This enables time compression -- "years of uptime in seconds of testing." Same seed produces identical execution paths and timing.

## Flow: Actor Model

Flow is a custom C++ actor framework (predating Rust async/await). ACTOR-marked functions use wait() to pause until futures complete; the state keyword preserves variables across waits. Compiles into state machines via actorcompiler.h.

## BUGGIFY Chaos Injection

BUGGIFY points scattered throughout the codebase fire at fixed probabilities during simulation only:
- BUGGIFY_WITH_PROB(0.01) fires 1% of the time (deterministically, per seed)
- Common usage: wait(BUGGIFY ? Never() : normalOperation()) -- Never() never completes, forcing timeout branches
- Timeout knobs shrink dramatically under BUGGIFY (e.g., 60s -> 0.1s), making legitimate operations far more likely to trigger timeout paths

The synergy creates combinatorial explosion: hundreds of randomized knobs generate thousands of different operating environments per test run. "Each BUGGIFY-enabled test run picks a different configuration: maybe connection monitors are 4x slower, but file I/O is using 32KB blocks, and cache size is 1000 entries."

## Simulated Cluster and Failure Injection

SimulatedCluster builds entire distributed systems in memory with configurable topology (1-5 datacenters, variable machines, different storage engines). Each machine boots actual fdbserver code (not mocks) connecting through simulated network. "75% of the time when BUGGIFY is enabled, a rebooting machine gets random disks from the datacenter pool."

Injected failure classes: network partitions (clogging/disconnection), process crashes (KillInstantly / RebootAndDelete with fresh empty disks), disk swaps, bit flips, slow I/O (AsyncFileNonDurable), forced timeout triggers (coordinator elections, proxy-to-TLog failures).

## Workloads: Verification Patterns

Four phases: SETUP -> EXECUTION (concurrent actors generate transactions) -> CHECK (verify invariants after chaos) -> METRICS.

Three correctness verification patterns:
1. **Reference implementation:** mirror operations in a simple in-memory model (std::map), compare with FDB state in CHECK.
2. **Operation logging:** log every operation to a separate keyspace during execution; replay during CHECK; compare computed final state with actual state.
3. **Invariant tracking:** maintain mathematical invariants that break if isolation fails. Example -- Cycle workload: random edge swaps in a directed graph must preserve exactly one ring of N nodes; CHECK walks the graph.

## Scale and Reproducibility

"After roughly one trillion CPU-hours of simulation testing, FoundationDB has been stress-tested under conditions far worse than any production environment." Every merge request triggers hundreds of thousands of simulation tests; deterministic seeds guarantee reproducibility of any failure.

## Developer Workflow

Simulation as automated CI/CD; early FoundationDB practice allowed automatic merge if simulation passed, without human code review. Prebuilt binaries run simulation via TOML workload files; JSON trace logs capture event timelines for post-mortem.
