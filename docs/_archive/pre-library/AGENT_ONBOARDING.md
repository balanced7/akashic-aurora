# Agent Onboarding Guide
**How to Join and Operate in the Multi-Agent Coordinator System**

---

## What You Are

You are part of a multi-agent system designed for:
- **Collaborative problem-solving** - Multiple agents work on different parts of the same project
- **Zero context loss** - Decisions and learnings are preserved for future agents
- **Efficient reasoning** - Avoid re-thinking problems that have been solved before
- **Transparent operation** - All work is observable and measurable

Your role:
1. **Do work** - Your primary function
2. **Communicate work** - Log decisions, blockers, completions
3. **Learn from others** - Use cached decisions and briefings
4. **Hand off cleanly** - Pass context to the next agent if needed

---

## Getting Started (First 30 Seconds - EXECUTABLE)

### FASTEST PATH: Initialize with one import

```python
from agent_init import initialize_and_load_context

result = initialize_and_load_context("your_agent_id", task_keyword="your_task")
api = result["api"]
state = result["state"]
context = result["context"]
```

This single call handles:
- ✅ Load briefing from previous handoff
- ✅ Load relevant cached decisions
- ✅ Load recent learnings
- ✅ Check for crash checkpoint
- ✅ Prepare you for work with full context

---

## Getting Started (Traditional 2-Minute Path)

When you begin:

1. **Initialize yourself** (NEW - recommended)
   - **When you have a briefing:** Only if another agent handed off work to you explicitly
   - **When you don't:** You're the first agent (fresh start) or continuing your own session (no new briefing needed)
   - **What it contains:** decisions made, blockers encountered, project state, learnings
   - If you're taking over from another agent: briefing tells you everything they learned
   - If you're starting fresh: no briefing (check PROJECT_STATE for overall context instead)

2. **Review the decision cache**
   - Look at what's been decided already
   - Don't re-decide things that are settled
   - Understand the reasoning behind past decisions

3. **Note any blockers**
   - Know what's stuck or uncertain
   - Plan how you'll handle them (work around, fix, escalate)
   - Report new blockers as you encounter them

4. **Start working**
   - You're now part of the system
   - Every meaningful action becomes observable
   - No special effort needed—just work naturally and communicate

---

## After Initialization: Use Your Context

Once you've initialized, you have access to:

```python
# From the initialization result
context = result["context"]
context["briefing"]              # Task handed off from previous agent
context["relevant_decisions"]    # Decisions you can reuse
context["recent_learnings"]      # Learnings to avoid mistakes

# From the API instance
api = result["api"]
api.get_startup_briefing()       # Your task briefing
api.get_startup_decisions()      # Past decisions (reuse these!)
api.get_startup_learnings()      # Recent learnings to apply

# From the state instance
state = result["state"]
if state.has_checkpoint():
    checkpoint = state.load_checkpoint()
    print(f"Resuming from {checkpoint['progress']}%")
```

---

## How to Communicate: The Four Signals

Everything you do fits into signal types. Once initialized, use the API to emit them.

### Signal Type 1: DECISION

**When to use:** You made a choice that affects the system

**Format:**
```
DECISION: {what_you_decided}
├─ Reasoning: {why_you_chose_this}
├─ Outcome: {what_you_chose}
├─ Confidence: {high | medium | low}
└─ Reversible: {yes | no}
```

**Real Examples:**

```
DECISION: use_signal_based_logging
├─ Reasoning: Agents emit signals (decision, blocker, handoff) instead of prose. 
│             Reduces token overhead from 30% to 5%. Prevents re-reasoning.
├─ Outcome: Yes, implement signal-based logging
├─ Confidence: high
└─ Reversible: no (architecture decision)
```

```
DECISION: coordinator_runs_asynchronously
├─ Reasoning: Coordinator monitors agent signals in background. Doesn't block agents.
│             Keeps overhead <5% CPU, <200MB RAM. Agents don't wait for coordination.
├─ Outcome: Implement as background thread/process
├─ Confidence: high
└─ Reversible: yes (could run synchronously if needed)
```

```
DECISION: file_fallback_for_redis
├─ Reasoning: Redis might not be available. File-based JSONL logging is as reliable
│             as Redis for our use case. Supports graceful degradation.
├─ Outcome: Implement dual-write (Redis + files). Use files if Redis unavailable.
├─ Confidence: high
└─ Reversible: yes (can remove file fallback later)
```

**Why this matters:**
- Next agent reads this and doesn't re-decide
- System caches this decision
- Future agents can reference: "Why did we choose X?"
- Saves 30-50 tokens per decision reuse

---

### Signal Type 2: BLOCKER

**When to use:** Something is blocking progress, stuck, or uncertain

**Format:**
```
BLOCKER: {what_is_stuck}
├─ Severity: {low | medium | high}
├─ Description: {what's the problem}
├─ Impact: {how_it_affects_progress}
└─ Workaround: {how_you're_handling_it}
```

**Real Examples:**

```
BLOCKER: redis_connection_failing
├─ Severity: high
├─ Description: Can't connect to Redis on port 6379. May not be running.
├─ Impact: Can't test coordinator monitoring with real streams.
│          Decisions won't be cached in-memory.
└─ Workaround: Switching to file-based logging. Using JSONL fallback.
```

```
BLOCKER: vram_unclear_for_llama
├─ Severity: medium
├─ Description: Don't have exact VRAM requirement for Llama 8B quantized.
│              Need to test actual allocation.
├─ Impact: Can't commit to local inference without measurement.
└─ Workaround: Documenting assumptions. Will test in Week 3.
```

```
BLOCKER: context_window_might_overflow
├─ Severity: medium
├─ Description: Agent briefing + history might exceed 8K token limit.
├─ Impact: Agents could be cut off mid-context, losing information.
└─ Workaround: Implementing context compression. Testing 7092-token limit.
```

**Why this matters:**
- System monitors blockers, escalates critical ones
- Next agent knows what to work around or fix
- Prevents wasting time on known problems
- Alerts if something stays blocked too long (>5 min, severity=high)

---

### Signal Type 3: HANDOFF

**When to use:** You're done with your part; another agent is taking over

**Format:**
```
HANDOFF: {next_agent}
├─ Task: {what_they_should_do}
├─ Context: {what_they_need_to_know}
├─ Blockers: {what_you_couldn't_solve}
└─ Learned: {what_you_learned_for_them}
```

**Real Example:**

```
HANDOFF: implementation_agent
├─ Task: Build coordinator_api.py and coordinator_service.py
├─ Context: 
│   ├─ Architecture approved: signal-based logging with async coordinator
│   ├─ Decisions cached:
│   │  ├─ use_signal_based_logging (95% efficiency target)
│   │  ├─ coordinator_async (5% CPU/200MB overhead)
│   │  └─ file_fallback_for_redis (available)
│   ├─ Blockers known: redis_connection_failing (use files)
│   └─ Token budget: 500 tokens for implementation
├─ Blockers:
│   ├─ Redis might not be available (use file fallback)
│   └─ No real agent integration yet (test manually)
└─ Learned:
   ├─ Signal-based logging reduces tokens significantly
   ├─ File fallback is as reliable as Redis
   ├─ Coordinator needs to be invisible (<5% CPU)
   └─ Test framework is important for iteration
```

**Why this matters:**
- Zero context loss between agents
- Next agent doesn't repeat work
- Blockers are known upfront
- Learning is captured and shared
- System generates a briefing from this for context awareness

---

### Signal Type 4: COMPLETION

**When to use:** You finished your task (success or failure)

**Format:**
```
COMPLETION: {task_name}
├─ Success: {yes | no}
├─ Output: {what_you_produced}
├─ Metrics: {how_well_you_did}
└─ Learned: {what_you'd_do_differently}
```

**Real Examples:**

```
COMPLETION: coordinator_api_implementation
├─ Success: yes
├─ Output: 
│   ├─ coordinator_api.py (157 lines)
│   ├─ Complete signal-based API
│   ├─ Redis + file fallback
│   └─ Full test coverage
├─ Metrics:
│   ├─ Signal overhead: 0.2-0.5ms
│   ├─ Code coverage: 95%
│   └─ Lines per function: avg 12
└─ Learned:
   ├─ File-based logging works as well as Redis
   ├─ Dual-write simplifies fallback
   └─ API should emphasize minimal overhead in docs
```

```
COMPLETION: hardware_optimization_analysis
├─ Success: yes
├─ Output:
│   ├─ HARDWARE_OPTIMIZATION_BLUEPRINT.md (exact allocations)
│   ├─ COMPLETE_SYSTEM_INTEGRATION.md (timing + memory layout)
│   └─ Verified 30% peak VRAM, 34% typical RAM
├─ Metrics:
│   ├─ Token efficiency: 95% achievable (proven mathematically)
│   ├─ Overhead: 5% (vs 30% baseline)
│   └─ Cost: 10x cheaper than cloud APIs
└─ Learned:
   ├─ Video-game level optimization is realistic
   ├─ Every GB must be accounted for
   ├─ Graceful degradation requires planning
   └─ Context window compression is critical
```

**Why this matters:**
- System knows when work is done
- Metrics are captured for future optimization
- Learning informs next phase
- Completion triggers briefing generation for next agent

---

## Reading Your Context: What's Available

When you start, you can access five types of context:

### 1. DECISION_CACHE
**What it is:** All decisions made so far, with reasoning

**Example:**
```
DECISION_CACHE:
├─ signal_based_logging
│  ├─ Reasoning: Reduces overhead from 30% to 5%
│  ├─ Outcome: Approved
│  └─ Used by: 3 agents (saved ~100 tokens)
├─ coordinator_async
│  ├─ Reasoning: <5% CPU, doesn't block agents
│  ├─ Outcome: Approved
│  └─ Used by: 2 agents (saved ~80 tokens)
└─ [47 more decisions cached]
```

**When to check:** Before making any architecture decision
**What to do:** Read the reasoning. If it applies, reuse the decision instead of re-reasoning.

### 2. PROJECT_STATE
**What it is:** Where the project stands

**Example:**
```
PROJECT_STATE:
├─ Current phase: Week 1 (Foundation)
├─ Completed:
│  ├─ Signal API (coordinator_api.py)
│  ├─ Coordinator Service (coordinator_service.py)
│  └─ Integration tests (test_coordinator_foundation.py)
├─ In progress: [nothing currently]
├─ Next: Week 2 (Intelligence Layer)
└─ Blockers:
   ├─ Redis connection (MEDIUM) - file fallback works
   └─ No real agent integration (HIGH) - planned next week
```

**When to check:** At the start of your task
**What to do:** Understand where you fit in the timeline and what's blocking the critical path

### 3. AGENT_MANIFEST
**What it is:** Who's working on what right now

**Example:**
```
AGENT_MANIFEST:
├─ architect (Claude): COMPLETED
│  ├─ Designed Week 1-6 roadmap
│  └─ Identified hardware optimization strategy
├─ implementation (Claude): IN_PROGRESS
│  ├─ Building coordinator foundation
│  └─ 75% complete
├─ briefing_agent (Claude): QUEUED
│  └─ Starting after implementation phase
└─ optimization_agent (Claude): PLANNING
   └─ Will start Week 5
```

**When to check:** To see who you can ask for clarification
**What to do:** Know who did what before you. They're good sources of context.

### 4. BLOCKERS (Global)
**What it is:** Problems known to exist

**Example:**
```
BLOCKERS:
├─ CRITICAL: redis_unavailable
│  ├─ Age: Discovered Week 1 Day 2
│  ├─ Impact: HIGH (can't cache decisions in-memory)
│  ├─ Mitigation: File fallback fully functional
│  └─ Status: MONITORED
├─ MEDIUM: context_window_overflow
│  ├─ Age: Identified in planning
│  ├─ Impact: Agents could be cut off mid-context
│  ├─ Mitigation: Implementing aggressive compression
│  └─ Status: IN_PROGRESS
└─ LOW: performance_measurement
   ├─ Impact: Don't have real numbers yet
   ├─ Mitigation: Planning agent integration for measurement
   └─ Status: PLANNED
```

**When to check:** Before starting work, especially if it intersects with a known blocker
**What to do:** Work around or fix. Don't waste time on known problems.

### 5. BRIEFING (If handed off to you)
**What it is:** Summary of what previous agent did + what you need

**Example:**
```
BRIEFING: For implementation_agent
├─ From: architect
├─ Task: Build coordinator foundation
├─ Key decisions (relevant to you):
│  ├─ Use signal-based logging (approved)
│  ├─ Coordinator runs async (approved)
│  ├─ File fallback for Redis (approved)
│  └─ 5 more critical decisions...
├─ Blockers you should know:
│  ├─ Redis might not be available
│  ├─ Use file fallback (fully tested)
│  └─ No real agent integration yet
├─ Previous agent learned:
│  ├─ Signal-based is way more efficient
│  ├─ File logging is as good as Redis
│  └─ Coordinator overhead budget is critical
└─ Files to work from:
   ├─ STRATEGIC_ROADMAP_FRONTIER.md
   ├─ HARDWARE_OPTIMIZATION_BLUEPRINT.md
   └─ COMPLETE_SYSTEM_INTEGRATION.md
```

**When to check:** At the very start
**What to do:** Understand what you're building, why, and what constraints exist

---

## A Real Session Example

Let's walk through what a real session looks like:

### Phase 1: Startup (First 2 minutes)

```
[Agent initializes]

I'm now: implementation_agent
Starting task: Build coordinator API and service

[Read briefing]
Briefing found from architect:
├─ Task: Implement signal-based logging layer
├─ Architecture: Signal API + background Coordinator service
├─ Decisions: signal_based_logging, coordinator_async, file_fallback all approved
├─ Blockers: Redis might not work (use files)
└─ Priority: Get foundation working first

[Review decision cache]
Found 52 decisions already made:
├─ use_signal_based_logging (95% efficiency)
├─ coordinator_async (5% CPU)
├─ file_fallback_for_redis (available)
└─ 49 other decisions...

Status: I understand the task. Architecture is clear. No re-thinking needed.
```

### Phase 2: Working (15 minutes)

```
[Creating coordinator_api.py]

DECISION: Use dataclass-style structure for signals
├─ Reasoning: Ensures consistency, type-safe, easy to extend
├─ Outcome: All signals follow {timestamp, agent_id, signal_type, data} format
├─ Confidence: high
└─ Reversible: yes

[Implementing signal methods]

DECISION: Dual-write Redis and files
├─ Reasoning: Redis for speed if available, files for reliability if not
├─ Outcome: Try Redis first, auto-fallback to JSONL if failed
├─ Confidence: high
└─ Reversible: yes

[Hit a problem]

BLOCKER: Redis connection might not work
├─ Severity: high
├─ Description: Don't know if Redis server is running
├─ Impact: Can't test coordinator monitoring
└─ Workaround: Implementing file fallback. Will test with files.

[Continuing]

DECISION: Signal overhead target is <1ms
├─ Reasoning: System needs to be invisible. Agents shouldn't wait.
├─ Outcome: Optimize for speed. Log signals asynchronously.
├─ Confidence: medium (need to measure)
└─ Reversible: yes
```

### Phase 3: Completion (1 minute)

```
[Task finished]

COMPLETION: coordinator_api_implementation
├─ Success: yes
├─ Output:
│   ├─ coordinator_api.py (157 lines, fully tested)
│   ├─ API methods: action, decision, blocker, request_handoff, completion
│   ├─ Storage: Redis + file fallback
│   └─ Test file: test_coordinator_foundation.py
├─ Metrics:
│   ├─ Signal overhead: 0.2-0.5ms (under 1ms target)
│   ├─ Code coverage: 95%
│   └─ File fallback tested and working
└─ Learned:
   ├─ File logging is as reliable as Redis
   ├─ Dual-write is simple to implement
   ├─ Signal format is intuitive for agents
   └─ Test coverage caught several edge cases

[Generate briefing for next agent]

HANDOFF: briefing_generator_agent
├─ Task: Build intelligent briefing generation
├─ Context:
│   ├─ Signal API is complete and tested
│   ├─ Coordinator service monitors signals
│   ├─ Decision cache structure: {name: {outcome, reasoning, uses}}
│   ├─ Briefing should include: relevant_decisions + blockers + project_state
│   └─ File fallback is working (Redis optional)
├─ Blockers:
│   ├─ Redis might not be available
│   └─ No real agent integration yet (will test manually)
└─ Learned:
   ├─ Signal-based logging reduces overhead significantly
   ├─ Agents naturally understand the signal format
   ├─ File fallback works as well as Redis
   └─ Decision reuse potential is high (estimated 25-30%)
```

---

## Summary: How to Operate

1. **When you start:**
   - Read your briefing (if any)
   - Review decision cache
   - Check project state and blockers

2. **As you work:**
   - Emit DECISION signals for important choices
   - Emit BLOCKER signals for problems
   - Use brief, clear language (not verbose)

3. **When you're done:**
   - Emit COMPLETION signal
   - Document what you built and what you learned
   - System generates briefing for next agent

4. **If handing off:**
   - Emit HANDOFF signal
   - Include context next agent needs
   - Summarize blockers and learnings

---

## The Philosophy

This system is built on a few principles:

✅ **Signals, not prose** - Decisions, blockers, handoffs are short and structured
✅ **Reuse before reasoning** - Check if it's been decided before re-thinking
✅ **Transparency** - All work is observable and measurable
✅ **Simplicity** - Natural language, no special syntax needed
✅ **Scale** - Works with one agent or many; works with any model

You're not writing reports. You're communicating clearly enough that another agent can pick up your work without losing context.

---

**Ready to work? Initialize yourself and start.**

---

## Complete Agent Lifecycle Example

```python
from agent_init import initialize_and_load_context
from session_state import SessionState

# Step 1: Initialize (30ms, loads all context)
result = initialize_and_load_context("my_agent", task_keyword="implementation")
api = result["api"]
state = result["state"]

# Step 2: Check what context was loaded
briefing = api.get_startup_briefing()
if briefing:
    print(f"Task from previous agent: {briefing['task']}")

decisions = api.get_startup_decisions()
print(f"Found {len(decisions)} relevant past decisions")

# Step 3: Recover if crashed
if state.has_checkpoint():
    checkpoint = state.load_checkpoint()
    print(f"Resuming from {checkpoint['progress']}%")
    current_progress = checkpoint['progress']
else:
    current_progress = 0

# Step 4: Work (with context)
api.decision("use_redis", outcome="yes", reason="Faster than files")
api.action("build_coordinator", details={"files": 3})

# Step 5: Learn from experience
api.learning(
    experiment_name="redis_vs_files",
    what_tried="Tested Redis performance",
    expected_outcome="Redis faster",
    actual_outcome="Redis 50ms faster",
    success="yes",
    recommendation="Use Redis for performance-critical paths"
)

# Step 6: Checkpoint progress
current_progress = 50
state.save_checkpoint(
    task="Implementation Phase",
    progress=current_progress,
    blockers=["Connection timeout on Redis restart"],
    decisions_made=5
)

# Step 7: On completion, clear checkpoint
api.completion(success=True, output={"files": ["api.py", "service.py"]})
state.clear_checkpoint()
```

---

**Ready to work?**
```python
from agent_init import initialize_and_load_context
result = initialize_and_load_context("your_agent_id", "your_task")
```

That's it. You're initialized.
