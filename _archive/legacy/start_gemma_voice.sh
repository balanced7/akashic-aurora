#!/bin/bash
# Gemma Voice AI - Startup Script
# Run this to start all services in WSL2

echo "=== Gemma Voice AI Startup ==="

# Start Redis HA (if not running)
echo "[1/4] Checking Redis HA..."
redis-cli -p 6379 PING > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "  Starting Redis..."
    redis-server /opt/redis/master/redis-master.conf --daemonize yes
    redis-server /opt/redis/replica1/redis-replica1.conf --daemonize yes
    redis-server /opt/redis/replica2/redis-replica2.conf --daemonize yes
    redis-server /opt/redis/sentinel1/sentinel1.conf --sentinel --daemonize yes
    redis-server /opt/redis/sentinel2/sentinel2.conf --sentinel --daemonize yes
    redis-server /opt/redis/sentinel3/sentinel3.conf --sentinel --daemonize yes
    echo "  Redis HA started"
else
    echo "  Redis already running"
fi

# Start Ollama (if not running)
echo "[2/4] Checking Ollama..."
curl -s http://localhost:11434/api/tags > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "  Starting Ollama..."
    export OLLAMA_MODELS=/root/.ollama/models
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
    echo "  Ollama started"
else
    echo "  Ollama already running"
fi

# Start Gemma Voice Service
echo "[3/4] Starting Gemma Voice Service..."
source /root/rocm-venv/bin/activate
nohup python -u /mnt/e/AI-Setup/gemma_voice_service.py > /tmp/gemma.log 2>&1 &
sleep 5

# Verify
echo "[4/4] Verifying services..."
sleep 2
curl -s http://localhost:5000/health | python -c "import sys,json; d=json.load(sys.stdin); print(f\"  Gemma Voice: {d['status']}\")"
curl -s http://localhost:11434/api/tags | python -c "import sys,json; d=json.load(sys.stdin); print(f\"  Ollama: UP ({len(d.get('models',[]))} models)\")"
redis-cli -p 6379 PING | python -c "import sys; print(f\"  Redis: {'UP' if 'PONG' in input() else 'DOWN'}\")"

echo ""
echo "=== Services Ready ==="
echo "  Gemma Voice: http://localhost:5000"
echo "  Ollama:      http://localhost:11434"
echo "  Redis:       localhost:6379"
echo ""
echo "Endpoints:"
echo "  POST /chat           - Chat with Gemma"
echo "  POST /voice/input    - Transcribe audio"
echo "  POST /voice/output   - Text to speech"
echo "  POST /code/execute   - Execute Python"
echo "  POST /memory/save    - Save to Redis"
echo "  GET  /models         - List models"
echo "  GET  /health         - Health check"
echo ""