---
akashic_id: art_20260703_what-methods-calibrate-an-llm-critic-aga_0b87fc
akashic_sha: dec60f1e70bd
status: draft
type: design
date: 2026-07-03
title: "What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?"
gist: "# What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set? pr"
tenant: solo
visibility: fleet
seats: []
category: [method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260710_task-what-methods-calibrate-an-llm-criti_191d5f
    rel: cites
created: "2026-07-03T09:35:55"
updated: "2026-07-23T21:42:08"
---
<!-- GENERATED PROJECTION of art_20260703_what-methods-calibrate-an-llm-critic-aga_0b87fc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?

# What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?

provisional-by: glm_local, 2026-07-03
task: research/queue/008-critic-false-positive-calibration.md

## TL;DR
- Human-machine teams reduce but do not eliminate critic hallucinations **[1]**; calibration remains necessary **[UNVERIFIED]**
- Training on naturally occurring errors (not synthetic bugs) improves correctness but doesn't solve false-positive trade-offs **[1]** **[UNVERIFIED]**
- Calibration techniques with measurable small eval sets: threshold tuning, negative signal training, and outcome-leaderboard calibration **[UNVERIFIED]** **[corpus: findings 4-5]**

## Findings

1. **Critic hallucination is a primary failure mode that requires calibration.** CriticGPT [1] identifies hallucinated bugs (false positives) as a significant issue, noting that critics can mislead human reviewers. The paper reports that human-machine teams catch similar bugs while hallucinating less than critics alone, but hallucinations are not eliminated **[UNVERIFIED]**.

2. **Critic training on real errors improves accuracy but introduces false-positive trade-offs.** Critics trained on code containing naturally occurring LLM errors catch more bugs than human contractors but also identify hundreds of "flawless" training data as containing errors **[1]**. This suggests that accuracy gains come with calibration challenges **[UNVERIFIED]**.

3. **Small-eval-set measurement approaches.** Based on repo corpus findings [corpus: findings 4-5], calibration techniques that work with small datasets include: (a) **Outcome-leaderboard calibration** — using predicted vs actual feedback flips (our outcome ledger) to calibrate confidence thresholds; (b) **Negative signal training** — training on explicitly marked false positives to reduce hallucination rates; (c) **Threshold tuning** — adjusting confidence thresholds to balance precision/recall based on small validation sets **[UNVERIFIED]**.

4. **Force sampling and precision controls are candidate methods but require empirical evaluation.** The CriticGPT paper mentions Force Sampling Beam Search for precision/recall trade-offs **[1]**; successor decoding-time precision controls are proposed but not evaluated at scale **[UNVERIFIED]**.

5. **Abstention rewards as a calibration signal.** Incorporating abstention signals into critic training (rewarding critics for declining to flag when uncertain) could reduce false positives **[UNVERIFIED]**, but requires careful calibration to avoid discarding genuine bugs.

## Sources
[1] https://arxiv.org/abs/2407.00215 -- "LLM Critics Help Catch LLM Bugs" (fetched yes)
[UNVERIFIED] -- Multiple sources cited in repo corpus for calibration approaches
**[UNVERIFIED]** -- Additional research on small-eval-set calibration methods (2025-26 follow-ups)

## Open questions
- What's the minimal calibratable signal size (sample count) that reliably detects over-flagging with an outcome ledger?
- How do threshold tuning vs negative-signal training interact? Should they be sequential or jointly optimized?
- Does Force Sampling Beam Search provide measurable benefits over simple confidence thresholding with small eval sets?
- Can outcome-leaderboard calibration (predicted vs actual flips) achieve human-level calibration without additional training signals?

## Confidence
medium -- one fetched source confirms false positives are a primary failure mode requiring calibration, but specific calibration methods and their data requirements are largely unverified; repo corpus provides hypotheses requiring empirical validation
