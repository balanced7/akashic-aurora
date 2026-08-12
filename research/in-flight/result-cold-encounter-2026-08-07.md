# RESULT: my headline prediction died, and the reason is the finding

Run 2026-08-07 against predictions committed at `67d9439`, before the probe. Ground truth by
execution, never from docstrings.

## Scorecard

| | prediction | outcome |
|---|---|---|
| **P1** | GROUP WHY beats GROUP LIST by ≥25 pts | **REFUTED, and backwards** — WHY **50%** (3/6), LIST **75%** (3/4) |
| **P2** | biggest misses are refusals & precedence | **CONFIRMED** — all 3 misses were unguessable behaviour |
| **P3** | ≥1 of my doors has a defect I can't see | **CONFIRMED** — three of them |

**The doors I wrote, deliberately following "explain why", scored WORSE than a verb whose
help is 183 characters.**

## Why P1 died, which is worth more than P1 holding

Read what GROUP LIST actually said:

> *"Advisory; ... not OS-enforced mandatory locks."*
> *"auto-releases when the TTL elapses. GUESS: typical lock semantics with a TTL imply
> expiration."*

**It answered from universal convention, not from the help.** `lock` scored 3/4 while
teaching nothing, because a lock with a TTL behaves the way every lock with a TTL behaves.

My verbs do **unconventional** things — round-robin capping, exit-0-when-unconfigured,
explicit-send-bypasses-the-filter — and no convention predicts any of them.

**So the two groups were never comparable, and I chose both.** That is precisely the confound
I pre-registered ("a significant gap is suggestive, not clean") and it turned out to dominate
the result rather than merely qualify it.

**The corrected claim, which the data does support:** help text matters *in proportion to how
far the verb sits from convention*. For a conventional verb it is nearly free — the reader
already knows. For a novel verb it is the only channel, and that is exactly where I failed.

## The three defects, all one shape

Every miss was the same error, and it is a subtle one because it *feels* like good
documentation:

> **I explained the RATIONALE and omitted the BEHAVIOUR.**

| flag | what my help said | what it never said |
|---|---|---|
| `--max-occurrences` | "a cap is always REPORTED in the blind list, never silent" | that the cap **samples round-robin across files** |
| `discord status` | (nothing about exit codes) | that unconfigured **exits 0** |
| `discord send` | (described the allowlist generally) | that an explicit send **bypasses** it |

The first is the clearest: I documented *why the blind note exists* — a real and hard-won
property — while omitting the mechanism a caller actually needs. A reader cannot infer
"round-robin" from "honestly reported".

**"Explain why" is not wrong; it is incomplete.** The sharpened rule:

> **State the behaviour that convention would NOT predict, then say why it is that way.**
> Rationale without behaviour reads as thorough and teaches nothing.

## The compounding half: fixed, then re-measured with the same instrument

Three help texts amended. Same three questions, same protocol, fresh helpers:

| case | before | after |
|---|---|---|
| `sift_cap` | "mostly the first few files" | **"Many different files, because the cap samples round-robin"** ✓ |
| `disc_status` | "1" | **"0"** ✓ |
| `disc_force` | "Filtered out." | **"Sent anyway... explicit send bypasses the kind allowlist"** ✓ |

**3/3 recovered**, each citing the added sentence as its reason. GROUP WHY moves 50% → 100%
on re-measure.

That closes the loop Daniil asked for: helpers' feedback located the defect, the fix was
cheap, and **the same instrument verified it** — which is the part that makes it compounding
rather than a one-off audit.

## Stated blindness

- Small n, and the group confound above is severe enough that the 50/75 split should not be
  quoted as an effect size for anything.
- The re-measure asked the **same questions** whose answers I had just written into the help.
  That proves the text now *says* the thing; it does not prove the help is good in general,
  and a fresh question on the same flag could still miss.
- Grading is mine. `lock_exit` and `lock_ttl` were marked GUESS by the helper and scored
  correct — a right answer from a stated guess is weaker evidence than the score implies.
