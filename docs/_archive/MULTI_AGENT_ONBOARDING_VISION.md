# Multi-Agent Collaborative Onboarding System
## Vision & Architecture Refinement

**Your Goal**: Any new AI agent (Claude, OpenCode, Cursor, etc.) can self-initialize, gain full context, and collaboratively contribute to projects with unified logging and handoff.

---

## What You Have ✅

### Infrastructure Layer
- ✅ **Redis HA** for persistent state (6379 master, sentinels)
- ✅ **MCP Server** (ai_setup_mcp.py) exposing tools & context
- ✅ **Session Logging** (JSONL with dual-write redundancy)
- ✅ **Agent Coordinator** (agent_coordinator_v2.py) for message passing
- ✅ **Background Monitor** (polling at 100ms for CLI agents)
- ✅ **Agent Dashboard** (real-time status visualization)

### Continuity Layer
- ✅ **Project Context** (4-layer: Architecture, Big Picture, Mid, Recent)
- ✅ **Session State** (blackboard_data/session_state.json)
- ✅ **Learning Storage** (learn:decisions, learn:experiences in Redis)
- ✅ **Manifest System** (agent status tracking)

### Documentation Layer
- ✅ **bootstrap.md** (infrastructure guide)
- ✅ **AGENT_PROTOCOL.md** (multi-agent rules)
- ✅ **ARCHITECTURE.md** (system overview)
- ✅ **COORDINATION_PRIMER.md** (agent communication)

---

## What's Missing ❌

### 1. **Formal Onboarding Protocol** (CRITICAL)
No standardized checklist new agents follow. You have bootstrap.md but it's infrastructure-focused, not agent-focused.

**What's needed:**
```markdown
# Agent Onboarding Checklist

[ ] 1. Read bootstrap.md (infrastructure awareness)
[ ] 2. Call session_register (establish identity)
[ ] 3. Load project context (understand scope)
[ ] 4. Check agent registry (discover collaborators)
[ ] 5. Analyze session history (catch up on past)
[ ] 6. Declare operation (announce self)
[ ] 7. Begin work with unified logging
```

### 2. **Agent Profile System** (HIGH PRIORITY)
Agents don't have declared specializations or capabilities.

**What's needed:**
```json
{
  "agent_id": "claude_20260616_001",
  "agent_type": "claude",
  "instance": "desktop",
  "specialization": ["architecture", "python", "redis"],
  "capabilities": {
    "code_generation": true,
    "system_design": true,
    "debugging": true,
    "documentation": true
  },
  "max_concurrent_tasks": 1,
  "handoff_expertise": ["opencode"],
  "status": "available",
  "current_project": "breakthrough-stack"
}
```

### 3. **Unified Handoff Protocol** (HIGH PRIORITY)
Agents can't hand off cleanly to each other.

**Missing:**
- Handoff templates
- State serialization format
- "Next Agent" routing logic
- Continuity checkpoints

### 4. **Agent Discovery & Awareness** (MEDIUM)
Agents don't know:
- What other agents are running
- What each agent is working on
- What expertise is available
- Who to ask for help

### 5. **Unified Prompt Templates** (MEDIUM)
No standard way to brief a new agent on project state.

**Missing:**
```
# Agent Briefing Template
You are assuming work on: {project}
Previous agent: {agent_id}
Project state: {status}
Your role: {role}
Next steps: {roadmap}
```

### 6. **Structured Handoff Log** (MEDIUM)
Session logs don't track agent transitions clearly.

**Missing:**
```json
{
  "type": "agent_handoff",
  "from_agent": "opencode_20260416",
  "to_agent": "claude_20260616",
  "timestamp": "2026-06-16T00:35:00Z",
  "reason": "Claude has code review expertise",
  "context_passed": ["project_state", "blockers", "decisions"],
  "expectations": ["Review architecture", "Suggest improvements"]
}
```

### 7. **Agent Health Monitoring** (LOW)
No way to detect dead/stuck agents.

### 8. **Collaborative Task Assignment** (LOW)
No intelligent task distribution across agents.

---

## Refined Architecture

### Tier 1: Onboarding (What agents do at startup)
```
New Agent Starts
    ↓
[ONBOARDING CHECKLIST]
    ├─ Load bootstrap.md → Understand infrastructure
    ├─ session_register → Establish Redis identity
    ├─ Load project context → Understand scope
    ├─ Query agent_registry → Know collaborators
    ├─ Run session_recovery → Understand history
    ├─ Load milestones/blockers → Know roadmap
    └─ Declare operation → Announce self to team
    ↓
Agent Ready
    ↓
[WORK PHASE]
    ├─ Log actions (session_append_event)
    ├─ Record decisions (learning_record_decision)
    ├─ Update milestones (project_update_milestone)
    └─ Monitor for handoff signals
    ↓
[HANDOFF]
    ├─ Serialize state (agent_prepare_handoff)
    ├─ Brief next agent (agent_handoff)
    └─ Log transition (handoff_event)
```

### Tier 2: Redis Data Structure (Unified State)
```
Agents:
  agent:registry → {all available agents}
  agent:{id}:status → {current state}
  agent:{id}:capabilities → {what it can do}
  agent:{id}:manifest → {current operation}

Projects:
  project:{name}:state → {project metadata}
  project:{name}:milestones → {progress}
  project:{name}:blockers → {issues}
  project:{name}:owner_agent → {who's leading}

Sessions:
  session:events → {canonical log stream}
  session:{id}:handoff → {transition markers}
  session:{id}:learnings → {decisions & insights}

Collaboration:
  collaboration:message_queue → {inter-agent messages}
  collaboration:help_requests → {requests for expertise}
  collaboration:handoff_queue → {pending handoffs}
```

### Tier 3: Unified Logging (What all agents write)
```json
{
  "type": "agent_event",
  "agent_id": "claude_20260616_001",
  "timestamp": "2026-06-16T00:35:00Z",
  "event_type": "work_start|work_progress|decision|blocker|handoff_request|handoff_complete",
  "project": "breakthrough-stack",
  "content": "...",
  "milestones_affected": ["milestone-id"],
  "next_agent": "opencode_xxx" (if handoff)
}
```

### Tier 4: Agent Specialization Routing
```python
# When a blocker appears, find best agent to help
def find_best_agent_for_task(task_type, expertise_required):
    candidates = query_agent_registry(expertise=expertise_required)
    available = [a for a in candidates if a.status == "available"]
    return max(available, key=lambda a: a.expertise_match(task_type))
```

---

## Concrete Implementation Plan

### Phase 1: Formalize Onboarding (This week)
**Create**: `E:\AI-Setup\AGENT_ONBOARDING_CHECKLIST.md`
```markdown
# Agent Onboarding Checklist

[ ] Step 1: Load bootstrap.md
    - Read infrastructure overview
    - Note Redis ports (6379, 6380, 6381)
    - Understand agent communication via Redis

[ ] Step 2: Register with system
    - Call: session_register(agent, tier, intent)
    - Store agent profile in Redis

[ ] Step 3: Load project context
    - Current project: {from session state}
    - Status: {from milestones}
    - Blockers: {from Redis}

[ ] Step 4: Understand agent ecosystem
    - Query: agent_registry (see who exists)
    - Check: handoff history (see how work flows)
    - Identify: relevant collaborators

[ ] Step 5: Catch up on history
    - Run: session_recovery for past 5 sessions
    - Extract: decisions and learnings
    - Review: blockers from past month

[ ] Step 6: Declare operation
    - Call: declare_operation(agent_id, task, estimated_duration)
    - Sets: manifest + operational alert

[ ] Step 7: Begin work
    - Use: session_append_event for logging
    - Use: learning_record_decision for decisions
    - Use: project_update_milestone for progress
    - Watch: collaboration:handoff_queue for handoff signals
```

### Phase 2: Agent Profile System (Next week)
**Create**: `E:\AI-Setup\agent_profiles.py`
```python
class AgentProfile:
    id: str
    type: str  # "claude", "opencode", "cursor"
    instance: str  # "desktop", "api", "server"
    specializations: List[str]
    capabilities: Dict[str, bool]
    max_concurrent_tasks: int
    redis_config: Dict
    
    def register(self):
        # Store in Redis
        r.hset(f"agent:{self.id}:profile", mapping=self.__dict__)
    
    @staticmethod
    def load(agent_id: str):
        # Load from Redis
        data = r.hgetall(f"agent:{agent_id}:profile")
        return AgentProfile(**data)
```

### Phase 3: Handoff Protocol (Next 2 weeks)
**Create**: `E:\AI-Setup\agent_handoff.py`
```python
class AgentHandoff:
    from_agent: str
    to_agent: str
    project: str
    reason: str
    state: Dict  # What to pass
    expectations: List[str]  # What to do next
    
    def execute(self):
        # 1. Serialize current state
        # 2. Log handoff event
        # 3. Create briefing for next agent
        # 4. Queue message to next agent
        # 5. Update Redis manifest
```

### Phase 4: Unified Agent Briefing Template (Week 4)
**Create**: `E:\AI-Setup\AGENT_BRIEFING_TEMPLATE.md`
```markdown
# Agent Briefing: {project_name}

## Your Role
You are Claude Code, assuming work on the BreakThrough Stack.

## Previous Agent
- ID: opencode_20260415_001327
- Duration: 6 hours
- Accomplishments: Multi-agent communication system

## Project State
- Status: {from project:state}
- Phase: {implementation}
- Completion: 45%

## Your Mission (Next 2 hours)
1. Review architecture changes from previous agent
2. Identify any technical debt
3. Set up vision engine integration
4. Document findings

## Blockers You May Encounter
{from Redis blockers list}

## Resources Available
- MCP server on 8080
- Redis on 6379 (master)
- ComfyUI-ZLUDA installed
- Session history available
```

---

## How This Solves Your Problem

| Need | Solution | Status |
|------|----------|--------|
| New agent initializes | Onboarding checklist | ✏️ To create |
| Gains infrastructure awareness | bootstrap.md + session_register | ✅ Exists |
| Catches up on history | session_recovery + learning_record | ✅ Exists (needs UI) |
| Knows other agents | agent_registry + manifest system | ✅ Partial (needs formalization) |
| Knows project state | project_context 4-layer system | ✅ Exists |
| Hands off cleanly | Handoff protocol + briefing template | ❌ Missing |
| Logs unified way | session_append_event | ✅ Exists |
| Works collaboratively | Message bus + help requests | ✅ Partial |

---

## Your Competitive Advantage

This is a **multi-agent OS**. Most AI systems work:
```
Single AI → Task → Output
```

You're building:
```
AI 1 → AI 2 → AI 3 → Output
(with full continuity, shared learnings, and collaborative history)
```

This enables:
1. **Specialization**: Claude for architecture, OpenCode for scripting, Cursor for refactoring
2. **Continuity**: Agent 2 picks up exactly where Agent 1 left off
3. **Learning**: All agents see what past agents learned
4. **Collaboration**: Agents can ask each other for help
5. **Resilience**: If one agent gets stuck, hand off to another

---

## Quick Win (Do This First)

Create **one unified checklist** that answers:
1. "How does a new agent initialize itself?"
2. "What does it need to know first?"
3. "How does it stay aware of other agents?"
4. "How does it hand off work?"

Then test it with Claude Code (this session) → OpenCode (next session) hand off.

---

## Next Steps

1. ✏️ **Create**: `AGENT_ONBOARDING_CHECKLIST.md`
2. ✏️ **Create**: `AGENT_BRIEFING_TEMPLATE.md`
3. ✏️ **Create**: `agent_profiles.py` with registration system
4. ✏️ **Update**: `ai_setup_mcp.py` to expose agent registry tools
5. 🧪 **Test**: Claude → OpenCode handoff using the new protocol

**Estimated time to working multi-agent handoff: 2-3 days**
