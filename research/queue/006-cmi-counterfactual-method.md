status: queued
# TASK: How does the CMI paper (arXiv 2605.17641) run per-memory counterfactual swaps, and what exactly must our Wave B bench copy or beat?
feeds: SQ1 (Ledger Replay Bench design -- causal memory utility)
seeds:
- https://arxiv.org/abs/2605.17641
notes: Split from task 001 after its first attempt timed out (scope was two papers).
  ONE paper only; fetch the abstract page and at most one methodology section; max 2
  fetches. Chase: the counterfactual swap procedure (what is held fixed, what is
  swapped), their metric definitions, error-trace handling (the credit confound from
  field-survey C2: flips may be caused by error traces, not lessons -- does CMI control
  for this?), and compute cost per swap. "Done" = a checklist of what Wave B must
  replicate to claim causal attribution, plus where we can be cheaper via REAL episodes.
