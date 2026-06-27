# Systems Architecture - Elegant Complexity

**Purpose**: Single source of truth for system design. Prevents code sprawl by grouping functionality into systems with clear responsibilities, dependencies, and build order.

**Philosophy**: 5 core systems + 2 meta-layers. Everything else is functionality WITHIN these systems. Build in dependency order.

---

## The 5 Core Systems (Execution Order)

```
┌─────────────────────────────────────────────────────┐
│ SYSTEM 1: INFRASTRUCTURE ORCHESTRATION              │
│ (foundation - must exist first)                      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ SYSTEM 2: SIGNALS & EVENTS                          │
│ (core primitive - agent ↔ system communication)     │
└─────────────────────────────────────────────────────┘
         ↓                            ↓
┌──────────────────────┐    ┌──────────────────────┐
│ SYSTEM 3: STATE      │    │ SYSTEM 4: CONTEXT    │
│ MANAGEMENT           │    │ INTELLIGENCE         │
│ (persistence,        │    │ (briefing, decisions,│
│  recovery)           │    │  learnings, context) │
└──────────────────────┘    └──────────────────────┘
         ↓                            ↓
         └─────────────┬──────────────┘
                       ↓
        ┌──────────────────────────────┐
        │ SYSTEM 5: AGENT ORCHESTRATION│
        │ (bootstrap, initialization,   │
        │  detection, lifecycle)       │
        └──────────────────────────────┘
                       ↓
            ┌──────────────────────┐
            │ ENTRY POINT          │
            │ bootstrap.py          │
            └──────────────────────┘
```

---

## SYSTEM 1: INFRASTRUCTURE ORCHESTRATION

**Status**: Partially exists (scattered in agent_init.py, coordinator_api.py)  
**Build Time**: 2-3 hours  
**Complexity**: Low-Medium  
**Location**: `infrastructure/` package

### Purpose
Ensure physical/external systems (Redis, Docker, WSL) are available and healthy. Fast health checks with aggressive timeouts.

### Responsibilities
- Detect WSL status
- Start Docker Desktop (async)
- Start Redis with health check
- Return infrastructure status dict
- Handle graceful degradation

### Functionality Matrix

| Function | Input | Output | Timeout | Fallback |
|----------|-------|--------|---------|----------|
| **check_wsl_available()** | None | bool | 1s | False (not available) |
| **start_docker_if_needed()** | None | {"status": "running\|starting\|failed"} | 5s | Skip, continue |
| **start_redis_if_needed(port=6379)** | port | {"status": "running\|degraded\|failed"} | 3s | File fallback |
| **health_check_all()** | None | {"wsl": bool, "docker": bool, "redis": bool, "status": "full\|partial\|degraded"} | 10s | Full degradation report |
| **get_infrastructure_status()** | None | Dict with all above + details | Instant | Cached |

### Key Design Principle
**"Fail fast, continue gracefully"**  
- 1-3s timeouts (not 50s)
- Return partial status, don't block
- Every system works without Redis

### Code Location (to create)
```
infrastructure/
├── __init__.py
├── orchestrator.py          # Main: launch all systems
├── wsl.py                   # WSL detection + enabling
├── docker.py                # Docker startup
├── redis.py                 # Redis startup + health check
└── health_check.py          # Overall system health
```

### Dependencies
- None (foundation layer)

### Success Criteria
- ✅ Start infrastructure in <10s total
- ✅ Redis available or gracefully degraded
- ✅ No 145-second timeouts
- ✅ Health check returns immediately

---

## SYSTEM 2: SIGNALS & EVENTS

**Status**: Exists (coordinator_api.py, signal_emitter exist)  
**Build Time**: Already done (1 hour to refactor if needed)  
**Complexity**: Low  
**Location**: Keep existing + clean up

### Purpose
Core communication primitive. Agents emit signals → System processes → Other agents receive context.

### Signal Types (Canonical List)
```
1. DECISION      → Agent made a choice (cached for reuse)
2. BLOCKER       → Agent hit obstacle (others need to know)
3. LEARNING      → Agent discovered insight (future agents apply)
4. HANDOFF       → Agent → next agent briefing
5. COMPLETION    → Agent finished task
6. RECOVERY      → Agent resumed from crash
7. STATUS        → System status update
```

### Responsibilities
- Define signal schema (immutable)
- Emit to Redis primary, file fallback
- Validate signal format
- Retrieve by: type, agent_id, timestamp, task_keyword
- Hash signals (detect duplicates)

### Functionality Matrix

| Function | Input | Output | Requirement |
|----------|-------|--------|-------------|
| **emit_decision()** | name, outcome, reason | signal_id | Logged to Redis/file |
| **emit_blocker()** | description, severity | signal_id | Logged to Redis/file |
| **emit_learning()** | experiment, tried, expected, actual, category | signal_id | Logged to Redis/file |
| **emit_handoff()** | briefing, next_steps | signal_id | Logged to Redis/file |
| **get_signals(type, agent_id, hours=24)** | Filters | [signals] | Fast retrieval |
| **get_signals_by_keyword(keyword)** | Task keyword | [signals] | Filter relevance |

### Key Design Principle
**"Immutable events, queryable everywhere"**  
- Signals never change (append-only)
- Hash them for dedup
- Query by any dimension

### Code Location (Existing - Refactor)
```
coordinator_api.py              # Main API (already exists)
signal_emitter.py              # Emission logic (already exists)
```

### Dependencies
- System 1 (Infrastructure)

### Success Criteria
- ✅ Signal schema is canonical (one source of truth)
- ✅ Emit to Redis primary, file fallback
- ✅ Query signals by type/agent/time/keyword in <100ms
- ✅ No signal loss (dual-write verified)

---

## SYSTEM 3: STATE MANAGEMENT

**Status**: Partially exists (session_state.py, redis_sync_coordinator.py)  
**Build Time**: 2-3 hours to refactor  
**Complexity**: Medium  
**Location**: `state/` package

### Purpose
Agent state survives crashes. Save checkpoints, resume from where you left off.

### Responsibilities
- Create/load agent sessions
- Save checkpoints (task progress, blockers, work state)
- Detect crashes (compare last heartbeat vs now)
- Resume from checkpoint
- Store session metadata
- Clean up old sessions

### Functionality Matrix

| Function | Input | Output | Requirement |
|----------|-------|--------|-------------|
| **create_session(agent_id, task)** | agent_id, task | session_id | Returns new session |
| **save_checkpoint(session_id, progress, blockers, state)** | Meta dict | bool | Saved to Redis/file |
| **load_checkpoint(session_id)** | session_id | checkpoint dict \| None | Most recent or None |
| **detect_crash(agent_id, timeout_seconds=300)** | agent_id | bool | True if crashed |
| **resume_from_crash(agent_id)** | agent_id | (checkpoint, session_id) | Ready to resume |
| **get_session_metadata(session_id)** | session_id | {status, duration, blockers, progress} | For reporting |

### Key Design Principle
**"Crash recovery is automatic, transparent"**  
- Agent doesn't think about crashes
- System detects and resumes automatically
- Checkpoint is incremental (not full dump)

### Code Location (Existing - Refactor)
```
state/
├── __init__.py
├── session_state.py          # Already exists
├── checkpoint.py             # Checkpoint save/load logic
├── crash_detector.py         # Detect agent crashes
├── metadata.py               # Session metadata
└── recovery.py               # Resume from checkpoint
```

### Dependencies
- System 1 (Infrastructure)
- System 2 (Signals & Events)

### Success Criteria
- ✅ Checkpoint save/load in <100ms
- ✅ Crash detection within 5min timeout
- ✅ Resume includes full context (where was I, what was I doing)
- ✅ No state loss even if Redis down

---

## SYSTEM 4: CONTEXT INTELLIGENCE

**Status**: Does NOT exist (theorized)  
**Build Time**: 3-4 hours  
**Complexity**: High (most novel part)  
**Location**: `context/` package

### Purpose
Load 8-10k tokens of useable context. Briefing + decisions + learnings filtered, ranked, summarized. This is where token efficiency happens.

### Responsibilities
- Load previous agent's briefing
- Load cached decisions (task-filtered)
- Load learnings (ranked by relevance + recency + confidence)
- Load active blockers
- Summarize long learnings into "key insights"
- Filter by task keyword
- Calculate context quality score
- Target 8-10k tokens exactly

### Functionality Matrix

| Component | Responsibility | Input | Output | Tokens |
|-----------|---|---|---|---|
| **Briefing Loader** | Get previous agent's handoff | agent_id | briefing dict \| None | 0.5k |
| **Decision Loader** | Get task-relevant decisions | task_keyword, hours=24 | [decisions] ranked | 1-1.5k |
| **Learning Loader** | Get learnings, rank by relevance | task_keyword, confidence_min="high" | [learnings] summarized | 3-4k |
| **Blocker Loader** | Get active blockers only | agent_id | [blockers] | 0.3-0.5k |
| **Summarizer** | Convert long learnings to insights | [learnings] | [insights] brief | 1k |
| **Ranker** | Score learnings by relevance | [learnings], task_keyword | [sorted learnings] | 0 |
| **Aggregator** | Combine all into one context dict | All above | context_dict | 0.5k |
| **Quality Scorer** | % of context that's actionable | context_dict | 0-1 score | 0 |

### Key Learnings Ranking Algorithm

Learnings scored by:
```
relevance_score = (
    0.4 * task_keyword_match +      # Is this about my task?
    0.3 * recency_score +            # Is it recent? (7-day decay)
    0.2 * confidence_score +         # How trustworthy? (high=1.0, medium=0.6, low=0.2)
    0.1 * success_score              # Did it work? (yes=1.0, no=0.5, mixed=0.7)
)
```

Only keep learnings with relevance_score > 0.5. Summarize each learning into 1-2 sentences.

### Example Context Dict (8-10k)

```python
{
    "briefing": "Continue semantic refactoring of remaining 10-12 files",  # 0.5k
    
    "recent_decisions": [  # 1.2k
        {
            "name": "use_semantic_naming_convention",
            "outcome": "yes",
            "reason": "60% faster code comprehension, 50-75% readability improvement",
            "age": "2h",
            "applicability": "all_future_methods"
        },
        {
            "name": "maintain_backward_compatibility",
            "outcome": "yes",
            "reason": "zero breaking changes via deprecated wrappers",
            "age": "2h",
            "applicability": "all_refactoring"
        }
    ],
    
    "key_learnings": [  # 3.8k (summarized)
        {
            "pattern": "5 semantic naming patterns discovered",
            "patterns": ["load_X_from_Y()", "cache_X_for_Y()", "record_X_preventing_Y()", "emit_X_causing_Y()", "derive_X_from_Y()"],
            "recommendation": "Apply to remaining files. Enables instant code understanding.",
            "confidence": "high",
            "priority": "high"
        },
        {
            "finding": "Backward compatibility via deprecated wrappers",
            "impact": "100% zero breaking changes, 50+ deprecated aliases created",
            "recommendation": "Continue using this strategy. Enables gradual migration.",
            "confidence": "high",
            "priority": "high"
        },
        {
            "insight": "Code readability improvement: 60% faster comprehension",
            "metrics": "50-75% readability improvement, 40-50% cognitive load reduction",
            "recommendation": "Semantic naming is the primary driver. Continue applying consistently.",
            "confidence": "high",
            "priority": "medium"
        }
    ],
    
    "active_blockers": [],  # 0.3k
    
    "system_status": {  # 0.3k
        "wsl": "available",
        "docker": "running",
        "redis": "running",
        "file_system": "operational"
    },
    
    "context_metadata": {  # 0.5k
        "quality_score": 0.94,
        "signal_quality": "high",
        "actionability_percentage": 94,
        "decisions_loaded": 2,
        "learnings_loaded": 3,
        "age_of_oldest_decision_hours": 2,
        "task_keyword_match_count": 5
    }
}
```

### Key Design Principle
**"Distilled knowledge, not raw data"**  
- Summarize long learnings
- Rank by relevance, not recency alone
- Filter ruthlessly (only high-signal items)
- Quality score tells agent how much to trust context

### Code Location (to create)
```
context/
├── __init__.py
├── briefing_loader.py        # Load previous handoff
├── decision_loader.py        # Load decisions
├── learning_loader.py        # Load learnings
├── blocker_loader.py         # Load blockers
├── ranker.py                 # Rank by relevance algorithm
├── summarizer.py             # Summarize long items
├── aggregator.py             # Combine into single dict
└── quality_scorer.py         # Calculate actionability score
```

### Dependencies
- System 1 (Infrastructure)
- System 2 (Signals & Events)
- System 3 (State Management)
- Also depends on learning_store.py (existing)

### Success Criteria
- ✅ Context loaded in <2 seconds
- ✅ Exactly 8-10k tokens (not more, not less)
- ✅ Quality score > 0.85 (85%+ actionable)
- ✅ Agent can act immediately without built-in context
- ✅ Token savings > 50% compared to current approach

---

## SYSTEM 5: AGENT ORCHESTRATION

**Status**: Partially exists (agent_init.py)  
**Build Time**: 2-3 hours to refactor  
**Complexity**: Low-Medium  
**Location**: `agent/` package

### Purpose
One-call bootstrap for any agent. Orchestrates Systems 1-4 into a ready-to-work state.

### Responsibilities
- Detect agent type (Claude Code, OpenCode, generic)
- Launch infrastructure (System 1)
- Load context (System 4)
- Detect if resuming from crash (System 3)
- Generate agent-specific briefing
- Return ready-to-work object
- Handle degradation gracefully

### Functionality Matrix

| Function | Input | Output | Requirement |
|----------|-------|--------|-------------|
| **detect_agent_type()** | None | "claude_code" \| "opencode" \| "generic" | Determines behavior |
| **bootstrap_agent(agent_id, agent_type, task_keyword)** | Minimal | Fully initialized agent object | <10s startup |
| **check_if_resuming_crash(agent_id)** | agent_id | (bool, checkpoint) | Enables recovery |
| **generate_agent_briefing(agent_id, context, checkpoint)** | Meta | briefing string | Human-readable |

### Key Design Principle
**"One call, fully initialized"**  
- Agent calls `bootstrap_agent()` once
- Gets everything: API, context, state, status
- No manual setup steps

### Code Location (Existing - Refactor)
```
agent/
├── __init__.py
├── initializer.py            # Main bootstrap function (refactored from agent_init.py)
├── detector.py               # Detect agent type
├── supervisor.py             # Manage agent lifecycle
└── briefing_generator.py      # Create agent briefing
```

### Dependencies
- System 1 (Infrastructure)
- System 2 (Signals & Events)
- System 3 (State Management)
- System 4 (Context Intelligence)

### Success Criteria
- ✅ `bootstrap_agent()` completes in <10 seconds
- ✅ Returns: api, context, state, status in one object
- ✅ Detects crash and auto-resumes
- ✅ Agent-type aware (different behavior for Claude Code vs OpenCode)
- ✅ Works with or without Redis (graceful degradation)

---

## 2 Meta-Layers (Support Systems)

### Meta-Layer A: Learning Management
**Status**: Exists (learning_store.py)  
**Purpose**: Capture and apply knowledge  
**Functionality**:
- Record experiments (agents emit LEARNING signals)
- Summarize learnings (compress long logs into insights)
- Deduplicate learnings (merge similar findings)
- Surface anti-patterns (what NOT to do)
- Rank learnings (used by System 4)

**Location**: learning/ package (exists)

### Meta-Layer B: Coordination
**Status**: Partially exists  
**Purpose**: Hand off between agents  
**Functionality**:
- Emit HANDOFF signal (agent A → B)
- Load briefing (agent B reads from System 4)
- Track agent sequence (which agent → next)
- Log coordination events

**Location**: coordination/ package (to create, 1-2 hours)

---

## Code Organization (Directory Structure)

```
E:\AI-Setup\
├── infrastructure/              # SYSTEM 1 (2-3 hours)
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── wsl.py
│   ├── docker.py
│   ├── redis.py
│   └── health_check.py
│
├── signals/                     # SYSTEM 2 (existing - refactor)
│   ├── __init__.py
│   └── ... (keep existing signal code)
│
├── state/                       # SYSTEM 3 (2-3 hours)
│   ├── __init__.py
│   ├── session_state.py
│   ├── checkpoint.py
│   ├── crash_detector.py
│   ├── metadata.py
│   └── recovery.py
│
├── context/                     # SYSTEM 4 (3-4 hours) ← NOVEL
│   ├── __init__.py
│   ├── briefing_loader.py
│   ├── decision_loader.py
│   ├── learning_loader.py
│   ├── blocker_loader.py
│   ├── ranker.py
│   ├── summarizer.py
│   ├── aggregator.py
│   └── quality_scorer.py
│
├── agent/                       # SYSTEM 5 (2-3 hours)
│   ├── __init__.py
│   ├── initializer.py
│   ├── detector.py
│   ├── supervisor.py
│   └── briefing_generator.py
│
├── learning/                    # Meta-Layer A (existing)
│   ├── __init__.py
│   └── learning_store.py
│
├── coordination/                # Meta-Layer B (1-2 hours)
│   ├── __init__.py
│   ├── handoff.py
│   └── sync.py
│
├── bootstrap.py                 # ENTRY POINT (uses System 5)
├── config.py                    # Configuration (new)
└── tests/                       # Tests for each system
    ├── test_infrastructure.py
    ├── test_signals.py
    ├── test_state.py
    ├── test_context.py
    ├── test_agent.py
    └── test_integration.py
```

---

## Build Roadmap (Execution Order)

### Phase A: Foundation (Existing ✅ - Verify)
**Duration**: 2-3 hours (refactoring)  
**Systems**: 1, 2  
**Output**: Fast infrastructure startup, canonical signals

```
[ ] SYSTEM 1: Infrastructure Orchestration
    [ ] infrastructure/orchestrator.py
    [ ] infrastructure/wsl.py
    [ ] infrastructure/docker.py
    [ ] infrastructure/redis.py
    [ ] infrastructure/health_check.py
    [ ] Test: Start infrastructure in <10s
    
[ ] SYSTEM 2: Signals & Events
    [ ] Verify coordinator_api.py signal schema
    [ ] Test: Emit/retrieve signals by type/agent/time
```

### Phase B: Persistence (Existing 🔧 - Refactor)
**Duration**: 2-3 hours (refactoring)  
**Systems**: 3  
**Output**: Crash recovery works, checkpoint load/save reliable

```
[ ] SYSTEM 3: State Management
    [ ] state/session_state.py (existing, refactor)
    [ ] state/checkpoint.py
    [ ] state/crash_detector.py
    [ ] state/metadata.py
    [ ] state/recovery.py
    [ ] Test: Save/load checkpoint <100ms
    [ ] Test: Detect crash within 5min timeout
```

### Phase C: Intelligence (NEW ✨ - Build)
**Duration**: 3-4 hours (new code)  
**Systems**: 4  
**Output**: 8-10k token context, 85%+ quality, agent-ready

```
[ ] SYSTEM 4: Context Intelligence (THE NOVEL PART)
    [ ] context/briefing_loader.py
    [ ] context/decision_loader.py
    [ ] context/learning_loader.py
    [ ] context/blocker_loader.py
    [ ] context/ranker.py (relevance scoring algorithm)
    [ ] context/summarizer.py (long → short insights)
    [ ] context/aggregator.py
    [ ] context/quality_scorer.py
    [ ] Test: Load context in <2s, exactly 8-10k tokens
    [ ] Test: Quality score > 0.85
    [ ] Test: Agent can act without built-in context
```

### Phase D: Orchestration (Existing 🔧 - Refactor)
**Duration**: 2-3 hours (refactoring)  
**Systems**: 5  
**Output**: One-call bootstrap for any agent

```
[ ] SYSTEM 5: Agent Orchestration
    [ ] agent/initializer.py (refactor from agent_init.py)
    [ ] agent/detector.py
    [ ] agent/supervisor.py
    [ ] agent/briefing_generator.py
    [ ] Test: bootstrap_agent() <10s
    [ ] Test: Returns api, context, state, status
    [ ] Test: Detects agent type correctly
    [ ] Test: Auto-resumes from crash
```

### Phase E: Support Systems (NEW/EXISTING - Build)
**Duration**: 2-3 hours  
**Systems**: Meta-Layer A & B  
**Output**: Learning captured, coordination working

```
[ ] Meta-Layer A: Learning Management
    [ ] learning/summarizer.py (if not exists)
    [ ] learning/deduplicator.py
    [ ] Test: Learnings deduplicated, ranked by relevance
    
[ ] Meta-Layer B: Coordination
    [ ] coordination/handoff.py
    [ ] coordination/sync.py
    [ ] Test: Agent A → B handoff with full context
```

### Phase F: Entry Point & Integration
**Duration**: 1-2 hours  
**Output**: Unified bootstrap.py, integration tests

```
[ ] Update bootstrap.py
    [ ] Use System 5 (Agent Orchestration)
    [ ] Remove old manual setup steps
    
[ ] Create config.py
    [ ] Centralized configuration
    [ ] Timeouts, thresholds, etc.
    
[ ] Integration tests
    [ ] test_full_startup.py (Systems 1-5 together)
    [ ] test_crash_recovery.py
    [ ] test_context_quality.py
    [ ] test_agent_handoff.py
```

---

## Total Build Time Estimate

| Phase | System | Status | Hours | Priority |
|-------|--------|--------|-------|----------|
| A | 1, 2 | Refactor | 2-3 | P0 (foundation) |
| B | 3 | Refactor | 2-3 | P0 (critical) |
| C | 4 | NEW BUILD | 3-4 | **P1 (novel)** |
| D | 5 | Refactor | 2-3 | P1 (orchestration) |
| E | Meta | NEW BUILD | 2-3 | P2 (support) |
| F | Integration | NEW | 1-2 | P1 (validation) |
| **TOTAL** | - | - | **13-18 hours** | - |

**Realistic estimate: 15-20 hours + testing**

---

## What This Prevents

✅ **No scattered micro-modules** - Everything grouped by system  
✅ **Clear dependencies** - Build in right order  
✅ **No code sprawl** - Each system has defined boundaries  
✅ **Elegant complexity** - 5 systems, each with single responsibility  
✅ **Extensible** - Add new functionality = add to existing system, not new file  
✅ **Testable** - Test each system independently, then integration  
✅ **Maintainable** - Know exactly where each piece lives  

---

## Critical Question for You

**Where should we start?**

Option A: **Start with System 4 (Context Intelligence)** first
- Most novel, most valuable
- Unlocks 50% token savings
- Can test in isolation (doesn't need other systems perfect)

Option B: **Follow build order (Systems 1-5)**
- Proper foundation first
- Lower risk of rework
- Takes longer to see value

**My recommendation**: Start with **Option A + B Hybrid**:
1. Quickly validate System 1 infrastructure (30 min)
2. Jump straight to System 4 (Context Intelligence) - most valuable
3. Then come back to System 3 & 5
4. This unblocks context loading while infrastructure stabilizes

What's your preference?

