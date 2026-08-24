"""Save the keepalive status to KB"""
from knowledge_base import KB

kb = KB()

kb.register_model("keepalive_system", "Ollama keep-alive system", ["keepalive", "monitoring"])
kb.write("keepalive_system", "current_status", {
    "status": "active",
    "interval_seconds": 30,
    "issue": "Ollama container exits due to GPU discovery timeout",
    "root_cause": "AMD RX 9070 XT (gfx1201) too new for ROCm 7.2.1",
    "solution": "Keep-alive pings every 30s to restart if exited",
    "files": [
        "E:\\AI-Setup\\keepalive_ollama.py",
        "E:\\AI-Setup\\launch_dashboard.py (updated with keepalive)"
    ]
})

kb.write_doc("keepalive", """
# Ollama Keep-Alive System

## Problem
Ollama container exits because GPU discovery times out.

## Solution
keepalive_ollama.py pings Ollama every 30 seconds.
If not responding, it restarts the container.

## Files
- `E:\\AI-Setup\\keepalive_ollama.py` - Main script
- `E:\\AI-Setup\\launch_dashboard.py` - Updated to start keepalive

## Usage
```bash
# Manual start:
python E:\\AI-Setup\\keepalive_ollama.py

# Or run in background:
python E:\\AI-Setup\\keepalive_ollama.py --background
```

## Status
Keep-alive is running but still experimental.
Root cause needs ROCm update for GPU support.
""", "keepalive_system")

print("Keep-alive status saved to KB")
print("Models:", kb.get_all_models())