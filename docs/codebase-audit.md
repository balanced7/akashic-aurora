# Codebase Audit — readability, robustness, simplicity, coherence

Date: 2026-06-19. Read-only audit of the **active coordination system** (core/,
agent/, infrastructure/, services/, stack_manager/, root modules). Vendored and
archived trees (`_archive/`, `temp/`, `backup_wsl_migration/`, `dockerized-ai/`,
`ComfyUI-Zluda/`, `gemma_realtime/`, `models/`, `rocm-lib/`) were excluded.

## The one-sentence finding

**The `core/` we rebuilt is clean and modern; the outer shell around it (entry
points, root modules, `services/` daemons, docs) still references the
pre-consolidation world** — archived module names, old Redis namespaces,
`sys.path` hacks, and silent `except:` blocks. The next wins are dragging that
shell up to the standard `core/` now sets.

## Health map

| Layer | What | Status |
|-------|------|--------|
| `core/` (foundation/signals/learning/state) | Store, Ledger, AgentSignalLedger, LearningStore, AgentMemory, reconciler | Clean, tested, 17 importers of `core.foundation` |
| `context/` | SYSTEM 4 stub (empty `__all__`) | Planned — see project_context.py below |
| `bootstrap.py` | Entry point (run via `bootstrap.bat`) | Partially stale (see R1) |
| root modules | project_context, fast_agent_comm, agent_logger, session_* | Mixed: some active, some orphaned (see S2/S3) |
| `services/*` | 6 standalone daemons (each has `__main__`, launched by `.bat`) | Import-disconnected; mixed legit/legacy (see S1) |
| `stack_manager/` | CLI tool (`python -m stack_manager`) | Entry-point package; not audited in depth |

## Findings by theme

### Coherence (highest leverage)

- **C1 — `project_context.py` is a half-built Context pillar.** It already
  assembles architectural / big / mid / recent context layers for agent
  re-priming (`derive_full_context_for_agent_repriming`) — i.e. the 8–10k-token
  goal — with good semantic naming. But it's **Redis-only** (no Store, dies when
  Redis is down) and lives at root, while the planned `context/` package is an
  empty stub. *Implication: when we build the Context pillar, consolidate this
  into `context/` and onto `Store`/`Ledger` — don't rebuild from scratch.*
- **C2 — `fast_agent_comm.py` is the real-time messaging bus** (Redis Streams +
  consumer groups, direct/broadcast/request-response). It is genuinely distinct
  from the `Ledger` (live messaging vs durable replay log), so the two coexisting
  is correct. Future consideration only: both ride Redis Streams; a
  `Ledger`-with-consumer-groups could eventually unify them — not urgent.
- **C3 — `services/` overlaps the foundation at the edges.** Two sub-groups:
  *infra-ops* (`redis_manager` 1072 ln: AOF/RDB/backups; `redis_ha_manager`:
  master/replica/sentinel) manage the Redis **server** — a legitimately different
  layer from our app-level `Store`. But `redis_sync.py` (polls logs → Redis)
  conceptually overlaps `StoreReconciler` + `HybridStore` dual-write, and
  `session_monitor.py` **self-deprecates** in its own docstring ("Prefer
  ai_watchdog.py"). Needs triage, not a blind delete.

### Robustness

- **R1 — `bootstrap.py` silently degrades.** The main entry point imports
  `ai_setup_mcp`, `catchup`, `smart_log` — all now in `_archive/` — and queries
  stale Redis namespaces (`decisions:*`, `experience:*`, `reflections:*`) that
  match neither the current `learn:` nor `mem:` namespaces. All wrapped in bare
  `except:`, so it reports misleading status instead of failing. High-value,
  low-risk fix: repoint or remove the dead integrations; query real namespaces.
- **R2 — ~65 bare `except:` blocks** swallow errors silently across active code:
  `fast_cache.py` (11), `agent_logger.py` (10), `services/redis_manager.py` (9),
  `services/background_monitor.py` (9), `session_logger.py` (6),
  `fast_agent_comm.py` (6), `bootstrap.py` (4). Narrow them to specific
  exceptions + log. Prioritize the high-traffic ones (`fast_cache`, `bootstrap`,
  `session_logger`).
- **R3 — `core/foundation/fast_cache.py` is the messiest file in `core/`.** The
  only remaining direct `redis.Redis(` connector (probe-gated, so no hang), 11
  bare excepts, a `sys.path` hack, and `from config import`. Candidate to refactor
  onto `Store` or at least clean up. (Note: the 48s-hang fix is otherwise broadly
  adopted — most modules use `connect_to_redis_with_fail_fast`.)

### Simplicity / sprawl

- **S1 — `services/` is ~3,300 lines with zero import-graph connection.** Run as
  daemons via `.bat`. Triage each: keep (infra-ops), merge (redis_sync →
  reconciler), or retire (session_monitor self-deprecated).
- **S2 — root logging/session modules overlap.** `session_logger.py` (3
  importers, active) vs `session_log.py`, `session_compressor.py`,
  `session_summarizer.py`, `agent_logger.py` (0 importers each). Likely several
  orphans + concept duplication. Triage which is canonical.
- **S3 — documentation sprawl.** Many root `.md` (CONSOLIDATION_PLAN,
  SYSTEMS_ARCHITECTURE, ACTUAL_INVENTORY, IMPLEMENTATION_INVENTORY…) plus
  `docs/current/` duplicates — likely stale post-consolidation. Archive the dead
  ones so the live docs (this folder) are the single source.

### Coupling / readability

- **R4 — 12 files use `sys.path.insert`** to import siblings — fragile and
  cwd-dependent. A proper package install (pyproject/editable, or a single path
  shim) would remove them all. Systemic but mechanical.
- **R5 — print + ANSI vs logging.** `bootstrap.py` and `services/` print with raw
  ANSI color codes; `core/` uses `logging`. Pick one convention for app output.

## Prioritized backlog

| # | Item | Value | Effort | Risk | Notes |
|---|------|-------|--------|------|-------|
| 1 | Fix `bootstrap.py` stale imports + namespaces (R1) | High | Low | Low | Entry point should tell the truth; quick win |
| 2 | Bare-except sweep in high-traffic files (R2/R3) | High | Med | Low | Start fast_cache, bootstrap, session_logger |
| 3 | Context pillar: consolidate `project_context.py` → `context/` + onto Store (C1) | High | High | Med | Aligns with the planned next feature + memory Phases B–E |
| 4 | `services/` triage: classify keep/merge/retire (S1/C3) | Med | Med | Med | Daemons — verify launch paths before removing |
| 5 | Root module triage: dedup session_*/agent_logger (S2) | Med | Med | Low | Confirm orphans; pick canonical logger |
| 6 | Kill `sys.path.insert` via packaging (R4) | Med | Med | Low | Systemic; touches ~12 files |
| 7 | Docs triage: archive stale root .md (S3) | Low | Low | Low | Make docs/ the single source |
| 8 | Unify fast_agent_comm onto Ledger+consumer-groups (C2) | Low | High | Med | Only if it earns its keep; future |

## Recommended sequence
1–2 first (quick, high-value truth + robustness). Then **3** (the Context pillar
is the natural next feature and the biggest payoff — and it reuses
`project_context.py` rather than rebuilding). Then **4–5** (sprawl triage), **6**
(packaging), **7** (docs). **8** is optional/future.

Nothing here was changed — this is a map for steering. Each item is independently
shippable and verifiable, consistent with how `core/` was built.
