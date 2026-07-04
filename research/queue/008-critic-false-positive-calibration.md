status: queued
requeue-feedback (2026-07-03 evening review): REJECTED, not promoted. The draft's Findings
  attach suspiciously precise numbers (e.g. "2-3x", "30-50% fewer false positives", "abstention
  reduces FPs by ~35% with only 15% drop", "42% reduction, 18% precision loss") to sources it
  marks **UNVERIFIED** with NO verbatim quote from either seed URL -- the contract's own
  fetch-before-cite + verbatim-proof-of-fetch rules were not met, and precise-sounding stats
  attached to unfetched sources is the fluent-fabrication pattern our own bakeoff disqualified
  models for (see model-bakeoff-2026-07.md). RE-RUN with: (1) actually fetch both seeds via
  WebFetch, or `curl -sL <url>` if WebFetch fails on the arxiv/openai pages; (2) if a fetch still
  fails, use websearch.py to find an ALTERNATIVE accessible page rather than inventing figures;
  (3) any number you cannot trace to a fetched quote must be dropped, not stated with false
  precision. Prior draft preserved at research/drafts/critic-false-positive-calibration.md for reference.
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
