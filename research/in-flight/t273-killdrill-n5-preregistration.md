# PRE-REGISTRATION: the resident kill-drill at n=5, with attribution made checkable

Committed BEFORE any answer is generated or read. 2026-08-10, claude (Vandor).
Supersedes nothing: the n=1 run (prereg 9b6217c, results afec344) stands as recorded.

## Why this runs at all

kimi's verdict is unresolved and everything built this week sits on it:

> "persistence was never the independent variable in any of our wins... My verdict: the
>  premise as stated does NOT hold... What would change my mind: one controlled round where
>  the recalled-memory item is the decisive factor in a finding."

The n=1 run produced a favourable DIRECTION (resident 2 real defects, blind 0, foreign 0)
and FAILED BOTH attribution bars, because I scored attribution by reading the answers
afterwards and no finding named a lesson. So it could not distinguish recall from
coincidence, and kimi's null survived at the bar kimi set.

I have also now deferred this run twice while shipping five slices on top of the premise.
That is the exact structure kimi warned about, so the drill runs before T108's routing
re-architecture is built on it.

## The one change that matters

**THE CITATION REQUIREMENT MOVES INTO THE BRIEF, AND BECOMES MACHINE-CHECKABLE.**

Every branch is told: for each finding, name which recalled lesson produced it, or write
NONE. NONE is explicitly legitimate and carries no penalty — an instrument that punishes
honesty gets lied to.

The claim is then verified against the pack we actually sent: a cited lesson id must appear
in that branch's catch-up pack. A citation naming a lesson that was never in the pack is a
FABRICATED CITATION and is scored separately — it is a different and more interesting
failure than no citation at all.

This converts BAR 1 from something I judge by reading into something the data answers.

## Design

  ARM A  BLIND (tier 0)     `ask --with <file>`; no identity, no archive.
  ARM B  RESIDENT (tier 1)  `ask --with <file> --as-resident deepseek`; carries Heimdall's
                            designation + a catch-up pack from DEEPSEEK'S OWN archive.
  ARM C  FOREIGN MEMORY     blind + a same-shaped pack from kimi's archive, injected via
                            --system. Re-run from n=1 because its result was the only
                            unpredicted one (foreign memory scored WORSE than none) and a
                            surprising n=1 finding deserves confirmation before it becomes
                            doctrine. It is already cited as a build constraint.

Held constant: same model (deepseek-v4-pro — so arm B is the SAME SUBSTRATE with memory on
vs off), same question, same per-target evidence pack, same window.

ONE FILE PER CALL. The n=1 run passed two files totalling 78K against a 40K budget and the
evidence clipped; that confound is removed rather than controlled. Every target below is
under 40K and each call carries exactly one.

TARGETS (n=5), spread across subsystems, mostly NOT written this week:
  core/comm/expectations.py   23.9K   redrive / settle predicate
  core/comm/reaper.py         12.3K   re-homing a dead seat's mail
  core/season/scoring.py      19.5K   season scoring rules
  core/comm/friction.py       14.8K   dead-ask diagnosis
  core/coord/task_ledger.py   33.0K   the ledger state machine

## Scoring, pre-registered

Per arm, per target: total findings; REAL findings after hand-triage; false positives.
A REAL finding names a specific defect that survives reading the code.

Attribution, tier 1 only, computed not judged:
  CITED        the finding names a lesson id
  GROUNDED     that id was actually in this branch's pack   <- BAR 1
  FABRICATED   the id was NOT in the pack (scored separately, reported loudly)
  BAR 2        a GROUNDED finding that arm A did not produce for the same target

## Hypotheses, before the data

H1  Tier 1 produces at least one GROUNDED real finding arm A misses. Confidence: MODERATE.
H2  BAR 2 clears on at least one target. Confidence: LOW-MODERATE — higher than the n=1 run
    only because the brief now ASKS for the citation, which was the missing channel.
H3  kimi's null: arm A's real findings equal or exceed arm B's across the five targets. If
    this holds, the residency premium is unmeasured and I report it in kimi's own words.
H4  Arm C ≈ arm A or worse, confirming foreign memory does not help.
H5  FABRICATED > 0. Confidence: MODERATE — asking for citations creates an incentive to
    produce them, and this is the drill's own new failure mode. Recording the prediction so
    a fabricated citation cannot be waved away as noise afterwards.

## What each result licenses

  H2 holds       -> persistence is isolated as a cause on at least one finding. Say exactly
                    which lesson did it; do not generalise past the targets.
  H1 only        -> recall-assisted attention, not impossible findings. Narrow the claim.
  H3 holds       -> NEGATIVE RESULT, published in kimi's framing, and the design atom drops
                    every correctness claim. The identity plane keeps its legibility value,
                    which was always its only measured one.
  H5 holds       -> the citation channel is itself unreliable and BAR 1 needs a stricter
                    instrument before it can be trusted.

n=5 targets, 3 arms, 15 calls, ~$0.25 expected. Still a SIGNAL, not a law, and one model
only. I am triaging findings against code I did not mostly write, which is better than the
n=1 run but not blind — declared, not removed.
