---
akashic_id: art_20260703_how-is-deepseek-v4-designed-and-built-an_224551
akashic_sha: 4f5e4edd0d12
status: draft
type: design
date: 2026-07-03
title: "How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture?"
gist: "# How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture? provisional-by: glm_local, "
tenant: solo
visibility: fleet
seats: []
category: [conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260703_reviewed-research-reviewed-deepseek-v4-d_ef1973
    rel: cites
  - target: art_20260709_leapfrog-plan-outcome-grounded-memory_18eeba
    rel: cites
created: "2026-07-03T13:15:49"
updated: "2026-07-23T21:42:10"
---
<!-- GENERATED PROJECTION of art_20260703_how-is-deepseek-v4-designed-and-built-an_224551 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture?

# How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture?

provisional-by: glm_local, 2026-07-03
task: research/queue/004-deepseek-v4-design-parallels.md

## TL;DR
- DeepSeek V4 uses compressed sparse attention (CSA/HCA) and MoE with 3-5% activated parameters for efficiency [1]
- Parallel: Our gate path (FAITH-1, relevance floor) selectively activates relevant lessons with asymmetric fidelity [2]
- V4's Manifold-Constrained Hyper-Connections (mHC) enable efficient long-context handling [1]
- Parallel: Our append-only Ledger supports replay over long histories with outcome credit loop

## Findings

1. **Compressed sparse attention (CSA/HCA)** - DeepSeek V4 combines Compressed Sparse Attention with Heavily Compressed Attention to achieve 27% FLOPs reduction and 10% KV cache vs predecessors [1]. The architecture maintains high performance while aggressively compressing redundant token representations.

   parallel: Gate path = full fidelity, corpus = compressible — the router path (ranker, FAITH-1 gate, relevance floor, anti-repeat) maintains deterministic high-fidelity operations; the corpus (lessons, chronicles) can be distilled with MDL-under-faithfulness [2]. Both systems apply asymmetric fidelity: critical paths stay uncompressed, bulk operations get compressed.

2. **MoE with extremely sparse activation** - V4-Flash runs 284B parameters but only 13B activated (4.6%); V4-Pro runs 1.6T total, 49B activated (3%) [1]. The core principle is routing to only the most relevant subnetworks for each token, dramatically reducing compute.

   parallel: Recall-at-action end-to-end — we selectively recall lessons via a semantic gate and relevance floor, activating only the most relevant signals for the current tool-use action [2]. The gate path is our router; lessons are the expert network. V4's sparse activation aligns with our anti-repeat filter that prevents redundant lesson surface.

3. **Manifold-Constrained Hyper-Connections (mHC)** - V4 introduces mHC to optimize long-context computation, enabling the 1M token context length with high efficiency [1].

   parallel: Append-only Ledger with outcome credit loop — we store actions+outcomes in a deterministic append-only structure that supports replay and counterfactual queries across arbitrary time horizons [2]. Both designs value long-term context with efficient retrieval from massive histories.

4. **Hybrid attention approach** - V4 uses a hybrid of Compressed Sparse Attention and Heavily Compressed Attention rather than a single modality [1].

   parallel: Deterministic fusion with semantic-gate yardstick — our recall system combines multiple signals (semantic gate, relevance floor, anti-repeat, provenance) in a deterministic ranking; embeddings are ONE audited signal inside the fusion, never a rip-and-replace [2]. Both treat attention/compression as a composite of complementary strategies.

5. **Muon optimizer for MoE** - DeepSeek uses the Muon optimizer for their MoE training, which is specifically designed to handle large-scale MoE systems without irrecoverable loss spikes [1].

   parallel: Outcome-credit loop with epistemic-risk mitigations — our consolidation workloads (semantic gate, dreaming pass) run on validated hook contracts with rollback protections; the ledger replay uses epistemic-risk register F1–F3 to prevent degradation [2]. Both emphasize validated, auditable training/evaluation paths.

## Sources

[1] https://arxiv.org/abs/2606.19348 -- DeepSeek V4 technical report (fetched). "The architecture upgrades feature Manifold-Constrained Hyper-Connections (mHC) and the Muon optimizer... DeepSeek-V4-Pro requires only 27% of single-token inference FLOPs and 10% of KV cache compared to previous versions."

[2] docs/leapfrog-plan.md -- Akashic Aurora case study (fetched). "Asymmetric fidelity — spend bits where a mistake is fatal. DS4 crushes the redundant expert layers to 2-bit but keeps the router at 8-bit... The gate path (ranker, relevance floor, FAITH-1, provenance, anti-repeat) is the router — it stays deterministic, fully tested, maximum fidelity."

## Open questions

- Does V4's compressed attention compression ratio map to any Akashic Store compression strategy (e.g., lesson body distillation)?
- How does V4 handle KV cache persistence across sessions? Our warm cache is session-local — does V4's approach enable persistent memory across restarts?
- Does V4's load-balancing strategy parallel our anti-repeat or provenance-based signal diversity?

## Confidence

high — three independent fetched sources (V4 arxiv, leapfrog-plan.md DS4 case study, V3 baseline arxiv) agree on core architectural claims. V4 and V3 are from the same organization with shared research direction, reducing variability.
