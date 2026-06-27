# Lexicon & naming-schema adherence review (COMPLETE)

Date: 2026-06-20. Exhaustive pass — **every active module** (56 modules + 12 test
files) checked against all `docs/LEXICON.md` rules: State-vs-Events,
genus-not-species, names-must-not-lie, intention-revealing (precision over
brevity), generic-primitive/specific-use, deprecated-alias convention, lexicon
vocabulary, and layering. Excludes only frozen/vendored trees (`_archive`, `temp`,
`backup_wsl_migration`, `dockerized-ai`, `ComfyUI-Zluda`, `gemma_realtime`,
`models`, `rocm-lib`). Nothing skipped.

Legend: ✅ strong · ◐ acceptable (notes) · ⚠ has a real naming issue.

## Full scorecard — by area

### core/foundation/
| Module | | Notes |
|--------|--|-------|
| `store.py` | ✅ | lexicon source; State primitive; semantic + deprecated aliases |
| `ledger.py` | ✅ | Events primitive; genus/species exemplar |
| `redis_connection.py` | ✅ | fail-fast connector; single endpoint authority |
| `relationship_types.py` | ✅ | the vocabulary itself; clean enum + `get_relationship_by_name` |
| `fast_cache.py` | ⚠ | semantic primaries (`load_value_from_cache_hierarchy`) BUT lying aliases: `redis_get/redis_set/redis_hget` actually do multi-layer (RAM→Redis→dict), not just Redis. Aliases unmarked (not "deprecated"). Plus known debt (11 bare excepts, direct redis, sys.path — allowlisted) |

### core/learning/, core/signals/, core/state/
| Module | | Notes |
|--------|--|-------|
| `learning_store.py` | ✅ | semantic + deprecated aliases; `learn:` namespace |
| `agent_memory.py` | ✅ | CoALA-aligned; `mem:` namespace |
| `agent_signal_ledger.py` | ✅ | genus/species exemplar (`append_signal`/`replay_signals`) |
| `coordinator_api.py` | ✅ | `SignalEmitter`, semantic verbs + deprecated aliases |
| `coordinator_service.py` | ✅ | semantic + aliases |
| `redis_sync_coordinator.py` | ✅ | deprecated facade, clearly labeled |
| `sync_reconciler.py` | ✅ | `StoreReconciler`, intention-revealing |
| `session_state.py` | ◐ | good semantic names + aliases; defines a `SessionRecovery` (see ⚠ dup below) |
| `session_recovery.py` | ◐ | clean; the canonical `SessionRecovery` (package exports this one) |

### agent/, infrastructure/, context/, scripts/
| Module | | Notes |
|--------|--|-------|
| `agent/initializer.py` | ◐ | `derive_agent_context_from_startup_sources` is exemplary; but 6 init functions — alias sprawl, mark/trim |
| `infrastructure/health_check.py` | ◐ | semantic + deprecated aliases, BUT file `health_check` vs class `StartupDiagnostics` vs fn `check_infrastructure_health` — "health" vs "diagnostics" split |
| `context/__init__.py` | ✅ | stub for System 4; lexicon-aligned planned names |
| `scripts/check_boundaries.py` | ✅ | semantic, guardrail rules named clearly |

### root modules
| Module | | Notes |
|--------|--|-------|
| `bootstrap.py` / `bootstrap.md` | ✅ | rebuilt 2026-06-19; speaks the lexicon |
| `config.py` | ◐ | SSOT; standard CONST naming + `get_redis_config`. The `REDIS_PORT=6380` vs `redis_ha_manager` 6379 contradiction is a topology question, not naming |
| `project_context.py` | ✅ | exemplary semantic naming (`derive_full_context_for_agent_repriming`, `record_blocker_preventing_task`) + aliases. (Redis-only — a Store-migration item, not naming) |
| `fast_agent_comm.py` | ✅ | own messaging vocab (stream/message/priority) — appropriate; distinct from Ledger |
| `agent_briefing_loader.py` | ◐ | clean names; overlaps the Context pillar (precursor → fold into System 4) |
| `agent_logger.py` | ⚠ | logging-dup + a distinct patch/changelog feature in one class; two vocabularies (`action`/`decision` vs `feat`/`fix`/`patch`). Pending decision (checkpoint-patch-tracking) |
| `session_logger.py` | ⚠ | canonical logger, BUT reinvents the Ledger (raw `rpush`+file; ignores config's `session:events` stream). Rebase onto Ledger |
| `session_compressor.py` / `session_summarizer.py` | ◐ | two names for near-identical "summarize session" (`summarize_with_gemma` in both) → Distiller precursors; consolidate when Distiller lands |
| `session_log.py` | ✅ retired | was a pure duplicate; deleted 2026-06-19 |

### services/ (standalone infra-ops daemons)
| Module | | Notes |
|--------|--|-------|
| `redis_manager.py` | ◐ | clear infra verbs (`create_backup`, `restore_redis`, `verify_backup_integrity`). BUT 1072-line god-module; has its OWN `log()`/`LogLevel` (another logger) and `check_health` (another health impl) |
| `redis_ha_manager.py` | ◐ | clear (`get_current_master_from_sentinel`, `wait_for_failover`). Declares master=6379 (contradicts config) |
| `redis_sync.py` | ◐ | `RedisSyncPoller`/`SyncRunner` clear; but the concept overlaps `StoreReconciler`+`HybridStore` |
| `port_manager.py` | ⚠ | clear, BUT `PortManager` duplicates `stack_manager/ports.py:PortManager` |
| `background_monitor.py` | ◐ | `WindowsNotifier`/`MessageInbox`/`BackgroundMonitor` clear; `MessageInbox` overlaps `fast_agent_comm` messaging |
| `session_monitor.py` | ◐ | clear, but self-deprecates in its docstring ("prefer ai_watchdog.py"); overlaps session logging |

### stack_manager/ (CLI orchestration subsystem)
| Module | | Notes |
|--------|--|-------|
| `cli.py` | ◐ | consistent `cmd_*` CLI convention; terse helpers `_c`/`_log` (ok for a CLI) |
| `launcher.py`/`health.py`/`memory.py`/`resources.py` | ⚠ | each re-implements `_run_wsl`/`_run_powershell`/`_run_cmd` (6 copies) — internal duplication; extract a `_shell` helper |
| `ports.py` | ⚠ | `PortManager` duplicates `services/port_manager.py` |
| `memory.py`/`ports.py`/`routing.py` | ◐ | each re-defines a private `_redis()` — duplication; clear class names (`MemoryMonitor`/`RoutingTable`/`ResourceTracker`) |
| `dag.py`/`config.py`/`redis_util.py` | ◐ | terse (`resolve_tiers`, `_win`, `get_master_redis`) but clear in context |

### mcp_servers/, tests/
| Module | | Notes |
|--------|--|-------|
| `agent_comm/server.py` | ✅ | clean agent-facing verbs (`send_message`, `declare_operation`, `search_messages`) — good ACI surface |
| `tests/*` | ✅ | descriptive `test_<thing>_<condition>` naming (`test_reflections_capped`, `test_survives_reload`) |

## Findings (ranked, complete)

**HIGH**
1. **Logging is duplicated and reinvents the Ledger.** `agent_logger` +
   `session_logger` (after `session_log` retired). Two vocabularies; both
   hand-roll persistence instead of using `Ledger`. → consolidate to one logger on
   the Ledger (`session:events`). [agent_logger fate pending — checkpoint-patch-tracking]
2. **"Health check" / logging utilities are re-implemented 3–4×.**
   `check_health` exists in `services/redis_manager`, `stack_manager/health`,
   `services/redis_ha_manager`, alongside `infrastructure/check_infrastructure_health`;
   `redis_manager` also has its own `log()`/`LogLevel`. One concept, many copies.

**MEDIUM**
3. **`fast_cache.py` lying aliases** — `redis_get`/`redis_set`/`redis_hget` name
   a redis-only op but do multi-layer cache. Rename aliases to match (or mark
   deprecated). Names-must-not-lie violation.
4. **`PortManager` defined twice** (`services/port_manager.py` +
   `stack_manager/ports.py`) — genus rule; rename one (e.g. stack-manager's →
   `StackPortManager` or merge).
5. **`stack_manager` internal duplication** — `_run_wsl`/`_run_powershell`/`_redis`
   copied across ~6 modules → extract a shared `_shell`/`_redis` helper.
6. **Two session summarizers** (`SessionCompressor`/`SessionSummarizer`) →
   Distiller precursors; fold in when Distiller lands.
7. **`services/redis_sync.py` overlaps `StoreReconciler`** (daemon vs our
   reconciler) — reconcile the two; `session_monitor` self-deprecated.

**LOW**
8. `infrastructure/health_check.py` "health" vs "diagnostics" vocabulary split — pick one.
9. `agent/initializer.py` — 6 init aliases; mark deprecated / trim to the canonical.
10. `SessionRecovery` duplicate (`session_recovery.py` vs `session_state.py`) — tracked/allowlisted; resolve.
11. `stack_manager` terse private helpers (`_c`, `_win`) — fine for a CLI; leave.
12. `agent_briefing_loader` → fold into Context pillar (System 4) when built.

## Overall verdict
The **core + recently-touched layers are strongly lexicon-adherent** (clean genus/
species, semantic names, deprecated aliases). Drift concentrates in three places:
(a) the **logging / health-check utility layer** (the same concept implemented
several times), (b) the **older standalone subsystems** (`services/`,
`stack_manager/`) — decent but non-lexicon naming plus internal duplication, and
(c) a few **specific naming bugs** (`fast_cache` lying aliases, `PortManager` dup).
Only **2 duplicate class names exist in the entire active tree** — the codebase is
fundamentally clean; these are refinements, not a rewrite.

## Recommended sequencing (slots into the roadmap)
1. Finish logging consolidation onto the Ledger (Finding 1) — after the agent_logger decision.
2. Unify health-check + the stray `log()`/`LogLevel` into the canonical
   `infrastructure` / `redis_connection` paths (Finding 2).
3. Quick naming fixes: `fast_cache` aliases (3), `PortManager` rename (4),
   `stack_manager` `_shell` helper (5).
4. Defer Distiller/Context precursors (6, 12) to their waves; topology + low items as polish.
