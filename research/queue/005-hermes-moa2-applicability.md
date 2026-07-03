status: queued
# TASK: How does Hermes Agent's Mixture of Agents 2.0 work in detail, and which elements should Akashic Aurora adopt for its local-model fleet?
feeds: SQ2+SQ3 (MoA aggregation for fleet + critic independence)
seeds:
- https://hermes-agent.nousresearch.com/docs/user-guide/features/mixture-of-agents
- https://www.tonyreviewsthings.com/hermes-agent-mixture-of-agents-20/
- https://dev.classmethod.jp/en/articles/hermes-agent-moa-first-touch/
- https://blogs.nvidia.com/blog/rtx-ai-garage-hermes-agent-dgx-spark/
notes: Frontier scoping already pinned (2026-07-02, do not re-derive): MoA presets are
  VIRTUAL MODELS -- reference_models are tool-less advisors that see only user/assistant
  text (no system prompt, no tool transcript); only the aggregator acts (writes response,
  emits tool calls); one round per agent-loop iteration, recursively applied; reference
  outputs inject as private context at the conversation TAIL to preserve cached prefixes;
  YAML presets with per-role temperatures; vendor-claims ~6-8pt gain over strongest
  single model. Chase DEEPER: (1) the aggregator prompt itself (what instruction merges
  advisor outputs -- find it in their open-source repo if public), (2) community/hands-on
  reports: when does MoA help vs hurt (task types, latency, cost multiplier), (3) failure
  modes (advisor disagreement, aggregator anchoring on one advisor), (4) HermesBench
  status/methodology if released, (5) any single-GPU or local-model usage patterns
  (VRAM-constrained = SEQUENTIAL advisors -- does anyone do this?). For EACH element add
  a "parallel:" line mapping to Akashic concepts (recall-at-action injection discipline,
  retrieval-critic independence ladder, evening-review-as-aggregation, judge panels) or
  "no parallel". "Done" = an adoption-candidates list with effort/benefit guesses a
  designer can adjudicate.
