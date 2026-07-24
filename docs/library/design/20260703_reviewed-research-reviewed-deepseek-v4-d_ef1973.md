---
akashic_id: art_20260703_reviewed-research-reviewed-deepseek-v4-d_ef1973
akashic_sha: ddac4b4fb9e9
status: draft
type: design
date: 2026-07-03
title: "reviewed: research/reviewed/deepseek-v4-design-parallels.md (2026-07-03) -- accepted, confidence"
gist: "# reviewed: research/reviewed/deepseek-v4-design-parallels.md (2026-07-03) -- accepted, confidence # claim corrected (see the review note in"
tenant: solo
visibility: fleet
seats: []
category: [memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260703_how-is-deepseek-v4-designed-and-built-an_1f2621
    rel: cites
  - target: art_20260709_leapfrog-plan-outcome-grounded-memory_18eeba
    rel: cites
created: "2026-07-03T23:10:50"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260703_reviewed-research-reviewed-deepseek-v4-d_ef1973 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# reviewed: research/reviewed/deepseek-v4-design-parallels.md (2026-07-03) -- accepted, confidence

# reviewed: research/reviewed/deepseek-v4-design-parallels.md (2026-07-03) -- accepted, confidence
#   claim corrected (see the review note in the reviewed file: an unfetched source was cited)
# TASK: How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture?
feeds: SQ3+SQ5 (architecture adoption candidates from DeepSeek V4)
seeds:
- https://arxiv.org/abs/2606.19348
- https://github.com/deepseek-ai
- https://arxiv.org/abs/2412.19437
notes: User request (2026-07-02): heard V4 mirrors some of our approach. IMPORTANT repo
  context to read FIRST: docs/leapfrog-plan.md already contains a DS4 case study and we
  adopted "asymmetric fidelity" (gate path = full fidelity, corpus = compressible) from it
  -- do not re-derive that; go DEEPER and find what the case study missed. Chase: (1) the
  V4 technical report (find it via the deepseek-ai org or api-docs; the V3 report
  2412.19437 is the design lineage baseline), (2) architecture choices -- sparse attention,
  memory/context handling, MoE topology, anything append-only or ledger-like in their
  training/data pipeline, (3) their verification/gating practice (how they gate what enters
  training vs what we do with gated ships + FAITH), (4) cheap-vs-expensive model tiering in
  their own tooling. For EACH finding add a "parallel:" line mapping it to an Akashic
  concept (Store/Ledger, recall-at-action, gated ship, funnel credit) or "no parallel".
  "Done" = a parallels table a designer can mine for adoption candidates, fetched sources.
requeue-feedback (2026-07-03 review): second class of timeout -- the full V4 report HTML
  is too heavy for local prefill. NARROWED: use websearch.py to find a SECONDARY analysis
  (blog/summary) of the V4 architecture instead of the primary paper; max 2 fetches, no
  arxiv HTML. Architecture parallels only; training-pipeline gating dropped (frontier
  covers it when needed).
