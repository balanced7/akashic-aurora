#!/bin/bash
docker rm -f ollama-rocm 2>/dev/null
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
  --name ollama-rocm \
  ollama/ollama:rocm
echo "Started Ollama with port mapping"