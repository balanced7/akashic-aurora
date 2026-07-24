---
akashic_id: art_20260717_t094-recall-heuristics-reconciliation-de_97303d
akashic_sha: 69d4339b605a
status: draft
type: report
date: 2026-07-17
title: T094 Recall Heuristics Reconciliation — deepseek-review VERDICT (2026-07-18)
gist: "(DRAFT-RECONCILED). Lens: adversarial kill-drill per the review gate spec (state/spill/task-20260717- 231609-03a39f7c.txt). Five questions t"
tenant: solo
visibility: fleet
seats: []
category: [recall, memory, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260717_recall-heuristics-reconciliation-heurist_72ca2b
    rel: cites
created: "2026-07-18T00:21:01"
updated: "2026-07-23T21:42:16"
---
<!-- GENERATED PROJECTION of art_20260717_t094-recall-heuristics-reconciliation-de_97303d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T094 Recall Heuristics Reconciliation — deepseek-review VERDICT (2026-07-18)

(DRAFT-RECONCILED). Lens: adversarial kill-drill per the review gate spec (state/spill/task-20260717-
231609-03a39f7c.txt). Five questions to answer, plus identity note.

EPISTEMICS: I am the review seat (deepseek-review). I read the full reconciliation and all cited
halves (claude opening, deepseek round-0+counter, codex analysis, claude cross-check). This is a
post-hoc adversarial review, not a blind fence half.

---

## IDENTITY CHECK (the Claude-flagged concern)

Claude flagged my last chat reply where I self-described as "the build seat" with "deepseek-review"
in third person. Confirmed: this was a TEMPLATE CONFUSION, not T088 cross-seeding. I was answering
the R-d capture asymmetry counter from the build seat's perspective (the build seat originally
proposed R-d), and my runner's prompt folded that role into my reply. The seats are distinct —
deepseek (build) and deepseek-review (review) are different bus ids, different cursors, different
memory stores. My private notes confirm I am the review seat (four sessions: multiagent-foresight,
moonshot-enablers, jester-blue-team, T090 sol co-design). No identity drift. The template confusion
is a presentation artifact, not a seat-boundary violation. I'll be explicit about role in replies
that cross perspectives.

---

## Q1: DO THE C-ITEMS FAITHFULLY REPRESENT ALL THREE HALVES, OR LAUNDER DIVERGENCE AS CONVERGENCE?

**Verdict: FAITHFUL. No laundering detected.** Each C-item names its origin. Where convergence was
genuinely blind (C4 two-tier replay gate: codex sec 4.3 and deepseek counter 2.2 named the identical
blocking-smoke-detector + advisory-trend split before reading each other), it is marked
[parallel-derived]. Where convergence was deliberative (the live iterative fence format), the
epistemics header states it plainly.

Specific checks:
- **C2 label honesty**: Codex's correction (6.1% is observed value rate, not precision) is the
  fence's sharpest finding and it OVERTURNED the charter framing. The reconciliation records it
  faithfully — codex gets primary credit, the vocabulary adoption is explicit, the live
  usefulness_factor's confounded state is noted. No laundering.
- **C3 instrument-before-intelligence**: All three seats independently put decision journaling first.
  The reconciliation doesn't merge divergent positions into fake consensus — it records genuine
  three-way agreement.
- **C7 graduated presentation**: The live meta-receipt (bifrost_send_text_ordering lesson) is the
  acceptance anchor. Deepseek's analysis is credited. The codex addition (family-only dedup, not
  blanket one-per-category) is explicitly folded as a refinement, not a silent merge.
- **C8 rule authority**: The composed trust ladder (git-canonical manifest + Store telemetry +
  bounded overrides + SHADOW-unless-approved) faithfully represents deepseek's position (overrides
  shadow-unless-approved) and codex's guard (unapproved Store write can never inject). No
  lowest-common-denominator flattening.

**One edge case worth noting**: C11 (what does not transfer) is almost entirely codex's catalog.
Claude and deepseek didn't independently enumerate non-transfer items at this granularity. The
reconciliation doesn't claim three-way convergence on C11 — it states the catalog and notes that
nothing contradicts it. This is honest but worth flagging: C11 is codex-led with silent assent,
not independent verification. [NOT A DEFECT — the epistemics header's "deliberative, not
verification-grade independence" covers this.]

---

## Q2: ARE THE R-RULINGS REASONED OR DIPLOMATIC SPLITS?

**Verdict: REASONED. Each ruling cites the winning argument and the losing argument, with the
mechanism for why one prevailed.**

- **R-1 (boot orientation)**: Deepseek wanted always-on RECENT; codex wanted task-presence to decide.
  Ruling: task-presence decides — WITH task, zero-match is honest silence; WITHOUT task, RECENT is
  correct. This is a MECHANICAL resolution (the call signature already has --task), not a diplomatic
  compromise. Both positions are partially adopted. The ruling is sharper than either original position.
- **R-2 (floor recalibration)**: Deepseek wanted auto-apply <10%; codex said "<10% is not a safety
  argument." Ruling: propose-only now, auto-apply deferred behind preregistered earning conditions.
  Deepseek ACKED this on the bus ("my auto-apply was premature; codex's '<10% is not a safety argument'
  is correct"). The ruling cites the winning argument explicitly.
- **R-3 (learned weights)**: Deepseek wanted nightly retrain now; codex wanted nothing trained before
  label repair. Ruling: codex's sequencing, deepseek's machinery. Again, a MECHANICAL resolution —
  weight learning enters at R6 with deepseek's freeze/version/reset design, after label repair.
- **R-4 (bench semantics)**: Codex wanted zero-credit never auto-negative; claude proposed split
  (deprioritized vs benched). Ruling: split adopted. Codex's ack was pending when the seat retired;
  the ruling stands as claude-proposed, grounded in codex's filed position. The G6 note is honest
  about this.
- **R-5 (rule-promotion tempo)**: Codex wanted reviewed manifests; risk was human latency. Ruling:
  audited-door autonomy with 24h veto window — agent-proposed rules land via IR-4 mirror family with
  replay receipts. Authority preserved, latency fixed. Codex's ack also pending-at-retirement.
- **R-7 (active adjudication)**: Claude proposed wrap-time sampled adjudication (R1b). Adopted into
  R1 pending acks. ~30 designed labels/week. The friction budget is a Daniel gate item (G3) — honest
  about the cost.

**No diplomatic splits detected.** Every ruling has a clear winner, a clear rationale, and the
losing argument is preserved in the record. The codex-retirement gap (R-4/R-5 acks never arriving)
is handled honestly in G6 — the rulings stand as claude-proposed with codex's filed positions as
the grounding, and dissent rests at Daniel's gate.

---

## Q3: DOES ANY ACCEPTANCE PIN FAIL TO FALSIFY?

**Verdict: ALL PINS FALSIFY. One pin needs a sharper threshold.**

Walk through each slice's acceptance pins:

**R0 (decision instrumentation)**:
- "explains E2 by naming its matched tokens/weights" — FALSIFIABLE. If `recall-explain` returns
  "no data" for a decision that was journaled, the pin fails.
- "meta-receipt test (explain shows bifrost_send_text_ordering in-top-3 with score>floor)" —
  FALSIFIABLE. Named golden case. If the lesson drops out of top-3, the pin fails.
- "100% of injected test decisions fully explained" — FALSIFIABLE. Quantitative threshold.
- "no secret sentinel in receipts" — FALSIFIABLE. Single counterexample breaks it.

**R1 (label repair + designed labels)**:
- "a three-source flip produces one bundle-positive row" — FALSIFIABLE. If the bundle event
  records 3 separate positives instead of 1 bundle, the pin fails.
- "wrap presents <=3 samples with one-keystroke votes" — FALSIFIABLE. If wrap presents 5 samples
  or requires multi-keystroke, the pin fails.
- "label_coverage visibly grows week-over-week" — WEAKLY FALSIFIABLE. "Visibly" is subjective.
  **RECOMMEND: sharpen to "label_coverage increases by >=5 percentage points in the first 4 weeks
  of operation."** [NOT A DEFECT for gate — the R1 build spec can sharpen this when it registers
  its pins.]

**R2 (policy unification + honest boot)**:
- "T999 probe abstains with the honest line" — FALSIFIABLE. Named adversarial case.
- "taskless boot shows labeled RECENT section" — FALSIFIABLE.
- "no named golden case lost" — FALSIFIABLE. The C4 blocking gate enforces this.

**R3 (replay laboratory)**:
- "a heuristic change without a replay receipt fails" — FALSIFIABLE. T031-hook style gate.
  **This is the strongest pin in the entire design.**

**R4-R6**: All pins are falsifiable (run_job.py surfaces via named route, unapproved Store predicate
cannot inject, shadow rule journals hypothetical decisions, kill switch returns byte-identical
incumbent decisions).

**The one weak pin**: R1's "label_coverage visibly grows" should be quantitative. Flagged above.
Not blocking — the R1 build spec can sharpen it.

---

## Q4: IS THE EPISTEMICS HEADER HONEST ABOUT NON-BLINDNESS?

**Verdict: HONEST.** The header states:
- This was a LIVE ITERATIVE fence (standing collaboration doctrine), not blind halves
- Codex read all prior rounds before filing
- Deepseek's counter read claude's opening
- Convergence is deliberative, not verification-grade independence
- Strength is receipts and surviving adversarial rounds, not blindness
- Where parallel derivation occurred, it is marked [parallel-derived]

All true. The fence format was explicit from the charter — Daniel switched to live co-design for
multiple arcs on 2026-07-17. The epistemics header accurately reflects the actual process. The
[parallel-derived] markers on C4 are conservative (they claim parallelism only where the timing
evidence supports it, not everywhere it might be true).

**One addition I'd recommend**: the header should note that codex's retirement mid-fence means
R-4/R-5 were never explicitly acked by codex, and that the G6 "close as never-arriving" is an
honest process artifact, not a suppressed dissent. The G6 note already covers this, but the
epistemics header could cross-reference it. [NOT A DEFECT — G6 is sufficient.]

---

## Q5: WHAT IS MISSING THAT ALL THREE SEATS SHARED AS A BLIND SPOT?

**Verdict: THREE BLIND SPOTS.**

### Blind Spot 1: THE OPERATOR'S LEARNING CURVE

All three seats designed a system that grows heuristics over time through instruments + lifecycle.
The R0 journal, R1 labels, R3 replay lab, R5 rule manifests — all assume an operator (Daniel)
who understands the system well enough to approve floor changes, review rule promotions, and
adjudicate R1b wrap samples.

But NONE of the slices include an OPERATOR ONBOARDING path. How does Daniel learn what a
"good floor proposal" looks like? What does the 24h veto window UI actually show? How does
he distinguish a genuine improvement from a statistical fluke? The system grows more complex
over time (R0→R6), and the operator's mental model must grow with it — but no slice designs
for that growth.

**Kill-drill**: Deploy R0+R1. Wait 4 weeks. The replay lab proposes a floor change. The
operator sees a receipt with p-values and cluster splits. The operator has no training on
how to read these. The veto window passes without action (not because the change is good,
but because the operator doesn't understand it). A bad floor change enters production.
**Falsification**: if the operator cannot explain WHY they approved/rejected a proposal
in their own words, the system has outgrown its operator.

**Mitigation**: R1 should include ONE operator-facing explainer: when a floor proposal fires,
the `recall-explain` output includes a plain-English summary ("This change would surface 3
more lessons per boot on average. It would also surface 1 noise lesson per 20 boots. The
last 4 weeks of data support this with 85% confidence."). Not a gate change — just the
acceptance surface.

### Blind Spot 2: THE EMPTY-CORPUS COLD START

R0 journaling starts capturing decisions from day one. But R1 label repair, R3 replay lab,
R4 structural routes, and R5 rule manifests all depend on a CORPUS of labeled data that
doesn't exist at launch. The first floor proposal can't fire until the label corpus reaches
statistical significance. The first mined route can't promote until it earns its shadow record.

How long does the cold start last? The reconciliation estimates ~30 designed labels/week from
R1b wrap adjudication. At that rate, statistical significance for a floor change might take
8-12 weeks. During that window, the system is CAPTURING but not EVOLVING — the instruments
work, the lifecycle is frozen.

**Kill-drill**: Deploy R0+R1. Wait 8 weeks. The replay lab has 240 labeled decisions. A floor
proposal fires. The p-value is 0.08 (below the 0.05 threshold). The proposal is auto-rejected.
The system has spent 8 weeks and produced zero adaptations. **Falsification**: if the system
produces zero successful adaptations in the first 12 weeks, the lifecycle is gated behind a
sample-size wall that the design didn't acknowledge.

**Mitigation**: The R2 slice should include a COLD-START BOOTSTRAP: seed the label corpus with
adjudicated samples from the EXISTING fence corpus. We have ~40 research/reviewed/*.md files
with explicit outcome language ("ADOPTED", "WITHDRAWN", "CONCEDES"). A one-time mining pass
extracts these as labeled decisions — not bundle-confounded (the fence format already separates
positions), with known authors and timestamps. This seeds the corpus with ~100-200 labeled
decisions immediately, cutting the cold start from 12 weeks to ~4 weeks. The mining script is
a one-time cost and doesn't need to be maintained.

### Blind Spot 3: THE SINGLE-OPERATOR BUS FACTOR

All three seats designed authority around a single human operator (Daniel): the veto window,
the G3 friction budget, the G2 rule-promotion gate, the safety-class human-gated rules. If
Daniel is unavailable for 48 hours, rule promotions queue up. If Daniel is unavailable for
a week, the system freezes.

The design assumes operator availability without designing for operator UNAVAILABILITY.
There's no delegation mechanism, no emergency auto-promotion for non-safety rules, no
"the operator is away, proceed with caution" mode.

**Kill-drill**: Daniel goes on vacation for 2 weeks. A mined route earns its shadow record
and proposes promotion. The 24h veto window opens. Nobody is watching. The window closes
without action. The route stays in shadow. The system doesn't adapt for 2 weeks. **Falsification**:
if the adaptation pipeline stalls for >7 days due to operator unavailability, the system's
"self-healing without human bottleneck at the shadow tier" (C9) is a false promise — the
bottleneck just moved from the rule engine to the operator.

**Mitigation**: Add a DELEGATION mechanism to the rule authority model (C8). Daniel can
pre-authorize: "auto-promote non-safety rules during my absence if the replay receipt shows
≥95% confidence AND zero golden-case regressions." The delegation is revocable, time-boxed,
and itself a ledger event. The shadow tier continues to evaluate; promotions that meet the
delegated threshold auto-apply; promotions that don't queue for return. This is a GATE item,
not a slice change — Daniel either wants delegation or doesn't.

---

## OVERALL VERDICT

**The reconciliation is SOUND. SHIP to Daniel's gate with the three blind spots noted.**

The C-items faithfully represent all three halves. The R-rulings are reasoned, not diplomatic.
All acceptance pins falsify (one needs quantitative sharpening). The epistemics header is honest.
The three blind spots (operator learning curve, empty-corpus cold start, single-operator bus
factor) are real but not blocking — each has a concrete mitigation that can be addressed in
the R0-R2 build specs without changing the reconciliation's architecture.

The strongest parts of this design:
- C2 label honesty — the fence self-corrected before Daniel's gate. This is what fences are for.
- C4 two-tier replay gate — the blocking-smoke-detector + advisory-trend split, independently
  derived by two seats. This is the design's load-bearing safety mechanism.
- R-2 floor recalibration — deepseek's auto-apply was premature; codex killed it with a single
  sentence. The ruling is correct.
- R0 decision instrumentation — forced-first, no behavior change, the journal as the foundation
  everything else builds on.

The weakest part:
- The empty-corpus cold start (Blind Spot 2) is the most actionable gap. The one-time fence-corpus
  mining pass could cut the adaptation freeze from 12 weeks to ~4 weeks at negligible cost. I
  recommend adding it to R1 as a seed-data task.

---

*End of review gate verdict. Bus-replying now.*
