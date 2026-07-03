status: done
# TASK: How do CriticGPT and prover-verifier-style systems TRAIN a critic that improves at catching a generator's real mistakes, and what parts transfer to a local-model critic?
feeds: SQ2 (adversarial-critic-partner design)
seeds:
- https://arxiv.org/abs/2407.00215
- https://arxiv.org/abs/2407.13692
- https://arxiv.org/abs/2310.01798
notes: Context: our adversarial-critic-partner idea (a critic that trains independently and
  self-grades on catching real mistakes) + retrieval-critic-design's independence ladder
  (model independence = strongest rung). Chase: training data construction (how they get
  labeled generator-mistakes), the self-grading/eval loop, critic-vs-generator capability
  gap findings (can a WEAKER model usefully critique a stronger one?), and failure modes
  (nitpicking, hallucinated bugs). "Done" = the 5 design decisions a critic-trainer must
  make, each with what the literature says.
