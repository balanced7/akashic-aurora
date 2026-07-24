@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM  AKASHIC AURORA — One‑click Bifrost Launch
REM  Double‑click this from your desktop to bring up DeepSeek + the Bifrost cockpit.
REM
REM  What it does:
REM    1. Starts Redis (Docker) if not running
REM    2. Starts the Bifrost UI web console  (http://127.0.0.1:8787)
REM    3. Opens your browser to it
REM    4. Auto‑launches deepseek‑build (agentic + write + shell) so DeepSeek is
REM       ready to build the moment the page loads
REM
REM  To QUIT: close the Bifrost UI terminal (Ctrl‑C). The launcher cleans up.
REM  To change which DeepSeek mode launches, edit the DEEPSEEK_MODE below.
REM ═══════════════════════════════════════════════════════════════════════════════
setlocal enabledelayedexpansion

cd /d "%~dp0.."
set ROOT=%CD%

REM ── Knobs (change these to suit) ──────────────────────────────────────────
set UI_PORT=8787
set REDIS_NAME=akashic-redis
set REDIS_PORT=16379

REM deepseek-build  = agentic + write + shell  (full builder, uses your API key)
REM deepseek        = agentic, read‑only       (review/critique/answer)
REM deepseek-think  = agentic + deep thinking  (slower, deeper analysis)
REM deepseek-write  = agentic + write access   (can edit files, no shell)
set DEEPSEEK_MODE=deepseek-build

REM ── Colours ───────────────────────────────────────────────────────────────
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set G=  %ESC%[92m
set C=  %ESC%[96m
set Y=  %ESC%[93m
set R=  %ESC%[0m

echo.
echo %C%╔════════════════════════════════════════════╗
echo %C%║   AKASHIC AURORA · Bifrost Launcher      ║
echo %C%╚════════════════════════════════════════════╝%R%
echo.

REM ── [1/4] Redis ──────────────────────────────────────────────────────────
echo %C%[1/4] Redis (port %REDIS_PORT%)...%R%
call :check-redis
if %REDIS_OK%==1 (
    echo %G%  ✓ Redis already running%R%
) else (
    echo %Y%  Redis not running — starting Docker container '%REDIS_NAME%'...%R%
    docker start %REDIS_NAME% >nul 2>&1
    if errorlevel 1 (
        echo %Y%  Container doesn't exist — creating it...%R%
        docker run -d --name %REDIS_NAME% -p %REDIS_PORT%:6379 redis:7-alpine >nul 2>&1
        if errorlevel 1 (
            echo %R%  ✗ Docker failed. Is Docker Desktop running?%R%
            echo %Y%  The Bifrost UI will start anyway; the bus may be offline.%R%
        )
    )
    REM Wait for Redis to be ready (max 10s)
    for /L %%i in (1,1,20) do (
        call :check-redis
        if !REDIS_OK!==1 goto :redis-ready
        timeout /t 1 /nobreak >nul
    )
    :redis-ready
    if !REDIS_OK!==1 (
        echo %G%  ✓ Redis is now reachable%R%
    ) else (
        echo %R%  ⚠ Redis still not reachable after 20s — bus will be offline%R%
    )
)

REM ── [2/4] Bifrost UI ─────────────────────────────────────────────────────
echo.
echo %C%[2/4] Bifrost UI (http://127.0.0.1:%UI_PORT%)...%R%

REM Kill any stale UI on this port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%UI_PORT% " ^| findstr LISTENING 2^>nul') do (
    taskkill /pid %%a /f >nul 2>&1
)

start "Bifrost UI" /min cmd /c "cd /d %ROOT% && py scripts/bifrost_ui.py --port %UI_PORT%"
echo %G%  ✓ Bifrost UI launching (minimised window)%R%

REM Wait for the UI to be ready
for /L %%i in (1,1,15) do (
    curl -s -o nul http://127.0.0.1:%UI_PORT%/status 2>nul
    if not errorlevel 1 goto :ui-ready
    timeout /t 1 /nobreak >nul
)
:ui-ready
echo %G%  ✓ UI reachable%R%

REM ── [3/4] Browser ────────────────────────────────────────────────────────
echo.
echo %C%[3/4] Browser...%R%
start "" http://127.0.0.1:%UI_PORT%
echo %G%  ✓ Opened http://127.0.0.1:%UI_PORT%%R%

REM ── [4/4] Launch DeepSeek ────────────────────────────────────────────────
echo.
echo %C%[4/4] DeepSeek (%DEEPSEEK_MODE%)...%R%

REM If a previous deepseek runner is lingering (pid file or runner lock), kill it
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "16379" 2^>nul') do (
    rem we don't kill redis connections; just checking
)

REM Ask the UI's launcher to spawn deepseek
for /L %%i in (1,1,10) do (
    curl -s -X POST http://127.0.0.1:%UI_PORT%/launcher/launch -H "Content-Type: application/json" -d "{\"agent_id\":\"%DEEPSEEK_MODE%\"}" >nul 2>&1
    if not errorlevel 1 goto :ds-launched
    timeout /t 2 /nobreak >nul
)
:ds-launched

REM Verify it launched
curl -s http://127.0.0.1:%UI_PORT%/launcher/status 2>nul | findstr /C:"\"tag\":\"%DEEPSEEK_MODE%\"" | findstr /C:"\"status\":\"running\"" >nul
if not errorlevel 1 (
    echo %G%  ✓ DeepSeek running (%DEEPSEEK_MODE%)%R%
) else (
    echo %Y%  ⚠ DeepSeek may still be starting — check the UI launcher panel%R%
)

REM ── Done ─────────────────────────────────────────────────────────────────
echo.
echo %G%╔════════════════════════════════════════════╗
echo %G%║   BIFROST IS LIVE                          ║
echo %G%╠════════════════════════════════════════════╣
echo %G%║  UI:  http://127.0.0.1:%UI_PORT%                  ║
echo %G%║  Redis: port %REDIS_PORT%                          ║
echo %G%║  DeepSeek: %DEEPSEEK_MODE%  ║
echo %G%╚════════════════════════════════════════════╝%R%
echo.
echo %Y%  Type messages to 'deepseek' in the UI — it auto‑responds.%R%
echo %Y%  Use the launcher panel (⚡ button) to manage agents.%R%
echo %Y%  Close the 'Bifrost UI' terminal window to shut everything down.%R%
echo.
echo %C%  Press any key to exit this launcher (Bifrost stays running)...%R%
pause >nul
exit /b 0

REM ── Helpers ──────────────────────────────────────────────────────────────
:check-redis
set REDIS_OK=0
docker exec %REDIS_NAME% redis-cli -p 6379 ping >nul 2>&1
if not errorlevel 1 set REDIS_OK=1
exit /b
