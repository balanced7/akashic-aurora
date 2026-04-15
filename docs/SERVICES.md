# Service Configurations

## Active Services

### Service Ports

| Service | Port | URL | Docker Container |
|---------|------|-----|------------------|
| Dashboard (React) | 3001 | http://127.0.0.1:3001 | - |
| Ollama | 11434 | http://127.0.0.1:11434 | ollama-rocm (WSL2) |
| Redis | 6379 | 127.0.0.1:6379 | ai-redis |
| YOLO Vision | 8001 | http://127.0.0.1:8001 | ai-yolo |
| WebUI | 3000 | http://127.0.0.1:3000 | ai-open-webui |
| Voice AI | 5000-5001 | - | ai-voice |

### Docker Containers

```bash
docker ps
# ai-redis        Up
# ai-voice        Up (healthy)
# ai-open-webui   Up (healthy)
# ai-yolo         Up (if running)
```

### WSL2 Docker

```bash
wsl -d Ubuntu-24.04 -e docker ps
# ollama-rocm     Up
```

### Port Proxy for WSL2

Ollama runs in WSL2 but needs port proxy for Windows access:

```bash
# Get WSL IP
wsl -d Ubuntu-24.04 -e hostname -I

# Set port proxy (replace with actual IP)
netsh interface portproxy add v4tov4 listenport=11434 connectport=11434 connectaddress=<WSL_IP>

# Check
netsh interface portproxy show all
```

### Startup Order

1. Docker Desktop (Windows) - REQUIRED for Redis, Voice, WebUI
2. Redis (port 6379)
3. Ollama in WSL2 (port 11434)
4. React Dashboard (port 3001)

### Dashboard Launcher

```bash
cd E:\AI-Setup\dockerized-ai\services\dashboard-react
npm run dev
# Opens at http://localhost:3001
```

### Health Checks

```bash
# Dashboard
curl http://127.0.0.1:3001/

# Ollama
curl http://127.0.0.1:11434/api/tags

# YOLO Vision
curl http://127.0.0.1:8001/

# Redis
docker exec ai-redis redis-cli ping

# WebUI
curl http://127.0.0.1:3000/
```

---

## Legacy Services

> Deprecated services - kept for reference. Use active services above.

| Service | Port | Deprecated | Replaced By | KB Reference |
|---------|------|------------|-------------|--------------|
| Dashboard (Streamlit) | 8501 | 2026-04-13 | Dashboard (React) on port 3001 | `kb.read('streamlit_deprecated_20260413')` |

### Legacy Dashboard (Streamlit) - DO NOT USE

```bash
# This is deprecated - use React dashboard on port 3001 instead
streamlit run E:\AI-Setup\dockerized-ai\services\dashboard\app.py --server.port 8501
```

Location: `services/dashboard/` (deprecated)

---

## Updated: 2026-04-13
