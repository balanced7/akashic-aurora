status: queued
# TASK: What evidence exists on the minimal model strength at which a critic still adds value against a stronger generator?
feeds: SQ2+SQ5 (can a 7B local critic usefully check a frontier generator?)
seeds:
- https://arxiv.org/abs/2407.13692
- https://arxiv.org/abs/2404.13076
notes: Context: our critic will be a LOCAL 7-30B model checking frontier-generated work
  (independence over strength -- retrieval-critic-design's ladder). CriticGPT found
  weaker-critic+human teams reduce hallucinated bugs; prover-verifier games train small
  verifiers robust to sneaky provers. Chase: (1) weak-to-strong generalization results
  (the 2404.13076 lineage and successors) -- where does verification stay easier than
  generation; (2) any published critic-vs-generator capability-gap ablations (does a 7B
  critic catch anything a frontier self-check misses BECAUSE of independence?); (3)
  task types where small verifiers demonstrably hold up (structured checks, contract
  violations, citation verification) vs collapse (deep reasoning). Use websearch for
  2025-26 work. "Done" = a capability-gap map: what to delegate to a 7B critic now,
  what needs the fine-tuned version, what stays frontier.
