"""
AGENT PRIMER - BREAKTHROUGH STACK
=================================
Every agent MUST read this on startup. This is the source of truth.

Version: 2.2
Updated: 2026-04-15

TABLE OF CONTENTS:
1. System Architecture
2. Port Registry (Critical)
3. Docker Best Practices
4. Redis Backup Requirements
5. GPU/ROCm Setup
6. Web Fetch Standards
7. Testing Requirements
8. Failure Mode Handling
9. Screenspace Toolkit (GUI Automation)

Search keys: "primer", "best_practices", "architecture", "ports", "docker", "screenspace", "gui_automation"
"""

# ============================================================================
# SECTION 1: SYSTEM ARCHITECTURE
# ============================================================================

SYSTEM_ARCHITECTURE = """
BREAKTHROUGH STACK ARCHITECTURE:

Windows Host (Docker Desktop + WSL2)
├── Windows Docker
│   ├── ai-ollama (port 11434) - PRIMARY INFERENCE
│   ├── ai-open-webui (port 3000)
│   └── ai-voice (port 5000/5001)
│
├── WSL2 Ubuntu-24.04
│   ├── Docker Daemon
│   │   └── wsl-ai-redis (port 6379) - STATE STORE
│   │
│   └── ROCm 7.2.1 + librocdxg
│       └── GPU: AMD RX 9070 XT (gfx1201)
│
└── Python/Automation
    └── E:\\AI-Setup\\

KEY PATHS:
- E:\\AI-Setup\\blackboard_data\\redis_backups\\ - Redis backups
- E:\\AI-Setup\\assets\\ - Downloaded assets cache
- E:\\AI-Setup\\ARCHITECTURE.md - Architecture doc
"""

# ============================================================================
# SECTION 2: PORT REGISTRY (CRITICAL - NO CONFLICTS)
# ============================================================================

PORT_REGISTRY = """
CRITICAL: Before deploying ANY container, check port availability.

REGISTERED PORTS:
- 6379: Redis (wsl-ai-redis) - NEVER CHANGE
- 11434: Ollama (ai-ollama) - PRIMARY INFERENCE
- 8000: vLLM (planned)
- 3000: Open WebUI (ai-open-webui)
- 5000/5001: Voice service
- 8080: Knowledge API

RULE: When adding a new service:
1. Query Redis: HGET system:ports <service>_port
2. If port exists, use it
3. If not, allocate from dynamic range 9000-65535
4. Document new allocation in Redis: HSET system:ports <service>_port <port>

AVOID CONFLICTS:
- WSL2 Docker and Windows Docker share the same network
- Never bind two containers to same port
- Check 'docker ps' before starting new containers
"""

# ============================================================================
# SECTION 3: DOCKER BEST PRACTICES
# ============================================================================

DOCKER_PRACTICES = """
ENTERPRISE DOCKER PRACTICES:

1. RESTART POLICIES
   - Use 'restart: unless-stopped' for all production containers
   - Test restart: docker update --restart unless-stopped <container>

2. HEALTH CHECKS
   - Define HEALTHCHECK in Dockerfile
   - Test: docker inspect --format='{{.State.Health.Status}}' <container>

3. LOGGING
   - Check logs: docker logs <container> --tail 50
   - Daemon logs: %LOCALAPPDATA%\\Docker\\log\\vm\\dockerd.log

4. PORT CONFLICTS (CRITICAL)
   - Before docker run, verify port not in use
   - Check: docker ps | grep <port>
   - WSL2 containers and Windows containers share host network

5. CONTAINER NAMING
   - Prefix with context: wsl-ai-, ai-, etc.
   - Never use generic names like 'redis' or 'app'

6. GPU ACCESS (ROCm)
   - Mount: /dev/dxg (only device needed in WSL2)
   - Mount: /opt/rocm-7.2.1:/opt/rocm:ro
   - Mount: /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro
   - Env: HSA_ENABLE_DXG_DETECTION=1
   - Env: LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib
   - Env: ROCM_PATH=/opt/rocm
   - DO NOT use /dev/kfd or /dev/dri - they don't exist in WSL2

7. VOLUMES
   - Always mount persistent data to E:\\AI-Setup\\
   - Never store critical data in container filesystem
"""

# ============================================================================
# SECTION 4: REDIS BACKUP REQUIREMENTS (ZERO DATA LOSS)
# ============================================================================

REDIS_BACKUP = """
REDIS BACKUP REQUIREMENTS:

1. ALWAYS BACKUP BEFORE CHANGES
   - Command: python E:\\AI-Setup\\redis_backup_fast.py
   - Verify: python E:\\AI-Setup\\redis_manager.py --verify

2. ROUTINE BACKUPS
   - Interval: Every 5 minutes
   - Manager: E:\\AI-Setup\\redis_manager.py --monitor
   - Catalog: E:\\AI-Setup\\blackboard_data\\redis_backups\\backup_catalog.json

3. VERIFICATION
   - SHA-256 checksum on every backup
   - Test restore weekly: python E:\\AI-Setup\\redis_manager.py --test-restore

4. FORCE SAVE (Before any risky operation)
   - WSL: docker exec wsl-ai-redis redis-cli SAVE
   - Then: docker exec wsl-ai-redis redis-cli BGSAVE

5. DUAL LOCATION
   - Primary: E:\\AI-Setup\\blackboard_data\\redis_backups\\
   - Secondary: E:\\AI-Setup\\assets\\redis_backups\\

6. HEALTH MONITORING
   - Check: python E:\\AI-Setup\\redis_manager.py --status
   - Health score should be 100/100
   - Alerts if backup older than 15 minutes
"""

# ============================================================================
# SECTION 5: GPU/ROCm SETUP (TESTED AND CONFIRMED)
# ============================================================================

GPU_SETUP = """
GPU SETUP - CONFIRMED WORKING (2026-04-14):

WSL2 Docker GPU Access for AMD RX 9070 XT (gfx1201):

1. DEVICES NEEDED
   - /dev/dxg (DirectX compute) - ONLY device needed

2. VOLUMES NEEDED
   - /opt/rocm-7.2.1:/opt/rocm:ro (ROCm with librocdxg)
   - /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro (WSL libs)

3. ENVIRONMENT
   - HSA_ENABLE_DXG_DETECTION=1
   - LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib
   - ROCM_PATH=/opt/rocm
   - HSA_OVERRIDE_GFX_VERSION=12.0.1

4. VERIFY GPU VISIBLE
   docker run --rm --device=/dev/dxg \\
     -v /usr/lib/wsl/lib:/usr/lib/wsl/lib \\
     -v /opt/rocm-7.2.1:/opt/rocm:ro \\
     -e HSA_ENABLE_DXG_DETECTION=1 \\
     -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib \\
     rocm/dev-ubuntu-24.04:7.1.1-complete \\
     rocminfo

   Expected: Agent 2 - gfx1201 - AMD Radeon RX 9070 XT

5. VERIFY OPENCL
   docker run --rm --device=/dev/dxg \\
     -v /usr/lib/wsl/lib:/usr/lib/wsl/lib \\
     -v /opt/rocm-7.2.1:/opt/rocm:ro \\
     -e HSA_ENABLE_DXG_DETECTION=1 \\
     -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib \\
     rocm/dev-ubuntu-24.04:7.1.1-complete \\
     clinfo

   Expected: Device Type: CL_DEVICE_TYPE_GPU, 16GB memory

6. WHAT DOESN'T WORK
   - /dev/kfd - Does NOT exist in WSL2
   - /dev/dri - Does NOT exist in WSL2
   - rocm-smi - Fails with "amdgpu not found" (expected)
"""

# ============================================================================
# SECTION 6: WEB FETCH STANDARDS
# ============================================================================

WEB_FETCH = """
ENTERPRISE WEB FETCH STANDARDS:

1. ALWAYS USE ENTERPRISE FETCHER
   - E:\\AI-Setup\\enterprise_web_fetch.py
   - Has retry logic, proper headers, caching

2. HEADERS (Make requests look legitimate)
   User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120...
   Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
   Accept-Language: en-US,en;q=0.9
   Accept-Encoding: gzip, deflate, br
   DNT: 1
   Connection: keep-alive

3. RETRY WITH BACKOFF
   - Max retries: 3
   - Exponential backoff: 1s, 2s, 4s
   - On 404: Don't retry (permanent)

4. FALLBACK URLS
   - Keep alternative URLs for critical docs
   - GitHub API as fallback: api.github.com

5. CACHING
   - Cache successful responses
   - Max age: 24 hours
   - Clear cache: Delete E:\\AI-Setup\\blackboard_data\\web_cache\\

6. COMMON FAILURES
   - 404: Page moved or deleted - try alternative
   - 429: Rate limited - wait and retry
   - Timeout: Reduce timeout, retry
"""

# ============================================================================
# SECTION 7: TESTING REQUIREMENTS
# ============================================================================

TESTING = """
TESTING BEFORE DEPLOY (ENTERPRISE STANDARD):

1. EVERY COMPONENT
   - Health check must pass before marking deployed
   - Test edge cases, not just happy path
   - Document failure modes

2. DOCKER CONTAINERS
   - Verify port not in use: docker ps | grep <port>
   - Verify container starts: docker ps
   - Verify logs clean: docker logs <container>
   - Verify health: docker inspect --format='{{.State.Health.Status}}'

3. INFERENCE
   - Actual inference test, not just API ping
   - Verify response format
   - Measure latency

4. BACKUP/RESTORE
   - Test backup creation
   - Test restore to fresh system
   - Verify data integrity

5. NETWORK
   - Verify containers can communicate
   - Check firewall rules
   - Verify port bindings

6. FAULT INJECTION
   - Stop container, verify auto-restart
   - Kill process, verify recovery
   - Simulate network failure
"""

# ============================================================================
# SECTION 8: FAILURE MODE HANDLING
# ============================================================================

FAILURE_MODES = """
KNOWN FAILURE MODES AND RESOLUTIONS:

1. CONTAINER PORT CONFLICT
   Symptom: "bind: address already in use"
   Resolution: 
   - Check: docker ps | grep <port>
   - Stop conflicting container
   - Or use different port via port manager

2. GPU NOT VISIBLE IN DOCKER
   Symptom: rocminfo shows only CPU agent
   Resolution:
   - Verify /dev/dxg exists: ls -la /dev/dxg
   - Verify ROCm mounted: docker exec <container> ls /opt/rocm/lib
   - Verify env vars: HSA_ENABLE_DXG_DETECTION=1

3. REDIS CONNECTION REFUSED
   Symptom: Error 10061 connecting to localhost:6379
   Resolution:
   - Check container: docker ps | grep redis
   - Start if stopped: docker start wsl-ai-redis
   - Check WSL2 Redis: wsl -d Ubuntu-24.04 -e docker ps

4. BACKUP CATALOG CORRUPTED
   Symptom: backup_catalog.json invalid
   Resolution:
   - Restore from latest good backup
   - python redis_manager.py --restore latest
   - Verify: python redis_manager.py --verify

5. WSL2 DOCKER GPU DRIVER NOT INITIALIZED
   Symptom: rocm-smi "Driver not initialized"
   Resolution:
   - This is EXPECTED in WSL2
   - Use rocminfo or clinfo to verify GPU
   - rocm-smi requires amdgpu kernel module

6. INFERENCE SLOW/ON CPU
   Symptom: Very slow inference
   Resolution:
   - Check if GPU detected: rocminfo
   - May be CPU fallback if GPU not accessible
   - Acceptable for now: CPU works, just slower
"""

# ============================================================================
# SECTION 9: SCREENSPACE TOOLKIT (GUI AUTOMATION)
# ============================================================================

SCREENSPACE_TOOLKIT = """
SCREENSPACE TOOLKIT - Automate any Windows GUI:

DOCUMENTATION: E:\\AI-Setup\\SCREENSPACE_TOOLKIT.md

CORE TOOLS:
1. Windows-MCP (pip install windows-mcp)
   - click, type, scroll, move, shortcut, screenshot, snapshot
   - app (launch/control windows), shell (PowerShell)
   - MCP server exposing Windows GUI control

2. UI Scout (ui_scout.py wrapper for naturo)
   - list_windows(), see(window, depth), find(element, text)
   - bring_to_front(window), screenshot_isolated(window)

3. Vision Engine (vision_engine.py)
   - capture_active_window()
   - Florence-2 for OCR, captioning, object detection
   - analyze_screen(image, task="ocr|caption|detailed_caption")

4. OCR Tools
   - ai_helper.ocr() - Tesseract
   - fast_ocr.py - Tesseract/PaddleOCR/EasyOCR fallback chain

5. Window Z-Order Preservation
   - track_window_order() - Call BEFORE bring_to_front()
   - restore_window_order() - Call AFTER work complete
   - WindowZOrder context manager - Auto restore on exit

BASIC WORKFLOW:
    from ui_scout import track_window_order, restore_window_order, bring_to_front
    track_window_order()
    bring_to_front("Target App")
    # ... automation via Windows-MCP or PyAutoGUI ...
    restore_window_order()

CREATIVE TOOLS:
- Adobe Premiere/After Effects: ExtendScript (JavaScript API) or UI automation
- FL Studio: Python API (flbot) or keyboard macros
- See SCREENSPACE_TOOLKIT.md for detailed recipes

SECURITY: Windows-MCP can execute arbitrary commands. Use in VMs or with caution.
"""

# ============================================================================
# QUICK REFERENCE KEYS
# ============================================================================

QUICK_REFERENCE = """
QUICK COMMANDS:

# Redis Backup
python E:\\AI-Setup\\redis_backup_fast.py
python E:\\AI-Setup\\redis_manager.py --status

# Docker Status
docker ps
wsl -d Ubuntu-24.04 -e docker ps

# GPU Verification
wsl -d Ubuntu-24.04 -e docker run --rm --device=/dev/dxg \\
  -v /usr/lib/wsl/lib:/usr/lib/wsl/lib \\
  -v /opt/rocm-7.2.1:/opt/rocm:ro \\
  -e HSA_ENABLE_DXG_DETECTION=1 \\
  -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib \\
  rocm/dev-ubuntu-24.04:7.1.1-complete \\
  rocminfo

# Web Fetch
python E:\\AI-Setup\\enterprise_web_fetch.py <url> --category <rocm|docker|wsl>

# Port Management
python E:\\AI-Setup\\port_manager.py --status

# Deployment
python E:\\AI-Setup\\deployment_framework.py --status
"""
