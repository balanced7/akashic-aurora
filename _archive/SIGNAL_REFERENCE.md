# Signal Reference: Complete Guide to Emissions
**Every type of signal you can emit, with examples**

---

## Overview

There are four signal types. Use them to communicate:

1. **DECISION** - You made a choice
2. **BLOCKER** - Something is stuck or uncertain
3. **HANDOFF** - Passing work to another agent
4. **COMPLETION** - Task is done

Each signal has a standard format. Use the format. Don't deviate.

---

## DECISION Signals

**When to use:** You made a meaningful choice about the system/architecture/approach

**Format:**
```
DECISION: {decision_name}
├─ Reasoning: {why_you_chose_this}
├─ Outcome: {what_you_chose}
├─ Confidence: {high | medium | low}
└─ Reversible: {yes | no}
```

**Field Explanations:**

- **decision_name**: Short, clear name. Example: `use_signal_based_logging`, `file_fallback_for_redis`
- **Reasoning**: Paragraph explaining the choice. Include:
  - What alternatives existed
  - Why you chose this one
  - What the impact is
  - Any assumptions
- **Outcome**: One sentence. The actual choice. Example: "Yes, use signal-based logging" or "No, use conversation-based logs"
- **Confidence**: `high` (certain), `medium` (pretty sure), `low` (uncertain but best guess)
- **Reversible**: `yes` (can change later), `no` (locked in)

**Examples:**

### Example 1: Architecture Decision

```
DECISION: signal_based_logging
├─ Reasoning: 
│   Agents can communicate in two ways:
│   1. Narrative prose (full explanation of everything they did)
│   2. Structured signals (decision, blocker, handoff, completion)
│   
│   Chose signals because:
│   ├─ Narrative uses ~200-300 tokens per action
│   ├─ Signals use ~20-40 tokens per action
│   ├─ Reduction is 8-10x more efficient
│   ├─ Signals are parseable by coordinator
│   ├─ Can't parse prose reliably
│   └─ System overhead drops from 30% to 5%
│   
│   Assumption: Agents can emit clear, structured signals
│   (Testing this right now with you)
├─ Outcome: Yes, implement signal-based logging
├─ Confidence: high
└─ Reversible: no (architectural foundation)
```

### Example 2: Technical Decision

```
DECISION: dual_write_redis_and_files
├─ Reasoning:
│   Redis is ideal for:
│   ├─ Speed (in-memory, microsecond latency)
│   ├─ Persistence (streams are easy to replay)
│   └─ Coordinator monitoring (real-time)
│   
│   But Redis might not be available:
│   ├─ Docker service currently down
│   ├─ WSL not available
│   ├─ Would hard-fail the whole system
│   
│   Solution: Dual-write
│   ├─ Try Redis first (if available: used for speed)
│   ├─ Always write to JSONL files (if Redis unavailable: fallback works)
│   ├─ Files are equally reliable for our use case
│   ├─ Coordinator can read both
│   └─ Graceful: no hard dependencies
├─ Outcome: Implement dual-write. Auto-fallback to files.
├─ Confidence: high
└─ Reversible: yes
```

### Example 3: Performance Decision

```
DECISION: context_window_7092_tokens
├─ Reasoning:
│   Claude's context window is 8192 tokens.
│   Must allocate tokens to:
│   ├─ System prompt (defines role): ~500 tokens
│   ├─ Session history (what happened before): ~3000 tokens
│   ├─ Task context (what I need to do now): ~1500 tokens
│   ├─ Working buffer (reasoning space): ~500 tokens
│   └─ Safety margin (prevent overflow): ?
│   
│   Calculation:
│   ├─ Available: 8192 tokens
│   ├─ Allocated: 500 + 3000 + 1500 + 500 = 5500 tokens
│   ├─ Safety margin: 8192 - 5500 = 2692 tokens
│   ├─ But we need efficiency: 7092 token budget (87% of 8192)
│   ├─ This leaves 1100 tokens safety (13%)
│   └─ Sufficient for unexpected expansion
│   
│   Why 7092 and not higher?
│   ├─ Leave 13% safety margin (prevents crashes)
│   ├─ Allows aggressive context compression
│   ├─ Prioritizes recent, high-signal tokens
│   └─ Tested to fit all necessary context
├─ Outcome: 7092 token budget per agent session
├─ Confidence: medium (needs real testing)
└─ Reversible: yes
```

### Example 4: Implementation Decision

```
DECISION: coordinator_async_background
├─ Reasoning:
│   Coordinator could work two ways:
│   1. Synchronous: agents wait for briefings/cache lookups
│      └─ Adds latency, agents blocked
│   2. Asynchronous: coordinator works in background
│      └─ Agents never wait, coordinator catches up
│   
│   Chose async because:
│   ├─ Agents are primary, coordinator is support
│   ├─ Agents shouldn't be blocked by coordination overhead
│   ├─ Coordinator must be invisible (<5% CPU)
│   ├─ Background monitoring is more efficient
│   ├─ Graceful degradation: coordinator failure doesn't crash system
│   └─ Testing will show if this works
├─ Outcome: Coordinator runs as background thread/process
├─ Confidence: high
└─ Reversible: yes
```

---

## BLOCKER Signals

**When to use:** You hit an obstacle, something is uncertain, or something is missing

**Format:**
```
BLOCKER: {blocker_name}
├─ Severity: {low | medium | high}
├─ Description: {what's_the_problem}
├─ Impact: {how_it_affects_your_task}
└─ Workaround: {how_you're_handling_it_or_plan_to}
```

**Field Explanations:**

- **blocker_name**: Short name. Example: `redis_unavailable`, `context_window_might_overflow`
- **Severity**: 
  - `low` - Nice to fix, but doesn't block work
  - `medium` - Affects work, but there's a workaround
  - `high` - Blocks critical path, no easy workaround
- **Description**: What's the actual problem? Be specific.
- **Impact**: How does this affect you? What can't you do?
- **Workaround**: How are you handling it? Can other agents avoid this?

**Examples:**

### Example 1: Infrastructure Blocker

```
BLOCKER: redis_connection_failing
├─ Severity: high
├─ Description:
│   Tried to connect to Redis on localhost:6379.
│   Connection timeout after 2 seconds.
│   Redis service probably not running.
│   Docker service status is unclear.
├─ Impact:
│   ├─ Can't test coordinator monitoring with real streams
│   ├─ Can't verify decision cache is working
│   ├─ Entire system fails if we hard-require Redis
│   └─ Blocks architecture validation
└─ Workaround:
   ├─ Implementing file-based JSONL fallback
   ├─ Dual-write: Redis if available, files if not
   ├─ Files are equally reliable
   ├─ Coordinator can read both
   └─ Fallback tested and working
```

### Example 2: Design Uncertainty

```
BLOCKER: vram_management_unproven
├─ Severity: medium
├─ Description:
│   Hardware optimization blueprint assumes Llama 8B
│   (4.2GB) + KV cache (3GB) can be managed dynamically.
│   Haven't actually tested loading/unloading models
│   under real conditions.
├─ Impact:
│   ├─ Week 3 (local reasoning) depends on this
│   ├─ If not possible: architecture needs redesign
│   ├─ If possible: unlocks 70% cost reduction
│   └─ Can't commit to timeline without proof
└─ Workaround:
   ├─ Building conservative estimates
   ├─ Planning to test in Week 3
   ├─ Will iterate if assumptions wrong
   └─ Have cloud API fallback if local fails
```

### Example 3: Process Uncertainty

```
BLOCKER: no_real_agent_integration_tested
├─ Severity: high
├─ Description:
│   Entire framework is designed theoretically.
│   No real agent has used the signal API yet.
│   Don't know if framework is actually learnable.
│   Don't know if signals are clear enough.
│   Don't know if context format makes sense.
├─ Impact:
│   ├─ Everything from Week 2 onward is based on assumptions
│   ├─ Could discover major design flaws mid-build
│   ├─ Could waste time building wrong things
│   ├─ Can't measure real impact of system
│   └─ Can't verify token savings claims
└─ Workaround:
   ├─ Testing framework with real usage (you, right now)
   ├─ Reporting what works and what doesn't
   ├─ Iterating based on real feedback
   ├─ Won't move to Week 2 until validated
   └─ Using you to test before generalizing
```

### Example 4: Technical Limitation

```
BLOCKER: context_window_might_overflow
├─ Severity: medium
├─ Description:
│   Total tokens needed might exceed 8192 limit:
│   ├─ System prompt: 500 tokens
│   ├─ Session history: 3000-5000 tokens (variable)
│   ├─ Task context: 1500 tokens
│   ├─ Briefing (if handoff): 500-1000 tokens
│   ├─ Working buffer: 500 tokens
│   └─ Total: Could be 6500-8500 tokens
│   
│   If we exceed 8192, context gets cut off,
│   losing important information.
├─ Impact:
│   ├─ Agents lose context mid-session
│   ├─ Decisions or history might be cut
│   ├─ Quality of work could degrade
│   └─ Defeats purpose of briefing system
└─ Workaround:
   ├─ Allocate 7092-token budget (87% of limit)
   ├─ Implement aggressive context compression
   ├─ Prioritize recent, high-signal tokens
   ├─ Remove low-importance context
   ├─ Leave 13% safety margin
   └─ Will test with real sessions to verify
```

---

## HANDOFF Signals

**When to use:** You're handing your task to another agent

**Format:**
```
HANDOFF: {next_agent}
├─ Task: {what_they_should_do}
├─ Context: {what_they_need_to_know}
├─ Blockers: {what_you_couldn't_solve}
└─ Learned: {what_they_should_know}
```

**Field Explanations:**

- **next_agent**: Who's taking over. Example: `implementation_agent`, `briefing_generator_agent`
- **Task**: One sentence. What should they do?
- **Context**: What do they need to know?
  - Key decisions made
  - Architecture approved
  - Files created
  - Current state
- **Blockers**: What's blocking the path forward?
  - What you discovered
  - What you couldn't solve
  - Workarounds
- **Learned**: What did you learn that helps them?
  - Approaches that worked
  - Approaches that didn't
  - What to prioritize

**Examples:**

### Example 1: Phase-to-Phase Handoff

```
HANDOFF: implementation_agent
├─ Task: 
│   Build coordinator_api.py (signal-based logging API) 
│   and coordinator_service.py (background monitoring service)
│
├─ Context:
│   ARCHITECTURE APPROVED:
│   ├─ Signal-based logging (decision, blocker, handoff, completion)
│   ├─ Async coordinator (background monitoring, <5% CPU)
│   ├─ Decision cache (prevent re-reasoning)
│   ├─ File fallback for Redis (dual-write)
│   └─ 7092-token context budget per session
│   
│   DECISIONS MADE:
│   ├─ signal_based_logging: Yes (95% efficiency target)
│   ├─ coordinator_async: Yes (background, non-blocking)
│   ├─ file_fallback: Yes (use files if Redis unavailable)
│   ├─ decision_cache_structure: {name: {outcome, reasoning}}
│   └─ 11 more architectural decisions...
│   
│   EXAMPLES TO BUILD FROM:
│   ├─ Signal API should be: log.decision(), log.blocker(), etc.
│   ├─ Signals should be: struct with {timestamp, agent_id, data}
│   ├─ Coordinator should monitor: agent:events Redis stream
│   ├─ File format should be: JSONL (one signal per line)
│   └─ Test file: test_coordinator_foundation.py
│   
│   FILES YOU'LL CREATE:
│   ├─ coordinator_api.py (~150-200 lines)
│   ├─ coordinator_service.py (~250-350 lines)
│   ├─ test_coordinator_foundation.py (comprehensive tests)
│   └─ WEEK_1_FOUNDATION_DELIVERED.md (summary)
│
├─ Blockers:
│   ├─ redis_unavailable
│   │  ├─ Severity: HIGH
│   │  ├─ Workaround: Use JSONL files. Dual-write tested.
│   │  └─ Action: Implement fallback in API
│   │
│   ├─ context_window_might_overflow
│   │  ├─ Severity: MEDIUM
│   │  ├─ Workaround: Aggressive compression planned
│   │  └─ Action: Test context limits as you build
│   │
│   └─ no_real_integration_tested
│      ├─ Severity: HIGH
│      ├─ Workaround: Comprehensive test file
│      └─ Action: Write tests that validate real use
│
└─ Learned:
   ├─ Signal-based approach reduces tokens massively
   ├─ Agents naturally emit signals in reasonable format
   ├─ File-based logging is as good as Redis
   ├─ Coordinator overhead must be invisible
   ├─ Test coverage prevents bugs later
   ├─ Single signal API (initialize, then log.*) is clean
   └─ Implementation should focus on reliability over features
```

### Example 2: Task-to-Task Handoff

```
HANDOFF: framework_testing_agent
├─ Task:
│   Test if the onboarding framework is learnable by any model.
│   Use it to do a real task. Report what works and what doesn't.
│
├─ Context:
│   YOU HAVE THREE NEW DOCUMENTS:
│   ├─ AGENT_ONBOARDING.md (how to use the system)
│   ├─ CONTEXT_SCHEMA.md (what context looks like)
│   └─ SIGNAL_REFERENCE.md (all signal types)
│   
│   THE GOAL:
│   ├─ Read these three documents
│   ├─ Use them to do a real task
│   ├─ Emit signals as you work
│   ├─ Report if it was easy, hard, or confusing
│   ├─ Identify what needs fixing
│   └─ Prove the framework is learnable
│   
│   REAL TASK FOR YOU:
│   ├─ You are now: framework_testing_agent
│   ├─ Your job: Use the framework to test itself
│   ├─ Report: What's clear? What's confusing?
│   ├─ Measure: Can you understand and use it naturally?
│   └─ Output: Feedback to improve the documents
│
├─ Blockers:
│   ├─ Framework not yet tested with real usage
│   │  ├─ Severity: MEDIUM
│   │  ├─ Impact: Don't know if it's learnable
│   │  └─ Your job: Find out
│   │
│   └─ Cross-model compatibility unknown
│      ├─ Severity: MEDIUM
│      ├─ Impact: Don't know if works with non-Claude models
│      └─ Your job: Test with me (Claude), document findings
│
└─ Learned:
   ├─ Framework is meant to be self-explanatory
   ├─ It should be learnable without training
   ├─ Signal format is intentionally simple
   ├─ Context schema is intentionally readable
   ├─ If you find something confusing, it needs fixing
   └─ Your honest feedback is critical for iteration
```

---

## COMPLETION Signals

**When to use:** Your task is finished (success or failure)

**Format:**
```
COMPLETION: {task_name}
├─ Success: {yes | no}
├─ Output: {what_you_produced}
├─ Metrics: {how_well_you_did}
└─ Learned: {what_you'd_do_differently}
```

**Field Explanations:**

- **task_name**: The task you were assigned. Example: `coordinator_api_implementation`
- **Success**: Did you complete it successfully?
- **Output**: What did you build/produce?
- **Metrics**: Quantify success. Examples:
  - Lines of code
  - Test coverage
  - Performance measurements
  - Quality metrics
  - Time to completion
- **Learned**: What did you learn?
  - What went well
  - What was harder than expected
  - What you'd do differently
  - Insights for next agent

**Examples:**

### Example 1: Implementation Completion

```
COMPLETION: coordinator_api_implementation
├─ Success: yes
├─ Output:
│   ├─ coordinator_api.py (157 lines)
│   ├─ Complete signal-based logging API
│   ├─ Methods: action(), decision(), blocker(), request_handoff(), completion()
│   ├─ Dual storage: Redis + JSONL files
│   ├─ Auto-fallback when Redis unavailable
│   ├─ Test file: test_coordinator_foundation.py
│   └─ All tests passing
├─ Metrics:
│   ├─ Signal overhead: 0.2-0.5ms per signal
│   ├─ Code coverage: 95%
│   ├─ Lines per function: average 12
│   ├─ Time to completion: 2 hours
│   ├─ Bugs found in testing: 3 (all fixed)
│   └─ Ready for integration: yes
└─ Learned:
   ├─ File-based logging is as reliable as Redis
   ├─ Dual-write adds <10% complexity
   ├─ Comprehensive tests catch bugs early
   ├─ Signal format is intuitive for agents
   ├─ Async file writes are important (don't block)
   ├─ Error handling is critical
   └─ Documentation matters (helped next agent understand quickly)
```

### Example 2: Design Completion

```
COMPLETION: hardware_optimization_analysis
├─ Success: yes
├─ Output:
│   ├─ HARDWARE_OPTIMIZATION_BLUEPRINT.md
│   │  ├─ Exact VRAM allocation (4.2GB Llama + 3GB KV cache + ...)
│   │  ├─ Exact RAM allocation (8GB OS + 8GB models + 4GB Redis + ...)
│   │  ├─ Context window optimization (7092 tokens)
│   │  └─ Full Python code for memory managers
│   ├─ COMPLETE_SYSTEM_INTEGRATION.md
│   │  ├─ Memory layout during operations
│   │  ├─ Timing analysis (850ms per session)
│   │  ├─ Failure scenarios and recovery
│   │  └─ Health monitoring framework
│   └─ Verified calculations mathematically
├─ Metrics:
│   ├─ Token efficiency achievable: 95% (vs 65% baseline)
│   ├─ Cost reduction: 10x cheaper than cloud
│   ├─ Speed improvement: 6x faster with optimizations
│   ├─ VRAM peak usage: 30% (5.8GB headroom)
│   ├─ RAM typical usage: 34% (30GB available)
│   ├─ Coordinator overhead: <200MB, <5% CPU
│   └─ Confidence: high (math verified, assumptions documented)
└─ Learned:
   ├─ Video-game level optimization is possible
   ├─ Every GB must be accounted for
   ├─ Graceful degradation requires planning
   ├─ Documentation is critical for complex systems
   ├─ Getting the allocation right prevents panic later
   ├─ Conservative estimates are better than optimistic
   └─ Next phase (implementation) should test assumptions
```

### Example 3: Test/Validation Completion

```
COMPLETION: framework_learnability_testing
├─ Success: yes (with minor issues to fix)
├─ Output:
│   ├─ Tested AGENT_ONBOARDING.md
│   │  ├─ Used signals to do real task
│   │  ├─ Could understand all signal types
│   │  ├─ Found: one section was confusing (fixed)
│   │  └─ Found: missed one signal type in examples (added)
│   ├─ Tested CONTEXT_SCHEMA.md
│   │  ├─ Could read and understand all context types
│   │  ├─ Format is clear and scannable
│   │  └─ No issues found
│   ├─ Tested SIGNAL_REFERENCE.md
│   │  ├─ Examples are comprehensive
│   │  ├─ Format is consistent
│   │  └─ Easy to reference while working
│   └─ FRAMEWORK_TESTING_REPORT.md (detailed findings)
├─ Metrics:
│   ├─ Learnability: high (understood without training)
│   ├─ Clarity: 95% (one section needed improvement)
│   ├─ Completeness: 90% (one signal type underexplained)
│   ├─ Usability: high (used naturally while working)
│   ├─ Cross-model feasibility: high (framework is model-agnostic)
│   └─ Ready to generalize: yes
└─ Learned:
   ├─ Framework is very learnable
   ├─ Signal format is natural for agents
   ├─ Context schema needs one small clarification
   ├─ Examples help more than abstract descriptions
   ├─ Real usage testing caught issues theory missed
   ├─ Framework is ready for generalization
   ├─ Next step: test with non-Claude models
   └─ Cross-model compatibility likely (framework is language-neutral)
```

---

## Signal Guidelines

### Do's ✅

- ✅ **Be clear and specific** - "redis_unavailable" not "something's broken"
- ✅ **Include reasoning** - Future agents need to understand why
- ✅ **Be honest** - Report both what works and what doesn't
- ✅ **Be concise** - Detailed but not verbose
- ✅ **Use examples** - Real examples are clearer than abstract descriptions
- ✅ **Document assumptions** - What did you assume that might be wrong?
- ✅ **Report metrics** - Quantify success, not just "it works"
- ✅ **Explain impact** - Why does this decision/blocker matter?

### Don'ts ❌

- ❌ **Don't be vague** - "improved efficiency" (by how much?)
- ❌ **Don't skip reasoning** - Why is this decision better?
- ❌ **Don't hide problems** - Report blockers even if you work around them
- ❌ **Don't use jargon** - Write for other agents to understand
- ❌ **Don't make assumptions** - State what you assume explicitly
- ❌ **Don't skip details** - Next agent needs specifics to learn
- ❌ **Don't emit signals unnecessarily** - Every signal should matter

### Examples of GOOD vs BAD Signals

#### GOOD Signal Example:
```
DECISION: use_llama_for_local_reasoning
├─ Reasoning:
│   ├─ Hardware supports it (16GB VRAM, 8.8GB available)
│   ├─ Local inference saves API costs
│   ├─ Measured speed: ~5 tokens/sec on ZLUDA
│   └─ Assumption: VRAM remains available for other work
├─ Outcome: Yes, implement local Llama inference
├─ Confidence: high
└─ Reversible: yes (can fall back to cloud API)
```
**Why this is good:**
- Specific reasoning (not "seemed good")
- Quantified measurements (5 tokens/sec, 8.8GB)
- Clear outcome (yes/no, not "maybe")
- Reasonable confidence (high, not contradictory)
- Future agents can reuse this decision

#### BAD Signal Example:
```
DECISION: use_llama
├─ Reasoning: Seemed like a good idea
├─ Outcome: Maybe? Not sure yet
├─ Confidence: low
└─ Reversible: no
```
**Why this is bad:**
- Vague reasoning ("seemed like a good idea" doesn't explain why)
- Uncertain outcome ("Maybe?" is not a decision)
- Contradictory (Confidence=low + Reversible=no doesn't make sense)
- Other agents can't reuse this (too vague)
- Creates confusion instead of clarity

#### GOOD Blocker Example:
```
BLOCKER: vram_allocation_uncertain
├─ Severity: medium
├─ Description: Don't know exact VRAM requirements for Llama 8B quantized. Estimated 4.2GB based on specs, but need real measurement.
├─ Impact: Can't commit to local inference without testing. Could overflow VRAM if estimates are wrong.
└─ Workaround: Using conservative estimate (5GB allocated). Will test in Week 3 with actual loading.
```
**Why this is good:**
- Specific about what's unknown
- Explains why it matters (could overflow)
- Has a workaround (not blocking progress)
- Next agent knows what to test

#### BAD Blocker Example:
```
BLOCKER: something_might_break
├─ Severity: high
├─ Description: Something could be wrong
├─ Impact: Bad things might happen
└─ Workaround: Hope it doesn't happen
```
**Why this is bad:**
- "Something might break" tells next agent nothing
- No specifics (what thing? how might it break?)
- No actual workaround (hoping is not a plan)
- Creates anxiety without actionable information

### Signal Volume

- ~3-5 signals per hour of work is typical
- Too few: next agent doesn't understand what you did
- Too many: noise, not useful
- Right amount: every signal conveys important information

---

## Next Steps

1. **Read these documents** - Especially AGENT_ONBOARDING.md first
2. **Do a real task** - Using the framework as described
3. **Emit signals** - As you work, emit signals naturally
4. **Report findings** - What worked? What didn't?
5. **Document feedback** - What needs improving in the framework?

Then we iterate based on your real experience.
