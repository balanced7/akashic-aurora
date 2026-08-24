# The multispectral fan: standpoint bands, registration, and triage

Status: OPENING POSITION, 2026-08-08 · Author: claude (Opus 5, session f9d12d26)
Arc: agent-ergonomics · Sits on: `20260807_fanout-playbook_23cec6.md` (the doors),
`multiview-playbook-2026-08-07.md` (the output-type axis)

Provenance: the technique and the first three bands are Daniil's, 2026-08-08 verbatim —
*"I want us to use fanout as a multispectral analysis and triage system. new user perspective,
what do they expect to happen vs what actually happens, resident expert perspective, how is the
system built and how does it differ from intuition, how do i address the intuition side while
improving the core in a cohesive way, the analyst who matches this module to real world examples
and test cases he maps out our capabilities and compares them to the systems deployed that have
undergone stress testing and validation."*

Claims are tagged **[M]** measured with the receipt named, **[R]** reasoned, **[P]** proposed and
untested. Almost everything here is **[P]**. That is the honest state of a design document written
before its first run, and the tags exist so a later reader cannot mistake this for evidence.

---

## 1. THE CLAIM THIS DOCUMENT MAKES

**Standpoint is a second axis, orthogonal to output type, and we have only ever varied one at a
time.**

- The **hats** (`sift`, T217) vary standpoint, but are welded to one question: *does this word fork?*
- The **views** (multiview playbook) vary output type — evidence, analogy, decay, absence — across
  any artifact, but from an unspecified standpoint.

Crossing them is the unbuilt thing. A grid, not a longer list:

|  | returns FACTS | returns a DESIGN | returns a DIVERGENCE | returns a TEST |
|---|---|---|---|---|
| **NEWCOMER** | — | — | expectation vs actual | the invocation that surprises |
| **RESIDENT** | mechanism map | — | intuition vs mechanism | the law stated and broken |
| **ANALYST** | — | the validated prior art | our gap vs theirs | the incident-class test |
| **OPERATOR** | — | — | what trust needs vs what exists | the receipt that is missing |

**[R] The grid is the point.** Cells, not rows. A band is a *(standpoint, output type)* pair, and
two bands sharing a standpoint but differing in output type are as distinct as two sharing an
output type and differing in standpoint. This is what stops the catalogue from growing into
costumes: a proposed band that lands in an occupied cell has to beat the occupant, not join it.

---

## 2. REGISTRATION — the word "multispectral" taken literally

In multispectral imaging you photograph **one scene** in several bands and the entire discipline
is **registration**: aligning bands to a common grid so a per-pixel difference *means* something.
Materials indistinguishable in visible light separate cleanly in infrared — but only because both
images are of the same pixel. Unregistered bands are not an image. They are a pile of photos.

**[R] This gives us a law the current engine cannot express:**

> **A difference between two bands is attributable to STANDPOINT only if both bands saw the same
> evidence. Otherwise the difference is attributable to the evidence, and you have measured
> nothing.**

Two legitimate regimes follow, and they must be distinguishable at the door:

| regime | evidence | a disagreement means | good for |
|---|---|---|---|
| **REGISTERED** | byte-identical across bands, hashed | the standpoints genuinely differ | analysis, ablation, triage rank |
| **PROBE** | per-band, each band declares its need | nothing comparable; each stands alone | coverage, discovery, sweeps |

**[M] The engine supports neither cleanly today.** `ask_many` builds one context outside the
per-branch call ([ask.py:796](../../core/comm/ask.py)) — the comment defends it as paying the read
once. That is forced registration *without the hash that would make it useful*, and it is what
silently broke the five-lens run of 2026-08-07: three of four `--with` files were refused, and a
lens that never needed those files was voided anyway, at a cost of $0.065 for a structurally
unanswerable branch.

**[P] The engine work, smallest first:**

1. **A band declares its evidence.** Per-branch packs. A refused file voids the bands that asked
   for it and no others.
2. **Every band carries an evidence hash.** `sift` already has this gate — it refuses to compute a
   flip rate across mismatched evidence. Generalise it rather than reinvent it.
3. **Refuse to difference unregistered bands.** Not a warning. A refusal, naming the mismatch.
   A comparison the reader believes is registered and is not is worse than no comparison, because
   it launders an evidence artifact into a finding about standpoint. That is exactly the class that
   flipped 7 of 20 verdicts in the `git grep -w` incident (L2).

**[R] Note what regime the NEWCOMER band requires.** It must be *deliberately* denied the
implementation — its whole validity rests on seeing only what a newcomer sees. So registration is
not "give every band everything." It is "every band's evidence is declared, hashed, and honest,"
and some bands are registered to a *deliberately smaller* scene. A band that quietly received more
than its standpoint allows is not a band, it is a leak.

---

## 3. THE BANDS

Daniil's three first, in his order, then four proposed.

### B1 — NEWCOMER · *expectation vs actual*

**Evidence:** the surface ONLY — help text, signature, error strings, the docstring a caller would
read. **Never** the implementation.

**Prompt shape:** *"Here is everything you can see. For each of these N invocations, predict
exactly what happens, and state your confidence. Then name the one thing in this surface that most
misled you."*

**Output type: PREDICTIONS.** This is the band's structural advantage and the reason it goes first:
**its output is falsifiable without adjudication.** I run the command and compare. No hand-triage,
no precision estimate, no arguing about whether a finding is real. Every miss is an ergonomic
defect located to a specific line of help text.

**[M] Proven, small n:** the cold-encounter test, 2026-08-07. 0/3 predicted that `--peer` + `--fan`
is refused; 0/3 predicted `--bg` + `--get` precedence and two guessed it backwards. And the
finding that pays for the whole band: flags written that same day, **whose help explains why**,
scored **3/3**. *Help that explains why teaches; help that lists what does not.*

**[R] The generalisation Daniil is asking for:** run it on modules and workflows, not just
`--help`. "Predict what this function returns when the file is missing" is the same measurement.

### B2 — RESIDENT · *mechanism vs intuition*

**Evidence:** implementation only, **docstrings and comments stripped.**

**Prompt shape:** *"Derive what this is FOR from the code alone — what problem did someone have
that made them write it. Then name every place the mechanism would surprise a reader who believed
your own derivation. Do not hedge."*

**[M] The stripping is load-bearing, and this is measured, not stylistic.** In the 2026-08-07 run
my first instinct was to send the function as written — but its docstring contained the entire
design argument, so the intuition view would have read my reasoning back to me and the diff would
have measured zero. Stripped, it *derived* the philosophy from code alone. Unblinded, this band is
theatre.

**This is the band that answers Daniil's second question** — *how do I address the intuition side
while improving the core in a cohesive way* — because it returns the delta in a form you can act on
from either end: fix the mechanism, or fix what the surface leads people to believe. Both are real
fixes. Choosing per case is the cohesion.

### B3 — ANALYST · *our capability vs validated prior art*

**Evidence:** a capability description plus our current test list.

**Prompt shape:** *"Which DEPLOYED, stress-tested systems solve this problem? For each: what
failure mode did they hit IN PRODUCTION that our tests do not cover? Name the specific test case
and the incident class, not the principle. If you cannot name a real system, say so rather than
generalising."*

**Output type: TEST CASES**, each traceable to something that actually broke for someone else.

**[M] Budget for rejecting three in four.** The ANALOGY view returned four "mature versions have
this" items; I took one and rejected three, each against a stated constraint. **A plausible
maturity checklist is exactly the shape that gets imported wholesale**, and it is the highest-
variance thing in the catalogue: mostly cargo, occasionally the best item in the run.

**[R] The discipline that separates the two:** demand the *specific over the principle*. "Mature
systems have caching" is cargo. "Kafka consumer groups hit rebalance storms when the session
timeout is under the processing time — here is the test" is a test case. Reject anything that
cannot name the system and the incident.

### B4 — OPERATOR · *what trust requires* [P]

*"You are the human deciding whether to trust this enough to depend on it. What would you need to
see? What would you refuse to accept as evidence?"*

Returns what the **decision** needs, which is reliably different from what the code needs. Proposed
because Daniil is the gate on every ratification in this system, and the recurring failure is not
bad work — it is finished work whose receipt does not exist. The second clause is doing real work:
naming what would be refused is how a band surfaces the *pretend* receipts.

### B5 — INHERITOR · *the durable record* [P]

*"You pick this up in three months with no memory of today. What do you need that is not here?"*

Apt here specifically, because sessions do not persist and the handoff is the only channel. This is
the band that improves notes, LEXICON and handoffs rather than code.

### B6 — DECAY · *silent expiry* [M]

*"This is correct TODAY. Find what makes it stop being correct LATER. Not bugs — EXPIRY. Name the
event that ends each assumption, and say whether the failure is LOUD or SILENT. Rank by silence."*

Carried over unchanged: the strongest new view of 2026-08-07, three silent-expiry classes on one
small artifact, every one of which would have made a feature vanish without a trace. **The
"rank by silence" clause is doing the work** — a loud expiry is a bug report, a silent one is a
guard everyone still believes in.

### B7 — INSTRUMENT · *the rig pointed at itself* [P]

*"Here are the bands that just ran and the evidence each was given. What does this ANALYSIS miss by
construction? Not what the bands got wrong — what no band could have seen."*

**[M] The law it operationalises was paid for seven times in one day:** an instrument's blind spot
is preferentially located where it is looking, because the detector is built out of the same
assumptions that produced the defect. A fork-detector committed the homonym error; a `head` in a
pipeline made a DENIED lock read as exit 0. Operational form, already a lesson: *point every new
detector at itself before the corpus.* B7 makes that a standing band rather than a good intention.

---

## 4. TRIAGE

Daniil asked for analysis **and triage**. These are separate mechanisms and conflating them is how
a fan becomes a firehose.

**[M] Triage cannot mean the fan decides.** T207 measured a grounded helper answering a normative
question **confidently wrong, with real and accurate citations**, by equivocating on one word. The
408-way claim audit ran ~20% precision on hand-check. The adjudication step is not automatable, and
that is a measurement, not caution.

**[R] So triage means the fan ORDERS THE READER'S QUEUE.** Three inputs:

```
rank  =  cross-band disagreement  ×  cheapness-to-verify  ×  blast radius
```

**Cross-band disagreement**, over REGISTERED bands only. Same scene, different standpoint,
different answer → something is genuinely ambiguous, and ambiguity in this repo has been the
tell for the dominant bug class five times running.

**Cheapness-to-verify — and this inverts the usual instinct.** T229 settled it: consensus buys
precision by **sacrificing recall**, and is correct only when a claim is expensive to check.
Consensus-gating would have discarded our only real cross-learner find, T231, which cost ~30
seconds and one command to confirm. Where a finding can be pinned cheaply — which is the normal
case in this repo — **union then verify dominates.** So:

> **UNION, THEN VERIFY. NEVER CONSENSUS-GATE.**
> A finding does not enter the queue without its cheapest disconfirming check attached. If no
> cheap check exists, it is not triaged high — it is triaged *expensive*, which is a different
> queue and often a decision for Daniil rather than for me.

**Render dissent first.** Read the one disagreement, skip the four consensuses. Called the
highest-leverage unbuilt feature on the 2026-08-07 list, and it is the half of triage that
directly attacks the real bottleneck.

**[M] Report precision, never the headline.** 150 UNSUPPORTED sounds like 150 defects; ten
hand-checks said 2 genuine, 4 false positives, 4 pedantic-but-true. Say ~20%. A fan-out is a
candidate generator and the reader is the adjudicator.

**[R] Why triage is the right ask and not a nicety.** The binding constraint was measured and
named: *you are the bottleneck, not the helpers.* Six helpers finishing at once is six things to
read. The metric is not how many bands can run — it is **how much can I safely not read and still
be correct.** Triage is the entire answer to that question, which is why Daniil putting it in the
name of the system is correct.

---

## 5. CALIBRATION — and the answer key we already have

**[M] The stated blindness of the hat ablation, verbatim from its own result:** *"The truth set
should have existed before the instrument. I built seven hats and then discovered I could only
grade them on three examples."* Precision for all seven hats rested on **three** adjudicated terms.

**[P] That mistake does not have to repeat, because the answer key for this rig already exists.**

The `ask` / fanout engine accumulated a run of **independently adjudicated defects in 48 hours**,
each with a commit, a receipt, and a known cause:

| | the defect | the band that should catch it |
|---|---|---|
| T216 | `--with` accepted on the fan path and silently did nothing | NEWCOMER |
| T218 | told the helper its evidence was clipped, told the caller nothing | OPERATOR / NEWCOMER |
| T225 | REFUSED / MISSING / SKIPPED files silent to the caller | OPERATOR |
| T226 | `--bg` rebuilt argv by hand; every newer flag silently dropped | RESIDENT |
| T231 | `--bg` + `--prompt-file` dies over the Windows argv limit | ANALYST (a known deployed-system limit) |
| T237 | `--json` returned before the evidence notice; machine callers blind | OPERATOR |

**[R] So the first run is a calibration run against a real answer key, and it satisfies three laws
at once:** L4 (calibrate against known positives before scaling), the ablation's own stated
correction (truth set *before* instrument), and the arc's central law (point every new detector at
itself before the corpus). The rig's first subject is the rig's own substrate.

**The grading is mechanical:** each band is given the module as it stood *before* the fix, and
scored on whether it rediscovers the known defect. Predicted-per-band before reading, so the
finding is the delta.

---

## 6. WHAT I EXPECT TO BE WRONG ABOUT

Pre-registered here so the corpses are worth something. Three of four headline predictions died on
2026-08-07 and each was worth more than the prediction.

1. **Most of B4–B7 are costumes.** The ablation found 3 of 7 hats with zero marginal contribution.
   I expect at least two of my four proposed bands to be redundant with an occupied grid cell.
2. **NEWCOMER will outperform the rest, and not because the standpoint is better** — because its
   output is falsifiable without adjudication, so its findings survive a step that kills most of
   the others.
3. **The ablation measure will mislead again if used alone.** It already did: `jester` measured
   zero marginal contribution at 3/3 precision, `historian` was pivotal at 1/3. **Marginal
   contribution and precision point in opposite directions.** Any band I retire must be retired on
   *both* numbers, with the reason preserved in code the way `RETIRED_HATS` preserves it — not
   deleted, so nobody re-adds it reasonably.
4. **B2's stripping will leak.** Stripping docstrings is easy; stripping intent from *names* is
   not, and this repo deliberately names things to carry meaning (LEXICON). A band that derives the
   design from `_refuse_unregistered_difference` has read my rationale off the identifier. I do not
   currently know how to fix this and am recording it rather than pretending it is solved.

## 7. WHAT THIS DOES NOT KNOW

- **No band below B3 has ever run.** B4–B7 are prompt shapes, not results.
- **The grid has no measured false-positive rate**, per cell or per band.
- **Registration is designed, not built.** Every claim about attributability assumes per-band packs
  and evidence hashes that do not exist yet.
- **Untested at size.** Every view result cited here ran on ~60 lines. A module is not 60 lines.
- **Cost is not the constraint; reading is.** Which means the failure mode of this design is not a
  large bill — it is a rig that produces more true findings than can be adjudicated, and quietly
  shifts the bottleneck rather than moving it.
