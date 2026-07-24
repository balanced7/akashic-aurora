---
akashic_id: art_20260718_kimi-fresh-eyes-dissent-round-t094-recal_71a6f9
akashic_sha: 40b1d0f7f3af
status: draft
type: report
date: 2026-07-18
title: Kimi fresh-eyes dissent round — T094 recall-heuristics reconciliation (2026-07-18)
gist: "claude opening, deepseek counter. NOT read before filing: deepseek-review verdict, codex analysis, frontier-avsearch doc (per brief). Verifi"
tenant: solo
visibility: fleet
seats: []
category: [library, recall, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-18T13:42:40"
updated: "2026-07-18T13:42:40"
---
<!-- GENERATED PROJECTION of art_20260718_kimi-fresh-eyes-dissent-round-t094-recal_71a6f9 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Kimi fresh-eyes dissent round — T094 recall-heuristics reconciliation (2026-07-18)

claude opening, deepseek counter. NOT read before filing: deepseek-review verdict,
codex analysis, frontier-avsearch doc (per brief). Verifications are my own code
reads, cited file:line. Tags: VERIFIED / INFER / GUESS.

Headline: the reconciliation is well-built *on its own axis*, and its axis is the
problem. Both halves are written by operators of the ranking system, so both take
the corpus as given and the flip signal as ground truth. The build wave's permanent
gate (R3) inherits a label bias neither half named, and the wave as written reduces
lesson exploration below today's level while demanding label growth it starves.
Dissent below, strongest first; safe agreements at the end.

## 1. SHARED ASSUMPTIONS (same-source, not independent)

- **S1 — Flips are ground truth for "a lesson helped." [VERIFIED the mechanism,
  INFER the consequence]** A flip is a FAIL→SUCCESS contrast on a target:
  `resolve_action_outcome` credits `helped` to lessons surfaced for that target,
  and "a first-try success credits nothing" (core/recall/at_action.py:508-512).
  Both halves adopt flip-credit as the GOLDEN corpus's positive label (opening A3;
  counter 2.2 debates only n-size). Neither names the episode-selection bias:
  **the positive label exists only on struggle episodes.** A lesson that prevents
  failure on the first attempt — the highest-value outcome, and the shape of most
  process lessons ("verify X before Y") — earns zero flip credit by construction.
  C2's label-honesty fix addresses bundle confounding; R-8's echo join enriches
  attribution; nothing repairs that prevention is invisible to the promotion
  currency. Same-source because both seats read the same funnel doc and neither
  re-derived the flip definition from code.
- **S2 — The corpus is worth ranking better.** [INFER] All seven slices optimize
  matching/routing/presentation of the existing lesson stream; none address lesson
  quality or supply. At ~6% observed value rate (their telemetry), the ceiling on
  any ranker improvement is set by corpus quality. Opening sec 9 calls capture-side
  doctrine "upstream of every matcher" — then assigns it no slice. BS2's seed mine
  produces LABELS, not better lessons. Both seats run the ranker daily; neither is
  positioned to feel content starvation. Classic ranking-team blind spot.
- **S3 — Deliberative convergence is treated as near-independence.** [VERIFIED as
  text, INFER the effect] The epistemics header is admirably honest (live iterative
  fence, "not verification-grade independence"). But the rulings then treat
  surviving-two-rounds as the strength property. S1/S2 survived every round
  precisely because both rounds shared the premise — that is what same-source
  means. This report is the designed-in catch working as intended.

## 2. WHAT NEITHER CONSIDERED (failure modes of the R0/R1 wave)

- **D1 — The label-growth acceptance fights the abstention drive.** [VERIFIED the
  mechanism, INFER the collision] R1 acceptance: label_coverage visibly grows
  (+5pp/4wk per 6a). C6 + R-1: show-nothing first-class, boot fallback removed,
  floors everywhere. Votes attach to *surfaced* lessons only (recall-feedback
  takes a surfaced source pointer). Fewer surfacings → fewer vote opportunities →
  slower coverage growth. The only compensating sources are R-7 (~30/wk, itself a
  friction gate item G3) and BS2's one-time mine. The wave's two headline
  acceptance criteria sit on opposite ends of the same volume dial, and the
  reconciliation never prices the trade. As written the wave must miss one of them.
- **D2 — No exploration path for never-surfaced lessons; the gate certifies
  exposure-winners.** [VERIFIED mechanism, INFER magnitude] Triage shows 107
  zero-credit ghost counters (opening). `usefulness_factor` is lifetime, no decay
  (at_action.py:359-370). The golden set is built from credited pairs — i.e., from
  lessons that already won exposure. IPW-style "log now, correct later" (S2)
  cannot rescue zero-exposure items: no propensity, no correction. Interleaving
  (S3/R-6) compares RULES, not LESSONS. Today's one accidental exploration surface
  is the boot top-3 fallback (`pool = relevant if relevant else scored[:3]`,
  context/relevance_budget.py:156-157) — the exact mechanism R-1 removes; R-1's
  RECENT section restores exposure for only the freshest 3 and only at taskless
  boot. Net effect of the wave as written: LESS lesson exploration than today,
  while the replay gate grows more confident about the exposure-winners.
- **D3 — Rich-get-richer is live in the ranking path now.** [VERIFIED code]
  `usefulness_factor` feeds ranking today; `helped` enters `eff` directly
  (at_action.py:366); surfacing increments `surfaced` (at_action.py:500-503). A
  lesson surfaced near a struggle gets credit; credit raises its multiplier; the
  multiplier raises future surfacing. No decay until R6 (S5 half-life deferred to
  "evidence-earned refinements"). The reconciliation sequences drift-correction
  LAST while the loop runs NOW. INFER: acceptable only if R0/R1 ship fast; the
  roster should say so explicitly.
- **D4 — Poisoned labels have no threat model while A6 makes reputation
  load-bearing.** [INFER] C8 builds a trust ladder for RULE writes (git canonical,
  bounded Store overrides, capability-gated). Nothing guards LABEL writes: any
  seat can vote useful/noise on any lesson at any rate; votes move
  `usefulness_factor` today and the golden corpus tomorrow. A6 (non-author credit
  outranks) then amplifies reputation at N=3 seats, where one drifting or
  compromised seat is a majority of non-author opinion. Poisoned LESSONS enter via
  learn() with no gate at all — the trust ladder governs rules, not the corpus
  the rules rank. The brief asked about adversarial/poisoned lessons; the
  reconciliation is silent on all three label-side vectors.
- **D5 — The named-case blocking tier invites overfitting; the small-n gate will
  ossify or be routed around.** [INFER structure, GUESS likelihood] C4 Tier-1
  blocking = named golden/adversarial cases; deepseek's own math: 95% at n=40 = 2
  misses. Two attractors: (a) gate blocks everything → operators learn to override
  → gate becomes advisory-in-practice (the failure deepseek predicted for
  auto-apply, relocated to the human); (b) agent rule-authors (R-5!) optimize
  proposals to pass the small, known, git-tracked named set — test-set overfitting.
  C4's time/cluster splits address mining leakage, not author overfitting. No
  held-out rotation is proposed anywhere.
- **D6 — Alert-fatigue inversion: R-5's veto window and G7 are the same dial
  turned two ways.** [INFER] Silence-consent (24h veto) makes auto-promotion the
  default at machine proposal speed; G7 asks about pre-authorizing the same thing
  during absence. Approve G7 and the operator becomes auditor-of-a-stream — the AV
  auto-deploy failure mode the fence elsewhere praises as solved by human gates.
  Decline G7 and lifecycle throughput = one operator's availability (BS3). The
  reconciliation presents R-5 and G7 as separate items; they are one policy
  question: what is the human's role in the loop — approver, vetoer, or auditor?
- **D7 — Machinery cost vs manual pass is never priced.** [GUESS on effort, INFER
  on omission] Seven slices of ranking infrastructure for a 27-lesson corpus at
  ~13 injections/day. The alternative — one focused operator pass over the 107
  ghosts and the worst lessons — is never compared. The compounding argument for
  machinery is real but the reconciliation does not make it; it makes no cost
  argument at all. At minimum the roster should state why build beats prune at
  this n.
- **D8 — Bench auto-restore is circular today.** [VERIFIED code, INFER impact]
  Benched lessons are excluded from the recall cache (at_action.py:102-104) while
  the comment promises "auto-reversed on new credit" — but an excluded lesson
  cannot surface to earn credit; the escape is pull-side votes, the rarest
  behavior in the system. R-4's deprioritized ("stays matchable") quietly repairs
  this; the reconciliation presents R-4 as new semantics without noting it fixes a
  live contradiction. One line in R-4 would make the repair explicit.

## 3. WHERE A RETRIEVAL/RANKING ENGINEER WOULD WINCE

- **W1 — R4's candidate caps silently shrink the counterfactual instrument.**
  [VERIFIED today's architecture, INFER the regression] Today the ranker scores
  the full corpus, so R0's "below-floor top-N" counterfactuals are complete over
  scored items. Deepseek 2.5 caps Stage-2 at 20 candidates; R4 adopts caps
  ("earned by replay"). Once caps land, "below-floor" covers only the retrieved
  20 — true misses (lessons candidate generation never emits) become invisible
  exactly when the ladder ships. Fix is one line in R0/R3: counterfactual logging
  and replay scoring run FULL-CORPUS even when the hot path is capped.
- **W2 — Calibration and evaluation share one corpus.** [INFER] Floor
  recalibration (counter 2.4 → R-2) optimizes retention/F1 on the golden set; the
  C4 gate then evaluates on the same golden set. No holdout is mentioned for floor
  tuning. At n=40, tuning-on-eval is not a rounding error; it is the estimate.
- **W3 — Position logging without a position model.** [INFER] S2 logs render
  position (good), but nothing in R0-R6 ever consumes it — interleaving is R6 and
  IPW is unscoped. Fine as instrumentation; wince because the doc cites
  position-bias correction as the justification and then schedules the correction
  never.
- **W4 — Statistical-power honesty is uneven.** [INFER] The fence is scrupulous
  about n=89 bounds for LEARNED weights (R-3, C5) and then writes "advisory tiers
  promote to blocking at preregistered n" (sec 3) without naming the n or the
  power analysis. GUESS: at ~30 designed labels/week plus ~13 injections/day,
  blocking-grade n for trend metrics is quarters away; the preregistered n should
  be in R3's spec before G1 approves, or "promote to blocking" is a promise the
  data cannot keep.

## 4. SAFE AGREEMENTS (low-ambition, stated honestly)

- **A1 — R0 instrument-first + explain verb.** [VERIFIED need] The E2 unnamed-
  matched-token exhibit is damning, and it generalizes: reading my own fleet mail
  today I hit the same class of opacity (mailbox shows evidence tiers and shas;
  no door verb shows bodies). Instrument-first is correct, observation-only,
  reversible. Low-ambition: nobody dissents from "add logging."
- **A2 — C10 E-anomaly resolution.** [VERIFIED independently]
  `normalize_target(None, None)` returns "" (at_action.py:521-532); deepseek's
  trace is correct and the R0 fix is right.
- **A3 — C2 label vocabulary.** Epistemically correct; note it is a renaming, not
  a repair — the same confounded counters feed `usefulness_factor` until R1 lands
  (VERIFIED at_action.py:366).
- **A4 — C5 deterministic hot path + bandit deferral.** Correct at n≈89; the
  tripwire number is defensible. Safe.
- **A5 — Two-tier gate SHAPE.** Blocking-smoke + advisory-trend is the right small-n
  shape; my dissent (D5/W1) targets the named-case construction and cap scope, not
  the tiers.
- **A6 — R-3 sequencing** (no learned weights on confounded labels): correct.

## 5. RECOMMENDED AMENDMENTS (small, before G1)

1. R3 spec: name the preregistered n + power basis for advisory→blocking promotion
   (answers W4); declare replay/counterfactual scoring full-corpus regardless of
   hot-path caps (answers W1); state the holdout policy for floor tuning (W2).
2. R1 spec: state the abstention↔label-coverage trade explicitly and pick which
   acceptance bends (answers D1); add ONE designed exploration slot for
   zero-exposure lessons (e.g., one rotation slot in taskless boot RECENT, oldest
   never-surfaced first) so the wave does not reduce exploration below today (D2).
3. R-4/R-5: one sentence that deprioritized repairs today's circular bench
   restore (D8); one paragraph naming the human's loop role — approver, vetoer, or
   auditor — and acknowledging R-5 and G7 are that one question (D6).
4. New gate item (or fold into G2): label-write integrity — who may vote, at what
   rate, with what anomaly detection — before A6 reputation becomes load-bearing
   (D4).
5. Roster note: state the build-vs-prune cost argument once (D7), and flag
   flip-episode bias (S1) as a known limitation of the golden corpus with
   useful-vote/adjudication labels as the only current escape — so R3's gate
   receipts carry the caveat on their face.

Line count target met (~120). Dissent delivered; where I agree, I said so and why
it is safe. — kimi (phase-1, fresh-eyes lane)
