# Redis Sync Integration: Best of Both Worlds

## What We're Combining

### OLD SYSTEM (Before Claude) - Patterns That Worked
**OpenCodeSync (sync.py)**
- ✅ Instance heartbeat/status publishing with TTL
- ✅ Learnings as LPUSH lists (newest first, pageable)
- ✅ Simple pub/sub style discovery
- ✅ Lightweight, fast

**AgentMemory (agent_memory.py)**
- ✅ Multi-faceted data structure (conversations, knowledge, states, context, tasks)
- ✅ Tag-based indexing for knowledge discovery
- ✅ Hash storage for structured data with lookups
- ✅ TTL-based temporary context (shared state)
- ✅ Separated concerns (conversation, knowledge, task)

### CURRENT SYSTEM (Claude-built) - What Improved
**CoordinatorAPI (coordinator_api.py)**
- ✅ Clean signal-based logging API
- ✅ Explicit signal types (ACTION, DECISION, BLOCKER, HANDOFF, COMPLETION, LEARNING)
- ✅ Redis streams for canonical event log
- ✅ Graceful file fallback when Redis unavailable
- ✅ Startup context loading (briefing, decisions, learnings)
- ✅ Self-describing API (bootstrap methods)

**LearningStore (learning_store.py)**
- ✅ Structured learning schema (what_tried, expected, actual, metrics, root_cause, recommendation)
- ✅ Multiple query paths (by category, anti-patterns, recommendations)
- ✅ File-based fallback implementation
- ✅ Success scoring and sorting

### NEW SYSTEM (redis_failover_sync.py) - What's Missing
**RedisSyncHandler**
- ✅ Hash-based verification (SHA256) to detect mismatches
- ✅ Metadata logging for audit trail
- ✅ Automatic resync when divergence detected
- ✅ Crash recovery from files
- ✅ Health monitoring
- ❌ NOT integrated with coordinator_api yet
- ❌ NOT used for learnings yet

---

## Integration Strategy

### Layer 1: Unified Sync Coordinator
**File:** `redis_sync_coordinator.py` (NEW)

Wraps `RedisSyncHandler` with:
1. **Signal persistence** - Signals written via RedisSyncHandler with verification
2. **Status/heartbeat** - Instance alive checks (from old OpenCodeSync pattern)
3. **Learning sync** - Learnings dual-written with hash verification
4. **Health dashboard** - Status of both Redis and file backup

```python
class RedisSyncCoordinator:
    def __init__(self, fallback_dir, redis_host, redis_port):
        self.sync_handler = RedisSyncHandler(fallback_dir, redis_host, redis_port)
        self.instance_id = generate_instance_id()
    
    # Signals
    def emit_signal(self, signal_type, data, agent_id):
        # Use RedisSyncHandler.write_signal + also to Redis streams
        
    # Learnings
    def record_learning(self, learning_signal):
        # Use RedisSyncHandler with learning-specific indexing
        
    # Status/heartbeat (from old OpenCodeSync)
    def publish_status(self, status_dict):
        # Instance heartbeat with TTL
        
    # Monitoring
    def health_check(self):
        # Returns sync status, health metrics
        
    def verify_all_synced(self):
        # Run full verification routine
        
    def resync_if_needed(self):
        # Auto-correct mismatches
```

### Layer 2: Updated coordinator_api.py
Replace `_emit_signal()` to use RedisSyncCoordinator:
- Still maintains same external API (action, decision, learning, etc.)
- Internally uses RedisSyncHandler for writes
- Signals go through verification pipeline
- File fallback now has hash tracking

### Layer 3: Updated learning_store.py
Add sync awareness:
- Use RedisSyncHandler for learnings
- Implement `verify_sync()` for learnings specifically
- Add `auto_resync()` to learning queries

---

## Data Flow

### Before (Current)
```
Agent Action → coordinator_api._emit_signal()
    ↓
  Try Redis.xadd()
    ↓ (if fails)
  Write to agent_*.jsonl
    ↓
  No verification, no sync status
```

### After (Integrated)
```
Agent Action → coordinator_api._emit_signal()
    ↓
  RedisSyncCoordinator.emit_signal()
    ↓
  RedisSyncHandler.write_signal()
    ├─ Try Redis.hset(signal:{key}, data+hash)
    └─ Write to file.jsonl with hash
    ↓
  RedisSyncHandler._log_sync_metadata()
    └─ Audit trail to sync_metadata.jsonl
    ↓
  Health monitoring (continuous)
    ├─ If divergence detected
    └─ Auto-resync or alert
```

### Learning Sync (New)
```
Agent Learning → coordinator_api.learning()
    ↓
  RedisSyncCoordinator.record_learning()
    ↓
  RedisSyncHandler.write_signal(type=learning, ...)
    ├─ Redis: Learn:experiment:{exp_id} hash
    ├─ File: learnings.jsonl entry
    └─ Both hashes logged
    ↓
  LearningStore queries auto-sync if mismatch found
    ├─ verify_sync() checks hashes match
    └─ resync_all() rebuilds from preferred source
```

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `redis_sync_coordinator.py` | CREATE | Unified coordinator wrapping RedisSyncHandler |
| `coordinator_api.py` | MODIFY | Replace _emit_signal with RedisSyncCoordinator |
| `learning_store.py` | MODIFY | Add sync verification to learning queries |
| `redis_sync_admin.py` | CREATE | Admin tools: verify status, manual resync, dashboard |
| `test_sync_integration.py` | CREATE | Integration tests validating sync |

---

## Validation Strategy

### Phase 1: Verify Current State
- Scan Redis (16379) for existing signals
- Scan learnings.jsonl for learnings
- Compare hashes (if Redis available)
- Identify what's only in Redis vs only in files

### Phase 2: Migrate Historical Data
- Load learnings.jsonl into Redis with hashes
- Verify migration succeeded
- Update sync metadata

### Phase 3: Enable Sync Layer
- Switch coordinator_api._emit_signal to RedisSyncCoordinator
- Run Phase 1.5 test again with new sync layer
- Verify dual-write is happening
- Verify hashes match

### Phase 4: Continuous Monitoring
- Start health_check() in background
- Monitor sync_metadata.jsonl growth
- Test resync routine manually
- Test crash recovery

---

## Benefits of This Approach

1. **Fault Tolerant** - Works with or without Redis, corrects itself
2. **Observable** - Every operation logged and auditable
3. **Discoverable** - Can find what's in sync vs out-of-sync
4. **Recoverable** - Can rebuild from files after crash
5. **Compatible** - Existing coordinator_api.py API unchanged externally
6. **Scalable** - Status/heartbeat patterns support multi-instance
7. **Proven** - Combines old patterns that worked + new fault tolerance

---

## Success Criteria

- ✅ All new signals go through RedisSyncHandler
- ✅ All learnings written to both Redis and file with matching hashes
- ✅ Health monitoring shows green (in_sync=true) for all signals
- ✅ Resync routine can be run without data loss
- ✅ Agent reads learnings successfully from both sources
- ✅ Phase 1.5 test passes with new sync layer
