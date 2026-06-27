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

## 🚀 LAUNCH OPTIONS

### Quick Start

```bash
python E:\AI-Setup\launch.py
```

This presents a menu with 5 options:

| Option | Mode | Best For |
|--------|------|----------|
| 1 | Single Primed Agent | Focused single-task work |
| 2 | Generator + Analyst | Proposal writing, code review |
| 3 | Custom Role Launch | Specific role (generator/analyst/master/etc) |
| 4 | Spawn Helper | Add another agent to help |
| 5 | System Status | Check active agents and blackboard |

### Auto-Launch

```bash
# Launch single agent
python E:\AI-Setup\launch.py --auto 1

# Launch generator + analyst pair
python E:\AI-Setup\launch.py --auto 2

# Check status
python E:\AI-Setup\launch.py --status
```

### Spawning Helpers from Within an Agent

```python
from multi_agent import spawn_helper_agent, create_help_request

# Request a helper (auto-launches)
spawn_helper_agent(
    help_type="analyst",
    description="Need help reviewing authentication code",
    context={"file": "auth.py", "task": "security review"}
)

# Or just create a request for another agent to pick up
create_help_request(
    help_type="researcher",
    description="Find best practices for rate limiting",
    priority="high"
)
```

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

### Redis HA Cluster (Recommended)

| Container | Port | Purpose |
|-----------|------|---------|
| `redis-master` | 6379 | Primary - writes |
| `redis-replica1` | 6380 | Read replica |
| `redis-replica2` | 6381 | Read replica |
| `sentinel1` | 26379 | Failover monitor |
| `sentinel2` | 26380 | Failover monitor |
| `sentinel3` | 26381 | Failover monitor |

**Commands:**
```bash
cd E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml up -d   # Start HA cluster
docker compose -f docker-compose-ha.yml down     # Stop HA cluster
```

### Legacy Containers

| Container | Port | Purpose |
|-----------|------|---------|
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

## 🔄 REDIS SYNC SERVICE

The Redis Sync Service automatically syncs session logs to Redis for persistent context.

### Start Sync Service

```bash
# Start background sync poller (runs every 5 seconds)
python E:\AI-Setup\redis_sync.py --daemon

# Check sync status
python E:\AI-Setup\redis_sync.py --status

# Reset and re-sync all
python E:\AI-Setup\redis_sync.py --reset
```

### What Gets Synced

- Session actions from `session_all.jsonl`
- Chat history
- Errors and faults
- Active sessions

### Sync State

Sync positions are tracked in `blackboard_data/redis_sync_state.json` to avoid re-syncing.

---

## 🔌 MCP SERVER (Model Context Protocol)

The system includes an MCP server that exposes session context, Redis data, and knowledge base to AI clients.

### Start MCP Server

```bash
# Stdio transport (for OpenCode)
python E:\AI-Setup\ai_setup_mcp.py

# HTTP transport (for Claude Desktop and other clients)
python E:\AI-Setup\ai_setup_mcp.py --http --port 8080
```

### MCP Resources Available

| Resource | Description |
|----------|-------------|
| `session://current` | Current session info |
| `session://actions` | Current session actions |
| `session://log` | Session log entries |
| `redis://stats` | Redis statistics |
| `redis://keys` | All Redis keys |
| `redis://key/{name}` | Specific key value |
| `knowledge://recent` | Recent knowledge entries |
| `learnings://all` | All learnings |
| `context://summary` | Context summary |

### MCP Tools Available

| Tool | Description |
|------|-------------|
| `get_session_info` | Get detailed session info |
| `search_knowledge` | Search knowledge base |
| `search_learnings` | Search learnings |
| `get_session_history` | Get historical sessions |
| `get_chat_history` | Get chat messages |
| `get_errors` | Get error history |
| `search_session_logs` | Search log files |
| `get_current_task` | Get current task |
| `get_active_blockers` | Get current blockers |

### OpenCode MCP Configuration

Add to your OpenCode MCP config:
```json
{
  "mcpServers": {
    "ai-setup": {
      "command": "python",
      "args": ["E:\\AI-Setup\\ai_setup_mcp.py"]
    }
  }
}
```

### Claude Desktop MCP Configuration

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ai-setup": {
      "command": "python",
      "args": ["E:\\AI-Setup\\ai_setup_mcp.py"]
    }
  }
}
```

---

## 🤖 MULTI-AGENT MODE

The system supports multiple OpenCode instances running concurrently via Redis + VectorStore.

### Initialization

```python
from multi_agent import initialize_multi_agent, get_agent_registry, get_message_bus

# On startup (after session_logger)
result = initialize_multi_agent(
    session_id=SESSION_ID,
    session_unique=SESSION_UNIQUE,
    role="generator"  # generator, analyst, master, orchestrator, general
)

print(f"Agent ID: {result['agent_id']}")
print(f"Other agents: {len(result['active_agents'])}")
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `AgentRegistry` | Track active agents, heartbeat, presence |
| `MessageBus` | Vector-based agent-to-agent messaging |
| `SharedWorkspace` | Collaborative task workspace with locking |

### Detecting Other Agents

```python
registry = get_agent_registry()

# Check if any other agents are active
if registry.is_any_other_agent_active():
    agents = registry.get_active_agents()
    for agent in agents:
        print(f"{agent.agent_id}: {agent.role} in {agent.session_id}")

# Get agents by role
analysts = registry.get_agent_by_role("analyst")
```

### Agent Messaging

```python
bus = get_message_bus()

# Send message to specific agent
bus.send_message(
    to_agent="analyst",
    msg_type="task_request",
    content="Review code for security",
    metadata={"file": "auth.py"}
)

# Broadcast to all agents
bus.broadcast_to_agents(
    msg_type="alert",
    content="Starting deployment",
    metadata={"target": "production"}
)

# Search messages semantically
results = bus.search_messages("security review", top_k=5)
```

### Shared Workspace

```python
ws = get_shared_workspace()

# Put item (auto-locks if another agent is editing)
ws.put("current_task", {"task": "refactor", "file": "main.py"})

# Lock for exclusive access
ws.lock("shared_resource")

# Release lock
ws.unlock("shared_resource")

# Search shared items
items = ws.search_items("refactor task")
```

### Collaborative Spaces

Spaces are isolated workspaces for different projects or tasks:

```python
ws = get_shared_workspace()

# Create a new space for a project
ws.create_space("project_alpha", "Main development workspace")

# List all spaces
spaces = ws.get_spaces()
for s in spaces:
    print(f"  {s['name']}: {s['description']}")
```

### Help Requests

When an agent needs assistance, it can create a help request:

```python
from multi_agent import create_help_request, spawn_helper_agent, get_pending_help_requests

# Create a help request (for another agent to pick up)
request = create_help_request(
    help_type="analyst",
    description="Review authentication flow for security issues",
    priority="high"
)

# Or spawn a helper immediately
spawn_helper_agent(
    help_type="tester",
    description="Run tests on the new authentication module",
    context={"module": "auth", "test_suite": "integration"}
)

# Check pending requests
pending = get_pending_help_requests()
for req in pending:
    print(f"[{req.help_type}] {req.description} from {req.from_agent}")
```

### Multi-Agent Escape Conditions

| Escape | Description |
|---------|-------------|
| `MULTI_AGENT_CONFLICT` | Acting without coordinating with other agents |
| `IGNORE_OTHER_AGENTS` | Not checking for active agents before actions |
| `RESOURCE_LOCKED_BY_OTHER` | Trying to access locked resource |

### Harness Enforcement in Multi-Agent Mode

```python
he = get_harness_enforcer()

# Check if running in multi-agent mode
if he.is_multi_agent_mode():
    other_agents = he.get_other_agents()
    print(f"{len(other_agents)} other agent(s) active")
    
    # Check if resource is locked
    locked_by = he.check_resource_lock("important_file.py")
    if locked_by:
        print(f"Locked by: {locked_by['agent_id']}")

# Send message to other agents
he.send_agent_message("analyst", "query", "Need code review")
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
| `MULTI_AGENT_CONFLICT` | Not coordinating with other agents | HIGH |
| `RESOURCE_LOCKED_BY_OTHER` | Accessing locked resource | HIGH |

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
