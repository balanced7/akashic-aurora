# Outside-world scan: heterogeneous ensembles, and what it means for our fan

Status: current (2026-08-07)
Scope: the ENSEMBLE/VERIFICATION axis. The orchestration-framework layer (A2A envelopes,
capability registry, Restate durable promises, LangGraph/AutoGen/Swarm) was already banked by
kimi 2026-07-28 in `research_web_multi_agent_orchestration_prior_art_synthesis`; this does not
repeat it.
Bears on: T229 (fan across learners), T228 (mode-aware diversity), `scripts/ask_panel.py`.

## The headline, and it is not the one I wanted

There is a live disagreement in the literature about whether mixing models helps at all, and
**both sides measure an objective we do not have.**

**Self-MoA** ([2502.00674](https://arxiv.org/html/2502.00674v1), Princeton, Feb 2025) finds that
aggregating N samples from the single best model BEATS mixing different models: +6.6 on
AlpacaEval 2.0, +3.8 average across MMLU/CRUX/MATH. Its stated mechanism: *"pursuing cross-model
diversity may inadvertently include low-quality models, resulting in a quality-diversity
trade-off"*, and *"MoA performance is rather sensitive to the quality, and mixing different LLMs
often lowers the average quality of the models."*

**Mixture of Complementary Agents** ([2605.24048](https://arxiv.org/html/2605.24048v1)) directly
contradicts it: proposers chosen for COMPLEMENTARITY beat the individually-best proposer with
"nontrivial gaps". Its selection criterion is marginal contribution to *summarizer accuracy*, and
it is explicit that *"any selection rule that evaluates proposers without reference to [the
summarizer's] information can miss the complementarity that makes a selection optimal."* It also
names when heterogeneity HURTS: on MMLU-Pro, *"where [the strongest model] alone composes well
with the summarizer and adding diverse but lower-accuracy proposers degrades aggregation."*

### Why the disagreement does not adjudicate our case

Both architectures are **N proposers -> ONE aggregator -> one answer, scored against ground
truth.** Self-MoA: *"MoA first queries multiple LLMs (proposers) ... and then uses an LLM
(aggregator) to synthesize and summarize these responses into a high-quality response."*

**The aggregator is the dilution channel.** A weak proposer hurts because a summarizer averages
it into the single output. That is the entire documented harm mechanism.

Our review/discovery case has no summarizer. N reviewers, a conductor reads all of them, and any
unique TRUE finding is pure gain — a weaker model that surfaces one real defect the others missed
is a win, not a drag on an average.

I asked Self-MoA's text directly whether it measures our objective. It does not:
*"No evidence in the paper measures coverage, recall, or union of distinct findings. The research
exclusively focuses on single synthesized answer quality."* The complementarity paper concedes
the same boundary from its side: *"label-level algorithms target multiple-choice tasks; extending
them to open-ended generation requires a reliable evaluation metric."*

**CONFESSION, and it is the point of this section.** I cannot cite either paper as SUPPORT for
T229. Neither tests coverage. What I can say — and it is much weaker than "the research backs
us" — is that the literature's OBJECTION to heterogeneity does not transfer to us, because its
mechanism requires a component (the summarizer) that our review path does not have. An objection
that fails to apply is not evidence in favour.

Worth noting: Self-MoA's own exception is close to our situation. In a constructed task *"where
each individual model excels in a specific subtask"*, Mixed-MoA beat Self-MoA. A large code
surface with per-model blind spots is arguably that task. Arguably — not measured here.

## The sharpest thing found, because it contradicts my own design

A practitioner account of running swarms on production code for three months
([Medium, May 2026](https://medium.com/engineering-playbook/i-ran-a-multi-agent-ai-swarm-on-production-code-for-3-months-heres-what-actually-works-and-what-d615136226ba),
via search summary — I did not fetch the full text, so treat the wording as reported) describes
merging by **consensus**: several prompts review the same code and *flag an issue only when they
agree*, because *a single hallucinated assumption in one branch can poison everything downstream*.

That is the opposite of union, and **it would have destroyed our one real result.** In the
cross-learner panel of 2026-08-07, DeepSeek uniquely found the `--bg` argv-length defect (T231,
reproduced with a 40k prompt, WinError 206). Gemini and GPT both missed it. An agree-only gate
discards it.

### The resolution, and it is about verification cost, not about voting

Consensus gating buys PRECISION by sacrificing RECALL. It is the right trade **when a claim is
expensive to check**. It is the wrong trade when verification is cheap.

Here, verification cost was ~30 seconds and one command: write a 40k file, run
`ask --bg --prompt-file`, watch it fail. Against that, a discarded real defect is expensive and
possibly permanent.

So for THIS repo the rule is **union, then verify** — never consensus-gate — and it is not a
preference, it is a fit with machinery we already have. The method baseline is RED-pin-first, and
the adversarial-verify pattern already treats every finding as a claim to be refuted. Union +
cheap verification dominates consensus filtering exactly where a pin can be written. Where a
claim CANNOT be cheaply pinned, consensus gating becomes the right instrument again.

## Adaptable, concrete

1. **NO DEFAULT AGGREGATOR if `ask_panel` folds into `ask_many` (T229).** The only documented
   harm from mixing models runs through a summarizer. Keep the union; let the conductor read.
   If an aggregator is ever added, Self-MoA is the warning label.
2. **Agreement across LEARNERS is worth more than agreement across samples**, and our diversity
   verdict cannot currently tell them apart — T228 gave the fan two shapes; a heterogeneous-
   learner fan is a genuine third, and it is the only one where `collapsed` is evidence rather
   than redundancy.
3. **Per-branch evidence packs.** Practitioner accounts report scoping each agent's context to
   what it needs (security agent sees the diff plus dependencies, style agent sees the diff plus
   the style guide) with a reported ~60% token reduction. `ask_many` currently builds ONE shared
   context for every branch (`build_context` is called once, outside `_one`). For a transect of
   different lenses that is both wasteful and blunt.
4. **Selection is a real subproblem, and we have not touched it.** Complementarity selection is
   greedy over marginal contribution, not "pick the best models". Our panel roster is a hardcoded
   list of three in `ask_panel.py:PANEL`. Not worth solving at n=3; worth knowing it is a known
   problem with known algorithms if the roster grows.

## Where I dissent from the prior art, with evidence

Practitioner guidance says *the orchestrator never reviews code itself, only delegates and
aggregates*, because an executing orchestrator pollutes its own decision context.

On 2026-08-07 the reverse held, repeatedly. The five-lens fan produced competent, well-hedged
answers and found nothing that changed the day. Every defect that mattered — the refused-evidence
silence, `--bg` eating `--fan`, the ORPHANED completed fan, the unrunnable diversity prescription
— was found by the conductor either running the tool or reading the code. The panel's one real
find (T231) came after the conductor designed the experiment that made it findable.

I am not generalising from one day to a law. But the local evidence says the conductor reviewing
is where the value was, and delegation was worth most when it was pointed at a question the
conductor had already sharpened.

## Sources

- Self-MoA: https://arxiv.org/html/2502.00674v1
- Mixture of Complementary Agents: https://arxiv.org/html/2605.24048v1
- Adaptive stability detection (debate early-stop; assessed and REJECTED for our fan — all
  branches dispatch concurrently, nothing left to cancel): https://arxiv.org/html/2510.12697v1
- Delegation vs majority: https://arxiv.org/pdf/2606.08098
- Sub-agent fan-out / context isolation: https://agentpatterns.ai/patterns/multi-agent/sub-agents-fan-out/
- Production swarm account (search summary only, full text NOT fetched):
  https://medium.com/engineering-playbook/i-ran-a-multi-agent-ai-swarm-on-production-code-for-3-months-heres-what-actually-works-and-what-d615136226ba
