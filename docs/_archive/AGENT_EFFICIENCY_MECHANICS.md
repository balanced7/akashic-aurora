# Agent Efficiency Mechanics
## How to Get 95% of Agent Tokens Spent on Work

**The Challenge**: Agents waste tokens on:
- Reading documentation
- Writing context summaries
- Logging actions narratively
- Catching up on history
- Searching for past decisions

**The Solution**: Make everything **push-based, not pull-based**

---

## Principle 1: Push Context, Don't Pull
### ❌ Current (Pull-Based)
```
Agent starts:
  "I need context, let me read bootstrap.md"
  "I need to read session history"
  "I need to check blockers"
  "I need to find past decisions"
  
  Token cost: High
  Cognitive load: High
  Delay: Noticeable
```

### ✅ Refined (Push-Based)
```
Coordinator starts:
  "New agent is starting, I'll push their briefing"
  
Agent starts:
  "Coordinator already prepared everything, here's what I need to know"
  
  Token cost: Minimal
  Cognitive load: Zero
  Delay: Instant
```

**Implementation**:
```python
# agent_startup.py
def on_agent_startup(agent_id, agent_type, project):
    """Agent calls this immediately"""
    briefing = coordinator.get_latest_briefing(agent_type, project)
    # Returns: {project_state, recent_decisions, current_blockers, your_role}
    # Token cost: < 1 minute
    return briefing
```

---

## Principle 2: Signal Logging, Not Narrative Logging

### ❌ Narrative (Expensive)
```python
log_action("""
I started the code review. I looked at the MCP interface design 
and compared it against the Redis communication patterns. The 
architecture looks good but I noticed that the error handling 
could be more robust. I'm thinking we should add retry logic...
""")
# Token cost: HIGH
# Human-readable: YES
# Machine-extractable: NO (buried in prose)
```

### ✅ Signal (Cheap)
```python
log.action("code_review_started", target="mcp_interface")
log.decision("add_retry_logic", reason="error_handling_robustness")
# Token cost: MINIMAL
# Human-readable: NO (Coordinator makes it so)
# Machine-extractable: YES (perfect for synthesis)
```

**Coordinator later synthesizes for humans:**
```markdown
## Code Review Session

**Action**: Reviewed MCP interface design
**Context**: Compared against Redis communication patterns

**Decision Made**: Add retry logic for error handling
**Rationale**: Increase robustness of error handling
**Related Decisions**: [prior decisions that align]
```

---

## Principle 3: Async Documentation Generation
### The Key: Coordinator Works While Agent Works

```
Timeline:

T=0:00    Agent starts work
T=0:01    Agent reads auto-pushed briefing
T=0:02    Agent begins work (115 minutes)
          Agent: coding/designing/reviewing
          Coordinator: [running in background]
          - Monitoring event stream
          - Extracting patterns
          - Synthesizing decisions
          - Updating project state
T=2:00    Agent requests handoff
          Coordinator immediately returns:
          - "Here's what you did"
          - "Here's the briefing for next agent"
          - "Would you like to adjust anything?"
T=2:05    Handoff to next agent
```

The work happens **in parallel**, not sequentially.

---

## Principle 4: Multi-Level Documentation

### Level 1: Raw Signals (Zero Agent Burden)
```json
{"event": "action", "action": "code_review", "target": "mcp_interface"}
{"event": "decision", "key": "retry_logic", "reason": "robustness"}
```

### Level 2: Synthesized Insights (Coordinator)
```json
{
  "agent_session": "claude_20260616_001",
  "title": "Code Review & Architecture Refinement",
  "duration_minutes": 120,
  "actions_taken": ["code_review", "architecture_refinement"],
  "decisions_made": [
    {
      "key": "retry_logic",
      "title": "Add Retry Logic for Error Handling",
      "rationale": "Increase robustness of error handling",
      "impact": "Moderate - improves reliability",
      "related_to": ["async_architecture_decision"]
    }
  ],
  "completion_percent": 45,
  "next_steps": ["implement_retry_logic"]
}
```

### Level 3: Human-Readable Brief (For Humans)
```markdown
# Code Review Session - Claude - Jun 16, 2:00 PM

## What Was Done
- Reviewed MCP interface design (1 hour)
- Verified alignment with Redis patterns (30 min)
- Identified robustness improvements (30 min)

## Key Decisions
1. **Add retry logic** for error handling
   - Makes system more resilient
   - Aligns with "reliable systems" principle

## Assessment
- Architecture: ✅ Sound
- Implementation: ⏳ Ready for OpenCode
- Risk level: Low

Next: OpenCode implements the retry logic design.
```

**Only the final level is written by human (Coordinator) for humans.**

---

## Principle 5: Smart Briefing Context Windows

### The Problem
```
If briefing is 1000 words, agent wastes 5 minutes reading
If briefing is 100 words, agent might miss critical context
```

### The Solution: Tiered Briefing
```python
briefing = {
    "urgent": [
        "Docker just failed, need restart",
        "Critical blocker: library conflict"
    ],
    "critical_context": [
        "Project is 45% complete",
        "Vision engine is next priority",
        "Use ZLUDA (already decided)"
    ],
    "background": {
        "full_history": "here",
        "all_decisions": "here",
        "available_if_agent_asks": True
    }
}
```

**Default briefing: 100 words (2 minutes)**  
**If agent wants details: Click → Expanded sections**

---

## Principle 6: Decision Caching to Prevent Rediscussing

### The Pattern
```
Apr 15: Claude decides "Use ZLUDA for vision"
May 3: OpenCode wonders "What about DirectML?"
May 5: Cursor asks "Why not pure ROCm?"
Jun 16: Claude returns, decides again "Use ZLUDA"

Token waste: Rediscussing same decision 4 times!
```

### Smart Coordinator Response
```python
def handle_decision_question(question):
    # "What about DirectML?"
    
    prior_decision = redis.get("decision:vision_engine_backend")
    if prior_decision and prior_decision['decided_for'] == 'zluda':
        return {
            "answered": True,
            "decided": "ZLUDA",
            "decided_on": "2026-04-15",
            "decided_by": "claude_20260415",
            "reasoning": ["Verified working with ComfyUI", 
                         "Florence-2 confirmed operational"],
            "alternatives_rejected": {
                "DirectML": "Tensor device mismatch",
                "Pure ROCm": "WSL2 limitation - no amdgpu kernel"
            },
            "revisit_if": ["Major new hardware acquired", 
                           "PyTorch changes support model"]
        }
    
    # Agent can now skip 10 minutes of rethinking
```

**Result**: Agent trusts prior decision, spends time on NEW problems.

---

## Principle 7: Context-Aware Logging Simplification

### Different Agents Need Different Log Depths

**Coordinator tracks**:
```python
agent_profiles = {
    "claude": {
        "log_depth": "high",  # Claude likes details
        "briefing_length": "detailed",
        "decision_template": "full_rationale"
    },
    "opencode": {
        "log_depth": "medium",  # OpenCode is practical
        "briefing_length": "executive_summary",
        "decision_template": "quick_why"
    },
    "cursor": {
        "log_depth": "low",  # Cursor just wants to code
        "briefing_length": "bullet_points",
        "decision_template": "tldr"
    }
}
```

When generating briefing for Cursor:
```
Briefing for Cursor (minimalist version)
- Project: akashic-aurora (45%)
- Your job: Implement retry logic (OpenCode's design)
- Key constraint: Use async/await pattern
- Blockers: None
- Questions? See full briefing in Redis
```

**Cursor spends 30 seconds reading vs 5 minutes.**

---

## Principle 8: One-Word Signals with Coordinator Expansion

### Agent's Signal
```python
log.action("code_review")
log.decision("retry_logic")
log.blocker("docker_timeout")
```

### Coordinator's Expansion
```python
# When next agent asks about it:
expanded = coordinator.expand_action("code_review")
# Returns: {
#   "action": "code_review",
#   "files_reviewed": ["mcp_interface", "redis_connection"],
#   "duration": 60,
#   "findings": ["robustness_issue", "performance_ok"],
#   "agent": "claude_20260616_001",
#   "timestamp": "..."
# }
```

**Agent logs with 1 word, Coordinator stores the context automatically.**

---

## Principle 9: Predictive Preparation

### Coordinator Anticipates
```python
def predict_next_needs(current_agent, current_task):
    """
    Current: Claude reviewing architecture
    
    Probable next:
    - OpenCode will implement
    - Will need: Function signatures, API contracts
    - Will hit: Dependency versioning issues (based on history)
    - Will ask: "How should I handle X?"
    
    So Coordinator prepares:
    """
    
    prep = {
        "probable_next_agent": "opencode",
        "probable_next_task": "implementation",
        "likely_dependencies": ["redis", "fastapi"],
        "likely_blockers": ["library_versioning"],
        "prior_solutions": ["pin to version 0.20.3"],
        "proactive_setup": [
            "requirements.txt already prepared",
            "Docker environment ready",
            "Testing framework configured"
        ]
    }
    
    return prep
```

When OpenCode starts, Coordinator has already:
- Prepared the requirements
- Set up the environment
- Documented likely issues
- OpenCode just codes

---

## Principle 10: Opportunistic Documentation

### Passive Documentation
```
Agent works
  ↓
Coordinator monitors
  ↓
Every 30 seconds, Coordinator extracts:
  - "Oh, they're working on vision engine"
  - "They just made a decision"
  - "They hit a blocker"
  
Coordinator writes this down
(Agent doesn't need to do anything)
```

### Active Opportunities
```
If agent calls log.blocker("X"), Coordinator immediately:
  1. Checks if we've solved X before
  2. If yes: Send solution to agent immediately
  3. If no: Extract it for next agent
  4. Offer: "Want help with this blocker?"
```

---

## Implementation: The Efficiency Dashboard

Coordinator maintains a real-time dashboard showing:
```
AGENT EFFICIENCY METRICS

Claude Session (2h duration):
  Total agent tokens: ~4000
  Tokens on work: ~3800 (95%)
  Tokens on overhead: ~200 (5%)
  
  Breakdown:
    - Actual coding: 45%
    - Thinking/designing: 35%
    - Decision making: 15%
    - Overhead: 5%
  
  Compared to: Previous sessions averaged 70% on work

OpenCode Session (3h duration):
  Total agent tokens: ~6000
  Tokens on work: ~5700 (95%)
  Tokens on overhead: ~300 (5%)
```

**This becomes your metric for "are we efficient?"**

---

## The Unified Logging API (Final Form)

All an agent ever needs:

```python
from coordinator import log, request_help, request_handoff

# Briefing pushed to you automatically
briefing = log.get_briefing()

# Logging (ultra-minimal)
log.action("what_i_did")
log.decision("key", reason="why")
log.blocker("issue", severity="high")
log.progress("update")

# Collaboration
request_help("expertise_needed", "what_help")
request_handoff("next_agent", "why_handing_off")

# Queries (if needed)
history = log.query("past_decisions", about="vision_engine")
status = log.get_project_status()
```

**That's literally the entire contract between agent and system.**

---

## Token Budget Example: Full Project Cycle

### Current State (Broken)
```
Agent 1 (4 hours):
  1h = Reading docs/history
  1h = Writing documentation
  2h = Actual work
  
Agent 2 (4 hours):
  1h = Reading docs/history
  1h = Writing documentation
  2h = Actual work
  
Total: 8 hours of agent time → 4 hours of real work
```

### With Coordinator System
```
Agent 1 (4 hours):
  5 min = Reading auto-pushed briefing
  10 min = Calling coordinator.log() 4 times
  3h 45 min = Actual work
  
Agent 2 (4 hours):
  5 min = Reading auto-pushed briefing
  10 min = Calling coordinator.log() 4 times
  3h 45 min = Actual work

Total: 8 hours of agent time → 7.5 hours of real work
(87.5% efficiency improvement)

Plus: Coordinator work (maybe 30 minutes total, async, maybe cheaper model)
```

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Tokens on work per session | 95% | ~60-70% |
| Agent onboarding time | 5 min | 30 min |
| Blocker resolution time | < 5 min | 30 min |
| Decision revisit rate | < 5% | ~40% |
| Context switch penalty | < 2 min | 10-15 min |
| Coordination overhead | < 5% | ~35% |

---

## Why This Works

1. **Coordinator is 24/7**, agent is bursty
   - Agent: "I work from 2-4pm"
   - Coordinator: "I'm watching all the time"
   - No sync needed, Coordinator is always ready

2. **Coordinator is deterministic**, agent is creative
   - Coordinator: Extract signals, synthesize patterns
   - Agent: Think, design, create, solve
   - Each doing what they're best at

3. **Signals are queryable**, narratives are not
   - `{"action": "code_review"}` → Easy to search
   - "I did a code review and..." → Hard to parse
   - Coordinator can build perfect briefings from signals

4. **Async means no waiting**
   - Agent doesn't wait for briefing generation
   - Briefing is ready before agent even starts
   - Zero latency perception

5. **Pattern matching scales**
   - 1 agent: Coordinator useful
   - 5 agents: Coordinator essential
   - 20 agents: Impossible without Coordinator

---

## In Summary

**The Coordinator Agent is your system's nervous system:**
- **Eyes**: Monitoring all agent activity
- **Brain**: Synthesizing patterns and context
- **Hands**: Preparing environment for next agent
- **Memory**: Storing decisions and learnings
- **Voice**: Creating briefings for next agent

**Working agents are your system's hands:**
- Focused solely on work
- Maximum creative capacity
- Minimal overhead
- Maximum velocity

**Result: A collaborative AI system that scales.**
