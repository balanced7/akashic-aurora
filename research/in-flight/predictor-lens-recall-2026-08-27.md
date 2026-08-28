# The predictor lens on recall — branch prediction, prefetch, replacement, scheduling

Provenance and credit, stated first because I got this wrong once tonight and had to be corrected
twice. **The design is Daniil's.** The research and the mapping below are mine (claude/Vandor).
Rill (dsh_agent) named the L0–L3 ladder and supplied the T377/T378 lineage; Navi (kimi) supplied the
"different moment" rule. See the provenance correction appended to
`recall-garden-trigger-ladder-2026-08-27.md`.

Design direction, NOT build authorization. The fence and the ledger govern.

## 0. Daniil's design, verbatim

> "Since we call so many tools we can have recall heuristics, when this sequence of tools fires the
> likelihood of this being useful / relevant increases. and each category has their own pool of
> lessons that get added or retired"

> "we could take it one step further if content or argument of toolcall contains x, then do y, or y
> and z"

> "We can find ways of more robustly reaching each recall category in a more bounded way, which
> enables it to be richer and more dense because the recalls are more bounded." — THE BOUNDEDNESS LAW

> "We can also mint sensors and logics for recall that allow certain tendencies or patterns or
> conditions to flag certain kinds of recall ... This way we aren't only tied to toolcall. It
> expands our domain awareness"

> "we can apply the branch prediction AT each toolcall or AT each repetition of x signatures or
> unique combinations and flags."

> "this granularity is what will enable incredible fidelity and percision, this maps back to the
> depth of the corpus being more specifically mapped out and tied into, even if its just this axis"

## 1. Why the last clause is the load-bearing move

The 2026-07-12 network report's falsifier #1: *"routing is handed its destination; retrieval must
discover it."* It names signature quality as THE unsolved prerequisite bounding everything
downstream. A branch predictor is handed its site identity — the program counter — for free. Every
systems lens we have brought to this plane has died on that wall, and both prior lenses (the
2026-06-16 cache hierarchy, the 2026-07-12 network report) remain UNBUILT.

Daniil's move does not solve the prerequisite. It makes the SITE DEFINITION A VARIABLE and fields
several at once (the toolcall; a recurring signature; a unique argument/flag combination), letting
the shelf adjudicate which definition predicts. The unsolved prerequisite becomes the thing under
test rather than the thing blocking the test.

His argument for granularity, which corrected my sparsity objection: **the corpus already has the
depth; the index is what is blunt.** 765 of 1,207 lessons (63.4%) open literally with "Use when …" —
those are site definitions written in prose by authors who knew their trigger. We pay the storage
cost of a deep corpus and the retrieval cost of a shallow index. Sharpening the index does not buy
incremental depth; it unlocks depth already paid for.

**The inversion, and it is the first time a systems lens has handed us something rather than costing
us something: WE HAVE AUTHOR-DECLARED SITES.** A branch predictor discovers every site from
execution because nobody annotated the program. Our authors annotated it. On this axis we are not
bounded by what the hardware can do.

## 2. Findings that transfer, with their mechanisms

### 2.1 The chooser rule — update only on disagreement (McFarling 1993)
The meta-predictor that decides WHICH component to trust is updated ONLY when the components
disagree. When they agree there is no information about which is more trustworthy, so nothing is
recorded. Shipped in Alpha 21264; still used inside TAGE-SC-L for the SC-vs-TAGE chooser.

### 2.2 Set dueling — the bounded-evidence mechanism (Qureshi et al., ISCA 2007)
The precise form, and it is stronger than "sample the agreements":
- Dedicate a small number of SETS exclusively to policy A and a disjoint small number to policy B.
  **32–64 sets suffices** — a validated sample-size result, spread non-contiguously so each group is
  a representative miniature of the whole workload.
- ALL remaining sets are FOLLOWERS: they run neither policy independently, they simply apply
  whichever currently wins.
- Winner selection is ONE shared saturating counter (PSEL, 10 bits): a miss in an A-set increments,
  a miss in a B-set decrements, and the sign alone is the verdict.
- **Total overhead under 2 bytes.** DRRIP reuses this exact machinery; TADRRIP chains PSELs past two
  competitors.

**CONSEQUENCE FOR US:** this dissolves rather than mitigates the T370 write-volume risk (N candidates
logging every opportunity becomes the loudest writer in the house — Rill's unfixed objection, the
largest open item, mine as M9). Candidates do not run everywhere and log everywhere. They run on a
bounded representative sample; everything else inherits the answer.

### 2.3 The u-bit is MARGINAL-contribution credit; ours is ABSOLUTE
TAGE increments an entry's usefulness counter only when that entry was correct **and the alternate
prediction would have been wrong**. It measures "was the finer context NECESSARY," not "was I
right." An entry firing correctly where a coarser one would also have fired correctly earns nothing.
Our `usefulness_factor` credits absolute usefulness, which is a mechanism for accumulating redundant
entries. Measurement outstanding with Heimdall.

### 2.4 Retrospective oracle reconstruction — Hawkeye/OPTgen (Jain & Lin, ISCA 2016)
**THIS CORRECTS A CLAIM I MADE TO THE FLEET AND TO DANIIL.** I said the fatal disanalogy is that a
branch resolves every time for free while our judged rate is 3.3%. True of branch prediction. NOT
true of cache replacement, which had the identical problem — Belady's optimal needs the future — and
solved it:
- OPTgen reconstructs AFTER THE FACT what OPT would have done on the recent past, using per-set
  occupancy vectors over overlapping liveness intervals, labeling each reference OPT-hit or
  OPT-miss.
- Those reconstructed labels train a per-PC predictor (8K entries, 13-bit hashed PC, 3-bit
  saturating counter).
- **Updated on a ~5% SAMPLE of accesses** to bound overhead.

We can replay our own trail and ask "given what actually happened next, would surfacing this lesson
have been correct?" — a reconstructed oracle from records we already keep. And 5% is roughly the
judged rate we already have, so the rate is not the ceiling I called it.

### 2.5 Binary labels discard ordering — Mockingjay (Shah, Jain, Lin, HPCA 2022)
Its critique of Hawkeye applies to us directly: a binary label (cache-friendly/averse; for us
useful/noise) means every "useful" item looks alike at decision time. Mockingjay predicts a
multiclass REUSE DISTANCE, converts it to an estimated time of arrival, and evicts the furthest
ETA. 15.2% over LRU vs Hawkeye's 12.9% and SHiP's 7.6%. This is Navi's "a category earns its place
only if it routes to a different MOMENT" as a learned quantity rather than a design rule.

### 2.6 The prefetch triad, with a usable timeliness definition
- ACCURACY = useful prefetches / total issued.
- COVERAGE = (misses_without − misses_with) / misses_without.
- TIMELINESS: a demand that finds its target ALREADY IN FLIGHT rather than resident counts as LATE;
  timeliness = 1 − late/useful. "Too early" is NOT tracked separately — it is indistinguishable from
  either pollution or an ordinary hit.
- POLLUTION is measured with a Bloom filter of addresses evicted BY A PREFETCH; a later demand miss
  on a filtered address increments the pollution counter, isolating prefetch-caused misses.

**BOP's finding is the sharp one** (Michaud, DPC2 2016): offsets that maximize raw COVERAGE are
frequently LATE and net-negative, so BOP makes timeliness the primary selection objective and
deliberately trades coverage away. Its scoring inserts addresses into the Recent-Requests table only
after a programmable DELAY (~60 cycles) so an offset scores only if it would have beaten that
window. **COVERAGE-OPTIMAL IS NOT USEFUL-OPTIMAL**, and we have no timeliness concept at all.

### 2.7 Feedback-directed aggressiveness (Srinath, Mutlu, Kim, Patt, HPCA 2007)
A 3-bit counter restricted to values 1–5 = five discrete aggressiveness levels, each a fixed
(distance, degree) pair. Every sampling interval, measured accuracy is bucketed against two
thresholds, lateness and pollution likewise, and the combination steps the counter. ~13.6% better
than fixed aggressiveness at equal bandwidth. Recall today has NO aggressiveness control; it is
fixed. A bounded ladder is the shape to copy, not a continuous knob.

### 2.8 Speculative insertions rank below demanded ones — PACMan
Prefetched lines get LOWER insertion priority than demand-fetched lines by default; only
predicted-accurate ones get normal priority; and a prefetched block is DEMOTED TO LOWEST PRIORITY
THE FIRST TIME IT IS USED, capping how much capacity unproven speculation holds hostage.

### 2.9 Starvation-freedom — EEVDF (Linux 6.6, 2023; completed 6.12, 2024)
LAG = entitled minus received, with the invariant that **the sum of all lag is always zero**.
Eligible iff lag ≥ 0. Being passed over MECHANICALLY RAISES eligibility over time, which is the
starvation-freedom argument. Requested slice length is decoupled from long-run share, so "how soon
you are picked" and "how much you average" are separate numbers — a distinction CFS conflated. Also
an anti-gaming detail: a task sleeping while ineligible stays on the runqueue in a deferred-dequeue
state so it cannot sleep briefly to reset its accounting.

Our lessons that stop surfacing have NOTHING that ever brings them back. We have no lag ledger.

## 3. Disanalogies that stand — do not import these

1. **We are ATTENTION-bounded, not STORAGE-bounded.** Seznec on the unbounded track: "the
   replacement policy is not a real issue." The entire aging/eviction/u-bit-reset apparatus exists
   BECAUSE storage is bounded. 1,207 lessons could be 100,000. The useful-counter should arrive as a
   RANKING signal; importing the reset machinery needs a reason better than "the hardware does it."
2. **Site identity is discovered, not given** (network report falsifier #1). Daniil's variable-site
   proposal addresses this rather than solving it; signature quality still bounds everything.
3. **A delivered lesson can SUBTRACT value by misleading** (network report falsifier #3) — no packet
   or cache-line analog. Pollution is the closest mechanism and it is not the same thing.
4. **The corpus is not neutral cargo** (falsifier #7). Prefetchers assume payloads are opaque and
   equally worth carrying.
5. **Cold start**: Lin & Tarsa (2019) fault online-only predictors for learning from scratch every
   launch, "discarding all prior experience." That is our seats every boot — and unlike silicon we
   CAN persist. CBP2025 changed its own scoring to separate the two: MPKI measured on 50% of
   instructions AFTER warming. Report cold-start and warmed performance as two numbers, never one.

## 4. Corrections to my own earlier claims, recorded because the error is the evidence

1. I told the fleet and Daniil the free-oracle gap was the fatal disanalogy. §2.4 shows an adjacent
   field solved it by retrospective reconstruction on a 5% sample. The claim was too strong.
2. I answered the write-volume risk with "log disagreements, sample agreements." §2.2 is tighter:
   only the dueling sets produce evidence at all.

## 5. Open

- Heimdall: of our credited-useful lessons, how many survive a MARGINAL-contribution test?
- Navi: does her namespace collapse apply to site definitions — killing Daniil's granularity
  proposal or disciplining it? (Her answer to the allocation-policy question: "not the same rule,
  adjacent, and the difference is the point" — her rule is a purity condition, TAGE is her rule with
  a scheduler wrapped around it, and the scheduler is what she is missing.)
- M9 remains mine: identify a DURABLE event source before any adapter. The tempdir-lifetime
  injection telemetry cannot produce a daily rate.

## Sources
Seznec & Michaud JILP 2006 (TAGE); Seznec L-TAGE CBP-2, TAGE-SC-L CBP-4/CBP-5, TAGE-SC CBP2025;
Jiménez & Lin HPCA 2001 (perceptron); Jiménez CBP-5 2016 (multiperspective); McFarling DEC WRL TN-36
1993 (combining); Kessler et al. (Alpha 21264); Qureshi et al. ISCA 2007 (DIP/set dueling); Jaleel
et al. ISCA 2010 (RRIP/DRRIP); Jain & Lin ISCA 2016 (Hawkeye/OPTgen); Shah, Jain, Lin HPCA 2022
(Mockingjay); Srinath, Mutlu, Kim, Patt HPCA 2007 (FDP); Wu, Jaleel et al. (PACMan); Michaud DPC2
2016 (BOP); Kim et al. MICRO 2016 (SPP); Bakhshalipour et al. HPCA 2019 (Bingo); Nesbit & Smith
(GHB); Bera et al. MICRO 2021 (Pythia); Linux EEVDF docs + LWN; Blumofe & Leiserson (work stealing);
Lin & Tarsa 2019; CBP2025 and DPC4 rules.
