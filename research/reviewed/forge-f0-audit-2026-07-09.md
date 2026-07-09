# Forge F0 — data-sufficiency audit (dual pre-registered criteria)

**Provenance**: 2026-07-09. Instrument: core/recall/replay.py (claude, tested, read-only),
run live via `recall-curate --forge-audit`. Judged against TWO independently
pre-registered criteria sets, both committed BEFORE the audit ran: claude's (design doc
sec.9 F0, git-timestamped) and DeepSeek's (fenced, bifrost 1783569850261-0; full
reasoning in its runner transcript). DeepSeek additionally ran its own code-reading
audit after un-fencing. Ledger: T013.

## Verdict (joint): FALLBACK — build F0b capture-side accrual; edits path may proceed under the human gate; merges wait.

Neither GO nor NO-GO. The replay premise held up (targets are concrete, replayable, and
the pipeline reproduces itself); the CREDIT-side validation data is durable but thin, and
the NOISE-side ledger is a rolling 7-day window. Both criteria frameworks — written
blind to the data and to each other — converge on capture-side accrual as the next slice.

## The instrument's live numbers (claude criteria, as-registered)

- Durable flips on the event-log firehose: **31**, targets **100% replayable** ->
  criterion 5 NO-GO: **clear**; criterion 3b (>=80% resolvable): **pass**.
- Credited lessons: **15**; with >=2 distinct credited contexts: **1** (6.7% << 50%) ->
  **criterion 3 FAIL** — the merge/regression axis is data-starved.
- Rehab candidates (surfaced>=10, credit 0): **4**; with >=8 reconstructable surfaced
  contexts: **75% >= 70%** -> **criterion 2 PASS** — the edit path's axis-B data exists
  (rehab candidates are active lessons; the rolling window keeps refreshing them).
- Injection-ledger retention: **6.9 days** (the 7d prune, measured live).
- Fidelity (criterion 1, as-registered): **FAIL — 17/80 (21%)** over the 48h sample.

## Fidelity decomposition (the FAIL is the system's history, not the harness)

157 (source,target) pairs decomposed by cause (scratchpad fidelity_decompose.py):

| cause | pairs |
|---|---|
| agree on replay | 25 |
| entry pre-dates the vNext regime (floor 0 -> 0.20 + trigger-aware relevance shipped 2026-07-08 01:52) | 120 |
| source now benched/graduated (curator applied post-entry — correct behavior change) | 11 |
| genuine mismatch on current regime | **1** |

Post-vNext agreement: **25/26 = 96.2%**. The single genuine miss
(bifrost_deepseek_runner_live @ a wake command) is explained: mined-trigger vocabulary
is derived from credited flips and credit votes were cast DURING the audit day — the
matcher is credit-adaptive, so its decisions drift with every credit even within a
regime. FINDING: bit-fidelity to history is unattainable by design; the criterion's
INTENT (detect harness wiring bugs) is satisfied — zero wiring bugs found. The
as-registered FAIL stands on the books (pre-registration discipline: no post-hoc
threshold rescue); F1 refines the criterion to "fidelity against a frozen counter
snapshot," which measures the harness rather than the corpus's live evolution.

## DeepSeek's criteria + audit, and the two-way corrections

DeepSeek's blind thresholds: axis A needs >=2 credited contexts/lesson + >=8 events over
>=3 lessons system-wide; axis B >=3 noise contexts/lesson + >=30 over >=5 lessons;
fallback if retention < 21d, or <3 qualifying credited lessons; NO-GO only if the
premise is unmeasurable (<5 credits AND <15 noise contexts) or edits show no/inverted
discrimination once measured.

Its audit (by code-reading): **F1 fires** (7-day prune — confirmed live: 6.9d),
**F3 fires** (predicted 0-2 lessons with >=2 recoverable credits; actual: 1),
F2 marginal-pass (~36% recoverable), **N4 does not fire** (premise measurable).
Verdict: WAIT + capture-side accrual.

**Correction to DeepSeek's audit (it read code, not runtime):** flips are DUALLY
recorded — the tempdir _FLIP_DIR copy it found is indeed 7-day-pruned, but
claude_posttooluse.py also emits `capture_event("flip", {target, credited, sources})`
onto the durable event-log firehose. The 31-flip durable record exists and is what the
instrument replays. Its "flip contexts are ephemeral" conclusion is therefore wrong in
the letter — but right in the consequence: 31 durable flips still yield only ONE lesson
with >=2 credited contexts, so the credit-side starvation stands either way.

**Correction to claude's criteria (the fence's catch):** my criterion 3b asked whether
flip targets are RESOLVABLE (concrete strings — they are); DeepSeek's F1 asked whether
noise contexts are RETAINED (they are not, past 7 days). Resolvability was never the
risk; retention was. Blind, it put a threshold on exactly the variable my set treated as
a background assumption. That asymmetry is the pre-registration fence working.

## What F0b must do (next slice, proposed)

Persist replay contexts DURABLY at the moment they exist:
1. At credit time (the scarce, precious signal): extend the existing durable flip event
   -- it already carries (target, sources); add the altitude + query string. Cost: ~5
   events/week. Effectively free.
2. At surface time (axis B): append injection-ledger entries to a durable, bounded
   store (event stream or non-pruned data dir), capped/rotated (~44/day is trivially
   cheap). The 7-day temp ledger stays as-is for its cost-observability job.
3. Re-audit gate (DeepSeek's, adopted): re-run `--forge-audit` when >=15-20 NEW credit
   events with persisted context have accrued; unblock the merge axis then.
4. Meanwhile the EDIT path (rehab class) proceeds under the trust ladder's human gate:
   its axis-B data passed coverage today, axis-A is vacuous for never-credited lessons
   by definition, and reversibility + the human gate absorb the residual risk (both
   criteria sets agree this class is the least data-hungry).

## Instrument shipped

core/recall/replay.py (+8 tests) behind `recall-curate --forge-audit` (read-only).
Criteria constants live in the module mirroring sec.9; changing them requires a
design-doc edit by convention.
