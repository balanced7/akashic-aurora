---
akashic_id: art_20260702_how-do-criticgpt-and-prover-verifier-sty_c34291
akashic_sha: b42df3af560b
status: draft
type: report
date: 2026-07-02
title: "How do CriticGPT and prover-verifier-style systems TRAIN a critic that improves at catching a generator's real mistakes, and what parts transfer to a local-mode"
gist: "# How do CriticGPT and prover-verifier-style systems TRAIN a critic that improves at catching a generator's real mistakes, and what parts tr"
tenant: solo
visibility: fleet
seats: []
category: [testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260702_task-how-do-criticgpt-and-prover-verifie_922c34
    rel: cites
  - target: art_20260709_an-automatic-critic-for-context-retrieva_3f4622
    rel: cites
created: "2026-07-02T23:38:28"
updated: "2026-07-23T21:42:13"
---
<!-- GENERATED PROJECTION of art_20260702_how-do-criticgpt-and-prover-verifier-sty_c34291 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# How do CriticGPT and prover-verifier-style systems TRAIN a critic that improves at catching a generator's real mistakes, and what parts transfer to a local-mode

# How do CriticGPT and prover-verifier-style systems TRAIN a critic that improves at catching a generator's real mistakes, and what parts transfer to a local-model critic?

provisional-by: glm_local, 2026-07-02
task: research/queue/002-critic-training-literature.md

## TL;DR
- Critics trained on real LLM errors (not synthetic bugs) catch bugs better than human contractors [1]
- Prover-verifier systems iteratively train verifiers to become robust against adversarial attacks, but human accuracy drops when checking sneaky outputs [2]
- Local-model critics must be weaker than the generator they critique, or they hallucinate bugs; human-machine teams with weaker critics reduce false positives [1]

## Findings

1. **Training data construction: Critics learn from real LLM errors, not synthetic bugs.** CriticGPT [1] trains on code with naturally occurring LLM errors from real-world assistant tasks, not artificially injected bugs. The RLHF process rewards critics that correctly identify real problems.

2. **Self-grading/eval loop: External feedback is essential for critics; intrinsic self-evaluation degrades performance.** In self-correction studies [3], LLMs struggle to improve outputs without external feedback, and performance often degrades after self-correction attempts. Critics need a teacher signal (human or stronger model) to learn.

3. **Critic-vs-generator capability gap: A weaker critic can be useful if properly aligned with failure modes.** CriticGPT [1] finds that human-machine teams with a weaker critic catch similar bugs as critics alone but with fewer hallucinated bugs. The key is mitigation of false positives. In prover-verifier games [2], verifiers trained against adversarial examples become robust, but humans struggle to spot sneaky (incorrect) outputs.

4. **Failure modes: Critic hallucinations are the primary failure mode, not the reverse.** Critics trained on real errors [1] can hallucinate bugs (false positives). Human-machine teams [1] reduce but don't eliminate this issue, suggesting critics need calibration or negative signal training.

5. **Design decisions for critic trainers:**
   - **Data source:** Use real generator mistakes, not synthetic errors [1]
   - **Training method:** RLHF with human feedback on mistake identification [1]; adversarial examples (helpful vs sneaky provers) [2]
   - **Critic strength:** Weaker critics are acceptable if combined with humans to filter false positives [1]
   - **Eval loop:** External evaluator (human or stronger model) required; self-evaluation is ineffective [3]
   - **Failure handling:** Explicit calibration for hallucinations, separate training on "correct-but-verbose" signals [1]

## Sources
[1] https://arxiv.org/abs/2407.00215 -- "LLM Critics Help Catch LLM Bugs" (fetched yes)
[2] https://arxiv.org/abs/2407.13692 -- "Prover-Verifier Games improve legibility of LLM outputs" (fetched yes)
[3] https://arxiv.org/abs/2310.01798 -- "Large Language Models Cannot Self-Correct Reasoning Yet" (fetched yes)

## Open questions
- How to calibrate critics to minimize false positives without losing bug-detection ability?
- What's the minimal critic strength that still provides utility when combined with human oversight?
- Can prover-verifier adversarial training generalize beyond code correctness to other error types?
- How does critic training scale with larger models and more complex generator tasks?

## Confidence
medium -- three independent fetched sources agree on core findings, but limited details on training data construction and specific failure mode mitigation techniques
## Review (frontier, 2026-07-02)
verdict: ACCEPT with one correction -- feeds SQ2 directly; the 5-decision list is the
scoping skeleton for the adversarial-critic design session.
- CORRECTION: TL;DR bullet 3 overstates finding 3 -- CriticGPT does NOT say critics must
  be weaker than the generator; it says weaker-critic+human TEAMS cut hallucinated bugs
  vs critics alone. Finding 3's own phrasing is correct; trust it, not the TL;DR.
- CONVERGENCE worth noting: [3] (2310.01798, self-correction degrades without external
  feedback) is already load-bearing in docs/retrieval-critic-design.md -- fleet and
  corpus agree independently. Confidence in that pillar upgrades to high.
- Open questions 1-2 (false-positive calibration, minimal useful critic strength) are
  the right next tasks AFTER the user answers the deferred critic scoping questions.
