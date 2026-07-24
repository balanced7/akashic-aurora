# ROCm 7.2.2 WSL2 Configuration
# For AMD RX 9070 XT (RDNA4 / gfx1200)
# Created: 2026-04-23

# ROCm 7.2.2 lib path (7.2.2 added after removing old Ubuntu packages)
export LD_LIBRARY_PATH=/opt/rocm-7.2.2/lib:/opt/rocm-7.2.1/lib:/usr/lib/wsl/lib:/opt/rocm/lib:/opt/rocm/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}

# GPU Detection via WSL DXG bridge
export HSA_ENABLE_DXG_DETECTION=1

# RDNA4 GPU override (gfx1200 = 12.0.0)
export HSA_OVERRIDE_GFX_VERSION=12.0.0

# ROCm binary paths - use ROCm 7.2.2 binaries first
export PATH=/opt/rocm-7.2.2/bin:/opt/rocm/bin:/opt/rocm-7.2.1/bin${PATH:+:$PATH}