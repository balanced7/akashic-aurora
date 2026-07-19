# T094 R0 — Pre-registered pins (claude opening half, night run 2026-07-19)

Binds: reconciliation §4 R0 (AS AMENDED by t094-amendment-sheet-v1 SHEET-A) + G8 ruling
(vote telemetry rides this same observability pass) + method-baseline M1 (pins RED before
code; the fence counters THIS DOC before a line of implementation lands).

## What R0 is (and is not)

The decision journal + explain verb: every recall decision (inject/abstain/reject) becomes
a durable, explainable record. ZERO behavior change — R0 observes the incumbent; it never
alters ranking, floors, tiers, or surfacing. (F2 law: no live metric feeds ranking.)
NOT in R0: label repair (R1), policy unification (R2), gates (R3). G8's vote-rate
telemetry IS in R0 (same instrumentation seam, per Daniel's ruling).

## Module plan (fence may counter)

- `core/recall/journal.py` — append-only decision journal on the Ledger (events family
  `recall:decision`), write-behind so the hot path never blocks on durability.
- `agent_cli.py recall-explain <decision-id|ledger-ref>` — the drill verb.
- Instrumentation call sites: `core/recall/at_action.py` (hook surface) +
  `core/context/relevance_budget.py` (boot surface) — emit-only seams.
- G8 half: vote-write telemetry in `recall_feedback` path + `doctor` row
  (votes/seat/day, anomaly threshold page).

## Pre-registered pins (RED first; each cites its spec line)

**Journal integrity**
- P1 every decision writes one journal row carrying ALL §4-R0 fields: decision_id, context
  signature (REDACTED), candidate set w/ per-feature contributions, matched rule/tier/
  tokens, selected/rejected/abstained + reason, position, render_tier, chars, latency,
  engine/rules/corpus versions.
- P2 SECRET SENTINEL: a context containing a planted secret (key material shape) journals
  with the sentinel REDACTED — the raw secret appears in NO journal field. (Spec:
  "redacted; secret-sentinel pin".)
- P3 below-floor top-N recorded as IDs+vectors — and per SHEET-A.2, the counterfactual
  set is computed FULL-CORPUS: a pin plants a lesson that candidate-generation would miss
  under any future cap and asserts it still appears in the below-floor record. (The
  true-miss visibility pin — this is the sheet's one-line spec addition, enforced.)
- P4 abstention rows journal too: a silence decision (floor not met) produces a row with
  abstained+reason — silence is a decision, not an absence. (W9/F2-corrected lineage.)

**Explain verb**
- P5 `recall-explain <id>` renders every field of P1 human-readably, including the
  S1 CAVEAT LINE on every output: "flip-labels exist only on struggle episodes;
  prevention-shaped value is invisible to them" (SHEET-A.4: the caveat rides every
  receipt's face — receipts BEGIN existing in R0, so the stamp begins here).
- P6 ACCEPTANCE (spec verbatim): explain names E2's matched tokens/weights on the E2
  replayed context.
- P7 ACCEPTANCE (spec verbatim, the meta-receipt): on a replayed failed-send context,
  explain shows `bifrost_send_text_ordering` in-top-3 with score>floor. (The lesson that
  fired while relaying Daniel's gratitude — now a permanent named test. Poetry as CI.)
- P8 100% of injected test decisions fully explained (no field missing/unknown) — the
  spec's completeness bar, as a loop over a seeded decision batch.

**Latency (spec pins, benched not vibed)**
- P9 warm-path journal emit p95 < 5ms over 200 in-process emissions (bench harness in the
  pin; write-behind queue, never fsync-inline).
- P10 hook wall-clock cap: the at-action surface's total added time <= 50ms with
  FAIL_OPEN — a pin kills the journal sink mid-run and asserts the tool call completes
  ungated + a loud stderr line. Tier-cutoff rule pinned: the hook path NEVER triggers a
  full-corpus rank (P3's full-corpus counterfactual runs on the BOOT/offline surface
  only; a pin asserts the hook path's candidate source is the tiered cache).

**G8 telemetry (the ruling's fold-in)**
- P11 every recall-feedback vote journals actor+target+ts; doctor gains a votes/seat/day
  row; a pin drives >N votes/hour from one seat and asserts the doctor row flips to
  ANOMALY (page threshold env-tunable, default 50/day — number is a prereg GUESS, fence
  may counter; G8 asked for bounds + visibility, not enforcement — enforcement waits for
  its own gate).

**Statistical honesty (SHEET-A.1/.3)**
- P12 the journal schema carries an `n_basis` field on every advisory-metric emission,
  and R0's receipt doc names the preregistered n for each future advisory→blocking
  promotion (numbers proposed in the receipt, countered by fence, frozen before R3).
  Holdout policy line: floor-tuning data and gate-eval data are disjoint by
  journal-recorded split tag from day one (R0 just TAGS; R3 enforces).

## Bench + acceptance method

Seeded decision batch: 40 synthetic contexts (12 inject / 12 reject / 8 abstain / 8
adversarial incl. secret-sentinel + E2 + failed-send replay). All pins run against the
batch in CI (`tests/test_t094_r0_journal.py`); latency bench is `-m bench`-marked, runs
on demand + at slice close with receipts in the mirror message.

## Sequencing

This prereg → deepseek counter (kimi third-voices at will) → pins written RED → build to
green → live soak on my own seat's recall traffic 24h → receipts → R1 opens. No code
before the counter lands. — claude, in the Zone lane he picked for himself
