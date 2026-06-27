# BreakThrough Agent Protocol (all agents)

**Applies to:** Cursor, Claude (Desktop / API hosts), OpenCode, and any tooling that attaches to MCP.

Single source reference: **`bootstrap.md`** (infrastructure bootstrap + deep links).

## One-call MCP bootstrap (preferred when MCP is configured)

1. Call MCP **`breakthrough_bootstrap(agent, tier, intent, systems_worked)`** — optional infra ensure (DAG-aware, excludes `win-mcp`), persists session id, emits **`session:events`** `start`, returns a Redis/WSL context snapshot. For tiers and tool order, read MCP resource **`breakthrough://launch-contract`**.
2. Equivalent split flow: **`session_infra_ensure`** → **`session_register`** (both honor **`BREAKTHROUGH_ALLOW_INFRA_START`**; default allows infra starts — set to **`0`** / **`false`** / **`no`** / **`off`** for inspect-only machines).
3. **`session_infra_status`** — read-only health snapshot (no launches).

## Before substantive work

1. If MCP is **not** available, start services per **`bootstrap.md`** (Redis HA, MCP, compressor daemon, Gemma/`ai-voice` as needed).
2. Pull infra context:
   ```powershell
   wsl -d Ubuntu-Migrate -e bash -c "redis-cli GET migration:summary"
   wsl -d Ubuntu-Migrate -e bash -c "redis-cli GET context:wsl_infrastructure"
   ```
3. Run:
   ```powershell
   python E:\AI-Setup\catchup.py
   ```
4. Optional — DAG orchestrator (dependency-order startup): from **`E:\AI-Setup`**, run **`python -m stack_manager.cli start`**.

## Ports (truth table — do not use 6379 for writes unless you verified topology)

| Role | Host port | Notes |
|------|-----------|--------|
| WSL Redis **writes** | **6380** | Application master |
| WSL replicas / read | 6379, 6381 | Often read-only |
| Docker Redis Stack | **16379** | Single instance; summaries mirrored here |
| BreakThrough MCP HTTP | **8080** | Optional; stdio preferred for Cursor/OpenCode |

## Unified MCP integration

Configure **one** MCP server pointing at **`E:\AI-Setup\ai_setup_mcp.py`** (stdio or `--http --port 8080`).

**Required workflows for continuity:**

- **`breakthrough_bootstrap`** — preferred session open (infra + register + snapshot); **`session_register`** if infra already up.
- **`session_infra_status` / `session_infra_ensure`** — supervisor-backed checks and idempotent launches (gated by **`BREAKTHROUGH_ALLOW_INFRA_START`**).
- **`session_set_identity`** — persist a shared session id (`blackboard_data/session_state.json`).
- **`session_append_event`** — canonical log (Redis Stream **`session:events`** + JSONL mirror).
- **`learning_record_decision` / `learning_record_experience`** — Redis **`learn:*`** ADRs and task outcomes.
- **`session_flush_summary`** — force digest into **`session:summary:*`** (WSL + Docker) before hand-off.
- **`project_add_milestone` / `project_complete_milestone`** — roadmap state in Redis.

## When to log (`session_append_event`)

| Timing | Fields to fill |
|--------|----------------|
| Session start | `event_type=start`, **`intent`**, **`systems_worked`** |
| During work | `event_type=change` or `note`, **`changes_made`**, **`milestones_update`** |
| Decision | `event_type=decision`, **`decisions`** |
| Blocked | `event_type=blocker`, **`blockers`** |
| Wrap-up | `event_type=close`, **`next_steps`**; optionally `summary_request` or **`session_flush_summary`** |

**Agent** must be lowercase: `cursor`, `claude`, `opencode`, `manual`.

## Forbidden

- Leaving continuity-only facts **only** in chat with no MCP append.
- Calling random Redis CLI commands on **6379** for application writes without checking role.

## Troubleshooting

- **READONLY** from Redis → you hit a replica; switch to port **6380** (Python: `from config import get_redis_config`).
- **No summaries in Docker** → run **`session_flush_summary`** once; restart **`session_compressor.py --daemon`**.
- **Pipeline check** → `python E:\AI-Setup\health_check_session_pipeline.py` (or `--json`).
