"""Save GPU fix to knowledge base"""
from knowledge_base import KB

kb = KB()

# Register this fix
kb.register_model("gpu_discovery_fix", "GPU discovery and Ollama fix", ["docker", "rocm", "amd-gpu"])

# Save the working config as a learning
working_config = {
    "issue": "Ollama container exits immediately with GPU discovery timeout",
    "root_cause": "ROCm library path issues in WSL2 container",
    "solution": {
        "volumes": [
            "- /opt/rocm-7.2.1:/opt/rocm:ro",
            "- /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro"
        ],
        "environment": [
            "HSA_ENABLE_DXG_DETECTION=1",
            "LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib",
            "ROCM_PATH=/opt/rocm",
            "HIP_VISIBLE_DEVICES=0",
            "HSA_OVERRIDE_GFX_VERSION=12.0.1"
        ],
        "docker_args": [
            "--device=/dev/dxg",
            "--network host",
            "--shm-size=8g",
            "--cap-add=SYS_PTRACE",
            "--ipc=host"
        ]
    },
    "test_command": "wsl -d Ubuntu-24.04 -e curl -s http://localhost:11434/api/tags",
    "port_proxy": "netsh interface portproxy add v4tov4 listenport=11434 connectport=11434 connectaddress=<WSL_IP>",
    "source": "E:\\AI-Setup\\dockerized-ai\\ollama\\docker-compose.wsl2.yml"
}

kb.write("gpu_discovery_fix", "ollama_gpu_fix", working_config)
kb.write_doc("gpu_discovery", """
# GPU Discovery Fix for Ollama

## The Problem
Ollama container exits immediately with:
```
level=WARN source=runner.go:464 msg="failure during GPU discovery" 
error="failed to finish discovery before timeout"
```

## The Solution (Working Config)
Use docker-compose.wsl2.yml which has all the correct ROCm settings:

```yaml
environment:
  - HSA_ENABLE_DXG_DETECTION=1
  - LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib
  - ROCM_PATH=/opt/rocm
  - HIP_VISIBLE_DEVICES=0
  - HSA_OVERRIDE_GFX_VERSION=12.0.1

volumes:
  - /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro
  - /opt/rocm-7.2.1:/opt/rocm:ro

devices:
  - /dev/dxg:/dev/dxg

shm_size: 8g
cap_add:
  - SYS_PTRACE
ipc: host
```

## Key Files
- Working compose: `E:\\AI-Setup\\dockerized-ai\\ollama\\docker-compose.wsl2.yml`
- Launcher: `E:\\AI-Setup\\launch_dashboard.py`
- GPU passthrough: `E:\\AI-Setup\\docker-gpu-passthrough.md`
""", "gpu_discovery_fix")

print("GPU fix saved to knowledge base")
print("Models:", kb.get_all_models())