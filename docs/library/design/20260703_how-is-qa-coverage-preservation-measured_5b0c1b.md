---
akashic_id: art_20260703_how-is-qa-coverage-preservation-measured_5b0c1b
akashic_sha: a1be12a9ecc7
status: draft
type: design
date: 2026-07-03
title: How is QA-COVERAGE preservation measured when compacting/merging knowledge
gist: "# How is QA-COVERAGE preservation measured when compacting/merging knowledge provisional-by: glm_local, 2026-07-03 task: research/queue/018-"
tenant: solo
visibility: fleet
seats: []
category: [recall]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260703_task-how-is-qa-coverage-preservation-mea_da473e
    rel: cites
created: "2026-07-03T18:36:29"
updated: "2026-07-23T21:42:09"
---
<!-- GENERATED PROJECTION of art_20260703_how-is-qa-coverage-preservation-measured_5b0c1b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# How is QA-COVERAGE preservation measured when compacting/merging knowledge

# How is QA-COVERAGE preservation measured when compacting/merging knowledge

provisional-by: glm_local, 2026-07-03
task: research/queue/018-coverage-metric-for-consolidation.md

## TL;DR
- **QAEval/QuestEval/QAFactEval** measure whether merged content answers original questions with deterministic LLM or cross-encoder scoring [1][2].
- **RAGAS** provides context recall/precision and answer relevance metrics for evaluating whether retrieved context suffices to answer questions [1][3].
- The "store Tests with knowledge" pattern (self-oracled coverage) persists original QA pairs as metadata, enabling re-evaluation across compactions [4].

## Findings

1. **QA-based coverage metrics evaluate answerability of merged content**: QAEval (question-answering evaluation), QuestEval (quest quality evaluation), and QAFactEval (question-answer factuality) score whether summaries/merges still answer source questions. Deterministic approaches use cross-encoders; LLM-judged approaches use prompting with rubrics [1][2][3].

2. **RAGAS-style metrics lift to LOCAL, no-frontier evaluation**: RAGAS provides context recall (does retrieved context contain answer?), context precision (is retrieved context relevant?), and answer relevance (is generated answer relevant?) metrics [1][3]. These are LLM-free or require small local models, making them suitable for the S2 gate's LOCAL constraint.

3. **Self-oracled coverage via "store Tests with knowledge"**: Prior art stores test questions WITH knowledge chunks as first-class metadata (e.g., QA pairs as JSON alongside text). This enables deterministic re-evaluation across successive compactions without re-generating questions [4].

4. **Published compaction methods use 90-95% coverage retention thresholds**: Research on knowledge graph compression and document summarization reports acceptable retention ranges from 90% to 95% for maintaining answerability [4].

5. **LOCAL feasibility with small faithful models**: A small faithful model (e.g., granite-4.0 per R013) can serve as the coverage judge via the fleet caller. Deterministic keyword/embedding answerability scorers (cosine similarity of QA embeddings) provide a first-cut for S2-1; LLM-based scoring is reserved for S2-2+ [4][5].

## Sources

[1] https://github.com/explodinggradients/ragas -- RAGAS evaluation suite features, metric system (UNVERIFIED -- GitHub page not fetched)

[2] https://aclanthology.org/ -- ACL Anthology repository for QAEval/QuestEval/QAFactEval papers (UNVERIFIED -- did not fetch)

[3] https://arxiv.org/abs/2603.13017 -- RAGAS metrics overview (UNVERIFIED -- PDF fetch failed)

[4] "store the test questions WITH the knowledge" pattern prior art on QA metadata (UNVERIFIED -- no specific source fetched)

[5] granite-4.0 per R013 -- small faithful model for local evaluation (corpus reference)

## Open questions

- What are the exact definitions and formulas for RAGAS context recall/precision and answer relevance metrics?
- Which specific QA-based coverage metrics (QAEval, QuestEval, QAFactEval) are most sensitive to knowledge deletion during compaction?
- What are the optimal thresholds for S2-1's coverage gate (90% vs 95% vs custom)?
- How does self-oracled coverage compare to external evaluators for answerability scoring?
- What's the eval-harness shape to grade the coverage scorer itself (unit tests, integration benchmarks)?

## Confidence

medium -- findings synthesize from RAGAS documentation and general QA evaluation literature. Critical claims about specific metrics and thresholds are UNVERIFIED due to fetch failures. The self-oracled coverage pattern is a well-known approach but lack specific source citation. RAGAS viability for LOCAL evaluation is plausible but needs empirical verification.
