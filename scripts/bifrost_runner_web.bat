@echo off
REM Gemini as a Bifrost citizen via FREE web UI (no API quota). Login once: gemini_web_login.bat
REM Repo root derived from this file's own location (%%~dp0), never hardcoded.
cd /d "%%~dp0.."
set PYTHONUNBUFFERED=1
py scripts\bifrost_runner.py --provider web
pause
