@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
:: AKASHIC AURORA - FAST LAUNCHER
:: Single-click to launch fully primed OpenCode
:: ============================================================

:check_admin
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ELEVATE] Restarting with admin privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %CD% && %~f0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo AKASHIC AURORA - FAST LAUNCH
echo ============================================================
echo.

:: ============================================================
:: STEP 1: DOCKER (skip if already running)
:: ============================================================
echo [1/4] Checking Docker...

docker ps >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [SKIP] Docker already running
    goto :docker_ready
)

echo   [START] Launching Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

:: Wait for Docker with progress dots
set docker_wait=0
:docker_wait
timeout /t 3 /nobreak >nul
docker ps >nul 2>&1
if %ERRORLEVEL% neq 0 (
    set /a docker_wait+=3
    if !docker_wait! lss 60 (
        echo   Waiting... !docker_wait!s
        goto :docker_wait
    )
    echo   [FAIL] Docker took too long to start
    echo   Please start Docker Desktop manually, then run this again.
    pause
    exit /b 1
)

:docker_ready
echo   [OK] Docker ready

:: ============================================================
:: STEP 2: REDIS HA (smart restart - only if needed)
:: ============================================================
echo.
echo [2/4] Checking Redis HA...

:: Quick check if containers are running
set redis_count=0
for %%c in (redis-master redis-replica1 redis-replica2 sentinel1 sentinel2 sentinel3) do (
    docker ps --filter "name=%%c" --format "{{.Status}}" | findstr /C:"Up" >nul 2>&1
    if !ERRORLEVEL! equ 0 set /a redis_count+=1
)

if !redis_count! equ 6 (
    echo   [SKIP] All 6 Redis containers already running
    goto :redis_ready
)

echo   [START] Starting Redis HA cluster...
cd /d E:\AI-Setup\dockerized-ai\redis

:: Cleanup any broken containers
docker compose -f docker-compose-ha.yml down >nul 2>&1

:: Start fresh
docker compose -f docker-compose-ha.yml up -d
echo   Waiting for containers...
timeout /t 8 /nobreak >nul

:: Quick verify
set /a redis_count=0
for %%c in (redis-master redis-replica1 redis-replica2 sentinel1 sentinel2 sentinel3) do (
    docker ps --filter "name=%%c" --format "{{.Status}}" | findstr /C:"Up" >nul 2>&1
    if !ERRORLEVEL! equ 0 set /a redis_count+=1
)

if !redis_count! equ 6 (
    echo   [OK] Redis HA cluster ready
) else (
    echo   [WARN] Only !redis_count!/6 containers running
)

:redis_ready

:: Quick Redis test
for /f %%i in ('docker exec redis-master redis-cli PING 2^>nul') do set pong=%%i
if "!pong!"=="PONG" (
    echo   [OK] Redis responding
) else (
    echo   [WARN] Redis may not be fully ready
)

:: ============================================================
:: STEP 3: SYNC SERVICE (start in background)
:: ============================================================
echo.
echo [3/4] Checking Sync Service...

:: Check if already running
tasklist /FI "WINDOWTITLE eq redis_sync*" 2>nul | findstr /C:"python.exe" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [SKIP] Sync already running
    goto :sync_ready
)

cd /d E:\AI-Setup
start "redis_sync" python services\redis_sync.py --daemon
timeout /t 2 /nobreak >nul
echo   [OK] Sync started

:sync_ready

:: ============================================================
:: STEP 4: LAUNCH OPENCODE (primed)
:: ============================================================
echo.
echo [4/4] Launching OpenCode...

:: Build primed command with context
set PRIMED_CMD="cd /d E:\AI-Setup && python -c \"from project_context import get_context_manager; mgr = get_context_manager(); ctx = mgr.get_full_context(); print('Architecture:', list(ctx.get('architecture', {}).keys())[:3]); print('Recent:', len(ctx.get('recent_sessions', [])))\""

cd /d E:\AI-Setup

:: Launch OpenCode with the agent primed via system prompt context
start "OpenCode" opencode --system-prompt-file E:\AI-Setup\AGENT_PRIMER.md

echo.
echo ============================================================
echo READY
echo ============================================================
echo.
echo Services: Redis HA, Sync running
echo OpenCode: Launched with AGENT_PRIMER context
echo.
echo Tip: First message to OpenCode should be:
echo   "Run the bootstrap catchup and tell me the status"
echo.
pause
endlocal
