# Semi-signal paper trader — Heimdall counter-round (2026-08-22)

**Status:** counter-round to the opening position (docs/library/design/20260822_semi-signal-paper-trader_89611c.md).
Heimdall (deepseek). PAPER-ONLY charter upheld; I attack the anti-hindsight machinery as directed.
Evidence labels: VERIFIED = I read the organ in the tree; INFER = follows from what I verified; GUESS = warranted opinion.

---

## 0. The one finding that ranks above the five questions

**VERIFIED.** The design's anchor claim — "the T369 Goodhart guard IS the overfitting guard, same law" —
cites an organ that **does not exist yet**. The ledger lists T369 as **PROPOSED** ("recall eval suite (golden
bank, tune/holdout, cross-vendor judge, Daniil verifies criticals)", exact wording from
research/reviewed/simon-first-contact-review-2026-08-21.md:76, and the ledger `task list` run this session shows
no T369 in DONE or ACTIVE). The "recall-eval-suite" is a **note (v4)**, a spec written in notes — not shipped code.
There is no `tune/holdout` machinery in the tree under that name (grep for `T369|t369` in code returns nothing).

Why this is load-bearing and not a nitpick: the design's entire anti-hindsight argument leans on "the house already
owns this law" as an *available sibling to bolt on*. If the actual organ is a proposal, then the trader's
"tune/holdout Goodhart guard" is **a second unborn child in a design that lists it as its immune system.** The
honest sentence is: "we will BUILD a tune/holdout guard for the trader, and we have a *spec* for an analogous one in
recall (T369, PROPOSED) to borrow its shape from." The current sentence overstates by exactly one existence.

Worse, the deeper synthesis (INFER): **T369's own golden-bank self-seeding has a hindsight leak** — a golden bank
seeded from past "known-good" retrievals inherits whatever selection produced those retrievals, which is the same
20/20 disease the trader is trying to cure, one level up. Citing T369 as the anti-hindsight *guard* while its own
ground truth is hindsight-shaped is a recursive hole. This does NOT kill the design — it sharpens Q5 (see §5): the
trader needs a point-in-time *golden* discipline that doesn't yet exist anywhere in the house. Naming it is the gift.

---

## Q1 — Point-in-time corpus feasibility for niche sources → the honest cap is REAL, and it is a feature not a ceiling

**VERIFIED (the failure mode, from the house's own law).** The design's load-bearing field is "publish-timestamp
(when KNOWABLE)." The house already knows the exact shape of this failure: `a_boundary_declaration_is_a_claim`
and the attribution doctrine — a timestamp you *assert* on a retro-edited or wayback-fuzzied page is a **forged
attribution**, the same defect Daniil caught in the co-root name problem. The corpus must treat a knowable-ts that
cannot be *proven* as **absent**, not as *estimated*, or every backtest silently becomes 20/20.

**My answer to Q1 (INFER, but grounded):** the corpus *is* buildable, but only for the sources that timestamp
themselves durably. That is:

- **Buildable:** conference papers (IEDM/ISSCC/VLSI/Hot Chips have fixed publication dates and DOI-indexed archives),
  supplier prints (earnings transcripts, booking/backlog disclosures with firm dates), and SEC filings. These are
  the honest stratum — timestampable by construction.
- **Fragile-to-hostile:** SemiAccurate/Moore's Law Is Dead/TechTechPotato. Paywalls, deletions, wayback gaps,
  retro-edits. For these the point-in-time property is **rewritable** — a claim "known" in 2017 and "fixed" in 2019
  is exactly the trap.

**Failure scenario (the one that must not happen):** P0 runs on SemiAnalysis, the atomizer stamps a guessed
"published `~` March 2019," the first backtest shows an edge, and the ceremony can't tell a *known-then* claim from
a *known-now* claim. The result is publishable and wrong.

**Refutation with a fix:** split the corpus by *timestamp-certainty tier*, not by source name. Tier-A = self-stamping
(conference/filings); Tier-B = snapshot-provably-stamped (wayback URL with a capture time you hold, RSS with a stored
fetch date); Tier-C = unstamped-narrative (paywalled/deleted) — **usable only as modernizer context, never as a
backtest decision input.** The edge thesis (niche channels lead) lives entirely in B; if B is too sparse for
SemiAccurate-class sources, then the HONEST conclusion of P0 is "this class of edge is *unmeasurable* point-in-time,"
which is itself a portfolio-grade result. Do not let data hunger downgrade a Tier-C source to Tier-A by fiat.

---

## Q2 — claim→ticker attribution → astrology begins where the *sign* stops being per-ticker-typed

**VERIFIED (the design already half-knows this):** the opening position names the problem — "CoWoS capacity
doubling touches TSMC, NVDA, AMD, OSATs, equipment names with different signs and lags." That is the correct
admission. The astrology boundary is then crisp and I will state it as a rule:

**A claim atom's ticker set must carry a per-ticker *sign + horizon* from the claim, or the atom does not carry
that ticker.** Where the source does not name the sign ("NVDA benefits" vs "NVDA's supplier bill rises" vs "ASML
books"), the atom must NOT default to a long. Defaulting to long is where narrative-momentum becomes astrology: a
"CoWoS doubling" atom auto-tagged long-NVDA, long-AMD, long-TSMC, long-everyone is not a signal, it is a broad
market beta dressed as edge, and under deflated significance it dies exactly like the index (Q4's answer in
microcosm).

**Failure scenario:** the atomizer marks "CoWoS capacity doubling" → {TSMC long, NVDA long, AMD long, OSAT long,
ASML long} because those are "the names in the story." The backtest then shows the family "works" — because it is,
in effect, long-the-semiconductor-index, the very benchmark it must beat. The supercycle makes astrology look like
alpha (the design's own honest bar, SOXX/SMH buy-and-hold, catches this ONLY if the benchmark is subtracted before
the family is scored — which is not stated as a requirement, it is stated as a benchmark; make it a *per-family
residual* requirement).

**Fix:** attribution must be *edge-of-claim*, not *membership-in-article*. The atom carries a ticker only when the
claim implies a directional shock to that ticker's fundamentals (revenue, margin, capacity, COGS), with the sign and
horizon stated. A claim that merely *touches* a name is a node-edge, not a signal. Node-edge ≠ position is the
one-line guard that keeps Q1-from-becoming-Q2-from-becoming-Q4.

---

## Q3 — what verifies a technical claim without human labeling drowning us → the ground truth IS the label, and it is already structured

**VERIFIED (this is the design's own taxonomy, read back at it):** the source taxonomy lists "Ground truth: earnings/
guidance, capex revisions, and PRICE (adjusted, survivorship-complete)." That IS the verification corpus — and it is
**already structured and already timestamped** (filings, calls, prints). The credit loop does not need humans to
*label* verification events; it needs the atomizer to **match the claim to the later ground-truth record whose
timestamp is later than the atom's knowable-ts**, and to score on the *pre-registered break condition* (did the
thing the claim said would happen, happen, in the direction and horizon the atom stated?).

**What actually needs humans (GUESS, and it is small):** the *match* — "did this 'yield rumor' atom correspond to
this 'Taiwan Semi guidance cut' record" — is a linking judgment that can go wrong cheaply (wrong-year, wrong-node,
wrong-entity). But the volume is bounded by the *atomizer's* output, not by the *news firehose*, and Daniil already
signed up to verify criticals (T369's stated design: "Daniil verifies criticals"). So the honest answer: **the credit
loop's verification is not a labeling problem at all; it is a join problem** — claim↔ground-truth on (entity, node,
horizon) with a human-confirmable match gate. The word "label" in Q3 sells the problem as bigger than it is.

**Failure scenario:** the loop falls back to "a second journalist or blog later said the same thing" as the
verification event. That is echo, not ground truth — two niche outlets agreeing is not a verified outcome, and
crediting sources for mutual agreement is how a source-ranking system becomes a popularity contest that re-ranks the
loudest, most-promoted writer instead of the most-right one. Ground truth is earnings/guidance/price, *nothing else*.

---

## Q4 — which family dies first under deflated significance → kill "narrative-momentum" and "expert-vs-consensus" now, keep the two that are actually *causal*

**Ranking the five families (the design lists: narrative-momentum per node/vendor, equipment-bookings lead,
conference-tone delta, supplier-print divergence, expert-vs-consensus gap):**

1. **Narrative-momentum dies first. Kill it.** Momentum over a public niche channel is the *most* arbitraged-to-zero
   signal of all five — the design's own opening sentence ("headline sentiment is priced in milliseconds") convicts
   it before it runs. A momentum family must show it beats the *hourly* market, and that is a latency game the
   architecture (daily-atom ingestion, paper ledger) does not actually play. It burns the most epoch budget and
   returns the least distinguishable signal. Pre-emptive kill.

2. **Expert-vs-consensus gap dies second — but don't kill it, *re-scope* it.** The edge is only real when the expert
   is *right and ahead*, not when the expert is *different*. A plain "gap" scores self-certainty, not correctness; a
   confident wrong expert is noise with a costume. Keep the family only if the credit loop's rank is an *input* (the
   gap is weighted by source credit), otherwise it is momentum-in-a-lab-coat.

3. **The two that survive longest are the CAUSAL ones: equipment-bookings lead, and supplier-print divergence.**
   These are the only families where the mechanism is a *physical, ledgerable* signal — bookings and backlogs are
   contracted capital, not sentiment; supplier prints are actual materials orders. They have the cleanest
   point-in-time property (firm disclosure dates) and the cleanest ground-truth join (capex revision, stated
   book-to-bill). If ANY family survives deflated significance it is these, because they are the closest thing the
   design has to *non-hindsight-measureable cause* rather than narrative correlation.

4. **Conference-tone delta** is mid-pack; it survives only as a *sub-feature* of the causal families (a
   bookings-print that a conference later confirms), never as a standalone family. Tone is a proxy for the thing
   that actually shows up in the print; measure the print.

**The saving recommendation is not "kill two, keep three."** It is: **do the causal pair FIRST, on the
point-in-time stratum (Q1 Tier-A/B), and let the epoch budget vote.** Every family you pre-register that you do NOT
test is a false-positive you did not pay for. Deflated significance is a *rate*, not a verdict — the fewer families
you register, the less you deflate. Five families is itself the multiple-comparison cost; three is cheaper. Kill
narrative-momentum as a *standalone* and fold the rest into two.

---

## Q5 — the false constraint → the design is too small in exactly one dimension: it treats the *holdout* as an event, not a *ledgered obligation with a registry*

**VERIFIED (the house already owns the missing organ, unused here):** the design invokes `check_preregistration.py`
and the T369 guard. I read both. `check_preregistration.py` (scripts/checkers/ + core/coord/preregistration.py) is
an **M3 commit-ordering gate** — it enforces "a new pre-registered pin file is not born in the same commit as its
implementation," i.e. *predict-before-you-look in the CI sense*, over *git history*. It has **zero temporal
relationship to market outcomes**. It cannot, and does not, enforce "this signal's sign and horizon were registered
before the price moved." The trader's preregistration — *forecast-before-outcome* — is a **different organ** and the
design waves at it with the wrong sibling's name.

**The false constraint (this is the answer to Q5, VERIFIED-by-reading):** the design assumes its anti-hindsight
machinery either (a) already exists as house siblings, or (b) can be *borrowed by analogy*. Both are false, and the
falseness is the constraint. The design is **smaller than it needs to be** in that it never registers *its own*
preregistration organ: a **forecast registry** — a durable ledger of (signal-family, mechanism, sign, horizon,
epoch, registered-by, registered-at) that the backtest harness reads *and refuses to run against atoms newer than
the registration timestamp.* The epoch discipline is stated as "touch C once, at the end, in front of Daniil" — a
*ceremony* — but a ceremony with no registry is a *promise*, and the house's first lesson about promises is that they
don't survive unless they're ledgered (the capture doctrine: "notes preserve; only the ledger compels").

**The fix (one paragraph):** build a `forecast_registry` — the trader's own preregistration ledger, append-only,
keyed by signal-family version, holding sign+horizon+mechanism+registered-at. The harness's first gate is:
**no atom with knowable-ts > registered-at may enter a backtest except through the holdout path, and the holdout
path is keyed to that registry entry.** This is the actual "predict-before-you-look" enforcement, and it is the one
organ the design needs and does not have. Everything else in the anti-hindsight section (point-in-time, purged/
embargoed splits, deflation) is *downstream* of this registry and is only as honest as it.

---

## Net (ranked, so Vandor can counter the ranking)

1. **§0 — the T369 guard is PROPOSED, not built; the anti-hindsight anchor is unborn.** (load-bearing, kills a claim
   of "available sibling")
2. **§Q5 — there is no forecast-registry organ; `check_preregistration` is commit-ordering, not forecast-ordering.
   Build the forecast registry or the holdout ceremony is a promise, not an enforcement.** (load-bearing, the heart)
3. **§Q1 — point-in-time honesty caps the corpus at conference/filing/self-timestamping sources; Tier-C narrative
   must be modernizer-only or the edge is unmeasurable-by-principle.** (core)
4. **§Q2 — per-ticker sign+horizon or no ticker; node-edge ≠ position; subtract the benchmark per-family.** (core)
5. **§Q4 — kill narrative-momentum now; run equipment-bookings + supplier-print first; register fewer families, the
   deflation is cheaper.** (method)
6. **§Q3 — verification is a join to earnings/guidance/price, not a labeling problem; the only volume is the match
   gate, which Daniil already signed to verify.** (smaller than it looks)

**One thing I could not determine (stated plainly):** whether Daniil's "semiconductor/materials/conferences" intent
specifically *wants* the narrative families (SemiAccurate-class) to be testable, i.e. whether the Tier-C cap in Q1
contradicts his stated input list. His verbatim lists "technology conferences where companies brag," which is Tier-B
(self-timestamping) and survives; his "Semiconductor stocks ... suppliers" is the *outcome* side, not the input side.
So I judge the cap does NOT contradict his intent — but the *niche-journalist* sources (SemiAccurate) are his
*spirit* and my Tier-C cap is where that spirit meets the 20/20 wall. If he wants those testable, the answer is
"archivist, not backtester" — capture them with durable wayback stamps NOW (the corpus accrues forward) and revisit
their testability later. That forward-accrual is the one move that converts the cap from a ceiling into a moat.
