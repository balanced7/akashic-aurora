# GPU Setup & Issues

Status: current (2026-09-04, ROCm 10.0.0 + PyTorch 2.13 VERIFIED LIVE on this box — see below)

## Update (2026-09-03): ROCm 10.0.0 changes the picture

Per AMD's official release notes (rocm.docs.amd.com, ROCm 10.0.0, dated 2026-08-26):
- RX 9070 XT (gfx1201/RDNA4 — the card below) is now officially listed supported hardware.
- ROCm 10.0.0 is native on **Windows**, not WSL2-only — the docs say "Applies to Linux and Windows." The old separate "HIP SDK for Windows" track (which lagged the mainline Linux releases and is what the April config below was working around) is now legacy; Windows is folded into the same release train as Linux.
- Driver stack: Windows 11 25H2 + AMD Adrenalin 26.8.1 + a "Windows CDE CPR" component (26.10.32) — not a hand-rolled WSL2 passthrough.
- PyTorch 2.13.0 is the officially supported version in this release.
- Known caveat straight from AMD's own release notes: "PyTorch training and fine-tuning workloads might experience GPU resets or crashes on some Radeon GPUs." Inference is not on that known-issues list.

## VERIFIED LIVE on this box (2026-09-04 night, Daniil present)

No driver change was needed: the installed 32.0.31041.1004 (2026-08-17) IS Adrenalin 26.8.1's
driver core — exactly the version the ROCm 10.0.0 matrix validates. (26.9.1 released 2026-09-03
but is undocumented against ROCm 10; deliberately skipped to stay on the validated combo.)

- **Venv**: `E:\venvs\rocm10` (Python 3.11). System Python untouched. The legacy HIP SDK 7.1
  (8 MSIs) was uninstalled first — a documented ROCm 10 prerequisite; restore point 94 taken,
  rollback product codes in note `preflight-2026-09-04-rocm10-climb`.
- **Installed**: `rocm[libraries,device-gfx1201]==10.0.0` + `torch==2.13.0+rocm10.0.0` /
  `torchvision==0.28.0+rocm10.0.0` / `torchaudio==2.11.0.2+rocm10.0.0` from
  `https://stable.repo.amd.com/rocm/whl-next/`.
- **Receipts**: hipinfo enumerates the 9070 XT (32 CU, 15.92 GB); `torch.cuda.is_available()`
  True on HIP 7.15.26333; **fp16 4096³ matmul 1.48 ms = 92.7 TFLOPS** (≈ card spec). The fp32
  first-call figure is kernel-compile-polluted — warm up before benchmarking anything.

Install gotchas, all hit live tonight:
1. AMD's documented single-index pip command fails under pip ≥ 26: the build dep (`wheel`)
   can't resolve from AMD's index → add `--extra-index-url https://pypi.org/simple`.
2. The `rocm` meta-package is a legacy sdist: against a venv's bundled setuptools 65 it dies
   with `invalid command 'bdist_wheel'` → `pip install -U setuptools` (84.x works), then
   install with `--no-build-isolation`. The real payloads are binary wheels; only this
   29 KB shim needs building.
3. MIOpen first-run auto-tuning makes the first conv SECONDS slow (12.2 s observed on a
   batch-64 conv2d); steady state is milliseconds. Not a regression — an empty kernel cache.
4. `torch.cuda.device_count()` is 2 — the iGPU is enumerated too. Pin device 0 or set
   `HIP_VISIBLE_DEVICES=0` so workloads never land on the integrated GPU.
5. `xnack 'Off'` warnings on RDNA4 are cosmetic.
6. AMD still flags training/fine-tuning flaky on gfx1201 (workaround
   `TORCH_BLAS_PREFER_HIPBLASLT=0`, perf cost); inference has no documented known issue.

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