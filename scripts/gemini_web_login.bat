@echo off
REM One-time Google login for Gemini web + AI Mode (free, not API tokens)
REM Repo root derived from this file's own location (%%~dp0), never hardcoded.
cd /d "%%~dp0.."
py -m pip install -r requirements-gemini-web.txt -q
py -m playwright install chrome
py scripts\gemini_web.py --login
