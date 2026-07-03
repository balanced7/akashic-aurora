# How does Hermes Agent's Mixture of Agents 2.0 work in detail, and which elements should Akashic Aurora adopt for its local-model fleet?

provisional-by: glm_local, 2026-07-03
task: research/queue/005-hermes-moa2-applicability.md

## TL;DR
- MoA uses N reference models plus one aggregator: references provide analysis without tools, aggregator synthesizes and executes [1][2]
- Performance gains: ~8-11% over strongest single model on HermesBench, but latency rises ~6x and costs ~80x on OpenRouter [1][3]
- No clear local-model sequential patterns; parallel N+1 calls require substantial compute for high-value tasks [1][2][3]

## Findings

**MoA architecture is strict N+1 parallel orchestration.** Each iteration runs all N reference models first (no tool schemas, only user/assistant text), then feeds their outputs as private context to one aggregator that writes response and emits tool calls [1]. This approach keeps calls cheap by avoiding strict-provider rejections [1] and works recursively over updated conversations including tool results [1].

**Per-role temperature discipline is explicit.** Configuration defines reference_temperature (0.6 for advisors) and aggregator_temperature (0.4 for acting model) rather than global settings [1]. This temperature split enables distinct behavioral modes: more exploratory reference outputs and more decisive aggregator synthesis.

**Failure handling is graceful degradation, not fail-fast.** Credential failures on one reference model don't abort the turn; the failure is included in reference context and processing continues with remaining models [1]. This makes the system resilient to individual model unavailability.

**Performance tradeoffs are asymmetric.** Vendor claims show ~6-8pt gain (0.8202 vs 0.7607 for Opus) on HermesBench, but hands-on tests report 6x latency and 80x cost vs single models [1][3]. One teardown exposed the economic reality: structural necessity of feeding all reference opinions into aggregator context drives the cost curve [3].

**Recursive MoA is blocked combinatorially.** Attempts to apply MoA to reference outputs are prohibited, preventing exponential complexity explosion [2]. This constraint makes MoA a shallow orchestration layer rather than recursive hierarchy.

**No documented sequential advisor patterns for VRAM constraints.** None of the fetched sources describe sequential reference model execution or local-model-specific adaptation strategies for VRAM-constrained scenarios [1][2][3][4].

**Parallel mappings to Akashic Aurora concepts:**
- parallel: reference outputs as recall-at-action injection (private context at conversation tail preserves cached prefixes) [1]
- parallel: aggregator as evening-review aggregation (synthesizes multiple perspectives before committing response) [1][2]
- parallel: N+1 parallelism as judge panel (multiple reviewers + synthesizer) [1]
- parallel: per-role temperatures as retrieval-critic independence ladder (exploratory vs decisive roles) [1]
- parallel: failure handling as graceful degradation with partial context [1]
- no parallel: configuration as YAML presets (Akashic has different discipline; no direct map) [1][2]

## Open questions
1. What is the aggregator prompt text that merges reference outputs? This is critical for adoption but not exposed in public docs [1].
2. HermesBench methodology: what tasks, evaluation rubric, and baselines define the 0.8202 score? [1][2]
3. Failure mode severity: when aggregator anchors on one reference vs when disagreements require re-calling, what's the guidance? [1]
4. Task-type heuristics: for which task types does 8% gain justify 6x latency and 80x cost? [3]
5. Single-GPU patterns: any workaround for VRAM-constrained environments that don't exist in public docs? [1]

## Sources
[1] https://hermes-agent.nousresearch.com/docs/user-guide/features/mixture-of-agents -- official MoA docs, configuration, aggregator behavior, HermesBench scores, failure mode, no local model specs
[2] https://www.tonyreviewsthings.com/hermes-agent-mixture-of-agents-20/ -- integration across surfaces, community reception, recursive MoA blocked, hands-on notes
[3] https://dev.classmethod.jp/en/articles/hermes-agent-moa-first-touch/ -- ~6x latency, 28-30s tool-calling, 80x cost breakdown, aggregator as virtual provider
[4] https://blogs.nvidia.com/blog/rtx-ai-garage-hermes-agent-dgx-spark/ -- sub-agent isolation concept, local-first orientation (but no MoA-specific patterns)

## Confidence
medium -- three sources provide consistent architecture, but four claims are UNVERIFIED: (1) aggregator prompt text [1], (2) HermesBench methodology [1][2], (3) task-type thresholds for cost/benefit tradeoff [3], (4) single-GPU sequential patterns [1][2][3][4]. Vendor blog (4) is tangential to MoA itself and offers no operational details.
## Review (frontier, 2026-07-03)
verdict: ACCEPT -- added real value beyond the frontier scoping (which it correctly did
not re-derive).
- THE GEM: hands-on cost teardown -- ~6x latency, ~80x token cost on cloud APIs [3].
  This reframes MoA adoption: reserve for highest-value judgments... OR run advisors on
  the free local fleet, where the 80x multiplier costs ~nothing. Our sequential-MoA
  idea remains an OPEN LANE (finding: no documented VRAM-constrained/sequential advisor
  pattern anywhere) -- consistent with the frontier record's unclaimed-lanes list.
- Useful specifics: per-role temperatures (advisors 0.6 / aggregator 0.4), graceful
  degradation on advisor failure, recursive MoA deliberately blocked.
- Parallel-mapping lines delivered as tasked; the evening-review-as-aggregator mapping
  now has vendor-benchmarked precedent.
- Open question 1 (aggregator prompt text) -> add to next Hermes repo sweep (open source).
