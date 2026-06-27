# LEXICON — the ubiquitous language of E:\AI-Setup

One authoritative definition per term. We use these words the same way in
conversation and in code (Domain-Driven Design "ubiquitous language") so there's
no translation layer. When you reach for a name, reach for one of these.

## Naming rules

- **State vs. Events.** Recording a fact you'll look up later → it's *state* (goes
  in a **Store**). Announcing something that happened, in order → it's an *event*
  (goes in a **Ledger**). If you can't tell which, ask "am I storing what *is*, or
  what *happened*?"
- **Genus, not species.** Name a container after the *genus* of what it holds,
  never one *species*. The six signal types (action/decision/blocker/handoff/
  completion/learning) are species; `signal` is the genus → `AgentSignalLedger`,
  never `decision_log`.
- **Generic primitive, specific use.** The reusable primitive stays generic
  (`Ledger`); the specific use names the variable (`signal_ledger`). We can have
  other ledgers.
- **Names must not lie.** A name must match what the thing does. If behavior and
  name disagree, one of them changes (we renamed `Bus`→`Ledger` for this reason;
  we normalized `success: "True"`→`"yes"`).
- **Intention-revealing, precision over brevity.** `append_signal`, not `add`;
  `derive_full_context_for_agent_repriming`, not `get_ctx`.
- **Backward-compat aliases are deprecated, not equal.** A terse old name may alias
  the canonical one, marked "Deprecated: use X".

## Persistence (System 0 — foundation, `core/foundation/`)

- **Store** — persistence of *state by key*: "what IS the value of X?" Mirrors the
  Redis command surface we use (key/value, hash, list, set, sorted-set, TTL,
  ltrim, key-scan). Backends: `RedisStore`, `FileStore`, `HybridStore`; factory
  `create_store`.
- **Ledger** — persistence of *events in sequence*: "what HAPPENED, in order?"
  Append-and-replay by cursor (`emit` / `consume`). NOT a real-time message bus
  (nothing is pushed). Backends: `RedisLedger`, `FileLedger`, `HybridLedger`;
  factory `create_ledger`.
- **Hybrid (Store/Ledger)** — the default backend: writes File-always +
  Redis-best-effort, reads Redis-first with File fallback. Degrades gracefully
  (no 48s hang) and never loses durability.
- **fail-fast connector** — `connect_to_redis_with_fail_fast`: the ONLY sanctioned
  way to reach Redis. Probes reachability first so a down Redis fails in ~seconds,
  not ~48s. (Enforced by `scripts/check_boundaries.py`.)
- **StoreReconciler** — heals divergence between a HybridStore's Redis and File
  backends (backfills Redis from the durable File on cold-start).
  `sync_state_reconciling_divergence()`.

## Domain (Systems 1–3, `core/`)

- **AgentSignalLedger** — THE specific ledger this system runs on: every signal an
  agent emits, recorded in order. Owns the signal layout (canonical `agent:events`
  firehose + per-agent streams + retention). `append_signal` / `replay_signals`.
- **signal** — the genus for what agents emit. Species: `action`, `decision`,
  `blocker`, `handoff`, `completion`, `learning` (+ `insight`, `context`).
- **SignalEmitter** — the agent-facing API for emitting signals
  (`emit_decision_referenced_by_agents`, etc.). Single source of truth for
  `SignalType`.
- **CoordinatorService** — replays the firehose and reacts: caches decisions,
  builds briefings, escalates blockers, routes learnings.
- **LearningStore** — experiment-outcome learnings (the `learn:` namespace).
  Success vocabulary is canonical `{yes, partial, no}`; keyed by `experiment_name`.
- **AgentMemory** — the richer multi-type memory (the `mem:` namespace): decisions
  (semantic), experiences (episodic), reflections (Reflexion), approaches
  (procedural). Persists through a Store. Distinct from `LearningStore`.

## Context & interface (Systems 4–5)

- **Context pillar (System 4)** — assembles 8–10k tokens of ranked, relevant
  context so an agent starts informed ("what the agent KNOWS"). Lives in
  `context/` (planned; consolidates `project_context.py`).
- **Agent Interface / ACI (System 5)** — the small, coherent verb surface agents
  use to act ("what the agent DOES"). Tool descriptions are prompts; errors teach.

## Cross-cutting concepts

- **chronicle** — RESERVED for the *curated highlights* layer (`chronicles/`:
  decisions, failures, milestones) *derived from* the raw ledger. Do NOT name the
  raw event log "chronicle". Raw ledger → distilled chronicle.
- **Ranker** (planned shared primitive) — scores items by relevance × importance ×
  recency, plus relationship-type weighting. Used by both the Context pillar and
  AgentMemory.
- **Distiller** (planned shared primitive) — writer→critic summarization to a token
  budget. Used by both the Context summarizer and the consolidation→chronicle loop.
- **relationship type** — one of 66 standardized relations (Dublin Core / OBO /
  RDF) in `core/foundation/relationship_types.py`; the vocabulary semantic method
  names are built from (`derived_from`, `prevents`, `supersedes`, …).

## Layers (who may depend on whom)

`System 0 (foundation)` ← `1–3 (domain)` ← `4 (context)` ← `5 (interface)`.
Lower layers never import higher ones. Agents touch only the top (System 5);
`Store`/`Ledger`/`AgentMemory` internals are never agent-facing tools.

## Knowledge layers (one source of truth, three views)

Harmonized 2026-06-20 (see `docs/knowledge-harmonization-plan.md`):

1. **Raw / archival** — `session_logs/learnings.jsonl` + Ledger streams. The deepest,
   richest record. Append-only; never mutated or deleted.
2. **Canonical state** — the `Store` (`learn:*` / `mem:*` / `proj:*`), mirrored across
   Redis (16379 db 0) and `session_logs/store_state.json`. Each record holds a lossy
   summary **plus** a `source` pointer (and `detail_json`) back to the raw line.
3. **Derived / curated** — `chronicles/`: generated `lessons.md` (Distiller output,
   regenerated, never hand-edited) and legacy curated `*.json` (milestones/failures/adrs).

Rule: raw is sacred; the Store summarizes-with-pointer; chronicles are regenerated from
the Store. Never hand-edit a derived view as if it were a source.

## Redis topology & test isolation

- **Canonical endpoint** = `config.REDIS_PORT` (16379, the Docker master). The 6379/6380
  WSL pair is a separate, inactive HA-server concern (`services/redis_ha_manager.py`).
- **Tests NEVER touch canonical.** They run on `config.REDIS_TEST_DB` (15) + a temp
  `AI_SETUP` file dir. Use `tests/isolate_canonical.py` (import first) for default-store
  tests, or `tests/redis_test_helpers.py` for explicit live-Redis stores/ledgers.
  Invariant: a full test run must leave canonical db 0 unchanged.
