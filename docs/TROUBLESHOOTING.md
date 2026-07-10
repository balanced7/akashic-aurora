# Troubleshooting Guide

Status: current  (2026-07-09, P4: Living ops)

## Quick Diagnostics

Run this first:
```bash
python E:\AI-Setup\init_ai.py
```

Or system diagnostic:
```bash
python E:\AI-Setup\system_diagnostic.py
```

## Common Issues

### 1. Dashboard won't start

**Symptoms**: React dashboard won't launch

**Fix**:
```bash
cd E:\AI-Setup\dockerized-ai\services\dashboard-react
npm install  # If dependencies missing
npm run dev
```

**[DEPRECATED] Streamlit Dashboard** (port 8501):
```bash
streamlit run E:\AI-Setup\dockerized-ai\services\dashboard\app.py --server.port 8501 --server.address 127.0.0.1
```
Use React dashboard on port 3001 instead.

### 2. Redis not accessible

**Symptoms**: "Connection refused" on port 6379

**Fix**:
```bash
# Check Docker
docker ps

# Start Redis
docker start ai-redis

# Or create if missing
docker run -d --name ai-redis -p 6379:6379 redis:7-alpine
```

### 3. Ollama not responding

**Symptoms**: Connection timeout on port 11434

**Fix**:
```bash
# Check in WSL2
wsl -d Ubuntu-24.04 -e docker ps

# Restart Ollama
wsl -d Ubuntu-24.04 -e docker start ollama-rocm

# If exited, restart
wsl -d Ubuntu-24.04 -e bash -c 'docker rm -f ollama-rocm; docker run -d --device=/dev/dxg -e OLLAMA_HOST=0.0.0.0 -e HSA_ENABLE_DXG_DETECTION=1 -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib -e ROCM_PATH=/opt/rocm -e HIP_VISIBLE_DEVICES=0 -e HSA_OVERRIDE_GFX_VERSION=12.0.1 -v /opt/rocm-7.2.1:/opt/rocm:ro -v /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro --network host --shm-size=8g --cap-add=SYS_PTRACE --ipc=host --name ollama-rocm ollama/ollama:rocm'

# Fix port proxy (if WSL IP changed)
wsl -d Ubuntu-24.04 -e hostname -I  # Get IP
# Then update port proxy:
netsh interface portproxy delete v4tov4 listenport=11434
netsh interface portproxy add v4tov4 listenport=11434 connectport=11434 connectaddress=<NEW_IP>
```

### 4. GPU not detected

**Symptoms**: Ollama runs on CPU, "GPU discovery timeout"

**Fix**:
This is a known issue - AMD RX 9070 XT (gfx1201) is too new for ROCm 7.2.1
- Ollama works but on CPU only
- Wait for ROCm 7.3+ or use CPU mode

### 5. WSL2 Docker not accessible

**Symptoms**: "docker: command not found" in WSL2

**Fix**:
```bash
# Install Docker in WSL2
wsl -d Ubuntu-24.04 -e sudo apt update
wsl -d Ubuntu-24.04 -e sudo apt install docker.io
wsl -d Ubuntu-24.04 -e sudo service docker start
```

### 6. Knowledge Base issues

**Symptoms**: "Redis not available"

**Fix**:
```bash
# Check Redis
docker ps | grep redis

# Restart
docker restart ai-redis

# Test
docker exec ai-redis redis-cli ping
```

## Check Commands

```bash
# All services
python E:\AI-Setup\system_diagnostic.py

# Windows
powershell -Command "Get-Process | Where-Object MainWindowTitle"

# Docker
docker ps

# WSL2 containers
wsl -d Ubuntu-24.04 -e docker ps

# Ollama
curl http://127.0.0.1:11434/api/tags

# Port proxy
netsh interface portproxy show all
```

---

## Updated: 2026-04-13