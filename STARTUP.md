# STARTUP.md - BreakThrough Stack Initialization
> **FOR ALL AGENTS**: Read this FIRST. This is the only file you need on startup.

**Version**: 4.0  
**Updated**: 2026-04-14  
**Supersedes**: bootstrap.md, bootstrap_generator.md, bootstrap_analyst.md, bootstrap_master.md

---

## SESSION CHANGE DETECTION

On every startup, the system automatically detects if this is:
- **NEW SESSION**: AI/user restarted → RE-PRIME TRIGGERED
- **CONTINUATION**: Same session continuing → Normal operation

Session change is detected by comparing SESSION_ID from `session_logger.py` against stored state in `blackboard_data/session_state.json`.

---

## 🚀 STARTUP SEQUENCE (Run These First)

### Step 1: Initialize Session Manager

```python
import sys
sys.path.insert(0, r'E:\AI-Setup')

from session_manager import check_and_reprime, get_session_manager
from session_logger import SESSION_ID, SESSION_UNIQUE

# This detects session changes and triggers re-prime if needed
state = check_and_reprime(SESSION_ID, SESSION_UNIQUE)

if state.is_new:
    print("=== NEW SESSION - RE-PRIME REQUIRED ===")
    print(get_session_manager().get_reprime_instructions())
else:
    print("Continuing session: " + SESSION_ID)
```

### Step 2: Start Redis (Enables Knowledge Base)

```python
import subprocess

# Start Redis container
result = subprocess.run(['docker', 'start', 'ai-redis'], capture_output=True)
print(result.stdout.decode() if result.stdout else "Redis started")
```

### Step 3: Initialize Blackboard (Clears Stale State)

```python
from blackboard import init_blackboard

bb = init_blackboard(force=False)  # Only initializes if no state file exists
print(f"Blackboard state: {bb.get_state()}")
```

### Step 4: Activate Logging

```python
from session_logger import log, log_chat, log_error, verify_logs

log("session_start", f"New session - {SESSION_ID}", source="system")
log_chat("system", "Bootstrap complete - READY")

# Verify logging integrity
result = verify_logs(100)
print(f"Logging: Valid={result['valid']}, Corrupted={result['corrupted']}")
```

### Step 5: Get Catch-Up from Previous Session

```python
from crash_recovery import get_summary, auto_recover_on_startup

# Check for previous session issues
auto_recover_on_startup()

# Get full summary
summary = get_summary()
print(f"Previous sessions: {len(summary.get('sessions', []))}")
print(f"Chat history: {len(summary.get('chat_history', []))} messages")
```

### Step 6: Check Services Health

```python
from master import check_prerequisites

for name, status in check_prerequisites():
    print(f"  {name}: {status}")
```

---

## 📋 COMPLETE STARTUP SCRIPT

Save as `E:\AI-Setup\init_session.py` and run on every startup:

```python
#!/usr/bin/env python3
"""
BreakThrough Stack - Session Initialization
Run this at the START of every session.
"""
import sys
sys.path.insert(0, r'E:\AI-Setup')

def initialize():
    """Full initialization sequence"""
    results = []
    
    # 1. Session detection
    from session_manager import check_and_reprime, get_session_manager
    from session_logger import SESSION_ID, SESSION_UNIQUE
    state = check_and_reprime(SESSION_ID, SESSION_UNIQUE)
    results.append(("session", state.is_new, state.session_id))
    
    # 2. Start Redis
    import subprocess
    subprocess.run(['docker', 'start', 'ai-redis'], capture_output=True)
    results.append(("redis", True, "started"))
    
    # 3. Initialize blackboard
    from blackboard import init_blackboard
    bb = init_blackboard()
    results.append(("blackboard", True, bb.get_state()))
    
    # 4. Activate logging
    from session_logger import log, verify_logs
    log("session_start", f"Initialized - {SESSION_ID}", source="system")
    result = verify_logs(100)
    results.append(("logging", result['valid'], f"Corrupted={result['corrupted']}"))
    
    # 5. Catch-up
    from crash_recovery import get_summary
    summary = get_summary()
    results.append(("catchup", True, f"{len(summary.get('sessions', []))} sessions"))
    
    # Print results
    print("\n" + "=" * 50)
    print("INITIALIZATION RESULTS")
    print("=" * 50)
    for name, success, info in results:
        status = "OK" if success else "RE-PRIME"
        print(f"  {name}: [{status}] {info}")
    
    if state.is_new:
        print("\n" + "=" * 50)
        print("RE-PRIME REQUIRED - Read STARTUP.md Section 3")
        print("=" * 50)
        print(get_session_manager().get_reprime_instructions())
    
    return state

if __name__ == "__main__":
    initialize()
```

---

## 🔄 RE-PRIME SEQUENCE

When `state.is_new == True`, you MUST do these things before proceeding:

### 1. Re-read Core Documentation
```python
# Read these files in order:
# 1. E:\AI-Setup\STARTUP.md (this file) - Already reading
# 2. E:\AI-Setup\ARCHITECTURE.md - System design
# 3. E:\AI-Setup\AGENT_PRIMER.md - Best practices
# 4. E:\AI-Setup\COORDINATION_PRIMER.md - Enterprise patterns
```

### 2. Re-initialize State Machine
```python
from blackboard import init_blackboard
bb = init_blackboard(force=True)  # Force fresh state
print(f"Fresh state: {bb.get_state()}")
```

### 3. Get Context from Previous Session
```python
from crash_recovery import recover, get_summary
summary = get_summary()

# Print key info
if summary.get('sessions'):
    for s in summary['sessions'][:3]:
        print(f"  [{s['session_id']}] {s.get('task', 'unknown')}")

if summary.get('chat_history'):
    print("\nRecent chat:")
    for c in summary['chat_history'][-5:]:
        print(f"  {c.get('role')}: {c.get('message', '')[:60]}")
```

### 4. Check for Unfinished Work
```python
from blackboard import Blackboard
bb = Blackboard()

# Check if there was a task in progress
state = bb.get_state()
if state != "IDLE":
    print(f"WARNING: Previous session had state={state}")
    print("Check blackboard_data/ for artifacts")
```

---

## 📁 KEY FILES

| File | Purpose |
|------|---------|
| `E:\AI-Setup\STARTUP.md` | **THIS FILE** - Start here |
| `E:\AI-Setup\ARCHITECTURE.md` | System architecture |
| `E:\AI-Setup\AGENT_PRIMER.md` | Best practices, ports, Docker |
| `E:\AI-Setup\COORDINATION_PRIMER.md` | Enterprise patterns |
| `E:\AI-Setup\blackboard.py` | State machine |
| `E:\AI-Setup\session_manager.py` | Session tracking & re-prime |
| `E:\AI-Setup\session_logger.py` | Action/chat logging |
| `E:\AI-Setup\crash_recovery.py` | Post-crash analysis |

---

## 🔧 KNOWLEDGE BASE (KB)

**Before ANY new task**, search the KB:
```python
from knowledge_base import KB
kb = KB()

kb.search('your_topic')  # Search for existing learnings
kb.get_model_context('your_model')  # Get model-specific context
```

**Required KB searches before ML/AI/GPU work:**
- `kb.search('rocm')` - AMD GPU setup
- `kb.search('gpu')` - General GPU
- `kb.search('torch')` - PyTorch
- `kb.search('yolo')` - Vision models

---

## 🏗️ BLACKBOARD STATE MACHINE

The blackboard manages task workflow:

```
IDLE → PLANNING → REVIEW → EXECUTING → VERIFYING → DONE
                        ↓
                      ERROR
```

| Phase | Who | Waits For |
|-------|-----|-----------|
| IDLE | - | User task |
| PLANNING | Generator | Writing proposal.json |
| REVIEW | Analyst | proposal.json ready |
| EXECUTING | Generator | PASS verdict |
| VERIFYING | Analyst | Execution complete |
| DONE | - | - |

---

## 📊 DOCKER SERVICES

| Container | Port | Purpose |
|-----------|------|---------|
| `ai-redis` | 6379 | Knowledge base & state |
| `ai-ollama` | 11434 | LLM inference |
| `ai-open-webui` | 3000 | Web interface |
| `ai-voice` | 5000-5001 | Speech I/O |

**Commands:**
```bash
docker ps                    # Check running
docker start ai-redis       # Start Redis
docker logs ai-redis        # View logs
```

---

## 🛡️ HARNESS ENFORCEMENT

The system includes **Harness Enforcer** (`harness_enforcer.py`) that continuously monitors for escape conditions:

### Detected Escape Conditions

| Escape | Description | Severity |
|--------|-------------|----------|
| `SKIP_REPRIME` | Acting without re-priming on new session | CRITICAL |
| `SKIP_VERIFY` | Running code without verification | HIGH |
| `SKIP_LOGGING` | Actions without logging | MEDIUM |
| `SKIP_KB_SEARCH` | Building without checking KB | HIGH |
| `SKIP_HEALTH_CHECKS` | Deploying without health checks | CRITICAL |
| `SKIP_BLACKBOARD_WORKFLOW` | Executing without proper phases | HIGH |
| `SKIP_SELF_CORRECTION` | Analyst ignoring fault learnings | CRITICAL |
| `SKIP_TESTING` | Assuming things work without testing | HIGH |
| `IMPATIENT_EXIT` | Exiting without session summary | MEDIUM |

### Using Harness Enforcer

```python
from harness_enforcer import get_harness_enforcer

he = get_harness_enforcer()

# Get compliance report anytime
he.print_compliance_report()

# Check escape risk level
report = he.get_compliance_report()
print(f"Escape Risk: {report['escape_risk']}")

# Verify specific action is allowed
if not he.enforce_pre_action("deploy", {"target": "service"}):
    print("BLOCKED - Health checks required")
```

### Install Enforcement Hooks

```python
from harness_enforcer import install_harness_hooks
install_harness_hooks()  # Hooks into session_logger
```

---

## 📜 MISSION-CRITICAL DIRECTIVES

These directives from `deployment_framework.py` are **ALWAYS ENFORCED**:

### 1. TEST BEFORE DEPLOY
> **Never assume, always verify**

Before any deployment or significant action:
```python
# Verify it works first
result = verify_logs(100)
if result['corrupted'] > 0:
    raise RuntimeError("Cannot deploy - logging corrupted")
```

### 2. HEALTH CHECKS
> **Every component must prove it's working**

```bash
python E:\AI-Setup\deployment_framework.py --all
```

### 3. GRACEFUL DEGRADATION
> **System survives component failures**

Always have fallbacks:
- Redis unavailable → Use file-only mode
- GPU unavailable → Use CPU fallback
- Ollama unavailable → Try vLLM fallback

### 4. FAILURE MODE ANALYSIS
> **Every failure anticipated and handled**

```python
try:
    result = risky_operation()
except KnownError as e:
    handle_known_failure(e)  # Anticipated
except Exception as e:
    log_error("unknown_failure", str(e))
    escalate()
```

### 5. ROLLBACK CAPABILITY
> **Can return to previous state**

Before any change:
```python
backup_current_state()
try:
    make_change()
except:
    rollback_to_previous()
    raise
```

### 6. OBSERVABILITY
> **Everything logged, nothing hidden**

```python
log("action", "description", {"key": "value"}, source="system")
# Never: log("action", "description")  # Missing data dict!
```

---

## ⚠️ CRITICAL RULES

1. **Start Redis FIRST** - Enables KB for all operations
2. **Log EVERY action** - Use `log()` with data dict
3. **Check KB BEFORE building** - Search for existing learnings
4. **Use full paths** - `python.exe` not `python`
5. **Never skip re-prime** - If `state.is_new == True`, do the re-prime sequence
6. **TEST BEFORE DEPLOY** - Never assume it works, verify first
7. **Respect FAIL verdicts** - Analyst said NO, revise and resubmit
8. **Create session summary** - Before any exit after active session

---

## 🔄 SESSION CONTINUITY

The system maintains continuity via:
1. **JSONL logs** - All actions in `session_logs/session_all.jsonl`
2. **Redis state** - Session data in Redis
3. **Knowledge base** - Cross-session learnings
4. **Session history** - `blackboard_data/session_history.json`

---

## 🆘 IF SOMETHING GOES WRONG

### Redis won't start
```bash
docker start ai-redis
docker logs ai-redis
```

### Session logger corrupted
```python
from session_logger import verify_logs
result = verify_logs(1000)
print(f"Valid: {result['valid']}, Corrupted: {result['corrupted']}")
```

### Blackboard stuck in ERROR
```python
from blackboard import init_blackboard
bb = init_blackboard(force=True)  # Full reset
```

### Need to force re-prime
```python
from session_manager import get_session_manager
sm = get_session_manager()
# Delete session_state.json to force re-prime
import os
os.remove(r"E:\AI-Setup\blackboard_data\session_state.json")
```

---

**Welcome to BreakThrough Stack!** 🎉
