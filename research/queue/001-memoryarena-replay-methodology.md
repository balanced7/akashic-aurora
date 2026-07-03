status: failed
# TASK: What exactly does MemoryArena (arXiv 2602.16313) replay, with which metrics, and where are the gaps our Ledger Replay Bench can differentiate on?
seeds:
- https://arxiv.org/abs/2602.16313

notes: We already know (field survey 2026-07) that MemoryArena published replay methodology
  Feb 2026, so our bench is "validated but not novel" -- the differentiation candidates are
  REAL episodes (not synthetic) and token-cost-normalized value rate. Chase: their episode
  source, their credit/attribution method, whether they do per-memory counterfactual swaps
  (2605.17641-style CMI), and what they explicitly list as limitations/future work. "Done" =
  a findings list a bench designer can act on without reading the paper.
escalation (2026-07-03 review): 2x timeout -- arxiv paper reading exceeds local prefill
  budget. ESCALATED TO FRONTIER: fold into the Wave B design session together with the
  CMI methodology (already frontier-fetched, see reviewed/cmi-counterfactual-method.md).
  Not requeued to the fleet.
