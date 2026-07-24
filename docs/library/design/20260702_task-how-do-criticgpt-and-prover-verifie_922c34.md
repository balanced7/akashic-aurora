---
akashic_id: art_20260702_task-how-do-criticgpt-and-prover-verifie_922c34
akashic_sha: f4a18fcaa812
status: draft
type: design
date: 2026-07-02
title: "TASK: How do CriticGPT and prover-verifier-style systems TRAIN a critic that improves at catching a generator's real mistakes, and what parts transfer to a loca"
gist: "# TASK: How do CriticGPT and prover-verifier-style systems TRAIN a critic that improves at catching a generator's real mistakes, and what pa"
tenant: solo
visibility: fleet
seats: []
category: [memory, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-02T23:37:23"
updated: "2026-07-02T23:37:23"
---
<!-- GENERATED PROJECTION of art_20260702_task-how-do-criticgpt-and-prover-verifie_922c34 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# TASK: How do CriticGPT and prover-verifier-style systems TRAIN a critic that improves at catching a generator's real mistakes, and what parts transfer to a loca

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
