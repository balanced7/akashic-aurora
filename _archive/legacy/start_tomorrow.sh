#!/bin/bash
# Quick Start for 2026-04-24
# Run this to get everything up and running

echo "=== Quick Start 2026-04-24 ==="

# Start Redis HA (if not running)
echo "[1/4] Checking Redis..."
wsl -d Ubuntu-Migrate -e bash -c "
  redis-server /opt/redis/master/redis-master.conf --daemonize yes 2>/dev/null || true
" 2>/dev/null

# Source ROCm (GPU working!)
echo "[2/4] ROCm environment..."
source /etc/profile.d/rocm.sh 2>/dev/null

# Start session logger
echo "[3/4] Session logger..."
cd /mnt/e/AI-Setup 2>/dev/null && nohup /opt/venv/bin/python log.py action "SESSION START" --tags session_start > /dev/null 2>&1 &

# Check GPU
echo "[4/4] GPU status..."
source /etc/profile.d/rocm.sh && /opt/voice_env/bin/python3 -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"

echo "=== Ready ==="
echo ""
echo "Next: Start WSL voice service with GPU:"
echo "  wsl -d Ubuntu-Migrate -e bash -c 'source /etc/profile.d/rocm.sh; cd /mnt/e/AI-Setup/gemma_realtime && nohup python server.py > /tmp/gemma.log 2>&1 &'"