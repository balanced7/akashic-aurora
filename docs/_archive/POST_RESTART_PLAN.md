# Post-Restart Plan: Bootstrap with Claude + OpenCode

**Status:** All files in place. Ready for restart.  
**Next Steps:** After restart, execute the plan below.

---

## PHASE 1: Claude Bootstraps System (Me)

### Step 1.1: Verify WSL + Docker

After you restart, I will:

```powershell
# Check WSL status
wsl --list --verbose
# Should show: Ubuntu ... Running ... 2

# Check Docker
docker --version
docker info
# Should both work without errors

# Verify Redis files
dir E:\AI-Setup\dockerized-ai\redis\docker-compose.yml
```

### Step 1.2: Start Redis

```powershell
cd E:\AI-Setup\dockerized-ai\redis
docker-compose -f docker-compose.yml up -d

# Wait 5 seconds
Start-Sleep -Seconds 5

# Verify it's running
docker ps | findstr redis
docker exec -it ai-redis redis-cli ping
# Should output: PONG
```

### Step 1.3: Test Bootstrap API

```powershell
cd E:\AI-Setup
py test_bootstrap_api_no_docs.py
# Should see: 6/6 tests PASS
```

### Step 1.4: Initialize Myself Using Bootstrap API

```python
from agent_init import initialize_and_load_context

result = initialize_and_load_context("claude_bootstrap_test", "system_validation")
api = result["api"]

# Verify I have access to Bootstrap API
info = api.get_bootstrap_info()
context = api.get_context_summary()

print(f"Bootstrap API working: {len(info['signals'])} signals available")
print(f"Context loaded: {context['summary']['recommendation']}")
```

---

## PHASE 2: OpenCode Bootstraps (With Redis)

Once Redis is confirmed running:

### Step 2.1: OpenCode Reads bootstrap.md

OpenCode will:
- Read bootstrap.md
- Find reference to OPENCODE_START_HERE.md
- Read OPENCODE_START_HERE.md (depth-optimized)
- Get initialization code

### Step 2.2: OpenCode Initializes

```python
from agent_init import initialize_and_load_context

result = initialize_and_load_context("opencode_post_restart", "general_agent")
api = result["api"]

# Get bootstrap info
info = api.get_bootstrap_info()
print(f"Signals: {list(info['signals'].keys())}")

# Get context
context = api.get_context_summary()
print(f"Context: {context['summary']['recommendation']}")
```

**Expected:** Initialization should complete in 3-5 seconds (vs 30+ seconds without Redis)

### Step 2.3: OpenCode Runs Bootstrap API Test

```bash
cd E:\AI-Setup
python test_bootstrap_api_no_docs.py
```

**Expected:** 6/6 tests PASS

---

## SUCCESS CRITERIA

### Phase 1 (Me)
- ✅ WSL showing "Running ... 2"
- ✅ Docker info shows no errors
- ✅ Redis container running and responding PONG
- ✅ test_bootstrap_api_no_docs.py shows 6/6 PASS
- ✅ Initialize via Bootstrap API works

### Phase 2 (OpenCode)
- ✅ OpenCode reads bootstrap.md (finds OPENCODE_START_HERE reference)
- ✅ OpenCode reads OPENCODE_START_HERE.md (finds init code)
- ✅ OpenCode runs initialization successfully (3-5 seconds)
- ✅ OpenCode gets Bootstrap API info (signals, methods, examples)
- ✅ OpenCode runs test_bootstrap_api_no_docs.py: 6/6 PASS

### Overall Success
- ✅ Cross-agent compatibility proven (Claude + OpenCode both initialize)
- ✅ Bootstrap API working for any agent
- ✅ Redis working with Docker + WSL
- ✅ No documentation depth issues (API-based discovery)

---

## Fallback Plans

### If Redis Doesn't Start
- Not critical; system has file-based fallback
- Initialization takes ~30 seconds instead of 3-5 seconds
- Tests still pass
- Proceed without Redis

### If Docker Doesn't Work
- Restart Docker Desktop from Start menu
- Wait 60 seconds for full startup
- Then start Redis

### If WSL Still Has Issues
- Run `fix_wsl_docker.ps1` as Administrator
- If that fails, another restart may be needed

---

## Files You'll Need

After restart, these files are your toolkit:

| File | Purpose |
|------|---------|
| `bootstrap.md` | Entry point (read first) |
| `check_docker_wsl.ps1` | Diagnostic (checks status) |
| `fix_wsl_docker.ps1` | Auto-fix (tries to repair) |
| `START_REDIS.md` | Redis startup guide |
| `agent_init.py` | Initialization code |
| `OPENCODE_START_HERE.md` | Quick-start for OpenCode |
| `test_bootstrap_api_no_docs.py` | Validation test (6/6 should pass) |

---

## Exact Commands After Restart

### Commands I'll Run (Claude)

```powershell
# Verify WSL
wsl --list --verbose

# Verify Docker
docker --version

# Start Redis
cd E:\AI-Setup\dockerized-ai\redis
docker-compose -f docker-compose.yml up -d
Start-Sleep -Seconds 5

# Verify Redis
docker exec -it ai-redis redis-cli ping

# Run test
cd E:\AI-Setup
py test_bootstrap_api_no_docs.py
```

### Commands OpenCode Will Execute

```
1. Read: E:\AI-Setup\bootstrap.md
2. Read: E:\AI-Setup\OPENCODE_START_HERE.md
3. Execute: python agent_init.py opencode_post_restart general_agent
4. Run: python test_bootstrap_api_no_docs.py
5. Report: Results of 6 tests
```

---

## Timeline

**After Restart:**
- 5-10 min: WSL + Docker verify
- 2-5 min: Redis startup + test
- 2-3 min: Bootstrap API test run
- 5 min: Claude initialization test
- 5-10 min: OpenCode initialization
- 5 min: OpenCode test run

**Total:** ~25-35 minutes from restart to full validation

---

## What Success Looks Like

### After Phase 1 (Me)
```
WSL Status: Running
Docker: Connected
Redis: PONG
Bootstrap API Test: 6/6 PASS
Initialization: Success in 3-5 seconds
```

### After Phase 2 (OpenCode)
```
Bootstrap read: OPENCODE_START_HERE.md located
Initialization: Success in 3-5 seconds
Bootstrap API Test: 6/6 PASS
Report: All systems operational
```

### Overall Proof
✅ Cross-agent compatibility achieved  
✅ Bootstrap API working elegantly  
✅ No documentation depth issues  
✅ Infrastructure stable (WSL + Docker + Redis)

---

## Ready?

Everything is in place. When you're ready:

1. **Restart your system**
2. **Tell me you're back up**
3. **I'll guide you through Phase 1**
4. **Then we'll have OpenCode do Phase 2**

Let's go! 🚀
