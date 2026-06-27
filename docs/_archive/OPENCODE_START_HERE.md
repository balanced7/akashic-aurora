# OPENCODE START HERE

**If you're reading this, you're an OpenCode instance. This file works in the first 50 lines.**

## What You Need to Know (RIGHT NOW)

You are part of a multi-agent coordination system. Your job:
1. **Initialize yourself** using the code below
2. **Load your context** (decisions, learnings, checkpoints from previous agents)
3. **Do your work**
4. **Record your learnings** for next agents

## Initialize Yourself (Copy This Code)

```python
from agent_init import initialize_and_load_context

result = initialize_and_load_context("your_agent_id", task_keyword="your_task")
api = result["api"]
context = result["context"]
state = result["state"]

print(f"Status: {result['status']}")
print(f"Decisions loaded: {len(api.get_startup_decisions())}")
print(f"Learnings loaded: {len(api.get_startup_learnings())}")
```

That's it. You now have:
- **api** - Make decisions, record learnings, emit signals
- **context** - Briefing, prior decisions, prior learnings
- **state** - Save/load checkpoints for crash recovery

## During Work

```python
# Make a decision (cached for next agent)
api.decision("your_decision_name", outcome="yes", reason="Why you chose it")

# Record a learning (for next agent to apply)
api.learning(
    experiment_name="what_you_tried",
    what_tried="x",
    expected_outcome="y",
    actual_outcome="z",
    category="performance",
    success="yes",
    recommendation="next_agent_should"
)

# Save progress checkpoint (survives crashes)
state.save_checkpoint(task="Your Task", progress=50, blockers=[])
```

## When Done

```python
# Signal completion with handoff for next agent
api.signal(
    signal_type="HANDOFF",
    briefing="What the next agent should know",
    details={"work_completed": "...", "next_steps": "..."}
)
```

## More Help

- See `agent_init.py` for all options
- See `AGENT_ONBOARDING.md` for examples
- See `SIGNAL_REFERENCE.md` for all signal types
- See `LEARNING_SYSTEM_QUICKSTART.md` for learning examples

**That's all you need. You're ready. What's your task?**
