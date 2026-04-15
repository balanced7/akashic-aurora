# bootstrap.md - BreakThrough Stack Bootstrap
> **IMPORTANT**: This file must be read and executed at the START of every session.

**Version**: 5.0  
**Updated**: 2026-04-15  

---

## 🚀 FIRST STEPS (Do These Immediately)

When starting a new session, run these commands in order:

### Step 1: Start Redis HA Cluster

```powershell
cd E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml up -d
```

Verify Redis is running:
```powershell
docker exec redis-master redis-cli PING
# Should return: PONG
```

### Step 2: Start Redis Sync Service (Background)

```powershell
python E:\AI-Setup\redis_sync.py --daemon
```

Verify sync is working:
```powershell
python E:\AI-Setup\redis_sync.py --status
# Should show: Running: True, Redis Available: True
```

### Step 3: Start MCP Server

For OpenCode (stdio transport):
```powershell
python E:\AI-Setup\ai_setup_mcp.py
```

For Claude Desktop (HTTP transport):
```powershell
python E:\AI-Setup\ai_setup_mcp.py --http --port 8080
```

---

## ✅ VERIFICATION CHECKLIST

After starting, verify all services are working:

| Service | Verify Command | Expected |
|---------|---------------|----------|
| Redis Master | `docker exec redis-master redis-cli PING` | `PONG` |
| Redis Replica | `docker exec redis-replica1 redis-cli PING` | `PONG` |
| Redis Sync | `python E:\AI-Setup\redis_sync.py --status` | `Running: True` |
| MCP Server | `python -c "from ai_setup_mcp import get_session_info; print(get_session_info())"` | JSON with session info |

---

## 📋 COMPLETE BOOTSTRAP SCRIPT

Run this entire bootstrap sequence:

```powershell
# 1. Start Redis HA
cd E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml up -d
Start-Sleep -Seconds 5

# 2. Verify Redis
docker exec redis-master redis-cli PING

# 3. Start Redis Sync (background)
Start-Job -ScriptBlock { 
    cd E:\AI-Setup
    python redis_sync.py --daemon
}

# 4. Start MCP Server (background)
Start-Job -ScriptBlock { 
    cd E:\AI-Setup
    python ai_setup_mcp.py
}

# 5. Verify services
python E:\AI-Setup\redis_sync.py --status
python -c "from ai_setup_mcp import get_session_info; print(get_session_info())"
```

---

## 🔧 TROUBLESHOOTING

### Redis won't start
```powershell
cd E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml down
docker compose -f docker-compose-ha.yml up -d
```

### Redis sync not running
```powershell
# Kill existing sync
Get-Process python | Where-Object { $_.CommandLine -like "*redis_sync*" } | Stop-Process -Force

# Restart sync
python E:\AI-Setup\redis_sync.py --daemon
```

### MCP server won't start
```powershell
# Check if MCP is installed
pip show mcp

# If not, install
pip install "mcp[cli]"
```

---

## 📁 KEY FILES

| File | Purpose |
|------|---------|
| `ai_setup_mcp.py` | MCP server - exposes session context via MCP protocol |
| `redis_sync.py` | Syncs session logs to Redis for persistence |
| `dockerized-ai/redis/docker-compose-ha.yml` | Redis HA cluster configuration |
| `STARTUP.md` | Full startup documentation |

---

**Last Updated**: 2026-04-15
