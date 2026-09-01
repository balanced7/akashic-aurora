---
akashic_id: art_20260828_cpu-core-architecture-lecture-01_93b7ca
akashic_sha: 1f1716180d95
schema_version: 1
status: current
type: report
arc: unofficial-college
date: 2026-08-28
title: cpu-core-architecture-lecture-01
gist: "Core architecture taught whole: branch prediction, speculation, cache ladder, prefetch - one refusal to wait; teach-back open"
visibility: fleet
body_type: markdown
seats: [claude]
category: [memory]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-28T23:14:20"
updated: "2026-08-28T23:14:20"
---
<!-- GENERATED PROJECTION of art_20260828_cpu-core-architecture-lecture-01_93b7ca -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# cpu-core-architecture-lecture-01

# A Memory System with a Small Arithmetic Habit

*The Unofficial College — Lecture 01. Delivered in-session 2026-08-28, on Daniil's ask: "how speculative execution and prefetch work, branch prediction efficiency, and how and why different cache types are selected." Preserved verbatim; the teach-back at the end is still open.*

## The wall (why any of this exists)

Two numbers generate the entire zoo:

- An add takes **1 cycle**. A trip to DRAM takes **~300+** (60–100ns at 5GHz). That's the ratio of making coffee to driving to Colombia.
- Ordinary integer code hits a branch every **4–6 instructions** — the machine faces a fork in the road roughly once per sentence.

A naive core — fetch, execute, wait for memory, repeat — would use maybe 1% of its silicon's potential. Everything here (prediction, speculation, caches, prefetch) is a single shared refusal: **the machine refuses to wait**. Each mechanism is a different way of manufacturing certainty about the future — and keeping receipts in case the certainty was fake.

## Branch prediction: why 95% right is a disaster

Modern cores are pipelines ~15–20 stages deep and 6–8 instructions wide — an assembly line that only works if it knows what's coming. A branch is the line *not knowing*. Waiting for the answer means ~15–20 dead cycles, so the core guesses and barrels on.

The arithmetic that makes accuracy existential: 100 instructions ≈ 20 branches, and a good core clears those 100 in ~25 cycles. At 95% accuracy you eat one mispredict per 100 instructions — ~17 wasted cycles per 25 useful ones. **You just paid nearly double.** At 99% it's +14%. At 99.5%, +7%. The gap between 95 and 99 isn't four points, it's most of your performance — that's why the industry chases the next nine forever.

How the guessing evolved, each step fixing the last one's failure:

1. **Static**: backward branches are loops, predict taken. ~70%.
2. **1-bit memory** per branch (do what you did last time): fails every loop *twice* — once at the exit, once re-entering.
3. **2-bit hysteresis**: must be wrong twice to change its mind. ~90%, then plateaus, because a branch's own past isn't enough.
4. **The correlation insight**: branches predict *each other*. Keep a shift register of the last N outcomes, hash it with the branch address, index a table. Now `if (x < 0)` remembers that a related check three branches ago already revealed the answer. ~95%+.
5. **TAGE** (the current champion): many tables tracking geometrically longer histories — 8, 16, 32, up to hundreds of branches back — and the longest history with an opinion wins. Ships, in some variant, in everything.
6. **Zen's twist**: AMD's first-level predictor is a *hashed perceptron* — a dot-product of history bits against learned weights. The Keller-era Zen restart literally shipped a one-layer neural net that retrains every cycle, years before "AI inside" was a sticker.

Supporting cast: the **BTB** caches branch *targets*, because "taken" is useless unless you know where to fetch *this cycle*, before decode has even confirmed it's a branch; a **return-address stack** (a tiny shadow stack) makes call/return near-perfect; indirect branches (vtables, switch statements) get their own target predictor. What's left unpredictable is branches on genuinely random data — `if (x < threshold)` on noise is unlearnable, which is why branchless tricks and `cmov` exist.

## Speculative execution: gambling with receipts

Prediction is just an opinion. Speculation is *acting on it* — executing hundreds of instructions past an unresolved branch — while keeping everything undoable:

- **Register renaming**: your 16 visible registers are a public API, a polite fiction. Behind them sit a few hundred physical registers; every write gets a fresh one and a map tracks the fiction. Undo = restore the map from a checkpoint.
- **The reorder buffer (ROB)**: every in-flight instruction holds a slot in program order — **~450 on Zen 5, 576 on Intel's Lion Cove, ~630 on Apple's big cores**. Execution happens in whatever order operands allow; *retirement* happens strictly in order, and retirement is the moment a guess becomes truth.
- **The store buffer**: memory is the one thing you can't un-write, so stores wait in a holding pen and only touch the cache once their fate is certain.
- **Mispredict**: flush everyone younger than the branch, restore the map, refetch. That's the 15–20 cycle bill from earlier.

Here's the part most explanations bury: the *point* of a 500-deep window isn't reordering arithmetic. It's that when a load misses to DRAM for 300 cycles, the core keeps chewing on everything independent of it — **including finding more loads that also miss**. Two overlapped misses cost half as much as two serial ones. The ROB is best understood as a machine for overlapping memory misses; out-of-order execution is mostly a memory-latency-hiding device wearing a compute costume.

(One definitional line, since it's culturally famous: the flush restores the registers but not the cache's contents — the ghost work leaves measurable footprints in access timing. Reading those footprints is Spectre.)

## The cache ladder: physics, not preference

You cannot build memory that is both big and fast — this is physics, not budgeting. SRAM holds a bit with 6 actively-driven transistors: fast, power-hungry, area-hungry. DRAM holds it as a whisper of charge on one leaky capacitor: an order of magnitude denser, but slow to sense and needing constant refresh. And independently of cell type, **bigger arrays mean longer wires** — at 5GHz, a signal crossing a few millimeters of die eats cycles just commuting. So every level is a different point on the same tradeoff curve, and you bet on locality to make the ladder behave like one big fast memory:

| Level | Size | Latency | What it really is |
|---|---|---|---|
| Registers | ~KBs (physical) | 0–1 cyc | the working set of *right now* |
| L1 (split I / D) | 32–48KB each | ~4 cyc | reflexes |
| L2 | 1–3MB | ~14 cyc | private per-core overflow |
| L3 | 32–96MB | ~45 cyc | shared; on AMD, a victim cache |
| DRAM | GBs | ~300+ cyc | the slow ocean |

The design choices, each with its *why*:

- **L1 is split** because instruction fetch is streaming and read-only while data is random and written — different access patterns, different ports, physically different neighborhoods of the die. Splitting doubles bandwidth for free.
- **L1 has been frozen at 32–48KB for 15 years** while everything else ballooned — ever notice that on spec sheets? It's a hostage situation: to overlap address translation with the lookup (VIPT), the index bits must come from the untranslated page offset, capping size at page size × associativity. 4KB × 8-way = 32KB; Zen 5 went 12-way precisely to reach 48KB. L1's size is chained to a page-size decision from the 1990s.
- **Lines are 64 bytes**: the quantum of the memory system. Touch one byte, ship 64 — spatial locality baked into the fabric (Apple uses 128). The dark side: two cores writing *different* bytes of the *same* line makes it ping-pong between them — false sharing, the same family of cliff as the measured 251µs→8,266µs at 20 threads.
- **Inclusive vs exclusive**: Intel's classic L3 holds copies of everything in the L1/L2s — wasteful, but coherence checks can stop at L3. AMD's L3 is a **victim cache**, filled only by L2 evictions — no duplication, more effective capacity. That design is what makes **V-Cache** pay: glue +64MB of pure SRAM on top, because game working sets are 40–100MB of pointer soup sitting exactly in the gap between 32MB and DRAM. (Zen 3/4 paid clocks for it — cache die on top, thermals; Zen 5 flipped the stack, cache underneath, penalty gone.)
- **Replacement**: small caches use pseudo-LRU, but L3s use re-reference prediction (RRIP-family), because under plain LRU one streaming scan would flush the entire cache to store bytes it will never see again — scan resistance, the same eviction problem a promoted tier has when a bulk import walks through.
- **Coherence**: 8–16 cores with private caches means the same line lives in many places, so hardware runs MESI: to *write*, a core must first own the line exclusively, which invalidates every other copy. "Dynamic facts need coherence" — this is that, literally, in metal.

## Prefetch: the offense

Caches only pay on the *second* touch. Cold misses and long streams still cost 300 cycles each — unless the machine fetches the future before you ask. Prefetchers watch address patterns per load-instruction and per memory region:

- **Stride**: detects `a[i]` walks with any constant step, locks on, runs ahead.
- **Stream**: tracks multiple concurrent sequences, running up to ~20 lines ahead when bandwidth allows.
- **Spatial/region**: learns a structure's footprint bitmap ("this code touches offsets 0, 16, 128") and replays it on next visit.

And the thing that defeats all of them: **pointer chasing**. The next address lives *inside* data you haven't received — a linked-list walk is a séance where you can't ask where the next node lives until the current ghost answers. Dependent loads serialize, miss-overlap dies, and the prefetcher is blind through the indirection. This is the single deepest reason contiguous arrays beat linked structures.

Prefetching is also a genuine gamble: every guess spends real bandwidth and a real cache slot, and a wrong guess **evicts truth to store fiction**. A prefetch can fail by being wrong, late (useless), or *early* (evicted before use) — so prefetchers meter their own accuracy and throttle when they're cold.

## The landing

Zoom out and the shape is: a modern core is a **speculation engine strapped to a memory hierarchy** — one half manufactures guesses (predictor, prefetcher), the other half makes guessing safe (rename, ROB, store buffer) or affordable (the SRAM ladder). The actual ALUs are a rounding error on the die. A computer is mostly a memory system with a small arithmetic habit.

And the organs have been built here before: recall-at-action is an IP-keyed prefetcher, "cache the address, not the value" is how hardware treats volatile data too (own it, don't copy it), and RRIP's scan-resistance is the promoted-tier eviction problem. Same organs, different physics — the store's DRAM wall is a context window.

## Teach-back — status: OPEN

Predict-before-look. Answer in your own words before looking anything up:

> A linked list and a flat array hold identical bytes, both fully resident in L2 — the array walk is still several times faster. You now own every mechanism needed to explain why. Name them.

*Daniil's answer, dated:*

## Next descents

- [ ] TLBs, and why 4KB pages are a tax
- [ ] SMT: one core, two threads — what's actually shared
- [ ] Wide-and-slow vs narrow-and-fast at equal power (the Apple question)
- [ ] DRAM internals: banks, refresh, and why "latency" is secretly five numbers
