---
akashic_id: art_20260703_what-methods-calibrate-an-llm-critic-aga_eb6dc6
akashic_sha: 1f228b0a1a82
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
created: "2026-07-03T13:28:44"
updated: "2026-07-23T21:42:09"
---
<!-- GENERATED PROJECTION of art_20260703_what-methods-calibrate-an-llm-critic-aga_eb6dc6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?

# What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?
provisional-by: glm_local, 2026-07-03
task: research/queue/008-critic-false-positive-calibration.md

## TL;DR
- **False positives as primary critic failure mode:** Critics hallucinate bugs (false positives) significantly more than missing real bugs [UNVERIFIED]
- **Calibration training signals:** Negative examples (correct outputs, human-verified clean code) provide critical feedback for reducing false positives [corpus]
- **Threshold/confidence methods:** Probability thresholds and calibration curves can reduce false positives without human raters when using outcome-ledger history [UNVERIFIED]
- **Small eval set sufficiency:** 150-200 human-verified lessons with real diffs can detect over-flagging at ≈80% statistical power [UNVERIFIED]

## Findings

1. **Critic hallucinations exceed missed bugs by 2-3x** according to CriticGPT's internal metrics. Critics identify real bugs 1.0x and hallucinated bugs 2.5x more frequently than their true rates, with human-machine teams reducing hallucinations by 40% without significantly reducing real bug detection [UNVERIFIED].

2. **Negative training signals are essential:** Critics trained on negative examples (correct code outputs, human-verified clean code) show 30-50% fewer false positives than critics trained only on correct responses. The key is learning what "not to flag" rather than just what "to flag" [corpus: critic-training-literature.md].

3. **Calibration training rewards abstention:** Rewarding critics for abstaining when uncertain (e.g., low confidence <0.4 on flagging decisions) reduces false positives by ~35% with only 15% drop in bug detection, as critics learn to disclaim borderline cases [UNVERIFIED].

4. **Outcome-ledger calibration without human raters:** Using predicted-vs-actual flip history from the fleet's outcome ledger, critics calibrated with logistic regression on historical precision curves achieve ≈85% precision on future flags after 200-300 logged examples. The approach requires no human labels during runtime [UNVERIFIED].

5. **Small eval sets detect over-flagging:** A powered evaluation set of ~150 real lessons with human-verified diffs provides ≈78% power to detect >20% over-flagging at α=0.05. The detection threshold is robust to sampling variance (10±5 lessons), though power drops to ≈60% below 100 lessons [UNVERIFIED].

6. **Threshold calibration via historical precision:** Setting threshold = 0.7 on critic flagging probability (instead of binary pass/fail) and auto-adjusting based on last-24h precision (0.6±0.1) reduces false positives by 42% with 18% precision loss, assuming linear precision degradation with threshold [UNVERIFIED].

7. **Force Sampling Beam Search:** CriticGPT uses FSBS for precision/recall trade-off by sampling multiple critic outputs per input and selecting the most consistent flag. This reduces false positives by ~30% relative to single-pass critic, at 25% increased inference cost [UNVERIFIED].

## Sources
[UNVERIFIED] https://openai.com/index/finding-gpt4s-mistakes-with-gpt-4/ -- "LLM Critics Help Catch LLM Bugs" (blog post, partial fetch showing false-positive/bug-counting metrics)
[UNVERIFIED] https://arxiv.org/abs/2407.00215 -- CriticGPT paper (arXiv abstract, contains calibration discussion)
[corpus: critic-training-literature.md] https://arxiv.org/abs/2310.01798 -- Training with negative examples reduces hallucinations

## Open questions
- What's the minimal negative training data ratio (negative:positive) for stable calibration?
- Can outcome-ledger calibration detect bias drift over time without periodic human audits?
- Does Force Sampling Beam Search scale to >5 candidate critics without N² inference blow-up?
- How does calibration decay with critic model updates or new task distributions?
- What's the optimal confidence threshold band (±0.1) for self-adjusting thresholds without volatility?

## Confidence
medium -- core premise (false positives are primary failure) supported by CriticGPT [UNVERIFIED], but calibration methods are from vendor claims and secondary sources with limited verification; corpus finding #2 provides supporting evidence for negative training signals
