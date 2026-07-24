---
akashic_id: art_20260701_knowledge-compaction-memory-consolidatio_f49716
akashic_sha: b35236fbb532
status: draft
type: report
date: 2026-07-01
title: Knowledge compaction + memory consolidation — full frontier research record (2026-07-02)
gist: "# Knowledge compaction + memory consolidation — full frontier research record (2026-07-02) provenance: two frontier research agents, claims "
tenant: solo
visibility: fleet
seats: []
category: [memory, agent-lifecycle, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-02T23:42:32"
updated: "2026-07-02T23:42:32"
---
<!-- GENERATED PROJECTION of art_20260701_knowledge-compaction-memory-consolidatio_f49716 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Knowledge compaction + memory consolidation — full frontier research record (2026-07-02)

# Knowledge compaction + memory consolidation — full frontier research record (2026-07-02)

provenance: two frontier research agents, claims fetched+verified same day; synthesized
by claude; summary note: `research: knowledge compaction + consolidation field state
2026-07`; feeds SQ1+SQ3 and the sharpening-loop plan (codex Wave 2 revival).

## A. Compression / compaction techniques

1. LLMLingua-2 is still the production prompt compressor (no v3; team pivoted to
   KV-cache work): 2-5x compression minimal-loss, ~14x on long CoT, frozen since 04-2024.
   https://llmlingua.com/llmlingua2.html ; https://github.com/microsoft/LLMLingua
2. Gist tokens research-only; failure modes "lost by the boundary / lost if surprise /
   lost along the way" — exact-detail recall degrades even when aggregates hold.
   https://aclanthology.org/2025.acl-long.241/
3. RAPTOR measured retention directly: 4% summary-node hallucination, does NOT propagate
   to parents, no discernible QA impact; +20% QuALITY. https://arxiv.org/abs/2401.18059
4. GraphRAG does NOT measure retention (LLM-judge comprehensiveness only); community
   summaries "deviate from fine-grained details". https://arxiv.org/abs/2404.16130 ;
   https://arxiv.org/pdf/2502.11371
5. HippoRAG 2: index abstractly, STORE LITERALLY (graph as index over full passages);
   +7% associative memory with factual recall preserved. https://arxiv.org/html/2502.14802v1
6. "Compression Represents Intelligence Linearly": benchmark scores ~linear with corpus
   compression ability across 31 LLMs. https://arxiv.org/abs/2404.09937
7. MDL for knowledge bases exists only in graph-mining (KG-MDL 2309.12908, survey
   2007.14009). **No published work uses MDL as the organizing principle for an LLM
   agent's textual lesson store — the codex plan is ahead of published practice.**
8. Corpus rewriting (phi/Textbooks, WRAP, Nemotron-CC, BeyondWeb) targets TRAINING data,
   not reference KBs; nearest docs application is llms.txt (convention, zero measurement).
   https://llmstxt.org/
9. Closest match to our need: "Structured Distillation for Personalized Agent Memory"
   (2026) — schema-constrained extraction, **11x token reduction with retrieval held**
   (NDCG/MRR ~unchanged). https://arxiv.org/pdf/2603.13017
10. Compaction evaluation: QA-preservation is the credible gate (QuestEval/QAEval
    lineage; QEVA adds coverage/factuality/chronology). PITFALL: faithfulness-only
    metrics reward over-deletion — score COVERAGE separately.
    https://arxiv.org/pdf/2103.12693 ; https://arxiv.org/pdf/2404.03278
11. **Photocopy drift**: "Useful Memories Become Faulty When Continuously Updated by
    LLMs" (2026) — repeated consolidation cycles drift memories generic; utility can fall
    BELOW no-memory baseline; keep detailed + abstracted representations separately,
    never erase evidence. https://arxiv.org/pdf/2605.12978
12. Mem0's production validation style: end-task benchmark (LoCoMo), not summary quality
    — +26% over OpenAI memory, >90% token savings vs full-context. https://arxiv.org/abs/2504.19413

## B. Consolidation practice (who maintains memory, and does anyone measure it)

13. Letta/MemGPT: sleep-time paper never evaluated curation; server-side sleeptime
    DEPRECATED ~04-2026 → client-side "dream" subagents over git-backed MemFS in
    isolated worktrees (convergent with our repo+fleet shape). Zero quantitative
    consolidation eval remains true; eval request closed "not planned"; their 06-2026
    post concedes "generic and lossy after repeated refinements" in prose.
    https://arxiv.org/abs/2504.13171 ; https://www.letta.com/blog/our-next-phase/ ;
    https://docs.letta.com/letta-agent/memory ; https://github.com/letta-ai/letta/issues/3115 ;
    https://www.letta.com/blog/towards-agents-that-learn/
14. Mem0 RETREATED from write-time supersession (04-2026): ADD-only extraction +
    retrieval-time temporal reasoning; admits "staleness in high-relevance memories is
    a harder, open problem". Decay shipped 05-2026 as search-time re-ranking only
    (1.5x boost / 0.3x dampen), no deletion, no ablation.
    https://github.com/mem0ai/mem0 ; https://mem0.ai/blog/state-of-ai-agent-memory-2026 ;
    https://mem0.ai/blog/introducing-memory-decay-in-mem0
15. Zep/Graphiti: bi-temporal invalidate-never-delete; LLM contradiction detection;
    community summaries need periodic full refresh (incremental drifts). Their rebuttal
    of Mem0's LoCoMo self-eval is a caution on all vendor memory benchmarks.
    https://arxiv.org/html/2501.13956v1 ; https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/
16. Curation quality became measurable only in 2026: MemoryAgentBench conflict-resolution
    competency; deterministic max(serial) supersession beats LLM freshness +10.8pts
    (2606.01435); **FAMA** (Forgetting-Aware Memory Accuracy) — first metric penalizing
    reliance on invalidated memories; finds "frequent reuse of invalid memories"
    everywhere. https://github.com/HUST-AI-HYZ/MemoryAgentBench ;
    https://arxiv.org/abs/2606.01435 ; https://arxiv.org/abs/2604.20006
17. A-MEM: in-place neighbor rewriting, no versioning (critiqued as unsafe); evolution
    worth ~+5.7 F1 by ablation; reproducibility issues open; field moved to MemoryOS /
    MIRIX / Mem-α / MemEvolve. The longitudinal reorganize-vs-append experiment still
    does not exist. https://arxiv.org/html/2502.12110v11 ; https://arxiv.org/html/2606.24775
18. Replace-vs-accumulate: Generative Agents accumulate; ExpeL head-to-head shows
    insights+episodes COMBINED always wins (39% vs 36/31 HotpotQA); ReasoningBank
    distilled-beats-raw but defers pruning. https://arxiv.org/html/2308.10144 ;
    https://arxiv.org/html/2509.25140v1
19. **Bloat measurably hurts**: add-all 2,411 records → 13.04% accuracy vs selective
    1,012 → 38.86%; utility-based deletion 38.89→42.65% with 23% smaller store
    ("experience-following" error propagation). https://ar5iv.labs.arxiv.org/html/2505.16067
20. Decay now has ablations: FadeMem 45% less storage AND higher F1 than Mem0
    (2601.18642); Oblivion tuned-decay beats both extremes (2604.00131); FSFM +29.2%
    signal-to-noise from pruning (2604.20300).
21. **Memory Worth** = p(success | memory retrieved), per-memory counters, ρ=0.89 vs
    ground-truth utility — the closest published thing to knowledge darwinism; our
    funnel already collects exactly this signal. https://arxiv.org/abs/2604.12007
22. SuperMemo/Wozniak knowledge darwinism: verified at source; **nobody has applied it
    to agent memory by name** — parts exist (Vestige FSRS MCP server; Memory Worth).
    https://supermemo.guru/wiki/Knowledge_darwinism ; https://github.com/samvallad33/vestige
23. Mem-α: RL-learned insert/update/delete against downstream-task reward with a
    compression penalty — ~50% footprint cut, generalizes 30K→400K+; the strongest
    "improvement pressure in the training signal" claim. https://arxiv.org/abs/2509.25911
24. RecMem: keep every raw interaction as "persistent safety net," consolidate lazily on
    recurrence (-87% construction tokens). https://arxiv.org/abs/2605.16045

## Verdict + house mapping

No shipping product has memory-that-gets-better-not-bigger. The converged credible
recipe = **append-only evidence + utility-scored, outcome-labeled projection/eviction**
= our Ledger + funnel + supersession, already built. Codex regenerate-from-atoms is
structurally immune to photocopy drift (re-distill always consumes originals). Unclaimed
lanes we can take: MDL-organized lesson store; knowledge darwinism with real outcome
labels; the sword metric = value per 1,000 injected tokens. Plan: sharpening loop
S1 (value-rate triage) → S2 (fleet consolidation pass, two-sided QA/faithfulness gate)
→ S3 (replay bench as compaction oracle).
