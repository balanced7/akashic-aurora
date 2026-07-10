# GPU Setup & Issues

Status: current  (2026-07-09, P4: Living ops; hardware status)

## Current Status (2026-04-13)

### GPU: AMD RX 9070 XT (16GB VRAM)
- **Architecture**: RDNA4 (gfx1201)
- **ROCm Version**: 7.2.1
- **Status**: WORKING (CPU fallback mode)

## The Issue

Ollama container shows:
```
level=WARN source=runner.go:464 msg="failure during GPU discovery" 
error="failed to finish discovery before timeout"
```

**Root Cause**: AMD RX 9070 XT is too new for ROCm 7.2.1

## Working Config

Use this docker-compose.wsl2.yml:

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

## Starting Ollama

```bash
# In WSL2:
wsl -d Ubuntu-24.04 -e docker run -d \
  --device=/dev/dxg \
  -e HSA_ENABLE_DXG_DETECTION=1 \
  -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib \
  -e ROCM_PATH=/opt/rocm \
  -e HIP_VISIBLE_DEVICES=0 \
  -e HSA_OVERRIDE_GFX_VERSION=12.0.1 \
  -v /opt/rocm-7.2.1:/opt/rocm:ro \
  -v /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro \
  --network host \
  --shm-size=8g \
  --cap-add=SYS_PTRACE \
  --ipc=host \
  --name ollama-rocm \
  ollama/ollama:rocm

# Setup port proxy (for Windows access):
wsl -d Ubuntu-24.04 -e hostname -I  # Get WSL IP
netsh interface portproxy add v4tov4 listenport=11434 connectport=11434 connectaddress=<WSL_IP>
```

## Verification

```bash
# Check from WSL2:
curl http://localhost:11434/api/tags

# Check from Windows:
curl http://127.0.0.1:11434/api/tags

# Check ROCm:
wsl -d Ubuntu-24.04 -e rocminfo
```

## Future Solutions

1. Wait for ROCm 7.3+ with RDNA4 support
2. Try AMD ROCm staging builds
3. Use CPU mode (current - works fine for small models)

---

## Updated: 2026-04-13