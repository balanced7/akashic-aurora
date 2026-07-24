---
akashic_id: art_20260703_task-what-methods-calibrate-an-llm-criti_254508
akashic_sha: 1b2b50b932c3
status: draft
type: design
date: 2026-07-03
title: "TASK: What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?"
gist: "# TASK: What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation s"
tenant: solo
visibility: fleet
seats: []
category: [library, memory, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-03T08:08:47"
updated: "2026-07-03T08:08:47"
---
<!-- GENERATED PROJECTION of art_20260703_task-what-methods-calibrate-an-llm-criti_254508 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# TASK: What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?

# TASK: What methods calibrate an LLM critic against hallucinated bugs / false positives, and which are measurable with a small evaluation set?
feeds: SQ2 (adversarial-critic design -- the failure mode CriticGPT names as primary)
seeds:
- https://arxiv.org/abs/2407.00215
- https://openai.com/index/finding-gpt4s-mistakes-with-gpt-4/
notes: Context: reviewed/critic-training-literature.md finding 4 -- critic hallucination
  (false positives) is the PRIMARY failure mode; CriticGPT mitigates via human teams and
  mentions Force Sampling Beam Search for precision/recall trade-off. Chase: (1) FSBS or
  successor decoding-time precision controls; (2) calibration training signals (negative
  examples? abstention rewards?); (3) threshold/confidence methods that work WITHOUT
  human raters (we have an outcome ledger instead -- can predicted-vs-actual flips
  calibrate a critic?); (4) how small an eval set still detects over-flagging (we can
  seed ~150 real lessons + real diffs). Use websearch for 2025-26 follow-ups citing
  CriticGPT. "Done" = a ranked list of calibration methods with their data requirements.
