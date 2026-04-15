# bootstrap_generator.md - DEPRECATED
> **⚠️ DEPRECATED**: Read `STARTUP.md` instead. Generator-specific info is now in `AGENT_PRIMER.md`.

**Superseded by**: `E:\AI-Setup\STARTUP.md` and `E:\AI-Setup\AGENT_PRIMER.md`

---

## Quick Redirect

For Generator agent initialization:

1. **`STARTUP.md`** - Session initialization, re-prime detection, startup sequence
2. **`AGENT_PRIMER.md`** - Best practices, ports, Docker, GPU setup

---

## Generator Workflow (Reference)

The Generator follows this workflow:

```
USER → PLANNING → write proposal.json → wait for verdict.json=PASS → EXECUTE → DONE
                                              ↓
                                          FAIL/NEEDS_WORK → REVISE → RESUBMIT
```

### Key Functions

```python
from blackboard import Blackboard

bb = Blackboard()

# Submit proposal
bb.submit_proposal(
    agent="Generator",
    title="Task title",
    description="What user asked for",
    steps=[...],
    metadata={}
)

# Wait for verdict
verdict = bb.wait_for_verdict(timeout=300)
if verdict["status"] == "PASS":
    # Execute
```

---

## What Changed (2026-04-14)

- Generator bootstrap is now integrated into `STARTUP.md`
- Session change detection via `session_manager.py`
- Re-prime triggers when SESSION_ID changes

---

**Last Updated**: 2026-04-14
