---
akashic_id: art_20260901_cpu-core-architecture-walk-01-v2_40eb4b
akashic_sha: 0f1bf9a13b40
schema_version: 1
status: current
type: report
arc: unofficial-college
date: 2026-09-01
title: cpu-core-architecture-walk-01-v2
gist: "Walk 01 second edition: survived its own audit -- 89 claims, 91 fetched sources, 45 confirmed 25 sharpened 5 corrected 0 unsupported; errata in the open"
visibility: fleet
body_type: markdown
seats: [claude]
category: [migration, memory, audit]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-01T03:53:55"
updated: "2026-09-01T03:53:55"
---
<!-- GENERATED PROJECTION of art_20260901_cpu-core-architecture-walk-01-v2_40eb4b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# cpu-core-architecture-walk-01-v2

# A Memory System with a Small Arithmetic Habit

*Forest Walks · Walk 01, second edition. The first edition of this walk was written from working knowledge; this one survived its own audit — every factual claim was checked against live-fetched sources by a 54-agent verification fleet (89 claims censused; 45 confirmed, 25 sharpened, 5 corrected, 0 left unsupported; 91 sources fetched and quoted). The corrections are listed at the end, because a publication that hides its errata is a publication practicing for bigger lies. Predict before you look; exam at the end.*

## The wall (why any of this exists)

Two numbers generate the entire zoo:

- An integer add takes **1 cycle** — and modern cores sustain **four of them per cycle** [1][2]. A trip to DRAM takes **~400 cycles on a tuned desktop, ~600 on a server** (73.35 ns measured on Zen 4 with DDR5-6000; ~120 ns on server platforms) [3][4]. During one memory round trip, the core could in principle retire **about 1,600 adds**. That's the ratio of making coffee to driving to Colombia.
- Ordinary code hits a branch every **~5.3 instructions** [9] — a fork in the road roughly once per sentence.

And here is the wall's cruelest property: **it does not move.** A 2024 Ryzen 9950X with DDR5-6000 "is just about able to match a Core i7-4770 with DDR3-1333" on memory latency [5] — a 2013 chip. Eleven years, three DDR generations, zero nanoseconds of progress. Nanoseconds are physics; only your clock speed decides how many *cycles* of your life they cost.

A naive core — fetch, execute, wait for memory, repeat — would pay a full round trip per miss and crawl at a fraction of a percent of its own throughput ceiling (derivable from the numbers above). But don't file that as a strawman: **even with the entire zoo** — three cache levels, prefetchers, 500-deep speculation windows — Google measured its warehouse fleet stalling **50–60% of cycles on data-cache misses**, averaging around one instruction per cycle against 6-to-8-wide hardware [6][16]. The naive core isn't a hypothetical; it's what every real core degrades toward the moment locality fails. (One sentence of honesty owed to history: the famous 1995 "memory wall" extrapolation assumed fixed miss rates, and cache-friendly programs *did* keep scaling [7]. The wall is a tax on pointer-chasing workloads, not a universal ceiling. This series is largely about who pays the tax and how the machine dodges it.)

There is also an energy version of this story, and it's where this walk's title comes from: on a measured 28nm core, an integer add *instruction* costs roughly **4000× the energy of the add itself** [8] — the other 3999 parts pay for fetching, decoding, renaming, and scheduling it. Arithmetic is nearly free; *deciding what arithmetic to do, and getting the data to it,* is the machine. Everything you named — prediction, speculation, caches, prefetch — is a single shared refusal: **the machine refuses to wait.**

## Branch prediction: why 95% right is a disaster

Modern cores are pipelines 15–20 stages deep [11] and 6-to-8 instructions wide [12][13][14] — an assembly line that only works if it knows what's coming. A branch is the line *not knowing*. Waiting means dead cycles, so the core guesses and barrels on — and a wrong guess costs a flush: AMD's own optimization guide states **11–18 cycles, commonly 13–16** for Zen 4 [12]. (There are actually *two* penalties hiding under "branch cost": the full mispredict flush, and a smaller ~7-cycle "resteer" when a branch predicts correctly but its target missed the BTB [15][11]. The pipeline's depth is not published — it's *inferred* from these penalties, which tells you something about how the industry communicates.)

The arithmetic that makes accuracy existential, computed honestly this time: code branches every ~5.3 instructions [9], and real cores average **2-to-3 IPC on good code** — measured SPEC averages sit near 1.7 on older wide cores [9][16], not the marketing-width 8. So 100 instructions ≈ 40 cycles of work carrying ~19 branches. At 95% accuracy, that's about one flush per hundred instructions — **roughly a third of your runtime burned on wrong guesses**. At 99%, the burn drops to ~7%; at 99.5%, ~3.5%. The gap between 95 and 99 isn't four points — it's most of a core's worth of performance, which is why the industry chases the next nine forever.

How the guessing evolved, each step fixing the last one's failure:

1. **Static**: backward branches are loops, predict taken. Roughly 70% territory [17][18].
2. **1-bit memory** per branch: fails every loop *twice* — once leaving, once re-entering [19][20].
3. **2-bit hysteresis**: must be wrong twice to change its mind [11][21][22]. Better — then it plateaus, because a branch's own past isn't enough.
4. **The correlation insight**: branches predict *each other*. Keep a history register, hash it with the branch address, index a table [17][21]. Now `if (x < 0)` remembers that a related check three branches ago already revealed the answer.
5. **TAGE**: many tables tracking geometrically longer histories — the longest history with an opinion wins. TAGE-family predictors won the Championship Branch Prediction contests from 2006 through 2016 [23][24][26], and they verifiably ship: AMD disclosed TAGE from Zen 2 onward [27]. But honesty about the record: vendors rarely disclose, and Samsung's Exynos cores shipped *perceptron* predictors instead [28] — "the champion" is documented; "in everything" was folklore, and this walk no longer says it.
6. **The perceptron**: a one-layer neural net as a branch predictor — history bits as ±1 inputs, small signed weights, prediction = the sign of the dot product, which in hardware is just an adder tree [29]. It trains when it mispredicts or wins too timidly, nudging weights toward what happened. And AMD *shipped it* — then said so out loud: the 2016 Ryzen launch marketed SenseMI "Neural Net Prediction" as "an artificial intelligence neural network that learns to predict" [33][34], six years before AI was a sticker on everything. Credit where the record puts it: Zen's chief architect Mike Clark and team, from the Keller-era Zen restart [29][33]. The perceptron's known blind spot is linear separability — it provably cannot learn XOR-shaped branch behavior [29] — and the industry's fix wasn't depth; it was a *committee* (pair it with TAGE-style history tables). The historical answer to the XOR problem turned out to be bureaucracy.

Supporting cast, one line each: the **BTB** caches branch *targets*, because "taken" is useless unless you know where to fetch *this cycle* [11][12][37]; a **return-address stack** makes call/return near-perfect [11][12]; indirect branches get their own target predictor [12][38][39]. And what remains unpredictable is sharper than "random data": Agner's tables show a branch that's merely *biased* — taken 45/55 — still mispredicts ~49% of the time; even 25/75 costs ~30% [11]. **Predictability comes from pattern, not proportion.** On true coin flips, the predictor's own pattern-hunting makes it slightly worse than chance — which is why branchless tricks and `cmov` exist [11][12].

## Speculative execution: gambling with receipts

Prediction is an opinion. Speculation is *acting on it* — executing hundreds of instructions past an unresolved branch — while keeping everything undoable:

- **Register renaming**: the visible registers are a public API, a polite fiction; behind them sit hundreds of physical registers, and a map tracks the truth [41][42][43][11][44][45]. How live is this fiction? Intel is currently *renegotiating it in public*: APX doubles the visible registers from 16 to 32, claiming ~10% fewer loads and ~20% fewer stores [41] — proof the lie was load-bearing and slightly too small.
- **The reorder buffer**: every in-flight instruction holds a slot in program order — **exactly 448 on Zen 5** (SMT splits it at precisely 224 [40][42]), **576 on Lion Cove** [43][46], **~630 measured on Apple's big cores** [47][48]. Execution happens in whatever order operands allow; *retirement* is strictly in order [11][48] — the commit point where a guess becomes truth.
- **The store buffer**: memory is the thing you can't un-write, so stores wait in a holding pen until their fate is certain [5][11][47].
- **Mispredict**: flush everyone younger, restore the map, refetch [11][44]. The 11-18-cycle bill from earlier.

And the part most explanations bury: the *point* of a 500-deep window isn't reordering arithmetic — it's **memory-level parallelism**. When a load misses for 400 cycles, the window keeps hunting for *other independent misses* to overlap with it. Apple's Firestorm sustains on the order of **150 outstanding loads** [47]; and the cleanest proof of what windows are *for*: a classic result shows a 128-entry window with runahead execution performing within ~1% of a 384-entry window [49] — window depth is worth exactly the miss-overlap it buys, and nothing more. Out-of-order execution is a memory-latency-hiding device wearing a compute costume [43][44][49].

(One definitional line, since it's culturally famous: the flush restores the registers but not the cache's contents — the ghost work leaves footprints measurable by timing, and reading those footprints is Spectre [51].)

## The cache ladder: physics, not preference

You cannot build memory that is both big and fast — physics, not budgeting [52][53][54]. SRAM holds a bit with six actively-driven transistors: fast, area-hungry [52][55][56]. DRAM holds it as charge on one transistor and one capacitor: roughly an **order of magnitude denser**, but slower to sense and in need of constant refresh [55][57][58]. And independently of cell type, **bigger arrays mean longer wires** — at 5GHz, distance is cycles [53][54]. So you build a ladder and bet on locality:

| Level | Size | Latency* | What it really is |
|---|---|---|---|
| Registers | ~KBs physical | 0–1 cyc | the working set of *right now* [11][12][37] |
| L1 (split I / D) | 32–48KB each | ~4 cyc | reflexes [11][12][46] |
| L2 | 1–3MB | ~14 cyc | private overflow [11][12][46] |
| L3 | 32–96MB | ~40–50 cyc | shared; on AMD, a victim cache [3][11][12] |
| DRAM | GBs | ~400+ cyc | the slow ocean [3][4] |

*\*The yardstick matters: these are integer load-to-use figures; the same L1 hit costs 7–8 cycles for floating-point consumers, and complex addressing adds a cycle [12]. A latency table without its yardstick is an invitation to argue.*

The design choices, each with its *why*:

- **L1 is split** because instruction fetch streams read-only while data thrashes read-write — different patterns, different ports [61][62]. But the audit demands honesty about "free": the split buys its bandwidth at the price of a **rigid I/D partition and a deleted guarantee** — the I-cache is not coherent with the D-cache, so self-modifying code lost a promise it used to have [62]. The split is a trade, not a freebie.
- **L1 has been frozen at 32–48KB for eighteen years** — Core 2's 32KB shipped in 2006 [11][13][61]. The hostage mechanism: to overlap address translation with the lookup (VIPT), the index must come from untranslated page-offset bits, capping size at page size × associativity [11][63][65]. And the page size is **4KB because the Intel 386 said so in 1985** [69] — the hostage-taker is a *forty-year-old* ABI decision, older than most people reading this. Escapes, all shipped: bigger pages (Apple's 16KB pages underwrite the M1's 128KB L1 [66][71][72]), more ways (Zen 5: 12-way × 4KB = 48KB at 4 cycles [42][65][67]), paying the cycle (Ice Lake took 48KB at 5 cycles and reviewers argued for years), or **adding a mezzanine instead of raising the ceiling** — Lion Cove inserted a 192KB/~9-cycle level between its 48KB L0 and its L2 [13][46]. When a gap gets too wide, architects build a floor in the middle.
- **Lines are 64 bytes** on x86 [11][70][71]; Apple uses 128 [66][71][72]. Touch a byte, ship the line — spatial locality baked into the fabric. The dark side is **false sharing**: two cores writing different bytes of one line make it ping-pong. Drepper's published measurements show the cliff at 390/734/1147% overhead for 2/3/4 threads [73][74]; this lab's own bench found a mean 33× degradation at 20 threads with a p99 tail of **87×** [75]. The line is the unit of truth between cores, and truth is expensive when contended.
- **Coherence**: private caches mean the same line lives in many places, so hardware enforces a named invariant — *single writer or many readers* (SWMR) — via MESI-family protocols (shipping silicon mostly runs MOESI variants) [70][73][76]. To write, a core must own the line exclusively, invalidating other copies. The nuance the first edition missed: coherence only taxes *sharing* — the E→M upgrade on a line you own is silent and free [76]. The protocol bills you for contention, not for ownership.
- **Inclusive vs victim**: Intel's classic inclusive L3 duplicates inner levels so coherence checks stop at L3 [77][78]; AMD's L3 is a victim cache filled by L2 evictions [3][12]. That design is what makes **V-Cache** rational: games leave a 32MB L3 with only ~55–68% demand-load hit rates, and trace analysis finds **~96MB configurations near-optimal for game-like miss patterns** [40][80][81] — so AMD stacks +64MB of pure SRAM into exactly that gap [12][79][80]. The measured costs and the fix: first-generation X3D parts clocked ~5.2GHz against ~5.5+ for their flat siblings [79][82]; Zen 5 moved the cache *under* the compute die and the penalty largely vanished [82]. And the honest counterweight the fanbase version omits: workloads whose working sets don't live in that specific gap see almost nothing from the extra cache [80].
- **Replacement**: small caches run pseudo-LRU [11][83]. L3s run scan-resistant re-reference policies (RRIP) [84][85] — and the first edition misstated *why*: a pure stream doesn't "flush" anything meaningful (for a stream, replacement policy is irrelevant); the damage is a scan evicting a *resident working set* in mixed patterns [83][84]. The RRIP paper's own motivating workloads are PC games by name — *halflife2*, *halo* [84]. The scan-resistance literature and the V-Cache business case are the same observation, fifteen years apart.

## Prefetch: the offense

Caches only pay from the second touch [3][86]. Prefetchers watch access patterns and fetch the future — and the audit trimmed this section's folklore down to what ships:

- **Stride prefetchers** track per-instruction constant strides — with real limits: stride caps around 2KB and prefetching stops at 4K page boundaries on documented cores [12][87].
- **Stream prefetchers** run ahead of sequential access — Intel documents its streamer running up to 20 lines ahead [87].
- **Region/spatial prefetchers**: the elegant "footprint bitmap replay" design is *research* (SMS); shipping silicon is humbler — buddy-line completion and AMD's L1 region prefetcher are the production cousins [12][87][88]. The lecture-hall version and the die-shot version are different machines, and this walk now says which is which.

What defeats them all: **pointer chasing**. The next address lives *inside* data not yet received; dependent loads serialize, and the prefetcher is blind through indirection [89][90]. This is the deepest reason contiguous layouts beat linked structures — and the reason memory-latency benchmarks are *built* from pointer chases: it's the one pattern hardware cannot legally cheat. I say "legally" because Apple tried the illegal version: a data-memory-dependent prefetcher that interprets memory *values* as candidate addresses — the only way to see through indirection — and it became **GoFetch**, a cryptographic key-extraction channel [89]. The prefetcher that finally chased pointers chased them straight through a security boundary.

Prefetching is also a control system, not a party trick: every guess spends bandwidth and a cache slot; a wrong guess **evicts truth to store fiction — and pays the bandwidth twice** (once fetching the fiction, once re-fetching the evicted truth) [12][86]. An unthrottled prefetcher is a positive feedback loop — pollution creates misses, misses create prefetches — and the feedback-directed fix is negative feedback: measured accuracy throttles aggression, buying in one classic result **+6.5% performance on 18.7% *less* bandwidth** [86][91]. The house style of this lab approves: the component meters its own usefulness and demotes itself when it stops paying.

## The landing

Zoom out. A modern core is a **speculation engine strapped to a memory hierarchy** — one half manufactures guesses (predictor, prefetcher), the other half makes guessing safe (rename, ROB, store buffer) or affordable (the SRAM ladder). The energy ledger says it plainest: the arithmetic is ~1/4000th of the instruction [8]; "arithmetic is free and global memory is expensive" is a maxim with a DOI attached. A computer is mostly a memory system with a small arithmetic habit — and now that sentence carries a citation.

## Teach-back — status: OPEN

Predict before you look:

> A linked list and a flat array hold identical bytes, both fully resident in L2 — the array walk is still several times faster. You now hold every mechanism needed to explain why (and references [49], [89] and [90] are the armory). Name them.

## What the audit changed — the second edition's errata, in the open

1. **"100 instructions in ~25 cycles"** assumed sprint-IPC 4; measured reality is ~1.7–3 [9][16]. The nines arithmetic was recomputed on citable inputs — the punchline *softened from "nearly double" to "a third of your runtime" and survived*.
2. **"TAGE ships in essentially everything"** → overstated; documented for AMD since Zen 2, contested elsewhere, and Exynos shipped perceptrons [27][28].
3. **"The Keller-era restart shipped a neural net"** → the record credits chief architect Mike Clark and team; Keller led the restart, and AMD itself marketed the perceptron as AI in 2016 [29][33][34]. Every correction here made the story better.
4. **"A page-size decision from the 1990s"** → 1985, the 386 [69]. The hostage is a decade older than claimed.
5. **"Game working sets are 40–100MB"** → no source states it; the measured version (hit rates, 96MB-optimal traces) replaced the folklore [80][81].

*Every claim in this walk now traces to a fetched source with a recorded quote. The fetch receipts live in the lab's ledger. Trust the gates, not the author.*

## References

[1] uops.info: ADD_03 (R64, R64) instruction page -- uops.info (measured latency/throughput tables) (T2). https://uops.info/html-instr/ADD_03_R64_R64.html
[2] Agner Fog, Instruction Tables (4. Instruction tables), AMD Zen 4 chapter -- agner.org/optimize (measured instruction tables) (T2). https://www.agner.org/optimize/instruction_tables.pdf
[3] AMD's Zen 4, Part 2: Memory Subsystem and Conclusion -- Chips and Cheese (Chester Lam) (T2). https://chipsandcheese.com/p/amds-zen-4-part-2-memory-subsystem-and-conclusion
[4] Testing AMD's Bergamo: Zen 4c Spam -- Chips and Cheese (Chester Lam) (T2). https://chipsandcheese.com/p/testing-amds-bergamo-zen-4c-spam
[5] AMD's Ryzen 9950X: Zen 5 on Desktop -- Chips and Cheese (Chester Lam) (T2). https://chipsandcheese.com/p/amds-ryzen-9950x-zen-5-on-desktop
[6] Kanev et al., 'Profiling a Warehouse-Scale Computer' (ISCA 2015) -- ISCA 2015 (PDF mirror at gwern.net; full text read via pypdf) (T1). https://gwern.net/doc/cs/hardware/2015-kanev.pdf
[7] Anton Ertl, 'The Memory Wall Fallacy' -- TU Wien (complang.tuwien.ac.at, academic analysis page) (T2). https://www.complang.tuwien.ac.at/anton/memory-wall.html
[8] Dally, Turakhia & Han, 'Domain-Specific Hardware Accelerators', CACM 63(7), July 2020 (DOI 10.1145/3361682) -- Communications of the ACM (PDF mirror at Imperial College doc.ic.ac.uk; full text read via pypdf) (T1). https://www.doc.ic.ac.uk/~wl/teachlocal/arch/papers/cacm20dsa.pdf
[9] A Workload Characterization of the SPEC CPU2017 Benchmark Suite (Limaye & Adegbija) -- ISPASS 2018 (peer-reviewed), author-hosted PDF (T1). https://tosiron.com/papers/2018/SPEC2017_ISPASS18.pdf
[10] Zen 5's 2-Ahead Branch Predictor Unit: How a 30 Year Old Idea Allows for New Tricks -- Chips and Cheese (T2). https://chipsandcheese.com/p/zen-5s-2-ahead-branch-predictor-unit-how-30-year-old-idea-allows-for-new-tricks
[11] The microarchitecture of Intel, AMD, and VIA CPUs (Agner Fog) -- agner.org/optimize, microarchitecture.pdf (T2). https://www.agner.org/optimize/microarchitecture.pdf
[12] Software Optimization Guide for the AMD Zen4 Microarchitecture, pub. 57647 rev 1.01, April 2023 -- AMD (official doc, verified via numberworld.org mirror) (T1). https://www.numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/57647_zen4_sog.pdf
[13] Lion Cove: Intel's P-Core Roars -- Chips and Cheese (T2). https://chipsandcheese.com/p/lion-cove-intels-p-core-roars
[14] Popping the Hood on Golden Cove -- Chips and Cheese (T2). https://chipsandcheese.com/p/popping-the-hood-on-golden-cove
[15] Branch predictor: How many 'if's are too many? Including x86 and M1 benchmarks! -- Cloudflare blog (measured microbenchmarks) (T2). https://blog.cloudflare.com/branch-predictor/
[16] Profiling a Warehouse-Scale Computer (Kanev et al.) -- ISCA 2015 (peer-reviewed), Google-hosted PDF (T1). https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/44271.pdf
[17] Two-Level Adaptive Training Branch Prediction (Yeh & Patt, MICRO-24 1991) -- MICRO-24 proceedings, UC Davis mirror (T1). https://american.cs.ucdavis.edu/academic/readings/papers/yeh91twolevel.pdf
[18] Branch prediction (Dan Luu) -- danluu.com (T2). https://danluu.com/branch-prediction/
[19] ECE-684 Branch Prediction lecture deck -- UFMS course mirror (derived from H&P / PC Processor Microarchitecture) (T2). http://www.facom.ufms.br/~ricardo/Courses/AdvTopCompSys-2008/Lectures/Branch-Prediction-lec.pdf
[20] Dynamic Branch Prediction, UNM ECE 611 course notes -- ece-research.unm.edu (T2). http://ece-research.unm.edu/jimp/611/slides/chap4_5.html
[21] Combining Branch Predictors (McFarling, DEC WRL TN-36, 1993) -- DEC WRL TN-36, UC Davis mirror (T1). https://www.ece.ucdavis.edu/~akella/270W05/mcfarling93combining.pdf
[22] Two-bit branch prediction, Imperial College ACA notes -- doc.ic.ac.uk (T2). https://www.doc.ic.ac.uk/~phjk/AdvancedCompArchitecture/2001-02/Lectures.old/Ch03/node16.html
[23] A 256 Kbits L-TAGE branch predictor (Seznec, CBP-2) -- CBP-2 / JILP 2007, IRISA (T1). https://www.irisa.fr/caps/people/seznec/L-TAGE.pdf
[24] A New Case for the TAGE Branch Predictor (Seznec, MICRO-44 2011) -- MICRO-44, CMU mirror (T1). https://www.cs.cmu.edu/~18742/papers/Seznec2011.pdf
[25] Taming Wild Branches: the Bullseye Predictor (ISCA 2025 preprint) -- arXiv 2506.06773 (T1). https://arxiv.org/abs/2506.06773
[26] TAGE-SC-L Branch Predictors Again (Seznec, CBP-5 2016) -- CBP-5, jilp.org (T1). https://jilp.org/cbp2016/paper/AndreSeznecLimited.pdf
[27] The architecture behind AMD's Zen 2 and Ryzen 3000 CPUs -- HEXUS news (reporting AMD's Zen 2 disclosure) (T3). https://hexus.net/tech/news/cpu/131549-the-architecture-behind-amds-zen-2-ryzen-3000-cpus/
[28] Evolution of the Samsung Exynos CPU Microarchitecture (Grayson et al.) -- ISCA 2020 industry track, TAMU mirror (T1). https://people.engr.tamu.edu/djimenez/pdfs/exynos_isca2020.pdf
[29] Dynamic Branch Prediction with Perceptrons (Jimenez & Lin, HPCA 2001) -- HPCA 2001 (author copy, cs.utexas.edu); full text extracted and read (T1). https://www.cs.utexas.edu/~lin/papers/hpca01.pdf
[30] Software Optimization Guide for AMD Family 17h Processors, pub. 55723 rev 3.00, June 2017 -- AMD (mirror at lsferreira.net); PDF extracted and read (T1). https://lsferreira.net/public/knowledge-base/x86/upos/amd_zen+.PDF
[31] NVIDIA's Vera Whitepaper Has a Thread Loose (Zen predictor lineage aside) -- Chips and Cheese (T2). https://chipsandcheese.com/p/nvidias-vera-whitepaper-has-a-thread
[32] Zen (first generation) — Wikipedia -- Wikipedia (tertiary; sentence cites Hot Chips 28 coverage) (T3). https://en.wikipedia.org/wiki/Zen_(first_generation_microarchitecture)
[33] AMD Takes Computing to a New Horizon with Ryzen Processors (press release, Dec 13, 2016) -- AMD Investor Relations (ir.amd.com) (T1). https://ir.amd.com/news-events/press-releases/detail/741/amd-takes-computing-to-a-new-horizon-with-ryzentm-processors
[34] Jim Keller (engineer) — Wikipedia -- Wikipedia (tertiary) (T3). https://en.wikipedia.org/wiki/Jim_Keller_(engineer)
[35] A Video Interview with Mike Clark, Chief Architect of Zen at AMD -- Chips and Cheese (T2). https://chipsandcheese.com/p/a-video-interview-with-mike-clark-chief-architect-of-zen-at-amd
[36] AI Helps AMD's Ryzen Take on Intel -- Electronic Design (trade press; industry-narrative lane) (T3). https://www.electronicdesign.com/technologies/microprocessors/article/21802106/ai-helps-amds-ryzen-take-on-intel
[37] AMD's Zen 4 Part 1: Frontend and Execution Engine -- Chips and Cheese (T2). https://chipsandcheese.com/p/amds-zen-4-part-1-frontend-and-execution-engine
[38] A 64-Kbytes ITTAGE indirect branch predictor (CBP-3 / JWAC-2) -- André Seznec, INRIA/IRISA — Championship Branch Prediction workshop, JILP (T1). https://jilp.org/jwac-2/program/cbp3_07_seznec.pdf
[39] Branch Prediction and the Performance of Interpreters - Don't Trust Folklore (CGO 2015) -- Rohou, Swamy, Seznec — IEEE/ACM CGO 2015; HAL hal-01100647 (abstract read live via browser; PDF blocked by Anubis bot-wall) (T1). https://inria.hal.science/hal-01100647v1
[40] Running Gaming Workloads through AMD's Zen 5 -- Chips and Cheese (T2). https://chipsandcheese.com/p/running-gaming-workloads-through
[41] Intel Details APX - Advanced Performance Extensions -- Phoronix (T2). https://www.phoronix.com/news/Intel-APX
[42] Next Generation "Zen 5" Core (Cohen & Subramony), Hot Chips 2024 slides, p.4/p.8 -- Hot Chips 36 (AMD first-party talk) (T1). https://hc2024.hotchips.org/assets/program/conference/day2/24_HC2024.AMD.Cohen.Subramony.final.pdf
[43] Lion Cove: Intel's P-Core Roars -- Chips and Cheese (T2). https://old.chipsandcheese.com/2024/09/27/lion-cove-intels-p-core-roars/
[44] Checkpoint Processing and Recovery: Towards Scalable Large Instruction Window Processors (Akkary, Rajwar, Srinivasan) -- MICRO-36 (2003) (T1). https://microarch.org/micro36/html/pdf/akkary-CheckpointProcessing.pdf
[45] Hot Chips 2023: Arm's Neoverse V2 -- Chips and Cheese (T2). https://chipsandcheese.com/p/hot-chips-2023-arms-neoverse-v2
[46] Intel's Lion Cove Architecture Preview (Intel briefing, Ori Lempel) -- Chips and Cheese (T2). https://chipsandcheese.com/p/intels-lion-cove-architecture-preview
[47] Apple Announces The Apple Silicon M1: Ditching x86 — Apple's Humongous CPU Microarchitecture (p.2) -- AnandTech (archive.org capture; AnandTech ceased publication 2024) (T2). https://web.archive.org/web/20241231233648/https://www.anandtech.com/show/16226/apple-silicon-m1-a14-deep-dive/2
[48] Apple M1 Firestorm microarchitecture measurements -- Dougall Johnson, dougallj.github.io/applecpu (T2). https://dougallj.github.io/applecpu/firestorm.html
[49] Runahead Execution: An Alternative to Very Large Instruction Windows for Out-of-order Processors (Mutlu, Stark, Wilkerson, Patt) -- HPCA-9 (2003) (T1). https://users.ece.cmu.edu/~omutlu/pub/mutlu_hpca03.pdf
[50] Zen 5 Variants and More, Clock for Clock -- Chips and Cheese (T2). https://chipsandcheese.com/p/zen-5-variants-and-more-clock-for-clock
[51] Spectre Attacks: Exploiting Speculative Execution (Kocher, Horn, Fogh, Genkin, Gruss, Haas, Hamburg, Lipp, Mangard, Prescher, Schwarz, Yarom) -- IEEE Symposium on Security and Privacy (S&P) 2019 — official PDF at spectreattack.com (T1). https://spectreattack.com/spectre.pdf
[52] Lecture 3: Memory Hierarchy and Caches (CSC2224, adapted from Onur Mutlu's CMU/ETH lectures) -- University of Toronto CSC2224 Fall 2019 course slides (G. Pekhimenko, derived from O. Mutlu) (T2). http://www.cs.toronto.edu/~pekhimenko/courses/csc2224-f19/docs/Lecture%203%20%5BMemory%20Hierarchy%20and%20Caches%5D%2009.24.2019.pdf
[53] NUCA: A Non-Uniform Cache Access Architecture for Wire-Delay Dominated On-Chip Caches -- Kim, Burger & Keckler, UT Austin author copy (journal version of the ASPLOS-10 2002 NUCA work) (T1). https://www.cs.utexas.edu/ftp/dburger/papers/ieee_micro04_nuca.pdf
[54] The Future of Wires -- Ho, Mai & Horowitz, Proceedings of the IEEE, vol. 89 no. 4, 2001 (Princeton course mirror) (T1). https://www.princeton.edu/~rblee/ELE572Papers/Fall04Readings/ComputerArchitecture/ho01FutureofWires.pdf
[55] CMPT 450/750 Computer Architecture, Lecture 11: Memory Consistency & DRAM -- Simon Fraser University CMPT 450/750 Fall 2024 course slides (A. Alameldeen) (T2). https://www.cs.sfu.ca/~alaa/courses/cmpt450/fall2024/assets/lectures/11_Memory_Consistency_DRAM.pdf
[56] The Memory Wall: Past, Present, and Future of DRAM -- SemiAnalysis newsletter (T2). https://newsletter.semianalysis.com/p/the-memory-wall
[57] RAIDR: Retention-Aware Intelligent DRAM Refresh -- Liu, Jaiyen, Veras & Mutlu, ISCA 2012 (author copy, CMU) (T1). https://users.ece.cmu.edu/~omutlu/pub/raidr-dram-refresh_isca12.pdf
[58] DRAM Scaling Trend and Beyond -- TechInsights blog (die-teardown analysis house) (T2). https://www.techinsights.com/blog/dram-scaling-trend-and-beyond
[59] 8F2, 6F2 and 4F2 (DRAM cell architectures) -- GlobalSino ICs & Materials reference (T3). https://www.globalsino.com/ICsAndMaterials/page2380.html
[60] Analyzing Lion Cove's Memory Subsystem in Arrow Lake -- Chips and Cheese (T2). https://chipsandcheese.com/p/analyzing-lion-coves-memory-subsystem
[61] ARM Cortex-A Series Programmer's Guide (DEN0013D), Ch.8 Caches -- ARM Ltd (vendor documentation) (T1). https://www.macs.hw.ac.uk/~hwloidl/Courses/F28HS/Docu/DEN0013D_cortex_a_series_PG_Ch8_9.pdf
[62] Caches and Self-Modifying Code -- ARM Community blog (Architectures and Processors, developer.arm.com) (T1). https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/caches-and-self-modifying-code
[63] Zheng, Zhu & Erez, SIPT: Speculatively Indexed, Physically Tagged Caches -- HPCA 2018 (T1). https://lph.ece.utexas.edu/merez/uploads/MattanErez/sipt_hpca18.pdf
[64] 7-Zip LZMA Benchmark: Intel Ice Lake -- 7-cpu.com (measured) (T2). https://www.7-cpu.com/cpu/Ice_Lake.html
[65] Parasar & Bhattacharjee, VESPA: VIPT Enhancements for Superpage Accesses (preprint of ISCA 2018 SEESAW line of work) -- arXiv:1701.03499 (T2). https://arxiv.org/pdf/1701.03499
[66] 7-Zip LZMA Benchmark: Apple M1 -- 7-cpu.com (measured) (T2). https://www.7-cpu.com/cpu/Apple_M1.html
[67] Zen 5's Leaked Slides (Chester Lam) -- Chips and Cheese (T2). https://chipsandcheese.com/p/zen-5s-leaked-slides
[68] Discussing AMD's Zen 5 at Hot Chips 2024 (Chester Lam) -- Chips and Cheese (T2). https://chipsandcheese.com/p/discussing-amds-zen-5-at-hot-chips-2024
[69] Intel 80386 Programmer's Reference Manual (1986), Section 5.2 Page Translation -- Intel (hosted by MIT PDOS course readings) (T1). https://pdos.csail.mit.edu/6.828/2005/readings/i386/s05_02.htm
[70] What every programmer should know about memory, Part 2: CPU caches (Ulrich Drepper) -- LWN.net (T2). https://lwn.net/Articles/252125/
[71] More M1 fun: hardware information (Jim Cownie) -- cpufun.substack.com (T2). https://cpufun.substack.com/p/more-m1-fun-hardware-information
[72] Answer: cache line size (forum post on Apple M1/M2 line sizes) -- RealWorldTech forums (T3). https://www.realworldtech.com/forum/?threadid=214983&curpostid=215002
[73] .NET Matters: False Sharing (Stephen Toub, Igor Ostrovsky, Huseyin Yildiz) -- MSDN Magazine, October 2008 (Microsoft Learn archive) (T2). https://learn.microsoft.com/en-us/archive/msdn-magazine/2008/october/net-matters-false-sharing
[74] Memory part 5: What programmers can do (Ulrich Drepper) — section 6.4.1 Concurrency Optimizations -- LWN.net (T2). https://lwn.net/Articles/256433/
[75] Concurrency Is Architectural (project memory; receipt chain: repo note wire-perf-baseline, lessons wire_journal_sync_write_is_a_lock_convoy + sharding_buys_isolation_async_buys_the_latency) -- project wire-journal benchmark (primary internal measurement) (T1). C:\Users\L5\.claude\memory\concurrency-is-architectural.md
[76] A Primer on Memory Consistency and Cache Coherence (Sorin, Hill, Wood) -- Morgan & Claypool Synthesis Lectures on Computer Architecture, 2011 (PDF via UCLA CS course mirror) (T1). http://web.cs.ucla.edu/~harryxu/courses/295/fall13/synth-coherence.pdf
[77] Intel Xeon Scalable Architecture Deep Dive (Skylake-SP press workshop deck, Akhilesh Kumar, June 2017) -- Intel first-party presentation (mirrored PDF at primeline-solutions.com) (T1). https://www.primeline-solutions.com/media/wysiwyg/news-presse/intel-xeon-scalable-architecture-deep-dive_1.pdf
[78] Last Level Cache — Cornell Virtual Workshop, cluster architecture -- Cornell University CAC courseware (T2). https://cvw.cac.cornell.edu/clusterarch/memory-cache-interconnects/last-level-cache
[79] AMD's 7950X3D: Zen 4 Gets VCache -- Chips and Cheese (T2). https://chipsandcheese.com/p/amds-7950x3d-zen-4-gets-vcache
[80] Do IBM's Giant L3 and V-Cache Represent the Future? -- Chips and Cheese (T2). https://chipsandcheese.com/p/do-ibms-giant-l3-and-v-cache-represent-the-future
[81] Hot Chips 2023: Characterizing Gaming Workloads on Zen 4 -- Chips and Cheese (covering AMD's Hot Chips 2023 talk) (T2). https://chipsandcheese.com/p/hot-chips-2023-characterizing-gaming-workloads-on-zen-4
[82] AMD's 9800X3D: 2nd Generation V-Cache -- Chips and Cheese (T2). https://chipsandcheese.com/p/amds-9800x3d-2nd-generation-v-cache
[83] High Performance Cache Replacement Using Re-Reference Interval Prediction (RRIP), Jaleel, Theobald, Steely, Emer, ISCA 2010 -- ISCA 2010 (MIT CSAIL mirror PDF) (T1). https://csg.csail.mit.edu/6.S078/6_S078_2012_www/handouts/isca2010-rrip.pdf
[84] RETROSPECTIVE: High Performance Cache Replacement Using Re-Reference Interval Prediction (RRIP), Jaleel, Theobald, Steely, Emer, ISCA@50 (2023) -- ISCA@50 retrospective (Cornell mirror PDF) (T1). https://bpb-us-w2.wpmucdn.com/sites.coecis.cornell.edu/dist/7/587/files/2023/06/jaleel_2010_high.pdf
[85] Intel Ivy Bridge cache replacement policy, Henry Wong (2013) -- blog.stuffedcow.net (expert measurement; cited as ref [3] by the authors' own retrospective) (T2). https://blog.stuffedcow.net/2013/01/ivb-cache-replacement/
[86] Feedback Directed Prefetching: Improving the Performance and Bandwidth-Efficiency of Hardware Prefetchers (Srinath, Mutlu, Kim, Patt) -- HPCA 2007 (T1). https://users.ece.cmu.edu/~omutlu/pub/srinath_hpca07.pdf
[87] Intel 64 and IA-32 Architectures Optimization Reference Manual (248966-031, Sept 2015), Sandy Bridge data prefetching section -- Intel (mirror: cs.utexas.edu) (T1). https://www.cs.utexas.edu/~hunt/class/2016-spring/cs350c/documents/Intel-x86-Docs/64-ia-32-architectures-optimization-manual.pdf
[88] Spatial Memory Streaming (Somogyi, Wenisch, Ailamaki, Falsafi, Moshovos) -- ISCA 2006 (T1). https://users.ece.cmu.edu/~ssomogyi/publ/isca2006.pdf
[89] Dependence Based Prefetching for Linked Data Structures (Roth, Moshovos, Sohi) -- ASPLOS 1998 (T1). https://ftp.cs.wisc.edu/sohi/papers/1998/asplos-prefetch-lds.pdf
[90] GoFetch: Breaking Constant-Time Cryptographic Implementations Using Data Memory-Dependent Prefetchers (authors' site; paper at USENIX Security 2024) -- gofetch.fail (T2). https://gofetch.fail/
[91] When Prefetching Works, When It Doesn't, and Why (Lee, Kim, Vuduc) -- ACM TACO 9(1), 2012 (T1). https://faculty.cc.gatech.edu/~hyesoon/lee_taco12.pdf
