# Port Registry — what lives where

Status: canonical (born 2026-07-16). **Single source of truth in code: `config.py` PORT
REGISTRY block.** This doc is the human-readable companion. If they ever disagree, `config.py`
wins and this doc is the bug.

## Why this exists

The console has **always** bound `8787` (`scripts/bifrost_ui.py`, `--port` default). But
`scripts/deepseek_chat.py` documented the UI as *"port 8788, falls back to 8787"* and its
`reload_ui()` targeted `8788` — so half the fleet looked for the console on a port nothing was
serving. Add a persistent sandbox clone (its own UI + Redis) and ad-hoc test UIs grabbing
whatever port, and every session re-litigated "which UI is this and is it the real one?" This
registry ends that: **the digits tell you the world.**

## The rule

```
87 8x   PRODUCTION bifrost    the one live fleet — harness-managed, stable forever
87 9x   SANDBOX               the persistent E:\AI-Setup-Sandbox clone
89 xx   TEST / EPHEMERAL UIs  throwaway; many at once; never touches production
```

Redis mirrors the same worlds: `16379` prod · `16380` sandbox · **db 15** on prod = test
isolation (tests never need their own Redis port — they use a separate logical DB).

## The map

| Port | World | What | Source of truth | Live? |
|------|-------|------|-----------------|-------|
| **8787** | prod | **Bifrost live agent console** (the UI you watch) | `config.PORT_UI` · `bifrost_ui.py:521` | ✅ the one to open |
| 8788 | prod | **RESERVED prod-aux — NOT the console** | `config.PORT_UI_RESERVED` | ⛔ do not bind |
| 18765 | prod | MCP HTTP mode (optional; MCP is stdio by default) | `config.PORT_MCP_HTTP` · `ai_setup_mcp.py:545` | rare |
| **16379** | prod | Redis (canonical knowledge store; db 0 prod / db 15 test) | `config.REDIS_PORT` | ✅ always |
| **8790** | sandbox | sandbox console | `config.PORT_UI_SANDBOX` | when sandbox runs |
| **16380** | sandbox | sandbox Redis (isolated from prod) | `config.REDIS_PORT_SANDBOX` | when sandbox runs |
| **8900–8999** | test | **test / ephemeral UI band** — allocate upward | `config.allocate_test_ui_port()` | per test |

### Legacy / inactive (documented so nobody resurrects them by accident)
- `6379` / `6380` — WSL Redis HA replica/master. Separate server lifecycle
  (`services/redis_ha_manager.py`); **not** the app endpoint. Inactive.
- `8080`, `8090`, `8188` — dead ports in `_archive/python_old/` (old MCP HTTP, stack GUI,
  ComfyUI). Archive only; never live.

## Rules for writing code that opens a port

1. **Never hardcode a UI port.** Import from `config.py`:
   - production console → `config.PORT_UI` (8787)
   - a test/throwaway UI → `config.allocate_test_ui_port(offset)` (8900+), which raises if you
     escape the band.
2. **8788 is not the console.** It's reserved prod-aux. Any code that says "the UI is on 8788"
   is stale — fix it to `config.PORT_UI`.
3. **Tests never bind 8787 or 8790.** A test UI lives in `[8900, 8999]`; test data lives in
   Redis **db 15**, not a separate Redis port.
4. **The harness owns reloading the prod console.** Agents do not POST `/reload` to 8787
   (it re-execs the server and breaks the harness-owned preview). Coordinate UI changes on
   the bus; claude/the harness reloads.

## Open follow-ups (tracked, not yet done)
- `scripts/deepseek_chat.py:216,720-725` still name **8788** as the UI port — align to
  `config.PORT_UI` and relabel 8788 as reserved. Handed to deepseek (owns that file; live).
- `scripts/bifrost_ui.py:521` hardcodes `default=8787` — should import `config.PORT_UI` so the
  canonical value has exactly one home. Low priority (values already agree).
