# Master Roadmap — synthesis & sequenced next steps

> **STATUS 2026-07-03 — this doc is the FOUNDATION-era synthesis (Waves 0–5, through 2026-06-20)
> and is now historical.** Those waves shipped; the work since (intelligence spine, recall-at-action
> + the outcome-credited funnel, the leapfrog plan, the local-model fleet, corpus sharpening S1/S2,
> and the revealed a-series assistant goal) lives in the durable **notes** — run `py agent_cli.py boot claude`
> then `notes --json`; that is the living "START HERE". Recent design docs: `docs/fleet-dispatch-design.md`
> (calling local models), `docs/s2-consolidation-design.md` (corpus sharpening). The waves below still
> hold as the bedrock they built.
>
> **ACTIVE TRACKS (2026-07, current work — plans live in their design docs):**
> - **Reliability / supervision (L0–L4)** — keep the agent fleet alive & recoverable.
>   Plan: `docs/agent-failure-modes-mitigation-roadmap-2026-07.md`. Shipped: L0/L1/L5/L3a/L3b/L3b-auto.
> - **The Mediation Membrane (System 5 / agent experience)** — the substrate between agents and Akashic
>   that cuts the cognitive load of using it (Surface / Capture / Enforce / **Unify the door**). This is
>   the fuller framing of the old *Wave 4 (Unify the ACI)* below — the membrane already exists as the
>   half-built **hook layer**. Plan: `docs/agent-membrane-design-2026-07.md`. **Status: designed, in
>   research before the first slice (door-parity).**
> - **Comprehension layer** — ARCHITECTURE/LEXICON/PRINCIPLES/INDEX now guarded by `check_comprehensibility.py`.

Date: 2026-06-19. This ties together everything in `docs/` and memory into one
plan, grouped so each piece of work serves multiple goals and no research is
wasted. Read this first; the linked docs are the depth.

## The system, as one picture

A layered stack — each layer built on the one below, agents touch only the top:

```
System 5  Agent Interface (ACI)      how agents DO things        docs/agent-interface-aci.md
System 4  Context pillar             what agents KNOW            docs/context-pillar-plan.md
System 1-3 Domain: memory, signals,  decisions/learnings/        docs/learning-memory-*.md
           coordination               coordination
System 0  Foundation: Store + Ledger  persistence (state/events)  docs/architecture.md   [DONE]
          + AgentSignalLedger, reconciler, fail-fast
```

"Know" (System 4) + "Do" (System 5) = the complete agent experience, standing on
a clean persistence foundation.

## What's done (the bedrock holds)

- Store + Ledger primitives, 3 backends, fail-fast, dual-write, tested.
- AgentSignalLedger; LearningStore on Store; AgentMemory **Phase A** on Store.
- redis_sync_coordinator collapsed to a reconciler; orphans retired.
- Naming made coherent (ubiquitous language + genus/species rule).

## The research corpus (so none of it is wasted)

| Doc / memory | What it gives the plan |
|--------------|------------------------|
| `docs/codebase-audit.md` | prioritized cleanup backlog; clean-core/stale-shell finding |
| `docs/learning-memory-analysis.md` + `-integration-plan.md` | CoALA mapping; Reflexion guardrails; Phases B–E |
| `docs/context-pillar-plan.md` | 5-phase Context design reusing project_context.py |
| `docs/agent-interface-aci.md` | System 5: unify the door; errors teach; measure |
| `docs/coding-principles-research.md` | DDD ubiquitous language; refactor patterns; **guardrails** |

## The key insight: build cross-cutting primitives ONCE

Several "separate" tasks are really the *same machinery* used in two places.
Building these once, at the seam, is the biggest anti-waste lever:

- **Ranker** (relevance × importance × recency + relationship-type weighting) →
  needed by the Context pillar (System 4) AND AgentMemory retrieval (`get_similar`).
- **Distiller** (writer→critic summarization to a token budget) → needed by the
  Context summarizer (System 4) AND the consolidation→`chronicles/` loop (Memory
  Phase D).
- **Supersession** (temporal: a new fact retires an old one) → needed by AgentMemory
  Phase B AND the Context ranker (don't surface retired facts).
- **"Migrate-onto-Store" playbook** (the AgentMemory Phase A pattern) → reused by the
  Context pillar Phase 1 (project_context) AND any remaining Redis-only module.

And several tasks serve multiple threads at once:
- **bare-except sweep** = audit robustness item **and** ACI "errors that teach."
- **project_context consolidation** = audit item #3 **and** Context pillar Phase 1.
- **guardrails** = coding-principles item **and** the thing that protects every
  other change from decay.

## Sequenced waves (grouped next steps)

Ordered by dependency and leverage. Each wave names the research it consumes.

### Wave 0 — Lock the foundation ✅ DONE (2026-06-19)
*Consumed: coding-principles.* Cheap, protects everything after it.
- `docs/LEXICON.md` ✅ — the ubiquitous language written down (naming rules +
  every core term + the layer dependency order).
- `scripts/check_boundaries.py` ✅ — 4 rules over `core/` (redis-only-via-connector,
  no-bare-except, no-syspath-insert, no-duplicate-class-names), with a documented
  ALLOWLIST for known debt (fast_cache R3, SessionRecovery dup). Runs green (exit 0).
- Core cleanups to pass green: removed vestigial `import redis`/`REDIS_AVAILABLE`
  from both coordinators; `SignalType` now defined once (facade imports it);
  narrowed session_recovery's 2 bare excepts.
- TODO when the repo is under git: wire `check_boundaries.py` into a pre-commit
  hook / CI (currently run manually: `py scripts/check_boundaries.py`).

### Wave 1 — Make the existing surface honest + robust (quick wins)
*Consumes: codebase-audit + ACI.* Low risk, high value.
- bootstrap truth-fix (dead `_archive` imports → real ones; stale Redis namespaces
  → `learn:`/`mem:`).
- bare-except sweep at boundaries, through the ACI lens (errors must *teach*).
  Start `fast_cache.py`, `bootstrap.py`, the agent-facing API.

### Wave 2 — Context pillar (System 4), reusing project_context.py
*Consumes: context-pillar-plan + memory retrieval research.* Biggest single
payoff; absorbs audit #3.
- Phase 1: consolidate `project_context.py` → `context/` onto Store (the Phase A
  playbook; fixes the Redis-down hard-fail).
- Loaders → **Ranker (shared primitive)** → **Distiller/summarizer (shared)** →
  aggregator/quality_scorer to the 8–10k token budget.

### Wave 3 — AgentMemory depth (Phases B–E), sharing Wave 2's primitives
*Consumes: learning-memory analysis + plan.* Build at the seam with Wave 2.
- Phase B: temporal + **supersession (shared)** — prerequisite for the ranker.
- Phase C: retrieval via the shared **Ranker**.
- Phase D: consolidation→`chronicles/` via the shared **Distiller** (+ Reflexion
  guardrails: confidence, provenance, retirable, writer→critic gate).
- Phase E: multi-agent scoping (per-agent vs shared).

### Wave 4 — Unify the Agent Interface (System 5 / ACI)
*Consumes: agent-interface-aci.* Depends on Wave 2 (context is the "know" surface).
- One front door (MCP) over the tiny verb set; descriptions-as-prompts;
  progressive disclosure via `get_bootstrap_info`; wire in the Context pillar.
- (Errors-teach already done in Wave 1.)

### Wave 5 — Hygiene (parallel / opportunistic, boy-scout)
*Consumes: cleanup-at-scale research.* Independent of the feature spine.
- services/ triage (keep infra-ops, merge redis_sync→reconciler, retire
  self-deprecated session_monitor); root module dedup; `sys.path` removal via an
  AST codemod; stale-docs triage.

**Dependency spine:** Wave 0 enables all → Waves 2 & 3 share primitives (build
them at the seam, not twice) → Wave 4 needs Wave 2 → Wave 5 runs alongside.

## What analysis would best steer us

Two analyses are worth doing *before/within* the build, because they de-risk the
most and prevent wasted work:

1. **Shared-primitives extraction (do before Wave 2/3).** A focused design pass
   that specifies the Ranker, Distiller, and Supersession interfaces *once*, so
   memory and context both consume them. Without this we build the ranker twice.
   This is the highest-leverage analysis.
2. **Agent-in-the-loop evaluation harness (the north-star metric).** The only
   analysis that answers "is the system actually succeeding for agents?": can a
   fresh agent accomplish a representative task using only the interface + context,
   no docs? Borrow ACI metrics — task success, tool-selection accuracy, tokens per
   task, error/retry rate. Build a `test_bootstrap_api_no_docs`-style baseline test. Run it
   as a baseline now, then after each wave to see if we're improving the thing that
   matters.

Supporting analyses (lighter): a **Mikado dependency map** for Wave 2's
project_context consolidation (leaf-first, no unraveling); a **token-budget audit**
(where do tokens actually go — context assembly, tool schemas, returns?) since
token efficiency is the whole point; and **characterization tests** capturing
current behavior before Wave 2/3 to prove no regression.

## Progress
- Wave 0 ✅ (LEXICON + guardrails). Bootstrap truth-fix ✅ (.py + .md).
- Shared-primitives analysis ✅ (`docs/shared-primitives-and-coherence.md`) + interface
  spec ✅ (`docs/shared-primitives-spec.md`): Supersession → Ranker → Distiller.
- B1 Redis port single-source-of-truth ✅ (foundation defers to config).
- COMPLETE lexicon-adherence review ✅ (`docs/lexicon-adherence-review.md`, all 56 modules).
- Logging: `session_log.py` retired (3→2); `agent_logger` fate pending decision.
- **Context pillar Phase 1 ✅ COMPLETE 2026-06-20:** `project_context` migrated off
  raw Redis onto a `Store` (Redis-down hard-fail fixed); relocated to
  `context/project_context.py` (+ deprecated root shim, bootstrap repointed,
  `context/__init__` exports it); 17 dead guards removed; docstring/`import redis`
  delying. Singleton integrity verified across all import paths. bootstrap's
  project-context check now passes with Redis down. First real brick of System 4.
- **Ranker shared primitive ✅ 2026-06-20:** `core/primitives/ranker.py` — relevance ×
  importance × recency + relationship-type weighting, supersession-aware (excludes
  `superseded`), keyword relevance with an embeddings seam (`relevance_fn`),
  transparent component breakdown. 8 tests pass; guardrails green. New `core/primitives/`
  package (shared algorithms; foundation=persistence, primitives=algorithms).
- **Context pillar loaders + aggregator ✅ 2026-06-20:** `context/learning_loader`,
  `decision_loader`, `blocker_loader`, `briefing_loader` (thin readers over
  LearningStore/AgentMemory/project_context/AgentSignalLedger, ranked via the shared
  Ranker, every entry carrying a `source` pointer); `context/aggregator.assemble_context`
  assembles all sections into one budget-fitted block (rank + trim; Distiller
  compression is Wave 3). Demoed end-to-end on real + seeded data. Found & fixed a
  real bug: project_context's IDs were second-resolution → collisions (now `_gen_id`
  + random suffix). 11 test suites green. `context/` package exports the pillar API.
- **Context pillar WIRED INTO AGENT STARTUP ✅ 2026-06-20 — THE LOOP IS CLOSED:**
  `agent/initializer.derive_agent_context_from_startup_sources` now assembles the
  agent's context via `context.aggregator.assemble_context` (layering-correct: agent/
  is the top layer, may import System 4; `coordinator_api` is NOT changed — that
  would be an inversion). `coordinator_api.initialize` called with `load_context=False`
  → the old `agent_briefing_loader` path is off the primary route (retire-candidate).
  Verified: a real agent boots, gets its 8 most-relevant learnings for a task within
  budget, api ready to emit. Also fixed: B1 straggler (initializer redis defaults →
  config) AND a perf bug the wiring exposed — every component re-probed Redis on
  construct (~20s startup when down). Two-part fix: (a) per-(host,port) reachability
  cache in redis_connection (probe once per startup, 5s TTL); (b) split the probe
  timeout (0.5s, fast liveness) from the client socket timeout (2s, for real ops).
  Result: **20s → 4.2s → 1.25s** (Redis-down worst case; instant when Redis is up).
  9 suites green.
- **Distiller primitive + skeleton ✅ 2026-06-20:** `core/primitives/distiller.py` —
  compacts ranked items to a token budget with a writer→critic gate, MD skeleton
  output, and the lossy-summary + **lossless source pointer** rule (dropped items
  recoverable via their pointers); heuristic writer ships now, LLM writer/critic is
  an injectable seam. Wired into `assemble_context`: it now emits a compact
  `skeleton` (one line + source per item — the "shape" an agent reads) alongside the
  structured `sections` (drill-down) = progressive disclosure. All 3 shared
  primitives now exist (Ranker, Distiller; Supersession is the latent data-convention
  the Ranker already honors). 10 suites green.
- **agent_briefing_loader RETIRED ✅ 2026-06-20** — deleted; coordinator_api's
  load-context branch removed (it shouldn't load context — layering); `load_context`
  is now a deprecated no-op; test_fixes_quick repointed to context.briefing_loader.
- **AgentMemory Phase B — Supersession ACTIVE ✅ 2026-06-20:** built
  `core/primitives/supersession.py` (is_active/mark/retire/active_only); `decide()`
  and `record()` take `supersedes=<old_id>` → retire the old record; `get_decisions`/
  `get_similar` exclude superseded; the Ranker now delegates its active-check to the
  Supersession primitive (single source). Memory has temporal correctness — stale
  facts stop surfacing everywhere (memory reads AND the Context pillar). 7 suites green.
- **AgentMemory Phase D — consolidation→chronicle ✅ 2026-06-20:**
  `core/learning/consolidation.py::consolidate_memory_into_chronicle` distills raw
  experiences + reflections (via Ranker + Distiller) into a generated
  `chronicles/lessons.md` — each lesson carries a `source` pointer (lossy+lossless),
  raw memory is READ-ONLY (never deleted), empty-graceful. Added
  `AgentMemory.load_all_experiences`. The episodic→semantic loop is live: memory now
  distills itself into the curated chronicle layer. 3 suites green + guardrails.
  Next: embeddings (swap Ranker.relevance_fn); Phase E (multi-agent scoping); decide
  fate of the static chronicles/*.json (adrs/failures/milestones) vs generated lessons.md.
  (Optional: IPv4-first probe.)
- **Robustness suite ✅ 2026-06-20 (`tests/test_robustness.py`):** deeper testing
  beyond single-pass units — model-based Store fuzz (1500 random ops vs a reference
  model), cross-backend equivalence (FileStore==HybridStore-down over random ops),
  Ranker/Distiller property invariants (hundreds of rounds), corruption resilience,
  backward-compat record loading, concurrency (parallel writes, no lost updates).
  It found a real bug on first run: the Distiller included source-LESS items as
  `(source: None)` — fixed to SKIP them (lossless-pointer rule) + report
  `skipped_no_source`. 14 maintained suites green; 5 LEGACY tests still red from
  stale pre-consolidation imports (agent_init/coordinator_api/learning_store +
  unicode) — repoint-or-retire is a pending cleanup.
- **Known testing gaps (honest):** the LIVE Redis path is never exercised (down in
  dev → RedisStore/RedisLedger live tests SKIP); no mutation testing; no failure-
  injection for Redis flapping mid-op.

## Recommended next move — time to BUILD (design gates are cleared)
The design is mapped; the risk now is over-planning. Two ready build targets:
- **Wave 1 remainder** (low risk): bare-except sweep at the agent boundary
  through the ACI "errors teach" lens (bootstrap already done).
- **Wave 2 start** (high payoff): Context pillar Phase 1 — consolidate
  `project_context.py` onto Store (fixes its Redis-down hard-fail + B2), then
  build Supersession → Ranker → Distiller per the spec as the pillar needs them.
