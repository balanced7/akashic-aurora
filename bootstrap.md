# bootstrap.md - BreakThrough Stack Bootstrap
> **CRITICAL**: Run this at the START of EVERY session before doing anything else.
> This starts Redis HA (with Sentinel failover), sync service, and MCP server.

**Version**: 6.0  
**Updated**: 2026-04-15  

---

## 🚀 COMPLETE BOOTSTRAP SEQUENCE

Copy and paste this entire section into PowerShell:

```powershell
# ============================================================
# BREAKTHROUGH STACK - COMPLETE BOOTSTRAP
# Run this FIRST at the start of every session
# ============================================================

Write-Host "=== BreakThrough Stack Bootstrap ===" -ForegroundColor Cyan

# --- STEP 1: CLEANUP OLD CONTAINERS ---
Write-Host "[1/6] Cleaning up old containers..." -ForegroundColor Yellow
cd E:\AI-Setup\dockerized-ai\redis

# Stop and remove any existing Redis HA containers
docker compose -f docker-compose-ha.yml down 2>$null

# Also cleanup any legacy containers
docker stop redis-master redis-replica1 redis-replica2 sentinel1 sentinel2 sentinel3 2>$null
docker rm redis-master redis-replica1 redis-replica2 sentinel1 sentinel2 sentinel3 2>$null

# --- STEP 2: START REDIS HA CLUSTER ---
Write-Host "[2/6] Starting Redis HA Cluster..." -ForegroundColor Yellow
docker compose -f docker-compose-ha.yml up -d

# Wait for containers to start
Start-Sleep -Seconds 10

# --- STEP 3: VERIFY ALL 6 CONTAINERS ARE RUNNING ---
Write-Host "[3/6] Verifying Redis HA containers..." -ForegroundColor Yellow
$containers = @("redis-master", "redis-replica1", "redis-replica2", "sentinel1", "sentinel2", "sentinel3")
$allRunning = $true

foreach ($c in $containers) {
    $status = docker ps --filter "name=$c" --format "{{.Status}}"
    if ($status -like "Up*") {
        Write-Host "  [OK] $c is running" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $c NOT running!" -ForegroundColor Red
        $allRunning = $false
    }
}

# --- STEP 4: VERIFY REDIS IS WORKING ---
Write-Host "[4/6] Verifying Redis functionality..." -ForegroundColor Yellow
$pong = docker exec redis-master redis-cli PING
if ($pong -eq "PONG") {
    Write-Host "  [OK] Redis master responding" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Redis master not responding!" -ForegroundColor Red
}

# Check replication
$replInfo = docker exec redis-master redis-cli INFO replication | Select-String "connected_slaves"
Write-Host "  Replication: $replInfo" -ForegroundColor Cyan

# --- STEP 5: START REDIS SYNC SERVICE ---
Write-Host "[5/6] Starting Redis Sync Service..." -ForegroundColor Yellow
cd E:\AI-Setup

# Kill any existing sync process
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*redis_sync*" } | Stop-Process -Force 2>$null

# Start sync in background
$syncJob = Start-Job -ScriptBlock {
    cd E:\AI-Setup
    python redis_sync.py --daemon
}
Start-Sleep -Seconds 3

# Verify sync started
$syncStatus = python redis_sync.py --status 2>&1 | Select-String "Running"
if ($syncStatus -like "*True*") {
    Write-Host "  [OK] Redis Sync Service running" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Redis Sync may not be running, check manually" -ForegroundColor Yellow
}

# --- STEP 6: VERIFY MCP SERVER CAN LOAD ---
Write-Host "[6/6] Verifying MCP Server..." -ForegroundColor Yellow
$mcpTest = python -c "import sys; sys.path.insert(0, r'E:\AI-Setup'); from ai_setup_mcp import get_session_info; print(get_session_info())" 2>&1
if ($mcpTest -like '*"session_id"*') {
    Write-Host "  [OK] MCP Server ready" -ForegroundColor Green
} else {
    Write-Host "  [WARN] MCP Server may need manual start" -ForegroundColor Yellow
    Write-Host "  Run: python E:\AI-Setup\ai_setup_mcp.py" -ForegroundColor Yellow
}

# --- FINAL SUMMARY ---
Write-Host ""
Write-Host "=== Bootstrap Complete ===" -ForegroundColor Cyan
Write-Host "Redis HA: 1 Master + 2 Replicas + 3 Sentinels" -ForegroundColor White
Write-Host "Sync: Every 5 seconds" -ForegroundColor White
Write-Host "MCP: Run 'python E:\AI-Setup\ai_setup_mcp.py' to start" -ForegroundColor White
Write-Host ""
```

---

## 📋 MANUAL STEP-BY-STEP (If script fails)

If the script above doesn't work, run these manually:

### Step 1: Stop old containers
```powershell
cd E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml down
```

### Step 2: Start Redis HA
```powershell
docker compose -f docker-compose-ha.yml up -d
```

### Step 3: Wait and verify all 6 containers
```powershell
# All 6 should show "Up"
docker ps --format "{{.Names}}: {{.Status}}"
```

Expected output:
```
sentinel3: Up
sentinel1: Up
sentinel2: Up
redis-replica2: Up
redis-replica1: Up
redis-master: Up
```

### Step 4: Test Redis
```powershell
docker exec redis-master redis-cli PING
# Should return: PONG

docker exec redis-master redis-cli INFO replication | Select-String "connected_slaves"
# Should show: connected_slaves:2
```

### Step 5: Start Redis Sync
```powershell
cd E:\AI-Setup
python redis_sync.py --daemon
```

### Step 6: Verify sync is running
```powershell
python redis_sync.py --status
```

---

## 🔧 QUICK REFERENCE

### What gets started

| Component | Containers | Purpose |
|-----------|------------|---------|
| Redis Master | redis-master | Primary Redis - all writes |
| Redis Replica 1 | redis-replica1 | Read replica #1 |
| Redis Replica 2 | redis-replica2 | Read replica #2 |
| Sentinel 1 | sentinel1 | Monitors master, triggers failover |
| Sentinel 2 | sentinel2 | Monitors master, triggers failover |
| Sentinel 3 | sentinel3 | Monitors master, triggers failover |
| Redis Sync | Background process | Syncs logs to Redis |
| MCP Server | Background process | Exposes context via MCP |

### Ports

| Service | Port | Description |
|---------|------|-------------|
| Redis Master | 6379 | Primary Redis |
| Redis Replica 1 | 6380 | Read replica |
| Redis Replica 2 | 6381 | Read replica |
| Sentinel 1 | 26379 | Failover monitor |
| Sentinel 2 | 26380 | Failover monitor |
| Sentinel 3 | 26381 | Failover monitor |
| MCP Server (HTTP) | 8080 | MCP protocol (optional) |

### Key Files

| File | Purpose |
|------|---------|
| `dockerized-ai/redis/docker-compose-ha.yml` | Redis HA cluster config |
| `dockerized-ai/redis/sentinel1.conf` | Sentinel 1 config |
| `dockerized-ai/redis/sentinel2.conf` | Sentinel 2 config |
| `dockerized-ai/redis/sentinel3.conf` | Sentinel 3 config |
| `redis_sync.py` | Sync service |
| `ai_setup_mcp.py` | MCP server |

### Start MCP Server (when needed)
```powershell
# Stdio transport (for OpenCode)
python E:\AI-Setup\ai_setup_mcp.py

# HTTP transport (for Claude Desktop)
python E:\AI-Setup\ai_setup_mcp.py --http --port 8080
```

---

## ❌ IF SOMETHING GOES WRONG

### Redis containers won't start
```powershell
cd E:\AI-Setup\dockerized-ai\redis
docker compose down
docker system prune -f
docker compose up -d
```

### Sentinel keeps restarting
```powershell
# Check sentinel logs
docker logs sentinel1
docker logs sentinel2
docker logs sentinel3

# Common fix: restart all
docker restart sentinel1 sentinel2 sentinel3
```

### Redis master not found by sentinel
```powershell
# Get Redis master IP
docker inspect redis-master --format "{{.NetworkSettings.Networks.redis_redis-ha.IPAddress}}"

# Update sentinel configs with correct IP
# Edit: sentinel1.conf, sentinel2.conf, sentinel3.conf
# Change: sentinel monitor breakthrough <IP> 6379 2
```

### Redis sync not working
```powershell
# Check if Python can connect
python -c "import redis; r=redis.Redis(host='localhost', port=6379); print(r.ping())"

# Restart sync
Get-Process python | Where-Object { $_.CommandLine -like "*redis_sync*" } | Stop-Process -Force
python E:\AI-Setup\redis_sync.py --daemon
```

---

**Last Updated**: 2026-04-15
