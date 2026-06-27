# Redis Sync Integration Quickstart

This guide explains how to use the integrated fault-tolerant sync system that combines the best of Redis, file backup, and verification patterns.

## What We Built

**Four new modules working together:**

1. **redis_sync_coordinator.py** (400+ lines)
   - Unified coordinator for dual-write with verification
   - Handles signals, learnings, status/heartbeat
   - Hash-based verification and auto-recovery

2. **coordinator_api_sync_adapter.py** (100+ lines)
   - Transparent adapter that patches coordinator_api
   - No changes needed to existing agent code
   - Enables sync layer with one function call

3. **redis_sync_admin.py** (300+ lines)
   - Command-line admin tool
   - Verification, health checks, manual resync
   - Data migration and diagnostics

4. **test_sync_integration.py** (300+ lines)
   - Comprehensive integration tests
   - Validates sync, recovery, verification

## How to Use

### Option 1: Use Existing coordinator_api with Sync Layer (RECOMMENDED)

```python
# At application startup, install sync layer ONCE
from coordinator_api_sync_adapter import install_sync_layer
install_sync_layer()

# Now use coordinator_api normally
from coordinator_api import initialize

api = initialize("my_agent")

# All calls now use fault-tolerant sync
api.action("doing_work")
api.decision("use_redis", outcome="yes", reason="Verified")
api.learning(
    experiment_name="sync_test",
    what_tried="Dual write to Redis and file",
    expected_outcome="Both writes succeed",
    actual_outcome="Success with hash verification",
    category="testing",
    success="yes",
    recommendation="Use RedisSyncCoordinator for production"
)
```

**Benefits:**
- Zero changes to existing agent code
- Automatic dual-write and verification
- Graceful fallback when Redis unavailable
- Audit trail of all sync operations

### Option 2: Use RedisSyncCoordinator Directly

```python
from redis_sync_coordinator import RedisSyncCoordinator, SignalType

# Create coordinator
coordinator = RedisSyncCoordinator("my_agent")

# Emit signals (dual-write with verification)
coordinator.emit_signal(
    SignalType.DECISION,
    {
        "decision_name": "use_async",
        "outcome": "yes",
        "reason": "Performance test"
    }
)

# Record learnings (structured + synced)
coordinator.record_learning(
    experiment_name="async_perf",
    what_tried="Async processing",
    expected_outcome="30% faster",
    actual_outcome="35% faster",
    category="performance",
    success="yes",
    recommendation="Always use async for I/O"
)

# Check health
health = coordinator.health_check()
print(f"Redis: {health['redis_available']}")
print(f"Signals in file: {health['signals_in_file']}")
print(f"Learnings in file: {health['learnings_in_file']}")

# Verify everything is synced
report = coordinator.verify_all_synced()
print(f"Sync health: {report['health']}")
```

**Benefits:**
- Full control over sync behavior
- Direct access to verification and recovery
- Status/heartbeat publishing
- Audit logging

## Admin Commands

Use `redis_sync_admin.py` to monitor and manage sync:

```bash
# Show health and sync status
python redis_sync_admin.py

# Detailed verification report
python redis_sync_admin.py verify

# List recent learnings
python redis_sync_admin.py learnings 20

# List recent signals
python redis_sync_admin.py signals 20

# Preview what would be resynced
python redis_sync_admin.py resync --dry-run

# Actually resync (fixes mismatches)
python redis_sync_admin.py resync

# Migrate learnings to Redis
python redis_sync_admin.py migrate

# Show statistics
python redis_sync_admin.py stats
```

## Integration Roadmap

### Phase 1: Verify Current State ✅ (Next Step)
```bash
python redis_sync_admin.py verify
python redis_sync_admin.py health
```

This shows:
- What's in Redis vs files
- Whether they're in sync
- Health status
- Any out-of-sync items

### Phase 2: Enable Sync Layer (After Phase 1)
1. Install sync layer in coordinator_api
   ```python
   from coordinator_api_sync_adapter import install_sync_layer
   install_sync_layer()
   ```

2. Run integration tests
   ```bash
   python test_sync_integration.py
   ```

3. Verify it worked
   ```bash
   python redis_sync_admin.py health
   ```

### Phase 3: Migrate Historical Data (Optional)
```bash
python redis_sync_admin.py migrate
```
Moves learnings.jsonl into Redis with proper indexing.

### Phase 4: Set Up Continuous Monitoring (Optional)
Run health checks periodically:
```python
from redis_sync_coordinator import RedisSyncCoordinator

coordinator = RedisSyncCoordinator("monitor")
while True:
    health = coordinator.health_check()
    if health['sync_status']['health'] != 'green':
        # Alert or auto-resync
        pass
    time.sleep(300)  # Check every 5 minutes
```

## Data Flow

### Before (Current)
```
Agent → coordinator_api._emit_signal()
        ├─ Try: Redis.xadd()
        └─ Fall back: Write to file
        (No verification, no sync status)
```

### After (Integrated)
```
Agent → coordinator_api._emit_signal()
        ↓ (patched)
RedisSyncCoordinator.emit_signal()
        ├─ Try: Redis.hset(with hash)
        ├─ Write to: file with hash
        └─ Log: sync_metadata.jsonl (audit trail)
        
Verification (continuous):
├─ Health checks every N minutes
├─ Detects mismatches automatically
├─ Can auto-resync if configured
└─ Admin tools for manual verification
```

## File Storage Structure

```
session_logs/
├─ signals_agent_id.jsonl          ← All signals for this agent
├─ learnings.jsonl                 ← All learnings (shared)
├─ sync_metadata.jsonl             ← Audit trail of all sync ops
├─ health_check.jsonl              ← Health monitoring history
├─ instance_status_*.jsonl         ← Instance heartbeats
└─ agent_*.jsonl                   ← Legacy format (still kept)
```

## Redis Key Structure

```
Redis (at localhost:16379):

Signal Keys:
├─ signal:action:signal-id-123        → {data: JSON, hash: SHA256}
├─ signal:decision:signal-id-456      → {data: JSON, hash: SHA256}
└─ signal:learning:signal-id-789      → {data: JSON, hash: SHA256}

Learning Keys:
├─ learn:experiment:exp_name_123      → {what_tried, actual, ...}
├─ learn:experiments:all              → [exp_1, exp_2, ...] (list)
├─ learn:category:performance         → {exp_1, exp_2, ...} (set)
├─ learn:anti_patterns                → {pattern_1, pattern_2} (set)
└─ learn:agent:agent_id               → [exp_1, exp_2, ...] (list)

Status Keys:
├─ instance:status:instance-123       → {status: {...}, ttl: 300}
└─ active_instances                   → {inst_1, inst_2, ...} (set, TTL: 300)
```

## Success Criteria

- ✅ All new signals go through RedisSyncHandler with verification
- ✅ All learnings written to both Redis and file with matching hashes
- ✅ Health monitoring shows green (in_sync=true) for all signals
- ✅ Resync routine can fix mismatches without data loss
- ✅ Agent reads learnings successfully from both sources
- ✅ Phase 1.5 test passes with new sync layer

## Troubleshooting

### Redis Not Available
The system continues to work using files. No data loss.
```bash
python redis_sync_admin.py verify
# Will show many "file_only" entries, but no errors
```

### Out-of-Sync Items Detected
Use dry-run to see what would be fixed:
```bash
python redis_sync_admin.py resync --dry-run
```

Then actually resync:
```bash
python redis_sync_admin.py resync
```

### Learnings Not Migrating to Redis
```bash
python redis_sync_admin.py migrate
```

Manually moves learnings.jsonl to Redis with proper indexing.

## Examples

### Example 1: Agent Learning from Previous Agent

```python
from coordinator_api_sync_adapter import install_sync_layer
from coordinator_api import initialize
from learning_store import get_recommendations

install_sync_layer()

# Agent B starts
api = initialize("agent_b")

# Get recommendations from previous learnings
recommendations = get_recommendations("performance optimization")

# Agent B applies learnings
for rec in recommendations:
    if rec['success'] == 'yes':
        api.decision(
            decision_name=f"apply_{rec['experiment']}",
            outcome="yes",
            reason=f"Learned from {rec['experiment']}: {rec['recommendation']}"
        )

# Agent B continues work
api.action("optimizing_code")
api.completion(success=True, learned="Optimization complete")
```

### Example 2: Crash Recovery

```python
# System crashes after writing signal to file but before Redis
# When system restarts:

from redis_sync_coordinator import RedisSyncCoordinator

coordinator = RedisSyncCoordinator("agent")

# Check sync status
report = coordinator.verify_all_synced()
print(f"Out of sync: {report['out_of_sync']}")

# Auto-resync to recover
coordinator.resync_all()

# All data restored
```

### Example 3: Manual Health Monitoring

```python
from redis_sync_coordinator import RedisSyncCoordinator
import time

coordinator = RedisSyncCoordinator("monitor")

while True:
    health = coordinator.health_check()
    
    if health['redis_available']:
        print("✓ Redis online")
    else:
        print("✗ Redis offline (using file fallback)")
    
    print(f"Signals: {health['signals_in_file']}")
    print(f"Learnings: {health['learnings_in_file']}")
    print(f"Sync health: {health['sync_status']['health']}")
    
    time.sleep(300)
```

---

**Status:** Ready to integrate and test.

Next step: Run `python redis_sync_admin.py verify` to see current state.
