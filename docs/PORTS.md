# Port Registry — what lives where

Status: current  ·  **GENERATED — do not edit by hand.**
Source of truth: `config.PORT_REGISTRY`. Regenerate with `py scripts/generators/gen_ports.py`.

This file is the DECLARED plane only, so it is reproducible on any machine. For what is actually
listening right now — and what nobody declared — run:

```
py scripts/checkers/check_ports.py --report
```

## The bands — the digits tell you the world

```
8780-8789   PROD
8790-8799   BETA
8800-8809   ALPHA
8900-8999   TEST
```

Redis mirrors the same worlds: `16379` prod · `16380` beta · `16381` alpha · **db 15** on prod = test isolation
(tests never need their own Redis port — they use a separate logical DB).

## The map

`bound_by` is the field the old hand-written map could not express, and the reason its blind spot
was invisible: a **container**-bound port appears in NO source literal, so no amount of grepping
this repo would ever have found it.

| Port | World | Bound by | What | Owner |
|------|-------|----------|------|-------|
| **3080** | prod | external | Rill DSH web UI on loopback | `dsh web / core/fleet/seat_launchers.py` |
| **8787** | prod | app | Bifrost live agent console | `scripts/bifrost_ui.py` |
| **8788** | prod | app | RESERVED prod-aux -- NOT the console; do not bind | `(reserved)` |
| **8888** | prod | container | the fleet's ONLY web-search door (loopback only) | `akashic-searxng / scripts/local/websearch.py` |
| **11434** | prod | container | local model lane; core/fleet/caller.py calls /api/generate | `ai-ollama` |
| **16379** | prod | container | canonical knowledge store + bus (db 0 prod / db 15 test) | `akashic-redis` |
| **18765** | prod | app | MCP HTTP mode (stdio is the default, so usually silent) | `ai_setup_mcp.py` |
| **47100** | prod | app | runner control-channel BASE; each seat takes base+n on loopback, so the exact port is dynamic by design | `core/comm/control_channel.py` |
| **3000** | external | container | human chat front-end over the same ollama; no live repo refs | `ai-open-webui` |
| **5000** | external | container | voice service; no live repo refs | `ai-voice` |
| **5001** | external | container | voice service (second port) | `ai-voice` |
| **8790** | beta | app | beta console (was: sandbox) | `beta:scripts/bifrost_ui.py` |
| **8800** | alpha | app | alpha console | `alpha:scripts/bifrost_ui.py` |
| **16380** | beta | container | beta Redis, isolated from prod and alpha | `akashic-redis-beta` |
| **16381** | alpha | container | alpha Redis, isolated from prod and beta | `akashic-redis-alpha` |

## Retired — never silently resurrect

Kept deliberately: deleting a retirement makes the port re-discoverable as "free" by the next
person, which is how a dead service comes back wearing a live port.

- **6379** — WSL Redis HA replica -- separate lifecycle, not the app endpoint
- **6380** — WSL Redis HA master -- separate lifecycle, not the app endpoint
- **8000** — vllm-server -- container REMOVED 2026-08-10 (status Created; never ran)
- **8080** — ai-knowledge-api -- container REMOVED 2026-08-10 (exit 127 for 7 weeks; dead)

## Rules for code that opens a port

1. **Never hardcode a port.** Import it from `config.py`; a throwaway UI uses `config.allocate_test_ui_port(offset)`, which raises if you escape the band.
2. **8788 is not the console.** It is reserved prod-aux. The console is `config.PORT_UI` (8787).
3. **Tests never bind 8787, 8790 or 8800.** A test UI lives in [8900, 8999]; test data lives in Redis db 15.
4. **A new port goes in `config.PORT_REGISTRY` with an owner** — `check_ports.py` fails the commit otherwise, and the failure names the three ways out.

## Dynamic by design

Runner control channels take `CONTROL_PORT_BASE + n` on loopback, one per seat (`core/comm/control_channel.py`),
so the exact port cannot be registered by number. An unregistered listener high in the range is
therefore not automatically drift — the checker says so rather than crying wolf.

