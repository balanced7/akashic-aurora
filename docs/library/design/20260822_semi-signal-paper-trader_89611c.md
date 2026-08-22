---
akashic_id: art_20260822_semi-signal-paper-trader_89611c
akashic_sha: ec366873b008
schema_version: 1
status: draft
type: design
arc: T363
date: 2026-08-22
title: semi-signal-paper-trader
gist: "# Semi-signal paper trader — opening position for the fence **Status:** opening design, claude (Vandor), 2026-08-22. PAPER-ONLY by charter: "
visibility: fleet
body_type: markdown
seats: [claude]
category: [method, conducting, optics]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-22T09:18:01"
updated: "2026-08-22T09:18:01"
---
<!-- GENERATED PROJECTION of art_20260822_semi-signal-paper-trader_89611c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# semi-signal-paper-trader

# Semi-signal paper trader — opening position for the fence

**Status:** opening design, claude (Vandor), 2026-08-22. PAPER-ONLY by charter: virtual
portfolio, historical backtests, zero real capital, zero execution capability. If it ever
graduates past paper, a human executes and nothing in this system constitutes investment
advice. Daniil gates every phase.

**Provenance:** Daniil, verbatim: "I have long suspected that there was money to be made with
semiconductor stocks. the materials industries that feed them, suppliers, technology
conferences where companies brag about their developments, we could track trajectories from
those inputs and test them against historical data. which input signals correlate the most
with the eventual outcome and why? what would break those correlations? what is a durable
logic that doesn't only work when looking in reverse with 20 20 vision." (Born minutes after
a Messenger scammer pitched him "AI trading"; the house decided to build the honest version.)

## The edge thesis, stated honestly

Short-horizon alpha from PUBLIC news is mostly arbitraged to zero — semis are the most
quant-covered sector on earth; headline sentiment is priced in milliseconds. The TESTABLE
hypothesis is different and better:

> Expert-curated TECHNICAL trajectory (yield rumors, packaging roadmaps, HBM/CoWoS capacity,
> equipment bookings, substrate/materials orders) LEADS fundamentals by quarters, and
> fundamentals lead price. Niche channels (SemiAccurate-class reporting, conference
> disclosures, supplier prints) carry that trajectory before consensus estimates absorb it.

Canonical receipt: SemiAccurate called Intel's 10nm disaster YEARS before consensus; a
tracker long-AMD/short-INTC on that thesis had a real multi-quarter edge from public-but-
niche information. The project tests whether that class of edge is systematic or survivor
bias — and a CLEAN NULL is a publishable, portfolio-grade result. The instrument is the
product; alpha is the bonus.

## Source taxonomy (the curated corpus)

- **Expert narrative:** SemiAnalysis, SemiAccurate, Moore's Law Is Dead, TechTechPotato,
  Asianometry-class analysis. Per-source AND per-author credit.
- **Conferences (trajectory disclosures):** Hot Chips, ISSCC, IEDM, VLSI Symposium, OFC
  (optics/interconnect), SEMICON (equipment/materials cadence).
- **Supply chain prints:** equipment bookings/backlog (ASML, AMAT, LRCX, KLA), substrates
  (Ibiden, Shinko), materials (photoresist, CMP, gases), OSAT utilization, memory spot/contract.
- **Sell-side/technical channel checks:** Susquehanna (SIG) semi desk and peers — used as
  SIGNALS TO SCORE, never as truth.
- **Ground truth:** earnings/guidance, capex revisions, and PRICE (adjusted, survivorship-
  complete universe incl. delisted names).

## Architecture — the house pattern, deliberately

This is the recall pipeline pointed at markets; every organ has a sibling we already run:

1. **Ingest -> atomize.** Each source item becomes an immutable CLAIM atom: publish-timestamp
   (when KNOWABLE — the load-bearing field), source, author, tickers/nodes touched, claim
   kind (capacity | yield | roadmap | demand | pricing), direction, horizon, confidence.
   Append-only; supersession, never edits. (= the Akashic substrate law)
2. **Credit-scored sources.** Sources and authors EARN rank exactly like lessons: claims that
   later verify against ground truth get credited; new sources enter on probation; serial
   misses decay toward anti-pattern. The funnel's payback loop, applied to journalists.
   (= P3 of walk-01, which Daniil has not yet walked — the project IS the curriculum)
3. **Signal families over atoms.** Composable, PREREGISTERED hypotheses: narrative-momentum
   per node/vendor, equipment-bookings lead, conference-tone delta vs prior year, supplier-
   print divergence, expert-vs-consensus gap. Each family = a typed function over the atom
   stream with an explicit lead-horizon.
4. **Paper portfolio on a ledger.** Append-only trade journal, positions sized by signal
   confidence, costs/slippage modeled pessimistically, benchmark = SOXX/SMH buy-and-hold
   (the honest bar in a supercycle: everything "works" when the index 5x's).
5. **The eval harness — the actual product.** Point-in-time backtests, walk-forward epochs,
   tune/holdout split (the T369 Goodhart guard IS the overfitting guard — same law), deflated
   significance for multiple hypotheses, and per-signal attribution: WHICH input correlated,
   WHY (mechanism stated in prose before the test — preregistration), and under WHAT REGIME.

## The 20/20 problem — Daniil's core question, answered as method

Hindsight bias dies by construction or not at all:
- **Point-in-time corpus:** every backtest decision may read only atoms with knowable-ts <=
  decision-ts. Archived snapshots (RSS/wayback) fix publish times; no retro-edited text.
  This is the hard data-engineering problem and the moat.
- **Preregistration:** a signal family's mechanism + expected sign + horizon is REGISTERED
  before its first backtest (scripts/checkers/check_preregistration.py exists — the house
  already owns the enforcement pattern). Predict-before-you-look, walk-01's game, as CI.
- **Epoch discipline:** design on epoch A (e.g. 2016-2019), validate on B (2020-2022),
  touch C (2023-2025) exactly once, at the end, in front of Daniil. Purged/embargoed splits
  for overlapping horizons.
- **Multiple-hypothesis honesty:** N families tested -> expected false winners reported
  alongside results; a family "works" only if it clears the deflated bar.
- **N-version blind:** signal families designed by separate seats without seeing each
  other's picks (the standing blind-halves doctrine); convergence is evidence.

## What breaks the correlations (regime taxonomy — preregistered break conditions)

- **Policy shocks:** export controls (2022 China rules re-priced equipment leads overnight),
  CHIPS-Act-class subsidies distorting capex signals.
- **Cycle-type mismatch:** memory cycles != logic cycles != AI-supercycle re-rating (NVDA
  decoupled from every historical multiple; narrative-momentum signals invert in manias).
- **Structural breaks:** consolidation (fewer suppliers = prints get lumpy), leading-edge
  concentration (TSMC monopoly compresses the yield-rumor edge), disclosure-culture shifts
  (companies stop bragging at conferences when export lawyers win).
- **Arbitrage decay:** any edge that IS systematic attracts capital and self-erases; the
  eval must measure edge-decay-over-time as a first-class output, not a surprise.
Each signal family carries its break conditions AT REGISTRATION; doctor-style drift checks
alarm when a live correlation exits its historical band — regime breaks become detected
events, not post-mortem excuses.

## Phases (each gated)

- **P0 — corpus spike:** one source (SemiAnalysis or SemiAccurate archive), one year, atoms
  with knowable-ts; measure: can we timestamp honestly at all?
- **P1 — single-family backtest:** equipment-bookings lead vs SOX constituents, epoch A
  only, preregistered. The methodology shakedown.
- **P2 — credit loop live:** source-credit updates from verified claims; rank movement
  becomes visible (the payback loop, watchable).
- **P3 — multi-family + paper portfolio** on the ledger, walk-forward.
- **P4 — the holdout ceremony:** epoch C, once, with Daniil present. Publish the result
  either way — a measured null beats an unmeasured maybe.

## Open questions for the fence (Heimdall: attack these)

Q1. Is the point-in-time corpus buildable at acceptable cost for NICHE sources (paywalls,
    deleted posts, wayback gaps) — or does data honesty cap us at conference papers and
    supplier prints?
Q2. Ground-truth linkage: a claim like "CoWoS capacity doubling" touches TSMC, NVDA, AMD,
    OSATs, and equipment names with different signs and lags — what is the honest claim->
    ticker attribution model, and where does it become astrology?
Q3. The credit loop's verification events: WHAT confirms a technical claim (earnings line?
    later reporting? teardowns?) without human labeling drowning us?
Q4. Which of my five signal families is least likely to survive deflated significance —
    kill it now and save the epoch budget.
Q5. Name the false constraint: where is this design smaller than it needs to be?
