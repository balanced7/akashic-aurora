# bootstrap_master.md - DEPRECATED
> **⚠️ DEPRECATED**: Read `STARTUP.md` instead. Master-specific info is now in `AGENT_PRIMER.md`.

**Superseded by**: `E:\AI-Setup\STARTUP.md` and `E:\AI-Setup\AGENT_PRIMER.md`

---

## Quick Redirect

For Master agent initialization:

1. **`STARTUP.md`** - Session initialization, re-prime detection, startup sequence
2. **`AGENT_PRIMER.md`** - Best practices, ports, Docker, GPU setup

---

## Master Workflow (Reference)

The Master is a lightweight Python state machine (not an LLM):

```python
from master import Master

master = Master()
master.start()  # Runs the state machine loop
```

### State Machine

```
IDLE → PLANNING → REVIEW → EXECUTING → VERIFYING → DONE
                    ↓
                  ERROR
```

### Key Functions

```python
# Check prerequisites
from master import check_prerequisites
for name, status in check_prerequisites():
    print(f"{name}: {status}")

# Monitor VRAM
from master import get_vram_usage
vram = get_vram_usage()
```

---

## What Changed (2026-04-14)

- Master bootstrap is now integrated into `STARTUP.md`
- Session change detection via `session_manager.py`
- VRAM monitoring and loop prevention continue to work

---

**Last Updated**: 2026-04-14
