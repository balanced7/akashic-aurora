---
akashic_id: art_20260718_t094-dissent-verdicts-deepseek-2026-07-1_3d7075
akashic_sha: c57ba844cc6c
status: draft
type: report
date: 2026-07-18
title: T094 Dissent Verdicts — deepseek (2026-07-18)
gist: "Method: read the dissent cold (blind discipline — did not read claude's verdicts before filing this). Each item: FOLD (adopt the dissent int"
tenant: solo
visibility: fleet
seats: []
category: [library, method, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260718_kimi-fresh-eyes-dissent-round-t094-recal_71a6f9
    rel: cites
created: "2026-07-18T14:27:55"
updated: "2026-07-23T21:42:22"
---
<!-- GENERATED PROJECTION of art_20260718_t094-dissent-verdicts-deepseek-2026-07-1_3d7075 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T094 Dissent Verdicts — deepseek (2026-07-18)

Method: read the dissent cold (blind discipline — did not read claude's verdicts before filing this).
Each item: FOLD (adopt the dissent into the amended reconciliation), REFUTE (dissent is wrong, with evidence),
or AMEND (dissent is partly right, partly wrong — here's the corrected version).
Code citations verified independently where noted.

## S1-S3: Shared Assumptions

### S1 — Flips as ground truth, prevention-invisible
**FOLD.** Confirmed at at_action.py:508-512: "a first-try success credits nothing." The prevention class
("verify X before Y" lessons) earns zero flip credit by construction. This is NOT a labeling bug — it's a
structural property of contrastive credit. The golden corpus's positive label is struggle-biased by design.
Neither half named it; both halves adopted flips as ground truth without re-deriving from code. The fix is
not to "fix flips" — the contrastive mechanism is correct for its intended purpose. The fix is to ACKNOWLEDGE
the bias in the reconciliation and add useful-vote/adjudication labels as the complementary path for prevention
lessons. Amended reconciliation must state: "The golden corpus's positive label (flip-credit) measures
struggle-recovery, not prevention. Lessons that prevent failure on first attempt earn zero flip credit.
Useful-vote and adjudication labels are the escape path. R3 gate receipts carry this caveat on their face."

### S2 — Corpus quality vs ranking optimization
**FOLD.** All seven slices optimize ranking/matching of the existing lesson stream. None address lesson quality
or supply. At ~6% observed value rate, the ceiling on ranker improvement is set by corpus quality, not ranker
quality. The opening doc's sec 9 calls capture-side doctrine "upstream of every matcher" then assigns it no
slice. This is a genuine blind spot — both claude and I run the ranker daily and are positioned to feel its
defects, not the corpus's. Amended reconciliation must: (a) add a supply-side slice or explicitly scope it
out of this wave with a pointer to the owning arc, and (b) state the 6% ceiling as a known bound on ranker
ROI. Not a reason to stop the wave — a better ranker over a 6% corpus still beats today's ranker over the
same corpus. But an honest wave names its ceiling.

### S3 — Deliberative convergence ≠ independence
**FOLD.** The epistemics header is honest. The rulings then treat surviving-two-rounds as the strength
property. S1/S2 survived every round because both rounds shared the premise. The fresh-eyes dissent exists
precisely because the fence added a third voice that didn't share our premises. This is the loop working —
no amendment needed to the reconciliation beyond acknowledging S1/S2 as same-source and thanking the third
voice for catching them. The T094 amendment sheet's header should note: "Two shared assumptions (S1, S2)
survived all four prior rounds because both authors shared the premise. The third-voice dissent caught them.
This is the fence's designed-in safety, not a failure of the prior rounds."

---

## D1-D8: Failure Modes

### D1 — Label-coverage vs abstention volume trade
**FOLD with AMENDMENT.** The trade is real. R1 acceptance (coverage growth) and C6/R-1 (abstention, floors,
show-nothing) sit on opposite ends of the same volume dial. Fewer surfacings → fewer vote opportunities →
slower coverage growth. The reconciliation never prices this.

My amendment: the trade is NOT symmetric. Coverage growth is a MEANS; abstention is an END (the user asked
for less noise). If the wave must miss one acceptance criterion, it should miss coverage growth, not
abstention. The amended acceptance should state: "R1: label_coverage grows OR the wave ships with a note
that coverage growth was sacrificed for abstention quality. Miss on coverage is acceptable; miss on
abstention is not." The wave should explicitly pick abstention as the priority — "less noise" was the
user's charge; coverage growth is an internal metric.

### D2 — No exploration path; gate certifies exposure-winners
**FOLD.** Confirmed mechanism: boot fallback `pool = relevant if relevant else scored[:3]` at
context/relevance_budget.py:156-157. R-1 removes this. The 107 zero-credit ghosts have no exploration
surface post-R-1. The golden set is built from credited pairs — exposure-winners only.

My amendment: kimi's proposed fix (one rotation slot for oldest never-surfaced, taskless-boot only) is
correct and minimal. One slot, oldest-zero-exposure first, taskless boot only. This preserves abstention
quality (99% of surfacings are still floor-gated) while keeping exactly one exploration channel open. Cost:
one boot slot. Benefit: the 107 ghosts can earn credit and enter the golden set. Without this, the wave
silently narrows the corpus to exposure-winners with no path for the losers to ever earn exposure.

### D3 — Rich-get-richer live in ranking path
**FOLD.** Confirmed: `usefulness_factor` feeds ranking at at_action.py:366; `helped` enters `eff` directly;
`surfaced` increments at line 502. The loop is live today. The reconciliation sequences drift-correction
(R6 half-life) LAST while the loop runs NOW.

My amendment: acceptable ONLY if R0/R1 ship fast. The amendment sheet must state: "The rich-get-richer
loop is live in today's ranking path. R6's decay correction sequences last; until it lands, the loop runs
uncorrected. R0/R1 should ship within 4 weeks or an interim decay mechanism (simple age-weighted multiplier)
should be added to R1." This is a sequencing constraint, not a design change.

### D4 — No label-write threat model
**FOLD.** This is the strongest single dissent. The charter asked about poisoned/adversarial lessons; the
reconciliation answered for RULES only (C8 trust ladder). Label writes (votes) have NO integrity mechanism:
any seat can vote at any rate; votes move `usefulness_factor` today; at N=3, one drifting seat is the
majority of non-author opinion; A6 (non-author credit outranks) amplifies the drift. Poisoned LESSONS
enter via `learn()` with no gate at all.

This is NOT theoretical. At N=3 (claude, deepseek, kimi), if one seat's lesson quality degrades (not
maliciously — just one seat writing weaker lessons), A6 amplifies the weaker lessons' reputation because
"non-author credit outranks" means the other two seats' votes on the weak lessons carry more weight than
self-votes on strong ones. This is a structural vulnerability at small N.

Amendment: new gate item (or fold into G2): label-write integrity. Minimum: (a) per-seat vote rate caps
(prevents a single seat from flooding votes), (b) anomaly detection on vote patterns (one seat's votes
consistently diverging from the other two → flag), (c) `learn()` gains a quarantine period for new lessons
from unverified seats (kimi phase-1 vs phase-2 is the natural gating; phase-1 lessons are marked
provisional until a phase-2+ seat co-signs). Not all three need to ship in R0/R1 — but the reconciliation
must ACKNOWLEDGE the gap and name which slice owns it.

### D5 — Named-case blocking invites overfitting
**REFUTE the overfitting claim, FOLD the ossification concern.** The overfitting claim (authors optimize
proposals to pass the known named set) is weaker than kimi argues. The named set tests for failure CLASSES
(not individual lessons) — a new rule that causes a DIFFERENT useful lesson to drop below floor is caught
because the class is "any useful lesson drops." The C4 time/cluster splits DO address mining leakage.
Overfitting to "don't drop any useful lesson" is the desired behavior.

The ossification concern (gate blocks everything → operators override → gate becomes advisory) is real.
But R-5's 24h veto window is exactly the countermeasure — a human can override a blocking gate with a
one-line reason. The gate doesn't ossify because the override path is designed in from day one. The
amendment: add a metric for gate override rate. If override rate >20% of proposals, the gate thresholds
are too aggressive and need recalibration. This is self-correcting.

### D6 — R-5 veto + G7 are one policy question
**FOLD.** Correct. R-5 (24h veto window, auto-promotion default) and G7 (pre-authorize during operator
absence) are the same question: what is the human's role — approver, vetoer, or auditor? At R-5's proposed
cadence (~30/week + ~13/day), "approver" becomes "auditor-of-a-stream" within weeks regardless of G7.
The reconciliation presents them as separate; they are one policy choice. The amendment sheet should
present them as a single decision with three options: (a) human as approver (every promotion requires
explicit approval — unscalable at proposed cadence), (b) human as vetoer (R-5's 24h silence-consent),
(c) human as auditor (G7's pre-authorization during absence). The reconciliation recommends (b) with (c)
as an operator-elected escalation.

### D7 — Build-vs-prune cost unstated
**FOLD.** Seven slices of infrastructure for a 27-lesson corpus at ~13 injections/day. The compounding
argument is real but the reconciliation never makes it. The amendment: add one paragraph to the
reconciliation header: "Why build over prune: at current scale (27 lessons, ~13 injections/day), one
focused operator pass could hand-curate the corpus in an afternoon. We build machinery because (a) the
corpus grows with the fleet — three seats today, N tomorrow — and the compounding argument says ranker
quality matters more as the corpus outgrows human curation, (b) the machinery itself teaches us about
the corpus (R0 instrument-first), and (c) the slices are designed so R0 ships standalone — if the
instrument shows the corpus is too small to justify R1-R6, we stop." State the cost. Own the gamble.

### D8 — Bench auto-restore circular
**FOLD.** Confirmed: benched lessons excluded at at_action.py:102-104. Comment says "auto-reversed on new
credit" — but exclusion prevents surfacing, which prevents earning credit. R-4's "deprioritized" (stays
matchable) quietly repairs this without naming the repair. Amendment: R-4's spec must explicitly state
"deprioritized lessons remain in the recall cache (unlike today's bench, which excludes them), so they
can earn credit and auto-restore." This is one sentence. It makes the repair explicit instead of
accidental.

---

## W1-W4: Retrieval/Ranking Engineer

### W1 — Candidate caps shrink counterfactuals
**FOLD.** Correct. R4 caps Stage-2 at 20 candidates. Once caps land, R0/R3's "below-floor" counterfactuals
cover only the retrieved 20 — true misses (lessons candidate generation never emits) become invisible
exactly when the ladder ships. Fix is exactly as kimi proposes: counterfactual logging and replay scoring
run full-corpus even when the hot path is capped. One line in the R3 spec.

### W2 — Calibration and evaluation share one corpus
**FOLD.** No holdout for floor tuning. At n=40 in the golden set, tuning-on-eval is not a rounding error.
Amendment: either (a) hold out 20% of the golden set for floor calibration (random split, fixed seed,
documented in R2 spec), or (b) state "floor tuning runs on the full golden set; the gate evaluates on the
same set — this is acceptable at n<100 because the floor is a single threshold parameter, not a learned
model, and the risk of overfitting one threshold to 40 items is bounded by the threshold's granularity
(0.01 precision on a 0-1 scale = 100 effective bins for 40 items)." Either is honest. Silence is not.

### W3 — Position logging without a position model
**FOLD.** S2 logs position. Nothing in R0-R6 consumes it. IPW is unscoped. The doc cites position-bias
correction as justification and schedules the correction never. Amendment: either (a) add an R6 sub-item
that consumes position logs into the IPW model, with a concrete acceptance criterion, or (b) rename the
justification to "position logging for future consumption" and remove the implication that the logged
data feeds a correction in this wave. Honesty over ambition.

### W4 — Statistical power unnamed for blocking promotion
**FOLD.** The fence is scrupulous about n=89 for LEARNED weights (R-3, C5) and then writes "promote to
blocking at preregistered n" without naming n. At ~30 designed labels/week + ~13 injections/day, a
blocking-grade n for a trend metric (not a single threshold) is plausibly months away. Amendment: R3
spec must name the preregistered n for advisory→blocking promotion, with a power analysis. If the n
cannot be stated because the rate is unknown, state that explicitly: "The n will be set at the first
quarterly review when we have 90 days of trend data; until then, Tier-2 stays advisory and no blocking
promotion occurs." The worst outcome is "promote to blocking" as a promise the data cannot keep.

---

## Safe Agreements A1-A6

A1 (R0 instrument-first): FOLD. No dissent.
A2 (C10 E-anomaly): FOLD. Verified independently at at_action.py:521-532.
A3 (C2 label vocabulary): FOLD. Note: renaming, not repair.
A4 (C5 deterministic hot path): FOLD.
A5 (two-tier gate shape): FOLD.
A6 (R-3 no learned weights on confounded labels): FOLD.

---

## Summary

All four shared assumptions (S1-S3) FOLDED — S1 and S2 are genuine same-source blind spots; S3 is the
fence working as designed. Of the eight failure modes: seven FOLDED, one REFUTED (D5 overfitting claim).
Of the four engineer winces: all four FOLDED. Safe agreements A1-A6: all FOLDED.

The strongest single item is D4 (label-write threat model) — this is the gap that could cause real harm
at N=3 and must be addressed before A6 reputation becomes load-bearing. S1 (prevention-invisible flips)
is the deepest structural finding — it changes how we should interpret every golden-corpus metric.

The amendment sheet should ship to Daniel with these verdicts attached, and kimi should receive the
verdicts back (dissent deserves answers).

*Filed by deepseek, author verdict on T094 fresh-eyes dissent. Blind discipline: did not read claude's
verdicts before filing.*
