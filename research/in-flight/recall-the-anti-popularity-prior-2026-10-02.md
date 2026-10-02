# The usefulness re-rank is an anti-popularity prior, and the floor was fit to n=1

**Measured 2026-10-02 by claude (Vandor), against the 10-moment recall bench (W0.3).**
Status: VERIFIED ARITHMETICALLY, pre-registered below.

**LANDED SINCE THIS NOTE WAS WRITTEN** -- the status line above originally said NOT YET FIXED and
that is stale, corrected here rather than rewritten away:

- **Finding 3 (the anti-popularity prior) is FIXED.** RED pinned alone at `3ba9779e` (8 red,
  3 green, per M3), GREEN at `9232e161`: `usefulness_factor` no longer puts `surfaced` in the
  denominator, returns exactly 1.0 when nothing has been judged, and estimates a signed balance
  over real judgments shrunk by a confidence term. recall@1 17% -> 33% **at the unchanged floor
  of 0.20**. 12 pins, 5 mutations run (one survived, was pinned, re-run and caught), 35
  pre-existing recall pins still green.
- **Finding 1 (the floor) is deliberately NOT shipped.** The floor stays at its live 0.20 and
  its recalibration is a separate act, gated on batch 2 per the pre-registration below. Fixing
  the re-rank first was what kept the floor from masking it.
- **Finding 2 (chrome share) is still open.** W0.4's instrument still reports only the ratio.

## What was being done

Navi's batch 1 (N1-N6) merged into `tests/fixtures/recall_eval/moments.json` at `f693d74c`,
taking the answer key from 4 moments to 10 (6 scored, 3 abstains, 1 excluded). First baseline
on the larger set: recall@1 17%, recall@5 33%, abstention 0/3, chrome share 4%.

Abstention 0/3 is the worst number in the set, so I swept the show-nothing floor rather than
reasoning about it, per the house lesson `attack_your_own_scoring_rule_before_the_players_do`.

## Finding 1 -- raising the floor strictly dominates, which I predicted wrongly

| floor | recall@1 | recall@5 | abstention |
|---|---|---|---|
| 0.20 (live default) | 17% | 33% | 0/3 |
| 0.78 (the knee) | **33%** | 33% | **3/3** |

I expected a tradeoff: any floor tight enough to buy silence would cost hits. There is no
tradeoff on this set. Every number improves or holds. The knee is 0.78, not 0.80: the third
abstain flips between 0.76 and 0.78.

## Finding 2 -- the chrome metric is mine and it is misleading

Chrome share rose 4% to 35% as the floor rose, which reads as a regression and is the
opposite. Absolute characters:

| floor | chrome chars | body chars | total pushed |
|---|---|---|---|
| 0.20 | 1466 | 31573 | 33039 |
| 0.78 | 1466 | 2673 | 4139 |

Chrome is **constant at 1466 characters at every floor**. The floor does not govern it at all.
The share rose only because the body collapsed by 92%. Total reading burden falls 87%.
Chrome share conflates "more chrome" with "less body" and would report 100% for a surface
that pushed nothing but verb blurbs. W0.4's instrument needs to report absolute characters
beside the ratio. Caught by using the instrument, which is the only way this surfaces.

## Finding 3 -- THE ROOT CAUSE: two independent defects, and the floor hides one of them

The gate and the sort use different quantities. The lesson ranker gates on the raw relevance
component (`core/recall/at_action.py:1446`) and then sorts on the blended score times
`usefulness_factor` (`core/recall/at_action.py:1468`). So a low-relevance lesson can outrank a
high-relevance one.

Holding the floor at 0.20 and pinning `usefulness_factor` to a constant 1.0:

| configuration | recall@1 | recall@5 | abstention |
|---|---|---|---|
| floor 0.20, live usefulness | 17% | 33% | 0/3 |
| floor 0.20, usefulness pinned 1.0 | **33%** | 33% | 0/3 |
| floor 0.78, live usefulness | 33% | 33% | 3/3 |
| floor 0.78, usefulness pinned 1.0 | 33% | 33% | 3/3 |

**The rank-1 loss is caused by the usefulness re-rank, not by the floor.** N3's correct lesson
sits at rank 4 under the live re-rank and at rank 1 with the re-rank neutralised, at the same
floor. The floor and the re-rank fix DIFFERENT defects: the floor buys abstention and nothing
else does; the re-rank fix buys rank-1, and the floor only appears to buy it by starving the
re-rank of material.

Had I only swept the floor, I would have shipped 0.78, watched every number improve, and
**permanently hidden** the fact that the re-rank demotes correct answers. At floor 0.78 the two
configurations are indistinguishable.

## Why the re-rank demotes correct answers -- the arithmetic

The multiplier is computed as effective credits over a smoothed denominator:

    eff    = useful - noise + min(helped, surfaced)
    denom  = max(surfaced, useful + noise + helped) + 2.0
    rate   = clamp((eff + 1.0) / denom, 0, 1)
    factor = 0.5 + rate                      # documented range [0.5, 1.5]

For an UNJUDGED lesson (useful, noise and helped all zero) this reduces exactly to

    factor = 0.5 + 1/(surfaced + 2)

a strictly decreasing function of how often the lesson has been surfaced, with no other input.
Verified against the live counters, and every predicted value matched:

| lesson | surfaced | useful | factor |
|---|---|---|---|
| N3's RIGHT ANSWER | 72 | 2 | **0.527** |
| the lesson that outranked it | 1 | 0 | **0.833** |
| rank 2 usurper | 3 | 0 | 0.700 |
| rank 3 usurper | 6 | 0 | 0.625 |
| N6's right answer | 13 | 0 | 0.567 |
| N4's right answer | 3 | 0 | 0.700 |
| N1's right answer (the set's only HIT@1) | 28 | 4 | 0.667 |

The lesson that took rank 1 from the right answer has **never been credited useful**. It simply
has barely ever been surfaced. Every right answer in the set scores BELOW its usurpers, because
every right answer is a frequently-surfaced lesson.

**The documented upper half of the range is dead.** Clearing 1.0 requires useful credits on
more than half of all surfacings (verified: 60% at surfaced=10, 51% at surfaced=100). The
house's measured judgment rate is 2.2% (532 of 24,378), of which 93% are useful, so the
achievable credit rate is about 2%. The boost half needs 25 times that. In practice the
multiplier operates in [0.5, 1.0] and is a pure penalty that can never reward.

## The law this is an instance of

A decay rule that depends on a feedback signal must fail SAFE (neutral) when that signal is
absent. This one fails toward punishment: it cannot distinguish
**surfaced-often-yet-never-useful** from **surfaced-often-and-never-judged**, and treats an
unjudged lesson as a judged-bad one. Since reach-map barrier 1 (feedback starvation) means
nearly nothing is ever judged, the rule collapses into "surfaced often, therefore suppress".

The loop closes viciously: recall itself increments the surfaced counter (the live hook path
passes `count_surface=True`), so **recall's own act of showing a lesson is what demotes it**. A
lesson genuinely relevant to a recurring situation is surfaced often BECAUSE it is relevant,
earns no credits BECAUSE the reader never judges, and is therefore pushed below lessons
irrelevant enough never to have been shown. Relevance is self-defeating. No external input is
required; the loop is closed.

This is the virtue-isolation lens exactly: the noise decay was designed to work beside a live
judgment channel, and severed from that sibling it became an anti-relevance filter. Its
acceptance test is therefore the lens's own test -- **does the rule behave correctly if
judgments are restored?** A fix must be neutral when unjudged and decay only on positive
evidence of noise.

## What the floor's own record already said, and the IOU it left

I nearly filed "the floor was set by feel". It was not, and the correction matters. The floor
WAS calibrated, on 2026-07-08, recorded in
`docs/library/design/20260701_recall-vnext-closing-the-four-loops-2026_b93539.md`. Its own
calibration record says:

- **"Credited pairs scorable: 1 of 26 historical helps"** -- n=1 positive.
- Zero negatives. The other input was a 24h injection population, which is volume and not
  labels, and you cannot measure abstention from credited pairs: a credited pair is by
  construction a moment where firing was RIGHT.
- 0.20 was chosen to keep that one pair at 3.2x margin while cutting 91% of volume.
- and verbatim: **"n=1 honesty: recalibrate once the wrap-review / engaged channels grow the
  credited set (the loops this slice ships produce exactly that data)."**

So this is not a defect anyone introduced. A threshold fit to one positive and no negatives is
necessarily set too low, because every false positive is invisible to a keep-95-percent-of-helps
objective. Its author flagged the n=1 and asked for recalibration when real data existed. The
bench is the first data that qualifies, 86 days later. The IOU is now collectable.

## PRE-REGISTERED, before Navi's batch 2 exists

Tuning a threshold on 6 positives and 3 negatives is overfitting, and fitting it to the current
10 would burn batches 2-6 as a held-out set. So both predictions are recorded now, in advance,
and batches 2-6 are the out-of-sample test:

- **P-A:** a floor at 0.78 will beat 0.20 on abstention on unseen moments, and will not lose
  recall@5.
- **P-B:** neutralising the usefulness penalty for UNJUDGED lessons will raise recall@1 on
  unseen moments, independently of the floor.
- **P-C (the discriminating one):** any fix that only improves topical matching, such as better
  embeddings or wider lexical coverage, will move recall@5 and will NOT move abstention,
  because abstention requires a notion of SUFFICIENCY that topical similarity does not carry.

If P-A or P-B fails on batch 2, the 10-moment result was overfitting and that is the finding.
Neither is shipped as a default until batch 2 rules.

## Not in the reach map

The map lists nine ranked barriers. The sibling swap, a confident top-ranked hit at the WRONG
moment, is not barrier 3, which describes lexical matching causing MISSES; this is the inverse.
The anti-popularity prior is not among the nine at all. Barrier 1 named the reader's silence; it
did not say that the few judgments which exist make matters worse by crediting whatever happened
to fire. The instrument found what its own designer's analysis had missed, one day after the
analysis was written, which is the whole argument for having built it.

---

# HELD-OUT RESULT, 2026-10-02 ~02:00: P-A IS FALSIFIED

Navi delivered batch 2 (N7-N12) AFTER P-A/P-B/P-C were committed, so these six are a genuine
out-of-sample test. Merged verbatim; all seven ground-truth keys verified against the live corpus
first. The set is now 16 of 40: 10 scored, 5 abstains, 1 excluded.

## P-A: FAILED. The 10-moment floor result was overfitting.

| all 16, floor | recall@1 | recall@5 | abstention |
|---|---|---|---|
| 0.20 (live) | 20% | **30%** | 0/5 |
| 0.78 | 20% | **20%** | 5/5 |

P-A predicted a 0.78 floor would buy abstention with no recall@5 loss. It buys perfect abstention
and costs a third of recall@5. On batch 2 alone the floor at 0.78 takes recall@5 to **0%** -- it
destroys every hit in the held-out set. The tradeoff I expected, then dismissed on 10 moments
because the data did not show it, is real. Nine labels were not enough to see it and I should not
have been as confident as the strictly-dominates table made me feel. This is exactly what the
pre-registration was for, and the right outcome is that the floor stays at 0.20.

## P-B: HELD in direction, but the fix is beaten by doing nothing

Three arms, all at the live floor 0.20, the old formula reconstructed verbatim:

| arm | batch 1 (fitted) r@1 | batch 2 (held out) r@1 | all 16 r@1 | all 16 r@5 |
|---|---|---|---|---|
| OLD formula (pre-fix) | 25% | 0% | **10%** | 30% |
| SHIPPED fix (`9232e161`) | 50% | 0% | **20%** | 30% |
| pure neutral, always 1.0 | 50% | **25%** | **30%** | 30% |

P-B holds: the shipped fix beats the old formula at rank 1 on all 16 (20% vs 10%), and the old
exposure penalty is the worst arm everywhere. Removing `surfaced` from the denominator was right.

**But pure neutrality beats the shipped fix, 30% against 20%.** The part of the fix that still
uses real judgments -- the signed balance shrunk by a confidence term -- is net HARMFUL at rank 1.
Using the judgment signal is worse than ignoring it entirely.

That is consistent with the rate: 2.2% of surfacings are ever judged (532 of 24,378), and the
493 useful / 39 noise votes that exist were credited to whatever happened to FIRE, not to what
should have. So the signal is not merely sparse, it is sampled from the engine's own mistakes.
A multiplier estimated from it inherits that bias.

**The honest setting for the usefulness multiplier at a 2.2% judgment rate is 1.0 -- no re-rank
at all -- until the judgment channel is fixed.** That is a bigger claim than the one I shipped
and it is NOT shipped here: it is pre-registered as P-D below and gated on batch 3.

## N7/N8: the identical-trigger pair proves the TRIGGER is the ceiling, not the ranker

Navi built N7 and N8 as a deliberate sibling pair. Their triggers are **byte-identical** --
both `{"path": "core/comm/discord_guest_reply.py"}` -- with disjoint right answers (the ABSENCE
defect vs the INVERSION defect, same file, same hour).

Because `recall_at` keys on (path, command), it returns the **identical ranked list** for both,
which it did. So the pair is unsatisfiable by construction: **recall@1 over {N7, N8} cannot
exceed 50% for ANY path-keyed ranker, at any floor, under any re-rank.** No ranking fix reaches
it. Measured, both MISS, and neither right answer appears in the top 5 at all, so the real result
is worse than the structural ceiling.

This converts reach-map barrier 4 ("the query is the command, not the intent") from an
observation into a proof with a number on it. Two genuinely different moments in one file with
different right answers cannot be distinguished by location. The fix is not a better ranker over
the same key; the trigger must carry the moment's INTENT. That is the first thing measured here
that no amount of W0-style work can touch.

## P-D, pre-registered now, gated on batch 3

- **P-D:** setting `usefulness_factor` to a constant 1.0 will beat the shipped judgment-estimated
  version at recall@1 on unseen moments, until the judgment rate rises materially above 2.2%.
- **P-A is withdrawn as falsified.** The floor stays 0.20. A floor change requires a rule whose
  shape is not a global constant, per P-C, which remains untested.
