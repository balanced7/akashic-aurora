status: queued
# TASK: How is QA-COVERAGE preservation measured when compacting/merging knowledge -- the metric for S2's second gate (does a merged lesson still answer what the originals answered)?
feeds: SQ3 + S2-1 (the coverage scorer -- docs/s2-consolidation-design.md); faithfulness-only gates reward over-deletion, so coverage must be scored separately
seeds:
- https://arxiv.org/abs/2603.13017
- https://github.com/explodinggradients/ragas
- https://aclanthology.org/
notes: |
  Trigger: docs/s2-consolidation-design.md slice S2-1 -- the two-sided gate needs a COVERAGE scorer:
  does the merged lesson answer the UNION of the originals' Tests? Field lesson (ADR_0702233250):
  faithfulness-only gates reward over-deletion; coverage is the brake that makes the gate two-sided.
  Fetch-before-cite. Chase:
  (1) QA-BASED coverage metrics: QAEval, QuestEval, QAFactEval, answerability-of-generated-questions --
      how they score whether a summary/merge still answers the source's questions; deterministic vs LLM-judged.
  (2) RAGAS-style answer/context coverage + recall metrics -- what is liftable to a LOCAL, no-frontier scorer.
  (3) The "store the test questions WITH the knowledge" pattern (self-oracled coverage) -- prior art on
      persisting QA pairs as first-class metadata for re-evaluation across successive compactions.
  (4) THRESHOLDS: what coverage-retention fraction do published compaction methods treat as acceptable?
  (5) LOCAL feasibility: can a small faithful model (granite-4.0 per R013) serve as the coverage judge via
      our fleet caller, or is a deterministic keyword/embedding answerability scorer enough for a first cut?
  "Done" = a recommended coverage metric for S2-1 (deterministic-first vs local-judge), its inputs (merged
  text + the originals' Tests), a starting threshold, and the eval-harness shape to grade the scorer itself.
