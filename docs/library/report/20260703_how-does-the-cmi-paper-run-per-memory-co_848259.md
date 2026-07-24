---
akashic_id: art_20260703_how-does-the-cmi-paper-run-per-memory-co_848259
akashic_sha: e851de2d1d2e
status: draft
type: report
date: 2026-07-03
title: "How does the CMI paper run per-memory counterfactual swaps, and what must Wave B copy?"
gist: "# How does the CMI paper run per-memory counterfactual swaps, and what must Wave B copy? provisional-by: glm_local, 2026-07-03 task: researc"
tenant: solo
visibility: fleet
seats: []
category: [memory, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260703_task-how-does-the-cmi-paper-arxiv-2605-1_6ace61
    rel: cites
created: "2026-07-03T02:16:27"
updated: "2026-07-23T21:42:13"
---
<!-- GENERATED PROJECTION of art_20260703_how-does-the-cmi-paper-run-per-memory-co_848259 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# How does the CMI paper run per-memory counterfactual swaps, and what must Wave B copy?

# How does the CMI paper run per-memory counterfactual swaps, and what must Wave B copy?

provisional-by: glm_local, 2026-07-03
task: research/queue/006-cmi-counterfactual-method.md

## TL;DR
- **UNVERIFIED** CMI uses controlled interventions to estimate how memories affect model outputs [1]
- **UNVERIFIED** They swap candidate memories with held-fixed baseline to measure impact [1]
- Wave B must replicate: counterfactual swap procedure, metric definitions, error-trace handling -- then beat with cheaper REAL episodes

## Findings
1. **UNVERIFIED** CMI proposes a technique called Causal Memory Intervention that "estimates how candidate memories affect the model's answer under controlled interventions" to select memories improving task performance while suppressing unstable/irrelevant/harmful ones [1]
2. **UNVERIFIED** The paper constructs a "causally annotated benchmark" with structured memory banks containing useful memories, irrelevant distractors, and synthetic harmful memories [1]
3. **UNVERIFIED** They compare CMI against baselines including vector-based retrieval, graph-based memory systems, reflection mechanisms, summaries, full-history inclusion, and no-memory [1]
4. **UNVERIFIED** The counterfactual swap procedure: what is held fixed vs swapped between memories [1]
5. **UNVERIFIED** Metric definitions they use to quantify memory impact [1]
6. **UNVERIFIED** Error-trace handling: whether they control for flips caused by error traces (credit confound mentioned in C2) [1]
7. **UNVERIFIED** Compute cost per counterfactual swap [1]
8. **UNVERIFIED** Full counterfactual algorithm steps [1]

## Wave B Bench Checklist (what must be copied)
- [ ] Counterfactual swap procedure: what is held fixed vs what is swapped between candidate and baseline memories
- [ ] Metric definitions: how to quantify memory impact on task performance
- [ ] Error-trace handling: control for confounds where flips are caused by error traces, not learned lessons
- [ ] Compute cost per swap
- [ ] Algorithm precision and reproducibility details
- [ ] Baseline comparison framework

## Open questions
- **UNVERIFIED** Exact counterfactual swap procedure: what is held constant across interventions?
- **UNVERIFIED** Error-trace control: does CMI explicitly account for credit confounds from error traces?
- **UNVERIFIED** Compute cost per swap: per-memory intervention timing and overhead?
- How to make REAL episodes cheaper than CMI's counterfactual interventions while preserving causal attribution?

## Sources
[1] https://arxiv.org/abs/2605.17641 -- Causal Intervention-Based Memory Selection for Long-Horizon LLM Agents (abstract-only, methodology UNVERIFIED)

## Confidence
low -- single abstract source, detailed methodology (counterfactual procedure, metrics, error-trace control) UNVERIFIED -- could not fetch PDF text
## Review (frontier, 2026-07-03) + frontier addendum
verdict: ACCEPT AS HONEST FAILURE, gap closed by frontier -- the worker could not fetch
the PDF and correctly marked EVERYTHING unverified instead of hallucinating a
methodology. That is the contract working. Content gap filled below (frontier fetch of
the HTML full text, 2026-07-03):

### CMI methodology (frontier-verified, arxiv.org/html/2605.17641v1)
- INTERVENTION: three conditions per candidate memory m_i --
  no-memory y_no ~ p(y|x,empty); with-memory y_with ~ p(y|x,{m_i});
  PERTURBED-memory y_pert ~ p(y|x,{m_i_perturbed}).
- METRICS: Utility(m_i) = s_with - s_no ; Stability(m_i) = s_with - s_pert.
  SELECT iff Utility > 0 AND Stability >= 0 (must help AND survive perturbation).
- BENCHMARK: Causal-LoCoMo -- 87 filtered examples derived from LoCoMo via GPT-5
  construction; memory banks = useful (rewritten evidence) + irrelevant distractors +
  SYNTHETIC harmful entries; 432 past sessions, 491 memory entries.
- COST: acknowledged extra inference cost, no mitigation details published.
- CONFOUNDS: no explicit error-trace confound handling found.

### Wave B implications (updates the checklist above)
1. COPY: the three-condition intervention shape + the Utility/Stability pair -- the
   perturbation condition is genuinely good (tests brittle-cue reliance; adopt).
2. BEAT on: (a) REAL episodes (ours are live ledger flips, theirs are 87 synthetic
   GPT-5-constructed examples); (b) token-cost-normalized value rate (they only
   acknowledge cost); (c) explicit error-trace confound control (field-survey C2 --
   absent in CMI); (d) scale via the fleet (interventions are embarrassingly parallel
   and free on local tokens).
3. MemoryArena (task 001, 2x timeout) escalates to the same frontier session that
   designs Wave B -- one paper-reading pass covers both.
