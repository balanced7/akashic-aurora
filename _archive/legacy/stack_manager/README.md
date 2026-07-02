# stack_manager — DAG orchestration

Starts Akashic Aurora services in **dependency tiers** (see `dag.py`: topological sort + parallelism).

## Requirements

- Python **psutil** (CLI uses it): `pip install psutil`
- Working directory **must be `E:\AI-Setup`** when running the module (so `config.py` resolves correctly).

## Usage

```powershell
cd E:\AI-Setup
python -m stack_manager.cli start    # launch tiers in order
python -m stack_manager.cli status
python -m stack_manager.cli stop     # stops services then terminates WSL
python -m stack_manager.cli monitor
```

Or:

```powershell
powershell -ExecutionPolicy Bypass -File E:\AI-Setup\scripts\stack_bootstrap.ps1 start
```

## Services (`config.py`)

Aligned with main **`bootstrap.md`**: `wsl-redis-ha`, optional `docker-edge-redis` (`docker-redis-master` on host **16379** — create once with **`docker compose -f dockerized-ai/redis/docker-compose-edge-mirror.yml up -d`**), `docker-ai-voice` (`ai-voice` + `ai-ollama`), `win-ai-watchdog` (`ai_watchdog.py --daemon` — ports + logging + infra snapshot), `win-stack-gui` (`stack_gui.py` — **http://127.0.0.1:8090**), `win-mcp` (`ai_setup_mcp.py`), `win-compressor` (`session_compressor.py`).

**Desktop launcher:** build **`Launch AI Stack.exe`** with **`scripts\build_launch_ai_stack.ps1`** (PyInstaller); source **`launch_ai_stack.py`** (Tk — runs `python -m stack_manager.cli start` and opens the Stack GUI / chat URLs).

Redis registry sidecars use **`config.get_redis_config()`** (WSL master port **6380**).
