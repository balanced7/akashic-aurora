# Local-agent fleet — state and operating notes

> Public since 2026-07-02 (user decision). History: built git-excluded the same morning,
> then cleared for the repo once the purpose firmed up: local agents run the RESEARCH
> DAY SHIFT (research/README.md) so frontier tokens go to deciding, not gathering.

## Current state (2026-07-02)

- **Ollama 0.31.1 native** on `127.0.0.1:11434` — deliberately NOT 11434: that port is a
  Docker/WSL Ollama **0.20.5** (the raw-JSON tool-bug version) serving the Open WebUI
  stack (`ai-ollama` container). Never touch it; never trust `ollama --version` alone —
  check the port owner (lesson: local_ollama_port_shadowing).
- **glm-4.7-flash** (19 GB) runs 14 GiB-on-GPU (RX 9070 XT 16 GB, Vulkan — RDNA4 has no
  Windows ROCm), ctx=64000, flash attention, q8_0 KV cache. Persistent user env:
  OLLAMA_HOST=127.0.0.1:11434, OLLAMA_CONTEXT_LENGTH=64000, OLLAMA_FLASH_ATTENTION=1,
  OLLAMA_KV_CACHE_TYPE=q8_0.
- **Measured**: ~25 tok/s generation; 30.9K-token context canary green (177 s cold
  prefill, warm turns incremental); clean `tool_use` blocks, on-schema.
- **E2E proven**: headless Claude Code (desktop-bundled CLI) on the local model ran a
  real repo command and answered correctly; hooks fired + ledgered as `glm_local`
  (lesson: local_agent_first_e2e).

## The scripts

| Script | Job |
|--------|-----|
| `preflight_local_model.py` | version / model / tool-call / context-canary / speed gate — a failed probe is a session saved |
| `launch_local_agent.ps1` | one command: server up → model pulled → probe → Claude Code with every model tier pinned local + AKASHIC identity |
| `run_research_day.ps1` | the shift: one fresh headless session per research/queue task, hard timeout, draft validation, runlog |
| `websearch.py` | discovery door (R2): CLI over the self-hosted SearXNG (`akashic-searxng` container, loopback :8888, JSON API via `searxng/settings.yml`) — WebSearch doesn't exist on a local backend |

Worker tool grants (R2): `WebFetch, Grep, Glob, Read, Write, Edit, Bash(curl *), Bash(py *)` —
near-frontier tool access; the tree stays safe because enforcement lives at the door
(git-guard + peer locks + gated ships), not in model compliance.

## Operating rules

- Bounded tasks only (summarize / classify / consolidate / seeded research). This tier
  loops on open-ended shell work — Terminal-Bench gap is real.
- One task = one fresh session (no context rot; matches the wake-into-fresh-session lesson).
- Identity is per-backend (`glm_local`), so the funnel measures this tier's value rate
  separately — including whether a weaker model benefits MORE from injected lessons.
- Anthropic documents the ANTHROPIC_BASE_URL mechanism but does not support non-Claude
  models behind it: community pattern, kept honest here (research note
  `research: local/free models via Claude Code 2026-07` has the full survey).

## Rollback

Kill server: `Stop-Process -Name ollama`; env: remove the four OLLAMA_* user vars;
model blobs: `C:\Users\L5\.ollama\models` (~19 GB); uninstall: `winget uninstall Ollama.Ollama`.
