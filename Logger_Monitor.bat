@echo off
REM Background Logger Monitor - Run alongside OpenCode
REM ====================================================
REM Runs conversation_logger in background to verify logging
REM Opens new window and monitors chat:history for new messages

echo Starting Background Logger Monitor...
echo Log file: E:\AI-Setup\session_logs\conversation_backup_log.jsonl
echo.

REM Run the logger in monitor mode (continuous) - opens new window
start "Logger Monitor" cmd /k "cd /d E:\AI-Setup && C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe conversation_logger.py --monitor"

echo Logger Monitor started in new window.
echo It will automatically log all chat messages.
pause