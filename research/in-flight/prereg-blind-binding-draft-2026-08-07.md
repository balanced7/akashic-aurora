# PRE-REGISTRATION: can a blind drafter reproduce the binding table?

Written 2026-08-07 ~17:35 by claude#69363f5a, **before running the draft**.

## The limit this addresses

T227 shipped with a stated defect: **I authored the bindings by reading the code and ratified
my own drafts.** The rules are fixture-validated; the table is not. A 7/7 MATCH against a
table I wrote from the same source is partly tautological.

A fan **cannot ratify** — that is the irreducible human step, and T207 measured that the
"therefore" is exactly what a helper gets confidently wrong. But a fan **can draft blind**,
and a diff between an independent draft and mine is real evidence about the table.

This is `blind_crosscheck_needs_fencing` applied: the helper gets the raw question and
**never sees my answer**.

## Method

For each concept, a helper receives ONLY:
- the concept name and a one-line definition
- the instruction to name the mechanisms implementing it, as `file` + `pattern`

It does **not** receive my table, my mechanism list, or the count. Then I diff.

Two strata, and the first is the calibration:

- **CONTROL (3 terms already in the table)** — `drained`, `confidence`, `undetectable`.
  Agreement here measures whether blind drafting reproduces a known answer.
- **CANDIDATES (new terms)** — drafts for a human to ratify later, never auto-adopted.

## Predictions, recorded before looking

- **P1: the drafter finds `drained`'s three cursor families.** They are co-located in
  `core/comm/bus.py`, so a competent reader looking at one file should see all three.
- **P2: the drafter MISSES the `confidence` fork.** Its two mechanisms live in different
  subsystems (`core/context/learning_loader.py` and `core/narrative/tagging.py`), and finding
  both requires knowing to look on the narrative plane at all. **If P2 holds it tells us what
  human ratification actually has to add: cross-subsystem reach, not local reading.**
- **P3: at least one candidate draft names a mechanism I would not have thought of.** The
  whole reason to ask someone else.

P2 is the one I care about. A blind drafter that reproduces same-file forks and misses
cross-file ones would mean the fan's real contribution is *volume on the easy cases*, and the
human's is *the cases that span planes* — which would be a concrete division of labour rather
than a slogan.

## Stated blindness

- The helper sees no repo context, so a miss may be "could not find the file" rather than
  "did not think to look". I will distinguish those in the triage, not in the score.
- Agreement with MY table is not agreement with TRUTH. My table could be wrong in the same
  way twice; that is the shared-blind-spot case and this design cannot detect it.
- n is small. This locates disagreements; it does not estimate a rate.
