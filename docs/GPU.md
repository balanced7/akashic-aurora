# GPU Setup & Issues

Status: current (2026-09-03, research refresh — see Update below; hardware status)

## Update (2026-09-03): ROCm 10.0.0 changes the picture

Per AMD's official release notes (rocm.docs.amd.com, ROCm 10.0.0, dated 2026-08-26):
- RX 9070 XT (gfx1201/RDNA4 — the card below) is now officially listed supported hardware.
- ROCm 10.0.0 is native on **Windows**, not WSL2-only — the docs say "Applies to Linux and Windows." The old separate "HIP SDK for Windows" track (which lagged the mainline Linux releases and is what the April config below was working around) is now legacy; Windows is folded into the same release train as Linux.
- Driver stack: Windows 11 25H2 + AMD Adrenalin 26.8.1 + a "Windows CDE CPR" component (26.10.32) — not a hand-rolled WSL2 passthrough.
- PyTorch 2.13.0 is the officially supported version in this release.
- Known caveat straight from AMD's own release notes: "PyTorch training and fine-tuning workloads might experience GPU resets or crashes on some Radeon GPUs." Inference is not on that known-issues list.

**Not yet verified on this box** — the WSL2/CPU-fallback config below was the working answer as of April; native ROCm 10.0.0 on Windows has not been installed/tested here yet. Treat the section below as historical until someone runs the new path and updates this file.

## Status as of 2026-04-13 (superseded by the update above, kept for reference)

### GPU: AMD RX 9070 XT (16GB VRAM)
- **Architecture**: RDNA4 (gfx1201)
- **ROCm Version**: 7.2.1
- **Status**: WORKING (CPU fallback mode)

## The Issue (as of April, ROCm 7.2.1)

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

## Future Solutions (as of April; see 2026-09-03 update above for what actually landed)

1. ~~Wait for ROCm 7.3+ with RDNA4 support~~ — done: ROCm 10.0.0 (2026-08-26) supports gfx1201 natively on Windows. Not yet installed/tested on this box.
2. Try AMD ROCm staging builds
3. Use CPU mode (current - works fine for small models)

---

## Updated: 2026-09-03 (research refresh; original entry 2026-04-13 preserved above)