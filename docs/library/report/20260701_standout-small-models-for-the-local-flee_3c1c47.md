---
akashic_id: art_20260701_standout-small-models-for-the-local-flee_3c1c47
akashic_sha: 2e023f4c0ce6
status: draft
type: report
date: 2026-07-01
title: "Standout small models for the local fleet's subtasks — full frontier research record (2026-07-03)"
gist: "# Standout small models for the local fleet's subtasks — full frontier research record (2026-07-03) provenance: deep-research workflow on Op"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, testing, frontier]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_fleet-dispatch-an-intelligent-easy-struc_303d15
    rel: cites
created: "2026-07-03T12:16:04"
updated: "2026-07-23T21:42:18"
---
<!-- GENERATED PROJECTION of art_20260701_standout-small-models-for-the-local-flee_3c1c47 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Standout small models for the local fleet's subtasks — full frontier research record (2026-07-03)

# Standout small models for the local fleet's subtasks — full frontier research record (2026-07-03)

provenance: deep-research workflow on Opus (R013), 104 agent calls, 22 sources fetched,
108 claims extracted → 25 adversarially verified (2/3-refute-to-kill) → 20 confirmed, 5 killed,
9 after synthesis. Recovered + re-run after the prior session's fleet sub-agents died on credit
exhaustion. This file preserves the FULL findings + citations; the summary note is the compressed
view. Feeds R016 (specialist capability map) and the fleet-dispatch registry (docs/fleet-dispatch-design.md).

DISQUALIFIER (unchanged from bakeoff round 1): fabrication / citation-laundering. A model that
invents or launders sources is out, regardless of leaderboard rank.

## Headline

For a 16GB-VRAM RX 9070 XT running bounded subtask workers, the **GLM family offers no in-budget
option beyond glm-4.7-flash** (which itself spills past 16GB). The **strongest in-budget candidate
set is the Qwen3.5 small dense series** (0.8b/2b/4b/9b, Apache-2.0, on Ollama), which leads the small
tier on standardized leaderboards for both tool-calling and instruction-following. Several sub-15B
models are highly faithful on grounded summarization (Granite-4.0, Gemma-3-12b, Qwen3-8b/4b) — but
that metric is NOT our citation-honesty disqualifier, so it filters, it does not decide. **Phi-4-mini
is a documented fabrication risk** (23.5% hallucination) and is excluded. Small models emit **0% usable
JSON under naive prompting** — structured output is a scaffolding problem (grammar/format prompt), not
only a model-selection one.

## Findings (adversarially verified)

1. **GLM family — no in-budget small option.** [confidence HIGH, vote unanimous 3-0]
   GLM-4.7-Flash (30B-A3B MoE, MIT, on Ollama) is the *smallest* GLM release. At Q4_K_M its 19GB build
   does NOT fit 16GB VRAM: measured ~17GB@4K ctx rising to ~20GB@32K (hardware-corner.net); a 16GB GPU
   ran it at 21GB with a 27/73 CPU/GPU split. **MoE does not reduce VRAM under llama.cpp/Ollama — all
   expert weights load.** GLM-5/5.1/5.2 are all 744–753B flagships (744B total / 40B active, variants
   differ only by quantization); no sub-40B Air/Flash GLM-5 sibling exists (only community requests).
   - https://huggingface.co/zai-org/GLM-4.7-Flash · https://ollama.com/library/glm-4.7-flash
   - https://huggingface.co/blog/zai-org/glm-52-blog · https://deepwiki.com/zai-org/GLM-5/1.3-model-variants

2. **Qwen3.5 small dense series — the strongest in-budget set.** [HIGH, unanimous 3-0]
   Variants (Ollama, Apache-2.0, released 2026-03-02): `qwen3.5:0.8b` (1.0GB), `:2b` (2.7GB),
   `:4b` (3.4GB), `:9b` (6.6GB, = `:latest`/default). `:27b` (17GB) sits just over the ceiling.
   All of 0.8b–9b fit comfortably in 16GB.
   - https://ollama.com/library/qwen3.5/tags · https://ollama.com/library/qwen3.5
   - CAVEAT: the "all variants ship 256K context" claim was REFUTED — per-variant context is UNVERIFIED;
     confirm 32K+ empirically (`ollama show qwen3.5:9b`) before relying on it.

3. **Qwen3.5-9B leads the small tier on tool-calling AND instruction-following.** [MEDIUM]
   BFCL-V4: Qwen3.5-9B = 0.661 (#7 overall; ahead of Amazon Nova 2 Pro 0.616, Lite 0.603, Omni 0.583);
   Qwen3.5-27B 0.685 (#5), 35B-A3B 0.673 (#6). IFEval: Qwen3.5-9B = 0.915 (#~12), Qwen3.5-4B = 0.898 (#~16),
   board led by Qwen3.5-27B 0.950.
   - https://llm-stats.com/benchmarks/bfcl-v4 · https://llm-stats.com/benchmarks/ifeval
   - CAVEAT: Berkeley/Gorilla BFCL-V4 table is JavaScript-rendered and could NOT be fetched directly —
     numbers rest on the llm-stats aggregator (secondary; self-labels IFEval "unverified"). The claim that
     sub-4B Qwen3.5 COLLAPSE on BFCL (4B 0.503 / 2B 0.436 / 0.8B 0.253) was REFUTED (plausible, not confirmed).

4. **~8B is the reliable off-the-shelf floor; Qwen3-8B the base winner.** [MEDIUM, single vendor blog]
   Across 8 classification/extraction/QA tasks (base, few-shot, no fine-tune): Qwen3-8B #1 (avg rank 1.75)
   > IBM Granite-3.3-8B (2.57) > Qwen3-4B-Instruct-2507 (3.75) > Llama-3.1-8B (4.14); every sub-8B variant ranks below.
   - https://www.distillabs.ai/blog/we-benchmarked-12-small-language-models-across-8-tasks-to-find-the-best-base-model-for-fine-tuning/
   - CAVEAT: single vendor blog (distillabs sells fine-tuning). The fine-tuned-Qwen3-4B-matches-GPT-OSS-120B claim was REFUTED.

5. **Faithfulness leaders (grounded summarization, Vectara HHEM-2.3, May 2026).** [HIGH]
   Hallucination rate (lower=better, all ~100% answer rate): Phi-4 3.7% · Gemma-3-12b-it 4.4% · Qwen3-8b 4.8% ·
   **IBM Granite-4.0-h-small 5.2%** · Qwen3-14b 5.4% · Qwen3-4b 5.7%. Granite 4 roughly HALVES Granite-3.3-8b
   (10.6% → 5.2%). Phi-4 (3.7%) even beats Llama-3.3-70B (4.1%).
   - https://github.com/vectara/hallucination-leaderboard
   - **CRITICAL SCOPE CAVEAT:** this measures grounded-summary factual consistency at temp=0. It does NOT
     measure the citation-laundering / fluent-fabrication mode that disqualified our bakeoff models. A low
     Vectara score is NECESSARY BUT NOT SUFFICIENT evidence of citation honesty in open-ended/agentic use.

6. **Phi-4-mini-instruct — documented silent-failure risk; EXCLUDE.** [HIGH, majority 2-1]
   23.5% hallucination (76.5% consistency) on summarization — ~6.35× worse than full Phi-4 (3.7%) — despite
   being marketed for extraction. Compounded by verbosity (420-word summaries vs Phi-4's 121 = instruction-ignoring
   + fabrication). (Correction: it is SECOND-worst; ministral-3-3b-2512 at 24.2% is worst.) Deprioritize for
   any faithfulness-critical subtask.
   - https://github.com/vectara/hallucination-leaderboard

7. **Structured output: 0% USABLE JSON under naive prompting — a scaffolding problem.** [HIGH]
   Small 7–9B instruct models (Llama-3.1-8B, Gemma-2-9B, Qwen-2.5-7B) reach ~85% task accuracy but 0% *output
   accuracy* (correct answer, invalid JSON) under naive prompting. Gemma-2-9B wraps every response in markdown
   fences → 0% JSON validity across all 1,319 samples despite 88.4% recoverable. Optimized no-fence prompts lift
   the same models to 84–87% usable. → **grammar-constrained decoding / explicit format scaffolding is mandatory**
   for the extraction lane.
   - https://arxiv.org/pdf/2605.02363 ("When Correct Isn't Usable", Galeone et al., May 2026)
   - CAVEATS: fence-wrapping is a model-specific generation default (GPT-4o does it too), NOT size-related; this is
     Gemma **2** (2024), not Gemma **3** — does not prove Gemma 3 still fence-wraps. Non-peer-reviewed v1 preprint.

8. **BFCL-V4 is the tool-calling benchmark that matters — but its authoritative table is unfetchable.** [HIGH]
   Berkeley Function-Calling Leaderboard is at V4 ("holistic agentic evaluation": single/multi-turn, web search,
   memory, format sensitivity; peer-reviewed PMLR v267). Two same-day fetches returned only framework text, zero
   rows (JS-rendered SPA). So every tool-calling number here is from the llm-stats mirror, NOT verified at Berkeley.
   - https://gorilla.cs.berkeley.edu/leaderboard.html · https://proceedings.mlr.press/v267/patil25a.html

9. **Genuine evidence gap: no standardized benchmark covers the current minis — round 2 is justified.** [HIGH]
   The most recent dedicated small-model subtask benchmark (AscentCore, Apr 2026; 22 quantized configs 1B–14B for
   backend/structured tasks) tested ONLY prior-gen models (Llama 3.2, Qwen 2.5, Gemma 3, Phi-3/3.5, Mistral 7B v0.3,
   SmolLM2) — NONE of GLM, Qwen3.5, Phi-5/Phi-4-mini, SmolLM3, Liquid LFM, Ministral, or Granite 4. The field data
   for our exact candidates does not exist yet → our own bakeoff round 2 is the right call.
   - https://ascentcore.com/2026/04/01/small-llm-performance-benchmark/

## Derived TOP-5 for bakeoff round 2 (each: why · silent-failure risk)

1. **qwen3.5:9b** (6.6GB, Apache-2.0) — leads small-tier BFCL-V4 (0.661) + IFEval (0.915), fits with headroom.
   · Risk: citation-honesty untested (Vectara doesn't measure it); confirm ctx ≥ 32K empirically.
2. **qwen3.5:4b** (3.4GB) — strong IFEval (0.898), small enough to run two in parallel; Qwen3-4b faithfulness 5.7%.
   · Risk: tool-calling weaker than 9b (the sub-4B "collapse" was refuted but degradation is plausible).
3. **granite-4.0-h-small** (IBM, faithful) — 5.2% hallucination (halved from Granite 3.3), enterprise-extraction lineage.
   · Risk: subtask breadth + agentic tool-calling unproven for our loop; confirm Ollama tag + VRAM.
4. **gemma-3-12b-it** — best-in-class faithfulness (4.4%). · Risk: Gemma-2 history of markdown-fence JSON + prior
   Claude Code tool-loop failures; MUST re-test whether Gemma 3 fixed it before trusting it in a tool chain.
5. **qwen3-8b** — off-the-shelf 8-task base winner (rank 1.75), faithfulness 4.8%. · Risk: single-vendor-blog evidence;
   a half-generation behind Qwen3.5.

EXCLUDED: **phi-4-mini** (documented fabrication, 23.5%). No primary data found for Phi-5, SmolLM3+, Liquid LFM,
current Ministral/Mistral-small — research gap, not a negative verdict (see R016 / open questions).

## Refuted claims (killed in verification — recorded so they don't resurface)
- GLM-4.7-Flash "131K context" (1-2). — the ctx figure did not hold on re-check.
- Fine-tuned Qwen3-4B "matches GPT-OSS-120B on 7/8" (1-2). — do not rely on the fine-tune-parity narrative.
- "Every Qwen3.5 Ollama variant ships 256K context" (1-2). — per-variant ctx UNVERIFIED.
- FaithJudge "llama-3.1-8b worst at 28.38%" (0-3). — unanimously refuted.
- "sub-4B Qwen3.5 collapse on BFCL (0.503/0.436/0.253)" (1-2). — plausible, not confirmed.

## Open questions (for R016 / round-2 in-house testing)
1. Actual per-variant context window of `qwen3.5:{0.8b,2b,4b,9b}` — confirm 32K+ before committing to long-page summarization.
2. Do current **Gemma 3** small models still fence-wrap / tool-loop, or is it fixed? Decides Gemma's place in round 2.
3. How do Qwen3.5-4B/9B do on the **citation-laundering probe** (our actual disqualifier), vs grounded-summary consistency? No bench covers this → in-house.
4. Specs/VRAM/faithfulness of Phi-5, SmolLM3+, Liquid LFM, current Ministral/Mistral-small (no primary data found). Will Z.ai ship a GLM-5 Air/Flash?

## Standing caveats
- **Metric mismatch (most important):** Vectara measures grounded-summary consistency at temp=0, NOT citation honesty
  in agentic use — our disqualifier. Leaderboard rank cannot substitute for our own citation-honesty probe in round 2.
- **Source-quality gaps:** BFCL-V4 primary table never fetched (all tool-calling numbers via llm-stats secondary mirror);
  Qwen3-8B base-winner rests on one vendor blog; the 0%-usable-JSON finding is a non-peer-reviewed v1 preprint.
- **Time-sensitivity:** ~2026-07-03 snapshot of a fast field — Ollama tags, leaderboard positions, and the GLM small-sibling
  situation can shift within weeks.

stats: 5 angles · 22 sources fetched · 108 claims → 25 verified → 20 confirmed / 5 killed · 9 after synthesis · 104 agent calls · run wf_03098973-2d9
