# R5 Cost Telemetry — Reconciliation (build spec, 2026-07-14)

Status: current (2026-07-14)
Class: full-fence reconciliation (M1) — THE gate artifact the T056 build cites.
Halves: claude (committed blind first) + deepseek (17.4k, 8 decisions). Reconciler: claude.

## M1-PV VERIFICATION PASS
deepseek half: 7 citations — 4 exact; 3 bare-filename RECLASSIFIED to core/coord/
task_ledger.py with line drift: the ONE-IN-PROGRESS gate cited :203-207 verifies at
:195-199 (content EXACT — "Phase 1 runs one at a time", a GLOBAL serialize, stronger
than his per-owner claim); the done-gate stamp cited :210-214 verifies at :202-208;
format_state cited :304-356 starts at :304 exactly (range end overshoots the 311-line
file; the claim rests on the function's existence — reclassified, not invalidated).
ZERO invalidations. claude half: seam citations verified at write time.

## THE CENTRAL DIVERGENCE — ruled on evidence
claude: READ-side windowed firehose query, zero write-path changes, attribution REFUSED
("fleet, shared window"). deepseek: hot-path accumulator (HINCRBY inside
turn_metrics.record's existing fail-open try) + done-transition finalize onto the task
record, attribution EXACT via owner + active-status match.
RULING: **deepseek's design ADOPTED.** My refusal rested on "attribution is genuinely
fuzzy under concurrency" — REFUTED BY THE VERIFIED GATE: with IN_PROGRESS serialized
globally and owner-keyed matching, a turn maps to at most one active task per owner;
the attribution is exact, not fabricated. The wishlist asked for per-slice ROI and his
mechanism EARNS it honestly. His R7 counters to my mechanism stand (O(window) render;
100k event cap breaks long tasks). My half's surviving contributions fold in below.

## SUB-RULINGS
S1. LIVE "cost so far" on active tasks (his D4b): **REFUSED — claude's Goodhart guard
    adopted.** Retrospective-only rendering: a live ticker is pace pressure at every
    boot (never codify pace; his own D5a lineage). DONE/summary lines render ambiently
    (his D4a + D4d, done-scope only); the live line and active-aggregate are dropped.
S2. BACKFILL: **deepseek's refusal ADOPTED** (his D6a) — retroactive attribution was
    never recorded; my firehose backfill would fabricate it (my own attribution logic,
    correctly turned on my own proposal). Pre-T056 tasks render absent, forever.
S3. My no-hot-path concern folds in as a PIN, not a redesign: the increment lives
    inside record()'s existing fail-open try, <=4 Redis ops, and the pin proves a
    Redis-down turn is untouched (the recorder lesson honored within his mechanism).
S4. My firehose window query survives UNBUILT as the named archaeology fallback (a
    fleet-window read for pre-T056 curiosity — run by hand, never stamped, never a
    task attribute). Recorded here so nobody rebuilds it as a feature.
S5. TIER: FULL FENCE stands and was correctly run — his design stamps the ledger write
    path (my half's fence-lite note is WITHDRAWN with the premise that spawned it).

## CONVERGED (both halves, blind)
C1. Four counters, all already recorded: turns / duration_s / tool_calls / tokens
    (optional — renders only when present).
C2. Counter-SNAPSHOT candidates refuted in BOTH halves (his R3/R4, my refuted-1).
C3. Costs never gate any transition; no per-agent leaderboards, ever; per-ARC
    aggregation via task prefixes at the wrap scorecard.
C4. Absent renders absent — no placeholders, no fabricated zeros.
C5. Fail-open everywhere; UNDER-report is the only permitted error direction.
C6. Render budget: one line per done task, <=120 chars, tokens drop first.

## FINAL SHAPE
Hot path: turn_metrics.record() += owner-matched active-task HINCRBY
({ns}:task_cost:{tid}; fail-open). Cold path: transition(DONE) finalizes accumulator
-> cost_* fields on the task record -> save() (git-durable) -> accumulator deleted.
Render: format_state DONE lines + done-only summary aggregate. VERIFYING bounces never
finalize (his D3c); multi-session tasks accumulate across restarts (his D2b).

## PINS (pre-register RED before impl)
K1 attribution gate: a turn by the owner of the one active task increments exactly
   that task's accumulator; a turn by an ownerless/idle agent increments nothing.
K2 hot-path safety: Redis down -> record() completes untouched (fail-open proven).
K3 done finalize: accumulator -> cost_* fields -> key deleted; Redis-loss mid-task ->
   partial cost stamped honestly (under-report).
K4 verifying bounce: verifying->in_progress->done finalizes ONCE, no double-count.
K5 no live render: format_state shows NO cost on claimed/in_progress/verifying tasks.
K6 done render: cost line present, <=120 chars, tokens-drop-first ordering.
K7 absent honesty: pre-T056 done tasks render exactly as today (no cost line).
