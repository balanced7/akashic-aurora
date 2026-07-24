---
akashic_id: art_20260709_knowledge-store-harmonization-plan-2026_9e9656
akashic_sha: f4262eac1515
status: fossil
type: design
date: 2026-07-09
title: Knowledge-Store Harmonization Plan (2026-06-20)
gist: "> **STATUS: EXECUTED ✅ 2026-06-20.** All phases done. Canonical = Redis **16379 db0** > + `session_logs/store_state.json`, holding exactly t"
tenant: solo
visibility: fleet
seats: []
category: [substrate, library, memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260627_lessons-auto-generated-from-the-learning_6dd9bf
    rel: cites
created: "2026-07-09T23:27:59"
updated: "2026-07-23T21:42:05"
---
<!-- GENERATED PROJECTION of art_20260709_knowledge-store-harmonization-plan-2026_9e9656 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Knowledge-Store Harmonization Plan (2026-06-20)

> **STATUS: EXECUTED ✅ 2026-06-20.** All phases done. Canonical = Redis **16379 db0**
> + `session_logs/store_state.json`, holding exactly the **6 real lessons** (rich:
> summary + `source` pointer + full `detail_json`), backends byte-consistent. Test
> junk quarantined to `session_logs/quarantine_test_data.jsonl` (+ full snapshot in
> `backups/knowledge_2026-06-20/`). `learnings.jsonl` trimmed to the 6 (original in
> backup). `chronicles/lessons.md` generated; static chronicles kept. Topology set in
> `config.py` (16379). **Test isolation** (`tests/isolate_canonical.py` + `db=15` +
> `tests/redis_test_helpers.py`) proven: full suite run twice leaves canonical db0 at
> 15 keys. Script: `scripts/harmonize_knowledge.py` (backup / rebuild / verify).
> Bonus bugs found & fixed: endpoint resolver ignored a lone `REDIS_PORT`; a flaky
> blocker test (Redis-backed state accumulated across runs in the shared test DB).



Goal: **one coherent, consistent knowledge layer with zero history lost.** Today the
same knowledge lives in several places that disagree, real lessons are tangled with
test junk, and the richest copy of our best learnings is the one we *don't* serve.
This plan inventories every store, defines the target model, and sequences the
cleanup so nothing is deleted — only *quarantined* — until you approve.

---

## 1. Inventory — what exists today

| Store | Location | Contents | State |
|---|---|---|---|
| **Raw learnings (archival)** | `session_logs/learnings.jsonl` | 11 lines: **6 real** `semantic_refactor_research` lessons + 5 test (test_learning_1, test_sync_learning_v1, 3× verify_exp) | **RICHEST** — has `key_insights`, `patterns_discovered`, `files_affected`, `implementation`, `progress` |
| **Canonical Store (file)** | `session_logs/store_state.json` | `learn:*` (9 unique exp) + `blockers:escalated` (14 test entries) | **FLATTENED** — lost the rich fields; indexes have duplicates |
| **Canonical Store (Redis)** | Redis `16379`, db0 | mirror of `learn:*` + `recon_facade_exp` + `agent:events`/`agent:recon_test_agent:events` streams (this session) | **DIVERGES** from file (e.g. `learn:experiments:all` = 12 in Redis vs 18 in file) |
| **AgentMemory** (`mem:`) | Store | — | **EMPTY** (Phase A/B built, no data) |
| **project_context** (`proj:`) | Store | — | **EMPTY** (built, unused) |
| **Static chronicles** | `chronicles/*.json` | adrs (3, mostly "Use Redis" dups), failures (1 real), milestones (real: Gemma Voice AI, backups), tag_vocabulary | **LEGACY curated** (April); genuine history in milestones/failures |
| **Generated chronicle** | `chronicles/lessons.md` | — | **NOT YET GENERATED** (consolidation built Phase D) |
| **Raw session logs** | `sessions/`, `backup_wsl_migration/`, `agent_verify_agent2_*.jsonl` | conversation transcripts | out of scope (not a knowledge store) — leave |

### The 6 real lessons (the only knowledge to keep live)
All `agent_id=semantic_refactor_research`, 2026-06-17, the big naming-refactor effort:
1. `relationship_types_framework_design` — 66 relationship types (Dublin Core/OBO/RDF/OWL)
2. `semantic_naming_readability_impact` — 160+ fns renamed, 60% faster comprehension
3. `semantic_naming_pattern_discovery` — the 5 naming patterns (load/cache/record/emit/derive)
4. `backward_compatibility_refactoring_strategy` — deprecated-alias strategy, 0 breaks
5. `semantic_refactoring_progress_analysis` — 160+ methods / 26h / 100% compat
6. `semantic_documentation_update_strategy` — semantic-style docs

### The junk (test artifacts — quarantine, don't delete)
- Learnings: `test_learning_1` (test_agent_6), `test_sync_learning_v1` (test_agent_2),
  `verify_exp` ×3 (verify_agent2), `recon_facade_exp` (recon_test_agent, this session)
- `blockers:escalated` — 14 entries from test_agent_1/test_agent_3 (a blocker test)
- Redis streams `agent:events`, `agent:recon_test_agent:events` (this session's facade test)

---

## 2. Problems found

1. **Test data is interleaved with real knowledge** in both the file Store and Redis.
2. **Lossy storage**: the 6 real lessons lost their deep fields (insights, patterns,
   files) when imported JSONL→Store. The JSONL still has them; the Store we *serve* doesn't.
3. **Backends disagree**: `learn:experiments:all` and `learn:agent:*` indexes have
   duplicates and differ between file and Redis — they were never reconciled cleanly.
4. **Redis topology split-brain**: data lives on **16379** (Docker, running), but
   `config.py` declares **6380** the master and `redis_ha_manager.py` says **6379**.
   The foundation defaults to 6380 (down) → it can't even see its own data by default.
5. **Tests pollute the real store**: they share Redis db0 and don't all clean up — this
   is how `recon_facade_exp` + the streams got written to your live Redis today.
6. **"Chronicle" is overloaded**: static `chronicles/*.json` (curated April) vs the
   generated `chronicles/lessons.md` (Distiller) vs the raw learnings — no stated layering.

---

## 3. Target model — one source of truth, three layers

Per our own architecture (State-vs-Events; lossy summary + lossless pointer; CoALA
episodic→semantic; chronicle = curated *derived* view):

```
RAW (append-only, archival)      session_logs/learnings.jsonl  +  Ledger streams
        │  (never deleted — the deepest, richest record)
        ▼
CANONICAL STATE (working set)    the Store:  learn:*  (live lessons)  /  mem:*  /  proj:*
        │  each record carries a `source` pointer back to its raw JSONL line
        ▼
DERIVED / CURATED (for reading)  chronicles/lessons.md (generated by Distiller)
                                 chronicles/*.json (legacy curated history — milestones/failures)
```

Rules: raw is never mutated/deleted; the Store holds the *summary + pointer* (lossy+lossless);
chronicles are regenerated from the Store, never hand-edited as a source.

---

## 4. Execution plan (phased; nothing destructive until Phase 3, and only after a backup)

**Phase 0 — Safety net (no changes to live data).**
- Snapshot everything first: copy `session_logs/store_state.json`, dump Redis 16379
  (`--rdb` or a JSON export), copy `chronicles/` → `backups/knowledge_2026-06-20/`.
- Append the to-be-quarantined test records to `session_logs/quarantine_test_data.jsonl`
  (so they're preserved verbatim outside the live store before any removal).

**Phase 1 — Resolve Redis topology (your decision).**
- Pick the canonical endpoint. Recommend **16379** (it's running and holds the data) →
  set `config.py REDIS_PORT=16379` as the single authority; reconcile `redis_ha_manager`
  /6379/6380 references or document them as the (separate) HA-server concern.
- After this, the foundation's default endpoint == where the data actually is.

**Phase 2 — Test isolation (root-cause fix, so this never recurs).**
- Add `REDIS_DB` support (default 0; tests set `REDIS_DB=15`) OR a `TEST_REDIS_PORT`
  convention, so live-Redis tests run in a sandboxed logical DB and can `FLUSHDB`
  their own space. Update the 3 live-path tests + robustness suite to use it.
- Guardrail: tests must never write to db0 of the canonical endpoint.

**Phase 3 — Quarantine the junk (after Phase 0 backup).**
- Remove from the live Store + Redis: the 5 test learnings, `recon_facade_exp`,
  `blockers:escalated`, and the 2 test streams. (Already preserved in Phase 0.)
- Leave ONLY the 6 real lessons live.

**Phase 4 — Re-import the 6 lessons *richly* (lossy + lossless).**
- Re-import the 6 from `learnings.jsonl` so each Store record keeps a compact summary
  **plus** a `source` pointer (jsonl line / hash) to the full rich record. Deep fields
  (key_insights, patterns_discovered, files_affected…) stay recoverable from the raw line.
- Rebuild ALL indexes (`learn:experiments:all`, `learn:agent:*`, `learn:category:*`,
  `learn:experiments:success`) from the canonical hashes — deduped, consistent.

**Phase 5 — Reconcile backends once, cleanly.**
- With topology fixed and junk gone, run the reconciler once so file Store and Redis
  are byte-for-byte consistent. Verify equality (cross-backend check, like the
  robustness suite does).

**Phase 6 — Define the chronicle layer.**
- Generate `chronicles/lessons.md` from the 6 lessons via `consolidation`.
- Keep `chronicles/{milestones,failures}.json` as "legacy curated history"; drop or
  fold the trivial `adrs.json` "Use Redis" duplicates. Document the 3-layer model in LEXICON.

**Phase 7 — Verify + record.**
- Re-run the full suite (now incl. live-Redis on the sandbox db) + guardrails.
- Update ROADMAP + memory with the harmonized model.

---

## 5. Decisions I need from you
1. **Redis topology**: make **16379** canonical (recommended), or do you want the
   long-term master to be 6379/6380 (then I migrate the data there)?
2. **Confirm quarantine-not-delete**: test data is archived to a jsonl, then removed
   from the live store. OK?
3. **Static `adrs.json`**: the 3 entries are 2 duplicate "Use Redis" + 1 stub — drop
   them, or keep as historical record?
