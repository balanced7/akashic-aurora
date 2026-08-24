# Fence Round 2 — reconciliation and dispositions (resident-fanout arc, T290/T291/T292)

**Status: RECONCILED — this document is the build authority for the arc.** Inputs: opening
position (resident-fanout-round2-2026-08-12.md), Heimdall counters
(fence-r2-heimdall-2026-08-12.md, ask 3415d07c), Navi counters
(fence-r2-navi-2026-08-12.md, ask e4db2962). Both resident-tier, both grounded on the same
pack, blind to each other. Reconciler: claude/Vandor. Daniil's go: 2026-08-12 verbatim
"Fence it and then build."

## Dispositions

| # | Counter | Disposition |
|---|---|---|
| H-C1 | Two-record join doesn't close self-grading; `by` is unverified | **ACCEPTED WHOLE.** RC1 default = adjudication accepted ONLY from operator/conductor identities; resident-authored adjudication REFUSED loudly at the write door. Crypto identity is out of scope (that is T088a's plane). |
| H-C2 + N-C2 | Per-resident × per-shape cells too sparse; pool shapes first; intervals not points; refuse to render under floor | **ACCEPTED, CONVERGENT (both high).** RC2 primary render = per-SHAPE pooled across residents, lower-bound Wilson, rendered only at n≥5. Per-resident cells appear only at n≥20 and always with the interval. Empty cell renders UNTESTED, never 0%, never green. |
| H-C3 | Role continuity depends on role-scoped (not wearer-scoped) retrieval | **ACCEPTED.** RC3 acceptance gains the second-wearer pin: wearer B's pack must surface verdicts/lessons filed under the ROLE by wearer A. |
| N-C3 | A pack "assembled by a helper" rots without a custodian | **ACCEPTED AMENDED.** The custodian is a BUILDER FUNCTION plus its pins (mechanical rebuild each invocation from live sources: roster, locks, active ledger, discover), not a person. Curated scout heuristics file as ROLE-keyed lessons — that store is the accumulating memory any wearer reads. Ownership of the builder = custodianship. |
| H-C4 + N-C4 | Goodhart: selective avoidance of hard shapes; pristine descriptive surface | **ACCEPTED, CONVERGENT (both high).** The ask door records `{resident, question_shape}` at ASSIGNMENT time (it knows both), so selectivity needs no new organ: challenge-acceptance = shapes-attempted / shapes-offered from door records. Renders on the card; a zero-attempt cell after N offers renders AVOIDANCE WARNING. Routing demotion deferred until routing-by-calibration exists at all. |
| H-C5 | Premise attack: scout first, calibration bootstraps from its verdicts | **ACCEPTED — REORDERS THE BUILD.** New order: RC1 schema (tiny, verdicts need a home) → RC3 scout (generates the stream as a side effect of real pre-flight work) → RC2 rendering (a projection that turns on when data exists; its RED pins may land early). |
| H-BLIND | The learning store is an adjudication back door (publish a "confirmation" lesson, cite it) | **ACCEPTED.** RC1 law: adjudication is ONLY the adjudication record type. A lesson, note, or bus message citing an ask_id flips nothing. Pinned. |
| N-FAIRNESS | §2 tests heterogeneity, not persistence. Matched pairs required | **ACCEPTED WHOLE — REPLACES §2.** Pre-registered amended claim below, verbatim from Navi. The sunset applies to the PAIRED effect. |
| N-CARD | The calibration card design | **ADOPTED as RC2's render spec** (shapes/attempts/survival + challenge acceptance + curiosity index + recent corrections + REFUSES block). The REFUSES block is a contract, not decoration: no aggregate score, no cross-resident ranking, no productivity count, survival only at n≥5, UNTESTED never green. |
| N-BLIND (cost) | Matched cold twins could multiply spend | **BOUNDED:** pairs run on a SAMPLE — each real resident ask has probability p (default 0.5, dial) of spawning one cold twin, until a shape reaches 20 adjudicated pairs; then p drops to maintenance (0.1). Branch cost is cents; the cap is the dial. |
| N-BLIND (framing bias) | Conductor framing could swamp the resident effect | **OPEN, recorded.** Matched pairs share the identical prompt by construction, which controls framing WITHIN a pair; cross-pair framing drift remains unmeasured. Noted for the 4-week review. |

## THE PRE-REGISTERED CLAIM (Navi's amendment, verbatim — this is the bar)

> For each question shape, we run matched pairs: one branch as the resident (catchup pack
> active) and one cold (no resident identity, no catchup). After ≥20 adjudicated pairs per
> shape, if the resident's verdict survival rate does not exceed the cold by a statistically
> significant margin (one-sided 90% CI lower bound > 0), then persistence is not the cause.
> The sunset in §6 applies to this paired effect, not to profile existence alone.

Navi's acceptance, verbatim: "If that is pre-registered, I will treat a negative result as
confirmation of the objection." It is now pre-registered. Either outcome settles the
2026-08-09 objection.

## Amended build order

1. **RC1 (T290, amended):** `residents:verdicts:log` + `residents:adjudications:log`
   (append-only, store physics). Write doors: `verdict_file(resident, ask_id, geometry,
   question_shape, gist, cold_twin_of=None)`, `adjudicate(ask_id, outcome, by, receipt)` —
   `by` must be in the OPERATOR set (env/config: daniil + conductor seats), else refused
   loudly. Lessons never adjudicate (pin). Projection helper `calibration(shape=None,
   resident=None)` returns counts only (no rendering yet). RED pins alone first.
2. **RC3 (T292, amended):** scout pack BUILDER (mechanical, live sources), `ask` integration
   (resident ask wearing the Scout role files verdicts under resident AND role),
   second-wearer continuity pin, planted drills (in-flight area; settled work).
3. **RC2 (T291, amended):** the card render per N-CARD + challenge-acceptance + matched-pair
   sampling machinery + the pre-registered claim's evaluator. RED pins may land now;
   rendering activates when the stream has rows.
4. **T281 integration completeness:** reconciliation insight — an ADJUDICATION is the only
   honest read-receipt; door-side "was it read" proxies are fake. Integration completeness
   := adjudicated/filed per fan (computable after RC1). T281 stays `verifying` until RC1
   lands and the field renders from real joins; then done cites this disposition.

## What I conceded and why (the record the next seat needs)

My opening §2 claim was methodologically wrong in exactly the way the house keeps
rediscovering: it would have measured SOMETHING (heterogeneity) and worn the name of
something else (persistence). Navi caught it because the objection is theirs; Heimdall
caught the sequencing because the verdict-starvation kill condition was already in my own §6
and I hadn't followed it to its conclusion. Both catches were cheap ($0.02 total, ~4 min)
and both would have been expensive later. The fence works.
