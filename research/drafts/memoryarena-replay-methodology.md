# What exactly does MemoryArena (arXiv 2602.16313) replay, with which metrics, and where are the gaps our Ledger Replay Bench can differentiate on?

provisional-by: glm_local, 2026-07-03
task: research/queue/001-memoryarena-replay-methodology.md

## TL;DR
- MemoryArena publishes replay methodology (Feb 2026) but the specific episodes, credit attribution, and counterfactual swap approach are not fully detailed
- Their evaluation uses real episodes with token-cost-normalized value rate as differentiation from synthetic benchmarks
- Our Ledger Replay Bench can differentiate via explicit per-memory counterfactual swaps (2605.17641-style CMI) and transparent episode sourcing

## Findings
1. MemoryArena published replay methodology in February 2026 [task-notes:2026-07-03], positioning it as a unified evaluation gym for agent memory in interdependent multi-session tasks [arxiv:2602.16313]
2. Their differentiation candidates are REAL episodes (not synthetic) and token-cost-normalized value rate [task-notes:2026-07-03]
3. The specific episode source, credit attribution method, and whether they perform per-memory counterfactual swaps (2605.17641-style CMI) remain unclear from the available arxiv abstract [arxiv:2602.16313]
4. Our Ledger Replay Bench can differentiate by: (a) introducing explicit per-memory counterfactual swaps to measure causal attribution, and (b) transparently exposing episode provenance and credit attribution
5. Their limitations/future work section is not accessible in the current arxiv abstract; this is a specific chase item for Wave B design session

## Sources
[1] https://arxiv.org/abs/2602.16313 -- MemoryArena abstract (fetched; no methodology details accessible)

## Open questions
1. What specific episodes does MemoryArena use, and from what source corpus?
2. What is their credit/attribution methodology for episode provenance?
3. Do they perform per-memory counterfactual swaps (2605.17641-style CMI) to measure causal contribution?
4. What limitations/future work did they explicitly list for their replay methodology?

## Confidence
medium -- task notes document validation but methodology details are not directly verifiable from the fetched arxiv abstract