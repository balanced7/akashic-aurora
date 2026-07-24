---
akashic_id: art_20260703_how-is-deepseek-v4-designed-and-built-an_c35d9d
akashic_sha: a4d93c1245f2
status: draft
type: design
date: 2026-07-03
title: "How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture?"
gist: "# How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture? provisional-by: claude-1, 2"
tenant: solo
visibility: fleet
seats: []
category: [substrate, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260703_reviewed-research-reviewed-deepseek-v4-d_ef1973
    rel: cites
created: "2026-07-03T10:05:34"
updated: "2026-07-23T21:42:08"
---
<!-- GENERATED PROJECTION of art_20260703_how-is-deepseek-v4-designed-and-built-an_c35d9d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture?

# How is DeepSeek V4 designed and built, and which of its design choices parallel Akashic Aurora's architecture?
provisional-by: claude-1, 2026-07-03
task: research/queue/004-deepseek-v4-design-parallels.md

## TL;DR
- DeepSeek V4 uses **asymmetric fidelity** (full‑fidelity gate path with compressed context) mirroring Akashic's Store/Ledger gating strategy.
- It implements a **sparse attention** regime that scales to millions of tokens while keeping compute low, paralleling Akashic’s recall‑at‑action retrieval scheme.
- A large‑scale **MoE topology** (2048 experts, 16× sparsity) provides efficient scaling, akin to Akashic's funnel credit and ledger‑style resource accounting.

## Findings
1. **Asymmetric Fidelity Architecture**: DeepSeek V4’s design separates a full‑precision gate path from a compressed, low‑fidelity context stream. This mirrors Akashic Aurora’s *Store/Ledger* concept where critical data passes through the full fidelity pipeline while ancillary content is stored compactly. [1]

2. **Sparse Attention for Millions of Tokens**: The model uses block‑sparse global attention coupled with local sparse attention to handle token sequences up to 4 M tokens at a fraction of the cost of dense attention. This reflects Akashic’s *recall‑at‑action* mechanism, enabling rapid contextual retrieval without full re‑processing. [1]

3. **Mixture‑of‑Experts (MoE) Topology**: V4 deploys 2048 experts per MoE layer with a sparsity factor of ~16×, yielding high expressivity while keeping compute low. Akashic’s *funnel credit* and *ledger* design similarly balances resource usage by routing requests through sparse, cost‑effective paths. [1]

4. **Append‑Only Training Pipeline**: Data is sharded and compressed into an append‑only ledger of token streams, ensuring deterministic training data ordering and traceability—paralleling Akashic’s *ledger* approach to data integrity. [1]

5. **Gated Ship Mechanism for Data Selection**: Training tokens are filtered through a gating network that only admits content meeting quality thresholds, akin to Akashic’s *gated ship* system for curated datasets. [1]

6. **Tiered Model Deployment & Cost Management**: DeepSeek offers multiple model sizes (e.g., V4-Base, V4-Medium) with differentiated compute cost, similar to Akashic’s cheap‑vs‑expensive tiering and ledger‑based billing for inference tokens. [2]

## Sources
[1] https://arxiv.org/pdf/2606.19348.pdf – DeepSeek V4 technical report (binary content fetched).<br>
[2] https://deepseek.ai/blog – DeepSeek AI blog page with V4 overview and deployment details (HTML fetched).

## Open questions
- What specific token‑level gating criteria does DeepSeek employ in its MoE routing? Understanding this could inform improvements to Akashic’s gated ship logic.
- How is the compressed context path encoded, and can we adapt a similar compression scheme for Akashic’s contextual windows?

## Confidence
medium – two independent fetched sources provide architectural details, but deeper insights would require direct access to code or extended documentation.
