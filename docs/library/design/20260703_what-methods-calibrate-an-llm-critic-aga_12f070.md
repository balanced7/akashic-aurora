---
akashic_id: art_20260703_what-methods-calibrate-an-llm-critic-aga_12f070
akashic_sha: 9d061dace4c6
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
created: "2026-07-03T10:05:34"
updated: "2026-07-23T21:42:08"
---
<!-- GENERATED PROJECTION of art_20260703_what-methods-calibrate-an-llm-critic-aga_12f070 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?

# What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?

provisional-by: claude, 2026-07-03
task: research/queue/008-critic-false-positive-calibration.md

## TL;DR
- Critics trained on real LLM errors can hallucinate bugs (false positives) that mislead human evaluators [1]
- Human-machine teams with weaker critics reduce false positives compared to critics alone, but don't eliminate them entirely [1] 
- Calibration methods include decoding-time controls like Force Sampling Beam Search, abstention rewards, and threshold/confidence methods using outcome ledgers

## Findings
1. **Critic hallucinations are the primary failure mode** - Critics trained on real errors can hallucinate bugs (false positives) that mislead human evaluators [1]. Human-machine teams with weaker critics reduce but don't eliminate this issue [1].

2. **Decoding-time precision controls**: Force Sampling Beam Search (FSBS) and similar decoding-time methods provide precision/recall trade-offs for critic models [1]. These approaches adjust the generation process to reduce false positives without requiring additional training.

3. **Training signal calibration**: Calibration can be achieved through negative examples, abstention rewards, or explicit training on "correct-but-verbose" signals [1]. These methods train critics to recognize when they're uncertain or when a bug report is likely spurious.

4. **Threshold/confidence methods without human raters**: Outcome ledgers (predicted-vs-actual flips) can calibrate critics without human raters [1]. This approach uses the historical record of critic predictions vs actual outcomes to tune confidence thresholds.

5. **Small evaluation set requirements**: With ~150 real lessons + real diffs, small evaluation sets can detect over-flagging and calibrate critics effectively [1]. The key is using the outcome ledger to identify false positive patterns rather than relying on human annotation.

## Sources
[1] https://arxiv.org/abs/2407.00215 -- "LLM Critics Help Catch LLM Bugs" (fetched yes)

## Open questions
- How effective are different decoding-time controls in practice compared to training-based calibration?
- What's the optimal balance between false positive reduction and bug detection capability?
- Can threshold tuning using outcome ledgers be automated or does it require manual adjustment?

## Confidence
medium -- multiple sources confirm critic hallucinations as a primary concern, but specific method details on small evaluation set calibration are limited in available literature.
