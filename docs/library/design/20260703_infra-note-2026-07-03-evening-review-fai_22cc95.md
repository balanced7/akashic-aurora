---
akashic_id: art_20260703_infra-note-2026-07-03-evening-review-fai_22cc95
akashic_sha: 0678985004e0
status: draft
type: design
date: 2026-07-03
title: "infra-note (2026-07-03 evening review): FAILED (thin/missing draft), partial 36-byte session"
gist: "# infra-note (2026-07-03 evening review): FAILED (thin/missing draft), partial 36-byte session # log -- started, then stalled with no draft "
tenant: solo
visibility: fleet
seats: []
category: [memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-03T23:11:38"
updated: "2026-07-03T23:11:38"
---
<!-- GENERATED PROJECTION of art_20260703_infra-note-2026-07-03-evening-review-fai_22cc95 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# infra-note (2026-07-03 evening review): FAILED (thin/missing draft), partial 36-byte session

# infra-note (2026-07-03 evening review): FAILED (thin/missing draft), partial 36-byte session
#   log -- started, then stalled with no draft written. Same family as the 6 empty-log timeouts
#   this shift (see runlog-2026-07-03.md). Requeued as-is; not a content problem.
# TASK: What UNCONVENTIONAL / clever compact models (specialists, not generalist chat minis) make a local fleet more powerful per GB -- and what is the subtask -> model CAPABILITY MAP for composing them?
feeds: SQ5 (fleet power-per-GB) + the fleet-dispatch layer (this is the router's evidence base) -- complements R013 (mainstream generalist survey) with the SPECIALIST long tail
seeds:
- https://huggingface.co/spaces/mteb/leaderboard
- https://huggingface.co/BAAI
- https://huggingface.co/collections
notes: |
  Trigger: user (2026-07-03, leaving for work) -- "unique and clever small llms that are useful...
  how we integrate them into our local stack... an intelligent easy-to-use structure for calling
  them." R013 answers the mainstream 1-15B generalist survey; THIS answers the CLEVER SPECIALIST
  tail + how to COMPOSE small models so the pool is stronger per GB, not just per model. Runs FREE
  on the fleet; disqualifier is unchanged (fabrication/citation honesty). Fetch-before-cite.
  Chase, numbered + URL-cited:
  (1) EMBEDDING + RERANK minis: the current best tiny embedders/rerankers (MTEB leaders under ~600M
      -- bge-small/base, gte-small, e5-small, EmbeddingGemma, nomic, jina; rerankers like bge-reranker,
      Qwen3-reranker). Params, dims, VRAM, Ollama/ONNX availability. These power recall/codex CHEAPLY.
  (2) STRUCTURED-OUTPUT / EXTRACTION specialists: models or approaches tuned for reliable JSON/schema
      output (constrained decoding: Outlines, llama.cpp GBNF grammars, XGrammar; models rated for
      function-calling at tiny sizes -- Hammer, xLAM/Salesforce, Nexusflow, Gorilla-OpenFunctions).
      Which combine a small model + grammar to get near-perfect schema adherence?
  (3) DRAFT models for SPECULATIVE DECODING: tiny draft models that speed up a bigger target on the
      same box (e.g. 0.5-1B drafting for a 30B target) -- does Ollama/llama.cpp expose it, real speedups.
  (4) GUARD / CLASSIFIER / ROUTER minis: safety-guards (Llama-Guard-class), zero-shot classifiers,
      and small ROUTER models (RouteLLM, and any tiny "which-model-should-handle-this" routers) --
      exactly the local/frontier routing decision our A0 loop needs.
  (5) DISTILLED / TASK-SPECIFIC oddities: clever distills or domain minis that punch above weight
      (summarizers, SQL, tool-callers, MoE-with-tiny-active). One line each on the clever trick.
  (6) COMPOSITION PATTERNS: draft-then-verify, embed->retrieve->small-generate, classifier-routes-to-
      -specialist, small-extracts + frontier-reasons. What sizes hold up per role, where they collapse.
  "Done" = a SUBTASK -> MODEL capability map (rows: summarize / classify / route / extract-JSON /
  embed / rerank / draft / guard; cols: recommended tiny model, size, VRAM, how-called, silent-failure
  risk) + 3-5 clever "power-per-GB" composition patterns worth prototyping on our box.
