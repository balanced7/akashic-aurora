# The retrieval regression gate has been RED for five days, and nobody heard it

Status: current | 2026-07-28 | claude | found while gating Sol's stream-wedge repair
AWAITING DANIEL'S GATE (it proposes a migration-completion task, not a test edit)

## WHAT IS RED

tests/test_lookback.py::test_the_preregistered_battery_passes -- 8 of 12 canonical
why-questions no longer return their governing artifact in top-3:

    C1/D1 why is the bifrost bus ephemeral      -> expected comms-pillar-synthesis
    C4    why does the forge gate edits         -> expected lesson-forge-design
    C5    the GPT experiment-pivot analysis     -> expected experiment-pivot-gpt-analysis
    C6    why does wake detect without consuming-> expected p0-wake-detect-design
    D2    why were CRDTs/consensus rejected     -> expected coordination-plan-synthesis
    D3    why is the ledger the substrate       -> expected coordination-plan-synthesis
    D5    where the forge blinded the optimizer -> expected 74d6e0d / 5562014

## WHY IT IS RED, AND WHY IT IS NOT A TEST BUG

This battery is not an ordinary test. Its own commit (e5c5cd4, T027/P7) calls it "a PERMANENT
CANONICAL-CORPUS REGRESSION PIN", dual-pre-registered BEFORE implementation, taken to 12/12
"after three ROOT-CAUSED rounds, NEVER TUNED". It measures the product claim directly: can a
why-question find the artifact that answers it.

It was 12/12 green at 77517d6 (2026-07-10). Then 425cf52 (2026-07-23) -- "P3: THE SPRAWL DIES
-- Daniel's gate verbatim: 'Delete the 643!'" -- removed 621 tracked docs and re-pointed
references to atom projections. VERIFIED: `git log --diff-filter=D` names 425cf52 as the
commit that deleted docs/comms-pillar-synthesis*, and the expected artifacts are absent from
docs/ AND from docs/library/design/ under their old names.

So the corpus was migrated OUT FROM UNDER the gate that measures it. The content survives as
atoms (the migration was lossless by design); the battery's expectations are name/id-based and
were never re-pointed. The gate went red the day of the migration.

## THE PART THAT MATTERS MORE THAN THE FIX

FIVE DAYS. A computed red, on the fleet's only end-to-end retrieval-quality gate, absorbed
silently into the suite's known-failure baseline -- the exact disease this arc has now hit
thirteen times (a red routed to a channel nobody reads). The ship_gate ratchet was built this
week to stop precisely this, and this red predates the ratchet's baseline, so the ratchet
INHERITED it as acceptable.

It is also the census's finding demonstrated on ourselves: NONE-EXISTS was 0 -- the knowledge
still exists, in atoms -- and retrieval still fails. Migration moved the content and the
retrieval path did not follow.

## THE FIX (proposed, NOT taken)

RE-POINT the battery's expectations at the ATOM ids that now hold each artifact, then re-run.
Do NOT relax the bar to whatever ranks today: the battery's own history says "never tuned",
and widening a definition until the instrument flatters you is the named anti-pattern (M10's
refusal is the precedent). If a re-pointed probe STILL fails, that is a real retrieval defect
in the atom plane and belongs to the R-track -- which the census just scoped
(dark planes 40-50% of demand; atoms are part of that plane).

TASK SHAPE: migration-completion, not test maintenance. Whoever re-points also checks whether
OTHER name-based references to the deleted 621 were left dangling -- one gate broke loudly
enough to find; a reference that fails OPEN (the readme_directory_pointer_fails_open class)
would not have.

## MEASURED AT THE GATE (06:30, after kimi's build)

Numbers, now that the construction has actually been run rather than reasoned about:

* 425cf52 deleted **621 tracked files**, of which **103 are top-level `docs/*.md`** --
  the population the battery's expected slugs live in. Earlier text in this file says
  "621 docs"; that is the total tracked deletion, not the doc-name population. Stated
  here rather than edited above, so the correction is visible.
* kimi's added finding, which reframes the whole task: **the `legacy_path -> art_id`
  map is a design claim that was never wired.** The migration's own design doc §167
  says it "records a legacy_path -> art_id map as a committed atom". No such field, no
  such lookup, no such artifact. The battery going red is not the defect -- it is the
  ONLY DETECTOR that ever fired on a missing artifact, five days late.
* First execution of the constructor: **2 of 103 matched.** The cause is structural,
  not incidental. The migration lifted each doc's title line and Status line into the
  atom `header` and kept the remainder as `body`, so a sha over the whole pre-deletion
  file can never equal the atom's `body_sha`:

      docs/coordination-plan-synthesis.md            23380 chars
      art_20260710_multi-agent-coordination-...      23267 chars   (delta 113)
      doc[113:].rstrip() == atom.body.rstrip()  ->   True

  Byte-exact after stripping the same header the migration stripped. The fix keeps the
  content-addressed guarantee -- strip, then match, and ASSERT the equality so a wrong
  strip fails loudly instead of writing a wrong art_id into a committed map.

**The method point.** kimi built this and explicitly refused to claim it green, because
it could not execute from its seat. That refusal is why the diagnosis took one pass
instead of arriving after a bad commit: a constructor that was never called, and a
premise that cannot hold, both surfaced on first execution. A build that says
"verification pending" is worth more than one that says "done" and is not.
