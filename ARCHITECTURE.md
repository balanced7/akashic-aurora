# BREAKTHROUGH STACK - ENTERPRISE ARCHITECTURE v2.1
## Mission-Critical Autonomous Agent System

---

## DESIGN PRINCIPLES

1. **Zero Data Loss** - Enterprise backup and recovery
2. **Fault Tolerance** - Every component has failover
3. **GPU Portability** - Support multiple backends
4. **Session Continuity** - Never lose context

---

## CURRENT STATUS (2026-04-14)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| Redis | [OK] | WSL2 Docker | 30 keys, backed up, enterprise manager |
| Ollama | [OK] | Windows Native | CPU mode, 3.8s/token |
| vLLM | [DEGRADED] | WSL2 Docker | GPU blocked by amdgpu kernel module |
| Vision | [OK] | Windows Python | GPU-based Florence-2 (DirectML) |
| Backup System | [OK] | E:\AI-Setup\ | 5-min intervals, SHA-256 verified |

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

### 4. AUTOMATION

- PyAutoGUI + Naturo for desktop automation
- Gemini Bridge for escalation

### 5. BACKUP SYSTEM (Enterprise Grade)

- **Interval:** 5-minute routine backups
- **Integrity:** SHA-256 verification
- **Storage:** Dual location (`E:\AI-Setup\` + `E:\AI-Setup\assets\`)
- **Retention:** 24 hourly, 7 daily, 4 weekly
- **Monitoring:** 30-second health checks
- **Catalog:** `E:\AI-Setup\blackboard_data\redis_backups\backup_catalog.json`

---

## FILE INVENTORY

### Core
- `E:\AI-Setup\blackboard.py` - Hybrid state machine
- `E:\AI-Setup\master.py` - Traffic controller
- `E:\AI-Setup\model_lifecycle.py` - VRAM management
- `E:\AI-Setup\config.py` - GPU provider configuration

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
| `E:\AI-Setup\assets\` | Cached downloads, models |
| `E:\AI-Setup\session_logs\` | JSONL session logs |
| `E:\AI-Setup\dockerized-ai\` | Docker compose files |
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
| 2026-04-14 | v2.1 | Updated status: Ollama working on CPU |
| 2026-04-13 | v2.0 | Restructured for WSL2, Redis in Docker |
| 2026-04-12 | v1.0 | Initial architecture |
