@echo off
chcp 65001 >nul
echo ============================================================
echo AKASHIC AURORA - BOOTSTRAP
echo ============================================================
echo.

echo [1/6] Ensuring Docker Desktop is running...
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker not found. Please install Docker Desktop.
    pause
    exit /b 1
)

docker ps >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker to initialize (30 seconds)...
    timeout /t 30 /nobreak >nul
    :wait_loop
    docker ps >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        timeout /t 5 /nobreak >nul
        goto wait_loop
    )
)
echo [OK] Docker running

echo.
echo [2/6] Cleaning up old containers...
cd /d E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml down >nul 2>&1
docker stop redis-master redis-replica1 redis-replica2 sentinel1 sentinel2 sentinel3 >nul 2>&1
docker rm redis-master redis-replica1 redis-replica2 sentinel1 sentinel2 sentinel3 >nul 2>&1
echo [OK] Cleanup complete

echo.
echo [3/6] Starting Redis HA Cluster...
docker compose -f docker-compose-ha.yml up -d
echo Waiting for containers to start...
timeout /t 10 /nobreak >nul

echo.
echo [4/6] Verifying Redis containers...
set all_running=1
for %%c in (redis-master redis-replica1 redis-replica2 sentinel1 sentinel2 sentinel3) do (
    docker ps --filter "name=%%c" --format "{{.Status}}" | findstr /C:"Up" >nul
    if %ERRORLEVEL% equ 0 (
        echo   [OK] %%c
    ) else (
        echo   [FAIL] %%c NOT running
        set all_running=0
    )
)

echo.
echo [5/6] Testing Redis...
for /f %%i in ('docker exec redis-master redis-cli PING 2^>nul') do set pong=%%i
if "%pong%"=="PONG" (
    echo   [OK] Redis master responding
) else (
    echo   [WARN] Redis master not responding yet
)

echo.
echo [6/6] Starting Redis Sync Service...
cd /d E:\AI-Setup
taskkill /F /IM python.exe /FI "WINDOWTITLE eq redis_sync*" >nul 2>&1
start "redis_sync" python services\redis_sync.py --daemon
echo   [OK] Redis Sync started

echo.
echo [7/7] Initializing Fast Cache (RAM + Redis hybrid)...
python -c "import sys; sys.path.insert(0, r'E:\AI-Setup'); from fast_cache import get_cache_status; status = get_cache_status(); print('  [OK] RAM cache: ' + str(status['ram_cache_entries']) + ' entries'); print('  [OK] RAM disk: ' + status['ram_disk']); print('  [OK] Redis: ' + ('connected' if status['redis_available'] else 'not available'))"

echo.
echo [8/8] Auto-logging session...
python -c "import sys; sys.path.insert(0, r'E:\AI-Setup'); from auto_logger import AutoLogger; a=AutoLogger(); a.log_action('Bootstrap completed'); a.log_action('Redis HA cluster ready (6 containers)'); a.log_action('Fast Cache initialized (RAM + RAM Disk + Redis)'); a.log_action('MCP Server available'); print('  [OK] Session logged')"

echo.
echo ============================================================
echo BOOTSTRAP COMPLETE
echo ============================================================
echo.
echo Redis HA: 1 Master + 2 Replicas + 3 Sentinels
echo Sync: Running in background
echo Fast Cache: X:\ (RAM Disk) + Redis hybrid
echo.
echo To start MCP server: python E:\AI-Setup\ai_setup_mcp.py
echo.
echo Quick commands:
echo   python -c "from fast_cache import get_cache_status; print(get_cache_status())"
echo   quick_log.bat --status
echo.
pause
