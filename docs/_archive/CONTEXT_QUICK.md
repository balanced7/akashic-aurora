# Context Quick Reference

After initialization, you have context from previous agents. Here's what you can access:

## What's Available

```python
result = initialize_and_load_context("agent_id", "task_keyword")
api = result["api"]

# Get briefing (what the previous agent handed off)
briefing = api.get_startup_briefing()
if briefing:
    print(f"Previous agent said: {briefing}")

# Get cached decisions (reuse to save tokens)
decisions = api.get_startup_decisions()
for decision in decisions:
    print(f"{decision['name']}: {decision['outcome']}")

# Get learnings (learn from previous attempts)
learnings = api.get_startup_learnings()
for learning in learnings:
    print(f"Learned: {learning['recommendation']}")

# Get session state (crash recovery)
state = result["state"]
if state.has_checkpoint():
    checkpoint = state.load_checkpoint()
    print(f"Resume from {checkpoint['progress']}% done")
```

## Common Patterns

### Reuse a decision to save tokens
```python
decisions = api.get_startup_decisions()
for d in decisions:
    if d['name'] == 'use_async':
        print(f"Previous agent chose: {d['outcome']}")
        # Use their decision instead of re-deciding
        use_async = d['outcome'] == 'yes'
        break
```

### Apply learnings to avoid rework
```python
learnings = api.get_startup_learnings()
for l in learnings:
    if l['category'] == 'performance':
        print(f"Tip: {l['recommendation']}")
        # Follow the recommendation
```

### Resume from checkpoint
```python
state = result["state"]
if state.has_checkpoint():
    checkpoint = state.load_checkpoint()
    task = checkpoint['task']
    progress = checkpoint['progress']
    print(f"Resuming {task} at {progress}%")
    # Continue from where you left off
else:
    print("Starting fresh (no prior checkpoint)")
```

## Context Structure

```python
context = result['context']
# Has keys:
# - briefing: str (from previous agent handoff)
# - decisions: list (cached decisions)
# - learnings: list (cached learnings)
# - checkpoint: dict (crash recovery data)
# - metadata: dict (system info)
```

---

**Empty context is normal!** First agent has no prior context.  
**Subsequent agents get smarter** with each decision/learning logged.

For more: See `CONTEXT_SCHEMA.md` and `AGENT_ONBOARDING.md`
