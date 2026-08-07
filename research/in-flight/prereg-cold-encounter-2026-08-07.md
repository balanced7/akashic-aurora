# PRE-REGISTRATION: does "help that explains WHY" actually teach?

Written 2026-08-07 ~09:50 by claude#69363f5a, **before running the probe**.

Daniil: *"I am still curious about the helpers with verbs idea and how you can use their
feedback to improve our core."* This is that loop, made measurable.

## The claim under test — someone else's finding, and I want to know if it replicates

The fan-out playbook, P4, from claude#42d00626's cold-encounter run:

> "0/3 predicted that `--peer` + `--fan` is refused... And the surprise: the flags written
> *that same day*, whose help text explains **why**, scored **3/3**. **Help that explains why
> teaches; help that lists what does not.**"

That is n=1 door and it was written by the person who then measured it — the most flattering
possible setup. I wrote tonight's help text (`sift`, `discord`) deliberately following that
finding, which means I am in exactly the same position, and a self-graded replication is
worth very little.

So this run compares **two groups on the same probe**:

- **GROUP WHY** — doors whose help explains the reason a flag exists (`sift`, `discord`,
  written tonight after reading P4).
- **GROUP LIST** — doors whose help states what a flag *is* without saying why (older verbs,
  chosen before any answer is seen).

## Method

1. **Ground truth first, by me, by running the thing.** Not from the docstring — from
   execution. A probe graded against my belief about my own code measures nothing; that is
   the trap that made T222 possible six hours ago.
2. Fresh helpers receive **ONLY the `--help` output** for one verb. No source, no docs, no
   repo context.
3. They predict what specific invocations do.
4. **Every misprediction is an ergonomic defect, located precisely** — that is the whole
   value; the score is secondary to the located line.

## Predictions, recorded before looking

- **P1: GROUP WHY outscores GROUP LIST by ≥25 points.** If the effect is real it should be
  large; a small gap here is indistinguishable from which verbs I happened to pick.
- **P2: the biggest misses will be REFUSALS and PRECEDENCE** — what a flag *forbids*, and
  which flag wins when two combine. His run missed exactly these (0/3 on `--peer`+`--fan`
  refusal, 2/3 guessing `--bg`+`--get` precedence backwards), and neither is expressible by
  describing a flag in isolation.
- **P3: at least one of MY doors has a real defect I cannot see.** I wrote them, I am the
  worst possible judge of their legibility, and the whole reason to hand them to a stranger
  is that familiarity is not reversible.

## Stated blindness

- Small n. This locates defects; it does not estimate an effect size to a decimal.
- I chose both groups, and I wrote one of them. A significant gap is **suggestive, not
  clean** — the honest confound is that I may simply write clearer help now than whoever
  wrote the older verbs, independent of the why/list distinction.
- Grading is mine, and a prediction can be *reasonable but wrong*. Those get their own bucket
  rather than being scored as failures, because a helper reasoning correctly from bad help is
  evidence about the HELP, not about the helper.
