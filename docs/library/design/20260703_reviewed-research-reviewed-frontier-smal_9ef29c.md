---
akashic_id: art_20260703_reviewed-research-reviewed-frontier-smal_9ef29c
akashic_sha: 4b5a2ca58bba
status: draft
type: design
date: 2026-07-03
title: "reviewed: research/reviewed/frontier-small-models-2026-07.md (2026-07-03, deep-research on Opus)"
gist: "# reviewed: research/reviewed/frontier-small-models-2026-07.md (2026-07-03, deep-research on Opus) # TASK: What are the current standout SMA"
tenant: solo
visibility: fleet
seats: []
category: [bus, tooling, performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_standout-small-models-for-the-local-flee_3c1c47
    rel: cites
created: "2026-07-03T12:16:13"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260703_reviewed-research-reviewed-frontier-smal_9ef29c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# reviewed: research/reviewed/frontier-small-models-2026-07.md (2026-07-03, deep-research on Opus)

# reviewed: research/reviewed/frontier-small-models-2026-07.md (2026-07-03, deep-research on Opus)
# TASK: What are the current standout SMALL models (~1B-15B, fit 16GB VRAM with 32K+ ctx, ideally Ollama-packaged) for bounded fleet SUBTASKS -- summarization, classification/routing, schema extraction, query generation, short tool-call chains?
feeds: SQ5 (fleet throughput / subtask specialization) + bakeoff round 2 candidate list
seeds:
- https://huggingface.co/zai-org
- https://gorilla.cs.berkeley.edu/leaderboard.html
- https://huggingface.co/spaces/allenai/reward-bench
notes: |
  RECOVERED 2026-07-03 from the plan-limit-killed session (2b1b8946): the deep-research
  agent was launched with this exact brief, then every sub-agent died on Fable credit
  exhaustion -- ZERO usable output was produced. Prompt preserved verbatim below so the
  free fleet (or a budget-refreshed frontier session) can run it at zero marginal cost.
  Contract: fetch-before-cite, one URL per finding, mark UNVERIFIED what you can't fetch.
  Context: glm-4.7-flash (30B-A3B MoE) just WON our bakeoff on citation-honesty grounds;
  two fast models were eliminated for citation laundering + fluent fabrication -- so
  fabrication/citation-honesty is the disqualifier for any candidate here too.

  Deliver:
  1. THE GLM FAMILY (mid-2026): variants smaller than 30B? glm-4.7 siblings? GLM-5 small
     releases? -- sizes, context, Ollama availability. Org: huggingface.co/zai-org.
  2. STANDOUT MINIS: models people actually rate for the subtasks above -- check Qwen3.5
     small variants, Phi-5/Phi-4-mini successors, SmolLM3+, Liquid LFM, Ministral/Mistral
     small, IBM Granite 4, Gemma small (gemma had documented tool-loop failures in Claude
     Code -- flag if fixed), and anything newer. Per model: params, VRAM @ Q4, context,
     license, Ollama tag.
  3. BENCHMARKS THAT MATTER FOR SUBTASKS: tool-calling (BFCL v4+), instruction-following
     (IFEval), structured-output reliability, hallucination/faithfulness for small models
     -- which minis lead? Prefer standardized leaderboards over vendor claims.
  4. FIELD REPORTS on small models as SUBTASK workers in agent pipelines (draft-then-verify,
     router models, extraction specialists) -- what sizes hold up, where they collapse.
  5. TOP-5 candidate list for bakeoff round 2, each with one sentence on why and one on its
     suspected silent-failure risk (fabrication/citation honesty is the disqualifier).
  "Done" = dense numbered findings + URLs, ending in the ranked top-5 for bakeoff round 2.
