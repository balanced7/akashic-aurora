---
akashic_id: art_20260831_cpu-core-architecture-lecture-03_0267ae
akashic_sha: 55ab1921312a
schema_version: 1
status: current
type: report
arc: unofficial-college
date: 2026-08-31
title: cpu-core-architecture-lecture-03
gist: "Lecture 03: the rogues gallery of brutal workloads, chains vs queues (four walls, Littles law, roofline), and the two religions of latency"
visibility: fleet
body_type: markdown
seats: [claude]
category: [performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-31T23:46:52"
updated: "2026-08-31T23:46:52"
---
<!-- GENERATED PROJECTION of art_20260831_cpu-core-architecture-lecture-03_0267ae -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# cpu-core-architecture-lecture-03

# The Rogues' Gallery and the Two Religions

*The Unofficial College — Lecture 03. Delivered in-session 2026-08-29, on Daniil's ask: "what workload types are the most brutal to predict? What becomes the execution bottleneck and the throughput bottleneck? Can you explain hiding latency vs the other thing you said." Preserved verbatim. All three questions turn out to be the same question wearing different coats.*

## The rogues' gallery: what's brutal to predict, and why

One law generates the whole ranking: **brutality = how much the immediate future depends on data the machine hasn't seen yet.** A loop counter is clairvoyance — the future is arithmetic. A just-loaded value that decides the next branch *and* the next address is the séance. Rank by that, and the gallery assembles itself:

| Workload | Why it's brutal | What it starves |
|---|---|---|
| **Graph analytics** (BFS, PageRank) | random neighbor hops over GBs — addresses from data, branches on data, zero locality of any kind | memory latency, purely |
| **Databases / OLTP** | B-tree descent = pointer chase; hash probes = deliberate randomness; plus *huge code* footprints that blow out L1i and the BTB | memory latency **and** the frontend |
| **Interpreters** (hi, CPython) | the dispatch loop is one indirect branch whose target *is* the next bytecode — control flow made of data | bad speculation |
| **Entropy decode** (CABAC) | unpredictability by mathematical construction; each bit gates the next | the dependency chain itself |
| **Hash tables at scale** | a good hash function destroys locality *on purpose* — it's an anti-prefetcher by contract; bigger than L3 = one guaranteed miss per probe | memory latency |
| **Sparse algebra** (SpMV) | indices come from data → gathers; almost no math per byte moved | bandwidth |
| **Dense GEMM, video pixel loops** | *(for contrast)* counters and strides everywhere — clairvoyance | nothing; this is the machine's happy place |

Two footnotes with teeth. Crypto code is unpredictable-*data* but predictable-*flow* — branchless **by law**, because a branch on secret data leaks the secret through timing (the Spectre lesson, taken as a design commandment). And the interpreter row has a redemption arc: ITTAGE predictors got good enough to *learn bytecode sequences*, taming dispatch far better than folklore claims — there is literally a paper on this titled "Don't trust folklore," which under house doctrine makes it required reading.

## Chains vs queues: the two ways a pipeline dies

The distinction hiding inside "execution bottleneck vs throughput bottleneck." Every stall is one of two shapes:

- **Waiting on a chain** — a *latency* bottleneck. The critical path is serial: load → use → load → use. No amount of machinery helps, because the next step needs the previous answer. This is the séance's signature.
- **Waiting on a queue** — a *throughput* bottleneck. There's plenty of independent work, but a pipe is full: memory bandwidth, or the execution ports themselves. Governed by Little's law; fixable with more lanes, never with lower latency.

The profiler's version is the four-wall taxonomy (Intel calls it Top-Down): every issue slot either **retired** (real work — GEMM lives here, ~90%), was lost to **bad speculation** (flushed — interpreters, branchy data code), starved at the **frontend** (i-cache/BTB misses — databases, and famously the dominant tax in datacenter code per Google's warehouse-scale profiling), or stalled in the **backend** — which splits into *memory-bound* (chains, misses) and *core-bound* (queues, ports). The gallery's third column is just "which wall."

Now the single most illuminating number in the whole subject. Little's law: `achieved bandwidth = (outstanding misses × 64B) / latency`. A pure pointer-chaser sustains exactly **one** outstanding miss — the chain forbids more. At 80ns: 64B / 80ns = **0.8 GB/s**. Against a memory system offering ~60. A séance thread uses about **1–2% of the highway it's paying for** — not because the machine is slow, but because the workload only ever sends one car at a time. That's what "latency-bound" *means*. MLP is the multiplier: ten independent misses in flight = 8 GB/s, forty = the pipe itself becomes the wall, and you've crossed from chain-limited to queue-limited. Everything the ROB does, it does to raise that one number.

For the throughput side, the matching instrument is the **roofline**: count FLOPs per byte moved. A machine with 400 GFLOP/s and 50 GB/s breaks even at 8 FLOP/byte — GEMM reuses each byte O(N) times and lives above the ridge (compute-bound); SpMV manages ~0.2 and no cleverness will ever lift it off the bandwidth roof. You don't profile to *discover* this; you can compute it from the algorithm before writing a line.

## The two religions

Both are answers to the same number — DRAM is ~300 cycles away — and they are theologically opposite:

**Latency avoidance** (the CPU religion): *make the wait not happen.* Spend enormous area per thread — caches so data is near, prefetchers so it arrives pre-asked, speculation so certainty is never waited for — all to keep **one** thread's dependency chain moving. Optimizes the latency of a single life.

**Latency hiding** (the GPU religion): *let the wait happen; make it cost nothing.* When a warp stalls on memory, the scheduler swaps in another warp **next cycle** — and the context switch is free because nothing is saved or restored: every resident thread's registers live on-chip simultaneously, permanently partitioned. This is why a GPU's register file is *bigger than its L1 cache* — an inversion that looks insane until you see that resident thread state is the very capital latency-hiding runs on. With ~64 warps resident, a 400-cycle stall is invisible as long as someone's always ready. The latency never shrank; it's simply always overlapped with someone else's work.

The price sheet: hiding makes each individual thread pathetic and demands *abundant, independent* parallelism to feed the swap; avoidance buys a magnificent single thread but caps at whatever ILP and MLP one instruction stream can expose, at brutal area cost per thread. The workload picks the religion: ten million independent pixels → hide; one gnarly pointer chase → avoid. And the nuance on graphs: one séance defeats both religions, but a *wide* graph frontier is 100,000 independent séances — and hiding wins after all, by having them all in flight at once. Hiding doesn't need each chain to be fast; it needs many chains.

SMT is the CPU quietly attending the other church on weekends: two threads resident in one core so that one thread's stalls are filled with the other's work. Hiding-lite, using avoidance's hardware.

## Teach-back — status: RESOLVED, unusually

> SMT typically buys databases ~20–30% more throughput, and GEMM roughly 0% — sometimes negative. Why both numbers?

*Resolution: Daniil answered this one by accident on 2026-08-31, designing the top-half/bottom-half nudge architecture — "a low-cost way of replying while working on the main thread" IS the SMT insight: a stall-heavy thread leaves gaps a second cheap thread can fill (databases stall constantly → +30%), while a saturated thread leaves nothing to fill (GEMM retires ~90% → ~0%, and the second thread just fights for cache). The student designed the answer before looking it up. See atom art_20260831_attention-architecture-wakes-nudges-pric_bba04c, Part B.*

## Standing exam

Still open from Lecture 01: the linked list and the flat array, identical bytes, both resident in L2 — the array walk severalfold faster; name every mechanism. (The holder of this exam has been over-armed for it since the day it was set: dependent loads serialize where independent ones pipeline, and the stride prefetcher sees arithmetic but cannot see through a pointer.)
