# Truth-grounding landscape — the full-fidelity sweep (T285, 2026-08-11 ~06:15)

**Charter (Daniil, pre-sleep directive 1, verbatim in note `pre-sleep-directives-2026-08-11`):**
"There are many platforms and vendors offering various mechanisms for making a
nondeterministic AI provide deterministic, grounded robustly in truth output reliably.
priori.sh is one take, there are others… what other sources should we examine to help us add
those truth grounding factors for ourselves and the different types of work that we do?"

**Arms:** 4× WebSearch (grounding platforms / faithfulness evals / constrained decoding /
provenance standards) + deepseek claims-anatomy lens ($0.007; the taxonomy lens abstained on
the findings-preset citation rule — known misfire, synthesis below is claude's with web
receipts). Frame correction honored: this maps the field to OUR doctrine's needs — outside
articulation sharpens, never charters.

---

## 1 · The seven mechanism classes, mapped to OUR work types

Work types: **(a)** multi-arm research sweeps · **(b)** design fences · **(c)** code changes
with pins · **(d)** corpus-level claims from fans · **(e)** operator-facing reports.

| # | Class | Canonical instances (verified live this sweep) | The guarantee it gives | What it CANNOT give | Grounds which of ours |
|---|---|---|---|---|---|
| 1 | **Retrieval-grounding + citation-required** | Vectara (RAG-as-service, HHEM eval model, Hallucination Corrector, sub-1% claims); Google Vertex grounding; citation-grounding as 2026 procurement bar | answers stay inside supplied evidence; every claim carries a source pointer | that the citation SUPPORTS the span — "citations exist but don't prove support" is the field's named 2026 symptom (our receipt-inflation class, industrialized) | a, d, e |
| 2 | **Faithfulness/hallucination evals** | Braintrust (judge scorers, regression diffs); Galileo (Luna-2, sub-200ms inline blocking); Arize Phoenix (RAG triad, OTel); Patronus Lynx (open-source); Promptfoo (CI-native YAML asserts); FaithBench/HalluLens/FaithLens benchmarks | a measured faithfulness RATE over a distribution, pre- or at-runtime | per-output truth; factuality ≠ faithfulness (the field's own split: wrong-about-world vs unfaithful-to-context) | a, d — and (e) as the rate on the report |
| 3 | **Constrained decoding / structured output** | XGrammar (<40µs/token; default in vLLM/SGLang/TensorRT-LLM since 2026-03), Outlines, Guidance, llguidance; JSONSchemaBench; Anthropic constrained decoding (2025-11) | the output SHAPE is guaranteed — schema-valid, parseable, machine-checkable | content truth; and even temp=0 is not deterministic (batching nondeterminism persists — the field says so plainly) | c, d — every fan verdict schema; our findings preset is class-3-by-prompt, upgradeable to class-3-by-decoder |
| 4 | **LLM-judge calibration** | judge-scorer stacks (Braintrust), panel/debate patterns; our own season scoring (T254) is this class | scalable second opinions with measurable agreement | ground truth — judges need calibration against adjudicated samples (calibrate_the_instrument lesson, ours, independently) | a, b, d |
| 5 | **Deterministic replay / reproducibility** | priori.sh (PIT + as_of + sealed extraction); temp-0+seed regimes; compile-don't-interpret framing ("Compiled AI" 2604.05150) | the same question against the same knowable state re-answers the same | novel-output determinism; only REPLAY determinism | a (sweep re-runs), d (kill-drills), c (pin suites ARE class 5 for code) |
| 6 | **Provenance / attestation standards** | **C2PA 2.1 = ISO/IEC 22144; v2.3 (2025-12) extends signed manifests to UNSTRUCTURED TEXT / LLM outputs**; Content Credentials as "de facto provenance language"; SLSA + Sigstore extending to model/pipeline lineage; **EU AI Act Art. 50 machine-detectable marking, applicable 2026-08-02 — live for nine days** | cryptographically attested ORIGIN and processing chain | truth of content — C2PA's own careful scope: "attested by the signer," never "true" | e — and the store's sha-addressed atoms + hash-sealed transcript copies are class-6-shaped already |
| 7 | **Self-consistency / adversarial verification** | debate patterns, N-version blind; OUR fence culture, backbrief, kill-drills, blind halves | survival under independent attack | consensus ≠ truth (correlated errors; the covariance lesson) | b — and the verification stage of a, c, d |

**The map's verdict:** we are STRONG in classes 4, 5, 7 (judge-with-season-scoring,
pin-replay, fence/backbrief — the doctrine's own organs), PARTIAL in 1 and 3 (packs cite
but spans aren't anchored; schemas by prompt not decoder), and THIN in 2 and 6 (no
faithfulness RATE on our own outputs; no signed provenance on artifacts). The thin two are
exactly what "selling truth" requires: a measured rate and an attested chain.

## 2 · The claims-anatomy template (deepseek lens, kept whole)

Every vendor claim decomposes into: **exact promise / the receipt behind it / what would
falsify it / what it carefully does NOT promise.** Worked examples from the lens: priori.sh
promises knowability-bounded answers (receipt: snapshot manifests; non-promise:
completeness); Vectara promises a sub-1% RATE (receipt: its benchmark; non-promise: any
individual output); Perplexity promises verifiable citations (non-promise: that citations
support the span); C2PA promises attested origin (non-promise: truth). **This four-field
anatomy is T287's claim template.**

**The fleet's three honestly-makeable claims today (lens draft, to be hardened in T287):**
1. "Every shipped slice passed pre-registered RED pins; violations blocked or flagged" —
   receipt: pin suites + gated ledger transitions.
2. "Peer fences intercept and correct a measurable fraction of design defects before
   commit, with an audit trail" — receipt: fence records with dispositions (six tonight).
3. "Sampled verification confirms X% of audited outputs against ground truth, with the
   sample named" — receipt: backbrief records + hand-verified quote checks.
**The claim we must NOT make:** any absolute ("never hallucinates," "always grounded") —
one curated counterexample falsifies it, and the field's honest players all scope to rates.

## 3 · Adopt / adapt / skip (first moves, ranked)

1. **ADOPT — span-anchored citations in packs (class 1):** every fan finding already cites
   `file:line`; extend the verifier to CHECK the span supports the claim (the field's
   "citation ≠ support" gap, closed at our scale by the summary-fidelity pin pattern —
   THE EYE's pin generalized to every pack).
2. **ADOPT — a faithfulness rate of our own (class 2):** run Lynx-class or judge-based
   faithfulness scoring over a SAMPLE of fan verdicts per week; publish the rate on the
   Herald page. Small, funnel-composable, makes "measured, not narrated" literal.
3. **ADAPT — constrained decoding at the ask door (class 3):** the findings preset's parse
   step upgrades from prompt-and-regex to schema-enforced output where the backend supports
   it (deepseek JSON mode); JSONSchemaBench names the eval.
4. **ADAPT — C2PA-text manifests for crown artifacts (class 6):** v2.3 makes signed
   manifests for text real; our artifacts/ copies + transcript copies could carry Content
   Credentials. Watch EU AI Act Art. 50 anyway (public repo, generated content, marking now
   in force). Investigate cost before committing.
5. **SKIP for now:** watermarking (media-centric), attestation-chains for model training
   (SLSA-for-models — we train nothing), inline-blocking runtime guards (Galileo-class —
   our risk profile is research, not chat-to-consumers).

## 4 · Sources

[FutureAGI grounding guide](https://futureagi.com/glossary/llm-grounding/) · [Onyx enterprise RAG 2026](https://onyx.app/insights/enterprise-rag-platforms-2026) · [AiOps citation grounding](https://aiopsschool.com/blog/citation-grounding/) · [Google Research grounding adaptation](https://research.google/blog/effective-large-language-model-adaptation-for-improved-grounding/) · [Braintrust hallucination tools 2026](https://www.braintrust.dev/articles/best-hallucination-detection-tools-2026) · [EdinburghNLP awesome-hallucination-detection](https://github.com/EdinburghNLP/awesome-hallucination-detection) · [RAG faithfulness leaderboards](https://arxiv.org/pdf/2505.04847) · [FaithLens](https://arxiv.org/pdf/2512.20182) · [Awesome-LLM-Constrained-Decoding](https://github.com/Saibo-creator/Awesome-LLM-Constrained-Decoding) · [XGrammar](https://arxiv.org/pdf/2411.15100) · [JSONSchemaBench](https://arxiv.org/pdf/2501.10868) · [Compiled AI determinism](https://arxiv.org/html/2604.05150) · [C2PA standard + limits](https://truescreen.io/articles/c2pa-standard-history-limitations/) · [Content Credentials](https://en.wikipedia.org/wiki/Content_Credentials) · [C2PA/watermarking 2026](https://internet-pros.com/blog/ai-content-provenance-watermarking-c2pa-2026/) · [AI identity standards](https://arxiv.org/pdf/2604.23280)
