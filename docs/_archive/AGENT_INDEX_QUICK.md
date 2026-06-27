# Agent Quick Index

**Use this to find what you need in 50-100 lines.**

## I need to...

| Need | File | Read Time |
|------|------|-----------|
| **Initialize myself** | `OPENCODE_START_HERE.md` | 2 min ✓ |
| **Understand what context is available** | `CONTEXT_QUICK.md` | 3 min ✓ |
| **Emit signals (decisions, learnings)** | `SIGNALS_QUICK.md` | 2 min ✓ |
| **See all available context types** | `CONTEXT_SCHEMA.md` | 5 min |
| **Understand the full system architecture** | `FRAMEWORK_PROTOCOL.md` | 15 min |
| **See recovery/checkpoint examples** | `AGENT_ONBOARDING.md` | 10 min |
| **Debug initialization problems** | `TROUBLESHOOTING.md` | varies |

## Quick Code Examples

### Initialize
```python
from agent_init import initialize_and_load_context
result = initialize_and_load_context("agent_id", "task")
api = result["api"]
```

### Load Context
```python
decisions = api.get_startup_decisions()
learnings = api.get_startup_learnings()
```

### Make a Decision (saves for next agent)
```python
api.decision("decision_name", outcome="yes", reason="Why")
```

### Record a Learning (helps next agent)
```python
api.learning(experiment_name="test", what_tried="x", actual_outcome="y", category="perf", success="yes")
```

### Save Checkpoint (survives crashes)
```python
state.save_checkpoint(task="MyTask", progress=50, blockers=[])
```

### Signal Completion (with handoff)
```python
api.signal(signal_type="HANDOFF", briefing="What next agent should know")
```

## System at a Glance

- **Phase:** 1.5 (Startup & Context Recovery) - COMPLETE
- **Status:** All tests passing, ready for agents
- **Your first task:** Initialize + report context loaded
- **Your goal:** Use cached decisions/learnings to work smarter

## If Something's Wrong

| Symptom | Check |
|---------|-------|
| Import fails | Make sure you're in E:\AI-Setup directory |
| Initialization hangs | Redis is down (expected, file fallback works) |
| No context loaded | Normal for first run |
| Checkpoint not loading | Check `state.has_checkpoint()` first |

---

**Read `OPENCODE_START_HERE.md` first (right now, it's only 40 lines).**  
**Everything else is optional depth.**

Then report back what context loaded!
