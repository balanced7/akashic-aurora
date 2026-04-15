# Agent Coordination Protocol
=================================

## Current Situation

Two OpenCode agents are active:
1. **agent_1965c354** (this session) - Generator role
2. **Other agent** - Unknown role (may be reading this file)

## Problem

Multiple agents working without coordination can:
- Overwrite each other's changes
- Duplicate work
- Create merge conflicts
- Miss context from each other

## Solution: Workspace Division

### Proposed Division of Labor

| Task Area | Agent | Status |
|-----------|-------|--------|
| Redis HA Deployment | agent_1965c354 | CLAIMED |
| Vector Store Integration | agent_1965c354 | IN PROGRESS |
| Harness Enforcement Fixes | agent_1965c354 | PENDING |
| Documentation Updates | Either | AVAILABLE |
| GitHub Push | Either | AVAILABLE |
| Testing/Verification | Either | AVAILABLE |

### Alternative: Task Switching Protocol

1. **Before starting a task**: Check `blackboard_data/agent_coordination/locks/task:<taskname>.lock`
2. **To claim a task**: Send broadcast `task_claimed` message
3. **To release a task**: Send broadcast `task_released` message
4. **On conflict**: Older agent wins (lower agent_id)

## Files Created in This Session

1. `redis_ha_manager.py` - Triple redundancy Redis with Sentinel
2. `sentinel1.conf`, `sentinel2.conf`, `sentinel3.conf` - Sentinel configs
3. `vector_store.py` - Fast similarity search for learnings
4. `agent_coordinator.py` - File-based inter-agent communication
5. Updated `knowledge_base.py` - Added `vector_search()`, `sync_to_vector_store()`

## Current Priority Tasks

1. **Deploy Redis HA**: `python redis_ha_manager.py --setup` then deploy
2. **Fix harness bugs**: Missing `sys` import fixed
3. **Save learnings**: About 8 lessons saved to KB
4. **GitHub push**: Files staged but not committed

## Coordination Commands

```bash
# Check for other agents
python -c "from agent_coordinator import coordinate_agents; print(coordinate_agents())"

# Claim a task
python -c "from agent_coordinator import get_coordinator; c=get_coordinator(); c.claim_task('task_name')"

# Broadcast status
python -c "from agent_coordinator import get_coordinator; c=get_coordinator(); c.broadcast('status', {'doing': 'task'})"

# Get messages
python -c "from agent_coordinator import get_coordinator; c=get_coordinator(); print(c.get_messages())"
```

## Rules

1. **Check locks before editing files**
2. **Broadcast before starting major work**
3. **Save learnings to KB** - prevent repeated mistakes
4. **Update this file** with current status

---

**Last Updated**: 2026-04-15 00:32 UTC
**Updated By**: agent_1965c354
