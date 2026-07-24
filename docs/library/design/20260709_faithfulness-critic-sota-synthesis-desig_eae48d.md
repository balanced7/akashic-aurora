---
akashic_id: art_20260709_faithfulness-critic-sota-synthesis-desig_eae48d
akashic_sha: d17d7d2e4534
status: fossil
type: design
date: 2026-07-09
title: "Faithfulness critic — SOTA synthesis & design rationale (FAITH-1)"
gist: "**Date:** 2026-06-29 · **Method:** 5 parallel research tracks (LLM-judge failures, deterministic signals, NLI/SummaC lineage, RAG citation g"
tenant: solo
visibility: fleet
seats: []
category: [security, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260709_faithfulness-critic-sota-synthesis-desig_eae48d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Faithfulness critic — SOTA synthesis & design rationale (FAITH-1)

**Date:** 2026-06-29 · **Method:** 5 parallel research tracks (LLM-judge failures, deterministic
signals, NLI/SummaC lineage, RAG citation grounding, shadow-mode gates) → synthesis → applied.
Implementation: `core/primitives/faithfulness.py`; tests: `tests/test_faithfulness.py`.

## The mandate
Gate whether a distillation is trustworthy, **deterministically and with NO LLM** (7-8B local box),
cheap, on the write path. Today `chronicler._compute_metrics` computes faithfulness then discards it,
and it had a false-positive bug. Rule: **validate before you gate; ship observational first.**

## What the SOTA says — and why we chose what we chose

### 1. Don't judge with an LLM, and don't trust fuzzy scores
- LLM-as-judge has systematic **position bias** (GPT-4 ~30% first-slot; rankings flip by reordering — [Zheng 2023](https://arxiv.org/abs/2306.05685), [Wang 2024](https://arxiv.org/abs/2305.17926)) and **self-preference** ([Panickssery 2024](https://arxiv.org/abs/2404.13076)).
- Automated coherence is **"broken"** — declares winners humans can't distinguish ([Hoyle 2021](https://arxiv.org/abs/2107.02173)).
- General faithfulness metrics perform **near chance** (best ~0.70 AUROC — [arXiv 2605.25052](https://arxiv.org/abs/2605.25052)).
→ **Decision: deterministic, no model.**

### 2. Overlap/ROUGE is faithfulness-blind and gameable → keep it SOFT
- ROUGE-1 ↔ faithfulness correlation **0.197** ([Maynez 2020](https://arxiv.org/abs/2005.00661)); 25% hallucination at high ROUGE ([Ji 2022](https://arxiv.org/abs/2202.03629)).
- **30% of *extractive* summaries are still unfaithful** ([Zhang 2023](https://aclanthology.org/2023.acl-long.120/)); coverage rewards copy-paste ([Grusky 2018](https://aclanthology.org/N18-1065/)).
- NLI lexical-overlap heuristics false-positive **~33%** ([PrefixNLI](https://arxiv.org/pdf/2511.01359)).
→ **Decision: grounding overlap is REPORTED (confidence + a note), never the hard gate** — gating on it would block legitimate paraphrase (the abstractiveness↔faithfulness tradeoff, [Dreyer 2023](https://aclanthology.org/2023.findings-eacl.156/)).

### 3. The robust, deterministic signals we DO hard-gate
- **Pointer-resolution.** LLM citation hallucination is rampant: GhostCite measured **50.3%** invalid across 13 models ([Xu 2026](https://arxiv.org/abs/2602.06718)); "Cited but not Verified" found surface-valid citations whose content is unsupported ~50% ([2025](https://arxiv.org/abs/2605.06635)). Best-practice minimal check = **pointer resolves + content supported** (Salesforce; ALCE uses NLI on top — [Gao 2023](https://arxiv.org/abs/2305.14627)). → every line's `(source:)` must resolve to a real input atom.
- **Number/identifier consistency.** FactCC's *own* negative-example recipe is entity-swap / pronoun-swap / **number-perturbation** ([Kryściński 2020](https://aclanthology.org/2020.emnlp-main.750/)); NLI models specifically **fail on numbers** ("two"≡"four" entailed — [Breaking-NLI](https://www.jpatrickpark.com/project/breaking_nli/)); entities are ~⅓ of tokens with ~2× hallucination rate ([EHI 2024](https://arxiv.org/abs/2507.22744)). → a number in a line absent from its cited source = fabricated figure = unfaithful. (Catches what even NLI misses; ~0 FP because it's exact-subset.)
- **Untraceable line.** A content claim with no pointer can't be grounded → unfaithful (the lossless-pointer rule).

### 4. Ship observational before enforcing
Shadow-mode is the standard rollout: run the gate on real traffic, log verdicts, measure FP/FN before it blocks ([Smith shadow-mode](https://christophergs.com/machine%20learning/2019/03/30/deploying-machine-learning-applications-in-shadow-mode/); [ML Test Score, Breck 2017](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45742.pdf)); 0.5 thresholds are suboptimal — tune to the cost matrix ([Evidently](https://www.evidentlyai.com/classification-metrics/classification-threshold)).
→ Our extractive heuristic writer copies each item's source verbatim, so the gate is a **no-op on today's output** (proven: `test_no_false_positive_on_real_output`, conf=1.0) and the **forward gate** for a future LLM writer. It's wired-and-ready, not yet biting — exactly shadow posture.

## Our critic (the synthesis)
Per distilled line `- <summary> [relates: …] (source: S)`:
| signal | type | rationale |
|---|---|---|
| `S` resolves to a real input source | **HARD** | citation hallucination is the dominant failure |
| no number in the line absent from `S`'s text | **HARD** | fabricated figures are the worst lie; NLI misses them |
| line has a source pointer at all | **HARD** | lossless-pointer rule |
| token overlap of line→cited source | **SOFT** (confidence) | overlap is gameable/FP-prone; paraphrase-safe |

Verdict `faithful = no untraceable ∧ no unresolved ∧ no fabricated-number`. `confidence` = mean overlap.
Paren-safe source regex (line-final `)`) regression-guards the old false-positive bug.

## Deliberately deferred (honest scope)
- **Named-entity (non-numeric) consistency** — high value (EHI) but needs NER; deterministic capitalization
  heuristics false-positive on technical terms. Add when a small model/daemon is resident.
- **Sentence/dependency-arc entailment** (SummaC/[DAE](https://aclanthology.org/2020.findings-emnlp.322/)/[AlignScore 355M](https://aclanthology.org/2023.acl-long.634/)) — model-based; the upgrade path once an LLM writer exists and overlap-soft proves insufficient.
- **τ tuning** — `grounding_tau=0.5` is only a reporting threshold today; must be characterized on labeled
  pairs ([BUMP minimal pairs](https://aclanthology.org/2023.acl-long.716/)) before overlap is ever promoted to a gate.
