# Agent Initialization Quick Start
**How to Initialize Any Agent (Including OpenCode) with Full Context**

---

## The One-Line Initialization

```python
from agent_init import initialize_and_load_context
result = initialize_and_load_context("your_agent_id", task_keyword="your_task")
api = result["api"]
```

That's it. Your agent now has:
- ✅ Briefing from previous handoff
- ✅ Relevant cached decisions
- ✅ Recent learnings
- ✅ Crash checkpoint (if applicable)

---

## Complete Usage Examples

### Example 1: OpenCode Code Analysis

```python
from agent_init import initialize_and_load_context

# Initialize
result = initialize_and_load_context(
    agent_id="opencode_code_analyzer",
    task_keyword="code_analysis"
)

if result["status"] != "success":
    print(f"Error: {result['message']}")
    exit(1)

api = result["api"]
state = result["state"]

# Use context
decisions = api.get_startup_decisions()
print(f"Found {len(decisions)} relevant past decisions")

# Do work
api.decision(
    "analyze_with_async",
    outcome="yes",
    reason="Faster processing for large codebases"
)

api.learning(
    experiment_name="async_analysis",
    what_tried="Async processing on 100+ files",
    expected_outcome="30% faster",
    actual_outcome="35% faster",
    category="performance",
    success="yes",
    recommendation="Always use async for >50 files"
)

# Checkpoint
state.save_checkpoint(
    task="Code Analysis",
    progress=100,
    blockers=[]
)
```

### Example 2: Implementation Agent with Recovery

```python
from agent_init import initialize_and_load_context

# Initialize (loads context + checks for crash recovery)
result = initialize_and_load_context(
    agent_id="impl_agent",
    task_keyword="implementation"
)

api = result["api"]
state = result["state"]

# Check for recovery
briefing = api.get_startup_briefing()
if briefing:
    print(f"Resuming task from previous handoff: {briefing['task']}")

if state.has_checkpoint():
    checkpoint = state.load_checkpoint()
    progress = checkpoint["progress"]
    print(f"Resuming from {progress}% complete")
else:
    progress = 0

# Work with context
api.action("implement_feature", details={"name": "feature_x"})

# Periodic checkpointing
while progress < 100:
    progress += 25
    state.save_checkpoint(
        task="Implementation",
        progress=progress,
        decisions_made=progress // 25
    )

# Complete
api.completion(success=True, output={"files_created": 5})
state.clear_checkpoint()
```

### Example 3: Quick Initialize (No Verbose Output)

```python
from agent_init import quick_initialize

# Fast initialization without diagnostics
try:
    api, state, context = quick_initialize("my_agent", "task_keyword")
    print("Ready to work!")
except RuntimeError as e:
    print(f"Initialization failed: {e}")
```

---

## Return Values Explained

```python
result = initialize_and_load_context("agent_id")

result["api"]                    # CoordinatorAPI instance
  .get_startup_briefing()        # Previous handoff briefing
  .get_startup_decisions()       # Relevant cached decisions
  .get_startup_learnings()       # Recent learnings to apply
  .decision()                    # Make a decision
  .action()                      # Log an action
  .learning()                    # Record a learning
  .completion()                  # Mark task complete

result["state"]                  # SessionState instance
  .has_checkpoint()              # Was there a crash?
  .load_checkpoint()             # Recover state
  .save_checkpoint()             # Save progress
  .clear_checkpoint()            # Mark recovery complete

result["context"]                # Full startup context dict
  ["briefing"]                   # Task briefing
  ["relevant_decisions"]         # Past decisions
  ["recent_learnings"]           # Learnings
  ["metadata"]                   # About what loaded

result["diagnostics"]            # StartupDiagnostics
  .print_report()                # Show startup timing

result["status"]                 # "success", "partial", "failed"
result["message"]                # Status message
result["initialization_time_ms"] # How long startup took
```

---

## For OpenCode Specifically

OpenCode can initialize with:

```python
# Direct invocation
from agent_init import initialize_and_load_context

result = initialize_and_load_context(
    agent_id="opencode_instance",
    task_keyword="code_analysis"  # or code_review, implementation, etc.
)

# Or via CLI
# python agent_init.py opencode_instance code_analysis
```

When OpenCode initializes:
1. Loads context from previous instances (if any)
2. Finds past decisions about code analysis
3. Discovers learnings about performance, best practices
4. Can recover from crash if it failed before
5. Starts fresh with all context ready

---

## Command-Line Usage

```bash
# Direct Python invocation
python agent_init.py opencode_instance code_analysis

# Or from within another script
from agent_init import initialize_and_load_context
result = initialize_and_load_context("opencode_instance", "code_analysis")
```

---

## Integration Points

### With Decision Making
```python
api = result["api"]

# Before making a decision, check what's cached
past_decisions = api.get_startup_decisions()
for decision in past_decisions:
    if decision_name == decision["name"]:
        # Reuse this decision
        api.decision(decision["name"], decision["outcome"], ...)
        break
```

### With Learning
```python
# Get learnings to avoid mistakes
learnings = api.get_startup_learnings()
for learning in learnings:
    if "to_avoid" in learning.get("anti_pattern", ""):
        print(f"Avoid: {learning['anti_pattern']}")

# Record new learnings
api.learning(
    experiment_name="...",
    what_tried="...",
    expected_outcome="...",
    actual_outcome="...",
    category="performance",  # or "quality", "cost", "architecture"
    success="yes",           # or "partial", "no"
    recommendation="..."
)
```

### With Checkpointing
```python
state = result["state"]

# On startup, check if recovering
if state.has_checkpoint():
    checkpoint = state.load_checkpoint()
    resume_from = checkpoint["progress"]

# During work, save periodically
state.save_checkpoint(
    task="My Task",
    progress=50,
    blockers=["Current issue"],
    decisions_made=5
)

# On completion
state.clear_checkpoint()
```

---

## Error Handling

```python
result = initialize_and_load_context("agent_id")

if result["status"] == "success":
    api = result["api"]
    # Use api normally
    
elif result["status"] == "partial":
    # Some features might not be available
    print(f"Warning: {result['message']}")
    api = result["api"]
    if api:
        # Still usable, but with reduced context
        pass
        
else:  # status == "failed"
    # Initialization failed completely
    print(f"Error: {result['message']}")
    exit(1)
```

---

## Performance Notes

### Startup Time
- **Without Redis:** ~55ms (file-based, very fast)
- **With Redis:** ~80-100ms (network dependent)
- **With Redis timeout:** Can be 60s+ (not recommended)

**Fix:** If startup is slow, Redis is timing out. System still works, just slower.

### Context Size
- Briefing: ~500 bytes
- Decisions (10): ~2KB
- Learnings (10): ~3KB
- Checkpoint: ~1KB
- **Total:** ~6KB (minimal overhead)

### Token Usage
- Initialization: ~100 tokens (load context)
- Per reused decision: 50 tokens saved
- Per new decision: 100 tokens used
- **At 60% reuse:** 35-40% overall savings

---

## Best Practices

### 1. Always Initialize at Startup
```python
# Good
from agent_init import initialize_and_load_context
result = initialize_and_load_context("agent_id")

# Bad - missing context
from coordinator_api import CoordinatorAPI
api = CoordinatorAPI("agent_id")  # No context loaded!
```

### 2. Use Task Keywords for Relevant Context
```python
# Good - gets relevant decisions
result = initialize_and_load_context("agent", task_keyword="implementation")

# Vague - might get irrelevant decisions
result = initialize_and_load_context("agent", task_keyword="work")
```

### 3. Check for Recovery Automatically
```python
result = initialize_and_load_context("agent_id")
state = result["state"]

# Always check for checkpoint
if state.has_checkpoint():
    # Agent crashed before, recover
    checkpoint = state.load_checkpoint()
    resume_from_progress = checkpoint["progress"]
```

### 4. Checkpoint Regularly During Long Tasks
```python
for i in range(10):
    # Do work
    progress = (i + 1) * 10
    
    # Checkpoint every 10%
    if progress % 20 == 0:
        state.save_checkpoint(
            task="Long Task",
            progress=progress
        )
```

### 5. Clear Checkpoint on Completion
```python
# On success
api.completion(success=True, output={...})
state.clear_checkpoint()

# Or on failure (but don't clear checkpoint for recovery)
api.completion(success=False, output={...})
# Don't clear - let next instance recover
```

---

## Testing

Run the verification test:

```bash
python test_opencode_init.py
```

Expected output:
```
[OK] OpenCode Initialization Test PASSED
  [+] OpenCode can initialize with agent_init
  [+] Bootstrap context loads automatically
  [+] API, state, and context are accessible
  [+] Decisions can be made and logged
  [+] Learnings can be recorded
  [+] Checkpoints work for recovery
```

---

## Troubleshooting

### "Connection timeout" during initialization
**Cause:** Redis is down or unreachable  
**Impact:** Startup slower (60s+) but still works  
**Fix:** Start Redis or ignore (file fallback works)

### "No context loaded" on first run
**Cause:** This is the agent's first run  
**Impact:** Normal - next run will have context  
**Fix:** None needed - expected behavior

### "Checkpoint file not found"
**Cause:** Checkpoint was cleared or doesn't exist  
**Impact:** Start fresh without recovery  
**Fix:** None - expected if no crash occurred

### "Can't import agent_init"
**Cause:** agent_init.py not in path  
**Impact:** Can't initialize  
**Fix:** Make sure E:\AI-Setup is in Python path

---

**Ready to initialize?**

```python
from agent_init import initialize_and_load_context
result = initialize_and_load_context("your_agent_id", "your_task")
```

That's it!
