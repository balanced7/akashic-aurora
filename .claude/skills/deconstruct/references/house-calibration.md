# The calibration case: the house (2026-10-13)

Moved here from `../SKILL.md` on 2026-10-13 so the skill that always loads stays short, and corrected the same day
after an adversarial review of the run (its fixes are listed at the end).

The card was first calibrated on our own house: 8 subsystem cards plus a whole-house report, all in
`research/in-flight/deconstruct-the-house-2026-10-13/`. The full record is
`research/in-flight/deconstruct-the-house-2026-10-13/the-house-deconstructed.md`, and its prediction register is
`research/in-flight/deconstruct-the-house-2026-10-13/predictions-house.md`.

## What it found

- **Thesis:** the house writes, stores and measures very well, but its readers were built late, aimed at the wrong
  population, or never wired. Two thirds of its false first principles (18 of 27) are stale, scope-dropped or
  unwired sentences that nobody re-measured, and at least two were wrong from the day they were written. Its fixes
  land in one organ while the same bug lives on in that organ's twin.
- **The data plane is sound:** 116,693 ledger and atom lines with none torn; 1,028 atoms that rehash clean; RED
  before GREEN on at least 37 of 39 builds. **The control plane is where it breaks:** of 54 loops, 7 are closed and
  26 are open by defect. 14 of those 26 have no reader or no clock, and 16 scheduled tasks run while none of them
  runs any of the seven drift readers the report names (some watchdogs do read gauges of their own).
- **Verification:** the cards ran 108 predictions. Read by direction, 78 exposed a defect, 27 were good news, and 3
  were inconclusive or not run. 19 more ran at house altitude: 18 held and 1 failed (H5: the territory moved during
  the run).

## The doctor: a partial catch, not a clean one

The brief that launched the run listed "doctor WITHOUT --page" as a read. It is not one. Every round of
`examine_fleet` can push page-grade findings to the human pager whatever `--page` says, retract standing pages and
delete their escalation keys, and set or clear per-agent stall keys (`core/comm/doctor.py:138-155`, `:1604-1608`,
`:1640-1642`, `:1653-1720`).

**1 card caught it in code, 2 ran it as a read, the house seat declined it.** The bus card found the writes in code
and by replay, and declined the verb. The doors and method cards ran it as a read before that catch reached them;
their side-effect blocks now say so, with the effect unknown, because pages leave no durable record. The house seat
declined it, but its report still uses readings from those two runs. The brief generator's read list still carried
the wrong rule after the run: a twin defect, fixed in the skill and not yet in the script that writes briefs.
Changing the rule is Daniel's call.

## What the house taught the method

Section 11 of the report, now built into `teardown-card.md` v2 (this folder): the loop table with its fixed
vocabulary; the direction column; Row 4's two fields, verdict list and "last measured" date; "could this test fail
for the right reason?" plus negative controls; checking that a verb is a read; the required footprint block;
summaries that carry all eight rows; resolving unknowns across cards; time stamps and re-running at synthesis;
splitting Recommendation from Proceed?; and Row 6 asking for both orders. The Great Sage voice mostly held: it
leaked once, when the house report's Notice stated an inferred cause as an observation.

## What the adversarial review fixed (2026-10-13)

The review opened 23 pointers (22 exact) and re-ran 12 predictions read-only (all 12 replicated). The evidence held;
the write-up did not, in these places, all now fixed:
- the skill's router named files that only another workflow's uncommitted work holds, so a clone would see dead
  routes (now pinned by `tests/test_deconstruct_skill_router.py`, which skips with the reason while a target is
  untracked);
- two cards ran `doctor` and called it a read, and the story above said the auditor declined it;
- private numbers (spend figures, private-plane sizes, counts and dates) had been copied into files bound for the
  public repo;
- "they decayed; nobody made them up" was a guess presented as a law;
- one house principle (HP9) reversed its own source, and two verdicts were outside the fixed list;
- the headline false principle misquoted its target (the docstring prices a 1 ms file read, measured at 9 ms; the
  153 ms whole call was never priced);
- some proposals changed a part without stating why it exists (the width gauge, the library generator, Redis's
  journal, the operator tables);
- the prediction registers lived only in a scratch folder (now copied into the record folder);
- one prediction's direction contradicted the tally, and several pointers and words slipped.
