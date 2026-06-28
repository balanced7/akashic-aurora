# Coordinator Agent: The System Supervisor
## Maximizing Agent Tokens for Work While Maintaining Rigor

**Core Insight**: Stop asking agents to document. Instead, have a dedicated **Coordinator Agent** that:
1. **Observes** what agents are doing (passively)
2. **Extracts** meaningful signals automatically
3. **Synthesizes** context for the next agent
4. **Orchestrates** handoffs and continuity
5. **Escalates** blockers and decisions

---

## The Token Economics Problem

### Current (Broken) Approach
```
Agent's 2-hour session:
  5 min  reading docs (token cost)
  10 min reading history (token cost)
  30 min actual work (actual value)
  45 min documenting (token cost!)
  30 min writing decision logs (token cost!)
  ────────────────────
  → 45% of tokens spent on admin overhead
  → Only 30/120 minutes on actual work
  → Friction discourages detailed logging
```

### Proposed Coordinator Approach
```
Agent's 2-hour session:
  1 min   read coordinator's briefing (low cost)
  1 min   call coordinator_log("event_type", "data") (ultra-minimal)
  115 min actual work (95% of session)
  3 min   request_handoff(next_agent) (low cost)
  ────────────────────
  → 5% overhead
  → 115/120 minutes on actual work
  → Coordinator handles all synthesis asynchronously
```

---

## Architecture: Three-Tier System

### Tier 1: Working Agents (Claude, OpenCode, Cursor)
**Goal**: Do work, minimize overhead

**Logging Contract** (ultra-minimal):
```python
# All an agent needs:
coordinator.log({
    "event": "action_start",
    "action": "code_review",
    "context": "architecture.md"
})

coordinator.log({
    "event": "decision",
    "key": "use_zluda_for_vision",
    "reason": "comfyui_verified_working"
})

coordinator.log({
    "event": "blocker",
    "blocker": "docker_not_running",
    "severity": "critical"
})

coordinator.log({
    "event": "handoff_request",
    "to_agent": "opencode",
    "reason": "needs_cli_implementation"
})
```

**That's it.** No narratives, no essays, no detailed logging. Just signals.

### Tier 2: Coordinator Agent (Background Process)
**Goal**: Handle all system administration

**Responsibilities**:

#### 2a. Passive Monitoring
```python
class CoordinatorAgent:
    def monitor_agent_activity(self):
        """Continuously watch Redis for agent signals"""
        while True:
            # Read from agent:events stream
            events = redis.xread('agent:events', count=10)
            
            for event in events:
                self.process_event(event)
            
            sleep(1)  # Run constantly but don't hammer
    
    def process_event(self, event):
        """Auto-extract meaning from signals"""
        if event['type'] == 'action_start':
            self.enrich_action(event)
            self.update_manifest(event)
        
        elif event['type'] == 'decision':
            self.synthesize_decision(event)
            self.extract_learnings(event)
        
        elif event['type'] == 'blocker':
            self.evaluate_blocker(event)
            self.check_for_best_agent_for_help(event)
        
        elif event['type'] == 'handoff_request':
            self.prepare_handoff(event)
```

#### 2b. Auto-Documentation Synthesis
```python
def synthesize_decision(self, decision_signal):
    """
    Agent logged:
    {"event": "decision", "key": "use_zluda", "reason": "verified_working"}
    
    Coordinator synthesizes to:
    """
    decision_doc = {
        "id": "decision_20260616_001",
        "agent_id": event['agent_id'],
        "decision": "Use ZLUDA for vision engine integration",
        "reason": ["ComfyUI implementation verified working",
                   "Florence-2 confirmed operational with ZLUDA"],
        "alternatives_rejected": ["DirectML", "Pure ROCm"],
        "project_impact": "Enables GPU-accelerated OCR/captioning",
        "timestamp": now(),
        "derivation": "auto_synthesized_from_signals",
        "confidence": "high"
    }
    
    redis.hset('learning:decisions', mapping=decision_doc)
    
    # Also log to structured format for next agent
    this_project_decisions.append(decision_doc)
```

#### 2c. Context Synthesis for Next Agent
```python
def prepare_handoff(self, handoff_request):
    """
    When agent requests handoff, coordinator prepares briefing:
    """
    
    from_agent = handoff_request['agent_id']
    to_agent_type = handoff_request['to_agent']
    project = redis.get('project:current')
    
    # Gather what happened
    session_events = self.get_session_events(from_agent)
    decisions = self.extract_decisions(session_events)
    blockers = self.extract_blockers(session_events)
    progress = self.calculate_progress(session_events)
    
    # Synthesize into briefing
    briefing = {
        "timestamp": now(),
        "for_agent": to_agent_type,
        "project": project,
        "from_agent": from_agent,
        
        "what_was_done": self.summarize_work(session_events),
        "key_decisions": decisions,
        "current_blockers": blockers,
        "progress": progress,
        
        "your_role": self.suggest_next_role(to_agent_type),
        "estimated_effort": "2-4 hours",
        
        "critical_context": [
            "Docker restored and working",
            "Redis HA cluster online",
            "Vision engine ready for integration"
        ]
    }
    
    redis.set(f'handoff:{to_agent_type}:latest', json.dumps(briefing))
    return briefing
```

#### 2d. Blocker Escalation
```python
def evaluate_blocker(self, blocker_signal):
    """
    Agent logged: {"event": "blocker", "blocker": "docker_not_running"}
    
    Coordinator decides:
    - Can we help? (Try to fix)
    - Should we call someone? (Request help from specialized agent)
    - Is this a pattern? (Have we seen this before?)
    """
    
    severity = blocker_signal.get('severity', 'normal')
    blocker_type = blocker_signal['blocker']
    
    # Check if we've solved this before
    prior_solution = redis.get(f'solution:{blocker_type}')
    if prior_solution:
        # Send to agent immediately
        send_help_message(blocker_signal['agent_id'], prior_solution)
        log_blocker(blocker_signal, status='resolved_via_prior')
        return
    
    # If critical, maybe we need specialized help
    if severity == 'critical':
        best_agent = find_best_agent_for(blocker_type)
        broadcast_help_request(blocker_type, best_agent)
```

#### 2e. Manifest & Status Updates
```python
def update_manifest(self, event):
    """
    Agent logs an action, coordinator updates the manifest
    This is ZERO burden on the agent
    """
    
    agent_manifest = {
        "agent_id": event['agent_id'],
        "status": "busy",  # or "idle", "blocked", etc
        "current_task": event.get('action'),
        "project": redis.get('project:current'),
        "last_update": now(),
        "on_milestones": self.detect_milestones(event),
        "performance": self.calculate_performance()
    }
    
    redis.hset(f"agent:{event['agent_id']}:manifest", 
               mapping=agent_manifest)
    
    # Broadcast status to dashboard
    broadcast_status_update(agent_manifest)
```

### Tier 3: Project State Machine
**Coordinator continuously maintains**:
```
project:state
  └─ current_phase
  └─ completion_percent
  └─ blockers (auto-extracted from blocker signals)
  └─ milestone_status
  └─ agent_history (who worked when)
  └─ decision_timeline
  └─ last_5_decisions
  └─ critical_context
```

**This state is AUTOMATICALLY UPDATED** from agent signals. No agent asks permission.

---

## Logging Contract: Ultra-Minimal API

Working agents just call:

```python
from coordinator import log, request_help, request_handoff

# Start of work
log.action("vision_engine_integration", context="architecture_review")

# During work - minimal
log.progress("designed_mcp_interface")

# A decision
log.decision("use_websockets_for_comfyui", reason="real_time_status")

# Stuck?
log.blocker("docker_service_fails_to_start", severity="critical")

# Need help?
request_help(expertise="devops", task="docker_troubleshooting")

# Done, ready for next
request_handoff(to_agent="opencode", reason="needs_implementation")
```

**Token cost: < 1 minute of the entire session**

---

## What Coordinator Does In Background

| Task | Timing | Benefit |
|------|--------|---------|
| Monitor events stream | Every 1 sec | Real-time status |
| Synthesize decisions | Event-driven | Captures context automatically |
| Extract learnings | After each action | Builds knowledge base |
| Prepare briefings | Before handoff | Next agent gets perfect context |
| Update manifest | Real-time | Dashboard always current |
| Track milestones | Event-driven | Auto-detect progress |
| Escalate blockers | Event-driven | Fast problem resolution |
| Generate summaries | Batch nightly | For next day's briefing |

---

## The Briefing an Agent Receives (Auto-Generated by Coordinator)

```markdown
# Your Mission Brief: akashic-aurora (Vision Engine Integration)

## What Just Happened
OpenCode worked for 4 hours and:
- ✅ Restored Docker service
- ✅ Started Redis HA cluster  
- ✅ Verified MCP server connectivity
- ⏳ Started vision engine architecture design

## Key Decisions Made
1. **Use ZLUDA for GPU acceleration**
   - Why: ComfyUI already verified, Florence-2 working
   - Alternatives: DirectML (rejected - tensor mismatch), Pure ROCm (rejected - WSL limitation)

2. **Use WebSocket for ComfyUI API**
   - Why: Real-time status updates needed
   - Cost: Extra complexity in MCP server

## Blockers Encountered
- Docker initially down (FIXED by restoring service)
- WSL Ubuntu-Migrate unavailable (DEFERRED - not critical path)

## Your Role
**Architecture Review** - You're Claude, the architect.

Your job: Review OpenCode's design and suggest improvements.
Expected effort: 2-4 hours

## What's Ready for You
- ComfyUI-ZLUDA cloned and ready at E:\AI-Setup\ComfyUI-Zluda
- Florence-2 model available
- MCP server framework ready
- Redis fully operational

## Critical Context
```
Project: akashic-aurora
Completion: 45% → Expected 60% after this session
Hardware: AMD 9950X3D + RX 9070 XT
Timeline: Started Apr 15, multiple agents have iterated
Vision: Build multi-agent collaborative system (that's what you're in!)
```

## What to Do First
1. Read: E:\AI-Setup\ARCHITECTURE.md (updated by OpenCode)
2. Check: E:\AI-Setup\vision_engine_comfy.py (preliminary design)
3. Review: Redis learning:decisions for past architecture decisions
4. Then: Begin your code review

---

Generated by: Coordinator Agent  
From: OpenCode session (2026-06-16 04:00:00)  
To: Claude (2026-06-16 12:00:00)  
```

**This briefing took Coordinator 2 minutes to auto-generate from raw signals.**

---

## Implementation Strategy: Three Phases

### Phase 1: Signal-Based Logging (Week 1)
Create ultra-minimal logging API that agents use:
```python
# coordinator.py - That's all agents need to import
def log(event_type: str, **kwargs):
    """Ultra-simple logging"""
    redis.xadd('agent:events', {'type': event_type, **kwargs})

def request_help(expertise: str, task: str):
    redis.lpush('collaboration:help_requests', 
                json.dumps({'expertise': expertise, 'task': task}))

def request_handoff(to_agent: str, reason: str):
    redis.xadd('collaboration:handoff_queue',
               {'from': current_agent_id(), 'to': to_agent, 'reason': reason})
```

### Phase 2: Coordinator Process (Week 2)
Create background coordinator that monitors and synthesizes:
```python
# coordinator_service.py - Runs as separate process
class CoordinatorService:
    def run(self):
        while True:
            self.monitor_agent_activity()
            self.synthesize_decisions()
            self.update_project_state()
            self.check_for_blockers()
            sleep(1)
```

Can run as:
- Background Python process
- Cron job every minute
- MCP tool called on-demand
- Hybrid (runs in background, also callable)

### Phase 3: Auto-Briefing Generation (Week 3)
Create briefing generator that creates context for next agent:
```python
# briefing_generator.py
def generate_briefing_for_agent(agent_type: str):
    """
    Called when agent starts.
    Returns auto-generated, perfectly contextualized briefing.
    """
    ...
```

---

## Cost Analysis: Coordinator Agent

**Key insight**: Coordinator can be **cheaper/smaller model** than working agents

### Option A: Async Background (Best)
```
Working Agents: Claude (big, expensive) ← Do actual work
Coordinator: Running constantly in background ← Can be smaller, cheaper model
Cost: Maybe $0.50/day for coordinator
Benefit: Zero friction on working agents
```

### Option B: On-Demand (Good)
```
Coordinator runs when:
- Agent calls request_handoff()
- Nightly summary generation
- Blocker escalation
Benefit: Only pays when needed
```

### Option C: Hybrid (Best for budget)
```
- Background process runs every 1 minute (cheap)
- On-demand when agents call functions
- Nightly comprehensive synthesis (batch)
Cost: Very low, benefit: immediate + comprehensive
```

---

## Scaling to Multiple Agents

### Single Agent
```
Agent ─→ Log signal ─→ Coordinator ─→ Next briefing
```

### Two Agents in Parallel
```
OpenCode ─┐
          ├─→ Coordinator ─→ Orchestrates both
Claude   ─┘

Coordinator sees:
- OpenCode doing "infrastructure setup"
- Claude doing "architecture review"
- Can detect: "OpenCode needs help from Claude"
- Can request: "Claude, OpenCode blocked on Docker"
```

### Three Agents (Future)
```
Cursor   ─┐
OpenCode ├─→ Coordinator ─→ Full multiagent orchestra
Claude   ─┘

Coordinator can:
- Detect when multiple agents need same blocker fixed
- Assign: "Cursor, can you refactor for testability?"
- Detect: "Claude and OpenCode disagree on architecture"
- Escalate: "Need human decision on vision engine approach"
```

---

## The Coordinator's "Intelligence"

### Pattern Recognition
```python
# Coordinator learns patterns
if blocker_type == "docker_not_running":
    # We've seen this 5 times
    # Solution: "Start service + wait 30s"
    # Accuracy: 100% from prior attempts
    return quick_solution_from_history
```

### Decision Synthesis
```python
# Coordinator notices:
# Decision 1: "Use ZLUDA" (reason: verified_working)
# Decision 2: "Use WebSocket API" (reason: real_time)
# Decision 3: "Document with Python docstrings" (reason: tools_read_docstrings)

# Coordinator synthesizes:
"Three decisions made, all align with 'real-time + verified' principle
Next agent should respect this principle when making new decisions"
```

### Blocker Anticipation
```python
# Coordinator sees:
# Decision: "Use ComfyUI-ZLUDA for vision"
# Action: "Created vision_engine_comfy.py"
# Blocker: "HIP library version conflict"

# Coordinator anticipates:
# "Next agent will likely encounter similar lib version issues
# Prepare: pre-emptively document workarounds"
```

---

## What Agents Focus On (99% of Tokens)

✅ **Actual Work**
- Code review
- Architecture design  
- Implementation
- Testing
- Problem-solving
- Creative thinking

❌ **Never Do**
- Manual logging (Coordinator does it)
- Documentation writing (Coordinator synthesizes)
- Context gathering (Coordinator provides briefing)
- Status updates (Coordinator tracks via signals)
- Decision justification essays (Signal + short reason = enough)

---

## Example: Full Session Flow

### Agent Starts (1 minute)
```python
# Agent reads auto-generated briefing from Coordinator
briefing = redis.get(f'handoff:{agent_type}:latest')
print(briefing)
# "OpenCode did X, here's the state, here's your role"

# Coordinator is running in background monitoring everything
```

### Agent Works (110 minutes)
```python
from coordinator import log, request_help

log.action("code_review", context="architecture.md")

# ... actual work, no documentation burden ...

log.decision("use_async_handlers", reason="performance_requirements")

log.progress("reviewed_mcp_interface")

# Blocked?
log.blocker("redis_connection_timeout", severity="high")
request_help(expertise="redis", task="connection_pooling")

# Ready to hand off
request_handoff(to_agent="opencode", reason="needs_implementation")
```

### Coordinator Works (Continuous)
```
Reads every log signal
Extracts meaning
Updates project state
Monitors for patterns
Prepares next briefing
All happening silently in background
```

### Next Agent Starts (1 minute)
```python
# Perfectly contextualized briefing waiting
briefing = read_coordinator_briefing()

# Knows exactly where previous agent left off
# Can jump straight into work
# Zero onboarding overhead
```

---

## The Rigor Paradox

**Conventional thinking**: More documentation = More rigor

**Your insight**: Better, you want:
- **Agents focused on work** (95% tokens on value)
- **System extracts documentation automatically** (zero overhead)
- **Coordinator maintains rigor** (patterns, learnings, blockers)

Result:
- ✅ More actual work gets done
- ✅ Better documented (auto-extracted, not rushed)
- ✅ More rigorous (coordinator enforces patterns)
- ✅ Higher quality (agents have mental space for thinking)

---

## Next Steps

### Week 1: Build Signal API
```python
# coordinator.py - ~200 lines
class Logger:
    def action(self, action, context=None): ...
    def decision(self, key, reason): ...
    def blocker(self, blocker, severity="normal"): ...
    def progress(self, update): ...

def request_help(expertise, task): ...
def request_handoff(to_agent, reason): ...
```

### Week 2: Build Coordinator
```python
# coordinator_service.py - ~300 lines
class CoordinatorService:
    def monitor(): ... # Watch agent:events stream
    def synthesize_decisions(): ...
    def update_project_state(): ...
    def check_blockers(): ...
    def run(): # Main loop
```

### Week 3: Auto-Briefing
```python
# briefing_generator.py - ~200 lines
def generate_briefing(agent_type, project): ...
```

**Total new code: ~700 lines**  
**Benefit: Unlimited scalability + zero agent overhead**

---

## Questions to Guide Your Thinking

1. **Should Coordinator be an Agent?**
   - Option A: Separate Python process (simple, dedicated)
   - Option B: Claude API call on-demand (more intelligent)
   - Option C: Hybrid (background process + on-demand API calls)

2. **What if Coordinator misinterprets a signal?**
   - Agents can call `log.override("decision_id", "corrected_reason")`
   - Or Coordinator is "confident" vs "best_guess" in synthesis

3. **Should agents be able to see what Coordinator is doing?**
   - Yes: `coordinator.get_status()` shows what it's tracking
   - Full transparency on how decisions/blockers extracted

4. **Can agents communicate directly?**
   - Yes: Still have `request_help()` for peer-to-peer
   - Coordinator just doesn't force documentation burden

5. **Who decides priorities if multiple blockers?**
   - Coordinator ranks by: severity + impact + prior solutions
   - Escalates to human if truly ambiguous

---

## In One Sentence

**Let a dedicated Coordinator Agent handle all the administrative overhead of continuity while working agents spend 95% of tokens on actual work.**
