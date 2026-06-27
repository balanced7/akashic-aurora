# Starting Redis for OpenCode Bootstrap Test

**Goal:** Get Redis running so OpenCode can initialize quickly instead of timing out on connection.

---

## Option 1: Using Docker (Recommended)

### Prerequisites
- Docker Desktop installed and running
- WSL2 enabled

### Steps

```powershell
# Navigate to redis directory
cd E:\AI-Setup\dockerized-ai\redis

# Start Redis container
docker-compose -f docker-compose.yml up -d

# Wait a few seconds
Start-Sleep -Seconds 5

# Verify it's running
docker ps | findstr redis

# Test connection
docker exec -it ai-redis redis-cli ping
# Should output: PONG
```

### Verify Working

```powershell
# Check status
docker-compose logs redis

# Should show: ready to accept connections
```

### Stop Redis (when done)
```powershell
docker-compose down
```

---

## Option 2: Using Simple Redis (Windows Binary)

If Docker isn't working, try:

```powershell
# Check if Redis is installed
redis-server --version

# If not installed, download from https://github.com/microsoftarchive/redis/releases
# Or use Chocolatey: choco install redis
```

---

## Option 3: Skip Redis (Use File Fallback)

Redis is optional. The system works with file-based storage, just slower:

```powershell
# No setup needed, just run:
cd E:\AI-Setup
py test_bootstrap_api_no_docs.py

# Initialization will take ~30 seconds instead of ~3 seconds
# But it will work
```

---

## Troubleshooting

### "Docker Desktop is unable to start"

**Problem:** Docker daemon isn't responding  
**Solution:** 
```powershell
# Restart Docker
Get-Process "Docker Desktop" | Stop-Process -Force
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# Wait 30-60 seconds for startup
```

### "WSL service cannot be started"

**Problem:** WSL not fully activated  
**Solution:**
```powershell
# Option 1: Restart system
Restart-Computer

# Option 2: Try to start service
Start-Service LxssManager
```

### "Cannot connect to server"

**Problem:** Redis container didn't start  
**Solution:**
```powershell
# Check logs
docker-compose logs redis

# Rebuild
docker-compose down
docker-compose up -d

# Check port
netstat -an | findstr :6379
```

---

## For OpenCode to Test

Once Redis is running:

```bash
cd E:\AI-Setup
python test_bootstrap_api_no_docs.py
```

Should see:
```
Result: 6/6 tests passed
VERDICT: [OK] BOOTSTRAP API FULLY FUNCTIONAL
```

---

## What Redis Does

- **Caches decisions** between agent runs (faster startup)
- **Persists learnings** for next agents
- **Stores session logs** (optional, file fallback works)

Without Redis, the system still works but uses slower file-based storage. Initialization takes ~30 seconds instead of ~3 seconds.

---

## Quick Start Script

Create `E:\AI-Setup\start-redis-simple.ps1`:

```powershell
Write-Host "Starting Redis..." -ForegroundColor Green

cd E:\AI-Setup\dockerized-ai\redis

Write-Host "Running docker-compose..." -ForegroundColor Cyan
docker-compose -f docker-compose.yml up -d

Write-Host "Waiting for startup..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "Testing connection..." -ForegroundColor Cyan
$result = docker exec -it ai-redis redis-cli ping 2>&1
if ($result -like "*PONG*") {
    Write-Host "✓ Redis is running and responding" -ForegroundColor Green
    Write-Host "`nRedis ready on localhost:6379" -ForegroundColor Green
} else {
    Write-Host "✗ Redis not responding" -ForegroundColor Red
    Write-Host "Run: docker-compose logs redis" -ForegroundColor Yellow
}
```

Then run: `& E:\AI-Setup\start-redis-simple.ps1`

---

## Next Steps

After Redis is running:

1. Have OpenCode run the Bootstrap API test:
   ```bash
   python test_bootstrap_api_no_docs.py
   ```

2. Should see 6/6 tests passing

3. Then OpenCode can work with full initialization and context loading

---

**Status:** Ready to launch Redis via Docker or fallback to file storage
