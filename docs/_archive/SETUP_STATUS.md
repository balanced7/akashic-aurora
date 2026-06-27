# AI Infrastructure Setup - Status Report

> **⚠️ HISTORICAL DOCUMENT**: This file reflects status at a point in time. For current status, see `ARCHITECTURE.md` and `bootstrap.md`.

## System Hardware
- **GPU**: AMD RX 9070 XT (16GB VRAM) - RDNA4 (gfx1201)
- **RAM**: 32GB DDR5
- **OS**: Windows 11 with WSL2 (Ubuntu-24.04)

## Project Location
All files are in: `E:\AI-Setup\`

## Accomplished So Far

### 1. GPU Passthrough - FIXED!
**Solution Found**: Run Docker from WSL2 (Ubuntu-24.04), NOT Windows Docker Desktop!

Key findings:
- Windows Docker Desktop uses 9p/drvfs mounts which show empty directories in containers
- WSL2 Docker correctly passes through ROCm libraries from `/opt/rocm-7.2.1`
- Use `ollama/ollama:rocm` image (not `latest`) for AMD GPU support

### 2. Ollama Setup - WORKING
- Ollama is running with GPU acceleration via WSL2 Docker
- Image: `ollama/ollama:rocm`
- GPU detected: AMD RX 9070 XT (gfx1201)
- Model loaded: `gpt-oss:20b` (tested successfully)

### 3. Dockerized AI Services (PARTIAL)
Project at `E:\AI-Setup\dockerized-ai\`:
- `docker-compose.yml` - Main orchestration (7 services)
- Services: orchestrator, whisper, llm-router, helper-ai, output-parser, tts, dashboard
- Streamlit dashboard at port 8501

### 4. Model Recommendations (DONE)
Document at `E:\AI-Setup\model-recommendations.md`

---

## Latest Updates (2026-04-12)

### Dashboard Overhaul
- **Multithreading**: Parallel service loading via `concurrent.futures.ThreadPoolExecutor` (8 workers)
- **Single-page UI**: All options consolidated with gear icon for settings
- **Tabs**: Dashboard, Chat, Experts, Services, Models
- **OpenRouter integration**: Cloud AI fallback with free models
- **Smart orchestrator**: Auto-selects models based on task type, recommends downloads

### OpenRouter Integration
- Added `OpenRouterClient` class with free models:
  - `openrouter/free` (auto-router)
  - `openai/gpt-4o-mini`, `anthropic/claude-3-haiku`
  - `meta-llama/llama-3.2-90b`, `google/gemini-2.0-flash-exp`
  - `deepseek/deepseek-chat`, `mistralai/mistral-7b`
- Toggle to switch between local Ollama and cloud

### Smart Orchestrator
- `ModelOrchestrator` class with:
  - Task type detection (coding, math, knowledge, creative)
  - Model selection based on task
  - Auto-recommend model downloads if missing

### AI Dashboard Launcher (EXE)
- Created `launch_dashboard.py` and built `AI Dashboard.exe`
- Auto-starts: Docker Desktop → Redis → Ollama → Streamlit
- Added fallback to create Redis container if not exists

### Screen Monitor
- Created `screen_monitor.py` for diagnostics
- Lists open windows, checks Docker/Ollama status
- Captures screenshot to desktop

---

## Troubleshooting Log

| Date | Issue | Solution |
|------|-------|----------|
| 2026-04-12 | localhost refused connection | Changed to 127.0.0.1 |
| 2026-04-12 | `Popen.__init__()` error | Removed `creation=` parameter |
| 2026-04-12 | Docker not running | Added auto-start Docker Desktop |
| 2026-04-12 | Redis container missing | Added auto-create if not exists |
| 2026-04-12 | Ollama port not mapped | Added `netsh portproxy` for WSL2 |
| 2026-04-13 | Ollama container exits immediately | Changed to `--network host` mode |
| 2026-04-13 | WSL2 IP changes on restart | Added dynamic IP detection for portproxy |
| 2026-04-13 | PowerShell `$_` not working | Use full variable names in commands |

---

## Knowledge Base System

### Purpose
All AI models use Redis-based knowledge base for sharing learnings.

### Usage
```python
from knowledge_base import KB
kb = KB()
kb.write("model_name", "key", "value")  # Write learning
kb.read("key")                          # Read learning
kb.get_all_models()                     # List models
```

### Documentation Standards
1. Register your model on startup
2. Use prefix: `model_name:key` for all keys
3. Never overwrite another model's learning
4. Document in `kb:docs` for shared docs

### Files
- `E:\AI-Setup\knowledge_base.py` - Knowledge base library
- `E:\AI-Setup\save_diagnostic.py` - Save diagnostic status
- Redis keys use prefixes: `kb:models`, `kb:learning:`, `kb:docs:`

---

## Port Mappings
- 6379 → Redis (Docker)
- 11434 → Ollama (WSL2 via portproxy)
- 8501 → Streamlit Dashboard

---

## The Solution (GPU Passthrough)

### How to Run Ollama with GPU Acceleration

**From WSL2 (Ubuntu-24.04), NOT from Windows PowerShell:**

```bash
# 1. Ensure you're in WSL2
wsl -d Ubuntu-24.04

# 2. Run Ollama with GPU support
docker run -d \
  --device=/dev/dxg \
  -e HSA_ENABLE_DXG_DETECTION=1 \
  -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib \
  -e ROCM_PATH=/opt/rocm \
  -e HIP_VISIBLE_DEVICES=0 \
  -e HSA_OVERRIDE_GFX_VERSION=12.0.1 \
  -v /opt/rocm-7.2.1:/opt/rocm:ro \
  -v /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro \
  -p 11434:11434 \
  --name ollama-gpu \
  ollama/ollama:rocm
```

### Or use the docker-compose:
```bash
cd E:\AI-Setup\dockerized-ai\ollama
docker compose -f docker-compose.wsl2.yml up -d
```

---

## Running Services

### Currently Running (via WSL2 Docker):
- **Ollama**: Port 11434 (GPU accelerated, AMD RX 9070 XT)
- **Redis**: Port 6379 (agent memory)

### Running (via Windows Docker Desktop):
- **Open WebUI**: Port 3000
- **Voice AI**: Port 5000-5001

---

## Next Steps

1. **Use WSL2 Docker for Ollama** - The Windows Docker Desktop approach doesn't work with ROCm
2. **Test GPU inference** - Already confirmed working
3. **Build other AI services** - Can use docker-compose from WSL2
4. **Access Ollama from Windows apps** - Works via localhost:11434
5. **Add OpenRouter API key** - Get from openrouter.ai for cloud AI fallback

---

## Files Reference

| File | Purpose |
|------|---------|
| `E:\AI-Setup\dockerized-ai\ollama\docker-compose.wsl2.yml` | WSL2-based Ollama with GPU |
| `E:\AI-Setup\dockerized-ai\docker-compose.yml` | Main AI services |
| `E:\AI-Setup\model-recommendations.md` | Model recommendations |
| `E:\AI-Setup\docker-gpu-passthrough.md` | GPU passthrough docs |
| `services/dashboard/app.py` | Updated dashboard with multithreading |

---

## Redis Sync (For Multiple opencode Instances)

Redis is running at `localhost:6379` (container: `ai-redis`)

**Key learnings stored:**
- `learnings:gpu_passthrough` - GPU passthrough fix
- `learnings:ollama_gpu` - ROCm mount issue details

---

## Agent Memory System

Using `E:\AI-Setup\dockerized-ai\redis\agent_memory.py`:
```python
from agent_memory import AgentMemory
mem = AgentMemory()
mem.save_interaction("question", "answer")
mem.add_fact("key", "value", tags=["tag"])
```

---

## Journey Log (Challenges & Solutions)

Our complete journey is stored in Redis at `knowledge:facts`:

| Phase | Title | Challenge |
|-------|-------|-----------|
| 1 | GPU Passthrough Setup | WSL2 doesn't expose AMD GPU to Docker |
| 2 | Docker CLI Not in PATH | Docker not accessible from PowerShell |
| 3 | Ollama GPU Detection | Ollama shows CPU only in container |
| 4 | Redis Sync System | Multiple instances need to share learnings |
| 5 | Agent Onboarding System | New agents need system context |

**View journey in Redis:**
```bash
docker exec ai-redis redis-cli HGETALL knowledge:facts | grep journey
```

**View learnings:**
```bash
docker exec ai-redis redis-cli LRANGE learnings:journey 0 10
```
```