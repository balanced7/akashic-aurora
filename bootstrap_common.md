# bootstrap_common.md - DEPRECATED
> **⚠️ DEPRECATED**: Read `STARTUP.md` instead. Common rules are now in `AGENT_PRIMER.md` and `COORDINATION_PRIMER.md`.

**Superseded by**: `E:\AI-Setup\STARTUP.md`, `E:\AI-Setup\AGENT_PRIMER.md`, and `E:\AI-Setup\COORDINATION_PRIMER.md`

---

## Quick Redirect

For shared rules across all agents:

1. **`STARTUP.md`** - Session initialization, re-prime detection, startup sequence
2. **`AGENT_PRIMER.md`** - Hardware config, ports, Docker, GPU setup
3. **`COORDINATION_PRIMER.md`** - Enterprise patterns, circuit breakers, retries

---

## Common Rules (Reference)

### 1. Local Files First
```
E:\AI-Setup\blackboard_data\    # State files (fast)
E:\AI-Setup\session_logs\        # JSONL logs with source tags
E:\AI-Setup\knowledge_base.py    # KB module
```

### 2. Redis for Signals Only
```python
# Don't block on Redis - poll local files
bb = Blackboard()  # Falls back to local-only if Redis down
```

### 3. Source Tags in Logs
```python
log("action", "description", source="generator")  # or "analyst", "master"
```

---

## What Changed (2026-04-14)

- Common rules now documented in `AGENT_PRIMER.md` and `COORDINATION_PRIMER.md`
- Session change detection via `session_manager.py`
- Unified startup sequence in `STARTUP.md`

---

**Last Updated**: 2026-04-14
