# Context Pillar (SYSTEM 4) — design & consolidation plan

Status: historical  (2026-07-09, P4: Proposed plan; never fully built)

Status: PROPOSED (2026-06-19). The goal you set: **load 8–10k tokens of rich,
immediately-usable context so an agent starts informed without burning the
model's own context window.** This plan reuses what already exists rather than
building from scratch — per the [audit](codebase-audit.md) finding that
`project_context.py` is a half-built version of this pillar.

## What already exists to reuse (don't rebuild)

| Source | Module | Gives the context pillar |
|--------|--------|--------------------------|
| Project state (architecture, milestones, tasks, blockers, current work, work log) | `project_context.py` — `derive_full_context_for_agent_repriming()` | the layered "where the project is" picture |
| Decisions | `AgentMemory.get_decisions` + coordinator `DecisionCache` | "what was already decided" (don't re-reason) |
| Learnings | `LearningStore` (experiment outcomes) + `AgentMemory` (experiences/reflections) | "what we learned the hard way" |
| Recent signals / handoffs | `AgentSignalLedger.replay_signals` | "what just happened / who handed off what" |
| Recent actions | session logs (`project_context._load_recent_actions_from_sessions`) | "the last N things agents did" |
| Relationship vocabulary | `core/foundation/relationship_types.py` (66 types) | a way to *rank* relevance semantically |

The pillar is therefore an **aggregation + ranking layer on top of the whole
system** — the capstone that ties Store, Ledger, AgentMemory, LearningStore, and
the coordinator together.

## Target architecture (`context/` package — fills the existing stub)

```
context/
  project_state.py   project_context.py migrated onto Store (survives Redis down)
  briefing_loader.py  load_briefing_from_previous_handoff(agent)   <- AgentSignalLedger HANDOFF + coordinator briefing
  decision_loader.py  load_decisions_applicable_to_task(task)      <- AgentMemory + DecisionCache
  learning_loader.py  load_learnings_ranked_by_relevance(task)     <- LearningStore + AgentMemory
  blocker_loader.py   load_blockers_preventing_progress()          <- project_state + coordinator BlockerMonitor
  ranker.py           rank by relevance x importance x recency, + relationship-type weighting
  summarizer.py       summarize_to_fit_token_budget(section, budget)
  aggregator.py       assemble_context(task, token_budget=9000)  -> orchestrates all of the above
  quality_scorer.py   score_context_quality()  -> coverage %, budget adherence, freshness
```

`assemble_context(task, token_budget)` is the one public entrypoint:
loaders gather → ranker prioritizes → summarizer trims to each section's budget →
aggregator dedups + assembles → quality_scorer rates the result.

## Best practices baked in (from the memory research)

- **Token budget is a hard constraint**, split across sections (illustrative):
  briefing 1.5k · decisions 2k · learnings 2.5k · blockers 1k · project state 1.5k
  · recent 1.5k. The ranker fills each section with its highest-scored items; the
  summarizer trims overflow.
- **Relevance × importance × recency** scoring (Generative Agents), not keyword
  overlap. Importance set at write time; recency decays; relevance starts
  keyword-based with an embeddings seam for later.
- **Relationship-type weighting is the differentiator** — your 66-type vocabulary
  lets the ranker prefer, say, `prevents` / `supersedes` / `derived_from`
  relations for a given task. Few systems can rank semantically like this.
- **Quality score**, so context assembly is measurable: did we cover every source
  type? did we stay within budget? how fresh is it?
- **Graceful degradation** — every loader reads through Store/Ledger, so a Redis
  outage degrades quality instead of returning `{"error": ...}` (the current
  `project_context.py` hard-fails when Redis is down — the key robustness fix).

## Phased plan (each independently shippable + verifiable)

- **Phase 1 — Migrate `project_context.py` → `context/project_state.py` onto Store.**
  Same foundation-fit we did for AgentMemory: route persistence through `Store`,
  fix the Redis-down hard-fail, keep the semantic API. *Verify: full context
  round-trips with Redis down.*
- **Phase 2 — Loaders.** Thin readers: briefing / decision / learning / blocker,
  each over an existing source. *Verify: each returns real data from a seeded store.*
- **Phase 3 — Ranker.** relevance × importance × recency + relationship-type
  weighting. *Verify: fresh/important/related items rank above stale/unrelated.*
- **Phase 4 — Summarizer + aggregator + quality_scorer.** Assemble to the token
  budget; score coverage/budget/freshness. *Verify: output stays under budget and
  covers all source types; quality score reflects gaps.*
- **Phase 5 — Wire into agent startup.** Replace/augment `agent_briefing_loader`
  and the coordinator briefing so agents boot with ranked 8–10k context. *Verify:
  a cold agent gets useful context without Redis, within budget.*

## Design rules locked by research (see docs/context-compaction-skeleton-research.md)
- **The Context pillar IS the harness** (Anthropic's pattern): query slices of the
  Ledger/Store event stream → rank → compact → inject. Logic isolated so it can
  change per model generation.
- **Budget is a FEATURE, not a limit.** "Context rot" means more tokens = worse
  recall. Target the *smallest high-signal* 8–10k; never "include everything".
- **Raw is sacred; compaction is a derived view + a pointer.** Never delete raw
  (Ledger is append-only). A compacted/skeleton entry carries a `source` pointer
  (Ledger cursor id / experiment id) → drill-down + reconstruction, footprint down
  with zero data loss.
- **Skeleton format = Markdown + YAML**, hierarchical `Domain > Topic > Entry`,
  edges = relationship_types, each entry `{type, tags, relates, confidence, source}`
  — human-readable + machine-parseable = "the shape of an idea". This is `chronicles/`.
- **Distiller is hierarchical + writer→critic** (faithfulness gate).

## Open decisions before building
- Token-budget split across sections (the numbers above are a starting guess).
- Relevance: keyword + relationship-type now, embeddings later (seam confirmed).
- Integration: this *replaces* `agent_briefing_loader.py` + the coordinator's
  briefing generation (recommended, to kill duplication) — confirm before deleting.
- Supersession: the Ranker is built supersession-aware now via a hook that defaults
  to "all active"; it activates fully when AgentMemory Phase B lands.
