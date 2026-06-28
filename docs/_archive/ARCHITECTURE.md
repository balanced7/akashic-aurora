# AKASHIC AURORA - ENTERPRISE ARCHITECTURE v2.1
## Mission-Critical Autonomous Agent System

---

## DESIGN PRINCIPLES

1. **Zero Data Loss** - Enterprise backup and recovery
2. **Fault Tolerance** - Every component has failover
3. **GPU Portability** - Support multiple backends
4. **Session Continuity** - Never lose context

---

## CURRENT STATUS (2026-04-15)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| Redis | [OK] | Docker (ai-redis) | 30 keys, backed up, enterprise manager |
| Ollama | [OK] | Windows Native | CPU mode, 3.8s/token |
| vLLM | [DEGRADED] | WSL2 Docker | GPU blocked by amdgpu kernel module |
| Vision | [OK] | Windows Python | GPU-based Florence-2 (DirectML) |
| Backup System | [OK] | E:\AI-Setup\ | 5-min intervals, SHA-256 verified |
| Multi-Agent Comm | [OK] | Redis Streams + File | 100ms polling, operational alerts |
| MCP Server | [OK] | E:\AI-Setup\mcp_servers\agent_comm\ | FastMCP, 7 tools |
| Screenspace Toolkit | [NEW] | E:\AI-Setup\SCREENSPACE_TOOLKIT.md | Windows-MCP + UI Scout + Vision |

---

## GPU LIMITATION - KNOWN ISSUE

WSL2 Docker cannot provide AMD GPU access to ROCm because:

1. ROCm requires **amdgpu Linux kernel module**
2. WSL2 does not expose kernel module interface
3. `/dev/dxg` exists but ROCm does not use DirectX path

**This is an AMD/WSL2 architectural limitation, not a configuration issue.**

### Workarounds Available:

- **Ollama on Windows direct** (PRIMARY - works on CPU)
- **vLLM on CPU** (not available in ROCm build)
- **Native Linux with ROCm** (future option)
- **Wait for AMD WSL2 GPU support** (no timeline)

---

## ARCHITECTURE

```
+------------------------------------------------------------------+
|                        WINDOWS HOST                                |
|                                                                   |
|  +-------------+    +-------------+    +------------------------+ |
|  |   OLLAMA   |    |  PYTHON/    |    |   DOCKER (WSL2)        | |
|  |  (Native)  |    |  AUTOMATION |    |   +------------+        | |
|  +------+------+    +------+------+    |   |   REDIS   |        | |
|         |                  |          |   |  (Backup) |        | |
|         |         +--------+--------+ |   +------------+        | |
|         |         |     BLACKBOARD   | +------------------------+ |
|         |         |     (Redis)     |                           |
|         |         |  E:\AI-Setup\  |                           |
|         +-------->|                 |<----------+              |
|                   +-----------------+           |              |
|                                                     |              |
|  +-----------------------------------------------------+        |
|  |              GPU: AMD RX 9070 XT (gfx1201)          |        |
|  |              DirectML: Detected as privateuseone:0  |        |
|  |              Status: CPU Only (no ROCm/CUDA)        |        |
|  +-----------------------------------------------------+        |
+------------------------------------------------------------------+
```

---

## COMPONENTS

### 1. BLACKBOARD STATE (Redis)

**Location:** WSL2 Ubuntu-24.04 Docker  
**Container:** `wsl-ai-redis` (redis:alpine)  
**Backup:** `E:\AI-Setup\blackboard_data\redis_backups\`  
**Catalog:** `backup_catalog.json` with SHA-256 verification  
**Manager:** `E:\AI-Setup\redis_manager.py`

**Status:** 30 keys restored from backup

### 2. INFERENCE ENGINES

| Engine | Location | Status | GPU | Notes |
|--------|----------|--------|-----|-------|
| Ollama | Windows Native | PRIMARY | CPU | Working, 3.8s/token |
| vLLM | WSL2 Docker | DEGRADED | Blocked | ROCm needs amdgpu |
| Transformers | Windows | FALLBACK | CPU | Available |

### 3. VISION ENGINE

- Florence-2 on GPU (DirectML privateuseone:0)
- DirectML detects AMD 9070 XT as `privateuseone:0`
- Model architecture incompatibility for GPU inference

### 4. AUTOMATION (SCREENSPACE TOOLKIT)

**Documentation:** `E:\AI-Setup\SCREENSPACE_TOOLKIT.md`

| Layer | Tools | Purpose |
|-------|-------|---------|
| MCP Server | windows-mcp | Exposes click, type, scroll, move, shortcut, screenshot, app control |
| UI Inspection | Naturo, ui_scout.py | list_windows, see, find, bring_to_front |
| Vision | VisionEngine (Florence-2) | OCR, captioning, object detection |
| OCR | Tesseract, PaddleOCR, EasyOCR | Multi-engine text extraction |
| Window Mgmt | WindowZOrder, track/restore_window_order | Preserve window arrangement |

**Creative Tool Support:**
- Adobe Premiere/After Effects: ExtendScript + UI Automation
- FL Studio: Python API (flbot) + keyboard macros
- Brave: Selenium + DevTools Protocol

### 5. BACKUP SYSTEM (Enterprise Grade)

- **Interval:** 5-minute routine backups
- **Integrity:** SHA-256 verification
- **Storage:** Dual location (`E:\AI-Setup\` + `E:\AI-Setup\assets\`)
- **Retention:** 24 hourly, 7 daily, 4 weekly
- **Monitoring:** 30-second health checks
- **Catalog:** `E:\AI-Setup\blackboard_data\redis_backups\backup_catalog.json`

### 6. MULTI-AGENT COMMUNICATION SYSTEM

**Architecture Overview:**
```
OpenCode Instance (CLI)
    │
    ├── MCP Client ──────> MCP Server (agent_comm)
    │                              │
    │                              └── Redis Streams (messaging)
    │                              └── File Inbox (persistence)
    │                              └── Vector Store (semantic search)
    │
    └── Background Monitor (100ms polling)
             │
             └── Redis PubSub ────> Windows Notifications
```

**Key Components:**

| File | Purpose |
|------|---------|
| `multi_agent.py` | Agent registry, MessageBus, SharedWorkspace |
| `fast_agent_comm.py` | Redis Streams for reliable messaging |
| `background_monitor.py` | 100ms polling, file inbox, notifications |
| `agent_coordinator_v2.py` | Manifests, coordination, lock management |
| `operational_alerts.py` | Tiered alerts (CRITICAL/HIGH/NORMAL/LOW) |
| `agent_comm_helper.py` | Quick functions for OpenCode |
| `agent_dashboard.py` | Flask web dashboard (port 5050) |

**MCP Server (agent_comm):**

| Tool | Description |
|------|-------------|
| `send_message` | Send message to agent or broadcast |
| `check_messages` | Check inbox, returns structured messages |
| `get_active_agents` | List all active agents |
| `get_my_status` | Current manifest and alerts |
| `declare_operation` | Start operation (manifest + alert) |
| `complete_operation` | End operation |
| `search_messages` | Semantic vector search |

**Configuration:**
- OpenCode MCP config: `E:\AI-Setup\mcp_servers\agent_comm\opencode_mcp.json`
- Start with: `opencode mcp add agent_comm -- python -m agent_comm serve`

**Message Flow:**
1. Agent sends via `send_message()` → Redis Streams
2. Background monitor polls at 100ms
3. Messages written to file inbox
4. Other agents check via `check_messages()` or MCP tool
5. CRITICAL/HIGH alerts trigger Windows notifications

---

## FILE INVENTORY

### Core
- `E:\AI-Setup\blackboard.py` - Hybrid state machine
- `E:\AI-Setup\master.py` - Traffic controller
- `E:\AI-Setup\model_lifecycle.py` - VRAM management
- `E:\AI-Setup\config.py` - GPU provider configuration

### Multi-Agent Communication
- `E:\AI-Setup\multi_agent.py` - Agent registry, MessageBus, SharedWorkspace
- `E:\AI-Setup\fast_agent_comm.py` - Redis Streams messaging
- `E:\AI-Setup\background_monitor.py` - 100ms polling, notifications
- `E:\AI-Setup\agent_coordinator_v2.py` - Manifests, coordination
- `E:\AI-Setup\operational_alerts.py` - Tiered alert system
- `E:\AI-Setup\agent_comm_helper.py` - Quick check/send functions
- `E:\AI-Setup\agent_dashboard.py` - Flask web dashboard

### MCP Server
- `E:\AI-Setup\mcp_servers\agent_comm\` - MCP server package
  - `server.py` - FastMCP server implementation
  - `__init__.py` - Package exports
  - `opencode_mcp.json` - OpenCode configuration

### Docker
- `E:\AI-Setup\dockerized-ai\docker-compose-wsl2.yml` - WSL2 compose
- `E:\AI-Setup\dockerized-ai\start_wsl2.sh` - WSL2 startup

### Backup & Assets
- `E:\AI-Setup\redis_manager.py` - Enterprise Redis manager
- `E:\AI-Setup\redis_backup_fast.py` - Fast backup utility
- `E:\AI-Setup\assets_manager.py` - Download cache

### Automation
- `E:\AI-Setup\agentic_automation.py`
- `E:\AI-Setup\desktop_automation.py`
- `E:\AI-Setup\vision_engine.py`

### Escalation
- `E:\AI-Setup\escalation.py`
- `E:\AI-Setup\gemini_bridge.py`

---

## DATA PATHS

| Path | Purpose |
|------|---------|
| `E:\AI-Setup\blackboard_data\` | Redis backups, logs |
| `E:\AI-Setup\blackboard_data\agent_coordination\` | Multi-agent coordination state |
| `E:\AI-Setup\blackboard_data\agent_coordination\inbox\{agent_id}\` | Per-agent message inbox |
| `E:\AI-Setup\blackboard_data\agent_coordination\manifests\{agent_id}.json` | Agent manifests |
| `E:\AI-Setup\blackboard_data\agent_coordination\alerts\active_alerts.json` | Active alerts |
| `E:\AI-Setup\assets\` | Cached downloads, models |
| `E:\AI-Setup\session_logs\` | JSONL session logs |
| `E:\AI-Setup\dockerized-ai\` | Docker compose files |
| `E:\AI-Setup\mcp_servers\agent_comm\` | MCP server package |
| `E:\AI-Setup\ARCHITECTURE.md` | This document |

---

## NEXT STEPS

1. **[CRITICAL]** Test full Ollama inference pipeline
2. **[HIGH]** Integrate Ollama as primary inference
3. **[HIGH]** Verify automation pipeline
4. **[MEDIUM]** Document all learnings in Redis
5. **[MEDIUM]** Set up monitoring alerts

---

## REVISION HISTORY

| Date | Version | Changes |
|------|---------|---------|
| 2026-04-15 | v2.2 | Added multi-agent comm system + MCP server |
| 2026-04-14 | v2.1 | Updated status: Ollama working on CPU |
| 2026-04-13 | v2.0 | Restructured for WSL2, Redis in Docker |
| 2026-04-12 | v1.0 | Initial architecture |
