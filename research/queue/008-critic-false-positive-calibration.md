status: queued
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
