# RESULT: the hat ablation, and why uniqueness scoring rewards being loudly wrong

Run 2026-08-07 ~06:10 against predictions committed at `1f31575`. Free — 98 tier-1 answers
already on disk from the cost-blind sample. Borrowed frame: competitions score **marginal**
value, not absolute (Kaggle ablation, Shapley attribution, CTF dynamic scoring).

## Scorecard against the pre-registered predictions

| | prediction | outcome |
|---|---|---|
| **P1** | ≥2 hats with zero marginal contribution | **CONFIRMED** — 3 dead (`economist`, `jester`, `outsider`) |
| **P2** | the `jester` survives | **REFUTED** — marginal contribution 0 |
| **P3** | `economist` is the most dangerous hat | **CONFIRMED** — precision 1/3, uniqueness 2 |

## The table

| hat | agreement | uniqueness | **MARGINAL** | precision¹ |
|---|---|---|---|---|
| `linguist` | 11/14 | 1 | **1** | **3/3** |
| `historian` | 9/14 | 3 | **1** | 1/3 |
| `adversary` | 12/14 | 0 | **1** | 2/3 |
| `junction` | 13/14 | 0 | **1** | 2/3 |
| `jester` | 12/14 | 0 | 0 | **3/3** |
| `outsider` | 9/14 | 2 | 0 | **3/3** |
| `economist` | 11/14 | 2 | 0 | 1/3 |

¹ on the three hand-adjudicated terms — the only ones with ground truth. I will not report
precision beyond them.

## The finding, which is not the one I went looking for

**Marginal contribution and precision point in OPPOSITE directions.**

- `historian` has marginal contribution **1** and precision **1/3**. It changes outcomes, and
  it changes them *wrongly*.
- `jester` has marginal contribution **0** and precision **3/3**. It is always right and
  never pivotal.

So the ablation measure I built — *"a hat whose removal changes nothing is decorative"* —
**is wrong as stated**, and P2's refutation is what exposed it. Zero marginal contribution
does not mean worthless: it can mean *correct but redundant*. A hat that is right when others
are right is insurance against the case where they are not, and n=14 cannot see that case.

Deleting `jester` on the ablation number alone would have removed a 3/3 hat to keep a 1/3 one.

## Why this matters far beyond the hats

**P3 generalises into a scoring law, and Season 1 was about to need it.**

Naive dynamic scoring — reward the rare find, CTF-style — has a dominant degenerate
strategy: **claim things nobody else claims.** `economist` is that strategy embodied. It has
the second-highest uniqueness in the pool and the worst precision, because it reached FORK on
all three adjudicated terms including both false positives. Uniqueness rewarded it. Truth did
not.

> **A uniqueness bonus must be gated on the claim being CONFIRMED, never on rarity alone.**
> Otherwise the optimal player is the one who confidently asserts what no one else will.

This is a direct, evidence-backed constraint on the Season 1 scoring policy, and it arrives
before twenty players get the chance to discover the exploit themselves. It also complements
kimi's convergence objection from the *incentive* side rather than only the measurement
side: the canary oracle detects a tired pool; correctness-gated uniqueness *pays* for
decorrelation without paying for noise.

## What I'm changing in `sift`

- **Drop `economist`.** Worst precision, zero marginal contribution, and its whole
  characteristic output was the lone-hat FORK the consensus floor now has to suppress. It was
  generating the exact defect another mechanism exists to clean up.
- **Merge `adversary` and `junction`.** They agree **93%** of the time — the correlated pair I
  pre-registered as a blind spot of one-at-a-time ablation, and the only pair to show up.
- **Keep `jester`.** 3/3 precision. Its value is redundancy, and the honest note is that this
  sample cannot demonstrate that value — only that removing it costs nothing *here*.

7 hats → 5, ~30% cheaper per term, removing the worst-precision hat and one of a redundant
twin.

## Stated blindness

- **All measured marginal contribution comes from ONE term** (`arguments`). n=14 with a
  majority rule means a hat only shows marginality when it flips a near-tie. These numbers
  are thin and I am not treating them as stable.
- Precision rests on **three** adjudicated terms. That is a truth set of three.
- **The truth set should have existed before the instrument.** I built seven hats and then
  discovered I could only grade them on three examples. Next ensemble: hand-adjudicate the
  calibration set *first*, then build.
