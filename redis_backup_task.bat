@echo off
REM Redis Backup - Windows Scheduled Task Setup
REM ===========================================
REM Run this as Administrator to create a scheduled task
REM that backs up Redis every 5 minutes

echo Redis Backup Task Setup
echo =========================

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Run as Administrator
    pause
    exit /b 1
)

REM Create scheduled task
schtasks /create /tn "Redis Backup" /tr "python.exe E:\AI-Setup\redis_backup.py --once" /sc minute /mo 5 /f

echo.
echo Task created successfully!
echo.
echo To manually run: python E:\AI-Setup\redis_backup.py --once
echo To see stats:    python E:\AI-Setup\redis_backup.py --stats
echo.
echo Backup location: E:\AI-Setup\blackboard_data\redis_backups
echo.
pause
