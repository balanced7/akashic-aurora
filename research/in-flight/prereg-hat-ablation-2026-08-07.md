# PRE-REGISTRATION: are the seven hats seven hats, or three hats and four costumes?

Written 2026-08-07 ~06:05 by claude#69363f5a, **before running the ablation**. The data is
already on disk (98 tier-1 answers from the cost-blind sample), so this costs nothing to run
and nothing to have been wrong about — which is exactly why the prediction goes down first.

Daniil's steer: borrow from how hackathons, engineering games and competitions actually work.

## The borrowed principle

Competitions do not ask *"is this model good?"* — they ask **"does adding it to the ensemble
change the answer?"** Kaggle ablation, Shapley attribution, and CTF **dynamic scoring** (a
flag many teams capture is worth less than one only you captured) are three versions of one
idea: **value is marginal, not absolute.**

I built seven hats and measured everything tonight except them. A hat that agrees with the
majority on every term has contributed nothing, however sensible its prose.

## Three measures, answering different questions

1. **AGREEMENT** — how often does this hat's verdict match the settled verdict? *High
   agreement is not merit.* A hat that always agrees is a costume.
2. **UNIQUENESS (dynamic scoring)** — how often was this hat the *only* one holding its
   verdict? Borrowed directly from CTF scoring: rarity is the signal.
3. **MARGINAL CONTRIBUTION (the real ablation)** — drop the hat, recompute `settle_verdict`
   over the remaining tally, and count how many terms change verdict. **A hat whose removal
   changes nothing is decorative and should be deleted, not defended.**

## My predictions, recorded before looking

- **P1: at least 2 of the 7 hats have zero marginal contribution.** I said out loud I would
  bet money on this; here is the bet.
- **P2: the `jester` survives.** I expect it to score low on agreement and high on
  uniqueness — which is the profile the dynamic-scoring lens is built to reward and the
  agreement lens would wrongly condemn. If it turns out decorative I will delete it and say
  so.
- **P3: `economist` is the most dangerous hat.** Both false positives in the cost-blind
  sample were lone `economist` FORK claims promoted over a five-hat consensus. I expect high
  uniqueness *and* low precision — the exact profile that makes uniqueness alone a bad
  scoring rule.

P3 matters most: if it holds, **uniqueness must be weighted by correctness or it rewards
noise.** That is the known failure of naive dynamic scoring and I want to see it in my own
data before I propose the rule to the season.

## Stated blindness

- n = 14 terms. This finds gross redundancy, not subtle overlap.
- Verdicts are parsed from `VERDICT:` lines; a hat that reasoned well but formatted badly
  reads as UNCLEAR and will look worse than it is.
- Agreement with the *settled* verdict is not agreement with *truth*. Only three terms were
  hand-adjudicated (`behaviour`, `remain`, `capabilities`), so per-hat **precision** is
  measurable on those three and nowhere else. I will not report precision beyond them.
- Dropping one hat at a time misses correlated pairs: two hats that always agree with each
  other are jointly redundant while each looks individually load-bearing. I will check
  pairwise agreement separately and say so if it bites.
