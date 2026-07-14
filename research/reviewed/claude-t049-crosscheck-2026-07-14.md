# claude cross-check — T049 fence-protocol v2 draft (2026-07-14)

Status: current (2026-07-14)
Class: counter-check of research/reviewed/deepseek-t049-fence-v2-draft-2026-07-14.md —
written IN the draft's own proposed M1-CC economy (one-line affirms; full text only on
adjustments) and after the draft's own M1-PV pass (every cited path verified to exist;
both M1 PROTOCOL/RECEIPTS insertion anchors confirmed in docs/method-baseline-2026-07.md).
Gate: Daniel ratifies per-amendment. This cross-check completes the preparation.

## Verdicts (M1-CC style)
- **A1 M1-PV — AFFIRM (CERTAIN).** Receipts real (r1/r2 records verified); section-scoped
  invalidation + verify-evidence-before-reading-arguments is a genuine anti-bias mechanic.
  Nit at adoption: typo "INVLAIDATION" (draft line 25).
- **A2 M1-CF — AFFIRM (CERTAIN).** Four-value vocabulary is minimal and sufficient; both
  cited reconciliations verified; R2's network-on-chip drift is exactly the case the
  missing-tags signal would have caught pre-read.
- **A3 M1-LITE — AFFIRM WITH TWO ADJUSTMENTS (below).**
- **A4 M1-BRIEF — AFFIRM (CERTAIN).** The recall-networking brief IS protocol-heavy
  (verified); the missing DESIGN-ONLY marker matches my own r1 root-cause finding
  verbatim. The five-section contract + relief-valve is the right fix.
- **A5 M1-CC — AFFIRM (CERTAIN).** The receipt is self-indicting (his own R3: ~80%
  re-proof) — maximal credibility. Length-as-signal (long counter-check = fence failed)
  is a clean operational read.

## A3 adjustments (the only full-text items)
1. **Bright-line path list omits the Ledger.** Full-fence trigger 1a names core/comm/,
   core/trust/, core/foundation/store.py — but core/foundation/ledger.py is exactly the
   "a bad event survives the revert" case that trigger 1b itself names as DATA LOSS.
   Adjust to: `core/foundation/` (the whole pillar) — Store AND Ledger are both
   poison-on-revert surfaces. The list stays extend-only per the draft's own rule.
2. **Tier gap: the 2-file non-mechanical change.** Fence-lite requires blast >= 3 files;
   no-fence requires mechanical nature (typo/rename/bugfix-with-pin) and trivial revert.
   A 2-file substantive change (new small capability, 2-file design decision) satisfies
   NEITHER tier as written. Add a default clause: "a change that fits neither tier 2 nor
   tier 3 takes FENCE-LITE" — under-fencing must never be the fall-through.

## T031 wiring (confirming the draft's own note 3)
Mechanically checkable, add to the T031 lane: M1-PV (reconciliation header lists the
verify pass), M1-BRIEF (five sections present), M1-LITE (tier recorded in the slice's
ledger entry). M1-CF/M1-CC stay reviewer-enforced.

## RECOMMENDATION TO DANIEL
ADOPT all five with the two A3 adjustments + the A1 typo fix, applied at merge time into
docs/method-baseline-2026-07.md. Nothing in the draft weakens the existing contract —
all five are additions, and two (M1-PV, M1-BRIEF's relief valve) are already validated
by tonight's live failures and fixes.
