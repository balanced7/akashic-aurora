"""
Service definitions — DAG inputs for Akashic Aurora (E:\\AI-Setup).

Tiers are resolved by ``dag.resolve_tiers()`` from ``depends`` edges.

Topology aligns with ``config.py`` / ``bootstrap.md``: WSL Redis (writes typically 6380),
Docker Redis Stack mirror 16379, summarizer via Docker ``ai-voice`` → ``localhost:5000``.
"""

from pathlib import Path

AI_SETUP_ROOT = Path(__file__).resolve().parents[1]

SESSION_COMPRESSOR_PY = AI_SETUP_ROOT / "session_compressor.py"
AI_WATCHDOG_PY = AI_SETUP_ROOT / "ai_watchdog.py"
STACK_GUI_PY = AI_SETUP_ROOT / "stack_gui.py"
AI_SETUP_MCP_PY = AI_SETUP_ROOT / "ai_setup_mcp.py"


def _win(p: Path) -> str:
    return str(p.resolve())


WSL_REDIS_HA_BLOCK = (
    "pkill -f 'redis-server' 2>/dev/null || true; "
    "pkill -f 'redis-sentinel' 2>/dev/null || true; "
    "sleep 1; "
    "redis-server /opt/redis/master/redis-master.conf --daemonize yes --logfile /var/log/redis/master.log; "
    "redis-server /opt/redis/replica1/redis-replica1.conf --daemonize yes --logfile /var/log/redis/replica1.log; "
    "redis-server /opt/redis/replica2/redis-replica2.conf --daemonize yes --logfile /var/log/redis/replica2.log; "
    "sleep 2; "
    "redis-server /opt/redis/sentinel1/sentinel1.conf --sentinel --daemonize yes --logfile /var/log/redis/sentinel1.log; "
    "redis-server /opt/redis/sentinel2/sentinel2.conf --sentinel --daemonize yes --logfile /var/log/redis/sentinel2.log; "
    "redis-server /opt/redis/sentinel3/sentinel3.conf --sentinel --daemonize yes --logfile /var/log/redis/sentinel3.log; "
    "sleep 2; "
    "redis-cli -p 6380 PING"
)

WSL_REDIS_HA_STOP = (
    "pkill -f redis-server 2>/dev/null || true; "
    "pkill -f redis-sentinel 2>/dev/null || true"
)


SERVICES = {
    "wsl-keeper": {
        "description": "WSL2 VM keep-alive (detached bash sleep in Ubuntu-Migrate)",
        "runtime": "windows",
        "command": (
            'Start-Process -WindowStyle Hidden -FilePath wsl '
            '-ArgumentList "-d","Ubuntu-Migrate","-e","bash","-lc","sleep infinity"'
        ),
        "depends": [],
        "health": {"type": "wsl_alive"},
        "stop": "wsl --terminate Ubuntu-Migrate",
        "ports": [],
        "resources": {"cpu_cores": 0, "ram_mb": 0, "gpu_vram_mb": 0},
        "startup_timeout": 15,
    },
    "wsl-redis-ha": {
        "description": "WSL Redis Stack HA (master + replicas + sentinels); app writes use port 6380",
        "runtime": "wsl",
        "command": WSL_REDIS_HA_BLOCK,
        "depends": ["wsl-keeper"],
        "health": {"type": "redis_ping", "port": 6380},
        "stop": WSL_REDIS_HA_STOP,
        "ports": [6379, 6380, 6381, 26379, 26380, 26381],
        "resources": {"cpu_cores": 2, "ram_mb": 768, "gpu_vram_mb": 0},
        "endpoint": {"host": "127.0.0.1", "port": 6380, "protocol": "redis"},
        "startup_timeout": 35,
    },
    "docker-edge-redis": {
        "description": "Docker Redis Stack mirror (host port 16379) — optional dual-write target",
        "runtime": "windows",
        "command": (
            'docker start docker-redis-master 2>$null; if (-not $?) { '
            'Write-Host "docker-redis-master not found — start your Docker Redis manually or adjust container name." }; '
            "exit 0"
        ),
        "depends": [],
        "health": {"type": "tcp", "host": "127.0.0.1", "port": 16379},
        "stop": "docker stop docker-redis-master",
        "ports": [16379],
        "resources": {"cpu_cores": 0.5, "ram_mb": 256, "gpu_vram_mb": 0},
        "startup_timeout": 20,
    },
    "docker-ai-voice": {
        "description": "Docker ai-voice (+ ai-ollama) — summarizer API http://localhost:5000",
        "runtime": "windows",
        "command": (
            "docker start ai-ollama 2>$null; "
            "docker start ai-voice 2>$null; "
            "exit 0"
        ),
        "depends": ["wsl-redis-ha"],
        "health": {"type": "http", "url": "http://127.0.0.1:5000/health"},
        "stop": "docker stop ai-voice; docker stop ai-ollama",
        "ports": [5000, 11434],
        "resources": {"cpu_cores": 2, "ram_mb": 4096, "gpu_vram_mb": 8192},
        "endpoint": {"host": "127.0.0.1", "port": 5000, "protocol": "http"},
        "startup_timeout": 45,
    },
    "win-mcp": {
        "description": "Akashic Aurora MCP (stdio-capable); HTTP mode on 8080",
        "runtime": "windows",
        "command": (
            "if (Get-Process python -ErrorAction SilentlyContinue | Where-Object "
            '{$_.CommandLine -like "*ai_setup_mcp*"}) { exit 0 }; '
            "Start-Process -WindowStyle Hidden -FilePath python "
            f'-ArgumentList "{_win(AI_SETUP_MCP_PY)}","--http","--port","8080"'
        ),
        "depends": ["wsl-redis-ha"],
        "health": {"type": "tcp", "host": "127.0.0.1", "port": 8080},
        "stop": (
            "Get-Process python -ErrorAction SilentlyContinue | "
            'Where-Object {$_.CommandLine -like "*ai_setup_mcp*"} | '
            "Stop-Process -Force"
        ),
        "ports": [8080],
        "resources": {"cpu_cores": 0.5, "ram_mb": 256, "gpu_vram_mb": 0},
        "endpoint": {"host": "127.0.0.1", "port": 8080, "protocol": "http"},
        "memory_limit_mb": 512,
        "startup_timeout": 20,
    },
    "win-compressor": {
        "description": "Session compressor daemon — stream + Redis log summarization",
        "runtime": "windows",
        "command": (
            "if (Get-Process python -ErrorAction SilentlyContinue | Where-Object "
            '{$_.CommandLine -like "*session_compressor*"}) { exit 0 }; '
            "Start-Process -WindowStyle Hidden -FilePath python "
            f'-ArgumentList "{_win(SESSION_COMPRESSOR_PY)}","--daemon"'
        ),
        "depends": ["wsl-redis-ha", "docker-ai-voice"],
        "health": {"type": "process", "name": "session_compressor"},
        "stop": (
            "Get-Process python -ErrorAction SilentlyContinue | "
            'Where-Object {$_.CommandLine -like "*session_compressor*"} | '
            "Stop-Process -Force"
        ),
        "ports": [],
        "resources": {"cpu_cores": 0.5, "ram_mb": 256, "gpu_vram_mb": 0},
        "memory_limit_mb": 512,
        "startup_timeout": 25,
    },
    "win-ai-watchdog": {
        "description": "AI Watchdog — port registry sync, canonical logging checks, infra snapshot loop",
        "runtime": "windows",
        "command": (
            "if (Get-Process python -ErrorAction SilentlyContinue | Where-Object "
            '{$_.CommandLine -like "*ai_watchdog*"}) { exit 0 }; '
            "Start-Process -WindowStyle Hidden -FilePath python "
            f'-ArgumentList "{_win(AI_WATCHDOG_PY)}","--daemon"'
        ),
        "depends": ["wsl-redis-ha"],
        "health": {"type": "process", "name": "ai_watchdog"},
        "stop": (
            "Get-Process python -ErrorAction SilentlyContinue | "
            'Where-Object {$_.CommandLine -like "*ai_watchdog*"} | '
            "Stop-Process -Force"
        ),
        "ports": [],
        "resources": {"cpu_cores": 0.25, "ram_mb": 128, "gpu_vram_mb": 0},
        "memory_limit_mb": 256,
        "startup_timeout": 18,
    },
    "win-stack-gui": {
        "description": "Akashic Aurora web GUI (FastAPI stack_gui on 8090)",
        "runtime": "windows",
        "command": (
            "if (Get-Process python -ErrorAction SilentlyContinue | Where-Object "
            '{$_.CommandLine -like "*stack_gui*"}) { exit 0 }; '
            "Start-Process -WindowStyle Hidden -FilePath python "
            f'-ArgumentList "{_win(STACK_GUI_PY)}","--no-browser"'
        ),
        "depends": ["wsl-redis-ha"],
        "health": {"type": "tcp", "host": "127.0.0.1", "port": 8090},
        "stop": (
            "Get-Process python -ErrorAction SilentlyContinue | "
            'Where-Object {$_.CommandLine -like "*stack_gui*"} | '
            "Stop-Process -Force"
        ),
        "ports": [8090],
        "resources": {"cpu_cores": 0.5, "ram_mb": 512, "gpu_vram_mb": 0},
        "memory_limit_mb": 1024,
        "startup_timeout": 45,
    },
}
