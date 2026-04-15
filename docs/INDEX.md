# AI Control Center - File Structure

## Quick Start (For AI Models)

**FIRST - Run bootstrap initialization:**
```bash
python E:\AI-Setup\init_ai.py
```

This will auto-activate logging and show system status.

---

## Directory Structure

```
E:\AI-Setup\
├── init_ai.py                    # [MUST RUN] Context loader for AI models
├── bootstrap.md                  # [MUST READ] Quick start for AI models
├── knowledge_base.py            # Redis KB library (import this)
├── SETUP_STATUS.md              # Main documentation (historical)
│
├── docs\                        # [CENTRALIZED DOCS]
│   ├── INDEX.md                 # This file - quick reference
│   ├── README.md                # KB system overview
│   ├── GPU.md                   # GPU setup & issues
│   ├── SERVICES.md              # Service configurations
│   ├── TROUBLESHOOTING.md       # Common issues & fixes
│   └── MODELS.md                # AI models info
│
├── launch_dashboard.py          # Dashboard launcher script
├── system_diagnostic.py          # Window/service diagnostic
├── check_kb.py                  # Check KB contents
│
├── save_*.py                    # Various save scripts
│   ├── save_diagnostic.py
│   ├── save_gpu_fix.py
│   ├── save_gpu_status.py
│
├── dockerized-ai\              # Docker services
│   ├── docker-compose.yml
│   ├── services\
│   │   ├── dashboard\          # [DEPRECATED] Streamlit dashboard
│   │   ├── dashboard-react\    # [CURRENT] React + Vite + FastAPI
│   │   ├── yolo\              # YOLO vision service
│   │   ├── whisper\            # Speech-to-text
│   │   └── ... (other services)
│   └── ollama\
│       └── docker-compose.wsl2.yml  # Working Ollama config
│
└── dist\                        # Built executables
    └── AI Dashboard.exe
```

---

## Key Files for AI Models

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `init_ai.py` | Initialize & load all context |
| 2 | `knowledge_base.py` | Read/write Redis learnings |
| 3 | `docs\INDEX.md` | Quick reference |
| 4 | `docs\GPU.md` | GPU troubleshooting |
| 5 | `docs\TROUBLESHOOTING.md` | Common issues |

---

## Usage

### For AI Models - Get Context
```python
from init_ai import initialize
context = initialize()
# Returns dict with KB status, system state, learnings, docs
```

### For Humans - Launch Dashboard
```
Double-click: C:\Users\L5\Desktop\AI_Dashboard.exe
```

### Manual Dashboard (CURRENT - React)
```bash
cd E:\AI-Setup\dockerized-ai\services\dashboard-react
npm run dev
# Opens at http://localhost:3001
```

**[DEPRECATED] Streamlit Dashboard** (port 8501)
```bash
streamlit run E:\AI-Setup\dockerized-ai\services\dashboard\app.py
```
Use `dashboard-react` instead.

---

## Updated: 2026-04-13