# bootstrap_analyst.md - DEPRECATED
> **⚠️ DEPRECATED**: Read `STARTUP.md` instead. Analyst-specific info is now in `AGENT_PRIMER.md`.

**Superseded by**: `E:\AI-Setup\STARTUP.md` and `E:\AI-Setup\AGENT_PRIMER.md`

---

## Quick Redirect

For Analyst agent initialization:

1. **`STARTUP.md`** - Session initialization, re-prime detection, startup sequence
2. **`AGENT_PRIMER.md`** - Best practices, ports, Docker, GPU setup
3. **`COORDINATION_PRIMER.md`** - Enterprise patterns including self-correction

---

## Analyst Workflow (Reference)

The Analyst follows this workflow:

```python
from blackboard import Blackboard

bb = Blackboard()

while True:
    proposal = bb.wait_for_proposal(timeout=0)
    if proposal:
        result = audit_proposal(proposal)  # Your audit logic
        bb.submit_verdict("Analyst", result["verdict"], 
                         result["reason"], result["checks"])
```

---

## What Changed (2026-04-14)

- Analyst bootstrap is now integrated into `STARTUP.md`
- Session change detection via `session_manager.py`
- Self-correction patterns documented in `COORDINATION_PRIMER.md`

---

**Last Updated**: 2026-04-14
