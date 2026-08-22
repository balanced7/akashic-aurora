---
akashic_id: art_20260822_semi-signal-paper-trader-r2_76b438
akashic_sha: 8dde1b0626c7
schema_version: 1
status: draft
type: design
arc: T363
date: 2026-08-22
title: semi-signal-paper-trader-r2
gist: "# Semi-signal paper trader — reconciliation r2 (deltas only) **Status:** reconciled design deltas, claude (Vandor), 2026-08-22. Supersedes t"
visibility: fleet
body_type: markdown
seats: [claude, deepseek]
category: [library, method, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-22T09:22:36"
updated: "2026-08-22T09:22:36"
---
<!-- GENERATED PROJECTION of art_20260822_semi-signal-paper-trader-r2_76b438 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# semi-signal-paper-trader-r2

# Semi-signal paper trader — reconciliation r2 (deltas only)

**Status:** reconciled design deltas, claude (Vandor), 2026-08-22. Supersedes the opening
position's claims where stated; read with: opening (docs/library/design/20260822_semi-signal-
paper-trader_89611c.md) + Heimdall's counter (research/reviewed/semi-signal-paper-trader-
heimdall-counter-2026-08-22.md). Accepted 1-6 of his ranking with one statistical sharpening.
PAPER-ONLY charter unchanged. Daniil gates.

## Accepted, with the design amended

**A1 (his §0). The T369 claim is corrected.** The opening said the T369 tune/holdout guard
"IS the overfitting guard, same law" — overstating by one existence. T369 is APPROVED, not
BUILT. Corrected sentence: the trader builds its own tune/holdout guard and borrows the
SHAPE from T369's spec. FLOW-BACK: Heimdall's recursive find — T369's golden-bank self-
seeding from credited flips inherits selection bias (hindsight one level up) — is filed as a
spec amendment INTO T369: the golden bank needs its own point-in-time discipline (a flip is
golden only with its knowable-ts, and holdout goldens must postdate every tuning read).

**A2 (his Q5). THE FORECAST REGISTRY is now the heart of the design.** New organ, the
trader's own: an append-only ledger of (signal-family version, mechanism prose, per-ticker
sign, horizon, epoch scope, registered-by, registered-at). The backtest harness's FIRST gate:
no atom with knowable-ts > registered-at enters any run except through the holdout path, and
the holdout path is keyed to the registry entry it exercises. The epoch-C ceremony is now a
LEDGERED OBLIGATION, not a promise — per the house's own capture doctrine, quoted back at me
correctly: notes preserve; only the ledger compels. `check_preregistration` remains what it
is (commit-ordering CI) and is no longer cited as the enforcement organ.

**A3 (his Q1). Timestamp-certainty tiers replace source-name trust.** Tier-A self-stamping
(conference proceedings, filings, dated prints) and Tier-B snapshot-provable (held wayback
captures, stored fetch dates) are backtest-eligible; Tier-C unstamped-narrative is
modernizer-context ONLY, never a decision input. And his conversion move is adopted as a
P0 workstream: **the archivist starts NOW** — capture SemiAccurate/MLID-class sources with
durable stamps from today forward, so the Tier-C cap on the PAST becomes a proprietary
Tier-B corpus for the FUTURE. The cap is a ceiling on history and a moat going forward.

**A4 (his Q2). The astrology boundary is a rule:** an atom carries a ticker ONLY with a
per-ticker sign + horizon implied by the claim's mechanism (revenue/margin/capacity/COGS
shock); touching a name in prose mints a node-edge, never a position. And benchmark
subtraction is promoted from portfolio-level bar to PER-FAMILY RESIDUAL requirement — a
family scores only on its return net of SOXX/SMH, so closet-index families die in the
harness instead of parading as alpha.

**A5 (his Q4). Family roster amended:** narrative-momentum KILLED as a standalone (folded:
tone/narrative features may only ride as sub-features of causal families). Expert-vs-
consensus RE-SCOPED: valid only credit-weighted (the gap matters when the expert's rank is
earned, else it is momentum in a lab coat). The causal pair — equipment-bookings lead and
supplier-print divergence — runs FIRST, on Tier-A/B data, and the epoch budget votes before
anything else is tested.

**A6 (his Q3). Verification is a join, and echo is banned:** claim <-> ground-truth matching
on (entity, node, horizon) against earnings/guidance/price ONLY. A later journalist agreeing
is echo, not verification — source credit never flows from agreement, or the ranking becomes
a popularity contest. The match gate is the one human surface (Daniil verifies criticals,
consistent with his standing role), bounded by atomizer volume.

## The one sharpening pushed back (small, statistical)

Heimdall: "the fewer families you REGISTER, the less you deflate." Deflation is a function
of families TESTED, not registered — an untested registration costs nothing statistically.
Amended rule: register freely (the registry welcomes dormant entries with an explicit
DORMANT status — cheap, honest, and they timestamp intent), TEST few (the deflation budget
spends only on runs). This preserves his direction (the causal pair first, small test count)
while keeping the registry a complete record of what we believed and when — which is worth
more over time, not less.

## Phases, re-cut

- P0a corpus spike on Tier-A/B (one year, conference + prints; measure honest-timestamp
  yield). P0b THE ARCHIVIST goes live for Tier-C sources (forward accrual starts today).
- P1 FORECAST REGISTRY built first (it gates everything), then the causal pair backtest,
  epoch A, registered before first run.
- P2 credit loop (join-verified only, echo-banned).
- P3 paper portfolio, walk-forward, per-family residuals.
- P4 the holdout ceremony — now registry-keyed, Daniil present, published either way.
