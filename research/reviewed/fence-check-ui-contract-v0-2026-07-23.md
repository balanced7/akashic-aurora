Status: current
Type: fence report · Arc: partner night / check_ui_contract · Build: deepseek (c31da1c) · Fence: claude · Date: 2026-07-23

# FENCE — check_ui_contract.py v0 (G6 split: deepseek build, claude fence)

**VERDICT: CONDITIONAL PASS.** M-L8 + M-L1 are fence-green and usable advisory tonight.
M-L3 is RED with two probe-proven defects — fix loop to deepseek, re-fence bar below.

## Method

Probe battery (per d3_mojibake_guard_fenced: true positives crafted from the actual
signature classes, not from what looks wrong), then false-positive traps, then the
incumbent run. Probe files: scratchpad probe_true_positives.py / probe_false_positives.py
(6 TP + 7 FP-trap constructs).

## Results

**True positives: 5/6 caught.**
- TP1 raw hex CSS callsite ✅ · TP2 raw hex JS literal ✅ · TP3 gauge missing title ✅ ·
  TP4 gauge missing data-agent ✅ · TP5 `warn` without predicate ✅
- **TP6 `tripped` without predicate — MISSED (RED #1):** `"tripped"` is a member of BOTH
  ALARM_CLASSES and STATE_PREDICATES, so any line containing the token self-satisfies the
  predicate check. Law 3 is structurally dead for its flagship alarm class — a check that
  cannot fire. Consequence: the incumbent's M-L3 = 0 report is UNTRUSTWORTHY (the zero is
  exactly the class of lie the tool exists to prevent).

**False-positive traps: 6/7 clean.**
- Token definitions, var() fallbacks, JS comment hex, same-line predicate, prev-line
  predicate: all correctly passed ✅. `.highlight` escaped only by adjacency luck (prev
  line contained "tripped" = predicate) — substring risk stands.
- **`--warn-ink` variable name flagged as alarm token (RED #2):** substring matching hits
  "warn" inside CSS custom-property NAMES. M-L8 already strips `--[\w-]+` definitions —
  M-L3 should reuse that cleaning; symmetry is free.

**Incumbent run:** M-L8 = **53 raw-hex callsites** (true findings — the debt ledger the
CONTRACT ratification needs; deepseek predicted these). M-L1 = **1**: L1908 fence-state
gauge has title but no data-agent — TRUE per law-as-written, and it surfaces a real
ratification question: a fence gauge measures a FENCE, so the axis law may want
`data-measure` generalization instead of agent-only. Filed for Daniel's gate package.
M-L3 = 0 — void until RED #1 is fixed.

## Fix suggestions (builder's call on mechanism, per R001)

1. Remove `tripped` from STATE_PREDICATES; represent tripped-GATING as comparisons
   (e.g. `==='tripped'`, `.state==='tripped'`) so USE (class assignment) and PREDICATE
   (comparison) are distinct token shapes.
2. Word-boundary token match (`\b(tripped|warn|high)\b`) AND strip `--[\w-]+` custom-
   property names before matching (M-L8's own cleaning pattern, reused).
3. Cosmetic, sturdiness: checker output em-dashes mojibake on cp1252 consoles (the
   rule-8 irony) — ASCII-only message text is scar-consistent.

## Re-fence bar (pre-registered)

TP6 flags · FP `--warn-ink` passes · TP5 still flags · `.tripped{` class-def still
passes · incumbent M-L3 re-read with receipts (zero must be EARNED, not structural).

## Standing rails confirmed

No ship.py/pre-commit wiring landed (deepseek deferred — matches the advisory
greenlight). Blocking flip rides Daniel's CONTRACT v0 ratification as a one-liner.

*Red is a gem: TP6/FP-warn-ink are exactly why the fence exists — the same loop that
caught-and-fixed three sighted-fence findings in one cycle last night. — claude*
