# Docker GPU Passthrough for AMD RX 9070 XT (gfx1201) in WSL2
# ============================================================
# UPDATED: 2026-04-14 - CONFIRMED WORKING with rocminfo

## Working Configuration

The key insight is that ROCm in Docker can see the GPU through:
1. `/dev/dxg` device pass-through
2. Mounting `/opt/rocm-7.2.1:/opt/rocm:ro` (NOT /opt/rocm from WSL2)
3. Setting `HSA_ENABLE_DXG_DETECTION=1`

## Working Docker Run Command

```bash
docker run --rm --device=/dev/dxg \
  -v /usr/lib/wsl/lib:/usr/lib/wsl/lib \
  -v /opt/rocm-7.2.1:/opt/rocm:ro \
  -e HSA_ENABLE_DXG_DETECTION=1 \
  -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib \
  -e ROCM_PATH=/opt/rocm \
  rocm/dev-ubuntu-24.04:7.1.1-complete \
  rocminfo
```

## Verify GPU is Visible

```bash
# Run this in WSL2:
wsl.exe -d Ubuntu-24.04 -e docker run --rm --device=/dev/dxg \
  -v /usr/lib/wsl/lib:/usr/lib/wsl/lib \
  -v /opt/rocm-7.2.1:/opt/rocm:ro \
  -e HSA_ENABLE_DXG_DETECTION=1 \
  -e LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib \
  -e ROCM_PATH=/opt/rocm \
  rocm/dev-ubuntu-24.04:7.1.1-complete \
  rocminfo
```

Expected output should show:
- Agent 2: gfx1201 (AMD Radeon RX 9070 XT)
- Device Type: GPU
- Memory: ~16GB

## Why This Works

ROCm can use the DirectX compute path via librocdxg when:
1. `/dev/dxg` is passed through (DirectX device)
2. ROCm 7.2.1 libraries are mounted (contain librocdxg.so)
3. `HSA_ENABLE_DXG_DETECTION=1` tells ROCm to use DirectX

## docker-compose.yml Example

```yaml
services:
  rocm:
    image: rocm/dev-ubuntu-24.04:7.1.1-complete
    devices:
      - /dev/dxg:/dev/dxg
    volumes:
      - /usr/lib/wsl/lib:/usr/lib/wsl/lib:ro
      - /opt/rocm-7.2.1:/opt/rocm:ro
    environment:
      - HSA_ENABLE_DXG_DETECTION=1
      - LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib
      - ROCM_PATH=/opt/rocm
```

## Current Status

- ROCm GPU Detection: WORKING
- vLLM GPU Inference: UNKNOWN (library compatibility issues)
- Ollama GPU Inference: UNKNOWN (needs testing)

## Notes

- `/dev/kfd` and `/dev/dri` do NOT exist in WSL2 (not needed)
- The DirectX path through `/dev/dxg` is sufficient for ROCm
- Must mount `/opt/rocm-7.2.1` from WSL2, not from container
