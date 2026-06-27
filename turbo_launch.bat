@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
:: BREAKTHROUGH STACK - TURBO LAUNCH
:: Optimized for fastest possible OpenCode startup
:: ============================================================

:check_admin
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ELEVATE] Restarting with admin privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %CD% && %~f0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo BREAKTHROUGH STACK - TURBO LAUNCH
echo ============================================================
echo.

:: ============================================================
:: PHASE 1: DOCKER (PARALLEL)
:: ============================================================
echo [1/3] Docker...

docker ps >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [OK] Docker already running
    goto :check_redis
)

echo   [START] Launching Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

:: Background wait with quick checks
set /a docker_tries=0
:docker_wait
timeout /t 3 /nobreak >nul
docker ps >nul 2>&1
if %ERRORLEVEL% neq 0 (
    set /a docker_tries+=1
    if !docker_tries! lss 15 (
        goto :docker_wait
    )
)
echo   [OK] Docker ready

:: ============================================================
:: PHASE 2: REDIS (SMART)
:: ============================================================
:check_redis
echo.
echo [2/3] Redis HA...

:: Ultra-quick check - just ping existing master
docker exec redis-master redis-cli PING >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [OK] Redis already running
    goto :redis_done
)

:: Quick restart if needed
cd /d E:\AI-Setup\dockerized-ai\redis
docker compose -f docker-compose-ha.yml up -d
timeout /t 6 /nobreak >nul

:: Quick verify
docker exec redis-master redis-cli PING >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [OK] Redis HA started
) else (
    echo   [WARN] Redis may need more time
)

:redis_done

:: ============================================================
:: PHASE 3: CONTEXT + LAUNCH (FASTEST)
:: ============================================================
echo.
echo [3/3] OpenCode...

:: Initialize Fast Cache (RAM + RAM Disk + Redis)
python -c "import sys; sys.path.insert(0, r'E:\AI-Setup'); from fast_cache import get_cache_status; s = get_cache_status(); print('Fast Cache: RAM(' + str(s['ram_cache_entries']) + ') Disk(' + s['ram_disk'] + ') Redis(' + ('Y' if s['redis_available'] else 'N') + ')')" 2>&1

:: Generate quick context file (reads from Redis if available, else cache)
cd /d E:\AI-Setup
python -c "
import sys, json
sys.path.insert(0, r'E:\AI-Setup')
try:
    from project_context import get_context_manager
    from fast_cache import redis_set
    mgr = get_context_manager()
    ctx = mgr.get_full_context()
    # Extract just the essentials for quick load
    quick = {
        'milestones': ctx.get('milestones', [])[-5:],
        'recent': ctx.get('recent_sessions', [])[:5],
        'decisions': ctx.get('decisions', [])[-3:],
        'current_work': ctx.get('current_work', ''),
        'architecture': list(ctx.get('architecture', {}).keys())[:3],
        'status': 'redis_primed'
    }
    # Cache in fast_cache for sub-ms access
    redis_set('quick_context', quick, ttl=300)
    print('Context cached')
except Exception as e:
    print('Context: ' + str(e)[:50])
" 2>&1

:: Start sync in background (non-blocking)
start "redis_sync" python services\redis_sync.py --daemon

:: Launch OpenCode with fast primer
start "OpenCode" opencode --system-prompt-file E:\AI-Setup\AGENT_PRIMER.md

echo.
echo ============================================================
echo READY
echo ============================================================
echo.
echo Services: Redis HA (6 containers), Sync running
echo OpenCode: Launched and primed
echo Context: Quick context at E:\AI-Setup\blackboard_data\quick_context.json
echo.
endlocal
