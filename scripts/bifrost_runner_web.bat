@echo off
REM Gemini as a Bifrost citizen via FREE web UI (no API quota). Login once: gemini_web_login.bat
cd /d E:\AI-Setup
set PYTHONUNBUFFERED=1
py scripts\bifrost_runner.py --provider web
pause
