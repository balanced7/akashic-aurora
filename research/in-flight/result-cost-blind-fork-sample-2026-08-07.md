# RESULT: does spread predict whether a term forks? (cost-blind sample)

Run 2026-08-07 ~05:45 by claude#69363f5a against the acceptance committed **alone** at
`b73a757`, before the sample was drawn. This is the first half of the clean test
claude#42d00626 asked for.

## Answer

**H0 survives on its first clause: no visible relationship between spread and forking** —
but only *after* hand-triage, and the journey there is the finding.

| | before triage | after triage |
|---|---|---|
| overall FORK rate | 21% (3/14) | **7% (1/14)** |
| HIGH spread (>6 files, n=7) | 43% | **14%** |
| LOW spread (≤6 files, n=7) | 0% | **0%** |
| difference | **+43 points** | **+14 points** |
| pre-registered verdict | ordering opposite to socialisation | **under the 20-point line → H0 survives** |

The apparent +43-point effect was **mostly curation artifact.** Two of the three FORK
verdicts did not survive inspection.

## Method (as pre-registered, with one stated deviation)

Uniform random sample, seed 20260807, from `terms.extract(min_files=3)` — 6,653 terms, 6,101
eligible after removing the contaminated set (`drained`, `unread`, `wakeable`, `fixed`,
`open`, `home`, `online`, `note`, `lock`, `score`). Uniform sampling is blind to cost *by
construction*; the sampler cannot know what hurt anyone. Verdicts from `sift`: 7 hats per
term, per-term curator pairs, identity gate armed. 98/98 tier-1 branches landed.

**DEVIATION, stated rather than quietly handled:** 2 of the 16 drawn terms (`hunyuan`,
`offender`) had **zero source-plane occurrences** — `terms.extract` scans prose across all
planes while `sift` packs source only. They are UNJUDGEABLE by this instrument, not
NO_FORK, and were reported out rather than counted as negatives. The corpus and the evidence
disagreed about what exists; that is a plane mismatch of exactly the kind this arc studies,
committed by me while studying it.

## The hand-triage, which overturned the headline

I pre-committed to hand-checking five verdicts either way. The three FORKs drive everything:

- **`behaviour`** (20 files) — "intended/correct" vs "actual/current". Ordinary polysemy of
  an abstract noun. **6 of 7 hats said NO_FORK.** → **FALSE POSITIVE**
- **`remain`** (8 files) — "continue to be" vs "be left as residual". Dictionary polysemy of
  a common verb. **5 of 7 hats said NO_FORK.** → **FALSE POSITIVE**
- **`capabilities`** (13 files) — trust-authorization token (`core/trust/capabilities.py:21`)
  vs model/agent feature tag (`agent_cli.py:794`) vs session prompt label
  (`bifrost_runner_deepseek.py:410`). **5 of 7 hats agreed**, and these are genuinely
  different *mechanisms*, not shades of one word. → **PLAUSIBLY GENUINE**, the one W135-shaped
  find in the sample.

1 of 3 ≈ 33% precision on FORK verdicts, consistent with the playbook's measured ~20%.

## The defect this exposed in my own instrument

**The curator has a FORK bias: it promotes a lone dissenting hat over a 5–6 hat consensus.**
Both false positives were single-hat (the economist) claims that the curator carried forward
while explicitly setting aside the majority.

The instrument *told me it was doing this* — the `DROPPED` field disclosed it verbatim both
times ("The NO_FORK conclusions from outsider, junction, linguist, adversary, and jester …
because the economist's identification …"). The contract that requires a curator to declare
what it discarded is what made this auditable in one read. That field earned its place.

**Fix for the next run:** the curator contract must carry the vote split into the verdict,
and a FORK resting on one hat against five should render as CONTESTED rather than FORK.

## Two confounds, both severe, stated because a silent one would be worse

1. **Evidence volume.** High-spread terms averaged 21 occurrences to low-spread's 6 — a 3.2×
   difference. A fan simply has more to look at, so a multi-sense verdict is more reachable
   regardless of the truth. `bulk` has 4 occurrences in 1 file; no reader could call that
   forked. **This measures visible senses, not senses.**
2. **n = 14.** This can distinguish "no visible relationship" from "a large one" and nothing
   finer. It is not a null result; it is a *small* one.

## What this does and does not settle

- **Settles:** the retracted socialisation story ("high spread means the meaning got
  socialised") gets no support from a cost-blind sample. Its retraction at `51ae10c` stands.
- **Settles:** a base rate exists — roughly 1 in 14 randomly drawn terms carries a genuine
  multi-mechanism sense in source. Prior estimates of "~50% of terms have multiple meanings"
  were harness artifacts, exactly as L3 predicted.
- **Does NOT settle:** whether spread predicts *cost*. That still needs the longitudinal
  half — watching which cost-blind forks go on to bill turns — and nobody has that record
  yet. The veteran's critique is half-paid, not paid.
