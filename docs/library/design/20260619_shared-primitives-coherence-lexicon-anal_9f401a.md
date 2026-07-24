---
akashic_id: art_20260619_shared-primitives-coherence-lexicon-anal_9f401a
akashic_sha: 50d32d0bd1d3
status: fossil
type: design
date: 2026-06-19
title: Shared primitives + coherence/lexicon analysis
gist: "Date: 2026-06-19. Read-only. Two passes over the active code: (A) what shared primitives should exist — both duplication we've *already* bui"
tenant: solo
visibility: fleet
seats: []
category: [performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260619_shared-primitives-coherence-lexicon-anal_9f401a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Shared primitives + coherence/lexicon analysis

Date: 2026-06-19. Read-only. Two passes over the active code: (A) what shared
primitives should exist — both duplication we've *already* built and the pieces
the next features will need; (B) coherence + adherence to `docs/LEXICON.md`.
Discipline: surface candidates, extract only under the **rule of three** ("a wrong
abstraction costs more than duplication").

---

## Part A — Shared primitives

### A1. Existing duplication (built code)

- **`IndexedRecords` on a Store — EXTRACT (rule of three is met).**
  `LearningStore` and `AgentMemory` both implement the *same* shape: store each
  record in a hash (`hset records id json`), index its id in a list/sorted-set,
  and read by scanning the index and hydrating each record (`lrange/zrange` →
  `hget` → `json.loads`). Confirmed: 22 index/hydrate ops across the two. The
  Context pillar (Wave 2) will be the *third* user (it stores ranked records too).
  → Extract a small `IndexedRecords` / `RecordCollection` helper on `Store`
  (put record, index by key, query/hydrate, cap). Both stores shrink; future
  stores reuse it. This is the highest-value extraction.

- **Module-singleton accessor — STANDARDIZE, don't extract (low value).**
  Six modules hand-roll `_instance` global + `get_X_instance()` (fast_cache,
  learning_store, agent_memory, coordinator_api, coordinator_service,
  redis_sync_coordinator). It's a trivial 4-line pattern; a shared helper would be
  over-abstraction. Keep the *shape* consistent (same naming, same lazy-init); no
  extraction.

- **`_gen_id` + dataclass→json — leave.** Minor, stable, not worth a primitive.

### A2. Planned shared primitives (spec once, before Waves 2–3)

Each is needed in two places and embodies a specific research finding:

| Primitive | Used by | Embodies | Build order |
|-----------|---------|----------|-------------|
| **Supersession** — a newer fact retires an older one | AgentMemory Phase B; the Ranker | temporal correctness (Zep) | 1st (others depend on it) |
| **Ranker** — score by relevance × importance × recency + relationship-type | Context pillar; AgentMemory retrieval | Generative Agents retrieval | 2nd (needs Supersession) |
| **Distiller** — writer→critic summarize to a token budget | Context summarizer; consolidation→`chronicles/` | Mem0 consolidation w/ critic | 3rd |

Spec each interface (inputs/outputs/contract) once in a small design doc so both
consumers plug into the same implementation.

---

## Part B — Coherence & lexicon adherence

### B1. Redis port split-brain — HIGH (latent correctness bug)
`config.py` sets `REDIS_PORT = 6380` ("WSL master; 6379 is a read-only replica"),
and `project_context.py` connects there. But the **new foundation factories
hardcode `port=6379`** (`create_store`, `create_ledger`, `AgentSignalLedger`,
the coordinators). So when Redis is actually up, the new foundation and the older
modules talk to **different Redis instances** — and the foundation may be writing
to a *read-only replica*. It's masked today only because both are down in dev and
everything uses the File fallback. There is **no single source of truth for "where
Redis is."**
→ Fix: the foundation factories should read host/port from `config` (one
authority), not hardcode them. Small change, prevents a nasty "works in dev,
splits in prod" failure. (Ties to the old `redis_architecture_audit` memory.)

### B2. Outer shell uses the connector but not the abstraction — MEDIUM
Root modules (`project_context`, `agent_logger`, `fast_agent_comm`,
`session_logger`) adopted `connect_to_redis_with_fail_fast` (good — no 48s hangs)
but still hand-roll raw Redis keys instead of persisting through `Store`/`Ledger`.
They're on the foundation's doorstep, not through the door. → Migrate onto
`Store`/`Ledger` as each is touched (`project_context` is first, in Context pillar
Wave 1; it also fixes its Redis-down hard-fail).

### B3. Lexicon naming adherence — mostly good
- `project_context.py` already uses exemplary semantic naming
  (`derive_full_context_for_agent_repriming`, `record_blocker_preventing_task`) —
  strong, lexicon-aligned.
- `fast_agent_comm.py` uses its own messaging vocabulary (stream/message/priority)
  — appropriate, it's the real-time messaging-bus domain (distinct from `Ledger`).
- `agent_logger.py` / `session_logger.py` — overlap in concept (logging/session)
  and haven't been checked against the lexicon; part of the root-module dedup
  (audit S2). Worth a naming pass when consolidated.
- Known tracked debt (allowlisted in `check_boundaries.py`): the `SessionRecovery`
  duplicate (session_recovery.py vs session_state.py:350) and `fast_cache.py`
  (redis/ sys.path/ bare-excepts, audit R3).

---

## Recommended sequencing
1. **Fix the Redis port authority (B1)** — small, high-value correctness fix; have
   the factories read `config`. Do this soon; it's a silent trap.
2. **Spec the planned primitives (A2)** — Supersession → Ranker → Distiller — before
   Waves 2–3.
3. **Extract `IndexedRecords` (A1)** as part of Context pillar Wave 1 (it becomes the
   third user, so the abstraction is earned, not premature).
4. Migrate the outer shell onto Store/Ledger opportunistically (B2), starting with
   `project_context` in the Context pillar.

Nothing changed here — this is the map. The one item I'd not let sit is **B1**:
it's the kind of latent split that feels fine until Redis comes up and quietly
splits your data.
