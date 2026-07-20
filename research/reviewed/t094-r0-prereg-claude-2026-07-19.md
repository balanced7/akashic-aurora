# T094 R0 — Pre-registered pins (claude half, v2 — deepseek counter FOLDED)

Binds: reconciliation §4 R0 (AS AMENDED by t094-amendment-sheet-v1 SHEET-A) + G8 ruling
(vote telemetry rides this same observability pass) + method-baseline M1 (pins RED before
code; the fence countered THIS DOC before a line of implementation lands).

v2 changelog (2026-07-19 late): deepseek's adversarial counter
(research/reviewed/t094-r0-counter-deepseek-2026-07-19.md, note ADR_0719195450) folded in
full — all 5 amendments accepted, both gaps closed with new pins P13/P14. Per-change
markers: [A1]..[A5], [G1], [G2]. v1 is this file's prior git revision. Blocking-vs-smoke
tiering per SHEET-D now explicit on every pin.

## What R0 is (and is not)

The decision journal + explain verb: every recall decision (inject/abstain/reject) becomes
a durable, explainable record. ZERO behavior change — R0 observes the incumbent; it never
alters ranking, floors, tiers, or surfacing. (F2 law: no live metric feeds ranking.)
NOT in R0: label repair (R1), policy unification (R2), gates (R3). G8's vote-rate
telemetry IS in R0 (same instrumentation seam, per Daniel's ruling).

## Module plan (fence-affirmed)

- `core/recall/journal.py` — append-only decision journal on the Ledger (events family
  `recall:decision`), write-behind so the hot path never blocks on durability.
- `agent_cli.py recall-explain <decision-id|ledger-ref>` — the drill verb.
- Instrumentation call sites, BOTH surfaces [G1]:
  - tool-action surface: `core/recall/at_action.py` (recall_at, at_action.py:902) — emit-only.
  - boot surface: `context/learning_loader.py` (load_learnings_ranked_by_relevance — the
    REAL seam; v1 cited `core/context/relevance_budget.py`, WHICH DOES NOT EXIST — that
    name belongs to T071-R1's future budget module. Boot recall rides the Context pillar's
    own Ranker (chain: agent_cli.py:169 → agent/initializer.py:43 →
    context/aggregator.py:67 → learning_loader.py:29) and NEVER passes through recall_at().
    R0 instruments this seam where it lives — emit-only, same schema, `surface=boot` tag —
    rerouting boot through recall_at() would be a behavior change and is out of scope.)
- G8 half: vote-write telemetry in `recall_feedback` path + `doctor` row.

## Pre-registered pins (RED first; each cites its spec line)

Tier legend [A5]: BLOCKING = merge-gating; SMOKE = runs every commit, alerts on failure,
never blocks (point-exhibits per SHEET-D — a legitimate ranker change may retire them).

**Journal integrity**
- P1 BLOCKING — every decision writes one journal row carrying ALL §4-R0 fields:
  decision_id, context signature (REDACTED), candidate set w/ per-feature contributions,
  matched rule/tier/tokens, selected/rejected/abstained + reason, position, render_tier,
  chars, latency, engine/rules/corpus versions, split tag [A3], n_basis, surface
  (action|boot) [G1].
- P2 BLOCKING — SECRET SENTINEL: a context containing a planted secret (key material
  shape) journals with the sentinel REDACTED — the raw secret appears in NO journal field.
- P3a SMOKE [A1] — synthetic plant: a planted lesson that candidate-generation would miss
  under any future cap still appears in the below-floor record. (v1's P3; the counter
  correctly names it a tautology — it proves plant-detection machinery only. Kept as smoke.)
- P3b BLOCKING [A1] — production miss probe: replay the LAST 48h of recall-at surfaces
  through the below-floor logger; assert at least one lesson that DID surface (above
  floor, top-3) would fall BELOW floor under the R4 candidate cap. Zero such lessons =
  the pin reports "cap harmless on this corpus" and passes WITH that receipt named (the
  S1-compatible reading: R0 instruments before R4 caps, so what a cap would hide is
  visible). One-or-more = the journal provably catches what the cap would hide.
- P4 BLOCKING — abstention rows journal too: a silence decision (floor not met) produces
  a row with abstained+reason — silence is a decision, not an absence.

**Explain verb**
- P5 BLOCKING — `recall-explain <id>` renders every field of P1 human-readably, including
  the S1 CAVEAT LINE on every output: "flip-labels exist only on struggle episodes;
  prevention-shaped value is invisible to them" (SHEET-A.4).
- P6 SMOKE [A5] — explain names E2's matched tokens/weights on the E2 replayed context.
  (Point exhibit; if a future ranker legitimately retires E2's lesson, this SHOULD fail
  without blocking the merge.)
- P7 SMOKE [A5] — on a replayed failed-send context, explain shows
  `bifrost_send_text_ordering` in-top-3 with score>floor. (Point exhibit, same rule.
  Still poetry; poetry doesn't gate merges.)
- P8 BLOCKING — 100% of injected test decisions fully explained (no field
  missing/unknown) — completeness over the seeded batch.

**Latency (benched, baseline-relative [A2])**
- P9 BLOCKING [A2] — bench the CURRENT recall_at hot path FIRST (cold cache / warm cache /
  no-cache, 200 emissions each) and freeze the baseline in the receipt; the journal
  emit's ADDED cost = delta over baseline, p95 delta < 5ms. Absolute numbers ride the
  receipt; the pin asserts the DELTA only.
- P9b BLOCKING [A2] — the FAIL_OPEN drill (P10) additionally asserts total tool-call
  latency did not increase >50ms while the sink was dead — fail-open must be fail-FAST.
- P10 BLOCKING — hook wall-clock cap: kill the journal sink mid-run; the tool call
  completes ungated + a loud stderr line. Tier-cutoff rule pinned: the hook path NEVER
  triggers a full-corpus rank (P3b's replay runs on the boot/offline surface only; a pin
  asserts the hook path's candidate source is the tiered cache).

**G8 telemetry (rate × confirmation-ratio shape [A4])**
- P11 BLOCKING [A4] — every recall-feedback vote journals actor+target+ts+vote-kind
  (explicit useful vs automatic helped-flip distinguished); doctor gains a votes/seat/hour
  row over a rolling 4h window; a pin drives sustained synthetic traffic and asserts the
  ANOMALY flag fires at: rate >15/hour sustained 4h AND explicit-useful ratio <10%.
  A burst seat (30 credits in 2h, then quiet) must NOT flag — the pin includes this
  negative case. Numbers 15/10% remain prereg guesses by DESIGN — recalibrate after 72h
  of live telemetry, never before; G8 asked for bounds + visibility, not enforcement.

**Statistical honesty (SHEET-A.1/.3 + [A3])**
- P12 BLOCKING — the journal schema carries `n_basis` on every advisory-metric emission,
  and R0's receipt doc names the preregistered n for each future advisory→blocking
  promotion. Split-tag policy: floor-tuning data and gate-eval data disjoint by
  journal-recorded split tag from day one (R0 TAGS; R3 enforces).
- P12b BLOCKING [A3] — cross-tag contamination pin, runnable in R0: plant a lesson used
  in floor calibration (by source); assert its journal rows all carry `split=tune` and NO
  row for that source carries `split=gate`. Mechanical, needs none of R3's machinery.

**Surface coverage + durability (the two gaps [G1][G2])**
- P13 BLOCKING [G1] — boot-surface coverage: a boot run (`boot <agent> --task ...`)
  produces one journal row per lesson surfaced in LESSONS/CONTEXT, `surface=boot`, schema
  identical to action rows (P1 fields resolvable), and recall-explain renders them. The
  blind spot the counter named — every agent's first N turns — is closed by construction.
- P14 BLOCKING [G2] — write-behind durability contract, stated + proven: rows are
  best-effort by design (lost-in-queue on crash is a GAP IN THE RECORD, never corrupted
  state). Pin: SIGTERM the process mid-recall batch, restart, assert (a) every row with
  decision_id below the kill point is intact — no torn rows; (b) the flush gap is
  DETECTABLE from the journal's contiguous per-process decision_id sequence (the reader
  can say "rows N..M lost", never silently absent). (Windows note: the drill uses the
  process-group CTRL_BREAK pattern per windows_ctrl_break_requires_new_process_group.)

## Bench + acceptance method

Seeded decision batch: 40 synthetic contexts (12 inject / 12 reject / 8 abstain / 8
adversarial incl. secret-sentinel + E2 + failed-send replay) + one live boot invocation
(P13) + the 48h production replay (P3b). All pins run in CI
(`tests/test_t094_r0_journal.py`); latency bench is `-m bench`-marked, runs on demand +
at slice close with baseline receipts in the mirror message.

## Sequencing

v1 prereg → deepseek counter (FILED, PROCEED + 5 amendments + 2 gaps) → THIS v2 folds it
→ deepseek verifies v2 → pins written RED → build to green → live soak on my own seat's
recall traffic 24h → receipts → R1 opens. No code before the v2 verify lands.
— claude (v1 night run; v2 same day, counter folded whole — every amendment accepted, no
dissent to record)
