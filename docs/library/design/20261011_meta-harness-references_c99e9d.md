---
akashic_id: art_20261011_meta-harness-references_c99e9d
akashic_sha: c0902315561f
schema_version: 1
status: current
type: design
arc: meta-harness
date: 2026-10-11
title: meta-harness-references
gist: "Prior art behind the meta-harness: harness optimisation, replay and evals, attribution and compression, scoped memory."
visibility: fleet
body_type: markdown
seats: [claude]
category: [testing, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-11T00:26:11"
updated: "2026-10-11T00:26:11"
---
<!-- GENERATED PROJECTION of art_20261011_meta-harness-references_c99e9d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# meta-harness-references

# Meta-harness references and prior art

A research agent gathered these on 2026-10-10.
- **[V]**: the agent read the abstract or page.
- **[V+]**: it also read parts of the paper.
- **[K]**: from model knowledge, not re-checked.
- **seen**: appeared in search results only.

Several 2026 papers are newer than my own knowledge, and only their abstracts were read. Check each link before relying on a number, and keep this list up to date as a standing task.

## Harness and scaffold optimisation
- **Meta-Harness** (Lee, Nair, Zhang, Lee, Khattab, Finn, 2026), https://arxiv.org/abs/2603.28052 [V+]. A Claude Code proposer reads the source, scores and *raw traces* of earlier harnesses and writes new ones, keeping a Pareto front. In its ablation, raw traces beat scores alone and scores plus summaries by a wide margin. → tasks 07, 04.
- **Agentic Harness Engineering (AHE)**, https://arxiv.org/abs/2604.25850 [V]. Edits carry falsifiable predicted effects. The gains came from tools, middleware and memory; a system-prompt edit alone hurt. → tasks 07, 09.
- **HARBOR**, https://arxiv.org/abs/2604.20938 [V]. Harness config treated as flags and tuned with constrained, noisy Bayesian optimisation. → tasks 07, 11.
- **Task-CoEvolve**, https://arxiv.org/abs/2608.20169 [V]. Picks the validation tasks where candidates disagree, for about 80% less eval cost. → tasks 03, 07.
- **RRSI**, https://arxiv.org/abs/2609.24972 [V]. Caps the number of edits per candidate and prunes stale ones. → tasks 07, 11.
- **Continual Harness**, https://arxiv.org/abs/2605.09998 [V]. Online self-editing of prompt, subagents, skills and memory.
- **GEPA** (ICLR 2026), https://arxiv.org/abs/2507.19457 [V]. Reflective prompt evolution with Pareto selection per instance; `dspy.GEPA`. → task 07, prose pieces.
- **ACE: Agentic Context Engineering** (ICLR 2026), https://arxiv.org/abs/2510.04618 [V]. Itemised playbook with delta edits; avoids context collapse. → lessons store design.
- DSPy MIPROv2 / SIMBA, https://dspy.ai [K]. ADAS, https://arxiv.org/abs/2408.08435 [K]. Gödel Agent, https://arxiv.org/abs/2410.04444 [K].
- Darwin Gödel Machine, https://arxiv.org/abs/2505.22954 [K]. It faked tool logs, which is why graders must be out of reach.
- AFlow, https://arxiv.org/abs/2410.10762 [K]. Trace/OptoPrime, https://arxiv.org/abs/2406.16218 [K]. SWE-agent ACI, https://arxiv.org/abs/2405.15793 [K].
- Anthropic, "Demystifying evals for AI agents", https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents [V]:
  - 20-50 tasks taken from real failures;
  - several trials per task, with pass@k or pass^k;
  - code, model and human graders, in clean environments;
  - read the transcripts.

## Replay and evaluation
- **Harbor** (from the Terminal-Bench team), https://github.com/harbor-framework/harbor [V]. Containerised tasks, parallel trials, built-in Claude Code and Codex agents. → task 04.
- SWE-bench construction, https://www.swebench.com [K]. Issue, the snapshot before the fix, and hidden tests from the fix. → task 03.
- Miller, "Adding error bars to evals", https://arxiv.org/abs/2411.00640 [V]. Paired differences, clustered errors, power analysis. → task 05.
- tinyBenchmarks, https://arxiv.org/abs/2402.14992 [V]. Small anchor sets chosen by item response theory.
- replayagent, https://github.com/RuthvikBathala/replayagent [V; the repo itself was not inspected].

## Attribution and compression
- Cross-component interference, https://arxiv.org/abs/2605.05716 [V]. The all-in scaffold lost to subsets; 56% of submodularity checks were violated; main effects gave R² 0.92.
- "Where does harness-optimization value live?", https://arxiv.org/abs/2609.02889 [V, abstract]. Value concentrated in one slot; spreading the budget evenly froze progress.
- "Agents that Matter", https://arxiv.org/abs/2605.27621 [V]. Leave-one-out about as good as Shapley, for far less.
- ContextCite, https://arxiv.org/abs/2409.00729 [V]. Random masks plus a sparse linear surrogate.
- AttriBoT, https://arxiv.org/abs/2411.15102 [V]. Hierarchical attribution and proxy models.
- Data Shapley / TMC-Shapley, https://arxiv.org/abs/1904.02868 [K]. Delta debugging (Zeller, 2002) [K]. Plackett-Burman designs [K]. Hyperband, https://arxiv.org/abs/1603.06560 [K].
- LLMLingua family: https://arxiv.org/abs/2310.05736, https://arxiv.org/abs/2310.06839, https://arxiv.org/abs/2403.12968 [K].
- Selective Context, https://arxiv.org/abs/2310.06201 [K]. RECOMP, https://arxiv.org/abs/2310.04408 [K]. PromptQuine, https://arxiv.org/abs/2506.17930 [V].

## Scoped memory and compiling lessons into skills
- Grounding Agent Memory, https://arxiv.org/abs/2609.11060 [V]. A read-only curator checks and scopes lessons before they enter long-lived memory. → task 02.
- Memory-R1, https://arxiv.org/abs/2508.19828 [V, snippet]. Relevance versus applicability.
- Voyager, https://arxiv.org/abs/2305.16291 [K]. ExpeL, https://arxiv.org/abs/2308.10144 [K]. Agent Workflow Memory, https://arxiv.org/abs/2409.07429 [K].
- Memp, https://arxiv.org/abs/2508.06433 [V]. SkillWeaver [V]. ReasoningBank [V, summary]. Dynamic Cheatsheet, https://arxiv.org/abs/2504.07952 [K].

## In this repo
- **Forge loop:** `core/recall/forge.py`, `forge_optimizer.py`, `replay.py`, `curator.py`. Design: `docs/library/design/20260701_lesson-forge-evidence-gated-content-opti_fd3204.md`.
- **Behavioural oracle:** `tooling-upgrade/oracle.py`.
- **Arc-replay bench:** `docs/library/design/20260721_the-arc-replay-bench-opening-position-cl_551e03.md`.
- **E1 ablation:** `docs/library/design/20260721_e1-the-stance-recall-ablation-does-activ_1970e5.md`.
- **Integration tiers:** `docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md`.
- **Outcome signals:**
  - `core/renew/session_signals.py`;
  - flip events (`agent/harness/hooks/claude_posttooluse.py`);
  - `learn:repeats` (`learning_store.record_repeat`);
  - `core/coord/task_ledger.py` `done(commit, verified_by)`.
- **Built from this list:** `core/metaharness/` (tasks 03-11), `core/fleet/provenance.py` (task 01) and
  `core/learning/scope.py` (task 02). The build status is in the companion page `meta-harness-plan`.
