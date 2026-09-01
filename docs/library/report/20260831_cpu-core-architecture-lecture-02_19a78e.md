---
akashic_id: art_20260831_cpu-core-architecture-lecture-02_19a78e
akashic_sha: f1239744472d
schema_version: 1
status: current
type: report
arc: unofficial-college
date: 2026-08-31
title: cpu-core-architecture-lecture-02
gist: "Lecture 02: the L1 hostage interrogated (constraint/escapes/history/cost/proportion), the perceptron at 5GHz, and why compression is prediction-proof"
visibility: fleet
body_type: markdown
seats: [claude]
category: [coordination, performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-31T23:46:51"
updated: "2026-08-31T23:46:51"
---
<!-- GENERATED PROJECTION of art_20260831_cpu-core-architecture-lecture-02_19a78e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# cpu-core-architecture-lecture-02

# The Hostage Negotiations

*The Unofficial College — Lecture 02. Delivered in-session 2026-08-29, on Daniil's five questions about the L1 limit ("what is the constraint of this limit? what would it take to break it? how did growth look like before it? What is the cost of making it bigger? what is the proper proportion for cache to execution to throughput to latency to workload type"), plus his asks on one-cycle perceptrons and whether random workloads like video compression pay a prediction penalty. Preserved verbatim. His five questions are, structurally, a computer-architecture sizing study: constraint → sensitivity → history → cost → balance.*

## The L1 hostage, interrogated

**The constraint, mechanically.** Programs run on virtual addresses — every process pretends it owns all of memory, and hardware translates virtual→physical through page tables, cached in a small thing called the **TLB** (a cache *of translations*). Translation only changes the *upper* bits of an address: within a 4KB page, the bottom 12 bits are identical in virtual and physical. The 4-cycle trick is a race: L1 starts its lookup using only those 12 untranslated bits *while* the TLB translates the rest in parallel, and the translated bits arrive just in time for the tag compare. The moment your cache needs bit 13 to pick a set, you must wait for the TLB *first* — serial, slower. So the index can only reach 4KB per way. Size = 4KB × ways. That's the whole hostage.

**What it takes to break it — all four escapes have shipped:**
1. **Bigger pages.** 16KB pages = 14 free bits = 4× headroom. Apple did exactly this on M-series — it's part of how the M1 fields a *128KB* L1d at ~3–4 cycles. They could do it because they owned the entire software stack and were starting ARM64 fresh. x86 can't easily, because forty years of software assumes 4KB. Sit with that: **the constraint was never silicon — it's a 1980s ABI contract.** The hostage-taker is software archaeology.
2. **More ways.** Zen 5's 12-way × 4KB = 48KB. Intel bought 48KB back in 2019 (Ice Lake) and *paid a cycle for it* — L1 went 4→5, and people argued about it for years, which tells you exactly what a cycle there is worth.
3. **Don't grow it — insert a floor.** Lion Cove: 48KB "L0" at ~4 cycles, then a 192KB "L1" at ~9. When you can't raise the ceiling, add a mezzanine (and rename all the levels, to reviewers' despair).
4. **Police the aliases.** Old Athlon shipped 64KB 2-way — over the lawful bound — by bolting on machinery to detect and evict virtual-address aliases. Paying the fine instead of obeying the law.

**How growth looked before the freeze:** 486: 8KB unified (1989) → Pentium: 8+8 split → PII/III: 16+16 → Athlon: 64+64 (1999, the outlaw) → Pentium 4: back DOWN to 8KB but 2-cycle (the speed-demon detour) → Core 2: 32+32 (2006) → frozen. Caches grew freely while clocks were low; then clocks 10×'d, wire delay started biting, VIPT became the discipline, and pages stayed 4KB. Three curves intersected around 2006 and L1 has been standing at the intersection ever since.

**The cost of bigger, in three currencies.** *Latency*: L1 load-to-use sits on every dependent-load chain in every program — pointer chases pay it serially — so +1 cycle costs low-single-digit % IPC *machine-wide*; architects will sacrifice enormous hit-rate to protect that number. *Power*: a set-associative L1 reads all N ways in parallel and throws away N−1 answers — 12-way means paying for 12 reads per load, billions of times a second (there's a mechanism called way *prediction* to fight this, because of course the fix is more prediction; everything in this machine is the same trick in a different hat). *Area*: SRAM next to the load units competes for the most expensive real estate on the die — the center of the core.

**The proportion question — there is no golden ratio, there's a method.** Three instruments: (1) **Working-set knees**: hit-rate-vs-size curves aren't smooth — workloads have plateaus (fits-in-32K, fits-in-2M, streams-everything). You size each level to catch a knee common in your *target* workloads; that's why server L3s are oceanic and client chips buy latency instead. (2) **Little's law** for the bandwidth axis: `data in flight = bandwidth × latency`. Want 400GB/s of streaming against 80ns memory? You need 32KB perpetually in flight — that single equation sizes miss buffers, prefetch depth, and how much MLP the ROB must expose. (3) **The strategy fork**: CPUs spend area so one thread never waits (caches, speculation); GPUs spend the same area on so many threads that waiting is free. Latency *avoidance* versus latency *hiding* — same physics, opposite proportions, and the workload picks the corner. "Cache to execution to throughput to latency to workload type" isn't answered by a ratio; it's answered by which of those two religions the workload converts you to.

## The perceptron, at 5GHz

The object is almost insultingly simple. Per branch (hashed by address): a row of small signed weights, one per bit of recent global history. History bits are ±1. Prediction = **the sign of the dot product** — and since multiplying by ±1 is just add-or-subtract, the whole "neural net" is an adder tree of small integers. No multiplies anywhere. Training, when the branch resolves: if the prediction was wrong — or right but *timid* (sum too close to zero) — nudge each weight toward what actually happened, saturating at the rails. The humble 2-bit counter, grown up and employed in machine learning.

**"How fast must it execute to be useful"** — the exact right question, and the answer is a courtroom. Something must steer fetch *every single cycle* or the pipeline starves, and the fancy predictor can't answer that fast. So there are two tiers: a dumb-fast predictor (BTB + simple tables) rules instantly, and the perceptron/TAGE apparatus delivers its verdict 2–3 cycles later — and if it *disagrees*, it redirects fetch, costing a 2–3 cycle bubble instead of the ~17-cycle flush. A snap judgment, then appellate review. The smart tier earns its area when `accuracy gained × 17 > override rate × bubble`. That inequality is the entire business case for intelligence in the frontend.

One more thing to savor: a single-layer perceptron is linearly separable only — it *provably cannot learn* "taken iff exactly one of the last two branches was taken." That's XOR. Minsky and Papert's 1969 objection to neural networks, alive in your CPU. And the industry's fix wasn't depth — no time for layers at 5GHz — it was a *committee*: pair the perceptron with TAGE, which brute-memorizes the nonlinear cases by context. The historical answer to the XOR problem turned out to be bureaucracy.

## The compression question is deeper than it looks

First the reframe: there's no mode-switch penalty, no "1 cycle for entering random-land." The cost is an expected value paid per branch, continuously: `mispredict rate × ~17`. A loop branch at 99.9% costs nothing; a coin-flip branch costs ~8.5 cycles *every time you meet it*, and code meets a branch every five instructions.

Video compression is the perfect specimen. A codec is two natures stapled together. The loops, DCTs, motion search: predictable control flow, and where the *data* would create branches, codec authors write **branchless** SIMD — compute both outcomes, blend with a mask. The escape from unpredictability is to *make the branch not exist*. But the entropy-coding stage (CABAC) is the opposite by construction: each decoded bit updates the context that decodes the *next* bit. It's the séance again — but in control flow. Serial by design, branching on maximum-entropy data. That's why hardware video blocks exist and why the entropy stage is famously the wall in every codec.

And here's the floor dropping out: **a predictor and a compressor are the same mathematical object.** Shannon says so. If a branch predictor beats 50% on your stream, it has found structure — which is *precisely the thing compression removes*. A perfectly compressed stream is indistinguishable from noise *by definition*, so entropy decode is the one workload no predictor will ever beat — not for lack of cleverness, but the way perpetual motion fails: lawfully. The machine's mature response to unpredictability is never "predict harder." It's *restructure so there's nothing to predict* (branchless, tables, SIMD) or *hand it to dedicated silicon*.

The recall corollary, for the house: split the planes like I and D caches; predict per-source with metered confidence (recall-feedback's useful/noise counters *are* saturating counters); and for the incompressible residue, don't predict — *index*. "Dynamic vs static facts" and "predictable vs random content" are the same question on two axes, and the answer is the same both times: meter it per-key, from observed history, and route by the measurement.

## One floor added to the marvel

Even the 5GHz isn't real. Boost is a control loop reading thermal and current sensors thousands of times a second, bidding frequency against headroom — the chip is its own SRE. The whole machine is lies all the way down, *with receipts at every layer*: renaming lies about registers, caching lies about distance, speculation lies about time, boost lies about the clock. The engineering miracle isn't any layer; it's that every layer keeps its interface contract while lying wildly about its internals.

## Teach-back — status: OPEN

> Why can no branch predictor ever beat entropy decoding — and what are the two lawful escape hatches?

*Daniil's answer, dated:*

## Descents ledger

- [x] TLBs and why 4KB pages are a tax — forced open early by the L1 constraint question
- [x] Perceptrons at cycle speed — this lecture
- [ ] SMT: one core, two threads — what's actually shared *(see Lecture 03's teach-back and its unusual resolution)*
- [ ] DRAM internals: banks, refresh, why "latency" is secretly five numbers
- [ ] Wide-and-slow vs narrow-and-fast at equal power (the Apple question)
