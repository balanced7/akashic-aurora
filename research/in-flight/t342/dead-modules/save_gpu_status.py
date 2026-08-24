"""Update knowledge base with GPU discovery findings"""
from knowledge_base import KB

kb = KB()

# Document the GPU issue
kb.write("gpu_discovery_fix", "root_cause", {
    "issue": "GPU discovery timeout in Ollama container",
    "error_log": "failure during GPU discovery - failed to finish discovery before timeout",
    "root_cause": "AMD RX 9070 XT (gfx1201/RDNA4) is too new for ROCm 7.2.1",
    "rocminfo_result": "0 GPU devices found",
    "librocdxg_status": "Working - ROCm libs mount correctly",
    "fallback": "Runs on CPU (30.5GB available)",
    "status": "WORKING but CPU-only for now"
})

kb.write_doc("gpu_status", """
# GPU Discovery Status - 2026-04-13

## Current Status
Ollama is RUNNING but on CPU fallback mode.

## Root Cause
AMD RX 9070 XT (gfx1201/RDN4) is too new for ROCm 7.2.1.
The GPU discovery process times out because ROCm can't detect the GPU.

## Evidence
1. `/opt/rocm/lib/` mounts correctly with all ROCm libraries
2. `clinfo` shows 0 GPU devices
3. Ollama logs: "failure during GPU discovery before timeout"
4. Falls back to CPU: 30.5 GB available

## What's Working
- All Docker containers (Redis, Voice, WebUI)
- Streamlit dashboard at http://127.0.0.1:8501
- Ollama API responding (but CPU mode)
- WSL2 port proxy for Ollama

## Solutions to Try
1. Wait for ROCm 7.3+ with RDNA4 support
2. Try AMD ROCm staging builds
3. Use CPU mode (current - works fine)
4. Try Ollama nightly with better GPU support
""", "gpu_discovery_fix")

print("GPU status updated in knowledge base")
print("Status:", kb.get_status())