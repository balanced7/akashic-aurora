@echo off
chcp 65001 >nul
:: Quick Log - Log an action without opening Python
:: Usage: quick_log.bat "My action description"
::   or: quick_log.bat --status

if "%1"=="--status" goto :status
if "%1"=="" goto :usage

python -c "import sys; sys.path.insert(0, r'E:\AI-Setup'); from auto_logger import AutoLogger; a=AutoLogger(); a.log_action('%*'); print('Logged: %*')"
exit /b

:status
python -c "import sys; sys.path.insert(0, r'E:\AI-Setup'); from auto_logger import AutoLogger; a=AutoLogger(); print(f'Session: {a.session_id}'); print(f'Entries so far: {len(a.entries)}')"
exit /b

:usage
echo Usage:
echo   quick_log.bat "Your action here"
echo   quick_log.bat --status
exit /b
